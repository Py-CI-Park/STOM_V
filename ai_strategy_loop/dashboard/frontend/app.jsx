/* Main app composition */
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { ConnBadge, StatusBadge, CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner } from "./panels.jsx";
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
import { ResearchRecordsPanel } from "./research-records-panel.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { HistoryConditionTreePanel } from "./history-condition-tree.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { AbPairCompareView, CellHeatmap, HoldoutFunnel } from "./history-viz.jsx";
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { EvolutionGuiParityPanel } from "./evolution-gui-parity-panel.jsx";
import { LabPage, ProPage, VerdictPanel, ResearchIndexPage } from "./dashboard-pages.jsx";
import { ResearchLabPanel } from "./research-lab.jsx";
import { DASHBOARD_ROUTE_CONTRACTS, DASHBOARD_TAB_GROUPS, EVOLUTION_SUBTAB_CONTRACTS, dashboardPathFor, dashboardRouteFromLocation, evolutionSubtabContract, normalizeDashboardTabKey, normalizeEvolutionSubtabKey, routeContract } from "./ui-contract.jsx";
import { UiStateBlock, MetricList } from "./ui-state.jsx";
import { pageOwnerContract } from "./dashboard-inventory.jsx";
import { INITIAL_STATE } from "./conn-backend.jsx";
const { useState: useState_a, useEffect: useEffect_a, useCallback: useCallback_a, useRef: useRef_a } = React;

