import { useCallback_bt, useEffect_bt, useState_bt, _btFetchJson } from "./bt-tab-utils.jsx";
import { bundleOverview } from "./analysis-bundle-overview-model.mjs";

const SECTION_LABELS = {
  metrics: "핵심 지표",
  series: "시계열",
  distribution: "분포",
  episodes: "에피소드",
  attribution: "기여 분석",
  counterfactual: "반사실",
  robustness: "강건성",
};

const REASON_LABELS = {
  bundle_not_loaded: "선택한 job의 분석 번들을 아직 불러오지 못했습니다.",
  demo_mode: "데모 화면에는 실제 분석 Evidence가 없습니다.",
  job_not_found: "선택한 job 기록을 찾을 수 없습니다.",
  job_not_terminal: "실행 종료 뒤 분석 번들을 만들 수 있습니다.",
  request_failed: "분석 번들 조회에 실패했습니다. 연결 상태를 확인한 뒤 다시 시도하세요.",
  source_identity_missing: "source hash가 없어 번들 생성을 차단했습니다.",
  trade_csv_missing: "거래 CSV가 없어 이 분석을 실행하지 않았습니다.",
  counterfactual_not_run: "반사실 분석을 실행하지 않았습니다.",
  fold_control_fdr_posterior_not_run: "fold·control·FDR·posterior를 실행하지 않았습니다.",
  preregistered_episode_cohort_missing: "사전 정의된 cohort가 없어 에피소드를 만들지 않았습니다.",
};

function _reason(value) {
  const key = String(value || "");
  if (REASON_LABELS[key]) return REASON_LABELS[key];
  if (key.startsWith("execution_")) return "실행이 완료되지 않아 경제 분석을 하지 않았습니다.";
  return key || "근거가 없어 이 기능을 사용할 수 없습니다.";
}

function _BundleAxis({ label, item }) {
  return (
    <div className="analysis-overview-axis">
      <dt>{label}</dt>
      <dd><strong>{item.label}</strong><code>{item.code}</code></dd>
    </div>
  );
}

function _Capability({ label, item }) {
  return (
    <div className={"analysis-capability status-" + item.code.toLowerCase()}>
      <div><b>{label}</b><code>{item.code}</code></div>
      <strong>{item.label}</strong>
      {item.reason && <small>{_reason(item.reason)}</small>}
    </div>
  );
}

function _Unavailable({ loading, reason, onReload }) {
  return (
    <section className="analysis-bundle-overview unavailable" aria-label="분석 번들 개요" aria-live="polite">
      <div>
        <span className="analysis-overview-kicker">ANALYSIS BUNDLE V2 · READ ONLY</span>
        <h3>{loading ? "분석 번들 조회 중" : "분석 번들 사용 불가"}</h3>
        <p>{_reason(reason)}</p>
      </div>
      {onReload && (
        <button className="btn ghost sm" onClick={onReload} disabled={loading}>
          {loading ? "조회 중…" : "다시 조회"}
        </button>
      )}
    </section>
  );
}

function AnalysisBundleOverview({ baseUrl, isDemo, jobId }) {
  const [payload, setPayload] = useState_bt(null);
  const [loading, setLoading] = useState_bt(false);
  const [error, setError] = useState_bt("");

  const load = useCallback_bt(() => {
    if (isDemo || !baseUrl || !jobId) return undefined;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    _btFetchJson(
      baseUrl + "/analysis-bundle/job?job_id=" + encodeURIComponent(jobId),
      12000,
      controller.signal,
    )
      .then(next => setPayload(next || null))
      .catch(nextError => {
        if (!controller.signal.aborted) setError(String(nextError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [baseUrl, isDemo, jobId]);

  useEffect_bt(() => load(), [load]);

  if (isDemo) return <_Unavailable loading={false} reason="demo_mode" />;
  if (!(payload && payload.job_id === jobId && payload.bundle_available && payload.bundle)) {
    return (
      <_Unavailable
        loading={loading}
        reason={error ? "request_failed" : (payload && payload.reason) || "bundle_not_loaded"}
        onReload={load}
      />
    );
  }

  const bundle = payload.bundle;
  const view = bundleOverview(payload);
  const capabilities = Object.keys(SECTION_LABELS);
  return (
    <section className="analysis-bundle-overview" aria-label="분석 번들 개요" aria-live="polite">
      <header className="analysis-overview-head">
        <div>
          <span className="analysis-overview-kicker">ANALYSIS BUNDLE V2 · READ ONLY</span>
          <h3>{view.candidate}</h3>
          <p className="mono">
            bundle {view.bundleHash} · identity {view.identityStatus} · persistence {view.persistence}
          </p>
        </div>
        <button className="btn ghost sm" onClick={load} disabled={loading}>
          {loading ? "조회 중…" : "Bundle 새로고침"}
        </button>
      </header>

      <dl className="analysis-overview-axes">
        <_BundleAxis label="실행" item={view.execution} />
        <_BundleAxis label="경제" item={view.economic} />
        <_BundleAxis label="권위" item={view.authority} />
        <_BundleAxis label="다음 행동" item={view.action} />
      </dl>

      <div className="analysis-completeness mono" role="status">
        <b>실행 완전성</b>
        <span>raw {view.rawStatus}</span>
        <span>rc {view.returnCode}</span>
        <span>events {view.eventCount}</span>
        <span>rows/trades {view.rowCount}/{view.tradeCount}</span>
        <span>checkpoint {view.checkpoint}</span>
        <span>cause {view.failureCause}</span>
      </div>

      <div className="analysis-capability-wrap" aria-label="분석 기능 가용성">
        <div className="analysis-capability-title">
          <b>분석 기능 가용성</b>
          <span>관측되지 않은 기능은 0이 아니라 미실행·평가 불가로 표시합니다.</span>
        </div>
        <div className="analysis-capability-grid">
          {capabilities.map(key => <_Capability key={key} label={SECTION_LABELS[key]} item={view[key]} />)}
        </div>
      </div>

      <footer className="analysis-overview-evidence mono">
        <span>evidence {view.evidenceId}</span>
        <span>CSV {view.csvHash}{view.csvSize == null ? "" : " · " + view.csvSize + " bytes"}</span>
        <span>spec {view.specHash}</span>
        <span>prereg {view.preregistration}</span>
        <span>generated {view.generatedAtSource}</span>
        <span>content {bundle.content_sha256}</span>
      </footer>
    </section>
  );
}

Object.assign(window, { AnalysisBundleOverview });
export { AnalysisBundleOverview };
