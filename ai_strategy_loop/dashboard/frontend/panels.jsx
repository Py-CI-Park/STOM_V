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
    // 데모 시뮬레이터(한국어) phase.
    "생성중": "var(--blue)",
    "백테스트중": "var(--amber)",
    "채점중": "var(--violet)",
    "완료": "var(--teal)",
    "대기중": "var(--ink-2)",
    "정지됨": "var(--ink-1)",
    "승인 완료": "var(--teal)",
    // R8 — LIVE(backend 영어) phase도 색을 매핑(이전엔 기본색으로만 표시됐다).
    "loop_start": "var(--blue)",
    "warm_prepare_start": "var(--blue)",
    "warm_prepare_done": "var(--blue)",
    "ga_init": "var(--blue)",
    "backtest_start": "var(--amber)",
    "ga_evaluate_start": "var(--amber)",
    "backtest_end": "var(--violet)",
    "generation_done": "var(--teal)",
    "ga_generation_done": "var(--teal)",
    "complete": "var(--teal)",
    "stopping": "var(--ink-1)",
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

// ---- Active config / toggles panel (R8) ----
// LoopState.active_config(루프가 적용한 주요 설정·5종 안전토글 스냅샷)를 LIVE로 렌더한다.
//   "지금 무슨 설정으로 돌고 있나"를 폼/상태가 아니라 실시간 상태에서 직접 보여준다.
//   active_config.toggles(켜진 bool 토글 이름 목록)로 토글을 강조한다. 없으면 안내만.
function _activeStrategyGenNo(item) {
  if (!item) return null;
  const raw = item.gen_no ?? item.gen;
  return typeof raw === "number" ? raw : null;
}

function _activeStrategyFromState(state) {
  const gens = Array.isArray(state.generations) ? state.generations : [];
  if (state.status === "complete" && _activeStrategyGenNo(state.winner) !== null) {
    return { source: "winner", generation: { ...state.winner, gen_no: _activeStrategyGenNo(state.winner) } };
  }
  if (_activeStrategyGenNo(state.best) !== null) {
    return { source: "best", generation: { ...state.best, gen_no: _activeStrategyGenNo(state.best) } };
  }
  if (gens.length > 0) {
    const latest = gens.slice().sort((a, b) => (_activeStrategyGenNo(b) ?? -1) - (_activeStrategyGenNo(a) ?? -1))[0];
    return { source: "latest_generation", generation: { ...latest, gen_no: _activeStrategyGenNo(latest) } };
  }
  const streaming = state.current_run?.generation || {};
  if (streaming.buy_code_partial || streaming.sell_code_partial) {
    return {
      source: "streaming_partial",
      generation: {
        gen_no: typeof state.current_gen === "number" ? state.current_gen : 0,
        buy_name: streaming.buy_name || "",
        sell_name: streaming.sell_name || "",
        buy_code: streaming.buy_code_partial || "",
        sell_code: streaming.sell_code_partial || "",
      },
    };
  }
  return { source: "no_strategy", generation: null };
}

