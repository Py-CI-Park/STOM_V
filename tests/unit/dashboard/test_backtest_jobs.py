"""Backtest job manager 라이프사이클 테스트 (PR2).

실제 백테 대신 단명 가짜 커맨드(sys.executable -c "...")를 command_builder 로 주입해
잡 라이프사이클(시작→완료/취소)을 검증한다. 동시 1개 큐잉도 확인한다.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.dashboard.backtest_jobs import (  # noqa: E402
    BacktestJobManager,
    BacktestJobSpec,
)


def _spec(buy="테스트매수", **kw):
    base = dict(buy=buy, sell="테스트매도", start=20250407, end=20250409, timeframe="min")
    base.update(kw)
    return BacktestJobSpec(**base)


def _success_command(csv_path: str):
    """status=success JSON 을 stdout 으로 즉시 뱉는 가짜 백테 커맨드.

    Windows 콘솔 인코딩 이슈를 피하려 ASCII 키만 쓰고 json.dumps 로 직렬화한다.
    """
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':12.5}}))"
    )

    def builder(spec):
        return [sys.executable, "-c", code]
    return builder


def _slow_command():
    """일정 시간 sleep 하는 가짜 백테(취소 테스트용). ASCII stdout 으로 인코딩 안전."""
    def builder(spec):
        return [sys.executable, "-c", "import time,sys; print('engine started'); sys.stdout.flush(); time.sleep(30)"]
    return builder


def _error_command():
    """status=error JSON 을 뱉는 가짜 백테."""
    def builder(spec):
        return [sys.executable, "-c", 'print(\'{"status": "error", "message": "no trades"}\')']
    return builder


def _wait_status(manager, job_id, targets, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get("status") in targets:
            return rec
        time.sleep(0.1)
    return manager.get(job_id)


# ------------------------------------------------------------------ lifecycle
def test_submit_and_success(tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/fake.csv"),
    )
    res = manager.submit(_spec())
    assert res["status"] == "ok"
    job_id = res["job_id"]

    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "success"
    assert rec["csv_path"] == "backtest/csv/fake.csv"
    assert rec["metrics"]["total_profit_pct"] == 12.5
    assert rec["progress"] == 1.0
    assert manager.result_csv_path(job_id) == "backtest/csv/fake.csv"


def test_error_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_error_command())
    job_id = manager.submit(_spec())["job_id"]
    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "error"
    assert "no trades" in rec["message"]


def test_cancel_running_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_slow_command())
    job_id = manager.submit(_spec())["job_id"]
    # running 상태가 될 때까지 대기.
    rec = _wait_status(manager, job_id, {"running"}, timeout=10.0)
    assert rec["status"] == "running"
    cancel = manager.cancel(job_id)
    assert cancel["status"] == "ok"
    rec = _wait_status(manager, job_id, {"cancelled", "error", "timeout"}, timeout=15.0)
    assert rec["status"] == "cancelled"


def test_cancel_queued_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_slow_command())
    first = manager.submit(_spec("first"))["job_id"]
    second = manager.submit(_spec("second"))["job_id"]
    # second 는 큐에서 대기 → 큐 취소 가능.
    _wait_status(manager, first, {"running"}, timeout=10.0)
    cancel = manager.cancel(second)
    assert cancel["status"] == "ok"
    assert cancel["cancelled"] == "queued"
    assert manager.get(second)["status"] == "cancelled"
    # 정리: 실행 중인 first 도 취소.
    manager.cancel(first)


# --------------------------------------------------------------- validation
def test_submit_rejects_bad_name(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(buy=""))["status"] == "error"
    assert manager.submit(_spec(buy="bad\nname"))["status"] == "error"


def test_submit_rejects_bad_dates(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(start=20250410, end=20250407))["status"] == "error"
    assert manager.submit(_spec(start=123))["status"] == "error"


def test_submit_rejects_bad_timeframe(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(timeframe="hour"))["status"] == "error"


# -------------------------------------------------------------- list/persist
def test_list_jobs_and_persistence(tmp_path: Path):
    jobs_dir = tmp_path / "jobs"
    manager = BacktestJobManager(jobs_dir=jobs_dir, command_builder=_success_command("x.csv"))
    job_id = manager.submit(_spec())["job_id"]
    _wait_status(manager, job_id, {"success", "error", "timeout"})
    listing = manager.list_jobs()
    assert listing["count"] >= 1
    assert any(j["job_id"] == job_id for j in listing["jobs"])

    # 재시작 시뮬레이션: 새 매니저가 JSON 영속에서 과거 잡 복원.
    manager2 = BacktestJobManager(jobs_dir=jobs_dir, command_builder=_success_command("x.csv"))
    restored = manager2.get(job_id)
    assert restored["available"] is True
    assert restored["status"] == "success"


def test_get_missing_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.get("nope")["available"] is False


def test_log_tail_captured(tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/fake.csv"),
    )
    job_id = manager.submit(_spec())["job_id"]
    _wait_status(manager, job_id, {"success", "error", "timeout"})
    rec = manager.get(job_id, log_tail=50)
    assert isinstance(rec["log_tail"], list)
    assert any("success" in line for line in rec["log_tail"])
