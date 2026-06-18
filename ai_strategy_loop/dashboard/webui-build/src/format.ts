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

// 진화 프로세스 7단계 — P4 통합 정본(research-lab `_RL_PIPELINE` + research-pro `RP_PIPELINE`의
//   단일 출처). 두 사본은 같은 7단계·아이콘이고 문구만 상세도가 달랐다 → 더 풍부한 RP 판본 +
//   라우팅용 `key` 필드를 정본으로 채택(RL 사본의 모든 의미를 포함하는 슈퍼셋). 소비처(.jsx)는
//   window.STOM_PIPELINE 로 참조(pre-app 전역, no-TDZ, .jsx collision 검사 면제 — C2 규칙).
export interface PipelineStage {
  key: string;
  title: string;
  icon: string;
  desc: string;
  terms: [string, string][];
}

export const STOM_PIPELINE: PipelineStage[] = [
  { key: "seed", title: "시드 선택", icon: "🌱",
    desc: "사람이 검증한 출발 전략(시드)을 고릅니다. 이후 모든 진화의 기준점이 됩니다.",
    terms: [["시드", "진화의 출발이 되는 기준 전략(예: Tick_902)."]] },
  { key: "gen", title: "후보 생성 (LLM)", icon: "🧬",
    desc: "LLM이 직전 세대의 부검(왜 졌는지)을 컨텍스트로 새 매수/매도 조건식을 생성합니다.",
    terms: [["세대", "한 번의 생성→평가 사이클. gen_00, gen_01 …로 번호가 매겨집니다."]] },
  { key: "grid", title: "격자 탐색", icon: "▦",
    desc: "파라미터(θ)를 격자(grid)로 훑어 어느 조합이 견고한지 지형을 만듭니다. 단일 피크가 아닌 '고원'을 찾습니다.",
    terms: [["격자", "여러 파라미터 값을 바둑판처럼 조합해 전수 탐색하는 방식."],
            ["고원/mesa", "이웃 파라미터도 모두 흑자인 안정 영역 — 과최적화가 아닌 진짜 우위."]] },
  { key: "bt", title: "백테스트 평가", icon: "📊",
    desc: "지정 기간·시간단위로 자본곡선·낙폭(MDD)·매매를 시뮬레이션해 성과를 측정합니다.",
    terms: [["MDD", "최대 낙폭 — 고점 대비 가장 크게 빠진 비율. 작을수록 안전."]] },
  { key: "gate", title: "적합도 / 품질 게이트", icon: "🚦",
    desc: "점수 ≥ 목표 & MDD ≤ 상한 & 거래수 ≥ 하한을 동시에 만족해야 통과합니다. 품질은 결과의 견고함을 봅니다.",
    terms: [["적합도(fitness)", "손익·MDD·거래수·일관성의 가중합 점수."],
            ["니치", "특정 환경(시간대·시총)에 특화된 전략 군집."]] },
  { key: "oos", title: "OOS 검증", icon: "🔬",
    desc: "학습에 쓰지 않은 기간(Out-Of-Sample)에서 성과가 유지되는지 확인합니다. 과최적화를 거르는 핵심 관문.",
    terms: [["OOS", "Out-Of-Sample — 최적화에 쓰지 않은 미래/별도 구간. 진짜 일반화 검증."]] },
  { key: "freeze", title: "명예의 전당 / 동결", icon: "🏆",
    desc: "검증을 통과한 전략을 명예의 전당에 올리고, 더 이상 바뀌지 않도록 동결(freeze)해 운영 후보로 보관합니다.",
    terms: [["동결", "전략을 고정·박제해 재현 가능한 기준선으로 보존하는 것."]] },
];

// 빌드 번들이 window 전역으로 공유 순수 유틸을 제공(소비처는 babel/build 무관 동일 호출).
if (typeof window !== "undefined") {
  Object.assign(window, {
    fmtScore, fmtPct, fmtMoney, fmtInt, fmtTime,
    STATUS_KR, isDemoSource, livePanelPending,
    _axisTicks, _priceTick, _hmsTimeLabel,
    STOM_PIPELINE,
  });
}
