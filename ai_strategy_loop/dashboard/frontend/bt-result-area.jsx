/* Backtest workbench analysis charts — 결과·분석 오케스트레이터 (split from backtest-charts.jsx).
   /bt/result 를 로드해 메트릭 카드 + 전체 차트/패널을 합성한다. backtest.jsx 의 BacktestTab 이 소비.
   각 차트/패널은 sibling 모듈(bt-equity-charts / bt-distribution-charts / bt-stat-panels / bt-gui-parity)
   에서 import 하고, 공용 헬퍼는 bt-chart-utils 에서 import 한다.

   무예외 fetch 헬퍼(_btFetchJson)는 bt-tab-utils.jsx 에 정의·export 된다. window 으로 재게시되지
     않으므로(전역 fallback 없음) 반드시 import 해야 한다 — bare 참조 시 esbuild 번들에서 free-global
     로 남아 load() 호출 시점에 `ReferenceError: _btFetchJson is not defined` 가 발생한다.
*/
import {
  useState_btc, useEffect_btc, useCallback_btc,
  _btDateLabel, _btDownloadAnalysisCsv, _useCountUp, _BtArcGauge, _BtSparkline,
} from "./bt-chart-utils.jsx";
import { _btFetchJson } from "./bt-tab-utils.jsx";
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

  // 결과 소스: jobId(잡) 우선, 없으면 evoSource(run_id+gen_no, 진화 세대 분석).
  //   진화 세대는 브러시/몬테카를로 구간 재계산을 지원하지 않는다(잡 전용 경로).
  const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);
  const hasSource = !!jobId || isEvo;
  const sourceKey = jobId || (isEvo ? evoSource.run_id + "/" + evoSource.gen_no : "");

  const load = useCallback_btc(() => {
    if (isDemo || !baseUrl || !hasSource) { setResult(null); return; }
    setLoading(true); setErr("");
    let url;
    if (jobId) {
      url = baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId);
      if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    } else {
      url = baseUrl + "/bt/result?run_id=" + encodeURIComponent(evoSource.run_id)
          + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
    }
    _btFetchJson(url, 8000)
      .then(j => { setResult(j); if (!(j && j.available)) setErr("결과를 찾을 수 없습니다"); })
      .catch(e => { setResult(null); setErr(String(e)); })
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, jobId, isEvo, sourceKey, range]);

  // 몬테카를로 재계산(현재 구간 반영). 잡 전용 — 진화 세대는 스킵. 무예외.
  const loadMc = useCallback_btc(() => {
    if (isDemo || !baseUrl || !jobId) { setMc(null); return; }
    setMcLoading(true);
    let url = baseUrl + "/bt/analysis/montecarlo?job_id=" + encodeURIComponent(jobId) + "&n=2000";
    if (range) { url += "&t_start=" + range.t_start + "&t_end=" + range.t_end; }
    _btFetchJson(url, 12000)
      .then(j => setMc((j && j.montecarlo) || null))
      .catch(() => setMc(null))
      .finally(() => setMcLoading(false));
  }, [baseUrl, isDemo, jobId, range]);

  useEffect_btc(() => { load(); }, [load]);
  // 소스(잡/세대)가 바뀌면 구간 선택·몬테카를로 초기화.
  useEffect_btc(() => { setRange(null); setMc(null); }, [sourceKey]);
  // 결과/구간이 바뀌면 몬테카를로 자동 재계산(성공/구간 잡일 때만; 세대는 스킵).
  useEffect_btc(() => {
    if (jobId && result && result.available && result.status !== "no_trades") { loadMc(); }
  }, [result, loadMc, jobId]);

  const onBrush = useCallback_btc((t_start, t_end) => {
    if (!jobId) { return; }   // 진화 세대는 구간 분석 미지원.
    setRange({ t_start, t_end });
  }, [jobId]);
  const onBrushClear = useCallback_btc(() => { setRange(null); }, []);

  if (!hasSource) {
    return (
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>결과 · 분석</div>
        </div>
        <div className="panel-bd">
          <div className="research-empty">
            왼쪽에서 백테스트를 실행하거나 잡 이력을 선택하면 결과·분석이 여기에 표시됩니다.
          </div>
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
        </div>
      </div>
    );
  }

  const analysis = result.analysis || {};
  // 메트릭 우선순위: CLI metrics(브리핑 필드) → 없으면 analysis.summary 매핑.
  const metrics = result.metrics || {};
  const summary = analysis.summary || {};
  const metricVal = (key) => {
    if (metrics[key] != null) return metrics[key];
    // analysis.summary 폴백 매핑(cagr 은 summary 에 없음).
    const map = {
      trade_count: summary.trade_count, win_rate: summary.win_rate,
      total_profit_pct: summary.total_profit_pct, total_profit_krw: summary.total_profit_krw,
      mdd_pct: summary.max_drawdown_pct, cagr: undefined,
    };
    return map[key];
  };

  const distribution = analysis.distribution || {};
  const insights = analysis.insights || [];
  const topC = distribution.top_contributors || [];
  const botC = distribution.bottom_contributors || [];
  const dailyPnl = ((analysis.equity || {}).daily || []).map(d => d.pnl || 0);
  const orderflow = analysis.orderflow || {};
  const stats = analysis.stats || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
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
      <div className="panel">
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
            {/* 비교 기준(A) 는 잡 전용(진화 세대는 A/B 비교 미지원). */}
            {onSetCompareA && jobId && (
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
            <button className="btn ghost sm" onClick={() => setFullscreen(true)}
                    title="전체 화면에서 더 많은 분석 그래프를 한눈에 보기 (Esc 로 닫기)">⛶ 전체화면 분석</button>
            <button className="btn ghost sm" onClick={load} disabled={loading}>{loading ? "로딩…" : "↻"}</button>
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

      {/* A/B 비교 뷰(활성 시 최상단) */}
      {compareView && <BtCompareView cmp={compareView} onClose={onCloseCompare} />}

      {/* 차트 — 수익곡선(인터랙션+브러시) → 분포 → 히트맵 → 언더워터 → MAE/MFE → 매도조건 */}
      <BtEquityChart equity={analysis.equity} onBrush={onBrush}
                     brushActive={!!range} onBrushClear={onBrushClear} />
      <BtDistributionChart distribution={distribution} />
      <BtHeatmap heatmap={analysis.heatmap} />
      <BtUnderwaterChart underwater={analysis.underwater} />
      <BtMaeMfeScatter points={analysis.mae_mfe} />
      <BtExitReasonPanel rows={analysis.exit_reasons} />

      {/* 2단계 — 몬테카를로 · 오더플로우 · 통계검정 */}
      <BtMonteCarloChart mc={mc} loading={mcLoading} onRun={loadMc} />
      <BtOrderflowPanel orderflow={orderflow} />
      <BtStatTestPanel stats={stats} />

      {/* B3 — STOM GUI 결과 이미지 2장 패리티(MDD 랜덤·일별·시간대·요일·보유금액·거래롤링) */}
      <BtGuiParitySection guiParity={analysis.gui_parity} columns={1} />

      {/* 트랙 D — 추가 분석 그래프(일반 모드에선 접이식, 전체화면에선 우선 배치) */}
      <details className="bt-extra-charts" open={false}>
        <summary style={{ cursor: "pointer", padding: "10px 14px", fontFamily: "var(--mono)", fontSize: 12, color: "var(--ink-2)", userSelect: "none" }}>
          ▸ 추가 분석 그래프 — 롤링 지표 · 월별 캘린더 · 누적 거래 (전체화면 권장)
        </summary>
        <div style={{ display: "flex", flexDirection: "column", gap: 14, marginTop: 10 }}>
          <BtRollingChart rolling={analysis.rolling} />
          <BtMonthlyCalendar monthly={analysis.monthly} />
          <BtCumulativeTradesChart data={analysis.cumulative_trades} />
        </div>
      </details>

      {/* 종목 기여 Top/Bottom */}
      {(topC.length > 0 || botC.length > 0) && (
        <div className="panel">
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
      )}

      {/* 인사이트 패널 */}
      <BtInsightsPanel insights={insights} />

      {/* 전체화면 분석 모드 오버레이(트랙 D) — position:fixed 풀스크린, 2~3컬럼 그리드 */}
      {fullscreen && (
        <_BtFullscreenAnalysis
          analysis={analysis} distribution={distribution} orderflow={orderflow}
          stats={stats} insights={insights} mc={mc} mcLoading={mcLoading} onRunMc={loadMc}
          range={range} onBrush={onBrush} onBrushClear={onBrushClear}
          onClose={() => setFullscreen(false)}
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

export { BtResultArea };
