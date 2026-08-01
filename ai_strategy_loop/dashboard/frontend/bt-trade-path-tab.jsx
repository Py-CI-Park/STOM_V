/* QSP7 result workbench: bounded post-exit path, advisory replay, official pair. */
import { BtTradePathChart } from "./bt-trade-path-chart.jsx";
import { BtExitCounterfactual } from "./bt-exit-counterfactual.jsx";
import { BtConditionProposals } from "./bt-condition-proposals.jsx";
import { BtExitTransition } from "./bt-exit-transition.jsx";
const { useState: useState_tpt, useEffect: useEffect_tpt } = React;

function _tpFetch(url, options) {
  return fetch(url, options).then(response => response.ok ? response.json() : Promise.reject(new Error("HTTP " + response.status)));
}
function _tpMoney(value) { return Number(value || 0).toLocaleString() + "원"; }

function BtTradePathTab({ baseUrl, onNavigate }) {
  const [jobs, setJobs] = useState_tpt([]), [jobId, setJobId] = useState_tpt("");
  const [preflight, setPreflight] = useState_tpt(null), [analysis, setAnalysis] = useState_tpt(null);
  const [cohorts, setCohorts] = useState_tpt([]), [trades, setTrades] = useState_tpt([]);
  const [detail, setDetail] = useState_tpt(null), [cf, setCf] = useState_tpt(null);
  const [proposals, setProposals] = useState_tpt(null), [error, setError] = useState_tpt("");
  const [activeView, setActiveView] = useState_tpt("summary");
  const analysisId = analysis && analysis.analysis_id;

  useEffect_tpt(() => {
    if (!baseUrl) return;
    _tpFetch(baseUrl + "/bt/jobs").then(payload => {
      const rows = (payload && (payload.jobs || payload.items)) || [];
      const ready = rows.filter(row => row && row.status === "success" && row.csv_exists !== false);
      setJobs(ready); setJobId(current => current || (ready[0] && ready[0].job_id) || "");
    }).catch(reason => setError(String(reason.message || reason)));
  }, [baseUrl]);

  const inspect = () => {
    if (!jobId) return;
    setError("");
    _tpFetch(baseUrl + "/bt/trade-path/preflight?job_id=" + encodeURIComponent(jobId))
      .then(setPreflight).catch(reason => setError(String(reason.message || reason)));
  };
  const start = () => {
    if (!jobId) return;
    setError(""); setDetail(null); setCf(null); setProposals(null);
    _tpFetch(baseUrl + "/bt/trade-path/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_id: jobId }) })
      .then(setAnalysis).catch(reason => setError(String(reason.message || reason)));
  };

  useEffect_tpt(() => {
    if (!analysisId || ["success", "error", "cancelled"].includes(analysis.status)) return undefined;
    const timer = setTimeout(() => _tpFetch(baseUrl + "/bt/trade-path/jobs/" + encodeURIComponent(analysisId)).then(setAnalysis).catch(reason => setError(String(reason.message || reason))), 600);
    return () => clearTimeout(timer);
  }, [baseUrl, analysisId, analysis && analysis.status, analysis && analysis.progress]);

  useEffect_tpt(() => {
    if (!analysisId || analysis.status !== "success") return;
    Promise.all([
      _tpFetch(baseUrl + "/bt/trade-path/cohorts?analysis_id=" + encodeURIComponent(analysisId)),
      _tpFetch(baseUrl + "/bt/trade-path/trades?limit=100&analysis_id=" + encodeURIComponent(analysisId)),
    ]).then(([cohortPayload, tradePayload]) => { setCohorts(cohortPayload.cohorts || []); setTrades(tradePayload.trades || []); });
  }, [baseUrl, analysisId, analysis && analysis.status]);

  const openTrade = row => {
    setActiveView("path"); setDetail(null);
    _tpFetch(baseUrl + "/bt/trade-path/trade/" + encodeURIComponent(row.trade_key) + "?analysis_id=" + encodeURIComponent(analysisId))
      .then(payload => setDetail(payload.episode || null)).catch(reason => setError(String(reason.message || reason)));
  };
  const generateProposals = () => {
    _tpFetch(baseUrl + "/bt/trade-path/proposals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis_id: analysisId }) })
      .then(payload => { setProposals(payload); setActiveView("proposals"); });
  };
  const replay = () => {
    if (!detail) return;
    const source = analysis.source || {}, actual = detail.actual_exit || {};
    const context = { trade_key: detail.key && `${detail.key.run_id}:${detail.key.result_row_id}:${detail.key.stock_code}:${detail.key.buy_time}:${detail.key.entry_sequence || 0}`, name: detail.name, code: detail.key.stock_code, buy_time: detail.key.buy_time, sell_time: actual.timestamp, boundary: detail.forced_liquidation_timestamp };
    try {
      localStorage.setItem("stom_trade_path_context", JSON.stringify(context));
      localStorage.setItem("stom_replay_prefill", JSON.stringify({ date: String(detail.key.buy_time).slice(0, 8), code: detail.key.stock_code, src: detail.timeframe, buy: source.strategy_buy || "", sell: source.strategy_sell || "", reason: `거래 경로 · 실제매도 ${actual.reason || "미분류"}` }));
    } catch (ignored) {}
    if (onNavigate) onNavigate("replay");
  };

  const totals = analysis && analysis.summary;
  const running = analysis && ["queued", "running"].includes(analysis.status);
  return <section className="panel tp-workbench" aria-labelledby="tp-title">
    <header className="panel-hd"><div><div className="stom-section-label" id="tp-title">QSP7 · 거래 에피소드 / 매도 연구</div><div className="mono">실제 매도 뒤도 전체청산까지만 관찰 · 미실행 거래는 공식 엔진으로 재검증</div></div><div className="tp-authority-strip"><span className="tp-authority diagnostic">진단</span><span className="tp-authority advisory">자문</span><span className="tp-authority official">정본</span></div></header>
    <div className="panel-bd">
      <div className="tp-source-bar"><label>완료 결과<select value={jobId} onChange={event => { setJobId(event.target.value); setPreflight(null); }}><option value="">job 선택</option>{jobs.map(job => <option key={job.job_id} value={job.job_id}>{job.spec?.buy || ""} · {job.spec?.sell || ""} · {job.job_id}</option>)}</select></label><button className="btn ghost sm" onClick={inspect} disabled={!jobId}>사전 점검</button><button className="btn primary sm" onClick={start} disabled={!jobId || running}>경로 분석 시작</button>{running && <button className="btn danger sm" onClick={() => _tpFetch(baseUrl + `/bt/trade-path/jobs/${analysisId}/cancel`, { method: "POST" })}>취소</button>}</div>
      {preflight && <div className={`tp-preflight ${preflight.available ? "ready" : "blocked"}`}><b>{preflight.available ? "분석 가능" : "분석 불가"}</b><span>{preflight.available ? `거래 ${preflight.trade_count} · 날짜 ${preflight.covered_date_count}/${preflight.date_count} · ${preflight.source.timeframe}` : preflight.reason}</span><small>경계: 전체청산 이후 데이터는 존재해도 사용하지 않음</small></div>}
      {running && <div className="tp-progress" role="progressbar" aria-valuenow={Math.round((analysis.progress || 0) * 100)}><i style={{ width: `${Math.round((analysis.progress || 0) * 100)}%` }}/><span>{analysis.processed || 0}/{analysis.total || "?"} · {Math.round((analysis.progress || 0) * 100)}%</span></div>}
      {error && <p className="tp-error" role="alert">{error}</p>}
      {totals && <><nav className="tp-view-tabs" aria-label="거래 경로 분석 단계">{[["summary","요약·코호트"],["path","거래 경로"],["counterfactual","가상 매도"],["proposals","조건식 후보"],["official","공식 pair"]].map(([key,label]) => <button key={key} className={activeView === key ? "active" : ""} onClick={() => setActiveView(key)}>{label}</button>)}</nav>
        {activeView === "summary" && <div className="tp-summary"><div className="tp-summary-actions"><span className="tp-authority diagnostic">진단</span><button className="btn ghost sm" onClick={() => window.open(baseUrl + "/bt/trade-path/report?analysis_id=" + encodeURIComponent(analysisId), "_blank", "noopener")}>진단 보고서 열기</button></div><div className="tp-kpis"><article><small>분석 거래</small><b>{totals.analyzed_count}</b></article><article><small>제외</small><b>{totals.excluded_count}</b></article><article><small>경계 전 회복</small><b>{totals.recovered_count}</b></article><article><small>실제 순손익</small><b>{_tpMoney(totals.actual_profit_krw)}</b></article></div><div className="tp-cohorts">{cohorts.map(row => <button key={row.key} onClick={() => { const hit = trades.find(trade => trade.exit_reason === row.key); if (hit) openTrade(hit); }}><b>{row.key}</b><span>{row.count}건 · 회복 {row.recovered_count} · {_tpMoney(row.actual_profit_krw)}</span></button>)}</div><div className="tp-trade-list">{trades.slice(0, 30).map(row => <button key={row.trade_key} onClick={() => openTrade(row)}><span>{row.name}</span><code>{String(row.buy_time).slice(8)} → {String(row.sell_time).slice(8)}</code><b className={row.actual_profit_krw >= 0 ? "pos" : "neg"}>{_tpMoney(row.actual_profit_krw)}</b></button>)}</div></div>}
        {activeView === "path" && (detail ? <div><BtTradePathChart episode={detail}/><div className="tp-path-actions"><span className="tp-authority diagnostic">진단</span><span>가상 horizon은 실제 틱 지연과 검열 사유를 함께 보존합니다.</span><button className="btn primary sm" onClick={replay}>이 거래를 Replay에서 열기</button></div></div> : <div className="tp-empty">요약에서 거래를 선택하세요.</div>)}
        {activeView === "counterfactual" && <div><BtExitCounterfactual baseUrl={baseUrl} analysisId={analysisId} onResult={setCf}/>{cf && <div className="tp-cf-result"><b>가상 순손익 변화 {_tpMoney(cf.total_delta_profit_krw)}</b><span>평가 {cf.outcomes?.length || 0} · 제외 {cf.failures?.length || 0}</span>{(cf.transitions || []).map(row => <small key={`${row.actual_reason}-${row.candidate_reason}`}>{row.actual_reason} → {row.candidate_reason}: {row.count}</small>)}</div>}</div>}
        {activeView === "proposals" && <div><button className="btn primary sm" onClick={generateProposals}>근거 기반 후보 생성</button><BtConditionProposals proposals={proposals}/></div>}
        {activeView === "official" && <BtExitTransition baseUrl={baseUrl} jobs={jobs} baselineJobId={jobId}/>}</>}
    </div>
  </section>;
}

Object.assign(window, { BtTradePathTab });
export { BtTradePathTab };
