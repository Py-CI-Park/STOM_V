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

    Phase14.4: 운영 컴포넌트는 단일 번들 bundle/app.js. 모델-무관 마이그레이션: concat 텍스트
    순서(glossary < app)는 모듈 스코프에선 무의미하므로 DROP 하고, glossary 가 정의하는 심볼이
    산출 번들에 존재함 + app.jsx 가 패널을 마운트함으로 검증한다(concat·bundle 양쪽 통과).
    """
    app_bundle = _read_front("bundle/app.js")
    app = _read_front("app.jsx")

    # glossary.jsx → ResearchGlossaryPanel.
    assert "ResearchGlossaryPanel" in app_bundle, "app.js 에 glossary(ResearchGlossaryPanel) 누락"
    assert "<ResearchGlossaryPanel" in app
