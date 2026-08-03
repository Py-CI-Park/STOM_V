/* QSP7 R2 buy-entry filter candidates: shallow single-clause filters from recovery discriminators.
 * A filter removes entries — the card always shows expected retention so nobody reads
 * "fewer trades, smaller loss" as an improvement. */
import { _btPostJson } from "./bt-tab-utils.jsx";
const { useState: useState_bf } = React;

function _bfPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(1)}%` : "—";
}

function BtBuyFilters({ baseUrl, analysisId, payload, onPayload, onSelect, selectedId }) {
  const [busy, setBusy] = useState_bf(false);
  const [error, setError] = useState_bf("");
  const generate = () => {
    if (!analysisId) return;
    setBusy(true); setError("");
    _btPostJson(`${baseUrl}/bt/trade-path/buy-filters`, { analysis_id: analysisId }, 120000)
      .then(result => onPayload && onPayload(result))
      .catch(reason => setError(String(reason.message || reason)))
      .finally(() => setBusy(false));
  };
  const rows = (payload && payload.proposals) || [];
  const skipped = (payload && payload.skipped) || [];
  const copy = code => { try { navigator.clipboard.writeText(code); } catch (ignored) {} };
  return <section className="tp-subpanel tp-buy-filters" aria-labelledby="tp-bf-title">
    <header><div><b id="tp-bf-title">매수 진입 필터 후보 · 축=매수</b><small>회복 판별(FDR 통과·fold 일관) 변수만 · 변수 1개짜리 얕은 필터</small></div><span className="tp-authority advisory">자문</span></header>
    <div className="tp-entry-guard">필터는 <b>진입을 줄입니다</b>. 총손익이 좋아져도 <b>건당 엣지</b>가 나빠지면 채택 게이트가 차단합니다.</div>
    <button className="btn primary sm" onClick={generate} disabled={busy || !analysisId}>{busy ? "판별 통계 계산 중…" : "근거 기반 매수 필터 생성"}</button>
    {error && <p className="tp-error" role="alert">{error}</p>}
    {payload && !payload.available && <div className="tp-empty">{payload.reason === "baseline_buy_missing" ? "레인 기준선 매수식을 찾을 수 없습니다." : "분석을 먼저 완료하세요."}</div>}
    {payload && payload.available && <>
      <div className="tp-ri-kpis mono">FDR 통과·fold 일관 변수 {payload.eligible_variables ?? 0}개 → 후보 {rows.length}개 · 제외 {skipped.length}개</div>
      {rows.length === 0 && <div className="tp-empty">근거를 통과한 필터 후보가 없습니다 — 이것도 결과입니다.</div>}
      <div className="tp-proposal-grid">
        {rows.map(row => <article className={`tp-proposal${selectedId === row.proposal_id ? " picked" : ""}`} key={row.proposal_id}>
          <header><div><b>{row.title}</b><small>{row.family} · {row.timeframe} · intent gate ✓</small><small>{row.intent}</small></div><span className="tp-authority advisory">자문</span></header>
          <div className="tp-bf-retention"><b>기대 진입 유지율 {_bfPct(row.expected_retention)}</b><span>{row.direction === "keep_high" ? "높은 쪽만 남김" : "낮은 쪽만 남김"} · 임계 {row.threshold}</span></div>
          <pre>{`elif not (${row.clause}):\n    매수 = False`}</pre>
          <div className="tp-proposal-sources"><b>임계값 출처 · 분위수</b>{(row.threshold_sources || []).map(source => <small key={source}>• {source}</small>)}</div>
          <dl><dt>근거</dt><dd>{row.evidence}</dd><dt>반증</dt><dd>{row.counterevidence}</dd><dt>위험</dt><dd>{row.risk}</dd></dl>
          <div className="tp-bf-actions">
            <button className="btn ghost sm" onClick={() => copy(row.stom_code)}>전체 매수식 복사</button>
            <button className="btn primary sm" onClick={() => onSelect && onSelect(row)}>이 필터로 실행 준비</button>
          </div>
        </article>)}
      </div>
      {skipped.length > 0 && <div className="tp-bf-skipped"><b>제외된 변수(추정하지 않음)</b>{skipped.map(row => <small key={row.column}>• {row.column} — {row.reason}</small>)}</div>}
    </>}
  </section>;
}

Object.assign(window, { BtBuyFilters });
export { BtBuyFilters };
