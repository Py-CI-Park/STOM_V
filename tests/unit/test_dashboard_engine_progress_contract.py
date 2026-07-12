"""Dashboard engine-state and honest progress contract tests."""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import to_loop_state  # noqa: E402
from .security_test_client import authorized_dashboard_client  # noqa: E402


def _summary() -> dict[str, str | int]:
    return {"run_id": "progressRun", "best_gen": -1, "max_generations": 5}


def test_latest_info_progress_and_engine_state_defaults_are_backward_compatible() -> None:
    """Given legacy latest payloads, When parsed, Then new observability fields default empty."""
    old_latest = {
        "phase": "backtest_start",
        "last_checkpoint": "csv",
        "message": "running",
    }

    latest = C.LatestInfo.model_validate(old_latest)

    assert latest.backtest_progress == {}
    assert latest.engine_state == {}


def test_to_loop_state_derives_loop_generation_progress_without_tick_counter(monkeypatch) -> None:
    """Given no runner counter, When publishing live state, Then progress is generation-only."""
    monkeypatch.setattr(S.time, "time", lambda: 1010.0)

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(max_generations=5, bt_timeframe="tick"),
        status="running",
        current_gen=2,
        latest={
            "phase": "backtest_start",
            "message": "backtest running",
            "phase_started_at": 1000.0,
        },
    )

    progress = state.latest.backtest_progress
    assert progress["source"] == "loop_generation"
    assert progress["phase"] == "backtest_start"
    assert progress["current_gen"] == 2
    assert progress["total_units"] == 5
    assert progress["done_units"] == 2
    assert progress["percent"] == 40.0
    assert progress["elapsed_sec"] == 10.0
    assert progress["eta_sec"] == 15.0
    assert progress["timeframe"] == "tick"
    assert progress["message"] == "backtest running"


def test_to_loop_state_counts_generation_done_as_completed(monkeypatch) -> None:
    """Given a generation_done phase, When progress is derived, Then current gen is completed."""
    monkeypatch.setattr(S.time, "time", lambda: 1010.0)

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(max_generations=5),
        status="running",
        current_gen=2,
        latest={"phase": "generation_done", "phase_started_at": 1000.0},
    )

    progress = state.latest.backtest_progress
    assert progress["done_units"] == 3
    assert progress["percent"] == 60.0


def test_to_loop_state_preserves_explicit_runner_progress(monkeypatch) -> None:
    """Given runner progress, When state is built, Then explicit counters win."""
    monkeypatch.setattr(S.time, "time", lambda: 1010.0)

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(max_generations=5),
        status="running",
        current_gen=2,
        latest={
            "phase": "backtest_start",
            "backtest_progress": {
                "source": "runner_counter",
                "done_units": 7,
                "total_units": 10,
                "elapsed_sec": 21.0,
            },
        },
    )

    progress = state.latest.backtest_progress
    assert progress["source"] == "runner_counter"
    assert progress["done_units"] == 7
    assert progress["total_units"] == 10
    assert progress["percent"] == 70.0
    assert progress["elapsed_sec"] == 21.0
    assert progress["eta_sec"] == 9.0


def test_to_loop_state_exposes_timeout_deadline_and_progress_source(monkeypatch) -> None:
    """Given warm config, When state is built, Then timeout and source labels are explicit."""
    monkeypatch.setattr(S.time, "time", lambda: 1010.0)

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(
            max_generations=5,
            bt_engine_mode="warm",
            bt_timeframe="tick",
            bt_timeout=1800,
            bt_warm_run_timeout=300,
            bt_full_start=20230101,
            bt_full_end=20251231,
            bt_universe_start_time=90000,
            bt_universe_end_time=93000,
        ),
        status="running",
        current_gen=1,
        latest={
            "phase": "backtest_start",
            "message": "backtest running",
            "phase_started_at": 1000.0,
        },
    )

    progress = state.latest.backtest_progress
    assert progress["source"] == "loop_generation"
    assert progress["progress_source"] == "generation_level"
    assert progress["timeout_sec"] == 300
    assert progress["timeout_deadline_epoch"] == 1300.0
    assert progress["elapsed_sec"] == 10.0

    engine = state.latest.engine_state
    assert engine["bt_timeout"] == 1800
    assert engine["bt_warm_run_timeout"] == 300
    assert engine["timeout_sec"] == 300
    assert engine["bt_full_start"] == 20230101
    assert engine["bt_full_end"] == 20251231
    assert engine["bt_universe_start_time"] == 90000
    assert engine["bt_universe_end_time"] == 93000


