from __future__ import annotations

from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_live_strategy_code_and_diff_have_independent_resilient_requests() -> None:
    source = _read("panels-config.jsx")
    viewer = _read("code-viewer.jsx")

    assert "const CONDITION_FETCH_TIMEOUT_MS = 10000;" in source
    assert "codeFetchError" in source
    assert "diffFetchError" in source
    assert "조건식 변경 비교 지연" in source
    assert "CONDITION_FETCH_TIMEOUT_MS" in viewer


def test_backtest_result_layout_restores_explicit_two_three_four_columns() -> None:
    result = _read("bt-result-area.jsx")
    history = _read("v4-history.jsx")
    settings = _read("v4-settings.jsx")

    assert 'const _BT_RESULT_LAYOUTS = ["2", "3", "4"];' in result
    assert '_btStoredPreference(_BT_RESULT_LAYOUT_KEY, "3")' in result
    assert "Math.floor((available + 12) / 360)" in result
    assert 'return Math.min(Number(layout), maxColumns);' in result
    assert 'const HISTORY_RESULT_LAYOUTS = ["2", "3", "4"];' in history
    assert 'return "3";' in history
    assert "기본 3열" in settings


def test_backtest_result_can_open_latest_valid_evolution_generation() -> None:
    selector = _read("bt-tab-analysis.jsx")
    root = _read("bt-tab-root.jsx")

    assert "autoPickedRunRef" in selector
    assert "items.findLast" in selector
    assert "최신 유효 세대 자동 선택" in selector
    assert 'title="진화 세대 결과 라이브러리"' in root
    assert "defaultOpen={true}" in root


def test_backtest_defaults_are_quarter_cpu_and_editors_show_more_code() -> None:
    run = _read("bt-tab-run.jsx")
    editor = _read("bt-tab-library.jsx")

    assert "function _btDefaultEngineCount()" in run
    assert "hardwareConcurrency" in run
    assert "* 0.25" in run
    assert "useState_bt(_btDefaultEngineCount)" in run
    assert "large ? 720 : 500" in editor


def test_replay_close_does_not_overwrite_specific_protocol_error() -> None:
    source = _read("sim-tab-root.jsx")

    assert "replayErrorReportedRef" in source
    assert "if (isActive && noFrames && !replayErrorReportedRef.current)" in source
    assert "종료 코드" in source


def test_replay_refreshes_an_expired_shell_session_before_opening_websocket() -> None:
    root = _read("sim-tab-root.jsx")
    utils = _read("sim-tab-utils.jsx")

    assert "async function _simRefreshReplaySession" in utils
    assert "_simRefreshReplaySession" in root
    assert "await _simRefreshReplaySession(baseUrl)" in root
    assert root.index("await _simRefreshReplaySession(baseUrl)") < root.index("new WebSocket(url)")


def test_backtest_job_archive_does_not_present_unopenable_terminal_rows_as_results() -> None:
    source = _read("bt-tab-run.jsx")

    assert "function _btJobOpenable" in source
    assert "analysisReadyCount" in source
    assert "showTerminalArchive" in source
    assert "terminalArchiveCount" in source


def test_backtest_charts_are_independent_flat_equal_matrix_cards() -> None:
    result = _read("bt-result-area.jsx")
    parity = _read("bt-gui-parity.jsx")
    quant = _read("bt-quant.jsx")
    css = _read("v4.css")

    assert 'className="bt-analysis-matrix"' in result
    assert "bt-result-diagnostics-title" not in result
    assert "bt-cadence-diagnostic" not in result
    assert "bt-gui-parity-group" not in parity
    assert quant.count('className="panel bt-equal-card bt-quant-card"') == 4
    assert ".bt-analysis-matrix" in css
    assert "--bt-analysis-card-height" in css


def test_history_is_a_research_first_drilldown_without_decision_ledger() -> None:
    source = _read("v4-history.jsx")

    assert "AuditDecisionTrace" not in source
    assert "VerdictPanel" not in source
    assert "historyStage" in source
    assert "data-history-stage={stage}" in source
    assert '["research", "1"' in source
    assert '["results", "2"' in source
    assert '["detail", "3"' in source
    assert '["evidence", "4"' in source
    assert 'onNavigate("reports")' in source


def test_reports_and_performance_add_data_backed_visual_summary_surfaces() -> None:
    reports = _read("v4-reports.jsx")
    report_summary = _read("report-summary-board.jsx")
    hall = _read("chart-hall-of-fame.jsx")
    performance = _read("hof-performance-overview.jsx")

    assert "ReportSummaryBoard" in reports
    assert 'reportView === "summary"' in reports
    assert "annual_return_pct" in report_summary
    assert "daily_avg_trades" in report_summary
    assert "max_hold_count" in report_summary
    assert "HofPerformanceOverview" in hall
    assert "performance-scatter" in performance
    assert "performance-distribution" in performance


def test_settings_and_glossary_use_one_equal_dashboard_panel_contract() -> None:
    css = _read("v4.css")

    assert "--dashboard-utility-card-height" in css
    assert ".v4-settings > .panel," in css
    assert ".v4g-grid > .panel" in css


def test_live_matrices_logs_and_evolution_visuals_are_explicit() -> None:
    research = _read("v4-research.jsx")
    evolution = _read("evolution-analysis.jsx")
    css = _read("v4.css")

    assert "best 손익" in research
    assert "best 거래" in research
    assert 'className="v6-log-console"' in research
    assert "현재 단계 상세 로그" in research
    assert "function EaGateTrendChart(" in evolution
    assert "function EaEfficiencyChart(" in evolution
    assert ".v59-matrix" in css
    assert ".v6-log-console" in css
    # Auto tracks keep cards equal within each matrix row without stretching every
    # later row to the tallest analytics panel on the page.
    assert "grid-auto-rows: auto" in css


def test_reports_catalog_and_settings_use_readable_full_width_contracts() -> None:
    reports = _read("v4-reports.jsx")
    catalog = _read("v4-catalog.jsx")
    css = _read("v4.css")

    assert 'className="v4-report-filter-step"' in reports
    assert 'className="v4-report-details"' in reports
    assert "프로필" in reports and "제약·주의" in reports
    assert 'className="v4-cat-viewdesc"' in catalog
    assert ".v4-settings {" in css and "max-width: none" in css
    assert ".v4-catalog-table" in css and "font-size: 13px" in css
