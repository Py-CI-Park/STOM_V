"""Snapshot adapter preserves legacy parser semantics without reopening paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pytest

from ai_strategy_loop.autopsy import label_dataset as labels
from ai_strategy_loop.dashboard import backtest_api as api
from ai_strategy_loop.dashboard import individual_source
from ai_strategy_loop.dashboard.feature_snapshot import (
    SnapshotFrameError,
    snapshot_dataset,
)
from ai_strategy_loop.dashboard.trade_csv_quality import load_trade_quality
from tests.unit.dashboard.feature_quality_fixtures import feature_csv
from tests.unit.dashboard.trade_quality_fixtures import official_pair
from tests.unit.test_revision_p2 import CODE

if TYPE_CHECKING:
    from pathlib import Path


def test_parser_disagreement_cannot_silently_remove_a_present_feature(
    tmp_path: Path,
) -> None:
    # Given: Python float accepts underscores, while the legacy numerical parser drops them.
    header, row = official_pair()
    columns = header.strip().split(",")
    cells = row.strip().split(",")
    cells[columns.index("B_체결강도")] = "1_0"
    path = tmp_path / "ambiguous.csv"
    path.write_text(header + ",".join(cells) + "\n", encoding="utf-8")
    checked = load_trade_quality(path)
    assert checked.quality.analysis_ready and checked.snapshot is not None
    # When / Then: raw quality does not authorize a lossy secondary interpretation.
    with pytest.raises(SnapshotFrameError, match="수치"):
        snapshot_dataset(checked.snapshot)


@pytest.mark.parametrize("legacy", [True, False])
@pytest.mark.parametrize("minute", [True, False])
def test_snapshot_matches_existing_dataframe_and_dtype_after_path_changes(
    tmp_path: Path,
    legacy: bool,
    minute: bool,
) -> None:
    # Given: quoted strings, CRLF, NA and all official B/S/R columns.
    path = feature_csv(tmp_path / "raw.csv", legacy=legacy, minute=minute)
    expected = labels.build(str(path))
    checked = load_trade_quality(path, expected_row_count=40)
    assert checked.quality.analysis_ready and checked.snapshot is not None
    snapshot = checked.snapshot
    original = (snapshot.headers, snapshot.rows, snapshot.sha256)
    path.write_text("changed after capture", encoding="utf-8")
    # When: use the captured cells, not the changed file.
    actual = snapshot_dataset(snapshot)
    # Then: existing parser dtype/NA/enrichment and original snapshot remain exact.
    pd.testing.assert_frame_equal(actual.df, expected.df)
    assert (
        actual.features == expected.features and actual.timeframe == expected.timeframe
    )
    assert (snapshot.headers, snapshot.rows, snapshot.sha256) == original


@pytest.mark.parametrize("kind", ["leaf", "map", "revision"])
def test_feature_routes_never_reopen_the_checked_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: str,
) -> None:
    # Given: a path that changes immediately after the single admission snapshot.
    path = feature_csv(tmp_path / "raw.csv")
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    reads: list[str] = []
    monkeypatch.setattr(
        api,
        "_gen_row_readonly",
        lambda *args: {
            "status": "ok",
            "csv_path": str(path),
            "trade_count": 40,
            "buy_name": "fixture",
        },
    )
    original = individual_source.inspect_job_result_source

    def capture(source_path, record):
        checked = original(source_path, record)
        reads.append(checked.quality.source_sha256)
        path.write_text("changed after admission", encoding="utf-8")
        return checked

    from ai_strategy_loop.controller import strategy_preflight

    monkeypatch.setattr(individual_source, "inspect_job_result_source", capture)
    monkeypatch.setattr(
        strategy_preflight, "load_loop_strategy_code", lambda *args: CODE
    )
    handlers = {
        "leaf": api.analysis_leaf_matrix,
        "map": api.analysis_feature_map,
        "revision": api.analysis_revision_proposals,
    }
    # When / Then: all three existing routes finish using one snapshot and real owners.
    result = handlers[kind](run_id="fixture", gen_no=1)
    assert len(reads) == 1
    assert result["analysis_ready"] is True, result.get("reason")
    assert result["data_quality"]["source_sha256"] == reads[0]
    assert (
        result["execution_status"] == "partial"
        and result["execution_verified"] is False
    )
