/* Chart simulation tab — PR3 (일일 tick/min DB 리플레이 + 조건식 매매 오버레이).
   /sim/* REST + WS /sim/ws 를 소비한다(simulation_api.py·replay_engine.py).
   디자인 언어: 다크 테마(var(--bg-1)/var(--line-1)) · mono 라벨 · panel/btn 클래스 재사용.

   캔들 차트·체결 로그는 simulation-charts.jsx 의 순수 SVG 컴포넌트 사용
   (window 전역, index.html 에서 이 파일보다 먼저 로드). 외부 차트 라이브러리 금지.
   WS push 기반(폴링 없음) — meta→bars(배치)→done 프로토콜. 재연결·에러 빈상태 처리. */
const {
  useState: useState_sim, useEffect: useEffect_sim,
  useCallback: useCallback_sim, useRef: useRef_sim, useMemo: useMemo_sim,
} = React;

// 무예외 fetch 헬퍼.
function _simFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 6000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

const _SIM_SPEEDS = [1, 5, 20, 60, 240];
const _SIM_MAX_CODES = 4;

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

// ===========================================================================
// 1. 컨트롤 바 — src·날짜·종목 멀티선택·조건식 buy/sell·agg_sec.
// ===========================================================================
function SimControlBar({
  baseUrl, isDemo, src, onSrc, date, onDate, days,
  stocks, selected, onToggleStock, stockQuery, onStockQuery,
  buy, onBuy, sell, onSell, strategies, aggSec, onAggSec, loadingStocks,
}) {
  const filteredStocks = useMemo_sim(() => {
    const q = (stockQuery || "").trim().toLowerCase();
    if (!q) return stocks;
    return stocks.filter(s =>
      (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
  }, [stocks, stockQuery]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          리플레이 설정
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {/* src + 날짜 + agg */}
        <div className="field-row">
          <div className="field">
            <label>시간단위</label>
            <div style={{ display: "flex", gap: 4 }}>
              {[["tick", "틱"], ["min", "분봉"]].map(([k, lbl]) => (
                <button key={k} onClick={() => onSrc(k)} className="mono" disabled={isDemo}
                  style={{
                    flex: 1, padding: "5px 8px", fontSize: 11, borderRadius: 5,
                    border: "1px solid " + (src === k ? "var(--teal-dim)" : "var(--line-1)"),
                    background: src === k ? "rgba(76,214,179,0.08)" : "transparent",
                    color: src === k ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                  }}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>날짜 ({days.length}일)</label>
            <select className="select" value={date || ""} onChange={e => onDate(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {days.map(d => <option key={d} value={d}>{_simFmtDate(d)}</option>)}
            </select>
          </div>
          {src === "tick" && (
            <div className="field" style={{ maxWidth: 110 }}>
              <label>집계(초)</label>
              <input className="input" type="number" min="1" max="60" value={aggSec}
                     onChange={e => onAggSec(e.target.value)} disabled={isDemo} />
            </div>
          )}
        </div>

        {/* 조건식 buy/sell */}
        <div className="field-row">
          <div className="field">
            <label>매수 조건식 (신호 오버레이)</label>
            <select className="select" value={buy} onChange={e => onBuy(e.target.value)} disabled={isDemo}>
              <option value="">— 없음 —</option>
              {strategies.buy.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field">
            <label>매도 조건식</label>
            <select className="select" value={sell} onChange={e => onSell(e.target.value)} disabled={isDemo}>
              <option value="">— 없음 —</option>
              {strategies.sell.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>

        {/* 종목 멀티선택(최대 4, 등락순 + 검색) */}
        <div className="field">
          <label>
            종목 선택 (최대 {_SIM_MAX_CODES} · 등락순)
            <span className="mono" style={{ color: "var(--ink-3)", marginLeft: 8 }}>
              {selected.length}/{_SIM_MAX_CODES} 선택
            </span>
          </label>
          <input className="input" placeholder="코드/이름 검색…" value={stockQuery}
                 onChange={e => onStockQuery(e.target.value)} spellCheck={false}
                 disabled={isDemo || !date} style={{ marginBottom: 6 }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 2, maxHeight: 220, overflowY: "auto" }}>
            {isDemo ? (
              <div className="research-empty">데모 모드 — 백엔드 연결 시 종목 목록이 표시됩니다.</div>
            ) : !date ? (
              <div className="research-empty">날짜를 먼저 선택하세요.</div>
            ) : loadingStocks ? (
              <div className="research-empty">종목 로딩 중…</div>
            ) : filteredStocks.length === 0 ? (
              <div className="research-empty">{stockQuery ? "검색 결과 없음" : "종목이 없습니다"}</div>
            ) : filteredStocks.map(s => {
              const active = selected.includes(s.code);
              const disabled = !active && selected.length >= _SIM_MAX_CODES;
              return (
                <button key={s.code} onClick={() => onToggleStock(s.code)} disabled={disabled}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "5px 8px", borderRadius: 5,
                    border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
                    background: active ? "rgba(76,214,179,0.08)" : "var(--bg-0)",
                    cursor: disabled ? "not-allowed" : "pointer", opacity: disabled ? 0.4 : 1,
                    textAlign: "left",
                  }}>
                  <span className="mono" style={{ fontSize: 11, color: active ? "var(--teal)" : "var(--ink-1)", flexShrink: 0, width: 56 }}>
                    {s.code}
                  </span>
                  <span style={{ fontSize: 11.5, color: "var(--ink-1)", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {s.name}
                  </span>
                  <span className={"mono " + (s.last_change_pct > 0 ? "num-pos" : s.last_change_pct < 0 ? "num-neg" : "")}
                        style={{ fontSize: 10.5, flexShrink: 0, width: 56, textAlign: "right" }}>
                    {s.last_change_pct > 0 ? "+" : ""}{(s.last_change_pct || 0).toFixed(2)}%
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

function _simFmtDate(d) {
  const s = String(d);
  if (s.length === 8) return s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
  return s;
}

// ===========================================================================
// 2. 재생 컨트롤 — ▶/⏸/⏹, 배속, 진행 슬라이더(seek), 현재 시각.
// ===========================================================================
function SimPlaybackBar({
  status, onPlay, onPause, onResume, onStop,
  speed, onSpeed, cursor, total, curT, sessionRange, onSeek, canPlay,
}) {
  const playing = status === "playing";
  const paused = status === "paused";
  const pct = total > 0 ? Math.round((cursor / total) * 100) : 0;

  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {!playing && !paused && (
            <button className="btn primary" onClick={onPlay} disabled={!canPlay}>▶ 재생</button>
          )}
          {playing && <button className="btn" onClick={onPause}>⏸ 일시정지</button>}
          {paused && <button className="btn primary" onClick={onResume}>▶ 재개</button>}
          {(playing || paused) && <button className="btn danger" onClick={onStop}>⏹ 정지</button>}

          {/* 배속 */}
          <div style={{ display: "flex", gap: 3, marginLeft: 8 }}>
            {_SIM_SPEEDS.map(sp => (
              <button key={sp} onClick={() => onSpeed(sp)} className="mono"
                style={{
                  padding: "4px 8px", fontSize: 10.5, borderRadius: 4,
                  border: "1px solid " + (speed === sp ? "var(--teal-dim)" : "var(--line-1)"),
                  background: speed === sp ? "rgba(76,214,179,0.08)" : "transparent",
                  color: speed === sp ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                }}>
                {sp === 240 ? "최대" : sp + "x"}
              </button>
            ))}
          </div>

          <span className="mono" style={{ fontSize: 11, color: "var(--ink-1)", marginLeft: "auto" }}>
            {curT != null ? window._simTimeLabel(curT) : "--:--:--"}
            <span style={{ color: "var(--ink-3)" }}> · {cursor}/{total}</span>
          </span>
        </div>

        {/* 진행 슬라이더(seek) */}
        <input type="range" min="0" max={Math.max(0, total - 1)} value={cursor}
               disabled={!total} onChange={e => onSeek(parseInt(e.target.value, 10))}
               style={{ width: "100%", accentColor: "var(--teal)", cursor: total ? "pointer" : "default" }} />
        <div className="progress-track">
          <div className={"progress-fill " + (playing ? "running" : "")} style={{ width: pct + "%" }}></div>
        </div>
      </div>
    </div>
  );
}

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
    // src 변경 시 선택/리플레이 리셋.
    _stopReplay();
    setDate(""); setStocks([]); setSelected([]);
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
    setSelected([]); _stopReplay();
  }, [baseUrl, isDemo, date]);

  const toggleStock = useCallback_sim((code) => {
    setSelected(prev => {
      if (prev.includes(code)) return prev.filter(c => c !== code);
      if (prev.length >= _SIM_MAX_CODES) return prev;
      return [...prev, code];
    });
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
        // 코드별 시계열에 append.
        const store = barsRef.current;
        (m.items || []).forEach(it => {
          if (!store[it.code]) store[it.code] = [];
          store[it.code].push({ t: m.t, o: it.o, h: it.h, l: it.l, c: it.c, vol: it.vol, change: it.change, strength: it.strength });
        });
        setCursor((m.index || 0) + 1);
        setCurT(m.t);
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

  const connected = !!(health && health.status === "ok");
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: "checking", color: "var(--amber)" };

  // 렌더용 코드별 bar 시계열(barsVersion 의존).
  const barsByCode = useMemo_sim(() => ({ ...barsRef.current }), [barsVersion]);
  const codes = (meta && meta.codes && meta.codes.length) ? meta.codes : selected;
  const gridCols = codes.length <= 1 ? "1fr" : "1fr 1fr";
  const nameByCode = useMemo_sim(() => {
    const m = {};
    stocks.forEach(s => { m[s.code] = s.name; });
    return m;
  }, [stocks]);
  const canPlay = !isDemo && !!date && selected.length > 0 && (status === "idle" || status === "done" || status === "error");

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
        {/* 좌: 컨트롤 + 체결 로그 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <SimControlBar
            baseUrl={baseUrl} isDemo={isDemo} src={src} onSrc={setSrc}
            date={date} onDate={setDate} days={days}
            stocks={stocks} selected={selected} onToggleStock={toggleStock}
            stockQuery={stockQuery} onStockQuery={setStockQuery} loadingStocks={loadingStocks}
            buy={buy} onBuy={setBuy} sell={sell} onSell={setSell} strategies={strategies}
            aggSec={aggSec} onAggSec={setAggSec} />
          {(buy && sell) && (
            <SimSignalLog signals={_flattenSignals(signals, codes)} curT={curT} />
          )}
        </div>

        {/* 우: 재생 컨트롤 + 차트 그리드 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <SimPlaybackBar
            status={status} onPlay={startReplay} onPause={pauseReplay}
            onResume={resumeReplay} onStop={stopReplay}
            speed={speed} onSpeed={changeSpeed} cursor={cursor}
            total={meta ? meta.bars_total : 0} curT={curT}
            sessionRange={meta ? meta.session_range : [0, 0]} onSeek={seekByIndex} canPlay={canPlay} />

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
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: gridCols, gap: 14 }}>
              {codes.map(code => (
                <SimCandleChart key={code} code={code} name={nameByCode[code]}
                  bars={barsByCode[code] || []} signals={signals[code] || []}
                  curT={curT} compact={codes.length > 1} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// 종목별 신호를 단일 로그용 평탄화(매수 시각순 정렬).
function _flattenSignals(signals, codes) {
  const out = [];
  (codes || []).forEach(code => {
    (signals[code] || []).forEach(s => out.push({ ...s, code }));
  });
  out.sort((a, b) => a.buy_hms - b.buy_hms);
  return out;
}

Object.assign(window, { SimulationTab });
