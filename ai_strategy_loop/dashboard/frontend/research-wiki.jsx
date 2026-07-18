/* Read-only research wiki/documentation browser */
const { useState: useState_rw, useEffect: useEffect_rw, useMemo: useMemo_rw, useRef: useRef_rw, useCallback: useCallback_rw } = React;

const RESEARCH_WIKI_CATEGORIES = [
  { key: "wiki", label: "Methods" },
  { key: "good_results", label: "Good Results" },
  { key: "condition_research", label: "Metrics" },
  { key: "update_log", label: "Failed Candidates" },
  { key: "next", label: "Next Experiments" },
];

function wikiLabel(category) {
  const found = RESEARCH_WIKI_CATEGORIES.find(c => c.key === category);
  return found ? found.label : category || "Docs";
}

function isWikiRow(row) {
  return Boolean(row && typeof row === "object" && typeof row.id === "string" && row.id &&
    typeof row.title === "string" && typeof row.category === "string" && Number.isFinite(row.size));
}

function isSelectedWikiDoc(value, selectedId) {
  return Boolean(value && typeof value === "object" && value.id === selectedId &&
    (value.available === false || (value.available === true && typeof value.title === "string" &&
      typeof value.category === "string" && typeof value.markdown === "string")));
}

function ResearchWikiPanel({ baseUrl, wsStatus }) {
  const [docs, setDocs] = useState_rw([]);
  const [selectedId, setSelectedId] = useState_rw("");
  const [doc, setDoc] = useState_rw(null);
  const [listLoading, setListLoading] = useState_rw(false);
  const [listErr, setListErr] = useState_rw("");
  const [detailLoading, setDetailLoading] = useState_rw(false);
  const [detailErr, setDetailErr] = useState_rw("");
  const [listedBase, setListedBase] = useState_rw("");
  const listGenerationRef = useRef_rw(0);
  const detailGenerationRef = useRef_rw(0);
  const listControllerRef = useRef_rw(null);
  const detailControllerRef = useRef_rw(null);
  const selectedIdRef = useRef_rw("");
  const baseRef = useRef_rw(baseUrl);
  baseRef.current = baseUrl;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const grouped = useMemo_rw(() => {
    const out = {};
    for (const row of docs) {
      const key = row.category || "Docs";
      if (!out[key]) out[key] = [];
      out[key].push(row);
    }
    return out;
  }, [docs]);

  const loadDocs = useCallback_rw(() => {
    const generation = listGenerationRef.current + 1;
    listGenerationRef.current = generation;
    const priorSelection = selectedIdRef.current;
    if (listControllerRef.current) listControllerRef.current.abort();
    if (detailControllerRef.current) detailControllerRef.current.abort();
    detailGenerationRef.current += 1;

    const controller = new AbortController();
    listControllerRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 3500);
    setDocs([]);
    setListedBase("");
    setSelectedId("");
    selectedIdRef.current = "";
    setDoc(null);
    setListErr("");
    setDetailErr("");
    setDetailLoading(false);

    if (isDemo || !baseUrl) {
      setListLoading(false);
      clearTimeout(timeout);
      return () => controller.abort();
    }

    setListLoading(true);
    fetch(baseUrl + "/research_docs", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (controller.signal.aborted || generation !== listGenerationRef.current || baseUrl !== baseRef.current) return;
        const rows = Array.isArray(j && j.docs) ? j.docs.filter(isWikiRow) : [];
        const retained = rows.some(row => row.id === priorSelection) ? priorSelection : "";
        const preferred = rows.find(row => row.category === "wiki") || rows[0];
        const nextSelectedId = retained || (preferred ? preferred.id : "");
        setDocs(rows);
        setListedBase(baseUrl);
        setSelectedId(nextSelectedId);
        selectedIdRef.current = nextSelectedId;
      })
      .catch(e => {
        if (controller.signal.aborted || generation !== listGenerationRef.current || baseUrl !== baseRef.current) return;
        setDocs([]);
        setListErr(String(e && e.message ? e.message : e));
      })
      .finally(() => {
        clearTimeout(timeout);
        if (!controller.signal.aborted && generation === listGenerationRef.current && baseUrl === baseRef.current) setListLoading(false);
      });
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [baseUrl, isDemo]);

  useEffect_rw(() => {
    loadDocs();
    return () => {
      if (listControllerRef.current) listControllerRef.current.abort();
    };
  }, [loadDocs]);

  useEffect_rw(() => {
    const generation = detailGenerationRef.current + 1;
    detailGenerationRef.current = generation;
    if (detailControllerRef.current) detailControllerRef.current.abort();
    const controller = new AbortController();
    detailControllerRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 3500);
    const owned = listedBase === baseUrl && docs.some(row => row.id === selectedId);

    setDoc(null);
    setDetailErr("");

    if (isDemo || !baseUrl || !selectedId || !owned) {
      setDetailLoading(false);
      clearTimeout(timeout);
      return () => controller.abort();
    }

    setDetailLoading(true);
    fetch(baseUrl + "/research_doc?id=" + encodeURIComponent(selectedId), { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (controller.signal.aborted || generation !== detailGenerationRef.current || baseUrl !== baseRef.current || selectedId !== selectedIdRef.current) return;
        setDoc(isSelectedWikiDoc(j, selectedId) ? j : null);
      })
      .catch(e => {
        if (controller.signal.aborted || generation !== detailGenerationRef.current || baseUrl !== baseRef.current || selectedId !== selectedIdRef.current) return;
        setDetailErr(String(e && e.message ? e.message : e));
      })
      .finally(() => {
        clearTimeout(timeout);
        if (!controller.signal.aborted && generation === detailGenerationRef.current && baseUrl === baseRef.current && selectedId === selectedIdRef.current) setDetailLoading(false);
      });
    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [baseUrl, docs, isDemo, listedBase, selectedId]);

  const ownsDetail = Boolean(listedBase === baseUrl && isSelectedWikiDoc(doc, selectedId));
  const selectDocument = id => {
    setSelectedId(id);
    selectedIdRef.current = id;
    setDoc(null);
    setDetailErr("");
  };

  return (
    <div className="panel research-wiki">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          Research Wiki
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <button className="btn ghost sm" onClick={loadDocs} disabled={isDemo || listLoading}>
          {listLoading ? "loading" : "refresh"}
        </button>
      </div>
      <div className="panel-bd">
        <div className="research-wiki-note">
          Good Results screenshots are reference only, not live proof. Markdown is displayed as plain text.
        </div>
        {isDemo ? (
          <div className="research-wiki-empty">Backend connection required for wiki documents.</div>
        ) : (
          <div className="research-wiki-layout">
            <div className="research-wiki-list">
              {listErr && <div className="research-wiki-empty danger">wiki query failed: {listErr}</div>}
              {!listErr && listLoading && <div className="research-wiki-muted">loading documents…</div>}
              {RESEARCH_WIKI_CATEGORIES.map(cat => (
                <div key={cat.key} className="research-wiki-category">
                  <div className="research-wiki-category-title">{cat.label}</div>
                  {(grouped[cat.key] || []).slice(0, 12).map(row => (
                    <button
                      key={row.id}
                      className={selectedId === row.id ? "active" : ""}
                      onClick={() => selectDocument(row.id)}
                      title={row.id}
                    >
                      <span>{row.title || row.id}</span>
                      <small>{row.size || 0} bytes</small>
                    </button>
                  ))}
                  {!(grouped[cat.key] || []).length && !listLoading && <small className="research-wiki-muted">no docs</small>}
                </div>
              ))}
            </div>
            <div className="research-wiki-doc">
              {detailLoading ? (
                <div className="research-wiki-empty">Loading document…</div>
              ) : detailErr ? (
                <div className="research-wiki-empty danger">document query failed: {detailErr}</div>
              ) : ownsDetail && doc.available ? (
                <>
                  <div className="research-wiki-doc-head">
                    <strong>{doc.title || selectedId}</strong>
                    <span>{wikiLabel(doc.category)} / {doc.id}</span>
                  </div>
                  <pre className="research-wiki-markdown">{doc.markdown || ""}</pre>
                </>
              ) : (
                <div className="research-wiki-empty">
                  {selectedId ? "Document unavailable or not allowed." : "Select a research document."}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ResearchWikiPanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchWikiPanel };
