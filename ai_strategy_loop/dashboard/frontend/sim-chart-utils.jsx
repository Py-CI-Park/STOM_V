/* Chart simulation — shared helpers · constants (split from simulation-charts.jsx for the 800-line cap).
   Phase7 클라이언트 지표(순수 함수, 와이어 무변경) · 색/세션/호가단위 헬퍼 · 차트 윈도우 상수 묶음.
   엔진 경로(LWC · SVG)와 서브패인 · 셸 · 신호로그가 공유하는 단일 출처.

   소비처: sim-chart-engines · sim-chart-subpanes · sim-chart-shell · sim-signal-log · simulation-charts(배럴).
   각 파일이 필요한 심볼만 골라 import 한다.

   window 전역으로 공유: index.html(번들 엔트리 그래프)에서 simulation.jsx 보다 먼저 로드된다.
   stom-ui(번들) 호스팅 심볼은 window 별칭으로 둔다(_simTimeLabel / _simPriceTick) — import 전환 금지. */
const {
  useState: useState_simc, useRef: useRef_simc, useMemo: useMemo_simc,
  useEffect: useEffect_simc,
} = React;

// 최근 N 캔들 윈도우(SVG 폴백 렌더 부하 상한). LWC 는 전체를 주고 내장 팬/줌에 맡긴다.
const _SIM_WINDOW = 400;
// LWC 에 넘기는 누적 캔들 상한(과대 입력 방지 — 일일 데이터는 통상 이 안).
const _SIM_LWC_MAX = 5000;

// 보조지표 기본 토글 — 차트 위 라인 오버레이로 렌더(LWC addLineSeries / SVG path 동일).
//   기존: ma(MA5/20/60), vwap(VWAP), boll(볼린저 20,2 상/중/하단).
//   Phase7 신규(CROSS-FILE CONTRACT — Track B 와 동일 키 집합):
//     · 클라이언트 계산(버퍼 위 순수 함수, 와이어 무변경): ema(EMA12/26), rsi(RSI14),
//       macd(MACD 12/26/9), volma(거래량 MA 5/20), strma(체결강도 MA 5).
//     · 서버 공급(vwap_up/vwap_low 프레임 필드): vwapband(VWAP 밴드 ±1σ).
//     · 뷰 토글(별도 데이터 없음 — 그리기만): strength(체결강도 그래프), imbalance(호가 불균형),
//       orderflow(net-delta strip).
//   heavy 한 것들은 기본 OFF. strength 는 SVG 가 이미 그리므로 기본 ON.
const _SIM_DEFAULT_INDICATORS = {
  ma: true, vwap: true, boll: false,
  ema: false, rsi: false, macd: false, volma: false, strma: false,
  vwapband: false, strength: true, imbalance: false, orderflow: false,
};

