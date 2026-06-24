/* Evolution generation GUI-parity panel. */
import { BtGuiParitySection } from "./bt-gui-parity.jsx";

const {
  useState: useState_egpp,
  useEffect: useEffect_egpp,
  useCallback: useCallback_egpp,
  useMemo: useMemo_egpp,
} = React;

function _egppDefaultGen(gens) {
  if (!gens.length) return null;
  const winners = gens.filter(g => g.gate_passed);
  if (winners.length) {
    return winners.reduce((a, b) => ((b.graded_score || 0) > (a.graded_score || 0) ? b : a)).gen_no;
  }
  return gens[gens.length - 1].gen_no;
}

function _egppSummary(summary) {
  const s = summary || {};
  return [
    ["trades", s.trade_count],
    ["profit", s.total_profit],
    ["mdd", s.max_drawdown_pct],
  ];
}

function EvolutionGuiParityPanel({ baseUrl, wsStatus, state, externalSelGen }) {
  const gens = (state && Array.isArray(state.generations)) ? state.generations : [];
  const runId = (state && state.run_id) || "";
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const defaultGen = useMemo_egpp(() => _egppDefaultGen(gens), [gens]);
  const genNo = externalSelGen != null ? externalSelGen : defaultGen;
  const [payload, setPayload] = useState_egpp(null);
  const [loading, setLoading] = useState_egpp(false);
  const [err, setErr] = useState_egpp("");

  const refresh = useCallback_egpp(() => {
    if (isDemo || !baseUrl || !runId || genNo == null) {
      setPayload(null);
      return;
    }
    setLoading(true);
    const url = baseUrl + "/evolution_gui_parity?run_id=" + encodeURIComponent(runId)
      + "&gen_no=" + encodeURIComponent(genNo);
    fetch(url, { signal: AbortSignal.timeout(6000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        setPayload(j);
        setErr("");
      })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, genNo, isDemo, runId]);

  useEffect_egpp(() => {
    refresh();
    if (isDemo || !baseUrl || !runId || genNo == null) return undefined;
    const timer = setInterval(refresh, 30000);
    return () => clearInterval(timer);
  }, [refresh, baseUrl, genNo, isDemo, runId]);

  const guiParity = payload && payload.gui_parity ? payload.gui_parity : null;
  const reason = payload && payload.reason ? payload.reason : (isDemo ? "demo" : "pending");
  const summary = payload && payload.summary ? payload.summary : {};
  const chips = _egppSummary(summary);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">
            <span className="dot" style={{ background: "var(--blue)" }}></span>
            Evolution GUI Parity
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
              run={runId || "-"} / gen={genNo != null ? genNo : "-"}
            </span>
            <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading || !runId || genNo == null}>
              {loading ? "Loading" : "Refresh"}
            </button>
          </div>
        </div>
        <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {err && <div className="research-empty danger">{err}</div>}
          <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
            <span className="mono" style={{ color: payload && payload.available ? "var(--teal)" : "var(--ink-3)" }}>
              status={reason}
            </span>
            <span className="mono" style={{ color: payload && payload.csv_path_found ? "var(--teal)" : "var(--ink-3)" }}>
              csv={payload && payload.csv_path_found ? "found" : "missing"}
            </span>
            <span className="mono" style={{ color: payload && payload.gate_passed ? "var(--teal)" : "var(--ink-3)" }}>
              gate={payload && payload.gate_passed ? "passed" : "-"}
            </span>
            <span className="mono" style={{ color: "var(--ink-2)" }}>
              externalSelGen={externalSelGen != null ? externalSelGen : "-"}
            </span>
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {chips.map(([label, value]) => (
              <div key={label} style={{ minWidth: 110 }}>
                <div className="stat-label">{label}</div>
                <div className="mono" style={{ color: "var(--ink-0)" }}>
                  {value == null ? "-" : String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
      <BtGuiParitySection guiParity={guiParity} layoutMode="large-one-column" />
    </div>
  );
}

Object.assign(window, { EvolutionGuiParityPanel });

export { EvolutionGuiParityPanel };
