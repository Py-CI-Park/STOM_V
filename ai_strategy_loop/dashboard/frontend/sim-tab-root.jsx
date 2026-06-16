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
import { useState_sim, useEffect_sim, useCallback_sim, useRef_sim, useMemo_sim, _simFetchJson, _SIM_SPEEDS, _simWsBar, _SIM_MAX_CODES, _SIM_DEMO_SPEED, _SIM_MAX_SPLIT_COLS, _loadIndicators, _saveIndicators, _loadSplitCols, _saveSplitCols, _loadSplitRows, _saveSplitRows, _loadEngineMode, _saveEngineMode, _wsUrl, _simDemoSeen, _simMarkDemoSeen, _flattenSignals } from "./sim-tab-utils.jsx";
import { SimControlBar, SimPresetBar, SimMarketMinimap, SimPlaybackBar, SimViewBar } from "./sim-tab-controls.jsx";
import { SimChartByEngine, SimIndicatorTable, SimLearningPanel, SimVariableWatch } from "./sim-tab-panels.jsx";

// ===========================================================================
// 탭 루트 — 컨트롤 + WS 리플레이 상태머신 + 차트 그리드 + 체결 로그.
// ===========================================================================
function SimulationTab({ baseUrl, wsStatus }) {
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

  // 즉시 체험 — 자동 데모 진행 중 여부·프리셋 조회 busy·자동재생 대기 플래그.
  const [demoActive, setDemoActive] = useState_sim(false);   // 예시 자동 재생 배지 노출.
  const [presetBusy, setPresetBusy] = useState_sim(false);   // /sim/demo 조회 중.
  const pendingAutoplayRef = useRef_sim(false);              // date/selected 반영 후 자동재생 트리거.
  const demoTriedRef = useRef_sim(false);                    // 자동 데모 1회만 시도(재진입 루프 방지).

  // 보조지표 토글(MA·VWAP·볼린저) — localStorage 보존. 차트 라인 오버레이 제어.
  const [indicators, setIndicators] = useState_sim(_loadIndicators);
  // 멀티차트 보기 모드(split/overlay) + 분할 컬럼 수(1/2 — 강제 토글, auto=반응형).
  const [chartMode, setChartMode] = useState_sim("split");
  const [splitCols, setSplitCols] = useState_sim(_loadSplitCols);
  // 분할 행 캡(0=자동·무제한). 종목수/열 기반 자동 행을 사용자가 줄여 스크롤 그리드로 만든다.
  const [splitRows, setSplitRows] = useState_sim(_loadSplitRows);
  // 차트 엔진 모드(live/lwc/svg) — 기본 라이브(S4). localStorage 보존.
  const [engineMode, setEngineMode] = useState_sim(_loadEngineMode);

  // 학습 모드 — 신호 자동 일시정지 토글 + 하이라이트 신호 키.
  const [autoPause, setAutoPause] = useState_sim(false);
  const [highlightSig, setHighlightSig] = useState_sim(null);  // "code@buy_hms" 형태.
  // 이미 자동정지한 신호(중복 정지 방지) — ref 로 들고 리렌더 유발 안 함.
  const autoPausedRef = useRef_sim(new Set());

  const wsRef = useRef_sim(null);
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
      .then(j => setDays(Array.isArray(j && j.days) ? j.days : []))
      .catch(() => setDays([]));
    // src 변경 시 선택/리플레이 리셋(프리셋/데모 자동재생 대기 중이면 보존).
    if (!pendingAutoplayRef.current) {
      _stopReplay();
      setDate(""); setStocks([]); setSelected([]);
    }
  }, [baseUrl, isDemo, src]);

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
      .then(j => setStocks(Array.isArray(j && j.stocks) ? j.stocks : []))
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

  // 신호 로드(buy/sell + 선택 종목 변경 시). 종목별로 1일·1종목 백테 신호를 받는다.
  useEffect_sim(() => {
    if (isDemo || !baseUrl || !date || !buy || !sell || selected.length === 0) {
      setSignals({}); return;
    }
    let cancelled = false;
    const next = {};
    Promise.all(selected.map(code =>
      _simFetchJson(
        baseUrl + "/sim/signals?date=" + encodeURIComponent(date) + "&src=" + src +
        "&code=" + encodeURIComponent(code) +
        "&buy=" + encodeURIComponent(buy) + "&sell=" + encodeURIComponent(sell),
        200000
      ).then(j => { next[code] = (j && Array.isArray(j.trades)) ? j.trades : []; })
       .catch(() => { next[code] = []; })
    )).then(() => { if (!cancelled) setSignals(next); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, date, src, buy, sell, selected.join(",")]);

  // --- WS 리플레이 제어 ---
  const _stopReplay = useCallback_sim(() => {
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

  const startReplay = useCallback_sim(() => {
    if (isDemo || !baseUrl || !date || selected.length === 0) return;
    _stopReplay();
    const url = _wsUrl(baseUrl, "/sim/ws");
    if (!url) { setWsErr("WS URL 생성 실패"); setStatus("error"); return; }
    setWsErr(""); barsRef.current = {}; setBarsVersion(v => v + 1);

    let ws;
    try { ws = new WebSocket(url); } catch (e) { setWsErr(String(e)); setStatus("error"); return; }
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        action: "start", date: parseInt(date, 10), src,
        codes: selected, speed, agg_sec: parseInt(aggSec, 10) || 10,
      }));
      setStatus("playing");
    };
    ws.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (m.type === "meta") {
        setMeta({ codes: m.codes || [], bars_total: m.bars_total || 0, session_range: m.session_range || [0, 0] });
        setCursor(0);
      } else if (m.type === "bars") {
        // S1 결함 수정 — 코드별 시계열에 **불변(immutable) append**.
        //   기존 .push() 는 같은 배열을 mutate 해 per-code 배열 참조가 안 바뀌어
        //   SimCandleChartLWC 의 useEffect([bars]) 가 최초 1회만 돌아 봉·거래량이 1개로 동결됐다.
        //   → 매 프레임 새 배열을 만들어(store[code] = [...prev, bar]) 참조를 갱신해야
        //     LWC effect 가 매번 재실행되며 봉·거래량 히스토그램이 정상 리플레이된다.
        const store = barsRef.current;
        (m.items || []).forEach(it => {
          store[it.code] = [...(store[it.code] || []), _simWsBar(it, m.t)];   // 새 배열 참조(불변 append).
        });
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
        setStatus(s => (s === "playing" || s === "paused") ? "done" : s);
      } else if (m.type === "error") {
        setWsErr(m.message || "리플레이 오류"); setStatus("error");
      }
    };
    ws.onerror = () => { setWsErr("WebSocket 연결 오류"); setStatus("error"); };
    ws.onclose = () => { if (wsRef.current === ws) wsRef.current = null; };
  }, [baseUrl, isDemo, date, src, selected, speed, aggSec, _stopReplay]);

  const _wsSend = (payload) => {
    if (wsRef.current && wsRef.current.readyState === 1) {
      try { wsRef.current.send(JSON.stringify(payload)); } catch (e) {}
    }
  };

  const pauseReplay = () => { _wsSend({ action: "pause" }); setStatus("paused"); };
  const resumeReplay = () => { _wsSend({ action: "resume" }); setStatus("playing"); };
  const changeSpeed = (sp) => { setSpeed(sp); _wsSend({ action: "speed", value: sp }); };
  const seekTo = (idx) => {
    setCursor(idx);
    if (meta && meta.session_range) {
      _wsSend({ action: "seek", t: idx });  // 서버는 t(HHMMSS) 기대 — 아래 보정.
    }
  };

  // seek 슬라이더는 frame 인덱스 기준 — 서버 seek 은 t(HHMMSS) 이므로 인덱스→t 변환이 필요.
  //   meta 만으로는 frame t 목록을 모르므로, 누적 수신된 bar 의 t 를 참조하거나(앞쪽)
  //   세션 범위 선형 보간으로 근사한다(뒤쪽 미수신 구간). 단순·실용 우선.
  const seekByIndex = (idx) => {
    setCursor(idx);
    const range = meta && meta.session_range;
    if (!range || range[1] <= range[0] || !meta.bars_total) return;
    const frac = meta.bars_total > 1 ? idx / (meta.bars_total - 1) : 0;
    const approxT = Math.round(range[0] + frac * (range[1] - range[0]));
    _wsSend({ action: "seek", t: approxT });
  };

  const stopReplay = () => { _stopReplay(); };

  // --- 즉시 체험: /sim/demo 추천 적용 + 자동재생 ---
  //   서버가 날짜·등락 1위 종목을 직접 주므로 stocks 목록 로딩을 기다리지 않고 바로 선택한다.
  //   date/selected/src/speed 를 세팅한 뒤 pendingAutoplay 플래그로 다음 렌더에서 재생 시작.
  const applyDemo = useCallback_sim((mode, asDemo) => {
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
        pendingAutoplayRef.current = true;
        setPresetBusy(false);
      })
      .catch(() => { setPresetBusy(false); if (asDemo) setDemoActive(false); });
  }, [baseUrl, isDemo, _stopReplay]);

  // 자동재생 트리거 — applyDemo 가 세팅한 date/selected 가 반영되면 1회 재생 시작.
  useEffect_sim(() => {
    if (!pendingAutoplayRef.current) return;
    if (!date || selected.length === 0) return;
    pendingAutoplayRef.current = false;
    startReplay();
  }, [date, selected, startReplay]);

  // 최초 진입 자동 데모 — 선택 없음 + 미시청 + 백엔드 연결 시 1회. localStorage 로 재방문 시 생략.
  useEffect_sim(() => {
    if (demoTriedRef.current) return;
    if (isDemo || !baseUrl) return;
    if (selected.length > 0 || date) return;        // 이미 사용자가 고른 상태면 데모 안 함.
    if (_simDemoSeen()) return;                     // 이전에 본 적 있으면 강제 안 함.
    demoTriedRef.current = true;
    _simMarkDemoSeen();
    applyDemo("latest", true);
  }, [baseUrl, isDemo, applyDemo]);

  // 사용자가 직접 선택/조작하면 데모 배지 해제(자동재생 컨텍스트 종료).
  const exitDemo = useCallback_sim(() => {
    setDemoActive(false);
    pendingAutoplayRef.current = false;
    _stopReplay();
    setDate(""); setSelected([]);
  }, [_stopReplay]);

  // 프리셋 클릭(수동) — 데모 배지 없이 추천 적용 + 자동재생.
  const onPreset = useCallback_sim((mode) => {
    setDemoActive(false);
    applyDemo(mode, false);
  }, [applyDemo]);

  // 렌더·로직 공용 파생값(차트 그리드·신호 평탄화·재생 가능 여부).
  const codes = (meta && meta.codes && meta.codes.length) ? meta.codes : selected;
  const canPlay = !isDemo && !!date && selected.length > 0 && (status === "idle" || status === "done" || status === "error");
  // 키보드 핸들러가 stale 클로저로 보지 않도록 canPlay 를 ref 로 미러링.
  const canPlayRef = useRef_sim(canPlay);
  useEffect_sim(() => { canPlayRef.current = canPlay; }, [canPlay]);

  // 신호 시각(HHMMSS)으로 직접 시킹 — 북마크 클릭용. 서버 seek 은 t(HHMMSS)를 직접 받는다.
  const seekToTime = useCallback_sim((hms) => {
    if (hms == null) return;
    _wsSend({ action: "seek", t: hms });
    setCurT(hms);
    // 커서 근사(세션 범위 선형 역보간) — 슬라이더/진행률 표시용.
    const range = meta && meta.session_range;
    if (range && range[1] > range[0] && meta.bars_total) {
      const frac = (hms - range[0]) / (range[1] - range[0]);
      setCursor(Math.max(0, Math.min(meta.bars_total, Math.round(frac * (meta.bars_total - 1)))));
    }
  }, [meta]);

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
      const tag = (e.target && e.target.tagName) || "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (e.target && e.target.isContentEditable)) return;
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
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: "checking", color: "var(--amber)" };

  // 렌더용 코드별 bar 시계열(barsVersion 의존).
  const barsByCode = useMemo_sim(() => ({ ...barsRef.current }), [barsVersion]);
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
                예시 자동 재생
              </span>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                준비된 데이터로 둘러보는 중 · {_SIM_DEMO_SPEED}x
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

          {selected.length === 0 ? (
            <div className="panel"><div className="panel-bd">
              <div className="research-empty">
                왼쪽에서 날짜·종목(최대 {_SIM_MAX_CODES})을 선택하고 ▶ 재생을 누르면
                캔들 차트가 실시간으로 리플레이됩니다.
              </div>
            </div></div>
          ) : (chartMode === "overlay" && codes.length > 1) ? (
            // 오버레이 모드 — 정규화(시작=100) 한 차트 겹침 비교.
            <SimOverlayChart codes={codes} barsByCode={barsByCode}
              nameByCode={nameByCode} curT={curT} />
          ) : (
            // 분할 모드 — 종목별 차트 그리드(반응형 열). 엔진 모드(라이브/LWC/SVG)로 컴포넌트 선택.
            <div style={{ display: "grid", gridTemplateColumns: gridCols, gap: dense ? 10 : 14, ...gridExtra }}>
              {codes.map(code => {
                const chartProps = {
                  code, name: nameByCode[code],
                  bars: barsByCode[code] || [], signals: signals[code] || [],
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
