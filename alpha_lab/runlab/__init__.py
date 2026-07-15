"""runlab — 분리형 배치 러너 + 보고 전용 워치독 (WBS v3 P1-4, 백로그 A18·A19).

해결하는 문제: 장시간 배치가 에이전트 세션 종료와 함께 죽는 사고(실측 2회,
핸드오프 v3 §7). 배치를 세션에서 분리(DETACHED_PROCESS)해 구조적으로 제거한다.

구성:
  detached_runner  Windows 세션 독립 기동기(창구). CLI:
                   python -P -S -m alpha_lab.runlab.detached_runner <run_dir> <스크립트> -- [인자...]
  child_wrap       대상 스크립트 무수정 래퍼 — 심박 갱신+종료코드 기록.
  watchdog         보고 전용 판정(RUNNING/STALLED/DEAD/EXITED/MISSING).
                   자동 재시작 금지 — 재기동 결정은 사람/메인 세션 몫.
  contract         run_dir 계약 파일 4종(pid/heartbeat/status/log) 단일 정의.
  scripts/batch_watch.py  워치독 CLI(ROOT/scripts).

측정 없음 — 이 패키지는 그릇/도구만 제공하며 시장 데이터에 접근하지 않는다.
"""
from __future__ import annotations

from alpha_lab.runlab.contract import (
    HEARTBEAT_FILE,
    LOG_FILE,
    PID_FILE,
    STATE_EXITED,
    STATE_LAUNCHED,
    STATE_RUNNING,
    STATUS_FILE,
)
from alpha_lab.runlab.watchdog import (
    DEFAULT_STALL_SEC,
    RunReport,
    check_pid_alive,
    format_report,
    heartbeat_age_sec,
    inspect_run,
    wait_for_exited,
)

# detached_runner 재수출은 지연 임포트(PEP 562) — `python -m ...detached_runner`
# 실행 시 "found in sys.modules" RuntimeWarning을 막는다.
_LAZY_DETACHED = ("LaunchResult", "launch_detached")


def __getattr__(name: str):
    if name in _LAZY_DETACHED:
        from alpha_lab.runlab import detached_runner
        return getattr(detached_runner, name)
    raise AttributeError(f"module 'alpha_lab.runlab' has no attribute {name!r}")

__all__ = [
    "HEARTBEAT_FILE",
    "LOG_FILE",
    "PID_FILE",
    "STATUS_FILE",
    "STATE_LAUNCHED",
    "STATE_RUNNING",
    "STATE_EXITED",
    "LaunchResult",
    "launch_detached",
    "DEFAULT_STALL_SEC",
    "RunReport",
    "check_pid_alive",
    "format_report",
    "heartbeat_age_sec",
    "inspect_run",
    "wait_for_exited",
]
