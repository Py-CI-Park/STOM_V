/* Chart — 세대 진화 추이 차트 묶음 (split from chart.jsx, P5.4).
   FitnessChart · ProfitChart · QualityTrendChart — state.generations[] 를 SVG 로 그리는
   진화 추이 차트(적합도·수익·품질지표). app.jsx 가 chart.jsx 배럴 경유로 import.
   - 작은 표현 컴포넌트(LegendDot · Mini · MetricHelpStrip)는 chart-primitives 에서 import.
   - 포맷 헬퍼(fmtScore · fmtPct · fmtMoney)는 stom-ui 빌드 번들이 제공하는 전역(connection.jsx
     의 const X = window.X 별칭이 babel 스코프보다 먼저 로드)을 bare 호출로 그대로 쓴다.
   - 축 눈금(_axisTicks)도 stom-ui(bundle/stom-ui.js, 소스 format.mjs)가 window._axisTicks 로
     제공하므로 babel 스코프 별칭만 둔다(NEVER import-convert).
   - fetch 기반 백테 상세/오버랩(EquityOverlayChart · BacktestDetailChart)은 chart-backtest-detail 로 분리.
*/
import { LegendDot, Mini, MetricHelpStrip } from "./chart-primitives.jsx";

const { useMemo: useMemo_c, useState: useState_c, useRef: useRef_c } = React;

// 축 눈금 값 배열 — Phase14.3 de-dup: 구현은 빌드 번들(bundle/stom-ui.js, 소스 format.mjs)이
//   window._axisTicks 로 제공(ESM 모듈이라 babel 실행보다 먼저 로드). 여기서는 babel 스코프
//   별칭만 둬서 기존 bare 호출(_axisTicks(...))이 계속 해소되게 한다.
const _axisTicks = window._axisTicks;

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
          적합도 추이
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
          수익 추이
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
            {/* 좌축 중간 눈금(수익률 %) — 0·max·min 과 겹치면 생략. */}
            {_axisTicks(pctMin, pctMax, 5).map((tv, i) => (
              (Math.abs(tv) < 1e-9 || Math.abs(tv - pctMax) < 1e-9 || Math.abs(tv - pctMin) < 1e-9) ? null : (
                <g key={`pyl${i}`}>
                  <line x1={padL} x2={W - padR} y1={yPct(tv)} y2={yPct(tv)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                  <text className="chart-axis-text" x={padL - 8} y={yPct(tv) + 3} textAnchor="end" fill="var(--ink-3)">{tv.toFixed(1)}%</text>
                </g>
              )
            ))}
            {/* 우축 라벨(수익금 max/min) */}
            <text className="chart-axis-text" x={W - padR + 6} y={yMoney(moneyMax) + 3} textAnchor="start"
                  fill="var(--blue)">{fmtMoney(moneyMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yMoney(moneyMin) + 3} textAnchor="start"
                  fill="var(--blue)">{fmtMoney(moneyMin)}</text>
            {/* 우축 중간 눈금(수익금) — max·min 과 겹치면 생략. */}
            {_axisTicks(moneyMin, moneyMax, 5).map((tv, i) => (
              (Math.abs(tv - moneyMax) < 1e-9 || Math.abs(tv - moneyMin) < 1e-9) ? null : (
                <text key={`pyr${i}`} className="chart-axis-text" x={W - padR + 6} y={yMoney(tv) + 3} textAnchor="start" fill="var(--ink-3)">{fmtMoney(tv)}</text>
              )
            ))}
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
          품질지표 추이
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

// Track Z (PR-3) — dual-safe ESM export (kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { FitnessChart, ProfitChart, QualityTrendChart };