function ActiveStrategyPanel({ state, baseUrl, onViewCode }) {
  const [expanded, setExpanded] = useState_p(false);
  const [codePayload, setCodePayload] = useState_p(null);
  const [diffPayload, setDiffPayload] = useState_p(null);
  const [fetchError, setFetchError] = useState_p("");
  const active = useMemo_p(() => _activeStrategyFromState(state || {}), [state]);
  const generation = active.generation || {};
  const genNo = _activeStrategyGenNo(generation);
  const runId = state.run_id || "";
  const canFetch = Boolean(baseUrl && runId && genNo !== null && active.source !== "streaming_partial" && active.source !== "no_strategy");

  useEffect_p(() => {
    setCodePayload(null);
    setDiffPayload(null);
    setFetchError("");
    if (!canFetch) return;
    let cancelled = false;
    const codeUrl = `${baseUrl}/strategy_code?run=${encodeURIComponent(runId)}&gen=${genNo}`;
    const diffUrl = `${baseUrl}/strategy_diff?run_id=${encodeURIComponent(runId)}&gen_no=${genNo}&base_gen=previous`;
    fetch(codeUrl, { signal: AbortSignal.timeout(2500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("strategy_code HTTP " + r.status)))
      .then(j => { if (!cancelled) setCodePayload(j); })
      .catch(e => { if (!cancelled) setFetchError(String(e)); });
    fetch(diffUrl, { signal: AbortSignal.timeout(2500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("strategy_diff HTTP " + r.status)))
      .then(j => { if (!cancelled) setDiffPayload(j); })
      .catch(e => { if (!cancelled) setFetchError(String(e)); });
    return () => { cancelled = true; };
  }, [baseUrl, runId, genNo, canFetch]);

  const buyName = codePayload?.buy_name || generation.buy_name || "";
  const sellName = codePayload?.sell_name || generation.sell_name || "";
  const buyCode = codePayload?.buy_code || generation.buy_code || "";
  const sellCode = codePayload?.sell_code || generation.sell_code || "";
  const codeStatus = active.source === "streaming_partial"
    ? "streaming_partial"
    : (codePayload?.code_status || (active.source === "no_strategy" ? "no_strategy" : "loading"));
  const diffStatus = diffPayload?.diff_status || (canFetch ? "loading" : "unavailable");
  const previewCode = [buyCode, sellCode].filter(Boolean).join("\n\n# sell\n");
  const previewLines = (previewCode || "").split("\n");
  const boundedPreview = previewLines.slice(0, expanded ? 80 : 10).join("\n");

  return (
    <div className="panel active-strategy-panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>Active Strategy</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          source={active.source}
        </span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
          <div className="stat">
            <span className="stat-label">buy_name</span>
            <span className="stat-sub mono">{buyName || "empty"}</span>
          </div>
          <div className="stat">
            <span className="stat-label">sell_name</span>
            <span className="stat-sub mono">{sellName || "empty"}</span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>run_id={runId || "none"}</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>gen_no={genNo ?? "none"}</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--teal)" }}>code_status={codeStatus}</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--amber)" }}>diff_status={diffStatus}</span>
        </div>
        {fetchError && (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>
            active strategy fetch error: {fetchError}
          </div>
        )}
        <pre className="code-block" style={{ maxHeight: 170, overflow: "auto", margin: 0 }}>
          {boundedPreview || `unavailable: ${codeStatus}`}
        </pre>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn ghost sm" onClick={() => setExpanded(!expanded)}>
            {expanded ? "collapse" : "expand"} preview
          </button>
          <button className="btn ghost sm" disabled={genNo === null || !onViewCode}
                  onClick={() => onViewCode && onViewCode(genNo)}>
            open full code
          </button>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", alignSelf: "center" }}>
            Previous Diff via /strategy_diff
          </span>
        </div>
      </div>
    </div>
  );
}

function ResearchCriteriaBanner({ state, baseUrl }) {
  const mode = state.active_config?.research_oos_mode || "disabled";
  const [payload, setPayload] = useState_p(null);
  const [error, setError] = useState_p("");

  useEffect_p(() => {
    if (!baseUrl) return;
    let cancelled = false;
    const url = `${baseUrl}/research_criteria?mode=${encodeURIComponent(mode)}`;
    fetch(url, { signal: AbortSignal.timeout(2500) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("research_criteria HTTP " + r.status)))
      .then(j => { if (!cancelled) { setPayload(j); setError(""); } })
      .catch(e => { if (!cancelled) setError(String(e)); });
    return () => { cancelled = true; };
  }, [baseUrl, mode]);

  const label = payload?.label || (mode === "disabled" ? "OOS disabled" : `OOS ${mode}`);
  const warning = payload?.warning || "research/exploration only; not proof of human-level or production readiness.";
  const explanation = payload?.explanation_ko || "OOS를 후보 탈락에 쓰지 않는 연구 탐색 상태입니다.";

  return (
    <div className="panel" data-testid="research-criteria-banner">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>Research Criteria</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--amber)" }}>
          research_oos_mode={mode}
        </span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span className="badge warn">{label}</span>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
            {warning}
          </span>
        </div>
        <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>
          {explanation}
        </div>
        {error && (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>
            research criteria route unavailable: {error}
          </div>
        )}
      </div>
    </div>
  );
}

