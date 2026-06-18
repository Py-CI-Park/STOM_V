/* Chart simulation tab — shared helpers/constants (split from simulation.jsx for the 800-line cap).
   무예외 fetch 헬퍼·WS URL·배속/엔진/분할 상수·localStorage 토글 로드/저장·반응형 그리드·
   WS frame→store bar 매퍼·날짜/숫자 포맷·신호 평탄화·SimViewBar 라벨 스타일·엔진 설명 행·
   변수 워치 정의/임계 평가 등 시뮬탭 sub-file 들이 공유하는 순수 유틸 묶음.

   소비처: sim-tab-controls / sim-tab-panels / sim-tab-root / simulation(배럴).
     각 sub-file 이 필요한 심볼만 골라 import 한다.

   stom-ui 전역(window._simTimeLabel 등)은 절대 import-변환하지 않는다(window 전역으로 호출).
   캔들 차트·체결 로그는 simulation-charts.jsx 의 순수 컴포넌트를 쓴다(별도 import).
*/
// Track Z — dual-safe ESM. React 훅 별칭을 한 파일에서 노출해 sub-file 이 공유한다(중복 선언 금지).
const {
  useState: useState_sim, useEffect: useEffect_sim,
  useCallback: useCallback_sim, useRef: useRef_sim, useMemo: useMemo_sim,
} = React;

// 무예외 fetch 헬퍼.
function _simFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 6000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

const _SIM_SPEEDS = [1, 5, 20, 60, 240, 600];
// WS frame item → store bar 필드 매핑(증분 "bars" 와 seek "history" 스냅샷이 공유).
const _simWsBar = (it, t) => ({
  t, o: it.o, h: it.h, l: it.l, c: it.c, vol: it.vol,
  change: it.change, strength: it.strength,
  ma5: it.ma5, ma20: it.ma20, ma60: it.ma60, imbalance: it.imbalance,
  buy_rest: it.buy_rest, sell_rest: it.sell_rest,
  vwap: it.vwap, vwap_up: it.vwap_up, vwap_low: it.vwap_low,
  bb_mid: it.bb_mid, bb_up: it.bb_up, bb_low: it.bb_low,
  net_qty: it.net_qty, bid1: it.bid1, ask1: it.ask1,
});
const _SIM_MAX_CODES = 10;                  // S2 동시보기 1~10(백엔드 replay_engine.MAX_CODES 와 일치).
const _SIM_DEMO_SPEED = 20;                 // 자동 데모 배속(빠른 둘러보기).
// 차트 엔진 모드 — 라이브(Canvas·기본) / LWC(lightweight-charts) / SVG(폴백 순수 SVG).
//   S4: "라이브" 가 기본. 멀티 비교용 overlay 는 별도 보기 모드(_SIM_VIEW_MODES)로 분리.
const _SIM_ENGINE_MODES = [["live", "라이브"], ["lwc", "LWC"], ["svg", "SVG"]];
const _SIM_ENGINE_LS_KEY = "stom.sim.engine.v1";
// 멀티차트 보기 모드 — split(분할 그리드) / overlay(정규화 한 차트 겹침).
const _SIM_CHART_MODES = [["split", "분할"], ["overlay", "오버레이"]];
// 분할 그리드 열(cols) 선택 1~5 + 행(rows) 캡 스테퍼. 단일 종목은 항상 1열.
const _SIM_SPLIT_LS_KEY = "stom.sim.split.v1";    // cols(1~5) 보존.
const _SIM_ROWS_LS_KEY = "stom.sim.rows.v1";      // rows 캡(0=자동·무제한) 보존.
const _SIM_MAX_SPLIT_COLS = 5;                    // 열 선택 상한(7.6).
const _SIM_IND_LS_KEY = "stom.sim.indicators.v1";
const _SIM_DEMO_LS_KEY = "stom.sim.demoSeen.v1";   // 데모 1회 시청 기억(매번 강제 금지).

// 데모 1회 시청 여부 — localStorage(무예외). 미지원 환경이면 '안 봄'으로 취급.
function _simDemoSeen() {
  try { return window.localStorage.getItem(_SIM_DEMO_LS_KEY) === "1"; }
  catch (e) { return false; }
}
function _simMarkDemoSeen() {
  try { window.localStorage.setItem(_SIM_DEMO_LS_KEY, "1"); } catch (e) {}
}

