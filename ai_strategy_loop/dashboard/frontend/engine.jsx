/* Backtest engine status panel + live equity/drawdown mini-chart */
const { useState: useState_e, useMemo: useMemo_e, useRef: useRef_e } = React;

function fmtElapsed(ms) {
  if (!ms || ms < 0) return "0.0s";
  if (ms < 60_000) return (ms / 1000).toFixed(1) + "s";
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function fmtEpoch(epochSec) {
  if (typeof epochSec !== "number" || !Number.isFinite(epochSec) || epochSec <= 0) return "-";
  return new Date(epochSec * 1000).toLocaleString("ko-KR", { hour12: false });
}

// 게이지 바(.stom-gauge) — 임계값 색상은 styles.css 토큰(.warn=--amber/.danger=--red)으로만.
//   값이 null/undefined/NaN 이면 빈 바 + "—" 값으로 표기(크래시 금지).
function GaugeRow({ label, value, unit, warn, danger }) {
  const hasValue = typeof value === "number" && Number.isFinite(value);
  const pct = hasValue ? Math.max(0, Math.min(100, value)) : 0;
  let fillClass = "stom-gauge-fill";
  if (hasValue && typeof danger === "number" && value >= danger) fillClass += " danger";
  else if (hasValue && typeof warn === "number" && value >= warn) fillClass += " warn";
  const valText = hasValue ? `${value.toFixed(1)}${unit || ""}` : "—";
  return (
    <div className="stom-gauge-row">
      <div className="stom-gauge-label">{label}</div>
      <div className="stom-gauge">
        <div className={fillClass} style={{ width: `${pct}%` }}></div>
      </div>
      <div className="stom-gauge-val">{valText}</div>
    </div>
  );
}

function EnginePanel({ state, wsStatus }) {
  const latest = state.latest || {};
  const progressInfo = latest.backtest_progress || {};
  const engineState = latest.engine_state || {};
  const e = state.engine || engineState || {};
  const running = state.status === "running" || state.status === "stopping";

  // LIVE↔DEMO 분리(M1): engine.* 메트릭(CPU/메모리/워커/throughput/chunks)은 backend가
  //   발행하지 않는 DEMO 전용 필드다(connection.jsx 필드경계 주석 참조). 데모면 DEMO 배지,
  //   라이브인데 engine 데이터가 없으면 "실시간 데이터 대기"로 명시 분리한다.
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const liveNoEngine = !isDemo && !state.engine && !latest.engine_state;

  const cpu = e.cpu_pct ?? 0;
  const mem = e.mem_mb ?? 0;
  const memCap = e.mem_cap_mb || 8192;
  const memPct = Math.min(100, (mem / memCap) * 100);
  // 게이지용 null-safe 값(0 과 "없음"을 구분 — 필드 부재 시 게이지는 빈 바 + "—").
  const cpuGauge = typeof e.cpu_pct === "number" ? e.cpu_pct : null;
  const memPctGauge = typeof e.mem_mb === "number" ? memPct : null;
  const workers = e.workers ?? 0;
  const workersActive = e.workers_active ?? 0;
  const tput = e.throughput ?? 0;
  const progress = typeof progressInfo.percent === "number"
    ? Math.max(0, Math.min(1, progressInfo.percent / 100))
    : (e.progress ?? 0);
  const maxGens = progressInfo.max_generations || state.max_generations || 0;
  const currentGen = typeof progressInfo.current_gen === "number"
    ? progressInfo.current_gen : (state.current_gen || 0);
  const overallPct = typeof progressInfo.percent === "number"
    ? Math.max(0, Math.min(100, progressInfo.percent))
    : (maxGens > 0 ? Math.min(100, (currentGen / maxGens) * 100) : Math.min(100, progress * 100));
  const remainingGens = Math.max(0, maxGens - currentGen);
  const elapsedMs = typeof progressInfo.elapsed_sec === "number" ? progressInfo.elapsed_sec * 1000 : (e.elapsed_ms ?? 0);
  const etaMs = typeof progressInfo.eta_sec === "number" ? progressInfo.eta_sec * 1000 : (e.eta_ms ?? 0);
  const activeConfig = state.active_config || engineState.active_config || {};
  const progressSource = progressInfo.progress_source || progressInfo.source || "counter unavailable";
  const doneUnits = progressInfo.done_units ?? progressInfo.current_gen ?? currentGen;
  const totalUnits = progressInfo.total_units ?? progressInfo.max_generations ?? maxGens;
  const engineMode = engineState.bt_engine_mode || activeConfig.bt_engine_mode || "-";
  const btTimeframe = state.bt_timeframe || progressInfo.timeframe || engineState.bt_timeframe || activeConfig.bt_timeframe || "min";
  const cpuCount = engineState.cpu_count ?? e.cpu_count ?? "-";
  const effectiveEngineCount = engineState.effective_engine_count ?? e.effective_engine_count ?? workers ?? "-";
  const evolutionMode = activeConfig.evolution_mode || engineState.evolution_mode || "-";
  const genModeLabel = evolutionMode === "ga" ? "GA population generation" : "gen = generation";
  const recentLogs = Array.isArray(engineState.recent_logs) ? engineState.recent_logs : [];
  const timeoutSec = progressInfo.timeout_sec ?? engineState.timeout_sec ?? activeConfig.bt_warm_run_timeout ?? activeConfig.bt_timeout;
  const timeoutMs = typeof timeoutSec === "number" ? timeoutSec * 1000 : 0;
  const timeoutDeadline = progressInfo.timeout_deadline_epoch ?? engineState.timeout_deadline_epoch;
  const periodStart = engineState.bt_full_start ?? activeConfig.bt_full_start ?? "-";
  const periodEnd = engineState.bt_full_end ?? activeConfig.bt_full_end ?? "-";
  const windowStart = engineState.bt_universe_start_time ?? activeConfig.bt_universe_start_time ?? "-";
  const windowEnd = engineState.bt_universe_end_time ?? activeConfig.bt_universe_end_time ?? "-";
  const warmTimeout = engineState.bt_warm_run_timeout ?? activeConfig.bt_warm_run_timeout ?? "-";
  const coldTimeout = engineState.bt_timeout ?? activeConfig.bt_timeout ?? "-";

  // Worker pip array
  const pips = [];
  for (let i = 0; i < workers; i++) {
    pips.push(i < workersActive ? "active" : "idle");
  }

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: running ? "var(--amber)" : "var(--ink-3)" }}></span>
          백테스트 엔진 — Runtime
          {isDemo && typeof window.DemoBadge === "function" && <DemoBadge />}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="tag-slim">
            {btTimeframe}
          </span>
          <span className="tag-slim">
            chunks {e.chunks_done ?? 0}/{e.chunks_total ?? 0}
          </span>
        </div>
      </div>
      <div className="panel-bd">
        <div className="engine-summary-strip">
          <span><b>Overall Progress</b> {overallPct.toFixed(1)}%</span>
          <span><b>Elapsed</b> {fmtElapsed(elapsedMs)}</span>
          <span><b>Remaining</b> {remainingGens} gen</span>
          <span><b>ETA</b> {fmtElapsed(etaMs)}</span>
          <span><b>Timeout</b> {fmtElapsed(timeoutMs)}</span>
          <span><b>Deadline</b> {fmtEpoch(timeoutDeadline)}</span>
          <span><b>Progress Source</b> {progressSource}</span>
          <span><b>Units</b> {doneUnits}/{totalUnits}</span>
        </div>
        <div className="engine-config-strip">
          <span><b>Engine Config</b></span>
          <span>min/tick={btTimeframe}</span>
          <span>mode={engineMode}</span>
          <span>cpu={cpuCount}</span>
          <span>engines={effectiveEngineCount}</span>
          <span>{genModeLabel}</span>
          <span>Period {periodStart}~{periodEnd}</span>
          <span>bt_full_start={periodStart}</span>
          <span>bt_full_end={periodEnd}</span>
          <span>window={windowStart}~{windowEnd}</span>
          <span>bt_timeout={coldTimeout}</span>
          <span>bt_warm_run_timeout={warmTimeout}</span>
        </div>
        <div className="engine-log-strip">
          <span><b>Recent Logs</b></span>
          <span>{progressInfo.phase || latest.phase || state.status || "-"}</span>
          <span>{progressInfo.message || latest.last_checkpoint || e.current_symbol || "waiting for engine event"}</span>
          {recentLogs.slice(-2).map((line, i) => (
            <span key={i}>{line}</span>
          ))}
        </div>
        {liveNoEngine && typeof window.LivePending === "function" ? (
          <LivePending note="엔진 런타임 메트릭(CPU/메모리/워커)은 backend가 아직 발행하지 않습니다." />
        ) : (
        <div className="engine-grid">
          {/* DEMO 명시(P4): 데모 소스면 런타임 게이지가 backend 미발행 시뮬값임을 분명히 표기
              (전체화면 헤더 DemoBadge 와 별개로, 게이지 바로 위에 오해 방지 캡션). */}
          {isDemo && (
            <div className="mono" title="이 런타임 게이지는 데모 시뮬레이션 값입니다 — 실제 엔진이 발행하지 않습니다."
                 style={{ gridColumn: "1 / -1", fontSize: 10.5, color: "var(--ink-3)",
                          padding: "4px 8px", border: "1px dashed var(--line-1)", borderRadius: 4 }}>
              DEMO 시뮬값 — CPU·메모리·워커·처리량 게이지는 데모 시뮬레이션 값입니다(backend 미발행)
            </div>
          )}
          {/* CPU — 게이지(warn ≥70 amber, danger ≥90 red), 텍스트 수치 병기 */}
          <div className="engine-cell">
            <div className="lbl">CPU 사용률</div>
            <div className="val tnum">
              {cpu.toFixed(1)}<span className="unit">%</span>
            </div>
            <GaugeRow label="CPU" value={cpuGauge} unit="%" warn={70} danger={90} />
          </div>

          {/* Memory — 게이지(warn ≥75 amber, danger ≥90 red), 텍스트 수치 병기 */}
          <div className="engine-cell">
            <div className="lbl">메모리</div>
            <div className="val tnum">
              {mem >= 1024 ? (mem / 1024).toFixed(2) : mem}
              <span className="unit">{mem >= 1024 ? "GB" : "MB"}</span>
            </div>
            <GaugeRow label="Mem %" value={memPctGauge} unit="%" warn={75} danger={90} />
            <div className="sub">/ {(memCap / 1024).toFixed(1)} GB cap</div>
          </div>

          {/* Workers */}
          <div className="engine-cell">
            <div className="lbl">병렬 워커</div>
            <div className="val tnum">
              {workersActive}<span className="unit">/ {workers}</span>
            </div>
            <div className="workers-row">
              {pips.map((s, i) => (
                <span key={i} className={`worker-pip ${s}`}></span>
              ))}
            </div>
          </div>

          {/* Throughput */}
          <div className="engine-cell">
            <div className="lbl">처리량</div>
            <div className="val tnum">
              {tput >= 1000 ? (tput / 1000).toFixed(1) : tput}
              <span className="unit">{tput >= 1000 ? "k/s" : "candles/s"}</span>
            </div>
            <div className="sub">{tput.toLocaleString("ko-KR")} candles/sec</div>
          </div>

          {/* Elapsed / ETA */}
          <div className="engine-cell">
            <div className="lbl">경과 시간</div>
            <div className="val tnum mono" style={{ fontSize: 15 }}>{fmtElapsed(elapsedMs)}</div>
            <div className="sub">ETA {fmtElapsed(etaMs)}</div>
          </div>

          {/* Current Symbol */}
          <div className="engine-cell" style={{ gridColumn: "span 2" }}>
            <div className="lbl">처리중 종목</div>
            <div className="val mono" style={{ fontSize: 14 }}>
              {e.current_symbol || "—"}
            </div>
            <div className="sub">
              window {e.current_window?.from || "—"} → {e.current_window?.to || "—"}
            </div>
          </div>

          {/* 세대 내 진행(숫자) + 전체 진행(게이지) — Phase12-A: 게이지 라벨을 '전체'로
              명확화(숫자=세대 내, 게이지=세대 누적 전체로 서로 다른 지표임을 구분). */}
          <div className="engine-cell">
            <div className="lbl">세대 백테 진행</div>
            <div className="val tnum">
              {(progress * 100).toFixed(0)}<span className="unit">%</span>
              <span className="unit"> (세대 내)</span>
            </div>
            <GaugeRow label="전체" value={overallPct} unit="%" />
          </div>
        </div>
        )}
      </div>
    </div>
  );
}

