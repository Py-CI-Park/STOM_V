from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"


def _read(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_v4_shell_declares_linked_roving_tab_contract() -> None:
    # Given: the six-destination V5.P0 application shell.
    source = _read("dashboard-v4-shell.jsx")

    # When/Then: the navigation and panel markup expose the exact ARIA contract.
    assert 'role="tablist"' in source
    assert 'aria-label="V4 연구 워크스페이스"' in source
    assert 'id={"v4-tab-" + tab.key}' in source
    assert 'aria-controls={"v4-panel-" + tab.key}' in source
    assert "tabIndex={activeTab === tab.key ? 0 : -1}" in source
    assert 'role="tabpanel"' in source
    assert 'id={"v4-panel-" + tab.key}' in source
    assert 'aria-labelledby={"v4-tab-" + tab.key}' in source

def test_v4_shell_freezes_normal_ia_and_default_off_rollback() -> None:
    source = _read("dashboard-v4-shell.jsx")
    inventory = _read("dashboard-inventory.jsx")

    assert "const DASHBOARD_PAGE_OWNER_MATRIX" in inventory
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    assert [key for key in ("research", "backtest", "replay", "history", "workbench", "reports")] == [
        line.split('key: "', 1)[1].split('"', 1)[0] for line in matrix.splitlines() if 'key: "' in line
    ]
    assert 'legacyAliases: ["records", "audit", "verdict"]' in inventory
    assert 'legacyAliases: ["wiki"]' in inventory
    assert 'owner: "성과·Hall-of-Fame"' in inventory
    assert 'notOwner: "후보 분석·비교·히스토리 거버넌스·append-only 결정·final approval"' in inventory
    assert "const V4_NORMAL_TABS = DASHBOARD_PAGE_OWNER_MATRIX;" in source
    assert "const V4_LEGACY_EXTRA_TABS" in source
    assert 'const V4_LEGACY_ROLLBACK_QUERY = "v4_legacy_extras"' in source
    assert "v4CanonicalizeLegacyLocation();" in source
    assert 'return v4LegacyExtrasEnabled() ? V4_NORMAL_TABS.concat(V4_LEGACY_EXTRA_TABS) : V4_NORMAL_TABS;' in source
    assert "{tabs.map(tab => (" in source
    assert "V4_TABS.map" not in source
    assert "v4-rail-div" not in source
    assert 'window.history.pushState(null, "", url.pathname + url.search);' in source
    assert 'window.addEventListener("popstate", onPopState);' in source
    assert "pendingTabFocusRef.current = nextTab;" in source

def test_v4_legacy_extra_tabs_are_runtime_default_off_and_explicitly_recoverable() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    inventory = _read("dashboard-inventory.jsx")
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_NORMAL_TABS")
    end = source.index("function v4TabFromPathname", start)
    helper = source[start:end]
    script = """
global.window = { location: { search: '' } };
const DASHBOARD_PAGE_OWNER_MATRIX = new Function('return [' + process.argv[3] + '];')();
const api = new Function(process.argv[2] + '; return { enabled: v4LegacyExtrasEnabled, tabs: v4TabsForSession };')();
const normal = api.tabs().map(tab => tab.key);
window.location.search = '?v4_legacy_extras=1';
const rollback = api.tabs().map(tab => tab.key);
console.log(JSON.stringify({ normal, rollback, explicitOff: api.enabled('?v4_legacy_extras=0') }));
"""
    result = subprocess.run(
        [node, "-", helper, matrix], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "normal": ["research", "backtest", "replay", "history", "workbench", "reports"],
        "rollback": [
            "research", "backtest", "replay", "history", "workbench", "reports",
            "lab", "catalog", "context", "alpha",
        ],
        "explicitOff": False,
    }



def test_v5_5_shell_migrates_retired_surfaces_and_owns_context_drawer() -> None:
    source = _read("dashboard-v4-shell.jsx")
    css = _read("v4.css")

    for marker in (
        'const V4_CONTEXT_DRAWER_QUERY = "v4_context"',
        'const V4_PROTOTYPE_QUERY = "prototype"',
        'import { AIContextPanel } from "./ai-context.jsx";',
        'storage.removeItem("stom_active_tab")',
        'storage.removeItem("stom_active_evolution_tab")',
        'aria-haspopup="dialog"',
        'aria-controls="v4-context-drawer"',
        'role="dialog"',
        'aria-modal="true"',
        'event.key === "Escape"',
        'event.key !== "Tab"',
        "contextTriggerRef.current?.focus()",
        'new URLSearchParams(window.location.search).get(V4_CONTEXT_DRAWER_QUERY) === "1"',
        '<V4History baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} onNavigate={selectTab} />',
    ):
        assert marker in source
    assert ".v4-context-drawer" in css
    assert "min-height: var(--target-touch)" in css
    assert 'url.searchParams.set(V4_LEGACY_ROLLBACK_QUERY, "1")' not in source


def test_v5_5_live_dual_mounts_existing_edge_heatmap_only_in_backtest_step() -> None:
    source = _read("v4-research.jsx")

    assert 'import { ResearchHeatmapPanel } from "./research-pro.jsx";' in source
    assert '<ResearchHeatmapPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />' in source
    assert "selectedStep === 1" in source
    assert "이는 백테스트 권위 필드가 아닌 참고용 탐색 지표" in source
    assert "OOS 검증 결과가 아닙니다." in source
    assert "평가용 CellHeatmap과 동일하지 않습니다." in source

def test_v4_tab_keyboard_runtime_wraps_and_supports_home_end() -> None:
    # Given: Node evaluating the shell's dependency-free navigation helper.
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("function _nextV4TabKey")
    end = source.index("\n}\n", start) + 2
    helper = source[start:end]
    script = """
const fn = new Function(process.argv[2] + '; return _nextV4TabKey;')();
const keys = ['research','backtest','replay','history','workbench','reports'];
console.log(JSON.stringify({
  right: fn(keys, 'research', 'ArrowRight'),
  leftWrap: fn(keys, 'research', 'ArrowLeft'),
  rightWrap: fn(keys, 'reports', 'ArrowRight'),
  home: fn(keys, 'history', 'Home'),
  end: fn(keys, 'research', 'End'),
  ignored: fn(keys, 'workbench', 'Enter'),
}));
"""
    result = subprocess.run(
        [node, "-", helper], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "right": "backtest",
        "leftWrap": "reports",
        "rightWrap": "research",
        "home": "research",
        "end": "reports",
        "ignored": "workbench",
    }


def test_v4_foundation_owns_narrow_layout_focus_and_motion() -> None:
    # Given: the shared V4 stylesheet.
    css = _read("v4.css")

    # When/Then: foundation tokens and narrow-screen containment are explicit.
    assert "--control-dense: 32px" in css
    assert "--target-touch: 44px" in css
    assert "--focus-width: 2px" in css
    assert "@media (max-width: 760px)" in css
    assert "grid-template-columns: minmax(0, 1fr)" in css
    assert "min-height: var(--target-touch)" in css
    assert "overflow-x: auto" in css
    assert "word-break: keep-all" in css
    assert "overflow-wrap: break-word" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "overflow-x: hidden" not in css


def test_v4_canonical_deep_links_map_to_tabs() -> None:
    # Given: Node evaluating the promoted shell's pathname->tab mapping (B-track default promotion).
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    inventory = _read("dashboard-inventory.jsx")
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    source = _read("dashboard-v4-shell.jsx")
    initial_start = source.index("const V4_NORMAL_TABS")
    fn_start = source.index("function v4TabFromPathname")
    fn_end = source.index("\n}\n", fn_start) + 2
    helper = source[initial_start:fn_end]
    script = """
const DASHBOARD_PAGE_OWNER_MATRIX = new Function('return [' + process.argv[3] + '];')();
const fn = new Function(process.argv[2] + '; return v4TabFromPathname;')();
console.log(JSON.stringify({
  evolution: fn('/ui/evolution'),
  process: fn('/ui/evolution/process'),
  records: fn('/ui/evolution/records'),
  lab: fn('/ui/evolution/lab'),
  context: fn('/ui/evolution/context'),
  alpha: fn('/ui/evolution/alpha'),
  catalog: fn('/ui/evolution/catalog'),
  workbench: fn('/ui/evolution/workbench'),
  verdict: fn('/ui/evolution/verdict'),
  audit: fn('/ui/audit'),
  backtest: fn('/ui/backtest'),
  replay: fn('/ui/chart-replay'),
  root: fn('/ui/'),
  unknown: fn('/ui/evolution/nope'),
}));
"""
    result = subprocess.run(
        [node, "-", helper, matrix], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "evolution": "research",
        "process": "research",
        "records": "history",
        "lab": "lab",
        "context": "context",
        "alpha": "alpha",
        "catalog": "catalog",
        "workbench": "workbench",
        "verdict": "history",
        "audit": "history",
        "backtest": "backtest",
        "replay": "replay",
        "root": "",
        "unknown": "nope",
    }
def test_v4_legacy_audit_query_migrates_to_history() -> None:
    inventory = _read("dashboard-inventory.jsx")
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_NORMAL_TABS")
    end = source.index("\n}\n", source.index("function v4InitialTab")) + 2
    helper = source[start:end]
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    script = """
global.window = { location: { search: '?tab=audit', pathname: '/ui/' } };
const DASHBOARD_PAGE_OWNER_MATRIX = new Function('return [' + process.argv[3] + '];')();
const fn = new Function(process.argv[2] + '; return v4InitialTab;')();
const keys = ['research', 'backtest', 'replay', 'history', 'workbench', 'reports'];
const audit = fn(keys);
window.location.search = '?tab=verdict';
console.log(JSON.stringify({ audit, verdict: fn(keys) }));
"""
    result = subprocess.run(
        [node, "-", helper, matrix], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"audit": "history", "verdict": "history"}
def test_v4_known_prototype_identity_migrates_without_enabling_rollback() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    inventory = _read("dashboard-inventory.jsx")
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_NORMAL_TABS")
    end = source.index("function _nextV4TabKey")
    helper = source[start:end]
    script = """
const DASHBOARD_PAGE_OWNER_MATRIX = new Function('return [' + process.argv[3] + '];')();
global.window = { location: { origin: 'http://localhost' } };
const api = new Function(process.argv[2] + '; return { canonicalize: v4CanonicalizeLegacyLocation, initial: v4InitialTab };')();
const calls = [];
const location = { pathname: '/ui/evolution/catalog', search: '', href: 'http://localhost/ui/evolution/catalog' };
const history = { replaceState: (_state, _title, url) => { calls.push(url); location.search = url.slice(url.indexOf('?')); } };
const prototype = api.canonicalize(location, history);
global.window.location = { search: location.search, pathname: location.pathname };
console.log(JSON.stringify({ prototype, url: calls[0], initial: api.initial(['research', 'backtest', 'replay', 'history', 'workbench', 'reports']) }));
"""
    result = subprocess.run(
        [node, "-", helper, matrix], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "prototype": "reports",
        "url": "/ui/evolution/catalog?tab=reports&prototype=catalog",
        "initial": "reports",
    }


def test_v4_explicit_rollback_preserves_prototype_identity() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node unavailable")
    inventory = _read("dashboard-inventory.jsx")
    matrix = inventory.split("const DASHBOARD_PAGE_OWNER_MATRIX = [", 1)[1].split("];", 1)[0]
    source = _read("dashboard-v4-shell.jsx")
    start = source.index("const V4_NORMAL_TABS")
    end = source.index("function _nextV4TabKey")
    helper = source[start:end]
    script = """
const DASHBOARD_PAGE_OWNER_MATRIX = new Function('return [' + process.argv[3] + '];')();
const api = new Function(process.argv[2] + '; return { canonicalize: v4CanonicalizeLegacyLocation, initial: v4InitialTab };')();
const location = {
  pathname: '/ui/evolution/catalog',
  search: '?v4_legacy_extras=1',
  href: 'http://localhost/ui/evolution/catalog?v4_legacy_extras=1',
};
const calls = [];
const history = { replaceState: (_state, _title, url) => calls.push(url) };
global.window = { location: { ...location, origin: 'http://localhost' } };
const prototype = api.canonicalize(location, history);
const initial = api.initial(['research', 'backtest', 'replay', 'history', 'workbench', 'reports', 'lab', 'catalog', 'context', 'alpha']);
console.log(JSON.stringify({ prototype, initial, calls }));
"""
    result = subprocess.run(
        [node, "-", helper, matrix], input=script, capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"prototype": "catalog", "initial": "catalog", "calls": []}


def test_v4_catalog_uses_only_sealed_rdc1_routes_and_guards_stale_base() -> None:
    source = _read("v4-catalog.jsx")

    assert "sealed rdc-1 Reports prototype" in source
    assert "STOM_RESEARCH_ASSETS_DB env-only" in source
    assert 'const CAT_CONTRACT_VERSION = "rdc-1"' in source
    assert 'assets: "/research/assets?limit=500"' in source
    assert 'judgments: "/research/judgments?include_ledger=1&limit=200"' in source
    assert 'clauses: "/research/clauses?limit=200"' in source
    assert 'return "/research/cells?source=" + encodeURIComponent(source) + "&limit=2000";' in source
    assert 'cells: "/research/cells?limit=1"' in source
    assert "/research/summary" not in source
    assert "AbortController" in source
    assert "generation !== generationRef.current" in source
    assert "baseUrl !== baseRef.current" in source
    assert 'value.contract_version !== CAT_CONTRACT_VERSION' in source
    assert 'reason: "contract_mismatch"' in source
    assert "asset.path" not in source
    assert "CAT_CELL_SOURCES" not in source


def test_v4_catalog_discovers_cell_sources_from_allowed_allowlist() -> None:
    source = _read("v4-catalog.jsx")

    for forbidden in (
        'const CAT_CELL_SOURCES = Object.freeze(["o1g"',
        "CAT_CELL_SOURCES.map",
        "CAT_CELL_SOURCES.length",
        'useState_cat("o1g")',
        'useState_cat("l3")',
        "const fallbackSource =",
    ):
        assert forbidden not in source

    assert "function _catDiscoveredCellSources(envelope)" in source
    assert "const raw = Array.isArray(envelope.allowed) ? envelope.allowed : [];" in source
    assert "const cellSources = _catDiscoveredCellSources(cellDiscovery);" in source
    assert "cellSources.length === 0" in source
    assert "cellSources.map(source => get(_catCellsRoute(source)).then(payload => [source, payload]))" in source
    assert "<_V4CatalogV2 cellsBySource={cellsBySource} cellSources={cellSources} />" in source
    assert "cellSources.map(source => <option" in source
    assert 'cell sources {ownsData ? cellSources.length : "—"}' in source


def test_v4_catalog_renders_five_honest_canonical_views() -> None:
    source = _read("v4-catalog.jsx")

    for marker in (
        "V1 연구 파이프라인/연혁실",
        "V2 함정 설명 지도",
        "V3 절 실험실",
        "V4 표본/출구 은행 조회",
        "V5 B1 honest empty skeleton",
        "39절 중 측정 38절(#39=#15 순수 중복 병합) · FDR 분모 34",
        "load_bearing\", 5",
        "counter_productive\", 6",
        "weak_signal\", 5",
        "inconclusive\", 4",
        "none\", 18",
        "이 조합의 사전 집계가 없습니다 — 원시 재계산은 금지되어 있습니다.",
        "운용 개시 전 — 데이터 없음",
        "U-4 미확정",
    ):
        assert marker in source

    assert "_catText(j.verdict)" in source
    assert "_catText(asset.status_tag)" in source
    assert "_catText(selected.label_tag)" in source
    assert "Number(cell.n) < 2000" in source
    assert "표본 부족(n<2,000) — 판정 금지" in source
    assert "ciLow > 0" in source
    assert "설명 지도(veto 아님)" in source
    assert 'className="v4-chip off"' in source
    assert "success" not in source[source.index("function _V4CatalogV5"):source.index("function V4Catalog")]


def test_v4_catalog_css_supports_responsive_sealed_views() -> None:
    css = _read("v4.css")

    for marker in (
        ".v4-catalog-view-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));",
        ".v4-catalog-provenance, .v4-catalog-panel",
        ".v4-catalog-watermark",
        ".v4-catalog-map-cell.insufficient",
        "filter: grayscale(1)",
        ".v4-catalog-class-counts",
        ".v4-catalog-bank-metrics",
        ".v4-catalog-b1-status",
        "@media (max-width: 1100px)",
        "@media (max-width: 720px)",
    ):
        assert marker in css
def test_v5_live_uses_accessible_process_tabs_and_pinned_follow_contract() -> None:
    source = _read("v4-research.jsx")

    assert 'role="tablist" aria-label="연구 단계"' in source
    assert 'role="tab"' in source
    assert 'role="tabpanel"' in source
    assert 'aria-controls={"v4-live-panel-" + step.key}' in source
    assert "pinnedStepRef.current = false;" in source
    assert "if (!pinnedStepRef.current) setSelectedStep(situation.active);" in source
    assert "identityRef.current !== runGenerationIdentity" in source
    assert 'event.key === "ArrowRight"' in source
    assert 'event.key === "Home"' in source
    assert 'aria-expanded={drawerOpen}' in source
    assert 'aria-controls="v4-live-drawer"' in source


def test_v5_live_backtest_authority_and_responsive_graph_contract() -> None:
    source = _read("v4-research.jsx")
    css = _read("v4.css")

    for label in (
        "매수 조건식 · buy_code",
        "매도 조건식 · sell_code",
        "source / run_id / generation",
        "engine_state / backtest_progress",
        "analysis evidence ·",
        "GET /strategy_code",
    ):
        assert label in source
    assert "_v4EngineSummary(situation.engineState)" in source
    assert "situation.backtestProgress" in source
    assert "situation.phaseStartedAt" in source
    for state in ("fresh", "stale", "error", "empty"):
        assert f'label: "{state}"' in source
    assert ".v4-graph-grid" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert "max-height: 320px" in css
    assert ".v4-live-page-title { font-size: 22px" in css
    assert ".v4-research .panel-hd-title { font-size: 16px" in css
    assert ".v4-research { display: flex; flex-direction: column; gap: 14px; min-width: 0; font-size: 14px; }" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "@keyframes v4-step-pulse" in css
    assert ".v4-live-drawer[hidden] { display: none !important; }" in css
    assert 'className={"v4-live-layout" + (drawerOpen ? " drawer-open" : "")}' in source
    assert ".v4-live-layout.drawer-open" in css
def test_v5_2_backtest_field_source_table_seals_existing_paths() -> None:
    source = _read("v4-research.jsx")
    css = _read("v4.css")

    for marker in (
        "V5.2 sealed field-source table",
        "V5_2_FIELD_SOURCES",
        "authoritative state path(s)",
        "freshness / status path",
        "GET /strategy_code → buy_code",
        "GET /strategy_code → sell_code",
        "exact code_status=ok",
        "latest.engine_state",
        "latest.backtest_progress",
        "generations[].graded_score/profit/mdd",
        "latest.evidence_status",
        "owner",
        "source · {evidence.source}",
    ):
        assert marker in source
    assert "/strategy_code?run=${encodeURIComponent(runId)}&gen=${strategyGen}" in source
    assert "_v4BindStrategyCodePayload(payload, runId, strategyGen)" in source
    assert "stream.buy_code_partial" not in source and "stream.sell_code_partial" not in source
    assert "strategyCodeRecord.runId === runId" in source
    assert "Number(strategyCodeRecord.gen) === Number(strategyGen)" in source
    assert 'strategyCodeStatus === "identity_mismatch" ? "GET /strategy_code · identity_mismatch"' in source
    assert "setInterval" not in source[source.index("function V4ResearchLive"):source.index("const hasFetchedCode")]
    for marker in (
        ".v4-field-source-table {",
        "overflow-x: auto",
        "min-width: 720px",
        "font-size: 14px",
    ):
        assert marker in css


def test_v5_2_evidence_freshness_is_explicit_and_fail_closed() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for frontend helper contract coverage.")
    source = _read("v4-research.jsx")
    start = source.index("function _v4EvidenceState")
    end = source.index("const V5_2_FIELD_SOURCES", start)
    helper = source[start:end]
    script = """
const map = new Function(process.argv[2] + '; return _v4EvidenceState;')();
const state = input => {
  const result = map(input);
  return [result.label, result.value];
};
console.log(JSON.stringify({
  explicitError: state({ latest: { evidence: 'partial', evidence_status: 'error', evidence_error: 'publisher failed' } }),
  explicitStale: state({ latest: { evidence: 'old evidence', evidence_status: 'stale' } }),
  explicitFresh: state({ latest: { evidence: 'confirmed', evidence_status: 'fresh' } }),
  unproven: state({ latest: { evidence: 'unproven' } }),
  empty: state({ latest: { evidence_status: 'fresh' } }),
  mixedHigherUnproven: state({ latest: { evidence: 'high' }, current_run: { evidence: 'low', evidence_status: 'fresh' } }),
  mixedLowerError: state({ latest: { evidence: 'high' }, current_run: { evidence: 'low', evidence_status: 'error', evidence_error: 'low failed' } }),
  mixedHigherFresh: state({ latest: { evidence: 'high', evidence_status: 'fresh' }, current_run: { evidence: 'low', evidence_status: 'stale' } }),
  metricFallback: state({ current_gen: 2, generations: [{ gen_no: 2, graded_score: 0.7, profit: 1200, mdd: 3.5 }] }),
}));
"""
    result = subprocess.run([node, "-", helper], input=script, capture_output=True, text=True, encoding="utf-8", timeout=20, check=False)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "explicitError": ["error", "publisher failed"],
        "explicitStale": ["stale", "old evidence"],
        "explicitFresh": ["fresh", "confirmed"],
        "unproven": ["stale", "unproven"],
        "empty": ["empty", "발행된 분석 증거 없음"],
        "mixedHigherUnproven": ["stale", "high"],
        "mixedLowerError": ["stale", "high"],
        "mixedHigherFresh": ["fresh", "high"],
        "metricFallback": ["stale", ["graded_score 0.7", "profit 1200", "mdd 3.5"]],
    }


