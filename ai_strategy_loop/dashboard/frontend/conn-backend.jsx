/* Connection backend (split from connection.jsx for the thin-barrel pattern).
   REST + WS w/ auto-reconnect; falls back to local simulator for demo. 핵심 useBackend 훅 +
   기본 BASE(DEFAULT_BASE) + 초기상태(INITIAL_STATE) + 설정 스펙(DEFAULT_CONFIG_SPEC) + 데모
   시뮬레이터. demo 코드 생성기(genBuyCode/genSellCode)는 conn-demo-codegen.jsx 에서 import.
   window.useBackend / window.DEFAULT_BASE 로 노출(앱 전역 소비). LIVE↔DEMO 모드 분리:
   실제 WS onopen 시 demo 중단(stopDemo), contract_version 프레임=LIVE setState, action 프레임=
   제어 echo(lastReply) 라우팅. LIVE↔DEMO 필드 경계 판정 함수는 connection.jsx 배럴에 유지.
*/
// Track Z — dual-safe ESM import from the in-bundle definer. KEEP on ONE physical line.
import { genBuyCode, genSellCode } from "./conn-demo-codegen.jsx";

// 파일별 React 훅 별칭(dup-globals 가드: 한 번들 한 스코프라 bare `const {useState}=React` 가
//   여러 파일에 있으면 충돌). conn-backend 전용 접미사 _cn1.
const { useState: useState_cn1, useEffect: useEffect_cn1, useRef: useRef_cn1, useCallback: useCallback_cn1 } = React;

// 기본 BASE는 대시보드가 실제로 서빙된 origin(same-origin)으로 잡는다.
//   UI(/ui/)와 API(/health,/bt/...)가 같은 서버에서 제공되므로, origin을 쓰면
//   포트가 8770/8771 무엇이든 브라우저 fetch가 same-origin이 되어 CORS 차단·데모
//   폴백을 원천 차단한다. 과거 하드코딩(8770)은 8771 서빙 시 CORS로 데모모드에 갇혔다.
//   file:// 등 origin이 없을 때만 마지막 폴백으로 127.0.0.1:8770 사용.
const DEFAULT_BASE = (typeof window !== "undefined" &&
  window.location && window.location.origin &&
  window.location.origin.startsWith("http"))
  ? window.location.origin
  : "http://127.0.0.1:8770";

// ---------- WS 끊김 계측(UXR-P1 관측) ----------
// debounce(P2) 적용 전에 실제 끊김 빈도·원인을 근거로 남긴다(검토 §4: 장애 은폐 방지).
//   순수 관측 — 연결 동작을 바꾸지 않는다. 링버퍼 + window 미러(수동 점검용).
const _WS_DIAG_MAX = 200;
const _wsDiag = [];
function _recordWsDiag(entry) {
  try {
    const rec = Object.assign({ t: Date.now() }, entry);
    _wsDiag.push(rec);
    if (_wsDiag.length > _WS_DIAG_MAX) _wsDiag.splice(0, _wsDiag.length - _WS_DIAG_MAX);
    if (typeof window !== "undefined") window.__stomWsDiag = _wsDiag;
  } catch (e) {}
}
// 끊김 요약: 총 close/error, 우리가 닫은 것 제외, 최근 close code 분포.
function getWsDiag() {
  const closes = _wsDiag.filter(e => e.kind === "close" && !e.byUs);
  const errors = _wsDiag.filter(e => e.kind === "error");
  const codes = {};
  for (const c of closes) { const k = String(c.code == null ? "?" : c.code); codes[k] = (codes[k] || 0) + 1; }
  return { total: _wsDiag.length, unexpectedCloses: closes.length, errors: errors.length, codes, entries: _wsDiag.slice() };
}
// ---------- Default config spec (used if /config/spec is unavailable) ----------
const DEFAULT_CONFIG_SPEC = [
  // 목표/제약
  { name: "mdd_cap", label: "MDD 상한(%)", type: "number", default: 40, group: "목표/제약",
    min: 0, max: 40, help: "데모 기본값. 실제 LIVE 기본값은 /config/spec에서만 확정된다." },
  { name: "min_daily_trades", label: "일평균 거래 하한", type: "number", default: 0.5, group: "목표/제약",
    min: 0, help: "주 빈도 기준: daily_avg_trades = 거래수 / 거래일수." },
  { name: "min_trades", label: "최소 거래수(폴백)", type: "number", default: 30, group: "목표/제약",
    min: 0, help: "일평균 거래수가 없는 구형 결과에서만 쓰는 폴백." },
  { name: "target_score", label: "목표 적합도", type: "number", default: "", group: "목표/제약",
    min: 0, help: "비우면 조기 종료 없음. winner_score가 이 값 이상이면 졸업." },

  // 평가 스코프
  { name: "bt_timeframe", label: "백테스트 시간단위", type: "select", default: "min",
    options: ["min", "tick"], group: "평가 스코프",
    help: "분봉(min) 또는 틱(tick) 데이터 사용." },
  { name: "bt_scope", label: "백테스트 범위", type: "select", default: "universe",
    options: ["universe", "one_code"], group: "평가 스코프",
    help: "전체 유니버스 또는 단일 종목 평가." },
  { name: "bt_one_code", label: "단일 종목 코드", type: "text", default: "005930", group: "평가 스코프",
    help: "bt_scope=one_code일 때 사용할 종목코드(KOSPI/KOSDAQ 6자리)." },
  { name: "bt_window_days", label: "백테스트 윈도우(일)", type: "number", default: 60, group: "평가 스코프",
    help: "최근 N일 데이터로 백테스트 수행." },
  { name: "bt_start", label: "시작일(YYYYMMDD)", type: "text", default: "", group: "평가 스코프",
    help: "비우면 DB 최소 거래일." },
  { name: "bt_end", label: "종료일(YYYYMMDD)", type: "text", default: "", group: "평가 스코프",
    help: "비우면 DB 최대 거래일." },

  // 엔진 리소스
  { name: "engine_workers", label: "병렬 워커수", type: "number", default: 115, group: "엔진 리소스",
    min: 0, max: 128, help: "현재 128 logical CPU 기준 90% 상한 기본값. 0이면 자동." },
  { name: "engine_mem_cap_mb", label: "메모리 상한(MB)", type: "number", default: 8192, group: "엔진 리소스",
    min: 0, help: "호스트 메모리 기반 자동 상한. 0이면 자동." },
  { name: "engine_chunk_days", label: "청크 크기(일)", type: "number", default: 20, group: "엔진 리소스",
    min: 0, help: "한 워커가 처리할 백테스트 날짜 청크. 0이면 자동." },

  // 과적합 가드
  { name: "graduation_holdout", label: "졸업 홀드아웃", type: "boolean", default: false, group: "과적합 가드",
    help: "최종 게이트 통과 시, 별도 보류 구간(holdout)에서 추가 검증. 과적합 방지에 도움이 되나 시간이 더 소요됨." },

  // AI
  { name: "provider", label: "프로바이더", type: "select", default: "gpt_auth",
    options: ["gpt_auth", "openrouter", "codex_proxy"], group: "AI",
    help: "전략 생성에 사용할 LLM 제공자. LIVE에서는 /config/spec 값이 우선이다." },
  { name: "model", label: "모델", type: "select", default: "gpt-5.6-terra", group: "AI",
    options: ["gpt-5.6-terra", "gpt-5.6-sol", "gpt-5.6-luna", "gpt-5.5", "gpt-5.5-mini", "openai-codex/gpt-5.5"],
    help: "GPT 5.6-terra 기본. reasoning_effort로 표시." },
  { name: "reasoning_effort", label: "Reasoning effort", type: "select", default: "high", group: "AI",
    options: ["xhigh", "high", "medium", "low"], help: "기본 high. provider 미지원 시 상태로 표시." },
  { name: "max_generations", label: "최대 세대", type: "number", default: 200, group: "AI",
    help: "장기 연구 기본값. 스모크 검증은 1~2로 낮춰 실행." },
  { name: "feedback_window", label: "피드백 윈도우", type: "number", default: 8, group: "AI",
    help: "다음 세대에 전달할 최근 부검/실패 원인 개수." },
];
const CONFIG_SPEC_DEMO_STATUS = {
  source: "fallback_demo",
  live: false,
  message: "데모/오프라인 기본 설정입니다. 실제 진화 시작에는 /config/spec 연결이 필요합니다.",
};

