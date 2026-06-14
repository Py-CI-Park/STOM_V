const r = (e) => typeof e == "number" ? e.toFixed(3) : "—", i = (e) => typeof e == "number" ? `${e.toFixed(2)}%` : "—", c = (e) => typeof e != "number" ? "—" : (e > 0 ? "+" : e < 0 ? "−" : "") + Math.abs(e).toLocaleString("ko-KR") + "원", u = (e) => typeof e == "number" ? e.toLocaleString("ko-KR") : "—", s = (e) => {
  if (!e) return "—";
  try {
    return new Date(e).toLocaleTimeString("ko-KR", { hour12: !1 });
  } catch {
    return "—";
  }
}, a = {
  idle: "대기",
  running: "실행중",
  stopping: "정지중",
  complete: "완료",
  error: "오류"
};
function o(e) {
  return e === "demo";
}
function f(e, t) {
  if (o(e)) return !1;
  const n = t && t.current_run;
  return !!!(n && (n.equity && n.equity.length || n.generation && (n.generation.buy_code_partial || n.generation.sell_code_partial)));
}
typeof window < "u" && Object.assign(window, {
  fmtScore: r,
  fmtPct: i,
  fmtMoney: c,
  fmtInt: u,
  fmtTime: s,
  STATUS_KR: a,
  isDemoSource: o,
  livePanelPending: f
});
export {
  a as STATUS_KR,
  u as fmtInt,
  c as fmtMoney,
  i as fmtPct,
  r as fmtScore,
  s as fmtTime,
  o as isDemoSource,
  f as livePanelPending
};
