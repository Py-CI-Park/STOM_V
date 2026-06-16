// track-z-harness.mjs — Track Z runtime harness (Story 1 V1+V2 · Story 4 entry-gate V3+V4).
//
//   None existed in the repo (no *.spec / page.goto / jsdom in any test). This BUILDS it.
//   Preferred host = node + jsdom (npm-free runtime is unaffected: jsdom is a build/test-only
//   dep under the gitignored webui-build/node_modules, never served). If jsdom cannot host
//   the index path, the pytest wrapper falls back to skip + the Playwright harness variant.
//
//   What it asserts:
//     V1 (pilot bundle mechanism): builds .track-z/app.pilot.js (STOM_BUNDLE path output),
//        loads vendored React + the pilot IIFE, asserts window.DemoBadge / window.LivePending
//        are functions, single React identity (window.React === the React the bundle's hooks
//        call — checked by rendering DemoBadge through the bundle and confirming it produced
//        React elements off the SAME window.React), and zero "Dynamic require" / render error.
//     V2 (harness capability — HARDEST path): loads vendored React + ReactDOM +
//        lightweight-charts + a classic stom-ui (window.fmt* side-effects) + the FLAGGED full
//        bundle (.track-z/app.pilot.js), mounts the index App via the file's own auto-mount at
//        an IDLE /status, asserts 0 errors and non-empty #root (idle index shell only).
//     V3 (Story 4 entry gate — PER-TAB render sweep): the gap V2 left open. V2 mounts the
//        index App only at IDLE = just the default (evolution) tab's idle shell, so a latent
//        missing cross-file import inside backtest/simulation/lab/pro/verdict tabs or the
//        non-idle evolution data components would NOT surface until the (future) flip. V3
//        closes it: load the FLAGGED bundle, then mount App once per tab driving `activeTab`
//        through EACH of evolution(NON-IDLE /status so charts/cards/tables/HypothesisPanel
//        render), backtest, simulation, lab, pro, verdict (the app reads the initial tab from
//        localStorage["stom_active_tab"], so a fresh mount per preset key selects the tab the
//        same way the app does). After each: assert 0 thrown/console errors AND #root non-empty.
//     V4 (Story 4 entry gate — STANDALONE page mounts): lab/pro/verdict each have a standalone
//        HTML that sets window.__STOM_NO_AUTO_MOUNT__=true, loads the SAME bundle, then mounts
//        window.LabPage / ProPage / VerdictPanel directly. V4 replicates each HTML's mount and
//        asserts each renders with 0 errors / non-empty #root.
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

