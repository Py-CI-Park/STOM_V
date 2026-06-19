/* Main app composition */
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { ConnBadge, StatusBadge, CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner } from "./panels.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { RunComparePanel } from "./run-compare.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { EnginePanel } from "./engine.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { FitnessChart, ProfitChart, EquityOverlayChart, QualityTrendChart, BacktestDetailChart, HallOfFamePanel } from "./chart.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { HypothesisPanel } from "./hypothesis.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { GenerationsTable } from "./table.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { CodeViewer } from "./code-viewer.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { PhaseDetailPanel, PhaseTimeline, ProcessFlowPanel } from "./phase-detail.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { SettingsModal } from "./settings.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { ResearchGlossaryPanel } from "./glossary.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { BacktestTab } from "./backtest.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { SimulationTab } from "./simulation.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { EvolutionAnalysisPanel } from "./evolution-analysis.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { ResearchLabPanel } from "./research-lab.jsx";
import { LabPage, ProPage, VerdictPanel, ResearchIndexPage } from "./dashboard-pages.jsx";
import { DASHBOARD_ROUTE_CONTRACTS, DASHBOARD_TAB_GROUPS, routeContract, normalizeDashboardTabKey } from "./ui-contract.jsx";
import { UiStateBlock, MetricList } from "./ui-state.jsx";
const { useState: useState_a, useEffect: useEffect_a, useCallback: useCallback_a } = React;

