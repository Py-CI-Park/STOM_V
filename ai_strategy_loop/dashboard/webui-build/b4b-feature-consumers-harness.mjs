// Real three feature consumers, controlled transport and production React scheduling.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {fileURLToPath} from "node:url";
import {JSDOM,VirtualConsole} from "jsdom";
import esbuild from "esbuild";
const fe=fileURLToPath(new URL("../frontend/",import.meta.url));
const imports=["bt-leaf-explorer.jsx","bt-feature-map.jsx","bt-entry-autopsy.jsx"].map(p=>JSON.stringify((fe+p).replaceAll("\\","/")));
const built=await esbuild.build({stdin:{contents:`import {BtLeafExplorer} from ${imports[0]}; import {BtFeatureMap} from ${imports[1]}; import {BtEntryAutopsy} from ${imports[2]}; Object.assign(window,{BtLeafExplorer,BtFeatureMap,BtEntryAutopsy});`,resolveDir:fe,loader:"js"},bundle:true,write:false,format:"iife",platform:"browser",jsxFactory:"React.createElement",jsxFragment:"React.Fragment"});
const errors=[], calls=[];
const vc=new VirtualConsole(); vc.on("jsdomError",e=>errors.push(e.message));
const dom=new JSDOM('<main id="root"></main>',{url:"http://127.0.0.1",runScripts:"outside-only",virtualConsole:vc});
const w=dom.window;
w.eval(readFileSync(fe+"vendor-react.js","utf8")); w.eval(readFileSync(fe+"vendor-react-dom.js","utf8"));
const blocked={available:false,analysis_ready:false,reason:"QUALITY_BLOCK",n:null,features:null,variables:null,
  data_quality:{status:"ROW_PARSE_PARTIAL",issues:[]}};
let payload=blocked;
w.fetch=url=>{calls.push(String(url)); return Promise.resolve({ok:true,json:async()=>payload});};
w.eval(built.outputFiles[0].text);
let root;
const flush=async fn=>{w.ReactDOM.flushSync(fn); await new Promise(r=>w.setTimeout(r,0)); w.ReactDOM.flushSync(()=>{}); await new Promise(r=>w.setTimeout(r,0));};
const props={baseUrl:"http://127.0.0.1",jobId:"A",isDemo:false,contract:{columns:[]}};
// Given denied feature envelopes / When each production consumer renders / Then no fabricated empty statistics.
for(const name of ["BtLeafExplorer","BtFeatureMap","BtEntryAutopsy"]){
  root=w.ReactDOM.createRoot(w.document.getElementById("root"));
  await flush(()=>root.render(w.React.createElement(w[name],props)));
  assert.match(w.document.body.textContent,/QUALITY_BLOCK/,name);
  if(name==="BtEntryAutopsy") assert.match(w.document.body.textContent.replaceAll(/\s/g,""),/라벨거래—/);
  await flush(()=>root.unmount());
}
// Given a prior map / When only backend changes / Then the new backend is queried.
payload={available:true,analysis_ready:true,variables:[],grid:null,regions:[],n:77,features:[],derived:[],leaf_matrix:[]};
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtFeatureMap,props)));
await flush(()=>root.render(w.React.createElement(w.BtFeatureMap,{...props,baseUrl:"http://localhost:9999"})));
assert.ok(calls.some(url=>url.startsWith("http://localhost:9999")));
await flush(()=>root.unmount());
// Removing the source must remove prior diagnostic counts.
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtEntryAutopsy,props)));
assert.match(w.document.body.textContent,/77/);
await flush(()=>root.render(w.React.createElement(w.BtEntryAutopsy,{...props,jobId:""})));
assert.doesNotMatch(w.document.body.textContent,/77/);
await flush(()=>root.unmount());
// A pending old-generation proposal cannot populate or unlock the new generation.
const proposals=[];
w.fetch=url=>String(url).includes("revision_proposals") ? new Promise(resolve=>proposals.push({url:String(url),resolve})) : Promise.resolve({ok:true,json:async()=>payload});
const proposalButton=()=>[...w.document.querySelectorAll("button")].find(b=>/제안 생성|생성 중|다시 생성/.test(b.textContent));
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtLeafExplorer,{...props,jobId:"",evoSource:{run_id:"A",gen_no:1}})));
await flush(()=>proposalButton().click());
await flush(()=>root.render(w.React.createElement(w.BtLeafExplorer,{...props,jobId:"",evoSource:{run_id:"B",gen_no:2}})));
assert.equal(proposalButton().disabled,false);
await flush(()=>proposalButton().click());
await flush(()=>proposals[0].resolve({ok:true,json:async()=>({available:true,analysis_ready:true,proposals:[],reason:"OLD_SOURCE"})}));
assert.equal(proposalButton().disabled,true);
await flush(()=>proposals[1].resolve({ok:true,json:async()=>({available:true,analysis_ready:true,proposals:[],reason:"NEW_SOURCE"})}));
assert.match(w.document.body.textContent,/NEW_SOURCE/); assert.doesNotMatch(w.document.body.textContent,/OLD_SOURCE/);
await flush(()=>root.unmount());
// Two individually valid receipts from different snapshots cannot be combined.
w.fetch=url=>Promise.resolve({ok:true,json:async()=>({...payload,data_quality:{status:"VALID",source_sha256:String(url).includes("leaf_matrix")?"A":"B"}})});
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtEntryAutopsy,props)));
assert.match(w.document.body.textContent,/원본 일치를 확인할 수 없습니다/);
assert.match(w.document.body.textContent.replaceAll(/\s/g,""),/라벨거래—/);
await flush(()=>root.unmount());
// HTTP200 with an invalid envelope is a protocol failure, never normal no-data.
w.fetch=()=>Promise.resolve({ok:true,json:async()=>null});
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtLeafExplorer,props)));
assert.match(w.document.body.textContent,/응답 형식/);
await flush(()=>root.unmount());
// An expected source hash requires an actual hash, not just a successful payload.
w.fetch=()=>Promise.resolve({ok:true,json:async()=>payload});
root=w.ReactDOM.createRoot(w.document.getElementById("root"));
await flush(()=>root.render(w.React.createElement(w.BtEntryAutopsy,{...props,sourceHash:"expected"})));
assert.match(w.document.body.textContent,/원본 일치를 확인할 수 없습니다/);
await flush(()=>root.unmount());
dom.window.close(); assert.deepEqual(errors,[]);
console.log(JSON.stringify({scenarios:9,passed:9,errors}));
