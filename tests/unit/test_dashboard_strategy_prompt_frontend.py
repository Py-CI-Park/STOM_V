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


def test_index_loads_strategy_inspector_before_app() -> None:
    src = _read_front("index.html")

    code_viewer_pos = src.index("code-viewer.jsx")
    inspector_pos = src.index("strategy-inspector.jsx")
    app_pos = src.index("app.jsx")
    assert code_viewer_pos < inspector_pos < app_pos


def test_strategy_inspector_is_exposed_on_window() -> None:
    src = _read_front("strategy-inspector.jsx")
    tail = src[src.rfind("Object.assign(window") :]

    assert "StrategyInspectorTabs" in tail
