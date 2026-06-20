// track-z-harness.mjs — Track Z runtime harness (Story 1 V1+V2 · Story 4 entry-gate V3+V4).
//
//   None existed in the repo (no *.spec / page.goto / jsdom in any test). This BUILDS it.
//   Preferred host = node + jsdom (npm-free runtime is unaffected: jsdom is a build/test-only
//   dep under the gitignored webui-build/node_modules, never served). If jsdom cannot host
//   the index path, the pytest wrapper falls back to skip + the Playwright harness variant.
//
//   PR-6 FLIP: V2/V3/V4 now load the REAL DEFAULT served artifact frontend/bundle/app.js (the
//     committed esbuild bundle written by `node build-app.mjs`), NOT the transient .track-z pilot.
//     This makes the harness the load-bearing safety proof for the flip: it proves the artifact the
//     browser actually downloads renders all 7 tabs + 3 standalone pages, 0 errors, single React.
//     V1 keeps a transient pilot build (a clean single-React/no-require MECHANISM proof of the
//     alias-to-shim entry — it asserts DemoBadge/LivePending republish, independent of the served
//     file's freshness).
//
//   What it asserts:
//     V1 (bundle MECHANISM proof): builds a transient .track-z/app.pilot.js (same esbuild options
//        as the served build), loads vendored React + the IIFE, asserts window.DemoBadge /
//        window.LivePending are functions, single React identity (window.React === the React the
//        bundle's hooks call — checked by rendering DemoBadge through the bundle and confirming it
//        produced React elements off the SAME window.React), and zero "Dynamic require" / render error.
//     V2 (SERVED bundle — index path, HARDEST): loads vendored React + ReactDOM +
//        lightweight-charts + a classic stom-ui (window.fmt* side-effects) + the SERVED DEFAULT
//        bundle (frontend/bundle/app.js), mounts the index App via the file's own auto-mount at
//        an IDLE /status, asserts 0 errors and non-empty #root (idle index shell only).
//     V3 (Story 4 entry gate — PER-ROUTE render sweep): the gap V2 left open. V2 mounts the
//        index App only at IDLE = just the default (evolution) route's idle shell. V3 closes it:
//        load the SERVED bundle, then mount App once per canonical URL path for the three
//        top-level pages plus the Evolution nested subtabs. Stale localStorage is preseeded on
//        purpose: URL must be canonical over storage. After each route: assert 0 thrown/console
//        errors, #root non-empty, and the expected selected tab labels are active.
//     V4 (Story 4 entry gate — STANDALONE page mounts): lab/pro/verdict each have a standalone
//        HTML that sets window.__STOM_NO_AUTO_MOUNT__=true, loads the SAME SERVED bundle, then
//        mounts window.LabPage / ProPage / VerdictPanel directly. V4 replicates each HTML's mount
//        and asserts each renders with 0 errors / non-empty #root.
//
//   Output: a single JSON object on stdout (the pytest wrapper parses it). Exit 0 iff
//   V1 && V2 && V3 && V4 pass. Any host-unavailability is reported as {"hostError": ...}
//   (exit 3) so the wrapper can skip rather than fail.

