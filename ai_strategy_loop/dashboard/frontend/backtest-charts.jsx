/* Backtest workbench analysis charts — PR2 (split from backtest.jsx for the 800-line cap).
   순수 SVG 차트(외부 라이브러리 금지)로 /bt/result 의 analysis 묶음을 시각화한다.
   chart.jsx 의 디자인 언어(chart-wrap·chart-grid-line·chart-axis-text·Mini·LegendDot)를 그대로 따른다.

   window 전역으로 공유: index.html 에서 backtest.jsx 보다 먼저 로드된다.
   소비 컴포넌트(export):
     - BtEquityChart      : analysis.equity   {daily, cumulative, drawdown}
     - BtDistributionChart: analysis.distribution.pnl_histogram (손익 % 히스토그램)
     - BtHeatmap          : analysis.heatmap.cells (요일×30분 슬롯)
     - BtUnderwaterChart  : analysis.underwater {series, max_drawdown}
*/
const {
  useState: useState_btc, useRef: useRef_btc, useMemo: useMemo_btc,
  useEffect: useEffect_btc, useCallback: useCallback_btc,
} = React;

// 무예외 fetch 헬퍼(_btFetchJson)는 backtest.jsx 에 정의되어 window 전역으로 공유된다.
//   BtResultArea 의 load()는 렌더 시점에 호출되므로(모듈 평가 시점 아님) 그때면 이미 정의돼 있다.

// 만/억 단위 축약(원). 그래프 축 라벨 가독성용.
function _btMoneyTick(v) {
  const a = Math.abs(v);
  if (a >= 1e8) return (v / 1e8).toFixed(1) + "억";
  if (a >= 1e4) return (v / 1e4).toFixed(0) + "만";
  return Math.round(v).toLocaleString("ko-KR");
}

// YYYYMMDD(int) → MM/DD 축약 라벨.
function _btDateLabel(d) {
  const s = String(d);
  if (s.length === 8) return s.slice(4, 6) + "/" + s.slice(6, 8);
  return s;
}

const _BT_WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"];

// prefers-reduced-motion 존중 — 모션 비활성 시 즉시 최종값.
function _btReducedMotion() {
  try {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch (e) { return false; }
}

// rAF 카운트업 훅 — target 으로 durMs 동안 부드럽게 증가(0.6s 기본). 모션 off 면 즉시.
function _useCountUp(target, durMs) {
  const [val, setVal] = useState_btc(typeof target === "number" ? target : 0);
  const fromRef = useRef_btc(0);
  const rafRef = useRef_btc(0);
  useEffect_btc(() => {
    const to = typeof target === "number" && isFinite(target) ? target : 0;
    if (_btReducedMotion()) { setVal(to); return; }
    const from = fromRef.current;
    const dur = durMs || 600;
    const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - p, 3);   // easeOutCubic.
      setVal(from + (to - from) * eased);
      if (p < 1) { rafRef.current = requestAnimationFrame(tick); }
      else { fromRef.current = to; }
    };
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, durMs]);
  return val;
}

// SVG 아크 게이지(승률·MDD) — 0~max 비율을 반원 호로. value/max 정규화.
function _BtArcGauge({ value, max, color, label, sub }) {
  const v = typeof value === "number" && isFinite(value) ? value : 0;
  const frac = Math.max(0, Math.min(1, max ? v / max : 0));
  const R = 22, CX = 26, CY = 26, sw = 6;
  const circ = Math.PI * R;   // 반원 둘레.
  const dash = circ * frac;
  // 반원 경로(좌→우, 위로 볼록).
  const arc = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;
  return (
    <div className="bt-gauge-wrap">
      <svg width="52" height="34" viewBox="0 0 52 34">
        <path d={arc} fill="none" stroke="var(--line-2)" strokeWidth={sw} strokeLinecap="round" />
        <path d={arc} fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
              strokeDasharray={`${dash.toFixed(1)} ${circ.toFixed(1)}`} />
      </svg>
      <div className="bt-gauge-num">
        <span className="summary-val" style={{ fontSize: 15, color }}>{label}</span>
        {sub && <span className="summary-sub">{sub}</span>}
      </div>
    </div>
  );
}