def test_to_loop_state_engine_state_carries_config_logs_and_effective_count() -> None:
    """Given warm tick config, When state is built, Then engine settings and logs are visible."""
    logs = [f"log-{i}" for i in range(60)]

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(
            bt_engine_mode="warm",
            bt_timeframe="tick",
            bt_engine_count=4,
            bt_warm_engine_count=32,
            bt_full_start=20230101,
            bt_full_end=20251231,
            bt_universe_start_time=90000,
            bt_universe_end_time=93000,
        ),
        status="running",
        current_gen=1,
        latest={"phase": "warm_prepare_start", "recent_logs": logs},
    )

    engine = state.latest.engine_state
    assert engine["status"] == "running"
    assert engine["phase"] == "warm_prepare_start"
    assert engine["current_gen"] == 1
    assert engine["cpu_count"] >= 1
    assert engine["bt_engine_mode"] == "warm"
    assert engine["bt_timeframe"] == "tick"
    assert engine["is_tick"] is True
    assert engine["bt_engine_count"] == 4
    assert engine["bt_warm_engine_count"] == 32
    assert engine["effective_engine_count"] == 32
    assert engine["period_start"] == 20230101
    assert engine["period_end"] == 20251231
    assert engine["buy_start_time"] == 90000
    assert engine["buy_end_time"] == 93000
    assert engine["recent_logs"] == logs[-50:]


def test_to_loop_state_preserves_timeout_cancel_reset_logs() -> None:
    """Given runtime logs, When state is built, Then recent timeout/cancel/reset lines remain."""
    logs = [
        "warm session prepared",
        "backtest timeout after 300s",
        "cancel requested by stop flag",
        "warm engine reset complete",
    ]

    state = to_loop_state(
        _summary(),
        [],
        config=LoopConfig(bt_engine_mode="warm", bt_warm_run_timeout=300),
        status="running",
        current_gen=1,
        latest={"phase": "backtest_end", "recent_logs": logs},
    )

    engine = state.latest.engine_state
    assert engine["recent_logs"] == logs
    assert any("timeout" in line for line in engine["recent_logs"])
    assert any("cancel" in line for line in engine["recent_logs"])
    assert any("reset" in line for line in engine["recent_logs"])


def test_status_route_normalizes_legacy_current_state_observability_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Given legacy current_state JSON, When /status is read, Then observability defaults exist."""
    from ai_strategy_loop.dashboard.app import create_app

    current_state = tmp_path / "current_state.json"
    current_state.write_text(
        json.dumps(
            {
                "contract_version": C.CONTRACT_VERSION,
                "run_id": "legacy-run",
                "status": "running",
                "current_gen": 1,
                "max_generations": 3,
                "bt_timeframe": "tick",
                "latest": {
                    "phase": "backtest_start",
                    "message": "legacy state",
                },
                "active_config": {
                    "bt_engine_mode": "warm",
                    "bt_timeframe": "tick",
                    "bt_engine_count": 4,
                    "bt_warm_engine_count": 12,
                    "bt_full_start": 20230101,
                    "bt_full_end": 20251231,
                    "bt_universe_start_time": 90000,
                    "bt_universe_end_time": 93000,
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", current_state)
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")

    response = authorized_dashboard_client(create_app()).get("/status")

    assert response.status_code == 200
    latest = response.json()["latest"]
    assert latest["backtest_progress"]["source"] == "loop_generation"
    assert latest["backtest_progress"]["total_units"] == 3
    assert latest["backtest_progress"]["timeframe"] == "tick"
    assert latest["engine_state"]["cpu_count"] >= 1
    assert latest["engine_state"]["bt_engine_mode"] == "warm"
    assert latest["engine_state"]["bt_timeframe"] == "tick"
    assert latest["engine_state"]["effective_engine_count"] == 12


def test_status_route_normalizes_legacy_current_state_timeout_fields(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Given legacy JSON, When /status is read, Then timeout observability is filled."""
    from ai_strategy_loop.dashboard import app as dashboard_app
    from ai_strategy_loop.dashboard.app import create_app

    current_state = tmp_path / "current_state.json"
    current_state.write_text(
        json.dumps(
            {
                "contract_version": C.CONTRACT_VERSION,
                "run_id": "legacy-timeout-run",
                "status": "running",
                "current_gen": 1,
                "max_generations": 3,
                "bt_timeframe": "tick",
                "latest": {
                    "phase": "backtest_start",
                    "message": "legacy state",
                    "phase_started_at": 1000.0,
                    "recent_logs": ["backtest timeout reset checkpoint"],
                },
                "active_config": {
                    "bt_engine_mode": "warm",
                    "bt_timeframe": "tick",
                    "bt_timeout": 1800,
                    "bt_warm_run_timeout": 900,
                    "bt_engine_count": 4,
                    "bt_warm_engine_count": 12,
                    "bt_full_start": 20230101,
                    "bt_full_end": 20251231,
                    "bt_universe_start_time": 90000,
                    "bt_universe_end_time": 93000,
                },
            },
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", current_state)
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(dashboard_app.time, "time", lambda: 1010.0)

    response = authorized_dashboard_client(create_app()).get("/status")

    assert response.status_code == 200
    latest = response.json()["latest"]
    assert latest["backtest_progress"]["progress_source"] == "generation_level"
    assert latest["backtest_progress"]["timeout_sec"] == 900
    assert latest["backtest_progress"]["timeout_deadline_epoch"] == 1900.0
    assert latest["engine_state"]["timeout_sec"] == 900
    assert latest["engine_state"]["bt_timeout"] == 1800
    assert latest["engine_state"]["bt_warm_run_timeout"] == 900
    assert latest["engine_state"]["recent_logs"] == ["backtest timeout reset checkpoint"]
