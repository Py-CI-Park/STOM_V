"""Windows 세션 독립 배치 기동기 — '배치가 세션과 함께 죽는 문제'의 구조적 제거.

배경(핸드오프 v3 §7): 배치가 에이전트 세션 종료와 함께 사망한 실측 2회.
원리: 대상 스크립트를 직접 띄우지 않고 심박·상태 기록 래퍼(child_wrap)를
DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP 플래그로 분리 기동한다.
가능하면 CREATE_BREAKAWAY_FROM_JOB까지 얹어 job object 동반 종료도 탈출하고,
job이 breakaway를 불허하면 기본 조합으로 자동 재시도한다.
stdout/stderr는 run_dir/log.txt로만 흐른다(콘솔 핸들 없음, stdin=DEVNULL).

실행 계약(run_dir): pid.txt / heartbeat.txt / status.json(launched|running|
exited+exit_code) / log.txt — 정의는 contract.py.
감시는 보고 전용 워치독으로만 한다(자동 재시작 금지):
    python scripts/batch_watch.py <run_dir>

실사용 예 — D5(D9 전이 온셋) 측정 437일 배치를 세션 독립으로 기동
(PowerShell 한 줄, 2026-07-12 실전 완주 실증 — exit 0):
    $repo = (Resolve-Path .).Path; $bootstrap = (Resolve-Path alpha_lab/runlab/bootstrap.py).Path; $env:STOM_ALLOW_MINIMAL_SETTING="1"; python -I -S $bootstrap detached-runner --receipt "$repo/receipts/<id>.json" --claim "$repo/claims/<id>.json" docs/research/condition_research/research_runs/alpha_restart_20260710/d5_d9/run_ctl/run1 scripts/d5_d9_measure.py -- --phase all
receipt와 claim은 필수이며 run_dir/target보다 앞에 둔다. target은 봉인된
dependency_roots의 정확한 항목만 허용되고, 신뢰된 소스 전용 러너가
manifest-only 잠금 stage에서 비공개 이벤트 핸드오프로 실행한다. 임의
--python-exe는 지원하지 않는다. 옵션 --interval/--cwd는 run_dir 앞에 두고,
대상 스크립트 인자는 '--' 뒤에 둔다. 대상 스크립트는 무수정 그대로 감싼다
— 체크포인트 러너 호환.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from alpha_lab.runlab import contract
from alpha_lab.runlab.sealed_execution import (
    WindowsEvent,
    WindowsJob,
    inherited_handle_startupinfo,
    locked_execution,
    stage_execution,
)

_DEFAULT_HEARTBEAT_SEC = 5.0
_HANDSHAKE_TIMEOUT_SEC = 15.0


@dataclass(frozen=True)
class LaunchResult:
    """분리 기동 결과 — pid와 계약 파일 경로 묶음."""

    pid: int
    run_dir: Path
    log_path: Path
    status_path: Path
    pid_path: Path
    heartbeat_path: Path
    cmd: Tuple[str, ...]
    creationflags: int


def _repo_root() -> Path:
    """워크트리 루트(ROOT) — 이 파일 기준 2단계 상위."""
    return Path(__file__).resolve().parents[2]


def _prepare_env(env: Optional[Dict[str, str]]) -> Dict[str, str]:
    """자식 환경에서 caller PYTHONPATH를 제거한다(-I/-S bootstrap이 경로를 봉인)."""
    merged = dict(os.environ if env is None else env)
    merged.pop("PYTHONPATH", None)
    return merged


def _bootstrap_path() -> Path:
    """추적된 절대 bootstrap 경로."""
    return _repo_root() / "alpha_lab" / "runlab" / "bootstrap.py"


def _wrapper_cmd(run_dir: Path, target: Path, target_args: Sequence[str],
                 interval: float, *, repo_root: Path, receipt: Path,
                 claim: Path, stage_root: Path, wrapper_ready: WindowsEvent,
                 parent_release: WindowsEvent) -> Tuple[str, ...]:
    """Build the evidence-bound child-wrap command with this interpreter only."""
    return (sys.executable, "-I", "-S", str(_bootstrap_path()), "child-wrap",
            "--repo-root", str(repo_root), "--receipt", str(receipt),
            "--claim", str(claim), "--stage-root", str(stage_root),
            "--wrapper-ready-handle", str(wrapper_ready.handle),
            "--parent-release-handle", str(parent_release.handle),
            "--interval", str(interval), str(run_dir), str(target),
            *[str(a) for a in target_args])


def _popen_detached(cmd: Sequence[str], log_path: Path, cwd: Path,
                    env: Dict[str, str], handles: tuple[int, ...]) -> Tuple[subprocess.Popen, int]:
    """Start the detached wrapper while inheriting only its private handoff events."""
    base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    candidates = (base | subprocess.CREATE_BREAKAWAY_FROM_JOB, base)
    last_err: Optional[OSError] = None
    with open(log_path, "ab") as log:
        for flags in candidates:
            try:
                proc = subprocess.Popen(
                    list(cmd), cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                    stdout=log, stderr=subprocess.STDOUT, creationflags=flags,
                    close_fds=True, startupinfo=inherited_handle_startupinfo(handles))
                return proc, flags
            except OSError as err:
                last_err = err
    raise last_err  # type: ignore[misc]

def _wait_for_child_handoff(wrapper_ready: WindowsEvent) -> None:
    """Wait for the wrapper's private post-lock acknowledgement event."""
    if not wrapper_ready.wait(int(_HANDSHAKE_TIMEOUT_SEC * 1000)):
        raise RuntimeError("child wrapper did not publish locked handoff")


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    """Terminate the wrapper before release; it cannot yet have spawned a target."""
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("wrapper did not exit after pre-release cleanup") from exc



