"""P6 — cross-process single-writer 락 단위 테스트 (lockfile 기반).

검증:
  (a) acquire → 락 파일 생성 + is_locked True.
  (b) 락 보유 중 두 번째 acquire는 거부(holder_pid 노출).
  (c) release 후 다시 acquire 가능.
  (d) stale 복구: 죽은 pid가 기록된 락은 stale로 보고 회수(재획득 성공).
  (e) stale 복구: timestamp 만료 락도 회수.
  (f) release 소유권: 다른 살아있는 pid의 락은 함부로 지우지 않는다.

실루프/네트워크 없음. lockfile 경로는 tmp_path로 격리한다(운영 파일 미접촉).
"""

import json
import os
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import runlock  # noqa: E402


def _lock(tmp_path):
    return str(tmp_path / "loop.lock")


def test_acquire_creates_lock_and_is_locked(tmp_path):
    """(a) acquire 성공 → 파일 생성 + is_locked True + 내 pid 기록."""
    path = _lock(tmp_path)
    res = runlock.acquire_run_lock(path)
    assert res["status"] == "ok"
    assert res["pid"] == os.getpid()
    assert os.path.isfile(path)
    assert runlock.is_locked(path) is True


def test_second_acquire_is_rejected_while_held(tmp_path):
    """(b) 살아있는 락 보유 중 두 번째 acquire는 거부된다."""
    path = _lock(tmp_path)
    first = runlock.acquire_run_lock(path)
    assert first["status"] == "ok"

    second = runlock.acquire_run_lock(path)
    assert second["status"] == "error"
    assert "실행 중" in second["message"]
    # 현재 보유 pid(=이 프로세스)를 노출한다.
    assert second["holder_pid"] == os.getpid()


def test_release_then_reacquire(tmp_path):
    """(c) release 후 락 파일이 사라지고 다시 acquire 가능하다."""
    path = _lock(tmp_path)
    runlock.acquire_run_lock(path)
    assert runlock.release_run_lock(path) is True
    assert not os.path.isfile(path)
    assert runlock.is_locked(path) is False

    again = runlock.acquire_run_lock(path)
    assert again["status"] == "ok"


def test_stale_recovery_when_pid_dead(tmp_path, monkeypatch):
    """(d) 죽은 pid가 기록된 락은 stale → 회수하고 재획득 성공."""
    path = _lock(tmp_path)
    # 죽은 pid(존재하지 않는 큰 pid)로 락 파일을 직접 심는다.
    dead_pid = 2_000_000_000
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pid": dead_pid, "timestamp": time.time()}, fh)

    # _pid_alive가 죽은 pid에 False를 돌리도록 강제(플랫폼 무관 결정론).
    monkeypatch.setattr(runlock, "_pid_alive", lambda pid: pid == os.getpid())

    # stale로 인식되어 잡혀있지 않은 것으로 본다.
    assert runlock.is_locked(path) is False
    res = runlock.acquire_run_lock(path)
    assert res["status"] == "ok"
    assert res["pid"] == os.getpid()


def test_stale_recovery_when_timestamp_expired(tmp_path):
    """(e) pid가 살아있어도 timestamp가 만료되면 stale로 회수한다."""
    path = _lock(tmp_path)
    # 내 pid(살아있음)지만 STALE_AFTER_SEC보다 훨씬 오래된 timestamp.
    old_ts = time.time() - (runlock.STALE_AFTER_SEC + 100)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pid": os.getpid(), "timestamp": old_ts}, fh)

    assert runlock.is_locked(path) is False
    res = runlock.acquire_run_lock(path)
    assert res["status"] == "ok"


def test_release_does_not_remove_other_live_holder(tmp_path, monkeypatch):
    """(f) 다른 살아있는 pid의 락은 release가 함부로 지우지 않는다."""
    path = _lock(tmp_path)
    other_pid = os.getpid() + 1
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pid": other_pid, "timestamp": time.time()}, fh)

    # other_pid도 내 pid도 모두 살아있다고 본다(소유권만 다름).
    monkeypatch.setattr(runlock, "_pid_alive", lambda pid: True)

    # 내 락이 아니고 stale도 아니므로 release는 False(미삭제).
    assert runlock.release_run_lock(path) is False
    assert os.path.isfile(path)


def test_release_reaps_stale_lock(tmp_path, monkeypatch):
    """release는 stale 락(사망 pid)은 정리 차원에서 회수한다(True)."""
    path = _lock(tmp_path)
    dead_pid = 2_000_000_001
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"pid": dead_pid, "timestamp": time.time()}, fh)
    monkeypatch.setattr(runlock, "_pid_alive", lambda pid: pid == os.getpid())

    assert runlock.release_run_lock(path) is True
    assert not os.path.isfile(path)


def test_corrupt_lockfile_is_treated_as_unlocked(tmp_path):
    """손상된 lockfile(JSON 아님)은 잠금 없음으로 보고 acquire가 회수한다."""
    path = _lock(tmp_path)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("not json{{{")

    assert runlock.is_locked(path) is False
    res = runlock.acquire_run_lock(path)
    assert res["status"] == "ok"