// 보조지표 토글 로드/저장(localStorage·무예외). 기본값은 charts 파일 전역 _SIM_DEFAULT_INDICATORS.
function _loadIndicators() {
  const def = window._SIM_DEFAULT_INDICATORS || { ma: true, vwap: true, boll: false };
  try {
    const raw = window.localStorage.getItem(_SIM_IND_LS_KEY);
    const obj = raw ? JSON.parse(raw) : null;
    if (obj && typeof obj === "object") return { ...def, ...obj };
  } catch (e) {}
  return { ...def };
}
function _saveIndicators(obj) {
  try { window.localStorage.setItem(_SIM_IND_LS_KEY, JSON.stringify(obj || {})); } catch (e) {}
}
// 분할 열(cols, 1~_SIM_MAX_SPLIT_COLS) 로드/저장. 미설정/이상값은 2(기존 기본).
function _loadSplitCols() {
  try {
    const v = parseInt(window.localStorage.getItem(_SIM_SPLIT_LS_KEY), 10);
    if (v >= 1 && v <= _SIM_MAX_SPLIT_COLS) return v;
    return 2;
  } catch (e) { return 2; }
}
function _saveSplitCols(v) {
  try { window.localStorage.setItem(_SIM_SPLIT_LS_KEY, String(v)); } catch (e) {}
}
// 분할 행(rows) 캡 로드/저장. 0=자동(무제한·종목수 기반 자동 행). 1 이상이면 그 행수로 캡(초과는 스크롤).
function _loadSplitRows() {
  try {
    const v = parseInt(window.localStorage.getItem(_SIM_ROWS_LS_KEY), 10);
    if (v >= 1 && v <= _SIM_MAX_CODES) return v;
    return 0;
  } catch (e) { return 0; }
}
function _saveSplitRows(v) {
  try { window.localStorage.setItem(_SIM_ROWS_LS_KEY, String(v)); } catch (e) {}
}
// 차트 엔진 모드(live/lwc/svg) 로드/저장. 기본 라이브(S4). LWC 부재 환경이어도 live/svg 동작.
function _loadEngineMode() {
  try {
    const v = window.localStorage.getItem(_SIM_ENGINE_LS_KEY);
    return (v === "lwc" || v === "svg" || v === "live") ? v : "live";
  } catch (e) { return "live"; }
}
function _saveEngineMode(v) {
  try { window.localStorage.setItem(_SIM_ENGINE_LS_KEY, String(v)); } catch (e) {}
}

// S2 자동 반응형 그리드 컬럼 수 — 동시 차트 개수에 따라(1→1, 2~4→2, 5~9→3, 10→4).
//   사용자가 분할열(1/2)을 강제하면 그 값 우선(단일 종목은 항상 1열).
function _responsiveCols(count) {
  if (count <= 1) return 1;
  if (count <= 4) return 2;
  if (count <= 9) return 3;
  return 4;
}

// baseUrl(http) → ws(ws/wss) URL.
function _wsUrl(baseUrl, path) {
  try {
    const u = new URL(baseUrl);
    u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
    u.pathname = (u.pathname.replace(/\/$/, "")) + path;
    return u.toString();
  } catch (e) {
    return null;
  }
}

function _simFmtDate(d) {
  const s = String(d);
  if (s.length === 8) return s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
  return s;
}

// 등락율(%) → 타일 배경색. 상승=빨강 계열, 하락=파랑 계열, 0=중립 회색. 농도는 |등락|로.
function _simTileColor(pct) {
  const v = Number(pct) || 0;
  const mag = Math.min(1, Math.abs(v) / 12);   // ±12% 에서 최대 농도 포화.
  const a = 0.12 + mag * 0.7;
  if (v > 0) return `rgba(255,93,108,${a.toFixed(3)})`;   // 상승 빨강(--red 계열).
  if (v < 0) return `rgba(56,140,255,${a.toFixed(3)})`;   // 하락 파랑.
  return "rgba(150,158,170,0.14)";                         // 보합 중립.
}

// SimViewBar 라벨 공통 스타일(7.0 가독성 — ink-3·10 → ink-1·11·600·자간).
//   styles.css 클래스 추가 없이 인라인(Shared 가 후속에서 추출할 수 있음).
const _SIM_VIEWBAR_LABEL = {
  fontSize: 11, color: "var(--ink-1)", fontWeight: 600, letterSpacing: ".3px",
};

