/* Chart simulation — 서브패인 묶음 (split from simulation-charts.jsx for the 800-line cap).
   체결강도 히트 스트립 · 호가 잔량 흐름 · 호가 불균형 · net-delta · RSI · MACD ·
   오더플로우 테이프 · footprint · HTS형 호가창. 차트 하단/접이식 패널로 SimChartShell 이 결선한다.

   ASYMMETRIC PARITY — 호가불균형 · net-delta · RSI · MACD 는 live+svg 전용(engine !== "lwc").
   SimChartShell 이 토글별로 노출한다(이 파일은 컴포넌트 정의만 — 결선은 sim-chart-shell).
   backtest-charts.jsx 의 디자인 언어(chart-wrap · chart-axis-text · panel)를 따른다. */
import {
  useState_simc, useRef_simc, useMemo_simc, useEffect_simc,
  _SIM_WINDOW,
  _simTimeLabel, _simPriceTick,
  _strengthColor, _simRsi, _simMacd,
  _simNq, _hoga_tick, _bucketPrice, _barBuySell,
} from "./sim-chart-utils.jsx";

/* ───────────────────────── 히트 스트립 (Part C) ─────────────────────────
   차트 하단 체결강도 색 밴드(시간축 정렬). 리플레이 진행에 따라 view 가 채워진다. */
function SimHeatStrip({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);
  const n = view.length;
  if (n === 0) return null;
  const H = compact ? 14 : 18;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--violet)", flexShrink: 0, width: 48 }}>
        체결강도
      </span>
      <div style={{ display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
        {view.map((b, i) => (
          <div key={i} title={_simTimeLabel(b.t) + " · " + (b.strength || 0).toFixed(0)}
               style={{ flex: 1, background: _strengthColor(b.strength, 0.85) }} />
        ))}
      </div>
    </div>
  );
}

/* ───────────────────── 호가 잔량 흐름 (Part C) ─────────────────────
   매수총잔량(위)·매도총잔량(아래) 미러형 영역 차트(시간축 동기). 캔들 아래 접이식 패널.
   데이터(buy_rest/sell_rest)가 전혀 없으면(컬럼 부재 등) 패널 자동 숨김(무예외). */
