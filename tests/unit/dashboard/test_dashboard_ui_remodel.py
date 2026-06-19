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
    for key in (
        '"evolution"',
        '"process"',
        '"backtest"',
        '"simulation"',
        '"records"',
        '"lab"',
        '"pro"',
        '"verdict"',
    ):
        assert key in src
    assert 'tabs: ["evolution", "process"]' in src
    assert 'tabs: ["records", "lab"]' in src
    assert 'tabs: ["pro", "verdict"]' in src
    assert "normalizeDashboardTabKey" in src


def test_app_shell_uses_grouped_nav_and_direct_page_imports() -> None:
    src = _read("app.jsx")
    assert 'from "./dashboard-pages.jsx"' in src
    assert "const STOM_TABS = DASHBOARD_ROUTE_CONTRACTS" in src
    assert "DASHBOARD_TAB_GROUPS.map" in src
    assert "stom-shell-context" in src
    assert "stom-tabgroup" in src
    assert "stom-tab-badge" in src
    assert "<LabPage" in src and "<ResearchIndexPage" in src


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
    for active in ('activeKey="records"', 'activeKey="lab"', 'activeKey="pro"', 'activeKey="verdict"'):
        assert active in src
    assert "normalizeVerdictSubtab" in src
    assert 'VERDICT_SUBTAB_KEYS = ["summary", "regime", "portfolio", "decide"]' in src


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
    assert "state.latest.current_step" in src
    assert "step_timings 누적" in src
    assert "ProcessFlowDiagram" in src
    assert "<iframe" not in src  # iframe remains app.jsx route chrome, not process component state mutation.
    assert "state mode" in src
    assert "discrete progress" in src
    assert "logWindow = logs.slice(-50)" in src