// 엔진 비대칭 설명 팝오버 — 3엔진의 실제 역할/오더플로우 지원 차이를 표로 보여준다(7.2).
//   라이브=Canvas·기본·최경량·풀 오더플로우 / SVG=무의존 폴백·풀 오더플로우 /
//   LWC=전문 줌·크로스헤어·체결강도 오버레이만.
const _SIM_ENGINE_ROWS = [
  ["라이브", "Canvas·기본·최경량 · 풀 오더플로우(체결강도·호가·net-delta)"],
  ["SVG", "무의존 폴백 · 풀 오더플로우(체결강도·호가·net-delta)"],
  ["LWC", "전문 줌/크로스헤어 · 체결강도 오버레이만"],
];

// 종목별 신호를 단일 로그용 평탄화(매수 시각순 정렬).
function _flattenSignals(signals, codes) {
  const out = [];
  (codes || []).forEach(code => {
    (signals[code] || []).forEach(s => out.push({ ...s, code }));
  });
  out.sort((a, b) => a.buy_hms - b.buy_hms);
  return out;
}

// 숫자 포맷(현지화·자릿수). null/비유한은 "—".
function _simFmtNum(v, digits) {
  if (v == null) return "—";
  const n = Number(v);
  if (!isFinite(n)) return "—";
  return n.toLocaleString("ko-KR", { maximumFractionDigits: digits == null ? 0 : digits });
}

// 워치 가능한 변수 정의(키·라벨·소수 자릿수). buy/sell_rest 는 None 가능(부재 시 —).
const _SIM_WATCH_VARS = [
  { key: "c", label: "현재가", digits: 0 },
  { key: "change", label: "등락율", digits: 2 },
  { key: "strength", label: "체결강도", digits: 0 },
  { key: "vwap", label: "VWAP", digits: 0 },
  { key: "ma5", label: "MA5", digits: 0 },
  { key: "ma20", label: "MA20", digits: 0 },
  { key: "ma60", label: "MA60", digits: 0 },
  { key: "net_qty", label: "순매수수량", digits: 0 },
  { key: "imbalance", label: "호가불균형", digits: 2 },
  { key: "buy_rest", label: "매수총잔량", digits: 0 },
  { key: "sell_rest", label: "매도총잔량", digits: 0 },
];

const _SIM_WATCH_LS_KEY = "stom.sim.watch.v1";

function _loadWatchThresholds() {
  try {
    const raw = window.localStorage.getItem(_SIM_WATCH_LS_KEY);
    const obj = raw ? JSON.parse(raw) : null;
    return (obj && typeof obj === "object") ? obj : {};
  } catch (e) { return {}; }
}

function _saveWatchThresholds(map) {
  try { window.localStorage.setItem(_SIM_WATCH_LS_KEY, JSON.stringify(map || {})); } catch (e) {}
}

// 임계 충족 평가 — 값/임계 유효할 때만. {met:bool|null} (null=미설정/무값).
function _evalWatch(value, th) {
  if (!th || th.value === "" || th.value == null) return null;
  if (value == null) return null;
  const v = Number(value), t = Number(th.value);
  if (!isFinite(v) || !isFinite(t)) return null;
  return th.op === "<=" ? v <= t : v >= t;
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { useState_sim, useEffect_sim, useCallback_sim, useRef_sim, useMemo_sim, _simFetchJson, _SIM_SPEEDS, _simWsBar, _SIM_MAX_CODES, _SIM_DEMO_SPEED, _SIM_ENGINE_MODES, _SIM_ENGINE_LS_KEY, _SIM_CHART_MODES, _SIM_SPLIT_LS_KEY, _SIM_ROWS_LS_KEY, _SIM_MAX_SPLIT_COLS, _SIM_IND_LS_KEY, _SIM_DEMO_LS_KEY, _simDemoSeen, _simMarkDemoSeen, _loadIndicators, _saveIndicators, _loadSplitCols, _saveSplitCols, _loadSplitRows, _saveSplitRows, _loadEngineMode, _saveEngineMode, _responsiveCols, _wsUrl, _simFmtDate, _simTileColor, _SIM_VIEWBAR_LABEL, _SIM_ENGINE_ROWS, _flattenSignals, _simFmtNum, _SIM_WATCH_VARS, _SIM_WATCH_LS_KEY, _loadWatchThresholds, _saveWatchThresholds, _evalWatch };
