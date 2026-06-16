/* Backtest workbench tab — 조건식 라이브러리·변수칩·코드 에디터 묶음 (split from backtest.jsx).
   라이브러리 목록 + SSOT 변수 칩 + 단일/듀얼 코드 에디터(로드/검증/저장/삭제). 디자인 언어:
   다크 테마(var(--bg-1)/var(--line-1)) · mono 라벨 · panel/btn 클래스 재사용.

   모든 fetch 는 무예외(실패→빈 상태+재시도), AbortSignal.timeout.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_bt, useEffect_bt, useCallback_bt, useMemo_bt, _btFetchJson, _btPostJson } from "./bt-tab-utils.jsx";

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

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { BtLibraryPanel, BtVarChips, BtCodeEditor, BtDualEditor };
