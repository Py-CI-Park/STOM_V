"""대상 스크립트 무수정 래퍼 — 심박 갱신 + 종료코드 기록(WBS v3 P1-4).

사용(보통은 detached_runner가 이 모듈을 분리 기동한다 — 직접 호출도 가능):
    python -I -S <absolute bootstrap.py> child-wrap [--interval 5] <run_dir> <대상스크립트.py> [인자...]

동작:
  1) run_dir에 pid.txt(자기 PID)·heartbeat.txt를 즉시 기록.
  2) 대상 스크립트를 [현재 python, -I, -S, bootstrap.py, target, 대상, 인자...]로
     자식 프로세스로 기동(stdout/stderr → run_dir/log.txt append — 대상 스크립트 무수정
     원칙, 기존 체크포인트 러너를 그대로 감쌀 수 있다).
  3) 자식이 도는 동안 --interval 초마다 heartbeat.txt 갱신.
  4) 자식 종료 시 status.json에 state=exited·exit_code 기록 후 같은 코드로 종료.

래퍼 자신이 강제 종료되면 exited 기록이 남지 않는다 — 그 경우 워치독이
pid 사망(DEAD) 또는 심박 정체(STALLED)로 보고한다(설계 의도).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional, Sequence

from alpha_lab.runlab import contract
from alpha_lab.runlab.sealed_execution import (
    WindowsEvent,
    inherited_handle_startupinfo,
    locked_execution,
)

# 기동 실패(대상 자체를 못 띄움) 시 관례적 종료코드.
_SPAWN_FAIL_EXIT_CODE = 127


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """인자 파싱 — run_dir·target 뒤 전부를 대상 인자로 넘긴다(REMAINDER)."""
    ap = argparse.ArgumentParser(
        prog="python -I -S <absolute bootstrap.py> child-wrap",
        description="대상 스크립트를 감싸 심박·종료코드를 run_dir에 기록한다")
    ap.add_argument("--interval", type=float, default=5.0,
                    help="심박 갱신 주기(초, 기본 5)")
    ap.add_argument("--repo-root", required=True, help="canonical repository root")
    ap.add_argument("--receipt", required=True, help="canonical schema-v2 receipt")
    ap.add_argument("--claim", required=True, help="canonical schema-v2 claim")
    ap.add_argument("--stage-root", required=True, help="manifest-only stage root")
    ap.add_argument("--wrapper-ready-handle", default=None)
    ap.add_argument("--parent-release-handle", default=None)
    ap.add_argument("run_dir", help="계약 파일 디렉토리")
    ap.add_argument("target", help="대상 파이썬 스크립트 경로")
    ap.add_argument("target_args", nargs=argparse.REMAINDER,
                    help="대상 스크립트에 그대로 전달할 인자")
    return ap.parse_args(argv)


def _watch_child(proc: subprocess.Popen, run_dir: Path, interval: float) -> int:
    """자식 종료까지 폴링하며 매 주기 심박을 갱신하고 종료코드를 돌려준다."""
    interval = max(0.05, interval)  # 0/음수 방어 — busy loop 금지.
    while True:
        rc = proc.poll()
        contract.touch_heartbeat(run_dir)
        if rc is not None:
            return rc
        time.sleep(interval)


def _run(run_dir: Path, target: str, target_args: Sequence[str],
         interval: float, *, repo_root: str | Path, receipt: str | Path,
         claim: str | Path, stage_root: str | Path,
         wrapper_ready_handle=None, parent_release_handle=None) -> int:
    """Launch only after locked parent release and target bootstrap acknowledgement."""
    contract.write_pid(run_dir, os.getpid())
    started = contract.utc_now_iso()
    wrapper_ready = WindowsEvent.inherited(wrapper_ready_handle)
    parent_release = WindowsEvent.inherited(parent_release_handle)
    with locked_execution(repo_root, receipt, claim, stage_root, target) as evidence:
        if wrapper_ready is not None:
            wrapper_ready.set()
            if parent_release is None or not parent_release.wait(15_000):
                raise RuntimeError("parent did not release locked wrapper")
        bootstrap = Path(__file__).resolve().with_name("bootstrap.py")
        base = {"pid": os.getpid(), "target": str(target),
                "target_args": list(target_args), "started_utc": started,
                "interval_sec": interval}
        with WindowsEvent.create() as target_ready, open(
            run_dir / contract.LOG_FILE, "ab"
        ) as log:
            cmd = [sys.executable, "-I", "-S", str(bootstrap), "target",
                   "--repo-root", str(evidence.repo_root), "--receipt",
                   str(evidence.receipt_path), "--claim", str(evidence.claim_path),
                   "--stage-root", str(Path(stage_root).resolve()),
                   "--target-ready-handle", str(target_ready.handle), str(target),
                   *target_args]
            try:
                proc = subprocess.Popen(
                    cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                    close_fds=True,
                    startupinfo=inherited_handle_startupinfo((target_ready.handle,)))
            except OSError as err:
                contract.write_status(run_dir, contract.STATE_EXITED,
                                      exit_code=_SPAWN_FAIL_EXIT_CODE,
                                      error=f"대상 기동 실패: {err}", **base)
                return _SPAWN_FAIL_EXIT_CODE
            if not target_ready.wait(15_000):
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired as exc:
                    raise RuntimeError(
                        "target acknowledgement cleanup did not confirm exit"
                    ) from exc
                raise RuntimeError("target did not acknowledge locked bootstrap")
            contract.touch_heartbeat(run_dir)
            contract.write_status(run_dir, contract.STATE_RUNNING,
                                  child_pid=proc.pid, **base)
            try:
                rc = _watch_child(proc, run_dir, interval)
            except Exception as err:
                polled = proc.poll()
                if polled is None:
                    contract.write_status(run_dir, contract.STATE_WRAPPER_ERROR,
                                          child_pid=proc.pid,
                                          error=f"래퍼 감시 오류(자식 생존): {err!r}",
                                          **base)
                    return 1
                rc = polled
    contract.write_status(run_dir, contract.STATE_EXITED, exit_code=rc,
                          child_pid=proc.pid, ended_utc=contract.utc_now_iso(),
                          **base)
    try:
        contract.touch_heartbeat(run_dir)
    except OSError:
        pass
    return rc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 진입점 — 예기치 못한 래퍼 내부 오류도 status.json에 남긴다."""
    args = _parse_args(argv)
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        return _run(
            run_dir, args.target, args.target_args, args.interval,
            repo_root=args.repo_root, receipt=args.receipt, claim=args.claim,
            stage_root=args.stage_root,
            wrapper_ready_handle=args.wrapper_ready_handle,
            parent_release_handle=args.parent_release_handle)
    except Exception as err:  # noqa: BLE001 — 마지막 안전망: 기록 후 실패 종료.
        try:
            # 직전 status의 child_pid를 보존한다 — 전체 교체로 잃으면 살아 있는
            # 자식을 추적·정리할 수단이 사라진다(검증 지적). 자식 생존이 확인되면
            # exited(거짓 종료) 대신 wrapper_error로 남긴다.
            prior = contract.read_status(run_dir) or {}
            child_pid = prior.get("child_pid")
            from alpha_lab.runlab.watchdog import check_pid_alive
            if child_pid and check_pid_alive(int(child_pid)):
                contract.write_status(run_dir, contract.STATE_WRAPPER_ERROR,
                                      child_pid=child_pid,
                                      error=f"래퍼 내부 오류(자식 생존): {err!r}")
            else:
                contract.write_status(run_dir, contract.STATE_EXITED,
                                      exit_code=1, child_pid=child_pid,
                                      error=f"래퍼 내부 오류: {err!r}")
        except OSError:
            pass  # 기록조차 불가 — 워치독이 DEAD/STALLED로 잡는다.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
