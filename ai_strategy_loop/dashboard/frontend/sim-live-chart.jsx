/* Chart simulation — 라이브 캔들 렌더러(S4, Phase6 Track S).
   외부 라이브러리 없는 자체 HTML5 Canvas 렌더러. window.SimLiveChart 전역으로 노출,
   simulation.jsx 가 차트 모드 "라이브"에서 SimCandleChart 대신 쓴다(LWC/SVG 는 유지).

   라이브 연출:
     - requestAnimationFrame 루프 — 최신(마지막) 캔들이 새 OHLC 로 lerp(~150ms) 성장.
     - 마지막 가격선 플래시(상승 teal / 하락 red) — 가격 변할 때 1회 점멸.
     - 거래량 히스토그램 서브패널이 캔들과 동기로 자란다.
     - 새 bar 도착 시 부드러운 오토스크롤(보이는 윈도우가 우측으로 미끄러짐).
     - 마우스 hover 크로스헤어 + OHLCV 리드아웃.
     - 매수▲/매도▼ 신호 마커(SimCandleChartLWC 와 동일 signals 모양: buy_hms/sell_hms…).
     - up/down 캔들 미세 글로우. devicePixelRatio 대응(레티나 선명).

   디자인 언어: 다크 테마 색(simulation-charts.jsx 팔레트와 동일 hex 사용 — CSS 변수는
   캔버스에서 못 읽으므로 hex 직접). 순수 in-browser Babel(import/export 금지·window 전역).
   index.html 에서 simulation.jsx 보다 먼저 로드돼야 한다(메인 통합 트랙이 script 태그 등록). */
const {
  useRef: useRef_slc, useEffect: useEffect_slc, useState: useState_slc,
} = React;

// 팔레트(캔버스 직접 hex — CSS 변수 불가). simulation-charts.jsx 와 동일 톤.
const _SLC_UP = "#4cd6b3";        // 상승(teal).
const _SLC_DOWN = "#ff5d6c";      // 하락(red).
const _SLC_INK1 = "#c8cdd7";
const _SLC_INK3 = "#6b7480";
const _SLC_GRID = "rgba(255,255,255,0.05)";
const _SLC_LINE = "rgba(255,255,255,0.10)";
const _SLC_BG = "transparent";

// 보이는 캔들 수(라이브 윈도우 — 오토스크롤로 최신이 우측). 과대 입력은 우측 N개로 한정.
const _SLC_WINDOW = 120;
// 봉이 적은 리플레이 초반에 봉들이 전체 폭으로 퍼져 윅만 두드러지는 왜곡 방지 —
//   최소 48슬롯 폭으로 왼쪽부터 채운다(실차트 관습). 렌더·히트테스트가 같은 식을 써야 한다.
const _SLC_MIN_SLOTS = 48;
function _slcSlot(innerW, n) { return innerW / Math.max(n, _SLC_MIN_SLOTS); }
// 최신 캔들 성장 lerp 시간(ms). 새 OHLC 도착 시 이 시간 동안 현재값→목표값 보간.
const _SLC_LERP_MS = 150;
// 마지막 가격선 플래시 지속(ms).
const _SLC_FLASH_MS = 220;

// HHMMSS(int) → HH:MM:SS (simulation-charts 의 _simTimeLabel 과 동일 규칙 — 독립 정의로 결합 회피).
function _slcTimeLabel(hms) {
  const s = String(hms == null ? 0 : hms).padStart(6, "0");
  return s.slice(0, 2) + ":" + s.slice(2, 4) + ":" + s.slice(4, 6);
}

function _slcPriceTick(v) {
  if (v == null || !isFinite(v)) return "—";
  return Math.round(v).toLocaleString("ko-KR");
}

// 선형 보간(현재→목표, 0..1 비율). t≥1 이면 목표 그대로.
function _lerp(from, to, t) {
  if (from == null || !isFinite(from)) return to;
  if (t >= 1) return to;
  return from + (to - from) * t;
}

/* 캔들 OHLC 를 보간한 스냅샷. 마지막 캔들만 성장 애니메이션, 나머지는 확정값. */
function _animatedBars(bars, lastAnim) {
  const n = bars.length;
  if (n === 0) return bars;
  // 마지막 캔들만 lastAnim(보간된 o/h/l/c)로 치환. 얕은 복사로 원본 불변.
  const out = bars.slice();
  if (lastAnim) {
    const base = out[n - 1];
    out[n - 1] = { ...base, o: lastAnim.o, h: lastAnim.h, l: lastAnim.l, c: lastAnim.c };
  }
  return out;
}

