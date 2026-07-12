// build-app.mjs — Track Z (PR-7): BUNDLE-ONLY. The esbuild `bundle:true` build is the SINGLE,
//   DEFAULT, and only served-artifact build. The legacy transform-concat fallback
//   (STOM_LEGACY_CONCAT=1) and the redundant STOM_BUNDLE=1 pilot path were RETIRED in PR-7 to
//   enable clean file decomposition (P5): decomposition adds many small modules, and a hardcoded
//   concat ORDER would have to be hand-maintained + kept dual-safe forever. The bundle resolves the
//   ESM graph automatically, so new modules need no build-script change. Rollback for any future
//   work = `git revert` per small PR.
//
//   BUILD → esbuild bundle:true of src/track-z-entry.pilot.js (the full per-module-scope ESM app
//     graph), alias-to-shim react/react-dom (single React identity, no require("react"), no
//     second-React sentinel), classic IIFE → writes the REAL served frontend/bundle/app.js, then
//     runs the post-build machinery (content-hash ?v= into all 5 HTMLs + manifest.json with
//     model:"bundle"). The harness (track-z-harness.mjs) proves this served artifact renders all
//     7 tabs + 3 standalone pages, 0 errors, single React — the load-bearing safety proof.
//
//   Principle (unchanged for users): behavior-invariant. stom-ui.js stays separate/unchanged.
//   app.js stays a classic+defer script in the 5 HTMLs (NOT type=module). Output is committed
//   (runtime npm-free). ?v= is content-hash (no manual bump): a source change changes the hash and
//   the HTML auto-updates (reproducible — hash is a function of content only, no timestamp).

import esbuild from "esbuild";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = resolve(__dirname, "../../..");
const FRONTEND = resolve(__dirname, "../frontend");
const BUNDLE = resolve(FRONTEND, "bundle");

// Bundle entry + alias-to-virtual-shim wiring. esbuild has no rollup `output.globals`, so map bare
//   `react`/`react-dom` to shims that re-export window.React/window.ReactDOM (single React identity,
//   no runtime `require("react")`, no second-React sentinel).
const ENTRY = resolve(__dirname, "src/track-z-entry.pilot.js");
const ENTRY_REL = "src/track-z-entry.pilot.js";
const REACT_SHIM = resolve(__dirname, "src/react-shim.js");
const REACT_DOM_SHIM = resolve(__dirname, "src/react-dom-shim.js");
const REACT_JSX_RUNTIME_SHIM = resolve(__dirname, "src/react-jsx-runtime-shim.js");
const WEBUI_NODE_MODULES = resolve(__dirname, "node_modules");
const REACT_FLOW_ENTRY = resolve(__dirname, "node_modules/@xyflow/react/dist/esm/index.js");
const DAGRE_ENTRY = resolve(__dirname, "node_modules/dagre/index.js");
const EXTERNALIZED_GLOBALS = { react: "window.React", "react-dom": "window.ReactDOM" };

// buildServedBundle(outfile) — the esbuild bundle:true build that produces the REAL served app.js.
async function buildServedBundle(outfile) {
  await esbuild.build({
    entryPoints: [ENTRY],
    absWorkingDir: PROJECT_ROOT,
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
    nodePaths: [WEBUI_NODE_MODULES],
    // Driver-2: resolve bare specifiers to the virtual shims (NOT bare `external`).
    alias: {
      "react/jsx-runtime": REACT_JSX_RUNTIME_SHIM,
      "react/jsx-dev-runtime": REACT_JSX_RUNTIME_SHIM,
      react: REACT_SHIM,
      "react-dom": REACT_DOM_SHIM,
      "react-dom/client": REACT_DOM_SHIM,
      "@xyflow/react": REACT_FLOW_ENTRY,
      dagre: DAGRE_ENTRY,
    },
  });
}

// ============================================================================
// POST-BUILD machinery — runs AFTER bundle/app.js has been written. content-hash ?v= injection
//   into all 5 HTMLs (app.js + stom-ui.js) + manifest.json (model:"bundle" + entry/externalized).
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
    // src="/ui/bundle/NAME(?v=...)" 또는 옛 상대경로 src="bundle/NAME(?v=...)" 의 ?v= 만
    // 정밀 교체. 깊은 SPA 링크(/ui/evolution/*)에서도 자산 경로가 흔들리지 않도록 /ui
    // 절대경로를 보존/승격한다.
    const esc = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return html.replace(
      new RegExp(`(src=["'])(?:/ui/)?bundle/${esc}(\\?v=[^"']*)?(["'])`, "g"),
      `$1/ui/bundle/${name}?v=${v}$3`,
    );
  };

  const htmlTargets = ["index.html", "lab.html", "pro.html", "verdict.html", "STOM AI Dashboard.html", "v4.html"];
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
// BUILD — bundle-only. The real served esbuild bundle is the single build path.
// ============================================================================
mkdirSync(BUNDLE, { recursive: true });
await buildServedBundle(resolve(BUNDLE, "app.js"));
const { appV, stomV, touched } = runPostBuild({
  model: "bundle",
  entry: ENTRY_REL,
  externalizedGlobals: EXTERNALIZED_GLOBALS,
});
console.log(`[build-app][bundle] app.js v=${appV} (entry=${ENTRY_REL}, react via alias-to-shim) · stom-ui.js v=${stomV}`);
console.log(`[build-app][bundle] html ?v= 갱신: ${touched.join(", ") || "(변경 없음)"}`);
