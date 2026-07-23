/* Backtest workbench analysis charts — 시계열·산점 차트 묶음 (split from backtest-charts.jsx).
   누적수익곡선·MAE/MFE 산점·언더워터·롤링지표·누적거래 — 거래 순서/시간 축 기반 차트.
   chart.jsx 의 디자인 언어(chart-wrap·chart-grid-line·chart-axis-text·Mini·LegendDot)를 따른다.
*/
import { LegendDot, Mini, MetricHelpStrip } from "./chart.jsx";
import {
  useState_btc, useRef_btc, useMemo_btc, useEffect_btc,
  _btMoneyTick, _btDateLabel, _btDateLabelY, _btAxisTicks,
  _btReducedMotion, _BtChartEmpty,
} from "./bt-chart-utils.jsx";
import { ChartFrame } from "./chart-frame.jsx";

function _btEquityWithEvidence(Chart, describe) {
  return function EvidenceChart(props) {
    const evidence = describe(props);
    return <ChartFrame {...evidence}><Chart {...props} /></ChartFrame>;
  };
}

/* ① 누적수익곡선 + 일별손익 — analysis.equity {daily[], cumulative[], drawdown[]}.
   일별손익은 막대(이익 teal 위 / 손실 red 아래, 좌축 원), 누적수익은 라인(amber, 우축 원).
   chart.jsx BacktestDetailChart 의 듀얼축 패턴을 분석 응답 필드명(date/pnl, date/cum_profit)에 맞춰 재현. */
