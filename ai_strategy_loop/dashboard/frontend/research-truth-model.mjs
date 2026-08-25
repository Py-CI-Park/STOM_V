const EXECUTION = Object.freeze({
  SUCCESS: { code: "SUCCESS", label: "정상 완료", tone: "ok", detail: "지표 생성 완료" },
  NO_TRADES: { code: "NO_TRADES", label: "정상 무거래", tone: "warn", detail: "실행은 완료됐지만 경제 표본 없음" },
  ERROR: { code: "ERROR", label: "실행 오류", tone: "bad", detail: "엔진 또는 전략 오류" },
  TIMEOUT: { code: "TIMEOUT", label: "시간 초과", tone: "bad", detail: "종료 원인 확인 필요" },
  CANCELLED: { code: "CANCELLED", label: "실행 취소", tone: "off", detail: "완료 증거 아님" },
  PARTIAL: { code: "PARTIAL", label: "부분 증거", tone: "warn", detail: "종료 계약이 불완전함" },
});

const ECONOMIC = Object.freeze({
  POSITIVE: { code: "POSITIVE", label: "양수 관측" },
  NEGATIVE: { code: "NEGATIVE", label: "음수 관측" },
  INCONCLUSIVE: { code: "INCONCLUSIVE", label: "판정 유보" },
  NOT_EVALUABLE: { code: "NOT_EVALUABLE", label: "평가 불가" },
});

const AUTHORITY = Object.freeze({
  FEASIBILITY: { code: "FEASIBILITY", label: "실행 가능성" },
  DEVELOPMENT: { code: "DEVELOPMENT", label: "개발 연구" },
  FROZEN_OOS: { code: "FROZEN_OOS", label: "동결 OOS" },
  SHADOW: { code: "SHADOW", label: "섀도 관측" },
  LIVE: { code: "LIVE", label: "실전" },
});

const ACTION = Object.freeze({
  DEBUG: { code: "DEBUG", label: "실행 진단", detail: "원인과 재시도 조건을 먼저 확인" },
  REPRODUCE: { code: "REPRODUCE", label: "동일 조건 재현", detail: "identity를 고정하고 다시 확인" },
  STRUCTURAL_REVISE: { code: "STRUCTURAL_REVISE", label: "구조 가설 작성", detail: "threshold가 아닌 역할·상태 구조를 검토" },
  EXPAND: { code: "EXPAND", label: "검증 범위 확장", detail: "사전등록 범위 안에서 증거 추가" },
  STOP: { code: "STOP", label: "연구 중지 기록", detail: "중지 근거를 원장에 남김" },
  HOLDOUT: { code: "HOLDOUT", label: "Holdout 준비", detail: "인간 승인 전 동결 상태 확인" },
});

function entry(table, code, fallbackLabel) {
  const found = table[String(code || "")];
  return found || { code: String(code || "UNKNOWN"), label: fallbackLabel, tone: "off", detail: "계약에 없는 상태" };
}

function blockerFor(truth) {
  switch (truth.execution) {
    case "ERROR":
      return "실행 실패를 해결하기 전에는 경제 KPI를 해석할 수 없습니다.";
    case "TIMEOUT":
      return "원인 분류 전에는 재실행과 경제 KPI 해석을 할 수 없습니다.";
    case "NO_TRADES":
      return "경제 표본이 없어 수익성 판단과 승격을 할 수 없습니다.";
    case "PARTIAL":
    case "CANCELLED":
      return "완료 증거가 아니므로 KPI와 승격 판단을 할 수 없습니다.";
    case "SUCCESS":
      if (truth.economic === "INCONCLUSIVE") {
        return "소표본·강건성 증거 전에는 성과 확장과 승격을 할 수 없습니다.";
      }
      if (truth.authority === "FEASIBILITY") {
        return "양수 관측이어도 재현·사전등록 전에는 승격할 수 없습니다.";
      }
      return "현재 권위와 승인 게이트를 넘는 행동은 할 수 없습니다.";
    default:
      return "상태 계약을 확인하기 전에는 다음 단계로 진행할 수 없습니다.";
  }
}

function shortHash(value) {
  const text = String(value || "");
  return text.length >= 12 ? text.slice(0, 12) : "미기록";
}

function truthPresentation(truth) {
  const safe = truth && typeof truth === "object" ? truth : {};
  const identity = safe.identity && typeof safe.identity === "object" ? safe.identity : {};
  return {
    execution: entry(EXECUTION, safe.execution, "실행 상태 미확인"),
    economic: entry(ECONOMIC, safe.economic, "경제 상태 미확인"),
    authority: entry(AUTHORITY, safe.authority, "권위 미확인"),
    action: entry(ACTION, safe.next_action, "증거 재조회"),
    blocker: blockerFor(safe),
    candidate: String(identity.candidate_id || "후보 미기록"),
    identityStatus: String(identity.identity_status || "UNKNOWN"),
    evidenceHash: shortHash(safe.legacy_input_sha256),
    rawStatus: String(safe.legacy_raw_status || "미기록"),
    failureCause: String(safe.failure_cause || "NONE"),
    corrected: safe.correction_applied === true,
    correctionReason: String(safe.correction_reason || ""),
  };
}

export { truthPresentation };
