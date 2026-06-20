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
    assert "EvidenceWorkspaceCards" in src
    assert "OWNER MATRIX" in src
    assert "Records는 전체 조회" in src
    assert "분석 워크벤치는 후보 분석" in src
    assert "append-only trail" in src
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
    assert "setOpsStrip(null); setOpsError" in lab
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

def test_phase2_inventory_gate_pins_owner_files_and_thresholds() -> None:
    src = _read("dashboard-inventory.jsx")
    for key in ('key: "evolution"', 'key: "process"', 'key: "records"', 'key: "pro"', 'key: "verdict"'):
        assert key in src
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
    assert "진화 홈" in src and "프로세스" in src
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
    assert "<iframe" not in src  # iframe remains app.jsx route chrome, not process component state mutation.
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
