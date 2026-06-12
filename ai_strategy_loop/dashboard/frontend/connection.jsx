/* Connection: REST + WS w/ auto-reconnect; falls back to local simulator for demo. */
const { useState, useEffect, useRef, useCallback, useMemo } = React;

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

// =====================================================================
// LIVE ↔ DEMO 필드 경계 (contract v2, M1 격차 해소)
//
//  대시보드 상태는 두 출처 중 하나에서 온다:
//    - LIVE: 실제 루프(controller/loop.py:_publish_live) → current_state.json → WS.
//            contract.LoopState(pydantic)가 발행하는 필드만 담긴다.
//    - DEMO: 프론트 로컬 시뮬레이터(startDemo). backend가 없을 때만 동작하며
//            phase-detail 패널을 보여주려고 풍부한 필드를 "클라이언트에서 날조"한다.
//
//  LIVE가 실제로 발행하는 필드 (backend 계약):
//    contract_version, run_id, status, current_gen, max_generations, provider,
//    bt_timeframe, best, winner, generations[], latest{phase,last_checkpoint,message},
//    cumulative{tokens,cost_or_count}, page_data{...}(v2 패스스루), updated_at.
//
//  DEMO 전용(=backend가 발행하지 않는, 시뮬레이터가 날조하는) 필드:
//    engine{cpu_pct,mem_mb,workers_active,throughput,progress,chunks_* ...},
//    current_run{equity[],drawdown[],trades[],
//                generation{buy_code_partial,sell_code_partial,stream_tokens,...},
//                scoring{metrics[],composite}, autopsy{text_partial,...}}.
//
//  ⇒ 그래서 LIVE 모드에서는 시뮬레이터를 절대 돌리지 않는다(setState(data)만).
//    위 DEMO 전용 패널은 LIVE에서 "실시간 데이터 대기"로 비우고, DEMO 모드에서만
//    내용을 채우되 "DEMO" 배지로 출처를 명시한다(phase-detail.jsx 참조).
//    backend가 page_data로 실제 데이터를 발행하기 시작하면 해당 패널이 LIVE로 승격된다.
// =====================================================================

// 순수 판정 함수(테스트 가능): 현재 상태가 데모 시뮬레이터 출처인지.
//   wsStatus === "demo"일 때만 current_run/engine을 신뢰할 수 있다.
function isDemoSource(wsStatus) {
  return wsStatus === "demo";
}

// 순수 판정 함수(테스트 가능): 라이브 상태인데 DEMO 전용 패널 데이터가 비었는지.
//   true면 패널은 "실시간 데이터 대기"를 보여줘야 한다(날조 금지).
function livePanelPending(wsStatus, state) {
  if (isDemoSource(wsStatus)) return false;            // 데모는 자체 데이터로 채움
  const cr = state && state.current_run;
  const hasRich = !!(cr && ((cr.equity && cr.equity.length) ||
                            (cr.generation && (cr.generation.buy_code_partial ||
                                               cr.generation.sell_code_partial))));
  return !hasRich;                                     // 라이브인데 풍부 필드 없음 → 대기
}

