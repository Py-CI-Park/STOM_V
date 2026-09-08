"""The real job result route must not compute normal metrics from bad inputs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_strategy_loop.dashboard import backtest_analysis, backtest_api
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("case", ["partial", "missing", "count", "error", "no_trades"])
def test_invalid_job_result_does_not_call_full_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    case: str,
) -> None:
    # Given: bad source or failed execution, plus a trap on metric computation.
    header, row = official_pair()
    path = tmp_path / "result.csv"
    if case != "missing":
        path.write_text(
            header + row + ("bad\n" if case == "partial" else ""), encoding="utf-8"
        )

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": True,
                "job_id": job_id,
                "status": case if case in ("error", "no_trades") else "success",
                "csv_path": str(path),
                "spec": {},
                "metrics": {"trade_count": 2 if case in ("count", "partial") else 1},
            }

    calls: list[str] = []

    def forbidden_analysis(*args, **kwargs):
        calls.append("computed")
        return {"summary": {"trade_count": 0}}

    monkeypatch.setattr(backtest_api, "get_job_manager", Manager)
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backtest_analysis, "full_analysis", forbidden_analysis)
    app = FastAPI()
    app.include_router(backtest_api.backtest_router)
    # When: invoke the production job result API, not a parallel route.
    with TestClient(app) as client:
        value = client.get("/bt/result", params={"job_id": "fixture"}).json()
    # Then: preserve the record but publish no fabricated numeric analysis.
    assert value["available"] is True
    assert calls == []
    assert value["analysis_ready"] is False
    assert value["analysis"] is None
    assert value["metrics"] is None
    assert value["data_quality"] is not None
    expected = {
        "partial": "ROW_PARSE_PARTIAL",
        "missing": "MISSING_ARTIFACT",
        "count": "ROW_COUNT_MISMATCH",
        "error": "VALID",
        "no_trades": "VALID",
    }
    assert value["data_quality"]["status"] == expected[case]


@pytest.mark.parametrize("t_start,selected", [(None, 1), (20260101000000, 0)])
def test_valid_job_analysis_uses_validated_snapshot_not_legacy_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    t_start: int | None,
    selected: int,
) -> None:
    # Given: actual zero-profit trade and a trap on any legacy CSV reread.
    header, row = official_pair()
    path = tmp_path / "result.csv"
    path.write_text(header + row, encoding="utf-8")

    class Manager:
        def get(self, job_id: str, log_tail: int = 0):
            return {
                "available": True,
                "job_id": job_id,
                "status": "success",
                "csv_path": str(path),
                "spec": {},
                "metrics": {"trade_count": 1},
            }

    rereads: list[str] = []

    def stale_loader(path):
        rereads.append(str(path))
        return []

    monkeypatch.setattr(backtest_api, "get_job_manager", Manager)
    monkeypatch.setattr(backtest_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(backtest_analysis, "load_trades_csv", stale_loader)
    # When: compute using the actual production summary/series functions.
    result = backtest_api.get_result(job_id="fixture", t_start=t_start)
    # Then: zero is real; the validated one-row snapshot reaches the analysis.
    assert rereads == []
    assert result["analysis_ready"] is True
    assert result["analysis"]["summary"]["trade_count"] == selected
    assert result["analysis"]["summary"]["total_profit_krw"] == 0
    assert result["data_quality"]["raw_count"] == 1


def test_prepared_empty_sequence_does_not_fall_back_to_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: explicit empty input is different from no prepared input.
    calls: list[str] = []

    def loader(path):
        calls.append(str(path))
        return []

    monkeypatch.setattr(backtest_analysis, "load_trades_csv", loader)
    # When / Then: the keyword seam preserves that distinction.
    assert (
        backtest_analysis.full_analysis("unused.csv", prepared_trades=())["trade_count"]
        == 0
    )
    assert calls == []


def test_invalid_count_metadata_is_not_treated_as_missing(tmp_path: Path) -> None:
    # Given: an explicit invalid count, not an omitted expectation.
    from ai_strategy_loop.dashboard.job_result_quality import inspect_job_result_source

    # When / Then: reject metadata without pretending to have read the artifact.
    result = inspect_job_result_source(
        tmp_path / "unused.csv", {"metrics": {"trade_count": "bad"}}
    )
    assert result.quality.status == "INVALID_SCHEMA"
    assert result.quality.raw_count is None
    assert result.snapshot is None
