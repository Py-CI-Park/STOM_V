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
    $env:STOM_ALLOW_MINIMAL_SETTING="1"; python -P -m alpha_lab.runlab.detached_runner docs/research/condition_research/research_runs/alpha_restart_20260710/d5_d9/run_ctl/run1 scripts/d5_d9_measure.py -- --phase all
(옵션 --interval/--cwd/--python-exe는 run_dir 앞에 두고, 대상 스크립트 인자는
'--' 뒤에 둔다. 대상 스크립트는 무수정 그대로 감싼다 — 체크포인트 러너 호환.)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from alpha_lab.runlab import contract

_DEFAULT_HEARTBEAT_SEC = 5.0


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
    """Seal the wrapper's import path before it is spawned."""
    return contract.sanitize_runtime_env(env, _repo_root())



def _wrapper_cmd(run_dir: Path, target: Path, target_args: Sequence[str],
                 python_exe: Optional[str], interval: float) -> Tuple[str, ...]:
    """child_wrap을 safe-path 모드로 기동한다(대상은 절대경로)."""
    py = python_exe or sys.executable
    return (py, "-P", "-m", "alpha_lab.runlab.child_wrap",
            "--interval", str(interval), str(run_dir), str(target),
            *[str(a) for a in target_args])


def _popen_detached(cmd: Sequence[str], log_path: Path, cwd: Path,
                    env: Dict[str, str]) -> Tuple[subprocess.Popen, int]:
    """분리 플래그 후보를 순서대로 시도해 (Popen, 사용 플래그)를 돌려준다.

    1순위: DETACHED|NEW_GROUP|BREAKAWAY_FROM_JOB(세션·job 양쪽 탈출).
    2순위: DETACHED|NEW_GROUP(과제 명세 기본 조합) — job이 breakaway 불허 시.
    """
    base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    candidates = (base | subprocess.CREATE_BREAKAWAY_FROM_JOB, base)
    last_err: Optional[OSError] = None
    with open(log_path, "ab") as log:
        for flags in candidates:
            try:
                proc = subprocess.Popen(
                    list(cmd), cwd=str(cwd), env=env,
                    stdin=subprocess.DEVNULL, stdout=log,
                    stderr=subprocess.STDOUT, creationflags=flags)
                return proc, flags
            except OSError as err:  # breakaway 불허 등 — 다음 조합으로.
                last_err = err
    raise last_err  # type: ignore[misc]


def launch_detached(run_dir, target, target_args: Sequence[str] = (), *,
                    python_exe: Optional[str] = None, cwd=None,
                    env: Optional[Dict[str, str]] = None,
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
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = (work_dir / target_path).resolve()
    cmd = _wrapper_cmd(run_path, target_path, target_args, python_exe,
                       heartbeat_interval)
    log_path = run_path / contract.LOG_FILE
    # 기동 직전 launched 기록 — 래퍼의 running이 항상 이후에 온다.
    contract.write_status(run_path, contract.STATE_LAUNCHED,
                          target=str(target_path), cwd=str(work_dir),
                          cmd=list(cmd))
    try:
        child_env = _prepare_env(env)
    except ValueError as err:
        contract.write_status(run_path, contract.STATE_LAUNCHED,
                              target=str(target_path), cwd=str(work_dir),
                              cmd=list(cmd), error=f"환경 검증 실패: {err}")
        raise
    try:
        proc, flags = _popen_detached(cmd, log_path, work_dir, child_env)
    except OSError as err:
        contract.write_status(run_path, contract.STATE_LAUNCHED,
                              target=str(target_path), cwd=str(work_dir),
                              cmd=list(cmd), error=f"기동 실패: {err}")
        raise

    contract.write_pid(run_path, proc.pid)
    return LaunchResult(
        pid=proc.pid, run_dir=run_path, log_path=log_path,
        status_path=run_path / contract.STATUS_FILE,
        pid_path=run_path / contract.PID_FILE,
        heartbeat_path=run_path / contract.HEARTBEAT_FILE,
        cmd=tuple(cmd), creationflags=flags)


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    """CLI 인자 — 옵션은 run_dir 앞, 대상 인자는 '--' 뒤(REMAINDER)."""
    ap = argparse.ArgumentParser(
        prog="python -P -m alpha_lab.runlab.detached_runner",
        description="배치를 세션 독립(detached)으로 기동한다 — 보고는 batch_watch.py")
    ap.add_argument("--interval", type=float, default=_DEFAULT_HEARTBEAT_SEC,
                    help="심박 갱신 주기(초, 기본 5)")
    ap.add_argument("--cwd", default=None, help="자식 작업 디렉토리(기본 ROOT)")
    ap.add_argument("--python-exe", default=None,
                    help="자식 파이썬 실행 파일(기본 현재 인터프리터)")
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
        python_exe=args.python_exe, cwd=args.cwd,
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