function App() {
  const initialDashboardRoute = dashboardRouteFromLocation();
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
  // 상단 탭은 조건식 AI·백테스트·차트 리플레이 3개만 노출한다. 연구/프로세스/
  // 결정 감사 워크스페이스는 조건식 AI 하위 canonical URL(/ui/evolution/*)로만 이동한다.
  const [activeTab, setActiveTab] = useState_a(() => initialDashboardRoute.tab);
  const [activeEvolutionTab, setActiveEvolutionTab] = useState_a(() => initialDashboardRoute.evolutionSubtab);
  // Phase6.1 — 시뮬 탭 keep-alive: 한 번 방문하면 언마운트하지 않고 hidden 처리(상태 유지).
  const [simVisited, setSimVisited] = useState_a(() => initialDashboardRoute.tab === "simulation");
  useEffect_a(() => { if (activeTab === "simulation") setSimVisited(true); }, [activeTab]);

  const { state: liveState, health, wsStatus, configSpec, configSpecStatus, send, lastReply, reconnect } = useBackend(baseUrl);

  const [settingsOpen, setSettingsOpen] = useState_a(false);
  const [approvalOpen, setApprovalOpen] = useState_a(false);
  const [codeViewGen, setCodeViewGen] = useState_a(null); // gen object
  // #65 P1 — 세대표 '백테상세' 클릭 시 BacktestDetailChart에 내려줄 선택 세대(드롭다운 대체).
  const [selectedDetailGen, setSelectedDetailGen] = useState_a(null);
  const [gptAuthProbe, setGptAuthProbe] = useState_a(null);

  // #65 P0 — run 셀렉터. selectedRun이 null/''이면 LIVE(현재 state, WS), 아니면 그 run을
  //   /run_state로 재구성해 본다. 라이브 state가 합성 run(segrun)으로 오염돼도 실 run을 골라
  //   볼 수 있다. runList=드롭다운 목록(최신순), fetchedRunState=선택 run의 재구성 payload.
  const [selectedRun, setSelectedRun] = useState_a("");        // "" = LIVE
  const [runList, setRunList] = useState_a([]);                // [{run_id, ...}]
  const [fetchedRunState, setFetchedRunState] = useState_a(null);

  const isDemoSrc = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // run 목록 로드(GET /runs). 데모/연결 전이면 빈 목록. baseUrl 변경 시 재조회.
  //   성능(2026-07-17): /runs 는 527런 3MB 대형 페이로드다. 과거엔 deps 에 liveState.run_id/
  //   status 가 있어 WS 상태 하이드레이션마다 3MB 를 3회씩 재요청(9MB)했다. 아카이브 목록은
  //   런이 '종료'될 때만 새 항목이 생기므로, active→inactive 전이에서만 재조회한다.
  const prevRunsActiveRef = useRef_a(false);
  const [runsEpoch, setRunsEpoch] = useState_a(0);
  useEffect_a(() => {
    const active = liveState.status === "running" || liveState.status === "stopping";
    if (prevRunsActiveRef.current && !active) setRunsEpoch((e) => e + 1); // 방금 종료 → 새 아카이브 가능
    prevRunsActiveRef.current = active;
  }, [liveState.status]);
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
  }, [baseUrl, isDemoSrc, runsEpoch]);

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
  useEffect_a(() => {
    localStorage.setItem("stom_active_evolution_tab", activeEvolutionTab);
  }, [activeEvolutionTab]);

  const syncBrowserRoute = useCallback_a((tab, evolutionSubtab, replace = false) => {
    if (typeof window === "undefined" || !window.history) return;
    const path = dashboardPathFor(tab, evolutionSubtab);
    const payload = {
      stomTab: normalizeDashboardTabKey(tab),
      stomEvolutionSubtab: normalizeEvolutionSubtabKey(evolutionSubtab),
    };
    if (replace || window.location.pathname === path) {
      window.history.replaceState(payload, "", path);
    } else {
      window.history.pushState(payload, "", path);
    }
  }, []);

  const onEvolutionSubtabSelect = useCallback_a((key) => {
    const next = normalizeEvolutionSubtabKey(key === "pro" ? "workbench" : key);
    setActiveTab("evolution");
    setActiveEvolutionTab(next);
    syncBrowserRoute("evolution", next);
  }, [syncBrowserRoute]);

  const onTopTabSelect = useCallback_a((key) => {
    const next = normalizeDashboardTabKey(key);
    setActiveTab(next);
    if (next === "simulation") setSimVisited(true);
    syncBrowserRoute(next, activeEvolutionTab);
  }, [activeEvolutionTab, syncBrowserRoute]);

  const onDashboardNavigate = useCallback_a((key) => {
    const top = normalizeDashboardTabKey(key);
    if (top === key && key !== "evolution") {
      onTopTabSelect(top);
      return;
    }
    if (key === "evolution") {
      onTopTabSelect("evolution");
      return;
    }
    onEvolutionSubtabSelect(key);
  }, [onTopTabSelect, onEvolutionSubtabSelect]);

  useEffect_a(() => {
    const route = dashboardRouteFromLocation();
    if (route.canonicalPath && (route.legacy || window.location.pathname !== route.canonicalPath)) {
      setActiveTab(route.tab);
      setActiveEvolutionTab(route.evolutionSubtab);
      syncBrowserRoute(route.tab, route.evolutionSubtab, true);
    }
  }, [syncBrowserRoute]);

  useEffect_a(() => {
    if (typeof window === "undefined") return undefined;
    const onPopState = () => {
      const route = dashboardRouteFromLocation();
      setActiveTab(route.tab);
      setActiveEvolutionTab(route.evolutionSubtab);
      if (route.tab === "simulation") setSimVisited(true);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const onStart = useCallback_a((config) => {
    send({ action: "start", config });
    setSettingsOpen(false);
  }, [send]);
  const onGptAuthTest = useCallback_a(() => {
    setGptAuthProbe({ status: "testing", message: "GPT auth proxy test running" });
    fetch(baseUrl + "/gpt_auth/test", { method: "POST", signal: AbortSignal.timeout(8000) })
      .then(r => r.json().then(j => ({ http_ok: r.ok, ...j })))
      .then(j => setGptAuthProbe(j))
      .catch(e => setGptAuthProbe({
        status: "unavailable",
        safe: true,
        starts_evolution: false,
        message: "GPT auth connection test failed without starting evolution",
        reason: String(e && e.message ? e.message : e),
      }));
  }, [baseUrl]);

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

  // Find config defaults for table/chart highlighting. Empty target_score means no early stop.
  const mddCap = Number((configSpec.find(f => f.name === "mdd_cap")?.default) ?? 40);
  const minDailyTrades = Number((configSpec.find(f => f.name === "min_daily_trades")?.default) ?? 0.5);
  const targetScoreRaw = (configSpec.find(f => f.name === "target_score")?.default);
  const targetScore = (targetScoreRaw === "" || targetScoreRaw === null || targetScoreRaw === undefined) ? 1.0 : Number(targetScoreRaw);

  const pct = state.max_generations > 0 ? Math.min(100, (state.current_gen / state.max_generations) * 100) : 0;
  const isIdle = state.status === "idle" && state.generations.length === 0 && !running;
  const activeRoute = routeContract(activeTab);
  const activeEvolutionRoute = activeTab === "evolution" ? evolutionSubtabContract(activeEvolutionTab) : null;
  const ownerKey = activeTab === "evolution" && activeEvolutionTab !== "overview"
    ? (activeEvolutionTab === "workbench" ? "pro" : activeEvolutionTab)
    : activeTab;
  const activeOwner = pageOwnerContract(ownerKey);
  const shellRouteLabel = activeEvolutionRoute ? `${activeRoute.label} / ${activeEvolutionRoute.label}` : activeRoute.label;
  const shellDetailKey = activeEvolutionRoute ? `evolution/${activeEvolutionRoute.key}` : (activeRoute.key || activeTab);
  const shellMetrics = [
    { label: "route", value: activeEvolutionRoute ? activeEvolutionRoute.badge : (activeRoute.badge || activeTab) },
    { label: "owner", value: activeOwner.owner || "—" },
    { label: "status", value: state.status || "—" },
    { label: "run", value: selectedRun ? "archive" : "LIVE" },
  ];
  const currentDashboardPath = (typeof window !== "undefined" && window.location && window.location.pathname) || "/ui/evolution";
  const v3PreviewHref = `${currentDashboardPath || "/ui/evolution"}?dashboard_version=v3`;
  const v4PreviewHref = `${currentDashboardPath || "/ui/evolution"}?dashboard_version=v4`;

  return (
    <div className="stom-app-shell">

      {/* ============= TOP BAR ============= */}
      <header className="stom-shell">
        <div className="stom-shell-top">
          <div className="stom-shell-brand">
            <Logo />
            <div className="stom-shell-title">
              <h1>STOM AI · 조건식 AI 연구 대시보드 (Legacy)</h1>
              <span className="mono">
                Legacy 운영 · autonomous_strategy_loop · contract_v{health.contract_version ?? state.contract_version ?? 1}
              </span>
            </div>
            <nav className="stom-pagenav mono" aria-label="현재 위치">
              <span className="stom-pagenav-item stom-pagenav-active"
                    title={activeRoute.contract || "현재 보고 있는 탭"}>
                {activeRoute.icon} {shellRouteLabel}
              </span>
            </nav>
          </div>

          <div className="stom-shell-controls">
            <ThemeToggle theme={theme} onChange={setTheme} />
            <a className="btn ghost sm mono"
               data-dashboard-preview="v3"
               href={v3PreviewHref}
               title="Legacy 화면은 유지하고 현재 경로를 V3 리모델 프리뷰로 1회 열기">
              V3 Preview
            </a>
            <a className="btn ghost sm mono"
               data-dashboard-preview="v4"
               href={v4PreviewHref}
               title="기본(V4 graph-first) 대시보드로 이동">
              V4 기본 화면
            </a>
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
          <UiStateBlock kind="info" compact title={activeRoute.group || "Dashboard"} detail={shellDetailKey}>
            <b>{activeOwner.owner || activeRoute.label}</b> · {activeRoute.contract || "STOM dashboard route"}
            <span className="stom-route-boundary">비소유: {activeOwner.notOwner || "—"}</span>
          </UiStateBlock>
          <MetricList items={shellMetrics} />
        </div>

        {/* ===== 탭 내비게이션 (전 탭 공통, 브랜드 행 바로 아래) ===== */}
        <TabNav activeTab={activeTab} onSelect={onTopTabSelect} />
        {activeTab === "evolution" && (
          <EvolutionSubtabNav activeSubtab={activeEvolutionTab} onSelect={onEvolutionSubtabSelect} />
        )}

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
        : activeTab === "evolution" && activeEvolutionTab === "process" ? (
        <ErrorBoundary>
          <main className="native-process-page" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <ProcessFlowPanel state={state} />
          </main>
        </ErrorBoundary>
      ) : activeTab === "evolution" && activeEvolutionTab === "records" ? (
        <ErrorBoundary>
          <main style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} />
            <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} />
            <AbPairCompareView baseUrl={baseUrl} wsStatus={wsStatus} />
            <CellHeatmap baseUrl={baseUrl} wsStatus={wsStatus} />
            <HoldoutFunnel baseUrl={baseUrl} wsStatus={wsStatus} />
            <ResearchIndexPage baseUrl={baseUrl} onNavigate={onDashboardNavigate} />
          </main>
        </ErrorBoundary>
      ) : activeTab === "evolution" && activeEvolutionTab === "lab" ? (
        <ErrorBoundary>
          <LabPage baseUrl={baseUrl} onNavigate={onDashboardNavigate} />
        </ErrorBoundary>
      ) : activeTab === "evolution" && activeEvolutionTab === "workbench" ? (
        <ErrorBoundary>
          <ProPage baseUrl={baseUrl} onNavigate={onDashboardNavigate} />
        </ErrorBoundary>
      ) : activeTab === "evolution" && activeEvolutionTab === "verdict" ? (
        <ErrorBoundary>
          <VerdictPanel baseUrl={baseUrl} onNavigate={onDashboardNavigate} />
        </ErrorBoundary>
      ) : (
        <main style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* 승인 export 결과 배너(final_approval 게이트는 ApprovalDialog가 유지) */}
          <ExportStatusBanner reply={lastReply} />

          <_EvoSection storageKey="stom_evo_live" label={<SectionLabel text="조건식 AI Live Monitor" />}>
            <CurrentGenPanel state={state} />
            <ActiveStrategyPanel state={state} baseUrl={baseUrl} onViewCode={onViewCodeByGen} />
            <PhaseTimeline state={state} />
            <ProcessFlowPanel state={state} />
            <PhaseDetailPanel state={state} wsStatus={wsStatus} />
          </_EvoSection>
          <_EvoSection storageKey="stom_evo_gate_engine" label={<SectionLabel text="설정 · 게이트 · 백테스트 엔진 요약" />}>
            <ResearchCriteriaBanner state={state} baseUrl={baseUrl} />
            <ResearchGlossaryPanel />
            <ActiveConfigPanel state={state} />
            <EnginePanel state={state} wsStatus={wsStatus} />
            <CostPanel state={state} cap={50000} />
          </_EvoSection>
          {isIdle && (
            <IdleState onStart={() => setSettingsOpen(true)} configSpec={configSpec} state={state} onNavigate={onDashboardNavigate} />
          )}
          <_EvoSection storageKey="stom_evo_researchnav" label={<SectionLabel text="연구실 종합 · 탐색/변수/검증" />}>
            {/* <ResearchLabPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id || ""} /> is mounted only inside LabPage; Home keeps summary/nav cards to avoid duplicate Lab ownership. */}
            <ResearchSuiteCards
              state={state}
              onNavigate={onDashboardNavigate}
              onOpenWorkbench={() => onEvolutionSubtabSelect("workbench")}
            />
          </_EvoSection>


          <div className="grid-main">
            <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>

              <FitnessChart state={state} target={targetScore} />
              <ProfitChart state={state} targetPct={0} />
              <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id} />
              {/* O1 — 백테 상세(일별손익 막대 + 누적수익곡선): 선택 세대의 per-trade CSV 시계열 재현 */}
              {/* #65 P1 — externalSelGen: 세대표 '백테상세' 클릭이 선택 세대를 여기로 동기화 */}
              <BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={state}
                                   externalSelGen={selectedDetailGen} />
              <EvolutionGuiParityPanel baseUrl={baseUrl} wsStatus={wsStatus} state={state}
                                       externalSelGen={selectedDetailGen} />
              <QualityTrendChart state={state} />
              {/* 🏆 명예의 전당 — 인간 벤치마크(19전략) + AI 생성 통합(목표선 가시화) */}
              <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
              <_EvoSection storageKey="stom_evo_strategy" label={<SectionLabel text="Strategy / Prompt" />}>
                <GenerationsTable state={state} mddCap={mddCap} minDailyTrades={minDailyTrades}
                                  onViewCode={(g) => setCodeViewGen(g)}
                                  onSelectDetail={(genNo) => {
                                    // v5.13.0(D1) — 차트가 표보다 위에 있어 "무반응"으로 보였다.
                                    //   선택 반영 후 백테 상세 차트로 스크롤해 갱신을 보여준다.
                                    setSelectedDetailGen(genNo);
                                    try {
                                      const el = document.getElementById("backtest-detail-chart");
                                      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                                    } catch (e) {}
                                  }} />
              </_EvoSection>
              {/* History owns Compare; overview keeps navigation only to avoid duplicate result owners. */}
              <_EvoSection storageKey="stom_evo_historynav" label={<SectionLabel text="History / Compare" />}>
                <div className="research-empty" style={{ textAlign: "left" }}>
                  Compare와 run/gen ResultDetail은 히스토리 탭에서만 렌더링합니다.
                  <div style={{ marginTop: 10 }}>
                    <button className="btn ghost sm" onClick={() => onEvolutionSubtabSelect("records")}>히스토리에서 Compare 열기</button>
                  </div>
                </div>
              </_EvoSection>
              {/* 트랙 L — 진화 결과 분석 시각화(세대 멀티라인·산점도·상위표, GET /bt/evo_gens) */}
              <_EvoSection storageKey="stom_evo_genanalytics" label={<SectionLabel text="Generation Analytics" />}>
                <ErrorBoundary><EvolutionAnalysisPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id || ""} onOpenWorkbench={() => onEvolutionSubtabSelect("workbench")} /></ErrorBoundary>
              </_EvoSection>
            </div>
            <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>

              {/* ── 분석 패널 묶음 (P1~P5 live page_data 소비, demo 배지 규약) ── */}
              <_EvoSection storageKey="stom_evo_analysis" label={<SectionLabel text="진화 분석 · P1~P5" />}>
                {/* P2b-2 — 가정 루프(세운 가정+채택/기각 판정) 가시화. 판정된 가정이
                    있는 세대가 없으면(토글 OFF/구 상태) 패널이 null 반환해 미표시. */}
                <HypothesisPanel state={state} />
                <ConditionDiscoveryPanel state={state} wsStatus={wsStatus} />
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
        configSpecStatus={configSpecStatus}
        onGptAuthTest={onGptAuthTest}
        gptAuthProbe={gptAuthProbe}
        disabled={running || (!isDemoSrc && configSpecStatus && !configSpecStatus.live)}
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

      <section
        data-safety-boundary="v2-research-only"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
          gap: 10,
          marginTop: 18,
        }}
      >
        {[
          ["실거래/주문 기능 없음", "No Live Order"],
          ["브로커 로그인 없음", "No Broker Login"],
          ["계좌/자산 연동 없음", "No Account Trading"],
          ["연구 전용", "Research Only"],
          ["Human Approval Gate", "승인 후 Export"],
          ["Append-Only Audit", "불변 감사 로그"],
        ].map(([title, detail]) => (
          <div key={title} className="panel" style={{ padding: "10px 12px" }}>
            <b>{title}</b>
            <div className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5, marginTop: 4 }}>{detail}</div>
          </div>
        ))}
      </section>
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
function EvolutionSubtabNav({ activeSubtab, onSelect }) {
  return (
    <nav role="tablist" aria-label="조건식 AI 하위 탭" className="evolution-subtabnav">
      {EVOLUTION_SUBTAB_CONTRACTS.map(tab => {
        const active = activeSubtab === tab.key;
        return (
          <button
            key={tab.key}
            role="tab"
            aria-selected={active}
            className={"evolution-subtab" + (active ? " active" : "")}
            onClick={() => onSelect(tab.key)}
            title={tab.contract}
          >
            <span className="stom-tab-ico" aria-hidden="true">{tab.icon}</span>
            <span>{tab.label}</span>
            <span className="stom-tab-badge mono">{tab.badge}</span>
          </button>
        );
      })}
    </nav>
  );
}

