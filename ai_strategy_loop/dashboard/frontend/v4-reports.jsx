/* v4-reports.jsx — V4 "Reports" 탭: 리포트 HTML 안전 뷰어.
 *   보안(§10-5, UXR-P7): 백엔드 /reports/view 가 CSP default-src 'none' 로 스크립트를 차단하고,
 *   여기서 sandbox="" iframe(스크립트·동일출처·폼·팝업 전면 차단)로 이중 방어한다.
 *   → inline JS 를 포함한 리포트(alpha_lab reporting 산출물 등)도 실행되지 않는다.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_rp7, useEffect: useEffect_rp7, useRef: useRef_rp7 } = React;

function _fmtReportBytes(n) {
  if (!Number.isFinite(n)) return "";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}
function _reportToc(report) {
  if (!Array.isArray(report && report.toc)) return null;
  return report.toc
    .filter(item => item && typeof item.id === "string" && typeof item.label === "string")
    .slice(0, 60)
    .map(item => ({ id: item.id, label: item.label, lvl: item.level === 3 ? 3 : 2 }));
}
function _reportKind(report) {
  if (!report || report.registered !== true) return "unregistered";
  return ["run", "step", "legacy"].includes(report.report_type) ? report.report_type : "legacy";
}
function _reportHash(report) {
  return report && (report.content_sha256 || report.source_sha256 || report.sha256 || "");
}
function _shortReportHash(value) {
  return value ? String(value).slice(0, 12) : "없음";
}
function _reportSearchText(report) {
  return [report.name, report.path, report.title, report.research_id, report.run_id].filter(Boolean).join(" ").toLowerCase();
}
function _fmtReportValue(value) {
  if (value === null || value === undefined || value === "") return "없음";
  if (Array.isArray(value)) return value.map(item => _fmtReportValue(item)).join(" · ");
  if (typeof value === "object") {
    try { return JSON.stringify(value); } catch (e) { return "구조화 메타데이터"; }
  }
  return String(value);
}



function V4Reports({ baseUrl }) {
  const [mode, setMode] = useState_rp7("reports"); // reports | wiki
  const [list, setList] = useState_rp7(null);
  const [err, setErr] = useState_rp7("");
  const [sel, setSel] = useState_rp7("");
  const [wiki, setWiki] = useState_rp7(null);
  const [wikiSel, setWikiSel] = useState_rp7("");
  const [wikiQuery, setWikiQuery] = useState_rp7("");
  const [wikiTotal, setWikiTotal] = useState_rp7(0);
  const [anchor, setAnchor] = useState_rp7("");
  const [wikiDoc, setWikiDoc] = useState_rp7(null);
  const [wikiIndexState, setWikiIndexState] = useState_rp7("idle"); // idle | loading | ready | error
  const [wikiError, setWikiError] = useState_rp7("");
  const wikiDetailControllerRef = useRef_rp7(null);
  const wikiSelRef = useRef_rp7("");
  const wikiReqRef = React.useRef(0);
  const modeTabRefs = useRef_rp7({});
  const [reportQuery, setReportQuery] = useState_rp7("");
  const [reportType, setReportType] = useState_rp7("all");
  const [reportStatus, setReportStatus] = useState_rp7("all");
  const [reportTrust, setReportTrust] = useState_rp7("all");
  const [reportLimit, setReportLimit] = useState_rp7(50);
  const [frameState, setFrameState] = useState_rp7("idle");
  const [tocOpen, setTocOpen] = useState_rp7(false);

  useEffect_rp7(() => {
    if (!baseUrl) { setList([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/reports", { signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (cancelled) return;
        const reports = Array.isArray(j && j.reports) ? j.reports : [];
        setList(reports);
        setSel(prev => reports.some(rp => rp.path === prev) ? prev : (reports.length ? reports[0].path : ""));
      })
      .catch(e => { if (!cancelled) { setList([]); setErr(String(e && e.message ? e.message : e)); } });
    return () => { cancelled = true; };
  }, [baseUrl]);

  useEffect_rp7(() => { // 서버 검색·페이지 제한: 930+ 문서 전량 DOM 렌더 금지.
    if (!baseUrl || mode !== "wiki") return undefined;
    let cancelled = false;
    const controller = new AbortController();
    setWiki(null);
    setWikiIndexState("loading");
    setWikiError("");
    const timer = setTimeout(() => {
      const query = wikiQuery.trim();
      const url = baseUrl + "/research_docs?limit=150" + (query ? "&q=" + encodeURIComponent(query) : "");
      fetch(url, { signal: controller.signal })
        .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
        .then(j => {
          if (cancelled) return;
          const docs = Array.isArray(j && j.docs) ? j.docs : [];
          setWiki(docs);
          setWikiTotal(Number(j && j.total) || docs.length);
          setWikiIndexState("ready");
          const nextWikiSel = docs.some(doc => doc.id === wikiSelRef.current)
            ? wikiSelRef.current
            : (docs.length ? docs[0].id : "");
          if (nextWikiSel !== wikiSelRef.current) {
            if (wikiDetailControllerRef.current) wikiDetailControllerRef.current.abort();
            setWikiDoc(null);
            wikiSelRef.current = nextWikiSel;
            setWikiSel(nextWikiSel);
          }
        })
        .catch(e => {
          if (!cancelled && e.name !== "AbortError") {
            setWiki([]);
            setWikiTotal(0);
            setWikiIndexState("error");
            setWikiError(String(e && e.message ? e.message : e));
          }
        });
    }, 180);
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [baseUrl, mode, wikiQuery]);

  useEffect_rp7(() => { // 선택 문서 마크다운(원문 그대로 <pre> 표시, 세대·취소 가드).
    if (!baseUrl || mode !== "wiki" || !wikiSel) {
      if (wikiDetailControllerRef.current) wikiDetailControllerRef.current.abort();
      wikiDetailControllerRef.current = null;
      setWikiDoc(null);
      return undefined;
    }
    const reqId = ++wikiReqRef.current;
    const controller = new AbortController();
    if (wikiDetailControllerRef.current) wikiDetailControllerRef.current.abort();
    wikiDetailControllerRef.current = controller;
    setWikiDoc(null);
    fetch(baseUrl + "/research_doc?id=" + encodeURIComponent(wikiSel), { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (reqId === wikiReqRef.current && !controller.signal.aborted) setWikiDoc(j);
      })
      .catch(e => {
        if (reqId === wikiReqRef.current && !controller.signal.aborted) {
          setWikiDoc({ available: false, reason: String(e && e.message ? e.message : e) });
        }
      });
    return () => {
      controller.abort();
      if (wikiDetailControllerRef.current === controller) wikiDetailControllerRef.current = null;
    };
  }, [baseUrl, mode, wikiSel]);
  useEffect_rp7(() => { setAnchor(""); }, [sel]);
  useEffect_rp7(() => { setReportLimit(50); }, [reportQuery, reportType, reportStatus, reportTrust]);
  useEffect_rp7(() => { setFrameState(sel ? "loading" : "idle"); }, [sel, anchor]);

  const reports = list || [];
  const selectedReport = reports.find(rp => rp.path === sel) || null;
  const toc = _reportToc(selectedReport);
  const viewUrl = sel ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";
  const frameSrc = viewUrl ? (anchor ? viewUrl + "#" + anchor : viewUrl) : "";
  const reportStatuses = [...new Set(reports.filter(rp => rp.registered === true).map(rp => rp.status).filter(Boolean))].sort();
  const reportTrusts = [...new Set(reports.filter(rp => rp.registered === true).map(rp => rp.trust).filter(Boolean))].sort();
  const filteredReports = reports.filter(rp => {
    const kind = _reportKind(rp);
    const query = reportQuery.trim().toLowerCase();
    return (!query || _reportSearchText(rp).includes(query))
      && (reportType === "all" || kind === reportType)
      && (reportStatus === "all" || rp.status === reportStatus)
      && (reportTrust === "all" || rp.trust === reportTrust);
  }).sort((a, b) => {
    const at = Date.parse(a.generated_at || a.date || "") || 0;
    const bt = Date.parse(b.generated_at || b.date || "") || 0;
    return bt - at || String(a.path || "").localeCompare(String(b.path || ""));
  });
  const catalogReports = filteredReports;
  const visibleReports = catalogReports.slice(0, Math.min(reportLimit, 250));
  const exampleReport = reports.find(rp => _reportKind(rp) === "run") || reports.find(rp => _reportKind(rp) === "step") || null;
  const wikiFiltered = (wiki || []).filter(d => {
    const q = wikiQuery.trim().toLowerCase();
    if (!q) return true;
    return ((d.title || "") + " " + (d.id || "") + " " + (d.category || "")).toLowerCase().includes(q);
  });
  const selectReport = (path) => { setSel(path); setAnchor(""); };
  const selectWiki = (id) => {
    if (id !== wikiSelRef.current) {
      if (wikiDetailControllerRef.current) wikiDetailControllerRef.current.abort();
      setWikiDoc(null);
      wikiSelRef.current = id;
      setWikiSel(id);
    }
  };
  const selectMode = (nextMode) => { setMode(nextMode); };
  const onModeKeyDown = (event) => {
    const modes = ["reports", "wiki"];
    const current = modes.indexOf(mode);
    let next = "";
    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = modes[(current + 1) % modes.length];
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = modes[(current + modes.length - 1) % modes.length];
    if (event.key === "Home") next = modes[0];
    if (event.key === "End") next = modes[modes.length - 1];
    if (!next) return;
    event.preventDefault();
    selectMode(next);
    requestAnimationFrame(() => { const tab = modeTabRefs.current[next]; if (tab) tab.focus(); });
  };
  const renderReportItem = (rp) => {
    const kind = _reportKind(rp);
    return (
      <button key={rp.path} className={"v4-reports-item" + (sel === rp.path ? " active" : "")} onClick={() => selectReport(rp.path)} title={rp.path}>
        <span className="v4-reports-name"><span className={"v4-report-kind " + kind}>{kind === "run" ? "run 종합" : kind === "step" ? "스텝" : kind === "legacy" ? "레거시" : "미등록"}</span>{rp.title || rp.name}</span>
        <span className="v4-reports-meta mono">{rp.research_id || rp.run_id || _fmtReportBytes(rp.bytes)} · {rp.status || rp.publication_status || "상태 없음"}</span>
      </button>
    );
  };

  return (
    <section className="v4-reports" aria-labelledby="v4-reports-heading">
      <div className="v4-reports-head">
        <h2 id="v4-reports-heading" className="panel-hd-title">Reports · 리포트/문서 뷰어</h2>
        <div className="v4-reports-head-actions">
          <div className="v4-reports-modes" role="tablist" aria-label="뷰 모드">
            <button id="v4-reports-mode-tab-reports" role="tab" aria-controls="v4-reports-panel-reports" aria-selected={mode === "reports"} tabIndex={mode === "reports" ? 0 : -1} ref={node => { modeTabRefs.current.reports = node; }} className={"btn ghost sm" + (mode === "reports" ? " active" : "")} onClick={() => selectMode("reports")} onKeyDown={onModeKeyDown}>HTML 리포트</button>
            <button id="v4-reports-mode-tab-wiki" role="tab" aria-controls="v4-reports-panel-wiki" aria-selected={mode === "wiki"} tabIndex={mode === "wiki" ? 0 : -1} ref={node => { modeTabRefs.current.wiki = node; }} className={"btn ghost sm" + (mode === "wiki" ? " active" : "")} onClick={() => selectMode("wiki")} onKeyDown={onModeKeyDown}>연구 문서(Wiki)</button>
          </div>
          <div className="v4-reports-actions">
            {exampleReport && (
              <button className="btn ghost sm v6-report-example" title="스텝 자동 리포트 표준양식 결과 예시 열기"
                      onClick={() => { selectMode("reports"); selectReport(exampleReport.path); }}>결과 보고서 예시</button>
            )}
            {(() => {
              const flat = catalogReports;
              const idx = flat.findIndex(rp => rp.path === sel);
              if (idx < 0 || flat.length < 2) return null;
              return (
                <span style={{ display: "inline-flex", gap: 4 }}>
                  <button className="btn ghost sm" disabled={idx <= 0} onClick={() => selectReport(flat[idx - 1].path)} title="이전 문서">◀ 이전</button>
                  <span className="mono" style={{ alignSelf: "center", fontSize: 11, color: "var(--ink-2)" }}>{idx + 1}/{flat.length}</span>
                  <button className="btn ghost sm" disabled={idx >= flat.length - 1} onClick={() => selectReport(flat[idx + 1].path)} title="다음 문서">다음 ▶</button>
                </span>
              );
            })()}
          </div>
        </div>
      </div>
      {mode === "reports" ? (
        <div id="v4-reports-panel-reports" role="tabpanel" aria-labelledby="v4-reports-mode-tab-reports">
          <p className="v4-reports-safe mono" role="note">읽기 전용 · 스크립트 차단(CSP default-src 'none' + sandbox iframe) · docs/ 하위 HTML 한정</p>
          <div className="v4-reports-body">
            <aside className="v4-reports-list" aria-label="리포트 목록">
              <div className="v4-reports-filters" aria-label="리포트 필터">
                <input className="toolbar-input" type="search" placeholder="제목 · 연구 · run 검색" value={reportQuery} onChange={e => setReportQuery(e.target.value)} aria-label="리포트 검색" />
                <select value={reportType} onChange={e => setReportType(e.target.value)} aria-label="리포트 종류"><option value="all">모든 종류</option><option value="run">run</option><option value="step">step</option><option value="legacy">legacy</option><option value="unregistered">미등록</option></select>
                <select value={reportStatus} onChange={e => setReportStatus(e.target.value)} aria-label="리포트 상태"><option value="all">모든 상태</option>{reportStatuses.map(value => <option key={value} value={value}>{value}</option>)}</select>
                <select value={reportTrust} onChange={e => setReportTrust(e.target.value)} aria-label="리포트 신뢰도"><option value="all">모든 신뢰도</option>{reportTrusts.map(value => <option key={value} value={value}>{value}</option>)}</select>
              </div>
              {list === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
              {list !== null && list.length === 0 && <div className="v4-reports-empty mono">리포트 없음{err ? " · " + err : ""}<div className="v4-reports-hint">docs/ 하위 *.html 생성 시 자동 표시</div></div>}
              {list !== null && list.length > 0 && catalogReports.length === 0 && <div className="v4-reports-empty mono">검색 결과 없음</div>}
              {visibleReports.length > 0 && <><div className="v6-report-group mono">최신순 리포트 · {visibleReports.length}/{catalogReports.length}건</div>{visibleReports.map(renderReportItem)}</>}
              {catalogReports.length > visibleReports.length && <button className="btn ghost sm" onClick={() => setReportLimit(limit => Math.min(limit + 50, 250))}>더 보기 · {visibleReports.length}/{catalogReports.length}</button>}
            </aside>
            <div className="v4-reports-main">
              {selectedReport && <section className="v4-report-provenance mono" aria-label="보고서 메타데이터와 출처">
                <span className={selectedReport.registered === true ? "v4-report-badge registered" : "v4-report-badge unregistered"}>{selectedReport.registered === true ? "등록됨" : "미등록·검증 불가"}</span>
                <span>type {_reportKind(selectedReport)}</span><span>status {selectedReport.status || "없음"}</span><span>trust {selectedReport.trust || "없음"}</span><span>research {selectedReport.research_id || "없음"}</span><span>run {selectedReport.run_id || "없음"}</span>
                <span>generation {selectedReport.generation ?? "없음"}</span><span>cycle {selectedReport.cycle ?? "없음"}</span>
                <span>publication {selectedReport.publication_status || "없음"}</span><span>generator {selectedReport.generator || "없음"}</span>
                <span>generated {selectedReport.generated_at || "없음"}</span><span>bytes {_fmtReportBytes(selectedReport.bytes) || "없음"}</span>
                <span>profile {_fmtReportValue(selectedReport.profile)}</span><span>limitations {_fmtReportValue(selectedReport.limitations || selectedReport.limits)}</span>
                <span>PDF {selectedReport.pdf_path ? "등록됨" : "없음"} {selectedReport.pdf_source_content_sha256 ? "· HTML 결속 검증" : ""}</span>
                <span title={_reportHash(selectedReport)}>hash {_shortReportHash(_reportHash(selectedReport))}</span><span>source {_shortReportHash(selectedReport.source_sha256)}</span>
              </section>}
              {selectedReport && selectedReport.registered === true && (selectedReport.decision || selectedReport.evidence) && (
                <section className="v4-report-insight" aria-label="보고서 결정과 근거 요약">
                  {selectedReport.decision && <div className="v4-report-decision"><b>결론·다음 행동</b><span>{_fmtReportValue(selectedReport.decision)}</span></div>}
                  {selectedReport.evidence && <div className="v4-report-evidence">
                    {Object.entries(selectedReport.evidence).slice(0, 10).map(([key, value]) => (
                      <span key={key}><i>{key}</i><b>{_fmtReportValue(value)}</b></span>
                    ))}
                  </div>}
                </section>
              )}
              <div className="v4-reports-view">
                {frameState === "loading" && <div className="v4-reports-empty mono" role="status">리포트 로드 중…</div>}
                {frameState === "error" && <div className="v4-reports-empty mono" role="alert">리포트를 불러오지 못했습니다. 등록된 원본과 연결 상태를 확인하세요.</div>}
                {viewUrl ? <iframe key={sel} className="v4-reports-frame" src={frameSrc} sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" onLoad={() => setFrameState("ready")} onError={() => setFrameState("error")} /> : <div className="v4-reports-empty mono">리포트를 선택하세요</div>}
              </div>
            </div>
            <div className={"v4-reports-toc-slot" + (tocOpen ? " open" : "")}>
              <button className="btn ghost sm v4-reports-toc-toggle" onClick={() => setTocOpen(open => !open)} aria-expanded={tocOpen} aria-controls="v4-reports-toc">{tocOpen ? "목차 접기" : "목차 열기"}</button>
              {tocOpen && (toc && toc.length > 0 ? (
                <nav id="v4-reports-toc" className="v4-reports-toc" aria-label="리포트 목차"><div className="v6-report-group mono">목차 · {toc.length}</div>{toc.map(t => <button key={t.id} className={"v4-toc-item lvl" + t.lvl + (anchor === t.id ? " active" : "")} onClick={() => setAnchor(t.id)} title={t.label}>{t.label}</button>)}</nav>
              ) : selectedReport && <aside id="v4-reports-toc" className="v4-reports-toc v4-reports-toc-empty" aria-label="리포트 목차 상태">{toc === null ? "목차 없음 · 레거시 리포트 메타데이터 미제공" : "목차 없음 · 리포트 메타데이터에 섹션 없음"}</aside>)}
            </div>
          </div>
        </div>
      ) : (
        <div id="v4-reports-panel-wiki" role="tabpanel" aria-labelledby="v4-reports-mode-tab-wiki">
          <p className="v4-reports-safe mono" role="note">읽기 전용 · 원문 마크다운 불변(pre 텍스트 표시) · /research_docs 색인</p>
          <div className="v4-reports-body">
            <aside className="v4-reports-list" aria-label="연구 문서 목록">
              <input className="toolbar-input v6-wiki-search" type="search" placeholder="검색 (제목·경로·분류)"
                     value={wikiQuery} onChange={e => setWikiQuery(e.target.value)}
                     aria-label="연구 문서 검색" />
              {wikiIndexState === "loading" && <div className="v4-reports-empty mono">불러오는 중…</div>}
              {wikiIndexState === "error" && <div className="v4-reports-empty mono">문서 색인 로드 실패 · {wikiError}</div>}
              {wikiIndexState === "ready" && wikiFiltered.length === 0 && <div className="v4-reports-empty mono">{wikiQuery ? "검색 결과 없음 · " + wikiQuery : "연구 문서 없음"}</div>}
              {wikiIndexState === "ready" && wikiFiltered.length > 0 && (
                <div className="v6-report-group mono">{wikiQuery ? "검색 결과" : "문서"} {wikiFiltered.length}건 / 전체 {wikiTotal}건 · 최대 150건 표시</div>
              )}
              {wikiIndexState === "ready" && wikiFiltered.map(d => (
                <button key={d.id} className={"v4-reports-item" + (wikiSel === d.id ? " active" : "")} onClick={() => selectWiki(d.id)} title={d.id}>
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
        </div>
      )}
    </section>
  );
}

Object.assign(window, { V4Reports });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Reports };
