"""Generation and parameter preservation for the individual MC admission."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import backtest_api as api
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "status,ready",
    [
        ("ok", True),
        ("error", False),
        ("timeout", False),
        ("cancelled", False),
        ("unknown", False),
    ],
)
def test_generation_mc_preserves_diagnostic_authority(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
    ready: bool,
) -> None:
    # Given: a valid losing generation, with no invented execution receipt.
    header, row = official_pair()
    path = tmp_path / "generation.csv"
    path.write_text(header + row.replace(",0,0\n", ",-1,-100\n"), encoding="utf-8")
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        api,
        "_gen_row_readonly",
        lambda *args: {
            "status": status,
            "gate_passed": False,
            "trade_count": 1,
            "csv_path": str(path),
        },
    )
    # When: execute only a synthetic diagnostic operator through the real handler.
    value = api.analysis_montecarlo(
        run_id="fixture", gen_no=2, n=3, seed=7, method="moving_block", block_length=2
    )
    # Then: loss/gate failure remains usable only with writer-ok, not SUCCESS.
    assert value["analysis_ready"] is ready
    assert value["execution_verified"] is False
    assert value["analysis_authority"] == "diagnostic_legacy_generation"
    if ready:
        assert value["execution_status"] == "partial"
        assert value["montecarlo"]["final"]["p50"] == -100
        assert value["montecarlo"]["method"] == "moving_block"
        assert value["montecarlo"]["block_length"] == 2
        assert value["montecarlo"]["seed"] == 7
    else:
        assert value["montecarlo"] is None


@pytest.mark.parametrize("empty_source", [True, False])
def test_real_empty_source_and_empty_selection_are_not_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    empty_source: bool,
) -> None:
    # Given: either an official zero-row source or a valid source outside the range.
    header, row = official_pair()
    path = tmp_path / "generation.csv"
    path.write_text(header + ("" if empty_source else row), encoding="utf-8")
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        api,
        "_gen_row_readonly",
        lambda *args: {
            "status": "ok",
            "trade_count": 0 if empty_source else 1,
            "csv_path": str(path),
        },
    )
    # When / Then: preserve real zero sample semantics and the original source count.
    value = api.analysis_montecarlo(
        run_id="fixture", gen_no=2, n=3, seed=7, t_start=20260101000000
    )
    assert value["analysis_ready"] is (not empty_source)
    if empty_source:
        assert value["montecarlo"] is None
        assert value["data_quality"]["status"] == "NO_TRADES"
    else:
        assert value["montecarlo"]["n"] == 0
    assert value["data_quality"]["raw_count"] == (0 if empty_source else 1)


def test_missing_generation_does_not_compute(monkeypatch: pytest.MonkeyPatch) -> None:
    # Given / When: no source record, despite a syntactically valid selector.
    monkeypatch.setattr(api, "_gen_row_readonly", lambda *args: None)
    calls: list[str] = []
    monkeypatch.setattr(
        analysis, "monte_carlo", lambda *args, **kwargs: calls.append("computed")
    )
    value = api.analysis_montecarlo(run_id="missing", gen_no=1)
    # Then: no fabricated zero MC.
    assert calls == []
    assert value["available"] is False and value["montecarlo"] is None