function ResearchSuiteCards({ state, onNavigate, onOpenWorkbench }) {
  const cards = [
    { key: "lab", label: "연구실", badge: "LAB", body: "탐색 히트맵·Edge Ratio·변수 중요도·상관관계·변수 조합·검증의 단일 소유 화면" },
    { key: "records", label: "히스토리", badge: "HISTORY", body: "모든 run/gen 백테스트 결과, 조건식, ResultDetail, Compare, 연구 기록 검색" },
    { key: "workbench", label: "분석 워크벤치", badge: "WORK", body: "후보 조건식 정밀 분석과 명예의 전당 후보 확인" },
    { key: "hof", label: "명예의 전당", badge: "HOF", body: "실시간/과거 백테스트에서 좋은 결과를 Workbench/HOF 기준으로 재검토" },
    { key: "backtest", label: "백테스트", badge: "BT", body: "조건식 실행·최적화·WFO·결과 라이브러리 확인" },
    { key: "simulation", label: "차트 리플레이", badge: "SIM", body: "조건식 신호와 실제 차트 흐름을 재생해 진입/청산 맥락 점검" },
  ];
  const runLabel = state?.run_id || "LIVE";
  return (
    <div className="research-suite-cards" aria-label="조건식 AI 연구 기능 네비게이션">
      <div className="research-suite-head">
        <b>연구 기능 위치 요약</b>
        <span className="mono">run={runLabel} · Home은 요약/이동만 제공하고 Lab/History/Workbench 내부 화면은 중복 렌더링하지 않습니다.</span>
      </div>
      <div className="research-suite-grid">
        {cards.map((card) => {
          const open = () => {
            if (card.key === "hof" || card.key === "workbench") {
              if (typeof onOpenWorkbench === "function") onOpenWorkbench();
              else if (typeof onNavigate === "function") onNavigate("workbench");
              return;
            }
            if (typeof onNavigate === "function") onNavigate(card.key);
          };
          return (
            <button key={card.key} type="button" className="research-suite-card" onClick={open}>
              <span className="mono research-suite-badge">{card.badge}</span>
              <b>{card.label}</b>
              <span>{card.body}</span>
            </button>
          );
        })}
      </div>
    </div>
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

function IdleState({ onStart, configSpec, state, onNavigate }) {
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
          <strong style={{ color: "var(--amber)" }}>조건식 AI는 시작 전에도 핵심 구조를 보여줍니다.</strong>
          {" "}아래 <span className="mono" style={{ color: "var(--ink-0)" }}>▸ 조건식 AI 시작 설정 열기</span>를 누르면
          생성→백테스트→채점→부검 흐름, 엔진 메트릭, 자본곡선, 점수 분해, 부검 스트리밍이 실시간으로 보입니다.
        </span>
        <button className="btn primary" style={{ marginLeft: "auto" }} onClick={onStart}>
          ▸ 시작
        </button>
      </div>
      <div className="panel" style={{ marginBottom: 14 }}>
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>조건식 발굴 프로세스</div>
        </div>
        <div className="panel-bd">
          <ProcessFlowPanel state={state || INITIAL_STATE} />
          <div className="phase3-home-links">
            {[
              { key: "backtest", label: "백테스트", text: "개별 조건식 백테스트와 진화 중 백테스트 결과 확인" },
              { key: "simulation", label: "차트 리플레이", text: "진입/청산 지점을 차트에서 다시 확인" },
              { key: "records", label: "히스토리", text: "모든 run/gen 결과·Compare·기록 검색" },
              { key: "lab", label: "연구실", text: "탐색 히트맵·Edge Ratio·변수 분석·검증을 한 화면에서 확인" },
              { key: "workbench", label: "분석 워크벤치", text: "후보 분석과 HoF 비교" },
              { key: "verdict", label: "결정 감사", text: "append-only 결정 이력 확인" },
            ].map(item => (
              <button key={item.key} className="phase3-home-link" type="button"
                      onClick={() => onNavigate && onNavigate(item.key)}>
                <b>{item.label}</b>
                <span>{item.text}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 }}>
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>Welcome</div>
        </div>
        <div className="panel-bd" style={{ padding: "28px 24px" }}>
          <h2 style={{ fontSize: 22, marginBottom: 10, letterSpacing: "-0.01em" }}>
            조건식 AI 루프를 시작할 준비가 되었습니다.
          </h2>
          <p style={{ color: "var(--ink-1)", lineHeight: 1.6, marginBottom: 22, fontSize: 13 }}>
            AI가 한국 주식 매수/매도 전략 코드를 자동 생성·백테스트·채점·반복합니다.
            각 세대의 부검(autopsy)이 다음 세대 생성기에 피드백되어 조건식이 점진적으로 진화합니다.
            <br /><br />
            <span style={{ color: "var(--ink-2)" }}>
              목표 점수와 MDD 상한을 동시에 만족하면 우승 후보로 표시되고,
              <br />
              운영 export/final approval은 연구 확인 화면과 분리된 별도 승인 절차입니다.
            </span>
          </p>
          <button className="btn primary lg" onClick={onStart}>
            ▸ 조건식 AI 시작 설정 열기
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
              { n: 1, k: "조건식 만들기", d: "LLM이 이전 실패 원인과 좋은 예시를 참고해 매수/매도 규칙을 작성합니다." },
              { n: 2, k: "과거 데이터로 검증", d: "백테스트 엔진이 지정 기간의 종목 데이터를 돌려 손익·낙폭·거래 빈도를 계산합니다." },
              { n: 3, k: "점수 계산", d: "수익, 위험(MDD), 우상향, 일평균 거래, 손익비를 목표 공식에 맞춰 점수화합니다." },
              { n: 4, k: "통과 기준 확인", d: "목표 적합도, MDD 상한, 일평균 거래 하한을 만족하는지 확인합니다." },
              { n: 5, k: "실패 원인 요약", d: "왜 떨어졌는지 쉬운 말로 정리해 다음 세대 프롬프트에 넣습니다." },
              { n: 6, k: "다시 개선", d: "이름이 붙은 run·세대·백테스트 결과를 저장해 나중에 다시 찾을 수 있게 합니다." },
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
