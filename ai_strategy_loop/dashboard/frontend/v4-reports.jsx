/* v4-reports.jsx — V4 "Reports" 탭: 리포트 HTML 안전 뷰어.
 *   보안(§10-5, UXR-P7): 백엔드 /reports/view 가 CSP default-src 'none' 로 스크립트를 차단하고,
 *   여기서 sandbox="" iframe(스크립트·동일출처·폼·팝업 전면 차단)로 이중 방어한다.
 *   → inline JS 를 포함한 리포트(alpha_lab reporting 산출물 등)도 실행되지 않는다.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_rp7, useEffect: useEffect_rp7, useRef: useRef_rp7 } = React;
import { sortReportsNewest } from "./report-order.mjs";
import { ReportSummaryBoard } from "./report-summary-board.jsx";

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
  if (_reportClassification(report) === "legacy_static") return "legacy";
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
  return [report.name, report.path, report.title, report.research_id, report.run_id, report.template_id, report.theme].filter(Boolean).join(" ").toLowerCase();
}
function _fmtReportValue(value) {
  if (value === null || value === undefined || value === "") return "없음";
  if (Array.isArray(value)) return value.map(item => _fmtReportValue(item)).join(" · ");
  if (typeof value === "object") {
    try { return JSON.stringify(value); } catch (e) { return "구조화 메타데이터"; }
  }
  return String(value);
}
function _reportClassification(report) {
  return (report && report.catalog_classification) || "unverifiable";
}
function _reportClassificationLabel(value) {
  return {
    canonical_registered: "정본 등록",
    source_backed_regenerable: "소스 근거 재생성 가능",
    legacy_static: "레거시 정적",
    unverifiable: "검증 불가",
  }[value] || value;
}



/* v5.13.2 — 필터 칩 그룹. 콤보(select)를 대체한다: 값이 전부 보이고 한 번에 눌린다.
   options=[[value,label],…]. counts 를 주면 칩에 건수를 함께 찍는다.
   선택지가 9개 이상이면 칩이 목록 영역을 잡아먹으므로 그때만 콤보로 자동 후퇴한다. */
