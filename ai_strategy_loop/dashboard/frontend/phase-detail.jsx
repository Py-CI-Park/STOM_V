import { ReactFlow, Background, Controls, MarkerType, Position } from "@xyflow/react";
import dagre from "dagre";
/* Phase timeline + phase-aware detail panel that switches by current phase */
const { useState: useState_ph, useMemo: useMemo_ph, useEffect: useEffect_ph, useRef: useRef_ph } = React;

// =====================================================================
// LIVE↔DEMO 격차 해소(M1) 공용 컴포넌트.
//   - DemoBadge: 데모 시뮬레이터가 날조한 패널임을 명시(connection.jsx 필드경계 주석 참조).
//   - LivePending: 라이브 모드인데 backend가 아직 그 패널 데이터를 발행하지 않아 비었을 때.
// 이 두 표식이 "phase-detail 풍부 패널은 demo-only이고 live에서는 비어있을 수 있다"는
// 사실을 사용자에게 드러낸다(빈칸/stale 오해 방지).
// =====================================================================
function DemoBadge() {
  return (
    <span className="mono" style={{
      fontSize: 9.5, letterSpacing: ".12em", padding: "1px 6px", borderRadius: 4,
      background: "rgba(165,148,255,0.16)", color: "#a594ff",
      border: "1px solid rgba(165,148,255,0.4)", textTransform: "uppercase",
    }} data-tip="시뮬레이터가 생성한 데모 데이터입니다 (backend 미발행)">
      DEMO
    </span>
  );
}

function LivePending({ note }) {
  return (
    <div style={{
      padding: "24px 20px", color: "var(--ink-3)", textAlign: "center",
      fontSize: 12, fontFamily: "var(--mono)", lineHeight: 1.6,
    }} data-tip="Live data pending: waiting for a fresh live snapshot from backend.">
      <div style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 6 }}>
        실시간 데이터 대기 · Live data pending
      </div>
      {note || "Waiting for a fresh live snapshot from backend; this panel is not a stale result."}
    </div>
  );
}

const PHASES = [
  { key: "생성중",      label: "생성",      sub: "LLM Code Gen" },
  { key: "백테스트중",  label: "백테스트",  sub: "Backtest" },
  { key: "채점중",      label: "채점",      sub: "Grading" },
  { key: "부검 작성",   label: "부검",      sub: "Autopsy" },
];

// R8 — LIVE phase 영/한 정규화 맵.
//   backend(loop.py:_publish_live, ga.py)는 phase를 **영어**로 발행한다
//   (warm_prepare_start, backtest_start, backtest_end, generation_done, complete,
//    ga_evaluate_start, ga_generation_done, loop_start, warm_prepare_done, ga_init,
//    stopping). 프론트 PHASES 키는 데모 시뮬레이터가 쓰는 **한국어**라, 영어 phase는
//   phaseIndex()=-1로 떨어져 LIVE 타임라인이 영구 미점등됐다(데모에서만 동작).
//   아래 맵으로 영어 phase를 4단계 인덱스(0생성·1백테·2채점·3부검/완료)로 정규화한다.
//   (warm 준비/loop_start/ga_init=생성 단계 0, backtest_start류=백테 1,
//    backtest_end=채점 2, generation_done류/complete=부검·완료 3.)
const LIVE_PHASE_INDEX = {
  // 생성/준비(백테 이전).
  loop_start: 0,
  warm_prepare_start: 0,
  warm_prepare_done: 0,
  ga_init: 0,
  generate_start: 0,
  generate_done: 0,
  // 백테스트.
  backtest_start: 1,
  ga_evaluate_start: 1,
  // 채점(백테 종료 직후 fitness 산출).
  backtest_end: 2,
  score_start: 2,
  score_done: 2,
  // 부검/세대 완료.
  autopsy_start: 3,
  autopsy_done: 3,
  generation_done: 3,
  ga_generation_done: 3,
  complete: 3,
};

// 순수 함수(테스트 가능): phase 문자열 → 4단계 인덱스. 한국어 키(데모)와 영어 키(LIVE)
//   둘 다 인식한다. 매칭 실패는 -1(타임라인 미점등). window에 노출해 정적/단위 검증 가능.
function phaseIndex(phase) {
  // 1) 한국어 PHASES 키(데모) 우선 — 기존 동작 보존.
  const k = PHASES.findIndex(p => p.key === phase);
  if (k !== -1) return k;
  // 2) 영어 LIVE phase 정규화 맵.
  if (phase != null && Object.prototype.hasOwnProperty.call(LIVE_PHASE_INDEX, phase)) {
    return LIVE_PHASE_INDEX[phase];
  }
  // 3) stopping 등 단계 외 phase는 미점등(-1).
  return -1;
}