function _BtEquityChartContent({ equity, onBrush, brushActive, onBrushClear }) {
  const daily = (equity && equity.daily) || [];
  const cumulative = (equity && equity.cumulative) || [];
  const [hover, setHover] = useState_btc(null);
  // 가시 인덱스 창 [i0, i1] (휠 줌/드래그 팬). null 이면 전체.
  const [view, setView] = useState_btc(null);
  // 드래그 상태: {mode:"pan"|"brush", startPx, startView|startIdx, curIdx}.
  const dragRef = useRef_btc(null);
  const [brushSel, setBrushSel] = useState_btc(null);  // {a, b} 인덱스(표시용).
  const svgRef = useRef_btc(null);

  const W = 880, H = 320;
  const padL = 58, padR = 62, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const total = daily.length;
  // 데이터가 바뀌면 뷰 리셋.
  useEffect_btc(() => { setView(null); setBrushSel(null); }, [total, equity]);

  const v0 = view ? Math.max(0, view[0]) : 0;
  const v1 = view ? Math.min(total - 1, view[1]) : total - 1;
  const n = total > 0 ? (v1 - v0 + 1) : 0;
  const vDaily = total > 0 ? daily.slice(v0, v1 + 1) : [];
  const vCum = total > 0 ? cumulative.slice(v0, v1 + 1) : [];

  // 막대 폭/간격(가시 거래일 균등 배치).
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, Math.min(22, slot * 0.7));
  const xCenter = (i) => padL + slot * (i + 0.5);
  // 화면 px → 가시 인덱스(0..n-1) 및 전역 인덱스.
  const pxToLocal = (px) => Math.floor((px - padL) / slot);
  const localToGlobal = (i) => v0 + i;

  // 일별손익(막대) 스케일 — 0 포함(가시 구간 기준).
  const pnlVals = vDaily.map(d => d.pnl || 0);
  const pnlMax = Math.max(0, ...pnlVals);
  const pnlMin = Math.min(0, ...pnlVals);
  const pnlRange = (pnlMax - pnlMin) || 1;
  const yPnl = (v) => padT + innerH - ((v - pnlMin) / pnlRange) * innerH;
  const zeroY = yPnl(0);

  // 누적수익(라인) 스케일 — 가시 구간 자체 min/max(0 포함), 우축.
  const cumVals = vCum.map(c => c.cum_profit || 0);
  const cumMax = Math.max(0, ...cumVals);
  const cumMin = Math.min(0, ...cumVals);
  const cumRange = (cumMax - cumMin) || 1;
  const yCum = (v) => padT + innerH - ((v - cumMin) / cumRange) * innerH;

  const cumPath = useMemo_btc(() => {
    if (vCum.length < 2) return "";
    return vCum.map((c, i) =>
      `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yCum(c.cum_profit || 0).toFixed(1)}`
    ).join(" ");
  }, [vCum, n, cumMin, cumRange]);

  // 드로우인 길이(첫 로드 reveal). path 총길이 추정 — viewBox 폭 기준 근사.
  const cumLen = useMemo_btc(() => Math.max(1, innerW * 1.4), [innerW]);

  // X 눈금: 최대 8개 균등(가시 구간).
  const xTickIdx = useMemo_btc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const _localPx = (e) => {
    if (!svgRef.current) return null;
    const rect = svgRef.current.getBoundingClientRect();
    return (e.clientX - rect.left) * (W / rect.width);
  };

  const onMove = (e) => {
    if (!n) return;
    const px = _localPx(e);
    if (px == null) return;
    const i = pxToLocal(px);
    // 드래그 진행 중.
    const drag = dragRef.current;
    if (drag) {
      if (drag.mode === "brush") {
        const ci = Math.max(0, Math.min(n - 1, i));
        setBrushSel({ a: drag.startIdx, b: ci });
      } else if (drag.mode === "pan") {
        const deltaIdx = Math.round((drag.startPx - px) / slot);
        const span = drag.startView[1] - drag.startView[0];
        let nv0 = drag.startView[0] + deltaIdx;
        nv0 = Math.max(0, Math.min(total - 1 - span, nv0));
        setView([nv0, nv0 + span]);
      }
      return;
    }
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  const onDown = (e) => {
    if (!n) return;
    const px = _localPx(e);
    if (px == null) return;
    const i = Math.max(0, Math.min(n - 1, pxToLocal(px)));
    if (e.shiftKey) {
      dragRef.current = { mode: "brush", startIdx: i };
      setBrushSel({ a: i, b: i });
    } else {
      dragRef.current = { mode: "pan", startPx: px, startView: [v0, v1] };
    }
  };

  const onUp = () => {
    const drag = dragRef.current;
    dragRef.current = null;
    if (drag && drag.mode === "brush" && brushSel && onBrush) {
      const a = Math.min(brushSel.a, brushSel.b), b = Math.max(brushSel.a, brushSel.b);
      const gA = localToGlobal(a), gB = localToGlobal(b);
      const dA = daily[gA] && daily[gA].date, dB = daily[gB] && daily[gB].date;
      if (dA && dB) {
        // 일 경계를 매수시간(YYYYMMDDHHMMSS)으로 확장: 시작일 00:00:00 ~ 종료일 23:59:59.
        onBrush(dA * 1000000, dB * 1000000 + 235959);
      }
    }
  };

  const onWheel = (e) => {
    if (!n || total <= 1) return;
    e.preventDefault();
    const px = _localPx(e);
    if (px == null) return;
    const center = localToGlobal(Math.max(0, Math.min(n - 1, pxToLocal(px))));
    const span = v1 - v0;
    const factor = e.deltaY < 0 ? 0.8 : 1.25;   // 휠 업=줌인.
    let newSpan = Math.round(span * factor);
    newSpan = Math.max(2, Math.min(total - 1, newSpan));
    let nv0 = Math.round(center - newSpan * (center - v0) / Math.max(1, span));
    nv0 = Math.max(0, Math.min(total - 1 - newSpan, nv0));
    if (newSpan >= total - 1) { setView(null); }
    else { setView([nv0, nv0 + newSpan]); }
    setHover(null);
  };
  const applyBrush = (selection) => {
    if (!selection || !onBrush) return;
    const a = Math.min(selection.a, selection.b), b = Math.max(selection.a, selection.b);
    const dA = daily[localToGlobal(a)] && daily[localToGlobal(a)].date;
    const dB = daily[localToGlobal(b)] && daily[localToGlobal(b)].date;
    if (dA != null && dB != null) onBrush(dA * 1000000, dB * 1000000 + 235959);
  };
  const onKeyDown = (event) => {
    if (!n) return;
    if (event.key === "Escape") {
      setBrushSel(null);
      if (onBrushClear) onBrushClear();
      return;
    }
    if (event.key === "Enter" && brushSel) {
      event.preventDefault();
      applyBrush(brushSel);
      return;
    }
    const delta = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (!delta) return;
    event.preventDefault();
    const current = hover == null ? 0 : hover;
    const next = Math.max(0, Math.min(n - 1, current + delta));
    setHover(next);
    if (event.shiftKey) setBrushSel(previous => previous ? { ...previous, b: next } : { a: current, b: next });
  };

  const last = cumulative.length ? cumulative[cumulative.length - 1].cum_profit : null;
  const peakCum = cumulative.length ? Math.max(...cumulative.map(c => c.cum_profit || 0)) : null;
  const zoomed = view != null;

  // 브러시 밴드 px 좌표.
  const brushBand = (brushSel && brushSel.a != null) ? (() => {
    const a = Math.min(brushSel.a, brushSel.b), b = Math.max(brushSel.a, brushSel.b);
    const x0 = xCenter(a) - slot / 2, x1 = xCenter(b) + slot / 2;
    return { x: Math.max(padL, x0), w: Math.min(W - padR, x1) - Math.max(padL, x0) };
  })() : null;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          누적수익곡선 · 일별손익
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="일이익 ₩" />
          <LegendDot color="var(--red)" label="일손실 ₩" />
          <LegendDot color="var(--amber)" label="누적수익 ₩" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "휠 = 시간축 줌 · 드래그 = 팬",
          "Shift+드래그 = 구간 선택 → 구간 분석",
          zoomed ? "줌 상태 — 더블클릭으로 전체 복귀" : "크로스헤어로 일별 값 확인",
        ]} />
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap", alignItems: "center" }}>
          <Mini label="최종 누적" value={last != null ? fmtMoney(last) : "—"}
                color={last != null && last > 0 ? "var(--teal)" : last != null && last < 0 ? "var(--red)" : undefined} />
          <Mini label="누적 고점" value={peakCum != null ? fmtMoney(peakCum) : "—"} />
          <Mini label="거래일수" value={total > 0 ? String(total) : "—"} />
          {zoomed && (
            <button className="btn ghost sm" onClick={() => { setView(null); setBrushSel(null); }}>
              ⤢ 전체 보기
            </button>
          )}
          {brushActive && (
            <button className="btn sm" onClick={() => { setBrushSel(null); onBrushClear && onBrushClear(); }}
                    style={{ borderColor: "var(--teal-dim)", color: "var(--teal)" }}>
              ↩ 전체로 복귀
            </button>
          )}
        </div>
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" tabIndex="0" role="application"
               aria-label="누적수익곡선. 화살표 키로 일자를 탐색하고 Shift+화살표로 구간을 선택한 뒤 Enter로 구간 분석을 적용합니다."
               style={{ cursor: dragRef.current ? (dragRef.current.mode === "brush" ? "crosshair" : "grabbing") : "crosshair" }}
               onMouseMove={onMove} onMouseLeave={() => { setHover(null); }}
               onMouseDown={onDown} onMouseUp={onUp} onWheel={onWheel} onKeyDown={onKeyDown}
               onDoubleClick={() => { setView(null); setBrushSel(null); }}>
            {/* 0 손익분기선 */}
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                  stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            {/* 좌축(일별손익 max/min) */}
            <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMax) + 3} textAnchor="end" fill="var(--teal)">{_btMoneyTick(pnlMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMin) + 3} textAnchor="end" fill="var(--red)">{_btMoneyTick(pnlMin)}</text>
            {/* 좌축 중간 눈금(가로 점선 + 라벨) — 스케일 가독성. 0·max·min 과 겹치면 생략. */}
            {_btAxisTicks(pnlMin, pnlMax, 5).map((tv, i) => (
              (Math.abs(tv) < 1e-9 || Math.abs(tv - pnlMax) < 1e-9 || Math.abs(tv - pnlMin) < 1e-9) ? null : (
                <g key={`eyl${i}`}>
                  <line x1={padL} x2={W - padR} y1={yPnl(tv)} y2={yPnl(tv)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                  <text className="chart-axis-text" x={padL - 8} y={yPnl(tv) + 3} textAnchor="end" fill="var(--ink-3)">{_btMoneyTick(tv)}</text>
                </g>
              )
            ))}
            {/* 우축(누적 max/min) */}
            <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMax) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(cumMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMin) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(cumMin)}</text>
            {/* 우축 중간 눈금 라벨(누적) — max·min 과 겹치면 생략. */}
            {_btAxisTicks(cumMin, cumMax, 5).map((tv, i) => (
              (Math.abs(tv - cumMax) < 1e-9 || Math.abs(tv - cumMin) < 1e-9) ? null : (
                <text key={`eyr${i}`} className="chart-axis-text" x={W - padR + 6} y={yCum(tv) + 3} textAnchor="start" fill="var(--ink-3)">{_btMoneyTick(tv)}</text>
              )
            ))}
            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 브러시 선택 밴드 */}
            {brushBand && brushBand.w > 0 && (
              <rect className="bt-brush-band" x={brushBand.x} y={padT} width={brushBand.w} height={innerH} />
            )}
            {/* 일별손익 막대 */}
            {vDaily.map((d, i) => {
              const v = d.pnl || 0;
              const y0 = zeroY, y1 = yPnl(v);
              const top = Math.min(y0, y1), h = Math.max(1, Math.abs(y1 - y0));
              return <rect key={`b${i}`} x={xCenter(i) - barW / 2} y={top} width={barW} height={h}
                           fill={v >= 0 ? "var(--teal)" : "var(--red)"} opacity={hover === i ? 1 : 0.55} />;
            })}
            {/* 누적수익 라인(첫 로드 드로우인) */}
            {vCum.length > 1 && (
              <path d={cumPath} fill="none" stroke="var(--amber)" strokeWidth="2"
                    className={(!zoomed && !_btReducedMotion()) ? "bt-draw-in" : ""}
                    style={(!zoomed && !_btReducedMotion())
                      ? { strokeDasharray: cumLen, strokeDashoffset: cumLen }
                      : undefined} />
            )}
            {/* X 라벨 — 연도 경계/첫 틱은 YYYY-MM-DD, 그 외 MM/DD. */}
            {xTickIdx.map((i, k) => (
              <text key={`x${i}`} className="chart-axis-text" x={xCenter(i)} y={H - 10} textAnchor="middle">
                {vDaily[i] ? _btDateLabelY(vDaily[i].date, k > 0 && vDaily[xTickIdx[k - 1]] ? vDaily[xTickIdx[k - 1]].date : null) : ""}
              </text>
            ))}
            {/* 크로스헤어(수직선) */}
            {hover != null && vDaily[hover] && (
              <line x1={xCenter(hover)} x2={xCenter(hover)} y1={padT} y2={padT + innerH}
                    stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>

          {hover != null && vDaily[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 170, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 }}>
                {_btDateLabel(vDaily[hover].date)}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>일손익</span>
                <span className={vDaily[hover].pnl > 0 ? "num-pos" : vDaily[hover].pnl < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>{fmtMoney(vDaily[hover].pnl)}</span>
                <span style={{ color: "var(--ink-2)" }}>누적</span>
                <span style={{ textAlign: "right" }}>
                  {vCum[hover] ? fmtMoney(vCum[hover].cum_profit) : "—"}
                </span>
              </div>
            </div>
          )}

          {total === 0 && <_BtChartEmpty message="거래가 누적되면 누적수익곡선이 표시됩니다" />}
        </div>
      </div>
    </div>
  );
}

