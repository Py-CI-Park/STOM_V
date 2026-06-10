"""Static UX contract tests for the research metric glossary panel."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_research_glossary_defines_all_user_visible_terms() -> None:
    """Given the dashboard glossary, When scanned, Then every advanced metric is explained."""
    src = _read_front("glossary.jsx")

    for text in (
        "OOS",
        "overfit",
        "MDD",
        "payoff",
        "edge ratio",
        "MFE/MAE",
        "slippage",
        "PBO",
        "DSR",
        "win-day ratio",
        "recent-weighted score",
        "research signal, not production proof",
        "human-level claim blocked",
    ):
        assert text in src


def test_research_glossary_is_loaded_before_app_and_rendered() -> None:
    """Given the UI shell, When loaded, Then the glossary component is available to app.jsx."""
    index = _read_front("index.html")
    app = _read_front("app.jsx")

    glossary_pos = index.find("glossary.jsx")
    app_pos = index.find("app.jsx")

    assert glossary_pos > -1
    assert app_pos > glossary_pos
    assert "<ResearchGlossaryPanel" in app
