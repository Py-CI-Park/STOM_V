/* Chart primitives — 광범위 소비되는 작은 표현 컴포넌트 묶음 (split from chart.jsx, P5.4).
   MetricHelpStrip · LegendDot · Mini — bt-equity-charts · bt-distribution-charts ·
   bt-stat-panels · bt-gui-parity · evolution-analysis 등이 chart.jsx 배럴 경유로 import 한다.
   순수 표현 컴포넌트(외부 의존 없음). stom-ui 디자인 토큰(var(--ink-2) 등)만 사용.
*/

function MetricHelpStrip({ items }) {
  return (
    <div className="metric-help-strip">
      {(items || []).map((item, i) => <span key={i}>{item}</span>)}
    </div>
  );
}

function LegendDot({ color, label, dashed, filled }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10.5, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
      {dashed ? (
        <span style={{ width: 14, height: 0, borderTop: `1px dashed ${color}` }}></span>
      ) : filled === "ring" ? (
        <span style={{ width: 9, height: 9, borderRadius: "50%", background: color, border: "1.5px solid #fff", boxSizing: "border-box" }}></span>
      ) : (
        <span style={{ width: 8, height: 8, borderRadius: "50%", background: color }}></span>
      )}
      {label}
    </span>
  );
}

function Mini({ label, value, sub, color }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>{label}</span>
      <span className="mono" style={{ fontSize: 17, color: color || "var(--ink-0)" }}>{value}</span>
      {sub && <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{sub}</span>}
    </div>
  );
}

// Track Z (PR-3) — dual-safe ESM export (kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { LegendDot, MetricHelpStrip, Mini };
