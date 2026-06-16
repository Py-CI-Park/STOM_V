"use strict";
(() => {
  // ../frontend/connection.jsx
  var { useState, useEffect, useRef, useCallback, useMemo } = React;
  var DEFAULT_BASE2 = typeof window !== "undefined" && window.location && window.location.origin && window.location.origin.startsWith("http") ? window.location.origin : "http://127.0.0.1:8770";
  function isDemoSource(wsStatus) {
    return wsStatus === "demo";
  }
  function livePanelPending(wsStatus, state) {
    if (isDemoSource(wsStatus)) return false;
    const cr = state && state.current_run;
    const hasRich = !!(cr && (cr.equity && cr.equity.length || cr.generation && (cr.generation.buy_code_partial || cr.generation.sell_code_partial)));
    return !hasRich;
  }
  function genBuyCode(tag, gen) {
    const seed = gen * 7 % 9 + 1;
    const map = {
      VWAP: `# BUY_VWAP_g${gen} \u2014 VWAP \xD7 \uAC70\uB798\uB7C9\uAC00\uC18D + RSI \uD544\uD130
def signal_buy(bar, ind, book):
    # 1) \uAC00\uACA9\uC774 VWAP \uC704\uB85C ${(0.2 + seed * 0.05).toFixed(2)}% \uC774\uC0C1 \uC774\uACA9
    if not (bar.close > ind.vwap * 1.00${seed}): 
        return False
    # 2) 5\uBD84 \uAC70\uB798\uB7C9\uC774 20\uBD09 \uD3C9\uADE0\uC758 ${150 + seed * 10}% \uC774\uC0C1
    if ind.vol_5m < ind.vol_20m_avg * ${(1.5 + seed * 0.1).toFixed(1)}:
        return False
    # 3) RSI(14) 50~70 \uAD6C\uAC04 (\uACFC\uB9E4\uC218 \uD68C\uD53C)
    if not (50 <= ind.rsi_14 <= 70):
        return False
    # 4) \uD638\uAC00\uCC3D \uB9E4\uC218\uCD1D\uC794\uB7C9 / \uB9E4\uB3C4\uCD1D\uC794\uB7C9 \uBE44\uC728
    if book.bid_total / max(1, book.ask_total) < ${(1.4 + seed * 0.1).toFixed(2)}:
        return False
    return True`,
      MOM: `# BUY_MOM_g${gen} \u2014 5/20 \uACE8\uB4E0\uD06C\uB85C\uC2A4 + \uAC70\uB798\uB7C9 \uAE09\uC99D
def signal_buy(bar, ind, book):
    if ind.ema_5 <= ind.ema_20:                # \uC815\uBC30\uC5F4 \uD544\uC694
        return False
    if ind.ema_5_prev > ind.ema_20_prev:       # \uC9C1\uC804\uBD09\uC774 \uC774\uBBF8 \uC815\uBC30\uC5F4\uC774\uBA74 \uC2E0\uC120\uB3C4\u2193
        return False
    if ind.vol_now < ind.vol_20m_avg * ${(2 + seed * 0.1).toFixed(1)}:
        return False
    if bar.close <= bar.open * 1.00${seed}:    # \uC591\uBD09 + 0.${seed}% \uC774\uC0C1
        return False
    return True`,
      ORB: `# BUY_ORB_g${gen} \u2014 Opening Range Breakout 30m
def signal_buy(bar, ind, book):
    if bar.minute_of_day > 30 + 60:            # \uC7A5\uCD08\uBC18 90\uBD84 \uC774\uB0B4\uB9CC
        return False
    if bar.high <= ind.or_30m_high:            # 30\uBD84 \uBC15\uC2A4 \uC0C1\uB2E8 \uB3CC\uD30C
        return False
    if abs(bar.gap_pct) > 0.6:                 # \uC2DC\uCD08\uAC00 \uAC2D 0.6% \uC774\uB0B4
        return False
    if ind.atr_14 < bar.close * 0.005:         # \uBCC0\uB3D9\uC131 \uB108\uBB34 \uB0AE\uC73C\uBA74 \uD328\uC2A4
        return False
    return True`,
      FLOW: `# BUY_FLOW_g${gen} \u2014 \uC218\uAE09 \uCD94\uC885 (\uD504\uB85C\uADF8\uB7A8\xB7\uC678\uC778)
def signal_buy(bar, ind, book):
    if ind.program_netbuy_5m < ${(8e8 + seed * 1e8).toExponential(1)}:
        return False
    if ind.foreign_netbuy_today <= 0:
        return False
    if ind.short_ratio_today > ${(0.1 + seed * 0.01).toFixed(2)}:  # \uACF5\uB9E4\uB3C4 \uBE44\uC728 \uC0C1\uD55C
        return False
    return True`,
      RSI: `# BUY_RSI_g${gen} \u2014 RSI \uB2E4\uC774\uBC84\uC804\uC2A4 + BB \uD558\uB2E8 \uBC18\uB4F1
def signal_buy(bar, ind, book):
    if ind.rsi_14 < 30 or ind.rsi_14 > 45:
        return False
    if bar.close > ind.bb_lower * 1.01:
        return False
    if ind.obv_slope <= 0:                     # OBV\uB294 \uC6B0\uC0C1\uD5A5
        return False
    return True`,
      OBV: `# BUY_OBV_g${gen} \u2014 OBV \uBC1C\uC0B0 + \uAC70\uB798\uB300\uAE08 \uD544\uD130
def signal_buy(bar, ind, book):
    if ind.obv_5m < ind.obv_5m_prev:
        return False
    if ind.trading_value_today < ${5e9 + seed * 1e9}:
        return False
    if bar.close < ind.ema_20:
        return False
    return True`
    };
    return map[tag] || map.VWAP;
  }
  function genSellCode(tag, gen) {
    const seed = gen * 11 % 9 + 1;
    const map = {
      ATR: `# SELL_ATR_g${gen} \u2014 ATR \uD2B8\uB808\uC77C\uB9C1 \uC2A4\uD0D1
def signal_sell(pos, bar, ind):
    trail = pos.high_since_entry - ind.atr_14 * ${(1.4 + seed * 0.1).toFixed(2)}
    if bar.close < trail:
        return ("trail_stop", bar.close)
    if pos.bars_held >= ${30 + seed * 5}:
        return ("time_exit", bar.close)
    if bar.close >= pos.entry_price * (1 + ${(0.024 + seed * 3e-3).toFixed(3)}):
        return ("take_profit", bar.close)
    return None`,
      TRAIL: `# SELL_TRAIL_g${gen} \u2014 \uB3D9\uC801 \uD2B8\uB808\uC77C + \uC190\uC775\uBE44 \uAC15\uC81C
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl < -${(0.012 + seed * 2e-3).toFixed(3)}:
        return ("stop_loss", bar.close)
    if pnl > ${(0.03 + seed * 4e-3).toFixed(3)} and ind.rsi_14 > 72:
        return ("overbought_exit", bar.close)
    if pos.high_since_entry / pos.entry_price > 1.025:
        # 1.025\uBC30 \uC774\uC0C1 \uAC14\uB2E4\uBA74 \uBCF8\uC804 + 0.3% \uC2A4\uD0D1
        if bar.close < pos.entry_price * 1.003:
            return ("breakeven_stop", bar.close)
    return None`,
      FIXED: `# SELL_FIXED_g${gen} \u2014 \uACE0\uC815 \uC775\uC808/\uC190\uC808
def signal_sell(pos, bar, ind):
    pnl = (bar.close / pos.entry_price) - 1
    if pnl >= ${(0.025 + seed * 5e-3).toFixed(3)}:
        return ("take_profit", bar.close)
    if pnl <= -${(0.015 + seed * 2e-3).toFixed(3)}:
        return ("stop_loss", bar.close)
    return None`,
      PIVOT: `# SELL_PIVOT_g${gen} \u2014 \uC77C\uC911 \uD53C\uBD07 \uC774\uD0C8
def signal_sell(pos, bar, ind):
    if bar.close < ind.pivot_s1:
        return ("pivot_break", bar.close)
    if bar.minute_of_day >= 360:                # 14\uC2DC \uC774\uD6C4 \uD2B8\uB808\uC77C \uAC15\uD654
        if bar.close < pos.high_since_entry * 0.99${seed}:
            return ("late_trail", bar.close)
    return None`,
      TIME: `# SELL_TIME_g${gen} \u2014 \uC2DC\uAC04 \uAE30\uBC18 \uCCAD\uC0B0
def signal_sell(pos, bar, ind):
    if bar.minute_of_day >= 359:                # \uC885\uAC00 30\uBD84 \uC804 \uAC15\uC81C\uCCAD\uC0B0
        return ("close_force", bar.close)
    if pos.bars_held >= ${20 + seed * 4}:
        return ("time_exit", bar.close)
    return None`
    };
    return map[tag] || map.ATR;
  }
  var DEFAULT_CONFIG_SPEC = [
    // 목표/제약
    {
      name: "mdd_cap",
      label: "MDD \uC0C1\uD55C",
      type: "number",
      default: 15,
      group: "\uBAA9\uD45C/\uC81C\uC57D",
      help: "\uD5C8\uC6A9 \uAC00\uB2A5\uD55C \uCD5C\uB300 \uB099\uD3ED(%) \uC0C1\uD55C. \uCD08\uACFC \uC2DC \uAC8C\uC774\uD2B8 \uD0C8\uB77D."
    },
    {
      name: "min_trades",
      label: "\uCD5C\uC18C \uAC70\uB798\uC218",
      type: "number",
      default: 20,
      group: "\uBAA9\uD45C/\uC81C\uC57D",
      help: "\uC720\uC758\uBBF8\uD55C \uD3C9\uAC00\uB97C \uC704\uD55C \uCD5C\uC18C \uAC70\uB798 \uD69F\uC218."
    },
    {
      name: "target_score",
      label: "\uBAA9\uD45C \uC801\uD569\uB3C4",
      type: "number",
      default: 1,
      group: "\uBAA9\uD45C/\uC81C\uC57D",
      help: "\uC774 \uC810\uC218 \uC774\uC0C1\uC774\uBA74 \uD558\uB4DC \uAC8C\uC774\uD2B8 \uD1B5\uACFC(\uC6B0\uC2B9 \uD6C4\uBCF4)."
    },
    // 평가 스코프
    {
      name: "bt_timeframe",
      label: "\uBC31\uD14C\uC2A4\uD2B8 \uC2DC\uAC04\uB2E8\uC704",
      type: "select",
      default: "min",
      options: ["min", "tick"],
      group: "\uD3C9\uAC00 \uC2A4\uCF54\uD504",
      help: "\uBD84\uBD09(min) \uB610\uB294 \uD2F1(tick) \uB370\uC774\uD130 \uC0AC\uC6A9."
    },
    {
      name: "bt_scope",
      label: "\uBC31\uD14C\uC2A4\uD2B8 \uBC94\uC704",
      type: "select",
      default: "universe",
      options: ["universe", "one_code"],
      group: "\uD3C9\uAC00 \uC2A4\uCF54\uD504",
      help: "\uC804\uCCB4 \uC720\uB2C8\uBC84\uC2A4 \uB610\uB294 \uB2E8\uC77C \uC885\uBAA9 \uD3C9\uAC00."
    },
    {
      name: "bt_one_code",
      label: "\uB2E8\uC77C \uC885\uBAA9 \uCF54\uB4DC",
      type: "text",
      default: "005930",
      group: "\uD3C9\uAC00 \uC2A4\uCF54\uD504",
      help: "bt_scope=one_code\uC77C \uB54C \uC0AC\uC6A9\uD560 \uC885\uBAA9\uCF54\uB4DC(KOSPI/KOSDAQ 6\uC790\uB9AC)."
    },
    {
      name: "bt_window_days",
      label: "\uBC31\uD14C\uC2A4\uD2B8 \uC708\uB3C4\uC6B0(\uC77C)",
      type: "number",
      default: 60,
      group: "\uD3C9\uAC00 \uC2A4\uCF54\uD504",
      help: "\uCD5C\uADFC N\uC77C \uB370\uC774\uD130\uB85C \uBC31\uD14C\uC2A4\uD2B8 \uC218\uD589."
    },
    {
      name: "bt_start_date",
      label: "\uC2DC\uC791\uC77C",
      type: "text",
      default: "2025-03-01",
      group: "\uD3C9\uAC00 \uC2A4\uCF54\uD504",
      help: "\uBC31\uD14C\uC2A4\uD2B8 \uAD6C\uAC04 \uC2DC\uC791\uC77C (YYYY-MM-DD). \uBE48 \uAC12\uC774\uBA74 \uCD5C\uADFC N\uC77C."
    },
    // 엔진 리소스
    {
      name: "engine_workers",
      label: "\uBCD1\uB82C \uC6CC\uCEE4\uC218",
      type: "number",
      default: 8,
      group: "\uC5D4\uC9C4 \uB9AC\uC18C\uC2A4",
      help: "\uBC31\uD14C\uC2A4\uD2B8 \uBCD1\uB82C \uC2E4\uD589 \uD504\uB85C\uC138\uC2A4 \uC218. \uBCF4\uD1B5 CPU \uCF54\uC5B4\uC218\uC640 \uAC19\uAC70\uB098 \uADF8 \uC774\uD558."
    },
    {
      name: "engine_cpu_cap",
      label: "CPU \uC0C1\uD55C(%)",
      type: "number",
      default: 85,
      group: "\uC5D4\uC9C4 \uB9AC\uC18C\uC2A4",
      help: "\uC804\uCCB4 \uC0AC\uC6A9\uB960\uC774 \uC774 \uAC12\uC744 \uB118\uC73C\uBA74 \uC0C8 \uC791\uC5C5\uC744 \uD050\uC789. 0\uC774\uBA74 \uBB34\uC81C\uD55C."
    },
    {
      name: "engine_mem_cap_mb",
      label: "\uBA54\uBAA8\uB9AC \uC0C1\uD55C(MB)",
      type: "number",
      default: 8192,
      group: "\uC5D4\uC9C4 \uB9AC\uC18C\uC2A4",
      help: "\uCD08\uACFC \uC2DC \uAC00\uC7A5 \uC624\uB798\uB41C \uCE90\uC2DC\uBD80\uD130 \uD574\uC81C."
    },
    {
      name: "engine_chunk_days",
      label: "\uCCAD\uD06C \uD06C\uAE30(\uC77C)",
      type: "number",
      default: 5,
      group: "\uC5D4\uC9C4 \uB9AC\uC18C\uC2A4",
      help: "\uD55C \uC6CC\uCEE4\uAC00 \uD55C \uBC88\uC5D0 \uCC98\uB9AC\uD558\uB294 \uBC31\uD14C\uC2A4\uD2B8 \uAD6C\uAC04 \uD06C\uAE30."
    },
    // 과적합 가드
    {
      name: "graduation_holdout",
      label: "\uC878\uC5C5 \uD640\uB4DC\uC544\uC6C3",
      type: "boolean",
      default: false,
      group: "\uACFC\uC801\uD569 \uAC00\uB4DC",
      help: "\uCD5C\uC885 \uAC8C\uC774\uD2B8 \uD1B5\uACFC \uC2DC, \uBCC4\uB3C4 \uBCF4\uB958 \uAD6C\uAC04(holdout)\uC5D0\uC11C \uCD94\uAC00 \uAC80\uC99D. \uACFC\uC801\uD569 \uBC29\uC9C0\uC5D0 \uB3C4\uC6C0\uC774 \uB418\uB098 \uC2DC\uAC04\uC774 \uB354 \uC18C\uC694\uB428."
    },
    // AI
    {
      name: "provider",
      label: "\uD504\uB85C\uBC14\uC774\uB354",
      type: "select",
      default: "gpt_auth",
      options: ["gpt_auth", "claude", "local"],
      group: "AI",
      help: "\uC804\uB7B5 \uC0DD\uC131\uC5D0 \uC0AC\uC6A9\uD560 LLM \uC81C\uACF5\uC790."
    },
    {
      name: "model",
      label: "\uBAA8\uB378",
      type: "text",
      default: "gpt-5-codex",
      group: "AI",
      help: "\uC0AC\uC6A9\uD560 \uBAA8\uB378 \uC2DD\uBCC4\uC790."
    },
    {
      name: "max_generations",
      label: "\uCD5C\uB300 \uC138\uB300",
      type: "number",
      default: 30,
      group: "AI",
      help: "\uC774 \uC138\uB300\uAE4C\uC9C0 \uB3C4\uB2EC\uD558\uBA74 \uB8E8\uD504 \uC885\uB8CC."
    },
    {
      name: "temperature",
      label: "Temperature",
      type: "number",
      default: 0.7,
      group: "AI",
      help: "\uC0DD\uC131 \uB2E4\uC591\uC131. \uB192\uC744\uC218\uB85D \uD0D0\uD5D8\uC801, \uB0AE\uC744\uC218\uB85D \uBCF4\uC218\uC801."
    },
    {
      name: "feedback_window",
      label: "\uD53C\uB4DC\uBC31 \uC708\uB3C4\uC6B0",
      type: "number",
      default: 3,
      group: "AI",
      help: "\uB2E4\uC74C \uC138\uB300\uC5D0 \uC804\uB2EC\uD560 \uC9C1\uC804 \uBD80\uAC80(autopsy) \uC218."
    }
  ];
  var INITIAL_STATE = {
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
    latest: { phase: "\uB300\uAE30\uC911", last_checkpoint: "\u2014", message: "\uC9C4\uD654 \uC2DC\uC791 \uB300\uAE30" },
    cumulative: { tokens: 0, cost_or_count: 0 },
    engine: {
      status: "idle",
      cpu_pct: 0,
      mem_mb: 0,
      mem_cap_mb: 8192,
      workers: 8,
      workers_active: 0,
      throughput: 0,
      // candles/sec
      elapsed_ms: 0,
      eta_ms: 0,
      current_symbol: "\u2014",
      current_window: { from: "\u2014", to: "\u2014" },
      progress: 0,
      // 0..1 within current gen's backtest
      chunks_done: 0,
      chunks_total: 0
    },
    current_run: {
      equity: [],
      // [{ t, value }]   value in won; starts ~10,000,000
      drawdown: [],
      // [{ t, value_pct }]
      trades: [],
      // [{ t, side, price }]
      // Phase-detail streams
      generation: {
        active: null,
        // "buy" | "sell" | "done"
        buy_code_partial: "",
        sell_code_partial: "",
        buy_done: false,
        sell_done: false,
        prompt_context: [],
        // previous autopsies fed into LLM
        stream_tokens: 0
      },
      scoring: {
        metrics: [],
        // [{ key, label, weight, value, ready }]
        composite: null
        // null while computing
      },
      autopsy: {
        text_partial: "",
        text_target: "",
        ready: false
      }
    },
    updated_at: (/* @__PURE__ */ new Date()).toISOString()
  };
  function useBackend2(baseUrl) {
    const [health, setHealth] = useState({ connected: false, contract_version: null });
    const [wsStatus, setWsStatus] = useState("connecting");
    const [state, setState] = useState(INITIAL_STATE);
    const [configSpec, setConfigSpec] = useState(DEFAULT_CONFIG_SPEC);
    const [lastReply, setLastReply] = useState(null);
    const wsRef = useRef(null);
    const reconnectAttempt = useRef(0);
    const closedByUs = useRef(false);
    const demoRef = useRef(null);
    const startDemo = useCallback((config) => {
      var _a, _b, _c, _d, _e, _f, _g, _h;
      stopDemo();
      setWsStatus("demo");
      const cfg = config || {};
      const max = Number((_a = cfg.max_generations) != null ? _a : 12);
      const target = Number((_b = cfg.target_score) != null ? _b : 1);
      const mddCap = Number((_c = cfg.mdd_cap) != null ? _c : 15);
      const minTrades = Number((_d = cfg.min_trades) != null ? _d : 20);
      const workers = Number((_e = cfg.engine_workers) != null ? _e : 8);
      const memCap = Number((_f = cfg.engine_mem_cap_mb) != null ? _f : 8192);
      const startDate = cfg.bt_start_date || "2025-03-01";
      const windowDays = Number((_g = cfg.bt_window_days) != null ? _g : 60);
      const provider = cfg.provider || "gpt_auth";
      const chunkDays = Number((_h = cfg.engine_chunk_days) != null ? _h : 5);
      let gen = 0;
      let best = null;
      let winner = null;
      let generations = [];
      let tokens = 0;
      let stepInGen = 0;
      const STEP_BUY_END = 5;
      const STEP_SELL_END = 10;
      const STEP_BT_END = 22;
      const STEP_SCORE_END = 26;
      const STEP_AUT_END = 30;
      const STEPS_PER_GEN = STEP_AUT_END;
      const TICK_MS = 300;
      const runId = "demo-" + Date.now().toString(36);
      const genStartedAt = { ms: Date.now() };
      let plan = null;
      let currentRun = freshRun();
      let equityVal = 1e7;
      let equityHigh = equityVal;
      let runMinutes = 0;
      let currentSymbol = pickSymbol();
      let currentDay = 0;
      let totalChunks = Math.max(4, Math.ceil(windowDays / chunkDays));
      let chunksDone = 0;
      const feedbackPool = [
        "\uAC70\uB798 0\uAC74 \u2192 \uC9C4\uC785 \uC870\uAC74 \uC644\uD654 (\uB9E4\uC218\uCD1D\uC794\uB7C9 \uC784\uACC4 \u219320%)",
        "\uC190\uC2E4 \uAD6C\uAC04\uC5D0 \uB9E4\uC218\uCD1D\uC794\uB7C9\uC774 \uD3C9\uADE0\uBCF4\uB2E4 38% \uB192\uC558\uC74C \u2192 \uAE30\uC900 \uAC15\uD654",
        "MDD 19.4% \uCD08\uACFC \u2192 \uC190\uC808 \uD2B8\uB808\uC77C\uC744 ATR\xD71.5\uB85C \uD0C0\uC774\uD2B8\uD558\uAC8C",
        "\uC708\uB808\uC774\uD2B8 41% / \uD3C9\uADE0 \uC190\uC775\uBE44 0.8 \u2192 \uC775\uC808 \uC870\uAC74\uC744 +2.4%\uB85C \uC0C1\uD5A5",
        "\uAC70\uB798 \uBE48\uB3C4 \uACFC\uB2E4(\uD3C9\uADE0 12\uD68C/\uC77C) \u2192 \uC2E0\uD638 \uD3C9\uD65C\uD654(EMA 5\u219212)",
        "\uC624\uBC84\uB098\uC787 \uAC2D\uC5D0\uC11C \uC190\uC2E4 \uC9D1\uC911 \u2192 \uC885\uAC00 30\uBD84 \uC804 \uAC15\uC81C \uCCAD\uC0B0",
        "\uAC70\uB798\uB7C9 thin\uD55C \uC885\uBAA9\uC5D0\uC11C \uC2AC\uB9AC\uD53C\uC9C0 \uB204\uC801 \u2192 \uAC70\uB798\uB300\uAE08 \u2265 50\uC5B5 \uD544\uD130 \uCD94\uAC00",
        "\uB2E8\uAE30 \uBAA8\uBA58\uD140 \uACFC\uBC18\uC751 \u2192 RSI 70 \uC774\uC0C1\uC5D0\uC11C \uC2E0\uADDC \uC9C4\uC785 \uCC28\uB2E8"
      ];
      const gistPool = [
        "VWAP \xD7 \uAC70\uB798\uB7C9\uAC00\uC18D + RSI(14) \uD544\uD130",
        "\uC7A5\uC911 \uAC70\uB798\uB300\uAE08 \uC0C1\uC704 10% & 5\uBD84 EMA \uC815\uBC30\uC5F4",
        "\uD504\uB85C\uADF8\uB7A8 \uB9E4\uC218\uC6B0\uC704 + \uC678\uC778\uC21C\uB9E4\uC218 \uC804\uD658",
        "OBV \uBC1C\uC0B0 + \uBCFC\uB9B0\uC800\uBC34\uB4DC \uD558\uB2E8 \uBC18\uB4F1",
        "5/20 \uACE8\uB4E0\uD06C\uB85C\uC2A4 + \uAC70\uB798\uB7C9 200% \uAE09\uC99D",
        "ATR-trailing stop, \uC9C4\uC785 \uC2DC \uC794\uB7C9\uBE44\uC728 \u2265 1.6",
        "\uC7A5\uCD08\uBC18 30\uBD84 \uBC15\uC2A4 \uB3CC\uD30C + \uC2DC\uCD08\uAC00 \uAC2D < 0.6%",
        "\uD638\uAC00\uCC3D \uB9E4\uC218\uCD1D\uC794\uB7C9/\uB9E4\uB3C4\uCD1D\uC794\uB7C9 \uBE44\uC728 > 2.0"
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
            stream_tokens: 0
          },
          scoring: { metrics: [], composite: null },
          autopsy: { text_partial: "", text_target: "", ready: false }
        };
      }
      function pickSymbol() {
        const samples = [
          ["005930", "\uC0BC\uC131\uC804\uC790"],
          ["000660", "SK\uD558\uC774\uB2C9\uC2A4"],
          ["035420", "NAVER"],
          ["051910", "LG\uD654\uD559"],
          ["207940", "\uC0BC\uC131\uBC14\uC774\uC624\uB85C\uC9C1\uC2A4"],
          ["005380", "\uD604\uB300\uCC28"],
          ["068270", "\uC140\uD2B8\uB9AC\uC628"],
          ["035720", "\uCE74\uCE74\uC624"],
          ["096770", "SK\uC774\uB178\uBCA0\uC774\uC158"],
          ["028260", "\uC0BC\uC131\uBB3C\uC0B0"],
          ["323410", "\uCE74\uCE74\uC624\uBC45\uD06C"],
          ["247540", "\uC5D0\uCF54\uD504\uB85C\uBE44\uC5E0"]
        ];
        return samples[Math.floor(Math.random() * samples.length)];
      }
      function dateAdd(base, days) {
        const d = new Date(base);
        d.setDate(d.getDate() + days);
        return d.toISOString().slice(0, 10);
      }
      function buildPlan(genNo) {
        const buyTag = ["VWAP", "MOM", "ORB", "FLOW", "RSI", "OBV"][Math.floor(Math.random() * 6)];
        const sellTag = ["ATR", "TRAIL", "FIXED", "PIVOT", "TIME"][Math.floor(Math.random() * 5)];
        const buyName = `BUY_${buyTag}_g${genNo + 1}`;
        const sellName = `SELL_${sellTag}_g${genNo + 1}`;
        const buy_code = genBuyCode(buyTag, genNo + 1);
        const sell_code = genSellCode(sellTag, genNo + 1);
        const buy_lines = buy_code.split("\n");
        const sell_lines = sell_code.split("\n");
        const climb = Math.min(0.92, 0.18 + (genNo + 1) / max * 0.85);
        const isErrorRoll = Math.random() < 0.06;
        let targetScore = isErrorRoll ? 0 : Math.max(0, climb + (Math.random() - 0.4) * 0.18);
        if (!isErrorRoll && genNo + 1 >= Math.floor(max * 0.55) && Math.random() < 0.22) {
          targetScore = +(target + Math.random() * 0.12).toFixed(3);
        }
        targetScore = +targetScore.toFixed(3);
        const profitW = 0.4, mddW = 0.2, tradesW = 0.2, consW = 0.2;
        const profit_factor = isErrorRoll ? 0 : Math.max(0, targetScore + (Math.random() - 0.5) * 0.15);
        const mdd_score = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.18));
        const trades_score = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.2));
        const cons_score = isErrorRoll ? 0 : Math.max(0, Math.min(1.2, targetScore + (Math.random() - 0.5) * 0.16));
        const metrics_def = [
          { key: "profit", label: "\uC190\uC775 (profit factor)", weight: profitW, value: +profit_factor.toFixed(3) },
          { key: "mdd", label: "MDD \uD398\uB110\uD2F0", weight: mddW, value: +mdd_score.toFixed(3) },
          { key: "trades", label: "\uAC70\uB798\uC218 \uC801\uC815\uC131", weight: tradesW, value: +trades_score.toFixed(3) },
          { key: "cons", label: "\uC77C\uAD00\uC131 (sharpe-ish)", weight: consW, value: +cons_score.toFixed(3) }
        ];
        const target_trades = isErrorRoll ? 0 : Math.max(0, Math.floor(profit_factor * 60 + (Math.random() - 0.3) * 20));
        const target_mdd_pct = isErrorRoll ? 0 : Math.max(2, Math.min(40, (1.4 - mdd_score) * 18 + (Math.random() - 0.5) * 4));
        const target_pnl = isErrorRoll ? 0 : Math.round((profit_factor - 0.4) * 35e5 + (Math.random() - 0.5) * 6e5);
        const willPass = !isErrorRoll && targetScore >= target && target_mdd_pct <= mddCap && target_trades >= minTrades;
        const autopsy_text = willPass ? `gen_${genNo + 1} \u2014 \uD558\uB4DC \uAC8C\uC774\uD2B8 \uD1B5\uACFC. graded_score=${targetScore.toFixed(3)} (target ${target.toFixed(2)}), MDD ${target_mdd_pct.toFixed(2)}% \u2264 ${mddCap}%, \uAC70\uB798 ${target_trades}\uD68C \u2265 ${minTrades}. \uB2E4\uC74C \uC138\uB300\uB294 \uB3D9\uC77C \uACE8\uACA9 \uC720\uC9C0\uD558\uBA70 \uC2AC\uB9AC\uD53C\uC9C0 \uAC00\uC815\uB9CC \uBCF4\uC218\uD654.` : isErrorRoll ? `gen_${genNo + 1} \u2014 \uB7F0\uD0C0\uC784 \uC608\uC678. \uC548\uC804\uD55C \uCEEC\uB7FC \uC811\uADFC \uBC0F None-\uAC00\uB4DC \uBCF4\uAC15 \uD544\uC694. \uB2E4\uC74C \uC138\uB300\uB294 fallback \uBD84\uAE30 \uCD94\uAC00.` : feedbackPool[Math.floor(Math.random() * feedbackPool.length)];
        const lastAutopsies = generations.slice(-2).map((g) => `gen_${g.gen_no}: ${g.gate_reason !== "\uC870\uAC74 \uCDA9\uC871" ? g.gate_reason : "\uD1B5\uACFC"} (score ${g.graded_score})`);
        return {
          buyTag,
          sellTag,
          buyName,
          sellName,
          buy_code,
          sell_code,
          buy_lines,
          sell_lines,
          metrics_def,
          autopsy_text,
          target_trades,
          target_mdd_pct,
          target_pnl,
          target_score: targetScore,
          is_error: isErrorRoll,
          gist: gistPool[Math.floor(Math.random() * gistPool.length)],
          prompt_context: lastAutopsies
        };
      }
      function resetGenRun(genNo) {
        currentRun = freshRun();
        plan = buildPlan(genNo);
        currentRun.generation.prompt_context = plan.prompt_context.slice();
        currentRun.generation.active = "buy";
        currentRun.autopsy.text_target = plan.autopsy_text;
        equityVal = 1e7;
        equityHigh = equityVal;
        runMinutes = 0;
        currentSymbol = pickSymbol();
        currentDay = 0;
        chunksDone = 0;
        genStartedAt.ms = Date.now();
      }
      resetGenRun(0);
      setState((s) => {
        var _a2;
        return {
          ...s,
          run_id: runId,
          status: "running",
          max_generations: max,
          current_gen: 0,
          provider,
          bt_timeframe: (_a2 = cfg.bt_timeframe) != null ? _a2 : "min",
          best: null,
          winner: null,
          generations: [],
          latest: { phase: "\uC0DD\uC131\uC911", last_checkpoint: "init", message: `\uC138\uB300 1 \uB9E4\uC218 \uC870\uAC74\uC2DD \uC0DD\uC131 \uC2DC\uC791 (provider=${provider})` },
          cumulative: { tokens: 0, cost_or_count: 0 },
          engine: {
            status: "running",
            cpu_pct: 6,
            mem_mb: 320,
            mem_cap_mb: memCap,
            workers,
            workers_active: 0,
            throughput: 0,
            elapsed_ms: 0,
            eta_ms: STEPS_PER_GEN * TICK_MS,
            current_symbol: "\u2014",
            current_window: { from: startDate, to: dateAdd(startDate, windowDays) },
            progress: 0,
            chunks_done: 0,
            chunks_total: totalChunks
          },
          current_run: cloneCurrentRun(),
          updated_at: (/* @__PURE__ */ new Date()).toISOString()
        };
      });
      function cloneCurrentRun() {
        return {
          equity: currentRun.equity.slice(),
          drawdown: currentRun.drawdown.slice(),
          trades: currentRun.trades.slice(),
          generation: { ...currentRun.generation, prompt_context: currentRun.generation.prompt_context.slice() },
          scoring: { ...currentRun.scoring, metrics: currentRun.scoring.metrics.slice() },
          autopsy: { ...currentRun.autopsy }
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
          phase = "\uC0DD\uC131\uC911";
          const frac = stepInGen / STEP_BUY_END;
          const linesToShow = Math.max(1, Math.ceil(plan.buy_lines.length * frac));
          currentRun.generation.active = "buy";
          currentRun.generation.buy_code_partial = plan.buy_lines.slice(0, linesToShow).join("\n");
          currentRun.generation.buy_done = linesToShow >= plan.buy_lines.length;
          currentRun.generation.stream_tokens = Math.round(tokens * 0.4);
          checkpoint = `BUY_${plan.buyTag} \uCF54\uB4DC \uC0DD\uC131 (${linesToShow}/${plan.buy_lines.length} \uB77C\uC778)`;
          message = `LLM(${provider}) \u2192 \uB9E4\uC218 \uC870\uAC74\uC2DD \uC2A4\uD2B8\uB9AC\uBC0D\uC911`;
          cpu = 8 + Math.random() * 5;
          mem = 360 + stepInGen * 14;
        } else if (stepInGen <= STEP_SELL_END) {
          phase = "\uC0DD\uC131\uC911";
          const sStep = stepInGen - STEP_BUY_END;
          const frac = sStep / (STEP_SELL_END - STEP_BUY_END);
          const linesToShow = Math.max(1, Math.ceil(plan.sell_lines.length * frac));
          currentRun.generation.active = "sell";
          currentRun.generation.buy_code_partial = plan.buy_code;
          currentRun.generation.buy_done = true;
          currentRun.generation.sell_code_partial = plan.sell_lines.slice(0, linesToShow).join("\n");
          currentRun.generation.sell_done = linesToShow >= plan.sell_lines.length;
          currentRun.generation.stream_tokens = Math.round(tokens * 0.7);
          checkpoint = `SELL_${plan.sellTag} \uCF54\uB4DC \uC0DD\uC131 (${linesToShow}/${plan.sell_lines.length} \uB77C\uC778)`;
          message = `LLM(${provider}) \u2192 \uB9E4\uB3C4 \uC870\uAC74\uC2DD \uC2A4\uD2B8\uB9AC\uBC0D\uC911`;
          cpu = 9 + Math.random() * 5;
          mem = 440 + sStep * 18;
          if (currentRun.generation.sell_done) {
            currentRun.generation.active = "done";
          }
        } else if (stepInGen <= STEP_BT_END) {
          phase = "\uBC31\uD14C\uC2A4\uD2B8\uC911";
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
          if (btStep === 1 || Math.random() < 0.25) currentSymbol = pickSymbol();
          currentDay = Math.floor(progress * windowDays);
          checkpoint = `chunk ${chunksDone}/${totalChunks} \xB7 ${currentSymbol[0]} ${currentSymbol[1]}`;
          message = `\uBC31\uD14C\uC2A4\uD2B8 \uC9C4\uD589 \u2014 ${dateAdd(startDate, currentDay)} \uCC98\uB9AC\uC911, \uC6CC\uCEE4 ${workersActive}/${workers} \uAC00\uB3D9`;
          const candlesPerTick = 25;
          const expectedFinalEquity = 1e7 + plan.target_pnl;
          const remainingTicks = btTotal - btStep + 1;
          for (let i = 0; i < candlesPerTick; i++) {
            runMinutes += 1;
            const drift = (expectedFinalEquity - equityVal) / Math.max(1, remainingTicks * candlesPerTick);
            const noise = (Math.random() - 0.5) * 12e3;
            equityVal = Math.max(equityVal + drift + noise, 1e7 * 0.7);
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
          phase = "\uCC44\uC810\uC911";
          const sStep = stepInGen - STEP_BT_END;
          const metrics = currentRun.scoring.metrics;
          const def = plan.metrics_def;
          if (metrics.length < def.length && sStep <= def.length) {
            metrics.push({ ...def[sStep - 1], ready: true });
          }
          if (sStep === STEP_SCORE_END - STEP_BT_END) {
            let comp = 0;
            for (const m of metrics) comp += m.value * m.weight;
            currentRun.scoring.composite = +comp.toFixed(3);
          }
          checkpoint = `metric ${Math.min(sStep, def.length)}/${def.length} \uCC44\uC810`;
          message = `\uC9C0\uD45C \uACC4\uC0B0 \u2014 ${sStep <= def.length ? def[sStep - 1].label : "composite score"}`;
          cpu = 22 + Math.random() * 10;
          mem = 1200 + Math.random() * 200;
          workersActive = 2;
        } else {
          phase = "\uBD80\uAC80 \uC791\uC131";
          const aStep = stepInGen - STEP_SCORE_END;
          const aTotal = STEP_AUT_END - STEP_SCORE_END;
          const fullText = plan.autopsy_text || "";
          const charsToShow = Math.ceil(fullText.length * (aStep / aTotal));
          currentRun.autopsy.text_partial = fullText.slice(0, charsToShow);
          currentRun.autopsy.ready = aStep >= aTotal;
          checkpoint = `autopsy ${charsToShow}/${fullText.length} chars`;
          message = `\uB2E4\uC74C \uC138\uB300 \uCEE8\uD14D\uC2A4\uD2B8\uC5D0 \uC8FC\uC785\uD560 \uBD80\uAC80 \uC694\uC57D \uC791\uC131\uC911...`;
          cpu = 10 + Math.random() * 5;
          mem = 800 + Math.random() * 100;
          workersActive = 1;
        }
        setState((s) => ({
          ...s,
          latest: { phase, last_checkpoint: checkpoint, message },
          cumulative: { tokens, cost_or_count: +(tokens * 15e-6).toFixed(4) },
          engine: {
            status: "running",
            cpu_pct: +cpu.toFixed(1),
            mem_mb: Math.round(mem),
            mem_cap_mb: memCap,
            workers,
            workers_active: workersActive,
            throughput,
            elapsed_ms: elapsedMs,
            eta_ms,
            current_symbol: phase === "\uBC31\uD14C\uC2A4\uD2B8\uC911" ? `${currentSymbol[0]} ${currentSymbol[1]}` : "\u2014",
            current_window: phase === "\uBC31\uD14C\uC2A4\uD2B8\uC911" ? { from: dateAdd(startDate, currentDay), to: dateAdd(startDate, Math.min(windowDays, currentDay + chunkDays)) } : { from: startDate, to: dateAdd(startDate, windowDays) },
            progress,
            chunks_done: chunksDone,
            chunks_total: totalChunks
          },
          current_run: cloneCurrentRun(),
          updated_at: (/* @__PURE__ */ new Date()).toISOString()
        }));
        if (stepInGen >= STEPS_PER_GEN) {
          finalizeGen();
        }
      }
      function finalizeGen() {
        var _a2;
        gen += 1;
        const isError = plan.is_error;
        const trade_count = isError ? 0 : Math.max(currentRun.trades.length, plan.target_trades);
        const final_equity = currentRun.equity.length ? currentRun.equity[currentRun.equity.length - 1].value : 1e7;
        const profit = isError ? 0 : Math.round(final_equity - 1e7);
        const peakDD = currentRun.drawdown.length ? Math.max(0, ...currentRun.drawdown.map((p) => p.value_pct)) : plan.target_mdd_pct;
        const mdd = +Math.min(40, Math.max(plan.target_mdd_pct, peakDD)).toFixed(2);
        const graded_score = isError ? 0 : (_a2 = currentRun.scoring.composite) != null ? _a2 : plan.target_score;
        const gate_passed = !isError && graded_score >= target && mdd <= mddCap && trade_count >= minTrades;
        let gate_reason = "\uC870\uAC74 \uCDA9\uC871";
        if (isError) gate_reason = "\uC2E4\uD589 \uC624\uB958";
        else if (trade_count === 0) gate_reason = "\uAC70\uB798 0\uAC74";
        else if (trade_count < minTrades) gate_reason = `\uAC70\uB798\uC218 \uBD80\uC871(${trade_count}/${minTrades})`;
        else if (mdd > mddCap) gate_reason = `MDD \uCD08\uACFC(${mdd}% > ${mddCap}%)`;
        else if (graded_score < target) gate_reason = `\uC810\uC218 \uBBF8\uB2EC(${graded_score.toFixed(3)} < ${target})`;
        const gist = plan.gist + " \u2014 " + (isError ? "\uB7F0\uD0C0\uC784 \uC608\uC678" : `\uC9C4\uC785 ${trade_count}\uD68C, MDD ${mdd}%`);
        const newGen = {
          gen_no: gen,
          status: isError ? "error" : "success",
          graded_score: +graded_score.toFixed(3),
          gate_passed,
          gate_reason,
          trade_count,
          mdd,
          profit,
          strategy_gist: gist,
          buy_name: plan.buyName,
          sell_name: plan.sellName,
          buy_code: plan.buy_code,
          sell_code: plan.sell_code,
          equity_curve: currentRun.equity.slice(),
          drawdown_curve: currentRun.drawdown.slice(),
          trades: currentRun.trades.slice(),
          score_breakdown: currentRun.scoring.metrics.slice(),
          autopsy: plan.autopsy_text
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
            phase: done ? "\uC644\uB8CC" : "\uC0DD\uC131\uC911",
            last_checkpoint: `gen_${gen} \uC885\uB8CC`,
            message: plan.autopsy_text
          },
          engine: {
            ...s.engine,
            status: done ? "idle" : "running",
            cpu_pct: done ? 4 : s.engine.cpu_pct,
            workers_active: done ? 0 : s.engine.workers_active,
            throughput: done ? 0 : s.engine.throughput,
            progress: 1,
            chunks_done: totalChunks
          },
          status: done ? "complete" : "running",
          updated_at: (/* @__PURE__ */ new Date()).toISOString()
        }));
        if (done) {
          stopDemo();
          return;
        }
        stepInGen = 0;
        resetGenRun(gen);
      }
      demoRef.current = setInterval(tick, TICK_MS);
    }, []);
    const stopDemo = () => {
      if (demoRef.current) {
        clearInterval(demoRef.current);
        demoRef.current = null;
      }
    };
    const stopDemoSoft = useCallback(() => {
      setState((s) => ({ ...s, status: "stopping", latest: { ...s.latest, message: "\uD604\uC7AC \uC138\uB300 \uC644\uB8CC \uD6C4 \uC815\uC9C0\uD569\uB2C8\uB2E4" } }));
      setTimeout(() => {
        stopDemo();
        setState((s) => ({ ...s, status: "complete", latest: { ...s.latest, phase: "\uC815\uC9C0\uB428", message: "\uC0AC\uC6A9\uC790 \uC694\uCCAD\uC73C\uB85C \uC815\uC9C0" } }));
      }, 1800);
    }, []);
    const tryConnect = useCallback(async () => {
      var _a;
      closedByUs.current = false;
      setWsStatus("connecting");
      try {
        const r = await fetch(baseUrl + "/health", { signal: AbortSignal.timeout(1500) });
        if (!r.ok) throw new Error("health failed");
        const j = await r.json();
        setHealth({ connected: true, contract_version: (_a = j.contract_version) != null ? _a : null });
        try {
          const cs = await fetch(baseUrl + "/config/spec", { signal: AbortSignal.timeout(1500) });
          if (cs.ok) {
            const csj = await cs.json();
            if (Array.isArray(csj) && csj.length) setConfigSpec(csj);
          }
        } catch (e) {
        }
        try {
          const st = await fetch(baseUrl + "/status", { signal: AbortSignal.timeout(1500) });
          if (st.ok) {
            const stj = await st.json();
            setState(stj);
          }
        } catch (e) {
        }
        openWs();
      } catch (e) {
        setHealth({ connected: false, contract_version: null });
        setWsStatus("demo");
      }
    }, [baseUrl]);
    const openWs = useCallback(() => {
      try {
        const wsUrl = baseUrl.replace(/^http/, "ws") + "/ws";
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onopen = () => {
          reconnectAttempt.current = 0;
          stopDemo();
          setWsStatus("open");
        };
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            if (data && typeof data === "object" && "contract_version" in data) {
              setState(data);
            } else if (data && typeof data === "object" && "action" in data) {
              setLastReply(data);
            }
          } catch (e) {
          }
        };
        ws.onclose = () => {
          if (closedByUs.current) return;
          setWsStatus("reconnecting");
          const delay = Math.min(8e3, 500 * Math.pow(1.7, reconnectAttempt.current));
          reconnectAttempt.current += 1;
          setTimeout(() => {
            if (!closedByUs.current) openWs();
          }, delay);
        };
        ws.onerror = () => {
        };
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
    const send = useCallback((msg) => {
      if (wsStatus === "demo" || !wsRef.current || wsRef.current.readyState !== 1) {
        if (msg.action === "start") {
          startDemo(msg.config);
        } else if (msg.action === "stop") {
          stopDemoSoft();
        } else if (msg.action === "final_approval") {
          setState((s) => ({
            ...s,
            status: "complete",
            latest: { ...s.latest, phase: "\uC2B9\uC778 \uC644\uB8CC", message: `${msg.user_buy} / ${msg.user_sell} \uC6B4\uC601 DB\uB85C \uB0B4\uBCF4\uB0C4` }
          }));
          setLastReply({
            action: "final_approval",
            status: "ok",
            demo: true,
            buy: { name: msg.user_buy },
            sell: { name: msg.user_sell }
          });
        }
        return true;
      }
      try {
        wsRef.current.send(JSON.stringify(msg));
        return true;
      } catch (e) {
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
      reconnect: tryConnect
    };
  }
  var fmtScore2 = window.fmtScore;
  var fmtPct2 = window.fmtPct;
  var fmtMoney2 = window.fmtMoney;
  var fmtInt2 = window.fmtInt;
  var fmtTime2 = window.fmtTime;
  var STATUS_KR = window.STATUS_KR;
  Object.assign(window, {
    useBackend: useBackend2,
    DEFAULT_BASE: DEFAULT_BASE2,
    // 포매터·STATUS_KR 는 빌드 번들이 이미 window 에 세팅(중복 노출 제거).
    // LIVE↔DEMO 경계 판정은 아직 connection.jsx 정의 유지(번들도 동일 제공) — 14.x에서 통합.
    isDemoSource,
    livePanelPending
  });

  // ../frontend/ai-context.jsx
  var { useState: useState_ac, useEffect: useEffect_ac } = React;
  function packText(value, fallback = "-") {
    if (value === null || value === void 0 || value === "") return fallback;
    return typeof value === "string" ? value : JSON.stringify(value, null, 2);
  }
  function AIContextPanel2({ baseUrl, wsStatus, runId, genNo }) {
    const [pack, setPack] = useState_ac(null);
    const [loading, setLoading] = useState_ac(false);
    const [err, setErr] = useState_ac("");
    const [copied, setCopied] = useState_ac(false);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const loadPack = React.useCallback(() => {
      if (isDemo || !baseUrl || !runId) return;
      setLoading(true);
      setErr("");
      const suffix = genNo != null ? "&gen_no=" + encodeURIComponent(genNo) : "";
      fetch(
        baseUrl + "/ai_context_pack?run_id=" + encodeURIComponent(runId) + suffix,
        { signal: AbortSignal.timeout(4e3) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => setPack(j || null)).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId, genNo]);
    useEffect_ac(() => {
      loadPack();
    }, [loadPack]);
    const copyPack = async () => {
      try {
        const text = pack ? pack.summary_text ? `${pack.summary_text}

context_pack:
${JSON.stringify(pack.context_pack || {}, null, 2)}` : JSON.stringify(pack.context_pack || pack, null, 2) : "";
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      } catch (e) {
      }
    };
    const contextPack = pack && pack.context_pack ? pack.context_pack : null;
    const guideContext = packText(contextPack && contextPack.guide_context, pack && pack.summary_text);
    const diffContext = packText(
      contextPack && contextPack.diff_context,
      pack ? [
        `strategy_buy: ${pack.strategy_names && pack.strategy_names.buy || "-"}`,
        `strategy_sell: ${pack.strategy_names && pack.strategy_names.sell || "-"}`,
        `verdict: ${pack.verdict_note || "-"}`
      ].join("\n") : "-"
    );
    const analysisContext = packText(
      contextPack && contextPack.analysis_context,
      pack && pack.analysis
    );
    const correlationContext = packText(
      contextPack && contextPack.correlation_context,
      pack && pack.analysis && pack.analysis.variable_correlation
    );
    return /* @__PURE__ */ React.createElement("div", { className: "panel ai-context-panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "AI State Context", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: loadPack, disabled: isDemo || loading || !runId }, loading ? "loading" : "refresh"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: copyPack, disabled: !pack }, copied ? "copied" : "copy AI state"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "ai-context-empty" }, "Backend connection required.") : err ? /* @__PURE__ */ React.createElement("div", { className: "ai-context-empty danger" }, "context pack failed: ", err) : !pack ? /* @__PURE__ */ React.createElement("div", { className: "ai-context-empty" }, "No context pack loaded.") : pack.error ? /* @__PURE__ */ React.createElement("div", { className: "ai-context-empty danger" }, pack.error) : /* @__PURE__ */ React.createElement("div", { className: "ai-context-body" }, /* @__PURE__ */ React.createElement("div", { className: "ai-context-kpis" }, /* @__PURE__ */ React.createElement("span", null, "run_id=", pack.run_id), /* @__PURE__ */ React.createElement("span", null, "gen_no=", pack.gen_no), /* @__PURE__ */ React.createElement("span", null, "timeframe=", pack.timeframe || "-"), /* @__PURE__ */ React.createElement("span", null, "prompt_count=", pack.prompt_count || 0)), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, pack.summary_text), /* @__PURE__ */ React.createElement("div", { className: "ai-context-pack" }, /* @__PURE__ */ React.createElement("div", { className: "ai-context-pack-head" }, /* @__PURE__ */ React.createElement("strong", null, "context_pack"), /* @__PURE__ */ React.createElement("span", null, contextPack ? Object.keys(contextPack).length + " sections" : "-")), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, JSON.stringify(contextPack, null, 2))), /* @__PURE__ */ React.createElement("div", { className: "ai-context-actions" }, /* @__PURE__ */ React.createElement("span", null, "guide_context"), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, guideContext), /* @__PURE__ */ React.createElement("span", null, "diff_context"), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, diffContext), /* @__PURE__ */ React.createElement("span", null, "analysis_context"), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, analysisContext), /* @__PURE__ */ React.createElement("span", null, "correlation_context"), /* @__PURE__ */ React.createElement("pre", { className: "ai-context-summary" }, correlationContext)), /* @__PURE__ */ React.createElement("div", { className: "ai-context-actions" }, /* @__PURE__ */ React.createElement("strong", null, "forbidden_actions"), (pack.forbidden_actions || []).map((item, i) => /* @__PURE__ */ React.createElement("span", { key: i }, item))))));
  }
  Object.assign(window, { AIContextPanel: AIContextPanel2 });

  // ../frontend/research-pro.jsx
  var {
    useState: useState_rp,
    useEffect: useEffect_rp,
    useCallback: useCallback_rp,
    useMemo: useMemo_rp,
    useRef: useRef_rp
  } = React;
  function _rpFetchJson(url, timeoutMs) {
    return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 8e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  function _rpPostJson(url, body, timeoutMs) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal: AbortSignal.timeout(timeoutMs || 8e3)
    }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  var _rpMoney = (v) => typeof window.fmtMoney === "function" ? window.fmtMoney(v) : typeof v === "number" && isFinite(v) ? Math.round(v).toLocaleString("ko-KR") + "\uC6D0" : "\u2014";
  var _rpInt = (v) => typeof v === "number" && isFinite(v) ? Math.round(v).toLocaleString("ko-KR") : "\u2014";
  var _rpNum = (v, d) => typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 2 : d) : "\u2014";
  var _rpPct = (v, d) => typeof v === "number" && isFinite(v) ? v.toFixed(d == null ? 1 : d) + "%" : "\u2014";
  function _rpOpenWorkbench(runId, genNo, onOpenWorkbench) {
    const detail = { run_id: runId, gen_no: genNo };
    try {
      window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
      localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
    } catch (e) {
    }
    if (typeof onOpenWorkbench === "function") onOpenWorkbench(detail);
  }
  function _rpEdgeColor(er, alpha) {
    if (typeof er !== "number" || !isFinite(er)) return "rgba(40,50,60,0.4)";
    const a = alpha == null ? 0.85 : alpha;
    const d = Math.max(-1, Math.min(1, er - 1));
    if (d >= 0) {
      const t2 = Math.min(1, d / 0.6);
      return `rgba(${Math.round(60 - 25 * t2)},${Math.round(170 + 20 * t2)},${Math.round(120 + 10 * t2)},${a})`;
    }
    const t = Math.min(1, -d / 0.6);
    return `rgba(${Math.round(200 + 40 * t)},${Math.round(110 - 40 * t)},${Math.round(90 - 30 * t)},${a})`;
  }
  function _RpVarChips({ baseUrl, isDemo, code }) {
    if (typeof window.BtVarChips === "function") {
      return React.createElement(window.BtVarChips, { baseUrl, isDemo, code });
    }
    const [known, setKnown] = useState_rp([]);
    const [unknown, setUnknown] = useState_rp([]);
    useEffect_rp(() => {
      if (isDemo || !baseUrl) {
        setKnown([]);
        setUnknown([]);
        return void 0;
      }
      const trimmed = (code || "").trim();
      if (!trimmed) {
        setKnown([]);
        setUnknown([]);
        return void 0;
      }
      let cancelled = false;
      const t = setTimeout(() => {
        _rpPostJson(baseUrl + "/bt/extract_vars", { code: trimmed }, 5e3).then((j) => {
          if (cancelled) return;
          setKnown(Array.isArray(j && j.known) ? j.known : []);
          setUnknown(Array.isArray(j && j.unknown) ? j.unknown : []);
        }).catch(() => {
          if (!cancelled) {
            setKnown([]);
            setUnknown([]);
          }
        });
      }, 350);
      return () => {
        cancelled = true;
        clearTimeout(t);
      };
    }, [baseUrl, isDemo, code]);
    if (known.length === 0 && unknown.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC0AC\uC6A9 \uBCC0\uC218 \uCE69 \u2014 \uC870\uAC74\uC2DD\uC758 \uD55C\uAE00 \uBCC0\uC218\uAC00 SSOT \uD654\uC774\uD2B8\uB9AC\uC2A4\uD2B8\uC640 \uB300\uC870\uB418\uC5B4 \uD45C\uC2DC\uB429\uB2C8\uB2E4.");
    }
    const chip = (v, ok) => /* @__PURE__ */ React.createElement(
      "span",
      {
        key: (ok ? "k:" : "u:") + v.name,
        className: "mono rp-chip",
        title: ok ? "SSOT \uD654\uC774\uD2B8\uB9AC\uC2A4\uD2B8 \uBCC0\uC218" : "SSOT \uC5B4\uD718 \uBC16 \u2014 \uC624\uD0C0\uC774\uAC70\uB098 \uBBF8\uC815\uC758 \uBCC0\uC218\uC77C \uC218 \uC788\uC2B5\uB2C8\uB2E4",
        style: {
          border: "1px solid " + (ok ? "var(--teal-dim)" : "rgba(240,179,90,0.45)"),
          color: ok ? "var(--teal)" : "var(--amber)",
          background: ok ? "rgba(76,214,179,0.06)" : "rgba(240,179,90,0.06)"
        }
      },
      ok ? "" : "\u26A0 ",
      v.name,
      v.count > 1 && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "\xD7", v.count)
    );
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 5 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 4 } }, known.map((v) => chip(v, true)), unknown.map((v) => chip(v, false))), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "SSOT \uBCC0\uC218 ", known.length, " \xB7 \uBBF8\uD655\uC778 ", unknown.length));
  }
  function _RpStrategyCode({ baseUrl, isDemo, runId, genNo }) {
    const [code, setCode] = useState_rp(null);
    const [loading, setLoading] = useState_rp(false);
    useEffect_rp(() => {
      if (isDemo || !baseUrl || !runId || genNo == null || genNo < 0) {
        setCode(null);
        return void 0;
      }
      let cancelled = false;
      setLoading(true);
      _rpFetchJson(
        baseUrl + "/strategy_code?run=" + encodeURIComponent(runId) + "&gen=" + encodeURIComponent(genNo),
        8e3
      ).then((j) => {
        if (!cancelled) setCode(j || null);
      }).catch(() => {
        if (!cancelled) setCode(null);
      }).finally(() => {
        if (!cancelled) setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, runId, genNo]);
    if (loading) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono rp-code-empty" }, "\uC870\uAC74\uC2DD \uBD88\uB7EC\uC624\uB294 \uC911\u2026");
    }
    if (!code) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono rp-code-empty" }, "\uC870\uAC74\uC2DD \uC815\uBCF4 \uC5C6\uC74C");
    }
    const buy = code.buy_code || "";
    const sell = code.sell_code || "";
    if (!buy && !sell) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono rp-code-empty" }, "\uC774 \uC138\uB300\uC758 \uC870\uAC74\uC2DD \uCF54\uB4DC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4", code.reason ? ` (${code.reason})` : "", ".");
    }
    return /* @__PURE__ */ React.createElement("div", { className: "rp-code-grid" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "rp-code-label", style: { color: "var(--teal)" } }, "\uB9E4\uC218 \uC870\uAC74\uC2DD ", code.buy_name ? `\xB7 ${code.buy_name}` : ""), /* @__PURE__ */ React.createElement("pre", { className: "rp-code-block" }, buy || "(\uC5C6\uC74C)"), /* @__PURE__ */ React.createElement(_RpVarChips, { baseUrl, isDemo, code: buy })), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "rp-code-label", style: { color: "var(--blue)" } }, "\uB9E4\uB3C4 \uC870\uAC74\uC2DD ", code.sell_name ? `\xB7 ${code.sell_name}` : ""), /* @__PURE__ */ React.createElement("pre", { className: "rp-code-block" }, sell || "(\uC5C6\uC74C)"), /* @__PURE__ */ React.createElement(_RpVarChips, { baseUrl, isDemo, code: sell })));
  }
  function _RpBigHeatmap({ baseUrl, isDemo, runId }) {
    const [data, setData] = useState_rp(null);
    const [loading, setLoading] = useState_rp(false);
    const [err, setErr] = useState_rp(null);
    const refresh = useCallback_rp(() => {
      if (isDemo || !baseUrl || !runId) {
        setData(null);
        return;
      }
      setLoading(true);
      _rpFetchJson(
        baseUrl + "/edge_ratio?run_ids=" + encodeURIComponent(runId) + "&fine_time=true",
        8e3
      ).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId]);
    useEffect_rp(() => {
      refresh();
    }, [refresh]);
    const grid = useMemo_rp(() => {
      const cross = data && data.segments && data.segments.cross || [];
      if (!cross.length) return null;
      const timeLabels = [];
      const capLabels = [];
      const cellMap = {};
      for (const c of cross) {
        const parts = (c.label || "").split("\xD7");
        const tl = parts[0] ? parts[0].trim() : c.label;
        const cl = parts[1] ? parts[1].trim() : "";
        if (!timeLabels.includes(tl)) timeLabels.push(tl);
        if (cl && !capLabels.includes(cl)) capLabels.push(cl);
        cellMap[tl + "\xD7" + cl] = c;
      }
      if (capLabels.length === 0) return null;
      return { timeLabels, capLabels, cellMap };
    }, [data]);
    const globalEr = data && data.global && typeof data.global.edge_ratio === "number" ? data.global.edge_ratio : null;
    return /* @__PURE__ */ React.createElement("div", { className: "rp-card" }, /* @__PURE__ */ React.createElement("div", { className: "rp-card-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\uC2DC\uAC04\uB300 \xD7 \uC2DC\uAC00\uCD1D\uC561 \uD0D0\uC0C9 \uD788\uD2B8\uB9F5"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "rp-help",
        title: "Edge Ratio = \uC720\uB9AC\uD55C \uAC00\uACA9 \uC9C4\uD589 / \uBD88\uB9AC\uD55C \uAC00\uACA9 \uC9C4\uD589. 1.0 \uCD08\uACFC\uBA74 \uD3C9\uADE0\uC801\uC73C\uB85C \uC720\uB9AC\uD55C \uAD6C\uAC04\uC785\uB2C8\uB2E4. \uC2DC\uAC04\uB300(\uD589) \xD7 \uC2DC\uAC00\uCD1D\uC561(\uC5F4) \uAD50\uCC28\uC5D0\uC11C \uC5B4\uB290 \uD658\uACBD\uC774 \uC6B0\uC704\uC778\uC9C0 \uD55C\uB208\uC5D0 \uBD05\uB2C8\uB2E4."
      },
      "?"
    ), globalEr != null && /* @__PURE__ */ React.createElement("span", { className: "rp-card-sub" }, "\uC804\uCCB4 edge ", _rpNum(globalEr, 3)), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", style: { marginLeft: "auto" }, onClick: refresh, disabled: isDemo || loading }, loading ? "\uC870\uD68C\uC911\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68")), /* @__PURE__ */ React.createElement("div", { className: "rp-card-bd" }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uB77C\uC774\uBE0C run \uC5F0\uACB0 \uC2DC \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : !runId ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "run\uC744 \uC120\uD0DD\uD558\uBA74 \uC2DC\uAC04\uB300\xD7\uC2DC\uCD1D \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : err ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uC870\uD68C \uC2E4\uD328 \u2014 ", err) : !grid ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uAD50\uCC28 \uC138\uADF8\uBA3C\uD2B8(\uC2DC\uAC04\uB300\xD7\uC2DC\uCD1D)\uAC00 \uB204\uC801\uB418\uBA74 \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.", loading ? " (\uB85C\uB529\uC911\u2026)" : "") : /* @__PURE__ */ React.createElement(_RpHeatmapGrid, { grid })));
  }
  function _RpHeatmapGrid({ grid }) {
    const { timeLabels, capLabels, cellMap } = grid;
    const cols = `120px repeat(${capLabels.length}, minmax(64px, 1fr))`;
    return /* @__PURE__ */ React.createElement("div", { className: "rp-heatmap", style: { gridTemplateColumns: cols } }, /* @__PURE__ */ React.createElement("div", { className: "rp-heatmap-corner mono" }, "\uC2DC\uAC04\uB300 \\ \uC2DC\uCD1D"), capLabels.map((cl) => /* @__PURE__ */ React.createElement("div", { key: "h" + cl, className: "rp-heatmap-colhd mono", title: cl }, cl)), timeLabels.map((tl) => /* @__PURE__ */ React.createElement(React.Fragment, { key: "r" + tl }, /* @__PURE__ */ React.createElement("div", { className: "rp-heatmap-rowhd mono", title: tl }, tl), capLabels.map((cl) => {
      const cell = cellMap[tl + "\xD7" + cl];
      const er = cell ? cell.edge_ratio : null;
      const bg = _rpEdgeColor(er, 0.85);
      const strong = er != null && Math.abs(er - 1) > 0.15;
      return /* @__PURE__ */ React.createElement(
        "div",
        {
          key: "c" + tl + cl,
          className: "rp-heatmap-cell mono",
          style: { background: bg, color: strong ? "#fff" : "var(--ink-1)" },
          title: cell ? `${tl} \xD7 ${cl} \xB7 edge ${_rpNum(er, 3)} \xB7 ${cell.count || 0}\uAC74` + (typeof cell.win_rate === "number" ? ` \xB7 \uC2B9\uB960 ${_rpPct(cell.win_rate * 100)}` : "") : `${tl} \xD7 ${cl} \xB7 \uB370\uC774\uD130 \uC5C6\uC74C`
        },
        /* @__PURE__ */ React.createElement("strong", null, er != null ? _rpNum(er, 2) : "\u2014"),
        cell && typeof cell.count === "number" && /* @__PURE__ */ React.createElement("small", null, cell.count, "\uAC74")
      );
    }))));
  }
  function _RpHallOfFame({ baseUrl, isDemo, onOpenWorkbench }) {
    const [hof, setHof] = useState_rp(null);
    const [loading, setLoading] = useState_rp(false);
    const [expanded, setExpanded] = useState_rp(null);
    const refresh = useCallback_rp(() => {
      if (isDemo || !baseUrl) {
        setHof(null);
        return;
      }
      setLoading(true);
      _rpFetchJson(baseUrl + "/hall_of_fame", 8e3).then((j) => setHof(j)).catch(() => setHof(null)).finally(() => setLoading(false));
    }, [baseUrl, isDemo]);
    useEffect_rp(() => {
      refresh();
    }, [refresh]);
    const ai = (hof && Array.isArray(hof.ai) ? hof.ai : []).filter((r) => r.run_id && r.gen_no != null);
    return /* @__PURE__ */ React.createElement("div", { className: "rp-card" }, /* @__PURE__ */ React.createElement("div", { className: "rp-card-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\u{1F3C6} \uBA85\uC608\uC758 \uC804\uB2F9 \uD504\uB85C \u2014 \uC870\uAC74\uC2DD \xB7 \uBC14\uB85C \uC0AC\uC6A9"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "rp-help",
        title: "\uAC8C\uC774\uD2B8\uB97C \uD1B5\uACFC\uD55C \uD751\uC790 \uC804\uB7B5\uC744 \uC810\uC218 \uB0B4\uB9BC\uCC28\uC21C\uC73C\uB85C \uBCF4\uC5EC\uC90D\uB2C8\uB2E4. \uD589\uC744 \uD3BC\uCE58\uBA74 \uB9E4\uC218\xB7\uB9E4\uB3C4 \uC870\uAC74\uC2DD\uACFC \uBCC0\uC218 \uCE69\uC744 \uD655\uC778\uD558\uACE0, '\uBC14\uB85C \uBC31\uD14C\uC2A4\uD2B8'\uB85C \uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0 \uADF8\uB300\uB85C \uC801\uC7AC\uD569\uB2C8\uB2E4."
      },
      "?"
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", style: { marginLeft: "auto" }, onClick: refresh, disabled: isDemo || loading }, loading ? "\uC870\uD68C\uC911\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68")), /* @__PURE__ */ React.createElement("div", { className: "rp-card-bd" }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uBA85\uC608\uC758 \uC804\uB2F9\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : ai.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uAC8C\uC774\uD2B8 \uD1B5\uACFC \uC804\uB7B5\uC774 \uB204\uC801\uB418\uBA74 \uD45C\uC2DC\uB429\uB2C8\uB2E4.", loading ? " (\uB85C\uB529\uC911\u2026)" : "") : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "rp-table mono" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC885\uB958"), /* @__PURE__ */ React.createElement("th", null, "\uC804\uB7B5(run/gen)"), /* @__PURE__ */ React.createElement("th", null, "\uBC31\uD14C \uAE30\uAC04"), /* @__PURE__ */ React.createElement("th", null, "\uC810\uC218"), /* @__PURE__ */ React.createElement("th", null, "\uCD1D\uC218\uC775"), /* @__PURE__ */ React.createElement("th", null, "\uC218\uC775\uB960"), /* @__PURE__ */ React.createElement("th", null, "\uC5F0\uD658\uC0B0"), /* @__PURE__ */ React.createElement("th", null, "MDD"), /* @__PURE__ */ React.createElement("th", null, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", null))), /* @__PURE__ */ React.createElement("tbody", null, ai.map((r) => {
      const key = r.run_id + "/" + r.gen_no;
      const isOpen = expanded === key;
      return /* @__PURE__ */ React.createElement(React.Fragment, { key }, /* @__PURE__ */ React.createElement("tr", { className: isOpen ? "rp-row-open" : "" }, /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement("span", { className: "rp-kind rp-kind-" + (r.kind || "ai") }, r.kind === "seed" ? "\uC2DC\uB4DC" : "AI")), /* @__PURE__ */ React.createElement("td", { title: r.buy_name || "" }, r.label || key), /* @__PURE__ */ React.createElement("td", null, r.period || "\uAE30\uAC04 \uC815\uBCF4 \uC5C6\uC74C"), /* @__PURE__ */ React.createElement("td", { style: { color: "var(--teal)" } }, _rpNum(r.score, 3)), /* @__PURE__ */ React.createElement("td", { className: r.total_return_krw > 0 ? "rp-pos" : "rp-neg" }, _rpMoney(r.total_return_krw)), /* @__PURE__ */ React.createElement("td", null, _rpPct(r.total_return_pct)), /* @__PURE__ */ React.createElement("td", { title: r.annual_unreliable ? "\uCC3D \uAE38\uC774 0.25\uB144 \uBBF8\uB9CC \u2014 \uC5F0\uD658\uC0B0 \uACFC\uB300 \uC8FC\uC758" : "" }, _rpPct(r.annual_return_pct), r.annual_unreliable ? " \u26A0" : ""), /* @__PURE__ */ React.createElement("td", { style: { color: "var(--red)" } }, _rpPct(r.mdd_pct)), /* @__PURE__ */ React.createElement("td", null, _rpInt(r.trades)), /* @__PURE__ */ React.createElement("td", { style: { whiteSpace: "nowrap" } }, /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          onClick: () => setExpanded(isOpen ? null : key),
          "data-tip": "\uC870\uAC74\uC2DD\xB7\uBCC0\uC218 \uCE69 \uD3BC\uCE58\uAE30"
        },
        isOpen ? "\u25B2 \uB2EB\uAE30" : "\u25BC \uC870\uAC74\uC2DD"
      ), /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          style: { marginLeft: 4 },
          onClick: () => _rpOpenWorkbench(r.run_id, r.gen_no, onOpenWorkbench),
          "data-tip": "\uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0 \uC774 \uC804\uB7B5\uC744 \uC801\uC7AC\uD558\uACE0 \uC804\uD658"
        },
        "\uBC14\uB85C \uBC31\uD14C\uC2A4\uD2B8"
      ))), isOpen && /* @__PURE__ */ React.createElement("tr", { className: "rp-row-detail" }, /* @__PURE__ */ React.createElement("td", { colSpan: 10 }, /* @__PURE__ */ React.createElement(_RpStrategyCode, { baseUrl, isDemo, runId: r.run_id, genNo: r.gen_no }))));
    }))))));
  }
  function _RpRunCompare({ baseUrl, isDemo, runList, currentRunId, currentGenNo, onOpenWorkbench }) {
    const [items, setItems] = useState_rp([]);
    const [addRun, setAddRun] = useState_rp("");
    const [addGen, setAddGen] = useState_rp(0);
    const add = useCallback_rp(
      (runId, genNo) => {
        if (isDemo || !baseUrl || !runId || genNo == null) return;
        const key = runId + "/" + genNo;
        setItems((prev) => {
          if (prev.some((p) => p.key === key)) return prev;
          return [...prev, { key, run_id: runId, gen_no: genNo, result: null, loading: true }];
        });
        _rpFetchJson(
          baseUrl + "/bt/result?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(genNo),
          9e3
        ).then((j) => {
          setItems(
            (prev) => prev.map((p) => p.key === key ? { ...p, result: j, loading: false } : p)
          );
        }).catch(() => {
          setItems((prev) => prev.map((p) => p.key === key ? { ...p, loading: false } : p));
        });
      },
      [baseUrl, isDemo]
    );
    const remove = useCallback_rp((key) => {
      setItems((prev) => prev.filter((p) => p.key !== key));
    }, []);
    const metricOf = (it) => {
      const m = it.result && (it.result.metrics || it.result.analysis && it.result.analysis.summary) || {};
      return m || {};
    };
    return /* @__PURE__ */ React.createElement("div", { className: "rp-card" }, /* @__PURE__ */ React.createElement("div", { className: "rp-card-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "Run Compare \uD504\uB85C \u2014 \uC88B\uC740 \uACB0\uACFC\uB97C \uBC14\uB85C \uC0AC\uC6A9"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "rp-help",
        title: "\uC5EC\uB7EC run/\uC138\uB300 \uACB0\uACFC\uB97C \uB098\uB780\uD788 \uBE44\uAD50\uD569\uB2C8\uB2E4. \uAC01 \uD589\uC5D0\uC11C '\uBC14\uB85C \uBC31\uD14C\uC2A4\uD2B8'\uB85C \uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0 \uC801\uC7AC\uD574 \uC815\uBC00 \uBD84\uC11D\uD569\uB2C8\uB2E4."
      },
      "?"
    )), /* @__PURE__ */ React.createElement("div", { className: "rp-card-bd" }, /* @__PURE__ */ React.createElement("div", { className: "rp-compare-add" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => add(currentRunId, currentGenNo),
        disabled: isDemo || !currentRunId,
        "data-tip": "\uC0C1\uB2E8\uC5D0\uC11C \uC120\uD0DD\uD55C run\xB7\uC138\uB300\uB97C \uBE44\uAD50\uC5D0 \uCD94\uAC00"
      },
      "+ \uD604\uC7AC \uC120\uD0DD \uCD94\uAC00 (",
      currentRunId || "\u2014",
      "/g",
      currentGenNo,
      ")"
    ), /* @__PURE__ */ React.createElement("span", { className: "rp-compare-sep" }, "\uB610\uB294"), /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "mono rp-select",
        value: addRun,
        onChange: (e) => setAddRun(e.target.value),
        disabled: isDemo
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "run \uC120\uD0DD"),
      (runList || []).map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : ""))
    ), /* @__PURE__ */ React.createElement("label", { className: "rp-compare-genlbl mono" }, "gen", /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        min: 0,
        value: addGen,
        onChange: (e) => setAddGen(Number(e.target.value) || 0),
        className: "rp-num-input mono"
      }
    )), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => add(addRun, addGen),
        disabled: isDemo || !addRun
      },
      "+ \uCD94\uAC00"
    )), items.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uBE44\uAD50\uD560 run/\uC138\uB300\uB97C \uCD94\uAC00\uD558\uC138\uC694.") : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "rp-table mono" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "run / gen"), /* @__PURE__ */ React.createElement("th", null, "\uCD1D\uC190\uC775"), /* @__PURE__ */ React.createElement("th", null, "MDD"), /* @__PURE__ */ React.createElement("th", null, "\uC2B9\uB960"), /* @__PURE__ */ React.createElement("th", null, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", null, "Payoff"), /* @__PURE__ */ React.createElement("th", null))), /* @__PURE__ */ React.createElement("tbody", null, items.map((it) => {
      const m = metricOf(it);
      return /* @__PURE__ */ React.createElement("tr", { key: it.key }, /* @__PURE__ */ React.createElement("td", null, it.key), it.loading ? /* @__PURE__ */ React.createElement("td", { colSpan: 5, className: "rp-muted" }, "\uBD88\uB7EC\uC624\uB294 \uC911\u2026") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("td", { className: m.total_profit > 0 ? "rp-pos" : "rp-neg" }, _rpMoney(m.total_profit != null ? m.total_profit : m.profit)), /* @__PURE__ */ React.createElement("td", { style: { color: "var(--red)" } }, _rpPct(m.mdd)), /* @__PURE__ */ React.createElement("td", null, _rpPct(m.win_rate != null ? m.win_rate * 100 : m.win_rate_pct)), /* @__PURE__ */ React.createElement("td", null, _rpInt(m.trade_count != null ? m.trade_count : m.trades)), /* @__PURE__ */ React.createElement("td", null, _rpNum(m.payoff_ratio != null ? m.payoff_ratio : m.payoff, 2))), /* @__PURE__ */ React.createElement("td", { style: { whiteSpace: "nowrap" } }, /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          onClick: () => _rpOpenWorkbench(it.run_id, it.gen_no, onOpenWorkbench),
          "data-tip": "\uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0 \uC801\uC7AC"
        },
        "\uBC14\uB85C \uBC31\uD14C\uC2A4\uD2B8"
      ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", style: { marginLeft: 4 }, onClick: () => remove(it.key) }, "\u2715")));
    }))))));
  }
  function _RpHistory({ baseUrl, isDemo, runList, onOpenWorkbench }) {
    const [selRun, setSelRun] = useState_rp("");
    const [gens, setGens] = useState_rp([]);
    const [selGen, setSelGen] = useState_rp(null);
    const [loading, setLoading] = useState_rp(false);
    useEffect_rp(() => {
      if (isDemo || !baseUrl || !selRun) {
        setGens([]);
        setSelGen(null);
        return void 0;
      }
      let cancelled = false;
      setLoading(true);
      _rpFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(selRun), 9e3).then((j) => {
        if (cancelled) return;
        const items = Array.isArray(j && j.items) ? j.items : [];
        setGens(items);
        const ranked = items.filter((g) => g.gen_no >= 0).slice().sort((a, b) => (b.score || 0) - (a.score || 0));
        const best = ranked.find((g) => g.gate_passed) || ranked[0];
        setSelGen(best ? best.gen_no : null);
      }).catch(() => {
        if (!cancelled) {
          setGens([]);
          setSelGen(null);
        }
      }).finally(() => {
        if (!cancelled) setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, selRun]);
    const topGens = useMemo_rp(
      () => gens.filter((g) => g.gen_no >= 0).slice().sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 12),
      [gens]
    );
    const hasBt = typeof window.BtResultArea === "function";
    return /* @__PURE__ */ React.createElement("div", { className: "rp-card" }, /* @__PURE__ */ React.createElement("div", { className: "rp-card-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\uD788\uC2A4\uD1A0\uB9AC \u2014 \uACFC\uAC70 \uC5F0\uAD6C \uC7AC\uC5F4\uB78C"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "rp-help",
        title: "\uACFC\uAC70 run\uC744 \uACE8\uB77C \uC138\uB300\uBCC4 \uC870\uAC74\uC2DD\uACFC \uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uACFC \uB3D9\uC77C\uD55C \uC0C1\uC138 \uACB0\uACFC \uC2DC\uAC01\uD654(\uC790\uBCF8\uACE1\uC120\xB7\uBD84\uD3EC\xB7\uD788\uD2B8\uB9F5\xB7\uC5B8\uB354\uC6CC\uD130 \uB4F1)\uB97C \uB2E4\uC2DC \uBD05\uB2C8\uB2E4."
      },
      "?"
    )), /* @__PURE__ */ React.createElement("div", { className: "rp-card-bd" }, /* @__PURE__ */ React.createElement("div", { className: "rp-history-bar" }, /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "mono rp-select",
        value: selRun,
        onChange: (e) => setSelRun(e.target.value),
        disabled: isDemo
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "\uACFC\uAC70 run \uC120\uD0DD\u2026"),
      (runList || []).map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : "", r.gate_passed_count > 0 ? " \u2713" : ""))
    ), loading && /* @__PURE__ */ React.createElement("span", { className: "rp-muted mono" }, "\uC138\uB300 \uBD88\uB7EC\uC624\uB294 \uC911\u2026")), !selRun ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uACFC\uAC70 run\uC744 \uC120\uD0DD\uD558\uBA74 \uC138\uB300\xB7\uC870\uAC74\uC2DD\xB7\uC0C1\uC138 \uACB0\uACFC\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", { className: "rp-history-grid" }, /* @__PURE__ */ React.createElement("div", { className: "rp-history-genlist" }, /* @__PURE__ */ React.createElement("div", { className: "rp-mini-label" }, "\uC138\uB300 (score \uB0B4\uB9BC\uCC28\uC21C)"), topGens.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uC138\uB300 \uC5C6\uC74C") : topGens.map((g) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: g.gen_no,
        className: "rp-gen-btn mono" + (selGen === g.gen_no ? " active" : ""),
        onClick: () => setSelGen(g.gen_no),
        title: `score ${_rpNum(g.score, 3)} \xB7 \uC190\uC775 ${_rpMoney(g.profit)} \xB7 MDD ${_rpPct(g.mdd)}`
      },
      /* @__PURE__ */ React.createElement("span", null, "gen_", String(g.gen_no).padStart(2, "0")),
      /* @__PURE__ */ React.createElement("span", { className: g.profit > 0 ? "rp-pos" : "rp-neg" }, _rpMoney(g.profit)),
      g.gate_passed && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)" } }, "\u2713")
    ))), /* @__PURE__ */ React.createElement("div", { className: "rp-history-detail" }, selGen == null ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uC138\uB300\uB97C \uC120\uD0DD\uD558\uC138\uC694.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "rp-history-actions" }, /* @__PURE__ */ React.createElement("span", { className: "rp-mini-label" }, selRun, " / gen_", String(selGen).padStart(2, "0"), " \u2014 \uC870\uAC74\uC2DD & \uC0C1\uC138 \uACB0\uACFC"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        style: { marginLeft: "auto" },
        onClick: () => _rpOpenWorkbench(selRun, selGen, onOpenWorkbench),
        "data-tip": "\uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0 \uC801\uC7AC"
      },
      "\uBC14\uB85C \uBC31\uD14C\uC2A4\uD2B8"
    )), /* @__PURE__ */ React.createElement(_RpStrategyCode, { baseUrl, isDemo, runId: selRun, genNo: selGen }), /* @__PURE__ */ React.createElement("div", { className: "rp-history-charts" }, hasBt ? /* @__PURE__ */ React.createElement(
      window.BtResultArea,
      {
        baseUrl,
        isDemo,
        jobId: null,
        evoSource: { run_id: selRun, gen_no: selGen }
      }
    ) : /* @__PURE__ */ React.createElement("div", { className: "rp-empty" }, "\uC0C1\uC138 \uCC28\uD2B8 \uCEF4\uD3EC\uB10C\uD2B8(BtResultArea)\uB97C \uBD88\uB7EC\uC62C \uC218 \uC5C6\uC2B5\uB2C8\uB2E4.")))))));
  }
  function _rpActiveStage(liveState, ops) {
    const phase = liveState && (liveState.phase || liveState.latest && liveState.latest.phase) || "";
    const status = liveState && liveState.status || "";
    const p = String(phase).toLowerCase();
    if (status === "running") {
      if (p.indexOf("generate") >= 0 || p.indexOf("loop_start") >= 0 || p.indexOf("warm") >= 0 || p.indexOf("ga_init") >= 0)
        return 1;
      if (p.indexOf("backtest") >= 0 || p.indexOf("evaluate") >= 0) return 3;
      if (p.indexOf("score") >= 0) return 4;
      if (p.indexOf("autopsy") >= 0 || p.indexOf("generation_done") >= 0) return 1;
    }
    const active = (ops && Array.isArray(ops.active) ? ops.active : []).length;
    if (active > 0 && status !== "complete") return 3;
    return -1;
  }
  function _RpProcessFlowOverlay({ onClose, liveState, ops }) {
    const activeStage = _rpActiveStage(liveState, ops);
    const PIPELINE = window.STOM_PIPELINE || [];
    useEffect_rp(() => {
      const onKey = (e) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);
    return /* @__PURE__ */ React.createElement("div", { className: "rp-overlay", onClick: onClose }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-card", onClick: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\uC9C4\uD654 \uD504\uB85C\uC138\uC2A4 \u2014 \uC804\uCCB4 \uD750\uB984"), activeStage >= 0 && /* @__PURE__ */ React.createElement("span", { className: "rp-card-sub" }, "\uD604\uC7AC \uB2E8\uACC4: ", PIPELINE[activeStage].title), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", style: { marginLeft: "auto" }, onClick: onClose }, "\u2715 \uB2EB\uAE30 (Esc)")), /* @__PURE__ */ React.createElement("div", { className: "rp-flow" }, PIPELINE.map((s, i) => {
      const isActive = i === activeStage;
      return /* @__PURE__ */ React.createElement(React.Fragment, { key: s.key }, /* @__PURE__ */ React.createElement("div", { className: "rp-flow-node" + (isActive ? " rp-flow-active" : "") }, /* @__PURE__ */ React.createElement("div", { className: "rp-flow-ico" }, s.icon), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-name" }, i + 1, ". ", s.title, isActive && /* @__PURE__ */ React.createElement("span", { className: "rp-flow-pulse" }, " \u25CF \uC9C4\uD589")), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-desc" }, s.desc), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-terms" }, s.terms.map(([t, d]) => /* @__PURE__ */ React.createElement("div", { key: t, className: "rp-flow-term" }, /* @__PURE__ */ React.createElement("b", null, t), " ", d)))), i < PIPELINE.length - 1 && /* @__PURE__ */ React.createElement("div", { className: "rp-flow-arrow" }, "\u2192"));
    }))));
  }
  Object.assign(window, { ResearchProcessFlowOverlay: _RpProcessFlowOverlay });
  function ResearchProPanel({ baseUrl, wsStatus, runId }) {
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const [runList, setRunList] = useState_rp([]);
    const [selRun, setSelRun] = useState_rp(runId || "");
    const [selGen, setSelGen] = useState_rp(0);
    const [ops, setOps] = useState_rp(null);
    const [liveState, setLiveState] = useState_rp(null);
    const [showFlow, setShowFlow] = useState_rp(false);
    const [refreshKey, setRefreshKey] = useState_rp(0);
    useEffect_rp(() => {
      if (runId && !selRun) setSelRun(runId);
    }, [runId]);
    useEffect_rp(() => {
      if (isDemo || !baseUrl) {
        setRunList([]);
        return void 0;
      }
      let cancelled = false;
      _rpFetchJson(baseUrl + "/runs", 6e3).then((j) => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
        if (!selRun && runs.length) setSelRun(runs[0].run_id);
      }).catch(() => {
        if (!cancelled) setRunList([]);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, refreshKey]);
    useEffect_rp(() => {
      if (isDemo || !baseUrl) return void 0;
      const pull = () => {
        _rpFetchJson(baseUrl + "/ops_status", 8e3).then((j) => setOps(j)).catch(() => {
        });
        _rpFetchJson(baseUrl + "/status", 8e3).then((j) => setLiveState(j)).catch(() => {
        });
      };
      pull();
      const timer = setInterval(pull, 1e4);
      return () => clearInterval(timer);
    }, [baseUrl, isDemo, refreshKey]);
    const onRefresh = useCallback_rp(() => setRefreshKey((k) => k + 1), []);
    const onOpenWorkbench = useCallback_rp(() => {
      try {
        localStorage.setItem("stom_active_tab", "backtest");
        window.location.href = "/ui/";
      } catch (e) {
      }
    }, []);
    const activeRunLabel = useMemo_rp(() => {
      const r = (runList || []).find((x) => x.run_id === selRun);
      return r && r.label ? r.label : "";
    }, [runList, selRun]);
    return /* @__PURE__ */ React.createElement("div", { className: "research-pro" }, /* @__PURE__ */ React.createElement("div", { className: "rp-topbar" }, /* @__PURE__ */ React.createElement("div", { className: "rp-topbar-title" }, /* @__PURE__ */ React.createElement("span", { className: "rp-topbar-mark" }, "\u{1F52C}"), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "rp-topbar-h" }, "\uB9AC\uC11C\uCE58 \uD504\uB85C \u2014 \uC804\uCCB4\uD654\uBA74 \uBD84\uC11D \uC6CC\uD06C\uC2A4\uD398\uC774\uC2A4"), /* @__PURE__ */ React.createElement("div", { className: "rp-topbar-sub mono" }, selRun ? selRun : "run \uBBF8\uC120\uD0DD", activeRunLabel ? " \xB7 " + activeRunLabel : ""))), /* @__PURE__ */ React.createElement("div", { className: "rp-topbar-controls" }, /* @__PURE__ */ React.createElement("label", { className: "rp-ctl mono" }, /* @__PURE__ */ React.createElement("span", null, "run"), /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "mono rp-select",
        value: selRun,
        onChange: (e) => setSelRun(e.target.value),
        disabled: isDemo
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "\uC120\uD0DD\u2026"),
      (runList || []).map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : "", r.gate_passed_count > 0 ? " \u2713" : ""))
    )), /* @__PURE__ */ React.createElement("label", { className: "rp-ctl mono" }, /* @__PURE__ */ React.createElement("span", null, "gen"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        min: 0,
        value: selGen,
        onChange: (e) => setSelGen(Number(e.target.value) || 0),
        className: "rp-num-input mono"
      }
    )), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onRefresh, disabled: isDemo }, "\u21BB \uC0C8\uB85C\uACE0\uCE68"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setShowFlow(true), "data-tip": "\uC9C4\uD654 \uC804\uCCB4 \uD504\uB85C\uC138\uC2A4 \uBCF4\uAE30" }, "\u{1F9ED} \uD504\uB85C\uC138\uC2A4"))), isDemo ? /* @__PURE__ */ React.createElement("div", { className: "rp-empty", style: { margin: 24 } }, "\uB370\uBAA8(\uBBF8\uC5F0\uACB0) \uBAA8\uB4DC \u2014 \uC2E4 run\uC5D0 \uC5F0\uACB0\uD558\uBA74 \uB9AC\uC11C\uCE58 \uD504\uB85C \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", { className: "rp-grid" }, /* @__PURE__ */ React.createElement(_RpBigHeatmap, { baseUrl, isDemo, runId: selRun, key: "hm" + refreshKey }), /* @__PURE__ */ React.createElement(_RpHallOfFame, { baseUrl, isDemo, onOpenWorkbench, key: "hof" + refreshKey }), /* @__PURE__ */ React.createElement(
      _RpRunCompare,
      {
        baseUrl,
        isDemo,
        runList,
        currentRunId: selRun,
        currentGenNo: selGen,
        onOpenWorkbench
      }
    ), /* @__PURE__ */ React.createElement(_RpHistory, { baseUrl, isDemo, runList, onOpenWorkbench })), showFlow && /* @__PURE__ */ React.createElement(_RpProcessFlowOverlay, { onClose: () => setShowFlow(false), liveState, ops }));
  }
  function ResearchHeatmapPanel({ baseUrl, wsStatus, runId }) {
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uD0D0\uC0C9 \uD788\uD2B8\uB9F5 \u2014 \uC2DC\uAC04\uB300 \xD7 \uC2DC\uAC00\uCD1D\uC561", /* @__PURE__ */ React.createElement(
      "span",
      {
        "data-tip": "\uC9C4\uD654 \uB8E8\uD504\uAC00 \uC5B4\uB290 \uC2DC\uAC04\uB300\xB7\uC5B4\uB290 \uC2DC\uAC00\uCD1D\uC561 \uAD6C\uAC04\uC5D0\uC11C \uC5E3\uC9C0(edge_ratio)\uB97C \uCC3E\uACE0 \uC788\uB294\uC9C0 \uBCF4\uC5EC\uC90D\uB2C8\uB2E4. 1.0 \uCD08\uACFC(\uB179\uC0C9) = \uD574\uB2F9 \uAD6C\uAC04\uC5D0\uC11C \uC2DC\uB4DC \uB300\uBE44 \uC6B0\uC704, 1.0 \uBBF8\uB9CC(\uC801\uC0C9) = \uC5F4\uC704. \uC140\uC5D0 \uB9C8\uC6B0\uC2A4\uB97C \uC62C\uB9AC\uBA74 \uC0C1\uC138 \uC218\uCE58\uAC00 \uB098\uC635\uB2C8\uB2E4.",
        style: {
          marginLeft: 6,
          fontSize: 10,
          color: "var(--ink-3)",
          border: "1px solid var(--line-2)",
          borderRadius: "50%",
          width: 15,
          height: 15,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "help"
        }
      },
      "?"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo || !runId ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12, color: "var(--ink-3)", padding: "18px 0", textAlign: "center" } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4." : "run \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(_RpBigHeatmap, { baseUrl, isDemo, runId })));
  }
  Object.assign(window, { ResearchProPanel, ResearchHeatmapPanel });

  // ../frontend/research-wiki.jsx
  var { useState: useState_rw, useEffect: useEffect_rw, useMemo: useMemo_rw } = React;
  var RESEARCH_WIKI_CATEGORIES = [
    { key: "wiki", label: "Methods" },
    { key: "good_results", label: "Good Results" },
    { key: "condition_research", label: "Metrics" },
    { key: "update_log", label: "Failed Candidates" },
    { key: "next", label: "Next Experiments" }
  ];
  function wikiLabel(category) {
    const found = RESEARCH_WIKI_CATEGORIES.find((c) => c.key === category);
    return found ? found.label : category || "Docs";
  }
  function ResearchWikiPanel({ baseUrl, wsStatus }) {
    const [docs, setDocs] = useState_rw([]);
    const [selectedId, setSelectedId] = useState_rw("");
    const [doc, setDoc] = useState_rw(null);
    const [loading, setLoading] = useState_rw(false);
    const [err, setErr] = useState_rw("");
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const grouped = useMemo_rw(() => {
      const out = {};
      for (const row of docs) {
        const key = row.category || "Docs";
        if (!out[key]) out[key] = [];
        out[key].push(row);
      }
      return out;
    }, [docs]);
    const loadDocs = React.useCallback(() => {
      if (isDemo || !baseUrl) return;
      setLoading(true);
      setErr("");
      fetch(baseUrl + "/research_docs", { signal: AbortSignal.timeout(3500) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        const rows = Array.isArray(j.docs) ? j.docs : [];
        setDocs(rows);
        if (!selectedId && rows.length) {
          const preferred = rows.find((r) => r.category === "wiki") || rows[0];
          setSelectedId(preferred.id);
        }
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, selectedId]);
    useEffect_rw(() => {
      loadDocs();
    }, [loadDocs]);
    useEffect_rw(() => {
      if (isDemo || !baseUrl || !selectedId) {
        setDoc(null);
        return;
      }
      setLoading(true);
      setErr("");
      fetch(
        baseUrl + "/research_doc?id=" + encodeURIComponent(selectedId),
        { signal: AbortSignal.timeout(3500) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => setDoc(j || null)).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, selectedId]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel research-wiki" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "Research Wiki", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: loadDocs, disabled: isDemo || loading }, loading ? "loading" : "refresh")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-wiki-note" }, "Good Results screenshots are reference only, not live proof. Markdown is displayed as plain text."), isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-wiki-empty" }, "Backend connection required for wiki documents.") : err ? /* @__PURE__ */ React.createElement("div", { className: "research-wiki-empty danger" }, "wiki query failed: ", err) : /* @__PURE__ */ React.createElement("div", { className: "research-wiki-layout" }, /* @__PURE__ */ React.createElement("div", { className: "research-wiki-list" }, RESEARCH_WIKI_CATEGORIES.map((cat) => /* @__PURE__ */ React.createElement("div", { key: cat.key, className: "research-wiki-category" }, /* @__PURE__ */ React.createElement("div", { className: "research-wiki-category-title" }, cat.label), (grouped[cat.key] || []).slice(0, 12).map((row) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: row.id,
        className: selectedId === row.id ? "active" : "",
        onClick: () => setSelectedId(row.id),
        title: row.id
      },
      /* @__PURE__ */ React.createElement("span", null, row.title || row.id),
      /* @__PURE__ */ React.createElement("small", null, row.size || 0, " bytes")
    )), !(grouped[cat.key] || []).length && /* @__PURE__ */ React.createElement("small", { className: "research-wiki-muted" }, "no docs")))), /* @__PURE__ */ React.createElement("div", { className: "research-wiki-doc" }, doc && doc.available ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "research-wiki-doc-head" }, /* @__PURE__ */ React.createElement("strong", null, doc.title || selectedId), /* @__PURE__ */ React.createElement("span", null, wikiLabel(doc.category), " / ", doc.id)), /* @__PURE__ */ React.createElement("pre", { className: "research-wiki-markdown" }, doc.markdown || "")) : /* @__PURE__ */ React.createElement("div", { className: "research-wiki-empty" }, selectedId ? "Document unavailable or not allowed." : "Select a research document.")))));
  }
  Object.assign(window, { ResearchWikiPanel });

  // ../frontend/sim-live-chart.jsx
  var {
    useRef: useRef_slc,
    useEffect: useEffect_slc,
    useState: useState_slc
  } = React;
  var _SLC_UP = "#4cd6b3";
  var _SLC_DOWN = "#ff5d6c";
  var _SLC_INK3 = "#6b7480";
  var _SLC_GRID = "rgba(255,255,255,0.05)";
  var _SLC_WINDOW = 120;
  var _SLC_MIN_SLOTS = 48;
  function _slcSlot(innerW, n) {
    return innerW / Math.max(n, _SLC_MIN_SLOTS);
  }
  var _SLC_LERP_MS = 150;
  var _SLC_FLASH_MS = 220;
  var _SLC_MIN_FRAME_MS = 28;
  var _slcTimeLabel = window._hmsTimeLabel;
  var _slcPriceTick = window._priceTick;
  function _lerp(from, to, t) {
    if (from == null || !isFinite(from)) return to;
    if (t >= 1) return to;
    return from + (to - from) * t;
  }
  function _animatedBars(bars, lastAnim) {
    const n = bars.length;
    if (n === 0) return bars;
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
    const animRef = useRef_slc({
      // 마지막 캔들 보간 진행: target(새 OHLC) / from(직전 표시값) / startTs.
      lastTarget: null,
      lastFrom: null,
      lastStart: 0,
      prevClose: null,
      flashKind: null,
      flashStart: 0,
      prevLastT: null,
      // 직전 마지막 bar 시각(새 bar 감지).
      scrollOffset: 0,
      // 오토스크롤 보간용 진행(0..1) — 새 bar 시 0→1.
      // Phase7 — 배치 도착 간 실제 경과(ms). lerp 를 min(_SLC_LERP_MS, batchWallMs)로 바운드해
      //   고속(240x/600x) 재생에서 보간이 배치가 대표하는 wall-time 을 넘지 않게 한다(1x=실시간 불변).
      prevArrival: 0,
      lerpMs: _SLC_LERP_MS,
      lastDrawTs: 0
      // 마지막 실제 재드로우 시각(프레임레이트 캡용).
    });
    const barsRef = useRef_slc(bars || []);
    const sigRef = useRef_slc(signals || []);
    const curTRef = useRef_slc(curT);
    const compactRef = useRef_slc(!!compact);
    const indRef = useRef_slc(indicators || null);
    const [hover, setHover] = useState_slc(null);
    const hoverRef = useRef_slc(null);
    const dirtyRef = useRef_slc(true);
    const markDirty = () => {
      dirtyRef.current = true;
    };
    const H = compact ? 220 : 340;
    useEffect_slc(() => {
      const arr2 = bars || [];
      const prev = barsRef.current;
      const a = animRef.current;
      const newLast = arr2.length ? arr2[arr2.length - 1] : null;
      const prevLast = prev.length ? prev[prev.length - 1] : null;
      if (newLast) {
        const sameBar = prevLast && prevLast.t === newLast.t;
        const from = sameBar && prevLast ? { o: prevLast.o, h: prevLast.h, l: prevLast.l, c: prevLast.c } : { o: newLast.o, h: newLast.o, l: newLast.o, c: newLast.o };
        a.lastFrom = from;
        a.lastTarget = { o: newLast.o, h: newLast.h, l: newLast.l, c: newLast.c };
        const nowTs = typeof performance !== "undefined" ? performance.now() : Date.now();
        const batchWallMs = a.prevArrival > 0 ? nowTs - a.prevArrival : _SLC_LERP_MS;
        a.lerpMs = Math.max(16, Math.min(_SLC_LERP_MS, batchWallMs));
        a.prevArrival = nowTs;
        a.lastStart = nowTs;
        if (a.prevClose != null && newLast.c !== a.prevClose) {
          a.flashKind = newLast.c >= a.prevClose ? "up" : "down";
          a.flashStart = a.lastStart;
        }
        a.prevClose = newLast.c;
        if (!sameBar) {
          a.scrollOffset = 0;
          a.prevLastT = newLast.t;
        }
      }
      barsRef.current = arr2;
      markDirty();
      const viewArr = arr2.length > _SLC_WINDOW ? arr2.slice(arr2.length - _SLC_WINDOW) : arr2;
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
    useEffect_slc(() => {
      sigRef.current = signals || [];
      markDirty();
    }, [signals]);
    useEffect_slc(() => {
      curTRef.current = curT;
      markDirty();
    }, [curT]);
    useEffect_slc(() => {
      compactRef.current = !!compact;
      markDirty();
    }, [compact]);
    useEffect_slc(() => {
      indRef.current = indicators || null;
      markDirty();
      const a = animRef.current;
      a.lastIndForCache = indicators || null;
      const arr2 = barsRef.current;
      const viewArr = arr2.length > _SLC_WINDOW ? arr2.slice(arr2.length - _SLC_WINDOW) : arr2;
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
    useEffect_slc(() => {
      const canvas = canvasRef.current;
      const wrap = wrapRef.current;
      if (!canvas || !wrap) return;
      const draw = () => {
        rafRef.current = requestAnimationFrame(draw);
        if (!wrap.offsetParent) return;
        const a = animRef.current;
        const now = typeof performance !== "undefined" ? performance.now() : Date.now();
        const animating = !!a.lastTarget && now - a.lastStart < (a.lerpMs || _SLC_LERP_MS) || !!a.flashKind && now - a.flashStart < _SLC_FLASH_MS;
        if (!dirtyRef.current && !animating) return;
        if (now - a.lastDrawTs < _SLC_MIN_FRAME_MS) return;
        a.lastDrawTs = now;
        _drawFrame(
          canvas,
          wrap,
          barsRef.current,
          sigRef.current,
          curTRef.current,
          compactRef.current,
          a,
          hoverRef.current,
          now,
          H,
          indRef.current
        );
        if (!animating) dirtyRef.current = false;
      };
      rafRef.current = requestAnimationFrame(draw);
      let ro = null;
      if (typeof ResizeObserver !== "undefined") {
        ro = new ResizeObserver(() => markDirty());
        try {
          ro.observe(wrap);
        } catch (e) {
        }
      }
      return () => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current);
        if (ro) {
          try {
            ro.disconnect();
          } catch (e) {
          }
        }
      };
    }, [H]);
    const onMove = (e) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const layout = _layout(rect.width, H, compactRef.current);
      const arr2 = barsRef.current;
      const view2 = arr2.length > _SLC_WINDOW ? arr2.slice(arr2.length - _SLC_WINDOW) : arr2;
      const n = view2.length;
      if (n === 0 || x < layout.padL || x > rect.width - layout.padR) {
        _setHover(null);
        return;
      }
      const slot = _slcSlot(rect.width - layout.padL - layout.padR, n);
      const i = Math.floor((x - layout.padL) / slot);
      if (i >= 0 && i < n) _setHover({ idx: i, base: arr2.length - n });
      else _setHover(null);
    };
    const _setHover = (h) => {
      hoverRef.current = h;
      setHover(h);
      markDirty();
    };
    const onLeave = () => _setHover(null);
    const lastBar = bars && bars.length ? bars[bars.length - 1] : null;
    const arr = bars || [];
    const view = arr.length > _SLC_WINDOW ? arr.slice(arr.length - _SLC_WINDOW) : arr;
    const hoverBar = hover && view[hover.idx] ? view[hover.idx] : null;
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: compact ? 11 : 12.5 } }, code, name ? " \xB7 " + name : ""), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9, color: "var(--ink-3)", marginLeft: 6 } }, "\uB77C\uC774\uBE0C")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, alignItems: "center" } }, lastBar && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: lastBar.change >= 0 ? "var(--teal)" : "var(--red)" } }, (lastBar.change || 0) >= 0 ? "+" : "", (lastBar.change || 0).toFixed(2), "%"), lastBar && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-1)" } }, _slcPriceTick(lastBar.c)))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { ref: wrapRef, className: "chart-wrap", style: { position: "relative", width: "100%", height: H } }, /* @__PURE__ */ React.createElement(
      "canvas",
      {
        ref: canvasRef,
        onMouseMove: onMove,
        onMouseLeave: onLeave,
        style: { width: "100%", height: H, display: "block", cursor: "crosshair" }
      }
    ), arr.length === 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)",
      pointerEvents: "none"
    } }, "\uC7AC\uC0DD\uC744 \uC2DC\uC791\uD558\uBA74 \uB77C\uC774\uBE0C \uCE94\uB4E4\uC774 \uC2E4\uC2DC\uAC04\uC73C\uB85C \uC790\uB77C\uB0A9\uB2C8\uB2E4"), hoverBar && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 10,
      right: 10,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "7px 9px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 138,
      pointerEvents: "none",
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 3 } }, _slcTimeLabel(hoverBar.t)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "1px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC2DC"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _slcPriceTick(hoverBar.o)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uACE0"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _slcPriceTick(hoverBar.h)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC800"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _slcPriceTick(hoverBar.l)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC885"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _slcPriceTick(hoverBar.c)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB7C9"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _slcPriceTick(hoverBar.vol)))))));
  }
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
  function _drawFrame(canvas, wrap, allBars, signals, curT, compact, anim, hover, now, H, indicators) {
    const ind = indicators || {};
    const cssW = wrap.clientWidth || 600;
    const cssH = H;
    const dpr = typeof window !== "undefined" && window.devicePixelRatio ? window.devicePixelRatio : 1;
    const needW = Math.round(cssW * dpr);
    const needH = Math.round(cssH * dpr);
    if (canvas.width !== needW || canvas.height !== needH) {
      canvas.width = needW;
      canvas.height = needH;
    }
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssW, cssH);
    const arr = allBars || [];
    if (arr.length === 0) return;
    let lastAnim = null;
    if (anim.lastTarget && anim.lastFrom) {
      const lerpMs = anim.lerpMs && isFinite(anim.lerpMs) ? anim.lerpMs : _SLC_LERP_MS;
      const t = Math.min(1, (now - anim.lastStart) / lerpMs);
      lastAnim = {
        o: _lerp(anim.lastFrom.o, anim.lastTarget.o, t),
        h: _lerp(anim.lastFrom.h, anim.lastTarget.h, t),
        l: _lerp(anim.lastFrom.l, anim.lastTarget.l, t),
        c: _lerp(anim.lastFrom.c, anim.lastTarget.c, t)
      };
    }
    const animated = _animatedBars(arr, lastAnim);
    const view = animated.length > _SLC_WINDOW ? animated.slice(animated.length - _SLC_WINDOW) : animated;
    const n = view.length;
    const hasStrength = ind.strength !== false;
    const hasImb = !!ind.imbalance && view.some((b) => b.imbalance != null && isFinite(b.imbalance) || b.buy_rest != null && b.sell_rest != null);
    const hasOf = !!ind.orderflow && view.some((b) => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0);
    const hasRsi = !!ind.rsi && typeof window !== "undefined" && typeof window._simRsi === "function";
    const hasMacd = !!ind.macd && typeof window !== "undefined" && typeof window._simMacd === "function";
    const strips = (hasStrength ? 1 : 0) + (hasImb ? 1 : 0) + (hasOf ? 1 : 0) + (hasRsi ? 1 : 0) + (hasMacd ? 1 : 0);
    const L = _layout(cssW, cssH, compact, strips);
    const innerW = cssW - L.padL - L.padR;
    const slot = _slcSlot(innerW, n);
    const candleW = Math.max(1, Math.min(13, slot * 0.64));
    const xCenter = (i) => L.padL + slot * (i + 0.5);
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
    const pRange = pMax - pMin || 1;
    const yPrice = (v) => priceBot - (v - pMin) / pRange * L.priceH;
    const volTop = priceBot + L.gap;
    const volBot = volTop + L.volH;
    let vMax = 1;
    for (let i = 0; i < n; i++) vMax = Math.max(vMax, view[i].vol || 0);
    const yVol = (v) => volBot - v / vMax * L.volH;
    ctx.font = "10px " + _slcFont();
    ctx.textBaseline = "middle";
    ctx.strokeStyle = _SLC_GRID;
    ctx.lineWidth = 1;
    ctx.fillStyle = _SLC_INK3;
    ctx.textAlign = "right";
    ctx.fillText(_slcPriceTick(pMax), L.padL - 6, priceTop + 4);
    ctx.fillText(_slcPriceTick(pMin), L.padL - 6, priceBot);
    ctx.beginPath();
    ctx.moveTo(L.padL, priceBot);
    ctx.lineTo(cssW - L.padR, priceBot);
    ctx.stroke();
    ctx.fillText("\uAC70\uB798\uB7C9", L.padL - 6, volTop + 6);
    for (let i = 0; i < n; i++) {
      const b = view[i];
      const up = (b.c || 0) >= (b.o || 0);
      const y = yVol(b.vol || 0);
      ctx.fillStyle = up ? "rgba(76,214,179,0.40)" : "rgba(255,93,108,0.40)";
      ctx.fillRect(xCenter(i) - candleW / 2, y, candleW, Math.max(0, volBot - y));
    }
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
      if (isLast) {
        ctx.save();
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;
      }
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, yHigh);
      ctx.lineTo(cx, yLow);
      ctx.stroke();
      ctx.fillStyle = color;
      ctx.fillRect(cx - candleW / 2, top, candleW, bodyH);
      if (isLast) ctx.restore();
    }
    if (ind.ma !== false) {
      _drawLine(ctx, view, xCenter, yPrice, "ma5", "#4cd6b3", 1, 0.5, n);
      _drawLine(ctx, view, xCenter, yPrice, "ma20", "#f0b35a", 1.1, 0.7, n);
      _drawLine(ctx, view, xCenter, yPrice, "ma60", "#7c6cf0", 1.1, 0.6, n);
    }
    if (ind.vwap !== false) _drawLine(ctx, view, xCenter, yPrice, "vwap", "#ffd24c", 1.4, 0.85, n);
    if (ind.vwapband) {
      _drawLine(ctx, view, xCenter, yPrice, "vwap_up", "#ffd24c", 0.9, 0.5, n);
      _drawLine(ctx, view, xCenter, yPrice, "vwap_low", "#ffd24c", 0.9, 0.5, n);
    }
    if (ind.ema) {
      _drawArrLine(ctx, anim.cachedEma12 || [], xCenter, yPrice, "#6fd6ff", 1, 0.7, n);
      _drawArrLine(ctx, anim.cachedEma26 || [], xCenter, yPrice, "#b07cf0", 1, 0.7, n);
    }
    if (ind.volma) {
      const vm = anim.cachedVolMa || {};
      _drawArrLine(ctx, vm.vol_ma5, xCenter, yVol, "#4cd6b3", 0.9, 0.7, n);
      _drawArrLine(ctx, vm.vol_ma20, xCenter, yVol, "#f0b35a", 0.9, 0.6, n);
    }
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
    if (hasRsi) {
      const rsiVals = anim.cachedRsi || [];
      _drawRsiPane(ctx, rsiVals, xCenter, L, stripRight, stripTop, n);
      stripTop += L.stripH + L.gap;
    }
    if (hasMacd) {
      const macdData = anim.cachedMacd || {};
      _drawMacdPane(ctx, macdData, xCenter, slot, L, stripRight, stripTop, n);
      stripTop += L.stripH + L.gap;
    }
    const last = view[n - 1];
    const yLast = yPrice(last.c || 0);
    let lineColor = (last.c || 0) >= (last.o || 0) ? _SLC_UP : _SLC_DOWN;
    let lineAlpha = 0.55;
    if (anim.flashKind) {
      const ft = (now - anim.flashStart) / _SLC_FLASH_MS;
      if (ft < 1) {
        lineColor = anim.flashKind === "up" ? _SLC_UP : _SLC_DOWN;
        lineAlpha = 0.55 + (1 - ft) * 0.45;
      } else {
        anim.flashKind = null;
      }
    }
    ctx.save();
    ctx.globalAlpha = lineAlpha;
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 3]);
    ctx.beginPath();
    ctx.moveTo(L.padL, yLast);
    ctx.lineTo(cssW - L.padR, yLast);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    ctx.fillStyle = lineColor;
    ctx.globalAlpha = 1;
    ctx.fillRect(cssW - L.padR, yLast - 8, L.padR, 16);
    ctx.fillStyle = "#0c1014";
    ctx.textAlign = "right";
    ctx.font = "9px " + _slcFont();
    ctx.fillText(_slcPriceTick(last.c), cssW - 1, yLast + 1);
    const sigs = signals || [];
    ctx.textAlign = "center";
    ctx.font = (compact ? 11 : 13) + "px " + _slcFont();
    for (let s = 0; s < sigs.length; s++) {
      const sig = sigs[s];
      if (curT == null || sig.buy_hms <= curT) {
        const bi = _nearestIdxInView(view, sig.buy_hms);
        if (bi >= 0) {
          ctx.fillStyle = _SLC_UP;
          ctx.fillText("\u25B2", xCenter(bi), yPrice(sig.buy_price || view[bi].c) + (compact ? 13 : 15));
        }
      }
      if (curT == null || sig.sell_hms <= curT) {
        const si = _nearestIdxInView(view, sig.sell_hms);
        if (si >= 0) {
          ctx.fillStyle = _SLC_DOWN;
          ctx.fillText("\u25BC", xCenter(si), yPrice(sig.sell_price || view[si].c) - (compact ? 6 : 8));
        }
      }
    }
    ctx.fillStyle = _SLC_INK3;
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "center";
    const tickIdx = n <= 1 ? [0] : [0, Math.floor(n / 2), n - 1];
    let lastLabelX = -Infinity;
    tickIdx.forEach((i) => {
      if (!view[i]) return;
      const lx = xCenter(i);
      if (lx - lastLabelX < 56) return;
      lastLabelX = lx;
      ctx.fillText(_slcTimeLabel(view[i].t), lx, cssH - L.padB + 12);
    });
    if (hover && view[hover.idx]) {
      const cx = xCenter(hover.idx);
      const cyv = view[hover.idx].c || 0;
      ctx.save();
      ctx.strokeStyle = "rgba(255,255,255,0.18)";
      ctx.lineWidth = 1;
      ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(cx, priceTop);
      ctx.lineTo(cx, priceBot);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(L.padL, yPrice(cyv));
      ctx.lineTo(cssW - L.padR, yPrice(cyv));
      ctx.stroke();
      ctx.restore();
    }
  }
  function _nearestIdxInView(view, hms) {
    let best = -1;
    for (let i = 0; i < view.length; i++) {
      if (view[i].t <= hms) best = i;
      else break;
    }
    return best;
  }
  function _drawLine(ctx, view, xCenter, yPrice, key, color, width, alpha, n) {
    if (n < 2) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < n; i++) {
      const v = view[i][key];
      if (v == null || !isFinite(v)) {
        started = false;
        continue;
      }
      const x = xCenter(i), y = yPrice(v);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.restore();
  }
  function _drawArrLine(ctx, vals, xCenter, yFn, color, width, alpha, n) {
    if (!vals || n < 2) return;
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    let started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) {
        started = false;
        continue;
      }
      const x = xCenter(i), y = yFn(v);
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();
    ctx.restore();
  }
  function _drawStrengthStrip(ctx, view, xCenter, L, right, top, n, compact, ind, cachedStrMa) {
    const h = L.stripH;
    const bot = top + h;
    let sMax = 100;
    for (let i = 0; i < n; i++) sMax = Math.max(sMax, view[i].strength || 0);
    const yStr = (v) => bot - Math.min(v, sMax) / sMax * h;
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(L.padL, yStr(100));
    ctx.lineTo(right, yStr(100));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    const colorFn = typeof window !== "undefined" && typeof window._strengthColor === "function" ? window._strengthColor : null;
    ctx.save();
    ctx.lineWidth = 1.3;
    if (n > 1) {
      ctx.beginPath();
      let started = false;
      for (let i = 0; i < n; i++) {
        const s = view[i].strength;
        if (s == null || !isFinite(s)) {
          started = false;
          continue;
        }
        const x = xCenter(i), y = yStr(s);
        if (!started) {
          ctx.moveTo(x, y);
          started = true;
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.strokeStyle = colorFn ? colorFn(view[n - 1].strength, 0.95) : "#7c6cf0";
      ctx.stroke();
    }
    ctx.restore();
    if (ind && ind.strma && cachedStrMa) {
      _drawArrLine(ctx, cachedStrMa, xCenter, yStr, "#f0b35a", 1, 0.7, n);
    }
    ctx.save();
    ctx.fillStyle = "#7c6cf0";
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText("\uCCB4\uACB0\uAC15\uB3C4", L.padL - 6, top + 6);
    ctx.restore();
  }
  function _drawImbalanceStrip(ctx, view, xCenter, L, right, top, n) {
    const h = L.stripH;
    const bot = top + h;
    const valOf = (b) => {
      if (b.imbalance != null && isFinite(b.imbalance)) return b.imbalance;
      const br = b.buy_rest != null && isFinite(b.buy_rest) ? b.buy_rest : null;
      const sr = b.sell_rest != null && isFinite(b.sell_rest) ? b.sell_rest : null;
      return br != null && sr != null && sr > 0 ? br / sr : null;
    };
    let vMax = 2;
    for (let i = 0; i < n; i++) {
      const v = valOf(view[i]);
      if (v != null && isFinite(v)) vMax = Math.max(vMax, v);
    }
    const yImb = (v) => bot - Math.min(v, vMax) / vMax * h;
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.14)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);
    ctx.beginPath();
    ctx.moveTo(L.padL, yImb(1));
    ctx.lineTo(right, yImb(1));
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.restore();
    _drawArrLine(ctx, view.map(valOf), xCenter, yImb, "#4cd6b3", 1.2, 0.85, n);
    ctx.save();
    ctx.fillStyle = _SLC_INK3;
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText("\uD638\uAC00\uBD88\uADE0\uD615", L.padL - 6, top + 6);
    ctx.restore();
  }
  function _drawNetDeltaStrip(ctx, view, xCenter, slot, L, right, top, n) {
    const h = L.stripH;
    const mid = top + h / 2;
    const half = h / 2 - 2;
    let maxAbs = 1;
    const _nq = (b) => b && b.net_qty != null && isFinite(b.net_qty) ? b.net_qty : 0;
    for (let i = 0; i < n; i++) maxAbs = Math.max(maxAbs, Math.abs(_nq(view[i])));
    const barW = Math.max(1, slot * 0.7);
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(L.padL, mid);
    ctx.lineTo(right, mid);
    ctx.stroke();
    ctx.restore();
    for (let i = 0; i < n; i++) {
      const nq = _nq(view[i]);
      const bh = Math.min(Math.abs(nq), maxAbs) / maxAbs * half;
      const x = xCenter(i) - barW / 2;
      const y = nq >= 0 ? mid - bh : mid;
      ctx.fillStyle = nq > 0 ? "rgba(76,214,179,0.7)" : nq < 0 ? "rgba(255,93,108,0.7)" : "rgba(107,116,128,0.5)";
      ctx.fillRect(x, y, barW, Math.max(0.5, bh));
    }
    ctx.save();
    ctx.fillStyle = _SLC_UP;
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText("net-delta", L.padL - 6, top + 6);
    ctx.restore();
  }
  function _drawRsiPane(ctx, rsiVals, xCenter, L, right, top, n) {
    const h = L.stripH;
    const bot = top + h;
    const yRsi = (v) => bot - Math.max(0, Math.min(100, v)) / 100 * h;
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.10)";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 3]);
    [30, 50, 70].forEach((lv) => {
      ctx.beginPath();
      ctx.moveTo(L.padL, yRsi(lv));
      ctx.lineTo(right, yRsi(lv));
      ctx.stroke();
    });
    ctx.setLineDash([]);
    ctx.restore();
    _drawArrLine(ctx, rsiVals, xCenter, yRsi, "#4cd6b3", 1.2, 0.85, n);
    ctx.save();
    ctx.fillStyle = "#4cd6b3";
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText("RSI(14)", L.padL - 6, top + 6);
    ctx.restore();
  }
  function _drawMacdPane(ctx, macdData, xCenter, slot, L, right, top, n) {
    const h = L.stripH;
    const mid = top + h / 2;
    const half = h / 2 - 1;
    const macd = macdData.macd || [];
    const signal = macdData.signal || [];
    const hist = macdData.hist || [];
    let maxAbs = 1;
    for (let i = 0; i < n; i++) {
      const v = hist[i];
      if (v != null && isFinite(v)) maxAbs = Math.max(maxAbs, Math.abs(v));
    }
    const yMacd = (v) => v == null || !isFinite(v) ? mid : mid - Math.max(-maxAbs, Math.min(maxAbs, v)) / maxAbs * half;
    ctx.save();
    ctx.strokeStyle = "rgba(255,255,255,0.12)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(L.padL, mid);
    ctx.lineTo(right, mid);
    ctx.stroke();
    ctx.restore();
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
    _drawArrLine(ctx, macd, xCenter, yMacd, "#4cd6b3", 1.1, 0.9, n);
    ctx.save();
    ctx.setLineDash([3, 2]);
    _drawArrLine(ctx, signal, xCenter, yMacd, "#f0b35a", 1, 0.8, n);
    ctx.setLineDash([]);
    ctx.restore();
    ctx.save();
    ctx.fillStyle = "#4cd6b3";
    ctx.font = "9px " + _slcFont();
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText("MACD", L.padL - 6, top + 6);
    ctx.restore();
  }
  function _slcFont() {
    return "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
  }
  Object.assign(window, { SimLiveChart, _slcTimeLabel, _slcPriceTick });

  // ../frontend/panels.jsx
  var { useState: useState_p, useEffect: useEffect_p, useMemo: useMemo_p } = React;
  function ConnBadge({ health, wsStatus }) {
    var _a;
    let cls = "badge idle", label = "\uD655\uC778\uC911";
    if (wsStatus === "open" && health.connected) {
      cls = "badge ok";
      label = `\uBC31\uC5D4\uB4DC \uC5F0\uACB0\uB428 \xB7 v${(_a = health.contract_version) != null ? _a : "?"}`;
    } else if (wsStatus === "demo") {
      cls = "badge warn";
      label = "\uB370\uBAA8 \uBAA8\uB4DC (\uBC31\uC5D4\uB4DC \uBBF8\uC811\uC18D)";
    } else if (wsStatus === "reconnecting") {
      cls = "badge warn";
      label = "\uC5F0\uACB0 \uB04A\uAE40 \xB7 \uC7AC\uC5F0\uACB0 \uC911";
    } else if (wsStatus === "connecting") {
      cls = "badge idle";
      label = "\uC5F0\uACB0 \uC2DC\uB3C4\uC911";
    }
    return /* @__PURE__ */ React.createElement("span", { className: cls }, /* @__PURE__ */ React.createElement("span", { className: `dot ${wsStatus === "reconnecting" ? "pulse-dot" : ""}` }), label);
  }
  function StatusBadge({ status }) {
    const map = {
      idle: { cls: "badge idle", txt: "\uB300\uAE30" },
      running: { cls: "badge run", txt: "\uC2E4\uD589\uC911" },
      stopping: { cls: "badge warn", txt: "\uC815\uC9C0\uC911" },
      complete: { cls: "badge done", txt: "\uC644\uB8CC" },
      error: { cls: "badge err", txt: "\uC624\uB958" }
    };
    const m = map[status] || map.idle;
    return /* @__PURE__ */ React.createElement("span", { className: m.cls }, /* @__PURE__ */ React.createElement("span", { className: `dot ${status === "running" || status === "stopping" ? "pulse-dot" : ""}` }), m.txt);
  }
  function CurrentGenPanel({ state }) {
    var _a, _b, _c;
    const running = state.status === "running" || state.status === "stopping";
    const inProgress = state.generations.length < state.current_gen + (running ? 1 : 0);
    const activeGen = running ? state.current_gen + 1 : state.current_gen;
    const phase = ((_a = state.latest) == null ? void 0 : _a.phase) || "\u2014";
    const checkpoint = ((_b = state.latest) == null ? void 0 : _b.last_checkpoint) || "\u2014";
    const message = ((_c = state.latest) == null ? void 0 : _c.message) || "";
    const phaseColor = {
      // 데모 시뮬레이터(한국어) phase.
      "\uC0DD\uC131\uC911": "var(--blue)",
      "\uBC31\uD14C\uC2A4\uD2B8\uC911": "var(--amber)",
      "\uCC44\uC810\uC911": "var(--violet)",
      "\uC644\uB8CC": "var(--teal)",
      "\uB300\uAE30\uC911": "var(--ink-2)",
      "\uC815\uC9C0\uB428": "var(--ink-1)",
      "\uC2B9\uC778 \uC644\uB8CC": "var(--teal)",
      // R8 — LIVE(backend 영어) phase도 색을 매핑(이전엔 기본색으로만 표시됐다).
      "loop_start": "var(--blue)",
      "warm_prepare_start": "var(--blue)",
      "warm_prepare_done": "var(--blue)",
      "ga_init": "var(--blue)",
      "backtest_start": "var(--amber)",
      "ga_evaluate_start": "var(--amber)",
      "backtest_end": "var(--violet)",
      "generation_done": "var(--teal)",
      "ga_generation_done": "var(--teal)",
      "complete": "var(--teal)",
      "stopping": "var(--ink-1)"
    }[phase] || "var(--ink-1)";
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: running ? "var(--amber)" : "var(--ink-3)" } }), "\uD604\uC7AC \uC138\uB300 \u2014 Live"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, fmtTime(state.updated_at))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "flex-end", gap: 22 } }, /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "\uC138\uB300"), /* @__PURE__ */ React.createElement("span", { className: "stat-value lg mono" }, "gen_", String(activeGen).padStart(2, "0"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", fontSize: 16 } }, " / ", state.max_generations))), /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "\uD398\uC774\uC988"), /* @__PURE__ */ React.createElement("span", { className: "stat-value mono", style: { color: phaseColor, fontSize: 20 } }, phase)), /* @__PURE__ */ React.createElement("div", { className: "stat", style: { marginLeft: "auto", textAlign: "right" } }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "\uCCB4\uD06C\uD3EC\uC778\uD2B8"), /* @__PURE__ */ React.createElement("span", { className: "stat-sub", style: { color: "var(--ink-1)" } }, checkpoint))), running && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement("div", { className: "scanbar" })), /* @__PURE__ */ React.createElement("div", { style: {
      marginTop: 14,
      padding: "10px 12px",
      background: "var(--bg-0)",
      border: "1px solid var(--line-1)",
      borderRadius: 6,
      fontFamily: "var(--mono)",
      fontSize: 12,
      color: "var(--ink-1)",
      minHeight: 38,
      display: "flex",
      alignItems: "center",
      gap: 8
    } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "\u203A"), /* @__PURE__ */ React.createElement("span", null, message || (state.status === "idle" ? "\uC9C4\uD654 \uC2DC\uC791 \uBC84\uD2BC\uC73C\uB85C \uB8E8\uD504\uB97C \uAC1C\uC2DC\uD558\uC138\uC694" : "\u2014")))));
  }
  function _activeStrategyGenNo(item) {
    var _a;
    if (!item) return null;
    const raw = (_a = item.gen_no) != null ? _a : item.gen;
    return typeof raw === "number" ? raw : null;
  }
  function _activeStrategyFromState(state) {
    var _a;
    const gens = Array.isArray(state.generations) ? state.generations : [];
    if (state.status === "complete" && _activeStrategyGenNo(state.winner) !== null) {
      return { source: "winner", generation: { ...state.winner, gen_no: _activeStrategyGenNo(state.winner) } };
    }
    if (_activeStrategyGenNo(state.best) !== null) {
      return { source: "best", generation: { ...state.best, gen_no: _activeStrategyGenNo(state.best) } };
    }
    if (gens.length > 0) {
      const latest = gens.slice().sort((a, b) => {
        var _a2, _b;
        return ((_a2 = _activeStrategyGenNo(b)) != null ? _a2 : -1) - ((_b = _activeStrategyGenNo(a)) != null ? _b : -1);
      })[0];
      return { source: "latest_generation", generation: { ...latest, gen_no: _activeStrategyGenNo(latest) } };
    }
    const streaming = ((_a = state.current_run) == null ? void 0 : _a.generation) || {};
    if (streaming.buy_code_partial || streaming.sell_code_partial) {
      return {
        source: "streaming_partial",
        generation: {
          gen_no: typeof state.current_gen === "number" ? state.current_gen : 0,
          buy_name: streaming.buy_name || "",
          sell_name: streaming.sell_name || "",
          buy_code: streaming.buy_code_partial || "",
          sell_code: streaming.sell_code_partial || ""
        }
      };
    }
    return { source: "no_strategy", generation: null };
  }
  function ActiveStrategyPanel({ state, baseUrl, onViewCode }) {
    const [expanded, setExpanded] = useState_p(false);
    const [codePayload, setCodePayload] = useState_p(null);
    const [diffPayload, setDiffPayload] = useState_p(null);
    const [fetchError, setFetchError] = useState_p("");
    const active = useMemo_p(() => _activeStrategyFromState(state || {}), [state]);
    const generation = active.generation || {};
    const genNo = _activeStrategyGenNo(generation);
    const runId = state.run_id || "";
    const canFetch = Boolean(baseUrl && runId && genNo !== null && active.source !== "streaming_partial" && active.source !== "no_strategy");
    useEffect_p(() => {
      setCodePayload(null);
      setDiffPayload(null);
      setFetchError("");
      if (!canFetch) return;
      let cancelled = false;
      const codeUrl = `${baseUrl}/strategy_code?run=${encodeURIComponent(runId)}&gen=${genNo}`;
      const diffUrl = `${baseUrl}/strategy_diff?run_id=${encodeURIComponent(runId)}&gen_no=${genNo}&base_gen=previous`;
      fetch(codeUrl, { signal: AbortSignal.timeout(2500) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("strategy_code HTTP " + r.status))).then((j) => {
        if (!cancelled) setCodePayload(j);
      }).catch((e) => {
        if (!cancelled) setFetchError(String(e));
      });
      fetch(diffUrl, { signal: AbortSignal.timeout(2500) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("strategy_diff HTTP " + r.status))).then((j) => {
        if (!cancelled) setDiffPayload(j);
      }).catch((e) => {
        if (!cancelled) setFetchError(String(e));
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, runId, genNo, canFetch]);
    const buyName = (codePayload == null ? void 0 : codePayload.buy_name) || generation.buy_name || "";
    const sellName = (codePayload == null ? void 0 : codePayload.sell_name) || generation.sell_name || "";
    const buyCode = (codePayload == null ? void 0 : codePayload.buy_code) || generation.buy_code || "";
    const sellCode = (codePayload == null ? void 0 : codePayload.sell_code) || generation.sell_code || "";
    const codeStatus = active.source === "streaming_partial" ? "streaming_partial" : (codePayload == null ? void 0 : codePayload.code_status) || (active.source === "no_strategy" ? "no_strategy" : "loading");
    const diffStatus = (diffPayload == null ? void 0 : diffPayload.diff_status) || (canFetch ? "loading" : "unavailable");
    const previewCode = [buyCode, sellCode].filter(Boolean).join("\n\n# sell\n");
    const previewLines = (previewCode || "").split("\n");
    const boundedPreview = previewLines.slice(0, expanded ? 80 : 10).join("\n");
    return /* @__PURE__ */ React.createElement("div", { className: "panel active-strategy-panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Active Strategy"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "source=", active.source)), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "buy_name"), /* @__PURE__ */ React.createElement("span", { className: "stat-sub mono" }, buyName || "empty")), /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "sell_name"), /* @__PURE__ */ React.createElement("span", { className: "stat-sub mono" }, sellName || "empty"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "run_id=", runId || "none"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "gen_no=", genNo != null ? genNo : "none"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--teal)" } }, "code_status=", codeStatus), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--amber)" } }, "diff_status=", diffStatus)), fetchError && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, "active strategy fetch error: ", fetchError), /* @__PURE__ */ React.createElement("pre", { className: "code-block", style: { maxHeight: 170, overflow: "auto", margin: 0 } }, boundedPreview || `unavailable: ${codeStatus}`), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setExpanded(!expanded) }, expanded ? "collapse" : "expand", " preview"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        disabled: genNo === null || !onViewCode,
        onClick: () => onViewCode && onViewCode(genNo)
      },
      "open full code"
    ), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", alignSelf: "center" } }, "Previous Diff via /strategy_diff"))));
  }
  function ResearchCriteriaBanner({ state, baseUrl }) {
    var _a;
    const mode = ((_a = state.active_config) == null ? void 0 : _a.research_oos_mode) || "disabled";
    const [payload, setPayload] = useState_p(null);
    const [error, setError] = useState_p("");
    useEffect_p(() => {
      if (!baseUrl) return;
      let cancelled = false;
      const url = `${baseUrl}/research_criteria?mode=${encodeURIComponent(mode)}`;
      fetch(url, { signal: AbortSignal.timeout(2500) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("research_criteria HTTP " + r.status))).then((j) => {
        if (!cancelled) {
          setPayload(j);
          setError("");
        }
      }).catch((e) => {
        if (!cancelled) setError(String(e));
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, mode]);
    const label = (payload == null ? void 0 : payload.label) || (mode === "disabled" ? "OOS disabled" : `OOS ${mode}`);
    const warning = (payload == null ? void 0 : payload.warning) || "research/exploration only; not proof of human-level or production readiness.";
    const explanation = (payload == null ? void 0 : payload.explanation_ko) || "OOS\uB97C \uD6C4\uBCF4 \uD0C8\uB77D\uC5D0 \uC4F0\uC9C0 \uC54A\uB294 \uC5F0\uAD6C \uD0D0\uC0C9 \uC0C1\uD0DC\uC785\uB2C8\uB2E4.";
    return /* @__PURE__ */ React.createElement("div", { className: "panel", "data-testid": "research-criteria-banner" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Research Criteria"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--amber)" } }, "research_oos_mode=", mode)), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "badge warn" }, label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, warning)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 } }, explanation), error && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, "research criteria route unavailable: ", error)));
  }
  function _fmtCfgVal(v) {
    if (v === true) return "ON";
    if (v === false) return "OFF";
    if (v == null) return "\u2014";
    return String(v);
  }
  var _CFG_LABELS = {
    dispersion_prompt_enabled: "\uBD84\uC0B0\uB9E4\uB9E4 \uD504\uB86C\uD504\uD2B8",
    dispersion_enabled: "\uBD84\uC0B0 \uC801\uD569\uB3C4 \uBCF4\uC0C1",
    min_hold_symbols: "\uBD84\uC0B0 \uAE30\uC900(\uB3D9\uC2DC\uBCF4\uC720 \uD558\uD55C)",
    target_daily_trades: "\uBAA9\uD45C \uC77C\uD3C9\uADE0\uAC70\uB798",
    require_liquidity_gate: "\uAC70\uB798\uB300\uAE08 \uAC8C\uC774\uD2B8 \uAC15\uC81C",
    mdd_control_enabled: "MDD \uC81C\uC5B4 \uAC15\uD654(\uB9E4\uB3C4)",
    evolution_mode: "\uC9C4\uD654 \uBAA8\uB4DC",
    winner_objective: "\uC6B0\uC2B9 \uBAA9\uD45C",
    profit_weight: "\uC218\uC775 \uAC00\uC911\uCE58",
    bt_engine_mode: "\uC5D4\uC9C4 \uBAA8\uB4DC",
    bt_scope: "\uBC31\uD14C \uC2A4\uCF54\uD504",
    bt_timeframe: "\uD0C0\uC784\uD504\uB808\uC784",
    bt_refine_from_best: "best \uC810\uC9C4 \uAC1C\uC120",
    freeze_buy_on_mdd_only: "MDD-only \uB9E4\uC218 \uB3D9\uACB0",
    bt_full_start: "\uC804\uCCB4 \uC2DC\uC791\uC77C",
    bt_full_end: "\uC804\uCCB4 \uC885\uB8CC\uC77C",
    bt_betting: "\uC885\uBAA9\uB2F9 \uBC30\uD305",
    mdd_cap: "MDD \uC0C1\uD55C",
    min_trades: "\uCD5C\uC18C \uAC70\uB798\uC218",
    min_daily_trades: "\uC77C\uD3C9\uADE0\uAC70\uB798 \uD558\uD55C",
    overtrade_softcap: "\uACFC\uB9E4\uB9E4 softcap",
    tpi_gate_enabled: "TPI \uAC8C\uC774\uD2B8",
    tpi_gate: "TPI \uD558\uD55C",
    exit_quality_enabled: "\uCCAD\uC0B0\uD488\uC9C8 \uBCF4\uC0C1",
    target_score: "\uBAA9\uD45C \uC810\uC218",
    max_generations: "\uCD5C\uB300 \uC138\uB300"
  };
  function ActiveConfigPanel({ state }) {
    const cfg = state.active_config || {};
    const toggleNames = new Set(cfg.toggles || []);
    const entries = Object.keys(cfg).filter((k) => k !== "toggles").map((k) => [k, cfg[k]]);
    const onToggles = entries.filter(([k, v]) => toggleNames.has(k) && v === true);
    const others = entries.filter(([k, v]) => !(toggleNames.has(k) && v === true));
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uD65C\uC131 \uC124\uC815 \xB7 \uD1A0\uAE00"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, entries.length > 0 ? `${entries.length}\uAC1C \uC124\uC815 \xB7 \uCF1C\uC9C4 \uD1A0\uAE00 ${onToggles.length}` : "\uD604\uC7AC \uC801\uC6A9 \uC124\uC815")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: entries.length === 0 ? 14 : 0 } }, entries.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \u2014 \uB8E8\uD504 \uC2DC\uC791 \uC2DC \uC801\uC6A9\uB41C \uC124\uC815\xB7\uD1A0\uAE00 \uC2A4\uB0C5\uC0F7\uC774 \uBC1C\uD589\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", null, onToggles.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 6, padding: "10px 12px" } }, onToggles.map(([k]) => /* @__PURE__ */ React.createElement("span", { key: k, className: "mono", style: {
      fontSize: 10.5,
      color: "var(--teal)",
      background: "rgba(76,214,179,0.10)",
      border: "1px solid rgba(76,214,179,0.35)",
      borderRadius: 4,
      padding: "2px 7px"
    } }, _CFG_LABELS[k] || k, " \xB7 ON"))), /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, others.map(([k, v], i) => {
      const isToggle = toggleNames.has(k);
      return /* @__PURE__ */ React.createElement("li", { key: k, style: {
        display: "flex",
        justifyContent: "space-between",
        gap: 10,
        padding: "6px 12px",
        borderTop: i === 0 && onToggles.length > 0 ? "1px solid var(--line-1)" : "none",
        borderBottom: i < others.length - 1 ? "1px solid var(--bg-2)" : "none"
      } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, _CFG_LABELS[k] || k), /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
        fontSize: 11.5,
        color: isToggle ? v === true ? "var(--teal)" : "var(--ink-3)" : "var(--ink-0)"
      } }, _fmtCfgVal(v)));
    })))));
  }
  function CostPanel({ state, cap = 5e4 }) {
    var _a, _b, _c, _d;
    const tokens = (_b = (_a = state.cumulative) == null ? void 0 : _a.tokens) != null ? _b : 0;
    const cost = (_d = (_c = state.cumulative) == null ? void 0 : _c.cost_or_count) != null ? _d : 0;
    const pct = Math.min(100, tokens / cap * 100);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uBE44\uC6A9 \xB7 \uB204\uC801")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement("div", { className: "row-2", style: { gap: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "\uB204\uC801 \uD1A0\uD070"), /* @__PURE__ */ React.createElement("span", { className: "stat-value mono" }, fmtInt(tokens))), /* @__PURE__ */ React.createElement("div", { className: "stat" }, /* @__PURE__ */ React.createElement("span", { className: "stat-label" }, "\uBE44\uC6A9 / Count"), /* @__PURE__ */ React.createElement("span", { className: "stat-value mono" }, "$", cost.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })))), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginBottom: 6 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" } }, "\uD55C\uB3C4 \uC0AC\uC6A9\uB7C9"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: pct > 80 ? "var(--amber)" : "var(--ink-1)" } }, pct.toFixed(1), "% / ", fmtInt(cap))), /* @__PURE__ */ React.createElement("div", { className: "gauge" }, /* @__PURE__ */ React.createElement("div", { className: `gauge-fill ${pct > 80 ? "warn" : ""}`, style: { width: `${pct}%` } })))));
  }
  function FeedbackPanel({ state }) {
    const history = useMemo_p(() => {
      var _a;
      const items = [];
      if ((_a = state.latest) == null ? void 0 : _a.message) {
        items.push({ kind: "latest", text: state.latest.message, gen: state.current_gen });
      }
      const lastGens = [...state.generations].slice(-4).reverse();
      for (const g of lastGens) {
        if (g.gate_reason && g.gate_reason !== "\uC870\uAC74 \uCDA9\uC871") {
          items.push({ kind: "gen", text: `gen_${g.gen_no}: ${g.gate_reason}`, gen: g.gen_no });
        }
      }
      return items.slice(0, 5);
    }, [state.latest, state.generations, state.current_gen]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uD53C\uB4DC\uBC31 \xB7 \uBD80\uAC80"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uB2E4\uC74C \uC138\uB300\uC5D0 \uC804\uB2EC\uB418\uB294 \uCEE8\uD14D\uC2A4\uD2B8")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: 0 } }, history.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { padding: 18, color: "var(--ink-3)", fontSize: 12 } }, "\uC544\uC9C1 \uC804\uB2EC\uB41C \uBD80\uAC80\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, history.map((h, i) => /* @__PURE__ */ React.createElement("li", { key: i, style: {
      padding: "12px 14px",
      borderBottom: i < history.length - 1 ? "1px solid var(--line-1)" : "none",
      display: "flex",
      gap: 10,
      alignItems: "flex-start"
    } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
      fontSize: 10.5,
      color: h.kind === "latest" ? "var(--amber)" : "var(--ink-3)",
      flexShrink: 0,
      marginTop: 2,
      width: 56
    } }, h.kind === "latest" ? "\u2192 LIVE" : `gen_${String(h.gen).padStart(2, "0")}`), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 12, color: "var(--ink-0)", lineHeight: 1.55 } }, h.text))))));
  }
  function _pct(x) {
    return (typeof x === "number" ? (x * 100).toFixed(0) : "\u2014") + "%";
  }
  function _num(x) {
    return typeof x === "number" ? x.toFixed(2) : "\u2014";
  }
  function _ThresholdCond(t) {
    if (t.operator === "between") {
      const lo = t.lower_bound == null ? "-\u221E" : _num(t.lower_bound);
      const hi = t.upper_bound == null ? "\u221E" : _num(t.upper_bound);
      return `${t.stom_var} \u2208 [${lo}, ${hi}]`;
    }
    if (t.threshold != null) return `${t.stom_var} ${t.operator} ${_num(t.threshold)}`;
    return t.stom_var;
  }
  function _SegRows({ title, rows }) {
    if (!rows || rows.length === 0) return null;
    return /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 } }, title), /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, rows.map((s, i) => /* @__PURE__ */ React.createElement("li", { key: i, className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", padding: "3px 0", lineHeight: 1.5 } }, /* @__PURE__ */ React.createElement("span", { style: { color: s.return_diff < 0 ? "var(--red)" : "var(--ink-1)" } }, s.label), ` \xB7 ${s.count}\uAC74 \xB7 \uC2B9\uB960 ${_pct(s.win_rate)} \xB7 \uD3C9\uADE0 ${_num(s.avg_return)}% \xB7 \uB300\uBE44 ${s.return_diff >= 0 ? "+" : ""}${_num(s.return_diff)}%p`))));
  }
  function AutopsyPanel({ state, wsStatus }) {
    var _a;
    const autopsy = (_a = state.page_data) == null ? void 0 : _a.autopsy;
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uC138\uADF8\uBA3C\uD2B8 \uBD80\uAC80", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC190\uC2E4 \uC9D1\uC911 \uC138\uADF8\uBA3C\uD2B8 \xB7 \uAD6C\uCCB4 \uC784\uACC4\uAC12")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !autopsy || autopsy.status !== "ok" ? /* @__PURE__ */ React.createElement("div", { style: { padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uC138\uADF8\uBA3C\uD2B8 \uBD80\uAC80\uC740 \uB77C\uC774\uBE0C \uC2E4\uD589\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." : "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \u2014 \uC138\uB300 \uC644\uB8CC \uC2DC \uC138\uADF8\uBA3C\uD2B8 \uBD80\uAC80\uC774 \uBC1C\uD589\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", marginBottom: 10 } }, "\uAC70\uB798 ", autopsy.trade_count, "\uAC74 \xB7 \uC804\uCCB4 \uC2B9\uB960 ", _pct(autopsy.overall_win_rate), " \xB7 \uD3C9\uADE0 ", _num(autopsy.overall_avg_return), "%"), /* @__PURE__ */ React.createElement(_SegRows, { title: "\uC2DC\uAC04\uB300 \uC190\uC2E4 \uC9D1\uC911", rows: autopsy.time_segments }), /* @__PURE__ */ React.createElement(_SegRows, { title: "\uC2DC\uCD1D \uBC34\uB4DC \uC190\uC2E4 \uC9D1\uC911", rows: autopsy.market_cap_segments }), /* @__PURE__ */ React.createElement(_SegRows, { title: "\uAD50\uCC28(\uC2DC\uAC04\uB300\xD7\uC2DC\uCD1D)", rows: autopsy.cross_segments }), autopsy.thresholds && autopsy.thresholds.length > 0 && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 } }, "\uAD6C\uCCB4 \uC784\uACC4\uAC12(\uC190\uC2E4 \uAD6C\uAC04)"), /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, autopsy.thresholds.map((t, i) => /* @__PURE__ */ React.createElement("li", { key: i, className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", padding: "3px 0", lineHeight: 1.5 } }, `${_ThresholdCond(t)} \xB7 ${t.count}\uAC74 \xB7 \uC2B9\uB960 ${_pct(t.win_rate)} \xB7 \uD3C9\uADE0 ${_num(t.mean_return)}%`)))))));
  }
  function _PopBar({ frac }) {
    const w = Math.max(0, Math.min(1, frac || 0)) * 100;
    return /* @__PURE__ */ React.createElement("div", { style: { background: "var(--bg-2)", borderRadius: 3, height: 6, overflow: "hidden" } }, /* @__PURE__ */ React.createElement("div", { style: { width: `${w}%`, height: "100%", background: "var(--accent)" } }));
  }
  function PopulationPanel({ state, wsStatus }) {
    var _a;
    const pop = (_a = state.page_data) == null ? void 0 : _a.population;
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const members = pop && pop.members || [];
    const maxGraded = members.reduce((m, x) => Math.max(m, x.graded || 0), 0) || 1;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "GA Population", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, pop && pop.status === "ok" ? `K=${pop.k} \xB7 gate\uD1B5\uACFC ${pop.gate_passed_count} \xB7 \uAC00\uB4DC\uC2E4\uD328 ${pop.guardfail_count}` : "\uAC1C\uCCB4\uAD70 \uC9C4\uD654")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !pop || pop.status !== "ok" || members.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 GA population\uC740 \uB77C\uC774\uBE0C \uC2E4\uD589(evolution_mode=ga)\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." : "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \u2014 GA \uBAA8\uB4DC \uC138\uB300 \uD3C9\uAC00 \uC2DC \uAC1C\uCCB4\uAD70\uC774 \uBC1C\uD589\uB429\uB2C8\uB2E4(hillclimb \uBAA8\uB4DC\uB294 \uBBF8\uBC1C\uD589).") : /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, members.map((m, i) => {
      var _a2, _b, _c;
      return /* @__PURE__ */ React.createElement("li", { key: i, style: { padding: "6px 0", borderBottom: "1px solid var(--bg-2)" } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", display: "flex", justifyContent: "space-between", marginBottom: 3 } }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("span", { style: { color: m.gate_passed ? "var(--green)" : "var(--ink-2)" } }, "\u25CF"), ` graded ${((_a2 = m.graded) != null ? _a2 : 0).toFixed(3)}`, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, ` [${m.origin}]`)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, `${m.trade_count}\uAC74 \xB7 MDD ${((_b = m.mdd) != null ? _b : 0).toFixed(1)} \xB7 ${((_c = m.profit) != null ? _c : 0).toLocaleString()}`)), /* @__PURE__ */ React.createElement(_PopBar, { frac: (m.graded || 0) / maxGraded }));
    }))));
  }
  function _lnNum(x) {
    return typeof x === "number" ? x.toFixed(2) : "\u2014";
  }
  function LineagePanel({ state, wsStatus }) {
    var _a;
    const lineage = (_a = state.page_data) == null ? void 0 : _a.lineage;
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const nodes = lineage && lineage.nodes || [];
    const bestPath = lineage && lineage.best_path || [];
    const bestSet = new Set(bestPath);
    const ordered = [...nodes].sort((a, b) => a.gen_no - b.gen_no);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uC804\uB7B5 \uACC4\uBCF4 \xB7 \uBC84\uC804 \uACBD\uACFC", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, lineage && lineage.status === "ok" ? `\uC2DC\uB4DC\u2192best \uACBD\uB85C ${bestPath.length}\uC138\uB300 \xB7 \uCD1D ${lineage.node_count}\uC138\uB300` : "\uC138\uB300 \uACC4\uBCF4/\uCD94\uC774")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !lineage || lineage.status !== "ok" || ordered.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uC804\uB7B5 \uACC4\uBCF4\uB294 \uB77C\uC774\uBE0C \uC2E4\uD589\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." : "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \u2014 \uC138\uB300 \uC644\uB8CC \uC2DC \uACC4\uBCF4\uAC00 \uBC1C\uD589\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", marginBottom: 8 } }, "best \uC138\uB300 = gen_", String(lineage.best_gen).padStart(2, "0"), " \xB7 \uACBD\uB85C ", bestPath.map((g) => `g${g}`).join(" \u2192 ")), /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, ordered.map((n, i) => /* @__PURE__ */ React.createElement("li", { key: i, style: { padding: "5px 0", borderBottom: "1px solid var(--bg-2)" } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", display: "flex", justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("span", { style: { color: bestSet.has(n.gen_no) ? "var(--teal)" : "var(--ink-2)" } }, bestSet.has(n.gen_no) ? "\u2605" : "\xB7"), ` gen_${String(n.gen_no).padStart(2, "0")}`, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, n.parent_gen != null ? ` \u2190 gen_${String(n.parent_gen).padStart(2, "0")}` : " (\uB8E8\uD2B8)")), /* @__PURE__ */ React.createElement("span", { style: { color: n.gate_passed ? "var(--green)" : "var(--ink-3)" } }, `graded ${_lnNum(n.graded_score)} \xB7 ${n.trade_count}\uAC74 \xB7 MDD ${_lnNum(n.mdd)}`)), n.diff_from_parent && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginTop: 2, paddingLeft: 14 } }, n.diff_from_parent)))))));
  }
  function MetaPanel({ state, wsStatus }) {
    var _a, _b, _c, _d;
    const meta = (_a = state.page_data) == null ? void 0 : _a.meta;
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const commonVars = meta && meta.common_pass_vars || [];
    const changes = meta && meta.improving_changes || [];
    const fp = meta && meta.failure_patterns || {};
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uBA54\uD0C0\uBD84\uC11D \xB7 \uB204\uC801 \uD559\uC2B5", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, meta && meta.status === "ok" ? `\uB204\uC801 ${meta.total_generations}\uC138\uB300 \xB7 \uD1B5\uACFC ${meta.passing_count}` : "\uD1B5\uACFC \uC804\uB7B5 \uACF5\uD1B5 \uC870\uAC74")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !meta || meta.status !== "ok" ? /* @__PURE__ */ React.createElement("div", { style: { padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBA54\uD0C0\uBD84\uC11D\uC740 \uB77C\uC774\uBE0C \uC2E4\uD589\uC5D0\uC11C \uB204\uC801 \uBC1C\uD589\uB429\uB2C8\uB2E4." : "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \u2014 run \uC885\uB8CC \uC2DC \uB204\uC801 \uBA54\uD0C0 \uC778\uC0AC\uC774\uD2B8\uAC00 \uBC1C\uD589\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", null, commonVars.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 } }, "\uD1B5\uACFC \uC804\uB7B5 \uACF5\uD1B5 \uBCC0\uC218"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 6 } }, commonVars.map((v, i) => /* @__PURE__ */ React.createElement("span", { key: i, className: "mono", style: {
      fontSize: 11,
      color: "var(--ink-0)",
      background: "var(--bg-2)",
      borderRadius: 4,
      padding: "2px 7px"
    } }, `${v[0]} \xD7${v[1]}`)))), changes.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 } }, "\uAC1C\uC120\uC744 \uB0B3\uC740 \uBCC0\uACBD"), /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none" } }, changes.map((c, i) => /* @__PURE__ */ React.createElement("li", { key: i, className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" } }, `\xB7 ${c[0]} (\xD7${c[1]})`)))), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-2)" } }, `\uC2E4\uD328 \uD328\uD134 \u2014 \uACFC\uB9E4\uB9E4 ${(_b = fp.overtrade) != null ? _b : 0} \xB7 0\uAC70\uB798 ${(_c = fp.zero_trade) != null ? _c : 0} \xB7 \uACE0MDD ${(_d = fp.high_mdd) != null ? _d : 0}`))));
  }
  function _hoNum(x) {
    return typeof x === "number" ? x.toFixed(2) : "\u2014";
  }
  function HoldoutPanel({ state, wsStatus }) {
    var _a;
    const holdout = (_a = state.page_data) == null ? void 0 : _a.holdout;
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const hasData = holdout && holdout.status && holdout.status !== "off";
    const passed = holdout && holdout.passed === true;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uACFC\uC801\uD569 \uBC29\uC5B4 \xB7 holdout \uC878\uC5C5\uAC80\uC0AC", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), hasData && /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
      fontSize: 10.5,
      fontWeight: 600,
      color: passed ? "var(--good, #2ecc71)" : "var(--warn, #e0a030)"
    } }, passed ? "holdout \uD1B5\uACFC \u2713" : "holdout \uBBF8\uD1B5\uACFC")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !hasData ? /* @__PURE__ */ React.createElement("div", { style: { padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 } }, isDemo ? "\uB370\uBAA8 \uBAA8\uB4DC \u2014 holdout \uC878\uC5C5\uAC80\uC0AC\uB294 \uB77C\uC774\uBE0C \uC2E4\uD589(graduation_holdout=ON)\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." : "holdout \uC878\uC5C5\uAC80\uC0AC OFF \uB610\uB294 \uB300\uAE30 \u2014 train \uAC8C\uC774\uD2B8 \uD1B5\uACFC \uD6C4\uBCF4\uC5D0 \uD55C\uD574 holdout \uD310\uC815\uC774 \uBC1C\uD589\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" } }, `train \uAC70\uB798 ${holdout.train_trade_count} \xB7 holdout \uAC70\uB798 ${holdout.trade_count}`), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" } }, `holdout MDD ${_hoNum(holdout.mdd_pct)}% \xB7 holdout \uC218\uC775 ${typeof holdout.total_profit === "number" ? holdout.total_profit.toLocaleString() : "\u2014"}\uC6D0`), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-2)", marginTop: 4 } }, `\uD310\uC815: ${holdout.reason || holdout.status}`))));
  }
  function ExportStatusBanner({ reply }) {
    if (!reply || reply.action !== "final_approval") return null;
    const ok = reply.status === "ok";
    const buyName = reply.buy && reply.buy.name;
    const sellName = reply.sell && reply.sell.name;
    return /* @__PURE__ */ React.createElement("div", { style: {
      padding: "10px 14px",
      borderRadius: 6,
      marginBottom: 4,
      fontSize: 12.5,
      border: `1px solid ${ok ? "rgba(46,204,113,0.4)" : "rgba(224,90,90,0.4)"}`,
      background: ok ? "rgba(46,204,113,0.08)" : "rgba(224,90,90,0.08)",
      color: "var(--ink-0)"
    } }, ok ? /* @__PURE__ */ React.createElement("span", null, "\u2713 \uC6B4\uC601 strategy.db\uB85C export \uC644\uB8CC", reply.demo ? " (\uB370\uBAA8)" : "", " \u2014 \uB9E4\uC218 ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, buyName || "\u2014"), " \xB7 \uB9E4\uB3C4 ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, sellName || "\u2014"), reply.dest_db && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-3)" } }, ` \u2192 ${reply.dest_db}`)) : /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, "\u2717 export \uC2E4\uD328 \u2014 ", reply.message || "\uC54C \uC218 \uC5C6\uB294 \uC624\uB958"));
  }
  Object.assign(window, { ConnBadge, StatusBadge, CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner });

  // ../frontend/run-compare.jsx
  var { useState: useState_rc, useEffect: useEffect_rc, useMemo: useMemo_rc } = React;
  function rcNum(value, digits = 2) {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
  }
  function rcMoney(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("ko-KR") : "-";
  }
  function rcPct(value) {
    return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)}%` : "-";
  }
  function rcDuration(sec) {
    if (typeof sec !== "number" || !Number.isFinite(sec)) return "-";
    if (sec < 60) return `${sec.toFixed(1)}s`;
    const min = Math.floor(sec / 60);
    const rem = Math.round(sec % 60);
    if (min < 60) return `${min}m ${rem}s`;
    return `${Math.floor(min / 60)}h ${min % 60}m`;
  }
  function rcYears(run) {
    if (Array.isArray(run.years) && run.years.length) return run.years.join(", ");
    if (run.start_year && run.end_year) return `${run.start_year}-${run.end_year}`;
    return "-";
  }
  function rcWindow(run) {
    const start = run.bt_universe_start_time;
    const end = run.bt_universe_end_time;
    return start || end ? `${start || "-"}~${end || "-"}` : "-";
  }
  function rcValue(run, key) {
    const v = run[key];
    return typeof v === "number" && Number.isFinite(v) ? v : Number.NEGATIVE_INFINITY;
  }
  function rcDefaultCompareIds(runs) {
    const matched = runs.filter((r) => /seed|ai/i.test(String(r.run_id || ""))).slice(0, 6).map((r) => r.run_id);
    return matched.length >= 2 ? matched : runs.slice(0, 2).map((r) => r.run_id);
  }
  function RunComparePanel({ baseUrl, wsStatus }) {
    const [runs, setRuns] = useState_rc([]);
    const [selected, setSelected] = useState_rc([]);
    const [compareRows, setCompareRows] = useState_rc([]);
    const [sortKey, setSortKey] = useState_rc("final_profit");
    const [err, setErr] = useState_rc("");
    const [loading, setLoading] = useState_rc(false);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const sortedRuns = useMemo_rc(() => {
      return [...runs].sort((a, b) => rcValue(b, sortKey) - rcValue(a, sortKey));
    }, [runs, sortKey]);
    const refresh = React.useCallback(() => {
      if (isDemo || !baseUrl) return;
      setLoading(true);
      setErr("");
      fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(3e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        const rows = Array.isArray(j.runs) ? j.runs : [];
        setRuns(rows);
        setErr(j.error || "");
        if (!selected.length) setSelected(rcDefaultCompareIds(rows));
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, selected.length]);
    useEffect_rc(() => {
      refresh();
    }, [refresh]);
    useEffect_rc(() => {
      if (isDemo || !baseUrl || !selected.length) {
        setCompareRows([]);
        return;
      }
      const ids = selected.map(encodeURIComponent).join(",");
      fetch(baseUrl + "/runs/compare?ids=" + ids, { signal: AbortSignal.timeout(3500) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => setCompareRows(Array.isArray(j.generation_rows) ? j.generation_rows : [])).catch(() => setCompareRows([]));
    }, [baseUrl, isDemo, selected.join("|")]);
    const toggleSelected = (runId) => {
      setSelected((prev) => prev.includes(runId) ? prev.filter((x) => x !== runId) : [...prev, runId]);
    };
    const selectSeedAi = () => setSelected(rcDefaultCompareIds(runs));
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Run Compare Console", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setSortKey("final_profit") }, "Sort: Total Profit"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setSortKey("total_profit_pct") }, "Return %"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: selectSeedAi, disabled: !runs.length }, "Seed vs AI"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: refresh, disabled: isDemo || loading }, loading ? "loading" : "refresh"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "run-compare-empty" }, "Demo mode: run comparison is available with a backend connection.") : err ? /* @__PURE__ */ React.createElement("div", { className: "run-compare-empty danger" }, "query failed: ", err) : runs.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "run-compare-empty" }, "No recorded runs.") : /* @__PURE__ */ React.createElement("div", { className: "run-compare-shell" }, /* @__PURE__ */ React.createElement("div", { className: "run-compare-kpis" }, /* @__PURE__ */ React.createElement("span", null, "runs=", runs.length), /* @__PURE__ */ React.createElement("span", null, "selected=", selected.length), /* @__PURE__ */ React.createElement("span", null, "generation_rows=", compareRows.length), /* @__PURE__ */ React.createElement("span", null, "sort=", sortKey)), /* @__PURE__ */ React.createElement("div", { className: "run-compare-scroll" }, /* @__PURE__ */ React.createElement("table", { className: "run-compare-table" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "Pick"), /* @__PURE__ */ React.createElement("th", null, "run_id"), /* @__PURE__ */ React.createElement("th", null, "Status"), /* @__PURE__ */ React.createElement("th", null, "Period"), /* @__PURE__ */ React.createElement("th", null, "Years"), /* @__PURE__ */ React.createElement("th", null, "min/tick"), /* @__PURE__ */ React.createElement("th", null, "Universe Time"), /* @__PURE__ */ React.createElement("th", null, "Total Profit"), /* @__PURE__ */ React.createElement("th", null, "Return %"), /* @__PURE__ */ React.createElement("th", null, "Trades"), /* @__PURE__ */ React.createElement("th", null, "Daily"), /* @__PURE__ */ React.createElement("th", null, "MDD"), /* @__PURE__ */ React.createElement("th", null, "Payoff"), /* @__PURE__ */ React.createElement("th", null, "Max Hold"), /* @__PURE__ */ React.createElement("th", null, "Elapsed"), /* @__PURE__ */ React.createElement("th", null, "Cost/Count"), /* @__PURE__ */ React.createElement("th", null, "Winner"))), /* @__PURE__ */ React.createElement("tbody", null, sortedRuns.map((r) => {
      var _a;
      const sparseHoldSuspicious = typeof r.max_hold_count === "number" && r.max_hold_count <= 1 && (r.trade_count || 0) >= 50;
      return /* @__PURE__ */ React.createElement("tr", { key: r.run_id }, /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement("input", { type: "checkbox", checked: selected.includes(r.run_id), onChange: () => toggleSelected(r.run_id) })), /* @__PURE__ */ React.createElement("td", null, r.run_id), /* @__PURE__ */ React.createElement("td", null, r.status || "-"), /* @__PURE__ */ React.createElement("td", null, r.period || "-"), /* @__PURE__ */ React.createElement("td", null, rcYears(r)), /* @__PURE__ */ React.createElement("td", null, r.timeframe || "-"), /* @__PURE__ */ React.createElement("td", null, rcWindow(r)), /* @__PURE__ */ React.createElement("td", { className: r.final_profit > 0 ? "num-pos" : r.final_profit < 0 ? "num-neg" : "num-muted" }, rcMoney(r.final_profit)), /* @__PURE__ */ React.createElement("td", { className: r.total_profit_pct > 0 ? "num-pos" : r.total_profit_pct < 0 ? "num-neg" : "num-muted" }, rcPct(r.total_profit_pct)), /* @__PURE__ */ React.createElement("td", null, (_a = r.trade_count) != null ? _a : 0), /* @__PURE__ */ React.createElement("td", null, rcNum(r.daily_avg_trades, 1)), /* @__PURE__ */ React.createElement("td", { className: r.mdd > 0 ? "num-neg" : "num-muted" }, rcPct(r.mdd)), /* @__PURE__ */ React.createElement("td", null, rcNum(r.payoff_ratio, 2)), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: sparseHoldSuspicious ? "num-neg" : "",
          title: sparseHoldSuspicious ? "Sparse hold warning: max_hold_count <= 1 with enough trades; compare Backtest Detail CSV peak_holdings. human corridor 6-12" : "max_hold_count"
        },
        rcNum(r.max_hold_count, 0),
        sparseHoldSuspicious ? " !" : ""
      ), /* @__PURE__ */ React.createElement("td", null, rcDuration(r.elapsed_sec)), /* @__PURE__ */ React.createElement("td", null, r.cost_or_count_text || rcNum(r.cost_or_count, 1)), /* @__PURE__ */ React.createElement("td", null, r.winner ? `gen_${String(r.winner.gen_no).padStart(2, "0")} / ${rcNum(r.winner.graded_score, 3)}` : "-"));
    })))), /* @__PURE__ */ React.createElement("div", { className: "run-compare-gen" }, /* @__PURE__ */ React.createElement("span", null, "Selected generation preview:"), compareRows.slice(0, 6).map((row) => /* @__PURE__ */ React.createElement("span", { key: `${row.run_id}-${row.gen_no}` }, row.run_id, "/g", row.gen_no, ": ", rcMoney(row.profit), " (", rcPct(row.return_pct), ") ", rcDuration(row.duration_sec)))))));
  }
  Object.assign(window, { RunComparePanel });

  // ../frontend/phase-detail.jsx
  var { useState: useState_ph, useMemo: useMemo_ph, useEffect: useEffect_ph, useRef: useRef_ph } = React;
  function DemoBadge() {
    return /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
      fontSize: 9.5,
      letterSpacing: ".12em",
      padding: "1px 6px",
      borderRadius: 4,
      background: "rgba(165,148,255,0.16)",
      color: "#a594ff",
      border: "1px solid rgba(165,148,255,0.4)",
      textTransform: "uppercase"
    }, "data-tip": "\uC2DC\uBBAC\uB808\uC774\uD130\uAC00 \uC0DD\uC131\uD55C \uB370\uBAA8 \uB370\uC774\uD130\uC785\uB2C8\uB2E4 (backend \uBBF8\uBC1C\uD589)" }, "DEMO");
  }
  function LivePending({ note }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      padding: "24px 20px",
      color: "var(--ink-3)",
      textAlign: "center",
      fontSize: 12,
      fontFamily: "var(--mono)",
      lineHeight: 1.6
    }, "data-tip": "Live data pending: waiting for a fresh live snapshot from backend." }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 13, color: "var(--ink-2)", marginBottom: 6 } }, "\uC2E4\uC2DC\uAC04 \uB370\uC774\uD130 \uB300\uAE30 \xB7 Live data pending"), note || "Waiting for a fresh live snapshot from backend; this panel is not a stale result.");
  }
  var PHASES = [
    { key: "\uC0DD\uC131\uC911", label: "\uC0DD\uC131", sub: "LLM Code Gen" },
    { key: "\uBC31\uD14C\uC2A4\uD2B8\uC911", label: "\uBC31\uD14C\uC2A4\uD2B8", sub: "Backtest" },
    { key: "\uCC44\uC810\uC911", label: "\uCC44\uC810", sub: "Grading" },
    { key: "\uBD80\uAC80 \uC791\uC131", label: "\uBD80\uAC80", sub: "Autopsy" }
  ];
  var LIVE_PHASE_INDEX = {
    // 생성/준비(백테 이전).
    loop_start: 0,
    warm_prepare_start: 0,
    warm_prepare_done: 0,
    ga_init: 0,
    generate_start: 0,
    generate_done: 0,
    // 백테스트.
    backtest_start: 1,
    ga_evaluate_start: 1,
    // 채점(백테 종료 직후 fitness 산출).
    backtest_end: 2,
    score_start: 2,
    score_done: 2,
    // 부검/세대 완료.
    autopsy_start: 3,
    autopsy_done: 3,
    generation_done: 3,
    ga_generation_done: 3,
    complete: 3
  };
  function phaseIndex(phase) {
    const k = PHASES.findIndex((p) => p.key === phase);
    if (k !== -1) return k;
    if (phase != null && Object.prototype.hasOwnProperty.call(LIVE_PHASE_INDEX, phase)) {
      return LIVE_PHASE_INDEX[phase];
    }
    return -1;
  }
  function PhaseTimeline({ state }) {
    var _a;
    const running = state.status === "running" || state.status === "stopping";
    const activeIdx = running ? phaseIndex((_a = state.latest) == null ? void 0 : _a.phase) : -1;
    const activeGen = running ? state.current_gen + 1 : state.current_gen;
    return /* @__PURE__ */ React.createElement("div", { className: "phase-timeline" }, PHASES.map((p, i) => {
      const isActive = i === activeIdx;
      const isDone = activeIdx > i;
      const isPending = activeIdx < i || activeIdx === -1;
      return /* @__PURE__ */ React.createElement(React.Fragment, { key: p.key }, /* @__PURE__ */ React.createElement("div", { className: `phase-step ${isActive ? "active" : isDone ? "done" : "pending"}` }, /* @__PURE__ */ React.createElement("div", { className: "phase-num" }, isDone ? /* @__PURE__ */ React.createElement("svg", { width: "11", height: "11", viewBox: "0 0 16 16" }, /* @__PURE__ */ React.createElement("path", { d: "M3 8 L7 12 L13 4", stroke: "currentColor", strokeWidth: "2", fill: "none", strokeLinecap: "round", strokeLinejoin: "round" })) : i + 1), /* @__PURE__ */ React.createElement("div", { className: "phase-step-text" }, /* @__PURE__ */ React.createElement("div", { className: "phase-step-label" }, p.label), /* @__PURE__ */ React.createElement("div", { className: "phase-step-sub" }, p.sub)), isActive && /* @__PURE__ */ React.createElement("span", { className: "phase-active-pulse" })), i < PHASES.length - 1 && /* @__PURE__ */ React.createElement("div", { className: `phase-connector ${isDone ? "done" : ""}` }, /* @__PURE__ */ React.createElement("div", { className: "phase-connector-fill", style: { width: isDone ? "100%" : isActive ? "50%" : "0%" } })));
    }), /* @__PURE__ */ React.createElement("div", { className: "phase-gen-tag" }, running ? `\uC138\uB300 ${activeGen} \uC9C4\uD589\uC911` : state.status === "complete" ? `${state.current_gen}\uC138\uB300 \uC644\uB8CC` : "\uB300\uAE30\uC911"));
  }
  function PhaseDetailPanel({ state, wsStatus, onViewLatestCode }) {
    var _a, _b, _c, _d;
    const phase = (_a = state.latest) == null ? void 0 : _a.phase;
    const running = state.status === "running" || state.status === "stopping";
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const livePending = typeof window.livePanelPending === "function" ? window.livePanelPending(wsStatus, state) : false;
    let body;
    if (livePending) {
      body = /* @__PURE__ */ React.createElement(LivePending, null);
    } else if (phase === "\uC0DD\uC131\uC911") {
      body = /* @__PURE__ */ React.createElement(GenerationView, { state, onViewLatestCode });
    } else if (phase === "\uBC31\uD14C\uC2A4\uD2B8\uC911") {
      body = /* @__PURE__ */ React.createElement(BacktestingView, { state });
    } else if (phase === "\uCC44\uC810\uC911") {
      body = /* @__PURE__ */ React.createElement(ScoringView, { state });
    } else if (phase === "\uBD80\uAC80 \uC791\uC131") {
      body = /* @__PURE__ */ React.createElement(AutopsyView, { state });
    } else if (!running && (((_c = (_b = state.current_run) == null ? void 0 : _b.equity) == null ? void 0 : _c.length) || 0) > 0) {
      body = /* @__PURE__ */ React.createElement(BacktestingView, { state });
    } else {
      body = /* @__PURE__ */ React.createElement(IdlePhaseView, null);
    }
    return /* @__PURE__ */ React.createElement("div", { className: "panel phase-detail" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: running ? "var(--amber)" : "var(--ink-3)" } }), "\uD398\uC774\uC988 \uC0C1\uC138 \u2014 ", phase || "\u2014", isDemo && /* @__PURE__ */ React.createElement(DemoBadge, null)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, ((_d = state.latest) == null ? void 0 : _d.last_checkpoint) || "\u2014")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: 0 } }, body));
  }
  function GenerationView({ state, onViewLatestCode }) {
    var _a;
    const g = ((_a = state.current_run) == null ? void 0 : _a.generation) || {};
    const ctx = g.prompt_context || [];
    const active = g.active || "buy";
    const showCode = active === "sell" || active === "done" ? g.sell_code_partial || "" : g.buy_code_partial || "";
    const codeLabel = active === "buy" ? "\uB9E4\uC218 \uC870\uAC74\uC2DD \u2014 streaming" : active === "sell" ? "\uB9E4\uB3C4 \uC870\uAC74\uC2DD \u2014 streaming" : "\uC0DD\uC131 \uC644\uB8CC";
    const buyDone = !!g.buy_done;
    const sellDone = !!g.sell_done;
    const highlighted = useMemo_ph(() => {
      if (typeof window.highlightPython === "function") {
        return window.highlightPython(showCode);
      }
      return showCode.split("\n").map((t, i) => ({ ln: i + 1, parts: [{ cls: "", t }] }));
    }, [showCode]);
    const codeRef = useRef_ph(null);
    useEffect_ph(() => {
      if (codeRef.current) {
        codeRef.current.scrollTop = codeRef.current.scrollHeight;
      }
    }, [showCode]);
    return /* @__PURE__ */ React.createElement("div", { className: "gen-view" }, /* @__PURE__ */ React.createElement("div", { className: "gen-view-grid" }, /* @__PURE__ */ React.createElement("div", { className: "gen-side" }, /* @__PURE__ */ React.createElement("div", { className: "side-section" }, /* @__PURE__ */ React.createElement("div", { className: "side-section-title" }, "LLM \uD638\uCD9C"), /* @__PURE__ */ React.createElement("div", { className: "side-kv" }, /* @__PURE__ */ React.createElement("span", { className: "k" }, "provider"), /* @__PURE__ */ React.createElement("span", { className: "v mono" }, state.provider), /* @__PURE__ */ React.createElement("span", { className: "k" }, "tokens"), /* @__PURE__ */ React.createElement("span", { className: "v mono tnum" }, (g.stream_tokens || 0).toLocaleString()))), /* @__PURE__ */ React.createElement("div", { className: "side-section" }, /* @__PURE__ */ React.createElement("div", { className: "side-section-title" }, "\uD53C\uB4DC\uBC31 \uCEE8\uD14D\uC2A4\uD2B8 (Few-shot)"), ctx.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "side-empty" }, "\uCCAB \uC138\uB300 \u2014 \uCEE8\uD14D\uC2A4\uD2B8 \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("ul", { className: "side-list" }, ctx.map((c, i) => /* @__PURE__ */ React.createElement("li", { key: i, className: "mono", style: { fontSize: 11 } }, c)))), /* @__PURE__ */ React.createElement("div", { className: "side-section" }, /* @__PURE__ */ React.createElement("div", { className: "side-section-title" }, "\uC9C4\uD589"), /* @__PURE__ */ React.createElement("div", { className: "gen-prog-row" }, /* @__PURE__ */ React.createElement("span", { className: `gen-prog-dot ${buyDone ? "done" : active === "buy" ? "active" : ""}` }), /* @__PURE__ */ React.createElement("span", { className: "gen-prog-label" }, "\uB9E4\uC218 \uC870\uAC74\uC2DD"), /* @__PURE__ */ React.createElement("span", { className: `mono gen-prog-state ${buyDone ? "done" : ""}` }, buyDone ? "\u2713" : active === "buy" ? "\u2026" : "")), /* @__PURE__ */ React.createElement("div", { className: "gen-prog-row" }, /* @__PURE__ */ React.createElement("span", { className: `gen-prog-dot ${sellDone ? "done" : active === "sell" ? "active" : ""}` }), /* @__PURE__ */ React.createElement("span", { className: "gen-prog-label" }, "\uB9E4\uB3C4 \uC870\uAC74\uC2DD"), /* @__PURE__ */ React.createElement("span", { className: `mono gen-prog-state ${sellDone ? "done" : ""}` }, sellDone ? "\u2713" : active === "sell" ? "\u2026" : "")))), /* @__PURE__ */ React.createElement("div", { className: "gen-code-col" }, /* @__PURE__ */ React.createElement("div", { className: "gen-code-header" }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: active === "sell" ? "var(--amber)" : "var(--teal)" } }, "\u25CF"), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 11, color: "var(--ink-1)", letterSpacing: ".06em", textTransform: "uppercase" } }, codeLabel), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" } }, (showCode || "").split("\n").length, " lines \xB7 \uC2A4\uD2B8\uB9AC\uBC0D\uC911")), /* @__PURE__ */ React.createElement("pre", { className: "code-block stream", ref: codeRef }, highlighted.map((row, i) => /* @__PURE__ */ React.createElement("div", { key: i }, /* @__PURE__ */ React.createElement("span", { className: "ln" }, row.ln), row.parts.map((p, j) => /* @__PURE__ */ React.createElement("span", { key: j, className: p.cls }, p.t)))), /* @__PURE__ */ React.createElement("span", { className: "stream-caret blink" }, "\u258C")))));
  }
  function BacktestingView({ state }) {
    var _a, _b, _c, _d, _e, _f, _g, _h;
    const equity = ((_a = state.current_run) == null ? void 0 : _a.equity) || [];
    const baseline = 1e7;
    const last = equity[equity.length - 1];
    const lastPnl = last ? last.value - baseline : 0;
    const lastDD = (_e = (_d = (_c = (_b = state.current_run) == null ? void 0 : _b.drawdown) == null ? void 0 : _c.slice(-1)[0]) == null ? void 0 : _d.value_pct) != null ? _e : 0;
    const trades = ((_f = state.current_run) == null ? void 0 : _f.trades) || [];
    return /* @__PURE__ */ React.createElement("div", { className: "bt-view" }, /* @__PURE__ */ React.createElement("div", { className: "bt-summary-row" }, /* @__PURE__ */ React.createElement(
      SummaryCell,
      {
        label: "\uD604\uC7AC \uC790\uBCF8",
        value: `${last ? (last.value / 1e6).toFixed(2) : "10.00"} M`,
        color: lastPnl >= 0 ? "var(--teal)" : "var(--red)",
        sub: `\uAE30\uC900 10.00M`
      }
    ), /* @__PURE__ */ React.createElement(
      SummaryCell,
      {
        label: "\uC21C\uC190\uC775",
        value: `${lastPnl >= 0 ? "+" : "\u2212"}${Math.abs(lastPnl).toLocaleString("ko-KR")}\uC6D0`,
        color: lastPnl >= 0 ? "var(--teal)" : "var(--red)",
        sub: `${(lastPnl / baseline * 100).toFixed(2)}%`
      }
    ), /* @__PURE__ */ React.createElement(
      SummaryCell,
      {
        label: "\uC2E4\uC2DC\uAC04 \uB099\uD3ED",
        value: `${lastDD.toFixed(2)}%`,
        color: "var(--red)",
        sub: `peak ${Math.max(0, ...((_h = (_g = state.current_run) == null ? void 0 : _g.drawdown) == null ? void 0 : _h.map((p) => p.value_pct)) || [0]).toFixed(2)}%`
      }
    ), /* @__PURE__ */ React.createElement(
      SummaryCell,
      {
        label: "\uB204\uC801 \uB9E4\uB9E4",
        value: trades.length,
        sub: `\uB9E4\uC218 ${trades.filter((t) => t.side === "buy").length} / \uB9E4\uB3C4 ${trades.filter((t) => t.side === "sell").length}`
      }
    )), window.LiveBacktestChart ? /* @__PURE__ */ React.createElement("div", { className: "bt-chart-embed" }, /* @__PURE__ */ React.createElement(LiveBacktestChartInline, { state })) : null);
  }
  function SummaryCell({ label, value, color, sub }) {
    return /* @__PURE__ */ React.createElement("div", { className: "summary-cell" }, /* @__PURE__ */ React.createElement("div", { className: "summary-lbl" }, label), /* @__PURE__ */ React.createElement("div", { className: "summary-val mono", style: { color: color || "var(--ink-0)" } }, value), sub && /* @__PURE__ */ React.createElement("div", { className: "summary-sub mono" }, sub));
  }
  function LiveBacktestChartInline({ state }) {
    var _a, _b, _c;
    const equity = ((_a = state.current_run) == null ? void 0 : _a.equity) || [];
    const drawdown = ((_b = state.current_run) == null ? void 0 : _b.drawdown) || [];
    const trades = ((_c = state.current_run) == null ? void 0 : _c.trades) || [];
    const baseline = 1e7;
    const W = 880, H = 200;
    const padL = 56, padR = 56, padT = 10, padB = 22;
    const innerH = H - padT - padB;
    const xMax = Math.max(60, equity.length ? equity[equity.length - 1].t : 60);
    const { maxEq, minEq, ddMax, x, y, yDD, eqPath, eqAreaPath, ddAreaPath } = useMemo_ph(
      () => _liveChartGeom({ equity, drawdown, baseline, W, H, padL, padR, padT, padB, xMax }),
      [equity, drawdown, xMax]
    );
    return /* @__PURE__ */ React.createElement("div", { className: "live-chart-wrap" }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("linearGradient", { id: "eq-grad-inline", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "#4cd6b3", stopOpacity: "0.5" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "#4cd6b3", stopOpacity: "0" })), /* @__PURE__ */ React.createElement("linearGradient", { id: "dd-grad-inline", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "#ff6b6b", stopOpacity: "0.22" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "#ff6b6b", stopOpacity: "0" }))), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)" }), /* @__PURE__ */ React.createElement("line", { x1: W - padR, x2: W - padR, y1: padT, y2: padT + innerH, stroke: "var(--line-2)" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(baseline), y2: y(baseline), className: "zero-line" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: y(baseline) + 3, textAnchor: "end" }, (baseline / 1e6).toFixed(1), "M"), [0.25, 0.5, 0.75].map((t, i) => {
      const v = minEq + (maxEq - minEq) * t;
      return /* @__PURE__ */ React.createElement("g", { key: i }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(v), y2: y(v), className: "chart-grid-line" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: y(v) + 3, textAnchor: "end" }, (v / 1e6).toFixed(2), "M"));
    }), [0.5, 1].map((t, i) => {
      const v = ddMax * t;
      return /* @__PURE__ */ React.createElement("text", { key: i, className: "chart-axis-text", x: W - padR + 6, y: yDD(v) + 3, fill: "var(--red)", opacity: "0.7" }, "\u2212", v.toFixed(1), "%");
    }), drawdown.length > 1 && /* @__PURE__ */ React.createElement("path", { d: ddAreaPath, fill: "url(#dd-grad-inline)" }), equity.length > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: eqAreaPath, fill: "url(#eq-grad-inline)" }), /* @__PURE__ */ React.createElement("path", { d: eqPath, className: "eq-line" })), trades.map((tr, i) => /* @__PURE__ */ React.createElement(
      "circle",
      {
        key: i,
        cx: x(tr.t),
        cy: y(tr.price),
        r: "2.5",
        className: tr.side === "buy" ? "trade-marker-buy" : "trade-marker-sell",
        opacity: "0.85"
      }
    )), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL, y: H - 6 }, "0m"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR, y: H - 6, textAnchor: "end" }, xMax, "m")), equity.length === 0 && /* @__PURE__ */ React.createElement("div", { className: "chart-empty" }, "\uBC31\uD14C\uC2A4\uD2B8 \uC2DC\uC791\uC744 \uAE30\uB2E4\uB9AC\uB294 \uC911..."));
  }
  function ScoringView({ state }) {
    var _a, _b, _c, _d;
    const metrics = ((_b = (_a = state.current_run) == null ? void 0 : _a.scoring) == null ? void 0 : _b.metrics) || [];
    const composite = (_d = (_c = state.current_run) == null ? void 0 : _c.scoring) == null ? void 0 : _d.composite;
    const targetFromConfig = 1;
    return /* @__PURE__ */ React.createElement("div", { className: "score-view" }, /* @__PURE__ */ React.createElement("div", { className: "score-formula" }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-2)" } }, "graded_score"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-3)" } }, "="), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-1)" } }, "\u03A3 (metric", /* @__PURE__ */ React.createElement("sub", null, "i"), " \xD7 weight", /* @__PURE__ */ React.createElement("sub", null, "i"), ")"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: "auto", color: "var(--ink-3)" } }, metrics.length, "/4 \uCC44\uC810 \uC644\uB8CC")), /* @__PURE__ */ React.createElement("div", { className: "score-metrics" }, [0, 1, 2, 3].map((i) => {
      var _a2, _b2;
      const m = metrics[i];
      const ready = !!m;
      const v = (_a2 = m == null ? void 0 : m.value) != null ? _a2 : 0;
      const w = (_b2 = m == null ? void 0 : m.weight) != null ? _b2 : 0.25;
      const weighted = ready ? v * w : 0;
      const labels = ["\uC190\uC775 (profit factor)", "MDD \uD398\uB110\uD2F0", "\uAC70\uB798\uC218 \uC801\uC815\uC131", "\uC77C\uAD00\uC131 (sharpe-ish)"];
      const label = (m == null ? void 0 : m.label) || labels[i];
      return /* @__PURE__ */ React.createElement("div", { key: i, className: `score-metric ${ready ? "ready" : "pending"}` }, /* @__PURE__ */ React.createElement("div", { className: "metric-row" }, /* @__PURE__ */ React.createElement("span", { className: "metric-label" }, label), /* @__PURE__ */ React.createElement("span", { className: "metric-weight" }, "w=", w.toFixed(2))), /* @__PURE__ */ React.createElement("div", { className: "metric-bar-wrap" }, /* @__PURE__ */ React.createElement("div", { className: "metric-bar" }, /* @__PURE__ */ React.createElement(
        "div",
        {
          className: "metric-bar-fill",
          style: { width: `${ready ? Math.min(100, v * 100) : 0}%` }
        }
      )), /* @__PURE__ */ React.createElement("span", { className: "metric-val mono" }, ready ? v.toFixed(3) : /* @__PURE__ */ React.createElement("span", { className: "pulse-dot" }, "\u2026")), /* @__PURE__ */ React.createElement("span", { className: "metric-weighted mono" }, "\u2192 +", ready ? weighted.toFixed(3) : "\u2014")));
    })), /* @__PURE__ */ React.createElement("div", { className: "score-composite" }, /* @__PURE__ */ React.createElement("div", { className: "composite-label" }, "composite (graded_score)"), /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "composite-val mono",
        style: { color: composite != null ? composite >= targetFromConfig ? "var(--teal)" : "var(--ink-0)" : "var(--ink-3)" }
      },
      composite != null ? composite.toFixed(3) : "\u2014"
    ), composite != null && composite >= targetFromConfig && /* @__PURE__ */ React.createElement("span", { className: "pill gate-pass" }, "\u2713 \uAC8C\uC774\uD2B8 \uD1B5\uACFC")));
  }
  function AutopsyView({ state }) {
    var _a;
    const a = ((_a = state.current_run) == null ? void 0 : _a.autopsy) || {};
    const text = a.text_partial || "";
    const target = a.text_target || "";
    const ready = !!a.ready;
    return /* @__PURE__ */ React.createElement("div", { className: "autopsy-view" }, /* @__PURE__ */ React.createElement("div", { className: "autopsy-header" }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".12em", textTransform: "uppercase" } }, "AUTOPSY  \xB7  \uB2E4\uC74C \uC138\uB300 \uCEE8\uD14D\uC2A4\uD2B8\uB85C \uC8FC\uC785"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" } }, text.length, "/", target.length, " chars")), /* @__PURE__ */ React.createElement("div", { className: "autopsy-body" }, /* @__PURE__ */ React.createElement("span", { className: "mono autopsy-text" }, text || "..."), !ready && /* @__PURE__ */ React.createElement("span", { className: "stream-caret blink" }, "\u258C")), /* @__PURE__ */ React.createElement("div", { className: "autopsy-footnote" }, "\uBD80\uAC80\uC740 LLM\uC774 \uB9E4\uC218/\uB9E4\uB3C4 \uCF54\uB4DC\uC758 \uBC31\uD14C\uC2A4\uD2B8 \uACB0\uACFC\uB97C \uC790\uC5F0\uC5B4\uB85C \uC694\uC57D\uD55C \uAC83\uC774\uBA70, \uB2E4\uC74C \uC138\uB300 \uD504\uB86C\uD504\uD2B8\uC758 few-shot \uCEE8\uD14D\uC2A4\uD2B8\uB85C \uC804\uB2EC\uB429\uB2C8\uB2E4."));
  }
  function IdlePhaseView() {
    return /* @__PURE__ */ React.createElement("div", { style: {
      padding: "28px 24px",
      color: "var(--ink-3)",
      textAlign: "center",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uD398\uC774\uC988\uAC00 \uC9C4\uD589\uB418\uBA74 \uB2E8\uACC4\uBCC4 \uC0C1\uC138\uAC00 \uC5EC\uAE30\uC5D0 \uD45C\uC2DC\uB429\uB2C8\uB2E4");
  }
  var FLOW_STEPS = [
    { label: "\uC0DD\uC131", sub: "Generate", timingKey: "generate" },
    { label: "\uBC31\uD14C", sub: "Backtest", timingKey: "backtest" },
    { label: "\uCC44\uC810", sub: "Score", timingKey: "score" },
    { label: "\uBD80\uAC80", sub: "Autopsy", timingKey: "autopsy" },
    { label: "\uBC18\uBCF5", sub: "Iterate", timingKey: "iterate" }
  ];
  function fmtElapsedSec(sec) {
    const s = typeof sec === "number" && isFinite(sec) && sec > 0 ? Math.floor(sec) : 0;
    if (s < 60) return `${s}s`;
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}m${String(r).padStart(2, "0")}s`;
  }
  function fmtClockFromEpoch(epochSec) {
    if (!(typeof epochSec === "number" && isFinite(epochSec) && epochSec > 0)) return "";
    try {
      return new Date(epochSec * 1e3).toLocaleTimeString("ko-KR", { hour12: false });
    } catch (e) {
      return "";
    }
  }
  function ProcessFlowDiagram({ currentStep, running, phaseElapsed, stepTimings }) {
    const steps = FLOW_STEPS;
    const n = steps.length;
    const NODE_W = 120, NODE_H = 56, GAP = 40, PAD_X = 16, PAD_Y = 14;
    const ARROW_H = 8;
    const vbW = PAD_X * 2 + n * NODE_W + (n - 1) * GAP;
    const vbH = PAD_Y * 2 + NODE_H;
    const cy = PAD_Y + NODE_H / 2;
    const nodeX = (i) => PAD_X + i * (NODE_W + GAP);
    return /* @__PURE__ */ React.createElement("div", { className: "stom-flow-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${vbW} ${vbH}`,
        preserveAspectRatio: "xMidYMid meet",
        width: "100%",
        height: vbH,
        style: { minWidth: vbW, display: "block" },
        role: "img",
        "aria-label": "\uC9C4\uD654 \uB8E8\uD504 \uD504\uB85C\uC138\uC2A4 \uD50C\uB85C\uC6B0"
      },
      /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("filter", { id: "stom-flow-glow", x: "-40%", y: "-40%", width: "180%", height: "180%" }, /* @__PURE__ */ React.createElement("feGaussianBlur", { in: "SourceAlpha", stdDeviation: "2.5", result: "blur" }), /* @__PURE__ */ React.createElement("feMerge", null, /* @__PURE__ */ React.createElement("feMergeNode", { in: "blur" }), /* @__PURE__ */ React.createElement("feMergeNode", { in: "SourceGraphic" })))),
      steps.slice(0, n - 1).map((_, i) => {
        const x1 = nodeX(i) + NODE_W;
        const x2 = nodeX(i + 1);
        const tip = x2 - 2;
        const lineEnd = tip - ARROW_H;
        const lit = typeof currentStep === "number" && currentStep >= i + 1;
        const cls = `stom-flow-arrow${lit ? " lit" : ""}`;
        return /* @__PURE__ */ React.createElement("g", { key: `arrow-${i}` }, /* @__PURE__ */ React.createElement("line", { className: cls, x1, y1: cy, x2: lineEnd, y2: cy }), /* @__PURE__ */ React.createElement(
          "polygon",
          {
            className: cls,
            points: `${lineEnd},${cy - ARROW_H / 2} ${tip},${cy} ${lineEnd},${cy + ARROW_H / 2}`,
            fill: "currentColor",
            stroke: "none",
            style: { color: lit ? "var(--teal)" : "var(--line-2)" }
          }
        ));
      }),
      steps.map((step, i) => {
        const isActive = i === currentStep;
        const isDone = typeof currentStep === "number" && currentStep > i;
        const statusCls = isDone ? "stom-flow-node-done" : isActive ? "stom-flow-node-active" : "stom-flow-node-pend";
        const doneSec = stepTimings ? stepTimings[step.timingKey] : void 0;
        let subText = step.sub;
        if (isActive && running && phaseElapsed != null) {
          subText = `\uACBD\uACFC ${fmtElapsedSec(phaseElapsed)}`;
        } else if (!isActive && typeof doneSec === "number" && doneSec >= 0) {
          subText = fmtElapsedSec(doneSec);
        }
        const x = nodeX(i);
        const labelX = x + NODE_W / 2;
        return /* @__PURE__ */ React.createElement("g", { key: `node-${i}` }, /* @__PURE__ */ React.createElement(
          "rect",
          {
            className: statusCls,
            x,
            y: PAD_Y,
            width: NODE_W,
            height: NODE_H,
            rx: 10,
            ry: 10,
            strokeWidth: isActive ? 2.5 : 1.5,
            filter: isActive ? "url(#stom-flow-glow)" : void 0
          }
        ), /* @__PURE__ */ React.createElement("text", { className: "stom-flow-label", x: labelX, y: cy - 2, textAnchor: "middle" }, step.label), /* @__PURE__ */ React.createElement("text", { className: "stom-flow-sub", x: labelX, y: cy + 14, textAnchor: "middle" }, subText));
      })
    ));
  }
  function ProcessFlowPanel({ state }) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k;
    const rawStep = (_a = state == null ? void 0 : state.latest) == null ? void 0 : _a.current_step;
    const currentStep = rawStep !== void 0 && rawStep !== null ? rawStep : phaseIndex((_b = state == null ? void 0 : state.latest) == null ? void 0 : _b.phase);
    const logs = (_d = (_c = state == null ? void 0 : state.latest) == null ? void 0 : _c.recent_logs) != null ? _d : [];
    const running = (state == null ? void 0 : state.status) === "running" || (state == null ? void 0 : state.status) === "stopping";
    const phaseStartedAt = (_f = (_e = state == null ? void 0 : state.latest) == null ? void 0 : _e.phase_started_at) != null ? _f : 0;
    const genStartedAt = (_h = (_g = state == null ? void 0 : state.latest) == null ? void 0 : _g.gen_started_at) != null ? _h : 0;
    const stepTimings = (_j = (_i = state == null ? void 0 : state.latest) == null ? void 0 : _i.step_timings) != null ? _j : {};
    const [nowSec, setNowSec] = useState_ph(() => Date.now() / 1e3);
    useEffect_ph(() => {
      if (!running) return;
      const id = setInterval(() => setNowSec(Date.now() / 1e3), 1e3);
      return () => clearInterval(id);
    }, [running]);
    const phaseElapsed = running && phaseStartedAt > 0 ? nowSec - phaseStartedAt : null;
    const genElapsedLive = running && genStartedAt > 0 ? nowSec - genStartedAt : null;
    const completedAt = !running && (state == null ? void 0 : state.status) === "complete" ? (_k = state == null ? void 0 : state.updated_at) != null ? _k : 0 : 0;
    const genElapsedDone = completedAt > 0 && genStartedAt > 0 ? completedAt - genStartedAt : null;
    const completionClock = fmtClockFromEpoch(completedAt);
    const totalSteps = FLOW_STEPS.length;
    const stepsDone = typeof currentStep === "number" && currentStep >= 0 ? Math.min(totalSteps, currentStep + 1) : 0;
    const progressPct = stepsDone / totalSteps * 100;
    const logRef = useRef_ph(null);
    useEffect_ph(() => {
      if (logRef.current) {
        logRef.current.scrollTop = logRef.current.scrollHeight;
      }
    }, [logs.length]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { padding: "12px 14px" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd", style: { marginBottom: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uD504\uB85C\uC138\uC2A4 \uD50C\uB85C\uC6B0"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" } }, genElapsedLive != null && /* @__PURE__ */ React.createElement("span", { "data-tip": "\uD604\uC7AC \uC138\uB300 \uACBD\uACFC \uC2DC\uAC04 (\uC138\uB300 \uC2DC\uC791 \uC774\uD6C4)" }, "\uC138\uB300 \uACBD\uACFC ", fmtElapsedSec(genElapsedLive)), genElapsedLive == null && genElapsedDone != null && /* @__PURE__ */ React.createElement("span", { "data-tip": "\uB9C8\uC9C0\uB9C9 \uC138\uB300 \uC18C\uC694 \uC2DC\uAC04" }, "\uC138\uB300 \uC18C\uC694 ", fmtElapsedSec(genElapsedDone), completionClock && ` \xB7 \uC644\uB8CC ${completionClock}`), stepsDone > 0 && /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 8 } }, "\xB7 ", stepsDone, "/", totalSteps, " \uB2E8\uACC4"))), /* @__PURE__ */ React.createElement("div", { className: "process-progress-track", style: {
      height: 3,
      background: "var(--line-2)",
      borderRadius: 2,
      marginBottom: 8,
      overflow: "hidden"
    } }, /* @__PURE__ */ React.createElement("div", { style: {
      width: `${progressPct}%`,
      height: "100%",
      background: "var(--amber)",
      transition: "width .3s ease"
    } })), /* @__PURE__ */ React.createElement(
      ProcessFlowDiagram,
      {
        currentStep,
        running,
        phaseElapsed,
        stepTimings
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "process-log-pane", ref: logRef }, logs.length === 0 ? /* @__PURE__ */ React.createElement("span", { className: "process-log-empty" }, "\uB85C\uADF8 \uB300\uAE30\uC911\u2026") : logs.map((line, i) => /* @__PURE__ */ React.createElement("div", { key: i }, line))));
  }
  Object.assign(window, {
    PhaseTimeline,
    PhaseDetailPanel,
    ProcessFlowPanel,
    ProcessFlowDiagram,
    GenerationView,
    BacktestingView,
    ScoringView,
    AutopsyView,
    LiveBacktestChartInline,
    DemoBadge,
    LivePending,
    // R8 — phase 매핑 순수 함수/맵 노출(영/한 정규화). 정적·단위 검증 가능.
    phaseIndex,
    PHASES,
    LIVE_PHASE_INDEX,
    // #64 — 진행시간 포맷 순수 함수 + 단계 메타 노출(정적·단위 검증 가능).
    fmtElapsedSec,
    fmtClockFromEpoch,
    FLOW_STEPS
  });

  // ../frontend/engine.jsx
  var { useState: useState_e, useMemo: useMemo_e, useRef: useRef_e } = React;
  function fmtElapsed(ms) {
    if (!ms || ms < 0) return "0.0s";
    if (ms < 6e4) return (ms / 1e3).toFixed(1) + "s";
    const m = Math.floor(ms / 6e4);
    const s = Math.floor(ms % 6e4 / 1e3);
    return `${m}m ${s.toString().padStart(2, "0")}s`;
  }
  function fmtEpoch(epochSec) {
    if (typeof epochSec !== "number" || !Number.isFinite(epochSec) || epochSec <= 0) return "-";
    return new Date(epochSec * 1e3).toLocaleString("ko-KR", { hour12: false });
  }
  function GaugeRow({ label, value, unit, warn, danger }) {
    const hasValue = typeof value === "number" && Number.isFinite(value);
    const pct = hasValue ? Math.max(0, Math.min(100, value)) : 0;
    let fillClass = "stom-gauge-fill";
    if (hasValue && typeof danger === "number" && value >= danger) fillClass += " danger";
    else if (hasValue && typeof warn === "number" && value >= warn) fillClass += " warn";
    const valText = hasValue ? `${value.toFixed(1)}${unit || ""}` : "\u2014";
    return /* @__PURE__ */ React.createElement("div", { className: "stom-gauge-row" }, /* @__PURE__ */ React.createElement("div", { className: "stom-gauge-label" }, label), /* @__PURE__ */ React.createElement("div", { className: "stom-gauge" }, /* @__PURE__ */ React.createElement("div", { className: fillClass, style: { width: `${pct}%` } })), /* @__PURE__ */ React.createElement("div", { className: "stom-gauge-val" }, valText));
  }
  function EnginePanel({ state, wsStatus }) {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i, _j, _k, _l, _m, _n, _o, _p, _q, _r, _s, _t, _u, _v, _w, _x, _y, _z, _A, _B, _C, _D, _E, _F, _G, _H, _I, _J, _K;
    const latest = state.latest || {};
    const progressInfo = latest.backtest_progress || {};
    const engineState = latest.engine_state || {};
    const e = state.engine || engineState || {};
    const running = state.status === "running" || state.status === "stopping";
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const liveNoEngine = !isDemo && !state.engine && !latest.engine_state;
    const cpu = (_a = e.cpu_pct) != null ? _a : 0;
    const mem = (_b = e.mem_mb) != null ? _b : 0;
    const memCap = e.mem_cap_mb || 8192;
    const memPct = Math.min(100, mem / memCap * 100);
    const cpuGauge = typeof e.cpu_pct === "number" ? e.cpu_pct : null;
    const memPctGauge = typeof e.mem_mb === "number" ? memPct : null;
    const workers = (_c = e.workers) != null ? _c : 0;
    const workersActive = (_d = e.workers_active) != null ? _d : 0;
    const tput = (_e = e.throughput) != null ? _e : 0;
    const progress = typeof progressInfo.percent === "number" ? Math.max(0, Math.min(1, progressInfo.percent / 100)) : (_f = e.progress) != null ? _f : 0;
    const maxGens = progressInfo.max_generations || state.max_generations || 0;
    const currentGen = typeof progressInfo.current_gen === "number" ? progressInfo.current_gen : state.current_gen || 0;
    const overallPct = typeof progressInfo.percent === "number" ? Math.max(0, Math.min(100, progressInfo.percent)) : maxGens > 0 ? Math.min(100, currentGen / maxGens * 100) : Math.min(100, progress * 100);
    const remainingGens = Math.max(0, maxGens - currentGen);
    const elapsedMs = typeof progressInfo.elapsed_sec === "number" ? progressInfo.elapsed_sec * 1e3 : (_g = e.elapsed_ms) != null ? _g : 0;
    const etaMs = typeof progressInfo.eta_sec === "number" ? progressInfo.eta_sec * 1e3 : (_h = e.eta_ms) != null ? _h : 0;
    const activeConfig = state.active_config || engineState.active_config || {};
    const progressSource = progressInfo.progress_source || progressInfo.source || "counter unavailable";
    const doneUnits = (_j = (_i = progressInfo.done_units) != null ? _i : progressInfo.current_gen) != null ? _j : currentGen;
    const totalUnits = (_l = (_k = progressInfo.total_units) != null ? _k : progressInfo.max_generations) != null ? _l : maxGens;
    const engineMode = engineState.bt_engine_mode || activeConfig.bt_engine_mode || "-";
    const btTimeframe = state.bt_timeframe || progressInfo.timeframe || engineState.bt_timeframe || activeConfig.bt_timeframe || "min";
    const cpuCount = (_n = (_m = engineState.cpu_count) != null ? _m : e.cpu_count) != null ? _n : "-";
    const effectiveEngineCount = (_q = (_p = (_o = engineState.effective_engine_count) != null ? _o : e.effective_engine_count) != null ? _p : workers) != null ? _q : "-";
    const evolutionMode = activeConfig.evolution_mode || engineState.evolution_mode || "-";
    const genModeLabel = evolutionMode === "ga" ? "GA population generation" : "gen = generation";
    const recentLogs = Array.isArray(engineState.recent_logs) ? engineState.recent_logs : [];
    const timeoutSec = (_t = (_s = (_r = progressInfo.timeout_sec) != null ? _r : engineState.timeout_sec) != null ? _s : activeConfig.bt_warm_run_timeout) != null ? _t : activeConfig.bt_timeout;
    const timeoutMs = typeof timeoutSec === "number" ? timeoutSec * 1e3 : 0;
    const timeoutDeadline = (_u = progressInfo.timeout_deadline_epoch) != null ? _u : engineState.timeout_deadline_epoch;
    const periodStart = (_w = (_v = engineState.bt_full_start) != null ? _v : activeConfig.bt_full_start) != null ? _w : "-";
    const periodEnd = (_y = (_x = engineState.bt_full_end) != null ? _x : activeConfig.bt_full_end) != null ? _y : "-";
    const windowStart = (_A = (_z = engineState.bt_universe_start_time) != null ? _z : activeConfig.bt_universe_start_time) != null ? _A : "-";
    const windowEnd = (_C = (_B = engineState.bt_universe_end_time) != null ? _B : activeConfig.bt_universe_end_time) != null ? _C : "-";
    const warmTimeout = (_E = (_D = engineState.bt_warm_run_timeout) != null ? _D : activeConfig.bt_warm_run_timeout) != null ? _E : "-";
    const coldTimeout = (_G = (_F = engineState.bt_timeout) != null ? _F : activeConfig.bt_timeout) != null ? _G : "-";
    const pips = [];
    for (let i = 0; i < workers; i++) {
      pips.push(i < workersActive ? "active" : "idle");
    }
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: running ? "var(--amber)" : "var(--ink-3)" } }), "\uBC31\uD14C\uC2A4\uD2B8 \uC5D4\uC9C4 \u2014 Runtime", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(DemoBadge, null)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "tag-slim" }, btTimeframe), /* @__PURE__ */ React.createElement("span", { className: "tag-slim" }, "chunks ", (_H = e.chunks_done) != null ? _H : 0, "/", (_I = e.chunks_total) != null ? _I : 0))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "engine-summary-strip" }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Overall Progress"), " ", overallPct.toFixed(1), "%"), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Elapsed"), " ", fmtElapsed(elapsedMs)), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Remaining"), " ", remainingGens, " gen"), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "ETA"), " ", fmtElapsed(etaMs)), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Timeout"), " ", fmtElapsed(timeoutMs)), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Deadline"), " ", fmtEpoch(timeoutDeadline)), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Progress Source"), " ", progressSource), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Units"), " ", doneUnits, "/", totalUnits)), /* @__PURE__ */ React.createElement("div", { className: "engine-config-strip" }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Engine Config")), /* @__PURE__ */ React.createElement("span", null, "min/tick=", btTimeframe), /* @__PURE__ */ React.createElement("span", null, "mode=", engineMode), /* @__PURE__ */ React.createElement("span", null, "cpu=", cpuCount), /* @__PURE__ */ React.createElement("span", null, "engines=", effectiveEngineCount), /* @__PURE__ */ React.createElement("span", null, genModeLabel), /* @__PURE__ */ React.createElement("span", null, "Period ", periodStart, "~", periodEnd), /* @__PURE__ */ React.createElement("span", null, "bt_full_start=", periodStart), /* @__PURE__ */ React.createElement("span", null, "bt_full_end=", periodEnd), /* @__PURE__ */ React.createElement("span", null, "window=", windowStart, "~", windowEnd), /* @__PURE__ */ React.createElement("span", null, "bt_timeout=", coldTimeout), /* @__PURE__ */ React.createElement("span", null, "bt_warm_run_timeout=", warmTimeout)), /* @__PURE__ */ React.createElement("div", { className: "engine-log-strip" }, /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("b", null, "Recent Logs")), /* @__PURE__ */ React.createElement("span", null, progressInfo.phase || latest.phase || state.status || "-"), /* @__PURE__ */ React.createElement("span", null, progressInfo.message || latest.last_checkpoint || e.current_symbol || "waiting for engine event"), recentLogs.slice(-2).map((line, i) => /* @__PURE__ */ React.createElement("span", { key: i }, line))), liveNoEngine && typeof window.LivePending === "function" ? /* @__PURE__ */ React.createElement(LivePending, { note: "\uC5D4\uC9C4 \uB7F0\uD0C0\uC784 \uBA54\uD2B8\uB9AD(CPU/\uBA54\uBAA8\uB9AC/\uC6CC\uCEE4)\uC740 backend\uAC00 \uC544\uC9C1 \uBC1C\uD589\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4." }) : /* @__PURE__ */ React.createElement("div", { className: "engine-grid" }, isDemo && /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "mono",
        title: "\uC774 \uB7F0\uD0C0\uC784 \uAC8C\uC774\uC9C0\uB294 \uB370\uBAA8 \uC2DC\uBBAC\uB808\uC774\uC158 \uAC12\uC785\uB2C8\uB2E4 \u2014 \uC2E4\uC81C \uC5D4\uC9C4\uC774 \uBC1C\uD589\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4.",
        style: {
          gridColumn: "1 / -1",
          fontSize: 10.5,
          color: "var(--ink-3)",
          padding: "4px 8px",
          border: "1px dashed var(--line-1)",
          borderRadius: 4
        }
      },
      "DEMO \uC2DC\uBBAC\uAC12 \u2014 CPU\xB7\uBA54\uBAA8\uB9AC\xB7\uC6CC\uCEE4\xB7\uCC98\uB9AC\uB7C9 \uAC8C\uC774\uC9C0\uB294 \uB370\uBAA8 \uC2DC\uBBAC\uB808\uC774\uC158 \uAC12\uC785\uB2C8\uB2E4(backend \uBBF8\uBC1C\uD589)"
    ), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "CPU \uC0AC\uC6A9\uB960"), /* @__PURE__ */ React.createElement("div", { className: "val tnum" }, cpu.toFixed(1), /* @__PURE__ */ React.createElement("span", { className: "unit" }, "%")), /* @__PURE__ */ React.createElement(GaugeRow, { label: "CPU", value: cpuGauge, unit: "%", warn: 70, danger: 90 })), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uBA54\uBAA8\uB9AC"), /* @__PURE__ */ React.createElement("div", { className: "val tnum" }, mem >= 1024 ? (mem / 1024).toFixed(2) : mem, /* @__PURE__ */ React.createElement("span", { className: "unit" }, mem >= 1024 ? "GB" : "MB")), /* @__PURE__ */ React.createElement(GaugeRow, { label: "Mem %", value: memPctGauge, unit: "%", warn: 75, danger: 90 }), /* @__PURE__ */ React.createElement("div", { className: "sub" }, "/ ", (memCap / 1024).toFixed(1), " GB cap")), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uBCD1\uB82C \uC6CC\uCEE4"), /* @__PURE__ */ React.createElement("div", { className: "val tnum" }, workersActive, /* @__PURE__ */ React.createElement("span", { className: "unit" }, "/ ", workers)), /* @__PURE__ */ React.createElement("div", { className: "workers-row" }, pips.map((s, i) => /* @__PURE__ */ React.createElement("span", { key: i, className: `worker-pip ${s}` })))), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uCC98\uB9AC\uB7C9"), /* @__PURE__ */ React.createElement("div", { className: "val tnum" }, tput >= 1e3 ? (tput / 1e3).toFixed(1) : tput, /* @__PURE__ */ React.createElement("span", { className: "unit" }, tput >= 1e3 ? "k/s" : "candles/s")), /* @__PURE__ */ React.createElement("div", { className: "sub" }, tput.toLocaleString("ko-KR"), " candles/sec")), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uACBD\uACFC \uC2DC\uAC04"), /* @__PURE__ */ React.createElement("div", { className: "val tnum mono", style: { fontSize: 15 } }, fmtElapsed(elapsedMs)), /* @__PURE__ */ React.createElement("div", { className: "sub" }, "ETA ", fmtElapsed(etaMs))), /* @__PURE__ */ React.createElement("div", { className: "engine-cell", style: { gridColumn: "span 2" } }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uCC98\uB9AC\uC911 \uC885\uBAA9"), /* @__PURE__ */ React.createElement("div", { className: "val mono", style: { fontSize: 14 } }, e.current_symbol || "\u2014"), /* @__PURE__ */ React.createElement("div", { className: "sub" }, "window ", ((_J = e.current_window) == null ? void 0 : _J.from) || "\u2014", " \u2192 ", ((_K = e.current_window) == null ? void 0 : _K.to) || "\u2014")), /* @__PURE__ */ React.createElement("div", { className: "engine-cell" }, /* @__PURE__ */ React.createElement("div", { className: "lbl" }, "\uC138\uB300 \uBC31\uD14C \uC9C4\uD589"), /* @__PURE__ */ React.createElement("div", { className: "val tnum" }, (progress * 100).toFixed(0), /* @__PURE__ */ React.createElement("span", { className: "unit" }, "%"), /* @__PURE__ */ React.createElement("span", { className: "unit" }, " (\uC138\uB300 \uB0B4)")), /* @__PURE__ */ React.createElement(GaugeRow, { label: "\uC804\uCCB4", value: overallPct, unit: "%" })))));
  }
  function _liveChartGeom2({ equity, drawdown, baseline, W, H, padL, padR, padT, padB, xMax }) {
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const eqVals = equity.map((p) => p.value);
    const maxEq = Math.max(baseline * 1.02, ...eqVals);
    const minEq = Math.min(baseline * 0.98, ...eqVals);
    const ddMax = Math.max(2, ...drawdown.map((p) => p.value_pct), 8);
    const x = (t) => padL + t / xMax * innerW;
    const y = (v) => padT + innerH - (v - minEq) / Math.max(1, maxEq - minEq) * innerH;
    const yDD = (v) => padT + v / ddMax * innerH;
    const eqPath = equity.length ? equity.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ") : "";
    let eqAreaPath = "";
    if (equity.length >= 2) {
      const by = y(baseline);
      eqAreaPath = `M ${x(equity[0].t).toFixed(1)} ${by.toFixed(1)} ` + equity.map((p) => `L ${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ") + ` L ${x(equity[equity.length - 1].t).toFixed(1)} ${by.toFixed(1)} Z`;
    }
    let ddAreaPath = "";
    if (drawdown.length >= 2) {
      ddAreaPath = `M ${x(drawdown[0].t).toFixed(1)} ${padT.toFixed(1)} ` + drawdown.map((p) => `L ${x(p.t).toFixed(1)} ${yDD(p.value_pct).toFixed(1)}`).join(" ") + ` L ${x(drawdown[drawdown.length - 1].t).toFixed(1)} ${padT.toFixed(1)} Z`;
    }
    return { maxEq, minEq, ddMax, x, y, yDD, eqPath, eqAreaPath, ddAreaPath };
  }
  function LiveBacktestChart({ state }) {
    var _a, _b, _c, _d, _e;
    const equity = ((_a = state.current_run) == null ? void 0 : _a.equity) || [];
    const drawdown = ((_b = state.current_run) == null ? void 0 : _b.drawdown) || [];
    const trades = ((_c = state.current_run) == null ? void 0 : _c.trades) || [];
    const baseline = 1e7;
    const W = 880, H = 240;
    const padL = 60, padR = 60, padT = 14, padB = 26;
    const innerH = H - padT - padB;
    const xMax = Math.max(60, equity.length, ...equity[equity.length - 1] ? [equity[equity.length - 1].t] : [60]);
    const { maxEq, minEq, ddMax, x, y, yDD, eqPath, eqAreaPath, ddAreaPath } = useMemo_e(
      () => _liveChartGeom2({ equity, drawdown, baseline, W, H, padL, padR, padT, padB, xMax }),
      [equity, drawdown, xMax]
    );
    const last = equity[equity.length - 1];
    const lastPnl = last ? last.value - baseline : 0;
    const lastDD = (_e = (_d = drawdown[drawdown.length - 1]) == null ? void 0 : _d.value_pct) != null ? _e : 0;
    const lastPnlPct = lastPnl / baseline * 100;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uD604\uC7AC \uC138\uB300 \uBC31\uD14C\uC2A4\uD2B8 \u2014 Equity & Drawdown"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { style: {
      fontSize: 13.5,
      /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */
      color: "var(--ink-2)",
      fontFamily: "var(--mono)"
    } }, /* @__PURE__ */ React.createElement("span", { style: { color: lastPnl >= 0 ? "var(--teal)" : "var(--red)" } }, lastPnl >= 0 ? "+" : "\u2212", Math.abs(lastPnl).toLocaleString("ko-KR"), "\uC6D0"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, " (", lastPnlPct >= 0 ? "+" : "", lastPnlPct.toFixed(2), "%)")), /* @__PURE__ */ React.createElement("span", { style: {
      fontSize: 13.5,
      /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */
      color: "var(--red)",
      fontFamily: "var(--mono)"
    } }, "DD ", lastDD.toFixed(2), "%"), /* @__PURE__ */ React.createElement("span", { style: {
      fontSize: 13.5,
      /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */
      color: "var(--ink-2)",
      fontFamily: "var(--mono)"
    } }, "trades ", trades.length))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "live-chart-wrap" }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("linearGradient", { id: "eq-grad", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "var(--teal)", stopOpacity: "0.5" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "var(--teal)", stopOpacity: "0" })), /* @__PURE__ */ React.createElement("linearGradient", { id: "dd-grad", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "var(--red)", stopOpacity: "0.20" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "var(--red)", stopOpacity: "0" }))), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: padT + innerH,
        y2: padT + innerH,
        stroke: "var(--line-2)"
      }
    ), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)" }), /* @__PURE__ */ React.createElement("line", { x1: W - padR, x2: W - padR, y1: padT, y2: padT + innerH, stroke: "var(--line-2)" }), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: y(baseline),
        y2: y(baseline),
        className: "zero-line"
      }
    ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: y(baseline) + 3, textAnchor: "end" }, (baseline / 1e6).toFixed(1), "M"), [0.25, 0.5, 0.75].map((t, i) => {
      const v = minEq + (maxEq - minEq) * t;
      return /* @__PURE__ */ React.createElement("g", { key: `yl${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(v), y2: y(v), className: "chart-grid-line" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: y(v) + 3, textAnchor: "end" }, (v / 1e6).toFixed(2), "M"));
    }), [0.25, 0.5, 0.75, 1].map((t, i) => {
      const v = ddMax * t;
      return /* @__PURE__ */ React.createElement(
        "text",
        {
          key: `yr${i}`,
          className: "chart-axis-text",
          x: W - padR + 6,
          y: yDD(v) + 3,
          fill: "var(--red)",
          opacity: "0.7"
        },
        "\u2212",
        v.toFixed(1),
        "%"
      );
    }), drawdown.length > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: ddAreaPath, className: "dd-area" })), equity.length > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: eqAreaPath, className: "eq-area" }), /* @__PURE__ */ React.createElement("path", { d: eqPath, className: `eq-line ${lastPnl < 0 ? "eq-line-neg" : ""}` })), trades.map((tr, i) => /* @__PURE__ */ React.createElement(
      "circle",
      {
        key: i,
        cx: x(tr.t),
        cy: y(tr.price),
        r: "2.5",
        className: tr.side === "buy" ? "trade-marker-buy" : "trade-marker-sell",
        opacity: "0.85"
      }
    )), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL, y: H - 8 }, "0m"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: (padL + W - padR) / 2, y: H - 8, textAnchor: "middle" }, Math.round(xMax / 2), "m"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR, y: H - 8, textAnchor: "end" }, xMax, "m"), /* @__PURE__ */ React.createElement("g", { transform: `translate(${padL + 8}, ${padT + 12})` }, /* @__PURE__ */ React.createElement("rect", { x: "0", y: "-8", width: "9", height: "9", fill: "var(--teal)", rx: "1" }), /* @__PURE__ */ React.createElement("text", { x: "14", y: "0", className: "chart-axis-text", fill: "var(--ink-1)" }, "\uC790\uBCF8"), /* @__PURE__ */ React.createElement("rect", { x: "60", y: "-8", width: "9", height: "9", fill: "var(--red)", opacity: "0.6", rx: "1" }), /* @__PURE__ */ React.createElement("text", { x: "74", y: "0", className: "chart-axis-text", fill: "var(--ink-1)" }, "\uB099\uD3ED"), /* @__PURE__ */ React.createElement("circle", { cx: "113", cy: "-4", r: "3", className: "trade-marker-buy" }), /* @__PURE__ */ React.createElement("text", { x: "120", y: "0", className: "chart-axis-text", fill: "var(--ink-1)" }, "\uB9E4\uC218"), /* @__PURE__ */ React.createElement("circle", { cx: "148", cy: "-4", r: "3", className: "trade-marker-sell" }), /* @__PURE__ */ React.createElement("text", { x: "155", y: "0", className: "chart-axis-text", fill: "var(--ink-1)" }, "\uB9E4\uB3C4"))), equity.length === 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)",
      pointerEvents: "none"
    } }, "\uBC31\uD14C\uC2A4\uD2B8\uAC00 \uC2DC\uC791\uB418\uBA74 \uC790\uBCF8\uACE1\uC120\uC774 \uC2E4\uC2DC\uAC04\uC73C\uB85C \uCC44\uC6CC\uC9D1\uB2C8\uB2E4"))));
  }
  Object.assign(window, { EnginePanel, LiveBacktestChart, fmtElapsed, _liveChartGeom: _liveChartGeom2 });

  // ../frontend/chart.jsx
  var { useMemo: useMemo_c, useState: useState_c, useRef: useRef_c } = React;
  var _axisTicks = window._axisTicks;
  function MetricHelpStrip({ items }) {
    return /* @__PURE__ */ React.createElement("div", { className: "metric-help-strip" }, (items || []).map((item, i) => /* @__PURE__ */ React.createElement("span", { key: i }, item)));
  }
  function FitnessChart({ state, target = 1 }) {
    const gens = state.generations || [];
    const bestSoFar = useMemo_c(() => {
      let bs = 0;
      return gens.map((g) => {
        bs = Math.max(bs, g.graded_score || 0);
        return bs;
      });
    }, [gens]);
    const W = 880, H = 320;
    const padL = 44, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const xMax = Math.max(state.max_generations, 8);
    const yMax = Math.max(1.15, ...gens.map((g) => g.graded_score || 0).concat([target + 0.1]));
    const x = (g) => padL + (g - 0.5) / xMax * innerW;
    const y = (v) => padT + innerH - v / yMax * innerH;
    const yTicks = [];
    const step = yMax > 1.5 ? 0.5 : 0.2;
    for (let v = 0; v <= yMax + 1e-9; v += step) yTicks.push(+v.toFixed(2));
    const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
    const xTicks = [];
    for (let g = 1; g <= xMax; g++) {
      if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);
    }
    const linePath = useMemo_c(() => {
      if (!gens.length) return "";
      return gens.map(
        (g, i) => `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${y(g.graded_score || 0).toFixed(2)}`
      ).join(" ");
    }, [gens, xMax, yMax]);
    const areaPath = useMemo_c(() => {
      if (!gens.length) return "";
      const start = `M ${x(gens[0].gen_no).toFixed(2)} ${y(0).toFixed(2)}`;
      const mid = gens.map((g) => `L ${x(g.gen_no).toFixed(2)} ${y(g.graded_score || 0).toFixed(2)}`).join(" ");
      const end = `L ${x(gens[gens.length - 1].gen_no).toFixed(2)} ${y(0).toFixed(2)} Z`;
      return `${start} ${mid} ${end}`;
    }, [gens, xMax, yMax]);
    const bestPath = useMemo_c(() => {
      if (!gens.length) return "";
      return gens.map(
        (g, i) => `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${y(bestSoFar[i]).toFixed(2)}`
      ).join(" ");
    }, [gens, bestSoFar, xMax, yMax]);
    const [hover, setHover] = useState_c(null);
    const svgRef = useRef_c(null);
    const onMove = (e) => {
      if (!gens.length) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      let best = null, bestDist = Infinity;
      for (const g of gens) {
        const gx = x(g.gen_no);
        const d = Math.abs(gx - px);
        if (d < bestDist) {
          bestDist = d;
          best = g;
        }
      }
      if (best && bestDist < 40) setHover(best);
      else setHover(null);
    };
    const onLeave = () => setHover(null);
    const latest = gens[gens.length - 1];
    const peak = gens.reduce((a, b) => b.graded_score > ((a == null ? void 0 : a.graded_score) || 0) ? b : a, null);
    const gatePassedCount = gens.filter((g) => g.gate_passed).length;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uC801\uD569\uB3C4 \uCD94\uC774 \u2014 Fitness Trajectory", /* @__PURE__ */ React.createElement(
      "span",
      {
        "data-tip": "\uC801\uD569\uB3C4(graded_score) = \uC218\uC775\xB7MDD\xB7\uAC70\uB798\uC218 \uAC8C\uC774\uD2B8\uB97C \uD1B5\uACFC\uD55C \uC815\uB3C4\uB97C 0~100\uC73C\uB85C \uB4F1\uAE09\uD654\uD55C \uC810\uC218. \uC138\uB300\uAC00 \uC9C4\uD589\uB418\uBA70 \uC810\uC218\uAC00 \uC6B0\uC0C1\uD5A5\uD558\uBA74 \uC9C4\uD654\uAC00 \uC791\uB3D9 \uC911\uC774\uB77C\uB294 \uB73B. \uC810\uC120 = \uC9C0\uAE08\uAE4C\uC9C0\uC758 \uCD5C\uACE0\uC810, \uB9C1 = \uAC8C\uC774\uD2B8 \uD1B5\uACFC \uC138\uB300.",
        style: {
          marginLeft: 6,
          fontSize: 10,
          color: "var(--ink-3)",
          border: "1px solid var(--line-2)",
          borderRadius: "50%",
          width: 15,
          height: 15,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "help"
        }
      },
      "?"
    )), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "graded_score" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--violet)", label: "best-so-far", dashed: true }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--blue)", label: "gate-passed", filled: "ring" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC2E0 \uC810\uC218",
        value: latest ? fmtScore(latest.graded_score) : "\u2014",
        color: latest && latest.graded_score >= target ? "var(--teal)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uACE0 \uC810\uC218",
        value: peak ? fmtScore(peak.graded_score) : "\u2014",
        sub: peak ? `gen_${peak.gen_no}` : ""
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uAC8C\uC774\uD2B8 \uD1B5\uACFC",
        value: `${gatePassedCount} / ${gens.length}`,
        color: gatePassedCount > 0 ? "var(--teal)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(Mini, { label: "\uBAA9\uD45C", value: target.toFixed(3), sub: "target_score" })), /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "graded_score = weighted fitness",
      "hard gate = target score plus MDD/trade rules",
      "Calmar = return divided by MDD",
      "uptrend_r2 = cumulative equity trend fit"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: onLeave
      },
      /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("linearGradient", { id: "chart-area-grad", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "#4cd6b3", stopOpacity: "0.45" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "#4cd6b3", stopOpacity: "0" }))),
      yTicks.map((t, i) => /* @__PURE__ */ React.createElement("g", { key: `y${i}` }, /* @__PURE__ */ React.createElement(
        "line",
        {
          className: "chart-grid-line",
          x1: padL,
          x2: W - padR,
          y1: y(t),
          y2: y(t)
        }
      ), /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: y(t) + 3,
          textAnchor: "end"
        },
        t.toFixed(t < 10 ? 2 : 0)
      ))),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: y(target),
          y2: y(target),
          stroke: "rgba(106,166,255,0.4)",
          strokeWidth: "1",
          strokeDasharray: "6 4"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: W - padR - 4,
          y: y(target) - 4,
          textAnchor: "end",
          fill: "var(--blue)"
        },
        "target ",
        target.toFixed(2)
      ),
      xTicks.map((g, i) => /* @__PURE__ */ React.createElement(
        "text",
        {
          key: `x${i}`,
          className: "chart-axis-text",
          x: x(g),
          y: H - 10,
          textAnchor: "middle"
        },
        "gen_",
        g
      )),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: padT + innerH,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: padL,
          y1: padT,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      gens.length > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: areaPath, className: "chart-area" }), /* @__PURE__ */ React.createElement("path", { d: linePath, className: "chart-line" }), /* @__PURE__ */ React.createElement("path", { d: bestPath, className: "chart-best-line" })),
      gens.map((g, i) => {
        const cx = x(g.gen_no), cy = y(g.graded_score || 0);
        if (g.gate_passed) {
          return /* @__PURE__ */ React.createElement("g", { key: i }, /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "7", fill: "rgba(165,148,255,0.16)" }), /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "4", className: "chart-pt-gate" }));
        }
        if (g.status === "error") {
          return /* @__PURE__ */ React.createElement("g", { key: i }, /* @__PURE__ */ React.createElement("line", { x1: cx - 3, y1: cy - 3, x2: cx + 3, y2: cy + 3, stroke: "var(--red)", strokeWidth: "1.4" }), /* @__PURE__ */ React.createElement("line", { x1: cx + 3, y1: cy - 3, x2: cx - 3, y2: cy + 3, stroke: "var(--red)", strokeWidth: "1.4" }));
        }
        return /* @__PURE__ */ React.createElement("circle", { key: i, cx, cy, r: "2.6", className: "chart-pt" });
      }),
      hover && (() => {
        const cx = x(hover.gen_no), cy = y(hover.graded_score || 0);
        return /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: cx,
            x2: cx,
            y1: padT,
            y2: padT + innerH,
            stroke: "rgba(255,255,255,0.12)",
            strokeWidth: "1"
          }
        ), /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "6", fill: "none", stroke: "var(--ink-0)", strokeWidth: "1" }));
      })()
    ), hover && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 200,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 } }, "gen_", String(hover.gen_no).padStart(2, "0")), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC810\uC218"), /* @__PURE__ */ React.createElement("span", { style: { color: hover.graded_score >= target ? "var(--teal)" : "var(--ink-0)" } }, fmtScore(hover.graded_score)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAC8C\uC774\uD2B8"), /* @__PURE__ */ React.createElement("span", { style: { color: hover.gate_passed ? "var(--teal)" : "var(--ink-2)" } }, hover.gate_passed ? "\u2713 \uD1B5\uACFC" : "\u2717 \uD0C8\uB77D"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("span", null, hover.trade_count), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC77C\uD3C9\uADE0\uAC70\uB798"), /* @__PURE__ */ React.createElement("span", null, (typeof hover.daily_avg_trades === "number" ? hover.daily_avg_trades : 0).toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "MDD"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, fmtPct(hover.mdd)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC190\uC775"), /* @__PURE__ */ React.createElement("span", { className: hover.profit > 0 ? "num-pos" : hover.profit < 0 ? "num-neg" : "" }, fmtMoney(hover.profit)))), gens.length === 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 \uCD94\uC774\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4"))));
  }
  function LegendDot({ color, label, dashed, filled }) {
    return /* @__PURE__ */ React.createElement("span", { style: { display: "inline-flex", alignItems: "center", gap: 6, fontSize: 10.5, color: "var(--ink-2)", fontFamily: "var(--mono)" } }, dashed ? /* @__PURE__ */ React.createElement("span", { style: { width: 14, height: 0, borderTop: `1px dashed ${color}` } }) : filled === "ring" ? /* @__PURE__ */ React.createElement("span", { style: { width: 9, height: 9, borderRadius: "50%", background: color, border: "1.5px solid #fff", boxSizing: "border-box" } }) : /* @__PURE__ */ React.createElement("span", { style: { width: 8, height: 8, borderRadius: "50%", background: color } }), label);
  }
  function Mini({ label, value, sub, color }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2 } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" } }, label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 17, color: color || "var(--ink-0)" } }, value), sub && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, sub));
  }
  function ProfitChart({ state, targetPct = 0 }) {
    const gens = state.generations || [];
    const W = 880, H = 300;
    const padL = 52, padR = 56, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const xMax = Math.max(state.max_generations, 8);
    const x = (g) => padL + (g - 0.5) / xMax * innerW;
    const pctVals = gens.map((g) => typeof g.total_profit_pct === "number" ? g.total_profit_pct : 0);
    const pctMax = Math.max(targetPct + 1, 1, ...pctVals);
    const pctMin = Math.min(0, ...pctVals);
    const pctRange = pctMax - pctMin || 1;
    const yPct = (v) => padT + innerH - (v - pctMin) / pctRange * innerH;
    const moneyVals = gens.map((g) => typeof g.profit === "number" ? g.profit : 0);
    const moneyMax = Math.max(0, ...moneyVals);
    const moneyMin = Math.min(0, ...moneyVals);
    const moneyRange = moneyMax - moneyMin || 1;
    const yMoney = (v) => padT + innerH - (v - moneyMin) / moneyRange * innerH;
    const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
    const xTicks = [];
    for (let g = 1; g <= xMax; g++) {
      if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);
    }
    const pctPath = useMemo_c(() => {
      if (!gens.length) return "";
      return gens.map(
        (g, i) => `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yPct(g.total_profit_pct || 0).toFixed(2)}`
      ).join(" ");
    }, [gens, xMax, pctMin, pctRange]);
    const moneyPath = useMemo_c(() => {
      if (!gens.length) return "";
      return gens.map(
        (g, i) => `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yMoney(g.profit || 0).toFixed(2)}`
      ).join(" ");
    }, [gens, xMax, moneyMin, moneyRange]);
    const latest = gens[gens.length - 1];
    const peakPct = gens.reduce((a, b) => {
      var _a;
      return (b.total_profit_pct || 0) > ((_a = a == null ? void 0 : a.total_profit_pct) != null ? _a : -Infinity) ? b : a;
    }, null);
    const zeroY = yPct(0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uC218\uC775 \uCD94\uC774 \u2014 Profit Trajectory"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uC218\uC775\uB960 %" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--blue)", label: "\uC218\uC775\uAE08 \u20A9", dashed: true }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC2E0 \uC218\uC775\uB960",
        value: latest ? fmtPct(latest.total_profit_pct) : "\u2014",
        color: latest && latest.total_profit_pct > 0 ? "var(--teal)" : latest && latest.total_profit_pct < 0 ? "var(--red)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uACE0 \uC218\uC775\uB960",
        value: peakPct ? fmtPct(peakPct.total_profit_pct) : "\u2014",
        sub: peakPct ? `gen_${peakPct.gen_no}` : ""
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC2E0 \uC218\uC775\uAE08",
        value: latest ? fmtMoney(latest.profit) : "\u2014",
        color: latest && latest.profit > 0 ? "var(--teal)" : latest && latest.profit < 0 ? "var(--red)" : void 0
      }
    )), /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "payoff_ratio = avg win / abs(avg loss)",
      "total_profit_pct = operating-capital return",
      "profit line uses right-axis money scale"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: zeroY,
        y2: zeroY,
        stroke: "rgba(255,255,255,0.28)",
        strokeWidth: "1",
        strokeDasharray: "2 3"
      }
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: padL - 8,
        y: zeroY + 3,
        textAnchor: "end",
        fill: "var(--ink-2)"
      },
      "0%"
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: padL - 8,
        y: yPct(pctMax) + 3,
        textAnchor: "end",
        fill: "var(--amber)"
      },
      pctMax.toFixed(1),
      "%"
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: padL - 8,
        y: yPct(pctMin) + 3,
        textAnchor: "end",
        fill: "var(--amber)"
      },
      pctMin.toFixed(1),
      "%"
    ), _axisTicks(pctMin, pctMax, 5).map((tv, i) => Math.abs(tv) < 1e-9 || Math.abs(tv - pctMax) < 1e-9 || Math.abs(tv - pctMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("g", { key: `pyl${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: yPct(tv), y2: yPct(tv), stroke: "rgba(255,255,255,0.06)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yPct(tv) + 3, textAnchor: "end", fill: "var(--ink-3)" }, tv.toFixed(1), "%"))), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: W - padR + 6,
        y: yMoney(moneyMax) + 3,
        textAnchor: "start",
        fill: "var(--blue)"
      },
      fmtMoney(moneyMax)
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: W - padR + 6,
        y: yMoney(moneyMin) + 3,
        textAnchor: "start",
        fill: "var(--blue)"
      },
      fmtMoney(moneyMin)
    ), _axisTicks(moneyMin, moneyMax, 5).map((tv, i) => Math.abs(tv - moneyMax) < 1e-9 || Math.abs(tv - moneyMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("text", { key: `pyr${i}`, className: "chart-axis-text", x: W - padR + 6, y: yMoney(tv) + 3, textAnchor: "start", fill: "var(--ink-3)" }, fmtMoney(tv))), targetPct > 0 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: yPct(targetPct),
        y2: yPct(targetPct),
        stroke: "rgba(76,214,179,0.4)",
        strokeWidth: "1",
        strokeDasharray: "6 4"
      }
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        className: "chart-axis-text",
        x: W - padR - 4,
        y: yPct(targetPct) - 4,
        textAnchor: "end",
        fill: "var(--teal)"
      },
      "target ",
      targetPct.toFixed(1),
      "%"
    )), xTicks.map((g, i) => /* @__PURE__ */ React.createElement(
      "text",
      {
        key: `px${i}`,
        className: "chart-axis-text",
        x: x(g),
        y: H - 10,
        textAnchor: "middle"
      },
      "gen_",
      g
    )), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: padT + innerH,
        y2: padT + innerH,
        stroke: "var(--line-2)",
        strokeWidth: "1"
      }
    ), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: padL,
        y1: padT,
        y2: padT + innerH,
        stroke: "var(--line-2)",
        strokeWidth: "1"
      }
    ), gens.length > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(
      "path",
      {
        d: moneyPath,
        fill: "none",
        stroke: "var(--blue)",
        strokeWidth: "1.5",
        strokeDasharray: "5 4",
        opacity: "0.85"
      }
    ), /* @__PURE__ */ React.createElement("path", { d: pctPath, fill: "none", stroke: "var(--amber)", strokeWidth: "2" })), gens.map((g, i) => {
      const cx = x(g.gen_no), cy = yPct(g.total_profit_pct || 0);
      const col = (g.total_profit_pct || 0) > 0 ? "var(--teal)" : (g.total_profit_pct || 0) < 0 ? "var(--red)" : "var(--ink-2)";
      return /* @__PURE__ */ React.createElement("circle", { key: `pp${i}`, cx, cy, r: "2.6", fill: col });
    })), gens.length === 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 \uC218\uC775 \uCD94\uC774\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4"))));
  }
  var { useState: useState_eq, useEffect: useEffect_eq, useCallback: useCallback_eq, useRef: useRef_eq } = React;
  var _EQ_WINNER_COLORS = [
    "#4cd6b3",
    "#a594ff",
    "#f0b35a",
    "#6aa6ff",
    "#ff7eb6",
    "#73d673",
    "#ff9966",
    "#c084fc",
    "#38bdf8",
    "#fb923c",
    "#a3e635",
    "#f472b6"
  ];
  function EquityOverlayChart({ baseUrl, wsStatus, runId }) {
    const [data, setData] = useState_eq(null);
    const [loading, setLoading] = useState_eq(false);
    const [err, setErr] = useState_eq(null);
    const [hover, setHover] = useState_eq(null);
    const [periodInfo, setPeriodInfo] = useState_eq(null);
    const svgRef = useRef_eq(null);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const refresh = useCallback_eq(() => {
      if (isDemo || !baseUrl) return;
      setLoading(true);
      const url = baseUrl + "/equity_curves" + (runId ? "?run_id=" + encodeURIComponent(runId) : "");
      fetch(url, { signal: AbortSignal.timeout(4e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId]);
    useEffect_eq(() => {
      refresh();
      const id = setInterval(refresh, 3e4);
      return () => clearInterval(id);
    }, [refresh]);
    useEffect_eq(() => {
      if (isDemo || !baseUrl || !runId) {
        setPeriodInfo(null);
        return;
      }
      let alive = true;
      fetch(
        baseUrl + "/generation_durations?run_id=" + encodeURIComponent(runId),
        { signal: AbortSignal.timeout(4e3) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        if (!alive) return;
        const first = (j && j.durations || []).find((d) => d.period) || null;
        setPeriodInfo(first ? { period: first.period, timeframe: first.timeframe } : null);
      }).catch(() => {
        if (alive) setPeriodInfo(null);
      });
      return () => {
        alive = false;
      };
    }, [baseUrl, isDemo, runId]);
    const curves = data && data.curves || [];
    const winners = curves.filter((c) => c.gate_passed);
    const nonWinners = curves.filter((c) => !c.gate_passed);
    const W = 880, H = 320;
    const padL = 52, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const allEquity = curves.flatMap((c) => c.equity || []);
    const _sortedEq = allEquity.slice().sort((a, b) => a - b);
    const _pctile = (p) => _sortedEq.length ? _sortedEq[Math.min(_sortedEq.length - 1, Math.max(0, Math.round(p * (_sortedEq.length - 1))))] : 0;
    const yRawMax = _sortedEq.length ? Math.max(0, _pctile(0.95)) : 1;
    const yRawMin = _sortedEq.length ? Math.min(0, _pctile(0.05)) : -1;
    const yRange = yRawMax - yRawMin || 1;
    const xSvg = (frac) => padL + frac * innerW;
    const ySvg = (v) => padT + innerH - (v - yRawMin) / yRange * innerH;
    const zeroY = ySvg(0);
    const yTicks = (() => {
      const ticks = [];
      const rawStep = yRange / 5;
      const mag = Math.pow(10, Math.floor(Math.log10(Math.abs(rawStep) || 1)));
      const step = Math.ceil(rawStep / mag) * mag || 1;
      const start = Math.ceil(yRawMin / step) * step;
      for (let v = start; v <= yRawMax + 1e-9; v += step) {
        ticks.push(Math.round(v));
        if (ticks.length >= 8) break;
      }
      return ticks;
    })();
    const toPath = (equity) => {
      if (!equity || equity.length < 2) return "";
      return equity.map((v, i) => {
        const fx = i / (equity.length - 1);
        return `${i === 0 ? "M" : "L"} ${xSvg(fx).toFixed(1)} ${ySvg(v).toFixed(1)}`;
      }).join(" ");
    };
    const onMove = (e) => {
      if (!curves.length || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
      const tips = curves.slice(0, 40).map((c) => {
        const eq = c.equity || [];
        if (eq.length < 2) return null;
        const idx = frac * (eq.length - 1);
        const lo = Math.floor(idx), hi = Math.ceil(idx);
        const t = idx - lo;
        const y = eq[lo] * (1 - t) + (eq[hi] || eq[lo]) * t;
        return { run_id: c.run_id, gen_no: c.gen_no, gate_passed: c.gate_passed, final_pct: c.final_pct, y };
      }).filter(Boolean);
      setHover({ frac, tips });
    };
    const onLeave = () => setHover(null);
    const winnerCount = winners.length;
    const totalCount = curves.length;
    const maxFinalPct = curves.length ? Math.max(...curves.map((c) => c.final_pct)) : null;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uC804 \uC804\uB7B5 \uB204\uC801 \uC218\uC775\uACE1\uC120", /* @__PURE__ */ React.createElement(
      "span",
      {
        "data-tip": "\uC774 run \uC758 \uBAA8\uB4E0 \uC138\uB300(\uC804\uB7B5)\uC758 \uBC31\uD14C\uC2A4\uD2B8 \uB204\uC801 \uC218\uC775\uAE08\uC744 \uD55C \uCC28\uD2B8\uC5D0 \uACB9\uCCD0, \uC6B0\uC2B9(\uAC8C\uC774\uD2B8 \uD1B5\uACFC) \uC804\uB7B5\uC774 \uBE44\uC6B0\uC2B9 \uB300\uBE44 \uC5BC\uB9C8\uB098 \uC6B0\uC6D4\uD55C\uC9C0 \uD55C\uB208\uC5D0 \uBE44\uAD50\uD569\uB2C8\uB2E4. X\uCD95 = \uAC70\uB798 \uC9C4\uD589\uB960(\uC804\uB7B5\uB9C8\uB2E4 \uAC70\uB798 \uC218\uAC00 \uB2EC\uB77C 0~100%\uB85C \uC815\uADDC\uD654), Y\uCD95 = \uB204\uC801 \uC218\uC775\uAE08(\uC6D0).",
        style: {
          marginLeft: 6,
          fontSize: 10,
          color: "var(--ink-3)",
          border: "1px solid var(--line-2)",
          borderRadius: "50%",
          width: 15,
          height: 15,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "help"
        }
      },
      "?"
    )), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 12, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(255,255,255,0.18)", label: "\uBE44\uC6B0\uC2B9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC6B0\uC2B9(gate_passed)" }), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: refresh,
        disabled: isDemo || loading,
        "data-tip": "equity curves \uC0C8\uB85C\uACE0\uCE68"
      },
      loading ? "\uB85C\uB529\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uC804\uCCB4 \uACE1\uC120", value: totalCount > 0 ? String(totalCount) : "\u2014" }), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uC6B0\uC2B9 \uACE1\uC120",
        value: winnerCount > 0 ? String(winnerCount) : "\u2014",
        color: winnerCount > 0 ? "var(--teal)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uACE0 \uC218\uC775\uB960",
        value: maxFinalPct != null ? (maxFinalPct >= 0 ? "+" : "") + maxFinalPct.toFixed(1) + "%" : "\u2014",
        color: maxFinalPct != null && maxFinalPct > 0 ? "var(--teal)" : maxFinalPct != null && maxFinalPct < 0 ? "var(--red)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uBC31\uD14C \uAE30\uAC04",
        value: periodInfo && periodInfo.period ? periodInfo.period : "\uAE30\uAC04 \uC815\uBCF4 \uC5C6\uC74C",
        sub: periodInfo && periodInfo.timeframe ? String(periodInfo.timeframe) : ""
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 } }, "X\uCD95 = \uAC70\uB798 \uC9C4\uD589\uB960 0~100%(\uC804\uB7B5\uB9C8\uB2E4 \uAC70\uB798 \uC218\uAC00 \uB2EC\uB77C \uC815\uADDC\uD654) \xB7 Y\uCD95 = \uB204\uC801 \uC218\uC775\uAE08(\uC6D0) \xB7 \uD68C\uC0C9 = \uBE44\uC6B0\uC2B9 \xB7 \uC0C9 = \uC6B0\uC2B9(gate \uD1B5\uACFC)"), /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "edge_ratio = segment edge density",
      "winner curves use a 12-color palette",
      "non-winner curves stay subdued for comparison"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, isDemo ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC equity curves\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : err ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--red)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC870\uD68C \uC2E4\uD328: ", err) : curves.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 \uC218\uC775\uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4") : /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: onLeave
      },
      yTicks.map((t, i) => /* @__PURE__ */ React.createElement("g", { key: `ey${i}` }, /* @__PURE__ */ React.createElement(
        "line",
        {
          className: "chart-grid-line",
          x1: padL,
          x2: W - padR,
          y1: ySvg(t),
          y2: ySvg(t)
        }
      ), /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: ySvg(t) + 3,
          textAnchor: "end"
        },
        Math.abs(t) >= 1e8 ? (t / 1e8).toFixed(1) + "\uC5B5" : Math.abs(t) >= 1e4 ? (t / 1e4).toFixed(0) + "\uB9CC" : t.toLocaleString()
      ))),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: zeroY,
          y2: zeroY,
          stroke: "rgba(255,255,255,0.28)",
          strokeWidth: "1",
          strokeDasharray: "2 3"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: zeroY + 3,
          textAnchor: "end",
          fill: "var(--ink-2)"
        },
        "0"
      ),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: padT + innerH,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: padL,
          y1: padT,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      [0, 0.25, 0.5, 0.75, 1].map((f, i) => /* @__PURE__ */ React.createElement(
        "text",
        {
          key: `ex${i}`,
          className: "chart-axis-text",
          x: xSvg(f),
          y: H - 10,
          textAnchor: "middle"
        },
        Math.round(f * 100),
        "%"
      )),
      nonWinners.map((c, i) => {
        const d = toPath(c.equity);
        if (!d) return null;
        return /* @__PURE__ */ React.createElement(
          "path",
          {
            key: `nw${i}`,
            d,
            fill: "none",
            stroke: "rgba(255,255,255,0.10)",
            strokeWidth: "0.8"
          }
        );
      }),
      winners.map((c, i) => {
        const d = toPath(c.equity);
        if (!d) return null;
        const col = _EQ_WINNER_COLORS[i % _EQ_WINNER_COLORS.length];
        return /* @__PURE__ */ React.createElement(
          "path",
          {
            key: `w${i}`,
            d,
            fill: "none",
            stroke: col,
            strokeWidth: "2.0",
            opacity: "0.9"
          }
        );
      }),
      hover && (() => {
        const hx = xSvg(hover.frac);
        return /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: hx,
            x2: hx,
            y1: padT,
            y2: padT + innerH,
            stroke: "rgba(255,255,255,0.15)",
            strokeWidth: "1"
          }
        );
      })()
    ), hover && hover.tips.length > 0 && (() => {
      const winTips = hover.tips.filter((t) => t.gate_passed);
      const topTips = [
        ...winTips,
        ...hover.tips.filter((t) => !t.gate_passed).slice(0, Math.max(0, 5 - winTips.length))
      ];
      return /* @__PURE__ */ React.createElement("div", { style: {
        position: "absolute",
        top: 16,
        right: 16,
        background: "var(--bg-0)",
        border: "1px solid var(--line-2)",
        borderRadius: 6,
        padding: "8px 10px",
        fontFamily: "var(--mono)",
        fontSize: 11,
        minWidth: 200,
        maxWidth: 260,
        boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
        pointerEvents: "none"
      } }, /* @__PURE__ */ React.createElement("div", { style: {
        fontSize: 10,
        color: "var(--ink-2)",
        letterSpacing: ".12em",
        textTransform: "uppercase",
        marginBottom: 4
      } }, "\uC9C4\uD589 ", Math.round(hover.frac * 100), "%"), topTips.map((t, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: {
        display: "flex",
        justifyContent: "space-between",
        gap: 8,
        padding: "2px 0",
        color: t.gate_passed ? "var(--teal)" : "var(--ink-2)"
      } }, /* @__PURE__ */ React.createElement("span", null, t.run_id.slice(-6), "/g", t.gen_no), /* @__PURE__ */ React.createElement("span", null, t.y >= 0 ? "+" : "", Math.round(t.y).toLocaleString()))), hover.tips.length > topTips.length && /* @__PURE__ */ React.createElement("div", { style: { color: "var(--ink-3)", fontSize: 10, marginTop: 3 } }, "\uC678 ", hover.tips.length - topTips.length, "\uAC1C\u2026"));
    })())));
  }
  var _QUALITY_METRICS = [
    { key: "calmar", label: "Calmar", color: "var(--teal)", fmt: (v) => v.toFixed(2), hint: "CAGR/MDD \uC704\uD5D8\uC870\uC815\uC218\uC775(\uB192\uC744\uC218\uB85D \uC6B0\uC218)" },
    { key: "uptrend_r2", label: "\uC6B0\uC0C1\uD5A5 R\xB2", color: "var(--violet)", fmt: (v) => v.toFixed(3), hint: "\uB204\uC801\uACE1\uC120 \uC6B0\uC0C1\uD5A5 \uC801\uD569\uB3C4 0~1(\uB192\uC744\uC218\uB85D \uC6B0\uC218)" },
    { key: "mdd", label: "MDD %", color: "var(--red)", fmt: (v) => fmtPct(v), hint: "\uCD5C\uB300\uB099\uD3ED(\uB0AE\uC744\uC218\uB85D \uC6B0\uC218) \u2014 \uBCF4\uACE0\uC11C 1.9~6.75%" },
    { key: "daily_avg_trades", label: "\uC77C\uD3C9\uADE0\uAC70\uB798", color: "var(--amber)", fmt: (v) => v.toFixed(2), hint: "\uAC70\uB798\uC218/\uAC70\uB798\uC77C(\uBCF4\uACE0\uC11C 10~23)" },
    { key: "max_hold_count", label: "\uB3D9\uC2DC\uBCF4\uC720", color: "var(--blue)", fmt: (v) => v.toFixed(0), hint: "\uCD5C\uB300 \uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9\uC218(\uBCF4\uACE0\uC11C 6~12)" },
    { key: "payoff_ratio", label: "\uC190\uC775\uBE44", color: "#73d673", fmt: (v) => v.toFixed(2), hint: "\uD3C9\uADE0\uC774\uC775/\uD3C9\uADE0\uC190\uC2E4(\uBCF4\uACE0\uC11C 1.15~1.47)" }
  ];
  function QualityTrendChart({ state }) {
    const gens = state.generations || [];
    const [enabled, setEnabled] = useState_c(() => ({
      calmar: true,
      uptrend_r2: true,
      mdd: true,
      daily_avg_trades: false,
      max_hold_count: false,
      payoff_ratio: false
    }));
    const toggle = (k) => setEnabled((s) => ({ ...s, [k]: !s[k] }));
    const W = 880, H = 320;
    const padL = 44, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const xMax = Math.max(state.max_generations, 8);
    const x = (g) => padL + (g - 0.5) / xMax * innerW;
    const okGens = useMemo_c(() => gens.filter((g) => g.status !== "error"), [gens]);
    const ranges = useMemo_c(() => {
      const r = {};
      for (const m of _QUALITY_METRICS) {
        const vals = okGens.map((g) => typeof g[m.key] === "number" ? g[m.key] : null).filter((v) => v != null);
        if (!vals.length) {
          r[m.key] = null;
          continue;
        }
        let lo = Math.min(...vals), hi = Math.max(...vals);
        if (hi === lo) hi = lo + 1;
        r[m.key] = { lo, hi };
      }
      return r;
    }, [okGens]);
    const ny = (m, g) => {
      const rg = ranges[m.key];
      if (!rg || typeof g[m.key] !== "number" || g.status === "error") return null;
      const t = (g[m.key] - rg.lo) / (rg.hi - rg.lo);
      return padT + innerH - t * innerH;
    };
    const pathFor = (m) => {
      let d = "", started = false;
      for (const g of okGens) {
        const yy = ny(m, g);
        if (yy == null) continue;
        d += `${started ? "L" : "M"} ${x(g.gen_no).toFixed(2)} ${yy.toFixed(2)} `;
        started = true;
      }
      return d.trim();
    };
    const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
    const xTicks = [];
    for (let g = 1; g <= xMax; g++) if (g === 1 || g === xMax || g % xStep === 0) xTicks.push(g);
    const [hover, setHover] = useState_c(null);
    const svgRef = useRef_c(null);
    const onMove = (e) => {
      if (!okGens.length || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      let best = null, bestDist = Infinity;
      for (const g of okGens) {
        const d = Math.abs(x(g.gen_no) - px);
        if (d < bestDist) {
          bestDist = d;
          best = g;
        }
      }
      setHover(best && bestDist < 40 ? best : null);
    };
    const activeMetrics = _QUALITY_METRICS.filter((m) => enabled[m.key]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uD488\uC9C8\uC9C0\uD45C \uCD94\uC774 \u2014 Quality Metrics", /* @__PURE__ */ React.createElement(
      "span",
      {
        "data-tip": "\uD488\uC9C8 = \uC218\uC775 \uD06C\uAE30\uC640 \uBCC4\uAC1C\uB85C '\uC804\uB7B5\uC774 \uC5BC\uB9C8\uB098 \uAC74\uAC15\uD55C\uAC00'\uB97C \uBCF4\uB294 \uC704\uD5D8\uC870\uC815 \uC9C0\uD45C \uBB36\uC74C(calmar\xB7\uC6B0\uC0C1\uD5A5 R\xB2\xB7MDD\xB7\uC77C\uD3C9\uADE0 \uAC70\uB798\xB7\uB3D9\uC2DC\uBCF4\uC720\xB7\uC190\uC775\uBE44). \uAC01 \uCE69\uC5D0 \uB9C8\uC6B0\uC2A4\uB97C \uC62C\uB9AC\uBA74 \uC9C0\uD45C\uBCC4 \uC124\uBA85\uC774 \uB098\uC624\uACE0, \uD074\uB9AD\uD558\uBA74 \uD45C\uC2DC\uB97C \uCF1C\uACE0 \uB055\uB2C8\uB2E4.",
        style: {
          marginLeft: 6,
          fontSize: 10,
          color: "var(--ink-3)",
          border: "1px solid var(--line-2)",
          borderRadius: "50%",
          width: 15,
          height: 15,
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "help"
        }
      },
      "?"
    )), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" } }, _QUALITY_METRICS.map((m) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: m.key,
        onClick: () => toggle(m.key),
        "data-tip": m.hint,
        style: {
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          fontSize: 10.5,
          fontFamily: "var(--mono)",
          cursor: "pointer",
          padding: "3px 7px",
          borderRadius: 5,
          border: `1px solid ${enabled[m.key] ? m.color : "var(--line-2)"}`,
          background: enabled[m.key] ? "rgba(255,255,255,0.04)" : "transparent",
          color: enabled[m.key] ? "var(--ink-0)" : "var(--ink-3)"
        }
      },
      /* @__PURE__ */ React.createElement("span", { style: {
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: enabled[m.key] ? m.color : "var(--line-2)"
      } }),
      m.label
    )))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 } }, "\uAC01 \uC9C0\uD45C\uB294 \uC790\uAE30 \uBC94\uC704\uB85C \uC815\uADDC\uD654\uD55C '\uCD94\uC138 \uBAA8\uC591' \u2014 \uC2E4\uC81C\uAC12\uC740 hover \uCC38\uC870. \uBCF4\uACE0\uC11C \uBAA9\uD45C: \uC77C\uD3C9\uADE010~23\xB7\uB3D9\uC2DC\uBCF4\uC7206~12\xB7MDD<7%\xB7\uC190\uC775\uBE44>1.25"), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      [0, 0.5, 1].map((t, i) => {
        const yy = padT + innerH - t * innerH;
        return /* @__PURE__ */ React.createElement("line", { key: `qg${i}`, className: "chart-grid-line", x1: padL, x2: W - padR, y1: yy, y2: yy });
      }),
      xTicks.map((g, i) => /* @__PURE__ */ React.createElement("text", { key: `qx${i}`, className: "chart-axis-text", x: x(g), y: H - 10, textAnchor: "middle" }, "gen_", g)),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      activeMetrics.map((m) => {
        const d = pathFor(m);
        if (!d) return null;
        return /* @__PURE__ */ React.createElement("g", { key: m.key }, /* @__PURE__ */ React.createElement("path", { d, fill: "none", stroke: m.color, strokeWidth: "1.8", opacity: "0.9" }), okGens.map((g, i) => {
          const yy = ny(m, g);
          if (yy == null) return null;
          return /* @__PURE__ */ React.createElement("circle", { key: i, cx: x(g.gen_no), cy: yy, r: "2.4", fill: m.color });
        }));
      }),
      hover && (() => {
        const hx = x(hover.gen_no);
        return /* @__PURE__ */ React.createElement("line", { x1: hx, x2: hx, y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.12)", strokeWidth: "1" });
      })()
    ), hover && activeMetrics.length > 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 170,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: {
      fontSize: 10.5,
      color: "var(--ink-2)",
      letterSpacing: ".12em",
      textTransform: "uppercase",
      marginBottom: 4
    } }, "gen_", String(hover.gen_no).padStart(2, "0")), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, activeMetrics.map((m) => /* @__PURE__ */ React.createElement(React.Fragment, { key: m.key }, /* @__PURE__ */ React.createElement("span", { style: { color: m.color } }, m.label), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, typeof hover[m.key] === "number" ? m.fmt(hover[m.key]) : "\u2014"))))), okGens.length === 0 && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 \uD488\uC9C8\uC9C0\uD45C \uCD94\uC774\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4"))));
  }
  var {
    useState: useState_bd,
    useEffect: useEffect_bd,
    useCallback: useCallback_bd,
    useRef: useRef_bd,
    useMemo: useMemo_bd
  } = React;
  function BacktestDetailChart({ baseUrl, wsStatus, state, externalSelGen }) {
    const gens = state && state.generations || [];
    const runId = state && state.run_id || "";
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const defaultGen = useMemo_bd(() => {
      if (!gens.length) return null;
      const winners = gens.filter((g) => g.gate_passed);
      if (winners.length) {
        return winners.reduce((a, b) => (b.graded_score || 0) > (a.graded_score || 0) ? b : a).gen_no;
      }
      return gens[gens.length - 1].gen_no;
    }, [gens]);
    const [selGen, setSelGen] = useState_bd(null);
    useEffect_bd(() => {
      setSelGen(defaultGen);
    }, [defaultGen, runId]);
    useEffect_bd(() => {
      if (externalSelGen != null) setSelGen(externalSelGen);
    }, [externalSelGen]);
    const genNo = selGen != null ? selGen : defaultGen;
    const [data, setData] = useState_bd(null);
    const [loading, setLoading] = useState_bd(false);
    const [err, setErr] = useState_bd(null);
    const [hover, setHover] = useState_bd(null);
    const svgRef = useRef_bd(null);
    const refresh = useCallback_bd(() => {
      if (isDemo || !baseUrl || !runId || genNo == null) return;
      setLoading(true);
      const url = baseUrl + "/backtest_detail?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(genNo);
      fetch(url, { signal: AbortSignal.timeout(4e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId, genNo]);
    useEffect_bd(() => {
      refresh();
      const id = setInterval(refresh, 3e4);
      return () => clearInterval(id);
    }, [refresh]);
    const daily = data && data.daily || [];
    const cumulative = data && data.cumulative || [];
    const drawdown = data && data.drawdown || [];
    const holdings = data && data.holdings || [];
    const summary = data && data.summary || {};
    const hasSeries = daily.length > 0;
    const hasHoldings = holdings.length > 0;
    const peakHoldings = summary.peak_holdings != null ? summary.peak_holdings : 0;
    const selectedGeneration = gens.find((g) => g.gen_no === genNo) || null;
    const dbMaxHold = selectedGeneration && typeof selectedGeneration.max_hold_count === "number" ? selectedGeneration.max_hold_count : null;
    const sparseHoldSuspicious = (summary.trade_count || 0) >= 50 && dbMaxHold != null && dbMaxHold <= 1 && peakHoldings > dbMaxHold;
    const noTrades = !hasSeries || summary.trade_count != null && summary.trade_count === 0;
    const W = 880, H = 320;
    const padL = 56, padR = 60, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const pnlVals = daily.map((d) => d.daily_pnl || 0);
    const pnlMax = Math.max(0, ...pnlVals);
    const pnlMin = Math.min(0, ...pnlVals);
    const pnlRange = pnlMax - pnlMin || 1;
    const yPnl = (v) => padT + innerH - (v - pnlMin) / pnlRange * innerH;
    const zeroY = yPnl(0);
    const cumVals = cumulative.map((c) => c.cum_profit || 0);
    const cumMax = Math.max(0, ...cumVals);
    const cumMin = Math.min(0, ...cumVals);
    const cumRange = cumMax - cumMin || 1;
    const yCum = (v) => padT + innerH - (v - cumMin) / cumRange * innerH;
    const n = daily.length;
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, slot * 0.7);
    const xBar = (i) => padL + (i + 0.5) * slot;
    const fmtMoneyShort = (v) => {
      const a = Math.abs(v);
      if (a >= 1e8) return (v / 1e8).toFixed(1) + "\uC5B5";
      if (a >= 1e4) return Math.round(v / 1e4) + "\uB9CC";
      return Math.round(v).toLocaleString();
    };
    const cumPath = useMemo_bd(() => {
      if (cumulative.length < 2) return "";
      return cumulative.map(
        (c, i) => `${i === 0 ? "M" : "L"} ${xBar(i).toFixed(2)} ${yCum(c.cum_profit || 0).toFixed(2)}`
      ).join(" ");
    }, [cumulative, n, cumMin, cumRange]);
    const HpH = 90;
    const hpPadT = 14, hpPadB = 18;
    const hpInnerH = HpH - hpPadT - hpPadB;
    const hN = holdings.length;
    const xHold = (i) => hN <= 1 ? padL + innerW / 2 : padL + i / (hN - 1) * innerW;
    const holdMax = Math.max(1, peakHoldings, ...holdings.map((h) => h.count || 0));
    const yHold = (v) => hpPadT + hpInnerH - v / holdMax * hpInnerH;
    const holdPath = useMemo_bd(() => {
      if (hN < 1) return "";
      let dStr = `M ${xHold(0).toFixed(2)} ${yHold(holdings[0].count || 0).toFixed(2)}`;
      for (let i = 1; i < hN; i++) {
        const x = xHold(i).toFixed(2);
        const yPrev = yHold(holdings[i - 1].count || 0).toFixed(2);
        const y = yHold(holdings[i].count || 0).toFixed(2);
        dStr += ` L ${x} ${yPrev} L ${x} ${y}`;
      }
      return dStr;
    }, [holdings, hN, holdMax]);
    const holdYTicks = (() => {
      if (holdMax <= 1) return [0, 1];
      if (holdMax <= 4) return Array.from({ length: holdMax + 1 }, (_, k) => k);
      return [0, Math.round(holdMax / 2), holdMax];
    })();
    const xLabelIdxs = (() => {
      if (n === 0) return [];
      const step = Math.max(1, Math.ceil(n / 8));
      const idxs = [];
      for (let i = 0; i < n; i += step) idxs.push(i);
      if (idxs[idxs.length - 1] !== n - 1) idxs.push(n - 1);
      return idxs;
    })();
    const fmtDate = (d) => {
      const s = String(d);
      return s.length === 8 ? s.slice(4, 6) + "/" + s.slice(6, 8) : s;
    };
    const fmtDateY = (d, prevD) => {
      const s = String(d);
      if (s.length !== 8) return fmtDate(d);
      const ps = prevD != null ? String(prevD) : "";
      const sameYear = ps.length === 8 && ps.slice(0, 4) === s.slice(0, 4);
      return sameYear ? s.slice(4, 6) + "/" + s.slice(6, 8) : s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
    };
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const i = Math.floor((px - padL) / slot);
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    const onLeave = () => setHover(null);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uBC31\uD14C \uC0C1\uC138 \u2014 \uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9\uC218 \xB7 \uC77C\uBCC4\uC190\uC775 \xB7 \uB204\uC801\uC218\uC775\uACE1\uC120"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 12, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9\uC218" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC774\uC775(\uC77C)" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--blue)", label: "\uC190\uC2E4(\uC77C)" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB204\uC801\uC218\uC775 \u20A9" }), gens.length > 0 && /* @__PURE__ */ React.createElement(
      "select",
      {
        value: genNo != null ? genNo : "",
        onChange: (e) => setSelGen(Number(e.target.value)),
        className: "mono",
        style: {
          fontSize: 11,
          background: "var(--bg-1)",
          color: "var(--ink-0)",
          border: "1px solid var(--line-2)",
          borderRadius: 5,
          padding: "3px 6px"
        },
        "data-tip": "\uC138\uB300 \uC120\uD0DD"
      },
      gens.map((g) => /* @__PURE__ */ React.createElement("option", { key: g.gen_no, value: g.gen_no }, "gen_", g.gen_no, g.gate_passed ? " \u2713" : ""))
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: refresh,
        disabled: isDemo || loading || !runId,
        "data-tip": "\uBC31\uD14C \uC0C1\uC138 \uC0C8\uB85C\uACE0\uCE68"
      },
      loading ? "\uB85C\uB529\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uAC70\uB798\uC218", value: summary.trade_count != null ? String(summary.trade_count) : "\u2014" }), /* @__PURE__ */ React.createElement(Mini, { label: "\uAC70\uB798\uC77C", value: summary.n_days != null ? String(summary.n_days) : "\u2014" }), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uB300 \uB3D9\uC2DC\uBCF4\uC720",
        value: noTrades ? "\uAC70\uB798\uC5C6\uC74C" : summary.peak_holdings != null ? String(summary.peak_holdings) : "\u2014",
        color: !noTrades && peakHoldings > 0 ? "var(--teal)" : "var(--ink-3)",
        sub: "\uC885\uBAA9\uC218"
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "DB max_hold_count",
        value: dbMaxHold != null ? String(dbMaxHold) : "\u2014",
        color: sparseHoldSuspicious ? "var(--red)" : void 0,
        sub: "\uC800\uC7A5\uAC12"
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC885 \uB204\uC801\uC218\uC775",
        value: summary.final_profit != null ? fmtMoney(summary.final_profit) : "\u2014",
        color: summary.final_profit > 0 ? "var(--teal)" : summary.final_profit < 0 ? "var(--red)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uB300 \uBC18\uB0A9\uC561",
        value: summary.max_drawdown != null ? fmtMoney(summary.max_drawdown) : "\u2014",
        color: summary.max_drawdown > 0 ? "var(--red)" : void 0,
        sub: "\uACE0\uC810 \uB300\uBE44(\uC6D0)"
      }
    )), /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      `run_id=${runId || "-"}`,
      `gen_no=${genNo != null ? genNo : "-"}`,
      "peak_holdings=0 can mean no overlap buy/sell timing data",
      `DB max_hold_count=${dbMaxHold != null ? dbMaxHold : "-"}`,
      "period/timeframe are inherited from the selected run"
    ] }), sparseHoldSuspicious && /* @__PURE__ */ React.createElement("div", { className: "research-empty danger", title: "Sparse hold warning" }, "Sparse hold warning: DB max_hold_count ", dbMaxHold, " differs from CSV peak_holdings ", peakHoldings, ". human corridor 6-12; treat this as an audit signal, not promotion proof."), !isDemo && !err && hasHoldings && /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 6 } }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${HpH}`,
        preserveAspectRatio: "none",
        style: { width: "100%", height: HpH, display: "block" }
      },
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: hpPadT + hpInnerH,
          y2: hpPadT + hpInnerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: padL,
          y1: hpPadT,
          y2: hpPadT + hpInnerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      holdYTicks.map((tk) => /* @__PURE__ */ React.createElement("g", { key: `hyt${tk}` }, /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: yHold(tk),
          y2: yHold(tk),
          stroke: "rgba(255,255,255,0.08)",
          strokeWidth: "1"
        }
      ), /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: yHold(tk) + 3,
          textAnchor: "end",
          fill: "var(--ink-2)"
        },
        tk
      ))),
      noTrades ? /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: W - padR + 6,
          y: hpPadT + hpInnerH / 2 + 3,
          textAnchor: "start",
          fill: "var(--ink-3)"
        },
        "\uAC70\uB798\uC5C6\uC74C"
      ) : peakHoldings > 0 && /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: W - padR + 6,
          y: yHold(peakHoldings) + 3,
          textAnchor: "start",
          fill: "var(--teal)"
        },
        "peak ",
        peakHoldings
      ),
      /* @__PURE__ */ React.createElement("path", { d: holdPath, fill: "none", stroke: "var(--teal)", strokeWidth: "1.8", opacity: "0.95" })
    ), /* @__PURE__ */ React.createElement("div", { style: {
      fontSize: 10.5,
      color: "var(--ink-3)",
      fontFamily: "var(--mono)",
      marginTop: 2,
      paddingLeft: padL * (100 / W) + "%"
    } }, "\uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9\uC218(\uB9E4\uC218~\uB9E4\uB3C4 \uAD6C\uAC04 \uC911\uCCA9). \uBCF4\uC720\uAE08\uC561(\uC6D0)\uC740 \uC5D4\uC9C4 \uC804\uC6A9\uC774\uB77C \uBBF8\uD45C\uC2DC \u2014 \uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9\uC218\uB85C \uB300\uCCB4.")), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, isDemo ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uBC31\uD14C \uC0C1\uC138\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : err ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--red)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC870\uD68C \uC2E4\uD328: ", err) : !hasSeries ? /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, summary.trade_count != null && summary.trade_count === 0 ? "\uC774 \uC138\uB300\uB294 \uAC70\uB798\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4 (\uD0C0\uC784\uC544\uC6C3/\uBB34\uAC70\uB798)" : "\uBC31\uD14C \uACB0\uACFC \uC2DC\uACC4\uC5F4\uC774 \uC5C6\uC2B5\uB2C8\uB2E4(CSV \uC5C6\uC74C/\uD1A0\uAE00)") : /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: onLeave
      },
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: zeroY,
          y2: zeroY,
          stroke: "rgba(255,255,255,0.28)",
          strokeWidth: "1",
          strokeDasharray: "2 3"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: zeroY + 3,
          textAnchor: "end",
          fill: "var(--ink-2)"
        },
        "0"
      ),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: yPnl(pnlMax) + 3,
          textAnchor: "end",
          fill: "var(--ink-2)"
        },
        fmtMoneyShort(pnlMax)
      ),
      pnlMin < 0 && /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: padL - 8,
          y: yPnl(pnlMin) + 3,
          textAnchor: "end",
          fill: "var(--ink-2)"
        },
        fmtMoneyShort(pnlMin)
      ),
      _axisTicks(pnlMin, pnlMax, 5).map((tv, i) => Math.abs(tv) < 1e-9 || Math.abs(tv - pnlMax) < 1e-9 || Math.abs(tv - pnlMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("g", { key: `byl${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: yPnl(tv), y2: yPnl(tv), stroke: "rgba(255,255,255,0.06)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yPnl(tv) + 3, textAnchor: "end", fill: "var(--ink-3)" }, fmtMoneyShort(tv)))),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: W - padR + 6,
          y: yCum(cumMax) + 3,
          textAnchor: "start",
          fill: "var(--amber)"
        },
        fmtMoneyShort(cumMax)
      ),
      /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: W - padR + 6,
          y: yCum(cumMin) + 3,
          textAnchor: "start",
          fill: "var(--amber)"
        },
        fmtMoneyShort(cumMin)
      ),
      _axisTicks(cumMin, cumMax, 5).map((tv, i) => Math.abs(tv - cumMax) < 1e-9 || Math.abs(tv - cumMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("text", { key: `byr${i}`, className: "chart-axis-text", x: W - padR + 6, y: yCum(tv) + 3, textAnchor: "start", fill: "var(--ink-3)" }, fmtMoneyShort(tv))),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: padT + innerH,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: padL,
          y1: padT,
          y2: padT + innerH,
          stroke: "var(--line-2)",
          strokeWidth: "1"
        }
      ),
      xLabelIdxs.map((i, k) => /* @__PURE__ */ React.createElement(
        "text",
        {
          key: `bx${i}`,
          className: "chart-axis-text",
          x: xBar(i),
          y: H - 10,
          textAnchor: "middle"
        },
        fmtDateY(daily[i].date, k > 0 && daily[xLabelIdxs[k - 1]] ? daily[xLabelIdxs[k - 1]].date : null)
      )),
      daily.map((d, i) => {
        const v = d.daily_pnl || 0;
        const yTop = v >= 0 ? yPnl(v) : zeroY;
        const yBot = v >= 0 ? zeroY : yPnl(v);
        const h = Math.max(0.5, yBot - yTop);
        const col = v >= 0 ? "var(--red)" : "var(--blue)";
        return /* @__PURE__ */ React.createElement(
          "rect",
          {
            key: `bar${i}`,
            x: xBar(i) - barW / 2,
            y: yTop,
            width: barW,
            height: h,
            fill: col,
            opacity: "0.78"
          }
        );
      }),
      cumulative.length > 1 && /* @__PURE__ */ React.createElement("path", { d: cumPath, fill: "none", stroke: "var(--amber)", strokeWidth: "2.2", opacity: "0.95" }),
      hover != null && (() => {
        const hx = xBar(hover);
        return /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: hx,
            x2: hx,
            y1: padT,
            y2: padT + innerH,
            stroke: "rgba(255,255,255,0.15)",
            strokeWidth: "1"
          }
        ), cumulative[hover] && /* @__PURE__ */ React.createElement(
          "circle",
          {
            cx: hx,
            cy: yCum(cumulative[hover].cum_profit || 0),
            r: "3.5",
            fill: "none",
            stroke: "var(--amber)",
            strokeWidth: "1.5"
          }
        ));
      })()
    ), hover != null && hasSeries && daily[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 190,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: {
      fontSize: 10.5,
      color: "var(--ink-2)",
      letterSpacing: ".12em",
      textTransform: "uppercase",
      marginBottom: 4
    } }, fmtDate(daily[hover].date), " \xB7 ", String(daily[hover].date)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC77C\uC190\uC775"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: daily[hover].daily_pnl > 0 ? "num-pos" : daily[hover].daily_pnl < 0 ? "num-neg" : "",
        style: { textAlign: "right" }
      },
      fmtMoney(daily[hover].daily_pnl)
    ), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--amber)" } }, cumulative[hover] ? fmtMoney(cumulative[hover].cum_profit) : "\u2014"), cumulative[hover] && cumulative[hover].cum_pct != null && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801%"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, fmtPct(cumulative[hover].cum_pct))), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uBC18\uB0A9\uC561"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--red)" } }, drawdown[hover] ? fmtMoney(drawdown[hover].drawdown) : "\u2014"))))));
  }
  function HallOfFamePanel({ baseUrl, wsStatus }) {
    const [data, setData] = useState_eq(null);
    const [loading, setLoading] = useState_eq(false);
    const [err, setErr] = useState_eq(null);
    const [sortKey, setSortKey] = useState_eq("total_return_pct");
    const [filter, setFilter] = useState_eq("all");
    const [galleryOpen, setGalleryOpen] = useState_eq(false);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const refresh = useCallback_eq(() => {
      if (isDemo || !baseUrl) return;
      setLoading(true);
      fetch(baseUrl + "/hall_of_fame", { signal: AbortSignal.timeout(4e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo]);
    useEffect_eq(() => {
      refresh();
      const id = setInterval(refresh, 3e4);
      return () => clearInterval(id);
    }, [refresh]);
    const human = data && data.human || [];
    const ai = data && data.ai || [];
    const rows = [
      ...human.map((h) => ({ ...h, _maxHold: h.max_holdings })),
      ...ai.map((a) => ({ ...a, _maxHold: a.max_hold_count }))
    ].filter((r) => filter === "all" ? true : r.kind === filter);
    const sorted = rows.slice().sort((a, b) => {
      const av = a[sortKey], bv = b[sortKey];
      const an = typeof av === "number" ? av : -Infinity;
      const bn = typeof bv === "number" ? bv : -Infinity;
      return bn - an;
    });
    const fmtPctSigned = (v) => typeof v === "number" ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : "\u2014";
    const fmtPlain = (v, d = 1) => typeof v === "number" ? v.toFixed(d) : "\u2014";
    const fmtInt22 = (v) => typeof v === "number" ? Math.round(v).toLocaleString("ko-KR") : "\u2014";
    const SORTS = [
      { key: "total_return_pct", label: "\uCD1D\uC218\uC775\uB960" },
      { key: "total_return_krw", label: "\uCD1D\uC218\uC775\uAE08" },
      { key: "annual_return_pct", label: "\uC5F0\uD3C9\uADE0" },
      { key: "mdd_pct", label: "MDD" },
      { key: "payoff", label: "payoff" }
    ];
    const FILTERS = [
      { key: "all", label: "\uC804\uCCB4" },
      { key: "human", label: "\u{1F464} \uC778\uAC04" },
      { key: "seed", label: "\u{1F331} \uC2DC\uB4DC" },
      { key: "ai", label: "\u{1F916} AI" }
    ];
    const HOF_KIND_META = {
      human: { color: "var(--green)", label: "\u{1F464} \uC778\uAC04", bg: "rgba(110,231,168,0.06)" },
      seed: { color: "var(--amber)", label: "\u{1F331} \uC2DC\uB4DC", bg: "rgba(240,179,90,0.08)" },
      ai: { color: "var(--violet)", label: "\u{1F916} AI", bg: "rgba(165,148,255,0.08)" }
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\u{1F3C6} \uC131\uACFC \uBA85\uC608\uC758 \uC804\uB2F9 \u2014 \uC778\uAC04 \uBCA4\uCE58\uB9C8\uD06C & AI \uC0DD\uC131"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--green)", label: "\u{1F464} \uC778\uAC04 \uBCA4\uCE58\uB9C8\uD06C" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\u{1F331} \uC2DC\uB4DC(Tick_902 \uC778\uAC04\uD29C\uB2DD)" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--violet)", label: "\u{1F916} AI \uC0DD\uC131(AILOOP)" }), /* @__PURE__ */ React.createElement(
      "span",
      {
        style: { fontSize: 10, color: "var(--ink-3)", fontFamily: "var(--mono)" },
        "data-tip": "\uBC31\uD14C \uAE30\uAC04\uC774 3\uAC1C\uC6D4 \uBBF8\uB9CC\uC774\uBA74 \uC5F0\uD3C9\uADE0\uC774 \uACFC\uB300\uCD94\uC815\uB428 \u2014 \uC2E0\uB8B0 \uB0AE\uC74C"
      },
      "\uB2E8\uAE30=\uC5F0\uD658\uC0B0 \uC2E0\uB8B0\uB0AE\uC74C(\uC9E7\uC740 \uBC31\uD14C)"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => setGalleryOpen(true),
        "data-tip": "\uC778\uAC04 reference \uACB0\uACFC \uC2A4\uD06C\uB9B0\uC0F7 \uAC24\uB7EC\uB9AC \uC5F4\uAE30"
      },
      "\u{1F4F7} \uC778\uAC04 \uACB0\uACFC \uC2A4\uD06C\uB9B0\uC0F7"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: refresh,
        disabled: isDemo || loading,
        "data-tip": "\uBA85\uC608\uC758 \uC804\uB2F9 \uC0C8\uB85C\uACE0\uCE68"
      },
      loading ? "\uB85C\uB529\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 16, marginBottom: 12, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" } }, "\uC815\uB82C"), SORTS.map((s) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: s.key,
        className: "btn ghost sm",
        onClick: () => setSortKey(s.key),
        style: sortKey === s.key ? { color: "var(--amber)", borderColor: "var(--amber)" } : void 0
      },
      s.label
    ))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" } }, "\uAD6C\uBD84"), FILTERS.map((f) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: f.key,
        className: "btn ghost sm",
        onClick: () => setFilter(f.key),
        style: filter === f.key ? { color: "var(--ink-0)", borderColor: "var(--line-2)" } : void 0
      },
      f.label
    ))), /* @__PURE__ */ React.createElement("div", { style: { marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" } }, "\uC778\uAC04 ", human.length, " \xB7 \uC2DC\uB4DC ", ai.filter((r) => r.kind === "seed").length, " \xB7 AI ", ai.filter((r) => r.kind === "ai").length)), isDemo ? /* @__PURE__ */ React.createElement("div", { style: {
      padding: "28px 0",
      textAlign: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uBA85\uC608\uC758 \uC804\uB2F9\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : err ? /* @__PURE__ */ React.createElement("div", { style: {
      padding: "28px 0",
      textAlign: "center",
      color: "var(--red)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uC870\uD68C \uC2E4\uD328: ", err) : sorted.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: {
      padding: "28px 0",
      textAlign: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, "\uD45C\uC2DC\uD560 \uC804\uB7B5\uC774 \uC5C6\uC2B5\uB2C8\uB2E4 (\uC778\uAC04 \uBCA4\uCE58\uB9C8\uD06C JSON / AI \uD751\uC790 \uC138\uB300 \uB204\uC801 \uC2DC \uD45C\uC2DC).") : /* @__PURE__ */ React.createElement("div", { className: "hof-scroll", style: { overflowX: "auto", width: "100%" } }, /* @__PURE__ */ React.createElement("table", { className: "data-table", style: {
      width: "100%",
      borderCollapse: "collapse",
      fontFamily: "var(--mono)",
      fontSize: 12,
      minWidth: 1180
    } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: {
      color: "var(--ink-2)",
      fontSize: 10,
      letterSpacing: ".08em",
      textTransform: "uppercase",
      borderBottom: "1px solid var(--line-2)"
    } }, /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "6px 8px" } }, "\uAD6C\uBD84"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "6px 8px" } }, "\uC774\uB984"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uCD1D\uC218\uC775\uAE08(\uC6D0)"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uCD1D\uC218\uC775\uB960%"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uC5F0\uD3C9\uADE0%"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "MDD%"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "payoff"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uC77C\uD3C9\uADE0\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uB3D9\uC2DC\uBCF4\uC720"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "6px 8px" } }, "\uC6B4\uC601\uAE08(\uC6D0)"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "6px 8px" } }, "\uBC31\uD14C \uAE30\uAC04"))), /* @__PURE__ */ React.createElement("tbody", null, sorted.map((r, i) => {
      const _km = HOF_KIND_META[r.kind] || HOF_KIND_META.ai;
      const accent = _km.color;
      return /* @__PURE__ */ React.createElement(
        "tr",
        {
          key: (r.kind || "") + (r.label || "") + i,
          style: { borderBottom: "1px solid rgba(255,255,255,0.05)" }
        },
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px" } }, /* @__PURE__ */ React.createElement("span", { style: {
          display: "inline-block",
          padding: "1px 6px",
          borderRadius: 4,
          fontSize: 10,
          fontWeight: 600,
          color: accent,
          border: `1px solid ${accent}`,
          background: _km.bg
        } }, _km.label)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", color: "var(--ink-0)" } }, r.label || "\u2014"),
        /* @__PURE__ */ React.createElement("td", { style: {
          padding: "5px 8px",
          textAlign: "right",
          color: typeof r.total_return_krw === "number" && r.total_return_krw > 0 ? "var(--teal)" : "var(--ink-0)"
        } }, typeof r.total_return_krw === "number" ? fmtMoney(r.total_return_krw) : "\u2014"),
        /* @__PURE__ */ React.createElement("td", { style: {
          padding: "5px 8px",
          textAlign: "right",
          color: typeof r.total_return_pct === "number" && r.total_return_pct > 0 ? "var(--teal)" : "var(--ink-0)"
        } }, fmtPctSigned(r.total_return_pct)),
        /* @__PURE__ */ React.createElement("td", { style: {
          padding: "5px 8px",
          textAlign: "right",
          color: r.annual_unreliable ? "var(--ink-3)" : "var(--ink-0)"
        } }, fmtPctSigned(r.annual_return_pct), r.annual_unreliable && /* @__PURE__ */ React.createElement(
          "span",
          {
            "data-tip": "\uBC31\uD14C \uAE30\uAC04\uC774 3\uAC1C\uC6D4 \uBBF8\uB9CC\uC774\uB77C \uC5F0\uD3C9\uADE0\uC774 \uACFC\uB300\uCD94\uC815\uB428(1\uAC1C\uC6D4 7%\u2192\uC5F084% \uC2DD). \uB2E8\uAE30 \uCC3D\uC740 \uC2E0\uB8B0 \uB0AE\uC74C.",
            title: "\uBC31\uD14C \uAE30\uAC04\uC774 3\uAC1C\uC6D4 \uBBF8\uB9CC\uC774\uB77C \uC5F0\uD3C9\uADE0\uC774 \uACFC\uB300\uCD94\uC815\uB428(1\uAC1C\uC6D4 7%\u2192\uC5F084% \uC2DD). \uB2E8\uAE30 \uCC3D\uC740 \uC2E0\uB8B0 \uB0AE\uC74C.",
            style: {
              fontSize: 9,
              color: "var(--ink-3)",
              marginLeft: 4,
              borderBottom: "1px dotted var(--ink-3)",
              cursor: "help"
            }
          },
          "\uB2E8\uAE30"
        )),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", textAlign: "right", color: "var(--red)" } }, fmtPlain(r.mdd_pct, 2)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" } }, fmtPlain(r.payoff, 2)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" } }, fmtPlain(r.daily_avg_trades, 1)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", textAlign: "right", color: "var(--ink-0)" } }, typeof r._maxHold === "number" ? fmtPlain(r._maxHold, r.kind === "ai" ? 1 : 0) : "\u2014"),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "5px 8px", textAlign: "right", color: "var(--ink-2)" } }, fmtInt22(r.operating_capital_krw)),
        /* @__PURE__ */ React.createElement("td", { style: {
          padding: "5px 8px",
          textAlign: "left",
          color: "var(--ink-2)",
          whiteSpace: "nowrap",
          fontSize: 11
        } }, r.period || "\u2014", typeof r.days === "number" && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", marginLeft: 5 } }, "(", r.days, "\uC77C)"))
      );
    }))))), galleryOpen && /* @__PURE__ */ React.createElement(ReferenceGallery, { baseUrl, onClose: () => setGalleryOpen(false) }));
  }
  var { useState: useState_rg, useEffect: useEffect_rg } = React;
  function ReferenceGallery({ baseUrl, onClose }) {
    const [files, setFiles] = useState_rg(null);
    const [err, setErr] = useState_rg(null);
    const [zoom, setZoom] = useState_rg(null);
    useEffect_rg(() => {
      if (!baseUrl) {
        setFiles([]);
        return;
      }
      let cancelled = false;
      fetch(baseUrl + "/reference_screenshots", { signal: AbortSignal.timeout(4e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        if (!cancelled) {
          setFiles(j.screenshots || []);
          setErr(null);
        }
      }).catch((e) => {
        if (!cancelled) setErr(String(e));
      }).finally(() => {
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl]);
    const imgSrc = (name) => baseUrl + "/reference_img/" + encodeURIComponent(name);
    return /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "modal-bd",
        onMouseDown: (e) => {
          if (e.target === e.currentTarget) zoom ? setZoom(null) : onClose();
        }
      },
      /* @__PURE__ */ React.createElement(
        "div",
        {
          className: "modal",
          style: { width: "min(1100px, calc(100vw - 32px))" },
          onMouseDown: (e) => e.stopPropagation()
        },
        /* @__PURE__ */ React.createElement("div", { className: "modal-hd" }, /* @__PURE__ */ React.createElement("h2", null, "\u{1F4F7} \uC778\uAC04 \uACB0\uACFC \uC2A4\uD06C\uB9B0\uC0F7", /* @__PURE__ */ React.createElement("span", { className: "sub" }, "STOM_Good_Results \u2014 \uACB0\uACFC \uD654\uBA74 ", files ? files.length : "\u2026", "\uC7A5 \xB7 \uC2A4\uD06C\uB9B0\uC0F7\u2194\uC804\uB7B5# \uB9E4\uD551 \uBD88\uD655\uC2E4(\uC804\uCCB4 \uBE0C\uB77C\uC6B0\uC9D5)")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, zoom && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setZoom(null) }, "\u2190 \uADF8\uB9AC\uB4DC"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose }, "\uB2EB\uAE30"))),
        /* @__PURE__ */ React.createElement("div", { style: { flex: 1, overflowY: "auto", padding: 16 } }, err ? /* @__PURE__ */ React.createElement("div", { style: {
          padding: "28px 0",
          textAlign: "center",
          color: "var(--red)",
          fontSize: 12,
          fontFamily: "var(--mono)"
        } }, "\uC2A4\uD06C\uB9B0\uC0F7 \uBAA9\uB85D \uC870\uD68C \uC2E4\uD328: ", err) : files == null ? /* @__PURE__ */ React.createElement("div", { style: {
          padding: "28px 0",
          textAlign: "center",
          color: "var(--ink-3)",
          fontSize: 12,
          fontFamily: "var(--mono)"
        } }, "\uC2A4\uD06C\uB9B0\uC0F7 \uBD88\uB7EC\uC624\uB294 \uC911\u2026") : files.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: {
          padding: "28px 0",
          textAlign: "center",
          color: "var(--ink-3)",
          fontSize: 12,
          fontFamily: "var(--mono)"
        } }, "\uD45C\uC2DC\uD560 \uC2A4\uD06C\uB9B0\uC0F7\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.") : zoom ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", gap: 10 } }, /* @__PURE__ */ React.createElement(
          "img",
          {
            src: imgSrc(zoom),
            alt: zoom,
            style: {
              maxWidth: "100%",
              maxHeight: "70vh",
              objectFit: "contain",
              border: "1px solid var(--line-2)",
              borderRadius: 6
            }
          }
        ), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 11, color: "var(--ink-3)", fontFamily: "var(--mono)" } }, zoom)) : /* @__PURE__ */ React.createElement("div", { style: {
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 12
        } }, files.map((name) => /* @__PURE__ */ React.createElement(
          "div",
          {
            key: name,
            onClick: () => setZoom(name),
            "data-tip": "\uD074\uB9AD\uD558\uBA74 \uD655\uB300",
            style: {
              cursor: "zoom-in",
              border: "1px solid var(--line-2)",
              borderRadius: 6,
              overflow: "hidden",
              background: "var(--bg-0)"
            }
          },
          /* @__PURE__ */ React.createElement(
            "img",
            {
              src: imgSrc(name),
              alt: name,
              loading: "lazy",
              style: { width: "100%", height: 120, objectFit: "cover", display: "block" }
            }
          ),
          /* @__PURE__ */ React.createElement("div", { style: {
            fontSize: 9.5,
            color: "var(--ink-3)",
            fontFamily: "var(--mono)",
            padding: "4px 6px",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis"
          } }, name)
        ))))
      )
    );
  }
  Object.assign(window, { FitnessChart, ProfitChart, EquityOverlayChart, QualityTrendChart, BacktestDetailChart, HallOfFamePanel, ReferenceGallery });

  // ../frontend/hypothesis.jsx
  var _VERDICT_META = {
    accepted: { label: "\uCC44\uD0DD", color: "var(--teal)", tip: "\uC2E4\uCE21 \uB378\uD0C0 \uBD80\uD638\uAC00 \uAE30\uB300 \uBC29\uD5A5\uACFC \uC77C\uCE58(\uAC00\uC815\uC774 \uB9DE\uC558\uB2E4)" },
    rejected: { label: "\uAE30\uAC01", color: "var(--red)", tip: "\uC2E4\uCE21 \uB378\uD0C0 \uBD80\uD638\uAC00 \uAE30\uB300 \uBC29\uD5A5\uACFC \uBC18\uB300(\uAC00\uC815\uC774 \uBE57\uB098\uAC14\uB2E4)" },
    inconclusive: { label: "\uD310\uC815\uBD88\uAC00", color: "var(--ink-3)", tip: "\uB378\uD0C0 \uC5C6\uC74C(\uBD80\uBAA8 \uC5C6\uC74C/\uD0A4 \uB204\uB77D) \uB610\uB294 \uC6C0\uC9C1\uC784 \uBBF8\uBBF8" },
    untested: { label: "\uBBF8\uAC80\uC99D", color: "var(--ink-3)", tip: "\uC544\uC9C1 \uB2E4\uC74C \uC138\uB300 \uB378\uD0C0\uB85C \uAC80\uC99D\uB418\uC9C0 \uC54A\uC74C" }
  };
  var _SIDE_LABEL = { buy: "\uB9E4\uC218", sell: "\uB9E4\uB3C4", both: "\uACF5\uD1B5" };
  var _METRIC_LABEL = {
    mdd: "MDD",
    profit: "\uCD1D\uC190\uC775",
    daily_avg_trades: "\uC77C\uD3C9\uADE0\uAC70\uB798",
    graded: "graded"
  };
  function _VerdictPill({ verdict }) {
    const meta = _VERDICT_META[verdict] || _VERDICT_META.untested;
    return /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "pill",
        "data-tip": meta.tip,
        style: { color: meta.color, borderColor: meta.color, fontSize: 10 }
      },
      meta.label
    );
  }
  function HypothesisPanel({ state }) {
    const gens = state.generations || [];
    let target = null;
    for (const g of gens) {
      const hyps2 = g.hypotheses || [];
      if (hyps2.length > 0 && (!target || g.gen_no > target.gen_no)) {
        target = g;
      }
    }
    if (!target) return null;
    const hyps = target.hypotheses || [];
    const genLabel = `gen_${String(target.gen_no).padStart(2, "0")}`;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uAC00\uC815 \uB8E8\uD504 \u2014 Hypothesis (", genLabel, ")"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC2E4\uD589\u2192\uBD84\uC11D\u2192\uAC00\uC815\u2192\uAC1C\uC120 \uACFC\uD559\uC801 \uBC29\uBC95 \uB8E8\uD504")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("ul", { style: { margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 } }, hyps.map((h, i) => {
      const dir = (h.expected_direction || 0) > 0 ? "\u2191" : (h.expected_direction || 0) < 0 ? "\u2193" : "\xB7";
      const metric = _METRIC_LABEL[h.target_metric] || h.target_metric || "\u2014";
      const sideLabel = _SIDE_LABEL[h.side] || h.side || "\u2014";
      const obs = h.observed_delta;
      return /* @__PURE__ */ React.createElement("li", { key: i, style: {
        padding: "8px 10px",
        background: "var(--bg-1)",
        border: "1px solid var(--line-1)",
        borderRadius: 6
      } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6, marginBottom: 4, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: "pill", style: { fontSize: 10 } }, sideLabel), /* @__PURE__ */ React.createElement(_VerdictPill, { verdict: h.verdict }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, metric, " ", dir), typeof obs === "number" && /* @__PURE__ */ React.createElement(
        "span",
        {
          className: "mono",
          style: { fontSize: 10.5, color: "var(--ink-2)", marginLeft: "auto" },
          "data-tip": "\uB2E4\uC74C \uC138\uB300 \uC2E4\uCE21 \uB378\uD0C0(\uD310\uC815 \uADFC\uAC70)"
        },
        "\u0394 ",
        obs >= 0 ? "+" : "",
        obs.toFixed(4)
      )), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12, color: "var(--ink-0)", lineHeight: 1.5 } }, h.text || "\u2014"), h.basis && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginTop: 2 } }, "\uADFC\uAC70: ", h.basis));
    }))));
  }
  Object.assign(window, { HypothesisPanel });

  // ../frontend/table.jsx
  var { useState: useState_t, useMemo: useMemo_t } = React;
  function fmtDaily(v) {
    const n = typeof v === "number" ? v : 0;
    return n.toFixed(2);
  }
  function GenerationsTable({ state, mddCap = 15, minDailyTrades = 0.5, onViewCode, onSelectDetail }) {
    var _a, _b;
    const [expanded, setExpanded] = useState_t(/* @__PURE__ */ new Set());
    const [sortKey, setSortKey] = useState_t("gen_desc");
    const rows = useMemo_t(() => {
      const base = [...state.generations || []];
      if (sortKey === "profit_desc") {
        return base.sort((a, b) => (b.profit || 0) - (a.profit || 0));
      }
      return base.reverse();
    }, [state.generations, sortKey]);
    const running = state.status === "running" || state.status === "stopping";
    const currentDisplayGen = running ? state.current_gen + 1 : state.current_gen;
    const toggleExpand = (g) => {
      setExpanded((prev) => {
        const n = new Set(prev);
        if (n.has(g)) n.delete(g);
        else n.add(g);
        return n;
      });
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uC138\uB300 \uC774\uB825 \u2014 Generations"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, rows.length, "\uAC1C \uC138\uB300 \uB204\uC801"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setSortKey("profit_desc"), "data-tip": "total_profit sort" }, "Sort: Total Profit"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setSortKey("gen_desc") }, "Sort: Gen"))), /* @__PURE__ */ React.createElement("div", { style: { maxHeight: 520, overflowY: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "gens" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { width: 68 } }, "\uC138\uB300"), /* @__PURE__ */ React.createElement("th", { style: { width: 70 } }, "\uC0C1\uD0DC"), /* @__PURE__ */ React.createElement("th", { style: { width: 82 } }, "\uB4F1\uAE09\uC810\uC218"), /* @__PURE__ */ React.createElement("th", { style: { width: 64 } }, "Calmar"), /* @__PURE__ */ React.createElement("th", { style: { width: 56 } }, "R\xB2"), /* @__PURE__ */ React.createElement("th", { style: { width: 64 } }, "\uAC8C\uC774\uD2B8"), /* @__PURE__ */ React.createElement("th", { style: { width: 70 } }, "\uAC70\uB798\uC218"), /* @__PURE__ */ React.createElement("th", { style: { width: 84 } }, "\uC77C\uD3C9\uADE0\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", { style: { width: 72 } }, "\uB3D9\uC2DC\uBCF4\uC720"), /* @__PURE__ */ React.createElement("th", { style: { width: 72 } }, "Payoff"), /* @__PURE__ */ React.createElement("th", { style: { width: 80 } }, "Give-back%"), /* @__PURE__ */ React.createElement("th", { style: { width: 76 } }, "MDD"), /* @__PURE__ */ React.createElement("th", { style: { width: 80 } }, "\uC218\uC775\uB960"), /* @__PURE__ */ React.createElement("th", { style: { width: 120 } }, "\uC218\uC775\uAE08"), /* @__PURE__ */ React.createElement("th", null, "\uC0AC\uC720 / \uC804\uB7B5 \uC694\uC9C0"), /* @__PURE__ */ React.createElement("th", { style: { width: 60, textAlign: "center" } }, "\uCF54\uB4DC"), /* @__PURE__ */ React.createElement("th", { style: { width: 76, textAlign: "center" } }, "\uBC31\uD14C\uC0C1\uC138"))), /* @__PURE__ */ React.createElement("tbody", null, running && /* @__PURE__ */ React.createElement("tr", { className: "current" }, /* @__PURE__ */ React.createElement("td", { className: "mono" }, "gen_", String(currentDisplayGen).padStart(2, "0")), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement("span", { className: "pill", style: { color: "var(--amber)", borderColor: "rgba(240,179,90,0.32)", background: "rgba(240,179,90,0.06)" } }, /* @__PURE__ */ React.createElement("span", { className: "dot pulse-dot", style: { background: "var(--amber)", width: 5, height: 5, borderRadius: "50%" } }), "\uC9C4\uD589\uC911")), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-muted" }, "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "gist-cell", style: { color: "var(--amber)" } }, ((_a = state.latest) == null ? void 0 : _a.phase) || "\u2014", " \xB7 ", ((_b = state.latest) == null ? void 0 : _b.last_checkpoint) || ""), /* @__PURE__ */ React.createElement("td", null), /* @__PURE__ */ React.createElement("td", null)), rows.length === 0 && !running && /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", { colSpan: "17", style: { textAlign: "center", padding: 32, color: "var(--ink-3)" } }, "\uC544\uC9C1 \uC2E4\uD589\uB41C \uC138\uB300\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4")), rows.map((g) => {
      var _a2;
      const mddBad = typeof g.mdd === "number" && g.mdd > mddCap;
      const dailyBad = typeof g.daily_avg_trades === "number" && g.daily_avg_trades < minDailyTrades;
      const sparseHoldSuspicious = typeof g.max_hold_count === "number" && g.max_hold_count <= 1 && (g.trade_count || 0) >= 50;
      const isExp = expanded.has(g.gen_no);
      return /* @__PURE__ */ React.createElement("tr", { key: g.gen_no }, /* @__PURE__ */ React.createElement("td", { className: "mono" }, "gen_", String(g.gen_no).padStart(2, "0")), /* @__PURE__ */ React.createElement("td", null, g.status === "error" ? /* @__PURE__ */ React.createElement("span", { className: "pill error" }, "\uC624\uB958") : /* @__PURE__ */ React.createElement("span", { className: "pill success" }, "success")), /* @__PURE__ */ React.createElement("td", { className: `mono ${g.graded_score >= 1 ? "num-pos" : ""}` }, fmtScore(g.graded_score)), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${typeof g.calmar === "number" && g.calmar > 0 ? "num-pos" : "num-muted"}`,
          title: "Calmar \uBE44\uC728 (CAGR/MDD) \u2014 \uC704\uD5D8\uC870\uC815 \uC218\uC775. \uB192\uC744\uC218\uB85D \uC6B0\uC218"
        },
        typeof g.calmar === "number" ? g.calmar.toFixed(2) : "\u2014"
      ), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${typeof g.uptrend_r2 === "number" && g.uptrend_r2 > 0 ? "" : "num-muted"}`,
          title: "\uC6B0\uC0C1\uD5A5 R\xB2 (\uB204\uC801\uC218\uC775 \uACE1\uC120\uC758 \uC9C1\uC120 \uC801\uD569\uB3C4, 0~1) \u2014 1\uC5D0 \uAC00\uAE4C\uC6B8\uC218\uB85D \uAFB8\uC900\uD55C \uC6B0\uC0C1\uD5A5"
        },
        typeof g.uptrend_r2 === "number" ? g.uptrend_r2.toFixed(2) : "\u2014"
      ), /* @__PURE__ */ React.createElement("td", null, g.gate_passed ? /* @__PURE__ */ React.createElement("span", { className: "pill gate-pass" }, "\u2713 \uD1B5\uACFC") : /* @__PURE__ */ React.createElement("span", { className: "pill gate-fail" }, "\u2717")), /* @__PURE__ */ React.createElement("td", { className: "mono" }, (_a2 = g.trade_count) != null ? _a2 : 0), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${dailyBad ? "num-neg" : g.daily_avg_trades >= minDailyTrades ? "num-pos" : ""}`,
          title: "\uC77C\uD3C9\uADE0\uAC70\uB798\uD69F\uC218 (\uAC70\uB798\uC218/\uAC70\uB798\uC77C\uC218) \u2014 \uBE48\uB3C4 \uAC8C\uC774\uD2B8 \uC8FC \uAE30\uC900"
        },
        fmtDaily(g.daily_avg_trades)
      ), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${sparseHoldSuspicious ? "num-neg" : typeof g.max_hold_count === "number" && g.max_hold_count > 0 ? "" : "num-muted"}`,
          title: sparseHoldSuspicious ? "Sparse hold warning: max_hold_count <= 1 with enough trades; compare Backtest Detail CSV peak_holdings. human corridor 6-12" : "\uCD5C\uB300 \uB3D9\uC2DC\uBCF4\uC720 \uC885\uBAA9 \uC218 \u2014 \uB2E4\uC885\uBAA9 \uBD84\uC0B0 \uC9C4\uC785\uC758 1\uCC28 \uADFC\uC0AC(\uD074\uC218\uB85D \uBD84\uC0B0)"
        },
        typeof g.max_hold_count === "number" ? `${g.max_hold_count.toFixed(0)}${sparseHoldSuspicious ? " !" : ""}` : "\u2014"
      ), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${typeof g.payoff_ratio === "number" && g.payoff_ratio > 0 ? "num-pos" : "num-muted"}`,
          title: "\uC190\uC775\uBE44 (\uD3C9\uADE0\uC774\uC775/abs(\uD3C9\uADE0\uC190\uC2E4)) \u2014 1 \uCD08\uACFC\uC77C\uC218\uB85D \uC6B0\uC218"
        },
        typeof g.payoff_ratio === "number" ? g.payoff_ratio.toFixed(2) : "\u2014"
      ), /* @__PURE__ */ React.createElement(
        "td",
        {
          className: `mono ${typeof g.give_back_rate === "number" && g.give_back_rate > 0 ? "num-neg" : "num-muted"}`,
          title: "\uAE30\uD68C \uBC18\uB0A9\uB960 \u2014 MFE \uB3C4\uB2EC \uD6C4 \uC190\uC2E4 \uC804\uD658 \uBE44\uC728. \uB0AE\uC744\uC218\uB85D \uC6B0\uC218"
        },
        typeof g.give_back_rate === "number" ? (g.give_back_rate * 100).toFixed(1) + "%" : "\u2014"
      ), /* @__PURE__ */ React.createElement("td", { className: `mono ${mddBad ? "num-neg" : ""}` }, fmtPct(g.mdd)), /* @__PURE__ */ React.createElement("td", { className: `mono ${typeof g.total_profit_pct !== "number" ? "num-muted" : g.total_profit_pct > 0 ? "num-pos" : g.total_profit_pct < 0 ? "num-neg" : "num-muted"}` }, typeof g.total_profit_pct === "number" ? fmtPct(g.total_profit_pct) : "\u2014"), /* @__PURE__ */ React.createElement("td", { className: `mono ${g.profit > 0 ? "num-pos" : g.profit < 0 ? "num-neg" : "num-muted"}` }, fmtMoney(g.profit)), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(
        "div",
        {
          className: `gist-cell ${isExp ? "expanded" : "truncated"}`,
          onClick: () => toggleExpand(g.gen_no),
          style: { cursor: "pointer" },
          title: isExp ? "\uCD95\uC18C" : "\uD655\uC7A5"
        },
        g.gate_reason && g.gate_reason !== "\uC870\uAC74 \uCDA9\uC871" && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "[", g.gate_reason, "] "),
        /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-0)" } }, g.strategy_gist || "\u2014")
      )), /* @__PURE__ */ React.createElement("td", { style: { textAlign: "center" } }, /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          onClick: () => onViewCode && onViewCode(g),
          "data-tip": "\uB9E4\uC218/\uB9E4\uB3C4 \uC870\uAC74\uC2DD \uCF54\uB4DC \uBCF4\uAE30",
          style: { padding: "3px 8px", fontSize: 11 }
        },
        "</>"
      )), /* @__PURE__ */ React.createElement("td", { style: { textAlign: "center" } }, /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          onClick: () => onSelectDetail && onSelectDetail(g.gen_no),
          "data-tip": "\uC774 \uC138\uB300\uB97C \uBC31\uD14C \uC0C1\uC138 \uCC28\uD2B8\uC5D0 \uD45C\uC2DC",
          style: { padding: "3px 8px", fontSize: 11 }
        },
        "\u{1F4CA}"
      )));
    })))));
  }
  Object.assign(window, { GenerationsTable });

  // ../frontend/cards.jsx
  var { useState: useState_card, useEffect: useEffect_card } = React;
  function BestCard({ best, onViewCode }) {
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { borderColor: best ? "rgba(76,214,179,0.25)" : void 0 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "Best (graded)"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uD604\uC7AC \uB204\uC801 \uCD5C\uACE0 \uC810\uC218")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !best ? /* @__PURE__ */ React.createElement("div", { style: { color: "var(--ink-3)", fontSize: 12, padding: "12px 0" } }, "\uC544\uC9C1 \uD3C9\uAC00\uB41C \uC138\uB300\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: 14, marginBottom: 14 } }, /* @__PURE__ */ React.createElement("span", { className: "stat-value lg mono", style: { color: "var(--teal)" } }, fmtScore(best.graded_score)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 12, color: "var(--ink-2)" } }, "gen_", String(best.gen).padStart(2, "0")), best.gate_passed && /* @__PURE__ */ React.createElement("span", { className: "pill gate-pass", style: { marginLeft: "auto" } }, "\u2713 \uAC8C\uC774\uD2B8")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8, marginBottom: 10 } }, /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uC218", value: best.buy_name }), /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uB3C4", value: best.sell_name })), onViewCode && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => onViewCode(best.gen),
        style: { width: "100%", justifyContent: "center" }
      },
      "</> \uCF54\uB4DC \uBCF4\uAE30 \u2014 gen_",
      String(best.gen).padStart(2, "0")
    ))));
  }
  function WinnerCard({ winner, onApprove, onViewCode }) {
    if (!winner) {
      return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { borderStyle: "dashed", borderColor: "var(--line-2)" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Winner \u2014 \uAC8C\uC774\uD2B8 \uD1B5\uACFC \uB300\uAE30")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { color: "var(--ink-3)", fontSize: 12 } }, "\uD558\uB4DC \uAC8C\uC774\uD2B8\uB97C \uD1B5\uACFC\uD55C \uC804\uB7B5\uC774 \uC544\uC9C1 \uC5C6\uC2B5\uB2C8\uB2E4.", /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6, fontSize: 11, color: "var(--ink-3)" } }, "target_score \uC774\uC0C1 + MDD \uC0C1\uD55C \uC774\uB0B4 + \uCD5C\uC18C \uAC70\uB798\uC218 \uC774\uC0C1")));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: {
      borderColor: "rgba(165,148,255,0.35)",
      background: "linear-gradient(180deg, rgba(165,148,255,0.06), var(--bg-1) 70%)"
    } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd", style: { background: "rgba(165,148,255,0.08)", borderBottom: "1px solid rgba(165,148,255,0.18)" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\u{1F3C6} Winner \u2014 \uD558\uB4DC \uAC8C\uC774\uD2B8 \uD1B5\uACFC"), /* @__PURE__ */ React.createElement("span", { className: "badge", style: { color: "var(--violet)", borderColor: "rgba(165,148,255,0.32)", background: "rgba(165,148,255,0.08)" } }, "gen_", String(winner.gen).padStart(2, "0"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: 14, marginBottom: 14 } }, /* @__PURE__ */ React.createElement("span", { className: "stat-value lg mono", style: { color: "var(--violet)" } }, fmtScore(winner.score)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "graded_score")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8, marginBottom: 14 } }, /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uC218", value: winner.buy_name }), /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uB3C4", value: winner.sell_name })), onViewCode && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => onViewCode(winner.gen),
        style: { width: "100%", justifyContent: "center", marginBottom: 10 }
      },
      "</> \uC804\uCCB4 \uCF54\uB4DC \uAC80\uD1A0"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn primary lg",
        style: { width: "100%", justifyContent: "center" },
        onClick: onApprove
      },
      /* @__PURE__ */ React.createElement("span", null, "\uC2E4\uC804 \uC804\uB7B5\uC73C\uB85C \uC2B9\uC778 \xB7 \uB0B4\uBCF4\uB0B4\uAE30"),
      /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12, opacity: 0.8 } }, "\u2192")
    ), /* @__PURE__ */ React.createElement("p", { style: { fontSize: 11, color: "var(--ink-2)", marginTop: 10, lineHeight: 1.55, textAlign: "center" } }, "\uC2B9\uC778 \uC2DC \uC6B4\uC601\uC6A9 ", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-1)" } }, "strategy.db"), "\uB85C export\uB429\uB2C8\uB2E4. \uCDE8\uC18C\uD560 \uC218 \uC5C6\uC73C\uB2C8 \uC2E0\uC911\uD788 \uC9C4\uD589\uD558\uC138\uC694.")));
  }
  function MergedBestWinnerCard({ best, winner, onApprove, onViewCode }) {
    const gen = winner.gen;
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: {
      borderColor: "rgba(165,148,255,0.35)",
      background: "linear-gradient(180deg, rgba(165,148,255,0.06), var(--bg-1) 70%)"
    } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd", style: { background: "rgba(165,148,255,0.08)", borderBottom: "1px solid rgba(165,148,255,0.18)" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\u{1F3C6} Best = Winner \u2014 \uAC8C\uC774\uD2B8 \uD1B5\uACFC \uCD5C\uACE0 \uC138\uB300"), /* @__PURE__ */ React.createElement("span", { className: "badge", style: { color: "var(--violet)", borderColor: "rgba(165,148,255,0.32)", background: "rgba(165,148,255,0.08)" } }, "gen_", String(gen).padStart(2, "0"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "baseline", gap: 14, marginBottom: 4, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: "stat-value lg mono", style: { color: "var(--teal)" } }, fmtScore(best.graded_score)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "graded"), /* @__PURE__ */ React.createElement("span", { className: "stat-value mono", style: { color: "var(--violet)", marginLeft: 6 } }, fmtScore(winner.score)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "winner_score"), /* @__PURE__ */ React.createElement("span", { className: "pill gate-pass", style: { marginLeft: "auto" } }, "\u2713 \uAC8C\uC774\uD2B8")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8, margin: "12px 0 14px" } }, /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uC218", value: winner.buy_name }), /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uB3C4", value: winner.sell_name })), onViewCode && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => onViewCode(gen),
        style: { width: "100%", justifyContent: "center", marginBottom: 10 }
      },
      "</> \uC804\uCCB4 \uCF54\uB4DC \uAC80\uD1A0 \u2014 gen_",
      String(gen).padStart(2, "0")
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn primary lg",
        style: { width: "100%", justifyContent: "center" },
        onClick: onApprove
      },
      /* @__PURE__ */ React.createElement("span", null, "\uC2E4\uC804 \uC804\uB7B5\uC73C\uB85C \uC2B9\uC778 \xB7 \uB0B4\uBCF4\uB0B4\uAE30"),
      /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12, opacity: 0.8 } }, "\u2192")
    ), /* @__PURE__ */ React.createElement("p", { style: { fontSize: 11, color: "var(--ink-2)", marginTop: 10, lineHeight: 1.55, textAlign: "center" } }, "\uC2B9\uC778 \uC2DC \uC6B4\uC601\uC6A9 ", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-1)" } }, "strategy.db"), "\uB85C export\uB429\uB2C8\uB2E4. \uCDE8\uC18C\uD560 \uC218 \uC5C6\uC73C\uB2C8 \uC2E0\uC911\uD788 \uC9C4\uD589\uD558\uC138\uC694.")));
  }
  function NameRow({ label, value }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "7px 10px",
      background: "var(--bg-0)",
      border: "1px solid var(--line-1)",
      borderRadius: 5
    } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10.5, letterSpacing: ".14em", textTransform: "uppercase", color: "var(--ink-2)", width: 36 } }, label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 12, color: "var(--ink-0)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, value || "\u2014"));
  }
  function ApprovalDialog({ winner, onClose, onConfirm }) {
    const [userBuy, setUserBuy] = useState_card("");
    const [userSell, setUserSell] = useState_card("");
    const [confirmText, setConfirmText] = useState_card("");
    useEffect_card(() => {
      if (winner) {
        const stripGen = (n) => (n || "").replace(/_g\d+$/, "");
        setUserBuy(stripGen(winner.buy_name) || "");
        setUserSell(stripGen(winner.sell_name) || "");
        setConfirmText("");
      }
    }, [winner]);
    if (!winner) return null;
    const canSubmit = userBuy.trim() && userSell.trim() && confirmText.trim() === "\uC2B9\uC778";
    return /* @__PURE__ */ React.createElement("div", { className: "modal-bd", onMouseDown: (e) => {
      if (e.target === e.currentTarget) onClose();
    } }, /* @__PURE__ */ React.createElement("div", { className: "modal", onMouseDown: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "modal-hd" }, /* @__PURE__ */ React.createElement("h2", null, "\uC2E4\uC804 \uC804\uB7B5 \uC2B9\uC778 \xB7 \uB0B4\uBCF4\uB0B4\uAE30", /* @__PURE__ */ React.createElement("span", { className: "sub" }, "gen_", String(winner.gen).padStart(2, "0"), " \xB7 score ", fmtScore(winner.score))), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose }, "\uB2EB\uAE30")), /* @__PURE__ */ React.createElement("div", { className: "modal-bd-content" }, /* @__PURE__ */ React.createElement("div", { className: "alert-danger", style: { marginBottom: 18 } }, /* @__PURE__ */ React.createElement("strong", null, "\u26A0 \uC6B4\uC601 DB \uBCC0\uACBD \uC791\uC5C5"), " \u2014 \uC774 \uC6B0\uC2B9 \uC804\uB7B5\uC744 \uC6B4\uC601\uC6A9 ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "strategy.db"), "\uC5D0", /* @__PURE__ */ React.createElement("span", { className: "mono" }, " live-deploy gate"), "\uB85C \uB0B4\uBCF4\uB0C5\uB2C8\uB2E4. \uC2E4\uAC70\uB798 \uC790\uB3D9\uB9E4\uB9E4\uC5D0\uC11C \uC989\uC2DC \uC0AC\uC6A9 \uAC00\uB2A5\uD558\uAC8C \uB429\uB2C8\uB2E4."), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { marginBottom: 14, fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5 } }, "\uB3D9\uC120: \uC99D\uAC70 \u2192 ", /* @__PURE__ */ React.createElement("b", null, "\uB0B4\uBCF4\uB0B4\uAE30 \uC2B9\uC778"), "(\uC774 \uB2E8\uACC4 \xB7 WS ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "final_approval"), ") \u2192", /* @__PURE__ */ React.createElement("b", null, " \uACB0\uC815 \uC774\uB825 \u2192 \uC6B4\uC6A9 \uACB0\uC815"), " \uD0ED\uC5D0\uC11C \uCC44\uD0DD \uC0AC\uC720 \uAE30\uB85D(REST ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "/record_decision"), ", append-only)."), /* @__PURE__ */ React.createElement("div", { className: "group" }, /* @__PURE__ */ React.createElement("div", { className: "group-title" }, "\uC6B0\uC2B9 \uC804\uB7B5 \uC6D0\uBCF8"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 6 } }, /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uC218", value: winner.buy_name }), /* @__PURE__ */ React.createElement(NameRow, { label: "\uB9E4\uB3C4", value: winner.sell_name }))), /* @__PURE__ */ React.createElement("div", { className: "group" }, /* @__PURE__ */ React.createElement("div", { className: "group-title" }, "\uC6B4\uC601 DB \uC800\uC7A5\uBA85 \u2014 \uC0AC\uC6A9\uC790 \uC9C0\uC815"), /* @__PURE__ */ React.createElement("div", { className: "field-row" }, /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uC218 \uC804\uB7B5 \uC774\uB984"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: userBuy,
        onChange: (e) => setUserBuy(e.target.value),
        placeholder: "\uC608: VWAP_MOMENTUM_v3"
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "help" }, "\uC6B4\uC601 \uC2DC\uC2A4\uD15C\uC5D0\uC11C \uC774 \uC774\uB984\uC73C\uB85C \uCC38\uC870\uB429\uB2C8\uB2E4")), /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uB3C4 \uC804\uB7B5 \uC774\uB984"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: userSell,
        onChange: (e) => setUserSell(e.target.value),
        placeholder: "\uC608: ATR_TRAILING_v3"
      }
    ), /* @__PURE__ */ React.createElement("span", { className: "help" }, "\uC911\uBCF5 \uC2DC \uB36E\uC5B4\uC4F0\uAE30 \uB429\uB2C8\uB2E4")))), /* @__PURE__ */ React.createElement("div", { className: "group" }, /* @__PURE__ */ React.createElement("div", { className: "group-title" }, "\uCD5C\uC885 \uD655\uC778"), /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uC544\uB798 \uC785\uB825\uB780\uC5D0 ", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--amber)" } }, "\uC2B9\uC778"), " \uC774\uB77C\uACE0 \uC785\uB825\uD558\uC138\uC694"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: confirmText,
        onChange: (e) => setConfirmText(e.target.value),
        placeholder: "\uC2B9\uC778",
        autoFocus: true
      }
    )))), /* @__PURE__ */ React.createElement("div", { className: "modal-ft" }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost", onClick: onClose }, "\uCDE8\uC18C"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn primary",
        disabled: !canSubmit,
        onClick: () => onConfirm({ userBuy: userBuy.trim(), userSell: userSell.trim() })
      },
      "\uC2B9\uC778 \xB7 \uB0B4\uBCF4\uB0B4\uAE30"
    ))));
  }
  Object.assign(window, { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog });

  // ../frontend/strategy-inspector.jsx
  var { useState: useState_si, useEffect: useEffect_si, useMemo: useMemo_si } = React;
  function asList(value) {
    return Array.isArray(value) ? value : [];
  }
  function safeText(value, fallback = "-") {
    if (value === null || value === void 0 || value === "") return fallback;
    return String(value);
  }
  function diffClass(line) {
    if (line.startsWith("+") && !line.startsWith("+++")) return "add";
    if (line.startsWith("-") && !line.startsWith("---")) return "del";
    if (line.startsWith("@@")) return "meta";
    return "";
  }
  function PromptRow({ prompt }) {
    const features = prompt && prompt.injected_features ? prompt.injected_features : {};
    return /* @__PURE__ */ React.createElement("div", { className: "strategy-prompt-row" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-prompt-meta" }, /* @__PURE__ */ React.createElement("span", { className: "pill" }, safeText(prompt.kind)), /* @__PURE__ */ React.createElement("span", null, "attempt=", safeText(prompt.attempt)), /* @__PURE__ */ React.createElement("span", null, "model=", safeText(prompt.model)), /* @__PURE__ */ React.createElement("span", null, "total_tokens=", safeText(prompt.total_tokens, "0"))), /* @__PURE__ */ React.createElement("div", { className: "strategy-prompt-head" }, "user_text_head: ", safeText(prompt.user_text_head, "not stored")), /* @__PURE__ */ React.createElement("pre", { className: "strategy-json" }, "injected_features ", JSON.stringify(features, null, 2)));
  }
  function DiffBlock({ title, lines }) {
    const rows = asList(lines);
    if (!rows.length) {
      return /* @__PURE__ */ React.createElement("div", { className: "strategy-empty" }, title, ": no diff lines");
    }
    return /* @__PURE__ */ React.createElement("div", { className: "strategy-diff-block" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-section-title" }, title), /* @__PURE__ */ React.createElement("pre", { className: "strategy-diff-lines" }, rows.map((line, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: diffClass(line) }, line))));
  }
  function CodeBlock({ title, code }) {
    const text = code || "";
    if (!text.trim()) {
      return /* @__PURE__ */ React.createElement("div", { className: "strategy-empty" }, title, ": no strategy code loaded");
    }
    return /* @__PURE__ */ React.createElement("div", { className: "strategy-diff-block" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-section-title" }, title), /* @__PURE__ */ React.createElement("pre", { className: "strategy-diff-lines" }, text));
  }
  function buildAiContext({ generation, runId, diffPayload, promptsPayload, buyCode, sellCode }) {
    const prompts = asList(promptsPayload && promptsPayload.prompts);
    const parts = [
      "STOM strategy research context",
      `run_id: ${safeText(runId)}`,
      `gen_no: ${safeText(generation && generation.gen_no)}`,
      `status: ${safeText(generation && generation.status)}`,
      `graded_score: ${safeText(generation && generation.graded_score)}`,
      `gate_passed: ${safeText(generation && generation.gate_passed)}`,
      `buy_name: ${safeText(generation && generation.buy_name)}`,
      `sell_name: ${safeText(generation && generation.sell_name)}`,
      `buy_code_lines: ${(buyCode || "").split("\n").filter(Boolean).length}`,
      `sell_code_lines: ${(sellCode || "").split("\n").filter(Boolean).length}`,
      `diff_base_gen: ${safeText(diffPayload && diffPayload.base_gen)}`,
      `diff_reason: ${safeText(diffPayload && diffPayload.reason, "available")}`,
      `prompt_count: ${prompts.length}`,
      `prompt_reason: ${safeText(promptsPayload && promptsPayload.reason, "available")}`,
      "buy_code:",
      buyCode || "(empty)",
      "sell_code:",
      sellCode || "(empty)",
      "Forbidden actions: do not approve or deploy from this copied context."
    ];
    return parts.join("\n");
  }
  function StrategyInspectorTabs({ generation, runId, baseUrl, buyCode, sellCode }) {
    const [tab, setTab] = useState_si("diff");
    const [diffPayload, setDiffPayload] = useState_si(null);
    const [promptsPayload, setPromptsPayload] = useState_si(null);
    const [loading, setLoading] = useState_si(false);
    const [diffError, setDiffError] = useState_si("");
    const [promptsError, setPromptsError] = useState_si("");
    const [copied, setCopied] = useState_si(false);
    const genNo = generation && generation.gen_no;
    useEffect_si(() => {
      setDiffPayload(null);
      setPromptsPayload(null);
      setDiffError("");
      setPromptsError("");
      if (!generation || !baseUrl || !runId || genNo === void 0 || genNo === null) {
        setLoading(false);
        return;
      }
      let cancelled = false;
      let pending = 2;
      const finishOne = () => {
        pending -= 1;
        if (!cancelled && pending <= 0) setLoading(false);
      };
      setLoading(true);
      const params = `run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}&base_gen=previous`;
      fetch(`${baseUrl}/strategy_diff?${params}`, { signal: AbortSignal.timeout(3e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((diff) => {
        if (!cancelled) setDiffPayload(diff || {});
      }).catch((e) => {
        if (!cancelled) setDiffError("strategy_diff route unavailable: " + String(e));
      }).finally(finishOne);
      fetch(
        `${baseUrl}/prompts?run_id=${encodeURIComponent(runId)}&gen_no=${encodeURIComponent(genNo)}`,
        { signal: AbortSignal.timeout(3e3) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((prompts2) => {
        if (!cancelled) setPromptsPayload(prompts2 || {});
      }).catch((e) => {
        if (!cancelled) setPromptsError("prompts route unavailable: " + String(e));
      }).finally(finishOne);
      return () => {
        cancelled = true;
      };
    }, [generation, baseUrl, runId, genNo]);
    const prompts = asList(promptsPayload && promptsPayload.prompts);
    const aiContext = useMemo_si(() => buildAiContext({
      generation,
      runId,
      diffPayload,
      promptsPayload,
      buyCode,
      sellCode
    }), [generation, runId, diffPayload, promptsPayload, buyCode, sellCode]);
    const copyAiContext = async () => {
      try {
        await navigator.clipboard.writeText(aiContext);
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      } catch (e) {
      }
    };
    return /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector-tabs" }, /* @__PURE__ */ React.createElement("button", { className: tab === "diff" ? "active" : "", onClick: () => setTab("diff") }, "Previous Diff"), /* @__PURE__ */ React.createElement("button", { className: tab === "prompts" ? "active" : "", onClick: () => setTab("prompts") }, "Prompt Timeline"), /* @__PURE__ */ React.createElement("button", { className: tab === "context" ? "active" : "", onClick: () => setTab("context") }, "AI Context"), /* @__PURE__ */ React.createElement("button", { className: tab === "code" ? "active" : "", onClick: () => setTab("code") }, "Current Code")), loading && /* @__PURE__ */ React.createElement("div", { className: "strategy-empty" }, "loading strategy inspector..."), diffError && /* @__PURE__ */ React.createElement("div", { className: "strategy-empty danger" }, diffError), promptsError && /* @__PURE__ */ React.createElement("div", { className: "strategy-empty danger" }, promptsError), !loading && tab === "diff" && /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector-body" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-kpis" }, /* @__PURE__ */ React.createElement("span", null, "base_gen=", safeText(diffPayload && diffPayload.base_gen)), /* @__PURE__ */ React.createElement("span", null, "reason=", safeText(diffPayload && diffPayload.reason, "available")), /* @__PURE__ */ React.createElement("span", null, "no_previous_generation=", String((diffPayload && diffPayload.reason) === "no_previous_generation"))), /* @__PURE__ */ React.createElement(DiffBlock, { title: "buy_diff", lines: diffPayload && diffPayload.buy_diff }), /* @__PURE__ */ React.createElement(DiffBlock, { title: "sell_diff", lines: diffPayload && diffPayload.sell_diff })), !loading && tab === "prompts" && /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector-body" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-kpis" }, /* @__PURE__ */ React.createElement("span", null, "prompt_count=", prompts.length), /* @__PURE__ */ React.createElement("span", null, "no-record reason=", safeText(promptsPayload && promptsPayload.reason, "available"))), prompts.length ? prompts.map((prompt, i) => /* @__PURE__ */ React.createElement(PromptRow, { key: `${prompt.kind || "prompt"}-${prompt.attempt || i}`, prompt })) : /* @__PURE__ */ React.createElement("div", { className: "strategy-empty" }, "no prompt records for this generation. no-record reason: ", safeText(promptsPayload && promptsPayload.reason, "prompt_logging_not_enabled_or_no_records"))), !loading && tab === "context" && /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector-body" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", gap: 8, alignItems: "center" } }, /* @__PURE__ */ React.createElement("div", { className: "strategy-section-title" }, "Safe current-run summary"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: copyAiContext }, copied ? "copied" : "copy AI context")), /* @__PURE__ */ React.createElement("pre", { className: "strategy-context" }, aiContext)), tab === "code" && /* @__PURE__ */ React.createElement("div", { className: "strategy-inspector-body" }, /* @__PURE__ */ React.createElement("div", { className: "strategy-section-title" }, "Current Strategy Code"), /* @__PURE__ */ React.createElement(CodeBlock, { title: "buy_code", code: buyCode }), /* @__PURE__ */ React.createElement(CodeBlock, { title: "sell_code", code: sellCode })));
  }
  Object.assign(window, { StrategyInspectorTabs });

  // ../frontend/code-viewer.jsx
  var { useState: useState_cv, useMemo: useMemo_cv, useEffect: useEffect_cv } = React;
  function highlightPython(code) {
    if (!code) return [];
    const lines = code.split("\n");
    const KEYWORDS = /* @__PURE__ */ new Set([
      "def",
      "return",
      "if",
      "elif",
      "else",
      "and",
      "or",
      "not",
      "for",
      "while",
      "in",
      "is",
      "None",
      "True",
      "False",
      "import",
      "from",
      "as",
      "pass",
      "break",
      "continue",
      "lambda",
      "try",
      "except",
      "finally",
      "with",
      "yield",
      "max",
      "min",
      "abs",
      "len"
    ]);
    const out = [];
    for (let ln = 0; ln < lines.length; ln++) {
      const line = lines[ln];
      const parts = [];
      let i = 0;
      while (i < line.length) {
        const ch = line[i];
        if (ch === "#") {
          parts.push({ cls: "tok-com", t: line.slice(i) });
          break;
        }
        if (ch === '"' || ch === "'") {
          const q = ch;
          let j = i + 1;
          while (j < line.length && line[j] !== q) j++;
          parts.push({ cls: "tok-str", t: line.slice(i, j + 1) });
          i = j + 1;
          continue;
        }
        if (/[0-9]/.test(ch) && (i === 0 || /[^a-zA-Z_]/.test(line[i - 1]))) {
          let j = i;
          while (j < line.length && /[0-9_.e+-]/.test(line[j])) j++;
          parts.push({ cls: "tok-num", t: line.slice(i, j) });
          i = j;
          continue;
        }
        if (/[a-zA-Z_]/.test(ch)) {
          let j = i;
          while (j < line.length && /[a-zA-Z0-9_]/.test(line[j])) j++;
          const word = line.slice(i, j);
          let k = j;
          while (k < line.length && line[k] === " ") k++;
          if (KEYWORDS.has(word)) parts.push({ cls: "tok-kw", t: word });
          else if (line[k] === "(") parts.push({ cls: "tok-fn", t: word });
          else parts.push({ cls: "", t: word });
          i = j;
          continue;
        }
        parts.push({ cls: "", t: ch });
        i++;
      }
      out.push({ ln: ln + 1, parts });
    }
    return out;
  }
  function CvCodeBlock({ code }) {
    const highlighted = useMemo_cv(() => highlightPython(code), [code]);
    if (!code) return /* @__PURE__ */ React.createElement("div", { className: "code-block", style: { color: "var(--ink-3)" } }, "unavailable: strategy code not found for this generation.");
    return /* @__PURE__ */ React.createElement("pre", { className: "code-block" }, highlighted.map((row, i) => /* @__PURE__ */ React.createElement("div", { key: i }, /* @__PURE__ */ React.createElement("span", { className: "ln" }, row.ln), row.parts.map((p, j) => /* @__PURE__ */ React.createElement("span", { key: j, className: p.cls }, p.t)))));
  }
  function CodeViewer({ generation, onClose, runId, baseUrl }) {
    const [tab, setTab] = useState_cv("buy");
    const [copied, setCopied] = useState_cv(false);
    const [expandedCodeView, setExpandedCodeView] = useState_cv(false);
    const [fetched, setFetched] = useState_cv(null);
    const [loading, setLoading] = useState_cv(false);
    const [fetchErr, setFetchErr] = useState_cv(null);
    const hasInline = Boolean(generation && (generation.buy_code || generation.sell_code));
    useEffect_cv(() => {
      setFetched(null);
      setFetchErr(null);
      if (!generation || hasInline || !baseUrl || !runId) return;
      const gen = generation.gen_no;
      let cancelled = false;
      setLoading(true);
      fetch(
        `${baseUrl}/strategy_code?run=${encodeURIComponent(runId)}&gen=${gen}`,
        { signal: AbortSignal.timeout(2500) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        if (!cancelled) setFetched({ buy_code: j.buy_code || "", sell_code: j.sell_code || "" });
      }).catch((e) => {
        if (!cancelled) setFetchErr(String(e));
      }).finally(() => {
        if (!cancelled) setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }, [generation, hasInline, baseUrl, runId]);
    if (!generation) return null;
    const isErr = generation.status === "error";
    const buyCode = generation.buy_code || fetched && fetched.buy_code || "";
    const sellCode = generation.sell_code || fetched && fetched.sell_code || "";
    const code = tab === "buy" ? buyCode : sellCode;
    const name = tab === "buy" ? generation.buy_name : generation.sell_name;
    const modalClass = `modal code-viewer-modal ${expandedCodeView ? "code-viewer-expanded" : ""}`;
    const modalStyle = {
      width: expandedCodeView ? "min(1320px, calc(100vw - 20px))" : "min(960px, calc(100vw - 32px))",
      maxHeight: expandedCodeView ? "calc(100vh - 18px)" : void 0
    };
    const onCopy = async () => {
      try {
        await navigator.clipboard.writeText(code || "");
        setCopied(true);
        setTimeout(() => setCopied(false), 1400);
      } catch (e) {
      }
    };
    return /* @__PURE__ */ React.createElement("div", { className: "modal-bd", onMouseDown: (e) => {
      if (e.target === e.currentTarget) onClose();
    } }, /* @__PURE__ */ React.createElement("div", { className: modalClass, style: modalStyle, onMouseDown: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "modal-hd" }, /* @__PURE__ */ React.createElement("h2", null, "\uC804\uB7B5 \uCF54\uB4DC \uBCF4\uAE30", /* @__PURE__ */ React.createElement("span", { className: "sub" }, "gen_", String(generation.gen_no).padStart(2, "0"), " \xB7 score ", fmtScore(generation.graded_score), generation.gate_passed && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)", marginLeft: 8 } }, "\u2713 \uAC8C\uC774\uD2B8 \uD1B5\uACFC"), isErr && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)", marginLeft: 8 } }, "\u26A0 \uC624\uB958"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        "data-testid": "code-viewer-height-toggle",
        "data-tip": expandedCodeView ? "\uC870\uAC74\uC2DD \uBCF4\uAE30 \uCC3D\uC744 \uAE30\uBCF8 \uB192\uC774\uB85C \uC904\uC785\uB2C8\uB2E4." : "\uC870\uAC74\uC2DD \uBCF4\uAE30 \uCC3D\uC744 \uC138\uB85C\uB85C \uD655\uB300\uD569\uB2C8\uB2E4.",
        "aria-pressed": expandedCodeView,
        onClick: () => setExpandedCodeView(!expandedCodeView)
      },
      expandedCodeView ? "\uAE30\uBCF8 \uB192\uC774" : "\uC138\uB85C \uD655\uB300"
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onCopy }, copied ? "\uBCF5\uC0AC\uB428 \u2713" : "\uBCF5\uC0AC"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose }, "\uB2EB\uAE30"))), /* @__PURE__ */ React.createElement("div", { className: "code-tabs" }, /* @__PURE__ */ React.createElement(
      "div",
      {
        className: `code-tab ${tab === "buy" ? "active" : ""}`,
        onClick: () => setTab("buy")
      },
      /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)" } }, "\u25CF"),
      " \uB9E4\uC218 \u2014 ",
      generation.buy_name || "\u2014"
    ), /* @__PURE__ */ React.createElement(
      "div",
      {
        className: `code-tab ${tab === "sell" ? "active" : ""}`,
        onClick: () => setTab("sell")
      },
      /* @__PURE__ */ React.createElement("span", { style: { color: "var(--amber)" } }, "\u25CF"),
      " \uB9E4\uB3C4 \u2014 ",
      generation.sell_name || "\u2014"
    ), /* @__PURE__ */ React.createElement("div", { style: { marginLeft: "auto", padding: "8px 16px", fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" } }, (code || "").split("\n").length, " lines")), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" } }, loading ? /* @__PURE__ */ React.createElement("div", { className: "code-block", style: { color: "var(--ink-3)" } }, "\uCF54\uB4DC \uBD88\uB7EC\uC624\uB294 \uC911\u2026") : fetchErr && !code ? /* @__PURE__ */ React.createElement("div", { className: "code-block", style: { color: "var(--red)" } }, "\uCF54\uB4DC \uC870\uD68C \uC2E4\uD328: ", fetchErr) : /* @__PURE__ */ React.createElement(CvCodeBlock, { code })), /* @__PURE__ */ React.createElement(
      StrategyInspectorTabs,
      {
        generation,
        runId,
        baseUrl,
        buyCode,
        sellCode
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "modal-ft", style: { justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 11, color: "var(--ink-2)", fontFamily: "var(--mono)" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "\uC694\uC9C0:"), " ", generation.strategy_gist || "\u2014")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "\uAC70\uB798 ", generation.trade_count, " \xB7 MDD ", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, fmtPct(generation.mdd)), " \xB7 \uC190\uC775 ", /* @__PURE__ */ React.createElement("span", { className: generation.profit > 0 ? "num-pos" : "num-neg" }, fmtMoney(generation.profit))), /* @__PURE__ */ React.createElement("button", { className: "btn ghost", onClick: onClose }, "\uB2EB\uAE30")))));
  }
  Object.assign(window, { CodeViewer, CvCodeBlock, highlightPython });

  // ../frontend/settings.jsx
  var { useState: useState_s, useMemo: useMemo_s, useEffect: useEffect_s } = React;
  function SettingsModal({ open, onClose, onStart, configSpec, disabled }) {
    const [values, setValues] = useState_s({});
    useEffect_s(() => {
      if (!open) return;
      const init = {};
      for (const f of configSpec) init[f.name] = f.default;
      setValues(init);
    }, [open, configSpec]);
    const groups = useMemo_s(() => {
      const g = {};
      const order = ["\uBAA9\uD45C/\uC81C\uC57D", "\uD3C9\uAC00 \uC2A4\uCF54\uD504", "\uACFC\uC801\uD569 \uAC00\uB4DC", "AI"];
      for (const f of configSpec) {
        const grp = f.group || "\uAE30\uD0C0";
        if (!g[grp]) g[grp] = [];
        g[grp].push(f);
      }
      const sorted = [];
      for (const k of order) if (g[k]) sorted.push([k, g[k]]);
      for (const [k, v] of Object.entries(g)) if (!order.includes(k)) sorted.push([k, v]);
      return sorted;
    }, [configSpec]);
    if (!open) return null;
    const set = (name, v) => setValues((prev) => ({ ...prev, [name]: v }));
    const renderField = (f) => {
      const val = values[f.name];
      const id = `cfg-${f.name}`;
      if (f.type === "boolean") {
        return /* @__PURE__ */ React.createElement("div", { key: f.name, className: "field", style: { gridColumn: "1 / -1" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 12 } }, /* @__PURE__ */ React.createElement(
          "button",
          {
            type: "button",
            className: `toggle ${val ? "on" : ""}`,
            onClick: () => set(f.name, !val),
            "aria-label": f.label
          }
        ), /* @__PURE__ */ React.createElement(
          "label",
          {
            htmlFor: id,
            style: { marginBottom: 0, cursor: "pointer" },
            onClick: () => set(f.name, !val)
          },
          f.label
        ), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: "auto", fontSize: 11, color: val ? "var(--teal)" : "var(--ink-3)" } }, val ? "ON" : "OFF")), f.help && /* @__PURE__ */ React.createElement("span", { className: "help", style: { paddingLeft: 46 } }, f.help));
      }
      if (f.type === "select" && f.options) {
        return /* @__PURE__ */ React.createElement("div", { key: f.name, className: "field" }, /* @__PURE__ */ React.createElement("label", { htmlFor: id }, f.label), /* @__PURE__ */ React.createElement(
          "select",
          {
            id,
            className: "select",
            value: val != null ? val : "",
            onChange: (e) => set(f.name, e.target.value)
          },
          f.options.map((opt) => /* @__PURE__ */ React.createElement("option", { key: opt, value: opt }, opt))
        ), f.help && /* @__PURE__ */ React.createElement("span", { className: "help" }, f.help));
      }
      return /* @__PURE__ */ React.createElement("div", { key: f.name, className: "field" }, /* @__PURE__ */ React.createElement("label", { htmlFor: id }, f.label), /* @__PURE__ */ React.createElement(
        "input",
        {
          id,
          className: "input",
          type: f.type === "number" ? "number" : "text",
          value: val != null ? val : "",
          step: f.type === "number" ? "any" : void 0,
          onChange: (e) => {
            const v = f.type === "number" ? e.target.value === "" ? "" : Number(e.target.value) : e.target.value;
            set(f.name, v);
          }
        }
      ), f.help && /* @__PURE__ */ React.createElement("span", { className: "help" }, f.help));
    };
    const submit = () => {
      const clean = {};
      for (const f of configSpec) {
        let v = values[f.name];
        if (v === "" || v === null || v === void 0) v = f.default;
        clean[f.name] = v;
      }
      onStart(clean);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "modal-bd", onMouseDown: (e) => {
      if (e.target === e.currentTarget) onClose();
    } }, /* @__PURE__ */ React.createElement("div", { className: "modal", style: { width: "min(820px, calc(100vw - 32px))" }, onMouseDown: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "modal-hd" }, /* @__PURE__ */ React.createElement("h2", null, "\uC9C4\uD654 \uC2DC\uC791 \uC124\uC815", /* @__PURE__ */ React.createElement("span", { className: "sub" }, "\uBAA9\uD45C \xB7 \uC2A4\uCF54\uD504 \xB7 AI \uD30C\uB77C\uBBF8\uD130")), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose }, "\uB2EB\uAE30")), /* @__PURE__ */ React.createElement("div", { className: "modal-bd-content" }, groups.map(([grp, fields]) => /* @__PURE__ */ React.createElement("div", { key: grp, className: "group" }, /* @__PURE__ */ React.createElement("div", { className: "group-title" }, grp), /* @__PURE__ */ React.createElement("div", { className: "field-row", style: {
      gridTemplateColumns: fields.length === 1 ? "1fr" : "1fr 1fr"
    } }, fields.map(renderField))))), /* @__PURE__ */ React.createElement("div", { className: "modal-ft" }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost", onClick: onClose }, "\uCDE8\uC18C"), /* @__PURE__ */ React.createElement("button", { className: "btn primary lg", onClick: submit, disabled }, "\u25B8 \uC9C4\uD654 \uC2DC\uC791"))));
  }
  Object.assign(window, { SettingsModal });

  // ../frontend/glossary.jsx
  var { useState: useState_g } = React;
  var RESEARCH_GLOSSARY_ITEMS = [
    {
      label: "OOS",
      text: "Out-of-sample. \uD6C4\uBCF4 \uC120\uD0DD\uACFC \uD29C\uB2DD\uC5D0 \uC4F0\uC9C0 \uC54A\uC740 \uAE30\uAC04 \uAC80\uC99D\uC774\uB2E4. OOS disabled\uB294 \uD0D0\uC0C9\uC740 \uD5C8\uC6A9\uD558\uC9C0\uB9CC human-level claim blocked \uC0C1\uD0DC\uB2E4."
    },
    {
      label: "overfit",
      text: "\uD2B9\uC815 \uAD6C\uAC04\uC5D0\uB9CC \uB9DE\uCD98 \uACFC\uC801\uD569\uC774\uB2E4. \uC804\uCCB4 \uAE30\uAC04 \uC6B0\uC0C1\uD5A5\uC774\uBA74 \uC5F0\uAD6C \uC2E0\uD638\uB85C \uBCFC \uC218 \uC788\uC9C0\uB9CC research signal, not production proof \uC774\uB2E4."
    },
    {
      label: "MDD",
      text: "Maximum Drawdown. \uB204\uC801 \uC218\uC775\uACE1\uC120\uC758 \uACE0\uC810 \uB300\uBE44 \uCD5C\uB300 \uD558\uB77D\uD3ED\uC774\uBA70, \uC190\uC2E4 \uAD6C\uAC04\uC758 \uAE4A\uC774\uB97C \uBCF8\uB2E4."
    },
    {
      label: "payoff",
      text: "payoff_ratio. \uD3C9\uADE0 \uC774\uC775\uC744 \uD3C9\uADE0 \uC190\uC2E4 \uC808\uB313\uAC12\uC73C\uB85C \uB098\uB208 \uAC12\uC774\uB2E4. \uC2B9\uB960\uC774 \uB0AE\uC544\uB3C4 \uD070 \uC774\uC775 \uAC70\uB798\uAC00 \uC788\uC73C\uBA74 \uBCF4\uC644\uB420 \uC218 \uC788\uB2E4."
    },
    {
      label: "edge ratio",
      text: "MFE\uB97C MAE \uC808\uB313\uAC12\uC73C\uB85C \uB098\uB208 \uC9C4\uC785 \uD488\uC9C8 \uC9C0\uD45C\uB2E4. 1\uBCF4\uB2E4 \uB192\uC73C\uBA74 \uC720\uB9AC\uD55C \uC6C0\uC9C1\uC784\uC774 \uBD88\uB9AC\uD55C \uC6C0\uC9C1\uC784\uBCF4\uB2E4 \uCEF8\uB2E4\uB294 \uB73B\uC774\uB2E4."
    },
    {
      label: "MFE/MAE",
      text: "MFE\uB294 \uBCF4\uC720 \uC911 \uCD5C\uB300 \uC720\uB9AC \uC6C0\uC9C1\uC784, MAE\uB294 \uCD5C\uB300 \uBD88\uB9AC \uC6C0\uC9C1\uC784\uC774\uB2E4. \uB9E4\uC218 \uD0C0\uC810\uACFC \uB9E4\uB3C4 \uD0C0\uC774\uBC0D\uC744 \uBD84\uB9AC\uD574 \uBCF8\uB2E4."
    },
    {
      label: "slippage",
      text: "\uBC31\uD14C\uC2A4\uD2B8 \uAC00\uC815\uAC00\uC640 \uC2E4\uC81C \uCCB4\uACB0\uAC00\uC758 \uCC28\uC774\uB2E4. \uAC70\uB798\uB7C9\xB7\uD638\uAC00\xB7\uC2DC\uC7A5\uCDA9\uACA9 \uB54C\uBB38\uC5D0 \uC2E4\uC804\uC5D0\uC11C\uB294 \uBC18\uB4DC\uC2DC \uBE44\uC6A9\uC73C\uB85C \uBC18\uC601\uD574\uC57C \uD55C\uB2E4."
    },
    {
      label: "PBO",
      text: "Probability of Backtest Overfitting. \uB9CE\uC740 \uD6C4\uBCF4\uB97C \uC2DC\uB3C4\uD55C \uB4A4 \uC6B0\uC5F0\uD788 \uC88B\uC740 \uD6C4\uBCF4\uB97C \uACE0\uB978 \uC704\uD5D8\uC744 \uCD94\uC815\uD55C\uB2E4."
    },
    {
      label: "DSR",
      text: "Deflated Sharpe Ratio. \uC5EC\uB7EC \uBC88\uC758 \uD0D0\uC0C9\uACFC \uBE44\uC815\uADDC \uC218\uC775\uBD84\uD3EC\uB97C \uAC10\uC548\uD574 Sharpe \uACC4\uC5F4 \uC131\uACFC\uB97C \uBCF4\uC218\uC801\uC73C\uB85C \uBCF8\uB2E4."
    },
    {
      label: "win-day ratio",
      text: "\uC218\uC775\uC774 \uD50C\uB7EC\uC2A4\uC778 \uAC70\uB798\uC77C \uBE44\uC728\uC774\uB2E4. \uC77C\uBCC4 \uC190\uC775\uC774 \uBCF5\uD569\uB418\uB294 \uC804\uB7B5\uC5D0\uC11C \uD558\uB8E8 \uB2E8\uC704 \uC548\uC815\uC131\uC744 \uD655\uC778\uD55C\uB2E4."
    },
    {
      label: "recent-weighted score",
      text: "2024~2026 \uAC19\uC740 \uCD5C\uADFC \uB370\uC774\uD130\uC5D0 \uB354 \uD070 \uAC00\uC911\uC744 \uC8FC\uB294 \uC5F0\uAD6C \uC810\uC218\uB2E4. \uC2DC\uC7A5 \uBCC0\uD654 \uB300\uC751\uC6A9\uC774\uBA70 \uB2E8\uB3C5 \uC2B9\uACA9 \uC99D\uAC70\uB294 \uC544\uB2C8\uB2E4."
    }
  ];
  function ResearchGlossaryPanel() {
    const [expanded, setExpanded] = useState_g(false);
    const visibleItems = expanded ? RESEARCH_GLOSSARY_ITEMS : RESEARCH_GLOSSARY_ITEMS.slice(0, 6);
    return /* @__PURE__ */ React.createElement("div", { className: "panel research-glossary-panel", "data-testid": "research-glossary-panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Metric Glossary"), /* @__PURE__ */ React.createElement("button", { className: "btn tiny", onClick: () => setExpanded(!expanded) }, expanded ? "less" : "all")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "glossary-proof-note" }, "research signal, not production proof \xB7 human-level claim blocked until multiyear holdout/OOS evidence exists."), /* @__PURE__ */ React.createElement("div", { className: "glossary-grid" }, visibleItems.map((item) => /* @__PURE__ */ React.createElement("div", { className: "glossary-card", key: item.label }, /* @__PURE__ */ React.createElement("div", { className: "glossary-term" }, item.label), /* @__PURE__ */ React.createElement("div", { className: "glossary-text" }, item.text))))));
  }
  Object.assign(window, { ResearchGlossaryPanel, RESEARCH_GLOSSARY_ITEMS });

  // ../frontend/bt-chart-utils.jsx
  var {
    useState: useState_btc,
    useRef: useRef_btc,
    useMemo: useMemo_btc,
    useEffect: useEffect_btc,
    useCallback: useCallback_btc
  } = React;
  function _btMoneyTick(v) {
    const a = Math.abs(v);
    if (a >= 1e8) return (v / 1e8).toFixed(1) + "\uC5B5";
    if (a >= 1e4) return (v / 1e4).toFixed(0) + "\uB9CC";
    return Math.round(v).toLocaleString("ko-KR");
  }
  function _btDateLabel(d) {
    const s = String(d);
    if (s.length === 8) return s.slice(4, 6) + "/" + s.slice(6, 8);
    return s;
  }
  function _btDateLabelY(d, prevD) {
    const s = String(d);
    if (s.length !== 8) return _btDateLabel(d);
    const ps = prevD != null ? String(prevD) : "";
    const sameYear = ps.length === 8 && ps.slice(0, 4) === s.slice(0, 4);
    if (sameYear) return s.slice(4, 6) + "/" + s.slice(6, 8);
    return s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
  }
  var _btAxisTicks = window._axisTicks;
  function _btCsvCell(v) {
    if (v == null) return "";
    const s = String(v);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function _btAnalysisCsv(analysis) {
    const eq = analysis && analysis.equity || {};
    const daily = eq.daily || [];
    const cumulative = eq.cumulative || [];
    const header = ["\uB0A0\uC9DC", "\uC77C\uBCC4\uC190\uC775(\uC6D0)", "\uB204\uC801\uC218\uC775(\uC6D0)"];
    const lines = [header.map(_btCsvCell).join(",")];
    const rowN = Math.max(daily.length, cumulative.length);
    for (let i = 0; i < rowN; i++) {
      const d = daily[i] || {};
      const c = cumulative[i] || {};
      lines.push([
        _btCsvCell(d.date),
        _btCsvCell(d.pnl != null ? Math.round(d.pnl) : ""),
        _btCsvCell(c.cum_profit != null ? Math.round(c.cum_profit) : "")
      ].join(","));
    }
    return "\uFEFF" + lines.join("\r\n");
  }
  function _btDownloadAnalysisCsv(analysis) {
    const csv = _btAnalysisCsv(analysis);
    const d = /* @__PURE__ */ new Date();
    const ymd = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    const fname = "\uBC31\uD14C\uC2A4\uD2B8_" + ymd + ".csv";
    try {
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => {
        try {
          URL.revokeObjectURL(url);
        } catch (e) {
        }
      }, 0);
    } catch (e) {
    }
  }
  var _BT_WEEKDAYS = ["\uC6D4", "\uD654", "\uC218", "\uBAA9", "\uAE08", "\uD1A0", "\uC77C"];
  function _btReducedMotion() {
    try {
      return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch (e) {
      return false;
    }
  }
  function _useCountUp(target, durMs) {
    const [val, setVal] = useState_btc(typeof target === "number" ? target : 0);
    const fromRef = useRef_btc(0);
    const rafRef = useRef_btc(0);
    useEffect_btc(() => {
      const to = typeof target === "number" && isFinite(target) ? target : 0;
      if (_btReducedMotion()) {
        setVal(to);
        return;
      }
      const from = fromRef.current;
      const dur = durMs || 600;
      const t0 = performance.now();
      const tick = (now) => {
        const p = Math.min(1, (now - t0) / dur);
        const eased = 1 - Math.pow(1 - p, 3);
        setVal(from + (to - from) * eased);
        if (p < 1) {
          rafRef.current = requestAnimationFrame(tick);
        } else {
          fromRef.current = to;
        }
      };
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(rafRef.current);
    }, [target, durMs]);
    return val;
  }
  function _BtArcGauge({ value, max, color, label, sub }) {
    const v = typeof value === "number" && isFinite(value) ? value : 0;
    const frac = Math.max(0, Math.min(1, max ? v / max : 0));
    const R = 22, CX = 26, CY = 26, sw = 6;
    const circ = Math.PI * R;
    const dash = circ * frac;
    const arc = `M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`;
    return /* @__PURE__ */ React.createElement("div", { className: "bt-gauge-wrap" }, /* @__PURE__ */ React.createElement("svg", { width: "52", height: "34", viewBox: "0 0 52 34" }, /* @__PURE__ */ React.createElement("path", { d: arc, fill: "none", stroke: "var(--line-2)", strokeWidth: sw, strokeLinecap: "round" }), /* @__PURE__ */ React.createElement(
      "path",
      {
        d: arc,
        fill: "none",
        stroke: color,
        strokeWidth: sw,
        strokeLinecap: "round",
        strokeDasharray: `${dash.toFixed(1)} ${circ.toFixed(1)}`
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "bt-gauge-num" }, /* @__PURE__ */ React.createElement("span", { className: "summary-val", style: { fontSize: 15, color } }, label), sub && /* @__PURE__ */ React.createElement("span", { className: "summary-sub" }, sub)));
  }
  function _BtSparkline({ values, w, h }) {
    const vals = Array.isArray(values) ? values : [];
    const W = w || 120, H = h || 24;
    if (vals.length === 0) return /* @__PURE__ */ React.createElement("svg", { className: "bt-spark", viewBox: `0 0 ${W} ${H}` });
    const maxAbs = Math.max(1, ...vals.map((v) => Math.abs(v || 0)));
    const n = vals.length;
    const bw = Math.max(1, W / n * 0.8);
    const mid = H / 2;
    return /* @__PURE__ */ React.createElement("svg", { className: "bt-spark", viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: "0", x2: W, y1: mid, y2: mid, stroke: "var(--line-1)", strokeWidth: "0.5" }), vals.map((v, i) => {
      const val = v || 0;
      const bh = Math.abs(val) / maxAbs * (mid - 1);
      const x = W / n * (i + 0.5) - bw / 2;
      const y = val >= 0 ? mid - bh : mid;
      return /* @__PURE__ */ React.createElement(
        "rect",
        {
          key: i,
          x,
          y,
          width: bw,
          height: Math.max(0.5, bh),
          fill: val >= 0 ? "var(--teal)" : "var(--red)",
          opacity: "0.8"
        }
      );
    }));
  }
  function _BtChartEmpty({ message }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)",
      textAlign: "center",
      padding: "0 16px"
    } }, message || "\uBD84\uC11D \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
  }
  function _gpMoney(v) {
    const a = Math.abs(v || 0);
    if (a >= 1e8) return ((v || 0) / 1e8).toFixed(1) + "\uC5B5";
    if (a >= 1e4) return Math.round((v || 0) / 1e4) + "\uB9CC";
    return Math.round(v || 0).toLocaleString("ko-KR");
  }

  // ../frontend/bt-equity-charts.jsx
  function BtEquityChart({ equity, onBrush, brushActive, onBrushClear }) {
    const daily = equity && equity.daily || [];
    const cumulative = equity && equity.cumulative || [];
    const [hover, setHover] = useState_btc(null);
    const [view, setView] = useState_btc(null);
    const dragRef = useRef_btc(null);
    const [brushSel, setBrushSel] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 300;
    const padL = 58, padR = 62, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const total = daily.length;
    useEffect_btc(() => {
      setView(null);
      setBrushSel(null);
    }, [total, equity]);
    const v0 = view ? Math.max(0, view[0]) : 0;
    const v1 = view ? Math.min(total - 1, view[1]) : total - 1;
    const n = total > 0 ? v1 - v0 + 1 : 0;
    const vDaily = total > 0 ? daily.slice(v0, v1 + 1) : [];
    const vCum = total > 0 ? cumulative.slice(v0, v1 + 1) : [];
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, Math.min(22, slot * 0.7));
    const xCenter = (i) => padL + slot * (i + 0.5);
    const pxToLocal = (px) => Math.floor((px - padL) / slot);
    const localToGlobal = (i) => v0 + i;
    const pnlVals = vDaily.map((d) => d.pnl || 0);
    const pnlMax = Math.max(0, ...pnlVals);
    const pnlMin = Math.min(0, ...pnlVals);
    const pnlRange = pnlMax - pnlMin || 1;
    const yPnl = (v) => padT + innerH - (v - pnlMin) / pnlRange * innerH;
    const zeroY = yPnl(0);
    const cumVals = vCum.map((c) => c.cum_profit || 0);
    const cumMax = Math.max(0, ...cumVals);
    const cumMin = Math.min(0, ...cumVals);
    const cumRange = cumMax - cumMin || 1;
    const yCum = (v) => padT + innerH - (v - cumMin) / cumRange * innerH;
    const cumPath = useMemo_btc(() => {
      if (vCum.length < 2) return "";
      return vCum.map(
        (c, i) => `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yCum(c.cum_profit || 0).toFixed(1)}`
      ).join(" ");
    }, [vCum, n, cumMin, cumRange]);
    const cumLen = useMemo_btc(() => Math.max(1, innerW * 1.4), [innerW]);
    const xTickIdx = useMemo_btc(() => {
      if (n <= 1) return n === 1 ? [0] : [];
      const step = Math.max(1, Math.ceil(n / 8));
      const idx = [];
      for (let i = 0; i < n; i += step) idx.push(i);
      if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
      return idx;
    }, [n]);
    const _localPx = (e) => {
      if (!svgRef.current) return null;
      const rect = svgRef.current.getBoundingClientRect();
      return (e.clientX - rect.left) * (W / rect.width);
    };
    const onMove = (e) => {
      if (!n) return;
      const px = _localPx(e);
      if (px == null) return;
      const i = pxToLocal(px);
      const drag = dragRef.current;
      if (drag) {
        if (drag.mode === "brush") {
          const ci = Math.max(0, Math.min(n - 1, i));
          setBrushSel({ a: drag.startIdx, b: ci });
        } else if (drag.mode === "pan") {
          const deltaIdx = Math.round((drag.startPx - px) / slot);
          const span = drag.startView[1] - drag.startView[0];
          let nv0 = drag.startView[0] + deltaIdx;
          nv0 = Math.max(0, Math.min(total - 1 - span, nv0));
          setView([nv0, nv0 + span]);
        }
        return;
      }
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    const onDown = (e) => {
      if (!n) return;
      const px = _localPx(e);
      if (px == null) return;
      const i = Math.max(0, Math.min(n - 1, pxToLocal(px)));
      if (e.shiftKey) {
        dragRef.current = { mode: "brush", startIdx: i };
        setBrushSel({ a: i, b: i });
      } else {
        dragRef.current = { mode: "pan", startPx: px, startView: [v0, v1] };
      }
    };
    const onUp = () => {
      const drag = dragRef.current;
      dragRef.current = null;
      if (drag && drag.mode === "brush" && brushSel && onBrush) {
        const a = Math.min(brushSel.a, brushSel.b), b = Math.max(brushSel.a, brushSel.b);
        const gA = localToGlobal(a), gB = localToGlobal(b);
        const dA = daily[gA] && daily[gA].date, dB = daily[gB] && daily[gB].date;
        if (dA && dB) {
          onBrush(dA * 1e6, dB * 1e6 + 235959);
        }
      }
    };
    const onWheel = (e) => {
      if (!n || total <= 1) return;
      e.preventDefault();
      const px = _localPx(e);
      if (px == null) return;
      const center = localToGlobal(Math.max(0, Math.min(n - 1, pxToLocal(px))));
      const span = v1 - v0;
      const factor = e.deltaY < 0 ? 0.8 : 1.25;
      let newSpan = Math.round(span * factor);
      newSpan = Math.max(2, Math.min(total - 1, newSpan));
      let nv0 = Math.round(center - newSpan * (center - v0) / Math.max(1, span));
      nv0 = Math.max(0, Math.min(total - 1 - newSpan, nv0));
      if (newSpan >= total - 1) {
        setView(null);
      } else {
        setView([nv0, nv0 + newSpan]);
      }
      setHover(null);
    };
    const last = cumulative.length ? cumulative[cumulative.length - 1].cum_profit : null;
    const peakCum = cumulative.length ? Math.max(...cumulative.map((c) => c.cum_profit || 0)) : null;
    const zoomed = view != null;
    const brushBand = brushSel && brushSel.a != null ? (() => {
      const a = Math.min(brushSel.a, brushSel.b), b = Math.max(brushSel.a, brushSel.b);
      const x0 = xCenter(a) - slot / 2, x1 = xCenter(b) + slot / 2;
      return { x: Math.max(padL, x0), w: Math.min(W - padR, x1) - Math.max(padL, x0) };
    })() : null;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uB204\uC801\uC218\uC775\uACE1\uC120 \xB7 \uC77C\uBCC4\uC190\uC775"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC77C\uC774\uC775 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC77C\uC190\uC2E4 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB204\uC801\uC218\uC775 \u20A9" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uD720 = \uC2DC\uAC04\uCD95 \uC90C \xB7 \uB4DC\uB798\uADF8 = \uD32C",
      "Shift+\uB4DC\uB798\uADF8 = \uAD6C\uAC04 \uC120\uD0DD \u2192 \uAD6C\uAC04 \uBD84\uC11D",
      zoomed ? "\uC90C \uC0C1\uD0DC \u2014 \uB354\uBE14\uD074\uB9AD\uC73C\uB85C \uC804\uCCB4 \uBCF5\uADC0" : "\uD06C\uB85C\uC2A4\uD5E4\uC5B4\uB85C \uC77C\uBCC4 \uAC12 \uD655\uC778"
    ] }), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC885 \uB204\uC801",
        value: last != null ? fmtMoney(last) : "\u2014",
        color: last != null && last > 0 ? "var(--teal)" : last != null && last < 0 ? "var(--red)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(Mini, { label: "\uB204\uC801 \uACE0\uC810", value: peakCum != null ? fmtMoney(peakCum) : "\u2014" }), /* @__PURE__ */ React.createElement(Mini, { label: "\uAC70\uB798\uC77C\uC218", value: total > 0 ? String(total) : "\u2014" }), zoomed && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => {
      setView(null);
      setBrushSel(null);
    } }, "\u2922 \uC804\uCCB4 \uBCF4\uAE30"), brushActive && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn sm",
        onClick: () => {
          setBrushSel(null);
          onBrushClear && onBrushClear();
        },
        style: { borderColor: "var(--teal-dim)", color: "var(--teal)" }
      },
      "\u21A9 \uC804\uCCB4\uB85C \uBCF5\uADC0"
    )), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        style: { cursor: dragRef.current ? dragRef.current.mode === "brush" ? "crosshair" : "grabbing" : "crosshair" },
        onMouseMove: onMove,
        onMouseLeave: () => {
          setHover(null);
        },
        onMouseDown: onDown,
        onMouseUp: onUp,
        onWheel,
        onDoubleClick: () => {
          setView(null);
          setBrushSel(null);
        }
      },
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: zeroY,
          y2: zeroY,
          stroke: "rgba(255,255,255,0.28)",
          strokeWidth: "1",
          strokeDasharray: "2 3"
        }
      ),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yPnl(pnlMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _btMoneyTick(pnlMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yPnl(pnlMin) + 3, textAnchor: "end", fill: "var(--red)" }, _btMoneyTick(pnlMin)),
      _btAxisTicks(pnlMin, pnlMax, 5).map((tv, i) => Math.abs(tv) < 1e-9 || Math.abs(tv - pnlMax) < 1e-9 || Math.abs(tv - pnlMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("g", { key: `eyl${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: yPnl(tv), y2: yPnl(tv), stroke: "rgba(255,255,255,0.06)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yPnl(tv) + 3, textAnchor: "end", fill: "var(--ink-3)" }, _btMoneyTick(tv)))),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yCum(cumMax) + 3, textAnchor: "start", fill: "var(--amber)" }, _btMoneyTick(cumMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yCum(cumMin) + 3, textAnchor: "start", fill: "var(--amber)" }, _btMoneyTick(cumMin)),
      _btAxisTicks(cumMin, cumMax, 5).map((tv, i) => Math.abs(tv - cumMax) < 1e-9 || Math.abs(tv - cumMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("text", { key: `eyr${i}`, className: "chart-axis-text", x: W - padR + 6, y: yCum(tv) + 3, textAnchor: "start", fill: "var(--ink-3)" }, _btMoneyTick(tv))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      brushBand && brushBand.w > 0 && /* @__PURE__ */ React.createElement("rect", { className: "bt-brush-band", x: brushBand.x, y: padT, width: brushBand.w, height: innerH }),
      vDaily.map((d, i) => {
        const v = d.pnl || 0;
        const y0 = zeroY, y1 = yPnl(v);
        const top = Math.min(y0, y1), h = Math.max(1, Math.abs(y1 - y0));
        return /* @__PURE__ */ React.createElement(
          "rect",
          {
            key: `b${i}`,
            x: xCenter(i) - barW / 2,
            y: top,
            width: barW,
            height: h,
            fill: v >= 0 ? "var(--teal)" : "var(--red)",
            opacity: hover === i ? 1 : 0.55
          }
        );
      }),
      vCum.length > 1 && /* @__PURE__ */ React.createElement(
        "path",
        {
          d: cumPath,
          fill: "none",
          stroke: "var(--amber)",
          strokeWidth: "2",
          className: !zoomed && !_btReducedMotion() ? "bt-draw-in" : "",
          style: !zoomed && !_btReducedMotion() ? { strokeDasharray: cumLen, strokeDashoffset: cumLen } : void 0
        }
      ),
      xTickIdx.map((i, k) => /* @__PURE__ */ React.createElement("text", { key: `x${i}`, className: "chart-axis-text", x: xCenter(i), y: H - 10, textAnchor: "middle" }, vDaily[i] ? _btDateLabelY(vDaily[i].date, k > 0 && vDaily[xTickIdx[k - 1]] ? vDaily[xTickIdx[k - 1]].date : null) : "")),
      hover != null && vDaily[hover] && /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: xCenter(hover),
          x2: xCenter(hover),
          y1: padT,
          y2: padT + innerH,
          stroke: "rgba(255,255,255,0.22)",
          strokeWidth: "1"
        }
      )
    ), hover != null && vDaily[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 170,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 } }, _btDateLabel(vDaily[hover].date)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC77C\uC190\uC775"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: vDaily[hover].pnl > 0 ? "num-pos" : vDaily[hover].pnl < 0 ? "num-neg" : "",
        style: { textAlign: "right" }
      },
      fmtMoney(vDaily[hover].pnl)
    ), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, vCum[hover] ? fmtMoney(vCum[hover].cum_profit) : "\u2014"))), total === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uB204\uC801\uC218\uC775\uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }))));
  }
  function BtMaeMfeScatter({ points }) {
    const pts = Array.isArray(points) ? points : [];
    const [hover, setHover] = useState_btc(null);
    const W = 880, H = 320;
    const padL = 52, padR = 24, padT = 18, padB = 36;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const maes = pts.map((p) => p.mae);
    const mfes = pts.map((p) => p.mfe);
    const xMin = Math.min(0, ...maes, 0), xMax = Math.max(0, ...maes, 0);
    const yMin = Math.min(0, ...mfes, 0), yMax = Math.max(0, ...mfes, 0);
    const xRange = xMax - xMin || 1, yRange = yMax - yMin || 1;
    const sx = (v) => padL + (v - xMin) / xRange * innerW;
    const sy = (v) => padT + innerH - (v - yMin) / yRange * innerH;
    const x0 = sx(0), y0 = sy(0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "MAE / MFE \uC0B0\uC810\uB3C4"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC774\uC775 \uAC70\uB798" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC190\uC2E4 \uAC70\uB798" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "x = R_MAE(\uB9E4\uC218\uD6C4 \uCD5C\uC800\uC218\uC775\uB960, %)",
      "y = R_MFE(\uB9E4\uC218\uD6C4 \uCD5C\uACE0\uC218\uC775\uB960, %)",
      "\uC88C\uC0C1=\uC7A0\uC7AC\uC774\uC775 \uD07C/\uB099\uD3ED \uD07C \xB7 \uC810\uC0C9=\uC2E4\uD604\uC190\uC775"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("line", { x1: x0, x2: x0, y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.3)", strokeWidth: "1", strokeDasharray: "3 3" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y0, y2: y0, stroke: "rgba(255,255,255,0.3)", strokeWidth: "1", strokeDasharray: "3 3" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL, y: H - 10, textAnchor: "start" }, xMin.toFixed(1), "%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR, y: H - 10, textAnchor: "end" }, xMax.toFixed(1), "%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: sy(yMax) + 3, textAnchor: "end" }, yMax.toFixed(1), "%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: sy(yMin) + 3, textAnchor: "end" }, yMin.toFixed(1), "%"),
      /* @__PURE__ */ React.createElement("text", { className: "bt-quadrant-label", x: x0 + 6, y: padT + 12 }, "MFE\u2191"),
      /* @__PURE__ */ React.createElement("text", { className: "bt-quadrant-label", x: padL + 4, y: y0 - 6 }, "MAE\u2193"),
      pts.map((p, i) => /* @__PURE__ */ React.createElement(
        "circle",
        {
          key: i,
          className: "bt-scatter-pt",
          cx: sx(p.mae),
          cy: sy(p.mfe),
          r: hover === i ? 5 : 3.2,
          fill: p.pnl_pct >= 0 ? "var(--teal)" : "var(--red)",
          opacity: hover == null ? 0.62 : hover === i ? 1 : 0.28,
          onMouseEnter: () => setHover(i)
        }
      ))
    ), hover != null && pts[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 180,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, pts[hover].code || "(\uBBF8\uC0C1)"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "MAE"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--red)" } }, pts[hover].mae.toFixed(2), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "MFE"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--teal)" } }, pts[hover].mfe.toFixed(2), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC2E4\uD604"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: pts[hover].pnl_pct > 0 ? "num-pos" : pts[hover].pnl_pct < 0 ? "num-neg" : "",
        style: { textAlign: "right" }
      },
      pts[hover].pnl_pct.toFixed(2),
      "%"
    ))), pts.length === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "MAE/MFE \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4 (R_MAE\xB7R_MFE \uACB0\uCE21)" }))));
  }
  function BtUnderwaterChart({ underwater }) {
    const series = underwater && underwater.series || [];
    const maxDd = underwater && underwater.max_drawdown;
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 240;
    const padL = 58, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const x = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const ddVals = series.map((d) => d.drawdown || 0);
    const ddMax = Math.max(1, ...ddVals);
    const y = (v) => padT + v / ddMax * innerH;
    const areaPath = useMemo_btc(() => {
      if (n < 2) return "";
      const top = series.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.drawdown || 0).toFixed(1)}`).join(" ");
      return `${top} L ${x(n - 1).toFixed(1)} ${padT.toFixed(1)} L ${x(0).toFixed(1)} ${padT.toFixed(1)} Z`;
    }, [series, n, ddMax]);
    const linePath = useMemo_btc(() => {
      if (n < 2) return "";
      return series.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d.drawdown || 0).toFixed(1)}`).join(" ");
    }, [series, n, ddMax]);
    const xTickIdx = useMemo_btc(() => {
      if (n <= 1) return n === 1 ? [0] : [];
      const step = Math.max(1, Math.ceil(n / 8));
      const idx = [];
      for (let i = 0; i < n; i += step) idx.push(i);
      if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
      return idx;
    }, [n]);
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
      const i = Math.round(frac * (n - 1));
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--red)" } }), "\uC5B8\uB354\uC6CC\uD130 \u2014 Drawdown"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uACE0\uC810 \uB300\uBE44 \uBC18\uB0A9\uC561(\uC6D0)")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uCD5C\uB300\uB099\uD3ED", value: maxDd ? fmtMoney(maxDd.drawdown) : "\u2014", color: maxDd ? "var(--red)" : void 0 }), maxDd && /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uB099\uD3ED \uAD6C\uAC04",
        value: `${_btDateLabel(maxDd.start_date)}~${_btDateLabel(maxDd.trough_date)}`,
        sub: maxDd.recovery_date ? `\uD68C\uBCF5 ${_btDateLabel(maxDd.recovery_date)}` : "\uBBF8\uD68C\uBCF5"
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("linearGradient", { id: "bt-uw-grad", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "#ff6b6b", stopOpacity: "0" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "#ff6b6b", stopOpacity: "0.42" }))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT, y2: padT, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: padT + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: padT + innerH + 3, textAnchor: "end", fill: "var(--red)" }, "\u2212", _btMoneyTick(ddMax)),
      _btAxisTicks(0, ddMax, 5).map((tv, i) => Math.abs(tv) < 1e-9 || Math.abs(tv - ddMax) < 1e-9 ? null : /* @__PURE__ */ React.createElement("g", { key: `uyl${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(tv), y2: y(tv), stroke: "rgba(255,255,255,0.06)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(tv) + 3, textAnchor: "end", fill: "var(--ink-3)" }, "\u2212", _btMoneyTick(tv)))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      n > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: areaPath, fill: "url(#bt-uw-grad)" }), /* @__PURE__ */ React.createElement("path", { d: linePath, fill: "none", stroke: "var(--red)", strokeWidth: "1.4", opacity: "0.85" })),
      xTickIdx.map((i, k) => /* @__PURE__ */ React.createElement("text", { key: `ux${i}`, className: "chart-axis-text", x: x(i), y: H - 10, textAnchor: "middle" }, series[i] ? _btDateLabelY(series[i].date, k > 0 && series[xTickIdx[k - 1]] ? series[xTickIdx[k - 1]].date : null) : "")),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: x(hover),
          x2: x(hover),
          y1: padT,
          y2: padT + innerH,
          stroke: "rgba(255,255,255,0.14)",
          strokeWidth: "1"
        }
      )
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 160,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, _btDateLabel(series[hover].date)), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--red)" } }, "\u2212", _btMoneyTick(series[hover].drawdown)))), n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC5B8\uB354\uC6CC\uD130 \uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }))));
  }
  function BtRollingChart({ rolling }) {
    const series = rolling && rolling.series || [];
    const window2 = rolling && rolling.window || 20;
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 260;
    const padL = 48, padR = 52, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const x = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const yWin = (v) => padT + innerH - Math.max(0, Math.min(100, v)) / 100 * innerH;
    const payoffMax = Math.max(2, ...series.map((s) => s.payoff || 0));
    const yPay = (v) => padT + innerH - Math.max(0, v) / payoffMax * innerH;
    const winPath = useMemo_btc(
      () => n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yWin(s.win_rate || 0).toFixed(1)}`).join(" "),
      [series, n]
    );
    const payPath = useMemo_btc(
      () => n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yPay(s.payoff || 0).toFixed(1)}`).join(" "),
      [series, n, payoffMax]
    );
    const xTickIdx = useMemo_btc(() => {
      if (n <= 1) return n === 1 ? [0] : [];
      const step = Math.max(1, Math.ceil(n / 8));
      const idx = [];
      for (let i = 0; i < n; i += step) idx.push(i);
      if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
      return idx;
    }, [n]);
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
      const i = Math.round(frac * (n - 1));
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uB864\uB9C1 \uC9C0\uD45C \u2014 \uC2B9\uB960 \xB7 Payoff"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uB864\uB9C1 \uC2B9\uB960 %" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB864\uB9C1 payoff \uBC30" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      `${window2}\uAC70\uB798 \uC774\uB3D9\uCC3D \uAE30\uC900`,
      "\uC88C\uCD95 = \uC2B9\uB960(%) \xB7 \uC6B0\uCD95 = payoff(\uD3C9\uADE0\uC774\uC775/\uD3C9\uADE0\uC190\uC2E4)",
      "\uAD6C\uAC04\uBCC4 \uC804\uB7B5 \uC548\uC815\uC131 \uCD94\uC774 \uC9C4\uB2E8"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: yWin(50), y2: yWin(50), stroke: "rgba(255,255,255,0.18)", strokeWidth: "1", strokeDasharray: "2 3" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yWin(50) + 3, textAnchor: "end", fill: "var(--ink-2)" }, "50%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yWin(100) + 3, textAnchor: "end", fill: "var(--teal)" }, "100%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yWin(0) + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0%"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yPay(payoffMax) + 3, textAnchor: "start", fill: "var(--amber)" }, payoffMax.toFixed(1), "\xD7"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yPay(1) + 3, textAnchor: "start", fill: "var(--ink-3)" }, "1\xD7"),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: yPay(1), y2: yPay(1), stroke: "rgba(240,179,90,0.2)", strokeWidth: "1", strokeDasharray: "4 4" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: winPath, fill: "none", stroke: "var(--teal)", strokeWidth: "2" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: payPath, fill: "none", stroke: "var(--amber)", strokeWidth: "1.6", strokeDasharray: "5 3", opacity: "0.9" }),
      xTickIdx.map((i) => /* @__PURE__ */ React.createElement("text", { key: `rx${i}`, className: "chart-axis-text", x: x(i), y: H - 10, textAnchor: "middle" }, series[i] ? `#${series[i].index + 1}` : "")),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement("line", { x1: x(hover), x2: x(hover), y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.22)", strokeWidth: "1" })
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 160,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, "\uAC70\uB798 #", series[hover].index + 1), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC2B9\uB960"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--teal)" } }, fmtPct(series[hover].win_rate)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "payoff"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--amber)" } }, (series[hover].payoff || 0).toFixed(2), "\xD7"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uD3C9\uADE0\uC190\uC775"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: series[hover].avg_pnl_pct > 0 ? "num-pos" : series[hover].avg_pnl_pct < 0 ? "num-neg" : "",
        style: { textAlign: "right" }
      },
      series[hover].avg_pnl_pct.toFixed(2),
      "%"
    ))), n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: `\uAC70\uB798\uAC00 ${window2}\uAC74 \uC774\uC0C1 \uB204\uC801\uB418\uBA74 \uB864\uB9C1 \uC9C0\uD45C\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4` }))));
  }
  function BtCumulativeTradesChart({ data }) {
    const series = data && data.series || [];
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 280;
    const padL = 52, padR = 60, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const x = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const maxTrades = Math.max(1, ...series.map((s) => s.cum_trades || 0));
    const yTrades = (v) => padT + innerH - v / maxTrades * innerH;
    const profits = series.map((s) => s.cum_profit_krw || 0);
    const pMax = Math.max(0, ...profits);
    const pMin = Math.min(0, ...profits);
    const pRange = pMax - pMin || 1;
    const yProfit = (v) => padT + innerH - (v - pMin) / pRange * innerH;
    const tradesArea = useMemo_btc(() => {
      if (n < 2) return "";
      const top = series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yTrades(s.cum_trades || 0).toFixed(1)}`).join(" ");
      return `${top} L ${x(n - 1).toFixed(1)} ${(padT + innerH).toFixed(1)} L ${x(0).toFixed(1)} ${(padT + innerH).toFixed(1)} Z`;
    }, [series, n, maxTrades]);
    const profitPath = useMemo_btc(
      () => n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${yProfit(s.cum_profit_krw || 0).toFixed(1)}`).join(" "),
      [series, n, pMin, pRange]
    );
    const xTickIdx = useMemo_btc(() => {
      if (n <= 1) return n === 1 ? [0] : [];
      const step = Math.max(1, Math.ceil(n / 8));
      const idx = [];
      for (let i = 0; i < n; i += step) idx.push(i);
      if (idx[idx.length - 1] !== n - 1) idx.push(n - 1);
      return idx;
    }, [n]);
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
      const i = Math.round(frac * (n - 1));
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    const profitZeroY = yProfit(0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uB204\uC801 \uAC70\uB798 \xB7 \uB204\uC801 \uC190\uC775"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--blue)", label: "\uB204\uC801 \uAC70\uB798\uC218" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB204\uC801 \uC190\uC775 \u20A9" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "x\uCD95 = \uAC70\uB798 \uC21C\uC11C(\uCCB4\uACB0 \uC21C)",
      "\uC88C\uCD95 = \uB204\uC801 \uAC70\uB798\uC218 \xB7 \uC6B0\uCD95 = \uB204\uC801 \uC2E4\uD604\uC190\uC775",
      "\uCCB4\uACB0 \uBE48\uB3C4\uC640 \uC790\uBCF8 \uC99D\uAC00\uB97C \uD55C \uD654\uBA74\uC5D0\uC11C \uBE44\uAD50"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("defs", null, /* @__PURE__ */ React.createElement("linearGradient", { id: "bt-ct-grad", x1: "0", y1: "0", x2: "0", y2: "1" }, /* @__PURE__ */ React.createElement("stop", { offset: "0%", stopColor: "#5b8def", stopOpacity: "0.34" }), /* @__PURE__ */ React.createElement("stop", { offset: "100%", stopColor: "#5b8def", stopOpacity: "0.02" }))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: profitZeroY, y2: profitZeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: profitZeroY + 3, textAnchor: "start", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yTrades(maxTrades) + 3, textAnchor: "end", fill: "var(--blue)" }, maxTrades),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yTrades(0) + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yProfit(pMax) + 3, textAnchor: "start", fill: "var(--amber)" }, _btMoneyTick(pMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yProfit(pMin) + 3, textAnchor: "start", fill: "var(--amber)" }, _btMoneyTick(pMin)),
      _btAxisTicks(pMin, pMax, 5).map((tv, i) => Math.abs(tv - pMax) < 1e-9 || Math.abs(tv - pMin) < 1e-9 || Math.abs(tv) < 1e-9 ? null : /* @__PURE__ */ React.createElement("text", { key: `cyr${i}`, className: "chart-axis-text", x: W - padR + 6, y: yProfit(tv) + 3, textAnchor: "start", fill: "var(--ink-3)" }, _btMoneyTick(tv))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: tradesArea, fill: "url(#bt-ct-grad)", stroke: "var(--blue)", strokeWidth: "1.2", opacity: "0.85" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: profitPath, fill: "none", stroke: "var(--amber)", strokeWidth: "2" }),
      xTickIdx.map((i) => /* @__PURE__ */ React.createElement("text", { key: `cx${i}`, className: "chart-axis-text", x: x(i), y: H - 10, textAnchor: "middle" }, series[i] ? `#${series[i].index}` : "")),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement("line", { x1: x(hover), x2: x(hover), y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.22)", strokeWidth: "1" })
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 170,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, "\uAC70\uB798 #", series[hover].index), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801 \uAC70\uB798"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--blue)" } }, series[hover].cum_trades, "\uAC74"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801 \uC190\uC775"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: series[hover].cum_profit_krw > 0 ? "num-pos" : series[hover].cum_profit_krw < 0 ? "num-neg" : "",
        style: { textAlign: "right" }
      },
      fmtMoney(series[hover].cum_profit_krw)
    ))), n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uB204\uC801 \uAC70\uB798\xB7\uC190\uC775 \uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }))));
  }

  // ../frontend/bt-distribution-charts.jsx
  function BtDistributionChart({ distribution }) {
    const bins = distribution && distribution.pnl_histogram || [];
    const [hover, setHover] = useState_btc(null);
    const W = 880, H = 260;
    const padL = 44, padR = 24, padT = 18, padB = 34;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = bins.length;
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, slot * 0.82);
    const xLeft = (i) => padL + slot * i;
    const maxCount = Math.max(1, ...bins.map((b) => b.count || 0));
    const yBar = (c) => padT + innerH - c / maxCount * innerH;
    const zeroX = useMemo_btc(() => {
      if (!n) return null;
      for (let i = 0; i < n; i++) {
        const b = bins[i];
        if (b.bin_start <= 0 && b.bin_end >= 0) {
          const frac = b.bin_end - b.bin_start ? (0 - b.bin_start) / (b.bin_end - b.bin_start) : 0.5;
          return xLeft(i) + slot * Math.max(0, Math.min(1, frac));
        }
      }
      return null;
    }, [bins, n]);
    const binColor = (b) => {
      if (b.bin_end <= 0) return "var(--red)";
      if (b.bin_start >= 0) return "var(--teal)";
      return "var(--amber)";
    };
    const yTicks = [0, 0.25, 0.5, 0.75, 1].map((t) => Math.round(t * maxCount));
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC190\uC775 \uBD84\uD3EC \u2014 Histogram"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC774\uC775 bin" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC190\uC2E4 bin" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "x\uCD95 = \uAC70\uB798 \uC218\uC775\uB960(%) \uAD6C\uAC04",
      "y\uCD95 = \uD574\uB2F9 \uAD6C\uAC04 \uAC70\uB798 \uC218",
      "0% \uACBD\uACC4\uC120 \uC88C=\uC190\uC2E4 / \uC6B0=\uC774\uC775"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseLeave: () => setHover(null)
      },
      yTicks.map((t, i) => /* @__PURE__ */ React.createElement("g", { key: `hy${i}` }, /* @__PURE__ */ React.createElement("line", { className: "chart-grid-line", x1: padL, x2: W - padR, y1: yBar(t), y2: yBar(t) }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yBar(t) + 3, textAnchor: "end" }, t))),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      bins.map((b, i) => {
        const c = b.count || 0;
        const top = yBar(c), h = Math.max(0, padT + innerH - top);
        return /* @__PURE__ */ React.createElement(
          "rect",
          {
            key: `hb${i}`,
            x: xLeft(i) + (slot - barW) / 2,
            y: top,
            width: barW,
            height: h,
            fill: binColor(b),
            opacity: hover === i ? 1 : 0.7,
            onMouseEnter: () => setHover(i)
          }
        );
      }),
      zeroX != null && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: zeroX,
          x2: zeroX,
          y1: padT,
          y2: padT + innerH,
          stroke: "rgba(255,255,255,0.4)",
          strokeWidth: "1",
          strokeDasharray: "3 3"
        }
      ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: zeroX, y: padT - 4, textAnchor: "middle", fill: "var(--ink-1)" }, "0%")),
      n > 0 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL, y: H - 10, textAnchor: "start" }, bins[0].bin_start.toFixed(1), "%"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR, y: H - 10, textAnchor: "end" }, bins[n - 1].bin_end.toFixed(1), "%"))
    ), hover != null && bins[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 180,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAD6C\uAC04"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, bins[hover].bin_start.toFixed(1), "~", bins[hover].bin_end.toFixed(1), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAC70\uB798\uC218"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, bins[hover].count))), n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC190\uC775 \uBD84\uD3EC\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }))));
  }
  function BtHeatmap({ heatmap }) {
    const cells = heatmap && heatmap.cells || [];
    const [hover, setHover] = useState_btc(null);
    const wrapRef = useRef_btc(null);
    const [wrapW, setWrapW] = useState_btc(0);
    useEffect_btc(() => {
      const el = wrapRef.current;
      if (!el || typeof ResizeObserver === "undefined") return void 0;
      const ro = new ResizeObserver((entries) => {
        for (const e of entries) {
          const w = e.contentRect ? e.contentRect.width : el.clientWidth;
          setWrapW(Math.max(0, Math.floor(w)));
        }
      });
      ro.observe(el);
      setWrapW(Math.max(0, Math.floor(el.clientWidth)));
      return () => {
        try {
          ro.disconnect();
        } catch (e) {
        }
      };
    }, []);
    const slots = useMemo_btc(() => {
      const s = Array.from(new Set(cells.map((c) => c.slot))).sort((a, b) => a - b);
      return s;
    }, [cells]);
    const weekdays = useMemo_btc(() => {
      const present = new Set(cells.map((c) => c.weekday));
      const base = [0, 1, 2, 3, 4];
      [5, 6].forEach((w) => {
        if (present.has(w)) base.push(w);
      });
      return base;
    }, [cells]);
    const cellMap = useMemo_btc(() => {
      const m = {};
      for (const c of cells) m[c.weekday + "_" + c.slot] = c;
      return m;
    }, [cells]);
    const cellPct = (c) => c ? Number(c.profit_pct_sum || 0) : 0;
    const maxAbs = Math.max(1e-6, ...cells.map((c) => Math.abs(cellPct(c))));
    const cellColor = (c) => {
      if (!c) return "var(--bg-0)";
      const t = Math.min(1, Math.abs(cellPct(c)) / maxAbs);
      if (cellPct(c) >= 0) {
        return `rgba(76,214,179,${(0.12 + 0.66 * t).toFixed(3)})`;
      }
      return `rgba(255,107,107,${(0.12 + 0.66 * t).toFixed(3)})`;
    };
    const slotLabel = (slot) => {
      const found = cells.find((c) => c.slot === slot);
      if (found && found.slot_label) return found.slot_label;
      const m = slot * 30;
      return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
    };
    const SP = 3;
    const ROW_LBL = 34;
    const colN = Math.max(1, slots.length);
    const avail = wrapW > 0 ? wrapW - ROW_LBL - SP * (colN + 1) - 2 : 0;
    const cellW = avail > 0 ? Math.max(34, Math.min(96, Math.floor(avail / colN))) : 34;
    const cellH = Math.max(26, Math.min(64, Math.round(cellW * 0.72)));
    const big = cellW >= 52;
    const valFont = big ? Math.min(18, Math.round(cellH * 0.34)) : 9.5;
    const hdFont = big ? 11 : 9.5;
    const lblFont = big ? 13 : 11;
    const cellPctLabel = (v) => `${(v || 0) >= 0 ? "+" : ""}${(v || 0).toFixed(1)}%`;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uC694\uC77C \xD7 \uC2DC\uAC04\uB300 \uD788\uD2B8\uB9F5"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uB9E4\uC218\uC2DC\uAC01 \uAE30\uC900 \xB7 \uC218\uC775\uB960 \uD569\uACC4(%)")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { ref: wrapRef, style: { width: "100%" } }, cells.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { position: "relative", minHeight: 120 } }, /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC2DC\uAC04\uB300 \uD788\uD2B8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" })) : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { borderCollapse: "separate", borderSpacing: SP, fontFamily: "var(--mono)", width: "100%", tableLayout: "fixed" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { width: ROW_LBL } }), slots.map((s) => /* @__PURE__ */ React.createElement("th", { key: s, style: { fontSize: hdFont, color: "var(--ink-3)", fontWeight: 400, padding: "0 1px", whiteSpace: "nowrap" } }, slotLabel(s))))), /* @__PURE__ */ React.createElement("tbody", null, weekdays.map((w) => /* @__PURE__ */ React.createElement("tr", { key: w }, /* @__PURE__ */ React.createElement("td", { style: { fontSize: lblFont, color: "var(--ink-2)", textAlign: "center", paddingRight: 4 } }, _BT_WEEKDAYS[w]), slots.map((s) => {
      const c = cellMap[w + "_" + s];
      const key = w + "_" + s;
      return /* @__PURE__ */ React.createElement(
        "td",
        {
          key: s,
          onMouseEnter: () => c && setHover(key),
          onMouseLeave: () => setHover(null),
          title: c ? `${_BT_WEEKDAYS[w]} ${slotLabel(s)} \xB7 \uC218\uC775\uB960 \uD569\uACC4 ${cellPctLabel(cellPct(c))} \xB7 \uC218\uC775\uAE08 ${fmtMoney(c.profit_krw)} \xB7 ${c.trades}\uAC74` : "",
          style: {
            width: cellW,
            height: cellH,
            borderRadius: 4,
            background: cellColor(c),
            border: hover === key ? "1px solid var(--ink-0)" : "1px solid var(--line-1)",
            textAlign: "center",
            fontSize: valFont,
            lineHeight: 1.15,
            color: c ? "var(--ink-0)" : "var(--ink-3)",
            cursor: "default",
            verticalAlign: "middle"
          }
        },
        c ? big ? /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" } }, /* @__PURE__ */ React.createElement("span", { style: { fontWeight: 600, color: cellPct(c) >= 0 ? "var(--teal)" : "var(--red)" } }, cellPctLabel(cellPct(c))), /* @__PURE__ */ React.createElement("span", { style: { fontSize: Math.max(8.5, valFont - 5), color: "var(--ink-3)" } }, c.trades, "\uAC74")) : cellPctLabel(cellPct(c)) : ""
      );
    }))))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, marginTop: 10, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(76,214,179,0.78)", label: "\uC774\uC775 \uC2AC\uB86F(\uC218\uC775\uB960 \uD569\uACC4 +)" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(255,107,107,0.78)", label: "\uC190\uC2E4 \uC2AC\uB86F(\uC218\uC775\uB960 \uD569\uACC4 \u2212)" }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, big ? "\uC140 = \uC218\uC775\uB960 \uD569\uACC4(%) \xB7 \uAC70\uB798 \uAC74\uC218" : "\uC140 = \uC218\uC775\uB960 \uD569\uACC4(%)"))))));
  }
  function BtMonteCarloChart({ mc, loading, onRun }) {
    const fan = mc && mc.fan || [];
    const observed = mc && mc.observed;
    const n = fan.length;
    const W = 880, H = 300;
    const padL = 58, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const allLo = fan.map((f) => f.p5);
    const allHi = fan.map((f) => f.p95);
    const obsVal = observed ? [observed.final_krw, 0] : [0];
    const yMin = Math.min(0, ...allLo, ...obsVal);
    const yMax = Math.max(0, ...allHi, ...obsVal);
    const yRange = yMax - yMin || 1;
    const x = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const y = (v) => padT + innerH - (v - yMin) / yRange * innerH;
    const band = (loKey, hiKey) => {
      if (n < 2) return "";
      const top = fan.map((f, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(f[hiKey]).toFixed(1)}`).join(" ");
      const bot = fan.slice().reverse().map((f, i) => `L ${x(n - 1 - i).toFixed(1)} ${y(f[loKey]).toFixed(1)}`).join(" ");
      return `${top} ${bot} Z`;
    };
    const median = useMemo_btc(() => {
      if (n < 2) return "";
      return fan.map((f, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(f.p50).toFixed(1)}`).join(" ");
    }, [fan, n, yMin, yRange]);
    const zeroY = y(0);
    const q = (obj) => obj || { p5: 0, p25: 0, p50: 0, p75: 0, p95: 0 };
    const mddPct = q(mc && mc.mdd_pct);
    const finalQ = q(mc && mc.final);
    const ruin = mc && typeof mc.ruin_prob === "number" ? mc.ruin_prob : null;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uBAAC\uD14C\uCE74\uB97C\uB85C \u2014 \uB204\uC801\uC190\uC775 \uD32C"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, mc && mc.n ? `${mc.n.toLocaleString("ko-KR")}\uD68C \xB7 ${mc.days}\uC77C` : "\uBBF8\uC2E4\uD589"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onRun, disabled: loading }, loading ? "\uACC4\uC0B0\uC911\u2026" : "\u21BB \uC7AC\uACC4\uC0B0"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uC77C\uBCC4 \uC190\uC775\uC744 \uBB34\uC791\uC704 \uC7AC\uBC30\uC5F4\uD55C \uBD84\uD3EC",
      "\uBC34\uB4DC = p5~p95 / \uC9C4\uD55C\uC120 = \uC911\uC559\uAC12(p50)",
      "\uAC70\uB798 \uC21C\uC11C\uAC00 \uACB0\uACFC\uC5D0 \uC900 \uC601\uD5A5(\uC6B4) \uC9C4\uB2E8"
    ] }), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uAE30\uB300 MDD p95", value: fmtPct(mddPct.p95), color: "var(--red)" }), /* @__PURE__ */ React.createElement(Mini, { label: "MDD \uC911\uC559\uAC12", value: fmtPct(mddPct.p50) }), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uC885\uC190\uC775 p50",
        value: fmtMoney(finalQ.p50),
        color: finalQ.p50 > 0 ? "var(--teal)" : finalQ.p50 < 0 ? "var(--red)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uD30C\uC0B0\uD655\uB960",
        value: ruin != null ? fmtPct(ruin * 100) : "\u2014",
        color: ruin != null && ruin >= 0.2 ? "var(--red)" : ruin != null && ruin >= 0.05 ? "var(--amber)" : void 0,
        sub: mc && mc.ruin_pct ? `\uC790\uBCF8 -${Math.round(mc.ruin_pct)}%` : void 0
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: zeroY, y2: zeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(yMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _btMoneyTick(yMax)), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(yMin) + 3, textAnchor: "end", fill: "var(--red)" }, _btMoneyTick(yMin)), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), n > 1 && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("path", { d: band("p5", "p95"), fill: "rgba(155,135,245,0.12)" }), /* @__PURE__ */ React.createElement("path", { d: band("p25", "p75"), fill: "rgba(155,135,245,0.24)" }), /* @__PURE__ */ React.createElement("path", { d: median, fill: "none", stroke: "var(--violet)", strokeWidth: "2" })), observed && n > 1 && /* @__PURE__ */ React.createElement("circle", { cx: x(n - 1), cy: y(observed.final_krw), r: "4", fill: "var(--amber)", stroke: "var(--bg-0)", strokeWidth: "1" })), n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uBAAC\uD14C\uCE74\uB97C\uB85C\uB97C \uC2E4\uD589\uD558\uBA74 \uC190\uC775 \uBD84\uD3EC \uD32C\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4 (\uAC70\uB798\uC77C 2\uC77C \uC774\uC0C1 \uD544\uC694)" })), mc && mc.n > 0 && /* @__PURE__ */ React.createElement(_BtMddBox, { mddPct, observedPct: observed ? observed.mdd_pct : null })));
  }
  function _BtMddBox({ mddPct, observedPct }) {
    const lo = mddPct.p5, hi = Math.max(mddPct.p95, observedPct || 0, 1e-4);
    const span = hi - lo || 1;
    const fx = (v) => (v - lo) / span * 100;
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 12 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginBottom: 4 } }, "MDD \uBD84\uD3EC (%)"), /* @__PURE__ */ React.createElement("div", { style: { position: "relative", height: 26, background: "var(--bg-0)", border: "1px solid var(--line-1)", borderRadius: 4 } }, /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 6,
      height: 14,
      borderRadius: 3,
      left: fx(mddPct.p25) + "%",
      width: Math.max(1, fx(mddPct.p75) - fx(mddPct.p25)) + "%",
      background: "rgba(255,107,107,0.28)",
      border: "1px solid rgba(255,107,107,0.5)"
    } }), /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: 4, height: 18, width: 2, background: "var(--red)", left: fx(mddPct.p50) + "%" } }), observedPct != null && /* @__PURE__ */ React.createElement("div", { title: "\uC2E4\uCE21 MDD", style: { position: "absolute", top: 2, height: 22, width: 2, background: "var(--amber)", left: Math.max(0, Math.min(100, fx(observedPct))) + "%" } })), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { display: "flex", justifyContent: "space-between", fontSize: 9.5, color: "var(--ink-3)", marginTop: 3 } }, /* @__PURE__ */ React.createElement("span", null, "p5 ", mddPct.p5.toFixed(1), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--amber)" } }, observedPct != null ? `\uC2E4\uCE21 ${observedPct.toFixed(1)}%` : ""), /* @__PURE__ */ React.createElement("span", null, "p95 ", mddPct.p95.toFixed(1), "%")));
  }
  var _BT_MONTHS = ["1\uC6D4", "2\uC6D4", "3\uC6D4", "4\uC6D4", "5\uC6D4", "6\uC6D4", "7\uC6D4", "8\uC6D4", "9\uC6D4", "10\uC6D4", "11\uC6D4", "12\uC6D4"];
  function BtMonthlyCalendar({ monthly }) {
    const years = monthly && monthly.years || [];
    const cells = monthly && monthly.cells || [];
    const [hover, setHover] = useState_btc(null);
    const cellMap = useMemo_btc(() => {
      const m = {};
      for (const c of cells) m[c.year + "_" + c.month] = c;
      return m;
    }, [cells]);
    const maxAbs = Math.max(1, ...cells.map((c) => Math.abs(c.profit_krw || 0)));
    const cellColor = (c) => {
      if (!c) return "var(--bg-0)";
      const t = Math.min(1, Math.abs(c.profit_krw || 0) / maxAbs);
      if ((c.profit_krw || 0) >= 0) return `rgba(76,214,179,${(0.12 + 0.66 * t).toFixed(3)})`;
      return `rgba(255,107,107,${(0.12 + 0.66 * t).toFixed(3)})`;
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uC6D4\uBCC4 \uC218\uC775 \uCE98\uB9B0\uB354"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uB9E4\uB3C4\uC77C \uAE30\uC900 \xB7 \uC6D4\uBCC4 \uC190\uC775 \uD569")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, cells.length === 0 ? /* @__PURE__ */ React.createElement("div", { style: { position: "relative", minHeight: 120 } }, /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC6D4\uBCC4 \uC218\uC775 \uCE98\uB9B0\uB354\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4" })) : /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { style: { borderCollapse: "separate", borderSpacing: 3, fontFamily: "var(--mono)" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { width: 44 } }), _BT_MONTHS.map((m, i) => /* @__PURE__ */ React.createElement("th", { key: i, style: { fontSize: 9.5, color: "var(--ink-3)", fontWeight: 400, padding: "0 1px", whiteSpace: "nowrap" } }, m)))), /* @__PURE__ */ React.createElement("tbody", null, years.map((yr) => /* @__PURE__ */ React.createElement("tr", { key: yr }, /* @__PURE__ */ React.createElement("td", { style: { fontSize: 11, color: "var(--ink-2)", textAlign: "center", paddingRight: 4 } }, yr), _BT_MONTHS.map((_, mi) => {
      const month = mi + 1;
      const key = yr + "_" + month;
      const c = cellMap[key];
      return /* @__PURE__ */ React.createElement(
        "td",
        {
          key: mi,
          onMouseEnter: () => c && setHover(key),
          onMouseLeave: () => setHover(null),
          title: c ? `${yr}\uB144 ${month}\uC6D4 \xB7 ${fmtMoney(c.profit_krw)} \xB7 ${c.trades}\uAC74 \xB7 ${fmtPct(c.win_rate)}` : "",
          style: {
            width: 48,
            height: 30,
            borderRadius: 4,
            background: cellColor(c),
            border: hover === key ? "1px solid var(--ink-0)" : "1px solid var(--line-1)",
            textAlign: "center",
            fontSize: 9,
            lineHeight: 1.25,
            color: c ? "var(--ink-0)" : "var(--ink-3)"
          }
        },
        c ? /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 9.5 } }, _btMoneyTick(c.profit_krw)), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 8, color: "var(--ink-2)" } }, c.trades, "\uAC74")) : ""
      );
    }))))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, marginTop: 10, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(76,214,179,0.78)", label: "\uC774\uC775 \uC6D4" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(255,107,107,0.78)", label: "\uC190\uC2E4 \uC6D4" }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC140 = \uC190\uC775 \xB7 \uAC70\uB798\uC218")))));
  }

  // ../frontend/bt-stat-panels.jsx
  function BtExitReasonPanel({ rows }) {
    const items = Array.isArray(rows) ? rows : [];
    const maxAbs = Math.max(1, ...items.map((r) => Math.abs(r.total_pnl || 0)));
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uB9E4\uB3C4\uC870\uAC74\uBCC4 \uC190\uC775 \uBD84\uD574"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uCCAD\uC0B0\uC0AC\uC720 \uAE30\uC900")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, items.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB9E4\uB3C4\uC870\uAC74 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4") : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 4 } }, items.map((r, i) => {
      const frac = Math.abs(r.total_pnl || 0) / maxAbs;
      const pos = (r.total_pnl || 0) >= 0;
      return /* @__PURE__ */ React.createElement("div", { key: i, className: "bt-exit-row" }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-1)", width: 96, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flexShrink: 0 } }, r.reason), /* @__PURE__ */ React.createElement("div", { className: "bt-exit-track" }, /* @__PURE__ */ React.createElement("div", { className: "bt-exit-fill", style: {
        width: (frac * 100).toFixed(1) + "%",
        background: pos ? "var(--teal)" : "var(--red)",
        opacity: 0.75
      } })), /* @__PURE__ */ React.createElement("span", { className: "mono " + (pos ? "num-pos" : "num-neg"), style: { fontSize: 10.5, width: 88, textAlign: "right", flexShrink: 0 } }, fmtMoney(r.total_pnl)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", width: 78, textAlign: "right", flexShrink: 0 } }, r.count, "\uAC74\xB7", fmtPct(r.win_rate)));
    }))));
  }
  function BtContribTable({ title, rows }) {
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 6 } }, title), !rows || rows.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uC774\uD130 \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2 } }, rows.map((r, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { display: "flex", alignItems: "center", gap: 8, padding: "4px 6px", borderBottom: "1px solid var(--line-1)" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-1)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, r.name), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", flexShrink: 0 } }, r.trades, "\uAC74"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono " + (r.profit_krw > 0 ? "num-pos" : r.profit_krw < 0 ? "num-neg" : ""),
        style: { fontSize: 11, flexShrink: 0, width: 96, textAlign: "right" }
      },
      fmtMoney(r.profit_krw)
    )))));
  }
  var _BT_SEVERITY = {
    critical: { color: "var(--red)", bg: "rgba(255,107,107,0.07)", border: "rgba(255,107,107,0.3)", label: "\uC704\uD5D8" },
    warning: { color: "var(--amber)", bg: "rgba(240,179,90,0.07)", border: "rgba(240,179,90,0.3)", label: "\uC8FC\uC758" },
    info: { color: "var(--teal)", bg: "rgba(76,214,179,0.06)", border: "rgba(76,214,179,0.28)", label: "\uC815\uBCF4" }
  };
  function BtInsightsPanel({ insights }) {
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC778\uC0AC\uC774\uD2B8"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uADDC\uCE59 \uAE30\uBC18 \uC790\uB3D9 \uC9C4\uB2E8")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 8 } }, !insights || insights.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC0DD\uC131\uB41C \uC778\uC0AC\uC774\uD2B8\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4 (\uAC70\uB798 \uBD80\uC871 \uB610\uB294 \uD2B9\uC774\uC0AC\uD56D \uC5C6\uC74C).") : insights.map((ins, i) => {
      const sev = _BT_SEVERITY[ins.severity] || _BT_SEVERITY.info;
      const sevClass = "bt-insight-card sev-" + (_BT_SEVERITY[ins.severity] ? ins.severity : "info");
      return /* @__PURE__ */ React.createElement("div", { key: i, className: sevClass, style: {
        border: "1px solid " + sev.border,
        background: sev.bg,
        borderRadius: 6,
        padding: "9px 11px",
        display: "flex",
        flexDirection: "column",
        gap: 3
      } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", { className: "tag-slim", style: { color: sev.color, borderColor: sev.border } }, sev.label), /* @__PURE__ */ React.createElement("strong", { style: { fontSize: 12.5, color: "var(--ink-0)" } }, ins.title)), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 12, color: "var(--ink-1)", lineHeight: 1.5 } }, ins.detail));
    })));
  }
  function BtOrderflowPanel({ orderflow }) {
    const sep = orderflow && orderflow.separation || [];
    const wins = orderflow && orderflow.wins || {};
    const losses = orderflow && orderflow.losses || {};
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uC624\uB354\uD50C\uB85C\uC6B0 \u2014 \uC774\uAE30\uB294 \uC9C4\uC785 \uD504\uB85C\uD30C\uC77C"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC2B9 \uC9C4\uC785" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uD328 \uC9C4\uC785" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, sep.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC624\uB354\uD50C\uB85C\uC6B0 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4 (B_\uCCB4\uACB0\uAC15\uB3C4\xB7\uC794\uB7C9 \uB4F1 \uACB0\uCE21)") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uBCC0\uC218\uBCC4 \uC2B9/\uD328 \uC9C4\uC785 \uBD84\uD3EC(p10~p90) \uBE44\uAD50",
      "\uBC15\uC2A4 = p25~p75 \xB7 \uC138\uB85C\uC120 = \uC911\uC559\uAC12(p50)",
      "\uBD84\uB9AC\uB825 = \uC2B9\uD328 \uC911\uC559\uAC12 \uCC28 \uC808\uB300\uAC12 \uC21C\uC704"
    ] }), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 10 } }, sep.map((s) => /* @__PURE__ */ React.createElement(_BtOfRow, { key: s.var, sep: s, win: wins[s.var], loss: losses[s.var] }))), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 12, borderTop: "1px solid var(--line-1)", paddingTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", letterSpacing: ".1em", textTransform: "uppercase", marginBottom: 6 } }, "\uBD84\uB9AC\uB825 \uC21C\uC704"), sep.map((s, i) => /* @__PURE__ */ React.createElement("div", { key: s.var, style: { display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 11, fontFamily: "var(--mono)" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", width: 16 } }, i + 1, "."), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-1)", flex: 1 } }, s.label), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)" } }, s.win_p50.toFixed(2)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "vs"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, s.loss_p50.toFixed(2)), /* @__PURE__ */ React.createElement("span", { className: s.diff > 0 ? "num-pos" : "num-neg", style: { width: 70, textAlign: "right" } }, s.diff > 0 ? "+" : "", s.diff.toFixed(2))))))));
  }
  function _BtOfRow({ sep, win, loss }) {
    const w = win || {}, l = loss || {};
    const vals = [w.p10, w.p90, l.p10, l.p90, w.p50, l.p50].filter((v) => typeof v === "number");
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const span = hi - lo || 1;
    const fx = (v) => typeof v === "number" ? (v - lo) / span * 100 : 0;
    const box = (d, color) => typeof d.p25 === "number" && typeof d.p75 === "number" ? /* @__PURE__ */ React.createElement("div", { style: { position: "relative", height: 16, flex: 1 } }, /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 7,
      height: 2,
      background: color,
      opacity: 0.4,
      left: fx(d.p10) + "%",
      width: Math.max(1, fx(d.p90) - fx(d.p10)) + "%"
    } }), /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 2,
      height: 12,
      borderRadius: 2,
      left: fx(d.p25) + "%",
      width: Math.max(1, fx(d.p75) - fx(d.p25)) + "%",
      background: color === "var(--teal)" ? "rgba(76,214,179,0.25)" : "rgba(255,107,107,0.25)",
      border: "1px solid " + color
    } }), /* @__PURE__ */ React.createElement("div", { style: { position: "absolute", top: 0, height: 16, width: 2, background: color, left: fx(d.p50) + "%" } })) : /* @__PURE__ */ React.createElement("div", { style: { flex: 1, fontSize: 10, color: "var(--ink-3)" } }, "\uD45C\uBCF8 \uBD80\uC871");
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginBottom: 2 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-1)", width: 86, flexShrink: 0 } }, sep.label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "\uC2B9 n=", w.n || 0, " \xB7 \uD328 n=", l.n || 0)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 3 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9, color: "var(--teal)", width: 20 } }, "\uC2B9"), box(w, "var(--teal)")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9, color: "var(--red)", width: 20 } }, "\uD328"), box(l, "var(--red)"))));
  }
  function BtStatTestPanel({ stats }) {
    const rows = Array.isArray(stats) ? stats : [];
    const sig = rows.filter((r) => r.significant);
    if (rows.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uD1B5\uACC4 \uAC80\uC815"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC694\uC77C\xB7\uC2DC\uAC04\uB300 \uD6A8\uACFC")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBC84\uD0B7\uC774 \uBD80\uC871\uD574 \uAC80\uC815\uC744 \uC218\uD589\uD558\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4 (\uC694\uC77C/\uC2DC\uAC04\uB300 2\uC885 \uC774\uC0C1 \uD544\uC694).")));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uD1B5\uACC4 \uAC80\uC815"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC720\uC758 ", sig.length, "\uAC74 / \uC804\uCCB4 ", rows.length, "\uBC84\uD0B7")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 4 } }, rows.map((r, i) => {
      const pos = r.mean > 0;
      return /* @__PURE__ */ React.createElement("div", { key: i, style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "5px 8px",
        borderRadius: 5,
        fontSize: 11,
        fontFamily: "var(--mono)",
        border: "1px solid " + (r.significant ? pos ? "rgba(76,214,179,0.4)" : "rgba(255,107,107,0.4)" : "var(--line-1)"),
        background: r.significant ? pos ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)" : "var(--bg-0)"
      } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", width: 56 } }, r.kind === "weekday" ? "\uC694\uC77C" : "\uC2DC\uAC04\uB300"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-1)", width: 48 } }, r.label), /* @__PURE__ */ React.createElement("span", { className: pos ? "num-pos" : "num-neg", style: { width: 64, textAlign: "right" } }, r.mean > 0 ? "+" : "", r.mean.toFixed(2), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", width: 56, textAlign: "right" } }, "n=", r.n), /* @__PURE__ */ React.createElement("span", { style: { flex: 1, textAlign: "right" } }, r.underpowered ? /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "\uD45C\uBCF8 \uBD80\uC871") : r.significant ? /* @__PURE__ */ React.createElement("span", { style: { color: pos ? "var(--teal)" : "var(--red)" } }, "\uC720\uC758 (p=", r.p_value != null ? r.p_value.toFixed(3) : "\u2014", ")") : /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "p=", r.p_value != null ? r.p_value.toFixed(3) : "\u2014")));
    })));
  }
  var _BT_CMP_METRICS = [
    { key: "trade_count", label: "\uAC70\uB798\uC218", fmt: (v) => fmtInt(v), higher: true },
    { key: "win_rate", label: "\uC2B9\uB960", fmt: (v) => fmtPct(v), higher: true },
    { key: "total_profit_pct", label: "\uC218\uC775\uB960\uD569", fmt: (v) => fmtPct(v), higher: true },
    { key: "total_profit_krw", label: "\uC218\uC775\uAE08", fmt: (v) => fmtMoney(v), higher: true },
    { key: "max_drawdown_pct", label: "MDD", fmt: (v) => fmtPct(v), higher: false },
    { key: "profit_factor", label: "PF", fmt: (v) => v != null ? v.toFixed(2) : "\u2014", higher: true },
    { key: "payoff_ratio", label: "Payoff", fmt: (v) => v != null ? v.toFixed(2) : "\u2014", higher: true },
    { key: "sharpe", label: "Sharpe", fmt: (v) => v != null ? v.toFixed(2) : "\u2014", higher: true }
  ];
  function BtCompareView({ cmp, onClose }) {
    const [norm, setNorm] = useState_btc(true);
    const a = cmp && cmp.a, b = cmp && cmp.b;
    const delta = cmp && cmp.delta || {};
    const cumA = a && a.equity && a.equity.cumulative || [];
    const cumB = b && b.equity && b.equity.cumulative || [];
    const W = 880, H = 280;
    const padL = 58, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const toSeries = (cum) => {
      const arr = cum.map((c) => c.cum_profit || 0);
      if (!norm) return arr;
      const base = arr.length ? arr[0] : 0;
      return arr.map((v) => 100 + (v - base));
    };
    const sA = toSeries(cumA), sB = toSeries(cumB);
    const allV = [...sA, ...sB];
    const yMin = allV.length ? Math.min(...allV) : 0;
    const yMax = allV.length ? Math.max(...allV) : 1;
    const yRange = yMax - yMin || 1;
    const nMax = Math.max(sA.length, sB.length);
    const x = (i) => nMax > 1 ? padL + i / (nMax - 1) * innerW : padL + innerW / 2;
    const y = (v) => padT + innerH - (v - yMin) / yRange * innerH;
    const pathOf = (s) => s.length < 2 ? "" : s.map((v, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "A / B \uBE44\uAD50"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "A " + (a ? a.job_id : "\u2014") }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--violet)", label: "B " + (b ? b.job_id : "\u2014") }), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setNorm((v) => !v) }, norm ? "\uC815\uADDC\uD654 ON" : "\uC815\uADDC\uD654 OFF"), onClose && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose }, "\u2715 \uB2EB\uAE30"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, !a && !b ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBE44\uAD50\uD560 \uC7A1\uC744 \uC120\uD0DD\uD558\uC138\uC694.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { marginBottom: 14 } }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(yMax) + 3, textAnchor: "end" }, norm ? yMax.toFixed(0) : _btMoneyTick(yMax)), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(yMin) + 3, textAnchor: "end" }, norm ? yMin.toFixed(0) : _btMoneyTick(yMin)), _btAxisTicks(yMin, yMax, 5).map((tv, i) => Math.abs(tv - yMax) < 1e-9 || Math.abs(tv - yMin) < 1e-9 ? null : /* @__PURE__ */ React.createElement("g", { key: `cmpy${i}` }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(tv), y2: y(tv), stroke: "rgba(255,255,255,0.06)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(tv) + 3, textAnchor: "end", fill: "var(--ink-3)" }, norm ? tv.toFixed(0) : _btMoneyTick(tv)))), sA.length > 1 && /* @__PURE__ */ React.createElement("path", { d: pathOf(sA), fill: "none", stroke: "var(--teal)", strokeWidth: "2" }), sB.length > 1 && /* @__PURE__ */ React.createElement("path", { d: pathOf(sB), fill: "none", stroke: "var(--violet)", strokeWidth: "2", strokeDasharray: "5 4" }), allV.length === 0 && null), allV.length === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uBE44\uAD50\uD560 \uC218\uC775\uACE1\uC120\uC774 \uC5C6\uC2B5\uB2C8\uB2E4" })), /* @__PURE__ */ React.createElement("table", { style: { width: "100%", borderCollapse: "collapse", fontFamily: "var(--mono)", fontSize: 11.5 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { color: "var(--ink-3)", fontSize: 10, textTransform: "uppercase", letterSpacing: ".08em" } }, /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "4px 8px" } }, "\uBA54\uD2B8\uB9AD"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "4px 8px", color: "var(--teal)" } }, "A"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "4px 8px", color: "var(--violet)" } }, "B"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "right", padding: "4px 8px" } }, "\u0394 (B\u2212A)"))), /* @__PURE__ */ React.createElement("tbody", null, _BT_CMP_METRICS.map((m) => {
      const sa = a && a.summary || {};
      const sb = b && b.summary || {};
      const va = sa[m.key], vb = sb[m.key];
      const d = delta[m.key];
      let aWin = false, bWin = false;
      if (typeof va === "number" && typeof vb === "number" && va !== vb) {
        const aBetter = m.higher ? va > vb : va < vb;
        aWin = aBetter;
        bWin = !aBetter;
      }
      const dColor = d == null ? "var(--ink-3)" : (m.higher ? d > 0 : d < 0) ? "var(--teal)" : d === 0 ? "var(--ink-3)" : "var(--red)";
      return /* @__PURE__ */ React.createElement("tr", { key: m.key, style: { borderTop: "1px solid var(--line-1)" } }, /* @__PURE__ */ React.createElement("td", { style: { textAlign: "left", padding: "5px 8px", color: "var(--ink-2)" } }, m.label), /* @__PURE__ */ React.createElement("td", { style: { textAlign: "right", padding: "5px 8px", color: aWin ? "var(--teal)" : "var(--ink-1)", fontWeight: aWin ? 700 : 400 } }, typeof va === "number" ? m.fmt(va) : "\u2014"), /* @__PURE__ */ React.createElement("td", { style: { textAlign: "right", padding: "5px 8px", color: bWin ? "var(--violet)" : "var(--ink-1)", fontWeight: bWin ? 700 : 400 } }, typeof vb === "number" ? m.fmt(vb) : "\u2014"), /* @__PURE__ */ React.createElement("td", { style: { textAlign: "right", padding: "5px 8px", color: dColor } }, d == null ? "\u2014" : (d > 0 ? "+" : "") + m.fmt(d)));
    }))))));
  }

  // ../frontend/bt-gui-parity.jsx
  function BtMddRandomChart({ data }) {
    const d = data || {};
    const curves = d.curves || [];
    const actual = d.actual || [];
    const W = 880, H = 260;
    const padL = 58, padR = 24, padT = 18, padB = 26;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const allCum = [];
    for (const c of curves) for (const p of c) allCum.push(p.cum || 0);
    for (const p of actual) allCum.push(p.cum || 0);
    const lo = allCum.length ? Math.min(0, ...allCum) : 0;
    const hi = allCum.length ? Math.max(0, ...allCum) : 1;
    const range = hi - lo || 1;
    const y = (v) => padT + innerH - (v - lo) / range * innerH;
    const pathOf = (pts) => {
      const m = pts.length;
      if (m < 2) return "";
      return pts.map(
        (p, i) => `${i === 0 ? "M" : "L"} ${(padL + i / (m - 1) * innerW).toFixed(1)} ${y(p.cum || 0).toFixed(1)}`
      ).join(" ");
    };
    const rmdd = d.random_mdd_pct || { max: 0, min: 0, avg: 0 };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "MDD \uB79C\uB364 \uACE1\uC120 \u2014 \uAC70\uB798\uC21C\uC11C \uBB34\uC791\uC704 30\uD68C vs \uC2E4\uC81C"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "rgba(255,255,255,0.35)", label: "\uC154\uD50C \uB204\uC801" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uC2E4\uC81C \uB204\uC801" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uAC70\uB798\uBCC4 \uC190\uC775 \uC21C\uC11C\uB97C \uBB34\uC791\uC704\uB85C \uC11E\uC740 30\uAC1C \uB204\uC801\uACE1\uC120",
      "\uC2E4\uC81C \uACE1\uC120\uC774 \uC154\uD50C \uBD84\uD3EC \uC548\uCABD\uC774\uBA74 \uC6B4(\uC21C\uC11C) \uC758\uC874\uC774 \uB0AE\uC74C",
      `\uC2E4\uC81C MDD ${(d.actual_mdd_pct || 0).toFixed(1)}% \xB7 \uC154\uD50C MDD \uD3C9\uADE0 ${rmdd.avg.toFixed(1)}%`
    ] }), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 10, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uC2E4\uC81C MDD", value: (d.actual_mdd_pct || 0).toFixed(1) + "%" }), /* @__PURE__ */ React.createElement(Mini, { label: "\uC154\uD50C MDD \uCD5C\uB300", value: rmdd.max.toFixed(1) + "%", color: "var(--red)" }), /* @__PURE__ */ React.createElement(Mini, { label: "\uC154\uD50C MDD \uD3C9\uADE0", value: rmdd.avg.toFixed(1) + "%" }), /* @__PURE__ */ React.createElement(Mini, { label: "\uC154\uD50C MDD \uCD5C\uC18C", value: rmdd.min.toFixed(1) + "%", color: "var(--teal)" })), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, curves.length === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 MDD \uB79C\uB364 \uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: y(0), y2: y(0), stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(0) + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(hi) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(hi)), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(lo) + 3, textAnchor: "end", fill: "var(--red)" }, _gpMoney(lo)), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), curves.map((c, i) => /* @__PURE__ */ React.createElement("path", { key: `mc${i}`, d: pathOf(c), fill: "none", stroke: "rgba(255,255,255,0.16)", strokeWidth: "0.6" })), actual.length > 1 && /* @__PURE__ */ React.createElement("path", { d: pathOf(actual), fill: "none", stroke: "var(--amber)", strokeWidth: "2.2" })))));
  }
  function BtDailyPnlChart({ data }) {
    const d = data || {};
    const series = d.series || [];
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 260;
    const padL = 58, padR = 62, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, Math.min(22, slot * 0.7));
    const xC = (i) => padL + slot * (i + 0.5);
    const pnls = series.map((s) => s.pnl || 0);
    const pMax = Math.max(0, ...pnls), pMin = Math.min(0, ...pnls);
    const pRange = pMax - pMin || 1;
    const yP = (v) => padT + innerH - (v - pMin) / pRange * innerH;
    const cums = series.map((s) => s.cum || 0);
    const cMax = Math.max(0, ...cums), cMin = Math.min(0, ...cums);
    const cRange = cMax - cMin || 1;
    const yC = (v) => padT + innerH - (v - cMin) / cRange * innerH;
    const cumPath = n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${xC(i).toFixed(1)} ${yC(s.cum || 0).toFixed(1)}`).join(" ");
    const zeroY = yP(0);
    const xTickIdx = useMemo_btc(() => {
      if (n <= 1) return n === 1 ? [0] : [];
      const step = Math.max(1, Math.ceil(n / 8));
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
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uC77C\uBCC4 \uC218\uC775 \xB7 \uB204\uC801"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC77C\uC774\uC775 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC77C\uC190\uC2E4 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB204\uC801 \u20A9" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uC77C\uBCC4 \uC2E4\uD604\uC190\uC775(\uB9C9\uB300) + \uADF8\uB0A0\uAE4C\uC9C0 \uB204\uC801(\uB77C\uC778)",
      d.index_available ? "\uC2DC\uC7A5\uC9C0\uC218 \uBE44\uAD50 \uD3EC\uD568" : "\uC2DC\uC7A5\uC9C0\uC218 \uBE44\uAD50\uB294 per-trade CSV \uC5D0 \uB370\uC774\uD130 \uC5C6\uC74C \u2014 \uBBF8\uD45C\uC2DC",
      "\uD06C\uB85C\uC2A4\uD5E4\uC5B4\uB85C \uC77C\uC790\uBCC4 \uAC12 \uD655\uC778"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC77C\uBCC4 \uC218\uC775\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: zeroY, y2: zeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yP(pMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(pMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yP(pMin) + 3, textAnchor: "end", fill: "var(--red)" }, _gpMoney(pMin)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yC(cMax) + 3, textAnchor: "start", fill: "var(--amber)" }, _gpMoney(cMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: W - padR + 6, y: yC(cMin) + 3, textAnchor: "start", fill: "var(--amber)" }, _gpMoney(cMin)),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      series.map((s, i) => {
        const v = s.pnl || 0;
        const y0 = zeroY, y1 = yP(v);
        return /* @__PURE__ */ React.createElement(
          "rect",
          {
            key: `d${i}`,
            x: xC(i) - barW / 2,
            y: Math.min(y0, y1),
            width: barW,
            height: Math.max(1, Math.abs(y1 - y0)),
            fill: v >= 0 ? "var(--teal)" : "var(--red)",
            opacity: hover === i ? 1 : 0.55
          }
        );
      }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: cumPath, fill: "none", stroke: "var(--amber)", strokeWidth: "2" }),
      xTickIdx.map((i) => /* @__PURE__ */ React.createElement("text", { key: `dx${i}`, className: "chart-axis-text", x: xC(i), y: H - 10, textAnchor: "middle" }, series[i] ? _btDateLabel(series[i].date) : "")),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement("line", { x1: xC(hover), x2: xC(hover), y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.22)", strokeWidth: "1" })
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 150,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, _btDateLabel(series[hover].date)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC77C\uC190\uC775"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: (series[hover].pnl || 0) >= 0 ? "var(--teal)" : "var(--red)" } }, fmtMoney(series[hover].pnl)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--amber)" } }, fmtMoney(series[hover].cum)))))));
  }
  function BtHourlyPnlChart({ data }) {
    const slots = data && data.slots || [];
    const [hover, setHover] = useState_btc(null);
    const W = 880, H = 240;
    const padL = 58, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = slots.length;
    const slotW = n > 0 ? innerW / n : innerW;
    const barW = Math.max(2, Math.min(30, slotW * 0.6));
    const xC = (i) => padL + slotW * (i + 0.5);
    const vals = [];
    for (const s of slots) {
      vals.push(s.profit || 0);
      vals.push(s.loss || 0);
    }
    const vMax = vals.length ? Math.max(0, ...vals) : 0;
    const vMin = vals.length ? Math.min(0, ...vals) : 0;
    const vRange = vMax - vMin || 1;
    const y = (v) => padT + innerH - (v - vMin) / vRange * innerH;
    const zeroY = y(0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uC2DC\uAC04\uB300\uBCC4 \uC190\uC775 (30\uBD84 \uC2AC\uB86F)"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC774\uC775 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC190\uC2E4 \u20A9" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: ["\uB9E4\uC218\uC2DC\uAC01 30\uBD84 \uC2AC\uB86F\uBCC4 \uC774\uC775/\uC190\uC2E4 \uBD84\uB9AC \uD569", "\uC704=\uC774\uC775 \xB7 \uC544\uB798=\uC190\uC2E4", "\uAC15\uD55C \uC190\uC2E4 \uC2DC\uAC04\uB300 \uD68C\uD53C \uD6C4\uBCF4 \uC9C4\uB2E8"] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uC2DC\uAC04 \uC815\uBCF4\uAC00 \uC788\uB294 \uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: zeroY, y2: zeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(vMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMin) + 3, textAnchor: "end", fill: "var(--red)" }, _gpMoney(vMin)),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      slots.map((s, i) => {
        const pTop = y(s.profit || 0), lBot = y(s.loss || 0);
        return /* @__PURE__ */ React.createElement("g", { key: `h${i}`, onMouseEnter: () => setHover(i) }, (s.profit || 0) > 0 && /* @__PURE__ */ React.createElement("rect", { x: xC(i) - barW / 2, y: pTop, width: barW, height: Math.max(0.5, zeroY - pTop), fill: "var(--teal)", opacity: hover === i ? 1 : 0.7 }), (s.loss || 0) < 0 && /* @__PURE__ */ React.createElement("rect", { x: xC(i) - barW / 2, y: zeroY, width: barW, height: Math.max(0.5, lBot - zeroY), fill: "var(--red)", opacity: hover === i ? 1 : 0.7 }), /* @__PURE__ */ React.createElement("rect", { x: xC(i) - slotW / 2, y: padT, width: slotW, height: innerH, fill: "transparent" }));
      }),
      slots.map((s, i) => i % Math.max(1, Math.ceil(n / 12)) === 0 || i === n - 1 ? /* @__PURE__ */ React.createElement("text", { key: `hx${i}`, className: "chart-axis-text", x: xC(i), y: H - 10, textAnchor: "middle" }, s.slot_label) : null)
    ), hover != null && slots[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 150,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, slots[hover].slot_label, " \uC2AC\uB86F"), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC774\uC775"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--teal)" } }, fmtMoney(slots[hover].profit)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC190\uC2E4"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--red)" } }, fmtMoney(slots[hover].loss)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC21C\uC190\uC775"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: (slots[hover].net || 0) >= 0 ? "var(--teal)" : "var(--red)" } }, fmtMoney(slots[hover].net)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, slots[hover].trades, "\uAC74"))))));
  }
  function BtWeekdayPnlChart({ data }) {
    const days = data && data.days || [];
    const W = 560, H = 240;
    const padL = 58, padR = 24, padT = 18, padB = 28;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = days.length;
    const slotW = n > 0 ? innerW / n : innerW;
    const barW = Math.max(8, Math.min(56, slotW * 0.62));
    const xC = (i) => padL + slotW * (i + 0.5);
    const vals = [];
    for (const d of days) {
      vals.push(d.profit || 0);
      vals.push(d.loss || 0);
    }
    const vMax = vals.length ? Math.max(0, ...vals) : 0;
    const vMin = vals.length ? Math.min(0, ...vals) : 0;
    const vRange = vMax - vMin || 1;
    const y = (v) => padT + innerH - (v - vMin) / vRange * innerH;
    const zeroY = y(0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC694\uC77C\uBCC4 \uC190\uC775"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uC774\uC775 \u20A9" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--red)", label: "\uC190\uC2E4 \u20A9" }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: ["\uC694\uC77C\uBCC4 \uC774\uC775/\uC190\uC2E4 \uBD84\uB9AC \uD569(\uB9E4\uC218\uC2DC\uAC01 \uAE30\uC900)", "\uD2B9\uC815 \uC694\uC77C \uD3B8\uD5A5 \uC9C4\uB2E8", "\uB9C9\uB300 \uC704 \uC22B\uC790 = \uC21C\uC190\uC775"] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uC694\uC77C\uBCC4 \uC190\uC775\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: zeroY, y2: zeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(vMax)), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMin) + 3, textAnchor: "end", fill: "var(--red)" }, _gpMoney(vMin)), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }), days.map((d, i) => {
      const pTop = y(d.profit || 0), lBot = y(d.loss || 0);
      const netY = (d.net || 0) >= 0 ? pTop - 4 : lBot + 12;
      return /* @__PURE__ */ React.createElement("g", { key: `w${i}` }, (d.profit || 0) > 0 && /* @__PURE__ */ React.createElement("rect", { x: xC(i) - barW / 2, y: pTop, width: barW, height: Math.max(0.5, zeroY - pTop), fill: "var(--teal)", opacity: "0.78" }), (d.loss || 0) < 0 && /* @__PURE__ */ React.createElement("rect", { x: xC(i) - barW / 2, y: zeroY, width: barW, height: Math.max(0.5, lBot - zeroY), fill: "var(--red)", opacity: "0.78" }), d.trades > 0 && /* @__PURE__ */ React.createElement(
        "text",
        {
          className: "chart-axis-text",
          x: xC(i),
          y: netY,
          textAnchor: "middle",
          fill: (d.net || 0) >= 0 ? "var(--teal)" : "var(--red)",
          style: { fontSize: 9.5 }
        },
        _gpMoney(d.net)
      ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: xC(i), y: H - 10, textAnchor: "middle", style: { fontSize: 12 } }, d.label));
    })))));
  }
  function BtHoldingCurveChart({ data }) {
    const d = data || {};
    const series = d.series || [];
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 240;
    const padL = 64, padR = 24, padT = 18, padB = 28;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const x = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const hMax = n ? Math.max(1, ...series.map((p) => p.holding || 0)) : 1;
    const y = (v) => padT + innerH - Math.max(0, v) / hMax * innerH;
    const path = n < 2 ? "" : series.map((p, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(p.holding || 0).toFixed(1)}`).join(" ");
    const areaPath = n < 2 ? "" : `${path} L ${x(n - 1).toFixed(1)} ${y(0).toFixed(1)} L ${x(0).toFixed(1)} ${y(0).toFixed(1)} Z`;
    const peak = n ? Math.max(...series.map((p) => p.holding || 0)) : 0;
    const partial = (d.covered || 0) < (d.total || 0);
    const _tLabel = (t) => {
      const s = String(t);
      return s.length >= 12 ? s.slice(4, 6) + "/" + s.slice(6, 8) + " " + s.slice(8, 10) + ":" + s.slice(10, 12) : s;
    };
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const i = Math.round(Math.max(0, Math.min(1, (px - padL) / innerW)) * (n - 1));
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--green, #4cd6a0)" } }), "\uBCF4\uC720\uAE08\uC561 \uACE1\uC120"), /* @__PURE__ */ React.createElement(Mini, { label: "\uCD5C\uB300 \uBCF4\uC720", value: fmtMoney(peak) })), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uC9C4\uC785 \uC2DC +\uB9E4\uC218\uAE08\uC561 \xB7 \uCCAD\uC0B0 \uC2DC -\uB9E4\uC218\uAE08\uC561\uC73C\uB85C \uC7AC\uAD6C\uC131\uD55C \uBCF4\uC720 \uC6D0\uAE08 \uD569",
      "GUI \uBCF4\uC720\uAE08\uC561\uC758 \uC815\uC9C1 \uADFC\uC0AC(\uD3C9\uAC00\uC190\uC775\xB7\uC218\uC218\uB8CC \uBBF8\uBC18\uC601, \uC9C4\uC785\uC6D0\uAC00 \uAE30\uC900)",
      partial ? `\uB9E4\uC218\uAE08\uC561 \uACB0\uCE21 \uAC70\uB798 \uC81C\uC678 \u2014 ${d.covered}/${d.total} \uAC70\uB798 \uBC18\uC601` : `${d.total} \uAC70\uB798 \uC804\uBD80 \uBC18\uC601`
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uB9E4\uC218\uAE08\uC561 \uC815\uBCF4\uAC00 \uC788\uB294 \uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uBCF4\uC720\uAE08\uC561 \uACE1\uC120\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(hMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(hMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(0) + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: areaPath, fill: "rgba(76,214,160,0.14)", stroke: "none" }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: path, fill: "none", stroke: "var(--teal)", strokeWidth: "2" }),
      [0, Math.floor(n / 2), n - 1].filter((v, idx, a) => n > 0 && a.indexOf(v) === idx).map((i) => /* @__PURE__ */ React.createElement("text", { key: `hcx${i}`, className: "chart-axis-text", x: x(i), y: H - 9, textAnchor: "middle" }, series[i] ? _tLabel(series[i].time) : "")),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement("line", { x1: x(hover), x2: x(hover), y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.22)", strokeWidth: "1" })
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 160,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, _tLabel(series[hover].time)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uBCF4\uC720\uAE08\uC561"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--teal)" } }, fmtMoney(series[hover].holding)))))));
  }
  function BtTradeRollingChart({ data }) {
    const d = data || {};
    const series = d.series || [];
    const windows = d.windows || [20, 60, 120, 240, 480];
    const [hover, setHover] = useState_btc(null);
    const svgRef = useRef_btc(null);
    const W = 880, H = 280;
    const padL = 60, padR = 24, padT = 18, padB = 30;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const n = series.length;
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, Math.min(14, slot * 0.6));
    const xC = (i) => padL + slot * (i + 0.5);
    const xL = (i) => n > 1 ? padL + i / (n - 1) * innerW : padL + innerW / 2;
    const allVals = [];
    for (const s of series) {
      allVals.push(s.pnl || 0);
      allVals.push(s.cum || 0);
      for (const w of windows) {
        const v = s.roll && s.roll[String(w)];
        if (v != null) allVals.push(v);
      }
    }
    const vMax = allVals.length ? Math.max(0, ...allVals) : 0;
    const vMin = allVals.length ? Math.min(0, ...allVals) : 0;
    const vRange = vMax - vMin || 1;
    const y = (v) => padT + innerH - (v - vMin) / vRange * innerH;
    const zeroY = y(0);
    const ROLL_COLORS = { "20": "var(--red)", "60": "var(--teal)", "120": "var(--blue)", "240": "var(--ink-3)", "480": "var(--ink-1)" };
    const cumPath = n < 2 ? "" : series.map((s, i) => `${i === 0 ? "M" : "L"} ${xL(i).toFixed(1)} ${y(s.cum || 0).toFixed(1)}`).join(" ");
    const rollPath = (w) => {
      const key = String(w);
      let dStr = "";
      let started = false;
      series.forEach((s, i) => {
        const v = s.roll && s.roll[key];
        if (v == null) {
          started = false;
          return;
        }
        dStr += `${started ? "L" : "M"} ${xL(i).toFixed(1)} ${y(v).toFixed(1)} `;
        started = true;
      });
      return dStr.trim();
    };
    const onMove = (e) => {
      if (!n || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      const i = Math.floor((px - padL) / slot);
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uAC70\uB798\uBCC4 \uC190\uC775 \xB7 \uB864\uB9C1 \uD3C9\uADE0"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--amber)", label: "\uB204\uC801 \u20A9" }), windows.map((w) => /* @__PURE__ */ React.createElement(LegendDot, { key: w, color: ROLL_COLORS[String(w)] || "var(--ink-2)", label: `MA${w}` })))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement(MetricHelpStrip, { items: [
      "\uAC70\uB798\uBCC4 \uC2E4\uD604\uC190\uC775(\uB9C9\uB300) + \uB204\uC801\uC190\uC775(\uC8FC\uD669) + \uB204\uC801\uC190\uC775 \uC774\uB3D9\uD3C9\uADE0(\uCC3D 20/60/120/240/480)",
      "\uB864\uB9C1 \uB77C\uC778\uC774 \uC6B0\uC0C1\uD5A5\uC774\uBA74 \uB204\uC801 \uC131\uC7A5 \uAC00\uC18D",
      "\uCC3D\uBCF4\uB2E4 \uAC70\uB798\uAC00 \uC801\uC73C\uBA74 \uD574\uB2F9 \uB864\uB9C1\uC120\uC740 \uC0DD\uB7B5"
    ] }), /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, n === 0 && /* @__PURE__ */ React.createElement(_BtChartEmpty, { message: "\uAC70\uB798\uAC00 \uB204\uC801\uB418\uBA74 \uAC70\uB798\uBCC4 \uC190\uC775\xB7\uB864\uB9C1\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4" }), /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: zeroY, y2: zeroY, stroke: "rgba(255,255,255,0.28)", strokeWidth: "1", strokeDasharray: "2 3" }),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: zeroY + 3, textAnchor: "end", fill: "var(--ink-2)" }, "0"),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMax) + 3, textAnchor: "end", fill: "var(--teal)" }, _gpMoney(vMax)),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(vMin) + 3, textAnchor: "end", fill: "var(--red)" }, _gpMoney(vMin)),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      series.map((s, i) => {
        const v = s.pnl || 0;
        const y0 = zeroY, y1 = y(v);
        return /* @__PURE__ */ React.createElement(
          "rect",
          {
            key: `tr${i}`,
            x: xC(i) - barW / 2,
            y: Math.min(y0, y1),
            width: barW,
            height: Math.max(0.5, Math.abs(y1 - y0)),
            fill: v >= 0 ? "var(--teal)" : "var(--red)",
            opacity: hover === i ? 0.95 : 0.45
          }
        );
      }),
      windows.map((w) => {
        const p = rollPath(w);
        return p ? /* @__PURE__ */ React.createElement("path", { key: `rp${w}`, d: p, fill: "none", stroke: ROLL_COLORS[String(w)] || "var(--ink-2)", strokeWidth: "1.3", opacity: "0.9" }) : null;
      }),
      n > 1 && /* @__PURE__ */ React.createElement("path", { d: cumPath, fill: "none", stroke: "var(--amber)", strokeWidth: "2" }),
      hover != null && series[hover] && /* @__PURE__ */ React.createElement("line", { x1: xC(hover), x2: xC(hover), y1: padT, y2: padT + innerH, stroke: "rgba(255,255,255,0.22)", strokeWidth: "1" })
    ), hover != null && series[hover] && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 16,
      right: 16,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 170,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, "\uAC70\uB798 #", series[hover].index + 1), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC190\uC775"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: (series[hover].pnl || 0) >= 0 ? "var(--teal)" : "var(--red)" } }, fmtMoney(series[hover].pnl)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB204\uC801"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right", color: "var(--amber)" } }, fmtMoney(series[hover].cum)))))));
  }
  function BtGuiParitySection({ guiParity, columns }) {
    const gp = guiParity || {};
    const grid = columns === 2;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "GUI \uD328\uB9AC\uD2F0 \u2014 STOM \uBC31\uD14C\uC2A4\uD2B8 \uACB0\uACFC \uC774\uBBF8\uC9C0 2\uC7A5"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uBD80\uAC00\uC815\uBCF4 2\xD72 \xB7 \uACB0\uACFC 2\xD71")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { style: grid ? { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 14 } : { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement(BtMddRandomChart, { data: gp.mdd_random }), /* @__PURE__ */ React.createElement(BtDailyPnlChart, { data: gp.daily }), /* @__PURE__ */ React.createElement(BtHourlyPnlChart, { data: gp.hourly }), /* @__PURE__ */ React.createElement(BtWeekdayPnlChart, { data: gp.weekday }), /* @__PURE__ */ React.createElement(BtHoldingCurveChart, { data: gp.holding }), /* @__PURE__ */ React.createElement(BtTradeRollingChart, { data: gp.trade_rolling }))));
  }

  // ../frontend/bt-result-area.jsx
  var _BT_METRIC_CARDS = [
    { key: "trade_count", label: "\uAC70\uB798\uC218", fmt: (v) => fmtInt(v) },
    { key: "win_rate", label: "\uC2B9\uB960", fmt: (v) => fmtPct(v) },
    { key: "total_profit_pct", label: "\uC218\uC775\uB960\uD569\uACC4", fmt: (v) => fmtPct(v), signed: true },
    { key: "total_profit_krw", label: "\uC218\uC775\uAE08", fmt: (v) => fmtMoney(v), signed: true },
    { key: "mdd_pct", label: "MDD", fmt: (v) => fmtPct(v), risk: true },
    { key: "cagr", label: "CAGR", fmt: (v) => fmtPct(v), signed: true }
  ];
  function BtResultArea({ baseUrl, isDemo, jobId, evoSource, onSetCompareA, compareView, onCloseCompare }) {
    const [result, setResult] = useState_btc(null);
    const [loading, setLoading] = useState_btc(false);
    const [err, setErr] = useState_btc("");
    const [range, setRange] = useState_btc(null);
    const [mc, setMc] = useState_btc(null);
    const [mcLoading, setMcLoading] = useState_btc(false);
    const [fullscreen, setFullscreen] = useState_btc(false);
    useEffect_btc(() => {
      if (!fullscreen) return void 0;
      const onKey = (e) => {
        if (e.key === "Escape") setFullscreen(false);
      };
      window.addEventListener("keydown", onKey);
      const prevOverflow = document.body.style.overflow;
      document.body.style.overflow = "hidden";
      return () => {
        window.removeEventListener("keydown", onKey);
        document.body.style.overflow = prevOverflow;
      };
    }, [fullscreen]);
    const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);
    const hasSource = !!jobId || isEvo;
    const sourceKey = jobId || (isEvo ? evoSource.run_id + "/" + evoSource.gen_no : "");
    const load = useCallback_btc(() => {
      if (isDemo || !baseUrl || !hasSource) {
        setResult(null);
        return;
      }
      setLoading(true);
      setErr("");
      let url;
      if (jobId) {
        url = baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId);
        if (range) {
          url += "&t_start=" + range.t_start + "&t_end=" + range.t_end;
        }
      } else {
        url = baseUrl + "/bt/result?run_id=" + encodeURIComponent(evoSource.run_id) + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
      }
      _btFetchJson(url, 8e3).then((j) => {
        setResult(j);
        if (!(j && j.available)) setErr("\uACB0\uACFC\uB97C \uCC3E\uC744 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4");
      }).catch((e) => {
        setResult(null);
        setErr(String(e));
      }).finally(() => setLoading(false));
    }, [baseUrl, isDemo, jobId, isEvo, sourceKey, range]);
    const loadMc = useCallback_btc(() => {
      if (isDemo || !baseUrl || !jobId) {
        setMc(null);
        return;
      }
      setMcLoading(true);
      let url = baseUrl + "/bt/analysis/montecarlo?job_id=" + encodeURIComponent(jobId) + "&n=2000";
      if (range) {
        url += "&t_start=" + range.t_start + "&t_end=" + range.t_end;
      }
      _btFetchJson(url, 12e3).then((j) => setMc(j && j.montecarlo || null)).catch(() => setMc(null)).finally(() => setMcLoading(false));
    }, [baseUrl, isDemo, jobId, range]);
    useEffect_btc(() => {
      load();
    }, [load]);
    useEffect_btc(() => {
      setRange(null);
      setMc(null);
    }, [sourceKey]);
    useEffect_btc(() => {
      if (jobId && result && result.available && result.status !== "no_trades") {
        loadMc();
      }
    }, [result, loadMc, jobId]);
    const onBrush = useCallback_btc((t_start, t_end) => {
      if (!jobId) {
        return;
      }
      setRange({ t_start, t_end });
    }, [jobId]);
    const onBrushClear = useCallback_btc(() => {
      setRange(null);
    }, []);
    if (!hasSource) {
      return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uACB0\uACFC \xB7 \uBD84\uC11D")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC67C\uCABD\uC5D0\uC11C \uBC31\uD14C\uC2A4\uD2B8\uB97C \uC2E4\uD589\uD558\uAC70\uB098 \uC7A1 \uC774\uB825\uC744 \uC120\uD0DD\uD558\uBA74 \uACB0\uACFC\xB7\uBD84\uC11D\uC774 \uC5EC\uAE30\uC5D0 \uD45C\uC2DC\uB429\uB2C8\uB2E4.")));
    }
    if (loading && !result) {
      return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uACB0\uACFC \xB7 \uBD84\uC11D")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uACB0\uACFC \uB85C\uB529 \uC911\u2026")));
    }
    if (err || !result || !result.available) {
      return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uACB0\uACFC \xB7 \uBD84\uC11D")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { color: "var(--red)" } }, err || "\uACB0\uACFC \uC5C6\uC74C", /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: load }, "\uC7AC\uC2DC\uB3C4")))));
    }
    if (result.status === "no_trades") {
      return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uACB0\uACFC \xB7 \uBD84\uC11D"), /* @__PURE__ */ React.createElement("span", { className: "badge warn" }, "\uAC70\uB798 0\uAC74")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "empty", style: { padding: "28px 24px" } }, /* @__PURE__ */ React.createElement("h2", { style: { color: "var(--amber)" } }, "\uAC70\uB798 0\uAC74"), /* @__PURE__ */ React.createElement("p", null, result.message || "\uC804\uB7B5\uC774 \uD574\uB2F9 \uAE30\uAC04\uC5D0 \uB9E4\uC218 \uC2E0\uD638\uB97C \uB0B4\uC9C0 \uC54A\uC558\uC2B5\uB2C8\uB2E4. \uC5D0\uB7EC\uAC00 \uC544\uB2D9\uB2C8\uB2E4 \u2014 \uC870\uAC74\uC2DD/\uAE30\uAC04\uC744 \uC870\uC815\uD574 \uBCF4\uC138\uC694."))));
    }
    const analysis = result.analysis || {};
    const metrics = result.metrics || {};
    const summary = analysis.summary || {};
    const metricVal = (key) => {
      if (metrics[key] != null) return metrics[key];
      const map = {
        trade_count: summary.trade_count,
        win_rate: summary.win_rate,
        total_profit_pct: summary.total_profit_pct,
        total_profit_krw: summary.total_profit_krw,
        mdd_pct: summary.max_drawdown_pct,
        cagr: void 0
      };
      return map[key];
    };
    const distribution = analysis.distribution || {};
    const insights = analysis.insights || [];
    const topC = distribution.top_contributors || [];
    const botC = distribution.bottom_contributors || [];
    const dailyPnl = ((analysis.equity || {}).daily || []).map((d) => d.pnl || 0);
    const orderflow = analysis.orderflow || {};
    const stats = analysis.stats || [];
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14 } }, range && /* @__PURE__ */ React.createElement("div", { className: "bt-range-bar" }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--teal)" } }, "\u25E7 \uAD6C\uAC04 \uBD84\uC11D \uC801\uC6A9 \uC911 \u2014 ", _btDateLabel(Math.floor(range.t_start / 1e6)), "~", _btDateLabel(Math.floor(range.t_end / 1e6)), result.ranged && analysis.trade_count != null ? ` \xB7 ${analysis.trade_count}\uAC70\uB798` : ""), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onBrushClear, style: { marginLeft: "auto" } }, "\uC804\uCCB4\uB85C \uBCF5\uADC0")), /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: isEvo ? "var(--violet)" : "var(--teal)" } }), isEvo ? "\uD575\uC2EC \uBA54\uD2B8\uB9AD \xB7 \uC9C4\uD654 \uC138\uB300" : "\uD575\uC2EC \uBA54\uD2B8\uB9AD", isEvo && /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono tag-slim",
        style: { fontSize: 9.5, color: "var(--violet)", marginLeft: 6 },
        title: "\uC9C4\uD654 run \uC138\uB300 \uBD84\uC11D \u2014 loop_runs.db \uC77D\uAE30 \uC804\uC6A9"
      },
      evoSource.run_id,
      "/g",
      evoSource.gen_no
    )), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "center" } }, onSetCompareA && jobId && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => onSetCompareA(jobId),
        title: "\uC774 \uC7A1\uC744 A/B \uBE44\uAD50\uC758 \uAE30\uC900(A)\uC73C\uB85C \uACE0\uC815"
      },
      "\u2295 \uBE44\uAD50 \uAE30\uC900(A)"
    ), isEvo && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => {
          const u = baseUrl + "/bt/report?run_id=" + encodeURIComponent(evoSource.run_id) + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
          try {
            window.open(u, "_blank", "noopener");
          } catch (e) {
          }
        },
        title: "\uC774 \uC138\uB300\uC758 \uC790\uAE09\uC790\uC871 HTML \uB9AC\uD3EC\uD2B8\uB97C \uC0C8 \uD0ED\uC73C\uB85C \uC5F4\uAE30"
      },
      "\u{1F4C4} \uB9AC\uD3EC\uD2B8"
    ), ((analysis.equity || {}).daily || []).length > 0 && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => _btDownloadAnalysisCsv(analysis),
        title: "\uC77C\uBCC4 \uC218\uC775\uACE1\uC120(\uB0A0\uC9DC\xB7\uC77C\uBCC4\uC190\uC775\xB7\uB204\uC801\uC218\uC775)\uC744 CSV \uB85C \uB0B4\uB824\uBC1B\uAE30 \u2014 \uD45C\uACC4\uC0B0 \uB3C4\uAD6C\uC5D0\uC11C \uCD94\uAC00 \uBD84\uC11D"
      },
      "\u2B07 CSV"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => setFullscreen(true),
        title: "\uC804\uCCB4 \uD654\uBA74\uC5D0\uC11C \uB354 \uB9CE\uC740 \uBD84\uC11D \uADF8\uB798\uD504\uB97C \uD55C\uB208\uC5D0 \uBCF4\uAE30 (Esc \uB85C \uB2EB\uAE30)"
      },
      "\u26F6 \uC804\uCCB4\uD654\uBA74 \uBD84\uC11D"
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: load, disabled: loading }, loading ? "\uB85C\uB529\u2026" : "\u21BB"))), /* @__PURE__ */ React.createElement("div", { className: "bt-summary-row", style: { gridTemplateColumns: "repeat(6, 1fr)" } }, _BT_METRIC_CARDS.map((m) => {
      const v = metricVal(m.key);
      const num = typeof v === "number" ? v : null;
      return /* @__PURE__ */ React.createElement(_BtMetricCard, { key: m.key, meta: m, num, dailyPnl });
    }))), compareView && /* @__PURE__ */ React.createElement(BtCompareView, { cmp: compareView, onClose: onCloseCompare }), /* @__PURE__ */ React.createElement(
      BtEquityChart,
      {
        equity: analysis.equity,
        onBrush,
        brushActive: !!range,
        onBrushClear
      }
    ), /* @__PURE__ */ React.createElement(BtDistributionChart, { distribution }), /* @__PURE__ */ React.createElement(BtHeatmap, { heatmap: analysis.heatmap }), /* @__PURE__ */ React.createElement(BtUnderwaterChart, { underwater: analysis.underwater }), /* @__PURE__ */ React.createElement(BtMaeMfeScatter, { points: analysis.mae_mfe }), /* @__PURE__ */ React.createElement(BtExitReasonPanel, { rows: analysis.exit_reasons }), /* @__PURE__ */ React.createElement(BtMonteCarloChart, { mc, loading: mcLoading, onRun: loadMc }), /* @__PURE__ */ React.createElement(BtOrderflowPanel, { orderflow }), /* @__PURE__ */ React.createElement(BtStatTestPanel, { stats }), /* @__PURE__ */ React.createElement(BtGuiParitySection, { guiParity: analysis.gui_parity, columns: 1 }), /* @__PURE__ */ React.createElement("details", { className: "bt-extra-charts", open: false }, /* @__PURE__ */ React.createElement("summary", { style: { cursor: "pointer", padding: "10px 14px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--ink-2)", userSelect: "none" } }, "\u25B8 \uCD94\uAC00 \uBD84\uC11D \uADF8\uB798\uD504 \u2014 \uB864\uB9C1 \uC9C0\uD45C \xB7 \uC6D4\uBCC4 \uCE98\uB9B0\uB354 \xB7 \uB204\uC801 \uAC70\uB798 (\uC804\uCCB4\uD654\uBA74 \uAD8C\uC7A5)"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14, marginTop: 10 } }, /* @__PURE__ */ React.createElement(BtRollingChart, { rolling: analysis.rolling }), /* @__PURE__ */ React.createElement(BtMonthlyCalendar, { monthly: analysis.monthly }), /* @__PURE__ */ React.createElement(BtCumulativeTradesChart, { data: analysis.cumulative_trades }))), (topC.length > 0 || botC.length > 0) && /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uC885\uBAA9 \uAE30\uC5EC")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "row-2" }, /* @__PURE__ */ React.createElement(BtContribTable, { title: "\uC0C1\uC704 \uAE30\uC5EC", rows: topC }), /* @__PURE__ */ React.createElement(BtContribTable, { title: "\uD558\uC704 \uAE30\uC5EC", rows: botC })))), /* @__PURE__ */ React.createElement(BtInsightsPanel, { insights }), fullscreen && /* @__PURE__ */ React.createElement(
      _BtFullscreenAnalysis,
      {
        analysis,
        distribution,
        orderflow,
        stats,
        insights,
        mc,
        mcLoading,
        onRunMc: loadMc,
        range,
        onBrush,
        onBrushClear,
        onClose: () => setFullscreen(false)
      }
    ));
  }
  function _BtFullscreenAnalysis({
    analysis,
    distribution,
    orderflow,
    stats,
    insights,
    mc,
    mcLoading,
    onRunMc,
    range,
    onBrush,
    onBrushClear,
    onClose
  }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      position: "fixed",
      inset: 0,
      zIndex: 4e3,
      background: "var(--bg-1, #0d1117)",
      overflowY: "auto",
      padding: "16px 22px 40px"
    } }, /* @__PURE__ */ React.createElement("div", { style: {
      position: "sticky",
      top: 0,
      zIndex: 2,
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "10px 4px 12px",
      marginBottom: 10,
      background: "var(--bg-1, #0d1117)",
      borderBottom: "1px solid var(--line-2)"
    } }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), /* @__PURE__ */ React.createElement("strong", { style: { fontSize: 15, color: "var(--ink-0)" } }, "\uC804\uCCB4\uD654\uBA74 \uBD84\uC11D"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uB354 \uB9CE\uC740 \uADF8\uB798\uD504\uB85C \uC778\uC0AC\uC774\uD2B8 \u2014 2~3\uCEEC\uB7FC \uD655\uB300 \uBC30\uCE58"), range && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--teal)" } }, "\u25E7 \uAD6C\uAC04 \uBD84\uC11D \uC801\uC6A9 \uC911"), /* @__PURE__ */ React.createElement("div", { style: { marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" } }, range && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onBrushClear }, "\uC804\uCCB4\uB85C \uBCF5\uADC0"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn sm",
        onClick: onClose,
        style: { borderColor: "var(--teal-dim)", color: "var(--teal)" }
      },
      "\u2715 \uB2EB\uAE30 (Esc)"
    ))), /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 14 } }, /* @__PURE__ */ React.createElement(BtInsightsPanel, { insights })), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: 14, marginBottom: 14 } }, /* @__PURE__ */ React.createElement(BtRollingChart, { rolling: analysis.rolling }), /* @__PURE__ */ React.createElement(BtCumulativeTradesChart, { data: analysis.cumulative_trades }), /* @__PURE__ */ React.createElement(BtMonthlyCalendar, { monthly: analysis.monthly }), /* @__PURE__ */ React.createElement(
      BtEquityChart,
      {
        equity: analysis.equity,
        onBrush,
        brushActive: !!range,
        onBrushClear
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { marginBottom: 14 } }, /* @__PURE__ */ React.createElement(BtGuiParitySection, { guiParity: analysis.gui_parity, columns: 2 })), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: 14 } }, /* @__PURE__ */ React.createElement(BtDistributionChart, { distribution }), /* @__PURE__ */ React.createElement(BtUnderwaterChart, { underwater: analysis.underwater }), /* @__PURE__ */ React.createElement(BtHeatmap, { heatmap: analysis.heatmap }), /* @__PURE__ */ React.createElement(BtMaeMfeScatter, { points: analysis.mae_mfe }), /* @__PURE__ */ React.createElement(BtMonteCarloChart, { mc, loading: mcLoading, onRun: onRunMc }), /* @__PURE__ */ React.createElement(BtExitReasonPanel, { rows: analysis.exit_reasons }), /* @__PURE__ */ React.createElement(BtOrderflowPanel, { orderflow }), /* @__PURE__ */ React.createElement(BtStatTestPanel, { stats })));
  }
  function _BtMetricCard({ meta, num, dailyPnl }) {
    const animated = _useCountUp(num != null ? num : 0, 600);
    const shown = num != null ? animated : null;
    let color;
    if (meta.risk) color = "var(--red)";
    else if (meta.signed && num != null) color = num > 0 ? "var(--teal)" : num < 0 ? "var(--red)" : void 0;
    if ((meta.key === "win_rate" || meta.key === "mdd_pct") && num != null) {
      const gaugeColor = meta.key === "mdd_pct" ? "var(--red)" : "var(--teal)";
      return /* @__PURE__ */ React.createElement("div", { className: "bt-metric-card" }, /* @__PURE__ */ React.createElement("span", { className: "summary-lbl" }, meta.label), /* @__PURE__ */ React.createElement(
        _BtArcGauge,
        {
          value: shown,
          max: 100,
          color: gaugeColor,
          label: meta.fmt(shown != null ? shown : 0)
        }
      ));
    }
    if (meta.key === "total_profit_krw") {
      return /* @__PURE__ */ React.createElement("div", { className: "bt-metric-card" }, /* @__PURE__ */ React.createElement("span", { className: "summary-lbl" }, meta.label), /* @__PURE__ */ React.createElement("span", { className: "summary-val", style: { color } }, shown != null ? meta.fmt(shown) : "\u2014"), /* @__PURE__ */ React.createElement(_BtSparkline, { values: dailyPnl }));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "bt-metric-card" }, /* @__PURE__ */ React.createElement("span", { className: "summary-lbl" }, meta.label), /* @__PURE__ */ React.createElement("span", { className: "summary-val", style: { color } }, shown != null ? meta.fmt(shown) : "\u2014"));
  }

  // ../frontend/backtest-charts.jsx
  Object.assign(window, {
    BtEquityChart,
    BtDistributionChart,
    BtHeatmap,
    BtUnderwaterChart,
    BtResultArea,
    BtMaeMfeScatter,
    BtExitReasonPanel,
    BtMonteCarloChart,
    BtOrderflowPanel,
    BtStatTestPanel,
    BtCompareView,
    BtRollingChart,
    BtMonthlyCalendar,
    BtCumulativeTradesChart,
    BtMddRandomChart,
    BtDailyPnlChart,
    BtHourlyPnlChart,
    BtWeekdayPnlChart,
    BtHoldingCurveChart,
    BtTradeRollingChart,
    BtGuiParitySection
  });

  // ../frontend/bt-tab-utils.jsx
  var {
    useState: useState_bt,
    useEffect: useEffect_bt,
    useCallback: useCallback_bt,
    useRef: useRef_bt,
    useMemo: useMemo_bt
  } = React;
  function _btFetchJson2(url, timeoutMs) {
    return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 5e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  function _btPostJson(url, body, timeoutMs) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal: AbortSignal.timeout(timeoutMs || 8e3)
    }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  function _btWsUrl(baseUrl, path) {
    let origin = baseUrl || (window.location ? window.location.origin : "");
    origin = origin.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
    if (!/^wss?:/i.test(origin)) {
      const loc = window.location || {};
      const proto = loc.protocol === "https:" ? "wss:" : "ws:";
      origin = proto + "//" + (loc.host || "");
    }
    return origin.replace(/\/$/, "") + path;
  }
  var _BT_JOB_BADGE = {
    pending: { txt: "\uB300\uAE30", cls: "badge idle" },
    running: { txt: "\uC2E4\uD589\uC911", cls: "badge run" },
    success: { txt: "\uC131\uACF5", cls: "badge done" },
    no_trades: { txt: "\uAC70\uB798 0\uAC74", cls: "badge warn" },
    error: { txt: "\uC624\uB958", cls: "badge err" },
    timeout: { txt: "\uC2DC\uAC04\uCD08\uACFC", cls: "badge err" },
    cancelled: { txt: "\uCDE8\uC18C\uB428", cls: "badge idle" }
  };
  var _BT_MODE_RUN_LABEL = {
    backtest: "\uBC31\uD14C\uC2A4\uD2B8 \uC2E4\uD589",
    optimize: "\uCD5C\uC801\uD654 \uC2E4\uD589",
    wfo: "\uC804\uC9C4\uBD84\uC11D \uC2E4\uD589",
    sweep: "\uC2A4\uC715 \uC2E4\uD589"
  };
  var _BT_MODE_TIP = {
    backtest: "\uBC31\uD14C\uC2A4\uD2B8 \u2014 \uACE0\uB978 \uAE30\uAC04\uC5D0 \uB9E4\uC218/\uB9E4\uB3C4 \uC870\uAC74\uC2DD\uC744 1\uD68C \uC2DC\uBBAC\uB808\uC774\uC158\uD569\uB2C8\uB2E4.",
    optimize: "\uCD5C\uC801\uD654 \u2014 \uD30C\uB77C\uBBF8\uD130 \uD0D0\uC0C9\uACF5\uAC04\uC744 \uACA9\uC790\uB85C \uD6D1\uC5B4 \uCD5C\uC801 \uC870\uD569\uC744 \uCC3E\uC2B5\uB2C8\uB2E4.",
    wfo: "WFO(\uC804\uC9C4\uBD84\uC11D, Walk-Forward) \u2014 \uD6C8\uB828 \uAD6C\uAC04\uC5D0\uC11C \uD30C\uB77C\uBBF8\uD130\uB97C \uACE0\uB978 \uB4A4, \uBC14\uB85C \uB2E4\uC74C \uBBF8\uD559\uC2B5 \uAD6C\uAC04\uC5D0\uC11C \uAC80\uC99D\uD558\uAE30\uB97C \uAD74\uB824\uAC00\uBA70 \uBC18\uBCF5\uD569\uB2C8\uB2E4(\uACFC\uCD5C\uC801\uD654 \uC810\uAC80).",
    sweep: "\uC2A4\uC715(sweep) \u2014 \uD30C\uB77C\uBBF8\uD130 \uC870\uD569 \uB610\uB294 \uB0A0\uC9DC \uC708\uB3C4\uC6B0\uB97C \uC77C\uAD04\uB85C \uC4F8\uC5B4\uAC00\uBA70 \uC131\uACFC \uC9C0\uD615(\uACE0\uC6D0/\uC808\uBCBD)\uC744 \uD3BC\uCCD0 \uBD05\uB2C8\uB2E4."
  };
  var _BT_YEAR = (/* @__PURE__ */ new Date()).getFullYear();
  var _BT_START_EG = _BT_YEAR + "0101";
  var _BT_END_EG = _BT_YEAR + "1231";
  function _btElapsed(rec) {
    const s = rec.started_at;
    if (!s) return "\u2014";
    const end = rec.finished_at || Date.now() / 1e3;
    const sec = Math.max(0, Math.round(end - s));
    if (sec < 60) return sec + "s";
    return Math.floor(sec / 60) + "m " + sec % 60 + "s";
  }
  function _btNum(v, digits) {
    const n = Number(v);
    if (v == null || isNaN(n)) return "\u2014";
    return n.toFixed(digits == null ? 2 : digits);
  }
  function _BtRowDetail({ label, data, numeric }) {
    const keys = Object.keys(data || {});
    return /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-2)", display: "flex", flexWrap: "wrap", gap: 14, marginTop: 4 } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", minWidth: 80 } }, label), keys.length === 0 ? /* @__PURE__ */ React.createElement("span", null, "\u2014") : keys.map((k) => /* @__PURE__ */ React.createElement("span", { key: k }, k, "=", /* @__PURE__ */ React.createElement("b", { style: { color: "var(--ink-1)" } }, numeric ? _btNum(data[k]) : String(data[k])))));
  }
  var _BT_OVERLAY_COLORS = ["var(--teal)", "var(--amber)", "var(--violet)", "var(--blue)"];
  function _btSweepRowCount(rows) {
    if (!Array.isArray(rows)) return 0;
    return rows.filter((r) => r && String(r.name || "").trim()).length;
  }
  function _btSweepValueCount(row) {
    if (!row) return 0;
    const lo = Number(row.min), hi = Number(row.max), step = Number(row.step);
    if (!isFinite(lo) || !isFinite(hi)) return 0;
    if (!isFinite(step) || step <= 0 || lo > hi) return 1;
    return Math.min(64, Math.floor((hi - lo) / step + 1e-9) + 1);
  }
  function _pfFmtMoney(v) {
    const n = Number(v) || 0;
    return (n >= 0 ? "+" : "") + Math.round(n).toLocaleString() + "\uC6D0";
  }

  // ../frontend/bt-tab-library.jsx
  function BtLibraryPanel({ baseUrl, isDemo, kind, onKind, onPick, selectedName, reloadKey, lockKind }) {
    const [items, setItems] = useState_bt([]);
    const [query, setQuery] = useState_bt("");
    const [err, setErr] = useState_bt("");
    const [loading, setLoading] = useState_bt(false);
    const load = useCallback_bt(() => {
      if (isDemo || !baseUrl) {
        setItems([]);
        return;
      }
      setLoading(true);
      setErr("");
      _btFetchJson2(baseUrl + "/bt/strategies?kind=" + encodeURIComponent(kind), 4e3).then((j) => setItems(Array.isArray(j && j.items) ? j.items : [])).catch((e) => {
        setItems([]);
        setErr(String(e));
      }).finally(() => setLoading(false));
    }, [baseUrl, isDemo, kind, reloadKey]);
    useEffect_bt(() => {
      load();
    }, [load]);
    const filtered = useMemo_bt(() => {
      const q = query.trim().toLowerCase();
      if (!q) return items;
      return items.filter((it) => (it.name || "").toLowerCase().includes(q));
    }, [items, query]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { display: "flex", flexDirection: "column", minHeight: 0 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uC870\uAC74\uC2DD \uB77C\uC774\uBE0C\uB7EC\uB9AC", lockKind && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginLeft: 6 } }, kind === "buy" ? "\uB9E4\uC218" : kind === "sell" ? "\uB9E4\uB3C4" : "\uC218\uC2DD")), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: load, disabled: isDemo || loading }, loading ? "\uB85C\uB529\u2026" : "\u21BB")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, !lockKind && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["buy", "\uB9E4\uC218"], ["sell", "\uB9E4\uB3C4"], ["formula", "\uC218\uC2DD"]].map(([k, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: k,
        onClick: () => onKind(k),
        className: "mono",
        style: {
          flex: 1,
          padding: "5px 8px",
          fontSize: 11,
          borderRadius: 5,
          border: "1px solid " + (kind === k ? "var(--teal-dim)" : "var(--line-1)"),
          background: kind === k ? "rgba(76,214,179,0.08)" : "transparent",
          color: kind === k ? "var(--teal)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      lbl
    ))), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        placeholder: "\uC774\uB984 \uAC80\uC0C9\u2026",
        value: query,
        onChange: (e) => setQuery(e.target.value),
        spellCheck: false
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 3, maxHeight: 420, overflowY: "auto" } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC870\uAC74\uC2DD \uBAA9\uB85D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : err ? /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { color: "var(--red)" } }, "\uC870\uD68C \uC2E4\uD328: ", err, /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: load }, "\uC7AC\uC2DC\uB3C4"))) : filtered.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, query ? "\uAC80\uC0C9 \uACB0\uACFC \uC5C6\uC74C" : "\uC870\uAC74\uC2DD\uC774 \uC5C6\uC2B5\uB2C8\uB2E4") : filtered.map((it) => {
      const active = it.name === selectedName;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: it.name,
          onClick: () => onPick(it.name),
          style: {
            textAlign: "left",
            padding: "7px 9px",
            borderRadius: 5,
            cursor: "pointer",
            border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
            background: active ? "rgba(76,214,179,0.07)" : "var(--bg-0)",
            display: "flex",
            flexDirection: "column",
            gap: 3
          }
        },
        /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11.5, color: active ? "var(--teal)" : "var(--ink-0)", wordBreak: "break-all" } }, it.name), it.is_ailoop && /* @__PURE__ */ React.createElement("span", { className: "tag-slim", style: { color: "var(--violet)" } }, "AILOOP")),
        it.preview && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" } }, it.preview)
      );
    })), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, filtered.length, "\uAC1C \uD45C\uC2DC / \uC804\uCCB4 ", items.length, "\uAC1C")));
  }
  function BtVarChips({ baseUrl, isDemo, code }) {
    const [known, setKnown] = useState_bt([]);
    const [unknown, setUnknown] = useState_bt([]);
    useEffect_bt(() => {
      if (isDemo || !baseUrl) {
        setKnown([]);
        setUnknown([]);
        return;
      }
      const trimmed = (code || "").trim();
      if (!trimmed) {
        setKnown([]);
        setUnknown([]);
        return;
      }
      let cancelled = false;
      const t = setTimeout(() => {
        _btPostJson(baseUrl + "/bt/extract_vars", { code: trimmed }, 5e3).then((j) => {
          if (cancelled) return;
          setKnown(Array.isArray(j && j.known) ? j.known : []);
          setUnknown(Array.isArray(j && j.unknown) ? j.unknown : []);
        }).catch(() => {
          if (!cancelled) {
            setKnown([]);
            setUnknown([]);
          }
        });
      }, 400);
      return () => {
        cancelled = true;
        clearTimeout(t);
      };
    }, [baseUrl, isDemo, code]);
    if (known.length === 0 && unknown.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC0AC\uC6A9 \uBCC0\uC218 \uCE69 \u2014 \uCF54\uB4DC \uC785\uB825 \uC2DC \uD55C\uAE00 \uBCC0\uC218\uAC00 SSOT \uB300\uC870\uB418\uC5B4 \uD45C\uC2DC\uB429\uB2C8\uB2E4.");
    }
    const chip = (v, ok) => /* @__PURE__ */ React.createElement(
      "span",
      {
        key: (ok ? "k:" : "u:") + v.name,
        className: "mono",
        title: ok ? "SSOT \uD654\uC774\uD2B8\uB9AC\uC2A4\uD2B8 \uBCC0\uC218" : "SSOT \uC5B4\uD718 \uBC16 \u2014 \uC624\uD0C0\uC774\uAC70\uB098 \uC815\uC758\uB418\uC9C0 \uC54A\uC740 \uBCC0\uC218\uC77C \uC218 \uC788\uC2B5\uB2C8\uB2E4",
        style: {
          fontSize: 10,
          padding: "2px 6px",
          borderRadius: 4,
          border: "1px solid " + (ok ? "var(--teal-dim)" : "rgba(240,179,90,0.45)"),
          color: ok ? "var(--teal)" : "var(--amber)",
          background: ok ? "rgba(76,214,179,0.06)" : "rgba(240,179,90,0.06)",
          display: "inline-flex",
          alignItems: "center",
          gap: 4
        }
      },
      ok ? "" : "\u26A0 ",
      v.name,
      v.count > 1 && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, "\xD7", v.count)
    );
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 5 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 4 } }, known.map((v) => chip(v, true)), unknown.map((v) => chip(v, false))), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "SSOT \uBCC0\uC218 ", known.length, " \xB7 \uBBF8\uD655\uC778 ", unknown.length));
  }
  function BtCodeEditor({ baseUrl, isDemo, kind, label, accent, name, onSaved, onDeleted }) {
    const [code, setCode] = useState_bt("");
    const [editName, setEditName] = useState_bt("");
    const [loadedName, setLoadedName] = useState_bt("");
    const [validate, setValidate] = useState_bt(null);
    const [busy, setBusy] = useState_bt("");
    const [msg, setMsg] = useState_bt(null);
    const [confirmDel, setConfirmDel] = useState_bt("");
    useEffect_bt(() => {
      if (isDemo || !baseUrl || !name) {
        if (!name) {
          setCode("");
          setEditName("");
          setLoadedName("");
          setValidate(null);
          setMsg(null);
        }
        return;
      }
      _btFetchJson2(baseUrl + "/bt/strategy?kind=" + encodeURIComponent(kind) + "&name=" + encodeURIComponent(name), 4e3).then((j) => {
        if (j && j.available) {
          setCode(j.code || "");
          setEditName(j.name || name);
          setLoadedName(j.name || name);
        } else {
          setCode("");
          setEditName(name);
          setLoadedName("");
        }
        setValidate(null);
        setMsg(null);
      }).catch(() => setMsg({ kind: "error", text: "\uC870\uAC74\uC2DD \uB85C\uB4DC \uC2E4\uD328" }));
    }, [baseUrl, isDemo, kind, name]);
    const lineCount = useMemo_bt(() => code.split("\n").length, [code]);
    const runValidate = () => {
      if (isDemo) return;
      setBusy("validate");
      setMsg(null);
      _btPostJson(baseUrl + "/bt/strategy/validate", { code }, 6e3).then((j) => setValidate(j || { ok: false, error: "\uC751\uB2F5 \uC5C6\uC74C" })).catch((e) => setValidate({ ok: false, error: String(e) })).finally(() => setBusy(""));
    };
    const doSave = (asNew) => {
      if (isDemo) return;
      const targetName = (editName || "").trim();
      if (!targetName) {
        setMsg({ kind: "error", text: "\uC774\uB984\uC744 \uC785\uB825\uD558\uC138\uC694." });
        return;
      }
      const overwrite = !asNew && targetName === loadedName;
      setBusy("save");
      setMsg(null);
      _btPostJson(baseUrl + "/bt/strategy", { kind, name: targetName, code, overwrite }, 8e3).then((j) => {
        if (j && j.status === "ok") {
          setLoadedName(targetName);
          setMsg({ kind: "ok", text: `\uC800\uC7A5 \uC644\uB8CC: ${targetName}` });
          onSaved && onSaved(targetName);
        } else if (j && j.code === "exists") {
          setMsg({ kind: "error", text: `'${targetName}' \uC774\uBBF8 \uC874\uC7AC \u2014 '\uB36E\uC5B4\uC4F0\uAE30'\uB97C \uB204\uB974\uC138\uC694.` });
        } else {
          setMsg({ kind: "error", text: j && j.message || "\uC800\uC7A5 \uC2E4\uD328" });
        }
      }).catch((e) => setMsg({ kind: "error", text: "\uC800\uC7A5 \uC2E4\uD328: " + e })).finally(() => setBusy(""));
    };
    const doDelete = () => {
      if (isDemo || !loadedName) return;
      setBusy("delete");
      setMsg(null);
      _btPostJson(baseUrl + "/bt/strategy/delete", { kind, name: loadedName, confirm: confirmDel }, 8e3).then((j) => {
        if (j && j.status === "ok") {
          const deleted = loadedName;
          setCode("");
          setEditName("");
          setLoadedName("");
          setConfirmDel("");
          setMsg({ kind: "ok", text: `\uC0AD\uC81C \uC644\uB8CC: ${deleted}` });
          onDeleted && onDeleted(deleted);
        } else {
          setMsg({ kind: "error", text: j && j.message || "\uC0AD\uC81C \uC2E4\uD328" });
        }
      }).catch((e) => setMsg({ kind: "error", text: "\uC0AD\uC81C \uC2E4\uD328: " + e })).finally(() => setBusy(""));
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { display: "flex", flexDirection: "column", minWidth: 0, flex: 1 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: accent } }), label, " \uC5D0\uB514\uD130", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginLeft: 6 } }, lineCount, "\uC904"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: editName,
        onChange: (e) => setEditName(e.target.value),
        placeholder: label + " \uC870\uAC74\uC2DD \uC774\uB984",
        spellCheck: false,
        disabled: isDemo
      }
    ), /* @__PURE__ */ React.createElement(
      "textarea",
      {
        className: "input mono",
        value: code,
        onChange: (e) => {
          setCode(e.target.value);
          setValidate(null);
        },
        spellCheck: false,
        disabled: isDemo,
        style: { minHeight: 200, resize: "vertical", lineHeight: 1.5, whiteSpace: "pre", tabSize: 4, fontSize: 12 },
        placeholder: "# " + label + " \uC804\uB7B5 \uCF54\uB4DC (Python)"
      }
    ), /* @__PURE__ */ React.createElement(BtVarChips, { baseUrl, isDemo, code }), validate && /* @__PURE__ */ React.createElement("div", { style: {
      padding: "6px 9px",
      borderRadius: 5,
      fontSize: 11,
      fontFamily: "var(--mono)",
      border: "1px solid " + (validate.ok ? "rgba(76,214,179,0.3)" : "rgba(255,107,107,0.3)"),
      background: validate.ok ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)",
      color: validate.ok ? "var(--teal)" : "var(--red)"
    } }, validate.ok ? "\u2713 \uBB38\uBC95 \uAC80\uC99D \uD1B5\uACFC" : "\u2717 " + (validate.error || "\uAC80\uC99D \uC2E4\uD328")), msg && /* @__PURE__ */ React.createElement("div", { style: {
      padding: "6px 9px",
      borderRadius: 5,
      fontSize: 11,
      fontFamily: "var(--mono)",
      border: "1px solid " + (msg.kind === "ok" ? "rgba(76,214,179,0.3)" : "rgba(255,107,107,0.3)"),
      background: msg.kind === "ok" ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)",
      color: msg.kind === "ok" ? "var(--teal)" : "var(--red)"
    } }, msg.text), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: runValidate, disabled: isDemo || busy === "validate" }, busy === "validate" ? "\uAC80\uC99D\uC911\u2026" : "\uAC80\uC99D"), /* @__PURE__ */ React.createElement("button", { className: "btn primary sm", onClick: () => doSave(false), disabled: isDemo || busy === "save" }, busy === "save" ? "\uC800\uC7A5\uC911\u2026" : editName.trim() === loadedName && loadedName ? "\uB36E\uC5B4\uC4F0\uAE30" : "\uC800\uC7A5"), /* @__PURE__ */ React.createElement("button", { className: "btn sm", onClick: () => doSave(true), disabled: isDemo || busy === "save" }, "\uB2E4\uB978 \uC774\uB984\uC73C\uB85C")), loadedName && /* @__PURE__ */ React.createElement("div", { style: { borderTop: "1px solid var(--line-1)", paddingTop: 8, display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        style: { flex: 1, minWidth: 100, fontSize: 11 },
        value: confirmDel,
        onChange: (e) => setConfirmDel(e.target.value),
        placeholder: "\uC0AD\uC81C\uD558\uB824\uBA74 '" + loadedName + "' \uC7AC\uC785\uB825",
        spellCheck: false,
        disabled: isDemo
      }
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn danger sm",
        onClick: doDelete,
        disabled: isDemo || busy === "delete" || confirmDel !== loadedName
      },
      busy === "delete" ? "\uC0AD\uC81C\uC911\u2026" : "\uC0AD\uC81C"
    ))));
  }
  function BtDualEditor({ baseUrl, isDemo, buyName, sellName, onSaved, onDeletedBuy, onDeletedSell }) {
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 12, minWidth: 0, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      BtCodeEditor,
      {
        baseUrl,
        isDemo,
        kind: "buy",
        label: "\uB9E4\uC218",
        accent: "var(--teal)",
        name: buyName,
        onSaved,
        onDeleted: onDeletedBuy
      }
    ), /* @__PURE__ */ React.createElement(
      BtCodeEditor,
      {
        baseUrl,
        isDemo,
        kind: "sell",
        label: "\uB9E4\uB3C4",
        accent: "var(--red)",
        name: sellName,
        onSaved,
        onDeleted: onDeletedSell
      }
    ));
  }

  // ../frontend/bt-tab-run.jsx
  function _SweepParamBuilder({ rows, onChange, disabled }) {
    const safeRows = Array.isArray(rows) ? rows : [];
    const setRow = (i, patch) => {
      const next = safeRows.map((r, idx) => idx === i ? Object.assign({}, r, patch) : r);
      onChange(next);
    };
    const addRow = () => onChange(safeRows.concat([{ name: "", min: "", max: "", step: "" }]));
    const removeRow = (i) => onChange(safeRows.filter((_, idx) => idx !== i));
    let comboEst = 1;
    let validCount = 0;
    safeRows.forEach((r) => {
      if (!r || !String(r.name || "").trim()) return;
      const vc = _btSweepValueCount(r);
      if (vc > 0) {
        comboEst *= vc;
        validCount += 1;
      }
    });
    if (validCount === 0) comboEst = 0;
    return /* @__PURE__ */ React.createElement("div", { className: "field", style: { flex: 1, minWidth: 320 } }, /* @__PURE__ */ React.createElement("label", null, "\uC2A4\uC715 \uBCC0\uC218 \uBE4C\uB354 (\uBCC0\uC218\uBA85 \xB7 \uCD5C\uC18C \xB7 \uCD5C\uB300 \xB7 \uAC04\uACA9)"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 4 } }, safeRows.length === 0 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uBCC0\uC218 \uD589\uC744 \uCD94\uAC00\uD558\uC138\uC694(\uC608: avg_time 60~180 \uAC04\uACA9 60 \u2192 60\xB7120\xB7180)."), safeRows.map((r, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { display: "flex", gap: 4, alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input mono",
        value: r.name || "",
        disabled,
        onChange: (e) => setRow(i, { name: e.target.value }),
        placeholder: "\uBCC0\uC218\uBA85 (\uC608: avg_time)",
        spellCheck: false,
        style: { flex: 1, minWidth: 110, fontSize: 11 }
      }
    ), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        value: r.min == null ? "" : r.min,
        disabled,
        onChange: (e) => setRow(i, { min: e.target.value }),
        placeholder: "min",
        style: { width: 64, fontSize: 11 }
      }
    ), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        value: r.max == null ? "" : r.max,
        disabled,
        onChange: (e) => setRow(i, { max: e.target.value }),
        placeholder: "max",
        style: { width: 64, fontSize: 11 }
      }
    ), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        value: r.step == null ? "" : r.step,
        disabled,
        onChange: (e) => setRow(i, { step: e.target.value }),
        placeholder: "step",
        style: { width: 64, fontSize: 11 }
      }
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => removeRow(i),
        disabled,
        title: "\uC774 \uBCC0\uC218 \uD589 \uC0AD\uC81C",
        style: { padding: "2px 8px" }
      },
      "\u2715"
    ))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 10 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: addRow, disabled }, "+ \uBCC0\uC218 \uCD94\uAC00"), validCount > 0 && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC608\uC0C1 \uC870\uD569 ", comboEst, "\uAC1C (", validCount, "\uAC1C \uBCC0\uC218)"))));
  }
  function BtRunPanel({
    baseUrl,
    isDemo,
    libNames,
    onResult,
    compareA,
    onCompareB,
    onJobs,
    buy,
    sell,
    onBuy,
    onSell,
    reloadJobsKey
  }) {
    const [start, setStart] = useState_bt("");
    const [end, setEnd] = useState_bt("");
    const [timeframe, setTimeframe] = useState_bt("min");
    const [engines, setEngines] = useState_bt(4);
    const [mode, setMode] = useState_bt("backtest");
    const [paramSpace, setParamSpace] = useState_bt("");
    const [trainWindow, setTrainWindow] = useState_bt("");
    const [testWindow, setTestWindow] = useState_bt("");
    const [stepDays, setStepDays] = useState_bt("");
    const [sweepAction, setSweepAction] = useState_bt("param");
    const [sweepParams, setSweepParams] = useState_bt("");
    const [sweepRows, setSweepRows] = useState_bt([{ name: "", min: "", max: "", step: "" }]);
    const [sweepInputMode, setSweepInputMode] = useState_bt("builder");
    const [windowDays, setWindowDays] = useState_bt("");
    const [range, setRange] = useState_bt(null);
    const [jobs, setJobs] = useState_bt([]);
    const [activeJob, setActiveJob] = useState_bt(null);
    const [runErr, setRunErr] = useState_bt("");
    const [showLog, setShowLog] = useState_bt(false);
    const [selectedJobId, setSelectedJobId] = useState_bt("");
    useEffect_bt(() => {
      if (isDemo || !baseUrl) {
        setRange(null);
        return;
      }
      _btFetchJson2(baseUrl + "/bt/data_range", 5e3).then(setRange).catch(() => setRange(null));
    }, [baseUrl, isDemo]);
    const loadJobs = useCallback_bt(() => {
      if (isDemo || !baseUrl) {
        setJobs([]);
        return;
      }
      _btFetchJson2(baseUrl + "/bt/jobs", 4e3).then((j) => setJobs(Array.isArray(j && j.jobs) ? j.jobs : [])).catch(() => {
      });
    }, [baseUrl, isDemo]);
    useEffect_bt(() => {
      loadJobs();
    }, [loadJobs, reloadJobsKey]);
    useEffect_bt(() => {
      onJobs && onJobs(jobs);
    }, [jobs, onJobs]);
    const trackId = activeJob && (activeJob.status === "running" || activeJob.status === "pending") ? activeJob.job_id : null;
    const wsOkRef = useRef_bt(false);
    useEffect_bt(() => {
      wsOkRef.current = false;
      if (isDemo || !baseUrl || !trackId) return;
      let ws = null;
      let closedByUs = false;
      try {
        const wsUrl = _btWsUrl(baseUrl, "/bt/ws_job?job_id=" + encodeURIComponent(trackId));
        ws = new WebSocket(wsUrl);
      } catch (e) {
        return;
      }
      ws.onopen = () => {
        wsOkRef.current = true;
      };
      ws.onmessage = (ev) => {
        let m = null;
        try {
          m = JSON.parse(ev.data);
        } catch (e) {
          return;
        }
        if (!m || m.error) {
          return;
        }
        wsOkRef.current = true;
        setActiveJob((prev) => Object.assign({}, prev, {
          job_id: m.job_id,
          status: m.status,
          progress: m.progress,
          phase: m.phase,
          message: m.message,
          log_tail: m.log_tail || prev && prev.log_tail || []
        }));
        if (m.terminal) {
          loadJobs();
        }
      };
      ws.onerror = () => {
        wsOkRef.current = false;
      };
      ws.onclose = () => {
        if (!closedByUs) {
        }
      };
      return () => {
        closedByUs = true;
        try {
          ws && ws.close();
        } catch (e) {
        }
      };
    }, [baseUrl, isDemo, trackId, loadJobs]);
    useEffect_bt(() => {
      if (isDemo || !baseUrl || !trackId) return;
      const id = setInterval(() => {
        if (wsOkRef.current) return;
        _btFetchJson2(baseUrl + "/bt/job?job_id=" + encodeURIComponent(trackId), 4e3).then((j) => {
          if (j && j.available) {
            setActiveJob(j);
            if (j.status !== "running" && j.status !== "pending") {
              loadJobs();
            }
          }
        }).catch(() => {
        });
      }, 2e3);
      return () => clearInterval(id);
    }, [baseUrl, isDemo, trackId, loadJobs]);
    const autoPickedRef = useRef_bt("");
    useEffect_bt(() => {
      if (!activeJob || isDemo) return;
      if (activeJob.status === "success" && activeJob.job_id && autoPickedRef.current !== activeJob.job_id) {
        autoPickedRef.current = activeJob.job_id;
        onResult && onResult(activeJob.job_id);
      }
    }, [activeJob, isDemo, onResult]);
    const tfRange = range ? range[timeframe] : null;
    const submit = () => {
      if (isDemo) return;
      setRunErr("");
      const payload = {
        buy: (buy || "").trim(),
        sell: (sell || "").trim(),
        start: parseInt(start, 10) || 0,
        end: parseInt(end, 10) || 0,
        timeframe,
        engines: parseInt(engines, 10) || 4,
        mode
      };
      if (!payload.buy || !payload.sell) {
        setRunErr("\uB9E4\uC218/\uB9E4\uB3C4 \uC870\uAC74\uC2DD\uC744 \uC120\uD0DD\uD558\uC138\uC694.");
        return;
      }
      if (!/^\d{8}$/.test(String(start)) || !/^\d{8}$/.test(String(end))) {
        setRunErr("\uAE30\uAC04\uC740 YYYYMMDD 8\uC790\uB9AC\uB85C \uC785\uB825\uD558\uC138\uC694.");
        return;
      }
      if (mode === "optimize") {
        const ps = (paramSpace || "").trim();
        if (!ps) {
          setRunErr("\uCD5C\uC801\uD654 \uBAA8\uB4DC\uB294 \uD30C\uB77C\uBBF8\uD130 \uD0D0\uC0C9\uACF5\uAC04 JSON \uACBD\uB85C\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4.");
          return;
        }
        payload.param_space = ps;
      } else if (mode === "wfo") {
        const tr = parseInt(trainWindow, 10) || 0;
        const te = parseInt(testWindow, 10) || 0;
        if (tr < 1 || te < 1) {
          setRunErr("\uC804\uC9C4\uBD84\uC11D\uC740 \uD6C8\uB828\xB7\uD14C\uC2A4\uD2B8 \uC708\uB3C4\uC6B0(\uC77C, 1 \uC774\uC0C1)\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4.");
          return;
        }
        payload.train_window_days = tr;
        payload.test_window_days = te;
        if (stepDays) payload.step_days = parseInt(stepDays, 10) || 0;
        if ((paramSpace || "").trim()) payload.param_space = (paramSpace || "").trim();
        payload.opt_objective = "tpi";
        payload.opt_method = "grid";
      } else if (mode === "sweep") {
        payload.sweep_action = sweepAction;
        if (sweepAction === "rolling") {
          const wd = parseInt(windowDays, 10) || 0;
          const sd = parseInt(stepDays, 10) || 0;
          if (wd < 1 || sd < 1) {
            setRunErr("\uB864\uB9C1 \uC2A4\uC715\uC740 \uC708\uB3C4\uC6B0\xB7\uC774\uB3D9(\uC77C, 1 \uC774\uC0C1)\uC774 \uD544\uC694\uD569\uB2C8\uB2E4.");
            return;
          }
          payload.window_days = wd;
          payload.step_days = sd;
        } else if (sweepInputMode === "file") {
          const sp = (sweepParams || "").trim();
          if (!sp) {
            setRunErr("\uD30C\uB77C\uBBF8\uD130 \uC2A4\uC715\uC740 \uC870\uD569 JSON \uACBD\uB85C\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4.");
            return;
          }
          payload.sweep_params = sp;
        } else {
          const validRows = (sweepRows || []).filter((r) => r && String(r.name || "").trim()).map((r) => ({
            name: String(r.name).trim(),
            min: Number(r.min),
            max: Number(r.max),
            step: Number(r.step)
          }));
          if (_btSweepRowCount(sweepRows) < 1) {
            setRunErr("\uD30C\uB77C\uBBF8\uD130 \uC2A4\uC715\uC740 \uBCC0\uC218 \uD589\uC774 1\uAC1C \uC774\uC0C1 \uD544\uC694\uD569\uB2C8\uB2E4(\uBCC0\uC218\uBA85 \uC785\uB825).");
            return;
          }
          const bad = validRows.find((r) => !isFinite(r.min) || !isFinite(r.max) || !isFinite(r.step));
          if (bad) {
            setRunErr(`\uBCC0\uC218 '${bad.name}' \uC758 min/max/step \uC744 \uC22B\uC790\uB85C \uC785\uB825\uD558\uC138\uC694.`);
            return;
          }
          payload.sweep_spec = validRows;
        }
      }
      _btPostJson(baseUrl + "/bt/run", payload, 8e3).then((j) => {
        if (j && j.status === "ok" && j.job_id) {
          setActiveJob({ job_id: j.job_id, status: "pending", progress: 0, spec: payload, log_tail: [] });
          setSelectedJobId(j.job_id);
          loadJobs();
        } else {
          setRunErr(j && j.message || "\uC2E4\uD589 \uC2E4\uD328");
        }
      }).catch((e) => setRunErr("\uC2E4\uD589 \uC2E4\uD328: " + e));
    };
    const cancelJob = (jobId) => {
      if (isDemo || !jobId) return;
      _btPostJson(baseUrl + "/bt/job/cancel", { job_id: jobId }, 5e3).then(() => {
        _btFetchJson2(baseUrl + "/bt/job?job_id=" + encodeURIComponent(jobId), 4e3).then((j) => {
          if (j && j.available) setActiveJob(j);
          loadJobs();
        }).catch(() => {
        });
      }).catch(() => {
      });
    };
    const pickJob = (jobId) => {
      setSelectedJobId(jobId);
      onResult && onResult(jobId);
    };
    const openReport = (jobId) => {
      if (isDemo || !baseUrl || !jobId) return;
      const url = baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId);
      try {
        window.open(url, "_blank", "noopener");
      } catch (e) {
      }
    };
    const pct = activeJob ? Math.round((activeJob.progress || 0) * 100) : 0;
    const tracking = activeJob && (activeJob.status === "running" || activeJob.status === "pending");
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { background: "var(--bg-1)" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 240 } }, /* @__PURE__ */ React.createElement("label", null, "\uBAA8\uB4DC"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["backtest", "\uBC31\uD14C\uC2A4\uD2B8"], ["optimize", "\uCD5C\uC801\uD654"], ["wfo", "WFO"], ["sweep", "\uC2A4\uC715"]].map(([m, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: m,
        onClick: () => setMode(m),
        className: "mono",
        disabled: isDemo,
        title: _BT_MODE_TIP[m],
        "data-tip": _BT_MODE_TIP[m],
        style: {
          flex: 1,
          padding: "6px 8px",
          fontSize: 11,
          borderRadius: 5,
          border: "1px solid " + (mode === m ? "var(--amber)" : "var(--line-1)"),
          background: mode === m ? "rgba(240,179,90,0.1)" : "transparent",
          color: mode === m ? "var(--amber)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      lbl
    )))), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 160 } }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uC218 \uC870\uAC74\uC2DD"), /* @__PURE__ */ React.createElement("select", { className: "select", value: buy, onChange: (e) => onBuy(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 \uC120\uD0DD \u2014"), libNames.buy.map((n) => /* @__PURE__ */ React.createElement("option", { key: n, value: n }, n)))), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 160 } }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uB3C4 \uC870\uAC74\uC2DD"), /* @__PURE__ */ React.createElement("select", { className: "select", value: sell, onChange: (e) => onSell(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 \uC120\uD0DD \u2014"), libNames.sell.map((n) => /* @__PURE__ */ React.createElement("option", { key: n, value: n }, n)))), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 110 } }, /* @__PURE__ */ React.createElement("label", null, "\uC2DC\uC791 (YYYYMMDD)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: start,
        onChange: (e) => setStart(e.target.value),
        placeholder: _BT_START_EG,
        spellCheck: false,
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 110 } }, /* @__PURE__ */ React.createElement("label", null, "\uC885\uB8CC (YYYYMMDD)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        value: end,
        onChange: (e) => setEnd(e.target.value),
        placeholder: _BT_END_EG,
        spellCheck: false,
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 100 } }, /* @__PURE__ */ React.createElement("label", null, "\uC2DC\uAC04\uB2E8\uC704"), /* @__PURE__ */ React.createElement("select", { className: "select", value: timeframe, onChange: (e) => setTimeframe(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "min" }, "\uBD84\uBD09 (min)"), /* @__PURE__ */ React.createElement("option", { value: "tick" }, "\uD2F1 (tick)"))), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 76 } }, /* @__PURE__ */ React.createElement("label", null, "\uC5D4\uC9C4 \uC218"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        max: "16",
        value: engines,
        onChange: (e) => setEngines(e.target.value),
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn primary",
        onClick: submit,
        disabled: isDemo || tracking,
        style: { fontSize: 14, padding: "10px 22px", minWidth: 120 }
      },
      "\u25B8 ",
      _BT_MODE_RUN_LABEL[mode] || "\uBC31\uD14C\uC2A4\uD2B8 \uC2E4\uD589"
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: loadJobs, disabled: isDemo }, "\u21BB \uC774\uB825")), mode === "optimize" && /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uD30C\uB77C\uBBF8\uD130 \uD0D0\uC0C9\uACF5\uAC04 JSON \uACBD\uB85C (_database/ \uB610\uB294 ai_strategy_loop/state/ \uD558\uC704)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input mono",
        value: paramSpace,
        onChange: (e) => setParamSpace(e.target.value),
        placeholder: "_database/param_space.json",
        spellCheck: false,
        disabled: isDemo,
        style: { fontSize: 11 }
      }
    )), mode === "wfo" && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 120 } }, /* @__PURE__ */ React.createElement("label", null, "\uD6C8\uB828 \uC708\uB3C4\uC6B0 (\uC77C)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        value: trainWindow,
        onChange: (e) => setTrainWindow(e.target.value),
        placeholder: "60",
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 120 } }, /* @__PURE__ */ React.createElement("label", null, "\uD14C\uC2A4\uD2B8 \uC708\uB3C4\uC6B0 (\uC77C)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        value: testWindow,
        onChange: (e) => setTestWindow(e.target.value),
        placeholder: "20",
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 120 } }, /* @__PURE__ */ React.createElement("label", null, "\uC774\uB3D9 \uAC04\uACA9 (\uC77C, \uC120\uD0DD)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        value: stepDays,
        onChange: (e) => setStepDays(e.target.value),
        placeholder: "\uD14C\uC2A4\uD2B8 \uC708\uB3C4\uC6B0",
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { flex: 1, minWidth: 200 } }, /* @__PURE__ */ React.createElement("label", null, "\uD0D0\uC0C9\uACF5\uAC04 JSON \uACBD\uB85C (\uC120\uD0DD \u2014 \uBBF8\uC9C0\uC815 \uC2DC \uACE0\uC815 \uD30C\uB77C\uBBF8\uD130)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input mono",
        value: paramSpace,
        onChange: (e) => setParamSpace(e.target.value),
        placeholder: "_database/param_space.json",
        spellCheck: false,
        disabled: isDemo,
        style: { fontSize: 11 }
      }
    ))), mode === "sweep" && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" } }, /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 160 } }, /* @__PURE__ */ React.createElement("label", null, "\uC2A4\uC715 \uC885\uB958"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["param", "\uD30C\uB77C\uBBF8\uD130"], ["rolling", "\uB0A0\uC9DC \uB864\uB9C1"]].map(([a, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: a,
        onClick: () => setSweepAction(a),
        className: "mono",
        disabled: isDemo,
        style: {
          flex: 1,
          padding: "6px 8px",
          fontSize: 11,
          borderRadius: 5,
          border: "1px solid " + (sweepAction === a ? "var(--amber)" : "var(--line-1)"),
          background: sweepAction === a ? "rgba(240,179,90,0.1)" : "transparent",
          color: sweepAction === a ? "var(--amber)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      lbl
    )))), sweepAction === "param" ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 150 } }, /* @__PURE__ */ React.createElement("label", null, "\uC785\uB825 \uBC29\uC2DD"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["builder", "\uBE4C\uB354"], ["file", "\uD30C\uC77C \uACBD\uB85C"]].map(([m, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: m,
        onClick: () => setSweepInputMode(m),
        className: "mono",
        disabled: isDemo,
        style: {
          flex: 1,
          padding: "6px 8px",
          fontSize: 11,
          borderRadius: 5,
          border: "1px solid " + (sweepInputMode === m ? "var(--amber)" : "var(--line-1)"),
          background: sweepInputMode === m ? "rgba(240,179,90,0.1)" : "transparent",
          color: sweepInputMode === m ? "var(--amber)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      lbl
    )))), sweepInputMode === "builder" ? /* @__PURE__ */ React.createElement(_SweepParamBuilder, { rows: sweepRows, onChange: setSweepRows, disabled: isDemo }) : /* @__PURE__ */ React.createElement("div", { className: "field", style: { flex: 1, minWidth: 220 } }, /* @__PURE__ */ React.createElement("label", null, "\uC2A4\uC715 \uC870\uD569 JSON \uACBD\uB85C (_database/ \uB610\uB294 ai_strategy_loop/state/ \uD558\uC704)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input mono",
        value: sweepParams,
        onChange: (e) => setSweepParams(e.target.value),
        placeholder: "_database/sweep_params.json",
        spellCheck: false,
        disabled: isDemo,
        style: { fontSize: 11 }
      }
    ))) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 120 } }, /* @__PURE__ */ React.createElement("label", null, "\uC708\uB3C4\uC6B0 (\uC77C)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        value: windowDays,
        onChange: (e) => setWindowDays(e.target.value),
        placeholder: "20",
        disabled: isDemo
      }
    )), /* @__PURE__ */ React.createElement("div", { className: "field", style: { minWidth: 120 } }, /* @__PURE__ */ React.createElement("label", null, "\uC774\uB3D9 \uAC04\uACA9 (\uC77C)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        value: stepDays,
        onChange: (e) => setStepDays(e.target.value),
        placeholder: "5",
        disabled: isDemo
      }
    )))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" } }, tfRange && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uAC00\uC6A9 ", timeframe, ": \uC77C\uC77CDB ", tfRange.count, "\uC77C", tfRange.back_range ? ` \xB7 back ${tfRange.back_range.start}~${tfRange.back_range.end}` : ""), runErr && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, runErr), compareA && /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono tag-slim",
        style: { fontSize: 9.5, color: "var(--amber)", marginLeft: "auto" },
        title: "\uBE44\uAD50 \uAE30\uC900(A) \uACE0\uC815\uB428 \u2014 \uACB0\uACFC \uB77C\uC774\uBE0C\uB7EC\uB9AC\uC5D0\uC11C \uB2E4\uB978 \uC7A1\uC758 '\uBE44\uAD50(B)' \uB97C \uB204\uB974\uC138\uC694"
      },
      "\uBE44\uAD50 A=",
      compareA
    )), activeJob && /* @__PURE__ */ React.createElement("div", { style: { border: "1px solid var(--line-1)", borderRadius: 6, padding: 10, background: "var(--bg-0)", display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: (_BT_JOB_BADGE[activeJob.status] || _BT_JOB_BADGE.pending).cls }, /* @__PURE__ */ React.createElement("span", { className: "dot " + (activeJob.status === "running" ? "pulse-dot" : "") }), (_BT_JOB_BADGE[activeJob.status] || _BT_JOB_BADGE.pending).txt), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, activeJob.job_id), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-2)", marginLeft: "auto" } }, _btElapsed(activeJob))), /* @__PURE__ */ React.createElement("div", { className: "progress-track" }, /* @__PURE__ */ React.createElement("div", { className: "progress-fill " + (activeJob.status === "running" ? "running" : ""), style: { width: pct + "%" } })), activeJob.message && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 } }, activeJob.message), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "center" } }, tracking && /* @__PURE__ */ React.createElement("button", { className: "btn danger sm", onClick: () => cancelJob(activeJob.job_id) }, "\u25FC \uC911\uC9C0"), (activeJob.status === "success" || activeJob.status === "no_trades") && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => pickJob(activeJob.job_id) }, "\uACB0\uACFC \uBCF4\uAE30"), (activeJob.status === "success" || activeJob.status === "no_trades") && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => openReport(activeJob.job_id),
        title: "\uC790\uAE09\uC790\uC871 HTML \uB9AC\uD3EC\uD2B8\uB97C \uC0C8 \uD0ED\uC73C\uB85C \uC5F4\uAE30"
      },
      "\u{1F4C4} \uB9AC\uD3EC\uD2B8"
    ), activeJob.log_tail && activeJob.log_tail.length > 0 && /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setShowLog((s) => !s) }, showLog ? "\uB85C\uADF8 \uC811\uAE30" : "\uB85C\uADF8 \uBCF4\uAE30")), showLog && activeJob.log_tail && activeJob.log_tail.length > 0 && /* @__PURE__ */ React.createElement("pre", { className: "process-log-pane", style: { margin: 0 } }, activeJob.log_tail.join("\n")))));
  }
  function BtResultLibrary({
    baseUrl,
    isDemo,
    jobs,
    onResult,
    selectedJobId,
    onReload,
    compareA,
    onSetCompareA,
    onCompareB
  }) {
    const [query, setQuery] = useState_bt("");
    const [favOnly, setFavOnly] = useState_bt(false);
    const [tagFilter, setTagFilter] = useState_bt("");
    const [editing, setEditing] = useState_bt("");
    const [tagDraft, setTagDraft] = useState_bt("");
    const [memoDraft, setMemoDraft] = useState_bt("");
    const openReport = (jobId) => {
      if (isDemo || !baseUrl || !jobId) return;
      try {
        window.open(baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId), "_blank", "noopener");
      } catch (e) {
      }
    };
    const saveMeta = (jobId, patch) => {
      if (isDemo || !baseUrl || !jobId) return;
      _btPostJson(baseUrl + "/bt/job/meta", Object.assign({ job_id: jobId }, patch), 6e3).then(() => {
        onReload && onReload();
      }).catch(() => {
      });
    };
    const toggleFav = (j) => saveMeta(j.job_id, { favorite: !j.favorite });
    const beginEdit = (j) => {
      setEditing(j.job_id);
      setTagDraft((j.tags || []).join(", "));
      setMemoDraft(j.memo || "");
    };
    const commitEdit = (jobId) => {
      const tags = tagDraft.split(",").map((s) => s.trim()).filter(Boolean);
      saveMeta(jobId, { tags, memo: memoDraft });
      setEditing("");
    };
    const allTags = useMemo_bt(() => {
      const s = /* @__PURE__ */ new Set();
      (jobs || []).forEach((j) => (j.tags || []).forEach((t) => s.add(t)));
      return Array.from(s).sort();
    }, [jobs]);
    const filtered = useMemo_bt(() => {
      const q = query.trim().toLowerCase();
      let out = jobs || [];
      if (favOnly) out = out.filter((j) => j.favorite);
      if (tagFilter) out = out.filter((j) => (j.tags || []).includes(tagFilter));
      if (q) out = out.filter((j) => {
        const hay = (j.job_id + " " + (j.memo || "") + " " + (j.tags || []).join(" ") + " " + (j.spec && j.spec.buy + " " + j.spec.sell || "")).toLowerCase();
        return hay.includes(q);
      });
      return out.slice().sort((a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0));
    }, [jobs, query, favOnly, tagFilter]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uACB0\uACFC \uB77C\uC774\uBE0C\uB7EC\uB9AC", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginLeft: 6 } }, filtered.length, "/", (jobs || []).length)), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onReload, disabled: isDemo }, "\u21BB")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uACB0\uACFC \uC774\uB825\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        placeholder: "\uC7A1/\uBA54\uBAA8/\uD0DC\uADF8/\uC804\uB7B5 \uAC80\uC0C9\u2026",
        value: query,
        onChange: (e) => setQuery(e.target.value),
        spellCheck: false,
        style: { flex: 1, minWidth: 140 }
      }
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "mono",
        onClick: () => setFavOnly((f) => !f),
        style: {
          padding: "5px 9px",
          fontSize: 11,
          borderRadius: 5,
          cursor: "pointer",
          border: "1px solid " + (favOnly ? "var(--amber)" : "var(--line-1)"),
          background: favOnly ? "rgba(240,179,90,0.1)" : "transparent",
          color: favOnly ? "var(--amber)" : "var(--ink-2)"
        }
      },
      "\u2605 \uC990\uACA8\uCC3E\uAE30"
    ), allTags.length > 0 && /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "select",
        value: tagFilter,
        onChange: (e) => setTagFilter(e.target.value),
        style: { maxWidth: 140 }
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "\uC804\uCCB4 \uD0DC\uADF8"),
      allTags.map((t) => /* @__PURE__ */ React.createElement("option", { key: t, value: t }, t))
    )), filtered.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, (jobs || []).length === 0 ? "\uC2E4\uD589 \uC774\uB825\uC774 \uC5C6\uC2B5\uB2C8\uB2E4" : "\uC870\uAC74\uC5D0 \uB9DE\uB294 \uACB0\uACFC \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 4, maxHeight: 360, overflowY: "auto" } }, filtered.map((j) => {
      const b = _BT_JOB_BADGE[j.status] || _BT_JOB_BADGE.pending;
      const clickable = j.status === "success" || j.status === "no_trades";
      const active = j.job_id === selectedJobId;
      const canCompare = clickable && compareA && onCompareB && j.job_id !== compareA;
      const isEditing = editing === j.job_id;
      return /* @__PURE__ */ React.createElement(
        "div",
        {
          key: j.job_id,
          style: {
            display: "flex",
            flexDirection: "column",
            gap: 5,
            padding: "7px 9px",
            borderRadius: 5,
            border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
            background: active ? "rgba(76,214,179,0.06)" : "var(--bg-0)",
            opacity: clickable ? 1 : 0.7
          }
        },
        /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: () => toggleFav(j),
            title: "\uC990\uACA8\uCC3E\uAE30 \uD1A0\uAE00",
            style: {
              background: "transparent",
              border: 0,
              cursor: "pointer",
              fontSize: 13,
              padding: 0,
              color: j.favorite ? "var(--amber)" : "var(--ink-3)"
            }
          },
          j.favorite ? "\u2605" : "\u2606"
        ), /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: () => clickable && onResult(j.job_id),
            disabled: !clickable,
            style: {
              display: "flex",
              alignItems: "center",
              gap: 8,
              flex: 1,
              minWidth: 0,
              background: "transparent",
              border: 0,
              padding: 0,
              textAlign: "left",
              cursor: clickable ? "pointer" : "default"
            }
          },
          /* @__PURE__ */ React.createElement("span", { className: b.cls, style: { flexShrink: 0 } }, b.txt),
          /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 } }, j.job_id),
          /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", flexShrink: 0 } }, _btElapsed(j))
        ), clickable && /* @__PURE__ */ React.createElement(
          "button",
          {
            className: "btn ghost sm",
            style: { flexShrink: 0, fontSize: 10, padding: "2px 6px" },
            onClick: () => openReport(j.job_id),
            title: "HTML \uB9AC\uD3EC\uD2B8 \uC0C8 \uD0ED"
          },
          "\u{1F4C4}"
        ), clickable && onSetCompareA && /* @__PURE__ */ React.createElement(
          "button",
          {
            className: "btn ghost sm",
            style: { flexShrink: 0, fontSize: 10, padding: "2px 6px" },
            onClick: () => onSetCompareA(j.job_id),
            title: "\uBE44\uAD50 \uAE30\uC900(A) \uC73C\uB85C \uACE0\uC815"
          },
          "A"
        ), canCompare && /* @__PURE__ */ React.createElement(
          "button",
          {
            className: "btn ghost sm",
            style: { flexShrink: 0, fontSize: 10, padding: "2px 6px" },
            onClick: () => onCompareB(j.job_id),
            title: "A(" + compareA + ") \uC640 \uBE44\uAD50"
          },
          "B"
        ), /* @__PURE__ */ React.createElement(
          "button",
          {
            className: "btn ghost sm",
            style: { flexShrink: 0, fontSize: 10, padding: "2px 6px" },
            onClick: () => isEditing ? setEditing("") : beginEdit(j),
            title: "\uD0DC\uADF8\xB7\uBA54\uBAA8 \uD3B8\uC9D1"
          },
          "\u{1F3F7}"
        )),
        !isEditing && (j.tags && j.tags.length > 0 || j.memo) && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" } }, (j.tags || []).map((t) => /* @__PURE__ */ React.createElement("span", { key: t, className: "tag-slim", style: { fontSize: 9.5, color: "var(--teal)" } }, t)), j.memo && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, "\xB7 ", j.memo)),
        isEditing && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 5 } }, /* @__PURE__ */ React.createElement(
          "input",
          {
            className: "input",
            value: tagDraft,
            onChange: (e) => setTagDraft(e.target.value),
            placeholder: "\uD0DC\uADF8(\uC27C\uD45C \uAD6C\uBD84)",
            spellCheck: false,
            style: { fontSize: 11 }
          }
        ), /* @__PURE__ */ React.createElement(
          "input",
          {
            className: "input",
            value: memoDraft,
            onChange: (e) => setMemoDraft(e.target.value),
            placeholder: "\uBA54\uBAA8",
            spellCheck: false,
            style: { fontSize: 11 }
          }
        ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6 } }, /* @__PURE__ */ React.createElement("button", { className: "btn primary sm", onClick: () => commitEdit(j.job_id) }, "\uC800\uC7A5"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: () => setEditing("") }, "\uCDE8\uC18C")))
      );
    })))));
  }

  // ../frontend/bt-tab-mode-results.jsx
  function BtWfoTable({ result }) {
    const [sortKey, setSortKey] = useState_bt("round");
    const [sortAsc, setSortAsc] = useState_bt(true);
    const [expanded, setExpanded] = useState_bt(null);
    const rounds = result && result.rounds || [];
    const summary = result && result.summary || {};
    const rows = useMemo_bt(() => rounds.map((r, i) => {
      const w = r.window || {};
      const tr = r.test_result && r.test_result.metrics || {};
      return {
        round: w.round != null ? w.round : i + 1,
        train: (w.train_start != null ? w.train_start : "\u2014") + "~" + (w.train_end != null ? w.train_end : "\u2014"),
        test: (w.test_start != null ? w.test_start : "\u2014") + "~" + (w.test_end != null ? w.test_end : "\u2014"),
        status: r.test_result && r.test_result.status || "\u2014",
        trade_count: tr.trade_count,
        total_profit_pct: tr.total_profit_pct,
        max_drawdown_pct: tr.max_drawdown_pct,
        best_params: r.best_params || {},
        // 드릴다운: 이 라운드가 훈련에서 고른 파라미터.
        _metrics: tr
        // 드릴다운: 표에 없는 전체 테스트 메트릭.
      };
    }), [rounds]);
    const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
      const va = a[sortKey], vb = b[sortKey];
      const na = Number(va), nb = Number(vb);
      const cmp = !isNaN(na) && !isNaN(nb) ? na - nb : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    }), [rows, sortKey, sortAsc]);
    const setSort = (k) => {
      if (k === sortKey) setSortAsc((a) => !a);
      else {
        setSortKey(k);
        setSortAsc(true);
      }
    };
    const cols = [
      ["round", "\uB77C\uC6B4\uB4DC"],
      ["train", "\uD6C8\uB828\uAE30\uAC04"],
      ["test", "\uD14C\uC2A4\uD2B8\uAE30\uAC04"],
      ["status", "\uC0C1\uD0DC"],
      ["trade_count", "\uAC70\uB798\uC218"],
      ["total_profit_pct", "\uC218\uC775%"],
      ["max_drawdown_pct", "MDD%"]
    ];
    if (rounds.length === 0) return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "WFO \uB77C\uC6B4\uB4DC \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.");
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", display: "flex", gap: 14, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", null, "\uB77C\uC6B4\uB4DC ", summary.round_count != null ? summary.round_count : rounds.length), /* @__PURE__ */ React.createElement("span", null, "\uC131\uACF5\uB960 ", summary.success_rate != null ? (summary.success_rate * 100).toFixed(0) + "%" : "\u2014"), /* @__PURE__ */ React.createElement("span", null, "\uD3C9\uADE0 OOS ", summary.metric || "tpi", " ", _btNum(summary.mean_oos_metric)), /* @__PURE__ */ React.createElement("span", null, "\uBB34\uAC70\uB798 \uB77C\uC6B4\uB4DC ", summary.zero_trade_rounds != null ? summary.zero_trade_rounds : "\u2014")), /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "mono", style: { borderCollapse: "collapse", fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, cols.map(([k, lbl]) => /* @__PURE__ */ React.createElement(
      "th",
      {
        key: k,
        onClick: () => setSort(k),
        title: "\uC815\uB82C",
        style: {
          padding: "5px 8px",
          textAlign: "left",
          cursor: "pointer",
          color: "var(--ink-3)",
          borderBottom: "1px solid var(--line-1)",
          whiteSpace: "nowrap"
        }
      },
      lbl,
      sortKey === k ? sortAsc ? " \u25B2" : " \u25BC" : ""
    )))), /* @__PURE__ */ React.createElement("tbody", null, sorted.map((r, i) => {
      const isOpen = expanded === r.round;
      return /* @__PURE__ */ React.createElement(React.Fragment, { key: i }, /* @__PURE__ */ React.createElement(
        "tr",
        {
          onClick: () => setExpanded(isOpen ? null : r.round),
          style: { cursor: "pointer", background: isOpen ? "var(--bg-2)" : void 0 },
          title: "\uD074\uB9AD \u2014 \uC774 \uB77C\uC6B4\uB4DC\uC758 \uC120\uD0DD \uD30C\uB77C\uBBF8\uD130\xB7\uC804\uCCB4 \uBA54\uD2B8\uB9AD \uD3BC\uCE58\uAE30/\uC811\uAE30"
        },
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", color: "var(--ink-0)" } }, isOpen ? "\u25BE " : "\u25B8 ", r.round),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", color: "var(--ink-3)" } }, r.train),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", color: "var(--ink-3)" } }, r.test),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px" } }, /* @__PURE__ */ React.createElement("span", { className: (_BT_JOB_BADGE[r.status] || _BT_JOB_BADGE.pending).cls }, r.status)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", textAlign: "right" } }, r.trade_count == null ? "\u2014" : r.trade_count),
        /* @__PURE__ */ React.createElement("td", { style: {
          padding: "4px 8px",
          textAlign: "right",
          color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)"
        } }, _btNum(r.total_profit_pct)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", textAlign: "right", color: "var(--red)" } }, _btNum(r.max_drawdown_pct))
      ), isOpen && /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", { colSpan: cols.length, style: { padding: "6px 12px 10px", background: "var(--bg-2)" } }, /* @__PURE__ */ React.createElement(_BtRowDetail, { label: "\uC120\uD0DD \uD30C\uB77C\uBBF8\uD130", data: r.best_params }), /* @__PURE__ */ React.createElement(_BtRowDetail, { label: "\uC804\uCCB4 \uBA54\uD2B8\uB9AD", data: r._metrics, numeric: true }))));
    })))));
  }
  function BtSweepTable({ result }) {
    const [sortKey, setSortKey] = useState_bt("__idx");
    const [sortAsc, setSortAsc] = useState_bt(true);
    const [expanded, setExpanded] = useState_bt(null);
    const raw = result && result.results || [];
    const rows = useMemo_bt(() => raw.map((item, i) => {
      const m = item && item.result && item.result.metrics || item.metrics || {};
      const combo = {};
      Object.keys(item || {}).forEach((k) => {
        if (k !== "result" && k !== "metrics" && k !== "window" && k !== "status") combo[k] = item[k];
      });
      return {
        __idx: i + 1,
        __combo: combo,
        window: item.window ? Array.isArray(item.window) ? item.window.join("~") : String(item.window) : null,
        trade_count: m.trade_count,
        total_profit_pct: m.total_profit_pct,
        max_drawdown_pct: m.max_drawdown_pct,
        _metrics: m
        // 드릴다운: 표 3컬럼 밖의 전체 메트릭(win_rate·sharpe·cagr…).
      };
    }), [raw]);
    const comboKeys = useMemo_bt(() => {
      const s = /* @__PURE__ */ new Set();
      rows.forEach((r) => Object.keys(r.__combo).forEach((k) => s.add(k)));
      return Array.from(s);
    }, [rows]);
    const hasWindow = useMemo_bt(() => rows.some((r) => r.window != null), [rows]);
    const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
      const get = (r) => r.__combo[sortKey] != null ? r.__combo[sortKey] : r[sortKey];
      const va = get(a), vb = get(b);
      const na = Number(va), nb = Number(vb);
      const cmp = !isNaN(na) && !isNaN(nb) ? na - nb : String(va).localeCompare(String(vb));
      return sortAsc ? cmp : -cmp;
    }), [rows, sortKey, sortAsc]);
    const setSort = (k) => {
      if (k === sortKey) setSortAsc((a) => !a);
      else {
        setSortKey(k);
        setSortAsc(true);
      }
    };
    if (raw.length === 0) return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC2A4\uC715 \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.");
    const metricCols = [["trade_count", "\uAC70\uB798\uC218"], ["total_profit_pct", "\uC218\uC775%"], ["max_drawdown_pct", "MDD%"]];
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)" } }, "\uCD1D ", result.total_combinations != null ? result.total_combinations : raw.length, "\uAC1C \uC870\uD569"), /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "mono", style: { borderCollapse: "collapse", fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { onClick: () => setSort("__idx"), style: { padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" } }, "#", sortKey === "__idx" ? sortAsc ? " \u25B2" : " \u25BC" : ""), hasWindow && /* @__PURE__ */ React.createElement("th", { onClick: () => setSort("window"), style: { padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" } }, "\uC708\uB3C4\uC6B0", sortKey === "window" ? sortAsc ? " \u25B2" : " \u25BC" : ""), comboKeys.map((k) => /* @__PURE__ */ React.createElement("th", { key: k, onClick: () => setSort(k), style: { padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" } }, k, sortKey === k ? sortAsc ? " \u25B2" : " \u25BC" : "")), metricCols.map(([k, lbl]) => /* @__PURE__ */ React.createElement("th", { key: k, onClick: () => setSort(k), style: { padding: "5px 8px", textAlign: "right", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" } }, lbl, sortKey === k ? sortAsc ? " \u25B2" : " \u25BC" : "")))), /* @__PURE__ */ React.createElement("tbody", null, sorted.map((r, i) => {
      const isOpen = expanded === r.__idx;
      const span = 1 + (hasWindow ? 1 : 0) + comboKeys.length + 3;
      return /* @__PURE__ */ React.createElement(React.Fragment, { key: i }, /* @__PURE__ */ React.createElement(
        "tr",
        {
          onClick: () => setExpanded(isOpen ? null : r.__idx),
          style: { cursor: "pointer", background: isOpen ? "var(--bg-2)" : void 0 },
          title: "\uD074\uB9AD \u2014 \uC774 \uC870\uD569\uC758 \uC804\uCCB4 \uBA54\uD2B8\uB9AD \uD3BC\uCE58\uAE30/\uC811\uAE30"
        },
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", color: "var(--ink-3)" } }, isOpen ? "\u25BE " : "\u25B8 ", r.__idx),
        hasWindow && /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", color: "var(--ink-3)" } }, r.window || "\u2014"),
        comboKeys.map((k) => /* @__PURE__ */ React.createElement("td", { key: k, style: { padding: "4px 8px", color: "var(--ink-0)" } }, r.__combo[k] != null ? String(r.__combo[k]) : "\u2014")),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", textAlign: "right" } }, r.trade_count == null ? "\u2014" : r.trade_count),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", textAlign: "right", color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" } }, _btNum(r.total_profit_pct)),
        /* @__PURE__ */ React.createElement("td", { style: { padding: "4px 8px", textAlign: "right", color: "var(--red)" } }, _btNum(r.max_drawdown_pct))
      ), isOpen && /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("td", { colSpan: span, style: { padding: "6px 12px 10px", background: "var(--bg-2)" } }, /* @__PURE__ */ React.createElement(_BtRowDetail, { label: "\uC870\uD569", data: r.__combo }), /* @__PURE__ */ React.createElement(_BtRowDetail, { label: "\uC804\uCCB4 \uBA54\uD2B8\uB9AD", data: r._metrics, numeric: true }))));
    })))));
  }
  function BtModeResultPanel({ baseUrl, isDemo, jobId, mode }) {
    const [data, setData] = useState_bt(null);
    const [err, setErr] = useState_bt("");
    useEffect_bt(() => {
      if (isDemo || !baseUrl || !jobId) {
        setData(null);
        return;
      }
      let cancelled = false;
      _btFetchJson2(baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId), 12e3).then((j) => {
        if (!cancelled) {
          setData(j);
          setErr("");
        }
      }).catch((e) => {
        if (!cancelled) {
          setData(null);
          setErr(String(e));
        }
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, jobId]);
    const mr = data && data.mode_result;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), mode === "wfo" ? "\uC804\uC9C4\uBD84\uC11D(WFO) \uACB0\uACFC" : "\uC2A4\uC715 \uACB0\uACFC")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, err ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, err) : !mr ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uACB0\uACFC\uB97C \uBD88\uB7EC\uC624\uB294 \uC911\uC774\uAC70\uB098 \uAD6C\uC870\uD654 \uACB0\uACFC\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.") : mode === "wfo" ? /* @__PURE__ */ React.createElement(BtWfoTable, { result: mr }) : /* @__PURE__ */ React.createElement(BtSweepTable, { result: mr })));
  }

  // ../frontend/bt-tab-analysis.jsx
  function BtOverlayCurves({ series, normalize }) {
    if (!series || series.length === 0) return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC624\uBC84\uB808\uC774\uD560 \uACE1\uC120\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.");
    const W = 680, H = 220, padL = 8, padR = 8, padT = 12, padB = 12;
    const lines = series.map((s) => {
      const cums = (s.cumulative || []).map((p) => p.cum_profit || 0);
      const base = normalize && cums.length > 0 ? cums[0] : 0;
      return cums.map((v) => v - base);
    });
    const allVals = lines.reduce((acc, ln) => acc.concat(ln), [0]);
    const lo = Math.min(...allVals), hi = Math.max(...allVals);
    const span = hi - lo || 1;
    const maxN = Math.max(1, ...lines.map((l) => l.length));
    const x = (i, n) => padL + (n <= 1 ? 0 : i * (W - padL - padR) / Math.max(1, maxN - 1));
    const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
    const zeroY = y(0);
    return /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, style: { width: "100%", height: 220 }, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, y1: zeroY, x2: W - padR, y2: zeroY, stroke: "var(--line-1)", strokeDasharray: "3 3" }), lines.map((ln, si) => {
      if (ln.length === 0) return null;
      const path = ln.map((v, i) => (i === 0 ? "M" : "L") + x(i, ln.length).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
      return /* @__PURE__ */ React.createElement("path", { key: si, d: path, fill: "none", stroke: _BT_OVERLAY_COLORS[si % _BT_OVERLAY_COLORS.length], strokeWidth: "1.6" });
    }));
  }
  function _btSplitCellPath(cumulative, normalize, W, H, padL, padR, padT, padB) {
    const cums = (cumulative || []).map((p) => p.cum_profit || 0);
    const base = normalize && cums.length > 0 ? cums[0] : 0;
    const vals = cums.map((v) => v - base);
    if (vals.length === 0) return { path: "", zeroY: padT + (H - padT - padB) / 2 };
    const withZero = vals.concat([0]);
    const lo = Math.min(...withZero), hi = Math.max(...withZero);
    const span = hi - lo || 1;
    const n = vals.length;
    const x = (i) => padL + (n <= 1 ? 0 : i * (W - padL - padR) / (n - 1));
    const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
    const path = vals.map((v, i) => (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
    return { path, zeroY: y(0) };
  }
  function BtSplitGrid({ series, normalize }) {
    if (!series || series.length === 0) return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBD84\uD560\uD560 \uACE1\uC120\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.");
    const W = 320, H = 140, padL = 6, padR = 6, padT = 10, padB = 10;
    return /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 } }, series.map((s, si) => {
      const { path, zeroY } = _btSplitCellPath(s.cumulative, normalize, W, H, padL, padR, padT, padB);
      const color = _BT_OVERLAY_COLORS[si % _BT_OVERLAY_COLORS.length];
      const pos = Number(s.summary && s.summary.total_profit_pct) >= 0;
      return /* @__PURE__ */ React.createElement("div", { key: s.job_id, style: { border: "1px solid var(--line-1)", borderRadius: 6, padding: 8, background: "var(--bg-0)" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6, marginBottom: 4 } }, /* @__PURE__ */ React.createElement("span", { style: { width: 10, height: 3, background: color, display: "inline-block", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, s.label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: pos ? "var(--teal)" : "var(--red)" } }, _btNum(s.summary && s.summary.total_profit_pct), "%")), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, style: { width: "100%", height: 120 }, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, y1: zeroY, x2: W - padR, y2: zeroY, stroke: "var(--line-1)", strokeDasharray: "3 3" }), path && /* @__PURE__ */ React.createElement("path", { d: path, fill: "none", stroke: color, strokeWidth: "1.6" })));
    }));
  }
  function BtOverlayPanel({ baseUrl, isDemo, jobs }) {
    const [picked, setPicked] = useState_bt([]);
    const [normalize, setNormalize] = useState_bt(false);
    const [viewMode, setViewMode] = useState_bt("overlay");
    const [result, setResult] = useState_bt(null);
    const [busy, setBusy] = useState_bt(false);
    const [err, setErr] = useState_bt("");
    const doneJobs = (jobs || []).filter((j) => j.status === "success" || j.status === "no_trades");
    const toggle = (jobId) => {
      setPicked((prev) => prev.includes(jobId) ? prev.filter((p) => p !== jobId) : prev.length >= 4 ? prev : prev.concat([jobId]));
    };
    const run = () => {
      if (isDemo || !baseUrl || picked.length < 2) return;
      setBusy(true);
      setErr("");
      setResult(null);
      _btFetchJson2(baseUrl + "/bt/overlay?job_ids=" + encodeURIComponent(picked.join(",")), 15e3).then((j) => {
        if (j && j.status === "ok") setResult(j);
        else {
          setErr(j && j.message || "\uC624\uBC84\uB808\uC774 \uC2E4\uD328");
        }
      }).catch((e) => setErr("\uC2E4\uD328: " + e)).finally(() => setBusy(false));
    };
    const clearAll = () => {
      setPicked([]);
      setResult(null);
      setErr("");
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uB2E4\uC911 \uC7A1 \uC624\uBC84\uB808\uC774", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginLeft: 6 } }, picked.length, "/4")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["overlay", "\uACB9\uCE68"], ["split", "\uBD84\uD560"]].map(([m, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: m,
        onClick: () => setViewMode(m),
        className: "mono",
        title: m === "overlay" ? "\uACB9\uCE68 \u2014 \uBAA8\uB4E0 \uC7A1 \uACE1\uC120\uC744 \uD55C \uCC28\uD2B8\uC5D0 \uACB9\uCCD0 \uADF8\uB9BD\uB2C8\uB2E4." : "\uBD84\uD560 \u2014 \uC7A1\uB9C8\uB2E4 \uC791\uC740 \uCC28\uD2B8\uB85C \uB098\uB220 \uADF8\uB9BD\uB2C8\uB2E4.",
        style: {
          padding: "4px 9px",
          fontSize: 10.5,
          borderRadius: 5,
          cursor: "pointer",
          border: "1px solid " + (viewMode === m ? "var(--teal)" : "var(--line-1)"),
          background: viewMode === m ? "rgba(76,214,179,0.1)" : "transparent",
          color: viewMode === m ? "var(--teal)" : "var(--ink-2)"
        }
      },
      lbl
    ))), /* @__PURE__ */ React.createElement("button", { className: "btn primary sm", onClick: run, disabled: isDemo || busy || picked.length < 2 }, busy ? "\uB85C\uB529\u2026" : "\u25B8 \uACB9\uCCD0\uBCF4\uAE30"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: clearAll, disabled: picked.length === 0 }, "\uBE44\uC6B0\uAE30"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC644\uB8CC \uC7A1\uC744 \uACB9\uCCD0\uBCFC \uC218 \uC788\uC2B5\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(React.Fragment, null, doneJobs.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC644\uB8CC\uB41C \uC7A1\uC774 \uC5C6\uC2B5\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4, flexWrap: "wrap" } }, doneJobs.slice(0, 16).map((j) => {
      const on = picked.includes(j.job_id);
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: j.job_id,
          className: "mono",
          onClick: () => toggle(j.job_id),
          disabled: !on && picked.length >= 4,
          style: {
            fontSize: 10,
            padding: "3px 7px",
            borderRadius: 4,
            cursor: "pointer",
            border: "1px solid " + (on ? "var(--teal)" : "var(--line-1)"),
            background: on ? "rgba(76,214,179,0.1)" : "transparent",
            color: on ? "var(--teal)" : "var(--ink-2)"
          },
          title: j.job_id
        },
        on ? "\u2713 " : "",
        j.job_id.slice(0, 14)
      );
    })), picked.length < 2 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC624\uBC84\uB808\uC774\uC5D0\uB294 2~4\uAC1C \uC7A1\uC774 \uD544\uC694\uD569\uB2C8\uB2E4."), err && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, err), result && result.series && result.series.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--line-1)", paddingTop: 10 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "mono",
        onClick: () => setNormalize((n) => !n),
        style: {
          padding: "4px 9px",
          fontSize: 10.5,
          borderRadius: 5,
          cursor: "pointer",
          border: "1px solid " + (normalize ? "var(--amber)" : "var(--line-1)"),
          background: normalize ? "rgba(240,179,90,0.1)" : "transparent",
          color: normalize ? "var(--amber)" : "var(--ink-2)"
        }
      },
      normalize ? "\u2713 " : "",
      "\uC815\uADDC\uD654(\uCCAB \uD3EC\uC778\uD2B8 0)"
    ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, flexWrap: "wrap" } }, result.series.map((s, i) => /* @__PURE__ */ React.createElement("span", { key: s.job_id, className: "mono", style: { fontSize: 10, display: "inline-flex", alignItems: "center", gap: 5 } }, /* @__PURE__ */ React.createElement("span", { style: { width: 12, height: 3, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], display: "inline-block" } }), s.label)))), viewMode === "split" ? /* @__PURE__ */ React.createElement(BtSplitGrid, { series: result.series, normalize }) : /* @__PURE__ */ React.createElement(BtOverlayCurves, { series: result.series, normalize }), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2 } }, result.series.map((s, i) => /* @__PURE__ */ React.createElement("div", { key: s.job_id, style: { display: "flex", alignItems: "center", gap: 8, padding: "3px 6px", borderBottom: "1px solid var(--line-1)" } }, /* @__PURE__ */ React.createElement("span", { style: { width: 10, height: 10, borderRadius: 2, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], flexShrink: 0 } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, s.label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: Number(s.summary.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" } }, _btNum(s.summary.total_profit_pct), "%"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", width: 70, textAlign: "right" } }, s.summary.trade_count, "\uAC70\uB798"))))))));
  }
  function BtCollapsible({ title, accent, defaultOpen, children }) {
    const [open, setOpen] = useState_bt(!!defaultOpen);
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: open ? 10 : 0 } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setOpen((o) => !o),
        className: "mono",
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 12px",
          borderRadius: 6,
          border: "1px solid var(--line-1)",
          background: "var(--bg-1)",
          cursor: "pointer",
          color: "var(--ink-1)",
          fontSize: 12,
          textAlign: "left"
        }
      },
      /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: accent || "var(--ink-3)" } }),
      /* @__PURE__ */ React.createElement("span", { style: { flex: 1 } }, title),
      /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, open ? "\u25BE \uC811\uAE30" : "\u25B8 \uD3BC\uCE58\uAE30")
    ), open && children);
  }
  function BtEvoSelector({ baseUrl, isDemo, onPickGen, activeEvo }) {
    const [runs, setRuns] = useState_bt([]);
    const [runId, setRunId] = useState_bt("");
    const [gens, setGens] = useState_bt([]);
    const [loadingRuns, setLoadingRuns] = useState_bt(false);
    const [loadingGens, setLoadingGens] = useState_bt(false);
    const loadRuns = useCallback_bt(() => {
      if (isDemo || !baseUrl) {
        setRuns([]);
        return;
      }
      setLoadingRuns(true);
      _btFetchJson2(baseUrl + "/runs", 6e3).then((j) => setRuns(Array.isArray(j && j.runs) ? j.runs : [])).catch(() => setRuns([])).finally(() => setLoadingRuns(false));
    }, [baseUrl, isDemo]);
    useEffect_bt(() => {
      loadRuns();
    }, [loadRuns]);
    useEffect_bt(() => {
      if (isDemo || !baseUrl || !runId) {
        setGens([]);
        return;
      }
      setLoadingGens(true);
      _btFetchJson2(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(runId), 6e3).then((j) => setGens(Array.isArray(j && j.items) ? j.items : [])).catch(() => setGens([])).finally(() => setLoadingGens(false));
    }, [baseUrl, isDemo, runId]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC9C4\uD654 \uC138\uB300 \uBD84\uC11D"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: loadRuns, disabled: isDemo || loadingRuns }, loadingRuns ? "\uB85C\uB529\u2026" : "\u21BB run")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC9C4\uD654 run \uBAA9\uB85D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uC9C4\uD654 run"), /* @__PURE__ */ React.createElement("select", { className: "select", value: runId, onChange: (e) => setRunId(e.target.value) }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 run \uC120\uD0DD \u2014"), runs.map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : "", r.status ? " [" + r.status + "]" : "")))), runId && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 3, maxHeight: 280, overflowY: "auto" } }, loadingGens ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC138\uB300 \uB85C\uB529 \uC911\u2026") : gens.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC138\uB300\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4") : gens.map((g) => {
      const active = activeEvo && activeEvo.run_id === runId && activeEvo.gen_no === g.gen_no;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: g.gen_no,
          onClick: () => onPickGen(runId, g.gen_no),
          style: {
            textAlign: "left",
            padding: "6px 9px",
            borderRadius: 5,
            cursor: "pointer",
            border: "1px solid " + (active ? "var(--violet)" : "var(--line-1)"),
            background: active ? "rgba(168,130,255,0.08)" : "var(--bg-0)",
            display: "flex",
            alignItems: "center",
            gap: 8
          }
        },
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: active ? "var(--violet)" : "var(--ink-0)", flexShrink: 0 } }, "g", g.gen_no),
        /* @__PURE__ */ React.createElement("span", { className: "badge " + (g.gate_passed ? "done" : "idle"), style: { flexShrink: 0 } }, g.gate_passed ? "gate" : "\u2014"),
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 } }, g.strategy_gist || g.buy_name || ""),
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", flexShrink: 0 } }, g.trade_count, "\uAC70\uB798", g.has_csv ? "" : " \xB7\uCD95\uC57D")
      );
    })), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "run ", runs.length, "\uAC1C \xB7 \uC138\uB300 ", gens.length, "\uAC1C (\uC77D\uAE30 \uC804\uC6A9)"))));
  }
  function BtPortfolioCurve({ equity }) {
    if (!equity || equity.length === 0) return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uACB0\uD569 \uACE1\uC120 \uC5C6\uC74C");
    const W = 640, H = 180, padL = 8, padR = 8, padT = 12, padB = 12;
    const cums = equity.map((p) => p.cum_profit || 0);
    const lo = Math.min(0, ...cums), hi = Math.max(0, ...cums);
    const span = hi - lo || 1;
    const n = equity.length;
    const x = (i) => padL + (n <= 1 ? 0 : i * (W - padL - padR) / (n - 1));
    const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
    const path = cums.map((v, i) => (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
    const zeroY = y(0);
    return /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, style: { width: "100%", height: 180 }, preserveAspectRatio: "none" }, /* @__PURE__ */ React.createElement("line", { x1: padL, y1: zeroY, x2: W - padR, y2: zeroY, stroke: "var(--line-1)", strokeDasharray: "3 3" }), /* @__PURE__ */ React.createElement("path", { d: path, fill: "none", stroke: "var(--teal)", strokeWidth: "1.6" }));
  }
  function BtPortfolioHeatmap({ correlation }) {
    const labels = correlation && correlation.labels || [];
    const matrix = correlation && correlation.matrix || [];
    if (labels.length === 0) return null;
    const cell = (r) => {
      if (r == null) return { bg: "var(--bg-1)", txt: "\u2014" };
      const a = Math.min(1, Math.abs(r));
      const color = r >= 0 ? `rgba(76,214,179,${0.12 + a * 0.5})` : `rgba(255,107,107,${0.12 + a * 0.5})`;
      return { bg: color, txt: r.toFixed(2) };
    };
    return /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "mono", style: { borderCollapse: "collapse", fontSize: 10 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { padding: 4 } }), labels.map((l, j) => /* @__PURE__ */ React.createElement("th", { key: j, style: { padding: 4, color: "var(--ink-3)", maxWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, title: l }, l)))), /* @__PURE__ */ React.createElement("tbody", null, matrix.map((row, i) => /* @__PURE__ */ React.createElement("tr", { key: i }, /* @__PURE__ */ React.createElement("td", { style: { padding: 4, color: "var(--ink-3)", maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, title: labels[i] }, labels[i]), row.map((v, j) => {
      const c = cell(v);
      return /* @__PURE__ */ React.createElement("td", { key: j, style: { padding: "6px 8px", textAlign: "center", background: c.bg, color: "var(--ink-1)", border: "1px solid var(--bg-0)" } }, c.txt);
    }))))));
  }
  function BtPortfolioPanel({ baseUrl, isDemo, jobs, activeEvo }) {
    const [picked, setPicked] = useState_bt([]);
    const [result, setResult] = useState_bt(null);
    const [busy, setBusy] = useState_bt(false);
    const [err, setErr] = useState_bt("");
    const addJob = (j) => {
      if (picked.length >= 6) return;
      const key = "job:" + j.job_id;
      if (picked.some((p) => p.key === key)) return;
      setPicked((prev) => prev.concat([{ key, kind: "job", job_id: j.job_id, label: j.job_id.slice(0, 14) }]));
    };
    const addEvo = () => {
      if (!activeEvo || picked.length >= 6) return;
      const key = "gen:" + activeEvo.run_id + "/" + activeEvo.gen_no;
      if (picked.some((p) => p.key === key)) return;
      setPicked((prev) => prev.concat([{
        key,
        kind: "gen",
        run_id: activeEvo.run_id,
        gen_no: activeEvo.gen_no,
        label: activeEvo.run_id.slice(0, 8) + "/g" + activeEvo.gen_no
      }]));
    };
    const removeAt = (key) => setPicked((prev) => prev.filter((p) => p.key !== key));
    const clearAll = () => {
      setPicked([]);
      setResult(null);
      setErr("");
    };
    const run = () => {
      if (isDemo || !baseUrl) return;
      setBusy(true);
      setErr("");
      setResult(null);
      const items = picked.map((p) => p.kind === "job" ? { job_id: p.job_id, label: p.label } : { run_id: p.run_id, gen_no: p.gen_no, label: p.label });
      _btPostJson(baseUrl + "/bt/portfolio", { items }, 2e4).then((j) => {
        if (j && j.status === "ok") {
          setResult(j.portfolio);
        } else {
          setErr(j && j.message || "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uBD84\uC11D \uC2E4\uD328");
        }
      }).catch((e) => setErr("\uC2E4\uD328: " + e)).finally(() => setBusy(false));
    };
    const doneJobs = (jobs || []).filter((j) => j.status === "success" || j.status === "no_trades");
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--blue)" } }), "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uACB0\uD569 \uBD84\uC11D", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginLeft: 6 } }, picked.length, "/6")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6 } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn primary sm",
        onClick: run,
        disabled: isDemo || busy || picked.length < 2
      },
      busy ? "\uBD84\uC11D\uC911\u2026" : "\u25B8 \uACB0\uD569 \uBD84\uC11D"
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: clearAll, disabled: picked.length === 0 }, "\uBE44\uC6B0\uAE30"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC7A1/\uC138\uB300\uB97C \uACB0\uD569\uD560 \uC218 \uC788\uC2B5\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uCD94\uAC00:"), activeEvo && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: addEvo,
        disabled: picked.length >= 6,
        title: "\uD604\uC7AC \uC120\uD0DD\uB41C \uC9C4\uD654 \uC138\uB300\uB97C \uD3EC\uD2B8\uD3F4\uB9AC\uC624\uC5D0 \uCD94\uAC00"
      },
      "\uFF0B\uC138\uB300 ",
      activeEvo.run_id.slice(0, 6),
      "/g",
      activeEvo.gen_no
    )), doneJobs.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4, flexWrap: "wrap" } }, doneJobs.slice(0, 10).map((j) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: j.job_id,
        className: "btn ghost sm",
        onClick: () => addJob(j),
        disabled: picked.length >= 6,
        style: { fontSize: 10, padding: "3px 7px" },
        title: "\uC7A1 " + j.job_id + " \uCD94\uAC00"
      },
      "\uFF0B",
      j.job_id.slice(0, 12)
    ))), picked.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexWrap: "wrap", gap: 4 } }, picked.map((p) => /* @__PURE__ */ React.createElement("span", { key: p.key, className: "mono", style: {
      fontSize: 10,
      padding: "3px 6px",
      borderRadius: 4,
      border: "1px solid " + (p.kind === "gen" ? "var(--violet)" : "var(--teal-dim)"),
      color: p.kind === "gen" ? "var(--violet)" : "var(--teal)",
      display: "inline-flex",
      alignItems: "center",
      gap: 5
    } }, p.label, /* @__PURE__ */ React.createElement("button", { onClick: () => removeAt(p.key), style: { background: "transparent", border: 0, color: "var(--ink-3)", cursor: "pointer", padding: 0 } }, "\u2715")))), picked.length < 2 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uACB0\uD569 \uBD84\uC11D\uC5D0\uB294 2~6\uAC1C \uC804\uB7B5(\uC7A1/\uC138\uB300)\uC774 \uD544\uC694\uD569\uB2C8\uB2E4."), err && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--red)" } }, err), result && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--line-1)", paddingTop: 10 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 16, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11 } }, "\uACB0\uD569 \uCD1D\uC190\uC775 ", /* @__PURE__ */ React.createElement("b", { style: { color: result.combined.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)" } }, _pfFmtMoney(result.combined.total_profit_krw))), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11 } }, "\uACB0\uD569 MDD ", /* @__PURE__ */ React.createElement("b", { style: { color: "var(--red)" } }, Math.round(result.combined.max_drawdown_krw).toLocaleString(), "\uC6D0")), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-3)" } }, result.combined.trading_days, "\uAC70\uB798\uC77C \xB7 ", result.count, "\uC804\uB7B5")), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginBottom: 4 } }, "\uACB0\uD569 \uB204\uC801\uC218\uC775\uACE1\uC120"), /* @__PURE__ */ React.createElement(BtPortfolioCurve, { equity: result.combined.equity })), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginBottom: 4 } }, "\uC804\uB7B5 \uAC04 \uC77C\uBCC4\uC190\uC775 \uC0C1\uAD00"), /* @__PURE__ */ React.createElement(BtPortfolioHeatmap, { correlation: result.correlation })), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginBottom: 4 } }, "\uAC1C\uBCC4 \uAE30\uC5EC"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2 } }, result.strategies.map((s, i) => /* @__PURE__ */ React.createElement("div", { key: i, style: { display: "flex", alignItems: "center", gap: 8, padding: "4px 6px", borderBottom: "1px solid var(--line-1)" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, s.label), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: s.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)" } }, _pfFmtMoney(s.total_profit_krw)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", width: 64, textAlign: "right" } }, "\uAE30\uC5EC ", s.contribution_pct.toFixed(0), "%"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--red)", width: 90, textAlign: "right" } }, "MDD ", Math.round(s.max_drawdown_krw).toLocaleString())))))))));
  }

  // ../frontend/bt-tab-root.jsx
  function BacktestTab({ baseUrl, wsStatus }) {
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const [health, setHealth] = useState_bt(null);
    const [reloadKey, setReloadKey] = useState_bt(0);
    const [resultJobId, setResultJobId] = useState_bt("");
    const [libNames, setLibNames] = useState_bt({ buy: [], sell: [] });
    const [buyName, setBuyName] = useState_bt("");
    const [sellName, setSellName] = useState_bt("");
    const [evoSource, setEvoSource] = useState_bt(null);
    const [jobsList, setJobsList] = useState_bt([]);
    const [jobsReloadKey, setJobsReloadKey] = useState_bt(0);
    const [compareA, setCompareA] = useState_bt("");
    const [compareView, setCompareView] = useState_bt(null);
    const [subTab, setSubTab] = useState_bt(() => {
      try {
        const v = window.localStorage && window.localStorage.getItem("bt_subtab");
        return v === "result" || v === "edit" ? v : "edit";
      } catch (e) {
        return "edit";
      }
    });
    const selectSubTab = useCallback_bt((t) => {
      setSubTab(t);
      try {
        window.localStorage && window.localStorage.setItem("bt_subtab", t);
      } catch (e) {
      }
    }, []);
    const onPickJobResult = useCallback_bt((jobId) => {
      setResultJobId(jobId);
      if (jobId) {
        setEvoSource(null);
        selectSubTab("result");
      }
    }, [selectSubTab]);
    const onPickGen = useCallback_bt((runId, genNo) => {
      setEvoSource({ run_id: runId, gen_no: genNo });
      setResultJobId("");
      selectSubTab("result");
    }, [selectSubTab]);
    useEffect_bt(() => {
      const consume = (detail) => {
        if (detail && detail.run_id && detail.gen_no != null) {
          onPickGen(detail.run_id, detail.gen_no);
        }
      };
      try {
        const raw = window.localStorage && window.localStorage.getItem("stom_bt_evo_pending");
        if (raw) {
          window.localStorage.removeItem("stom_bt_evo_pending");
          consume(JSON.parse(raw));
        }
      } catch (e) {
      }
      const onSelect = (ev) => {
        try {
          window.localStorage && window.localStorage.removeItem("stom_bt_evo_pending");
        } catch (e) {
        }
        consume(ev && ev.detail);
      };
      window.addEventListener("stom:bt-evo-select", onSelect);
      return () => window.removeEventListener("stom:bt-evo-select", onSelect);
    }, [onPickGen]);
    const runCompare = useCallback_bt((jobB) => {
      if (isDemo || !baseUrl || !compareA || !jobB) return;
      const url = baseUrl + "/bt/compare?job_a=" + encodeURIComponent(compareA) + "&job_b=" + encodeURIComponent(jobB);
      _btFetchJson2(url, 12e3).then((j) => setCompareView(j || null)).catch(() => setCompareView(null));
    }, [baseUrl, isDemo, compareA]);
    const onSetCompareA = useCallback_bt((jobId) => {
      setCompareA(jobId);
      setCompareView(null);
    }, []);
    const onCloseCompare = useCallback_bt(() => {
      setCompareView(null);
    }, []);
    useEffect_bt(() => {
      if (isDemo || !baseUrl) {
        setHealth(null);
        return;
      }
      _btFetchJson2(baseUrl + "/bt/health", 3e3).then(setHealth).catch(() => setHealth(null));
    }, [baseUrl, isDemo, reloadKey]);
    useEffect_bt(() => {
      if (isDemo || !baseUrl) {
        setLibNames({ buy: [], sell: [] });
        return;
      }
      let cancelled = false;
      Promise.all([
        _btFetchJson2(baseUrl + "/bt/strategies?kind=buy", 4e3).catch(() => ({ items: [] })),
        _btFetchJson2(baseUrl + "/bt/strategies?kind=sell", 4e3).catch(() => ({ items: [] }))
      ]).then(([b, s]) => {
        if (cancelled) return;
        setLibNames({
          buy: (b.items || []).map((it) => it.name),
          sell: (s.items || []).map((it) => it.name)
        });
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, reloadKey]);
    const connected = !!(health && health.status === "ok");
    const badge = isDemo ? { label: "demo", color: "var(--ink-3)" } : connected ? { label: "connected \xB7 api v" + health.api_version, color: "var(--teal)" } : { label: "checking", color: "var(--amber)" };
    const onSaved = useCallback_bt(() => {
      setReloadKey((k) => k + 1);
    }, []);
    const reloadJobs = useCallback_bt(() => {
      setJobsReloadKey((k) => k + 1);
    }, []);
    const showDemoResult = connected && !isDemo && !resultJobId && !evoSource;
    const effectiveJobId = showDemoResult ? "__demo__" : resultJobId;
    const selectedJobMode = useMemo_bt(() => {
      if (!resultJobId) return "backtest";
      const j = (jobsList || []).find((x) => x.job_id === resultJobId);
      return j && j.spec && j.spec.mode || "backtest";
    }, [jobsList, resultJobId]);
    const isModeResult = resultJobId && (selectedJobMode === "wfo" || selectedJobMode === "sweep");
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "8px 14px",
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: 8
    } }, /* @__PURE__ */ React.createElement("span", { className: "panel-hd-title", style: { border: 0 } }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uBC31\uD14C\uC2A4\uD2B8 \uC6CC\uD06C\uBCA4\uCE58"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: badge.color, letterSpacing: ".06em", marginLeft: "auto" } }, "\u25CF ", badge.label)), isDemo && /* @__PURE__ */ React.createElement("div", { className: "mono", style: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      padding: "8px 14px",
      background: "rgba(240,179,90,0.08)",
      border: "1px solid rgba(240,179,90,0.35)",
      borderRadius: 8,
      fontSize: 11.5,
      color: "var(--amber)"
    } }, /* @__PURE__ */ React.createElement("span", { className: "badge warn", style: { flexShrink: 0 } }, "\uB370\uBAA8 \uBAA8\uB4DC"), "\uBC31\uC5D4\uB4DC \uBBF8\uC5F0\uACB0 \u2014 \uD45C\uC2DC\uB418\uB294 \uACB0\uACFC\uB294 \uC608\uC2DC\uC774\uBA70 \uC2E4\uC81C \uB370\uC774\uD130\uAC00 \uC544\uB2D9\uB2C8\uB2E4. \uC11C\uBC84\uC5D0 \uC5F0\uACB0\uD558\uBA74 \uC2E4\uAC70\uB798 \uBC31\uD14C\uC2A4\uD2B8\uAC00 \uD65C\uC131\uD654\uB429\uB2C8\uB2E4."), /* @__PURE__ */ React.createElement(
      BtRunPanel,
      {
        baseUrl,
        isDemo,
        libNames,
        onResult: onPickJobResult,
        compareA,
        onCompareB: runCompare,
        onJobs: setJobsList,
        buy: buyName,
        sell: sellName,
        onBuy: setBuyName,
        onSell: setSellName,
        reloadJobsKey: jobsReloadKey
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "bt-subtabs", style: {
      display: "flex",
      gap: 4,
      padding: 4,
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: 8
    } }, [
      { id: "edit", label: "\uC870\uAC74\uC2DD \uD3B8\uC9D1" },
      { id: "result", label: "\uACB0\uACFC \uBD84\uC11D" }
    ].map((t) => {
      const active = subTab === t.id;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: t.id,
          onClick: () => selectSubTab(t.id),
          style: {
            flex: 1,
            padding: "9px 14px",
            borderRadius: 6,
            cursor: "pointer",
            fontFamily: "var(--mono)",
            fontSize: 13,
            fontWeight: active ? 700 : 400,
            border: active ? "1px solid var(--teal-dim, var(--teal))" : "1px solid transparent",
            background: active ? "var(--bg-0)" : "transparent",
            color: active ? "var(--teal)" : "var(--ink-2)"
          }
        },
        t.label
      );
    })), subTab === "edit" && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement(
      BtDualEditor,
      {
        baseUrl,
        isDemo,
        buyName,
        sellName,
        onSaved,
        onDeletedBuy: () => {
          setReloadKey((k) => k + 1);
          setBuyName("");
        },
        onDeletedSell: () => {
          setReloadKey((k) => k + 1);
          setSellName("");
        }
      }
    ), /* @__PURE__ */ React.createElement(BtCollapsible, { title: "\uC870\uAC74\uC2DD \uB77C\uC774\uBE0C\uB7EC\uB9AC(\uBE60\uB978 \uC120\uD0DD)", accent: "var(--teal)", defaultOpen: true }, /* @__PURE__ */ React.createElement("div", { className: "grid-main", style: { gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" } }, /* @__PURE__ */ React.createElement(
      BtLibraryPanel,
      {
        baseUrl,
        isDemo,
        kind: "buy",
        onKind: () => {
        },
        lockKind: true,
        onPick: setBuyName,
        selectedName: buyName,
        reloadKey
      }
    ), /* @__PURE__ */ React.createElement(
      BtLibraryPanel,
      {
        baseUrl,
        isDemo,
        kind: "sell",
        onKind: () => {
        },
        lockKind: true,
        onPick: setSellName,
        selectedName: sellName,
        reloadKey
      }
    )))), subTab === "result" && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement(
      BtResultLibrary,
      {
        baseUrl,
        isDemo,
        jobs: jobsList,
        onResult: onPickJobResult,
        selectedJobId: resultJobId,
        onReload: reloadJobs,
        compareA,
        onSetCompareA,
        onCompareB: runCompare
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { minWidth: 0, position: "relative" } }, showDemoResult && /* @__PURE__ */ React.createElement("span", { className: "badge warn", style: { position: "absolute", top: 10, right: 10, zIndex: 2 } }, "\uC608\uC2DC \uB370\uC774\uD130"), isModeResult ? /* @__PURE__ */ React.createElement(BtModeResultPanel, { baseUrl, isDemo, jobId: resultJobId, mode: selectedJobMode }) : /* @__PURE__ */ React.createElement(
      BtResultArea,
      {
        baseUrl,
        isDemo,
        jobId: effectiveJobId,
        evoSource,
        onSetCompareA,
        compareView,
        onCloseCompare
      }
    )), /* @__PURE__ */ React.createElement(BtCollapsible, { title: "\uC9C4\uD654 \uC138\uB300 \uBD84\uC11D", accent: "var(--violet)", defaultOpen: false }, /* @__PURE__ */ React.createElement(BtEvoSelector, { baseUrl, isDemo, onPickGen, activeEvo: evoSource })), /* @__PURE__ */ React.createElement(BtCollapsible, { title: "\uB2E4\uC911 \uC7A1 \uC624\uBC84\uB808\uC774(\uC218\uC775\uACE1\uC120 \uACB9\uCCD0\uBCF4\uAE30)", accent: "var(--teal)", defaultOpen: false }, /* @__PURE__ */ React.createElement(BtOverlayPanel, { baseUrl, isDemo, jobs: jobsList })), /* @__PURE__ */ React.createElement(BtCollapsible, { title: "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uACB0\uD569 \uBD84\uC11D", accent: "var(--blue)", defaultOpen: false }, /* @__PURE__ */ React.createElement(BtPortfolioPanel, { baseUrl, isDemo, jobs: jobsList, activeEvo: evoSource }))));
  }

  // ../frontend/backtest.jsx
  Object.assign(window, { BacktestTab });

  // ../frontend/simulation-charts.jsx
  var {
    useState: useState_simc,
    useRef: useRef_simc,
    useMemo: useMemo_simc,
    useEffect: useEffect_simc
  } = React;
  var _SIM_WINDOW = 400;
  var _SIM_LWC_MAX = 5e3;
  var _SIM_DEFAULT_INDICATORS = {
    ma: true,
    vwap: true,
    boll: false,
    ema: false,
    rsi: false,
    macd: false,
    volma: false,
    strma: false,
    vwapband: false,
    strength: true,
    imbalance: false,
    orderflow: false
  };
  var _SIM_IND_STYLE = {
    ma5: { color: "#4cd6b3", width: 1, dashed: true, label: "MA5" },
    ma20: { color: "#f0b35a", width: 1.1, dashed: false, label: "MA20" },
    ma60: { color: "#7c6cf0", width: 1.1, dashed: false, label: "MA60" },
    vwap: { color: "#ffd24c", width: 1.4, dashed: false, label: "VWAP" },
    bb_up: { color: "#5a93c8", width: 1, dashed: true, label: "BB+" },
    bb_mid: { color: "#5a93c8", width: 0.9, dashed: true, label: "BB" },
    bb_low: { color: "#5a93c8", width: 1, dashed: true, label: "BB-" },
    // Phase7 — 클라이언트 계산 라인(EMA/VWAP밴드).
    ema12: { color: "#6fd6ff", width: 1, dashed: false, label: "EMA12" },
    ema26: { color: "#b07cf0", width: 1, dashed: false, label: "EMA26" },
    vwap_up: { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP+" },
    vwap_low: { color: "#ffd24c", width: 0.9, dashed: true, label: "VWAP-" }
  };
  function _simSma(bars, period, sel) {
    const out = new Array(bars.length).fill(null);
    let sum = 0, cnt = 0;
    const q = [];
    for (let i = 0; i < bars.length; i++) {
      const v = sel(bars[i]);
      const x = v != null && isFinite(v) ? v : null;
      q.push(x);
      if (x != null) {
        sum += x;
        cnt++;
      }
      if (q.length > period) {
        const drop = q.shift();
        if (drop != null) {
          sum -= drop;
          cnt--;
        }
      }
      out[i] = q.length >= period && cnt === period ? sum / period : null;
    }
    return out;
  }
  function _simEma(bars, period) {
    const out = new Array(bars.length).fill(null);
    const k = 2 / (period + 1);
    let ema = null;
    for (let i = 0; i < bars.length; i++) {
      const c = bars[i].c;
      if (c == null || !isFinite(c)) {
        out[i] = ema;
        continue;
      }
      ema = ema == null ? c : c * k + ema * (1 - k);
      out[i] = ema;
    }
    return out;
  }
  function _simRsi(bars, period) {
    const p = period || 14;
    const out = new Array(bars.length).fill(null);
    let avgGain = null, avgLoss = null, prev = null;
    let seedG = 0, seedL = 0, seedN = 0;
    for (let i = 0; i < bars.length; i++) {
      const c = bars[i].c;
      if (c == null || !isFinite(c)) {
        out[i] = null;
        continue;
      }
      if (prev == null) {
        prev = c;
        out[i] = null;
        continue;
      }
      const ch = c - prev;
      prev = c;
      const gain = ch > 0 ? ch : 0, loss = ch < 0 ? -ch : 0;
      if (avgGain == null) {
        seedG += gain;
        seedL += loss;
        seedN++;
        if (seedN === p) {
          avgGain = seedG / p;
          avgLoss = seedL / p;
        } else {
          out[i] = null;
          continue;
        }
      } else {
        avgGain = (avgGain * (p - 1) + gain) / p;
        avgLoss = (avgLoss * (p - 1) + loss) / p;
      }
      const rs = avgLoss === 0 ? Infinity : avgGain / avgLoss;
      out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + rs);
    }
    return out;
  }
  function _simMacd(bars) {
    const fast = _simEma(bars, 12);
    const slow = _simEma(bars, 26);
    const macd = bars.map((b, i) => fast[i] != null && slow[i] != null ? fast[i] - slow[i] : null);
    const signal = new Array(bars.length).fill(null);
    const k = 2 / (9 + 1);
    let s = null;
    for (let i = 0; i < bars.length; i++) {
      const m = macd[i];
      if (m == null) {
        signal[i] = s;
        continue;
      }
      s = s == null ? m : m * k + s * (1 - k);
      signal[i] = s;
    }
    const hist = bars.map((b, i) => macd[i] != null && signal[i] != null ? macd[i] - signal[i] : null);
    return { macd, signal, hist };
  }
  function _simVolMa(bars, periods) {
    const ps = periods || [5, 20];
    const out = {};
    ps.forEach((p) => {
      out["vol_ma" + p] = _simSma(bars, p, (b) => b.vol);
    });
    return out;
  }
  function _simStrengthMa(bars, period) {
    return _simSma(bars, period || 5, (b) => b.strength);
  }
  var _simTimeLabel = window._hmsTimeLabel;
  var _simPriceTick = window._priceTick;
  function _hmsToSec(hms) {
    const s = String(hms).padStart(6, "0");
    return parseInt(s.slice(0, 2), 10) * 3600 + parseInt(s.slice(2, 4), 10) * 60 + parseInt(s.slice(4, 6), 10);
  }
  function _strengthColor(v, alpha) {
    const a = alpha == null ? 1 : alpha;
    const s = Math.max(0, Math.min(200, v == null ? 100 : v));
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
    return typeof window !== "undefined" && window.LightweightCharts && typeof window.LightweightCharts.createChart === "function";
  }
  var _SESSION_START_SEC = 9 * 3600;
  var _SESSION_END_SEC = 15 * 3600 + 30 * 60;
  function _sessionProgress(hms) {
    if (hms == null) return 0;
    const sec = _hmsToSec(hms);
    const span = _SESSION_END_SEC - _SESSION_START_SEC;
    if (span <= 0) return 0;
    return Math.max(0, Math.min(1, (sec - _SESSION_START_SEC) / span));
  }
  function _changeColor(pct) {
    const v = Number(pct) || 0;
    const mag = Math.min(1, Math.abs(v) / 12);
    const a = (0.35 + mag * 0.6).toFixed(3);
    if (v > 0) return `rgba(255,93,108,${a})`;
    if (v < 0) return `rgba(56,140,255,${a})`;
    return "rgba(150,158,170,0.5)";
  }
  function SimChangeGauge({ changePct, size }) {
    const S = size || 56;
    const v = Number(changePct) || 0;
    const clamped = Math.max(-12, Math.min(12, v));
    const angle = 180 - (clamped + 12) / 24 * 180;
    const rad = angle * Math.PI / 180;
    const r = S / 2 - 4;
    const cx = S / 2, cy = S / 2;
    const nx = cx + r * Math.cos(rad);
    const ny = cy - r * Math.sin(rad);
    const color = _changeColor(v);
    return /* @__PURE__ */ React.createElement("svg", { width: S, height: S / 2 + 6, viewBox: `0 0 ${S} ${S / 2 + 6}`, "aria-hidden": "true" }, /* @__PURE__ */ React.createElement(
      "path",
      {
        d: `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`,
        fill: "none",
        stroke: "var(--line-2)",
        strokeWidth: "3",
        strokeLinecap: "round"
      }
    ), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: cx,
        y1: cy - r,
        x2: cx,
        y2: cy - r + 4,
        stroke: "var(--ink-3)",
        strokeWidth: "1"
      }
    ), /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: cx,
        y1: cy,
        x2: nx.toFixed(2),
        y2: ny.toFixed(2),
        stroke: color,
        strokeWidth: "2.4",
        strokeLinecap: "round"
      }
    ), /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "2.6", fill: color }), /* @__PURE__ */ React.createElement(
      "text",
      {
        x: cx,
        y: cy - 2,
        textAnchor: "middle",
        fontSize: "10",
        className: "mono",
        fill: color
      },
      v > 0 ? "+" : "",
      v.toFixed(2),
      "%"
    ));
  }
  function SimSessionRing({ curT, size }) {
    const S = size || 52;
    const r = S / 2 - 5;
    const cx = S / 2, cy = S / 2;
    const circ = 2 * Math.PI * r;
    const prog = _sessionProgress(curT);
    const dash = (circ * prog).toFixed(2);
    const label = curT != null ? _simTimeLabel(curT).slice(0, 5) : "--:--";
    return /* @__PURE__ */ React.createElement("svg", { width: S, height: S, viewBox: `0 0 ${S} ${S}`, "aria-hidden": "true" }, /* @__PURE__ */ React.createElement("circle", { cx, cy, r, fill: "none", stroke: "var(--line-2)", strokeWidth: "3" }), /* @__PURE__ */ React.createElement(
      "circle",
      {
        cx,
        cy,
        r,
        fill: "none",
        stroke: "var(--teal)",
        strokeWidth: "3",
        strokeLinecap: "round",
        strokeDasharray: `${dash} ${(circ - dash).toFixed(2)}`,
        transform: `rotate(-90 ${cx} ${cy})`
      }
    ), /* @__PURE__ */ React.createElement(
      "text",
      {
        x: cx,
        y: cy + 3.2,
        textAnchor: "middle",
        fontSize: "10",
        className: "mono",
        fill: "var(--ink-1)"
      },
      label
    ));
  }
  function SimHeatStrip({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const n = view.length;
    if (n === 0) return null;
    const H = compact ? 14 : 18;
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--violet)", flexShrink: 0, width: 48 } }, "\uCCB4\uACB0\uAC15\uB3C4"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" } }, view.map((b, i) => /* @__PURE__ */ React.createElement(
      "div",
      {
        key: i,
        title: _simTimeLabel(b.t) + " \xB7 " + (b.strength || 0).toFixed(0),
        style: { flex: 1, background: _strengthColor(b.strength, 0.85) }
      }
    ))));
  }
  function SimRestFlow({ bars, compact }) {
    const [open, setOpen] = useState_simc(false);
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const hasData = useMemo_simc(
      () => view.some((b) => b.buy_rest != null && isFinite(b.buy_rest) || b.sell_rest != null && isFinite(b.sell_rest)),
      [view]
    );
    if (!hasData) return null;
    const n = view.length;
    const W = 880;
    const half = compact ? 28 : 38;
    const H = half * 2 + 18;
    const padL = 56, padR = 16;
    const innerW = W - padL - padR;
    const mid = half + 4;
    const buyVals = view.map((b) => b.buy_rest != null && isFinite(b.buy_rest) ? b.buy_rest : 0);
    const sellVals = view.map((b) => b.sell_rest != null && isFinite(b.sell_rest) ? b.sell_rest : 0);
    const maxRest = Math.max(1, ...buyVals, ...sellVals);
    const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + innerW * i / (n - 1);
    const yBuy = (v) => mid - Math.min(v, maxRest) / maxRest * half;
    const ySell = (v) => mid + Math.min(v, maxRest) / maxRest * half;
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
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setOpen((o) => !o),
        className: "mono",
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "4px 8px",
          background: "transparent",
          border: "1px solid var(--line-1)",
          borderRadius: 5,
          color: "var(--ink-2)",
          cursor: "pointer",
          fontSize: 10
        }
      },
      /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, open ? "\u25BC" : "\u25B6"),
      "\uD638\uAC00 \uC794\uB7C9 \uD750\uB984",
      lastBuy != null && /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", color: "var(--teal)" } }, "\uB9E4\uC218 ", _simPriceTick(lastBuy)),
      lastSell != null && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, "\uB9E4\uB3C4 ", _simPriceTick(lastSell))
    ), open && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 4 } }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: mid,
        y2: mid,
        stroke: "var(--line-2)",
        strokeWidth: "1"
      }
    ), n > 0 && /* @__PURE__ */ React.createElement(
      "path",
      {
        d: areaPath(buyVals, yBuy),
        fill: "rgba(76,214,179,0.28)",
        stroke: "var(--teal)",
        strokeWidth: "1"
      }
    ), n > 0 && /* @__PURE__ */ React.createElement(
      "path",
      {
        d: areaPath(sellVals, ySell),
        fill: "rgba(255,93,108,0.26)",
        stroke: "var(--red)",
        strokeWidth: "1"
      }
    ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: mid - half + 8, textAnchor: "end", fill: "var(--teal)" }, "\uB9E4\uC218"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: mid + half, textAnchor: "end", fill: "var(--red)" }, "\uB9E4\uB3C4"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: mid + 3, textAnchor: "end", fill: "var(--ink-3)" }, _simPriceTick(maxRest)))));
  }
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
  function _lineData(bars, secs, key) {
    const out = [];
    for (let i = 0; i < bars.length; i++) {
      const v = bars[i][key];
      if (v == null || !isFinite(v)) continue;
      out.push({ time: secs[i], value: v });
    }
    return out;
  }
  function SimCandleChartLWC({ bars, signals, curT, code, name, compact, indicators }) {
    const wrapRef = useRef_simc(null);
    const chartRef = useRef_simc(null);
    const candleRef = useRef_simc(null);
    const volRef = useRef_simc(null);
    const roRef = useRef_simc(null);
    const lineRef = useRef_simc({});
    const strRef = useRef_simc(null);
    const strMaRef = useRef_simc(null);
    const ind = indicators || _SIM_DEFAULT_INDICATORS;
    const H = compact ? 240 : 360;
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
          rightOffset: 4,
          barSpacing: 7,
          minBarSpacing: 2,
          timeVisible: true,
          secondsVisible: !compact,
          tickMarkFormatter: (t) => {
            const sec = (t % 86400 + 86400) % 86400;
            const hh = String(Math.floor(sec / 3600)).padStart(2, "0");
            const mm = String(Math.floor(sec % 3600 / 60)).padStart(2, "0");
            return hh + ":" + mm;
          }
        },
        crosshair: { mode: LWC.CrosshairMode ? LWC.CrosshairMode.Normal : 0 },
        handleScroll: true,
        handleScale: true
      });
      const candle = chart.addCandlestickSeries({
        upColor: "#4cd6b3",
        downColor: "#ff5d6c",
        borderUpColor: "#4cd6b3",
        borderDownColor: "#ff5d6c",
        wickUpColor: "#4cd6b3",
        wickDownColor: "#ff5d6c"
      });
      const vol = chart.addHistogramSeries({
        priceFormat: { type: "volume" },
        priceScaleId: "vol"
      });
      chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
      chartRef.current = chart;
      candleRef.current = candle;
      volRef.current = vol;
      const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => {
        if (chartRef.current && el.clientWidth) chartRef.current.applyOptions({ width: el.clientWidth });
      }) : null;
      if (ro) {
        ro.observe(el);
        roRef.current = ro;
      }
      return () => {
        if (roRef.current) {
          try {
            roRef.current.disconnect();
          } catch (e) {
          }
          roRef.current = null;
        }
        try {
          chart.remove();
        } catch (e) {
        }
        chartRef.current = null;
        candleRef.current = null;
        volRef.current = null;
        lineRef.current = {};
        strRef.current = null;
        strMaRef.current = null;
      };
    }, [H, compact]);
    useEffect_simc(() => {
      const candle = candleRef.current, vol = volRef.current;
      if (!candle || !vol) return;
      const arr = bars || [];
      const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
      const cData = [];
      const vData = [];
      let lastSec = -1;
      for (let i = 0; i < src.length; i++) {
        const b = src[i];
        let sec = _hmsToSec(b.t);
        if (sec <= lastSec) sec = lastSec + 1;
        lastSec = sec;
        const up = (b.c || 0) >= (b.o || 0);
        cData.push({ time: sec, open: b.o || b.c || 0, high: b.h || b.c || 0, low: b.l || b.c || 0, close: b.c || 0 });
        vData.push({ time: sec, value: b.vol || 0, color: up ? "rgba(76,214,179,0.4)" : "rgba(255,93,108,0.4)" });
      }
      try {
        candle.setData(cData);
        vol.setData(vData);
      } catch (e) {
      }
    }, [bars]);
    useEffect_simc(() => {
      const chart = chartRef.current;
      if (!chart || typeof chart.addLineSeries !== "function") return;
      const arr = bars || [];
      const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
      const secs = _monotonicSecs(src);
      const lines = lineRef.current;
      const active = {};
      if (ind.ma) {
        active.ma5 = 1;
        active.ma20 = 1;
        active.ma60 = 1;
      }
      if (ind.vwap) active.vwap = 1;
      if (ind.boll) {
        active.bb_up = 1;
        active.bb_mid = 1;
        active.bb_low = 1;
      }
      if (ind.vwapband) {
        active.vwap_up = 1;
        active.vwap_low = 1;
      }
      if (ind.ema) {
        active.ema12 = 1;
        active.ema26 = 1;
      }
      const emaData = {};
      if (ind.ema) {
        const e12 = _simEma(src, 12), e26 = _simEma(src, 26);
        emaData.ema12 = [];
        emaData.ema26 = [];
        for (let i = 0; i < src.length; i++) {
          if (e12[i] != null && isFinite(e12[i])) emaData.ema12.push({ time: secs[i], value: e12[i] });
          if (e26[i] != null && isFinite(e26[i])) emaData.ema26.push({ time: secs[i], value: e26[i] });
        }
      }
      Object.keys(lines).forEach((key) => {
        if (!active[key]) {
          try {
            chart.removeSeries(lines[key]);
          } catch (e) {
          }
          delete lines[key];
        }
      });
      Object.keys(active).forEach((key) => {
        const st = _SIM_IND_STYLE[key];
        if (!st) return;
        if (!lines[key]) {
          try {
            lines[key] = chart.addLineSeries({
              color: st.color,
              lineWidth: st.width,
              lineStyle: st.dashed && window.LightweightCharts && window.LightweightCharts.LineStyle ? window.LightweightCharts.LineStyle.Dashed : 0,
              priceLineVisible: false,
              lastValueVisible: false,
              crosshairMarkerVisible: false
            });
          } catch (e) {
            return;
          }
        }
        const data = key === "ema12" || key === "ema26" ? emaData[key] || [] : _lineData(src, secs, key);
        try {
          lines[key].setData(data);
        } catch (e) {
        }
      });
    }, [bars, ind.ma, ind.vwap, ind.boll, ind.ema, ind.vwapband]);
    useEffect_simc(() => {
      const chart = chartRef.current;
      if (!chart || typeof chart.addLineSeries !== "function") return;
      const arr = bars || [];
      const src = arr.length > _SIM_LWC_MAX ? arr.slice(arr.length - _SIM_LWC_MAX) : arr;
      const secs = _monotonicSecs(src);
      const ensureScale = () => {
        try {
          chart.priceScale("strength").applyOptions({ scaleMargins: { top: 0.86, bottom: 0 } });
        } catch (e) {
        }
      };
      if (ind.strength) {
        if (!strRef.current) {
          try {
            strRef.current = chart.addLineSeries({
              color: "#7c6cf0",
              lineWidth: 1.2,
              priceScaleId: "strength",
              priceLineVisible: false,
              lastValueVisible: false,
              crosshairMarkerVisible: false
            });
          } catch (e) {
            strRef.current = null;
          }
          ensureScale();
        }
        if (strRef.current) {
          const data = [];
          for (let i = 0; i < src.length; i++) {
            const s = src[i].strength;
            if (s != null && isFinite(s)) data.push({ time: secs[i], value: s });
          }
          try {
            strRef.current.setData(data);
          } catch (e) {
          }
        }
      } else if (strRef.current) {
        try {
          chart.removeSeries(strRef.current);
        } catch (e) {
        }
        strRef.current = null;
      }
      if (ind.strength && ind.strma) {
        if (!strMaRef.current) {
          try {
            strMaRef.current = chart.addLineSeries({
              color: "#f0b35a",
              lineWidth: 1,
              priceScaleId: "strength",
              lineStyle: window.LightweightCharts && window.LightweightCharts.LineStyle ? window.LightweightCharts.LineStyle.Dashed : 0,
              priceLineVisible: false,
              lastValueVisible: false,
              crosshairMarkerVisible: false
            });
          } catch (e) {
            strMaRef.current = null;
          }
          ensureScale();
        }
        if (strMaRef.current) {
          const ma = _simStrengthMa(src, 5);
          const data = [];
          for (let i = 0; i < src.length; i++) {
            if (ma[i] != null && isFinite(ma[i])) data.push({ time: secs[i], value: ma[i] });
          }
          try {
            strMaRef.current.setData(data);
          } catch (e) {
          }
        }
      } else if (strMaRef.current) {
        try {
          chart.removeSeries(strMaRef.current);
        } catch (e) {
        }
        strMaRef.current = null;
      }
    }, [bars, ind.strength, ind.strma]);
    useEffect_simc(() => {
      const candle = candleRef.current;
      if (!candle) return;
      const arr = bars || [];
      if (arr.length === 0) {
        try {
          candle.setMarkers([]);
        } catch (e) {
        }
        return;
      }
      const secOf = [];
      let lastSec = -1;
      for (let i = 0; i < arr.length; i++) {
        let sec = _hmsToSec(arr[i].t);
        if (sec <= lastSec) sec = lastSec + 1;
        lastSec = sec;
        secOf.push(sec);
      }
      const nearestSec = (hms) => {
        let best = -1;
        for (let i = 0; i < arr.length; i++) {
          if (arr[i].t <= hms) best = i;
          else break;
        }
        return best >= 0 ? secOf[best] : null;
      };
      const markers = [];
      (signals || []).forEach((sig) => {
        if (curT == null || sig.buy_hms <= curT) {
          const s = nearestSec(sig.buy_hms);
          if (s != null) markers.push({ time: s, position: "belowBar", color: "#4cd6b3", shape: "arrowUp", text: "\uB9E4\uC218" });
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
      try {
        candle.setMarkers(markers);
      } catch (e) {
      }
    }, [signals, curT, bars, compact]);
    const lastBar = bars && bars.length ? bars[bars.length - 1] : null;
    return /* @__PURE__ */ React.createElement(
      SimChartShell,
      {
        code,
        name,
        lastBar,
        bars,
        signals,
        curT,
        compact,
        engine: "lwc",
        indicators: ind
      },
      /* @__PURE__ */ React.createElement("div", { ref: wrapRef, style: { width: "100%", height: H } })
    );
  }
  function SimCandleChartSVG({ bars, signals, curT, code, name, compact, indicators }) {
    const ind = indicators || _SIM_DEFAULT_INDICATORS;
    const [hover, setHover] = useState_simc(null);
    const [zoom, setZoom] = useState_simc(0);
    const [pan, setPan] = useState_simc(0);
    const dragRef = useRef_simc(null);
    const svgRef = useRef_simc(null);
    const allBars = bars || [];
    const visCount = Math.max(20, Math.min(allBars.length || _SIM_WINDOW, _SIM_WINDOW - zoom * 40));
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
    const highs = view.map((b) => b.h || b.c || 0);
    const lows = view.map((b) => b.l || b.c || 0).filter((v) => v > 0);
    const pMax = highs.length ? Math.max(...highs) : 1;
    const pMin = lows.length ? Math.min(...lows) : 0;
    const pRange = pMax - pMin || 1;
    const yPrice = (v) => priceBot - (v - pMin) / pRange * priceH;
    const volTop = priceBot + gap;
    const volBot = volTop + volH;
    const vMax = Math.max(1, ...view.map((b) => b.vol || 0));
    const yVol = (v) => volBot - v / vMax * volH;
    const strTop = volBot + gap;
    const strBot = strTop + strH;
    const strVals = view.map((b) => b.strength || 0);
    const sMax = Math.max(100, ...strVals);
    const yStr = (v) => strBot - Math.min(v, sMax) / sMax * strH;
    const tIndex = useMemo_simc(() => {
      const m = /* @__PURE__ */ new Map();
      view.forEach((b, i) => m.set(b.t, i));
      return m;
    }, [view]);
    const nearestIdx = (hms) => {
      if (tIndex.has(hms)) return tIndex.get(hms);
      let best = -1;
      for (let i = 0; i < n; i++) {
        if (view[i].t <= hms) best = i;
        else break;
      }
      return best;
    };
    const strPath = useMemo_simc(() => {
      if (n < 2) return "";
      return view.map(
        (b, i) => `${i === 0 ? "M" : "L"} ${xCenter(i).toFixed(1)} ${yStr(b.strength || 0).toFixed(1)}`
      ).join(" ");
    }, [view, n, sMax]);
    const ema12 = useMemo_simc(() => ind.ema ? _simEma(view, 12) : [], [view, ind.ema]);
    const ema26 = useMemo_simc(() => ind.ema ? _simEma(view, 26) : [], [view, ind.ema]);
    const strMa = useMemo_simc(() => ind.strength && ind.strma ? _simStrengthMa(view, 5) : [], [view, ind.strength, ind.strma]);
    const volMa = useMemo_simc(() => ind.volma ? _simVolMa(view, [5, 20]) : {}, [view, ind.volma]);
    const arrPath = (vals, yFn) => {
      if (!vals || n < 2) return "";
      let d = "", started = false;
      for (let i = 0; i < n; i++) {
        const v = vals[i];
        if (v == null || !isFinite(v)) {
          started = false;
          continue;
        }
        d += `${started ? "L" : "M"} ${xCenter(i).toFixed(1)} ${yFn(v).toFixed(1)} `;
        started = true;
      }
      return d;
    };
    const maPath = (key) => {
      if (n < 2) return "";
      let d = "", started = false;
      view.forEach((b, i) => {
        const v = b[key];
        if (v == null) {
          started = false;
          return;
        }
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
      if (i >= 0 && i < n) setHover(i);
      else setHover(null);
      if (dragRef.current != null) {
        const dxPx = (e.clientX - dragRef.current.x) * (W / rect.width);
        const dCandles = Math.round(dxPx / Math.max(1, slot));
        const next = Math.max(0, Math.min(allBars.length - visCount, dragRef.current.pan + dCandles));
        setPan(next);
      }
    };
    const onWheel = (e) => {
      e.preventDefault();
      setZoom((z) => Math.max(0, Math.min(8, z + (e.deltaY < 0 ? 1 : -1))));
    };
    const onDown = (e) => {
      dragRef.current = { x: e.clientX, pan };
    };
    const onUp = () => {
      dragRef.current = null;
    };
    const lastBar = bars && bars.length ? bars[bars.length - 1] : null;
    return /* @__PURE__ */ React.createElement(
      SimChartShell,
      {
        code,
        name,
        lastBar,
        bars,
        signals,
        curT,
        compact,
        engine: "svg",
        indicators: ind
      },
      /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement(
        "svg",
        {
          ref: svgRef,
          viewBox: `0 0 ${W} ${H}`,
          preserveAspectRatio: "none",
          onMouseMove: onMove,
          onMouseLeave: () => {
            setHover(null);
            onUp();
          },
          onWheel,
          onMouseDown: onDown,
          onMouseUp: onUp,
          style: { cursor: dragRef.current ? "grabbing" : "crosshair" }
        },
        /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: priceTop + 8, textAnchor: "end", fill: "var(--ink-2)" }, _simPriceTick(pMax)),
        /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: priceBot, textAnchor: "end", fill: "var(--ink-2)" }, _simPriceTick(pMin)),
        /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: priceBot, y2: priceBot, stroke: "var(--line-2)", strokeWidth: "1" }),
        /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: priceTop, y2: priceBot, stroke: "var(--line-2)", strokeWidth: "1" }),
        n > 1 && ind.ma && /* @__PURE__ */ React.createElement("path", { d: maPath("ma5"), fill: "none", stroke: "var(--teal)", strokeWidth: "1", opacity: "0.5", strokeDasharray: "3 2" }),
        n > 1 && ind.ma && /* @__PURE__ */ React.createElement("path", { d: maPath("ma20"), fill: "none", stroke: "var(--amber)", strokeWidth: "1.1", opacity: "0.7" }),
        n > 1 && ind.ma && /* @__PURE__ */ React.createElement("path", { d: maPath("ma60"), fill: "none", stroke: "var(--violet)", strokeWidth: "1.1", opacity: "0.6" }),
        n > 1 && ind.vwap && /* @__PURE__ */ React.createElement("path", { d: maPath("vwap"), fill: "none", stroke: "#ffd24c", strokeWidth: "1.4", opacity: "0.85" }),
        n > 1 && ind.vwapband && /* @__PURE__ */ React.createElement("path", { d: maPath("vwap_up"), fill: "none", stroke: "#ffd24c", strokeWidth: "0.9", opacity: "0.5", strokeDasharray: "2 3" }),
        n > 1 && ind.vwapband && /* @__PURE__ */ React.createElement("path", { d: maPath("vwap_low"), fill: "none", stroke: "#ffd24c", strokeWidth: "0.9", opacity: "0.5", strokeDasharray: "2 3" }),
        n > 1 && ind.ema && /* @__PURE__ */ React.createElement("path", { d: arrPath(ema12, yPrice), fill: "none", stroke: "#6fd6ff", strokeWidth: "1", opacity: "0.7" }),
        n > 1 && ind.ema && /* @__PURE__ */ React.createElement("path", { d: arrPath(ema26, yPrice), fill: "none", stroke: "#b07cf0", strokeWidth: "1", opacity: "0.7" }),
        n > 1 && ind.boll && /* @__PURE__ */ React.createElement("path", { d: maPath("bb_up"), fill: "none", stroke: "#5a93c8", strokeWidth: "1", opacity: "0.6", strokeDasharray: "3 2" }),
        n > 1 && ind.boll && /* @__PURE__ */ React.createElement("path", { d: maPath("bb_mid"), fill: "none", stroke: "#5a93c8", strokeWidth: "0.9", opacity: "0.45", strokeDasharray: "2 3" }),
        n > 1 && ind.boll && /* @__PURE__ */ React.createElement("path", { d: maPath("bb_low"), fill: "none", stroke: "#5a93c8", strokeWidth: "1", opacity: "0.6", strokeDasharray: "3 2" }),
        view.map((b, i) => {
          const up = (b.c || 0) >= (b.o || 0);
          const color = up ? "var(--teal)" : "var(--red)";
          const cx = xCenter(i);
          const yHigh = yPrice(b.h || b.c || 0);
          const yLow = yPrice(b.l || b.c || 0);
          const yO = yPrice(b.o || b.c || 0);
          const yC = yPrice(b.c || 0);
          const top = Math.min(yO, yC);
          const bodyH = Math.max(1, Math.abs(yC - yO));
          return /* @__PURE__ */ React.createElement("g", { key: `k${i}`, opacity: hover === i ? 1 : 0.92 }, /* @__PURE__ */ React.createElement("line", { x1: cx, x2: cx, y1: yHigh, y2: yLow, stroke: color, strokeWidth: "1" }), /* @__PURE__ */ React.createElement("rect", { x: cx - candleW / 2, y: top, width: candleW, height: bodyH, fill: color }));
        }),
        view.map((b, i) => {
          const up = (b.c || 0) >= (b.o || 0);
          const y = yVol(b.vol || 0);
          return /* @__PURE__ */ React.createElement(
            "rect",
            {
              key: `v${i}`,
              x: xCenter(i) - candleW / 2,
              y,
              width: candleW,
              height: Math.max(0, volBot - y),
              fill: up ? "var(--teal)" : "var(--red)",
              opacity: "0.4"
            }
          );
        }),
        n > 1 && ind.volma && /* @__PURE__ */ React.createElement("path", { d: arrPath(volMa.vol_ma5, yVol), fill: "none", stroke: "#4cd6b3", strokeWidth: "0.9", opacity: "0.7" }),
        n > 1 && ind.volma && /* @__PURE__ */ React.createElement("path", { d: arrPath(volMa.vol_ma20, yVol), fill: "none", stroke: "#f0b35a", strokeWidth: "0.9", opacity: "0.6" }),
        /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: volTop + 8, textAnchor: "end", fill: "var(--ink-3)" }, "\uAC70\uB798\uB7C9"),
        ind.strength && /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: padL,
            x2: W - padR,
            y1: yStr(100),
            y2: yStr(100),
            stroke: "rgba(255,255,255,0.12)",
            strokeWidth: "1",
            strokeDasharray: "2 3"
          }
        ),
        n > 1 && ind.strength && /* @__PURE__ */ React.createElement("path", { d: strPath, fill: "none", stroke: "var(--violet)", strokeWidth: "1.3", opacity: "0.85" }),
        n > 1 && ind.strength && ind.strma && /* @__PURE__ */ React.createElement("path", { d: arrPath(strMa, yStr), fill: "none", stroke: "#f0b35a", strokeWidth: "1", opacity: "0.7", strokeDasharray: "3 2" }),
        ind.strength && /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: strTop + 8, textAnchor: "end", fill: "var(--violet)" }, "\uCCB4\uACB0\uAC15\uB3C4"),
        (signals || []).map((sig, si) => {
          const bi = nearestIdx(sig.buy_hms);
          const sj = nearestIdx(sig.sell_hms);
          const reached = curT != null && sig.sell_hms <= curT;
          const buyVisible = bi >= 0 && (curT == null || sig.buy_hms <= curT);
          const sellVisible = sj >= 0 && (curT == null || sig.sell_hms <= curT);
          return /* @__PURE__ */ React.createElement("g", { key: `s${si}` }, buyVisible && /* @__PURE__ */ React.createElement(
            "text",
            {
              x: xCenter(bi),
              y: yPrice(sig.buy_price) + 13,
              textAnchor: "middle",
              fontSize: compact ? 10 : 12,
              fill: "var(--teal)",
              opacity: reached ? 1 : 0.85
            },
            "\u25B2"
          ), sellVisible && /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement(
            "text",
            {
              x: xCenter(sj),
              y: yPrice(sig.sell_price) - 5,
              textAnchor: "middle",
              fontSize: compact ? 10 : 12,
              fill: "var(--red)",
              opacity: "1"
            },
            "\u25BC"
          ), !compact && /* @__PURE__ */ React.createElement(
            "text",
            {
              x: xCenter(sj),
              y: yPrice(sig.sell_price) - 16,
              textAnchor: "middle",
              fontSize: "9",
              className: "mono",
              fill: sig.profit_pct >= 0 ? "var(--teal)" : "var(--red)"
            },
            sig.profit_pct >= 0 ? "+" : "",
            (sig.profit_pct || 0).toFixed(1),
            "%"
          )));
        }),
        xTickIdx.map((i) => /* @__PURE__ */ React.createElement("text", { key: `x${i}`, className: "chart-axis-text", x: xCenter(i), y: H - 6, textAnchor: "middle" }, view[i] ? _simTimeLabel(view[i].t) : "")),
        hover != null && view[hover] && /* @__PURE__ */ React.createElement("g", null, /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: xCenter(hover),
            x2: xCenter(hover),
            y1: priceTop,
            y2: priceBot,
            stroke: "rgba(255,255,255,0.18)",
            strokeWidth: "1",
            strokeDasharray: "3 3"
          }
        ), /* @__PURE__ */ React.createElement(
          "line",
          {
            x1: padL,
            x2: W - padR,
            y1: yPrice(view[hover].c || 0),
            y2: yPrice(view[hover].c || 0),
            stroke: "rgba(255,255,255,0.12)",
            strokeWidth: "1",
            strokeDasharray: "3 3"
          }
        ))
      ), hover != null && view[hover] && /* @__PURE__ */ React.createElement("div", { style: {
        position: "absolute",
        top: 12,
        right: 12,
        background: "var(--bg-0)",
        border: "1px solid var(--line-2)",
        borderRadius: 6,
        padding: "8px 10px",
        fontFamily: "var(--mono)",
        fontSize: 11,
        minWidth: 150,
        boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
        pointerEvents: "none"
      } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", marginBottom: 4 } }, _simTimeLabel(view[hover].t)), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC885\uAC00"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, _simPriceTick(view[hover].c)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uB4F1\uB77D"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" }, className: view[hover].change >= 0 ? "num-pos" : "num-neg" }, (view[hover].change || 0).toFixed(2), "%"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uCCB4\uACB0\uAC15\uB3C4"), /* @__PURE__ */ React.createElement("span", { style: { textAlign: "right" } }, (view[hover].strength || 0).toFixed(0)))), n > 0 && (zoom > 0 || pan > 0) && /* @__PURE__ */ React.createElement(
        "button",
        {
          className: "btn ghost sm",
          onClick: () => {
            setZoom(0);
            setPan(0);
          },
          style: { position: "absolute", top: 10, left: 10, fontSize: 10, padding: "2px 7px" }
        },
        "\u2922 \uB9AC\uC14B"
      ), n === 0 && /* @__PURE__ */ React.createElement("div", { style: {
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "var(--ink-3)",
        fontSize: 12,
        fontFamily: "var(--mono)"
      } }, "\uC7AC\uC0DD\uC744 \uC2DC\uC791\uD558\uBA74 \uCE94\uB4E4\uC774 \uC2E4\uC2DC\uAC04\uC73C\uB85C \uCC44\uC6CC\uC9D1\uB2C8\uB2E4"))
    );
  }
  function SimImbalancePane({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const vals = useMemo_simc(() => view.map((b) => {
      if (b.imbalance != null && isFinite(b.imbalance)) return b.imbalance;
      const br = b.buy_rest != null && isFinite(b.buy_rest) ? b.buy_rest : null;
      const sr = b.sell_rest != null && isFinite(b.sell_rest) ? b.sell_rest : null;
      if (br != null && sr != null && sr > 0) return br / sr;
      return null;
    }), [view]);
    const hasData = useMemo_simc(() => vals.some((v) => v != null), [vals]);
    if (!hasData) return null;
    const n = view.length;
    const W = 880;
    const H = compact ? 30 : 40;
    const padL = 56, padR = 16, padT = 4, padB = 4;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const finite = vals.filter((v) => v != null && isFinite(v));
    const vMax = Math.max(2, ...finite);
    const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + innerW * i / (n - 1);
    const yAt = (v) => padT + innerH - Math.min(v, vMax) / vMax * innerH;
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = vals[i];
      if (v == null || !isFinite(v)) {
        started = false;
        continue;
      }
      d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
      started = true;
    }
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "\uD638\uAC00 \uBD88\uADE0\uD615(\uB808\uBCA81 \uCD1D\uC794\uB7C9\uBE44)"), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: yAt(1),
        y2: yAt(1),
        stroke: "rgba(255,255,255,0.14)",
        strokeWidth: "1",
        strokeDasharray: "2 3"
      }
    ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(1) + 3, textAnchor: "end", fill: "var(--ink-3)" }, "1.0"), n > 1 && /* @__PURE__ */ React.createElement("path", { d, fill: "none", stroke: "var(--teal)", strokeWidth: "1.2", opacity: "0.85" })));
  }
  function SimNetDeltaStrip({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const hasData = useMemo_simc(
      () => view.some((b) => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
      [view]
    );
    if (!hasData) return null;
    const n = view.length;
    const W = 880;
    const H = compact ? 28 : 38;
    const padL = 56, padR = 16;
    const innerW = W - padL - padR;
    const mid = H / 2;
    const half = mid - 3;
    const maxAbs = Math.max(1, ...view.map((b) => Math.abs(_simNq(b))));
    const slot = n > 0 ? innerW / n : innerW;
    const barW = Math.max(1, slot * 0.7);
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--teal)" } }, "net-delta(\uC21C\uB9E4\uC218\uC218\uB7C9)"), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: mid, y2: mid, stroke: "rgba(255,255,255,0.12)", strokeWidth: "1" }), view.map((b, i) => {
      const nq = _simNq(b);
      const h = Math.min(Math.abs(nq), maxAbs) / maxAbs * half;
      const x = padL + slot * i + (slot - barW) / 2;
      const y = nq >= 0 ? mid - h : mid;
      const color = nq > 0 ? "var(--teal)" : nq < 0 ? "var(--red)" : "var(--ink-3)";
      return /* @__PURE__ */ React.createElement(
        "rect",
        {
          key: i,
          x: x.toFixed(1),
          y: y.toFixed(1),
          width: barW.toFixed(1),
          height: Math.max(0.5, h).toFixed(1),
          fill: color,
          opacity: "0.7"
        }
      );
    })));
  }
  function SimRsiPane({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const rsiVals = useMemo_simc(
      () => typeof _simRsi === "function" ? _simRsi(view, 14) : [],
      [view]
    );
    const hasData = useMemo_simc(() => rsiVals.some((v) => v != null), [rsiVals]);
    if (!hasData) return null;
    const n = view.length;
    const W = 880;
    const H = compact ? 30 : 40;
    const padL = 56, padR = 16, padT = 4, padB = 4;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + innerW * i / (n - 1);
    const yAt = (v) => padT + innerH - Math.max(0, Math.min(100, v)) / 100 * innerH;
    let d = "", started = false;
    for (let i = 0; i < n; i++) {
      const v = rsiVals[i];
      if (v == null || !isFinite(v)) {
        started = false;
        continue;
      }
      d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
      started = true;
    }
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--teal)" } }, "RSI(14)"), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, [30, 50, 70].map((lv) => /* @__PURE__ */ React.createElement(
      "line",
      {
        key: lv,
        x1: padL,
        x2: W - padR,
        y1: yAt(lv),
        y2: yAt(lv),
        stroke: "rgba(255,255,255,0.10)",
        strokeWidth: "1",
        strokeDasharray: "2 3"
      }
    )), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(70) + 3, textAnchor: "end", fill: "var(--ink-3)" }, "70"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(30) + 3, textAnchor: "end", fill: "var(--ink-3)" }, "30"), n > 1 && /* @__PURE__ */ React.createElement("path", { d, fill: "none", stroke: "var(--teal)", strokeWidth: "1.2", opacity: "0.85" })));
  }
  function SimMacdPane({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const macdData = useMemo_simc(
      () => typeof _simMacd === "function" ? _simMacd(view) : { macd: [], signal: [], hist: [] },
      [view]
    );
    const hasData = useMemo_simc(
      () => (macdData.macd || []).some((v) => v != null),
      [macdData]
    );
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
    const xAt = (i) => n <= 1 ? padL + innerW / 2 : padL + innerW * i / (n - 1);
    const yAt = (v) => v == null || !isFinite(v) ? mid : mid - Math.max(-maxAbs, Math.min(maxAbs, v)) / maxAbs * half;
    const slot = n > 1 ? innerW / n : innerW;
    const barW = Math.max(1, slot * 0.55);
    const linePath = (vals) => {
      let d = "", started = false;
      for (let i = 0; i < n; i++) {
        const v = vals[i];
        if (v == null || !isFinite(v)) {
          started = false;
          continue;
        }
        d += `${started ? "L" : "M"} ${xAt(i).toFixed(1)} ${yAt(v).toFixed(1)} `;
        started = true;
      }
      return d;
    };
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--teal)" } }, "MACD(12,26,9)"), /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: mid, y2: mid, stroke: "rgba(255,255,255,0.12)", strokeWidth: "1" }), view.map((b, i) => {
      const v = hist[i];
      if (v == null || !isFinite(v)) return null;
      const bh = Math.abs(yAt(v) - mid);
      const x = xAt(i) - barW / 2;
      const y = v >= 0 ? mid - bh : mid;
      const color = v > 0 ? "var(--teal)" : "var(--red)";
      return /* @__PURE__ */ React.createElement(
        "rect",
        {
          key: i,
          x: x.toFixed(1),
          y: y.toFixed(1),
          width: barW.toFixed(1),
          height: Math.max(0.5, bh).toFixed(1),
          fill: color,
          opacity: "0.55"
        }
      );
    }), n > 1 && /* @__PURE__ */ React.createElement("path", { d: linePath(macdLine), fill: "none", stroke: "var(--teal)", strokeWidth: "1.1", opacity: "0.9" }), n > 1 && /* @__PURE__ */ React.createElement("path", { d: linePath(signalLine), fill: "none", stroke: "var(--amber)", strokeWidth: "1", opacity: "0.8", strokeDasharray: "3 2" })));
  }
  function SimChartShell({ code, name, lastBar, bars, signals, curT, compact, engine, indicators, children }) {
    const ind = indicators || _SIM_DEFAULT_INDICATORS;
    const seenRef = useRef_simc(/* @__PURE__ */ new Set());
    const [flash, setFlash] = useState_simc(null);
    useEffect_simc(() => {
      if (curT == null) seenRef.current = /* @__PURE__ */ new Set();
    }, [curT]);
    useEffect_simc(() => {
      if (curT == null) return;
      const seen = seenRef.current;
      let kind = null;
      (signals || []).forEach((sig) => {
        const bk = code + "@b@" + sig.buy_hms;
        if (sig.buy_hms != null && sig.buy_hms <= curT && !seen.has(bk)) {
          seen.add(bk);
          kind = "buy";
        }
        const sk = code + "@s@" + sig.sell_hms;
        if (sig.sell_hms != null && sig.sell_hms <= curT && !seen.has(sk)) {
          seen.add(sk);
          kind = "sell";
        }
      });
      if (kind) {
        setFlash(kind);
        const id = setTimeout(() => setFlash(null), 650);
        return () => clearTimeout(id);
      }
    }, [curT, signals, code]);
    const flashGlow = flash === "buy" ? "0 0 0 2px var(--teal), 0 0 16px 2px rgba(76,214,179,0.55)" : flash === "sell" ? "0 0 0 2px var(--red), 0 0 16px 2px rgba(255,93,108,0.55)" : "none";
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { minWidth: 0, boxShadow: flashGlow, transition: "box-shadow 0.45s ease-out" } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: compact ? 11 : 12.5 } }, code, name ? " \xB7 " + name : ""), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9, color: "var(--ink-3)", marginLeft: 6 } }, engine === "lwc" ? "LWC" : "SVG")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, alignItems: "center" } }, lastBar && /* @__PURE__ */ React.createElement(SimChangeGauge, { changePct: lastBar.change, size: compact ? 48 : 56 }), /* @__PURE__ */ React.createElement(SimSessionRing, { curT, size: compact ? 44 : 52 }), lastBar && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-1)" } }, _simPriceTick(lastBar.c)))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, children, engine !== "lwc" && ind.imbalance && /* @__PURE__ */ React.createElement(SimImbalancePane, { bars, compact }), engine !== "lwc" && ind.orderflow && /* @__PURE__ */ React.createElement(SimNetDeltaStrip, { bars, compact }), engine !== "lwc" && ind.rsi && /* @__PURE__ */ React.createElement(SimRsiPane, { bars, compact }), engine !== "lwc" && ind.macd && /* @__PURE__ */ React.createElement(SimMacdPane, { bars, compact }), /* @__PURE__ */ React.createElement(SimOrderBook, { lastBar, compact }), /* @__PURE__ */ React.createElement(SimOrderFlowTape, { bars, compact }), /* @__PURE__ */ React.createElement(SimFootprint, { bars, compact }), /* @__PURE__ */ React.createElement(SimHeatStrip, { bars, compact }), /* @__PURE__ */ React.createElement(SimRestFlow, { bars, compact })));
  }
  function SimCandleChart(props) {
    const useLwc = useMemo_simc(() => _lwcAvailable(), []);
    return useLwc ? /* @__PURE__ */ React.createElement(SimCandleChartLWC, { ...props }) : /* @__PURE__ */ React.createElement(SimCandleChartSVG, { ...props });
  }
  function SimOrderFlowTape({ bars, compact }) {
    const view = useMemo_simc(() => {
      const arr = bars || [];
      return arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
    }, [bars]);
    const hasData = useMemo_simc(
      () => view.some((b) => b.net_qty != null && isFinite(b.net_qty) && b.net_qty !== 0),
      [view]
    );
    if (!hasData) return null;
    const maxAbs = Math.max(1, ...view.map((b) => Math.abs(_simNq(b))));
    const H = compact ? 14 : 18;
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, marginTop: 6 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--teal)", flexShrink: 0, width: 48 } }, "\uC624\uB354\uD50C\uB85C\uC6B0"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flex: 1, height: H, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" } }, view.map((b, i) => {
      const nq = _simNq(b);
      const mag = Math.min(1, Math.abs(nq) / maxAbs);
      const a = (0.15 + mag * 0.75).toFixed(3);
      const bg = nq > 0 ? `rgba(76,214,179,${a})` : nq < 0 ? `rgba(255,93,108,${a})` : "rgba(150,158,170,0.12)";
      return /* @__PURE__ */ React.createElement(
        "div",
        {
          key: i,
          title: _simTimeLabel(b.t) + " \xB7 \uC21C\uB9E4\uC218 " + _simPriceTick(nq),
          style: { flex: 1, background: bg }
        }
      );
    })));
  }
  function _simNq(b) {
    return b && b.net_qty != null && isFinite(b.net_qty) ? b.net_qty : 0;
  }
  function _hoga_tick(price) {
    const p = Math.abs(Number(price) || 0);
    if (p < 2e3) return 1;
    if (p < 5e3) return 5;
    if (p < 2e4) return 10;
    if (p < 5e4) return 50;
    if (p < 2e5) return 100;
    if (p < 5e5) return 500;
    return 1e3;
  }
  function _bucketPrice(price, tick) {
    const t = tick || 1;
    return Math.round(Math.floor((Number(price) || 0) / t) * t);
  }
  function _barBuySell(bar) {
    const vol = bar.vol != null && isFinite(bar.vol) ? bar.vol : 0;
    const nq = bar.net_qty;
    if (nq != null && isFinite(nq)) {
      const buy = (vol + nq) / 2;
      const sell = (vol - nq) / 2;
      return { buy: Math.max(0, buy), sell: Math.max(0, sell), real: true };
    }
    const s = bar.strength != null && isFinite(bar.strength) ? bar.strength : 100;
    const buyShare = Math.max(0, Math.min(1, s / 200));
    return { buy: vol * buyShare, sell: vol * (1 - buyShare), real: false };
  }
  function SimFootprint({ bars, compact }) {
    const [open, setOpen] = useState_simc(false);
    const agg = useMemo_simc(() => {
      const arr = bars || [];
      const view = arr.length > _SIM_WINDOW ? arr.slice(arr.length - _SIM_WINDOW) : arr;
      if (view.length === 0) return { levels: [], real: true, curPrice: null, hasVol: false };
      const last = view[view.length - 1];
      const map = /* @__PURE__ */ new Map();
      let real = true;
      let hasVol = false;
      for (let i = 0; i < view.length; i++) {
        const b = view[i];
        const bs = _barBuySell(b);
        if (!bs.real) real = false;
        if (bs.buy + bs.sell > 0) hasVol = true;
        const key = _bucketPrice(b.c, _hoga_tick(b.c));
        const cur = map.get(key) || { buy: 0, sell: 0 };
        cur.buy += bs.buy;
        cur.sell += bs.sell;
        map.set(key, cur);
      }
      const levels = Array.from(map.entries()).map(([price, v]) => ({ price, buy: v.buy, sell: v.sell, delta: v.buy - v.sell })).sort((a, b) => b.price - a.price);
      return { levels, real, curPrice: _bucketPrice(last.c, _hoga_tick(last.c)), hasVol };
    }, [bars]);
    if (!agg.hasVol) return null;
    const maxSide = Math.max(1, ...agg.levels.map((l) => Math.max(l.buy, l.sell)));
    const rowH = compact ? 14 : 17;
    const barW = compact ? 80 : 110;
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setOpen((o) => !o),
        className: "mono",
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8,
          width: "100%",
          padding: "4px 8px",
          background: "transparent",
          border: "1px solid var(--line-1)",
          borderRadius: 5,
          color: "var(--ink-2)",
          cursor: "pointer",
          fontSize: 10
        }
      },
      /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, open ? "\u25BC" : "\u25B6"),
      "\uC624\uB354\uD50C\uB85C\uC6B0 footprint",
      /* @__PURE__ */ React.createElement("span", { style: { marginLeft: "auto", color: agg.real ? "var(--teal)" : "var(--amber)" } }, agg.real ? "\uC2E4\uB370\uC774\uD130" : "\uAC15\uB3C4 \uADFC\uC0AC")
    ), open && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 4, display: "flex", flexDirection: "column", gap: 1 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { display: "flex", alignItems: "center", fontSize: 8.5, color: "var(--ink-3)", padding: "0 2px" } }, /* @__PURE__ */ React.createElement("span", { style: { width: barW, textAlign: "left", color: "var(--red)" } }, "\uB9E4\uB3C4\uCCB4\uACB0"), /* @__PURE__ */ React.createElement("span", { style: { flex: 1, textAlign: "center" } }, "\uAC00\uACA9"), /* @__PURE__ */ React.createElement("span", { style: { width: barW, textAlign: "right", color: "var(--teal)" } }, "\uB9E4\uC218\uCCB4\uACB0"), /* @__PURE__ */ React.createElement("span", { style: { width: compact ? 44 : 56, textAlign: "right" } }, "\uB378\uD0C0")), agg.levels.map((lv) => {
      const isCur = lv.price === agg.curPrice;
      const sellW = lv.sell / maxSide * barW;
      const buyW = lv.buy / maxSide * barW;
      const sellInt = Math.min(1, lv.sell / maxSide);
      const buyInt = Math.min(1, lv.buy / maxSide);
      return /* @__PURE__ */ React.createElement(
        "div",
        {
          key: lv.price,
          className: "mono",
          style: {
            display: "flex",
            alignItems: "center",
            height: rowH,
            fontSize: 9.5,
            background: isCur ? "rgba(255,210,76,0.10)" : "transparent",
            borderRadius: 3,
            boxShadow: isCur ? "0 0 0 1px rgba(255,210,76,0.4) inset" : "none"
          }
        },
        /* @__PURE__ */ React.createElement("div", { style: { width: barW, display: "flex", justifyContent: "flex-end", alignItems: "center", gap: 4 } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", fontSize: 8.5 } }, lv.sell >= 1 ? _simPriceTick(lv.sell) : ""), /* @__PURE__ */ React.createElement("div", { style: { width: sellW, height: rowH - 5, background: `rgba(255,93,108,${(0.25 + sellInt * 0.6).toFixed(3)})`, borderRadius: 2 } })),
        /* @__PURE__ */ React.createElement("span", { style: { flex: 1, textAlign: "center", color: isCur ? "var(--amber)" : "var(--ink-1)", fontWeight: isCur ? 600 : 400 } }, _simPriceTick(lv.price)),
        /* @__PURE__ */ React.createElement("div", { style: { width: barW, display: "flex", justifyContent: "flex-start", alignItems: "center", gap: 4 } }, /* @__PURE__ */ React.createElement("div", { style: { width: buyW, height: rowH - 5, background: `rgba(76,214,179,${(0.25 + buyInt * 0.6).toFixed(3)})`, borderRadius: 2 } }), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", fontSize: 8.5 } }, lv.buy >= 1 ? _simPriceTick(lv.buy) : "")),
        /* @__PURE__ */ React.createElement("span", { style: { width: compact ? 44 : 56, textAlign: "right", color: lv.delta >= 0 ? "var(--teal)" : "var(--red)" } }, lv.delta >= 0 ? "+" : "", _simPriceTick(lv.delta))
      );
    }), !agg.real && /* @__PURE__ */ React.createElement("div", { style: { fontSize: 8.5, color: "var(--ink-3)", marginTop: 3, lineHeight: 1.4 } }, "\uC21C\uB9E4\uC218\uC218\uB7C9(net_qty) \uBD80\uC7AC\uB85C \uCCB4\uACB0\uAC15\uB3C4 \uAE30\uBC18 \uADFC\uC0AC \uBD84\uB9AC\uB2E4(\uC2E4 \uB9E4\uC218/\uB9E4\uB3C4 \uCCB4\uACB0\uB7C9 \uC544\uB2D8).")));
  }
  function SimOrderBook({ lastBar, compact }) {
    const prevRef = useRef_simc({ bid1: null, ask1: null });
    const [flash, setFlash] = useState_simc({ bid: false, ask: false });
    const bid1 = lastBar && lastBar.bid1 != null && isFinite(lastBar.bid1) ? lastBar.bid1 : null;
    const ask1 = lastBar && lastBar.ask1 != null && isFinite(lastBar.ask1) ? lastBar.ask1 : null;
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
    const buyRest = lastBar.buy_rest != null && isFinite(lastBar.buy_rest) ? lastBar.buy_rest : null;
    const sellRest = lastBar.sell_rest != null && isFinite(lastBar.sell_rest) ? lastBar.sell_rest : null;
    if (bid1 == null && ask1 == null && buyRest == null && sellRest == null) return null;
    const cur = lastBar.c != null && isFinite(lastBar.c) ? lastBar.c : null;
    const strength = lastBar.strength != null && isFinite(lastBar.strength) ? lastBar.strength : null;
    const maxRest = Math.max(1, buyRest || 0, sellRest || 0);
    const askW = sellRest != null ? sellRest / maxRest * 100 : 0;
    const bidW = buyRest != null ? buyRest / maxRest * 100 : 0;
    const spread = bid1 != null && ask1 != null ? ask1 - bid1 : null;
    const mid = bid1 != null && ask1 != null ? (ask1 + bid1) / 2 : null;
    const spreadBps = spread != null && mid && mid > 0 ? spread / mid * 1e4 : null;
    const totRest = (buyRest || 0) + (sellRest || 0);
    const buyShare = totRest > 0 ? (buyRest || 0) / totRest * 100 : null;
    const sellShare = totRest > 0 ? (sellRest || 0) / totRest * 100 : null;
    const stColor = strength == null ? "var(--ink-2)" : strength >= 100 ? "var(--teal)" : "var(--red)";
    const rowH = compact ? 20 : 24;
    const askBg = flash.ask ? "rgba(56,140,255,0.22)" : "rgba(56,140,255,0.06)";
    const bidBg = flash.bid ? "rgba(255,93,108,0.22)" : "rgba(255,93,108,0.06)";
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3, gap: 6 } }, /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono",
        style: { fontSize: 9.5, color: "var(--ink-3)" },
        title: "\uC77C\uC77C DB\uB294 \uCD5C\uC6B0\uC120\uD638\uAC00\xB7\uCD1D\uC794\uB7C9\uB9CC \uC81C\uACF5(\uB808\uBCA82~10 \uC5C6\uC74C)"
      },
      "\uD638\uAC00\uCC3D (\uB808\uBCA81 + \uCD1D\uC794\uB7C9)"
    ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 6 } }, spread != null && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-2)" } }, "\uC2A4\uD504\uB808\uB4DC ", _simPriceTick(spread), spreadBps != null ? ` (${spreadBps.toFixed(1)}bp)` : ""), strength != null && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: stColor, padding: "1px 6px", borderRadius: 3, border: "1px solid " + (strength >= 100 ? "var(--teal-dim)" : "var(--line-1)") } }, "\uCCB4\uACB0\uAC15\uB3C4 ", strength.toFixed(0)))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", height: rowH, background: askBg, borderRadius: 3, marginBottom: 1, transition: "background 0.28s ease-out" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#5aa0ff", paddingRight: 8 } }, ask1 != null ? _simPriceTick(ask1) : "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, height: rowH - 8, position: "relative", display: "flex", justifyContent: "flex-start" } }, /* @__PURE__ */ React.createElement("div", { style: { width: askW + "%", height: "100%", background: "rgba(56,140,255,0.30)", borderRadius: 2, transition: "width 0.2s ease-out" } })), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#5aa0ff", paddingRight: 4 } }, sellRest != null ? _simPriceTick(sellRest) : "\u2014")), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { textAlign: "center", fontSize: 11, color: "var(--amber)", padding: "2px 0", letterSpacing: ".04em" } }, "\u25B8 ", cur != null ? _simPriceTick(cur) : "\u2014", " \u25C2"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", height: rowH, background: bidBg, borderRadius: 3, marginTop: 1, transition: "background 0.28s ease-out" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { width: compact ? 66 : 80, textAlign: "right", fontSize: 10.5, color: "#ff8088", paddingRight: 8 } }, bid1 != null ? _simPriceTick(bid1) : "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, height: rowH - 8, display: "flex", justifyContent: "flex-start" } }, /* @__PURE__ */ React.createElement("div", { style: { width: bidW + "%", height: "100%", background: "rgba(255,93,108,0.28)", borderRadius: 2, transition: "width 0.2s ease-out" } })), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { width: compact ? 60 : 74, textAlign: "right", fontSize: 9.5, color: "#ff8088", paddingRight: 4 } }, buyRest != null ? _simPriceTick(buyRest) : "\u2014")), buyShare != null && sellShare != null && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 5 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", height: 6, borderRadius: 3, overflow: "hidden", border: "1px solid var(--line-1)" } }, /* @__PURE__ */ React.createElement("div", { style: { width: buyShare.toFixed(1) + "%", background: "var(--teal)", opacity: 0.7, transition: "width 0.25s ease-out" } }), /* @__PURE__ */ React.createElement("div", { style: { width: sellShare.toFixed(1) + "%", background: "var(--red)", opacity: 0.7, transition: "width 0.25s ease-out" } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: 2, fontSize: 9 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--teal)" } }, "\uB9E4\uC218 ", buyShare.toFixed(0), "%"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--red)" } }, "\uB9E4\uB3C4 ", sellShare.toFixed(0), "%"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: 4, fontSize: 9.5 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "#5aa0ff" } }, "\uCD1D\uB9E4\uB3C4 ", sellRest != null ? _simPriceTick(sellRest) : "\u2014"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "#ff8088" } }, "\uCD1D\uB9E4\uC218 ", buyRest != null ? _simPriceTick(buyRest) : "\u2014")));
  }
  var _SIM_OVERLAY_COLORS = ["#4cd6b3", "#ff5d6c", "#f0b35a", "#7c6cf0"];
  function SimOverlayChart({ codes, barsByCode, nameByCode, curT }) {
    const series = useMemo_simc(() => {
      return (codes || []).map((code, idx) => {
        const arr = barsByCode[code] || [];
        const base = arr.length ? arr[0].c || 0 : 0;
        const pts = base > 0 ? arr.map((b) => ({ t: b.t, v: b.c / base * 100 })) : [];
        return { code, name: nameByCode[code] || code, color: _SIM_OVERLAY_COLORS[idx % 4], pts };
      });
    }, [codes.join(","), barsByCode]);
    const allVals = [];
    series.forEach((s) => s.pts.forEach((p) => allVals.push(p.v)));
    const hasData = allVals.length > 0;
    const W = 880, H = 360, padL = 48, padR = 16, padT = 16, padB = 26;
    const innerW = W - padL - padR, innerH = H - padT - padB;
    const vMax = hasData ? Math.max(100.5, ...allVals) : 105;
    const vMin = hasData ? Math.min(99.5, ...allVals) : 95;
    const vRange = vMax - vMin || 1;
    const allT = useMemo_simc(() => {
      const set = /* @__PURE__ */ new Set();
      series.forEach((s) => s.pts.forEach((p) => set.add(p.t)));
      return Array.from(set).sort((a, b) => a - b);
    }, [series]);
    const tIdx = useMemo_simc(() => {
      const m = /* @__PURE__ */ new Map();
      allT.forEach((t, i) => m.set(t, i));
      return m;
    }, [allT]);
    const nT = allT.length;
    const xAt = (t) => {
      const i = tIdx.has(t) ? tIdx.get(t) : 0;
      return nT <= 1 ? padL + innerW / 2 : padL + innerW * i / (nT - 1);
    };
    const yAt = (v) => padT + innerH - (v - vMin) / vRange * innerH;
    const linePath = (pts) => {
      if (pts.length < 2) return "";
      return pts.map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(p.t).toFixed(1)} ${yAt(p.v).toFixed(1)}`).join(" ");
    };
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { minWidth: 0 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 12.5 } }, "\uC815\uADDC\uD654 \uC624\uBC84\uB808\uC774 (\uC2DC\uC791=100)")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 10, flexWrap: "wrap" } }, series.map((s) => {
      const last = s.pts.length ? s.pts[s.pts.length - 1].v : 100;
      return /* @__PURE__ */ React.createElement("span", { key: s.code, className: "mono", style: { fontSize: 10, color: s.color, display: "flex", alignItems: "center", gap: 4 } }, /* @__PURE__ */ React.createElement("span", { style: { width: 9, height: 2, background: s.color, display: "inline-block" } }), s.name, " ", /* @__PURE__ */ React.createElement("span", { style: { color: last >= 100 ? "var(--teal)" : "var(--red)" } }, last.toFixed(1)));
    }))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "chart-wrap" }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: "none", style: { width: "100%", height: H } }, /* @__PURE__ */ React.createElement(
      "line",
      {
        x1: padL,
        x2: W - padR,
        y1: yAt(100),
        y2: yAt(100),
        stroke: "rgba(255,255,255,0.15)",
        strokeWidth: "1",
        strokeDasharray: "3 3"
      }
    ), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(100) + 3, textAnchor: "end", fill: "var(--ink-3)" }, "100"), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(vMax) + 8, textAnchor: "end", fill: "var(--ink-2)" }, vMax.toFixed(1)), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 6, y: yAt(vMin), textAnchor: "end", fill: "var(--ink-2)" }, vMin.toFixed(1)), series.map((s) => s.pts.length > 1 && /* @__PURE__ */ React.createElement("path", { key: s.code, d: linePath(s.pts), fill: "none", stroke: s.color, strokeWidth: "1.5", opacity: "0.9" })), nT > 0 && [0, Math.floor(nT / 2), nT - 1].map((i, k) => /* @__PURE__ */ React.createElement("text", { key: k, className: "chart-axis-text", x: xAt(allT[i]), y: H - 8, textAnchor: "middle" }, allT[i] != null ? _simTimeLabel(allT[i]) : "")), !hasData && /* @__PURE__ */ React.createElement("text", { x: W / 2, y: H / 2, textAnchor: "middle", fill: "var(--ink-3)", fontSize: "12", className: "mono" }, "\uC7AC\uC0DD\uC744 \uC2DC\uC791\uD558\uBA74 \uC815\uADDC\uD654 \uBE44\uAD50\uC120\uC774 \uCC44\uC6CC\uC9D1\uB2C8\uB2E4")))));
  }
  function _simCsvCell(v) {
    let s = v == null ? "" : String(v);
    if (/^[=+\-@]/.test(s)) s = "'" + s;
    return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function _simCsvTime(full, hms) {
    if (full != null && full !== "") {
      const s = String(full).padStart(14, "0");
      return s.slice(8, 10) + ":" + s.slice(10, 12) + ":" + s.slice(12, 14);
    }
    return _simTimeLabel(hms);
  }
  function _simSignalLogCsv(rows) {
    const list = rows || [];
    const hasCode = list.some((r) => r && (r.code != null && r.code !== ""));
    const header = (hasCode ? ["\uC885\uBAA9\uCF54\uB4DC"] : []).concat(["\uB9E4\uC218\uC2DC\uAC04", "\uB9E4\uB3C4\uC2DC\uAC04", "\uB9E4\uC218\uAC00", "\uB9E4\uB3C4\uAC00", "\uC218\uC775\uB960(%)"]);
    const lines = [header.map(_simCsvCell).join(",")];
    for (let i = 0; i < list.length; i++) {
      const r = list[i] || {};
      const cells = hasCode ? [r.code != null ? r.code : ""] : [];
      cells.push(_simCsvTime(r.buy_time, r.buy_hms));
      cells.push(_simCsvTime(r.sell_time, r.sell_hms));
      cells.push(r.buy_price != null ? Math.round(r.buy_price) : "");
      cells.push(r.sell_price != null ? Math.round(r.sell_price) : "");
      cells.push((r.profit_pct || 0).toFixed(2));
      lines.push(cells.map(_simCsvCell).join(","));
    }
    return "\uFEFF" + lines.join("\r\n");
  }
  function _simDownloadSignalLogCsv(rows) {
    const csv = _simSignalLogCsv(rows);
    const d = /* @__PURE__ */ new Date();
    const ymd = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
    const fname = "\uCCB4\uACB0\uB85C\uADF8_" + ymd + ".csv";
    try {
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => {
        try {
          URL.revokeObjectURL(url);
        } catch (e) {
        }
      }, 0);
    } catch (e) {
    }
  }
  function SimSignalLog({ signals, curT }) {
    const rows = signals || [];
    return /* @__PURE__ */ React.createElement("div", { className: "panel", style: { display: "flex", flexDirection: "column", minHeight: 0 } }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uCCB4\uACB0 \uB85C\uADF8"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, rows.length, "\uAC74 \xB7 \uC5D4\uC9C4 \uC2E0\uD638"), rows.length > 0 && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        style: { fontSize: 10, padding: "2px 8px" },
        onClick: () => _simDownloadSignalLogCsv(rows),
        title: "\uCCB4\uACB0 \uB85C\uADF8\uB97C CSV \uD30C\uC77C\uB85C \uB0B4\uBCF4\uB0C5\uB2C8\uB2E4"
      },
      "CSV \uB0B4\uBCF4\uB0B4\uAE30"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { maxHeight: 420, overflowY: "auto", padding: "8px 10px" } }, rows.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC870\uAC74\uC2DD\uC744 \uC120\uD0DD\uD558\uBA74 \uB9E4\uB9E4 \uC2E0\uD638\uAC00 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2 } }, rows.map((s, i) => {
      const reached = curT != null && s.sell_hms <= curT;
      const buying = curT != null && s.buy_hms <= curT && s.sell_hms > curT;
      return /* @__PURE__ */ React.createElement("div", { key: i, style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "5px 7px",
        borderRadius: 5,
        border: "1px solid " + (buying ? "var(--amber)" : reached ? "var(--line-1)" : "var(--line-1)"),
        background: buying ? "rgba(240,179,90,0.10)" : reached ? "var(--bg-0)" : "transparent",
        opacity: reached || buying ? 1 : 0.5
      } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--teal)", flexShrink: 0 } }, "\u25B2", _simTimeLabel(s.buy_hms)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--red)", flexShrink: 0 } }, "\u25BC", _simTimeLabel(s.sell_hms)), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", flex: 1, textAlign: "right", whiteSpace: "nowrap" } }, _simPriceTick(s.buy_price), "\u2192", _simPriceTick(s.sell_price)), /* @__PURE__ */ React.createElement(
        "span",
        {
          className: "mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg"),
          style: { fontSize: 11, flexShrink: 0, width: 52, textAlign: "right" }
        },
        s.profit_pct >= 0 ? "+" : "",
        (s.profit_pct || 0).toFixed(1),
        "%"
      ));
    }))));
  }
  Object.assign(window, {
    SimCandleChart,
    SimCandleChartLWC,
    SimCandleChartSVG,
    SimHeatStrip,
    SimRestFlow,
    SimSignalLog,
    SimChangeGauge,
    SimSessionRing,
    SimOrderFlowTape,
    SimFootprint,
    SimOrderBook,
    SimOverlayChart,
    SimImbalancePane,
    SimNetDeltaStrip,
    SimRsiPane,
    SimMacdPane,
    _simTimeLabel,
    _simPriceTick,
    _strengthColor,
    _sessionProgress,
    _changeColor,
    _simSma,
    _simEma,
    _simRsi,
    _simMacd,
    _simVolMa,
    _simStrengthMa,
    _SIM_DEFAULT_INDICATORS
  });

  // ../frontend/simulation.jsx
  var {
    useState: useState_sim,
    useEffect: useEffect_sim,
    useCallback: useCallback_sim,
    useRef: useRef_sim,
    useMemo: useMemo_sim
  } = React;
  function _simFetchJson(url, timeoutMs) {
    return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 6e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  var _SIM_SPEEDS = [1, 5, 20, 60, 240, 600];
  var _simWsBar = (it, t) => ({
    t,
    o: it.o,
    h: it.h,
    l: it.l,
    c: it.c,
    vol: it.vol,
    change: it.change,
    strength: it.strength,
    ma5: it.ma5,
    ma20: it.ma20,
    ma60: it.ma60,
    imbalance: it.imbalance,
    buy_rest: it.buy_rest,
    sell_rest: it.sell_rest,
    vwap: it.vwap,
    vwap_up: it.vwap_up,
    vwap_low: it.vwap_low,
    bb_mid: it.bb_mid,
    bb_up: it.bb_up,
    bb_low: it.bb_low,
    net_qty: it.net_qty,
    bid1: it.bid1,
    ask1: it.ask1
  });
  var _SIM_MAX_CODES = 10;
  var _SIM_DEMO_SPEED = 20;
  var _SIM_ENGINE_MODES = [["live", "\uB77C\uC774\uBE0C"], ["lwc", "LWC"], ["svg", "SVG"]];
  var _SIM_ENGINE_LS_KEY = "stom.sim.engine.v1";
  var _SIM_CHART_MODES = [["split", "\uBD84\uD560"], ["overlay", "\uC624\uBC84\uB808\uC774"]];
  var _SIM_SPLIT_LS_KEY = "stom.sim.split.v1";
  var _SIM_ROWS_LS_KEY = "stom.sim.rows.v1";
  var _SIM_MAX_SPLIT_COLS = 5;
  var _SIM_IND_LS_KEY = "stom.sim.indicators.v1";
  var _SIM_DEMO_LS_KEY = "stom.sim.demoSeen.v1";
  function _simDemoSeen() {
    try {
      return window.localStorage.getItem(_SIM_DEMO_LS_KEY) === "1";
    } catch (e) {
      return false;
    }
  }
  function _simMarkDemoSeen() {
    try {
      window.localStorage.setItem(_SIM_DEMO_LS_KEY, "1");
    } catch (e) {
    }
  }
  function _loadIndicators() {
    const def = window._SIM_DEFAULT_INDICATORS || { ma: true, vwap: true, boll: false };
    try {
      const raw = window.localStorage.getItem(_SIM_IND_LS_KEY);
      const obj = raw ? JSON.parse(raw) : null;
      if (obj && typeof obj === "object") return { ...def, ...obj };
    } catch (e) {
    }
    return { ...def };
  }
  function _saveIndicators(obj) {
    try {
      window.localStorage.setItem(_SIM_IND_LS_KEY, JSON.stringify(obj || {}));
    } catch (e) {
    }
  }
  function _loadSplitCols() {
    try {
      const v = parseInt(window.localStorage.getItem(_SIM_SPLIT_LS_KEY), 10);
      if (v >= 1 && v <= _SIM_MAX_SPLIT_COLS) return v;
      return 2;
    } catch (e) {
      return 2;
    }
  }
  function _saveSplitCols(v) {
    try {
      window.localStorage.setItem(_SIM_SPLIT_LS_KEY, String(v));
    } catch (e) {
    }
  }
  function _loadSplitRows() {
    try {
      const v = parseInt(window.localStorage.getItem(_SIM_ROWS_LS_KEY), 10);
      if (v >= 1 && v <= _SIM_MAX_CODES) return v;
      return 0;
    } catch (e) {
      return 0;
    }
  }
  function _saveSplitRows(v) {
    try {
      window.localStorage.setItem(_SIM_ROWS_LS_KEY, String(v));
    } catch (e) {
    }
  }
  function _loadEngineMode() {
    try {
      const v = window.localStorage.getItem(_SIM_ENGINE_LS_KEY);
      return v === "lwc" || v === "svg" || v === "live" ? v : "live";
    } catch (e) {
      return "live";
    }
  }
  function _saveEngineMode(v) {
    try {
      window.localStorage.setItem(_SIM_ENGINE_LS_KEY, String(v));
    } catch (e) {
    }
  }
  function _wsUrl(baseUrl, path) {
    try {
      const u = new URL(baseUrl);
      u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
      u.pathname = u.pathname.replace(/\/$/, "") + path;
      return u.toString();
    } catch (e) {
      return null;
    }
  }
  function SimControlBar({
    baseUrl,
    isDemo,
    src,
    onSrc,
    date,
    onDate,
    days,
    stocks,
    selected,
    onToggleStock,
    stockQuery,
    onStockQuery,
    buy,
    onBuy,
    sell,
    onSell,
    strategies,
    aggSec,
    onAggSec,
    loadingStocks
  }) {
    const filteredStocks = useMemo_sim(() => {
      const q = (stockQuery || "").trim().toLowerCase();
      if (!q) return stocks;
      return stocks.filter((s) => (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
    }, [stocks, stockQuery]);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uB9AC\uD50C\uB808\uC774 \uC124\uC815")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 12 } }, /* @__PURE__ */ React.createElement("div", { className: "field-row" }, /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uC2DC\uAC04\uB2E8\uC704"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, [["tick", "\uD2F1"], ["min", "\uBD84\uBD09"]].map(([k, lbl]) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: k,
        onClick: () => onSrc(k),
        className: "mono",
        disabled: isDemo,
        style: {
          flex: 1,
          padding: "5px 8px",
          fontSize: 11,
          borderRadius: 5,
          border: "1px solid " + (src === k ? "var(--teal-dim)" : "var(--line-1)"),
          background: src === k ? "rgba(76,214,179,0.08)" : "transparent",
          color: src === k ? "var(--teal)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      lbl
    )))), /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uB0A0\uC9DC (", days.length, "\uC77C)"), /* @__PURE__ */ React.createElement("select", { className: "select", value: date || "", onChange: (e) => onDate(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 \uC120\uD0DD \u2014"), days.map((d) => /* @__PURE__ */ React.createElement("option", { key: d, value: d }, _simFmtDate(d))))), src === "tick" && /* @__PURE__ */ React.createElement("div", { className: "field", style: { maxWidth: 110 } }, /* @__PURE__ */ React.createElement("label", null, "\uC9D1\uACC4(\uCD08)"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "number",
        min: "1",
        max: "60",
        value: aggSec,
        onChange: (e) => onAggSec(e.target.value),
        disabled: isDemo
      }
    ))), /* @__PURE__ */ React.createElement("div", { className: "field-row" }, /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uC218 \uC870\uAC74\uC2DD (\uC2E0\uD638 \uC624\uBC84\uB808\uC774)"), /* @__PURE__ */ React.createElement("select", { className: "select", value: buy, onChange: (e) => onBuy(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 \uC5C6\uC74C \u2014"), strategies.buy.map((n) => /* @__PURE__ */ React.createElement("option", { key: n, value: n }, n)))), /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uB9E4\uB3C4 \uC870\uAC74\uC2DD"), /* @__PURE__ */ React.createElement("select", { className: "select", value: sell, onChange: (e) => onSell(e.target.value), disabled: isDemo }, /* @__PURE__ */ React.createElement("option", { value: "" }, "\u2014 \uC5C6\uC74C \u2014"), strategies.sell.map((n) => /* @__PURE__ */ React.createElement("option", { key: n, value: n }, n))))), /* @__PURE__ */ React.createElement("div", { className: "field" }, /* @__PURE__ */ React.createElement("label", null, "\uC885\uBAA9 \uC120\uD0DD (\uCD5C\uB300 ", _SIM_MAX_CODES, " \xB7 \uB4F1\uB77D\uC21C)", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-3)", marginLeft: 8 } }, selected.length, "/", _SIM_MAX_CODES, " \uC120\uD0DD")), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        placeholder: "\uCF54\uB4DC/\uC774\uB984 \uAC80\uC0C9\u2026",
        value: stockQuery,
        onChange: (e) => onStockQuery(e.target.value),
        spellCheck: false,
        disabled: isDemo || !date,
        style: { marginBottom: 6 }
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 2, maxHeight: 220, overflowY: "auto" } }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC885\uBAA9 \uBAA9\uB85D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : !date ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB0A0\uC9DC\uB97C \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.") : loadingStocks ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC885\uBAA9 \uB85C\uB529 \uC911\u2026") : filteredStocks.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, stockQuery ? "\uAC80\uC0C9 \uACB0\uACFC \uC5C6\uC74C" : "\uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4") : filteredStocks.map((s) => {
      const active = selected.includes(s.code);
      const disabled = !active && selected.length >= _SIM_MAX_CODES;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: s.code,
          onClick: () => onToggleStock(s.code),
          disabled,
          style: {
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "5px 8px",
            borderRadius: 5,
            border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
            background: active ? "rgba(76,214,179,0.08)" : "var(--bg-0)",
            cursor: disabled ? "not-allowed" : "pointer",
            opacity: disabled ? 0.4 : 1,
            textAlign: "left"
          }
        },
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: active ? "var(--teal)" : "var(--ink-1)", flexShrink: 0, width: 56 } }, s.code),
        /* @__PURE__ */ React.createElement("span", { style: { fontSize: 11.5, color: "var(--ink-1)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" } }, s.name),
        /* @__PURE__ */ React.createElement(
          "span",
          {
            className: "mono " + (s.last_change_pct > 0 ? "num-pos" : s.last_change_pct < 0 ? "num-neg" : ""),
            style: { fontSize: 10.5, flexShrink: 0, width: 56, textAlign: "right" }
          },
          s.last_change_pct > 0 ? "+" : "",
          (s.last_change_pct || 0).toFixed(2),
          "%"
        )
      );
    })))));
  }
  function _simFmtDate(d) {
    const s = String(d);
    if (s.length === 8) return s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
    return s;
  }
  function SimPresetBar({ isDemo, busy, onPreset }) {
    if (isDemo) return null;
    const presets = [
      { mode: "latest", label: "\uCD5C\uADFC \uAC70\uB798\uC77C", hint: "\uB9C8\uC9C0\uB9C9 \uAC70\uB798\uC77C\xB7\uB4F1\uB77D 1\uC704" },
      { mode: "top_gainer", label: "\uCD5C\uB300 \uC0C1\uC2B9\uC77C", hint: "\uCD5C\uADFC \uC911 \uB4F1\uB77D \uCD5C\uB300\uC77C" }
    ];
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "8px 10px" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginRight: 2 } }, "\uBE60\uB978 \uC2DC\uC791"), presets.map((p) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: p.mode,
        className: "btn sm",
        onClick: () => onPreset(p.mode),
        disabled: busy,
        title: p.hint,
        style: { fontSize: 11, padding: "4px 10px", opacity: busy ? 0.5 : 1 }
      },
      "\u26A1 ",
      p.label
    )), busy && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uCD94\uCC9C \uC870\uD68C \uC911\u2026")));
  }
  function _simTileColor(pct) {
    const v = Number(pct) || 0;
    const mag = Math.min(1, Math.abs(v) / 12);
    const a = 0.12 + mag * 0.7;
    if (v > 0) return `rgba(255,93,108,${a.toFixed(3)})`;
    if (v < 0) return `rgba(56,140,255,${a.toFixed(3)})`;
    return "rgba(150,158,170,0.14)";
  }
  function SimMarketMinimap({ stocks, selected, onToggleStock, query, isDemo, date, loading }) {
    const tiles = useMemo_sim(() => {
      const q = (query || "").trim().toLowerCase();
      const base = stocks || [];
      if (!q) return base;
      return base.filter((s) => (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
    }, [stocks, query]);
    let body;
    if (isDemo) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB370\uBAA8 \uBAA8\uB4DC \u2014 \uBC31\uC5D4\uB4DC \uC5F0\uACB0 \uC2DC \uC2DC\uC7A5 \uBBF8\uB2C8\uB9F5\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.");
    } else if (!date) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB0A0\uC9DC\uB97C \uBA3C\uC800 \uC120\uD0DD\uD558\uC138\uC694.");
    } else if (loading) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBBF8\uB2C8\uB9F5 \uB85C\uB529 \uC911\u2026");
    } else if (tiles.length === 0) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, query ? "\uAC80\uC0C9 \uACB0\uACFC \uC5C6\uC74C" : "\uC885\uBAA9\uC774 \uC5C6\uC2B5\uB2C8\uB2E4");
    } else {
      body = /* @__PURE__ */ React.createElement("div", { style: {
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(74px, 1fr))",
        gap: 4,
        maxHeight: 240,
        overflowY: "auto"
      } }, tiles.map((s) => {
        const active = selected.includes(s.code);
        const atCap = !active && selected.length >= _SIM_MAX_CODES;
        const pct = Number(s.last_change_pct) || 0;
        return /* @__PURE__ */ React.createElement(
          "button",
          {
            key: s.code,
            onClick: () => onToggleStock(s.code),
            disabled: atCap,
            title: s.code + " \xB7 " + (s.name || "") + " \xB7 " + (pct > 0 ? "+" : "") + pct.toFixed(2) + "%",
            style: {
              display: "flex",
              flexDirection: "column",
              gap: 1,
              padding: "5px 6px",
              borderRadius: 5,
              textAlign: "left",
              overflow: "hidden",
              border: "1.5px solid " + (active ? "var(--teal)" : "transparent"),
              background: _simTileColor(pct),
              cursor: atCap ? "not-allowed" : "pointer",
              opacity: atCap ? 0.45 : 1,
              boxShadow: active ? "0 0 0 1px var(--teal-dim) inset" : "none"
            }
          },
          /* @__PURE__ */ React.createElement("span", { style: {
            fontSize: 10.5,
            color: "var(--ink-1)",
            fontWeight: active ? 600 : 400,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap"
          } }, s.name || s.code),
          /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: pct >= 0 ? "#ffd2d6" : "#cfe0ff" } }, pct > 0 ? "+" : "", pct.toFixed(2), "%")
        );
      }));
    }
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--red)" } }), "\uC2DC\uC7A5 \uBBF8\uB2C8\uB9F5"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, selected.length, "/", _SIM_MAX_CODES, " \uC120\uD0DD \xB7 \uB4F1\uB77D\uC21C")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: "8px 10px" } }, body));
  }
  function SimPlaybackBar({
    status,
    onPlay,
    onPause,
    onResume,
    onStop,
    speed,
    onSpeed,
    cursor,
    total,
    curT,
    sessionRange,
    onSeek,
    canPlay
  }) {
    const playing = status === "playing";
    const paused = status === "paused";
    const pct = total > 0 ? Math.round(cursor / total * 100) : 0;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" } }, !playing && !paused && /* @__PURE__ */ React.createElement("button", { className: "btn primary", onClick: onPlay, disabled: !canPlay }, "\u25B6 \uC7AC\uC0DD"), playing && /* @__PURE__ */ React.createElement("button", { className: "btn", onClick: onPause }, "\u23F8 \uC77C\uC2DC\uC815\uC9C0"), paused && /* @__PURE__ */ React.createElement("button", { className: "btn primary", onClick: onResume }, "\u25B6 \uC7AC\uAC1C"), (playing || paused) && /* @__PURE__ */ React.createElement("button", { className: "btn danger", onClick: onStop }, "\u23F9 \uC815\uC9C0"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 3, marginLeft: 8 } }, _SIM_SPEEDS.map((sp) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: sp,
        onClick: () => onSpeed(sp),
        className: "mono",
        style: {
          padding: "4px 8px",
          fontSize: 10.5,
          borderRadius: 4,
          border: "1px solid " + (speed === sp ? "var(--teal-dim)" : "var(--line-1)"),
          background: speed === sp ? "rgba(76,214,179,0.08)" : "transparent",
          color: speed === sp ? "var(--teal)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      sp === 600 ? "\uCD08\uACE0\uC18D" : sp + "x"
    ))), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono",
        style: { fontSize: 9.5, color: "var(--ink-3)", marginLeft: 6 },
        title: "1x = \uC2E4\uC2DC\uAC04(1\uCD08\uBD09 1\uCD08/1\uBD84\uBD09 1\uBD84). \uBC30\uC18D\uB9CC\uD07C \uBE60\uB974\uAC8C \uD750\uB985\uB2C8\uB2E4."
      },
      "\u23F1 ",
      speed === 1 ? "\uC2E4\uC2DC\uAC04" : speed + "x",
      " \uD398\uC774\uC2F1"
    ), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 13, color: "var(--teal)", marginLeft: "auto", letterSpacing: ".04em" } }, curT != null ? window._simTimeLabel(curT) : "--:--:--", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)", fontSize: 11 } }, " \xB7 ", cursor, "/", total))), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "range",
        min: "0",
        max: Math.max(0, total - 1),
        value: cursor,
        disabled: !total,
        onChange: (e) => onSeek(parseInt(e.target.value, 10)),
        style: { width: "100%", accentColor: "var(--teal)", cursor: total ? "pointer" : "default" }
      }
    ), /* @__PURE__ */ React.createElement("div", { className: "progress-track" }, /* @__PURE__ */ React.createElement("div", { className: "progress-fill " + (playing ? "running" : ""), style: { width: pct + "%" } }))));
  }
  function SimulationTab({ baseUrl, wsStatus }) {
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const [health, setHealth] = useState_sim(null);
    const [src, setSrc] = useState_sim("min");
    const [days, setDays] = useState_sim([]);
    const [date, setDate] = useState_sim("");
    const [stocks, setStocks] = useState_sim([]);
    const [loadingStocks, setLoadingStocks] = useState_sim(false);
    const [selected, setSelected] = useState_sim([]);
    const [stockQuery, setStockQuery] = useState_sim("");
    const [buy, setBuy] = useState_sim("");
    const [sell, setSell] = useState_sim("");
    const [strategies, setStrategies] = useState_sim({ buy: [], sell: [] });
    const [aggSec, setAggSec] = useState_sim(10);
    const [status, setStatus] = useState_sim("idle");
    const [speed, setSpeed] = useState_sim(20);
    const [meta, setMeta] = useState_sim(null);
    const [cursor, setCursor] = useState_sim(0);
    const [curT, setCurT] = useState_sim(null);
    const [wsErr, setWsErr] = useState_sim("");
    const [signals, setSignals] = useState_sim({});
    const [demoActive, setDemoActive] = useState_sim(false);
    const [presetBusy, setPresetBusy] = useState_sim(false);
    const pendingAutoplayRef = useRef_sim(false);
    const demoTriedRef = useRef_sim(false);
    const [indicators, setIndicators] = useState_sim(_loadIndicators);
    const [chartMode, setChartMode] = useState_sim("split");
    const [splitCols, setSplitCols] = useState_sim(_loadSplitCols);
    const [splitRows, setSplitRows] = useState_sim(_loadSplitRows);
    const [engineMode, setEngineMode] = useState_sim(_loadEngineMode);
    const [autoPause, setAutoPause] = useState_sim(false);
    const [highlightSig, setHighlightSig] = useState_sim(null);
    const autoPausedRef = useRef_sim(/* @__PURE__ */ new Set());
    const wsRef = useRef_sim(null);
    const barsRef = useRef_sim({});
    const [barsVersion, setBarsVersion] = useState_sim(0);
    useEffect_sim(() => {
      if (isDemo || !baseUrl) {
        setHealth(null);
        return;
      }
      _simFetchJson(baseUrl + "/sim/health", 3e3).then(setHealth).catch(() => setHealth(null));
    }, [baseUrl, isDemo]);
    useEffect_sim(() => {
      if (isDemo || !baseUrl) {
        setDays([]);
        return;
      }
      _simFetchJson(baseUrl + "/sim/days?src=" + src, 5e3).then((j) => setDays(Array.isArray(j && j.days) ? j.days : [])).catch(() => setDays([]));
      if (!pendingAutoplayRef.current) {
        _stopReplay();
        setDate("");
        setStocks([]);
        setSelected([]);
      }
    }, [baseUrl, isDemo, src]);
    useEffect_sim(() => {
      if (isDemo || !baseUrl) {
        setStrategies({ buy: [], sell: [] });
        return;
      }
      let cancelled = false;
      Promise.all([
        _simFetchJson(baseUrl + "/bt/strategies?kind=buy", 4e3).catch(() => ({ items: [] })),
        _simFetchJson(baseUrl + "/bt/strategies?kind=sell", 4e3).catch(() => ({ items: [] }))
      ]).then(([b, s]) => {
        if (cancelled) return;
        setStrategies({
          buy: (b.items || []).map((it) => it.name),
          sell: (s.items || []).map((it) => it.name)
        });
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo]);
    useEffect_sim(() => {
      if (isDemo || !baseUrl || !date) {
        setStocks([]);
        return;
      }
      setLoadingStocks(true);
      _simFetchJson(baseUrl + "/sim/stocks?date=" + encodeURIComponent(date) + "&src=" + src, 8e3).then((j) => setStocks(Array.isArray(j && j.stocks) ? j.stocks : [])).catch(() => setStocks([])).finally(() => setLoadingStocks(false));
      if (!pendingAutoplayRef.current) {
        setSelected([]);
        _stopReplay();
      }
    }, [baseUrl, isDemo, date]);
    const toggleStock = useCallback_sim((code) => {
      setDemoActive(false);
      setSelected((prev) => {
        if (prev.includes(code)) return prev.filter((c) => c !== code);
        if (prev.length >= _SIM_MAX_CODES) return prev;
        return [...prev, code];
      });
    }, []);
    const toggleIndicator = useCallback_sim((key) => {
      setIndicators((prev) => {
        const next = { ...prev, [key]: !prev[key] };
        _saveIndicators(next);
        return next;
      });
    }, []);
    const setSplitColsPersist = useCallback_sim((v) => {
      setSplitCols(v);
      _saveSplitCols(v);
    }, []);
    const setSplitRowsPersist = useCallback_sim((v) => {
      setSplitRows(v);
      _saveSplitRows(v);
    }, []);
    const setEngineModePersist = useCallback_sim((v) => {
      setEngineMode(v);
      _saveEngineMode(v);
    }, []);
    useEffect_sim(() => {
      if (isDemo || !baseUrl || !date || !buy || !sell || selected.length === 0) {
        setSignals({});
        return;
      }
      let cancelled = false;
      const next = {};
      Promise.all(selected.map(
        (code) => _simFetchJson(
          baseUrl + "/sim/signals?date=" + encodeURIComponent(date) + "&src=" + src + "&code=" + encodeURIComponent(code) + "&buy=" + encodeURIComponent(buy) + "&sell=" + encodeURIComponent(sell),
          2e5
        ).then((j) => {
          next[code] = j && Array.isArray(j.trades) ? j.trades : [];
        }).catch(() => {
          next[code] = [];
        })
      )).then(() => {
        if (!cancelled) setSignals(next);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, date, src, buy, sell, selected.join(",")]);
    const _stopReplay = useCallback_sim(() => {
      if (wsRef.current) {
        try {
          wsRef.current.send(JSON.stringify({ action: "stop" }));
        } catch (e) {
        }
        try {
          wsRef.current.close();
        } catch (e) {
        }
        wsRef.current = null;
      }
      setStatus("idle");
      setMeta(null);
      setCursor(0);
      setCurT(null);
      barsRef.current = {};
      setBarsVersion((v) => v + 1);
    }, []);
    useEffect_sim(() => () => {
      _stopReplay();
    }, [_stopReplay]);
    const startReplay = useCallback_sim(() => {
      if (isDemo || !baseUrl || !date || selected.length === 0) return;
      _stopReplay();
      const url = _wsUrl(baseUrl, "/sim/ws");
      if (!url) {
        setWsErr("WS URL \uC0DD\uC131 \uC2E4\uD328");
        setStatus("error");
        return;
      }
      setWsErr("");
      barsRef.current = {};
      setBarsVersion((v) => v + 1);
      let ws;
      try {
        ws = new WebSocket(url);
      } catch (e) {
        setWsErr(String(e));
        setStatus("error");
        return;
      }
      wsRef.current = ws;
      ws.onopen = () => {
        ws.send(JSON.stringify({
          action: "start",
          date: parseInt(date, 10),
          src,
          codes: selected,
          speed,
          agg_sec: parseInt(aggSec, 10) || 10
        }));
        setStatus("playing");
      };
      ws.onmessage = (ev) => {
        let m;
        try {
          m = JSON.parse(ev.data);
        } catch (e) {
          return;
        }
        if (m.type === "meta") {
          setMeta({ codes: m.codes || [], bars_total: m.bars_total || 0, session_range: m.session_range || [0, 0] });
          setCursor(0);
        } else if (m.type === "bars") {
          const store = barsRef.current;
          (m.items || []).forEach((it) => {
            store[it.code] = [...store[it.code] || [], _simWsBar(it, m.t)];
          });
          setCursor((m.index || 0) + 1);
          setCurT(m.t);
          setBarsVersion((v) => v + 1);
        } else if (m.type === "history") {
          const store = {};
          Object.keys(m.items_by_code || {}).forEach((code) => {
            store[code] = (m.items_by_code[code] || []).map((b) => _simWsBar(b, b.t));
          });
          barsRef.current = store;
          if (m.index != null) setCursor(m.index);
          if (m.t != null) setCurT(m.t);
          setBarsVersion((v) => v + 1);
        } else if (m.type === "done") {
          setStatus((s) => s === "playing" || s === "paused" ? "done" : s);
        } else if (m.type === "error") {
          setWsErr(m.message || "\uB9AC\uD50C\uB808\uC774 \uC624\uB958");
          setStatus("error");
        }
      };
      ws.onerror = () => {
        setWsErr("WebSocket \uC5F0\uACB0 \uC624\uB958");
        setStatus("error");
      };
      ws.onclose = () => {
        if (wsRef.current === ws) wsRef.current = null;
      };
    }, [baseUrl, isDemo, date, src, selected, speed, aggSec, _stopReplay]);
    const _wsSend = (payload) => {
      if (wsRef.current && wsRef.current.readyState === 1) {
        try {
          wsRef.current.send(JSON.stringify(payload));
        } catch (e) {
        }
      }
    };
    const pauseReplay = () => {
      _wsSend({ action: "pause" });
      setStatus("paused");
    };
    const resumeReplay = () => {
      _wsSend({ action: "resume" });
      setStatus("playing");
    };
    const changeSpeed = (sp) => {
      setSpeed(sp);
      _wsSend({ action: "speed", value: sp });
    };
    const seekTo = (idx) => {
      setCursor(idx);
      if (meta && meta.session_range) {
        _wsSend({ action: "seek", t: idx });
      }
    };
    const seekByIndex = (idx) => {
      setCursor(idx);
      const range = meta && meta.session_range;
      if (!range || range[1] <= range[0] || !meta.bars_total) return;
      const frac = meta.bars_total > 1 ? idx / (meta.bars_total - 1) : 0;
      const approxT = Math.round(range[0] + frac * (range[1] - range[0]));
      _wsSend({ action: "seek", t: approxT });
    };
    const stopReplay = () => {
      _stopReplay();
    };
    const applyDemo = useCallback_sim((mode, asDemo) => {
      if (isDemo || !baseUrl) return;
      setPresetBusy(true);
      _stopReplay();
      _simFetchJson(baseUrl + "/sim/demo?src=min&mode=" + encodeURIComponent(mode || "latest"), 8e3).then((j) => {
        if (!j || !j.available || !j.date || !j.code) {
          setPresetBusy(false);
          if (asDemo) setDemoActive(false);
          return;
        }
        setSrc("min");
        setDate(String(j.date));
        setSelected([String(j.code)]);
        setSpeed(_SIM_DEMO_SPEED);
        setDemoActive(!!asDemo);
        pendingAutoplayRef.current = true;
        setPresetBusy(false);
      }).catch(() => {
        setPresetBusy(false);
        if (asDemo) setDemoActive(false);
      });
    }, [baseUrl, isDemo, _stopReplay]);
    useEffect_sim(() => {
      if (!pendingAutoplayRef.current) return;
      if (!date || selected.length === 0) return;
      pendingAutoplayRef.current = false;
      startReplay();
    }, [date, selected, startReplay]);
    useEffect_sim(() => {
      if (demoTriedRef.current) return;
      if (isDemo || !baseUrl) return;
      if (selected.length > 0 || date) return;
      if (_simDemoSeen()) return;
      demoTriedRef.current = true;
      _simMarkDemoSeen();
      applyDemo("latest", true);
    }, [baseUrl, isDemo, applyDemo]);
    const exitDemo = useCallback_sim(() => {
      setDemoActive(false);
      pendingAutoplayRef.current = false;
      _stopReplay();
      setDate("");
      setSelected([]);
    }, [_stopReplay]);
    const onPreset = useCallback_sim((mode) => {
      setDemoActive(false);
      applyDemo(mode, false);
    }, [applyDemo]);
    const codes = meta && meta.codes && meta.codes.length ? meta.codes : selected;
    const canPlay = !isDemo && !!date && selected.length > 0 && (status === "idle" || status === "done" || status === "error");
    const canPlayRef = useRef_sim(canPlay);
    useEffect_sim(() => {
      canPlayRef.current = canPlay;
    }, [canPlay]);
    const seekToTime = useCallback_sim((hms) => {
      if (hms == null) return;
      _wsSend({ action: "seek", t: hms });
      setCurT(hms);
      const range = meta && meta.session_range;
      if (range && range[1] > range[0] && meta.bars_total) {
        const frac = (hms - range[0]) / (range[1] - range[0]);
        setCursor(Math.max(0, Math.min(meta.bars_total, Math.round(frac * (meta.bars_total - 1)))));
      }
    }, [meta]);
    const flatSignals = useMemo_sim(() => _flattenSignals(signals, codes), [signals, codes.join(",")]);
    useEffect_sim(() => {
      if (!autoPause || status !== "playing" || curT == null) return;
      const seen = autoPausedRef.current;
      for (const sig of flatSignals) {
        const key = sig.code + "@" + sig.buy_hms;
        if (sig.buy_hms <= curT && !seen.has(key)) {
          seen.add(key);
          setHighlightSig(key);
          _wsSend({ action: "pause" });
          setStatus("paused");
          break;
        }
      }
    }, [autoPause, status, curT, flatSignals]);
    useEffect_sim(() => {
      if (status === "idle" || status === "playing" && cursor === 0) {
        autoPausedRef.current = /* @__PURE__ */ new Set();
      }
    }, [status]);
    useEffect_sim(() => {
      const onKey = (e) => {
        const tag = e.target && e.target.tagName || "";
        if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || e.target && e.target.isContentEditable) return;
        if (e.key === " " || e.code === "Space") {
          e.preventDefault();
          if (status === "playing") pauseReplay();
          else if (status === "paused") resumeReplay();
          else if (canPlayRef.current) startReplay();
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          const i = _SIM_SPEEDS.indexOf(speed);
          changeSpeed(_SIM_SPEEDS[Math.min(_SIM_SPEEDS.length - 1, (i < 0 ? 0 : i) + 1)]);
        } else if (e.key === "ArrowLeft") {
          e.preventDefault();
          const i = _SIM_SPEEDS.indexOf(speed);
          changeSpeed(_SIM_SPEEDS[Math.max(0, (i < 0 ? 0 : i) - 1)]);
        } else if (e.key === "Escape") {
          if (status === "playing" || status === "paused") stopReplay();
        }
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [status, speed]);
    const connected = !!(health && health.status === "ok");
    const badge = isDemo ? { label: "demo", color: "var(--ink-3)" } : connected ? { label: "connected \xB7 api v" + health.api_version, color: "var(--teal)" } : { label: "checking", color: "var(--amber)" };
    const barsByCode = useMemo_sim(() => ({ ...barsRef.current }), [barsVersion]);
    const colCap = Math.min(_SIM_MAX_SPLIT_COLS, Math.max(1, codes.length));
    const effCols = codes.length <= 1 ? 1 : Math.min(Math.max(1, splitCols), colCap);
    const gridCols = "repeat(" + effCols + ", minmax(0, 1fr))";
    const autoRows = Math.max(1, Math.ceil(codes.length / effCols));
    const effRows = splitRows > 0 ? Math.min(splitRows, autoRows) : autoRows;
    const rowsCapped = effRows < autoRows;
    const dense = codes.length >= 5;
    const gridExtra = rowsCapped ? {
      gridAutoRows: "minmax(0, " + (100 / effRows).toFixed(4) + "%)",
      maxHeight: "calc(100vh - 220px)",
      overflowY: "auto"
    } : {};
    const nameByCode = useMemo_sim(() => {
      const m = {};
      stocks.forEach((s) => {
        m[s.code] = s.name;
      });
      return m;
    }, [stocks]);
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "8px 14px",
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: 8
    } }, /* @__PURE__ */ React.createElement("span", { className: "panel-hd-title", style: { border: 0 } }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uCC28\uD2B8 \uC2DC\uBBAC\uB808\uC774\uC158"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginLeft: 12 } }, "\uC77C\uC77C ", src === "tick" ? "tick" : "min", " DB \uB9AC\uD50C\uB808\uC774 \xB7 \uC5D4\uC9C4 \uC815\uD569 \uC2E0\uD638 \uC624\uBC84\uB808\uC774"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: badge.color, letterSpacing: ".06em", marginLeft: "auto" } }, "\u25CF ", badge.label)), /* @__PURE__ */ React.createElement("div", { className: "grid-main", style: { gridTemplateColumns: "minmax(0, 380px) minmax(0, 1fr)" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14, minWidth: 0 } }, /* @__PURE__ */ React.createElement(SimPresetBar, { isDemo, busy: presetBusy, onPreset }), /* @__PURE__ */ React.createElement(
      SimControlBar,
      {
        baseUrl,
        isDemo,
        src,
        onSrc: setSrc,
        date,
        onDate: setDate,
        days,
        stocks,
        selected,
        onToggleStock: toggleStock,
        stockQuery,
        onStockQuery: setStockQuery,
        loadingStocks,
        buy,
        onBuy: setBuy,
        sell,
        onSell: setSell,
        strategies,
        aggSec,
        onAggSec: setAggSec
      }
    ), /* @__PURE__ */ React.createElement(
      SimMarketMinimap,
      {
        stocks,
        selected,
        onToggleStock: toggleStock,
        query: stockQuery,
        isDemo,
        date,
        loading: loadingStocks
      }
    ), codes.length > 0 && (status !== "idle" || cursor > 0) && /* @__PURE__ */ React.createElement(SimIndicatorTable, { codes, barsByCode, nameByCode }), codes.length > 0 && (status !== "idle" || cursor > 0) && /* @__PURE__ */ React.createElement(SimVariableWatch, { codes, barsByCode, nameByCode }), buy && sell && /* @__PURE__ */ React.createElement(
      SimLearningPanel,
      {
        autoPause,
        onToggleAutoPause: () => setAutoPause((v) => !v),
        signals: flatSignals,
        curT,
        highlightSig,
        onSeek: seekToTime
      }
    ), buy && sell && /* @__PURE__ */ React.createElement(SimSignalLog, { signals: flatSignals, curT })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14, minWidth: 0 } }, demoActive && /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 10,
      padding: "8px 12px",
      background: "rgba(124,108,240,0.10)",
      border: "1px solid var(--violet)",
      borderRadius: 8
    } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
      fontSize: 10.5,
      color: "var(--violet)",
      letterSpacing: ".04em",
      fontWeight: 600,
      display: "flex",
      alignItems: "center",
      gap: 6
    } }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC608\uC2DC \uC790\uB3D9 \uC7AC\uC0DD"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uC900\uBE44\uB41C \uB370\uC774\uD130\uB85C \uB458\uB7EC\uBCF4\uB294 \uC911 \xB7 ", _SIM_DEMO_SPEED, "x"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: exitDemo,
        style: { marginLeft: "auto", fontSize: 10.5, padding: "3px 10px" }
      },
      "\uB0B4\uAC00 \uC120\uD0DD\uD558\uAE30"
    )), /* @__PURE__ */ React.createElement(
      SimPlaybackBar,
      {
        status,
        onPlay: startReplay,
        onPause: pauseReplay,
        onResume: resumeReplay,
        onStop: stopReplay,
        speed,
        onSpeed: changeSpeed,
        cursor,
        total: meta ? meta.bars_total : 0,
        curT,
        sessionRange: meta ? meta.session_range : [0, 0],
        onSeek: seekByIndex,
        canPlay
      }
    ), selected.length > 0 && /* @__PURE__ */ React.createElement(
      SimViewBar,
      {
        indicators,
        onToggleIndicator: toggleIndicator,
        chartMode,
        onChartMode: setChartMode,
        splitCols,
        onSplitCols: setSplitColsPersist,
        splitRows,
        onSplitRows: setSplitRowsPersist,
        colCap,
        codeCount: codes.length,
        engineMode,
        onEngineMode: setEngineModePersist,
        multi: codes.length > 1
      }
    ), wsErr && /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { color: "var(--red)" } }, "\uB9AC\uD50C\uB808\uC774 \uC624\uB958: ", wsErr, /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: startReplay, disabled: !canPlay && status !== "error" }, "\uC7AC\uC2DC\uB3C4"))))), selected.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC67C\uCABD\uC5D0\uC11C \uB0A0\uC9DC\xB7\uC885\uBAA9(\uCD5C\uB300 ", _SIM_MAX_CODES, ")\uC744 \uC120\uD0DD\uD558\uACE0 \u25B6 \uC7AC\uC0DD\uC744 \uB204\uB974\uBA74 \uCE94\uB4E4 \uCC28\uD2B8\uAC00 \uC2E4\uC2DC\uAC04\uC73C\uB85C \uB9AC\uD50C\uB808\uC774\uB429\uB2C8\uB2E4."))) : chartMode === "overlay" && codes.length > 1 ? (
      // 오버레이 모드 — 정규화(시작=100) 한 차트 겹침 비교.
      /* @__PURE__ */ React.createElement(
        SimOverlayChart,
        {
          codes,
          barsByCode,
          nameByCode,
          curT
        }
      )
    ) : (
      // 분할 모드 — 종목별 차트 그리드(반응형 열). 엔진 모드(라이브/LWC/SVG)로 컴포넌트 선택.
      /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: gridCols, gap: dense ? 10 : 14, ...gridExtra } }, codes.map((code) => {
        const chartProps = {
          code,
          name: nameByCode[code],
          bars: barsByCode[code] || [],
          signals: signals[code] || [],
          curT,
          compact: codes.length > 1 && effCols > 1 || dense,
          indicators
        };
        return /* @__PURE__ */ React.createElement(SimChartByEngine, { key: code, engineMode, ...chartProps });
      }))
    ))));
  }
  function SimChartByEngine({ engineMode, ...props }) {
    const Live = window.SimLiveChart;
    const Lwc = window.SimCandleChartLWC;
    const Svg = window.SimCandleChartSVG;
    const Auto = window.SimCandleChart;
    if (engineMode === "live" && Live) return /* @__PURE__ */ React.createElement(Live, { ...props });
    if (engineMode === "svg" && Svg) return /* @__PURE__ */ React.createElement(Svg, { ...props });
    if (engineMode === "lwc" && Lwc) return /* @__PURE__ */ React.createElement(Lwc, { ...props });
    return Auto ? /* @__PURE__ */ React.createElement(Auto, { ...props }) : null;
  }
  var _SIM_VIEWBAR_LABEL = {
    fontSize: 11,
    color: "var(--ink-1)",
    fontWeight: 600,
    letterSpacing: ".3px"
  };
  var _SIM_ENGINE_ROWS = [
    ["\uB77C\uC774\uBE0C", "Canvas\xB7\uAE30\uBCF8\xB7\uCD5C\uACBD\uB7C9 \xB7 \uD480 \uC624\uB354\uD50C\uB85C\uC6B0(\uCCB4\uACB0\uAC15\uB3C4\xB7\uD638\uAC00\xB7net-delta)"],
    ["SVG", "\uBB34\uC758\uC874 \uD3F4\uBC31 \xB7 \uD480 \uC624\uB354\uD50C\uB85C\uC6B0(\uCCB4\uACB0\uAC15\uB3C4\xB7\uD638\uAC00\xB7net-delta)"],
    ["LWC", "\uC804\uBB38 \uC90C/\uD06C\uB85C\uC2A4\uD5E4\uC5B4 \xB7 \uCCB4\uACB0\uAC15\uB3C4 \uC624\uBC84\uB808\uC774\uB9CC"]
  ];
  function SimEnginePopover({ onClose }) {
    const ref = useRef_sim(null);
    useEffect_sim(() => {
      const onKey = (e) => {
        if (e.key === "Escape") onClose();
      };
      const onDoc = (e) => {
        if (ref.current && !ref.current.contains(e.target)) onClose();
      };
      document.addEventListener("keydown", onKey);
      document.addEventListener("mousedown", onDoc);
      if (ref.current) {
        try {
          ref.current.focus();
        } catch (e) {
        }
      }
      return () => {
        document.removeEventListener("keydown", onKey);
        document.removeEventListener("mousedown", onDoc);
      };
    }, [onClose]);
    return /* @__PURE__ */ React.createElement(
      "div",
      {
        ref,
        role: "dialog",
        "aria-label": "\uC5D4\uC9C4 \uC124\uBA85",
        tabIndex: -1,
        onKeyDown: (e) => {
          if (e.key === "Enter" || e.key === " ") onClose();
        },
        style: {
          position: "absolute",
          top: "100%",
          left: 0,
          marginTop: 6,
          zIndex: 30,
          minWidth: 320,
          maxWidth: 420,
          padding: "10px 12px",
          background: "var(--bg-1)",
          border: "1px solid var(--line-1)",
          borderRadius: 8,
          boxShadow: "0 8px 24px rgba(0,0,0,0.45)",
          color: "var(--ink-1)"
        }
      },
      /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, fontWeight: 600, color: "var(--ink-1)", marginBottom: 6 } }, "\uC5D4\uC9C4\uBCC4 \uC5ED\uD560(\uBE44\uB300\uCE6D) \u2014 \uAC19\uC740 \uB370\uC774\uD130, \uB2E4\uB978 \uAC15\uC810"),
      /* @__PURE__ */ React.createElement("table", { className: "mono", style: { width: "100%", fontSize: 10.5, color: "var(--ink-1)", borderCollapse: "collapse" } }, /* @__PURE__ */ React.createElement("tbody", null, _SIM_ENGINE_ROWS.map(([name, desc]) => /* @__PURE__ */ React.createElement("tr", { key: name }, /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 8px 3px 0", color: "var(--teal)", whiteSpace: "nowrap", verticalAlign: "top" } }, name), /* @__PURE__ */ React.createElement("td", { style: { padding: "3px 0", color: "var(--ink-1)" } }, desc))))),
      /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8, textAlign: "right" } }, /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onClose, style: { fontSize: 10.5, padding: "2px 10px" } }, "\uB2EB\uAE30"))
    );
  }
  function SimViewBar({
    indicators,
    onToggleIndicator,
    chartMode,
    onChartMode,
    splitCols,
    onSplitCols,
    splitRows,
    onSplitRows,
    colCap,
    codeCount,
    multi,
    engineMode,
    onEngineMode
  }) {
    const indGroups = [
      ["\uAC00\uACA9", [["ma", "MA"], ["ema", "EMA"], ["vwap", "VWAP"], ["boll", "\uBCFC\uB9B0\uC800"], ["vwapband", "VWAP\uBC34\uB4DC"]]],
      ["\uBAA8\uBA58\uD140", [["rsi", "RSI"], ["macd", "MACD"]]],
      ["\uD750\uB984", [["strength", "\uCCB4\uACB0\uAC15\uB3C4"], ["imbalance", "\uD638\uAC00"], ["orderflow", "\uC624\uB354\uD50C\uB85C\uC6B0"], ["volma", "\uAC70\uB798\uB7C9MA"], ["strma", "\uCCB4\uACB0\uAC15\uB3C4MA"]]]
    ];
    const [engineInfoOpen, setEngineInfoOpen] = useState_sim(false);
    const tbtn = (active, label, onClick, key, title) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key,
        onClick,
        className: "mono",
        title,
        style: {
          padding: "3px 9px",
          fontSize: 10.5,
          borderRadius: 4,
          border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
          background: active ? "rgba(76,214,179,0.10)" : "transparent",
          color: active ? "var(--teal)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      label
    );
    const colChoices = [];
    for (let c = 1; c <= Math.max(1, colCap || 1); c += 1) colChoices.push(c);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", padding: "7px 10px" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { ..._SIM_VIEWBAR_LABEL, display: "inline-flex", alignItems: "center", gap: 4, position: "relative" } }, "\uC5D4\uC9C4", /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        "aria-label": "\uC5D4\uC9C4 \uC124\uBA85",
        title: "\uC5D4\uC9C4\uBCC4 \uC5ED\uD560 \uC124\uBA85",
        onClick: () => setEngineInfoOpen((v) => !v),
        style: {
          width: 16,
          height: 16,
          lineHeight: "14px",
          padding: 0,
          borderRadius: "50%",
          border: "1px solid var(--line-1)",
          background: "transparent",
          color: "var(--ink-1)",
          cursor: "pointer",
          fontSize: 10,
          fontWeight: 700
        }
      },
      "\u24D8"
    ), engineInfoOpen && /* @__PURE__ */ React.createElement(SimEnginePopover, { onClose: () => setEngineInfoOpen(false) })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, _SIM_ENGINE_MODES.map(([m, lbl]) => tbtn(
      engineMode === m,
      lbl,
      () => onEngineMode(m),
      "e" + m,
      m === "live" ? "Canvas \uB77C\uC774\uBE0C \uB80C\uB354(\uD604\uC7AC\uBD09 \uC131\uC7A5\xB7\uD50C\uB798\uC2DC\xB7\uD480 \uC624\uB354\uD50C\uB85C\uC6B0)" : m === "lwc" ? "lightweight-charts(\uC804\uBB38 \uC90C/\uD06C\uB85C\uC2A4\uD5E4\uC5B4\xB7\uCCB4\uACB0\uAC15\uB3C4 \uC624\uBC84\uB808\uC774\uB9CC)" : "\uC21C\uC218 SVG \uD3F4\uBC31(\uD480 \uC624\uB354\uD50C\uB85C\uC6B0)"
    ))), engineMode === "lwc" && /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "mono",
        title: "LWC(lightweight-charts)\uB294 \uCE94\uB4E4 \uAC00\uB3C5\uC131\uC744 \uC704\uD574 \uC77C\uBD80 \uD558\uB2E8 \uC11C\uBE0C\uD328\uC778\uC744 \uC2E3\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4(\uC758\uB3C4\uB41C \uBE44\uB300\uCE6D). \uC804\uCCB4 \uC624\uB354\uD50C\uB85C\uC6B0/\uBAA8\uBA58\uD140\uC740 \uB77C\uC774\uBE0C\xB7SVG \uC5D4\uC9C4\uC5D0\uC11C \uBCF4\uC138\uC694.",
        style: { fontSize: 9.5, color: "var(--ink-3)" }
      },
      "LWC \uBE44\uB300\uCE6D \u2014 RSI\xB7MACD\xB7\uD638\uAC00\uBD88\uADE0\uD615\xB7net-delta \uBBF8\uD45C\uC2DC(\uB77C\uC774\uBE0C\xB7SVG \uC804\uC6A9)"
    ), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { ..._SIM_VIEWBAR_LABEL, marginLeft: 6 } }, "\uC9C0\uD45C"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" } }, indGroups.map(([grp, defs]) => /* @__PURE__ */ React.createElement("div", { key: grp, style: { display: "flex", gap: 4, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, grp), defs.map(([k, lbl]) => tbtn(!!indicators[k], lbl, () => onToggleIndicator(k), k))))), multi && /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { ..._SIM_VIEWBAR_LABEL, marginLeft: 6 } }, "\uBCF4\uAE30"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4 } }, _SIM_CHART_MODES.map(([m, lbl]) => tbtn(
      chartMode === m,
      lbl,
      () => onChartMode(m),
      m,
      m === "overlay" ? "\uC815\uADDC\uD654 \uD55C \uCC28\uD2B8 \uACB9\uCE68" : "\uC885\uBAA9\uBCC4 \uBD84\uD560 \uADF8\uB9AC\uB4DC"
    ))), chartMode === "split" && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "\uC5F4"), colChoices.map((c) => tbtn(splitCols === c, String(c), () => onSplitCols(c), "c" + c, c + "\uC5F4\uB85C \uBD84\uD560"))), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 4, alignItems: "center" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)" } }, "\uD589"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "mono",
        title: "\uC790\uB3D9 \uD589\uC218(\uC885\uBAA9\uC218/\uC5F4)",
        onClick: () => onSplitRows(0),
        style: {
          padding: "3px 9px",
          fontSize: 10.5,
          borderRadius: 4,
          border: "1px solid " + ((splitRows || 0) === 0 ? "var(--teal-dim)" : "var(--line-1)"),
          background: (splitRows || 0) === 0 ? "rgba(76,214,179,0.10)" : "transparent",
          color: (splitRows || 0) === 0 ? "var(--teal)" : "var(--ink-2)",
          cursor: "pointer"
        }
      },
      "\uC790\uB3D9"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "mono",
        "aria-label": "\uD589 \uC904\uC774\uAE30",
        title: "\uBCF4\uC774\uB294 \uD589 \uC904\uC774\uAE30",
        onClick: () => onSplitRows(Math.max(1, (splitRows || 0) - 1)),
        style: { padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "1px solid var(--line-1)", background: "transparent", color: "var(--ink-2)", cursor: "pointer" }
      },
      "\u2212"
    ), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-1)", minWidth: 18, textAlign: "center" } }, (splitRows || 0) === 0 ? "\u2014" : splitRows), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "mono",
        "aria-label": "\uD589 \uB298\uB9AC\uAE30",
        title: "\uBCF4\uC774\uB294 \uD589 \uB298\uB9AC\uAE30",
        onClick: () => onSplitRows(Math.min(_SIM_MAX_CODES, (splitRows || 0) + 1)),
        style: { padding: "3px 8px", fontSize: 11, borderRadius: 4, border: "1px solid var(--line-1)", background: "transparent", color: "var(--ink-2)", cursor: "pointer" }
      },
      "\uFF0B"
    ))))));
  }
  function _flattenSignals(signals, codes) {
    const out = [];
    (codes || []).forEach((code) => {
      (signals[code] || []).forEach((s) => out.push({ ...s, code }));
    });
    out.sort((a, b) => a.buy_hms - b.buy_hms);
    return out;
  }
  function _simFmtNum(v, digits) {
    if (v == null) return "\u2014";
    const n = Number(v);
    if (!isFinite(n)) return "\u2014";
    return n.toLocaleString("ko-KR", { maximumFractionDigits: digits == null ? 0 : digits });
  }
  function SimIndicatorCell({ value, digits, prev, className }) {
    const dir = prev == null || value == null || value === prev ? "" : value > prev ? "sim-flash-up" : "sim-flash-down";
    return /* @__PURE__ */ React.createElement("td", { key: value + ":" + dir, className: (className || "") + " " + dir }, _simFmtNum(value, digits));
  }
  function SimIndicatorTable({ codes, barsByCode, nameByCode }) {
    const prevRef = useRef_sim({});
    const rows = (codes || []).map((code) => {
      const arr = barsByCode[code] || [];
      const last = arr.length ? arr[arr.length - 1] : null;
      return { code, name: nameByCode[code] || code, bar: last };
    });
    const prev = prevRef.current;
    useEffect_sim(() => {
      const next = {};
      rows.forEach((r) => {
        if (r.bar) next[r.code] = r.bar;
      });
      prevRef.current = next;
    });
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "\uC9C0\uD45C \uB77C\uC774\uBE0C"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uD604\uC7AC \uC2DC\uAC01 \uAE30\uC900")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { overflowX: "auto", padding: "6px 8px" } }, /* @__PURE__ */ React.createElement("table", { className: "sim-live-table" }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC885\uBAA9"), /* @__PURE__ */ React.createElement("th", null, "\uD604\uC7AC\uAC00"), /* @__PURE__ */ React.createElement("th", null, "\uB4F1\uB77D%"), /* @__PURE__ */ React.createElement("th", null, "\uAC15\uB3C4"), /* @__PURE__ */ React.createElement("th", null, "VWAP"), /* @__PURE__ */ React.createElement("th", null, "MA5"), /* @__PURE__ */ React.createElement("th", null, "MA20"), /* @__PURE__ */ React.createElement("th", null, "MA60"), /* @__PURE__ */ React.createElement("th", null, "\uD638\uAC00\uBD88\uADE0\uD615"))), /* @__PURE__ */ React.createElement("tbody", null, rows.map(({ code, name, bar }) => {
      const p = prev[code] || {};
      if (!bar) {
        return /* @__PURE__ */ React.createElement("tr", { key: code }, /* @__PURE__ */ React.createElement("td", { title: name }, code), /* @__PURE__ */ React.createElement("td", { colSpan: 8, style: { color: "var(--ink-3)" } }, "\uB300\uAE30\u2026"));
      }
      return /* @__PURE__ */ React.createElement("tr", { key: code }, /* @__PURE__ */ React.createElement("td", { title: name, style: { color: "var(--ink-1)" } }, code), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.c, digits: 0, prev: p.c }), /* @__PURE__ */ React.createElement("td", { className: bar.change > 0 ? "num-pos" : bar.change < 0 ? "num-neg" : "" }, bar.change > 0 ? "+" : "", (bar.change || 0).toFixed(2)), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.strength, digits: 0, prev: p.strength }), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.vwap, digits: 0, prev: p.vwap }), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.ma5, digits: 0, prev: p.ma5 }), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.ma20, digits: 0, prev: p.ma20 }), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.ma60, digits: 0, prev: p.ma60 }), /* @__PURE__ */ React.createElement(SimIndicatorCell, { value: bar.imbalance, digits: 2, prev: p.imbalance }));
    })))));
  }
  function SimLearningPanel({ autoPause, onToggleAutoPause, signals, curT, highlightSig, onSeek }) {
    const rows = signals || [];
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uD559\uC2B5 \uBAA8\uB4DC")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { display: "flex", flexDirection: "column", gap: 10, padding: "10px" } }, /* @__PURE__ */ React.createElement("label", { style: { display: "flex", alignItems: "center", gap: 8, cursor: "pointer" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "checkbox",
        checked: autoPause,
        onChange: onToggleAutoPause,
        style: { accentColor: "var(--violet)" }
      }
    ), /* @__PURE__ */ React.createElement("span", { style: { fontSize: 11.5, color: "var(--ink-1)" } }, "\uC2E0\uD638 \uC790\uB3D9 \uC77C\uC2DC\uC815\uC9C0"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)", marginLeft: "auto" } }, "\uB9E4\uC218 \uC2DC\uAC01 \uB3C4\uB2EC \uC2DC \uC815\uC9C0")), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 10, color: "var(--ink-3)" } }, /* @__PURE__ */ React.createElement("span", { className: "sim-kbd" }, "Space"), " \uC7AC\uC0DD/\uC815\uC9C0", /* @__PURE__ */ React.createElement("span", { className: "sim-kbd" }, "\u2190"), /* @__PURE__ */ React.createElement("span", { className: "sim-kbd" }, "\u2192"), " \uBC30\uC18D", /* @__PURE__ */ React.createElement("span", { className: "sim-kbd" }, "Esc"), " \uC815\uC9C0"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 3, maxHeight: 200, overflowY: "auto" } }, rows.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { fontSize: 10.5 } }, "\uB9E4\uB9E4 \uC2E0\uD638\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4.") : rows.map((s, i) => {
      const key = s.code + "@" + s.buy_hms;
      const reached = curT != null && s.buy_hms <= curT;
      const isHi = highlightSig === key;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: i,
          className: "sim-bookmark " + (reached ? "reached" : "pending"),
          onClick: () => onSeek(s.buy_hms),
          style: isHi ? { borderColor: "var(--violet)", background: "rgba(124,108,240,0.12)" } : null
        },
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--teal)", flexShrink: 0 } }, "\u25B2", window._simTimeLabel(s.buy_hms)),
        /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 9.5, color: "var(--ink-3)", flexShrink: 0 } }, s.code),
        /* @__PURE__ */ React.createElement(
          "span",
          {
            className: "mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg"),
            style: { fontSize: 10.5, marginLeft: "auto", flexShrink: 0 }
          },
          s.profit_pct >= 0 ? "+" : "",
          (s.profit_pct || 0).toFixed(1),
          "%"
        )
      );
    }))));
  }
  var _SIM_WATCH_VARS = [
    { key: "c", label: "\uD604\uC7AC\uAC00", digits: 0 },
    { key: "change", label: "\uB4F1\uB77D\uC728", digits: 2 },
    { key: "strength", label: "\uCCB4\uACB0\uAC15\uB3C4", digits: 0 },
    { key: "vwap", label: "VWAP", digits: 0 },
    { key: "ma5", label: "MA5", digits: 0 },
    { key: "ma20", label: "MA20", digits: 0 },
    { key: "ma60", label: "MA60", digits: 0 },
    { key: "net_qty", label: "\uC21C\uB9E4\uC218\uC218\uB7C9", digits: 0 },
    { key: "imbalance", label: "\uD638\uAC00\uBD88\uADE0\uD615", digits: 2 },
    { key: "buy_rest", label: "\uB9E4\uC218\uCD1D\uC794\uB7C9", digits: 0 },
    { key: "sell_rest", label: "\uB9E4\uB3C4\uCD1D\uC794\uB7C9", digits: 0 }
  ];
  var _SIM_WATCH_LS_KEY = "stom.sim.watch.v1";
  function _loadWatchThresholds() {
    try {
      const raw = window.localStorage.getItem(_SIM_WATCH_LS_KEY);
      const obj = raw ? JSON.parse(raw) : null;
      return obj && typeof obj === "object" ? obj : {};
    } catch (e) {
      return {};
    }
  }
  function _saveWatchThresholds(map) {
    try {
      window.localStorage.setItem(_SIM_WATCH_LS_KEY, JSON.stringify(map || {}));
    } catch (e) {
    }
  }
  function _evalWatch(value, th) {
    if (!th || th.value === "" || th.value == null) return null;
    if (value == null) return null;
    const v = Number(value), t = Number(th.value);
    if (!isFinite(v) || !isFinite(t)) return null;
    return th.op === "<=" ? v <= t : v >= t;
  }
  function SimVariableWatch({ codes, barsByCode, nameByCode }) {
    const [thresholds, setThresholds] = useState_sim(_loadWatchThresholds);
    const [watchCode, setWatchCode] = useState_sim(codes && codes[0] || "");
    const prevMetRef = useRef_sim({});
    useEffect_sim(() => {
      if (!codes || codes.length === 0) return;
      if (!codes.includes(watchCode)) setWatchCode(codes[0]);
    }, [codes.join(",")]);
    const setTh = useCallback_sim((key, patch) => {
      setThresholds((prev) => {
        const cur = prev[key] || { op: ">=", value: "" };
        const next = { ...prev, [key]: { ...cur, ...patch } };
        _saveWatchThresholds(next);
        return next;
      });
    }, []);
    const clearAll = useCallback_sim(() => {
      setThresholds({});
      _saveWatchThresholds({});
      prevMetRef.current = {};
    }, []);
    const arr = barsByCode[watchCode] || [];
    const bar = arr.length ? arr[arr.length - 1] : null;
    useEffect_sim(() => {
      const snap = {};
      _SIM_WATCH_VARS.forEach((v) => {
        snap[v.key] = bar ? _evalWatch(bar[v.key], thresholds[v.key]) : null;
      });
      prevMetRef.current = snap;
    });
    const prevMet = prevMetRef.current;
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--amber)" } }), "\uBCC0\uC218 \uC6CC\uCE58"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } }, codes && codes.length > 1 && /* @__PURE__ */ React.createElement(
      "select",
      {
        className: "select",
        value: watchCode,
        onChange: (e) => setWatchCode(e.target.value),
        style: { fontSize: 10.5, padding: "2px 6px", height: "auto" }
      },
      codes.map((c) => /* @__PURE__ */ React.createElement("option", { key: c, value: c }, nameByCode[c] || c))
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: clearAll, style: { fontSize: 10, padding: "2px 7px" } }, "\uC784\uACC4 \uCD08\uAE30\uD654"))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: "6px 8px" } }, !bar ? /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { fontSize: 10.5 } }, "\uC7AC\uC0DD\uC744 \uC2DC\uC791\uD558\uBA74 \uD604\uC7AC \uAC12\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement("table", { className: "sim-live-table", style: { width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left" } }, "\uBCC0\uC218"), /* @__PURE__ */ React.createElement("th", null, "\uD604\uC7AC\uAC12"), /* @__PURE__ */ React.createElement("th", { style: { width: 44 } }, "\uC870\uAC74"), /* @__PURE__ */ React.createElement("th", { style: { width: 76 } }, "\uC784\uACC4\uAC12"))), /* @__PURE__ */ React.createElement("tbody", null, _SIM_WATCH_VARS.map((v) => {
      const value = bar[v.key];
      const th = thresholds[v.key] || { op: ">=", value: "" };
      const met = _evalWatch(value, th);
      const was = prevMet[v.key];
      const rowBg = met == null ? "transparent" : met ? "rgba(76,214,179,0.10)" : "rgba(255,93,108,0.10)";
      const flash = met === true && was !== true ? "sim-flash-up" : "";
      const valTxt = value == null ? "\u2014" : _simFmtNum(value, v.digits);
      return /* @__PURE__ */ React.createElement("tr", { key: v.key, className: flash, style: { background: rowBg } }, /* @__PURE__ */ React.createElement("td", { style: { textAlign: "left", color: "var(--ink-1)" } }, v.label), /* @__PURE__ */ React.createElement("td", { className: "mono", style: {
        color: met == null ? "var(--ink-1)" : met ? "var(--teal)" : "var(--red)"
      } }, valTxt), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(
        "select",
        {
          value: th.op,
          onChange: (e) => setTh(v.key, { op: e.target.value }),
          className: "mono",
          style: {
            fontSize: 11,
            padding: "1px 2px",
            background: "var(--bg-0)",
            color: "var(--ink-1)",
            border: "1px solid var(--line-1)",
            borderRadius: 4
          }
        },
        /* @__PURE__ */ React.createElement("option", { value: ">=" }, "\u2265"),
        /* @__PURE__ */ React.createElement("option", { value: "<=" }, "\u2264")
      )), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(
        "input",
        {
          type: "number",
          value: th.value,
          onChange: (e) => setTh(v.key, { value: e.target.value }),
          placeholder: "\u2014",
          className: "mono",
          style: {
            width: "100%",
            fontSize: 11,
            padding: "2px 4px",
            textAlign: "right",
            background: "var(--bg-0)",
            color: "var(--ink-1)",
            border: "1px solid var(--line-1)",
            borderRadius: 4
          }
        }
      )));
    }))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 9.5, color: "var(--ink-3)", marginTop: 6, lineHeight: 1.5 } }, "\uC784\uACC4\uB294 \uD604\uC7AC \uD504\uB808\uC784 \uAC12\uACFC\uC758 \uB2E8\uC21C \uBE44\uAD50\uB2E4. \uC870\uAC74\uC2DD \uC5D4\uC9C4 \uC815\uD569 \uB9E4\uB9E4 \uC2E0\uD638\uB294 \uC704 ", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)" } }, "\uB9E4\uC218/\uB9E4\uB3C4 \uC870\uAC74\uC2DD"), " \uC120\uD0DD \uC2DC \uCC28\uD2B8\uC5D0 \uC624\uBC84\uB808\uC774\uB41C\uB2E4.")));
  }
  Object.assign(window, { SimulationTab });

  // ../frontend/evolution-analysis.jsx
  var {
    useState: useState_ea,
    useEffect: useEffect_ea,
    useMemo: useMemo_ea,
    useRef: useRef_ea,
    useCallback: useCallback_ea
  } = React;
  function _eaFetchJson(url, timeoutMs) {
    return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 5e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)));
  }
  var _fScore = (v) => typeof window.fmtScore === "function" ? window.fmtScore(v) : typeof v === "number" ? v.toFixed(3) : "\u2014";
  var _fPct = (v) => typeof window.fmtPct === "function" ? window.fmtPct(v) : typeof v === "number" ? v.toFixed(2) + "%" : "\u2014";
  var _fMoney = (v) => typeof window.fmtMoney === "function" ? window.fmtMoney(v) : typeof v === "number" ? v.toLocaleString("ko-KR") + "\uC6D0" : "\u2014";
  var _fInt = (v) => typeof window.fmtInt === "function" ? window.fmtInt(v) : typeof v === "number" ? v.toLocaleString("ko-KR") : "\u2014";
  var EA_SERIES = [
    { key: "score", label: "score", color: "var(--teal)", fmt: _fScore },
    { key: "profit", label: "profit", color: "var(--violet)", fmt: _fMoney },
    { key: "mdd", label: "mdd(%)", color: "var(--red)", fmt: _fPct },
    { key: "trade_count", label: "trades", color: "var(--blue)", fmt: _fInt }
  ];
  function EaEmpty({ text }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      inset: 0,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)"
    } }, text);
  }
  function EaMultiMetricChart({ gens, normalize }) {
    const W = 880, H = 320;
    const padL = 46, padR = 24, padT = 18, padB = 34;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const nums = gens.filter((g) => g.gen_no >= 0);
    const xMax = Math.max(8, ...nums.map((g) => g.gen_no + 1));
    const x = (g) => padL + (g + 0.5) / xMax * innerW;
    const ranges = useMemo_ea(() => {
      const r = {};
      for (const s of EA_SERIES) {
        const vals = nums.map((g) => typeof g[s.key] === "number" ? g[s.key] : 0);
        const mn = Math.min(0, ...vals), mx = Math.max(1, ...vals);
        r[s.key] = { mn, mx, span: mx - mn || 1 };
      }
      return r;
    }, [nums]);
    const yNorm = (v, key) => {
      const rg = ranges[key];
      const t = (v - rg.mn) / rg.span;
      return padT + innerH - t * innerH;
    };
    const activeSeries = normalize ? EA_SERIES : [EA_SERIES[0]];
    const paths = useMemo_ea(() => {
      return activeSeries.map((s) => {
        if (nums.length === 0) return { key: s.key, d: "" };
        const d = nums.map(
          (g, i) => `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yNorm(typeof g[s.key] === "number" ? g[s.key] : 0, s.key).toFixed(2)}`
        ).join(" ");
        return { key: s.key, d, color: s.color };
      });
    }, [nums, xMax, normalize, ranges]);
    const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
    const xTicks = [];
    for (let g = 0; g < xMax; g++) {
      if (g === 0 || g === xMax - 1 || g % xStep === 0) xTicks.push(g);
    }
    const [hover, setHover] = useState_ea(null);
    const svgRef = useRef_ea(null);
    const onMove = (e) => {
      if (!nums.length || !svgRef.current) return;
      const rect = svgRef.current.getBoundingClientRect();
      const px = (e.clientX - rect.left) * (W / rect.width);
      let best = null, bestDist = Infinity;
      for (const g of nums) {
        const d = Math.abs(x(g.gen_no) - px);
        if (d < bestDist) {
          bestDist = d;
          best = g;
        }
      }
      setHover(best && bestDist < 40 ? best : null);
    };
    return /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        ref: svgRef,
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseMove: onMove,
        onMouseLeave: () => setHover(null)
      },
      (normalize ? [0, 0.25, 0.5, 0.75, 1] : [0, 0.5, 1]).map((t, i) => {
        const yy = normalize ? padT + innerH - t * innerH : yNorm(t, "score");
        return /* @__PURE__ */ React.createElement("g", { key: `g${i}` }, /* @__PURE__ */ React.createElement("line", { className: "chart-grid-line", x1: padL, x2: W - padR, y1: yy, y2: yy }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: yy + 3, textAnchor: "end" }, normalize ? t.toFixed(2) : t.toFixed(1)));
      }),
      xTicks.map((g, i) => /* @__PURE__ */ React.createElement("text", { key: `x${i}`, className: "chart-axis-text", x: x(g), y: H - 14, textAnchor: "middle" }, "g", g)),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      nums.length > 1 && paths.map((p) => /* @__PURE__ */ React.createElement(
        "path",
        {
          key: p.key,
          d: p.d,
          fill: "none",
          stroke: p.color,
          strokeWidth: "1.6",
          strokeLinejoin: "round",
          strokeLinecap: "round",
          opacity: "0.92"
        }
      )),
      nums.map((g, i) => g.gate_passed ? /* @__PURE__ */ React.createElement(
        "path",
        {
          key: `m${i}`,
          d: `M ${x(g.gen_no)} ${padT + innerH + 2} l 4 7 l -8 0 Z`,
          fill: "var(--teal)",
          opacity: "0.9"
        }
      ) : null),
      hover && /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: x(hover.gen_no),
          x2: x(hover.gen_no),
          y1: padT,
          y2: padT + innerH,
          stroke: "rgba(255,255,255,0.12)",
          strokeWidth: "1"
        }
      )
    ), hover && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 14,
      right: 14,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 190,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 } }, "gen_", String(hover.gen_no).padStart(2, "0"), hover.gate_passed && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)", marginLeft: 6 } }, "\u2713")), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, EA_SERIES.map((s) => /* @__PURE__ */ React.createElement(React.Fragment, { key: s.key }, /* @__PURE__ */ React.createElement("span", { style: { color: s.color } }, s.label), /* @__PURE__ */ React.createElement("span", null, s.fmt(hover[s.key])))))), nums.length === 0 && /* @__PURE__ */ React.createElement(EaEmpty, { text: "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4" }));
  }
  function EaScatterChart({ gens }) {
    const W = 880, H = 360;
    const padL = 64, padR = 24, padT = 18, padB = 40;
    const innerW = W - padL - padR;
    const innerH = H - padT - padB;
    const pts = gens.filter((g) => g.gen_no >= 0 && g.status !== "error");
    const mddVals = pts.map((p) => typeof p.mdd === "number" ? p.mdd : 0);
    const profVals = pts.map((p) => typeof p.profit === "number" ? p.profit : 0);
    const mddMax = Math.max(1, ...mddVals);
    const profMax = Math.max(0, ...profVals);
    const profMin = Math.min(0, ...profVals);
    const profSpan = profMax - profMin || 1;
    const x = (mdd) => padL + mdd / mddMax * innerW;
    const y = (p) => padT + innerH - (p - profMin) / profSpan * innerH;
    const xTicks = useMemo_ea(() => {
      const out = [];
      const step = mddMax <= 10 ? 2 : mddMax <= 30 ? 5 : 10;
      for (let v = 0; v <= mddMax + 1e-9; v += step) out.push(+v.toFixed(1));
      return out;
    }, [mddMax]);
    const yTicks = useMemo_ea(() => {
      const out = [];
      const step = profSpan / 4;
      for (let i = 0; i <= 4; i++) out.push(profMin + step * i);
      return out;
    }, [profMin, profSpan]);
    const [hover, setHover] = useState_ea(null);
    return /* @__PURE__ */ React.createElement("div", { className: "chart-wrap", style: { position: "relative" } }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${H}`,
        preserveAspectRatio: "none",
        onMouseLeave: () => setHover(null)
      },
      yTicks.map((t, i) => /* @__PURE__ */ React.createElement("g", { key: `y${i}` }, /* @__PURE__ */ React.createElement("line", { className: "chart-grid-line", x1: padL, x2: W - padR, y1: y(t), y2: y(t) }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL - 8, y: y(t) + 3, textAnchor: "end" }, Math.abs(t) >= 1e6 ? (t / 1e6).toFixed(1) + "M" : Math.round(t / 1e3) + "k"))),
      profMin < 0 && /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: padL,
          x2: W - padR,
          y1: y(0),
          y2: y(0),
          stroke: "rgba(106,166,255,0.5)",
          strokeWidth: "1",
          strokeDasharray: "5 4"
        }
      ),
      xTicks.map((t, i) => /* @__PURE__ */ React.createElement("g", { key: `x${i}` }, /* @__PURE__ */ React.createElement("line", { x1: x(t), x2: x(t), y1: padT, y2: padT + innerH, stroke: "var(--line-1)", strokeWidth: "1", opacity: "0.5" }), /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: x(t), y: H - 18, textAnchor: "middle" }, t, "%"))),
      /* @__PURE__ */ React.createElement("text", { className: "chart-axis-text", x: padL + innerW / 2, y: H - 4, textAnchor: "middle", fill: "var(--ink-2)" }, "MDD (\uB099\uD3ED %) \u2192  \xB7  \u2191 \uC190\uC775(\uC6D0)"),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: W - padR, y1: padT + innerH, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      /* @__PURE__ */ React.createElement("line", { x1: padL, x2: padL, y1: padT, y2: padT + innerH, stroke: "var(--line-2)", strokeWidth: "1" }),
      pts.map((p, i) => {
        const cx = x(typeof p.mdd === "number" ? p.mdd : 0);
        const cy = y(typeof p.profit === "number" ? p.profit : 0);
        const col = p.gate_passed ? "var(--teal)" : "var(--ink-3)";
        const isH = hover && hover.gen_no === p.gen_no;
        return /* @__PURE__ */ React.createElement("g", { key: i, onMouseEnter: () => setHover(p), style: { cursor: "pointer" } }, p.gate_passed && /* @__PURE__ */ React.createElement("circle", { cx, cy, r: "8", fill: "rgba(76,214,179,0.14)" }), /* @__PURE__ */ React.createElement(
          "circle",
          {
            cx,
            cy,
            r: isH ? 6 : 4,
            fill: col,
            stroke: isH ? "var(--ink-0)" : "none",
            strokeWidth: "1.2"
          }
        ));
      })
    ), hover && /* @__PURE__ */ React.createElement("div", { style: {
      position: "absolute",
      top: 14,
      left: 80,
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      borderRadius: 6,
      padding: "8px 10px",
      fontFamily: "var(--mono)",
      fontSize: 11,
      minWidth: 190,
      boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
      pointerEvents: "none"
    } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 } }, "gen_", String(hover.gen_no).padStart(2, "0"), hover.gate_passed && /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)", marginLeft: 6 } }, "\u2713 \uD1B5\uACFC")), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" } }, /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "score"), /* @__PURE__ */ React.createElement("span", null, _fScore(hover.score)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "MDD"), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, _fPct(hover.mdd)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uC190\uC775"), /* @__PURE__ */ React.createElement("span", { className: hover.profit > 0 ? "num-pos" : hover.profit < 0 ? "num-neg" : "" }, _fMoney(hover.profit)), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("span", null, _fInt(hover.trade_count)))), pts.length === 0 && /* @__PURE__ */ React.createElement(EaEmpty, { text: "\uC0B0\uC810 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4" }));
  }
  function EaTopTable({ runId, gens, topN, onOpenWorkbench }) {
    const canOpenWorkbench = typeof onOpenWorkbench === "function";
    const top = useMemo_ea(() => {
      return gens.filter((g) => g.gen_no >= 0).slice().sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, topN);
    }, [gens, topN]);
    const openInWorkbench = useCallback_ea((genNo) => {
      const detail = { run_id: runId, gen_no: genNo };
      try {
        window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
        localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
      } catch (e) {
      }
      if (typeof onOpenWorkbench === "function") onOpenWorkbench(detail);
    }, [runId, onOpenWorkbench]);
    if (top.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono", style: { padding: "16px 4px", color: "var(--ink-3)", fontSize: 12 } }, "\uC0C1\uC704 \uC138\uB300\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4");
    }
    return /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement("table", { className: "mono", style: { width: "100%", borderCollapse: "collapse", fontSize: 11.5 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", { style: { color: "var(--ink-2)", textAlign: "right" } }, /* @__PURE__ */ React.createElement("th", { style: { textAlign: "left", padding: "6px 8px" } }, "gen"), /* @__PURE__ */ React.createElement("th", { style: { padding: "6px 8px" } }, "score"), /* @__PURE__ */ React.createElement("th", { style: { padding: "6px 8px" } }, "\uC190\uC775"), /* @__PURE__ */ React.createElement("th", { style: { padding: "6px 8px" } }, "MDD"), /* @__PURE__ */ React.createElement("th", { style: { padding: "6px 8px" } }, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", { style: { textAlign: "center", padding: "6px 8px" } }, "\uAC8C\uC774\uD2B8"), /* @__PURE__ */ React.createElement("th", { style: { padding: "6px 8px" } }))), /* @__PURE__ */ React.createElement("tbody", null, top.map((g) => /* @__PURE__ */ React.createElement("tr", { key: g.gen_no, style: { borderTop: "1px solid var(--line-1)", textAlign: "right" } }, /* @__PURE__ */ React.createElement("td", { style: { textAlign: "left", padding: "6px 8px", color: "var(--ink-0)" } }, "gen_", String(g.gen_no).padStart(2, "0")), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", color: "var(--teal)" } }, _fScore(g.score)), /* @__PURE__ */ React.createElement(
      "td",
      {
        style: { padding: "6px 8px" },
        className: g.profit > 0 ? "num-pos" : g.profit < 0 ? "num-neg" : ""
      },
      _fMoney(g.profit)
    ), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", color: "var(--red)" } }, _fPct(g.mdd)), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px" } }, _fInt(g.trade_count)), /* @__PURE__ */ React.createElement("td", { style: {
      textAlign: "center",
      padding: "6px 8px",
      color: g.gate_passed ? "var(--teal)" : "var(--ink-3)"
    } }, g.gate_passed ? "\u2713" : "\u2014"), /* @__PURE__ */ React.createElement("td", { style: { padding: "6px 8px", textAlign: "center" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        disabled: !g.has_csv || !canOpenWorkbench,
        "data-tip": !canOpenWorkbench ? "\uC6CC\uD06C\uBCA4\uCE58 \uC5F0\uB3D9\uC774 \uBE44\uD65C\uC131\uD654\uB428(\uD0ED \uC804\uD658 \uCF5C\uBC31 \uC5C6\uC74C)" : g.has_csv ? "\uBC31\uD14C\uC2A4\uD2B8 \uD0ED\uC5D0\uC11C \uC774 \uC138\uB300 \uACB0\uACFC\uB97C \uC0C1\uC138 \uBD84\uC11D" : "\uACB0\uACFC CSV \uAC00 \uC5C6\uC5B4 \uC0C1\uC138 \uBD84\uC11D \uBD88\uAC00",
        onClick: () => openInWorkbench(g.gen_no)
      },
      "\uC6CC\uD06C\uBCA4\uCE58 \uBD84\uC11D"
    )))))));
  }
  function EvolutionAnalysisPanel({ baseUrl, wsStatus, runId, onOpenWorkbench }) {
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const [runList, setRunList] = useState_ea([]);
    const [selRun, setSelRun] = useState_ea(runId || "");
    const [gens, setGens] = useState_ea([]);
    const [loading, setLoading] = useState_ea(false);
    const [normalize, setNormalize] = useState_ea(true);
    useEffect_ea(() => {
      if (runId && !selRun) setSelRun(runId);
    }, [runId]);
    useEffect_ea(() => {
      if (isDemo || !baseUrl) {
        setRunList([]);
        return;
      }
      let cancelled = false;
      _eaFetchJson(baseUrl + "/runs", 3e3).then((j) => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      }).catch(() => {
        if (!cancelled) setRunList([]);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo]);
    useEffect_ea(() => {
      const rid = selRun || runId || "";
      if (isDemo || !baseUrl || !rid) {
        setGens([]);
        return;
      }
      let cancelled = false;
      setLoading(true);
      _eaFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(rid), 8e3).then((j) => {
        if (cancelled) return;
        setGens(Array.isArray(j && j.items) ? j.items : []);
      }).catch(() => {
        if (!cancelled) setGens([]);
      }).finally(() => {
        if (!cancelled) setLoading(false);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemo, selRun, runId]);
    const summary = useMemo_ea(() => {
      const nums = gens.filter((g) => g.gen_no >= 0);
      if (!nums.length) return null;
      const gate = nums.filter((g) => g.gate_passed).length;
      const best = nums.reduce((a, b) => (b.score || 0) > (a.score || 0) ? b : a, nums[0]);
      const bestProfit = nums.reduce((a, b) => (b.profit || 0) > (a.profit || 0) ? b : a, nums[0]);
      return { count: nums.length, gate, best, bestProfit };
    }, [gens]);
    const effRun = selRun || runId || "";
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "\uC9C4\uD654 \uACB0\uACFC \uBD84\uC11D \u2014 Generation Analytics"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "center" } }, /* @__PURE__ */ React.createElement(
      "select",
      {
        value: effRun,
        onChange: (e) => setSelRun(e.target.value),
        disabled: isDemo,
        className: "mono",
        "data-tip": "\uBD84\uC11D\uD560 run \uC120\uD0DD(\uAE30\uBCF8 \uD604\uC7AC run)",
        style: {
          fontSize: 11,
          background: "var(--bg-1)",
          color: "var(--ink-0)",
          border: "1px solid var(--line-2)",
          borderRadius: 5,
          padding: "3px 6px",
          maxWidth: 240
        }
      },
      effRun && !runList.some((r) => r.run_id === effRun) && /* @__PURE__ */ React.createElement("option", { value: effRun }, effRun, " (\uD604\uC7AC)"),
      (runList || []).map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : "", r.gate_passed_count > 0 ? " \u2713" : ""))
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { padding: "20px 4px", color: "var(--ink-3)", fontSize: 12 } }, "\uB370\uBAA8(\uBBF8\uC5F0\uACB0) \uBAA8\uB4DC \u2014 \uC2E4 run \uC5D0 \uC5F0\uACB0\uD558\uBA74 \uC138\uB300 \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : !effRun ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { padding: "20px 4px", color: "var(--ink-3)", fontSize: 12 } }, "run \uC744 \uC120\uD0DD\uD558\uBA74 \uC138\uB300 \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4.") : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(Mini, { label: "\uC138\uB300 \uC218", value: summary ? _fInt(summary.count) : "\u2014" }), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uAC8C\uC774\uD2B8 \uD1B5\uACFC",
        value: summary ? `${summary.gate} / ${summary.count}` : "\u2014",
        color: summary && summary.gate > 0 ? "var(--teal)" : void 0
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uACE0 \uC810\uC218",
        value: summary ? _fScore(summary.best.score) : "\u2014",
        sub: summary ? `gen_${summary.best.gen_no}` : ""
      }
    ), /* @__PURE__ */ React.createElement(
      Mini,
      {
        label: "\uCD5C\uB300 \uC190\uC775",
        value: summary ? _fMoney(summary.bestProfit.profit) : "\u2014",
        sub: summary ? `gen_${summary.bestProfit.gen_no}` : ""
      }
    )), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center", margin: "6px 0 8px" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" } }, EA_SERIES.map((s) => /* @__PURE__ */ React.createElement(LegendDot, { key: s.key, color: s.color, label: s.label }))), /* @__PURE__ */ React.createElement("label", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", display: "flex", alignItems: "center", gap: 6, cursor: "pointer" } }, /* @__PURE__ */ React.createElement("input", { type: "checkbox", checked: normalize, onChange: (e) => setNormalize(e.target.checked) }), "\uC815\uADDC\uD654(0~1)")), /* @__PURE__ */ React.createElement(EaMultiMetricChart, { gens, normalize }), !normalize && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", marginTop: 4 } }, "\uC815\uADDC\uD654 OFF \u2014 \uC2A4\uCF00\uC77C\uC774 \uB2E4\uB978 \uACC4\uC5F4\uC740 \uACB9\uCCD0 \uBE44\uAD50\uAC00 \uC5B4\uB824\uC6CC score \uB9CC \uC6D0\uCD95\uC73C\uB85C \uD45C\uC2DC\uD569\uB2C8\uB2E4."), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, alignItems: "center", margin: "16px 0 8px" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", letterSpacing: ".08em" } }, "\uC138\uB300 \uC0B0\uC810\uB3C4 \u2014 MDD \xD7 \uC190\uC775(\uB2C8\uCE58 \uC9C0\uB3C4)"), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--teal)", label: "\uAC8C\uC774\uD2B8 \uD1B5\uACFC", filled: "ring" }), /* @__PURE__ */ React.createElement(LegendDot, { color: "var(--ink-3)", label: "\uAC8C\uC774\uD2B8 \uD0C8\uB77D(\uD750\uB9B0 \uC810)" })), /* @__PURE__ */ React.createElement(EaScatterChart, { gens }), /* @__PURE__ */ React.createElement("div", { style: { margin: "16px 0 8px" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", letterSpacing: ".08em" } }, "\uC0C1\uC704 \uC138\uB300 \u2014 score \uB0B4\uB9BC\uCC28\uC21C(\uC6CC\uD06C\uBCA4\uCE58 \uBD84\uC11D\uC73C\uB85C \uBC31\uD14C \uD0ED \uC5F0\uB3D9)")), /* @__PURE__ */ React.createElement(EaTopTable, { runId: effRun, gens, topN: 8, onOpenWorkbench }), loading && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginTop: 8 } }, "\uBD88\uB7EC\uC624\uB294 \uC911\u2026"))));
  }
  Object.assign(window, { EvolutionAnalysisPanel });

  // ../frontend/analysis.jsx
  var {
    useState: useState_an,
    useEffect: useEffect_an,
    useCallback: useCallback_an,
    useMemo: useMemo_an
  } = React;
  function _anNum(x, digits) {
    if (typeof x !== "number" || !isFinite(x)) return "\u2014";
    return x.toFixed(digits != null ? digits : 3);
  }
  function _edgeColor(v, alpha) {
    if (typeof v !== "number" || !isFinite(v)) return `rgba(80,100,120,${alpha || 0.5})`;
    const delta = v - 1;
    if (delta >= 0) {
      const t = Math.min(1, delta);
      const r = Math.round(20 + (1 - t) * 80);
      const g = Math.round(100 + t * 114);
      const b = Math.round(100 + t * 79);
      return `rgba(${r},${g},${b},${alpha || 0.85})`;
    } else {
      const t = Math.min(1, -delta);
      const r = Math.round(200 + t * 55);
      const g = Math.round(Math.round(179 * (1 - t)));
      return `rgba(${r},${g},40,${alpha || 0.85})`;
    }
  }
  function _cohensColor(d) {
    if (typeof d !== "number" || !isFinite(d)) return "var(--ink-3)";
    return d >= 0 ? "var(--teal)" : "var(--amber)";
  }
  function _EmptyState({ msg }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      padding: "28px 18px",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)",
      lineHeight: 1.7,
      textAlign: "center"
    } }, msg);
  }
  function EdgeRatioPanel({ baseUrl, wsStatus, runId }) {
    const [data, setData] = useState_an(null);
    const [loading, setLoading] = useState_an(false);
    const [err, setErr] = useState_an(null);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const refresh = useCallback_an(() => {
      if (isDemo || !baseUrl || !runId) return;
      setLoading(true);
      const url = baseUrl + "/edge_ratio?run_ids=" + encodeURIComponent(runId) + "&fine_time=true";
      fetch(url, { signal: AbortSignal.timeout(5e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId]);
    useEffect_an(() => {
      refresh();
      const id = setInterval(refresh, 3e4);
      return () => clearInterval(id);
    }, [refresh]);
    const global_ = data && data.global || {};
    const segs = data && data.segments || {};
    const crossSegs = segs.cross || [];
    const changeSegs = segs.change || [];
    const timeSegs = segs.time || [];
    const capSegs = segs.market_cap || [];
    const heatmap = useMemo_an(() => {
      if (!crossSegs.length) return null;
      const timeLabels = [];
      const capLabels = [];
      const cellMap = {};
      for (const c of crossSegs) {
        const parts = (c.label || "").split("\xD7");
        const tl = parts[0] ? parts[0].trim() : c.label;
        const cl = parts[1] ? parts[1].trim() : "";
        if (!timeLabels.includes(tl)) timeLabels.push(tl);
        if (cl && !capLabels.includes(cl)) capLabels.push(cl);
        cellMap[tl + "\xD7" + cl] = c;
      }
      if (capLabels.length === 0) return null;
      return { timeLabels, capLabels, cellMap };
    }, [crossSegs]);
    const hasData = data && (typeof global_.edge_ratio === "number" || crossSegs.length > 0 || changeSegs.length > 0);
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "Edge Ratio \uBD84\uC11D", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC2DC\uAC04\uB300\xD7\uC2DC\uCD1D \uD788\uD2B8\uB9F5 \xB7 \uB4F1\uB77D\uB960 \uCD95"), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: refresh,
        disabled: isDemo || loading || !runId,
        "data-tip": "edge_ratio \uC0C8\uB85C\uACE0\uCE68"
      },
      loading ? "\uC870\uD68C\uC911\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uB370\uBAA8 \uBAA8\uB4DC \u2014 Edge Ratio \uBD84\uC11D\uC740 \uB77C\uC774\uBE0C \uC2E4\uD589\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." }) : !runId ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "run\uC744 \uC120\uD0DD\uD558\uAC70\uB098 \uB8E8\uD504\uB97C \uC2DC\uC791\uD558\uBA74 Edge Ratio \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4." }) : err ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uC870\uD68C \uC2E4\uD328 \u2014 " + err }) : !hasData ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 Edge Ratio \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4." + (loading ? " (\uB85C\uB529\uC911\u2026)" : "") }) : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 16 } }, (typeof global_.edge_ratio === "number" || typeof global_.mae_efficiency === "number") && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 8, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uAE00\uB85C\uBC8C \uC9C0\uD45C"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 20, flexWrap: "wrap" } }, typeof global_.edge_ratio === "number" && /* @__PURE__ */ React.createElement(
      _EdgeStat,
      {
        label: "Edge Ratio",
        value: _anNum(global_.edge_ratio, 3),
        color: _edgeColor(global_.edge_ratio, 1),
        hint: "1.0 \uAE30\uC900: \uB192\uC744\uC218\uB85D \uC720\uB9AC"
      }
    ), typeof global_.mae_efficiency === "number" && /* @__PURE__ */ React.createElement(
      _EdgeStat,
      {
        label: "MAE Efficiency",
        value: _anNum(global_.mae_efficiency, 3),
        color: global_.mae_efficiency >= 0 ? "var(--teal)" : "var(--amber)",
        hint: "\uD3C9\uADE0 \uBD88\uB9AC \uB178\uCD9C \uD6A8\uC728(\uB192\uC744\uC218\uB85D \uC801\uC740 \uC5ED\uBC29\uD5A5 \uB178\uCD9C)"
      }
    ), typeof global_.win_rate === "number" && /* @__PURE__ */ React.createElement(
      _EdgeStat,
      {
        label: "\uC2B9\uB960",
        value: _anNum(global_.win_rate * 100, 1) + "%",
        color: "var(--ink-0)"
      }
    ), typeof global_.trade_count === "number" && /* @__PURE__ */ React.createElement(_EdgeStat, { label: "\uAC70\uB798\uC218", value: String(global_.trade_count), color: "var(--ink-2)" }))), heatmap ? /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 8, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uC2DC\uAC04\uB300 \xD7 \uC2DC\uCD1D \uAD50\uCC28 \uD788\uD2B8\uB9F5 (edge_ratio \xB7 1.0 \uAE30\uC900 \uBC1C\uC0B0\uC0C9)"), /* @__PURE__ */ React.createElement(_Heatmap, { heatmap })) : crossSegs.length > 0 ? (
      /* fallback: cross 목록 */
      /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uAD50\uCC28 \uC138\uADF8\uBA3C\uD2B8"), /* @__PURE__ */ React.createElement(_SegBarList, { segs: crossSegs }))
    ) : null, changeSegs.length > 0 && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uB4F1\uB77D\uB960 \uAD6C\uAC04\uBCC4 edge_ratio"), /* @__PURE__ */ React.createElement(_SegBarList, { segs: changeSegs })), !crossSegs.length && timeSegs.length > 0 && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uC2DC\uAC04\uB300\uBCC4 edge_ratio"), /* @__PURE__ */ React.createElement(_SegBarList, { segs: timeSegs })), !crossSegs.length && capSegs.length > 0 && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" } }, "\uC2DC\uCD1D \uBC34\uB4DC\uBCC4 edge_ratio"), /* @__PURE__ */ React.createElement(_SegBarList, { segs: capSegs })))));
  }
  function _EdgeStat({ label, value, color, hint }) {
    return /* @__PURE__ */ React.createElement(
      "div",
      {
        style: { display: "flex", flexDirection: "column", gap: 2 },
        title: hint || ""
      },
      /* @__PURE__ */ React.createElement("span", { style: { fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", fontFamily: "var(--mono)" } }, label),
      /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 18, color: color || "var(--ink-0)" } }, value)
    );
  }
  function _Heatmap({ heatmap }) {
    const { timeLabels, capLabels, cellMap } = heatmap;
    const cellW = 72, cellH = 30;
    const labelColW = 80, labelRowH = 26;
    const W = labelColW + capLabels.length * cellW;
    const H = labelRowH + timeLabels.length * cellH;
    return /* @__PURE__ */ React.createElement("div", { style: { overflowX: "auto" } }, /* @__PURE__ */ React.createElement(
      "svg",
      {
        viewBox: `0 0 ${W} ${H}`,
        style: { width: "100%", maxWidth: W, display: "block" },
        preserveAspectRatio: "xMinYMin meet"
      },
      capLabels.map((cl, ci) => /* @__PURE__ */ React.createElement(
        "text",
        {
          key: "ch" + ci,
          x: labelColW + ci * cellW + cellW / 2,
          y: labelRowH - 6,
          textAnchor: "middle",
          style: { fontSize: 9, fill: "var(--ink-3)", fontFamily: "var(--mono)" }
        },
        cl.length > 8 ? cl.slice(0, 8) + "\u2026" : cl
      )),
      timeLabels.map((tl, ti) => /* @__PURE__ */ React.createElement("g", { key: "tr" + ti }, /* @__PURE__ */ React.createElement(
        "text",
        {
          x: labelColW - 4,
          y: labelRowH + ti * cellH + cellH / 2 + 4,
          textAnchor: "end",
          style: { fontSize: 9.5, fill: "var(--ink-2)", fontFamily: "var(--mono)" }
        },
        tl.length > 9 ? tl.slice(0, 9) + "\u2026" : tl
      ), capLabels.map((cl, ci) => {
        const cell = cellMap[tl + "\xD7" + cl];
        const er = cell ? cell.edge_ratio : null;
        const bg = er != null ? _edgeColor(er, 0.82) : "rgba(40,50,60,0.4)";
        const textColor = er != null ? Math.abs(er - 1) > 0.15 ? "#fff" : "var(--ink-1)" : "var(--ink-3)";
        const cx = labelColW + ci * cellW;
        const cy = labelRowH + ti * cellH;
        return /* @__PURE__ */ React.createElement("g", { key: "c" + ci }, /* @__PURE__ */ React.createElement(
          "rect",
          {
            x: cx + 1,
            y: cy + 1,
            width: cellW - 2,
            height: cellH - 2,
            rx: "3",
            fill: bg
          }
        ), /* @__PURE__ */ React.createElement(
          "text",
          {
            x: cx + cellW / 2,
            y: cy + cellH / 2 + 4,
            textAnchor: "middle",
            style: { fontSize: 9.5, fill: textColor, fontFamily: "var(--mono)", fontWeight: 600 }
          },
          er != null ? _anNum(er, 2) : "\u2014"
        ), cell && typeof cell.count === "number" && /* @__PURE__ */ React.createElement(
          "text",
          {
            x: cx + cellW / 2,
            y: cy + cellH - 4,
            textAnchor: "middle",
            style: { fontSize: 7.5, fill: "rgba(255,255,255,0.45)", fontFamily: "var(--mono)" }
          },
          cell.count,
          "\uAC74"
        ));
      })))
    ));
  }
  function _SegBarList({ segs }) {
    if (!segs || !segs.length) return null;
    const maxAbsDelta = segs.reduce((m, s) => {
      const d = typeof s.edge_ratio === "number" ? Math.abs(s.edge_ratio - 1) : 0;
      return Math.max(m, d);
    }, 0.01);
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 5 } }, segs.map((s, i) => {
      const er = typeof s.edge_ratio === "number" ? s.edge_ratio : null;
      const delta = er != null ? er - 1 : 0;
      const barFrac = er != null ? Math.abs(delta) / (maxAbsDelta || 1) : 0;
      const barW = Math.max(2, Math.round(barFrac * 120));
      const barColor = _edgeColor(er != null ? er : 1, 0.85);
      return /* @__PURE__ */ React.createElement("div", { key: i, style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: "var(--ink-2)", minWidth: 90, flexShrink: 0 } }, s.label || "\u2014"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 4 } }, /* @__PURE__ */ React.createElement("div", { style: {
        width: barW,
        height: 12,
        borderRadius: 3,
        background: barColor,
        flexShrink: 0
      } }), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 11, color: barColor, minWidth: 42 } }, er != null ? _anNum(er, 3) : "\u2014")), typeof s.win_rate === "number" && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, "\uC2B9\uB960 ", _anNum(s.win_rate * 100, 1), "%"), typeof s.count === "number" && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)" } }, s.count, "\uAC74"));
    }));
  }
  function FeatureImportancePanel({ baseUrl, wsStatus, runId }) {
    const [data, setData] = useState_an(null);
    const [loading, setLoading] = useState_an(false);
    const [err, setErr] = useState_an(null);
    const [axis, setAxis] = useState_an("time");
    const [selSeg, setSelSeg] = useState_an(null);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const refresh = useCallback_an(() => {
      if (isDemo || !baseUrl || !runId) return;
      setLoading(true);
      const url = baseUrl + "/feature_importance?run_ids=" + encodeURIComponent(runId) + "&axis=" + encodeURIComponent(axis) + "&fine_time=true";
      fetch(url, { signal: AbortSignal.timeout(5e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
        setSelSeg(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId, axis]);
    useEffect_an(() => {
      refresh();
      const id = setInterval(refresh, 3e4);
      return () => clearInterval(id);
    }, [refresh]);
    const globalFeats = data && Array.isArray(data.global) ? data.global : [];
    const bySeg = data && data.by_segment ? data.by_segment : {};
    const segKeys = Object.keys(bySeg);
    const activeFeats = useMemo_an(() => {
      const raw = selSeg && bySeg[selSeg] ? bySeg[selSeg] : globalFeats;
      return [...raw].sort((a, b) => Math.abs(b.cohens_d || 0) - Math.abs(a.cohens_d || 0));
    }, [selSeg, bySeg, globalFeats]);
    const maxAbsD = activeFeats.reduce((m, f) => Math.max(m, Math.abs(f.cohens_d || 0)), 0.01);
    const hasData = data && (globalFeats.length > 0 || segKeys.length > 0);
    const _AxisBtn = ({ val, label }) => /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => {
          setAxis(val);
          setSelSeg(null);
        },
        className: "btn ghost sm",
        style: {
          fontFamily: "var(--mono)",
          fontSize: 10.5,
          padding: "3px 9px",
          background: axis === val ? "rgba(76,214,179,0.12)" : "transparent",
          border: axis === val ? "1px solid var(--teal)" : "1px solid var(--line-2)",
          color: axis === val ? "var(--teal)" : "var(--ink-3)"
        }
      },
      label
    );
    return /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--violet)" } }), "Feature Importance \uBD84\uC11D", isDemo && typeof window.DemoBadge === "function" && /* @__PURE__ */ React.createElement(window.DemoBadge, null)), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(_AxisBtn, { val: "time", label: "\uC2DC\uAC04\uB300" }), /* @__PURE__ */ React.createElement(_AxisBtn, { val: "market_cap", label: "\uC2DC\uCD1D" }), /* @__PURE__ */ React.createElement(_AxisBtn, { val: "change", label: "\uB4F1\uB77D\uB960" }), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: refresh,
        disabled: isDemo || loading || !runId,
        "data-tip": "feature importance \uC0C8\uB85C\uACE0\uCE68"
      },
      loading ? "\uC870\uD68C\uC911\u2026" : "\u21BB \uC0C8\uB85C\uACE0\uCE68"
    ))), /* @__PURE__ */ React.createElement("div", { className: "panel-bd" }, isDemo ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uB370\uBAA8 \uBAA8\uB4DC \u2014 Feature Importance \uBD84\uC11D\uC740 \uB77C\uC774\uBE0C \uC2E4\uD589\uC5D0\uC11C \uBC1C\uD589\uB429\uB2C8\uB2E4." }) : !runId ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "run\uC744 \uC120\uD0DD\uD558\uAC70\uB098 \uB8E8\uD504\uB97C \uC2DC\uC791\uD558\uBA74 Feature Importance \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4." }) : err ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uC870\uD68C \uC2E4\uD328 \u2014 " + err }) : !hasData ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uC138\uB300 \uB370\uC774\uD130\uAC00 \uB204\uC801\uB418\uBA74 Feature Importance \uBD84\uC11D\uC774 \uD45C\uC2DC\uB429\uB2C8\uB2E4." + (loading ? " (\uB85C\uB529\uC911\u2026)" : "") }) : /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 12 } }, segKeys.length > 0 && /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 6, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(
      "button",
      {
        onClick: () => setSelSeg(null),
        className: "btn ghost sm",
        style: {
          fontFamily: "var(--mono)",
          fontSize: 10.5,
          padding: "2px 8px",
          background: selSeg === null ? "rgba(165,148,255,0.12)" : "transparent",
          border: selSeg === null ? "1px solid var(--violet)" : "1px solid var(--line-2)",
          color: selSeg === null ? "var(--violet)" : "var(--ink-3)"
        }
      },
      "\uC804\uCCB4"
    ), segKeys.map((k) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: k,
        onClick: () => setSelSeg(k),
        className: "btn ghost sm",
        style: {
          fontFamily: "var(--mono)",
          fontSize: 10.5,
          padding: "2px 8px",
          background: selSeg === k ? "rgba(165,148,255,0.12)" : "transparent",
          border: selSeg === k ? "1px solid var(--violet)" : "1px solid var(--line-2)",
          color: selSeg === k ? "var(--violet)" : "var(--ink-3)"
        }
      },
      k.length > 14 ? k.slice(0, 14) + "\u2026" : k
    ))), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" } }, "Cohen's d: \uD1B5\uACFC/\uD0C8\uB77D \uC138\uB300 \uAC04 \uD53C\uCC98 \uBD84\uD3EC \uCC28\uC774. \uC591(teal)=\uD1B5\uACFC\uC138\uB300 \uB354 \uB192\uC74C, \uC74C(amber)=\uB0AE\uC744\uC218\uB85D \uD1B5\uACFC. |d|\u2193 \uC815\uB82C."), activeFeats.length === 0 ? /* @__PURE__ */ React.createElement(_EmptyState, { msg: "\uC774 \uC138\uADF8\uBA3C\uD2B8\uC5D0 \uD53C\uCC98 \uB370\uC774\uD130\uAC00 \uC5C6\uC2B5\uB2C8\uB2E4." }) : /* @__PURE__ */ React.createElement(_FeatureBarChart, { feats: activeFeats, maxAbsD }))));
  }
  function _FeatureBarChart({ feats, maxAbsD }) {
    const BAR_MAX_W = 180;
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 4 } }, feats.map((f, i) => {
      const d = typeof f.cohens_d === "number" ? f.cohens_d : 0;
      const absD = Math.abs(d);
      const frac = absD / (maxAbsD || 1);
      const barW = Math.max(2, Math.round(frac * BAR_MAX_W));
      const barColor = _cohensColor(d);
      const featureLabel = f.feature || f.name || "feature_" + i;
      return /* @__PURE__ */ React.createElement("div", { key: i, style: {
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "3px 0",
        borderBottom: i < feats.length - 1 ? "1px solid var(--bg-2)" : "none"
      } }, /* @__PURE__ */ React.createElement(
        "span",
        {
          className: "mono",
          style: {
            fontSize: 11,
            color: "var(--ink-1)",
            minWidth: 140,
            maxWidth: 180,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            flexShrink: 0
          },
          title: featureLabel
        },
        featureLabel
      ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 2, minWidth: BAR_MAX_W * 2 + 10 } }, /* @__PURE__ */ React.createElement("div", { style: { width: BAR_MAX_W, display: "flex", justifyContent: "flex-end" } }, d < 0 && /* @__PURE__ */ React.createElement("div", { style: {
        width: barW,
        height: 12,
        borderRadius: "3px 0 0 3px",
        background: barColor,
        opacity: 0.85
      } })), /* @__PURE__ */ React.createElement("div", { style: { width: 1, height: 14, background: "var(--line-2)", flexShrink: 0 } }), /* @__PURE__ */ React.createElement("div", { style: { width: BAR_MAX_W } }, d >= 0 && /* @__PURE__ */ React.createElement("div", { style: {
        width: barW,
        height: 12,
        borderRadius: "0 3px 3px 0",
        background: barColor,
        opacity: 0.85
      } }))), /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
        fontSize: 11,
        color: barColor,
        minWidth: 52,
        textAlign: "right"
      } }, d >= 0 ? "+" : "", _anNum(d, 3)), typeof f.mean_pass === "number" && typeof f.mean_fail === "number" && /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)" } }, "\uD1B5\uACFC ", _anNum(f.mean_pass, 2), " / \uD0C8\uB77D ", _anNum(f.mean_fail, 2)));
    }));
  }
  Object.assign(window, { EdgeRatioPanel, FeatureImportancePanel });

  // ../frontend/research-lab.jsx
  var {
    useState: useState_rl,
    useEffect: useEffect_rl,
    useCallback: useCallback_rl,
    useMemo: useMemo_rl
  } = React;
  var _VDT_STATUS_ICON = { pass: "\u2705", warn: "\u26A0\uFE0F", fail: "\u274C", pending: "\u23F3" };
  function VdtPromoteChecklist({ v }) {
    const checks = v && v.promote_checklist || [];
    if (checks.length === 0) {
      return /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6 } }, "PROMOTE \uCCB4\uD06C\uB9AC\uC2A4\uD2B8: \uB370\uC774\uD130 \uC5C6\uC74C");
    }
    return /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 12, width: "100%", marginBottom: 8 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "PROMOTE \uC870\uAC74"), /* @__PURE__ */ React.createElement("th", null, "\uC0C1\uD0DC"), /* @__PURE__ */ React.createElement("th", null, "\uADFC\uAC70"))), /* @__PURE__ */ React.createElement("tbody", null, checks.map((c, i) => /* @__PURE__ */ React.createElement("tr", { key: "vdtc" + i }, /* @__PURE__ */ React.createElement("td", null, c.item), /* @__PURE__ */ React.createElement("td", null, _VDT_STATUS_ICON[c.status] || "?"), /* @__PURE__ */ React.createElement("td", null, c.detail || "\u2014")))));
  }
  function VdtAlerts({ v }) {
    const alerts = v && v.alerts || [];
    return alerts.map((a, i) => /* @__PURE__ */ React.createElement("div", { key: "vdta" + i, className: "mono", style: { fontSize: 12, color: "var(--amber)" } }, "\u26A0\uFE0F ", a));
  }
  function VdtSummaryLines({ v }) {
    const lines = v && v.lines || [];
    return lines.map((l, i) => /* @__PURE__ */ React.createElement("div", { key: "vdtl" + i, className: "mono", style: { fontSize: 12 } }, l));
  }
  Object.assign(window, { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines });
  var RESEARCH_TABS = [
    { id: "edge", label: "\uC5E3\uC9C0(\uC2B9\uB960\xB7\uAE30\uB300\uAC12)" },
    { id: "feature", label: "\uBCC0\uC218 \uC911\uC694\uB3C4" },
    { id: "correlation", label: "\uC0C1\uAD00\uAD00\uACC4" },
    { id: "combos", label: "\uBCC0\uC218 \uC870\uD569" },
    { id: "validation", label: "\uAC80\uC99D" }
  ];
  function _rlNum(value, digits) {
    if (typeof value !== "number" || !isFinite(value)) return "--";
    return value.toFixed(digits == null ? 3 : digits);
  }
  function _rlYmd(v) {
    const n = typeof v === "number" ? v : parseInt(v, 10);
    if (!isFinite(n) || n < 19000101 || n > 21001231) return null;
    const y = Math.floor(n / 1e4);
    const m = Math.floor(n % 1e4 / 100);
    const d = n % 100;
    if (m < 1 || m > 12 || d < 1 || d > 31) return null;
    return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  }
  function _rlPeriodFromDays(days) {
    if (!Array.isArray(days) || days.length === 0) return "\uAE30\uAC04 \uC815\uBCF4 \uC5C6\uC74C";
    const s = _rlYmd(days[0]);
    const e = _rlYmd(days[days.length - 1]);
    if (!s || !e) return "\uAE30\uAC04 \uC815\uBCF4 \uC5C6\uC74C";
    return s === e ? s : `${s} ~ ${e}`;
  }
  function _rlCorrColor(value) {
    if (typeof value !== "number" || !isFinite(value)) {
      return "color-mix(in srgb, var(--ink-2) 42%, transparent)";
    }
    const t = Math.min(1, Math.abs(value));
    const pct = Math.round(22 + 64 * t);
    const token = value >= 0 ? "var(--teal)" : "var(--red)";
    return `color-mix(in srgb, ${token} ${pct}%, transparent)`;
  }
  function _ResearchEmptyState({ message }) {
    return /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, message || "\uC120\uD0DD\uD55C \uB9AC\uC11C\uCE58 \uD654\uBA74\uC5D0 \uD45C\uC2DC\uD560 \uB370\uC774\uD130\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4.");
  }
  function _CorrelationControls({ method, setMethod, axis, setAxis, loading, pooledTrades, featureCount }) {
    return /* @__PURE__ */ React.createElement("div", { className: "research-controls" }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "method"), /* @__PURE__ */ React.createElement("select", { value: method, onChange: (e) => setMethod(e.target.value), disabled: loading }, /* @__PURE__ */ React.createElement("option", { value: "pearson" }, "pearson"), /* @__PURE__ */ React.createElement("option", { value: "spearman" }, "spearman"))), /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "segment axis"), /* @__PURE__ */ React.createElement("select", { value: axis, onChange: (e) => setAxis(e.target.value) }, /* @__PURE__ */ React.createElement("option", { value: "time" }, "time"), /* @__PURE__ */ React.createElement("option", { value: "market_cap" }, "market_cap"), /* @__PURE__ */ React.createElement("option", { value: "change" }, "change"))), /* @__PURE__ */ React.createElement("div", { className: "research-kpis" }, /* @__PURE__ */ React.createElement("span", null, "sample count ", _rlNum(pooledTrades, 0)), /* @__PURE__ */ React.createElement("span", null, "features ", _rlNum(featureCount, 0))));
  }
  function _CorrelationHeatmap({ rows }) {
    if (!rows || rows.length === 0) {
      return /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC0C1\uAD00 \uD788\uD2B8\uB9F5\uC744 \uADF8\uB9B4 feature_matrix \uD589\uC774 \uBD80\uC871\uD569\uB2C8\uB2E4." });
    }
    return /* @__PURE__ */ React.createElement("div", { className: "research-heatmap" }, rows.slice(0, 36).map((row, i) => {
      const label = [row.feature_a, row.feature_b].filter(Boolean).join(" / ") || row.feature || "feature_" + i;
      const corr = typeof row.correlation === "number" ? row.correlation : null;
      return /* @__PURE__ */ React.createElement(
        "div",
        {
          key: i,
          className: "research-cell",
          style: { background: _rlCorrColor(corr) },
          title: `${label} | correlation ${_rlNum(corr, 4)} | sample count ${row.n || 0}`
        },
        /* @__PURE__ */ React.createElement("strong", null, label),
        /* @__PURE__ */ React.createElement("span", null, _rlNum(corr, 3)),
        /* @__PURE__ */ React.createElement("small", null, "n=", row.n || 0)
      );
    }));
  }
  var _COMBO_MAX_FEATURES = 10;
  function _combinationMatrix(rows) {
    const score = {};
    const cellMap = {};
    rows.forEach((row) => {
      const a = row.feature_a || row.feature;
      const b = row.feature_b;
      if (!a || !b || a === b) return;
      const corr = typeof row.correlation === "number" ? row.correlation : null;
      const val = typeof row.research_score === "number" ? row.research_score : corr;
      if (val == null) return;
      const n = row.sample_count || row.n || 0;
      const w = Math.abs(val);
      score[a] = (score[a] || 0) + w;
      score[b] = (score[b] || 0) + w;
      cellMap[a + "|" + b] = { score: val, n };
      cellMap[b + "|" + a] = { score: val, n };
    });
    const features = Object.keys(score).sort((x, y) => score[y] - score[x]).slice(0, _COMBO_MAX_FEATURES);
    return { features, cellMap };
  }
  var _COMBO_MIN_SAMPLE = 30;
  function _rlPairInterpret(score, n) {
    const v = typeof score === "number" && isFinite(score) ? score : null;
    if (v == null) {
      return { sign: "\u2014", strength: "\uD574\uC11D \uBD88\uAC00", line: "\uAC12\uC774 \uC5C6\uC5B4 \uC0C1\uD638\uC791\uC6A9\uC744 \uD574\uC11D\uD560 \uC218 \uC5C6\uC2B5\uB2C8\uB2E4." };
    }
    const a = Math.abs(v);
    const sign = v >= 0 ? "\uC591(+)" : "\uC74C(-)";
    const strength = a >= 0.5 ? "\uAC15\uD568" : a >= 0.3 ? "\uC911\uAC04" : a >= 0.1 ? "\uC57D\uD568" : "\uBBF8\uBBF8";
    const lowSample = (n || 0) < _COMBO_MIN_SAMPLE;
    let line;
    if (a >= 0.5) {
      line = v >= 0 ? "\uAC15\uD55C \uC591\uC758 \uC0C1\uD638\uC791\uC6A9 \u2014 \uB450 \uBCC0\uC218\uAC00 \uD568\uAED8 \uB192\uC744 \uB54C \uC6B0\uC218\uD55C \uACBD\uD5A5." : "\uAC15\uD55C \uC74C\uC758 \uC0C1\uD638\uC791\uC6A9 \u2014 \uD55C\uCABD\uC774 \uB192\uACE0 \uB2E4\uB978 \uCABD\uC774 \uB0AE\uC744 \uB54C \uC6B0\uC218\uD55C \uACBD\uD5A5.";
    } else if (a >= 0.3) {
      line = v >= 0 ? "\uC911\uAC04 \uC591\uC758 \uC0C1\uD638\uC791\uC6A9 \u2014 \uD568\uAED8 \uC6C0\uC9C1\uC774\uB294 \uACBD\uD5A5\uC774 \uAD00\uCC30\uB429\uB2C8\uB2E4." : "\uC911\uAC04 \uC74C\uC758 \uC0C1\uD638\uC791\uC6A9 \u2014 \uBC18\uB300\uB85C \uC6C0\uC9C1\uC774\uB294 \uACBD\uD5A5\uC774 \uAD00\uCC30\uB429\uB2C8\uB2E4.";
    } else if (a >= 0.1) {
      line = "\uC57D\uD55C \uC0C1\uAD00 \u2014 \uBC29\uD5A5\uC131\uC740 \uC788\uC73C\uB098 \uC2E0\uD638\uAC00 \uC57D\uD569\uB2C8\uB2E4.";
    } else {
      line = "\uBBF8\uBBF8\uD55C \uC0C1\uAD00 \u2014 \uB450 \uBCC0\uC218\uC758 \uC0C1\uD638\uC791\uC6A9\uC774 \uAC70\uC758 \uC5C6\uC2B5\uB2C8\uB2E4.";
    }
    if (lowSample) {
      line += ` \uD45C\uBCF8 \uBD80\uC871 \uC8FC\uC758(n=${n || 0} < ${_COMBO_MIN_SAMPLE}) \u2014 \uD574\uC11D \uC2E0\uB8B0\uB3C4 \uB0AE\uC74C.`;
    }
    return { sign, strength, line, lowSample };
  }
  function _ComboPairPopover({ pair, onClose }) {
    useEffect_rl(() => {
      const onKey = (e) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);
    if (!pair) return null;
    const info = _rlPairInterpret(pair.score, pair.n);
    return /* @__PURE__ */ React.createElement("div", { className: "rp-overlay", onClick: onClose }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-card", style: { maxWidth: 460 }, onClick: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\uBCC0\uC218\uC30D \uC0C1\uC138 \u2014 ", pair.a, " \xD7 ", pair.b), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn ghost sm", style: { marginLeft: "auto" }, onClick: onClose }, "\u2715 \uB2EB\uAE30 (Esc)")), /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 18px", display: "flex", flexDirection: "column", gap: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12 } }, "\uBCC0\uC218\uC30D: ", /* @__PURE__ */ React.createElement("b", null, pair.a), " \xD7 ", /* @__PURE__ */ React.createElement("b", null, pair.b)), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12 } }, "research_score/correlation: ", /* @__PURE__ */ React.createElement("b", { style: { color: pair.score >= 0 ? "var(--teal)" : "var(--red)" } }, _rlNum(pair.score, 4)), " \xB7 ", "\uBD80\uD638 ", info.sign, " \xB7 \uAC15\uB3C4 ", info.strength), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12 } }, "sample_count: ", /* @__PURE__ */ React.createElement("b", null, pair.n || 0), info.lowSample ? /* @__PURE__ */ React.createElement("span", { style: { color: "var(--amber)" } }, " \xB7 \uD45C\uBCF8 \uBD80\uC871") : null), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { marginTop: 2 } }, info.line), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { color: "var(--ink-3)", fontSize: 11 } }, "\u203B \uB354 \uAE4A\uC740 \uBCC0\uC218\uC30D\uBCC4 \uAC70\uB798 \uBD84\uD3EC(\uC2B9\uB960\xB7\uAD6C\uAC04\uBCC4 \uC190\uC775 \uB4F1)\uB294 \uD5A5\uD6C4 \uBC31\uC5D4\uB4DC \uC5D4\uB4DC\uD3EC\uC778\uD2B8\uAC00 \uD544\uC694\uD569\uB2C8\uB2E4 \u2014 \uD604\uC7AC\uB294 \uC774 \uD654\uBA74 \uB370\uC774\uD130(score\xB7n)\uC5D0 \uC5C6\uB294 \uD1B5\uACC4\uB97C \uB9CC\uB4E4\uC5B4 \uD45C\uC2DC\uD558\uC9C0 \uC54A\uC2B5\uB2C8\uB2E4."))));
  }
  function _CombinationList({ rows }) {
    const { features, cellMap } = _combinationMatrix(rows || []);
    const [selected, setSelected] = useState_rl(null);
    if (features.length === 0) {
      return /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC120\uD0DD\uD55C run \uC5D0 \uBD84\uC11D\uD560 \uBCC0\uC218 \uC870\uD569\uC774 \uBD80\uC871\uD569\uB2C8\uB2E4." });
    }
    const N = features.length;
    const selKey = selected ? selected.a + "|" + selected.b : null;
    return /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "stom-combo-grid",
        style: { gridTemplateColumns: `auto repeat(${N}, minmax(0,1fr))` }
      },
      /* @__PURE__ */ React.createElement("div", { className: "stom-combo-axis" }),
      features.map((f) => /* @__PURE__ */ React.createElement("div", { key: "col-" + f, className: "stom-combo-axis col", title: f }, f)),
      features.map((rowF) => /* @__PURE__ */ React.createElement(React.Fragment, { key: "row-" + rowF }, /* @__PURE__ */ React.createElement("div", { className: "stom-combo-axis", title: rowF }, rowF), features.map((colF) => {
        if (rowF === colF) {
          return /* @__PURE__ */ React.createElement("div", { key: rowF + "|" + colF, className: "stom-combo-cell" });
        }
        const cell = cellMap[rowF + "|" + colF];
        if (!cell) {
          return /* @__PURE__ */ React.createElement("div", { key: rowF + "|" + colF, className: "stom-combo-cell" });
        }
        const key = rowF + "|" + colF;
        const isSel = selKey === key;
        return /* @__PURE__ */ React.createElement(
          "div",
          {
            key,
            className: "stom-combo-cell",
            role: "button",
            tabIndex: 0,
            style: {
              background: _rlCorrColor(cell.score),
              cursor: "pointer",
              outline: isSel ? "2px solid var(--blue)" : "none"
            },
            title: `${rowF} \xD7 ${colF} \xB7 ${_rlNum(cell.score, 3)} \xB7 n=${cell.n} \xB7 \uD074\uB9AD=\uC0C1\uC138`,
            onClick: () => setSelected({ a: rowF, b: colF, score: cell.score, n: cell.n })
          },
          _rlNum(cell.score, 2)
        );
      })))
    ), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { marginTop: 6 } }, "\uBC94\uB840: ", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--teal)" } }, "teal=\uC591(+)"), " \xB7 ", /* @__PURE__ */ React.createElement("span", { style: { color: "var(--red)" } }, "red=\uC74C(-)"), " \xB7 |\uAC12|\uC774 \uD074\uC218\uB85D \uC9C4\uD568 \xB7 \uB300\uAC01/\uB204\uB77D \uC870\uD569\uC740 \uBE48 \uC140 \xB7 \uC140 \uD074\uB9AD=\uBCC0\uC218\uC30D \uC0C1\uC138"), selected && /* @__PURE__ */ React.createElement(_ComboPairPopover, { pair: selected, onClose: () => setSelected(null) }));
  }
  function _RangeSummaryList({ rows }) {
    if (!rows || rows.length === 0) {
      return /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uD788\uC2A4\uD1A0\uADF8\uB7A8 \uBD84\uC11D\uC5D0 \uD544\uC694\uD55C range_summaries \uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4." });
    }
    return /* @__PURE__ */ React.createElement("div", { className: "research-combo-list" }, rows.slice(0, 8).map((row, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "research-combo-row", title: "histogram and win/loss range contrast" }, /* @__PURE__ */ React.createElement("span", { className: "mono" }, row.feature), /* @__PURE__ */ React.createElement("span", null, "median ", _rlNum(row.median, 2)), /* @__PURE__ */ React.createElement("span", null, "q25-q75 ", _rlNum(row.q25, 2), "~", _rlNum(row.q75, 2)), /* @__PURE__ */ React.createElement("span", null, "win/loss \u0394 ", _rlNum(row.win_loss && row.win_loss.mean_delta, 3)), /* @__PURE__ */ React.createElement("small", null, "histogram ", (row.histogram || []).map((b) => b.count).join("/")))));
  }
  function _SegmentSummaryList({ summary, axis }) {
    const rows = summary && Array.isArray(summary[axis]) ? summary[axis] : [];
    if (rows.length === 0) {
      return /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: axis + " \uCD95\uC758 segment_summaries \uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4." });
    }
    return /* @__PURE__ */ React.createElement("div", { className: "research-combo-list" }, rows.slice(0, 8).map((row, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "research-combo-row" }, /* @__PURE__ */ React.createElement("span", { className: "mono" }, axis, ":", row.label), /* @__PURE__ */ React.createElement("span", null, "avg ", _rlNum(row.avg_return, 3)), /* @__PURE__ */ React.createElement("span", null, "win ", _rlNum(row.win_rate, 3)), /* @__PURE__ */ React.createElement("small", null, "sample count ", row.sample_count || 0))));
  }
  function _RecencyResearchBadge({ recency }) {
    if (!recency) return null;
    return /* @__PURE__ */ React.createElement("div", { className: "research-empty", title: "research_score_not_promotion" }, "recency_research \xB7 ", recency.score_label || "research_score_not_promotion", " \xB7 score ", _rlNum(recency.research_score, 4));
  }
  function _PipelineCheckpointPanel({ baseUrl, isDemo }) {
    const [items, setItems] = useState_rl(null);
    useEffect_rl(() => {
      if (isDemo || !baseUrl) return;
      fetch(baseUrl + "/pipeline_status", { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null).then((j) => setItems(j && Array.isArray(j.items) ? j.items : [])).catch(() => {
      });
    }, [baseUrl, isDemo]);
    if (!items || items.length === 0) return null;
    return /* @__PURE__ */ React.createElement("div", { style: { marginTop: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uD30C\uC774\uD504\uB77C\uC778 \uCCB4\uD06C\uD3EC\uC778\uD2B8"), items.slice(0, 5).map((item, i) => {
      const stages = item.stages || {};
      const stageList = Object.entries(stages);
      return /* @__PURE__ */ React.createElement("div", { key: i, className: "mono", style: { fontSize: 11, marginTop: 2 } }, /* @__PURE__ */ React.createElement("b", null, item.prefix), " \xB7 ", stageList.length === 0 ? "\uB2E8\uACC4 \uC5C6\uC74C" : stageList.map(([k, v]) => (v ? "\u2705" : "\xB7") + k).join("  "));
    }));
  }
  function _ValidationPanel({ baseUrl, runId, isDemo }) {
    const [selector, setSelector] = useState_rl("seed_relative_v1");
    const [yearly, setYearly] = useState_rl(null);
    const [preview, setPreview] = useState_rl(null);
    const [autopsyGen, setAutopsyGen] = useState_rl(0);
    const [autopsy, setAutopsy] = useState_rl(null);
    const [cf, setCf] = useState_rl(null);
    const [mc, setMc] = useState_rl(null);
    const [tmap, setTmap] = useState_rl(null);
    const [compareRun, setCompareRun] = useState_rl("");
    const [ops, setOps] = useState_rl(null);
    const [grid, setGrid] = useState_rl(null);
    const [gridRun, setGridRun] = useState_rl("");
    const [loading, setLoading] = useState_rl(false);
    const [err, setErr] = useState_rl(null);
    const fetchGrid = useCallback_rl(() => {
      if (isDemo || !baseUrl) return;
      const rid = gridRun.trim() || runId;
      if (!rid) return;
      fetch(
        baseUrl + "/tmap_grid?run_id=" + encodeURIComponent(rid),
        { signal: AbortSignal.timeout(1e4) }
      ).then((r) => r.ok ? r.json() : null).then((j) => setGrid(j)).catch((e) => setErr(String(e)));
    }, [baseUrl, gridRun, isDemo, runId]);
    const [gridMetric, setGridMetric] = useState_rl("profit");
    const [runOptions, setRunOptions] = useState_rl([]);
    useEffect_rl(() => {
      if (isDemo || !baseUrl) return;
      fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((d) => setRunOptions((d && d.runs || []).slice(0, 40).map((r) => r.run_id))).catch(() => {
      });
    }, [baseUrl, isDemo]);
    const [niche, setNiche] = useState_rl(null);
    const fetchNiche = useCallback_rl(() => {
      if (isDemo || !baseUrl) return;
      fetch(baseUrl + "/niche_compare", { signal: AbortSignal.timeout(15e3) }).then((r) => r.ok ? r.json() : null).then((j) => setNiche(j)).catch((e) => setErr(String(e)));
    }, [baseUrl, isDemo]);
    const [psimRun1, setPsimRun1] = useState_rl("");
    const [psimRun2, setPsimRun2] = useState_rl("");
    const [psim, setPsim] = useState_rl(null);
    const fetchPsim = useCallback_rl(() => {
      if (isDemo || !baseUrl) return;
      const r1 = psimRun1.trim(), r2 = psimRun2.trim();
      if (!r1 || !r2) return;
      fetch(
        baseUrl + "/portfolio_sim?runs=" + encodeURIComponent(r1 + "," + r2),
        { signal: AbortSignal.timeout(15e3) }
      ).then((r) => r.ok ? r.json() : null).then((j) => setPsim(j)).catch((e) => setErr(String(e)));
    }, [baseUrl, isDemo, psimRun1, psimRun2]);
    const [verdict, setVerdict] = useState_rl(null);
    useEffect_rl(() => {
      if (isDemo || !baseUrl) return void 0;
      const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null).then((j) => setOps(j)).catch(() => {
      });
      pull();
      const timer = setInterval(pull, 1e4);
      fetch(baseUrl + "/freeze_verdict", { signal: AbortSignal.timeout(12e3) }).then((r) => r.ok ? r.json() : null).then((j) => setVerdict(j)).catch(() => {
      });
      return () => clearInterval(timer);
    }, [baseUrl, isDemo]);
    const fetchTmap = useCallback_rl(() => {
      if (isDemo || !baseUrl || !runId) return;
      const cmp = compareRun.trim() ? "&compare_run_id=" + encodeURIComponent(compareRun.trim()) : "";
      fetch(
        baseUrl + "/tmap_map?run_id=" + encodeURIComponent(runId) + cmp,
        { signal: AbortSignal.timeout(1e4) }
      ).then((r) => r.ok ? r.json() : null).then((j) => setTmap(j)).catch((e) => setErr(String(e)));
    }, [baseUrl, compareRun, isDemo, runId]);
    const refresh = useCallback_rl(() => {
      if (isDemo || !baseUrl || !runId) return;
      setLoading(true);
      const yUrl = baseUrl + "/run_yearly?run_id=" + encodeURIComponent(runId);
      const pUrl = baseUrl + "/selector_preview?run_id=" + encodeURIComponent(runId) + "&selector=" + encodeURIComponent(selector);
      Promise.all([
        fetch(yUrl, { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null),
        fetch(pUrl, { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null)
      ]).then(([y, p]) => {
        setYearly(y);
        setPreview(p);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, runId, selector]);
    useEffect_rl(() => {
      refresh();
    }, [refresh]);
    const [equity, setEquity] = useState_rl(null);
    const fetchAutopsy = useCallback_rl(() => {
      if (isDemo || !baseUrl || !runId) return;
      const q = "?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(autopsyGen);
      Promise.all([
        fetch(baseUrl + "/autopsy" + q, { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null),
        fetch(baseUrl + "/counterfactual" + q, { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null),
        fetch(baseUrl + "/freeze_mc" + q, { signal: AbortSignal.timeout(15e3) }).then((r) => r.ok ? r.json() : null),
        fetch(baseUrl + "/equity_curve" + q, { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null)
      ]).then(([a, c, m, eq]) => {
        setAutopsy(a);
        setCf(c);
        setMc(m);
        setEquity(eq);
      }).catch((e) => setErr(String(e)));
    }, [autopsyGen, baseUrl, isDemo, runId]);
    if (isDemo || !runId) {
      return /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uAC80\uC99D \uD654\uBA74\uC744 \uD45C\uC2DC\uD560 run \uCEE8\uD14D\uC2A4\uD2B8\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4." }));
    }
    const gens = yearly && Array.isArray(yearly.generations) ? yearly.generations : [];
    return /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement("div", { className: "research-controls" }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "selector"), /* @__PURE__ */ React.createElement("select", { value: selector, onChange: (e) => setSelector(e.target.value), disabled: loading }, /* @__PURE__ */ React.createElement("option", { value: "seed_relative_v1" }, "seed_relative_v1"), /* @__PURE__ */ React.createElement("option", { value: "sparse_positive_v1" }, "sparse_positive_v1"))), /* @__PURE__ */ React.createElement("span", { className: "research-empty" }, "diagnostic_only \xB7 \uB3D9\uACB0 \uC544\uD2F0\uD329\uD2B8 \uC544\uB2D8"), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "research-help",
        title: "\uC801\uD569\uB3C4(Fitness): \uC190\uC775\xB7MDD\xB7\uAC70\uB798\uC218\xB7\uC77C\uAD00\uC131\uC744 \uAC00\uC911\uD569\uD55C \uD55C \uAC1C\uC758 \uC810\uC218. \uC138\uB300(\uC804\uB7B5)\uAC00 \uBAA9\uD45C \uAE30\uC900\uC5D0 \uC5BC\uB9C8\uB098 \uBD80\uD569\uD558\uB294\uC9C0\uB97C \uB098\uD0C0\uB0C5\uB2C8\uB2E4 \u2014 \uB192\uC744\uC218\uB85D \uC88B\uACE0, \uAC8C\uC774\uD2B8\uC758 1\uCC28 \uD1B5\uACFC \uAE30\uC900\uC785\uB2C8\uB2E4. \uCC28\uD2B8\uB294 \uC138\uB300 \uC9C4\uD589(x)\uC5D0 \uB530\uB77C \uC801\uD569\uB3C4\uAC00 \uC6B0\uC0C1\uD5A5\uD558\uB294\uC9C0\uB97C \uBD05\uB2C8\uB2E4."
      },
      "\uC801\uD569\uB3C4 ?"
    ), /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "research-help",
        title: "\uD488\uC9C8(Quality): \uACB0\uACFC\uC758 \uACAC\uACE0\uD568 \uC9C0\uD45C \uBAA8\uC74C(\uD751\uC790\uC728\xB7\uACE0\uC6D0/mesa \uC548\uC815\uC131\xB7OOS \uC720\uC9C0 \uB4F1). \uB2E8\uBC1C \uACE0\uC810\uC774 \uC544\uB2C8\uB77C \uC774\uC6C3 \uD30C\uB77C\uBBF8\uD130\xB7\uB2E4\uB978 \uAE30\uAC04\uC5D0\uC11C\uB3C4 \uC131\uACFC\uAC00 \uC720\uC9C0\uB418\uB294\uC9C0\uB97C \uBD05\uB2C8\uB2E4 \u2014 \uACFC\uCD5C\uC801\uD654\uB97C \uAC70\uB974\uB294 \uCC99\uB3C4\uC785\uB2C8\uB2E4."
      },
      "\uD488\uC9C8 ?"
    )), err && /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC751\uB2F5\uC744 \uBC1B\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4: " + err }), ops && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC6B4\uC601 \uD604\uD669 (10\uCD08 \uC790\uB3D9 \uAC31\uC2E0)" + (ops.walkforward ? ` \xB7 WF ${ops.walkforward.path}: \uC815\uCC45 ${Math.round(ops.walkforward.policy_total || 0).toLocaleString()} vs \uC2DC\uB4DC ${Math.round(ops.walkforward.baseline_total || 0).toLocaleString()} (${ops.walkforward.windows_done}\uCC3D \uC644\uB8CC)` : "")), (ops.active || []).length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uC2E4\uD589 \uC911 run \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC2E4\uD589 \uC911 run"), /* @__PURE__ */ React.createElement("th", null, "\uC138\uB300"), /* @__PURE__ */ React.createElement("th", null, "\uB9C8\uC9C0\uB9C9 \uD3EC\uC778\uD2B8"), /* @__PURE__ */ React.createElement("th", null, "\uBB34\uC9C4\uD589(\uCD08)"), /* @__PURE__ */ React.createElement("th", null, "\uC0C1\uD0DC"))), /* @__PURE__ */ React.createElement("tbody", null, ops.active.map((a) => /* @__PURE__ */ React.createElement("tr", { key: a.run_id }, /* @__PURE__ */ React.createElement("td", null, a.run_id), /* @__PURE__ */ React.createElement("td", null, a.gens), /* @__PURE__ */ React.createElement("td", null, a.last_label || "\u2014"), /* @__PURE__ */ React.createElement("td", null, a.seconds_since_last_gen), /* @__PURE__ */ React.createElement("td", null, a.health === "active" ? "\u2705 \uC9C4\uD589 \uC911" : "\u26A0\uFE0F \uC815\uCCB4 \uC758\uC2EC"))))), (ops.recent || []).length > 0 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uCD5C\uADFC \uC644\uB8CC: " + ops.recent.slice(0, 5).map(
      (r) => `${r.run_id}(${r.gens}\uC138\uB300${r.best_profit != null ? "\xB7\uCD5C\uACE0 " + Math.round(r.best_profit).toLocaleString() : ""})`
    ).join("  \xB7  ")), (ops.evidence || []).length > 0 && /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uCD5C\uC2E0 \uC99D\uAC70: " + ops.evidence.map((e) => `${e.name}(${e.age_min}\uBD84 \uC804)`).join(" \xB7 "))), verdict && (verdict.lines || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uAC80\uC99D \uACB0\uC0B0 (V1~V5 + \uB9AC\uC2A4\uD06C \u2014 \uACB0\uC815 \uCE74\uB4DC \uB77C\uC774\uBE0C)"), (verdict.promote_checklist || []).length > 0 && /* @__PURE__ */ React.createElement(VdtPromoteChecklist, { v: verdict }), verdict.walkforward && Array.isArray(verdict.walkforward.windows) && verdict.walkforward.windows.length > 0 && /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, marginBottom: 4 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "WF \uCC3D(fit)"), /* @__PURE__ */ React.createElement("th", null, "eval"), /* @__PURE__ */ React.createElement("th", null, "\u03B8 \uC120\uD0DD"), /* @__PURE__ */ React.createElement("th", null, "\uC815\uCC45"), /* @__PURE__ */ React.createElement("th", null, "\uC2DC\uB4DC"))), /* @__PURE__ */ React.createElement("tbody", null, verdict.walkforward.windows.map((w, i) => /* @__PURE__ */ React.createElement("tr", { key: "w" + i }, /* @__PURE__ */ React.createElement("td", null, w.fit_start, "~", w.fit_end), /* @__PURE__ */ React.createElement("td", null, w.eval_start, "~", w.eval_end), /* @__PURE__ */ React.createElement("td", null, w.theta ? Object.entries(w.theta).map(([k, v]) => `${k}=${v}`).join(",") : "\uAE30\uAD8C(\uC2DC\uB4DC \uC720\uC9C0)"), /* @__PURE__ */ React.createElement("td", null, w.policy ? Math.round(w.policy.profit).toLocaleString() : "\u2014"), /* @__PURE__ */ React.createElement("td", null, w.baseline ? Math.round(w.baseline.profit).toLocaleString() : "\u2014"))))), /* @__PURE__ */ React.createElement(VdtAlerts, { v: verdict }), /* @__PURE__ */ React.createElement(VdtSummaryLines, { v: verdict })), niche && (niche.runs || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB2C8\uCE58 \uC9C0\uB3C4 \uBE44\uAD50 (\uCD5C\uADFC tmap run \uC790\uB3D9 \u2014 \uC2E0\uADDC \uB2C8\uCE58 4\uC885 \uC544\uCE68 \uBD84\uC11D\uC6A9)"), /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "run"), /* @__PURE__ */ React.createElement("th", null, "\uC0C1\uD0DC"), /* @__PURE__ */ React.createElement("th", null, "ok\uC138\uB300"), /* @__PURE__ */ React.createElement("th", null, "\uBCA0\uC774\uC2A4\uB77C\uC778"), /* @__PURE__ */ React.createElement("th", null, "\uCD5C\uAC15 \uC2AC\uB86F \uACE0\uC6D0 / \uACA9\uC790"), /* @__PURE__ */ React.createElement("th", null, "\uCD5C\uACE0 \uB2E8\uC77C\uC810"), /* @__PURE__ */ React.createElement("th", null, "\uC2DC\uAC04\uB300"), /* @__PURE__ */ React.createElement("th", null, "R\xB2\xB7\uC815\uCCB4"), /* @__PURE__ */ React.createElement("th", null, "\uB3D9\uACB0\uC0C1\uAD00"))), /* @__PURE__ */ React.createElement("tbody", null, niche.runs.map((r) => /* @__PURE__ */ React.createElement("tr", { key: r.run_id }, /* @__PURE__ */ React.createElement("td", null, r.run_id), /* @__PURE__ */ React.createElement("td", null, r.status === "running" ? "\u{1F504}" : "\u2705"), /* @__PURE__ */ React.createElement("td", null, r.gens_ok), /* @__PURE__ */ React.createElement("td", null, r.baseline ? `${Math.round(r.baseline.profit).toLocaleString()} (MDD ${_rlNum(r.baseline.mdd, 1)})` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, r.top_slot ? `${r.top_slot.param}: \uC911\uC2EC ${r.top_slot.center} \xB7 \uD3C9\uADE0 ${Math.round(r.top_slot.mean_profit || 0).toLocaleString()} (score ${_rlNum(r.top_slot.plateau_score, 2)})` : r.grid ? `\uACA9\uC790 ${r.grid.cells}\uC140 \xB7 \uD751\uC790 ${Math.round((r.grid.positive_ratio || 0) * 100)}% \xB7 mesa ${r.grid.mesa}` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, r.best_profit != null ? Math.round(r.best_profit).toLocaleString() : "\u2014"), /* @__PURE__ */ React.createElement("td", null, (r.time_buckets || []).join(",") || "\u2014"), /* @__PURE__ */ React.createElement("td", null, r.shape_r2 != null ? `${_rlNum(r.shape_r2, 2)}\xB7${r.stagnation_days}\uC77C` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, r.corr_vs_frozen != null ? _rlNum(r.corr_vs_frozen, 2) : "\u2014")))))), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { marginTop: 6 } }, "\uC5F0\uB3C4 \uBD84\uD574 (per-trade CSV \uC9D1\uACC4)"), /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "gen"), /* @__PURE__ */ React.createElement("th", null, "label"), /* @__PURE__ */ React.createElement("th", null, "\uC5F0\uB3C4\uBCC4 \uC190\uC775(\uAC70\uB798\uC218\xB7\uC2B9\uB960)"))), /* @__PURE__ */ React.createElement("tbody", null, gens.map((g) => /* @__PURE__ */ React.createElement("tr", { key: g.gen_no }, /* @__PURE__ */ React.createElement("td", null, g.gen_no), /* @__PURE__ */ React.createElement("td", null, g.label || g.buy_name || "\u2014"), /* @__PURE__ */ React.createElement("td", null, (g.years || []).length ? g.years.map((y) => `${y.year}: ${Math.round(y.profit).toLocaleString()} (${y.trades}\uAC74\xB7${Math.round((y.win_rate || 0) * 100)}%)`).join("  \xB7  ") : "\u2014"))))), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { marginTop: 8 } }, "\uC120\uD0DD\uAE30 \uBBF8\uB9AC\uBCF4\uAE30 \u2014 selected: ", preview && preview.selected ? "TRUE" : "false", preview && preview.mdd_limit != null ? ` \xB7 mdd_limit ${_rlNum(preview.mdd_limit, 2)}` : "", preview && preview.selected_candidate ? ` \xB7 gen${preview.selected_candidate.gen_no} ${preview.selected_candidate.label || preview.selected_candidate.buy_name}` : ""), preview && Array.isArray(preview.rejected) && preview.rejected.length > 0 && /* @__PURE__ */ React.createElement("ul", { className: "mono", style: { fontSize: 11 } }, preview.rejected.map((rj) => /* @__PURE__ */ React.createElement("li", { key: rj.gen_no }, "gen", rj.gen_no, " ", rj.label || "", ": ", (rj.reasons || []).join("; ")))), /* @__PURE__ */ React.createElement("div", { className: "research-controls", style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "gen"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "number",
        value: autopsyGen,
        min: 0,
        onChange: (e) => setAutopsyGen(Number(e.target.value) || 0),
        style: { width: 64 }
      }
    )), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: fetchAutopsy }, "\uBD80\uAC80\xB7\uBC18\uC0AC\uC2E4\xB7MC \uBCF4\uAE30"), /* @__PURE__ */ React.createElement("datalist", { id: "rl-run-options" }, runOptions.map((id) => /* @__PURE__ */ React.createElement("option", { key: id, value: id }))), /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "\uBE44\uAD50 run"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: compareRun,
        placeholder: "\uB2E4\uB978 \uC2A4\uC715 run_id (\uC120\uD0DD)",
        list: "rl-run-options",
        onChange: (e) => setCompareRun(e.target.value),
        style: { width: 180 }
      }
    )), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: fetchTmap }, "TMAP \uC9C0\uB3C4"), /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "\uACA9\uC790 run"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: gridRun,
        placeholder: "--grid \uC2A4\uC715 run_id",
        list: "rl-run-options",
        onChange: (e) => setGridRun(e.target.value),
        style: { width: 180 }
      }
    )), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: fetchGrid }, "2-D \uD788\uD2B8\uB9F5"), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: fetchNiche }, "\uB2C8\uCE58 \uBE44\uAD50")), autopsy && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, whiteSpace: "pre-wrap" } }, autopsy.status !== "ok" ? `autopsy: ${autopsy.status}` : `${autopsy.entry_summary || "(\uC9C4\uC785 \uBD80\uAC80 \uC5C6\uC74C)"}

${autopsy.exit_summary || "(\uCCAD\uC0B0 \uBD80\uAC80 \uC5C6\uC74C)"}`), cf && cf.status === "ok" && Array.isArray(cf.suggestions) && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBC18\uC0AC\uC2E4 \uD544\uD130 \uC81C\uC548 (\uBC31\uD14C 0\uD68C\xB7\uC778\uC0D8\uD50C advisory \u2014 \uCC44\uD0DD \uC2DC \uC815\uC2DD \uD30C\uC774\uD504\uB77C\uC778 \uAC80\uC99D \uD544\uC218)"), cf.suggestions.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uCD1D\uC190\uC775\uC774 \uAE4E\uC774\uC9C0 \uC54A\uB294 \uAC15\uD654 \uD544\uD130 \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uD544\uD130"), /* @__PURE__ */ React.createElement("th", null, "\uAC70\uB798"), /* @__PURE__ */ React.createElement("th", null, "\uCD1D\uC190\uC775"), /* @__PURE__ */ React.createElement("th", null, "\uC2B9\uB960"), /* @__PURE__ */ React.createElement("th", null, "\uC798\uB9B0 \uAC70\uB798 \uC21C\uC190\uC775"), /* @__PURE__ */ React.createElement("th", null, "\uCD5C\uADFC\uC5F0\uB3C4"))), /* @__PURE__ */ React.createElement("tbody", null, cf.suggestions.map((s, i) => /* @__PURE__ */ React.createElement("tr", { key: i }, /* @__PURE__ */ React.createElement("td", null, s.filter), /* @__PURE__ */ React.createElement("td", null, s.base_trades, "\u2192", s.kept_trades), /* @__PURE__ */ React.createElement("td", null, Math.round((s.profit_ratio || 0) * 100), "%"), /* @__PURE__ */ React.createElement("td", null, Math.round((s.base_win_rate || 0) * 100), "%\u2192", Math.round((s.kept_win_rate || 0) * 100), "%"), /* @__PURE__ */ React.createElement("td", null, Math.round(s.cut_net_profit || 0).toLocaleString()), /* @__PURE__ */ React.createElement("td", null, s.recent_year ? `${s.recent_year.year}: ${Math.round(s.recent_year.base_profit).toLocaleString()}\u2192${Math.round(s.recent_year.kept_profit).toLocaleString()}` : "\u2014")))))), mc && mc.status === "ok" && mc.mc && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBE14\uB85D \uBD80\uD2B8\uC2A4\uD2B8\uB7A9 MC (\uC77C\uBCC4 \uC190\uC775\xB7\uB808\uC9D0 \uAD70\uC9D1 \uBCF4\uC874 \u2014 iid \uAC70\uB798 \uCD94\uCD9C MC\uC758 OOS \uC804\uC774 \uC2E4\uD328 \uAD50\uD6C8 \uBC18\uC601)"), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, `P(\uCD1D\uC190\uC775>0)=${Math.round((mc.mc.p_positive || 0) * 100)}% \xB7 \uCD1D\uC190\uC775 p05/p50/p95 = ${Math.round(mc.mc.profit_p05).toLocaleString()} / ${Math.round(mc.mc.profit_p50).toLocaleString()} / ${Math.round(mc.mc.profit_p95).toLocaleString()} \xB7 MDD(\uB099\uD3ED\uAE08\uC561) p50/p95 = ${Math.round(mc.mc.mdd_p50).toLocaleString()} / ${Math.round(mc.mc.mdd_p95).toLocaleString()} (${mc.mc.n_days}\uC77C\xB7${mc.mc.n_boot}\uD68C\xB7\uBE14\uB85D ${mc.mc.block_len}\uC77C)`), /* @__PURE__ */ React.createElement(_McFanChart, { fan: mc.mc.fan })), equity && equity.status === "ok" && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "research-empty",
        title: "x\uCD95\uC740 \uAC70\uB798\uC77C \uC9C4\uD589(\uC67C\u2192\uC624\uB978\uCABD=\uACFC\uAC70\u2192\uD604\uC7AC), y\uCD95\uC740 \uB204\uC801 \uC190\uC775(\uC6D0). 0\uC120 \uC810\uC120 \uC704\uB294 \uD751\uC790 \uAD6C\uAC04\uC785\uB2C8\uB2E4."
      },
      `\uB204\uC801 \uC218\uC775\uACE1\uC120 \u2014 gen ${equity.gen_no}${equity.label ? " \xB7 " + equity.label : ""} \xB7 \uCD1D ${Math.round(equity.total).toLocaleString()}`
    ), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, color: "var(--ink-2)", marginBottom: 2 } }, `x\uCD95: \uAC70\uB798\uC77C \uC9C4\uD589(${equity.n_days}\uAC70\uB798\uC77C) \xB7 \uAE30\uAC04 ${_rlPeriodFromDays(equity.days)} \xB7 y\uCD95: \uB204\uC801 \uC190\uC775(\uC6D0)`), /* @__PURE__ */ React.createElement(_EquityChart, { cum: equity.cum })), tmap && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "TMAP \uACBD\uD5A5\uC131 \uC9C0\uB3C4 (\uACE0\uC6D0 > \uD53C\uD06C \u2014 \uC774\uC6C3 \u03B8\uB3C4 \uD751\uC790\uC778 \uC601\uC5ED\uC774 \uC9C4\uC9DC)"), !tmap.count || !Object.keys(tmap.params || {}).length ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uC774 run\uC740 TMAP \uC2A4\uC715\uC774 \uC544\uB2D9\uB2C8\uB2E4 (tmap_sweep run_id\uB97C \uC120\uD0DD\uD558\uC138\uC694)") : /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, tmap.baseline ? `\uBCA0\uC774\uC2A4\uB77C\uC778(\u03B8=\uAE30\uBCF8\uAC12): \uC190\uC775 ${Math.round(tmap.baseline.profit).toLocaleString()} \xB7 MDD ${_rlNum(tmap.baseline.mdd, 2)} \xB7 ${tmap.baseline.trades}\uAC74` : "\uBCA0\uC774\uC2A4\uB77C\uC778 \uC5C6\uC74C"), /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC2AC\uB86F(\u03B8)"), /* @__PURE__ */ React.createElement("th", null, "\uC751\uB2F5 \uACE1\uC120"), /* @__PURE__ */ React.createElement("th", null, "plateau score"), /* @__PURE__ */ React.createElement("th", null, "\uACE0\uC6D0 \uC911\uC2EC"), /* @__PURE__ */ React.createElement("th", null, "\uD3ED"), /* @__PURE__ */ React.createElement("th", null, "\uACE0\uC6D0 \uD3C9\uADE0\uC190\uC775"), /* @__PURE__ */ React.createElement("th", null, "\uD751\uC790\uC728"), /* @__PURE__ */ React.createElement("th", null, "\uC808\uBCBD(\uCD5C\uB300 \uC810\uD504)"), /* @__PURE__ */ React.createElement("th", null, "\uC911\uC2EC \uD615\uD0DC(R\xB2\xB7\uC815\uCCB4\uC77C)"), tmap.compare && /* @__PURE__ */ React.createElement("th", null, "\uBE44\uAD50 run(\uC911\uC2EC\xB7score)"))), /* @__PURE__ */ React.createElement("tbody", null, Object.entries(tmap.params).sort((a, b) => (b[1].plateau_score || 0) - (a[1].plateau_score || 0)).map(([name, m]) => {
      const cm = tmap.compare && tmap.compare.params ? tmap.compare.params[name] : null;
      return /* @__PURE__ */ React.createElement("tr", { key: name }, /* @__PURE__ */ React.createElement("td", null, name), /* @__PURE__ */ React.createElement("td", null, /* @__PURE__ */ React.createElement(_CurveSpark, { curve: m.curve })), /* @__PURE__ */ React.createElement("td", null, _rlNum(m.plateau_score, 3)), /* @__PURE__ */ React.createElement("td", null, m.plateau ? m.plateau.center_value : "\u2014"), /* @__PURE__ */ React.createElement("td", null, m.plateau ? m.plateau.width : "\u2014"), /* @__PURE__ */ React.createElement("td", null, m.plateau ? Math.round(m.plateau.mean_profit).toLocaleString() : "\u2014"), /* @__PURE__ */ React.createElement("td", null, Math.round((m.positive_ratio || 0) * 100), "%"), /* @__PURE__ */ React.createElement("td", null, m.cliff ? `${Math.round(m.cliff.jump).toLocaleString()} @${m.cliff.between.join("\u2192")}` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, m.center_shape ? `${_rlNum(m.center_shape.uptrend_r2, 2)}\xB7${m.center_shape.max_stagnation_days}\uC77C` : "\u2014"), tmap.compare && /* @__PURE__ */ React.createElement("td", null, cm && cm.plateau ? `${cm.plateau.center_value} \xB7 ${_rlNum(cm.plateau_score, 2)}` : "\u2014"));
    }))), tmap.compare && /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uBE44\uAD50 run: ", tmap.compare.run_id || "\u2014", " \u2014 \uAD6C\uAC04\uBCC4 \uACBD\uD5A5 \uBC1C\uC0B0 \uD655\uC778\uC6A9(M12). \uB2E4\uB144 \uC9C0\uB3C4\uC758 \uACE0\uC6D0\uB9CC \uB3D9\uACB0 \uC790\uACA9."))), grid && grid.count > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { display: "flex", alignItems: "center", gap: 8 } }, /* @__PURE__ */ React.createElement("span", null, `2-D \uACA9\uC790 \uD788\uD2B8\uB9F5 (${grid.param_a} \xD7 ${grid.param_b}) \u2014 \u2605=mesa(4-\uC774\uC6C3 \uC804\uBD80 \uD751\uC790) \xB7 \uD751\uC790\uC728 ${Math.round((grid.positive_ratio || 0) * 100)}%` + (grid.baseline ? ` \xB7 \uBCA0\uC774\uC2A4\uB77C\uC778 ${Math.round(grid.baseline.profit).toLocaleString()}` : "")), /* @__PURE__ */ React.createElement(
      "button",
      {
        type: "button",
        className: "research-tab",
        onClick: () => setGridMetric(gridMetric === "profit" ? "mdd" : "profit")
      },
      "\uC0C9: ",
      gridMetric === "profit" ? "\uC218\uC775" : "MDD"
    )), /* @__PURE__ */ React.createElement(_GridHeatmap, { grid, metric: gridMetric })), grid && grid.count === 0 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uACA9\uC790 run \uC544\uB2D8(--grid \uC2A4\uC715 run_id\uB97C \uC785\uB825\uD558\uC138\uC694)"), /* @__PURE__ */ React.createElement(_PipelineCheckpointPanel, { baseUrl, isDemo }), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uACB0\uD569 \uC2DC\uBBAC (v0 \uADE0\uB4F1\uAC00\uC911) \u2014 advisory. \uD310\uC815 \uBBF8\uC0AC\uC6A9."), /* @__PURE__ */ React.createElement("div", { className: "research-controls", style: { marginTop: 4 } }, /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "run 1"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: psimRun1,
        placeholder: "run_id",
        list: "rl-run-options",
        onChange: (e) => setPsimRun1(e.target.value),
        style: { width: 180 }
      }
    )), /* @__PURE__ */ React.createElement("label", null, /* @__PURE__ */ React.createElement("span", null, "run 2"), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: psimRun2,
        placeholder: "run_id",
        list: "rl-run-options",
        onChange: (e) => setPsimRun2(e.target.value),
        style: { width: 180 }
      }
    )), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: fetchPsim }, "\uACB0\uD569 \uC2DC\uBBAC \uC2E4\uD589")), psim && !psim.error && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 6 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uACB0\uD569 \uCD1D\uC190\uC775: ", /* @__PURE__ */ React.createElement("b", null, Math.round(psim.combined_total || 0).toLocaleString()), " \xB7 ", "\uACB0\uD569 MDD: ", /* @__PURE__ */ React.createElement("b", null, Math.round(psim.combined_mdd || 0).toLocaleString()), psim.diversification_gain != null ? ` \xB7 \uBD84\uC0B0\uC774\uB4DD: ${(psim.diversification_gain * 100).toFixed(1)}%` : ""), psim.correlation && Array.isArray(psim.correlation.labels) && /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, marginTop: 4 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC0C1\uAD00"), psim.correlation.labels.map((l) => /* @__PURE__ */ React.createElement("th", { key: l }, l.split(":")[0])))), /* @__PURE__ */ React.createElement("tbody", null, psim.correlation.labels.map((row, i) => /* @__PURE__ */ React.createElement("tr", { key: row }, /* @__PURE__ */ React.createElement("th", null, row.split(":")[0]), (psim.correlation.matrix[i] || []).map((v, j) => /* @__PURE__ */ React.createElement("td", { key: j }, v.toFixed(2)))))))), psim && psim.error && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--amber)" } }, psim.error)));
  }
  function _GridHeatmap({ grid, metric }) {
    const useMdd = metric === "mdd";
    const cells = {};
    (grid.cells || []).forEach((c) => {
      cells[c.a + "|" + c.b] = c;
    });
    const maxAbs = Math.max(1, ...(grid.cells || []).map((c) => Math.abs(useMdd ? c.mdd : c.profit)));
    const mesaSet = new Set((grid.mesa_cells || []).map((m) => m.a + "|" + m.b));
    return /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 10, marginTop: 4 } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, grid.param_a + " \\ " + grid.param_b), (grid.b_values || []).map((b) => /* @__PURE__ */ React.createElement("th", { key: b, style: { padding: "2px 6px" } }, b)))), /* @__PURE__ */ React.createElement("tbody", null, (grid.a_values || []).map((a) => /* @__PURE__ */ React.createElement("tr", { key: a }, /* @__PURE__ */ React.createElement("th", { style: { padding: "2px 6px" } }, a), (grid.b_values || []).map((b) => {
      const c = cells[a + "|" + b];
      if (!c) return /* @__PURE__ */ React.createElement("td", { key: b }, "\u2014");
      const value = useMdd ? c.mdd : c.profit;
      const pct = Math.round(15 + 70 * Math.abs(value) / maxAbs);
      const token = useMdd ? "var(--red)" : c.profit > 0 ? "var(--teal)" : "var(--red)";
      const bg = `color-mix(in srgb, ${token} ${pct}%, transparent)`;
      const isMesa = mesaSet.has(a + "|" + b);
      return /* @__PURE__ */ React.createElement(
        "td",
        {
          key: b,
          title: `${grid.param_a}=${a}, ${grid.param_b}=${b} \xB7 \uC190\uC775 ${Math.round(c.profit).toLocaleString()} \xB7 MDD ${_rlNum(c.mdd, 2)} \xB7 ${c.trades}\uAC74`,
          style: {
            background: bg,
            textAlign: "right",
            padding: "2px 6px",
            outline: isMesa ? "2px solid var(--mesa-gold)" : "none"
          }
        },
        useMdd ? _rlNum(c.mdd, 1) : Math.round(c.profit / 1e4).toLocaleString() + "\uB9CC",
        isMesa ? "\u2605" : ""
      );
    })))));
  }
  function _EquityChart({ cum }) {
    const pts = (cum || []).map(Number).filter((v) => isFinite(v));
    if (pts.length < 2) return null;
    const W = 620, H = 150, PAD = 6;
    const min = Math.min(0, ...pts), max = Math.max(0, ...pts);
    const span = Math.max(max - min, 1);
    const x = (i) => PAD + i / (pts.length - 1) * (W - PAD * 2);
    const y = (v) => H - PAD - (v - min) / span * (H - PAD * 2);
    const path = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
    const last = pts[pts.length - 1];
    return /* @__PURE__ */ React.createElement("svg", { width: W, height: H, style: { background: "rgba(255,255,255,0.03)", borderRadius: 4 } }, /* @__PURE__ */ React.createElement("line", { x1: PAD, y1: y(0), x2: W - PAD, y2: y(0), stroke: "#777", strokeDasharray: "3,3", strokeWidth: "0.8" }), /* @__PURE__ */ React.createElement("path", { d: path, fill: "none", stroke: last >= 0 ? "#4c9" : "#c66", strokeWidth: "1.8" }), /* @__PURE__ */ React.createElement("text", { x: W - PAD - 4, y: y(last) - 6, fill: "var(--ink-2)", fontSize: "10", textAnchor: "end" }, Math.round(last).toLocaleString()));
  }
  function _CurveSpark({ curve }) {
    const pts = (curve || []).filter((p) => p && p.ok);
    if (pts.length < 2) return null;
    const W = 90, H = 22;
    const profits = pts.map((p) => p.profit || 0);
    const min = Math.min(0, ...profits), max = Math.max(0, ...profits);
    const span = Math.max(max - min, 1);
    const x = (i) => 2 + i / (pts.length - 1) * (W - 4);
    const y = (v) => H - 2 - (v - min) / span * (H - 4);
    const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.profit || 0).toFixed(1)}`).join(" ");
    return /* @__PURE__ */ React.createElement("svg", { width: W, height: H, style: { verticalAlign: "middle" } }, /* @__PURE__ */ React.createElement("line", { x1: "2", y1: y(0), x2: W - 2, y2: y(0), stroke: "#777", strokeDasharray: "2,2", strokeWidth: "0.8" }), /* @__PURE__ */ React.createElement("path", { d: path, fill: "none", stroke: "#5b9", strokeWidth: "1.5" }));
  }
  function _McFanChart({ fan }) {
    if (!fan || !Array.isArray(fan.x) || !fan.x.length) return null;
    const W = 320, H = 90, PAD = 4;
    const all = [].concat(fan.p05 || [], fan.p95 || [], fan.p50 || []);
    const lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
    const span = hi - lo || 1;
    const px = (i) => PAD + (W - 2 * PAD) * (fan.x[i] || 0);
    const py = (v) => H - PAD - (H - 2 * PAD) * ((v - lo) / span);
    const pts = (arr) => arr.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(" ");
    const band = (upper, lower) => pts(upper) + " " + lower.map((v, i) => `${px(lower.length - 1 - i).toFixed(1)},${py(lower[lower.length - 1 - i]).toFixed(1)}`).join(" ");
    return /* @__PURE__ */ React.createElement(
      "svg",
      {
        width: W,
        height: H,
        style: { display: "block", marginTop: 4 },
        role: "img",
        "aria-label": "MC fan chart"
      },
      /* @__PURE__ */ React.createElement("polygon", { points: band(fan.p95, fan.p05), fill: "rgba(80,140,200,0.18)", stroke: "none" }),
      /* @__PURE__ */ React.createElement("polygon", { points: band(fan.p75, fan.p25), fill: "rgba(80,140,200,0.28)", stroke: "none" }),
      /* @__PURE__ */ React.createElement("polyline", { points: pts(fan.p50), fill: "none", stroke: "rgba(120,190,255,0.95)", strokeWidth: "1.5" }),
      /* @__PURE__ */ React.createElement(
        "line",
        {
          x1: PAD,
          y1: py(0),
          x2: W - PAD,
          y2: py(0),
          stroke: "rgba(200,200,200,0.4)",
          strokeDasharray: "3,3",
          strokeWidth: "1"
        }
      )
    );
  }
  function _RlProcessFlowOverlay({ onClose, activeStage }) {
    const PIPELINE = window.STOM_PIPELINE || [];
    useEffect_rl(() => {
      const onKey = (e) => {
        if (e.key === "Escape") onClose();
      };
      window.addEventListener("keydown", onKey);
      return () => window.removeEventListener("keydown", onKey);
    }, [onClose]);
    const ai = typeof activeStage === "number" ? activeStage : -1;
    return /* @__PURE__ */ React.createElement("div", { className: "rp-overlay", onClick: onClose }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-card", onClick: (e) => e.stopPropagation() }, /* @__PURE__ */ React.createElement("div", { className: "rp-overlay-hd" }, /* @__PURE__ */ React.createElement("span", { className: "rp-card-title" }, "\uC9C4\uD654 \uD504\uB85C\uC138\uC2A4 \u2014 \uC804\uCCB4 \uD750\uB984"), ai >= 0 && /* @__PURE__ */ React.createElement("span", { className: "rp-card-sub" }, "\uD604\uC7AC \uB2E8\uACC4: ", PIPELINE[ai].title), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn ghost sm", style: { marginLeft: "auto" }, onClick: onClose }, "\u2715 \uB2EB\uAE30 (Esc)")), /* @__PURE__ */ React.createElement("div", { className: "rp-flow" }, PIPELINE.map((s, i) => /* @__PURE__ */ React.createElement(React.Fragment, { key: s.title }, /* @__PURE__ */ React.createElement("div", { className: "rp-flow-node" + (i === ai ? " rp-flow-active" : "") }, /* @__PURE__ */ React.createElement("div", { className: "rp-flow-ico" }, s.icon), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-name" }, i + 1, ". ", s.title, i === ai && /* @__PURE__ */ React.createElement("span", { className: "rp-flow-pulse" }, " \u25CF \uC9C4\uD589")), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-desc" }, s.desc), /* @__PURE__ */ React.createElement("div", { className: "rp-flow-terms" }, s.terms.map(([t, d]) => /* @__PURE__ */ React.createElement("div", { key: t, className: "rp-flow-term" }, /* @__PURE__ */ React.createElement("b", null, t), " ", d)))), i < PIPELINE.length - 1 && /* @__PURE__ */ React.createElement("div", { className: "rp-flow-arrow" }, "\u2192"))))));
  }
  function ResearchLabPanel({ baseUrl, wsStatus, runId }) {
    const [tab, setTab] = useState_rl("edge");
    const [fullscreen, setFullscreen] = useState_rl(false);
    const [opsStrip, setOpsStrip] = useState_rl(null);
    const [showFlow, setShowFlow] = useState_rl(false);
    useEffect_rl(() => {
      if (!baseUrl) return void 0;
      const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null).then((j) => {
        setOpsStrip(j);
        try {
          const stalled = (j && j.active || []).some((a) => a.health !== "active");
          const base = document.title.replace(/^⚠️ /, "");
          document.title = (stalled ? "\u26A0\uFE0F " : "") + base;
        } catch (e) {
        }
      }).catch(() => {
      });
      pull();
      const timer = setInterval(pull, 1e4);
      return () => clearInterval(timer);
    }, [baseUrl]);
    const [method, setMethod] = useState_rl("spearman");
    const [axis, setAxis] = useState_rl("time");
    const [data, setData] = useState_rl(null);
    const [loading, setLoading] = useState_rl(false);
    const [err, setErr] = useState_rl(null);
    const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    const needsCorrelation = tab === "correlation" || tab === "combos";
    const refreshCorrelation = useCallback_rl(() => {
      if (!needsCorrelation || isDemo || !baseUrl || !runId) return;
      setLoading(true);
      const url = baseUrl + "/variable_correlation?run_id=" + encodeURIComponent(runId) + "&method=" + encodeURIComponent(method);
      fetch(url, { signal: AbortSignal.timeout(5e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        setData(j);
        setErr(null);
      }).catch((e) => setErr(String(e))).finally(() => setLoading(false));
    }, [baseUrl, isDemo, method, needsCorrelation, runId]);
    useEffect_rl(() => {
      refreshCorrelation();
    }, [refreshCorrelation]);
    const matrixRows = data && Array.isArray(data.feature_matrix) ? data.feature_matrix : [];
    const outcomeRows = data && Array.isArray(data.outcome_correlations) ? data.outcome_correlations : [];
    const rangeRows = data && Array.isArray(data.range_summaries) ? data.range_summaries : [];
    const segmentSummary = data && data.segment_summaries || {};
    const recencyResearch = data && data.recency_research || null;
    const pairRows = useMemo_rl(() => {
      const raw = data && Array.isArray(data.interaction_candidates) && data.interaction_candidates.length ? data.interaction_candidates : data && Array.isArray(data.top_pairs) && data.top_pairs.length ? data.top_pairs : matrixRows;
      return [...raw].sort((a, b) => (b.research_score || b.abs_correlation || Math.abs(b.correlation || 0)) - (a.research_score || a.abs_correlation || Math.abs(a.correlation || 0)));
    }, [data, matrixRows]);
    let body = null;
    if (tab === "edge") {
      body = /* @__PURE__ */ React.createElement(EdgeRatioPanel, { baseUrl, wsStatus, runId });
    } else if (tab === "validation") {
      body = /* @__PURE__ */ React.createElement(_ValidationPanel, { baseUrl, runId, isDemo });
    } else if (tab === "feature") {
      body = /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(
        _CorrelationControls,
        {
          method,
          setMethod,
          axis,
          setAxis,
          loading,
          pooledTrades: data && data.pooled_trades,
          featureCount: data && data.feature_count
        }
      ), /* @__PURE__ */ React.createElement(FeatureImportancePanel, { baseUrl, wsStatus, runId }));
    } else if (isDemo || !runId) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC0C1\uAD00 \uBD84\uC11D\uC744 \uD45C\uC2DC\uD560 run \uCEE8\uD14D\uC2A4\uD2B8\uAC00 \uBD80\uC871\uD569\uB2C8\uB2E4." }));
    } else if (err) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC751\uB2F5\uC744 \uBC1B\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4: " + err }));
    } else if (loading && !data) {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(_ResearchEmptyState, { message: "\uC0C1\uAD00 \uBD84\uC11D\uC744 \uBD88\uB7EC\uC624\uB294 \uC911\u2026" }));
    } else if (tab === "correlation") {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(
        _CorrelationControls,
        {
          method,
          setMethod,
          axis,
          setAxis,
          loading,
          pooledTrades: data && data.pooled_trades,
          featureCount: data && data.feature_count
        }
      ), /* @__PURE__ */ React.createElement(_CorrelationHeatmap, { rows: matrixRows.length ? matrixRows : outcomeRows }), /* @__PURE__ */ React.createElement(_RangeSummaryList, { rows: rangeRows }), /* @__PURE__ */ React.createElement(_SegmentSummaryList, { summary: segmentSummary, axis }), /* @__PURE__ */ React.createElement(_RecencyResearchBadge, { recency: recencyResearch }));
    } else {
      body = /* @__PURE__ */ React.createElement("div", { className: "research-lab-panel" }, /* @__PURE__ */ React.createElement(
        _CorrelationControls,
        {
          method,
          setMethod,
          axis,
          setAxis,
          loading,
          pooledTrades: data && data.pooled_trades,
          featureCount: data && data.feature_count
        }
      ), /* @__PURE__ */ React.createElement(_CombinationList, { rows: pairRows }));
    }
    const shellStyle = fullscreen ? {
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      zIndex: 9999,
      background: "#0d1117",
      overflow: "auto",
      padding: "12px 18px"
    } : void 0;
    const activeOps = opsStrip && opsStrip.active || [];
    const recentOps = opsStrip && opsStrip.recent || [];
    const labMode = activeOps.length ? "\uC6B4\uC601(\uC2E4\uD589 \uC911)" : "\uC5F0\uAD6C(\uBD84\uC11D)";
    const flowActiveStage = activeOps.length ? 3 : -1;
    return /* @__PURE__ */ React.createElement("div", { className: "research-lab-shell", style: shellStyle }, /* @__PURE__ */ React.createElement(
      "div",
      {
        className: "research-tabs",
        role: "tablist",
        "aria-label": "Research Lab",
        style: { display: "flex", alignItems: "center" }
      },
      RESEARCH_TABS.map((item) => /* @__PURE__ */ React.createElement(
        "button",
        {
          key: item.id,
          type: "button",
          className: "research-tab" + (tab === item.id ? " active" : ""),
          onClick: () => setTab(item.id)
        },
        item.label
      )),
      /* @__PURE__ */ React.createElement(
        "button",
        {
          type: "button",
          className: "research-tab",
          style: { marginLeft: "auto" },
          title: "\uC2DC\uB4DC\u2192\uC0DD\uC131\u2192\uACA9\uC790\u2192\uBC31\uD14C\u2192\uAC8C\uC774\uD2B8\u2192OOS\u2192\uB3D9\uACB0 \uC804\uCCB4 \uD750\uB984\uACFC \uC6A9\uC5B4 \uBCF4\uAE30",
          onClick: () => setShowFlow(true)
        },
        "\u{1F9ED} \uD504\uB85C\uC138\uC2A4"
      ),
      /* @__PURE__ */ React.createElement(
        "a",
        {
          className: "research-tab",
          href: "/ui/pro.html",
          target: "_blank",
          rel: "noopener",
          style: { textDecoration: "none" },
          title: "\uD654\uBA74 \uC804\uCCB4\uB97C \uC4F0\uB294 \uC0C1\uC138 \uBD84\uC11D \uC6CC\uD06C\uC2A4\uD398\uC774\uC2A4(\uD788\uD2B8\uB9F5\xB7\uBA85\uC608\uC758\uC804\uB2F9\xB7\uBE44\uAD50\xB7\uD788\uC2A4\uD1A0\uB9AC)"
        },
        "\u{1F52C} \uB9AC\uC11C\uCE58 \uD504\uB85C"
      ),
      /* @__PURE__ */ React.createElement(
        "button",
        {
          type: "button",
          className: "research-tab",
          onClick: () => setFullscreen(!fullscreen)
        },
        fullscreen ? "\u2715 \uC804\uCCB4 \uD654\uBA74 \uB2EB\uAE30" : "\u26F6 \uC804\uCCB4 \uD654\uBA74"
      )
    ), /* @__PURE__ */ React.createElement("div", { className: "research-statusbar mono" }, /* @__PURE__ */ React.createElement("span", { className: "research-badge", title: "\uD604\uC7AC \uB9AC\uC11C\uCE58\uB7A9 \uBAA8\uB4DC \u2014 \uC2E4\uD589 \uC911 run\uC774 \uC788\uC73C\uBA74 '\uC6B4\uC601', \uC5C6\uC73C\uBA74 '\uC5F0\uAD6C(\uBD84\uC11D)'." }, /* @__PURE__ */ React.createElement("b", null, "\uBAA8\uB4DC"), " ", labMode), /* @__PURE__ */ React.createElement("span", { className: "research-badge", title: "\uC774 \uD328\uB110\uC774 \uBCF4\uC5EC\uC8FC\uB294 \uB300\uC0C1 \u2014 \uBD84\uC11D \uC911\uC778 run/\uC138\uB300 \uACB0\uACFC\uC758 \uAC74\uC218." }, /* @__PURE__ */ React.createElement("b", null, "\uB300\uC0C1"), " \uC2E4\uD589 ", activeOps.length, "\uAC74 \xB7 \uCD5C\uADFC\uC644\uB8CC ", recentOps.length, "\uAC74"), activeOps.length ? activeOps.map((a) => /* @__PURE__ */ React.createElement(
      "span",
      {
        key: a.run_id,
        className: "research-badge",
        title: `run ${a.run_id} \xB7 ${a.gens}\uC138\uB300 \xB7 \uB9C8\uC9C0\uB9C9 ${a.last_label || "\u2014"} \xB7 ${a.health === "active" ? "\uC815\uC0C1 \uC9C4\uD589" : "10\uBD84+ \uBB34\uC9C4\uD589(\uC815\uCCB4 \uC758\uC2EC)"}`
      },
      /* @__PURE__ */ React.createElement("b", null, a.health === "active" ? "\u{1F504} \uC9C4\uD589" : "\u26A0\uFE0F \uC815\uCCB4"),
      " ",
      a.run_id,
      " \xB7 ",
      a.gens,
      "\uC138\uB300"
    )) : /* @__PURE__ */ React.createElement("span", { className: "research-badge", title: "\uD604\uC7AC \uC2E4\uD589 \uC911\uC778 \uC9C4\uD654 \uC791\uC5C5\uC774 \uC5C6\uC2B5\uB2C8\uB2E4(\uBD84\uC11D \uC804\uC6A9)." }, /* @__PURE__ */ React.createElement("b", null, "\uC0C1\uD0DC"), " \uC2E4\uD589 \uC911 \uC791\uC5C5 \uC5C6\uC74C")), body, showFlow && (typeof window.ResearchProcessFlowOverlay === "function" ? React.createElement(window.ResearchProcessFlowOverlay, {
      onClose: () => setShowFlow(false),
      liveState: activeOps.length ? { status: "running" } : null,
      ops: opsStrip
    }) : /* @__PURE__ */ React.createElement(_RlProcessFlowOverlay, { onClose: () => setShowFlow(false), activeStage: flowActiveStage })));
  }
  Object.assign(window, { ResearchLabPanel });

  // ../frontend/app.jsx
  var { useState: useState_a, useEffect: useEffect_a, useCallback: useCallback_a } = React;
  function App() {
    var _a, _b, _c, _d, _e, _f, _g, _h, _i;
    const [baseUrl, setBaseUrl] = useState_a(() => {
      const cached = localStorage.getItem("stom_base_url");
      const here = typeof window !== "undefined" && window.location && window.location.origin || "";
      if (cached && here.startsWith("http")) {
        try {
          if (new URL(cached).origin !== here) return DEFAULT_BASE;
        } catch (e) {
          return DEFAULT_BASE;
        }
      }
      return cached || DEFAULT_BASE;
    });
    const [pendingBase, setPendingBase] = useState_a(baseUrl);
    const [theme, setTheme] = useState_a(() => localStorage.getItem("stom_theme") || "dark");
    const [activeTab, setActiveTab] = useState_a(() => localStorage.getItem("stom_active_tab") || "evolution");
    const [simVisited, setSimVisited] = useState_a(() => (localStorage.getItem("stom_active_tab") || "evolution") === "simulation");
    useEffect_a(() => {
      if (activeTab === "simulation") setSimVisited(true);
    }, [activeTab]);
    const { state: liveState, health, wsStatus, configSpec, send, lastReply, reconnect } = useBackend(baseUrl);
    const [settingsOpen, setSettingsOpen] = useState_a(false);
    const [approvalOpen, setApprovalOpen] = useState_a(false);
    const [codeViewGen, setCodeViewGen] = useState_a(null);
    const [selectedDetailGen, setSelectedDetailGen] = useState_a(null);
    const [selectedRun, setSelectedRun] = useState_a("");
    const [runList, setRunList] = useState_a([]);
    const [fetchedRunState, setFetchedRunState] = useState_a(null);
    const isDemoSrc = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
    useEffect_a(() => {
      if (isDemoSrc || !baseUrl) {
        setRunList([]);
        return;
      }
      let cancelled = false;
      fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(3e3) }).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      }).catch(() => {
        if (!cancelled) setRunList([]);
      });
      return () => {
        cancelled = true;
      };
    }, [baseUrl, isDemoSrc, liveState.run_id, liveState.status]);
    const fetchRunState = useCallback_a(() => {
      if (!selectedRun || isDemoSrc || !baseUrl) {
        setFetchedRunState(null);
        return;
      }
      fetch(
        baseUrl + "/run_state?run_id=" + encodeURIComponent(selectedRun),
        { signal: AbortSignal.timeout(4e3) }
      ).then((r) => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))).then((j) => setFetchedRunState(j)).catch(() => setFetchedRunState(null));
    }, [baseUrl, selectedRun, isDemoSrc]);
    useEffect_a(() => {
      if (!selectedRun) {
        setFetchedRunState(null);
        return;
      }
      fetchRunState();
      const id = setInterval(fetchRunState, 3e4);
      return () => clearInterval(id);
    }, [fetchRunState, selectedRun]);
    const state = selectedRun && fetchedRunState ? fetchedRunState : liveState;
    const running = state.status === "running" || state.status === "stopping";
    useEffect_a(() => {
      localStorage.setItem("stom_base_url", baseUrl);
    }, [baseUrl]);
    useEffect_a(() => {
      document.documentElement.setAttribute("data-theme", theme);
      localStorage.setItem("stom_theme", theme);
    }, [theme]);
    useEffect_a(() => {
      localStorage.setItem("stom_active_tab", activeTab);
    }, [activeTab]);
    const onStart = useCallback_a((config) => {
      send({ action: "start", config });
      setSettingsOpen(false);
    }, [send]);
    const onStop = useCallback_a(() => {
      send({ action: "stop" });
    }, [send]);
    const onApprove = useCallback_a(({ userBuy, userSell }) => {
      if (!state.winner) return;
      send({
        action: "final_approval",
        buy_name: state.winner.buy_name,
        sell_name: state.winner.sell_name,
        user_buy: userBuy,
        user_sell: userSell
      });
      setApprovalOpen(false);
    }, [send, state.winner]);
    const onViewCodeByGen = useCallback_a((genNo) => {
      const g = (state.generations || []).find((x) => x.gen_no === genNo);
      if (g) setCodeViewGen(g);
    }, [state.generations]);
    const mddCap = (_b = (_a = configSpec.find((f) => f.name === "mdd_cap")) == null ? void 0 : _a.default) != null ? _b : 15;
    const minDailyTrades = (_d = (_c = configSpec.find((f) => f.name === "min_daily_trades")) == null ? void 0 : _c.default) != null ? _d : 0.5;
    const targetScore = (_f = (_e = configSpec.find((f) => f.name === "target_score")) == null ? void 0 : _e.default) != null ? _f : 1;
    const pct = state.max_generations > 0 ? Math.min(100, state.current_gen / state.max_generations * 100) : 0;
    const isIdle = state.status === "idle" && state.generations.length === 0 && !running;
    return /* @__PURE__ */ React.createElement("div", { style: { minHeight: "100vh", padding: "16px", maxWidth: 1600, margin: "0 auto" } }, /* @__PURE__ */ React.createElement("header", { style: { marginBottom: 16 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", marginBottom: 12 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", gap: 10 } }, /* @__PURE__ */ React.createElement(Logo, null), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", lineHeight: 1.15 } }, /* @__PURE__ */ React.createElement("h1", { style: { fontSize: 15, letterSpacing: ".01em" } }, "STOM AI \xB7 \uC870\uAC74\uC2DD \uC790\uC728 \uC9C4\uD654 \uB300\uC2DC\uBCF4\uB4DC"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".08em" } }, "autonomous_strategy_loop \xB7 contract_v", (_h = (_g = health.contract_version) != null ? _g : state.contract_version) != null ? _h : 1)), /* @__PURE__ */ React.createElement("nav", { className: "stom-pagenav mono", "aria-label": "\uD604\uC7AC \uC704\uCE58" }, /* @__PURE__ */ React.createElement(
      "span",
      {
        className: "stom-pagenav-item stom-pagenav-active",
        title: "\uD604\uC7AC \uBCF4\uACE0 \uC788\uB294 \uD0ED(\uC544\uB798 \uD0ED\uBC14\uB85C \uC804\uD658)"
      },
      (() => {
        const cur = STOM_TABS.find((t) => t.key === activeTab);
        return cur ? `${cur.icon} ${cur.label}` : "STOM";
      })()
    ))), /* @__PURE__ */ React.createElement("div", { style: { marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" } }, /* @__PURE__ */ React.createElement(ThemeToggle, { theme, onChange: setTheme }), /* @__PURE__ */ React.createElement(
      BaseUrlControl,
      {
        value: pendingBase,
        onChange: setPendingBase,
        onApply: () => setBaseUrl(pendingBase),
        onReconnect: reconnect
      }
    ), /* @__PURE__ */ React.createElement(ConnBadge, { health, wsStatus }), /* @__PURE__ */ React.createElement(StatusBadge, { status: state.status }))), /* @__PURE__ */ React.createElement(TabNav, { activeTab, onSelect: setActiveTab }), activeTab === "evolution" && /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 14,
      padding: "12px 16px",
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: 8
    } }, /* @__PURE__ */ React.createElement("div", { style: { minWidth: 200 } }, /* @__PURE__ */ React.createElement("div", { className: "stat-label", style: { marginBottom: 4 } }, "\uC9C4\uD589\uB3C4"), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 15, color: "var(--ink-0)" } }, /* @__PURE__ */ React.createElement("span", { style: { color: running ? "var(--amber)" : "var(--ink-0)" } }, state.current_gen), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-3)" } }, " / ", state.max_generations), /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 8, color: "var(--ink-2)", fontSize: 11 } }, "\uC138\uB300"))), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, minWidth: 200 } }, /* @__PURE__ */ React.createElement("div", { className: "progress-track" }, /* @__PURE__ */ React.createElement("div", { className: `progress-fill ${running ? "running" : ""}`, style: { width: `${pct}%` } })), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" } }, /* @__PURE__ */ React.createElement("span", null, "provider=", state.provider), /* @__PURE__ */ React.createElement("span", null, "tf=", state.bt_timeframe), /* @__PURE__ */ React.createElement("span", null, "run_id=", state.run_id || "\u2014"), /* @__PURE__ */ React.createElement("span", null, pct.toFixed(1), "%"))), /* @__PURE__ */ React.createElement(
      RunSelector,
      {
        runList,
        selectedRun,
        onSelect: setSelectedRun,
        onRefresh: fetchRunState,
        disabled: isDemoSrc
      }
    ), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 8 } }, /* @__PURE__ */ React.createElement("button", { className: "btn primary", onClick: () => setSettingsOpen(true), disabled: running }, "\u25B8 \uC2DC\uC791"), /* @__PURE__ */ React.createElement("button", { className: "btn danger", onClick: onStop, disabled: !running }, "\u25FC \uC815\uC9C0")))), simVisited && /* @__PURE__ */ React.createElement("div", { style: { display: activeTab === "simulation" ? void 0 : "none" } }, /* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(SimulationTab, { baseUrl, wsStatus }))), activeTab === "backtest" ? /* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(BacktestTab, { baseUrl, wsStatus })) : activeTab === "simulation" ? null : activeTab === "lab" ? /* @__PURE__ */ React.createElement(ErrorBoundary, null, window.LabPage ? /* @__PURE__ */ React.createElement(window.LabPage, { baseUrl }) : /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { padding: "12px 16px" } }, "\uC5F0\uAD6C\uC2E4 \uB85C\uB529 \uC911\u2026")) : activeTab === "pro" ? /* @__PURE__ */ React.createElement(ErrorBoundary, null, window.ProPage ? /* @__PURE__ */ React.createElement(window.ProPage, { baseUrl }) : /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { padding: "12px 16px" } }, "\uBD84\uC11D \uD504\uB85C \uB85C\uB529 \uC911\u2026")) : activeTab === "verdict" ? /* @__PURE__ */ React.createElement(ErrorBoundary, null, window.VerdictPanel ? /* @__PURE__ */ React.createElement(window.VerdictPanel, { baseUrl }) : /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { padding: "12px 16px" } }, "\uACB0\uC815 \uC774\uB825 \uB85C\uB529 \uC911\u2026")) : activeTab === "process" ? /* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(
      "iframe",
      {
        src: baseUrl + "/process_flow",
        title: "\uD504\uB85C\uC138\uC2A4 \uD750\uB984",
        style: { width: "100%", height: "calc(100vh - 130px)", border: "none", borderRadius: 8, background: "#0d1117" }
      }
    )) : isIdle ? /* @__PURE__ */ React.createElement(IdleState, { onStart: () => setSettingsOpen(true), configSpec }) : /* @__PURE__ */ React.createElement("main", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement(ExportStatusBanner, { reply: lastReply }), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_runmon", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "Run Monitor" }) }, /* @__PURE__ */ React.createElement(CurrentGenPanel, { state }), /* @__PURE__ */ React.createElement(ResearchCriteriaBanner, { state, baseUrl }), /* @__PURE__ */ React.createElement(ResearchGlossaryPanel, null), /* @__PURE__ */ React.createElement(ActiveStrategyPanel, { state, baseUrl, onViewCode: onViewCodeByGen }), /* @__PURE__ */ React.createElement(PhaseTimeline, { state }), /* @__PURE__ */ React.createElement(ProcessFlowPanel, { state }), /* @__PURE__ */ React.createElement(PhaseDetailPanel, { state, wsStatus }), /* @__PURE__ */ React.createElement(EnginePanel, { state, wsStatus })), /* @__PURE__ */ React.createElement("div", { className: "grid-main" }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 14, minWidth: 0 } }, window.ResearchHeatmapPanel ? /* @__PURE__ */ React.createElement(window.ResearchHeatmapPanel, { baseUrl, wsStatus, runId: state.run_id }) : null, /* @__PURE__ */ React.createElement(FitnessChart, { state, target: targetScore }), /* @__PURE__ */ React.createElement(ProfitChart, { state, targetPct: 0 }), /* @__PURE__ */ React.createElement(EquityOverlayChart, { baseUrl, wsStatus, runId: state.run_id }), /* @__PURE__ */ React.createElement(
      BacktestDetailChart,
      {
        baseUrl,
        wsStatus,
        state,
        externalSelGen: selectedDetailGen
      }
    ), /* @__PURE__ */ React.createElement(QualityTrendChart, { state }), /* @__PURE__ */ React.createElement(HallOfFamePanel, { baseUrl, wsStatus }), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_strategy", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "Strategy / Prompt" }) }, /* @__PURE__ */ React.createElement(
      GenerationsTable,
      {
        state,
        mddCap,
        minDailyTrades,
        onViewCode: (g) => setCodeViewGen(g),
        onSelectDetail: (genNo) => setSelectedDetailGen(genNo)
      }
    )), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_compare", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "Compare" }) }, /* @__PURE__ */ React.createElement(RunComparePanel, { baseUrl, wsStatus })), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_genanalytics", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "Generation Analytics" }) }, /* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(EvolutionAnalysisPanel, { baseUrl, wsStatus, runId: state.run_id || "", onOpenWorkbench: () => setActiveTab("backtest") })))), /* @__PURE__ */ React.createElement("aside", { style: { display: "flex", flexDirection: "column", gap: 14 } }, /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_researchlab", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "Research Lab" }) }, /* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(ResearchLabPanel, { baseUrl, wsStatus, runId: state.run_id || "" })), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: () => setActiveTab("lab"),
        style: { alignSelf: "flex-start", marginTop: 2 },
        title: "\uC5F0\uAD6C \uC704\uD0A4 \xB7 AI \uCEE8\uD14D\uC2A4\uD2B8 \uD329\uC740 \uC5F0\uAD6C\uC2E4 \uD0ED\uC73C\uB85C \uC774\uB3D9\uD588\uC2B5\uB2C8\uB2E4"
      },
      "\u{1F4DA} \uC5F0\uAD6C \uC704\uD0A4 \xB7 AI \uCEE8\uD14D\uC2A4\uD2B8 \uD329 \u2192 \uC5F0\uAD6C\uC2E4 \uD0ED"
    )), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_analysis", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "\uC9C4\uD654 \uBD84\uC11D \xB7 P1~P5" }) }, /* @__PURE__ */ React.createElement(HypothesisPanel, { state }), /* @__PURE__ */ React.createElement(AutopsyPanel, { state, wsStatus }), /* @__PURE__ */ React.createElement(PopulationPanel, { state, wsStatus }), /* @__PURE__ */ React.createElement(LineagePanel, { state, wsStatus }), /* @__PURE__ */ React.createElement(MetaPanel, { state, wsStatus }), /* @__PURE__ */ React.createElement(HoldoutPanel, { state, wsStatus })), /* @__PURE__ */ React.createElement(_EvoSection, { storageKey: "stom_evo_verdict", label: /* @__PURE__ */ React.createElement(SectionLabel, { text: "\uD310\uC815 \xB7 Best / Winner" }) }, state.best && state.winner && state.best.gen === state.winner.gen ? /* @__PURE__ */ React.createElement(
      MergedBestWinnerCard,
      {
        best: state.best,
        winner: state.winner,
        onApprove: () => setApprovalOpen(true),
        onViewCode: onViewCodeByGen
      }
    ) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(BestCard, { best: state.best, onViewCode: onViewCodeByGen }), /* @__PURE__ */ React.createElement(
      WinnerCard,
      {
        winner: state.winner,
        onApprove: () => setApprovalOpen(true),
        onViewCode: onViewCodeByGen
      }
    )), /* @__PURE__ */ React.createElement(ActiveConfigPanel, { state }), /* @__PURE__ */ React.createElement(CostPanel, { state, cap: 5e4 }), /* @__PURE__ */ React.createElement(FeedbackPanel, { state }))))), /* @__PURE__ */ React.createElement(
      SettingsModal,
      {
        open: settingsOpen,
        onClose: () => setSettingsOpen(false),
        onStart,
        configSpec,
        disabled: running
      }
    ), /* @__PURE__ */ React.createElement(
      ApprovalDialog,
      {
        winner: approvalOpen ? state.winner : null,
        onClose: () => setApprovalOpen(false),
        onConfirm: onApprove
      }
    ), /* @__PURE__ */ React.createElement(
      CodeViewer,
      {
        generation: codeViewGen,
        onClose: () => setCodeViewGen(null),
        runId: state.run_id,
        baseUrl
      }
    ), /* @__PURE__ */ React.createElement("footer", { style: { marginTop: 24, padding: "12px 0", textAlign: "center", color: "var(--ink-3)", fontSize: 10.5, fontFamily: "var(--mono)" } }, "STOM AI \xB7 STATE_CONTRACT v", (_i = state.contract_version) != null ? _i : 1, " \xB7 last_update ", fmtTime(state.updated_at)));
  }
  var STOM_TABS = [
    { key: "evolution", label: "\uC9C4\uD654 \uB300\uC2DC\uBCF4\uB4DC", icon: "\u{1F9EC}" },
    { key: "backtest", label: "\uBC31\uD14C\uC2A4\uD2B8", icon: "\u{1F4CA}" },
    { key: "simulation", label: "\uCC28\uD2B8 \uC2DC\uBBAC\uB808\uC774\uC158", icon: "\u{1F4C8}" },
    { key: "lab", label: "\uC5F0\uAD6C\uC2E4", icon: "\u{1F52C}" },
    { key: "pro", label: "\uBD84\uC11D \uD504\uB85C", icon: "\u{1F4CA}" },
    { key: "verdict", label: "\uACB0\uC815 \uC774\uB825", icon: "\u2696\uFE0F" },
    { key: "process", label: "\uD504\uB85C\uC138\uC2A4 \uD750\uB984", icon: "\u{1F5FA}\uFE0F" }
  ];
  function TabNav({ activeTab, onSelect }) {
    return /* @__PURE__ */ React.createElement("nav", { role: "tablist", "aria-label": "\uB300\uC2DC\uBCF4\uB4DC \uD0ED", className: "stom-tabnav" }, STOM_TABS.map((tab) => {
      const active = activeTab === tab.key;
      return /* @__PURE__ */ React.createElement(
        "button",
        {
          key: tab.key,
          role: "tab",
          "aria-selected": active,
          className: "stom-tab" + (active ? " stom-tab-active" : ""),
          onClick: () => onSelect(tab.key)
        },
        /* @__PURE__ */ React.createElement("span", { className: "stom-tab-ico", "aria-hidden": "true" }, tab.icon),
        tab.label
      );
    }));
  }
  function SectionLabel({ text }) {
    return /* @__PURE__ */ React.createElement("div", { className: "stom-section-label" }, text);
  }
  function _EvoSection({ storageKey, label, children }) {
    const [open, setOpen] = useState_a(() => {
      try {
        const v = window.localStorage.getItem(storageKey);
        return v === null ? true : v === "1";
      } catch (e) {
        return true;
      }
    });
    const onToggle = (e) => {
      const o = e.currentTarget.open;
      setOpen(o);
      try {
        window.localStorage.setItem(storageKey, o ? "1" : "0");
      } catch (e2) {
      }
    };
    return /* @__PURE__ */ React.createElement("details", { className: "evo-group", open, onToggle }, /* @__PURE__ */ React.createElement("summary", { className: "evo-group-summary", "aria-expanded": open }, label), /* @__PURE__ */ React.createElement("div", { className: "evo-group-body" }, children));
  }
  function ThemeToggle({ theme, onChange }) {
    return /* @__PURE__ */ React.createElement("div", { className: "theme-toggle", role: "group", "aria-label": "\uD14C\uB9C8" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: theme === "dark" ? "active" : "",
        onClick: () => onChange("dark"),
        "data-tip": "\uB2E4\uD06C \uBAA8\uB4DC"
      },
      /* @__PURE__ */ React.createElement(SunMoonIcon, { dark: true }),
      " Dark"
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: theme === "light" ? "active" : "",
        onClick: () => onChange("light"),
        "data-tip": "\uB77C\uC774\uD2B8 \uBAA8\uB4DC"
      },
      /* @__PURE__ */ React.createElement(SunMoonIcon, null),
      " Light"
    ));
  }
  function SunMoonIcon({ dark }) {
    if (dark) return /* @__PURE__ */ React.createElement("svg", { width: "12", height: "12", viewBox: "0 0 16 16", fill: "none" }, /* @__PURE__ */ React.createElement(
      "path",
      {
        d: "M11.5 9.5A6 6 0 0 1 6 4c0-1.2.36-2.3.97-3.23A8 8 0 1 0 14.73 11a6 6 0 0 1-3.23.5z",
        fill: "currentColor"
      }
    ));
    return /* @__PURE__ */ React.createElement("svg", { width: "12", height: "12", viewBox: "0 0 16 16", fill: "none" }, /* @__PURE__ */ React.createElement("circle", { cx: "8", cy: "8", r: "3", fill: "currentColor" }), /* @__PURE__ */ React.createElement("g", { stroke: "currentColor", strokeWidth: "1.2", strokeLinecap: "round" }, /* @__PURE__ */ React.createElement("line", { x1: "8", y1: "1", x2: "8", y2: "2.5" }), /* @__PURE__ */ React.createElement("line", { x1: "8", y1: "13.5", x2: "8", y2: "15" }), /* @__PURE__ */ React.createElement("line", { x1: "1", y1: "8", x2: "2.5", y2: "8" }), /* @__PURE__ */ React.createElement("line", { x1: "13.5", y1: "8", x2: "15", y2: "8" }), /* @__PURE__ */ React.createElement("line", { x1: "3", y1: "3", x2: "4", y2: "4" }), /* @__PURE__ */ React.createElement("line", { x1: "12", y1: "12", x2: "13", y2: "13" }), /* @__PURE__ */ React.createElement("line", { x1: "13", y1: "3", x2: "12", y2: "4" }), /* @__PURE__ */ React.createElement("line", { x1: "4", y1: "12", x2: "3", y2: "13" })));
  }
  function Logo() {
    return /* @__PURE__ */ React.createElement("svg", { width: "36", height: "36", viewBox: "0 0 36 36", fill: "none" }, /* @__PURE__ */ React.createElement("rect", { x: "0.5", y: "0.5", width: "35", height: "35", rx: "6", fill: "#0c1014", stroke: "#2a3441" }), /* @__PURE__ */ React.createElement(
      "path",
      {
        d: "M5 26 L11 22 L16 24 L21 16 L26 18 L31 9",
        stroke: "#4cd6b3",
        strokeWidth: "1.5",
        fill: "none",
        strokeLinecap: "round",
        strokeLinejoin: "round"
      }
    ), /* @__PURE__ */ React.createElement("circle", { cx: "11", cy: "22", r: "1.6", fill: "#4cd6b3" }), /* @__PURE__ */ React.createElement("circle", { cx: "16", cy: "24", r: "1.6", fill: "#4cd6b3" }), /* @__PURE__ */ React.createElement("circle", { cx: "21", cy: "16", r: "1.6", fill: "#4cd6b3" }), /* @__PURE__ */ React.createElement("circle", { cx: "26", cy: "18", r: "1.6", fill: "#4cd6b3" }), /* @__PURE__ */ React.createElement("circle", { cx: "31", cy: "9", r: "2.2", fill: "#a594ff", stroke: "#fff", strokeWidth: "0.6" }), /* @__PURE__ */ React.createElement("path", { d: "M3 3 L7 3 M3 3 L3 7", stroke: "#2a3441", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("path", { d: "M33 33 L29 33 M33 33 L33 29", stroke: "#2a3441", strokeWidth: "1" }));
  }
  function BaseUrlControl({ value, onChange, onApply, onReconnect }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      background: "var(--bg-1)",
      border: "1px solid var(--line-1)",
      borderRadius: 5,
      padding: "3px 6px"
    } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", letterSpacing: ".08em" } }, "BASE"), /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "toolbar-input",
        value,
        onChange: (e) => onChange(e.target.value),
        onKeyDown: (e) => {
          if (e.key === "Enter") onApply();
        },
        spellCheck: false
      }
    ), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onApply, "data-tip": "Base URL \uC801\uC6A9 \uD6C4 \uC7AC\uC5F0\uACB0" }, "\uC801\uC6A9"), /* @__PURE__ */ React.createElement("button", { className: "btn ghost sm", onClick: onReconnect, "data-tip": "\uD604\uC7AC URL\uB85C \uC7AC\uC5F0\uACB0" }, "\u21BB"));
  }
  function RunSelector({ runList, selectedRun, onSelect, onRefresh, disabled }) {
    return /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      background: "var(--bg-0)",
      border: "1px solid var(--line-1)",
      borderRadius: 5,
      padding: "3px 6px"
    } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: { fontSize: 10, color: "var(--ink-3)", letterSpacing: ".08em" } }, "RUN"), /* @__PURE__ */ React.createElement(
      "select",
      {
        value: selectedRun,
        onChange: (e) => onSelect(e.target.value),
        disabled,
        className: "mono",
        "data-tip": "\uBCFC run \uC120\uD0DD \u2014 LIVE(\uD604\uC7AC) \uB610\uB294 \uACFC\uAC70 \uC2E4 run",
        style: {
          fontSize: 11,
          background: "var(--bg-1)",
          color: "var(--ink-0)",
          border: "1px solid var(--line-2)",
          borderRadius: 5,
          padding: "3px 6px",
          maxWidth: 200
        }
      },
      /* @__PURE__ */ React.createElement("option", { value: "" }, "LIVE(\uD604\uC7AC)"),
      (runList || []).map((r) => /* @__PURE__ */ React.createElement("option", { key: r.run_id, value: r.run_id }, r.run_id, r.label ? " \xB7 " + r.label : "", r.gate_passed_count > 0 ? " \u2713" : ""))
    ), selectedRun && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn ghost sm",
        onClick: onRefresh,
        disabled,
        "data-tip": "\uC120\uD0DD run \uC0C8\uB85C\uACE0\uCE68"
      },
      "\u21BB"
    ));
  }
  function IdleState({ onStart, configSpec }) {
    return /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { style: {
      padding: "10px 14px",
      background: "linear-gradient(90deg, rgba(240,179,90,0.10), rgba(240,179,90,0.02))",
      border: "1px solid rgba(240,179,90,0.32)",
      borderRadius: 6,
      marginBottom: 14,
      display: "flex",
      alignItems: "center",
      gap: 12,
      fontSize: 12,
      color: "var(--ink-1)"
    } }, /* @__PURE__ */ React.createElement("span", { style: { fontSize: 16 } }, "\u{1F4A1}"), /* @__PURE__ */ React.createElement("span", null, /* @__PURE__ */ React.createElement("strong", { style: { color: "var(--amber)" } }, "\uB300\uC2DC\uBCF4\uB4DC\uB294 \uC9C4\uD654 \uC2DC\uC791 \uD6C4 \uD65C\uC131\uD654\uB429\uB2C8\uB2E4."), " ", "\uC544\uB798 ", /* @__PURE__ */ React.createElement("span", { className: "mono", style: { color: "var(--ink-0)" } }, "\u25B8 \uC9C4\uD654 \uC2DC\uC791 \uC124\uC815 \uC5F4\uAE30"), "\uB97C \uB204\uB974\uBA74 \uD398\uC774\uC988 \uD0C0\uC784\uB77C\uC778(\uC0DD\uC131\u2192\uBC31\uD14C\u2192\uCC44\uC810\u2192\uBD80\uAC80), \uC5D4\uC9C4 \uBA54\uD2B8\uB9AD, \uC790\uBCF8\uACE1\uC120, \uC810\uC218 \uBD84\uD574, \uBD80\uAC80 \uC2A4\uD2B8\uB9AC\uBC0D\uC774 \uC2E4\uC2DC\uAC04\uC73C\uB85C \uBCF4\uC785\uB2C8\uB2E4."), /* @__PURE__ */ React.createElement("button", { className: "btn primary", style: { marginLeft: "auto" }, onClick: onStart }, "\u25B8 \uC2DC\uC791")), /* @__PURE__ */ React.createElement("div", { style: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot", style: { background: "var(--teal)" } }), "Welcome")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: "28px 24px" } }, /* @__PURE__ */ React.createElement("h2", { style: { fontSize: 22, marginBottom: 10, letterSpacing: "-0.01em" } }, "\uB8E8\uD504\uB97C \uC2DC\uC791\uD560 \uC900\uBE44\uAC00 \uB418\uC5C8\uC2B5\uB2C8\uB2E4."), /* @__PURE__ */ React.createElement("p", { style: { color: "var(--ink-1)", lineHeight: 1.6, marginBottom: 22, fontSize: 13 } }, "AI\uAC00 \uD55C\uAD6D \uC8FC\uC2DD \uB9E4\uC218/\uB9E4\uB3C4 \uC804\uB7B5 \uCF54\uB4DC\uB97C \uC790\uB3D9 \uC0DD\uC131\xB7\uBC31\uD14C\uC2A4\uD2B8\xB7\uCC44\uC810\xB7\uBC18\uBCF5\uD569\uB2C8\uB2E4. \uAC01 \uC138\uB300\uC758 \uBD80\uAC80(autopsy)\uC774 \uB2E4\uC74C \uC138\uB300 \uC0DD\uC131\uAE30\uC5D0 \uD53C\uB4DC\uBC31\uB418\uC5B4 \uC870\uAC74\uC2DD\uC774 \uC810\uC9C4\uC801\uC73C\uB85C \uC9C4\uD654\uD569\uB2C8\uB2E4.", /* @__PURE__ */ React.createElement("br", null), /* @__PURE__ */ React.createElement("br", null), /* @__PURE__ */ React.createElement("span", { style: { color: "var(--ink-2)" } }, "\uBAA9\uD45C \uC810\uC218\uC640 MDD \uC0C1\uD55C\uC744 \uB3D9\uC2DC\uC5D0 \uB9CC\uC871\uD558\uBA74 \uD558\uB4DC \uAC8C\uC774\uD2B8\uB97C \uD1B5\uACFC\uD55C \uC6B0\uC2B9 \uC804\uB7B5\uC73C\uB85C \uB4F1\uB85D\uB418\uACE0,", /* @__PURE__ */ React.createElement("br", null), "\uC0AC\uC6A9\uC790\uC758 \uBA85\uC2DC\uC801 \uC2B9\uC778 \uD6C4\uC5D0\uB9CC \uC6B4\uC601 strategy.db\uB85C export \uB429\uB2C8\uB2E4.")), /* @__PURE__ */ React.createElement("button", { className: "btn primary lg", onClick: onStart }, "\u25B8 \uC9C4\uD654 \uC2DC\uC791 \uC124\uC815 \uC5F4\uAE30"))), /* @__PURE__ */ React.createElement("div", { className: "panel" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd" }, /* @__PURE__ */ React.createElement("div", { className: "panel-hd-title" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "\uB8E8\uD504 \uAC1C\uC694")), /* @__PURE__ */ React.createElement("div", { className: "panel-bd", style: { padding: 0 } }, /* @__PURE__ */ React.createElement("ol", { style: { margin: 0, padding: 0, listStyle: "none" } }, [
      { n: 1, k: "\uC0DD\uC131", d: "LLM\uC774 \uC9C1\uC804 \uBD80\uAC80\uC744 \uCEE8\uD14D\uC2A4\uD2B8\uB85C \uB9E4\uC218/\uB9E4\uB3C4 \uC804\uB7B5 \uCF54\uB4DC\uB97C \uC0DD\uC131 (\uC2E4\uC2DC\uAC04 \uC2A4\uD2B8\uB9AC\uBC0D \uD45C\uC2DC)" },
      { n: 2, k: "\uBC31\uD14C\uC2A4\uD2B8", d: "\uC9C0\uC815\uB41C \uC2DC\uAC04\uB2E8\uC704\xB7\uC2A4\uCF54\uD504\xB7\uC708\uB3C4\uC6B0\uB85C \uC790\uBCF8\uACE1\uC120\xB7\uB099\uD3ED\xB7\uB9E4\uB9E4\uB97C \uC2DC\uBBAC\uB808\uC774\uC158" },
      { n: 3, k: "\uCC44\uC810", d: "graded_score = \uC190\uC775\xB7MDD\xB7\uAC70\uB798\uC218\xB7\uC77C\uAD00\uC131\uC758 \uAC00\uC911\uD569 (\uBA54\uD2B8\uB9AD\uBCC4 \uBD84\uD574 \uD45C\uC2DC)" },
      { n: 4, k: "\uAC8C\uC774\uD2B8", d: "score \u2265 target & MDD \u2264 cap & trades \u2265 min \u2192 \uD1B5\uACFC" },
      { n: 5, k: "\uBD80\uAC80", d: "\uD0C8\uB77D \uC6D0\uC778\uC744 \uC790\uC5F0\uC5B4\uB85C \uC694\uC57D \u2192 \uB2E4\uC74C \uC138\uB300 \uCEE8\uD14D\uC2A4\uD2B8\uC5D0 \uC8FC\uC785" },
      { n: 6, k: "\uC2B9\uC778", d: "\uD1B5\uACFC \uC804\uB7B5\uC744 \uC6B4\uC601 DB\uB85C export (\uC0AC\uC6A9\uC790 \uBA85\uC2DC\uC801 \uD655\uC778 \uD544\uC694)" }
    ].map((s, i, arr) => /* @__PURE__ */ React.createElement("li", { key: s.n, style: {
      padding: "12px 16px",
      borderBottom: i < arr.length - 1 ? "1px solid var(--line-1)" : "none",
      display: "flex",
      gap: 12,
      alignItems: "flex-start"
    } }, /* @__PURE__ */ React.createElement("span", { className: "mono", style: {
      width: 22,
      height: 22,
      borderRadius: "50%",
      background: "var(--bg-0)",
      border: "1px solid var(--line-2)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontSize: 11,
      color: "var(--ink-1)",
      flexShrink: 0
    } }, s.n), /* @__PURE__ */ React.createElement("div", { style: { flex: 1 } }, /* @__PURE__ */ React.createElement("div", { style: { fontSize: 13, color: "var(--ink-0)", marginBottom: 2 } }, s.k), /* @__PURE__ */ React.createElement("div", { style: { fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 } }, s.d)))))))));
  }
  var ErrorBoundary = class extends React.Component {
    constructor(props) {
      super(props);
      this.state = { error: null };
    }
    static getDerivedStateFromError(error) {
      return { error };
    }
    componentDidCatch(error, info) {
      console.error("Dashboard render error:", error, info);
    }
    render() {
      if (this.state.error) {
        const msg = String(this.state.error && this.state.error.stack || this.state.error);
        return /* @__PURE__ */ React.createElement("div", { style: { padding: 40, fontFamily: "system-ui, sans-serif", background: "#0c1014", minHeight: "100vh" } }, /* @__PURE__ */ React.createElement("h2", { style: { color: "#ff8a8a", fontSize: 16, marginBottom: 8 } }, "\uB300\uC2DC\uBCF4\uB4DC \uB80C\uB354 \uC624\uB958"), /* @__PURE__ */ React.createElement("p", { style: { color: "#9fb0c0", fontSize: 13, marginBottom: 12 } }, "\uC77C\uBD80 \uB370\uC774\uD130\uC5D0\uC11C \uB80C\uB354 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4. ", /* @__PURE__ */ React.createElement("b", null, "Ctrl+Shift+R"), "\uB85C \uC0C8\uB85C\uACE0\uCE68\uD558\uAC70\uB098 \uC0C1\uB2E8 RUN \uC140\uB809\uD130\uC5D0\uC11C \uB2E4\uB978 run\uC744 \uC120\uD0DD\uD574 \uBCF4\uC138\uC694."), /* @__PURE__ */ React.createElement("pre", { style: { color: "#caa", fontSize: 11, whiteSpace: "pre-wrap", background: "#11161c", padding: 12, borderRadius: 6, overflow: "auto", maxHeight: 300 } }, msg), /* @__PURE__ */ React.createElement(
          "button",
          {
            onClick: () => location.reload(),
            style: { marginTop: 12, padding: "6px 14px", background: "#1a2530", color: "#cfe0f0", border: "1px solid #2a3441", borderRadius: 5, cursor: "pointer" }
          },
          "\uC0C8\uB85C\uACE0\uCE68"
        ));
      }
      return this.props.children;
    }
  };
  Object.assign(window, { App, ErrorBoundary });
  if (typeof window === "undefined" || !window.__STOM_NO_AUTO_MOUNT__) {
    const root = ReactDOM.createRoot(document.getElementById("root"));
    root.render(/* @__PURE__ */ React.createElement(ErrorBoundary, null, /* @__PURE__ */ React.createElement(App, null)));
  }

  // ../frontend/dashboard-pages.jsx
  var { useState: useState_dp, useEffect: useEffect_dp } = React;
  function _DpLoading({ name }) {
    return /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { padding: "12px 16px" } }, name, " \uB85C\uB529 \uC911\u2026");
  }
  function _dpBase(baseUrl) {
    if (baseUrl) return baseUrl;
    return typeof window !== "undefined" && window.location && window.location.origin || "";
  }
  var RUN_KIND = (id) => id.startsWith("tmap2") ? "\uACA9\uC790" : id.startsWith("tmap") ? "\uC9C0\uB3C4" : id.startsWith("wf_") ? "\uC804\uC9C4" : id.includes("placebo") ? "\uB300\uC870" : id.includes("oos") ? "OOS" : id.includes("reeval") || id.includes("combo") ? "\uC7AC\uD3C9\uAC00" : id.includes("multiseed") ? "\uBC1C\uAD74" : "\uB8E8\uD504";
  function _DpSidebar({ runs, runId, setRunId, ops, verdict }) {
    const active = ops && ops.active || [];
    return /* @__PURE__ */ React.createElement("div", { style: {
      width: 280,
      flexShrink: 0,
      paddingRight: 12,
      overflowY: "auto",
      maxHeight: "calc(100vh - 24px)",
      borderRight: "1px solid rgba(255,255,255,0.08)"
    } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC2E4\uD589 \uC911"), active.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uC5C6\uC74C") : active.map((a) => /* @__PURE__ */ React.createElement("div", { key: a.run_id, className: "mono", style: { fontSize: 11, marginBottom: 4 } }, "\u{1F504} ", a.run_id, /* @__PURE__ */ React.createElement("div", { style: { opacity: 0.65 } }, a.gens, "\uC138\uB300 \xB7 ", a.health === "active" ? "\uC9C4\uD589 \uC911" : "\u26A0\uFE0F \uC815\uCCB4 \uC758\uC2EC"))), ops && ops.batch_queue && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10.5, opacity: 0.7, marginTop: 2 } }, "\uD050: ", ops.batch_queue.stages_done, "\uB2E8\uACC4 \uC644\uB8CC \xB7 ", ops.batch_queue.current_template || "\u2014"), verdict && (verdict.lines || []).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 10 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uAC80\uC99D \uACB0\uC0B0 \uC694\uC57D", (verdict.alerts || []).length ? ` \xB7 \u26A0\uFE0F${verdict.alerts.length}` : ""), verdict.lines.slice(0, 2).map((l, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "mono", style: { fontSize: 10.5, opacity: 0.85 } }, l))), /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { marginTop: 10 } }, "run \uBAA9\uB85D (\uCD5C\uC2E0\uC21C)"), runs.map((r) => /* @__PURE__ */ React.createElement(
      "div",
      {
        key: r.run_id,
        onClick: () => setRunId(r.run_id),
        className: "mono",
        style: {
          fontSize: 11,
          padding: "3px 5px",
          cursor: "pointer",
          borderRadius: 4,
          background: r.run_id === runId ? "rgba(90,140,200,0.25)" : "transparent"
        }
      },
      /* @__PURE__ */ React.createElement("span", { style: { opacity: 0.55 } }, "[", RUN_KIND(r.run_id), "]"),
      r.status === "running" ? " \u{1F504} " : " ",
      r.run_id,
      r.label ? /* @__PURE__ */ React.createElement("div", { style: { opacity: 0.5, fontSize: 10 } }, r.label) : null
    )));
  }
  function LabPage({ baseUrl }) {
    const base = _dpBase(baseUrl);
    const [runs, setRuns] = useState_dp([]);
    const [runId, setRunId] = useState_dp("");
    const [ops, setOps] = useState_dp(null);
    const [verdict, setVerdict] = useState_dp(null);
    useEffect_dp(() => {
      fetch(base + "/runs", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((d) => {
        const list = (d && d.runs || []).slice(0, 40);
        setRuns(list);
        if (list.length) setRunId((prev) => prev || list[0].run_id);
      }).catch(() => {
      });
      fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12e3) }).then((r) => r.ok ? r.json() : null).then((j) => setVerdict(j)).catch(() => {
      });
      const pull = () => fetch(base + "/ops_status", { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null).then((j) => setOps(j)).catch(() => {
      });
      pull();
      const timer = setInterval(pull, 1e4);
      return () => clearInterval(timer);
    }, [base]);
    const Panel = window.ResearchLabPanel;
    return /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 14, padding: "12px 0", minHeight: "60vh" } }, /* @__PURE__ */ React.createElement(_DpSidebar, { runs, runId, setRunId, ops, verdict }), /* @__PURE__ */ React.createElement("div", { style: { flex: 1, minWidth: 0 } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", marginBottom: 6 } }, /* @__PURE__ */ React.createElement("b", { style: { fontSize: 15 } }, "STOM Research Lab"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: 10, fontSize: 11, opacity: 0.7 } }, runId)), Panel ? /* @__PURE__ */ React.createElement(Panel, { baseUrl: base, wsStatus: "na", runId }) : /* @__PURE__ */ React.createElement(_DpLoading, { name: "\uC5F0\uAD6C\uC2E4 \uD328\uB110" }), window.ResearchWikiPanel && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement(ResearchWikiPanel, { baseUrl: base, wsStatus: "na", runId })), window.AIContextPanel && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement(AIContextPanel, { baseUrl: base, wsStatus: "na", runId, genNo: null }))));
  }
  function ProPage({ baseUrl }) {
    const base = _dpBase(baseUrl);
    const [runId, setRunId] = useState_dp("");
    useEffect_dp(() => {
      fetch(base + "/runs", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((d) => {
        const list = (d && d.runs || []).slice(0, 40);
        if (list.length) setRunId((prev) => prev || list[0].run_id);
      }).catch(() => {
      });
    }, [base]);
    const Panel = window.ResearchProPanel;
    return /* @__PURE__ */ React.createElement("div", { style: { minHeight: "60vh" } }, /* @__PURE__ */ React.createElement("div", { style: {
      display: "flex",
      alignItems: "center",
      gap: 12,
      padding: "10px 0",
      borderBottom: "1px solid rgba(255,255,255,0.08)",
      marginBottom: 8
    } }, /* @__PURE__ */ React.createElement("b", { style: { fontSize: 15 } }, "STOM \uB9AC\uC11C\uCE58 \uD504\uB85C")), Panel ? /* @__PURE__ */ React.createElement(Panel, { baseUrl: base, wsStatus: "na", runId }) : /* @__PURE__ */ React.createElement(_DpLoading, { name: "\uB9AC\uC11C\uCE58 \uD504\uB85C \uD328\uB110" }));
  }
  function VerdictPanel({ baseUrl }) {
    const base = _dpBase(baseUrl);
    const [v, setV] = useState_dp(null);
    const [history, setHistory] = useState_dp([]);
    const [choice, setChoice] = useState_dp("hold");
    const [note, setNote] = useState_dp("");
    const [saved, setSaved] = useState_dp(null);
    const [regime, setRegime] = useState_dp(null);
    const [revival, setRevival] = useState_dp(null);
    const [portfolio, setPortfolio] = useState_dp(null);
    const [vsub, setVsub] = useState_dp(() => {
      try {
        return window.localStorage.getItem("stom_verdict_subtab") || "summary";
      } catch (e) {
        return "summary";
      }
    });
    const selectVsub = (k) => {
      setVsub(k);
      try {
        window.localStorage.setItem("stom_verdict_subtab", k);
      } catch (e) {
      }
    };
    const loadHistory = () => fetch(base + "/decisions", { signal: AbortSignal.timeout(8e3) }).then((r) => r.ok ? r.json() : null).then((d) => setHistory(d && d.decisions || [])).catch(() => {
    });
    useEffect_dp(() => {
      fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12e3) }).then((r) => r.ok ? r.json() : null).then((j) => setV(j)).catch(() => {
      });
      fetch(base + "/regime_report", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((j) => setRegime(j)).catch(() => {
      });
      fetch(base + "/revival_registry", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((j) => setRevival(j)).catch(() => {
      });
      fetch(base + "/portfolio_verdict", { signal: AbortSignal.timeout(1e4) }).then((r) => r.ok ? r.json() : null).then((j) => setPortfolio(j)).catch(() => {
      });
      loadHistory();
    }, [base]);
    const submit = () => {
      fetch(base + "/record_decision", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verdict: choice, note })
      }).then((r) => r.json()).then((d) => {
        setSaved(d);
        setNote("");
        loadHistory();
      }).catch((e) => setSaved({ status: "error", error: String(e) }));
    };
    const _vBadge = (() => {
      const checks = v && v.promote_checklist || [];
      const alerts = (v && v.alerts || []).length;
      return {
        summary: checks.length ? alerts ? "\u26A0\uFE0F" + alerts : "\u2713" : "",
        regime: regime && regime.status !== "unavailable" ? "" : "\u2014",
        portfolio: portfolio && portfolio.adopted ? "\u2605" : portfolio && portfolio.status === "unavailable" ? "\u2014" : "",
        decide: history.length ? String(history.length) : ""
      };
    })();
    const VSUBS = [
      { key: "summary", label: "\uAC80\uC99D \uACB0\uC0B0", ico: "\u{1F4CB}" },
      { key: "regime", label: "\uB808\uC9D0\xB7\uBD80\uD65C", ico: "\u{1F310}" },
      { key: "portfolio", label: "V6 \uD3EC\uD2B8\uD3F4\uB9AC\uC624", ico: "\u2605" },
      { key: "decide", label: "\uC6B4\uC6A9 \uACB0\uC815", ico: "\u2696\uFE0F" }
    ];
    return /* @__PURE__ */ React.createElement("div", { style: { padding: "14px 0", maxWidth: 980, margin: "0 auto", minHeight: "60vh" } }, /* @__PURE__ */ React.createElement("div", { style: { display: "flex", alignItems: "center", marginBottom: 10 } }, /* @__PURE__ */ React.createElement("b", { style: { fontSize: 16 } }, "\uAC80\uC99D \uACB0\uC0B0\uACFC \uC6B4\uC6A9 \uACB0\uC815 (V6)"), /* @__PURE__ */ React.createElement("span", { className: "mono", style: { marginLeft: 10, fontSize: 11, color: "var(--ink-3)" } }, "\uC99D\uAC70 \u2192 \uACB0\uC815(append-only) \uC6CC\uD06C\uD50C\uB85C\uC6B0")), /* @__PURE__ */ React.createElement("div", { className: "research-tabs", role: "tablist", "aria-label": "\uACB0\uC815 \uC774\uB825 \uD558\uC704 \uD0ED", style: { marginBottom: 12 } }, VSUBS.map((t) => /* @__PURE__ */ React.createElement(
      "button",
      {
        key: t.key,
        type: "button",
        role: "tab",
        "aria-selected": vsub === t.key,
        className: "research-tab" + (vsub === t.key ? " active" : ""),
        onClick: () => selectVsub(t.key)
      },
      /* @__PURE__ */ React.createElement("span", { "aria-hidden": "true", style: { marginRight: 4 } }, t.ico),
      t.label,
      _vBadge[t.key] ? /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 5, opacity: 0.7 } }, _vBadge[t.key]) : null
    ))), vsub === "summary" && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement(window.VdtPromoteChecklist, { v }), v && v.oos_diff_ci && Object.keys(v.oos_diff_ci).length > 0 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8, marginBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "#9fb0c0", marginBottom: 2 } }, "OOS \uCC28\uC774 \uC2E0\uB8B0\uAD6C\uAC04 (advisory) \u2014 CI\uAC00 0\uC744 \uAC78\uCE58\uBA74 \uD45C\uBCF8 \uBD80\uC871 \uC2E0\uD638 \u2014 \uD310\uC815 \uBBF8\uC0AC\uC6A9"), /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "OOS \uC5F0\uB3C4"), /* @__PURE__ */ React.createElement("th", null, "total_diff"), /* @__PURE__ */ React.createElement("th", null, "CI 95%"), /* @__PURE__ */ React.createElement("th", null, "P(diff\u22640)"))), /* @__PURE__ */ React.createElement("tbody", null, Object.entries(v.oos_diff_ci).map(([year, ci]) => /* @__PURE__ */ React.createElement("tr", { key: year }, /* @__PURE__ */ React.createElement("td", null, year), /* @__PURE__ */ React.createElement("td", null, ci ? Math.round(ci.total_diff).toLocaleString() : "\u2014"), /* @__PURE__ */ React.createElement("td", null, ci ? `[${Math.round(ci.ci_low).toLocaleString()}, ${Math.round(ci.ci_high).toLocaleString()}]` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, ci ? ci.p_diff_le_0 : "\u2014")))))), /* @__PURE__ */ React.createElement(window.VdtAlerts, { v }), /* @__PURE__ */ React.createElement(window.VdtSummaryLines, { v })), vsub === "regime" && /* @__PURE__ */ React.createElement("div", null, regime && regime.status !== "unavailable" && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uB808\uC9D0 \uBD84\uD574 (advisory) \u2014 \uD310\uC815 \uBBF8\uC0AC\uC6A9"), ["THETA", "SEED"].map((grp) => {
      const d = (regime.breakdowns || {})[grp];
      if (!d) return null;
      const act = d.active || {}, con = d.contracted || {};
      return /* @__PURE__ */ React.createElement("div", { key: grp, className: "mono", style: { fontSize: 11, marginTop: 4 } }, /* @__PURE__ */ React.createElement("b", null, grp), " \xB7 \uD65C\uC131\uC7A5 ", act.profit != null ? "+" + Math.round(act.profit).toLocaleString() : "\u2014", act.days != null ? ` (${act.days}\uC77C)` : "", " \xB7 \uC704\uCD95\uC7A5 ", con.profit != null ? "+" + Math.round(con.profit).toLocaleString() : "\u2014", con.days != null ? ` (${con.days}\uC77C)` : "", d.concentration != null ? ` \xB7 \uC9D1\uC911\uB3C4 ${(d.concentration * 100).toFixed(1)}%` : "", d.warning ? /* @__PURE__ */ React.createElement("span", { style: { color: "#c95" } }, " \u26A0\uFE0F ", d.warning) : /* @__PURE__ */ React.createElement("span", { style: { color: "#7c4" } }, " \u2713 \uB808\uC9D0 \uADE0\uD615"));
    })), regime && regime.status === "unavailable" && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6 } }, "\uB808\uC9D0 \uBD84\uD574: \uB370\uC774\uD130 \uC5C6\uC74C"), revival && revival.status !== "unavailable" && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 14 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uD328\uC790\uBD80\uD65C \uB808\uC9C0\uC2A4\uD2B8\uB9AC", Array.isArray(revival.rejected) ? ` \u2014 \uB4F1\uC7AC ${revival.rejected.length}\uAC74` : ""), Array.isArray(revival.rejected) && revival.rejected.slice(0, 10).map((item, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "mono", style: { fontSize: 11, marginTop: 2 } }, /* @__PURE__ */ React.createElement("b", null, item.label || "\u2014"), item.rejected_at ? ` \xB7 \uAE30\uAC01 ${item.rejected_at}` : "", item.reject_basis ? ` \xB7 ${item.reject_basis}` : "")), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, opacity: 0.65, marginTop: 2 } }, "\uC2E0\uADDC \uB370\uC774\uD130 \uB3C4\uCC29 \uC2DC \uC804\uC218 \uC790\uB3D9 \uC7AC\uAC80\uC99D")), revival && revival.status === "unavailable" && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, marginTop: 14, opacity: 0.6 } }, "\uD328\uC790\uBD80\uD65C \uB808\uC9C0\uC2A4\uD2B8\uB9AC: \uB370\uC774\uD130 \uC5C6\uC74C")), vsub === "portfolio" && /* @__PURE__ */ React.createElement("div", null, portfolio && portfolio.adopted && /* @__PURE__ */ React.createElement("div", { style: { padding: 12, border: "1px solid rgba(90,180,100,0.35)", borderRadius: 6, background: "rgba(50,120,60,0.08)" } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty", style: { color: "#7c4" } }, "\u2605 V6 \uCC44\uD0DD \uCD94\uCC9C \uD3EC\uD2B8\uD3F4\uB9AC\uC624"), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12, marginTop: 6 } }, (portfolio.members || []).map((m) => /* @__PURE__ */ React.createElement("span", { key: m.name, style: { marginRight: 16 } }, /* @__PURE__ */ React.createElement("b", null, m.name), " ", Math.round(m.weight * 100), "%"))), portfolio.m4 && /* @__PURE__ */ React.createElement("div", { style: { marginTop: 8 } }, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.75, marginBottom: 2 } }, "M4 baseline (\uD3EC\uD2B8\uD3F4\uB9AC\uC624 vs \uC2DC\uB4DC \u2014 ", portfolio.m4.n_months, "\uAC1C\uC6D4)"), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 12 } }, "\uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uD569\uACC4: ", /* @__PURE__ */ React.createElement("b", null, portfolio.m4.champion_total != null ? Math.round(portfolio.m4.champion_total).toLocaleString() : "\u2014"), " \xB7 ", "\uC2DC\uB4DC \uD569\uACC4: ", /* @__PURE__ */ React.createElement("b", null, portfolio.m4.challenger_total != null ? Math.round(portfolio.m4.challenger_total).toLocaleString() : "\u2014"), portfolio.m4.champion_total != null && portfolio.m4.challenger_total != null && portfolio.m4.challenger_total !== 0 && /* @__PURE__ */ React.createElement("span", { style: { marginLeft: 8, color: portfolio.m4.champion_total >= portfolio.m4.challenger_total ? "#7c4" : "#c95" } }, "(", portfolio.m4.champion_total >= portfolio.m4.challenger_total ? "+" : "", ((portfolio.m4.champion_total - portfolio.m4.challenger_total) / Math.abs(portfolio.m4.challenger_total) * 100).toFixed(1), "% \uC6B0\uC704)")), (portfolio.m4.alerts || []).length > 0 && portfolio.m4.alerts.map((a, i) => /* @__PURE__ */ React.createElement("div", { key: i, className: "mono", style: { fontSize: 11, color: "#c95" } }, "\u26A0\uFE0F ", a)), (portfolio.m4.alerts || []).length === 0 && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6 } }, "\uACBD\uBCF4 \uC5C6\uC74C")), portfolio.decision_note && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, marginTop: 8, opacity: 0.85, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 6 } }, "\uACB0\uC815 \uB178\uD2B8: ", portfolio.decision_note), portfolio.findings_doc && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 10, marginTop: 4, opacity: 0.55 } }, "\uAC80\uC99D \uBB38\uC11C: ", portfolio.findings_doc)), portfolio && !portfolio.adopted && portfolio.status !== "unavailable" && /* @__PURE__ */ React.createElement("div", { style: { padding: 12, border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "V6 \uD3EC\uD2B8\uD3F4\uB9AC\uC624 \uCC44\uD0DD \uBBF8\uACB0\uC815"), /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6, marginTop: 4 } }, "complement \uACB0\uC815 \uAE30\uB85D \uC5C6\uC74C")), portfolio && portfolio.status === "unavailable" && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6 } }, "V6 \uD3EC\uD2B8\uD3F4\uB9AC\uC624: \uB370\uC774\uD130 \uC5C6\uC74C"), !portfolio && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, opacity: 0.6 } }, "V6 \uD3EC\uD2B8\uD3F4\uB9AC\uC624: \uB85C\uB529 \uC911\u2026")), vsub === "decide" && /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5, marginBottom: 8, padding: "6px 8px", border: "1px dashed var(--line-1)", borderRadius: 6 } }, "\u2139\uFE0F \uC6B4\uC601 \uCC44\uD0DD \uB3D9\uC120: \uC6B0\uC2B9 \uC804\uB7B5 ", /* @__PURE__ */ React.createElement("b", null, "\uB0B4\uBCF4\uB0B4\uAE30 \uC2B9\uC778"), "\uC740 \uC9C4\uD654 \uD0ED\uC758 ", /* @__PURE__ */ React.createElement("b", null, "\uC2B9\uC778\xB7\uB0B4\uBCF4\uB0B4\uAE30 \uB2E4\uC774\uC5BC\uB85C\uADF8"), "\uC5D0\uC11C WS(", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "final_approval"), ")\uB85C \uCC98\uB9AC\uB429\uB2C8\uB2E4. \uC774 \uD3FC\uC740 \uADF8 \uC6B4\uC6A9 ", /* @__PURE__ */ React.createElement("b", null, "\uACB0\uC815\uC744 append-only"), "\uB85C \uB0A8\uAE30\uB294 \uAE30\uB85D\uBD80\uC785\uB2C8\uB2E4(REST ", /* @__PURE__ */ React.createElement("span", { className: "mono" }, "/record_decision"), ")."), /* @__PURE__ */ React.createElement("div", { style: { padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uC6B4\uC6A9 \uACB0\uC815 \uAE30\uB85D (append-only \u2014 \uBC88\uBCF5\uB3C4 \uC0C8 \uB808\uCF54\uB4DC\uB85C \uC774\uB825 \uBCF4\uC874)"), /* @__PURE__ */ React.createElement("div", { style: { display: "flex", gap: 12, alignItems: "center", margin: "8px 0", flexWrap: "wrap" } }, ["promote", "complement", "hold", "reject"].map((k) => /* @__PURE__ */ React.createElement("label", { key: k, className: "mono", style: { fontSize: 12, cursor: "pointer" } }, /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "radio",
        name: "verdict",
        checked: choice === k,
        onChange: () => setChoice(k)
      }
    ), " ", k)), /* @__PURE__ */ React.createElement(
      "input",
      {
        type: "text",
        value: note,
        placeholder: "\uACB0\uC815 \uADFC\uAC70 \uBA54\uBAA8",
        onChange: (e) => setNote(e.target.value),
        className: "mono",
        style: { flex: 1, minWidth: 220, fontSize: 12 }
      }
    ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "research-tab", onClick: submit }, "\uAE30\uB85D")), saved && /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11, color: saved.status === "ok" ? "#5b9" : "#c95" } }, saved.status === "ok" ? "\uAE30\uB85D\uB428" : `\uC2E4\uD328: ${saved.error || saved.status}`)), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 12 } }, /* @__PURE__ */ React.createElement("div", { className: "research-empty" }, "\uACB0\uC815 \uC774\uB825"), history.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "mono", style: { fontSize: 11 } }, "\uAE30\uB85D \uC5C6\uC74C") : /* @__PURE__ */ React.createElement("table", { className: "mono", style: { fontSize: 11, width: "100%" } }, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "\uC2DC\uAC01"), /* @__PURE__ */ React.createElement("th", null, "\uACB0\uC815"), /* @__PURE__ */ React.createElement("th", null, "\uB300\uC0C1 \uD6C4\uBCF4"), /* @__PURE__ */ React.createElement("th", null, "\uBA54\uBAA8"))), /* @__PURE__ */ React.createElement("tbody", null, history.slice().reverse().map((d, i) => /* @__PURE__ */ React.createElement("tr", { key: i }, /* @__PURE__ */ React.createElement("td", null, new Date((d.ts || 0) * 1e3).toLocaleString("ko-KR")), /* @__PURE__ */ React.createElement("td", null, d.verdict), /* @__PURE__ */ React.createElement("td", null, d.candidate ? `${d.candidate.buy_name} (${Math.round(d.candidate.profit || 0).toLocaleString()})` : "\u2014"), /* @__PURE__ */ React.createElement("td", null, d.note || "\u2014"))))))));
  }
  Object.assign(window, { LabPage, ProPage, VerdictPanel });

  // src/track-z-entry.pilot.js
  Object.assign(window, {
    // FROZEN — index.html / lab.html / pro.html / verdict.html mount these by name.
    App,
    ErrorBoundary,
    LabPage,
    ProPage,
    VerdictPanel,
    // TRACK_Z_DEPS §4 — shared components consumed via window.X across standalone pages.
    DemoBadge,
    LivePending,
    LiveBacktestChart,
    EnginePanel,
    PhaseDetailPanel,
    PhaseTimeline,
    ProcessFlowPanel,
    ResearchLabPanel,
    VdtAlerts,
    VdtPromoteChecklist,
    VdtSummaryLines,
    BtResultArea,
    BtVarChips,
    SimCandleChart,
    SimCandleChartLWC,
    SimCandleChartSVG
  });
})();