function App() {
  const [baseUrl, setBaseUrl] = useState_a(() => {
    // 캐시된 BASE가 현재 페이지 origin과 다른 cross-origin(예: 과거 8770 캐시인데
    // 8771에서 서빙)이면 same-origin으로 마이그레이션한다 — 안 그러면 CORS로 데모모드.
    const cached = localStorage.getItem("stom_base_url");
    const here = (typeof window !== "undefined" && window.location && window.location.origin) || "";
    if (cached && here.startsWith("http")) {
      try {
        if (new URL(cached).origin !== here) return DEFAULT_BASE;
      } catch { return DEFAULT_BASE; }
    }
    return cached || DEFAULT_BASE;
  });
  const [pendingBase, setPendingBase] = useState_a(baseUrl);
  const [theme, setTheme] = useState_a(() => localStorage.getItem("stom_theme") || "dark");
  // 상단 탭: "evolution"(진화 대시보드·기본) | "backtest" | "simulation".
  //   localStorage 로 새로고침 후에도 마지막 탭 유지. useBackend(WS)는 App 레벨에
  //   그대로 두어 어느 탭에 있어도 진화 상태 수신이 끊기지 않는다.
  const [activeTab, setActiveTab] = useState_a(() => normalizeDashboardTabKey(localStorage.getItem("stom_active_tab") || "evolution"));
  // Phase6.1 — 시뮬 탭 keep-alive: 한 번 방문하면 언마운트하지 않고 hidden 처리(상태 유지).
  const [simVisited, setSimVisited] = useState_a(() => normalizeDashboardTabKey(localStorage.getItem("stom_active_tab") || "evolution") === "simulation");
  useEffect_a(() => { if (activeTab === "simulation") setSimVisited(true); }, [activeTab]);

  const { state: liveState, health, wsStatus, configSpec, send, lastReply, reconnect } = useBackend(baseUrl);

  const [settingsOpen, setSettingsOpen] = useState_a(false);
  const [approvalOpen, setApprovalOpen] = useState_a(false);
  const [codeViewGen, setCodeViewGen] = useState_a(null); // gen object
  // #65 P1 — 세대표 '백테상세' 클릭 시 BacktestDetailChart에 내려줄 선택 세대(드롭다운 대체).
  const [selectedDetailGen, setSelectedDetailGen] = useState_a(null);

  // #65 P0 — run 셀렉터. selectedRun이 null/''이면 LIVE(현재 state, WS), 아니면 그 run을
  //   /run_state로 재구성해 본다. 라이브 state가 합성 run(segrun)으로 오염돼도 실 run을 골라
  //   볼 수 있다. runList=드롭다운 목록(최신순), fetchedRunState=선택 run의 재구성 payload.
  const [selectedRun, setSelectedRun] = useState_a("");        // "" = LIVE
  const [runList, setRunList] = useState_a([]);                // [{run_id, ...}]
  const [fetchedRunState, setFetchedRunState] = useState_a(null);

  const isDemoSrc = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // run 목록 로드(GET /runs). 데모/연결 전이면 빈 목록. baseUrl 변경 시 재조회.
  useEffect_a(() => {
    if (isDemoSrc || !baseUrl) { setRunList([]); return; }
    let cancelled = false;
    fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(3000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        // 최신순(started_at 내림차순). started_at 없으면 뒤로.
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      })
      .catch(() => { if (!cancelled) setRunList([]); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemoSrc, liveState.run_id, liveState.status]);

  // 선택 run의 state를 /run_state로 재구성해 가져온다(LIVE면 스킵). 30초 자동 새로고침.
  const fetchRunState = useCallback_a(() => {
    if (!selectedRun || isDemoSrc || !baseUrl) { setFetchedRunState(null); return; }
    fetch(baseUrl + "/run_state?run_id=" + encodeURIComponent(selectedRun),
          { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setFetchedRunState(j))
      .catch(() => setFetchedRunState(null));
  }, [baseUrl, selectedRun, isDemoSrc]);

  useEffect_a(() => {
    if (!selectedRun) { setFetchedRunState(null); return; }
    fetchRunState();
    const id = setInterval(fetchRunState, 30000);
    return () => clearInterval(id);
  }, [fetchRunState, selectedRun]);

  // effectiveState: 선택 run이 있고 그 state를 받아왔으면 그것을, 아니면 라이브 state를 쓴다.
  //   모든 하위 패널(차트/테이블/카드/명전 등)은 이 effectiveState를 소비한다(기본 LIVE).
  const state = (selectedRun && fetchedRunState) ? fetchedRunState : liveState;

  const running = state.status === "running" || state.status === "stopping";

  useEffect_a(() => {
    localStorage.setItem("stom_base_url", baseUrl);
  }, [baseUrl]);

  useEffect_a(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stom_theme", theme);
  }, [theme]);

  useEffect_a(() => {
    localStorage.setItem("stom_active_tab", activeTab);
  }, [activeTab]);

  const onStart = useCallback_a((config) => {
    send({ action: "start", config });
    setSettingsOpen(false);
  }, [send]);

  const onStop = useCallback_a(() => {
    send({ action: "stop" });
  }, [send]);

  const onApprove = useCallback_a(({ userBuy, userSell }) => {
    if (!state.winner) return;
    send({
      action: "final_approval",
      buy_name: state.winner.buy_name,
      sell_name: state.winner.sell_name,
      user_buy: userBuy,
      user_sell: userSell,
    });
    setApprovalOpen(false);
  }, [send, state.winner]);

  const onViewCodeByGen = useCallback_a((genNo) => {
    const g = (state.generations || []).find(x => x.gen_no === genNo);
    if (g) setCodeViewGen(g);
  }, [state.generations]);

  // Find mdd_cap from configSpec defaults to color MDDs in the table
  const mddCap = (configSpec.find(f => f.name === "mdd_cap")?.default) ?? 15;
  // 일평균거래횟수 하한(빈도 게이트 주 기준) — 테이블에서 미달 행을 경고색으로 표시.
  const minDailyTrades = (configSpec.find(f => f.name === "min_daily_trades")?.default) ?? 0.5;
  const targetScore = (configSpec.find(f => f.name === "target_score")?.default) ?? 1.0;

  const pct = state.max_generations > 0 ? Math.min(100, (state.current_gen / state.max_generations) * 100) : 0;
  const isIdle = state.status === "idle" && state.generations.length === 0 && !running;
  const activeRoute = routeContract(activeTab);
  const shellMetrics = [
    { label: "route", value: activeRoute.badge || activeTab },
    { label: "group", value: activeRoute.group || "—" },
    { label: "status", value: state.status || "—" },
    { label: "run", value: selectedRun ? "archive" : "LIVE" },
  ];

  return (
    <div className="stom-app-shell">

      {/* ============= TOP BAR ============= */}
      <header className="stom-shell">
        <div className="stom-shell-top">
          <div className="stom-shell-brand">
            <Logo />
            <div className="stom-shell-title">
              <h1>STOM AI · 조건식 자율 진화 대시보드</h1>
              <span className="mono">
                autonomous_strategy_loop · contract_v{health.contract_version ?? state.contract_version ?? 1}
              </span>
            </div>
            <nav className="stom-pagenav mono" aria-label="현재 위치">
              <span className="stom-pagenav-item stom-pagenav-active"
                    title={activeRoute.contract || "현재 보고 있는 탭"}>
                {activeRoute.icon} {activeRoute.label}
              </span>
            </nav>
          </div>

          <div className="stom-shell-controls">
            <ThemeToggle theme={theme} onChange={setTheme} />
            <BaseUrlControl
              value={pendingBase}
              onChange={setPendingBase}
              onApply={() => setBaseUrl(pendingBase)}
              onReconnect={reconnect}
            />
            <ConnBadge health={health} wsStatus={wsStatus} />
            <StatusBadge status={state.status} />
          </div>
        </div>

        <div className="stom-shell-context">
          <UiStateBlock kind="info" compact title={activeRoute.group || "Dashboard"} detail={activeRoute.key || activeTab}>
            {activeRoute.contract || "STOM dashboard route"}
          </UiStateBlock>
          <MetricList items={shellMetrics} />
        </div>

        {/* ===== 탭 내비게이션 (전 탭 공통, 브랜드 행 바로 아래) ===== */}
        <TabNav activeTab={activeTab} onSelect={setActiveTab} />

        {/* 진화 컨트롤 스트립(진행도/run 셀렉터/시작·정지)은 진화 탭에서만 노출 */}
        {activeTab === "evolution" && (
        <div className="stom-run-strip">
          <div style={{ minWidth: 200 }}>
            <div className="stat-label" style={{ marginBottom: 4 }}>진행도</div>
            <div className="mono" style={{ fontSize: 15, color: "var(--ink-0)" }}>
              <span style={{ color: running ? "var(--amber)" : "var(--ink-0)" }}>{state.current_gen}</span>
              <span style={{ color: "var(--ink-3)" }}> / {state.max_generations}</span>
              <span style={{ marginLeft: 8, color: "var(--ink-2)", fontSize: 11 }}>세대</span>
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div className="progress-track">
              <div className={`progress-fill ${running ? "running" : ""}`} style={{ width: `${pct}%` }}></div>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
              <span>provider={state.provider}</span>
              <span>tf={state.bt_timeframe}</span>
              <span>run_id={state.run_id || "—"}</span>
              <span>{pct.toFixed(1)}%</span>
            </div>
          </div>
          {/* #65 P0 — run 셀렉터: LIVE(현재) 또는 과거 실 run을 골라 본다(라이브 오염 우회). */}
          <RunSelector
            runList={runList}
            selectedRun={selectedRun}
            onSelect={setSelectedRun}
            onRefresh={fetchRunState}
            disabled={isDemoSrc}
          />
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn primary" onClick={() => setSettingsOpen(true)} disabled={running}>
              ▸ 시작
            </button>
            <button className="btn danger" onClick={onStop} disabled={!running}>
              ◼ 정지
            </button>
          </div>
        </div>
        )}
      </header>

      {/* ============= MAIN ============= */}
      {/* Phase6.1 — 시뮬 탭은 첫 방문 후 hidden 으로 유지(언마운트 금지): 탭을 오가도
          리플레이 WS·재생 위치·종목 선택이 초기화되지 않는다(사용자 신고). */}
      {simVisited && (
        <div style={{ display: activeTab === "simulation" ? undefined : "none" }}>
          <ErrorBoundary>
            <SimulationTab baseUrl={baseUrl} wsStatus={wsStatus} />
          </ErrorBoundary>
        </div>
      )}
      {activeTab === "backtest" ? (
        <ErrorBoundary>
          <BacktestTab baseUrl={baseUrl} wsStatus={wsStatus} />
        </ErrorBoundary>
      ) : activeTab === "simulation" ? null
        /* Phase9/Remodel — SPA 증거 워크스페이스 탭은 dashboard-pages.jsx 컴포넌트를
           직접 import해 auto-mount 시점에도 Lab/Records/Pro/Verdict가 즉시 렌더된다. */
        : activeTab === "lab" ? (
        <ErrorBoundary>
          <LabPage baseUrl={baseUrl} onNavigate={setActiveTab} />
        </ErrorBoundary>
      ) : activeTab === "pro" ? (
        <ErrorBoundary>
          <ProPage baseUrl={baseUrl} onNavigate={setActiveTab} />
        </ErrorBoundary>
      ) : activeTab === "verdict" ? (
        <ErrorBoundary>
          <VerdictPanel baseUrl={baseUrl} onNavigate={setActiveTab} />
        </ErrorBoundary>
      ) : activeTab === "records" ? (
        <ErrorBoundary>
          <ResearchIndexPage baseUrl={baseUrl} onNavigate={setActiveTab} />
        </ErrorBoundary>
      ) : activeTab === "process" ? (
        <ErrorBoundary>
          <main style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <ProcessFlowPanel state={state} />
            <iframe
              src={baseUrl + "/process_flow"}
              title="프로세스 흐름"
              style={{ width: "100%", height: "calc(100vh - 300px)", minHeight: 420, border: "none", borderRadius: 8, background: "#0d1117" }}
            />
          </main>
        </ErrorBoundary>
      ) : isIdle ? (
        <IdleState onStart={() => setSettingsOpen(true)} configSpec={configSpec} />
      ) : (
        <main style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* 승인 export 결과 배너(final_approval 게이트는 ApprovalDialog가 유지) */}
          <ExportStatusBanner reply={lastReply} />

          <_EvoSection storageKey="stom_evo_runmon" label={<SectionLabel text="Run Monitor" />}>
            <CurrentGenPanel state={state} />
            <ResearchCriteriaBanner state={state} baseUrl={baseUrl} />
            <ResearchGlossaryPanel />
            <ActiveStrategyPanel state={state} baseUrl={baseUrl} onViewCode={onViewCodeByGen} />
            <PhaseTimeline state={state} />
            <ProcessFlowPanel state={state} />
            <PhaseDetailPanel state={state} wsStatus={wsStatus} />
            <EnginePanel state={state} wsStatus={wsStatus} />
          </_EvoSection>

          <div className="grid-main">
            <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
              {/* Phase6.1(E7) — 탐색 히트맵을 적합도 추이 위에 동일 크기 패널로(사용자 요청). */}
              {window.ResearchHeatmapPanel ? (
                <window.ResearchHeatmapPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id} />
              ) : null}
              <FitnessChart state={state} target={targetScore} />
              <ProfitChart state={state} targetPct={0} />
              <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id} />
              {/* O1 — 백테 상세(일별손익 막대 + 누적수익곡선): 선택 세대의 per-trade CSV 시계열 재현 */}
              {/* #65 P1 — externalSelGen: 세대표 '백테상세' 클릭이 선택 세대를 여기로 동기화 */}
              <BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={state}
                                   externalSelGen={selectedDetailGen} />
              <QualityTrendChart state={state} />
              {/* 🏆 명예의 전당 — 인간 벤치마크(19전략) + AI 생성 통합(목표선 가시화) */}
              <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
              <_EvoSection storageKey="stom_evo_strategy" label={<SectionLabel text="Strategy / Prompt" />}>
                <GenerationsTable state={state} mddCap={mddCap} minDailyTrades={minDailyTrades}
                                  onViewCode={(g) => setCodeViewGen(g)}
                                  onSelectDetail={(genNo) => setSelectedDetailGen(genNo)} />
              </_EvoSection>
              {/* 운영·관찰: run 비교 콘솔(REST /runs, loop_runs.db 직접) */}
              <_EvoSection storageKey="stom_evo_compare" label={<SectionLabel text="Compare" />}>
                <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
              </_EvoSection>
              {/* 트랙 L — 진화 결과 분석 시각화(세대 멀티라인·산점도·상위표, GET /bt/evo_gens) */}
              <_EvoSection storageKey="stom_evo_genanalytics" label={<SectionLabel text="Generation Analytics" />}>
                <ErrorBoundary><EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id || ""} onOpenWorkbench={() => setActiveTab("backtest")} /></ErrorBoundary>
              </_EvoSection>
            </div>
            <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* #65 P0 — 분석 클러스터를 판정 카드 위로(인과 순서: 분석→가정→개선이
                  판정의 근거). 패널 자체 변경 없이 JSX 순서만 재배치. */}
              {/* ── AI 분석 패널 묶음 (edge / feature / correlation / combinations REST) ── */}
              <_EvoSection storageKey="stom_evo_researchlab" label={<SectionLabel text="Research Lab" />}>
                <ErrorBoundary>
                  <ResearchLabPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id || ""} />
                </ErrorBoundary>
                {/* P2(2026-06-14): 연구 위키·AI 컨텍스트 팩은 연구실 탭으로 이전(진화 사이드바 중복 제거).
                    진화 탭엔 발견용 링크만 둔다 — 홈은 dashboard-pages.jsx LabPage(P1). */}
                <button className="btn ghost sm" onClick={() => setActiveTab("lab")}
                        style={{ alignSelf: "flex-start", marginTop: 2 }}
                        title="연구 위키 · AI 컨텍스트 팩은 연구실 탭으로 이동했습니다">
                  📚 연구 위키 · AI 컨텍스트 팩 → 연구실 탭
                </button>
              </_EvoSection>

              {/* ── 분석 패널 묶음 (P1~P5 live page_data 소비, demo 배지 규약) ── */}
              <_EvoSection storageKey="stom_evo_analysis" label={<SectionLabel text="진화 분석 · P1~P5" />}>
                {/* P2b-2 — 가정 루프(세운 가정+채택/기각 판정) 가시화. 판정된 가정이
                    있는 세대가 없으면(토글 OFF/구 상태) 패널이 null 반환해 미표시. */}
                <HypothesisPanel state={state} />
                <AutopsyPanel state={state} wsStatus={wsStatus} />
                <PopulationPanel state={state} wsStatus={wsStatus} />
                <LineagePanel state={state} wsStatus={wsStatus} />
                <MetaPanel state={state} wsStatus={wsStatus} />
                <HoldoutPanel state={state} wsStatus={wsStatus} />
              </_EvoSection>

              {/* ── 판정 카드(분석의 결론) ── */}
              <_EvoSection storageKey="stom_evo_verdict" label={<SectionLabel text="판정 · Best / Winner" />}>
                {/* #65 P1 — best.gen===winner.gen이면(게이트 통과한 best가 곧 winner) 한 카드로
                    병합 표기(graded+score 동시). 다르면 기존 2카드(하위호환). */}
                {(state.best && state.winner && state.best.gen === state.winner.gen) ? (
                  <MergedBestWinnerCard best={state.best} winner={state.winner}
                                        onApprove={() => setApprovalOpen(true)}
                                        onViewCode={onViewCodeByGen} />
                ) : (
                  <>
                    <BestCard best={state.best} onViewCode={onViewCodeByGen} />
                    <WinnerCard winner={state.winner}
                                onApprove={() => setApprovalOpen(true)}
                                onViewCode={onViewCodeByGen} />
                  </>
                )}
                {/* R8 — 활성 설정/토글 스냅샷(LoopState.active_config) LIVE 노출 */}
                <ActiveConfigPanel state={state} />
                <CostPanel state={state} cap={50000} />
                <FeedbackPanel state={state} />
              </_EvoSection>
            </aside>
          </div>
        </main>
      )}

      {/* ============= MODALS ============= */}
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onStart={onStart}
        configSpec={configSpec}
        disabled={running}
      />
      <ApprovalDialog
        winner={approvalOpen ? state.winner : null}
        onClose={() => setApprovalOpen(false)}
        onConfirm={onApprove}
      />
      <CodeViewer
        generation={codeViewGen}
        onClose={() => setCodeViewGen(null)}
        runId={state.run_id}
        baseUrl={baseUrl}
      />

      {/* Footer */}
      <footer style={{ marginTop: 24, padding: "12px 0", textAlign: "center", color: "var(--ink-3)", fontSize: 10.5, fontFamily: "var(--mono)" }}>
        STOM AI · STATE_CONTRACT v{state.contract_version ?? 1} · last_update {fmtTime(state.updated_at)}
      </footer>
    </div>
  );
}

