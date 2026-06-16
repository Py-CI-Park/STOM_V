// build-app.mjs — Track Z (PR-6 / Story 4+5b FLIP): the REAL esbuild `bundle:true` build is now
//   the DEFAULT served artifact. The legacy transform-concat path is retained ONLY as an emergency
//   instant-rollback behind STOM_LEGACY_CONCAT=1 (NOT deleted — safer revert than a git revert).
//
//   DEFAULT (no env)  → esbuild bundle:true of src/track-z-entry.pilot.js (the full per-module-scope
//     ESM app graph), alias-to-shim react/react-dom (single React identity, no require("react"),
//     no second-React sentinel), classic IIFE → writes the REAL served frontend/bundle/app.js,
//     then runs the SHARED post-build machinery (content-hash ?v= into all 5 HTMLs + manifest.json
//     with model:"bundle"). The harness (track-z-harness.mjs) proves this served artifact renders
//     all 7 tabs + 3 standalone pages, 0 errors, single React — the load-bearing safety proof.
//   STOM_LEGACY_CONCAT=1 → the old transform-concat path (26 .jsx, _stripTopLevelEsm, ==== markers,
//     manifest appSources:ORDER, model:"concat"). Emergency rollback only.
//   STOM_BUNDLE=1 (legacy pilot flag) → builds the bundle to the transient gitignored .track-z dir
//     ONLY (used by older tooling); does NOT touch the served tree. Kept for back-compat.
//
//   Principle (unchanged for users): behavior-invariant. The bundle renders identically to concat —
//   the harness proves it. stom-ui.js stays separate/unchanged. app.js stays a classic+defer script
//   in the 5 HTMLs (NOT type=module). Output is committed (runtime npm-free). ?v= is content-hash
//   (no manual bump): a source change changes the hash and the HTML auto-updates (reproducible —
//   hash is a function of content only, no timestamp).

import esbuild from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = resolve(__dirname, "../frontend");
const BUNDLE = resolve(FRONTEND, "bundle");

// Bundle entry + alias-to-virtual-shim wiring (shared by the DEFAULT bundle build and the legacy
//   STOM_BUNDLE=1 pilot). esbuild has no rollup `output.globals`, so map bare `react`/`react-dom`
//   to shims that re-export window.React/window.ReactDOM (single React identity, no runtime
//   `require("react")`, no second-React sentinel).
const ENTRY = resolve(__dirname, "src/track-z-entry.pilot.js");
const ENTRY_REL = "src/track-z-entry.pilot.js";
const REACT_SHIM = resolve(__dirname, "src/react-shim.js");
const REACT_DOM_SHIM = resolve(__dirname, "src/react-dom-shim.js");
const EXTERNALIZED_GLOBALS = { react: "window.React", "react-dom": "window.ReactDOM" };

// buildServedBundle(outfile) — the esbuild bundle:true build that produces the REAL served app.js
//   (DEFAULT) or a transient pilot artifact (legacy STOM_BUNDLE=1). Options are identical so the
//   harness's transient build and the served build are byte-equivalent for a given source tree.
async function buildServedBundle(outfile) {
  await esbuild.build({
    entryPoints: [ENTRY],
    outfile,
    bundle: true,
    format: "iife",            // classic IIFE → app.js tag stays classic+defer (no type=module flip).
    platform: "browser",
    target: "es2018",
    jsx: "transform",
    jsxFactory: "React.createElement",
    jsxFragment: "React.Fragment",
    minify: false,
    sourcemap: false,
    loader: { ".jsx": "jsx" },
    // Driver-2: resolve bare specifiers to the virtual shims (NOT bare `external`).
    alias: {
      react: REACT_SHIM,
      "react-dom": REACT_DOM_SHIM,
      "react-dom/client": REACT_DOM_SHIM,
    },
  });
}

