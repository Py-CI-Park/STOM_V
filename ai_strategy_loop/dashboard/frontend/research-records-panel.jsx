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

function ResearchRecordsPanel({ baseUrl, wsStatus }) {
  const [payload, setPayload] = useState_rrp(null);
  const [selectedCampaign, setSelectedCampaign] = useState_rrp("");
  const [detail, setDetail] = useState_rrp(null);
  const [loading, setLoading] = useState_rrp(false);
  const [err, setErr] = useState_rrp("");
  const [runList, setRunList] = useState_rrp([]);
  const [runListLoading, setRunListLoading] = useState_rrp(false);
  // §10-10 completeness: 12개 초과 campaign 을 조용히 자르지 않고 명시(전체 보기 토글).
  const [showAll, setShowAll] = useState_rrp(false);
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
        if (!selectedCampaign && rows.length) setSelectedCampaign(rows[0].name || "");
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, selectedCampaign]);

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
    // V5.4(§10-10): 세대 가드 — 늦게 도착한 이전 선택 응답이 새 선택을 덮어쓰지 않게 한다.
    const reqId = ++detailReqRef.current;
    const forCampaign = selectedCampaign;
    let cancelled = false;
    fetch(baseUrl + "/research_records/detail?campaign=" + encodeURIComponent(selectedCampaign),
          { signal: AbortSignal.timeout(6000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => { if (!cancelled && reqId === detailReqRef.current) setDetail(Object.assign({ __campaign: forCampaign }, j)); })
      .catch(e => { if (!cancelled && reqId === detailReqRef.current) setDetail({ available: false, reason: String(e), __campaign: forCampaign }); });
    return () => { cancelled = true; };
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
      window.location.href = "/ui/backtest";
    } catch (e) {}
  }, []);

  const rows = (payload && Array.isArray(payload.campaigns)) ? payload.campaigns : [];
  const selected = (detail && detail.available && detail.campaign)
    ? detail.campaign : rows.find(r => r.name === selectedCampaign);
  const candidates = (selected && Array.isArray(selected.candidates)) ? selected.candidates.slice(0, 5) : [];
  const errors = (payload && Array.isArray(payload.errors)) ? payload.errors : [];
  const currentRunId = runList.length ? runList[0].run_id : "";
  const currentGenNo = 0;

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
                  const active = row.name === selectedCampaign;
                  return (
                    <tr key={row.name} style={{
                      borderTop: "1px solid var(--line-1)",
                      background: active ? "rgba(56, 189, 248, 0.08)" : "transparent",
                    }}>
                      <td style={{ padding: "7px 8px", minWidth: 180 }}>
                        <button className="btn ghost sm" onClick={() => setSelectedCampaign(row.name)}
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
                root={(payload && payload.root) || "-"}
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
