"""Frontend contract tests for the research wiki browser."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_research_wiki_component_uses_docs_endpoints_and_safe_rendering() -> None:
    src = _read_front("research-wiki.jsx")

    assert "function ResearchWikiPanel(" in src
    assert "/research_docs" in src
    assert "/research_doc" in src
    assert "reference only, not live proof" in src
    assert "Good Results" in src
    assert "Methods" in src
    assert "Failed Candidates" in src
    assert "Metrics" in src
    assert "Next Experiments" in src
    assert "dangerouslySetInnerHTML" not in src
    assert ".innerHTML" not in src


def test_research_wiki_exposed_and_loaded_before_app() -> None:
    wiki = _read_front("research-wiki.jsx")
    # Phase14.4: 운영 컴포넌트는 단일 컴파일 번들 bundle/app.js — 순서는 "==== X.jsx ====" 마커.
    app_bundle = _read_front("bundle/app.js")

    assert "Object.assign(window, { ResearchWikiPanel" in wiki
    assert app_bundle.index("==== research-wiki.jsx ====") < app_bundle.index("==== app.jsx ====")


def test_app_mounts_research_wiki_panel_with_backend_context() -> None:
    src = _read_front("app.jsx")

    assert "<ResearchWikiPanel" in src
    snippet = src[src.find("<ResearchWikiPanel") : src.find("<ResearchWikiPanel") + 180]
    assert "baseUrl={baseUrl}" in snippet
    assert "wsStatus={wsStatus}" in snippet