/* ⑤ MAE/MFE 산점도 — analysis.mae_mfe [{mae,mfe,pnl_pct,hold_sec,code}].
   x=R_MAE(매수후 최저, ≤0), y=R_MFE(매수후 최고, ≥0). 색=손익 양/음. 사분면 가이드+호버. */
function _BtMaeMfeScatterContent({ points }) {
  const pts = Array.isArray(points) ? points : [];
  const [hover, setHover] = useState_btc(null);

  const W = 880, H = 320;
  const padL = 52, padR = 24, padT = 18, padB = 36;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // x(MAE)는 보통 ≤0, y(MFE)는 ≥0. 0 을 항상 포함하도록 도메인 확장.
  const maes = pts.map(p => p.mae);
  const mfes = pts.map(p => p.mfe);
  const xMin = Math.min(0, ...maes, 0), xMax = Math.max(0, ...maes, 0);
  const yMin = Math.min(0, ...mfes, 0), yMax = Math.max(0, ...mfes, 0);
  const xRange = (xMax - xMin) || 1, yRange = (yMax - yMin) || 1;
  const sx = (v) => padL + ((v - xMin) / xRange) * innerW;
  const sy = (v) => padT + innerH - ((v - yMin) / yRange) * innerH;
  const x0 = sx(0), y0 = sy(0);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          MAE / MFE 산점도
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="이익 거래" />
          <LegendDot color="var(--red)" label="손실 거래" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "x = R_MAE(매수후 최저수익률, %)",
          "y = R_MFE(매수후 최고수익률, %)",
          "좌상=잠재이익 큼/낙폭 큼 · 점색=실현손익",
        ]} />
        <div className="chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseLeave={() => setHover(null)}>
            {/* 사분면 가이드(0축) */}
            <line x1={x0} x2={x0} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.3)" strokeWidth="1" strokeDasharray="3 3" />
            <line x1={padL} x2={W - padR} y1={y0} y2={y0} stroke="rgba(255,255,255,0.3)" strokeWidth="1" strokeDasharray="3 3" />
            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 축 라벨 */}
            <text className="chart-axis-text" x={padL} y={H - 10} textAnchor="start">{xMin.toFixed(1)}%</text>
            <text className="chart-axis-text" x={W - padR} y={H - 10} textAnchor="end">{xMax.toFixed(1)}%</text>
            <text className="chart-axis-text" x={padL - 8} y={sy(yMax) + 3} textAnchor="end">{yMax.toFixed(1)}%</text>
            <text className="chart-axis-text" x={padL - 8} y={sy(yMin) + 3} textAnchor="end">{yMin.toFixed(1)}%</text>
            <text className="bt-quadrant-label" x={x0 + 6} y={padT + 12}>MFE↑</text>
            <text className="bt-quadrant-label" x={padL + 4} y={y0 - 6}>MAE↓</text>
            {/* 점 */}
            {pts.map((p, i) => (
              <circle key={i} className="bt-scatter-pt"
                      cx={sx(p.mae)} cy={sy(p.mfe)} r={hover === i ? 5 : 3.2}
                      fill={p.pnl_pct >= 0 ? "var(--teal)" : "var(--red)"}
                      opacity={hover == null ? 0.62 : (hover === i ? 1 : 0.28)}
                      onMouseEnter={() => setHover(i)} />
            ))}
          </svg>

          {hover != null && pts[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 180, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {pts[hover].code || "(미상)"}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>MAE</span>
                <span style={{ textAlign: "right", color: "var(--red)" }}>{pts[hover].mae.toFixed(2)}%</span>
                <span style={{ color: "var(--ink-2)" }}>MFE</span>
                <span style={{ textAlign: "right", color: "var(--teal)" }}>{pts[hover].mfe.toFixed(2)}%</span>
                <span style={{ color: "var(--ink-2)" }}>실현</span>
                <span className={pts[hover].pnl_pct > 0 ? "num-pos" : pts[hover].pnl_pct < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>{pts[hover].pnl_pct.toFixed(2)}%</span>
              </div>
            </div>
          )}

          {pts.length === 0 && <_BtChartEmpty message="MAE/MFE 데이터가 없습니다 (R_MAE·R_MFE 결측)" />}
        </div>
      </div>
    </div>
  );
}

