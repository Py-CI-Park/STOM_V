/* v4-hypothesis-registry.jsx — ANA-08 가설→사전등록→큐 원장 패널 (P10·P11·P12).
 *
 *   /hypothesis-registry/state 를 읽어 finding 원장·가설 상태·사전등록·큐를 보여준다.
 *   쓰기(검토/사전등록 초안/봉인/큐)는 API 가 상태머신 게이트를 강제한다 —
 *   이 패널은 사람 승인 증거 없는 봉인을 절대 요청하지 않는다.
 */
const { useState: useState_hr, useEffect: useEffect_hr, useCallback: useCallback_hr } = React;

const _HR_STATUS = {
  HYPOTHESIS_DRAFT: { cls: "pending", ko: "가설 초안" },
  REJECTED: { cls: "blocked", ko: "기각" },
  NEEDS_DATA: { cls: "pending", ko: "자료 부족" },
  ACCEPTED_FOR_PREREG: { cls: "signal", ko: "사전등록 후보" },
  PREREG_DRAFT: { cls: "signal", ko: "사전등록 초안" },
  PREREG_SEALED: { cls: "valid", ko: "봉인됨" },
};

function _hrShort(hash) {
  return hash ? String(hash).slice(0, 12) + "…" : "—";
}

function _hrPost(baseUrl, path, body) {
  return fetch(String(baseUrl || "").replace(/\/$/, "") + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  }).then(r => r.json().then(j => (r.ok ? j : Promise.reject(new Error(`${j.code || "HTTP " + r.status}`)))));
}

function _HrActions({ baseUrl, hyp, onChanged }) {
  const [reviewer, setReviewer] = useState_hr("");
  const [note, setNote] = useState_hr("");
  const [approval, setApproval] = useState_hr({ evidence: "", approver: "" });
  const [msg, setMsg] = useState_hr("");
  const act = (label, fn) => () => {
    setMsg("");
    fn().then(() => { setMsg(label + " 완료"); onChanged(); })
      .catch(e => setMsg(`차단 · ${e.message}`));
  };
  if (hyp.status === "HYPOTHESIS_DRAFT") return (
    <div className="hr-actions">
      <input placeholder="검토자(필수)" value={reviewer} onChange={e => setReviewer(e.target.value)} />
      <input placeholder="검토 메모" value={note} onChange={e => setNote(e.target.value)} />
      <button type="button" className="btn sm" disabled={!reviewer.trim()}
        onClick={act("승인", () => _hrPost(baseUrl, `/hypothesis-registry/hypotheses/${hyp.hypothesis_id}/review`, { decision: "ACCEPTED_FOR_PREREG", reviewer, note }))}>사전등록 승인</button>
      <button type="button" className="btn ghost sm" disabled={!reviewer.trim()}
        onClick={act("자료요청", () => _hrPost(baseUrl, `/hypothesis-registry/hypotheses/${hyp.hypothesis_id}/review`, { decision: "NEEDS_DATA", reviewer, note }))}>자료 부족</button>
      <button type="button" className="btn ghost sm" disabled={!reviewer.trim()}
        onClick={act("기각", () => _hrPost(baseUrl, `/hypothesis-registry/hypotheses/${hyp.hypothesis_id}/review`, { decision: "REJECTED", reviewer, note }))}>기각</button>
      {msg && <span className="hr-msg mono">{msg}</span>}
    </div>
  );
  if (hyp.status === "ACCEPTED_FOR_PREREG") return (
    <div className="hr-actions">
      <button type="button" className="btn sm"
        onClick={act("초안 생성", () => _hrPost(baseUrl, `/hypothesis-registry/hypotheses/${hyp.hypothesis_id}/prereg-draft`))}>사전등록 초안 생성</button>
      <button type="button" className="btn ghost sm"
        onClick={act("큐 등록", () => _hrPost(baseUrl, "/hypothesis-registry/queue", { hypothesis_id: hyp.hypothesis_id, deadline: Date.now() / 1000 + 86400 * 7 }))}>연구 큐 등록(7일)</button>
      {msg && <span className="hr-msg mono">{msg}</span>}
    </div>
  );
  if (hyp.status === "PREREG_DRAFT") return (
    <div className="hr-actions">
      <input placeholder="승인 증거(회의/결재 ID, 필수)" value={approval.evidence} onChange={e => setApproval(c => ({ ...c, evidence: e.target.value }))} />
      <input placeholder="승인자(필수)" value={approval.approver} onChange={e => setApproval(c => ({ ...c, approver: e.target.value }))} />
      <button type="button" className="btn sm" disabled={!(approval.evidence.trim() && approval.approver.trim())}
        onClick={act("봉인", () => _hrPost(baseUrl, `/hypothesis-registry/preregs/${hyp.hypothesis_id}/seal`, { approval_evidence: approval.evidence, approver: approval.approver }))}>사전등록 봉인</button>
      <small className="hr-warn">사람 승인 증거 없이 봉인할 수 없습니다.</small>
      {msg && <span className="hr-msg mono">{msg}</span>}
    </div>
  );
  return null;
}

