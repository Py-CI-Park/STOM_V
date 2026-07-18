/* Governed all-record research index browser.
 *
 * Read-only UI over /research_index + /research_index/detail.  The panel intentionally
 * renders markdown as inert <pre> text and loads row details only after selection.
 */
import { UiStateBlock } from "./ui-state.jsx";
const { useState: useState_rix, useEffect: useEffect_rix, useMemo: useMemo_rix, useRef: useRef_rix } = React;

const RIX_KIND_LABELS = {
  campaign: "Campaign",
  doc: "Doc",
  update_log: "Update log",
  registry: "Registry",
  hof: "Hall of Fame",
  loop_run: "Loop run",
  decision: "Decision",
  evidence: "Evidence",
};

const RIX_CANONICALITY_LABELS = {
  canonical: "canonical",
  derived: "derived",
  historical: "historical",
  stale: "stale",
  reference: "reference",
  candidate: "candidate",
};

const RIX_AUTHORITY_LABELS = {
  raw_campaign: "raw campaign",
  curated_doc: "curated doc",
  selected_update_log: "selected update_log",
  registry_entry: "registry entry",
  historical_planning_context: "historical context",
  hall_of_fame: "hall of fame",
  loop_runs_db: "loop_runs.db",
  decision_log: "decision log",
  evidence_artifact: "evidence artifact",
};

const RIX_TRACE_LABELS = {
  linked: "linked",
  unlinked: "unlinked",
  unknown: "unknown",
};


const RIX_SORT_LABELS = {
  updated_desc: "updated ↓",
  title_asc: "title A-Z",
  kind_asc: "kind/source",
};

function _rixBase(baseUrl) {
  if (baseUrl) return baseUrl;
  return (typeof window !== "undefined" && window.location && window.location.origin) || "";
}

function _rixShortPath(path) {
  if (!path) return "—";
  if (path.length <= 96) return path;
  return "…" + path.slice(-94);
}

function _rixFmtTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ko-KR", { hour12: false });
}

function ResearchBadge({ type, value }) {
  const label = type === "kind"
    ? (RIX_KIND_LABELS[value] || value || "—")
    : type === "canonicality"
      ? (RIX_CANONICALITY_LABELS[value] || value || "—")
      : type === "trace"
        ? (RIX_TRACE_LABELS[value] || value || "—")
        : (RIX_AUTHORITY_LABELS[value] || value || "—");
  return <span className={`research-index-badge research-index-badge-${type}`}>{label}</span>;
}

function _rixDetailText(detail) {
  if (!detail || !detail.available) return "";
  if (detail.markdown) return detail.markdown;
  if (detail.registry_entry) return JSON.stringify(detail.registry_entry, null, 2);
  if (detail.campaign) return JSON.stringify(detail.campaign, null, 2);
  return "";
}

function _rixExactResearchId(record) {
  if (!record || typeof record !== "object") return "";
  const direct = [record.research_id, record.id]
    .find(candidate => typeof candidate === "string" && /^(campaign|loop_run):.+$/.test(candidate));
  if (direct) return direct;
  if (typeof record.exact_link !== "string") return "";
  const match = record.exact_link.match(/^research-index:\/\/((?:campaign|loop_run):.+)$/);
  return match ? match[1] : "";
}

