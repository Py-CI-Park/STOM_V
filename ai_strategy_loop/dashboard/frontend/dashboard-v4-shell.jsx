/* dashboard-v4-shell.jsx — V4 대시보드 셸 (프로토타입 IA: 좌측 레일 + graph-first)
 *
 *   승인된 리디자인 프로토타입(design-system/v4-redesign-prototype.html)을 구현한다.
 *   frontend/v4.html 이 window.DashboardV4Shell 로 이름-마운트(lab/pro/verdict 패턴),
 *   같은 컴파일 번들(bundle/app.js)·단일 React 공유. V2 기본 경로는 불변(opt-in).
 *
 *   구조: 좌측 슬림 레일(7뷰) + 상단바(브랜드·안전 strip·연결/상태·BASE·테마·run 제어)
 *   + 뷰 스테이지. run 제어(설정/시작/정지·RUN 셀렉터)는 app.jsx:76-119/201-233 패턴 재사용.
 *   BASE 는 ?base= 쿼리 1회 오버라이드(wt-dev 백엔드 실데이터 연동/스크린샷 자동화용)
 *   → localStorage(cross-origin 캐시는 same-origin 으로 마이그레이션) → DEFAULT_BASE.
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { ConnBadge, StatusBadge } from "./panels.jsx";
import { ErrorBoundary } from "./app.jsx";
import { SettingsModal } from "./settings.jsx";
import { CodeViewer } from "./code-viewer.jsx";
import { V4RunControls } from "./v4-run-controls.jsx";
import { V4ResearchLive } from "./v4-research.jsx";
import { V4Backtest } from "./v4-backtest.jsx";
import { V4Replay } from "./v4-replay.jsx";
import { V4History } from "./v4-history.jsx";
import { V4Lab } from "./v4-lab.jsx";
import { V4Workbench } from "./v4-workbench.jsx";
import { V4Audit } from "./v4-audit.jsx";
const { useState: useState_v4, useEffect: useEffect_v4, useCallback: useCallback_v4 } = React;

// V4 IA — 좌측 레일 7뷰(승인 프로토타입). 아이콘은 stroke currentColor 인라인 SVG.
const V4_TABS = [
  { key: "research", label: "Live", full: "Research Live", badge: "LIVE", hint: "조건식 자율 진화 · 실시간 관찰" },
  { key: "backtest", label: "Backtest", full: "Backtest", badge: "BT", hint: "전략 실행 · 결과 리포트" },
  { key: "replay", label: "Replay", full: "Replay", badge: "SIM", hint: "캔들 리플레이 · 신호 맥락" },
  { key: "history", label: "History", full: "History", badge: "HIST", hint: "run/gen 아카이브 · Compare · 연구 기록 검색" },
  { key: "lab", label: "Lab", full: "Lab", badge: "LAB", hint: "탐색 히트맵 · Edge Ratio · 변수 분석" },
  { key: "workbench", label: "Bench", full: "Workbench", badge: "WORK", hint: "후보 비교 · 명예의 전당" },
  { key: "audit", label: "Audit", full: "Audit", badge: "AUDIT", hint: "append-only 결정 감사 · 안전 게이트" },
  { key: "context", label: "Context", full: "AI Context Pack", badge: "PACK", hint: "모델에 전달된 컨텍스트 · 복사 가능" },
];
const V4_TAB_KEYS = V4_TABS.map(t => t.key);

function v4InitialTab() {
  try {
    const t = new URLSearchParams(window.location.search).get("tab");
    if (t && V4_TAB_KEYS.includes(t)) return t;
  } catch (e) {}
  return "research";
}

// BASE 결정: ?base= 1회 오버라이드(wt-dev 실데이터 연동) → localStorage(cross-origin
//   캐시는 same-origin 폴백) → prop(origin) → DEFAULT_BASE. ?base= 는 영속하지 않는다.
function v4InitialBase(propBase) {
  try {
    const q = new URLSearchParams(window.location.search).get("base");
    if (q && /^https?:\/\//.test(q)) return new URL(q).origin;
  } catch (e) {}
  try {
    const cached = localStorage.getItem("stom_base_url");
    const here = (window.location && window.location.origin) || "";
    if (cached && here.startsWith("http") && new URL(cached).origin === here) return cached;
  } catch (e) {}
  return propBase || DEFAULT_BASE;
}

function V4RailIcon({ name }) {
  const p = { width: 18, height: 18, viewBox: "0 0 18 18", fill: "none", stroke: "currentColor", strokeWidth: 1.4 };
  if (name === "research") return (<svg {...p}><path d="M2 12 L6 8 L9 10 L15 3" /><circle cx="15" cy="3" r="1.3" fill="currentColor" stroke="none" /></svg>);
  if (name === "backtest") return (<svg {...p}><rect x="2" y="9" width="3" height="6" rx="1" /><rect x="7.5" y="5" width="3" height="10" rx="1" /><rect x="13" y="2" width="3" height="13" rx="1" /></svg>);
  if (name === "replay") return (<svg {...p}><path d="M3 4 L3 14" /><path d="M7 6 L7 12" /><path d="M11 3 L11 15" /><path d="M15 7 L15 11" /></svg>);
  if (name === "history") return (<svg {...p}><circle cx="9" cy="9" r="6.5" /><path d="M9 5.5 V9 L12 10.5" /></svg>);
  if (name === "lab") return (<svg {...p}><rect x="2.5" y="2.5" width="4" height="4" rx="1" /><rect x="11.5" y="2.5" width="4" height="4" rx="1" /><rect x="2.5" y="11.5" width="4" height="4" rx="1" /><rect x="11.5" y="11.5" width="4" height="4" rx="1" /></svg>);
  if (name === "workbench") return (<svg {...p}><path d="M3 6 h12" /><path d="M3 10 h12" /><path d="M3 14 h7" /><circle cx="13" cy="3.5" r="1.4" /></svg>);
  if (name === "audit") return (<svg {...p}><path d="M9 2 L15 5 V9 C15 12.5 12.5 15 9 16 C5.5 15 3 12.5 3 9 V5 Z" /><path d="M6.5 9 L8.3 10.8 L11.5 7" /></svg>);
  return (<svg {...p}><rect x="3" y="3" width="12" height="12" rx="2" /><path d="M6 7 h6 M6 10 h4" /></svg>);
}

function V4ThemeToggle({ theme, onChange }) {
  return (
    <div className="theme-toggle" role="group" aria-label="테마">
      <button className={theme === "dark" ? "active" : ""} onClick={() => onChange("dark")} data-tip="다크 모드">Dark</button>
      <button className={theme === "light" ? "active" : ""} onClick={() => onChange("light")} data-tip="라이트 모드">Light</button>
    </div>
  );
}

function V4BaseControl({ value, onChange, onApply, onReconnect }) {
  return (
    <div className="v4-base">
      <span className="mono v4-base-lbl">BASE</span>
      <input className="toolbar-input" value={value} spellCheck={false}
             onChange={e => onChange(e.target.value)}
             onKeyDown={e => { if (e.key === "Enter") onApply(); }} />
      <button className="btn ghost sm" onClick={onApply} data-tip="Base URL 적용 후 재연결">적용</button>
      <button className="btn ghost sm" onClick={onReconnect} data-tip="현재 URL로 재연결">↻</button>
    </div>
  );
}

function DashboardV4Shell({ baseUrl: baseUrlProp }) {
  const [baseUrl, setBaseUrl] = useState_v4(() => v4InitialBase(baseUrlProp));
  const [pendingBase, setPendingBase] = useState_v4(baseUrl);
  const [theme, setTheme] = useState_v4(() => localStorage.getItem("stom_theme") || "dark");
  const [activeTab, setActiveTab] = useState_v4(() => v4InitialTab());
  const [replayVisited, setReplayVisited] = useState_v4(() => v4InitialTab() === "replay");

  useEffect_v4(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stom_theme", theme);
  }, [theme]);
  useEffect_v4(() => { if (activeTab === "replay") setReplayVisited(true); }, [activeTab]);

  const { state: liveState, health, wsStatus, configSpec, configSpecStatus, send, lastReply, reconnect } = useBackend(baseUrl);
  const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // ---- run 셀렉터 데이터(app.jsx:76-119 패턴): LIVE 또는 과거 run 재구성 ----
  const [selectedRun, setSelectedRun] = useState_v4("");
  const [runList, setRunList] = useState_v4([]);
  const [fetchedRunState, setFetchedRunState] = useState_v4(null);

  useEffect_v4(() => {
    if (isDemo || !baseUrl) { setRunList([]); return; }
    let cancelled = false;
    // 10s: 대형 아카이브(run 수백 개)·연구 실행 중 CPU 포화 백엔드의 콜드 응답이 3s 를
    //   넘길 수 있다(cross-origin 데이터 연동 시나리오 실측) — V2 기본(3s)보다 여유.
    fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      })
      .catch(() => { if (!cancelled) setRunList([]); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, liveState.run_id, liveState.status]);

  const fetchRunState = useCallback_v4(() => {
    if (!selectedRun || isDemo || !baseUrl) { setFetchedRunState(null); return; }
    fetch(baseUrl + "/run_state?run_id=" + encodeURIComponent(selectedRun), { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => setFetchedRunState(j))
      .catch(() => setFetchedRunState(null));
  }, [baseUrl, selectedRun, isDemo]);
  useEffect_v4(() => {
    if (!selectedRun) { setFetchedRunState(null); return; }
    fetchRunState();
    const id = setInterval(fetchRunState, 30000);
    return () => clearInterval(id);
  }, [fetchRunState, selectedRun]);

  const state = (selectedRun && fetchedRunState) ? fetchedRunState : liveState;
  const running = state.status === "running" || state.status === "stopping";
  const runId = state.run_id || "";

  // ---- 시작/정지/설정 (app.jsx:201-233 패턴) ----
  const [settingsOpen, setSettingsOpen] = useState_v4(false);
  const [gptAuthProbe, setGptAuthProbe] = useState_v4(null);
  const [codeViewGen, setCodeViewGen] = useState_v4(null);

  const onStart = useCallback_v4((config) => { send({ action: "start", config }); setSettingsOpen(false); }, [send]);
  const onStop = useCallback_v4(() => { send({ action: "stop" }); }, [send]);
  const onGptAuthTest = useCallback_v4(() => {
    setGptAuthProbe({ status: "testing", message: "GPT auth proxy test running" });
    fetch(baseUrl + "/gpt_auth/test", { method: "POST", signal: AbortSignal.timeout(8000) })
      .then(r => r.json().then(j => ({ http_ok: r.ok, ...j })))
      .then(j => setGptAuthProbe(j))
      .catch(e => setGptAuthProbe({
        status: "unavailable", safe: true, starts_evolution: false,
        message: "GPT auth connection test failed without starting evolution",
        reason: String(e && e.message ? e.message : e),
      }));
  }, [baseUrl]);
  const onViewCodeByGen = useCallback_v4((genNo) => {
    const g = (state.generations || []).find(x => x.gen_no === genNo);
    if (g) setCodeViewGen(g);
  }, [state.generations]);

  // config 파생값(app.jsx:241-244 패턴): 차트 gate 라인·세대표 하이라이트 기준
  const mddCap = Number((configSpec.find(f => f.name === "mdd_cap")?.default) ?? 40);
  const minDailyTrades = Number((configSpec.find(f => f.name === "min_daily_trades")?.default) ?? 0.5);
  const targetScoreRaw = (configSpec.find(f => f.name === "target_score")?.default);
  const targetScore = (targetScoreRaw === "" || targetScoreRaw === null || targetScoreRaw === undefined) ? 1.0 : Number(targetScoreRaw);

  const selectTab = (key) => {
    setActiveTab(key);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", key);
      window.history.replaceState(null, "", url.pathname + url.search);
    } catch (e) {}
  };
  const active = V4_TABS.find(t => t.key === activeTab) || V4_TABS[0];

  return (
    <div className="v4-root" data-v4-tab={activeTab}>
      {/* ===== 좌측 레일 ===== */}
      <aside className="v4-rail" aria-label="V4 내비게이션">
        <div className="v4-rail-logo" title="STOM V4">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M2 15 L6 12 L9 13 L13 7 L18 3" stroke="var(--teal)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /><circle cx="18" cy="3" r="1.8" fill="var(--violet)" /></svg>
        </div>
        {V4_TABS.map(tab => (
          <button key={tab.key} role="tab" aria-selected={activeTab === tab.key}
                  className={"v4-rail-item" + (activeTab === tab.key ? " active" : "")}
                  onClick={() => selectTab(tab.key)} title={tab.full + " — " + tab.hint}>
            <V4RailIcon name={tab.key} />
            <span className="v4-ri-label">{tab.label}</span>
            <i className="v4-ri-dot"></i>
          </button>
        ))}
        <div className="v4-rail-spacer"></div>
        <a className="v4-rail-item" href="/ui/" title="V2 운영 대시보드로">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M11 3 L5 9 L11 15" /></svg>
          <span className="v4-ri-label">V2</span>
        </a>
      </aside>

      {/* ===== 워크스페이스 ===== */}
      <div className="v4-workspace">
        <header className="v4-topbar">
          <div className="v4-brand">
            <b>조건식 AI 연구 터미널</b>
            <span className="mono">V4 · autonomous_strategy_loop · contract v{health.contract_version ?? state.contract_version ?? 1}</span>
          </div>
          <div className="v4-safety" aria-label="안전 경계">
            {isDemo && <span className="v4-sfx demo">DEMO</span>}
            <span className="v4-sfx">실거래 없음</span>
            <span className="v4-sfx">브로커 없음</span>
            <span className="v4-sfx gate">HUMAN GATE</span>
            <span className="v4-sfx">APPEND-ONLY 감사</span>
          </div>
          <div className="v4-grow"></div>
          <V4BaseControl value={pendingBase} onChange={setPendingBase}
                         onApply={() => setBaseUrl(pendingBase)} onReconnect={reconnect} />
          <ConnBadge health={health} wsStatus={wsStatus} />
          <StatusBadge status={state.status} />
          <V4ThemeToggle theme={theme} onChange={setTheme} />
        </header>
        <div className="v4-controlbar">
          <div className="v4-view-title">
            <h2>{active.full}</h2>
            <span className="mono">{active.hint} · run={selectedRun ? "archive" : "LIVE"}{runId ? " · " + runId : ""}</span>
          </div>
          <V4RunControls
            running={running} state={state} isDemo={isDemo}
            runList={runList} selectedRun={selectedRun}
            onSelectRun={setSelectedRun} onRefreshRun={fetchRunState}
            onOpenSettings={() => setSettingsOpen(true)} onStop={onStop} />
        </div>

        <main className="v4-stage">
          {/* Replay keep-alive: 첫 방문 후 hidden 유지(언마운트 금지 — WS·재생 위치 보존) */}
          {replayVisited && (
            <div style={{ display: activeTab === "replay" ? undefined : "none" }}>
              <ErrorBoundary>
                <V4Replay baseUrl={baseUrl} wsStatus={wsStatus} />
              </ErrorBoundary>
            </div>
          )}
          {activeTab === "replay" ? null : (
            <ErrorBoundary>
              {activeTab === "research" ? (
                <V4ResearchLive baseUrl={baseUrl} state={state} wsStatus={wsStatus} send={send}
                                lastReply={lastReply} onViewCode={onViewCodeByGen}
                                onOpenSettings={() => setSettingsOpen(true)}
                                targetScore={targetScore} mddCap={mddCap} minDailyTrades={minDailyTrades} />
              ) : activeTab === "backtest" ? (
                <V4Backtest baseUrl={baseUrl} wsStatus={wsStatus} />
              ) : activeTab === "history" ? (
                <V4History baseUrl={baseUrl} wsStatus={wsStatus} onNavigate={selectTab} />
              ) : activeTab === "lab" ? (
                <V4Lab baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} onNavigate={selectTab} />
              ) : activeTab === "workbench" ? (
                <V4Workbench baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
              ) : activeTab === "audit" ? (
                <V4Audit baseUrl={baseUrl} onNavigate={selectTab} />
              ) : (
                <div className="v4-context">
                  {typeof window.AIContextPanel === "function" ? (
                    <window.AIContextPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} genNo={state.current_gen} />
                  ) : (
                    <div className="v4-placeholder">
                      <h2>AI Context Pack</h2>
                      <p className="mono">AIContextPanel 미로드 — 번들 재빌드 필요</p>
                    </div>
                  )}
                </div>
              )}
            </ErrorBoundary>
          )}
        </main>
      </div>

      {/* ===== 모달(중앙 호스팅) ===== */}
      <SettingsModal
        open={settingsOpen} onClose={() => setSettingsOpen(false)} onStart={onStart}
        configSpec={configSpec} configSpecStatus={configSpecStatus}
        onGptAuthTest={onGptAuthTest} gptAuthProbe={gptAuthProbe}
        disabled={running || (!isDemo && configSpecStatus && !configSpecStatus.live)} />
      <CodeViewer generation={codeViewGen} onClose={() => setCodeViewGen(null)} runId={runId} baseUrl={baseUrl} />
    </div>
  );
}

Object.assign(window, { DashboardV4Shell });
// dual-safe ESM export. KEEP on ONE physical line.
export { DashboardV4Shell };