// ---------- Demo strategy code generators (Korean-flavored stock pseudo-Python) ----------
function genBuyCode(tag, gen) {
  const seed = (gen * 7) % 9 + 1;
  const map = {
    VWAP: `# BUY_VWAP_g${gen} — VWAP × 거래량가속 + RSI 필터
def signal_buy(bar, ind, book):
    # 1) 가격이 VWAP 위로 ${(0.2 + seed * 0.05).toFixed(2)}% 이상 이격
    if not (bar.close > ind.vwap * 1.00${seed}): 
        return False
    # 2) 5분 거래량이 20봉 평균의 ${(150 + seed * 10)}% 이상
    if ind.vol_5m < ind.vol_20m_avg * ${(1.5 + seed * 0.1).toFixed(1)}:
        return False
    # 3) RSI(14) 50~70 구간 (과매수 회피)
    if not (50 <= ind.rsi_14 <= 70):
        return False
    # 4) 호가창 매수총잔량 / 매도총잔량 비율
    if book.bid_total / max(1, book.ask_total) < ${(1.4 + seed * 0.1).toFixed(2)}:
        return False
    return True`,
    MOM: `# BUY_MOM_g${gen} — 5/20 골든크로스 + 거래량 급증
def signal_buy(bar, ind, book):
    if ind.ema_5 <= ind.ema_20:                # 정배열 필요
        return False
    if ind.ema_5_prev > ind.ema_20_prev:       # 직전봉이 이미 정배열이면 신선도↓
        return False
    if ind.vol_now < ind.vol_20m_avg * ${(2.0 + seed * 0.1).toFixed(1)}:
        return False
    if bar.close <= bar.open * 1.00${seed}:    # 양봉 + 0.${seed}% 이상
        return False
    return True`,
    ORB: `# BUY_ORB_g${gen} — Opening Range Breakout 30m
def signal_buy(bar, ind, book):
    if bar.minute_of_day > 30 + 60:            # 장초반 90분 이내만
        return False
    if bar.high <= ind.or_30m_high:            # 30분 박스 상단 돌파
        return False
    if abs(bar.gap_pct) > 0.6:                 # 시초가 갭 0.6% 이내
        return False
    if ind.atr_14 < bar.close * 0.005:         # 변동성 너무 낮으면 패스
        return False
    return True`,
    FLOW: `# BUY_FLOW_g${gen} — 수급 추종 (프로그램·외인)
def signal_buy(bar, ind, book):
    if ind.program_netbuy_5m < ${(8e8 + seed * 1e8).toExponential(1)}:
        return False
    if ind.foreign_netbuy_today <= 0:
        return False
    if ind.short_ratio_today > ${(0.10 + seed * 0.01).toFixed(2)}:  # 공매도 비율 상한
        return False
    return True`,
    RSI: `# BUY_RSI_g${gen} — RSI 다이버전스 + BB 하단 반등
def signal_buy(bar, ind, book):
    if ind.rsi_14 < 30 or ind.rsi_14 > 45:
        return False
    if bar.close > ind.bb_lower * 1.01:
        return False
    if ind.obv_slope <= 0:                     # OBV는 우상향
        return False
    return True`,
    OBV: `# BUY_OBV_g${gen} — OBV 발산 + 거래대금 필터
def signal_buy(bar, ind, book):
    if ind.obv_5m < ind.obv_5m_prev:
        return False
    if ind.trading_value_today < ${5_000_000_000 + seed * 1e9}:
        return False
    if bar.close < ind.ema_20:
        return False
    return True`,
  };
  return map[tag] || map.VWAP;
}

function genSellCode(tag, gen) {
  const seed = (gen * 11) % 9 + 1;
  const map = {
    ATR: `# SELL_ATR_g${gen} — ATR 트레일링 스탑
def signal_sell(pos, bar, ind):
    trail = pos.high_since_entry - ind.atr_14 * ${(1.4 + seed * 0.1).toFixed(2)}
    if bar.close < trail:
        return ("trail_stop", bar.close)
    if pos.bars_held >= ${30 + seed * 5}:
        return ("time_exit", bar.close)
    if bar.close >= pos.entry_price * (1 + ${(0.024 + seed * 0.003).toFixed(3)}):
        return ("take_profit", bar.close)
    return None`,
    TRAIL: `# SELL_TRAIL_g${gen} — 동적 트레일 + 손익비 강제
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl < -${(0.012 + seed * 0.002).toFixed(3)}:
        return ("stop_loss", bar.close)
    if pnl > ${(0.03 + seed * 0.004).toFixed(3)} and ind.rsi_14 > 72:
        return ("overbought_exit", bar.close)
    if pos.high_since_entry / pos.entry_price > 1.025:
        # 1.025배 이상 갔다면 본전 + 0.3% 스탑
        if bar.close < pos.entry_price * 1.003:
            return ("breakeven_stop", bar.close)
    return None`,
    FIXED: `# SELL_FIXED_g${gen} — 고정 익절/손절
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl >= ${(0.025 + seed * 0.005).toFixed(3)}:
        return ("take_profit", bar.close)
    if pnl <= -${(0.015 + seed * 0.002).toFixed(3)}:
        return ("stop_loss", bar.close)
    return None`,
    PIVOT: `# SELL_PIVOT_g${gen} — 일중 피봇 이탈
def signal_sell(pos, bar, ind):
    if bar.close < ind.pivot_s1:
        return ("pivot_break", bar.close)
    if bar.minute_of_day >= 360:                # 14시 이후 트레일 강화
        if bar.close < pos.high_since_entry * 0.99${seed}:
            return ("late_trail", bar.close)
    return None`,
    TIME: `# SELL_TIME_g${gen} — 시간 기반 청산
def signal_sell(pos, bar, ind):
    if bar.minute_of_day >= 359:                # 종가 30분 전 강제청산
        return ("close_force", bar.close)
    if pos.bars_held >= ${20 + seed * 4}:
        return ("time_exit", bar.close)
    return None`,
  };
  return map[tag] || map.ATR;
}

