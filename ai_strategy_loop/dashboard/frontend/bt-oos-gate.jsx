/* QSP7 페이지 11 — 채택 게이트.
 * 두 모드를 지원한다.
 *   v2 분할(기본): 연속 1회 런 job 한 쌍을 날짜로 갈라 판정 — 후보당 백테스트 1회.
 *   4-job 독립(기존): 설계/OOS 를 각각 따로 돌린 job 4개.
 * 연속 런은 자본이 이어지므로 "OOS" 가 아니라 "홀드아웃"이라 부른다. */
import { _btFetchJson, _btPostJson } from "./bt-tab-utils.jsx";
const { useState: useState_oos, useEffect: useEffect_oos } = React;

function _oosJobLabel(job) {
  const spec = job.spec || {};
  return `${spec.start || "?"}~${spec.end || "?"} · ${spec.timeframe || "?"} · ${spec.buy || ""}/${spec.sell || ""} · ${job.job_id}`;
}

function _oosPickAttributed(runs) {
  // 최신 귀속 우선: 기준선/후보 × 설계/OOS 4칸을 candidate-runs 에서 채운다(P1-4).
  const latest = (role, isBaseline) => {
    const hit = runs.find(row => row.role === role && (row.candidate_id === "baseline") === isBaseline);
    return hit ? hit.job_id : "";
  };
  return {
    designBaseline: latest("design", true), designCandidate: latest("design", false),
    oosBaseline: latest("oos", true), oosCandidate: latest("oos", false),
  };
}

function _oosMoney(value) { return Number(value || 0).toLocaleString() + "원"; }
function _oosPct(value) { return Math.round((Number(value) || 0) * 100) + "%"; }