function SimRestFlow({ bars, compact }) {
  const [open, setOpen] = useState_simc(false);

  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  // 유효 잔량 데이터 유무 — 하나라도 숫자면 패널 노출. 전부 None/무값이면 숨김.
  const hasData = useMemo_simc(() =>
    view.some(b => (b.buy_rest != null && isFinite(b.buy_rest)) ||
                   (b.sell_rest != null && isFinite(b.sell_rest))),
    [view]);

  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const half = compact ? 28 : 38;          // 위/아래 각 영역 높이.
  const H = half * 2 + 18;                  // +중앙 라벨/축 여백.
  const padL = 56, padR = 16;
  const innerW = W - padL - padR;
  const mid = half + 4;                     // 중앙선 y.

  const buyVals = view.map(b => (b.buy_rest != null && isFinite(b.buy_rest)) ? b.buy_rest : 0);
  const sellVals = view.map(b => (b.sell_rest != null && isFinite(b.sell_rest)) ? b.sell_rest : 0);
  const maxRest = Math.max(1, ...buyVals, ...sellVals);

  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yBuy = (v) => mid - (Math.min(v, maxRest) / maxRest) * half;     // 위로.
  const ySell = (v) => mid + (Math.min(v, maxRest) / maxRest) * half;    // 아래로.

  const areaPath = (vals, yFn) => {
    if (n === 0) return "";
    let d = `M ${xAt(0).toFixed(1)} ${mid.toFixed(1)} `;
    for (let i = 0; i < n; i++) d += `L ${xAt(i).toFixed(1)} ${yFn(vals[i]).toFixed(1)} `;
    d += `L ${xAt(n - 1).toFixed(1)} ${mid.toFixed(1)} Z`;
    return d;
  };

  const last = view.length ? view[view.length - 1] : null;
  const lastBuy = last && last.buy_rest != null ? last.buy_rest : null;
  const lastSell = last && last.sell_rest != null ? last.sell_rest : null;

  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "4px 8px",
          background: "transparent", border: "1px solid var(--line-1)", borderRadius: 5,
          color: "var(--ink-2)", cursor: "pointer", fontSize: 10,
        }}>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▼" : "▶"}</span>
        호가 잔량 흐름
        {lastBuy != null && (
          <span style={{ marginLeft: "auto", color: "var(--teal)" }}>
            매수 {_simPriceTick(lastBuy)}
          </span>
        )}
        {lastSell != null && (
          <span style={{ color: "var(--red)" }}>매도 {_simPriceTick(lastSell)}</span>
        )}
      </button>
      {open && (
        <div style={{ marginTop: 4 }}>
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
            {/* 중앙 기준선 */}
            <line x1={padL} x2={W - padR} y1={mid} y2={mid}
                  stroke="var(--line-2)" strokeWidth="1" />
            {/* 매수잔량(위, teal 영역) */}
            {n > 0 && <path d={areaPath(buyVals, yBuy)} fill="rgba(76,214,179,0.28)"
                            stroke="var(--teal)" strokeWidth="1" />}
            {/* 매도잔량(아래, red 영역) */}
            {n > 0 && <path d={areaPath(sellVals, ySell)} fill="rgba(255,93,108,0.26)"
                            stroke="var(--red)" strokeWidth="1" />}
            <text className="chart-axis-text" x={padL - 8} y={mid - half + 8} textAnchor="end" fill="var(--teal)">매수</text>
            <text className="chart-axis-text" x={padL - 8} y={mid + half} textAnchor="end" fill="var(--red)">매도</text>
            <text className="chart-axis-text" x={padL - 8} y={mid + 3} textAnchor="end" fill="var(--ink-3)">
              {_simPriceTick(maxRest)}
            </text>
          </svg>
        </div>
      )}
    </div>
  );
}

/* ─────────────── 호가 불균형 그래프 (Req 9, ASYMMETRIC: live+svg only) ───────────────
   b.imbalance(=매수총잔량/매도총잔량, 1.0=균형) 시계열 + 1.0 기준선. imbalance 부재 시
   buy_rest/sell_rest 로 정규화 폴백. 데이터 전무면 숨김(무예외). LWC 는 싣지 않는다. */
function SimImbalancePane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  // imbalance 값(직접 필드 우선, 없으면 buy_rest/sell_rest 비율). 둘 다 없으면 null.
  const vals = useMemo_simc(() => view.map(b => {
    if (b.imbalance != null && isFinite(b.imbalance)) return b.imbalance;
    const br = (b.buy_rest != null && isFinite(b.buy_rest)) ? b.buy_rest : null;
    const sr = (b.sell_rest != null && isFinite(b.sell_rest)) ? b.sell_rest : null;
    if (br != null && sr != null && sr > 0) return br / sr;
    return null;
  }), [view]);

  const hasData = useMemo_simc(() => vals.some(v => v != null), [vals]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 40;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  // 1.0 중심, 동적 상한(최대 비율, 최소 2.0). 0..vMax 선형, 1.0 균형선.
  const finite = vals.filter(v => v != null && isFinite(v));
  const vMax = Math.max(2.0, ...finite);
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => padT + innerH - (Math.min(v, vMax) / vMax) * innerH;

  let d = "", started = false;
  for (let i = 0; i < n; i++) {
    const v = vals[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
    started = true;
  }

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>호가 불균형(레벨1 총잔량비)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 1.0 균형선 */}
        <line x1={padL} x2={W - padR} y1={yAt(1.0)} y2={yAt(1.0)}
              stroke="rgba(255,255,255,0.14)" strokeWidth="1" strokeDasharray="2 3" />
        <text className="chart-axis-text" x={padL - 6} y={yAt(1.0) + 3} textAnchor="end" fill="var(--ink-3)">1.0</text>
        {n > 1 && <path d={d} fill="none" stroke="var(--teal)" strokeWidth="1.2" opacity="0.85" />}
      </svg>
    </div>
  );
}

