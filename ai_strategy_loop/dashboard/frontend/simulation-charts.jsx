/* Chart simulation candles — PR3 (split from simulation.jsx for the 800-line cap).
   순수 SVG 캔들+거래량 차트(외부 라이브러리 금지). 실시간 append 렌더(최근 N=400 캔들 윈도우),
   매수▲/매도▼ 신호 마커+수익률 라벨, 체결강도 서브라인. backtest-charts.jsx 의 디자인 언어
   (chart-wrap·chart-axis-text·panel)를 그대로 따른다.

   window 전역으로 공유: index.html 에서 simulation.jsx 보다 먼저 로드된다.
   소비 컴포넌트(export):
     - SimCandleChart : 한 종목의 캔들+거래량+신호 마커+체결강도 서브라인.
     - SimSignalLog   : 신호(매수/매도) 시각·가격·수익률 목록(현재 t 도달 시 하이라이트). */
const {
  useState: useState_simc, useRef: useRef_simc, useMemo: useMemo_simc,
} = React;

// 최근 N 캔들 윈도우(렌더 부하 상한).
const _SIM_WINDOW = 400;

// HHMMSS(int) → HH:MM:SS 라벨.
function _simTimeLabel(hms) {
  const s = String(hms).padStart(6, "0");
  return s.slice(0, 2) + ":" + s.slice(2, 4) + ":" + s.slice(4, 6);
}

// 가격 축약(원). 큰 가격도 읽기 쉽게.
function _simPriceTick(v) {
  if (v == null) return "—";
  return Math.round(v).toLocaleString("ko-KR");
}

/* ① 캔들 + 거래량 + 신호 마커 + 체결강도 서브라인.
   props:
     bars     : [{t, o, h, l, c, vol, change, strength}...]  (이 종목 누적 시계열)
     signals  : [{buy_hms, sell_hms, buy_price, sell_price, profit_pct}...]
     curT     : 현재 리플레이 시각(HHMMSS) — 도달 신호 강조용.
     code/name: 헤더 라벨.
     compact  : 그리드(2~4종목) 모드면 높이 축소. */