function BtOosGate({ baseUrl, jobs, baselineJobId, lane, axis = "sell", manifest }) {
  const [mode, setMode] = useState_oos("split");
  const [form, setForm] = useState_oos({ designBaseline: baselineJobId || "", designCandidate: "", oosBaseline: "", oosCandidate: "" });
  const [split, setSplit] = useState_oos({ baseline: baselineJobId || "", candidate: "" });
  const [result, setResult] = useState_oos(null);
  const [busy, setBusy] = useState_oos(false);
  const [attributed, setAttributed] = useState_oos(null);

  useEffect_oos(() => {
    if (!baseUrl || !lane) return undefined;
    let alive = true;
    _btFetchJson(`${baseUrl}/bt/trade-path/candidate-runs?lane=${encodeURIComponent(lane)}`, 15000)
      .then(payload => { if (alive) setAttributed(_oosPickAttributed(payload.runs || [])); })
      .catch(() => { if (alive) setAttributed(null); });
    return () => { alive = false; };
  }, [baseUrl, lane]);

  const row = manifest && manifest.manifest;
  const designPeriod = row ? { t_start: row.design.start, t_end: row.design.end } : null;
  const holdoutPeriod = row ? { t_start: row.oos.start, t_end: row.oos.end } : null;

  const applyAttributed = () => {
    if (attributed) setForm(current => ({ ...current, ...Object.fromEntries(Object.entries(attributed).filter(([, value]) => value)) }));
  };
  const field = (key, label) => <label>{label}<select value={form[key]} onChange={event => setForm(current => ({ ...current, [key]: event.target.value }))}><option value="">공식 job 선택</option>{(jobs || []).map(job => <option key={job.job_id} value={job.job_id}>{_oosJobLabel(job)}</option>)}</select></label>;
  const splitField = (key, label) => <label>{label}<select value={split[key]} onChange={event => setSplit(current => ({ ...current, [key]: event.target.value }))}><option value="">공식 job 선택</option>{(jobs || []).map(job => <option key={job.job_id} value={job.job_id}>{_oosJobLabel(job)}</option>)}</select></label>;

  const ready = mode === "split"
    ? Boolean(split.baseline && split.candidate && designPeriod && holdoutPeriod)
    : Object.values(form).every(Boolean);

  const run = () => {
    if (!ready) return;
    setBusy(true); setResult(null);
    const body = mode === "split"
      ? { baseline_job_id: split.baseline, candidate_job_id: split.candidate, axis,
          design_period: designPeriod, holdout_period: holdoutPeriod }
      : { design_baseline_job_id: form.designBaseline, design_candidate_job_id: form.designCandidate,
          oos_baseline_job_id: form.oosBaseline, oos_candidate_job_id: form.oosCandidate, axis };
    _btPostJson(`${baseUrl}/bt/trade-path/promotion-gate`, body, 120000)
      .then(setResult)
      .catch(reason => setResult({ verdict: "blocked", blockers: [String(reason.message || reason)] }))
      .finally(() => setBusy(false));
  };

  const second = result && (result.holdout || result.oos);
  const secondLabel = result && result.mode === "2job_split" ? "홀드아웃" : "OOS";
  const secondEdge = result && (result.holdout_per_trade_delta ?? result.oos_per_trade_delta);
  const secondRatio = result && (result.holdout_trade_ratio ?? result.oos_trade_ratio);

  return <section className="tp-subpanel tp-oos-gate" aria-labelledby="tp-oos-title">
    <header>
      <div><b id="tp-oos-title">채택 게이트</b>
        <small>가상 재생이 좋아도 채택하지 않습니다. 두 구간 공식 결과가 모두 개선돼야 합니다.</small></div>
      <span className="tp-authority official">정본</span>
    </header>

    <div className="tp-oos-modes" role="tablist" aria-label="판정 모드">
      {[["split", "v2 분할 (연속 1회 런)"], ["four", "4-job 독립 런"]].map(([key, label]) =>
        <button key={key} role="tab" aria-selected={mode === key} className={mode === key ? "active" : ""}
          onClick={() => { setMode(key); setResult(null); }}>{label}</button>)}
    </div>

    {mode === "split" ? <>
      <div className="tp-oos-rule">
        연속 1회 런을 <b>{designPeriod ? `${designPeriod.t_start}~${designPeriod.t_end}` : "?"}</b>(설계)과
        <b> {holdoutPeriod ? `${holdoutPeriod.t_start}~${holdoutPeriod.t_end}` : "?"}</b>(홀드아웃)으로 나눠 판정합니다.
        ⚠ 자본이 이어지므로 홀드아웃은 독립 OOS 가 아닙니다 — 건당 손익으로 판단하세요.
      </div>
      <div className="tp-oos-form">
        <fieldset><legend>기준선 런</legend>{splitField("baseline", "기준")}</fieldset>
        <fieldset><legend>후보 런</legend>{splitField("candidate", "후보")}</fieldset>
      </div>
    </> : <>
      <div className="tp-oos-rule">설계 공식 pair와 <b>비중첩</b> OOS 공식 pair가 모두 개선돼야 합니다.</div>
      {attributed && Object.values(attributed).some(Boolean) &&
        <button className="btn ghost sm" onClick={applyAttributed}>귀속된 후보 실행 job 자동 채움</button>}
      <div className="tp-oos-form">
        <fieldset><legend>① 설계 구간</legend>{field("designBaseline", "기준")}{field("designCandidate", "후보")}</fieldset>
        <fieldset><legend>② OOS 구간</legend>{field("oosBaseline", "기준")}{field("oosCandidate", "후보")}</fieldset>
      </div>
    </>}

    <button className="btn primary sm" disabled={busy || !ready} onClick={run}>
      {busy ? "공식 결과 확인 중…" : "채택 판정"}
    </button>

    {result && <div className={`tp-oos-verdict ${result.verdict === "adoptable" ? "ready" : "blocked"}`}>
      <b>{result.verdict === "adoptable" ? "채택 가능 (사람 승인 대기)" : "채택 불가"}</b>
      <span>설계 {_oosMoney(result.design?.pair?.delta_profit_krw)} · {secondLabel} {_oosMoney(second?.pair?.delta_profit_krw)}</span>
      {axis === "buy" && <span className="mono">
        건당 엣지 설계 {_oosMoney(result.design_per_trade_delta)} · {secondLabel} {_oosMoney(secondEdge)} ·
        거래 유지 {_oosPct(result.design_trade_ratio)}/{_oosPct(secondRatio)} (하한 {_oosPct(result.min_trade_ratio || 0.4)})
      </span>}
      {result.mode === "2job_split" && <span className={`mono ${result.split_reconciled ? "" : "neg"}`}>
        검산 {result.split_reconciled ? "통과" : "실패"} — 두 구간 합 {Number(result.split_trade_counts?.parts || 0).toLocaleString()} /
        전체 {Number(result.split_trade_counts?.whole || 0).toLocaleString()}건
      </span>}
      <small>{(result.blockers || []).join(" · ") || result.rule}</small>
      {result.caveat && <small>{result.caveat}</small>}
    </div>}
  </section>;
}

Object.assign(window, { BtOosGate });
export { BtOosGate };