function _fmtCfgVal(v) {
  if (v === true) return "ON";
  if (v === false) return "OFF";
  if (v == null) return "—";
  return String(v);
}

// 사람이 읽는 라벨(없으면 키 그대로). 키→한국어 매핑(가시화 보조).
const _CFG_LABELS = {
  dispersion_prompt_enabled: "분산매매 프롬프트",
  dispersion_enabled: "분산 적합도 보상",
  min_hold_symbols: "분산 기준(동시보유 하한)",
  target_daily_trades: "목표 일평균거래",
  require_liquidity_gate: "거래대금 게이트 강제",
  mdd_control_enabled: "MDD 제어 강화(매도)",
  evolution_mode: "진화 모드",
  winner_objective: "우승 목표",
  profit_weight: "수익 가중치",
  bt_engine_mode: "엔진 모드",
  bt_scope: "백테 스코프",
  bt_timeframe: "타임프레임",
  bt_refine_from_best: "best 점진 개선",
  freeze_buy_on_mdd_only: "MDD-only 매수 동결",
  bt_full_start: "전체 시작일",
  bt_full_end: "전체 종료일",
  bt_betting: "종목당 배팅",
  mdd_cap: "MDD 상한",
  min_trades: "최소 거래수",
  min_daily_trades: "일평균거래 하한",
  overtrade_softcap: "과매매 softcap",
  tpi_gate_enabled: "TPI 게이트",
  tpi_gate: "TPI 하한",
  exit_quality_enabled: "청산품질 보상",
  target_score: "목표 점수",
  max_generations: "최대 세대",
};

