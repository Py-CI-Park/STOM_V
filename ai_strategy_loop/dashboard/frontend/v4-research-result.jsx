/* v4-research-result.jsx — UX-04 mission control over the sealed UX-03 gateboard. */
const { useCallback: useCallback_rr3, useEffect: useEffect_rr3, useState: useState_rr3 } = React;

const _RR3_FAILURES = Object.freeze({
  EXECUTION_OR_SOURCE: "실행·원본",
  MIN_TRADES_EACH_FOLD: "Fold 거래수",
  MIN_POSITIVE_TOTAL_PROFIT_FOLDS: "양수 Fold",
  COMBINED_TOTAL_PROFIT: "결합 손익",
  COMBINED_AVG_PROFIT: "거래가중 평균",
  MAX_MDD_EACH_FOLD: "MDD 상한",
  PAIR_METRICS_UNAVAILABLE: "짝지표 미관측",
  MEDIAN_AVG_PROFIT_DELTA_NOT_POSITIVE: "중앙 개선 없음",
  WORST_FOLD_TOTAL_PROFIT_DELTA_NEGATIVE: "최악 Fold 악화",
});

function _rr3Num(value, digits = 2) {
  return value == null || Number.isNaN(Number(value)) ? "미관측" : Number(value).toFixed(digits);
}

function _rr3DeltaClass(value, zeroIsPositive = false) {
  if (value == null || Number.isNaN(Number(value))) return "";
  return zeroIsPositive ? (Number(value) >= 0 ? "positive" : "negative") : (Number(value) > 0 ? "positive" : "negative");
}

function _rr3CandidateLabel(row) {
  const suffix = String(row.candidate_id || "").split("_MCAP_A_LT3000_").pop();
  return `${String(row.family_id || "UNKNOWN").replaceAll("_", " ")} · ${suffix}`;
}

function _Rr3Rail({ label, value, detail, tone }) {
  return <article className={`rr3-rail ${tone}`}><span>{label}</span><strong>{value}</strong><p>{detail}</p></article>;
}

function _Rr4MissionControl({ platform, decision, detailOpen, onToggleDetail }) {
  const candidateCount = decision.candidate_count || 0;
  const developmentPassCount = decision.development_pass_count || 0;
  const pairedPassCount = decision.paired_pass_count || 0;
  return (
    <section className="rr4-mission" aria-labelledby="rr4-title">
      <header className="rr4-heading">
        <div><span>UX-04 · MISSION CONTROL</span><h2 id="rr4-title">Research Mission Control</h2></div>
        <strong>정상 중단</strong>
      </header>
      <p className="rr4-lede">공식 실행은 완료됐지만 경제 기준을 통과한 후보가 없어 연구가 안전하게 멈췄습니다.</p>
      <div className="rr4-status-grid" role="list" aria-label="현재 연구 판단 요약">
        <article className="complete" role="listitem"><span>실행 상태</span><strong>G1 {platform.valid_jobs || 0}/{platform.total_jobs || 0} VALID</strong><p>실행·원본·분석 번들 확인 완료</p></article>
        <article className="stopped" role="listitem"><span>왜 멈췄나</span><strong>Development Rule {developmentPassCount}/{candidateCount}</strong><p>짝신호 {pairedPassCount}/{candidateCount}는 승격 근거가 아닙니다.</p></article>
        <article className="allowed" role="listitem"><span>지금 허용된 행동</span><strong>읽기 전용 실패 부검</strong><p>결과를 바꾸지 않고 Fold·Exit·계보만 검토</p></article>
      </div>
      <ol className="rr4-roadmap" aria-label="G0에서 현재 중단까지의 연구 흐름">
        <li className="done"><span>01</span><b>G0 실행</b><small>28 jobs</small></li>
        <li className="done"><span>02</span><b>G1 실행</b><small>{platform.valid_jobs || 0}/{platform.total_jobs || 0}</small></li>
        <li className="signal"><span>03</span><b>짝비교</b><small>{pairedPassCount}/{candidateCount}</small></li>
        <li className="stop"><span>04</span><b>경제 Gate</b><small>{developmentPassCount}/{candidateCount}</small></li>
        <li className="locked"><span>05</span><b>G2/Holdout</b><small>차단</small></li>
      </ol>
      <div className="rr4-policy">
        <p><b>G2 · Holdout · 자동채택 차단</b><span>{decision.next_gate || "STOP_NO_G2_NO_HOLDOUT"}</span></p>
        <button type="button" className="btn ghost sm" aria-expanded={detailOpen} aria-controls="rr4-evidence-detail" onClick={onToggleDetail}>{detailOpen ? "판정 근거 접기" : "판정 근거 펼치기"}</button>
      </div>
      <p className="rr4-prereg">새 연구는 별도 사전등록 후 새 프로그램에서만 시작할 수 있습니다.</p>
    </section>
  );
}

