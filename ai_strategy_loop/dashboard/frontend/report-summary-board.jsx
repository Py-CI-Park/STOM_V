/* Data-backed summary for a selected registered report. Missing values stay explicit.
 *
 *   v5.11.3 — 보고서 메타데이터에 지표가 없으면 같은 run 의 연구 기록(/runs 발행 필드)에서
 *   가져온다. 값을 만들어내는 것이 아니라 이미 발행된 값을 연결하는 것이며, 어느 쪽에서
 *   왔는지를 항상 카드에 표시한다. 어디에도 없으면 그대로 `미발행` 이다.
 */
import { riAnnualizedPct } from "./research-improvement.jsx";

const _RS_SOURCE_LABEL = {
  report: "보고서 메타데이터",
  run: "연구 run 기록",
  derived: "파생값",
};

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

function _runSummaryNumber(runMeta, keys) {
  if (!runMeta || typeof runMeta !== "object") return null;
  for (const key of keys) {
    const value = Number(runMeta[key]);
    if (Number.isFinite(value)) return value;
  }
  return null;
}

// 보고서 → run 기록 순으로 찾고, 어디서 왔는지를 함께 돌려준다.
function reportSummaryResolve(report, runMeta, keys) {
  const fromReport = _reportSummaryNumber(report, keys);
  if (fromReport != null) return { value: fromReport, origin: "report" };
  const fromRun = _runSummaryNumber(runMeta, keys);
  if (fromRun != null) return { value: fromRun, origin: "run" };
  return { value: null, origin: null };
}

function _reportSummaryValue(value, suffix = "", digits = 1) {
  if (value == null) return "미발행";
  return `${value.toLocaleString("ko-KR", { maximumFractionDigits: digits })}${suffix}`;
}

function ReportSummaryBoard({ report, runMeta }) {
  if (!report) return <div className="v4-reports-empty mono">결과 보고서를 선택하세요.</div>;
  const cumulative = reportSummaryResolve(report, runMeta, ["total_profit_pct", "return_pct", "total_return_pct"]);
  const published = reportSummaryResolve(report, runMeta, ["annual_return_pct", "cagr", "cagr_pct"]);
  const years = Array.isArray(runMeta && runMeta.years) && runMeta.years.length ? runMeta.years.length : null;
  // 연평균이 발행되지 않았고 기간(연 수)이 확인되면 누적 수익률에서 환산한다(파생값 표기).
  const derivedAnnual = published.value == null && years
    ? riAnnualizedPct(cumulative.value, years)
    : null;
  const annual = published.value != null
    ? published
    : (derivedAnnual != null ? { value: derivedAnnual, origin: "derived" } : { value: null, origin: null });

  const metrics = [
    ["연평균 수익률", annual, "%", "annual_return_pct"],
    ["누적 수익률", cumulative, "%", "total_profit_pct"],
    ["MDD", reportSummaryResolve(report, runMeta, ["mdd_pct", "mdd", "max_drawdown_pct"]), "%", "mdd_pct"],
    ["일평균 거래", reportSummaryResolve(report, runMeta, ["daily_avg_trades", "avg_trades_per_day"]), "회", "daily_avg_trades"],
    ["하루 최대 보유", reportSummaryResolve(report, runMeta, ["max_hold_count", "max_holdings", "max_concurrent_positions"]), "종목", "max_hold_count"],
    ["총 거래", reportSummaryResolve(report, runMeta, ["trade_count", "trades"]), "건", "trade_count"],
  ];
  const digitsFor = (key) => (key === "trade_count" || key === "max_hold_count" ? 0 : 2);
  const visualMetrics = metrics.slice(0, 3).filter(([, entry]) => entry.value != null);
  const runLinked = metrics.some(([, entry]) => entry.origin === "run" || entry.origin === "derived");

  return (
    <section className="v4-report-summary-board" aria-labelledby="v4-report-summary-title">
      <header>
        <div>
          <div id="v4-report-summary-title" className="stom-section-label">결과 Summary · 운영 성과 보드</div>
          <p>
            보고서 메타데이터를 먼저 쓰고, 없으면 같은 run 의 연구 기록에서 이미 발행된 값을 가져옵니다.
            어느 쪽에도 없으면 추정하지 않고 <b>미발행</b>으로 둡니다. 값마다 출처를 함께 표시합니다.
          </p>
        </div>
        <span className="v4-report-summary-source mono">{report.research_id || report.run_id || report.title || "선택 보고서"}</span>
      </header>
      {runLinked && (
        <p className="v4-report-summary-note mono" role="note">
          이 보고서의 일부 지표는 run <b>{report.run_id}</b> 의 연구 기록에서 연결했습니다.
        </p>
      )}
      <div className="v4-report-summary-kpis">
        {metrics.map(([label, entry, suffix, key]) => (
          <article key={key} className={entry.value == null ? "missing" : ("origin-" + entry.origin)}>
            <span>{label}</span>
            <b>{_reportSummaryValue(entry.value, suffix, digitsFor(key))}</b>
            <small>{entry.origin ? `${key} · ${_RS_SOURCE_LABEL[entry.origin]}` : key}</small>
          </article>
        ))}
      </div>
      <div className="v4-report-summary-visual" aria-label="핵심 성과 상대 막대">
        {visualMetrics.length ? visualMetrics.map(([label, entry, suffix, key]) => (
          <div key={key} className={key === "mdd_pct" ? "risk" : entry.value < 0 ? "negative" : "positive"}>
            <span>{label}</span>
            <i><b style={{ width: `${Math.max(3, Math.min(100, Math.abs(entry.value)))}%` }}></b></i>
            <strong>{_reportSummaryValue(entry.value, suffix, 2)}</strong>
          </div>
        )) : <p className="mono">시각화 가능한 성과 지표가 아직 발행되지 않았습니다.</p>}
      </div>
      <div className="v4-report-summary-table-wrap">
        <table className="data-table"><caption>보고서 결과 Summary 지표</caption><thead><tr><th scope="col">지표</th><th scope="col">값</th><th scope="col">원천 필드</th><th scope="col">출처</th></tr></thead>
          <tbody>{metrics.map(([label, entry, suffix, key]) => (
            <tr key={key}>
              <th scope="row">{label}</th>
              <td>{_reportSummaryValue(entry.value, suffix, digitsFor(key))}</td>
              <td className="mono">{key}</td>
              <td className="mono">{entry.origin ? _RS_SOURCE_LABEL[entry.origin] : "—"}</td>
            </tr>
          ))}</tbody></table>
      </div>
    </section>
  );
}

Object.assign(window, { ReportSummaryBoard, reportSummaryResolve });

export { ReportSummaryBoard, reportSummaryResolve };
