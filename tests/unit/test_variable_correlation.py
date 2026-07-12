"""Variable correlation analysis API tests.

The dashboard must expose read-only correlation analysis over existing
per-trade CSVs. These tests pin the pure analytics contract first, then the
FastAPI route that resolves csv_path values from the loop state DB.
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.config import LoopConfig  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.controller.state import LoopState  # noqa: E402
from ai_strategy_loop.fitness.correlation import (  # noqa: E402
    compute_variable_correlation,
    variable_correlation_from_csvs,
)


def _row_by_feature(rows: list[dict], feature: str) -> dict:
    return next(row for row in rows if row["feature"] == feature)


def test_compute_variable_correlation_exact_pearson() -> None:
    """Given numeric B_* features, When Pearson runs, Then exact correlations are JSON-safe."""
    df = pd.DataFrame({
        "수익률": [1.0, 2.0, 3.0, 4.0, 5.0],
        "B_상승": [1.0, 2.0, 3.0, 4.0, 5.0],
        "B_역행": [5.0, 4.0, 3.0, 2.0, 1.0],
        "B_반복": [2.0, 1.0, 2.0, 1.0, 2.0],
        "S_누수": [1.0, 2.0, 3.0, 4.0, 5.0],
        "R_MFE": [10.0, 20.0, 30.0, 40.0, 50.0],
    })

    out = compute_variable_correlation(df, method="pearson", min_samples=3)

    assert out["method"] == "pearson"
    assert out["pooled_trades"] == 5
    assert out["feature_count"] == 3
    features = {row["feature"] for row in out["outcome_correlations"]}
    assert features == {"B_상승", "B_역행", "B_반복"}
    assert "S_누수" not in features
    assert "R_MFE" not in features

    up = _row_by_feature(out["outcome_correlations"], "B_상승")
    down = _row_by_feature(out["outcome_correlations"], "B_역행")
    assert up["correlation"] == pytest.approx(1.0)
    assert down["correlation"] == pytest.approx(-1.0)
    assert up["n"] == 5

    matrix = {(row["feature_a"], row["feature_b"]): row for row in out["feature_matrix"]}
    assert matrix[("B_상승", "B_역행")]["correlation"] == pytest.approx(-1.0)
    assert out["top_pairs"][0]["abs_correlation"] == pytest.approx(1.0)


def test_compute_variable_correlation_spearman_switch() -> None:
    """Given monotonic nonlinear values, When Spearman runs, Then rank correlation is exact."""
    df = pd.DataFrame({
        "수익률": [1.0, 2.0, 3.0, 4.0, 5.0],
        "B_곡선": [1.0, 4.0, 9.0, 16.0, 25.0],
    })

    out = compute_variable_correlation(df, method="spearman", min_samples=3)

    row = _row_by_feature(out["outcome_correlations"], "B_곡선")
    assert out["method"] == "spearman"
    assert row["correlation"] == pytest.approx(1.0)


def test_compute_variable_correlation_adds_research_profile() -> None:
    """Given buy-time variables, When correlation runs, Then research-only profile fields are returned."""
    df = pd.DataFrame({
        "일자": [20230102, 20230103, 20240102, 20240103, 20250102, 20250103, 20250104, 20250105],
        "수익률": [-2.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        "B_시분초": [90100, 90200, 93000, 93100, 100000, 100100, 110000, 110100],
        "B_시가총액": [100.0, 150.0, 200.0, 220.0, 1000.0, 1200.0, 2000.0, 2200.0],
        "B_상승": [1.0, 1.2, 2.0, 2.2, 3.0, 3.2, 4.0, 4.2],
        "B_역행": [4.2, 4.0, 3.2, 3.0, 2.2, 2.0, 1.2, 1.0],
        "B_보완": [1.0, 2.0, 1.0, 2.0, 3.0, 1.0, 3.0, 2.0],
    })

    out = compute_variable_correlation(df, method="spearman", min_samples=2, top_n=5)

    assert out["source"] == "pooled_trade_csv"
    assert out["sample_count"] == 8
    assert out["input_rows"] == 8
    assert out["truncated"] is False

    ranges = {row["feature"]: row for row in out["range_summaries"]}
    assert ranges["B_상승"]["histogram"]
    assert sum(bin_["count"] for bin_ in ranges["B_상승"]["histogram"]) == 8
    assert ranges["B_상승"]["win_loss"]["mean_win"] > ranges["B_상승"]["win_loss"]["mean_loss"]

    segments = out["segment_summaries"]
    assert segments["time"]
    assert segments["market_cap"]
    assert {row["label"] for row in segments["year"]} == {"2023", "2024", "2025"}
    assert all("feature_ranges" in row for row in segments["year"])

    assert out["interaction_candidates"]
    candidate = out["interaction_candidates"][0]
    assert {"feature_a", "feature_b", "research_score", "sample_count"} <= set(candidate)

    recency = out["recency_research"]
    assert recency["research_only"] is True
    assert recency["score_label"] == "research_score_not_promotion"
    assert recency["weights"]["2025"] == pytest.approx(1.5)


def test_compute_variable_correlation_row_limit_reports_truncation() -> None:
    """Given too many rows, When row_limit is set, Then deterministic truncation is reported."""
    df = pd.DataFrame({
        "수익률": [1.0, 2.0, 3.0, 4.0],
        "B_상승": [1.0, 2.0, 3.0, 4.0],
    })

    out = compute_variable_correlation(df, min_samples=2, row_limit=3)

    assert out["input_rows"] == 4
    assert out["sample_count"] == 3
    assert out["row_limit"] == 3
    assert out["truncated"] is True


def test_compute_variable_correlation_insufficient_guards() -> None:
    """Given missing/low-sample inputs, When analysis runs, Then it returns insufficient."""
    missing_outcome = compute_variable_correlation(pd.DataFrame({"B_x": [1, 2, 3]}))
    assert missing_outcome["insufficient"] is True
    assert missing_outcome["reason"] == "missing_outcome_column"

    low_sample = compute_variable_correlation(
        pd.DataFrame({"수익률": [1.0, 2.0], "B_x": [1.0, 2.0]}),
        min_samples=3,
    )
    assert low_sample["insufficient"] is True
    assert low_sample["pooled_trades"] == 2


def _write_csv(path: Path, rows: list[tuple[float, float, float]]) -> str:
    """Write utf-8-sig per-trade rows: (return, B_up, B_down)."""
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["종목명", "수익률", "B_상승", "B_역행"])
        writer.writeheader()
        for ret, up, down in rows:
            writer.writerow({"종목명": "A종목", "수익률": ret, "B_상승": up, "B_역행": down})
    return str(path)


def test_variable_correlation_from_csvs_pools_and_skips_missing(tmp_path: Path) -> None:
    """Given two CSVs plus one missing path, When pooling, Then only readable files count."""
    p1 = _write_csv(tmp_path / "a.csv", [(1.0, 1.0, 5.0), (2.0, 2.0, 4.0), (3.0, 3.0, 3.0)])
    p2 = _write_csv(tmp_path / "b.csv", [(4.0, 4.0, 2.0), (5.0, 5.0, 1.0)])
    missing = str(tmp_path / "missing.csv")

    out = variable_correlation_from_csvs([p1, missing, p2], method="pearson")

    assert out["sources"] == 2
    assert out["pooled_trades"] == 5
    assert _row_by_feature(out["outcome_correlations"], "B_상승")["correlation"] == pytest.approx(1.0)
    assert _row_by_feature(out["outcome_correlations"], "B_역행")["correlation"] == pytest.approx(-1.0)


def test_variable_correlation_from_csvs_empty_pool_insufficient() -> None:
    """Given no readable CSVs, When pooling, Then it returns the standard insufficient payload."""
    assert variable_correlation_from_csvs([]) == {"insufficient": True, "pooled_trades": 0}
    assert variable_correlation_from_csvs(["missing_a.csv"]) == {
        "insufficient": True,
        "pooled_trades": 0,
    }


def test_variable_correlation_route_reads_generation_csv_without_mutation(monkeypatch, tmp_path: Path) -> None:
    """Given a seeded run DB, When the route is called, Then it returns pooled correlations read-only."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    snaps = tmp_path / "snaps"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "cs.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    csv_path = _write_csv(
        tmp_path / "route.csv",
        [(1.0, 1.0, 5.0), (2.0, 2.0, 4.0), (3.0, 3.0, 3.0), (4.0, 4.0, 2.0)],
    )

    st = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    st.start_run(LoopConfig(provider="gpt_auth", bt_timeframe="tick"), run_id="corrRun")
    st.record_generation(
        "corrRun",
        0,
        buy_name="b",
        sell_name="s",
        status="ok",
        score=1.0,
        gate_passed=True,
        csv_path=csv_path,
    )
    st.close()

    client = authorized_dashboard_client(create_app())
    resp = client.get("/variable_correlation?run_id=corrRun&method=spearman")

    assert resp.status_code == 200
    body = resp.json()
    assert body["runs"] == ["corrRun"]
    assert body["method"] == "spearman"
    assert body["pooled_trades"] == 4
    assert _row_by_feature(body["outcome_correlations"], "B_상승")["correlation"] == pytest.approx(1.0)

    after = LoopState(db_path=str(db), snapshot_dir=str(snaps))
    try:
        assert len(after.get_generations("corrRun")) == 1
    finally:
        after.close()