// 상단 탭 내비게이션. 브랜드 행 아래에 위치하며 전 탭 공통으로 항상 보인다.
//   Phase4 트랙A(2026-06-12): 대형화·강한 활성 대비·탭 아이콘.
//   크기/색/대비는 styles.css(.stom-tabnav / .stom-tab / .stom-tab-active)에서
//   구동한다 — 인라인 스타일은 클래스를 덮으므로 사이즈 prop을 두지 않는다.
// Phase9(2026-06-13) — SPA 6탭 통합: 별도 HTML(lab/pro/verdict)을 인페이지 탭으로
//   승격해 풀 리로드·중복 진입을 제거. lab/pro/verdict 본문은 dashboard-pages.jsx
//   전역(window.LabPage / ProPage / VerdictPanel)이 담당한다.
const STOM_TABS = DASHBOARD_ROUTE_CONTRACTS;

function TabNav({ activeTab, onSelect }) {
  return (
    <nav role="tablist" aria-label="대시보드 탭" className="stom-tabnav">
      {DASHBOARD_TAB_GROUPS.map(group => (
        <div key={group.key} className="stom-tabgroup" data-group={group.key}>
          <span className="stom-tabgroup-label mono">{group.label}</span>
          <div className="stom-tabgroup-items">
            {group.tabs.map(key => STOM_TABS.find(tab => tab.key === key)).filter(Boolean).map(tab => {
              const active = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  role="tab"
                  aria-selected={active}
                  className={"stom-tab" + (active ? " stom-tab-active" : "")}
                  onClick={() => onSelect(tab.key)}
                  title={tab.contract}
                >
                  <span className="stom-tab-ico" aria-hidden="true">{tab.icon}</span>
                  <span className="stom-tab-label">{tab.label}</span>
                  <span className="stom-tab-badge mono">{tab.badge}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

// 분석 패널 묶음을 시각적으로 구분하는 작은 섹션 라벨(레이아웃 정리용).
// Design Pass(2026-06-14): 섹션 헤더를 styles.css .stom-section-label(ink-1·12px·teal accent)로
//   승격 — 진화 탭의 논리 그룹(Run Monitor·Strategy·Compare·Research·분석·판정) 경계를 분명히
//   해 "단일 30패널 스크롤"을 시각적으로 구획한다. 인라인(dim ink-3) 대비 가독성·위계 향상.
function SectionLabel({ text }) {
  return <div className="stom-section-label">{text}</div>;
}

// P3(2026-06-14): 진화 탭 섹션 그룹 접이식 래퍼(IA 완화). 네이티브 <details> — 키보드 기본 동작 +
//   aria-expanded + localStorage 영속. 기본 open(펼침) → 첫 페인트는 기존과 동일(작은 disclosure
//   caret 만 추가). label 은 기존 <SectionLabel text="..."/> 엘리먼트를 그대로 받아 summary 에 렌더
//   (text="..." 리터럴이 호출부에 보존되어 design_pass/integrated_layout 계약 유지). 패널 순서 불변.
function _EvoSection({ storageKey, label, children }) {
  const [open, setOpen] = useState_a(() => {
    try { const v = window.localStorage.getItem(storageKey); return v === null ? true : v === "1"; }
    catch (e) { return true; }
  });
  const onToggle = (e) => {
    const o = e.currentTarget.open;
    setOpen(o);
    try { window.localStorage.setItem(storageKey, o ? "1" : "0"); } catch (e2) {}
  };
  return (
    <details className="evo-group" open={open} onToggle={onToggle}>
      <summary className="evo-group-summary" aria-expanded={open}>{label}</summary>
      <div className="evo-group-body">{children}</div>
    </details>
  );
}

function ThemeToggle({ theme, onChange }) {
  return (
    <div className="theme-toggle" role="group" aria-label="테마">
      <button className={theme === "dark" ? "active" : ""}
              onClick={() => onChange("dark")}
              data-tip="다크 모드">
        <SunMoonIcon dark /> Dark
      </button>
      <button className={theme === "light" ? "active" : ""}
              onClick={() => onChange("light")}
              data-tip="라이트 모드">
        <SunMoonIcon /> Light
      </button>
    </div>
  );
}

function SunMoonIcon({ dark }) {
  if (dark) return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <path d="M11.5 9.5A6 6 0 0 1 6 4c0-1.2.36-2.3.97-3.23A8 8 0 1 0 14.73 11a6 6 0 0 1-3.23.5z"
            fill="currentColor" />
    </svg>
  );
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="3" fill="currentColor" />
      <g stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
        <line x1="8" y1="1" x2="8" y2="2.5" />
        <line x1="8" y1="13.5" x2="8" y2="15" />
        <line x1="1" y1="8" x2="2.5" y2="8" />
        <line x1="13.5" y1="8" x2="15" y2="8" />
        <line x1="3" y1="3" x2="4" y2="4" />
        <line x1="12" y1="12" x2="13" y2="13" />
        <line x1="13" y1="3" x2="12" y2="4" />
        <line x1="4" y1="12" x2="3" y2="13" />
      </g>
    </svg>
  );
}

function Logo() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <rect x="0.5" y="0.5" width="35" height="35" rx="6" fill="#0c1014" stroke="#2a3441"/>
      {/* Stylized rising-and-evolving curve */}
      <path d="M5 26 L11 22 L16 24 L21 16 L26 18 L31 9"
            stroke="#4cd6b3" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="11" cy="22" r="1.6" fill="#4cd6b3" />
      <circle cx="16" cy="24" r="1.6" fill="#4cd6b3" />
      <circle cx="21" cy="16" r="1.6" fill="#4cd6b3" />
      <circle cx="26" cy="18" r="1.6" fill="#4cd6b3" />
      <circle cx="31" cy="9" r="2.2" fill="#a594ff" stroke="#fff" strokeWidth="0.6" />
      {/* corner ticks */}
      <path d="M3 3 L7 3 M3 3 L3 7" stroke="#2a3441" strokeWidth="1" />
      <path d="M33 33 L29 33 M33 33 L33 29" stroke="#2a3441" strokeWidth="1" />
    </svg>
  );
}

function BaseUrlControl({ value, onChange, onApply, onReconnect }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6,
                  background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, padding: "3px 6px" }}>
      <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: ".08em" }}>BASE</span>
      <input className="toolbar-input"
             value={value} onChange={e => onChange(e.target.value)}
             onKeyDown={e => { if (e.key === "Enter") onApply(); }}
             spellCheck={false} />
      <button className="btn ghost sm" onClick={onApply} data-tip="Base URL 적용 후 재연결">적용</button>
      <button className="btn ghost sm" onClick={onReconnect} data-tip="현재 URL로 재연결">↻</button>
    </div>
  );
}