def launch_detached(run_dir, target, target_args: Sequence[str] = (), *,
                    receipt, claim, cwd=None, env: Optional[Dict[str, str]] = None,
                    heartbeat_interval: float = _DEFAULT_HEARTBEAT_SEC,
                    ) -> LaunchResult:
    """대상 스크립트를 세션 독립 래퍼로 분리 기동하고 즉시 반환한다.

    run_dir에 계약 파일을 남기며, 이후 상태는 scripts/batch_watch.py로 본다.
    실패 시 status.json에 error를 남기고 예외를 그대로 올린다.
    """
    if os.name != "nt":
        raise RuntimeError("detached_runner는 Windows 전용(DETACHED_PROCESS 계약)")
    run_path = Path(run_dir).resolve()
    run_path.mkdir(parents=True, exist_ok=True)
    work_dir = Path(cwd).resolve() if cwd else _repo_root()
    heartbeat_path = run_path / contract.HEARTBEAT_FILE
    try:
        heartbeat_path.unlink()
    except FileNotFoundError:
        pass
    with locked_execution(_repo_root(), receipt, claim) as evidence:
        stage_root, target_path = stage_execution(run_path, evidence, target)
        with locked_execution(
            evidence.repo_root, evidence.receipt_path, evidence.claim_path,
            stage_root, target_path,
        ) as locked:
            with (WindowsEvent.create() as wrapper_ready,
                  WindowsEvent.create() as parent_release,
                  WindowsJob() as job):
                cmd = _wrapper_cmd(
                    run_path, target_path, target_args, heartbeat_interval,
                    repo_root=locked.repo_root, receipt=locked.receipt_path,
                    claim=locked.claim_path, stage_root=stage_root,
                    wrapper_ready=wrapper_ready, parent_release=parent_release)
                log_path = run_path / contract.LOG_FILE
                contract.write_status(run_path, contract.STATE_LAUNCHED,
                                      target=str(target_path), cwd=str(work_dir), cmd=list(cmd))
                proc = None
                assigned = False
                try:
                    proc, flags = _popen_detached(
                        cmd, log_path, work_dir, _prepare_env(env),
                        (wrapper_ready.handle, parent_release.handle))
                    job.assign(proc._handle)
                    assigned = True
                    _wait_for_child_handoff(wrapper_ready)
                    parent_release.set()
                except Exception as err:
                    if proc is not None:
                        if assigned:
                            job.terminate()
                            try:
                                proc.wait(timeout=15)
                            except subprocess.TimeoutExpired as cleanup_error:
                                raise RuntimeError(
                                    "job cleanup did not confirm wrapper exit"
                                ) from cleanup_error
                        else:
                            _terminate_process_tree(proc)
                    contract.write_status(run_path, contract.STATE_LAUNCHED,
                                          target=str(target_path), cwd=str(work_dir),
                                          cmd=list(cmd), error=f"기동 실패: {err}")
                    raise
    contract.write_pid(run_path, proc.pid)
    return LaunchResult(
        pid=proc.pid, run_dir=run_path, log_path=log_path,
        status_path=run_path / contract.STATUS_FILE,
        pid_path=run_path / contract.PID_FILE,
        heartbeat_path=heartbeat_path, cmd=tuple(cmd), creationflags=flags)


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """CLI 인자 — 옵션은 run_dir 앞, 대상 인자는 '--' 뒤(REMAINDER)."""
    ap = argparse.ArgumentParser(
        prog="python -I -S <absolute bootstrap.py> detached-runner",
        description="배치를 세션 독립(detached)으로 기동한다 — 보고는 batch_watch.py")
    ap.add_argument("--interval", type=float, default=_DEFAULT_HEARTBEAT_SEC,
                    help="심박 갱신 주기(초, 기본 5)")
    ap.add_argument("--cwd", default=None, help="자식 작업 디렉토리(기본 ROOT)")
    ap.add_argument("--receipt", required=True,
                    help="canonical schema-v2 receipt JSON path")
    ap.add_argument("--claim", required=True,
                    help="canonical schema-v2 claim JSON path")
    ap.add_argument("run_dir", help="계약 파일이 놓일 실행 디렉토리")
    ap.add_argument("target", help="대상 파이썬 스크립트 경로(무수정 래핑)")
    ap.add_argument("target_args", nargs=argparse.REMAINDER,
                    help="대상 스크립트 인자('--' 뒤에 배치 권장)")
    return ap.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI 진입점 — 기동 결과를 json 한 줄로 출력하고 즉시 종료한다."""
    args = _parse_args(argv)
    result = launch_detached(
        args.run_dir, args.target, args.target_args,
        receipt=args.receipt, claim=args.claim,
        cwd=args.cwd,
        heartbeat_interval=args.interval)
    print(json.dumps({
        "pid": result.pid,
        "run_dir": str(result.run_dir),
        "log": str(result.log_path),
        "status": str(result.status_path),
        "watch": f"python scripts/batch_watch.py {result.run_dir}",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