// ---------- Default config spec (used if /config/spec is unavailable) ----------
const DEFAULT_CONFIG_SPEC = [
  // 목표/제약
  { name: "mdd_cap", label: "MDD 상한", type: "number", default: 15, group: "목표/제약",
    help: "허용 가능한 최대 낙폭(%) 상한. 초과 시 게이트 탈락." },
  { name: "min_trades", label: "최소 거래수", type: "number", default: 20, group: "목표/제약",
    help: "유의미한 평가를 위한 최소 거래 횟수." },
  { name: "target_score", label: "목표 적합도", type: "number", default: 1.0, group: "목표/제약",
    help: "이 점수 이상이면 하드 게이트 통과(우승 후보)." },

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
  { name: "bt_start_date", label: "시작일", type: "text", default: "2025-03-01", group: "평가 스코프",
    help: "백테스트 구간 시작일 (YYYY-MM-DD). 빈 값이면 최근 N일." },

  // 엔진 리소스
  { name: "engine_workers", label: "병렬 워커수", type: "number", default: 8, group: "엔진 리소스",
    help: "백테스트 병렬 실행 프로세스 수. 보통 CPU 코어수와 같거나 그 이하." },
  { name: "engine_cpu_cap", label: "CPU 상한(%)", type: "number", default: 85, group: "엔진 리소스",
    help: "전체 사용률이 이 값을 넘으면 새 작업을 큐잉. 0이면 무제한." },
  { name: "engine_mem_cap_mb", label: "메모리 상한(MB)", type: "number", default: 8192, group: "엔진 리소스",
    help: "초과 시 가장 오래된 캐시부터 해제." },
  { name: "engine_chunk_days", label: "청크 크기(일)", type: "number", default: 5, group: "엔진 리소스",
    help: "한 워커가 한 번에 처리하는 백테스트 구간 크기." },

  // 과적합 가드
  { name: "graduation_holdout", label: "졸업 홀드아웃", type: "boolean", default: false, group: "과적합 가드",
    help: "최종 게이트 통과 시, 별도 보류 구간(holdout)에서 추가 검증. 과적합 방지에 도움이 되나 시간이 더 소요됨." },

  // AI
  { name: "provider", label: "프로바이더", type: "select", default: "gpt_auth",
    options: ["gpt_auth", "claude", "local"], group: "AI",
    help: "전략 생성에 사용할 LLM 제공자." },
  { name: "model", label: "모델", type: "text", default: "gpt-5-codex", group: "AI",
    help: "사용할 모델 식별자." },
  { name: "max_generations", label: "최대 세대", type: "number", default: 30, group: "AI",
    help: "이 세대까지 도달하면 루프 종료." },
  { name: "temperature", label: "Temperature", type: "number", default: 0.7, group: "AI",
    help: "생성 다양성. 높을수록 탐험적, 낮을수록 보수적." },
  { name: "feedback_window", label: "피드백 윈도우", type: "number", default: 3, group: "AI",
    help: "다음 세대에 전달할 직전 부검(autopsy) 수." },
];

