from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"
THEME = REMODEL / "styles" / "theme.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_condition_detail_surface_exports_read_only_api_contracts() -> None:
    app = _text(APP)

    for marker in [
        "const ConditionDetailContracts = [",
        "function conditionDetailContext(input = {})",
        "function conditionDetailEndpoint(contract, context)",
        "function renderConditionDetailSurface(context = conditionDetailContext())",
        "const ConditionDetailAdapter = {",
        "window.ConditionDetailSurface = {",
        "contracts: ConditionDetailContracts",
        "context: conditionDetailContext",
        "endpoint: conditionDetailEndpoint",
        "render: renderConditionDetailSurface",
    ]:
        assert marker in app

    for endpoint in [
        "/strategy_code?run=&gen=",
        "/strategy_diff?run_id=&gen_no=&base_gen=previous",
        "/prompts?run_id=&gen_no=",
        "/ai_context_pack?run_id=&gen_no=",
        "/backtest_detail?run_id=&gen_no=",
    ]:
        assert endpoint in app


def test_condition_detail_surface_ui_handles_missing_and_empty_states() -> None:
    app = _text(APP)
    theme = _text(THEME)

    for marker in [
        "data-condition-detail-surface",
        "data-condition-run-gen-selector",
        "data-condition-detail-context",
        "data-condition-detail-empty",
        "data-condition-detail-api=\"/strategy_code?run=&gen=\"",
        "data-condition-detail-api=\"/strategy_diff?run_id=&gen_no=&base_gen=previous\"",
        "data-condition-detail-api=\"/prompts?run_id=&gen_no=\"",
        "data-condition-detail-api=\"/ai_context_pack?run_id=&gen_no=\"",
        "data-condition-detail-api=\"/backtest_detail?run_id=&gen_no=\"",
        "Strategy code / diff / prompt / context / backtest detail are read-only.",
        "Missing run/gen returns an empty state, not a broken inspector.",
    ]:
        assert marker in app

    for marker in [
        ".condition-detail-surface",
        ".condition-detail-grid",
        ".condition-detail-card",
        ".condition-detail-empty",
    ]:
        assert marker in theme

    assert "record_decision" not in app.split("function renderConditionDetailSurface", 1)[1].split("window.ConditionDetailSurface", 1)[0]
    assert "/bt/run" not in app.split("function renderConditionDetailSurface", 1)[1].split("window.ConditionDetailSurface", 1)[0]
