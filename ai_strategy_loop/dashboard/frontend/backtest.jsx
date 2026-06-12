/* Backtest workbench tab — PR2 (조건식 라이브러리·에디터·실행·결과/분석).
   GUI 백테스트의 웹 이관. /bt/* REST 계약을 소비한다(backtest_api.py·backtest_analysis.py).
   디자인 언어: 다크 테마(var(--bg-1)/var(--line-1)) · mono 라벨 · panel/btn 클래스 재사용.

   모든 fetch 는 무예외(실패→빈 상태+재시도), AbortSignal.timeout, 폴링은 running 중에만.
   차트(누적수익·히스토그램·히트맵·언더워터)는 backtest-charts.jsx 의 순수 SVG 컴포넌트 사용
   (window 전역, index.html 에서 이 파일보다 먼저 로드). 외부 차트 라이브러리 금지. */
const {
  useState: useState_bt, useEffect: useEffect_bt,
  useCallback: useCallback_bt, useRef: useRef_bt, useMemo: useMemo_bt,
} = React;

// 무예외 fetch 헬퍼 — 실패 시 throw 대신 거부를 호출측 catch 로 흘린다.
//   backtest-charts.jsx 의 BtResultArea 도 _btFetchJson 을 전역으로 공유해 쓴다(호출은 렌더 시점).
function _btFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 5000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}
function _btPostJson(url, body, timeoutMs) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
    signal: AbortSignal.timeout(timeoutMs || 8000),
  }).then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

// http(s) baseUrl + 경로 → ws(s) URL. baseUrl 이 비면 현재 origin 기준.
function _btWsUrl(baseUrl, path) {
  let origin = baseUrl || (window.location ? window.location.origin : "");
  origin = origin.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");
  if (!/^wss?:/i.test(origin)) {
    const loc = window.location || {};
    const proto = (loc.protocol === "https:") ? "wss:" : "ws:";
    origin = proto + "//" + (loc.host || "");
  }
  return origin.replace(/\/$/, "") + path;
}

const _BT_JOB_BADGE = {
  pending:   { txt: "대기", cls: "badge idle" },
  running:   { txt: "실행중", cls: "badge run" },
  success:   { txt: "성공", cls: "badge done" },
  no_trades: { txt: "거래 0건", cls: "badge warn" },
  error:     { txt: "오류", cls: "badge err" },
  timeout:   { txt: "시간초과", cls: "badge err" },
  cancelled: { txt: "취소됨", cls: "badge idle" },
};

// 모드별 대형 실행 버튼 라벨.
const _BT_MODE_RUN_LABEL = {
  backtest: "백테스트 실행",
  optimize: "최적화 실행",
  wfo: "전진분석 실행",
  sweep: "스윕 실행",
};

function _btElapsed(rec) {
  const s = rec.started_at;
  if (!s) return "—";
  const end = rec.finished_at || (Date.now() / 1000);
  const sec = Math.max(0, Math.round(end - s));
  if (sec < 60) return sec + "s";
  return Math.floor(sec / 60) + "m " + (sec % 60) + "s";
}

