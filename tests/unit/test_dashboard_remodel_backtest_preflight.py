from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel" / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_backtest_preflight_exports_v2_run_payload_adapter() -> None:
    app = _app_text()

    for marker in [
        "const BACKTEST_PREFLIGHT_DEFAULTS = Object.freeze({",
        "function buildBacktestRunPayload(form = {})",
        "function validateBacktestRunPayload(payload)",
        "function renderBacktestPreflightPanel()",
        "window.BacktestPreflight = {",
        "buildRunPayload: buildBacktestRunPayload",
        "validateRunPayload: validateBacktestRunPayload",
    ]:
        assert marker in app

    for payload_key in [
        "buy:",
        "sell:",
        "start:",
        "end:",
        "timeframe:",
        "engines:",
        "mode:",
        "param_space",
        "train_window_days",
        "test_window_days",
        "step_days",
        "sweep_action",
        "sweep_spec",
        "sweep_params",
        "window_days",
        "opt_method",
        "opt_objective",
    ]:
        assert payload_key in app


def test_backtest_preflight_ui_has_validation_and_confirm_gate_contract() -> None:
    app = _app_text()

    for marker in [
        'data-backtest-preflight-payload',
        'data-backtest-validation-summary',
        'data-backtest-disabled-reason',
        'data-backtest-confirm-gate',
        'data-backtest-run-payload-shape="buy|sell|start|end|timeframe|engines|mode"',
        "Reference/demo preflight only; /bt/run is not called.",
        "Invalid preflight blocks /bt/run before confirm.",
        "Live mode requires a manual confirm before POST /bt/run.",
    ]:
        assert marker in app

    assert "fetchJson('/bt/run'" not in app
    assert 'data-action="bt-run"' not in app
