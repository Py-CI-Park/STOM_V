"""QSP7 거래 경로 연구가 V4 정본 화면에 배선되는지 검사한다."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_backtest_mounts_trade_path_workbench() -> None:
    source = _read("v4-backtest.jsx")
    assert 'from "./bt-trade-path-tab.jsx"' in source
    assert "<BtTradePathTab" in source


def test_pages_25_to_34_receive_the_selected_base_url() -> None:
    trade_path = _read("bt-trade-path-tab.jsx")
    research = _read("v4-research.jsx")
    settings = _read("v4-settings.jsx")

    assert "<BtAnalysisCardTab baseUrl={baseUrl} jobId={jobId}/>" in trade_path
    assert "<BtExitAxisPanel baseUrl={baseUrl}/>" in trade_path
    assert 'fetch((baseUrl || "") + path' in _read("bt-analysis-card.jsx")
    assert 'fetch((baseUrl || "") + path' in _read("bt-exit-axis.jsx")
    assert "<AiProviderStatusPanel baseUrl={baseUrl} />" in settings
    for panel in ("LoopAutonomyPanel", "LoopStandingPanel"):
        assert f"<{panel} baseUrl={{baseUrl}} />" in research
    assert "<LoopStrategyLedgerPanel baseUrl={baseUrl} reviewContext={reviewContext}" in research
    for panel in (
        "LoopPowerGaugePanel",
        "LoopResponseSurfacePanel",
        "LoopConditionDiffPanel",
        "LoopTradePairsPanel",
    ):
        assert f"<{panel} baseUrl={{baseUrl}} reviewContext={{reviewContext}}" in research


def test_v4_research_mounts_probability_research_tools_with_base_url() -> None:
    research = _read("v4-research.jsx")
    source = _read("loop-research-tools.jsx")

    assert 'from "./loop-research-tools.jsx"' in research
    assert "<LoopResearchToolsPanel baseUrl={baseUrl} />" in research
    assert "확률 연구 도구" in research and "확률 연구 도구" in source
    assert "fetch(loopRtBase(baseUrl) + path" in source


def test_probability_research_tools_are_manual_no_adoption_only() -> None:
    source = _read("loop-research-tools.jsx")

    assert 'loopRtGet(baseUrl, "/loop/research-tools")' in source
    for endpoint in (
        "/loop/research-tools/bayesian",
        "/loop/research-tools/ast",
        "/loop/research-tools/qmc",
        "/loop/research-tools/denoise",
    ):
        assert endpoint in source
    # Only the status GET is mounted automatically; all POST calls stay behind submit handlers.
    effect_block = source.split("useEffect_lrt(() =>", 1)[1].split("const updateError", 1)[0]
    assert "loadStatus();" in effect_block
    assert "loopRtPost" not in effect_block
    for handler in ("onBayesianSubmit", "onAstSubmit", "onQmcSubmit", "onDenoiseSubmit"):
        assert handler in source
    assert "no_adoption" in source
    assert "receipts" in source
    assert "진단/제안 전용" in source
    assert "OOS 판정·전략 채택·내보내기 권한이 없습니다" in source
    assert "APPROVE" in source and "statistical boundary only" in source and "전략 승인 아님" in source
    for forbidden in ("/export", "final_approval", "record_decision"):
        assert forbidden not in source
    for empty_or_error in ("상태 요청 실패", "아직 실행한 수동 진단이 없습니다", "요청 실패", "감사할 소스를 입력하세요"):
        assert empty_or_error in source


def test_probability_research_tools_match_strict_api_payload_shapes() -> None:
    source = _read("loop-research-tools.jsx")
    assert "counts: { successes, failures }" in source
    assert "limits: {" in source
    assert 'kind: "continuous"' in source
    assert "budget: loopRtClamp(qmc.count" in source
    assert 'operator: "mask_one_clause"' in source
    assert "corruption_rate" not in source
    assert "payload.posterior && payload.posterior.mean" in source
    assert "payload.pareto.entries" in source


def test_ledger_selection_publishes_shared_review_context() -> None:
    research = _read("v4-research.jsx")
    ledger = _read("loop-strategy-ledger.jsx")

    assert "const [reviewContext, setReviewContext]" in research
    assert "onSelectContext={setReviewContext}" in research
    for field in (
        "candidate_id",
        "baseline_id",
        "artifact_id",
        "study_id",
        "lane",
        "split",
        "source_hash",
    ):
        assert field in ledger


def test_replay_reads_trade_path_deep_link_context() -> None:
    source = _read("v4-replay.jsx")
    assert 'from "./bt-replay-trade-context.jsx"' in source
    assert "<BtReplayTradeContext" in source


def test_history_mounts_official_pair_evidence() -> None:
    source = _read("v4-history.jsx")
    assert 'from "./bt-trade-path-history.jsx"' in source
    assert "<BtTradePathHistory" in source


def test_trade_path_surface_discloses_authority_and_boundary() -> None:
    source = _read("bt-trade-path-tab.jsx") + _read("bt-exit-counterfactual.jsx")
    assert "진단" in source
    assert "자문" in source
    assert "정본" in source
    assert "전체청산" in source
    assert "전체청산 (HHMMSS)" in source
    assert "forced_liquidation_time" in source
    assert "/bt/trade-path/preflight" in source
    assert "/bt/trade-path/counterfactual" in source


def test_trade_path_surface_mounts_data_contract_page() -> None:
    source = _read("bt-trade-path-tab.jsx")
    contract = _read("bt-data-contract.jsx")
    assert 'from "./bt-data-contract.jsx"' in source
    assert "데이터 계약" in source
    assert "/bt/trade-path/data-contract" in source
    assert "CSV SHA256" in contract
    assert "zero_only" in contract
    assert "missing" in contract


def test_candidate_console_injects_manifest_and_never_accepts_manual_periods() -> None:
    source = _read("bt-candidate-console.jsx")
    # manifest 자동 주입 계약(P1): 기간·세션·기준선은 manifest 에서만 온다.
    assert "/bt/trade-path/lane-manifest" not in source  # manifest 는 상위(tab)가 주입
    assert "laneManifest.baseline_buy" in source
    assert "period.start" in source and "period.end" in source
    assert "session_start" in source and "session_end" in source
    # 수기 기간 입력 경로 부재: input 요소로 기간을 받지 않는다.
    assert "<input" not in source
    # 3클릭 흐름과 귀속 기록.
    assert "/bt/strategy" in source
    assert "/bt/run" in source
    assert "/bt/trade-path/candidate-runs" in source
    assert "자동 채택 아님" in source


def test_workbench_lane_switch_isolates_lanes_and_mounts_console() -> None:
    source = _read("bt-trade-path-tab.jsx")
    assert 'from "./bt-candidate-console.jsx"' in source
    assert "/bt/trade-path/lane-manifest" in source
    assert "resetForLane" in source
    # 레인과 다른 timeframe job 은 목록에서 제외된다.
    assert '=== lane' in source or "row.spec.timeframe) || \"min\") === lane" in source
    assert "tp-lane-badge" in source
    assert "후보 실행" in source


def test_oos_gate_prefills_from_attributed_candidate_runs() -> None:
    source = _read("bt-oos-gate.jsx")
    assert "/bt/trade-path/candidate-runs" in source
    assert "귀속" in source
    assert "candidate_id" in source


def test_recovery_insight_page_gates_by_fdr_and_marks_labels_research_only() -> None:
    source = _read("bt-recovery-insight.jsx")
    tab = _read("bt-trade-path-tab.jsx")
    assert "/bt/trade-path/recovery-insight" in source
    assert "passes_fdr" in source and "fold_consistent" in source
    assert "조건식 입력으로 사용하지 않습니다" in source
    assert "판별력 있는 변수가 없습니다" in source  # 0건도 결과로 표시
    assert "회복 판별" in tab and "<BtRecoveryInsight" in tab


def test_calibration_page_accumulates_and_never_fakes_virtual_deltas() -> None:
    source = _read("bt-calibration.jsx")
    tab = _read("bt-trade-path-tab.jsx")
    assert "/bt/trade-path/calibration" in source
    assert "미기록" in source  # 가상 delta 부재를 숫자로 꾸미지 않는다
    assert "캘리브레이션" in tab and "<BtCalibration" in tab


def test_sell_anatomy_auto_summary_uses_observational_language_only() -> None:
    source = _read("bt-trade-path-tab.jsx")
    assert "관찰 결과이며 이 조건을 제거한 효과가 아닙니다" in source
    # 인과 표현 금지: "제거하면 ~ 개선" 류 문구가 화면 문자열에 없어야 한다.
    assert "제거하면" not in source


def test_every_workbench_failure_path_speaks_korean_guidance() -> None:
    tab = _read("bt-trade-path-tab.jsx")
    messages = _read("bt-tp-messages.jsx")
    # 모든 setError 경로가 한국어 사전(_tpKo)을 통과한다 — 날 것 사유 노출 금지.
    assert tab.count("setError(") == tab.count("setError(_tpKo(") + tab.count('setError("")')
    # 대표 사유들이 조치 안내를 갖는다.
    for reason in ("market_path_missing", "backtest_result_not_ready",
                   "cohort_too_small", "design_oos_period_overlap"):
        assert reason in messages
    assert "확인하세요" in messages


def test_wizard_shows_next_condition_for_every_step() -> None:
    tab = _read("bt-trade-path-tab.jsx")
    messages = _read("bt-tp-messages.jsx")
    assert "_tpNextHint" in tab
    for view in ("data", "entry", "summary", "path", "counterfactual", "insight",
                 "proposals", "console", "official", "oos", "calibration", "ledger"):
        assert f'{view}:' in messages or f'"{view}"' in messages


def test_preflight_surfaces_uncovered_dates_warning() -> None:
    tab = _read("bt-trade-path-tab.jsx")
    assert "uncovered_dates" in tab
    assert "데이터 없는 날짜" in tab


def test_ledger_browser_mounts_with_entities() -> None:
    source = _read("bt-ledger-browser.jsx")
    tab = _read("bt-trade-path-tab.jsx")
    assert "/bt/trade-path/ledger" in source
    assert "rebuild" in source
    assert "<BtLedgerBrowser" in tab and "원장" in tab


def test_axis_switch_routes_to_the_matching_candidate_page() -> None:
    tab = _read("bt-trade-path-tab.jsx")
    assert "tp-axis-switch" in tab
    assert "매수 축" in tab and "매도 축" in tab
    assert 'from "./bt-buy-filters.jsx"' in tab
    assert "<BtBuyFilters" in tab
    # 축을 바꾸면 후보 선택 상태를 초기화한다(교차 오염 방지).
    assert "setSelectedFilter(null)" in tab


def test_buy_filter_cards_always_disclose_entry_retention() -> None:
    source = _read("bt-buy-filters.jsx")
    assert "/bt/trade-path/buy-filters" in source
    assert "기대 진입 유지율" in source
    assert "건당 엣지" in source          # 거래 축소형 가짜 개선 경고
    assert "이것도 결과입니다" in source   # 0건도 결과
    assert "추정하지 않음" in source or "제외된 변수" in source


def test_console_and_gate_are_axis_aware() -> None:
    console = _read("bt-candidate-console.jsx")
    gate = _read("bt-oos-gate.jsx")
    # 한 라운드 한 축: 매수 축이면 매수식이 후보, 매도식은 기준선 고정.
    assert 'axis === "buy" ? strategyName : laneManifest.baseline_buy' in console
    assert 'kind: axis' in console
    assert "axis," in gate or "axis: axis" in gate
    assert "거래 유지" in gate


def test_official_run_form_sends_intraday_session_boundary() -> None:
    source = _read("bt-tab-run.jsx")
    assert "start_time" in source
    assert "end_time" in source
    assert "전체청산" in source


def test_trade_path_surface_mounts_entry_variable_autopsy() -> None:
    source = _read("bt-trade-path-tab.jsx")
    entry = _read("bt-entry-autopsy.jsx")
    assert 'from "./bt-entry-autopsy.jsx"' in source
    assert "매수 해부" in source
    assert "/bt/analysis/leaf_matrix" in entry
    assert "/bt/analysis/feature_map" in entry
    assert "모든 B_*" in entry
    assert "R_*·S_*는 매수 입력으로 사용하지 않습니다" in entry


def test_sell_dsl_trace_is_a_distinct_bounded_advisory_page() -> None:
    source = _read("bt-sell-dsl-trace.jsx")
    tab = _read("bt-trade-path-tab.jsx")
    assert "/bt/trade-path/sell-dsl-trace" in source
    assert "전체청산 이전까지만" in source
    assert "지원하지 않는 변수·함수는 임의 값으로 추측하지 않습니다" in source
    assert '"sell-trace","매도식 추적"' in tab


def test_sell_proposal_cards_disclose_family_and_timeframe() -> None:
    source = _read("bt-condition-proposals.jsx")
    assert 'row.family || "연구군"' in source
    assert 'row.timeframe || "unknown"' in source


def test_oos_page_requires_two_official_non_overlapping_pairs() -> None:
    """채택 게이트는 두 구간 공식 결과를 요구한다 — v2 분할 모드와 4-job 모드 모두."""
    source = _read("bt-oos-gate.jsx")
    tab = _read("bt-trade-path-tab.jsx")
    styles = _read("trade-path.css")
    assert "/bt/trade-path/promotion-gate" in source
    assert "비중첩" in source                      # 4-job 모드의 비중첩 요구
    assert "채택 판정" in source
    assert '["oos","채택 게이트"]' in tab
    assert '· ${job.job_id}`' in source
    assert ".tp-oos-form select" in styles


def test_oos_page_offers_both_v2_split_and_four_job_modes() -> None:
    """v2 는 연속 1회 런을 날짜로 가른다 — 자본 연속 경고와 검산 표시가 함께 있어야 한다."""
    source = _read("bt-oos-gate.jsx")
    assert "design_period" in source and "holdout_period" in source
    assert "baseline_job_id" in source and "candidate_job_id" in source
    assert "design_baseline_job_id" in source     # 4-job 모드 유지
    assert "홀드아웃" in source
    assert "자본이 이어지므로" in source
    assert "split_reconciled" in source
    assert ".tp-oos-modes" in _read("trade-path.css")


def test_trade_path_polling_continues_after_an_unchanged_progress_response() -> None:
    source = _read("bt-trade-path-tab.jsx")
    assert "}, [baseUrl, analysisId, analysis]);" in source
    assert "analysis && analysis.progress" not in source


def test_trade_path_time_formatter_handles_tick_and_min_timestamps() -> None:
    source = _read("bt-trade-path-chart.jsx")
    assert "text.length === 12" in source
    assert "text.length === 14" in source


def test_reports_wiki_indexes_quant_scoring_pipeline() -> None:
    research_api = (ROOT / "ai_strategy_loop" / "dashboard" / "research_api.py").read_text(encoding="utf-8")
    research_index = (ROOT / "ai_strategy_loop" / "dashboard" / "research_index.py").read_text(encoding="utf-8")
    assert "docs/research/quant_scoring_pipeline" in research_api
    assert "docs/research/quant_scoring_pipeline" in research_index
