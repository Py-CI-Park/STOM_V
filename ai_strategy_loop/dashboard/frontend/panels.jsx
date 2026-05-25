/* Reusable small panels: badges, gauges, feedback, current-gen, cost */
const { useState: useState_p, useEffect: useEffect_p, useMemo: useMemo_p } = React;

function ConnBadge({ health, wsStatus }) {
  let cls = "badge idle", label = "확인중";
  if (wsStatus === "open" && health.connected) { cls = "badge ok"; label = `백엔드 연결됨 · v${health.contract_version ?? "?"}`; }
  else if (wsStatus === "demo") { cls = "badge warn"; label = "데모 모드 (백엔드 미접속)"; }
  else if (wsStatus === "reconnecting") { cls = "badge warn"; label = "연결 끊김 · 재연결 중"; }
  else if (wsStatus === "connecting") { cls = "badge idle"; label = "연결 시도중"; }
  return (
    <span className={cls}>
      <span className={`dot ${wsStatus === "reconnecting" ? "pulse-dot" : ""}`}></span>
      {label}
    </span>
  );
}

function StatusBadge({ status }) {
  const map = {
    idle:     { cls: "badge idle", txt: "대기" },
    running:  { cls: "badge run",  txt: "실행중" },
    stopping: { cls: "badge warn", txt: "정지중" },
    complete: { cls: "badge done", txt: "완료" },
    error:    { cls: "badge err",  txt: "오류" },
  };
  const m = map[status] || map.idle;
  return (
    <span className={m.cls}>
      <span className={`dot ${status === "running" || status === "stopping" ? "pulse-dot" : ""}`}></span>
      {m.txt}
    </span>
  );
}

// ---- Current generation panel ----
function CurrentGenPanel({ state }) {
  const running = state.status === "running" || state.status === "stopping";
  const inProgress = state.generations.length < state.current_gen + (running ? 1 : 0);
  // Active gen number for display
  const activeGen = running ? state.current_gen + 1 : state.current_gen;
  const phase = state.latest?.phase || "—";
  const checkpoint = state.latest?.last_checkpoint || "—";
  const message = state.latest?.message || "";

  const phaseColor = {
    "생성중": "var(--blue)",
    "백테스트중": "var(--amber)",
    "채점중": "var(--violet)",
    "완료": "var(--teal)",
    "대기중": "var(--ink-2)",
    "정지됨": "var(--ink-1)",
    "승인 완료": "var(--teal)",
  }[phase] || "var(--ink-1)";

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: running ? "var(--amber)" : "var(--ink-3)" }}></span>
          현재 세대 — Live
        </div>
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
          {fmtTime(state.updated_at)}
        </span>
      </div>
      <div className="panel-bd">
        <div style={{ display: "flex", alignItems: "flex-end", gap: 22 }}>
          <div className="stat">
            <span className="stat-label">세대</span>
            <span className="stat-value lg mono">
              gen_{String(activeGen).padStart(2, "0")}
              <span style={{ color: "var(--ink-3)", fontSize: 16 }}> / {state.max_generations}</span>
            </span>
          </div>
          <div className="stat">
            <span className="stat-label">페이즈</span>
            <span className="stat-value mono" style={{ color: phaseColor, fontSize: 20 }}>
              {phase}
            </span>
          </div>
          <div className="stat" style={{ marginLeft: "auto", textAlign: "right" }}>
            <span className="stat-label">체크포인트</span>
            <span className="stat-sub" style={{ color: "var(--ink-1)" }}>{checkpoint}</span>
          </div>
        </div>

        {running && (
          <div style={{ marginTop: 14 }}>
            <div className="scanbar"></div>
          </div>
        )}

        <div style={{
          marginTop: 14,
          padding: "10px 12px",
          background: "var(--bg-0)",
          border: "1px solid var(--line-1)",
          borderRadius: 6,
          fontFamily: "var(--mono)",
          fontSize: 12,
          color: "var(--ink-1)",
          minHeight: 38,
          display: "flex",
          alignItems: "center",
          gap: 8,
        }}>
          <span style={{ color: "var(--ink-3)" }}>›</span>
          <span>{message || (state.status === "idle" ? "진화 시작 버튼으로 루프를 개시하세요" : "—")}</span>
        </div>
      </div>
    </div>
  );
}

// ---- Cost / cumulative panel ----
function CostPanel({ state, cap = 50000 }) {
  const tokens = state.cumulative?.tokens ?? 0;
  const cost = state.cumulative?.cost_or_count ?? 0;
  const pct = Math.min(100, (tokens / cap) * 100);
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>비용 · 누적</div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        <div className="row-2" style={{ gap: 10 }}>
          <div className="stat">
            <span className="stat-label">누적 토큰</span>
            <span className="stat-value mono">{fmtInt(tokens)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">비용 / Count</span>
            <span className="stat-value mono">${(cost).toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
          </div>
        </div>
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <span style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase" }}>
              한도 사용량
            </span>
            <span className="mono" style={{ fontSize: 11, color: pct > 80 ? "var(--amber)" : "var(--ink-1)" }}>
              {pct.toFixed(1)}% / {fmtInt(cap)}
            </span>
          </div>
          <div className="gauge">
            <div className={`gauge-fill ${pct > 80 ? "warn" : ""}`} style={{ width: `${pct}%` }}></div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---- Feedback / autopsy panel ----
function FeedbackPanel({ state }) {
  // We surface latest.message + last few gate_reasons as a "loop reasoning" view
  const history = useMemo_p(() => {
    const items = [];
    if (state.latest?.message) {
      items.push({ kind: "latest", text: state.latest.message, gen: state.current_gen });
    }
    // Take last 3 gens with a meaningful reason
    const lastGens = [...state.generations].slice(-4).reverse();
    for (const g of lastGens) {
      if (g.gate_reason && g.gate_reason !== "조건 충족") {
        items.push({ kind: "gen", text: `gen_${g.gen_no}: ${g.gate_reason}`, gen: g.gen_no });
      }
    }
    return items.slice(0, 5);
  }, [state.latest, state.generations, state.current_gen]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>피드백 · 부검</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          다음 세대에 전달되는 컨텍스트
        </span>
      </div>
      <div className="panel-bd" style={{ padding: 0 }}>
        {history.length === 0 ? (
          <div style={{ padding: 18, color: "var(--ink-3)", fontSize: 12 }}>
            아직 전달된 부검이 없습니다.
          </div>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {history.map((h, i) => (
              <li key={i} style={{
                padding: "12px 14px",
                borderBottom: i < history.length - 1 ? "1px solid var(--line-1)" : "none",
                display: "flex",
                gap: 10,
                alignItems: "flex-start",
              }}>
                <span className="mono" style={{
                  fontSize: 10.5,
                  color: h.kind === "latest" ? "var(--amber)" : "var(--ink-3)",
                  flexShrink: 0,
                  marginTop: 2,
                  width: 56,
                }}>
                  {h.kind === "latest" ? "→ LIVE" : `gen_${String(h.gen).padStart(2, "0")}`}
                </span>
                <span className="mono" style={{ fontSize: 12, color: "var(--ink-0)", lineHeight: 1.55 }}>
                  {h.text}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ConnBadge, StatusBadge, CurrentGenPanel, CostPanel, FeedbackPanel });