import { JSDOM } from "jsdom";
import esbuild from "esbuild";
import { readFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FE = resolve(__dirname, "../frontend");
const TRACK_Z = resolve(__dirname, ".track-z");
mkdirSync(TRACK_Z, { recursive: true });

const read = (p) => readFileSync(p, "utf8");

// PR-6 FLIP: V2/V3/V4 load the REAL DEFAULT served artifact (committed by `node build-app.mjs`),
//   proving the file the browser downloads renders. V1 still uses a transient pilot build below
//   as a clean alias-to-shim MECHANISM proof. (Build the served bundle first with build-app.mjs.)
const SERVED_APP = resolve(FE, "bundle/app.js");

// --- Build the transient pilot the V1 mechanism proof needs (idempotent; gitignored) ---
// Pilot bundle (same options as build-app.mjs default bundle path).
const reactShim = resolve(__dirname, "src/react-shim.js");
const reactDomShim = resolve(__dirname, "src/react-dom-shim.js");
const reactJsxRuntimeShim = resolve(__dirname, "src/react-jsx-runtime-shim.js");
const webuiNodeModules = resolve(__dirname, "node_modules");
const reactFlowEntry = resolve(__dirname, "node_modules/@xyflow/react/dist/esm/index.js");
const dagreEntry = resolve(__dirname, "node_modules/dagre/index.js");
await esbuild.build({
  entryPoints: [resolve(__dirname, "src/track-z-entry.pilot.js")],
  outfile: resolve(TRACK_Z, "app.pilot.js"),
  bundle: true, format: "iife", platform: "browser", target: "es2018",
  jsx: "transform", jsxFactory: "React.createElement", jsxFragment: "React.Fragment",
  minify: false, sourcemap: false, loader: { ".jsx": "jsx" },
  nodePaths: [webuiNodeModules],
  alias: {
    "react/jsx-runtime": reactJsxRuntimeShim,
    "react/jsx-dev-runtime": reactJsxRuntimeShim,
    react: reactShim,
    "react-dom": reactDomShim,
    "react-dom/client": reactDomShim,
    "@xyflow/react": reactFlowEntry,
    dagre: dagreEntry,
  },
});
// Classic stom-ui (window.fmt* side-effects) for the harness — jsdom does not run ESM <script>.
await esbuild.build({
  entryPoints: [resolve(__dirname, "src/format.ts")],
  outfile: resolve(TRACK_Z, "stom-ui.classic.js"),
  bundle: true, format: "iife", platform: "browser", target: "es2018", sourcemap: false,
});

// CONTRACT-VALID idle state — generations:[], status:"idle". Mirrors controller/contract.py
//   idle_state(): App renders its REAL idle shell (not ErrorBoundary, not demo simulator).
const IDLE_STATE = {
  contract_version: 2, run_id: "", status: "idle", current_gen: 0, max_generations: 30,
  provider: "", bt_timeframe: "", best: null, winner: null, generations: [],
  latest: { phase: "", last_checkpoint: "", message: "", recent_logs: [], current_step: -1,
            step_timings: {}, backtest_progress: {}, engine_state: {} },
  cumulative: { tokens: 0, cost_or_count: 0 },
  page_data: {}, active_config: {}, updated_at: 0,
};

// CONTRACT-VALID NON-IDLE (running) state — mirrors controller/contract.py LoopState +
//   GenerationInfo + BestInfo + WinnerInfo + LatestInfo exactly (field names/types). This drives
//   the evolution-tab DATA components (CurrentGenPanel, FitnessChart/ProfitChart/…, GenerationsTable,
//   BestCard/WinnerCard/MergedBestWinnerCard, HypothesisPanel, etc.) to actually render rows/points —
//   not just IdleState. Minimal but contract-valid: 2 graded generations, a best, a winner whose
//   gen === best.gen (exercises the MergedBestWinnerCard branch, app.jsx:373), one with a parsed
//   hypotheses[] entry (exercises HypothesisPanel, hypothesis.jsx:44). status:"running" so
//   isIdle=false (app.jsx:161) → the full evolution main renders.
const _gen = (n, extra) => ({
  gen_no: n, status: "ok", graded_score: 1.0 + n * 0.1, gate_passed: n === 2,
  gate_reason: n === 2 ? "" : "score<target", trade_count: 12 + n, daily_avg_trades: 1.2,
  mdd: 8.5, profit: 120000 + n * 1000, total_profit_pct: 3.2 + n,
  strategy_gist: "gen" + n + " buy/sell", payoff_ratio: 1.4, give_back_rate: 0.2,
  calmar: 0.9, uptrend_r2: 0.7, dispersion_term: 1.0, max_hold_count: 3.0,
  hypotheses: [], ...extra,
});
const RUNNING_STATE = {
  contract_version: 2, run_id: "harness_run_1", status: "running", current_gen: 2,
  max_generations: 30, provider: "harness", bt_timeframe: "3m",
  best: { gen: 2, graded_score: 1.2, gate_passed: true, buy_name: "buy_g2", sell_name: "sell_g2" },
  winner: { gen: 2, score: 1.2, buy_name: "buy_g2", sell_name: "sell_g2" },
  generations: [
    _gen(1, { hypotheses: [{ text: "낮은 변동성 구간 진입", verdict: "rejected", reason: "샘플 부족" }] }),
    _gen(2, { gate_passed: true }),
  ],
  latest: {
    phase: "generation_done", last_checkpoint: "gen2_scored", message: "세대 2 채점 완료",
    recent_logs: ["[gen2] backtest_start", "[gen2] backtest_end", "[gen2] scored graded=1.2"],
    current_step: 4, phase_started_at: 0, gen_started_at: 0,
    step_timings: { generate: 4.0, backtest: 30.0, score: 1.0, autopsy: 2.0 },
    backtest_progress: {}, engine_state: {},
  },
  cumulative: { tokens: 1234, cost_or_count: 2 },
  page_data: {}, active_config: { evolution_mode: "tick", winner_objective: "graded" },
  updated_at: 0,
};
const RIX_HARNESS_ROWS = [
  {
    id: "doc:docs/research/condition_research/alpha.md",
    kind: "doc",
    title: "Alpha Doc",
    source_path: "docs/research/condition_research/alpha.md",
    updated_at: "2026-06-18T00:00:00Z",
    canonicality: "canonical",
    source_authority: "curated_doc",
    detail_available: true,
    tags: ["alpha", "oos"],
    related_ids: ["registry:beta"],
    summary: "Unsafe markdown fixture should stay inert.",
    trace_status: "linked",
    exact_link: "research-index://doc:docs/research/condition_research/alpha.md",
  },
  {
    id: "doc:docs/research/condition_research/slow.md",
    kind: "doc",
    title: "Slow Doc",
    source_path: "docs/research/condition_research/slow.md",
    updated_at: "2026-06-18T00:01:00Z",
    canonicality: "historical",
    source_authority: "curated_doc",
    detail_available: true,
    tags: ["slow"],
    related_ids: [],
    summary: "Late detail fixture used to prove stale response guards.",
    trace_status: "unknown",
    exact_link: "research-index://doc:docs/research/condition_research/slow.md",
  },
  {
    id: "registry:beta",
    kind: "registry",
    title: "Beta Registry",
    source_path: ".omo/evidence/stom-reorg-20260618/research-registry.json",
    updated_at: "2026-06-18T00:02:00Z",
    canonicality: "candidate",
    source_authority: "registry_entry",
    detail_available: true,
    tags: ["beta", "registry"],
    related_ids: ["doc:docs/research/condition_research/alpha.md"],
    summary: "Registry candidate fixture.",
    trace_status: "linked",
    exact_link: "research-index://registry:beta",
  },
  {
    id: "hof:reference-strategies",
    kind: "hof",
    title: "Hall of Fame Reference",
    source_path: "ai_strategy_loop/dashboard/reference_strategies.json",
    updated_at: "2026-06-17T00:03:00Z",
    canonicality: "reference",
    source_authority: "hall_of_fame",
    detail_available: true,
    tags: ["hof"],
    related_ids: ["registry:beta"],
    summary: "HOF fixture.",
    trace_status: "linked",
    exact_link: "research-index://hof:reference-strategies",
  },
  {
    id: "decision:1",
    kind: "decision",
    title: "Decision Audit Fixture",
    source_path: ".omo/evidence/decisions.jsonl",
    updated_at: "2026-06-17T00:04:00Z",
    canonicality: "historical",
    source_authority: "decision_log",
    detail_available: true,
    tags: ["decision"],
    related_ids: ["doc:docs/research/condition_research/alpha.md"],
    summary: "Decision fixture.",
    trace_status: "linked",
    exact_link: "research-index://decision:1",
  },
  {
    id: "evidence:.omo/evidence/tmap-walkforward/manual_evidence.json",
    kind: "evidence",
    title: "Manual Evidence",
    source_path: ".omo/evidence/tmap-walkforward/manual_evidence.json",
    updated_at: "2026-06-17T00:05:00Z",
    canonicality: "derived",
    source_authority: "evidence_artifact",
    detail_available: true,
    tags: ["evidence"],
    related_ids: [],
    summary: "Evidence fixture.",
    trace_status: "unlinked",
    exact_link: "research-index://evidence:.omo/evidence/tmap-walkforward/manual_evidence.json",
  },
];

// makeDom(opts) — opts.state: the /status (and /run_state) payload to serve (default IDLE_STATE).
//   opts.noAutoMount: set window.__STOM_NO_AUTO_MOUNT__=true BEFORE the bundle loads so the index
//     App does NOT auto-mount (the standalone page mounts its own root component — V4).
//   opts.activeTab: preset localStorage["stom_active_tab"] BEFORE mount so a fresh App selects that
//     tab the same way the app does (app.jsx:52 reads it on init) — V3.
function makeDom(opts = {}) {
  const STATE = opts.state || IDLE_STATE;
  const domUrl = opts.url || `http://localhost${opts.path || "/ui/"}`;
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body><div id=root></div></body></html>",
    { runScripts: "dangerously", pretendToBeVisual: true, url: domUrl },
  );
  const { window } = dom;
  const errs = [];
  window.addEventListener("error", (e) => errs.push("window.error: " + ((e.error && e.error.stack) || e.message)));
  // Capture console.error into `errs` only — do NOT forward to the real process stdout/
  //   stderr, so the harness's single JSON result on stdout stays parseable by the wrapper.
  window.console.error = (...a) => { errs.push("console.error: " + a.map(String).join(" ")); };
  window.console.warn = (...a) => { window.__HARNESS_WARNINGS__ = [...(window.__HARNESS_WARNINGS__ || []), a.map(String).join(" ")]; };
  // Minimal browser shims jsdom lacks (used by chart/animation paths).
  window.matchMedia = window.matchMedia || (() => ({ matches: false, addListener() {}, removeListener() {}, addEventListener() {}, removeEventListener() {} }));
  window.requestAnimationFrame = window.requestAnimationFrame || ((cb) => setTimeout(() => cb(Date.now()), 0));
  window.cancelAnimationFrame = window.cancelAnimationFrame || ((id) => clearTimeout(id));
  window.scrollTo = window.scrollTo || (() => {});
  if (!window.ResizeObserver) window.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  // jsdom has no fetch/WebSocket; the served :8770 app does. The App's useBackend() calls
  //   GET /health → /config/spec → /status → opens a WS. We emulate a real backend: /health ok,
  //   /status returns the CONTRACT-VALID STATE (idle or running) so the App renders its REAL shell
  //   (not the ErrorBoundary fallback, and NOT the demo simulator). All other GETs return benign
  //   contract-shaped empties so on-demand tab fetches (backtest/sim/lab/pro/verdict) don't throw.
  const jsonResp = (obj) => Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve(obj),
    text: () => Promise.resolve(JSON.stringify(obj)),
    headers: { get: () => null },
  });
  const defaultFetch = (url) => {
    const u = String(url);
    if (u.includes("/health")) return jsonResp({ contract_version: 2, ok: true });
    if (u.includes("/config/spec")) return jsonResp([]);
    if (u.includes("/status")) return jsonResp(STATE);
    if (u.includes("/run_state")) return jsonResp(STATE);
    if (u.includes("/runs")) return jsonResp({ runs: [] });
    // Lab/Records/Pro/Verdict + backtest/sim on-demand GETs: contract-shaped benign empties.
    if (u.includes("/research_index/detail")) {
      const detailId = new URL(u, "http://localhost").searchParams.get("id") || "";
      if (detailId === "registry:beta") return jsonResp({ available: true, registry_entry: { machine_name: "beta" } });
      return jsonResp({ available: true, markdown: "<script>alert(1)</script>\n# Alpha detail" });
    }
    if (u.includes("/research_index")) {
      return jsonResp({
        records: RIX_HARNESS_ROWS,
        errors: [{ source_path: "bad.json", reason: "JSONDecodeError" }],
        count: RIX_HARNESS_ROWS.length,
        cache: { hit: false, sources: 3 },
      });
    }
    if (u.includes("/research_docs")) return jsonResp({ docs: [], count: 0 });
    if (u.includes("/bt/strategies")) return jsonResp({ strategies: [], count: 0 });
    if (u.includes("/verdict")) return jsonResp({ entries: [], count: 0, status: "unavailable" });
    return jsonResp({});
  };
  window.fetch = opts.fetch || window.fetch || defaultFetch;
  if (!window.WebSocket) {
    // Connect successfully (wsStatus -> "open") but deliver no messages: state stays the
    //   contract-valid /status payload. This avoids the demo-simulator fallback path.
    window.WebSocket = class {
      constructor() { this.readyState = 1; setTimeout(() => { if (typeof this.onopen === "function") this.onopen({}); }, 0); }
      send() {} close() { this.readyState = 3; }
      addEventListener() {} removeEventListener() {}
    };
  }
  if (!window.localStorage) {
    const store = {};
    window.localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; }, clear: () => { for (const k in store) delete store[k]; } };
  }
  // V3 — preset stale storage values before mount. Current G002 contract requires the URL path to
  //   win over localStorage, so these values must not select the rendered route.
  if (opts.activeTab) window.localStorage.setItem("stom_active_tab", opts.activeTab);
  if (opts.activeEvolutionTab) window.localStorage.setItem("stom_active_evolution_tab", opts.activeEvolutionTab);
  // V4 — disable the index App auto-mount so the standalone page mounts its own root.
  if (opts.noAutoMount) window.__STOM_NO_AUTO_MOUNT__ = true;
  return { dom, window, errs };
}
const inject = (window, code) => { const s = window.document.createElement("script"); s.textContent = code; window.document.body.appendChild(s); };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------------------------------------------------------------- V1: pilot
async function runV1() {
  const { window, errs } = makeDom();
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  // PR-3: the pilot bundle is now the FULL app graph (the entry imports app.jsx). Its components
  //   resolve bare stom-ui helpers (fmt*, _axisTicks, …) via the window globals, so load the
  //   vendored chart lib + classic stom-ui first — same hosts the real index page provides. This
  //   keeps V1 a CLEAN single-React-identity / no-require mechanism proof (no spurious fmt* refs).
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  const reactIdentityBefore = window.React;
  inject(window, read(resolve(TRACK_Z, "app.pilot.js")));
  await wait(50);
  const demoIsFn = typeof window.DemoBadge === "function";
  const liveIsFn = typeof window.LivePending === "function";
  // Single React identity + hook dispatch:
  //   (1) the pilot injection must not have replaced the one vendored React, and
  //   (2) a component calling useState THROUGH window.React must render — with two React
  //       copies the hooks dispatcher is null and "Invalid hook call" throws here.
  //   ($$typeof was dropped: Symbol.for('react.element') is globally interned, so it is
  //    identical even across two Reacts — a near-tautological, non-protective check.)
  let singleIdentity = false;
  let hookDispatchOk = false;
  let renderError = null;
  try {
    const identityStable = window.React === reactIdentityBefore
      && typeof window.React.version === "string" && window.React.version.length > 0;
    function Probe() { const [v] = window.React.useState("ok"); return window.React.createElement("span", null, v); }
    const root = window.ReactDOM.createRoot(window.document.getElementById("root"));
    root.render(window.React.createElement(Probe, null));
    await wait(50);
    hookDispatchOk = window.document.getElementById("root").innerHTML.includes("ok");
    // Then mount the actual bundled pilot component (exercises the bundle's render path).
    root.render(window.React.createElement(window.DemoBadge, null));
    await wait(50);
    singleIdentity = identityStable && hookDispatchOk;
  } catch (e) { renderError = e.message; }
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const rootHtml = window.document.getElementById("root").innerHTML;
  const pass = demoIsFn && liveIsFn && singleIdentity && !renderError && dynReq.length === 0;
  return {
    name: "V1_pilot",
    pass,
    demoBadgeIsFunction: demoIsFn,
    livePendingIsFunction: liveIsFn,
    singleReactIdentity: singleIdentity,
    hookDispatchOk,
    renderError,
    dynamicRequireErrors: dynReq,
    rootNonEmpty: rootHtml.trim().length > 0,
    rootHtmlLen: rootHtml.length,
    errorCount: errs.length,
    errors: errs.slice(0, 10),
  };
}

