/* Chart simulation — 공통 셸 + 헤더 비주얼 (split from simulation-charts.jsx for the 800-line cap).
   ① SimChangeGauge : 종목 등락율 반원 게이지(상승 빨강/하락 파랑, ±12% 포화).
   ② SimSessionRing : 세션 진행 링(09:00~15:30 대비 현재 시각 호 채움).
   ③ SimChartShell  : 헤더(종목·현재가·게이지·세션 링) + 본문(차트) + 서브패인 + 히트 스트립.
       신호 도달 순간 패널 테두리 1회 플래시. 호가불균형 · net-delta · RSI · MACD 서브패인은
       ASYMMETRIC — live+svg 만(engine !== "lwc") 토글 시 노출.

   소비처: sim-chart-engines(SimCandleChartLWC · SimCandleChartSVG 가 children 으로 차트를 싣는다). */
import {
  useState_simc, useRef_simc, useEffect_simc,
  _SIM_DEFAULT_INDICATORS,
  _simTimeLabel, _simPriceTick,
  _sessionProgress, _changeColor,
} from "./sim-chart-utils.jsx";
import {
  SimHeatStrip, SimRestFlow,
  SimImbalancePane, SimNetDeltaStrip, SimRsiPane, SimMacdPane,
  SimOrderFlowTape, SimFootprint, SimOrderBook,
} from "./sim-chart-subpanes.jsx";

// 반원 게이지 — 등락율을 -12%(좌)~+12%(우) 반원 바늘로 표시. SVG 순수(라이브러리 없음).
function SimChangeGauge({ changePct, size }) {
  const S = size || 56;
  const v = Number(changePct) || 0;
  const clamped = Math.max(-12, Math.min(12, v));
  // -12%→180°(좌), 0%→90°(상), +12%→0°(우). 반원(180°→0°).
  const angle = 180 - ((clamped + 12) / 24) * 180;
  const rad = (angle * Math.PI) / 180;
  const r = S / 2 - 4;
  const cx = S / 2, cy = S / 2;
  const nx = cx + r * Math.cos(rad);
  const ny = cy - r * Math.sin(rad);
  const color = _changeColor(v);
  return (
    <svg width={S} height={S / 2 + 6} viewBox={`0 0 ${S} ${S / 2 + 6}`} aria-hidden="true">
      {/* 반원 트랙 */}
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
            fill="none" stroke="var(--line-2)" strokeWidth="3" strokeLinecap="round" />
      {/* 중앙 0% 틱 */}
      <line x1={cx} y1={cy - r} x2={cx} y2={cy - r + 4}
            stroke="var(--ink-3)" strokeWidth="1" />
      {/* 바늘 */}
      <line x1={cx} y1={cy} x2={nx.toFixed(2)} y2={ny.toFixed(2)}
            stroke={color} strokeWidth="2.4" strokeLinecap="round" />
      <circle cx={cx} cy={cy} r="2.6" fill={color} />
      {/* 등락 라벨 */}
      <text x={cx} y={cy - 2} textAnchor="middle" fontSize="10" className="mono"
            fill={color}>
        {v > 0 ? "+" : ""}{v.toFixed(2)}%
      </text>
    </svg>
  );
}

// 세션 진행 링 — 09:00~15:30 대비 현재 시각(curT) 호 채움 + 중앙 HH:MM.
function SimSessionRing({ curT, size }) {
  const S = size || 52;
  const r = S / 2 - 5;
  const cx = S / 2, cy = S / 2;
  const circ = 2 * Math.PI * r;
  const prog = _sessionProgress(curT);
  const dash = (circ * prog).toFixed(2);
  const label = curT != null ? _simTimeLabel(curT).slice(0, 5) : "--:--";
  return (
    <svg width={S} height={S} viewBox={`0 0 ${S} ${S}`} aria-hidden="true">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--line-2)" strokeWidth="3" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--teal)" strokeWidth="3"
              strokeLinecap="round" strokeDasharray={`${dash} ${(circ - dash).toFixed(2)}`}
              transform={`rotate(-90 ${cx} ${cy})`} />
      <text x={cx} y={cy + 3.2} textAnchor="middle" fontSize="10" className="mono"
            fill="var(--ink-1)">{label}</text>
    </svg>
  );
}