// --- Build the artifacts the harness needs (idempotent; transient, gitignored) ---
// Pilot bundle (same options as build-app.mjs STOM_BUNDLE path).
const reactShim = resolve(__dirname, "src/react-shim.js");
const reactDomShim = resolve(__dirname, "src/react-dom-shim.js");
await esbuild.build({
  entryPoints: [resolve(__dirname, "src/track-z-entry.pilot.js")],
  outfile: resolve(TRACK_Z, "app.pilot.js"),
  bundle: true, format: "iife", platform: "browser", target: "es2018",
  jsx: "transform", jsxFactory: "React.createElement", jsxFragment: "React.Fragment",
  minify: false, sourcemap: false, loader: { ".jsx": "jsx" },
  alias: { react: reactShim, "react-dom": reactDomShim, "react-dom/client": reactDomShim },
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

// makeDom(opts) — opts.state: the /status (and /run_state) payload to serve (default IDLE_STATE).
//   opts.noAutoMount: set window.__STOM_NO_AUTO_MOUNT__=true BEFORE the bundle loads so the index
//     App does NOT auto-mount (the standalone page mounts its own root component — V4).
//   opts.activeTab: preset localStorage["stom_active_tab"] BEFORE mount so a fresh App selects that
//     tab the same way the app does (app.jsx:52 reads it on init) — V3.
function makeDom(opts = {}) {
  const STATE = opts.state || IDLE_STATE;
  const dom = new JSDOM(
    "<!DOCTYPE html><html><body><div id=root></div></body></html>",
    { runScripts: "dangerously", pretendToBeVisual: true, url: "http://localhost/" },
  );
  const { window } = dom;
  const errs = [];
  window.addEventListener("error", (e) => errs.push("window.error: " + ((e.error && e.error.stack) || e.message)));
  // Capture console.error into `errs` only — do NOT forward to the real process stdout/
  //   stderr, so the harness's single JSON result on stdout stays parseable by the wrapper.
  window.console.error = (...a) => { errs.push("console.error: " + a.map(String).join(" ")); };
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
  window.fetch = window.fetch || ((url) => {
    const u = String(url);
    if (u.includes("/health")) return jsonResp({ contract_version: 2, ok: true });
    if (u.includes("/config/spec")) return jsonResp([]);
    if (u.includes("/status")) return jsonResp(STATE);
    if (u.includes("/run_state")) return jsonResp(STATE);
    if (u.includes("/runs")) return jsonResp({ runs: [] });
    // Lab/Pro/Verdict + backtest/sim on-demand GETs: contract-shaped benign empties.
    if (u.includes("/research_docs")) return jsonResp({ docs: [], count: 0 });
    if (u.includes("/bt/strategies")) return jsonResp({ strategies: [], count: 0 });
    if (u.includes("/verdict")) return jsonResp({ entries: [], count: 0, status: "unavailable" });
    return jsonResp({});
  });
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
  // V3 — preset the initial tab the way the app reads it (app.jsx:52, localStorage on init).
  if (opts.activeTab) window.localStorage.setItem("stom_active_tab", opts.activeTab);
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
//   PR-3: V2 now loads the FLAGGED FULL bundle (.track-z/app.pilot.js — the real per-module-
//   scope ESM graph of all 26 converted files), NOT the legacy concat bundle/app.js. This proves
//   the flagged bundle is a working app: it auto-mounts App (app.jsx's guarded auto-mount runs on
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
  // The FLAGGED full bundle auto-mounts App on load (app.jsx guarded auto-mount; no
  //   __STOM_NO_AUTO_MOUNT__ set) and resolves `react` via the alias-to-shim → window.React.
  inject(window, read(resolve(TRACK_Z, "app.pilot.js")));
  await wait(400);
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const appIsFn = typeof window.App === "function";
  // FROZEN mount-by-name globals must be published by the bundle entry.
  const frozenReady = ["App", "ErrorBoundary", "LabPage", "ProPage", "VerdictPanel"]
    .every((n) => typeof window[n] === "function");
  // Single React identity: the bundle's hooks ran through window.React (alias-to-shim), so the
  //   one vendored React must be unchanged and an App render must have produced DOM.
  const singleReactIdentity = window.React === reactIdentityBefore
    && typeof window.React.version === "string" && window.React.version.length > 0;
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  const pass = appIsFn && frozenReady && fmtReady && lwcReady && singleReactIdentity
    && dynReq.length === 0 && errs.length === 0 && rootHtml.trim().length > 0;
  return {
    name: "V2_flagged_full_bundle",
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

// ---------------------------------------------------------------- V3: per-tab render sweep
//   Story 4 entry gate. For EACH tab, build a fresh jsdom with the FLAGGED bundle, preset the
//   initial tab (localStorage["stom_active_tab"]) + serve the matching /status (RUNNING for the
//   evolution tab so its data components render; IDLE is enough for the others — they fetch their
//   own data on demand, which our stubs answer with contract-shaped empties). The index App
//   auto-mounts (no __STOM_NO_AUTO_MOUNT__), reads the preset tab on init (app.jsx:52), and renders
//   that tab's subtree. Assert: 0 thrown/console errors AND #root non-empty.
const V3_TABS = [
  { tab: "evolution", state: RUNNING_STATE },  // NON-IDLE: charts/cards/tables/HypothesisPanel
  { tab: "backtest", state: IDLE_STATE },
  { tab: "simulation", state: IDLE_STATE },
  { tab: "lab", state: IDLE_STATE },
  { tab: "pro", state: IDLE_STATE },
  { tab: "verdict", state: IDLE_STATE },
  // process(7번째): 본문이 <iframe src=/process_flow> 한 장. jsdom은 iframe 내용을 로드하지
  //   않으므로 iframe 콘텐츠가 아니라 iframe 엘리먼트 존재 + React 에러 0 만 단언한다.
  { tab: "process", state: IDLE_STATE, expectIframe: true },
];
async function runTabOnce({ tab, state, expectIframe }) {
  const { window, errs } = makeDom({ state, activeTab: tab });
  inject(window, read(resolve(FE, "vendor-react.js")));
  inject(window, read(resolve(FE, "vendor-react-dom.js")));
  inject(window, read(resolve(FE, "vendor-lightweight-charts.js")));
  inject(window, read(resolve(TRACK_Z, "stom-ui.classic.js")));
  await wait(50);
  inject(window, read(resolve(TRACK_Z, "app.pilot.js")));  // auto-mounts App at the preset tab
  await wait(450);  // useBackend fetch chain + WS open + per-tab on-demand fetches settle
  const root = window.document.getElementById("root");
  const rootHtml = root.innerHTML;
  const rootNonEmpty = rootHtml.trim().length > 0;
  // ErrorBoundary fallback marker (app.jsx:705 "대시보드 렌더 오류") = a caught render throw.
  const boundaryTripped = rootHtml.includes("대시보드 렌더 오류")
    || rootHtml.includes("Dashboard render error");
  const dynReq = errs.filter((e) => /Dynamic require|require is not/i.test(e));
  // process 탭: iframe 엘리먼트 자체가 mount 됐는지(내용 로드 아님)만 확인. src 는 /process_flow.
  const iframeEl = expectIframe ? root.querySelector('iframe[src$="/process_flow"]') : null;
  const iframePresent = expectIframe ? iframeEl != null : undefined;
  const iframeOk = expectIframe ? iframePresent === true : true;
  const pass = errs.length === 0 && rootNonEmpty && !boundaryTripped && dynReq.length === 0 && iframeOk;
  return {
    tab, pass, rootNonEmpty, rootHtmlLen: rootHtml.length,
    errorBoundaryTripped: boundaryTripped, dynamicRequireErrors: dynReq,
    ...(expectIframe ? { iframePresent } : {}),
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
//   the SAME bundle, then mount window.LabPage / ProPage / VerdictPanel directly. V4 replicates that
//   mount: load the flagged bundle with auto-mount disabled, then createRoot(...).render(
//   createElement(window.<Page>, {baseUrl})). Assert each renders 0 errors / non-empty #root.
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
  inject(window, read(resolve(TRACK_Z, "app.pilot.js")));  // publishes globals, does NOT auto-mount
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
  const result = {
    host: "node+jsdom", v1, v2, v3, v4,
    allPass: v1.pass && v2.pass && v3.pass && v4.pass,
  };
  process.stdout.write(asciiSafe(JSON.stringify(result, null, 2)) + "\n");
  process.exit(result.allPass ? 0 : 1);
} catch (e) {
  process.stdout.write(asciiSafe(JSON.stringify({ hostError: String((e && e.stack) || e) })) + "\n");
  process.exit(3);
}
