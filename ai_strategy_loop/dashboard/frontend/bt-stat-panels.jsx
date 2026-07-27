/* Backtest workbench analysis charts — 통계·기여·비교 패널 묶음 (split from backtest-charts.jsx).
   매도조건 분해·종목 기여·인사이트·오더플로우·통계검정·A/B 비교 — 표/리스트 위주 패널.
   chart.jsx 의 디자인 언어(chart-wrap·chart-axis-text·panel·LegendDot)를 따른다.
*/
import { LegendDot, MetricHelpStrip } from "./chart.jsx";
import {
  useState_btc, _btMoneyTick, _btAxisTicks, _BtChartEmpty,
} from "./bt-chart-utils.jsx";

/* ⑥ 매도조건 분해 미니 패널 — analysis.exit_reasons [{reason,count,total_pnl,win_rate}].
   가로 막대(총손익 절대값 기준), 우측에 거래수/승률. */
function BtExitReasonPanel({ rows }) {
  const items = Array.isArray(rows) ? rows : [];
  const maxAbs = Math.max(1, ...items.map(r => Math.abs(r.total_pnl || 0)));
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          매도조건별 손익 분해
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>청산사유 기준</span>
      </div>
      <div className="panel-bd">
        {items.length === 0 ? (
          <div className="research-empty">매도조건 데이터가 없습니다</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {items.map((r, i) => {
              const frac = Math.abs(r.total_pnl || 0) / maxAbs;
              const pos = (r.total_pnl || 0) >= 0;
              return (
                <div key={i} className="bt-exit-row">
                  <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)", width: 96, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flexShrink: 0 }}>
                    {r.reason}
                  </span>
                  <div className="bt-exit-track">
                    <div className="bt-exit-fill" style={{
                      width: (frac * 100).toFixed(1) + "%",
                      background: pos ? "var(--teal)" : "var(--red)", opacity: 0.75,
                    }}></div>
                  </div>
                  <span className={"mono " + (pos ? "num-pos" : "num-neg")} style={{ fontSize: 10.5, width: 88, textAlign: "right", flexShrink: 0 }}>
                    {fmtMoney(r.total_pnl)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", width: 78, textAlign: "right", flexShrink: 0 }}>
                    {r.count}건·{fmtPct(r.win_rate)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

function BtContribTable({ title, rows }) {
  return (
    <div>
      <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 6 }}>
        {title}
      </div>
      {(!rows || rows.length === 0) ? (
        <div className="research-empty">데이터 없음</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {rows.map((r, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 6px", borderBottom: "1px solid var(--line-1)" }}>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.name}
              </span>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>{r.trades}건</span>
              <span className={"mono " + (r.profit_krw > 0 ? "num-pos" : r.profit_krw < 0 ? "num-neg" : "")}
                    style={{ fontSize: 11, flexShrink: 0, width: 96, textAlign: "right" }}>
                {fmtMoney(r.profit_krw)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const _BT_SEVERITY = {
  critical: { color: "var(--red)", bg: "rgba(255,107,107,0.07)", border: "rgba(255,107,107,0.3)", label: "위험" },
  warning:  { color: "var(--amber)", bg: "rgba(240,179,90,0.07)", border: "rgba(240,179,90,0.3)", label: "주의" },
  info:     { color: "var(--teal)", bg: "rgba(76,214,179,0.06)", border: "rgba(76,214,179,0.28)", label: "정보" },
};

function BtInsightsPanel({ insights }) {
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--violet)" }}></span>인사이트</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>규칙 기반 자동 진단</span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {(!insights || insights.length === 0) ? (
          <div className="research-empty">생성된 인사이트가 없습니다 (거래 부족 또는 특이사항 없음).</div>
        ) : insights.map((ins, i) => {
          const sev = _BT_SEVERITY[ins.severity] || _BT_SEVERITY.info;
          const sevClass = "bt-insight-card sev-" + (_BT_SEVERITY[ins.severity] ? ins.severity : "info");
          return (
            <div key={i} className={sevClass} style={{
              border: "1px solid " + sev.border, background: sev.bg, borderRadius: 6, padding: "9px 11px",
              display: "flex", flexDirection: "column", gap: 3,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span className="tag-slim" style={{ color: sev.color, borderColor: sev.border }}>{sev.label}</span>
                <strong style={{ fontSize: 12.5, color: "var(--ink-0)" }}>{ins.title}</strong>
              </div>
              <span style={{ fontSize: 12, color: "var(--ink-1)", lineHeight: 1.5 }}>{ins.detail}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ⑧ 오더플로우 진입 프로파일 — analysis orderflow {wins, losses, separation}.
   변수별 승/패 분포(p10~p90 박스 비교, SVG) + 분리력 순위 리스트. */
function BtOrderflowPanel({ orderflow }) {
  const sep = (orderflow && orderflow.separation) || [];
  const wins = (orderflow && orderflow.wins) || {};
  const losses = (orderflow && orderflow.losses) || {};

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          오더플로우 — 이기는 진입 프로파일
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="승 진입" />
          <LegendDot color="var(--red)" label="패 진입" />
        </div>
      </div>
      <div className="panel-bd">
        {/* v5.13.0 — "오더플로우가 뭘 뜻하는지 모르겠다" 피드백: 비유 먼저, 그 다음 기술 설명. */}
        <p className="mono" style={{ margin: "0 0 10px", fontSize: 11.5, color: "var(--ink-2)", lineHeight: 1.6 }}>
          오더플로우 = <b>매수 버튼을 누르던 순간의 시장 상태</b>입니다. 가게로 치면 "손님이 몰려드는
          중이었나, 빠져나가는 중이었나"를 보는 것 — 체결강도·호가잔량 같은 주문 흐름 변수를 기준으로,
          이긴 진입과 진 진입의 시장 상태가 어떻게 달랐는지 비교합니다. 승/패 분포가 뚜렷이 갈리는
          변수일수록 매수 조건식에 넣을 필터 후보입니다.
        </p>
        {sep.length === 0 ? (
          <div className="research-empty">오더플로우 데이터가 없습니다 (B_체결강도·잔량 등 결측)</div>
        ) : (
          <>
            <MetricHelpStrip items={[
              "변수별 승/패 진입 분포(p10~p90) 비교",
              "박스 = p25~p75 · 세로선 = 중앙값(p50)",
              "분리력 = 승패 중앙값 차 절대값 순위",
            ]} />
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {sep.map((s) => (
                <_BtOfRow key={s.var} sep={s} win={wins[s.var]} loss={losses[s.var]} />
              ))}
            </div>
            <div style={{ marginTop: 12, borderTop: "1px solid var(--line-1)", paddingTop: 8 }}>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 6 }}>
                분리력 순위
              </div>
              {sep.map((s, i) => (
                <div key={s.var} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 11, fontFamily: "var(--mono)" }}>
                  <span style={{ color: "var(--ink-3)", width: 16 }}>{i + 1}.</span>
                  <span style={{ color: "var(--ink-1)", flex: 1 }}>{s.label}</span>
                  <span style={{ color: "var(--teal)" }}>{s.win_p50.toFixed(2)}</span>
                  <span style={{ color: "var(--ink-3)" }}>vs</span>
                  <span style={{ color: "var(--red)" }}>{s.loss_p50.toFixed(2)}</span>
                  <span className={s.diff > 0 ? "num-pos" : "num-neg"} style={{ width: 70, textAlign: "right" }}>
                    {s.diff > 0 ? "+" : ""}{s.diff.toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// 오더플로우 변수 1개 — 승/패 분포 가로 박스 비교(공통 도메인 정규화).
function _BtOfRow({ sep, win, loss }) {
  const w = win || {}, l = loss || {};
  const vals = [w.p10, w.p90, l.p10, l.p90, w.p50, l.p50].filter(v => typeof v === "number");
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const span = (hi - lo) || 1;
  const fx = (v) => typeof v === "number" ? ((v - lo) / span) * 100 : 0;
  const box = (d, color) => (typeof d.p25 === "number" && typeof d.p75 === "number") ? (
    <div style={{ position: "relative", height: 16, flex: 1 }}>
      {/* whisker p10~p90 */}
      <div style={{ position: "absolute", top: 7, height: 2, background: color, opacity: 0.4,
                    left: fx(d.p10) + "%", width: Math.max(1, fx(d.p90) - fx(d.p10)) + "%" }} />
      {/* box p25~p75 */}
      <div style={{ position: "absolute", top: 2, height: 12, borderRadius: 2,
                    left: fx(d.p25) + "%", width: Math.max(1, fx(d.p75) - fx(d.p25)) + "%",
                    background: color === "var(--teal)" ? "rgba(76,214,179,0.25)" : "rgba(255,107,107,0.25)",
                    border: "1px solid " + color }} />
      {/* p50 */}
      <div style={{ position: "absolute", top: 0, height: 16, width: 2, background: color, left: fx(d.p50) + "%" }} />
    </div>
  ) : <div style={{ flex: 1, fontSize: 10, color: "var(--ink-3)" }}>표본 부족</div>;
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 2 }}>
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)", width: 86, flexShrink: 0 }}>{sep.label}</span>
        <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>승 n={w.n || 0} · 패 n={l.n || 0}</span>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="mono" style={{ fontSize: 9, color: "var(--teal)", width: 20 }}>승</span>{box(w, "var(--teal)")}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="mono" style={{ fontSize: 9, color: "var(--red)", width: 20 }}>패</span>{box(l, "var(--red)")}
        </div>
      </div>
    </div>
  );
}

/* ⑨ 통계 검정 인사이트 패널 — analysis stats [{kind,bucket,label,n,mean,p_value,significant,underpowered}].
   유의(p<0.05) 항목 강조 · 표본 부족 경고. 요일/시간대 효과 신뢰도 구분. */
function BtStatTestPanel({ stats }) {
  const rows = Array.isArray(stats) ? stats : [];
  const sig = rows.filter(r => r.significant);
  if (rows.length === 0) {
    return (
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>통계 검정</div>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>요일·시간대 효과</span>
        </div>
        <div className="panel-bd"><div className="research-empty">버킷이 부족해 검정을 수행하지 못했습니다 (요일/시간대 2종 이상 필요).</div></div>
      </div>
    );
  }
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>통계 검정</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>유의 {sig.length}건 / 전체 {rows.length}버킷</span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {rows.map((r, i) => {
          const pos = r.mean > 0;
          return (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 8, padding: "5px 8px", borderRadius: 5, fontSize: 11, fontFamily: "var(--mono)",
              border: "1px solid " + (r.significant ? (pos ? "rgba(76,214,179,0.4)" : "rgba(255,107,107,0.4)") : "var(--line-1)"),
              background: r.significant ? (pos ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)") : "var(--bg-0)",
            }}>
              <span style={{ color: "var(--ink-3)", width: 56 }}>{r.kind === "weekday" ? "요일" : "시간대"}</span>
              <span style={{ color: "var(--ink-1)", width: 48 }}>{r.label}</span>
              <span className={pos ? "num-pos" : "num-neg"} style={{ width: 64, textAlign: "right" }}>{r.mean > 0 ? "+" : ""}{r.mean.toFixed(2)}%</span>
              <span style={{ color: "var(--ink-3)", width: 56, textAlign: "right" }}>n={r.n}</span>
              <span style={{ flex: 1, textAlign: "right" }}>
                {r.underpowered ? (
                  <span style={{ color: "var(--ink-3)" }}>표본 부족</span>
                ) : r.significant ? (
                  <span style={{ color: pos ? "var(--teal)" : "var(--red)" }}>유의 (p={r.p_value != null ? r.p_value.toFixed(3) : "—"})</span>
                ) : (
                  <span style={{ color: "var(--ink-3)" }}>p={r.p_value != null ? r.p_value.toFixed(3) : "—"}</span>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ⑩ A/B 비교 뷰 — /bt/compare {a, b, delta}.
   수익곡선 오버레이(A 실선 / B 점선, 정규화 토글) + 메트릭 나란히 표(delta 색상·우세 하이라이트). */
const _BT_CMP_METRICS = [
  { key: "trade_count", label: "거래수", fmt: (v) => fmtInt(v), higher: true },
  { key: "win_rate", label: "승률", fmt: (v) => fmtPct(v), higher: true },
  { key: "total_profit_pct", label: "수익률합", fmt: (v) => fmtPct(v), higher: true },
  { key: "total_profit_krw", label: "수익금", fmt: (v) => fmtMoney(v), higher: true },
  { key: "max_drawdown_pct", label: "MDD", fmt: (v) => fmtPct(v), higher: false },
  { key: "profit_factor", label: "PF", fmt: (v) => (v != null ? v.toFixed(2) : "—"), higher: true },
  { key: "payoff_ratio", label: "Payoff", fmt: (v) => (v != null ? v.toFixed(2) : "—"), higher: true },
  { key: "sharpe", label: "Sharpe", fmt: (v) => (v != null ? v.toFixed(2) : "—"), higher: true },
];

function BtCompareView({ cmp, onClose }) {
  const [norm, setNorm] = useState_btc(true);   // 정규화(시작점 100) 토글.
  const a = cmp && cmp.a, b = cmp && cmp.b;
  const delta = (cmp && cmp.delta) || {};

  const cumA = (a && a.equity && a.equity.cumulative) || [];
  const cumB = (b && b.equity && b.equity.cumulative) || [];

  const W = 880, H = 280;
  const padL = 58, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // 정규화: 시작점 100 기준 (시작 누적이 0 일 수 있으므로 첫 값 기준 가산 방식).
  const toSeries = (cum) => {
    const arr = cum.map(c => c.cum_profit || 0);
    if (!norm) return arr;
    const base = arr.length ? arr[0] : 0;
    // 시작 100 + 누적증분 비율 — base 가 0 이면 절대 증분에 100 가산(스케일 통일).
    return arr.map(v => 100 + (v - base));
  };
  const sA = toSeries(cumA), sB = toSeries(cumB);
  const allV = [...sA, ...sB];
  const yMin = allV.length ? Math.min(...allV) : 0;
  const yMax = allV.length ? Math.max(...allV) : 1;
  const yRange = (yMax - yMin) || 1;
  const nMax = Math.max(sA.length, sB.length);
  const x = (i) => nMax > 1 ? padL + (i / (nMax - 1)) * innerW : padL + innerW / 2;
  const y = (v) => padT + innerH - ((v - yMin) / yRange) * innerH;
  const pathOf = (s) => s.length < 2 ? "" : s.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          A / B 비교
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label={"A " + (a ? a.job_id : "—")} />
          <LegendDot color="var(--violet)" label={"B " + (b ? b.job_id : "—")} />
          <button className="btn ghost sm" onClick={() => setNorm(v => !v)}>
            {norm ? "정규화 ON" : "정규화 OFF"}
          </button>
          {onClose && <button className="btn ghost sm" onClick={onClose}>✕ 닫기</button>}
        </div>
      </div>
      <div className="panel-bd">
        {(!a && !b) ? (
          <div className="research-empty">비교할 잡을 선택하세요.</div>
        ) : (
          <>
            {/* 수익곡선 오버레이 */}
            <div className="chart-wrap" style={{ marginBottom: 14 }}>
              <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
                <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
                <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
                <text className="chart-axis-text" x={padL - 8} y={y(yMax) + 3} textAnchor="end">{norm ? yMax.toFixed(0) : _btMoneyTick(yMax)}</text>
                <text className="chart-axis-text" x={padL - 8} y={y(yMin) + 3} textAnchor="end">{norm ? yMin.toFixed(0) : _btMoneyTick(yMin)}</text>
                {/* y 중간 눈금(가로 점선 + 라벨) — max·min 과 겹치면 생략. */}
                {_btAxisTicks(yMin, yMax, 5).map((tv, i) => (
                  (Math.abs(tv - yMax) < 1e-9 || Math.abs(tv - yMin) < 1e-9) ? null : (
                    <g key={`cmpy${i}`}>
                      <line x1={padL} x2={W - padR} y1={y(tv)} y2={y(tv)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                      <text className="chart-axis-text" x={padL - 8} y={y(tv) + 3} textAnchor="end" fill="var(--chart-axis)">{norm ? tv.toFixed(0) : _btMoneyTick(tv)}</text>
                    </g>
                  )
                ))}
                {sA.length > 1 && <path d={pathOf(sA)} fill="none" stroke="var(--chart-profit)" strokeWidth="2" />}
                {sB.length > 1 && <path d={pathOf(sB)} fill="none" stroke="var(--chart-accent)" strokeWidth="2" strokeDasharray="5 4" />}
                {allV.length === 0 && null}
              </svg>
              {allV.length === 0 && <_BtChartEmpty message="비교할 수익곡선이 없습니다" />}
            </div>
            {/* 메트릭 나란히 표 */}
            <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--mono)", fontSize: 11.5 }}>
              <thead>
                <tr style={{ color: "var(--ink-3)", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em" }}>
                  <th style={{ textAlign: "left", padding: "4px 8px" }}>메트릭</th>
                  <th style={{ textAlign: "right", padding: "4px 8px", color: "var(--teal)" }}>A</th>
                  <th style={{ textAlign: "right", padding: "4px 8px", color: "var(--violet)" }}>B</th>
                  <th style={{ textAlign: "right", padding: "4px 8px" }}>Δ (B−A)</th>
                </tr>
              </thead>
              <tbody>
                {_BT_CMP_METRICS.map(m => {
                  const sa = (a && a.summary) || {};
                  const sb = (b && b.summary) || {};
                  const va = sa[m.key], vb = sb[m.key];
                  const d = delta[m.key];
                  // 우세 판정: higher=true 면 큰 쪽, false(MDD) 면 작은 쪽이 우세.
                  let aWin = false, bWin = false;
                  if (typeof va === "number" && typeof vb === "number" && va !== vb) {
                    const aBetter = m.higher ? va > vb : va < vb;
                    aWin = aBetter; bWin = !aBetter;
                  }
                  const dColor = d == null ? "var(--ink-3)"
                    : (m.higher ? d > 0 : d < 0) ? "var(--teal)" : (d === 0 ? "var(--ink-3)" : "var(--red)");
                  return (
                    <tr key={m.key} style={{ borderTop: "1px solid var(--line-1)" }}>
                      <td style={{ textAlign: "left", padding: "5px 8px", color: "var(--ink-2)" }}>{m.label}</td>
                      <td style={{ textAlign: "right", padding: "5px 8px", color: aWin ? "var(--teal)" : "var(--ink-1)", fontWeight: aWin ? 700 : 400 }}>
                        {typeof va === "number" ? m.fmt(va) : "—"}
                      </td>
                      <td style={{ textAlign: "right", padding: "5px 8px", color: bWin ? "var(--violet)" : "var(--ink-1)", fontWeight: bWin ? 700 : 400 }}>
                        {typeof vb === "number" ? m.fmt(vb) : "—"}
                      </td>
                      <td style={{ textAlign: "right", padding: "5px 8px", color: dColor }}>
                        {d == null ? "—" : (d > 0 ? "+" : "") + m.fmt(d)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
}

export {
  BtExitReasonPanel, BtContribTable, BtInsightsPanel,
  BtOrderflowPanel, BtStatTestPanel, BtCompareView,
};
