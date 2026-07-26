/* Backtest workbench analysis charts — 분포·히트맵 차트 묶음 (split from backtest-charts.jsx).
   손익 히스토그램·요일×시간 히트맵·몬테카를로 팬·월별 캘린더 — 빈도/분포 기반 차트.
   chart.jsx 의 디자인 언어(chart-wrap·chart-grid-line·chart-axis-text·Mini·LegendDot)를 따른다.
*/
import { LegendDot, Mini, MetricHelpStrip } from "./chart.jsx";
import {
  useState_btc, useRef_btc, useMemo_btc, useEffect_btc,
  _btMoneyTick, _btAxisTicks, _BT_WEEKDAYS, _BtChartEmpty,
} from "./bt-chart-utils.jsx";
import { ChartFrame } from "./chart-frame.jsx";

function _btDistributionWithEvidence(Chart, describe) {
  return function EvidenceChart(props) {
    return <ChartFrame {...describe(props)}><Chart {...props} /></ChartFrame>;
  };
}

/* ② 손익 히스토그램 — analysis.distribution.pnl_histogram [{bin_start,bin_end,count,unit}].
   각 bin 을 막대로(손실 구간 red / 이익 구간 teal / 0 걸친 구간 amber), 0% 경계선 강조. */
function _BtDistributionChartContent({ distribution }) {
  const bins = (distribution && distribution.pnl_histogram) || [];
  const [hover, setHover] = useState_btc(null);

  const W = 880, H = 260;
  const padL = 44, padR = 24, padT = 18, padB = 34;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = bins.length;
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.82);
  const xLeft = (i) => padL + slot * i;

  const maxCount = Math.max(1, ...bins.map(b => b.count || 0));
  const yBar = (c) => padT + innerH - (c / maxCount) * innerH;

  // 0% 경계 위치(bin 좌표 보간) — 손익분기 기준선.
  const zeroX = useMemo_btc(() => {
    if (!n) return null;
    for (let i = 0; i < n; i++) {
      const b = bins[i];
      if (b.bin_start <= 0 && b.bin_end >= 0) {
        const frac = (b.bin_end - b.bin_start) ? (0 - b.bin_start) / (b.bin_end - b.bin_start) : 0.5;
        return xLeft(i) + slot * Math.max(0, Math.min(1, frac));
      }
    }
    return null;
  }, [bins, n]);

  const binColor = (b) => {
    if (b.bin_end <= 0) return "var(--red)";
    if (b.bin_start >= 0) return "var(--teal)";
    return "var(--amber)";
  };

  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(t => Math.round(t * maxCount));

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          손익 분포 — Histogram
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="이익 bin" />
          <LegendDot color="var(--red)" label="손실 bin" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "x축 = 거래 수익률(%) 구간",
          "y축 = 해당 구간 거래 수",
          "0% 경계선 좌=손실 / 우=이익",
        ]} />
        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseLeave={() => setHover(null)}>
            {/* Y 그리드 + 눈금 */}
            {yTicks.map((t, i) => (
              <g key={`hy${i}`}>
                <line className="chart-grid-line" x1={padL} x2={W - padR} y1={yBar(t)} y2={yBar(t)} />
                <text className="chart-axis-text" x={padL - 8} y={yBar(t) + 3} textAnchor="end">{t}</text>
              </g>
            ))}
            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {/* 막대 */}
            {bins.map((b, i) => {
              const c = b.count || 0;
              const top = yBar(c), h = Math.max(0, (padT + innerH) - top);
              return <rect key={`hb${i}`} x={xLeft(i) + (slot - barW) / 2} y={top} width={barW} height={h}
                           fill={binColor(b)} opacity={hover === i ? 1 : 0.7}
                           onMouseEnter={() => setHover(i)} />;
            })}
            {/* 0% 경계선 */}
            {zeroX != null && (
              <>
                <line x1={zeroX} x2={zeroX} y1={padT} y2={padT + innerH}
                      stroke="rgba(255,255,255,0.4)" strokeWidth="1" strokeDasharray="3 3" />
                <text className="chart-axis-text" x={zeroX} y={padT - 4} textAnchor="middle" fill="var(--ink-1)">0%</text>
              </>
            )}
            {/* X 라벨(min/max) */}
            {n > 0 && (
              <>
                <text className="chart-axis-text" x={padL} y={H - 10} textAnchor="start">
                  {(bins[0].bin_start).toFixed(1)}%
                </text>
                <text className="chart-axis-text" x={W - padR} y={H - 10} textAnchor="end">
                  {(bins[n - 1].bin_end).toFixed(1)}%
                </text>
              </>
            )}
          </svg>

          {hover != null && bins[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 180, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>구간</span>
                <span style={{ textAlign: "right" }}>
                  {bins[hover].bin_start.toFixed(1)}~{bins[hover].bin_end.toFixed(1)}%
                </span>
                <span style={{ color: "var(--ink-2)" }}>거래수</span>
                <span style={{ textAlign: "right" }}>{bins[hover].count}</span>
              </div>
            </div>
          )}

          {n === 0 && <_BtChartEmpty message="거래가 누적되면 손익 분포가 표시됩니다" />}
        </div>
      </div>
    </div>
  );
}