// ---------------------------------------------------------------- V2: index path
//   PR-6 FLIP: V2 now loads the REAL DEFAULT SERVED bundle (frontend/bundle/app.js — the committed
//   esbuild artifact the browser downloads), NOT the transient .track-z pilot. This proves the
//   served artifact is a working app: it auto-mounts App (app.jsx's guarded auto-mount runs on
//   module eval), publishes the FROZEN globals, resolves bare stom-ui/connection helpers via the
//   window globals (esbuild leaves undeclared bare reads as global lookups), keeps a SINGLE React
//   identity (alias-to-shim), and renders with 0 errors / non-empty #root.
async function runV2() {
  const { window, errs } = makeDom();
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));  // window.fmt* etc.
  await wait(50);
  const reactIdentityBefore = window.React;
  const fmtReady = typeof window.fmtTime === "function" && typeof window.fmtScore === "function";
  const lwcReady = typeof window.LightweightCharts !== "undefined";
  // The SERVED bundle auto-mounts App on load (app.jsx guarded auto-mount; no
  //   __STOM_NO_AUTO_MOUNT__ set) and resolves `react` via the alias-to-shim → window.React.
  inject(window, read(SERVED_APP));
  await wait(400);
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const appIsFn = typeof window.App === "function";
  // FROZEN mount-by-name globals must be published by the bundle entry.
  const frozenReady = ["App", "ErrorBoundary", "LabPage", "ProPage", "VerdictPanel", "ResearchIndexPage"]
    .every((n) => typeof window[n] === "function");
  // Single React identity: the bundle's hooks ran through window.React (alias-to-shim), so the
  //   one vendored React must be unchanged and an App render must have produced DOM.
  const singleReactIdentity = window.React === reactIdentityBefore
    && typeof window.React.version === "string" && window.React.version.length > 0;
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const pass = appIsFn && frozenReady && fmtReady && lwcReady && singleReactIdentity
    && dynReq.length === 0 && errs.length === 0 && rootHtml.trim().length > 0;
  return {
    name: "V2_served_default_bundle",
    pass,
    appIsFunction: appIsFn,
    frozenGlobalsReady: frozenReady,
    fmtGlobalsReady: fmtReady,
    lightweightChartsReady: lwcReady,
    singleReactIdentity,
    dynamicRequireErrors: dynReq,
    rootNonEmpty: rootHtml.trim().length > 0,
    rootHtmlLen: rootHtml.length,
    errorCount: errs.length,
    errors: errs.slice(0, 10),
  };
}

