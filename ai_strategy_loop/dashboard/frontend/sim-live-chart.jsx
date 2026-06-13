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
// 재드로우 최소 간격(ms) — 약 35fps 캡. 차트 다수 활성 재생 시 CPU 포화 방지.
const _SLC_MIN_FRAME_MS = 28;

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

function SimLiveChart({ bars, signals, curT, code, name, compact, indicators }) {
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
    // Phase7 — 배치 도착 간 실제 경과(ms). lerp 를 min(_SLC_LERP_MS, batchWallMs)로 바운드해
    //   고속(240x/600x) 재생에서 보간이 배치가 대표하는 wall-time 을 넘지 않게 한다(1x=실시간 불변).
    prevArrival: 0, lerpMs: _SLC_LERP_MS,
    lastDrawTs: 0,            // 마지막 실제 재드로우 시각(프레임레이트 캡용).
  });
  const barsRef = useRef_slc(bars || []);
  const sigRef = useRef_slc(signals || []);
  const curTRef = useRef_slc(curT);
  const compactRef = useRef_slc(!!compact);
  const indRef = useRef_slc(indicators || null);
  const [hover, setHover] = useState_slc(null);  // {x, idx} — 크로스헤어.
  const hoverRef = useRef_slc(null);
  // 성능 — 더티 플래그. rAF 는 60fps 로 돌지만, 실제 캔버스 재드로우는
  //   ① 더티(데이터/지표/hover/리사이즈 변경) 또는 ② 진행 중 애니메이션(lerp·플래시·스크롤)
  //   일 때만 한다. 정지/유휴(다른 탭 keep-alive 포함) 시엔 그리지 않아 CPU/GPU 점유 0.
  //   초기 1회는 그려야 하므로 true 로 시작.
  const dirtyRef = useRef_slc(true);
  const markDirty = () => { dirtyRef.current = true; };

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
      const nowTs = (typeof performance !== "undefined" ? performance.now() : Date.now());
      // 배치 도착 간 실제 경과 = 이 배치가 대표하는 wall-time. lerp 를 이 값과 150ms 중
      //   작은 쪽으로 바운드 → 고속 재생에서 보간이 wall-time 을 넘기지 않음(1x=실시간 보존).
      const batchWallMs = a.prevArrival > 0 ? (nowTs - a.prevArrival) : _SLC_LERP_MS;
      a.lerpMs = Math.max(16, Math.min(_SLC_LERP_MS, batchWallMs));
      a.prevArrival = nowTs;
      a.lastStart = nowTs;
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
    markDirty();   // 새 배치 → 재드로우 필요.

    // MEDIUM-1: 배치 도착 시점에 클라이언트 지표 배열을 한 번만 계산해 animRef 에 캐시.
    //   rAF _drawFrame 은 60fps 로 돌지만 bar 데이터는 배치 단위로만 바뀐다.
    //   캐시를 여기서 갱신하고 draw 에서 참조하면 프레임당 재계산이 0 으로 줄어든다.
    //   window 전역(_simRsi/_simMacd/_simEma/_simVolMa/_simStrengthMa)은 simulation-charts.jsx 가
    //   이미 로드된 이후이므로 이 effect 호출 시점에는 반드시 정의돼 있다(load 순서 보장).
    const viewArr = arr.length > _SLC_WINDOW ? arr.slice(arr.length - _SLC_WINDOW) : arr;
    const ind = a.lastIndForCache || null;
    const rsiEnabled = !ind || ind.rsi !== false ? !!ind && !!ind.rsi : false;
    const macdEnabled = !ind || ind.macd !== false ? !!ind && !!ind.macd : false;
    const emaEnabled = !ind || ind.ema !== false ? !!ind && !!ind.ema : false;
    const volmaEnabled = !ind || ind.volma !== false ? !!ind && !!ind.volma : false;
    if (typeof window !== "undefined") {
      if (rsiEnabled && typeof window._simRsi === "function")
        a.cachedRsi = window._simRsi(viewArr, 14);
      if (macdEnabled && typeof window._simMacd === "function")
        a.cachedMacd = window._simMacd(viewArr);
      if (emaEnabled && typeof window._simEma === "function") {
        a.cachedEma12 = window._simEma(viewArr, 12);
        a.cachedEma26 = window._simEma(viewArr, 26);
      }
      if (volmaEnabled && typeof window._simVolMa === "function")
        a.cachedVolMa = window._simVolMa(viewArr, [5, 20]);
      if (typeof window._simStrengthMa === "function")
        a.cachedStrMa = window._simStrengthMa(viewArr, 5);
    }
  }, [bars]);

  useEffect_slc(() => { sigRef.current = signals || []; markDirty(); }, [signals]);
  useEffect_slc(() => { curTRef.current = curT; markDirty(); }, [curT]);
  useEffect_slc(() => { compactRef.current = !!compact; markDirty(); }, [compact]);
  useEffect_slc(() => {
    indRef.current = indicators || null;
    markDirty();   // 지표 토글 → 재드로우 필요.
    // indicators 변경 시에도 캐시를 즉시 재계산한다(토글 ON 시 다음 frame 부터 바로 그려짐).
    const a = animRef.current;
    a.lastIndForCache = indicators || null;
    const arr = barsRef.current;
    const viewArr = arr.length > _SLC_WINDOW ? arr.slice(arr.length - _SLC_WINDOW) : arr;
    const ind = indicators || null;
    if (typeof window !== "undefined" && viewArr.length > 0) {
      if (ind && ind.rsi && typeof window._simRsi === "function")
        a.cachedRsi = window._simRsi(viewArr, 14);
      if (ind && ind.macd && typeof window._simMacd === "function")
        a.cachedMacd = window._simMacd(viewArr);
      if (ind && ind.ema && typeof window._simEma === "function") {
        a.cachedEma12 = window._simEma(viewArr, 12);
        a.cachedEma26 = window._simEma(viewArr, 26);
      }
      if (ind && ind.volma && typeof window._simVolMa === "function")
        a.cachedVolMa = window._simVolMa(viewArr, [5, 20]);
      if (typeof window._simStrengthMa === "function")
        a.cachedStrMa = window._simStrengthMa(viewArr, 5);
    }
  }, [indicators]);

  // rAF 렌더 루프 — 마운트 1회 시작, 언마운트 시 취소.
  useEffect_slc(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;

    const draw = () => {
      rafRef.current = requestAnimationFrame(draw);
      // 가시성 게이트 — 다른 탭으로 전환된 keep-alive(display:none)면 offsetParent 가 null.
      //   숨김 상태에선 절대 그리지 않는다(차트 10개 × 60fps 영구 재드로우 → 전체 랙의 주원인).
      if (!wrap.offsetParent) return;
      const a = animRef.current;
      const now = (typeof performance !== "undefined" ? performance.now() : Date.now());
      // 진행 중 애니메이션이 있나? (마지막 캔들 lerp · 가격선 플래시) — 있으면 매 프레임 갱신.
      const animating =
        (!!a.lastTarget && (now - a.lastStart) < (a.lerpMs || _SLC_LERP_MS)) ||
        (!!a.flashKind && (now - a.flashStart) < _SLC_FLASH_MS);
      // 더티(데이터/지표/hover/리사이즈)도 애니도 없으면 재드로우 스킵 — 유휴 시 CPU 0.
      if (!dirtyRef.current && !animating) return;
      // 프레임레이트 캡(~35fps) — 차트 다수(분할 5~10) 활성 재생 시 60fps 풀 재드로우가
      //   CPU 를 포화시키는 것 방지. 더티는 소비 전이라 다음 프레임에 반드시 그려진다(유실 없음).
      if ((now - a.lastDrawTs) < _SLC_MIN_FRAME_MS) return;
      a.lastDrawTs = now;
      _drawFrame(canvas, wrap, barsRef.current, sigRef.current, curTRef.current,
                 compactRef.current, a, hoverRef.current, now, H,
                 indRef.current);
      // 애니메이션이 끝났고 더티만으로 그린 경우 → 더티 소비(다음 변경까지 유휴).
      if (!animating) dirtyRef.current = false;
    };
    rafRef.current = requestAnimationFrame(draw);
    // 컨테이너 크기 변경 시 재드로우 필요 — ResizeObserver 로 더티 표시.
    let ro = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(() => markDirty());
      try { ro.observe(wrap); } catch (e) { /* noop */ }
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      if (ro) { try { ro.disconnect(); } catch (e) { /* noop */ } }
    };
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
  const _setHover = (h) => { hoverRef.current = h; setHover(h); markDirty(); };
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