def test_v5_2_strategy_code_binding_rejects_cross_identity_payloads() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for frontend helper contract coverage.")
    source = _read("v4-research.jsx")
    start = source.index("function _v4BindStrategyCodePayload")
    end = source.index("function _V5_2FieldSourceTable", start)
    helper = source[start:end]
    script = """
const bind = new Function(process.argv[2] + '; return _v4BindStrategyCodePayload;')();
const summarize = value => [value.status, value.payload && value.payload.buy_code];
console.log(JSON.stringify({
  match: summarize(bind({ run_id: 'run-a', gen_no: 4, code_status: 'ok', buy_code: 'MATCH', sell_code: '' }, 'run-a', 4)),
  wrongRun: summarize(bind({ run_id: 'run-b', gen_no: 4, code_status: 'ok', buy_code: 'WRONG', sell_code: '' }, 'run-a', 4)),
  wrongGen: summarize(bind({ run_id: 'run-a', gen: 3, code_status: 'ok', buy_code: 'OLD', sell_code: '' }, 'run-a', 4)),
  unknownStatus: summarize(bind({ run_id: 'run-a', gen_no: 4, code_status: 'future', buy_code: 'UNTRUSTED', sell_code: '' }, 'run-a', 4)),
  malformed: summarize(bind({ run_id: 'run-a', gen_no: 4, code_status: 'ok', buy_code: 'ONLY' }, 'run-a', 4)),
  empty: summarize(bind(null, 'run-a', 4)),
}));
"""
    result = subprocess.run([node, "-", helper], input=script, capture_output=True, text=True, encoding="utf-8", timeout=20, check=False)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "match": ["fresh", "MATCH"],
        "wrongRun": ["identity_mismatch", None],
        "wrongGen": ["identity_mismatch", None],
        "unknownStatus": ["future", None],
        "malformed": ["malformed_code", None],
        "empty": ["empty", None],
    }


