// Real MC hook, controlled wire responses, no clock sleeps or live server.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {JSDOM, VirtualConsole} from "jsdom";
import esbuild from "esbuild";

const fe = fileURLToPath(new URL("../frontend/", import.meta.url));
const modulePath = (fe + "bt-montecarlo-source.jsx").replaceAll("\\", "/");
const built = await esbuild.build({stdin:{contents:`
  import {useMonteCarloSource} from ${JSON.stringify(modulePath)};
  window.Probe = function(props) {const state = useMonteCarloSource(props); window.state = state;
    return React.createElement('pre',null,JSON.stringify({mc:state.mc,envelope:state.mcEnvelope,loading:state.mcLoading}));};`,
  resolveDir:fe,loader:"js"}, bundle:true,write:false,format:"iife",platform:"browser",
  jsxFactory:"React.createElement",jsxFragment:"React.Fragment"});
const errors = [];
const vc = new VirtualConsole();
vc.on("jsdomError", e => errors.push(e.message));
const dom = new JSDOM('<main id="root"></main>', {url:"http://127.0.0.1",runScripts:"outside-only",virtualConsole:vc});
const w = dom.window;
w.eval(readFileSync(fe + "vendor-react.js","utf8"));
w.eval(readFileSync(fe + "vendor-react-dom.js","utf8"));
const pending = [];
w.fetch = (url, options) => new Promise((resolve,reject) => pending.push({url:String(url), options, resolve, reject}));
w.eval(built.outputFiles[0].text);
const root = w.ReactDOM.createRoot(w.document.getElementById("root"));
const act = async fn => {
  let completion;
  w.ReactDOM.flushSync(() => { completion = fn(); });
  await completion;
  // Production React in jsdom schedules on window timers, not Node's check phase.
  await new Promise(resolve => w.setTimeout(resolve, 0));
  w.ReactDOM.flushSync(() => {});
  await new Promise(resolve => w.setTimeout(resolve, 0));
};
const props = (jobId, extra={}) => ({baseUrl:"http://127.0.0.1",jobId,enabled:true,
  result:{available:true,status:"success",analysis_ready:true},...extra});
const render = async p => act(async()=>root.render(w.React.createElement(w.Probe,p)));
const reply = async (request, payload) => act(async()=>request.resolve({ok:true,json:async()=>payload}));
const success = marker => ({analysis_ready:true,montecarlo:{marker}});

// Given A pending / When switching B / Then late A cannot populate B.
await render(props("A")); const a = pending.at(-1);
await render(props("B")); const b = pending.at(-1);
await reply(a,success("OLD")); assert.equal(w.state.mc,null);
await reply(b,success("B")); assert.equal(w.state.mc.marker,"B");

// Same source becomes blocked while MC is pending.
await render(props("C")); const c = pending.at(-1);
await render(props("C",{result:{available:true,status:"error",analysis_ready:false}}));
await reply(c,success("STALE")); assert.equal(w.state.mc,null); assert.equal(w.state.mcLoading,false);

// A later response can carry a different source hash; show evidence, not its chart.
await render(props("D",{result:{available:true,analysis_ready:true,data_quality:{source_sha256:"expected"}}}));
await reply(pending.at(-1),{...success("WRONG"),data_quality:{source_sha256:"different"}});
assert.equal(w.state.mc,null); assert.equal(w.state.mcEnvelope.display_ready,false);

// Network failure is not a normal empty sample.
await render(props("E")); await act(async()=>pending.at(-1).reject(new Error("offline")));
assert.equal(w.state.mcEnvelope.analysis_ready,false);
assert.match(w.state.mcEnvelope.display_reason,/응답을 확인할 수 없습니다/);

// Range changes clear old values and reject the earlier response.
await render(props("F",{range:{t_start:1,t_end:2}})); const oldRange=pending.at(-1);
await render(props("F",{range:{t_start:3,t_end:4}})); const newRange=pending.at(-1);
await reply(oldRange,success("RANGE_OLD")); assert.equal(w.state.mc,null);
await reply(newRange,success("RANGE_NEW")); assert.equal(w.state.mc.marker,"RANGE_NEW");
assert.match(newRange.url,/t_start=3&t_end=4/);

// Base URL is also source identity, and manual method selection is retained.
await render(props("G")); const oldHost=pending.at(-1);
await render(props("G",{baseUrl:"http://localhost:9999"})); const newHost=pending.at(-1);
await reply(oldHost,success("HOST_OLD")); assert.equal(w.state.mc,null);
await reply(newHost,success("HOST_NEW")); assert.equal(w.state.mc.marker,"HOST_NEW");
await act(async()=>w.state.loadMc("bootstrap"));
assert.match(pending.at(-1).url,/method=bootstrap/);
await reply(pending.at(-1),{analysis_ready:false,data_quality:{status:"ROW_PARSE_PARTIAL"},montecarlo:null});
assert.equal(w.state.mc,null); assert.equal(w.state.mcEnvelope.data_quality.status,"ROW_PARSE_PARTIAL");
await act(async()=>w.state.loadMc("moving_block"));
assert.match(pending.at(-1).url,/method=moving_block/);
await reply(pending.at(-1),success("BLOCK"));
await act(async()=>root.unmount());
dom.window.close();
assert.deepEqual(errors,[]);
console.log(JSON.stringify({scenarios:8,passed:8,errors}));