/* 레이아웃 상수(패딩·서브패널 높이). 캔들/거래량/하단 스트립 영역 분할.
   strips = 켜진 하단 서브패인 수(체결강도/호가불균형/net-delta/RSI/MACD) — 각 stripH 만큼 priceH 에서 차감. */
function _layout(W, H, compact, strips) {
  const padL = 52, padR = 14, padT = 12, padB = 20;
  const volH = compact ? 38 : 56;
  const gap = 8;
  const ns = strips || 0;
  const stripH = compact ? 22 : 30;
  const stripsTotal = ns > 0 ? ns * (stripH + gap) : 0;
  const priceH = H - padT - padB - volH - gap - stripsTotal;
  return { padL, padR, padT, padB, volH, gap, priceH, stripH };
}

/* 한 프레임 렌더 — devicePixelRatio 대응 + 보간 애니메이션. 순수(상태 변이는 anim ref 진행만).
   indicators(토글) 로 하단 서브패인(체결강도/호가불균형/net-delta — ASYMMETRIC: live 가 풀셋)
   과 EMA 오버레이를 그린다. 헬퍼(_simEma/_simStrengthMa)는 simulation-charts.jsx 의 window 전역. */
function _drawFrame(canvas, wrap, allBars, signals, curT, compact, anim, hover, now, H, indicators) {
  const ind = indicators || {};
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

  // 마지막 캔들 성장 보간(lerp). 보간 시간은 배치 wall-time 으로 바운드된 anim.lerpMs
  //   (= min(_SLC_LERP_MS, batchWallMs)) — 고속 재생에서 1x=실시간 비례 보존.
  let lastAnim = null;
  if (anim.lastTarget && anim.lastFrom) {
    const lerpMs = (anim.lerpMs && isFinite(anim.lerpMs)) ? anim.lerpMs : _SLC_LERP_MS;
    const t = Math.min(1, (now - anim.lastStart) / lerpMs);
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

  // 켜진 하단 서브패인 수(체결강도/호가불균형/net-delta/RSI/MACD) — 데이터 유무도 함께 본다.
  const hasStrength = ind.strength !== false;   // 기본 ON(SVG 와 동일).
  const hasImb = !!ind.imbalance && view.some(b =>
    (b.imbalance != null && isFinite(b.imbalance)) ||
    (b.buy_rest != null && b.sell_rest != null));
  const hasOf = !!ind.orderflow && view.some(b => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0);
  // RSI/MACD: 클라이언트 헬퍼가 window 에 있고 ind 토글이 켜졌을 때만. 데이터는 항상 충분(close 만 필요).
  const hasRsi = !!ind.rsi && typeof window !== "undefined" && typeof window._simRsi === "function";
  const hasMacd = !!ind.macd && typeof window !== "undefined" && typeof window._simMacd === "function";
  const strips = (hasStrength ? 1 : 0) + (hasImb ? 1 : 0) + (hasOf ? 1 : 0) + (hasRsi ? 1 : 0) + (hasMacd ? 1 : 0);

  const L = _layout(cssW, cssH, compact, strips);
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
  //     null 구간은 끊어 그린다(윈도우 미충족). 토글(ind.ma/ind.vwap) — 미지정(undefined)이면
  //     하위호환으로 ON 취급(기존 라이브 동작 보존). ---
  if (ind.ma !== false) {
    _drawLine(ctx, view, xCenter, yPrice, "ma5", "#4cd6b3", 1, 0.5, n);
    _drawLine(ctx, view, xCenter, yPrice, "ma20", "#f0b35a", 1.1, 0.7, n);
    _drawLine(ctx, view, xCenter, yPrice, "ma60", "#7c6cf0", 1.1, 0.6, n);
  }
  if (ind.vwap !== false) _drawLine(ctx, view, xCenter, yPrice, "vwap", "#ffd24c", 1.4, 0.85, n);
  // VWAP 밴드(서버 vwap_up/vwap_low) — ind.vwapband.
  if (ind.vwapband) {
    _drawLine(ctx, view, xCenter, yPrice, "vwap_up", "#ffd24c", 0.9, 0.5, n);
    _drawLine(ctx, view, xCenter, yPrice, "vwap_low", "#ffd24c", 0.9, 0.5, n);
  }
  // EMA12/26 — 배치 캐시(anim.cachedEma12/26) 사용. 배치 도착 시 한 번만 재계산(60fps 재계산 X).
  if (ind.ema) {
    _drawArrLine(ctx, anim.cachedEma12 || [], xCenter, yPrice, "#6fd6ff", 1, 0.7, n);
    _drawArrLine(ctx, anim.cachedEma26 || [], xCenter, yPrice, "#b07cf0", 1, 0.7, n);
  }
  // 거래량 MA5/20 — 배치 캐시(anim.cachedVolMa) 사용.
  if (ind.volma) {
    const vm = anim.cachedVolMa || {};
    _drawArrLine(ctx, vm.vol_ma5, xCenter, yVol, "#4cd6b3", 0.9, 0.7, n);
    _drawArrLine(ctx, vm.vol_ma20, xCenter, yVol, "#f0b35a", 0.9, 0.6, n);
  }

  // --- 하단 서브패인(체결강도 / 호가 불균형 / net-delta / RSI / MACD) — ASYMMETRIC: live 가 풀셋 ---
  let stripTop = volBot + L.gap;
  const stripRight = cssW - L.padR;
  if (hasStrength) {
    _drawStrengthStrip(ctx, view, xCenter, L, stripRight, stripTop, n, compact, ind, anim.cachedStrMa);
    stripTop += L.stripH + L.gap;
  }
  if (hasImb) {
    _drawImbalanceStrip(ctx, view, xCenter, L, stripRight, stripTop, n);
    stripTop += L.stripH + L.gap;
  }
  if (hasOf) {
    _drawNetDeltaStrip(ctx, view, xCenter, slot, L, stripRight, stripTop, n);
    stripTop += L.stripH + L.gap;
  }
  // RSI(0–100, Wilder 14기간) — 30/50/70 가이드선 + 폴리라인. LWC 제외(ASYMMETRIC PARITY).
  if (hasRsi) {
    const rsiVals = anim.cachedRsi || [];
    _drawRsiPane(ctx, rsiVals, xCenter, L, stripRight, stripTop, n);
    stripTop += L.stripH + L.gap;
  }
  // MACD(12/26/9) — 히스토그램 막대 + MACD 라인 + 시그널 라인. LWC 제외(ASYMMETRIC PARITY).
  if (hasMacd) {
    const macdData = anim.cachedMacd || {};
    _drawMacdPane(ctx, macdData, xCenter, slot, L, stripRight, stripTop, n);
    stripTop += L.stripH + L.gap;
  }

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

// 값 배열(view 길이) 라인 그리기(클라이언트 계산 지표 — EMA/volMA). null 구간 끊어 그림.
function _drawArrLine(ctx, vals, xCenter, yFn, color, width, alpha, n) {
  if (!vals || n < 2) return;
  ctx.save();
  ctx.globalAlpha = alpha; ctx.strokeStyle = color; ctx.lineWidth = width;
  ctx.beginPath();
  let started = false;
  for (let i = 0; i < n; i++) {
    const v = vals[i];
    if (v == null || !isFinite(v)) { started = false; continue; }
    const x = xCenter(i), y = yFn(v);
    if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
  }
  ctx.stroke();
  ctx.restore();
}

// 체결강도 스트립(Req 8) — strength 폴리라인 + 100 균형선, _strengthColor 로 채색.
//   strma 토글 시 배치 캐시 배열(cachedStrMa) 점선 오버레이.
function _drawStrengthStrip(ctx, view, xCenter, L, right, top, n, compact, ind, cachedStrMa) {
  const h = L.stripH;
  const bot = top + h;
  let sMax = 100;
  for (let i = 0; i < n; i++) sMax = Math.max(sMax, view[i].strength || 0);
  const yStr = (v) => bot - (Math.min(v, sMax) / sMax) * h;
  // 100 균형선.
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
  ctx.beginPath(); ctx.moveTo(L.padL, yStr(100)); ctx.lineTo(right, yStr(100)); ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
  // 강도 폴리라인 — _strengthColor(라이브 색 통일). window 전역(simulation-charts.jsx) 우선, 폴백 violet.
  const colorFn = (typeof window !== "undefined" && typeof window._strengthColor === "function")
    ? window._strengthColor : null;
  ctx.save();
  ctx.lineWidth = 1.3;
  if (n > 1) {
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < n; i++) {
      const s = view[i].strength;
      if (s == null || !isFinite(s)) { started = false; continue; }
      const x = xCenter(i), y = yStr(s);
      if (!started) { ctx.moveTo(x, y); started = true; } else { ctx.lineTo(x, y); }
    }
    ctx.strokeStyle = colorFn ? colorFn(view[n - 1].strength, 0.95) : "#7c6cf0";
    ctx.stroke();
  }
  ctx.restore();
  // strma — 체결강도 MA5 점선. cachedStrMa 는 배치 도착 시 갱신(60fps 재계산 X).
  if (ind && ind.strma && cachedStrMa) {
    _drawArrLine(ctx, cachedStrMa, xCenter, yStr, "#f0b35a", 1, 0.7, n);
  }
  // 라벨.
  ctx.save();
  ctx.fillStyle = "#7c6cf0"; ctx.font = "9px " + _slcFont(); ctx.textAlign = "right"; ctx.textBaseline = "middle";
  ctx.fillText("체결강도", L.padL - 6, top + 6);
  ctx.restore();
}

// 호가 불균형 스트립(Req 9) — imbalance(=매수/매도 총잔량비, 1.0=균형) 시계열 + 1.0 기준선.
function _drawImbalanceStrip(ctx, view, xCenter, L, right, top, n) {
  const h = L.stripH;
  const bot = top + h;
  const valOf = (b) => {
    if (b.imbalance != null && isFinite(b.imbalance)) return b.imbalance;
    const br = (b.buy_rest != null && isFinite(b.buy_rest)) ? b.buy_rest : null;
    const sr = (b.sell_rest != null && isFinite(b.sell_rest)) ? b.sell_rest : null;
    return (br != null && sr != null && sr > 0) ? br / sr : null;
  };
  let vMax = 2.0;
  for (let i = 0; i < n; i++) { const v = valOf(view[i]); if (v != null && isFinite(v)) vMax = Math.max(vMax, v); }
  const yImb = (v) => bot - (Math.min(v, vMax) / vMax) * h;
  // 1.0 균형선.
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.14)"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
  ctx.beginPath(); ctx.moveTo(L.padL, yImb(1.0)); ctx.lineTo(right, yImb(1.0)); ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
  _drawArrLine(ctx, view.map(valOf), xCenter, yImb, "#4cd6b3", 1.2, 0.85, n);
  ctx.save();
  ctx.fillStyle = _SLC_INK3; ctx.font = "9px " + _slcFont(); ctx.textAlign = "right"; ctx.textBaseline = "middle";
  ctx.fillText("호가불균형", L.padL - 6, top + 6);
  ctx.restore();
}