// ============================================================================
// LEGACY pilot path (STOM_BUNDLE=1) — transient .track-z build ONLY, served tree untouched.
//   Kept for back-compat with older tooling that builds the pilot artifact directly. The flip
//   makes the DEFAULT path do the real served bundle, so this is no longer the only bundle build.
// ============================================================================
if (process.env.STOM_BUNDLE === "1") {
  const TRACK_Z_DIR = resolve(__dirname, ".track-z");
  mkdirSync(TRACK_Z_DIR, { recursive: true });
  const pilotOut = resolve(TRACK_Z_DIR, "app.pilot.js");
  await buildServedBundle(pilotOut);
  const pilotV = createHash("sha256").update(readFileSync(pilotOut)).digest("hex").slice(0, 8);
  const pilotManifest = {
    note: "Track Z legacy pilot manifest (FLAGGED, transient — NOT committed, NOT served).",
    model: "bundle",
    entry: ENTRY_REL,
    externalizedGlobals: EXTERNALIZED_GLOBALS,
    bundles: { "app.pilot.js": { v: pilotV } },
  };
  writeFileSync(resolve(TRACK_Z_DIR, "manifest.pilot.json"), JSON.stringify(pilotManifest, null, 2) + "\n", "utf8");
  console.log(`[build-app][track-z] pilot bundle → .track-z/app.pilot.js v=${pilotV} (model=bundle, react via alias-to-shim)`);
  process.exit(0);
}

// ============================================================================
// SHARED post-build machinery — runs for BOTH the DEFAULT bundle path and the legacy concat
//   fallback, AFTER bundle/app.js has been written. content-hash ?v= injection into all 5 HTMLs
//   (app.js + stom-ui.js) + manifest.json. The only model difference is the manifest body (model:
//   "bundle" + entry/externalizedGlobals vs model:"concat" + appSources).
// ============================================================================
function runPostBuild(manifestModelFields) {
  // ---------- content-hash 계산 ----------
  const hash8 = (p) => createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 8);
  const appPath = resolve(BUNDLE, "app.js");
  const appV = hash8(appPath);
  const stomPath = resolve(BUNDLE, "stom-ui.js");
  const stomV = hash8(stomPath);  // stom-ui.js 는 선행 `vite build` 산출물(분리·불변).

  // ---------- HTML ?v= 자동 갱신(수동 핀 폐지) ----------
  //   대상: bundle/app.js + bundle/stom-ui.js (번들을 로드하는 모든 엔트리).
  const setV = (html, name, v) => {
    // src="bundle/NAME(?v=...)" 의 ?v= 만 정밀 교체. 파일명 "." 이스케이프(.map 오버매치 방지),
    // src 속성 앵커(주석·문서 내 파일명 언급은 건드리지 않음).
    const esc = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return html.replace(
      new RegExp(`(src=["'])bundle/${esc}(\\?v=[^"']*)?(["'])`, "g"),
      `$1bundle/${name}?v=${v}$3`,
    );
  };

  const htmlTargets = ["index.html", "lab.html", "pro.html", "verdict.html", "STOM AI Dashboard.html"];
  const touched = [];
  for (const h of htmlTargets) {
    const p = resolve(FRONTEND, h);
    let s;
    try { s = readFileSync(p, "utf8"); } catch { continue; }
    let out = s;
    if (out.includes("bundle/app.js")) out = setV(out, "app.js", appV);
    if (out.includes("bundle/stom-ui.js")) out = setV(out, "stom-ui.js", stomV);
    if (out !== s) { writeFileSync(p, out, "utf8"); touched.push(h); }
  }

  // ---------- 매니페스트(계약 검증용) ----------
  const manifest = {
    note: "Track Z PR-6 build manifest — content-hash 캐시 버전(수동 ?v= 폐지). 빌드 산출.",
    bundles: { "app.js": { v: appV }, "stom-ui.js": { v: stomV } },
    ...manifestModelFields,
  };
  writeFileSync(resolve(BUNDLE, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
  return { appV, stomV, touched };
}

// ============================================================================
// EMERGENCY FALLBACK (STOM_LEGACY_CONCAT=1) — the old transform-concat path. Strip top-level ESM
//   `import`/`export { ... }` from the dual-safe .jsx files so they compile as CLASSIC scripts in a
//   single shared scope, concat the 26 files with `==== X.jsx ====` markers, write bundle/app.js,
//   then run the shared post-build with model:"concat" + appSources:ORDER. Instant rollback only.
// ============================================================================
const _stripTopLevelEsm = (src) =>
  src
    // multi-line + single-line named/default/namespace import ending in `from "...";`
    .replace(/^import\b[\s\S]*?\bfrom\s*["'][^"']*["']\s*;?\s*$/gm, "")
    // side-effect import (no `from`): `import "...";`
    .replace(/^import\s*["'][^"']*["']\s*;?\s*$/gm, "")
    // top-level `export { ... };`
    .replace(/^\s*export\s*\{[^}]*\}\s*;?\s*$/gm, "");

