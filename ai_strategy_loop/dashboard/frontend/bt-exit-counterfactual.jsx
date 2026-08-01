/* Restricted fixed-entry exit replay controls. Future labels are not accepted by the API. */
const { useState: useState_tpcf } = React;

function BtExitCounterfactual({ baseUrl, analysisId, onResult }) {
  const [after, setAfter] = useState_tpcf(90);
  const [target, setTarget] = useState_tpcf(1.5);
  const [busy, setBusy] = useState_tpcf(false);
  const [error, setError] = useState_tpcf("");
  const run = () => {
    if (!analysisId || busy) return;
    setBusy(true); setError("");
    fetch(baseUrl + "/bt/trade-path/counterfactual", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ analysis_id: analysisId, policy: {
        name: `회복 익절 ${target}%`, rules: [
          { rule_id: "recovery_take_profit", after_seconds: Number(after),
            clauses: [{ field: "net_return_pct", operator: ">=", value: Number(target) }] },
          { rule_id: "forced_liquidation", after_seconds: 0,
            clauses: [{ field: "hold_seconds", operator: ">=", value: 86400 }] },
        ],
      }}),
    }).then(response => response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)))
      .then(payload => { if (!payload.available) throw new Error(payload.reason || "가상 재생 실패"); onResult(payload); })
      .catch(reason => setError(String(reason && reason.message ? reason.message : reason)))
      .finally(() => setBusy(false));
  };
  return (
    <section className="tp-subpanel" aria-labelledby="tp-cf-title">
      <header><div><b id="tp-cf-title">고정 진입 가상 매도</b><small>ADVISORY · 이후 재진입/자본 재배분은 바꾸지 않습니다</small></div><span className="tp-authority advisory">자문</span></header>
      <div className="tp-form-row">
        <label>최소 보유(초)<input type="number" min="0" max="3600" value={after} onChange={event => setAfter(event.target.value)} /></label>
        <label>비용 후 수익률(%)<input type="number" min="-10" max="30" step="0.1" value={target} onChange={event => setTarget(event.target.value)} /></label>
        <button className="btn primary sm" disabled={!analysisId || busy} onClick={run}>{busy ? "재생 중…" : "전체 거래 재생"}</button>
      </div>
      {error && <p className="tp-error" role="alert">{error}</p>}
    </section>
  );
}

Object.assign(window, { BtExitCounterfactual });
export { BtExitCounterfactual };