// net-delta 스트립(Req 7 in-chart orderflow) — bar 별 net_qty 히스토그램(>0 teal / <0 red).
function _drawNetDeltaStrip(ctx, view, xCenter, slot, L, right, top, n) {
  const h = L.stripH;
  const mid = top + h / 2;
  const half = h / 2 - 2;
  let maxAbs = 1;
  // Phase12-A — null(데이터 없음)과 실제 0(순매수 균형)을 구분: 둘 다 막대 없음으로
  //   그리되 || 0 (NaN 위험·의미 모호) 대신 유한값만 사용.
  const _nq = (b) => (b && b.net_qty != null && isFinite(b.net_qty)) ? b.net_qty : 0;
  for (let i = 0; i < n; i++) maxAbs = Math.max(maxAbs, Math.abs(_nq(view[i])));
  const barW = Math.max(1, slot * 0.7);
  // 0 기준선.
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(L.padL, mid); ctx.lineTo(right, mid); ctx.stroke();
  ctx.restore();
  for (let i = 0; i < n; i++) {
    const nq = _nq(view[i]);
    const bh = (Math.min(Math.abs(nq), maxAbs) / maxAbs) * half;
    const x = xCenter(i) - barW / 2;
    const y = nq >= 0 ? mid - bh : mid;
    ctx.fillStyle = nq > 0 ? "rgba(76,214,179,0.7)" : nq < 0 ? "rgba(255,93,108,0.7)" : "rgba(107,116,128,0.5)";
    ctx.fillRect(x, y, barW, Math.max(0.5, bh));
  }
  ctx.save();
  ctx.fillStyle = _SLC_UP; ctx.font = "9px " + _slcFont(); ctx.textAlign = "right"; ctx.textBaseline = "middle";
  ctx.fillText("net-delta", L.padL - 6, top + 6);
  ctx.restore();
}