function normalizeConfigSpecPayload(payload) {
  if (Array.isArray(payload) && payload.length) {
    return { fields: payload, status: { source: "live", live: true, contract_version: null, message: "array spec" } };
  }
  if (payload && typeof payload === "object" && Array.isArray(payload.fields) && payload.fields.length) {
    return {
      fields: payload.fields,
      status: {
        source: "live",
        live: true,
        contract_version: payload.contract_version ?? null,
        schema: payload.schema ?? "fields",
        message: "config spec loaded",
      },
    };
  }
  return { fields: [], status: { source: "missing", live: false, message: "config spec payload has no fields" } };
}

const INITIAL_STATE = {
  contract_version: 1,
  run_id: null,
  status: "idle",
  current_gen: 0,
  max_generations: 200,
  provider: "gpt_auth",
  bt_timeframe: "min",
  best: null,
  winner: null,
  generations: [],
  latest: { phase: "대기중", last_checkpoint: "—", message: "진화 시작 대기" },
  cumulative: { tokens: 0, cost_or_count: 0 },
  engine: {
    status: "idle",
    cpu_pct: 0,
    mem_mb: 0,
    mem_cap_mb: 8192,
    workers: 8,
    workers_active: 0,
    throughput: 0,        // candles/sec
    elapsed_ms: 0,
    eta_ms: 0,
    current_symbol: "—",
    current_window: { from: "—", to: "—" },
    progress: 0,          // 0..1 within current gen's backtest
    chunks_done: 0,
    chunks_total: 0,
  },
  current_run: {
    equity: [],           // [{ t, value }]   value in won; starts ~10,000,000
    drawdown: [],         // [{ t, value_pct }]
    trades: [],           // [{ t, side, price }]
    // Phase-detail streams
    generation: {
      active: null,                // "buy" | "sell" | "done"
      buy_code_partial: "",
      sell_code_partial: "",
      buy_done: false,
      sell_done: false,
      prompt_context: [],          // previous autopsies fed into LLM
      stream_tokens: 0,
    },
    scoring: {
      metrics: [],                 // [{ key, label, weight, value, ready }]
      composite: null,             // null while computing
    },
    autopsy: {
      text_partial: "",
      text_target: "",
      ready: false,
    },
  },
  updated_at: new Date().toISOString(),
};