// ---------------------------------------------------------------- V3: per-route render sweep
//   Story 4 entry gate. For EACH canonical path, build a fresh jsdom with the SERVED bundle, preset
//   stale localStorage tab keys, and serve the matching /status (RUNNING for Evolution overview and
//   process so their data/live-flow components render; IDLE is enough for the others). The index App
//   auto-mounts and must derive its route from location.pathname, not stale storage.
const V3_TABS = [
  { tab: "evolution-overview", path: "/ui/evolution", state: RUNNING_STATE, selectedNeedles: ["진화 홈", "개요"] },
  { tab: "backtest", path: "/ui/backtest", state: IDLE_STATE, selectedNeedles: ["백테스트"] },
  { tab: "chart-replay", path: "/ui/chart-replay", state: IDLE_STATE, selectedNeedles: ["차트 리플레이"] },
  { tab: "records", path: "/ui/evolution/records", state: IDLE_STATE, selectedNeedles: ["진화 홈", "기록 검색"], expectRecordsIndex: true },
  { tab: "lab", path: "/ui/evolution/lab", state: IDLE_STATE, selectedNeedles: ["진화 홈", "연구실"] },
  { tab: "workbench", path: "/ui/evolution/workbench", state: IDLE_STATE, selectedNeedles: ["진화 홈", "분석 워크벤치"] },
  { tab: "verdict", path: "/ui/evolution/verdict", state: IDLE_STATE, selectedNeedles: ["진화 홈", "결정 감사"] },
  { tab: "process", path: "/ui/evolution/process", state: RUNNING_STATE, selectedNeedles: ["진화 홈", "프로세스"], expectIframe: true, expectProcessLive: true },
];
async function runTabOnce({ tab, path, state, selectedNeedles, expectIframe, expectProcessLive, expectRecordsIndex }) {
  const { window, errs } = makeDom({ state, path, activeTab: "backtest", activeEvolutionTab: "verdict" });
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  await wait(50);
  inject(window, read(SERVED_APP));  // auto-mounts App at the preset tab (real served artifact)
  await wait(900);  // useBackend fetch chain + WS open + per-route on-demand fetches settle
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const rootNonEmpty = rootHtml.trim().length > 0;
  // ErrorBoundary fallback marker (app.jsx:705 "대시보드 렌더 오류") = a caught render throw.
  const boundaryTripped = rootHtml.includes("대시보드 렌더 오류")
    || rootHtml.includes("Dashboard render error");
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const selectedTabs = Array.from(root.querySelectorAll('[aria-selected="true"]'))
    .map((el) => (el.textContent || "").replace(/\s+/g, " ").trim());
  const selectedJoined = selectedTabs.join(" / ");
  const selectedOk = (selectedNeedles || []).every((needle) => selectedJoined.includes(needle));
  const iframeEl = expectIframe ? root.querySelector('iframe[src*="/process_flow"]') : null;
  const iframePresent = expectIframe ? iframeEl != null : undefined;
  const iframeOk = expectIframe ? iframePresent === true : true;
  const recordsIndexContent = expectRecordsIndex
    ? rootHtml.includes("Governed Research Index")
      && rootHtml.includes("Alpha Doc")
      && rootHtml.includes("Beta Registry")
      && root.querySelector(".research-index-warning") != null
    : undefined;
  const recordsOk = expectRecordsIndex ? recordsIndexContent === true : true;
  const processLiveStripPresent = expectProcessLive ? root.querySelector(".process-live-strip") != null : undefined;
  const processTimingGridPresent = expectProcessLive ? root.querySelector(".process-timing-grid") != null : undefined;
  const processLatestLogVisible = expectProcessLive ? root.textContent.includes("[gen2] scored graded=1.2") : undefined;
  const processOk = expectProcessLive
    ? processLiveStripPresent === true && processTimingGridPresent === true && processLatestLogVisible === true
    : true;
  const pass = errs.length === 0 && rootNonEmpty && !boundaryTripped && dynReq.length === 0
    && selectedOk && iframeOk && recordsOk && processOk;
  return {
    tab, path, pass, rootNonEmpty, rootHtmlLen: rootHtml.length,
    errorBoundaryTripped: boundaryTripped, dynamicRequireErrors: dynReq,
    selectedTabs, selectedOk,
    ...(expectIframe ? { iframePresent } : {}),
    ...(expectRecordsIndex ? { recordsIndexContent } : {}),
    ...(expectProcessLive ? { processLiveStripPresent, processTimingGridPresent, processLatestLogVisible } : {}),
    errorCount: errs.length, errors: errs.slice(0, 10),
  };
}
async function runV3() {
  const tabs = {};
  let allPass = true;
  for (const spec of V3_TABS) {
    const r = await runTabOnce(spec);  // serial: each tab gets a clean jsdom (isolated errs)
    tabs[spec.tab] = r;
    if (!r.pass) allPass = false;
  }
  return { name: "V3_per_tab_sweep", pass: allPass, tabs };
}

