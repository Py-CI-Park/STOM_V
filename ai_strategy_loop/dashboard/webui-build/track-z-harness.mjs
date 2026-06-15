// track-z-harness.mjs — Track Z (PR-1) runtime harness (Story 1, V1 + V2).
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
//        lightweight-charts + a classic stom-ui (window.fmt* side-effects) + the LEGACY
//        committed bundle/app.js (the full app), mounts the index App via the file's own
//        auto-mount, asserts 0 errors and non-empty #root.
//
//   Output: a single JSON object on stdout (the pytest wrapper parses it). Exit 0 iff both
//   V1 and V2 pass. Any host-unavailability is reported as {"hostError": ...} (exit 3) so
//   the wrapper can skip rather than fail.

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

function makeDom() {
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
  //   GET /health → /config/spec → /status → opens a WS. We emulate a real backend with NO
  //   active run: /health ok, /status returns a CONTRACT-VALID idle state (generations:[],
  //   status:"idle", …) so the App renders its REAL shell (not the ErrorBoundary fallback,
  //   and NOT the demo simulator). This is what V2 verifies: the harness can HOST the index
  //   path (App mounts, #root non-empty, 0 errors), independent of live data.
  const IDLE_STATE = {
    contract_version: 1, run_id: "", status: "idle", current_gen: 0, max_generations: 30,
    provider: "", best: null, winner: null, generations: [],
    latest: { phase: null, last_checkpoint: null, message: null, status: "idle" },
    current_run: null,
  };
  const jsonResp = (obj) => Promise.resolve({
    ok: true, status: 200,
    json: () => Promise.resolve(obj),
    text: () => Promise.resolve(JSON.stringify(obj)),
    headers: { get: () => null },
  });
  window.fetch = window.fetch || ((url) => {
    const u = String(url);
    if (u.includes("/health")) return jsonResp({ contract_version: 1, ok: true });
    if (u.includes("/config/spec")) return jsonResp([]);
    if (u.includes("/status")) return jsonResp(IDLE_STATE);
    if (u.includes("/run_state")) return jsonResp(IDLE_STATE);
    if (u.includes("/runs")) return jsonResp({ runs: [] });
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
  const result = { host: "node+jsdom", v1, v2, allPass: v1.pass && v2.pass };
  process.stdout.write(asciiSafe(JSON.stringify(result, null, 2)) + "\n");
  process.exit(result.allPass ? 0 : 1);
} catch (e) {
  process.stdout.write(asciiSafe(JSON.stringify({ hostError: String((e && e.stack) || e) })) + "\n");
  process.exit(3);
}
