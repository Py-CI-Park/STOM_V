from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel" / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_replay_playback_exports_ws_action_and_message_adapter() -> None:
    app = _app_text()

    for marker in [
        "const REPLAY_PLAYBACK_STATES = Object.freeze([",
        "function replayWsActionPayload(action, patch = {})",
        "function normalizeReplayWsMessage(message = {})",
        "function renderReplayPlaybackControls()",
        "window.ReplayPlayback = {",
        "actionPayload: replayWsActionPayload",
        "normalizeMessage: normalizeReplayWsMessage",
    ]:
        assert marker in app

    for marker in [
        "playing",
        "paused",
        "done",
        "error",
        "over-limit",
        "meta",
        "bars",
        "history",
    ]:
        assert marker in app


def test_replay_playback_ui_is_manual_gated() -> None:
    app = _app_text()

    for marker in [
        'data-replay-playback-controls',
        'data-replay-ws-action="start"',
        'data-replay-ws-action="pause"',
        'data-replay-ws-action="resume"',
        'data-replay-ws-action="speed"',
        'data-replay-ws-action="seek"',
        'data-replay-ws-action="stop"',
        'data-replay-ws-message-kind',
        "Playback controls build /sim/ws messages only after manual start.",
        "Over session limit remains visible as error state.",
    ]:
        assert marker in app

    assert "new WebSocket(`/sim/ws" not in app
    assert "new WebSocket(backendUrl('/sim/ws" not in app
