from __future__ import annotations

from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
APP = REPO / "ai_strategy_loop" / "dashboard" / "frontend" / "remodel" / "src" / "app.js"


def _app_text() -> str:
    return APP.read_text(encoding="utf-8")


def test_backtest_analysis_surface_lists_v2_result_endpoints() -> None:
    app = _app_text()

    for marker in [
        "const BACKTEST_ANALYSIS_SURFACES = Object.freeze([",
        "function renderBacktestAnalysisSurface()",
        "window.BacktestAnalysisSurface = {",
        "surfaces: BACKTEST_ANALYSIS_SURFACES",
        "data-backtest-analysis-surface",
    ]:
        assert marker in app

    for endpoint in [
        "/bt/result?job_id=__demo__",
        "/bt/analysis/summary?job_id=",
        "/bt/analysis/equity?job_id=",
        "/bt/analysis/distribution?job_id=",
        "/bt/analysis/heatmap?job_id=",
        "/bt/analysis/underwater?job_id=",
        "/bt/analysis/insights?job_id=",
        "/bt/analysis/mae_mfe?job_id=",
        "/bt/analysis/exit_reasons?job_id=",
        "/bt/analysis/montecarlo?job_id=",
        "/bt/analysis/orderflow?job_id=",
        "/bt/analysis/gui_parity?job_id=",
        "/bt/compare?job_a=&job_b=",
        "/bt/overlay?job_ids=",
        "/bt/report?job_id=",
    ]:
        assert endpoint in app


def test_backtest_analysis_ui_has_empty_compare_and_report_states() -> None:
    app = _app_text()

    for marker in [
        'data-backtest-result-empty',
        'data-backtest-compare-disabled-reason',
        'data-backtest-report-state',
        'No completed job selected; analysis calls remain disabled.',
        'Need two completed job ids before compare.',
        'Report opens only for existing completed job evidence.',
    ]:
        assert marker in app

    assert "fetchJson('/bt/analysis" not in app
    assert "fetchJson('/bt/compare" not in app
