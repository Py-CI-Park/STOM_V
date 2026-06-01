/* SVG chart for graded_score per generation. */
const { useMemo: useMemo_c, useState: useState_c, useRef: useRef_c } = React;

function FitnessChart({ state, target = 1.0 }) {
  const gens = state.generations || [];
  const bestSoFar = useMemo_c(() => {
    let bs = 0;
    return gens.map(g => {
      bs = Math.max(bs, g.graded_score || 0);
      return bs;
    });
  }, [gens]);

  const W = 880, H = 320;
  const padL = 44, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const xMax = Math.max(state.max_generations, 8);
  const yMax = Math.max(1.15, ...gens.map(g => g.graded_score || 0).concat([target + 0.1]));

  const x = (g) => padL + (g - 0.5) / xMax * innerW; // gen 1 starts a bit in
  const y = (v) => padT + innerH - (v / yMax) * innerH;

  // Y ticks
  const yTicks = [];
  const step = yMax > 1.5 ? 0.5 : 0.2;
  for (let v = 0; v <= yMax + 1e-9; v += step) yTicks.push(+v.toFixed(2));

  // X ticks: every gen if <=15, else every 2 or 5
  const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
  const xTicks = [];
  for (let g = 1; g <= xMax; g++) {
    if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);
  }

  const linePath = useMemo_c(() => {
    if (!gens.length) return "";
    return gens.map((g, i) =>
      `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${y(g.graded_score || 0).toFixed(2)}`
    ).join(" ");
  }, [gens, xMax, yMax]);

  const areaPath = useMemo_c(() => {
    if (!gens.length) return "";
    const start = `M ${x(gens[0].gen_no).toFixed(2)} ${y(0).toFixed(2)}`;
    const mid = gens.map(g => `L ${x(g.gen_no).toFixed(2)} ${y(g.graded_score || 0).toFixed(2)}`).join(" ");
    const end = `L ${x(gens[gens.length - 1].gen_no).toFixed(2)} ${y(0).toFixed(2)} Z`;
    return `${start} ${mid} ${end}`;
  }, [gens, xMax, yMax]);

  const bestPath = useMemo_c(() => {
    if (!gens.length) return "";
    return gens.map((g, i) =>
      `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${y(bestSoFar[i]).toFixed(2)}`
    ).join(" ");
  }, [gens, bestSoFar, xMax, yMax]);

  // Hover state
  const [hover, setHover] = useState_c(null);
  const svgRef = useRef_c(null);

  const onMove = (e) => {
    if (!gens.length) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    // find nearest gen
    let best = null, bestDist = Infinity;
    for (const g of gens) {
      const gx = x(g.gen_no);
      const d = Math.abs(gx - px);
      if (d < bestDist) { bestDist = d; best = g; }
    }
    if (best && bestDist < 40) setHover(best);
    else setHover(null);
  };

  const onLeave = () => setHover(null);

  // Stats summary
  const latest = gens[gens.length - 1];
  const peak = gens.reduce((a, b) => (b.graded_score > (a?.graded_score || 0) ? b : a), null);
  const gatePassedCount = gens.filter(g => g.gate_passed).length;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          적합도 추이 — Fitness Trajectory
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="graded_score" />
          <LegendDot color="var(--violet)" label="best-so-far" dashed />
          <LegendDot color="var(--blue)" label="gate-passed" filled="ring" />
        </div>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="최신 점수" value={latest ? fmtScore(latest.graded_score) : "—"}
                color={latest && latest.graded_score >= target ? "var(--teal)" : undefined} />
          <Mini label="최고 점수" value={peak ? fmtScore(peak.graded_score) : "—"}
                sub={peak ? `gen_${peak.gen_no}` : ""} />
          <Mini label="게이트 통과" value={`${gatePassedCount} / ${gens.length}`}
                color={gatePassedCount > 0 ? "var(--teal)" : undefined} />
          <Mini label="목표" value={target.toFixed(3)} sub="target_score" />
        </div>

        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`}
               preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={onLeave}>
            <defs>
              <linearGradient id="chart-area-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4cd6b3" stopOpacity="0.45" />
                <stop offset="100%" stopColor="#4cd6b3" stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Y gridlines + labels */}
            {yTicks.map((t, i) => (
              <g key={`y${i}`}>
                <line className="chart-grid-line"
                      x1={padL} x2={W - padR}
                      y1={y(t)} y2={y(t)} />
                <text className="chart-axis-text"
                      x={padL - 8} y={y(t) + 3} textAnchor="end">
                  {t.toFixed(t < 10 ? 2 : 0)}
                </text>
              </g>
            ))}
            {/* Target line */}
            <line x1={padL} x2={W - padR} y1={y(target)} y2={y(target)}
                  stroke="rgba(106,166,255,0.4)" strokeWidth="1" strokeDasharray="6 4" />
            <text className="chart-axis-text"
                  x={W - padR - 4} y={y(target) - 4} textAnchor="end"
                  fill="var(--blue)">
              target {target.toFixed(2)}
            </text>

            {/* X labels */}
            {xTicks.map((g, i) => (
              <text key={`x${i}`} className="chart-axis-text"
                    x={x(g)} y={H - 10} textAnchor="middle">
                gen_{g}
              </text>
            ))}

            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                  stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                  stroke="var(--line-2)" strokeWidth="1" />

            {/* Data */}
            {gens.length > 1 && (
              <>
                <path d={areaPath} className="chart-area" />
                <path d={linePath} className="chart-line" />
                <path d={bestPath} className="chart-best-line" />
              </>
            )}
            {/* Points */}
            {gens.map((g, i) => {
              const cx = x(g.gen_no), cy = y(g.graded_score || 0);
              if (g.gate_passed) {
                return <g key={i}>
                  <circle cx={cx} cy={cy} r="7" fill="rgba(165,148,255,0.16)" />
                  <circle cx={cx} cy={cy} r="4" className="chart-pt-gate" />
                </g>;
              }
              if (g.status === "error") {
                return <g key={i}>
                  <line x1={cx-3} y1={cy-3} x2={cx+3} y2={cy+3} stroke="var(--red)" strokeWidth="1.4" />
                  <line x1={cx+3} y1={cy-3} x2={cx-3} y2={cy+3} stroke="var(--red)" strokeWidth="1.4" />
                </g>;
              }
              return <circle key={i} cx={cx} cy={cy} r="2.6" className="chart-pt" />;
            })}

            {/* Hover */}
            {hover && (() => {
              const cx = x(hover.gen_no), cy = y(hover.graded_score || 0);
              return <g>
                <line x1={cx} x2={cx} y1={padT} y2={padT + innerH}
                      stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
                <circle cx={cx} cy={cy} r="6" fill="none" stroke="var(--ink-0)" strokeWidth="1" />
              </g>;
            })()}
          </svg>

          {hover && (
            <div style={{
              position: "absolute",
              top: 16,
              right: 16,
              background: "var(--bg-0)",
              border: "1px solid var(--line-2)",
              borderRadius: 6,
              padding: "8px 10px",
              fontFamily: "var(--mono)",
              fontSize: 11,
              minWidth: 200,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 }}>
                gen_{String(hover.gen_no).padStart(2, "0")}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>점수</span>
                <span style={{ color: hover.graded_score >= target ? "var(--teal)" : "var(--ink-0)" }}>
                  {fmtScore(hover.graded_score)}
                </span>
                <span style={{ color: "var(--ink-2)" }}>게이트</span>
                <span style={{ color: hover.gate_passed ? "var(--teal)" : "var(--ink-2)" }}>
                  {hover.gate_passed ? "✓ 통과" : "✗ 탈락"}
                </span>
                <span style={{ color: "var(--ink-2)" }}>거래</span>
                <span>{hover.trade_count}</span>
                <span style={{ color: "var(--ink-2)" }}>일평균거래</span>
                <span>{(typeof hover.daily_avg_trades === "number" ? hover.daily_avg_trades : 0).toFixed(2)}</span>
                <span style={{ color: "var(--ink-2)" }}>MDD</span>
                <span style={{ color: "var(--red)" }}>{fmtPct(hover.mdd)}</span>
                <span style={{ color: "var(--ink-2)" }}>손익</span>
                <span className={hover.profit > 0 ? "num-pos" : hover.profit < 0 ? "num-neg" : ""}>
                  {fmtMoney(hover.profit)}
                </span>
              </div>
            </div>
          )}

          {gens.length === 0 && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
            }}>
              세대 데이터가 누적되면 추이가 표시됩니다
            </div>
          )}
        </div>
      </div>
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

/* P10 — 세대별 수익률(%) + 수익금(원) 추이 차트(듀얼축).
   적합도(graded) 차트와 별개로, 손익 자체의 진화를 한눈에 본다. 0선(손익분기)을
   강조하고, 수익률 라인(좌축, %)과 수익금 라인(우축, 원)을 함께 그린다. 두 지표의
   스케일이 다르므로 각자 자기 min/max로 정규화해 같은 패널에 겹쳐 그린다. */
function ProfitChart({ state, targetPct = 0 }) {
  const gens = state.generations || [];

  const W = 880, H = 300;
  const padL = 52, padR = 56, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const xMax = Math.max(state.max_generations, 8);
  const x = (g) => padL + (g - 0.5) / xMax * innerW;

  // 수익률(%) 스케일: 0을 항상 포함하고, ±여유를 둔다.
  const pctVals = gens.map(g => (typeof g.total_profit_pct === "number" ? g.total_profit_pct : 0));
  const pctMax = Math.max(targetPct + 1, 1, ...pctVals);
  const pctMin = Math.min(0, ...pctVals);
  const pctRange = (pctMax - pctMin) || 1;
  const yPct = (v) => padT + innerH - ((v - pctMin) / pctRange) * innerH;

  // 수익금(원) 스케일: 자체 min/max(0 포함)로 정규화(우축).
  const moneyVals = gens.map(g => (typeof g.profit === "number" ? g.profit : 0));
  const moneyMax = Math.max(0, ...moneyVals);
  const moneyMin = Math.min(0, ...moneyVals);
  const moneyRange = (moneyMax - moneyMin) || 1;
  const yMoney = (v) => padT + innerH - ((v - moneyMin) / moneyRange) * innerH;

  // X 눈금(적합도 차트와 동일 규칙).
  const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
  const xTicks = [];
  for (let g = 1; g <= xMax; g++) {
    if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);
  }

  const pctPath = useMemo_c(() => {
    if (!gens.length) return "";
    return gens.map((g, i) =>
      `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yPct(g.total_profit_pct || 0).toFixed(2)}`
    ).join(" ");
  }, [gens, xMax, pctMin, pctRange]);

  const moneyPath = useMemo_c(() => {
    if (!gens.length) return "";
    return gens.map((g, i) =>
      `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yMoney(g.profit || 0).toFixed(2)}`
    ).join(" ");
  }, [gens, xMax, moneyMin, moneyRange]);

  // 통계 요약.
  const latest = gens[gens.length - 1];
  const peakPct = gens.reduce((a, b) =>
    ((b.total_profit_pct || 0) > (a?.total_profit_pct ?? -Infinity) ? b : a), null);

  const zeroY = yPct(0);  // 손익분기(0%) 기준선(좌축 기준).

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          수익 추이 — Profit Trajectory
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--amber)" label="수익률 %" />
          <LegendDot color="var(--blue)" label="수익금 ₩" dashed />
        </div>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="최신 수익률" value={latest ? fmtPct(latest.total_profit_pct) : "—"}
                color={latest && latest.total_profit_pct > 0 ? "var(--teal)"
                       : latest && latest.total_profit_pct < 0 ? "var(--red)" : undefined} />
          <Mini label="최고 수익률" value={peakPct ? fmtPct(peakPct.total_profit_pct) : "—"}
                sub={peakPct ? `gen_${peakPct.gen_no}` : ""} />
          <Mini label="최신 수익금" value={latest ? fmtMoney(latest.profit) : "—"}
                color={latest && latest.profit > 0 ? "var(--teal)"
                       : latest && latest.profit < 0 ? "var(--red)" : undefined} />
        </div>

        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            {/* 0% 손익분기 기준선(강조) */}
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                  stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end"
                  fill="var(--ink-2)">0%</text>
            {/* 좌축 라벨(수익률 max/min) */}
            <text className="chart-axis-text" x={padL - 8} y={yPct(pctMax) + 3} textAnchor="end"
                  fill="var(--amber)">{pctMax.toFixed(1)}%</text>
            <text className="chart-axis-text" x={padL - 8} y={yPct(pctMin) + 3} textAnchor="end"
                  fill="var(--amber)">{pctMin.toFixed(1)}%</text>
            {/* 우축 라벨(수익금 max/min) */}
            <text className="chart-axis-text" x={W - padR + 6} y={yMoney(moneyMax) + 3} textAnchor="start"
                  fill="var(--blue)">{fmtMoney(moneyMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yMoney(moneyMin) + 3} textAnchor="start"
                  fill="var(--blue)">{fmtMoney(moneyMin)}</text>
            {/* 목표 수익률선(targetPct > 0일 때만) */}
            {targetPct > 0 && (
              <>
                <line x1={padL} x2={W - padR} y1={yPct(targetPct)} y2={yPct(targetPct)}
                      stroke="rgba(76,214,179,0.4)" strokeWidth="1" strokeDasharray="6 4" />
                <text className="chart-axis-text" x={W - padR - 4} y={yPct(targetPct) - 4}
                      textAnchor="end" fill="var(--teal)">target {targetPct.toFixed(1)}%</text>
              </>
            )}

            {/* X 라벨 */}
            {xTicks.map((g, i) => (
              <text key={`px${i}`} className="chart-axis-text"
                    x={x(g)} y={H - 10} textAnchor="middle">gen_{g}</text>
            ))}

            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                  stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                  stroke="var(--line-2)" strokeWidth="1" />

            {/* Data: 수익률(좌축, 실선) + 수익금(우축, 점선) */}
            {gens.length > 1 && (
              <>
                <path d={moneyPath} fill="none" stroke="var(--blue)" strokeWidth="1.5"
                      strokeDasharray="5 4" opacity="0.85" />
                <path d={pctPath} fill="none" stroke="var(--amber)" strokeWidth="2" />
              </>
            )}
            {/* 수익률 포인트(부호별 색) */}
            {gens.map((g, i) => {
              const cx = x(g.gen_no), cy = yPct(g.total_profit_pct || 0);
              const col = (g.total_profit_pct || 0) > 0 ? "var(--teal)"
                        : (g.total_profit_pct || 0) < 0 ? "var(--red)" : "var(--ink-2)";
              return <circle key={`pp${i}`} cx={cx} cy={cy} r="2.6" fill={col} />;
            })}
          </svg>

          {gens.length === 0 && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
            }}>
              세대 데이터가 누적되면 수익 추이가 표시됩니다
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* R-Viz1 — 전 전략 누적 수익곡선 오버랩 차트.
   /equity_curves(GET)에서 세대별 수익금합계 시계열을 받아 멀티라인으로 겹쳐 그린다.
   - 흐린 회색 얇은 선: 전체 곡선(비우승).
   - 색 굵은 선: gate_passed=True(우승) 곡선.
   - 손익분기(y=0) 기준선.
   - 30초 자동 새로고침 + 수동 새로고침 버튼.
   - hover 시 run/gen·final_pct 툴팁. */
const { useState: useState_eq, useEffect: useEffect_eq, useCallback: useCallback_eq, useRef: useRef_eq } = React;

// 우승 곡선 색 팔레트 (최대 12개).
const _EQ_WINNER_COLORS = [
  "#4cd6b3", "#a594ff", "#f0b35a", "#6aa6ff",
  "#ff7eb6", "#73d673", "#ff9966", "#c084fc",
  "#38bdf8", "#fb923c", "#a3e635", "#f472b6",
];

function EquityOverlayChart({ baseUrl, wsStatus }) {
  const [data, setData] = useState_eq(null);   // {curves, count}
  const [loading, setLoading] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [hover, setHover] = useState_eq(null); // {x_frac, curves_at_x:[{run_id,gen_no,gate_passed,final_pct,y}]}
  const svgRef = useRef_eq(null);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_eq(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    fetch(baseUrl + "/equity_curves", { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  // 최초 + 30초 자동 새로고침.
  useEffect_eq(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const curves = (data && data.curves) || [];
  const winners = curves.filter(c => c.gate_passed);
  const nonWinners = curves.filter(c => !c.gate_passed);

  const W = 880, H = 320;
  const padL = 52, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // Y 범위: 전체 equity 값의 min/max (0 포함).
  const allEquity = curves.flatMap(c => c.equity || []);
  const yRawMax = allEquity.length ? Math.max(0, ...allEquity) : 1;
  const yRawMin = allEquity.length ? Math.min(0, ...allEquity) : -1;
  const yRange = (yRawMax - yRawMin) || 1;

  // SVG 좌표 변환. x는 0~1 정규화(각 곡선 길이 제각각 → 거래진행%).
  const xSvg = (frac) => padL + frac * innerW;
  const ySvg = (v) => padT + innerH - ((v - yRawMin) / yRange) * innerH;
  const zeroY = ySvg(0);

  // Y 눈금 (최대 6개).
  const yTicks = (() => {
    const ticks = [];
    const rawStep = yRange / 5;
    const mag = Math.pow(10, Math.floor(Math.log10(Math.abs(rawStep) || 1)));
    const step = Math.ceil(rawStep / mag) * mag || 1;
    const start = Math.ceil(yRawMin / step) * step;
    for (let v = start; v <= yRawMax + 1e-9; v += step) {
      ticks.push(Math.round(v));
      if (ticks.length >= 8) break;
    }
    return ticks;
  })();

  // 각 곡선을 SVG path d 문자열로 변환.
  const toPath = (equity) => {
    if (!equity || equity.length < 2) return "";
    return equity.map((v, i) => {
      const fx = i / (equity.length - 1);
      return `${i === 0 ? "M" : "L"} ${xSvg(fx).toFixed(1)} ${ySvg(v).toFixed(1)}`;
    }).join(" ");
  };

  // Hover: SVG mousemove → x 위치 → 가장 가까운 포인트 요약.
  const onMove = (e) => {
    if (!curves.length || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
    // 각 곡선에서 해당 frac 위치의 값 보간.
    const tips = curves.slice(0, 40).map(c => {  // 성능: 최대 40곡선만 툴팁
      const eq = c.equity || [];
      if (eq.length < 2) return null;
      const idx = frac * (eq.length - 1);
      const lo = Math.floor(idx), hi = Math.ceil(idx);
      const t = idx - lo;
      const y = eq[lo] * (1 - t) + (eq[hi] || eq[lo]) * t;
      return { run_id: c.run_id, gen_no: c.gen_no, gate_passed: c.gate_passed, final_pct: c.final_pct, y };
    }).filter(Boolean);
    setHover({ frac, tips });
  };
  const onLeave = () => setHover(null);

  // 통계.
  const winnerCount = winners.length;
  const totalCount = curves.length;
  const maxFinalPct = curves.length ? Math.max(...curves.map(c => c.final_pct)) : null;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          전 전략 누적 수익곡선
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <LegendDot color="rgba(255,255,255,0.18)" label="비우승" />
          <LegendDot color="var(--teal)" label="우승(gate_passed)" />
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}
                  data-tip="equity curves 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="전체 곡선" value={totalCount > 0 ? String(totalCount) : "—"} />
          <Mini label="우승 곡선" value={winnerCount > 0 ? String(winnerCount) : "—"}
                color={winnerCount > 0 ? "var(--teal)" : undefined} />
          <Mini label="최고 수익률"
                value={maxFinalPct != null ? (maxFinalPct >= 0 ? "+" : "") + maxFinalPct.toFixed(1) + "%" : "—"}
                color={maxFinalPct != null && maxFinalPct > 0 ? "var(--teal)" : maxFinalPct != null && maxFinalPct < 0 ? "var(--red)" : undefined} />
        </div>

        <div className="chart-wrap">
          {isDemo ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              데모 모드 — 백엔드 연결 시 equity curves가 표시됩니다.
            </div>
          ) : err ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--red)", fontSize: 12, fontFamily: "var(--mono)" }}>
              조회 실패: {err}
            </div>
          ) : curves.length === 0 ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              세대 데이터가 누적되면 수익곡선이 표시됩니다
            </div>
          ) : (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`}
                 preserveAspectRatio="none"
                 onMouseMove={onMove} onMouseLeave={onLeave}>
              {/* Y 그리드 + 눈금 */}
              {yTicks.map((t, i) => (
                <g key={`ey${i}`}>
                  <line className="chart-grid-line"
                        x1={padL} x2={W - padR} y1={ySvg(t)} y2={ySvg(t)} />
                  <text className="chart-axis-text"
                        x={padL - 8} y={ySvg(t) + 3} textAnchor="end">
                    {t >= 10000 ? (t / 10000).toFixed(0) + "만" : t.toLocaleString()}
                  </text>
                </g>
              ))}
              {/* 손익분기(0) 기준선 */}
              <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                    stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
              <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end"
                    fill="var(--ink-2)">0</text>
              {/* X 축 프레임 */}
              <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* X 축 라벨 */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((f, i) => (
                <text key={`ex${i}`} className="chart-axis-text"
                      x={xSvg(f)} y={H - 10} textAnchor="middle">
                  {Math.round(f * 100)}%
                </text>
              ))}

              {/* 비우승 곡선: 얇은 회색 */}
              {nonWinners.map((c, i) => {
                const d = toPath(c.equity);
                if (!d) return null;
                return <path key={`nw${i}`} d={d} fill="none"
                             stroke="rgba(255,255,255,0.10)" strokeWidth="0.8" />;
              })}

              {/* 우승 곡선: 강조(색+굵기). 색 팔레트 순환. */}
              {winners.map((c, i) => {
                const d = toPath(c.equity);
                if (!d) return null;
                const col = _EQ_WINNER_COLORS[i % _EQ_WINNER_COLORS.length];
                return <path key={`w${i}`} d={d} fill="none"
                             stroke={col} strokeWidth="2.0" opacity="0.9" />;
              })}

              {/* Hover 수직선 */}
              {hover && (() => {
                const hx = xSvg(hover.frac);
                return <line x1={hx} x2={hx} y1={padT} y2={padT + innerH}
                             stroke="rgba(255,255,255,0.15)" strokeWidth="1" />;
              })()}
            </svg>
          )}

          {/* Hover 툴팁 */}
          {hover && hover.tips.length > 0 && (() => {
            const winTips = hover.tips.filter(t => t.gate_passed);
            const topTips = [
              ...winTips,
              ...hover.tips.filter(t => !t.gate_passed).slice(0, Math.max(0, 5 - winTips.length)),
            ];
            return (
              <div style={{
                position: "absolute", top: 16, right: 16,
                background: "var(--bg-0)", border: "1px solid var(--line-2)",
                borderRadius: 6, padding: "8px 10px",
                fontFamily: "var(--mono)", fontSize: 11,
                minWidth: 200, maxWidth: 260,
                boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
                pointerEvents: "none",
              }}>
                <div style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em",
                              textTransform: "uppercase", marginBottom: 4 }}>
                  진행 {Math.round(hover.frac * 100)}%
                </div>
                {topTips.map((t, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between",
                                        gap: 8, padding: "2px 0",
                                        color: t.gate_passed ? "var(--teal)" : "var(--ink-2)" }}>
                    <span>{t.run_id.slice(-6)}/g{t.gen_no}</span>
                    <span>{t.y >= 0 ? "+" : ""}{Math.round(t.y).toLocaleString()}</span>
                  </div>
                ))}
                {hover.tips.length > topTips.length && (
                  <div style={{ color: "var(--ink-3)", fontSize: 10, marginTop: 3 }}>
                    외 {hover.tips.length - topTips.length}개…
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

/* P1a — 품질지표 추이 차트(QualityTrendChart).
   위험조정 품질지표(calmar·우상향R²·MDD·일평균거래·동시보유·손익비)의 세대간 추이를
   한 패널에 겹쳐 본다. 지표마다 스케일이 크게 다르므로(calmar 0~100 vs R² 0~1 vs
   MDD 0~160% vs 동시보유 0~12) 각 지표를 자기 min/max로 정규화해 '추세 모양'을 비교하고,
   실제값은 hover 툴팁에 표시한다. 데이터는 이미 state.generations[]에 LIVE 존재(백엔드 무변).
   기본 표시 = calmar·우상향R²·MDD(핵심 졸업 기준). 범례 버튼 클릭으로 지표 토글.
   보고서(STOM_Good_Results) 목표: 일평균10~23·동시보유6~12·MDD<7%·손익비>1.25. */
const _QUALITY_METRICS = [
  { key: "calmar",           label: "Calmar",     color: "var(--teal)",   fmt: (v) => v.toFixed(2), hint: "CAGR/MDD 위험조정수익(높을수록 우수)" },
  { key: "uptrend_r2",       label: "우상향 R²",  color: "var(--violet)", fmt: (v) => v.toFixed(3), hint: "누적곡선 우상향 적합도 0~1(높을수록 우수)" },
  { key: "mdd",              label: "MDD %",      color: "var(--red)",    fmt: (v) => fmtPct(v),    hint: "최대낙폭(낮을수록 우수) — 보고서 1.9~6.75%" },
  { key: "daily_avg_trades", label: "일평균거래", color: "var(--amber)",  fmt: (v) => v.toFixed(2), hint: "거래수/거래일(보고서 10~23)" },
  { key: "max_hold_count",   label: "동시보유",   color: "var(--blue)",   fmt: (v) => v.toFixed(0), hint: "최대 동시보유 종목수(보고서 6~12)" },
  { key: "payoff_ratio",     label: "손익비",     color: "#73d673",       fmt: (v) => v.toFixed(2), hint: "평균이익/평균손실(보고서 1.15~1.47)" },
];

function QualityTrendChart({ state }) {
  const gens = state.generations || [];
  const [enabled, setEnabled] = useState_c(() => ({
    calmar: true, uptrend_r2: true, mdd: true,
    daily_avg_trades: false, max_hold_count: false, payoff_ratio: false,
  }));
  const toggle = (k) => setEnabled(s => ({ ...s, [k]: !s[k] }));

  const W = 880, H = 320;
  const padL = 44, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const xMax = Math.max(state.max_generations, 8);
  const x = (g) => padL + (g - 0.5) / xMax * innerW;

  // status==error(전 지표 0)는 스케일 왜곡 방지를 위해 제외.
  // useMemo로 안정 참조 유지 → 하위 ranges useMemo 캐시가 실제로 동작(FitnessChart와 동일 원리).
  const okGens = useMemo_c(() => gens.filter(g => g.status !== "error"), [gens]);

  // 각 지표의 자기 min/max(정규화용).
  const ranges = useMemo_c(() => {
    const r = {};
    for (const m of _QUALITY_METRICS) {
      const vals = okGens.map(g => (typeof g[m.key] === "number" ? g[m.key] : null)).filter(v => v != null);
      if (!vals.length) { r[m.key] = null; continue; }
      let lo = Math.min(...vals), hi = Math.max(...vals);
      if (hi === lo) hi = lo + 1;  // 평탄선 방지(단일/동일값).
      r[m.key] = { lo, hi };
    }
    return r;
  }, [okGens]);

  // 정규화 y: 지표값 → [0,1] → svg y. 값 없으면 null(선 끊김).
  const ny = (m, g) => {
    const rg = ranges[m.key];
    if (!rg || typeof g[m.key] !== "number" || g.status === "error") return null;
    const t = (g[m.key] - rg.lo) / (rg.hi - rg.lo);
    return padT + innerH - t * innerH;
  };

  const pathFor = (m) => {
    let d = "", started = false;
    for (const g of okGens) {
      const yy = ny(m, g);
      if (yy == null) continue;
      d += `${started ? "L" : "M"} ${x(g.gen_no).toFixed(2)} ${yy.toFixed(2)} `;
      started = true;
    }
    return d.trim();
  };

  const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
  const xTicks = [];
  for (let g = 1; g <= xMax; g++) if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);

  const [hover, setHover] = useState_c(null);
  const svgRef = useRef_c(null);
  const onMove = (e) => {
    if (!okGens.length || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    let best = null, bestDist = Infinity;
    for (const g of okGens) { const d = Math.abs(x(g.gen_no) - px); if (d < bestDist) { bestDist = d; best = g; } }
    setHover(best && bestDist < 40 ? best : null);
  };

  const activeMetrics = _QUALITY_METRICS.filter(m => enabled[m.key]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          품질지표 추이 — Quality Metrics
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          {_QUALITY_METRICS.map(m => (
            <button key={m.key} onClick={() => toggle(m.key)} data-tip={m.hint}
              style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                fontSize: 10.5, fontFamily: "var(--mono)", cursor: "pointer",
                padding: "3px 7px", borderRadius: 5,
                border: `1px solid ${enabled[m.key] ? m.color : "var(--line-2)"}`,
                background: enabled[m.key] ? "rgba(255,255,255,0.04)" : "transparent",
                color: enabled[m.key] ? "var(--ink-0)" : "var(--ink-3)",
              }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%",
                background: enabled[m.key] ? m.color : "var(--line-2)" }}></span>
              {m.label}
            </button>
          ))}
        </div>
      </div>
      <div className="panel-bd">
        <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 }}>
          각 지표는 자기 범위로 정규화한 '추세 모양' — 실제값은 hover 참조. 보고서 목표: 일평균10~23·동시보유6~12·MDD&lt;7%·손익비&gt;1.25
        </div>
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            {/* 정규화 기준 가로 그리드(0/50/100%) */}
            {[0, 0.5, 1].map((t, i) => {
              const yy = padT + innerH - t * innerH;
              return <line key={`qg${i}`} className="chart-grid-line" x1={padL} x2={W - padR} y1={yy} y2={yy} />;
            })}
            {/* X 라벨 */}
            {xTicks.map((g, i) => (
              <text key={`qx${i}`} className="chart-axis-text" x={x(g)} y={H - 10} textAnchor="middle">gen_{g}</text>
            ))}
            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 지표 라인 */}
            {activeMetrics.map(m => {
              const d = pathFor(m);
              if (!d) return null;
              return <g key={m.key}>
                <path d={d} fill="none" stroke={m.color} strokeWidth="1.8" opacity="0.9" />
                {okGens.map((g, i) => {
                  const yy = ny(m, g);
                  if (yy == null) return null;
                  return <circle key={i} cx={x(g.gen_no)} cy={yy} r="2.4" fill={m.color} />;
                })}
              </g>;
            })}
            {/* Hover 수직선 */}
            {hover && (() => {
              const hx = x(hover.gen_no);
              return <line x1={hx} x2={hx} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />;
            })()}
          </svg>

          {hover && activeMetrics.length > 0 && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px",
              fontFamily: "var(--mono)", fontSize: 11, minWidth: 170,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em",
                            textTransform: "uppercase", marginBottom: 4 }}>
                gen_{String(hover.gen_no).padStart(2, "0")}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                {activeMetrics.map(m => (
                  <React.Fragment key={m.key}>
                    <span style={{ color: m.color }}>{m.label}</span>
                    <span style={{ textAlign: "right" }}>
                      {typeof hover[m.key] === "number" ? m.fmt(hover[m.key]) : "—"}
                    </span>
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {okGens.length === 0 && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", alignItems: "center",
              justifyContent: "center", color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
            }}>
              세대 데이터가 누적되면 품질지표 추이가 표시됩니다
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { FitnessChart, ProfitChart, EquityOverlayChart, QualityTrendChart });