function SimLiveChart({ bars, signals, curT, code, name, compact }) {
  const canvasRef = useRef_slc(null);
  const wrapRef = useRef_slc(null);
  const rafRef = useRef_slc(0);
  // 애니메이션 상태(ref — 리렌더 유발 없이 rAF 루프가 갱신).
  const animRef = useRef_slc({
    // 마지막 캔들 보간 진행: target(새 OHLC) / from(직전 표시값) / startTs.
    lastTarget: null, lastFrom: null, lastStart: 0,
    prevClose: null, flashKind: null, flashStart: 0,
    prevLastT: null,          // 직전 마지막 bar 시각(새 bar 감지).
    scrollOffset: 0,          // 오토스크롤 보간용 진행(0..1) — 새 bar 시 0→1.
  });
  const barsRef = useRef_slc(bars || []);
  const sigRef = useRef_slc(signals || []);
  const curTRef = useRef_slc(curT);
  const compactRef = useRef_slc(!!compact);
  const [hover, setHover] = useState_slc(null);  // {x, idx} — 크로스헤어.
  const hoverRef = useRef_slc(null);

  const H = compact ? 220 : 340;

  // props → ref 미러링(rAF 루프가 stale 클로저로 안 보도록).
  useEffect_slc(() => {
    const arr = bars || [];
    const prev = barsRef.current;
    const a = animRef.current;
    const newLast = arr.length ? arr[arr.length - 1] : null;
    const prevLast = prev.length ? prev[prev.length - 1] : null;

    if (newLast) {
      const sameBar = prevLast && prevLast.t === newLast.t;
      // from = 직전 표시 OHLC(같은 bar 면 직전값, 새 bar 면 그 시가에서 시작).
      const from = sameBar && prevLast
        ? { o: prevLast.o, h: prevLast.h, l: prevLast.l, c: prevLast.c }
        : { o: newLast.o, h: newLast.o, l: newLast.o, c: newLast.o };
      a.lastFrom = from;
      a.lastTarget = { o: newLast.o, h: newLast.h, l: newLast.l, c: newLast.c };
      a.lastStart = (typeof performance !== "undefined" ? performance.now() : Date.now());
      // 종가 변화 → 플래시(상승/하락).
      if (a.prevClose != null && newLast.c !== a.prevClose) {
        a.flashKind = newLast.c >= a.prevClose ? "up" : "down";
        a.flashStart = a.lastStart;
      }
      a.prevClose = newLast.c;
      // 새 bar 도착 → 오토스크롤 보간 시작.
      if (!sameBar) { a.scrollOffset = 0; a.prevLastT = newLast.t; }
    }
    barsRef.current = arr;
  }, [bars]);

  useEffect_slc(() => { sigRef.current = signals || []; }, [signals]);
  useEffect_slc(() => { curTRef.current = curT; }, [curT]);
  useEffect_slc(() => { compactRef.current = !!compact; }, [compact]);

  // rAF 렌더 루프 — 마운트 1회 시작, 언마운트 시 취소.
  useEffect_slc(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const draw = () => {
      const now = (typeof performance !== "undefined" ? performance.now() : Date.now());
      _drawFrame(canvas, wrap, barsRef.current, sigRef.current, curTRef.current,
                 compactRef.current, animRef.current, hoverRef.current, now, H);
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [H]);

  // hover 좌표 → bar 인덱스. 보이는 윈도우 기준 역산.
  const onMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const layout = _layout(rect.width, H, compactRef.current);
    const arr = barsRef.current;
    const view = arr.length > _SLC_WINDOW ? arr.slice(arr.length - _SLC_WINDOW) : arr;
    const n = view.length;
    if (n === 0 || x < layout.padL || x > rect.width - layout.padR) { _setHover(null); return; }
    const slot = _slcSlot(rect.width - layout.padL - layout.padR, n);
    const i = Math.floor((x - layout.padL) / slot);
    if (i >= 0 && i < n) _setHover({ idx: i, base: arr.length - n }); else _setHover(null);
  };
  const _setHover = (h) => { hoverRef.current = h; setHover(h); };
  const onLeave = () => _setHover(null);

  const lastBar = (bars && bars.length) ? bars[bars.length - 1] : null;
  const arr = bars || [];
  const view = arr.length > _SLC_WINDOW ? arr.slice(arr.length - _SLC_WINDOW) : arr;
  const hoverBar = hover && view[hover.idx] ? view[hover.idx] : null;

  return (
    <div className="panel" style={{ minWidth: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          <span className="mono" style={{ fontSize: compact ? 11 : 12.5 }}>
            {code}{name ? " · " + name : ""}
          </span>
          <span className="mono" style={{ fontSize: 9, color: "var(--ink-3)", marginLeft: 6 }}>라이브</span>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {lastBar && (
            <span className="mono" style={{ fontSize: 11, color: lastBar.change >= 0 ? "var(--teal)" : "var(--red)" }}>
              {(lastBar.change || 0) >= 0 ? "+" : ""}{(lastBar.change || 0).toFixed(2)}%
            </span>
          )}
          {lastBar && (
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)" }}>
              {_slcPriceTick(lastBar.c)}
            </span>
          )}
        </div>
      </div>
      <div className="panel-bd">
        <div ref={wrapRef} className="chart-wrap" style={{ position: "relative", width: "100%", height: H }}>
          <canvas ref={canvasRef}
                  onMouseMove={onMove} onMouseLeave={onLeave}
                  style={{ width: "100%", height: H, display: "block", cursor: "crosshair" }} />
          {arr.length === 0 && (
            <div style={{
              position: "absolute", inset: 0, display: "flex", alignItems: "center",
              justifyContent: "center", color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
              pointerEvents: "none",
            }}>
              재생을 시작하면 라이브 캔들이 실시간으로 자라납니다
            </div>
          )}
          {hoverBar && (
            <div style={{
              position: "absolute", top: 10, right: 10, background: "var(--bg-0)",
              border: "1px solid var(--line-2)", borderRadius: 6, padding: "7px 9px",
              fontFamily: "var(--mono)", fontSize: 11, minWidth: 138, pointerEvents: "none",
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", marginBottom: 3 }}>
                {_slcTimeLabel(hoverBar.t)}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "1px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>시</span><span style={{ textAlign: "right" }}>{_slcPriceTick(hoverBar.o)}</span>
                <span style={{ color: "var(--ink-2)" }}>고</span><span style={{ textAlign: "right" }}>{_slcPriceTick(hoverBar.h)}</span>
                <span style={{ color: "var(--ink-2)" }}>저</span><span style={{ textAlign: "right" }}>{_slcPriceTick(hoverBar.l)}</span>
                <span style={{ color: "var(--ink-2)" }}>종</span><span style={{ textAlign: "right" }}>{_slcPriceTick(hoverBar.c)}</span>
                <span style={{ color: "var(--ink-2)" }}>량</span><span style={{ textAlign: "right" }}>{_slcPriceTick(hoverBar.vol)}</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* 레이아웃 상수(패딩·서브패널 높이). 캔들/거래량 영역 분할. */
function _layout(W, H, compact) {
  const padL = 52, padR = 14, padT = 12, padB = 20;
  const volH = compact ? 38 : 56;
  const gap = 8;
  const priceH = H - padT - padB - volH - gap;
  return { padL, padR, padT, padB, volH, gap, priceH };
}

/* 한 프레임 렌더 — devicePixelRatio 대응 + 보간 애니메이션. 순수(상태 변이는 anim ref 진행만). */
function _drawFrame(canvas, wrap, allBars, signals, curT, compact, anim, hover, now, H) {
  const cssW = wrap.clientWidth || 600;
  const cssH = H;
  const dpr = (typeof window !== "undefined" && window.devicePixelRatio) ? window.devicePixelRatio : 1;
  // 캔버스 백버퍼를 dpr 배율로(레티나 선명). CSS 크기는 그대로.
  const needW = Math.round(cssW * dpr);
  const needH = Math.round(cssH * dpr);
  if (canvas.width !== needW || canvas.height !== needH) {
    canvas.width = needW; canvas.height = needH;
  }
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, cssW, cssH);

  const arr = allBars || [];
  if (arr.length === 0) return;

  // 마지막 캔들 성장 보간(lerp).
  let lastAnim = null;
  if (anim.lastTarget && anim.lastFrom) {
    const t = Math.min(1, (now - anim.lastStart) / _SLC_LERP_MS);
    lastAnim = {
      o: _lerp(anim.lastFrom.o, anim.lastTarget.o, t),
      h: _lerp(anim.lastFrom.h, anim.lastTarget.h, t),
      l: _lerp(anim.lastFrom.l, anim.lastTarget.l, t),
      c: _lerp(anim.lastFrom.c, anim.lastTarget.c, t),
    };
  }
  const animated = _animatedBars(arr, lastAnim);
  const view = animated.length > _SLC_WINDOW ? animated.slice(animated.length - _SLC_WINDOW) : animated;
  const n = view.length;

  const L = _layout(cssW, cssH, compact);
  const innerW = cssW - L.padL - L.padR;
  const slot = _slcSlot(innerW, n);
  const candleW = Math.max(1, Math.min(13, slot * 0.64));
  const xCenter = (i) => L.padL + slot * (i + 0.5);

  // 가격 스케일.
  const priceTop = L.padT;
  const priceBot = L.padT + L.priceH;
  let pMax = -Infinity, pMin = Infinity;
  for (let i = 0; i < n; i++) {
    const b = view[i];
    pMax = Math.max(pMax, b.h || b.c || 0);
    const lo = b.l || b.c || 0;
    if (lo > 0) pMin = Math.min(pMin, lo);
  }
  if (!isFinite(pMax)) pMax = 1;
  if (!isFinite(pMin)) pMin = 0;
  const pRange = (pMax - pMin) || 1;
  const yPrice = (v) => priceBot - ((v - pMin) / pRange) * L.priceH;

  // 거래량 스케일.
  const volTop = priceBot + L.gap;
  const volBot = volTop + L.volH;
  let vMax = 1;
  for (let i = 0; i < n; i++) vMax = Math.max(vMax, view[i].vol || 0);
  const yVol = (v) => volBot - (v / vMax) * L.volH;

  // --- 그리드 + 축 라벨 ---
  ctx.font = "10px " + _slcFont();
  ctx.textBaseline = "middle";
  ctx.strokeStyle = _SLC_GRID; ctx.lineWidth = 1;
  ctx.fillStyle = _SLC_INK3; ctx.textAlign = "right";
  ctx.fillText(_slcPriceTick(pMax), L.padL - 6, priceTop + 4);
  ctx.fillText(_slcPriceTick(pMin), L.padL - 6, priceBot);
  ctx.beginPath(); ctx.moveTo(L.padL, priceBot); ctx.lineTo(cssW - L.padR, priceBot); ctx.stroke();
  ctx.fillText("거래량", L.padL - 6, volTop + 6);

  // --- 거래량 막대 ---
  for (let i = 0; i < n; i++) {
    const b = view[i];
    const up = (b.c || 0) >= (b.o || 0);
    const y = yVol(b.vol || 0);
    ctx.fillStyle = up ? "rgba(76,214,179,0.40)" : "rgba(255,93,108,0.40)";
    ctx.fillRect(xCenter(i) - candleW / 2, y, candleW, Math.max(0, volBot - y));
  }

  // --- 캔들 ---
  for (let i = 0; i < n; i++) {
    const b = view[i];
    const up = (b.c || 0) >= (b.o || 0);
    const color = up ? _SLC_UP : _SLC_DOWN;
    const cx = xCenter(i);
    const yHigh = yPrice(b.h || b.c || 0);
    const yLow = yPrice(b.l || b.c || 0);
    const yO = yPrice(b.o || b.c || 0);
    const yC = yPrice(b.c || 0);
    const top = Math.min(yO, yC);
    const bodyH = Math.max(1, Math.abs(yC - yO));
    const isLast = i === n - 1;
    // 마지막 캔들 미세 글로우(라이브 강조).
    if (isLast) { ctx.save(); ctx.shadowColor = color; ctx.shadowBlur = 8; }
    ctx.strokeStyle = color; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(cx, yHigh); ctx.lineTo(cx, yLow); ctx.stroke();
    ctx.fillStyle = color;
    ctx.fillRect(cx - candleW / 2, top, candleW, bodyH);
    if (isLast) ctx.restore();
  }

  // --- 지표 라인(MA/VWAP) — bars 가 서버 계산값(ma5/ma20/ma60·vwap)을 들고 있으면 그린다.
  //     null 구간은 끊어 그린다(윈도우 미충족). 라이브 모드는 핵심 추세선만(과밀 방지). ---
  _drawLine(ctx, view, xCenter, yPrice, "ma5", "#4cd6b3", 1, 0.5, n);
  _drawLine(ctx, view, xCenter, yPrice, "ma20", "#f0b35a", 1.1, 0.7, n);
  _drawLine(ctx, view, xCenter, yPrice, "ma60", "#7c6cf0", 1.1, 0.6, n);
  _drawLine(ctx, view, xCenter, yPrice, "vwap", "#ffd24c", 1.4, 0.85, n);

  // --- 마지막 가격선 + 플래시 ---
  const last = view[n - 1];
  const yLast = yPrice(last.c || 0);
  let lineColor = (last.c || 0) >= (last.o || 0) ? _SLC_UP : _SLC_DOWN;
  let lineAlpha = 0.55;
  if (anim.flashKind) {
    const ft = (now - anim.flashStart) / _SLC_FLASH_MS;
    if (ft < 1) {
      lineColor = anim.flashKind === "up" ? _SLC_UP : _SLC_DOWN;
      lineAlpha = 0.55 + (1 - ft) * 0.45;   // 점멸: 밝게 시작→감쇠.
    } else {
      anim.flashKind = null;
    }
  }
  ctx.save();
  ctx.globalAlpha = lineAlpha;
  ctx.strokeStyle = lineColor; ctx.lineWidth = 1; ctx.setLineDash([4, 3]);
  ctx.beginPath(); ctx.moveTo(L.padL, yLast); ctx.lineTo(cssW - L.padR, yLast); ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
  // 마지막가 가격 태그(우측).
  ctx.fillStyle = lineColor; ctx.globalAlpha = 1;
  ctx.fillRect(cssW - L.padR, yLast - 8, L.padR, 16);
  ctx.fillStyle = "#0c1014"; ctx.textAlign = "right"; ctx.font = "9px " + _slcFont();
  ctx.fillText(_slcPriceTick(last.c), cssW - 1, yLast + 1);

  // --- 신호 마커(매수▲/매도▼) — curT 이하만. nearest bar 스냅 ---
  const sigs = signals || [];
  ctx.textAlign = "center"; ctx.font = (compact ? 11 : 13) + "px " + _slcFont();
  for (let s = 0; s < sigs.length; s++) {
    const sig = sigs[s];
    if (curT == null || sig.buy_hms <= curT) {
      const bi = _nearestIdxInView(view, sig.buy_hms);
      if (bi >= 0) {
        ctx.fillStyle = _SLC_UP;
        ctx.fillText("▲", xCenter(bi), yPrice(sig.buy_price || view[bi].c) + (compact ? 13 : 15));
      }
    }
    if (curT == null || sig.sell_hms <= curT) {
      const si = _nearestIdxInView(view, sig.sell_hms);
      if (si >= 0) {
        ctx.fillStyle = _SLC_DOWN;
        ctx.fillText("▼", xCenter(si), yPrice(sig.sell_price || view[si].c) - (compact ? 6 : 8));
      }
    }
  }

  // --- 시간축 라벨(시작·중간·끝) ---
  ctx.fillStyle = _SLC_INK3; ctx.font = "9px " + _slcFont(); ctx.textAlign = "center";
  const tickIdx = n <= 1 ? [0] : [0, Math.floor(n / 2), n - 1];
  let lastLabelX = -Infinity;
  tickIdx.forEach((i) => {
    if (!view[i]) return;
    const lx = xCenter(i);
    if (lx - lastLabelX < 56) return;   // 라벨 폭(약 50px) 미만 간격이면 겹침 — 건너뛴다.
    lastLabelX = lx;
    ctx.fillText(_slcTimeLabel(view[i].t), lx, cssH - L.padB + 12);
  });

  // --- 크로스헤어(hover) ---
  if (hover && view[hover.idx]) {
    const cx = xCenter(hover.idx);
    const cyv = view[hover.idx].c || 0;
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.18)"; ctx.lineWidth = 1; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(cx, priceTop); ctx.lineTo(cx, priceBot); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(L.padL, yPrice(cyv)); ctx.lineTo(cssW - L.padR, yPrice(cyv)); ctx.stroke();
    ctx.restore();
  }
}

// 보이는 view 안에서 시각≤hms 인 가장 가까운 인덱스.
function _nearestIdxInView(view, hms) {
  let best = -1;
  for (let i = 0; i < view.length; i++) {
    if (view[i].t <= hms) best = i; else break;
  }
  return best;
}

// 지표 라인 그리기(키가 null 인 구간은 끊어 그림).
function _drawLine(ctx, view, xCenter, yPrice, key, color, width, alpha, n) {
  if (n < 2) return;
  ctx.save();
  ctx.globalAlpha = alpha; ctx.strokeStyle = color; ctx.lineWidth = width;
  ctx.beginPath();
  let started = false;
  for (let i = 0; i < n; i++) {
    const v = view[i][key];
    if (v == null || !isFinite(v)) { started = false; continue; }
    const x = xCenter(i), y = yPrice(v);
    if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
  }
  ctx.stroke();
  ctx.restore();
}

function _slcFont() {
  // mono 폰트 스택(캔버스는 CSS var 불가 — 안전 스택 직접).
  return "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
}

Object.assign(window, { SimLiveChart, _slcTimeLabel, _slcPriceTick });