// #65 P0 — run 셀렉터 드롭다운. 'LIVE(현재)' = 라이브 state(WS), 그 외 = 그 run을
//   /run_state로 재구성해 본다. 라이브 state가 합성 run(segrun)으로 오염돼도 실 run을
//   골라 브라우징할 수 있다. 기본 LIVE(value="").
function RunSelector({ runList, selectedRun, onSelect, onRefresh, disabled }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 6,
      background: "var(--bg-0)", border: "1px solid var(--line-1)",
      borderRadius: 5, padding: "3px 6px",
    }}>
      <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: ".08em" }}>RUN</span>
      <select
        value={selectedRun}
        onChange={e => onSelect(e.target.value)}
        disabled={disabled}
        className="mono"
        data-tip="볼 run 선택 — LIVE(현재) 또는 과거 실 run"
        style={{
          fontSize: 11, background: "var(--bg-1)", color: "var(--ink-0)",
          border: "1px solid var(--line-2)", borderRadius: 5, padding: "3px 6px",
          maxWidth: 200,
        }}>
        <option value="">LIVE(현재)</option>
        {(runList || []).map(r => (
          <option key={r.run_id} value={r.run_id}>
            {/* D5(2026-06-10): 배치 run은 세대 라벨(BASE_SEED/C7_…)이 정체성 — 대표 라벨 병기 */}
            {r.run_id}{r.label ? " · " + r.label : ""}{r.gate_passed_count > 0 ? " ✓" : ""}
          </option>
        ))}
      </select>
      {selectedRun && (
        <button className="btn ghost sm" onClick={onRefresh} disabled={disabled}
                data-tip="선택 run 새로고침">↻</button>
      )}
    </div>
  );
}

