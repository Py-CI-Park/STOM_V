// Actual shared result renderer: blocked quality must never render metric cards.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";
import esbuild from "esbuild";

const fe = fileURLToPath(new URL("../frontend/", import.meta.url));
const entry = (fe + "bt-result-area.jsx").replaceAll("\\", "/");
const output = await esbuild.build({
  stdin: { contents: `import { ResultDetailBody } from ${JSON.stringify(entry)}; window.QaResult = ResultDetailBody;`,
    resolveDir: fe, loader: "js" },
  bundle: true, write: false, format: "iife", platform: "browser",
  jsxFactory: "React.createElement", jsxFragment: "React.Fragment",
});
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", error => errors.push(error.message));
const dom = new JSDOM('<!doctype html><html><body><main id="root"></main></body></html>', {
  url: "http://127.0.0.1/", runScripts: "outside-only", pretendToBeVisual: true,
  virtualConsole: vc,
});
const w = dom.window;
const requests = [];
w.fetch = url => {
  requests.push(String(url));
  return Promise.resolve({ ok: true, json: async () => ({ available: false, reason: "synthetic" }) });
};
w.eval(readFileSync(fe + "vendor-react.js", "utf8"));
w.eval(readFileSync(fe + "vendor-react-dom.js", "utf8"));
w.eval(output.outputFiles[0].text);
const root = w.ReactDOM.createRoot(w.document.getElementById("root"));
for (const status of ["ROW_PARSE_PARTIAL", "MISSING_ARTIFACT", "NO_TRADES", "ROW_COUNT_MISMATCH"]) {
  const result = { available: true, status: "success", execution_status: "success",
    analysis_ready: false, metrics: null, analysis: null,
    data_quality: { status, issues: [], issue_count: 0 } };
  const capabilities = { label: "synthetic", range: false, monteCarlo: false, compare: false,
    notes: { range: "", monteCarlo: "", compare: "" } };
  // Given / When: the production shared renderer receives an admitted job but blocked data.
  w.ReactDOM.flushSync(() => root.render(w.React.createElement(w.QaResult, {
    result, sourceContext: { capabilities, baseUrl: "", jobId: "fixture" },
  })));
  // Then: show diagnostic quality, not zero-valued profit cards or chart/MC actions.
  assert.ok(w.document.querySelector('[aria-label="CSV 품질 진단"]'));
  assert.equal(w.document.querySelector('[aria-label="결과 분석 섹션"]'), null);
  assert.match(w.document.getElementById("root").textContent, /분석 준비 미충족/);
}
w.ReactDOM.flushSync(() => root.unmount());
dom.window.close();
assert.deepEqual(errors, []);
assert.deepEqual(requests, []);
console.log(JSON.stringify({ scenarios: 4, passed: 4, errors }));
