/* v4-reports.jsx — V4 "Reports" tab: structured report manifest + safe HTML viewer.
 *   Security (§10-5, UXR-P7): backend /reports/view blocks scripts with CSP default-src 'none' and
 *   this tab renders only inside sandbox="" iframe (no scripts, same-origin, forms, or popups).
 *   → inline JS in reports never executes; manifest metadata is rendered as escaped React text.
 */
// dual-safe ESM. KEEP hooks alias on ONE physical line.
const { useState: useState_rp7, useEffect: useEffect_rp7, useRef: useRef_rp7 } = React;
// dual-safe ESM import (esbuild bundle path). KEEP each on ONE physical line.
import { ResearchWikiPanel } from "./research-wiki.jsx";

function _fmtReportBytes(n) {
  if (!Number.isFinite(n)) return "";
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + " KB";
  return (n / (1024 * 1024)).toFixed(1) + " MB";
}

function _shortHash(value) {
  return typeof value === "string" && value.length > 12 ? value.slice(0, 12) + "…" : (value || "—");
}

function isReport(row) {
  return Boolean(row && typeof row === "object" && typeof row.path === "string" && row.path &&
    typeof row.name === "string" && Number.isFinite(row.bytes));
}

function isManifestReport(row) {
  return Boolean(isReport(row) && row.manifest === true &&
    typeof row.title === "string" && typeof row.kind === "string" &&
    typeof row.research_id === "string" && row.research_id &&
    typeof row.step_id === "string" && typeof row.html_sha256 === "string" &&
    typeof row.hash_status === "string" && typeof row.trust === "string" &&
    typeof row.missing === "boolean" && typeof row.stale === "boolean" &&
    Array.isArray(row.source_paths) && Array.isArray(row.links) &&
    row.source_paths.every(v => typeof v === "string") &&
    row.links.every(v => typeof v === "string"));
}

function isManifestEnvelope(value) {
  return Boolean(value && typeof value === "object" &&
    value.schema === "stom-research-report-manifest-v1" &&
    typeof value.available === "boolean" &&
    Array.isArray(value.reports) && Array.isArray(value.errors));
}

function _manifestGroups(rows) {
  const map = new Map();
  rows.forEach(row => {
    if (!map.has(row.research_id)) map.set(row.research_id, { research_id: row.research_id, items: [] });
    map.get(row.research_id).items.push(row);
  });
  return Array.from(map.values());
}

function _reportStatusText(row) {
  const states = [];
  if (row.missing) states.push("missing");
  if (row.stale) states.push("stale");
  if (row.hash_status) states.push("hash:" + row.hash_status);
  return states.length ? states.join(" · ") : "fresh";
}

function _errorText(error) {
  if (!error || typeof error !== "object") return "manifest_error";
  const parts = [String(error.type || "manifest_error")];
  if (typeof error.field === "string") parts.push(error.field);
  if (typeof error.path === "string") parts.push(error.path);
  return parts.join(" · ");
}

function _renderReportButton(rp, sel, selectReport, manifestMode) {
  const label = manifestMode ? (rp.title || rp.name) : rp.name;
  const meta = manifestMode ? [rp.kind, _fmtReportBytes(rp.bytes), rp.trust].filter(Boolean).join(" · ") : _fmtReportBytes(rp.bytes);
  const classes = "v4-reports-item" + (sel === rp.path ? " active" : "") +
    (manifestMode && rp.missing ? " missing" : "") + (manifestMode && rp.stale ? " stale" : "");
  return (
    <button key={rp.path}
            className={classes}
            onClick={() => selectReport(rp.path)} title={rp.path}>
      <span className="v4-reports-name">{manifestMode && rp.step_id ? rp.step_id + " · " : ""}{label}</span>
      <span className="v4-reports-meta mono">{meta}</span>
      {manifestMode && <span className="v4-reports-badges mono">{_reportStatusText(rp)}</span>}
    </button>
  );
}

