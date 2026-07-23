/* Backtest workbench analysis charts — 결과·분석 오케스트레이터 (split from backtest-charts.jsx).
   /bt/result 를 로드해 메트릭 카드 + 전체 차트/패널을 합성한다. backtest.jsx 의 BacktestTab 이 소비.
   각 차트/패널은 sibling 모듈(bt-equity-charts / bt-distribution-charts / bt-stat-panels / bt-gui-parity)
   에서 import 하고, 공용 헬퍼는 bt-chart-utils 에서 import 한다.

   무예외 fetch 헬퍼(_btFetchJson)는 bt-tab-utils.jsx 에 정의·export 된다. window 으로 재게시되지
     않으므로(전역 fallback 없음) 반드시 import 해야 한다 — bare 참조 시 esbuild 번들에서 free-global
     로 남아 load() 호출 시점에 `ReferenceError: _btFetchJson is not defined` 가 발생한다.
*/
import {
  useState_btc, useEffect_btc, useCallback_btc, useRef_btc,
  _btDateLabel, _btDownloadAnalysisCsv, _useCountUp, _BtArcGauge, _BtSparkline,
} from "./bt-chart-utils.jsx";
import { _btFetchJson } from "./bt-tab-utils.jsx";
import { btRequestIsCurrent, btMetricValue } from "./bt-request-guard.mjs";
import {
  BtEquityChart, BtMaeMfeScatter, BtUnderwaterChart, BtRollingChart, BtCumulativeTradesChart,
} from "./bt-equity-charts.jsx";
import {
  BtDistributionChart, BtHeatmap, BtMonteCarloChart, BtMonthlyCalendar,
} from "./bt-distribution-charts.jsx";
import {
  BtExitReasonPanel, BtContribTable, BtInsightsPanel,
  BtOrderflowPanel, BtStatTestPanel, BtCompareView,
} from "./bt-stat-panels.jsx";
import { BtGuiParitySection } from "./bt-gui-parity.jsx";
import { BtQuantPanel } from "./bt-quant.jsx";

// ===========================================================================
// 결과·분석 영역 — 메트릭 카드 + 4차트 + 기여 테이블 + 인사이트.
//   /bt/result 를 로드해 위 차트들을 합성한다. backtest.jsx 의 BacktestTab 이 소비.
// ===========================================================================
const _BT_METRIC_CARDS = [
  { key: "trade_count",      label: "거래수",     fmt: (v) => fmtInt(v) },
  { key: "win_rate",         label: "승률",       fmt: (v) => fmtPct(v) },
  { key: "total_profit_pct", label: "수익률합계", fmt: (v) => fmtPct(v), signed: true },
  { key: "total_profit_krw", label: "수익금",     fmt: (v) => fmtMoney(v), signed: true },
  { key: "mdd_pct",          label: "MDD",        fmt: (v) => fmtPct(v), risk: true },
  { key: "cagr",             label: "CAGR",       fmt: (v) => fmtPct(v), signed: true },
];
const _BT_RESULT_CAPABILITIES = {
  job: { label: "완료 잡", range: true, monteCarlo: true, compare: true,
    notes: { range: "완료 잡의 거래 시계열로 구간을 다시 계산합니다.", monteCarlo: "완료 잡의 거래 표본으로 계산합니다.", compare: "다른 완료 잡을 비교 대상으로 선택할 수 있습니다." } },
  evolution: { label: "진화 세대", range: false, monteCarlo: false, compare: false,
    notes: { range: "세대 요약에는 구간별 거래 시계열이 없습니다.", monteCarlo: "세대 요약에는 몬테카를로 입력 거래 표본이 없습니다.", compare: "A/B 비교는 완료 잡 결과만 지원합니다." } },
  demo: { label: "데모", range: false, monteCarlo: false, compare: false,
    notes: { range: "데모 상태는 결과 artifact를 발행하지 않습니다.", monteCarlo: "데모 상태는 결과 artifact를 발행하지 않습니다.", compare: "데모 상태는 완료 잡을 제공하지 않습니다." } },
  none: { label: "선택 없음", range: false, monteCarlo: false, compare: false,
    notes: { range: "결과를 선택한 뒤 사용할 수 있습니다.", monteCarlo: "결과를 선택한 뒤 사용할 수 있습니다.", compare: "결과를 선택한 뒤 사용할 수 있습니다." } },
};

