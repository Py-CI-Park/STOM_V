from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REMODEL = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel"
APP = REMODEL / "src" / "app.js"
THEME = REMODEL / "styles" / "theme.css"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_whole_process_workflow_rail_and_shared_context_exports() -> None:
    app = _text(APP)

    for marker in [
        "const REMODEL_WORKFLOW_STEPS = [",
        "function workflowStepForState()",
        "function currentWorkflowContext(input = {})",
        "function renderWorkflowRail()",
        "function renderSharedContextStrip(context = currentWorkflowContext())",
        "window.RemodelWorkflowUX = {",
        "steps: REMODEL_WORKFLOW_STEPS",
        "workflowStepForState",
        "currentWorkflowContext",
        "renderWorkflowRail",
        "renderSharedContextStrip",
    ]:
        assert marker in app

    for workflow in [
        "Overview",
        "Condition AI",
        "Backtest",
        "Chart Replay",
        "Audit/Decision",
        "Settings",
    ]:
        assert workflow in app


def test_whole_process_ui_markers_and_responsive_styles() -> None:
    app = _text(APP)
    theme = _text(THEME)

    for marker in [
        "data-workflow-rail",
        "data-workflow-step=",
        "data-workflow-route=",
        "/ui/remodel/backtest",
        "/ui/remodel/chart-replay",
        'data-workflow-action="settings"',
        "data-shared-context-strip",
        "data-context-run-gen",
        "data-context-strategy",
        "data-context-symbol-date",
        "data-context-decision",
        "data-primary-action-slot",
    ]:
        assert marker in app

    for marker in [
        ".workflow-rail",
        ".workflow-step",
        ".workflow-step.active",
        ".shared-context-strip",
        ".context-chip",
    ]:
        assert marker in theme

    shell_block = app.split("function renderShell", 1)[1].split("function attachShellEvents", 1)[0]
    assert "renderWorkflowRail()" in shell_block
    assert "renderSharedContextStrip()" in shell_block
    assert "new WebSocket" not in shell_block
    assert "/bt/run" not in shell_block
