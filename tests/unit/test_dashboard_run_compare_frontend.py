"""Frontend contract tests for the enriched run comparison console."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_enriched_run_compare_component_exists_and_uses_compare_routes() -> None:
    src = _read_front("run-compare.jsx")

    assert "function RunComparePanel(" in src
    assert "/runs" in src
    assert "/runs/compare" in src
    assert "Seed vs AI" in src
    assert "Sort: Total Profit" in src
    assert "final_profit" in src
    assert "total_profit_pct" in src
    assert "period" in src
    assert "years" in src
    assert "timeframe" in src
    assert "bt_universe_start_time" in src
    assert "bt_universe_end_time" in src
    assert "elapsed_sec" in src
    assert "cost_or_count_text" in src
    assert "daily_avg_trades" in src
    assert "max_hold_count" in src
    assert "payoff_ratio" in src
    assert "mdd" in src
    assert "sparseHoldSuspicious" in src
    assert "Sparse hold warning" in src
    assert "human corridor 6-12" in src


def test_run_compare_does_not_filter_negative_profit_rows() -> None:
    src = _read_front("run-compare.jsx")

    assert "filter(r => r.final_profit > 0" not in src
    assert "filter((r) => r.final_profit > 0" not in src
    assert "num-neg" in src


def test_primary_bundle_keeps_compare_out_of_home_owner() -> None:
    # Dashboard remodel: Compare remains available as source code and History-owned
    # navigation, but the primary Home bundle must not render RunComparePanel directly.
    src = _read_front("bundle/app.js")

    assert "CurrentGenPanel" in src, "app.js 에 panels(CurrentGenPanel) 누락"
    assert "ResearchRecordsPanel" in src, "app.js 에 records owner 누락"
    assert "ResearchIndexPage" in src, "app.js 에 history route 누락"
    assert "RunComparePanel" not in src, "Home bundle must not duplicate Compare owner"


def test_run_compare_component_exposed_on_window() -> None:
    src = _read_front("run-compare.jsx")
    tail = src[src.rfind("Object.assign(window") :]

    assert "RunComparePanel" in tail