/* ④ 언더워터 곡선 — analysis.underwater {series:[{date,drawdown}], max_drawdown}.
   고점 대비 반납액(원)을 0 아래로 채워 그린다(red 영역). 최대낙폭 구간(start~trough~recovery) 표기. */
function _BtUnderwaterChartContent({ underwater }) {
  const series = (underwater && underwater.series) || [];
  const maxDd = underwater && underwater.max_drawdown;
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);

  const W = 880, H = 320;
  const padL = 58, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = series.length;
  const x = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;

  // drawdown 은 항상 >=0(반납액). 위가 0, 아래로 갈수록 큰 낙폭.
  const ddVals = series.map(d => d.drawdown || 0);
  const ddMax = Math.max(1, ...ddVals);
  const y = (v) => padT + (v / ddMax) * innerH;  // v=0 → padT(상단), v=ddMax → 하단.

  const areaPath = useMemo_btc(() => {
    if (n < 2) return "";
    const top = series.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.drawdown || 0).toFixed(1)}`).join(" ");
    return `${top} L ${x(n - 1).toFixed(1)} ${padT.toFixed(1)} L ${x(0).toFixed(1)} ${padT.toFixed(1)} Z`;
  }, [series, n, ddMax]);

  const linePath = useMemo_btc(() => {
    if (n < 2) return "";
    return series.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.drawdown || 0).toFixed(1)}`).join(" ");
  }, [series, n, ddMax]);

  const xTickIdx = useMemo_btc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
    const i = Math.round(frac * (n - 1));
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--red)" }}></span>
          언더워터 — Drawdown
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>고점 대비 반납액(원)</span>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="최대낙폭" value={maxDd ? fmtMoney(maxDd.drawdown) : "—"} color={maxDd ? "var(--red)" : undefined} />
          {maxDd && (
            <Mini label="낙폭 구간"
                  value={`${_btDateLabel(maxDd.start_date)}~${_btDateLabel(maxDd.trough_date)}`}
                  sub={maxDd.recovery_date ? `회복 ${_btDateLabel(maxDd.recovery_date)}` : "미회복"} />
          )}
        </div>
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            <defs>
              <linearGradient id="bt-uw-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff6b6b" stopOpacity="0" />
                <stop offset="100%" stopColor="#ff6b6b" stopOpacity="0.42" />
              </linearGradient>
            </defs>
            {/* 0 기준선(상단) */}
            <line x1={padL} x2={W - padR} y1={padT} y2={padT} stroke="var(--line-2)" strokeWidth="1" />
            <text className="chart-axis-text" x={padL - 8} y={padT + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            <text className="chart-axis-text" x={padL - 8} y={padT + innerH + 3} textAnchor="end" fill="var(--red)">
              −{_btMoneyTick(ddMax)}
            </text>
            {/* y 중간 눈금(반납액) — 가로 점선 + 라벨. 0·ddMax 와 겹치면 생략. */}
            {_btAxisTicks(0, ddMax, 5).map((tv, i) => (
              (Math.abs(tv) < 1e-9 || Math.abs(tv - ddMax) < 1e-9) ? null : (
                <g key={`uyl${i}`}>
                  <line x1={padL} x2={W - padR} y1={y(tv)} y2={y(tv)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                  <text className="chart-axis-text" x={padL - 8} y={y(tv) + 3} textAnchor="end" fill="var(--ink-3)">−{_btMoneyTick(tv)}</text>
                </g>
              )
            ))}
            {/* Frame */}
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 언더워터 영역 + 라인 */}
            {n > 1 && (
              <>
                <path d={areaPath} fill="url(#bt-uw-grad)" />
                <path d={linePath} fill="none" stroke="var(--red)" strokeWidth="1.4" opacity="0.85" />
              </>
            )}
            {/* X 라벨 — 연도 경계/첫 틱은 YYYY-MM-DD, 그 외 MM/DD. */}
            {xTickIdx.map((i, k) => (
              <text key={`ux${i}`} className="chart-axis-text" x={x(i)} y={H - 10} textAnchor="middle">
                {series[i] ? _btDateLabelY(series[i].date, k > 0 && series[xTickIdx[k - 1]] ? series[xTickIdx[k - 1]].date : null) : ""}
              </text>
            ))}
            {/* Hover */}
            {hover != null && series[hover] && (
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH}
                    stroke="rgba(255,255,255,0.14)" strokeWidth="1" />
            )}
          </svg>

          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 160, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>{_btDateLabel(series[hover].date)}</span>
                <span style={{ textAlign: "right", color: "var(--red)" }}>−{_btMoneyTick(series[hover].drawdown)}</span>
              </div>
            </div>
          )}

          {n === 0 && <_BtChartEmpty message="거래가 누적되면 언더워터 곡선이 표시됩니다" />}
        </div>
      </div>
    </div>
  );
}

