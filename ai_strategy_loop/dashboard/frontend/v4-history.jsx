/* v4-history.jsx — V4 "History" 탭: run/gen 아카이브 · Compare · governed 연구 기록.
 *   legacy evolution/records 의 정본(ResearchRecordsPanel + ResearchIndexPage)을 직접 마운트.
 *   규칙 유지: run/gen 재열람·Compare·ResultDetail 은 History 가 단독 소유한다.
 *   B트랙 승격(2026-07-17): v4.1 조건식 History 트리 + G002 시각화 3종(A/B 쌍대비교·
 *   셀 히트맵·홀드아웃 퍼널)을 legacy records 탭과 동일 순서로 마운트한다.
 */
import { BtTradePathHistory } from "./bt-trade-path-history.jsx";
// dual-safe ESM import. KEEP each on ONE physical line.
import { ResearchRecordsPanel } from "./research-records-panel.jsx";
import { HistoryConditionTreePanel } from "./history-condition-tree.jsx";
import { ResearchIndexPage } from "./dashboard-pages.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { BtResultArea } from "./backtest-charts.jsx";
const { useState: useState_v4h, useEffect: useEffect_v4h } = React;
const HISTORY_RESULT_LAYOUT_KEY = "stom_v511_result_layout";
const HISTORY_RESULT_LAYOUTS = ["2", "3", "4"];
function _historyLayoutPreference() {
  try {
    const value = window.localStorage.getItem(HISTORY_RESULT_LAYOUT_KEY);
    return HISTORY_RESULT_LAYOUTS.includes(value) ? value : "3";
  } catch (error) {
    return "3";
  }
}
function _historyMetric(row, keys) {
  for (const key of keys) {
    if (typeof row[key] === "number" && Number.isFinite(row[key])) return row[key];
  }
  return null;
}
function _historyGenerationRows(selection) {
  if (!selection) return [];
  if (Array.isArray(selection.generation_rows)) return selection.generation_rows;
  if (Array.isArray(selection.generations)) return selection.generations;
  return _historyMetric(selection, ["graded_score", "score", "mdd", "max_drawdown"]) !== null ? [selection] : [];
}
function _historyValue(value, digits = 3) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";
}
function _HistoryIterationAnalysis({ selection, layout, onLayoutChange }) {
  const rows = _historyGenerationRows(selection);
  const points = rows.map((row, index) => ({
    gen: row.gen_no == null ? "—" : row.gen_no,
    score: _historyMetric(row, ["graded_score", "score"]),
    mdd: _historyMetric(row, ["mdd", "max_drawdown"]),
    reason: typeof row.failure_reason === "string" ? row.failure_reason
      : typeof row.rejection_reason === "string" ? row.rejection_reason
        : typeof row.error === "string" ? row.error : "",
    index,
  }));
  const scored = points.filter(point => point.score !== null);
  const scatter = points.filter(point => point.score !== null && point.mdd !== null);
  const failures = points.filter(point => point.reason);
  const regressions = points.filter((point, index) => index > 0 && point.score !== null && points[index - 1].score !== null && point.score < points[index - 1].score);
  const scoreMin = scored.length ? Math.min(...scored.map(point => point.score)) : null;
  const scoreMax = scored.length ? Math.max(...scored.map(point => point.score)) : null;
  const mddMin = scatter.length ? Math.min(...scatter.map(point => point.mdd)) : null;
  const mddMax = scatter.length ? Math.max(...scatter.map(point => point.mdd)) : null;
  const scale = (value, min, max, start, size) => min === null || max === null ? start : (max === min ? start + size / 2 : start + ((value - min) / (max - min)) * size);
  return (
    <section className={"v4-history-iteration v4-history-layout-" + layout} aria-labelledby="history-iteration-title">
      <div className="v4-history-iteration-head">
        <div>
          <div id="history-iteration-title" className="stom-section-label">세대 반복 분석 · 로드된 출처만</div>
          <p className="v4-history-feature-copy">선택 이벤트에 이미 포함된 generation 필드만 표시합니다. 누락 지표는 추정하거나 0으로 바꾸지 않습니다.</p>
        </div>
        <span className="bt-result-layout-controls" role="radiogroup" aria-label="History 결과 레이아웃">
          {HISTORY_RESULT_LAYOUTS.map(mode => (
            <button key={mode} type="button" className={"btn ghost sm" + (layout === mode ? " active" : "")}
                    role="radio" aria-checked={layout === mode} onClick={() => onLayoutChange(mode)}>
              {mode}
            </button>
          ))}
        </span>
      </div>
      {!rows.length ? <p className="v4-history-unavailable" role="status">반복 분석 사용 불가 — 선택한 세대에 로드된 generation 지표가 없습니다.</p> : (
        <React.Fragment>
          <div className="v4-history-iteration-charts">
            <figure className="v4-history-mini-chart">
              <figcaption>점수 추세 <span>{scored.length ? `${scored.length}개 출처 값` : "사용 불가"}</span></figcaption>
              {scored.length ? <svg viewBox="0 0 240 72" role="img" aria-label="로드된 세대 점수 추세">
                <polyline className="v4-history-score-line" fill="none" points={scored.map((point, index) => `${20 + (scored.length === 1 ? 100 : index * 200 / (scored.length - 1))},${60 - scale(point.score, scoreMin, scoreMax, 0, 48)}`).join(" ")} />
                {scored.map((point, index) => <circle key={`${point.gen}-${index}`} className="v4-history-score-point" cx={20 + (scored.length === 1 ? 100 : index * 200 / (scored.length - 1))} cy={60 - scale(point.score, scoreMin, scoreMax, 0, 48)} r="3"><title>gen {point.gen}: score {_historyValue(point.score)}</title></circle>)}
              </svg> : <p className="v4-history-unavailable">점수 사용 불가 —</p>}
            </figure>
            <figure className="v4-history-mini-chart">
              <figcaption>점수 대 MDD <span>{scatter.length ? `${scatter.length}개 출처 값` : "사용 불가"}</span></figcaption>
              {scatter.length ? <svg viewBox="0 0 240 72" role="img" aria-label="로드된 점수와 MDD 산점도">
                {scatter.map((point, index) => <circle key={`${point.gen}-${index}`} className="v4-history-scatter-point" cx={20 + scale(point.mdd, mddMin, mddMax, 0, 200)} cy={60 - scale(point.score, scoreMin, scoreMax, 0, 48)} r="3"><title>gen {point.gen}: score {_historyValue(point.score)}, MDD {_historyValue(point.mdd)}</title></circle>)}
              </svg> : <p className="v4-history-unavailable">MDD 또는 점수 사용 불가 —</p>}
            </figure>
            <aside className="v4-history-failure-summary" aria-label="회귀와 실패 사유 요약">
              <b>회귀 · 실패 사유</b>
              <span>점수 회귀: {scored.length > 1 ? regressions.length : "—"} · 사유 기록: {failures.length || "—"}</span>
              {failures.length ? <ul>{failures.slice(0, 3).map((point, index) => <li key={`${point.gen}-${index}`}>gen {point.gen}: {point.reason}</li>)}</ul> : <p>실패 사유 사용 불가 —</p>}
            </aside>
          </div>
          <div className="v4-history-iteration-table" tabIndex={0} aria-label="반복 분석 텍스트 표">
            <table><caption>반복 분석 텍스트 대안</caption><thead><tr><th scope="col">세대</th><th scope="col">점수</th><th scope="col">MDD</th><th scope="col">실패 사유</th></tr></thead>
              <tbody>{points.map((point, index) => <tr key={`${point.gen}-${index}`}><td>{point.gen}</td><td>{_historyValue(point.score)}</td><td>{_historyValue(point.mdd)}</td><td>{point.reason || "—"}</td></tr>)}</tbody></table>
          </div>
        </React.Fragment>
      )}
    </section>
  );
}