function _RptChips({ step, title, value, onPick, options, counts }) {
  const opts = (options || []).filter(o => Array.isArray(o) && o[0] != null);
  if (opts.length <= 1) return null;
  const wide = opts.length >= 9;
  return (
    <div className={"v4-report-filter-step" + (wide ? " wide" : "")}>
      <b><i>{step}</i> {title}</b>
      {wide ? (
        <select value={value} onChange={e => onPick(e.target.value)} aria-label={title}>
          {opts.map(([v, label]) => <option key={v} value={v}>{label}</option>)}
        </select>
      ) : (
        <div className="v4-report-chips" role="radiogroup" aria-label={title}>
          {opts.map(([v, label]) => (
            <button key={v} type="button" role="radio" aria-checked={value === v}
                    className={"v4-report-chip" + (value === v ? " active" : "")}
                    onClick={() => onPick(v)} title={title + ": " + label}>
              {label}{counts && counts[v] != null ? <em>{counts[v]}</em> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
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
  const [reportClassification, setReportClassification] = useState_rp7("all");
  const [reportIntegrity, setReportIntegrity] = useState_rp7("all");
  const [reportTemplate, setReportTemplate] = useState_rp7("all");
  const [reportTheme, setReportTheme] = useState_rp7("all");
  const [reportLimit, setReportLimit] = useState_rp7(50);
  const [frameState, setFrameState] = useState_rp7("idle");
  const [tocOpen, setTocOpen] = useState_rp7(false);
  const [reportView, setReportView] = useState_rp7("summary");

  useEffect_rp7(() => {
    if (!baseUrl) { setList([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/reports", { signal: AbortSignal.timeout(6000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (cancelled) return;
        const reports = sortReportsNewest(Array.isArray(j && j.reports) ? j.reports : []);
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
  useEffect_rp7(() => { setReportLimit(50); }, [reportQuery, reportType, reportStatus, reportTrust, reportClassification, reportIntegrity, reportTemplate, reportTheme]);
  useEffect_rp7(() => { setFrameState(sel ? "loading" : "idle"); }, [sel, anchor]);

  const reports = list || [];
  const selectedReport = reports.find(rp => rp.path === sel) || null;
  // v5.11.3 — 보고서 메타데이터에 없는 지표는 같은 run 의 연구 기록에서 연결한다.
  //   선택된 보고서의 run 만 조회하므로 목록 전체를 끌어오지 않는다.
  const selectedRunId = selectedReport && selectedReport.run_id ? String(selectedReport.run_id) : "";
  const [runMeta, setRunMeta] = useState_rp7(null);
  useEffect_rp7(() => {
    setRunMeta(null);
    if (!baseUrl || !selectedRunId) return undefined;
    const controller = new AbortController();
    fetch(baseUrl + "/runs?limit=500", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        const hit = ((j && j.runs) || []).find(r => r && String(r.run_id) === selectedRunId);
        if (!controller.signal.aborted && hit) setRunMeta(hit);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [baseUrl, selectedRunId]);
  const toc = _reportToc(selectedReport);
  const viewUrl = sel ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";
  const frameSrc = viewUrl ? (anchor ? viewUrl + "#" + anchor : viewUrl) : "";
  const reportStatuses = [...new Set(reports.filter(rp => rp.registered === true).map(rp => rp.status).filter(Boolean))].sort();
  const reportTrusts = [...new Set(reports.filter(rp => rp.registered === true).map(rp => rp.trust).filter(Boolean))].sort();
  const reportClassifications = [...new Set(reports.map(_reportClassification))].sort();
  const reportIntegrities = [...new Set(reports.map(rp => rp.integrity_status).filter(Boolean))].sort();
  const reportTemplates = [...new Set(reports.map(rp => rp.template_id).filter(Boolean))].sort();
  const reportThemes = [...new Set(reports.map(rp => rp.theme).filter(Boolean))].sort();
  const reportCounts = reports.reduce((counts, rp) => {
    const classification = _reportClassification(rp);
    counts[classification] = (counts[classification] || 0) + 1;
    return counts;
  }, {});
  const filteredReports = sortReportsNewest(reports.filter(rp => {
    const kind = _reportKind(rp);
    const query = reportQuery.trim().toLowerCase();
    return (!query || _reportSearchText(rp).includes(query))
      && (reportType === "all" || kind === reportType)
      && (reportStatus === "all" || rp.status === reportStatus)
      && (reportTrust === "all" || rp.trust === reportTrust)
      && (reportClassification === "all" || _reportClassification(rp) === reportClassification)
      && (reportIntegrity === "all" || rp.integrity_status === reportIntegrity)
      && (reportTemplate === "all" || rp.template_id === reportTemplate)
      && (reportTheme === "all" || rp.theme === reportTheme);
  }));
  const catalogReports = filteredReports;
  const visibleReports = catalogReports.slice(0, Math.min(reportLimit, 250));
  const exampleReport = reports.find(rp => _reportKind(rp) === "run") || reports.find(rp => _reportKind(rp) === "step") || null;
  const wikiFiltered = (wiki || []).filter(d => {
    const q = wikiQuery.trim().toLowerCase();
    if (!q) return true;
    return ((d.title || "") + " " + (d.id || "") + " " + (d.category || "")).toLowerCase().includes(q);
  });
  const selectReport = (path) => { setSel(path); setAnchor(""); setReportView("summary"); };
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
        <span className="v4-reports-name"><span className={"v4-report-kind " + kind}>{_reportClassificationLabel(_reportClassification(rp))}</span>{rp.title || rp.name}</span>
        <span className="v4-reports-meta mono">{rp.research_id || rp.run_id || _fmtReportBytes(rp.bytes)} · template {rp.template_id || "legacy"} · theme {rp.theme || "문서 기본값"} · {rp.integrity_status || "상태 없음"}</span>
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
                <div className="v4-report-filter-step wide"><b><i>1</i> 검색</b><input className="toolbar-input" type="search" placeholder="제목 · 연구 · run 검색" value={reportQuery} onChange={e => setReportQuery(e.target.value)} aria-label="리포트 검색" /></div>
                {/* v5.13.2 — 콤보(select) 전량을 버튼 칩으로 교체(이전 요청 미반영분).
                    콤보는 "열고 → 훑고 → 고르는" 3동작이지만 칩은 한 번에 눌린다.
                    선택지가 8개를 넘으면 칩이 목록을 밀어내므로 그때만 콤보로 남긴다. */}
                <_RptChips step="2" title="문서 종류" value={reportType} onPick={setReportType}
                           options={[["all", "전체"], ["run", "run"], ["step", "step"], ["legacy", "legacy"], ["unregistered", "미등록"]]} />
                <_RptChips step="3" title="상태" value={reportStatus} onPick={setReportStatus}
                           options={[["all", "전체"], ...reportStatuses.map(v => [v, v])]} />
                <_RptChips step="4" title="정본 분류" value={reportClassification} onPick={setReportClassification}
                           options={[["all", "전체"], ...reportClassifications.map(v => [v, _reportClassificationLabel(v)])]}
                           counts={reportCounts} />
                <_RptChips step="5" title="검증" value={reportIntegrity} onPick={setReportIntegrity}
                           options={[["all", "전체"], ...reportIntegrities.map(v => [v, v])]} />
                <_RptChips step="6" title="템플릿" value={reportTemplate} onPick={setReportTemplate}
                           options={[["all", "전체"], ...reportTemplates.map(v => [v, v])]} />
                <_RptChips step="7" title="문서 테마" value={reportTheme} onPick={setReportTheme}
                           options={[["all", "전체"], ...reportThemes.map(v => [v, v])]} />
              </div>
              {list === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
              {list !== null && list.length === 0 && <div className="v4-reports-empty mono">리포트 없음{err ? " · " + err : ""}<div className="v4-reports-hint">docs/ 하위 *.html 생성 시 자동 표시</div></div>}
              {list !== null && list.length > 0 && catalogReports.length === 0 && <div className="v4-reports-empty mono">검색 결과 없음</div>}
              {list !== null && list.length > 0 && <div className="v6-report-group mono">분류 · {reportClassifications.map(value => `${_reportClassificationLabel(value)} ${reportCounts[value] || 0}건`).join(" · ")}</div>}
              {visibleReports.length > 0 && <><div className="v6-report-group mono">최신순 리포트 · {visibleReports.length}/{catalogReports.length}건</div>{visibleReports.map(renderReportItem)}</>}
              {catalogReports.length > visibleReports.length && <button className="btn ghost sm" onClick={() => setReportLimit(limit => Math.min(limit + 50, 250))}>더 보기 · {visibleReports.length}/{catalogReports.length}</button>}
            </aside>
            <div className="v4-reports-main">
              {/* v5.13.0(F1) — 순서대로 누르는 단계식 버튼: ① 요약 확인 → ② 보고서 열람 → ③ 출처 검증. */}
              {selectedReport && <div className="v4-report-view-tabs v4-report-steps" role="tablist" aria-label="선택 보고서 보기 순서">
                <button role="tab" aria-selected={reportView === "summary"} className={"v4-report-step" + (reportView === "summary" ? " active" : "")} onClick={() => setReportView("summary")}>
                  <i>1</i><span><b>결과 Summary</b><small>핵심 지표 먼저</small></span>
                </button>
                <span className="v4-report-step-arrow" aria-hidden="true">→</span>
                <button role="tab" aria-selected={reportView === "html"} className={"v4-report-step" + (reportView === "html" ? " active" : "")} onClick={() => setReportView("html")}>
                  <i>2</i><span><b>HTML 보고서</b><small>전체 차트·표 열람</small></span>
                </button>
                <span className="v4-report-step-arrow" aria-hidden="true">→</span>
                <button role="tab" aria-selected={reportView === "provenance"} className={"v4-report-step" + (reportView === "provenance" ? " active" : "")} onClick={() => setReportView("provenance")}>
                  <i>3</i><span><b>정본 · 출처</b><small>원본 검증(선택)</small></span>
                </button>
              </div>}
              {reportView === "summary" && <ReportSummaryBoard report={selectedReport} runMeta={runMeta} />}
              {reportView === "provenance" && selectedReport && <section className="v4-report-provenance mono" aria-label="보고서 메타데이터와 출처">
                <header><span className={"v4-report-badge " + _reportClassification(selectedReport)}>{_reportClassificationLabel(_reportClassification(selectedReport))}</span><b>정본 등록 · 검증 · 생성 출처</b></header>
                {/* v5.13.0(F3) — "정본"이 무슨 뜻인지부터 밝힌다. */}
                <p style={{ margin: "0 0 10px", fontSize: 12, lineHeight: 1.6, color: "var(--ink-2)" }}>
                  <b style={{ color: "var(--ink-0)" }}>정본(正本)</b> = 시스템이 등록하고 해시로 검증한 <b>원본 보고서</b>라는 뜻입니다.
                  도서관 원본 대장과 같아서, 이 화면은 지금 보는 보고서가 <b>어디서(어느 연구·세대) 어떻게(어느 생성기·템플릿) 만들어졌고
                  위·변조 없이 보관 중인지</b>를 보여줍니다. 값이 "없음"이면 그 정보가 발행되지 않았다는 뜻입니다.
                </p>
                <div className="v4-report-details">
                  <div><b>분류 사유</b><span>{selectedReport.catalog_reason || "없음"}</span></div>
                  <div><b>검증</b><span>{selectedReport.integrity_status || "없음"}</span></div>
                  <div><b>오류</b><span>{selectedReport.integrity_error || "없음"}</span></div>
                  <div><b>종류 · 상태</b><span>{_reportKind(selectedReport)} · {selectedReport.status || "없음"}</span></div>
                  <div><b>신뢰</b><span>{selectedReport.trust || "없음"}</span></div>
                  <div><b>연구</b><span>{selectedReport.research_id || "없음"}</span></div>
                  <div><b>run</b><span>{selectedReport.run_id || "없음"}</span></div>
                  <div><b>세대 · cycle</b><span>{selectedReport.generation ?? "없음"} · {selectedReport.cycle ?? "없음"}</span></div>
                  <div><b>발행</b><span>{selectedReport.publication_status || "없음"}</span></div>
                  <div><b>생성기</b><span>{selectedReport.generator || "없음"}</span></div>
                  <div><b>템플릿 · 테마</b><span>{selectedReport.template_id || "legacy/미제공"} · {selectedReport.theme || "문서 기본값"}</span></div>
                  <div><b>렌더러</b><span>{selectedReport.renderer_version || "legacy/미제공"}</span></div>
                  <div><b>생성 시각 · 크기</b><span>{selectedReport.generated_at || "없음"} · {_fmtReportBytes(selectedReport.bytes) || "없음"}</span></div>
                  <div className="wide"><b>출처</b><span>{_fmtReportValue(selectedReport.provenance)}</span></div>
                  <div className="wide"><b>프로필</b><span>{_fmtReportValue(selectedReport.profile)}</span></div>
                  <div className="wide caution"><b>제약·주의</b><span>{_fmtReportValue(selectedReport.limitations || selectedReport.limits)}</span></div>
                  <div><b>PDF</b><span>{selectedReport.pdf_path ? "등록됨" : "없음"} {selectedReport.pdf_source_content_sha256 ? "· HTML 결속 검증" : ""}</span></div>
                  <div><b>hash · source</b><span title={_reportHash(selectedReport)}>{_shortReportHash(_reportHash(selectedReport))} · {_shortReportHash(selectedReport.source_sha256)}</span></div>
                  <div className="wide"><b>재생성</b><span>{selectedReport.catalog_classification === "source_backed_regenerable" ? "원천 근거가 있어 재생성 가능" : selectedReport.catalog_classification === "legacy_static" ? "레거시 정적 파일은 자동 재생성·덮어쓰지 않음" : "정본 등록/검증 상태를 확인"}</span></div>
                </div>
              </section>}
              {reportView === "provenance" && selectedReport && selectedReport.registered === true && (selectedReport.decision || selectedReport.evidence) && (
                <section className="v4-report-insight" aria-label="보고서 결정과 근거 요약">
                  {selectedReport.decision && <div className="v4-report-decision"><b>결론·다음 행동</b><span>{_fmtReportValue(selectedReport.decision)}</span></div>}
                  {selectedReport.evidence && <div className="v4-report-evidence">
                    {Object.entries(selectedReport.evidence).slice(0, 10).map(([key, value]) => (
                      <span key={key}><i>{key}</i><b>{_fmtReportValue(value)}</b></span>
                    ))}
                  </div>}
                </section>
              )}
              {reportView === "html" && <div className="v4-reports-view">
                {frameState === "loading" && <div className="v4-reports-empty mono" role="status">리포트 로드 중…</div>}
                {frameState === "error" && <div className="v4-reports-empty mono" role="alert">리포트를 불러오지 못했습니다. 등록된 원본과 연결 상태를 확인하세요.</div>}
                {viewUrl ? <iframe key={sel} className="v4-reports-frame" src={frameSrc} sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" onLoad={() => setFrameState("ready")} onError={() => setFrameState("error")} /> : <div className="v4-reports-empty mono">리포트를 선택하세요</div>}
              </div>}
            </div>
            {reportView === "html" && <div className={"v4-reports-toc-slot" + (tocOpen ? " open" : "")}>
              <button className="btn ghost sm v4-reports-toc-toggle" onClick={() => setTocOpen(open => !open)} aria-expanded={tocOpen} aria-controls="v4-reports-toc">{tocOpen ? "목차 접기" : "목차 열기"}</button>
              {tocOpen && (toc && toc.length > 0 ? (
                <nav id="v4-reports-toc" className="v4-reports-toc" aria-label="리포트 목차"><div className="v6-report-group mono">목차 · {toc.length}</div>{toc.map(t => <button key={t.id} className={"v4-toc-item lvl" + t.lvl + (anchor === t.id ? " active" : "")} onClick={() => setAnchor(t.id)} title={t.label}>{t.label}</button>)}</nav>
              ) : selectedReport && <aside id="v4-reports-toc" className="v4-reports-toc v4-reports-toc-empty" aria-label="리포트 목차 상태">{toc === null ? "목차 없음 · 레거시 리포트 메타데이터 미제공" : "목차 없음 · 리포트 메타데이터에 섹션 없음"}</aside>)}
            </div>}
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