// RSI 패인(Req 2, ASYMMETRIC: live+svg only, LWC 제외).
//   0–100 스케일, 30/50/70 가이드선(점선), RSI 폴리라인. null 구간 끊어 그림.
//   rsiVals 는 배치 캐시(anim.cachedRsi — view 길이와 동일).
function _drawRsiPane(ctx, rsiVals, xCenter, L, right, top, n) {
  const h = L.stripH;
  const bot = top + h;
  // y 변환: 0→bot, 100→top.
  const yRsi = (v) => bot - (Math.max(0, Math.min(100, v)) / 100) * h;
  // 30 / 50 / 70 가이드선.
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.10)"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]);
  [30, 50, 70].forEach(lv => {
    ctx.beginPath(); ctx.moveTo(L.padL, yRsi(lv)); ctx.lineTo(right, yRsi(lv)); ctx.stroke();
  });
  ctx.setLineDash([]);
  ctx.restore();
  // RSI 폴리라인(teal).
  _drawArrLine(ctx, rsiVals, xCenter, yRsi, "#4cd6b3", 1.2, 0.85, n);
  // 라벨.
  ctx.save();
  ctx.fillStyle = "#4cd6b3"; ctx.font = "9px " + _slcFont();
  ctx.textAlign = "right"; ctx.textBaseline = "middle";
  ctx.fillText("RSI(14)", L.padL - 6, top + 6);
  ctx.restore();
}

