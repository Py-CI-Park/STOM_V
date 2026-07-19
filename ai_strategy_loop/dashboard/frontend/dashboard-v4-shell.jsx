/* dashboard-v4-shell.jsx — V4 대시보드 셸 (정본 IA: 좌측 레일 + graph-first)
 *
 *   승인된 리디자인 프로토타입(design-system/v4-redesign-prototype.html)을 구현한다.
 *   frontend/v4.html 이 window.DashboardV4Shell 로 이름-마운트(lab/pro/verdict 패턴),
 *   같은 컴파일 번들(bundle/app.js)·단일 React 공유. V2 기본 경로는 불변(opt-in).
 *
 *   구조: 좌측 슬림 레일(정본 6뷰) + 상단바(브랜드·안전 strip·연결/상태·BASE·테마·run 제어)
 *   + 뷰 스테이지. run 제어(설정/시작/정지·RUN 셀렉터)는 app.jsx:76-119/201-233 패턴 재사용.
 *   BASE 는 ?base= 쿼리 1회 오버라이드(wt-dev 실데이터 연동/스크린샷 자동화용)
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
import { V4Alpha } from "./v4-alpha.jsx";
import { V4Reports } from "./v4-reports.jsx";
import { V4Catalog } from "./v4-catalog.jsx";
import { fetchRunsShared } from "./runs-shared.jsx";
import { _resolveReplayDisplayState } from "./replay-lifecycle.jsx";
import { DASHBOARD_PAGE_OWNER_MATRIX } from "./dashboard-inventory.jsx";
import { AIContextPanel } from "./ai-context.jsx";
const { useState: useState_v4, useEffect: useEffect_v4, useCallback: useCallback_v4, useRef: useRef_v4 } = React;

// V5.P0 정본 IA owner: inventory matrix is the one canonical six-destination rail.
// Lab/Context remain explicit rollback-only identities; Catalog is Reports-owned when gated by prototype=catalog.
const V4_NORMAL_TABS = DASHBOARD_PAGE_OWNER_MATRIX;
const V4_LEGACY_ROLLBACK_QUERY = "v4_legacy_extras";
const V4_LEGACY_EXTRA_TABS = [
  { key: "lab", label: "Lab", full: "Lab prototype", badge: "LAB", hint: "비정본 prototype · 명시적 rollback 전용" },
  { key: "catalog", label: "카탈로그", full: "연구 카탈로그 prototype (P4)", badge: "P4", hint: "비권위적·비규범적 prototype · sealed P4 API/views 미완성" },
  { key: "context", label: "Context", full: "AI Context Pack prototype", badge: "PACK", hint: "비정본 prototype · 명시적 rollback 전용" },
  { key: "alpha", label: "Alpha", full: "Alpha Lab prototype", badge: "ALPHA", hint: "비정본 prototype · 명시적 rollback 전용" },
];
const V4_TAB_KEYS = V4_NORMAL_TABS.map(t => t.key);
const V4_LEGACY_TAB_KEYS = V4_NORMAL_TABS.concat(V4_LEGACY_EXTRA_TABS).map(t => t.key);
const V4_PROTOTYPE_TAB_KEYS = ["lab", "context", "alpha", "catalog"];
const V4_CONTEXT_DRAWER_QUERY = "v4_context";
const V4_PROTOTYPE_QUERY = "prototype";
const V4_REPORTS_PROTOTYPE_KEYS = ["catalog"];
let v4LegacyDestinationBootstrapped = false;
let v4LegacyStoredDestination = "";

function v4CanonicalDestinationKey(key) {
  const item = DASHBOARD_PAGE_OWNER_MATRIX.find(destination =>
    destination.key === key || destination.legacyAliases.includes(key) || destination.internalAliases.includes(key)
  );
  return item ? item.key : "";
}
function v4LegacyExtrasEnabled(search) {
  try {
    return new URLSearchParams(search === undefined ? window.location.search : search).get(V4_LEGACY_ROLLBACK_QUERY) === "1";
  } catch (e) { return false; }
}
function v4TabsForSession() {
  return v4LegacyExtrasEnabled() ? V4_NORMAL_TABS.concat(V4_LEGACY_EXTRA_TABS) : V4_NORMAL_TABS;
}
function v4TabFromPathname(pathname) {
  try {
    const parts = String(pathname || "").split("/").filter(Boolean);
    if (parts[0] !== "ui") return "";
    const leaf = parts[1] === "evolution" ? (parts[2] || "") : (parts[1] || "");
    if (parts[1] === "evolution" && !parts[2]) return "research";
    if (V4_PROTOTYPE_TAB_KEYS.includes(leaf)) return leaf;
    return v4CanonicalDestinationKey(leaf) || leaf;
  } catch (e) { return ""; }
}
function v4ReportsPrototype(search) {
  try {
    const value = new URLSearchParams(search === undefined ? window.location.search : search).get(V4_PROTOTYPE_QUERY);
    return V4_REPORTS_PROTOTYPE_KEYS.includes(value) ? value : "";
  } catch (e) { return ""; }
}
function v4PrototypeOwner(key) {
  return key === "catalog" ? "reports" : "";
}
function v4PrototypeForTab(tab, search) {
  const prototype = v4ReportsPrototype(search);
  return prototype && tab === v4PrototypeOwner(prototype) && !v4LegacyExtrasEnabled(search) ? prototype : "";
}
function v4RequestedDestination(location = window.location) {
  try {
    const prototype = v4ReportsPrototype(location.search || "");
    if (prototype) return prototype;
    const requested = new URLSearchParams(location.search || "").get("tab");
    return requested || v4TabFromPathname(location.pathname);
  } catch (e) { return ""; }
}
function v4CanonicalizeLegacyLocation(location = window.location, history = window.history) {
  try {
    const requested = v4RequestedDestination(location);
    const rollback = v4LegacyExtrasEnabled(location.search);
    if (!requested) return "";
    if (rollback && V4_PROTOTYPE_TAB_KEYS.includes(requested)) return requested;

    const canonical = v4CanonicalDestinationKey(requested);
    const isContext = requested === "context";
    const owner = canonical || v4PrototypeOwner(requested) ||
      (requested === "lab" ? "history" : requested === "alpha" ? "research" : "");
    if (!owner) return "";
    const url = new URL(location.href || (location.pathname + location.search), window.location.origin);
    if (isContext) {
      const pathOwner = v4CanonicalDestinationKey(v4TabFromPathname(location.pathname));
      url.searchParams.set("tab", pathOwner || "research");
      url.searchParams.set(V4_CONTEXT_DRAWER_QUERY, "1");
    } else {
      url.searchParams.set("tab", owner);
      if (requested === "alpha" || v4PrototypeOwner(requested)) {
        url.searchParams.delete(V4_PROTOTYPE_QUERY);
        url.searchParams.set(V4_PROTOTYPE_QUERY, requested);
      }
    }
    if (url.pathname + url.search !== location.pathname + location.search) {
      history.replaceState(null, "", url.pathname + url.search);
    }
    return owner;
  } catch (e) { return ""; }
}
function v4UnavailableDestination(location = window.location) {
  const requested = v4RequestedDestination(location);
  if (!requested) return "";
  if (v4LegacyExtrasEnabled(location.search) && V4_PROTOTYPE_TAB_KEYS.includes(requested)) return "";
  if (v4CanonicalDestinationKey(requested)) return "";
  return ["lab", "context", "alpha", "catalog"].includes(requested) ? "" : requested;
}
function v4Storage() {
  try { return window.localStorage; } catch (e) { return null; }
}
function v4StoredDestination() {
  if (v4LegacyDestinationBootstrapped) return v4LegacyStoredDestination;
  v4LegacyDestinationBootstrapped = true;
  const storage = v4Storage();
  if (!storage) return "";
  let primary = "";
  let evolution = "";
  try {
    primary = storage.getItem("stom_active_tab");
    evolution = storage.getItem("stom_active_evolution_tab");
  } catch (e) {
  } finally {
    try {
      storage.removeItem("stom_active_tab");
      storage.removeItem("stom_active_evolution_tab");
    } catch (e) {}
  }
  const requested = evolution && primary === "evolution" ? evolution : primary;
  v4LegacyStoredDestination = v4CanonicalDestinationKey(requested) ||
    (requested === "lab" ? "history" : requested === "alpha" ? "research" : v4PrototypeOwner(requested));
  return v4LegacyStoredDestination;
}
function v4InitialTab(tabKeys = V4_TAB_KEYS, storedDestination = "") {
  try {
    const requested = v4RequestedDestination();
    const rollback = v4LegacyExtrasEnabled();
    if (rollback && V4_PROTOTYPE_TAB_KEYS.includes(requested) && tabKeys.includes(requested)) return requested;
    const canonical = v4CanonicalDestinationKey(requested) ||
      (requested === "lab" ? "history" : requested === "alpha" ? "research" : v4PrototypeOwner(requested));
    if (canonical && tabKeys.includes(canonical)) return canonical;
    if (!requested && storedDestination && tabKeys.includes(storedDestination)) return storedDestination;
  } catch (e) {}
  return "research";
}

function _nextV4TabKey(keys, current, key) {
  const index = Math.max(0, keys.indexOf(current));
  if (key === "Home") return keys[0];
  if (key === "End") return keys[keys.length - 1];
  if (key === "ArrowRight") return keys[(index + 1) % keys.length];
  if (key === "ArrowLeft") return keys[(index - 1 + keys.length) % keys.length];
  return current;
}

// BASE 결정: ?base= 1회 오버라이드(wt-dev 실데이터 연동) → localStorage(cross-origin
//   캐시는 same-origin 폴백) → prop(origin) → DEFAULT_BASE. ?base= 는 영속하지 않는다.
function v4InitialBase(propBase) {
  try {
    const q = new URLSearchParams(window.location.search).get("base");
    if (q && /^https?:\/\//.test(q)) return new URL(q).origin;
  } catch (e) {}
  try {
    const storage = v4Storage();
    const cached = storage && storage.getItem("stom_base_url");
    const here = (window.location && window.location.origin) || "";
    if (cached && here.startsWith("http") && new URL(cached).origin === here) return cached;
  } catch (e) {}
  return propBase || DEFAULT_BASE;
}
function v4InitialTheme() {
  try {
    const storage = v4Storage();
    return (storage && storage.getItem("stom_theme")) || "dark";
  } catch (e) { return "dark"; }
}

// 현재 로드된 번들 빌드 지문(app.js?v=…)을 런타임에 파싱 — 사용자가 최신 빌드 여부를 확인.
//   빌드 스크립트가 content-hash ?v= 를 HTML script src 에 주입하므로 별도 빌드 변경 불필요.
function v4BundleVersion() {
  try {
    const src = Array.from(document.querySelectorAll("script[src]"))
      .map(e => e.src).find(s => /\/app\.js\?v=/.test(s));
    if (src) { const m = src.match(/[?&]v=([0-9A-Za-z._-]+)/); if (m) return m[1]; }
  } catch (e) {}
  return "";
}

function V4RailIcon({ name }) {
  const p = { width: 18, height: 18, viewBox: "0 0 18 18", fill: "none", stroke: "currentColor", strokeWidth: 1.4 };
  if (name === "research") return (<svg {...p}><path d="M2 12 L6 8 L9 10 L15 3" /><circle cx="15" cy="3" r="1.3" fill="currentColor" stroke="none" /></svg>);
  if (name === "backtest") return (<svg {...p}><rect x="2" y="9" width="3" height="6" rx="1" /><rect x="7.5" y="5" width="3" height="10" rx="1" /><rect x="13" y="2" width="3" height="13" rx="1" /></svg>);
  if (name === "replay") return (<svg {...p}><path d="M3 4 L3 14" /><path d="M7 6 L7 12" /><path d="M11 3 L11 15" /><path d="M15 7 L15 11" /></svg>);
  if (name === "history") return (<svg {...p}><circle cx="9" cy="9" r="6.5" /><path d="M9 5.5 V9 L12 10.5" /></svg>);
  if (name === "lab") return (<svg {...p}><rect x="2.5" y="2.5" width="4" height="4" rx="1" /><rect x="11.5" y="2.5" width="4" height="4" rx="1" /><rect x="2.5" y="11.5" width="4" height="4" rx="1" /><rect x="11.5" y="11.5" width="4" height="4" rx="1" /></svg>);
  if (name === "workbench") return (<svg {...p}><path d="M3 6 h12" /><path d="M3 10 h12" /><path d="M3 14 h7" /><circle cx="13" cy="3.5" r="1.4" /></svg>);
  if (name === "reports") return (<svg {...p}><path d="M4 2 h6 l4 4 v10 H4 Z" /><path d="M10 2 v4 h4" /><path d="M6.5 10 h5 M6.5 12.5 h3" /></svg>);
  if (name === "catalog") return (<svg {...p}><ellipse cx="9" cy="4" rx="6" ry="2.2" /><path d="M3 4 V14 C3 15.2 5.7 16 9 16 C12.3 16 15 15.2 15 14 V4" /><path d="M3 9 C3 10.2 5.7 11 9 11 C12.3 11 15 10.2 15 9" /></svg>);
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
  const tabs = v4TabsForSession();
  const tabKeys = tabs === V4_NORMAL_TABS ? V4_TAB_KEYS : V4_LEGACY_TAB_KEYS;
  const storedDestinationRef = useRef_v4(null);
  if (storedDestinationRef.current === null) storedDestinationRef.current = v4StoredDestination();
  const initialTabRef = useRef_v4("");
  if (!initialTabRef.current) {
    const hadDestination = !!v4RequestedDestination();
    v4CanonicalizeLegacyLocation();
    initialTabRef.current = v4InitialTab(tabKeys, storedDestinationRef.current);
    if (!hadDestination && initialTabRef.current !== "research") {
      try {
        const url = new URL(window.location.href);
        url.searchParams.set("tab", initialTabRef.current);
        window.history.replaceState(null, "", url.pathname + url.search);
      } catch (e) {}
    }
  }
  const [baseUrl, setBaseUrl] = useState_v4(() => v4InitialBase(baseUrlProp));
  const [pendingBase, setPendingBase] = useState_v4(baseUrl);
  const [theme, setTheme] = useState_v4(v4InitialTheme);
  const [activeTab, setActiveTab] = useState_v4(initialTabRef.current);
  const [activePrototype, setActivePrototype] = useState_v4(() => v4PrototypeForTab(initialTabRef.current));
  const [unavailableDestination, setUnavailableDestination] = useState_v4(() => v4UnavailableDestination());
  const [replayVisited, setReplayVisited] = useState_v4(() => initialTabRef.current === "replay");
  const [contextOpen, setContextOpen] = useState_v4(() => {
    try { return new URLSearchParams(window.location.search).get(V4_CONTEXT_DRAWER_QUERY) === "1"; } catch (e) { return false; }
  });
  const pendingTabFocusRef = useRef_v4("");
  const contextTriggerRef = useRef_v4(null);
  const contextDrawerRef = useRef_v4(null);
  const contextOpenRef = useRef_v4(contextOpen);
  const [buildVer] = useState_v4(() => v4BundleVersion());
  useEffect_v4(() => { contextOpenRef.current = contextOpen; }, [contextOpen]);

  useEffect_v4(() => {
    document.documentElement.setAttribute("data-theme", theme);
    try { v4Storage()?.setItem("stom_theme", theme); } catch (e) {}
  }, [theme]);
  useEffect_v4(() => { if (activeTab === "replay") setReplayVisited(true); }, [activeTab]);
  useEffect_v4(() => {
    const onPopState = () => {
      const nextTab = v4CanonicalizeLegacyLocation() || v4InitialTab(tabKeys);
      const nextContextOpen = (() => {
        try { return new URLSearchParams(window.location.search).get(V4_CONTEXT_DRAWER_QUERY) === "1"; } catch (e) { return false; }
      })();
      const restoreContextTrigger = contextOpenRef.current && !nextContextOpen;
      pendingTabFocusRef.current = nextTab;
      setActiveTab(nextTab);
      setUnavailableDestination(v4UnavailableDestination());
      setActivePrototype(v4PrototypeForTab(nextTab));
      contextOpenRef.current = nextContextOpen;
      setContextOpen(nextContextOpen);
      if (restoreContextTrigger) setTimeout(() => contextTriggerRef.current?.focus(), 0);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [tabKeys]);
  useEffect_v4(() => {
    if (!pendingTabFocusRef.current) return;
    document.getElementById("v4-tab-" + pendingTabFocusRef.current)?.focus();
    pendingTabFocusRef.current = "";
  }, [activeTab]);
  useEffect_v4(() => {
    if (!contextOpen) return;
    const first = contextDrawerRef.current?.querySelector("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
    first?.focus();
  }, [contextOpen]);

  const { state: liveState, health, wsStatus, configSpec, configSpecStatus, send, lastReply, reconnect } = useBackend(baseUrl);
  const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // ---- run 셀렉터 데이터(app.jsx:76-119 패턴): LIVE 또는 과거 run 재구성 ----
  const [selectedRun, setSelectedRun] = useState_v4("");
  const [runList, setRunList] = useState_v4([]);
  const [fetchedRunState, setFetchedRunState] = useState_v4(null);
  const [archiveLoadError, setArchiveLoadError] = useState_v4("");
  const [runsLoadError, setRunsLoadError] = useState_v4("");
  const [runsLoaded, setRunsLoaded] = useState_v4(false);
  const archiveRequestRef = useRef_v4(0);
  const runsRequestRef = useRef_v4(0);
  const backendIdentityRef = useRef_v4(0);

  // 성능(2026-07-17): /runs 는 527런 3MB 대형 페이로드. 과거엔 deps 에 liveState.run_id/status 가
  //   있어 WS 상태 하이드레이션마다 3MB 를 3회 재요청(9MB/로드)했다. 아카이브는 런 '종료' 시에만
  //   새 항목이 생기므로 active→inactive 전이에서만 재조회한다(app.jsx 와 동일 규약).
  const prevRunsActiveRef = useRef_v4(false);
  const [runsEpoch, setRunsEpoch] = useState_v4(0);
  useEffect_v4(() => {
    const active = liveState.status === "running" || liveState.status === "stopping";
    if (prevRunsActiveRef.current && !active) setRunsEpoch((e) => e + 1);
    prevRunsActiveRef.current = active;
  }, [liveState.status]);
  const loadedRunsEpochRef = useRef_v4(-1);
  useEffect_v4(() => {
    if (isDemo || !baseUrl) {
      runsRequestRef.current += 1;
      setRunList([]);
      setRunsLoadError("");
      setRunsLoaded(false);
      return;
    }
    const requestId = ++runsRequestRef.current;
    const backendIdentity = backendIdentityRef.current;
    let cancelled = false;
    let attempt = 0;
    // §1c: 런 종료 전이(runsEpoch 증가)에서는 공용 캐시를 강제 무효화해 새 아카이브를 즉시 반영한다.
    const force = loadedRunsEpochRef.current !== -1 && runsEpoch !== loadedRunsEpochRef.current;
    loadedRunsEpochRef.current = runsEpoch;
    // 대형 아카이브(/runs 가 수 MB)는 초기 로드 동시 fetch 큐에 밀려 지연될 수 있어 실패 시
    //   4s 간격 재시도(최대 4회)로 초기 혼잡을 흡수한다. transport timeout 은 공용 모듈이 고정.
    const load = () => {
      fetchRunsShared(baseUrl, { force })
        .then(j => {
          if (cancelled || requestId !== runsRequestRef.current || backendIdentity !== backendIdentityRef.current) return;
          if (!j || typeof j !== "object" || !Array.isArray(j.runs) || j.runs.some(run => !run || typeof run !== "object")) {
            throw new Error("Malformed /runs response: expected an object with a runs array");
          }
          const runs = j.runs.slice();
          runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
          setRunList(runs);
          setRunsLoadError("");
          setRunsLoaded(true);
        })
        .catch(e => {
          if (cancelled || requestId !== runsRequestRef.current || backendIdentity !== backendIdentityRef.current) return;
          if (attempt < 4) { attempt += 1; setTimeout(() => { if (!cancelled) load(); }, 4000); }
          else setRunsLoadError(String(e && e.message ? e.message : e));
        });
    };
    load();
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, runsEpoch]);

  const fetchRunState = useCallback_v4(() => {
    if (!selectedRun || isDemo || !baseUrl) {
      setFetchedRunState(null); setArchiveLoadError(""); return;
    }
    const requestId = ++archiveRequestRef.current;
    const backendIdentity = backendIdentityRef.current;
    fetch(baseUrl + "/run_state?run_id=" + encodeURIComponent(selectedRun), { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (requestId !== archiveRequestRef.current || backendIdentity !== backendIdentityRef.current) return;
        setFetchedRunState(j); setArchiveLoadError("");
      })
      .catch(e => {
        if (requestId !== archiveRequestRef.current || backendIdentity !== backendIdentityRef.current) return;
        setFetchedRunState(null);
        setArchiveLoadError(String(e && e.message ? e.message : e));
      });
  }, [baseUrl, selectedRun, isDemo]);
  useEffect_v4(() => {
    if (!selectedRun) { setFetchedRunState(null); return; }
    fetchRunState();
    const id = setInterval(fetchRunState, 30000);
    return () => clearInterval(id);
  }, [fetchRunState, selectedRun]);

  const selectRun = useCallback_v4((runId) => {
    archiveRequestRef.current += 1;
    setSelectedRun(runId);
    setFetchedRunState(null);
    setArchiveLoadError("");
  }, []);
  const display = _resolveReplayDisplayState(selectedRun, fetchedRunState, archiveLoadError, liveState);
  const state = display.displayState || { status: "archive_unavailable", run_id: selectedRun, current_gen: -1, generations: [] };
  const running = liveState.status === "running" || liveState.status === "stopping";
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
  const applyBase = () => {
    backendIdentityRef.current += 1;
    archiveRequestRef.current += 1;
    runsRequestRef.current += 1;
    loadedRunsEpochRef.current = -1;
    setSelectedRun("");
    setFetchedRunState(null);
    setArchiveLoadError("");
    setRunList([]);
    setRunsLoadError("");
    setRunsLoaded(false);
    setBaseUrl(pendingBase);
  };
  const retryRunList = () => {
    setRunsLoadError("");
    setRunsEpoch((epoch) => epoch + 1);
  };

  // config 파생값(app.jsx:241-244 패턴): 차트 gate 라인·세대표 하이라이트 기준
  const mddCap = Number((configSpec.find(f => f.name === "mdd_cap")?.default) ?? 40);
  const minDailyTrades = Number((configSpec.find(f => f.name === "min_daily_trades")?.default) ?? 0.5);
  const targetScoreRaw = (configSpec.find(f => f.name === "target_score")?.default);
  const targetScore = (targetScoreRaw === "" || targetScoreRaw === null || targetScoreRaw === undefined) ? 1.0 : Number(targetScoreRaw);

  const setContextDrawer = (open, returnFocus = false) => {
    if (open === contextOpenRef.current) return;
    try {
      const url = new URL(window.location.href);
      if (open) {
        url.searchParams.set(V4_CONTEXT_DRAWER_QUERY, "1");
        window.history.pushState({ ...(window.history.state || {}), v4ContextDrawer: true }, "", url.pathname + url.search);
        contextOpenRef.current = true;
        setContextOpen(true);
        return;
      }
      url.searchParams.delete(V4_CONTEXT_DRAWER_QUERY);
      contextOpenRef.current = false;
      setContextOpen(false);
      if (window.history.state && window.history.state.v4ContextDrawer === true) {
        window.history.back();
      } else {
        const nextState = { ...(window.history.state || {}) };
        delete nextState.v4ContextDrawer;
        window.history.replaceState(nextState, "", url.pathname + url.search);
      }
    } catch (e) {
      contextOpenRef.current = false;
      setContextOpen(false);
    }
    if (!open && returnFocus) setTimeout(() => contextTriggerRef.current?.focus(), 0);
  };
  const onContextKeyDown = (event) => {
    if (event.key === "Escape") {
      event.preventDefault();
      setContextDrawer(false, true);
      return;
    }
    if (event.key !== "Tab") return;
    const drawer = contextDrawerRef.current;
    const focusable = drawer ? Array.from(drawer.querySelectorAll("button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])")) : [];
    if (!focusable.length) { event.preventDefault(); drawer?.focus(); return; }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };
  const selectTab = (key, retainFocus = true) => {
    if (!tabKeys.includes(key)) return;
    if (key === activeTab && contextOpenRef.current) {
      setContextDrawer(false, retainFocus);
      return;
    }
    if (key === activeTab && !activePrototype) return;
    if (retainFocus) pendingTabFocusRef.current = key;
    setActiveTab(key);
    setUnavailableDestination("");
    contextOpenRef.current = false;
    setContextOpen(false);
    setActivePrototype("");
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("tab", key);
      url.searchParams.delete(V4_CONTEXT_DRAWER_QUERY);
      url.searchParams.delete(V4_PROTOTYPE_QUERY);
      window.history.pushState(null, "", url.pathname + url.search);
    } catch (e) {}
  };
  const onTabKeyDown = (event, key) => {
    const next = _nextV4TabKey(tabKeys, key, event.key);
    if (next === key && !["Home", "End"].includes(event.key)) return;
    event.preventDefault();
    selectTab(next);
  };
  const activePrototypeMeta = activePrototype === "catalog"
    ? { full: "Reports · 연구 카탈로그 prototype", hint: "Reports 소유 gated prototype · 일반 레일 추가 없음" }
    : null;
  const active = unavailableDestination
    ? { full: "요청 대상 사용할 수 없음", hint: `명시적 route "${unavailableDestination}" 보존` }
    : (activePrototypeMeta || tabs.find(t => t.key === activeTab) || tabs[0]);

  return (
    <div className="v4-root" data-v4-tab={activeTab}>
      {/* ===== 좌측 레일 ===== */}
      <aside className="v4-rail" aria-label="V4 내비게이션">
        <div className="v4-rail-logo" title="STOM V4">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M2 15 L6 12 L9 13 L13 7 L18 3" stroke="var(--teal)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /><circle cx="18" cy="3" r="1.8" fill="var(--violet)" /></svg>
        </div>
        <div className="v4-rail-tabs" role="tablist" aria-label="V4 연구 워크스페이스">
          {tabs.map(tab => (
            <button key={tab.key} id={"v4-tab-" + tab.key} role="tab"
                    aria-controls={"v4-panel-" + tab.key} aria-selected={activeTab === tab.key}
                    tabIndex={activeTab === tab.key ? 0 : -1}
                    className={"v4-rail-item" + (activeTab === tab.key ? " active" : "")}
                    onKeyDown={event => onTabKeyDown(event, tab.key)}
                    onClick={() => selectTab(tab.key)} title={tab.full + " — " + tab.hint}>
              <V4RailIcon name={tab.key} />
              <span className="v4-ri-label">{tab.label}</span>
              <i className="v4-ri-dot"></i>
            </button>
          ))}
        </div>
        <div className="v4-rail-spacer"></div>
        <a className="v4-rail-item" href="/ui/?dashboard_version=legacy" title="Legacy 대시보드를 1회 열기(영속 없음)">
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M11 3 L5 9 L11 15" /></svg>
          <span className="v4-ri-label">LEGACY</span>
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
            {buildVer && <span className="v4-sfx build" title="현재 로드된 번들 빌드 지문(app.js?v=)">build {buildVer}</span>}
            <span className="v4-sfx">실거래 없음</span>
            <span className="v4-sfx">브로커 없음</span>
            <span className="v4-sfx gate">HUMAN GATE</span>
            <span className="v4-sfx">APPEND-ONLY 감사</span>
          </div>
          <div className="v4-grow"></div>
          <V4BaseControl value={pendingBase} onChange={setPendingBase}
                         onApply={applyBase} onReconnect={reconnect} />
          <ConnBadge health={health} wsStatus={wsStatus} />
          <StatusBadge status={state.status} />
          <button ref={contextTriggerRef} className="btn ghost sm v4-context-trigger"
                  type="button" aria-haspopup="dialog" aria-expanded={contextOpen}
                  aria-controls="v4-context-drawer" onClick={() => setContextDrawer(!contextOpenRef.current, contextOpenRef.current)}>
            AI Context
          </button>
          <V4ThemeToggle theme={theme} onChange={setTheme} />
        </header>
        <div className="v4-controlbar">
          <div className="v4-view-title">
            <h2>{active.full}</h2>
            <span className="mono">{active.hint} · run={selectedRun ? "archive" : "LIVE"}{runId ? " · " + runId : ""}</span>
          </div>
          <V4RunControls
            running={running} state={liveState} isDemo={isDemo}
            isLive={activeTab === "research"}
            runList={runList} selectedRun={selectedRun}
            onSelectRun={selectRun} onRefreshRun={fetchRunState}
            onOpenSettings={() => setSettingsOpen(true)} onStop={onStop}
            onGoLive={() => selectTab("research")} />
        </div>

        <main className="v4-stage">
          {display.mode === "archive" && display.error && (
            <div className="research-empty" role="alert">
              아카이브 run 로드 실패 · {selectedRun} · {display.error}
            </div>
          )}
          {runsLoadError && (
            <div className="research-empty" role="alert">
              아카이브 목록을 새로 고치지 못했습니다 · {runsLoadError} · {runList.length ? `마지막 확인 ${runList.length}건을 표시합니다.` : "확인된 아카이브 행이 없습니다."}
              <button className="btn ghost sm" type="button" onClick={retryRunList}>다시 시도</button>
            </div>
          )}
          {runsLoaded && !runsLoadError && runList.length === 0 && (
            <div className="research-empty" role="status">아카이브 run이 없습니다.</div>
          )}
          {/* Replay keep-alive: 첫 방문 후 hidden 유지(언마운트 금지 — WS·재생 위치 보존) */}
          {replayVisited && (
            <div id="v4-panel-replay" role="tabpanel" aria-labelledby="v4-tab-replay"
                 hidden={activeTab !== "replay"}
                 style={{ display: activeTab === "replay" ? undefined : "none" }}
                 aria-hidden={activeTab !== "replay"}
                 inert={activeTab === "replay" ? undefined : ""}>
              <ErrorBoundary>
                <V4Replay baseUrl={baseUrl} wsStatus={wsStatus} active={activeTab === "replay"} />
              </ErrorBoundary>
            </div>
          )}
          {!replayVisited && (
            <div id="v4-panel-replay" role="tabpanel" aria-labelledby="v4-tab-replay"
                 hidden aria-hidden="true" inert="" />
          )}
          {tabs.filter(tab => tab.key !== activeTab && tab.key !== "replay").map(tab => (
            <div key={tab.key} id={"v4-panel-" + tab.key} role="tabpanel"
                 aria-labelledby={"v4-tab-" + tab.key} hidden aria-hidden="true" inert="" />
          ))}
          {activeTab === "replay" ? null : (
            <div id={"v4-panel-" + activeTab} role="tabpanel"
                 aria-labelledby={"v4-tab-" + activeTab}>
              <ErrorBoundary>
                {unavailableDestination ? (
                  <div className="research-empty" role="alert">
                    요청한 대상 "{unavailableDestination}"은(는) 사용할 수 없습니다. URL을 변경하지 않았으며, 왼쪽 탐색에서 지원되는 대상을 선택하세요.
                  </div>
                ) : activeTab === "research" ? (
                <V4ResearchLive baseUrl={baseUrl} state={state} wsStatus={wsStatus} send={send}
                                lastReply={lastReply} onViewCode={onViewCodeByGen}
                                onOpenSettings={() => setSettingsOpen(true)}
                                targetScore={targetScore} mddCap={mddCap} minDailyTrades={minDailyTrades} />
              ) : activeTab === "backtest" ? (
                <V4Backtest baseUrl={baseUrl} wsStatus={wsStatus} />
              ) : activeTab === "history" ? (
                <V4History baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} onNavigate={selectTab} />
              ) : activeTab === "lab" ? (
                <V4Lab baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} onNavigate={selectTab} />
              ) : activeTab === "workbench" ? (
                <V4Workbench baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
              ) : activeTab === "reports" ? (
                <V4Reports baseUrl={baseUrl} prototype={activePrototype} />
              ) : activeTab === "alpha" ? (
                <V4Alpha baseUrl={baseUrl} wsStatus={wsStatus} />
              ) : activeTab === "catalog" ? (
                <V4Catalog baseUrl={baseUrl} />
              ) : (
                <div className="v4-context">
                  <AIContextPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} genNo={state.current_gen} />
                </div>
                )}
              </ErrorBoundary>
            </div>
          )}
        </main>
      </div>
      {contextOpen && (
        <div className="v4-context-backdrop">
          <section id="v4-context-drawer" ref={contextDrawerRef} className="v4-context-drawer"
                   role="dialog" aria-modal="true" aria-labelledby="v4-context-drawer-title"
                   tabIndex="-1" onKeyDown={onContextKeyDown}>
            <div className="v4-context-drawer-head">
              <h2 id="v4-context-drawer-title">AI Context developer drawer</h2>
              <button className="btn ghost sm" type="button" onClick={() => setContextDrawer(false, true)}
                      aria-label="AI Context drawer 닫기">닫기</button>
            </div>
            <AIContextPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} genNo={state.current_gen} />
          </section>
        </div>
      )}

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
export { DashboardV4Shell, _nextV4TabKey, v4TabFromPathname };