/* ⑪ 롤링 지표 라인(트랙 D) — analysis.rolling {window, series:[{index,sell_time,win_rate,payoff,avg_pnl_pct}]}.
   거래 순서 축으로 롤링 승률(좌축 %)·payoff(우축 배)를 듀얼축 라인으로 겹쳐 그린다. */
function _BtRollingChartContent({ rolling }) {
  const series = (rolling && rolling.series) || [];
  const window = (rolling && rolling.window) || 20;
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);

  const W = 880, H = 320;
  const padL = 48, padR = 52, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = series.length;
  const x = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;

  // 좌축: 승률 0~100%.
  const yWin = (v) => padT + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH;
  // 우축: payoff 0~max(2 하한).
  const payoffMax = Math.max(2, ...series.map(s => s.payoff || 0));
  const yPay = (v) => padT + innerH - (Math.max(0, v) / payoffMax) * innerH;

  const winPath = useMemo_btc(() => n < 2 ? "" :
    series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yWin(s.win_rate || 0).toFixed(1)}`).join(" "),
    [series, n]);
  const payPath = useMemo_btc(() => n < 2 ? "" :
    series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yPay(s.payoff || 0).toFixed(1)}`).join(" "),
    [series, n, payoffMax]);

  const xTickIdx = useMemo_btc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
    const i = Math.round(frac * (n - 1));
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          롤링 지표 — 승률 · Payoff
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="롤링 승률 %" />
          <LegendDot color="var(--amber)" label="롤링 payoff 배" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          `${window}거래 이동창 기준`,
          "좌축 = 승률(%) · 우축 = payoff(평균이익/평균손실)",
          "구간별 전략 안정성 추이 진단",
        ]} />
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            {/* 50% 기준선(좌축) */}
            <line x1={padL} x2={W - padR} y1={yWin(50)} y2={yWin(50)} stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={yWin(50) + 3} textAnchor="end" fill="var(--ink-2)">50%</text>
            {/* 좌축 0/100 */}
            <text className="chart-axis-text" x={padL - 8} y={yWin(100) + 3} textAnchor="end" fill="var(--teal)">100%</text>
            <text className="chart-axis-text" x={padL - 8} y={yWin(0) + 3} textAnchor="end" fill="var(--ink-2)">0%</text>
            {/* 우축 payoff max */}
            <text className="chart-axis-text" x={W - padR + 6} y={yPay(payoffMax) + 3} textAnchor="start" fill="var(--amber)">{payoffMax.toFixed(1)}×</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yPay(1) + 3} textAnchor="start" fill="var(--ink-3)">1×</text>
            {/* payoff=1 손익분기선 */}
            <line x1={padL} x2={W - padR} y1={yPay(1)} y2={yPay(1)} stroke="rgba(240,179,90,0.2)" strokeWidth="1" strokeDasharray="4 4" />
            {/* Frame */}
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 라인 */}
            {n > 1 && <path d={winPath} fill="none" stroke="var(--teal)" strokeWidth="2" />}
            {n > 1 && <path d={payPath} fill="none" stroke="var(--amber)" strokeWidth="1.6" strokeDasharray="5 3" opacity="0.9" />}
            {/* X 라벨(거래 인덱스) */}
            {xTickIdx.map((i) => (
              <text key={`rx${i}`} className="chart-axis-text" x={x(i)} y={H - 10} textAnchor="middle">
                {series[i] ? `#${series[i].index + 1}` : ""}
              </text>
            ))}
            {hover != null && series[hover] && (
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>

          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 160, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>거래 #{series[hover].index + 1}</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>승률</span>
                <span style={{ textAlign: "right", color: "var(--teal)" }}>{fmtPct(series[hover].win_rate)}</span>
                <span style={{ color: "var(--ink-2)" }}>payoff</span>
                <span style={{ textAlign: "right", color: "var(--amber)" }}>{(series[hover].payoff || 0).toFixed(2)}×</span>
                <span style={{ color: "var(--ink-2)" }}>평균손익</span>
                <span className={series[hover].avg_pnl_pct > 0 ? "num-pos" : series[hover].avg_pnl_pct < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>{series[hover].avg_pnl_pct.toFixed(2)}%</span>
              </div>
            </div>
          )}

          {n === 0 && <_BtChartEmpty message={`거래가 ${window}건 이상 누적되면 롤링 지표가 표시됩니다`} />}
        </div>
      </div>
    </div>
  );
}

