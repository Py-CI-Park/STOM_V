/* Chart simulation candles — 엔진 경로 (split from simulation-charts.jsx for the 800-line cap).
   기본 엔진: TradingView lightweight-charts(standalone, vendor-lightweight-charts.js).
   window.LightweightCharts 전역이 있으면 캔들+거래량+마커(매수▲/매도▼)를 그 엔진으로
   그리고(줌/팬/크로스헤어 내장), 없으면(오프라인 등) 기존 순수 SVG 폴백을 쓴다 —
   SVG 폴백도 휠 줌·드래그 팬·크로스헤어를 직접 구현해 두 경로 모두 동작한다.

   소비 컴포넌트(export):
     - SimCandleChartLWC : lightweight-charts 엔진 캔들+거래량+신호 마커(체결강도 오버레이 1개).
     - SimCandleChartSVG : 순수 SVG 폴백(줌/팬/크로스헤어 직접 구현) + 서브패인(ASYMMETRIC).
     - SimCandleChart    : 엔진 자동선택(LWC↔SVG) 래퍼.
   공통 셸(헤더·서브패인·히트 스트립)은 SimChartShell(sim-chart-shell)이 담당한다. */
import {
  useState_simc, useRef_simc, useMemo_simc, useEffect_simc,
  _SIM_WINDOW, _SIM_LWC_MAX, _SIM_DEFAULT_INDICATORS, _SIM_IND_STYLE,
  _simEma, _simVolMa, _simStrengthMa,
  _simTimeLabel, _simPriceTick,
  _hmsToSec, _lwcAvailable, _monotonicSecs, _lineData,
} from "./sim-chart-utils.jsx";
import { SimChartShell } from "./sim-chart-shell.jsx";

/* ─────────────── lightweight-charts 엔진 경로 (기본) ─────────────── */
/* ⚠ ASYMMETRIC PARITY (FINAL) — LWC stacking SPIKE 결론(Phase7 §7.3 STEP 0):
   lightweight-charts v4.2 에는 addPane API 가 없다. 서브-시리즈는 단일 캔들 페인 위에
   distinct priceScaleId + scaleMargins 로 쌓는 "오버레이 프라이스 스케일"뿐이다.
   compact H=240 에서 vol(scaleMargins top:0.82 → 18%) + strength + imbalance 를 3개
   오버레이 밴드로 쌓으면 각 밴드가 화면을 또 갉아먹어 캔들 본체 밴드가 가독 하한
   55% 아래(추정 ~45% 이하)로 떨어진다(vol 18% + strength~13% + imbalance~13% ≈ 44%
   소비 → 캔들 ≈ 56% 이지만 축 라벨/여백 차감 시 55% 하회). 따라서 비대칭 패리티를
   FINAL 로 못박는다: LWC 는 strength 오버레이 한 개만 싣는다(그 전문 강점은 줌/크로스헤어/
   네이티브 last-price 애니메이션이지 커스텀 서브패인이 아니다). 호가 불균형·net-delta 는
   live+svg 만 싣는다(SimCandleChartSVG·SimLiveChart). */
