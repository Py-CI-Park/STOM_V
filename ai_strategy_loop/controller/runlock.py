"""P6 — cross-process single-writer lock (동시 루프 차단).

CLI(`python -m ai_strategy_loop.controller.loop`)와 GUI(대시보드 start 제어)는
같은 `current_state.json`/`loop_runs.db`에 쓴다. 두 진입점이 동시에 루프를
돌리면 라이브 상태/세대 기록이 서로를 덮어쓴다(Critic M3). 이를 막기 위해
**PID 기록 lockfile** 기반의 단일 writer 락을 둔다.

설계 원칙(SIMPLICITY + 안전):
  - 표준 파일 하나(`ai_strategy_loop/state/loop.lock`)에 pid+timestamp를 기록한다.
    OS advisory 락(fcntl/msvcrt)은 플랫폼 분기가 커서 쓰지 않는다. 이 락은
    "협조적(cooperative)" — 두 STOM 루프 진입점만 이 규약을 따르면 충분하다.
  - **stale 복구 필수**: 크래시로 락 파일이 남아도 영구 잔존하면 안 된다.
    기록된 pid가 더 이상 살아있지 않거나(프로세스 종료), timestamp가 너무
    오래되면(STALE_AFTER_SEC) stale로 보고 회수(acquire가 덮어쓴다).
  - 무예외 계약에 가깝게: 락 파일 I/O 실패는 락을 못 잡은 것으로 표준화한다.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

# 패키지 루트(.../ai_strategy_loop) 기준 표준 lockfile 경로.
#   state/ 디렉토리는 .gitignore 로 런타임 산출물 취급(추적 제외)이다.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_STATE_DIR = _PACKAGE_DIR / "state"
LOCK_FILE = _STATE_DIR / "loop.lock"

# 이 시간(초)보다 오래된 락은 timestamp 기준으로도 stale로 본다.
#   pid 생존 확인이 1차이고, 이건 pid 재사용(다른 프로세스가 같은 pid를 점유)
#   같은 드문 경우의 2차 안전장치다. 한 세대(백테 1회)가 수 분이 걸릴 수 있으므로
#   넉넉히 둔다 — 락 갱신(refresh) 없이도 정상 루프를 stale로 오인하지 않게.
STALE_AFTER_SEC = 6 * 60 * 60  # 6시간


def _pid_alive(pid: int) -> bool:
    """pid가 살아있는 프로세스인지 확인한다(플랫폼 무관, 보수적).

    - POSIX: os.kill(pid, 0) — 권한 오류(EPERM)는 '살아있음'으로 본다.
    - Windows: os.kill이 signal 0을 지원하지 않으므로 OpenProcess로 확인한다.
    판정 불가(예외)면 보수적으로 True(살아있다고 가정)를 돌려 멀쩡한 락을 함부로
    회수하지 않는다 — stale 오판으로 동시 실행을 허용하는 것보다 안전하다.
    """
    if pid <= 0:
        return False
    if os.name == "nt":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # 다른 사용자 소유 프로세스 — 존재하긴 한다.
        return True
    except OSError:
        return True
    return True


def _pid_alive_windows(pid: int) -> bool:
    """Windows에서 pid 생존 확인 (OpenProcess + GetExitCodeProcess)."""
    try:
        import ctypes  # noqa: PLC0415

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong(0)
            ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            if not ok:
                return True  # 판정 불가 — 보수적으로 살아있다고 본다.
            return exit_code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    except Exception:  # noqa: BLE001 - 판정 실패는 보수적으로 살아있음.
        return True


def _read_lock(path: Path) -> Optional[Dict[str, Any]]:
    """lockfile을 읽어 {pid, timestamp, ...} dict로 돌린다. 없거나 손상이면 None."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _is_stale(info: Dict[str, Any]) -> bool:
    """기록된 락 정보가 stale(회수 가능)인지 판정한다.

    stale 조건(둘 중 하나):
      1) 기록된 pid가 더 이상 살아있지 않음(크래시/정상 종료 후 잔존).
      2) timestamp가 STALE_AFTER_SEC 보다 오래됨(pid 재사용 등 2차 안전장치).
    pid가 살아있고 시간도 최근이면 stale 아님(=유효한 락).
    """
    try:
        pid = int(info.get("pid", -1))
    except (TypeError, ValueError):
        return True
    if not _pid_alive(pid):
        return True
    try:
        ts = float(info.get("timestamp", 0.0))
    except (TypeError, ValueError):
        return True
    if (time.time() - ts) > STALE_AFTER_SEC:
        return True
    return False


def is_locked(path: Optional[str] = None) -> bool:
    """현재 유효한(살아있는·최근) 락이 잡혀 있는지 확인한다.

    stale 락(크래시 잔존)은 잡혀 있지 않은 것으로 본다 — acquire가 회수한다.
    """
    target = Path(path or LOCK_FILE)
    info = _read_lock(target)
    if info is None:
        return False
    return not _is_stale(info)


def acquire_run_lock(path: Optional[str] = None) -> Dict[str, Any]:
    """단일 writer 락을 잡는다. 이미 유효한 락이 있으면 거부한다.

    stale 락(기록 pid 사망 또는 timestamp 만료)은 회수하고 새로 잡는다.

    Returns:
        {"status": "ok", "pid", "lock_file"} — 락 획득(또는 stale 회수 후 획득).
        {"status": "error", "message", "holder_pid"} — 다른 살아있는 루프가 보유 중.
    """
    target = Path(path or LOCK_FILE)
    existing = _read_lock(target)
    if existing is not None and not _is_stale(existing):
        return {
            "status": "error",
            "message": "다른 루프가 실행 중입니다(단일 writer 락 보유). 동시 실행 차단.",
            "holder_pid": existing.get("pid"),
            "lock_file": str(target),
        }

    # 없거나 stale → 회수하고 새 락을 atomic write 한다(.tmp → os.replace).
    payload = {
        "pid": os.getpid(),
        "timestamp": time.time(),
        "lock_file": str(target),
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(target.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp, target)
    except OSError as exc:
        return {
            "status": "error",
            "message": f"락 파일 기록 실패: {exc}",
            "lock_file": str(target),
        }
    return {"status": "ok", "pid": payload["pid"], "lock_file": str(target)}


def release_run_lock(path: Optional[str] = None) -> bool:
    """이 프로세스가 잡은 락을 해제한다(lockfile 제거).

    소유권 확인: 기록된 pid가 내 pid일 때만 지운다(다른 루프의 락을 실수로
    지우지 않게). 단, stale 락(사망 pid)은 정리 차원에서 함께 회수한다.
    파일이 없으면 조용히 False. 해제했으면 True.
    """
    target = Path(path or LOCK_FILE)
    info = _read_lock(target)
    if info is None:
        return False
    try:
        holder = int(info.get("pid", -1))
    except (TypeError, ValueError):
        holder = -1
    # 내 락이거나, 이미 stale(사망 pid)이면 회수한다.
    if holder == os.getpid() or _is_stale(info):
        try:
            target.unlink()
            return True
        except OSError:
            return False
    return False
