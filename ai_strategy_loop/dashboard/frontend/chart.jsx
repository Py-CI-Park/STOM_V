/* SVG chart for graded_score per generation. */
const { useMemo: useMemo_c, useState: useState_c, useRef: useRef_c } = React;

function MetricHelpStrip({ items }) {
  return (
    <div className="metric-help-strip">
      {(items || []).map((item, i) => <span key={i}>{item}</span>)}
    </div>
  );
}

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
          <span data-tip="적합도(graded_score) = 수익·MDD·거래수 게이트를 통과한 정도를 0~100으로 등급화한 점수. 세대가 진행되며 점수가 우상향하면 진화가 작동 중이라는 뜻. 점선 = 지금까지의 최고점, 링 = 게이트 통과 세대."
                style={{ marginLeft: 6, fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--line-2)",
                         borderRadius: "50%", width: 15, height: 15, display: "inline-flex",
                         alignItems: "center", justifyContent: "center", cursor: "help" }}>?</span>
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
        <MetricHelpStrip items={[
          "graded_score = weighted fitness",
          "hard gate = target score plus MDD/trade rules",
          "Calmar = return divided by MDD",
          "uptrend_r2 = cumulative equity trend fit",
        ]} />

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
        <MetricHelpStrip items={[
          "payoff_ratio = avg win / abs(avg loss)",
          "total_profit_pct = operating-capital return",
          "profit line uses right-axis money scale",
        ]} />

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

function EquityOverlayChart({ baseUrl, wsStatus, runId }) {
  const [data, setData] = useState_eq(null);   // {curves, count}
  const [loading, setLoading] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [hover, setHover] = useState_eq(null); // {x_frac, curves_at_x:[{run_id,gen_no,gate_passed,final_pct,y}]}
  const [periodInfo, setPeriodInfo] = useState_eq(null); // {period:"YYYY-MM-DD ~ YYYY-MM-DD", timeframe}
  const svgRef = useRef_eq(null);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_eq(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    // 현재 run만 조회 — 전체 이력의 과발화 폭망 곡선(±수십억)이 y스케일을 장악해
    //   정상 곡선이 0선에 압착되는 문제 회피. runId 없으면 전체(하위호환).
    const url = baseUrl + "/equity_curves" + (runId ? "?run_id=" + encodeURIComponent(runId) : "");
    fetch(url, { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId]);

  // 최초 + 30초 자동 새로고침.
  useEffect_eq(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  // 백테 기간(연도 포함) — /generation_durations 가 run config 의 bt_full_start/end 를
  //   "YYYY-MM-DD ~ YYYY-MM-DD" 로 이미 제공한다. run 당 1회만 조회(무예외).
  useEffect_eq(() => {
    if (isDemo || !baseUrl || !runId) { setPeriodInfo(null); return; }
    let alive = true;
    fetch(baseUrl + "/generation_durations?run_id=" + encodeURIComponent(runId),
          { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (!alive) return;
        const first = ((j && j.durations) || []).find(d => d.period) || null;
        setPeriodInfo(first ? { period: first.period, timeframe: first.timeframe } : null);
      })
      .catch(() => { if (alive) setPeriodInfo(null); });
    return () => { alive = false; };
  }, [baseUrl, isDemo, runId]);

  const curves = (data && data.curves) || [];
  const winners = curves.filter(c => c.gate_passed);
  const nonWinners = curves.filter(c => !c.gate_passed);

  const W = 880, H = 320;
  const padL = 52, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // Y 범위: 전체 equity 값의 min/max (0 포함). 단 과발화 폭망 곡선(±수십억) outlier가
  //   스케일을 장악해 정상 곡선을 0선에 압착하지 않도록 5~95 퍼센타일로 클립한다
  //   (run 필터가 적용되면 보통 outlier가 없어 min/max와 같지만, 전체 모드 견고성용).
  const allEquity = curves.flatMap(c => c.equity || []);
  const _sortedEq = allEquity.slice().sort((a, b) => a - b);
  const _pctile = (p) => _sortedEq.length
    ? _sortedEq[Math.min(_sortedEq.length - 1, Math.max(0, Math.round(p * (_sortedEq.length - 1))))]
    : 0;
  const yRawMax = _sortedEq.length ? Math.max(0, _pctile(0.95)) : 1;
  const yRawMin = _sortedEq.length ? Math.min(0, _pctile(0.05)) : -1;
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
          <span data-tip="이 run 의 모든 세대(전략)의 백테스트 누적 수익금을 한 차트에 겹쳐, 우승(게이트 통과) 전략이 비우승 대비 얼마나 우월한지 한눈에 비교합니다. X축 = 거래 진행률(전략마다 거래 수가 달라 0~100%로 정규화), Y축 = 누적 수익금(원)."
                style={{ marginLeft: 6, fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--line-2)",
                         borderRadius: "50%", width: 15, height: 15, display: "inline-flex",
                         alignItems: "center", justifyContent: "center", cursor: "help" }}>?</span>
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
          <Mini label="백테 기간"
                value={periodInfo && periodInfo.period ? periodInfo.period : "기간 정보 없음"}
                sub={periodInfo && periodInfo.timeframe ? String(periodInfo.timeframe) : ""} />
        </div>
        <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 }}>
          X축 = 거래 진행률 0~100%(전략마다 거래 수가 달라 정규화) · Y축 = 누적 수익금(원) · 회색 = 비우승 · 색 = 우승(gate 통과)
        </div>
        <MetricHelpStrip items={[
          "edge_ratio = segment edge density",
          "winner curves use a 12-color palette",
          "non-winner curves stay subdued for comparison",
        ]} />

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
                    {Math.abs(t) >= 1e8 ? (t / 1e8).toFixed(1) + "억"
                      : Math.abs(t) >= 10000 ? (t / 10000).toFixed(0) + "만"
                      : t.toLocaleString()}
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
          <span data-tip="품질 = 수익 크기와 별개로 '전략이 얼마나 건강한가'를 보는 위험조정 지표 묶음(calmar·우상향 R²·MDD·일평균 거래·동시보유·손익비). 각 칩에 마우스를 올리면 지표별 설명이 나오고, 클릭하면 표시를 켜고 끕니다."
                style={{ marginLeft: 6, fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--line-2)",
                         borderRadius: "50%", width: 15, height: 15, display: "inline-flex",
                         alignItems: "center", justifyContent: "center", cursor: "help" }}>?</span>
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

