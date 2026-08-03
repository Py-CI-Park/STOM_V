/* QSP7 candidate execution console (P1): register → design run → OOS run in 3 clicks.
 * Periods/session/baseline come ONLY from the lane manifest — no manual period input. */
import { _btFetchJson, _btPostJson } from "./bt-tab-utils.jsx";
const { useState: useState_cc, useEffect: useEffect_cc, useRef: useRef_cc } = React;

function _ccHash6(text) {
  let hash = 5381;
  for (let index = 0; index < text.length; index += 1) hash = ((hash << 5) + hash + text.charCodeAt(index)) >>> 0;
  return hash.toString(16).slice(0, 6).padStart(6, "0");
}
function _ccToday() {
  const now = new Date();
  return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
}
function _ccFamilySlug(family) {
  return String(family || "후보").replace(/\s+/g, "");
}

function BtCandidateConsole({ baseUrl, lane, manifest, proposal, axis = "sell" }) {
  const [regState, setRegState] = useState_cc({ phase: "idle", name: "", message: "" });
  const [jobs, setJobs] = useState_cc({ design: null, oos: null });
  const [error, setError] = useState_cc("");
  const timerRef = useRef_cc(null);

  useEffect_cc(() => {
    // 후보가 바뀌면 콘솔 상태를 초기화한다 — 다른 후보의 job 이 귀속되는 실수 방지.
    setRegState({ phase: "idle", name: "", message: "" });
    setJobs({ design: null, oos: null });
    setError("");
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [proposal && proposal.proposal_id, lane]);

  if (!manifest) return <div className="tp-empty">레인 manifest 를 불러온 뒤 사용할 수 있습니다.</div>;
  if (!proposal) return <div className="tp-empty">조건식 후보 단계에서 후보를 먼저 선택하세요.</div>;

  const laneManifest = manifest.manifest || {};
  const design = laneManifest.design || {};
  const oos = laneManifest.oos || {};
  const candidateName = regState.name
    || `QSP7_${lane}_${_ccFamilySlug(proposal.family)}_${_ccToday()}_${_ccHash6(proposal.stom_code || "")}`;

  const register = () => {
    setError("");
    setRegState(current => ({ ...current, phase: "busy" }));
    _btPostJson(`${baseUrl}/bt/strategy`, {
      kind: axis, name: candidateName, code: proposal.stom_code, overwrite: false,
    }, 20000).then(payload => {
      if (payload && (payload.status === "ok" || payload.saved || payload.available)) {
        setRegState({ phase: "done", name: candidateName, message: "연구용 전략으로 등록됨 · 자동 채택 아님" });
      } else {
        setRegState({ phase: "error", name: candidateName, message: (payload && payload.message) || "등록 실패" });
      }
    }).catch(reason => setRegState({ phase: "error", name: candidateName, message: String(reason.message || reason) }));
  };

  const poll = (role, jobId) => {
    _btFetchJson(`${baseUrl}/bt/job?job_id=${encodeURIComponent(jobId)}`, 15000).then(payload => {
      const record = { id: jobId, status: payload.status || "unknown", progress: payload.progress || 0 };
      setJobs(current => ({ ...current, [role]: record }));
      if (!["success", "error", "cancelled"].includes(record.status)) {
        timerRef.current = setTimeout(() => poll(role, jobId), 1500);
      }
    }).catch(reason => setError(String(reason.message || reason)));
  };

  const run = (role, strategyName, candidateId) => {
    const period = role === "design" ? design : oos;
    // 한 라운드 한 축: 바꾼 축만 후보 전략, 반대 축은 manifest 기준선 고정.
    const buyName = axis === "buy" ? strategyName : laneManifest.baseline_buy;
    const sellName = axis === "buy" ? laneManifest.baseline_sell : strategyName;
    setError("");
    _btPostJson(`${baseUrl}/bt/run`, {
      buy: buyName, sell: sellName,
      start: period.start, end: period.end,
      start_time: laneManifest.session_start, end_time: laneManifest.session_end,
      timeframe: laneManifest.timeframe, mode: "backtest",
    }, 30000).then(payload => {
      const jobId = payload && payload.job_id;
      if (!jobId) { setError((payload && payload.message) || "공식 실행 시작 실패"); return; }
      setJobs(current => ({ ...current, [role]: { id: jobId, status: "queued", progress: 0 } }));
      _btPostJson(`${baseUrl}/bt/trade-path/candidate-runs`, {
        candidate_id: candidateId, lane, role, axis, job_id: jobId,
        sell_name: sellName, buy_name: buyName, family: proposal.family || "",
      }, 15000).catch(reason => setError(`귀속 기록 실패: ${String(reason.message || reason)}`));
      poll(role, jobId);
    }).catch(reason => setError(String(reason.message || reason)));
  };

  const designDone = jobs.design && jobs.design.status === "success";
  const jobBadge = record => record
    ? <span className={`tp-cc-job ${record.status}`}>{record.id} · {record.status} · {Math.round((record.progress || 0) * 100)}%</span>
    : <span className="tp-cc-job idle">미실행</span>;

  return <section className="tp-subpanel tp-candidate-console" aria-labelledby="tp-cc-title">
    <header><div><b id="tp-cc-title">후보 실행 콘솔 · {lane} · 축={axis === "buy" ? "매수" : "매도"}</b><small>기간·세션·기준선은 manifest 자동 주입 — 수기 입력 없음 · 반대 축은 기준선 고정</small></div><span className="tp-authority official">정본</span></header>
    <div className="tp-cc-manifest mono">
      설계 {design.start}~{design.end} · OOS {oos.start}~{oos.end} · 세션 {String(laneManifest.session_start).padStart(6, "0")}~{String(laneManifest.session_end).padStart(6, "0")} · 기준선 {laneManifest.baseline_buy}/{laneManifest.baseline_sell}
      {laneManifest.decision_status && laneManifest.decision_status.includes("대기") && <em className="tp-cc-pending"> · {laneManifest.decision_status}</em>}
    </div>
    <ol className="tp-cc-steps">
      <li className={regState.phase === "done" ? "done" : ""}>
        <div><b>① 전략 등록</b><code>{candidateName}</code><small>{regState.message || "연구용 등록이며 운영·실거래 반영이 아닙니다."}</small></div>
        <button className="btn primary sm" onClick={register} disabled={regState.phase === "busy" || regState.phase === "done"}>
          {regState.phase === "busy" ? "등록 중…" : regState.phase === "done" ? "등록 완료" : "전략으로 등록"}
        </button>
      </li>
      <li className={designDone ? "done" : ""}>
        <div><b>② 설계 실행</b>{jobBadge(jobs.design)}<small>{axis === "buy" ? "기준선 매도식 고정 · 후보 매수식만 교체" : "기준선 매수식 고정 · 후보 매도식만 교체"}(한 라운드 한 축)</small></div>
        <button className="btn primary sm" onClick={() => run("design", regState.name || candidateName, proposal.proposal_id)} disabled={regState.phase !== "done" || (jobs.design && !["error", "cancelled"].includes(jobs.design.status))}>설계 실행</button>
      </li>
      <li>
        <div><b>③ OOS 실행</b>{jobBadge(jobs.oos)}<small>설계 성공 후에만 활성 · 설정 잠금 후 비중첩 기간 실행</small></div>
        <button className="btn primary sm" onClick={() => run("oos", regState.name || candidateName, proposal.proposal_id)} disabled={!designDone || (jobs.oos && !["error", "cancelled"].includes(jobs.oos.status))}>OOS 실행</button>
      </li>
    </ol>
    <div className="tp-cc-baseline">
      <small>기준선 pair 가 없으면 함께 실행하세요 (같은 기간·기준선 전략):</small>
      <button className="btn ghost sm" onClick={() => run("design", axis === "buy" ? laneManifest.baseline_buy : laneManifest.baseline_sell, "baseline")}>기준선 설계 실행</button>
      <button className="btn ghost sm" onClick={() => run("oos", axis === "buy" ? laneManifest.baseline_buy : laneManifest.baseline_sell, "baseline")}>기준선 OOS 실행</button>
    </div>
    {error && <p className="tp-error" role="alert">{error}</p>}
  </section>;
}

Object.assign(window, { BtCandidateConsole });
export { BtCandidateConsole };