function V4Reports({ baseUrl }) {
  const [list, setList] = useState_rp7(null); // null=loading, []=empty
  const [manifest, setManifest] = useState_rp7(null);
  const [err, setErr] = useState_rp7("");
  const [sel, setSel] = useState_rp7("");
  const [listedBase, setListedBase] = useState_rp7("");
  const generationRef = useRef_rp7(0);
  const selectionRef = useRef_rp7("");
  const baseRef = useRef_rp7(baseUrl);
  baseRef.current = baseUrl;

  useEffect_rp7(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    const priorSelection = selectionRef.current;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 6000);

    setList(baseUrl ? null : []);
    setManifest(null);
    setListedBase("");
    setErr("");
    setSel("");
    selectionRef.current = "";

    if (!baseUrl) {
      clearTimeout(timeout);
      return () => controller.abort();
    }

    fetch(baseUrl + "/reports", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        const reports = Array.isArray(j && j.reports) ? j.reports.filter(isReport) : [];
        const nextManifest = isManifestEnvelope(j && j.manifest) ? j.manifest : null;
        const manifestReports = nextManifest && nextManifest.available ? nextManifest.reports.filter(isManifestReport) : [];
        const selectionPool = manifestReports.length ? manifestReports : reports;
        const retained = selectionPool.some(rp => rp.path === priorSelection) ? priorSelection : "";
        const nextSelection = retained || (selectionPool.length ? selectionPool[0].path : "");
        setList(reports);
        setManifest(nextManifest);
        setListedBase(baseUrl);
        setSel(nextSelection);
        selectionRef.current = nextSelection;
      })
      .catch(e => {
        if (controller.signal.aborted || generation !== generationRef.current || baseUrl !== baseRef.current) return;
        setList([]);
        setManifest(null);
        setErr(String(e && e.message ? e.message : e));
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [baseUrl]);

  const selectReport = path => {
    setSel(path);
    selectionRef.current = path;
  };
  const ownsSelection = Boolean(baseUrl && listedBase === baseUrl && Array.isArray(list) && list.some(rp => rp.path === sel));
  const manifestRows = manifest && manifest.available && Array.isArray(manifest.reports) ? manifest.reports.filter(isManifestReport) : [];
  const manifestErrors = manifest && Array.isArray(manifest.errors) ? manifest.errors : [];
  const usingManifest = manifestRows.length > 0;
  const selectedManifest = ownsSelection && usingManifest ? (manifestRows.find(rp => rp.path === sel) || null) : null;
  const viewUrl = ownsSelection ? (baseUrl + "/reports/view?path=" + encodeURIComponent(sel)) : "";
  const groups = usingManifest ? _manifestGroups(manifestRows) : [];

  return (
    <section className="v4-reports" aria-labelledby="v4-reports-heading">
      <h2 id="v4-reports-heading" className="panel-hd-title">Reports · 리포트 뷰어</h2>
      <p className="v4-reports-safe mono" role="note">
        읽기 전용 · 스크립트 차단(CSP default-src 'none' + sandbox iframe) · docs/ 하위 HTML 한정
      </p>
      <div className="v4-reports-body">
        <aside className="v4-reports-list" aria-label="리포트 목록">
          {list === null && <div className="v4-reports-empty mono">불러오는 중…</div>}
          {list !== null && manifestErrors.length > 0 && (
            <div className="v4-reports-manifest-errors mono" title="Invalid manifest entries are dropped before display">
              manifest errors: {manifestErrors.slice(0, 3).map(_errorText).join(" / ")}{manifestErrors.length > 3 ? " +" + (manifestErrors.length - 3) : ""}
            </div>
          )}
          {list !== null && list.length === 0 && (
            <div className="v4-reports-empty mono">
              리포트 없음{err ? " · " + err : ""}
              <div className="v4-reports-hint">docs/ 하위 *.html 생성 시 자동 표시</div>
            </div>
          )}
          {list !== null && list.length > 0 && usingManifest && (
            <>
              <div className="v4-reports-manifest-head mono">
                <b>manifest v1</b>
                <span>{manifestRows.length} structured · {manifest.writer || "manual-offline"}</span>
              </div>
              {groups.map(group => (
                <div className="v4-reports-group" key={group.research_id}>
                  <div className="v4-reports-group-title mono">{group.research_id}</div>
                  {group.items.map(rp => _renderReportButton(rp, sel, selectReport, true))}
                </div>
              ))}
            </>
          )}
          {list !== null && list.length > 0 && !usingManifest && list.map(rp => _renderReportButton(rp, sel, selectReport, false))}
        </aside>
        <div className="v4-reports-view">
          {selectedManifest && (
            <div className="v4-reports-detail">
              <div className="v4-reports-detail-head">
                <b>{selectedManifest.title}</b>
                <span className="mono">{selectedManifest.research_id}{selectedManifest.step_id ? " / " + selectedManifest.step_id : ""}</span>
              </div>
              <div className="v4-reports-detail-grid mono">
                <span>trust: {selectedManifest.trust}</span>
                <span>status: {_reportStatusText(selectedManifest)}</span>
                <span title={selectedManifest.html_sha256}>html: {_shortHash(selectedManifest.html_sha256)}</span>
                <span>bytes: {_fmtReportBytes(selectedManifest.bytes)}</span>
              </div>
              {selectedManifest.source_paths.length > 0 && (
                <div className="v4-reports-provenance">
                  <span className="mono">provenance</span>
                  {selectedManifest.source_paths.slice(0, 6).map(src => (
                    <code key={src} title={selectedManifest.source_sha256 && selectedManifest.source_sha256[src] ? selectedManifest.source_sha256[src] : ""}>
                      {src}{selectedManifest.source_sha256 && selectedManifest.source_sha256[src] ? " · " + _shortHash(selectedManifest.source_sha256[src]) : ""}
                    </code>
                  ))}
                </div>
              )}
              {selectedManifest.links.length > 0 && (
                <div className="v4-reports-provenance">
                  <span className="mono">allowlisted links</span>
                  {selectedManifest.links.slice(0, 4).map(link => <code key={link}>{link}</code>)}
                </div>
              )}
            </div>
          )}
          {viewUrl ? (
            <iframe key={viewUrl} className="v4-reports-frame" src={viewUrl}
                    sandbox="" referrerPolicy="no-referrer" title={"리포트: " + sel} loading="lazy" />
          ) : (
            <div className="v4-reports-empty mono">리포트를 선택하세요</div>
          )}
        </div>
      </div>
      <section className="v4-reports-wiki v4-cjk-safe" aria-labelledby="v4-reports-wiki-heading">
        <h2 id="v4-reports-wiki-heading" className="panel-hd-title">Research Wiki · 읽기 전용 참고 문서</h2>
        <ResearchWikiPanel baseUrl={baseUrl} wsStatus="na" />
      </section>
    </section>
  );
}

Object.assign(window, { V4Reports });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Reports };
