"""Raw feature routes must admit evidence before reading strategy or calculating."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.autopsy import label_dataset as labels
from ai_strategy_loop.controller import strategy_preflight
from ai_strategy_loop.dashboard import backtest_api as api
from tests.unit.dashboard.trade_quality_fixtures import official_pair

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("kind", ["leaf", "map", "revision"])
@pytest.mark.parametrize("case", ["partial", "error", "missing"])
def test_feature_admission_precedes_calculation_and_strategy_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
    case: str,
) -> None:
    # Given: rejected generation and observable expensive operations.
    header, row = official_pair()
    path = tmp_path / "features.csv"
    if case != "missing":
        path.write_text(
            header + row + ("bad\n" if case == "partial" else ""), encoding="utf-8"
        )
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        api,
        "_gen_row_readonly",
        lambda *args: {
            "status": "error" if case == "error" else "ok",
            "csv_path": str(path),
            "trade_count": 1,
            "buy_name": "fixture",
        },
    )
    calls: list[str] = []
    original = labels.enrich

    def enrich(frame):
        calls.append("enrich")
        return original(frame)

    def strategy(*args, **kwargs):
        calls.append("strategy")

    monkeypatch.setattr(labels, "enrich", enrich)
    monkeypatch.setattr(strategy_preflight, "load_loop_strategy_code", strategy)
    # When: call the existing production API handlers.
    handlers = {
        "leaf": api.analysis_leaf_matrix,
        "map": api.analysis_feature_map,
        "revision": api.analysis_revision_proposals,
    }
    result = handlers[kind](run_id="fixture", gen_no=1)
    # Then: no feature/strategy work before source admission.
    assert calls == []
    assert result["analysis_ready"] is False
    assert result["data_quality"] is not None


@pytest.mark.parametrize("axis", ["R_MFE", "수익률", "수익금"])
def test_outcome_columns_cannot_be_requested_as_entry_features(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    axis: str,
) -> None:
    # Given: genuine outcome columns in an otherwise valid official source.
    header, row = official_pair()
    path = tmp_path / "features.csv"
    path.write_text(header + row, encoding="utf-8")
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(
        api,
        "_gen_row_readonly",
        lambda *args: {"status": "ok", "csv_path": str(path), "trade_count": 1},
    )
    # When / Then: raw outcome retention must not become an input-variable bypass.
    result = api.analysis_feature_map(run_id="fixture", gen_no=1, x=axis)
    assert result["analysis_ready"] is False
    assert result["feature_status"] == "INVALID_VARIABLE"
    assert result["grid"] is None
