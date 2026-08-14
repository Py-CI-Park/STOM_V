/* v4-research.jsx — v5.3.2 "Research Live" 스테이지 구동 단일 포커스 뷰 (4스테이지)
 *
 *   구조(위→아래): 통합 상황판[수평 파이프라인 벨트(구 원형 사이클+타임라인 흡수, N3)
 *   + 현재세대 패널 통합(N4) + KPI + 게이트 + 단계시간 미니바·차단 배지·로그]
 *   → 핵심 그래프 밴드(hasData 시, 3440 4열) → 스테이지 탭 4개(N6: 채점+부검 통합)
 *   → 현재 스테이지 단일 포커스 패널.
 *   배치 계약(N6): 백테 결과(파리티)는 백테스트 스테이지, 탐색 히트맵·엣지 분석은
 *   채점·부검 스테이지. ProcessFlowPanel 은 벨트·스테이지 탭과 3중 중복이라 제거(N7).
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel, AutopsyPanel, AutopsyFocusCard, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner } from "./panels.jsx";
import { HypothesisPanel } from "./hypothesis.jsx";
import { LoopAutonomyPanel } from "./loop-autonomy.jsx";
import { LoopStandingPanel } from "./loop-standing.jsx";
import { LoopStrategyLedgerPanel } from "./loop-strategy-ledger.jsx";
import { LoopPowerGaugePanel } from "./loop-power-gauge.jsx";
import { LoopResponseSurfacePanel } from "./loop-response-surface.jsx";
import { LoopConditionDiffPanel } from "./loop-condition-diff.jsx";
import { LoopTradePairsPanel } from "./loop-trade-pairs.jsx";
import { LoopResearchToolsPanel } from "./loop-research-tools.jsx";
import { GenerationsTable } from "./table.jsx";
import { EvolutionAnalysisPanel } from "./evolution-analysis.jsx";
import { ResearchImprovementCard } from "./research-improvement.jsx";
import { ResearchNextStepsCard } from "./research-next-steps.jsx";
import { ProfitChart, QualityTrendChart, EquityOverlayChart } from "./chart.jsx";
import { EnginePanel } from "./engine.jsx";
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
import { PhaseDetailPanel, phaseIndex } from "./phase-detail.jsx";
import { V4HeroChart } from "./v4-charts.jsx";
import { BtResultArea } from "./backtest-charts.jsx";
const { useEffect: useEffect_v4r, useState: useState_v4r } = React;

const _V4_APPROVAL_HASH_KEYS = ["review_hash", "evidence_hash", "buy_code_hash", "sell_code_hash"];

function _v4ApprovalBindingProblem(binding, state) {
  const winner = state && state.winner;
  if (!winner) return "우승 후보가 아직 확정되지 않았습니다.";
  if (!binding || typeof binding !== "object") return "동결 검토 근거를 확인하는 중입니다.";
  if (binding.available !== true) return `동결 검토 근거를 사용할 수 없습니다 (${String(binding.reason || "사유 미발행")}).`;
  const missing = ["run_id", "current_gen", "winner_gen", ..._V4_APPROVAL_HASH_KEYS]
    .filter(key => binding[key] === undefined || binding[key] === null || binding[key] === "");
  if (missing.length) return `승인 근거 필드가 누락되었습니다 (${missing.join(", ")}).`;
  const identity = binding.candidate_identity;
  if (!identity || typeof identity !== "object" || Array.isArray(identity)) {
    return "승인 후보 신원(candidate_identity)이 누락되었습니다.";
  }
  if (String(identity.run_id || "") !== String(binding.run_id)
      || Number(identity.gen_no) !== Number(binding.winner_gen)) {
    return "승인 후보 신원이 현재 승인 근거의 run·우승 세대와 일치하지 않습니다.";
  }
  if (binding.candidate_identity_hash !== undefined
      && !/^[0-9a-f]{64}$/.test(String(binding.candidate_identity_hash))) {
    return "승인 후보 신원 해시 형식이 올바르지 않습니다 (candidate_identity_hash).";
  }
  if (binding.run_id !== state.run_id || Number(binding.current_gen) !== Number(state.current_gen)
      || Number(binding.winner_gen) !== Number(winner.gen)
      || binding.winner_buy !== winner.buy_name || binding.winner_sell !== winner.sell_name) {
    return "현재 run·세대·우승 후보와 동결 승인 근거가 일치하지 않습니다.";
  }
  const invalidHash = _V4_APPROVAL_HASH_KEYS.find(key => !/^[0-9a-f]{64}$/.test(String(binding[key])));
  return invalidHash ? `승인 근거 해시 형식이 올바르지 않습니다 (${invalidHash}).` : "";
}
const _V4_RUN_STATUS = Object.freeze({
  idle: { stage: -1, engineLabel: "대기", engineTone: "idle" },
  running: { stage: null, engineLabel: "실행 중", engineTone: "run" },
  stopping: { stage: null, engineLabel: "정지 중", engineTone: "run" },
  complete: { stage: 3, engineLabel: "완료", engineTone: "complete" },
  error: { stage: -1, engineLabel: "오류", engineTone: "error" },
  blocked: { stage: -1, engineLabel: "차단", engineTone: "blocked" },
});

function _v4RunStatus(status, phase) {
  const rawStatus = status === "failed" ? "error" : status;
  const key = Object.prototype.hasOwnProperty.call(_V4_RUN_STATUS, rawStatus) ? rawStatus : "idle";
  const mapped = _V4_RUN_STATUS[key];
  const phaseIdx = phaseIndex(phase);
  return {
    key,
    stage: mapped.stage === null ? (phaseIdx >= 0 ? STAGE_FROM_PHASE[phaseIdx] : -1) : mapped.stage,
    engineLabel: mapped.engineLabel,
    engineTone: mapped.engineTone,
  };
}


// 접이식 섹션(app.jsx _EvoSection 패턴 — styles.css .evo-group 재사용, V4 전용 storage key)
function _V4Fold({ storageKey, label, children, defaultOpen = false, forceOpen = false }) {
  const [open, setOpen] = useState_v4r(() => {
    try { const v = window.localStorage.getItem(storageKey); return v === null ? defaultOpen : v === "1"; }
    catch (e) { return defaultOpen; }
  });
  const onToggle = (e) => {
    const o = e.currentTarget.open;
    setOpen(o);
    try { window.localStorage.setItem(storageKey, o ? "1" : "0"); } catch (e2) {}
  };
  const effOpen = forceOpen || open;
  return (
    <details className="evo-group" open={effOpen} onToggle={onToggle}>
      <summary className="evo-group-summary" aria-expanded={effOpen}>
        <div className="stom-section-label">{label}</div>
      </summary>
      <div className="evo-group-body">{children}</div>
    </details>
  );
}

// v5.3.9(검수): 온보딩 문구 전체 삭제 — 상단 시작/설정 버튼과 중복. 설정 버튼 1개만 유지.
function _V4Onboarding({ onOpenSettings }) {
  return (
    <div className="v6-onboarding-btnrow">
      <button className="btn primary lg" onClick={onOpenSettings}>▸ 조건식 AI 설정</button>
    </div>
  );
}

function _V4EngineGateBar({ state, targetScore, mddCap, minDailyTrades }) {
  const s = state || {};
  const prog = (s.latest || {}).backtest_progress || {};
  const runStatus = _v4RunStatus(s.status, s.latest && s.latest.phase);
  const pct = typeof prog.percent === "number" ? Math.max(0, Math.min(100, prog.percent)) : null;
  const curGen = typeof prog.current_gen === "number" ? prog.current_gen : (s.current_gen || 0);
  const maxGens = prog.max_generations || s.max_generations || 0;
  const engineLabel = runStatus.engineLabel;
  const fmt = (v, d = 2) => (v == null || v === "" ? "—" : Number(v).toFixed(d));
  return (
    <div className="v4-enggate-bar" aria-label="엔진·게이트 상황판">
      <div className="v4-eg-group">
        <span className="v4-eg-lbl">엔진</span>
        <span className={"v4-eg-chip " + runStatus.engineTone}>{engineLabel}</span>
        {pct != null && <span className="v4-eg-v">{pct.toFixed(0)}%</span>}
        <span className="v4-eg-v mono">gen {curGen >= 0 ? curGen : "—"}{maxGens ? "/" + maxGens : ""}</span>
      </div>
      <div className="v4-eg-group">
        <span className="v4-eg-lbl">게이트 · 현재 run 유효값</span>
        <span className="v4-eg-v mono" title="목표 적합도 점수">score ≥ {fmt(targetScore)}</span>
        <span className="v4-eg-v mono" title="MDD 상한">MDD ≤ {fmt(mddCap)}</span>
        <span className="v4-eg-v mono" title="최소 일거래 수">trades ≥ {minDailyTrades != null ? minDailyTrades : "—"}</span>
      </div>
    </div>
  );
}

function _V4Stats({ state, hideCurrent }) {
  const curRaw = Number(state.current_gen);
  const cur = Number.isFinite(curRaw) && curRaw >= 0 ? curRaw : "시작 전";
  const max = Number(state.max_generations) || 0;
  const best = state.best || null;
  const bestGen = best ? (state.generations || []).find(g => g.gen_no === best.gen) : null;
  const bestScore = best && best.graded_score != null ? Number(best.graded_score) : null;
  const mdd = bestGen && bestGen.mdd != null ? Number(bestGen.mdd) : null;
  const bestProfit = bestGen && bestGen.profit != null ? Number(bestGen.profit) : null;
  const bestTrades = bestGen && bestGen.trade_count != null ? Number(bestGen.trade_count) : null;
  const generationCount = Array.isArray(state.generations) ? state.generations.length : 0;
  const tokens = (state.cumulative && Number(state.cumulative.tokens)) || 0;
  const cost = (state.cumulative && state.cumulative.cost_or_count) ?? "—";
  return (
    <div className="v4-stats">
      {!hideCurrent && (
      <div className="v4-stat">
        <span className="v">{cur}<span className="dim"> / {max || "—"}</span></span>
        <span className="s">현재 세대 · {state.status || "idle"}</span>
      </div>
      )}
      <div className="v4-stat">
        <span className={"v" + (bestScore != null ? " pos" : "")}>{bestScore != null ? bestScore.toFixed(2) : "—"}</span>
        <span className="s">best fitness{best && best.gate_passed ? " · gate ✓" : ""}</span>
      </div>
      <div className="v4-stat">
        <span className={"v" + (mdd != null ? " neg" : "")}>{mdd != null ? "-" + Math.abs(mdd).toFixed(1) + "%" : "—"}</span>
        <span className="s">best MDD</span>
      </div>
      <div className="v4-stat">
        <span className={"v" + (bestProfit != null && bestProfit > 0 ? " pos" : bestProfit != null && bestProfit < 0 ? " neg" : "")}>{bestProfit != null ? (bestProfit / 10000).toFixed(0) + "만" : "—"}</span>
        <span className="s">best 손익</span>
      </div>
      <div className="v4-stat">
        <span className="v">{bestTrades != null ? bestTrades.toLocaleString("ko-KR") : "—"}</span>
        <span className="s">best 거래</span>
      </div>
      <div className="v4-stat">
        <span className="v">{tokens ? (tokens >= 1000 ? (tokens / 1000).toFixed(1) + "k" : tokens) : "—"}</span>
        <span className="s">token 사용량</span>
      </div>
      <div className="v4-stat">
        <span className="v">{String(cost)}</span>
        <span className="s">누적 cost</span>
      </div>
      <div className="v4-stat">
        <span className={"v" + (best && best.gate_passed ? " pos" : "")}>{best ? (best.gate_passed ? "PASS" : "검토") : "—"}</span>
        <span className="s">best gate</span>
      </div>
      <div className="v4-stat">
        <span className="v">{generationCount}<span className="dim"> / {max || "—"}</span></span>
        <span className="s">완료 세대</span>
      </div>
    </div>
  );
}

// v5.3.2 스테이지 정의 — 4탭(N6: 채점+부검 통합). phaseIndex(0생성·1백테·2채점·3부검)
//   → 스테이지 [0,1,2,2]. run 완료(complete)는 반복·성과(3).
const V6_STAGES = [
  { key: "generate", label: "생성", sub: "조건식 생성" },
  { key: "backtest", label: "백테스트", sub: "엔진 검증·결과" },
  { key: "score", label: "채점·부검", sub: "게이트·분석·실패" },
  { key: "iterate", label: "반복·성과", sub: "세대 요약" },
];
const STAGE_FROM_PHASE = [0, 1, 2, 2];

// v5.3.2 수평 파이프라인 벨트(N3) — 구 원형 사이클(V4LoopCycle)+PhaseTimeline 을 흡수한
//   8노드 가로 벨트. 활성 노드 pulse, 클릭 시 해당 스테이지 pin. 환류(↩)는 다음 세대로.
const _BELT_NODES = [
  { key: "seed", label: "시드", ai: false, stage: 0 },
  { key: "prompt", label: "프롬프트", ai: false, stage: 0 },
  { key: "gen", label: "AI 생성", ai: true, stage: 0 },
  { key: "gate", label: "게이트", ai: false, stage: 1 },
  { key: "bt", label: "공식 백테", ai: false, stage: 1 },
  { key: "score", label: "채점", ai: false, stage: 2 },
  { key: "autopsy", label: "부검", ai: true, stage: 2 },
  { key: "loop", label: "환류 ↩", ai: false, stage: 3 },
];
function _V6PipelineBelt({ liveStage, activeStage, onStagePin }) {
  return (
    <div className="v6-belt" role="group" aria-label="반복 세대 파이프라인(클릭 시 해당 단계 고정)">
      {_BELT_NODES.map((n, i) => {
        const live = liveStage === n.stage;
        const sel = activeStage === n.stage;
        return (
          <React.Fragment key={n.key}>
            {i > 0 && <span className={"v6-belt-arrow" + (live ? " lit" : "")} aria-hidden="true">→</span>}
            <button type="button"
                    className={"v6-belt-node" + (live ? " live" : "") + (sel ? " sel" : "") + (n.ai ? " ai" : "")}
                    title={(n.ai ? "AI 개입 · " : "코드 · ") + V6_STAGES[n.stage].label + " 단계로 이동"}
                    onClick={() => { if (typeof onStagePin === "function") onStagePin(n.stage); }}>
              <span className="v6-belt-badge">{n.ai ? "AI" : "⚙"}</span>
              <span className="v6-belt-label">{n.label}</span>
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );
}

// v5.4 L1 — 핵심 그래프 밴드(적합도·수익곡선·수익·품질) : 상황판 내부로 이동, 영어 제목 제거.
function _V6GraphBand({ state, baseUrl, wsStatus, runId, targetScore }) {
  const s = state || {};
  return (
    <div className="v6-graphs" aria-label="핵심 품질 지표 추이 4종">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>적합도 · 채점 점수</div>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
            best {s.best && s.best.graded_score != null ? Number(s.best.graded_score).toFixed(2) : "—"}
            {" · gate "}{targetScore != null ? Number(targetScore).toFixed(2) : "—"}
          </span>
        </div>
        <div className="v4-hero-primary v6-hero-compact">
          <V4HeroChart state={s} target={targetScore} />
        </div>
        <div className="v4-canvas-legend">
          <span><i style={{ borderTop: "2px solid var(--teal)" }}></i>채점 적합도</span>
          <span><i style={{ borderTop: "1px dashed var(--violet)" }}></i>게이트 {targetScore != null ? Number(targetScore).toFixed(2) : ""}</span>
          <span><span className="dot-v" style={{ background: "var(--violet)", border: "1.5px solid #fff", boxSizing: "border-box" }}></span>best</span>
          <span><span className="dot-v" style={{ background: "var(--amber)" }}></span>현재 세대</span>
        </div>
      </div>
      <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      <ProfitChart state={s} targetPct={0} />
      <QualityTrendChart state={s} />
    </div>
  );
}

// v5.3.2 통합 상황판 — 벨트 + [프로세스/게이트 | 현재세대(N4 통합) | KPI] + 미니바/배지/로그.
function _V6StatusBoard({ state, liveStage, activeStage, onStagePin, targetScore, mddCap, minDailyTrades, baseUrl, wsStatus, runId, hasData }) {
  const s = state || {};
  const latest = s.latest || {};
  const discovery = (s.page_data && s.page_data.condition_discovery) || {};
  const observability = discovery.research_observability || {};
  const ma = observability.mode_authority || {};
  const procLabel = ma.process || (discovery.current_process && discovery.current_process.code) || "process-research";
  const authKnown = ma.generation_allowed === true || ma.generation_allowed === false;
  const authLabel = ma.generation_allowed === true ? "research allowed"
    : ma.generation_allowed === false ? "review only" : "authority 대기";
  const authCls = ma.generation_allowed === true ? "ok" : ma.generation_allowed === false ? "warn" : "off";
  const nextMsg = (latest.message || latest.phase) || "대기";
  const timings = Object.entries(latest.step_timings || {}).filter(([, sec]) => typeof sec === "number" && sec >= 0);
  const maxT = timings.reduce((m, [, sec]) => Math.max(m, sec), 0) || 1;
  const blockerSource = observability.promotion_blockers || discovery.promotion_blockers || s.blockers || [];
  const rawBlockers = Array.isArray(blockerSource) ? blockerSource : (blockerSource.blockers || []);
  const blockers = Array.isArray(rawBlockers) ? rawBlockers : [];
  const logs = Array.isArray(latest.recent_logs) ? latest.recent_logs : [];
  const errorText = s.error || latest.error || "";
  return (
    <section className="v6-board" aria-labelledby="v6-board-heading">
      <h2 id="v6-board-heading" className="panel-hd-title">LIVE RESEARCH BOARD</h2>
      <_V6PipelineBelt liveStage={liveStage} activeStage={activeStage} onStagePin={onStagePin} />
      {/* v5.5.1 — 상황판 재설계: 넓은 빈 카드 대신 ①콤팩트 상태 칩 한 줄 ②[현재세대 | KPI 4열] */}
      <div className="v55-board-chips" aria-label="프로세스·권한·다음 행동·엔진·게이트 상태">
        <span className="v55-chip"><span className="k">process</span><b className="mono">{procLabel}</b></span>
        <span className={"v4-chip " + authCls} title={authKnown ? "mode_authority.generation_allowed" : "관찰성 발행 대기(폴백)"}>{authLabel}</span>
        <span className="v55-chip grow" title="다음 행동"><span className="k">다음 행동</span><b>{nextMsg}</b></span>
        <_V4EngineGateBar state={s} targetScore={targetScore} mddCap={mddCap} minDailyTrades={minDailyTrades} />
      </div>
      {/* v5.6 U2 — 현재세대+KPI 통합 단일 카드(중복 '현재 세대' 표기 제거) */}
      <div className="v55-board-main v56-unified">
        <div className="v6-board-curgen">
          <CurrentGenPanel state={s} />
        </div>
        <div className="v6-board-kpi">
          <_V4Stats state={s} hideCurrent={true} />
        </div>
      </div>
      <div className="v6-board-strip">
        <div className="v6-timing" aria-label="단계별 실제 시간" tabIndex="0">
          {timings.length ? timings.map(([step, sec]) => (
            <div key={step} className="v6-timing-item" title={`${step} ${sec.toFixed(1)}초`}>
              <span className="k mono">{step}</span>
              <span className="bar"><i style={{ width: Math.max(4, Math.round((sec / maxT) * 100)) + "%" }}></i></span>
              <span className="v mono">{sec.toFixed(1)}s</span>
            </div>
          )) : <span className="mono v6-dim">완료 단계 없음</span>}
        </div>
        <div className="v6-blockers" aria-label="차단 사유" tabIndex="0">
          {blockers.length
            ? blockers.map(b => <span key={String(b)} className="v4-chip warn" title="promotion blocker">{String(b)}</span>)
            : <span className="v4-chip ok">발행된 차단 사유 없음</span>}
        </div>
        <section className="v6-log-console" aria-label="현재 단계 상세 로그">
          <div className="v6-log-console-head">
            <b>현재 단계 상세 로그</b>
            <span className="mono">{latest.phase || latest.current_step || "대기"} · 최근 {Math.min(logs.length, 14)}건</span>
          </div>
          <div className="v6-log-list mono" role="log" aria-live="polite">
            {logs.length ? logs.slice(-14).map((line, index) => (
              <div key={index} className="v6-log-line">
                <span>{String(logs.length - Math.min(logs.length, 14) + index + 1).padStart(2, "0")}</span>
                <b>{String(line)}</b>
              </div>
            )) : <div className="v6-log-line"><span>—</span><b>다음 단계 로그를 기다리는 중입니다.</b></div>}
          </div>
        </section>
      </div>
      {hasData && <_V6GraphBand state={s} baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} targetScore={targetScore} />}
      {errorText && <p className="v4-research-error" role="alert">연구 요청 실패 · {String(errorText)}</p>}
    </section>
  );
}

