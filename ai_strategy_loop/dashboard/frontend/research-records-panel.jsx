import { _RpRunCompare, _RpHistory } from "./rp-heatmap.jsx";
import { fetchRunsShared } from "./runs-shared.jsx";
/* Evolution dashboard research-record index panel. */
const {
  useState: useState_rrp,
  useEffect: useEffect_rrp,
  useCallback: useCallback_rrp,
  useRef: useRef_rrp,
} = React;

function _rrpMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return sign + Math.round(n).toLocaleString();
}

function _rrpPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(2) + "%";
}

function _rrpDate(ts) {
  if (ts == null || ts === "") return "—";
  const n = Number(ts);
  if (!Number.isFinite(n) || n <= 0) return "—";
  const date = new Date(n * 1000);
  return Number.isNaN(date.getTime()) ? "—" : date.toLocaleString();
}

function _rrpMetadataValue(value) {
  if (value == null || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.map(String).join(" / ") : "—";
  return typeof value === "object" ? "—" : String(value);
}

function _rrpBestLabel(record) {
  const best = (record && record.best) || {};
  return best.label || best.name || best.strategy_gist || "-";
}

function ResearchRecordsPanel({ baseUrl, wsStatus, onSelectCampaign }) {
  const [payload, setPayload] = useState_rrp(null);
  const [selectedCampaign, setSelectedCampaign] = useState_rrp("");
  const [detail, setDetail] = useState_rrp(null);
  const [loading, setLoading] = useState_rrp(false);
  const [err, setErr] = useState_rrp("");
  const [runList, setRunList] = useState_rrp([]);
  const [runListLoading, setRunListLoading] = useState_rrp(false);
  // §10-10 completeness: 12개 초과 campaign 을 조용히 자르지 않고 명시(전체 보기 토글).
  const [showAll, setShowAll] = useState_rrp(false);
  // v5.3.9(검수): 캠페인 필터 + 열 제목 클릭 정렬(연구·시점·세대 체계 탐색).
  const [rq, setRq] = useState_rrp("");
  const [sortKey, setSortKey] = useState_rrp("updated_at");
  const [sortAsc, setSortAsc] = useState_rrp(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_rrp(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    fetch(baseUrl + "/research_records", { signal: AbortSignal.timeout(6000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        setPayload(j);
        setErr("");
        const rows = Array.isArray(j && j.campaigns) ? j.campaigns : [];
        // v5.4 H1 — 함수형 갱신으로 selectedCampaign 의존 제거(선택 변경마다 목록 재fetch 하던 중복 해소).
        if (rows.length) setSelectedCampaign(prev => prev || rows[0].name || "");
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_rrp(() => {
    refresh();
    if (isDemo || !baseUrl) return undefined;
    const timer = setInterval(refresh, 60000);
    return () => clearInterval(timer);
  }, [refresh, baseUrl, isDemo]);

  const detailReqRef = useRef_rrp(0);
  useEffect_rrp(() => {
    if (isDemo || !baseUrl || !selectedCampaign) {
      setDetail(null);
      return;
    }
    // Clear the prior detail before requesting the newly selected campaign.
    // The response must also name that campaign before it becomes selectable metadata.
    setDetail(null);
    const reqId = ++detailReqRef.current;
    const forCampaign = selectedCampaign;
    const controller = new AbortController();
    let timedOut = false;
    const timeout = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, 6000);
    fetch(baseUrl + "/research_records/detail?campaign=" + encodeURIComponent(forCampaign),
          { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        const campaign = j && j.campaign;
        if (reqId !== detailReqRef.current) return;
        if (!j || !j.available || !campaign || campaign.name !== forCampaign) {
          setDetail({ available: false, reason: "selection_metadata_unavailable", __campaign: forCampaign });
          return;
        }
        setDetail({ available: true, campaign, __campaign: forCampaign });
        if (typeof onSelectCampaign === "function") onSelectCampaign(forCampaign, campaign);
      })
      .catch(e => {
        if (reqId === detailReqRef.current && (timedOut || e.name !== "AbortError")) {
          setDetail({ available: false, reason: timedOut ? "request_timeout" : String(e), __campaign: forCampaign });
        }
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      clearTimeout(timeout);
      controller.abort();
    };
  }, [baseUrl, isDemo, selectedCampaign]);
  const refreshRuns = useCallback_rrp(() => {
    if (isDemo || !baseUrl) {
      setRunList([]);
      return;
    }
    setRunListLoading(true);
    fetchRunsShared(baseUrl, { timeoutMs: 6000 })
      .then(j => {
        const runs = Array.isArray(j && j.runs) ? j.runs.slice() : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      })
      .catch(() => setRunList([]))
      .finally(() => setRunListLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_rrp(() => {
    refreshRuns();
  }, [refreshRuns]);

  const onOpenWorkbench = useCallback_rrp(() => {
    try {
      localStorage.setItem("stom_active_tab", "backtest");
      window.location.href = "/?tab=backtest";
    } catch (e) {}
  }, []);

  const rowsAll = (payload && Array.isArray(payload.campaigns)) ? payload.campaigns : [];
  const _rrpSortVal = (row, k) => {
    const best = row.best || {};
    if (k === "name") return String(row.name || "");
    if (k === "candidate_count") return Number(row.candidate_count || 0);
    if (k === "profit") return Number(best.profit || 0);
    if (k === "mdd") return Number(best.mdd || 0);
    return Number(row.updated_at || 0);
  };
  const rows = rowsAll
    .filter(r => !rq.trim() || String(r.name || "").toLowerCase().includes(rq.trim().toLowerCase()))
    .sort((a, b) => {
      const va = _rrpSortVal(a, sortKey), vb = _rrpSortVal(b, sortKey);
      const c = typeof va === "string" ? va.localeCompare(String(vb)) : (va - vb);
      return sortAsc ? c : -c;
    });
  const onSort = (k) => { if (k === sortKey) setSortAsc(v => !v); else { setSortKey(k); setSortAsc(k === "name"); } };
  const _si = (k) => (sortKey === k ? (sortAsc ? " ▲" : " ▼") : "");
  const selected = (detail && detail.__campaign === selectedCampaign && detail.available && detail.campaign)
    ? detail.campaign : null;
  const candidates = (selected && Array.isArray(selected.candidates)) ? selected.candidates.slice(0, 5) : [];
  const errors = (payload && Array.isArray(payload.errors)) ? payload.errors : [];
  const currentRunId = runList.length ? runList[0].run_id : "";
  const currentGenNo = 0;
  const selectedSummary = selected && selected.summary && typeof selected.summary === "object" ? selected.summary : {};
  const selectedArtifacts = selected && selected.artifacts && typeof selected.artifacts === "object" ? selected.artifacts : {};
  const selectedLinkage = (() => {
    const parts = [];
    if (selectedSummary.run_id != null && selectedSummary.run_id !== "") parts.push(`run ${selectedSummary.run_id}`);
    if (selectedSummary.gen_no != null && selectedSummary.gen_no !== "") parts.push(`gen ${selectedSummary.gen_no}`);
    return parts.length ? parts.join(" / ") : "—";
  })();
  const selectedEvidence = [
    selectedArtifacts.summary,
    selectedArtifacts.jsonl,
    selectedArtifacts.run_log,
    ...(Array.isArray(selectedArtifacts.pairs) ? selectedArtifacts.pairs : []),
  ].filter(Boolean);
  const selectedUseReference = [
    selectedSummary.use_evidence,
    selectedSummary.referenced_by,
  ].filter(value => value != null && value !== "");
  const selectedFields = [
    ["Research date", selectedSummary.research_date],
    ["Created", selectedSummary.created_at],
    ["Updated", selected ? _rrpDate(selected.updated_at) : "—"],
    ["Purpose", selectedSummary.purpose],
    ["Source", selectedSummary.source],
    ["Run / generation", selectedLinkage],
    ["Use / reference evidence", selectedUseReference],
    ["Evidence files", selectedEvidence],
    ["Status", selected ? "available" : `unavailable${detail && detail.reason ? `: ${detail.reason}` : ""}`],
    ["Freshness", wsStatus === "open" ? "connected response" : wsStatus === "demo" ? "unavailable in Demo" : "connection not current; displayed response may be stale"],
  ];

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          Research Records
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
            {rows.length} campaigns
          </span>
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}>
            {loading ? "Loading" : "Refresh"}
          </button>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {err && <div className="research-empty danger">{err}</div>}
        {isDemo && <div className="research-empty">Demo mode</div>}
        {!isDemo && rows.length === 0 && !err && <div className="research-empty">No research records</div>}
        {rowsAll.length > 0 && (
          <div className="research-records-list-viewport" data-region="scroll" tabIndex={0} aria-label="연구 기록 목록">
            <input className="toolbar-input" type="search" placeholder="캠페인 검색(필터)"
                   value={rq} onChange={e => setRq(e.target.value)} aria-label="캠페인 필터"
                   style={{ marginBottom: 8, width: 260 }} />
            {rq && <span className="mono" style={{ marginLeft: 10, fontSize: 11, color: "var(--ink-3)" }}>필터 {rows.length}/{rowsAll.length}건</span>}
            <table className="mono research-records-sticky-table" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead className="research-records-sticky-header">
                <tr style={{ color: "var(--ink-3)" }}>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}><button className="rrp-th" onClick={() => onSort("name")}>Campaign{_si("name")}</button></th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}><button className="rrp-th" onClick={() => onSort("candidate_count")}>Candidates{_si("candidate_count")}</button></th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}><button className="rrp-th" onClick={() => onSort("profit")}>Best PnL{_si("profit")}</button></th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}><button className="rrp-th" onClick={() => onSort("mdd")}>MDD{_si("mdd")}</button></th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Artifacts</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}><button className="rrp-th" onClick={() => onSort("updated_at")}>Updated{_si("updated_at")}</button></th>
                </tr>
              </thead>
              <tbody>
                {(showAll ? rows : rows.slice(0, 12)).map(row => {
                  const best = row.best || {};
                  const artifacts = row.artifacts || {};
                  const active = row.name === selectedCampaign;
                  return (
                    <tr key={row.name} style={{
                      borderTop: "1px solid var(--line-1)",
                      background: active ? "rgba(56, 189, 248, 0.08)" : "transparent",
                    }}>
                      <td style={{ padding: "7px 8px", minWidth: 180 }}>
                        <button className="btn ghost sm" onClick={() => { setSelectedCampaign(row.name); if (typeof onSelectCampaign === "function") onSelectCampaign(row.name, null); }}
                                style={{ maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
                          {row.name}
                        </button>
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right" }}>{row.candidate_count || 0}</td>
                      <td style={{
                        padding: "7px 8px", textAlign: "right",
                        color: Number(best.profit || 0) >= 0 ? "var(--teal)" : "var(--red)",
                      }}>
                        {_rrpMoney(best.profit)}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right" }}>{_rrpPct(best.mdd)}</td>
                      <td style={{ padding: "7px 8px", color: "var(--ink-2)" }}>
                        {(artifacts.pairs || []).length} pairs / {artifacts.summary ? "summary" : "-"} / {artifacts.run_log ? "log" : "-"}
                      </td>
                      <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--ink-3)" }}>
                        {_rrpDate(row.updated_at)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {rows.length > 12 && (
          <div className="mono" style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 10.5, color: "var(--ink-3)" }}>
            <span>{showAll ? `전체 ${rows.length}개 표시 중` : `전체 ${rows.length}개 중 12개 표시`}</span>
            <button className="btn ghost sm" onClick={() => setShowAll(v => !v)}>
              {showAll ? "처음 12개만 보기" : `전체 ${rows.length}개 보기`}
            </button>
          </div>
        )}
        {selectedCampaign && (
          <div className="research-records-selected-detail">
            <div style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 10 }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>Selected</div>
              <div className="mono" style={{ color: "var(--ink-0)", marginBottom: 6 }}>{selected ? selected.name : selectedCampaign}</div>
              {selected ? (
                <React.Fragment>
                  <div className="mono" style={{ color: "var(--ink-2)", fontSize: 11 }}>
                    best={_rrpBestLabel(selected)}
                  </div>
                  <div className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5, marginTop: 6 }}>
                    root={(payload && payload.root) || "—"}
                  </div>
                </React.Fragment>
              ) : (
                <div className="mono" style={{ color: "var(--ink-3)", fontSize: 11 }}>
                  Selected metadata unavailable
                </div>
              )}
              <div className="research-records-fields mono">
                {selectedFields.map(([label, value]) => <div key={label}><span>{label}</span><b>{_rrpMetadataValue(value)}</b></div>)}
              </div>
            </div>
            <div style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 10 }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>Top Candidates</div>
              {candidates.length === 0 ? (
                <div className="research-empty" style={{ padding: "8px 0" }}>No candidate rows</div>
              ) : candidates.map(c => (
                <div key={`${c.label}-${c.round || ""}`} className="mono" style={{
                  display: "grid",
                  gridTemplateColumns: "minmax(110px, 1fr) 72px 56px 56px",
                  gap: 8,
                  padding: "4px 0",
                  borderTop: "1px solid var(--line-1)",
                  fontSize: 11,
                }}>
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{c.label}</span>
                  <span style={{ textAlign: "right", color: Number(c.profit || 0) >= 0 ? "var(--teal)" : "var(--red)" }}>{_rrpMoney(c.profit)}</span>
                  <span style={{ textAlign: "right" }}>{_rrpPct(c.mdd)}</span>
                  <span style={{ textAlign: "right" }}>{c.trades || 0}</span>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="panel" style={{ borderColor: "var(--line-1)", background: "var(--bg-0)" }}>
          <div className="panel-hd">
            <div className="panel-hd-title">
              <span className="dot" style={{ background: "var(--violet)" }}></span>
              히스토리 ResultDetail · Compare
            </div>
            <button className="btn ghost sm" onClick={refreshRuns} disabled={isDemo || runListLoading}>
              {runListLoading ? "run 로딩…" : "run 새로고침"}
            </button>
          </div>
          <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              History가 과거 run/gen 아카이브와 Compare를 소유합니다. Workbench는 깊은 분석으로 연결만 제공합니다.
            </div>
            <_RpRunCompare
              baseUrl={baseUrl}
              isDemo={isDemo}
              runList={runList}
              currentRunId={currentRunId}
              currentGenNo={currentGenNo}
              onOpenWorkbench={onOpenWorkbench}
            />
            <_RpHistory baseUrl={baseUrl} isDemo={isDemo} runList={runList} onOpenWorkbench={onOpenWorkbench} />
          </div>
        </div>
        {errors.length > 0 && (
          <div className="research-empty danger">
            Parse warnings: {errors.slice(0, 3).map(e => `${e.file}:${e.reason}`).join(" / ")}
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ResearchRecordsPanel });

export { ResearchRecordsPanel };