def test_v5_2_engine_and_progress_objects_render_as_scalars() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for frontend helper contract coverage.")
    source = _read("v4-research.jsx")
    start = source.index("function _v4ObjectSummary")
    end = source.index("function v4LiveSituation", start)
    helper = source[start:end]
    script = """
const render = new Function(process.argv[2] + '; return { engine: _v4EngineSummary, progress: _v4ProgressSummary };')();
console.log(JSON.stringify({
  engine: render.engine({ status: 'running', phase: 'backtest_start', bt_engine_mode: 'warm', effective_engine_count: 12 }),
  progress: render.progress({ percent: 60, progress_source: 'generation_level' }),
  countProgress: render.progress({ phase: 'backtest_start', done_units: 3, total_units: 5 }),
  empty: render.engine({}),
}));
"""
    result = subprocess.run([node, "-", helper], input=script, capture_output=True, text=True, encoding="utf-8", timeout=20, check=False)

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["engine"] == "status running · phase backtest_start · bt_engine_mode warm · effective_engine_count 12"
    assert payload["progress"] == "60.0% · generation_level"
    assert payload["countProgress"] == "phase backtest_start · done_units 3 · total_units 5"
    assert payload["empty"] == "대기"


def test_v5_live_state_typography_floor_is_fourteen_pixels() -> None:
    css = _read("v4.css")

    for rule in (
        "padding: 8px 12px; font-size: 14px; font-family: var(--mono);",
        ".v4-onboarding-bd p { color: var(--ink-1); font-size: 14px;",
        ".v4-onboarding-steps b { display: block; font-size: 14px;",
        ".v4-onboarding-steps span { font-size: 14px;",
        ".phase-status-banner { margin-top: 8px; padding: 7px 11px; border-radius: var(--radius-sm); font-size: 14px;",
        ".v4-evidence-source { display: block; margin-top: 4px; color: var(--ink-3); font-size: 14px;",
        ".v4-research :where(p, span, div, b, small, label, button, a, th, td, dt, dd, pre, code):not(:has(*)) { font-size: max(14px, 1em) !important; }",
        ".v4-research svg text { font-size: 14px !important; }",
        ".v4-research .panel-hd-title { font-size: 16px !important; }",
        ".v4-research .v4-live-page-title { font-size: 22px !important; }",
        ".v4-log-toggle, .v4-drawer-toggle { min-height: 44px;",
        ".v4-graph-grid .chart-wrap, .v4-graph-grid .v4-canvas-wrap { min-height: 0; height: 300px; max-height: 300px; }",
    ):
        assert rule in css
