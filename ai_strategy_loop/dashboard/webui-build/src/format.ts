// format.ts — Phase14.6 TS 점진 시드: 공유 순수 유틸의 타입 명시 정본(빌드 입력).
//   format.mjs 를 .ts 로 전환(타입 안전망). 런타임 동작·window 전역 계약은 불변.
//   소비처(.jsx)는 여전히 window.fmt*/_axisTicks 로 호출(런타임 계약 동일).

export const fmtScore = (v: unknown): string => (typeof v === "number" ? v.toFixed(3) : "—");

export const fmtPct = (v: unknown): string => (typeof v === "number" ? `${v.toFixed(2)}%` : "—");

export const fmtMoney = (v: unknown): string => {
  if (typeof v !== "number") return "—";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return sign + Math.abs(v).toLocaleString("ko-KR") + "원";
};

export const fmtInt = (v: unknown): string => (typeof v === "number" ? v.toLocaleString("ko-KR") : "—");

export const fmtTime = (iso: unknown): string => {
  if (!iso) return "—";
  try {
    const d = new Date(iso as string | number | Date);
    return d.toLocaleTimeString("ko-KR", { hour12: false });
  } catch { return "—"; }
};

export const STATUS_KR: Record<string, string> = {
  idle: "대기",
  running: "실행중",
  stopping: "정지중",
  complete: "완료",
  error: "오류",
};

// 순수 판정 함수: 현재 상태가 데모 시뮬레이터 출처인지.
export function isDemoSource(wsStatus: unknown): boolean {
  return wsStatus === "demo";
}

interface RunStateLike {
  current_run?: {
    equity?: unknown[];
    generation?: { buy_code_partial?: string; sell_code_partial?: string };
  } | null;
}

// 순수 판정 함수: 라이브 상태인데 DEMO 전용 패널 데이터가 비었는지.
export function livePanelPending(wsStatus: unknown, state: RunStateLike | null | undefined): boolean {
  if (isDemoSource(wsStatus)) return false;            // 데모는 자체 데이터로 채움
  const cr = state && state.current_run;
  const hasRich = !!(cr && ((cr.equity && cr.equity.length) ||
                            (cr.generation && (cr.generation.buy_code_partial ||
                                               cr.generation.sell_code_partial))));
  return !hasRich;                                     // 라이브인데 풍부 필드 없음 → 대기
}

// 축 눈금 값 배열(min~max 를 cnt 등분, 양끝 포함). 중간 눈금 라벨용. 무예외.
export function _axisTicks(min: unknown, max: unknown, cnt?: unknown): number[] {
  const lo = Number(min), hi = Number(max);
  const n = Math.max(2, Math.floor(Number(cnt) || 5));
  if (!isFinite(lo) || !isFinite(hi)) return [];
  if (hi === lo) return [lo];
  const out: number[] = [];
  for (let i = 0; i < n; i++) out.push(lo + ((hi - lo) * i) / (n - 1));
  return out;
}

// 가격 축 눈금 라벨(원, 천단위 콤마). P3 de-dup: simulation-charts(_simPriceTick)·
//   sim-live-chart(_slcPriceTick) 동일 로직의 단일 출처. null/비유한값 → "—"(슈퍼셋 가드).
export function _priceTick(v: unknown): string {
  const n = Number(v);
  return (v == null || !isFinite(n)) ? "—" : Math.round(n).toLocaleString("ko-KR");
}

// HMS(HHMMSS) 시각 라벨 "HH:MM:SS". P3 de-dup: simulation-charts(_simTimeLabel)·
//   sim-live-chart(_slcTimeLabel) 동일 로직의 단일 출처. null → 0 으로 안전 보정(슈퍼셋).
export function _hmsTimeLabel(hms: unknown): string {
  const s = String(hms == null ? 0 : hms).padStart(6, "0");
  return s.slice(0, 2) + ":" + s.slice(2, 4) + ":" + s.slice(4, 6);
}

// 빌드 번들이 window 전역으로 공유 순수 유틸을 제공(소비처는 babel/build 무관 동일 호출).
if (typeof window !== "undefined") {
  Object.assign(window, {
    fmtScore, fmtPct, fmtMoney, fmtInt, fmtTime,
    STATUS_KR, isDemoSource, livePanelPending,
    _axisTicks, _priceTick, _hmsTimeLabel,
  });
}
