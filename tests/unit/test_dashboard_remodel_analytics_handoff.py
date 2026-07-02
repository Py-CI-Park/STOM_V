from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"
THEME = REMODEL / "styles" / "theme.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_analytics_handoff_exports_read_only_endpoints_and_payload_builders() -> None:
    app = _text(APP)

    for marker in [
        "const ANALYTICS_HANDOFF_ENDPOINTS = Object.freeze([",
        "function analyticsHandoffContext(input = {})",
        "function buildConditionToBacktestHandoff(context = analyticsHandoffContext())",
        "function buildBacktestToReplayHandoff(input = {})",
        "function validateAnalyticsHandoff(context = analyticsHandoffContext())",
        "function renderAnalyticsHandoffSurface(context = analyticsHandoffContext())",
        "window.AnalyticsHandoffSurface = {",
        "context: analyticsHandoffContext",
        "conditionToBacktest: buildConditionToBacktestHandoff",
        "backtestToReplay: buildBacktestToReplayHandoff",
        "validate: validateAnalyticsHandoff",
        "render: renderAnalyticsHandoffSurface",
    ]:
        assert marker in app

    for endpoint in [
        "/edge_ratio?run_ids=",
        "/feature_importance?run_id=&gen_no=",
        "/variable_correlation?run_id=&gen_no=",
    ]:
        assert endpoint in app


def test_analytics_handoff_ui_is_prefill_only_and_handles_incomplete_context() -> None:
    app = _text(APP)
    theme = _text(THEME)

    for marker in [
        "data-analytics-handoff-surface",
        'data-analytics-endpoint="/edge_ratio?run_ids="',
        'data-analytics-endpoint="/feature_importance?run_id=&gen_no="',
        'data-analytics-endpoint="/variable_correlation?run_id=&gen_no="',
        "data-condition-to-backtest-handoff",
        "data-backtest-to-replay-handoff",
        "data-handoff-disabled-reason",
        'data-handoff-route="/ui/remodel/backtest"',
        'data-handoff-route="/ui/remodel/chart-replay"',
        "Incomplete context disables handoff actions.",
        "No auto-run; handoff only pre-fills the next workflow.",
    ]:
        assert marker in app

    for marker in [
        ".analytics-handoff-surface",
        ".analytics-endpoint-grid",
        ".analytics-handoff-grid",
        ".analytics-handoff-card",
    ]:
        assert marker in theme

    surface_block = app.split("function renderAnalyticsHandoffSurface", 1)[1].split("window.AnalyticsHandoffSurface", 1)[0]
    assert "localStorage.setItem" not in surface_block
    assert "new WebSocket" not in surface_block
