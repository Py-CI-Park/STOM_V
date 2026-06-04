/* ResearchLabPanel - compact analysis workspace for Edge, Feature, Correlation, and Variable Combinations. */

const {
  useState: useState_rl,
  useEffect: useEffect_rl,
  useCallback: useCallback_rl,
  useMemo: useMemo_rl,
} = React;

const RESEARCH_TABS = [
  { id: "edge", label: "Edge" },
  { id: "feature", label: "Feature Importance" },
  { id: "correlation", label: "Correlation" },
  { id: "combos", label: "Variable Combinations" },
];

function _rlNum(value, digits) {
  if (typeof value !== "number" || !isFinite(value)) return "--";
  return value.toFixed(digits == null ? 3 : digits);
}

function _rlCorrColor(value) {
  if (typeof value !== "number" || !isFinite(value)) return "rgba(80,96,116,0.48)";
  const t = Math.min(1, Math.abs(value));
  if (value >= 0) return `rgba(${Math.round(35 + 30 * (1 - t))},${Math.round(130 + 70 * t)},${Math.round(126 + 40 * t)},0.86)`;
  return `rgba(${Math.round(178 + 48 * t)},${Math.round(108 - 32 * t)},${Math.round(62 - 24 * t)},0.86)`;
}

function _ResearchEmptyState({ message }) {
  return (
    <div className="research-empty">
      {message || "insufficient data for the selected research view."}
    </div>
  );
}

function _CorrelationControls({ method, setMethod, axis, setAxis, loading, pooledTrades, featureCount }) {
  return (
    <div className="research-controls">
      <label>
        <span>method</span>
        <select value={method} onChange={(e) => setMethod(e.target.value)} disabled={loading}>
          <option value="pearson">pearson</option>
          <option value="spearman">spearman</option>
        </select>
      </label>
      <label>
        <span>segment axis</span>
        <select value={axis} onChange={(e) => setAxis(e.target.value)}>
          <option value="time">time</option>
          <option value="market_cap">market_cap</option>
          <option value="change">change</option>
        </select>
      </label>
      <div className="research-kpis">
        <span>sample count {_rlNum(pooledTrades, 0)}</span>
        <span>features {_rlNum(featureCount, 0)}</span>
      </div>
    </div>
  );
}

function _CorrelationHeatmap({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient feature_matrix rows for a correlation heatmap." />;
  }
  return (
    <div className="research-heatmap">
      {rows.slice(0, 36).map((row, i) => {
        const label = [row.feature_a, row.feature_b].filter(Boolean).join(" / ") || row.feature || ("feature_" + i);
        const corr = typeof row.correlation === "number" ? row.correlation : null;
        return (
          <div key={i}
               className="research-cell"
               style={{ background: _rlCorrColor(corr) }}
               title={`${label} | correlation ${_rlNum(corr, 4)} | sample count ${row.n || 0}`}>
            <strong>{label}</strong>
            <span>{_rlNum(corr, 3)}</span>
            <small>n={row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

function _CombinationList({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient variable combinations for the selected run." />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 14).map((row, i) => {
        const a = row.feature_a || row.feature || "feature_a";
        const b = row.feature_b || "feature_b";
        const corr = typeof row.correlation === "number" ? row.correlation : null;
        return (
          <div key={i} className="research-combo-row">
            <span className="mono">{a}</span>
            <span className="research-muted">x</span>
            <span className="mono">{b}</span>
            <strong style={{ color: _rlCorrColor(corr) }}>{_rlNum(corr, 3)}</strong>
            <small>sample count {row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

function ResearchLabPanel({ baseUrl, wsStatus, runId }) {
  const [tab, setTab] = useState_rl("edge");
  const [method, setMethod] = useState_rl("spearman");
  const [axis, setAxis] = useState_rl("time");
  const [data, setData] = useState_rl(null);
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const needsCorrelation = tab === "correlation" || tab === "combos";

  const refreshCorrelation = useCallback_rl(() => {
    if (!needsCorrelation || isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const url = baseUrl + "/variable_correlation?run_id=" + encodeURIComponent(runId)
      + "&method=" + encodeURIComponent(method);
    fetch(url, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, method, needsCorrelation, runId]);

  useEffect_rl(() => {
    refreshCorrelation();
  }, [refreshCorrelation]);

  const matrixRows = (data && Array.isArray(data.feature_matrix)) ? data.feature_matrix : [];
  const outcomeRows = (data && Array.isArray(data.outcome_correlations)) ? data.outcome_correlations : [];
  const pairRows = useMemo_rl(() => {
    const raw = (data && Array.isArray(data.top_pairs) && data.top_pairs.length) ? data.top_pairs : matrixRows;
    return [...raw].sort((a, b) => (b.abs_correlation || Math.abs(b.correlation || 0)) - (a.abs_correlation || Math.abs(a.correlation || 0)));
  }, [data, matrixRows]);

  let body = null;
  if (tab === "edge") {
    body = <EdgeRatioPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />;
  } else if (tab === "feature") {
    body = (
      <div>
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <FeatureImportancePanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </div>
    );
  } else if (isDemo || !runId) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="insufficient run context for correlation research." /></div>;
  } else if (err) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message={"insufficient response: " + err} /></div>;
  } else if (loading && !data) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="loading correlation research..." /></div>;
  } else if (tab === "correlation") {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CorrelationHeatmap rows={matrixRows.length ? matrixRows : outcomeRows} />
      </div>
    );
  } else {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CombinationList rows={pairRows} />
      </div>
    );
  }

  return (
    <div className="research-lab-shell">
      <div className="research-tabs" role="tablist" aria-label="Research Lab">
        {RESEARCH_TABS.map(item => (
          <button key={item.id}
                  type="button"
                  className={"research-tab" + (tab === item.id ? " active" : "")}
                  onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      {body}
    </div>
  );
}

Object.assign(window, { ResearchLabPanel });