/* O1 — 백테 상세 차트(BacktestDetailChart).
   일반 STOM 백테가 만드는 2-그래프(상단 일별손익 막대 + 하단 누적수익곡선)를 헤드리스
   루프 결과로 한 패널에 재현한다. 헤드리스 루프는 엔진 PNG 생성이 꺼져 있으나(cli/runner.py)
   per-trade 거래 CSV는 항상 생성되므로, /backtest_detail(GET)이 그 CSV를
   parse_backtest_series로 일별손익+누적곡선+낙폭으로 변환해 보낸다(추가 백테 0회).
   - 현재 run(state.run_id)의 세대 중 선택된 gen(기본=best 또는 최신)을 드롭다운으로 고른다.
   - 한 영역에 STOM fig2 재현: 일별손익 막대(이익=red 위, 손실=blue 아래, 0 기준선) 위에
     누적수익곡선(cum_profit, orange 굵은선, 별도 우측 스케일).
   - hover 시 그 거래일의 일손익·누적·낙폭(반납액) 툴팁.
   - demo면 미fetch(EquityOverlayChart 패턴). 빈 시계열이면 빈 상태 표시. */
const {
  useState: useState_bd, useEffect: useEffect_bd,
  useCallback: useCallback_bd, useRef: useRef_bd, useMemo: useMemo_bd,
} = React;

