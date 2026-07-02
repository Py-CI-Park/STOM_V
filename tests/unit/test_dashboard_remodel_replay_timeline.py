from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"
THEME = REMODEL / "styles" / "theme.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_replay_timeline_exports_shared_cursor_and_handoff_adapter() -> None:
    app = _text(APP)

    for marker in [
        "const REPLAY_TIMELINE_EMPTY_TEXT",
        "function replayTimelineCursor(payload = {})",
        "function replayTimelineHandoffContext(input = {})",
        "function renderReplayTimelineSurface(data = {}, selectedStock = {})",
        "window.ReplayTimeline = {",
        "normalizeCursor: replayTimelineCursor",
        "handoffContext: replayTimelineHandoffContext",
        "render: renderReplayTimelineSurface",
    ]:
        assert marker in app

    for marker in [
        "bars",
        "signals",
        "trades",
        "positions",
        "logs",
        "selectedIndex",
        "selectedTime",
        "selectedCode",
        "prefillReady",
    ]:
        assert marker in app


def test_replay_timeline_ui_has_empty_states_and_backtest_handoff_context() -> None:
    app = _text(APP)
    theme = _text(THEME)

    for marker in [
        "data-replay-timeline-surface",
        'data-replay-cursor-source="shared"',
        "data-replay-timeline",
        'data-replay-event-kind="signal"',
        'data-replay-event-kind="trade"',
        'data-replay-event-kind="position"',
        "data-replay-empty-signals",
        "data-replay-empty-trades",
        "data-replay-selected-detail",
        "data-replay-backtest-handoff",
        'data-replay-handoff-source="bt-result-localStorage-event"',
        "Backtest result handoff prefill",
        "No signal/trade data for selected replay cursor.",
    ]:
        assert marker in app

    for marker in [
        ".replay-timeline-surface",
        ".replay-event-timeline",
        ".replay-event-item",
        ".replay-detail-grid",
        ".replay-empty-state",
    ]:
        assert marker in theme
