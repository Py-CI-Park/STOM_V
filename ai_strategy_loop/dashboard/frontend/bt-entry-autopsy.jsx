/* QSP7 entry-variable autopsy: reuse the official result analyzers, never post-exit labels. */
import { useFeatureEvidence, FeatureQualityNotice } from "./bt-feature-evidence.jsx";

function _tpeaNum(value, digits = 2) {
  if(value == null || value === "") return "—";
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}

function BtEntryAutopsy({ baseUrl, jobId, contract, sourceHash }) {
  const query=useFeatureEvidence({baseUrl,paths:[
    `/bt/analysis/leaf_matrix?job_id=${encodeURIComponent(jobId||"")}`,
    `/bt/analysis/feature_map?job_id=${encodeURIComponent(jobId||"")}&mode=regions&bins=5&top=50`,
  ],enabled:!!baseUrl&&!!jobId,timeoutMs:30000,expectedHash:sourceHash});
  const leaf=query.payloads?.[0]||null;
  const regions=query.payloads?.[1]||null;
  const denied=(query.payloads||[]).filter(p=>p?.analysis_ready===false);
  const blocked=!!(query.error || query.mismatch || denied.length);
  if(!baseUrl || !jobId) return <section className="tp-entry-autopsy"><p>완료 결과를 선택하세요.</p></section>;

  const allB = ((contract && contract.columns) || []).filter(row => row.group === "B");
  const availableB = allB.filter(row => row.status === "available");
  const modelVars = (!blocked && regions && regions.variables) || [];
  const effects = (leaf && leaf.features) || [];
  const lossRegions = (regions && regions.regions) || [];
  return <section className="tp-entry-autopsy" aria-labelledby="tp-entry-title">
    <header><div><b id="tp-entry-title">매수 해부 · 실행시점 변수</b><small>모든 B_*를 확인하고, 분산이 있는 변수만 승/패·손실구간 계산에 사용</small></div><span className="tp-authority diagnostic">진단</span></header>
    <div className="tp-entry-guard">전체 결과 CSV 기준 · R_*·S_*는 매수 입력으로 사용하지 않습니다 · 매도 후 회복/MFE/MAE는 label로만 분리합니다</div>
    <div className="tp-entry-kpis">
      <article><small>CSV B_* 전체</small><b>{contract?.columns?allB.length:"—"}</b><span>누락·0-only 포함</span></article>
      <article><small>실제 비0 B_*</small><b>{contract?.columns?availableB.length:"—"}</b><span>timeframe 가용</span></article>
      <article><small>분석 투입 B/D</small><b>{!blocked&&regions?.available?modelVars.length:"—"}</b><span>표본≥30·분산&gt;0</span></article>
      <article><small>라벨 거래</small><b>{!blocked&&leaf?.available?_tpeaNum(leaf.n,0):"—"}</b><span>{(leaf && leaf.timeframe) || contract?.timeframe || "—"}</span></article>
    </div>
    {query.loading && <p role="status">매수 해부 자료를 확인하고 있습니다…</p>}
    {(query.error||query.mismatch) && <FeatureQualityNotice payload={leaf} title="매수 해부 보류" reason={query.error?"매수 해부 조회 실패: "+query.error:"선택 결과와 분석 자료의 원본 일치를 확인할 수 없습니다. 다시 조회하세요."}/>}
    {denied.map((payload,index)=><FeatureQualityNotice key={index} payload={payload} title="매수 해부 보류"/>)}
    {!blocked && !query.loading && <><div className="tp-entry-layout">
      <section><h4>변수 전수 가용성</h4><div className="tp-entry-variable-list">{allB.map(row => <span key={row.name} className={row.status}><code>{row.name}</code><b>{row.status}</b></span>)}</div></section>
      <section><h4>승/패 변별 상위 · Cohen d</h4><div className="tp-entry-effect-list">{effects.length ? effects.map(row => <article key={row.feature}><code>{row.feature}</code><b>{_tpeaNum(row.d, 3)}</b><span>승 {_tpeaNum(row.win_mean)} · 패 {_tpeaNum(row.loss_mean)} · n={row.n}</span></article>) : <div className="tp-empty">표본 또는 변별 변수가 없습니다.</div>}</div></section>
    </div>
    <section className="tp-loss-regions"><h4>손실 집중 구간 · 자동 제거가 아닌 가설 후보</h4><div>{lossRegions.length ? lossRegions.map((row, index) => <article key={`${row.feature}-${row.bin}`}><strong>#{index + 1}</strong><code>{row.feature}</code><span>{row.bin}</span><b className="neg">{_tpeaNum(row.pnl, 0)}원</b><small>n={row.n}</small></article>) : <div className="tp-empty">손실 구간 계산 결과가 없습니다.</div>}</div></section></>}
  </section>;
}

Object.assign(window, { BtEntryAutopsy });
export { BtEntryAutopsy };