// UX-06 — 가설 초안 작성 폼: 필수 11개 필드를 모두 요구한다(비어 있으면 서버가 409).
function _HrDraftForm({ baseUrl, onChanged }) {
  const [f, setF] = useState_hr({
    finding_id: "", bundle_sha256: "", axis: "", role: "train", n: "", q: "",
    failure_explained: "", falsifiable_prediction: "",
    entry_time_vars: "", forbidden_vars: "", data_requirement: "",
    leakage_risk: "", negative_controls: "", budget: "", normal_stop: "",
  });
  const [msg, setMsg] = useState_hr("");
  const set = (k) => (e) => setF(c => ({ ...c, [k]: e.target.value }));
  const required = ["finding_id", "bundle_sha256", "axis", "failure_explained",
    "falsifiable_prediction", "entry_time_vars", "data_requirement",
    "leakage_risk", "budget", "normal_stop"];
  const missing = required.filter(k => !String(f[k]).trim());
  const submit = () => {
    setMsg("");
    _hrPost(baseUrl, "/hypothesis-registry/hypotheses", {
      finding: {
        finding_id: f.finding_id, bundle_sha256: f.bundle_sha256, axis: f.axis,
        role: f.role, n: f.n === "" ? null : Number(f.n),
        q: f.q === "" ? null : Number(f.q), effect: null, ci: null,
      },
      failure_explained: f.failure_explained,
      falsifiable_prediction: f.falsifiable_prediction,
      entry_time_vars: f.entry_time_vars.split(",").map(s => s.trim()).filter(Boolean),
      forbidden_vars: f.forbidden_vars.split(",").map(s => s.trim()).filter(Boolean),
      data_requirement: f.data_requirement, leakage_risk: f.leakage_risk,
      negative_controls: f.negative_controls.split(",").map(s => s.trim()).filter(Boolean),
      budget: f.budget, normal_stop: f.normal_stop,
    }).then(() => { setMsg("초안 등록 완료"); onChanged(); })
      .catch(e => setMsg(`차단 · ${e.message}`));
  };
  const field = (key, label, ph) => (
    <label key={key}>{label}
      <input value={f[key]} onChange={set(key)} placeholder={ph || ""} />
    </label>
  );
  return (
    <details className="hr-draft-form">
      <summary><b>새 가설 초안 작성</b><span>finding 기반 · 필수 필드 전부 필요 · validation/OOS finding은 차단됨</span></summary>
      <div className="hr-form-grid">
        {field("finding_id", "finding ID", "f-…")}
        {field("bundle_sha256", "bundle sha256", "64 hex")}
        {field("axis", "축", "exit_timing")}
        <label>role
          <select value={f.role} onChange={set("role")}>
            <option value="train">train</option>
            <option value="discovery">discovery</option>
            <option value="validation">validation(차단됨)</option>
            <option value="oos">oos(차단됨)</option>
          </select>
        </label>
        {field("n", "표본 n", "50")}
        {field("q", "q값", "0.03")}
        {field("failure_explained", "설명하는 실패")}
        {field("falsifiable_prediction", "반증 가능한 예측")}
        {field("entry_time_vars", "진입시점 변수(,)", "entry_price")}
        {field("forbidden_vars", "금지 변수(,)", "exit_pnl")}
        {field("data_requirement", "필요 자료량", "n>=30")}
        {field("leakage_risk", "누수 위험")}
        {field("negative_controls", "negative controls(,)")}
        {field("budget", "예산", "2 runs")}
        {field("normal_stop", "정상 STOP 조건", "q>0.1")}
      </div>
      <div className="hr-actions">
        <button type="button" className="btn sm" disabled={missing.length > 0}
          onClick={submit}>가설 초안 등록{missing.length ? ` (미기재 ${missing.length})` : ""}</button>
        {msg && <span className="hr-msg mono">{msg}</span>}
      </div>
    </details>
  );
}