function IdleState({ onStart, configSpec }) {
  return (
    <>
      <div style={{
        padding: "10px 14px",
        background: "linear-gradient(90deg, rgba(240,179,90,0.10), rgba(240,179,90,0.02))",
        border: "1px solid rgba(240,179,90,0.32)",
        borderRadius: 6,
        marginBottom: 14,
        display: "flex",
        alignItems: "center",
        gap: 12,
        fontSize: 12,
        color: "var(--ink-1)",
      }}>
        <span style={{ fontSize: 16 }}>💡</span>
        <span>
          <strong style={{ color: "var(--amber)" }}>대시보드는 진화 시작 후 활성화됩니다.</strong>
          {" "}아래 <span className="mono" style={{ color: "var(--ink-0)" }}>▸ 진화 시작 설정 열기</span>를 누르면
          페이즈 타임라인(생성→백테→채점→부검), 엔진 메트릭, 자본곡선, 점수 분해, 부검 스트리밍이 실시간으로 보입니다.
        </span>
        <button className="btn primary" style={{ marginLeft: "auto" }} onClick={onStart}>
          ▸ 시작
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 }}>
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>Welcome</div>
        </div>
        <div className="panel-bd" style={{ padding: "28px 24px" }}>
          <h2 style={{ fontSize: 22, marginBottom: 10, letterSpacing: "-0.01em" }}>
            루프를 시작할 준비가 되었습니다.
          </h2>
          <p style={{ color: "var(--ink-1)", lineHeight: 1.6, marginBottom: 22, fontSize: 13 }}>
            AI가 한국 주식 매수/매도 전략 코드를 자동 생성·백테스트·채점·반복합니다.
            각 세대의 부검(autopsy)이 다음 세대 생성기에 피드백되어 조건식이 점진적으로 진화합니다.
            <br /><br />
            <span style={{ color: "var(--ink-2)" }}>
              목표 점수와 MDD 상한을 동시에 만족하면 하드 게이트를 통과한 우승 전략으로 등록되고,
              <br />
              사용자의 명시적 승인 후에만 운영 strategy.db로 export 됩니다.
            </span>
          </p>
          <button className="btn primary lg" onClick={onStart}>
            ▸ 진화 시작 설정 열기
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>루프 개요</div>
        </div>
        <div className="panel-bd" style={{ padding: 0 }}>
          <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {[
              { n: 1, k: "생성", d: "LLM이 직전 부검을 컨텍스트로 매수/매도 전략 코드를 생성 (실시간 스트리밍 표시)" },
              { n: 2, k: "백테스트", d: "지정된 시간단위·스코프·윈도우로 자본곡선·낙폭·매매를 시뮬레이션" },
              { n: 3, k: "채점", d: "graded_score = 손익·MDD·거래수·일관성의 가중합 (메트릭별 분해 표시)" },
              { n: 4, k: "게이트", d: "score ≥ target & MDD ≤ cap & trades ≥ min → 통과" },
              { n: 5, k: "부검", d: "탈락 원인을 자연어로 요약 → 다음 세대 컨텍스트에 주입" },
              { n: 6, k: "승인", d: "통과 전략을 운영 DB로 export (사용자 명시적 확인 필요)" },
            ].map((s, i, arr) => (
              <li key={s.n} style={{
                padding: "12px 16px",
                borderBottom: i < arr.length - 1 ? "1px solid var(--line-1)" : "none",
                display: "flex", gap: 12, alignItems: "flex-start",
              }}>
                <span className="mono" style={{
                  width: 22, height: 22, borderRadius: "50%",
                  background: "var(--bg-0)", border: "1px solid var(--line-2)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, color: "var(--ink-1)", flexShrink: 0,
                }}>{s.n}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: "var(--ink-0)", marginBottom: 2 }}>{s.k}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>{s.d}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
      </div>
    </>
  );
}