// ---------------------------------------------------------------- V4: standalone page mounts
//   Story 4 entry gate. lab.html/pro.html/verdict.html each set __STOM_NO_AUTO_MOUNT__=true, load
//   the SAME SERVED bundle, then mount window.LabPage / ProPage / VerdictPanel directly. V4
//   replicates that mount: load the served bundle with auto-mount disabled, then createRoot(...)
//   .render(createElement(window.<Page>, {baseUrl})). Assert each renders 0 errors / non-empty #root.
const V4_PAGES = [
  { page: "lab", global: "LabPage" },
  { page: "pro", global: "ProPage" },
  { page: "verdict", global: "VerdictPanel" },
];
async function runPageOnce({ page, global: globalName }) {
  const { window, errs } = makeDom({ state: IDLE_STATE, noAutoMount: true });
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  await wait(50);
  inject(window, read(SERVED_APP));  // served bundle: publishes globals, does NOT auto-mount
  await wait(50);
  const componentIsFn = typeof window[globalName] === "function";
  let mountError = null;
  if (componentIsFn) {
    // Replicate the HTML's DOMContentLoaded mount (lab/pro/verdict.html lines 37-40).
    inject(window, `(function(){try{
      ReactDOM.createRoot(document.getElementById("root"))
        .render(React.createElement(window.${globalName}, { baseUrl: window.location.origin }));
    }catch(e){window.__mountError=String((e&&e.stack)||e);}})();`);
    await wait(450);
    mountError = window.__mountError || null;
  } else {
    mountError = "window." + globalName + " is not a function";
  }
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const rootNonEmpty = rootHtml.trim().length > 0;
  const boundaryTripped = rootHtml.includes("대시보드 렌더 오류")
    || rootHtml.includes("Dashboard render error");
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const pass = componentIsFn && !mountError && errs.length === 0 && rootNonEmpty
    && !boundaryTripped && dynReq.length === 0;
  return {
    page, global: globalName, pass, componentIsFunction: componentIsFn, mountError,
    rootNonEmpty, rootHtmlLen: rootHtml.length, errorBoundaryTripped: boundaryTripped,
    dynamicRequireErrors: dynReq, errorCount: errs.length, errors: errs.slice(0, 10),
  };
}
async function runV4() {
  const pages = {};
  let allPass = true;
  for (const spec of V4_PAGES) {
    const r = await runPageOnce(spec);  // serial: each page gets a clean jsdom (isolated errs)
    pages[spec.page] = r;
    if (!r.pass) allPass = false;
  }
  return { name: "V4_standalone_pages", pass: allPass, pages };
}

