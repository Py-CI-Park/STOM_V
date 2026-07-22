/* Chart — fetch 기반 백테 상세/오버랩 차트 묶음 (split from chart.jsx → chart-equity, P5.4).
   EquityOverlayChart · BacktestDetailChart — 백엔드 /equity_curves · /backtest_detail 를 fetch 해
   세대 누적곡선 오버랩과 선택 세대의 일별손익/누적/동시보유를 그리는 차트. app.jsx 가 chart.jsx
   배럴 경유로 BacktestDetailChart 등을 import.
   - 작은 표현 컴포넌트(LegendDot · Mini · MetricHelpStrip)는 chart-primitives 에서 import.
   - 포맷 헬퍼(fmtPct · fmtMoney)는 stom-ui 빌드 번들이 제공하는 전역(connection.jsx 의
     const X = window.X 별칭이 babel 스코프보다 먼저 로드)을 bare 호출로 그대로 쓴다.
   - 축 눈금(_axisTicks)도 stom-ui(bundle/stom-ui.js, 소스 format.mjs)가 window._axisTicks 로
     제공하므로 babel 스코프 별칭만 둔다(NEVER import-convert).
*/
import { LegendDot, Mini, MetricHelpStrip } from "./chart-primitives.jsx";
import { ChartFrame } from "./chart-frame.jsx";

// 축 눈금 값 배열 — Phase14.3 de-dup: 구현은 빌드 번들(bundle/stom-ui.js, 소스 format.mjs)이
//   window._axisTicks 로 제공(ESM 모듈이라 babel 실행보다 먼저 로드). 여기서는 babel 스코프
//   별칭만 둔다. P5.4: 단일 번들 한 스코프에서 같은 최상위 이름이 두 파일에 있으면 충돌하므로
//   (chart-equity 가 이미 const _axisTicks 선언) 이 파일은 _bdAxisTicks 로 파일-고유 별칭한다.
const _bdAxisTicks = window._axisTicks;

/* R-Viz1 — 전 전략 누적 수익곡선 오버랩 차트.
   /equity_curves(GET)에서 세대별 수익금합계 시계열을 받아 멀티라인으로 겹쳐 그린다.
   - 흐린 회색 얇은 선: 전체 곡선(비우승).
   - 색 굵은 선: gate_passed=True(우승) 곡선.
   - 손익분기(y=0) 기준선.
   - 30초 자동 새로고침 + 수동 새로고침 버튼.
   - hover 시 run/gen·final_pct 툴팁. */
const { useState: useState_eq, useEffect: useEffect_eq, useCallback: useCallback_eq, useRef: useRef_eq } = React;

function _validEquityCurves(payload, runId) {
  return !!payload && Array.isArray(payload.curves) && payload.curves.every(curve =>
    curve && Array.isArray(curve.equity) && curve.equity.length >= 2
    && curve.equity.every(value => typeof value === "number" && Number.isFinite(value))
    && typeof curve.run_id === "string" && (!runId || curve.run_id === runId)
    && Number.isFinite(curve.gen_no)
    && typeof curve.final_pct === "number" && Number.isFinite(curve.final_pct)
    && typeof curve.gate_passed === "boolean"
  );
}

// 우승 곡선 색 팔레트 (최대 12개).
const _EQ_WINNER_COLORS = [
  "#4cd6b3", "#a594ff", "#f0b35a", "#6aa6ff",
  "#ff7eb6", "#73d673", "#ff9966", "#c084fc",
  "#38bdf8", "#fb923c", "#a3e635", "#f472b6",
];

