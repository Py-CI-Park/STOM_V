"""Frontend contract tests for strategy code, diff, and prompt inspection."""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_strategy_inspector_component_exists_and_uses_readonly_routes() -> None:
    src = _read_front("strategy-inspector.jsx")

    assert "function StrategyInspectorTabs(" in src
    assert "/strategy_diff" in src
    assert "/prompts" in src
    assert "base_gen=previous" in src
    assert "Previous Diff" in src
    assert "Prompt Timeline" in src
    assert "AI Context" in src
    assert "copy AI context" in src
    assert "prompt_count" in src
    assert "injected_features" in src
    assert "total_tokens" in src
    assert "user_text_head" in src
    assert "no-record reason" in src
    assert "no_previous_generation" in src
    assert "final_approval" not in src
    assert "export_winner" not in src


def test_code_viewer_embeds_strategy_inspector_and_unavailable_reason() -> None:
    src = _read_front("code-viewer.jsx")
    cv = src[src.find("function CodeViewer("):]

    assert "/strategy_code" in cv
    assert "<StrategyInspectorTabs" in cv
    assert "buyCode={buyCode}" in cv
    assert "sellCode={sellCode}" in cv
    assert "unavailable: strategy code not found for this generation" in src


def test_code_viewer_has_vertical_expand_reader_mode() -> None:
    """Given strategy code can be long, When viewing it, Then a vertical expand control exists."""
    src = _read_front("code-viewer.jsx")
    css = _read_front("styles.css")

    assert "code-viewer-height-toggle" in src
    assert "code-viewer-modal" in src
    assert "code-viewer-expanded" in src
    assert "aria-pressed={expandedCodeView}" in src
    assert "세로 확대" in src
    assert ".code-viewer-modal.code-viewer-expanded" in css
    assert ".code-viewer-modal.code-viewer-expanded .code-block" in css
    assert "72vh" in css


def test_index_loads_strategy_inspector_before_app() -> None:
    # 모델-무관 마이그레이션: concat 텍스트 순서(code-viewer < strategy-inspector < app)는 모듈
    #   스코프에선 무의미하므로 DROP 하고, 두 모듈이 정의하는 심볼 존재로 검증한다(concat·bundle 양쪽 통과).
    #   code-viewer→CodeViewer, strategy-inspector→StrategyInspectorTabs.
    src = _read_front("bundle/app.js")

    assert "CodeViewer" in src, "app.js 에 code-viewer(CodeViewer) 누락"
    assert "StrategyInspectorTabs" in src, "app.js 에 strategy-inspector(StrategyInspectorTabs) 누락"


def test_strategy_inspector_is_exposed_on_window() -> None:
    src = _read_front("strategy-inspector.jsx")
    tail = src[src.rfind("Object.assign(window") :]

    assert "StrategyInspectorTabs" in tail


def test_strategy_inspector_tolerates_partial_route_failures_and_shows_code() -> None:
    src = _read_front("strategy-inspector.jsx")

    assert "diffError" in src
    assert "promptsError" in src
    assert "strategy_diff route unavailable" in src
    assert "prompts route unavailable" in src
    assert "Promise.all([" not in src
    assert "Current Code" in src
    assert "buy_code" in src
    assert "sell_code" in src


def test_active_strategy_panel_is_main_page_visible_and_fetches_code_diff() -> None:
    # P5.9 분해 — ActiveStrategyPanel 본문은 panels-config.jsx, window 재노출은 panels.jsx(배럴).
    defn = _read_front("panels-config.jsx")
    barrel = _read_front("panels.jsx")
    app = _read_front("app.jsx")

    assert "function ActiveStrategyPanel(" in defn
    assert "active-strategy-panel" in defn
    assert "/strategy_code" in defn
    assert "/strategy_diff" in defn
    assert "code_status" in defn
    assert "diff_status" in defn
    assert "streaming_partial" in defn
    assert "no_strategy" in defn
    assert "Object.assign(window" in barrel
    assert "ActiveStrategyPanel" in barrel[barrel.rfind("Object.assign(window"):]
    assert "<ActiveStrategyPanel" in app
    assert "baseUrl={baseUrl}" in app
    assert "onViewCode={onViewCodeByGen}" in app


def test_research_criteria_banner_explains_oos_disabled_mode() -> None:
    # P5.9 분해 — ResearchCriteriaBanner 본문은 panels-status.jsx, window 재노출은 panels.jsx(배럴).
    defn = _read_front("panels-status.jsx")
    barrel = _read_front("panels.jsx")
    app = _read_front("app.jsx")

    assert "function ResearchCriteriaBanner(" in defn
    assert "/research_criteria" in defn
    assert "research_oos_mode" in defn
    assert "OOS disabled" in defn
    assert "research/exploration only" in defn
    assert "not proof of human-level" in defn
    assert "Object.assign(window" in barrel
    assert "ResearchCriteriaBanner" in barrel[barrel.rfind("Object.assign(window"):]
    assert "<ResearchCriteriaBanner" in app