/* ─────────────── net-delta strip (Req 7 in-chart orderflow, ASYMMETRIC: live+svg only) ───────────────
   bar 별 순매수수량(net_qty)을 색 히스토그램(>0 teal / <0 red)으로 캔들 아래 띠에 그린다.
   SimOrderFlowTape(side panel)과 달리 차트-내부 오더플로우 표현. net_qty 전무면 숨김. LWC 제외. */
function SimNetDeltaStrip({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const hasData = useMemo_simc(() =>
    view.some(b => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
    [view]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 28 : 38;
  const padL = 56, padR = 16;
  const innerW = W - padL - padR;
  const mid = H / 2;
  const half = mid - 3;
  const maxAbs = Math.max(1, ...view.map(b => Math.abs(_simNq(b))));
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.7);

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>net-delta(순매수수량)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 0 기준선 */}
        <line x1={padL} x2={W - padR} y1={mid} y2={mid} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        {view.map((b, i) => {
          const nq = _simNq(b);
          const h = (Math.min(Math.abs(nq), maxAbs) / maxAbs) * half;
          const x = padL + slot * i + (slot - barW) / 2;
          const y = nq >= 0 ? mid - h : mid;
          const color = nq > 0 ? "var(--teal)" : nq < 0 ? "var(--red)" : "var(--ink-3)";
          return <rect key={i} x={x.toFixed(1)} y={y.toFixed(1)} width={barW.toFixed(1)}
                       height={Math.max(0.5, h).toFixed(1)} fill={color} opacity="0.7" />;
        })}
      </svg>
    </div>
  );
}

/* ─────────────── RSI 서브패인 (Req 2, ASYMMETRIC: live+svg only) ───────────────
   RSI(Wilder 14기간) 0–100 스케일 SVG. 30/50/70 가이드선 + 폴리라인.
   클라이언트 _simRsi(window 전역) 으로 계산. LWC 는 싣지 않는다(ASYMMETRIC PARITY). */
function SimRsiPane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const rsiVals = useMemo_simc(() =>
    (typeof _simRsi === "function") ? _simRsi(view, 14) : [],
    [view]);

  const hasData = useMemo_simc(() => rsiVals.some(v => v != null), [rsiVals]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 40;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => padT + innerH - (Math.max(0, Math.min(100, v)) / 100) * innerH;

  let d = "", started = false;
  for (let i = 0; i < n; i++) {
    const v = rsiVals[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
    started = true;
  }

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>RSI(14)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 30 / 50 / 70 가이드선 */}
        {[30, 50, 70].map(lv => (
          <line key={lv} x1={padL} x2={W - padR} y1={yAt(lv)} y2={yAt(lv)}
                stroke="rgba(255,255,255,0.10)" strokeWidth="1" strokeDasharray="2 3" />
        ))}
        <text className="chart-axis-text" x={padL - 6} y={yAt(70) + 3} textAnchor="end" fill="var(--ink-3)">70</text>
        <text className="chart-axis-text" x={padL - 6} y={yAt(30) + 3} textAnchor="end" fill="var(--ink-3)">30</text>
        {n > 1 && <path d={d} fill="none" stroke="var(--teal)" strokeWidth="1.2" opacity="0.85" />}
      </svg>
    </div>
  );
}

/* ─────────────── MACD 서브패인 (Req 2, ASYMMETRIC: live+svg only) ───────────────
   MACD(12/26/9) zero-centered SVG: 히스토그램(hist) + MACD 라인 + 시그널 라인.
   클라이언트 _simMacd(window 전역) 으로 계산. LWC 는 싣지 않는다(ASYMMETRIC PARITY). */