function ActiveConfigPanel({ state }) {
  const cfg = state.active_config || {};
  const toggleNames = new Set(cfg.toggles || []);
  // toggles 메타 키는 표에서 제외하고 나머지를 정렬해 보여준다.
  const entries = Object.keys(cfg)
    .filter(k => k !== "toggles")
    .map(k => [k, cfg[k]]);
  // 켜진 토글을 위로(강조), 나머지는 키 순서 유지.
  const onToggles = entries.filter(([k, v]) => toggleNames.has(k) && v === true);
  const others = entries.filter(([k, v]) => !(toggleNames.has(k) && v === true));

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>활성 설정 · 토글</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {entries.length > 0 ? `${entries.length}개 설정 · 켜진 토글 ${onToggles.length}` : "현재 적용 설정"}
        </span>
      </div>
      <div className="panel-bd" style={{ padding: entries.length === 0 ? 14 : 0 }}>
        {entries.length === 0 ? (
          <div style={{ color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            실시간 데이터 대기 — 루프 시작 시 적용된 설정·토글 스냅샷이 발행됩니다.
          </div>
        ) : (
          <div>
            {onToggles.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "10px 12px" }}>
                {onToggles.map(([k]) => (
                  <span key={k} className="mono" style={{
                    fontSize: 10.5, color: "var(--teal)", background: "rgba(76,214,179,0.10)",
                    border: "1px solid rgba(76,214,179,0.35)", borderRadius: 4, padding: "2px 7px",
                  }}>
                    {(_CFG_LABELS[k] || k)} · ON
                  </span>
                ))}
              </div>
            )}
            <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
              {others.map(([k, v], i) => {
                const isToggle = toggleNames.has(k);
                return (
                  <li key={k} style={{
                    display: "flex", justifyContent: "space-between", gap: 10,
                    padding: "6px 12px",
                    borderTop: i === 0 && onToggles.length > 0 ? "1px solid var(--line-1)" : "none",
                    borderBottom: i < others.length - 1 ? "1px solid var(--bg-2)" : "none",
                  }}>
                    <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
                      {_CFG_LABELS[k] || k}
                    </span>
                    <span className="mono" style={{
                      fontSize: 11.5,
                      color: isToggle ? (v === true ? "var(--teal)" : "var(--ink-3)") : "var(--ink-0)",
                    }}>
                      {_fmtCfgVal(v)}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
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

// ---- Segment autopsy panel (P1) ----
// page_data.autopsy(세그먼트 강화 부검 요약)를 LIVE로 렌더한다. backend가 발행하면
//   세그먼트/임계값 테이블을 보이고, 없으면(데모 또는 미발행) 출처를 명시한다.
//   M1 LIVE↔DEMO 규약 준수: 데모면 DEMO 배지, 라이브인데 미발행이면 "실시간 데이터 대기".
function _pct(x) { return (typeof x === "number" ? (x * 100).toFixed(0) : "—") + "%"; }
function _num(x) { return typeof x === "number" ? x.toFixed(2) : "—"; }

function _ThresholdCond(t) {
  if (t.operator === "between") {
    const lo = t.lower_bound == null ? "-∞" : _num(t.lower_bound);
    const hi = t.upper_bound == null ? "∞" : _num(t.upper_bound);
    return `${t.stom_var} ∈ [${lo}, ${hi}]`;
  }
  if (t.threshold != null) return `${t.stom_var} ${t.operator} ${_num(t.threshold)}`;
  return t.stom_var;
}

function _SegRows({ title, rows }) {
  if (!rows || rows.length === 0) return null;
  return (
    <div style={{ marginBottom: 10 }}>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>{title}</div>
      <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
        {rows.map((s, i) => (
          <li key={i} className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", padding: "3px 0", lineHeight: 1.5 }}>
            <span style={{ color: s.return_diff < 0 ? "var(--red)" : "var(--ink-1)" }}>{s.label}</span>
            {` · ${s.count}건 · 승률 ${_pct(s.win_rate)} · 평균 ${_num(s.avg_return)}% · 대비 ${s.return_diff >= 0 ? "+" : ""}${_num(s.return_diff)}%p`}
          </li>
        ))}
      </ul>
    </div>
  );
}

function AutopsyPanel({ state, wsStatus }) {
  const autopsy = state.page_data?.autopsy;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>세그먼트 부검
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          손실 집중 세그먼트 · 구체 임계값
        </span>
      </div>
      <div className="panel-bd">
        {!autopsy || autopsy.status !== "ok" ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — 세그먼트 부검은 라이브 실행에서 발행됩니다."
              : "실시간 데이터 대기 — 세대 완료 시 세그먼트 부검이 발행됩니다."}
          </div>
        ) : (
          <div>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", marginBottom: 10 }}>
              거래 {autopsy.trade_count}건 · 전체 승률 {_pct(autopsy.overall_win_rate)} · 평균 {_num(autopsy.overall_avg_return)}%
            </div>
            <_SegRows title="시간대 손실 집중" rows={autopsy.time_segments} />
            <_SegRows title="시총 밴드 손실 집중" rows={autopsy.market_cap_segments} />
            <_SegRows title="교차(시간대×시총)" rows={autopsy.cross_segments} />
            {autopsy.thresholds && autopsy.thresholds.length > 0 && (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>구체 임계값(손실 구간)</div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {autopsy.thresholds.map((t, i) => (
                    <li key={i} className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", padding: "3px 0", lineHeight: 1.5 }}>
                      {`${_ThresholdCond(t)} · ${t.count}건 · 승률 ${_pct(t.win_rate)} · 평균 ${_num(t.mean_return)}%`}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Population panel (P2 GA) ----
// page_data.population(개체별 graded/거래/MDD/수익/gate)을 LIVE로 렌더한다.
//   backend(GA 모드)가 발행하면 개체 테이블/막대를 보이고, 없으면(hillclimb 또는
//   미발행) 출처를 명시한다. M1 LIVE↔DEMO 규약 준수.
function _PopBar({ frac }) {
  const w = Math.max(0, Math.min(1, frac || 0)) * 100;
  return (
    <div style={{ background: "var(--bg-2)", borderRadius: 3, height: 6, overflow: "hidden" }}>
      <div style={{ width: `${w}%`, height: "100%", background: "var(--accent)" }}></div>
    </div>
  );
}

function PopulationPanel({ state, wsStatus }) {
  const pop = state.page_data?.population;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const members = (pop && pop.members) || [];
  const maxGraded = members.reduce((m, x) => Math.max(m, x.graded || 0), 0) || 1;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>GA Population
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {pop && pop.status === "ok"
            ? `K=${pop.k} · gate통과 ${pop.gate_passed_count} · 가드실패 ${pop.guardfail_count}`
            : "개체군 진화"}
        </span>
      </div>
      <div className="panel-bd">
        {!pop || pop.status !== "ok" || members.length === 0 ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — GA population은 라이브 실행(evolution_mode=ga)에서 발행됩니다."
              : "실시간 데이터 대기 — GA 모드 세대 평가 시 개체군이 발행됩니다(hillclimb 모드는 미발행)."}
          </div>
        ) : (
          <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {members.map((m, i) => (
              <li key={i} style={{ padding: "6px 0", borderBottom: "1px solid var(--bg-2)" }}>
                <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span>
                    <span style={{ color: m.gate_passed ? "var(--green)" : "var(--ink-2)" }}>●</span>
                    {` graded ${(m.graded ?? 0).toFixed(3)}`}
                    <span style={{ color: "var(--ink-3)" }}>{` [${m.origin}]`}</span>
                  </span>
                  <span style={{ color: "var(--ink-3)" }}>
                    {`${m.trade_count}건 · MDD ${(m.mdd ?? 0).toFixed(1)} · ${(m.profit ?? 0).toLocaleString()}`}
                  </span>
                </div>
                <_PopBar frac={(m.graded || 0) / maxGraded} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ---- Lineage panel (P3 연구 데이터 파이프라인) ----
// page_data.lineage(계보 트리/best_path/세대 노드)을 LIVE로 렌더한다.
//   backend가 발행하면 시드→best 경로와 세대별 부모/지표 diff를 보이고,
//   없으면(데모 또는 미발행) 출처를 명시한다. M1 LIVE↔DEMO 규약 준수.
function _lnNum(x) { return typeof x === "number" ? x.toFixed(2) : "—"; }

function LineagePanel({ state, wsStatus }) {
  const lineage = state.page_data?.lineage;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const nodes = (lineage && lineage.nodes) || [];
  const bestPath = (lineage && lineage.best_path) || [];
  const bestSet = new Set(bestPath);
  // 세대 번호 오름차순으로 보여준다(계보 흐름).
  const ordered = [...nodes].sort((a, b) => a.gen_no - b.gen_no);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>전략 계보 · 버전 경과
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {lineage && lineage.status === "ok"
            ? `시드→best 경로 ${bestPath.length}세대 · 총 ${lineage.node_count}세대`
            : "세대 계보/추이"}
        </span>
      </div>
      <div className="panel-bd">
        {!lineage || lineage.status !== "ok" || ordered.length === 0 ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — 전략 계보는 라이브 실행에서 발행됩니다."
              : "실시간 데이터 대기 — 세대 완료 시 계보가 발행됩니다."}
          </div>
        ) : (
          <div>
            <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", marginBottom: 8 }}>
              best 세대 = gen_{String(lineage.best_gen).padStart(2, "0")} · 경로 {bestPath.map(g => `g${g}`).join(" → ")}
            </div>
            <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
              {ordered.map((n, i) => (
                <li key={i} style={{ padding: "5px 0", borderBottom: "1px solid var(--bg-2)" }}>
                  <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", display: "flex", justifyContent: "space-between" }}>
                    <span>
                      <span style={{ color: bestSet.has(n.gen_no) ? "var(--teal)" : "var(--ink-2)" }}>
                        {bestSet.has(n.gen_no) ? "★" : "·"}
                      </span>
                      {` gen_${String(n.gen_no).padStart(2, "0")}`}
                      <span style={{ color: "var(--ink-3)" }}>
                        {n.parent_gen != null ? ` ← gen_${String(n.parent_gen).padStart(2, "0")}` : " (루트)"}
                      </span>
                    </span>
                    <span style={{ color: n.gate_passed ? "var(--green)" : "var(--ink-3)" }}>
                      {`graded ${_lnNum(n.graded_score)} · ${n.trade_count}건 · MDD ${_lnNum(n.mdd)}`}
                    </span>
                  </div>
                  {n.diff_from_parent && (
                    <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 2, paddingLeft: 14 }}>
                      {n.diff_from_parent}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Meta-analysis panel (P4 메타분석 엔진) ----
// page_data.meta(누적 메타 인사이트: 통과 전략 공통 변수/개선 변경/실패 패턴)을
//   LIVE로 렌더한다. 없으면(데모 또는 미발행) 출처를 명시한다. M1 규약 준수.
function MetaPanel({ state, wsStatus }) {
  const meta = state.page_data?.meta;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const commonVars = (meta && meta.common_pass_vars) || [];
  const changes = (meta && meta.improving_changes) || [];
  const fp = (meta && meta.failure_patterns) || {};

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>메타분석 · 누적 학습
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {meta && meta.status === "ok"
            ? `누적 ${meta.total_generations}세대 · 통과 ${meta.passing_count}`
            : "통과 전략 공통 조건"}
        </span>
      </div>
      <div className="panel-bd">
        {!meta || meta.status !== "ok" ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — 메타분석은 라이브 실행에서 누적 발행됩니다."
              : "실시간 데이터 대기 — run 종료 시 누적 메타 인사이트가 발행됩니다."}
          </div>
        ) : (
          <div>
            {commonVars.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>
                  통과 전략 공통 변수
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {commonVars.map((v, i) => (
                    <span key={i} className="mono" style={{
                      fontSize: 11, color: "var(--ink-0)", background: "var(--bg-2)",
                      borderRadius: 4, padding: "2px 7px",
                    }}>
                      {`${v[0]} ×${v[1]}`}
                    </span>
                  ))}
                </div>
              </div>
            )}
            {changes.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>
                  개선을 낳은 변경
                </div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {changes.map((c, i) => (
                    <li key={i} className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" }}>
                      {`· ${c[0]} (×${c[1]})`}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)" }}>
              {`실패 패턴 — 과매매 ${fp.overtrade ?? 0} · 0거래 ${fp.zero_trade ?? 0} · 고MDD ${fp.high_mdd ?? 0}`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Holdout 졸업검사 패널 (P5) ----
// page_data.holdout(과적합 방어: holdout 거래일 슬라이스 게이트 결과)을 LIVE로 렌더한다.
//   graduation_holdout=ON일 때만 backend가 holdout 섹션을 발행한다(OFF면 섹션 없음).
//   status: "ok"(판정함) | "insufficient"(holdout 거래 부족) | "no_holdout"(분할 불가)
//           | "error" | "off"(토글 OFF/이번 세대 train 미통과). passed: train 통과
//           후보가 holdout에서도 게이트를 통과했는지(졸업 인정 여부).
function _hoNum(x) { return typeof x === "number" ? x.toFixed(2) : "—"; }

function HoldoutPanel({ state, wsStatus }) {
  const holdout = state.page_data?.holdout;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  // 토글 OFF(또는 미발행)면 섹션 자체가 없다 → 패널은 안내만 표시.
  const hasData = holdout && holdout.status && holdout.status !== "off";
  const passed = holdout && holdout.passed === true;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>과적합 방어 · holdout 졸업검사
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        {hasData && (
          <span className="mono" style={{
            fontSize: 10.5, fontWeight: 600,
            color: passed ? "var(--good, #2ecc71)" : "var(--warn, #e0a030)",
          }}>
            {passed ? "holdout 통과 ✓" : "holdout 미통과"}
          </span>
        )}
      </div>
      <div className="panel-bd">
        {!hasData ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — holdout 졸업검사는 라이브 실행(graduation_holdout=ON)에서 발행됩니다."
              : "holdout 졸업검사 OFF 또는 대기 — train 게이트 통과 후보에 한해 holdout 판정이 발행됩니다."}
          </div>
        ) : (
          <div>
            <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" }}>
              {`train 거래 ${holdout.train_trade_count} · holdout 거래 ${holdout.trade_count}`}
            </div>
            <div className="mono" style={{ fontSize: 11.5, color: "var(--ink-0)", padding: "2px 0" }}>
              {`holdout MDD ${_hoNum(holdout.mdd_pct)}% · holdout 수익 ${typeof holdout.total_profit === "number" ? holdout.total_profit.toLocaleString() : "—"}원`}
            </div>
            <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", marginTop: 4 }}>
              {`판정: ${holdout.reason || holdout.status}`}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Run 비교 콘솔 (P6 운영·관찰) ----
// /runs 엔드포인트(loop_runs.db 직접, lineage.compare_runs)에서 여러 run의
//   지표/우승전략을 가져와 비교 테이블로 렌더한다. 데모/백엔드 미접속이면 안내만.
//   page_data(라이브 발행)가 아니라 REST 조회라 baseUrl로 직접 fetch 한다.
function _rcNum(x) { return typeof x === "number" ? x.toFixed(3) : "—"; }
function _rcTime(ts) {
  if (typeof ts !== "number") return "—";
  try { return new Date(ts * 1000).toLocaleString("ko-KR", { hour12: false }); }
  catch { return "—"; }
}

// ---- Export 상태 배너 (P6 final_approval 결과 노출) ----
// final_approval(승인 export) 제어의 마지막 결과(lastReply)를 표시한다. 게이트는
//   ApprovalDialog(이름+"승인" 입력)가 유지하므로 여기선 결과만 보여준다(자동 export 아님).
function ExportStatusBanner({ reply }) {
  if (!reply || reply.action !== "final_approval") return null;
  const ok = reply.status === "ok";
  const buyName = reply.buy && reply.buy.name;
  const sellName = reply.sell && reply.sell.name;
  return (
    <div style={{
      padding: "10px 14px", borderRadius: 6, marginBottom: 4, fontSize: 12.5,
      border: `1px solid ${ok ? "rgba(46,204,113,0.4)" : "rgba(224,90,90,0.4)"}`,
      background: ok ? "rgba(46,204,113,0.08)" : "rgba(224,90,90,0.08)",
      color: "var(--ink-0)",
    }}>
      {ok ? (
        <span>
          ✓ 운영 strategy.db로 export 완료
          {reply.demo ? " (데모)" : ""} — 매수 <span className="mono">{buyName || "—"}</span> · 매도 <span className="mono">{sellName || "—"}</span>
          {reply.dest_db && <span className="mono" style={{ color: "var(--ink-3)" }}>{` → ${reply.dest_db}`}</span>}
        </span>
      ) : (
        <span style={{ color: "var(--red)" }}>✗ export 실패 — {reply.message || "알 수 없는 오류"}</span>
      )}
    </div>
  );
}

Object.assign(window, { ConnBadge, StatusBadge, CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, AutopsyPanel, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ActiveConfigPanel, ActiveStrategyPanel, AutopsyPanel, ConnBadge, CostPanel, CurrentGenPanel, ExportStatusBanner, FeedbackPanel, HoldoutPanel, LineagePanel, MetaPanel, PopulationPanel, ResearchCriteriaBanner, StatusBadge };
