/* dashboard-v4-shell.jsx — V4 대시보드 셸 (graph-first 리모델, opt-in)
 *
 *   V2 운영 대시보드(app.jsx 의 App)는 그대로 두고, frontend/v4.html 이 이 셸을
 *   window.DashboardV4Shell 로 직접 마운트한다(lab/pro/verdict.html 의 이름-마운트 패턴).
 *   같은 컴파일 번들(bundle/app.js)·단일 React(window.React)를 공유하므로 별도 번들이 없다.
 *
 *   원칙: 컴포넌트를 새로 만들지 않고 기존 V2 컴포넌트를 재배치한다. graph-first 는
 *   .v4-root 스코프의 v4.css 레이아웃으로 달성한다(V2 styles.css 회귀 0).
 *
 *   Phase 1: 셸 골격(상단바·테마·탭 네비·백엔드 연결 검증) + 탭 본문 placeholder.
 *   후속 phase 에서 각 탭 본문을 기존 V2 컴포넌트로 채운다.
 */
// dual-safe ESM import (esbuild bundle 경로에서 그대로 해석). KEEP on ONE physical line.
import { ConnBadge, StatusBadge } from "./panels.jsx";
// ErrorBoundary 재사용(단일 크래시가 전체 언마운트되지 않도록). KEEP on ONE physical line.
import { ErrorBoundary } from "./app.jsx";
// 탭 본문(phase 별 추가) — 기존 V2 컴포넌트 재배치. KEEP each on ONE physical line.
import { V4ResearchLive } from "./v4-research.jsx";
const { useState: useState_v4, useEffect: useEffect_v4 } = React;

// V4 IA — 상단 6탭(핸드오프 §7). 본문은 phase 별로 기존 컴포넌트로 채운다.
const V4_TABS = [
  { key: "research", label: "Research Live", badge: "LIVE", hint: "실시간 연구 관찰 · 대형 fitness/equity 차트" },
  { key: "backtest", label: "Backtest", badge: "BT", hint: "전략 실행 · equity/underwater/rolling 대형 차트" },
  { key: "replay", label: "Replay", badge: "SIM", hint: "캔들 리플레이 · 신호 로그" },
  { key: "lab", label: "Lab", badge: "LAB", hint: "탐색 히트맵 · Edge Ratio · 변수 분석" },
  { key: "workbench", label: "Workbench", badge: "WORK", hint: "후보 비교 · 명예의 전당" },
  { key: "audit", label: "Audit", badge: "AUDIT", hint: "append-only 결정 감사 · 안전 게이트" },
];

function DashboardV4Shell({ baseUrl: baseUrlProp }) {
  const [baseUrl] = useState_v4(() => baseUrlProp || DEFAULT_BASE);
  const [theme, setTheme] = useState_v4(() => localStorage.getItem("stom_theme") || "dark");
  const [activeTab, setActiveTab] = useState_v4("research");

  // 테마: V2 와 동일한 data-theme 메커니즘·토큰 재사용(app.jsx:127-130).
  useEffect_v4(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stom_theme", theme);
  }, [theme]);

  const { state, health, wsStatus, send } = useBackend(baseUrl);
  const active = V4_TABS.find(t => t.key === activeTab) || V4_TABS[0];

  return (
    <div className="v4-root" data-v4-tab={activeTab}>
      <header className="v4-topbar">
        <div className="v4-brand">
          <span className="v4-brand-mark">STOM</span>
          <span className="v4-brand-sub mono">V4 · graph-first research terminal</span>
        </div>
        <div className="v4-controls">
          <div className="theme-toggle" role="group" aria-label="테마">
            <button className={theme === "dark" ? "active" : ""} onClick={() => setTheme("dark")} data-tip="다크 모드">Dark</button>
            <button className={theme === "light" ? "active" : ""} onClick={() => setTheme("light")} data-tip="라이트 모드">Light</button>
          </div>
          <ConnBadge health={health} wsStatus={wsStatus} />
          <StatusBadge status={state.status} />
          <a className="btn ghost sm mono" href="/ui/" title="V2 운영 대시보드로">← V2</a>
        </div>
      </header>

      <nav className="v4-tabnav" role="tablist" aria-label="V4 탭">
        {V4_TABS.map(tab => (
          <button
            key={tab.key}
            role="tab"
            aria-selected={activeTab === tab.key}
            className={"v4-tab" + (activeTab === tab.key ? " active" : "")}
            onClick={() => setActiveTab(tab.key)}
            title={tab.hint}
          >
            <span className="v4-tab-label">{tab.label}</span>
            <span className="v4-tab-badge mono">{tab.badge}</span>
          </button>
        ))}
      </nav>

      <main className="v4-main">
        <ErrorBoundary>
          {activeTab === "research" ? (
            <V4ResearchLive baseUrl={baseUrl} state={state} wsStatus={wsStatus} send={send} />
          ) : (
            <div className="v4-placeholder">
              <div className="v4-placeholder-badge mono">{active.badge}</div>
              <h2>{active.label}</h2>
              <p>{active.hint}</p>
              <p className="mono v4-placeholder-note">
                base={baseUrl} · ws={wsStatus} · status={state.status || "—"} ·
                이 탭은 후속 phase 에서 기존 V2 컴포넌트로 채웁니다.
              </p>
            </div>
          )}
        </ErrorBoundary>
      </main>
    </div>
  );
}

Object.assign(window, { DashboardV4Shell });
// dual-safe ESM export (concat 경로에서 stripped, bundle 경로에서 실제 모듈 export). KEEP on ONE physical line.
export { DashboardV4Shell };
