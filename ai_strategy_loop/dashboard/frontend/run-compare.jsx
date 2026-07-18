/* Enriched run comparison console. Overrides the lean RunComparePanel from panels.jsx. */
const { useState: useState_rc, useEffect: useEffect_rc, useMemo: useMemo_rc, useRef: useRef_rc } = React;

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
function rcValidRunsPayload(payload) {
  return !!payload
    && typeof payload === "object"
    && Array.isArray(payload.runs)
    && payload.runs.every(run => run && typeof run === "object"
      && typeof run.run_id === "string" && run.run_id.length > 0);
}

function rcValidCompareRows(payload, selectedIds) {
  if (!payload || typeof payload !== "object"
      || !Array.isArray(payload.runs) || !Array.isArray(payload.generation_rows)) return null;
  const selectedSet = new Set(selectedIds);
  const ownsSelectedRun = row => row && typeof row === "object"
    && typeof row.run_id === "string" && selectedSet.has(row.run_id);
  if (!payload.runs.every(ownsSelectedRun) || !payload.generation_rows.every(ownsSelectedRun)) return null;
  return payload.generation_rows;
}

function RunComparePanel({ baseUrl, wsStatus }) {
  const [runs, setRuns] = useState_rc([]);
  const [selected, setSelected] = useState_rc([]);
  const [compareRows, setCompareRows] = useState_rc([]);
  const [sortKey, setSortKey] = useState_rc("final_profit");
  const [err, setErr] = useState_rc("");
  const [loading, setLoading] = useState_rc(false);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const runsRequestRef = useRef_rc({ generation: 0, controller: null, baseUrl: "" });
  const compareRequestRef = useRef_rc({ generation: 0, controller: null, baseUrl: "", selectedKey: "" });

  const sortedRuns = useMemo_rc(() => {
    return [...runs].sort((a, b) => rcValue(b, sortKey) - rcValue(a, sortKey));
  }, [runs, sortKey]);

  const refresh = React.useCallback(() => {
    if (runsRequestRef.current.controller) runsRequestRef.current.controller.abort();
    const controller = new AbortController();
    const generation = runsRequestRef.current.generation + 1;
    const identity = baseUrl || "";
    runsRequestRef.current = { generation, controller, baseUrl: identity };
    if (isDemo || !identity) {
      setRuns([]);
      setSelected([]);
      setCompareRows([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setErr("");
    const timeoutId = setTimeout(() => controller.abort(), 3000);
    fetch(identity + "/runs", { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        const current = runsRequestRef.current;
        if (current.generation !== generation || current.baseUrl !== identity) return;
        if (!rcValidRunsPayload(j)) throw new Error("Malformed /runs response");
        const rows = j.runs;
        setRuns(rows);
        setErr(typeof j.error === "string" ? j.error : "");
        setSelected(prev => prev.length ? prev : rcDefaultCompareIds(rows));
      })
      .catch(e => {
        const current = runsRequestRef.current;
        if (current.generation !== generation || current.baseUrl !== identity || controller.signal.aborted) return;
        setRuns([]);
        setSelected([]);
        setCompareRows([]);
        setErr(String(e));
      })
      .finally(() => {
        clearTimeout(timeoutId);
        const current = runsRequestRef.current;
        if (current.generation === generation && current.baseUrl === identity) setLoading(false);
      });
  }, [baseUrl, isDemo]);

  useEffect_rc(() => {
    if (runsRequestRef.current.controller) runsRequestRef.current.controller.abort();
    if (compareRequestRef.current.controller) compareRequestRef.current.controller.abort();
    runsRequestRef.current.generation += 1;
    compareRequestRef.current.generation += 1;
    setRuns([]);
    setSelected([]);
    setCompareRows([]);
    setErr("");
    setLoading(false);
    return () => {
      if (runsRequestRef.current.controller) runsRequestRef.current.controller.abort();
      if (compareRequestRef.current.controller) compareRequestRef.current.controller.abort();
      runsRequestRef.current.generation += 1;
      compareRequestRef.current.generation += 1;
    };
  }, [baseUrl, isDemo]);

  useEffect_rc(() => { refresh(); }, [refresh]);

  useEffect_rc(() => {
    if (compareRequestRef.current.controller) compareRequestRef.current.controller.abort();
    const controller = new AbortController();
    const generation = compareRequestRef.current.generation + 1;
    const identity = baseUrl || "";
    const selectedIds = selected.slice();
    const selectedKey = selectedIds.join("|");
    compareRequestRef.current = { generation, controller, baseUrl: identity, selectedKey };
    if (isDemo || !identity || !selectedIds.length) {
      setCompareRows([]);
      return () => controller.abort();
    }
    setCompareRows([]);
    const timeoutId = setTimeout(() => controller.abort(), 3500);
    const ids = selectedIds.map(encodeURIComponent).join(",");
    fetch(identity + "/runs/compare?ids=" + ids, { signal: controller.signal })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        const current = compareRequestRef.current;
        if (current.generation !== generation || current.baseUrl !== identity || current.selectedKey !== selectedKey) return;
        const rows = rcValidCompareRows(j, selectedIds);
        if (rows === null) throw new Error("Malformed /runs/compare response");
        setCompareRows(rows);
      })
      .catch(() => {
        const current = compareRequestRef.current;
        if (current.generation === generation && current.baseUrl === identity
            && current.selectedKey === selectedKey && !controller.signal.aborted) setCompareRows([]);
      })
      .finally(() => clearTimeout(timeoutId));
    return () => controller.abort();
  }, [baseUrl, isDemo, selected.join("|")]);

  const toggleSelected = (runId) => {
    setSelected(prev => prev.includes(runId) ? prev.filter(x => x !== runId) : [...prev, runId]);
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
            <div className="run-compare-kpis">
              <span>runs={runs.length}</span>
              <span>selected={selected.length}</span>
              <span>generation_rows={compareRows.length}</span>
              <span>sort={sortKey}</span>
            </div>
            <div className="run-compare-scroll">
              <table className="run-compare-table">
                <thead>
                  <tr>
                    <th>Pick</th><th>run_id</th><th>Status</th><th>Period</th><th>Years</th>
                    <th>min/tick</th><th>Universe Time</th><th>Total Profit</th><th>Return %</th>
                    <th>Trades</th><th>Daily</th><th>MDD</th><th>Payoff</th><th>Max Hold</th>
                    <th>Elapsed</th><th>Cost/Count</th><th>Winner</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedRuns.map(r => {
                    const sparseHoldSuspicious = typeof r.max_hold_count === "number"
                      && r.max_hold_count <= 1
                      && (r.trade_count || 0) >= 50;
                    return (
                      <tr key={r.run_id}>
                        <td><input type="checkbox" checked={selected.includes(r.run_id)} onChange={() => toggleSelected(r.run_id)} /></td>
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
