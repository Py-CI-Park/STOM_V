"""Dashboard UI remodel contract tests.

Pins the IA contract, shared state primitives, HoF inventory gate, visual/perf planning
surface, and process-flow growth added for the 2026-06-19 remodel lane.
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_route_contract_preserves_stable_keys_and_groups() -> None:
    src = _read("ui-contract.jsx")
    top_block = src.split("const DASHBOARD_ROUTE_CONTRACTS = [", 1)[1].split("];", 1)[0]
    for key in ('"evolution"', '"backtest"', '"simulation"'):
        assert key in top_block
    assert len([ln for ln in top_block.splitlines() if "key:" in ln]) == 3

    sub_block = src.split("const EVOLUTION_SUBTAB_CONTRACTS = [", 1)[1].split("];", 1)[0]
    for key in ('"overview"', '"process"', '"records"', '"lab"', '"workbench"', '"verdict"'):
        assert key in sub_block
    assert 'tabs: ["evolution", "backtest", "simulation"]' in src
    assert 'pro: "workbench"' in src
    assert "normalizeDashboardTabKey" in src
    assert "normalizeEvolutionSubtabKey" in src
    assert 'label: "프로세스"' in src
    assert "writing-mode: vertical-rl" not in _read("styles.css").split(".stom-tabgroup-label", 1)[1].split("}", 1)[0]


def test_phase2_history_owns_result_detail_and_compare() -> None:
    result_area = _read("bt-result-area.jsx")
    charts = _read("backtest-charts.jsx")
    records = _read("research-records-panel.jsx")
    workbench = _read("rp-panel.jsx")
    contract = _read("ui-contract.jsx")
    app = _read("app.jsx")

    assert "function ResultDetailBody" in result_area
    body_block = result_area.split("function ResultDetailBody", 1)[1].split("function _BtFullscreenAnalysis", 1)[0]
    assert "_btFetchJson" not in body_block
    assert "sourceContext" in body_block
    assert "ResultDetailBody" in charts.split("Object.assign(window", 1)[1]

    records_history = records.split("히스토리 ResultDetail · Compare", 1)[1].split("{errors.length > 0", 1)[0]
    assert "<_RpRunCompare" in records_history
    assert "<_RpHistory" in records_history
    assert "History가 과거 run/gen 아카이브와 Compare를 소유합니다" in records_history

    workbench_panel = workbench.split("function ResearchProPanel", 1)[1].split("function ResearchHeatmapPanel", 1)[0]
    assert "<_RpRunCompare" not in workbench_panel
    assert "<_RpHistory" not in workbench_panel
    assert "히스토리 탭 소유" in workbench_panel
    assert "<_RpBigHeatmap" in workbench_panel
    assert "탐색 히트맵은 연구실 소유" not in workbench_panel
    assert "RunComparePanel" not in app
    assert "ResearchLabPanel" in app
    assert "Compare와 run/gen ResultDetail은 히스토리 탭에서만 렌더링합니다" in app
    assert "연구실 종합 · 탐색/변수/검증" in app

    assert 'label: "히스토리"' in contract
    assert 'history: "records"' in contract
    assert "const canonical = EVOLUTION_LEGACY_ALIASES[value] || value" in contract
    assert "dashboardPathFor(\"evolution\", sub)" in contract
    assert 'label: "조건식 AI"' in contract
    assert 'group: "조건식 AI"' in contract
    assert "조건식 AI Live Monitor" in app
    assert "설정 · 게이트 · 백테스트 엔진 요약" in app
    assert "조건식 AI 하위 탭" in app
    assert "ResearchLabPanel" in app
    assert ") : isIdle ? (" not in app
    assert "조건식 AI 시작 설정 열기" in app
    assert "STOM AI · 조건식 AI 연구 대시보드 (Legacy)" in app
    assert '{ key: "records", label: "히스토리"' in app

def test_app_shell_uses_grouped_nav_and_direct_page_imports() -> None:
    src = _read("app.jsx")
    assert 'from "./dashboard-pages.jsx"' in src
    assert "const STOM_TABS = DASHBOARD_ROUTE_CONTRACTS" in src
    assert "DASHBOARD_TAB_GROUPS.map" in src
    assert "EvolutionSubtabNav" in src
    assert "evolution-subtabnav" in src
    assert "stom-shell-context" in src
    assert "stom-tabgroup" in src
    assert "stom-tab-badge" in src
    assert "<LabPage" in src and "<ResearchIndexPage" in src
    assert "phase3-home-links" in src
    assert "configSpecStatus" in src
    assert "연구실 종합 · 탐색/변수/검증" in src
    assert "ResearchLabPanel" in src
    assert "연구 위키 · AI 컨텍스트 팩 → 연구실 탭" not in src
    research_nav = src.split('storageKey="stom_evo_researchnav"', 1)[1].split('storageKey="stom_evo_historynav"', 1)[0]
    assert 'onEvolutionSubtabSelect("workbench")' in research_nav
    assert 'onOpenWorkbench={() => setActiveTab("backtest")}' not in src
    assert "window.ResearchHeatmapPanel" not in src


def test_shared_ui_state_primitives_are_presentation_only_and_exported() -> None:
    src = _read("ui-state.jsx")
    for symbol in ("UiStateBlock", "UiInlinePill", "WorkspaceCard", "WorkspaceNav", "MetricList"):
        assert f"function {symbol}" in src
        assert symbol in src.split("Object.assign(window", 1)[1]
        assert symbol in src.split("export {", 1)[1]
    assert "fetch(" not in src and "localStorage" not in src


def test_evidence_workspace_labels_each_owner_surface() -> None:
    src = _read("dashboard-pages.jsx")
    assert "EvidenceWorkspaceHeader" in src
    assert "EvidenceWorkspaceCards" not in src
    assert "WorkspaceNav" not in src
    assert "WorkspaceCard" not in src
    assert "EVIDENCE_WORKSPACE_LINKS" not in src
    assert "evidence-workspace-head-static" in src
    assert "현재 표면: <b>{owner.owner}</b>" in src
    assert "이 표면은 현재 하위탭의 책임과 비소유 범위만 설명합니다" not in src
    assert "같은 기능 버튼이 화면 안에 다시 생기지 않도록 합니다" not in src
    assert "<Phase2InventoryPanel compact />" in src
    assert "STOM 연구실" in src
    assert "연구 위키 · AI 컨텍스트 보기" in src
    assert "연구실 내부 메뉴는 하위 탭이 아니라 분석 종류를 고르는 필터입니다" not in _read("rl-panel.jsx")
    assert "탐색 히트맵 · Edge Ratio" in _read("rl-panel.jsx")
    assert "탐색 히트맵 · Edge Ratio 통합 분석" in _read("analysis.jsx")
    assert "ResearchHeatmapPanel" not in _read("rl-panel.jsx")
    panels = _read("panels-analysis.jsx")
    app = _read("app.jsx")
    assert "function ConditionDiscoveryPanel" in panels
    assert "조건식 발굴 거버넌스" in panels
    assert "생성품질 점수" in panels
    assert "Human DB pattern cards" in panels
    assert "Research Pack / Branch Tree" in panels
    assert "context pack health" in panels
    assert "candidate pack" in panels
    assert "analysis cards" in panels
    assert "prompt receipts" in panels
    assert "fallback status" in panels
    assert "Promotion blockers" in panels
    assert "zero-generation review" in panels
    assert "authority pending/blocked" in panels
    assert "<ConditionDiscoveryPanel state={state} wsStatus={wsStatus} />" in app
    assert "workspace-owner-boundary" in src
    for active in ('activeKey="records"', 'activeKey="lab"', 'activeKey="workbench"', 'activeKey="verdict"'):
        assert active in src
    lab_section = src.split("function LabPage", 1)[1].split("function ResearchIndexPage", 1)[0]
    assert "ResearchIndexPanel" not in lab_section
    assert "VERDICT_SECTION_KEYS" in src
    assert "verdict-section-index" in src
    assert "normalizeVerdictSubtab" not in src
    assert "VERDICT_SUBTAB_KEYS" not in src



def test_g006_removes_duplicate_inner_tabs_and_pins_readability() -> None:
    pages = _read("dashboard-pages.jsx")
    lab = _read("rl-panel.jsx")
    css = _read("styles.css")

    assert 'role="tablist" aria-label="결정 이력 하위 탭"' not in pages
    assert "stom_verdict_subtab" not in pages
    assert 'vsub === "summary"' not in pages
    assert 'id="verdict-summary"' in pages
    assert 'id="verdict-decide"' in pages
    assert "verdict-glossary" in pages
    assert "verdict-example" in pages
    assert "verdictErrors" in pages
    assert "markVerdictError" in pages
    assert "missingVerdictGlobals" in pages
    assert "결정 감사 데이터 일부 로드 실패" in pages
    assert "결정 감사 공용 컴포넌트 로드 실패" in pages
    assert "proErrors" in pages
    assert "분석 워크벤치 데이터 일부 로드 실패" in pages
    assert "historyFailed" in pages
    assert "결정 이력 로드 실패" in pages
    assert "WikiPanel = window.ResearchWikiPanel" in pages
    assert "ContextPanel = window.AIContextPanel" in pages
    assert '<_DpLoading name="리서치 위키 패널" />' in pages
    assert '<_DpLoading name="AI 컨텍스트 패널" />' in pages

    assert 'role="tablist" aria-label="Research Lab"' not in lab
    assert "research-section-filter" in lab
    assert "research-filter-chip" in lab
    assert "lab-glossary" in lab
    assert "lab-example" in lab
    assert "/ui/pro.html" not in lab
    assert "onOpenWorkbench" in lab
    assert "/ui/evolution/workbench" in lab
    assert "RL_FALLBACK_PIPELINE" not in lab
    assert "_rlPipelineState" in lab
    assert "프로세스 정본 로드 실패" in lab
    assert ".filter((pair) => Array.isArray(pair) && pair.length >= 2)" in lab
    assert "오래된 로컬 fallback 프로세스는 표시하지 않습니다" in lab
    assert "명시적 변수 조합 후보가 없습니다" in lab
    assert ": matrixRows" not in lab
    assert "labErrors" in pages
    assert "연구실 데이터 일부 로드 실패" in pages
    assert "opsError" in lab
    assert "운영 상태를 불러오지 못했습니다" in lab
    assert "setOpsStrip(null);" in lab and "setOpsError(String(e));" in lab
    assert 'const labMode = opsError ? "상태 오류"' in lab
    assert "실행 없음으로 표시하지 않습니다" in lab

    assert "--fs-prose: 14px" in css
    assert ".readability-note" in css and "font-size: var(--fs-prose)" in css
    assert ".verdict-section-head p" in css and "color: var(--ink-1)" in css
    assert ".research-filter-chip," in css and ".research-filter-action" in css
    assert ".lab-glossary span," in css and ".verdict-glossary span" in css
    assert ".verdict-section-link small" in css
    for selector in (".research-filter-chip,", ".lab-glossary span,", ".lab-example,", ".verdict-section-link b", ".verdict-section-link small"):
        assert "font-size: var(--fs-prose)" in css.split(selector, 1)[1].split("}", 1)[0]
    assert ".stom-shell-title span" in css and "font-size: var(--fs-dense)" in css

def test_process_tab_documents_condition_discovery_defaults() -> None:
    src = _read("phase-detail.jsx")
    css = _read("styles.css")

    assert "PROCESS_DEFAULT_ROWS" in src
    for marker in (
        "09:00:00~09:28:00",
        "09:00~15:18/15:19",
        "최대 300초",
        "fast 35% · research 25% · promotion 15%",
        "TPI",
        "매매성능지수",
        "성과 점수 100점",
        "생성품질 100점",
        "Prompt / Equity 저장",
        "부검 hypothesis",
        "인간 DB pattern cards",
        "Transformer/ML",
    ):
        assert marker in src
    assert "process-defaults-table" in src
    assert ".process-defaults-panel" in css
    assert "상세 프로세스" in src
    assert ".process-detail-callout" in css
    for marker in (
        "PROCESS_FALLBACK_CATALOG",
        "FULL_PIPELINE_STEPS",
        "fast-discovery",
        "process-research",
        "promotion-review",
        "research_validation",
        "advisory_split",
        "can_promote",
        "can_export",
        "can_live",
        "state.page_data.condition_discovery.process",
        "state.page_data.warm_session",
        "warm metadata pending — existing display remains valid",
        "separate frozen promotion review",
        "research allowed",
        "still blocked",
        "quick start",
        "condition_improvement_loop",
        "full_period_validation",
        "review only",
        "승격 검토 전용",
    ):
        assert marker in src
    for css_marker in (
        ".process-selector-panel",
        ".process-selector-option.active",
        ".process-readout-grid",
        ".process-capability-pill.off",
        ".process-pipeline-panel",
        ".process-pipeline-step",
        ".process-warm-panel",
        ".process-warm-grid",
    ):
        assert css_marker in css


def test_process_research_heatmap_visibility_and_sizing_contracts() -> None:
    analysis = _read("analysis.jsx")
    rp_heatmap = _read("rp-heatmap.jsx")
    css = _read("styles.css")

    for marker in (
        "function _splitCrossLabel",
        "edge-heatmap-missing",
        "edge-heatmap-scroll",
        "B_시분초/B_시가총액",
        "시간대×시총 교차 히트맵",
    ):
        assert marker in analysis
    for marker in (
        "function _rpSplitCrossLabel",
        "rp-heatmap-scroll",
        "minmax(58px, 96px)",
        "시간대 \\ 시총",
    ):
        assert marker in rp_heatmap
    edge_scroll = css.split(".edge-heatmap-scroll", 1)[1].split("}", 1)[0]
    assert "max-height: 360px" in edge_scroll
    assert "overflow: auto" in edge_scroll
    assert ".edge-heatmap-missing" in css
    rp_scroll = css.split(".rp-heatmap-scroll", 1)[1].split("}", 1)[0]
    assert "max-height: 420px" in rp_scroll
    assert "overflow: auto" in rp_scroll
    rp_grid = css.split(".rp-heatmap {", 1)[1].split("}", 1)[0]
    assert "width: max-content" in rp_grid
    rp_cell = css.split(".rp-heatmap-cell {", 1)[1].split("}", 1)[0]
    assert "max-height: 48px" in rp_cell


def test_g004_editor_legacy_tools_and_variable_influence_contracts() -> None:
    library = _read("bt-tab-library.jsx")
    run = _read("bt-tab-run.jsx")
    analysis = _read("bt-tab-analysis.jsx")
    root = _read("bt-tab-root.jsx")
    mode_results = _read("bt-tab-mode-results.jsx")

    assert "editorFocus" in library
    assert "매수만 크게" in library
    assert "매도만 크게" in library
    assert "editorMinHeight = large ? 560 : 320" in library
    assert "large={editorFocus === \"buy\"}" in library and "large={editorFocus === \"sell\"}" in library
    assert "display: showBuy ? \"flex\" : \"none\"" in library
    assert "조건식 목록 조회 실패" in library
    assert "조건식 로드 실패" in library and "j && j.status === \"error\"" in library

    assert "/bt/legacy/self_vars" in run
    assert "self.vars → 스윕 빌더" in run
    assert 'setMode("sweep")' in run
    assert "setSweepRows" in run
    assert "실행 없이 미리보기" in run
    assert "index: r.index, default: r.default" in run
    assert "기본 ${r.default}" in run

    assert "/bt/backfinder/preflight" in analysis
    assert "BtBackFinderPreflightPanel" in analysis
    assert "self.tickcols" in analysis
    assert "self.tickdata" in analysis
    assert "run_enabled={String(!!data.run_enabled)}" in analysis
    assert "<BtBackFinderPreflightPanel" in root

    assert "function _btVariableInfluenceRows" in mode_results
    assert "function BtVariableInfluencePanel" in mode_results
    assert "변수 영향도 자동 분석" in mode_results
    assert "<BtVariableInfluencePanel result={mr} mode={mode} />" in mode_results
    assert "function _btSweepCombo" in mode_results
    assert "const params = item && item.params" in mode_results
    assert "return combo;" in mode_results.split("if (params && typeof params === \"object\" && !Array.isArray(params))", 1)[1].split("Object.keys(item || {})", 1)[0]
    assert 'name === "params"' in mode_results
    assert "const combo = _btSweepCombo(item)" in mode_results
    assert "_btSweepCombo" in mode_results.split("export {", 1)[1]

def test_g004_quick_start_help_texts_are_explicit() -> None:
    controls = _read("sim-tab-controls.jsx")
    assert "보유한 일일 DB 중 가장 최근 거래일을 고르고 그날 등락률 1위 종목을 자동 재생합니다." in controls
    assert "최근 거래일 후보 전체에서 일중 최대 상승률이 가장 큰 날짜·종목을 찾아 자동 재생합니다." in controls
    assert "버튼에 마우스를 올리면 선택 기준 설명이 표시됩니다." in controls
def test_phase2_inventory_gate_pins_owner_files_and_thresholds() -> None:
    src = _read("dashboard-inventory.jsx")
    for key in ('key: "research"', 'key: "backtest"', 'key: "replay"', 'key: "history"', 'key: "workbench"', 'key: "reports"'):
        assert key in src
    for alias in ('legacyAliases: ["evolution"]', 'legacyAliases: ["records", "audit", "verdict"]', 'prototypeAliases: ["catalog"]'):
        assert alias in src
    for owner_file in ("research-index.jsx", "rp-panel.jsx", "chart-hall-of-fame.jsx", "table.jsx"):
        assert owner_file in src
    assert "PHASE2_SOURCE_INVENTORY" in src
    assert "LARGE_LIST_PERF_TARGETS" in src
    assert "visibleLimit: 80" in src
    assert "duplicate_cleanup" in src
    assert "Phase2InventoryPanel" in src
    assert "pageOwnerContract" in src

def test_hof_inventory_gate_blocks_merge_without_field_contract() -> None:
    gate = _read("hof-inventory.jsx")
    chart = _read("chart-hall-of-fame.jsx")
    expected_sources = {
        "kind": "HOF_KIND_META",
        "name": "r.label",
        "total_return_krw": "r.total_return_krw",
        "total_return_pct": "r.total_return_pct",
        "annual_return_pct": "r.annual_return_pct",
        "mdd_pct": "r.mdd_pct",
        "payoff": "r.payoff",
        "daily_avg_trades": "r.daily_avg_trades",
        "max_hold": "_maxHold",
        "operating_capital_krw": "r.operating_capital_krw",
        "period": "r.period",
        "screenshots": "ReferenceGallery",
        "workbench_actions": "ResearchProPanel",
    }
    dashboard_pages = _read("dashboard-pages.jsx")
    for field, render_marker in expected_sources.items():
        assert f'key: "{field}"' in gate
        assert render_marker in chart or render_marker in dashboard_pages
    assert "annual_unreliable" in gate and "annual_unreliable" in chart
    assert "No HoF component merge" in gate
    assert "HofInventoryGate" in chart
    assert "HofInventoryGate" in _read("dashboard-pages.jsx")
    assert "<HofInventoryGate />" in _read("dashboard-pages.jsx")
    assert "HOF_FIELD_GROUPS" in gate
    assert "HOF_WORKBENCH_ACTIONS" in gate
    assert "조건 후보 열기" in gate
    assert "즉시 백테스트 연결" in gate


def test_visual_quality_surface_pins_baselines_and_perf_budgets() -> None:
    src = _read("visual-quality.jsx")
    for route in ('route: "evolution"', 'route: "records"', 'route: "process"', 'route: "hof"'):
        assert route in src
    for surface in ('surface: "records"', 'surface: "generations"', 'surface: "hof"'):
        assert surface in src
    assert "조건식 AI" in src and "프로세스" in src
    assert "no-dependency windowing" in src

def test_records_lookup_has_sort_and_windowing_controls() -> None:
    src = _read("research-index.jsx")
    assert "RIX_SORT_LABELS" in src
    assert "updated_desc" in src and "title_asc" in src and "kind_asc" in src
    assert "displayLimit" in src
    assert "더 보기" in src
    assert "detailRequestSeq" in src
    assert "research-index-pre" in src



def test_process_flow_growth_keeps_readonly_state_contract() -> None:
    src = _read("phase-detail.jsx")
    assert "process-flow-cards" in src
    assert "실시간 상태" in src
    assert "각 단계가 끝난 뒤 누적되는 실제 시간 표본" in src
    assert "ProcessFlowDiagram" in src
    assert 'from "@xyflow/react"' in src
    assert 'from "dagre"' in src
    assert "ReactFlow" in src and "dagre.layout" in src
    assert "process-explain-grid" in src
    assert "<iframe" not in src  # Process state component must remain native; app route also owns no iframe after remaining parity closure.
    assert "상태 구분" in src
    assert "단계 진행" in src
    assert "logWindow = logs.slice(-50)" in src
    css = _read("styles.css")
    assert ".react-flow__pane" in css and "z-index: 1" in css
    assert ".stom-rf-node-active" in css and ".react-flow__edge.animated path" in css
    pkg = (PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "webui-build" / "package.json").read_text(encoding="utf-8")
    assert '"@xyflow/react"' in pkg and '"dagre"' in pkg
    app_src = (PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "app.py").read_text(encoding="utf-8")
    process_route = app_src.split('@app.get("/process_flow"', 1)[1].split('@app.get("/status"', 1)[0]
    route_read_block = process_route.split("except Exception:", 1)[0]
    assert "read_text" in route_read_block
    assert "write_text" not in process_route and "subprocess" not in process_route
    process_doc = (PROJECT_ROOT / "docs" / "process_flow.html").read_text(encoding="utf-8")
    assert "쉽게 보는 조건식 발굴 루프" in process_doc
    assert "같은 좌표 양분기" not in process_doc
    assert "사후슬라이스 착시" not in process_doc
    assert "Research Prompt Context Pack → Analysis Card v2 → Multi-Hypothesis Candidate Pack" in process_doc
    assert "Promotion Review = zero-generation" in process_doc
    assert "diagnostic fallback" in process_doc