// 지표별 색/스타일(LWC·SVG 공통 팔레트). dashed 는 SVG strokeDasharray·LWC LineStyle 매핑.
const _SIM_IND_STYLE = {
  ma5:    { color: "#4cd6b3", width: 1, dashed: true,  label: "MA5" },
  ma20:   { color: "#f0b35a", width: 1.1, dashed: false, label: "MA20" },
  ma60:   { color: "#7c6cf0", width: 1.1, dashed: false, label: "MA60" },
  vwap:   { color: "#ffd24c", width: 1.4, dashed: false, label: "VWAP" },
  bb_up:  { color: "#5a93c8", width: 1, dashed: true,  label: "BB+" },
  bb_mid: { color: "#5a93c8", width: 0.9, dashed: true, label: "BB" },
  bb_low: { color: "#5a93c8", width: 1, dashed: true,  label: "BB-" },
  // Phase7 — 클라이언트 계산 라인(EMA/VWAP밴드).
  ema12:    { color: "#6fd6ff", width: 1, dashed: false, label: "EMA12" },
  ema26:    { color: "#b07cf0", width: 1, dashed: false, label: "EMA26" },
  vwap_up:  { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP+" },
  vwap_low: { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP-" },
};

/* ─────────────── Phase7 클라이언트 지표 헬퍼 (CROSS-FILE CONTRACT) ───────────────
   bar 버퍼 위 순수 함수 — 동일 입력 ⇒ 동일 출력(엔진 간 발산 없음). 입력은 모두
   이미 프레임에 실려 오는 값(OHLCV + strength)이라 와이어 변경/서버 헬퍼가 필요 없다.
   각 헬퍼는 bars 와 같은 길이의 배열을 돌려준다(윈도우 미충족 구간은 null → 끊어 그림). */

// 단순이동평균(period) over selector(b)→number. 윈도우 미충족 구간 null.
function _simSma(bars, period, sel) {
  const out = new Array(bars.length).fill(null);
  let sum = 0, cnt = 0;
  const q = [];
  for (let i = 0; i < bars.length; i++) {
    const v = sel(bars[i]);
    const x = (v != null && isFinite(v)) ? v : null;
    q.push(x);
    if (x != null) { sum += x; cnt++; }
    if (q.length > period) {
      const drop = q.shift();
      if (drop != null) { sum -= drop; cnt--; }
    }
    out[i] = (q.length >= period && cnt === period) ? sum / period : null;
  }
  return out;
}

// 지수이동평균(period) over close. 첫 유효 close 를 seed, 이후 EMA 점화식.
function _simEma(bars, period) {
  const out = new Array(bars.length).fill(null);
  const k = 2 / (period + 1);
  let ema = null;
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i].c;
    if (c == null || !isFinite(c)) { out[i] = ema; continue; }
    ema = (ema == null) ? c : c * k + ema * (1 - k);
    out[i] = ema;
  }
  return out;
}

// RSI(Wilder, 기본 14) over close. 윈도우 미충족 구간 null.
function _simRsi(bars, period) {
  const p = period || 14;
  const out = new Array(bars.length).fill(null);
  let avgGain = null, avgLoss = null, prev = null;
  let seedG = 0, seedL = 0, seedN = 0;
  for (let i = 0; i < bars.length; i++) {
    const c = bars[i].c;
    if (c == null || !isFinite(c)) { out[i] = null; continue; }
    if (prev == null) { prev = c; out[i] = null; continue; }
    const ch = c - prev; prev = c;
    const gain = ch > 0 ? ch : 0, loss = ch < 0 ? -ch : 0;
    if (avgGain == null) {
      seedG += gain; seedL += loss; seedN++;
      if (seedN === p) { avgGain = seedG / p; avgLoss = seedL / p; }
      else { out[i] = null; continue; }
    } else {
      avgGain = (avgGain * (p - 1) + gain) / p;
      avgLoss = (avgLoss * (p - 1) + loss) / p;
    }
    const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + rs);
  }
  return out;
}

// MACD(12/26/9) over close → {macd[], signal[], hist[]} (각 bars 길이, null 패딩).
function _simMacd(bars) {
  const fast = _simEma(bars, 12);
  const slow = _simEma(bars, 26);
  const macd = bars.map((b, i) =>
    (fast[i] != null && slow[i] != null) ? fast[i] - slow[i] : null);
  // signal = MACD 의 9 EMA(유효 구간만 점화).
  const signal = new Array(bars.length).fill(null);
  const k = 2 / (9 + 1);
  let s = null;
  for (let i = 0; i < bars.length; i++) {
    const m = macd[i];
    if (m == null) { signal[i] = s; continue; }
    s = (s == null) ? m : m * k + s * (1 - k);
    signal[i] = s;
  }
  const hist = bars.map((b, i) =>
    (macd[i] != null && signal[i] != null) ? macd[i] - signal[i] : null);
  return { macd, signal, hist };
}

// 거래량 MA — periods(예 [5,20]) 각각의 SMA over b.vol → { ["vol_ma"+p]: number[] }.
function _simVolMa(bars, periods) {
  const ps = periods || [5, 20];
  const out = {};
  ps.forEach(p => { out["vol_ma" + p] = _simSma(bars, p, b => b.vol); });
  return out;
}

