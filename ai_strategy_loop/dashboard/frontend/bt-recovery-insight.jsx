/* QSP7 recovery-discriminator insight (P3): what separates recovered losses from the rest.
 * Labels are research labels — never condition inputs. FDR-gated display only. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_ri, useEffect: useEffect_ri } = React;

function _riNum(value, digits = 3) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}

function BtRecoveryInsight({ baseUrl, analysisId }) {
  const [label, setLabel] = useState_ri("recovery");
  const [payload, setPayload] = useState_ri(null);
  const [error, setError] = useState_ri("");
  useEffect_ri(() => {
    if (!baseUrl || !analysisId) return undefined;
    let alive = true;
    setPayload(null); setError("");
    _btFetchJson(`${baseUrl}/bt/trade-path/recovery-insight?analysis_id=${encodeURIComponent(analysisId)}&label=${label}`, 60000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, analysisId, label]);

  if (!analysisId) return <div className="tp-empty">경로 분석을 먼저 완료하세요.</div>;
  if (error) return <p className="tp-error">판별 변수 조회 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">B_* 변수 × 라벨 판별력을 계산 중입니다…</div>;
  return <section className="tp-subpanel tp-recovery-insight" aria-labelledby="tp-ri-title">
    <header><div><b id="tp-ri-title">판별 변수 인사이트</b><small>FDR q≤{payload.fdr_alpha ?? 0.1} 통과분만 강조 · fold 3분할 부호 일관 표시</small></div><span className="tp-authority diagnostic">진단</span></header>
    <div className="tp-ri-controls" role="tablist" aria-label="판별 라벨 선택">
      {[["recovery", "회복 vs 비회복 (손실군)"], ["winloss", "승 vs 패 (전체)"]].map(([key, text]) =>
        <button key={key} role="tab" aria-selected={label === key} className={label === key ? "active" : ""} onClick={() => setLabel(key)}>{text}</button>)}
    </div>
    <div className="tp-entry-guard">{payload.guard || "라벨은 연구 라벨이며 조건식 입력으로 사용하지 않습니다."}</div>
    {!payload.available
      ? <div className="tp-empty">표본 부족 — 양성 {payload.n_positive} / 음성 {payload.n_negative} (그룹당 최소 {payload.min_group}건 필요)</div>
      : <>
        <div className="tp-ri-kpis mono">양성 {payload.n_positive} · 음성 {payload.n_negative} · 검정 {payload.tested}개 변수 · FDR 통과 {payload.passing_count}개</div>
        <div className="tp-ri-table" role="table" aria-label="판별 변수 상위">
          <div role="row" className="head"><span>변수</span><span>Cohen d</span><span>q</span><span>fold</span><span>양성 평균</span><span>음성 평균</span><span>표본</span></div>
          {(payload.top || []).map(row => <div role="row" key={row.feature} className={row.passes_fdr ? "pass" : "weak"}>
            <code>{row.feature}</code>
            <b>{_riNum(row.d)}</b>
            <span>{_riNum(row.q, 4)}{row.passes_fdr ? " ✓" : ""}</span>
            <span>{row.fold_consistent ? "일관" : "혼재"}</span>
            <span>{_riNum(row.positive_mean)}</span>
            <span>{_riNum(row.negative_mean)}</span>
            <small>{row.n_positive}/{row.n_negative}</small>
          </div>)}
        </div>
        {(payload.top || []).length === 0 && <div className="tp-empty">판별력 있는 변수가 없습니다 — 이것도 결과입니다.</div>}
      </>}
  </section>;
}

Object.assign(window, { BtRecoveryInsight });
export { BtRecoveryInsight };