/* 공통 셸 — 헤더(종목·현재가·등락 게이지·세션 링) + 본문(차트) + 히트 스트립.
   신호(매수/매도) 도달 순간 패널 테두리를 1회 플래시한다(curT 가 신호 시각을 막 넘을 때).
   호가 불균형·net-delta·RSI·MACD 서브패인은 ASYMMETRIC — live+svg 만(engine !== "lwc") 토글 시 노출. */
function SimChartShell({ code, name, lastBar, bars, signals, curT, compact, engine, indicators, children }) {
  const ind = indicators || _SIM_DEFAULT_INDICATORS;
  // 신호 도달 플래시 — curT 가 새 신호 시각(buy/sell)을 넘는 순간 1회 깜빡. ref 로 도달분 추적.
  const seenRef = useRef_simc(new Set());
  const [flash, setFlash] = useState_simc(null);  // "buy"|"sell"|null.

  // 리플레이 재시작(curT 리셋) 시 도달 기록 초기화.
  useEffect_simc(() => {
    if (curT == null) seenRef.current = new Set();
  }, [curT]);

  useEffect_simc(() => {
    if (curT == null) return;
    const seen = seenRef.current;
    let kind = null;
    (signals || []).forEach((sig) => {
      const bk = code + "@b@" + sig.buy_hms;
      if (sig.buy_hms != null && sig.buy_hms <= curT && !seen.has(bk)) { seen.add(bk); kind = "buy"; }
      const sk = code + "@s@" + sig.sell_hms;
      if (sig.sell_hms != null && sig.sell_hms <= curT && !seen.has(sk)) { seen.add(sk); kind = "sell"; }
    });
    if (kind) {
      setFlash(kind);
      const id = setTimeout(() => setFlash(null), 650);
      return () => clearTimeout(id);
    }
  }, [curT, signals, code]);

  // 신호 도달 테두리 플래시 — 인라인 boxShadow + transition 으로 1회 점멸(styles.css 불가).
  //   매수=teal 글로우, 매도=red 글로우. 650ms 뒤 flash=null → transition 으로 부드럽게 소멸.
  const flashGlow = flash === "buy"
    ? "0 0 0 2px var(--teal), 0 0 16px 2px rgba(76,214,179,0.55)"
    : flash === "sell"
      ? "0 0 0 2px var(--red), 0 0 16px 2px rgba(255,93,108,0.55)"
      : "none";
  return (
    <div className="panel" style={{ minWidth: 0, boxShadow: flashGlow, transition: "box-shadow 0.45s ease-out" }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          <span className="mono" style={{ fontSize: compact ? 11 : 12.5 }}>
            {code}{name ? " · " + name : ""}
          </span>
          <span className="mono" style={{ fontSize: 9, color: "var(--ink-3)", marginLeft: 6 }}>
            {engine === "lwc" ? "LWC" : "SVG"}
          </span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {lastBar && <SimChangeGauge changePct={lastBar.change} size={compact ? 48 : 56} />}
          <SimSessionRing curT={curT} size={compact ? 44 : 52} />
          {lastBar && (
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)" }}>
              {_simPriceTick(lastBar.c)}
            </span>
          )}
        </div>
      </div>
      <div className="panel-bd">
        {children}
        {/* 차트-내부 서브패인 — ASYMMETRIC: live+svg 만(LWC 제외). 토글별 노출. */}
        {engine !== "lwc" && ind.imbalance && <SimImbalancePane bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.orderflow && <SimNetDeltaStrip bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.rsi && <SimRsiPane bars={bars} compact={compact} />}
        {engine !== "lwc" && ind.macd && <SimMacdPane bars={bars} compact={compact} />}
        <SimOrderBook lastBar={lastBar} compact={compact} />
        <SimOrderFlowTape bars={bars} compact={compact} />
        <SimFootprint bars={bars} compact={compact} />
        <SimHeatStrip bars={bars} compact={compact} />
        <SimRestFlow bars={bars} compact={compact} />
      </div>
    </div>
  );
}

export { SimChangeGauge, SimSessionRing, SimChartShell };