// 체결강도 MA — SMA(period=5) over b.strength. volMA 와 동일 계열의 클라이언트 계산.
function _simStrengthMa(bars, period) {
  return _simSma(bars, period || 5, b => b.strength);
}

// HHMMSS → HH:MM:SS · 가격 축약(원). P3 de-dup: 빌드 번들(stom-ui.js, format.ts)이
//   window._hmsTimeLabel/_priceTick 로 단일 출처 제공(ESM 모듈이라 babel/app.js 보다 먼저 로드).
//   babel 스코프 별칭만 둬서 기존 호출(_simTimeLabel/_simPriceTick)이 그대로 해소된다.
const _simTimeLabel = window._hmsTimeLabel;
const _simPriceTick = window._priceTick;

// HHMMSS(int) → 자정 기준 초(LWC time 축의 단조 증가 UTCTimestamp 로 사용).
function _hmsToSec(hms) {
  const s = String(hms).padStart(6, "0");
  return parseInt(s.slice(0, 2), 10) * 3600 + parseInt(s.slice(2, 4), 10) * 60 + parseInt(s.slice(4, 6), 10);
}

// 체결강도(0~200, 100=균형) → 색(낮음 파랑 → 100 중립 → 높음 빨강). 히트 스트립·밴드 공용.
function _strengthColor(v, alpha) {
  const a = alpha == null ? 1 : alpha;
  const s = Math.max(0, Math.min(200, v == null ? 100 : v));
  // 0→파랑(56,140,255), 100→회청(120,130,150), 200→빨강(240,80,80).
  let r, g, b;
  if (s <= 100) {
    const t = s / 100;
    r = Math.round(56 + (120 - 56) * t);
    g = Math.round(140 + (130 - 140) * t);
    b = Math.round(255 + (150 - 255) * t);
  } else {
    const t = (s - 100) / 100;
    r = Math.round(120 + (240 - 120) * t);
    g = Math.round(130 + (80 - 130) * t);
    b = Math.round(150 + (80 - 150) * t);
  }
  return `rgba(${r},${g},${b},${a})`;
}

function _lwcAvailable() {
  return typeof window !== "undefined" && window.LightweightCharts &&
    typeof window.LightweightCharts.createChart === "function";
}

/* ─────────────────────── 비주얼 추가 (Track C) ───────────────────────
   ① SimChangeGauge : 종목 등락율 반원 게이지(상승 빨강/하락 파랑, ±12% 포화).
   ② SimSessionRing : 세션 진행 링(09:00~15:30 대비 현재 시각 호 채움).
   ③ 신호 플래시    : 신호 도달 순간 차트 테두리 1회 플래시(SimChartShell 적용). */
const _SESSION_START_SEC = 9 * 3600;            // 09:00:00.
const _SESSION_END_SEC = 15 * 3600 + 30 * 60;   // 15:30:00.

// HHMMSS(int) 또는 None → 세션 진행률 0..1(09:00=0, 15:30=1, 범위 밖 클램프).
function _sessionProgress(hms) {
  if (hms == null) return 0;
  const sec = _hmsToSec(hms);
  const span = _SESSION_END_SEC - _SESSION_START_SEC;
  if (span <= 0) return 0;
  return Math.max(0, Math.min(1, (sec - _SESSION_START_SEC) / span));
}

// 등락율(%) → 게이지 색. 상승 빨강(--red), 하락 파랑, 0=중립 회색. 농도는 |등락|/12.
function _changeColor(pct) {
  const v = Number(pct) || 0;
  const mag = Math.min(1, Math.abs(v) / 12);
  const a = (0.35 + mag * 0.6).toFixed(3);
  if (v > 0) return `rgba(255,93,108,${a})`;
  if (v < 0) return `rgba(56,140,255,${a})`;
  return "rgba(150,158,170,0.5)";
}