function SimMacdPane({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const macdData = useMemo_simc(() =>
    (typeof _simMacd === "function") ? _simMacd(view) : { macd: [], signal: [], hist: [] },
    [view]);

  const hasData = useMemo_simc(() =>
    (macdData.macd || []).some(v => v != null),
    [macdData]);
  if (!hasData) return null;

  const n = view.length;
  const W = 880;
  const H = compact ? 30 : 42;
  const padL = 56, padR = 16, padT = 4, padB = 4;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const mid = padT + innerH / 2;
  const half = innerH / 2 - 1;

  const hist = macdData.hist || [];
  const macdLine = macdData.macd || [];
  const signalLine = macdData.signal || [];

  let maxAbs = 1;
  for (let i = 0; i < n; i++) {
    const v = hist[i];
    if (v != null && isFinite(v)) maxAbs = Math.max(maxAbs, Math.abs(v));
  }
  const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + (innerW * i) / (n - 1);
  const yAt = (v) => (v == null || !isFinite(v)) ? mid
    : mid - (Math.max(-maxAbs, Math.min(maxAbs, v)) / maxAbs) * half;

  const slot = n > 1 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.55);

  // MACD / 시그널 라인 path.
  const linePath = (vals) => {
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) { started = false; continue; }
      d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
      started = true;
    }
    return d;
  };

  return (
    <div style={{ marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)" }}>MACD(12,26,9)</span>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height: H }}>
        {/* 0 기준선 */}
        <line x1={padL} x2={W - padR} y1={mid} y2={mid} stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        {/* 히스토그램 막대 */}
        {view.map((b, i) => {
          const v = hist[i];
          if (v == null || !isFinite(v)) return null;
          const bh = Math.abs(yAt(v) - mid);
          const x = xAt(i) - barW / 2;
          const y = v >= 0 ? mid - bh : mid;
          const color = v > 0 ? "var(--teal)" : "var(--red)";
          return <rect key={i} x={x.toFixed(1)} y={y.toFixed(1)}
                       width={barW.toFixed(1)} height={Math.max(0.5, bh).toFixed(1)}
                       fill={color} opacity="0.55" />;
        })}
        {/* MACD 라인(teal 실선) */}
        {n > 1 && <path d={linePath(macdLine)} fill="none" stroke="var(--teal)" strokeWidth="1.1" opacity="0.9" />}
        {/* 시그널 라인(amber 점선) */}
        {n > 1 && <path d={linePath(signalLine)} fill="none" stroke="var(--amber)" strokeWidth="1" opacity="0.8" strokeDasharray="3 2" />}
      </svg>
    </div>
  );
}

/* ─────────────── 오더플로우 테이프 (Part: 오더플로우) ───────────────
   최근 N bar 의 순매수수량(net_qty) 을 색 스트립으로(순매수>0 teal 농도 / 순매도<0 red 농도).
   net_qty 데이터 전무면 숨김. 진행에 따라 우측으로 자라난다(리플레이 체감 강화). */
