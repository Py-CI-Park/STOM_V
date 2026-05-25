/* Backtest engine status panel + live equity/drawdown mini-chart */
const { useState: useState_e, useMemo: useMemo_e, useRef: useRef_e } = React;

function fmtElapsed(ms) {
  if (!ms || ms < 0) return "0.0s";
  if (ms < 60_000) return (ms / 1000).toFixed(1) + "s";
  const m = Math.floor(ms / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function EnginePanel({ state }) {
  const e = state.engine || {};
  const running = state.status === "running" || state.status === "stopping";

  const cpu = e.cpu_pct ?? 0;
  const mem = e.mem_mb ?? 0;
  const memCap = e.mem_cap_mb || 8192;
  const memPct = Math.min(100, (mem / memCap) * 100);
  const workers = e.workers ?? 0;
  const workersActive = e.workers_active ?? 0;
  const tput = e.throughput ?? 0;
  const progress = e.progress ?? 0;

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
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="tag-slim">
            {state.bt_timeframe || "min"}
          </span>
          <span className="tag-slim">
            chunks {e.chunks_done ?? 0}/{e.chunks_total ?? 0}
          </span>
        </div>
      </div>
      <div className="panel-bd">
        <div className="engine-grid">
          {/* CPU */}
          <div className="engine-cell">
            <div className="lbl">CPU 사용률</div>
            <div className="val tnum">
              {cpu.toFixed(1)}<span className="unit">%</span>
            </div>
            <div className="mini-bar">
              <div className={cpu > 85 ? "warn" : cpu < 10 ? "cool" : ""} style={{ width: `${Math.min(100, cpu)}%` }}></div>
            </div>
          </div>

          {/* Memory */}
          <div className="engine-cell">
            <div className="lbl">메모리</div>
            <div className="val tnum">
              {mem >= 1024 ? (mem / 1024).toFixed(2) : mem}
              <span className="unit">{mem >= 1024 ? "GB" : "MB"}</span>
            </div>
            <div className="mini-bar">
              <div className={memPct > 80 ? "warn" : memPct < 10 ? "cool" : ""} style={{ width: `${memPct}%` }}></div>
            </div>
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
            <div className="val tnum mono" style={{ fontSize: 15 }}>{fmtElapsed(e.elapsed_ms)}</div>
            <div className="sub">ETA {fmtElapsed(e.eta_ms)}</div>
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

          {/* Progress within gen */}
          <div className="engine-cell">
            <div className="lbl">세대 백테 진행</div>
            <div className="val tnum">
              {(progress * 100).toFixed(0)}<span className="unit">%</span>
            </div>
            <div className="mini-bar">
              <div style={{ width: `${progress * 100}%` }}></div>
            </div>
          </div>
        </div>
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
          <span style={{ fontSize: 10.5, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
            <span style={{ color: lastPnl >= 0 ? "var(--teal)" : "var(--red)" }}>
              {lastPnl >= 0 ? "+" : "−"}{Math.abs(lastPnl).toLocaleString("ko-KR")}원
            </span>
            <span style={{ color: "var(--ink-3)" }}> ({lastPnlPct >= 0 ? "+" : ""}{lastPnlPct.toFixed(2)}%)</span>
          </span>
          <span style={{ fontSize: 10.5, color: "var(--red)", fontFamily: "var(--mono)" }}>
            DD {lastDD.toFixed(2)}%
          </span>
          <span style={{ fontSize: 10.5, color: "var(--ink-2)", fontFamily: "var(--mono)" }}>
            trades {trades.length}
          </span>
        </div>
      </div>
      <div className="panel-bd">
        <div className="live-chart-wrap">
          <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
            <defs>
              <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#4cd6b3" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#4cd6b3" stopOpacity="0" />
              </linearGradient>
              <linearGradient id="dd-grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#ff6b6b" stopOpacity="0.20" />
                <stop offset="100%" stopColor="#ff6b6b" stopOpacity="0" />
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