// ---------------------------------------------------------------- V5: governed records behavior
//   Directly mounts ResearchIndexPanel with controlled fetch timing.  This proves the user-facing
//   controls, inert detail rendering, warning display, and stale detail guard against late responses.
function setInputValue(window, el, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  setter.call(el, value);
  el.dispatchEvent(new window.Event("input", { bubbles: true }));
}
function setSelectValue(window, el, value) {
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
  setter.call(el, value);
  el.dispatchEvent(new window.Event("change", { bubbles: true }));
}
function jsonResponse(obj) {
  return Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve(obj),
    text: () => Promise.resolve(JSON.stringify(obj)),
    headers: { get: () => null },
  });
}
async function runV5() {
  const calls = [];
  const researchFetch = (url) => {
    const u = String(url);
    calls.push(u);
    if (u.includes("/research_index/detail")) {
      const id = new URL(u, "http://localhost").searchParams.get("id") || "";
      if (id === "doc:docs/research/condition_research/slow.md") {
        return new Promise((resolve) => setTimeout(() => resolve({
          ok: true, status: 200,
          json: () => Promise.resolve({ available: true, markdown: "SLOW_STALE_MARKER" }),
          text: () => Promise.resolve("SLOW_STALE_MARKER"),
          headers: { get: () => null },
        }), 120));
      }
      if (id === "registry:beta") {
        return jsonResponse({ available: true, registry_entry: { machine_name: "beta", detail: "registry detail" } });
      }
      return jsonResponse({ available: true, markdown: "<script>alert(1)</script>\n# Alpha detail" });
    }
    if (u.includes("/research_index")) {
      return jsonResponse({
        records: RIX_HARNESS_ROWS,
        errors: [{ source_path: "bad.json", reason: "JSONDecodeError" }],
        count: RIX_HARNESS_ROWS.length,
        cache: { hit: false, sources: 3 },
      });
    }
    return jsonResponse({});
  };
  const { window, errs } = makeDom({ noAutoMount: true, fetch: researchFetch });
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  await wait(50);
  inject(window, read(SERVED_APP));
  await wait(50);
  const componentIsFn = typeof window.ResearchIndexPanel === "function";
  let mountError = null;
  if (componentIsFn) {
    inject(window, `(function(){try{
      ReactDOM.createRoot(document.getElementById("root"))
        .render(React.createElement(window.ResearchIndexPanel, { baseUrl: window.location.origin, initialLimit: 3 }));
    }catch(e){window.__mountError=String((e&&e.stack)||e);}})();`);
  } else {
    mountError = "window.ResearchIndexPanel is not a function";
  }
  await wait(220);
  mountError = mountError || window.__mountError || null;
  const root = window.document.getElementById("root");
  const initialText = root.textContent || "";
  const badgesVisible = initialText.includes("Doc") && initialText.includes("canonical")
    && initialText.includes("curated doc") && initialText.includes("Registry")
    && initialText.includes("candidate") && root.querySelector(".research-index-warning") != null;
  const filterLabelsVisible = initialText.includes("kind") && initialText.includes("canonicality") && initialText.includes("trace");
  const detailCallsBeforeSelection = calls.filter((u) => u.includes("/research_index/detail")).length;
  const detailLazyOk = detailCallsBeforeSelection === 0
    && root.querySelector(".research-index-pre") == null
    && initialText.includes("Select a governed research record.");

  const alphaBtn = root.querySelector('button[title="doc:docs/research/condition_research/alpha.md"]');
  let inertDetail = false;
  if (alphaBtn) {
    alphaBtn.click();
    await wait(80);
    const inertPre = root.querySelector(".research-index-pre");
    inertDetail = inertPre != null
      && inertPre.textContent.includes("<script>alert(1)</script>")
      && inertPre.querySelector("script") == null;
  }

  const search = root.querySelector('input[type="search"]');
  const selects = root.querySelectorAll("select");
  let searchFilterOk = false;
  let noMatchOk = false;
  let kindFilterOk = false;
  let canonicalityFilterOk = false;
  let traceFilterOk = false;
  if (search && selects.length >= 3) {
    setInputValue(window, search, "Beta");
    await wait(230);
    const listText = Array.from(root.querySelectorAll(".research-index-list button"))
      .map((button) => button.textContent).join("\n");
    searchFilterOk = listText.includes("Beta Registry") && !listText.includes("Slow Doc");
    setInputValue(window, search, "no-such-record");
    await wait(230);
    noMatchOk = root.textContent.includes("No matching research records.");
    setInputValue(window, search, "");
    setSelectValue(window, selects[0], "registry");
    await wait(230);
    const filteredButtons = Array.from(root.querySelectorAll(".research-index-list button"));
    kindFilterOk = filteredButtons.length === 1 && filteredButtons[0].getAttribute("title") === "registry:beta";
    setSelectValue(window, selects[0], "all");
    setSelectValue(window, selects[1], "historical");
    await wait(230);
    const historicalButtons = Array.from(root.querySelectorAll(".research-index-list button"));
    const historicalTitles = historicalButtons.map((button) => button.getAttribute("title"));
    const historicalOk = historicalButtons.length === 2
      && historicalTitles.includes("doc:docs/research/condition_research/slow.md")
      && historicalTitles.includes("decision:1");
    setSelectValue(window, selects[1], "candidate");
    await wait(230);
    const candidateButtons = Array.from(root.querySelectorAll(".research-index-list button"));
    const candidateOk = candidateButtons.length === 1 && candidateButtons[0].getAttribute("title") === "registry:beta";
    canonicalityFilterOk = historicalOk && candidateOk;
    setSelectValue(window, selects[1], "all");
    setSelectValue(window, selects[2], "unknown");
    await wait(230);
    const unknownButtons = Array.from(root.querySelectorAll(".research-index-list button"));
    traceFilterOk = unknownButtons.length === 1 && unknownButtons[0].getAttribute("title") === "doc:docs/research/condition_research/slow.md";
    setSelectValue(window, selects[2], "all");
    await wait(80);
  }

  const slowBtn = root.querySelector('button[title="doc:docs/research/condition_research/slow.md"]');
  const registryBtn = root.querySelector('button[title="registry:beta"]');
  let staleDetailGuardOk = false;
  if (slowBtn && registryBtn) {
    slowBtn.click();
    await wait(20);
    registryBtn.click();
    await wait(220);
    const pre = root.querySelector(".research-index-pre");
    const text = pre ? pre.textContent : "";
    staleDetailGuardOk = text.includes('"machine_name": "beta"') && !text.includes("SLOW_STALE_MARKER");
  }

  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const pass = componentIsFn && !mountError && errs.length === 0 && dynReq.length === 0
    && badgesVisible && filterLabelsVisible && detailLazyOk && inertDetail
    && searchFilterOk && noMatchOk && kindFilterOk && canonicalityFilterOk && traceFilterOk && staleDetailGuardOk;
  return {
    name: "V5_records_behavior",
    pass,
    componentIsFunction: componentIsFn,
    mountError,
    badgesVisible,
    filterLabelsVisible,
    detailLazyOk,
    inertDetail,
    searchFilterOk,
    noMatchOk,
    kindFilterOk,
    canonicalityFilterOk,
    traceFilterOk,
    staleDetailGuardOk,
    fetchCallCount: calls.length,
    dynamicRequireErrors: dynReq,
    errorCount: errs.length,
    errors: errs.slice(0, 10),
  };
}

