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
    # Ownership contract: the V2 Home/evolution SPA (app.jsx) must not render
    # RunComparePanel directly. Compare is owned by History navigation and, in the
    # opt-in V4 shell, by the Workbench tab. Since V4 shares the single compiled
    # bundle, app.js legitimately CONTAINS RunComparePanel (imported by V4 Workbench);
    # asserting bundle string-absence is therefore invalid post-V4. Assert the real
    # contract on the owning source files instead.
    bundle = _read_front("bundle/app.js")
    assert "CurrentGenPanel" in bundle, "app.js 에 panels(CurrentGenPanel) 누락"
    assert "ResearchRecordsPanel" in bundle, "app.js 에 records owner 누락"
    assert "ResearchIndexPage" in bundle, "app.js 에 history route 누락"

    # Home SPA must not own/render Compare.
    app_src = _read_front("app.jsx")
    assert "RunComparePanel" not in app_src, "Home SPA(app.jsx) must not render Compare owner"

    # Compare is owned by the V4 Workbench tab (single legitimate render site).
    workbench_src = _read_front("v4-workbench.jsx")
    assert "RunComparePanel" in workbench_src, "V4 Workbench must own Compare"


def test_run_compare_component_exposed_on_window() -> None:
    src = _read_front("run-compare.jsx")
    tail = src[src.rfind("Object.assign(window") :]

    assert "RunComparePanel" in tail
