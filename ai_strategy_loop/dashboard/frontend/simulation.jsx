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
const _SIM_MAX_CODES = 10;                  // S2 동시보기 1~10(백엔드 replay_engine.MAX_CODES 와 일치).
const _SIM_DEMO_SPEED = 20;                 // 자동 데모 배속(빠른 둘러보기).
// 차트 엔진 모드 — 라이브(Canvas·기본) / LWC(lightweight-charts) / SVG(폴백 순수 SVG).
//   S4: "라이브" 가 기본. 멀티 비교용 overlay 는 별도 보기 모드(_SIM_VIEW_MODES)로 분리.
const _SIM_ENGINE_MODES = [["live", "라이브"], ["lwc", "LWC"], ["svg", "SVG"]];
const _SIM_ENGINE_LS_KEY = "stom.sim.engine.v1";
// 멀티차트 보기 모드 — split(분할 그리드) / overlay(정규화 한 차트 겹침).
const _SIM_CHART_MODES = [["split", "분할"], ["overlay", "오버레이"]];
// 분할 그리드 컬럼 토글(1/2 — 4종목이면 2열이 2×2). 단일 종목은 항상 1열.
const _SIM_SPLIT_LS_KEY = "stom.sim.split.v1";
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
// 분할 컬럼(1/2) 로드/저장.
function _loadSplitCols() {
  try {
    const v = parseInt(window.localStorage.getItem(_SIM_SPLIT_LS_KEY), 10);
    return v === 1 ? 1 : 2;
  } catch (e) { return 2; }
}
function _saveSplitCols(v) {
  try { window.localStorage.setItem(_SIM_SPLIT_LS_KEY, String(v)); } catch (e) {}
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
// 1c. 원클릭 프리셋 바 — [최근 거래일]·[최대 상승일] 즉시 적용(서버 /sim/demo 추천).
//     클릭 시 추천 날짜·등락 1위 종목을 선택하고 자동 재생까지 트리거한다.
// ===========================================================================
function SimPresetBar({ isDemo, busy, onPreset }) {
  if (isDemo) return null;
  const presets = [
    { mode: "latest", label: "최근 거래일", hint: "마지막 거래일·등락 1위" },
    { mode: "top_gainer", label: "최대 상승일", hint: "최근 중 등락 최대일" },
  ];
  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", padding: "8px 10px" }}>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginRight: 2 }}>
          빠른 시작
        </span>
        {presets.map(p => (
          <button key={p.mode} className="btn sm" onClick={() => onPreset(p.mode)} disabled={busy}
                  title={p.hint}
                  style={{ fontSize: 11, padding: "4px 10px", opacity: busy ? 0.5 : 1 }}>
            ⚡ {p.label}
          </button>
        ))}
        {busy && <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>추천 조회 중…</span>}
      </div>
    </div>
  );
}

// ===========================================================================
// 1b. 시장 미니맵 — 그날 종목을 등락율 색상 타일 그리드로(상승 빨강/하락 파랑 농도).
//     타일 클릭 → 선택 토글(최대 4). 선택 타일 테두리 강조. 검색 필터와 공존.
// ===========================================================================
// 등락율(%) → 타일 배경색. 상승=빨강 계열, 하락=파랑 계열, 0=중립 회색. 농도는 |등락|로.
function _simTileColor(pct) {
  const v = Number(pct) || 0;
  const mag = Math.min(1, Math.abs(v) / 12);   // ±12% 에서 최대 농도 포화.
  const a = 0.12 + mag * 0.7;
  if (v > 0) return `rgba(255,93,108,${a.toFixed(3)})`;   // 상승 빨강(--red 계열).
  if (v < 0) return `rgba(56,140,255,${a.toFixed(3)})`;   // 하락 파랑.
  return "rgba(150,158,170,0.14)";                         // 보합 중립.
}