// ---------------------------------------------------------------- V6: process-flow edge states
//   Mounts the process tab with malformed/idle/latest edge states.  This proves the realtime strip
//   and timing grid fail safe beyond the single happy RUNNING_STATE used in the tab sweep.
function stateWithLatest(latestPatch) {
  const state = JSON.parse(JSON.stringify(RUNNING_STATE));
  state.latest = { ...state.latest, ...latestPatch };
  return state;
}
const PROCESS_EDGE_CASES = [
  {
    name: "idle_unknown_step",
    state: stateWithLatest({ phase: "", message: "", recent_logs: [], current_step: -1, step_timings: {} }),
  },
  {
    name: "missing_timings",
    state: stateWithLatest({ phase: "score", message: "score phase without timings", recent_logs: [], current_step: null, step_timings: null }),
  },
  {
    name: "out_of_range_step",
    state: stateWithLatest({ phase: "iterate", message: "out of range step", recent_logs: [], current_step: 99, step_timings: { generate: 0.1 } }),
  },
];
async function runProcessEdgeCase(spec) {
  const { window, errs } = makeDom({ state: spec.state, path: "/ui/evolution/process", activeTab: "backtest", activeEvolutionTab: "verdict" });
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  await wait(50);
  inject(window, read(SERVED_APP));
  await wait(450);
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const boundaryTripped = rootHtml.includes("대시보드 렌더 오류")
    || rootHtml.includes("Dashboard render error");
  const liveStrip = root.querySelector(".process-live-strip") != null;
  const timingGrid = root.querySelector(".process-timing-grid") != null;
  const iframePresent = root.querySelector('iframe[src*="/process_flow"]') != null;
  const edgeText = root.textContent.includes("현재 노드") && root.textContent.includes("최근 로그");
  const selectedJoined = Array.from(root.querySelectorAll('[aria-selected="true"]')).map((el) => el.textContent || "").join(" ");
  const selectedOk = selectedJoined.includes("진화 홈") && selectedJoined.includes("프로세스");
  const pass = errs.length === 0 && dynReq.length === 0 && !boundaryTripped
    && rootHtml.trim().length > 0 && liveStrip && timingGrid && iframePresent && edgeText && selectedOk;
  return {
    name: spec.name,
    pass,
    liveStrip,
    timingGrid,
    iframePresent,
    edgeText,
    selectedOk,
    rootHtmlLen: rootHtml.length,
    errorBoundaryTripped: boundaryTripped,
    dynamicRequireErrors: dynReq,
    errorCount: errs.length,
    errors: errs.slice(0, 10),
  };
}
async function runV6() {
  const cases = {};
  let allPass = true;
  for (const spec of PROCESS_EDGE_CASES) {
    const r = await runProcessEdgeCase(spec);
    cases[spec.name] = r;
    if (!r.pass) allPass = false;
  }
  return { name: "V6_process_edge_states", pass: allPass, cases };
}

// Emit ASCII-safe JSON: captured error strings may carry Korean (the app's console.error),
//   and the Windows console default codec (cp949) would corrupt non-ASCII on the wrapper's
//   stdout read. \uXXXX-escaping every non-ASCII char keeps stdout pure ASCII and parseable.
const asciiSafe = (s) => Array.from(s, (c) => {
  const cp = c.charCodeAt(0);
  return cp > 127 ? "\\u" + cp.toString(16).padStart(4, "0") : c;
}).join("");

try {
  const v1 = await runV1();
  const v2 = await runV2();
  const v3 = await runV3();
  const v4 = await runV4();
  const v5 = await runV5();
  const v6 = await runV6();
  const result = {
    host: "node+jsdom", v1, v2, v3, v4, v5, v6,
    allPass: v1.pass && v2.pass && v3.pass && v4.pass && v5.pass && v6.pass,
  };
  process.stdout.write(asciiSafe(JSON.stringify(result, null, 2)) + "\n");
  process.exit(result.allPass ? 0 : 1);
} catch (e) {
  process.stdout.write(asciiSafe(JSON.stringify({ hostError: String((e && e.stack) || e) })) + "\n");
  process.exit(3);
}
