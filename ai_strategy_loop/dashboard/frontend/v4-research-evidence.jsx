/* v4-research-evidence.jsx — v5.16 failure atlas and bounded evidence inspector. */
const { useEffect: useEffect_re16, useState: useState_re16 } = React;

const RE16_STATES = ["PROVEN", "REFUTED", "FIXED", "OPEN", "LIMITATION"];

function V516FailureEvidence({ baseUrl }) {
  const [failures, setFailures] = useState_re16({ status: "loading", rows: [], error: "" });
  const [evidence, setEvidence] = useState_re16({ status: "idle", id: "", data: null, error: "" });
  const root = String(baseUrl || "").replace(/\/$/, "");
  useEffect_re16(() => {
    const controller = new AbortController();
    fetch(root + "/research-program/failures", { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(payload => setFailures({ status: "ready", rows: payload.failures || [], error: "" }))
      .catch(error => { if (error.name !== "AbortError") setFailures({ status: "error", rows: [], error: String(error.message || error) }); });
    return () => controller.abort();
  }, [root]);
  const inspect = evidenceId => {
    if (!evidenceId) return;
    setEvidence({ status: "loading", id: evidenceId, data: null, error: "" });
    fetch(root + "/research-program/evidence/" + encodeURIComponent(evidenceId))
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(payload => setEvidence({ status: "ready", id: evidenceId, data: payload, error: "" }))
      .catch(error => setEvidence({ status: "error", id: evidenceId, data: null, error: String(error.message || error) }));
  };
  return (
    <section className="re16-panel" aria-labelledby="re16-title">
      <div className="re16-heading"><div><span>CAUSE · EVIDENCE · AUTHORITY</span><h2 id="re16-title">Failure Atlas · Evidence Inspector</h2></div><div className="re16-legend" aria-label="실패원인 상태 범례">{RE16_STATES.map(state => <span key={state} className={state.toLowerCase()}>{state}</span>)}</div></div>
      {failures.status === "loading" && <p aria-live="polite">실패 원인 원장을 불러오는 중입니다.</p>}
      {failures.status === "error" && <p role="alert">Failure Atlas 요청 실패 · {failures.error}</p>}
      <div className="re16-grid" role="list" aria-label="실패 원인 원장">
        {failures.rows.map(item => <article key={item.failure_id} role="listitem" className={`re16-failure ${String(item.state).toLowerCase()}`}><header><b>{item.failure_id}</b><strong>{item.state}</strong></header><h3>{item.title}</h3><div>{(item.evidence || []).map(id => <button type="button" key={id} onClick={() => inspect(id)} aria-pressed={evidence.id === id}>{id}</button>)}</div></article>)}
      </div>
      <section className="re16-inspector" aria-labelledby="re16-inspector-title">
        <h3 id="re16-inspector-title">Evidence Inspector</h3>
        {evidence.status === "idle" && <p>Failure Atlas의 Evidence ID를 선택하십시오.</p>}
        {evidence.status === "loading" && <p aria-live="polite">{evidence.id} 검증 메타데이터를 불러오는 중입니다.</p>}
        {evidence.status === "error" && <p role="alert">Evidence 요청 실패 · {evidence.error}</p>}
        {evidence.status === "ready" && evidence.data && <div className="re16-evidence"><dl><div><dt>ID</dt><dd>{evidence.id}</dd></div><div><dt>상태</dt><dd>{evidence.data.available ? "AVAILABLE" : String(evidence.data.reason || "UNAVAILABLE")}</dd></div><div><dt>SHA-256</dt><dd className="mono">{evidence.data.sha256 || "—"}</dd></div><div><dt>경로</dt><dd>{evidence.data.source && evidence.data.source.path || "—"}</dd></div><div><dt>권위</dt><dd>{evidence.data.authority}</dd></div></dl><details><summary>검증된 Evidence 요약 보기</summary><pre tabIndex={0}>{JSON.stringify(evidence.data.data, null, 2).slice(0, 12000)}</pre></details></div>}
      </section>
      <p className="re16-note">Evidence는 read-only allowlist로 조회하며 누락과 손상을 구분합니다. 원본 결과가 플랫폼 PASS여도 경제적 성공 권한은 부여하지 않습니다.</p>
    </section>
  );
}

Object.assign(window, { V516FailureEvidence });
export { V516FailureEvidence };