function BacktestDetailChart({ baseUrl, wsStatus, state, externalSelGen }) {
  const gens = (state && state.generations) || [];
  const runId = (state && state.run_id) || "";
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // 기본 선택 gen: gate_passed(우승) 중 점수 최고 → 없으면 최신 세대.
  const defaultGen = useMemo_bd(() => {
    if (!gens.length) return null;
    const winners = gens.filter(g => g.gate_passed);
    if (winners.length) {
      return winners.reduce((a, b) =>
        ((b.graded_score || 0) > (a.graded_score || 0) ? b : a)).gen_no;
    }
    return gens[gens.length - 1].gen_no;
  }, [gens]);

  const [selGen, setSelGen] = useState_bd(null);
  // run/세대 목록이 바뀌면 선택을 기본값으로 재동기화(수동 선택 후 새 run 시작 대비).
  useEffect_bd(() => { setSelGen(defaultGen); }, [defaultGen, runId]);
  // #65 P1 — 외부(세대표 '백테상세' 클릭)에서 선택 세대를 내려주면 내부 선택을 동기화한다.
  //   externalSelGen이 null이면(미선택) 내부 선택/기본값을 그대로 쓴다(하위호환).
  useEffect_bd(() => {
    if (externalSelGen != null) setSelGen(externalSelGen);
  }, [externalSelGen]);
  const genNo = selGen != null ? selGen : defaultGen;

  const [data, setData] = useState_bd(null);   // {run_id,gen_no,gate_passed,daily,cumulative,drawdown,summary}
  const [loading, setLoading] = useState_bd(false);
  const [err, setErr] = useState_bd(null);
  const [hover, setHover] = useState_bd(null);  // 거래일 인덱스
  const svgRef = useRef_bd(null);

  const refresh = useCallback_bd(() => {
    if (isDemo || !baseUrl || !runId || genNo == null) return;
    setLoading(true);
    const url = baseUrl + "/backtest_detail?run_id=" + encodeURIComponent(runId)
      + "&gen_no=" + encodeURIComponent(genNo);
    fetch(url, { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, genNo]);

  // 최초 + gen 변경 + 30초 자동 새로고침.
  useEffect_bd(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const daily = (data && data.daily) || [];
  const cumulative = (data && data.cumulative) || [];
  const drawdown = (data && data.drawdown) || [];
  const holdings = (data && data.holdings) || [];
  const summary = (data && data.summary) || {};
  const hasSeries = daily.length > 0;
  const hasHoldings = holdings.length > 0;
  const peakHoldings = summary.peak_holdings != null ? summary.peak_holdings : 0;
  const selectedGeneration = gens.find(g => g.gen_no === genNo) || null;
  const dbMaxHold = selectedGeneration && typeof selectedGeneration.max_hold_count === "number"
    ? selectedGeneration.max_hold_count : null;
  const sparseHoldSuspicious = (summary.trade_count || 0) >= 50
    && dbMaxHold != null
    && dbMaxHold <= 1
    && peakHoldings > dbMaxHold;
  // 무거래 세대 판정: 시계열 없음 또는 trade_count가 명시적으로 0.
  const noTrades = !hasSeries || (summary.trade_count != null && summary.trade_count === 0);

  const W = 880, H = 320;
  const padL = 56, padR = 60, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // 일별손익(막대) 스케일: 0 포함, ±여유. 좌축.
  const pnlVals = daily.map(d => d.daily_pnl || 0);
  const pnlMax = Math.max(0, ...pnlVals);
  const pnlMin = Math.min(0, ...pnlVals);
  const pnlRange = (pnlMax - pnlMin) || 1;
  const yPnl = (v) => padT + innerH - ((v - pnlMin) / pnlRange) * innerH;
  const zeroY = yPnl(0);  // 0 손익분기 기준선(막대 기준).

  // 누적수익(라인) 스케일: 자체 min/max(0 포함). 우축.
  const cumVals = cumulative.map(c => c.cum_profit || 0);
  const cumMax = Math.max(0, ...cumVals);
  const cumMin = Math.min(0, ...cumVals);
  const cumRange = (cumMax - cumMin) || 1;
  const yCum = (v) => padT + innerH - ((v - cumMin) / cumRange) * innerH;

  // 막대 x 위치(거래일 인덱스 기반 등간격). 막대폭은 간격의 70%.
  const n = daily.length;
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.7);
  const xBar = (i) => padL + (i + 0.5) * slot;  // 막대 중심.

  const fmtMoneyShort = (v) => {
    const a = Math.abs(v);
    if (a >= 1e8) return (v / 1e8).toFixed(1) + "억";
    if (a >= 1e4) return Math.round(v / 1e4) + "만";
    return Math.round(v).toLocaleString();
  };

  // 누적 곡선 path(거래일 인덱스 → 막대 중심 x).
  const cumPath = useMemo_bd(() => {
    if (cumulative.length < 2) return "";
    return cumulative.map((c, i) =>
      `${i === 0 ? "M" : "L"} ${xBar(i).toFixed(2)} ${yCum(c.cum_profit || 0).toFixed(2)}`
    ).join(" ");
  }, [cumulative, n, cumMin, cumRange]);

  // ── 상단 보유종목수 sub-panel(STOM fig2 상단 대응) ──────────────────────
  //   동시보유 종목수(holdings: [{t_index,count}])를 이벤트(시각) 진행 축으로 계단
  //   라인 그린다. 보유금액(원)은 엔진 전용(CSV 미저장)이라 동시보유 종목수로 대체.
  const HpH = 90;                              // 상단 패널 높이.
  const hpPadT = 14, hpPadB = 18;              // 상하 패딩.
  const hpInnerH = HpH - hpPadT - hpPadB;
  // x축은 하단과 동일한 [padL, W-padR] 폭을 쓰되 holdings 이벤트 인덱스로 매핑.
  const hN = holdings.length;
  const xHold = (i) => (hN <= 1
    ? padL + innerW / 2
    : padL + (i / (hN - 1)) * innerW);
  // y축: 0..max(count) (정수). 최소 1칸 확보.
  const holdMax = Math.max(1, peakHoldings, ...holdings.map(h => h.count || 0));
  const yHold = (v) => hpPadT + hpInnerH - (v / holdMax) * hpInnerH;
  // 계단(step) path: 각 점에서 수평 유지 후 다음 count로 수직 이동(보유수=정수 계단).
  const holdPath = useMemo_bd(() => {
    if (hN < 1) return "";
    let dStr = `M ${xHold(0).toFixed(2)} ${yHold(holdings[0].count || 0).toFixed(2)}`;
    for (let i = 1; i < hN; i++) {
      const x = xHold(i).toFixed(2);
      const yPrev = yHold(holdings[i - 1].count || 0).toFixed(2);
      const y = yHold(holdings[i].count || 0).toFixed(2);
      dStr += ` L ${x} ${yPrev} L ${x} ${y}`;   // 수평 후 수직 = 계단.
    }
    return dStr;
  }, [holdings, hN, holdMax]);
  // y 눈금(0·max만 — 정수). max가 작으면 중간값도.
  const holdYTicks = (() => {
    if (holdMax <= 1) return [0, 1];
    if (holdMax <= 4) return Array.from({ length: holdMax + 1 }, (_, k) => k);
    return [0, Math.round(holdMax / 2), holdMax];
  })();

  // X 라벨(거래일): 최대 ~8개만 표시(YYYYMMDD → MM/DD).
  const xLabelIdxs = (() => {
    if (n === 0) return [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idxs = [];
    for (let i = 0; i < n; i += step) idxs.push(i);
    if (idxs[idxs.length - 1] !== n - 1) idxs.push(n - 1);
    return idxs;
  })();
  const fmtDate = (d) => {
    const s = String(d);
    return s.length === 8 ? s.slice(4, 6) + "/" + s.slice(6, 8) : s;
  };

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };
  const onLeave = () => setHover(null);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          백테 상세 — 동시보유 종목수 · 일별손익 · 누적수익곡선
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="동시보유 종목수" />
          <LegendDot color="var(--red)" label="이익(일)" />
          <LegendDot color="var(--blue)" label="손실(일)" />
          <LegendDot color="var(--amber)" label="누적수익 ₩" />
          {gens.length > 0 && (
            <select
              value={genNo != null ? genNo : ""}
              onChange={e => setSelGen(Number(e.target.value))}
              className="mono"
              style={{
                fontSize: 11, background: "var(--bg-1)", color: "var(--ink-0)",
                border: "1px solid var(--line-2)", borderRadius: 5, padding: "3px 6px",
              }}
              data-tip="세대 선택">
              {gens.map(g => (
                <option key={g.gen_no} value={g.gen_no}>
                  gen_{g.gen_no}{g.gate_passed ? " ✓" : ""}
                </option>
              ))}
            </select>
          )}
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading || !runId}
                  data-tip="백테 상세 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="거래수" value={summary.trade_count != null ? String(summary.trade_count) : "—"} />
          <Mini label="거래일" value={summary.n_days != null ? String(summary.n_days) : "—"} />
          <Mini label="최대 동시보유"
                value={noTrades ? "거래없음" : (summary.peak_holdings != null ? String(summary.peak_holdings) : "—")}
                color={!noTrades && peakHoldings > 0 ? "var(--teal)" : "var(--ink-3)"} sub="종목수" />
          <Mini label="DB max_hold_count"
                value={dbMaxHold != null ? String(dbMaxHold) : "—"}
                color={sparseHoldSuspicious ? "var(--red)" : undefined} sub="저장값" />
          <Mini label="최종 누적수익" value={summary.final_profit != null ? fmtMoney(summary.final_profit) : "—"}
                color={summary.final_profit > 0 ? "var(--teal)"
                       : summary.final_profit < 0 ? "var(--red)" : undefined} />
          <Mini label="최대 반납액" value={summary.max_drawdown != null ? fmtMoney(summary.max_drawdown) : "—"}
                color={summary.max_drawdown > 0 ? "var(--red)" : undefined} sub="고점 대비(원)" />
        </div>
        <MetricHelpStrip items={[
          `run_id=${runId || "-"}`,
          `gen_no=${genNo != null ? genNo : "-"}`,
          "peak_holdings=0 can mean no overlap buy/sell timing data",
          `DB max_hold_count=${dbMaxHold != null ? dbMaxHold : "-"}`,
          "period/timeframe are inherited from the selected run",
        ]} />
        {sparseHoldSuspicious && (
          <div className="research-empty danger" title="Sparse hold warning">
            Sparse hold warning: DB max_hold_count {dbMaxHold} differs from CSV peak_holdings {peakHoldings}.
            human corridor 6-12; treat this as an audit signal, not promotion proof.
          </div>
        )}

        {/* ── 상단: 동시보유 종목수 시계열(STOM fig2 상단 대응) ──
            보유금액(원)은 엔진 전용(CSV 미저장)이라 미표시, 동시보유 종목수로 대체.
            holdings(매수/매도시간 event-sweep)가 비면 이 패널은 생략한다(빈 상태). */}
        {!isDemo && !err && hasHoldings && (
          <div style={{ marginBottom: 6 }}>
            <svg viewBox={`0 0 ${W} ${HpH}`} preserveAspectRatio="none"
                 style={{ width: "100%", height: HpH, display: "block" }}>
              {/* 프레임(좌·하) */}
              <line x1={padL} x2={W - padR} y1={hpPadT + hpInnerH} y2={hpPadT + hpInnerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={hpPadT} y2={hpPadT + hpInnerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* y 눈금(정수 보유수) + 가로 점선 */}
              {holdYTicks.map((tk) => (
                <g key={`hyt${tk}`}>
                  <line x1={padL} x2={W - padR} y1={yHold(tk)} y2={yHold(tk)}
                        stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                  <text className="chart-axis-text" x={padL - 8} y={yHold(tk) + 3}
                        textAnchor="end" fill="var(--ink-2)">{tk}</text>
                </g>
              ))}
              {/* peak 강조선 */}
              {noTrades ? (
                <text className="chart-axis-text" x={W - padR + 6} y={hpPadT + hpInnerH / 2 + 3}
                      textAnchor="start" fill="var(--ink-3)">거래없음</text>
              ) : peakHoldings > 0 && (
                <text className="chart-axis-text" x={W - padR + 6} y={yHold(peakHoldings) + 3}
                      textAnchor="start" fill="var(--teal)">peak {peakHoldings}</text>
              )}
              {/* 동시보유 종목수 계단 라인(teal) */}
              <path d={holdPath} fill="none" stroke="var(--teal)" strokeWidth="1.8" opacity="0.95" />
            </svg>
            <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)",
                          marginTop: 2, paddingLeft: padL * (100 / W) + "%" }}>
              동시보유 종목수(매수~매도 구간 중첩). 보유금액(원)은 엔진 전용이라 미표시 — 동시보유 종목수로 대체.
            </div>
          </div>
        )}

        <div className="chart-wrap">
          {isDemo ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              데모 모드 — 백엔드 연결 시 백테 상세가 표시됩니다.
            </div>
          ) : err ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--red)", fontSize: 12, fontFamily: "var(--mono)" }}>
              조회 실패: {err}
            </div>
          ) : !hasSeries ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              {(summary.trade_count != null && summary.trade_count === 0)
                ? "이 세대는 거래가 없습니다 (타임아웃/무거래)"
                : "백테 결과 시계열이 없습니다(CSV 없음/토글)"}
            </div>
          ) : (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
                 onMouseMove={onMove} onMouseLeave={onLeave}>
              {/* 0 손익분기 기준선(막대 기준, 좌축) */}
              <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                    stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
              <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end"
                    fill="var(--ink-2)">0</text>
              {/* 좌축 라벨(일별손익 max/min) */}
              <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMax) + 3} textAnchor="end"
                    fill="var(--ink-2)">{fmtMoneyShort(pnlMax)}</text>
              {pnlMin < 0 && (
                <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMin) + 3} textAnchor="end"
                      fill="var(--ink-2)">{fmtMoneyShort(pnlMin)}</text>
              )}
              {/* 우축 라벨(누적수익 max/min) */}
              <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMax) + 3} textAnchor="start"
                    fill="var(--amber)">{fmtMoneyShort(cumMax)}</text>
              <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMin) + 3} textAnchor="start"
                    fill="var(--amber)">{fmtMoneyShort(cumMin)}</text>

              {/* X 프레임 */}
              <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* X 라벨(거래일) */}
              {xLabelIdxs.map((i) => (
                <text key={`bx${i}`} className="chart-axis-text"
                      x={xBar(i)} y={H - 10} textAnchor="middle">
                  {fmtDate(daily[i].date)}
                </text>
              ))}

              {/* 일별손익 막대(이익=red 위, 손실=blue 아래) */}
              {daily.map((d, i) => {
                const v = d.daily_pnl || 0;
                const yTop = v >= 0 ? yPnl(v) : zeroY;
                const yBot = v >= 0 ? zeroY : yPnl(v);
                const h = Math.max(0.5, yBot - yTop);
                const col = v >= 0 ? "var(--red)" : "var(--blue)";
                return <rect key={`bar${i}`} x={xBar(i) - barW / 2} y={yTop}
                             width={barW} height={h} fill={col} opacity="0.78" />;
              })}

              {/* 누적수익 곡선(우축, orange 굵은선) */}
              {cumulative.length > 1 && (
                <path d={cumPath} fill="none" stroke="var(--amber)" strokeWidth="2.2" opacity="0.95" />
              )}

              {/* Hover 수직선 + 강조 */}
              {hover != null && (() => {
                const hx = xBar(hover);
                return <g>
                  <line x1={hx} x2={hx} y1={padT} y2={padT + innerH}
                        stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
                  {cumulative[hover] && (
                    <circle cx={hx} cy={yCum(cumulative[hover].cum_profit || 0)} r="3.5"
                            fill="none" stroke="var(--amber)" strokeWidth="1.5" />
                  )}
                </g>;
              })()}
            </svg>
          )}

          {/* Hover 툴팁 */}
          {hover != null && hasSeries && daily[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px",
              fontFamily: "var(--mono)", fontSize: 11, minWidth: 190,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em",
                            textTransform: "uppercase", marginBottom: 4 }}>
                {fmtDate(daily[hover].date)} · {String(daily[hover].date)}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>일손익</span>
                <span className={daily[hover].daily_pnl > 0 ? "num-pos" : daily[hover].daily_pnl < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>
                  {fmtMoney(daily[hover].daily_pnl)}
                </span>
                <span style={{ color: "var(--ink-2)" }}>누적</span>
                <span style={{ textAlign: "right", color: "var(--amber)" }}>
                  {cumulative[hover] ? fmtMoney(cumulative[hover].cum_profit) : "—"}
                </span>
                {cumulative[hover] && cumulative[hover].cum_pct != null && (
                  <>
                    <span style={{ color: "var(--ink-2)" }}>누적%</span>
                    <span style={{ textAlign: "right" }}>{fmtPct(cumulative[hover].cum_pct)}</span>
                  </>
                )}
                <span style={{ color: "var(--ink-2)" }}>반납액</span>
                <span style={{ textAlign: "right", color: "var(--red)" }}>
                  {drawdown[hover] ? fmtMoney(drawdown[hover].drawdown) : "—"}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────
   명예의 전당 — 인간 벤치마크(19전략) + AI 생성 통합 패널.

   GET /hall_of_fame 에서 {human:[...], ai:[...]} 를 받아 한 테이블에 합쳐 보여준다.
   - 금액은 원 단위(fmtMoney), 수익률은 '운영금 대비'(%), 연평균은 단리 환산.
   - AI 단기창(annual_unreliable)은 연평균을 회색 + '단기' 표기(과대 환산 경고).
   - 인간(👤)은 초록/중립, AI(🤖)는 보라(violet) 뱃지로 시각 구분 → 인간 벤치마크가
     'AI가 도달해야 할 목표선'으로 한눈에 보이게 한다.
   - 정렬 토글(총수익률/연평균/MDD/payoff) + 필터(전체/인간/시드/AI). 기본=총수익률 ↓.
   - demo면 미fetch(EquityOverlayChart 패턴). 빈 응답이면 빈 상태.
   ───────────────────────────────────────────────────────────────────────── */
function HallOfFamePanel({ baseUrl, wsStatus }) {
  const [data, setData] = useState_eq(null);   // {human:[...], ai:[...]}
  const [loading, setLoading] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [sortKey, setSortKey] = useState_eq("total_return_pct"); // total_return_pct|total_return_krw|annual_return_pct|mdd_pct|payoff
  const [filter, setFilter] = useState_eq("all");                // all|human|ai
  const [galleryOpen, setGalleryOpen] = useState_eq(false);      // 📷 인간 결과 스크린샷 모달.
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_eq(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    fetch(baseUrl + "/hall_of_fame", { signal: AbortSignal.timeout(4000) })
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

  const human = (data && data.human) || [];
  const ai = (data && data.ai) || [];

  // 통합 행: 인간(max_holdings)·AI(max_hold_count)를 공통 max_hold로 정규화.
  const rows = [
    ...human.map(h => ({ ...h, _maxHold: h.max_holdings })),
    ...ai.map(a => ({ ...a, _maxHold: a.max_hold_count })),
  ].filter(r => (filter === "all" ? true : r.kind === filter));

  // 정렬: 선택 키 내림차순(없는 값은 맨 뒤). MDD는 낮을수록 좋지만 일관성 위해
  //   '값 큰 순'을 그대로 쓰되, 사용자가 의도적으로 토글한다(라벨로 의미 전달).
  const sorted = rows.slice().sort((a, b) => {
    const av = a[sortKey], bv = b[sortKey];
    const an = (typeof av === "number") ? av : -Infinity;
    const bn = (typeof bv === "number") ? bv : -Infinity;
    return bn - an;
  });

  const fmtPctSigned = (v) => (typeof v === "number"
    ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : "—");
  const fmtPlain = (v, d = 1) => (typeof v === "number" ? v.toFixed(d) : "—");
  const fmtInt2 = (v) => (typeof v === "number" ? Math.round(v).toLocaleString("ko-KR") : "—");

  const SORTS = [
    { key: "total_return_pct", label: "총수익률" },
    { key: "total_return_krw", label: "총수익금" },
    { key: "annual_return_pct", label: "연평균" },
    { key: "mdd_pct", label: "MDD" },
    { key: "payoff", label: "payoff" },
  ];
  const FILTERS = [
    { key: "all", label: "전체" },
    { key: "human", label: "👤 인간" },
    { key: "seed", label: "🌱 시드" },
    { key: "ai", label: "🤖 AI" },
  ];
  // 구분 뱃지 메타 — 인간 벤치마크(초록) / 시드 Tick_902 인간 튜닝(앰버) / AI 생성 AILOOP(보라).
  const HOF_KIND_META = {
    human: { color: "var(--green)",  label: "👤 인간", bg: "rgba(110,231,168,0.06)" },
    seed:  { color: "var(--amber)",  label: "🌱 시드", bg: "rgba(240,179,90,0.08)" },
    ai:    { color: "var(--violet)", label: "🤖 AI",   bg: "rgba(165,148,255,0.08)" },
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          🏆 성과 명예의 전당 — 인간 벤치마크 &amp; AI 생성
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <LegendDot color="var(--green)" label="👤 인간 벤치마크" />
          <LegendDot color="var(--amber)" label="🌱 시드(Tick_902 인간튜닝)" />
          <LegendDot color="var(--violet)" label="🤖 AI 생성(AILOOP)" />
          <span style={{ fontSize: 10, color: "var(--ink-3)", fontFamily: "var(--mono)" }}
                data-tip="백테 기간이 3개월 미만이면 연평균이 과대추정됨 — 신뢰 낮음">
            단기=연환산 신뢰낮음(짧은 백테)
          </span>
          <button className="btn ghost sm" onClick={() => setGalleryOpen(true)}
                  data-tip="인간 reference 결과 스크린샷 갤러리 열기">
            📷 인간 결과 스크린샷
          </button>
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}
                  data-tip="명예의 전당 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {/* 정렬/필터 컨트롤 */}
        <div style={{ display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>정렬</span>
            {SORTS.map(s => (
              <button key={s.key} className="btn ghost sm"
                      onClick={() => setSortKey(s.key)}
                      style={sortKey === s.key
                        ? { color: "var(--amber)", borderColor: "var(--amber)" } : undefined}>
                {s.label}
              </button>
            ))}
          </div>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>구분</span>
            {FILTERS.map(f => (
              <button key={f.key} className="btn ghost sm"
                      onClick={() => setFilter(f.key)}
                      style={filter === f.key
                        ? { color: "var(--ink-0)", borderColor: "var(--line-2)" } : undefined}>
                {f.label}
              </button>
            ))}
          </div>
          <div style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
            인간 {human.length} · 시드 {ai.filter(r => r.kind === "seed").length} · AI {ai.filter(r => r.kind === "ai").length}
          </div>
        </div>

        {isDemo ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            데모 모드 — 백엔드 연결 시 명예의 전당이 표시됩니다.
          </div>
        ) : err ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--red)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            조회 실패: {err}
          </div>
        ) : sorted.length === 0 ? (
          <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                        fontSize: 12, fontFamily: "var(--mono)" }}>
            표시할 전략이 없습니다 (인간 벤치마크 JSON / AI 흑자 세대 누적 시 표시).
          </div>
        ) : (
          <div className="hof-scroll" style={{ overflowX: "auto", width: "100%" }}>
            <table className="data-table" style={{ width: "100%", borderCollapse: "collapse",
                                                   fontFamily: "var(--mono)", fontSize: 12,
                                                   minWidth: 1180 }}>
              <thead>
                <tr style={{ color: "var(--ink-2)", fontSize: 10, letterSpacing: ".08em",
                             textTransform: "uppercase", borderBottom: "1px solid var(--line-2)" }}>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>구분</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>이름</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>총수익금(원)</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>총수익률%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>연평균%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>MDD%</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>payoff</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>일평균거래</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>동시보유</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>운영금(원)</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>백테 기간</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r, i) => {
                  const _km = HOF_KIND_META[r.kind] || HOF_KIND_META.ai;
                  const accent = _km.color;
                  return (
                    <tr key={(r.kind || "") + (r.label || "") + i}
                        style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      <td style={{ padding: "5px 8px" }}>
                        <span style={{
                          display: "inline-block", padding: "1px 6px", borderRadius: 4,
                          fontSize: 10, fontWeight: 600, color: accent,
                          border: `1px solid ${accent}`,
                          background: _km.bg,
                        }}>
                          {_km.label}
                        </span>
                      </td>
                      <td style={{ padding: "5px 8px", color: "var(--ink-0)" }}>{r.label || "—"}</td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: (typeof r.total_return_krw === "number" && r.total_return_krw > 0)
                                     ? "var(--teal)" : "var(--ink-0)" }}>
                        {typeof r.total_return_krw === "number" ? fmtMoney(r.total_return_krw) : "—"}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: (typeof r.total_return_pct === "number" && r.total_return_pct > 0)
                                     ? "var(--teal)" : "var(--ink-0)" }}>
                        {fmtPctSigned(r.total_return_pct)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right",
                                   color: r.annual_unreliable ? "var(--ink-3)" : "var(--ink-0)" }}>
                        {fmtPctSigned(r.annual_return_pct)}
                        {r.annual_unreliable && (
                          <span
                            data-tip="백테 기간이 3개월 미만이라 연평균이 과대추정됨(1개월 7%→연84% 식). 단기 창은 신뢰 낮음."
                            title="백테 기간이 3개월 미만이라 연평균이 과대추정됨(1개월 7%→연84% 식). 단기 창은 신뢰 낮음."
                            style={{ fontSize: 9, color: "var(--ink-3)", marginLeft: 4,
                                     borderBottom: "1px dotted var(--ink-3)", cursor: "help" }}>
                            단기
                          </span>
                        )}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--red)" }}>
                        {fmtPlain(r.mdd_pct, 2)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {fmtPlain(r.payoff, 2)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {fmtPlain(r.daily_avg_trades, 1)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" }}>
                        {typeof r._maxHold === "number" ? fmtPlain(r._maxHold, r.kind === "ai" ? 1 : 0) : "—"}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "right", color: "var(--ink-2)" }}>
                        {fmtInt2(r.operating_capital_krw)}
                      </td>
                      <td style={{ padding: "5px 8px", textAlign: "left", color: "var(--ink-2)",
                                   whiteSpace: "nowrap", fontSize: 11 }}>
                        {r.period || "—"}
                        {typeof r.days === "number" && (
                          <span style={{ color: "var(--ink-3)", marginLeft: 5 }}>
                            ({r.days}일)
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
      {galleryOpen && (
        <ReferenceGallery baseUrl={baseUrl} onClose={() => setGalleryOpen(false)} />
      )}
    </div>
  );
}

/* 📷 인간 결과 스크린샷 갤러리 모달.
   GET /reference_screenshots 로 파일명 목록(17장)을 받아 썸네일 그리드로 보여주고,
   썸네일 클릭 시 같은 모달에서 확대(라이트박스)한다. 이미지 src는
   baseUrl+'/reference_img/'+filename(StaticFiles 읽기 전용 마운트)로 직접 가져온다.
   스크린샷↔전략# 매핑은 불확실하므로 개별 행 정확 매핑을 시도하지 않고 전체 갤러리
   브라우징만 제공한다(정직). 모달 패턴은 CodeViewer(modal-bd/modal)를 따른다. */
const { useState: useState_rg, useEffect: useEffect_rg } = React;

function ReferenceGallery({ baseUrl, onClose }) {
  const [files, setFiles] = useState_rg(null);   // string[] | null
  const [err, setErr] = useState_rg(null);
  const [zoom, setZoom] = useState_rg(null);     // 확대 중인 파일명 | null

  useEffect_rg(() => {
    if (!baseUrl) { setFiles([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/reference_screenshots", { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { if (!cancelled) { setFiles(j.screenshots || []); setErr(null); } })
      .catch(e => { if (!cancelled) setErr(String(e)); })
      .finally(() => {});
    return () => { cancelled = true; };
  }, [baseUrl]);

  const imgSrc = (name) => baseUrl + "/reference_img/" + encodeURIComponent(name);

  return (
    <div className="modal-bd"
         onMouseDown={(e) => { if (e.target === e.currentTarget) (zoom ? setZoom(null) : onClose()); }}>
      <div className="modal" style={{ width: "min(1100px, calc(100vw - 32px))" }}
           onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-hd">
          <h2>
            📷 인간 결과 스크린샷
            <span className="sub">
              STOM_Good_Results — 결과 화면 {files ? files.length : "…"}장 · 스크린샷↔전략# 매핑 불확실(전체 브라우징)
            </span>
          </h2>
          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
            {zoom && (
              <button className="btn ghost sm" onClick={() => setZoom(null)}>← 그리드</button>
            )}
            <button className="btn ghost sm" onClick={onClose}>닫기</button>
          </div>
        </div>

        <div style={{ flex: 1, overflowY: "auto", padding: 16 }}>
          {err ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--red)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              스크린샷 목록 조회 실패: {err}
            </div>
          ) : files == null ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              스크린샷 불러오는 중…
            </div>
          ) : files.length === 0 ? (
            <div style={{ padding: "28px 0", textAlign: "center", color: "var(--ink-3)",
                          fontSize: 12, fontFamily: "var(--mono)" }}>
              표시할 스크린샷이 없습니다.
            </div>
          ) : zoom ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <img src={imgSrc(zoom)} alt={zoom}
                   style={{ maxWidth: "100%", maxHeight: "70vh", objectFit: "contain",
                            border: "1px solid var(--line-2)", borderRadius: 6 }} />
              <div style={{ fontSize: 11, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>{zoom}</div>
            </div>
          ) : (
            <div style={{ display: "grid",
                          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 12 }}>
              {files.map((name) => (
                <div key={name} onClick={() => setZoom(name)}
                     data-tip="클릭하면 확대"
                     style={{ cursor: "zoom-in", border: "1px solid var(--line-2)",
                              borderRadius: 6, overflow: "hidden", background: "var(--bg-0)" }}>
                  <img src={imgSrc(name)} alt={name} loading="lazy"
                       style={{ width: "100%", height: 120, objectFit: "cover", display: "block" }} />
                  <div style={{ fontSize: 9.5, color: "var(--ink-3)", fontFamily: "var(--mono)",
                                padding: "4px 6px", whiteSpace: "nowrap", overflow: "hidden",
                                textOverflow: "ellipsis" }}>
                    {name}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { FitnessChart, ProfitChart, EquityOverlayChart, QualityTrendChart, BacktestDetailChart, HallOfFamePanel, ReferenceGallery });
