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


def test_index_loads_run_compare_override_before_app() -> None:
    # Phase14.4: 단일 컴파일 번들 bundle/app.js 의 "==== X.jsx ====" 마커 순서로 검증.
    src = _read_front("bundle/app.js")

    panels_pos = src.index("==== panels.jsx ====")
    compare_pos = src.index("==== run-compare.jsx ====")
    app_pos = src.index("==== app.jsx ====")
    assert panels_pos < compare_pos < app_pos


def test_run_compare_component_exposed_on_window() -> None:
    src = _read_front("run-compare.jsx")
    tail = src[src.rfind("Object.assign(window") :]

    assert "RunComparePanel" in tail
