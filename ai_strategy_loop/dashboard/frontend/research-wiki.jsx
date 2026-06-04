/* Read-only research wiki/documentation browser */
const { useState: useState_rw, useEffect: useEffect_rw, useMemo: useMemo_rw } = React;

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

function ResearchWikiPanel({ baseUrl, wsStatus }) {
  const [docs, setDocs] = useState_rw([]);
  const [selectedId, setSelectedId] = useState_rw("");
  const [doc, setDoc] = useState_rw(null);
  const [loading, setLoading] = useState_rw(false);
  const [err, setErr] = useState_rw("");
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

  const loadDocs = React.useCallback(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    setErr("");
    fetch(baseUrl + "/research_docs", { signal: AbortSignal.timeout(3500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        const rows = Array.isArray(j.docs) ? j.docs : [];
        setDocs(rows);
        if (!selectedId && rows.length) {
          const preferred = rows.find(r => r.category === "wiki") || rows[0];
          setSelectedId(preferred.id);
        }
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, selectedId]);

  useEffect_rw(() => { loadDocs(); }, [loadDocs]);

  useEffect_rw(() => {
    if (isDemo || !baseUrl || !selectedId) {
      setDoc(null);
      return;
    }
    setLoading(true);
    setErr("");
    fetch(baseUrl + "/research_doc?id=" + encodeURIComponent(selectedId),
          { signal: AbortSignal.timeout(3500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setDoc(j || null))
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, selectedId]);

  return (
    <div className="panel research-wiki">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          Research Wiki
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <button className="btn ghost sm" onClick={loadDocs} disabled={isDemo || loading}>
          {loading ? "loading" : "refresh"}
        </button>
      </div>
      <div className="panel-bd">
        <div className="research-wiki-note">
          Good Results screenshots are reference only, not live proof. Markdown is displayed as plain text.
        </div>
        {isDemo ? (
          <div className="research-wiki-empty">Backend connection required for wiki documents.</div>
        ) : err ? (
          <div className="research-wiki-empty danger">wiki query failed: {err}</div>
        ) : (
          <div className="research-wiki-layout">
            <div className="research-wiki-list">
              {RESEARCH_WIKI_CATEGORIES.map(cat => (
                <div key={cat.key} className="research-wiki-category">
                  <div className="research-wiki-category-title">{cat.label}</div>
                  {(grouped[cat.key] || []).slice(0, 12).map(row => (
                    <button
                      key={row.id}
                      className={selectedId === row.id ? "active" : ""}
                      onClick={() => setSelectedId(row.id)}
                      title={row.id}
                    >
                      <span>{row.title || row.id}</span>
                      <small>{row.size || 0} bytes</small>
                    </button>
                  ))}
                  {!(grouped[cat.key] || []).length && <small className="research-wiki-muted">no docs</small>}
                </div>
              ))}
            </div>
            <div className="research-wiki-doc">
              {doc && doc.available ? (
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
