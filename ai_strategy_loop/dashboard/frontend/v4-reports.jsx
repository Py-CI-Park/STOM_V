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
  // v5.3.9: 뷰어 강화 — 목차(TOC)·앵커 점프·이전/다음 문서 순회.
  const [toc, setToc] = useState_rp7([]);
  const [anchor, setAnchor] = useState_rp7("");
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
  useEffect_rp7(() => { // v5.3.9 TOC: 선택 리포트 HTML 에서 id 있는 h2/h3 추출(무실행 텍스트 파싱).
    setToc([]); setAnchor("");
    if (!baseUrl || mode !== "reports" || !sel) return undefined;
    let cancelled = false;
    fetch(baseUrl + "/reports/view?path=" + encodeURIComponent(sel), { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.text() : ""))
      .then(html => {
        if (cancelled) return;
        const out = [];
        const re = /<h([23])[^>]*id="([^"]+)"[^>]*>([\s\S]*?)<\/h\1>/g;
        let m2;
        while ((m2 = re.exec(html)) && out.length < 60) {
          const txt = m2[3].replace(/<[^>]+>/g, "").trim().slice(0, 48);
          if (txt) out.push({ lvl: Number(m2[1]), id: m2[2], txt });
        }
        setToc(out);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [baseUrl, mode, sel]);

  const viewUrl = sel ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";
  const frameSrc = viewUrl ? (anchor ? viewUrl + "#" + anchor : viewUrl) : "";
  // v5.4 R2 — 결과 분석 시스템: 목록을 3그룹으로 구분해 "결과 리포트(자동)"와 "연구 문서"를 분리.
  //   ① run 종합 보고서(사이클 전체 결과) ② 스텝 자동 리포트 ③ 일반 연구 문서.
  const generated = (list || []).filter(rp => String(rp.path).startsWith("generated_reports/"));
  const runReports = generated.filter(rp => /run_report_/.test(rp.path));
  const stepReports = generated.filter(rp => !/run_report_/.test(rp.path));
  const otherReports = (list || []).filter(rp => !String(rp.path).startsWith("generated_reports/"));
  const exampleReport = runReports[0] || stepReports.find(rp => /v5_reporting_demo/.test(rp.path)) || stepReports[0] || null;
  const wikiFiltered = (wiki || []).filter(d => {
    const q = wikiQuery.trim().toLowerCase();
    if (!q) return true;
    return ((d.title || "") + " " + (d.id || "") + " " + (d.category || "")).toLowerCase().includes(q);
  });
  const renderReportItem = (rp) => (
    <button key={rp.path} className={"v4-reports-item" + (sel === rp.path ? " active" : "")} onClick={() => setSel(rp.path)} title={rp.path}>
      <span className="v4-reports-name">{/run_report_/.test(rp.path) && <span className="v4-chip ok" style={{ marginRight: 6 }}>run 종합</span>}{rp.name}</span>
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
          {(() => { // v5.3.9: 이전/다음 문서 순회(보는 순서).
            const flat = [...runReports, ...stepReports, ...otherReports];
            const idx = flat.findIndex(rp => rp.path === sel);
            if (idx < 0 || flat.length < 2) return null;
            return (
              <span style={{ display: "inline-flex", gap: 4 }}>
                <button className="btn ghost sm" disabled={idx <= 0} onClick={() => setSel(flat[idx - 1].path)} title="이전 문서">◀ 이전</button>
                <span className="mono" style={{ alignSelf: "center", fontSize: 11, color: "var(--ink-3)" }}>{idx + 1}/{flat.length}</span>
                <button className="btn ghost sm" disabled={idx >= flat.length - 1} onClick={() => setSel(flat[idx + 1].path)} title="다음 문서">다음 ▶</button>
              </span>
            );
          })()}
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
              {list !== null && runReports.length > 0 && (
                <div className="v6-report-group run mono">결과 리포트 · run 종합 {runReports.length}건 (사이클 전체 자동 생성)</div>
              )}
              {list !== null && runReports.map(renderReportItem)}
              {list !== null && stepReports.length > 0 && (
                <div className="v6-report-group mono">스텝 자동 리포트 · {stepReports.length}건 (build_step_reports.py)</div>
              )}
              {list !== null && stepReports.map(renderReportItem)}
              {list !== null && otherReports.length > 0 && (
                <div className="v6-report-group mono">연구 문서(사람 작성) · {otherReports.length}건</div>
              )}
              {list !== null && otherReports.map(renderReportItem)}
            </aside>
            {toc.length > 0 && (
              <nav className="v4-reports-toc" aria-label="리포트 목차">
                <div className="v6-report-group mono">목차 · {toc.length}</div>
                {toc.map(t => (
                  <button key={t.id} className={"v4-toc-item lvl" + t.lvl + (anchor === t.id ? " active" : "")}
                          onClick={() => setAnchor(t.id)} title={t.txt}>{t.txt}</button>
                ))}
              </nav>
            )}
            <div className="v4-reports-view">
              {viewUrl ? (
                <iframe key={frameSrc} className="v4-reports-frame" src={frameSrc} sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" />
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