// ErrorBoundary — 한 컴포넌트가 특정 데이터에서 throw해도 전체가 검은 화면이 되지
//   않게 한다(이전엔 에러바운더리 부재로 단일 크래시가 #root 전체를 언마운트→검은 화면).
//   크래시 시 오류 메시지+스택+새로고침 버튼을 보여 진단·복구를 돕는다.
class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(error) { return { error }; }
  componentDidCatch(error, info) { console.error("Dashboard render error:", error, info); }
  render() {
    if (this.state.error) {
      const msg = String((this.state.error && this.state.error.stack) || this.state.error);
      return (
        <div style={{ padding: 40, fontFamily: "system-ui, sans-serif", background: "#0c1014", minHeight: "100vh" }}>
          <h2 style={{ color: "#ff8a8a", fontSize: 16, marginBottom: 8 }}>대시보드 렌더 오류</h2>
          <p style={{ color: "#9fb0c0", fontSize: 13, marginBottom: 12 }}>
            일부 데이터에서 렌더 오류가 발생했습니다. <b>Ctrl+Shift+R</b>로 새로고침하거나 상단 RUN 셀렉터에서 다른 run을 선택해 보세요.
          </p>
          <pre style={{ color: "#caa", fontSize: 11, whiteSpace: "pre-wrap", background: "#11161c", padding: 12, borderRadius: 6, overflow: "auto", maxHeight: 300 }}>{msg}</pre>
          <button onClick={() => location.reload()}
                  style={{ marginTop: 12, padding: "6px 14px", background: "#1a2530", color: "#cfe0f0", border: "1px solid #2a3441", borderRadius: 5, cursor: "pointer" }}>
            새로고침
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

Object.assign(window, { App, ErrorBoundary });

// Mount — Phase14.7: lab/pro/verdict 가 동일 app.js 를 로드해 다른 루트 컴포넌트를 마운트할 수
//   있도록 자동 마운트를 플래그로 가드한다. window.__STOM_NO_AUTO_MOUNT__ 이면 해당 페이지가
//   직접 (LabPage/ProPage/VerdictPanel 등) 마운트하므로 여기서는 App 을 마운트하지 않는다.
if (typeof window === "undefined" || !window.__STOM_NO_AUTO_MOUNT__) {
  const root = ReactDOM.createRoot(document.getElementById("root"));
  root.render(<ErrorBoundary><App /></ErrorBoundary>);
}

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { App, ErrorBoundary };
