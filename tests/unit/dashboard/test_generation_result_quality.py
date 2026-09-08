"""Real generation result route, with synthetic rows instead of a live state DB."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.dashboard import backtest_analysis, backtest_api
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("gate", [True, False])
def test_completed_generation_allows_loss_diagnostics_without_forged_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    gate: bool,
) -> None:
    # Given: writer-ok can be a loss or gate failure; no returncode was recorded.
    header, row = official_pair()
    path = tmp_path / "gen.csv"
    path.write_text(header + row.replace(",0,0\n", ",-1,-100\n"), encoding="utf-8")
    record = {
        "status": "ok",
        "gate_passed": gate,
        "trade_count": 1,
        "csv_path": str(path),
        "profit": -100.0,
        "total_profit_pct": -1.0,
    }
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backtest_api, "_gen_row_readonly", lambda *args: record)
    # When: use the actual generation route.
    value = backtest_api.get_result(run_id="fixture", gen_no=1)
    # Then: quality allows diagnostics, not an invented verified execution or promotion.
    assert value["analysis_ready"] is True
    assert value["metrics"]["total_profit_krw"] == -100
    assert value["execution_status"] == "partial"
    assert value["execution_verified"] is False
    assert value["analysis_authority"] == "diagnostic_legacy_generation"
    assert value["status"] == "ok"
    assert "return_code" not in record


@pytest.mark.parametrize(
    "status", ["error", "timeout", "cancelled", "rejected", "unknown"]
)
def test_non_completed_generation_does_not_compute_csv_metrics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
) -> None:
    # Given: valid CSV alone does not prove a completed generation.
    header, row = official_pair()
    path = tmp_path / "gen.csv"
    path.write_text(header + row, encoding="utf-8")
    record = {"status": status, "trade_count": 1, "csv_path": str(path)}
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backtest_api, "_gen_row_readonly", lambda *args: record)
    calls: list[str] = []

    def forbidden(*args, **kwargs):
        calls.append("computed")
        return {"summary": {}}

    monkeypatch.setattr(backtest_analysis, "full_analysis", forbidden)
    # When / Then: no new calculation, but retain generation identity and raw status.
    value = backtest_api.get_result(run_id="fixture", gen_no=1)
    assert calls == []
    assert value["analysis_ready"] is False
    assert value["analysis"] is None
    assert value["metrics"] is None
    assert value["status"] == status


def test_missing_csv_preserves_unverified_stored_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: historical stored loss, no CSV, and a corrupt nonfinite field.
    record = {
        "status": "rejected",
        "trade_count": 0,
        "csv_path": None,
        "profit": -5000.0,
        "mdd": float("nan"),
        "gate_passed": False,
    }
    monkeypatch.setattr(backtest_api, "_gen_row_readonly", lambda *args: record)
    # When / Then: retain useful stored values without fabricating CSV analysis.
    value = backtest_api.get_result(run_id="fixture", gen_no=1)
    assert value["metrics"]["total_profit_krw"] == -5000
    assert value["metrics"]["max_drawdown_pct"] is None
    assert value["analysis"] is None
    assert value["analysis_ready"] is False
    assert value["summary_authority"] == "stored_unverified"
    json.dumps(value, allow_nan=False)


@pytest.mark.parametrize("created", [1e300, -1e300])
def test_out_of_range_timestamp_does_not_destroy_stored_summary(
    monkeypatch: pytest.MonkeyPatch, created: float,
) -> None:
    # Given: finite but unrepresentable legacy timestamp metadata.
    record = {"status": "rejected", "trade_count": 0, "csv_path": None,
              "created_at": created, "profit": -5000.0}
    monkeypatch.setattr(backtest_api, "_gen_row_readonly", lambda *args: record)
    # When / Then: preserve diagnostic data rather than raising HTTP500.
    value = backtest_api.get_result(run_id="fixture", gen_no=1)
    assert value["metrics"]["total_profit_krw"] == -5000
    assert value["context"]["executed_at"] is None
    assert value["context"]["executed_at_unix"] is None


@pytest.mark.parametrize("partial", [False, True])
def test_bad_generation_csv_never_becomes_normal_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    partial: bool,
) -> None:
    # Given: either mismatched expected count or a rejected CSV row.
    header, row = official_pair()
    path = tmp_path / "gen.csv"
    path.write_text(header + row + ("bad\n" if partial else ""), encoding="utf-8")
    record = {"status": "ok", "trade_count": 2, "csv_path": str(path)}
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backtest_api, "_gen_row_readonly", lambda *args: record)
    # When / Then: keep the precise quality issue.
    value = backtest_api.get_result(run_id="fixture", gen_no=1)
    assert value["analysis_ready"] is False
    assert value["analysis"] is None
    assert value["data_quality"]["status"] == (
        "ROW_PARSE_PARTIAL" if partial else "ROW_COUNT_MISMATCH"
    )
