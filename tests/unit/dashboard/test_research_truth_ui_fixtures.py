from __future__ import annotations

import json
from pathlib import Path

from ai_strategy_loop.controller.research_truth_contract import ExecutionStatus
from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue
from ai_strategy_loop.dashboard.research_truth_adapter import project_legacy_job_truth

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "research_truth_ui"
)


def _fixture(path: Path) -> dict[str, JsonValue]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_browser_fixtures_project_all_five_truth_states() -> None:
    expected = {
        "ux_fixture_success.json": ExecutionStatus.SUCCESS,
        "ux_fixture_no_trades.json": ExecutionStatus.NO_TRADES,
        "ux_fixture_error.json": ExecutionStatus.ERROR,
        "ux_fixture_timeout.json": ExecutionStatus.TIMEOUT,
        "ux_fixture_partial.json": ExecutionStatus.PARTIAL,
    }

    observed = {
        path.name: project_legacy_job_truth(
            _fixture(path),
            manager_id="research_truth_ui",
            jobs_dir=FIXTURES.as_posix(),
            log_size_bytes=None,
        ).execution
        for path in FIXTURES.glob("*.json")
    }

    assert observed == expected
