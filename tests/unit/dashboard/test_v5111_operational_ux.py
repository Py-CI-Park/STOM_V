from __future__ import annotations

from pathlib import Path


FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _read_backend(name: str) -> str:
    return (FRONTEND.parent / name).read_text(encoding="utf-8")


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


def test_report_summary_falls_back_to_published_run_metrics_with_visible_origin() -> None:
    """보고서 메타데이터에 없으면 같은 run 의 발행 값을 쓰되, 출처를 감추지 않는다."""
    reports = _read("v4-reports.jsx")
    board = _read("report-summary-board.jsx")

    # 선택된 보고서의 run 만 조회해 넘긴다.
    assert "selectedRunId" in reports
    assert "runMeta={runMeta}" in reports
    assert "/runs?limit=500" in reports

    # 보고서 → run 기록 순서로 찾고, 출처를 값과 함께 표시한다.
    assert "function reportSummaryResolve" in board
    assert '"report"' in board and '"run"' in board and '"derived"' in board
    assert "_RS_SOURCE_LABEL" in board
    assert "연구 run 기록" in board
    assert '"origin-" + entry.origin' in board
    css = _read("v4.css")
    assert ".v4-report-summary-kpis article.origin-run" in css
    assert ".v4-report-summary-kpis article.origin-derived" in css
    # 연평균은 발행값이 없을 때만 기간으로 환산하고 파생값으로 표기한다.
    assert "riAnnualizedPct" in board
    assert "파생값" in board
    # 어디에도 없으면 여전히 미발행이다.
    assert "미발행" in board


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


def test_ab_compare_accepts_evolution_generations() -> None:
    """A/B 비교가 완료 잡 전용이면, 완주한 잡이 없는 동안에는 기능 자체를 못 쓴다."""
    api = _read_backend("backtest_api.py")
    analysis_panel = _read("bt-tab-analysis.jsx")
    root = _read("bt-tab-root.jsx")
    result_area = _read("bt-result-area.jsx")

    # 세대도 잡과 같은 스키마로 비교 페이로드를 만든다.
    assert "def _compare_side_for_run" in api
    assert "run_a: str" in api and "gen_a: Optional[int]" in api
    assert "run_b: str" in api and "gen_b: Optional[int]" in api

    # 결과 라이브러리에서 세대마다 A/B 를 고른다.
    assert "onSetCompareA" in analysis_panel and "onCompareB" in analysis_panel
    assert "canCompareB" in analysis_panel

    # 비교 키는 잡이면 job_id, 세대면 run_id/gen_no 로 갈린다.
    assert "function _btCompareParams" in root
    assert '"run_" + side' in root and '"job_" + side' in root

    # 세대 소스도 A/B 비교 지원으로 표기한다.
    evolution_block = result_area.split("evolution: {", 1)[1].split("},", 1)[0]
    assert "compare: true" in evolution_block
