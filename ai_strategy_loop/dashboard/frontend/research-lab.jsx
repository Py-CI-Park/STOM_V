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
  { id: "validation", label: "Validation" },
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
        const score = typeof row.research_score === "number" ? row.research_score : null;
        return (
          <div key={i} className="research-combo-row">
            <span className="mono">{a}</span>
            <span className="research-muted">x</span>
            <span className="mono">{b}</span>
            <strong style={{ color: _rlCorrColor(score == null ? corr : score) }}>
              {score == null ? _rlNum(corr, 3) : _rlNum(score, 3)}
            </strong>
            <small>sample count {row.sample_count || row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

function _RangeSummaryList({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient range_summaries for histogram research." />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row" title="histogram and win/loss range contrast">
          <span className="mono">{row.feature}</span>
          <span>median {_rlNum(row.median, 2)}</span>
          <span>q25-q75 {_rlNum(row.q25, 2)}~{_rlNum(row.q75, 2)}</span>
          <span>win/loss Δ {_rlNum(row.win_loss && row.win_loss.mean_delta, 3)}</span>
          <small>histogram {(row.histogram || []).map(b => b.count).join("/")}</small>
        </div>
      ))}
    </div>
  );
}

function _SegmentSummaryList({ summary, axis }) {
  const rows = summary && Array.isArray(summary[axis]) ? summary[axis] : [];
  if (rows.length === 0) {
    return <_ResearchEmptyState message={"insufficient segment_summaries for " + axis + "."} />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row">
          <span className="mono">{axis}:{row.label}</span>
          <span>avg {_rlNum(row.avg_return, 3)}</span>
          <span>win {_rlNum(row.win_rate, 3)}</span>
          <small>sample count {row.sample_count || 0}</small>
        </div>
      ))}
    </div>
  );
}

function _RecencyResearchBadge({ recency }) {
  if (!recency) return null;
  return (
    <div className="research-empty" title="research_score_not_promotion">
      recency_research · {recency.score_label || "research_score_not_promotion"} ·
      score {_rlNum(recency.research_score, 4)}
    </div>
  );
}

/* D1/D2/D4(2026-06-10) — 검증 패널: 연도 분해 · 선택기 미리보기 · 부검 요약.
   읽기 전용 GET 3종(/run_yearly /selector_preview /autopsy)만 소비한다.
   근거: 원인5(연도별 쇠퇴는 합계로 안 보임)·원인1(기준-목표 비정합을 눈으로 확인). */
