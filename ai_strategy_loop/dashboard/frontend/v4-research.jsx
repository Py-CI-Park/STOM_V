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
const { useState: useState_v4r } = React;

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

// workflow + authority 스트립: PhaseTimeline(정본) + process/authority 칩 + 다음 행동
function _V4WorkflowStrip({ state }) {
  const discovery = (state.page_data && state.page_data.condition_discovery) || {};
  const ma = (discovery.research_observability && discovery.research_observability.mode_authority) || {};
  const procLabel = ma.process || (discovery.current_process && discovery.current_process.code) || "process-research";
  const authKnown = ma.generation_allowed === true || ma.generation_allowed === false;
  const authLabel = ma.generation_allowed === true ? "research allowed"
    : ma.generation_allowed === false ? "review only" : "authority 대기";
  const authCls = ma.generation_allowed === true ? "ok" : ma.generation_allowed === false ? "warn" : "off";
  const nextMsg = (state.latest && (state.latest.message || state.latest.phase)) || "대기";
  return (
    <div className="v4-wfwrap">
      <PhaseTimeline state={state} />
      <div className="v4-wf-next">
        <div><span className="k">process</span><b className="mono" style={{ color: "var(--ink-0)" }}>{procLabel}</b></div>
        <span className={"v4-chip " + authCls} title={authKnown ? "mode_authority.generation_allowed" : "관찰성 발행 대기(폴백)"}>{authLabel}</span>
        <div><span className="k">다음 행동</span><b>{nextMsg}</b></div>
      </div>
    </div>
  );
}

function _V4Stats({ state }) {
  const curRaw = Number(state.current_gen);
  const cur = Number.isFinite(curRaw) && curRaw >= 0 ? curRaw : "—";
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

function V4ResearchLive({ baseUrl, state, wsStatus, send, lastReply, onViewCode, targetScore, mddCap, minDailyTrades }) {
  const [approvalOpen, setApprovalOpen] = useState_v4r(false);
  const [selectedDetailGen, setSelectedDetailGen] = useState_v4r(null);
  const s = state || {};
  const runId = s.run_id || "";
  const gens = Array.isArray(s.generations) ? s.generations : [];
  const hasData = gens.length > 0;
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;
  const viewCode = typeof onViewCode === "function" ? onViewCode : () => {};

  const onApprove = ({ userBuy, userSell }) => {
    if (!s.winner || typeof send !== "function") { setApprovalOpen(false); return; }
    send({
      action: "final_approval",
      buy_name: s.winner.buy_name, sell_name: s.winner.sell_name,
      user_buy: userBuy, user_sell: userSell,
    });
    setApprovalOpen(false);
  };

  return (
    <div className="v4-research">
      <ExportStatusBanner reply={lastReply} />
      <_V4WorkflowStrip state={s} />
      {!hasData && (
        <div className="v4-idle-strip">
          연구 대기 · 세대 데이터 없음 — 상단 <b style={{ color: "var(--ink-0)" }}>▸ 설정·시작</b>으로 조건식 AI 루프를 시작하면 아래가 실시간으로 채워집니다.
        </div>
      )}

      <div className="v4-rlive">
        {/* ===== HERO 컬럼 ===== */}
        <div className="v4-hero-col">
          <div className="panel">
            <div className="panel-hd">
              <div className="panel-hd-title"><span className="dot"></span>Fitness 곡선 · graded score</div>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
                best {s.best && s.best.graded_score != null ? Number(s.best.graded_score).toFixed(2) : "—"}
                {" · gate "}{targetScore != null ? Number(targetScore).toFixed(2) : "—"}
                {" · gen "}{s.current_gen || 0}
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

          <_V4Stats state={s} />

          <div className="v4-two">
            <ProfitChart state={s} targetPct={0} />
            <QualityTrendChart state={s} />
          </div>
          <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
          <EnginePanel state={s} wsStatus={wsStatus} />

          <_V4Fold storageKey="stom_v4_live_detail" label="Live 상세 · 단계 스트리밍">
            <PhaseDetailPanel state={s} wsStatus={wsStatus} onViewLatestCode={viewCode} />
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
          {merged ? (
            <MergedBestWinnerCard best={s.best} winner={s.winner}
                                  onApprove={() => setApprovalOpen(true)} onViewCode={viewCode} />
          ) : (
            <>
              <BestCard best={s.best} onViewCode={viewCode} />
              <WinnerCard winner={s.winner} onApprove={() => setApprovalOpen(true)} onViewCode={viewCode} />
            </>
          )}
          {/* wt-dev 연구 파이프라인 관찰성: Research Pack/Branch Tree · Candidate Pack ·
              Prompt Receipts · Promotion Blockers (advisory-only, 대기/폴백 내장) */}
          <ConditionDiscoveryPanel state={s} wsStatus={wsStatus} />
          <PopulationPanel state={s} wsStatus={wsStatus} />
        </aside>
      </div>

      {/* Human approval gate — 연구 확인과 분리된 명시적 승인(운영 export) */}
      <ApprovalDialog winner={approvalOpen ? s.winner : null}
                      onClose={() => setApprovalOpen(false)} onConfirm={onApprove} />
    </div>
  );
}

Object.assign(window, { V4ResearchLive });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4ResearchLive };
