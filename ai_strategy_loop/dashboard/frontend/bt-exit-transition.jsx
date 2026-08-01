/* Official baseline/candidate job comparison; no unrun pair is inferred. */
const { useState: useState_tpxt } = React;

function BtExitTransition({ baseUrl, jobs, baselineJobId }) {
  const [candidate, setCandidate] = useState_tpxt("");
  const [result, setResult] = useState_tpxt(null);
  const [busy, setBusy] = useState_tpxt(false);
  const compare = () => {
    if (!baselineJobId || !candidate) return;
    setBusy(true);
    fetch(baseUrl + "/bt/trade-path/official-pair", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ baseline_job_id: baselineJobId, candidate_job_id: candidate }) })
      .then(response => response.json()).then(setResult).catch(() => setResult({ available: false, reason: "비교 실패" }))
      .finally(() => setBusy(false));
  };
  const pair = result && result.pair;
  return <section className="tp-subpanel" aria-labelledby="tp-pair-title">
    <header><div><b id="tp-pair-title">공식 pair 재백테스트 비교</b><small>두 job 모두 공식 엔진 결과일 때만 정본</small></div><span className="tp-authority official">정본</span></header>
    <div className="tp-form-row"><label>후보 job<select value={candidate} onChange={event => setCandidate(event.target.value)}><option value="">선택</option>{(jobs || []).filter(job => job.job_id !== baselineJobId).map(job => <option key={job.job_id} value={job.job_id}>{job.spec?.buy || ""} · {job.spec?.sell || ""} · {job.job_id}</option>)}</select></label><button className="btn primary sm" onClick={compare} disabled={!candidate || busy}>{busy ? "비교 중…" : "정본 비교"}</button></div>
    {result && !result.available && <p className="tp-error">{result.reason}</p>}
    {pair && <div className="tp-pair-result"><strong className={pair.delta_profit_krw >= 0 ? "pos" : "neg"}>{Number(pair.delta_profit_krw).toLocaleString()}원</strong><span>매칭 {pair.matched_count} · 기준만 {pair.baseline_only_count} · 후보만 {pair.candidate_only_count}</span><div className="tp-transition-list">{(pair.transitions || []).map(row => <span key={`${row.baseline_reason}-${row.candidate_reason}`}>{row.baseline_reason} → {row.candidate_reason} <b>{row.count}</b></span>)}</div></div>}
  </section>;
}

Object.assign(window, { BtExitTransition });
export { BtExitTransition };