// bar t → 자정 기준 단조 증가 초 매핑(LWC setData 와 동일 규칙: 동일/역순 슬롯 +1 보정).
function _monotonicSecs(bars) {
  const out = [];
  let lastSec = -1;
  for (let i = 0; i < bars.length; i++) {
    let sec = _hmsToSec(bars[i].t);
    if (sec <= lastSec) sec = lastSec + 1;
    lastSec = sec;
    out.push(sec);
  }
  return out;
}

// 지표 라인 데이터 추출 — bar[key] 가 null 인 구간은 건너뛴다(끊어 그림 → LWC whitespace).
function _lineData(bars, secs, key) {
  const out = [];
  for (let i = 0; i < bars.length; i++) {
    const v = bars[i][key];
    if (v == null || !isFinite(v)) continue;
    out.push({ time: secs[i], value: v });
  }
  return out;
}

/* ─────────────── footprint 오더플로우 헬퍼 (S3) ───────────────
   가격 레벨별 매수/매도 체결량 추정에 쓰는 순수 헬퍼. SimFootprint(sim-chart-subpanes)·
   net-delta(SimNetDeltaStrip · SimOrderFlowTape)가 공유. */
// Phase12-A — net_qty 유한값만(null=데이터없음·실제 0 모두 막대 없음, NaN 위험 제거).
function _simNq(b) { return (b && b.net_qty != null && isFinite(b.net_qty)) ? b.net_qty : 0; }

function _hoga_tick(price) {
  // 한국거래소 호가단위 근사(2023 개편 기준 단순화). 정확값 아님 — footprint 버킷팅용.
  const p = Math.abs(Number(price) || 0);
  if (p < 2000) return 1;
  if (p < 5000) return 5;
  if (p < 20000) return 10;
  if (p < 50000) return 50;
  if (p < 200000) return 100;
  if (p < 500000) return 500;
  return 1000;
}

function _bucketPrice(price, tick) {
  const t = tick || 1;
  return Math.round(Math.floor((Number(price) || 0) / t) * t);
}

// bar 한 개의 (buy, sell) 체결량 추정. real=net_qty 사용 여부.
function _barBuySell(bar) {
  const vol = (bar.vol != null && isFinite(bar.vol)) ? bar.vol : 0;
  const nq = bar.net_qty;
  if (nq != null && isFinite(nq)) {
    const buy = (vol + nq) / 2;
    const sell = (vol - nq) / 2;
    return { buy: Math.max(0, buy), sell: Math.max(0, sell), real: true };
  }
  // 휴리스틱 — 체결강도로 매수 점유율 근사(100=균형).
  const s = (bar.strength != null && isFinite(bar.strength)) ? bar.strength : 100;
  const buyShare = Math.max(0, Math.min(1, s / 200));
  return { buy: vol * buyShare, sell: vol * (1 - buyShare), real: false };
}

/* ─────────────── 멀티차트 오버레이 색 팔레트 ───────────────
   선택 종목들(≤4) 정규화 비교선 색. SimOverlayChart(sim-signal-log) 가 쓴다. */
const _SIM_OVERLAY_COLORS = ["#4cd6b3", "#ff5d6c", "#f0b35a", "#7c6cf0"];

export {
  useState_simc, useRef_simc, useMemo_simc, useEffect_simc,
  _SIM_WINDOW, _SIM_LWC_MAX, _SIM_DEFAULT_INDICATORS, _SIM_IND_STYLE,
  _simSma, _simEma, _simRsi, _simMacd, _simVolMa, _simStrengthMa,
  _simTimeLabel, _simPriceTick,
  _hmsToSec, _strengthColor, _lwcAvailable,
  _SESSION_START_SEC, _SESSION_END_SEC, _sessionProgress, _changeColor,
  _monotonicSecs, _lineData,
  _simNq, _hoga_tick, _bucketPrice, _barBuySell,
  _SIM_OVERLAY_COLORS,
};
