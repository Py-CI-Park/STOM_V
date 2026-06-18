const l = (e) => typeof e == "number" ? e.toFixed(3) : "—", a = (e) => typeof e == "number" ? `${e.toFixed(2)}%` : "—", f = (e) => typeof e != "number" ? "—" : (e > 0 ? "+" : e < 0 ? "−" : "") + Math.abs(e).toLocaleString("ko-KR") + "원", m = (e) => typeof e == "number" ? e.toLocaleString("ko-KR") : "—", d = (e) => {
  if (!e) return "—";
  try {
    return new Date(e).toLocaleTimeString("ko-KR", { hour12: !1 });
  } catch {
    return "—";
  }
}, g = {
  idle: "대기",
  running: "실행중",
  stopping: "정지중",
  complete: "완료",
  error: "오류"
};
function u(e) {
  return e === "demo";
}
function y(e, t) {
  if (u(e)) return !1;
  const n = t && t.current_run;
  return !!!(n && (n.equity && n.equity.length || n.generation && (n.generation.buy_code_partial || n.generation.sell_code_partial)));
}
function p(e, t, n) {
  const i = Number(e), r = Number(t), c = Math.max(2, Math.floor(Number(n) || 5));
  if (!isFinite(i) || !isFinite(r)) return [];
  if (r === i) return [i];
  const s = [];
  for (let o = 0; o < c; o++) s.push(i + (r - i) * o / (c - 1));
  return s;
}
function S(e) {
  const t = Number(e);
  return e == null || !isFinite(t) ? "—" : Math.round(t).toLocaleString("ko-KR");
}
function k(e) {
  const t = String(e ?? 0).padStart(6, "0");
  return t.slice(0, 2) + ":" + t.slice(2, 4) + ":" + t.slice(4, 6);
}
const b = [
  {
    key: "seed",
    title: "시드 선택",
    icon: "🌱",
    desc: "사람이 검증한 출발 전략(시드)을 고릅니다. 이후 모든 진화의 기준점이 됩니다.",
    terms: [["시드", "진화의 출발이 되는 기준 전략(예: Tick_902)."]]
  },
  {
    key: "gen",
    title: "후보 생성 (LLM)",
    icon: "🧬",
    desc: "LLM이 직전 세대의 부검(왜 졌는지)을 컨텍스트로 새 매수/매도 조건식을 생성합니다.",
    terms: [["세대", "한 번의 생성→평가 사이클. gen_00, gen_01 …로 번호가 매겨집니다."]]
  },
  {
    key: "grid",
    title: "격자 탐색",
    icon: "▦",
    desc: "파라미터(θ)를 격자(grid)로 훑어 어느 조합이 견고한지 지형을 만듭니다. 단일 피크가 아닌 '고원'을 찾습니다.",
    terms: [
      ["격자", "여러 파라미터 값을 바둑판처럼 조합해 전수 탐색하는 방식."],
      ["고원/mesa", "이웃 파라미터도 모두 흑자인 안정 영역 — 과최적화가 아닌 진짜 우위."]
    ]
  },
  {
    key: "bt",
    title: "백테스트 평가",
    icon: "📊",
    desc: "지정 기간·시간단위로 자본곡선·낙폭(MDD)·매매를 시뮬레이션해 성과를 측정합니다.",
    terms: [["MDD", "최대 낙폭 — 고점 대비 가장 크게 빠진 비율. 작을수록 안전."]]
  },
  {
    key: "gate",
    title: "적합도 / 품질 게이트",
    icon: "🚦",
    desc: "점수 ≥ 목표 & MDD ≤ 상한 & 거래수 ≥ 하한을 동시에 만족해야 통과합니다. 품질은 결과의 견고함을 봅니다.",
    terms: [
      ["적합도(fitness)", "손익·MDD·거래수·일관성의 가중합 점수."],
      ["니치", "특정 환경(시간대·시총)에 특화된 전략 군집."]
    ]
  },
  {
    key: "oos",
    title: "OOS 검증",
    icon: "🔬",
    desc: "학습에 쓰지 않은 기간(Out-Of-Sample)에서 성과가 유지되는지 확인합니다. 과최적화를 거르는 핵심 관문.",
    terms: [["OOS", "Out-Of-Sample — 최적화에 쓰지 않은 미래/별도 구간. 진짜 일반화 검증."]]
  },
  {
    key: "freeze",
    title: "명예의 전당 / 동결",
    icon: "🏆",
    desc: "검증을 통과한 전략을 명예의 전당에 올리고, 더 이상 바뀌지 않도록 동결(freeze)해 운영 후보로 보관합니다.",
    terms: [["동결", "전략을 고정·박제해 재현 가능한 기준선으로 보존하는 것."]]
  }
];
typeof window < "u" && Object.assign(window, {
  fmtScore: l,
  fmtPct: a,
  fmtMoney: f,
  fmtInt: m,
  fmtTime: d,
  STATUS_KR: g,
  isDemoSource: u,
  livePanelPending: y,
  _axisTicks: p,
  _priceTick: S,
  _hmsTimeLabel: k,
  STOM_PIPELINE: b
});
export {
  g as STATUS_KR,
  b as STOM_PIPELINE,
  p as _axisTicks,
  k as _hmsTimeLabel,
  S as _priceTick,
  m as fmtInt,
  f as fmtMoney,
  a as fmtPct,
  l as fmtScore,
  d as fmtTime,
  u as isDemoSource,
  y as livePanelPending
};