function SimCandleChart({ bars, signals, curT, code, name, compact }) {
  const [hover, setHover] = useState_simc(null);
  const svgRef = useRef_simc(null);

  // 최근 윈도우만 렌더.
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const W = 880;
  const H = compact ? 220 : 340;
  const volH = compact ? 34 : 52;       // 거래량 영역 높이.
  const strH = compact ? 24 : 34;       // 체결강도 서브라인 높이.
  const padL = 56, padR = 16, padT = 14;
  const gap = 8;
  const priceH = H - padT - volH - strH - gap * 2 - 22;  // 하단 22 = 시간축.
  const innerW = W - padL - padR;

  const n = view.length;
  const slot = n > 0 ? innerW / n : innerW;
  const candleW = Math.max(1, Math.min(14, slot * 0.66));
  const xCenter = (i) => padL + slot * (i + 0.5);

  // 가격 스케일(고저 기준).
  const priceTop = padT;
  const priceBot = padT + priceH;
  const highs = view.map(b => b.h || b.c || 0);
  const lows = view.map(b => b.l || b.c || 0).filter(v => v > 0);
  const pMax = highs.length ? Math.max(...highs) : 1;
  const pMin = lows.length ? Math.min(...lows) : 0;
  const pRange = (pMax - pMin) || 1;
  const yPrice = (v) => priceBot - ((v - pMin) / pRange) * priceH;

  // 거래량 스케일.
  const volTop = priceBot + gap;
  const volBot = volTop + volH;
  const vMax = Math.max(1, ...view.map(b => b.vol || 0));
  const yVol = (v) => volBot - (v / vMax) * volH;

  // 체결강도 스케일(0~200 통상, 100=균형).
  const strTop = volBot + gap;
  const strBot = strTop + strH;
  const strVals = view.map(b => b.strength || 0);
  const sMax = Math.max(100, ...strVals);
  const yStr = (v) => strBot - (Math.min(v, sMax) / sMax) * strH;

  // 신호 마커 — view 윈도우 안의 t 에 매핑(가장 가까운 캔들 인덱스).
  const tIndex = useMemo_simc(() => {
    const m = new Map();
    view.forEach((b, i) => m.set(b.t, i));
    return m;
  }, [view]);

  const nearestIdx = (hms) => {
    if (tIndex.has(hms)) return tIndex.get(hms);
    // 가장 가까운(이하) 캔들 — 신호 시각이 정확한 캔들 t 와 다를 수 있다.
    let best = -1;
    for (let i = 0; i < n; i++) {
      if (view[i].t <= hms) best = i; else break;
    }
    return best;
  };

  const strPath = useMemo_simc(() => {
    if (n < 2) return "";
    return view.map((b, i) =>
      `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yStr(b.strength || 0).toFixed(1)}`
    ).join(" ");
  }, [view, n, sMax]);

  const xTickIdx = useMemo_simc(() => {
    if (n <= 1) return n === 1 ? [0] : [];
    const step = Math.max(1, Math.ceil(n / 7));
    const idx = [];
    for (let i = 0; i < n; i += step) idx.push(i);
    if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
    return idx;
  }, [n]);

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };

  const lastBar = n > 0 ? view[n - 1] : null;

  return (
    <div className="panel" style={{ minWidth: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          <span className="mono" style={{ fontSize: compact ? 11 : 12.5 }}>
            {code}{name ? " · " + name : ""}
          </span>
        </div>
        {lastBar && (
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)" }}>
              {_simPriceTick(lastBar.c)}
            </span>
            <span className={"mono " + (lastBar.change > 0 ? "num-pos" : lastBar.change < 0 ? "num-neg" : "")}
                  style={{ fontSize: 11 }}>
              {lastBar.change > 0 ? "+" : ""}{(lastBar.change || 0).toFixed(2)}%
            </span>
          </div>
        )}
      </div>
      <div className="panel-bd">
        <div className="chart-wrap">
          <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
               onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
            {/* 가격 축 라벨(고/저) */}
            <text className="chart-axis-text" x={padL - 8} y={priceTop + 8} textAnchor="end" fill="var(--ink-2)">
              {_simPriceTick(pMax)}
            </text>
            <text className="chart-axis-text" x={padL - 8} y={priceBot} textAnchor="end" fill="var(--ink-2)">
              {_simPriceTick(pMin)}
            </text>
            {/* 가격 프레임 */}
            <line x1={padL} x2={W - padR} y1={priceBot} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />
            <line x1={padL} x2={padL} y1={priceTop} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />

            {/* 캔들 */}
            {view.map((b, i) => {
              const up = (b.c || 0) >= (b.o || 0);
              const color = up ? "var(--teal)" : "var(--red)";
              const cx = xCenter(i);
              const yHigh = yPrice(b.h || b.c || 0);
              const yLow = yPrice(b.l || b.c || 0);
              const yO = yPrice(b.o || b.c || 0);
              const yC = yPrice(b.c || 0);
              const top = Math.min(yO, yC);
              const bodyH = Math.max(1, Math.abs(yC - yO));
              return (
                <g key={`k${i}`} opacity={hover === i ? 1 : 0.92}>
                  <line x1={cx} x2={cx} y1={yHigh} y2={yLow} stroke={color} strokeWidth="1" />
                  <rect x={cx - candleW / 2} y={top} width={candleW} height={bodyH} fill={color} />
                </g>
              );
            })}

            {/* 거래량 막대 */}
            {view.map((b, i) => {
              const up = (b.c || 0) >= (b.o || 0);
              const y = yVol(b.vol || 0);
              return <rect key={`v${i}`} x={xCenter(i) - candleW / 2} y={y}
                           width={candleW} height={Math.max(0, volBot - y)}
                           fill={up ? "var(--teal)" : "var(--red)"} opacity="0.4" />;
            })}
            <text className="chart-axis-text" x={padL - 8} y={volTop + 8} textAnchor="end" fill="var(--ink-3)">거래량</text>

            {/* 체결강도 서브라인(100 균형선) */}
            <line x1={padL} x2={W - padR} y1={yStr(100)} y2={yStr(100)}
                  stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />
            {n > 1 && <path d={strPath} fill="none" stroke="var(--violet)" strokeWidth="1.3" opacity="0.85" />}
            <text className="chart-axis-text" x={padL - 8} y={strTop + 8} textAnchor="end" fill="var(--violet)">체결강도</text>

            {/* 신호 마커 — 매수▲(teal, 가격 아래) / 매도▼(red, 가격 위) */}
            {(signals || []).map((sig, si) => {
              const bi = nearestIdx(sig.buy_hms);
              const sj = nearestIdx(sig.sell_hms);
              const reached = curT != null && sig.sell_hms <= curT;
              const buyVisible = bi >= 0 && (curT == null || sig.buy_hms <= curT);
              const sellVisible = sj >= 0 && (curT == null || sig.sell_hms <= curT);
              return (
                <g key={`s${si}`}>
                  {buyVisible && (
                    <text x={xCenter(bi)} y={yPrice(sig.buy_price) + 13} textAnchor="middle"
                          fontSize={compact ? 10 : 12} fill="var(--teal)" opacity={reached ? 1 : 0.85}>▲</text>
                  )}
                  {sellVisible && (
                    <g>
                      <text x={xCenter(sj)} y={yPrice(sig.sell_price) - 5} textAnchor="middle"
                            fontSize={compact ? 10 : 12} fill="var(--red)" opacity="1">▼</text>
                      {!compact && (
                        <text x={xCenter(sj)} y={yPrice(sig.sell_price) - 16} textAnchor="middle"
                              fontSize="9" className="mono"
                              fill={sig.profit_pct >= 0 ? "var(--teal)" : "var(--red)"}>
                          {sig.profit_pct >= 0 ? "+" : ""}{(sig.profit_pct || 0).toFixed(1)}%
                        </text>
                      )}
                    </g>
                  )}
                </g>
              );
            })}

            {/* X 시간 라벨 */}
            {xTickIdx.map((i) => (
              <text key={`x${i}`} className="chart-axis-text" x={xCenter(i)} y={H - 6} textAnchor="middle">
                {view[i] ? _simTimeLabel(view[i].t) : ""}
              </text>
            ))}

            {/* Hover 수직선 */}
            {hover != null && view[hover] && (
              <line x1={xCenter(hover)} x2={xCenter(hover)} y1={priceTop} y2={priceBot}
                    stroke="rgba(255,255,255,0.14)" strokeWidth="1" />
            )}
          </svg>

          {hover != null && view[hover] && (
            <div style={{
              position: "absolute", top: 12, right: 12,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11,
              minWidth: 150, boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 }}>
                {_simTimeLabel(view[hover].t)}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>종가</span>
                <span style={{ textAlign: "right" }}>{_simPriceTick(view[hover].c)}</span>
                <span style={{ color: "var(--ink-2)" }}>등락</span>
                <span style={{ textAlign: "right" }} className={view[hover].change >= 0 ? "num-pos" : "num-neg"}>
                  {(view[hover].change || 0).toFixed(2)}%
                </span>
                <span style={{ color: "var(--ink-2)" }}>체결강도</span>
                <span style={{ textAlign: "right" }}>{(view[hover].strength || 0).toFixed(0)}</span>
              </div>
            </div>
          )}

          {n === 0 && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", alignItems: "center",
              justifyContent: "center", color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
            }}>
              재생을 시작하면 캔들이 실시간으로 채워집니다
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ② 체결 로그 — 신호(매수/매도) 목록. 현재 리플레이 시각(curT) 도달 행 하이라이트. */
function SimSignalLog({ signals, curT }) {
  const rows = signals || [];
  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          체결 로그
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {rows.length}건 · 엔진 신호
        </span>
      </div>
      <div className="panel-bd" style={{ maxHeight: 420, overflowY: "auto", padding: "8px 10px" }}>
        {rows.length === 0 ? (
          <div className="research-empty">조건식을 선택하면 매매 신호가 표시됩니다.</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {rows.map((s, i) => {
              const reached = curT != null && s.sell_hms <= curT;
              const buying = curT != null && s.buy_hms <= curT && s.sell_hms > curT;
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 8, padding: "5px 7px", borderRadius: 5,
                  border: "1px solid " + (buying ? "var(--amber)" : reached ? "var(--line-1)" : "var(--line-1)"),
                  background: buying ? "rgba(240,179,90,0.10)" : reached ? "var(--bg-0)" : "transparent",
                  opacity: reached || buying ? 1 : 0.5,
                }}>
                  <span className="mono" style={{ fontSize: 10, color: "var(--teal)", flexShrink: 0 }}>
                    ▲{_simTimeLabel(s.buy_hms)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--red)", flexShrink: 0 }}>
                    ▼{_simTimeLabel(s.sell_hms)}
                  </span>
                  <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flex: 1, textAlign: "right", whiteSpace: "nowrap" }}>
                    {_simPriceTick(s.buy_price)}→{_simPriceTick(s.sell_price)}
                  </span>
                  <span className={"mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg")}
                        style={{ fontSize: 11, flexShrink: 0, width: 52, textAlign: "right" }}>
                    {s.profit_pct >= 0 ? "+" : ""}{(s.profit_pct || 0).toFixed(1)}%
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

Object.assign(window, { SimCandleChart, SimSignalLog, _simTimeLabel, _simPriceTick });
