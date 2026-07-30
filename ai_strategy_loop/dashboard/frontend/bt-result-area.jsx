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
import { BtLeafExplorer } from "./bt-leaf-explorer.jsx";

// ===========================================================================
// 결과·분석 영역 — 메트릭 카드 + 4차트 + 기여 테이블 + 인사이트.
//   /bt/result 를 로드해 위 차트들을 합성한다. backtest.jsx 의 BacktestTab 이 소비.
// ===========================================================================
/* v5.13.2 — 보유시간 표기 헬퍼. 엔진 CSV 의 보유시간 컬럼은 tick=초 / min=분 이라
   서버가 초로 정규화해 내려준다(summary.avg_hold_sec / median_hold_sec).
   화면은 크기에 맞춰 초/분/시간으로 읽어준다("1726분" 같은 허수 방지). */
export function btFmtHold(sec) {
  const v = Number(sec);
  if (!Number.isFinite(v) || v <= 0) return "—";
  if (v < 60) return `${Math.round(v)}초`;
  if (v < 3600) return `${(v / 60).toFixed(1)}분`;
  return `${(v / 3600).toFixed(1)}시간`;
}

// v5.13.2 — 카드 구성 개편(사용자 지적: "핵심 메트릭 정보 부족 / 65.36%가 무슨 기준인지 모름").
//   ① 자본 대비 수익률을 1급 지표로 올리고 ② 거래수익률 합은 참고치로 이름을 바꾸고
//   ③ 늘 비어 있던 CAGR 을 context.annual_return_pct 로 실제로 채우고
//   ④ 보유시간(중앙값)을 추가해 tick/min 감각을 준다.
const _BT_METRIC_CARDS = [
  { key: "trade_count",      label: "거래수",     fmt: (v) => fmtInt(v) },
  { key: "win_rate",         label: "승률",       fmt: (v) => fmtPct(v) },
  { key: "return_on_capital_pct", label: "자본대비 수익률", fmt: (v) => fmtPct(v), signed: true,
    hint: "운용자본 대비 실제 수익률(연구 채점기 기준). 아래 '거래수익률 합'과 다른 값입니다." },
  { key: "total_profit_krw", label: "수익금",     fmt: (v) => fmtMoney(v), signed: true },
  // v5.13.2 — MDD 두 정의 분리. 같은 세대가 2.16%(자본대비)와 47.53%(수익 반납률)로
  //   동시에 표시되던 혼선을 이름으로 끝낸다. 자본대비가 없으면 반납률만 보인다.
  { key: "mdd_on_capital_pct", label: "MDD (자본대비)", fmt: (v) => fmtPct(v), risk: true,
    hint: "운용자본 대비 최대 낙폭(연구 채점기·명예의 전당과 같은 정의)." },
  { key: "mdd_pct",          label: "수익 반납률", fmt: (v) => fmtPct(v), risk: true,
    hint: "누적 실현손익 고점 대비 되돌린 비율. 자본 대비 낙폭과 다른 질문입니다." },
  { key: "cagr",             label: "연평균(CAGR)", fmt: (v) => fmtPct(v), signed: true,
    hint: "자본대비 수익률을 기간 길이로 연환산한 값. 기간이 20일 미만이면 계산하지 않습니다." },
  { key: "median_hold_sec",  label: "보유시간(중앙)", fmt: (v) => btFmtHold(v),
    hint: "청산까지 걸린 시간의 중앙값. tick 백테는 초 단위로 기록됩니다." },
  { key: "sum_trade_return_pct", label: "거래수익률 합(참고)", fmt: (v) => fmtPct(v), signed: true,
    hint: "거래별 수익률을 그냥 더한 값입니다. 같은 자본이 여러 번 회전하므로 자본 대비 수익률이 아닙니다 — 비교용 참고치로만 보세요." },
];
const _BT_RESULT_CAPABILITIES = {
  job: { label: "완료 잡", range: true, monteCarlo: true, compare: true,
    notes: { range: "완료 잡의 거래 시계열로 구간을 다시 계산합니다.", monteCarlo: "완료 잡의 거래 표본으로 계산합니다.", compare: "다른 완료 잡을 비교 대상으로 선택할 수 있습니다." } },
  // 세대 결과도 잡과 같은 거래 CSV 를 남긴다 → 구간 재계산·몬테카를로 표본이 실제로 존재한다.
  evolution: { label: "진화 세대", range: true, monteCarlo: true, compare: true,
    notes: { range: "세대 결과 CSV 의 거래 시계열로 구간을 다시 계산합니다.", monteCarlo: "세대 결과 CSV 의 거래 표본으로 계산합니다.", compare: "결과 라이브러리에서 A·B 를 골라 세대끼리 비교합니다." } },
  // 결과 CSV 가 없는 세대(메트릭 행만 남은 축약 결과) — 표본이 없으므로 정직하게 미지원.
  evolution_summary: { label: "진화 세대 · 메트릭 요약", range: false, monteCarlo: false, compare: false,
    notes: { range: "이 세대에는 결과 CSV 가 없어 구간을 다시 계산할 수 없습니다.", monteCarlo: "이 세대에는 결과 CSV 가 없어 몬테카를로 표본을 만들 수 없습니다.", compare: "A/B 비교는 완료 잡 결과만 지원합니다." } },
  demo: { label: "데모", range: false, monteCarlo: false, compare: false,
    notes: { range: "데모 상태는 결과 artifact를 발행하지 않습니다.", monteCarlo: "데모 상태는 결과 artifact를 발행하지 않습니다.", compare: "데모 상태는 완료 잡을 제공하지 않습니다." } },
  none: { label: "선택 없음", range: false, monteCarlo: false, compare: false,
    notes: { range: "결과를 선택한 뒤 사용할 수 있습니다.", monteCarlo: "결과를 선택한 뒤 사용할 수 있습니다.", compare: "결과를 선택한 뒤 사용할 수 있습니다." } },
};
const _BT_RESULT_LAYOUT_KEY = "stom_v511_result_layout";
const _BT_RESULT_LAYOUTS = ["2", "3", "4"];
function _btStoredPreference(key, fallback) {
  try {
    const value = window.localStorage.getItem(key);
    return value === null ? fallback : value;
  } catch (e) {
    return fallback;
  }
}
function _btResultColumns(layout, width) {
  const available = Number(width) || 0;
  if (available < 864) return 1;
  const maxColumns = Math.max(1, Math.min(4, Math.floor((available + 12) / 360)));
  return Math.min(Number(layout), maxColumns);
}

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
  // 세대 결과의 기능 지원은 '세대라서'가 아니라 '결과 CSV 가 실제로 있느냐'로 결정한다.
  //   응답 도착 전에는 축약(요약) 계약을 가정해 없는 표본을 먼저 요청하지 않는다.
  const evoHasSeries = isEvo && !!(result && result.has_csv === true);
  const sourceKind = isDemo
    ? "demo"
    : (jobId ? "job" : (isEvo ? (evoHasSeries ? "evolution" : "evolution_summary") : "none"));
  const capabilities = _BT_RESULT_CAPABILITIES[sourceKind];
  const hasSource = sourceKind === "job" || sourceKind === "evolution" || sourceKind === "evolution_summary";
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
      if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
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

  // 몬테카를로 재계산(현재 구간 반영). 완료 잡과 결과 CSV 가 있는 진화 세대 모두 지원. 무예외.
  //   v5.13.2 — method 인자 추가: "shuffle"(순서 위험) / "bootstrap"(표본 위험).
  const loadMc = useCallback_btc((method) => {
    const requestState = mcRequestRef.current;
    if (requestState.controller) requestState.controller.abort();
    if (isDemo || !baseUrl || (!jobId && !isEvo)) {
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
    let url = baseUrl + "/bt/analysis/montecarlo?n=2000&"
            + (jobId
                ? "job_id=" + encodeURIComponent(jobId)
                : "run_id=" + encodeURIComponent(evoSource.run_id)
                  + "&gen_no=" + encodeURIComponent(evoSource.gen_no));
    if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    url += "&method=" + (method === "bootstrap" ? "bootstrap" : "shuffle");
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
  }, [baseUrl, isDemo, jobId, isEvo, sourceKey, range]);

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
  const [layout, setLayout] = useState_btc(() => {
    const stored = _btStoredPreference(_BT_RESULT_LAYOUT_KEY, "3");
    return _BT_RESULT_LAYOUTS.includes(stored) ? stored : "3";
  });
  const layoutRef = useRef_btc(null);
  const [layoutWidth, setLayoutWidth] = useState_btc(() => typeof window === "undefined" ? 0 : window.innerWidth);
  const columns = _btResultColumns(layout, layoutWidth);
  useEffect_btc(() => {
    const node = layoutRef.current;
    if (!node) return undefined;
    const update = () => setLayoutWidth(node.clientWidth || window.innerWidth || 0);
    update();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", update);
      return () => window.removeEventListener("resize", update);
    }
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);
  useEffect_btc(() => {
    try { window.localStorage.setItem(_BT_RESULT_LAYOUT_KEY, layout); } catch (e) {}
  }, [layout]);
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
// v5.13.2 — 실행 맥락(/bt/result 의 context): 언제·어떤 연구·몇 세대·어느 기간·tick/min.
//   자본대비 수익률·연평균은 여기에만 있으므로 summary 에 합쳐 카드가 집어 쓰게 한다.
const runCtx = result.context || {};
const summaryPlus = {
  ...summary,
  return_on_capital_pct: runCtx.return_on_capital_pct,
  cagr: runCtx.annual_return_pct,
  mdd_on_capital_pct: runCtx.mdd_on_capital_pct,
};
const metricVal = (key) => btMetricValue(metrics, summaryPlus, key);
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
        <div className="bt-summary-row" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
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

// v5.13.0 — 돈 축 차트 공용 컨텍스트(C8): 종목당 배팅·연평균 수익률을 차트 위에 병기한다.
//   배팅은 고정배팅 모델(수익금 = 배팅 × 수익률합 ÷ 100)에서 역산한 파생값으로 정직하게 표기.
const _mxPct = metricVal("total_profit_pct");
const _mxKrw = metricVal("total_profit_krw");
const _mxCagr = metricVal("cagr");
const moneyCtx = {
  betting: (typeof _mxPct === "number" && Math.abs(_mxPct) > 0.01 && typeof _mxKrw === "number" && Number.isFinite(_mxKrw))
    ? Math.round((_mxKrw / _mxPct) * 100) : null,
  bettingDerived: true,
  cagr: typeof _mxCagr === "number" && Number.isFinite(_mxCagr) ? _mxCagr : null,
};

const distribution = analysis.distribution || {};
const insights = analysis.insights || [];
const topC = distribution.top_contributors || [];
const botC = distribution.bottom_contributors || [];
const dailyPnl = ((analysis.equity || {}).daily || []).map(d => d.pnl || 0);
const orderflow = analysis.orderflow || {};
const stats = analysis.stats || [];

return (
  <div ref={layoutRef} className={"bt-result-flow bt-result-grid-12 bt-result-layout-" + layout}
       style={{ "--bt-result-columns": columns }}>
    <nav className="bt-result-nav" aria-label="결과 분석 섹션">
      <a href="#bt-result-summary-title">요약</a>
      <a href="#bt-analysis-matrix-title">전체 차트</a>
      <span className="bt-result-layout-status" role="status">
        레이아웃: {layout} · 실제 {columns}열
      </span>
      <span className="bt-result-layout-controls" role="radiogroup" aria-label="결과 차트 레이아웃">
        {_BT_RESULT_LAYOUTS.map(mode => (
          <button key={mode} type="button" className={"btn ghost sm" + (layout === mode ? " active" : "")}
                  role="radio" aria-checked={layout === mode} onClick={() => setLayout(mode)}>
            {mode}열
          </button>
        ))}
      </span>
    </nav>
    <_BtResultCapabilities capabilities={capabilities} />
    <section className="bt-result-section bt-result-summary" aria-labelledby="bt-result-summary-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-result-summary-title" className="stom-section-label">결과 요약</div>
          <p className="bt-section-purpose">조건식, 기간, 표본 내 advisory와 핵심 지표를 한 곳에서 확인합니다.</p>
        </div>
      </div>
    {/* v5.13.2 — 이 결과가 "무엇인지" 한 줄로: 언제 실행 · 어떤 연구 · 몇 세대 ·
        어느 기간 · tick/min · 게이트. 사용자 지적("결과 요약에 상세 설명이 있었으면") 반영. */}
    <_BtRunContextBand ctx={runCtx} summary={summary} />
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
          {/* v5.13.0(I1/I2) — 최악뿐 아니라 최고 거래일도 연다. 프리필에 타임프레임(src)과
              매수/매도 조건식을 함께 실어, 리플레이 탭이 DB·신호까지 그대로 이어받게 한다
              ("눌러도 아무 일 없음"의 실체는 min/tick DB 불일치 + 조건식 미지정이었다). */}
          {(() => {
            const openReplay = (mode) => {
              try {
                const daily = ((analysis.equity || {}).daily) || [];
                let day = null;
                for (const d of daily) {
                  const pnl = Number(d && d.pnl);
                  if (!Number.isFinite(pnl)) continue;
                  if (!day || (mode === "worst" ? pnl < day.pnl : pnl > day.pnl)) day = { date: d.date, pnl };
                }
                let trade = null;
                for (const t of (analysis.mae_mfe || [])) {
                  const v = Number(t && t.pnl_pct);
                  if (!Number.isFinite(v)) continue;
                  if (!trade || (mode === "worst" ? v < trade.pnl_pct : v > trade.pnl_pct)) trade = { code: t.code, pnl_pct: v };
                }
                if (day && day.date) {
                  window.localStorage.setItem("stom_replay_prefill", JSON.stringify({
                    date: String(day.date).replace(/-/g, ""),
                    code: trade ? trade.code : "",
                    src: (spec.timeframe === "tick" || spec.timeframe === "min") ? spec.timeframe : "",
                    buy: spec.buy || result.buy || "",
                    sell: spec.sell || result.sell || "",
                    reason: mode === "worst"
                      ? `손실이 가장 컸던 거래일(${day.date})`
                      : `수익이 가장 컸던 거래일(${day.date})`,
                  }));
                }
              } catch (e) {}
              window.location.href = "/?tab=replay";
            };
            return (
              <>
                <button className="btn ghost sm" title="이 결과에서 손실이 가장 컸던 거래일·종목으로 리플레이를 연다"
                        onClick={() => openReplay("worst")}>
                  ▶ 최악 거래일 리플레이
                </button>
                <button className="btn ghost sm" title="이 결과에서 수익이 가장 컸던 거래일·종목으로 리플레이를 연다"
                        onClick={() => openReplay("best")}>
                  ▶ 최고 거래일 리플레이
                </button>
              </>
            );
          })()}
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
      <div className="bt-summary-row" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))" }}>
        {_BT_METRIC_CARDS.map(m => {
          const v = metricVal(m.key);
          const num = typeof v === "number" ? v : null;
          return <_BtMetricCard key={m.key} meta={m} num={num} dailyPnl={dailyPnl} />;
        })}
      </div>
    </div>
    </section>

    <section className="bt-result-section bt-result-analysis" aria-labelledby="bt-analysis-matrix-title">
      <div className="bt-section-heading">
        <div>
          <div id="bt-analysis-matrix-title" className="stom-section-label">전체 분석 차트 · 독립 매트릭스</div>
          <p className="bt-section-purpose">차트 하나를 하나의 근거 단위로 표시합니다. 언더워터·회귀·타이밍·GUI 패리티를 같은 크기로 직접 비교하세요.</p>
        </div>
      </div>
      {compareView && <BtCompareView cmp={compareView} onClose={onCloseCompare} />}
      <div className="bt-analysis-matrix">
        <BtEquityChart equity={analysis.equity} onBrush={capabilities.range ? onBrush : undefined}
                       brushActive={capabilities.range && !!range} onBrushClear={onBrushClear}
                       moneyCtx={moneyCtx} />
        <BtDistributionChart distribution={distribution} />
        <BtUnderwaterChart underwater={analysis.underwater} />
        {capabilities.monteCarlo ? (
          <BtMonteCarloChart mc={mc} loading={mcLoading} onRun={onRunMc} moneyCtx={moneyCtx} />
        ) : (
          <div className="panel bt-equal-card bt-analysis-unavailable" role="status">
            <div className="panel-hd"><div className="panel-hd-title"><span className="dot"></span>몬테카를로</div></div>
            <div className="panel-bd"><div className="research-empty">미지원 · {capabilities.notes.monteCarlo}</div></div>
          </div>
        )}
        <BtHeatmap heatmap={analysis.heatmap} />
        {/* v5.13.4(QSP1 P1) — 라벨셋 탐색기: 리프(시간×시총) 잔차 히트맵 + 변별 변수. */}
        <BtLeafExplorer baseUrl={baseUrl} jobId={jobId} evoSource={evoSource} isDemo={false} />
        <BtMaeMfeScatter points={analysis.mae_mfe} />
        <BtQuantPanel analysis={analysis} />
        <BtExitReasonPanel rows={analysis.exit_reasons} />
        <BtOrderflowPanel orderflow={orderflow} />
        <BtStatTestPanel stats={stats} />
        <BtRollingChart rolling={analysis.rolling} />
        <BtMonthlyCalendar monthly={analysis.monthly} />
        <BtGuiParitySection guiParity={analysis.gui_parity} />
        <BtCumulativeTradesChart data={analysis.cumulative_trades} moneyCtx={moneyCtx} />
      </div>
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
        onClose={onCloseFullscreen} moneyCtx={moneyCtx}
      />
    )}
  </div>
);
}