// MACD 패인(Req 2, ASYMMETRIC: live+svg only, LWC 제외).
//   zero-centered: 히스토그램 막대(hist) + MACD 라인(teal) + 시그널 라인(amber).
//   macdData 는 배치 캐시(anim.cachedMacd — {macd[], signal[], hist[]}, view 길이 동일).
function _drawMacdPane(ctx, macdData, xCenter, slot, L, right, top, n) {
  const h = L.stripH;
  const mid = top + h / 2;
  const half = h / 2 - 1;
  const macd = macdData.macd || [];
  const signal = macdData.signal || [];
  const hist = macdData.hist || [];
  // 스케일: hist 의 최대 절댓값 기준.
  let maxAbs = 1;
  for (let i = 0; i < n; i++) {
    const v = hist[i];
    if (v != null && isFinite(v)) maxAbs = Math.max(maxAbs, Math.abs(v));
  }
  const yMacd = (v) => (v == null || !isFinite(v)) ? mid : mid - (Math.max(-maxAbs, Math.min(maxAbs, v)) / maxAbs) * half;
  // 0 기준선.
  ctx.save();
  ctx.strokeStyle = "rgba(255,255,255,0.12)"; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(L.padL, mid); ctx.lineTo(right, mid); ctx.stroke();
  ctx.restore();
  // 히스토그램 막대(>0 teal / <0 red).
  const barW = Math.max(1, slot * 0.55);
  for (let i = 0; i < n; i++) {
    const v = hist[i];
    if (v == null || !isFinite(v)) continue;
    const bh = Math.abs(yMacd(v) - mid);
    const x = xCenter(i) - barW / 2;
    const y = v >= 0 ? mid - bh : mid;
    ctx.fillStyle = v > 0 ? "rgba(76,214,179,0.55)" : "rgba(255,93,108,0.55)";
    ctx.fillRect(x, y, barW, Math.max(0.5, bh));
  }
  // MACD 라인(teal 실선).
  _drawArrLine(ctx, macd, xCenter, yMacd, "#4cd6b3", 1.1, 0.9, n);
  // 시그널 라인(amber 점선).
  ctx.save();
  ctx.setLineDash([3, 2]);
  _drawArrLine(ctx, signal, xCenter, yMacd, "#f0b35a", 1, 0.8, n);
  ctx.setLineDash([]);
  ctx.restore();
  // 라벨.
  ctx.save();
  ctx.fillStyle = "#4cd6b3"; ctx.font = "9px " + _slcFont();
  ctx.textAlign = "right"; ctx.textBaseline = "middle";
  ctx.fillText("MACD", L.padL - 6, top + 6);
  ctx.restore();
}

function _slcFont() {
  // mono 폰트 스택(캔버스는 CSS var 불가 — 안전 스택 직접).
  return "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
}

Object.assign(window, { SimLiveChart, _slcTimeLabel, _slcPriceTick });
