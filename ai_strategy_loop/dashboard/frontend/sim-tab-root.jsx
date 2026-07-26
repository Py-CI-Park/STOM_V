/* Chart simulation tab — 탭 루트 오케스트레이터 (split from simulation.jsx for the thin-barrel pattern).
   컨트롤 + WS 리플레이 상태머신 + 차트 그리드 + 체결 로그. /sim/* REST + WS /sim/ws 소비
   (simulation_api.py·replay_engine.py). WS push 기반(폴링 없음) — meta→bars(배치)→done 프로토콜.

   캔들 차트·체결 로그는 simulation-charts.jsx 의 순수 컴포넌트(SimOverlayChart/SimSignalLog) 사용.
   하위 UI(컨트롤·프리셋·미니맵·재생·보기바·팝오버)는 sim-tab-controls.jsx,
   좌측 패널/엔진 디스패처는 sim-tab-panels.jsx, 공용 상수/훅/헬퍼는 sim-tab-utils.jsx 에서 import.
   stom-ui 전역(window._simTimeLabel 등)은 window 으로 호출(import 금지). 외부 차트 라이브러리 금지.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { SimOverlayChart, SimSignalLog } from "./simulation-charts.jsx";
import { useState_sim, useEffect_sim, useCallback_sim, useRef_sim, useMemo_sim, _simFetchJson, _simRefreshReplaySession, _SIM_SPEEDS, _simWsBar, _SIM_MAX_CODES, _SIM_DEMO_SPEED, _SIM_MAX_SPLIT_COLS, _loadIndicators, _saveIndicators, _loadSplitCols, _saveSplitCols, _loadSplitRows, _saveSplitRows, _loadEngineMode, _saveEngineMode, _wsUrl, _simDemoSeen, _simMarkDemoSeen, _flattenSignals, _simRenderBudget, _simRenderBars } from "./sim-tab-utils.jsx";
import { SimControlBar, SimPresetBar, SimMarketMinimap, SimPlaybackBar, SimViewBar } from "./sim-tab-controls.jsx";
import { SimChartByEngine, SimIndicatorTable, SimLearningPanel, SimVariableWatch } from "./sim-tab-panels.jsx";
import { _bindReplayKeydown, _isReplayEditableTarget, _exactReplayTimestamp } from "./replay-lifecycle.jsx";

// ===========================================================================
// 탭 루트 — 컨트롤 + WS 리플레이 상태머신 + 차트 그리드 + 체결 로그.
// ===========================================================================
function SimulationTab({ baseUrl, wsStatus, active = true }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

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

  // 리플레이 런타임 상태.
  const [status, setStatus] = useState_sim("idle");   // idle|playing|paused|done|error
  const [speed, setSpeed] = useState_sim(20);
  const [meta, setMeta] = useState_sim(null);          // {codes, bars_total, session_range}
  const [cursor, setCursor] = useState_sim(0);
  const [curT, setCurT] = useState_sim(null);
  const [wsErr, setWsErr] = useState_sim("");
  const [signals, setSignals] = useState_sim({});      // code → [signal...]
  const [signalErr, setSignalErr] = useState_sim("");

  // 즉시 체험 — 자동 데모 추천 여부·프리셋 조회 busy·수동 시작 대기 플래그.
  const [demoActive, setDemoActive] = useState_sim(false);   // 예시 추천 배지 노출.
  const [presetBusy, setPresetBusy] = useState_sim(false);   // /sim/demo 조회 중.
  const pendingAutoplayRef = useRef_sim(false);              // 사용자 프리셋 후 재생 트리거.
  const demoTriedRef = useRef_sim(false);                    // 자동 데모 1회만 시도(재진입 루프 방지).

  // 보조지표 토글(MA·VWAP·볼린저) — localStorage 보존. 차트 라인 오버레이 제어.
  const [indicators, setIndicators] = useState_sim(_loadIndicators);
  // 멀티차트 보기 모드(split/overlay) + 분할 컬럼 수(1~5).
  const [chartMode, setChartMode] = useState_sim("split");
  const [splitCols, setSplitCols] = useState_sim(_loadSplitCols);
  // 분할 행 캡(0=자동·무제한). 종목수/열 기반 자동 행을 사용자가 줄여 스크롤 그리드로 만든다.
  const [splitRows, setSplitRows] = useState_sim(_loadSplitRows);
  // 차트 엔진 모드(live/lwc/svg) — 신규 프로필은 LWC, 명시적 localStorage 선택은 보존.
  const [engineMode, setEngineMode] = useState_sim(_loadEngineMode);
  const [viewportTick, setViewportTick] = useState_sim(0);

  // 학습 모드 — 신호 자동 일시정지 토글 + 하이라이트 신호 키.
  const [autoPause, setAutoPause] = useState_sim(false);
  const [highlightSig, setHighlightSig] = useState_sim(null);  // "code@buy_hms" 형태.
  // 이미 자동정지한 신호(중복 정지 방지) — ref 로 들고 리렌더 유발 안 함.
  const autoPausedRef = useRef_sim(new Set());

  const wsRef = useRef_sim(null);
  // A replay is loading until metadata arrives; a bounded timer prevents silent 0/0 playback.
  const zeroFrameTimerRef = useRef_sim(null);
  const receivedBarCountRef = useRef_sim(0);
  const replayErrorReportedRef = useRef_sim(false);
  const clearZeroFrameTimer = () => {
    if (zeroFrameTimerRef.current) {
      clearTimeout(zeroFrameTimerRef.current);
      zeroFrameTimerRef.current = null;
    }
  };
  // 코드별 누적 bar 시계열(append). ref 로 들고 상태는 버전 카운터로 리렌더.
  const barsRef = useRef_sim({});
  const [barsVersion, setBarsVersion] = useState_sim(0);

  // 헬스 체크.
  useEffect_sim(() => {
    if (isDemo || !baseUrl) { setHealth(null); return; }
    _simFetchJson(baseUrl + "/sim/health", 3000).then(setHealth).catch(() => setHealth(null));
  }, [baseUrl, isDemo]);

  // 날짜 인벤토리(src 변경 시 재로드).
  useEffect_sim(() => {
    if (isDemo || !baseUrl) { setDays([]); return; }
    _simFetchJson(baseUrl + "/sim/days?src=" + src, 5000)
      .then(j => {
        const list = Array.isArray(j && j.days) ? j.days : [];
        setDays(list);
        // 프리필 날짜가 이 리플레이 DB 에 없으면 그 사실을 그대로 말한다.
        const wanted = pendingPrefillDateRef.current;
        if (wanted) {
          pendingPrefillDateRef.current = "";
          const has = list.some(d => String(d) === wanted || String(d).replace(/-/g, "") === wanted);
          if (!has) {
            prefillRef.current = null;
            setPrefillNote(`리플레이 ${src === "tick" ? "틱" : "분"} DB 에 ${wanted} 일자가 없습니다. 아래에서 보유한 거래일을 고르세요.`);
          }
        }
      })
      .catch(() => setDays([]));
    // src 변경 시 선택/리플레이 리셋(프리셋/데모 자동재생 대기 중이면 보존).
    if (!pendingAutoplayRef.current) {
      _stopReplay();
      setDate(""); setStocks([]); setSelected([]);
    }
  }, [baseUrl, isDemo, src]);

  // v5.11.3 — 결과 분석에서 "이 거래를 리플레이로" 로 넘어온 프리필을 1회 소비한다.
  //   {date, code, reason} 을 localStorage 로 받아 날짜를 먼저 세팅하고, 종목 목록이
  //   로드되면 해당 종목을 골라 준다. 없는 종목이면 이유를 알려주고 날짜만 유지한다.
  const prefillRef = useRef_sim(null);
  const pendingPrefillDateRef = useRef_sim("");
  const [prefillNote, setPrefillNote] = useState_sim("");
  const [sessionReady, setSessionReady] = useState_sim(false);
  useEffect_sim(() => {
    try {
      const raw = window.localStorage && window.localStorage.getItem("stom_replay_prefill");
      if (!raw) return;
      window.localStorage.removeItem("stom_replay_prefill");
      const detail = JSON.parse(raw);
      if (!detail || !detail.date) return;
      prefillRef.current = detail;
      setDate(String(detail.date));
      setPrefillNote(detail.reason ? `결과 분석에서 이동 — ${detail.reason}` : "결과 분석에서 이동");
      pendingPrefillDateRef.current = String(detail.date);
    } catch (e) {}
  }, []);

  // 조건식 목록(buy/sell).
  useEffect_sim(() => {
    if (isDemo || !baseUrl) { setStrategies({ buy: [], sell: [] }); return; }
    let cancelled = false;
    Promise.all([
      _simFetchJson(baseUrl + "/bt/strategies?kind=buy", 4000).catch(() => ({ items: [] })),
      _simFetchJson(baseUrl + "/bt/strategies?kind=sell", 4000).catch(() => ({ items: [] })),
    ]).then(([b, s]) => {
      if (cancelled) return;
      setStrategies({
        buy: (b.items || []).map(it => it.name),
        sell: (s.items || []).map(it => it.name),
      });
    });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo]);

  // 종목 목록(날짜 선택 시).
  useEffect_sim(() => {
    if (isDemo || !baseUrl || !date) { setStocks([]); return; }
    setLoadingStocks(true);
    _simFetchJson(baseUrl + "/sim/stocks?date=" + encodeURIComponent(date) + "&src=" + src, 8000)
      .then(j => {
        const items = Array.isArray(j && j.stocks) ? j.stocks : [];
        setStocks(items);
        const wanted = prefillRef.current;
        if (wanted && wanted.code && String(wanted.date) === String(date)) {
          prefillRef.current = null;
          const hit = items.find(it => it && (it.code === wanted.code || it.name === wanted.code));
          if (hit) {
            setSelected([hit.code]);
            setPrefillNote(`결과 분석에서 이동 — ${wanted.reason || ""} · ${hit.name || hit.code} 선택됨`.trim());
          } else {
            setPrefillNote(`이 날짜의 종목 목록에 '${wanted.code}' 가 없습니다. 날짜만 적용했습니다.`);
          }
        }
      })
      .catch(() => setStocks([]))
      .finally(() => setLoadingStocks(false));
    // 프리셋/데모가 미리 고른 종목·재생은 보존(autoplay 대기 중이면 리셋하지 않음).
    if (!pendingAutoplayRef.current) { setSelected([]); _stopReplay(); }
  }, [baseUrl, isDemo, date]);

  const toggleStock = useCallback_sim((code) => {
    setDemoActive(false);   // 사용자가 직접 종목을 고르면 데모 컨텍스트 종료.
    setSelected(prev => {
      if (prev.includes(code)) return prev.filter(c => c !== code);
      if (prev.length >= _SIM_MAX_CODES) return prev;
      return [...prev, code];
    });
  }, []);

  // 보조지표 토글(ma/vwap/boll) — 즉시 차트 반영 + localStorage 저장.
  const toggleIndicator = useCallback_sim((key) => {
    setIndicators(prev => {
      const next = { ...prev, [key]: !prev[key] };
      _saveIndicators(next);
      return next;
    });
  }, []);
  const setSplitColsPersist = useCallback_sim((v) => {
    setSplitCols(v); _saveSplitCols(v);
  }, []);
  const setSplitRowsPersist = useCallback_sim((v) => {
    setSplitRows(v); _saveSplitRows(v);
  }, []);
  const setEngineModePersist = useCallback_sim((v) => {
    setEngineMode(v); _saveEngineMode(v);
  }, []);
  useEffect_sim(() => {
    if (typeof window === "undefined") return undefined;
    const onResize = () => setViewportTick(v => v + 1);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);


  // 신호 로드 — 선택 코드 전체를 하나의 bounded batch request로 받는다.
  useEffect_sim(() => {
    if (isDemo || !baseUrl || !date || !buy || !sell || selected.length === 0) {
      setSignals({}); setSignalErr(""); return;
    }
    let cancelled = false;
    const selectedCodes = Array.from(new Set(selected)).slice(0, _SIM_MAX_CODES);
    _simFetchJson(
      baseUrl + "/sim/signals/batch?date=" + encodeURIComponent(date) + "&src=" + src +
      "&codes=" + encodeURIComponent(selectedCodes.join(",")) +
      "&buy=" + encodeURIComponent(buy) + "&sell=" + encodeURIComponent(sell),
      200000
    ).then(j => {
      if (cancelled) return;
      const next = {};
      const results = (j && j.results && typeof j.results === "object") ? j.results : {};
      const failedCodes = [];
      selectedCodes.forEach(code => {
        const result = results[code] || {};
        next[code] = Array.isArray(result.trades) ? result.trades : [];
        if (result.status !== "ok") failedCodes.push(code + ": " + (result.note || "신호 로드 실패"));
      });
      setSignals(next);
      setSignalErr(failedCodes.length ? "신호 로드 실패: " + failedCodes.join(", ") : "");
    }).catch(e => {
      if (!cancelled) {
        setSignals(Object.fromEntries(selectedCodes.map(code => [code, []])));
        setSignalErr("신호 로드 실패: " + String(e && e.message ? e.message : e));
      }
    });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, date, src, buy, sell, selected.join(",")]);

  // --- WS 리플레이 제어 ---
  const _stopReplay = useCallback_sim(() => {
    clearZeroFrameTimer();
    receivedBarCountRef.current = 0;
    if (wsRef.current) {
      try { wsRef.current.send(JSON.stringify({ action: "stop" })); } catch (e) {}
      try { wsRef.current.close(); } catch (e) {}
      wsRef.current = null;
    }
    setStatus("idle"); setMeta(null); setCursor(0); setCurT(null);
    barsRef.current = {}; setBarsVersion(v => v + 1);
  }, []);

  // 컴포넌트 언마운트 시 WS 정리.
  useEffect_sim(() => () => { _stopReplay(); }, [_stopReplay]);

  const startReplay = useCallback_sim(async () => {
    const selectedCodes = Array.from(new Set(selected)).slice(0, _SIM_MAX_CODES);
    const knownCodes = new Set(stocks.map(s => String(s.code)));
    if (isDemo || !baseUrl || !date || loadingStocks || selectedCodes.length === 0 ||
        !selectedCodes.every(code => knownCodes.has(String(code)))) {
      setWsErr("날짜의 종목 목록을 불러온 뒤 유효한 종목을 선택하세요.");
      setStatus("error");
      return;
    }
    _stopReplay();
    const url = _wsUrl(baseUrl, "/sim/ws");
    if (!url) { setWsErr("WS URL 생성 실패"); setStatus("error"); return; }
    setWsErr(""); receivedBarCountRef.current = 0; replayErrorReportedRef.current = false;
    barsRef.current = {}; setBarsVersion(v => v + 1);
    setStatus("loading");

    try {
      await _simRefreshReplaySession(baseUrl);
      setSessionReady(true);
    } catch (e) {
      setSessionReady(false);
      replayErrorReportedRef.current = true;
      setWsErr("서버 세션을 새로 준비하지 못했습니다. 대시보드 연결을 확인한 뒤 재시도하세요.");
      setStatus("error");
      return;
    }

    let ws;
    try { ws = new WebSocket(url); } catch (e) { setWsErr(String(e)); setStatus("error"); return; }
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: "start", date: parseInt(date, 10), src,
        codes: selectedCodes, speed, agg_sec: parseInt(aggSec, 10) || 10,
      }));
      setStatus("loading");
      clearZeroFrameTimer();
      zeroFrameTimerRef.current = setTimeout(() => {
        if (receivedBarCountRef.current === 0 && wsRef.current === ws) {
          try { ws.close(); } catch (e) {}
          wsRef.current = null;
          replayErrorReportedRef.current = true;
          setWsErr("리플레이 데이터를 받지 못했습니다. 날짜·종목을 다시 선택한 뒤 재시도하세요.");
          setStatus("error");
        }
      }, 8000);
    };
    ws.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (e) {
        clearZeroFrameTimer();
        replayErrorReportedRef.current = true;
        setWsErr("리플레이 프레임 해석 실패: " + String(e && e.message ? e.message : e));
        setStatus("error");
        return;
      }
      if (!m || !m.type) {
        clearZeroFrameTimer();
        replayErrorReportedRef.current = true;
        setWsErr("리플레이 프로토콜 오류: type 누락");
        setStatus("error");
        return;
      }
      if (m.type === "meta") {
        setMeta({ codes: m.codes || [], bars_total: m.bars_total || 0, session_range: m.session_range || [0, 0], replay_metadata: m.replay_metadata || {} });
        setCursor(0);
        setStatus("playing");
      } else if (m.type === "bars") {
        //   기존 .push() 는 같은 배열을 mutate 해 per-code 배열 참조가 안 바뀌어
        //   SimCandleChartLWC 의 useEffect([bars]) 가 최초 1회만 돌아 봉·거래량이 1개로 동결됐다.
        //   → 매 프레임 새 배열을 만들어(store[code] = [...prev, bar]) 참조를 갱신해야
        //     LWC effect 가 매번 재실행되며 봉·거래량 히스토그램이 정상 리플레이된다.
        const store = barsRef.current;
        const items = Array.isArray(m.items) ? m.items : [];
        items.forEach(it => {
          store[it.code] = [...(store[it.code] || []), _simWsBar(it, m.t)];   // 새 배열 참조(불변 append).
        });
        receivedBarCountRef.current += items.length;
        if (receivedBarCountRef.current > 0) clearZeroFrameTimer();
        setCursor((m.index || 0) + 1);
        setCurT(m.t);
        setBarsVersion(v => v + 1);
      } else if (m.type === "history") {
        // Phase6.1 — seek 스냅샷: 코드별 시계열을 통째로 교체. 전진 seek 의 공백(시킹
        //   이후 frame 만 쌓여 봉 6개만 남던 신고 증상)과 후진 seek 의 중복 append 를
        //   모두 해소한다. bar 필드 매핑은 증분 "bars" 와 동일(_simWsBar 공유).
        const store = {};
        Object.keys(m.items_by_code || {}).forEach(code => {
          store[code] = (m.items_by_code[code] || []).map(b => _simWsBar(b, b.t));
        });
        barsRef.current = store;
        if (m.index != null) setCursor(m.index);
        if (m.t != null) setCurT(m.t);
        setBarsVersion(v => v + 1);
      } else if (m.type === "done") {
        clearZeroFrameTimer();
        if (receivedBarCountRef.current === 0) {
          replayErrorReportedRef.current = true;
          setWsErr("리플레이 데이터가 비어 있습니다. 날짜·종목을 다시 선택한 뒤 재시도하세요.");
          setStatus("error");
        } else {
          setStatus(s => (s === "playing" || s === "paused") ? "done" : s);
        }
      } else if (m.type === "error") {
        clearZeroFrameTimer();
        replayErrorReportedRef.current = true;
        setWsErr(m.message || "리플레이 오류"); setStatus("error");
      } else {
        clearZeroFrameTimer();
        replayErrorReportedRef.current = true;
        setWsErr("리플레이 프로토콜 오류: 알 수 없는 frame type " + String(m.type));
        setStatus("error");
      }
    };
    ws.onerror = () => { clearZeroFrameTimer(); replayErrorReportedRef.current = true; setWsErr("WebSocket 연결 오류"); setStatus("error"); };
    ws.onclose = (event) => {
      const isActive = wsRef.current === ws;
      const noFrames = receivedBarCountRef.current === 0;
      if (isActive) wsRef.current = null;
      clearZeroFrameTimer();
      if (isActive && noFrames && !replayErrorReportedRef.current) {
        const closeInfo = event && event.code ? ` · 종료 코드 ${event.code}${event.reason ? " · " + event.reason : ""}` : "";
        setWsErr("리플레이 연결이 데이터를 보내기 전에 종료됐습니다" + closeInfo + ". 날짜·종목 선택과 서버 세션을 확인한 뒤 재시도하세요.");
        setStatus("error");
      }
    };
  }, [baseUrl, isDemo, date, src, selected, stocks, loadingStocks, speed, aggSec, _stopReplay]);

  const _wsSend = (payload) => {
    if (wsRef.current && wsRef.current.readyState === 1) {
      try { wsRef.current.send(JSON.stringify(payload)); } catch (e) {}
    }
  };

  const pauseReplay = () => { _wsSend({ action: "pause" }); setStatus("paused"); };
  const resumeReplay = () => { _wsSend({ action: "resume" }); setStatus("playing"); };
  const changeSpeed = (sp) => { setSpeed(sp); _wsSend({ action: "speed", value: sp }); };

  // 숨겨진 탭에서 리플레이가 계속 소비되지 않도록 탭 이탈 즉시 안전하게 일시정지한다.
  useEffect_sim(() => {
    if (active || status !== "playing") return;
    _wsSend({ action: "pause" });
    setStatus("paused");
  }, [active, status]);


  const seekByIndex = (idx) => {
    setCursor(idx);
    _wsSend({ action: "seek_index", index: idx });
  };

  const stopReplay = () => { _stopReplay(); };

  // --- 즉시 체험: /sim/demo 추천 적용 + 수동 게이트 ---
  //   서버가 날짜·등락 1위 종목을 직접 주므로 stocks 목록 로딩을 기다리지 않고 바로 선택한다.
  //   페이지 진입만으로 /sim/ws 를 열지 않는다. 자동재생은 명시적 프리셋/재생 조작에서만 허용한다.
  const applyDemo = useCallback_sim((mode, asDemo, autoStart = false) => {
    if (isDemo || !baseUrl) return;
    setPresetBusy(true);
    _stopReplay();
    _simFetchJson(baseUrl + "/sim/demo?src=min&mode=" + encodeURIComponent(mode || "latest"), 8000)
      .then(j => {
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
        pendingAutoplayRef.current = !!autoStart;
        setPresetBusy(false);
      })
      .catch(() => { setPresetBusy(false); if (asDemo) setDemoActive(false); });
  }, [baseUrl, isDemo, _stopReplay]);

  // Presets wait for the selected code to appear in the loaded date inventory before opening WS.
  useEffect_sim(() => {
    if (!pendingAutoplayRef.current) return;
    const knownCodes = new Set(stocks.map(s => String(s.code)));
    if (!date || loadingStocks || selected.length === 0 ||
        !selected.every(code => knownCodes.has(String(code)))) return;
    pendingAutoplayRef.current = false;
    startReplay();
  }, [date, selected, stocks, loadingStocks, startReplay]);

  // 최초 진입 데모 추천 — 선택 없음 + 미시청 + 백엔드 연결 시 1회. localStorage 로 재방문 시 생략.
  useEffect_sim(() => {
    if (demoTriedRef.current) return;
    if (isDemo || !baseUrl) return;
    if (selected.length > 0 || date) return;        // 이미 사용자가 고른 상태면 데모 안 함.
    if (_simDemoSeen()) return;                     // 이전에 본 적 있으면 강제 안 함.
    demoTriedRef.current = true;
    _simMarkDemoSeen();
    applyDemo("latest", true, false);
  }, [baseUrl, isDemo, applyDemo]);

  // 사용자가 직접 선택/조작하면 데모 배지 해제(자동재생 컨텍스트 종료).
  const exitDemo = useCallback_sim(() => {
    setDemoActive(false);
    pendingAutoplayRef.current = false;
    _stopReplay();
    setDate(""); setSelected([]);
  }, [_stopReplay]);

  // 프리셋 클릭(수동) — 데모 배지 없이 추천 적용 후 사용자 조작 컨텍스트에서 재생.
  const onPreset = useCallback_sim((mode) => {
    setDemoActive(false);
    applyDemo(mode, false, true);
  }, [applyDemo]);

  // 렌더·로직 공용 파생값(차트 그리드·신호 평탄화·재생 가능 여부).
  const codes = (meta && meta.codes && meta.codes.length) ? meta.codes : selected;
  const selectedCodesLoaded = selected.length > 0 && !loadingStocks &&
    selected.every(code => stocks.some(stock => String(stock.code) === String(code)));
  const canPlay = !isDemo && !!date && selectedCodesLoaded &&
    (status === "idle" || status === "done" || status === "error");
  // 키보드 핸들러가 stale 클로저로 보지 않도록 canPlay 를 ref 로 미러링.
  const canPlayRef = useRef_sim(canPlay);
  useEffect_sim(() => { canPlayRef.current = canPlay; }, [canPlay]);

  // 신호 시각(HHMMSS)으로 직접 시킹 — 북마크 클릭용. 서버 seek 은 t(HHMMSS)를 직접 받는다.
  const seekToTime = useCallback_sim((hms) => {
    const timestamp = _exactReplayTimestamp(hms);
    if (timestamp == null) return;
    _wsSend({ action: "seek", t: timestamp });
    setCurT(timestamp);
  }, []);

  // 학습 모드 — 평탄화된 전체 신호(시각순). 자동정지·북마크 공용.
  const flatSignals = useMemo_sim(() => _flattenSignals(signals, codes), [signals, codes.join(",")]);

  // 신호 자동 일시정지 — 재생 중 curT 가 거래(매수) 시각에 도달하면 1회 pause + 하이라이트.
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

  // 리플레이 새로 시작/정지 시 자동정지 기록 리셋.
  useEffect_sim(() => {
    if (status === "idle" || status === "playing" && cursor === 0) {
      autoPausedRef.current = new Set();
    }
  }, [status]);

  // 키보드 단축키 — Space=재생/정지, ←/→=배속 다운/업, Esc=정지. 입력 필드 포커스 시 무시.
  useEffect_sim(() => {
    const onKey = (e) => {
      if (_isReplayEditableTarget(e.target)) return;
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
    return _bindReplayKeydown(active, window, onKey);
  }, [active, status, speed]);

  const connected = !!(health && health.status === "ok");
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: "checking", color: "var(--amber)" };

  // 렌더용 코드별 bar 시계열(barsVersion 의존).
  const barsByCode = useMemo_sim(() => ({ ...barsRef.current }), [barsVersion]);
  const renderBudget = useMemo_sim(() => _simRenderBudget(codes.length), [codes.length, viewportTick]);
  const renderBarsByCode = useMemo_sim(() => {
    const out = {};
    codes.forEach(code => { out[code] = _simRenderBars(barsByCode[code] || [], renderBudget); });
    return out;
  }, [barsByCode, codes.join(","), renderBudget]);
  // 7.6 분할 그리드 — 사용자가 열(1~5)을 직접 고른다. 단일 종목은 항상 1열.
  //   effCols = clamp(userCols, 1, min(5, codes.length)). 종목수보다 많은 열은 빈칸 방지로 클램프.
  const colCap = Math.min(_SIM_MAX_SPLIT_COLS, Math.max(1, codes.length));
  const effCols = codes.length <= 1 ? 1 : Math.min(Math.max(1, splitCols), colCap);
  const gridCols = "repeat(" + effCols + ", minmax(0, 1fr))";
  // 자동 행수 = ceil(종목수/열). 사용자가 splitRows(>0)로 더 적게 캡하면 그 행만 보이고 나머지는 스크롤.
  const autoRows = Math.max(1, Math.ceil(codes.length / effCols));
  const effRows = splitRows > 0 ? Math.min(splitRows, autoRows) : autoRows;
  const rowsCapped = effRows < autoRows;
  // S2 컴팩트 — 5개 이상이면 차트 높이·보조패널을 축소(과밀 방지).
  const dense = codes.length >= 5;
  // 행 캡 시: 보이는 행만큼 높이를 제한하고 세로 스크롤(gridAutoRows 로 행 높이 균일).
  const gridExtra = rowsCapped
    ? { gridAutoRows: "minmax(0, " + (100 / effRows).toFixed(4) + "%)",
        maxHeight: "calc(100vh - 220px)", overflowY: "auto" }
    : {};
  const nameByCode = useMemo_sim(() => {
    const m = {};
    stocks.forEach(s => { m[s.code] = s.name; });
    return m;
  }, [stocks]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 탭 헤더 배지 */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
                    background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 8 }}>
        <span className="panel-hd-title" style={{ border: 0 }}>
          <span className="dot" style={{ background: "var(--violet)" }}></span>차트 시뮬레이션
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginLeft: 12 }}>
          일일 {src === "tick" ? "tick" : "min"} DB 리플레이 · 엔진 정합 신호 오버레이
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: badge.color, letterSpacing: ".06em", marginLeft: "auto" }}>
          ● {badge.label}
        </span>
      </div>

      <div className="grid-main" style={{ gridTemplateColumns: "minmax(0, 380px) minmax(0, 1fr)" }}>
        {/* 좌: 컨트롤 + 지표 라이브 테이블 + 학습 모드 + 체결 로그 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          {/* v5.11.3 — 세션은 실패해야만 알 수 있었다. 항상 보이게 한다. */}
          <div className="sim-session-strip mono" role="status">
            <span className={"sim-session-dot " + (sessionReady ? "ok" : "wait")} aria-hidden="true"></span>
            <span>{sessionReady
              ? "서버 세션 준비됨 — 재생 시 즉시 연결됩니다."
              : "서버 세션 미확인 — 재생을 누르면 먼저 세션을 새로 준비합니다."}</span>
          </div>
          {prefillNote && (
            <div className="sim-prefill-note mono" role="status">
              {prefillNote}
              <button className="btn ghost sm" onClick={() => setPrefillNote("")}>닫기</button>
            </div>
          )}
          <SimPresetBar isDemo={isDemo} busy={presetBusy} onPreset={onPreset} />
          <SimControlBar
            baseUrl={baseUrl} isDemo={isDemo} src={src} onSrc={setSrc}
            date={date} onDate={setDate} days={days}
            stocks={stocks} selected={selected} onToggleStock={toggleStock}
            stockQuery={stockQuery} onStockQuery={setStockQuery} loadingStocks={loadingStocks}
            buy={buy} onBuy={setBuy} sell={sell} onSell={setSell} strategies={strategies}
            aggSec={aggSec} onAggSec={setAggSec} />
          <SimMarketMinimap
            stocks={stocks} selected={selected} onToggleStock={toggleStock}
            query={stockQuery} isDemo={isDemo} date={date} loading={loadingStocks} />
          {codes.length > 0 && (status !== "idle" || cursor > 0) && (
            <SimIndicatorTable codes={codes} barsByCode={barsByCode} nameByCode={nameByCode} />
          )}
          {codes.length > 0 && (status !== "idle" || cursor > 0) && (
            <SimVariableWatch codes={codes} barsByCode={barsByCode} nameByCode={nameByCode} />
          )}
          {(buy && sell) && (
            <SimLearningPanel autoPause={autoPause} onToggleAutoPause={() => setAutoPause(v => !v)}
              signals={flatSignals} curT={curT} highlightSig={highlightSig} onSeek={seekToTime} />
          )}
          {(buy && sell) && (
            <SimSignalLog signals={flatSignals} curT={curT} />
          )}
        </div>

        {/* 우: 재생 컨트롤 + 차트 그리드 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          {demoActive && (
            <div style={{
              display: "flex", alignItems: "center", gap: 10, padding: "8px 12px",
              background: "rgba(124,108,240,0.10)", border: "1px solid var(--violet)",
              borderRadius: 8,
            }}>
              <span className="mono" style={{
                fontSize: 10.5, color: "var(--violet)", letterSpacing: ".04em",
                fontWeight: 600, display: "flex", alignItems: "center", gap: 6,
              }}>
                <span className="dot" style={{ background: "var(--violet)" }}></span>
                예시 추천 준비
              </span>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                예시 자동 재생 준비 · 재생은 사용자 게이트 후 시작
              </span>
              <button className="btn ghost sm" onClick={exitDemo}
                      style={{ marginLeft: "auto", fontSize: 10.5, padding: "3px 10px" }}>
                내가 선택하기
              </button>
            </div>
          )}
          <SimPlaybackBar
            status={status} onPlay={startReplay} onPause={pauseReplay}
            onResume={resumeReplay} onStop={stopReplay}
            speed={speed} onSpeed={changeSpeed} cursor={cursor}
            total={meta ? meta.bars_total : 0} curT={curT}
            sessionRange={meta ? meta.session_range : [0, 0]} onSeek={seekByIndex} canPlay={canPlay} />
          <div className="mono" role="status" style={{ fontSize: 10, color: "var(--ink-3)", padding: "0 4px" }}>
            상태: {status} · 엔진: {engineMode === "live" ? "Canvas (고급/실험적)" : engineMode.toUpperCase()} · 소스: {src}
            {" · "}수신 봉: {receivedBarCountRef.current}/{meta ? meta.bars_total : "?"}
            {(() => {
              const visible = Object.values(barsByCode).flat();
              if (!visible.length) return " · OHLC: —";
              const hi = Math.max(...visible.map(b => Number(b.h) || Number(b.c) || 0));
              const lo = Math.min(...visible.map(b => Number(b.l) || Number(b.c) || Infinity));
              return " · OHLC: " + lo.toLocaleString("ko-KR") + "–" + hi.toLocaleString("ko-KR");
            })()}
          </div>
          {meta && meta.replay_metadata && meta.replay_metadata.truncated && (
            <div className="research-empty" role="status">
              리플레이 원본이 안전 상한으로 잘렸습니다
              {meta.replay_metadata.row_capped_codes && meta.replay_metadata.row_capped_codes.length
                ? ": " + meta.replay_metadata.row_capped_codes.join(", ") : "."}
            </div>
          )}

          {selected.length > 0 && (
            <SimViewBar
              indicators={indicators} onToggleIndicator={toggleIndicator}
              chartMode={chartMode} onChartMode={setChartMode}
              splitCols={splitCols} onSplitCols={setSplitColsPersist}
              splitRows={splitRows} onSplitRows={setSplitRowsPersist}
              colCap={colCap} codeCount={codes.length}
              engineMode={engineMode} onEngineMode={setEngineModePersist}
              multi={codes.length > 1} />
          )}

          {wsErr && (
            <div className="panel"><div className="panel-bd">
              <div className="research-empty" style={{ color: "var(--red)" }}>
                리플레이 오류: {wsErr}
                <div style={{ marginTop: 8 }}>
                  <button className="btn ghost sm" onClick={startReplay} disabled={!canPlay && status !== "error"}>재시도</button>
                </div>
              </div>
            </div></div>
          )}
          {signalErr && (
            <div className="panel"><div className="panel-bd">
              <div className="research-empty" style={{ color: "var(--amber)" }}>
                {signalErr}
              </div>
            </div></div>
          )}

          {selected.length === 0 ? (
            <div className="panel"><div className="panel-bd">
              <div className="research-empty">
                왼쪽에서 날짜·종목(최대 {_SIM_MAX_CODES})을 선택하고 ▶ 재생을 누르면
                캔들 차트가 실시간으로 리플레이됩니다.
              </div>
            </div></div>
          ) : (chartMode === "overlay" && codes.length > 1) ? (
            // 오버레이 모드 — 정규화(시작=100) 한 차트 겹침 비교.
            <SimOverlayChart codes={codes} barsByCode={renderBarsByCode}
              nameByCode={nameByCode} curT={curT} />
          ) : (
            // 분할 모드 — 종목별 차트 그리드(반응형 열). 엔진 모드(라이브/LWC/SVG)로 컴포넌트 선택.
            <div style={{ display: "grid", gridTemplateColumns: gridCols, gap: dense ? 10 : 14, ...gridExtra }}>
              {codes.map(code => {
                const fullBars = barsByCode[code] || [];
                const renderedBars = renderBarsByCode[code] || [];
                const chartProps = {
                  code, name: nameByCode[code],
                  bars: renderedBars, fullBarCount: fullBars.length,
                  renderBudget, signals: signals[code] || [],
                  curT, compact: (codes.length > 1 && effCols > 1) || dense,
                  indicators,
                };
                return <SimChartByEngine key={code} engineMode={engineMode} {...chartProps} />;
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { SimulationTab };
