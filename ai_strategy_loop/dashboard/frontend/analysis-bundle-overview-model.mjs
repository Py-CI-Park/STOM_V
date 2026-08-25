const EXECUTION = Object.freeze({
  SUCCESS: "정상 완료",
  NO_TRADES: "정상 무거래",
  ERROR: "실행 오류",
  TIMEOUT: "시간 초과",
  CANCELLED: "실행 취소",
  PARTIAL: "부분 증거",
});

const ECONOMIC = Object.freeze({
  POSITIVE: "양수 관측",
  NEGATIVE: "음수 관측",
  INCONCLUSIVE: "판정 유보",
  NOT_EVALUABLE: "평가 불가",
});

const AUTHORITY = Object.freeze({
  FEASIBILITY: "실행 가능성",
  DEVELOPMENT: "개발 연구",
  FROZEN_OOS: "동결 OOS",
  SHADOW: "섀도 관측",
  LIVE: "실전",
});

const ACTION = Object.freeze({
  DEBUG: "실행 진단",
  REPRODUCE: "동일 조건 재현",
  STRUCTURAL_REVISE: "구조 가설 작성",
  EXPAND: "검증 범위 확장",
  STOP: "연구 중지 기록",
  HOLDOUT: "Holdout 준비",
});

const CAPABILITY = Object.freeze({
  OBSERVED: "관측됨",
  NOT_RUN: "미실행",
  NOT_EVALUABLE: "평가 불가",
});

function axis(table, code, fallback) {
  const normalized = String(code || "UNKNOWN");
  return { code: normalized, label: table[normalized] || fallback };
}

function capability(section) {
  const safe = section && typeof section === "object" ? section : {};
  const code = String(safe.status || "NOT_RUN");
  return {
    code,
    label: CAPABILITY[code] || "상태 미확인",
    reason: String(safe.reason || ""),
  };
}

function shortHash(value) {
  const text = String(value || "");
  return text.length >= 12 ? text.slice(0, 12) : "미기록";
}

function bundleOverview(payload) {
  const bundle = payload && payload.bundle && typeof payload.bundle === "object" ? payload.bundle : {};
  const identity = bundle.identity && typeof bundle.identity === "object" ? bundle.identity : {};
  const source = bundle.source && typeof bundle.source === "object" ? bundle.source : {};
  const decision = bundle.decision && typeof bundle.decision === "object" ? bundle.decision : {};
  const execution = bundle.execution && typeof bundle.execution === "object" ? bundle.execution : {};
  const evidence = bundle.evidence && typeof bundle.evidence === "object" ? bundle.evidence : {};
  const preregistration = bundle.preregistration && typeof bundle.preregistration === "object"
    ? bundle.preregistration : {};
  return {
    available: payload && payload.bundle_available === true,
    candidate: String(identity.candidate_id || "후보 미기록"),
    identityStatus: String(identity.identity_status || "UNKNOWN"),
    evidenceId: String(identity.evidence_id || "미기록"),
    bundleHash: shortHash(bundle.content_sha256),
    csvHash: shortHash(source.csv_sha256),
    specHash: shortHash(source.legacy_spec_sha256),
    csvSize: Number.isFinite(Number(source.csv_size_bytes)) ? Number(source.csv_size_bytes) : null,
    preregistration: String(preregistration.status || "NOT_OBSERVED"),
    persistence: String(evidence.persistence || payload?.persistence || "unknown"),
    generatedAtSource: String(evidence.generated_at_source || "not_observed"),
    execution: axis(EXECUTION, execution.status, "실행 상태 미확인"),
    economic: axis(ECONOMIC, decision.economic, "경제 상태 미확인"),
    authority: axis(AUTHORITY, decision.authority, "권위 미확인"),
    action: axis(ACTION, decision.next_action, "행동 미확인"),
    failureCause: String(execution.failure_cause || "NONE"),
    rawStatus: String(execution.legacy_raw_status || "미기록"),
    returnCode: execution.return_code == null ? "미기록" : String(execution.return_code),
    eventCount: execution.event_count == null ? "미기록" : String(execution.event_count),
    rowCount: execution.row_count == null ? "미기록" : String(execution.row_count),
    tradeCount: execution.trade_count == null ? "미기록" : String(execution.trade_count),
    checkpoint: String(execution.checkpoint || "미기록"),
    metrics: capability(bundle.metrics),
    series: capability(bundle.series),
    distribution: capability(bundle.distribution),
    episodes: capability(bundle.episodes),
    attribution: capability(bundle.attribution),
    counterfactual: capability(bundle.counterfactual),
    robustness: capability(bundle.robustness),
  };
}

export { bundleOverview };
