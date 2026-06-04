"""Static regression tests for generation table sorting."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_generation_table_supports_total_profit_sort_without_losing_actions() -> None:
    src = _read_front("table.jsx")

    assert "sortKey" in src
    assert "total_profit" in src
    assert "Sort: Total Profit" in src
    assert "setSortKey(\"profit_desc\")" in src
    assert "setSortKey(\"gen_desc\")" in src
    assert "onViewCode && onViewCode(g)" in src
    assert "onSelectDetail && onSelectDetail(g.gen_no)" in src
