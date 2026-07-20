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
import { CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner } from "./panels.jsx";
import { HypothesisPanel } from "./hypothesis.jsx";
import { GenerationsTable } from "./table.jsx";
import { EvolutionAnalysisPanel } from "./evolution-analysis.jsx";
import { EvolutionGuiParityPanel } from "./evolution-gui-parity-panel.jsx";
import { ResearchGlossaryPanel } from "./glossary.jsx";
import { ProfitChart, QualityTrendChart, EquityOverlayChart, BacktestDetailChart } from "./chart.jsx";
import { EnginePanel } from "./engine.jsx";
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
import { PhaseDetailPanel, phaseIndex } from "./phase-detail.jsx";
import { V4HeroChart } from "./v4-charts.jsx";
import { ResearchLabPanel } from "./research-lab.jsx";
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
  const running = s.status === "running" || s.status === "stopping";
  const pct = typeof prog.percent === "number" ? Math.max(0, Math.min(100, prog.percent)) : null;
  const curGen = typeof prog.current_gen === "number" ? prog.current_gen : (s.current_gen || 0);
  const maxGens = prog.max_generations || s.max_generations || 0;
  const engineLabel = running ? "실행 중" : (s.status === "done" ? "완료" : s.status === "error" ? "오류" : "대기");
  const fmt = (v, d = 2) => (v == null || v === "" ? "—" : Number(v).toFixed(d));
  return (
    <div className="v4-enggate-bar" aria-label="엔진·게이트 상황판">
      <div className="v4-eg-group">
        <span className="v4-eg-lbl">엔진</span>
        <span className={"v4-eg-chip " + (running ? "run" : "idle")}>{engineLabel}</span>
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

// v5.3.2 스테이지 정의 — 4탭(N6: 채점+부검 통합). phaseIndex(0생성·1백테·2채점·3부검)
//   → 스테이지 [0,1,2,2]. run 완료(done)는 반복·성과(3).
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
  const lastLog = logs.length ? logs[logs.length - 1] : "로그 대기";
  const errorText = s.error || latest.error || "";
  return (
    <section className="v6-board" aria-labelledby="v6-board-heading">
      <h2 id="v6-board-heading" className="panel-hd-title">실시간 연구 상황판</h2>
      <_V6PipelineBelt liveStage={liveStage} activeStage={activeStage} onStagePin={onStagePin} />
      <div className="v6-board-top v6-board-top--belt">
        <div className="v6-board-timeline">
          <div className="v4-wf-next">
            <div><span className="k">process</span><b className="mono" style={{ color: "var(--ink-0)" }}>{procLabel}</b></div>
            <span className={"v4-chip " + authCls} title={authKnown ? "mode_authority.generation_allowed" : "관찰성 발행 대기(폴백)"}>{authLabel}</span>
            <div><span className="k">다음 행동</span><b>{nextMsg}</b></div>
          </div>
          <_V4EngineGateBar state={s} targetScore={targetScore} mddCap={mddCap} minDailyTrades={minDailyTrades} />
        </div>
        <div className="v6-board-curgen">
          <CurrentGenPanel state={s} />
        </div>
        <div className="v6-board-kpi">
          <_V4Stats state={s} />
        </div>
      </div>
      <div className="v6-board-strip">
        <div className="v6-timing" aria-label="단계별 실제 시간">
          {timings.length ? timings.map(([step, sec]) => (
            <div key={step} className="v6-timing-item" title={`${step} ${sec.toFixed(1)}초`}>
              <span className="k mono">{step}</span>
              <span className="bar"><i style={{ width: Math.max(4, Math.round((sec / maxT) * 100)) + "%" }}></i></span>
              <span className="v mono">{sec.toFixed(1)}s</span>
            </div>
          )) : <span className="mono v6-dim">완료 단계 없음</span>}
        </div>
        <div className="v6-blockers" aria-label="차단 사유">
          {blockers.length
            ? blockers.map(b => <span key={String(b)} className="v4-chip warn" title="promotion blocker">{String(b)}</span>)
            : <span className="v4-chip ok">발행된 차단 사유 없음</span>}
        </div>
        <details className="v6-log">
          <summary className="mono" title="최신 로그 · 클릭하면 최근 로그 펼침">{String(lastLog)}</summary>
          <div className="v6-log-list mono">{logs.slice(-8).map((l, i) => <div key={i}>{String(l)}</div>)}</div>
        </details>
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
  const [selectedDetailGen, setSelectedDetailGen] = useState_v4r(null);
  // 스테이지 pin — 벨트/탭 클릭 시 고정, 해제 시 라이브 자동전환.
  const [stagePin, setStagePin] = useState_v4r(null);
  // v5.4 L2 — 스테이지 그리드 열 수 선택(2열/4열, localStorage 유지).
  const [stageCols, setStageCols] = useState_v4r(() => {
    try { const v = window.localStorage.getItem("stom_v6_stage_cols"); return v === "2" || v === "4" ? v : "4"; }
    catch (e) { return "4"; }
  });
  const setStageColsPersist = (c) => {
    setStageCols(c);
    try { window.localStorage.setItem("stom_v6_stage_cols", c); } catch (e) {}
  };
  const s = state || {};
  const latest = s.latest || {};
  const runId = s.run_id || "";
  const gens = Array.isArray(s.generations) ? s.generations : [];
  const hasData = gens.length > 0;
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;
  const viewCode = typeof onViewCode === "function" ? onViewCode : () => {};
  const running = s.status === "running" || s.status === "stopping";
  const phaseIdx = running ? phaseIndex(latest.phase) : -1;
  const liveStage = s.status === "done" ? 3 : (phaseIdx >= 0 ? STAGE_FROM_PHASE[phaseIdx] : -1);
  // 활성 스테이지: pin > 라이브 단계 > (데이터 있으면 반복·성과, 없으면 생성).
  const activeStage = stagePin != null ? stagePin : (liveStage >= 0 ? liveStage : (hasData ? 3 : 0));
  const onStagePin = (i) => setStagePin(prev => (prev === i ? null : i));
  const onStageKey = (e) => {
    const n = V6_STAGES.length;
    if (e.key === "ArrowRight") { e.preventDefault(); setStagePin(((activeStage + 1) % n)); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); setStagePin(((activeStage - 1 + n) % n)); }
    else if (e.key === "Home") { e.preventDefault(); setStagePin(0); }
    else if (e.key === "End") { e.preventDefault(); setStagePin(n - 1); }
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

  return (
    <section className="v4-research v6-live" aria-labelledby="v4-research-heading">
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


      {/* ===== 스테이지 탭(4) — 라이브 자동전환·pin ===== */}
      {/* v5.4 L2: 스테이지 탭 우측 배치(열 수) 선택 */}
      <div className="v6-stage-tabs" role="tablist" aria-label="연구 프로세스 단계" onKeyDown={onStageKey}>
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
        {stagePin != null && (
          <button className="btn ghost sm v5-pin-reset" onClick={() => setStagePin(null)}>
            단계 고정 해제 · 라이브 따라가기
          </button>
        )}
        <span className="v6-cols-pick" role="group" aria-label="스테이지 배치 열 수 선택">
          <span className="lbl">배치</span>
          {["2", "4"].map(c => (
            <button key={c} type="button" className={"btn ghost sm" + (stageCols === c ? " on" : "")}
                    aria-pressed={stageCols === c} onClick={() => setStageColsPersist(c)}>{c}열</button>
          ))}
        </span>
      </div>

      {/* ===== 현재 스테이지 단일 포커스 패널 ===== */}
      <div id="v6-stage-panel" className={"v6-stage-panel cols-" + stageCols} role="tabpanel"
           aria-labelledby={"v6-stage-tab-" + V6_STAGES[activeStage].key} aria-live="polite">
        {activeStage === 0 && (
          <div className="v6-stage-grid">
            <HypothesisPanel state={s} />
            <ActiveStrategyPanel state={s} baseUrl={baseUrl} onViewCode={viewCode} />
            <ConditionDiscoveryPanel state={s} wsStatus={wsStatus} />
          </div>
        )}
        {activeStage === 1 && (
          <div className="v6-stage-grid">
            <PhaseDetailPanel state={s} wsStatus={wsStatus} onViewLatestCode={viewCode} pinnedIdx={1} />
            <div className="v6-engine-xl">
              <EnginePanel state={s} wsStatus={wsStatus} />
            </div>
            <BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} />
            <EvolutionGuiParityPanel baseUrl={baseUrl} wsStatus={wsStatus} state={s} externalSelGen={selectedDetailGen} />
          </div>
        )}
        {activeStage === 2 && (
          <div className="v6-stage-grid">
            <_V4Fold storageKey="stom_v6_gate" label="게이트·채점 기준 · 현재 run 유효값 (클릭 상세)">
              <ResearchCriteriaBanner state={s} baseUrl={baseUrl} />
              <ActiveConfigPanel state={s} />
              <CostPanel state={s} cap={50000} />
              <ResearchGlossaryPanel />
            </_V4Fold>
            <GenerationsTable state={s} mddCap={mddCap} minDailyTrades={minDailyTrades}
                              onViewCode={(g) => viewCode(g && g.gen_no != null ? g.gen_no : g)}
                              onSelectDetail={(genNo) => setSelectedDetailGen(genNo)} />
            {/* v5.4 L5 — 탐색 히트맵(edge)과 엣지·상관·안정성 중복 병합: 연구실 단일 섹션(전폭) */}
            <section className="v6-stage-lab v54-span-all" aria-label="탐색·엣지·상관·안정성 통합 분석">
              <h3 className="stom-section-label">탐색 히트맵 · 엣지 · 상관 · 안정성 검증 (통합 분석)</h3>
              <ResearchLabPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
            </section>
            <AutopsyPanel state={s} wsStatus={wsStatus} />
            <LineagePanel state={s} wsStatus={wsStatus} />
            <MetaPanel state={s} wsStatus={wsStatus} />
            <HoldoutPanel state={s} wsStatus={wsStatus} />
            <FeedbackPanel state={s} />
          </div>
        )}
        {activeStage === 3 && (
          <div className="v6-stage-grid">
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
            <section className="v6-stage-lab v54-span-all" aria-label="세대 진화 분석(전폭)">
              <h3 className="stom-section-label">세대 진화 분석 · 개별 그래프</h3>
              <EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
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
