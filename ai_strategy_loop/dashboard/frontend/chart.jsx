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

Object.assign(window, { FitnessChart, ProfitChart });
