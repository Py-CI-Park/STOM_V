/* v4-research-program.jsx — v5.16 read-only research program cockpit overview. */
const { useCallback: useCallback_rp16, useEffect: useEffect_rp16, useState: useState_rp16 } = React;

function _Rp16Badge({ label, value, tone = "neutral" }) {
  return <span className={`rp16-badge ${tone}`}><span>{label}</span><b>{value == null ? "—" : String(value)}</b></span>;
}

function _Rp16Scope({ scope, authority }) {
  const rows = [
    ["DATA", scope && scope.source || "existing_database_only"],
    ["LANE", scope && scope.lane || "pending_census"],
    ["WINDOW", scope && scope.window_contract || "pending_census"],
    ["DB", scope && scope.operational_db || "read_only"],
    ["AUTHORITY", authority || "development_no_adoption"],
  ];
  return (
    <div className="rp16-scope" role="list" aria-label="연구 데이터 범위와 권위">
      {rows.map(([key, value]) => <div key={key} role="listitem"><span>{key}</span><b>{value}</b></div>)}
    </div>
  );
}

function _Rp16Funnel({ funnel }) {
  const rows = [
    ["생성", "generated"], ["실행계약", "execution_contract"],
    ["공식엔진", "official_engine_rows"], ["국소 양수", "local_positive"],
    ["개발 Rule-pass", "development_rule_pass"], ["Bayesian 승인", "bayesian_approve"],
    ["BO 적격", "bo_eligible"],
  ];
  return (
    <ol className="rp16-funnel" aria-label="조건식 연구 퍼널">
      {rows.map(([label, key], index) => (
        <li key={key}><span>{index + 1}</span><b>{label}</b><strong>{Number(funnel && funnel[key] || 0).toLocaleString()}</strong></li>
      ))}
    </ol>
  );
}

function V516ResearchProgramOverview({ baseUrl }) {
  const [view, setView] = useState_rp16({ status: "loading", data: null, error: "" });
  const load = useCallback_rp16(() => {
    const controller = new AbortController();
    setView(current => ({ ...current, status: "loading", error: "" }));
    const endpoint = String(baseUrl || "").replace(/\/$/, "") + "/research-program/summary";
    fetch(endpoint, { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(data => setView({ status: "ready", data, error: "" }))
      .catch(error => {
        if (error && error.name !== "AbortError") setView({ status: "error", data: null, error: String(error.message || error) });
      });
    return () => controller.abort();
  }, [baseUrl]);
  useEffect_rp16(() => load(), [load]);

  if (view.status === "loading" && !view.data) return <section className="rp16-overview pending" aria-live="polite"><h2>Research Program</h2><p>연구 원장과 Evidence를 불러오는 중입니다.</p></section>;
  if (view.status === "error") return (
    <section className="rp16-overview danger" role="alert">
      <h2>Research Program 요청 실패</h2><p>{view.error}</p><button type="button" className="btn" onClick={load}>다시 시도</button>
    </section>
  );
  const data = view.data || {};
  const platform = data.platform || {};
  const economic = data.economic || {};
  const phases = data.phases || {};
  return (
    <section className="rp16-overview" aria-labelledby="rp16-overview-title">
      <div className="rp16-heading">
        <div><span className="eyebrow">v5.16 PROGRAM COCKPIT</span><h2 id="rp16-overview-title">기존 DB 조건식 연구 현황</h2></div>
        <div className="rp16-badges" aria-label="연구 최상위 판정">
          <_Rp16Badge label="플랫폼" value={platform.verdict || "SOURCE_UNAVAILABLE"} tone={platform.verdict === "PASS" ? "safe" : "warn"} />
          <_Rp16Badge label="경제 판정" value={economic.verdict || "SOURCE_UNAVAILABLE"} tone="danger" />
          <_Rp16Badge label="Robust" value={economic.robust_candidates || 0} />
          <_Rp16Badge label="BO" value={economic.bo_eligible || 0} />
        </div>
      </div>
      <_Rp16Scope scope={data.data_scope} authority={data.authority} />
      <div className="rp16-grid">
        <div className="rp16-card"><h3>연구 Funnel</h3><_Rp16Funnel funnel={data.funnel || {}} /></div>
        <div className="rp16-card"><h3>단계 Timeline</h3><table><thead><tr><th>단계</th><th>봉인 판정</th></tr></thead><tbody>{["D1", "D2", "PAIRED"].map(key => <tr key={key}><th>{key}</th><td>{phases[key] || "SOURCE_UNAVAILABLE"}</td></tr>)}</tbody></table></div>
      </div>
      <p className="rp16-authority"><b>DEVELOPMENT ONLY</b> · 기존 결과는 OOS·실전·자동채택 근거가 아닙니다. 플랫폼 PASS와 경제적 성공은 별도 판정입니다.</p>
    </section>
  );
}

Object.assign(window, { V516ResearchProgramOverview });
export { V516ResearchProgramOverview };
