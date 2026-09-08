// Execute production JSX against deterministic, non-market API responses.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";
import esbuild from "esbuild";

const fe = fileURLToPath(new URL("../frontend/", import.meta.url));
const built = await esbuild.build({
  entryPoints: [fe + "bt-csv-quality.jsx"], bundle: true, write: false,
  format: "iife", jsxFactory: "React.createElement", jsxFragment: "React.Fragment",
});
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => errors.push(e.message));
const dom = new JSDOM('<!doctype html><html><body><main id="root"></main></body></html>', {
  runScripts: "outside-only", url: "http://127.0.0.1/", virtualConsole: vc,
});
const w = dom.window;
w.eval(readFileSync(fe + "vendor-react.js", "utf8"));
w.eval(readFileSync(fe + "vendor-react-dom.js", "utf8"));
w.eval(built.outputFiles[0].text);
const root = w.ReactDOM.createRoot(w.document.getElementById("root"));
function render(envelope) {
  w.ReactDOM.flushSync(() => root.render(w.React.createElement(w.BtCsvQuality, { envelope })));
  return w.document.getElementById("root").textContent;
}
const envelope = (status, count, execution = "success") => ({
  execution_status: execution, analysis_ready: status === "VALID" && execution === "success",
  data_quality: { status, raw_count: count, accepted_count: count, rejected_count: 0,
    source_sha256: "f".repeat(64), issues: [], issue_count: 0 },
});
// Given / When / Then: distinguish true zero, missing, partial and failed execution.
assert.match(render(envelope("VALID", 1)), /정상/);
assert.match(render(envelope("NO_TRADES", 0)), /정상 무거래/);
assert.match(render(envelope("MISSING_ARTIFACT", null)), /파일 없음/);
assert.match(render(envelope("ROW_PARSE_PARTIAL", 2)), /일부 행 오류/);
assert.match(render(envelope("VALID", 1, "error")), /실행 실패/);
assert.match(render(envelope("VALID", 1, "error")), /분석 준비 미충족/);
assert.match(render({ execution_status: "success" }), /품질 미확인/);
const attack = envelope("ROW_PARSE_PARTIAL", 1);
attack.data_quality.issues = [{ code: "ROW_PARSE_PARTIAL", row: 2, column: "<img src=x onerror=alert(1)>", detail: "bad" }];
render(attack);
assert.equal(w.document.querySelector("img"), null);
assert.deepEqual(errors, []);
w.ReactDOM.flushSync(() => root.unmount());
dom.window.close();
console.log(JSON.stringify({ scenarios: 8, passed: 8, errors }));
