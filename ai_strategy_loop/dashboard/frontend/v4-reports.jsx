/* v4-reports.jsx — V4 "Reports" 탭: 리포트 HTML 안전 뷰어.
 *   보안(§10-5, UXR-P7): 백엔드 /reports/view 가 CSP default-src 'none' 로 스크립트를 차단하고,
 *   여기서 sandbox="" iframe(스크립트·동일출처·폼·팝업 전면 차단)로 이중 방어한다.
 *   → inline JS 를 포함한 리포트(alpha_lab reporting 산출물 등)도 실행되지 않는다.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_rp7, useEffect: useEffect_rp7 } = React;

function _fmtReportBytes(n) {
  if (!Number.isFinite(n)) return "";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}

function V4Reports({ baseUrl }) {
  const [mode, setMode] = useState_rp7("reports"); // reports | wiki
  const [list, setList] = useState_rp7(null);
  const [err, setErr] = useState_rp7("");
  const [sel, setSel] = useState_rp7("");
  const [wiki, setWiki] = useState_rp7(null);
  const [wikiSel, setWikiSel] = useState_rp7("");
  const [wikiQuery, setWikiQuery] = useState_rp7("");
  const [wikiDoc, setWikiDoc] = useState_rp7(null);
  const wikiReqRef = React.useRef(0);

  useEffect_rp7(() => {
    if (!baseUrl) { setList([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/reports", { signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (cancelled) return;
        const reports = Array.isArray(j && j.reports) ? j.reports : [];
        setList(reports);
        setSel(prev => prev || (reports.length ? reports[0].path : ""));
      })
      .catch(e => { if (!cancelled) { setList([]); setErr(String(e && e.message ? e.message : e)); } });
    return () => { cancelled = true; };
  }, [baseUrl]);

  useEffect_rp7(() => { // V5.6 Wiki 색인(모드 진입 시 1회) — 원문 불변, /research_docs 소비.
    if (!baseUrl || mode !== "wiki" || wiki !== null) return;
    let cancelled = false;
    fetch(baseUrl + "/research_docs", { signal: AbortSignal.timeout(20000) }) // 930+ 문서 색인 — 콜드 서버에서 6s 초과 실측
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { if (!cancelled) { const docs = Array.isArray(j && j.docs) ? j.docs : []; setWiki(docs); setWikiSel(prev => prev || (docs.length ? docs[0].id : "")); } })
      .catch(() => { if (!cancelled) setWiki([]); });
    return () => { cancelled = true; };
  }, [baseUrl, mode, wiki]);

  useEffect_rp7(() => { // 선택 문서 마크다운(원문 그대로 <pre> 표시, 세대 가드).
    if (!baseUrl || mode !== "wiki" || !wikiSel) { setWikiDoc(null); return; }
    const reqId = ++wikiReqRef.current;
    let cancelled = false;
    fetch(baseUrl + "/research_doc?id=" + encodeURIComponent(wikiSel), { signal: AbortSignal.timeout(12000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { if (!cancelled && reqId === wikiReqRef.current) setWikiDoc(j); })
      .catch(e => { if (!cancelled && reqId === wikiReqRef.current) setWikiDoc({ available: false, reason: String(e && e.message ? e.message : e) }); });
    return () => { cancelled = true; };
  }, [baseUrl, mode, wikiSel]);

  const viewUrl = sel ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";
  // V6.4(S5): 스텝 자동 리포트(generated_reports/)와 일반 문서를 구분 + 결과 보고서 예시 바로가기.
  const stepReports = (list || []).filter(rp => String(rp.path).startsWith("generated_reports/"));
  const otherReports = (list || []).filter(rp => !String(rp.path).startsWith("generated_reports/"));
  const exampleReport = stepReports.find(rp => /v5_reporting_demo/.test(rp.path)) || stepReports[0] || null;
  const wikiFiltered = (wiki || []).filter(d => {
    const q = wikiQuery.trim().toLowerCase();
    if (!q) return true;
    return ((d.title || "") + " " + (d.id || "") + " " + (d.category || "")).toLowerCase().includes(q);
  });
  const renderReportItem = (rp) => (
    <button key={rp.path} className={"v4-reports-item" + (sel === rp.path ? " active" : "")} onClick={() => setSel(rp.path)} title={rp.path}>
      <span className="v4-reports-name">{rp.name}</span>
      <span className="v4-reports-meta mono">{_fmtReportBytes(rp.bytes)}</span>
    </button>
  );

  return (
    <section className="v4-reports" aria-labelledby="v4-reports-heading">
      <div className="v4-reports-head">
        <h2 id="v4-reports-heading" className="panel-hd-title">Reports · 리포트/문서 뷰어</h2>
        <div className="v4-reports-modes" role="tablist" aria-label="뷰 모드">
          <button role="tab" aria-selected={mode === "reports"} className={"btn ghost sm" + (mode === "reports" ? " active" : "")} onClick={() => setMode("reports")}>HTML 리포트</button>
          <button role="tab" aria-selected={mode === "wiki"} className={"btn ghost sm" + (mode === "wiki" ? " active" : "")} onClick={() => setMode("wiki")}>연구 문서(Wiki)</button>
          {exampleReport && (
            <button className="btn ghost sm v6-report-example" title="스텝 자동 리포트 표준양식 결과 예시 열기"
                    onClick={() => { setMode("reports"); setSel(exampleReport.path); }}>결과 보고서 예시</button>
          )}
        </div>
      </div>
      {mode === "reports" ? (
        <React.Fragment>
          <p className="v4-reports-safe mono" role="note">읽기 전용 · 스크립트 차단(CSP default-src 'none' + sandbox iframe) · docs/ 하위 HTML 한정</p>
          <div className="v4-reports-body">
            <aside className="v4-reports-list" aria-label="리포트 목록">
              {list === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
              {list !== null && list.length === 0 && (
                <div className="v4-reports-empty mono">리포트 없음{err ? " · " + err : ""}<div className="v4-reports-hint">docs/ 하위 *.html 생성 시 자동 표시</div></div>
              )}
              {list !== null && stepReports.length > 0 && (
                <div className="v6-report-group mono">스텝 자동 리포트 · {stepReports.length}건 (build_step_reports.py)</div>
              )}
              {list !== null && stepReports.map(renderReportItem)}
              {list !== null && otherReports.length > 0 && (
                <div className="v6-report-group mono">일반 문서 리포트 · {otherReports.length}건</div>
              )}
              {list !== null && otherReports.map(renderReportItem)}
            </aside>
            <div className="v4-reports-view">
              {viewUrl ? (
                <iframe key={viewUrl} className="v4-reports-frame" src={viewUrl} sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" />
              ) : (
                <div className="v4-reports-empty mono">리포트를 선택하세요</div>
              )}
            </div>
          </div>
        </React.Fragment>
      ) : (
        <React.Fragment>
          <p className="v4-reports-safe mono" role="note">읽기 전용 · 원문 마크다운 불변(pre 텍스트 표시) · /research_docs 색인</p>
          <div className="v4-reports-body">
            <aside className="v4-reports-list" aria-label="연구 문서 목록">
              <input className="toolbar-input v6-wiki-search" type="search" placeholder="검색 (제목·경로·분류)"
                     value={wikiQuery} onChange={e => setWikiQuery(e.target.value)}
                     aria-label="연구 문서 검색" />
              {wiki === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
              {wiki !== null && wikiFiltered.length === 0 && <div className="v4-reports-empty mono">{wikiQuery ? "검색 결과 없음 · " + wikiQuery : "연구 문서 없음"}</div>}
              {wiki !== null && wikiQuery && wikiFiltered.length > 0 && (
                <div className="v6-report-group mono">검색 결과 {wikiFiltered.length}건 / 전체 {wiki.length}건</div>
              )}
              {wiki !== null && wikiFiltered.map(d => (
                <button key={d.id} className={"v4-reports-item" + (wikiSel === d.id ? " active" : "")} onClick={() => setWikiSel(d.id)} title={d.id}>
                  <span className="v4-reports-name">{d.title || d.id}</span>
                  <span className="v4-reports-meta mono">{d.category || ""}</span>
                </button>
              ))}
            </aside>
            <div className="v4-reports-view v4-wiki-view">
              {wikiDoc == null ? (
                <div className="v4-reports-empty mono">문서를 선택하세요</div>
              ) : wikiDoc.available === false ? (
                <div className="v4-reports-empty mono">문서 로드 실패 · {wikiDoc.reason}</div>
              ) : (
                <pre className="v4-wiki-md">{wikiDoc.markdown || ""}</pre>
              )}
            </div>
          </div>
        </React.Fragment>
      )}
    </section>
  );
}

Object.assign(window, { V4Reports });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Reports };