/* ⑬ 누적 거래 듀얼축(트랙 D) — analysis.cumulative_trades {series:[{index,sell_time,cum_trades,cum_profit_krw}]}.
   거래 순서 축으로 누적 거래수(좌축, 면적)와 누적 실현손익(우축, 라인)을 겹쳐 그린다. */
function _BtCumulativeTradesChartContent({ data }) {
  const series = (data && data.series) || [];
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);

  const W = 880, H = 320;
  const padL = 52, padR = 60, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const n = series.length;
  const x = (i) => n > 1 ? padL + (i / (n - 1)) * innerW : padL + innerW / 2;

  // 좌축: 누적 거래수 0~max.
  const maxTrades = Math.max(1, ...series.map(s => s.cum_trades || 0));
  const yTrades = (v) => padT + innerH - (v / maxTrades) * innerH;
  // 우축: 누적 손익(0 포함).
  const profits = series.map(s => s.cum_profit_krw || 0);
  const pMax = Math.max(0, ...profits);
  const pMin = Math.min(0, ...profits);
  const pRange = (pMax - pMin) || 1;
  const yProfit = (v) => padT + innerH - ((v - pMin) / pRange) * innerH;

  const tradesArea = useMemo_btc(() => {
    if (n < 2) return "";
    const top = series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yTrades(s.cum_trades || 0).toFixed(1)}`).join(" ");
    return `${top} L ${x(n - 1).toFixed(1)} ${(padT + innerH).toFixed(1)} L ${x(0).toFixed(1)} ${(padT + innerH).toFixed(1)} Z`;
  }, [series, n, maxTrades]);
  const profitPath = useMemo_btc(() => n < 2 ? "" :
    series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yProfit(s.cum_profit_krw || 0).toFixed(1)}`).join(" "),
    [series, n, pMin, pRange]);

  const xTickIdx = useMemo_btc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
    const i = Math.round(frac * (n - 1));
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  const profitZeroY = yProfit(0);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          누적 거래 · 누적 손익
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <LegendDot color="var(--blue)" label="누적 거래수" />
          <LegendDot color="var(--amber)" label="누적 손익 ₩" />
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "x축 = 거래 순서(체결 순)",
          "좌축 = 누적 거래수 · 우축 = 누적 실현손익",
          "체결 빈도와 자본 증가를 한 화면에서 비교",
        ]} />
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            <defs>
              <linearGradient id="bt-ct-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#5b8def" stopOpacity="0.34" />
                <stop offset="100%" stopColor="#5b8def" stopOpacity="0.02" />
              </linearGradient>
            </defs>
            {/* 손익 0 기준선(우축) */}
            <line x1={padL} x2={W - padR} y1={profitZeroY} y2={profitZeroY} stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={W - padR + 6} y={profitZeroY + 3} textAnchor="start" fill="var(--ink-2)">0</text>
            {/* 좌축(누적 거래수 max) */}
            <text className="chart-axis-text" x={padL - 8} y={yTrades(maxTrades) + 3} textAnchor="end" fill="var(--blue)">{maxTrades}</text>
            <text className="chart-axis-text" x={padL - 8} y={yTrades(0) + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            {/* 우축(누적 손익 max/min) */}
            <text className="chart-axis-text" x={W - padR + 6} y={yProfit(pMax) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(pMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yProfit(pMin) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(pMin)}</text>
            {/* 우축 중간 눈금(누적 손익) — max·min·0 과 겹치면 생략. */}
            {_btAxisTicks(pMin, pMax, 5).map((tv, i) => (
              (Math.abs(tv - pMax) < 1e-9 || Math.abs(tv - pMin) < 1e-9 || Math.abs(tv) < 1e-9) ? null : (
                <text key={`cyr${i}`} className="chart-axis-text" x={W - padR + 6} y={yProfit(tv) + 3} textAnchor="start" fill="var(--ink-3)">{_btMoneyTick(tv)}</text>
              )
            ))}
            {/* Frame */}
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 누적 거래수 면적 + 누적 손익 라인 */}
            {n > 1 && <path d={tradesArea} fill="url(#bt-ct-grad)" stroke="var(--blue)" strokeWidth="1.2" opacity="0.85" />}
            {n > 1 && <path d={profitPath} fill="none" stroke="var(--amber)" strokeWidth="2" />}
            {/* X 라벨 */}
            {xTickIdx.map((i) => (
              <text key={`cx${i}`} className="chart-axis-text" x={x(i)} y={H - 10} textAnchor="middle">
                {series[i] ? `#${series[i].index}` : ""}
              </text>
            ))}
            {hover != null && series[hover] && (
              <line x1={x(hover)} x2={x(hover)} y1={padT} y2={padT + innerH} stroke="rgba(255,255,255,0.22)" strokeWidth="1" />
            )}
          </svg>

          {hover != null && series[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 170, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>거래 #{series[hover].index}</div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>누적 거래</span>
                <span style={{ textAlign: "right", color: "var(--blue)" }}>{series[hover].cum_trades}건</span>
                <span style={{ color: "var(--ink-2)" }}>누적 손익</span>
                <span className={series[hover].cum_profit_krw > 0 ? "num-pos" : series[hover].cum_profit_krw < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>{fmtMoney(series[hover].cum_profit_krw)}</span>
              </div>
            </div>
          )}

          {n === 0 && <_BtChartEmpty message="거래가 누적되면 누적 거래·손익 곡선이 표시됩니다" />}
        </div>
      </div>
    </div>
  );
}

