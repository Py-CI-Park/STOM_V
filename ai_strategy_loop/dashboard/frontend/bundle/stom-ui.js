const a = (n) => typeof n == "number" ? n.toFixed(3) : "—", f = (n) => typeof n == "number" ? `${n.toFixed(2)}%` : "—", l = (n) => typeof n != "number" ? "—" : (n > 0 ? "+" : n < 0 ? "−" : "") + Math.abs(n).toLocaleString("ko-KR") + "원", m = (n) => typeof n == "number" ? n.toLocaleString("ko-KR") : "—", d = (n) => {
  if (!n) return "—";
  try {
    return new Date(n).toLocaleTimeString("ko-KR", { hour12: !1 });
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
function s(n) {
  return n === "demo";
}
function p(n, t) {
  if (s(n)) return !1;
  const e = t && t.current_run;
  return !!!(e && (e.equity && e.equity.length || e.generation && (e.generation.buy_code_partial || e.generation.sell_code_partial)));
}
function h(n, t, e) {
  const r = Number(n), o = Number(t), c = Math.max(2, Math.floor(Number(e) || 5));
  if (!isFinite(r) || !isFinite(o)) return [];
  if (o === r) return [r];
  const u = [];
  for (let i = 0; i < c; i++) u.push(r + (o - r) * i / (c - 1));
  return u;
}
function b(n) {
  const t = Number(n);
  return n == null || !isFinite(t) ? "—" : Math.round(t).toLocaleString("ko-KR");
}
function y(n) {
  const t = String(n ?? 0).padStart(6, "0");
  return t.slice(0, 2) + ":" + t.slice(2, 4) + ":" + t.slice(4, 6);
}
typeof window < "u" && Object.assign(window, {
  fmtScore: a,
  fmtPct: f,
  fmtMoney: l,
  fmtInt: m,
  fmtTime: d,
  STATUS_KR: g,
  isDemoSource: s,
  livePanelPending: p,
  _axisTicks: h,
  _priceTick: b,
  _hmsTimeLabel: y
});
export {
  g as STATUS_KR,
  h as _axisTicks,
  y as _hmsTimeLabel,
  b as _priceTick,
  m as fmtInt,
  l as fmtMoney,
  f as fmtPct,
  a as fmtScore,
  d as fmtTime,
  s as isDemoSource,
  p as livePanelPending
};