function _Rr3FoldMatrix({ candidate }) {
  return (
    <div className="rr3-table-scroll" tabIndex={0} aria-label="같은 부모와 같은 Fold의 G0 G1 비교표">
      <table className="rr3-fold-table">
        <caption>G0 → G1 동일 Fold · 평균 개선과 최악 손익 방어를 별도 확인</caption>
        <thead><tr><th>Fold</th><th>실행</th><th>거래 G0→G1</th><th>평균 Δ %p</th><th>총손익 Δ %p</th><th>G1 MDD %</th></tr></thead>
        <tbody>{candidate.folds.map(row => (
          <tr key={row.fold_id} className={row.g1_metrics_observed ? "observed" : "unobserved"}>
            <th>{String(row.fold_id).replace("DEV_", "")}</th>
            <td><span className={`rr3-status ${String(row.g1_execution).toLowerCase()}`}>{row.g1_execution}</span></td>
            <td>{row.g0_trade_count} → <b>{row.g1_trade_count}</b></td>
            <td className={_rr3DeltaClass(row.avg_profit_pct_delta)}>{_rr3Num(row.avg_profit_pct_delta)}</td>
            <td className={_rr3DeltaClass(row.total_profit_pct_delta, true)}>{_rr3Num(row.total_profit_pct_delta)}</td>
            <td className={row.g1_mdd_pct != null && Number(row.g1_mdd_pct) > 15 ? "negative" : ""}>{_rr3Num(row.g1_mdd_pct)}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function _Rr3ExitDelta({ candidate }) {
  return (
    <div className="rr3-exits">
      <h4>Exit attribution · 거래수와 손익 변화</h4>
      <div className="rr3-table-scroll" tabIndex={0}>
        <table><thead><tr><th>청산</th><th>거래 G0→G1</th><th>Δ</th><th>손익 Δ 원</th></tr></thead>
          <tbody>{candidate.exits.map(row => <tr key={row.exit_kind}><th>{row.exit_kind}</th><td>{row.g0_count} → {row.g1_count}</td><td>{row.count_delta > 0 ? "+" : ""}{row.count_delta}</td><td className={row.pnl_delta_krw >= 0 ? "positive" : "negative"}>{Math.round(row.pnl_delta_krw).toLocaleString("ko-KR")}</td></tr>)}</tbody>
        </table>
      </div>
    </div>
  );
}

function _Rr3CandidateDetail({ candidate }) {
  const pairFailures = candidate.paired_failures || [];
  const developmentFailures = candidate.development_failures || [];
  return (
    <section className="rr3-detail" aria-live="polite">
      <header><div><span>SELECTED LINEAGE</span><h3>{_rr3CandidateLabel(candidate)}</h3></div><div className="rr3-detail-badges"><b className={candidate.paired_falsification_pass ? "signal" : "blocked"}>PAIR {candidate.paired_falsification_pass ? "SIGNAL" : "REFUTED"}</b><b className={candidate.development_rule_pass ? "signal" : "blocked"}>DEV {candidate.development_rule_pass ? "PASS" : "STOP"}</b></div></header>
      <div className="rr3-lineage"><code>{candidate.parent_candidate_id}</code><span aria-hidden="true">＋</span><mark>{candidate.added_guard_source}</mark><span aria-hidden="true">→</span><code>{candidate.candidate_id}</code></div>
      <div className="rr3-kpis" role="list" aria-label="선택 후보 핵심 지표">
        <div role="listitem"><span>거래</span><b>{candidate.g0_total_trades} → {candidate.g1_total_trades}</b></div>
        <div role="listitem"><span>양수 Fold</span><b>{candidate.g1_positive_fold_count}/4</b></div>
        <div role="listitem"><span>G1 결합 손익</span><b>{_rr3Num(candidate.g1_sum_total_profit_pct)}%</b></div>
        <div role="listitem"><span>짝 중앙 Δ</span><b>{_rr3Num(candidate.median_fold_avg_profit_delta)}%p</b></div>
        <div role="listitem"><span>최악 Fold Δ</span><b>{_rr3Num(candidate.worst_fold_total_profit_delta)}%p</b></div>
        <div role="listitem"><span>최대 MDD</span><b>{_rr3Num(candidate.g1_max_fold_mdd_pct)}%</b></div>
      </div>
      <_Rr3FoldMatrix candidate={candidate} />
      <div className="rr3-rule-grid">
        <div><h4>짝비교 판정</h4><p>{pairFailures.length ? pairFailures.map(key => <span key={key}>{_RR3_FAILURES[key] || key}</span>) : <span className="pass">두 조건 통과</span>}</p></div>
        <div><h4>개발 규칙 차단</h4><p>{developmentFailures.map(key => <span key={key}>{_RR3_FAILURES[key] || key}</span>)}</p></div>
      </div>
      <_Rr3ExitDelta candidate={candidate} />
    </section>
  );
}

function V516ResearchResultGateboard({ baseUrl }) {
  const [view, setView] = useState_rr3({ status: "loading", data: null, error: "" });
  const [selectedId, setSelectedId] = useState_rr3("");
  const [detailOpen, setDetailOpen] = useState_rr3(false);
  const load = useCallback_rr3(() => {
    const controller = new AbortController();
    setView(current => ({ ...current, status: "loading", error: "" }));
    fetch(String(baseUrl || "").replace(/\/$/, "") + "/research-result/current", { signal: controller.signal })
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(data => setView({ status: "ready", data, error: "" }))
      .catch(error => { if (error && error.name !== "AbortError") setView({ status: "error", data: null, error: String(error.message || error) }); });
    return () => controller.abort();
  }, [baseUrl]);
  useEffect_rr3(() => load(), [load]);
  const candidates = view.data && view.data.analysis && view.data.analysis.candidates || [];
  useEffect_rr3(() => { if (candidates.length && !candidates.some(row => row.candidate_id === selectedId)) setSelectedId(candidates[0].candidate_id); }, [candidates, selectedId]);
  if (view.status === "loading" && !view.data) return <section className="rr3-gateboard pending" aria-live="polite"><h2>RES-03 Decision Gateboard</h2><p>봉인된 G0/G1 증거를 검증하는 중입니다.</p></section>;
  if (view.status === "error") return <section className="rr3-gateboard danger" role="alert"><h2>RES-03 결과를 열 수 없습니다</h2><p>{view.error}</p><button type="button" className="btn" onClick={load}>다시 시도</button></section>;
  const data = view.data || {};
  const platform = data.platform || {};
  const decision = data.decision || {};
  const selected = candidates.find(row => row.candidate_id === selectedId) || candidates[0];
  return (
    <div className="rr3-gateboard rr4-shell">
      <_Rr4MissionControl platform={platform} decision={decision} detailOpen={detailOpen} onToggleDetail={() => setDetailOpen(open => !open)} />
      <details className="rr4-evidence" id="rr4-evidence-detail" open={detailOpen} onToggle={event => setDetailOpen(event.currentTarget.open)}>
        <summary><span>UX-03 봉인 판정 근거</span><strong>{detailOpen ? "판정 근거 접기" : "판정 근거 펼치기"}</strong></summary>
        <header className="rr3-heading"><div><span>UX-03 · SEALED DECISION / READ ONLY</span><h2 id="rr3-title">G0 → G1 연구 게이트보드</h2></div><strong>{decision.holdout_status || "UNKNOWN"}</strong></header>
        <div className="rr3-rails">
          <_Rr3Rail label="PLATFORM GATE" value={`${platform.valid_jobs || 0}/${platform.total_jobs || 0} VALID`} detail={`SUCCESS ${platform.success_jobs || 0} · NO_TRADES ${platform.no_trades_jobs || 0} · source/bundle ${platform.source_match_jobs || 0}/${platform.analysis_bundle_jobs || 0}`} tone="valid" />
          <_Rr3Rail label="ECONOMIC GATE" value={`${decision.development_pass_count || 0}/${decision.candidate_count || 0} · STOP`} detail="실행은 성공했지만 절대 개발 기준을 통과한 전략은 없습니다." tone="stop" />
          <_Rr3Rail label="PAIRED SIGNAL" value={`${decision.paired_pass_count || 0}/${decision.candidate_count || 0}`} detail="부모 대비 구조 신호일 뿐 승격·수익성 증거가 아닙니다." tone="signal" />
        </div>
        <div className="rr3-lock" role="status"><b>NEXT · {decision.next_gate || "STOP"}</b><span>G2 금지 · Holdout 미개봉 · 자동채택 불가 · DEVELOPMENT ONLY</span></div>
        <div className="rr3-body">
          <nav className="rr3-candidates" aria-label="G1 후보 선택"><h3>7 candidates</h3>{candidates.map(row => <button type="button" key={row.candidate_id} aria-pressed={row.candidate_id === selectedId} onClick={() => setSelectedId(row.candidate_id)}><span>{_rr3CandidateLabel(row)}</span><b>{row.g1_total_trades} trades</b><em>{row.paired_falsification_pass ? "PAIR SIGNAL" : "PAIR STOP"} · DEV STOP</em></button>)}</nav>
          {selected && <_Rr3CandidateDetail candidate={selected} />}
        </div>
        <footer>Evidence {String(data.evidence && data.evidence[1] && data.evidence[1].sha256 || "unavailable").slice(0, 16)}… · persistence none · 경제 실패를 실행 실패로 바꾸지 않습니다.</footer>
      </details>
    </div>
  );
}

Object.assign(window, { V516ResearchResultGateboard });
export { V516ResearchResultGateboard };
