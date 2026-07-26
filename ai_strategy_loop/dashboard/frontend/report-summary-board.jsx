/* Data-backed summary for a selected registered report. Missing values stay explicit. */
function _reportSummaryNumber(report, keys) {
  const sources = [report, report && report.metrics, report && report.evidence, report && report.profile];
  for (const source of sources) {
    if (!source || typeof source !== "object") continue;
    for (const key of keys) {
      const value = Number(source[key]);
      if (Number.isFinite(value)) return value;
    }
  }
  return null;
}

function _reportSummaryValue(value, suffix = "", digits = 1) {
  if (value == null) return "미발행";
  return `${value.toLocaleString("ko-KR", { maximumFractionDigits: digits })}${suffix}`;
}

function ReportSummaryBoard({ report }) {
  if (!report) return <div className="v4-reports-empty mono">결과 보고서를 선택하세요.</div>;
  const metrics = [
    ["연평균 수익률", _reportSummaryNumber(report, ["annual_return_pct", "cagr", "cagr_pct"]), "%", "annual_return_pct"],
    ["누적 수익률", _reportSummaryNumber(report, ["total_profit_pct", "return_pct", "total_return_pct"]), "%", "total_profit_pct"],
    ["MDD", _reportSummaryNumber(report, ["mdd_pct", "mdd", "max_drawdown_pct"]), "%", "mdd_pct"],
    ["일평균 거래", _reportSummaryNumber(report, ["daily_avg_trades", "avg_trades_per_day"]), "회", "daily_avg_trades"],
    ["하루 최대 보유", _reportSummaryNumber(report, ["max_hold_count", "max_holdings", "max_concurrent_positions"]), "종목", "max_hold_count"],
    ["총 거래", _reportSummaryNumber(report, ["trade_count", "trades"]), "건", "trade_count"],
  ];
  const visualMetrics = metrics.slice(0, 3).filter(([, value]) => value != null);
  return (
    <section className="v4-report-summary-board" aria-labelledby="v4-report-summary-title">
      <header>
        <div>
          <div id="v4-report-summary-title" className="stom-section-label">결과 Summary · 운영 성과 보드</div>
          <p>정본 메타데이터에 실제 발행된 값만 표시합니다. 없는 값은 추정하지 않습니다.</p>
        </div>
        <span className="v4-report-summary-source mono">{report.research_id || report.run_id || report.title || "선택 보고서"}</span>
      </header>
      <div className="v4-report-summary-kpis">
        {metrics.map(([label, value, suffix, key]) => (
          <article key={key} className={value == null ? "missing" : ""}>
            <span>{label}</span><b>{_reportSummaryValue(value, suffix, key === "trade_count" || key === "max_hold_count" ? 0 : 2)}</b><small>{key}</small>
          </article>
        ))}
      </div>
      <div className="v4-report-summary-visual" aria-label="핵심 성과 상대 막대">
        {visualMetrics.length ? visualMetrics.map(([label, value, suffix, key]) => (
          <div key={key} className={key === "mdd_pct" ? "risk" : value < 0 ? "negative" : "positive"}>
            <span>{label}</span><i><b style={{ width: `${Math.max(3, Math.min(100, Math.abs(value)))}%` }}></b></i><strong>{_reportSummaryValue(value, suffix, 2)}</strong>
          </div>
        )) : <p className="mono">시각화 가능한 성과 지표가 아직 발행되지 않았습니다.</p>}
      </div>
      <div className="v4-report-summary-table-wrap">
        <table className="data-table"><caption>보고서 결과 Summary 지표</caption><thead><tr><th scope="col">지표</th><th scope="col">값</th><th scope="col">원천 필드</th></tr></thead>
          <tbody>{metrics.map(([label, value, suffix, key]) => <tr key={key}><th scope="row">{label}</th><td>{_reportSummaryValue(value, suffix, key === "trade_count" || key === "max_hold_count" ? 0 : 2)}</td><td className="mono">{key}</td></tr>)}</tbody></table>
      </div>
    </section>
  );
}

export { ReportSummaryBoard };
