const f = (t) => typeof t == "number" ? t.toFixed(3) : "—", a = (t) => typeof t == "number" ? `${t.toFixed(2)}%` : "—", l = (t) => typeof t != "number" ? "—" : (t > 0 ? "+" : t < 0 ? "−" : "") + Math.abs(t).toLocaleString("ko-KR") + "원", m = (t) => typeof t == "number" ? t.toLocaleString("ko-KR") : "—", d = (t) => {
  if (!t) return "—";
  try {
    return new Date(t).toLocaleTimeString("ko-KR", { hour12: !1 });
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
function s(t) {
  return t === "demo";
}
function h(t, e) {
  if (s(t)) return !1;
  const n = e && e.current_run;
  return !!!(n && (n.equity && n.equity.length || n.generation && (n.generation.buy_code_partial || n.generation.sell_code_partial)));
}
function p(t, e, n) {
  const o = Number(t), r = Number(e), c = Math.max(2, Math.floor(n || 5));
  if (!isFinite(o) || !isFinite(r)) return [];
  if (r === o) return [o];
  const u = [];
  for (let i = 0; i < c; i++) u.push(o + (r - o) * i / (c - 1));
  return u;
}
typeof window < "u" && Object.assign(window, {
  fmtScore: f,
  fmtPct: a,
  fmtMoney: l,
  fmtInt: m,
  fmtTime: d,
  STATUS_KR: g,
  isDemoSource: s,
  livePanelPending: h,
  _axisTicks: p
});
export {
  g as STATUS_KR,
  p as _axisTicks,
  m as fmtInt,
  l as fmtMoney,
  a as fmtPct,
  f as fmtScore,
  d as fmtTime,
  s as isDemoSource,
  h as livePanelPending
};
