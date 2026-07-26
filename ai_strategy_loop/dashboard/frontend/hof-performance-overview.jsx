/* Compact, data-backed performance visuals for the Performance tab. */
function _hofOverviewNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function HofPerformanceOverview({ humanRows, catalogRows }) {
  const human = Array.isArray(humanRows) ? humanRows : [];
  const ai = Array.isArray(catalogRows) ? catalogRows : [];
  const points = [
    ...human.map(row => ({ label: row.label, kind: "human", ret: _hofOverviewNumber(row.total_return_pct), mdd: _hofOverviewNumber(row.mdd_pct) })),
    ...ai.map(row => ({ label: row.label || `${row.run_id}/g${row.gen_no}`, kind: "ai", ret: _hofOverviewNumber(row.return_pct), mdd: _hofOverviewNumber(row.mdd_pct) })),
  ].filter(point => point.ret != null && point.mdd != null);
  const outcomes = ["success", "loss", "failure", "no_trade", "unavailable"].map(key => ({
    key,
    count: ai.filter(row => String(row.outcome || "unavailable").toLowerCase() === key).length,
  }));
  const maxOutcome = Math.max(1, ...outcomes.map(item => item.count));
  const retValues = points.map(point => point.ret);
  const mddValues = points.map(point => Math.abs(point.mdd));
  const retMin = Math.min(0, ...retValues);
  const retMax = Math.max(1, ...retValues);
  const mddMax = Math.max(1, ...mddValues);
  const x = value => 42 + (Math.abs(value) / mddMax) * 316;
  const y = value => 196 - ((value - retMin) / (retMax - retMin || 1)) * 164;
  const passed = ai.filter(row => row.gate_passed === true).length;
  const positive = ai.filter(row => _hofOverviewNumber(row.return_pct) > 0).length;
  const avgDailyRows = ai.map(row => _hofOverviewNumber(row.daily_avg_trades)).filter(value => value != null);
  const avgDaily = avgDailyRows.length ? avgDailyRows.reduce((sum, value) => sum + value, 0) / avgDailyRows.length : null;
  return (
    <section className="hof-performance-overview" aria-label="성과 시각화 요약">
      <article className="panel performance-scatter">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>수익률 × MDD</div><span className="mono">실제 지표 {points.length}건</span></div>
        <div className="panel-bd">
          {points.length ? <svg viewBox="0 0 380 220" role="img" aria-label="수익률과 MDD 산점도">
            <line x1="42" x2="358" y1={y(0)} y2={y(0)} stroke="var(--line-2)" strokeDasharray="4 4" />
            <line x1="42" x2="42" y1="24" y2="196" stroke="var(--line-2)" />
            <line x1="42" x2="358" y1="196" y2="196" stroke="var(--line-2)" />
            {points.map((point, index) => <circle key={`${point.kind}-${point.label}-${index}`} cx={x(point.mdd)} cy={y(point.ret)} r={point.kind === "human" ? 5 : 3.5} fill={point.kind === "human" ? "var(--green)" : "var(--violet)"} fillOpacity=".78"><title>{point.label} · 수익 {point.ret.toFixed(2)}% · MDD {point.mdd.toFixed(2)}%</title></circle>)}
            <text x="200" y="215" textAnchor="middle" fill="var(--ink-3)" fontSize="11">MDD 절대값 (%)</text>
            <text x="12" y="110" textAnchor="middle" fill="var(--ink-3)" fontSize="11" transform="rotate(-90 12 110)">수익률 (%)</text>
          </svg> : <div className="research-empty">수익률과 MDD가 함께 발행된 결과가 없습니다.</div>}
        </div>
      </article>
      <article className="panel performance-distribution">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--violet)" }}></span>AI 결과 분포</div><span className="mono">로드 {ai.length}건</span></div>
        <div className="panel-bd hof-outcome-bars">
          {outcomes.map(item => <div key={item.key}><span>{item.key}</span><i><b style={{ width: `${item.count / maxOutcome * 100}%` }}></b></i><strong>{item.count}</strong></div>)}
        </div>
      </article>
      <article className="panel hof-performance-kpis">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>연구 운영 요약</div></div>
        <div className="panel-bd">
          <div><span>gate 통과</span><b>{passed}/{ai.length || "—"}</b></div>
          <div><span>양(+) 수익 결과</span><b>{positive}/{ai.length || "—"}</b></div>
          <div><span>평균 일거래</span><b>{avgDaily == null ? "미발행" : avgDaily.toFixed(2) + "회"}</b></div>
          <div><span>인간 벤치마크</span><b>{human.length}건</b></div>
        </div>
      </article>
    </section>
  );
}

export { HofPerformanceOverview };
