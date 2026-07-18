/* v4-research.jsx — V4 "Research Live" (플래그십, graph-first)
 *
 *   승인 프로토타입 구현: 좌측 대형 hero(V4HeroChart canvas) + 스탯 행 + 보조 차트 +
 *   접이식 분석 스택 / 우측 관찰성 rail(현재세대 · Best/Winner 게이트 ·
 *   조건식 발굴 거버넌스(wt-dev research_observability) · population).
 *   전부 기존 V2 컴포넌트 재배치 + V4 전용 캔버스 hero. 데이터/액션은 셸에서 props.
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner } from "./panels.jsx";
import { HypothesisPanel } from "./hypothesis.jsx";
import { GenerationsTable } from "./table.jsx";
import { EvolutionAnalysisPanel } from "./evolution-analysis.jsx";
import { EvolutionGuiParityPanel } from "./evolution-gui-parity-panel.jsx";
import { ResearchGlossaryPanel } from "./glossary.jsx";
import { ProfitChart, QualityTrendChart, EquityOverlayChart, BacktestDetailChart } from "./chart.jsx";
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
import { PhaseDetailPanel, ProcessFlowPanel } from "./phase-detail.jsx";
import { V4HeroChart } from "./v4-charts.jsx";
import { V4LoopCycle } from "./v4-loop-cycle.jsx";
const { useEffect: useEffect_v4r, useRef: useRef_v4r, useState: useState_v4r } = React;

const _V4_APPROVAL_HASH_KEYS = ["review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"];

function _v4ApprovalBindingProblem(binding, state) {
  const winner = state && state.winner;
  if (!winner) return "우승 후보가 아직 확정되지 않았습니다.";
  if (!binding || typeof binding !== "object") return "동결 검토 근거를 확인하는 중입니다.";
  if (binding.available !== true) return `동결 검토 근거를 사용할 수 없습니다 (${String(binding.reason || "사유 미발행")}).`;
  const missing = ["run_id", "current_gen", "winner_gen", ..._V4_APPROVAL_HASH_KEYS]
    .filter(key => binding[key] === undefined || binding[key] === null || binding[key] === "");
  if (missing.length) return `승인 근거 필드가 누락되었습니다 (${missing.join(", ")}).`;
  if (binding.run_id !== state.run_id || Number(binding.current_gen) !== Number(state.current_gen)
      || Number(binding.winner_gen) !== Number(winner.gen)
      || binding.winner_buy !== winner.buy_name || binding.winner_sell !== winner.sell_name) {
    return "현재 run·세대·우승 후보와 동결 승인 근거가 일치하지 않습니다.";
  }
  const invalidHash = _V4_APPROVAL_HASH_KEYS.find(key => !/^[0-9a-f]{64}$/.test(String(binding[key])));
  return invalidHash ? `승인 근거 해시 형식이 올바르지 않습니다 (${invalidHash}).` : "";
}

// 접이식 섹션(app.jsx _EvoSection 패턴 — styles.css .evo-group 재사용, V4 전용 storage key)
function _V4Fold({ storageKey, label, children, defaultOpen = true }) {
  const [open, setOpen] = useState_v4r(() => {
    try { const v = window.localStorage.getItem(storageKey); return v === null ? defaultOpen : v === "1"; }
    catch (e) { return defaultOpen; }
  });
  const onToggle = (e) => {
    const o = e.currentTarget.open;
    setOpen(o);
    try { window.localStorage.setItem(storageKey, o ? "1" : "0"); } catch (e2) {}
  };
  return (
    <details className="evo-group" open={open} onToggle={onToggle}>
      <summary className="evo-group-summary" aria-expanded={open}>
        <div className="stom-section-label">{label}</div>
      </summary>
      <div className="evo-group-body">{children}</div>
    </details>
  );
}

const V4_LIVE_STEP_KEYS = ["generate", "backtest", "score", "autopsy"];
const V4_LIVE_STEP_LABELS = ["생성", "백테스트", "채점", "부검"];
const V4_LIVE_PHASE_STEP = {
  loop_start: 0, warm_prepare_start: 0, warm_prepare_done: 0, ga_init: 0, generate_start: 0, generate_done: 0,
  backtest_start: 1, ga_evaluate_start: 1, backtest_end: 2, score_start: 2, score_done: 2,
  autopsy_start: 3, autopsy_done: 3, generation_done: 4, ga_generation_done: 4, complete: 4,
};
function _v4ObjectSummary(value, fields, empty = "empty") {
  if (value === null || value === undefined || value === "") return empty;
  if (typeof value !== "object") return String(value);
  const parts = fields.flatMap(field => {
    const item = value[field];
    return item === null || item === undefined || item === "" || typeof item === "object" ? [] : [`${field} ${String(item)}`];
  });
  return parts.length ? parts.join(" · ") : empty;
}

function _v4EngineSummary(value) {
  return _v4ObjectSummary(value, ["status", "phase", "bt_engine_mode", "bt_timeframe", "effective_engine_count"], "대기");
}

function _v4ProgressSummary(value) {
  if (value && typeof value === "object" && Number.isFinite(Number(value.percent))) {
    const source = value.progress_source || value.source || value.phase;
    return `${Number(value.percent).toFixed(1)}%${source ? ` · ${String(source)}` : ""}`;
  }
  return _v4ObjectSummary(value, ["phase", "done_units", "total_units", "progress_source", "source"], "대기");
}

function v4LiveSituation(state) {
  const s = state || {};
  const latest = s.latest || {};
  const phase = String(latest.phase || "").toLowerCase();
  const statusValues = [s.status, latest.status].map(value => String(value || "").toLowerCase());
  const engineState = latest.engine_state ?? s.engine_state ?? null;
  const engine = String(engineState && typeof engineState === "object" ? (engineState.status || engineState.phase || "") : (engineState || "")).toLowerCase();
  const phaseStartedAt = latest.phase_started_at || null;
  const backtestProgress = latest.backtest_progress ?? s.backtest_progress ?? null;
  const rawStep = Number(latest.current_step);
  const mapped = Object.prototype.hasOwnProperty.call(V4_LIVE_PHASE_STEP, phase)
    ? V4_LIVE_PHASE_STEP[phase]
    : (Number.isFinite(rawStep) ? rawStep : -1);
  const mappedActive = Math.min(3, Math.max(0, mapped));
  const terminalFailure = statusValues.some(value => ["error", "failed", "blocked"].includes(value))
    || ["error", "failed"].includes(engine);
  const stopping = !terminalFailure && (statusValues.some(value => value === "stopping") || phase === "stopping");
  const reconnecting = !terminalFailure && !stopping && statusValues.some(value => ["reconnect", "reconnecting", "disconnected"].includes(value));
  const exceptionalState = terminalFailure ? "failure" : ((stopping || reconnecting) ? "retry" : "");
  const complete = !exceptionalState && (statusValues.includes("complete") || phase === "complete" || mapped >= 4);
  const active = complete ? 3 : mappedActive;
  const legacy = !phase && !Number.isFinite(rawStep);
  const steps = V4_LIVE_STEP_KEYS.map((key, index) => {
    let stateName = "pending";
    if (exceptionalState && index === active) stateName = exceptionalState;
    else if (Array.isArray(latest.skipped_steps) && latest.skipped_steps.includes(key)) stateName = "skipped";
    else if (complete) stateName = "success";
    else if (index < active) stateName = "success";
    else if (index === active && !legacy) stateName = "active";
    return { key, index, state: stateName, seconds: Number((latest.step_timings || {})[key]) };
  });
  return { active, steps, complete, legacy, reconnecting, stopping, terminalFailure, phase, engine, engineState, phaseStartedAt, backtestProgress };
}

function _v4EvidenceState(state) {
  const s = state || {};
  const latest = s.latest || {};
  const current = s.current_run || {};
  if (s.error || latest.error) return { label: "error", value: latest.error || s.error, source: "loop status" };
  const candidates = [
    { source: "latest", value: latest.analysis_evidence || latest.evidence, status: latest.evidence_status, stale: latest.stale, error: latest.evidence_error },
    { source: "current_run", value: current.analysis_evidence || current.evidence, status: current.evidence_status, stale: current.stale, error: current.evidence_error },
    { source: "root", value: s.analysis_evidence || s.evidence, status: s.evidence_status, stale: s.stale, error: s.evidence_error },
  ];
  const selected = candidates.find(candidate => candidate.value && (!Array.isArray(candidate.value) || candidate.value.length));
  if (selected) {
    const status = String(selected.status || "").toLowerCase();
    if (selected.error || status === "error") return { label: "error", value: selected.error || "분석 증거 발행 오류", source: selected.source };
    if (selected.stale === true || status === "stale") return { label: "stale", value: selected.value, source: selected.source };
    if (status === "fresh") return { label: "fresh", value: selected.value, source: selected.source };
    return { label: "stale", value: selected.value, source: selected.source };
  }
  const generation = (Array.isArray(s.generations) ? s.generations : [])
    .find(item => Number(item.gen_no) === Number(s.current_gen));
  const metrics = generation ? [
    generation.graded_score != null ? `graded_score ${generation.graded_score}` : "",
    generation.profit != null ? `profit ${generation.profit}` : "",
    generation.mdd != null ? `mdd ${generation.mdd}` : "",
  ].filter(Boolean) : [];
  return metrics.length
    ? { label: "stale", value: metrics, source: "generations metrics · freshness 미발행" }
    : { label: "empty", value: "발행된 분석 증거 없음", source: "unavailable" };
}

const V5_2_FIELD_SOURCES = [
  { field: "매수 조건식 · buy_code", paths: "GET /strategy_code → buy_code (production) / current_run.generation.buy_code_partial (demo streaming only)", unit: "STOM 조건식", status: "/strategy_code.code_status / latest.phase", owner: "Strategy code read API / LoopState snapshot publisher" },
  { field: "매도 조건식 · sell_code", paths: "GET /strategy_code → sell_code (production) / current_run.generation.sell_code_partial (demo streaming only)", unit: "STOM 조건식", status: "/strategy_code.code_status / latest.phase", owner: "Strategy code read API / LoopState snapshot publisher" },
  { field: "source / run_id / generation", paths: "GET /strategy_code / run_id / current_gen", unit: "source · run ID · generation", status: "/strategy_code.code_status / latest.status", owner: "Strategy code read API / LoopState snapshot publisher" },
  { field: "engine_state / backtest_progress", paths: "latest.engine_state / latest.backtest_progress", unit: "engine status/config · percent/count progress", status: "latest.engine_state.status / latest.backtest_progress.phase / latest.status", owner: "Backtest state publisher" },
  { field: "analysis evidence", paths: "generations[].graded_score/profit/mdd (production) / latest.analysis_evidence + latest.evidence_status (optional extension)", unit: "score · KRW · percent / evidence entries", status: "latest.status / selected source evidence_status", owner: "LoopState snapshot publisher / optional analysis extension" },
];

function _V5_2FieldSourceTable() {
  return (
    <section className="v4-field-source-table" aria-labelledby="v5-2-field-source-heading">
      <h3 id="v5-2-field-source-heading">V5.2 sealed field-source table</h3>
      <table>
        <thead><tr><th>displayed field</th><th>authoritative state path(s)</th><th>unit</th><th>freshness / status path</th><th>owner</th></tr></thead>
        <tbody>{V5_2_FIELD_SOURCES.map(row => <tr key={row.field}><th scope="row">{row.field}</th><td className="mono">{row.paths}</td><td>{row.unit}</td><td className="mono">{row.status}</td><td>{row.owner}</td></tr>)}</tbody>
      </table>
    </section>
  );
}

function _V4WorkflowStrip({ state, situation }) {
  const s = state || {};
  const latest = s.latest || {};
  const discovery = (s.page_data && s.page_data.condition_discovery) || {};
  const observability = discovery.research_observability || {};
  const blockers = observability.promotion_blockers || discovery.promotion_blockers || s.blockers || [];
  const blockerList = Array.isArray(blockers) ? blockers : (blockers.blockers || []);
  const logs = Array.isArray(latest.recent_logs) ? latest.recent_logs : [];
  const [logsOpen, setLogsOpen] = useState_v4r(false);
  const effective = latest.effective_gates || latest.effective_scoring || s.current_run?.effective_gates || s.current_run?.effective_scoring || s.active_config || {};
  const gateText = effective.gates || effective.target_score || effective.target_mdd || "현재 run 유효값 발행 대기";
  return (
    <section className="v4-situation-board v4-research-evidence" aria-labelledby="v4-research-evidence-heading">
      <div className="v4-situation-head">
        <div><h2 id="v4-research-evidence-heading" className="panel-hd-title">실시간 연구 상황</h2>
          <p className="v4-research-live-summary" role="status" aria-live="polite">run {s.run_id || "legacy"} · gen {s.current_gen ?? "—"} · {situation.legacy ? "legacy snapshot" : (s.status || "idle")}</p>
          <p className="v4-engine-summary">engine {_v4EngineSummary(situation.engineState)} · progress {_v4ProgressSummary(situation.backtestProgress)} · phase started {situation.phaseStartedAt || "대기"}</p></div>
        <div className="v4-effective-summary"><b>현재 run 유효 게이트/채점</b><span>{typeof gateText === "string" ? gateText : JSON.stringify(gateText)}</span><small>정책 기본값과 별도 · latest.effective_gates / active_config</small></div>
      </div>
      <div className="v4-timing-bars" aria-label="단계별 실제 시간">
        {situation.steps.map(step => <div className={"v4-timing-step " + step.state} key={step.key}>
          <span>{V4_LIVE_STEP_LABELS[step.index]}</span><i style={{ "--v4-duration": `${Math.min(100, Math.max(8, (Number.isFinite(step.seconds) ? step.seconds : 0) * 8))}%` }}></i>
          <b>{Number.isFinite(step.seconds) ? `${step.seconds.toFixed(1)}초` : "—"}</b>
        </div>)}
      </div>
      <div className="v4-situation-meta">
        <div className="v4-blocker-badges" aria-label="차단 사유">{blockerList.length ? blockerList.map((blocker, index) => <span key={index}>{String(blocker)}</span>) : <span className="clear">차단 사유 없음</span>}</div>
        <button type="button" className="v4-log-toggle" aria-expanded={logsOpen} onClick={() => setLogsOpen(open => !open)}>로그 {logsOpen ? "접기" : "펼치기"}</button>
        <p className={"v4-one-line-log" + (logsOpen ? " expanded" : "")}>{logsOpen ? (logs.join("\n") || "로그 대기") : String(logs[logs.length - 1] || latest.message || "로그 대기")}</p>
      </div>
      {s.error || latest.error ? <p className="v4-research-error" role="alert">연구 요청 실패 · {String(s.error || latest.error)}</p> : null}
    </section>
  );
}

function _V4Stats({ state }) {
  const curRaw = Number(state.current_gen);
  const cur = Number.isFinite(curRaw) && curRaw >= 0 ? curRaw : "시작 전";
  const max = Number(state.max_generations) || 0;
  const best = state.best || null;
  const bestGen = best ? (state.generations || []).find(g => g.gen_no === best.gen) : null;
  const bestScore = best && best.graded_score != null ? Number(best.graded_score) : null;
  const mdd = bestGen && bestGen.mdd != null ? Number(bestGen.mdd) : null;
  const tokens = (state.cumulative && Number(state.cumulative.tokens)) || 0;
  const cost = (state.cumulative && state.cumulative.cost_or_count) ?? "—";
  return (
    <div className="v4-stats">
      <div className="v4-stat">
        <span className="v">{cur}<span className="dim"> / {max || "—"}</span></span>
        <span className="s">현재 세대 · {state.status || "idle"}</span>
      </div>
      <div className="v4-stat">
        <span className={"v" + (bestScore != null ? " pos" : "")}>{bestScore != null ? bestScore.toFixed(2) : "—"}</span>
        <span className="s">best fitness{best && best.gate_passed ? " · gate ✓" : ""}</span>
      </div>
      <div className="v4-stat">
        <span className={"v" + (mdd != null ? " neg" : "")}>{mdd != null ? "-" + Math.abs(mdd).toFixed(1) + "%" : "—"}</span>
        <span className="s">best MDD</span>
      </div>
      <div className="v4-stat">
        <span className="v">{tokens ? (tokens >= 1000 ? (tokens / 1000).toFixed(1) + "k" : tokens) : "—"}</span>
        <span className="s">tokens · cost {String(cost)}</span>
      </div>
    </div>
  );
}

// 온보딩(V2 IdleState 의 Welcome·루프 개요 이식) — idle + 세대 없음일 때만 노출.
function _V4Onboarding({ onOpenSettings }) {
  const steps = [
    ["조건식 만들기", "LLM이 이전 실패 원인과 좋은 예시를 참고해 매수/매도 규칙을 작성합니다."],
    ["과거 데이터로 검증", "백테스트 엔진이 지정 기간의 종목 데이터를 돌려 손익·낙폭·거래 빈도를 계산합니다."],
    ["점수 계산", "수익, 위험(MDD), 우상향, 일평균 거래, 손익비를 목표 공식에 맞춰 점수화합니다."],
    ["통과 기준 확인", "목표 적합도, MDD 상한, 일평균 거래 하한을 만족하는지 확인합니다."],
    ["실패 원인 요약", "왜 떨어졌는지 쉬운 말로 정리해 다음 세대 프롬프트에 넣습니다."],
    ["다시 개선", "이름 붙은 run·세대·백테스트 결과를 저장해 나중에 다시 찾을 수 있게 합니다."],
  ];
  return (
    <div className="panel v4-onboarding">
      <div className="panel-bd v4-onboarding-bd">
        <div>
          <h2>조건식 AI 루프를 시작할 준비가 되었습니다</h2>
          <p>
            AI가 한국 주식 매수/매도 전략을 자동 생성·백테스트·채점·부검하며 조건식을 진화시킵니다.
            각 세대의 부검이 다음 세대 생성기에 피드백됩니다. 우승 후보의 운영 export 는
            연구 확인과 분리된 human 승인 절차입니다.
          </p>
          <button className="btn primary lg" onClick={onOpenSettings}>▸ 조건식 AI 시작 설정 열기</button>
        </div>
        <ol className="v4-onboarding-steps">
          {steps.map(([k, d], i) => (
            <li key={k}><b>{i + 1}. {k}</b><span>{d}</span></li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function V4ResearchLive({ baseUrl, state, wsStatus, send, lastReply, onViewCode, onOpenSettings, targetScore, mddCap, minDailyTrades }) {
  const [approvalOpen, setApprovalOpen] = useState_v4r(false);
  const [approvalBinding, setApprovalBinding] = useState_v4r(null);
  const [approvalBlockReason, setApprovalBlockReason] = useState_v4r("동결 승인 근거를 확인하는 중입니다.");
  const [selectedDetailGen, setSelectedDetailGen] = useState_v4r(null);
  const [strategyCodePayload, setStrategyCodePayload] = useState_v4r(null);
  const [strategyCodeStatus, setStrategyCodeStatus] = useState_v4r("idle");
  const s = state || {};
  const runId = s.run_id || "";
  const gens = Array.isArray(s.generations) ? s.generations : [];
  const stream = (s.current_run && s.current_run.generation) || {};
  const streamedGeneration = Boolean(stream.buy_code_partial || stream.sell_code_partial);
  const strategyGen = s.current_gen != null && Number.isFinite(Number(s.current_gen)) && Number(s.current_gen) >= 0
    ? Number(s.current_gen) : null;
  const hasData = gens.length > 0;
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;
  const viewCode = typeof onViewCode === "function" ? onViewCode : () => {};
  const situation = v4LiveSituation(s);
  const runGenerationIdentity = `${runId}:${s.current_gen ?? "legacy"}`;
  const [selectedStep, setSelectedStep] = useState_v4r(situation.active);
  const [drawerOpen, setDrawerOpen] = useState_v4r(false);
  const pinnedStepRef = useRef_v4r(false);
  const identityRef = useRef_v4r(runGenerationIdentity);
  useEffect_v4r(() => {
    if (identityRef.current !== runGenerationIdentity) {
      identityRef.current = runGenerationIdentity;
      pinnedStepRef.current = false;
      setSelectedStep(situation.active);
    } else if (!pinnedStepRef.current) setSelectedStep(situation.active);
  }, [runGenerationIdentity, situation.active]);
  useEffect_v4r(() => {
    setStrategyCodePayload(null);
    if (streamedGeneration) {
      setStrategyCodeStatus("streaming_partial");
      return;
    }
    if (!baseUrl || !runId || strategyGen === null) {
      setStrategyCodeStatus("unavailable");
      return;
    }
    let active = true;
    setStrategyCodeStatus("loading");
    const endpoint = `${String(baseUrl).replace(/\/$/, "")}/strategy_code?run=${encodeURIComponent(runId)}&gen=${strategyGen}`;
    fetch(endpoint, { signal: AbortSignal.timeout(2500) })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`strategy_code HTTP ${response.status}`)))
      .then(payload => {
        if (!active) return;
        setStrategyCodePayload(payload || null);
        setStrategyCodeStatus(payload && payload.code_status === "ok" ? "fresh" : String(payload && payload.code_status || "empty"));
      })
      .catch(error => {
        if (!active) return;
        setStrategyCodeStatus(`error · ${String(error && error.message || error)}`);
      });
    return () => { active = false; };
  }, [baseUrl, runId, strategyGen, streamedGeneration]);
  const selectStep = (index, pinned = true) => {
    pinnedStepRef.current = pinned;
    setSelectedStep(index);
  };
  const onStepKeyDown = (event, index) => {
    const next = event.key === "ArrowRight" ? (index + 1) % V4_LIVE_STEP_KEYS.length
      : event.key === "ArrowLeft" ? (index + V4_LIVE_STEP_KEYS.length - 1) % V4_LIVE_STEP_KEYS.length
        : event.key === "Home" ? 0 : event.key === "End" ? V4_LIVE_STEP_KEYS.length - 1 : null;
    if (next !== null) {
      event.preventDefault();
      selectStep(next);
      window.requestAnimationFrame(() => {
        const tab = document.getElementById("v4-live-tab-" + V4_LIVE_STEP_KEYS[next]);
        if (tab) tab.focus();
      });
    }
  };

  useEffect_v4r(() => {
    let active = true;
    setApprovalBinding(null);
    setApprovalBlockReason("동결 승인 근거를 확인하는 중입니다.");
    const endpoint = String(baseUrl || "").replace(/\/$/, "") + "/freeze_verdict";
    fetch(endpoint, { signal: AbortSignal.timeout(12000) })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(verdict => {
        if (!active) return;
        const binding = verdict && verdict.approval_binding;
        setApprovalBinding(binding || null);
        setApprovalBlockReason(_v4ApprovalBindingProblem(binding, s));
      })
      .catch(error => {
        if (active) setApprovalBlockReason(`동결 검토 근거 요청에 실패했습니다 (${String(error && error.message || error)}).`);
      });
    return () => { active = false; };
  }, [baseUrl, runId, s.current_gen, s.winner && s.winner.gen, s.winner && s.winner.buy_name, s.winner && s.winner.sell_name]);

  const requestApproval = () => {
    const problem = _v4ApprovalBindingProblem(approvalBinding, s);
    setApprovalBlockReason(problem);
    if (!problem) setApprovalOpen(true);
  };

  const onApprove = ({ userBuy, userSell }) => {
    const problem = _v4ApprovalBindingProblem(approvalBinding, s);
    if (problem || typeof send !== "function") {
      setApprovalBlockReason(problem || "승인 전송 연결을 사용할 수 없습니다.");
      return;
    }
    send({
      action: "final_approval",
      run_id: approvalBinding.run_id,
      current_gen: approvalBinding.current_gen,
      winner_gen: approvalBinding.winner_gen,
      user_buy: userBuy, user_sell: userSell,
      review_hash: approvalBinding.review_hash,
      evidence_hash: approvalBinding.evidence_hash,
      buy_code_hash: approvalBinding.buy_code_hash,
      sell_code_hash: approvalBinding.sell_code_hash,
    });
    setApprovalBlockReason("");
    setApprovalOpen(false);
  };

  const matchedGeneration = gens.find(g => Number(g.gen_no) === Number(s.current_gen)) || null;
  const hasFetchedCode = Boolean(strategyCodePayload && (strategyCodePayload.buy_code || strategyCodePayload.sell_code));
  const activeGeneration = streamedGeneration ? {
    buy_code: stream.buy_code_partial, sell_code: stream.sell_code_partial,
    buy_name: stream.buy_name, sell_name: stream.sell_name,
  } : hasFetchedCode ? strategyCodePayload : (matchedGeneration || s.best || s.winner || {});
  const activeGenerationSource = streamedGeneration ? "current_run.generation · demo streaming"
    : hasFetchedCode ? `GET /strategy_code · ${strategyCodeStatus}` : strategyCodeStatus === "loading" ? "GET /strategy_code · loading"
      : strategyCodeStatus.startsWith("error") ? strategyCodeStatus
        : matchedGeneration ? "generations metrics · code unavailable"
          : s.best ? "best metrics · code unavailable" : s.winner ? "winner metrics · code unavailable" : "empty";
  const evidence = _v4EvidenceState(s);
  const evidenceText = Array.isArray(evidence.value) ? evidence.value.join(" · ") : String(evidence.value);
  return (
    <section className="v4-research" aria-labelledby="v4-research-heading">
      <h2 id="v4-research-heading" className="v4-live-page-title">Research · 조건식 연구 관찰</h2>
      <ExportStatusBanner reply={lastReply} />
      <_V4WorkflowStrip state={s} situation={situation} />
      {!hasData && (s.status === "idle" || !s.status) && <_V4Onboarding onOpenSettings={typeof onOpenSettings === "function" ? onOpenSettings : () => {}} />}
      {!hasData && s.status && s.status !== "idle" && <div className={"v4-idle-strip v4-state-panel " + (s.status === "error" || s.status === "failed" ? "danger" : "pending")} role={s.status === "error" || s.status === "failed" ? "alert" : "status"}>연구 {s.status} · 세대 데이터 대기</div>}
      <div className={"v4-live-layout" + (drawerOpen ? " drawer-open" : "")}>
        <main className="v4-live-main">
          <div className="v4-graph-grid" aria-label="핵심 분석 그래프">
            <div className="panel v4-graph-card v4-graph-fitness">
              <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>Fitness 곡선 · graded score</div>
                <span className="mono">best {s.best && s.best.graded_score != null ? Number(s.best.graded_score).toFixed(2) : "—"} · gate {targetScore != null ? Number(targetScore).toFixed(2) : "—"}</span></div>
              <div className="v4-hero-primary"><V4HeroChart state={s} target={targetScore} /></div>
            </div>
            <ProfitChart state={s} targetPct={0} />
            <QualityTrendChart state={s} />
            <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
          </div>
          <_V4Stats state={s} />
          <section className="v4-process-board" aria-label="단일 프로세스 상황판">
            <div className="v4-process-tabs" role="tablist" aria-label="연구 단계">
              {situation.steps.map(step => <button type="button" role="tab" key={step.key}
                id={"v4-live-tab-" + step.key} aria-controls={"v4-live-panel-" + step.key}
                aria-selected={selectedStep === step.index} tabIndex={selectedStep === step.index ? 0 : -1}
                className={"v4-process-tab " + step.state} onClick={() => selectStep(step.index)}
                onKeyDown={event => onStepKeyDown(event, step.index)}>
                {V4_LIVE_STEP_LABELS[step.index]} <small>{step.state}</small>
              </button>)}
            </div>
            <div role="tabpanel" id={"v4-live-panel-" + V4_LIVE_STEP_KEYS[selectedStep]} aria-labelledby={"v4-live-tab-" + V4_LIVE_STEP_KEYS[selectedStep]} className="v4-step-panel">
              {selectedStep === 0 && <><PhaseTimeline state={s} /><PhaseDetailPanel state={s} wsStatus={wsStatus} onViewLatestCode={viewCode} /><ActiveStrategyPanel state={s} baseUrl={baseUrl} onViewCode={viewCode} /></>}
              {selectedStep === 1 && <><section className="panel v4-backtest-authority"><div className="panel-hd"><div className="panel-hd-title">Backtest · authoritative live fields</div><span className={"v4-data-state " + evidence.label}>{evidence.label}</span></div>
                <div className="panel-bd"><dl><div><dt>매수 조건식 · buy_code</dt><dd className="mono">{activeGeneration.buy_code || "empty"}</dd></div><div><dt>매도 조건식 · sell_code</dt><dd className="mono">{activeGeneration.sell_code || "empty"}</dd></div>
                  <div><dt>source / run_id / generation</dt><dd>{activeGenerationSource} · {runId || "legacy"} · {s.current_gen != null && Number(s.current_gen) >= 0 ? s.current_gen : "시작 전"}</dd></div>
                  <div><dt>engine_state / backtest_progress</dt><dd>{_v4EngineSummary(s.latest?.engine_state ?? s.engine_state)} · {_v4ProgressSummary(s.latest?.backtest_progress ?? s.backtest_progress)}</dd></div>
                  <div><dt>analysis evidence · {evidence.label}</dt><dd>{evidenceText}<small className="v4-evidence-source">source · {evidence.source}</small></dd></div></dl><_V5_2FieldSourceTable /></div></section><EnginePanel state={s} wsStatus={wsStatus} /></>}
              {selectedStep === 2 && <><ResearchCriteriaBanner state={s} baseUrl={baseUrl} /><EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} /></>}
              {selectedStep === 3 && <><AutopsyPanel state={s} wsStatus={wsStatus} /><HypothesisPanel state={s} /><FeedbackPanel state={s} /></>}
            </div>
          </section>
        </main>
        <div className="v4-drawer-control"><button type="button" className="v4-drawer-toggle" aria-expanded={drawerOpen} aria-controls="v4-live-drawer" onClick={() => setDrawerOpen(open => !open)}>상세 패널 {drawerOpen ? "접기" : "펼치기"}</button></div>
        <aside id="v4-live-drawer" className="v4-live-drawer" hidden={!drawerOpen} aria-label="연구 상세 drawer">
          <CurrentGenPanel state={s} /><V4LoopCycle state={s} />
          {merged ? <MergedBestWinnerCard best={s.best} winner={s.winner} onApprove={requestApproval} onViewCode={viewCode} /> : <><BestCard best={s.best} onViewCode={viewCode} /><WinnerCard winner={s.winner} onApprove={requestApproval} onViewCode={viewCode} /></>}
          {s.winner && approvalBlockReason && <p className="v4-research-error" role="alert">최종 승인 차단 · {approvalBlockReason}</p>}
          <_V4Fold storageKey="stom_v4_process" label="프로세스 상세"><ProcessFlowPanel state={s} /></_V4Fold>
          <_V4Fold storageKey="stom_v4_strategy" label="세대 이력"><GenerationsTable state={s} mddCap={mddCap} minDailyTrades={minDailyTrades} onViewCode={g => viewCode(g && g.gen_no != null ? g.gen_no : g)} onSelectDetail={genNo => setSelectedDetailGen(genNo)} /><BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} /><EvolutionGuiParityPanel baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} /></_V4Fold>
          <_V4Fold storageKey="stom_v4_analysis" label="진화 분석"><LineagePanel state={s} wsStatus={wsStatus} /><MetaPanel state={s} wsStatus={wsStatus} /><HoldoutPanel state={s} wsStatus={wsStatus} /></_V4Fold>
          <_V4Fold storageKey="stom_v4_config" label="설정 · 게이트 · 비용" defaultOpen={false}><ResearchGlossaryPanel /><ActiveConfigPanel state={s} /><CostPanel state={s} cap={50000} /><ConditionDiscoveryPanel state={s} wsStatus={wsStatus} /><PopulationPanel state={s} wsStatus={wsStatus} /></_V4Fold>
        </aside>
      </div>
      <ApprovalDialog winner={approvalOpen ? s.winner : null} onClose={() => setApprovalOpen(false)} onConfirm={onApprove} />
    </section>
  );
}

Object.assign(window, { V4ResearchLive, V4_LIVE_PHASE_STEP, v4LiveSituation, _v4EvidenceState });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4ResearchLive };