// 일별손익 미니 스파크라인(바). values=일별 pnl 배열.
function _BtSparkline({ values, w, h }) {
  const vals = Array.isArray(values) ? values : [];
  const W = w || 120, H = h || 24;
  if (vals.length === 0) return <svg className="bt-spark" viewBox={`0 0 ${W} ${H}`} />;
  const maxAbs = Math.max(1, ...vals.map(v => Math.abs(v || 0)));
  const n = vals.length;
  const bw = Math.max(1, (W / n) * 0.8);
  const mid = H / 2;
  return (
    <svg className="bt-spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <line x1="0" x2={W} y1={mid} y2={mid} stroke="var(--line-1)" strokeWidth="0.5" />
      {vals.map((v, i) => {
        const val = v || 0;
        const bh = (Math.abs(val) / maxAbs) * (mid - 1);
        const x = (W / n) * (i + 0.5) - bw / 2;
        const y = val >= 0 ? mid - bh : mid;
        return <rect key={i} x={x} y={y} width={bw} height={Math.max(0.5, bh)}
                     fill={val >= 0 ? "var(--teal)" : "var(--red)"} opacity="0.8" />;
      })}
    </svg>
  );
}

// 차트 공용 빈 상태 오버레이.
function _BtChartEmpty({ message }) {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
      textAlign: "center", padding: "0 16px",
    }}>
      {message || "분석 데이터가 없습니다"}
    </div>
  );
}

/* ① 누적수익곡선 + 일별손익 — analysis.equity {daily[], cumulative[], drawdown[]}.
   일별손익은 막대(이익 teal 위 / 손실 red 아래, 좌축 원), 누적수익은 라인(amber, 우축 원).
   chart.jsx BacktestDetailChart 의 듀얼축 패턴을 분석 응답 필드명(date/pnl, date/cum_profit)에 맞춰 재현. */
