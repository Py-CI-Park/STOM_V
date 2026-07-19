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
import { EnginePanel } from "./engine.jsx";
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
import { PhaseTimeline, PhaseDetailPanel, ProcessFlowPanel } from "./phase-detail.jsx";
import { V4HeroChart } from "./v4-charts.jsx";
import { V4LoopCycle } from "./v4-loop-cycle.jsx";
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
  if (binding.run_id !== state.run_id || Number(binding.current_gen) !== Number(state.current_gen)
      || Number(binding.winner_gen) !== Number(winner.gen)
      || binding.winner_buy !== winner.buy_name || binding.winner_sell !== winner.sell_name) {
    return "현재 run·세대·우승 후보와 동결 승인 근거가 일치하지 않습니다.";
  }
  const invalidHash = _V4_APPROVAL_HASH_KEYS.find(key => !/^[0-9a-f]{64}$/.test(String(binding[key])));
  return invalidHash ? `승인 근거 해시 형식이 올바르지 않습니다 (${invalidHash}).` : "";
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

// workflow + authority 스트립: PhaseTimeline(정본) + process/authority 칩 + 다음 행동
function _V4WorkflowStrip({ state, pinnedIdx = null, onStepClick = null }) {
  const discovery = (state.page_data && state.page_data.condition_discovery) || {};
  const observability = discovery.research_observability || {};
  const ma = observability.mode_authority || {};
  const latest = state.latest || {};
  const procLabel = ma.process || (discovery.current_process && discovery.current_process.code) || "process-research";
  const authKnown = ma.generation_allowed === true || ma.generation_allowed === false;
  const authLabel = ma.generation_allowed === true ? "research allowed"
    : ma.generation_allowed === false ? "review only" : "authority 대기";
  const authCls = ma.generation_allowed === true ? "ok" : ma.generation_allowed === false ? "warn" : "off";
  const nextMsg = (state.latest && (state.latest.message || state.latest.phase)) || "대기";
  const genLabel = state.current_gen != null && Number.isFinite(Number(state.current_gen)) && Number(state.current_gen) >= 0 ? String(state.current_gen) : "시작 전";
  const stepLabel = latest.current_step != null && Number.isFinite(Number(latest.current_step)) && Number(latest.current_step) >= 0 ? String(latest.current_step) : "발행 대기";
  const timingText = Object.entries(latest.step_timings || {}).filter(([, seconds]) => typeof seconds === "number" && seconds >= 0)
    .map(([step, seconds]) => `${step} ${seconds.toFixed(1)}초`).join(" · ") || "완료 단계 없음";
  const logs = Array.isArray(latest.recent_logs) ? latest.recent_logs : [];
  const lastLog = logs.length ? logs[logs.length - 1] : "로그 대기";
  const blockerSource = observability.promotion_blockers || discovery.promotion_blockers || state.blockers || [];
  const rawBlockers = Array.isArray(blockerSource) ? blockerSource : (blockerSource.blockers || []);
  const blockerText = Array.isArray(rawBlockers) && rawBlockers.length ? rawBlockers.join(" · ") : "발행된 차단 사유 없음";
  const errorText = state.error || latest.error || "";
  return (
    <section className="v4-wfwrap v4-research-evidence" aria-labelledby="v4-research-evidence-heading">
      <h2 id="v4-research-evidence-heading" className="panel-hd-title">실시간 연구 근거</h2>
      <PhaseTimeline state={state} pinnedIdx={pinnedIdx} onStepClick={onStepClick} />
      <div className="v4-wf-next">
        <div><span className="k">process</span><b className="mono" style={{ color: "var(--ink-0)" }}>{procLabel}</b></div>
        <span className={"v4-chip " + authCls} title={authKnown ? "mode_authority.generation_allowed" : "관찰성 발행 대기(폴백)"}>{authLabel}</span>
        <div><span className="k">다음 행동</span><b>{nextMsg}</b></div>
      </div>
      <p className="v4-research-live-summary" role="status" aria-live="polite">세대 {genLabel} · 현재 단계 {stepLabel} · {state.status || "idle"}</p>
      {errorText && <p className="v4-research-error" role="alert">연구 요청 실패 · {String(errorText)}</p>}
      <dl className="v4-research-evidence-grid"><div><dt>단계별 실제 시간</dt><dd>{timingText}</dd></div>
        <div><dt>차단 사유</dt><dd>{blockerText}</dd></div>
        <div><dt>최신 로그</dt><dd className="mono">{String(lastLog)}</dd></div></dl>
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
  // V5.1: 단계 상세 고정(pin) — 클릭 시 해당 단계 뷰 고정, 재클릭/리셋 시 라이브 자동전환 복귀.
  const [pinnedIdx, setPinnedIdx] = useState_v4r(null);
  const onStepPin = (i) => setPinnedIdx(prev => (prev === i ? null : i));
  const s = state || {};
  const runId = s.run_id || "";
  const gens = Array.isArray(s.generations) ? s.generations : [];
  const hasData = gens.length > 0;
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;
  const viewCode = typeof onViewCode === "function" ? onViewCode : () => {};

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

  return (
    <section className="v4-research" aria-labelledby="v4-research-heading">
      <h2 id="v4-research-heading" className="panel-hd-title">Research · 조건식 연구 관찰</h2>
      <ExportStatusBanner reply={lastReply} />
      <_V4WorkflowStrip state={s} pinnedIdx={pinnedIdx} onStepClick={onStepPin} />
      {pinnedIdx != null && (
        <button className="btn ghost sm v5-pin-reset" onClick={() => setPinnedIdx(null)}>
          단계 고정 해제 · 라이브 따라가기
        </button>
      )}
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

      <div className="v4-rlive">
        {/* ===== HERO 컬럼 ===== */}
        <div className="v4-hero-col">
          {/* V5.0 Live 밀도: KPI 바 상단 + 핵심 그래프 2×2 그리드(세로 스택 해체) */}
          <_V4Stats state={s} />
          <div className="v5-live-grid">
            <div className="panel">
              <div className="panel-hd">
                <div className="panel-hd-title"><span className="dot"></span>Fitness 곡선 · graded score</div>
                <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
                  best {s.best && s.best.graded_score != null ? Number(s.best.graded_score).toFixed(2) : "—"}
                  {" · gate "}{targetScore != null ? Number(targetScore).toFixed(2) : "—"}
                  {" · gen "}{s.current_gen != null && Number.isFinite(Number(s.current_gen)) && Number(s.current_gen) >= 0 ? Number(s.current_gen) : "시작 전"}
                </span>
              </div>
              <div className="v4-hero-primary">
                <V4HeroChart state={s} target={targetScore} />
              </div>
              <div className="v4-canvas-legend">
                <span><i style={{ borderTop: "2px solid var(--teal)" }}></i>graded fitness</span>
                <span><i style={{ borderTop: "1px dashed var(--violet)" }}></i>gate {targetScore != null ? Number(targetScore).toFixed(2) : ""}</span>
                <span><span className="dot-v" style={{ background: "var(--violet)", border: "1.5px solid #fff", boxSizing: "border-box" }}></span>best</span>
                <span><span className="dot-v" style={{ background: "var(--amber)" }}></span>현재 세대</span>
              </div>
            </div>
            <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
            <ProfitChart state={s} targetPct={0} />
            <QualityTrendChart state={s} />
          </div>
          <EnginePanel state={s} wsStatus={wsStatus} />

          <_V4Fold storageKey="stom_v4_live_detail" label={"Live 상세 · 단계 스트리밍" + (pinnedIdx != null ? " · 단계 고정됨" : "")} forceOpen={pinnedIdx != null}>
            <PhaseDetailPanel state={s} wsStatus={wsStatus} onViewLatestCode={viewCode} pinnedIdx={pinnedIdx} />
            <ActiveStrategyPanel state={s} baseUrl={baseUrl} onViewCode={viewCode} />
          </_V4Fold>
          <_V4Fold storageKey="stom_v4_process" label="프로세스 · process selector (research vs review 권한)">
            <ProcessFlowPanel state={s} />
          </_V4Fold>
          <_V4Fold storageKey="stom_v4_strategy" label="Strategy / Prompt · 세대 이력">
            <GenerationsTable state={s} mddCap={mddCap} minDailyTrades={minDailyTrades}
                              onViewCode={(g) => viewCode(g && g.gen_no != null ? g.gen_no : g)}
                              onSelectDetail={(genNo) => setSelectedDetailGen(genNo)} />
            <BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} />
            <EvolutionGuiParityPanel baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} />
          </_V4Fold>
          <_V4Fold storageKey="stom_v4_analytics" label="Generation Analytics · 세대 분석">
            <EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
          </_V4Fold>
          <_V4Fold storageKey="stom_v4_analysis" label="진화 분석 · 가정/부검/계보/홀드아웃">
            <HypothesisPanel state={s} />
            <AutopsyPanel state={s} wsStatus={wsStatus} />
            <LineagePanel state={s} wsStatus={wsStatus} />
            <MetaPanel state={s} wsStatus={wsStatus} />
            <HoldoutPanel state={s} wsStatus={wsStatus} />
            <FeedbackPanel state={s} />
          </_V4Fold>
          <_V4Fold storageKey="stom_v4_config" label="설정 · 게이트 · 비용" defaultOpen={false}>
            <ResearchCriteriaBanner state={s} baseUrl={baseUrl} />
            <ResearchGlossaryPanel />
            <ActiveConfigPanel state={s} />
            <CostPanel state={s} cap={50000} />
          </_V4Fold>
        </div>

        {/* ===== 관찰성 rail ===== */}
        <aside className="v4-side-col">
          <CurrentGenPanel state={s} />
          <V4LoopCycle state={s} />
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
          {/* wt-dev 연구 파이프라인 관찰성: Research Pack/Branch Tree · Candidate Pack ·
              Prompt Receipts · Promotion Blockers (advisory-only, 대기/폴백 내장) */}
          <ConditionDiscoveryPanel state={s} wsStatus={wsStatus} />
          <PopulationPanel state={s} wsStatus={wsStatus} />
        </aside>
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
