"""The existing real proposer remains a read-only preview after raw admission."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ai_strategy_loop.controller import strategy_preflight
from ai_strategy_loop.dashboard import backtest_api as api
from tests.unit.dashboard.feature_quality_fixtures import revision_csv
from tests.unit.test_revision_p2 import CODE

if TYPE_CHECKING:
    from pathlib import Path


def test_real_proposal_preview_remains_readonly(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given: existing synthetic distribution and strategy, not an operating DB.
    path = revision_csv(tmp_path / "revision.csv")
    before = path.read_bytes()
    monkeypatch.setattr(api, "REPO_ROOT", tmp_path)
    lookups: list[str] = []

    def lookup(*args):
        lookups.append("generation")
        return {
            "status": "ok",
            "csv_path": str(path),
            "trade_count": 160,
            "buy_name": "fixture",
        }

    monkeypatch.setattr(api, "_gen_row_readonly", lookup)
    monkeypatch.setattr(
        strategy_preflight, "load_loop_strategy_code", lambda *args: CODE
    )
    # When: actual proposer/apply/intent checker produce only an in-memory preview.
    result = api.analysis_revision_proposals(run_id="fixture", gen_no=1, top_k=1)
    # Then: finite preview without changing or adding any original artifact.
    assert result["analysis_ready"] is True, result.get("reason")
    assert len(result["proposals"]) == 1
    assert result["proposals"][0]["gate"]["ok"] is True
    assert result["proposals"][0]["diff_preview"]
    assert path.read_bytes() == before and list(tmp_path.iterdir()) == [path]
    assert lookups == ["generation"]
