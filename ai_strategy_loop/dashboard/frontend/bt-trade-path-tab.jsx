/* QSP7 result workbench: bounded post-exit path, advisory replay, official pair. */
import { BtTradePathChart } from "./bt-trade-path-chart.jsx";
import { BtExitCounterfactual } from "./bt-exit-counterfactual.jsx";
import { BtConditionProposals } from "./bt-condition-proposals.jsx";
import { BtExitTransition } from "./bt-exit-transition.jsx";
import { BtDataContract } from "./bt-data-contract.jsx";
import { BtEntryAutopsy } from "./bt-entry-autopsy.jsx";
import { BtSellDslTrace } from "./bt-sell-dsl-trace.jsx";
import { BtOosGate } from "./bt-oos-gate.jsx";
import { BtCandidateConsole } from "./bt-candidate-console.jsx";
import { BtRecoveryInsight } from "./bt-recovery-insight.jsx";
import { BtCalibration } from "./bt-calibration.jsx";
import { BtLedgerBrowser } from "./bt-ledger-browser.jsx";
import { _tpKo, _tpNextHint } from "./bt-tp-messages.jsx";
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
  const [dataContract, setDataContract] = useState_tpt(null);
  const [boundaryTime, setBoundaryTime] = useState_tpt("");
  const [activeView, setActiveView] = useState_tpt("data");
  const [lane, setLane] = useState_tpt("min");
  const [laneManifest, setLaneManifest] = useState_tpt(null);
  const [selectedProposalId, setSelectedProposalId] = useState_tpt("");
  const analysisId = analysis && analysis.analysis_id;

  const resetForLane = () => {
    setJobId(""); setPreflight(null); setDataContract(null); setBoundaryTime("");
    setAnalysis(null); setCohorts([]); setTrades([]); setDetail(null); setCf(null);
    setProposals(null); setSelectedProposalId(""); setActiveView("data");
  };

  useEffect_tpt(() => {
    if (!baseUrl) return;
    // 레인 전환은 하위 상태를 전부 초기화한다 — tick/min 교차 오염 방지(P1-6).
    _tpFetch(baseUrl + "/bt/trade-path/lane-manifest?lane=" + encodeURIComponent(lane))
      .then(payload => setLaneManifest(payload.available ? payload : null))
      .catch(reason => setError(_tpKo(String(reason.message || reason))));
    _tpFetch(baseUrl + "/bt/jobs").then(payload => {
      const rows = (payload && (payload.jobs || payload.items)) || [];
      const ready = rows.filter(row => row && row.status === "success" && row.csv_exists !== false
        && ((row.spec && row.spec.timeframe) || "min") === lane);
      setJobs(ready); setJobId(current => (ready.some(row => row.job_id === current) ? current : (ready[0] && ready[0].job_id) || ""));
    }).catch(reason => setError(_tpKo(String(reason.message || reason))));
  }, [baseUrl, lane]);

  const inspect = () => {
    if (!jobId) return;
    setError("");
    const boundaryQuery = boundaryTime ? "&forced_liquidation_time=" + encodeURIComponent(boundaryTime) : "";
    Promise.all([
      _tpFetch(baseUrl + "/bt/trade-path/preflight?job_id=" + encodeURIComponent(jobId) + boundaryQuery),
      _tpFetch(baseUrl + "/bt/trade-path/data-contract?job_id=" + encodeURIComponent(jobId)),
    ]).then(([payload, contractPayload]) => { setPreflight(payload); setDataContract(contractPayload.contract || null); setActiveView("data"); if (payload.forced_liquidation_time) setBoundaryTime(String(payload.forced_liquidation_time).padStart(6, "0")); })
      .catch(reason => setError(_tpKo(String(reason.message || reason))));
  };
  const start = () => {
    if (!jobId || !preflight?.available || !boundaryTime) return;
    setError(""); setDetail(null); setCf(null); setProposals(null);
    _tpFetch(baseUrl + "/bt/trade-path/jobs", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_id: jobId, forced_liquidation_time: Number(boundaryTime) }) })
      .then(setAnalysis).catch(reason => setError(_tpKo(String(reason.message || reason))));
  };

  useEffect_tpt(() => {
    if (!analysisId || ["success", "error", "cancelled"].includes(analysis.status)) return undefined;
    const timer = setTimeout(() => _tpFetch(baseUrl + "/bt/trade-path/jobs/" + encodeURIComponent(analysisId)).then(setAnalysis).catch(reason => setError(_tpKo(String(reason.message || reason)))), 600);
    return () => clearTimeout(timer);
  }, [baseUrl, analysisId, analysis]);

  useEffect_tpt(() => {
    if (!analysisId || analysis.status !== "success") return;
    Promise.all([
      _tpFetch(baseUrl + "/bt/trade-path/cohorts?analysis_id=" + encodeURIComponent(analysisId)),
      _tpFetch(baseUrl + "/bt/trade-path/trades?limit=100&analysis_id=" + encodeURIComponent(analysisId)),
    ]).then(([cohortPayload, tradePayload]) => { setCohorts(cohortPayload.cohorts || []); setTrades(tradePayload.trades || []); })
      .catch(reason => setError(_tpKo(String(reason.message || reason))));
  }, [baseUrl, analysisId, analysis && analysis.status]);

  const openTrade = row => {
    setActiveView("path"); setDetail(null);
    _tpFetch(baseUrl + "/bt/trade-path/trade/" + encodeURIComponent(row.trade_key) + "?analysis_id=" + encodeURIComponent(analysisId))
      .then(payload => setDetail(payload.episode || null)).catch(reason => setError(_tpKo(String(reason.message || reason))));
  };
  const generateProposals = () => {
    _tpFetch(baseUrl + "/bt/trade-path/proposals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ analysis_id: analysisId }) })
      .then(payload => { setProposals(payload); setActiveView("proposals"); })
      .catch(reason => setError(_tpKo(String(reason.message || reason))));
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
  const proposalRows = (proposals && proposals.proposals) || [];
  const selectedProposal = proposalRows.find(row => row.proposal_id === selectedProposalId) || null;
  const pageTabs = [["data","데이터 계약"],["entry","매수 해부"],...(totals ? [["summary","매도 해부"],["path","거래 경로"],...(detail ? [["sell-trace","매도식 추적"]] : []),["counterfactual","가상 매도"],["insight","회복 판별"],["proposals","조건식 후보"],["console","후보 실행"],["official","공식 pair"],["oos","OOS 채택"],["calibration","캘리브레이션"]] : []),["ledger","원장"]];
  const manifestRow = laneManifest && laneManifest.manifest;
  return <section className="panel tp-workbench" aria-labelledby="tp-title">
    <header className="panel-hd"><div><div className="stom-section-label" id="tp-title">QSP7 · 거래 에피소드 / 매도 연구</div><div className="mono">실제 매도 뒤도 전체청산까지만 관찰 · 미실행 거래는 공식 엔진으로 재검증</div></div><div className="tp-authority-strip"><span className={`tp-lane-badge ${lane}`}>{lane}</span><span className="tp-authority diagnostic">진단</span><span className="tp-authority advisory">자문</span><span className="tp-authority official">정본</span></div></header>
    <div className="panel-bd">
      <div className="tp-lane-bar" role="tablist" aria-label="연구 레인 선택">
        {["min","tick"].map(name => <button key={name} role="tab" aria-selected={lane === name} className={lane === name ? "active" : ""} onClick={() => { if (name !== lane) { setLane(name); resetForLane(); } }}>{name} 레인</button>)}
        {manifestRow && <span className="tp-lane-manifest mono">설계 {manifestRow.design.start}~{manifestRow.design.end} · OOS {manifestRow.oos.start}~{manifestRow.oos.end} · 세션 ~{String(manifestRow.session_end).padStart(6, "0")}{laneManifest.baseline_registered ? "" : " · ⚠ 기준선 미등록"}</span>}
      </div>
      <div className="tp-source-bar"><label>완료 결과<select value={jobId} onChange={event => { setJobId(event.target.value); setBoundaryTime(""); setPreflight(null); setDataContract(null); setActiveView("data"); setAnalysis(null); setCohorts([]); setTrades([]); setDetail(null); }}><option value="">job 선택</option>{jobs.map(job => <option key={job.job_id} value={job.job_id}>{job.spec?.buy || ""} · {job.spec?.sell || ""} · {job.job_id}</option>)}</select></label><label>전체청산 (HHMMSS)<input value={boundaryTime} inputMode="numeric" maxLength="6" placeholder="자동 판별" onChange={event => { setBoundaryTime(event.target.value.replace(/\D/g, "").slice(0, 6)); setPreflight(null); }}/></label><button className="btn ghost sm" onClick={inspect} disabled={!jobId}>사전 점검</button><button className="btn primary sm" onClick={start} disabled={!jobId || !preflight?.available || running}>경로 분석 시작</button>{running && <button className="btn danger sm" onClick={() => _tpFetch(baseUrl + `/bt/trade-path/jobs/${analysisId}/cancel`, { method: "POST" }).catch(reason => setError(_tpKo(String(reason.message || reason))))}>취소</button>}</div>
      {preflight && <div className={`tp-preflight ${preflight.available ? "ready" : "blocked"}`}><b>{preflight.available ? "분석 가능" : "분석 불가"}</b><span>{preflight.available ? `거래 ${preflight.trade_count} · 날짜 ${preflight.covered_date_count}/${preflight.date_count} · ${preflight.source.timeframe}` : `${_tpKo(preflight.reason)}${preflight.exit_after_boundary_count ? ` · 경계 뒤 실제 매도 ${preflight.exit_after_boundary_count}건` : ""}`}</span>{(preflight.uncovered_dates || []).length > 0 && <span className="tp-uncovered">⚠ 데이터 없는 날짜 {preflight.date_count - preflight.covered_date_count}일: {preflight.uncovered_dates.slice(0, 6).join(", ")}{preflight.uncovered_dates.length > 6 ? " …" : ""}</span>}<small>전체청산 {String(preflight.forced_liquidation_time || "").padStart(6, "0")} · {preflight.boundary_source || "미확인"} · 전체청산 이후 데이터는 존재해도 사용하지 않음</small></div>}
      {dataContract && <nav className="tp-view-tabs" aria-label="통합 백테스트 연구 단계">{pageTabs.map(([key,label]) => <button key={key} className={activeView === key ? "active" : ""} onClick={() => setActiveView(key)}>{label}</button>)}</nav>}
      {dataContract && _tpNextHint(activeView) && <div className="tp-next-hint">{_tpNextHint(activeView)}</div>}
      {dataContract && activeView === "data" && <div aria-label="데이터 계약"><BtDataContract contract={dataContract}/></div>}
      {dataContract && activeView === "entry" && <BtEntryAutopsy baseUrl={baseUrl} jobId={jobId} contract={dataContract}/>}
      {running && <div className="tp-progress" role="progressbar" aria-valuenow={Math.round((analysis.progress || 0) * 100)}><i style={{ width: `${Math.round((analysis.progress || 0) * 100)}%` }}/><span>{analysis.processed || 0}/{analysis.total || "?"} · {Math.round((analysis.progress || 0) * 100)}%</span></div>}
      {error && <p className="tp-error" role="alert">{error}</p>}
      {totals && <>
        {activeView === "summary" && <div className="tp-summary"><div className="tp-summary-actions"><span className="tp-authority diagnostic">진단</span><button className="btn ghost sm" onClick={() => window.open(baseUrl + "/bt/trade-path/report?analysis_id=" + encodeURIComponent(analysisId), "_blank", "noopener")}>진단 보고서 열기</button></div>
          <div className="tp-auto-summary">{cohorts.slice(0, 4).map(row => <small key={row.key}>• {row.key} {row.count}건에서 {_tpMoney(row.actual_profit_krw)} 실현 · 경계 전 회복 관측 {row.recovered_count}건 — 관찰 결과이며 이 조건을 제거한 효과가 아닙니다.</small>)}</div><div className="tp-kpis"><article><small>분석 거래</small><b>{totals.analyzed_count}</b></article><article><small>제외</small><b>{totals.excluded_count}</b></article><article><small>경계 전 회복</small><b>{totals.recovered_count}</b></article><article><small>실제 순손익</small><b>{_tpMoney(totals.actual_profit_krw)}</b></article></div><div className="tp-cohorts">{cohorts.map(row => <button key={row.key} onClick={() => { const hit = trades.find(trade => trade.exit_reason === row.key); if (hit) openTrade(hit); }}><b>{row.key}</b><span>{row.count}건 · 회복 {row.recovered_count} · {_tpMoney(row.actual_profit_krw)}</span></button>)}</div><div className="tp-trade-list">{trades.slice(0, 30).map(row => <button key={row.trade_key} onClick={() => openTrade(row)}><span>{row.name}</span><code>{String(row.buy_time).slice(8)} → {String(row.sell_time).slice(8)}</code><b className={row.actual_profit_krw >= 0 ? "pos" : "neg"}>{_tpMoney(row.actual_profit_krw)}</b></button>)}</div></div>}
        {activeView === "path" && (detail ? <div><BtTradePathChart episode={detail}/><div className="tp-path-actions"><span className="tp-authority diagnostic">진단</span><span>가상 horizon은 실제 틱 지연과 검열 사유를 함께 보존합니다.</span><button className="btn primary sm" onClick={replay}>이 거래를 Replay에서 열기</button></div></div> : <div className="tp-empty">요약에서 거래를 선택하세요.</div>)}
        {activeView === "sell-trace" && <BtSellDslTrace baseUrl={baseUrl} analysisId={analysisId} episode={detail}/>}
        {activeView === "counterfactual" && <div><BtExitCounterfactual baseUrl={baseUrl} analysisId={analysisId} onResult={setCf}/>{cf && <div className="tp-cf-result"><b>가상 순손익 변화 {_tpMoney(cf.total_delta_profit_krw)}</b><span>평가 {cf.outcomes?.length || 0} · 제외 {cf.failures?.length || 0}</span>{(cf.transitions || []).map(row => <small key={`${row.actual_reason}-${row.candidate_reason}`}>{row.actual_reason} → {row.candidate_reason}: {row.count}</small>)}</div>}</div>}
        {activeView === "insight" && <BtRecoveryInsight baseUrl={baseUrl} analysisId={analysisId}/>}
        {activeView === "calibration" && <BtCalibration baseUrl={baseUrl} lane={lane}/>}
        {activeView === "proposals" && <div><button className="btn primary sm" onClick={generateProposals}>근거 기반 후보 생성</button><BtConditionProposals proposals={proposals}/></div>}
        {activeView === "console" && <div>
          {proposalRows.length > 0 && <label className="tp-cc-picker">실행할 후보
            <select value={selectedProposalId} onChange={event => setSelectedProposalId(event.target.value)}>
              <option value="">후보 선택</option>
              {proposalRows.map(row => <option key={row.proposal_id} value={row.proposal_id}>{row.family} · {row.title}</option>)}
            </select></label>}
          <BtCandidateConsole baseUrl={baseUrl} lane={lane} manifest={laneManifest} proposal={selectedProposal}/>
        </div>}
        {activeView === "official" && <BtExitTransition baseUrl={baseUrl} jobs={jobs} baselineJobId={jobId}/>}
        {activeView === "oos" && <BtOosGate baseUrl={baseUrl} jobs={jobs} baselineJobId={jobId} lane={lane}/>}</>}
      {activeView === "ledger" && <BtLedgerBrowser baseUrl={baseUrl} lane={lane}/>}
    </div>
  </section>;
}

Object.assign(window, { BtTradePathTab });
export { BtTradePathTab };
