/* One MC request lifecycle: retain admission evidence, discard stale source/range results. */
import {useState_btc, useEffect_btc, useCallback_btc, useRef_btc} from "./bt-chart-utils.jsx";
import {_btFetchJson} from "./bt-tab-utils.jsx";
import {BtCsvQuality} from "./bt-csv-quality.jsx";
import {BtMonteCarloChart} from "./bt-distribution-charts.jsx";

function useMonteCarloSource({baseUrl, jobId, evoSource, range, result, enabled}) {
  const runId = evoSource?.run_id || "";
  const genNo = evoSource?.gen_no;
  const expectedHash = result?.data_quality?.source_sha256 || "";
  const key = JSON.stringify([baseUrl, jobId, runId, genNo, range?.t_start, range?.t_end, expectedHash]);
  const eligible = !!(enabled && baseUrl && result?.available && result.analysis_ready !== false && result.status !== "no_trades");
  const current = useRef_btc({key, eligible});
  current.current = {key, eligible};
  const request = useRef_btc({seq:0, controller:null});
  const [state, setState] = useState_btc({key:"", envelope:null, loading:false});
  const loadMc = useCallback_btc((method) => {
    request.current.controller?.abort();
    const seq = request.current.seq + 1;
    if (!eligible) {
      request.current = {seq, controller:null};
      setState({key, envelope:null, loading:false});
      return;
    }
    const controller = new AbortController();
    request.current = {seq, controller};
    const active = () => !controller.signal.aborted && request.current.seq === seq && current.current.key === key && current.current.eligible;
    setState({key, envelope:null, loading:true});
    let url = baseUrl + "/bt/analysis/montecarlo?n=2000&" + (jobId
      ? "job_id=" + encodeURIComponent(jobId)
      : "run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(genNo));
    if (range) url += "&t_start=" + range.t_start + "&t_end=" + range.t_end;
    url += "&method=" + (["shuffle", "bootstrap", "moving_block"].includes(method) ? method : "shuffle");
    _btFetchJson(url, 12000, controller.signal).then(envelope => {
      if (!active()) return;
      const actualHash = envelope?.data_quality?.source_sha256;
      const mismatch = expectedHash && actualHash && expectedHash !== actualHash;
      setState({key, loading:false, envelope: mismatch ? {...envelope, display_ready:false,
        display_reason:"결과 화면과 몬테카를로의 원본 CSV가 다릅니다. 결과를 다시 조회하세요."} : envelope});
    }).catch(() => {
      if (active()) setState({key, loading:false, envelope:{analysis_ready:false,
        display_reason:"몬테카를로 응답을 확인할 수 없습니다. 다시 시도하세요."}});
    });
  }, [baseUrl, jobId, runId, genNo, key, eligible, range, expectedHash]);
  useEffect_btc(() => {
    loadMc();
    return () => request.current.controller?.abort();
  }, [loadMc]);
  const visible = eligible && state.key === key;
  const envelope = visible ? state.envelope : null;
  const blocked = envelope?.analysis_ready === false || envelope?.display_ready === false;
  return {loadMc, mcEnvelope:envelope, mc:blocked ? null : envelope?.montecarlo || null,
    mcLoading:visible && state.loading};
}

function BtAdmittedMonteCarlo({envelope, mc, loading, onRun, moneyCtx}) {
  if (envelope?.analysis_ready === false || envelope?.display_ready === false) {
    return <section className="panel bt-equal-card" aria-label="몬테카를로 분석 보류">
      <div className="panel-hd"><b>몬테카를로 분석 보류</b></div>
      <div className="panel-bd"><BtCsvQuality envelope={envelope}/>
        <p>{envelope.display_reason || "자료 품질 또는 실행 상태가 계산 조건을 충족하지 않습니다."}</p>
        {onRun && <button className="btn ghost sm" onClick={() => onRun()}>다시 확인</button>}
      </div>
    </section>;
  }
  return <BtMonteCarloChart mc={mc} loading={loading} onRun={onRun} moneyCtx={moneyCtx}/>;
}

export {useMonteCarloSource, BtAdmittedMonteCarlo};