// ===========================================================================
// 1. 조건식 라이브러리 패널 (좌) — kind 토글 + 검색 + 목록.
// ===========================================================================
function BtLibraryPanel({ baseUrl, isDemo, kind, onKind, onPick, selectedName, reloadKey, lockKind }) {
  const [items, setItems] = useState_bt([]);
  const [query, setQuery] = useState_bt("");
  const [err, setErr] = useState_bt("");
  const [loading, setLoading] = useState_bt(false);

  const load = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setItems([]); return; }
    setLoading(true); setErr("");
    _btFetchJson(baseUrl + "/bt/strategies?kind=" + encodeURIComponent(kind), 4000)
      .then(j => setItems(Array.isArray(j && j.items) ? j.items : []))
      .catch(e => { setItems([]); setErr(String(e)); })
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, kind, reloadKey]);

  useEffect_bt(() => { load(); }, [load]);

  const filtered = useMemo_bt(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(it => (it.name || "").toLowerCase().includes(q));
  }, [items, query]);

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", minHeight: 0 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          조건식 라이브러리
          {lockKind && (
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
              {kind === "buy" ? "매수" : kind === "sell" ? "매도" : "수식"}
            </span>
          )}
        </div>
        <button className="btn ghost sm" onClick={load} disabled={isDemo || loading}>
          {loading ? "로딩…" : "↻"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {/* kind 토글(잠금 시 숨김) */}
        {!lockKind && (
          <div style={{ display: "flex", gap: 4 }}>
            {[["buy", "매수"], ["sell", "매도"], ["formula", "수식"]].map(([k, lbl]) => (
              <button key={k} onClick={() => onKind(k)} className="mono"
                style={{
                  flex: 1, padding: "5px 8px", fontSize: 11, borderRadius: 5,
                  border: "1px solid " + (kind === k ? "var(--teal-dim)" : "var(--line-1)"),
                  background: kind === k ? "rgba(76,214,179,0.08)" : "transparent",
                  color: kind === k ? "var(--teal)" : "var(--ink-2)", cursor: "pointer",
                }}>
                {lbl}
              </button>
            ))}
          </div>
        )}
        {/* 검색 */}
        <input className="input" placeholder="이름 검색…" value={query}
               onChange={e => setQuery(e.target.value)} spellCheck={false} />
        {/* 목록 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 3, maxHeight: 420, overflowY: "auto" }}>
          {isDemo ? (
            <div className="research-empty">데모 모드 — 백엔드 연결 시 조건식 목록이 표시됩니다.</div>
          ) : err ? (
            <div className="research-empty" style={{ color: "var(--red)" }}>
              조회 실패: {err}
              <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={load}>재시도</button></div>
            </div>
          ) : filtered.length === 0 ? (
            <div className="research-empty">{query ? "검색 결과 없음" : "조건식이 없습니다"}</div>
          ) : filtered.map(it => {
            const active = it.name === selectedName;
            return (
              <button key={it.name} onClick={() => onPick(it.name)}
                style={{
                  textAlign: "left", padding: "7px 9px", borderRadius: 5, cursor: "pointer",
                  border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
                  background: active ? "rgba(76,214,179,0.07)" : "var(--bg-0)",
                  display: "flex", flexDirection: "column", gap: 3,
                }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <span className="mono" style={{ fontSize: 11.5, color: active ? "var(--teal)" : "var(--ink-0)", wordBreak: "break-all" }}>
                    {it.name}
                  </span>
                  {it.is_ailoop && <span className="tag-slim" style={{ color: "var(--violet)" }}>AILOOP</span>}
                </div>
                {it.preview && (
                  <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {it.preview}
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
          {filtered.length}개 표시 / 전체 {items.length}개
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// 2b. 변수 키워드 칩 — 코드에서 한글 변수 추출 후 SSOT 대조(POST /bt/extract_vars).
//   known(청록): SSOT 화이트리스트에 있는 변수. unknown(경고): 어휘 밖(오타/미지).
// ===========================================================================
function BtVarChips({ baseUrl, isDemo, code }) {
  const [known, setKnown] = useState_bt([]);
  const [unknown, setUnknown] = useState_bt([]);

  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setKnown([]); setUnknown([]); return; }
    const trimmed = (code || "").trim();
    if (!trimmed) { setKnown([]); setUnknown([]); return; }
    let cancelled = false;
    // 입력 디바운스(타이핑 중 과호출 방지).
    const t = setTimeout(() => {
      _btPostJson(baseUrl + "/bt/extract_vars", { code: trimmed }, 5000)
        .then(j => {
          if (cancelled) return;
          setKnown(Array.isArray(j && j.known) ? j.known : []);
          setUnknown(Array.isArray(j && j.unknown) ? j.unknown : []);
        })
        .catch(() => { if (!cancelled) { setKnown([]); setUnknown([]); } });
    }, 400);
    return () => { cancelled = true; clearTimeout(t); };
  }, [baseUrl, isDemo, code]);

  if (known.length === 0 && unknown.length === 0) {
    return (
      <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
        사용 변수 칩 — 코드 입력 시 한글 변수가 SSOT 대조되어 표시됩니다.
      </div>
    );
  }
  const chip = (v, ok) => (
    <span key={(ok ? "k:" : "u:") + v.name} className="mono"
      title={ok ? "SSOT 화이트리스트 변수" : "SSOT 어휘 밖 — 오타이거나 정의되지 않은 변수일 수 있습니다"}
      style={{
        fontSize: 10, padding: "2px 6px", borderRadius: 4,
        border: "1px solid " + (ok ? "var(--teal-dim)" : "rgba(240,179,90,0.45)"),
        color: ok ? "var(--teal)" : "var(--amber)",
        background: ok ? "rgba(76,214,179,0.06)" : "rgba(240,179,90,0.06)",
        display: "inline-flex", alignItems: "center", gap: 4,
      }}>
      {ok ? "" : "⚠ "}{v.name}
      {v.count > 1 && <span style={{ color: "var(--ink-3)" }}>×{v.count}</span>}
    </span>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
        {known.map(v => chip(v, true))}
        {unknown.map(v => chip(v, false))}
      </div>
      <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
        SSOT 변수 {known.length} · 미확인 {unknown.length}
      </div>
    </div>
  );
}

// ===========================================================================
// 2c. 단일 코드 에디터(매수/매도 한 쪽) — 로드/검증/저장/변수칩. 듀얼 에디터의 한 패널.
// ===========================================================================
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
      if (!name) { setCode(""); setEditName(""); setLoadedName(""); setValidate(null); setMsg(null); }
      return;
    }
    _btFetchJson(baseUrl + "/bt/strategy?kind=" + encodeURIComponent(kind) + "&name=" + encodeURIComponent(name), 4000)
      .then(j => {
        if (j && j.available) { setCode(j.code || ""); setEditName(j.name || name); setLoadedName(j.name || name); }
        else { setCode(""); setEditName(name); setLoadedName(""); }
        setValidate(null); setMsg(null);
      })
      .catch(() => setMsg({ kind: "error", text: "조건식 로드 실패" }));
  }, [baseUrl, isDemo, kind, name]);

  const lineCount = useMemo_bt(() => code.split("\n").length, [code]);

  const runValidate = () => {
    if (isDemo) return;
    setBusy("validate"); setMsg(null);
    _btPostJson(baseUrl + "/bt/strategy/validate", { code }, 6000)
      .then(j => setValidate(j || { ok: false, error: "응답 없음" }))
      .catch(e => setValidate({ ok: false, error: String(e) }))
      .finally(() => setBusy(""));
  };

  const doSave = (asNew) => {
    if (isDemo) return;
    const targetName = (editName || "").trim();
    if (!targetName) { setMsg({ kind: "error", text: "이름을 입력하세요." }); return; }
    const overwrite = !asNew && targetName === loadedName;
    setBusy("save"); setMsg(null);
    _btPostJson(baseUrl + "/bt/strategy", { kind, name: targetName, code, overwrite }, 8000)
      .then(j => {
        if (j && j.status === "ok") {
          setLoadedName(targetName);
          setMsg({ kind: "ok", text: `저장 완료: ${targetName}` });
          onSaved && onSaved(targetName);
        } else if (j && j.code === "exists") {
          setMsg({ kind: "error", text: `'${targetName}' 이미 존재 — '덮어쓰기'를 누르세요.` });
        } else {
          setMsg({ kind: "error", text: (j && j.message) || "저장 실패" });
        }
      })
      .catch(e => setMsg({ kind: "error", text: "저장 실패: " + e }))
      .finally(() => setBusy(""));
  };

  const doDelete = () => {
    if (isDemo || !loadedName) return;
    setBusy("delete"); setMsg(null);
    _btPostJson(baseUrl + "/bt/strategy/delete", { kind, name: loadedName, confirm: confirmDel }, 8000)
      .then(j => {
        if (j && j.status === "ok") {
          const deleted = loadedName;
          setCode(""); setEditName(""); setLoadedName(""); setConfirmDel("");
          setMsg({ kind: "ok", text: `삭제 완료: ${deleted}` });
          onDeleted && onDeleted(deleted);
        } else {
          setMsg({ kind: "error", text: (j && j.message) || "삭제 실패" });
        }
      })
      .catch(e => setMsg({ kind: "error", text: "삭제 실패: " + e }))
      .finally(() => setBusy(""));
  };

  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", minWidth: 0, flex: 1 }}>
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: accent }}></span>
          {label} 에디터
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>{lineCount}줄</span>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <input className="input" value={editName} onChange={e => setEditName(e.target.value)}
               placeholder={label + " 조건식 이름"} spellCheck={false} disabled={isDemo} />
        <textarea className="input mono" value={code}
          onChange={e => { setCode(e.target.value); setValidate(null); }}
          spellCheck={false} disabled={isDemo}
          style={{ minHeight: 200, resize: "vertical", lineHeight: 1.5, whiteSpace: "pre", tabSize: 4, fontSize: 12 }}
          placeholder={"# " + label + " 전략 코드 (Python)"} />
        <BtVarChips baseUrl={baseUrl} isDemo={isDemo} code={code} />
        {validate && (
          <div style={{
            padding: "6px 9px", borderRadius: 5, fontSize: 11, fontFamily: "var(--mono)",
            border: "1px solid " + (validate.ok ? "rgba(76,214,179,0.3)" : "rgba(255,107,107,0.3)"),
            background: validate.ok ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)",
            color: validate.ok ? "var(--teal)" : "var(--red)",
          }}>
            {validate.ok ? "✓ 문법 검증 통과" : "✗ " + (validate.error || "검증 실패")}
          </div>
        )}
        {msg && (
          <div style={{
            padding: "6px 9px", borderRadius: 5, fontSize: 11, fontFamily: "var(--mono)",
            border: "1px solid " + (msg.kind === "ok" ? "rgba(76,214,179,0.3)" : "rgba(255,107,107,0.3)"),
            background: msg.kind === "ok" ? "rgba(76,214,179,0.06)" : "rgba(255,107,107,0.06)",
            color: msg.kind === "ok" ? "var(--teal)" : "var(--red)",
          }}>
            {msg.text}
          </div>
        )}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          <button className="btn ghost sm" onClick={runValidate} disabled={isDemo || busy === "validate"}>
            {busy === "validate" ? "검증중…" : "검증"}
          </button>
          <button className="btn primary sm" onClick={() => doSave(false)} disabled={isDemo || busy === "save"}>
            {busy === "save" ? "저장중…" : (editName.trim() === loadedName && loadedName ? "덮어쓰기" : "저장")}
          </button>
          <button className="btn sm" onClick={() => doSave(true)} disabled={isDemo || busy === "save"}>
            다른 이름으로
          </button>
        </div>
        {/* 삭제(이름 재입력 confirm) */}
        {loadedName && (
          <div style={{ borderTop: "1px solid var(--line-1)", paddingTop: 8, display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
            <input className="input" style={{ flex: 1, minWidth: 100, fontSize: 11 }} value={confirmDel}
                   onChange={e => setConfirmDel(e.target.value)} placeholder={"삭제하려면 '" + loadedName + "' 재입력"}
                   spellCheck={false} disabled={isDemo} />
            <button className="btn danger sm" onClick={doDelete}
                    disabled={isDemo || busy === "delete" || confirmDel !== loadedName}>
              {busy === "delete" ? "삭제중…" : "삭제"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 2d. 매수+매도 듀얼 에디터 — 두 코드 에디터를 나란히 표시(한 화면 동시 편집).
//   각 패널은 독립 라이브러리 선택(buyName/sellName)에서 코드를 로드한다.
// ===========================================================================
function BtDualEditor({ baseUrl, isDemo, buyName, sellName, onSaved, onDeletedBuy, onDeletedSell }) {
  return (
    <div style={{ display: "flex", gap: 12, minWidth: 0, flexWrap: "wrap" }}>
      <BtCodeEditor baseUrl={baseUrl} isDemo={isDemo} kind="buy" label="매수" accent="var(--teal)"
                    name={buyName} onSaved={onSaved} onDeleted={onDeletedBuy} />
      <BtCodeEditor baseUrl={baseUrl} isDemo={isDemo} kind="sell" label="매도" accent="var(--red)"
                    name={sellName} onSaved={onSaved} onDeleted={onDeletedSell} />
    </div>
  );
}

// ===========================================================================
// 3. 백테스트 실행 패널 — buy/sell 선택, 기간/tf/engines, 잡 카드 + 이력 + 폴링.
// ===========================================================================
function BtRunPanel({ baseUrl, isDemo, libNames, onResult, compareA, onCompareB, onJobs,
                      buy, sell, onBuy, onSell, reloadJobsKey }) {
  const [start, setStart] = useState_bt("");
  const [end, setEnd] = useState_bt("");
  const [timeframe, setTimeframe] = useState_bt("min");
  const [engines, setEngines] = useState_bt(4);
  const [mode, setMode] = useState_bt("backtest");      // backtest | optimize | wfo | sweep.
  const [paramSpace, setParamSpace] = useState_bt("");  // optimize/wfo 탐색공간 JSON 경로.
  // wfo(전진분석) 입력.
  const [trainWindow, setTrainWindow] = useState_bt("");
  const [testWindow, setTestWindow] = useState_bt("");
  const [stepDays, setStepDays] = useState_bt("");       // wfo/sweep rolling 공용.
  // sweep 입력.
  const [sweepAction, setSweepAction] = useState_bt("param");  // param | rolling.
  const [sweepParams, setSweepParams] = useState_bt("");       // sweep param 조합 JSON 경로.
  const [windowDays, setWindowDays] = useState_bt("");         // sweep rolling 윈도우 크기.
  const [range, setRange] = useState_bt(null);          // /bt/data_range
  const [jobs, setJobs] = useState_bt([]);              // 이력
  const [activeJob, setActiveJob] = useState_bt(null);  // 현재 추적 job record
  const [runErr, setRunErr] = useState_bt("");
  const [showLog, setShowLog] = useState_bt(false);
  const [selectedJobId, setSelectedJobId] = useState_bt("");

  // 데이터 가용 범위 로드.
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setRange(null); return; }
    _btFetchJson(baseUrl + "/bt/data_range", 5000).then(setRange).catch(() => setRange(null));
  }, [baseUrl, isDemo]);

  // 잡 이력 로드(결과 라이브러리가 검색/필터하므로 전체를 끌어온다).
  const loadJobs = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setJobs([]); return; }
    _btFetchJson(baseUrl + "/bt/jobs", 4000)
      .then(j => setJobs(Array.isArray(j && j.jobs) ? j.jobs : []))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  useEffect_bt(() => { loadJobs(); }, [loadJobs, reloadJobsKey]);

  // 잡 목록이 바뀌면 부모로 끌어올린다(포트폴리오 패널이 완료 잡을 소비).
  useEffect_bt(() => { onJobs && onJobs(jobs); }, [jobs, onJobs]);

  // 추적 대상 job_id(WS/폴링 공용). 활성 잡이 running/pending 이면 그 id.
  const trackId = activeJob && (activeJob.status === "running" || activeJob.status === "pending")
    ? activeJob.job_id : null;
  // WS 연결 성공 여부 ref — 성공 시 폴링을 끈다(폴백 전용).
  const wsOkRef = useRef_bt(false);

  // 라이브 잡 WebSocket — running/pending 일 때 구독. 실패 시 폴링 폴백(무예외).
  useEffect_bt(() => {
    wsOkRef.current = false;
    if (isDemo || !baseUrl || !trackId) return;
    let ws = null;
    let closedByUs = false;
    try {
      const wsUrl = _btWsUrl(baseUrl, "/bt/ws_job?job_id=" + encodeURIComponent(trackId));
      ws = new WebSocket(wsUrl);
    } catch (e) { return; }
    ws.onopen = () => { wsOkRef.current = true; };
    ws.onmessage = (ev) => {
      let m = null;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (!m || m.error) { return; }
      wsOkRef.current = true;
      // WS 페이로드를 activeJob 형태로 머지(job 카드가 기대하는 필드 유지).
      setActiveJob(prev => Object.assign({}, prev, {
        job_id: m.job_id, status: m.status, progress: m.progress,
        phase: m.phase, message: m.message, log_tail: m.log_tail || (prev && prev.log_tail) || [],
      }));
      if (m.terminal) { loadJobs(); }
    };
    ws.onerror = () => { wsOkRef.current = false; };
    ws.onclose = () => { if (!closedByUs) { /* 폴링 폴백이 이어받음 */ } };
    return () => { closedByUs = true; try { ws && ws.close(); } catch (e) {} };
  }, [baseUrl, isDemo, trackId, loadJobs]);

  // 폴링 폴백 — WS 미연결일 때만 2초 간격(WS 성공 시 즉시 중단).
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !trackId) return;
    const id = setInterval(() => {
      if (wsOkRef.current) return;   // WS 가 살아있으면 폴링은 쉰다(폴백 전용).
      _btFetchJson(baseUrl + "/bt/job?job_id=" + encodeURIComponent(trackId), 4000)
        .then(j => {
          if (j && j.available) {
            setActiveJob(j);
            if (j.status !== "running" && j.status !== "pending") { loadJobs(); }
          }
        })
        .catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [baseUrl, isDemo, trackId, loadJobs]);

  // B2 — 잡이 성공으로 종결되면 결과를 자동 선택(부모가 결과 분석 탭으로 전환).
  //   같은 잡을 두 번 자동선택하지 않도록 마지막 자동선택 id 를 기억한다.
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
      buy: (buy || "").trim(), sell: (sell || "").trim(),
      start: parseInt(start, 10) || 0, end: parseInt(end, 10) || 0,
      timeframe, engines: parseInt(engines, 10) || 4,
      mode,
    };
    if (!payload.buy || !payload.sell) { setRunErr("매수/매도 조건식을 선택하세요."); return; }
    if (!/^\d{8}$/.test(String(start)) || !/^\d{8}$/.test(String(end))) {
      setRunErr("기간은 YYYYMMDD 8자리로 입력하세요."); return;
    }
    if (mode === "optimize") {
      const ps = (paramSpace || "").trim();
      if (!ps) { setRunErr("최적화 모드는 파라미터 탐색공간 JSON 경로가 필요합니다."); return; }
      payload.param_space = ps;
    } else if (mode === "wfo") {
      const tr = parseInt(trainWindow, 10) || 0;
      const te = parseInt(testWindow, 10) || 0;
      if (tr < 1 || te < 1) { setRunErr("전진분석은 훈련·테스트 윈도우(일, 1 이상)가 필요합니다."); return; }
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
        if (wd < 1 || sd < 1) { setRunErr("롤링 스윕은 윈도우·이동(일, 1 이상)이 필요합니다."); return; }
        payload.window_days = wd;
        payload.step_days = sd;
      } else {
        const sp = (sweepParams || "").trim();
        if (!sp) { setRunErr("파라미터 스윕은 조합 JSON 경로가 필요합니다."); return; }
        payload.sweep_params = sp;
      }
    }
    _btPostJson(baseUrl + "/bt/run", payload, 8000)
      .then(j => {
        if (j && j.status === "ok" && j.job_id) {
          setActiveJob({ job_id: j.job_id, status: "pending", progress: 0, spec: payload, log_tail: [] });
          setSelectedJobId(j.job_id);
          loadJobs();
        } else {
          setRunErr((j && j.message) || "실행 실패");
        }
      })
      .catch(e => setRunErr("실행 실패: " + e));
  };

  const cancelJob = (jobId) => {
    if (isDemo || !jobId) return;
    _btPostJson(baseUrl + "/bt/job/cancel", { job_id: jobId }, 5000)
      .then(() => {
        _btFetchJson(baseUrl + "/bt/job?job_id=" + encodeURIComponent(jobId), 4000)
          .then(j => { if (j && j.available) setActiveJob(j); loadJobs(); })
          .catch(() => {});
      })
      .catch(() => {});
  };

  // 잡 이력 클릭 → 결과 로드(부모로 위임).
  const pickJob = (jobId) => {
    setSelectedJobId(jobId);
    onResult && onResult(jobId);
  };

  // 자급자족 HTML 리포트를 새 탭으로 연다(외부 리소스 0 — /bt/report 가 완성 HTML 반환).
  const openReport = (jobId) => {
    if (isDemo || !baseUrl || !jobId) return;
    const url = baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId);
    try { window.open(url, "_blank", "noopener"); } catch (e) {}
  };

  const pct = activeJob ? Math.round((activeJob.progress || 0) * 100) : 0;
  const tracking = activeJob && (activeJob.status === "running" || activeJob.status === "pending");

  return (
    <div className="panel" style={{ background: "var(--bg-1)" }}>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {/* 전폭 실행 컨트롤 바 — 모드 토글 · 매수/매도 · 기간 · tf/engines · 대형 실행 버튼 */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
          {/* 모드 토글 [백테스트|최적화|WFO|스윕] */}
          <div className="field" style={{ minWidth: 240 }}>
            <label>모드</label>
            <div style={{ display: "flex", gap: 4 }}>
              {[["backtest", "백테스트"], ["optimize", "최적화"], ["wfo", "WFO"], ["sweep", "스윕"]].map(([m, lbl]) => (
                <button key={m} onClick={() => setMode(m)} className="mono" disabled={isDemo}
                  style={{
                    flex: 1, padding: "6px 8px", fontSize: 11, borderRadius: 5,
                    border: "1px solid " + (mode === m ? "var(--amber)" : "var(--line-1)"),
                    background: mode === m ? "rgba(240,179,90,0.1)" : "transparent",
                    color: mode === m ? "var(--amber)" : "var(--ink-2)", cursor: "pointer",
                  }}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>매수 조건식</label>
            <select className="select" value={buy} onChange={e => onBuy(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {libNames.buy.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>매도 조건식</label>
            <select className="select" value={sell} onChange={e => onSell(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {libNames.sell.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 110 }}>
            <label>시작 (YYYYMMDD)</label>
            <input className="input" value={start} onChange={e => setStart(e.target.value)}
                   placeholder="20250101" spellCheck={false} disabled={isDemo} />
          </div>
          <div className="field" style={{ minWidth: 110 }}>
            <label>종료 (YYYYMMDD)</label>
            <input className="input" value={end} onChange={e => setEnd(e.target.value)}
                   placeholder="20251231" spellCheck={false} disabled={isDemo} />
          </div>
          <div className="field" style={{ minWidth: 100 }}>
            <label>시간단위</label>
            <select className="select" value={timeframe} onChange={e => setTimeframe(e.target.value)} disabled={isDemo}>
              <option value="min">분봉 (min)</option>
              <option value="tick">틱 (tick)</option>
            </select>
          </div>
          <div className="field" style={{ minWidth: 76 }}>
            <label>엔진 수</label>
            <input className="input" type="number" min="1" max="16" value={engines}
                   onChange={e => setEngines(e.target.value)} disabled={isDemo} />
          </div>
          {/* 대형 실행 버튼 — 폴드 위 가시성 핵심 */}
          <button className="btn primary" onClick={submit}
                  disabled={isDemo || tracking}
                  style={{ fontSize: 14, padding: "10px 22px", minWidth: 120 }}>
            ▸ {_BT_MODE_RUN_LABEL[mode] || "백테스트 실행"}
          </button>
          <button className="btn ghost sm" onClick={loadJobs} disabled={isDemo}>↻ 이력</button>
        </div>

        {/* optimize 전용 — 파라미터 탐색공간 JSON 경로 */}
        {mode === "optimize" && (
          <div className="field">
            <label>파라미터 탐색공간 JSON 경로 (_database/ 또는 ai_strategy_loop/state/ 하위)</label>
            <input className="input mono" value={paramSpace} onChange={e => setParamSpace(e.target.value)}
                   placeholder="_database/param_space.json" spellCheck={false} disabled={isDemo}
                   style={{ fontSize: 11 }} />
          </div>
        )}

        {/* wfo 전용 — 전진분석 윈도우 입력(훈련/테스트/이동일, 선택 탐색공간 JSON) */}
        {mode === "wfo" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
            <div className="field" style={{ minWidth: 120 }}>
              <label>훈련 윈도우 (일)</label>
              <input className="input" type="number" min="1" value={trainWindow}
                     onChange={e => setTrainWindow(e.target.value)} placeholder="60" disabled={isDemo} />
            </div>
            <div className="field" style={{ minWidth: 120 }}>
              <label>테스트 윈도우 (일)</label>
              <input className="input" type="number" min="1" value={testWindow}
                     onChange={e => setTestWindow(e.target.value)} placeholder="20" disabled={isDemo} />
            </div>
            <div className="field" style={{ minWidth: 120 }}>
              <label>이동 간격 (일, 선택)</label>
              <input className="input" type="number" min="1" value={stepDays}
                     onChange={e => setStepDays(e.target.value)} placeholder="테스트 윈도우" disabled={isDemo} />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 200 }}>
              <label>탐색공간 JSON 경로 (선택 — 미지정 시 고정 파라미터)</label>
              <input className="input mono" value={paramSpace} onChange={e => setParamSpace(e.target.value)}
                     placeholder="_database/param_space.json" spellCheck={false} disabled={isDemo}
                     style={{ fontSize: 11 }} />
            </div>
          </div>
        )}

        {/* sweep 전용 — 하위 동작 토글(param|rolling) + 동작별 입력 */}
        {mode === "sweep" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
            <div className="field" style={{ minWidth: 160 }}>
              <label>스윕 종류</label>
              <div style={{ display: "flex", gap: 4 }}>
                {[["param", "파라미터"], ["rolling", "날짜 롤링"]].map(([a, lbl]) => (
                  <button key={a} onClick={() => setSweepAction(a)} className="mono" disabled={isDemo}
                    style={{
                      flex: 1, padding: "6px 8px", fontSize: 11, borderRadius: 5,
                      border: "1px solid " + (sweepAction === a ? "var(--amber)" : "var(--line-1)"),
                      background: sweepAction === a ? "rgba(240,179,90,0.1)" : "transparent",
                      color: sweepAction === a ? "var(--amber)" : "var(--ink-2)", cursor: "pointer",
                    }}>
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            {sweepAction === "param" ? (
              <div className="field" style={{ flex: 1, minWidth: 220 }}>
                <label>스윕 조합 JSON 경로 (_database/ 또는 ai_strategy_loop/state/ 하위)</label>
                <input className="input mono" value={sweepParams} onChange={e => setSweepParams(e.target.value)}
                       placeholder="_database/sweep_params.json" spellCheck={false} disabled={isDemo}
                       style={{ fontSize: 11 }} />
              </div>
            ) : (
              <>
                <div className="field" style={{ minWidth: 120 }}>
                  <label>윈도우 (일)</label>
                  <input className="input" type="number" min="1" value={windowDays}
                         onChange={e => setWindowDays(e.target.value)} placeholder="20" disabled={isDemo} />
                </div>
                <div className="field" style={{ minWidth: 120 }}>
                  <label>이동 간격 (일)</label>
                  <input className="input" type="number" min="1" value={stepDays}
                         onChange={e => setStepDays(e.target.value)} placeholder="5" disabled={isDemo} />
                </div>
              </>
            )}
          </div>
        )}

        {/* 가용 범위 안내 + 실행 오류 */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          {tfRange && (
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
              가용 {timeframe}: 일일DB {tfRange.count}일
              {tfRange.back_range ? ` · back ${tfRange.back_range.start}~${tfRange.back_range.end}` : ""}
            </span>
          )}
          {runErr && <span className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{runErr}</span>}
          {compareA && (
            <span className="mono tag-slim" style={{ fontSize: 9.5, color: "var(--amber)", marginLeft: "auto" }}
                  title="비교 기준(A) 고정됨 — 결과 라이브러리에서 다른 잡의 '비교(B)' 를 누르세요">
              비교 A={compareA}
            </span>
          )}
        </div>

        {/* 활성 잡 카드 */}
        {activeJob && (
          <div style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 10, background: "var(--bg-0)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span className={(_BT_JOB_BADGE[activeJob.status] || _BT_JOB_BADGE.pending).cls}>
                <span className={"dot " + (activeJob.status === "running" ? "pulse-dot" : "")}></span>
                {(_BT_JOB_BADGE[activeJob.status] || _BT_JOB_BADGE.pending).txt}
              </span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{activeJob.job_id}</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", marginLeft: "auto" }}>
                {_btElapsed(activeJob)}
              </span>
            </div>
            <div className="progress-track">
              <div className={"progress-fill " + (activeJob.status === "running" ? "running" : "")} style={{ width: pct + "%" }}></div>
            </div>
            {activeJob.message && (
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{activeJob.message}</div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {tracking && (
                <button className="btn danger sm" onClick={() => cancelJob(activeJob.job_id)}>◼ 중지</button>
              )}
              {(activeJob.status === "success" || activeJob.status === "no_trades") && (
                <button className="btn ghost sm" onClick={() => pickJob(activeJob.job_id)}>결과 보기</button>
              )}
              {(activeJob.status === "success" || activeJob.status === "no_trades") && (
                <button className="btn ghost sm" onClick={() => openReport(activeJob.job_id)}
                        title="자급자족 HTML 리포트를 새 탭으로 열기">📄 리포트</button>
              )}
              {(activeJob.log_tail && activeJob.log_tail.length > 0) && (
                <button className="btn ghost sm" onClick={() => setShowLog(s => !s)}>
                  {showLog ? "로그 접기" : "로그 보기"}
                </button>
              )}
            </div>
            {showLog && activeJob.log_tail && activeJob.log_tail.length > 0 && (
              <pre className="process-log-pane" style={{ margin: 0 }}>
                {activeJob.log_tail.join("\n")}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3b. 결과 라이브러리 — 잡 이력 + 태그·메모·즐겨찾기·검색·필터(결과 체계 관리).
//   완료 잡을 클릭하면 결과를 로드(onResult). 메타는 POST /bt/job/meta 로 영속.
// ===========================================================================
function BtResultLibrary({ baseUrl, isDemo, jobs, onResult, selectedJobId, onReload,
                           compareA, onSetCompareA, onCompareB }) {
  const [query, setQuery] = useState_bt("");
  const [favOnly, setFavOnly] = useState_bt(false);
  const [tagFilter, setTagFilter] = useState_bt("");
  const [editing, setEditing] = useState_bt("");      // 메타 편집 중인 job_id.
  const [tagDraft, setTagDraft] = useState_bt("");
  const [memoDraft, setMemoDraft] = useState_bt("");

  const openReport = (jobId) => {
    if (isDemo || !baseUrl || !jobId) return;
    try { window.open(baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId), "_blank", "noopener"); } catch (e) {}
  };

  const saveMeta = (jobId, patch) => {
    if (isDemo || !baseUrl || !jobId) return;
    _btPostJson(baseUrl + "/bt/job/meta", Object.assign({ job_id: jobId }, patch), 6000)
      .then(() => { onReload && onReload(); })
      .catch(() => {});
  };

  const toggleFav = (j) => saveMeta(j.job_id, { favorite: !j.favorite });

  const beginEdit = (j) => {
    setEditing(j.job_id);
    setTagDraft((j.tags || []).join(", "));
    setMemoDraft(j.memo || "");
  };
  const commitEdit = (jobId) => {
    const tags = tagDraft.split(",").map(s => s.trim()).filter(Boolean);
    saveMeta(jobId, { tags, memo: memoDraft });
    setEditing("");
  };

  // 전체 태그 어휘(필터 셀렉터용).
  const allTags = useMemo_bt(() => {
    const s = new Set();
    (jobs || []).forEach(j => (j.tags || []).forEach(t => s.add(t)));
    return Array.from(s).sort();
  }, [jobs]);

  const filtered = useMemo_bt(() => {
    const q = query.trim().toLowerCase();
    let out = (jobs || []);
    if (favOnly) out = out.filter(j => j.favorite);
    if (tagFilter) out = out.filter(j => (j.tags || []).includes(tagFilter));
    if (q) out = out.filter(j => {
      const hay = (j.job_id + " " + (j.memo || "") + " " + (j.tags || []).join(" ")
        + " " + ((j.spec && (j.spec.buy + " " + j.spec.sell)) || "")).toLowerCase();
      return hay.includes(q);
    });
    // 즐겨찾기 우선 정렬(이후 원래 최신순 유지).
    return out.slice().sort((a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0));
  }, [jobs, query, favOnly, tagFilter]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          결과 라이브러리
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
            {filtered.length}/{(jobs || []).length}
          </span>
        </div>
        <button className="btn ghost sm" onClick={onReload} disabled={isDemo}>↻</button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 결과 이력이 표시됩니다.</div>
        ) : (
          <>
            {/* 검색·필터 */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <input className="input" placeholder="잡/메모/태그/전략 검색…" value={query}
                     onChange={e => setQuery(e.target.value)} spellCheck={false}
                     style={{ flex: 1, minWidth: 140 }} />
              <button className="mono" onClick={() => setFavOnly(f => !f)}
                style={{
                  padding: "5px 9px", fontSize: 11, borderRadius: 5, cursor: "pointer",
                  border: "1px solid " + (favOnly ? "var(--amber)" : "var(--line-1)"),
                  background: favOnly ? "rgba(240,179,90,0.1)" : "transparent",
                  color: favOnly ? "var(--amber)" : "var(--ink-2)",
                }}>
                ★ 즐겨찾기
              </button>
              {allTags.length > 0 && (
                <select className="select" value={tagFilter} onChange={e => setTagFilter(e.target.value)}
                        style={{ maxWidth: 140 }}>
                  <option value="">전체 태그</option>
                  {allTags.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              )}
            </div>
            {/* 목록 */}
            {filtered.length === 0 ? (
              <div className="research-empty">{(jobs || []).length === 0 ? "실행 이력이 없습니다" : "조건에 맞는 결과 없음"}</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 360, overflowY: "auto" }}>
                {filtered.map(j => {
                  const b = _BT_JOB_BADGE[j.status] || _BT_JOB_BADGE.pending;
                  const clickable = j.status === "success" || j.status === "no_trades";
                  const active = j.job_id === selectedJobId;
                  const canCompare = clickable && compareA && onCompareB && j.job_id !== compareA;
                  const isEditing = editing === j.job_id;
                  return (
                    <div key={j.job_id}
                      style={{
                        display: "flex", flexDirection: "column", gap: 5, padding: "7px 9px", borderRadius: 5,
                        border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
                        background: active ? "rgba(76,214,179,0.06)" : "var(--bg-0)",
                        opacity: clickable ? 1 : 0.7,
                      }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <button onClick={() => toggleFav(j)} title="즐겨찾기 토글"
                          style={{ background: "transparent", border: 0, cursor: "pointer", fontSize: 13, padding: 0,
                                   color: j.favorite ? "var(--amber)" : "var(--ink-3)" }}>
                          {j.favorite ? "★" : "☆"}
                        </button>
                        <button onClick={() => clickable && onResult(j.job_id)} disabled={!clickable}
                          style={{
                            display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0,
                            background: "transparent", border: 0, padding: 0, textAlign: "left",
                            cursor: clickable ? "pointer" : "default",
                          }}>
                          <span className={b.cls} style={{ flexShrink: 0 }}>{b.txt}</span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
                            {j.job_id}
                          </span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>{_btElapsed(j)}</span>
                        </button>
                        {clickable && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => openReport(j.job_id)} title="HTML 리포트 새 탭">📄</button>
                        )}
                        {clickable && onSetCompareA && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => onSetCompareA(j.job_id)} title="비교 기준(A) 으로 고정">A</button>
                        )}
                        {canCompare && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => onCompareB(j.job_id)} title={"A(" + compareA + ") 와 비교"}>B</button>
                        )}
                        <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                onClick={() => (isEditing ? setEditing("") : beginEdit(j))} title="태그·메모 편집">🏷</button>
                      </div>
                      {/* 태그·메모 표시 */}
                      {!isEditing && ((j.tags && j.tags.length > 0) || j.memo) && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
                          {(j.tags || []).map(t => (
                            <span key={t} className="tag-slim" style={{ fontSize: 9.5, color: "var(--teal)" }}>{t}</span>
                          ))}
                          {j.memo && <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>· {j.memo}</span>}
                        </div>
                      )}
                      {/* 태그·메모 편집 */}
                      {isEditing && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                          <input className="input" value={tagDraft} onChange={e => setTagDraft(e.target.value)}
                                 placeholder="태그(쉼표 구분)" spellCheck={false} style={{ fontSize: 11 }} />
                          <input className="input" value={memoDraft} onChange={e => setMemoDraft(e.target.value)}
                                 placeholder="메모" spellCheck={false} style={{ fontSize: 11 }} />
                          <div style={{ display: "flex", gap: 6 }}>
                            <button className="btn primary sm" onClick={() => commitEdit(j.job_id)}>저장</button>
                            <button className="btn ghost sm" onClick={() => setEditing("")}>취소</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3b-2. 모드별 결과 표(WFO·스윕) — /bt/result 의 mode_result 를 정렬 가능 표로.
//   wfo: 윈도우(라운드)별 train/test 기간·메트릭. sweep: 조합/윈도우별 결과.
//   csv 단일 분석(BtResultArea)과 별개 — wfo/sweep 잡 선택 시 이 표가 뜬다.
// ===========================================================================
function _btNum(v, digits) {
  const n = Number(v);
  if (v == null || isNaN(n)) return "—";
  return n.toFixed(digits == null ? 2 : digits);
}

// wfo rounds → 정렬 가능 행. 각 round: {window:{round,train_*,test_*}, best_params, test_result:{metrics}}.
function BtWfoTable({ result }) {
  const [sortKey, setSortKey] = useState_bt("round");
  const [sortAsc, setSortAsc] = useState_bt(true);
  const rounds = (result && result.rounds) || [];
  const summary = (result && result.summary) || {};
  const rows = useMemo_bt(() => rounds.map((r, i) => {
    const w = r.window || {};
    const tr = (r.test_result && r.test_result.metrics) || {};
    return {
      round: w.round != null ? w.round : (i + 1),
      train: (w.train_start != null ? w.train_start : "—") + "~" + (w.train_end != null ? w.train_end : "—"),
      test: (w.test_start != null ? w.test_start : "—") + "~" + (w.test_end != null ? w.test_end : "—"),
      status: (r.test_result && r.test_result.status) || "—",
      trade_count: tr.trade_count,
      total_profit_pct: tr.total_profit_pct,
      max_drawdown_pct: tr.max_drawdown_pct,
    };
  }), [rounds]);
  const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    const na = Number(va), nb = Number(vb);
    const cmp = (!isNaN(na) && !isNaN(nb)) ? (na - nb) : String(va).localeCompare(String(vb));
    return sortAsc ? cmp : -cmp;
  }), [rows, sortKey, sortAsc]);
  const setSort = (k) => { if (k === sortKey) setSortAsc(a => !a); else { setSortKey(k); setSortAsc(true); } };
  const cols = [
    ["round", "라운드"], ["train", "훈련기간"], ["test", "테스트기간"], ["status", "상태"],
    ["trade_count", "거래수"], ["total_profit_pct", "수익%"], ["max_drawdown_pct", "MDD%"],
  ];
  if (rounds.length === 0) return <div className="research-empty">WFO 라운드 결과가 없습니다.</div>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", display: "flex", gap: 14, flexWrap: "wrap" }}>
        <span>라운드 {summary.round_count != null ? summary.round_count : rounds.length}</span>
        <span>성공률 {summary.success_rate != null ? (summary.success_rate * 100).toFixed(0) + "%" : "—"}</span>
        <span>평균 OOS {summary.metric || "tpi"} {_btNum(summary.mean_oos_metric)}</span>
        <span>무거래 라운드 {summary.zero_trade_rounds != null ? summary.zero_trade_rounds : "—"}</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
          <thead>
            <tr>
              {cols.map(([k, lbl]) => (
                <th key={k} onClick={() => setSort(k)} title="정렬"
                  style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)",
                           borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {lbl}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={i}>
                <td style={{ padding: "4px 8px", color: "var(--ink-0)" }}>{r.round}</td>
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.train}</td>
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.test}</td>
                <td style={{ padding: "4px 8px" }}>
                  <span className={(_BT_JOB_BADGE[r.status] || _BT_JOB_BADGE.pending).cls}>{r.status}</span>
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right" }}>{r.trade_count == null ? "—" : r.trade_count}</td>
                <td style={{ padding: "4px 8px", textAlign: "right",
                             color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {_btNum(r.total_profit_pct)}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "var(--red)" }}>{_btNum(r.max_drawdown_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// sweep results → 정렬 가능 표. 각 항목: {...combo, result:{metrics}} 또는 {window, ...metrics}.
function BtSweepTable({ result }) {
  const [sortKey, setSortKey] = useState_bt("__idx");
  const [sortAsc, setSortAsc] = useState_bt(true);
  const raw = (result && result.results) || [];
  // 조합 키(combo)는 result/window 외 임의 키. 동적 컬럼을 수집한다.
  const rows = useMemo_bt(() => raw.map((item, i) => {
    const m = (item && item.result && item.result.metrics) || item.metrics || {};
    const combo = {};
    Object.keys(item || {}).forEach(k => {
      if (k !== "result" && k !== "metrics" && k !== "window" && k !== "status") combo[k] = item[k];
    });
    return {
      __idx: i + 1,
      __combo: combo,
      window: item.window ? (Array.isArray(item.window) ? item.window.join("~") : String(item.window)) : null,
      trade_count: m.trade_count,
      total_profit_pct: m.total_profit_pct,
      max_drawdown_pct: m.max_drawdown_pct,
    };
  }), [raw]);
  const comboKeys = useMemo_bt(() => {
    const s = new Set();
    rows.forEach(r => Object.keys(r.__combo).forEach(k => s.add(k)));
    return Array.from(s);
  }, [rows]);
  const hasWindow = useMemo_bt(() => rows.some(r => r.window != null), [rows]);
  const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
    const get = (r) => (r.__combo[sortKey] != null ? r.__combo[sortKey] : r[sortKey]);
    const va = get(a), vb = get(b);
    const na = Number(va), nb = Number(vb);
    const cmp = (!isNaN(na) && !isNaN(nb)) ? (na - nb) : String(va).localeCompare(String(vb));
    return sortAsc ? cmp : -cmp;
  }), [rows, sortKey, sortAsc]);
  const setSort = (k) => { if (k === sortKey) setSortAsc(a => !a); else { setSortKey(k); setSortAsc(true); } };
  if (raw.length === 0) return <div className="research-empty">스윕 결과가 없습니다.</div>;
  const metricCols = [["trade_count", "거래수"], ["total_profit_pct", "수익%"], ["max_drawdown_pct", "MDD%"]];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
        총 {result.total_combinations != null ? result.total_combinations : raw.length}개 조합
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
          <thead>
            <tr>
              <th onClick={() => setSort("__idx")} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" }}>
                #{sortKey === "__idx" ? (sortAsc ? " ▲" : " ▼") : ""}
              </th>
              {hasWindow && (
                <th onClick={() => setSort("window")} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" }}>
                  윈도우{sortKey === "window" ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              )}
              {comboKeys.map(k => (
                <th key={k} onClick={() => setSort(k)} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {k}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
              {metricCols.map(([k, lbl]) => (
                <th key={k} onClick={() => setSort(k)} style={{ padding: "5px 8px", textAlign: "right", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {lbl}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => (
              <tr key={i}>
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.__idx}</td>
                {hasWindow && <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.window || "—"}</td>}
                {comboKeys.map(k => (
                  <td key={k} style={{ padding: "4px 8px", color: "var(--ink-0)" }}>
                    {r.__combo[k] != null ? String(r.__combo[k]) : "—"}
                  </td>
                ))}
                <td style={{ padding: "4px 8px", textAlign: "right" }}>{r.trade_count == null ? "—" : r.trade_count}</td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {_btNum(r.total_profit_pct)}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "var(--red)" }}>{_btNum(r.max_drawdown_pct)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BtModeResultPanel({ baseUrl, isDemo, jobId, mode }) {
  const [data, setData] = useState_bt(null);
  const [err, setErr] = useState_bt("");
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !jobId) { setData(null); return; }
    let cancelled = false;
    _btFetchJson(baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId), 12000)
      .then(j => { if (!cancelled) { setData(j); setErr(""); } })
      .catch(e => { if (!cancelled) { setData(null); setErr(String(e)); } });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, jobId]);
  const mr = data && data.mode_result;
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          {mode === "wfo" ? "전진분석(WFO) 결과" : "스윕 결과"}
        </div>
      </div>
      <div className="panel-bd">
        {err ? (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>
        ) : !mr ? (
          <div className="research-empty">결과를 불러오는 중이거나 구조화 결과가 없습니다.</div>
        ) : mode === "wfo" ? (
          <BtWfoTable result={mr} />
        ) : (
          <BtSweepTable result={mr} />
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3b-3. 다중 잡 오버레이 — 결과 라이브러리에서 2~4개 선택 → 수익곡선 겹쳐 보기.
//   GET /bt/overlay?job_ids=a,b,c. 정규화 토글(첫 포인트 0 기준)·범례.
// ===========================================================================
const _BT_OVERLAY_COLORS = ["var(--teal)", "var(--amber)", "var(--violet)", "var(--blue)"];

function BtOverlayCurves({ series, normalize }) {
  if (!series || series.length === 0) return <div className="research-empty">오버레이할 곡선이 없습니다.</div>;
  const W = 680, H = 220, padL = 8, padR = 8, padT = 12, padB = 12;
  // 각 시리즈의 cum_profit 배열(정규화 시 첫 포인트를 0으로 평행이동).
  const lines = series.map(s => {
    const cums = (s.cumulative || []).map(p => p.cum_profit || 0);
    const base = (normalize && cums.length > 0) ? cums[0] : 0;
    return cums.map(v => v - base);
  });
  const allVals = lines.reduce((acc, ln) => acc.concat(ln), [0]);
  const lo = Math.min(...allVals), hi = Math.max(...allVals);
  const span = (hi - lo) || 1;
  const maxN = Math.max(1, ...lines.map(l => l.length));
  const x = (i, n) => padL + (n <= 1 ? 0 : (i * (W - padL - padR) / (Math.max(1, maxN - 1))));
  const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
  const zeroY = y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 220 }} preserveAspectRatio="none">
      <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} stroke="var(--line-1)" strokeDasharray="3 3" />
      {lines.map((ln, si) => {
        if (ln.length === 0) return null;
        const path = ln.map((v, i) => (i === 0 ? "M" : "L") + x(i, ln.length).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
        return <path key={si} d={path} fill="none" stroke={_BT_OVERLAY_COLORS[si % _BT_OVERLAY_COLORS.length]} strokeWidth="1.6" />;
      })}
    </svg>
  );
}

function BtOverlayPanel({ baseUrl, isDemo, jobs }) {
  const [picked, setPicked] = useState_bt([]);   // job_id 목록(2~4).
  const [normalize, setNormalize] = useState_bt(false);
  const [result, setResult] = useState_bt(null);
  const [busy, setBusy] = useState_bt(false);
  const [err, setErr] = useState_bt("");

  const doneJobs = (jobs || []).filter(j => j.status === "success" || j.status === "no_trades");
  const toggle = (jobId) => {
    setPicked(prev => prev.includes(jobId)
      ? prev.filter(p => p !== jobId)
      : (prev.length >= 4 ? prev : prev.concat([jobId])));
  };
  const run = () => {
    if (isDemo || !baseUrl || picked.length < 2) return;
    setBusy(true); setErr(""); setResult(null);
    _btFetchJson(baseUrl + "/bt/overlay?job_ids=" + encodeURIComponent(picked.join(",")), 15000)
      .then(j => {
        if (j && j.status === "ok") setResult(j);
        else { setErr((j && j.message) || "오버레이 실패"); }
      })
      .catch(e => setErr("실패: " + e))
      .finally(() => setBusy(false));
  };
  const clearAll = () => { setPicked([]); setResult(null); setErr(""); };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          다중 잡 오버레이
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>{picked.length}/4</span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn primary sm" onClick={run} disabled={isDemo || busy || picked.length < 2}>
            {busy ? "로딩…" : "▸ 겹쳐보기"}
          </button>
          <button className="btn ghost sm" onClick={clearAll} disabled={picked.length === 0}>비우기</button>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 완료 잡을 겹쳐볼 수 있습니다.</div>
        ) : (
          <>
            {doneJobs.length === 0 ? (
              <div className="research-empty">완료된 잡이 없습니다.</div>
            ) : (
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {doneJobs.slice(0, 16).map(j => {
                  const on = picked.includes(j.job_id);
                  return (
                    <button key={j.job_id} className="mono" onClick={() => toggle(j.job_id)}
                      disabled={!on && picked.length >= 4}
                      style={{
                        fontSize: 10, padding: "3px 7px", borderRadius: 4, cursor: "pointer",
                        border: "1px solid " + (on ? "var(--teal)" : "var(--line-1)"),
                        background: on ? "rgba(76,214,179,0.1)" : "transparent",
                        color: on ? "var(--teal)" : "var(--ink-2)",
                      }}
                      title={j.job_id}>
                      {on ? "✓ " : ""}{j.job_id.slice(0, 14)}
                    </button>
                  );
                })}
              </div>
            )}
            {picked.length < 2 && (
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>오버레이에는 2~4개 잡이 필요합니다.</div>
            )}
            {err && <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>}
            {result && result.series && result.series.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--line-1)", paddingTop: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <button className="mono" onClick={() => setNormalize(n => !n)}
                    style={{
                      padding: "4px 9px", fontSize: 10.5, borderRadius: 5, cursor: "pointer",
                      border: "1px solid " + (normalize ? "var(--amber)" : "var(--line-1)"),
                      background: normalize ? "rgba(240,179,90,0.1)" : "transparent",
                      color: normalize ? "var(--amber)" : "var(--ink-2)",
                    }}>
                    {normalize ? "✓ " : ""}정규화(첫 포인트 0)
                  </button>
                  {/* 범례 */}
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {result.series.map((s, i) => (
                      <span key={s.job_id} className="mono" style={{ fontSize: 10, display: "inline-flex", alignItems: "center", gap: 5 }}>
                        <span style={{ width: 12, height: 3, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], display: "inline-block" }}></span>
                        {s.label}
                      </span>
                    ))}
                  </div>
                </div>
                <BtOverlayCurves series={result.series} normalize={normalize} />
                {/* 시리즈별 요약 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {result.series.map((s, i) => (
                    <div key={s.job_id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 6px", borderBottom: "1px solid var(--line-1)" }}>
                      <span style={{ width: 10, height: 10, borderRadius: 2, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], flexShrink: 0 }}></span>
                      <span className="mono" style={{ fontSize: 10.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
                      <span className="mono" style={{ fontSize: 10.5, color: (Number(s.summary.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)") }}>
                        {_btNum(s.summary.total_profit_pct)}%
                      </span>
                      <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", width: 70, textAlign: "right" }}>
                        {s.summary.trade_count}거래
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3c. 접이식 섹션 래퍼 — 수직 과적 해소(evo/포트폴리오를 접을 수 있게).
// ===========================================================================
function BtCollapsible({ title, accent, defaultOpen, children }) {
  const [open, setOpen] = useState_bt(!!defaultOpen);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: open ? 10 : 0 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 6,
          border: "1px solid var(--line-1)", background: "var(--bg-1)", cursor: "pointer",
          color: "var(--ink-1)", fontSize: 12, textAlign: "left",
        }}>
        <span className="dot" style={{ background: accent || "var(--ink-3)" }}></span>
        <span style={{ flex: 1 }}>{title}</span>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▾ 접기" : "▸ 펼치기"}</span>
      </button>
      {open && children}
    </div>
  );
}

// ===========================================================================
// 4. 진화 세대 분석 셀렉터 — run 선택(GET /runs) → 세대 선택(GET /bt/evo_gens).
//   선택 시 부모로 {run_id, gen_no} 를 올려 BtResultArea 가 run/gen 모드로 로드한다.
//   진화 탭 파일은 건드리지 않는다 — /runs·/bt/evo_gens 읽기 전용 계약만 소비.
// ===========================================================================
function BtEvoSelector({ baseUrl, isDemo, onPickGen, activeEvo }) {
  const [runs, setRuns] = useState_bt([]);
  const [runId, setRunId] = useState_bt("");
  const [gens, setGens] = useState_bt([]);
  const [loadingRuns, setLoadingRuns] = useState_bt(false);
  const [loadingGens, setLoadingGens] = useState_bt(false);

  // run 목록 로드(최신 우선 — 서버 정렬 그대로).
  const loadRuns = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setRuns([]); return; }
    setLoadingRuns(true);
    _btFetchJson(baseUrl + "/runs", 6000)
      .then(j => setRuns(Array.isArray(j && j.runs) ? j.runs : []))
      .catch(() => setRuns([]))
      .finally(() => setLoadingRuns(false));
  }, [baseUrl, isDemo]);
  useEffect_bt(() => { loadRuns(); }, [loadRuns]);

  // run 선택 시 세대 목록 로드.
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !runId) { setGens([]); return; }
    setLoadingGens(true);
    _btFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(runId), 6000)
      .then(j => setGens(Array.isArray(j && j.items) ? j.items : []))
      .catch(() => setGens([]))
      .finally(() => setLoadingGens(false));
  }, [baseUrl, isDemo, runId]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          진화 세대 분석
        </div>
        <button className="btn ghost sm" onClick={loadRuns} disabled={isDemo || loadingRuns}>
          {loadingRuns ? "로딩…" : "↻ run"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 진화 run 목록이 표시됩니다.</div>
        ) : (
          <>
            <div className="field">
              <label>진화 run</label>
              <select className="select" value={runId} onChange={e => setRunId(e.target.value)}>
                <option value="">— run 선택 —</option>
                {runs.map(r => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}{r.label ? " · " + r.label : ""}{r.status ? " [" + r.status + "]" : ""}
                  </option>
                ))}
              </select>
            </div>
            {runId && (
              <div style={{ display: "flex", flexDirection: "column", gap: 3, maxHeight: 280, overflowY: "auto" }}>
                {loadingGens ? (
                  <div className="research-empty">세대 로딩 중…</div>
                ) : gens.length === 0 ? (
                  <div className="research-empty">세대가 없습니다</div>
                ) : gens.map(g => {
                  const active = activeEvo && activeEvo.run_id === runId && activeEvo.gen_no === g.gen_no;
                  return (
                    <button key={g.gen_no} onClick={() => onPickGen(runId, g.gen_no)}
                      style={{
                        textAlign: "left", padding: "6px 9px", borderRadius: 5, cursor: "pointer",
                        border: "1px solid " + (active ? "var(--violet)" : "var(--line-1)"),
                        background: active ? "rgba(168,130,255,0.08)" : "var(--bg-0)",
                        display: "flex", alignItems: "center", gap: 8,
                      }}>
                      <span className="mono" style={{ fontSize: 11, color: active ? "var(--violet)" : "var(--ink-0)", flexShrink: 0 }}>
                        g{g.gen_no}
                      </span>
                      <span className={"badge " + (g.gate_passed ? "done" : "idle")} style={{ flexShrink: 0 }}>
                        {g.gate_passed ? "gate" : "—"}
                      </span>
                      <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
                        {g.strategy_gist || g.buy_name || ""}
                      </span>
                      <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>
                        {g.trade_count}거래{g.has_csv ? "" : " ·축약"}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}
            <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
              run {runs.length}개 · 세대 {gens.length}개 (읽기 전용)
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 5. 포트폴리오 결합 분석 패널 — 잡/세대 다중 선택(2~6) → POST /bt/portfolio.
//   결합 수익곡선 SVG · 상관 히트맵 · 개별 기여 표를 그린다. 워크벤치 UI 레이어
//   (부모 P-A 의 포트폴리오 상관 스캔과 역할 구분 — backtest_api docstring 참조).
// ===========================================================================
function _pfFmtMoney(v) {
  const n = Number(v) || 0;
  return (n >= 0 ? "+" : "") + Math.round(n).toLocaleString() + "원";
}

// 결합 누적수익곡선 SVG(외부 라이브러리 금지 — 순수 path).
function BtPortfolioCurve({ equity }) {
  if (!equity || equity.length === 0) return <div className="research-empty">결합 곡선 없음</div>;
  const W = 640, H = 180, padL = 8, padR = 8, padT = 12, padB = 12;
  const cums = equity.map(p => p.cum_profit || 0);
  const lo = Math.min(0, ...cums), hi = Math.max(0, ...cums);
  const span = (hi - lo) || 1;
  const n = equity.length;
  const x = (i) => padL + (n <= 1 ? 0 : (i * (W - padL - padR) / (n - 1)));
  const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
  const path = cums.map((v, i) => (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
  const zeroY = y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 180 }} preserveAspectRatio="none">
      <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} stroke="var(--line-1)" strokeDasharray="3 3" />
      <path d={path} fill="none" stroke="var(--teal)" strokeWidth="1.6" />
    </svg>
  );
}

// 상관 히트맵(피어슨, -1~+1; None 은 회색).
function BtPortfolioHeatmap({ correlation }) {
  const labels = (correlation && correlation.labels) || [];
  const matrix = (correlation && correlation.matrix) || [];
  if (labels.length === 0) return null;
  const cell = (r) => {
    if (r == null) return { bg: "var(--bg-1)", txt: "—" };
    // -1(빨강) ~ 0(중립) ~ +1(청록). 절대값으로 알파.
    const a = Math.min(1, Math.abs(r));
    const color = r >= 0 ? `rgba(76,214,179,${0.12 + a * 0.5})` : `rgba(255,107,107,${0.12 + a * 0.5})`;
    return { bg: color, txt: r.toFixed(2) };
  };
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="mono" style={{ borderCollapse: "collapse", fontSize: 10 }}>
        <thead>
          <tr>
            <th style={{ padding: 4 }}></th>
            {labels.map((l, j) => (
              <th key={j} style={{ padding: 4, color: "var(--ink-3)", maxWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={l}>{l}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td style={{ padding: 4, color: "var(--ink-3)", maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={labels[i]}>{labels[i]}</td>
              {row.map((v, j) => {
                const c = cell(v);
                return <td key={j} style={{ padding: "6px 8px", textAlign: "center", background: c.bg, color: "var(--ink-1)", border: "1px solid var(--bg-0)" }}>{c.txt}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BtPortfolioPanel({ baseUrl, isDemo, jobs, activeEvo }) {
  // 선택 항목: [{kind:"job"|"gen", id, label}]. 최대 6개.
  const [picked, setPicked] = useState_bt([]);
  const [result, setResult] = useState_bt(null);
  const [busy, setBusy] = useState_bt(false);
  const [err, setErr] = useState_bt("");

  const addJob = (j) => {
    if (picked.length >= 6) return;
    const key = "job:" + j.job_id;
    if (picked.some(p => p.key === key)) return;
    setPicked(prev => prev.concat([{ key, kind: "job", job_id: j.job_id, label: j.job_id.slice(0, 14) }]));
  };
  const addEvo = () => {
    if (!activeEvo || picked.length >= 6) return;
    const key = "gen:" + activeEvo.run_id + "/" + activeEvo.gen_no;
    if (picked.some(p => p.key === key)) return;
    setPicked(prev => prev.concat([{
      key, kind: "gen", run_id: activeEvo.run_id, gen_no: activeEvo.gen_no,
      label: activeEvo.run_id.slice(0, 8) + "/g" + activeEvo.gen_no,
    }]));
  };
  const removeAt = (key) => setPicked(prev => prev.filter(p => p.key !== key));
  const clearAll = () => { setPicked([]); setResult(null); setErr(""); };

  const run = () => {
    if (isDemo || !baseUrl) return;
    setBusy(true); setErr(""); setResult(null);
    const items = picked.map(p => p.kind === "job"
      ? { job_id: p.job_id, label: p.label }
      : { run_id: p.run_id, gen_no: p.gen_no, label: p.label });
    _btPostJson(baseUrl + "/bt/portfolio", { items }, 20000)
      .then(j => {
        if (j && j.status === "ok") { setResult(j.portfolio); }
        else { setErr((j && j.message) || "포트폴리오 분석 실패"); }
      })
      .catch(e => setErr("실패: " + e))
      .finally(() => setBusy(false));
  };

  const doneJobs = (jobs || []).filter(j => j.status === "success" || j.status === "no_trades");

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          포트폴리오 결합 분석
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
            {picked.length}/6
          </span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn primary sm" onClick={run}
                  disabled={isDemo || busy || picked.length < 2}>
            {busy ? "분석중…" : "▸ 결합 분석"}
          </button>
          <button className="btn ghost sm" onClick={clearAll} disabled={picked.length === 0}>비우기</button>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 잡/세대를 결합할 수 있습니다.</div>
        ) : (
          <>
            {/* 추가 소스 */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>추가:</span>
              {activeEvo && (
                <button className="btn ghost sm" onClick={addEvo} disabled={picked.length >= 6}
                        title="현재 선택된 진화 세대를 포트폴리오에 추가">
                  ＋세대 {activeEvo.run_id.slice(0, 6)}/g{activeEvo.gen_no}
                </button>
              )}
            </div>
            {/* 완료 잡 칩 */}
            {doneJobs.length > 0 && (
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {doneJobs.slice(0, 10).map(j => (
                  <button key={j.job_id} className="btn ghost sm" onClick={() => addJob(j)}
                          disabled={picked.length >= 6}
                          style={{ fontSize: 10, padding: "3px 7px" }}
                          title={"잡 " + j.job_id + " 추가"}>
                    ＋{j.job_id.slice(0, 12)}
                  </button>
                ))}
              </div>
            )}
            {/* 선택 항목 */}
            {picked.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {picked.map(p => (
                  <span key={p.key} className="mono" style={{
                    fontSize: 10, padding: "3px 6px", borderRadius: 4,
                    border: "1px solid " + (p.kind === "gen" ? "var(--violet)" : "var(--teal-dim)"),
                    color: p.kind === "gen" ? "var(--violet)" : "var(--teal)",
                    display: "inline-flex", alignItems: "center", gap: 5,
                  }}>
                    {p.label}
                    <button onClick={() => removeAt(p.key)} style={{ background: "transparent", border: 0, color: "var(--ink-3)", cursor: "pointer", padding: 0 }}>✕</button>
                  </span>
                ))}
              </div>
            )}
            {picked.length < 2 && (
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                결합 분석에는 2~6개 전략(잡/세대)이 필요합니다.
              </div>
            )}
            {err && <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>}

            {/* 결과 */}
            {result && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--line-1)", paddingTop: 10 }}>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  <span className="mono" style={{ fontSize: 11 }}>
                    결합 총손익 <b style={{ color: (result.combined.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)") }}>
                      {_pfFmtMoney(result.combined.total_profit_krw)}</b>
                  </span>
                  <span className="mono" style={{ fontSize: 11 }}>
                    결합 MDD <b style={{ color: "var(--red)" }}>{Math.round(result.combined.max_drawdown_krw).toLocaleString()}원</b>
                  </span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
                    {result.combined.trading_days}거래일 · {result.count}전략
                  </span>
                </div>
                {/* 결합 곡선 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>결합 누적수익곡선</div>
                  <BtPortfolioCurve equity={result.combined.equity} />
                </div>
                {/* 상관 히트맵 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>전략 간 일별손익 상관</div>
                  <BtPortfolioHeatmap correlation={result.correlation} />
                </div>
                {/* 개별 기여 표 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>개별 기여</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    {result.strategies.map((s, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 6px", borderBottom: "1px solid var(--line-1)" }}>
                        <span className="mono" style={{ fontSize: 11, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
                        <span className="mono" style={{ fontSize: 10.5, color: (s.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)") }}>
                          {_pfFmtMoney(s.total_profit_krw)}
                        </span>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", width: 64, textAlign: "right" }}>
                          기여 {s.contribution_pct.toFixed(0)}%
                        </span>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--red)", width: 90, textAlign: "right" }}>
                          MDD {Math.round(s.max_drawdown_krw).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 탭 루트 — 헬스 배지 + 좌(라이브러리·에디터·실행) / 우(결과) 레이아웃.
//   결과·분석 영역(BtResultArea + 메트릭 카드 + 차트 + 기여/인사이트)은
//   backtest-charts.jsx 에 있으며 window 전역으로 공유된다(이 파일보다 먼저 로드).
// ===========================================================================
function BacktestTab({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [health, setHealth] = useState_bt(null);
  const [reloadKey, setReloadKey] = useState_bt(0);     // 라이브러리 재로드 트리거(저장/삭제 후).
  const [resultJobId, setResultJobId] = useState_bt("");
  const [libNames, setLibNames] = useState_bt({ buy: [], sell: [] });
  // 실행 셀렉터 = 듀얼 에디터 소스. 매수/매도 선택을 탭 루트로 끌어올려 공유한다.
  const [buyName, setBuyName] = useState_bt("");
  const [sellName, setSellName] = useState_bt("");
  // 진화 세대 분석 소스 — {run_id, gen_no} 또는 null. 잡 선택과 상호배타(둘 중 하나만).
  const [evoSource, setEvoSource] = useState_bt(null);
  // 포트폴리오·결과 라이브러리가 소비할 완료 잡 목록(BtRunPanel 이 끌어올려 공유).
  const [jobsList, setJobsList] = useState_bt([]);
  // 결과 라이브러리 강제 재로드 토큰(메타 갱신/잡 변경 후 잡 목록 새로고침).
  const [jobsReloadKey, setJobsReloadKey] = useState_bt(0);
  // A/B 비교 — compareA(기준 잡 id), compareView(/bt/compare 응답).
  const [compareA, setCompareA] = useState_bt("");
  const [compareView, setCompareView] = useState_bt(null);

  // B2 — 하위 탭 [조건식 편집 | 결과 분석]. STOM GUI 처럼 화면 전환(상단 실행바는 항상 노출).
  //   localStorage 로 마지막 선택을 유지(선택). 잘못된 값/접근 실패는 기본값으로 흡수.
  const [subTab, setSubTab] = useState_bt(() => {
    try {
      const v = window.localStorage && window.localStorage.getItem("bt_subtab");
      return v === "result" || v === "edit" ? v : "edit";
    } catch (e) { return "edit"; }
  });
  const selectSubTab = useCallback_bt((t) => {
    setSubTab(t);
    try { window.localStorage && window.localStorage.setItem("bt_subtab", t); } catch (e) {}
  }, []);

  // 잡 선택 → 잡 결과 모드(진화 세대 소스 해제) + 결과 분석 탭으로 자동 전환.
  const onPickJobResult = useCallback_bt((jobId) => {
    setResultJobId(jobId);
    if (jobId) { setEvoSource(null); selectSubTab("result"); }
  }, [selectSubTab]);
  // 진화 세대 선택 → 세대 결과 모드(잡 결과 해제) + 결과 분석 탭으로 자동 전환.
  const onPickGen = useCallback_bt((runId, genNo) => {
    setEvoSource({ run_id: runId, gen_no: genNo });
    setResultJobId("");
    selectSubTab("result");
  }, [selectSubTab]);

  // "바로 백테스트" 핸드오프 소비 — 진화 탭(evolution-analysis)·리서치 프로(pro.html)가
  //   localStorage(stom_bt_evo_pending)에 {run_id, gen_no}를 적재하고 탭/페이지를 전환한다.
  //   ① 마운트 시 pending 1회 소비(cross-page: pro.html → /ui/ 이동 케이스),
  //   ② 마운트 중에는 CustomEvent("stom:bt-evo-select")를 직접 수신(같은 페이지 케이스).
  //   소비 후 키를 지워 다음 진입 시 재적용을 막는다. 파싱 실패는 조용히 폐기.
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
    } catch (e) {}
    const onSelect = (ev) => {
      try { window.localStorage && window.localStorage.removeItem("stom_bt_evo_pending"); } catch (e) {}
      consume(ev && ev.detail);
    };
    window.addEventListener("stom:bt-evo-select", onSelect);
    return () => window.removeEventListener("stom:bt-evo-select", onSelect);
  }, [onPickGen]);

  // 비교(B) 실행 — A 고정 후 다른 잡을 B 로 비교.
  const runCompare = useCallback_bt((jobB) => {
    if (isDemo || !baseUrl || !compareA || !jobB) return;
    const url = baseUrl + "/bt/compare?job_a=" + encodeURIComponent(compareA)
              + "&job_b=" + encodeURIComponent(jobB);
    _btFetchJson(url, 12000)
      .then(j => setCompareView(j || null))
      .catch(() => setCompareView(null));
  }, [baseUrl, isDemo, compareA]);

  const onSetCompareA = useCallback_bt((jobId) => {
    setCompareA(jobId);
    setCompareView(null);
  }, []);
  const onCloseCompare = useCallback_bt(() => { setCompareView(null); }, []);

  // 헬스 체크.
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setHealth(null); return; }
    _btFetchJson(baseUrl + "/bt/health", 3000).then(setHealth).catch(() => setHealth(null));
  }, [baseUrl, isDemo, reloadKey]);

  // 실행 셀렉터용 buy/sell 이름 목록(라이브러리와 독립적으로 양쪽 모두 필요).
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setLibNames({ buy: [], sell: [] }); return; }
    let cancelled = false;
    Promise.all([
      _btFetchJson(baseUrl + "/bt/strategies?kind=buy", 4000).catch(() => ({ items: [] })),
      _btFetchJson(baseUrl + "/bt/strategies?kind=sell", 4000).catch(() => ({ items: [] })),
    ]).then(([b, s]) => {
      if (cancelled) return;
      setLibNames({
        buy: (b.items || []).map(it => it.name),
        sell: (s.items || []).map(it => it.name),
      });
    });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, reloadKey]);

  const connected = !!(health && health.status === "ok");
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: "checking", color: "var(--amber)" };

  const onSaved = useCallback_bt(() => { setReloadKey(k => k + 1); }, []);
  const reloadJobs = useCallback_bt(() => { setJobsReloadKey(k => k + 1); }, []);

  // 데모 예시 모드 — 연결됐고 잡/세대 미선택이면 기본 화면에 합성 예시 결과를 띄운다
  //   (빈 화면 금지). sentinel job_id 를 BtResultArea 에 실어 charts 무수정 렌더 경로로 보낸다.
  const showDemoResult = connected && !isDemo && !resultJobId && !evoSource;
  const effectiveJobId = showDemoResult ? "__demo__" : resultJobId;

  // 선택 잡의 모드(wfo/sweep 이면 csv 단일 분석 대신 모드별 표를 띄운다).
  const selectedJobMode = useMemo_bt(() => {
    if (!resultJobId) return "backtest";
    const j = (jobsList || []).find(x => x.job_id === resultJobId);
    return (j && j.spec && j.spec.mode) || "backtest";
  }, [jobsList, resultJobId]);
  const isModeResult = resultJobId && (selectedJobMode === "wfo" || selectedJobMode === "sweep");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 탭 헤더 배지 행 */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
                    background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 8 }}>
        <span className="panel-hd-title" style={{ border: 0 }}>
          <span className="dot" style={{ background: "var(--teal)" }}></span>백테스트 워크벤치
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: badge.color, letterSpacing: ".06em", marginLeft: "auto" }}>
          ● {badge.label}
        </span>
      </div>

      {/* 상단 고정 전폭 실행 패널 — 항상 노출(매수/매도·기간·모드·대형 실행 버튼·활성 잡 카드) */}
      <BtRunPanel baseUrl={baseUrl} isDemo={isDemo} libNames={libNames} onResult={onPickJobResult}
                  compareA={compareA} onCompareB={runCompare} onJobs={setJobsList}
                  buy={buyName} sell={sellName} onBuy={setBuyName} onSell={setSellName}
                  reloadJobsKey={jobsReloadKey} />

      {/* B2 — 하위 탭 전환 바 [조건식 편집 | 결과 분석] (STOM GUI 화면 전환과 동일) */}
      <div className="bt-subtabs" style={{ display: "flex", gap: 4, padding: 4,
            background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 8 }}>
        {[
          { id: "edit", label: "조건식 편집" },
          { id: "result", label: "결과 분석" },
        ].map(t => {
          const active = subTab === t.id;
          return (
            <button key={t.id} onClick={() => selectSubTab(t.id)}
                    style={{
                      flex: 1, padding: "9px 14px", borderRadius: 6, cursor: "pointer",
                      fontFamily: "var(--mono)", fontSize: 13, fontWeight: active ? 700 : 400,
                      border: active ? "1px solid var(--teal-dim, var(--teal))" : "1px solid transparent",
                      background: active ? "var(--bg-0)" : "transparent",
                      color: active ? "var(--teal)" : "var(--ink-2)",
                    }}>
              {t.label}
            </button>
          );
        })}
      </div>

      {/* 조건식 편집 탭 — 듀얼 에디터(변수 칩 포함) + 조건식 라이브러리 */}
      {subTab === "edit" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <BtDualEditor baseUrl={baseUrl} isDemo={isDemo} buyName={buyName} sellName={sellName}
                        onSaved={onSaved}
                        onDeletedBuy={() => { setReloadKey(k => k + 1); setBuyName(""); }}
                        onDeletedSell={() => { setReloadKey(k => k + 1); setSellName(""); }} />
          <BtCollapsible title="조건식 라이브러리(빠른 선택)" accent="var(--teal)" defaultOpen>
            <div className="grid-main" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
              <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="buy" onKind={() => {}} lockKind
                              onPick={setBuyName} selectedName={buyName} reloadKey={reloadKey} />
              <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="sell" onKind={() => {}} lockKind
                              onPick={setSellName} selectedName={sellName} reloadKey={reloadKey} />
            </div>
          </BtCollapsible>
        </div>
      )}

      {/* 결과 분석 탭 — 결과 라이브러리 + 전폭 결과/분석 영역 + 접이식 분석 섹션 */}
      {subTab === "result" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <BtResultLibrary baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} onResult={onPickJobResult}
                           selectedJobId={resultJobId} onReload={reloadJobs}
                           compareA={compareA} onSetCompareA={onSetCompareA} onCompareB={runCompare} />
          <div style={{ minWidth: 0, position: "relative" }}>
            {showDemoResult && (
              <span className="badge warn" style={{ position: "absolute", top: 10, right: 10, zIndex: 2 }}>
                예시 데이터
              </span>
            )}
            {isModeResult ? (
              <BtModeResultPanel baseUrl={baseUrl} isDemo={isDemo} jobId={resultJobId} mode={selectedJobMode} />
            ) : (
              <BtResultArea baseUrl={baseUrl} isDemo={isDemo} jobId={effectiveJobId} evoSource={evoSource}
                            onSetCompareA={onSetCompareA} compareView={compareView} onCloseCompare={onCloseCompare} />
            )}
          </div>

          {/* 접이식 분석 섹션 — 진화 세대 분석 · 오버레이 · 포트폴리오 결합 */}
          <BtCollapsible title="진화 세대 분석" accent="var(--violet)" defaultOpen={false}>
            <BtEvoSelector baseUrl={baseUrl} isDemo={isDemo} onPickGen={onPickGen} activeEvo={evoSource} />
          </BtCollapsible>
          <BtCollapsible title="다중 잡 오버레이(수익곡선 겹쳐보기)" accent="var(--teal)" defaultOpen={false}>
            <BtOverlayPanel baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} />
          </BtCollapsible>
          <BtCollapsible title="포트폴리오 결합 분석" accent="var(--blue)" defaultOpen={false}>
            <BtPortfolioPanel baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} activeEvo={evoSource} />
          </BtCollapsible>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { BacktestTab });
