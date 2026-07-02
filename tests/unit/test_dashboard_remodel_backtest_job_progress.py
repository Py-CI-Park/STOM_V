from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel" / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_backtest_job_progress_adapter_models_ws_contract() -> None:
    app = _app_text()

    for marker in [
        "const BACKTEST_JOB_STATES = Object.freeze([",
        "function normalizeBacktestJobMessage(message = {})",
        "function backtestJobWsPath(jobId)",
        "function renderBacktestJobProgressPanel()",
        "window.BacktestJobProgress = {",
        "normalizeMessage: normalizeBacktestJobMessage",
        "jobWsPath: backtestJobWsPath",
    ]:
        assert marker in app

    for marker in [
        "pending",
        "running",
        "success",
        "error",
        "cancelled",
        "missing-job",
        "unknown-job",
        "ws-closed",
        "terminal",
    ]:
        assert marker in app


def test_backtest_job_progress_ui_is_user_gated_and_not_auto_opened() -> None:
    app = _app_text()

    for marker in [
        'data-backtest-job-progress',
        'data-backtest-ws-path="/bt/ws_job?job_id=J10235"',
        'data-backtest-terminal-state',
        'data-backtest-job-error="missing-job"',
        'data-backtest-job-error="unknown-job"',
        "WebSocket observer is manual-gated; no stream opens on page load.",
        "Result fetch waits for terminal job evidence.",
    ]:
        assert marker in app

    assert "new WebSocket(`/bt/ws_job" not in app
    assert "new WebSocket(backendUrl('/bt/ws_job" not in app