// ---------- Hook ----------
function useBackend(baseUrl) {
  const [health, setHealth] = useState_cn1({ connected: false, contract_version: null });
  const [wsStatus, setWsStatus] = useState_cn1("connecting"); // connecting | open | reconnecting | demo
  const [state, setState] = useState_cn1(INITIAL_STATE);
  const [configSpec, setConfigSpec] = useState_cn1(DEFAULT_CONFIG_SPEC);
  const [configSpecStatus, setConfigSpecStatus] = useState_cn1(CONFIG_SPEC_DEMO_STATUS);
  // 제어 응답(start/stop/final_approval)의 마지막 결과. contract_version이 없는
  //   응답 프레임(=상태 스냅샷이 아닌 제어 echo)을 여기로 라우팅해 export 상태 등을
  //   UI가 표시할 수 있게 한다. final_approval(export) 게이트 결과 노출에 쓰인다.
  const [lastReply, setLastReply] = useState_cn1(null);

  const wsRef = useRef_cn1(null);
  const reconnectAttempt = useRef_cn1(0);
  const closedByUs = useRef_cn1(false);
  const demoRef = useRef_cn1(null);
  // UXR-P2 정직한 재연결 grace: 안정 연결의 단발 blip만 짧게 유예하고,
  //   열리자마자 닫히는 '플래핑'(예: 세션/권한 지속 실패)은 즉시 노출한다(은폐 금지).
  const lastOpenAt = useRef_cn1(0);
  const graceTimer = useRef_cn1(null);

  // ---- Demo simulator ----
  const startDemo = useCallback_cn1((config) => {
    stopDemo();
    setWsStatus("demo");
    const cfg = config || {};
    const max = Number(cfg.max_generations ?? 12);
    const target = Number((cfg.target_score === "" || cfg.target_score === null || cfg.target_score === undefined) ? 1.0 : cfg.target_score);
    const mddCap = Number(cfg.mdd_cap ?? 40);
    const minDailyTrades = Number(cfg.min_daily_trades ?? 0.5);
    const minTrades = Number(cfg.min_trades ?? 30);
    const workers = Number(cfg.engine_workers ?? 8);
    const memCap = Number(cfg.engine_mem_cap_mb ?? 8192);
    const startDate = normalizeDemoDate(cfg.bt_start || cfg.bt_start_date, "2025-03-01");
    const endDate = normalizeDemoDate(cfg.bt_end, null);
    const windowDays = endDate ? Math.max(1, Math.ceil((Date.parse(endDate) - Date.parse(startDate)) / 86400000) + 1) : Number(cfg.bt_window_days ?? 60);
    const provider = cfg.provider || "gpt_auth";
    const chunkDays = Number(cfg.engine_chunk_days ?? 5);

    let gen = 0;
    let best = null;
    let winner = null;
    let generations = [];
    let tokens = 0;
    let stepInGen = 0;

    // Phase boundaries (1-indexed step bounds)
    const STEP_BUY_END   = 5;
    const STEP_SELL_END  = 10;
    const STEP_BT_END    = 22;
    const STEP_SCORE_END = 26;
    const STEP_AUT_END   = 30;
    const STEPS_PER_GEN  = STEP_AUT_END;
    const TICK_MS = 300;

    const runId = "demo-" + Date.now().toString(36);
    const genStartedAt = { ms: Date.now() };

    // ---- Per-gen pre-computed plan ----
    let plan = null;          // { buyTag, sellTag, buyName, sellName, buy_code, sell_code, buy_lines, sell_lines, metrics, autopsy_text, target_trades, target_mdd, target_pnl }
    let currentRun = freshRun();
    let equityVal = 10_000_000;
    let equityHigh = equityVal;
    let runMinutes = 0;
    let currentSymbol = pickSymbol();
    let currentDay = 0;
    let totalChunks = Math.max(4, Math.ceil(windowDays / chunkDays));
    let chunksDone = 0;

    const feedbackPool = [
      "거래 0건 → 진입 조건 완화 (매수총잔량 임계 ↓20%)",
      "손실 구간에 매수총잔량이 평균보다 38% 높았음 → 기준 강화",
      "MDD 19.4% 초과 → 손절 트레일을 ATR×1.5로 타이트하게",
      "윈레이트 41% / 평균 손익비 0.8 → 익절 조건을 +2.4%로 상향",
      "거래 빈도 과다(평균 12회/일) → 신호 평활화(EMA 5→12)",
      "오버나잇 갭에서 손실 집중 → 종가 30분 전 강제 청산",
      "거래량 thin한 종목에서 슬리피지 누적 → 거래대금 ≥ 50억 필터 추가",
      "단기 모멘텀 과반응 → RSI 70 이상에서 신규 진입 차단",
    ];
    const gistPool = [
      "VWAP × 거래량가속 + RSI(14) 필터",
      "장중 거래대금 상위 10% & 5분 EMA 정배열",
      "프로그램 매수우위 + 외인순매수 전환",
      "OBV 발산 + 볼린저밴드 하단 반등",
      "5/20 골든크로스 + 거래량 200% 급증",
      "ATR-trailing stop, 진입 시 잔량비율 ≥ 1.6",
      "장초반 30분 박스 돌파 + 시초가 갭 < 0.6%",
      "호가창 매수총잔량/매도총잔량 비율 > 2.0",
    ];

    function freshRun() {
      return {
        equity: [],
        drawdown: [],
        trades: [],
        generation: {
          active: null,
          buy_code_partial: "",
          sell_code_partial: "",
          buy_done: false,
          sell_done: false,
          prompt_context: [],
          stream_tokens: 0,
        },
        scoring: { metrics: [], composite: null },
        autopsy: { text_partial: "", text_target: "", ready: false },
      };
    }
    function pickSymbol() {
      const samples = [
        ["005930", "삼성전자"], ["000660", "SK하이닉스"], ["035420", "NAVER"],
        ["051910", "LG화학"], ["207940", "삼성바이오로직스"], ["005380", "현대차"],
        ["068270", "셀트리온"], ["035720", "카카오"], ["096770", "SK이노베이션"],
        ["028260", "삼성물산"], ["323410", "카카오뱅크"], ["247540", "에코프로비엠"],
      ];
      return samples[Math.floor(Math.random() * samples.length)];
    }
    function dateAdd(base, days) {
      const d = new Date(base);
      d.setDate(d.getDate() + days);
      return d.toISOString().slice(0, 10);
    }
    function normalizeDemoDate(value, fallback) {
      if (value === null || value === undefined || value === "") return fallback;
      const text = String(value);
      if (/^\d{8}$/.test(text)) return `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6, 8)}`;
      return text || fallback;
    }
    function dailyAvg(trades) {
      return +(Number(trades || 0) / Math.max(1, Number(windowDays || 1))).toFixed(3);
    }
    function frequencyPass(trades) {
      const daily = dailyAvg(trades);
      return minDailyTrades > 0 ? daily >= minDailyTrades : Number(trades || 0) >= minTrades;
    }

    function buildPlan(genNo) {
      const buyTag = ["VWAP","MOM","ORB","FLOW","RSI","OBV"][Math.floor(Math.random()*6)];
      const sellTag = ["ATR","TRAIL","FIXED","PIVOT","TIME"][Math.floor(Math.random()*5)];
      const buyName = `BUY_${buyTag}_g${genNo + 1}`;
      const sellName = `SELL_${sellTag}_g${genNo + 1}`;
      const buy_code = genBuyCode(buyTag, genNo + 1);
      const sell_code = genSellCode(sellTag, genNo + 1);
      const buy_lines = buy_code.split("\n");
      const sell_lines = sell_code.split("\n");

      // Score that climbs slowly; sometimes hits target
      const climb = Math.min(0.92, 0.18 + (genNo + 1) / max * 0.85);
      const isErrorRoll = Math.random() < 0.06;
      let targetScore = isErrorRoll ? 0 : Math.max(0, climb + (Math.random() - 0.4) * 0.18);
      if (!isErrorRoll && genNo + 1 >= Math.floor(max * 0.55) && Math.random() < 0.22) {
        targetScore = +(target + Math.random() * 0.12).toFixed(3);
      }
      targetScore = +targetScore.toFixed(3);

      // Decompose into 4 weighted metrics that sum (roughly) to targetScore
      // weights: profit 0.40, mdd 0.20, trades 0.20, consistency 0.20
      const profitW = 0.40, mddW = 0.20, tradesW = 0.20, consW = 0.20;
      const profit_factor = isErrorRoll ? 0 : Math.max(0, targetScore + (Math.random() - 0.5) * 0.15);
      const mdd_score     = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.18));
      const trades_score  = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.20));
      const cons_score    = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.16));
      const metrics_def = [
        { key: "profit", label: "손익 (profit factor)", weight: profitW, value: +profit_factor.toFixed(3) },
        { key: "mdd",    label: "MDD 페널티",         weight: mddW,    value: +mdd_score.toFixed(3) },
        { key: "trades", label: "거래수 적정성",      weight: tradesW, value: +trades_score.toFixed(3) },
        { key: "cons",   label: "일관성 (sharpe-ish)", weight: consW,  value: +cons_score.toFixed(3) },
      ];

      // Trade count target
      const target_trades = isErrorRoll ? 0 : Math.max(0, Math.floor(profit_factor * 60 + (Math.random() - 0.3) * 20));
      const target_mdd_pct = isErrorRoll ? 0 : Math.max(2, Math.min(40, (1.4 - mdd_score) * 18 + (Math.random() - 0.5) * 4));
      // PnL target (pos/neg) tied to profit_factor
      const target_pnl = isErrorRoll ? 0 : Math.round((profit_factor - 0.4) * 3_500_000 + (Math.random() - 0.5) * 600_000);

      // Autopsy text
      const willPass = !isErrorRoll && targetScore >= target && target_mdd_pct <= mddCap && frequencyPass(target_trades);
      const autopsy_text = willPass
        ? `gen_${genNo + 1} — 하드 게이트 통과. graded_score=${targetScore.toFixed(3)} (target ${target.toFixed(2)}), MDD ${target_mdd_pct.toFixed(2)}% ≤ ${mddCap}%, 일평균 거래 ${dailyAvg(target_trades)}회/일 ≥ ${minDailyTrades}. 다음 세대는 동일 골격 유지하며 슬리피지 가정만 보수화.`
        : isErrorRoll
          ? `gen_${genNo + 1} — 런타임 예외. 안전한 컬럼 접근 및 None-가드 보강 필요. 다음 세대는 fallback 분기 추가.`
          : feedbackPool[Math.floor(Math.random() * feedbackPool.length)];

      // Prompt context = last 2 autopsies
      const lastAutopsies = generations
        .slice(-2)
        .map(g => `gen_${g.gen_no}: ${g.gate_reason !== "조건 충족" ? g.gate_reason : "통과"} (score ${g.graded_score})`);

      return {
        buyTag, sellTag, buyName, sellName,
        buy_code, sell_code, buy_lines, sell_lines,
        metrics_def, autopsy_text,
        target_trades, target_mdd_pct,
        target_pnl, target_score: targetScore,
        is_error: isErrorRoll,
        gist: gistPool[Math.floor(Math.random() * gistPool.length)],
        prompt_context: lastAutopsies,
      };
    }

    function resetGenRun(genNo) {
      currentRun = freshRun();
      plan = buildPlan(genNo);
      currentRun.generation.prompt_context = plan.prompt_context.slice();
      currentRun.generation.active = "buy";
      currentRun.autopsy.text_target = plan.autopsy_text;
      equityVal = 10_000_000;
      equityHigh = equityVal;
      runMinutes = 0;
      currentSymbol = pickSymbol();
      currentDay = 0;
      chunksDone = 0;
      genStartedAt.ms = Date.now();
    }

    // Initial setState
    resetGenRun(0);
    setState((s) => ({
      ...s,
      run_id: runId,
      status: "running",
      max_generations: max,
      current_gen: 0,
      provider,
      bt_timeframe: cfg.bt_timeframe ?? "min",
      best: null,
      winner: null,
      generations: [],
      latest: { phase: "생성중", last_checkpoint: "init", message: `세대 1 매수 조건식 생성 시작 (provider=${provider})` },
      cumulative: { tokens: 0, cost_or_count: 0 },
      engine: {
        status: "running",
        cpu_pct: 6, mem_mb: 320, mem_cap_mb: memCap,
        workers, workers_active: 0,
        throughput: 0, elapsed_ms: 0, eta_ms: STEPS_PER_GEN * TICK_MS,
        current_symbol: "—",
        current_window: { from: startDate, to: dateAdd(startDate, windowDays) },
        progress: 0, chunks_done: 0, chunks_total: totalChunks,
      },
      current_run: cloneCurrentRun(),
      updated_at: new Date().toISOString(),
    }));

    function cloneCurrentRun() {
      return {
        equity: currentRun.equity.slice(),
        drawdown: currentRun.drawdown.slice(),
        trades: currentRun.trades.slice(),
        generation: { ...currentRun.generation, prompt_context: currentRun.generation.prompt_context.slice() },
        scoring: { ...currentRun.scoring, metrics: currentRun.scoring.metrics.slice() },
        autopsy: { ...currentRun.autopsy },
      };
    }

    function tick() {
      tokens += Math.floor(Math.random() * 600 + 120);
      stepInGen += 1;

      const elapsedMs = Date.now() - genStartedAt.ms;
      const eta_ms = Math.max(0, (STEPS_PER_GEN - stepInGen) * TICK_MS);

      let phase, checkpoint, message;
      let cpu = 6, mem = 400, workersActive = 0, throughput = 0, progress = 0;

      if (stepInGen <= STEP_BUY_END) {
        // ===== 생성중 - buy code streaming =====
        phase = "생성중";
        const frac = stepInGen / STEP_BUY_END;
        const linesToShow = Math.max(1, Math.ceil(plan.buy_lines.length * frac));
        currentRun.generation.active = "buy";
        currentRun.generation.buy_code_partial = plan.buy_lines.slice(0, linesToShow).join("\n");
        currentRun.generation.buy_done = (linesToShow >= plan.buy_lines.length);
        currentRun.generation.stream_tokens = Math.round(tokens * 0.4);
        checkpoint = `BUY_${plan.buyTag} 코드 생성 (${linesToShow}/${plan.buy_lines.length} 라인)`;
        message = `LLM(${provider}) → 매수 조건식 스트리밍중`;
        cpu = 8 + Math.random() * 5;
        mem = 360 + stepInGen * 14;
      } else if (stepInGen <= STEP_SELL_END) {
        // ===== 생성중 - sell code streaming =====
        phase = "생성중";
        const sStep = stepInGen - STEP_BUY_END;
        const frac = sStep / (STEP_SELL_END - STEP_BUY_END);
        const linesToShow = Math.max(1, Math.ceil(plan.sell_lines.length * frac));
        currentRun.generation.active = "sell";
        currentRun.generation.buy_code_partial = plan.buy_code;
        currentRun.generation.buy_done = true;
        currentRun.generation.sell_code_partial = plan.sell_lines.slice(0, linesToShow).join("\n");
        currentRun.generation.sell_done = (linesToShow >= plan.sell_lines.length);
        currentRun.generation.stream_tokens = Math.round(tokens * 0.7);
        checkpoint = `SELL_${plan.sellTag} 코드 생성 (${linesToShow}/${plan.sell_lines.length} 라인)`;
        message = `LLM(${provider}) → 매도 조건식 스트리밍중`;
        cpu = 9 + Math.random() * 5;
        mem = 440 + sStep * 18;
        if (currentRun.generation.sell_done) {
          currentRun.generation.active = "done";
        }
      } else if (stepInGen <= STEP_BT_END) {
        // ===== 백테스트중 =====
        phase = "백테스트중";
        currentRun.generation.active = "done";
        currentRun.generation.buy_code_partial = plan.buy_code;
        currentRun.generation.sell_code_partial = plan.sell_code;
        currentRun.generation.buy_done = true;
        currentRun.generation.sell_done = true;

        const btStep = stepInGen - STEP_SELL_END;
        const btTotal = STEP_BT_END - STEP_SELL_END;
        progress = btStep / btTotal;
        chunksDone = Math.min(totalChunks, Math.floor(progress * totalChunks));
        cpu = 60 + Math.random() * 30;
        mem = 1600 + progress * 2600 + Math.random() * 200;
        workersActive = Math.min(workers, Math.max(2, Math.round(workers * (0.55 + Math.random() * 0.45))));
        throughput = Math.round(7500 + Math.random() * 9500);

        // Change symbol occasionally
        if (btStep === 1 || Math.random() < 0.25) currentSymbol = pickSymbol();
        currentDay = Math.floor(progress * windowDays);
        checkpoint = `chunk ${chunksDone}/${totalChunks} · ${currentSymbol[0]} ${currentSymbol[1]}`;
        message = `백테스트 진행 — ${dateAdd(startDate, currentDay)} 처리중, 워커 ${workersActive}/${workers} 가동`;

        // Build out equity & drawdown. Bias toward plan.target_pnl
        // Each tick adds ~25 candles, total ~12 ticks → 300 candles
        const candlesPerTick = 25;
        const expectedFinalEquity = 10_000_000 + plan.target_pnl;
        const remainingTicks = btTotal - btStep + 1;
        for (let i = 0; i < candlesPerTick; i++) {
          runMinutes += 1;
          // Drift toward expected final equity over remaining ticks
          const drift = (expectedFinalEquity - equityVal) / Math.max(1, remainingTicks * candlesPerTick);
          const noise = (Math.random() - 0.5) * 12000;
          equityVal = Math.max(equityVal + drift + noise, 10_000_000 * 0.7);
          if (equityVal > equityHigh) equityHigh = equityVal;
          const dd = (equityHigh - equityVal) / equityHigh * 100;
          currentRun.equity.push({ t: runMinutes, value: Math.round(equityVal) });
          currentRun.drawdown.push({ t: runMinutes, value_pct: +dd.toFixed(3) });
          if (Math.random() < 0.022) {
            const side = Math.random() < 0.52 ? "buy" : "sell";
            currentRun.trades.push({ t: runMinutes, side, price: equityVal });
          }
        }
      } else if (stepInGen <= STEP_SCORE_END) {
        // ===== 채점중 =====
        phase = "채점중";
        const sStep = stepInGen - STEP_BT_END;
        // Reveal one metric per step
        const metrics = currentRun.scoring.metrics;
        const def = plan.metrics_def;
        if (metrics.length < def.length && sStep <= def.length) {
          metrics.push({ ...def[sStep - 1], ready: true });
        }
        // After last metric, compute composite
        if (sStep === STEP_SCORE_END - STEP_BT_END) {
          // composite at last tick
          let comp = 0;
          for (const m of metrics) comp += m.value * m.weight;
          currentRun.scoring.composite = +comp.toFixed(3);
        }
        checkpoint = `metric ${Math.min(sStep, def.length)}/${def.length} 채점`;
        message = `지표 계산 — ${sStep <= def.length ? def[sStep - 1].label : "composite score"}`;
        cpu = 22 + Math.random() * 10;
        mem = 1200 + Math.random() * 200;
        workersActive = 2;
      } else {
        // ===== 부검 작성 =====
        phase = "부검 작성";
        const aStep = stepInGen - STEP_SCORE_END;
        const aTotal = STEP_AUT_END - STEP_SCORE_END;
        const fullText = plan.autopsy_text || "";
        const charsToShow = Math.ceil(fullText.length * (aStep / aTotal));
        currentRun.autopsy.text_partial = fullText.slice(0, charsToShow);
        currentRun.autopsy.ready = (aStep >= aTotal);
        checkpoint = `autopsy ${charsToShow}/${fullText.length} chars`;
        message = `다음 세대 컨텍스트에 주입할 부검 요약 작성중...`;
        cpu = 10 + Math.random() * 5;
        mem = 800 + Math.random() * 100;
        workersActive = 1;
      }

      // Push state update
      setState((s) => ({
        ...s,
        latest: { phase, last_checkpoint: checkpoint, message },
        cumulative: { tokens, cost_or_count: +(tokens * 0.000015).toFixed(4) },
        engine: {
          status: "running",
          cpu_pct: +cpu.toFixed(1),
          mem_mb: Math.round(mem),
          mem_cap_mb: memCap,
          workers, workers_active: workersActive,
          throughput,
          elapsed_ms: elapsedMs,
          eta_ms,
          current_symbol: phase === "백테스트중" ? `${currentSymbol[0]} ${currentSymbol[1]}` : "—",
          current_window: phase === "백테스트중"
            ? { from: dateAdd(startDate, currentDay), to: dateAdd(startDate, Math.min(windowDays, currentDay + chunkDays)) }
            : { from: startDate, to: dateAdd(startDate, windowDays) },
          progress,
          chunks_done: chunksDone,
          chunks_total: totalChunks,
        },
        current_run: cloneCurrentRun(),
        updated_at: new Date().toISOString(),
      }));

      // Finalize at end of cycle
      if (stepInGen >= STEPS_PER_GEN) {
        finalizeGen();
      }
    }

    function finalizeGen() {
      gen += 1;
      const isError = plan.is_error;
      const trade_count = isError ? 0 : Math.max(currentRun.trades.length, plan.target_trades);
      const final_equity = currentRun.equity.length ? currentRun.equity[currentRun.equity.length - 1].value : 10_000_000;
      const profit = isError ? 0 : Math.round(final_equity - 10_000_000);

      // Final MDD: max of drawdown curve
      const peakDD = currentRun.drawdown.length
        ? Math.max(0, ...currentRun.drawdown.map(p => p.value_pct))
        : plan.target_mdd_pct;
      const mdd = +Math.min(40, Math.max(plan.target_mdd_pct, peakDD)).toFixed(2);

      const graded_score = isError ? 0 : (currentRun.scoring.composite ?? plan.target_score);
      const gate_passed = !isError && graded_score >= target && mdd <= mddCap && frequencyPass(trade_count);

      let gate_reason = "조건 충족";
      if (isError) gate_reason = "실행 오류";
      else if (trade_count === 0) gate_reason = "거래 0건";
      else if (!frequencyPass(trade_count)) gate_reason = minDailyTrades > 0 ? `일평균 거래 부족(${dailyAvg(trade_count)}/${minDailyTrades})` : `거래수 부족(${trade_count}/${minTrades})`;
      else if (mdd > mddCap) gate_reason = `MDD 초과(${mdd}% > ${mddCap}%)`;
      else if (graded_score < target) gate_reason = `점수 미달(${graded_score.toFixed(3)} < ${target})`;

      const gist = plan.gist + " — " + (isError ? "런타임 예외" : `진입 ${trade_count}회, MDD ${mdd}%`);

      const newGen = {
        gen_no: gen,
        status: isError ? "error" : "success",
        graded_score: +graded_score.toFixed(3),
        gate_passed, gate_reason,
        trade_count, mdd, profit,
        daily_avg_trades: dailyAvg(trade_count),
        strategy_gist: gist,
        buy_name: plan.buyName, sell_name: plan.sellName,
        buy_code: plan.buy_code, sell_code: plan.sell_code,
        equity_curve: currentRun.equity.slice(),
        drawdown_curve: currentRun.drawdown.slice(),
        trades: currentRun.trades.slice(),
        score_breakdown: currentRun.scoring.metrics.slice(),
        autopsy: plan.autopsy_text,
      };
      generations = [...generations, newGen];

      if (!isError && (!best || graded_score > best.graded_score)) {
        best = { gen, graded_score: newGen.graded_score, gate_passed, buy_name: plan.buyName, sell_name: plan.sellName };
      }
      if (gate_passed && !winner) {
        winner = { gen, score: newGen.graded_score, buy_name: plan.buyName, sell_name: plan.sellName };
      }

      const done = gen >= max;

      setState((s) => ({
        ...s,
        current_gen: gen,
        generations,
        best,
        winner,
        latest: {
          phase: done ? "완료" : "생성중",
          last_checkpoint: `gen_${gen} 종료`,
          message: plan.autopsy_text,
        },
        engine: { ...s.engine,
          status: done ? "idle" : "running",
          cpu_pct: done ? 4 : s.engine.cpu_pct,
          workers_active: done ? 0 : s.engine.workers_active,
          throughput: done ? 0 : s.engine.throughput,
          progress: 1, chunks_done: totalChunks,
        },
        status: done ? "complete" : "running",
        updated_at: new Date().toISOString(),
      }));

      if (done) {
        stopDemo();
        return;
      }
      // Prep next gen
      stepInGen = 0;
      resetGenRun(gen);
    }

    demoRef.current = setInterval(tick, TICK_MS);
  }, []); // eslint-disable-line

  const stopDemo = () => {
    if (demoRef.current) {
      clearInterval(demoRef.current);
      demoRef.current = null;
    }
  };

  const stopDemoSoft = useCallback_cn1(() => {
    // emulate "stopping after current gen"
    setState((s) => ({ ...s, status: "stopping", latest: { ...s.latest, message: "현재 세대 완료 후 정지합니다" } }));
    setTimeout(() => {
      stopDemo();
      setState((s) => ({ ...s, status: "complete", latest: { ...s.latest, phase: "정지됨", message: "사용자 요청으로 정지" } }));
    }, 1800);
  }, []);

  // ---------- Try real backend ----------
  const tryConnect = useCallback_cn1(async () => {
    closedByUs.current = false;
    setWsStatus("connecting");
    try {
      const r = await fetch(baseUrl + "/health", { signal: AbortSignal.timeout(5000) });
      if (!r.ok) throw new Error("health failed");
      const j = await r.json();
      setHealth({ connected: true, contract_version: j.contract_version ?? null });

      // Fetch config spec
      try {
        const cs = await fetch(baseUrl + "/config/spec", { signal: AbortSignal.timeout(5000) });
        if (cs.ok) {
          const csj = await cs.json();
          const normalized = normalizeConfigSpecPayload(csj);
          if (normalized.fields.length) {
            setConfigSpec(normalized.fields);
          }
          setConfigSpecStatus(normalized.status);
        } else {
          setConfigSpecStatus({ source: "error", live: false, message: "config spec HTTP " + cs.status });
        }
      } catch (e) {
        setConfigSpecStatus({ source: "error", live: false, message: String(e && e.message ? e.message : e) });
      }

      // Fetch current state
      try {
        const st = await fetch(baseUrl + "/status", { signal: AbortSignal.timeout(5000) });
        if (st.ok) {
          const stj = await st.json();
          setState(stj);
        }
      } catch {}

      // Open WS
      openWs();
    } catch (e) {
      // Fall back to demo
      setHealth({ connected: false, contract_version: null });
      setConfigSpecStatus(CONFIG_SPEC_DEMO_STATUS);
      _recordWsDiag({ kind: "demo" });
      setWsStatus("demo");
    }
  }, [baseUrl]); // eslint-disable-line

  const openWs = useCallback_cn1(() => {
    try {
      const wsUrl = baseUrl.replace(/^http/, "ws") + "/ws";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
        _recordWsDiag({ kind: "open", recoveredAfter: reconnectAttempt.current });
        lastOpenAt.current = Date.now();
        if (graceTimer.current) { clearTimeout(graceTimer.current); graceTimer.current = null; }
        reconnectAttempt.current = 0;
        // LIVE↔DEMO 분리: 실제 WS가 열리면 데모 시뮬레이터를 즉시 중단한다.
        //   (이게 없으면 demo가 돌던 중 연결 시 current_run/engine을 계속 날조해
        //    라이브 데이터와 섞인다.) 이제 LIVE는 setState(data)만으로 갱신된다.
        stopDemo();
        setWsStatus("open");
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data && typeof data === "object" && "contract_version" in data) {
            // LIVE 경로: backend 계약 필드를 그대로 반영(날조 없음). DEMO 전용
            //   패널(current_run/engine)은 비어 있을 수 있고, 패널이 "실시간
            //   데이터 대기"로 처리한다(livePanelPending 참조).
            setState(data);
          } else if (data && typeof data === "object" && "action" in data) {
            // 제어 echo(start/stop/final_approval 결과). export 상태 등 노출용.
            setLastReply(data);
          }
        } catch {}
      };
      ws.onclose = (ev) => {
        _recordWsDiag({ kind: "close", code: ev && ev.code, reason: (ev && ev.reason) || "", byUs: !!closedByUs.current, attempt: reconnectAttempt.current });
        if (closedByUs.current) return;
        // 안정 연결(>=2s 유지)의 단발 종료만 1.2s 유예 — 그 안에 재연결 성공하면 깜빡임 없음.
        //   열리자마자(<2s) 닫히는 플래핑은 지속 장애 신호 → 즉시 노출(은폐 금지, 검토 §4).
        const openMs = lastOpenAt.current ? (Date.now() - lastOpenAt.current) : 0;
        const flapping = !lastOpenAt.current || openMs < 2000;
        if (graceTimer.current) { clearTimeout(graceTimer.current); graceTimer.current = null; }
        if (flapping) {
          setWsStatus("reconnecting");
        } else {
          graceTimer.current = setTimeout(() => { setWsStatus("reconnecting"); graceTimer.current = null; }, 1200);
        }
        lastOpenAt.current = 0;
        const delay = Math.min(8000, 500 * Math.pow(1.7, reconnectAttempt.current));
        reconnectAttempt.current += 1;
        setTimeout(() => {
          if (!closedByUs.current) openWs();
        }, delay);
      };
      ws.onerror = () => { _recordWsDiag({ kind: "error", attempt: reconnectAttempt.current }); /* onclose will fire */ };
    } catch (e) {
      setWsStatus("reconnecting");
    }
  }, [baseUrl]);

  useEffect_cn1(() => {
    tryConnect();
    return () => {
      closedByUs.current = true;
      if (graceTimer.current) { clearTimeout(graceTimer.current); graceTimer.current = null; }
      if (wsRef.current) wsRef.current.close();
      stopDemo();
    };
  }, [tryConnect]);

  // ---------- Send control messages ----------
  const send = useCallback_cn1((msg) => {
    if (msg && msg.action === "start" && wsStatus !== "demo" && !(configSpecStatus && configSpecStatus.live)) {
      setLastReply({
        action: "start",
        status: "error",
        reason: "config_spec_unavailable",
        message: "LIVE 진화 시작은 /config/spec가 정상 로드된 뒤에만 가능합니다.",
      });
      return false;
    }
    if (wsStatus === "demo" || !wsRef.current || wsRef.current.readyState !== 1) {
      // Demo mode: handle locally
      if (msg.action === "start") {
        startDemo(msg.config);
      } else if (msg.action === "stop") {
        stopDemoSoft();
      } else if (msg.action === "final_approval") {
        // Just reflect a flag
        setState((s) => ({
          ...s,
          status: "complete",
          latest: { ...s.latest, phase: "승인 완료", message: `${msg.user_buy} / ${msg.user_sell} 연구 Export 후보로 기록됨` },
        }));
        // 데모에서도 export 결과 배너가 뜨도록 합성 reply를 둔다(실제 export 아님).
        setLastReply({ action: "final_approval", status: "ok", demo: true,
                       buy: { name: msg.user_buy }, sell: { name: msg.user_sell } });
      }
      return true;
    }
    try {
      wsRef.current.send(JSON.stringify(msg));
      return true;
    } catch {
      return false;
    }
  }, [wsStatus, startDemo, stopDemoSoft, configSpecStatus]);

  return {
    state,
    health,
    wsStatus,
    configSpec,
    configSpecStatus,
    send,
    lastReply,
    reconnect: tryConnect,
  };
}

Object.assign(window, {
  useBackend,
  DEFAULT_BASE,
  getWsDiag,
});

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { useBackend, DEFAULT_BASE, INITIAL_STATE, DEFAULT_CONFIG_SPEC, normalizeConfigSpecPayload, getWsDiag };