function _ValidationPanel({ baseUrl, runId, isDemo }) {
  const [selector, setSelector] = useState_rl("seed_relative_v1");
  const [yearly, setYearly] = useState_rl(null);
  const [preview, setPreview] = useState_rl(null);
  const [autopsyGen, setAutopsyGen] = useState_rl(0);
  const [autopsy, setAutopsy] = useState_rl(null);
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const refresh = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const yUrl = baseUrl + "/run_yearly?run_id=" + encodeURIComponent(runId);
    const pUrl = baseUrl + "/selector_preview?run_id=" + encodeURIComponent(runId)
      + "&selector=" + encodeURIComponent(selector);
    Promise.all([
      fetch(yUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
      fetch(pUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
    ])
      .then(([y, p]) => { setYearly(y); setPreview(p); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, selector]);

  useEffect_rl(() => { refresh(); }, [refresh]);

  const fetchAutopsy = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const url = baseUrl + "/autopsy?run_id=" + encodeURIComponent(runId)
      + "&gen_no=" + encodeURIComponent(autopsyGen);
    fetch(url, { signal: AbortSignal.timeout(10000) })
      .then(r => r.ok ? r.json() : null)
      .then(j => setAutopsy(j))
      .catch(e => setErr(String(e)));
  }, [autopsyGen, baseUrl, isDemo, runId]);

  if (isDemo || !runId) {
    return <div className="research-lab-panel"><_ResearchEmptyState message="insufficient run context for validation views." /></div>;
  }

  const gens = (yearly && Array.isArray(yearly.generations)) ? yearly.generations : [];
  return (
    <div className="research-lab-panel">
      <div className="research-controls">
        <label>
          <span>selector</span>
          <select value={selector} onChange={(e) => setSelector(e.target.value)} disabled={loading}>
            <option value="seed_relative_v1">seed_relative_v1</option>
            <option value="sparse_positive_v1">sparse_positive_v1</option>
          </select>
        </label>
        <span className="research-empty">diagnostic_only · 동결 아티팩트 아님</span>
      </div>
      {err && <_ResearchEmptyState message={"insufficient response: " + err} />}

      <div className="research-empty" style={{ marginTop: 6 }}>연도 분해 (per-trade CSV 집계)</div>
      <table className="mono" style={{ fontSize: 11, width: "100%" }}>
        <thead><tr><th>gen</th><th>label</th><th>연도별 손익(거래수·승률)</th></tr></thead>
        <tbody>
          {gens.map(g => (
            <tr key={g.gen_no}>
              <td>{g.gen_no}</td>
              <td>{g.label || g.buy_name || "—"}</td>
              <td>
                {(g.years || []).length
                  ? g.years.map(y => `${y.year}: ${Math.round(y.profit).toLocaleString()} (${y.trades}건·${Math.round((y.win_rate || 0) * 100)}%)`).join("  ·  ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="research-empty" style={{ marginTop: 8 }}>
        선택기 미리보기 — selected: {preview && preview.selected ? "TRUE" : "false"}
        {preview && preview.mdd_limit != null ? ` · mdd_limit ${_rlNum(preview.mdd_limit, 2)}` : ""}
        {preview && preview.selected_candidate
          ? ` · gen${preview.selected_candidate.gen_no} ${preview.selected_candidate.label || preview.selected_candidate.buy_name}`
          : ""}
      </div>
      {preview && Array.isArray(preview.rejected) && preview.rejected.length > 0 && (
        <ul className="mono" style={{ fontSize: 11 }}>
          {preview.rejected.map(rj => (
            <li key={rj.gen_no}>gen{rj.gen_no} {rj.label || ""}: {(rj.reasons || []).join("; ")}</li>
          ))}
        </ul>
      )}

      <div className="research-controls" style={{ marginTop: 8 }}>
        <label>
          <span>autopsy gen</span>
          <input type="number" value={autopsyGen} min={0}
                 onChange={(e) => setAutopsyGen(Number(e.target.value) || 0)}
                 style={{ width: 64 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchAutopsy}>부검 보기</button>
      </div>
      {autopsy && (
        <div className="mono" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
          {autopsy.status !== "ok"
            ? `autopsy: ${autopsy.status}`
            : `${autopsy.entry_summary || "(진입 부검 없음)"}\n\n${autopsy.exit_summary || "(청산 부검 없음)"}`}
        </div>
      )}
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
  const rangeRows = (data && Array.isArray(data.range_summaries)) ? data.range_summaries : [];
  const segmentSummary = (data && data.segment_summaries) || {};
  const recencyResearch = (data && data.recency_research) || null;
  const pairRows = useMemo_rl(() => {
    const raw = (data && Array.isArray(data.interaction_candidates) && data.interaction_candidates.length)
      ? data.interaction_candidates
      : ((data && Array.isArray(data.top_pairs) && data.top_pairs.length) ? data.top_pairs : matrixRows);
    return [...raw].sort((a, b) => (
      (b.research_score || b.abs_correlation || Math.abs(b.correlation || 0))
      - (a.research_score || a.abs_correlation || Math.abs(a.correlation || 0))
    ));
  }, [data, matrixRows]);

  let body = null;
  if (tab === "edge") {
    body = <EdgeRatioPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />;
  } else if (tab === "validation") {
    body = <_ValidationPanel baseUrl={baseUrl} runId={runId} isDemo={isDemo} />;
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
        <_RangeSummaryList rows={rangeRows} />
        <_SegmentSummaryList summary={segmentSummary} axis={axis} />
        <_RecencyResearchBadge recency={recencyResearch} />
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
