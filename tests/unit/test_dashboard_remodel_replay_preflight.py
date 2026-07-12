from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel" / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_replay_preflight_exports_v2_start_payload_adapter() -> None:
    app = _app_text()

    for marker in [
        "const REPLAY_PREFLIGHT_DEFAULTS = Object.freeze({",
        "function buildReplayStartPayload(form = {})",
        "function validateReplayStartPayload(payload)",
        "function renderReplayPreflightPanel()",
        "window.ReplayPreflight = {",
        "buildStartPayload: buildReplayStartPayload",
        "validateStartPayload: validateReplayStartPayload",
    ]:
        assert marker in app

    for payload_key in [
        "action: 'start'",
        "date:",
        "src:",
        "codes:",
        "speed:",
        "agg_sec:",
        "buy:",
        "sell:",
    ]:
        assert payload_key in app


def test_replay_preflight_ui_blocks_missing_dataset_before_ws() -> None:
    app = _app_text()

    for marker in [
        'data-replay-preflight-payload',
        'data-replay-dataset-selector',
        'data-replay-disabled-reason',
        'data-replay-start-gate',
        'data-replay-start-payload-shape="action|date|src|codes|speed|agg_sec|buy|sell"',
        "Missing date/code blocks /sim/ws start before confirm.",
        "Reference/demo replay preflight only; /sim/ws is not opened.",
    ]:
        assert marker in app

    assert "new WebSocket(`/sim/ws" not in app
    assert "new WebSocket(backendUrl('/sim/ws" not in app