function SimMarketMinimap({ stocks, selected, onToggleStock, query, isDemo, date, loading }) {
  // 검색 필터와 공존 — 컨트롤바와 동일 규칙(코드/이름 부분일치).
  const tiles = useMemo_sim(() => {
    const q = (query || "").trim().toLowerCase();
    const base = stocks || [];
    if (!q) return base;
    return base.filter(s =>
      (s.code || "").toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q));
  }, [stocks, query]);

  let body;
  if (isDemo) {
    body = <div className="research-empty">데모 모드 — 백엔드 연결 시 시장 미니맵이 표시됩니다.</div>;
  } else if (!date) {
    body = <div className="research-empty">날짜를 먼저 선택하세요.</div>;
  } else if (loading) {
    body = <div className="research-empty">미니맵 로딩 중…</div>;
  } else if (tiles.length === 0) {
    body = <div className="research-empty">{query ? "검색 결과 없음" : "종목이 없습니다"}</div>;
  } else {
    body = (
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(74px, 1fr))",
        gap: 4, maxHeight: 240, overflowY: "auto",
      }}>
        {tiles.map(s => {
          const active = selected.includes(s.code);
          const atCap = !active && selected.length >= _SIM_MAX_CODES;
          const pct = Number(s.last_change_pct) || 0;
          return (
            <button key={s.code} onClick={() => onToggleStock(s.code)} disabled={atCap}
              title={s.code + " · " + (s.name || "") + " · " + (pct > 0 ? "+" : "") + pct.toFixed(2) + "%"}
              style={{
                display: "flex", flexDirection: "column", gap: 1, padding: "5px 6px",
                borderRadius: 5, textAlign: "left", overflow: "hidden",
                border: "1.5px solid " + (active ? "var(--teal)" : "transparent"),
                background: _simTileColor(pct),
                cursor: atCap ? "not-allowed" : "pointer", opacity: atCap ? 0.45 : 1,
                boxShadow: active ? "0 0 0 1px var(--teal-dim) inset" : "none",
              }}>
              <span style={{
                fontSize: 10.5, color: "var(--ink-1)", fontWeight: active ? 600 : 400,
                overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
              }}>
                {s.name || s.code}
              </span>
              <span className="mono" style={{ fontSize: 10, color: pct >= 0 ? "#ffd2d6" : "#cfe0ff" }}>
                {pct > 0 ? "+" : ""}{pct.toFixed(2)}%
              </span>
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--red)" }}></span>
          시장 미니맵
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
          {selected.length}/{_SIM_MAX_CODES} 선택 · 등락순
        </span>
      </div>
      <div className="panel-bd" style={{ padding: "8px 10px" }}>{body}</div>
    </div>
  );
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

          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", marginLeft: 6 }}
                title="1x = 실시간(1초봉 1초/1분봉 1분). 배속만큼 빠르게 흐릅니다.">
            ⏱ {speed === 1 ? "실시간" : speed + "x"} 페이싱
          </span>
          <span className="mono" style={{ fontSize: 13, color: "var(--teal)", marginLeft: "auto", letterSpacing: ".04em" }}>
            {curT != null ? window._simTimeLabel(curT) : "--:--:--"}
            <span style={{ color: "var(--ink-3)", fontSize: 11 }}> · {cursor}/{total}</span>
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
          const bar = {
            t: m.t, o: it.o, h: it.h, l: it.l, c: it.c, vol: it.vol,
            change: it.change, strength: it.strength,
            ma5: it.ma5, ma20: it.ma20, ma60: it.ma60, imbalance: it.imbalance,
            buy_rest: it.buy_rest, sell_rest: it.sell_rest,
            vwap: it.vwap, bb_mid: it.bb_mid, bb_up: it.bb_up, bb_low: it.bb_low,
            net_qty: it.net_qty, bid1: it.bid1, ask1: it.ask1,
          };
          store[it.code] = [...(store[it.code] || []), bar];   // 새 배열 참조(불변 append).
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
  // S2 분할 그리드 컬럼 — 단일 종목은 1열. 사용자가 1/2열을 강제하면 우선,
  //   아니면 개수 기반 반응형(2~4→2 / 5~9→3 / 10→4)으로 화면을 최대 활용.
  const autoCols = _responsiveCols(codes.length);
  const effCols = codes.length <= 1 ? 1 : (splitCols === 1 ? 1 : (splitCols === 2 && autoCols <= 2 ? 2 : autoCols));
  const gridCols = "repeat(" + effCols + ", minmax(0, 1fr))";
  // S2 컴팩트 — 5개 이상이면 차트 높이·보조패널을 축소(과밀 방지).
  const dense = codes.length >= 5;
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
            <div style={{ display: "grid", gridTemplateColumns: gridCols, gap: dense ? 10 : 14 }}>
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

// ===========================================================================
// 엔진 디스패처 — engineMode(live/lwc/svg)에 맞는 차트 컴포넌트를 고른다.
//   live  → window.SimLiveChart(Canvas·기본). 미로드(부재)면 SimCandleChart 로 폴백(무중단).
//   lwc   → window.SimCandleChartLWC(부재 시 SimCandleChart 자동선택).
//   svg   → window.SimCandleChartSVG(부재 시 SimCandleChart).
//   모든 경로는 동일 props(bars/signals/curT/code/name/compact/indicators)를 받는다.
// ===========================================================================
function SimChartByEngine({ engineMode, ...props }) {
  const Live = window.SimLiveChart;
  const Lwc = window.SimCandleChartLWC;
  const Svg = window.SimCandleChartSVG;
  const Auto = window.SimCandleChart;
  if (engineMode === "live" && Live) return <Live {...props} />;
  if (engineMode === "svg" && Svg) return <Svg {...props} />;
  if (engineMode === "lwc" && Lwc) return <Lwc {...props} />;
  // 폴백 — 선택 엔진 컴포넌트가 아직 window 에 없으면 자동선택(LWC↔SVG) 래퍼.
  return Auto ? <Auto {...props} /> : null;
}

// ===========================================================================
// 보기 도구 바 — 엔진 모드(라이브/LWC/SVG) + 보조지표 토글(MA·VWAP·볼린저)
//   + 멀티차트 모드(분할/오버레이) + 분할 열(1/2).
// ===========================================================================
function SimViewBar({ indicators, onToggleIndicator, chartMode, onChartMode,
                      splitCols, onSplitCols, multi, engineMode, onEngineMode }) {
  const indDefs = [["ma", "MA"], ["vwap", "VWAP"], ["boll", "볼린저"]];
  const tbtn = (active, label, onClick, key, title) => (
    <button key={key} onClick={onClick} className="mono" title={title}
      style={{
        padding: "3px 9px", fontSize: 10.5, borderRadius: 4,
        border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
        background: active ? "rgba(76,214,179,0.10)" : "transparent",
        color: active ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
      }}>
      {label}
    </button>
  );
  return (
    <div className="panel">
      <div className="panel-bd" style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap", padding: "7px 10px" }}>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>엔진</span>
        <div style={{ display: "flex", gap: 4 }}>
          {_SIM_ENGINE_MODES.map(([m, lbl]) =>
            tbtn(engineMode === m, lbl, () => onEngineMode(m), "e" + m,
                 m === "live" ? "Canvas 라이브 렌더(현재봉 성장·플래시)"
                   : m === "lwc" ? "lightweight-charts 엔진" : "순수 SVG 폴백"))}
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>지표</span>
        <div style={{ display: "flex", gap: 4 }}>
          {indDefs.map(([k, lbl]) => tbtn(!!indicators[k], lbl, () => onToggleIndicator(k), k))}
        </div>
        {multi && (
          <>
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>보기</span>
            <div style={{ display: "flex", gap: 4 }}>
              {_SIM_CHART_MODES.map(([m, lbl]) =>
                tbtn(chartMode === m, lbl, () => onChartMode(m), m,
                     m === "overlay" ? "정규화 한 차트 겹침" : "종목별 분할 그리드"))}
            </div>
            {chartMode === "split" && (
              <div style={{ display: "flex", gap: 4 }}>
                {[[2, "2열"], [1, "1열"]].map(([v, lbl]) =>
                  tbtn(splitCols === v, lbl, () => onSplitCols(v), "c" + v))}
              </div>
            )}
          </>
        )}
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

// ===========================================================================
// 변수 라이브 뷰 — 종목별 현재 지표 테이블(현재가·등락·체결강도·MA5/20/60·호가불균형).
//   갱신 시 값 변화 방향(상승=teal / 하락=red)으로 셀 색 플래시.
// ===========================================================================
function _simFmtNum(v, digits) {
  if (v == null) return "—";
  const n = Number(v);
  if (!isFinite(n)) return "—";
  return n.toLocaleString("ko-KR", { maximumFractionDigits: digits == null ? 0 : digits });
}

function SimIndicatorCell({ value, digits, prev, className }) {
  // 이전값 대비 방향으로 1회 플래시. key 를 값+버전으로 바꿔 애니메이션 재시작.
  const dir = (prev == null || value == null || value === prev) ? "" :
    (value > prev ? "sim-flash-up" : "sim-flash-down");
  return (
    <td key={value + ":" + dir} className={(className || "") + " " + dir}>
      {_simFmtNum(value, digits)}
    </td>
  );
}

function SimIndicatorTable({ codes, barsByCode, nameByCode }) {
  const prevRef = useRef_sim({});
  const rows = (codes || []).map(code => {
    const arr = barsByCode[code] || [];
    const last = arr.length ? arr[arr.length - 1] : null;
    return { code, name: nameByCode[code] || code, bar: last };
  });
  // 이전값 스냅샷(렌더 후 갱신).
  const prev = prevRef.current;
  useEffect_sim(() => {
    const next = {};
    rows.forEach(r => { if (r.bar) next[r.code] = r.bar; });
    prevRef.current = next;
  });

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          지표 라이브
        </div>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>현재 시각 기준</span>
      </div>
      <div className="panel-bd" style={{ overflowX: "auto", padding: "6px 8px" }}>
        <table className="sim-live-table">
          <thead>
            <tr>
              <th>종목</th><th>현재가</th><th>등락%</th><th>강도</th>
              <th>VWAP</th><th>MA5</th><th>MA20</th><th>MA60</th><th>호가불균형</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ code, name, bar }) => {
              const p = prev[code] || {};
              if (!bar) {
                return (
                  <tr key={code}>
                    <td title={name}>{code}</td>
                    <td colSpan={8} style={{ color: "var(--ink-3)" }}>대기…</td>
                  </tr>
                );
              }
              return (
                <tr key={code}>
                  <td title={name} style={{ color: "var(--ink-1)" }}>{code}</td>
                  <SimIndicatorCell value={bar.c} digits={0} prev={p.c} />
                  <td className={bar.change > 0 ? "num-pos" : bar.change < 0 ? "num-neg" : ""}>
                    {bar.change > 0 ? "+" : ""}{(bar.change || 0).toFixed(2)}
                  </td>
                  <SimIndicatorCell value={bar.strength} digits={0} prev={p.strength} />
                  <SimIndicatorCell value={bar.vwap} digits={0} prev={p.vwap} />
                  <SimIndicatorCell value={bar.ma5} digits={0} prev={p.ma5} />
                  <SimIndicatorCell value={bar.ma20} digits={0} prev={p.ma20} />
                  <SimIndicatorCell value={bar.ma60} digits={0} prev={p.ma60} />
                  <SimIndicatorCell value={bar.imbalance} digits={2} prev={p.imbalance} />
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ===========================================================================
// 학습 모드 패널 — 신호 자동 일시정지 토글 + 키보드 힌트 + 신호 북마크(클릭 시킹).
// ===========================================================================
function SimLearningPanel({ autoPause, onToggleAutoPause, signals, curT, highlightSig, onSeek }) {
  const rows = signals || [];
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          학습 모드
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10, padding: "10px" }}>
        {/* 자동 일시정지 토글 */}
        <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
          <input type="checkbox" checked={autoPause} onChange={onToggleAutoPause}
                 style={{ accentColor: "var(--violet)" }} />
          <span style={{ fontSize: 11.5, color: "var(--ink-1)" }}>신호 자동 일시정지</span>
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", marginLeft: "auto" }}>
            매수 시각 도달 시 정지
          </span>
        </label>

        {/* 키보드 힌트 */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", fontSize: 10, color: "var(--ink-3)" }}>
          <span className="sim-kbd">Space</span> 재생/정지
          <span className="sim-kbd">←</span><span className="sim-kbd">→</span> 배속
          <span className="sim-kbd">Esc</span> 정지
        </div>

        {/* 신호 북마크 목록 → 클릭 시킹 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 3, maxHeight: 200, overflowY: "auto" }}>
          {rows.length === 0 ? (
            <div className="research-empty" style={{ fontSize: 10.5 }}>매매 신호가 없습니다.</div>
          ) : rows.map((s, i) => {
            const key = s.code + "@" + s.buy_hms;
            const reached = curT != null && s.buy_hms <= curT;
            const isHi = highlightSig === key;
            return (
              <button key={i} className={"sim-bookmark " + (reached ? "reached" : "pending")}
                onClick={() => onSeek(s.buy_hms)}
                style={isHi ? { borderColor: "var(--violet)", background: "rgba(124,108,240,0.12)" } : null}>
                <span className="mono" style={{ fontSize: 10, color: "var(--teal)", flexShrink: 0 }}>
                  ▲{window._simTimeLabel(s.buy_hms)}
                </span>
                <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", flexShrink: 0 }}>
                  {s.code}
                </span>
                <span className={"mono " + (s.profit_pct >= 0 ? "num-pos" : "num-neg")}
                      style={{ fontSize: 10.5, marginLeft: "auto", flexShrink: 0 }}>
                  {s.profit_pct >= 0 ? "+" : ""}{(s.profit_pct || 0).toFixed(1)}%
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// 변수 워치 패널 — 현재 프레임 값 + 사용자 임계 비교(≥/≤). 충족 행 녹색/미충족 적색,
//   충족 순간 1회 플래시. 임계 세트는 localStorage 저장(조건식 코드 평가는 범위 외 —
//   엔진 정합 신호는 /sim/signals 가 담당). 단일 종목(첫 선택) 기준.
// ===========================================================================
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

function SimVariableWatch({ codes, barsByCode, nameByCode }) {
  // 임계 맵: key → {op:">="|"<=", value:string}. localStorage 동기화.
  const [thresholds, setThresholds] = useState_sim(_loadWatchThresholds);
  // 워치 대상 종목(첫 선택). 다종목이어도 워치는 1종목 집중(직관·과밀 방지).
  const [watchCode, setWatchCode] = useState_sim((codes && codes[0]) || "");
  // 직전 충족 상태(플래시 트리거용) — ref 로 들고 리렌더 유발 안 함.
  const prevMetRef = useRef_sim({});

  // codes 변경 시 워치 종목 보정(현재 선택이 사라지면 첫 종목으로).
  useEffect_sim(() => {
    if (!codes || codes.length === 0) return;
    if (!codes.includes(watchCode)) setWatchCode(codes[0]);
  }, [codes.join(",")]);

  const setTh = useCallback_sim((key, patch) => {
    setThresholds(prev => {
      const cur = prev[key] || { op: ">=", value: "" };
      const next = { ...prev, [key]: { ...cur, ...patch } };
      _saveWatchThresholds(next);
      return next;
    });
  }, []);

  const clearAll = useCallback_sim(() => {
    setThresholds({}); _saveWatchThresholds({}); prevMetRef.current = {};
  }, []);

  const arr = barsByCode[watchCode] || [];
  const bar = arr.length ? arr[arr.length - 1] : null;

  // 충족 상태 스냅샷 갱신(플래시는 prev→met 전환 시 1회).
  useEffect_sim(() => {
    const snap = {};
    _SIM_WATCH_VARS.forEach(v => {
      snap[v.key] = bar ? _evalWatch(bar[v.key], thresholds[v.key]) : null;
    });
    prevMetRef.current = snap;
  });

  const prevMet = prevMetRef.current;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          변수 워치
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {codes && codes.length > 1 && (
            <select className="select" value={watchCode} onChange={e => setWatchCode(e.target.value)}
                    style={{ fontSize: 10.5, padding: "2px 6px", height: "auto" }}>
              {codes.map(c => <option key={c} value={c}>{nameByCode[c] || c}</option>)}
            </select>
          )}
          <button className="btn ghost sm" onClick={clearAll} style={{ fontSize: 10, padding: "2px 7px" }}>
            임계 초기화
          </button>
        </div>
      </div>
      <div className="panel-bd" style={{ padding: "6px 8px" }}>
        {!bar ? (
          <div className="research-empty" style={{ fontSize: 10.5 }}>재생을 시작하면 현재 값이 표시됩니다.</div>
        ) : (
          <table className="sim-live-table" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>변수</th>
                <th>현재값</th>
                <th style={{ width: 44 }}>조건</th>
                <th style={{ width: 76 }}>임계값</th>
              </tr>
            </thead>
            <tbody>
              {_SIM_WATCH_VARS.map(v => {
                const value = bar[v.key];
                const th = thresholds[v.key] || { op: ">=", value: "" };
                const met = _evalWatch(value, th);
                const was = prevMet[v.key];
                // 미설정 → 무색. 충족 → 녹/미충족 → 적. 막 충족(was≠true & met) → 플래시.
                const rowBg = met == null ? "transparent"
                  : met ? "rgba(76,214,179,0.10)" : "rgba(255,93,108,0.10)";
                const flash = (met === true && was !== true) ? "sim-flash-up" : "";
                const valTxt = value == null ? "—" : _simFmtNum(value, v.digits);
                return (
                  <tr key={v.key} className={flash} style={{ background: rowBg }}>
                    <td style={{ textAlign: "left", color: "var(--ink-1)" }}>{v.label}</td>
                    <td className="mono" style={{
                      color: met == null ? "var(--ink-1)" : met ? "var(--teal)" : "var(--red)",
                    }}>
                      {valTxt}
                    </td>
                    <td>
                      <select value={th.op} onChange={e => setTh(v.key, { op: e.target.value })}
                              className="mono" style={{
                                fontSize: 11, padding: "1px 2px", background: "var(--bg-0)",
                                color: "var(--ink-1)", border: "1px solid var(--line-1)", borderRadius: 4,
                              }}>
                        <option value=">=">≥</option>
                        <option value="<=">≤</option>
                      </select>
                    </td>
                    <td>
                      <input type="number" value={th.value}
                             onChange={e => setTh(v.key, { value: e.target.value })}
                             placeholder="—" className="mono"
                             style={{
                               width: "100%", fontSize: 11, padding: "2px 4px", textAlign: "right",
                               background: "var(--bg-0)", color: "var(--ink-1)",
                               border: "1px solid var(--line-1)", borderRadius: 4,
                             }} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        <div style={{ fontSize: 9.5, color: "var(--ink-3)", marginTop: 6, lineHeight: 1.5 }}>
          임계는 현재 프레임 값과의 단순 비교다. 조건식 엔진 정합 매매 신호는
          위 <span style={{ color: "var(--teal)" }}>매수/매도 조건식</span> 선택 시 차트에 오버레이된다.
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { SimulationTab });