function ResearchIndexPanel({ baseUrl, wsStatus, initialLimit = 80, selectedResearchId, onSelectResearch }) {
  const base = _rixBase(baseUrl);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const [records, setRecords] = useState_rix([]);
  const [errors, setErrors] = useState_rix([]);
  const [cacheInfo, setCacheInfo] = useState_rix(null);
  const [selectedId, setSelectedId] = useState_rix("");
  const [detail, setDetail] = useState_rix(null);
  const [detailLoading, setDetailLoading] = useState_rix(false);
  const [loading, setLoading] = useState_rix(false);
  const [elapsed, setElapsed] = useState_rix(0);
  const [err, setErr] = useState_rix("");
  const [queryInput, setQueryInput] = useState_rix("");
  const [query, setQuery] = useState_rix("");
  const [kind, setKind] = useState_rix("all");
  const [canonicality, setCanonicality] = useState_rix("all");
  const [traceStatus, setTraceStatus] = useState_rix("all");
  const [sortKey, setSortKey] = useState_rix("updated_desc");
  const [displayLimit, setDisplayLimit] = useState_rix(initialLimit);
  const requestsRef = useRef_rix({ index: null, detail: null });
  const generationRef = useRef_rix({ index: 0, detail: 0 });
  const controlled = selectedResearchId != null || typeof onSelectResearch === "function";
  const baseIdentity = (isDemo ? "demo:" : "live:") + base;
  const baseIdentityRef = useRef_rix(baseIdentity);
  baseIdentityRef.current = baseIdentity;

  useEffect_rix(() => {
    Object.values(requestsRef.current).forEach(controller => {
      if (controller) controller.abort();
    });
    generationRef.current.index += 1;
    generationRef.current.detail += 1;
    setRecords([]);
    setErrors([]);
    setCacheInfo(null);
    setSelectedId("");
    setDetail(null);
    setDetailLoading(false);
    setLoading(false);
    setElapsed(0);
    setErr("");
  }, [baseIdentity]);

  useEffect_rix(() => {
    const timer = setTimeout(() => setQuery(queryInput.trim().toLowerCase()), 180);
    return () => clearTimeout(timer);
  }, [queryInput]);

  // 로딩 경과 초 — /research_index 는 대용량(수천 건, 실측 ~11초)이라 '멈춤'으로 오해되기 쉽다.
  //   로딩 중 매초 경과를 갱신해 진행 중임을 명확히 알린다(C5).
  useEffect_rix(() => {
    if (!loading) return;
    setElapsed(0);
    const id = setInterval(() => setElapsed(e => e + 1), 1000);
    return () => clearInterval(id);
  }, [loading]);

  const loadIndex = React.useCallback(() => {
    if (isDemo || !base) return undefined;
    if (requestsRef.current.index) requestsRef.current.index.abort();
    const controller = new AbortController();
    const generation = ++generationRef.current.index;
    const requestBase = baseIdentity;
    requestsRef.current.index = controller;
    setLoading(true);
    setErr("");
    fetch(base + "/research_index", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (!j || typeof j !== "object" || !Array.isArray(j.records) || !Array.isArray(j.errors)
          || (j.cache != null && typeof j.cache !== "object")
          || !j.records.every(row => row && typeof row === "object" && typeof row.id === "string"
            && Array.isArray(row.tags) && Array.isArray(row.related_ids))
          || !j.errors.every(item => item && typeof item === "object")) {
          throw new Error("Malformed research index response");
        }
        if (generation !== generationRef.current.index || controller.signal.aborted
          || baseIdentityRef.current !== requestBase) return;
        setRecords(j.records);
        setErrors(j.errors);
        setCacheInfo(j.cache || null);
        setSelectedId(prev => j.records.some(row => row.id === prev) ? prev : "");
      })
      .catch(e => {
        if (e.name !== "AbortError" && generation === generationRef.current.index && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) {
          setRecords([]);
          setErrors([]);
          setCacheInfo(null);
          setErr(String(e));
        }
      })
      .finally(() => {
        if (generation === generationRef.current.index && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setLoading(false);
      });
    return () => controller.abort();
  }, [base, baseIdentity, isDemo]);

  useEffect_rix(() => {
    const cancel = loadIndex();
    return () => { if (typeof cancel === "function") cancel(); };
  }, [loadIndex]);

  const filtered = useMemo_rix(() => {
    const q = query;
    const rows = records.filter(row => {
      if (kind !== "all" && row.kind !== kind) return false;
      if (canonicality !== "all" && row.canonicality !== canonicality) return false;
      if (traceStatus !== "all" && row.trace_status !== traceStatus) return false;
      if (!q) return true;
      const hay = [row.id, row.title, row.source_path, row.summary, row.exact_link, row.trace_status, ...(row.tags || []), ...(row.related_ids || [])]
        .join("\n").toLowerCase();
      return hay.includes(q);
    });
    rows.sort((a, b) => {
      if (sortKey === "title_asc") return String(a.title || a.id).localeCompare(String(b.title || b.id), "ko-KR");
      if (sortKey === "kind_asc") {
        const ak = `${a.kind || ""}:${a.canonicality || ""}:${a.trace_status || ""}:${a.title || a.id}`;
        const bk = `${b.kind || ""}:${b.canonicality || ""}:${b.trace_status || ""}:${b.title || b.id}`;
        return ak.localeCompare(bk, "ko-KR");
      }
      const at = Date.parse(a.updated_at || "") || 0;
      const bt = Date.parse(b.updated_at || "") || 0;
      return bt - at;
    });
    return rows;
  }, [records, query, kind, canonicality, traceStatus, sortKey]);

  useEffect_rix(() => {
    setDisplayLimit(initialLimit);
  }, [query, kind, canonicality, traceStatus, sortKey, initialLimit]);

  const visibleRows = useMemo_rix(() => filtered.slice(0, displayLimit), [filtered, displayLimit]);


  useEffect_rix(() => {
    if (requestsRef.current.detail) requestsRef.current.detail.abort();
    const requestId = ++generationRef.current.detail;
    if (isDemo || !base || !selectedId) {
      setDetail(null);
      setDetailLoading(false);
      return undefined;
    }
    const controller = new AbortController();
    const requestBase = baseIdentity;
    requestsRef.current.detail = controller;
    setDetailLoading(true);
    setDetail(null);
    fetch(base + "/research_index/detail?id=" + encodeURIComponent(selectedId), { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (!j || typeof j !== "object" || typeof j.available !== "boolean"
          || (j.row != null && (typeof j.row !== "object" || j.row.id !== selectedId))) {
          throw new Error("Malformed research index detail response");
        }
        if (requestId === generationRef.current.detail && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setDetail(j);
      })
      .catch(e => {
        if (e.name !== "AbortError" && requestId === generationRef.current.detail && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) {
          setDetail({ available: false, reason: String(e) });
        }
      })
      .finally(() => {
        if (requestId === generationRef.current.detail && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setDetailLoading(false);
      });
    return () => controller.abort();
  }, [base, baseIdentity, isDemo, selectedId]);

  const selectedRow = records.find(row => row.id === selectedId) || null;
  const detailText = _rixDetailText(detail);
  const sourceCounts = useMemo_rix(() => {
    const out = { campaign: 0, doc: 0, update_log: 0, registry: 0, hof: 0, loop_run: 0, decision: 0, evidence: 0 };
    for (const row of records) if (out[row.kind] != null) out[row.kind] += 1;
    return out;
  }, [records]);
  const traceCounts = useMemo_rix(() => {
    const out = { linked: 0, unlinked: 0, unknown: 0 };
    for (const row of records) if (out[row.trace_status] != null) out[row.trace_status] += 1;
    return out;
  }, [records]);
  const timelineRows = useMemo_rix(() => visibleRows.slice(0, 12), [visibleRows]);
  const selectRecord = record => {
    setSelectedId(record.id);
    const researchId = _rixExactResearchId(record);
    if (researchId && typeof onSelectResearch === "function") onSelectResearch(researchId);
  };


  return (
    <div className="panel research-index">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          Governed Research Index
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
          {controlled && <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
            parent research {typeof selectedResearchId === "string" ? selectedResearchId : "none"}
          </span>}
        </div>
        <button className="btn ghost sm" onClick={loadIndex} disabled={isDemo || loading}>
          {loading ? "loading" : "refresh"}
        </button>
      </div>
      <div className="panel-bd">
        <div className="research-index-note">
          Governed exact-link timeline across campaigns, docs, update logs, HOF, loop_runs, evidence artifacts, decisions, and allowlisted registry rows. Badges use closed source_authority, canonicality, and trace_status values; unknown/unlinked lineage stays visible instead of being hidden.
        </div>
        {isDemo ? (
          <UiStateBlock kind="demo" compact title="Backend connection required">Governed research index is available when the dashboard backend is connected.</UiStateBlock>
        ) : err ? (
          <UiStateBlock kind="error" compact title="index query failed" detail={err}>Refresh after checking backend connectivity.</UiStateBlock>
        ) : (
          <>
            <div className="research-index-controls">
              <input
                type="search"
                className="research-index-search"
                value={queryInput}
                onChange={e => setQueryInput(e.target.value)}
                placeholder="Search title, source path, tag, related id"
              />
              <label>kind
                <select value={kind} onChange={e => setKind(e.target.value)}>
                  <option value="all">all</option>
                  <option value="campaign">campaign</option>
                  <option value="doc">doc</option>
                  <option value="update_log">update_log</option>
                  <option value="registry">registry</option>
                  <option value="hof">hof</option>
                  <option value="loop_run">loop_run</option>
                  <option value="decision">decision</option>
                  <option value="evidence">evidence</option>
                </select>
              </label>
              <label>canonicality
                <select value={canonicality} onChange={e => setCanonicality(e.target.value)}>
                  <option value="all">all</option>
                  <option value="canonical">canonical</option>
                  <option value="derived">derived</option>
                  <option value="historical">historical</option>
                  <option value="reference">reference</option>
                  <option value="candidate">candidate</option>
                  <option value="stale">stale</option>
                </select>
              </label>
              <label>trace
                <select value={traceStatus} onChange={e => setTraceStatus(e.target.value)}>
                  <option value="all">all</option>
                  <option value="linked">linked</option>
                  <option value="unlinked">unlinked</option>
                  <option value="unknown">unknown</option>
                </select>
              </label>
              <label>sort
                <select value={sortKey} onChange={e => setSortKey(e.target.value)}>
                  {Object.entries(RIX_SORT_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>
            </div>
            <div className="research-index-kpis">
              <span>rows <b>{records.length}</b></span>
              <span>shown <b>{visibleRows.length}</b>{filtered.length > visibleRows.length ? ` / ${filtered.length}` : ""}</span>
              <span>campaign <b>{sourceCounts.campaign}</b></span>
              <span>doc <b>{sourceCounts.doc}</b></span>
              <span>update_log <b>{sourceCounts.update_log}</b></span>
              <span>registry <b>{sourceCounts.registry}</b></span>
              <span>hof <b>{sourceCounts.hof}</b></span>
              <span>loop_runs <b>{sourceCounts.loop_run}</b></span>
              <span>decisions <b>{sourceCounts.decision}</b></span>
              <span>evidence <b>{sourceCounts.evidence}</b></span>
              <span>linked <b>{traceCounts.linked}</b></span>
              <span>unlinked <b>{traceCounts.unlinked}</b></span>
              <span>unknown <b>{traceCounts.unknown}</b></span>
              {cacheInfo && <span>cache <b>{cacheInfo.hit ? "hit" : "miss"}</b> · sources {cacheInfo.sources}</span>}
              <span>cap <b>{displayLimit}</b>{filtered.length > displayLimit ? " windowed" : ""}</span>
            </div>
            {errors.length > 0 && (
              <div className="research-index-warning">
                {errors.length} index source warning(s); details remain read-only.
              </div>
            )}
            <div className="research-index-timeline" aria-label="governed exact-link research timeline">
              <div className="research-index-timeline-head">
                <b>Governed Exact-Link Timeline</b>
                <span className="mono">source_authority · canonicality · trace_status · exact_link</span>
              </div>
              <div className="research-index-timeline-rail">
                {timelineRows.map(row => (
                  <button
                    type="button"
                    key={`tl-${row.id}`}
                    className={selectedId === row.id ? "active" : ""}
                    onClick={() => selectRecord(row)}
                    title={row.exact_link || row.id}
                  >
                    <span className="research-index-timeline-time">{_rixFmtTime(row.updated_at)}</span>
                    <strong>{row.title || row.id}</strong>
                    <span className="research-index-row-badges">
                      <ResearchBadge type="trace" value={row.trace_status} />
                      <ResearchBadge type="canonicality" value={row.canonicality} />
                      <ResearchBadge type="authority" value={row.source_authority} />
                    </span>
                    <small>{row.exact_link || row.id}</small>
                  </button>
                ))}
                {loading && records.length === 0 && <UiStateBlock kind="loading" compact title={`거버넌스 인덱스 로딩 중… (경과 ${elapsed}s)`}>수천 건의 exact-link 레코드를 집계 중입니다(대용량 · 보통 ~11초, 최대 ~20초).</UiStateBlock>}
                {!loading && timelineRows.length === 0 && <UiStateBlock kind="empty" compact title="No timeline records.">필터를 조정하면 exact-link 타임라인이 다시 표시됩니다.</UiStateBlock>}
              </div>
            </div>
            <div className="research-index-layout">
              <div className="research-index-list" role="listbox" aria-label="research index records">
                {visibleRows.map(row => (
                  <button
                    type="button"
                    key={row.id}
                    className={selectedId === row.id ? "active" : ""}
                    onClick={() => selectRecord(row)}
                    title={row.id}
                  >
                    <span className="research-index-row-title">{row.title || row.id}</span>
                    <span className="research-index-row-badges">
                      <ResearchBadge type="kind" value={row.kind} />
                      <ResearchBadge type="canonicality" value={row.canonicality} />
                      <ResearchBadge type="authority" value={row.source_authority} />
                      <ResearchBadge type="trace" value={row.trace_status} />
                    </span>
                    <small>{_rixShortPath(row.source_path)}</small>
                  </button>
                ))}
                {loading && records.length === 0 && <UiStateBlock kind="loading" compact title={`거버넌스 인덱스 로딩 중… (경과 ${elapsed}s)`}>수천 건의 레코드를 불러오는 중입니다(대용량 · 보통 ~11초, 최대 ~20초).</UiStateBlock>}
                {!loading && visibleRows.length === 0 && <UiStateBlock kind="empty" compact title="No matching research records.">검색어와 필터를 조정하세요.</UiStateBlock>}
                {visibleRows.length < filtered.length && (
                  <button type="button" className="btn ghost sm research-index-more"
                          onClick={() => setDisplayLimit(v => Math.min(filtered.length, v + initialLimit))}>
                    더 보기 {visibleRows.length}/{filtered.length}
                  </button>
                )}
              </div>
              <div className="research-index-detail">
                {selectedRow ? (
                  <>
                    <div className="research-index-detail-head">
                      <strong>{selectedRow.title || selectedRow.id}</strong>
                      <span className="mono">{selectedRow.id}</span>
                      <div className="research-index-row-badges">
                        <ResearchBadge type="kind" value={selectedRow.kind} />
                        <ResearchBadge type="canonicality" value={selectedRow.canonicality} />
                        <ResearchBadge type="authority" value={selectedRow.source_authority} />
                        <ResearchBadge type="trace" value={selectedRow.trace_status} />
                      </div>
                    </div>
                    <div className="research-index-meta mono">
                      <div><b>source</b> {_rixShortPath(selectedRow.source_path)}</div>
                      <div><b>exact_link</b> {selectedRow.exact_link || selectedRow.id}</div>
                      <div><b>trace_status</b> {selectedRow.trace_status || "unknown"}</div>
                      <div><b>updated</b> {_rixFmtTime(selectedRow.updated_at)}</div>
                      <div><b>tags</b> {(selectedRow.tags || []).join(", ") || "—"}</div>
                      <div><b>summary</b> {selectedRow.summary || "—"}</div>
                    </div>
                    {(selectedRow.related_ids || []).length > 0 && (
                      <div className="research-index-related">
                        <div className="research-index-related-title">Related lineage</div>
                        {selectedRow.related_ids.map(id => (
                          <button key={id} type="button" onClick={() => {
                            const related = records.find(row => row.id === id);
                            if (related) selectRecord(related);
                            else setSelectedId(id);
                          }}>{id}</button>
                        ))}
                      </div>
                    )}
                    {(!selectedRow.related_ids || selectedRow.related_ids.length === 0) && (
                      <div className="research-index-related research-index-related-muted">
                        Trace lineage: {selectedRow.trace_status === "unlinked" ? "unlinked source" : "unknown lineage"}
                      </div>
                    )}
                    {detailLoading ? (
                      <UiStateBlock kind="loading" compact title="Detail loading…">선택한 기록의 상세를 지연 조회 중입니다.</UiStateBlock>
                    ) : detail && detail.available ? (
                      <pre className="research-index-pre">{detailText}</pre>
                    ) : (
                      <UiStateBlock kind={detail ? "error" : "empty"} compact title={detail ? "Detail unavailable" : "Select a row to lazy-load detail"} detail={detail ? (detail.reason || "unknown") : "no selected detail"}>
                        Raw evidence remains read-only and linked by lineage.
                      </UiStateBlock>
                    )}
                  </>
                ) : (
                  <UiStateBlock kind="empty" compact title="Select a governed research record.">왼쪽 목록에서 행을 선택하면 상세를 지연 로딩합니다.</UiStateBlock>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ResearchIndexPanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchIndexPanel };
