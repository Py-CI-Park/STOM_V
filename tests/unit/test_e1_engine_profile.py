from ai_strategy_loop.labeling.run_e1_engine_profile import (
    _arm_summary,
    _worker_snapshot,
    classify,
)


def _row(arm, status, checkpoint="engine_strategy_progress", ticks=1000):
    return {
        "arm": arm,
        "status": status,
        "diagnostics": {
            "last_by_source": {
                "BackTest": "backtest_child_waiting_mq_heartbeat",
                "BackEngine:0": checkpoint,
            },
            "last_detail_by_source": {
                "BackEngine:0": {
                    "tick_count": ticks,
                    "code_count": 2,
                    "elapsed_seconds": 10.0,
                    "code": "A",
                    "index": 20231114090000,
                    "error": None,
                }
            },
        },
    }


def test_worker_snapshot_keeps_only_bounded_engine_fields():
    snapshot = _worker_snapshot(_row("generated", "timeout"))
    assert snapshot == {
        "BackEngine:0": {
            "checkpoint": "engine_strategy_progress",
            "tick_count": 1000,
            "code_count": 2,
            "elapsed_seconds": 10.0,
            "code": "A",
            "index": 20231114090000,
            "error": None,
        }
    }


def test_classify_requires_stable_three_by_three_worker_boundary():
    rows = (
        [_row("baseline", "success", "engine_backtest_completed", 5000) for _ in range(3)]
        + [_row("generated", "timeout") for _ in range(3)]
    )
    assert classify(rows) == "WORKER_BOTTLENECK_LOCALIZED"
    assert _arm_summary(rows[:3])["tick_count"]["median"] == 5000


def test_classify_fails_closed_without_worker_evidence():
    rows = [_row("baseline", "success") for _ in range(3)]
    rows += [_row("generated", "timeout") for _ in range(3)]
    rows[-1]["diagnostics"] = {}
    assert classify(rows) == "BLOCKED_ENVIRONMENT"
