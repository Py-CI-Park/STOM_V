"""보고 전용 워치독 — run_dir 상태 판정(자동 재시작 없음·금지, 백로그 A19).

판정 규칙(inspect_run):
  MISSING   status.json 없음/파손 — 계약 미개시 또는 디렉토리 오지정.
  EXITED    state=exited — exit_code 함께 보고(0 정상, 그 외 실패).
  RUNNING   state=launched|running + pid 생존 + 심박 나이 ≤ 임계.
  STALLED   pid는 살아 있으나 심박 나이 > 임계 — 행 걸림(hang) 의심.
  DEAD      state가 exited가 아닌데 pid 사망 — 세션 동반사/강제 종료 서명.

pid 생존은 ctypes OpenProcess + GetExitCodeProcess(STILL_ACTIVE)로 확인한다
(psutil 의존 금지). 심박 나이는 heartbeat.txt mtime 기준이며, 기동 직후
심박 미생성 구간은 status.json mtime으로 대체해 오탐(STALLED)을 막는다.
"""
from __future__ import annotations

import ctypes
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from alpha_lab.runlab import contract

# 판정 상수 — batch_watch.py와 테스트가 공유한다.
VERDICT_RUNNING = "RUNNING"
VERDICT_STALLED = "STALLED"
VERDICT_DEAD = "DEAD"
VERDICT_EXITED = "EXITED"
VERDICT_MISSING = "MISSING"
# 래퍼는 죽었는데 자식 배치는 살아 있을 수 있는 상태(child_wrap 기록) — 경보.
VERDICT_WRAPPER_ERROR = "WRAPPER_ERROR"

DEFAULT_STALL_SEC = 180.0

# Win32 상수.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259
_ERROR_ACCESS_DENIED = 5

if os.name == "nt":
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.OpenProcess.restype = ctypes.c_void_p
    _kernel32.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int,
                                      ctypes.c_uint32)
    _kernel32.GetExitCodeProcess.restype = ctypes.c_int
    _kernel32.GetExitCodeProcess.argtypes = (ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_uint32))
    _kernel32.CloseHandle.restype = ctypes.c_int
    _kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)


@dataclass(frozen=True)
class RunReport:
    """단일 run_dir 검사 결과(보고 전용)."""

    run_dir: str
    verdict: str
    state: Optional[str]
    pid: Optional[int]
    pid_alive: bool
    exit_code: Optional[int]
    heartbeat_age_sec: Optional[float]
    detail: str


def check_pid_alive(pid: Optional[int]) -> bool:
    """PID 생존 확인 — Windows는 ctypes OpenProcess, 그 외는 os.kill(pid, 0)."""
    if pid is None or pid <= 0:
        return False
    if os.name != "nt":  # 이식 대비 폴백(현 운용 환경은 Windows).
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
    if not handle:
        # 접근 거부 = 프로세스 존재(권한만 없음), 그 외 = 부재.
        return ctypes.get_last_error() == _ERROR_ACCESS_DENIED
    try:
        code = ctypes.c_uint32(0)
        if not _kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == _STILL_ACTIVE
    finally:
        _kernel32.CloseHandle(handle)


def heartbeat_age_sec(run_dir, now: Optional[float] = None) -> Optional[float]:
    """심박 나이(초). 심박 미생성 시 status.json mtime 대체, 둘 다 없으면 None."""
    base = Path(run_dir)
    for name in (contract.HEARTBEAT_FILE, contract.STATUS_FILE):
        try:
            mtime = (base / name).stat().st_mtime
            return max(0.0, (now if now is not None else time.time()) - mtime)
        except OSError:
            continue
    return None


def _verdict_live(pid_alive: bool, age: Optional[float],
                  stall_sec: float) -> str:
    """launched/running 상태의 판정 분기."""
    if not pid_alive:
        return VERDICT_DEAD
    if age is not None and age > stall_sec:
        return VERDICT_STALLED
    return VERDICT_RUNNING


def inspect_run(run_dir, stall_sec: float = DEFAULT_STALL_SEC,
                now: Optional[float] = None) -> RunReport:
    """run_dir 하나를 검사해 RunReport를 돌려준다(파일 읽기 외 부작용 없음)."""
    run_dir = str(run_dir)
    status = contract.read_status(run_dir)
    pid = contract.read_pid(run_dir)
    if pid is None and status is not None:
        pid = status.get("pid")
    if status is None:
        return RunReport(run_dir, VERDICT_MISSING, None, pid, False, None,
                         None, "status.json 없음/파손 — 계약 미개시")
    state = status.get("state")
    if state == contract.STATE_EXITED:
        rc = status.get("exit_code")
        note = "정상 종료" if rc == 0 else f"실패 종료(exit_code={rc})"
        # pid_alive를 False로 하드코딩하지 않는다 — 거짓 exited 상황에서
        # 실제 생존 중인 프로세스를 '사망'으로 위장하지 않기 위함(검증 지적).
        exited_alive = check_pid_alive(status.get("child_pid") or pid)
        if exited_alive:
            note += " ※주의: 관련 프로세스 생존 감지 — 거짓 종료 가능성 점검"
        return RunReport(run_dir, VERDICT_EXITED, state, pid, exited_alive, rc,
                         heartbeat_age_sec(run_dir, now), note)
    if state == contract.STATE_WRAPPER_ERROR:
        child_pid = status.get("child_pid")
        child_alive = check_pid_alive(child_pid)
        note = (f"래퍼 오류 — 자식(child_pid={child_pid}) "
                f"{'생존 중(수동 확인·정리 필요)' if child_alive else '사망 확인'}: "
                f"{status.get('error', '')}")
        return RunReport(run_dir, VERDICT_WRAPPER_ERROR, state, pid,
                         child_alive, None, heartbeat_age_sec(run_dir, now),
                         note)
    alive = check_pid_alive(pid)
    age = heartbeat_age_sec(run_dir, now)
    verdict = _verdict_live(alive, age, stall_sec)
    detail = {
        VERDICT_DEAD: "exited 기록 없이 pid 사망 — 세션 동반사/강제 종료 의심",
        VERDICT_STALLED: f"심박 정체 {age:.0f}s > 임계 {stall_sec:.0f}s — 행 걸림 의심"
        if age is not None else "심박 정체",
        VERDICT_RUNNING: "정상 구동 중",
    }[verdict]
    return RunReport(run_dir, verdict, state, pid, alive, None, age, detail)


def format_report(report: RunReport) -> str:
    """사람용 한 줄 요약(한국어) — batch_watch.py 출력 형식."""
    pid_txt = f"{report.pid}({'생존' if report.pid_alive else '사망'})" \
        if report.pid else "-"
    age_txt = f"{report.heartbeat_age_sec:.1f}s" \
        if report.heartbeat_age_sec is not None else "-"
    rc_txt = "-" if report.exit_code is None else str(report.exit_code)
    return (f"[{report.verdict:7s}] {Path(report.run_dir).name} | "
            f"state={report.state or '-'} pid={pid_txt} 심박={age_txt} "
            f"exit={rc_txt} | {report.detail}")


def wait_for_exited(run_dir, timeout_sec: float = 30.0,
                    poll_sec: float = 0.2) -> Optional[dict]:
    """state=exited가 될 때까지 대기(테스트·기동 직후 확인용, 보고 전용)."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        status = contract.read_status(run_dir)
        if status is not None and status.get("state") == contract.STATE_EXITED:
            return status
        time.sleep(poll_sec)
    return contract.read_status(run_dir)
