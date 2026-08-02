/* QSP7 official design + non-overlapping OOS adoption gate. */
import { _btPostJson } from "./bt-tab-utils.jsx";
const { useState: useState_oos } = React;

function _oosJobLabel(job) {
  const spec = job.spec || {};
  return `${spec.start || "?"}~${spec.end || "?"} · ${spec.timeframe || "?"} · ${spec.buy || ""}/${spec.sell || ""} · ${job.job_id}`;
}

function BtOosGate({ baseUrl, jobs, baselineJobId }) {
  const [form, setForm] = useState_oos({ designBaseline: baselineJobId || "", designCandidate: "", oosBaseline: "", oosCandidate: "" });
  const [result, setResult] = useState_oos(null);
  const [busy, setBusy] = useState_oos(false);
  const field = (key, label) => <label>{label}<select value={form[key]} onChange={event => setForm(current => ({ ...current, [key]: event.target.value }))}><option value="">공식 job 선택</option>{(jobs || []).map(job => <option key={job.job_id} value={job.job_id}>{_oosJobLabel(job)}</option>)}</select></label>;
  const run = () => {
    if (Object.values(form).some(value => !value)) return;
    setBusy(true); setResult(null);
    _btPostJson(`${baseUrl}/bt/trade-path/promotion-gate`, {
      design_baseline_job_id: form.designBaseline, design_candidate_job_id: form.designCandidate,
      oos_baseline_job_id: form.oosBaseline, oos_candidate_job_id: form.oosCandidate,
    }, 60000).then(setResult).catch(reason => setResult({ verdict: "blocked", blockers: [String(reason.message || reason)] })).finally(() => setBusy(false));
  };
  const designDelta = result?.design?.pair?.delta_profit_krw;
  const oosDelta = result?.oos?.pair?.delta_profit_krw;
  return <section className="tp-subpanel tp-oos-gate" aria-labelledby="tp-oos-title">
    <header><div><b id="tp-oos-title">설계 + 비중첩 OOS 채택 게이트</b><small>같은 매수식·timeframe의 기준/후보 공식 job 2쌍을 비교합니다.</small></div><span className="tp-authority official">정본</span></header>
    <div className="tp-oos-rule">가상 재생이 좋아도 채택하지 않습니다. 설계 공식 pair와 별도 기간 OOS 공식 pair가 모두 개선돼야 합니다.</div>
    <div className="tp-oos-form"><fieldset><legend>① 설계 구간</legend>{field("designBaseline", "기준")}{field("designCandidate", "후보")}</fieldset><fieldset><legend>② OOS 구간</legend>{field("oosBaseline", "기준")}{field("oosCandidate", "후보")}</fieldset></div>
    <button className="btn primary sm" disabled={busy || Object.values(form).some(value => !value)} onClick={run}>{busy ? "공식 결과 확인 중…" : "설계/OOS 채택 판정"}</button>
    {result && <div className={`tp-oos-verdict ${result.verdict === "adoptable" ? "ready" : "blocked"}`}><b>{result.verdict === "adoptable" ? "채택 가능" : "채택 불가"}</b><span>설계 {Number(designDelta || 0).toLocaleString()}원 · OOS {Number(oosDelta || 0).toLocaleString()}원</span><small>{(result.blockers || []).join(" · ") || result.rule}</small></div>}
  </section>;
}

Object.assign(window, { BtOosGate });
export { BtOosGate };