function SimCandleChartLWC({ bars, signals, curT, code, name, compact, indicators }) {
  const wrapRef = useRef_simc(null);
  const chartRef = useRef_simc(null);
  const candleRef = useRef_simc(null);
  const volRef = useRef_simc(null);
  const roRef = useRef_simc(null);
  const lineRef = useRef_simc({});   // key → LWC line series.
  const strRef = useRef_simc(null);  // 체결강도 오버레이 라인 시리즈(단 하나의 서브-시리즈).
  const strMaRef = useRef_simc(null); // 체결강도 MA 오버레이(strma 토글 시).
  const ind = indicators || _SIM_DEFAULT_INDICATORS;

  const H = compact ? 240 : 360;

  // 차트 1회 생성(언마운트 시 정리). ResizeObserver 로 폭 추종.
  useEffect_simc(() => {
    const LWC = window.LightweightCharts;
    const el = wrapRef.current;
    if (!LWC || !el) return;
    const chart = LWC.createChart(el, {
      width: el.clientWidth || 600,
      height: H,
      layout: { background: { color: "transparent" }, textColor: "rgba(200,205,215,0.7)", fontFamily: "var(--mono)" },
      grid: { vertLines: { color: "rgba(255,255,255,0.04)" }, horzLines: { color: "rgba(255,255,255,0.05)" } },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.1)" },
      timeScale: {
        borderColor: "rgba(255,255,255,0.1)",
        // 봉 수가 적은 리플레이 초반의 우측 압착/과확대 방지 — 고정 기본 간격.
        rightOffset: 4, barSpacing: 7, minBarSpacing: 2,
        timeVisible: true, secondsVisible: !compact,
        tickMarkFormatter: (t) => {
          const sec = ((t % 86400) + 86400) % 86400;
          const hh = String(Math.floor(sec / 3600)).padStart(2, "0");
          const mm = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
          return hh + ":" + mm;
        },
      },
      crosshair: { mode: LWC.CrosshairMode ? LWC.CrosshairMode.Normal : 0 },
      handleScroll: true, handleScale: true,
    });
    const candle = chart.addCandlestickSeries({
      upColor: "#4cd6b3", downColor: "#ff5d6c",
      borderUpColor: "#4cd6b3", borderDownColor: "#ff5d6c",
      wickUpColor: "#4cd6b3", wickDownColor: "#ff5d6c",
    });
    const vol = chart.addHistogramSeries({
      priceFormat: { type: "volume" }, priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    chartRef.current = chart;
    candleRef.current = candle;
    volRef.current = vol;

    const ro = typeof ResizeObserver !== "undefined"
      ? new ResizeObserver(() => {
          if (chartRef.current && el.clientWidth) chartRef.current.applyOptions({ width: el.clientWidth });
        })
      : null;
    if (ro) { ro.observe(el); roRef.current = ro; }

    return () => {
      if (roRef.current) { try { roRef.current.disconnect(); } catch (e) {} roRef.current = null; }
      try { chart.remove(); } catch (e) {}
      chartRef.current = null; candleRef.current = null; volRef.current = null;
      lineRef.current = {};   // chart.remove() 가 모든 series 파괴 — 참조만 비운다.
      strRef.current = null; strMaRef.current = null;
    };
  }, [H, compact]);

  // bars 변경 시 데이터 갱신(시각=자정 기준 초로 단조 증가 보장, 중복 t 는 마지막 우선).
  useEffect_simc(() => {
    const candle = candleRef.current, vol = volRef.current;
    if (!candle || !vol) return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const cData = [];
    const vData = [];
    let lastSec = -1;
    for (let i = 0; i < src.length; i++) {
      const b = src[i];
      let sec = _hmsToSec(b.t);
      if (sec <= lastSec) sec = lastSec + 1;  // 동일/역순 슬롯 방지(LWC 단조 증가 요구).
      lastSec = sec;
      const up = (b.c || 0) >= (b.o || 0);
      cData.push({ time: sec, open: b.o || b.c || 0, high: b.h || b.c || 0, low: b.l || b.c || 0, close: b.c || 0 });
      vData.push({ time: sec, value: b.vol || 0, color: up ? "rgba(76,214,179,0.4)" : "rgba(255,93,108,0.4)" });
    }
    try { candle.setData(cData); vol.setData(vData); } catch (e) {}
  }, [bars]);

  // 보조지표 라인 오버레이(MA5/20/60·VWAP·볼린저) — 토글에 따라 생성/갱신/제거.
  useEffect_simc(() => {
    const chart = chartRef.current;
    if (!chart || typeof chart.addLineSeries !== "function") return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const secs = _monotonicSecs(src);
    const lines = lineRef.current;

    // 토글에 따라 켜질 지표 키 집합. 서버 라인(ma/vwap/boll/vwapband)은 bar 필드,
    //   클라이언트 라인(ema)은 _simEma 로 계산해 src 위에 매핑한다.
    const active = {};
    if (ind.ma) { active.ma5 = 1; active.ma20 = 1; active.ma60 = 1; }
    if (ind.vwap) active.vwap = 1;
    if (ind.boll) { active.bb_up = 1; active.bb_mid = 1; active.bb_low = 1; }
    if (ind.vwapband) { active.vwap_up = 1; active.vwap_low = 1; }   // 서버 공급 필드.
    if (ind.ema) { active.ema12 = 1; active.ema26 = 1; }             // 클라이언트 계산.

    // 클라이언트 계산 EMA(12/26) — bar 필드가 아니므로 별도 배열로 준비.
    const emaData = {};
    if (ind.ema) {
      const e12 = _simEma(src, 12), e26 = _simEma(src, 26);
      emaData.ema12 = []; emaData.ema26 = [];
      for (let i = 0; i < src.length; i++) {
        if (e12[i] != null && isFinite(e12[i])) emaData.ema12.push({ time: secs[i], value: e12[i] });
        if (e26[i] != null && isFinite(e26[i])) emaData.ema26.push({ time: secs[i], value: e26[i] });
      }
    }

    // 비활성 라인 제거.
    Object.keys(lines).forEach(key => {
      if (!active[key]) {
        try { chart.removeSeries(lines[key]); } catch (e) {}
        delete lines[key];
      }
    });
    // 활성 라인 생성·갱신.
    Object.keys(active).forEach(key => {
      const st = _SIM_IND_STYLE[key];
      if (!st) return;
      if (!lines[key]) {
        try {
          lines[key] = chart.addLineSeries({
            color: st.color, lineWidth: st.width,
            lineStyle: st.dashed && window.LightweightCharts && window.LightweightCharts.LineStyle
              ? window.LightweightCharts.LineStyle.Dashed : 0,
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { return; }
      }
      // ema12/ema26 는 클라이언트 계산 배열, 그 외는 bar 필드.
      const data = (key === "ema12" || key === "ema26") ? (emaData[key] || []) : _lineData(src, secs, key);
      try { lines[key].setData(data); } catch (e) {}
    });
  }, [bars, ind.ma, ind.vwap, ind.boll, ind.ema, ind.vwapband]);

  // 체결강도 오버레이 — LWC 가 싣는 단 하나의 서브-시리즈(비대칭 패리티). 자체 priceScaleId +
  //   scaleMargins 로 캔들 페인 하단에 얇은 밴드를 카빙(0~200 스케일). strma 토글 시 MA5 도 함께.
  useEffect_simc(() => {
    const chart = chartRef.current;
    if (!chart || typeof chart.addLineSeries !== "function") return;
    const arr = (bars || []);
    const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
    const secs = _monotonicSecs(src);

    const ensureScale = () => {
      try { chart.priceScale("strength").applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } }); } catch (e) {}
    };
    // 체결강도 라인.
    if (ind.strength) {
      if (!strRef.current) {
        try {
          strRef.current = chart.addLineSeries({
            color: "#7c6cf0", lineWidth: 1.2, priceScaleId: "strength",
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { strRef.current = null; }
        ensureScale();
      }
      if (strRef.current) {
        const data = [];
        for (let i = 0; i < src.length; i++) {
          const s = src[i].strength;
          if (s != null && isFinite(s)) data.push({ time: secs[i], value: s });
        }
        try { strRef.current.setData(data); } catch (e) {}
      }
    } else if (strRef.current) {
      try { chart.removeSeries(strRef.current); } catch (e) {}
      strRef.current = null;
    }
    // 체결강도 MA5(클라이언트 _simStrengthMa) — strength+strma 둘 다 켜질 때만.
    if (ind.strength && ind.strma) {
      if (!strMaRef.current) {
        try {
          strMaRef.current = chart.addLineSeries({
            color: "#f0b35a", lineWidth: 1, priceScaleId: "strength",
            lineStyle: window.LightweightCharts && window.LightweightCharts.LineStyle
              ? window.LightweightCharts.LineStyle.Dashed : 0,
            priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
          });
        } catch (e) { strMaRef.current = null; }
        ensureScale();
      }
      if (strMaRef.current) {
        const ma = _simStrengthMa(src, 5);
        const data = [];
        for (let i = 0; i < src.length; i++) {
          if (ma[i] != null && isFinite(ma[i])) data.push({ time: secs[i], value: ma[i] });
        }
        try { strMaRef.current.setData(data); } catch (e) {}
      }
    } else if (strMaRef.current) {
      try { chart.removeSeries(strMaRef.current); } catch (e) {}
      strMaRef.current = null;
    }
  }, [bars, ind.strength, ind.strma]);

  // 신호 마커(매수▲/매도▼) — curT 이하 도달분만. nearest bar 시각에 스냅.
  useEffect_simc(() => {
    const candle = candleRef.current;
    if (!candle) return;
    const arr = bars || [];
    if (arr.length === 0) { try { candle.setMarkers([]); } catch (e) {} return; }
    // bar t → 단조 sec 매핑(setData 와 동일 규칙으로 재현).
    const secOf = [];
    let lastSec = -1;
    for (let i = 0; i < arr.length; i++) {
      let sec = _hmsToSec(arr[i].t);
      if (sec <= lastSec) sec = lastSec + 1;
      lastSec = sec; secOf.push(sec);
    }
    const nearestSec = (hms) => {
      let best = -1;
      for (let i = 0; i < arr.length; i++) { if (arr[i].t <= hms) best = i; else break; }
      return best >= 0 ? secOf[best] : null;
    };
    const markers = [];
    (signals || []).forEach((sig) => {
      if (curT == null || sig.buy_hms <= curT) {
        const s = nearestSec(sig.buy_hms);
        if (s != null) markers.push({ time: s, position: "belowBar", color: "#4cd6b3", shape: "arrowUp", text: "매수" });
      }
      if (curT == null || sig.sell_hms <= curT) {
        const s = nearestSec(sig.sell_hms);
        if (s != null) {
          const pct = (sig.profit_pct >= 0 ? "+" : "") + (sig.profit_pct || 0).toFixed(1) + "%";
          markers.push({ time: s, position: "aboveBar", color: "#ff5d6c", shape: "arrowDown", text: compact ? "" : pct });
        }
      }
    });
    markers.sort((a, b) => a.time - b.time);
    try { candle.setMarkers(markers); } catch (e) {}
  }, [signals, curT, bars, compact]);

  const lastBar = (bars && bars.length) ? bars[bars.length - 1] : null;
  return (
    <SimChartShell code={code} name={name} lastBar={lastBar} bars={bars}
                   signals={signals} curT={curT} compact={compact} engine="lwc"
                   indicators={ind}>
      <div ref={wrapRef} style={{ width: "100%", height: H }} />
    </SimChartShell>
  );
}

/* ─────────────── 순수 SVG 폴백 경로(줌/팬/크로스헤어 직접 구현) ─────────────── */
function SimCandleChartSVG({ bars, signals, curT, code, name, compact, indicators }) {
  const ind = indicators || _SIM_DEFAULT_INDICATORS;
  const [hover, setHover] = useState_simc(null);
  // 팬 오프셋(우측 끝에서 좌로 이동한 캔들 수) + 줌(보이는 캔들 수).
  const [zoom, setZoom] = useState_simc(0);     // 추가 확대 단계(0=기본 윈도우).
  const [pan, setPan] = useState_simc(0);       // 오른쪽 끝 기준 좌측 이동량.
  const dragRef = useRef_simc(null);
  const svgRef = useRef_simc(null);

  const allBars = bars || [];
  // 보이는 캔들 수: 기본 윈도우에서 zoom 단계만큼 축소(최소 20).
  const visCount = Math.max(20, Math.min(allBars.length || _SIM_WINDOW, _SIM_WINDOW - zoom * 40));
  // 윈도우 끝 인덱스(팬 적용). 최신이 우측.
  const endIdx = Math.max(visCount, allBars.length - pan);
  const startIdx = Math.max(0, endIdx - visCount);
  const view = useMemo_simc(() => allBars.slice(startIdx, endIdx), [bars, startIdx, endIdx]);

  const W = 880;
  const H = compact ? 220 : 340;
  const volH = compact ? 34 : 52;
  const strH = compact ? 24 : 34;
  const padL = 56, padR = 16, padT = 14;
  const gap = 8;
  const priceH = H - padT - volH - strH - gap * 2 - 22;
  const innerW = W - padL - padR;

  const n = view.length;
  const slot = n > 0 ? innerW / n : innerW;
  const candleW = Math.max(1, Math.min(14, slot * 0.66));
  const xCenter = (i) => padL + slot * (i + 0.5);

  const priceTop = padT;
  const priceBot = padT + priceH;
  const highs = view.map(b => b.h || b.c || 0);
  const lows = view.map(b => b.l || b.c || 0).filter(v => v > 0);
  const pMax = highs.length ? Math.max(...highs) : 1;
  const pMin = lows.length ? Math.min(...lows) : 0;
  const pRange = (pMax - pMin) || 1;
  const yPrice = (v) => priceBot - ((v - pMin) / pRange) * priceH;

  const volTop = priceBot + gap;
  const volBot = volTop + volH;
  const vMax = Math.max(1, ...view.map(b => b.vol || 0));
  const yVol = (v) => volBot - (v / vMax) * volH;

  const strTop = volBot + gap;
  const strBot = strTop + strH;
  const strVals = view.map(b => b.strength || 0);
  const sMax = Math.max(100, ...strVals);
  const yStr = (v) => strBot - (Math.min(v, sMax) / sMax) * strH;

  const tIndex = useMemo_simc(() => {
    const m = new Map();
    view.forEach((b, i) => m.set(b.t, i));
    return m;
  }, [view]);

  const nearestIdx = (hms) => {
    if (tIndex.has(hms)) return tIndex.get(hms);
    let best = -1;
    for (let i = 0; i < n; i++) { if (view[i].t <= hms) best = i; else break; }
    return best;
  };

  const strPath = useMemo_simc(() => {
    if (n < 2) return "";
    return view.map((b, i) =>
      `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yStr(b.strength || 0).toFixed(1)}`
    ).join(" ");
  }, [view, n, sMax]);

  // 클라이언트 계산 지표(EMA12/26, 체결강도 MA5, 거래량 MA5/20) — 순수 헬퍼로 버퍼 위 계산.
  //   토글 OFF 면 계산 자체를 생략(빈 배열)해 비용 0.
  const ema12 = useMemo_simc(() => ind.ema ? _simEma(view, 12) : [], [view, ind.ema]);
  const ema26 = useMemo_simc(() => ind.ema ? _simEma(view, 26) : [], [view, ind.ema]);
  const strMa = useMemo_simc(() => (ind.strength && ind.strma) ? _simStrengthMa(view, 5) : [], [view, ind.strength, ind.strma]);
  const volMa = useMemo_simc(() => ind.volma ? _simVolMa(view, [5, 20]) : {}, [view, ind.volma]);

  // 값 배열(bars 길이)→ y 매핑 path. null 구간 끊어 그림. yFn 으로 스케일 선택(가격/거래량/강도).
  const arrPath = (vals, yFn) => {
    if (!vals || n < 2) return "";
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) { started = false; continue; }
      d += `${started ? "L" : "M"} ${xCenter(i).toFixed(1)} ${yFn(v).toFixed(1)} `;
      started = true;
    }
    return d;
  };

  // MA 오버레이 path(MA5/20/60 — null 구간은 끊어 그린다).
  const maPath = (key) => {
    if (n < 2) return "";
    let d = "", started = false;
    view.forEach((b, i) => {
      const v = b[key];
      if (v == null) { started = false; return; }
      d += `${started ? "L" : "M"} ${xCenter(i).toFixed(1)} ${yPrice(v).toFixed(1)} `;
      started = true;
    });
    return d;
  };

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
    // 드래그 팬.
    if (dragRef.current != null) {
      const dxPx = (e.clientX - dragRef.current.x) * (W / rect.width);
      const dCandles = Math.round(dxPx / Math.max(1, slot));
      const next = Math.max(0, Math.min(allBars.length - visCount, dragRef.current.pan + dCandles));
      setPan(next);
    }
  };

  // 휠 줌(위로=확대). 기본 페이지 스크롤 막고 zoom 단계 조절.
  const onWheel = (e) => {
    e.preventDefault();
    setZoom(z => Math.max(0, Math.min(8, z + (e.deltaY < 0 ? 1 : -1))));
  };
  const onDown = (e) => { dragRef.current = { x: e.clientX, pan }; };
  const onUp = () => { dragRef.current = null; };

  const lastBar = (bars && bars.length) ? bars[bars.length - 1] : null;

  return (
    <SimChartShell code={code} name={name} lastBar={lastBar} bars={bars}
                   signals={signals} curT={curT} compact={compact} engine="svg"
                   indicators={ind}>
      <div className="chart-wrap">
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
             onMouseMove={onMove} onMouseLeave={() => { setHover(null); onUp(); }}
             onWheel={onWheel} onMouseDown={onDown} onMouseUp={onUp}
             style={{ cursor: dragRef.current ? "grabbing" : "crosshair" }}>
          <text className="chart-axis-text" x={padL - 8} y={priceTop + 8} textAnchor="end" fill="var(--ink-2)">
            {_simPriceTick(pMax)}
          </text>
          <text className="chart-axis-text" x={padL - 8} y={priceBot} textAnchor="end" fill="var(--ink-2)">
            {_simPriceTick(pMin)}
          </text>
          <line x1={padL} x2={W - padR} y1={priceBot} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />
          <line x1={padL} x2={padL} y1={priceTop} y2={priceBot} stroke="var(--line-2)" strokeWidth="1" />

          {/* MA 오버레이(5=teal점선, 20=amber, 60=violet) — 토글 ind.ma */}
          {n > 1 && ind.ma && <path d={maPath("ma5")} fill="none" stroke="var(--teal)" strokeWidth="1" opacity="0.5" strokeDasharray="3 2" />}
          {n > 1 && ind.ma && <path d={maPath("ma20")} fill="none" stroke="var(--amber)" strokeWidth="1.1" opacity="0.7" />}
          {n > 1 && ind.ma && <path d={maPath("ma60")} fill="none" stroke="var(--violet)" strokeWidth="1.1" opacity="0.6" />}
          {/* VWAP(금색 실선) — 토글 ind.vwap */}
          {n > 1 && ind.vwap && <path d={maPath("vwap")} fill="none" stroke="#ffd24c" strokeWidth="1.4" opacity="0.85" />}
          {/* VWAP 밴드(±1σ, 서버 vwap_up/vwap_low) — 토글 ind.vwapband */}
          {n > 1 && ind.vwapband && <path d={maPath("vwap_up")} fill="none" stroke="#ffd24c" strokeWidth="0.9" opacity="0.5" strokeDasharray="2 3" />}
          {n > 1 && ind.vwapband && <path d={maPath("vwap_low")} fill="none" stroke="#ffd24c" strokeWidth="0.9" opacity="0.5" strokeDasharray="2 3" />}
          {/* EMA12/26(클라이언트 _simEma) — 토글 ind.ema */}
          {n > 1 && ind.ema && <path d={arrPath(ema12, yPrice)} fill="none" stroke="#6fd6ff" strokeWidth="1" opacity="0.7" />}
          {n > 1 && ind.ema && <path d={arrPath(ema26, yPrice)} fill="none" stroke="#b07cf0" strokeWidth="1" opacity="0.7" />}
          {/* 볼린저(20,2) 상/중/하단(청색 점선) — 토글 ind.boll */}
          {n > 1 && ind.boll && <path d={maPath("bb_up")} fill="none" stroke="#5a93c8" strokeWidth="1" opacity="0.6" strokeDasharray="3 2" />}
          {n > 1 && ind.boll && <path d={maPath("bb_mid")} fill="none" stroke="#5a93c8" strokeWidth="0.9" opacity="0.45" strokeDasharray="2 3" />}
          {n > 1 && ind.boll && <path d={maPath("bb_low")} fill="none" stroke="#5a93c8" strokeWidth="1" opacity="0.6" strokeDasharray="3 2" />}

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
          {/* 거래량 MA5/20(클라이언트 _simVolMa) — 토글 ind.volma */}
          {n > 1 && ind.volma && <path d={arrPath(volMa.vol_ma5, yVol)} fill="none" stroke="#4cd6b3" strokeWidth="0.9" opacity="0.7" />}
          {n > 1 && ind.volma && <path d={arrPath(volMa.vol_ma20, yVol)} fill="none" stroke="#f0b35a" strokeWidth="0.9" opacity="0.6" />}
          <text className="chart-axis-text" x={padL - 8} y={volTop + 8} textAnchor="end" fill="var(--ink-3)">거래량</text>

          {/* 체결강도 서브라인(100 균형선) — 토글 ind.strength. strma 시 MA5 점선 오버레이. */}
          {ind.strength && <line x1={padL} x2={W - padR} y1={yStr(100)} y2={yStr(100)}
                stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="2 3" />}
          {n > 1 && ind.strength && <path d={strPath} fill="none" stroke="var(--violet)" strokeWidth="1.3" opacity="0.85" />}
          {n > 1 && ind.strength && ind.strma && <path d={arrPath(strMa, yStr)} fill="none" stroke="#f0b35a" strokeWidth="1" opacity="0.7" strokeDasharray="3 2" />}
          {ind.strength && <text className="chart-axis-text" x={padL - 8} y={strTop + 8} textAnchor="end" fill="var(--violet)">체결강도</text>}

          {/* 신호 마커 */}
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

          {/* 크로스헤어(수직+수평) */}
          {hover != null && view[hover] && (
            <g>
              <line x1={xCenter(hover)} x2={xCenter(hover)} y1={priceTop} y2={priceBot}
                    stroke="rgba(255,255,255,0.18)" strokeWidth="1" strokeDasharray="3 3" />
              <line x1={padL} x2={W - padR} y1={yPrice(view[hover].c || 0)} y2={yPrice(view[hover].c || 0)}
                    stroke="rgba(255,255,255,0.12)" strokeWidth="1" strokeDasharray="3 3" />
            </g>
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

        {/* 줌/팬 힌트 + 리셋 */}
        {n > 0 && (zoom > 0 || pan > 0) && (
          <button className="btn ghost sm" onClick={() => { setZoom(0); setPan(0); }}
                  style={{ position: "absolute", top: 10, left: 10, fontSize: 10, padding: "2px 7px" }}>
            ⤢ 리셋
          </button>
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
    </SimChartShell>
  );
}

/* ① 엔진 자동선택 래퍼 — LWC 가용 시 lightweight-charts, 아니면 SVG 폴백. */
function SimCandleChart(props) {
  const useLwc = useMemo_simc(() => _lwcAvailable(), []);
  return useLwc ? <SimCandleChartLWC {...props} /> : <SimCandleChartSVG {...props} />;
}

export { SimCandleChartLWC, SimCandleChartSVG, SimCandleChart };
