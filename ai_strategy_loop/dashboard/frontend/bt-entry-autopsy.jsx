/* QSP7 entry-variable autopsy: reuse the official result analyzers, never post-exit labels. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_tpea, useEffect: useEffect_tpea } = React;

function _tpeaNum(value, digits = 2) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}

function BtEntryAutopsy({ baseUrl, jobId, contract }) {
  const [leaf, setLeaf] = useState_tpea(null);
  const [regions, setRegions] = useState_tpea(null);
  const [error, setError] = useState_tpea("");
  useEffect_tpea(() => {
    if (!baseUrl || !jobId) return undefined;
    let alive = true;
    setError("");
    Promise.all([
      _btFetchJson(`${baseUrl}/bt/analysis/leaf_matrix?job_id=${encodeURIComponent(jobId)}`, 30000),
      _btFetchJson(`${baseUrl}/bt/analysis/feature_map?job_id=${encodeURIComponent(jobId)}&mode=regions&bins=5&top=50`, 30000),
    ]).then(([leafPayload, regionPayload]) => {
      if (!alive) return;
      setLeaf(leafPayload); setRegions(regionPayload);
    }).catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, jobId]);

  const allB = ((contract && contract.columns) || []).filter(row => row.group === "B");
  const availableB = allB.filter(row => row.status === "available");
  const modelVars = (regions && regions.variables) || [];
  const effects = (leaf && leaf.features) || [];
  const lossRegions = (regions && regions.regions) || [];
  return <section className="tp-entry-autopsy" aria-labelledby="tp-entry-title">
    <header><div><b id="tp-entry-title">매수 해부 · 실행시점 변수</b><small>모든 B_*를 확인하고, 분산이 있는 변수만 승/패·손실구간 계산에 사용</small></div><span className="tp-authority diagnostic">진단</span></header>
    <div className="tp-entry-guard">R_*·S_*는 매수 입력으로 사용하지 않습니다 · 매도 후 회복/MFE/MAE는 label로만 분리합니다</div>
    <div className="tp-entry-kpis">
      <article><small>CSV B_* 전체</small><b>{allB.length}</b><span>누락·0-only 포함</span></article>
      <article><small>실제 비0 B_*</small><b>{availableB.length}</b><span>timeframe 가용</span></article>
      <article><small>분석 투입 B/D</small><b>{modelVars.length}</b><span>표본≥30·분산&gt;0</span></article>
      <article><small>라벨 거래</small><b>{(leaf && leaf.n) || 0}</b><span>{(leaf && leaf.timeframe) || contract?.timeframe || "—"}</span></article>
    </div>
    {error && <p className="tp-error">매수 해부 조회 실패: {error}</p>}
    <div className="tp-entry-layout">
      <section><h4>변수 전수 가용성</h4><div className="tp-entry-variable-list">{allB.map(row => <span key={row.name} className={row.status}><code>{row.name}</code><b>{row.status}</b></span>)}</div></section>
      <section><h4>승/패 변별 상위 · Cohen d</h4><div className="tp-entry-effect-list">{effects.length ? effects.map(row => <article key={row.feature}><code>{row.feature}</code><b>{_tpeaNum(row.d, 3)}</b><span>승 {_tpeaNum(row.win_mean)} · 패 {_tpeaNum(row.loss_mean)} · n={row.n}</span></article>) : <div className="tp-empty">표본 또는 변별 변수가 없습니다.</div>}</div></section>
    </div>
    <section className="tp-loss-regions"><h4>손실 집중 구간 · 자동 제거가 아닌 가설 후보</h4><div>{lossRegions.length ? lossRegions.map((row, index) => <article key={`${row.feature}-${row.bin}`}><strong>#{index + 1}</strong><code>{row.feature}</code><span>{row.bin}</span><b className="neg">{_tpeaNum(row.pnl, 0)}원</b><small>n={row.n}</small></article>) : <div className="tp-empty">손실 구간 계산 결과가 없습니다.</div>}</div></section>
  </section>;
}

Object.assign(window, { BtEntryAutopsy });
export { BtEntryAutopsy };