function PhaseTimeline({ state }) {
  const running = state.status === "running" || state.status === "stopping";
  const activeIdx = running ? phaseIndex(state.latest?.phase) : -1;
  const activeGen = running ? state.current_gen + 1 : state.current_gen;

  return (
    <div className="phase-timeline">
      {PHASES.map((p, i) => {
        const isActive = i === activeIdx;
        const isDone = activeIdx > i;
        const isPending = activeIdx < i || activeIdx === -1;
        return (
          <React.Fragment key={p.key}>
            <div className={`phase-step ${isActive ? "active" : isDone ? "done" : "pending"}`}>
              <div className="phase-num">
                {isDone ? (
                  <svg width="11" height="11" viewBox="0 0 16 16">
                    <path d="M3 8 L7 12 L13 4" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  i + 1
                )}
              </div>
              <div className="phase-step-text">
                <div className="phase-step-label">{p.label}</div>
                <div className="phase-step-sub">{p.sub}</div>
              </div>
              {isActive && <span className="phase-active-pulse"></span>}
            </div>
            {i < PHASES.length - 1 && (
              <div className={`phase-connector ${isDone ? "done" : ""}`}>
                <div className="phase-connector-fill" style={{ width: isDone ? "100%" : isActive ? "50%" : "0%" }}></div>
              </div>
            )}
          </React.Fragment>
        );
      })}
      <div className="phase-gen-tag">
        {running ? `세대 ${activeGen} 진행중` : state.status === "complete" ? `${state.current_gen}세대 완료` : "대기중"}
      </div>
    </div>
  );
}

// ===================== PHASE DETAIL PANEL =====================
function PhaseDetailPanel({ state, wsStatus, onViewLatestCode }) {
  const phase = state.latest?.phase;
  const running = state.status === "running" || state.status === "stopping";

  // LIVE↔DEMO 분리(M1): phase-detail 풍부 패널(코드 스트리밍/자본곡선/채점분해/부검
  //   스트리밍)은 모두 current_run에 의존하는 DEMO 전용 데이터다. 라이브에서 그 데이터가
  //   없으면 "실시간 데이터 대기"를 보여주고(stale/빈칸 오해 방지), 데모에서만 채운다.
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const livePending = typeof window.livePanelPending === "function"
    ? window.livePanelPending(wsStatus, state) : false;

  let body;
  if (livePending) {
    body = <LivePending />;
  } else if (phase === "생성중") {
    body = <GenerationView state={state} onViewLatestCode={onViewLatestCode} />;
  } else if (phase === "백테스트중") {
    body = <BacktestingView state={state} />;
  } else if (phase === "채점중") {
    body = <ScoringView state={state} />;
  } else if (phase === "부검 작성") {
    body = <AutopsyView state={state} />;
  } else if (!running && (state.current_run?.equity?.length || 0) > 0) {
    // Between gens or complete — show last backtest snapshot
    body = <BacktestingView state={state} />;
  } else {
    body = <IdlePhaseView />;
  }

  return (
    <div className="panel phase-detail">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: running ? "var(--amber)" : "var(--ink-3)" }}></span>
          페이즈 상세 — {phase || "—"}
          {isDemo && <DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {state.latest?.last_checkpoint || "—"}
        </span>
      </div>
      <div className="panel-bd" style={{ padding: 0 }}>
        {body}
      </div>
    </div>
  );
}