const BtEquityChart = _btEquityWithEvidence(_BtEquityChartContent, ({ equity }) => ({
  title: "누적수익곡선 · 일별손익", unit: "일별·누적 손익 (원)",
  period: "일자별", sampleCount: Array.isArray(equity && equity.daily) ? equity.daily.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.equity.daily",
  rows: equity && equity.daily, columns: ["date", "pnl"], rowKey: "date",
}));
const BtMaeMfeScatter = _btEquityWithEvidence(_BtMaeMfeScatterContent, ({ points }) => ({
  title: "MAE / MFE 산점도", unit: "수익률 (%)", period: "거래별",
  sampleCount: Array.isArray(points) ? points.length : 0, freshness: "백테스트 분석 응답",
  threshold: "손익분기 0%", source: "analysis.mae_mfe", rows: points,
  columns: ["code", "mae", "mfe", "pnl_pct"], rowKey: "code",
}));
const BtUnderwaterChart = _btEquityWithEvidence(_BtUnderwaterChartContent, ({ underwater }) => ({
  title: "언더워터 — Drawdown", unit: "고점 대비 반납액 (원)", period: "일자별",
  sampleCount: Array.isArray(underwater && underwater.series) ? underwater.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "고점 대비 0원", source: "analysis.underwater.series",
  rows: underwater && underwater.series, columns: ["date", "drawdown"], rowKey: "date",
}));
const BtRollingChart = _btEquityWithEvidence(_BtRollingChartContent, ({ rolling }) => ({
  title: "롤링 지표 — 승률 · Payoff", unit: "승률 (%) · payoff (배)", period: "거래 순서",
  sampleCount: Array.isArray(rolling && rolling.series) ? rolling.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "승률 50% · payoff 1배", source: "analysis.rolling.series",
  rows: rolling && rolling.series, columns: ["index", "sell_time", "win_rate", "payoff", "avg_pnl_pct"], rowKey: "index",
}));
const BtCumulativeTradesChart = _btEquityWithEvidence(_BtCumulativeTradesChartContent, ({ data }) => ({
  title: "누적 거래 · 누적 손익", unit: "거래 수 · 누적 손익 (원)", period: "거래 순서",
  sampleCount: Array.isArray(data && data.series) ? data.series.length : 0,
  freshness: "백테스트 분석 응답", threshold: "손익분기 0원", source: "analysis.cumulative_trades.series",
  rows: data && data.series, columns: ["index", "sell_time", "cum_trades", "cum_profit_krw"], rowKey: "index",
}));

export {
  BtEquityChart, BtMaeMfeScatter, BtUnderwaterChart, BtRollingChart, BtCumulativeTradesChart,
};
