/* v4-research-family.jsx — v5.16 read-only family explorer and fold heatmap. */
const { useEffect: useEffect_rf16, useMemo: useMemo_rf16, useState: useState_rf16 } = React;

function _rf16Text(value, fallback = "—") { return value == null || value === "" ? fallback : String(value); }
function _rf16Metric(row, keys) {
  for (const key of keys) {
    if (row && row[key] != null) return row[key];
    if (row && row.metrics && row.metrics[key] != null) return row.metrics[key];
  }
  return null;
}
function _rf16Tone(row) {
  const profit = Number(_rf16Metric(row, ["total_profit", "total_profit_amount", "profit", "profit_rate"]));
  const trades = Number(_rf16Metric(row, ["trade_count", "trades"]));
  if (!Number.isFinite(trades) || trades < 20) return "insufficient";
  if (!Number.isFinite(profit)) return "unknown";
  return profit > 0 ? "positive" : "negative";
}

function V516FamilyFoldExplorer({ baseUrl }) {
  const [state, setState] = useState_rf16({ status: "loading", families: [], folds: [], error: "" });
  const [selected, setSelected] = useState_rf16("ALL");
  useEffect_rf16(() => {
    const controller = new AbortController();
    const root = String(baseUrl || "").replace(/\/$/, "");
    Promise.all([
      fetch(root + "/research-program/families", { signal: controller.signal }).then(r => r.ok ? r.json() : Promise.reject(new Error(`families HTTP ${r.status}`))),
      fetch(root + "/research-program/folds", { signal: controller.signal }).then(r => r.ok ? r.json() : Promise.reject(new Error(`folds HTTP ${r.status}`))),
    ]).then(([families, folds]) => setState({ status: "ready", families: families.families || [], folds: folds.rows || [], error: "" }))
      .catch(error => { if (error.name !== "AbortError") setState({ status: "error", families: [], folds: [], error: String(error.message || error) }); });
    return () => controller.abort();
  }, [baseUrl]);
  const visible = useMemo_rf16(() => state.folds.filter(row => {
    if (selected === "ALL") return true;
    return [row.family, row.family_id, row.candidate_family].map(String).includes(selected);
  }), [state.folds, selected]);

  if (state.status === "loading") return <section className="rf16-panel pending" aria-live="polite"><h2>Family Explorer</h2><p>Family와 Fold Evidence를 불러오는 중입니다.</p></section>;
  if (state.status === "error") return <section className="rf16-panel danger" role="alert"><h2>Family/Fold 요청 실패</h2><p>{state.error}</p></section>;
  return (
    <section className="rf16-panel" aria-labelledby="rf16-title">
      <div className="rf16-heading"><div><span>V5.16 DEVELOPMENT EVIDENCE</span><h2 id="rf16-title">Family Explorer · Fold Heatmap</h2></div><label>Family 필터<select value={selected} onChange={event => setSelected(event.target.value)}><option value="ALL">전체</option>{state.families.map(item => <option key={item.family} value={item.family}>{item.family}</option>)}</select></label></div>
      <div className="rf16-family-grid" role="list" aria-label="연구 Family 목록">
        {state.families.length ? state.families.map(item => <button type="button" role="listitem" key={item.family} className={selected === item.family ? "active" : ""} onClick={() => setSelected(item.family)}><b>{item.family}</b><span>후보 {item.candidate_count}</span><span>국소통과 {item.local_advanced}</span><strong>{item.status}</strong></button>) : <p>Family Evidence가 없습니다.</p>}
      </div>
      <div className="rf16-fold-scroll" tabIndex={0} aria-label="Fold 성과 표. 색상과 함께 상태 텍스트를 제공합니다.">
        <table className="rf16-fold-table"><caption>Development fold evidence · OOS 아님</caption><thead><tr><th>단계</th><th>Family/Candidate</th><th>Fold</th><th>수익</th><th>평균</th><th>거래</th><th>MDD</th><th>상태</th></tr></thead><tbody>
          {visible.length ? visible.map((row, index) => { const tone = _rf16Tone(row); return <tr key={String(row.candidate_id || row.pair_id || row.family || "row") + index} className={tone}><td>{_rf16Text(row.phase)}</td><th>{_rf16Text(row.family || row.family_id || row.candidate_id || row.pair_id)}</th><td>{_rf16Text(row.fold_id || row.fold || row.period)}</td><td>{_rf16Text(_rf16Metric(row, ["total_profit", "total_profit_amount", "profit", "profit_rate"]))}</td><td>{_rf16Text(_rf16Metric(row, ["average_return", "avg_return", "average_profit_rate"]))}</td><td>{_rf16Text(_rf16Metric(row, ["trade_count", "trades"]))}</td><td>{_rf16Text(_rf16Metric(row, ["mdd", "max_drawdown"]))}</td><td><span className={`rf16-cell ${tone}`}>{tone === "positive" ? "양수" : tone === "negative" ? "음수" : tone === "insufficient" ? "표본부족" : "미확인"}</span></td></tr>; }) : <tr><td colSpan="8">선택된 Family의 Fold Evidence가 없습니다.</td></tr>}
        </tbody></table>
      </div>
      <p className="rf16-note">Heatmap 색상은 보조표현이며 표본·수익·MDD와 상태 텍스트가 판정 근거입니다.</p>
    </section>
  );
}

Object.assign(window, { V516FamilyFoldExplorer });
export { V516FamilyFoldExplorer };