// --------- Generation view ---------
function GenerationView({ state, onViewLatestCode }) {
  const g = state.current_run?.generation || {};
  const ctx = g.prompt_context || [];
  const active = g.active || "buy";
  const showCode = active === "sell" || active === "done" ? (g.sell_code_partial || "") : (g.buy_code_partial || "");
  const codeLabel = active === "buy" ? "매수 조건식 — streaming" : active === "sell" ? "매도 조건식 — streaming" : "생성 완료";
  const buyDone = !!g.buy_done;
  const sellDone = !!g.sell_done;

  // Highlight the streaming code
  const highlighted = useMemo_ph(() => {
    if (typeof window.highlightPython === "function") {
      return window.highlightPython(showCode);
    }
    return showCode.split("\n").map((t, i) => ({ ln: i + 1, parts: [{ cls: "", t }] }));
  }, [showCode]);

  // Auto-scroll to bottom as code streams
  const codeRef = useRef_ph(null);
  useEffect_ph(() => {
    if (codeRef.current) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [showCode]);

  return (
    <div className="gen-view">
      <div className="gen-view-grid">
        {/* Left: prompt context */}
        <div className="gen-side">
          <div className="side-section">
            <div className="side-section-title">LLM 호출</div>
            <div className="side-kv">
              <span className="k">provider</span><span className="v mono">{state.provider}</span>
              <span className="k">tokens</span><span className="v mono tnum">{(g.stream_tokens || 0).toLocaleString()}</span>
            </div>
          </div>
          <div className="side-section">
            <div className="side-section-title">피드백 컨텍스트 (Few-shot)</div>
            {ctx.length === 0 ? (
              <div className="side-empty">첫 세대 — 컨텍스트 없음</div>
            ) : (
              <ul className="side-list">
                {ctx.map((c, i) => (
                  <li key={i} className="mono" style={{ fontSize: 11 }}>{c}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="side-section">
            <div className="side-section-title">진행</div>
            <div className="gen-prog-row">
              <span className={`gen-prog-dot ${buyDone ? "done" : active === "buy" ? "active" : ""}`}></span>
              <span className="gen-prog-label">매수 조건식</span>
              <span className={`mono gen-prog-state ${buyDone ? "done" : ""}`}>{buyDone ? "✓" : active === "buy" ? "…" : ""}</span>
            </div>
            <div className="gen-prog-row">
              <span className={`gen-prog-dot ${sellDone ? "done" : active === "sell" ? "active" : ""}`}></span>
              <span className="gen-prog-label">매도 조건식</span>
              <span className={`mono gen-prog-state ${sellDone ? "done" : ""}`}>{sellDone ? "✓" : active === "sell" ? "…" : ""}</span>
            </div>
          </div>
        </div>

        {/* Right: streaming code */}
        <div className="gen-code-col">
          <div className="gen-code-header">
            <span className="mono" style={{ fontSize: 11, color: active === "sell" ? "var(--amber)" : "var(--teal)" }}>
              ●
            </span>
            <span style={{ fontSize: 11, color: "var(--ink-1)", letterSpacing: ".06em", textTransform: "uppercase" }}>
              {codeLabel}
            </span>
            <span className="mono" style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" }}>
              {(showCode || "").split("\n").length} lines · 스트리밍중
            </span>
          </div>
          <pre className="code-block stream" ref={codeRef}>
            {highlighted.map((row, i) => (
              <div key={i}>
                <span className="ln">{row.ln}</span>
                {row.parts.map((p, j) => (
                  <span key={j} className={p.cls}>{p.t}</span>
                ))}
              </div>
            ))}
            {/* blinking caret */}
            <span className="stream-caret blink">▌</span>
          </pre>
        </div>
      </div>
    </div>
  );
}

// --------- Backtesting view (uses LiveBacktestChart) ---------
function BacktestingView({ state }) {
  const equity = state.current_run?.equity || [];
  const baseline = 10_000_000;
  const last = equity[equity.length - 1];
  const lastPnl = last ? (last.value - baseline) : 0;
  const lastDD = state.current_run?.drawdown?.slice(-1)[0]?.value_pct ?? 0;
  const trades = state.current_run?.trades || [];

  return (
    <div className="bt-view">
      <div className="bt-summary-row">
        <SummaryCell label="현재 자본" value={`${last ? (last.value / 1_000_000).toFixed(2) : "10.00"} M`}
                     color={lastPnl >= 0 ? "var(--teal)" : "var(--red)"}
                     sub={`기준 10.00M`} />
        <SummaryCell label="순손익" value={`${lastPnl >= 0 ? "+" : "−"}${Math.abs(lastPnl).toLocaleString("ko-KR")}원`}
                     color={lastPnl >= 0 ? "var(--teal)" : "var(--red)"}
                     sub={`${((lastPnl / baseline) * 100).toFixed(2)}%`} />
        <SummaryCell label="실시간 낙폭" value={`${lastDD.toFixed(2)}%`}
                     color="var(--red)"
                     sub={`peak ${Math.max(0, ...state.current_run?.drawdown?.map(p => p.value_pct) || [0]).toFixed(2)}%`} />
        <SummaryCell label="누적 매매" value={trades.length}
                     sub={`매수 ${trades.filter(t => t.side === "buy").length} / 매도 ${trades.filter(t => t.side === "sell").length}`} />
      </div>
      {window.LiveBacktestChart ? (
        <div className="bt-chart-embed">
          <LiveBacktestChartInline state={state} />
        </div>
      ) : null}
    </div>
  );
}

function SummaryCell({ label, value, color, sub }) {
  return (
    <div className="summary-cell">
      <div className="summary-lbl">{label}</div>
      <div className="summary-val mono" style={{ color: color || "var(--ink-0)" }}>{value}</div>
      {sub && <div className="summary-sub mono">{sub}</div>}
    </div>
  );
}

// A leaner inline version of the live chart for the phase detail context
function LiveBacktestChartInline({ state }) {
  const equity = state.current_run?.equity || [];
  const drawdown = state.current_run?.drawdown || [];
  const trades = state.current_run?.trades || [];
  const baseline = 10_000_000;

  const W = 880, H = 200;
  const padL = 56, padR = 56, padT = 10, padB = 22;
  const innerH = H - padT - padB;
  const xMax = Math.max(60, equity.length ? equity[equity.length - 1].t : 60);
  // P2: 스케일·경로 수식은 engine.jsx 의 공유 _liveChartGeom 으로 위임(중복 제거, 픽셀 동일).
  //   인라인본은 자체 치수(H=200·여백)·xMax 공식·시각 셸(2눈금·범례없음·하드코딩색)을 그대로 유지.
  const { maxEq, minEq, ddMax, x, y, yDD, eqPath, eqAreaPath, ddAreaPath } = useMemo_ph(
    () => _liveChartGeom({ equity, drawdown, baseline, W, H, padL, padR, padT, padB, xMax }),
    [equity, drawdown, xMax]
  );

  return (
    <div className="live-chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="eq-grad-inline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#4cd6b3" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#4cd6b3" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="dd-grad-inline" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff6b6b" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#ff6b6b" stopOpacity="0" />
          </linearGradient>
        </defs>

        <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" />
        <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" />
        <line x1={W - padR} x2={W - padR} y1={padT} y2={padT + innerH} stroke="var(--line-2)" />

        <line x1={padL} x2={W - padR} y1={y(baseline)} y2={y(baseline)} className="zero-line" />
        <text className="chart-axis-text" x={padL - 6} y={y(baseline) + 3} textAnchor="end">
          {(baseline / 1_000_000).toFixed(1)}M
        </text>
        {[0.25, 0.5, 0.75].map((t, i) => {
          const v = minEq + (maxEq - minEq) * t;
          return (
            <g key={i}>
              <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} className="chart-grid-line" />
              <text className="chart-axis-text" x={padL - 6} y={y(v) + 3} textAnchor="end">
                {(v / 1_000_000).toFixed(2)}M
              </text>
            </g>
          );
        })}
        {[0.5, 1].map((t, i) => {
          const v = ddMax * t;
          return (
            <text key={i} className="chart-axis-text" x={W - padR + 6} y={yDD(v) + 3} fill="var(--red)" opacity="0.7">
              −{v.toFixed(1)}%
            </text>
          );
        })}

        {drawdown.length > 1 && (
          <path d={ddAreaPath} fill="url(#dd-grad-inline)" />
        )}
        {equity.length > 1 && (
          <>
            <path d={eqAreaPath} fill="url(#eq-grad-inline)" />
            <path d={eqPath} className="eq-line" />
          </>
        )}
        {trades.map((tr, i) => (
          <circle key={i} cx={x(tr.t)} cy={y(tr.price)} r="2.5"
                  className={tr.side === "buy" ? "trade-marker-buy" : "trade-marker-sell"}
                  opacity="0.85" />
        ))}

        <text className="chart-axis-text" x={padL} y={H - 6}>0m</text>
        <text className="chart-axis-text" x={W - padR} y={H - 6} textAnchor="end">{xMax}m</text>
      </svg>
      {equity.length === 0 && (
        <div className="chart-empty">백테스트 시작을 기다리는 중...</div>
      )}
    </div>
  );
}

// --------- Scoring view ---------
function ScoringView({ state }) {
  const metrics = state.current_run?.scoring?.metrics || [];
  const composite = state.current_run?.scoring?.composite;
  const targetFromConfig = 1.0; // could pass in

  return (
    <div className="score-view">
      <div className="score-formula">
        <span className="mono" style={{ color: "var(--ink-2)" }}>graded_score</span>
        <span className="mono" style={{ color: "var(--ink-3)" }}>=</span>
        <span className="mono" style={{ color: "var(--ink-1)" }}>
          Σ (metric<sub>i</sub> × weight<sub>i</sub>)
        </span>
        <span className="mono" style={{ marginLeft: "auto", color: "var(--ink-3)" }}>
          {metrics.length}/4 채점 완료
        </span>
      </div>

      <div className="score-metrics">
        {[0, 1, 2, 3].map(i => {
          const m = metrics[i];
          const ready = !!m;
          const v = m?.value ?? 0;
          const w = m?.weight ?? 0.25;
          const weighted = ready ? v * w : 0;
          const labels = ["손익 (profit factor)", "MDD 페널티", "거래수 적정성", "일관성 (sharpe-ish)"];
          const label = m?.label || labels[i];
          return (
            <div key={i} className={`score-metric ${ready ? "ready" : "pending"}`}>
              <div className="metric-row">
                <span className="metric-label">{label}</span>
                <span className="metric-weight">w={w.toFixed(2)}</span>
              </div>
              <div className="metric-bar-wrap">
                <div className="metric-bar">
                  <div className="metric-bar-fill"
                       style={{ width: `${ready ? Math.min(100, v * 100) : 0}%` }}></div>
                </div>
                <span className="metric-val mono">
                  {ready ? v.toFixed(3) : <span className="pulse-dot">…</span>}
                </span>
                <span className="metric-weighted mono">
                  → +{ready ? weighted.toFixed(3) : "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="score-composite">
        <div className="composite-label">composite (graded_score)</div>
        <div className="composite-val mono"
             style={{ color: composite != null ? (composite >= targetFromConfig ? "var(--teal)" : "var(--ink-0)") : "var(--ink-3)" }}>
          {composite != null ? composite.toFixed(3) : "—"}
        </div>
        {composite != null && composite >= targetFromConfig && (
          <span className="pill gate-pass">✓ 게이트 통과</span>
        )}
      </div>
    </div>
  );
}

// --------- Autopsy view ---------
function AutopsyView({ state }) {
  const a = state.current_run?.autopsy || {};
  const text = a.text_partial || "";
  const target = a.text_target || "";
  const ready = !!a.ready;

  return (
    <div className="autopsy-view">
      <div className="autopsy-header">
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".12em", textTransform: "uppercase" }}>
          AUTOPSY  ·  다음 세대 컨텍스트로 주입
        </span>
        <span className="mono" style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" }}>
          {text.length}/{target.length} chars
        </span>
      </div>
      <div className="autopsy-body">
        <span className="mono autopsy-text">{text || "..."}</span>
        {!ready && <span className="stream-caret blink">▌</span>}
      </div>
      <div className="autopsy-footnote">
        부검은 LLM이 매수/매도 코드의 백테스트 결과를 자연어로 요약한 것이며, 다음 세대 프롬프트의 few-shot 컨텍스트로 전달됩니다.
      </div>
    </div>
  );
}

function IdlePhaseView() {
  return (
    <div style={{
      padding: "28px 24px",
      color: "var(--ink-3)",
      textAlign: "center",
      fontSize: 12,
      fontFamily: "var(--mono)",
    }}>
      페이즈가 진행되면 단계별 상세가 여기에 표시됩니다
    </div>
  );
}

// =====================================================================
// ProcessFlowPanel — 5단계 프로세스 플로우 + 라이브 로그 패널.
//   current_step(-1~4): 0=생성 1=백테 2=채점 3=부검 4=반복.
//   구 current_state.json(current_step 미포함)은 phaseIndex() 폴백으로 하이라이트.
// =====================================================================
// FLOW_STEPS — 5단계 이산 프로세스. timingKey는 backend step_timings dict의 키
//   (loop.py _STEP_NAME_BY_INDEX와 일치: 0생성 1백테 2채점 3부검 4반복). 완료된 단계는
//   step_timings[timingKey]로 소요초 배지를 단다.
const FLOW_STEPS = [
  { label: "조건식", sub: "만들기", timingKey: "generate" },
  { label: "검증",   sub: "과거데이터", timingKey: "backtest" },
  { label: "점수",   sub: "적합도",    timingKey: "score" },
  { label: "원인",   sub: "실패요약",  timingKey: "autopsy" },
  { label: "개선",   sub: "다음세대",  timingKey: "iterate" },
];

const PROCESS_DEFAULT_ROWS = [
  {
    area: "Preset",
    value: "fast / research / promotion",
    detail: "fast=빠른 탐색, research=프롬프트·equity·evidence 보존 연구, promotion=동결 후보 승격 검토. 모두 점수는 advisory-only입니다.",
  },
  {
    area: "Tick 기본 연구",
    value: "09:00:00~09:28:00",
    detail: "Tick 후보 연구/promotion은 장초반 28분 opening window를 기본으로 봅니다.",
  },
  {
    area: "MIN 풀세션",
    value: "09:00~15:18/15:19",
    detail: "research/promotion MIN은 풀세션을 요구합니다. 15:18과 15:19는 DB 경계 후보로 표시하고 명시 검증합니다.",
  },
  {
    area: "백테스트 1회 제한",
    value: "최대 300초",
    detail: "bt_timeout 기본값입니다. warm run은 이보다 빨라야 하며, 과발화/비용 큰 매도식은 fail-fast 대상입니다.",
  },
  {
    area: "단계별 MDD gate",
    value: "fast 35% · research 25% · promotion 15%",
    detail: "설정 mdd_cap이 더 낮으면 더 엄격한 값이 적용됩니다. hard gate가 점수보다 우선합니다.",
  },
  {
    area: "거래 빈도/과매매",
    value: "일평균 ≥0.5 · softcap 150",
    detail: "과매매 자체는 금지가 아니라 soft penalty입니다. 빈도 부족은 hard/fitness 경계로 다룹니다.",
  },
  {
    area: "TPI",
    value: "매매성능지수 · gate 기본 OFF",
    detail: "TPI는 거래 품질/수익 효율을 보조로 보는 매매성능지수입니다. tpi_gate_enabled=false가 기본이며 승격권한을 만들지 않습니다.",
  },
  {
    area: "성과 점수 100점",
    value: "수익·MDD·Calmar·우상향·빈도·청산·안정성",
    detail: "후보 설명/정렬용 advisory score입니다. promotion/export/winner 선택권은 없습니다.",
  },
  {
    area: "생성품질 100점",
    value: "문법·변수다양성·니치·창의성·과발화·비용·매도구조",
    detail: "조건식 생성 품질을 설명하는 점수입니다. 성과를 보증하지 않고 hard gate를 대체하지 않습니다.",
  },
  {
    area: "Prompt / Equity 저장",
    value: "fast 선택 · research/promotion evidence",
    detail: "기본 토글은 OFF입니다. research/promotion 검토에서는 프롬프트·손익곡선 evidence가 없으면 blocker로 표시합니다.",
  },
  {
    area: "부검 hypothesis",
    value: "accepted/rejected/deferred/inconclusive",
    detail: "부검 가정은 다음 프롬프트 맥락으로 환류하되 advisory-only provenance를 유지합니다.",
  },
  {
    area: "인간 DB pattern cards",
    value: "조합 문법/창의성 전용",
    detail: "성과 복사·전체식 복사·임계값 복사는 금지합니다. few-shot은 구조 학습용으로만 씁니다.",
  },
  {
    area: "Transformer/ML",
    value: "추후 연구 과제",
    detail: "이번 작업 범위에서는 구현하지 않습니다. 별도 연구로 예측/파라미터화 가능성만 추적합니다.",
  },
];

// #64 — 초 단위 경과를 사람이 읽는 짧은 라벨로(예: 45s, 2m03s). 음수/NaN은 0s.
function fmtElapsedSec(sec) {
  const s = typeof sec === "number" && isFinite(sec) && sec > 0 ? Math.floor(sec) : 0;
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}m${String(r).padStart(2, "0")}s`;
}

// #64 — epoch(초) → 완료 시각 표기(로컬 HH:MM:SS). 0/미발행은 빈 문자열(표시 생략).
function fmtClockFromEpoch(epochSec) {
  if (!(typeof epochSec === "number" && isFinite(epochSec) && epochSec > 0)) return "";
  try {
    return new Date(epochSec * 1000).toLocaleTimeString("ko-KR", { hour12: false });
  } catch (e) {
    return "";
  }
}

function normalizeFlowStepIndex(rawStep, phase) {
  let value = Number(rawStep);
  if (!Number.isInteger(value)) value = phaseIndex(phase);
  if (!Number.isInteger(value) || value < 0) return -1;
  return Math.min(FLOW_STEPS.length - 1, value);
}

function flowStepStatus(index, currentStep) {
  if (!Number.isInteger(currentStep) || currentStep < 0) return "pending";
  if (currentStep > index) return "done";
  if (currentStep === index) return "active";
  return "pending";
}

// =====================================================================
// ProcessFlowDiagram — React Flow + Dagre 기반 프로세스 그래프.
//   props: currentStep(-1~4) · running · phaseElapsed(활성 라이브 경과초|null) ·
//          stepTimings(완료단계 소요초 dict, key=FLOW_STEPS[i].timingKey).
//   노드 status by index vs currentStep: done(teal) / active(amber pulse) / pending(dim).
//   Dagre가 좌→우 레이아웃을 계산하고, active path edge만 animated 처리한다.
// ============================================================================
function ProcessFlowDiagram({ currentStep, running, phaseElapsed, stepTimings }) {
  const graph = useMemo_ph(() => {
    const NODE_W = 172;
    const NODE_H = 86;
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: "LR", nodesep: 34, ranksep: 76, marginx: 22, marginy: 22 });

    FLOW_STEPS.forEach((step, index) => {
      dagreGraph.setNode(step.timingKey, { width: NODE_W, height: NODE_H, index });
    });
    FLOW_STEPS.slice(0, -1).forEach((step, index) => {
      dagreGraph.setEdge(step.timingKey, FLOW_STEPS[index + 1].timingKey);
    });
    dagre.layout(dagreGraph);

    const nodes = FLOW_STEPS.map((step, index) => {
      const status = flowStepStatus(index, currentStep);
      const doneSec = stepTimings ? stepTimings[step.timingKey] : undefined;
      let subText = step.sub;
      if (status === "active" && running && phaseElapsed != null) {
        subText = `경과 ${fmtElapsedSec(phaseElapsed)}`;
      } else if (status === "done" && typeof doneSec === "number" && doneSec >= 0) {
        subText = `완료 ${fmtElapsedSec(doneSec)}`;
      }
      const positioned = dagreGraph.node(step.timingKey);
      return {
        id: step.timingKey,
        type: "default",
        position: {
          x: positioned.x - NODE_W / 2,
          y: positioned.y - NODE_H / 2,
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        draggable: false,
        selectable: false,
        className: `stom-rf-node stom-rf-node-${status}`,
        data: {
          label: (
            <div className="stom-rf-node-label">
              <span className="stom-rf-node-step">{index + 1}</span>
              <b>{step.label}</b>
              <small>{subText}</small>
            </div>
          ),
        },
        style: { width: NODE_W, height: NODE_H },
        initialWidth: NODE_W,
        initialHeight: NODE_H,
      };
    });

    const edges = FLOW_STEPS.slice(0, -1).map((step, index) => {
      const next = FLOW_STEPS[index + 1];
      const lit = typeof currentStep === "number" && currentStep >= index + 1;
      return {
        id: `${step.timingKey}-${next.timingKey}`,
        source: step.timingKey,
        target: next.timingKey,
        type: "smoothstep",
        animated: lit && running,
        className: lit ? "stom-rf-edge-lit" : "stom-rf-edge",
        markerEnd: { type: MarkerType.ArrowClosed },
        label: lit ? "진행" : "",
      };
    });
    return { nodes, edges };
  }, [currentStep, running, phaseElapsed, stepTimings]);

  return (
    <div className="stom-rf-wrap" aria-label="React Flow Dagre 프로세스 그래프">
      <ReactFlow
        nodes={graph.nodes}
        edges={graph.edges}
        fitView
        fitViewOptions={{ padding: 0.12 }}
        minZoom={0.55}
        maxZoom={1.35}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnScroll={false}
        zoomOnScroll={false}
        preventScrolling={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={18} size={0.8} />
        <Controls showInteractive={false} position="bottom-right" />
      </ReactFlow>
    </div>
  );
}

function ProcessFlowPanel({ state }) {
  const currentStep = normalizeFlowStepIndex(state?.latest?.current_step, state?.latest?.phase);

  const logs = state?.latest?.recent_logs ?? [];
  const running = state?.status === "running" || state?.status === "stopping";

  // #64 진행시간 발행필드(0/미발행이면 경과 표시 생략 — 구 상태/하위호환 안전).
  const phaseStartedAt = state?.latest?.phase_started_at ?? 0;
  const genStartedAt = state?.latest?.gen_started_at ?? 0;
  const stepTimings = state?.latest?.step_timings ?? {};

  // 라이브 경과초는 1초마다 now를 갱신해 증가시킨다(running일 때만 — 정지/완료는 멈춤).
  const [nowSec, setNowSec] = useState_ph(() => Date.now() / 1000);
  useEffect_ph(() => {
    if (!running) return;
    const id = setInterval(() => setNowSec(Date.now() / 1000), 1000);
    return () => clearInterval(id);
  }, [running]);

  // 활성 단계 경과초(now - phase_started_at) — running이고 phase_started_at>0일 때만.
  const phaseElapsed = (running && phaseStartedAt > 0) ? (nowSec - phaseStartedAt) : null;
  // 세대 경과초(now - gen_started_at) — running이고 gen_started_at>0일 때만 라이브,
  //   완료(complete)면 완료시각(updated_at) 기준 정지값으로 보여준다.
  const genElapsedLive = (running && genStartedAt > 0) ? (nowSec - genStartedAt) : null;
  const completedAt = (!running && state?.status === "complete") ? (state?.updated_at ?? 0) : 0;
  const genElapsedDone = (completedAt > 0 && genStartedAt > 0)
    ? (completedAt - genStartedAt) : null;
  const completionClock = fmtClockFromEpoch(completedAt);

  // 진행률(정직): 연속% 금지 — 이산 (current_step+1)/5 단계.
  const totalSteps = FLOW_STEPS.length;
  const stepsDone = (typeof currentStep === "number" && currentStep >= 0)
    ? Math.min(totalSteps, currentStep + 1) : 0;
  const progressPct = (stepsDone / totalSteps) * 100;
  const activeStep = currentStep >= 0 ? FLOW_STEPS[currentStep] : null;
  const latestPhase = state?.latest?.phase || "—";
  const lastLog = logs.length ? logs[logs.length - 1] : "로그 대기중…";
  const flowMode = running ? "live" : (state?.run_id ? "archive/read-only" : "idle");
  const logWindow = logs.slice(-50);
  const progressLabel = stepsDone > 0 ? `${stepsDone}/${totalSteps}` : "0/5";
  const timingRows = FLOW_STEPS.map((step, index) => {
    const status = flowStepStatus(index, currentStep);
    const doneSec = stepTimings ? stepTimings[step.timingKey] : undefined;
    const elapsed = status === "active" && phaseElapsed != null
      ? fmtElapsedSec(phaseElapsed)
      : (typeof doneSec === "number" && doneSec >= 0 ? fmtElapsedSec(doneSec) : "—");
    return { ...step, index, status, elapsed };
  });

  // 로그 패널 자동 스크롤.
  const logRef = useRef_ph(null);
  useEffect_ph(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs.length]);

  return (
    <div className="panel" style={{ padding: "12px 14px" }}>
      <div className="panel-hd" style={{ marginBottom: 8 }}>
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          조건식 발굴 프로세스
        </div>
        {/* #64 — 세대 경과/완료 시각 + 이산 진행단계(N/5). running이면 라이브, complete면 정지. */}
        <span className="mono" style={{ marginLeft: "auto", fontSize: 10.5, color: "var(--ink-3)" }}>
          {genElapsedLive != null && (
            <span data-tip="현재 세대 경과 시간 (세대 시작 이후)">
              세대 경과 {fmtElapsedSec(genElapsedLive)}
            </span>
          )}
          {genElapsedLive == null && genElapsedDone != null && (
            <span data-tip="마지막 세대 소요 시간">
              세대 소요 {fmtElapsedSec(genElapsedDone)}
              {completionClock && ` · 완료 ${completionClock}`}
            </span>
          )}
          {(stepsDone > 0) && (
            <span style={{ marginLeft: 8 }}>· {stepsDone}/{totalSteps} 단계</span>
          )}
        </span>
      </div>
      {/* #64 — 이산 진행 막대(연속% 아님, (current_step+1)/5). 단계 미정(−1)이면 0%. */}
      <div className="process-progress-track" style={{
        height: 3, background: "var(--line-2)", borderRadius: 2, marginBottom: 8, overflow: "hidden",
      }}>
        <div style={{
          width: `${progressPct}%`, height: "100%",
          background: "var(--amber)", transition: "width .3s ease",
        }}></div>
      </div>
      <div className="process-live-strip">
        <span><b>현재 노드</b> {activeStep ? activeStep.label : "미정"}</span>
        <span><b>phase</b> {latestPhase}</span>
        <span><b>current_step</b> {currentStep >= 0 ? currentStep : "—"}</span>
        <span><b>최근 로그</b> {lastLog}</span>
      </div>
      <div className="process-flow-cards" aria-label="프로세스 흐름 계약 요약">
        <div>
          <span>데이터 출처</span>
          <b>실시간 상태</b>
          <small>현재 세대·현재 단계·백테스트 로그를 읽기 전용으로 표시</small>
        </div>
        <div>
          <span>상태 구분</span>
          <b>{flowMode}</b>
          <small>live/archive/idle을 구분해 옛 결과를 실시간으로 오해하지 않게 함</small>
        </div>
        <div>
          <span>현재 단계</span>
          <b>{activeStep ? `${currentStep + 1}. ${activeStep.label}` : "미정"}</b>
          <small>{phaseElapsed != null ? `현재 단계 경과 ${fmtElapsedSec(phaseElapsed)}` : "단계 경과 대기"}</small>
        </div>
        <div>
          <span>단계 진행</span>
          <b>{progressLabel}</b>
          <small>예측값이 아니라 실제 current_step 기준</small>
        </div>
        <div>
          <span>소요시간</span>
          <b>{timingRows.filter(row => row.elapsed !== "—").length}/{totalSteps}</b>
          <small>각 단계가 끝난 뒤 누적되는 실제 시간 표본</small>
        </div>
        <div>
          <span>로그</span>
          <b>{logs.length}</b>
          <small>엔진/백테스트 로그 최근 {logWindow.length}줄 자동 스크롤</small>
        </div>
      </div>
      {/* G004 — React Flow + Dagre 그래프. active path만 animated 처리해 시각적 생동감과 성능을 같이 지킨다. */}
      <ProcessFlowDiagram
        currentStep={currentStep}
        running={running}
        phaseElapsed={phaseElapsed}
        stepTimings={stepTimings}
      />
      <div className="process-explain-grid" aria-label="프로세스 쉬운 설명과 용어">
        <div>
          <b>한눈에 보는 흐름</b>
          <p>조건식을 만들고, 과거 데이터로 검증한 뒤, 점수와 실패 원인을 보고 다음 세대를 개선합니다.</p>
        </div>
        <div>
          <b>현재 세대</b>
          <p>지금 실행 중인 후보 묶음입니다. current_step이 바뀌면 그래프의 활성 노드와 로그가 같이 움직입니다.</p>
        </div>
        <div>
          <b>적합도</b>
          <p>수익·손실폭·거래 빈도 같은 기준을 합쳐 후보를 비교하는 점수입니다. 높을수록 다음 후보로 남기 쉽습니다.</p>
        </div>
        <details>
          <summary>예시 보기</summary>
          <p>검증 노드가 켜져 있으면 백테스트 엔진이 후보 조건식을 과거 데이터에 적용 중이라는 뜻입니다.</p>
        </details>
      </div>
      <div className="process-defaults-panel" aria-label="조건식 발굴 기본 설정과 게이트 표">
        <div className="process-defaults-head">
          <b>기본 설정 · 게이트 · 채점 기준</b>
          <small>사용자 협의 기준을 한 표로 고정합니다. 모든 점수는 설명/연구용이며 hard gate·evidence·인간 승인이 우선합니다.</small>
        </div>
        <div className="process-defaults-table-wrap">
          <table className="process-defaults-table">
            <thead>
              <tr>
                <th>구분</th>
                <th>기본값/정책</th>
                <th>설명</th>
              </tr>
            </thead>
            <tbody>
              {PROCESS_DEFAULT_ROWS.map(row => (
                <tr key={row.area}>
                  <td>{row.area}</td>
                  <td>{row.value}</td>
                  <td>{row.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="process-timing-grid" aria-label="프로세스 단계별 소요 시간">
        {timingRows.map(row => (
          <div key={row.timingKey} className={`process-timing-cell ${row.status}`} data-status={row.status}>
            <span className="process-timing-label">{row.index + 1}. {row.label}</span>
            <span className="process-timing-value">{row.elapsed}</span>
          </div>
        ))}
      </div>
      <div className="process-log-pane" ref={logRef}>
        {logWindow.length === 0
          ? <span className="process-log-empty">로그 대기중…</span>
          : logWindow.map((line, i) => <div key={i}>{line}</div>)
        }
      </div>
    </div>
  );
}

Object.assign(window, {
  PhaseTimeline,
  PhaseDetailPanel,
  ProcessFlowPanel,
  ProcessFlowDiagram,
  GenerationView, BacktestingView, ScoringView, AutopsyView,
  LiveBacktestChartInline,
  DemoBadge, LivePending,
  // R8 — phase 매핑 순수 함수/맵 노출(영/한 정규화). 정적·단위 검증 가능.
  phaseIndex, PHASES, LIVE_PHASE_INDEX,
  // #64 — 진행시간 포맷 순수 함수 + 단계 메타 노출(정적·단위 검증 가능).
  fmtElapsedSec, fmtClockFromEpoch, normalizeFlowStepIndex, flowStepStatus, FLOW_STEPS,
});

// Track Z (PR-1) — ESM dual-safe export.
//   The FLAGGED bundle path (STOM_BUNDLE=1) consumes these via `import` (real per-module
//   scope). The DEFAULT concat path (build-app.mjs ORDER) strips the line below before
//   esbuild transform (see build-app.mjs `_stripTopLevelExports`), so the legacy single-
//   scope classic script stays a no-op SyntaxError-free (Object.assign above still
//   publishes the FROZEN globals). KEEP this statement on ONE physical line — the concat
//   stripper matches a single-line `export { ... };`.
export { DemoBadge, LivePending, PhaseDetailPanel, PhaseTimeline, ProcessFlowPanel };