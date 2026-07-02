from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"


def _text(relative_path: str) -> str:
    return (REMODEL / relative_path).read_text(encoding="utf-8")


def test_task_frame_renders_shared_functional_state_strip() -> None:
    # Given: every V3 page enters through the shared task frame.
    app = _text("src/app.js")
    theme = _text("styles/theme.css")

    # When/Then: the frame exposes one shared state vocabulary and page state map.
    for marker in [
        "function functionalStateStrip(pageId, config = {})",
        "const UX_PAGE_KEY_ALIASES = {",
        "chart_replay: 'replay'",
        "RemodelStatusVocabulary.map(status =>",
        "data-functional-state-strip=",
        "data-state-vocabulary=",
        "data-state-token=",
        "${functionalStateStrip(pageId, config)}",
    ]:
        assert marker in app

    for marker in [
        ".functional-state-strip",
        ".state-token",
        ".page-state-chip",
    ]:
        assert marker in theme


def test_task_frame_copy_is_constrained_for_narrow_viewports() -> None:
    # Given: Korean task titles can be longer than the narrow mobile viewport.
    theme = _text("styles/theme.css")

    # When/Then: the shared task frame keeps copy and field text inside the panel.
    for marker in [
        ".task-frame-copy",
        ".task-frame h2",
        "overflow-wrap: anywhere;",
        "line-break: anywhere;",
        ".task-field b",
    ]:
        assert marker in theme