const INITIAL_STATE = {
  contract_version: 1,
  run_id: null,
  status: "idle",
  current_gen: 0,
  max_generations: 30,
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
  const [health, setHealth] = useState({ connected: false, contract_version: null });
  const [wsStatus, setWsStatus] = useState("connecting"); // connecting | open | reconnecting | demo
  const [state, setState] = useState(INITIAL_STATE);
  const [configSpec, setConfigSpec] = useState(DEFAULT_CONFIG_SPEC);
  // 제어 응답(start/stop/final_approval)의 마지막 결과. contract_version이 없는
  //   응답 프레임(=상태 스냅샷이 아닌 제어 echo)을 여기로 라우팅해 export 상태 등을
  //   UI가 표시할 수 있게 한다. final_approval(export) 게이트 결과 노출에 쓰인다.
  const [lastReply, setLastReply] = useState(null);

  const wsRef = useRef(null);
  const reconnectAttempt = useRef(0);
  const closedByUs = useRef(false);
  const demoRef = useRef(null);

  // ---- Demo simulator ----
  const startDemo = useCallback((config) => {
    stopDemo();
    setWsStatus("demo");
    const cfg = config || {};
    const max = Number(cfg.max_generations ?? 12);
    const target = Number(cfg.target_score ?? 1.0);
    const mddCap = Number(cfg.mdd_cap ?? 15);
    const minTrades = Number(cfg.min_trades ?? 20);
    const workers = Number(cfg.engine_workers ?? 8);
    const memCap = Number(cfg.engine_mem_cap_mb ?? 8192);
    const startDate = cfg.bt_start_date || "2025-03-01";
    const windowDays = Number(cfg.bt_window_days ?? 60);
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
      const willPass = !isErrorRoll && targetScore >= target && target_mdd_pct <= mddCap && target_trades >= minTrades;
      const autopsy_text = willPass
        ? `gen_${genNo + 1} — 하드 게이트 통과. graded_score=${targetScore.toFixed(3)} (target ${target.toFixed(2)}), MDD ${target_mdd_pct.toFixed(2)}% ≤ ${mddCap}%, 거래 ${target_trades}회 ≥ ${minTrades}. 다음 세대는 동일 골격 유지하며 슬리피지 가정만 보수화.`
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
      const gate_passed = !isError && graded_score >= target && mdd <= mddCap && trade_count >= minTrades;

      let gate_reason = "조건 충족";
      if (isError) gate_reason = "실행 오류";
      else if (trade_count === 0) gate_reason = "거래 0건";
      else if (trade_count < minTrades) gate_reason = `거래수 부족(${trade_count}/${minTrades})`;
      else if (mdd > mddCap) gate_reason = `MDD 초과(${mdd}% > ${mddCap}%)`;
      else if (graded_score < target) gate_reason = `점수 미달(${graded_score.toFixed(3)} < ${target})`;

      const gist = plan.gist + " — " + (isError ? "런타임 예외" : `진입 ${trade_count}회, MDD ${mdd}%`);

      const newGen = {
        gen_no: gen,
        status: isError ? "error" : "success",
        graded_score: +graded_score.toFixed(3),
        gate_passed, gate_reason,
        trade_count, mdd, profit,
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

  const stopDemoSoft = useCallback(() => {
    // emulate "stopping after current gen"
    setState((s) => ({ ...s, status: "stopping", latest: { ...s.latest, message: "현재 세대 완료 후 정지합니다" } }));
    setTimeout(() => {
      stopDemo();
      setState((s) => ({ ...s, status: "complete", latest: { ...s.latest, phase: "정지됨", message: "사용자 요청으로 정지" } }));
    }, 1800);
  }, []);

  // ---------- Try real backend ----------
  const tryConnect = useCallback(async () => {
    closedByUs.current = false;
    setWsStatus("connecting");
    try {
      const r = await fetch(baseUrl + "/health", { signal: AbortSignal.timeout(1500) });
      if (!r.ok) throw new Error("health failed");
      const j = await r.json();
      setHealth({ connected: true, contract_version: j.contract_version ?? null });

      // Fetch config spec
      try {
        const cs = await fetch(baseUrl + "/config/spec", { signal: AbortSignal.timeout(1500) });
        if (cs.ok) {
          const csj = await cs.json();
          if (Array.isArray(csj) && csj.length) setConfigSpec(csj);
        }
      } catch {}

      // Fetch current state
      try {
        const st = await fetch(baseUrl + "/status", { signal: AbortSignal.timeout(1500) });
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
      setWsStatus("demo");
    }
  }, [baseUrl]); // eslint-disable-line

  const openWs = useCallback(() => {
    try {
      const wsUrl = baseUrl.replace(/^http/, "ws") + "/ws";
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
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
      ws.onclose = () => {
        if (closedByUs.current) return;
        setWsStatus("reconnecting");
        const delay = Math.min(8000, 500 * Math.pow(1.7, reconnectAttempt.current));
        reconnectAttempt.current += 1;
        setTimeout(() => {
          if (!closedByUs.current) openWs();
        }, delay);
      };
      ws.onerror = () => { /* onclose will fire */ };
    } catch (e) {
      setWsStatus("reconnecting");
    }
  }, [baseUrl]);

  useEffect(() => {
    tryConnect();
    return () => {
      closedByUs.current = true;
      if (wsRef.current) wsRef.current.close();
      stopDemo();
    };
  }, [tryConnect]);

  // ---------- Send control messages ----------
  const send = useCallback((msg) => {
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
          latest: { ...s.latest, phase: "승인 완료", message: `${msg.user_buy} / ${msg.user_sell} 운영 DB로 내보냄` },
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
  }, [wsStatus, startDemo, stopDemoSoft]);

  return {
    state,
    health,
    wsStatus,
    configSpec,
    send,
    lastReply,
    reconnect: tryConnect,
  };
}

// ---------- Formatting helpers ----------
const fmtScore = (v) => (typeof v === "number" ? v.toFixed(3) : "—");
const fmtPct = (v) => (typeof v === "number" ? `${v.toFixed(2)}%` : "—");
const fmtMoney = (v) => {
  if (typeof v !== "number") return "—";
  const sign = v > 0 ? "+" : v < 0 ? "−" : "";
  return sign + Math.abs(v).toLocaleString("ko-KR") + "원";
};
const fmtInt = (v) => (typeof v === "number" ? v.toLocaleString("ko-KR") : "—");
const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("ko-KR", { hour12: false });
  } catch { return "—"; }
};

const STATUS_KR = {
  idle: "대기",
  running: "실행중",
  stopping: "정지중",
  complete: "완료",
  error: "오류",
};

Object.assign(window, {
  useBackend,
  fmtScore, fmtPct, fmtMoney, fmtInt, fmtTime,
  STATUS_KR,
  DEFAULT_BASE,
  // LIVE↔DEMO 경계 판정(테스트/패널 공용 순수 함수).
  isDemoSource, livePanelPending,
});
