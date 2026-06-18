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
    # 모델-무관: concat 텍스트 순서(research-wiki < app) DROP — 모듈 스코프에선 무의미.
    #   research-wiki 가 window 에 노출(소스 계약) + 정의 심볼이 산출 번들에 존재함으로 검증
    #   (concat·bundle 양쪽 통과).
    app_bundle = _read_front("bundle/app.js")

    assert "Object.assign(window, { ResearchWikiPanel" in wiki
    assert "ResearchWikiPanel" in app_bundle, "app.js 에 research-wiki(ResearchWikiPanel) 누락"


def test_app_mounts_research_wiki_panel_with_backend_context() -> None:
    # P2(2026-06-14): ResearchWiki 의 홈은 연구실 탭(dashboard-pages.jsx LabPage) — 진화 사이드바에서 제거.
    #   새 마운트 사이트는 _dpBase 정규화 baseUrl(base) + 무WS 탭의 wsStatus="na"(백엔드 컨텍스트 props).
    src = _read_front("dashboard-pages.jsx")

    assert "<ResearchWikiPanel" in src
    snippet = src[src.find("<ResearchWikiPanel") : src.find("<ResearchWikiPanel") + 180]
    assert "baseUrl={base}" in snippet
    assert 'wsStatus="na"' in snippet