function V4HypothesisRegistry({ baseUrl }) {
  const [view, setView] = useState_hr({ status: "loading", data: null, error: "" });
  const load = useCallback_hr(() => {
    const controller = new AbortController();
    fetch(String(baseUrl || "").replace(/\/$/, "") + "/hypothesis-registry/state", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(data => setView({ status: "ready", data, error: "" }))
      .catch(e => { if (e && e.name !== "AbortError") setView({ status: "error", data: null, error: String(e.message || e) }); });
    return () => controller.abort();
  }, [baseUrl]);
  useEffect_hr(() => load(), [load]);

  if (view.status === "loading") return <section className="hr-panel pending" aria-live="polite"><h3>가설 · 사전등록 원장</h3><p>원장을 읽는 중입니다.</p></section>;
  if (view.status === "error") return <section className="hr-panel danger" role="alert"><h3>가설 원장을 열 수 없습니다</h3><p>{view.error}</p></section>;
  const data = view.data || {};
  const counts = data.counts || {};
  const openFindings = (data.findings || []).filter(f => !(f.falsified_by || []).length);
  const falsified = (data.findings || []).filter(f => (f.falsified_by || []).length);

  return (
    <section className="hr-panel v4-cjk-safe" aria-labelledby="hr-title">
      <header className="hr-heading">
        <div><span>ANA-08 · FINDING → HYPOTHESIS → PREREG</span><h3 id="hr-title">가설 · 사전등록 원장</h3></div>
        <strong className="mono">{data.persistence || "none"}</strong>
      </header>
      <p className="hr-lede">봉인은 사람 승인 증거가 있을 때만 가능하며, 이 원장은 실행·채택·주문 권한을 주지 않습니다.</p>
      <div className="hr-counts" role="list" aria-label="상태별 가설 수">
        {["HYPOTHESIS_DRAFT", "ACCEPTED_FOR_PREREG", "PREREG_DRAFT", "PREREG_SEALED", "REJECTED", "NEEDS_DATA"].map(k => (
          <div key={k} role="listitem" className={"hr-count " + ((_HR_STATUS[k] || {}).cls || "")}>
            <b>{counts[k] || 0}</b><span>{(_HR_STATUS[k] || {}).ko || k}</span>
          </div>
        ))}
      </div>

      <_HrDraftForm baseUrl={baseUrl} onChanged={load} />

      <div className="hr-table-scroll" tabIndex={0}>
        <table className="hr-table">
          <caption>가설 원장 — bundle·finding 계보와 상태를 함께 표시</caption>
          <thead><tr><th>가설</th><th>상태</th><th>예측</th><th>bundle</th><th>findings</th><th>검토</th><th>행동</th></tr></thead>
          <tbody>
            {(data.hypotheses || []).length === 0 && <tr><td colSpan="7">등록된 가설이 없습니다.</td></tr>}
            {(data.hypotheses || []).map(h => {
              const meta = _HR_STATUS[h.status] || { cls: "", ko: h.status };
              return (
                <tr key={h.hypothesis_id}>
                  <th><code>{_hrShort(h.hypothesis_id)}</code></th>
                  <td><span className={"hr-badge " + meta.cls}>{meta.ko}</span></td>
                  <td>{h.falsifiable_prediction}</td>
                  <td><code>{_hrShort(h.bundle_sha256)}</code></td>
                  <td>{(h.source_finding_ids || []).map(fid => (
                    <a key={fid} href={`/?tab=catalog&view=registry#finding-${fid}`} title="finding 원장 행으로 이동">{fid}</a>
                  )).reduce((acc, el, i) => i ? [...acc, ", ", el] : [el], [])}</td>
                  <td>{h.review_note || "—"}</td>
                  <td><_HrActions baseUrl={baseUrl} hyp={h} onChanged={load} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="hr-grid">
        <section aria-label="지식·반증 원장">
          <h4>지식 원장 · 열림 {openFindings.length} / 반증됨 {falsified.length}</h4>
          <ul className="hr-findings">
            {(data.findings || []).map(f => (
              <li key={f.finding_id} id={`finding-${f.finding_id}`} className={f.falsified_by && f.falsified_by.length ? "falsified" : ""}>
                <code>{f.finding_id}</code> · {f.axis} · role={f.role} · n={f.n == null ? "미관측" : f.n} · q={f.q == null ? "미관측" : f.q}
                {f.falsified_by && f.falsified_by.length ? <em> 반증: {f.falsified_by.join(", ")}</em> : null}
              </li>
            ))}
          </ul>
        </section>
        <section aria-label="사전등록·큐">
          <h4>사전등록 봉인 {((data.preregs || []).filter(p => p.status === "PREREG_SEALED")).length}건 · 큐 {(data.queue || []).length}건</h4>
          <ul className="hr-preregs">
            {(data.preregs || []).map(p => (
              <li key={p.hypothesis_id}>
                <code>{_hrShort(p.hypothesis_id)}</code> · {p.status}
                {p.sealed_sha256 ? <> · seal <code>{_hrShort(p.sealed_sha256)}</code> · {p.approver}</> : null}
              </li>
            ))}
            {(data.queue || []).map(q => (
              <li key={q.item_id}>
                큐 <code>{q.item_id}</code> · {q.status} · 시도 {q.attempts}회 · 마감 {new Date(q.deadline * 1000).toISOString().slice(0, 10)}
                {(q.receipts || []).length ? <em> · 영수증 {q.receipts.length}건</em> : null}
              </li>
            ))}
          </ul>
        </section>
      </div>
      <footer>store {data.store || "—"} · corrupt {data.corrupt_events || 0} · 실행·G2·FROZEN_OOS 개봉 권한 없음</footer>
    </section>
  );
}

Object.assign(window, { V4HypothesisRegistry });
export { V4HypothesisRegistry };