// index.html 의 로드 순서와 동일해야 한다(전역 정의 순서 보존).
const ORDER = [
  "connection.jsx", "panels.jsx", "run-compare.jsx", "engine.jsx", "chart.jsx",
  "hypothesis.jsx", "table.jsx", "cards.jsx", "code-viewer.jsx", "strategy-inspector.jsx",
  "phase-detail.jsx", "settings.jsx", "analysis.jsx", "research-pro.jsx", "research-lab.jsx",
  "research-wiki.jsx", "ai-context.jsx", "glossary.jsx", "backtest-charts.jsx", "backtest.jsx",
  "sim-live-chart.jsx", "simulation-charts.jsx", "simulation.jsx", "evolution-analysis.jsx",
  "dashboard-pages.jsx", "app.jsx",
];

async function buildLegacyConcat() {
  const header =
    "/* GENERATED by webui-build/build-app.mjs (STOM_LEGACY_CONCAT FALLBACK). DO NOT EDIT.\n" +
    "   운영 컴포넌트 .jsx 를 빌드 시점에 컴파일한 단일 클래식 스크립트(런타임 babel 대체).\n" +
    "   비상 롤백 경로(기본은 esbuild bundle). 로드 순서는 build-app.mjs 의 ORDER. */\n";
  const parts = [header];
  for (const f of ORDER) {
    const code = _stripTopLevelEsm(readFileSync(resolve(FRONTEND, f), "utf8"));
    const res = await esbuild.transform(code, {
      loader: "jsx",
      jsx: "transform",
      jsxFactory: "React.createElement",
      jsxFragment: "React.Fragment",
      minify: false,
      sourcemap: false,
    });
    parts.push(`\n;/* ==== ${f} ==== */\n${res.code}`);
  }
  writeFileSync(resolve(BUNDLE, "app.js"), parts.join(""), "utf8");
}

// ============================================================================
// DISPATCH — default = bundle; STOM_LEGACY_CONCAT=1 = emergency concat fallback.
// ============================================================================
if (process.env.STOM_LEGACY_CONCAT === "1") {
  await buildLegacyConcat();
  const { appV, stomV, touched } = runPostBuild({ model: "concat", appSources: ORDER });
  console.log(`[build-app][LEGACY concat] app.js v=${appV} (${ORDER.length} files) · stom-ui.js v=${stomV}`);
  console.log(`[build-app][LEGACY concat] html ?v= 갱신: ${touched.join(", ") || "(변경 없음)"}`);
} else {
  // DEFAULT — the real served esbuild bundle.
  mkdirSync(BUNDLE, { recursive: true });
  await buildServedBundle(resolve(BUNDLE, "app.js"));
  const { appV, stomV, touched } = runPostBuild({
    model: "bundle",
    entry: ENTRY_REL,
    externalizedGlobals: EXTERNALIZED_GLOBALS,
  });
  console.log(`[build-app][bundle] app.js v=${appV} (entry=${ENTRY_REL}, react via alias-to-shim) · stom-ui.js v=${stomV}`);
  console.log(`[build-app][bundle] html ?v= 갱신: ${touched.join(", ") || "(변경 없음)"}`);
}
