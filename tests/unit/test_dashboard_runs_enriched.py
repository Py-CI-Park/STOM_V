"""Dashboard run metadata enrichment tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402


@pytest.fixture
def seeded_runs_enriched(monkeypatch, tmp_path: Path) -> dict[str, Path]:
    """Seed one completed tick run with deterministic config, timing, and profit fields."""
    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    cfg = LoopConfig(
        provider="gpt_auth",
        bt_timeframe="tick",
        bt_full_start=20230101,
        bt_full_end=20251231,
        bt_universe_start_time=90000,
        bt_universe_end_time=92800,
    )
    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    try:
        st.start_run(cfg, run_id="runEnrich")
        st.record_generation(
            "runEnrich",
            0,
            buy_name="b0",
            sell_name="s0",
            status="ok",
            score=1.0,
            gate_passed=False,
            trade_count=10,
            mdd=4.0,
            profit=1000.0,
            total_profit_pct=1.2,
            daily_avg_trades=1.0,
            max_hold_count=2.0,
        )
        st.record_generation(
            "runEnrich",
            1,
            buy_name="b1",
            sell_name="s1",
            status="ok",
            score=2.0,
            gate_passed=True,
            trade_count=20,
            mdd=5.0,
            profit=2000.0,
            total_profit_pct=2.5,
            daily_avg_trades=2.0,
            max_hold_count=3.0,
            payoff_ratio=1.7,
        )
        st.finish_run("runEnrich")
        st._con.execute(
            "UPDATE runs SET started_at = ?, finished_at = ? WHERE run_id = ?",
            (1000.0, 1120.0, "runEnrich"),
        )
        st._con.execute(
            "UPDATE generations SET created_at = ? WHERE run_id = ? AND gen_no = ?",
            (1030.0, "runEnrich", 0),
        )
        st._con.execute(
            "UPDATE generations SET created_at = ? WHERE run_id = ? AND gen_no = ?",
            (1100.0, "runEnrich", 1),
        )
        st._con.commit()
    finally:
        st.close()
    return {"db": db}


@pytest.fixture
def client(monkeypatch, tmp_path: Path):
    """Dashboard TestClient with runtime state files isolated."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


def test_runs_payload_includes_period_profit_timeframe(client, seeded_runs_enriched) -> None:
    """Given a seeded run, When /runs is called, Then enriched sortable metadata is present."""
    body = client.get("/runs").json()
    row = next(run for run in body["runs"] if run["run_id"] == "runEnrich")

    assert row["period"] == "2023-01-01 ~ 2025-12-31"
    assert row["timeframe"] == "tick"
    assert row["years"] == [2023, 2024, 2025]
    assert row["start_year"] == 2023
    assert row["end_year"] == 2025
    assert row["bt_universe_start_time"] == 90000
    assert row["bt_universe_end_time"] == 92800
    assert row["final_profit"] == pytest.approx(2000.0)
    assert row["total_profit_pct"] == pytest.approx(2.5)
    assert row["trade_count"] == 20
    assert row["daily_avg_trades"] == pytest.approx(2.0)
    assert row["max_hold_count"] == pytest.approx(3.0)
    assert row["mdd"] == pytest.approx(5.0)
    assert row["payoff_ratio"] == pytest.approx(1.7)
    assert row["elapsed_sec"] == pytest.approx(120.0)
    assert row["cost_or_count"] == pytest.approx(2.0)
    assert row["cost_or_count_text"] == "2.0"


def test_runs_compare_includes_generation_rows(client, seeded_runs_enriched) -> None:
    """Given a selected run, When /runs/compare is called, Then per-generation rows are included."""
    body = client.get("/runs/compare?ids=runEnrich").json()

    assert body["count"] == 1
    assert body["generation_count"] == 2
    rows = body["generation_rows"]
    assert [row["gen_no"] for row in rows] == [0, 1]
    assert rows[0]["duration_sec"] == pytest.approx(30.0)
    assert rows[1]["duration_sec"] == pytest.approx(70.0)
    assert rows[1]["profit"] == pytest.approx(2000.0)
    assert rows[1]["total_profit_pct"] == pytest.approx(2.5)
    assert rows[1]["period"] == "2023-01-01 ~ 2025-12-31"
    assert rows[1]["timeframe"] == "tick"
    assert rows[1]["payoff_ratio"] == pytest.approx(1.7)


def test_run_state_active_config_includes_engine_window(client, seeded_runs_enriched) -> None:
    """Given run config_json, When /run_state is called, Then active_config shows engine settings."""
    body = client.get("/run_state?run_id=runEnrich").json()

    cfg = body["active_config"]
    assert cfg["bt_timeframe"] == "tick"
    assert cfg["bt_full_start"] == 20230101
    assert cfg["bt_full_end"] == 20251231
    assert cfg["bt_universe_start_time"] == 90000
    assert cfg["bt_universe_end_time"] == 92800


def test_generation_durations_include_period_and_timeframe(client, seeded_runs_enriched) -> None:
    """Given generation timing, When /generation_durations is called, Then rows carry run context."""
    body = client.get("/generation_durations?run_id=runEnrich").json()

    assert body["count"] == 2
    rows = body["durations"]
    assert rows[0]["duration_sec"] == pytest.approx(30.0)
    assert rows[0]["period"] == "2023-01-01 ~ 2025-12-31"
    assert rows[0]["timeframe"] == "tick"
