"""runlab 실행 계약 — run_dir 상태 파일 4종의 단일 정의(WBS v3 P1-4, 백로그 A18).

계약 파일(모두 run_dir 바로 아래):
  pid.txt        분리 기동된 래퍼 프로세스 PID(정수 텍스트 1줄).
  heartbeat.txt  래퍼가 주기 갱신하는 심박. 내용은 사람 확인용 UTC ISO 문자열이고,
                 정체(stall) 판정은 파일 mtime으로 한다.
  status.json    상태 기계 launched → running → exited(+exit_code).
  log.txt        래퍼·대상 스크립트의 stdout/stderr 통합 로그(append 전용).

원칙: 표준 라이브러리만 사용(psutil 등 외부 의존 금지). status.json은
임시파일+os.replace 원자 교체로 쓴다 — 워치독이 반쯤 쓰인 json을 읽지 않게.
Windows에서 읽는 쪽이 파일을 잡고 있으면 os.replace가 공유 위반으로 실패할 수
있어 짧은 재시도를 둔다(실측 대비 보험).
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

PID_FILE = "pid.txt"
HEARTBEAT_FILE = "heartbeat.txt"
STATUS_FILE = "status.json"
LOG_FILE = "log.txt"

STATE_LAUNCHED = "launched"
STATE_RUNNING = "running"
STATE_EXITED = "exited"
# 래퍼 자신이 IO 장애 등으로 죽되 자식 배치는 생존 중일 수 있는 상태 —
# exited(거짓 종료)로 위장하지 않기 위한 별도 상태(검증 지적 반영).
STATE_WRAPPER_ERROR = "wrapper_error"

# 원자 교체/읽기 재시도 폭 — 워치독과의 순간 충돌만 흡수하면 충분하다.
_IO_RETRY = 5
_IO_RETRY_SLEEP_SEC = 0.05


def utc_now_iso() -> str:
    """UTC 현재 시각 ISO 문자열(초 단위)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    """임시 파일에 쓴 뒤 os.replace로 원자 교체한다(짧은 재시도 포함)."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    last_err: Optional[OSError] = None
    for _ in range(_IO_RETRY):
        try:
            os.replace(tmp, path)
            return
        except OSError as err:  # 읽는 쪽이 잡고 있는 순간 — 잠깐 뒤 재시도.
            last_err = err
            time.sleep(_IO_RETRY_SLEEP_SEC)
    raise last_err  # type: ignore[misc]


def write_status(run_dir, state: str, **fields: Any) -> Dict[str, Any]:
    """status.json 갱신 — state·utc에 부가 필드를 얹은 전체 페이로드를 쓴다."""
    payload: Dict[str, Any] = {"state": state, "utc": utc_now_iso(), **fields}
    write_json_atomic(Path(run_dir) / STATUS_FILE, payload)
    return payload


def read_status(run_dir) -> Optional[Dict[str, Any]]:
    """status.json을 읽는다. 없음/파손/순간 잠금이면 None."""
    path = Path(run_dir) / STATUS_FILE
    for _ in range(_IO_RETRY):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except ValueError:
            return None  # 파손 — 워치독이 MISSING으로 보고한다.
        except OSError:
            time.sleep(_IO_RETRY_SLEEP_SEC)  # 교체 순간과 겹침 — 재시도.
    return None


def touch_heartbeat(run_dir) -> None:
    """심박 갱신 — 판정은 mtime, 내용은 디버깅용 타임스탬프.

    초당~수초당 반복 호출되는 유일한 계약 파일이라 일시 잠금(AV·인덱서) 1회에
    래퍼가 즉사하지 않도록 status.json과 동일한 짧은 재시도를 둔다.
    """
    path = Path(run_dir) / HEARTBEAT_FILE
    last_err: Optional[OSError] = None
    for _ in range(_IO_RETRY):
        try:
            path.write_text(utc_now_iso() + "\n", encoding="utf-8")
            return
        except OSError as err:
            last_err = err
            time.sleep(_IO_RETRY_SLEEP_SEC)
    raise last_err  # type: ignore[misc]


def write_pid(run_dir, pid: int) -> None:
    """pid.txt 기록(정수 1줄)."""
    (Path(run_dir) / PID_FILE).write_text(f"{pid}\n", encoding="utf-8")


def read_pid(run_dir) -> Optional[int]:
    """pid.txt를 읽는다. 없거나 정수가 아니면 None."""
    try:
        raw = (Path(run_dir) / PID_FILE).read_text(encoding="utf-8").strip()
        return int(raw)
    except (OSError, ValueError):
        return None
