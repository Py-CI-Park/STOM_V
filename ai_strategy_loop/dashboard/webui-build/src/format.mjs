// format.mjs — Phase14.1 빌드 소스: connection.jsx 순수 포매터의 ESM 정본.
//
//   connection.jsx(909~941줄) 구현과 "바이트 동일"을 유지한다. 이 동일성이
//   출력 동등성 게이트의 전제다(번들 출력 == 런타임-babel 출력). 14.x에서
//   connection.jsx 가 이 모듈을 import 하도록 전환하면 중복이 사라진다.
//
//   포함: 순수 포매터/판정 함수만. DEFAULT_BASE 는 window.location 의존이라 제외.

export const fmtScore = (v) => (typeof v === "number" ? v.toFixed(3) : "—");

export const fmtPct = (v) => (typeof v === "number" ? `${v.toFixed(2)}%` : "—");

export const fmtMoney = (v) => {
  if (typeof v !== "number") return "—";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return sign + Math.abs(v).toLocaleString("ko-KR") + "원";
};

export const fmtInt = (v) => (typeof v === "number" ? v.toLocaleString("ko-KR") : "—");

export const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("ko-KR", { hour12: false });
  } catch { return "—"; }
};

export const STATUS_KR = {
  idle: "대기",
  running: "실행중",
  stopping: "정지중",
  complete: "완료",
  error: "오류",
};

// 순수 판정 함수(테스트 가능): 현재 상태가 데모 시뮬레이터 출처인지.
export function isDemoSource(wsStatus) {
  return wsStatus === "demo";
}

// 순수 판정 함수(테스트 가능): 라이브 상태인데 DEMO 전용 패널 데이터가 비었는지.
export function livePanelPending(wsStatus, state) {
  if (isDemoSource(wsStatus)) return false;            // 데모는 자체 데이터로 채움
  const cr = state && state.current_run;
  const hasRich = !!(cr && ((cr.equity && cr.equity.length) ||
                            (cr.generation && (cr.generation.buy_code_partial ||
                                               cr.generation.sell_code_partial))));
  return !hasRich;                                     // 라이브인데 풍부 필드 없음 → 대기
}

// 동일 전역 계약 재현: 14.x 전환 시 connection.jsx 의 window 노출을 이 번들이
//   대체할 수 있음을 증명한다(공존 단계에서는 production 경로가 별도로 동일 전역을 채움).
if (typeof window !== "undefined") {
  Object.assign(window, {
    fmtScore, fmtPct, fmtMoney, fmtInt, fmtTime,
    STATUS_KR, isDemoSource, livePanelPending,
  });
}