function BtEquityChart({ equity, onBrush, brushActive, onBrushClear }) {
  const daily = (equity && equity.daily) || [];
  const cumulative = (equity && equity.cumulative) || [];
  const [hover, setHover] = useState_btc(null);
  // 가시 인덱스 창 [i0, i1] (휠 줌/드래그 팬). null 이면 전체.
  const [view, setView] = useState_btc(null);
  // 드래그 상태: {mode:"pan"|"brush", startPx, startView|startIdx, curIdx}.
  const dragRef = useRef_btc(null);
  const [brushSel, setBrushSel] = useState_btc(null);  // {a, b} 인덱스(표시용).
  const svgRef = useRef_btc(null);

  const W = 880, H = 300;
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
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               style={{ cursor: dragRef.current ? (dragRef.current.mode === "brush" ? "crosshair" : "grabbing") : "crosshair" }}
               onMouseMove={onMove} onMouseLeave={() => { setHover(null); }}
               onMouseDown={onDown} onMouseUp={onUp} onWheel={onWheel}
               onDoubleClick={() => { setView(null); setBrushSel(null); }}>
            {/* 0 손익분기선 */}
            <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                  stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
            <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end" fill="var(--ink-2)">0</text>
            {/* 좌축(일별손익 max/min) */}
            <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMax) + 3} textAnchor="end" fill="var(--teal)">{_btMoneyTick(pnlMax)}</text>
            <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMin) + 3} textAnchor="end" fill="var(--red)">{_btMoneyTick(pnlMin)}</text>
            {/* 우축(누적 max/min) */}
            <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMax) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(cumMax)}</text>
            <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMin) + 3} textAnchor="start" fill="var(--amber)">{_btMoneyTick(cumMin)}</text>
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
            {/* X 라벨 */}
            {xTickIdx.map((i) => (
              <text key={`x${i}`} className="chart-axis-text" x={xCenter(i)} y={H - 10} textAnchor="middle">
                {vDaily[i] ? _btDateLabel(vDaily[i].date) : ""}
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
function BtMaeMfeScatter({ points }) {
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

/* ② 손익 히스토그램 — analysis.distribution.pnl_histogram [{bin_start,bin_end,count,unit}].
   각 bin 을 막대로(손실 구간 red / 이익 구간 teal / 0 걸친 구간 amber), 0% 경계선 강조. */
function BtDistributionChart({ distribution }) {
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
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
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

/* ③ 요일×시간 히트맵 — analysis.heatmap.cells [{weekday,slot,slot_label,profit_krw,trades}].
   행=요일(월~금 우선, 토/일은 데이터 있을 때만), 열=30분 슬롯(09:00~15:30 범위).
   셀 색: 손익 부호·크기(red↔teal), hover 시 손익/거래수 툴팁. research-cell 패턴 차용. */
function BtHeatmap({ heatmap }) {
  const cells = (heatmap && heatmap.cells) || [];
  const [hover, setHover] = useState_btc(null);

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

  // 색 스케일 — 절대 손익 최대값 기준 정규화.
  const maxAbs = Math.max(1, ...cells.map(c => Math.abs(c.profit_krw || 0)));
  const cellColor = (c) => {
    if (!c) return "var(--bg-0)";
    const t = Math.min(1, Math.abs(c.profit_krw || 0) / maxAbs);
    if ((c.profit_krw || 0) >= 0) {
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

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          요일 × 시간대 히트맵
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>매수시각 기준 · 손익 합</span>
      </div>
      <div className="panel-bd">
        {cells.length === 0 ? (
          <div style={{ position: "relative", minHeight: 120 }}>
            <_BtChartEmpty message="거래가 누적되면 시간대 히트맵이 표시됩니다" />
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ borderCollapse: "separate", borderSpacing: 3, fontFamily: "var(--mono)" }}>
              <thead>
                <tr>
                  <th style={{ width: 30 }}></th>
                  {slots.map(s => (
                    <th key={s} style={{ fontSize: 9.5, color: "var(--ink-3)", fontWeight: 400, padding: "0 1px", whiteSpace: "nowrap" }}>
                      {slotLabel(s)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {weekdays.map(w => (
                  <tr key={w}>
                    <td style={{ fontSize: 11, color: "var(--ink-2)", textAlign: "center", paddingRight: 4 }}>
                      {_BT_WEEKDAYS[w]}
                    </td>
                    {slots.map(s => {
                      const c = cellMap[w + "_" + s];
                      const key = w + "_" + s;
                      return (
                        <td key={s}
                            onMouseEnter={() => c && setHover(key)}
                            onMouseLeave={() => setHover(null)}
                            title={c ? `${_BT_WEEKDAYS[w]} ${slotLabel(s)} · ${fmtMoney(c.profit_krw)} · ${c.trades}건` : ""}
                            style={{
                              width: 34, height: 26, borderRadius: 4,
                              background: cellColor(c),
                              border: hover === key ? "1px solid var(--ink-0)" : "1px solid var(--line-1)",
                              textAlign: "center", fontSize: 9.5,
                              color: c ? "var(--ink-0)" : "var(--ink-3)",
                              cursor: c ? "default" : "default",
                            }}>
                          {c ? c.trades : ""}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ display: "flex", gap: 14, marginTop: 10, alignItems: "center" }}>
              <LegendDot color="rgba(76,214,179,0.78)" label="이익 슬롯" />
              <LegendDot color="rgba(255,107,107,0.78)" label="손실 슬롯" />
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>셀 숫자 = 거래 건수</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ④ 언더워터 곡선 — analysis.underwater {series:[{date,drawdown}], max_drawdown}.
   고점 대비 반납액(원)을 0 아래로 채워 그린다(red 영역). 최대낙폭 구간(start~trough~recovery) 표기. */
function BtUnderwaterChart({ underwater }) {
  const series = (underwater && underwater.series) || [];
  const maxDd = underwater && underwater.max_drawdown;
  const [hover, setHover] = useState_btc(null);
  const svgRef = useRef_btc(null);

  const W = 880, H = 240;
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
            {/* Frame */}
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
            {/* 언더워터 영역 + 라인 */}
            {n > 1 && (
              <>
                <path d={areaPath} fill="url(#bt-uw-grad)" />
                <path d={linePath} fill="none" stroke="var(--red)" strokeWidth="1.4" opacity="0.85" />
              </>
            )}
            {/* X 라벨 */}
            {xTickIdx.map((i) => (
              <text key={`ux${i}`} className="chart-axis-text" x={x(i)} y={H - 10} textAnchor="middle">
                {series[i] ? _btDateLabel(series[i].date) : ""}
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

// ===========================================================================
// 결과·분석 영역 — 메트릭 카드 + 4차트 + 기여 테이블 + 인사이트.
//   /bt/result 를 로드해 위 차트들을 합성한다. backtest.jsx 의 BacktestTab 이 소비.
// ===========================================================================
const _BT_METRIC_CARDS = [
  { key: "trade_count",      label: "거래수",     fmt: (v) => fmtInt(v) },
  { key: "win_rate",         label: "승률",       fmt: (v) => fmtPct(v) },
  { key: "total_profit_pct", label: "수익률합계", fmt: (v) => fmtPct(v), signed: true },
  { key: "total_profit_krw", label: "수익금",     fmt: (v) => fmtMoney(v), signed: true },
  { key: "mdd_pct",          label: "MDD",        fmt: (v) => fmtPct(v), risk: true },
  { key: "cagr",             label: "CAGR",       fmt: (v) => fmtPct(v), signed: true },
];

function BtResultArea({ baseUrl, isDemo, jobId }) {
  const [result, setResult] = useState_btc(null);   // /bt/result
  const [loading, setLoading] = useState_btc(false);
  const [err, setErr] = useState_btc("");
  // 브러시 구간 분석 — {t_start,t_end} 또는 null(전체).
  const [range, setRange] = useState_btc(null);

  const load = useCallback_btc(() => {
    if (isDemo || !baseUrl || !jobId) { setResult(null); return; }
    setLoading(true); setErr("");
    let url = baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId);
    if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    _btFetchJson(url, 8000)
      .then(j => { setResult(j); if (!(j && j.available)) setErr("결과를 찾을 수 없습니다"); })
      .catch(e => { setResult(null); setErr(String(e)); })
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, jobId, range]);

  useEffect_btc(() => { load(); }, [load]);
  // jobId 가 바뀌면 구간 선택 초기화.
  useEffect_btc(() => { setRange(null); }, [jobId]);

  const onBrush = useCallback_btc((t_start, t_end) => {
    setRange({ t_start, t_end });
  }, []);
  const onBrushClear = useCallback_btc(() => { setRange(null); }, []);

  if (!jobId) {
    return (
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div>
        </div>
        <div className="panel-bd">
          <div className="research-empty">
            왼쪽에서 백테스트를 실행하거나 잡 이력을 선택하면 결과·분석이 여기에 표시됩니다.
          </div>
        </div>
      </div>
    );
  }

  if (loading && !result) {
    return (
      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div></div>
        <div className="panel-bd"><div className="research-empty">결과 로딩 중…</div></div>
      </div>
    );
  }

  if (err || !result || !result.available) {
    return (
      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div></div>
        <div className="panel-bd">
          <div className="research-empty" style={{ color: "var(--red)" }}>
            {err || "결과 없음"}
            <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={load}>재시도</button></div>
          </div>
        </div>
      </div>
    );
  }

  // no_trades → 안내 카드(에러 아님).
  if (result.status === "no_trades") {
    return (
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>결과 · 분석</div>
          <span className="badge warn">거래 0건</span>
        </div>
        <div className="panel-bd">
          <div className="empty" style={{ padding: "28px 24px" }}>
            <h2 style={{ color: "var(--amber)" }}>거래 0건</h2>
            <p>{result.message || "전략이 해당 기간에 매수 신호를 내지 않았습니다. 에러가 아닙니다 — 조건식/기간을 조정해 보세요."}</p>
          </div>
        </div>
      </div>
    );
  }

  const analysis = result.analysis || {};
  // 메트릭 우선순위: CLI metrics(브리핑 필드) → 없으면 analysis.summary 매핑.
  const metrics = result.metrics || {};
  const summary = analysis.summary || {};
  const metricVal = (key) => {
    if (metrics[key] != null) return metrics[key];
    // analysis.summary 폴백 매핑(cagr 은 summary 에 없음).
    const map = {
      trade_count: summary.trade_count, win_rate: summary.win_rate,
      total_profit_pct: summary.total_profit_pct, total_profit_krw: summary.total_profit_krw,
      mdd_pct: summary.max_drawdown_pct, cagr: undefined,
    };
    return map[key];
  };

  const distribution = analysis.distribution || {};
  const insights = analysis.insights || [];
  const topC = distribution.top_contributors || [];
  const botC = distribution.bottom_contributors || [];
  const dailyPnl = ((analysis.equity || {}).daily || []).map(d => d.pnl || 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 구간 분석 상태 배너 */}
      {range && (
        <div className="bt-range-bar">
          <span className="mono" style={{ fontSize: 11, color: "var(--teal)" }}>
            ◧ 구간 분석 적용 중 — {_btDateLabel(Math.floor(range.t_start / 1000000))}
            ~{_btDateLabel(Math.floor(range.t_end / 1000000))}
            {result.ranged && analysis.trade_count != null ? ` · ${analysis.trade_count}거래` : ""}
          </span>
          <button className="btn ghost sm" onClick={onBrushClear} style={{ marginLeft: "auto" }}>전체로 복귀</button>
        </div>
      )}

      {/* 메트릭 카드 행 — 카운트업 + 게이지 */}
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">
            <span className="dot" style={{ background: "var(--teal)" }}></span>핵심 메트릭
          </div>
          <button className="btn ghost sm" onClick={load} disabled={loading}>{loading ? "로딩…" : "↻"}</button>
        </div>
        <div className="bt-summary-row" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
          {_BT_METRIC_CARDS.map(m => {
            const v = metricVal(m.key);
            const num = typeof v === "number" ? v : null;
            return <_BtMetricCard key={m.key} meta={m} num={num} dailyPnl={dailyPnl} />;
          })}
        </div>
      </div>

      {/* 차트 — 수익곡선(인터랙션+브러시) → 분포 → 히트맵 → 언더워터 → MAE/MFE → 매도조건 */}
      <BtEquityChart equity={analysis.equity} onBrush={onBrush}
                     brushActive={!!range} onBrushClear={onBrushClear} />
      <BtDistributionChart distribution={distribution} />
      <BtHeatmap heatmap={analysis.heatmap} />
      <BtUnderwaterChart underwater={analysis.underwater} />
      <BtMaeMfeScatter points={analysis.mae_mfe} />
      <BtExitReasonPanel rows={analysis.exit_reasons} />

      {/* 종목 기여 Top/Bottom */}
      {(topC.length > 0 || botC.length > 0) && (
        <div className="panel">
          <div className="panel-hd">
            <div className="panel-hd-title"><span className="dot" style={{ background: "var(--blue)" }}></span>종목 기여</div>
          </div>
          <div className="panel-bd">
            <div className="row-2">
              <BtContribTable title="상위 기여" rows={topC} />
              <BtContribTable title="하위 기여" rows={botC} />
            </div>
          </div>
        </div>
      )}

      {/* 인사이트 패널 */}
      <BtInsightsPanel insights={insights} />
    </div>
  );
}

// 메트릭 카드 1개 — 카운트업 숫자 + (승률/MDD 게이지 · 수익금 스파크라인).
function _BtMetricCard({ meta, num, dailyPnl }) {
  const animated = _useCountUp(num != null ? num : 0, 600);
  const shown = num != null ? animated : null;
  let color;
  if (meta.risk) color = "var(--red)";
  else if (meta.signed && num != null) color = num > 0 ? "var(--teal)" : num < 0 ? "var(--red)" : undefined;

  // 승률·MDD 는 반원 게이지(0~100%).
  if ((meta.key === "win_rate" || meta.key === "mdd_pct") && num != null) {
    const gaugeColor = meta.key === "mdd_pct" ? "var(--red)" : "var(--teal)";
    return (
      <div className="bt-metric-card">
        <span className="summary-lbl">{meta.label}</span>
        <_BtArcGauge value={shown} max={100} color={gaugeColor}
                     label={meta.fmt(shown != null ? shown : 0)} />
      </div>
    );
  }
  // 수익금 카드는 일별손익 스파크라인 동반.
  if (meta.key === "total_profit_krw") {
    return (
      <div className="bt-metric-card">
        <span className="summary-lbl">{meta.label}</span>
        <span className="summary-val" style={{ color }}>{shown != null ? meta.fmt(shown) : "—"}</span>
        <_BtSparkline values={dailyPnl} />
      </div>
    );
  }
  return (
    <div className="bt-metric-card">
      <span className="summary-lbl">{meta.label}</span>
      <span className="summary-val" style={{ color }}>{shown != null ? meta.fmt(shown) : "—"}</span>
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

Object.assign(window, {
  BtEquityChart, BtDistributionChart, BtHeatmap, BtUnderwaterChart, BtResultArea,
  BtMaeMfeScatter, BtExitReasonPanel,
});
