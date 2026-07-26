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
import { V4Workbench } from "./v4-workbench.jsx";
import { V4Reports } from "./v4-reports.jsx";
import { V4Catalog } from "./v4-catalog.jsx";
import { V4SettingsTab } from "./v4-settings.jsx";
import { V4GlossaryTab } from "./v4-glossary.jsx";
import { fetchRunsShared } from "./runs-shared.jsx";
import { _resolveReplayDisplayState } from "./replay-lifecycle.jsx";
const { useState: useState_v4, useEffect: useEffect_v4, useCallback: useCallback_v4, useRef: useRef_v4 } = React;
// v5.3.9: 대시보드 버전(릴리스 태그와 동기 수동 갱신) — 브랜드/탭 타이틀에 명시.
// v5.5 F9 — 대시보드 버전은 STOM 본체와 분리(태그 V2UC-Dashboard-v*). 릴리스마다 수동 갱신.
const V4_DASH_VERSION = "v5.11.0";
// v5.10 P2 — process-local browser diagnostic ring. Entries are redacted before
// they enter the ring; no diagnostic data is persisted by this frontend.
(function _initFeLogBuffer() {
  const capacity = 200;
  const redact = (value) => {
    let text;
    try { text = String(value == null ? "" : value); } catch (e) { return "[unprintable diagnostic]"; }
    return text
      .replace(/\b(?:set-)?cookie\b(?:["']?\s*[:=]\s*)[^\r\n]*/gi, "Cookie: <redacted>")
      .replace(/\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password)\b(["']?\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)/gi, (match, name, separator) => name + separator + "<redacted>")
      .replace(/\b(?:authorization\s*[:=]?\s*)?bearer\s+[^\s,;]+/gi, "Bearer <redacted>")
      .replace(/(?:[a-z]:[\\/][^\s,;'"`]+|\\\\[^\s,;'"`]+|(?<![:\w])\/(?!\/)[^\s,;'"`]+)/gi, "<absolute-path>")
      .slice(0, 400);
  };
  window.__stomRedactLog = redact;
  const buf = Array.isArray(window.__stomFeLog) ? window.__stomFeLog : [];
  while (buf.length > capacity) buf.shift();
  for (let i = 0; i < buf.length; i += 1) {
    const entry = buf[i] || {};
    buf[i] = { ts: Number(entry.ts) || Date.now() / 1000, level: redact(entry.level || "ERROR"), msg: redact(entry.msg) };
  }
  const push = (level, msg) => {
    try {
      buf.push({ ts: Date.now() / 1000, level: redact(level), msg: redact(msg) });
      while (buf.length > capacity) buf.shift();
    } catch (e) {}
  };
  const describeConsoleValue = (value) => {
    if (typeof value === "string") return value;
    if (value && typeof value.message === "string") return value.message;
    try {
      const serialized = JSON.stringify(value);
      return serialized === undefined ? String(value) : serialized;
    } catch (error) {
      return "[unserializable console.error argument: " + ((error && error.message) || "unknown") + "]";
    }
  };
  window.__stomFeLog = buf;
  if (window.__stomFeLogCaptureInstalled) return;
  window.__stomFeLogCaptureInstalled = true;
  window.addEventListener("error", e => push("ERROR", e.message || e.type));
  window.addEventListener("unhandledrejection", e => push("REJECT", (e.reason && e.reason.message) || e.reason || "unhandled rejection"));
  const origErr = console.error.bind(console);
  console.error = (...args) => {
    try {
      push("CONSOLE", args.map(describeConsoleValue).join(" "));
    } catch (error) {
      push("CONSOLE", "[console.error diagnostic unavailable]");
    } finally {
      origErr(...args);
    }
  };
})();

// V4 IA(UXR-P3): primary 6뷰(연구 워크스페이스) + secondary 보조도구를 레일에서 구획한다.
//   key 는 불변(딥링크·파리티 보존). Bench→성과(전당) 개명. 아이콘은 stroke currentColor 인라인 SVG.
// v5.6 U11 — 연구 흐름 순서: Live → History → Reports(결과 열람) → 성과 → Backtest → Replay.
const V4_TABS = [
  { key: "research", label: "라이브", full: "Research Live", badge: "LIVE", hint: "조건식 자율 진화 · 스테이지 구동 실시간 관찰", group: "primary" },
  { key: "history", label: "기록", full: "History", badge: "HIST", hint: "run/gen 아카이브 · Compare · 연구 기록 검색", group: "primary" },
  { key: "reports", label: "보고서", full: "Reports · 리포트 뷰어", badge: "DOC", hint: "리포트 HTML 안전 뷰어 · 읽기 전용(sandbox)", group: "primary" },
  { key: "workbench", label: "성과", full: "명예의 전당 · 인간+AI 성과", badge: "HALL", hint: "명예의 전당 전용 — 인간 벤치마크와 AI 연구 성과 비교", group: "primary" },
  { key: "backtest", label: "백테스트", full: "Backtest", badge: "BT", hint: "전략 실행 · 결과 리포트", group: "primary" },
  { key: "replay", label: "리플레이", full: "Replay", badge: "SIM", hint: "캔들 리플레이 · 신호 맥락", group: "primary" },
  { key: "catalog", label: "연구 자산", full: "연구 자산 (P4 비정본 preview prototype + 진행 관찰)", badge: "자산", hint: "연혁실·함정지도·절실험실·출구은행·진행 관찰(구 Alpha)·B1 — 읽기 전용 · 비정본 preview", group: "secondary" },
  { key: "settings", label: "설정", full: "설정 · 대시보드 관리", badge: "CFG", hint: "화면 배치·UI 저장상태·버전 정보·로그 — 클라이언트 표시 설정 전용", group: "secondary" },
  { key: "glossary", label: "용어", full: "용어 · 종합 위키", badge: "WIKI", hint: "지표·분석·거버넌스 용어를 한 곳에서 — 읽기 전용", group: "secondary" },
];
const V4_TAB_KEYS = V4_TABS.map(t => t.key);

// 정본 딥링크 경로 → V4 탭 매핑(B트랙 승격): /ui/evolution/* 를 V4 뷰로 이어준다.
//   process 는 V4 전용 뷰가 없어 research(Live)로 흡수(사이클 다이어그램이 해당 맥락 제공).
const V4_PATH_TAB_MAP = {
  "backtest": "backtest",
  "chart-replay": "replay",
  "records": "history",
  "lab": "research",
  "workbench": "workbench",
  "verdict": "history",
  "audit": "history",
  "process": "research",
};
// 2026-07-26 단일 진입점 통합: 주소를 쓸 때는 항상 정본 루트(`/?tab=`)를 쓴다.
//   위 V4_PATH_TAB_MAP 은 기존 북마크·외부 문서의 /ui/… 딥링크를 탭으로 되읽는 용도로만 남는다.

// v5.3.1: 은퇴 탭(audit·verdict·lab·alpha) legacy ?tab= 딥링크를 소유 탭으로 봉인한다.
const V4_LEGACY_TAB_ALIAS = { "audit": "history", "verdict": "history", "lab": "research", "alpha": "catalog" };

function v4TabFromPathname(pathname) {
  try {
    const parts = String(pathname || "").split("/").filter(Boolean); // ["ui", "evolution", "records"]
    if (parts[0] !== "ui") return "";
    const leaf = parts[1] === "evolution" ? (parts[2] || "") : parts[1];
    if (parts[1] === "evolution" && !parts[2]) return "research";
    return V4_PATH_TAB_MAP[leaf] || "";
  } catch (e) { return ""; }
}

function v4InitialTab() {
  try {
    const fromPath = v4TabFromPathname(window.location.pathname);
    if (fromPath && V4_TAB_KEYS.includes(fromPath)) return fromPath;
    const t = new URLSearchParams(window.location.search).get("tab");
    if (t && V4_TAB_KEYS.includes(t)) return t;
    if (t && V4_LEGACY_TAB_ALIAS[t]) return V4_LEGACY_TAB_ALIAS[t];
  } catch (e) {}
  return "research";
}

function _nextV4TabKey(keys, current, key, orientation) {
  const index = Math.max(0, keys.indexOf(current));
  if (key === "Home") return keys[0];
  if (key === "End") return keys[keys.length - 1];
  if (orientation === "vertical" && key === "ArrowDown") return keys[(index + 1) % keys.length];
  if (orientation === "vertical" && key === "ArrowUp") return keys[(index - 1 + keys.length) % keys.length];
  if (orientation === "horizontal" && key === "ArrowRight") return keys[(index + 1) % keys.length];
  if (orientation === "horizontal" && key === "ArrowLeft") return keys[(index - 1 + keys.length) % keys.length];
  return current;
}

function useV4TabOrientation() {
  const query = "(max-width: 768px)";
  const [orientation, setOrientation] = useState_v4(() =>
    window.matchMedia(query).matches ? "horizontal" : "vertical");
  useEffect_v4(() => {
    const media = window.matchMedia(query);
    const update = () => setOrientation(media.matches ? "horizontal" : "vertical");
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return orientation;
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
function v4BackendMismatch(identity, buildVer) {
  if (identity === undefined) return "";
  if (!identity || typeof identity !== "object") return "백엔드가 대시보드 릴리스/빌드 식별자를 제공하지 않습니다.";
  const shell = identity.shell;
  const backend = identity.backend;
  if (!shell || typeof shell !== "object" || !backend || typeof backend !== "object") {
    return "백엔드 대시보드 식별자 형식이 지원되지 않습니다.";
  }
  if (shell.name !== "v4-ops" || shell.release !== V4_DASH_VERSION) {
    return "프론트엔드와 백엔드 대시보드 릴리스가 일치하지 않습니다.";
  }
  if (buildVer && shell.build !== buildVer) {
    return "프론트엔드와 백엔드가 서로 다른 빌드를 보고합니다.";
  }
  if (backend.release !== shell.release || backend.build !== shell.build) {
    return "백엔드 프로세스와 대시보드 셸 식별자가 일치하지 않습니다.";
  }
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
      <button type="button" className={theme === "dark" ? "active" : ""} aria-pressed={theme === "dark"} onClick={() => onChange("dark")} data-tip="다크 모드">Dark</button>
      <button type="button" className={theme === "light" ? "active" : ""} aria-pressed={theme === "light"} onClick={() => onChange("light")} data-tip="라이트 모드">Light</button>
    </div>
  );
}

function V4BaseControl({ value, onChange, onApply, onReconnect }) {
  return (
    <div className="v4-base">
      <span className="mono v4-base-lbl">BASE</span>
      <input className="toolbar-input" value={value} spellCheck={false} aria-label="대시보드 API Base URL"
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
  const tabOrientation = useV4TabOrientation();
  const pendingTabFocusRef = useRef_v4("");
  const [buildVer] = useState_v4(() => v4BundleVersion());
  // v5.3.8: 구버전 탭 감지 — 열린 탭이 옛 JS 를 들고 있으면 배너로 새로고침 유도(검수 불일치 재발 방지).
  const [newVer, setNewVer] = useState_v4("");
  const [backendDashboard, setBackendDashboard] = useState_v4(undefined);
  useEffect_v4(() => {
    if (!buildVer) return undefined;
    const check = () => fetch("/ui/bundle/manifest.json?ts=" + Date.now(), { cache: "no-store" })
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        const v = j && j.bundles && j.bundles["app.js"] && j.bundles["app.js"].v;
        if (v && v !== buildVer) setNewVer(String(v));
      })
      .catch(() => {});
    const id = setInterval(check, 60000);
    check();
    return () => clearInterval(id);
  }, [buildVer]);
  useEffect_v4(() => {
    const controller = new AbortController();
    setBackendDashboard(undefined);
    fetch(baseUrl + "/health", { signal: controller.signal })
      .then(response => response.ok ? response.json() : null)
      .then(payload => { if (!controller.signal.aborted) setBackendDashboard(payload && payload.dashboard ? payload.dashboard : null); })
      .catch(() => { if (!controller.signal.aborted) setBackendDashboard(null); });
    return () => controller.abort();
  }, [baseUrl]);

  useEffect_v4(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stom_theme", theme);
    // v5.3.9: 브라우저 탭 제목에 대시보드 버전 명시(V4 잔존 표기 제거).
    document.title = "STOM AI · 조건식 자율 진화 대시보드 " + V4_DASH_VERSION;
  }, [theme]);
  useEffect_v4(() => {
    // 구 딥링크(/ui/…, /ui/v4/)로 들어와도 주소창은 정본 루트 + ?tab= 으로 정규화한다.
    //   탭 상태는 그대로 유지되므로 사용자는 화면을 잃지 않는다.
    if (!/^\/ui(\/|$)/.test(window.location.pathname)) return;
    try {
      const url = new URL(window.location.href);
      url.pathname = "/";
      url.searchParams.set("tab", v4TabFromPathname(window.location.pathname) || activeTab);
      window.history.replaceState(null, "", url.pathname + url.search);
    } catch (e) {}
  }, []);
  useEffect_v4(() => { if (activeTab === "replay") setReplayVisited(true); }, [activeTab]);
  useEffect_v4(() => {
    if (!pendingTabFocusRef.current) return;
    document.getElementById("v4-tab-" + pendingTabFocusRef.current)?.focus();
    pendingTabFocusRef.current = "";
  }, [activeTab]);

  const { state: liveState, health, wsStatus, configSpec, configSpecStatus, send, lastReply, reconnect } = useBackend(baseUrl);
  const isDemo = typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // ---- run 셀렉터 데이터(app.jsx:76-119 패턴): LIVE 또는 과거 run 재구성 ----
  const [selectedRun, setSelectedRun] = useState_v4("");
  const [runList, setRunList] = useState_v4([]);
  const [fetchedRunState, setFetchedRunState] = useState_v4(null);
  const [archiveLoadError, setArchiveLoadError] = useState_v4("");
  const archiveRequestRef = useRef_v4(0);

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
    if (isDemo || !baseUrl) { setRunList([]); return; }
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
          if (cancelled) return;
          const runs = Array.isArray(j && j.runs) ? j.runs : [];
          runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
          setRunList(runs);
        })
        .catch(() => {
          if (cancelled) return;
          if (attempt < 4) { attempt += 1; setTimeout(() => { if (!cancelled) load(); }, 4000); }
          else setRunList([]);
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
    fetch(baseUrl + "/run_state?run_id=" + encodeURIComponent(selectedRun), { signal: AbortSignal.timeout(4000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (requestId !== archiveRequestRef.current) return;
        setFetchedRunState(j); setArchiveLoadError("");
      })
      .catch(e => {
        if (requestId !== archiveRequestRef.current) return;
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
  const [contextDrawerOpen, setContextDrawerOpen] = useState_v4(false);
  const [verFx, setVerFx] = useState_v4(false);

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

  const selectTab = (key, retainFocus = true) => {
    if (retainFocus) pendingTabFocusRef.current = key;
    setActiveTab(key);
    try {
      // 단일 진입점 규약(2026-07-26): 주소는 항상 루트 + ?tab= 이다.
      //   /ui/v4/ 같은 버전 접미사나 탭마다 다른 경로를 주소창에 남기지 않는다.
      const url = new URL(window.location.href);
      url.pathname = "/";
      url.searchParams.set("tab", key);
      window.history.replaceState(null, "", url.pathname + url.search);
    } catch (e) {}
  };
  const onTabKeyDown = (event, key) => {
    const next = _nextV4TabKey(V4_TAB_KEYS, key, event.key, tabOrientation);
    if (next === key && !["Home", "End"].includes(event.key)) return;
    event.preventDefault();
    selectTab(next);
  };
  const active = V4_TABS.find(t => t.key === activeTab) || V4_TABS[0];
  const backendMismatch = v4BackendMismatch(backendDashboard, buildVer);

  return (
    <div className="v4-root" data-v4-tab={activeTab}>
      {/* ===== 좌측 레일 ===== */}
      <aside className="v4-rail" aria-label="V4 내비게이션">
        <div className="v4-rail-logo" title="STOM V4">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M2 15 L6 12 L9 13 L13 7 L18 3" stroke="var(--teal)" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /><circle cx="18" cy="3" r="1.8" fill="var(--violet)" /></svg>
        </div>
        <div className="v4-rail-tabs" role="tablist" aria-label="V4 연구 워크스페이스" aria-orientation={tabOrientation}>
          {V4_TABS.map((tab, i) => (
            <React.Fragment key={tab.key}>
              {tab.group === "secondary" && V4_TABS[i - 1] && V4_TABS[i - 1].group !== "secondary" && (
                <div className="v4-rail-div" role="presentation" aria-hidden="true" title="보조 도구(분석·감사·컨텍스트)"><span>보조</span></div>
              )}
              <button id={"v4-tab-" + tab.key} role="tab"
                      aria-controls={"v4-panel-" + tab.key} aria-selected={activeTab === tab.key}
                      tabIndex={activeTab === tab.key ? 0 : -1}
                      data-group={tab.group}
                      className={"v4-rail-item" + (tab.group === "secondary" ? " secondary" : "") + (activeTab === tab.key ? " active" : "")}
                      onKeyDown={event => onTabKeyDown(event, tab.key)}
                      onClick={() => selectTab(tab.key)} title={tab.full + " — " + tab.hint}>
                <V4RailIcon name={tab.key} />
                <span className="v4-ri-label">{tab.label}</span>
                <i className="v4-ri-dot"></i>
              </button>
            </React.Fragment>
          ))}
        </div>
        <div className="v4-rail-spacer"></div>
        <button type="button" className={"v4-rail-item" + (contextDrawerOpen ? " active" : "")} onClick={() => setContextDrawerOpen(v => !v)} title="AI Context Pack(개발자 서랍) 토글" aria-pressed={contextDrawerOpen}>
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="3" y="3" width="12" height="12" rx="2" /><path d="M6 7 h6 M6 10 h4" /></svg>
          <span className="v4-ri-label">컨텍스트</span>
        </button>
        {/* v5.11.3 — 대시보드는 하나다. 레거시 셸로 가는 상시 버튼을 레일에서 뺐다.
            비상 진입은 `?dashboard_version=legacy` 쿼리로만 남는다(서버 라우트 불변). */}
      </aside>

      {/* ===== 워크스페이스 ===== */}
      <div className="v4-workspace">
        {newVer && (
          <button type="button" className="v6-stale-banner" onClick={() => window.location.reload()}
                  title="이 탭은 이전 빌드를 실행 중입니다. 클릭하면 최신 버전으로 새로고침합니다.">
            ⟳ 새 버전 배포됨 (build {newVer}) — 이 탭은 구버전({buildVer})입니다. 클릭하여 새로고침
          </button>
        )}
        {backendMismatch && (
          <div role="alert" className="v6-stale-banner" style={{ cursor: "default" }}
               title="자동 새로고침이나 상태 변경 없이 표시됩니다.">
            백엔드 호환성 경고 — {backendMismatch} 현재 탭을 새로고침하기 전에 배포 프로세스를 확인하세요.
          </div>
        )}
        <header className="v4-topbar">
          <div className="v4-brand">
            <b>조건식 AI 연구 터미널</b>
            <span className="mono v6-dash-ver">대시보드 <b>{V4_DASH_VERSION}</b> · build {buildVer || "?"} · contract v{health.contract_version ?? state.contract_version ?? 1}</span>
          </div>
          <div className="v4-safety" aria-label="안전 경계">
            {isDemo && <span className="v4-sfx demo">DEMO</span>}
            {buildVer && <button type="button" className={"v4-sfx build v4-verfx" + (verFx ? " on" : "")} onClick={() => setVerFx(v => !v)} title="버전 하이라이트 효과 토글(app.js?v=)" aria-pressed={verFx}>build {buildVer}</button>}
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
          {V4_TABS.filter(tab => tab.key !== activeTab && tab.key !== "replay").map(tab => (
            <div key={tab.key} id={"v4-panel-" + tab.key} role="tabpanel"
                 aria-labelledby={"v4-tab-" + tab.key} hidden aria-hidden="true" inert="" />
          ))}
          {activeTab === "replay" ? null : (
            <div id={"v4-panel-" + activeTab} role="tabpanel"
                 aria-labelledby={"v4-tab-" + activeTab}>
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
              ) : activeTab === "workbench" ? (
                <V4Workbench baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
              ) : activeTab === "reports" ? (
                <V4Reports baseUrl={baseUrl} />
              ) : activeTab === "catalog" ? (
                <V4Catalog baseUrl={baseUrl} wsStatus={wsStatus} />
              ) : activeTab === "settings" ? (
                <V4SettingsTab baseUrl={baseUrl} dashVersion={V4_DASH_VERSION} />
              ) : activeTab === "glossary" ? (
                <V4GlossaryTab />
              ) : (
                <div className="v4-placeholder"><p className="mono">알 수 없는 뷰</p></div>
                )}
              </ErrorBoundary>
            </div>
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
      {contextDrawerOpen && (
        <aside className="v4-context-drawer" role="dialog" aria-label="AI Context Pack (개발자 서랍)">
          <div className="v4-cdrawer-hd">
            <b>AI Context Pack · 개발자 서랍</b>
            <button type="button" className="v4-cdrawer-x" onClick={() => setContextDrawerOpen(false)} aria-label="닫기">✕</button>
          </div>
          <div className="v4-cdrawer-bd">
            {typeof window.AIContextPanel === "function" ? (
              <window.AIContextPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} genNo={state.current_gen} />
            ) : (
              <p className="mono">AIContextPanel 미로드 — 번들 재빌드 필요</p>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

Object.assign(window, { DashboardV4Shell });
// dual-safe ESM export. KEEP on ONE physical line.
export { DashboardV4Shell, _nextV4TabKey, v4TabFromPathname };