function EquityOverlayChart({ baseUrl, wsStatus, runId }) {
  const [data, setData] = useState_eq(null);   // {curves, count}
  const [loading, setLoading] = useState_eq(false);
  const [err, setErr] = useState_eq(null);
  const [hover, setHover] = useState_eq(null); // {x_frac, curves_at_x:[{run_id,gen_no,gate_passed,final_pct,y}]}
  const [periodInfo, setPeriodInfo] = useState_eq(null); // {runId, period:"YYYY-MM-DD ~ YYYY-MM-DD", timeframe}
  const svgRef = useRef_eq(null);
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const overlayRequestRef = useRef_eq({ key: "", controller: null });
  const durationRequestRef = useRef_eq({ key: "", controller: null });
  const refresh = useCallback_eq(() => {
    if (overlayRequestRef.current.controller) overlayRequestRef.current.controller.abort();
    if (isDemo || !baseUrl) {
      overlayRequestRef.current = { key: "", controller: null };
      setData(null); setErr(null); setHover(null); setLoading(false);
      return;
    }
    const key = runId || "__all__";
    const controller = new AbortController();
    overlayRequestRef.current = { key, controller };
    setData(null); setErr(null); setHover(null);
    setLoading(true);
    // 현재 run만 조회 — 전체 이력의 과발화 폭망 곡선(±수십억)이 y스케일을 장악해
    //   정상 곡선이 0선에 압착되는 문제 회피. runId 없으면 전체(하위호환).
    const url = baseUrl + "/equity_curves" + (runId ? "?run_id=" + encodeURIComponent(runId) : "");
    fetch(url, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(4000)]) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (overlayRequestRef.current.key !== key || controller.signal.aborted) return;
        if (!_validEquityCurves(j, runId)) throw new Error("Malformed equity curves response");
        setData({ ...j, _requestKey: key }); setErr(null);
      })
      .catch(e => {
        if (overlayRequestRef.current.key === key && !controller.signal.aborted) setErr(String(e));
      })
      .finally(() => {
        if (overlayRequestRef.current.key === key && !controller.signal.aborted) setLoading(false);
      });
  }, [baseUrl, isDemo, runId]);

  // 최초 + 30초 자동 새로고침.
  useEffect_eq(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  // 백테 기간(연도 포함) — /generation_durations 가 run config 의 bt_full_start/end 를
  //   "YYYY-MM-DD ~ YYYY-MM-DD" 로 이미 제공한다. 응답은 현재 run에만 귀속한다.
  useEffect_eq(() => {
    if (durationRequestRef.current.controller) durationRequestRef.current.controller.abort();
    const key = runId || "";
    setPeriodInfo(null);
    if (isDemo || !baseUrl || !runId) {
      durationRequestRef.current = { key: "", controller: null };
      return;
    }
    const controller = new AbortController();
    durationRequestRef.current = { key, controller };
    fetch(baseUrl + "/generation_durations?run_id=" + encodeURIComponent(runId),
          { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(4000)]) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        if (durationRequestRef.current.key !== key || controller.signal.aborted) return;
        const first = ((j && j.durations) || []).find(d => d.period) || null;
        setPeriodInfo(first ? { runId, period: first.period, timeframe: first.timeframe } : null);
      })
      .catch(() => {
        if (durationRequestRef.current.key === key && !controller.signal.aborted) setPeriodInfo(null);
      });
    return () => {
      if (durationRequestRef.current.key === key) controller.abort();
    };
  }, [baseUrl, isDemo, runId]);

  const curves = data && data._requestKey === (runId || "__all__") ? data.curves : [];
  const periodMatchesRun = periodInfo && periodInfo.runId === runId;
  const winners = curves.filter(c => c.gate_passed === true);
  const nonWinners = curves.filter(c => c.gate_passed !== true);

  const W = 880, H = 320;
  const padL = 52, padR = 24, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // Y 범위: 전체 equity 값의 min/max (0 포함). 단 과발화 폭망 곡선(±수십억) outlier가
  //   스케일을 장악해 정상 곡선을 0선에 압착하지 않도록 5~95 퍼센타일로 클립한다
  //   (run 필터가 적용되면 보통 outlier가 없어 min/max와 같지만, 전체 모드 견고성용).
  const allEquity = curves.flatMap(c => c.equity || []);
  const _sortedEq = allEquity.slice().sort((a, b) => a - b);
  const _pctile = (p) => _sortedEq.length
    ? _sortedEq[Math.min(_sortedEq.length - 1, Math.max(0, Math.round(p * (_sortedEq.length - 1))))]
    : 0;
  const yRawMax = _sortedEq.length ? Math.max(0, _pctile(0.95)) : 1;
  const yRawMin = _sortedEq.length ? Math.min(0, _pctile(0.05)) : -1;
  const yRange = (yRawMax - yRawMin) || 1;

  // SVG 좌표 변환. x는 0~1 정규화(각 곡선 길이 제각각 → 거래진행%).
  const xSvg = (frac) => padL + frac * innerW;
  const ySvg = (v) => padT + innerH - ((v - yRawMin) / yRange) * innerH;
  const zeroY = ySvg(0);

  // Y 눈금 (최대 6개).
  const yTicks = (() => {
    const ticks = [];
    const rawStep = yRange / 5;
    const mag = Math.pow(10, Math.floor(Math.log10(Math.abs(rawStep) || 1)));
    const step = Math.ceil(rawStep / mag) * mag || 1;
    const start = Math.ceil(yRawMin / step) * step;
    for (let v = start; v <= yRawMax + 1e-9; v += step) {
      ticks.push(Math.round(v));
      if (ticks.length >= 8) break;
    }
    return ticks;
  })();

  // 각 곡선을 SVG path d 문자열로 변환.
  const toPath = (equity) => {
    if (!equity || equity.length < 2) return "";
    return equity.map((v, i) => {
      const fx = i / (equity.length - 1);
      return `${i === 0 ? "M" : "L"} ${xSvg(fx).toFixed(1)} ${ySvg(v).toFixed(1)}`;
    }).join(" ");
  };

  // Hover: SVG mousemove → x 위치 → 가장 가까운 포인트 요약.
  const onMove = (e) => {
    if (!curves.length || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const frac = Math.max(0, Math.min(1, (px - padL) / innerW));
    // 각 곡선에서 해당 frac 위치의 값 보간.
    const tips = curves.slice(0, 40).map(c => {  // 성능: 최대 40곡선만 툴팁
      const eq = c.equity || [];
      if (eq.length < 2) return null;
      const idx = frac * (eq.length - 1);
      const lo = Math.floor(idx), hi = Math.ceil(idx);
      const t = idx - lo;
      const y = eq[lo] * (1 - t) + (eq[hi] || eq[lo]) * t;
      return { run_id: c.run_id, gen_no: c.gen_no, gate_passed: c.gate_passed, final_pct: c.final_pct, y };
    }).filter(Boolean);
    setHover({ frac, tips });
  };
  const onLeave = () => setHover(null);

  // 통계.
  const winnerCount = winners.length;
  const totalCount = curves.length;
  const maxFinalPct = curves.length ? Math.max(...curves.map(c => c.final_pct)) : null;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          전 전략 누적 수익곡선
          <span data-tip="이 run 의 모든 세대(전략)의 백테스트 누적 수익금을 한 차트에 겹쳐, 우승(게이트 통과) 전략이 비우승 대비 얼마나 우월한지 한눈에 비교합니다. X축 = 거래 진행률(전략마다 거래 수가 달라 0~100%로 정규화), Y축 = 누적 수익금(원)."
                style={{ marginLeft: 6, fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--line-2)",
                         borderRadius: "50%", width: 15, height: 15, display: "inline-flex",
                         alignItems: "center", justifyContent: "center", cursor: "help" }}>?</span>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <LegendDot color="rgba(255,255,255,0.18)" label="비우승" />
          <LegendDot color="var(--teal)" label="우승(gate_passed)" />
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading}
                  data-tip="equity curves 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd" tabIndex="0" aria-label="세대별 Equity 곡선 상세">
        <ChartFrame title="전 전략 누적 수익곡선" unit="누적 수익금(원)"
          period={periodMatchesRun && periodInfo.period ? periodInfo.period : "기간 미발행"} sampleCount={curves.length}
          freshness={loading ? "새로고침 중" : "30초 주기 조회"}
          threshold="gate_passed 우승 곡선 · 손익분기 0원"
          source="/equity_curves · /generation_durations"
          rows={curves.flatMap(c => c.equity.map((equity, point_index) => ({ run_id: c.run_id, gen_no: c.gen_no, gate_passed: c.gate_passed, final_pct: c.final_pct, point_index, equity })))}
          status={isDemo ? "stale" : err ? "malformed" : curves.length ? "ready" : "empty"}>
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="전체 곡선" value={totalCount > 0 ? String(totalCount) : "—"} />
          <Mini label="우승 곡선" value={winnerCount > 0 ? String(winnerCount) : "—"}
                color={winnerCount > 0 ? "var(--teal)" : undefined} />
          <Mini label="최고 수익률"
                value={maxFinalPct != null ? (maxFinalPct >= 0 ? "+" : "") + maxFinalPct.toFixed(1) + "%" : "—"}
                color={maxFinalPct != null && maxFinalPct > 0 ? "var(--teal)" : maxFinalPct != null && maxFinalPct < 0 ? "var(--red)" : undefined} />
          <Mini label="백테 기간"
                value={periodMatchesRun && periodInfo.period ? periodInfo.period : "기간 정보 없음"}
                sub={periodMatchesRun && periodInfo.timeframe ? String(periodInfo.timeframe) : ""} />
        </div>
        <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)", marginBottom: 8 }}>
          X축 = 거래 진행률 0~100%(전략마다 거래 수가 달라 정규화) · Y축 = 누적 수익금(원) · 회색 = 비우승 · 색 = 우승(gate 통과)
        </div>
        <MetricHelpStrip items={[
          "edge_ratio = segment edge density",
          "winner curves use a 12-color palette",
          "non-winner curves stay subdued for comparison",
        ]} />

        <div className="chart-wrap">
          {isDemo ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              데모 모드 — 백엔드 연결 시 equity curves가 표시됩니다.
            </div>
          ) : err ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--red)", fontSize: 12, fontFamily: "var(--mono)" }}>
              조회 실패: {err}
            </div>
          ) : curves.length === 0 ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              세대 데이터가 누적되면 수익곡선이 표시됩니다
            </div>
          ) : (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`}
                 preserveAspectRatio="none"
                 onMouseMove={onMove} onMouseLeave={onLeave}>
              {/* Y 그리드 + 눈금 */}
              {yTicks.map((t, i) => (
                <g key={`ey${i}`}>
                  <line className="chart-grid-line"
                        x1={padL} x2={W - padR} y1={ySvg(t)} y2={ySvg(t)} />
                  <text className="chart-axis-text"
                        x={padL - 8} y={ySvg(t) + 3} textAnchor="end">
                    {Math.abs(t) >= 1e8 ? (t / 1e8).toFixed(1) + "억"
                      : Math.abs(t) >= 10000 ? (t / 10000).toFixed(0) + "만"
                      : t.toLocaleString()}
                  </text>
                </g>
              ))}
              {/* 손익분기(0) 기준선 */}
              <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                    stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
              <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end"
                    fill="var(--ink-2)">0</text>
              {/* X 축 프레임 */}
              <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* X 축 라벨 */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((f, i) => (
                <text key={`ex${i}`} className="chart-axis-text"
                      x={xSvg(f)} y={H - 10} textAnchor="middle">
                  {Math.round(f * 100)}%
                </text>
              ))}

              {/* 비우승 곡선: 얇은 회색 */}
              {nonWinners.map((c, i) => {
                const d = toPath(c.equity);
                if (!d) return null;
                return <path key={`nw${i}`} d={d} fill="none"
                             stroke="rgba(255,255,255,0.10)" strokeWidth="0.8" />;
              })}

              {/* 우승 곡선: 강조(색+굵기). 색 팔레트 순환. */}
              {winners.map((c, i) => {
                const d = toPath(c.equity);
                if (!d) return null;
                const col = _EQ_WINNER_COLORS[i % _EQ_WINNER_COLORS.length];
                return <path key={`w${i}`} d={d} fill="none"
                             stroke={col} strokeWidth="2.0" opacity="0.9" />;
              })}

              {/* Hover 수직선 */}
              {hover && (() => {
                const hx = xSvg(hover.frac);
                return <line x1={hx} x2={hx} y1={padT} y2={padT + innerH}
                             stroke="rgba(255,255,255,0.15)" strokeWidth="1" />;
              })()}
            </svg>
          )}

          {/* Hover 툴팁 */}
          {hover && hover.tips.length > 0 && (() => {
            const winTips = hover.tips.filter(t => t.gate_passed === true);
            const topTips = [
              ...winTips,
              ...hover.tips.filter(t => t.gate_passed !== true).slice(0, Math.max(0, 5 - winTips.length)),
            ];
            return (
              <div style={{
                position: "absolute", top: 16, right: 16,
                background: "var(--bg-0)", border: "1px solid var(--line-2)",
                borderRadius: 6, padding: "8px 10px",
                fontFamily: "var(--mono)", fontSize: 11,
                minWidth: 200, maxWidth: 260,
                boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
                pointerEvents: "none",
              }}>
                <div style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em",
                              textTransform: "uppercase", marginBottom: 4 }}>
                  진행 {Math.round(hover.frac * 100)}%
                </div>
                {topTips.map((t, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between",
                                        gap: 8, padding: "2px 0",
                                        color: t.gate_passed === true ? "var(--teal)" : "var(--ink-2)" }}>
                    <span>{t.run_id.slice(-6)}/g{t.gen_no}</span>
                    <span>{t.y >= 0 ? "+" : ""}{Math.round(t.y).toLocaleString()}</span>
                  </div>
                ))}
                {hover.tips.length > topTips.length && (
                  <div style={{ color: "var(--ink-3)", fontSize: 10, marginTop: 3 }}>
                    외 {hover.tips.length - topTips.length}개…
                  </div>
                )}
              </div>
            );
          })()}
        </div>
        </ChartFrame>
      </div>
    </div>
  );
}

/* O1 — 백테 상세 차트(BacktestDetailChart).
   일반 STOM 백테가 만드는 2-그래프(상단 일별손익 막대 + 하단 누적수익곡선)를 헤드리스
   루프 결과로 한 패널에 재현한다. 헤드리스 루프는 엔진 PNG 생성이 꺼져 있으나(cli/runner.py)
   per-trade 거래 CSV는 항상 생성되므로, /backtest_detail(GET)이 그 CSV를
   parse_backtest_series로 일별손익+누적곡선+낙폭으로 변환해 보낸다(추가 백테 0회).
   - 현재 run(state.run_id)의 세대 중 선택된 gen(기본=best 또는 최신)을 드롭다운으로 고른다.
   - 한 영역에 STOM fig2 재현: 일별손익 막대(이익=red 위, 손실=blue 아래, 0 기준선) 위에
     누적수익곡선(cum_profit, orange 굵은선, 별도 우측 스케일).
   - hover 시 그 거래일의 일손익·누적·낙폭(반납액) 툴팁.
   - demo면 미fetch(EquityOverlayChart 패턴). 빈 시계열이면 빈 상태 표시. */
const {
  useState: useState_bd, useEffect: useEffect_bd,
  useCallback: useCallback_bd, useRef: useRef_bd, useMemo: useMemo_bd,
} = React;

function _finiteChartNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function _validChartDate(value) {
  if (!/^\d{8}$/.test(value)) return false;
  const year = Number(value.slice(0, 4));
  const month = Number(value.slice(4, 6));
  const day = Number(value.slice(6, 8));
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

function _backtestDetailRows(payload, runId, genNo) {
  if (!payload || payload.run_id !== runId || payload.gen_no !== genNo
      || !Array.isArray(payload.daily) || !Array.isArray(payload.cumulative)
      || payload.daily.length !== payload.cumulative.length
      || (payload.drawdown != null && (!Array.isArray(payload.drawdown)
        || payload.drawdown.length !== payload.daily.length))
      || (payload.holdings != null && !Array.isArray(payload.holdings))
      || (payload.summary != null && (typeof payload.summary !== "object" || Array.isArray(payload.summary)))) {
    return null;
  }
  const rows = [];
  for (let index = 0; index < payload.daily.length; index += 1) {
    const daily = payload.daily[index];
    const cumulative = payload.cumulative[index];
    const drawdown = payload.drawdown ? payload.drawdown[index] : null;
    const date = daily && daily.date != null ? String(daily.date) : "";
    const cumulativeDate = cumulative && cumulative.date != null ? String(cumulative.date) : "";
    const drawdownDate = drawdown && drawdown.date != null ? String(drawdown.date) : "";
    if (!daily || !cumulative || !date || !_validChartDate(date)
        || (index > 0 && date <= rows[index - 1].date) || date !== cumulativeDate
        || !_finiteChartNumber(daily.daily_pnl) || !_finiteChartNumber(cumulative.cum_profit)
        || (drawdown && (!_finiteChartNumber(drawdown.drawdown) || drawdownDate !== date))) {
      return null;
    }
    rows.push({
      date, daily_pnl: daily.daily_pnl, cum_profit: cumulative.cum_profit,
      drawdown: drawdown ? drawdown.drawdown : "—",
    });
  }
  if (payload.holdings && !payload.holdings.every(h => h && _finiteChartNumber(h.count))) return null;
  const numericSummary = ["trade_count", "n_days", "peak_holdings", "final_profit", "max_drawdown"];
  if (payload.summary && !numericSummary.every(key => payload.summary[key] == null || _finiteChartNumber(payload.summary[key]))) return null;
  return rows;
}

function BacktestDetailChart({ baseUrl, wsStatus, state, externalSelGen }) {
  const rawGens = state && state.generations;
  const gens = Array.isArray(rawGens) && rawGens.every(g => g && typeof g === "object"
    && _finiteChartNumber(g.gen_no) && typeof g.gate_passed === "boolean"
    && (g.graded_score == null || _finiteChartNumber(g.graded_score))
    && (g.max_hold_count == null || _finiteChartNumber(g.max_hold_count))) ? rawGens : [];
  const runId = (state && state.run_id) || "";
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // 기본 선택 gen: gate_passed(우승) 중 점수 최고 → 없으면 최신 세대.
  const defaultGen = useMemo_bd(() => {
    if (!gens.length) return null;
    const winners = gens.filter(g => g.gate_passed === true);
    if (winners.length) {
      return winners.reduce((a, b) =>
        ((b.graded_score ?? 0) > (a.graded_score ?? 0) ? b : a)).gen_no;
    }
    return gens[gens.length - 1].gen_no;
  }, [gens]);

  const [selGen, setSelGen] = useState_bd(null);
  // run/세대 목록이 바뀌면 선택을 기본값으로 재동기화(수동 선택 후 새 run 시작 대비).
  useEffect_bd(() => { setSelGen(defaultGen); }, [defaultGen, runId, gens]);
  // #65 P1 — 외부(세대표 '백테상세' 클릭)에서 선택 세대를 내려주면 내부 선택을 동기화한다.
  //   externalSelGen이 null이면(미선택) 내부 선택/기본값을 그대로 쓴다(하위호환).
  useEffect_bd(() => {
    if (externalSelGen != null) setSelGen(externalSelGen);
  }, [externalSelGen]);
  const genNo = selGen != null ? selGen : defaultGen;

  const [data, setData] = useState_bd(null);   // {run_id,gen_no,gate_passed,daily,cumulative,drawdown,summary}
  const [loading, setLoading] = useState_bd(false);
  const [err, setErr] = useState_bd(null);
  const [hover, setHover] = useState_bd(null);  // 거래일 인덱스
  const svgRef = useRef_bd(null);
  const requestRef = useRef_bd({ key: "", controller: null });

  const refresh = useCallback_bd(() => {
    if (requestRef.current.controller) requestRef.current.controller.abort();
    if (isDemo || !baseUrl || !runId || genNo == null) {
      requestRef.current = { key: "", controller: null };
      setData(null); setErr(null); setHover(null); setLoading(false);
      return;
    }
    const key = `${runId}:${genNo}`;
    const controller = new AbortController();
    requestRef.current = { key, controller };
    setData(null); setErr(null); setHover(null);
    setLoading(true);
    const url = baseUrl + "/backtest_detail?run_id=" + encodeURIComponent(runId)
      + "&gen_no=" + encodeURIComponent(genNo);
    fetch(url, { signal: AbortSignal.any([controller.signal, AbortSignal.timeout(4000)]) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => {
        const rows = _backtestDetailRows(j, runId, genNo);
        if (requestRef.current.key !== key || controller.signal.aborted) return;
        if (!rows) throw new Error("Malformed backtest detail response");
        setData({ ...j, _chartRows: rows });
        setErr(null);
      })
      .catch(e => {
        if (requestRef.current.key === key && !controller.signal.aborted) setErr(String(e));
      })
      .finally(() => {
        if (requestRef.current.key === key && !controller.signal.aborted) setLoading(false);
      });
  }, [baseUrl, isDemo, runId, genNo]);

  // 최초 + gen 변경 + 30초 자동 새로고침.
  useEffect_bd(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => {
      clearInterval(id);
      if (requestRef.current.controller) requestRef.current.controller.abort();
    };
  }, [refresh]);

  const responseMatchesSelection = data && data.run_id === runId && data.gen_no === genNo;
  const chartRows = responseMatchesSelection ? data._chartRows : null;
  const daily = chartRows ? data.daily : [];
  const cumulative = chartRows ? data.cumulative : [];
  const drawdown = chartRows ? (data.drawdown || []) : [];
  const holdings = chartRows ? (data.holdings || []) : [];
  const summary = chartRows ? (data.summary || {}) : {};
  const detailStatus = err ? "malformed" : chartRows ? (chartRows.length ? "ready" : "empty") : (loading ? "stale" : "empty");
  const hasSeries = daily.length > 0;
  const hasHoldings = holdings.length > 0;
  const peakHoldings = summary.peak_holdings != null ? summary.peak_holdings : 0;
  const selectedGeneration = gens.find(g => g.gen_no === genNo) || null;
  const dbMaxHold = selectedGeneration && _finiteChartNumber(selectedGeneration.max_hold_count)
    ? selectedGeneration.max_hold_count : null;
  const sparseHoldSuspicious = _finiteChartNumber(summary.trade_count) && summary.trade_count >= 50
    && dbMaxHold != null
    && dbMaxHold <= 1
    && peakHoldings > dbMaxHold;
  // 무거래는 명시적으로 검증된 trade_count=0일 때만 판정한다.
  const noTrades = _finiteChartNumber(summary.trade_count) && summary.trade_count === 0;

  const W = 880, H = 320;
  const padL = 56, padR = 60, padT = 18, padB = 30;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  // 일별손익(막대) 스케일: 0 포함, ±여유. 좌축.
  const pnlVals = daily.map(d => d.daily_pnl || 0);
  const pnlMax = Math.max(0, ...pnlVals);
  const pnlMin = Math.min(0, ...pnlVals);
  const pnlRange = (pnlMax - pnlMin) || 1;
  const yPnl = (v) => padT + innerH - ((v - pnlMin) / pnlRange) * innerH;
  const zeroY = yPnl(0);  // 0 손익분기 기준선(막대 기준).

  // 누적수익(라인) 스케일: 자체 min/max(0 포함). 우축.
  const cumVals = cumulative.map(c => c.cum_profit || 0);
  const cumMax = Math.max(0, ...cumVals);
  const cumMin = Math.min(0, ...cumVals);
  const cumRange = (cumMax - cumMin) || 1;
  const yCum = (v) => padT + innerH - ((v - cumMin) / cumRange) * innerH;

  // 막대 x 위치(거래일 인덱스 기반 등간격). 막대폭은 간격의 70%.
  const n = daily.length;
  const slot = n > 0 ? innerW / n : innerW;
  const barW = Math.max(1, slot * 0.7);
  const xBar = (i) => padL + (i + 0.5) * slot;  // 막대 중심.

  const fmtMoneyShort = (v) => {
    const a = Math.abs(v);
    if (a >= 1e8) return (v / 1e8).toFixed(1) + "억";
    if (a >= 1e4) return Math.round(v / 1e4) + "만";
    return Math.round(v).toLocaleString();
  };

  // 누적 곡선 path(거래일 인덱스 → 막대 중심 x).
  const cumPath = useMemo_bd(() => {
    if (cumulative.length < 2) return "";
    return cumulative.map((c, i) =>
      `${i === 0 ? "M" : "L"} ${xBar(i).toFixed(2)} ${yCum(c.cum_profit || 0).toFixed(2)}`
    ).join(" ");
  }, [cumulative, n, cumMin, cumRange]);

  // ── 상단 보유종목수 sub-panel(STOM fig2 상단 대응) ──────────────────────
  //   동시보유 종목수(holdings: [{t_index,count}])를 이벤트(시각) 진행 축으로 계단
  //   라인 그린다. 보유금액(원)은 엔진 전용(CSV 미저장)이라 동시보유 종목수로 대체.
  const HpH = 96;                              // compact holdings strip height.
  const hpPadT = 14, hpPadB = 18;              // 상하 패딩.
  const hpInnerH = HpH - hpPadT - hpPadB;
  // x축은 하단과 동일한 [padL, W-padR] 폭을 쓰되 holdings 이벤트 인덱스로 매핑.
  const hN = holdings.length;
  const xHold = (i) => (hN <= 1
    ? padL + innerW / 2
    : padL + (i / (hN - 1)) * innerW);
  // y축: 0..max(count) (정수). 최소 1칸 확보.
  const holdMax = Math.max(1, peakHoldings, ...holdings.map(h => h.count || 0));
  const yHold = (v) => hpPadT + hpInnerH - (v / holdMax) * hpInnerH;
  // 계단(step) path: 각 점에서 수평 유지 후 다음 count로 수직 이동(보유수=정수 계단).
  const holdPath = useMemo_bd(() => {
    if (hN < 1) return "";
    let dStr = `M ${xHold(0).toFixed(2)} ${yHold(holdings[0].count || 0).toFixed(2)}`;
    for (let i = 1; i < hN; i++) {
      const x = xHold(i).toFixed(2);
      const yPrev = yHold(holdings[i - 1].count || 0).toFixed(2);
      const y = yHold(holdings[i].count || 0).toFixed(2);
      dStr += ` L ${x} ${yPrev} L ${x} ${y}`;   // 수평 후 수직 = 계단.
    }
    return dStr;
  }, [holdings, hN, holdMax]);
  // y 눈금(0·max만 — 정수). max가 작으면 중간값도.
  const holdYTicks = (() => {
    if (holdMax <= 1) return [0, 1];
    if (holdMax <= 4) return Array.from({ length: holdMax + 1 }, (_, k) => k);
    return [0, Math.round(holdMax / 2), holdMax];
  })();

  // X 라벨(거래일): 최대 ~8개만 표시(YYYYMMDD → MM/DD).
  const xLabelIdxs = (() => {
    if (n === 0) return [];
    const step = Math.max(1, Math.ceil(n / 8));
    const idxs = [];
    for (let i = 0; i < n; i += step) idxs.push(i);
    if (idxs[idxs.length - 1] !== n - 1) idxs.push(n - 1);
    return idxs;
  })();
  const fmtDate = (d) => {
    const s = String(d);
    return s.length === 8 ? s.slice(4, 6) + "/" + s.slice(6, 8) : s;
  };
  // 연도 보강 x축 라벨 — 직전 틱과 연도가 다르거나 첫 틱이면 YYYY-MM-DD, 그 외 MM/DD.
  const fmtDateY = (d, prevD) => {
    const s = String(d);
    if (s.length !== 8) return fmtDate(d);
    const ps = prevD != null ? String(prevD) : "";
    const sameYear = ps.length === 8 && ps.slice(0, 4) === s.slice(0, 4);
    return sameYear
      ? s.slice(4, 6) + "/" + s.slice(6, 8)
      : s.slice(0, 4) + "-" + s.slice(4, 6) + "-" + s.slice(6, 8);
  };

  const onMove = (e) => {
    if (!n || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    const i = Math.floor((px - padL) / slot);
    if (i >= 0 && i < n) setHover(i); else setHover(null);
  };
  const onLeave = () => setHover(null);

  return (
    <div className="panel bt-backtest-detail bt-equal-card">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          백테 상세 — 부분 GUI 패리티 · 보유 · 일별손익 · 누적수익
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <LegendDot color="var(--teal)" label="동시보유 종목수" />
          <LegendDot color="var(--red)" label="이익(일)" />
          <LegendDot color="var(--blue)" label="손실(일)" />
          <LegendDot color="var(--amber)" label="누적수익 ₩" />
          {gens.length > 0 && (
            <select
              value={genNo != null ? genNo : ""}
              onChange={e => setSelGen(Number(e.target.value))}
              className="mono"
              style={{
                fontSize: 11, background: "var(--bg-1)", color: "var(--ink-0)",
                border: "1px solid var(--line-2)", borderRadius: 5, padding: "3px 6px",
              }}
              data-tip="세대 선택">
              {gens.map(g => (
                <option key={g.gen_no} value={g.gen_no}>
                  gen_{g.gen_no}{g.gate_passed === true ? " ✓" : ""}
                </option>
              ))}
            </select>
          )}
          <button className="btn ghost sm" onClick={refresh} disabled={isDemo || loading || !runId}
                  data-tip="백테 상세 새로고침">
            {loading ? "로딩…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd bt-backtest-detail-body">
        <ChartFrame title="백테 상세" unit="일별 손익·누적 수익(원)"
          period={chartRows && chartRows.length ? `${chartRows[0].date} ~ ${chartRows[chartRows.length - 1].date}` : "기간 미발행"}
          sampleCount={chartRows ? chartRows.length : 0} freshness={loading ? "새로고침 중" : "선택 시 조회"}
          threshold="손익분기 0원 · 일자 정렬된 원본 행" source="/backtest_detail"
          rows={(chartRows || []).map(row => ({ evidence: "daily", ...row })).concat(holdings.map((holding, index) => ({ evidence: "holding", point_index: index, count: holding.count })))}
          status={detailStatus}>
        <div className="bt-detail-summary-rail">
        <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
          <Mini label="거래수" value={summary.trade_count != null ? String(summary.trade_count) : "—"} />
          <Mini label="거래일" value={summary.n_days != null ? String(summary.n_days) : "—"} />
          <Mini label="최대 동시보유"
                value={noTrades ? "거래없음" : (summary.peak_holdings != null ? String(summary.peak_holdings) : "—")}
                color={!noTrades && peakHoldings > 0 ? "var(--teal)" : "var(--ink-3)"} sub="종목수" />
          <Mini label="DB max_hold_count"
                value={dbMaxHold != null ? String(dbMaxHold) : "—"}
                color={sparseHoldSuspicious ? "var(--red)" : undefined} sub="저장값" />
          <Mini label="최종 누적수익" value={summary.final_profit != null ? fmtMoney(summary.final_profit) : "—"}
                color={summary.final_profit > 0 ? "var(--teal)"
                       : summary.final_profit < 0 ? "var(--red)" : undefined} />
          <Mini label="최대 반납액" value={summary.max_drawdown != null ? fmtMoney(summary.max_drawdown) : "—"}
                color={summary.max_drawdown > 0 ? "var(--red)" : undefined} sub="고점 대비(원)" />
        </div>
        <MetricHelpStrip items={[
          `run_id=${runId || "-"}`,
          `gen_no=${genNo != null ? genNo : "-"}`,
          "peak_holdings=0 can mean no overlap buy/sell timing data",
          `DB max_hold_count=${dbMaxHold != null ? dbMaxHold : "-"}`,
          "period/timeframe are inherited from the selected run",
        ]} />
        </div>
        {sparseHoldSuspicious && (
          <div className="research-empty danger" title="Sparse hold warning">
            Sparse hold warning: DB max_hold_count {dbMaxHold} differs from CSV peak_holdings {peakHoldings}.
            human corridor 6-12; treat this as an audit signal, not promotion proof.
          </div>
        )}

        {/* ── 상단: 동시보유 종목수 시계열(STOM fig2 상단 대응) ──
            보유금액(원)은 엔진 전용(CSV 미저장)이라 미표시, 동시보유 종목수로 대체.
            holdings(매수/매도시간 event-sweep)가 비면 이 패널은 생략한다(빈 상태). */}
        {!isDemo && !err && hasHoldings && (
          <div className="bt-detail-holdings-strip">
            <svg viewBox={`0 0 ${W} ${HpH}`} preserveAspectRatio="none"
                 style={{ width: "100%", height: HpH, display: "block" }}>
              {/* 프레임(좌·하) */}
              <line x1={padL} x2={W - padR} y1={hpPadT + hpInnerH} y2={hpPadT + hpInnerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={hpPadT} y2={hpPadT + hpInnerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* y 눈금(정수 보유수) + 가로 점선 */}
              {holdYTicks.map((tk) => (
                <g key={`hyt${tk}`}>
                  <line x1={padL} x2={W - padR} y1={yHold(tk)} y2={yHold(tk)}
                        stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
                  <text className="chart-axis-text" x={padL - 8} y={yHold(tk) + 3}
                        textAnchor="end" fill="var(--ink-2)">{tk}</text>
                </g>
              ))}
              {/* peak 강조선 */}
              {noTrades ? (
                <text className="chart-axis-text" x={W - padR + 6} y={hpPadT + hpInnerH / 2 + 3}
                      textAnchor="start" fill="var(--ink-3)">거래없음</text>
              ) : peakHoldings > 0 && (
                <text className="chart-axis-text" x={W - padR + 6} y={yHold(peakHoldings) + 3}
                      textAnchor="start" fill="var(--teal)">peak {peakHoldings}</text>
              )}
              {/* 동시보유 종목수 계단 라인(teal) */}
              <path d={holdPath} fill="none" stroke="var(--teal)" strokeWidth="1.8" opacity="0.95" />
            </svg>
            <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)",
                          marginTop: 2, paddingLeft: padL * (100 / W) + "%" }}>
              동시보유 종목수(매수~매도 구간 중첩). 보유금액(원)은 엔진 전용이라 미표시 — 동시보유 종목수로 대체.
            </div>
          </div>
        )}

        <div className="chart-wrap bt-detail-primary-chart">
          {isDemo ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              데모 모드 — 백엔드 연결 시 백테 상세가 표시됩니다.
            </div>
          ) : err ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--red)", fontSize: 12, fontFamily: "var(--mono)" }}>
              조회 실패: {err}
            </div>
          ) : !hasSeries ? (
            <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
                          color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)" }}>
              {(summary.trade_count != null && summary.trade_count === 0)
                ? "이 세대는 거래가 없습니다 (타임아웃/무거래)"
                : "백테 결과 시계열이 없습니다(CSV 없음/토글)"}
            </div>
          ) : (
            <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
                 onMouseMove={onMove} onMouseLeave={onLeave}>
              {/* 0 손익분기 기준선(막대 기준, 좌축) */}
              <line x1={padL} x2={W - padR} y1={zeroY} y2={zeroY}
                    stroke="rgba(255,255,255,0.28)" strokeWidth="1" strokeDasharray="2 3" />
              <text className="chart-axis-text" x={padL - 8} y={zeroY + 3} textAnchor="end"
                    fill="var(--ink-2)">0</text>
              {/* 좌축 라벨(일별손익 max/min) */}
              <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMax) + 3} textAnchor="end"
                    fill="var(--ink-2)">{fmtMoneyShort(pnlMax)}</text>
              {pnlMin < 0 && (
                <text className="chart-axis-text" x={padL - 8} y={yPnl(pnlMin) + 3} textAnchor="end"
                      fill="var(--ink-2)">{fmtMoneyShort(pnlMin)}</text>
              )}
              {/* 좌축 중간 눈금(일별손익) — 0·max·min 과 겹치면 생략. */}
              {_bdAxisTicks(pnlMin, pnlMax, 5).map((tv, i) => (
                (Math.abs(tv) < 1e-9 || Math.abs(tv - pnlMax) < 1e-9 || Math.abs(tv - pnlMin) < 1e-9) ? null : (
                  <g key={`byl${i}`}>
                    <line x1={padL} x2={W - padR} y1={yPnl(tv)} y2={yPnl(tv)} stroke="rgba(255,255,255,0.06)" strokeWidth="1" />
                    <text className="chart-axis-text" x={padL - 8} y={yPnl(tv) + 3} textAnchor="end" fill="var(--ink-3)">{fmtMoneyShort(tv)}</text>
                  </g>
                )
              ))}
              {/* 우축 라벨(누적수익 max/min) */}
              <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMax) + 3} textAnchor="start"
                    fill="var(--amber)">{fmtMoneyShort(cumMax)}</text>
              <text className="chart-axis-text" x={W - padR + 6} y={yCum(cumMin) + 3} textAnchor="start"
                    fill="var(--amber)">{fmtMoneyShort(cumMin)}</text>
              {/* 우축 중간 눈금(누적수익) — max·min 과 겹치면 생략. */}
              {_bdAxisTicks(cumMin, cumMax, 5).map((tv, i) => (
                (Math.abs(tv - cumMax) < 1e-9 || Math.abs(tv - cumMin) < 1e-9) ? null : (
                  <text key={`byr${i}`} className="chart-axis-text" x={W - padR + 6} y={yCum(tv) + 3} textAnchor="start" fill="var(--ink-3)">{fmtMoneyShort(tv)}</text>
                )
              ))}

              {/* X 프레임 */}
              <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              <line x1={padL} x2={padL} y1={padT} y2={padT + innerH}
                    stroke="var(--line-2)" strokeWidth="1" />
              {/* X 라벨(거래일) — 연도 경계/첫 틱은 YYYY-MM-DD, 그 외 MM/DD. */}
              {xLabelIdxs.map((i, k) => (
                <text key={`bx${i}`} className="chart-axis-text"
                      x={xBar(i)} y={H - 10} textAnchor="middle">
                  {fmtDateY(daily[i].date, k > 0 && daily[xLabelIdxs[k - 1]] ? daily[xLabelIdxs[k - 1]].date : null)}
                </text>
              ))}

              {/* 일별손익 막대(이익=red 위, 손실=blue 아래) */}
              {daily.map((d, i) => {
                const v = d.daily_pnl || 0;
                const yTop = v >= 0 ? yPnl(v) : zeroY;
                const yBot = v >= 0 ? zeroY : yPnl(v);
                const h = Math.max(0.5, yBot - yTop);
                const col = v >= 0 ? "var(--red)" : "var(--blue)";
                return <rect key={`bar${i}`} x={xBar(i) - barW / 2} y={yTop}
                             width={barW} height={h} fill={col} opacity="0.78" />;
              })}

              {/* 누적수익 곡선(우축, orange 굵은선) */}
              {cumulative.length > 1 && (
                <path d={cumPath} fill="none" stroke="var(--amber)" strokeWidth="2.2" opacity="0.95" />
              )}

              {/* Hover 수직선 + 강조 */}
              {hover != null && (() => {
                const hx = xBar(hover);
                return <g>
                  <line x1={hx} x2={hx} y1={padT} y2={padT + innerH}
                        stroke="rgba(255,255,255,0.15)" strokeWidth="1" />
                  {cumulative[hover] && (
                    <circle cx={hx} cy={yCum(cumulative[hover].cum_profit || 0)} r="3.5"
                            fill="none" stroke="var(--amber)" strokeWidth="1.5" />
                  )}
                </g>;
              })()}
            </svg>
          )}

          {/* Hover 툴팁 */}
          {hover != null && hasSeries && daily[hover] && (
            <div style={{
              position: "absolute", top: 16, right: 16,
              background: "var(--bg-0)", border: "1px solid var(--line-2)",
              borderRadius: 6, padding: "8px 10px",
              fontFamily: "var(--mono)", fontSize: 11, minWidth: 190,
              boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
            }}>
              <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em",
                            textTransform: "uppercase", marginBottom: 4 }}>
                {fmtDate(daily[hover].date)} · {String(daily[hover].date)}
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
                <span style={{ color: "var(--ink-2)" }}>일손익</span>
                <span className={daily[hover].daily_pnl > 0 ? "num-pos" : daily[hover].daily_pnl < 0 ? "num-neg" : ""}
                      style={{ textAlign: "right" }}>
                  {fmtMoney(daily[hover].daily_pnl)}
                </span>
                <span style={{ color: "var(--ink-2)" }}>누적</span>
                <span style={{ textAlign: "right", color: "var(--amber)" }}>
                  {cumulative[hover] ? fmtMoney(cumulative[hover].cum_profit) : "—"}
                </span>
                {cumulative[hover] && cumulative[hover].cum_pct != null && (
                  <>
                    <span style={{ color: "var(--ink-2)" }}>누적%</span>
                    <span style={{ textAlign: "right" }}>{fmtPct(cumulative[hover].cum_pct)}</span>
                  </>
                )}
                <span style={{ color: "var(--ink-2)" }}>반납액</span>
                <span style={{ textAlign: "right", color: "var(--red)" }}>
                  {drawdown[hover] ? fmtMoney(drawdown[hover].drawdown) : "—"}
                </span>
              </div>
            </div>
          )}
        </div>
        </ChartFrame>
      </div>
    </div>
  );
}

// Track Z (PR-3) — dual-safe ESM export (kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { BacktestDetailChart, EquityOverlayChart };
