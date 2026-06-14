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
    """Given the UI shell, When loaded, Then the glossary component is available to app.jsx.

    Phase14.4: 운영 컴포넌트는 단일 번들 bundle/app.js — 순서는 "==== X.jsx ====" 마커로 검증.
    """
    app_bundle = _read_front("bundle/app.js")
    app = _read_front("app.jsx")

    glossary_pos = app_bundle.find("==== glossary.jsx ====")
    app_pos = app_bundle.find("==== app.jsx ====")

    assert glossary_pos > -1
    assert app_pos > glossary_pos
    assert "<ResearchGlossaryPanel" in app
