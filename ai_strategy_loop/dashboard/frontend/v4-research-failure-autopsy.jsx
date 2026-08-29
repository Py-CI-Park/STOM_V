/* v4-research-failure-autopsy.jsx — ANA-04 read-only G0/G1 failure synthesis. */
import { failureAutopsy } from "./v4-research-failure-autopsy-model.mjs";

function _ra4Num(value, digits = 2) {
  return value == null ? "미관측" : Number(value).toFixed(digits);
}

function _ra4Signed(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${Math.round(number).toLocaleString("ko-KR")}`;
}

function V516ResearchFailureAutopsy({ analysis, onInspectCandidate }) {
  const autopsy = failureAutopsy(analysis || {});
  if (!autopsy.candidateCount) return null;
  const stopLoss = autopsy.exits.find(row => row.exitKind === "STOP_LOSS");
  const takeProfit = autopsy.exits.find(row => row.exitKind === "TAKE_PROFIT");
  return (
    <section className="ra4-autopsy" aria-label="G0 G1 공통 실패 부검">
      <header className="ra4-heading"><div><span>ANA-04 · READ ONLY FAILURE AUTOPSY</span><h2>7개 후보가 공통으로 실패한 곳</h2></div><strong>DEV {autopsy.developmentPassCount}/{autopsy.candidateCount} · STOP</strong></header>
      <p className="ra4-lede">상대 개선 Fold가 있어도 절대 양수 Fold와 결합 손익이 부족했습니다. 아래 수치는 봉인 결과의 집계이며 새 기준이나 재실행 지시가 아닙니다.</p>
      <div className="ra4-kpis" role="list" aria-label="실패 부검 핵심 관측">
        <article role="listitem"><span>공통 Blocker</span><b>{autopsy.failureCounts.MIN_POSITIVE_TOTAL_PROFIT_FOLDS}/{autopsy.candidateCount}</b><p>양수 Fold 부족</p></article>
        <article role="listitem"><span>양수 Fold</span><b>{autopsy.folds.positiveProfit}/{autopsy.folds.total}</b><p>관측 {autopsy.folds.observed} · 미관측 {autopsy.folds.unobserved}</p></article>
        <article role="listitem"><span>거래 감소</span><b>{autopsy.trades.g0} → {autopsy.trades.g1}</b><p>-{autopsy.trades.reduction} · -{autopsy.trades.reductionPct}%</p></article>
        <article role="listitem"><span>MDD &gt; 15%</span><b>{autopsy.folds.mddOver15} Fold</b><p>위험 상한 실패 후보 {autopsy.failureCounts.MAX_MDD_EACH_FOLD || 0}/{autopsy.candidateCount}</p></article>
      </div>
      <section className="ra4-blockers" aria-labelledby="ra4-blockers-title">
        <h3 id="ra4-blockers-title">공통 실패 빈도</h3>
        <div className="ra4-blocker-list">{autopsy.failureRows.map(row => <div key={row.code}><span>{row.label}</span><i aria-hidden="true"><b style={{ width: `${row.count / autopsy.candidateCount * 100}%` }}></b></i><strong>{row.count}/{autopsy.candidateCount}</strong></div>)}</div>
      </section>
      <aside className="ra4-interpretation"><b>관측 해석</b><span>평균 개선 Fold {autopsy.folds.averageImproved}/{autopsy.folds.total}와 Paired 신호 {autopsy.pairedPassCount}/{autopsy.candidateCount}는 존재하지만, 양수 Fold {autopsy.folds.positiveProfit}/{autopsy.folds.total}와 DEV 통과 0/{autopsy.candidateCount}를 뒤집지 못합니다.</span></aside>
      <details className="ra4-details">
        <summary><span>Family·Exit·후보 근거</span><strong>읽기 전용 상세</strong></summary>
        <div className="ra4-table-scroll" tabIndex={0}>
          <table className="ra4-family-table"><caption>Family 요약 · 미관측을 0% 성과로 해석하지 않음</caption><thead><tr><th>Family</th><th>후보</th><th>거래 G0→G1</th><th>양수 Fold</th><th>G1 결합손익</th><th>최대 MDD</th><th>Paired</th><th>DEV</th></tr></thead>
            <tbody>{autopsy.families.map(row => <tr key={row.familyId}><th>{row.familyId.replaceAll("_", " ")}</th><td>{row.candidateCount}</td><td>{row.g0Trades}→{row.g1Trades}</td><td>{row.positiveFolds}</td><td>{row.sumProfitPct == null ? "미관측" : `${_ra4Num(row.sumProfitPct)}%`}</td><td>{row.maxMddPct == null ? "미관측" : `${_ra4Num(row.maxMddPct)}%`}</td><td>{row.pairedPassCount}/{row.candidateCount}</td><td className="negative">{row.developmentPassCount}/{row.candidateCount}</td></tr>)}</tbody>
          </table>
        </div>
        <div className="ra4-detail-grid">
          <section><h3>Exit attribution</h3><p className="ra4-exit-note">손절 {stopLoss?.countDelta || 0}건 · 익절 {takeProfit?.countDelta || 0}건. 거래 감소만으로 개선을 주장하지 않습니다.</p><div className="ra4-table-scroll" tabIndex={0}><table><thead><tr><th>Exit</th><th>G0→G1</th><th>거래 Δ</th><th>손익 Δ 원</th></tr></thead><tbody>{autopsy.exits.map(row => <tr key={row.exitKind}><th>{row.exitKind}</th><td>{row.g0Count}→{row.g1Count}</td><td>{row.countDelta}</td><td className={row.pnlDeltaKrw >= 0 ? "positive" : "negative"}>{_ra4Signed(row.pnlDeltaKrw)}</td></tr>)}</tbody></table></div></section>
          <section><h3>후보별 근거 열기</h3><div className="ra4-candidates">{autopsy.candidates.map(row => <button type="button" key={row.candidateId} onClick={() => onInspectCandidate(row.candidateId)}><span>{row.familyId.replaceAll("_", " ")}</span><b>{row.metricsObserved ? `${row.positiveFolds}/4 양수 · ${_ra4Num(row.sumProfitPct)}%` : "미관측 · NO_TRADES"}</b><em>{row.pairedPass ? "PAIR SIGNAL" : "PAIR STOP"} · DEV STOP</em></button>)}</div></section>
        </div>
      </details>
      <footer>persistence none · threshold 변경 없음 · G2/Holdout/자동채택 권한 없음</footer>
    </section>
  );
}

Object.assign(window, { V516ResearchFailureAutopsy });
export { V516ResearchFailureAutopsy };
