/* QSP7 research ledger browser (P4): sidecar entities, idempotency status, rebuild hash. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_lb, useEffect: useEffect_lb } = React;

const _LB_ENTITIES = [["analyses", "분석"], ["artifacts", "artifact"], ["candidate-runs", "후보 귀속"], ["events", "이벤트"]];

function BtLedgerBrowser({ baseUrl, lane }) {
  const [entity, setEntity] = useState_lb("analyses");
  const [payload, setPayload] = useState_lb(null);
  const [error, setError] = useState_lb("");
  useEffect_lb(() => {
    if (!baseUrl) return undefined;
    let alive = true;
    setPayload(null); setError("");
    _btFetchJson(`${baseUrl}/bt/trade-path/ledger?entity=${entity}&lane=${encodeURIComponent(lane || "")}&limit=50`, 30000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, entity, lane]);

  if (error) return <p className="tp-error">원장 조회 실패: {error}</p>;
  return <section className="tp-subpanel tp-ledger-browser" aria-labelledby="tp-lb-title">
    <header><div><b id="tp-lb-title">연구 원장 브라우저</b><small>sidecar SQLite · 멱등 ingest · 서버 재시작 후에도 보존</small></div><span className="tp-authority diagnostic">진단</span></header>
    <div className="tp-ri-controls" role="tablist" aria-label="원장 엔티티">
      {_LB_ENTITIES.map(([key, text]) => <button key={key} role="tab" aria-selected={entity === key} className={entity === key ? "active" : ""} onClick={() => setEntity(key)}>{text}</button>)}
    </div>
    {!payload ? <div className="tp-empty">원장을 불러오는 중…</div> : <>
      <div className="tp-ri-kpis mono">artifact {payload.counts?.artifacts ?? 0} · 분석 {payload.counts?.analyses ?? 0} · rebuild SHA <code title={payload.rebuild_sha256}>{String(payload.rebuild_sha256 || "").slice(0, 12)}</code></div>
      <div className="tp-lb-rows">
        {(payload.rows || []).length === 0 && <div className="tp-empty">기록이 없습니다.</div>}
        {(payload.rows || []).map((row, index) => <article key={index} className="tp-lb-row">
          <pre>{JSON.stringify(row, null, 1)}</pre>
        </article>)}
      </div>
    </>}
  </section>;
}

Object.assign(window, { BtLedgerBrowser });
export { BtLedgerBrowser };