/* ③ 요일×시간 히트맵 — analysis.heatmap.cells [{weekday,slot,slot_label,profit_pct_sum,profit_krw,trades}].
   행=요일(월~금 우선, 토/일은 데이터 있을 때만), 열=30분 슬롯(09:00~15:30 범위).
   셀 값=수익률 합계(%) (수익금 절대액은 종목 규모에 좌우돼 시간대 비교에 부적합).
   셀 색: 부호·크기(red↔teal, 0 중심), hover 시 수익률 합계·수익금·거래수 툴팁. */
function _BtHeatmapContent({ heatmap }) {
  const cells = (heatmap && heatmap.cells) || [];
  const [hover, setHover] = useState_btc(null);
  // B1 — 컨테이너 폭 추종 동적 셀 크기. ResizeObserver 로 래퍼 폭을 측정해 셀을 키운다.
  const wrapRef = useRef_btc(null);
  const [wrapW, setWrapW] = useState_btc(0);
  useEffect_btc(() => {
    const el = wrapRef.current;
    if (!el || typeof ResizeObserver === "undefined") return undefined;
    const ro = new ResizeObserver((entries) => {
      for (const e of entries) {
        const w = e.contentRect ? e.contentRect.width : el.clientWidth;
        setWrapW(Math.max(0, Math.floor(w)));
      }
    });
    ro.observe(el);
    setWrapW(Math.max(0, Math.floor(el.clientWidth)));
    return () => { try { ro.disconnect(); } catch (e) {} };
  }, []);

  // 등장 슬롯 집합(정렬) — 거래 없는 슬롯 열은 생략.
  const slots = useMemo_btc(() => {
    const s = Array.from(new Set(cells.map(c => c.slot))).sort((a, b) => a - b);
    return s;
  }, [cells]);

  // 등장 요일(0~6). 토/일은 거래 있을 때만 표기, 평일은 항상.
  const weekdays = useMemo_btc(() => {
    const present = new Set(cells.map(c => c.weekday));
    const base = [0, 1, 2, 3, 4];
    [5, 6].forEach(w => { if (present.has(w)) base.push(w); });
    return base;
  }, [cells]);

  // (weekday,slot) → cell 빠른 조회.
  const cellMap = useMemo_btc(() => {
    const m = {};
    for (const c of cells) m[c.weekday + "_" + c.slot] = c;
    return m;
  }, [cells]);

  // 셀 1차 지표 = 수익률 합계(%). 구버전 API(profit_pct_sum 부재) 면 0 으로 폴백.
  const cellPct = (c) => (c ? Number(c.profit_pct_sum || 0) : 0);
  // 색 스케일 — 수익률 합계 절대 최대값 기준 정규화(0 중심: 이익 teal / 손실 red).
  const maxAbs = Math.max(1e-6, ...cells.map(c => Math.abs(cellPct(c))));
  const cellColor = (c) => {
    if (!c) return "var(--bg-0)";
    const t = Math.min(1, Math.abs(cellPct(c)) / maxAbs);
    if (cellPct(c) >= 0) {
      return `rgba(76,214,179,${(0.12 + 0.66 * t).toFixed(3)})`;
    }
    return `rgba(255,107,107,${(0.12 + 0.66 * t).toFixed(3)})`;
  };

  const slotLabel = (slot) => {
    const found = cells.find(c => c.slot === slot);
    if (found && found.slot_label) return found.slot_label;
    const m = slot * 30;
    return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
  };

  // B1 — 측정 폭으로 셀 크기를 동적 산출(전체 패널 폭 사용). 행 라벨 폭·간격을 빼고
  //   슬롯 수로 균등 분배. 최소 34px(기존)·최대 96px 로 클램프, 셀이 크면 값 폰트도 키운다.
  const SP = 3;          // borderSpacing.
  const ROW_LBL = 34;    // 요일 라벨 열 폭.
  const colN = Math.max(1, slots.length);
  const avail = wrapW > 0 ? wrapW - ROW_LBL - SP * (colN + 1) - 2 : 0;
  const cellW = avail > 0
    ? Math.max(34, Math.min(96, Math.floor(avail / colN)))
    : 34;
  const cellH = Math.max(26, Math.min(64, Math.round(cellW * 0.72)));
  const big = cellW >= 52;                 // 셀이 충분히 크면 값 폰트 확대.
  const valFont = big ? Math.min(18, Math.round(cellH * 0.34)) : 9.5;
  const hdFont = big ? 11 : 9.5;
  const lblFont = big ? 13 : 11;
  // 수익률 합계(%) 라벨 — "+12.3%" / "-4.5%" 형식(부호 포함).
  const cellPctLabel = (v) => `${(v || 0) >= 0 ? "+" : ""}${(v || 0).toFixed(1)}%`;
  // v5.11.3 — 슬롯이 몇 개 없으면 표를 100% 로 늘리지 않는다. 연구 시간대가 09:00~09:28
  //   한 구간뿐인 run 에서는 셀 하나가 카드 전체를 덮어 "거대한 단색 블록"으로 보였다.
  const stretch = colN >= 6;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          요일 × 시간대 히트맵
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>매수시각 기준 · 수익률 합계(%)</span>
      </div>
      <div className="panel-bd">
        {/* 측정 래퍼 — 전체 폭을 차지해 ResizeObserver 가 패널 폭을 읽는다. */}
        <div ref={wrapRef} style={{ width: "100%" }}>
          {cells.length === 0 ? (
            <div style={{ position: "relative", minHeight: 120 }}>
              <_BtChartEmpty message="거래가 누적되면 시간대 히트맵이 표시됩니다" />
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ borderCollapse: "separate", borderSpacing: SP, fontFamily: "var(--mono)",
                              width: stretch ? "100%" : "auto", maxWidth: "100%", tableLayout: "fixed" }}>
                <thead>
                  <tr>
                    <th style={{ width: ROW_LBL }}></th>
                    {slots.map(s => (
                      <th key={s} style={{ fontSize: hdFont, color: "var(--ink-3)", fontWeight: 400, padding: "0 1px", whiteSpace: "nowrap" }}>
                        {slotLabel(s)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {weekdays.map(w => (
                    <tr key={w}>
                      <td style={{ fontSize: lblFont, color: "var(--ink-2)", textAlign: "center", paddingRight: 4 }}>
                        {_BT_WEEKDAYS[w]}
                      </td>
                      {slots.map(s => {
                        const c = cellMap[w + "_" + s];
                        const key = w + "_" + s;
                        return (
                          <td key={s}
                              onMouseEnter={() => c && setHover(key)}
                              onMouseLeave={() => setHover(null)}
                              title={c ? `${_BT_WEEKDAYS[w]} ${slotLabel(s)} · 수익률 합계 ${cellPctLabel(cellPct(c))} · 수익금 ${fmtMoney(c.profit_krw)} · ${c.trades}건` : ""}
                              style={{
                                width: cellW, height: cellH, borderRadius: 4,
                                background: cellColor(c),
                                border: hover === key ? "1px solid var(--ink-0)" : "1px solid var(--line-1)",
                                textAlign: "center", fontSize: valFont, lineHeight: 1.15,
                                color: c ? "var(--ink-0)" : "var(--ink-3)",
                                cursor: "default", verticalAlign: "middle",
                              }}>
                            {c ? (
                              big ? (
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                                  <span style={{ fontWeight: 600, color: cellPct(c) >= 0 ? "var(--teal)" : "var(--red)" }}>
                                    {cellPctLabel(cellPct(c))}
                                  </span>
                                  <span style={{ fontSize: Math.max(8.5, valFont - 5), color: "var(--ink-3)" }}>
                                    {c.trades}건
                                  </span>
                                </div>
                              ) : cellPctLabel(cellPct(c))
                            ) : ""}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              <div style={{ display: "flex", gap: 14, marginTop: 10, alignItems: "center" }}>
                <LegendDot color="rgba(76,214,179,0.78)" label="이익 슬롯(수익률 합계 +)" />
                <LegendDot color="rgba(255,107,107,0.78)" label="손실 슬롯(수익률 합계 −)" />
                <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                  {big ? "셀 = 수익률 합계(%) · 거래 건수" : "셀 = 수익률 합계(%)"}
                </span>
              </div>
              {slots.length === 1 && (
                <p className="mono" style={{ margin: "8px 0 0", fontSize: 10.5, color: "var(--ink-3)", lineHeight: 1.55 }}>
                  이 연구는 시간대가 <b>{slotLabel(slots[0])}</b> 한 구간뿐이라 시간대 축이 만들어지지 않습니다.
                  지금은 요일별 비교로 읽으세요.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ⑦ 몬테카를로 팬 차트 — analysis montecarlo {fan:[{day_index,p5,p25,p50,p75,p95}], mdd_pct, final, ruin_prob, observed}.
   누적 손익 분포 밴드(p5~p95 음영) + 실측 곡선 오버레이 + MDD 분포 미니 히스토그램 + 파산/기대MDD 카드. */
function _BtMonteCarloChartContent({ mc, loading, onRun }) {
  const fan = (mc && mc.fan) || [];
  const observed = mc && mc.observed;
  const n = fan.length;

  const W = 880, H = 300;
  const padL = 58, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // y 도메인 — p5 최저 ~ p95 최고(0 포함).
  const allLo = fan.map(f => f.p5);
  const allHi = fan.map(f => f.p95);
  const obsVal = observed ? [observed.final_krw, 0] : [0];
  const yMin = Math.min(0, ...allLo, ...obsVal);
  const yMax = Math.max(0, ...allHi, ...obsVal);
  const yRange = (yMax - yMin) || 1;
  const x = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;
  const y = (v) => padT + innerH - ((v - yMin) / yRange) * innerH;

  const band = (loKey, hiKey) => {
    if (n < 2) return "";
    const top = fan.map((f, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(f[hiKey]).toFixed(1)}`).join(" ");
    const bot = fan.slice().reverse().map((f, i) => `L ${x(n - 1 - i).toFixed(1)} ${y(f[loKey]).toFixed(1)}`).join(" ");
    return `${top} ${bot} Z`;
  };
  const median = useMemo_btc(() => {
    if (n < 2) return "";
    return fan.map((f, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(f.p50).toFixed(1)}`).join(" ");
  }, [fan, n, yMin, yRange]);

  // 실측 곡선(셔플 없는 원래 순서) — observed 는 최종값만 있어 fan median 과 비교용으로 직선 보조.
  const zeroY = y(0);

  const q = (obj) => obj || { p5: 0, p25: 0, p50: 0, p75: 0, p95: 0 };
  const mddPct = q(mc && mc.mdd_pct);
  const finalQ = q(mc && mc.final);
  const ruin = mc && typeof mc.ruin_prob === "number" ? mc.ruin_prob : null;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          몬테카를로 — 누적손익 팬
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
            {mc && mc.n ? `${mc.n.toLocaleString("ko-KR")}회 · ${mc.days}일` : "미실행"}
          </span>
          <button className="btn ghost sm" onClick={onRun} disabled={loading}>{loading ? "계산중…" : "↻ 재계산"}</button>
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "일별 손익을 무작위 재배열한 분포",
          "밴드 = p5~p95 / 진한선 = 중앙값(p50)",
          "거래 순서가 결과에 준 영향(운) 진단",
        ]} />
        {/* 분포 카드 행 */}
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="기대 MDD p95" value={fmtPct(mddPct.p95)} color="var(--red)" />
          <Mini label="MDD 중앙값" value={fmtPct(mddPct.p50)} />
          <Mini label="최종손익 p50" value={fmtMoney(finalQ.p50)}
                color={finalQ.p50 > 0 ? "var(--teal)" : finalQ.p50 < 0 ? "var(--red)" : undefined} />
          <Mini label="파산확률" value={ruin != null ? fmtPct(ruin * 100) : "—"}
                color={ruin != null && ruin >= 0.2 ? "var(--red)" : ruin != null && ruin >= 0.05 ? "var(--amber)" : undefined}
                sub={mc && mc.ruin_pct ? `자본 -${Math.round(mc.ruin_pct)}%` : undefined} />
        </div>
        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            {/* 0 기준선 */}
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={y(yMax) + 3} textAnchor="end" fill="var(--chart-profit)">{_btMoneyTick(yMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={y(yMin) + 3} textAnchor="end" fill="var(--chart-loss)">{_btMoneyTick(yMin)}</text>
            {/* Frame */}
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--chart-grid)" strokeWidth="1" />
            {/* 밴드 p5~p95(연한), p25~p75(진한) */}
            {n > 1 && (
              <>
                <path d={band("p5", "p95")} fill="rgba(155,135,245,0.12)" />
                <path d={band("p25", "p75")} fill="rgba(155,135,245,0.24)" />
                <path d={median} fill="none" stroke="var(--chart-accent)" strokeWidth="2" />
              </>
            )}
            {/* 관측 최종손익 마지막 점 가이드 */}
            {observed && n > 1 && (
              <circle cx={x(n - 1)} cy={y(observed.final_krw)} r="4" fill="var(--amber)" stroke="var(--bg-0)" strokeWidth="1" />
            )}
          </svg>

          {n === 0 && <_BtChartEmpty message="몬테카를로를 실행하면 손익 분포 팬이 표시됩니다 (거래일 2일 이상 필요)" />}
        </div>
        {/* MDD 분포 미니 박스(p5~p95) */}
        {mc && mc.n > 0 && (
          <_BtMddBox mddPct={mddPct} observedPct={observed ? observed.mdd_pct : null} />
        )}
      </div>
    </div>
  );
}

// MDD 백분위 분포 미니 박스플롯(가로) — p5~p95 범위에 p25/50/75 박스 + 실측 마커.
// fan 백분위의 요약 장식이며, 별도 원본 행을 만들거나 증거 차트로 취급하지 않는다.
function _BtMddBox({ mddPct, observedPct }) {
  const lo = mddPct.p5, hi = Math.max(mddPct.p95, observedPct || 0, 0.0001);
  const span = (hi - lo) || 1;
  const fx = (v) => ((v - lo) / span) * 100;
  return (
    <div style={{ marginTop: 12 }}>
      <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>MDD 분포 (%)</div>
      <div style={{ position: "relative", height: 26, background: "var(--bg-0)", border: "1px solid var(--line-1)", borderRadius: 4 }}>
        {/* p25~p75 박스 */}
        <div style={{ position: "absolute", top: 6, height: 14, borderRadius: 3,
                      left: fx(mddPct.p25) + "%", width: Math.max(1, fx(mddPct.p75) - fx(mddPct.p25)) + "%",
                      background: "rgba(255,107,107,0.28)", border: "1px solid rgba(255,107,107,0.5)" }} />
        {/* p50 중앙선 */}
        <div style={{ position: "absolute", top: 4, height: 18, width: 2, background: "var(--red)", left: fx(mddPct.p50) + "%" }} />
        {/* 실측 마커 */}
        {observedPct != null && (
          <div title="실측 MDD" style={{ position: "absolute", top: 2, height: 22, width: 2, background: "var(--amber)", left: Math.max(0, Math.min(100, fx(observedPct))) + "%" }} />
        )}
      </div>
      <div className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--ink-3)", marginTop: 3 }}>
        <span>p5 {mddPct.p5.toFixed(1)}%</span>
        <span style={{ color: "var(--amber)" }}>{observedPct != null ? `실측 ${observedPct.toFixed(1)}%` : ""}</span>
        <span>p95 {mddPct.p95.toFixed(1)}%</span>
      </div>
    </div>
  );
}

const _BT_MONTHS = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

/* ⑫ 월별 캘린더 히트맵(트랙 D) — analysis.monthly {years:[...], cells:[{year,month,profit_krw,trades,win_rate}]}.
   행=연도, 열=1~12월. 셀 색=실현손익 부호·크기. 거래 없는 (연,월) 은 빈 셀. */
function _BtMonthlyCalendarContent({ monthly }) {
  const years = (monthly && monthly.years) || [];
  const cells = (monthly && monthly.cells) || [];
  const [hover, setHover] = useState_btc(null);

  const cellMap = useMemo_btc(() => {
    const m = {};
    for (const c of cells) m[c.year + "_" + c.month] = c;
    return m;
  }, [cells]);

  const maxAbs = Math.max(1, ...cells.map(c => Math.abs(c.profit_krw || 0)));
  const cellColor = (c) => {
    if (!c) return "var(--bg-0)";
    const t = Math.min(1, Math.abs(c.profit_krw || 0) / maxAbs);
    if ((c.profit_krw || 0) >= 0) return `rgba(76,214,179,${(0.12 + 0.66 * t).toFixed(3)})`;
    return `rgba(255,107,107,${(0.12 + 0.66 * t).toFixed(3)})`;
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          월별 수익 캘린더
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>매도일 기준 · 월별 손익 합</span>
      </div>
      <div className="panel-bd">
        {cells.length === 0 ? (
          <div style={{ position: "relative", minHeight: 120 }}>
            <_BtChartEmpty message="거래가 누적되면 월별 수익 캘린더가 표시됩니다" />
          </div>
        ) : (
          <div className="bt-monthly-calendar-scroll" style={{ overflowX: "auto" }}>
            <table className="bt-monthly-calendar-table" style={{ borderCollapse: "separate", borderSpacing: 5, fontFamily: "var(--mono)" }}>
              <thead>
                <tr>
                  <th style={{ width: 44 }}></th>
                  {_BT_MONTHS.map((m, i) => (
                    <th key={i} style={{ fontSize: 9.5, color: "var(--ink-3)", fontWeight: 400, padding: "0 1px", whiteSpace: "nowrap" }}>{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {years.map(yr => (
                  <tr key={yr}>
                    <td style={{ fontSize: 11, color: "var(--ink-2)", textAlign: "center", paddingRight: 4 }}>{yr}</td>
                    {_BT_MONTHS.map((_, mi) => {
                      const month = mi + 1;
                      const key = yr + "_" + month;
                      const c = cellMap[key];
                      return (
                        <td key={mi}
                            onMouseEnter={() => c && setHover(key)}
                            onMouseLeave={() => setHover(null)}
                            title={c ? `${yr}년 ${month}월 · ${fmtMoney(c.profit_krw)} · ${c.trades}건 · ${fmtPct(c.win_rate)}` : ""}
                            style={{
                              width: 64, height: 44, borderRadius: 6,
                              background: cellColor(c),
                              border: hover === key ? "1px solid var(--ink-0)" : "1px solid var(--line-1)",
                              textAlign: "center", fontSize: 10.5, lineHeight: 1.3,
                              color: c ? "var(--ink-0)" : "var(--ink-3)",
                            }}>
                          {c ? (
                            <div>
                              <div style={{ fontSize: 11 }}>{_btMoneyTick(c.profit_krw)}</div>
                              <div style={{ fontSize: 9.5, color: "var(--ink-2)" }}>{c.trades}건</div>
                            </div>
                          ) : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: "flex", gap: 14, marginTop: 10, alignItems: "center" }}>
              <LegendDot color="rgba(76,214,179,0.78)" label="이익 월" />
              <LegendDot color="rgba(255,107,107,0.78)" label="손실 월" />
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>셀 = 손익 · 거래수</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const BtDistributionChart = _btDistributionWithEvidence(_BtDistributionChartContent, ({ distribution }) => ({
  title: "손익 분포 — Histogram", unit: "거래 수", period: "거래별 수익률 구간",
  sampleCount: Array.isArray(distribution && distribution.pnl_histogram) ? distribution.pnl_histogram.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0%", source: "analysis.distribution.pnl_histogram",
  rows: distribution && distribution.pnl_histogram, columns: ["bin_start", "bin_end", "count", "unit"], rowKey: row => `${row.bin_start}:${row.bin_end}`,
}));
const BtHeatmap = _btDistributionWithEvidence(_BtHeatmapContent, ({ heatmap }) => ({
  title: "요일 × 시간대 히트맵", unit: "수익률 합계 (%)", period: "매수 시각별",
  sampleCount: Array.isArray(heatmap && heatmap.cells) ? heatmap.cells.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0%", source: "analysis.heatmap.cells",
  rows: heatmap && heatmap.cells, columns: ["weekday", "slot_label", "profit_pct_sum", "profit_krw", "trades"],
  rowKey: row => `${row.weekday}:${row.slot}`,
}));
const BtMonteCarloChart = _btDistributionWithEvidence(_BtMonteCarloChartContent, ({ mc, loading }) => ({
  title: "몬테카를로 — 누적손익 팬", unit: "누적 손익 (원)", period: "시뮬레이션 일자별",
  sampleCount: Array.isArray(mc && mc.fan) ? mc.fan.length : 0,
  freshness: loading ? "계산 중" : "백테스트 분석 응답", threshold: "p5~p95 분포", source: "analysis.montecarlo.fan",
  status: loading ? "loading" : undefined, rows: mc && mc.fan,
  columns: ["day_index", "p5", "p25", "p50", "p75", "p95"], rowKey: "day_index",
}));
const BtMonthlyCalendar = _btDistributionWithEvidence(_BtMonthlyCalendarContent, ({ monthly }) => ({
  title: "월별 수익 캘린더", unit: "월별 손익 (원)", period: "매도일 월별",
  sampleCount: Array.isArray(monthly && monthly.cells) ? monthly.cells.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.monthly.cells",
  rows: monthly && monthly.cells, columns: ["year", "month", "profit_krw", "trades", "win_rate"],
  rowKey: row => `${row.year}:${row.month}`,
}));

export {
  BtDistributionChart, BtHeatmap, BtMonteCarloChart, BtMonthlyCalendar,
};