function V4ResearchLive({ baseUrl, state, wsStatus, send, lastReply, onViewCode, onOpenSettings, targetScore, mddCap, minDailyTrades }) {
  const [approvalOpen, setApprovalOpen] = useState_v4r(false);
  const [approvalBinding, setApprovalBinding] = useState_v4r(null);
  const [approvalBlockReason, setApprovalBlockReason] = useState_v4r("동결 승인 근거를 확인하는 중입니다.");
  const [reviewContext, setReviewContext] = useState_v4r(null);
  const [selectedDetailGen, setSelectedDetailGen] = useState_v4r(null);
  // 스테이지 pin — 벨트/탭 클릭 시 고정, 해제 시 라이브 자동전환.
  const [stagePin, setStagePin] = useState_v4r(null);
  const [liveStageDensity, setLiveStageDensity] = useState_v4r(() => {
    try {
      const stored = window.localStorage.getItem("stom_v511_live_stage_density");
      return stored === "compact" ? "compact" : "comfortable";
    } catch (e) {
      return "comfortable";
    }
  });
  const s = state || {};
  const latest = s.latest || {};
  const runId = s.run_id || "";
  const gens = Array.isArray(s.generations) ? s.generations : [];
  const hasData = gens.length > 0;
  const knownGenNos = gens.map(g => Number(g.gen_no)).filter(Number.isFinite);
  const latestGen = knownGenNos.length ? Math.max(...knownGenNos) : null;
  const selectedGen = [selectedDetailGen, s.best && s.best.gen, latestGen]
    .map(value => value == null ? null : Number(value))
    .find(value => Number.isFinite(value) && knownGenNos.includes(value));
  const isDemo = wsStatus === "demo";
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;
  const viewCode = typeof onViewCode === "function" ? onViewCode : () => {};
  const runStatus = _v4RunStatus(s.status, latest.phase);
  const liveStage = runStatus.stage;
  // v5.6 U6 — 초기 스테이지: 연구 중이면 해당 단계, 아니면 항상 1. 생성.
  const activeStage = stagePin != null ? stagePin : (liveStage >= 0 ? liveStage : 0);
  const onStagePin = (i) => setStagePin(prev => (prev === i ? null : i));
  const onStageKey = (e) => {
    const n = V6_STAGES.length;
    if (e.key === "ArrowRight") { e.preventDefault(); setStagePin(((activeStage + 1) % n)); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); setStagePin(((activeStage - 1 + n) % n)); }
    else if (e.key === "Home") { e.preventDefault(); setStagePin(0); }
    else if (e.key === "End") { e.preventDefault(); setStagePin(n - 1); }
  };
  useEffect_v4r(() => {
    try { window.localStorage.setItem("stom_v511_live_stage_density", liveStageDensity); } catch (e) {}
  }, [liveStageDensity]);

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
      candidate_identity: approvalBinding.candidate_identity,
    });
    setApprovalBlockReason("");
    setApprovalOpen(false);
  };

  return (
    <section className={"v4-research v6-live v6-live-density-" + liveStageDensity} aria-labelledby="v4-research-heading">
      <h2 id="v4-research-heading" className="panel-hd-title">Research · 조건식 연구 관찰</h2>
      <ExportStatusBanner reply={lastReply} />

      {/* ===== 통합 상황판(벨트 + 현재세대 + KPI + 게이트) ===== */}
      <_V6StatusBoard state={s} liveStage={liveStage} activeStage={activeStage} onStagePin={onStagePin}
                      targetScore={targetScore} mddCap={mddCap} minDailyTrades={minDailyTrades}
                      baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} hasData={hasData} />

      {!hasData && (s.status === "idle" || !s.status) && (
        <_V4Onboarding onOpenSettings={typeof onOpenSettings === "function" ? onOpenSettings : () => {}} />
      )}
      {!hasData && s.status && s.status !== "idle" && (
        <div className={"v4-idle-strip v4-state-panel " + (s.status === "error" || s.status === "failed" ? "danger" : "pending")} role={s.status === "error" || s.status === "failed" ? "alert" : "status"}>
          {s.status === "error" || s.status === "failed"
            ? `연구 요청 실패 · ${String(s.error || (s.latest && s.latest.error) || "서버 로그를 확인하세요")}`
            : `연구 ${s.status === "blocked" ? "차단" : "진행"} · 현재 단계 ${(s.latest && s.latest.current_step) ?? "발행 대기"} · 세대 데이터 대기`}
        </div>
      )}
      {runStatus.key === "complete" && runId && selectedGen != null && (
        <div className="v511-result-ready" role="status">
          <span>완료된 세대 g{selectedGen}의 결과 분석을 다시 열 수 있습니다.</span>
          <button className="btn primary sm" type="button" onClick={() => setStagePin(1)}>
            결과 분석 열기
          </button>
        </div>
      )}


      {/* ===== 스테이지 탭(4) — 라이브 자동전환·pin ===== */}
      <div className="v6-stage-tabs" role="group" aria-label="연구 프로세스 단계">
        <span className="v6-stage-tablist" role="tablist" aria-label="연구 프로세스 단계" onKeyDown={onStageKey}>
          {V6_STAGES.map((st, i) => (
            <button key={st.key} type="button" role="tab" id={"v6-stage-tab-" + st.key}
                    aria-selected={activeStage === i} aria-controls="v6-stage-panel"
                    tabIndex={activeStage === i ? 0 : -1}
                    className={"v6-stage-tab" + (activeStage === i ? " active" : "") + (liveStage === i ? " live" : "")}
                    onClick={() => onStagePin(i)}
                    title={st.sub + (liveStage === i ? " · 진행 중" : "")}>
              <b>{i + 1}. {st.label}</b>
              <span>{st.sub}</span>
              {liveStage === i && <i className="v6-live-dot" aria-label="진행 중"></i>}
            </button>
          ))}
        </span>
        <span className="v6-stage-density" role="group" aria-label="Live 단계 밀도">
          <span>단계 밀도</span>
          <button className={"btn ghost sm" + (liveStageDensity === "comfortable" ? " active" : "")}
                  type="button" aria-pressed={liveStageDensity === "comfortable"}
                  onClick={() => setLiveStageDensity("comfortable")}>여유</button>
          <button className={"btn ghost sm" + (liveStageDensity === "compact" ? " active" : "")}
                  type="button" aria-pressed={liveStageDensity === "compact"}
                  onClick={() => setLiveStageDensity("compact")}>압축</button>
        </span>
        {stagePin != null && (
          <button className="btn ghost sm v5-pin-reset" onClick={() => setStagePin(null)}>
            단계 고정 해제 · 라이브 따라가기
          </button>
        )}
      </div>

      {/* ===== 현재 스테이지 단일 포커스 패널 ===== */}
      <div id="v6-stage-panel" className="v6-stage-panel v59-stage-layout" role="tabpanel"
           aria-labelledby={"v6-stage-tab-" + V6_STAGES[activeStage].key} aria-live="polite">
        {activeStage === 0 && (
          <div className="v6-stage-grid v59-matrix v59-stage-generate">
            {/* v5.11.2 — 왜 이렇게 만드는가(부검 근거) → 무엇을 기대하는가(가정) →
                무엇을 만들었는가(조건식) → 어떤 규칙을 지키는가(거버넌스) 순서로 읽힌다. */}
            <AutopsyFocusCard state={s} onOpenAutopsy={() => onStagePin(2)} />
            <HypothesisPanel state={s} />
            <ActiveStrategyPanel state={s} baseUrl={baseUrl} onViewCode={viewCode} />
            <ConditionDiscoveryPanel state={s} wsStatus={wsStatus} />
          </div>
        )}
        {activeStage === 1 && (
          <div className="v6-stage-grid v59-matrix v59-stage-backtest">
            {/* v5.5.1 F3' — 매트릭스: 1행[페이즈 상세|엔진] → 2행[BT 상세(2칸)|패리티 fold(2칸)].
                전폭 독점 금지(다른 결과 가림) + 백테스트 탭 상세 분석 딥링크. */}
            <div className="v56-cell">
              <PhaseDetailPanel state={s} wsStatus={wsStatus} onViewLatestCode={viewCode} pinnedIdx={1} />
            </div>
            <div className="v56-cell v6-engine-xl">
              <EnginePanel state={s} wsStatus={wsStatus} />
            </div>
            {/* v5.11.2 — 결과 소유자는 이 섹션 하나다. 아래에 있던 '결과 출처 · 상태' 중복
                블록은 같은 사실을 두 번 말할 뿐이라 제거하고, 실제로 쓰이는 이동 버튼만
                헤더로 올렸다(구 버튼의 링크 /ui/evolution/backtest 는 404 였다). */}
            <section className="v59-live-result-analysis v54-span-all" aria-labelledby="v59-live-result-heading">
              <div className="v59-live-result-head">
                <div>
                  <h3 id="v59-live-result-heading" className="stom-section-label">전체 결과 분석 · Backtest와 동일한 정본</h3>
                  <p className="v59-section-intro">
                    선택·best·최신 순서로 유효한 세대를 연결해 자본곡선, 분포, 위험 및 거래 분석을 Backtest 소유 컴포넌트로 재사용합니다.
                    {runId && selectedGen != null
                      ? ` 현재 연결: run ${runId} · g${selectedGen}`
                      : " 유효한 run·세대를 기다리는 중입니다."}
                  </p>
                </div>
                <button className="btn ghost sm"
                        title="선택 세대를 백테스트 탭의 정본 결과 분석으로 연다"
                        disabled={!runId || selectedGen == null}
                        onClick={() => {
                          if (!runId || selectedGen == null) return;
                          try {
                            const detail = { run_id: runId, gen_no: selectedGen };
                            window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
                            window.localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
                          } catch (e) {}
                          window.location.href = "/?tab=backtest";
                        }}>
                  ⇲ 백테스트 탭에서 열기
                </button>
              </div>
              {runId && selectedGen != null ? (
                <BtResultArea baseUrl={baseUrl} isDemo={isDemo} jobId={null}
                              evoSource={{ run_id: runId, gen_no: selectedGen }} />
              ) : (
                <div className="v59-result-pending">유효한 run과 세대가 발행되면 전체 결과 분석이 표시됩니다.</div>
              )}
            </section>
          </div>
        )}
        {activeStage === 2 && (
          <div className="v6-stage-grid v59-matrix v59-stage-score">
            {/* 게이트·부검·계보·메타·홀드아웃·피드백과 세대 이력은 보존한다. */}
            <div className="v54-span-all">
              <_V4Fold storageKey="stom_v6_gate" label="게이트·채점 기준 · 현재 run 유효값 (클릭 상세)">
                <div className="v55-gatefold-grid">
                  <ResearchCriteriaBanner state={s} baseUrl={baseUrl} />
                  <ActiveConfigPanel state={s} />
                  <CostPanel state={s} cap={50000} />
                  {/* v5.6.1 — 용어집은 '용어' 탭으로 이동(사장님 지시) */}
                </div>
              </_V4Fold>
            </div>
            <AutopsyPanel state={s} wsStatus={wsStatus} />
            <LineagePanel state={s} wsStatus={wsStatus} />
            <MetaPanel state={s} wsStatus={wsStatus} />
            <HoldoutPanel state={s} wsStatus={wsStatus} />
            <FeedbackPanel state={s} />
            <div className="v54-span-all">
              <GenerationsTable state={s} mddCap={mddCap} minDailyTrades={minDailyTrades}
                                onViewCode={(g) => viewCode(g && g.gen_no != null ? g.gen_no : g)}
                                onSelectDetail={(genNo) => {
                                  // v5.13.1(D1 재수정) — 세대표는 스테이지 2, 결과 분석 섹션은
                                  //   스테이지 1 에 있어 클릭 효과가 화면 밖 스테이지에서 일어났다
                                  //   ("눌러도 반응 없음"의 v4 셸 실체). 세대를 고정하고 스테이지
                                  //   1 로 전환한 뒤 결과 섹션으로 스크롤한다.
                                  setSelectedDetailGen(genNo);
                                  setStagePin(1);
                                  try {
                                    setTimeout(() => {
                                      const el = document.getElementById("v59-live-result-heading");
                                      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                                    }, 80);
                                  } catch (e) {}
                                }} />
            </div>
          </div>
        )}
        {activeStage === 3 && (
          <div className="v6-stage-grid v59-matrix v59-stage-iterate">
            {merged ? (
              <MergedBestWinnerCard best={s.best} winner={s.winner}
                                    onApprove={requestApproval} onViewCode={viewCode} />
            ) : (
              <>
                <BestCard best={s.best} onViewCode={viewCode} />
                <WinnerCard winner={s.winner} onApprove={requestApproval} onViewCode={viewCode} />
              </>
            )}
            {s.winner && approvalBlockReason && <p className="v4-research-error" role="alert">최종 승인 차단 · {approvalBlockReason}</p>}
            <PopulationPanel state={s} wsStatus={wsStatus} />
            {/* v5.11.2 — "지금 세대가 어떤가"가 아니라 "세대를 거듭하며 좋아지고 있나"에 답한다. */}
            <div className="v54-span-all">
              <ResearchImprovementCard state={s} baseUrl={baseUrl} runId={runId} />
            </div>
            {/* 관찰(추이)에서 끝내지 않고 "그래서 무엇을 바꿀까"까지 이어 붙인다. */}
            <div className="v54-span-all">
              <ResearchNextStepsCard state={s} />
            </div>
            <section className="v6-stage-lab v54-span-all" aria-label="세대 진화 분석(전폭)">
              <h3 className="stom-section-label">세대 진화 분석 · 개별 그래프</h3>
              <EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
            </section>
            {/* 페이지 26 — 자율 루프 관제: 가정·판정·수정 예산 (사람 승인 없이 도는 루프의 관측면) */}
            <section className="v6-stage-lab v54-span-all" aria-label="자율 루프 관제(페이지 26)">
              <h3 className="stom-section-label">자율 루프 관제 · 가정 판정과 수정 예산</h3>
              <LoopAutonomyPanel baseUrl={baseUrl} />
            </section>
            {/* 페이지 29 — 상설화: 백필·재검증 계획 (실행 버튼 없음, 홀드아웃은 잠김) */}
            <section className="v6-stage-lab v54-span-all" aria-label="상설화 현황(페이지 29)">
              <h3 className="stom-section-label">상설화 · 백필과 상설 재검증</h3>
              <LoopStandingPanel baseUrl={baseUrl} />
            </section>
            {/* 페이지 30 — 조건식 성과 원장: 지금까지 만든 후보 전부의 엔진 실측 누적 */}
            <section className="v6-stage-lab v54-span-all" aria-label="조건식 성과 원장(페이지 30)">
              <h3 className="stom-section-label">조건식 성과 원장 · 챔피언 대비 누적</h3>
              <LoopStrategyLedgerPanel baseUrl={baseUrl} reviewContext={reviewContext}
                                       onSelectContext={setReviewContext} />
            </section>
            {/* 페이지 31 — 표본·검정력: 판정을 믿을 만한가, 못 믿겠으면 며칠 더 재야 하나 */}
            <section className="v6-stage-lab v54-span-all" aria-label="표본·검정력 계기판(페이지 31)">
              <h3 className="stom-section-label">표본·검정력 · 지금 확정할 수 있는 것</h3>
              <LoopPowerGaugePanel baseUrl={baseUrl} reviewContext={reviewContext} />
            </section>
            {/* 페이지 32 — 파라미터 응답면: 그 값을 채택해도 표본 밖에서 살아남는가 */}
            <section className="v6-stage-lab v54-span-all" aria-label="파라미터 응답면(페이지 32)">
              <h3 className="stom-section-label">파라미터 응답면 · 고원인가 절벽인가</h3>
              <LoopResponseSurfacePanel baseUrl={baseUrl} reviewContext={reviewContext} />
            </section>
            {/* 페이지 33 — 조건식 비교: 두 조건식이 정확히 무엇이 다른가 */}
            <section className="v6-stage-lab v54-span-all" aria-label="조건식 비교 뷰어(페이지 33)">
              <h3 className="stom-section-label">조건식 비교 · 절 단위 diff</h3>
              <LoopConditionDiffPanel baseUrl={baseUrl} reviewContext={reviewContext} />
            </section>
            {/* 페이지 34 — 거래 짝: 짝지은 검정의 숫자 뒤에 있는 개별 거래 */}
            <section className="v6-stage-lab v54-span-all" aria-label="거래 짝 뷰어(페이지 34)">
              <h3 className="stom-section-label">거래 짝 · 왜 그런지 직접 본다</h3>
              <LoopTradePairsPanel baseUrl={baseUrl} reviewContext={reviewContext} />
            </section>
            {/* 오프라인 안전 확률 연구: 수동 진단/제안 전용. OOS·채택·내보내기 권한 없음. */}
            <section className="v6-stage-lab v54-span-all" aria-label="확률 연구 도구">
              <h3 className="stom-section-label">확률 연구 도구 · 수동 진단/제안</h3>
              <LoopResearchToolsPanel baseUrl={baseUrl} />
            </section>
          </div>
        )}
      </div>

      {/* Human approval gate — 연구 확인과 분리된 명시적 승인(운영 export) */}
      <ApprovalDialog winner={approvalOpen ? s.winner : null}
                      onClose={() => setApprovalOpen(false)} onConfirm={onApprove} />
    </section>
  );
}

Object.assign(window, { V4ResearchLive });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4ResearchLive };
