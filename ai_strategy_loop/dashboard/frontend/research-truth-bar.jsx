import { useCallback_bt, useEffect_bt, useState_bt, _btFetchJson } from "./bt-tab-utils.jsx";
import { truthPresentation } from "./research-truth-model.mjs";

const REASON_LABEL = {
  source_not_selected: "완료된 job을 선택하면 실행 진실을 표시합니다.",
  evolution_not_supported: "진화 세대 Truth 연결은 ANA-01 이후 제공됩니다.",
  demo_mode: "데모 값은 실제 Evidence가 아니므로 Truth를 만들지 않습니다.",
  job_not_found: "선택한 job의 원본 기록을 찾을 수 없습니다.",
  job_not_terminal: "실행이 끝난 뒤 최종 Truth를 표시합니다.",
  source_identity_missing: "source hash가 없어 Truth를 생성하지 않았습니다.",
  legacy_job_invalid: "과거 job 형식이 계약과 맞지 않아 해석을 중지했습니다.",
};

function _TruthUnavailable({ reason, loading, onReload }) {
  const message = REASON_LABEL[reason] || "Truth를 안전하게 해석할 수 없습니다.";
  return (
    <section className="research-truth-bar unavailable" aria-label="연구 진실 바" aria-live="polite">
      <div className="research-truth-kicker">RESEARCH TRUTH · READ ONLY</div>
      <div className="research-truth-empty">
        <div>
          <strong>{loading ? "Truth 갱신 중" : "현재 Truth 없음"}</strong>
          <span>{message}</span>
        </div>
        {onReload && (
          <button className="btn ghost sm" onClick={onReload} disabled={loading}>
            {loading ? "갱신 중…" : "다시 조회"}
          </button>
        )}
      </div>
    </section>
  );
}

function _TruthAxis({ label, item }) {
  return (
    <div className="research-truth-axis">
      <dt>{label}</dt>
      <dd>
        <strong>{item.label}</strong>
        <code>{item.code}</code>
      </dd>
      {item.detail && <small>{item.detail}</small>}
    </div>
  );
}

function ResearchTruthBar({ baseUrl, isDemo, jobId, evoSource }) {
  const [payload, setPayload] = useState_bt(null);
  const [loading, setLoading] = useState_bt(false);
  const [error, setError] = useState_bt("");
  const [observedAt, setObservedAt] = useState_bt("");

  const load = useCallback_bt(() => {
    if (isDemo || !baseUrl || !jobId) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    _btFetchJson(
      baseUrl + "/research-truth/job?job_id=" + encodeURIComponent(jobId),
      5000,
      controller.signal,
    )
      .then(next => {
        setPayload(next || null);
        setObservedAt(new Date().toLocaleTimeString());
      })
      .catch(nextError => {
        if (!controller.signal.aborted) setError(String(nextError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [baseUrl, isDemo, jobId]);

  useEffect_bt(() => load(), [load]);

  if (isDemo) return <_TruthUnavailable reason="demo_mode" loading={false} />;
  if (!jobId && evoSource) {
    return <_TruthUnavailable reason="evolution_not_supported" loading={false} />;
  }
  if (!jobId) return <_TruthUnavailable reason="source_not_selected" loading={false} />;
  if (error && !(payload && payload.job_id === jobId)) {
    return <_TruthUnavailable reason="request_failed" loading={loading} onReload={load} />;
  }
  if (!(payload && payload.job_id === jobId && payload.truth_available && payload.truth)) {
    return (
      <_TruthUnavailable
        reason={(payload && payload.job_id === jobId && payload.reason) || "job_not_terminal"}
        loading={loading}
        onReload={load}
      />
    );
  }

  const view = truthPresentation(payload.truth);
  return (
    <section
      className={"research-truth-bar tone-" + view.execution.tone}
      aria-label="연구 진실 바"
      aria-live="polite"
      data-execution={view.execution.code}
    >
      <header className="research-truth-head">
        <div>
          <div className="research-truth-kicker">RESEARCH TRUTH · READ ONLY</div>
          <h3>{view.candidate}</h3>
          <p>
            job {jobId} · 화면 조회 {observedAt || "미확인"} · persistence {payload.persistence || "unknown"}
          </p>
        </div>
        <button className="btn ghost sm" onClick={load} disabled={loading}>
          {loading ? "갱신 중…" : "Truth 새로고침"}
        </button>
      </header>

      <dl className="research-truth-axes">
        <_TruthAxis label="실행" item={view.execution} />
        <_TruthAxis label="경제" item={view.economic} />
        <_TruthAxis label="권위" item={view.authority} />
        <_TruthAxis label="다음 허용 행동" item={view.action} />
      </dl>

      <div className="research-truth-decision">
        <div>
          <span>차단 사유</span>
          <strong>{view.blocker}</strong>
        </div>
        <div className="research-truth-evidence mono">
          identity {view.identityStatus} · input {view.evidenceHash} · 원시 상태 {view.rawStatus}
        </div>
      </div>

      {(view.corrected || view.failureCause !== "NONE") && (
        <div className="research-truth-correction" role="status">
          <b>{view.corrected ? "원시 상태 정정" : "실패 원인"}</b>
          <code>{view.failureCause}</code>
          {view.correctionReason && <span>{view.correctionReason}</span>}
        </div>
      )}
    </section>
  );
}

Object.assign(window, { ResearchTruthBar });
export { ResearchTruthBar };
