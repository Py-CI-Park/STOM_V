"""Production individual endpoints must not turn rejected sources into statistics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import backtest_api as api
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path

OPERATORS = {
    "summary": "summary_metrics",
    "equity": "equity_series",
    "distribution": "pnl_distribution",
    "heatmap": "time_heatmap",
    "underwater": "underwater",
    "insights": "generate_insights",
    "mae_mfe": "mae_mfe",
    "exit_reasons": "exit_reason_breakdown",
    "orderflow": "entry_orderflow",
    "gui_parity": "gui_parity",
    "montecarlo": "monte_carlo",
}


@pytest.mark.parametrize("operation", OPERATORS)
@pytest.mark.parametrize(
    "case", ["partial", "missing", "count", "error", "unknown_job"]
)
def test_individual_rejects_before_calculation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: str,
    case: str,
) -> None:
    # Given: a source not eligible for diagnostics and a trap on its operator.
    header, row = official_pair()
    path = tmp_path / "source.csv"
    if case != "missing":
        path.write_text(
            header + row + ("bad\n" if case == "partial" else ""), encoding="utf-8"
        )

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": case != "unknown_job",
                "status": "error" if case == "error" else "success",
                "csv_path": str(path),
                "metrics": {"trade_count": 2 if case == "count" else 1},
            }

    calls: list[str] = []

    def forbidden(*args, **kwargs):
        calls.append("calculated")
        return {}

    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", Manager)
    monkeypatch.setattr(analysis, OPERATORS[operation], forbidden)
    app = FastAPI()
    app.include_router(api.backtest_router)
    # When: call the real HTTP route without starting the operating dashboard.
    with TestClient(app) as client:
        value = client.get(
            f"/bt/analysis/{operation}", params={"job_id": "fixture"}
        ).json()
    # Then: null result plus explicit quality, not empty-list normal metrics.
    assert calls == []
    assert value[operation] is None
    assert value["analysis_ready"] is False
    assert value["available"] is (case != "unknown_job")
    assert value["data_quality"]["analysis_ready"] is not None


@pytest.mark.parametrize("operation", OPERATORS)
def test_individual_valid_input_uses_checked_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    operation: str,
) -> None:
    # Given: official one-row input and a forbidden legacy reread.
    header, row = official_pair()
    path = tmp_path / "source.csv"
    path.write_text(header + row, encoding="utf-8")

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": True,
                "status": "success",
                "csv_path": str(path),
                "metrics": {"trade_count": 1},
            }

    rereads: list[str] = []

    def forbidden(*args, **kwargs):
        rereads.append("read")
        return []

    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(api, "get_job_manager", Manager)
    monkeypatch.setattr(analysis, "load_trades_csv", forbidden)
    app = FastAPI()
    app.include_router(api.backtest_router)
    # When / Then: real calculator sees the admitted snapshot.
    with TestClient(app) as client:
        value = client.get(
            f"/bt/analysis/{operation}", params={"job_id": "fixture", "n": 3, "seed": 7}
        ).json()
    assert rereads == []
    assert value["analysis_ready"] is True
    assert value[operation] is not None
    assert value["data_quality"]["accepted_count"] == 1