function SimOrderFlowTape({ bars, compact }) {
  const view = useMemo_simc(() => {
    const arr = bars || [];
    return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
  }, [bars]);

  const hasData = useMemo_simc(() =>
    view.some(b => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
    [view]);
  if (!hasData) return null;

  const maxAbs = Math.max(1, ...view.map(b => Math.abs(_simNq(b))));
  const H = compact ? 14 : 18;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 6 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--teal)", flexShrink: 0, width: 48 }}>
        오더플로우
      </span>
      <div style={{ display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
        {view.map((b, i) => {
          const nq = _simNq(b);
          const mag = Math.min(1, Math.abs(nq) / maxAbs);
          const a = (0.15 + mag * 0.75).toFixed(3);
          const bg = nq > 0 ? `rgba(76,214,179,${a})` : nq < 0 ? `rgba(255,93,108,${a})` : "rgba(150,158,170,0.12)";
          return (
            <div key={i} title={_simTimeLabel(b.t) + " · 순매수 " + _simPriceTick(nq)}
                 style={{ flex: 1, background: bg }} />
          );
        })}
      </div>
    </div>
  );
}

/* ─────────────── footprint 오더플로우 (S3) ───────────────
   가격 레벨별 매수/매도 체결량을 누적해 footprint 차트처럼 그린다(가격 사다리 행).
   각 행: [매도체결량 막대 | 가격 | 매수체결량 막대] + 델타. 현재가 행 강조, 강도 히트 색.

   체결량 분리(매수 vs 매도) — 데이터 출처 정직성:
     • net_qty(=초/분당매수수량−매도수량) 가 있으면 **실데이터 정확 분리**:
         buy = (vol + net_qty)/2,  sell = (vol − net_qty)/2   (분당매수/매도수량 복원).
     • net_qty 가 없으면(구버전 DB) 체결강도 휴리스틱으로 근사:
         강도>100 → 매수 우세, <100 → 매도 우세. share = clamp(strength/200, 0..1).
       이 경우는 근사임을 행 상단 배지로 명시한다(허위 정밀 회피).
   가격 버킷: bar 종가를 틱 크기로 내림 정렬(추정 틱 = 가격대별 한국거래소 호가단위 근사).
   순수 헬퍼(_simNq · _hoga_tick · _bucketPrice · _barBuySell)는 sim-chart-utils 단일 출처. */
function SimFootprint({ bars, compact }) {
  const [open, setOpen] = useState_simc(false);

  // 가격 레벨별 누적 매수/매도 체결량 집계(최근 윈도우). real 플래그도 추적.
  const agg = useMemo_simc(() => {
    const arr = bars || [];
    const view = arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    if (view.length === 0) return { levels: [], real: true, curPrice: null, hasVol: false };
    const last = view[view.length - 1];
    const map = new Map();     // bucketPrice → {buy, sell}
    let real = true;
    let hasVol = false;
    for (let i = 0; i < view.length; i++) {
      const b = view[i];
      const bs = _barBuySell(b);
      if (!bs.real) real = false;
      if ((bs.buy + bs.sell) > 0) hasVol = true;
      // Phase12-A — 호가단위는 bar 자기 가격으로 산정(단일 last.c tick 으로 전 구간을
      //   버킷하면 KRX 호가단위 경계(예: 50,000 전후 50→100)를 가로지를 때 정렬이 어긋남).
      const key = _bucketPrice(b.c, _hoga_tick(b.c));
      const cur = map.get(key) || { buy: 0, sell: 0 };
      cur.buy += bs.buy; cur.sell += bs.sell;
      map.set(key, cur);
    }
    // 가격 내림차순(높은 가격이 위).
    const levels = Array.from(map.entries())
      .map(([price, v]) => ({ price, buy: v.buy, sell: v.sell, delta: v.buy - v.sell }))
      .sort((a, b) => b.price - a.price);
    return { levels, real, curPrice: _bucketPrice(last.c, _hoga_tick(last.c)), hasVol };
  }, [bars]);

  if (!agg.hasVol) return null;   // 체결량 데이터 전무 → 숨김(무예외).

  const maxSide = Math.max(1, ...agg.levels.map(l => Math.max(l.buy, l.sell)));
  const rowH = compact ? 14 : 17;
  const barW = compact ? 80 : 110;

  return (
    <div style={{ marginTop: 6 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, width: "100%", padding: "4px 8px",
          background: "transparent", border: "1px solid var(--line-1)", borderRadius: 5,
          color: "var(--ink-2)", cursor: "pointer", fontSize: 10,
        }}>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▼" : "▶"}</span>
        오더플로우 footprint
        <span style={{ marginLeft: "auto", color: agg.real ? "var(--teal)" : "var(--amber)" }}>
          {agg.real ? "실데이터" : "강도 근사"}
        </span>
      </button>
      {open && (
        <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 1 }}>
          {/* 헤더 */}
          <div className="mono" style={{ display: "flex", alignItems: "center", fontSize: 8.5, color: "var(--ink-3)", padding: "0 2px" }}>
            <span style={{ width: barW, textAlign: "left", color: "var(--red)" }}>매도체결</span>
            <span style={{ flex: 1, textAlign: "center" }}>가격</span>
            <span style={{ width: barW, textAlign: "right", color: "var(--teal)" }}>매수체결</span>
            <span style={{ width: compact ? 44 : 56, textAlign: "right" }}>델타</span>
          </div>
          {agg.levels.map(lv => {
            const isCur = lv.price === agg.curPrice;
            const sellW = (lv.sell / maxSide) * barW;
            const buyW = (lv.buy / maxSide) * barW;
            const sellInt = Math.min(1, lv.sell / maxSide);
            const buyInt = Math.min(1, lv.buy / maxSide);
            return (
              <div key={lv.price} className="mono"
                   style={{
                     display: "flex", alignItems: "center", height: rowH, fontSize: 9.5,
                     background: isCur ? "rgba(255,210,76,0.10)" : "transparent",
                     borderRadius: 3,
                     boxShadow: isCur ? "0 0 0 1px rgba(255,210,76,0.4) inset" : "none",
                   }}>
                {/* 매도 체결 막대(우측 정렬 — 가격 쪽으로 자람) */}
                <div style={{ width: barW, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 4 }}>
                  <span style={{ color: "var(--ink-3)", fontSize: 8.5 }}>
                    {lv.sell >= 1 ? _simPriceTick(lv.sell) : ""}
                  </span>
                  <div style={{ width: sellW, height: rowH - 5, background: `rgba(255,93,108,${(0.25 + sellInt * 0.6).toFixed(3)})`, borderRadius: 2 }} />
                </div>
                {/* 가격 */}
                <span style={{ flex: 1, textAlign: "center", color: isCur ? "var(--amber)" : "var(--ink-1)", fontWeight: isCur ? 600 : 400 }}>
                  {_simPriceTick(lv.price)}
                </span>
                {/* 매수 체결 막대(좌측 정렬 — 가격 쪽에서 자람) */}
                <div style={{ width: barW, display: "flex", justifyContent: "flex-start", alignItems: "center", gap: 4 }}>
                  <div style={{ width: buyW, height: rowH - 5, background: `rgba(76,214,179,${(0.25 + buyInt * 0.6).toFixed(3)})`, borderRadius: 2 }} />
                  <span style={{ color: "var(--ink-3)", fontSize: 8.5 }}>
                    {lv.buy >= 1 ? _simPriceTick(lv.buy) : ""}
                  </span>
                </div>
                {/* 델타 */}
                <span style={{ width: compact ? 44 : 56, textAlign: "right", color: lv.delta >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {lv.delta >= 0 ? "+" : ""}{_simPriceTick(lv.delta)}
                </span>
              </div>
            );
          })}
          {!agg.real && (
            <div style={{ fontSize: 8.5, color: "var(--ink-3)", marginTop: 3, lineHeight: 1.4 }}>
              순매수수량(net_qty) 부재로 체결강도 기반 근사 분리다(실 매수/매도 체결량 아님).
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─────────────── HTS형 호가창 (S5) ───────────────
   실제 거래화면 호가창처럼 현재가 중심 수직 사다리. 매도 호가(위·파랑 톤·HTS 관행)·
   매수 호가(아래·빨강 톤)·레벨별 가로 잔량 막대·총매도/총매수 잔량 footer·체결강도 배지.

   가용 실데이터 한계 정직 표기: 일일 DB 는 최우선호가(bid1/ask1)와 총잔량(buy_rest/
   sell_rest)만 제공한다(레벨 2~10 호가 없음). 따라서 레벨1 + 총잔량을 크게 보여주고
   "레벨1 호가 + 총잔량" 임을 명시한다(허위 다단 호가 생성 금지). */
function SimOrderBook({ lastBar, compact }) {
  // Phase7 — bid1/ask1 변동 플래시. prev 값 추적해 변할 때 짧은 배경 글로우(CSS transition).
  const prevRef = useRef_simc({ bid1: null, ask1: null });
  const [flash, setFlash] = useState_simc({ bid: false, ask: false });

  const bid1 = (lastBar && lastBar.bid1 != null && isFinite(lastBar.bid1)) ? lastBar.bid1 : null;
  const ask1 = (lastBar && lastBar.ask1 != null && isFinite(lastBar.ask1)) ? lastBar.ask1 : null;

  useEffect_simc(() => {
    const p = prevRef.current;
    const bidChg = p.bid1 != null && bid1 != null && bid1 !== p.bid1;
    const askChg = p.ask1 != null && ask1 != null && ask1 !== p.ask1;
    if (bidChg || askChg) {
      setFlash({ bid: bidChg, ask: askChg });
      const id = setTimeout(() => setFlash({ bid: false, ask: false }), 280);
      prevRef.current = { bid1, ask1 };
      return () => clearTimeout(id);
    }
    prevRef.current = { bid1, ask1 };
  }, [bid1, ask1]);

  if (!lastBar) return null;
  const buyRest = (lastBar.buy_rest != null && isFinite(lastBar.buy_rest)) ? lastBar.buy_rest : null;
  const sellRest = (lastBar.sell_rest != null && isFinite(lastBar.sell_rest)) ? lastBar.sell_rest : null;
  // 호가도 잔량도 전무하면 숨김(무예외).
  if (bid1 == null && ask1 == null && buyRest == null && sellRest == null) return null;

  const cur = (lastBar.c != null && isFinite(lastBar.c)) ? lastBar.c : null;
  const strength = (lastBar.strength != null && isFinite(lastBar.strength)) ? lastBar.strength : null;
  const maxRest = Math.max(1, buyRest || 0, sellRest || 0);
  const askW = sellRest != null ? (sellRest / maxRest) * 100 : 0;
  const bidW = buyRest != null ? (buyRest / maxRest) * 100 : 0;
  // 스프레드(ask1-bid1) + bps(중간가 기준 만분율). 둘 다 있을 때만.
  const spread = (bid1 != null && ask1 != null) ? (ask1 - bid1) : null;
  const mid = (bid1 != null && ask1 != null) ? (ask1 + bid1) / 2 : null;
  const spreadBps = (spread != null && mid && mid > 0) ? (spread / mid) * 10000 : null;
  // 잔량 점유율(buy_rest vs sell_rest 총합 대비) — true ratio depth.
  const totRest = (buyRest || 0) + (sellRest || 0);
  const buyShare = totRest > 0 ? (buyRest || 0) / totRest * 100 : null;
  const sellShare = totRest > 0 ? (sellRest || 0) / totRest * 100 : null;
  // 체결강도 색(100=균형). >100 매수 우세(teal), <100 매도 우세(red).
  const stColor = strength == null ? "var(--ink-2)" : strength >= 100 ? "var(--teal)" : "var(--red)";
  const rowH = compact ? 20 : 24;
  const askBg = flash.ask ? "rgba(56,140,255,0.22)" : "rgba(56,140,255,0.06)";
  const bidBg = flash.bid ? "rgba(255,93,108,0.22)" : "rgba(255,93,108,0.06)";

  return (
    <div style={{ marginTop: 6 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3, gap: 6 }}>
        <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}
              title="일일 DB는 최우선호가·총잔량만 제공(레벨2~10 없음)">호가창 (레벨1 + 총잔량)</span>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {spread != null && (
            <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-2)" }}>
              스프레드 {_simPriceTick(spread)}{spreadBps != null ? ` (${spreadBps.toFixed(1)}bp)` : ""}
            </span>
          )}
          {strength != null && (
            <span className="mono" style={{ fontSize: 9.5, color: stColor, padding: "1px 6px", borderRadius: 3, border: "1px solid " + (strength >= 100 ? "var(--teal-dim)" : "var(--line-1)") }}>
              체결강도 {strength.toFixed(0)}
            </span>
          )}
        </div>
      </div>
      {/* 매도호가1(위, HTS 파랑 톤) — bid/ask 변동 시 배경 플래시(CSS transition) */}
      <div style={{ display: "flex", alignItems: "center", height: rowH, background: askBg, borderRadius: 3, marginBottom: 1, transition: "background 0.28s ease-out" }}>
        <span className="mono" style={{ width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#5aa0ff", paddingRight: 8 }}>
          {ask1 != null ? _simPriceTick(ask1) : "—"}
        </span>
        <div style={{ flex: 1, height: rowH - 8, position: "relative", display: "flex", justifyContent: "flex-start" }}>
          <div style={{ width: askW + "%", height: "100%", background: "rgba(56,140,255,0.30)", borderRadius: 2, transition: "width 0.2s ease-out" }} />
        </div>
        <span className="mono" style={{ width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#5aa0ff", paddingRight: 4 }}>
          {sellRest != null ? _simPriceTick(sellRest) : "—"}
        </span>
      </div>
      {/* 현재가 구분선 */}
      <div className="mono" style={{ textAlign: "center", fontSize: 11, color: "var(--amber)", padding: "2px 0", letterSpacing: ".04em" }}>
        ▸ {cur != null ? _simPriceTick(cur) : "—"} ◂
      </div>
      {/* 매수호가1(아래, HTS 빨강 톤) */}
      <div style={{ display: "flex", alignItems: "center", height: rowH, background: bidBg, borderRadius: 3, marginTop: 1, transition: "background 0.28s ease-out" }}>
        <span className="mono" style={{ width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#ff8088", paddingRight: 8 }}>
          {bid1 != null ? _simPriceTick(bid1) : "—"}
        </span>
        <div style={{ flex: 1, height: rowH - 8, display: "flex", justifyContent: "flex-start" }}>
          <div style={{ width: bidW + "%", height: "100%", background: "rgba(255,93,108,0.28)", borderRadius: 2, transition: "width 0.2s ease-out" }} />
        </div>
        <span className="mono" style={{ width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#ff8088", paddingRight: 4 }}>
          {buyRest != null ? _simPriceTick(buyRest) : "—"}
        </span>
      </div>
      {/* 미니 불균형 게이지 — buy_rest vs sell_rest 점유율(% 라벨). 잔량 데이터 있을 때만. */}
      {buyShare != null && sellShare != null && (
        <div style={{ marginTop: 5 }}>
          <div style={{ display: "flex", height: 6, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" }}>
            <div style={{ width: buyShare.toFixed(1) + "%", background: "var(--teal)", opacity: 0.7, transition: "width 0.25s ease-out" }} />
            <div style={{ width: sellShare.toFixed(1) + "%", background: "var(--red)", opacity: 0.7, transition: "width 0.25s ease-out" }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 2, fontSize: 9 }}>
            <span className="mono" style={{ color: "var(--teal)" }}>매수 {buyShare.toFixed(0)}%</span>
            <span className="mono" style={{ color: "var(--red)" }}>매도 {sellShare.toFixed(0)}%</span>
          </div>
        </div>
      )}
      {/* footer — 총매도/총매수 잔량 */}
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 9.5 }}>
        <span className="mono" style={{ color: "#5aa0ff" }}>총매도 {sellRest != null ? _simPriceTick(sellRest) : "—"}</span>
        <span className="mono" style={{ color: "#ff8088" }}>총매수 {buyRest != null ? _simPriceTick(buyRest) : "—"}</span>
      </div>
    </div>
  );
}

export {
  SimHeatStrip, SimRestFlow,
  SimImbalancePane, SimNetDeltaStrip, SimRsiPane, SimMacdPane,
  SimOrderFlowTape, SimFootprint, SimOrderBook,
};
