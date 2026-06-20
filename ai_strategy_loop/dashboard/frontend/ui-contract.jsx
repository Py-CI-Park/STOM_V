/* Dashboard IA and route contract.
 *
 * Phase 4 correction: only three pages are visible at the top level.  Evolution owns
 * the research/process/decision workspaces as nested, canonical deep-link subtabs.
 */
const DASHBOARD_ROUTE_CONTRACTS = [
  { key: "evolution", label: "진화 홈", icon: "🧬", group: "주요 페이지", badge: "LIVE", contract: "실시간 생성·백테스트·채점·승인 대기 루프와 하위 연구 워크스페이스" },
  { key: "backtest", label: "백테스트", icon: "📊", group: "주요 페이지", badge: "BT", contract: "조건식 백테스트 실행·결과 조회" },
  { key: "simulation", label: "차트 리플레이", icon: "📈", group: "주요 페이지", badge: "SIM", contract: "차트 리플레이·수동 신호 검토" },
];

const EVOLUTION_SUBTAB_CONTRACTS = [
  { key: "overview", label: "개요", icon: "🏠", group: "진화 홈", badge: "HOME", contract: "진화 루프 시작·실시간 진행·핵심 연구 요약" },
  { key: "process", label: "프로세스", icon: "🗺️", group: "진화 홈", badge: "FLOW", contract: "조건식 발굴 단계·현재 노드·백테스트 진행·쉬운 설명" },
  { key: "records", label: "기록 검색", icon: "IDX", group: "진화 홈", badge: "INDEX", contract: "campaign/docs/update_log/registry 전체 governed lookup" },
  { key: "lab", label: "연구실·위키", icon: "🔬", group: "진화 홈", badge: "LAB", contract: "위키·AI 컨텍스트·run 분석 홈" },
  { key: "workbench", label: "분석 워크벤치", icon: "📊", group: "진화 홈", badge: "WORK", contract: "조건 후보 분석·명예의 전당 workbench" },
  { key: "verdict", label: "결정 감사", icon: "⚖️", group: "진화 홈", badge: "AUDIT", contract: "append-only 운용 결정 이력" },
];

const DASHBOARD_TAB_GROUPS = [
  { key: "main", label: "전체 페이지", tabs: ["evolution", "backtest", "simulation"] },
];

const EVIDENCE_WORKSPACE_LINKS = [
  { key: "records", label: "기록 검색", icon: "IDX", badge: "lookup", contract: "전체 기록 검색·라인리지" },
  { key: "lab", label: "연구실·위키", icon: "🔬", badge: "wiki", contract: "위키·컨텍스트·run 분석" },
  { key: "workbench", label: "분석 워크벤치", icon: "📊", badge: "workbench", contract: "후보 분석·HoF 비교" },
  { key: "verdict", label: "결정 감사", icon: "⚖️", badge: "append-only", contract: "운용 결정 감사 trail" },
];

const EVOLUTION_LEGACY_ALIASES = {
  process: "process",
  records: "records",
  lab: "lab",
  pro: "workbench",
  verdict: "verdict",
  workbench: "workbench",
};

const DASHBOARD_PATH_ALIASES = {
  backtest: "backtest",
  simulation: "simulation",
  "chart-replay": "simulation",
};

function routeContract(key) {
  return DASHBOARD_ROUTE_CONTRACTS.find(item => item.key === key) || DASHBOARD_ROUTE_CONTRACTS[0];
}

function evolutionSubtabContract(key) {
  return EVOLUTION_SUBTAB_CONTRACTS.find(item => item.key === key) || EVOLUTION_SUBTAB_CONTRACTS[0];
}

function normalizeDashboardTabKey(value) {
  return DASHBOARD_ROUTE_CONTRACTS.some(item => item.key === value) ? value : "evolution";
}

function normalizeEvolutionSubtabKey(value) {
  return EVOLUTION_SUBTAB_CONTRACTS.some(item => item.key === value) ? value : "overview";
}

function dashboardPathFor(tab, evolutionSubtab) {
  const top = normalizeDashboardTabKey(tab);
  if (top === "evolution") {
    const sub = normalizeEvolutionSubtabKey(evolutionSubtab);
    return sub === "overview" ? "/ui/evolution" : `/ui/evolution/${sub}`;
  }
  if (top === "backtest") return "/ui/backtest";
  if (top === "simulation") return "/ui/chart-replay";
  return "/ui/evolution";
}

function _safeDecodeSegment(segment) {
  try { return decodeURIComponent(segment); }
  catch (e) { return segment; }
}

function dashboardRouteFromLocation() {
  const storedTop = typeof window !== "undefined" && window.localStorage
    ? window.localStorage.getItem("stom_active_tab")
    : null;
  const storedEvolution = typeof window !== "undefined" && window.localStorage
    ? window.localStorage.getItem("stom_active_evolution_tab")
    : null;
  const fallback = {
    tab: normalizeDashboardTabKey(storedTop || "evolution"),
    evolutionSubtab: normalizeEvolutionSubtabKey(storedEvolution || "overview"),
    canonicalPath: null,
    legacy: false,
  };
  if (typeof window === "undefined" || !window.location) return fallback;

  const segments = String(window.location.pathname || "/ui/")
    .split("/")
    .filter(Boolean)
    .map(_safeDecodeSegment);
  const uiAt = segments.indexOf("ui");
  const tail = uiAt >= 0 ? segments.slice(uiAt + 1) : [];
  const head = tail[0] || "";

  if (head === "evolution") {
    const sub = normalizeEvolutionSubtabKey(tail[1] || "overview");
    return { tab: "evolution", evolutionSubtab: sub, canonicalPath: dashboardPathFor("evolution", sub), legacy: false };
  }
  if (EVOLUTION_LEGACY_ALIASES[head]) {
    const sub = EVOLUTION_LEGACY_ALIASES[head];
    return { tab: "evolution", evolutionSubtab: sub, canonicalPath: dashboardPathFor("evolution", sub), legacy: true };
  }
  if (DASHBOARD_PATH_ALIASES[head]) {
    const tab = DASHBOARD_PATH_ALIASES[head];
    return { tab, evolutionSubtab: fallback.evolutionSubtab, canonicalPath: dashboardPathFor(tab, fallback.evolutionSubtab), legacy: head !== tab };
  }
  return { ...fallback, canonicalPath: dashboardPathFor(fallback.tab, fallback.evolutionSubtab), legacy: false };
}

Object.assign(window, {
  DASHBOARD_ROUTE_CONTRACTS,
  EVOLUTION_SUBTAB_CONTRACTS,
  DASHBOARD_TAB_GROUPS,
  EVIDENCE_WORKSPACE_LINKS,
  EVOLUTION_LEGACY_ALIASES,
  DASHBOARD_PATH_ALIASES,
  normalizeDashboardTabKey,
  normalizeEvolutionSubtabKey,
  dashboardRouteFromLocation,
  dashboardPathFor,
  evolutionSubtabContract,
  routeContract,
});

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { DASHBOARD_ROUTE_CONTRACTS, EVOLUTION_SUBTAB_CONTRACTS, DASHBOARD_TAB_GROUPS, EVIDENCE_WORKSPACE_LINKS, EVOLUTION_LEGACY_ALIASES, DASHBOARD_PATH_ALIASES, normalizeDashboardTabKey, normalizeEvolutionSubtabKey, dashboardRouteFromLocation, dashboardPathFor, evolutionSubtabContract, routeContract };
