/* QSP7 analysis, official pair, and append-only evidence in History. */
const { useState: useState_tph, useEffect: useEffect_tph } = React;

function BtTradePathHistory({ baseUrl, active }) {
  const [payload, setPayload] = useState_tph(null);
  useEffect_tph(() => {
    if (!active || !baseUrl) return undefined;
    const controller = new AbortController();
    fetch(baseUrl + "/bt/trade-path/history", { signal: controller.signal })
      .then(response => response.json())
      .then(setPayload)
      .catch(() => setPayload({ available: false }));
    return () => controller.abort();
  }, [baseUrl, active]);
  if (!active) return null;

  const analyses = (payload && payload.analyses) || [];
  const pairs = (payload && payload.official_pairs) || [];
  const records = (payload && payload.records) || [];
  const persisted = (payload && payload.persisted) || [];
  const reopen = analysisId => {
    // P4 — get() 이 sidecar 에서 투명 복원하므로 상태 조회만으로 다시 열린다.
    fetch(baseUrl + "/bt/trade-path/jobs/" + encodeURIComponent(analysisId))
      .then(response => response.json())
      .then(() => fetch(baseUrl + "/bt/trade-path/history").then(r => r.json()).then(setPayload))
      .catch(() => {});
  };
  return (
    <details className="evo-group" open>
      <summary className="evo-group-summary">
        <h2 className="stom-section-label">QSP7 거래 경로·공식 pair 원장</h2>
      </summary>
      <div className="evo-group-body tp-history-grid">
        <section>
          <b>진단 분석</b>
          {!analyses.length ? <p className="tp-empty">이 프로세스에서 실행한 거래 경로 분석이 없습니다.</p> : analyses.map(row => (
            <article key={row.analysis_id}>
              <span className={`tp-status ${row.status}`}>{row.status}</span>
              <code>{row.analysis_id}</code>
              <small>{row.summary ? `분석 ${row.summary.analyzed_count} · 제외 ${row.summary.excluded_count}` : `진행 ${Math.round((row.progress || 0) * 100)}%`}</small>
            </article>
          ))}
        </section>
        <section>
          <b>보존된 분석 (재시작 후에도 유지)</b>
          {!persisted.length ? <p className="tp-empty">sidecar 원장에 보존된 분석이 없습니다.</p> : persisted.slice(0, 10).map(row => (
            <article key={row.analysis_id}>
              <span className={`tp-lane-badge ${row.lane}`}>{row.lane}</span>
              <code>{row.analysis_id}</code>
              <small>분석 {row.totals?.analyzed_count ?? 0}건 · {String(row.created_at || "").slice(0, 19)}</small>
              <button className="btn ghost sm" onClick={() => reopen(row.analysis_id)}>다시 열기</button>
            </article>
          ))}
        </section>
        <section>
          <b>정본 pair</b>
          {!pairs.length ? <p className="tp-empty">비교된 공식 job pair가 없습니다.</p> : pairs.map((row, index) => (
            <article key={index}>
              <span className="tp-authority official">정본</span>
              <code>{row.pair.baseline_job_id} → {row.pair.candidate_job_id}</code>
              <small>손익 변화 {Number(row.pair.delta_profit_krw).toLocaleString()}원 · 매칭 {row.pair.matched_count}</small>
            </article>
          ))}
        </section>
        <section>
          <b>append-only 연구 기록</b>
          {!records.length ? <p className="tp-empty">누적된 QSP7 연구 이벤트가 없습니다.</p> : records.slice(0, 20).map((row, index) => (
            <article key={`${row.recorded_at}-${index}`}>
              <span className={`tp-authority ${row.authority || "diagnostic"}`}>{row.authority || "diagnostic"}</span>
              <code>{row.event}</code>
              <small>{row.recorded_at}</small>
            </article>
          ))}
        </section>
      </div>
    </details>
  );
}

Object.assign(window, { BtTradePathHistory });
export { BtTradePathHistory };
