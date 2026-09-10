/* Shared raw-feature request identity; never retain another source's diagnostics. */
import {useState_btc, useEffect_btc, useRef_btc, useCallback_btc} from "./bt-chart-utils.jsx";
import {_btFetchJson} from "./bt-tab-utils.jsx";
import {BtCsvQuality} from "./bt-csv-quality.jsx";

function useFeatureEvidence({baseUrl, paths, enabled, expectedHash="", automatic=true, timeoutMs=15000}) {
  const key=JSON.stringify([baseUrl,paths,!!enabled,expectedHash]);
  const current=useRef_btc({key,enabled}); current.current={key,enabled};
  const request=useRef_btc({seq:0,controller:null});
  const [state,setState]=useState_btc({key:"",payloads:null,error:"",loading:false});
  const load=useCallback_btc(()=>{
    request.current.controller?.abort();
    const seq=request.current.seq+1;
    if(!enabled || !baseUrl || !paths.length){
      request.current={seq,controller:null};
      setState({key,payloads:null,error:"",loading:false}); return;
    }
    const controller=new AbortController(); request.current={seq,controller};
    const active=()=>!controller.signal.aborted && request.current.seq===seq && current.current.key===key && current.current.enabled;
    setState({key,payloads:null,error:"",loading:true});
    Promise.all(paths.map(path=>_btFetchJson(baseUrl+path,timeoutMs,controller.signal)))
      .then(payloads=>{
        if(!active()) return;
        const valid=payloads.every(p=>p && typeof p==="object" && !Array.isArray(p) && typeof p.available==="boolean"
          && (p.analysis_ready===undefined || typeof p.analysis_ready==="boolean"));
        setState({key,payloads:valid?payloads:null,error:valid?"":"분석 응답 형식을 확인할 수 없습니다.",loading:false});
      })
      .catch(error=>{if(active()) setState({key,payloads:null,error:String(error?.message||error),loading:false});});
  },[key,enabled,timeoutMs]);
  useEffect_btc(()=>{
    if(automatic) load();
    else {request.current.controller?.abort(); setState({key,payloads:null,error:"",loading:false});}
    return ()=>request.current.controller?.abort();
  },[load,automatic]);
  const same=enabled && state.key===key;
  const payloads=same?state.payloads:null;
  const hashes=(payloads||[]).map(p=>p?.data_quality?.source_sha256).filter(Boolean);
  const mismatch=!!((expectedHash && (payloads||[]).some(p=>p?.analysis_ready!==false && p?.data_quality?.source_sha256!==expectedHash)) || new Set(hashes).size>1);
  return {payloads,error:same?state.error:"",mismatch,
    loading:!!enabled && (same?state.loading:automatic),load,key};
}

function FeatureQualityNotice({payload,title="피처 분석 보류",reason}) {
  return <section className="panel" aria-label={title}>
    <div className="panel-hd"><b>{title}</b></div>
    <div className="panel-bd"><BtCsvQuality envelope={payload || {analysis_ready:false}}/>
      <p>{reason || payload?.reason || "분석 자료를 확인할 수 없습니다."}</p>
    </div>
  </section>;
}

export {useFeatureEvidence,FeatureQualityNotice};
