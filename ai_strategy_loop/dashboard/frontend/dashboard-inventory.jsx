/* Dashboard UI phase-2 owner and performance inventory.
 *
 * This file is the pre-edit inventory gate from the approved plan.  It is product-visible
 * documentation and a testable source contract; it does not fetch, mutate state, or touch
 * broker/export/protected runtime boundaries.
 */
const DASHBOARD_PAGE_OWNER_MATRIX = [
  { key: "evolution", owner: "운영 루프", owns: "실시간 생성·백테스트·채점 루프와 승인 대기 관찰", notOwner: "기록 검색·분석 워크벤치·운용 결정 이력", primarySurface: "App/evolution panels", emptyState: "진화 시작 전 안내와 설정 열기" },
  { key: "process", owner: "조건식 발굴 프로세스", owns: "read-only current_step, step_timings, recent_logs, /process_flow 동시 확인", notOwner: "루프 제어·상태 변경·final approval/export", primarySurface: "ProcessFlowPanel + /process_flow iframe", emptyState: "노드 미정·로그 대기" },
  { key: "backtest", owner: "검증 실행", owns: "조건식 백테스트 실행, 최적화, WFO, 결과 조회", notOwner: "진화 루프 최종 승인·운용 결정 기록", primarySurface: "BacktestTab", emptyState: "조건식/이력 없음" },
  { key: "simulation", owner: "차트 리플레이", owns: "일일 min DB 리플레이와 수동 신호 검토", notOwner: "실거래 주문·전략 DB 쓰기", primarySurface: "SimulationTab", emptyState: "날짜·종목 선택 대기" },
  { key: "records", owner: "전체 기록 조회", owns: "campaign/docs/update_log/registry lineage 검색과 inert 원문 확인", notOwner: "위키 큐레이션·분석 편집·결정 기록", primarySurface: "ResearchIndexPanel", emptyState: "필터/검색어 조정" },
  { key: "lab", owner: "연구실", owns: "위키, AI 컨텍스트, run 분석 홈, 연구 탐색", notOwner: "전체 기록 인덱스 정본·Pro 워크벤치 액션", primarySurface: "LabPage + ResearchWikiPanel", emptyState: "run/위키 데이터 대기" },
  { key: "pro", owner: "분석 워크벤치", owns: "조건 후보 분석, HoF 비교, 워크벤치 액션", notOwner: "append-only 운용 결정·final approval", primarySurface: "ProPage + ResearchProPanel + HofInventoryGate", emptyState: "run 선택 또는 분석 데이터 대기" },
  { key: "verdict", owner: "결정 이력", owns: "검증 결산, 레짐/포트폴리오 advisory, append-only 결정 기록", notOwner: "전략 내보내기 승인(final_approval)", primarySurface: "VerdictPanel", emptyState: "결정 이력 없음" },
];

const PHASE2_SOURCE_INVENTORY = [
  { surface: "records", ownerFiles: ["research-index.jsx", "dashboard-pages.jsx"], endpoints: ["GET /research_index", "GET /research_index/detail"], fields: ["id", "title", "kind", "canonicality", "source_authority", "source_path", "updated_at", "tags", "related_ids", "summary"], sentinels: ["inert <pre>", "detailRequestSeq", "visible row cap", "authority badges"] },
  { surface: "pro_hof", ownerFiles: ["dashboard-pages.jsx", "research-pro.jsx", "rp-panel.jsx", "rp-heatmap.jsx", "chart-hall-of-fame.jsx", "hof-inventory.jsx"], endpoints: ["GET /runs", "research pro REST surfaces"], fields: ["HOF_INVENTORY_FIELDS", "human/seed/AI kind", "screenshots", "workbench_actions"], sentinels: ["HofInventoryGate", "No HoF component merge", "field render markers"] },
  { surface: "large_lists", ownerFiles: ["table.jsx", "research-index.jsx", "chart-hall-of-fame.jsx", "rp-heatmap.jsx", "dashboard-pages.jsx"], endpoints: ["GET /runs", "GET /research_index", "dashboard state.generations"], fields: ["row count", "visible cap", "sort/filter keys", "stable row id"], sentinels: ["no-dependency windowing", "memoized derived lists", "before/after observation"] },
  { surface: "duplicate_cleanup", ownerFiles: ["dashboard-pages.jsx", "research-lab.jsx", "research-pro.jsx", "chart-hall-of-fame.jsx", "ui-state.jsx"], endpoints: ["none; source-equivalence only"], fields: ["labels", "empty states", "cards", "HoF rows"], sentinels: ["equivalence tests before deletion", "no field loss", "standalone globals"] },
];

const LARGE_LIST_PERF_TARGETS = [
  { surface: "records", dataset: "research_index rows", visibleLimit: 80, reviewAt: 500, target: "filter/sort under one interaction frame on common cache-hit data" },
  { surface: "generations", dataset: "state.generations", visibleLimit: 300, reviewAt: 300, target: "sort and expand without blocking route switch" },
  { surface: "hof", dataset: "human + seed + AI benchmark rows", visibleLimit: 150, reviewAt: 150, target: "preserve field inventory while keeping table scroll bounded" },
  { surface: "verdict", dataset: "append-only decisions", visibleLimit: 300, reviewAt: 300, target: "newest decision visible without reordering audit trail" },
  { surface: "process_logs", dataset: "state.latest.recent_logs", visibleLimit: 50, reviewAt: 100, target: "auto-scroll latest logs with state source labels" },
];

function pageOwnerContract(key) {
  return DASHBOARD_PAGE_OWNER_MATRIX.find(item => item.key === key) || DASHBOARD_PAGE_OWNER_MATRIX[0];
}

function listPerfTarget(surface) {
  return LARGE_LIST_PERF_TARGETS.find(item => item.surface === surface) || null;
}

function Phase2InventoryPanel({ compact = false }) {
  const pageCount = DASHBOARD_PAGE_OWNER_MATRIX.length;
  return (
    <div className={"phase2-inventory-panel" + (compact ? " compact" : "")}>
      <div className="phase2-inventory-head">
        <div>
          <div className="phase2-inventory-kicker mono">PHASE 2 INVENTORY GATE</div>
          <b>페이지 역할 · 소스 소유권 · 성능 기준</b>
        </div>
        <span className="mono">{pageCount} pages · {PHASE2_SOURCE_INVENTORY.length} source groups</span>
      </div>
      <p>
        UI 대공사는 라벨을 먼저 바꾸는 작업이 아니라, 각 페이지가 무엇을 소유하고 무엇을 소유하지 않는지
        고정한 뒤 안전하게 재배치하는 작업입니다.
      </p>
      {!compact && (
        <div className="phase2-owner-grid">
          {DASHBOARD_PAGE_OWNER_MATRIX.map(item => (
            <div key={item.key} className="phase2-owner-card">
              <span className="mono">{item.key}</span>
              <b>{item.owner}</b>
              <small>소유: {item.owns}</small>
              <small>비소유: {item.notOwner}</small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { DASHBOARD_PAGE_OWNER_MATRIX, PHASE2_SOURCE_INVENTORY, LARGE_LIST_PERF_TARGETS, pageOwnerContract, listPerfTarget, Phase2InventoryPanel });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { DASHBOARD_PAGE_OWNER_MATRIX, PHASE2_SOURCE_INVENTORY, LARGE_LIST_PERF_TARGETS, pageOwnerContract, listPerfTarget, Phase2InventoryPanel };
