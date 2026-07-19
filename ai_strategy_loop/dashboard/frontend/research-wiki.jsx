/* Read-only research wiki/documentation browser */
const { useState: useState_rw, useEffect: useEffect_rw, useMemo: useMemo_rw, useRef: useRef_rw, useCallback: useCallback_rw } = React;

const WIKI_PAGE_LIMIT = 60;

const RESEARCH_WIKI_CATEGORIES = [
  { key: "", label: "All" },
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

function isStringList(value) {
  return Array.isArray(value) && value.every(item => typeof item === "string");
}

function isWikiChronology(value) {
  return Array.isArray(value) && value.every(item => item && typeof item === "object" &&
    (item.date == null || typeof item.date === "string") &&
    (item.label == null || typeof item.label === "string") &&
    (item.status == null || typeof item.status === "string") &&
    (item.id == null || typeof item.id === "string"));
}

function isWikiRow(row) {
  return Boolean(row && typeof row === "object" && typeof row.id === "string" && row.id &&
    typeof row.title === "string" && typeof row.category === "string" && Number.isFinite(row.size) &&
    (row.source_sha256 == null || typeof row.source_sha256 === "string") &&
    (row.source_bytes == null || Number.isFinite(row.source_bytes)) &&
    (row.tags == null || isStringList(row.tags)) &&
    (row.related_ids == null || isStringList(row.related_ids)) &&
    (row.chronology == null || isWikiChronology(row.chronology)) &&
    (row.history == null || isWikiChronology(row.history)));
}

function isSelectedWikiDoc(value, selectedId) {
  return Boolean(value && typeof value === "object" && value.id === selectedId &&
    (value.available === false || (value.available === true && isWikiRow(value) &&
      typeof value.markdown === "string")));
}

function shortWikiSha(value) {
  return typeof value === "string" && value.length >= 12 ? value.slice(0, 12) : value || "unknown";
}

function wikiMetaChips(row) {
  if (!row || typeof row !== "object") return [];
  const chips = [];
  if (row.trust) chips.push(["trust", "trust", row.trust]);
  if (row.standard_template_status) chips.push(["template", "template", row.standard_template_status]);
  if (row.metadata_status) chips.push(["metadata", "metadata", row.metadata_status]);
  if (row.stale === true) chips.push(["stale", "stale", "source changed"]);
  if (Number.isFinite(row.source_bytes)) chips.push(["bytes", "raw bytes", String(row.source_bytes)]);
  if (row.source_sha256) chips.push(["sha", "sha256", shortWikiSha(row.source_sha256)]);
  return chips;
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
  const [query, setQuery] = useState_rw("");
  const [tagFilter, setTagFilter] = useState_rw("");
  const [categoryFilter, setCategoryFilter] = useState_rw("");
  const [cursor, setCursor] = useState_rw("0");
  const [nextCursor, setNextCursor] = useState_rw("");
  const [totalCount, setTotalCount] = useState_rw(0);
  const filtersRef = useRef_rw({ q: "", tag: "", category: "", cursor: "0" });
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

  const allowedDocById = useMemo_rw(() => {
    const out = {};
    for (const row of docs) out[row.id] = row;
    return out;
  }, [docs]);

  const loadDocs = useCallback_rw(() => {
    const generation = listGenerationRef.current + 1;
    listGenerationRef.current = generation;
    const priorSelection = selectedIdRef.current;
    const filters = filtersRef.current || { q: "", tag: "", category: "", cursor: "0" };
    if (listControllerRef.current) listControllerRef.current.abort();
    if (detailControllerRef.current) detailControllerRef.current.abort();
    detailGenerationRef.current += 1;

    const controller = new AbortController();
    listControllerRef.current = controller;
    const timeout = setTimeout(() => controller.abort(), 15000);
    setDocs([]);
    setListedBase("");
    setSelectedId("");
    selectedIdRef.current = "";
    setDoc(null);
    setListErr("");
    setDetailErr("");
    setDetailLoading(false);
    setNextCursor("");
    setTotalCount(0);

    if (isDemo || !baseUrl) {
      setListLoading(false);
      clearTimeout(timeout);
      return () => controller.abort();
    }

    const params = new URLSearchParams();
    params.set("limit", String(WIKI_PAGE_LIMIT));
    params.set("cursor", filters.cursor || "0");
    if ((filters.q || "").trim()) params.set("q", filters.q.trim());
    if ((filters.tag || "").trim()) params.set("tag", filters.tag.trim());
    if ((filters.category || "").trim()) params.set("category", filters.category.trim());

    setListLoading(true);
    fetch(baseUrl + "/research_docs?" + params.toString(), { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (controller.signal.aborted || generation !== listGenerationRef.current || baseUrl !== baseRef.current) return;
        if (j && j.available === false) {
          setDocs([]);
          setListErr(j.error || j.status || "wiki_query_rejected");
          setCursor(typeof j.cursor === "string" ? j.cursor : "0");
          return;
        }
        const rows = Array.isArray(j && j.docs) ? j.docs.filter(isWikiRow) : [];
        const retained = rows.some(row => row.id === priorSelection) ? priorSelection : "";
        const preferred = rows.find(row => row.category === "wiki") || rows[0];
        const nextSelectedId = retained || (preferred ? preferred.id : "");
        setDocs(rows);
        setListedBase(baseUrl);
        setSelectedId(nextSelectedId);
        selectedIdRef.current = nextSelectedId;
        setCursor(typeof j.cursor === "string" ? j.cursor : (filters.cursor || "0"));
        setNextCursor(typeof j.next_cursor === "string" ? j.next_cursor : "");
        setTotalCount(Number.isFinite(j.total_count) ? j.total_count : rows.length);
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
    const timeout = setTimeout(() => controller.abort(), 15000);
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
  const chronology = ownsDetail && doc.available
    ? (Array.isArray(doc.chronology) ? doc.chronology : (Array.isArray(doc.history) ? doc.history : []))
    : [];
  const relatedDocs = ownsDetail && doc.available && Array.isArray(doc.related_ids) && listedBase === baseUrl
    ? doc.related_ids.map(id => allowedDocById[id]).filter(Boolean)
    : [];
  const hiddenRelatedCount = ownsDetail && doc.available && Array.isArray(doc.related_ids)
    ? Math.max(0, doc.related_ids.length - relatedDocs.length)
    : 0;
  const pageOffset = Math.max(0, Number.parseInt(cursor || "0", 10) || 0);
  const previousCursor = String(Math.max(0, pageOffset - WIKI_PAGE_LIMIT));
  const hasPrevious = pageOffset > 0;

  const applyFilters = next => {
    const normalized = {
      q: String(next.q || ""),
      tag: String(next.tag || ""),
      category: String(next.category || ""),
      cursor: String(next.cursor || "0"),
    };
    filtersRef.current = normalized;
    setQuery(normalized.q);
    setTagFilter(normalized.tag);
    setCategoryFilter(normalized.category);
    setCursor(normalized.cursor);
    loadDocs();
  };
  const selectDocument = id => {
    if (listedBase !== baseUrl || !docs.some(row => row.id === id)) return;
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
          Good Results screenshots are reference only, not live proof. Markdown is displayed as plain text; metadata is read-only sidecar/index data.
        </div>
        {isDemo ? (
          <div className="research-wiki-empty">Backend connection required for wiki documents.</div>
        ) : (
          <div className="research-wiki-layout">
            <div className="research-wiki-list">
              <div className="research-wiki-filters">
                <label>
                  q
                  <input
                    value={query}
                    maxLength={120}
                    onChange={e => applyFilters({ ...filtersRef.current, q: e.target.value, cursor: "0" })}
                    placeholder="title, id, tag, sha"
                  />
                </label>
                <label>
                  tag
                  <input
                    value={tagFilter}
                    maxLength={48}
                    onChange={e => applyFilters({ ...filtersRef.current, tag: e.target.value, cursor: "0" })}
                    placeholder="e.g. audit"
                  />
                </label>
                <label>
                  category
                  <select
                    value={categoryFilter}
                    onChange={e => applyFilters({ ...filtersRef.current, category: e.target.value, cursor: "0" })}
                  >
                    {RESEARCH_WIKI_CATEGORIES.map(cat => (
                      <option key={cat.key || "all"} value={cat.key}>{cat.label}</option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="btn ghost sm"
                  onClick={() => applyFilters({ q: "", tag: "", category: "", cursor: "0" })}
                  disabled={listLoading && !query && !tagFilter && !categoryFilter}
                >
                  clear
                </button>
              </div>
              <div className="research-wiki-pagebar">
                <span>{docs.length} / {totalCount} docs</span>
                <button type="button" className="btn ghost sm" disabled={!hasPrevious || listLoading} onClick={() => applyFilters({ ...filtersRef.current, cursor: previousCursor })}>prev</button>
                <button type="button" className="btn ghost sm" disabled={!nextCursor || listLoading} onClick={() => applyFilters({ ...filtersRef.current, cursor: nextCursor })}>next</button>
              </div>
              {listErr && <div className="research-wiki-empty danger">wiki query failed: {listErr}</div>}
              {!listErr && listLoading && <div className="research-wiki-muted">loading documents…</div>}
              {RESEARCH_WIKI_CATEGORIES.filter(cat => cat.key).map(cat => (
                <div key={cat.key} className="research-wiki-category">
                  <div className="research-wiki-category-title">{cat.label}</div>
                  {(grouped[cat.key] || []).map(row => (
                    <button
                      key={row.id}
                      className={selectedId === row.id ? "active" : ""}
                      onClick={() => selectDocument(row.id)}
                      title={row.id}
                    >
                      <span>{row.title || row.id}</span>
                      <small>{row.source_bytes || row.size || 0} raw bytes · {row.trust || "unknown trust"}</small>
                      {(row.tags || []).length > 0 && <small>{row.tags.slice(0, 4).map(tag => `#${tag}`).join(" ")}</small>}
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
                    <div className="research-wiki-chips">
                      {wikiMetaChips(doc).map(([key, label, value]) => (
                        <span key={key} className={key === "stale" ? "danger" : ""}>{label}: {value}</span>
                      ))}
                      {(doc.tags || []).slice(0, 10).map(tag => (
                        <button key={tag} type="button" onClick={() => applyFilters({ ...filtersRef.current, tag, cursor: "0" })}>#{tag}</button>
                      ))}
                    </div>
                  </div>
                  {(chronology.length > 0 || relatedDocs.length > 0 || hiddenRelatedCount > 0) && (
                    <div className="research-wiki-metadata">
                      {chronology.length > 0 && (
                        <div className="research-wiki-section">
                          <div className="research-wiki-section-title">Chronology / history</div>
                          <ol>
                            {chronology.map((item, index) => (
                              <li key={`${item.date || "event"}-${index}`}>
                                <b>{item.date || "undated"}</b>
                                <span>{item.label || item.status || "event"}</span>
                                {item.status && <small>{item.status}</small>}
                              </li>
                            ))}
                          </ol>
                        </div>
                      )}
                      {(relatedDocs.length > 0 || hiddenRelatedCount > 0) && (
                        <div className="research-wiki-section">
                          <div className="research-wiki-section-title">Related docs</div>
                          <div className="research-wiki-related">
                            {relatedDocs.map(row => (
                              <button key={row.id} type="button" onClick={() => selectDocument(row.id)} title={row.id}>
                                {row.title || row.id}
                              </button>
                            ))}
                            {hiddenRelatedCount > 0 && <small>{hiddenRelatedCount} related id(s) outside the current allowed result set hidden.</small>}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
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