// 전체화면 분석 오버레이 — 차트를 2~3컬럼 그리드로 크게 배치(인사이트 우선 노출).
//   인라인 스타일 풀스크린(position:fixed). 닫기: ✕ 버튼 또는 Esc(상위에서 처리).
function _BtFullscreenAnalysis({
  analysis, distribution, orderflow, stats, insights,
  mc, mcLoading, onRunMc, range, onBrush, onBrushClear, onClose, moneyCtx,
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

      <div className="bt-analysis-matrix bt-analysis-matrix-fullscreen">
        <BtEquityChart equity={analysis.equity} onBrush={onBrush}
                       brushActive={!!range} onBrushClear={onBrushClear} moneyCtx={moneyCtx} />
        <BtDistributionChart distribution={distribution} />
        <BtUnderwaterChart underwater={analysis.underwater} />
        <BtMonteCarloChart mc={mc} loading={mcLoading} onRun={onRunMc} moneyCtx={moneyCtx} />
        <BtHeatmap heatmap={analysis.heatmap} />
        <BtMaeMfeScatter points={analysis.mae_mfe} />
        <BtQuantPanel analysis={analysis} />
        <BtExitReasonPanel rows={analysis.exit_reasons} />
        <BtOrderflowPanel orderflow={orderflow} />
        <BtStatTestPanel stats={stats} />
        <BtRollingChart rolling={analysis.rolling} />
        <BtMonthlyCalendar monthly={analysis.monthly} />
        <BtGuiParitySection guiParity={analysis.gui_parity} />
        <BtCumulativeTradesChart data={analysis.cumulative_trades} moneyCtx={moneyCtx} />
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
  if ((meta.key === "win_rate" || meta.key === "mdd_pct" || meta.key === "mdd_on_capital_pct") && num != null) {
    const gaugeColor = meta.key === "win_rate" ? "var(--teal)" : "var(--red)";
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
    <div className="bt-metric-card" title={meta.hint || undefined}>
      <span className="summary-lbl">{meta.label}{meta.hint ? <span className="bt-metric-help" aria-hidden="true">ⓘ</span> : null}</span>
      <span className="summary-val" style={{ color }}>{shown != null ? meta.fmt(shown) : "—"}</span>
      {meta.hint && <span className="bt-metric-hint">{meta.hint}</span>}
    </div>
  );
}

/* v5.13.2 — 실행 맥락 밴드. "이 숫자가 언제·무엇을 돌린 결과인지"를 요약 맨 위에 둔다.
   tick/min 배지를 여기서 처음 제시한다(엔진 CSV 시각 자릿수로 판별 — 추측 아님). */
const _BT_TF_LABEL = {
  tick: { text: "TICK (틱 단위)", cls: "tick", tip: "틱 백테 — 초 단위 체결. 보유시간이 초로 기록됩니다." },
  min: { text: "MIN (분 단위)", cls: "min", tip: "분봉 백테 — 분 단위 체결. 보유시간이 분으로 기록됩니다." },
  unknown: { text: "타임프레임 미상", cls: "unknown", tip: "결과 CSV 에서 타임프레임을 판별하지 못했습니다." },
};
function _btCtxDate(ymd) {
  const s = String(ymd || "");
  return s.length === 8 ? `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}` : (s || "—");
}
function _BtRunContextBand({ ctx, summary }) {
  if (!ctx || !ctx.run_id) return null;
  const tf = _BT_TF_LABEL[ctx.timeframe] || _BT_TF_LABEL.unknown;
  const executed = ctx.executed_at ? String(ctx.executed_at).replace("T", " ") : "기록 없음";
  const period = (ctx.period_start || ctx.period_end)
    ? `${_btCtxDate(ctx.period_start)} ~ ${_btCtxDate(ctx.period_end)}`
    : "—";
  const span = ctx.calendar_days
    ? `${ctx.calendar_days}일(거래일 ${ctx.trading_days || 0}일)` : "—";
  // 운용 자본은 손익이 아니므로 부호(+)를 붙이지 않는다(fmtMoney 는 signed 표기).
  const capital = typeof ctx.capital_krw === "number" && Number.isFinite(ctx.capital_krw)
    ? Math.round(ctx.capital_krw).toLocaleString("ko-KR") + "원" : "—";
  return (
    <div className="bt-runctx-band" aria-label="이 결과의 실행 맥락">
      <div className="bt-runctx-head">
        <span className={"bt-tf-badge " + tf.cls} title={tf.tip}>{tf.text}</span>
        <b className="mono bt-runctx-run" title="연구 run · 세대">{ctx.run_id} · {ctx.gen_no}세대</b>
        {ctx.research_label && <span className="bt-runctx-gist mono" title="연구 라벨(strategy_gist)">{ctx.research_label}</span>}
        <span className={"badge " + (ctx.gate_passed ? "ok" : "warn")}
              title="연구 게이트(품질 기준) 통과 여부">{ctx.gate_passed ? "게이트 통과" : "게이트 미통과"}</span>
      </div>
      <div className="bt-runctx-grid mono">
        <div><span className="k">실행 시각</span><b>{executed}</b></div>
        <div><span className="k">대상 기간</span><b>{period}</b></div>
        <div><span className="k">기간 길이</span><b>{span}</b></div>
        <div><span className="k">운용 자본</span><b>{capital}</b></div>
        <div><span className="k">보유시간(중앙)</span><b>{btFmtHold(summary && summary.median_hold_sec)}</b></div>
        <div><span className="k">최장 보유</span><b>{btFmtHold(summary && summary.max_hold_sec)}</b></div>
      </div>
      <p className="bt-runctx-note">
        아래 <b>자본대비 수익률</b>은 운용자본 기준 실제 수익률이고,
        <b> 거래수익률 합</b>은 거래별 수익률을 그냥 더한 참고치입니다 — 두 값이 다른 것이 정상입니다.
      </p>
    </div>
  );
}

export { BtResultArea, ResultDetailBody };
