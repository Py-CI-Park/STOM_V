/* Dashboard V5 canonical destination owner inventory.
 *
 * This product-visible, testable matrix is the single ownership convention for the
 * V5 shell and the legacy dashboard.  Alias metadata records compatibility only:
 * aliases never create an additional normal-rail destination.
 */
const DASHBOARD_PAGE_OWNER_MATRIX = [
  { key: "research", label: "Live", full: "Research Live", badge: "LIVE", hint: "조건식 자율 진화 · 실시간 관찰", owner: "운영 루프", owns: "실시간 생성·백테스트·채점 루프와 승인 대기 관찰", notOwner: "히스토리 거버넌스·후보 비교·운용 결정 이력", primarySurface: "V4ResearchLive", emptyState: "진화 시작 전 안내와 설정 열기", legacyAliases: ["evolution"], internalAliases: ["process"], prototypeAliases: ["lab", "context", "alpha"] },
  { key: "backtest", label: "Backtest", full: "Backtest", badge: "BT", hint: "전략 실행 · 결과 리포트", owner: "검증 실행", owns: "조건식 백테스트 실행, 최적화, WFO, 결과 조회", notOwner: "진화 루프 최종 승인·운용 결정 기록", primarySurface: "V4Backtest", emptyState: "조건식/이력 없음", legacyAliases: [], internalAliases: [], prototypeAliases: [] },
  { key: "replay", label: "Replay", full: "Replay", badge: "SIM", hint: "캔들 리플레이 · 신호 맥락", owner: "차트 리플레이", owns: "일일 min DB 리플레이와 수동 신호 검토", notOwner: "실거래 주문·전략 DB 쓰기", primarySurface: "V4Replay", emptyState: "날짜·종목 선택 대기", legacyAliases: ["simulation", "chart-replay"], internalAliases: [], prototypeAliases: [] },
  { key: "history", label: "History", full: "History", badge: "HIST", hint: "run/gen 아카이브 · Compare · 연구 기록 검색 · 감사 거버넌스", owner: "히스토리·거버넌스", owns: "run/gen 아카이브, ResultDetail, Compare, 연구 기록 검색, audit/verdict append-only 거버넌스", notOwner: "위키 큐레이션·분석 편집·final approval/export", primarySurface: "V4History", emptyState: "run/세대 또는 검색 필터 조정", legacyAliases: ["records", "audit", "verdict"], internalAliases: ["governance"], prototypeAliases: [] },
  { key: "workbench", label: "성과", full: "성과 · 후보 비교", badge: "HALL", hint: "후보 비교 · 명예의 전당은 후속 소유권 이관 대상", owner: "성과·후보 비교", owns: "후보 심층 분석과 비교; 명예의 전당은 후속 V5.5 이관 전까지 완성된 정본 표면이 아님", notOwner: "히스토리 거버넌스·append-only 결정·final approval", primarySurface: "V4Workbench", emptyState: "run 선택 또는 분석 데이터 대기", legacyAliases: ["pro"], internalAliases: [], prototypeAliases: [] },
  { key: "reports", label: "Reports", full: "Reports · Wiki", badge: "DOC", hint: "리포트 HTML 안전 뷰어 · Wiki 목적지 기록 · 읽기 전용", owner: "리포트·Wiki", owns: "읽기 전용 리포트 뷰어와 Wiki 목적지 기록", notOwner: "판정 정본·전략 승인·카탈로그를 권위 있는 연구 API로 주장", primarySurface: "V4Reports", emptyState: "리포트 선택 대기", legacyAliases: ["wiki"], internalAliases: [], prototypeAliases: ["catalog"] },
];

const PHASE2_SOURCE_INVENTORY = [
  { surface: "history_records", ownerFiles: ["research-records-panel.jsx", "rp-heatmap.jsx", "bt-result-area.jsx", "research-index.jsx", "dashboard-pages.jsx"], endpoints: ["GET /runs", "GET /bt/evo_gens", "GET /bt/result", "GET /research_records", "GET /research_index", "GET /research_index/detail"], fields: ["run_id", "gen_no", "ResultDetailBody", "Compare", "condition_identity", "evidence_id", "source_path", "exact_link", "summary"], sentinels: ["History owns ResultDetail/Compare", "Workbench handoff only", "route alias history->records", "inert <pre>", "visible row cap"] },
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
  return DASHBOARD_PAGE_OWNER_MATRIX.find(item =>
    item.key === key || [item.legacyAliases, item.internalAliases, item.prototypeAliases].some(keys => keys.includes(key))
  ) || DASHBOARD_PAGE_OWNER_MATRIX[0];
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
          <div className="phase2-inventory-kicker mono">V5 CANONICAL DESTINATION INVENTORY</div>
          <b>페이지 역할 · 소스 소유권 · 성능 기준</b>
        </div>
        <span className="mono">{pageCount} canonical destinations · {PHASE2_SOURCE_INVENTORY.length} source groups</span>
      </div>
      <p>
        이 인벤토리는 일반 레일의 여섯 정본 목적지와 호환 별칭만 기록합니다. 별칭은 새 페이지가 아니며,
        prototype 표면은 명시적 rollback 계약에서만 접근합니다.
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
