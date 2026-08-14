"""Local research-analysis persistence tests."""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.dashboard import analysis_snapshot as SNAP  # noqa: E402
from ai_strategy_loop.dashboard.app import create_app  # noqa: E402
from ai_strategy_loop.fitness.correlation import _OUTCOME_COLUMN  # noqa: E402
from ai_strategy_loop.fitness.edge_ratio import _MAE_PRIMARY, _MFE_PRIMARY, _PROFIT_COLUMN  # noqa: E402
from ai_strategy_loop.fitness.equity_series import _BUY_TIME_COLUMN, _SELL_TIME_COLUMN  # noqa: E402


def _write_analysis_csv(path: Path) -> str:
    """Given a temp path, When writing a trade CSV, Then analysis routes can read it."""
    fieldnames = [
        "종목명",
        _BUY_TIME_COLUMN,
        _SELL_TIME_COLUMN,
        _OUTCOME_COLUMN,
        _PROFIT_COLUMN,
        _MFE_PRIMARY,
        _MAE_PRIMARY,
        "B_시분초",
        "B_시가총액",
        "B_체결강도",
    ]
    rows = [
        ("A", "20250102090100", "20250102090400", 1.0, 1000.0, 2.2, -0.8, 90100, 1200, 80),
        ("B", "20250102090200", "20250102090500", 2.0, 2000.0, 3.4, -0.7, 90200, 1400, 91),
        ("C", "20250102090600", "20250102091000", -1.0, -900.0, 0.8, -1.9, 90600, 4500, 55),
        ("D", "20250103090700", "20250103091100", 3.0, 3100.0, 4.1, -0.6, 90700, 4700, 103),
        ("E", "20250103091100", "20250103091600", -2.0, -1600.0, 0.7, -2.3, 91100, 9000, 48),
        ("F", "20250103091200", "20250103091800", 4.0, 4100.0, 5.0, -0.9, 91200, 9500, 112),
    ]
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "종목명": row[0],
                _BUY_TIME_COLUMN: row[1],
                _SELL_TIME_COLUMN: row[2],
                _OUTCOME_COLUMN: row[3],
                _PROFIT_COLUMN: row[4],
                _MFE_PRIMARY: row[5],
                _MAE_PRIMARY: row[6],
                "B_시분초": row[7],
                "B_시가총액": row[8],
                "B_체결강도": row[9],
            })
    return str(path)


def test_analysis_snapshot_persists_local_research_tables(tmp_path: Path) -> None:
    """Given analysis reports, When persisted, Then snapshot and row tables are queryable."""
    db_path = tmp_path / "research_analysis.db"

    stored = SNAP.persist_analysis_bundle(
        db_path=db_path,
        run_key="runA",
        reports={
            "variable_correlation": {
                "pooled_trades": 3,
                "outcome_correlations": [{"feature": "B_시분초", "correlation": 0.7, "n": 3}],
                "range_summaries": [{"feature": "B_시분초", "median": 90500.0}],
                "segment_summaries": {
                    "time": [{"label": "09:00-09:05", "avg_return": 1.5, "sample_count": 2}],
                    "market_cap": [{"label": "small", "avg_return": 1.0, "sample_count": 2}],
                },
                "interaction_candidates": [
                    {"feature_a": "B_시분초", "feature_b": "B_시가총액", "research_score": 0.8}
                ],
            },
            "edge_ratio": {"global": {"edge_ratio": 1.4, "mean_mfe": 2.0, "mean_mae": 1.4}},
            "generation_metrics": [{"run_id": "runA", "gen_no": 1, "payoff_ratio": 1.8}],
            "daily_profit_loss": [{"date": 20250102, "daily_pnl": 1000.0}],
        },
        params={"method": "spearman"},
    )

    assert stored["persisted"] is True
    assert stored["analysis_id"] > 0
    assert stored["row_counts"]["b_variable_correlation"] == 1
    assert stored["row_counts"]["time_bucket"] == 1
    assert stored["row_counts"]["generation_metric"] == 1

    with sqlite3.connect(db_path) as con:
        snapshot_count = con.execute("SELECT COUNT(*) FROM analysis_snapshots").fetchone()[0]
        row_kinds = {
            row[0] for row in con.execute("SELECT DISTINCT row_kind FROM analysis_rows").fetchall()
        }
    assert snapshot_count == 1
    assert {"compound_feature_interaction", "daily_profit_loss", "edge_global"} <= row_kinds


def test_analysis_snapshot_get_missing_loop_db_leaves_files_absent(
    monkeypatch, tmp_path: Path,
) -> None:
    """Given no loop DB, When snapshot GET runs, Then read paths create no SQLite files."""
    from fastapi.testclient import TestClient

    loop_db = tmp_path / "state" / "loop_runs.db"
    analysis_db = tmp_path / "analysis" / "research_analysis.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", loop_db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(SNAP, "RESEARCH_ANALYSIS_DB", analysis_db)

    client: TestClient = authorized_dashboard_client(create_app())
    resp = client.get("/analysis_snapshot?run_id=missingRun")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["status"] == "no_csv"
    assert body["persisted"] is False
    assert body["store"] is None
    assert not loop_db.exists()
    assert not analysis_db.exists()


def test_analysis_snapshot_route_reads_existing_loop_db_without_persisting(
    monkeypatch, tmp_path: Path,
) -> None:
    """Given a run CSV, When snapshot GET runs, Then loop DB is read-only and not persisted."""
    from fastapi.testclient import TestClient

    loop_db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    analysis_db = tmp_path / "research_analysis.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", loop_db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    monkeypatch.setattr(SNAP, "RESEARCH_ANALYSIS_DB", analysis_db)

    csv_path = _write_analysis_csv(tmp_path / "analysis_route.csv")
    st = LoopState(db_path=str(loop_db), snapshot_dir=str(snaps))
    st.start_run(LoopConfig(provider="gpt_auth", bt_timeframe="tick"), run_id="analysisRun")
    st.record_generation(
        "analysisRun",
        1,
        buy_name="b",
        sell_name="s",
        status="ok",
        score=3.0,
        gate_passed=True,
        csv_path=csv_path,
        trade_count=6,
        daily_avg_trades=3.0,
        mdd=1.2,
        profit=7700.0,
        payoff_ratio=1.8,
        max_hold_count=2.0,
    )
    st.close()

    client = authorized_dashboard_client(create_app())
    resp = client.get(
        "/analysis_snapshot?run_id=analysisRun&persist=true&method=spearman&fine_time=true"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["persisted"] is False
    assert body["store"] is None
    assert body["analysis"]["variable_correlation"]["pooled_trades"] == 6
    assert body["analysis"]["edge_ratio"]["global"]["edge_ratio"] > 1.0
    assert len(body["analysis"]["generation_metrics"]) == 1
    assert len(body["analysis"]["daily_profit_loss"]) == 2
    assert not analysis_db.exists()

    after = LoopState(db_path=str(loop_db), snapshot_dir=str(snaps), readonly=True)
    try:
        assert len(after.get_generations("analysisRun")) == 1
    finally:
        after.close()
