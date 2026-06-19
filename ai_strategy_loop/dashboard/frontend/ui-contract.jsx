/* Dashboard IA and route contract.
 *
 * Stable keys remain the localStorage and Track Z contract.  Labels/groups may evolve, but key
 * migrations require explicit tests before execution.
 */
const DASHBOARD_ROUTE_CONTRACTS = [
  { key: "evolution", label: "진화 대시보드", icon: "🧬", group: "운영 루프", badge: "LIVE", contract: "실시간 생성·백테스트·채점·승인 대기 루프" },
  { key: "backtest", label: "백테스트", icon: "📊", group: "검증", badge: "BT", contract: "전략/조건식 백테스트 실행·결과 조회" },
  { key: "simulation", label: "차트 시뮬레이션", icon: "📈", group: "검증", badge: "SIM", contract: "차트 리플레이·수동 검토" },
  { key: "records", label: "기록 인덱스", icon: "IDX", group: "연구 기록", badge: "INDEX", contract: "campaign/docs/update_log/registry 전체 governed lookup" },
  { key: "lab", label: "연구실", icon: "🔬", group: "연구 기록", badge: "LAB", contract: "연구 위키·AI 컨텍스트·run별 분석 홈" },
  { key: "pro", label: "분석 프로", icon: "📊", group: "판정", badge: "PRO", contract: "분석 워크벤치·명예의 전당 workbench" },
  { key: "verdict", label: "결정 이력", icon: "⚖️", group: "판정", badge: "LOG", contract: "append-only 운용 결정 이력" },
  { key: "process", label: "프로세스 흐름", icon: "🗺️", group: "프로세스", badge: "FLOW", contract: "read-only current_step/step_timing/process_flow" },
];

const DASHBOARD_TAB_GROUPS = [
  { key: "run", label: "운영 루프", tabs: ["evolution", "process"] },
  { key: "verify", label: "검증", tabs: ["backtest", "simulation"] },
  { key: "research", label: "연구 기록", tabs: ["records", "lab"] },
  { key: "decision", label: "판정", tabs: ["pro", "verdict"] },
];

const EVIDENCE_WORKSPACE_LINKS = [
  { key: "records", label: "기록 인덱스", icon: "IDX", badge: "lookup", contract: "전체 기록 검색·라인리지" },
  { key: "lab", label: "연구실", icon: "🔬", badge: "wiki", contract: "위키·컨텍스트·run 분석" },
  { key: "pro", label: "분석 프로", icon: "📊", badge: "workbench", contract: "분석 워크벤치" },
  { key: "verdict", label: "결정 이력", icon: "⚖️", badge: "append-only", contract: "운용 결정 감사 trail" },
];

function routeContract(key) {
  return DASHBOARD_ROUTE_CONTRACTS.find(item => item.key === key) || DASHBOARD_ROUTE_CONTRACTS[0];
}

function normalizeDashboardTabKey(value) {
  return DASHBOARD_ROUTE_CONTRACTS.some(item => item.key === value) ? value : "evolution";
}

Object.assign(window, {
  DASHBOARD_ROUTE_CONTRACTS,
  DASHBOARD_TAB_GROUPS,
  EVIDENCE_WORKSPACE_LINKS,
  normalizeDashboardTabKey,
  routeContract,
});

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { DASHBOARD_ROUTE_CONTRACTS, DASHBOARD_TAB_GROUPS, EVIDENCE_WORKSPACE_LINKS, normalizeDashboardTabKey, routeContract };