function _HistoryStrategyCode({ baseUrl, selection }) {
  const [state, setState] = useState_v4h({ status: "loading", data: null, error: "" });
  useEffect_v4h(() => {
    if (!baseUrl || !selection) return undefined;
    const controller = new AbortController();
    const key = `${selection.run_id}:${selection.gen_no}`;
    setState({ status: "loading", data: null, error: "" });
    fetch(
      baseUrl + "/strategy_code?run=" + encodeURIComponent(selection.run_id)
      + "&gen=" + encodeURIComponent(selection.gen_no),
      { signal: controller.signal }
    )
      .then(response => response.ok ? response.json() : Promise.reject(new Error(`HTTP ${response.status}`)))
      .then(data => {
        if (!controller.signal.aborted && key === `${selection.run_id}:${selection.gen_no}`) {
          setState({ status: "ready", data, error: "" });
        }
      })
      .catch(error => {
        if (!controller.signal.aborted && error.name !== "AbortError") {
          setState({ status: "error", data: null, error: String(error) });
        }
      });
    return () => controller.abort();
  }, [baseUrl, selection && selection.run_id, selection && selection.gen_no]);

  const data = state.data || {};
  const buyCode = data.buy_code || "";
  const sellCode = data.sell_code || "";
  const copy = value => {
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(value || "");
  };
  return (
    <section className="history-strategy-code" aria-labelledby="history-strategy-code-title">
      <div className="bt-section-heading">
        <div>
          <div id="history-strategy-code-title" className="stom-section-label">선택 세대 매수 · 매도 조건식</div>
          <p className="v4-history-feature-copy">출처: /strategy_code · 선택한 run/gen과 결속된 읽기 전용 원문입니다.</p>
        </div>
        <span className="badge">{data.code_status || state.status}</span>
      </div>
      {state.status === "error" ? (
        <div className="research-empty danger" role="alert">조건식 조회 실패 — {state.error}</div>
      ) : (
        <div className="rp-code-grid">
          {/* v5.13.1(A2 누락분) — 히스토리 결과 상세의 조건식도 문법 강조로 표시한다. */}
          {[["매수", data.buy_name, buyCode], ["매도", data.sell_name, sellCode]].map(([side, name, codeText]) => {
            const CodeBlock = window.CvCodeBlock;
            return (
              <div key={side}>
                <div className="rp-code-label">
                  <span>{side} · {name || "이름 미발행"}</span>
                  <button type="button" className="btn ghost sm" onClick={() => copy(codeText)} disabled={!codeText}>{side} 복사</button>
                </div>
                {state.status === "loading" ? (
                  <pre className="rp-code-block">불러오는 중…</pre>
                ) : codeText && typeof CodeBlock === "function" ? (
                  <div className="rp-code-block rp-code-highlight"><CodeBlock code={codeText} /></div>
                ) : (
                  <pre className="rp-code-block">{codeText || "코드 미발행"}</pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

/* v5.13.0(E4) — 결과 상세 직접 선택기. 종전에는 결과 상세로 가는 유일한 길이 Run Compare 의
 *   [분석 보기]뿐이라 "상세를 보려면 비교부터 해야 하는" 뒤집힌 동선이었다.
 *   /runs → run 선택 → /bt/evo_gens → 세대 선택으로 비교 없이 바로 상세를 연다. */
function _HistoryDirectPicker({ baseUrl, onSelectAnalysis }) {
  const [runs, setRuns] = useState_v4h([]);
  const [runId, setRunId] = useState_v4h("");
  const [gens, setGens] = useState_v4h([]);
  const [loading, setLoading] = useState_v4h(false);
  useEffect_v4h(() => {
    if (!baseUrl) return undefined;
    const controller = new AbortController();
    fetch(baseUrl + "/runs", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        const rows = Array.isArray(j && j.runs) ? j.runs : [];
        rows.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRuns(rows);
        if (rows.length && !runId) setRunId(rows[0].run_id);
      })
      .catch(() => setRuns([]));
    return () => controller.abort();
  }, [baseUrl]);
  useEffect_v4h(() => {
    if (!baseUrl || !runId) { setGens([]); return undefined; }
    const controller = new AbortController();
    setLoading(true);
    fetch(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(runId), { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => setGens(Array.isArray(j && j.items) ? j.items : []))
      .catch(() => setGens([]))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [baseUrl, runId]);
  const top = gens.filter(g => g.gen_no >= 0).slice().sort((a, b) => (b.score || 0) - (a.score || 0)).slice(0, 10);
  return (
    <div className="history-direct-picker">
      <p className="v4-history-feature-copy">연구(run)와 세대를 고르면 결과 비교를 거치지 않고 바로 상세를 엽니다.</p>
      <div className="hdp-row">
        <label className="mono hdp-label">연구(run)</label>
        <select className="mono hdp-select" value={runId} onChange={e => setRunId(e.target.value)}
                aria-label="상세를 볼 연구 run 선택">
          {!runs.length && <option value="">기록된 run 없음</option>}
          {runs.map(r => (
            <option key={r.run_id} value={r.run_id}>
              {r.run_id}{r.gate_passed_count > 0 ? " ✓" : ""}
            </option>
          ))}
        </select>
        {loading && <span className="mono hdp-loading">세대 불러오는 중…</span>}
      </div>
      {top.length > 0 && (
        <table className="mono hdp-table">
          <thead>
            <tr>
              <th className="left">세대</th>
              <th>score</th>
              <th>손익</th>
              <th>MDD</th>
              <th className="center">게이트</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {top.map(g => (
              <tr key={g.gen_no}>
                <td className="left">Gen {g.gen_no}</td>
                <td className="hdp-score">{typeof g.score === "number" ? g.score.toFixed(3) : "—"}</td>
                <td className={g.profit > 0 ? "num-pos" : g.profit < 0 ? "num-neg" : ""}>
                  {typeof g.profit === "number" ? g.profit.toLocaleString("ko-KR") + "원" : "—"}
                </td>
                <td className="hdp-mdd">{typeof g.mdd === "number" ? g.mdd.toFixed(2) + "%" : "—"}</td>
                <td className={"center " + (g.gate_passed ? "hdp-gate-pass" : "hdp-gate-none")}>
                  {g.gate_passed ? "✓" : "—"}
                </td>
                <td className="center">
                  <button className="btn primary sm" onClick={() => onSelectAnalysis({ run_id: runId, gen_no: g.gen_no })}>
                    상세 열기
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {runId && !loading && top.length === 0 && (
        <div className="research-empty">이 run 에는 표시할 세대가 없습니다.</div>
      )}
    </div>
  );
}

function V4History({ baseUrl, wsStatus, onNavigate }) {
  const historyLoading = wsStatus === "connecting" || wsStatus === "reconnecting";
  const [historyStage, setHistoryStage] = useState_v4h("research");
  // V6.3(S4): 선택 연구 마스터-디테일 — records 패널이 lift 한 선택을 컨텍스트 바가 소유.
  const [selResearch, setSelResearch] = useState_v4h(null); // { name, researchId, meta|null }
  const onSelectCampaign = (name, meta) => {
    const researchId = "campaign:" + name;
    // A new campaign is a new identity. Do not retain the prior campaign's
    // metadata while its authoritative detail request is in flight.
    setSelResearch({ name, researchId, meta: meta || null });
  };
  const [selectedAnalysis, setSelectedAnalysis] = useState_v4h(null);
  const [resultLayout, setResultLayout] = useState_v4h(_historyLayoutPreference);
  const onSelectAnalysis = (selection) => {
    if (!selection || !selection.run_id || selection.gen_no == null) {
      setSelectedAnalysis(null);
      return;
    }
    // Keep the archive identity as an indivisible run/gen pair; carry only fields already loaded with it.
    setSelectedAnalysis({ run_id: selection.run_id, gen_no: selection.gen_no, generation_rows: _historyGenerationRows(selection) });
    setHistoryStage("detail");
  };
  const setHistoryLayout = mode => {
    if (!HISTORY_RESULT_LAYOUTS.includes(mode)) return;
    setResultLayout(mode);
    try { window.localStorage.setItem(HISTORY_RESULT_LAYOUT_KEY, mode); } catch (error) {}
  };
  useEffect_v4h(() => {
    const consume = detail => {
      if (detail && detail.run_id && detail.gen_no != null) {
        onSelectAnalysis(detail);
      }
    };
    try {
      const raw = window.localStorage && window.localStorage.getItem("stom_history_evo_pending");
      if (raw) {
        window.localStorage.removeItem("stom_history_evo_pending");
        consume(JSON.parse(raw));
      }
    } catch (error) {}
    const onSelect = event => consume(event && event.detail);
    window.addEventListener("stom:history-evo-select", onSelect);
    return () => window.removeEventListener("stom:history-evo-select", onSelect);
  }, []);
  // L10: 재연결 문구 깜빡임 디바운스 — reconnecting 이 2초 지속될 때만 경고 문구 표시.
  const [stableWs, setStableWs] = useState_v4h(wsStatus);
  useEffect_v4h(() => {
    if (wsStatus !== "reconnecting") { setStableWs(wsStatus); return undefined; }
    const t = setTimeout(() => setStableWs("reconnecting"), 2000);
    return () => clearTimeout(t);
  }, [wsStatus]);
  const freshnessLabel = stableWs === "open"
    ? "서버 연결됨 · 선택한 아카이브 응답을 표시합니다."
    : stableWs === "demo"
      ? "예시 아카이브 · 운영 기록과 분리된 데이터입니다."
      : stableWs === "reconnecting"
        ? "연결 끊김 · 표시된 기록은 마지막 응답일 수 있습니다. 새 응답 전에는 최신으로 간주하지 않습니다."
        : "아카이브 연결 중 · 로딩이 끝날 때까지 이전 응답을 최신으로 간주하지 않습니다.";

  return (
    <div className="v4-history">
      <section className="panel" aria-labelledby="v4-history-journey-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-history-journey-title">History 작업 흐름</div>
            <div className="mono">과거 run/gen을 선택하고 근거를 비교하는 읽기 전용 여정</div>
          </div>
        </header>
        <div className="panel-bd">
          {/* v5.13.0(E1) — 단계 순서 재정렬: 상세가 본류, 비교는 필요할 때만.
              종전 "선택→비교→상세"는 상세를 보려고 비교를 강제하는 뒤집힌 동선이었다. */}
          <div className="v4-history-stage-nav" role="tablist" aria-label="History 연구 조회 단계">
            {[
              ["research", "1", "연구 선택", "캠페인과 연구 ID 고정"],
              ["detail", "2", "결과 상세", "run·세대를 바로 골라 조건식·차트 검토"],
              ["results", "3", "결과 비교 (선택)", "필요할 때만 run 끼리 비교"],
              ["evidence", "4", "근거 · 문서", "조건식 계보·색인으로 깊게 조회"],
            ].map(([stage, number, title, detail]) => (
              <button key={stage} type="button" role="tab" data-history-stage={stage}
                      aria-selected={historyStage === stage}
                      className={"v4-history-stage" + (historyStage === stage ? " active" : "")}
                      onClick={() => setHistoryStage(stage)}>
                <span className="v4-wf-num">{number}</span>
                <span className="v4-wf-txt"><b>{title}</b><span>{detail}</span></span>
              </button>
            ))}
          </div>
          <p className="mono" aria-live="polite">{freshnessLabel}</p>
        </div>
      </section>

      {selResearch && (
        <div className="v6-selres" role="note" aria-label="선택 연구 컨텍스트">
          <span className="v6-selres-id mono" title="stable research ID">{selResearch.researchId}</span>
          {selResearch.meta && (
            <span className="v6-selres-meta mono">
              수정 {(() => { const u = selResearch.meta.updated_at; if (u == null) return "—"; const n = Number(u); return Number.isFinite(n) && n > 1e9 ? new Date(n * 1000).toISOString().slice(0, 10) : String(u).slice(0, 10); })()} · 후보 {selResearch.meta.candidate_count ?? "—"}
              {selResearch.meta.best && (selResearch.meta.best.label || selResearch.meta.best.name) ? " · best " + (selResearch.meta.best.label || selResearch.meta.best.name) : ""}
            </span>
          )}
          <button className="btn ghost sm" title="stable ID 복사"
                  onClick={() => { try { navigator.clipboard.writeText(selResearch.researchId); } catch (e) {} }}>ID 복사</button>
          <button className="btn ghost sm" title="연구 기록 색인으로 이동"
                  onClick={() => { const el = document.getElementById("v4-history-index-title"); el && el.scrollIntoView({ behavior: "smooth", block: "start" }); }}>색인에서 관련 기록</button>
          <span className="v6-selres-note">호환 섹션만 이 연구 ID를 사용합니다. 다른 유형의 분석은 독립 선택 상태로 유지됩니다.</span>
        </div>
      )}
      {historyStage === "research" && (
      <section className="panel v4-history-stage-panel" aria-labelledby="v4-history-archive-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-archive-title">아카이브 선택 · 요약</h2>
        <p className="v4-history-feature-copy">
          <b>캠페인 = 하나의 연구 묶음</b>입니다. AI 가 조건식을 발굴한 한 번의 연구 단위(기간·시간대·가설이 같은 세대들의 모음)를
          캠페인이라고 부릅니다. 아래에서 캠페인을 고르면 그 연구의 후보·기록이 고정되고, 이후 상세·비교는 이 선택을 기준으로 동작합니다.
        </p>
        <div className="v4-history-archive-scroll" data-region="scroll" tabIndex={0} aria-label="과거 run과 세대 비교 데이터 영역">
          <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} onSelectCampaign={onSelectCampaign} />
        </div>
      </section>
      )}

      {/* Compare와 조건식 트리는 즉시 열고, 대용량 시각화 근거는 필요할 때만 마운트한다. */}
      {historyStage === "results" && (
      <section className="panel v4-history-stage-panel" aria-labelledby="v4-history-compare-title">
        <header className="panel-hd"><h2 id="v4-history-compare-title" className="stom-section-label">Run Compare · A/B 비교</h2></header>
        <div className="panel-bd" data-region="scroll" tabIndex={0}>
          <p className="v4-history-feature-copy">목적: run의 성과와 winner 세대를 같은 기준으로 비교합니다. 방법: 최대 6개 run을 선택하고 ‘분석 보기’를 누르세요. 필요성: <b>campaign 연구 ID는 호환되지 않으며</b> Run Compare는 loop_run만 사용합니다.</p>
          <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} onSelectAnalysis={onSelectAnalysis} />
        </div>
      </section>
      )}

      {historyStage === "detail" && (
        selectedAnalysis ? (
          <section className="v4-history-analysis v4-history-stage-panel" aria-label="선택한 run winner 분석">
            <div className="v4-history-analysis-head">
              <span className="mono">{selectedAnalysis.run_id} / gen {selectedAnalysis.gen_no}</span>
              <div className="v4-history-detail-actions">
                <button className="btn ghost sm" onClick={() => onNavigate("reports")}>연결 리포트 보기</button>
                <button className="btn ghost sm" onClick={() => setHistoryStage("results")}>다시 비교</button>
              </div>
            </div>
            <_HistoryStrategyCode baseUrl={baseUrl} selection={selectedAnalysis} />
            <_HistoryIterationAnalysis selection={selectedAnalysis} layout={resultLayout} onLayoutChange={setHistoryLayout} />
            <BtResultArea key={`${selectedAnalysis.run_id}:${selectedAnalysis.gen_no}`} baseUrl={baseUrl} isDemo={wsStatus === "demo"} jobId={null} evoSource={selectedAnalysis} />
          </section>
        ) : (
          <section className="panel v4-history-stage-panel" aria-label="결과 상세 직접 선택">
            <header className="panel-hd"><h2 className="stom-section-label">결과 상세 · 연구/세대 직접 선택</h2></header>
            <div className="panel-bd">
              <_HistoryDirectPicker baseUrl={baseUrl} onSelectAnalysis={onSelectAnalysis} />
              <p className="v4-history-feature-copy hdp-compare-hint">
                여러 run 을 나란히 비교하려면 <button className="btn ghost sm" onClick={() => setHistoryStage("results")}>결과 비교</button> 단계를 사용하세요.
              </p>
            </div>
          </section>
        )
      )}
      {historyStage === "evidence" && (
      <div className="v4-history-evidence-stack">
      <BtTradePathHistory baseUrl={baseUrl} active={historyStage === "evidence"} />
      <details className="evo-group" open>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-lineage-title">조건식 History 트리</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="조건식 계보 트리 영역">
          <p className="v4-history-feature-copy">목적: 조건식 계보와 평가 흔적을 탐색합니다. 방법: research ID를 선택해 단계와 조건을 펼치세요. 필요성: <b>loop_run과 campaign ID는 서로 호환되지 않는 경우가 있어</b> 서버가 허용한 기록만 표시합니다.</p>
          <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} />
        </div>
      </details>
      {/* v5.13.0(E5) — A/B 쌍대비교·셀 히트맵·홀드아웃 퍼널 묶음 제거(육안 검토: 불필요 잔재).
          해당 시각화 정본은 레거시 records 화면에만 남긴다. */}
      {/* v5.3.1: 엣지 섹션 제거 — 채점·부검 스테이지(Live)가 정위치. 중복 mount 해소. */}

      <details className="evo-group" open aria-labelledby="v4-history-index-title">
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-index-title">연구 기록 색인 · 상세 근거 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="연구 기록 표와 상세 데이터 영역" aria-busy={historyLoading}>
          <p className="v4-history-feature-copy">목적: 대량 연구 기록의 상세 근거를 찾습니다. 방법: 필요할 때만 펼쳐 검색하세요. 필요성: 색인은 무겁고, 호환되지 않는 research ID는 독립 조회로 남습니다.</p>
          <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} initialQuery={selResearch ? selResearch.researchId : ""} preferredResearchId={selResearch && selResearch.researchId} />
        </div>
      </details>
      </div>
      )}

    </div>
  );
}

Object.assign(window, { V4History });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4History };
