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
  if (!ts) return "-";
  try {
    return new Date(Number(ts) * 1000).toLocaleString();
  } catch {
    return "-";
  }
}

function _rrpBestLabel(record) {
  const best = (record && record.best) || {};
  return best.label || best.name || best.strategy_gist || "-";
}

function _rrpCampaignResearchId(row) {
  const researchId = row && row.research_id;
  if (typeof researchId === "string") {
    return researchId.startsWith("campaign:") ? researchId : "";
  }
  const campaignId = row && (row.id || row.name);
  return typeof campaignId === "string" && campaignId ? `campaign:${campaignId}` : "";
}

function ResearchRecordsPanel({ baseUrl, wsStatus, selectedResearchId, onSelectResearch, showRunCompare = true }) {
  const [payload, setPayload] = useState_rrp(null);
  const [selectedCampaign, setSelectedCampaign] = useState_rrp("");
  const [detail, setDetail] = useState_rrp(null);
  const [loading, setLoading] = useState_rrp(false);
  const [err, setErr] = useState_rrp("");
  const [runList, setRunList] = useState_rrp([]);
  const [runListLoading, setRunListLoading] = useState_rrp(false);
  // §10-10 completeness: 12개 초과 campaign 을 조용히 자르지 않고 명시(전체 보기 토글).
  const [showAll, setShowAll] = useState_rrp(false);
  const requestsRef = useRef_rrp({ records: null, runs: null, detail: null });
  const generationRef = useRef_rrp({ records: 0, runs: 0, detail: 0 });
  const controlled = selectedResearchId != null || typeof onSelectResearch === "function";
  const controlledCampaign = typeof selectedResearchId === "string" && selectedResearchId.startsWith("campaign:")
    ? selectedResearchId.slice("campaign:".length) : "";
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const baseIdentity = (isDemo ? "demo:" : "live:") + (baseUrl || "");
  const baseIdentityRef = useRef_rrp(baseIdentity);
  baseIdentityRef.current = baseIdentity;

  useEffect_rrp(() => {
    Object.values(requestsRef.current).forEach(controller => {
      if (controller) controller.abort();
    });
    generationRef.current.records += 1;
    generationRef.current.runs += 1;
    generationRef.current.detail += 1;
    setPayload(null);
    setSelectedCampaign("");
    setDetail(null);
    setLoading(false);
    setErr("");
    setRunList([]);
    setRunListLoading(false);
    setShowAll(false);
  }, [baseIdentity]);

  const refresh = useCallback_rrp(() => {
    if (isDemo || !baseUrl) return;
    if (requestsRef.current.records) requestsRef.current.records.abort();
    const controller = new AbortController();
    const generation = ++generationRef.current.records;
    const requestBase = baseIdentity;
    requestsRef.current.records = controller;
    setLoading(true);
    setErr("");
    const timeoutId = setTimeout(() => controller.abort(), 6000);
    fetch(baseUrl + "/research_records", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        if (!j || typeof j !== "object" || !Array.isArray(j.campaigns) || !Array.isArray(j.errors)
          || !j.campaigns.every(row => row && typeof row === "object" && typeof row.name === "string")
          || !j.errors.every(item => item && typeof item === "object")) {
          throw new Error("Malformed research records response");
        }
        if (generation !== generationRef.current.records || controller.signal.aborted
          || baseIdentityRef.current !== requestBase) return;
        setPayload(j);
        setErr("");
        if (!controlled && !selectedCampaign && j.campaigns.length) setSelectedCampaign(j.campaigns[0].name || "");
      })
      .catch(e => {
        if (generation !== generationRef.current.records || controller.signal.aborted
          || baseIdentityRef.current !== requestBase) return;
        setPayload(null);
        setErr(String(e));
      })
      .finally(() => {
        clearTimeout(timeoutId);
        if (generation === generationRef.current.records && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setLoading(false);
      });
  }, [baseUrl, baseIdentity, isDemo, selectedCampaign, controlled]);

  useEffect_rrp(() => {
    refresh();
    if (isDemo || !baseUrl) return undefined;
    const timer = setInterval(refresh, 60000);
    return () => clearInterval(timer);
  }, [refresh, baseUrl, isDemo]);

  useEffect_rrp(() => {
    if (requestsRef.current.detail) requestsRef.current.detail.abort();
    const requestId = ++generationRef.current.detail;
    const activeCampaign = controlled ? controlledCampaign : selectedCampaign;
    if (isDemo || !baseUrl || !activeCampaign) {
      setDetail(null);
      return undefined;
    }
    const controller = new AbortController();
    const requestBase = baseIdentity;
    requestsRef.current.detail = controller;
    fetch(baseUrl + "/research_records/detail?campaign=" + encodeURIComponent(activeCampaign),
          { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        if (!j || typeof j !== "object" || typeof j.available !== "boolean"
          || (j.available && (!j.campaign || typeof j.campaign !== "object" || j.campaign.name !== activeCampaign))) {
          throw new Error("Malformed research record detail response");
        }
        if (requestId === generationRef.current.detail && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setDetail(j);
      })
      .catch(e => {
        if (e.name !== "AbortError" && requestId === generationRef.current.detail && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setDetail({ available: false, reason: String(e) });
      });
    return () => controller.abort();
  }, [baseUrl, baseIdentity, isDemo, selectedCampaign, controlled, controlledCampaign]);

  const refreshRuns = useCallback_rrp(() => {
    if (isDemo || !baseUrl) return;
    if (requestsRef.current.runs) requestsRef.current.runs.abort();
    const controller = new AbortController();
    const generation = ++generationRef.current.runs;
    const requestBase = baseIdentity;
    requestsRef.current.runs = controller;
    setRunListLoading(true);
    fetchRunsShared(baseUrl, { timeoutMs: 6000, signal: controller.signal })
      .then(j => {
        if (!j || typeof j !== "object" || !Array.isArray(j.runs)
          || !j.runs.every(run => run && typeof run === "object")) {
          throw new Error("Malformed shared runs response");
        }
        if (generation !== generationRef.current.runs || controller.signal.aborted
          || baseIdentityRef.current !== requestBase) return;
        const runs = j.runs.slice();
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      })
      .catch(() => {
        if (generation === generationRef.current.runs && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setRunList([]);
      })
      .finally(() => {
        if (generation === generationRef.current.runs && !controller.signal.aborted
          && baseIdentityRef.current === requestBase) setRunListLoading(false);
      });
  }, [baseUrl, baseIdentity, isDemo]);

  useEffect_rrp(() => {
    refreshRuns();
  }, [refreshRuns]);

  const onOpenWorkbench = useCallback_rrp(() => {
    try {
      window.location.href = "/ui/backtest";
    } catch (e) {}
  }, []);

  const rows = (payload && Array.isArray(payload.campaigns)) ? payload.campaigns : [];
  const activeCampaign = controlled ? controlledCampaign : selectedCampaign;
  const selected = (detail && detail.available && detail.campaign && detail.campaign.name === activeCampaign)
    ? detail.campaign : rows.find(r => r.name === activeCampaign);
  const candidates = (selected && Array.isArray(selected.candidates)) ? selected.candidates.slice(0, 5) : [];
  const errors = (payload && Array.isArray(payload.errors)) ? payload.errors : [];
  const selectedRunId = typeof selectedResearchId === "string" && selectedResearchId.startsWith("loop_run:")
    ? selectedResearchId.slice("loop_run:".length) : "";
  const currentRunId = selectedRunId || (runList.length ? runList[0].run_id : "");
  const currentGenNo = 0;
  const selectCampaign = row => {
    setSelectedCampaign(row.name || "");
    const researchId = _rrpCampaignResearchId(row);
    if (researchId && typeof onSelectResearch === "function") onSelectResearch(researchId);
  };

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
        {rows.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
              <thead>
                <tr style={{ color: "var(--ink-3)" }}>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Campaign</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Candidates</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Best PnL</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>MDD</th>
                  <th style={{ textAlign: "left", padding: "6px 8px" }}>Artifacts</th>
                  <th style={{ textAlign: "right", padding: "6px 8px" }}>Updated</th>
                </tr>
              </thead>
              <tbody>
                {(showAll ? rows : rows.slice(0, 12)).map(row => {
                  const best = row.best || {};
                  const artifacts = row.artifacts || {};
                  const active = row.name === activeCampaign;
                  return (
                    <tr key={row.name} style={{
                      borderTop: "1px solid var(--line-1)",
                      background: active ? "rgba(56, 189, 248, 0.08)" : "transparent",
                    }}>
                      <td style={{ padding: "7px 8px", minWidth: 180 }}>
                        <button className="btn ghost sm" onClick={() => selectCampaign(row)}
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
        {selected && (
          <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 1fr) minmax(260px, 1.3fr)", gap: 12 }}>
            <div style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 10 }}>
              <div className="stat-label" style={{ marginBottom: 6 }}>Selected</div>
              <div className="mono" style={{ color: "var(--ink-0)", marginBottom: 6 }}>{selected.name}</div>
              <div className="mono" style={{ color: "var(--ink-2)", fontSize: 11 }}>
                best={_rrpBestLabel(selected)}
              </div>
              <div className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5, marginTop: 6 }}>
                source={(payload && payload.root) || "-"}
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
              히스토리 ResultDetail{showRunCompare ? " · Compare" : ""}
            </div>
            <button className="btn ghost sm" onClick={refreshRuns} disabled={isDemo || runListLoading}>
              {runListLoading ? "run 로딩…" : "run 새로고침"}
            </button>
          </div>
          <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
              History가 과거 run/gen 아카이브와 Compare를 소유합니다. Workbench는 깊은 분석으로 연결만 제공합니다.
            </div>
            {showRunCompare && (
              <_RpRunCompare
                baseUrl={baseUrl}
                isDemo={isDemo}
                runList={runList}
                currentRunId={currentRunId}
                currentGenNo={currentGenNo}
                onOpenWorkbench={onOpenWorkbench}
              />
            )}
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
