from __future__ import annotations

from ai_strategy_loop.labeling.run_e0_observability import (
    Fixture, classify, run_once,
)


class FakeClient:
    def __init__(self, statuses, result=None):
        self.statuses = list(statuses)
        self.result = result or {}
        self.calls = []

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        if path == "/bt/run":
            return {"job_id": "J1"}
        if path == "/bt/jobs":
            status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
            return {"jobs": [{"job_id": "J1", "status": status, "message": "m"}]}
        if path == "/bt/job/cancel":
            return {"status": "canceled"}
        if path.startswith("/bt/result"):
            return self.result
        raise AssertionError(path)


def test_run_once_records_bounded_diagnostics():
    client = FakeClient(["running", "success"], {
        "status": "success", "metrics": {"trade_count": 1},
        "process_diagnostics": {
            "event_count": 3,
            "last_checkpoint": "backtest_child_mq_first_received",
            "last_by_source": {"BackTest": "backtest_child_mq_first_received"},
            "events": [{"large": "not copied"}],
        },
    })
    ticks = iter([0.0, 1.0, 2.0])
    row = run_once(
        client, Fixture("x", "B", "S"), 1,
        start=20230101, end=20230102, engines=2,
        job_timeout=10, poll_timeout=20, poll_interval=0,
        clock=lambda: next(ticks), sleep=lambda _: None,
    )
    assert row["status"] == "success"
    assert row["metrics_available"] is True
    assert row["diagnostics"]["event_count"] == 3
    assert row["diagnostics"]["last_detail_by_source"] == {}
    assert "events" not in row["diagnostics"]
    assert client.calls[0][2]["timeout"] == 10


def test_run_once_accepts_job_result_process_diagnostics_key():
    client = FakeClient(["success"], {
        "status": "success",
        "process_diagnostics": {
            "event_count": 4,
            "last_checkpoint": "backtest_child_completed",
            "last_by_source": {"BackTest": "backtest_child_completed"},
        },
    })
    ticks = iter([0.0, 1.0])
    row = run_once(
        client, Fixture("x", "B", "S"), 1,
        start=20230101, end=20230102, engines=2,
        job_timeout=10, poll_timeout=20, poll_interval=0,
        clock=lambda: next(ticks), sleep=lambda _: None,
    )
    assert row["diagnostics"]["last_checkpoint"] == "backtest_child_completed"


def test_run_once_cancels_at_poll_deadline():
    client = FakeClient(["running"], {"status": "canceled"})
    ticks = iter([0.0, 21.0, 22.0])
    row = run_once(
        client, Fixture("x", "B", "S"), 1,
        start=20230101, end=20230102, engines=2,
        job_timeout=10, poll_timeout=20, poll_interval=0,
        clock=lambda: next(ticks), sleep=lambda _: None,
    )
    assert row["timed_out"] is True
    assert any(path == "/bt/job/cancel" for _, path, _ in client.calls)


def _rows(a, b):
    return [
        {"arm": "baseline", "status": a[0], "diagnostics": {"last_checkpoint": a[1]}},
        {"arm": "baseline", "status": a[0], "diagnostics": {"last_checkpoint": a[1]}},
        {"arm": "baseline", "status": a[0], "diagnostics": {"last_checkpoint": a[1]}},
        {"arm": "generated", "status": b[0], "diagnostics": {"last_checkpoint": b[1]}},
        {"arm": "generated", "status": b[0], "diagnostics": {"last_checkpoint": b[1]}},
        {"arm": "generated", "status": b[0], "diagnostics": {"last_checkpoint": b[1]}},
    ]


def test_classify_reproduced_no_difference_and_unstable():
    assert classify(_rows(("success", "received"), ("failed", "waiting"))) == "REPRODUCED"
    assert classify(_rows(("success", "received"), ("success", "received"))) == "NO_DIFFERENCE"
    rows = _rows(("success", "received"), ("failed", "waiting"))
    rows[0]["status"] = "failed"
    assert classify(rows) == "UNSTABLE"
    assert classify(rows[:5]) == "BLOCKED_ENVIRONMENT"


def test_classify_requires_protocol_checkpoint_evidence():
    rows = _rows(("success", "received"), ("failed", "waiting"))
    rows[4]["diagnostics"]["last_checkpoint"] = None
    assert classify(rows) == "BLOCKED_ENVIRONMENT"
