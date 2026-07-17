from __future__ import annotations

from pathlib import Path

from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402



REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_whole_flow_exports_all_v2_parity_surfaces_and_handoffs() -> None:
    app = _app_text()

    for marker in [
        "window.ConditionDetailSurface = {",
        "window.AnalyticsHandoffSurface = {",
        "window.BacktestPreflight = {",
        "window.BacktestJobProgress = {",
        "window.BacktestAnalysisSurface = {",
        "window.ReplayPreflight = {",
        "window.ReplayPlayback = {",
        "window.ReplayTimeline = {",
        "window.DecisionAuditSurface = {",
        "window.RemodelWorkflowUX = {",
        "function buildConditionToBacktestHandoff(context = analyticsHandoffContext())",
        "function buildBacktestToReplayHandoff(input = {})",
        "function decisionAuditDraftContext(input = {})",
        "function renderSharedContextStrip(context = currentWorkflowContext())",
    ]:
        assert marker in app

    for marker in [
        "data-condition-to-backtest-handoff",
        "data-backtest-to-replay-handoff",
        "data-record-decision-payload",
        "data-shared-context-strip",
        "data-workflow-rail",
    ]:
        assert marker in app


def test_whole_flow_mutations_and_streams_remain_manual_gated() -> None:
    app = _app_text()

    for marker in [
        "/bt/run",
        "/sim/ws",
        "/record_decision",
        "Live mode requires a manual confirm before POST /bt/run.",
        "Playback controls build /sim/ws messages only after manual start.",
        "Append-only record only; this does not export or place orders.",
        "final approval remains separate from /record_decision.",
    ]:
        assert marker in app

    forbidden_auto_invocations = [
        "fetchJson('/bt/run'",
        "fetchJson('/bt/portfolio'",
        "new WebSocket(`/sim/ws",
        "new WebSocket(backendUrl('/sim/ws",
        "final_approval",
        'data-action="live-order"',
        'data-action="broker-login"',
        'data-action="account-trade"',
    ]
    for marker in forbidden_auto_invocations:
        assert marker not in app


def test_condition_panel_separates_safe_empty_from_api_error() -> None:
    app = _app_text()
    condition_block = app.split("const ConditionDetailAdapter = {", 1)[1].split("window.ConditionDetailSurface", 1)[0]

    for marker in [
        "markConditionDetailEvidence(contract.id, 'EMPTY', context.reason)",
        "markConditionDetailEvidence(contract.id, 'LIVE ERROR', e.message || 'request failed')",
        "Missing run/gen returns an empty state, not a broken inspector.",
        "data-condition-detail-empty",
    ]:
        assert marker in condition_block or marker in app


def test_ops_default_routes_do_not_flip_while_v3_parity_flow_is_explicit() -> None:
    from ai_strategy_loop.dashboard.app import create_app

    client = authorized_dashboard_client(create_app())
    v2 = client.get("/ui/backtest", follow_redirects=False)
    assert v2.status_code == 200
    assert v2.headers["x-stom-dashboard-version"] == "v4-ops"
    assert "/ui/bundle/app.js" in v2.text
    assert "/ui/remodel/src/app.js" not in v2.text

    v3 = client.get("/ui/remodel/backtest", follow_redirects=False)
    assert v3.status_code == 200
    assert v3.headers["x-stom-dashboard-version"] == "v3-remodel"
    assert "/ui/remodel/src/app.js?v=20260628canonical" in v3.text
    assert "/ui/bundle/app.js" not in v3.text
