/* 확률 연구 도구 — 오프라인 안전 수동 진단/제안 패널.

   Bayesian sequential, AST source audit, QMC/Pareto preview, D0 denoising sentinel을
   한 곳에서 확인한다. 이 화면은 엔진 실행·DB 기록·OOS 판정·채택·내보내기를 하지 않는다.
   전역 충돌 방지로 LoopRt* 접두를 쓴다. */

const { useState: useState_lrt, useEffect: useEffect_lrt, useCallback: useCallback_lrt } = React;

const LOOP_RT_TOOL_SPECS = [
  { id: "bayesian", label: "Bayesian sequential", ko: "베이지안 순차 경계", endpoint: "/loop/research-tools/bayesian" },
  { id: "ast", label: "AST audit", ko: "AST 소스 감사", endpoint: "/loop/research-tools/ast" },
  { id: "qmc", label: "QMC/Pareto", ko: "QMC/Pareto 미리보기", endpoint: "/loop/research-tools/qmc" },
  { id: "denoise", label: "D0 denoising", ko: "D0 디노이징 센티널", endpoint: "/loop/research-tools/denoise" },
];

function loopRtBase(baseUrl) {
  return String(baseUrl || "").replace(/\/$/, "");
}

function loopRtSignal(ms) {
  return (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function")
    ? AbortSignal.timeout(ms)
    : undefined;
}

function loopRtJson(baseUrl, path, options) {
  const opts = Object.assign({ credentials: "same-origin", cache: "no-store" }, options || {});
  if (opts.body) opts.headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
  const signal = loopRtSignal(opts.method === "POST" ? 15000 : 8000);
  if (signal) opts.signal = signal;
  return fetch(loopRtBase(baseUrl) + path, opts).then(async (response) => {
    const text = await response.text();
    let payload = {};
    try { payload = text ? JSON.parse(text) : {}; }
    catch (e) { payload = { raw: text }; }
    if (!response.ok) {
      throw new Error(String((payload && (payload.detail || payload.error || payload.reason)) || `HTTP ${response.status}`));
    }
    return payload;
  });
}

function loopRtGet(baseUrl, path) {
  return loopRtJson(baseUrl, path, { method: "GET" });
}

function loopRtPost(baseUrl, path, body) {
  return loopRtJson(baseUrl, path, { method: "POST", body: JSON.stringify(body || {}) });
}

function loopRtClamp(value, fallback, min, max, integer) {
  const n = Number(value);
  const bounded = Math.max(min, Math.min(max, Number.isFinite(n) ? n : fallback));
  return integer ? Math.round(bounded) : bounded;
}

function loopRtFormat(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

function loopRtShort(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : loopRtFormat(value, 4);
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function loopRtParseDimensions(text) {
  return String(text || "")
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 8)
    .map((line, index) => {
      const parts = line.split(/[:,]/).map((part) => part.trim()).filter(Boolean);
      if (parts.length < 3) return null;
      const low = Number(parts[1]);
      const high = Number(parts[2]);
      if (!Number.isFinite(low) || !Number.isFinite(high) || low >= high) return null;
      return { name: parts[0] || `x${index + 1}`, kind: "continuous", low, high };
    })
    .filter(Boolean);
}

function loopRtToolFromStatus(status, spec) {
  const tools = Array.isArray(status && status.tools) ? status.tools : [];
  return tools.find((tool) => {
    const id = String((tool && tool.id) || "").toLowerCase();
    const endpoint = String((tool && tool.endpoint) || "").toLowerCase();
    const label = String((tool && tool.label) || "").toLowerCase();
    return id === spec.id || endpoint === spec.endpoint || endpoint.endsWith(spec.endpoint) || label.indexOf(spec.id) >= 0;
  }) || null;
}

function loopRtAuthorityText(payload) {
  const authority = payload && payload.authority ? String(payload.authority) : "미발행";
  return authority === "no_adoption" ? "no_adoption · 채택 권한 없음" : authority;
}

function LoopRtReceipts({ payload }) {
  if (!payload) return null;
  const authority = loopRtAuthorityText(payload);
  const items = [];
  if (payload.config_receipt) items.push(["config", payload.config_receipt]);
  if (payload.seed_receipt) items.push(["seed", payload.seed_receipt]);
  const receipts = payload.receipts;
  if (Array.isArray(receipts)) {
    receipts.slice(0, 8).forEach((value, index) => items.push([`receipt${index + 1}`, value]));
  } else if (receipts && typeof receipts === "object") {
    Object.keys(receipts).slice(0, 8).forEach((key) => items.push([key, receipts[key]]));
  }
  if (!items.length) return <p className="v4s-note">authority <span className="mono">{authority}</span> · receipts 미발행 · 이 출력은 채택 근거가 아닙니다.</p>;
  return (
    <div className="v4s-note" aria-label="연구 도구 영수증">
      <b>authority</b> <span className="mono">{authority}</span>{" "}
      <b>receipts</b>{" "}
      {items.map(([key, value]) => (
        <span key={key} className="mono" style={{ marginRight: 8 }}>{key}={loopRtShort(value)}</span>
      ))}
    </div>
  );
}

function LoopRtStatusGrid({ status }) {
  return (
    <div className="v4s-probe-grid" aria-label="확률 연구 도구 상태">
      {LOOP_RT_TOOL_SPECS.map((spec) => {
        const tool = status ? loopRtToolFromStatus(status, spec) : null;
        const available = !status ? false : (status.available !== false && !!tool);
        return (
          <div className="v4s-probe-card" key={spec.id}>
            <b>{spec.ko}</b>
            <span className={"mono " + (available ? "pos" : "neg")}>{available ? "사용 가능" : "대기/미발행"}</span>
            <small className="v4s-en">{tool ? `${tool.method || "POST"} ${tool.endpoint || spec.endpoint}` : spec.endpoint}</small>
            <small className="v4s-en">authority {status ? loopRtAuthorityText(status) : "상태 확인 중"}</small>
            <small>{spec.label}</small>
          </div>
        );
      })}
    </div>
  );
}

function LoopRtObjectPreview({ payload, title }) {
  if (!payload) return <p className="v4s-note">아직 실행한 수동 진단이 없습니다.</p>;
  const entries = Object.entries(payload).filter(([key]) => key !== "receipts" && key !== "config_receipt" && key !== "seed_receipt").slice(0, 14);
  return (
    <div>
      <div className="table-wrap" aria-label={title || "결과 요약"}>
        <table className="tbl">
          <tbody>
            {entries.map(([key, value]) => (
              <tr key={key}><th scope="row" className="mono">{key}</th><td className="mono">{loopRtShort(value)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      <LoopRtReceipts payload={payload}/>
    </div>
  );
}

function LoopRtBayesianResult({ payload }) {
  if (!payload) return <p className="v4s-note">아직 실행한 수동 진단이 없습니다. 버튼을 눌러야 POST 요청이 전송됩니다.</p>;
  const decision = String(payload.decision || payload.verdict || "pending");
  const decisionLabel = String(payload.decision_label || "statistical boundary only");
  const safeLabel = `${decision} ${decisionLabel}`.toUpperCase().indexOf("APPROVE") >= 0
    ? "APPROVE · statistical boundary only · 전략 승인 아님"
    : `${decision} · ${decisionLabel}`;
  return (
    <div>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>Posterior decision</b><span className="mono">{safeLabel}</span><small>통계 경계 표시이며 전략 승인/채택이 아닙니다.</small></div>
        <div className="v4s-probe-card"><b>posterior mean</b><span className="mono">{loopRtFormat(payload.posterior && payload.posterior.mean, 4)}</span></div>
        <div className="v4s-probe-card"><b>alpha/beta</b><span className="mono">{loopRtShort(payload.posterior && payload.posterior.alpha)} / {loopRtShort(payload.posterior && payload.posterior.beta)}</span></div>
        <div className="v4s-probe-card"><b>ROPE 초과확률</b><span className="mono">{loopRtFormat(payload.posterior && payload.posterior.probability_above_rope, 4)}</span></div>
      </div>
      <LoopRtReceipts payload={payload}/>
    </div>
  );
}

function LoopRtAstResult({ payload }) {
  if (!payload) return <p className="v4s-note">아직 실행한 수동 감사가 없습니다. 소스를 넣고 감사 버튼을 눌러야 합니다.</p>;
  const violations = Array.isArray(payload.violations) ? payload.violations : [];
  return (
    <div>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>감사 상태</b><span className={"mono " + (payload.ok ? "pos" : "neg")}>{payload.ok ? "위반 없음" : "검토 필요"}</span></div>
        <div className="v4s-probe-card"><b>violations</b><span className="mono">{violations.length}</span></div>
        <div className="v4s-probe-card"><b>estimated work</b><span className="mono">{loopRtShort(payload.estimated_work)}</span></div>
        <div className="v4s-probe-card"><b>parsed</b><span className="mono">{loopRtShort(payload.parsed)}</span></div>
      </div>
      {violations.length > 0 ? (
        <ul className="v4s-note">
          {violations.slice(0, 12).map((violation, index) => <li key={index} className="mono">{loopRtShort(violation)}</li>)}
        </ul>
      ) : <p className="v4s-note">위반 목록이 비어 있습니다. 그래도 채택/OOS 근거가 아니라 AST 진단 출력입니다.</p>}
      <LoopRtReceipts payload={payload}/>
    </div>
  );
}

function LoopRtQmcResult({ payload }) {
  if (!payload) return <p className="v4s-note">아직 QMC 미리보기를 만들지 않았습니다. seed/count 입력 후 버튼을 누르세요.</p>;
  const candidates = Array.isArray(payload.candidates) ? payload.candidates : [];
  const pareto = payload.pareto && Array.isArray(payload.pareto.entries) ? payload.pareto.entries : [];
  const columns = candidates.length ? Object.keys(candidates[0]).slice(0, 8) : [];
  return (
    <div>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>candidate preview</b><span className="mono">{candidates.length}</span><small>엔진 실행 아님</small></div>
        <div className="v4s-probe-card"><b>Pareto archive</b><span className="mono">{pareto.length}</span><small>제안 묶음일 뿐 채택 아님</small></div>
        <div className="v4s-probe-card"><b>authority</b><span className="mono">{loopRtAuthorityText(payload)}</span></div>
      </div>
      {candidates.length > 0 ? (
        <div className="table-wrap">
          <table className="tbl"><thead><tr>{columns.map((key) => <th key={key}>{key}</th>)}</tr></thead>
            <tbody>{candidates.slice(0, 10).map((row, index) => (
              <tr key={index}>{columns.map((key) => <td key={key} className="mono">{loopRtShort(row[key])}</td>)}</tr>
            ))}</tbody></table>
        </div>
      ) : <p className="v4s-note">후보 목록이 비어 있습니다. 이것도 미리보기 결과이며 자동 실행하지 않습니다.</p>}
      <LoopRtReceipts payload={payload}/>
    </div>
  );
}

export function LoopResearchToolsPanel({ baseUrl }) {
  const [status, setStatus] = useState_lrt(null);
  const [statusError, setStatusError] = useState_lrt("");
  const [busy, setBusy] = useState_lrt("");
  const [errors, setErrors] = useState_lrt({});
  const [results, setResults] = useState_lrt({ bayesian: null, ast: null, qmc: null, denoise: null });
  const [bayesian, setBayesian] = useState_lrt({ successes: "12", failures: "8", ropeLower: "0.50", approveThreshold: "0.95", rejectThreshold: "0.05", maxSample: "2000" });
  const [ast, setAst] = useState_lrt({ source: "", allowedFunctions: "", maxClauses: "24", maxLookback: "240", maxUnknownLines: "0" });
  const [qmc, setQmc] = useState_lrt({ seed: "1", count: "16", dimensions: "arm:0.1:1.2\ngive:0.0:0.8" });
  const [denoise, setDenoise] = useState_lrt({ source: "", seed: "1" });

  const loadStatus = useCallback_lrt(() => {
    setStatusError("");
    loopRtGet(baseUrl, "/loop/research-tools")
      .then((payload) => { setStatus(payload); setStatusError(payload && payload.available === false ? String(payload.reason || "연구 도구 상태가 unavailable 입니다.") : ""); })
      .catch((error) => { setStatus(null); setStatusError(`상태 요청 실패 · ${String(error && error.message || error)}`); });
  }, [baseUrl]);

  useEffect_lrt(() => { loadStatus(); }, [loadStatus]);

  const updateError = (key, message) => setErrors((prev) => Object.assign({}, prev, { [key]: message || "" }));
  const updateResult = (key, payload) => setResults((prev) => Object.assign({}, prev, { [key]: payload }));
  const runManual = (key, path, body) => {
    setBusy(key);
    updateError(key, "");
    loopRtPost(baseUrl, path, body)
      .then((payload) => updateResult(key, payload))
      .catch((error) => updateError(key, `요청 실패 · ${String(error && error.message || error)}`))
      .finally(() => setBusy(""));
  };

  const onBayesianSubmit = (event) => {
    event.preventDefault();
    const successes = loopRtClamp(bayesian.successes, 0, 0, 100000, true);
    const failures = loopRtClamp(bayesian.failures, 0, 0, 100000, true);
    const ropeLower = loopRtClamp(bayesian.ropeLower, 0.5, 0, 1, false);
    runManual("bayesian", "/loop/research-tools/bayesian", {
      config: {
        prior_alpha: 1,
        prior_beta: 1,
        rope_lower: ropeLower,
        approve_prob_threshold: loopRtClamp(bayesian.approveThreshold, 0.95, 0, 1, false),
        reject_prob_threshold: loopRtClamp(bayesian.rejectThreshold, 0.05, 0, 1, false),
        max_sample: loopRtClamp(bayesian.maxSample, 2000, successes + failures, 200000, true),
        credible_mass: 0.95,
      },
      counts: { successes, failures },
    });
  };

  const onAstSubmit = (event) => {
    event.preventDefault();
    if (!String(ast.source || "").trim()) {
      updateError("ast", "감사할 소스를 입력하세요.");
      return;
    }
    runManual("ast", "/loop/research-tools/ast", {
      source: String(ast.source || "").slice(0, 12000),
      allowed_functions: String(ast.allowedFunctions || "").split(",").map((item) => item.trim()).filter(Boolean).slice(0, 64),
      limits: {
        max_clauses: loopRtClamp(ast.maxClauses, 24, 1, 200, true),
        max_lookback: loopRtClamp(ast.maxLookback, 240, 1, 5000, false),
        max_unknown_lines: loopRtClamp(ast.maxUnknownLines, 0, 0, 1000, true),
      },
    });
  };

  const onQmcSubmit = (event) => {
    event.preventDefault();
    const dimensions = loopRtParseDimensions(qmc.dimensions);
    if (!dimensions.length) {
      updateError("qmc", "dimension은 name:low:high 형식으로 1개 이상 입력하세요.");
      return;
    }
    runManual("qmc", "/loop/research-tools/qmc", {
      dimensions,
      budget: loopRtClamp(qmc.count, 16, 1, 128, true),
      seed: loopRtClamp(qmc.seed, 1, 0, Number.MAX_SAFE_INTEGER, true),
      scramble: true,
      skip: 0,
    });
  };

  const onDenoiseSubmit = (event) => {
    event.preventDefault();
    if (!String(denoise.source || "").trim()) {
      updateError("denoise", "D0 소스/템플릿을 입력하세요.");
      return;
    }
    runManual("denoise", "/loop/research-tools/denoise", {
      source: String(denoise.source || "").slice(0, 12000),
      seed: loopRtClamp(denoise.seed, 1, 0, Number.MAX_SAFE_INTEGER, true),
      operator: "mask_one_clause",
    });
  };

  const statusAuthority = status ? loopRtAuthorityText(status) : "상태 확인 중";
  return (
    <div className="loop-research-tools" aria-label="확률 연구 도구">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">확률 연구 도구 <small className="v4s-en">offline-safe manual diagnostics</small></div>
          <span className="badge warn" title="진단/제안 전용이며 채택 권한이 없습니다.">no_adoption</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note"><b>진단/제안 전용</b> — Bayesian, AST, QMC/Pareto, D0 출력은 OOS 판정·전략 채택·내보내기 권한이 없습니다. Bayesian 응답에 <span className="mono">APPROVE</span>가 보여도 <b>statistical boundary only</b>이며 전략 승인 아님입니다.</p>
          <div className="v4s-log-controls">
            <button className="btn ghost sm" type="button" onClick={loadStatus}>상태 새로고침</button>
            <small className="v4s-en">GET /loop/research-tools · authority {statusAuthority}</small>
          </div>
          {statusError && <p className="v4-research-error" role="alert">{statusError}</p>}
          {!status && !statusError && <p className="v4s-note">상태 확인 중입니다. 수동 폼은 상태 응답이 비어 있어도 버튼을 누를 때만 요청됩니다.</p>}
          <LoopRtStatusGrid status={status}/>
          {status && Array.isArray(status.warnings) && status.warnings.length > 0 && (
            <ul className="v4s-note">{status.warnings.map((warning, index) => <li key={index}>{String(warning)}</li>)}</ul>
          )}
          <LoopRtReceipts payload={status}/>
        </div>
      </div>

      <div className="v6-stage-grid v59-matrix" style={{ marginTop: 12 }}>
        <section className="panel" aria-labelledby="loop-rt-bayesian-heading">
          <div className="panel-hd"><div id="loop-rt-bayesian-heading" className="panel-hd-title">Bayesian sequential <small className="v4s-en">success/failure/ROPE</small></div><span className="badge">manual</span></div>
          <div className="panel-bd">
            <form onSubmit={onBayesianSubmit}>
              <div className="v4s-log-controls" style={{ flexWrap: "wrap" }}>
                <label>successes <input type="number" min="0" max="100000" value={bayesian.successes} onChange={(e) => setBayesian(Object.assign({}, bayesian, { successes: e.target.value }))}/></label>
                <label>failures <input type="number" min="0" max="100000" value={bayesian.failures} onChange={(e) => setBayesian(Object.assign({}, bayesian, { failures: e.target.value }))}/></label>
                <label>ROPE lower <input type="number" min="0" max="1" step="0.01" value={bayesian.ropeLower} onChange={(e) => setBayesian(Object.assign({}, bayesian, { ropeLower: e.target.value }))}/></label>
                <label>approve prob <input type="number" min="0" max="1" step="0.01" value={bayesian.approveThreshold} onChange={(e) => setBayesian(Object.assign({}, bayesian, { approveThreshold: e.target.value }))}/></label>
                <label>reject prob <input type="number" min="0" max="1" step="0.01" value={bayesian.rejectThreshold} onChange={(e) => setBayesian(Object.assign({}, bayesian, { rejectThreshold: e.target.value }))}/></label>
                <button className="btn primary sm" type="submit" disabled={busy === "bayesian"}>posterior decision 계산</button>
              </div>
            </form>
            <p className="v4s-note">POST /loop/research-tools/bayesian · posterior decision은 통계 경계만 표시합니다.</p>
            {errors.bayesian && <p className="v4-research-error" role="alert">{errors.bayesian}</p>}
            <LoopRtBayesianResult payload={results.bayesian}/>
          </div>
        </section>

        <section className="panel" aria-labelledby="loop-rt-ast-heading">
          <div className="panel-hd"><div id="loop-rt-ast-heading" className="panel-hd-title">AST source audit <small className="v4s-en">bounded source inspection</small></div><span className="badge">manual</span></div>
          <div className="panel-bd">
            <form onSubmit={onAstSubmit}>
              <label>source<textarea value={ast.source} placeholder="감사할 조건식/파이썬 조각" onChange={(e) => setAst(Object.assign({}, ast, { source: e.target.value }))} style={{ width: "100%", minHeight: 120 }}/></label>
              <div className="v4s-log-controls" style={{ flexWrap: "wrap" }}>
                <label>allowed functions <input value={ast.allowedFunctions} placeholder="MA, CROSSUP" onChange={(e) => setAst(Object.assign({}, ast, { allowedFunctions: e.target.value }))}/></label>
                <label>max clauses <input type="number" min="1" max="200" value={ast.maxClauses} onChange={(e) => setAst(Object.assign({}, ast, { maxClauses: e.target.value }))}/></label>
                <label>max lookback <input type="number" min="1" max="5000" value={ast.maxLookback} onChange={(e) => setAst(Object.assign({}, ast, { maxLookback: e.target.value }))}/></label>
                <label>unknown lines <input type="number" min="0" max="1000" value={ast.maxUnknownLines} onChange={(e) => setAst(Object.assign({}, ast, { maxUnknownLines: e.target.value }))}/></label>
                <button className="btn primary sm" type="submit" disabled={busy === "ast"}>AST 감사</button>
              </div>
            </form>
            <p className="v4s-note">POST /loop/research-tools/ast · 소스 구조 진단이며 엔진 검증/OOS가 아닙니다.</p>
            {errors.ast && <p className="v4-research-error" role="alert">{errors.ast}</p>}
            <LoopRtAstResult payload={results.ast}/>
          </div>
        </section>

        <section className="panel" aria-labelledby="loop-rt-qmc-heading">
          <div className="panel-hd"><div id="loop-rt-qmc-heading" className="panel-hd-title">QMC/Pareto preview <small className="v4s-en">seed/count bounded</small></div><span className="badge">manual</span></div>
          <div className="panel-bd">
            <form onSubmit={onQmcSubmit}>
              <label>dimensions <textarea value={qmc.dimensions} placeholder="name:low:high" onChange={(e) => setQmc(Object.assign({}, qmc, { dimensions: e.target.value }))} style={{ width: "100%", minHeight: 76 }}/></label>
              <div className="v4s-log-controls" style={{ flexWrap: "wrap" }}>
                <label>seed <input value={qmc.seed} onChange={(e) => setQmc(Object.assign({}, qmc, { seed: e.target.value }))}/></label>
                <label>count <input type="number" min="1" max="128" value={qmc.count} onChange={(e) => setQmc(Object.assign({}, qmc, { count: e.target.value }))}/></label>
                <button className="btn primary sm" type="submit" disabled={busy === "qmc"}>QMC 후보 미리보기</button>
              </div>
            </form>
            <p className="v4s-note">POST /loop/research-tools/qmc · Pareto archive는 제안 목록이며 실행·채택하지 않습니다.</p>
            {errors.qmc && <p className="v4-research-error" role="alert">{errors.qmc}</p>}
            <LoopRtQmcResult payload={results.qmc}/>
          </div>
        </section>

        <section className="panel" aria-labelledby="loop-rt-denoise-heading">
          <div className="panel-hd"><div id="loop-rt-denoise-heading" className="panel-hd-title">D0 denoising <small className="v4s-en">source/template seed sentinel</small></div><span className="badge">manual</span></div>
          <div className="panel-bd">
            <form onSubmit={onDenoiseSubmit}>
              <label>D0 source/template<textarea value={denoise.source} placeholder="디노이징 센티널을 확인할 소스/템플릿" onChange={(e) => setDenoise(Object.assign({}, denoise, { source: e.target.value }))} style={{ width: "100%", minHeight: 110 }}/></label>
              <div className="v4s-log-controls" style={{ flexWrap: "wrap" }}>
                <label>seed sentinel <input value={denoise.seed} onChange={(e) => setDenoise(Object.assign({}, denoise, { seed: e.target.value }))}/></label>
                <span className="v4s-en">operator mask_one_clause</span>
                <button className="btn primary sm" type="submit" disabled={busy === "denoise"}>D0 센티널 진단</button>
              </div>
            </form>
            <p className="v4s-note">POST /loop/research-tools/denoise · deterministic corruption/repair 진단만 표시합니다.</p>
            {errors.denoise && <p className="v4-research-error" role="alert">{errors.denoise}</p>}
            <LoopRtObjectPreview payload={results.denoise} title="D0 denoising result"/>
          </div>
        </section>
      </div>
    </div>
  );
}