function _BtResultCapabilities({ capabilities }) {
  return (
    <div className="bt-result-capabilities" role="status" aria-label={"결과 소스 기능: " + capabilities.label}>
      <b>결과 소스 · {capabilities.label}</b>
      {[["구간 분석", "range"], ["몬테카를로", "monteCarlo"], ["A/B 비교", "compare"]].map(([label, key]) => (
        <span key={key} className={capabilities[key] ? "ok" : "unsupported"}>
          {label}: {capabilities[key] ? "지원" : "미지원"}{!capabilities[key] ? " — " + capabilities.notes[key] : ""}
        </span>
      ))}
    </div>
  );
}

function BtResultArea({ baseUrl, isDemo, jobId, evoSource, onSetCompareA, compareView, onCloseCompare }) {
  const [result, setResult] = useState_btc(null);   // /bt/result
  const [loading, setLoading] = useState_btc(false);
  const [err, setErr] = useState_btc("");
  // 브러시 구간 분석 — {t_start,t_end} 또는 null(전체). 진화 세대(evoSource)는 미지원.
  const [range, setRange] = useState_btc(null);
  // 몬테카를로(지연 계산) — {data, loading}.
  const [mc, setMc] = useState_btc(null);
  const [mcLoading, setMcLoading] = useState_btc(false);
  // 전체화면 분석 모드(트랙 D) — position:fixed 오버레이. Esc 로 닫기.
  const [fullscreen, setFullscreen] = useState_btc(false);
  const resultRequestRef = useRef_btc({ seq: 0, controller: null });
  const mcRequestRef = useRef_btc({ seq: 0, controller: null });
  const sourceKeyRef = useRef_btc("");

  // Esc 키로 전체화면 닫기 + 배경 스크롤 잠금(전체화면 동안만).
  useEffect_btc(() => {
    if (!fullscreen) return undefined;
    const onKey = (e) => { if (e.key === "Escape") setFullscreen(false); };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [fullscreen]);

  // 결과 소스별 지원 기능은 UI와 요청 경로가 함께 따르는 명시 계약이다.
  const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);
  const sourceKind = isDemo ? "demo" : (jobId ? "job" : (isEvo ? "evolution" : "none"));
  const capabilities = _BT_RESULT_CAPABILITIES[sourceKind];
  const hasSource = sourceKind === "job" || sourceKind === "evolution";
  const sourceKey = jobId || (isEvo ? evoSource.run_id + "/" + evoSource.gen_no : "");

  const load = useCallback_btc(() => {
    const requestState = resultRequestRef.current;
    if (requestState.controller) requestState.controller.abort();
    if (isDemo || !baseUrl || !hasSource) {
      requestState.controller = null;
      setResult(null);
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    const seq = requestState.seq + 1;
    resultRequestRef.current = { seq, controller };
    const expectedKey = sourceKey;
    setLoading(true); setErr("");
    let url;
    if (jobId) {
      url = baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId);
      if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    } else {
      url = baseUrl + "/bt/result?run_id=" + encodeURIComponent(evoSource.run_id)
          + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
    }
    _btFetchJson(url, 8000, controller.signal)
      .then(j => {
        if (!btRequestIsCurrent(resultRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) return;
        setResult(j);
        if (!(j && j.available)) setErr("결과를 찾을 수 없습니다");
      })
      .catch(e => {
        if (!btRequestIsCurrent(resultRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) return;
        setResult(null); setErr(String(e));
      })
      .finally(() => {
        if (btRequestIsCurrent(resultRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) setLoading(false);
      });
  }, [baseUrl, isDemo, jobId, isEvo, sourceKey, range]);

  // 몬테카를로 재계산(현재 구간 반영). 잡 전용 — 진화 세대는 스킵. 무예외.
  const loadMc = useCallback_btc(() => {
    const requestState = mcRequestRef.current;
    if (requestState.controller) requestState.controller.abort();
    if (isDemo || !baseUrl || !jobId) {
      requestState.controller = null;
      setMc(null);
      setMcLoading(false);
      return;
    }
    const controller = new AbortController();
    const seq = requestState.seq + 1;
    mcRequestRef.current = { seq, controller };
    const expectedKey = sourceKey;
    setMcLoading(true);
    let url = baseUrl + "/bt/analysis/montecarlo?job_id=" + encodeURIComponent(jobId) + "&n=2000";
    if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    _btFetchJson(url, 12000, controller.signal)
      .then(j => {
        if (!btRequestIsCurrent(mcRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) return;
        setMc((j && j.montecarlo) || null);
      })
      .catch(() => {
        if (btRequestIsCurrent(mcRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) setMc(null);
      })
      .finally(() => {
        if (btRequestIsCurrent(mcRequestRef.current, seq, sourceKeyRef.current, expectedKey, controller.signal)) setMcLoading(false);
      });
  }, [baseUrl, isDemo, jobId, sourceKey, range]);

  useEffect_btc(() => {
    sourceKeyRef.current = sourceKey;
    setResult(null); setErr(""); setRange(null); setMc(null);
    if (resultRequestRef.current.controller) resultRequestRef.current.controller.abort();
    if (mcRequestRef.current.controller) mcRequestRef.current.controller.abort();
  }, [sourceKey]);
  useEffect_btc(() => { load(); }, [load]);
  useEffect_btc(() => () => {
    if (resultRequestRef.current.controller) resultRequestRef.current.controller.abort();
    if (mcRequestRef.current.controller) mcRequestRef.current.controller.abort();
  }, []);
  // 결과/구간이 바뀌면 몬테카를로 자동 재계산(성공/구간 잡일 때만; 세대는 스킵).
  useEffect_btc(() => {
    if (capabilities.monteCarlo && result && result.available && result.status !== "no_trades") { loadMc(); }
  }, [result, loadMc, capabilities.monteCarlo]);

  const onBrush = useCallback_btc((t_start, t_end) => {
    if (!capabilities.range) return;
    setRange({ t_start, t_end });
  }, [capabilities.range]);
  const onBrushClear = useCallback_btc(() => { setRange(null); }, []);

  if (!hasSource) {
    const message = isDemo
      ? "데모 모드에는 결과 artifact가 없습니다. 실제로 실행된 완료 잡 또는 진화 세대를 선택하면 분석을 표시합니다."
      : "완료된 백테스트 잡 또는 진화 세대를 선택하면 결과·분석이 여기에 표시됩니다.";
    return (
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div>
        </div>
        <div className="panel-bd">
          <div className="research-empty">{message}</div>
          <_BtResultCapabilities capabilities={capabilities} />
        </div>
      </div>
    );
  }

  if (loading && !result) {
    return (
      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div></div>
        <div className="panel-bd"><div className="research-empty">결과 로딩 중…</div></div>
      </div>
    );
  }

  if (err || !result || !result.available) {
    return (
      <div className="panel">
        <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div></div>
        <div className="panel-bd">
          <div className="research-empty" style={{ color: "var(--red)" }}>
            {err || "결과 없음"}
            <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={load}>재시도</button></div>
          </div>
        </div>
      </div>
    );
  }

  const sourceContext = { isEvo, evoSource, jobId, baseUrl, capabilities };
  return (
    <ResultDetailBody
      result={result}
      sourceContext={sourceContext}
      range={range}
      loading={loading}
      mc={mc}
      mcLoading={mcLoading}
      compareView={compareView}
      onSetCompareA={onSetCompareA}
      onCloseCompare={onCloseCompare}
      onBrush={onBrush}
      onBrushClear={onBrushClear}
      onRunMc={loadMc}
      onReload={load}
      onFullscreen={() => setFullscreen(true)}
      onCloseFullscreen={() => setFullscreen(false)}
      fullscreen={fullscreen}
    />
  );
}


function ResultDetailBody({
  result, sourceContext, range, loading, mc, mcLoading, compareView,
  onSetCompareA, onCloseCompare, onBrush, onBrushClear, onRunMc, onReload,
  onFullscreen, onCloseFullscreen, fullscreen,
}) {
  const { isEvo, evoSource, jobId, baseUrl, capabilities } = sourceContext || {};
  const [diagnosticsOpen, setDiagnosticsOpen] = useState_btc(false);
// no_trades → 안내 카드(에러 아님).
if (result.status === "no_trades") {
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>결과 · 분석</div>
        <span className="badge warn">거래 0건</span>
      </div>
      <div className="panel-bd">
        <div className="empty" style={{ padding: "28px 24px" }}>
          <h2 style={{ color: "var(--amber)" }}>거래 0건</h2>
          <p>{result.message || "전략이 해당 기간에 매수 신호를 내지 않았습니다. 에러가 아닙니다 — 조건식/기간을 조정해 보세요."}</p>
        </div>
          <_BtResultCapabilities capabilities={capabilities} />
      </div>
    </div>
  );
}

const analysis = result.analysis || {};
// 메트릭 우선순위: CLI metrics(브리핑 필드) → 없으면 analysis.summary 매핑.
const metrics = result.metrics || {};
const summary = analysis.summary || {};
const metricVal = (key) => btMetricValue(metrics, summary, key);
const metricsOnly = result.has_csv === false || result.artifact_state === "metrics_only_csv_missing";
if (metricsOnly) {
  return (
    <div className="panel bt-result-metrics-only" role="status">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--amber)" }}></span>메트릭 요약 · 차트 증거 없음</div>
        <span className="badge warn">CSV 없음</span>
      </div>
      <div className="panel-bd">
        <p className="bt-section-purpose">{result.message || "결과 CSV가 없어 저장된 세대 메트릭만 표시합니다. 차트와 상세 분석은 제공하지 않습니다."}</p>
        <div className="bt-summary-row" style={{ gridTemplateColumns: "repeat(6, minmax(0, 1fr))" }}>
          {_BT_METRIC_CARDS.map(meta => {
            const value = metricVal(meta.key);
            const num = typeof value === "number" && Number.isFinite(value) ? value : null;
            return <_BtMetricCard key={meta.key} meta={meta} num={num} dailyPnl={[]} />;
          })}
        </div>
        <div className="mono" style={{ marginTop: 10, color: "var(--ink-3)" }}>
          artifact={result.artifact_state || "metrics_only"} · evidence={result.evidence_id || "없음"}
        </div>
        <_BtResultCapabilities capabilities={capabilities} />
      </div>
    </div>
  );
}

const distribution = analysis.distribution || {};
const insights = analysis.insights || [];
const topC = distribution.top_contributors || [];
const botC = distribution.bottom_contributors || [];
const dailyPnl = ((analysis.equity || {}).daily || []).map(d => d.pnl || 0);
const orderflow = analysis.orderflow || {};
const stats = analysis.stats || [];

return (
  <div className="bt-result-flow bt-result-grid-12">
    <nav className="bt-result-nav" aria-label="결과 분석 섹션">
      <a href="#bt-result-summary-title">요약</a>
      <a href="#bt-result-primary-title">핵심 결과</a>
      <a href="#bt-result-risk-title">MDD · 위험</a>
      <a href="#bt-result-diagnostics-title" onClick={() => setDiagnosticsOpen(true)}>진단</a>
      <button type="button" className="btn ghost sm" onClick={() => setDiagnosticsOpen(true)}
              aria-expanded={diagnosticsOpen} aria-controls="bt-result-diagnostics">
        모든 진단 펼치기
      </button>
    </nav>
    <_BtResultCapabilities capabilities={capabilities} />
    <section className="bt-result-section bt-result-summary" aria-labelledby="bt-result-summary-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-result-summary-title" className="stom-section-label">결과 요약</div>
          <p className="bt-section-purpose">조건식, 기간, 표본 내 advisory와 핵심 지표를 한 곳에서 확인합니다.</p>
        </div>
      </div>
    {/* V5.3(gap-only): 결과가 어떤 조건식·기간을 테스트했는지 상단 명시(job spec 소비, 재계산 없음) */}
    {(() => {
      const spec = result.spec || {};
      const buy = spec.buy || result.buy || "—";
      const sell = spec.sell || result.sell || "—";
      const period = (spec.start && spec.end) ? `${spec.start}~${spec.end}` : (result.period || "—");
      return (
        <div className="bt-condition-band" aria-label="테스트 조건식과 기간">
          <div><span className="k">매수 조건식</span><b className="mono">{buy}</b></div>
          <div><span className="k">매도 조건식</span><b className="mono">{sell}</b></div>
          <div><span className="k">기간·출처</span><b className="mono">{period}{jobId ? " · " + jobId : ""}</b></div>
          {/* v5.3.5(U6): 결과→리플레이 직행 동선(딥링크). 파라미터 prefill 은 운영검사 후. */}
          <a className="btn ghost sm" href="/ui/chart-replay" title="이 조건식 신호 맥락을 캔들 리플레이에서 확인">▶ 리플레이에서 확인</a>
        </div>
      );
    })()}
    {/* 구간 분석 상태 배너 */}
    {range && (
      <div className="bt-range-bar">
        <span className="mono" style={{ fontSize: 11, color: "var(--teal)" }}>
          ◧ 구간 분석 적용 중 — {_btDateLabel(Math.floor(range.t_start / 1000000))}
          ~{_btDateLabel(Math.floor(range.t_end / 1000000))}
          {result.ranged && analysis.trade_count != null ? ` · ${analysis.trade_count}거래` : ""}
        </span>
        <button className="btn ghost sm" onClick={onBrushClear} style={{ marginLeft: "auto" }}>전체로 복귀</button>
      </div>
    )}

    {/* 메트릭 카드 행 — 카운트업 + 게이지 */}
    <div className="panel bt-equal-card">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: isEvo ? "var(--violet)" : "var(--teal)" }}></span>
          {isEvo ? "핵심 메트릭 · 진화 세대" : "핵심 메트릭"}
          {isEvo && (
            <span className="mono tag-slim" style={{ fontSize: 9.5, color: "var(--violet)", marginLeft: 6 }}
                  title="진화 run 세대 분석 — loop_runs.db 읽기 전용">
              {evoSource.run_id}/g{evoSource.gen_no}
            </span>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {onSetCompareA && jobId && capabilities.compare && (
            <button className="btn ghost sm" onClick={() => onSetCompareA(jobId)}
                    title="이 잡을 A/B 비교의 기준(A)으로 고정">⊕ 비교 기준(A)</button>
          )}
          {isEvo && (
            <button className="btn ghost sm"
                    onClick={() => {
                      const u = baseUrl + "/bt/report?run_id=" + encodeURIComponent(evoSource.run_id)
                              + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
                      try { window.open(u, "_blank", "noopener"); } catch (e) {}
                    }}
                    title="이 세대의 자급자족 HTML 리포트를 새 탭으로 열기">📄 리포트</button>
          )}
          {((analysis.equity || {}).daily || []).length > 0 && (
            <button className="btn ghost sm" onClick={() => _btDownloadAnalysisCsv(analysis)}
                    title="일별 수익곡선(날짜·일별손익·누적수익)을 CSV 로 내려받기 — 표계산 도구에서 추가 분석">⬇ CSV</button>
          )}
          <button className="btn ghost sm" onClick={() => onFullscreen()}
                  title="전체 화면에서 더 많은 분석 그래프를 한눈에 보기 (Esc 로 닫기)">⛶ 전체화면 분석</button>
          <button className="btn ghost sm" onClick={onReload} disabled={loading}>{loading ? "로딩…" : "↻"}</button>
        </div>
      </div>
      <div className="bt-summary-row" style={{ gridTemplateColumns: "repeat(6, 1fr)" }}>
        {_BT_METRIC_CARDS.map(m => {
          const v = metricVal(m.key);
          const num = typeof v === "number" ? v : null;
          return <_BtMetricCard key={m.key} meta={m} num={num} dailyPnl={dailyPnl} />;
        })}
      </div>
    </div>
    </section>

    <section className="bt-result-section bt-result-primary" aria-labelledby="bt-result-primary-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-result-primary-title" className="stom-section-label">핵심 결과</div>
          <p className="bt-section-purpose">누적 수익 경로와 손익 분포를 먼저 검토합니다.{capabilities.range ? " 드래그하면 구간 분석을 적용합니다." : ""}</p>
        </div>
      </div>
      {compareView && <BtCompareView cmp={compareView} onClose={onCloseCompare} />}
      <div className="bt-primary-chart-grid bt-equal-card-grid">
        <BtEquityChart equity={analysis.equity} onBrush={capabilities.range ? onBrush : undefined}
                       brushActive={capabilities.range && !!range} onBrushClear={onBrushClear} />
        <BtDistributionChart distribution={distribution} />
      </div>
    </section>

    <section className="bt-result-section bt-result-evidence" aria-labelledby="bt-result-risk-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-result-risk-title" className="stom-section-label">MDD · 위험 증거</div>
          <p className="bt-section-purpose">관측된 최대 낙폭 경로와, 지원되는 경우 거래 표본의 몬테카를로 결과를 확인합니다.</p>
        </div>
      </div>
      <div className="bt-primary-chart-grid bt-equal-card-grid">
        <BtUnderwaterChart underwater={analysis.underwater} />
        {capabilities.monteCarlo ? (
          <BtMonteCarloChart mc={mc} loading={mcLoading} onRun={onRunMc} />
        ) : (
          <div className="research-empty" role="status">몬테카를로 미지원 — {capabilities.notes.monteCarlo}</div>
        )}
      </div>
    </section>

    <section id="bt-result-diagnostics" className="bt-result-section bt-result-diagnostics" aria-labelledby="bt-result-diagnostics-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-result-diagnostics-title" className="stom-section-label">진단</div>
          <p className="bt-section-purpose">손실 구간, 거래 품질, 실행 흐름과 cadence를 교차 확인합니다.</p>
        </div>
        <button type="button" className="btn ghost sm" onClick={() => setDiagnosticsOpen(open => !open)}
                aria-expanded={diagnosticsOpen} aria-controls="bt-result-diagnostics-body">
          {diagnosticsOpen ? "진단 접기" : "진단 펼치기"}
        </button>
      </div>
      {diagnosticsOpen && (
        <div id="bt-result-diagnostics-body" className="bt-diagnostic-grid bt-equal-card-grid">
          <BtHeatmap heatmap={analysis.heatmap} />
          <BtMaeMfeScatter points={analysis.mae_mfe} />
          <BtQuantPanel analysis={analysis} />
          <BtExitReasonPanel rows={analysis.exit_reasons} />
          <BtOrderflowPanel orderflow={orderflow} />
          <BtStatTestPanel stats={stats} />
          <BtRollingChart rolling={analysis.rolling} />
          <BtMonthlyCalendar monthly={analysis.monthly} />
          <BtGuiParitySection guiParity={analysis.gui_parity} columns={2} />
          <div className="bt-cadence-diagnostic">
            <BtCumulativeTradesChart data={analysis.cumulative_trades} />
          </div>
        </div>
      )}
    </section>

    {(topC.length > 0 || botC.length > 0) && (
      <section className="bt-result-section bt-result-evidence bt-contributor-evidence" aria-label="종목 기여 증거">
        <div className="panel bt-equal-card">
          <div className="panel-hd">
            <div className="panel-hd-title"><span className="dot" style={{ background: "var(--blue)" }}></span>종목 기여</div>
          </div>
          <div className="panel-bd">
            <div className="row-2">
              <BtContribTable title="상위 기여" rows={topC} />
              <BtContribTable title="하위 기여" rows={botC} />
            </div>
          </div>
        </div>
      </section>
    )}

    <section className="bt-result-section bt-result-evidence" aria-label="분석 인사이트">
      <BtInsightsPanel insights={insights} />
    </section>

    {/* 전체화면 분석 모드 오버레이(트랙 D) — position:fixed 풀스크린, 2~3컬럼 그리드 */}
    {fullscreen && (
      <_BtFullscreenAnalysis
        analysis={analysis} distribution={distribution} orderflow={orderflow}
        stats={stats} insights={insights} mc={mc} mcLoading={mcLoading} onRunMc={onRunMc}
        range={range} onBrush={onBrush} onBrushClear={onBrushClear}
        onClose={onCloseFullscreen}
      />
    )}
  </div>
);
}


// 전체화면 분석 오버레이 — 차트를 2~3컬럼 그리드로 크게 배치(인사이트 우선 노출).
//   인라인 스타일 풀스크린(position:fixed). 닫기: ✕ 버튼 또는 Esc(상위에서 처리).
function _BtFullscreenAnalysis({
  analysis, distribution, orderflow, stats, insights,
  mc, mcLoading, onRunMc, range, onBrush, onBrushClear, onClose,
}) {
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 4000,
      background: "var(--bg-1, #0d1117)", overflowY: "auto",
      padding: "16px 22px 40px",
    }}>
      {/* 상단 고정 바 */}
      <div style={{
        position: "sticky", top: 0, zIndex: 2,
        display: "flex", alignItems: "center", gap: 12,
        padding: "10px 4px 12px", marginBottom: 10,
        background: "var(--bg-1, #0d1117)", borderBottom: "1px solid var(--line-2)",
      }}>
        <span className="dot" style={{ background: "var(--teal)" }}></span>
        <strong style={{ fontSize: 15, color: "var(--ink-0)" }}>전체화면 분석</strong>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          더 많은 그래프로 인사이트 — 2~3컬럼 확대 배치
        </span>
        {range && (
          <span className="mono" style={{ fontSize: 10.5, color: "var(--teal)" }}>
            ◧ 구간 분석 적용 중
          </span>
        )}
        <div style={{ marginLeft: "auto", display: "flex", gap: 8, alignItems: "center" }}>
          {range && <button className="btn ghost sm" onClick={onBrushClear}>전체로 복귀</button>}
          <button className="btn sm" onClick={onClose}
                  style={{ borderColor: "var(--teal-dim)", color: "var(--teal)" }}>✕ 닫기 (Esc)</button>
        </div>
      </div>

      {/* 인사이트 우선 — 전체 폭 */}
      <div style={{ marginBottom: 14 }}>
        <BtInsightsPanel insights={insights} />
      </div>

      {/* 추가 분석 그래프 우선 배치(트랙 D) — 2컬럼 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(440px, 1fr))", gap: 14, marginBottom: 14 }}>
        <BtRollingChart rolling={analysis.rolling} />
        <BtCumulativeTradesChart data={analysis.cumulative_trades} />
        <BtMonthlyCalendar monthly={analysis.monthly} />
        <BtEquityChart equity={analysis.equity} onBrush={onBrush}
                       brushActive={!!range} onBrushClear={onBrushClear} />
      </div>

      {/* B3 — GUI 패리티 차트 6종(전체화면에서 2컬럼 확대 배치) */}
      <div style={{ marginBottom: 14 }}>
        <BtGuiParitySection guiParity={analysis.gui_parity} columns={2} />
      </div>

      {/* 나머지 분석 — 3컬럼(넓은 화면) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(380px, 1fr))", gap: 14 }}>
        <BtDistributionChart distribution={distribution} />
        <BtUnderwaterChart underwater={analysis.underwater} />
        <BtHeatmap heatmap={analysis.heatmap} />
        <BtMaeMfeScatter points={analysis.mae_mfe} />
        <BtQuantPanel analysis={analysis} />
        <BtMonteCarloChart mc={mc} loading={mcLoading} onRun={onRunMc} />
        <BtExitReasonPanel rows={analysis.exit_reasons} />
        <BtOrderflowPanel orderflow={orderflow} />
        <BtStatTestPanel stats={stats} />
      </div>
    </div>
  );
}

// 메트릭 카드 1개 — 카운트업 숫자 + (승률/MDD 게이지 · 수익금 스파크라인).
function _BtMetricCard({ meta, num, dailyPnl }) {
  const animated = _useCountUp(num != null ? num : 0, 600);
  const shown = num != null ? animated : null;
  let color;
  if (meta.risk) color = "var(--red)";
  else if (meta.signed && num != null) color = num > 0 ? "var(--teal)" : num < 0 ? "var(--red)" : undefined;

  // 승률·MDD 는 반원 게이지(0~100%).
  if ((meta.key === "win_rate" || meta.key === "mdd_pct") && num != null) {
    const gaugeColor = meta.key === "mdd_pct" ? "var(--red)" : "var(--teal)";
    return (
      <div className="bt-metric-card">
        <span className="summary-lbl">{meta.label}</span>
        <_BtArcGauge value={shown} max={100} color={gaugeColor}
                     label={meta.fmt(shown != null ? shown : 0)} />
      </div>
    );
  }
  // 수익금 카드는 일별손익 스파크라인 동반.
  if (meta.key === "total_profit_krw") {
    return (
      <div className="bt-metric-card">
        <span className="summary-lbl">{meta.label}</span>
        <span className="summary-val" style={{ color }}>{shown != null ? meta.fmt(shown) : "—"}</span>
        <_BtSparkline values={dailyPnl} />
      </div>
    );
  }
  return (
    <div className="bt-metric-card">
      <span className="summary-lbl">{meta.label}</span>
      <span className="summary-val" style={{ color }}>{shown != null ? meta.fmt(shown) : "—"}</span>
    </div>
  );
}

export { BtResultArea, ResultDetailBody };