// ---------- Live equity / drawdown chart for current gen ----------
function LiveBacktestChart({ state }) {
  const equity = state.current_run?.equity || [];
  const drawdown = state.current_run?.drawdown || [];
  const trades = state.current_run?.trades || [];
  const baseline = 10_000_000;

  const W = 880, H = 240;
  const padL = 60, padR = 60, padT = 14, padB = 26;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const xMax = Math.max(60, equity.length, ...(equity[equity.length - 1] ? [equity[equity.length - 1].t] : [60]));
  const eqVals = equity.map(p => p.value);
  const maxEq = Math.max(baseline * 1.02, ...eqVals);
  const minEq = Math.min(baseline * 0.98, ...eqVals);
  const ddMax = Math.max(2, ...drawdown.map(p => p.value_pct), 8);

  const x = (t) => padL + (t / xMax) * innerW;
  const y = (v) => padT + innerH - ((v - minEq) / Math.max(1, (maxEq - minEq))) * innerH;
  const yDD = (v) => padT + (v / ddMax) * innerH;   // drawdown shown inverted from top

  const eqPath = useMemo_e(() => {
    if (!equity.length) return "";
    return equity.map((p, i) => `${i === 0 ? "M" : "L"} ${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");
  }, [equity, xMax, maxEq, minEq]);

  const eqAreaPath = useMemo_e(() => {
    if (equity.length < 2) return "";
    const baselineY = y(baseline);
    const start = `M ${x(equity[0].t).toFixed(1)} ${baselineY.toFixed(1)}`;
    const mid = equity.map(p => `L ${x(p.t).toFixed(1)} ${y(p.value).toFixed(1)}`).join(" ");
    const end = `L ${x(equity[equity.length - 1].t).toFixed(1)} ${baselineY.toFixed(1)} Z`;
    return `${start} ${mid} ${end}`;
  }, [equity, xMax, maxEq, minEq]);

  const ddAreaPath = useMemo_e(() => {
    if (drawdown.length < 2) return "";
    const top = padT;
    const start = `M ${x(drawdown[0].t).toFixed(1)} ${top.toFixed(1)}`;
    const mid = drawdown.map(p => `L ${x(p.t).toFixed(1)} ${yDD(p.value_pct).toFixed(1)}`).join(" ");
    const end = `L ${x(drawdown[drawdown.length - 1].t).toFixed(1)} ${top.toFixed(1)} Z`;
    return `${start} ${mid} ${end}`;
  }, [drawdown, xMax, ddMax]);

  const last = equity[equity.length - 1];
  const lastPnl = last ? (last.value - baseline) : 0;
  const lastDD = drawdown[drawdown.length - 1]?.value_pct ?? 0;
  const lastPnlPct = (lastPnl / baseline) * 100;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          현재 세대 백테스트 — Equity & Drawdown
        </div>
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <span style={{ fontSize: 13.5,  /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */ color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
            <span style={{ color: lastPnl >= 0 ? "var(--teal)" : "var(--red)" }}>
              {lastPnl >= 0 ? "+" : "−"}{Math.abs(lastPnl).toLocaleString("ko-KR")}원
            </span>
            <span style={{ color: "var(--ink-3)" }}> ({lastPnlPct >= 0 ? "+" : ""}{lastPnlPct.toFixed(2)}%)</span>
          </span>
          <span style={{ fontSize: 13.5,  /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */ color: "var(--red)", fontFamily: "var(--mono)" }}>
            DD {lastDD.toFixed(2)}%
          </span>
          <span style={{ fontSize: 13.5,  /* G-2(2026-06-11): 10.5 → 13.5 — 지표 가독성 상향. */ color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
            trades {trades.length}
          </span>
        </div>
      </div>
      <div className="panel-bd">
        <div className="live-chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <defs>
              <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--teal)" stopOpacity="0.5" />
                <stop offset="100%" stopColor="var(--teal)" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="dd-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--red)" stopOpacity="0.20" />
                <stop offset="100%" stopColor="var(--red)" stopOpacity="0" />
              </linearGradient>
            </defs>

            {/* Frame */}
            <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH}
                  stroke="var(--line-2)" />
            <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" />
            <line x1={W - padR} x2={W - padR} y1={padT} y2={padT + innerH} stroke="var(--line-2)" />

            {/* Baseline */}
            <line x1={padL} x2={W - padR} y1={y(baseline)} y2={y(baseline)}
                  className="zero-line" />
            <text className="chart-axis-text" x={padL - 6} y={y(baseline) + 3} textAnchor="end">
              {(baseline / 1_000_000).toFixed(1)}M
            </text>

            {/* Y left ticks for equity */}
            {[0.25, 0.5, 0.75].map((t, i) => {
              const v = minEq + (maxEq - minEq) * t;
              return (
                <g key={`yl${i}`}>
                  <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} className="chart-grid-line" />
                  <text className="chart-axis-text" x={padL - 6} y={y(v) + 3} textAnchor="end">
                    {(v / 1_000_000).toFixed(2)}M
                  </text>
                </g>
              );
            })}

            {/* Right axis: drawdown % */}
            {[0.25, 0.5, 0.75, 1].map((t, i) => {
              const v = ddMax * t;
              return (
                <text key={`yr${i}`} className="chart-axis-text"
                      x={W - padR + 6} y={yDD(v) + 3} fill="var(--red)" opacity="0.7">
                  −{v.toFixed(1)}%
                </text>
              );
            })}

            {/* Drawdown area first (background) */}
            {drawdown.length > 1 && (
              <>
                <path d={ddAreaPath} className="dd-area" />
              </>
            )}

            {/* Equity area */}
            {equity.length > 1 && (
              <>
                <path d={eqAreaPath} className="eq-area" />
                <path d={eqPath} className={`eq-line ${lastPnl < 0 ? "eq-line-neg" : ""}`} />
              </>
            )}

            {/* Trade markers */}
            {trades.map((tr, i) => (
              <circle key={i}
                      cx={x(tr.t)} cy={y(tr.price)} r="2.5"
                      className={tr.side === "buy" ? "trade-marker-buy" : "trade-marker-sell"}
                      opacity="0.85" />
            ))}

            {/* X-axis labels */}
            <text className="chart-axis-text" x={padL} y={H - 8}>0m</text>
            <text className="chart-axis-text" x={(padL + W - padR) / 2} y={H - 8} textAnchor="middle">
              {Math.round(xMax / 2)}m
            </text>
            <text className="chart-axis-text" x={W - padR} y={H - 8} textAnchor="end">{xMax}m</text>

            {/* Legend */}
            <g transform={`translate(${padL + 8}, ${padT + 12})`}>
              <rect x="0" y="-8" width="9" height="9" fill="var(--teal)" rx="1" />
              <text x="14" y="0" className="chart-axis-text" fill="var(--ink-1)">자본</text>
              <rect x="60" y="-8" width="9" height="9" fill="var(--red)" opacity="0.6" rx="1" />
              <text x="74" y="0" className="chart-axis-text" fill="var(--ink-1)">낙폭</text>
              <circle cx="113" cy="-4" r="3" className="trade-marker-buy" />
              <text x="120" y="0" className="chart-axis-text" fill="var(--ink-1)">매수</text>
              <circle cx="148" cy="-4" r="3" className="trade-marker-sell" />
              <text x="155" y="0" className="chart-axis-text" fill="var(--ink-1)">매도</text>
            </g>
          </svg>

          {equity.length === 0 && (
            <div style={{
              position: "absolute", inset: 0,
              display: "flex", alignItems: "center", justifyContent: "center",
              color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
              pointerEvents: "none",
            }}>
              백테스트가 시작되면 자본곡선이 실시간으로 채워집니다
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { EnginePanel, LiveBacktestChart, fmtElapsed });
