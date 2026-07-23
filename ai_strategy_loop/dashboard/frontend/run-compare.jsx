/* Enriched run comparison console. Overrides the lean RunComparePanel from panels.jsx. */
import { fetchRunsShared } from "./runs-shared.jsx";
const { useState: useState_rc, useEffect: useEffect_rc, useMemo: useMemo_rc } = React;

function rcNum(value, digits = 2) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function rcMoney(value) {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString("ko-KR") : "-";
}

function rcPct(value) {
  return typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(2)}%` : "-";
}

function rcDuration(sec) {
  if (typeof sec !== "number" || !Number.isFinite(sec)) return "-";
  if (sec < 60) return `${sec.toFixed(1)}s`;
  const min = Math.floor(sec / 60);
  const rem = Math.round(sec % 60);
  if (min < 60) return `${min}m ${rem}s`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

function rcYears(run) {
  if (Array.isArray(run.years) && run.years.length) return run.years.join(", ");
  if (run.start_year && run.end_year) return `${run.start_year}-${run.end_year}`;
  return "-";
}

function rcWindow(run) {
  const start = run.bt_universe_start_time;
  const end = run.bt_universe_end_time;
  return start || end ? `${start || "-"}~${end || "-"}` : "-";
}

function rcValue(run, key) {
  const v = run[key];
  return typeof v === "number" && Number.isFinite(v) ? v : Number.NEGATIVE_INFINITY;
}

function rcDefaultCompareIds(runs) {
  const matched = runs
    .filter(r => /seed|ai/i.test(String(r.run_id || "")))
    .slice(0, 6)
    .map(r => r.run_id);
  return matched.length >= 2 ? matched : runs.slice(0, 2).map(r => r.run_id);
}

function RunComparePanel({ baseUrl, wsStatus, preferredResearchId, onSelectAnalysis }) {
  const [runs, setRuns] = useState_rc([]);
  const [selected, setSelected] = useState_rc([]);
  const [compareRows, setCompareRows] = useState_rc([]);
  const [sortKey, setSortKey] = useState_rc("final_profit");
  const [err, setErr] = useState_rc("");
  const [loading, setLoading] = useState_rc(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const sortedRuns = useMemo_rc(() => {
    return [...runs].sort((a, b) => rcValue(b, sortKey) - rcValue(a, sortKey));
  }, [runs, sortKey]);

  const refresh = React.useCallback(() => {
    if (isDemo || !baseUrl) return;
    setLoading(true);
    setErr("");
    fetchRunsShared(baseUrl, { timeoutMs: 3000 })
      .then(j => {
        const rows = Array.isArray(j.runs) ? j.runs : [];
        setRuns(rows);
        setErr(j.error || "");
        if (!selected.length) setSelected(rcDefaultCompareIds(rows));
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, selected.length]);

  useEffect_rc(() => { refresh(); }, [refresh]);
  useEffect_rc(() => {
    if (!preferredResearchId || !preferredResearchId.startsWith("loop_run:")) return;
    const runId = preferredResearchId.slice("loop_run:".length);
    if (runs.some(run => run.run_id === runId)) setSelected([runId]);
  }, [preferredResearchId, runs]);

  useEffect_rc(() => {
    if (isDemo || !baseUrl || !selected.length) {
      setCompareRows([]);
      return;
    }
    const ids = selected.map(encodeURIComponent).join(",");
    fetch(baseUrl + "/runs/compare?ids=" + ids, { signal: AbortSignal.timeout(3500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setCompareRows(Array.isArray(j.generation_rows) ? j.generation_rows : []))
      .catch(() => setCompareRows([]));
  }, [baseUrl, isDemo, selected.join("|")]);

  const toggleSelected = (runId) => {
    setSelected(prev => {
      if (prev.includes(runId)) return prev.filter(x => x !== runId);
      return prev.length >= 6 ? prev : prev.concat(runId);
    });
  };

  const selectAnalysis = (run) => {
    if (!run || !run.winner || run.winner.gen_no == null || typeof onSelectAnalysis !== "function") return;
    onSelectAnalysis({ run_id: run.run_id, gen_no: run.winner.gen_no });
  };

  const selectSeedAi = () => setSelected(rcDefaultCompareIds(runs));

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>Run Compare Console
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn ghost sm" onClick={() => setSortKey("final_profit")}>Sort: Total Profit</button>
          <button className="btn ghost sm" onClick={() => setSortKey("total_profit_pct")}>Return %</button>
          <button className="btn ghost sm" onClick={selectSeedAi} disabled={!runs.length}>Seed vs AI</button>
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}>
            {loading ? "loading" : "refresh"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <div className="run-compare-empty">Demo mode: run comparison is available with a backend connection.</div>
        ) : err ? (
          <div className="run-compare-empty danger">query failed: {err}</div>
        ) : runs.length === 0 ? (
          <div className="run-compare-empty">No recorded runs.</div>
        ) : (
          <div className="run-compare-shell">
            {preferredResearchId && !preferredResearchId.startsWith("loop_run:") && (
              <div className="run-compare-empty">선택 연구 {preferredResearchId}는 Run Compare와 호환되지 않습니다. 이 패널은 독립 run 비교입니다.</div>
            )}
            <div className="run-compare-kpis">
              <span>runs={runs.length}</span>
              <span>selected={selected.length}</span>
              <span>generation_rows={compareRows.length}</span>
              <span>sort={sortKey}</span>
            </div>
            <div className="run-compare-scroll run-compare-viewport" data-region="scroll" tabIndex={0} aria-label="run 비교 목록">
              <table className="run-compare-table">
                <thead className="run-compare-sticky-header">
                  <tr>
                    <th>Pick</th><th>run_id</th><th>Status</th><th>Period</th><th>Years</th>
                    <th>min/tick</th><th>Universe Time</th><th>Total Profit</th><th>Return %</th>
                    <th>Trades</th><th>Daily</th><th>MDD</th><th>Payoff</th><th>Max Hold</th>
                    <th>Elapsed</th><th>Cost/Count</th><th>Winner</th><th>Analysis</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRuns.map(r => {
                    const sparseHoldSuspicious = typeof r.max_hold_count === "number"
                      && r.max_hold_count <= 1
                      && (r.trade_count || 0) >= 50;
                    return (
                      <tr key={r.run_id} className={selected.includes(r.run_id) ? "run-compare-row is-selected" : "run-compare-row"}>
                        <td><input type="checkbox" aria-label={`${r.run_id} 비교 선택`} checked={selected.includes(r.run_id)} onChange={() => toggleSelected(r.run_id)} /></td>
                        <td>{r.run_id}</td>
                        <td>{r.status || "-"}</td>
                        <td>{r.period || "-"}</td>
                        <td>{rcYears(r)}</td>
                        <td>{r.timeframe || "-"}</td>
                        <td>{rcWindow(r)}</td>
                        <td className={r.final_profit > 0 ? "num-pos" : r.final_profit < 0 ? "num-neg" : "num-muted"}>{rcMoney(r.final_profit)}</td>
                        <td className={r.total_profit_pct > 0 ? "num-pos" : r.total_profit_pct < 0 ? "num-neg" : "num-muted"}>{rcPct(r.total_profit_pct)}</td>
                        <td>{r.trade_count ?? 0}</td>
                        <td>{rcNum(r.daily_avg_trades, 1)}</td>
                        <td className={r.mdd > 0 ? "num-neg" : "num-muted"}>{rcPct(r.mdd)}</td>
                        <td>{rcNum(r.payoff_ratio, 2)}</td>
                        <td className={sparseHoldSuspicious ? "num-neg" : ""}
                            title={sparseHoldSuspicious
                              ? "Sparse hold warning: max_hold_count <= 1 with enough trades; compare Backtest Detail CSV peak_holdings. human corridor 6-12"
                              : "max_hold_count"}>
                          {rcNum(r.max_hold_count, 0)}{sparseHoldSuspicious ? " !" : ""}
                        </td>
                        <td>{rcDuration(r.elapsed_sec)}</td>
                        <td>{r.cost_or_count_text || rcNum(r.cost_or_count, 1)}</td>
                        <td>{r.winner ? `gen_${String(r.winner.gen_no).padStart(2, "0")} / ${rcNum(r.winner.graded_score, 3)}` : "-"}</td>
                        <td><button className="btn ghost sm" onClick={() => selectAnalysis(r)} disabled={!r.winner || r.winner.gen_no == null}>분석 보기</button></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="run-compare-gen">
              <span>Selected generation preview:</span>
              {compareRows.slice(0, 6).map(row => (
                <span key={`${row.run_id}-${row.gen_no}`}>
                  {row.run_id}/g{row.gen_no}: {rcMoney(row.profit)} ({rcPct(row.return_pct)}) {rcDuration(row.duration_sec)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { RunComparePanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { RunComparePanel };
