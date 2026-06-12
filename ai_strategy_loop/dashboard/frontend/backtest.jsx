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
  const [mode, setMode] = useState_bt("backtest");      // backtest | optimize (GUI 패리티 1차).
  const [paramSpace, setParamSpace] = useState_bt("");  // optimize 탐색공간 JSON 경로.
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
          {/* 모드 토글 [백테스트|최적화] */}
          <div className="field" style={{ minWidth: 150 }}>
            <label>모드</label>
            <div style={{ display: "flex", gap: 4 }}>
              {[["backtest", "백테스트"], ["optimize", "최적화"]].map(([m, lbl]) => (
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
            ▸ {mode === "optimize" ? "최적화 실행" : "백테스트 실행"}
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

  // 잡 선택 → 잡 결과 모드(진화 세대 소스 해제).
  const onPickJobResult = useCallback_bt((jobId) => {
    setResultJobId(jobId);
    if (jobId) setEvoSource(null);
  }, []);
  // 진화 세대 선택 → 세대 결과 모드(잡 결과 해제).
  const onPickGen = useCallback_bt((runId, genNo) => {
    setEvoSource({ run_id: runId, gen_no: genNo });
    setResultJobId("");
  }, []);

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

      {/* 상단 고정 전폭 실행 패널 — 폴드 위 가시성 핵심(매수/매도·기간·모드·대형 실행 버튼) */}
      <BtRunPanel baseUrl={baseUrl} isDemo={isDemo} libNames={libNames} onResult={onPickJobResult}
                  compareA={compareA} onCompareB={runCompare} onJobs={setJobsList}
                  buy={buyName} sell={sellName} onBuy={setBuyName} onSell={setSellName}
                  reloadJobsKey={jobsReloadKey} />

      {/* 본문 2컬럼 — 좌(라이브러리·듀얼 에디터·결과 라이브러리) / 우(결과·분석) */}
      <div className="grid-main" style={{ gridTemplateColumns: "minmax(0, 520px) minmax(0, 1fr)" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
          <BtDualEditor baseUrl={baseUrl} isDemo={isDemo} buyName={buyName} sellName={sellName}
                        onSaved={onSaved}
                        onDeletedBuy={() => { setReloadKey(k => k + 1); setBuyName(""); }}
                        onDeletedSell={() => { setReloadKey(k => k + 1); setSellName(""); }} />
          <BtResultLibrary baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} onResult={onPickJobResult}
                           selectedJobId={resultJobId} onReload={reloadJobs}
                           compareA={compareA} onSetCompareA={onSetCompareA} onCompareB={runCompare} />
        </div>
        <div style={{ minWidth: 0, position: "relative" }}>
          {showDemoResult && (
            <span className="badge warn" style={{ position: "absolute", top: 10, right: 10, zIndex: 2 }}>
              예시 데이터
            </span>
          )}
          <BtResultArea baseUrl={baseUrl} isDemo={isDemo} jobId={effectiveJobId} evoSource={evoSource}
                        onSetCompareA={onSetCompareA} compareView={compareView} onCloseCompare={onCloseCompare} />
        </div>
      </div>

      {/* 접이식 섹션 — 수직 과적 해소(진화 세대 분석 · 포트폴리오 결합) */}
      <BtCollapsible title="진화 세대 분석" accent="var(--violet)" defaultOpen={false}>
        <BtEvoSelector baseUrl={baseUrl} isDemo={isDemo} onPickGen={onPickGen} activeEvo={evoSource} />
      </BtCollapsible>
      <BtCollapsible title="포트폴리오 결합 분석" accent="var(--blue)" defaultOpen={false}>
        <BtPortfolioPanel baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} activeEvo={evoSource} />
      </BtCollapsible>

      {/* 조건식 라이브러리 — 듀얼 에디터의 보조(접이식). 선택 시 셀렉터로 끌어와 편집 */}
      <BtCollapsible title="조건식 라이브러리(빠른 선택)" accent="var(--teal)" defaultOpen={false}>
        <div className="grid-main" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
          <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="buy" onKind={() => {}} lockKind
                          onPick={setBuyName} selectedName={buyName} reloadKey={reloadKey} />
          <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="sell" onKind={() => {}} lockKind
                          onPick={setSellName} selectedName={sellName} reloadKey={reloadKey} />
        </div>
      </BtCollapsible>
    </div>
  );
}

Object.assign(window, { BacktestTab });
