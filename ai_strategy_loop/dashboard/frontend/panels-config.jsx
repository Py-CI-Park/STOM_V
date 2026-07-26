/* Reusable small panels — config / strategy panels (split from panels.jsx for the 800-line cap).
   현재 세대(Live) · 활성 전략(코드/diff) · 활성 설정·토글 · GA 개체군 · 메타분석 누적학습 등
   "지금 무슨 전략/설정으로 돌고 있나"를 LIVE 상태에서 직접 렌더하는 패널 묶음. app.jsx 와
   panels.jsx(배럴)이 소비한다.

   stom-ui 전역(fmtTime 등)은 절대 import-변환하지 않는다(window 전역으로 공유). DemoBadge·
   isDemoSource 도 window 전역으로 소비한다. React 훅은 파일 고유 별칭(useState_pcf / …)으로
   destructure 한다(단일 번들 dup-globals 가드).
*/
const { useState: useState_pcf, useEffect: useEffect_pcf, useMemo: useMemo_pcf } = React;
const CONDITION_FETCH_TIMEOUT_MS = 10000;

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
      <div className="panel-bd" tabIndex="0" aria-label="현재 세대 상세">
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
  const [wrapCode, setWrapCode] = useState_pcf(false);
  const [codePayload, setCodePayload] = useState_pcf(null);
  const [diffPayload, setDiffPayload] = useState_pcf(null);
  const [codeFetchError, setCodeFetchError] = useState_pcf("");
  const [diffFetchError, setDiffFetchError] = useState_pcf("");
  const [copyStatus, setCopyStatus] = useState_pcf("");
  const active = useMemo_pcf(() => _activeStrategyFromState(state || {}), [state]);
  const generation = active.generation || {};
  const genNo = _activeStrategyGenNo(generation);
  const runId = state.run_id || "";
  const canFetch = Boolean(baseUrl && runId && genNo !== null && active.source !== "streaming_partial" && active.source !== "no_strategy");

  useEffect_pcf(() => {
    setCodePayload(null);
    setDiffPayload(null);
    setCodeFetchError("");
    setDiffFetchError("");
    if (!canFetch) return;
    let cancelled = false;
    const codeUrl = `${baseUrl}/strategy_code?run=${encodeURIComponent(runId)}&gen=${genNo}`;
    const diffUrl = `${baseUrl}/strategy_diff?run_id=${encodeURIComponent(runId)}&gen_no=${genNo}&base_gen=previous`;
    fetch(codeUrl, { signal: AbortSignal.timeout(CONDITION_FETCH_TIMEOUT_MS) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("strategy_code HTTP " + r.status)))
      .then(j => { if (!cancelled) setCodePayload(j); })
      .catch(e => { if (!cancelled) setCodeFetchError(String(e)); });
    fetch(diffUrl, { signal: AbortSignal.timeout(CONDITION_FETCH_TIMEOUT_MS) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("strategy_diff HTTP " + r.status)))
      .then(j => { if (!cancelled) setDiffPayload(j); })
      .catch(e => { if (!cancelled) setDiffFetchError(String(e)); });
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
  const copyCode = (label, code) => {
    if (!code) {
      setCopyStatus(`${label} 코드가 아직 없어 복사하지 못했습니다.`);
      return;
    }
    if (!(navigator.clipboard && typeof navigator.clipboard.writeText === "function")) {
      setCopyStatus("브라우저가 클립보드 복사를 지원하지 않아 복사하지 못했습니다.");
      return;
    }
    navigator.clipboard.writeText(code)
      .then(() => setCopyStatus(`${label} 코드를 복사했습니다.`))
      .catch(() => setCopyStatus(`${label} 코드 복사에 실패했습니다.`));
  };

  return (
    <div className="panel active-strategy-panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>현재 조건식 · 매수/매도</div>
        <span className="active-strategy-status mono">gen {genNo ?? "—"} · {codeStatus === "ok" ? "코드 수신" : codeStatus}</span>
      </div>
      <div className="panel-bd active-strategy-body">
        <div className="active-strategy-identity">
          <div className="v54-cond-names">
            <div className="v54-cond-name buy">
              <span className="k">매수 조건식</span>
              <b className="mono">{buyName || "생성 대기"}</b>
            </div>
            <div className="v54-cond-name sell">
              <span className="k">매도 조건식</span>
              <b className="mono">{sellName || "생성 대기"}</b>
            </div>
          </div>
          <span className="active-strategy-provenance mono">run {runId || "—"} · gen {genNo ?? "—"} · source {active.source} · diff {diffStatus}</span>
        </div>
        {codeFetchError && <div className="active-strategy-fetch-error mono">조건식 코드 조회 실패: {codeFetchError} · 10초 후 중단됨</div>}
        {!codeFetchError && diffFetchError && <div className="active-strategy-diff-warning mono">조건식 코드는 표시됨 · 조건식 변경 비교 지연: {diffFetchError}</div>}
        <div className={"active-strategy-code-columns" + (wrapCode ? " is-wrapped" : "")}>
          <div className="active-strategy-code-viewport buy">
            <div className="cap">매수 로직 · 전체 코드</div>
            <pre className="code-block">{buyCode || `대기: ${codeStatus}`}</pre>
          </div>
          <div className="active-strategy-code-viewport sell">
            <div className="cap">매도 로직 · 전체 코드</div>
            <pre className="code-block">{sellCode || `대기: ${codeStatus}`}</pre>
          </div>
        </div>
        <div className="active-strategy-actions">
          <button className="btn ghost sm" onClick={() => setWrapCode(value => !value)} aria-pressed={wrapCode}>
            줄바꿈 {wrapCode ? "해제" : "켜기"}
          </button>
          <button className="btn ghost sm" onClick={() => copyCode("매수", buyCode)}>매수 복사</button>
          <button className="btn ghost sm" onClick={() => copyCode("매도", sellCode)}>매도 복사</button>
          <button className="btn ghost sm" onClick={() => copyCode("매수·매도", [buyCode, sellCode].filter(Boolean).join("\n\n"))}>매수·매도 함께 복사</button>
          <button className="btn ghost sm" disabled={genNo === null || !onViewCode}
                  onClick={() => onViewCode && onViewCode(genNo)}>
            전체 코드 대화상자
          </button>
          <span className="active-strategy-copy-status mono" role="status" aria-live="polite">{copyStatus}</span>
        </div>
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
  min_trades: "최소 거래수(폴백)",
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

// ---- Meta-analysis panel (P4 메타분석 엔진) ----
// page_data.meta(누적 메타 인사이트: 통과 전략 공통 변수/개선 변경/실패 패턴)을
//   LIVE로 렌더한다. 없으면(데모 또는 미발행) 출처를 명시한다. M1 규약 준수.
function _metaDerivedFallbackAllowed(meta) {
  return !meta || meta.status === "missing" || meta.status === "pending";
}

function _metaAuthorityDetail(meta) {
  const reason = meta.reason || meta.error || meta.message || "사유 미발행";
  const lastNormal = meta.last_normal || meta.last_known_good || meta.last_success_at || meta.last_ok_at || "마지막 정상 정보 미발행";
  return { reason: String(reason), lastNormal: String(lastNormal) };
}

function _MetaAuthorityStatus({ meta }) {
  if (!meta || meta.status === "ok") return null;
  const detail = _metaAuthorityDetail(meta);
  return (
    <div className="mono" role="status" style={{ fontSize: 10.5, color: "var(--amber)", marginBottom: 8, lineHeight: 1.55 }}>
      정본 상태: {String(meta.status)} · 사유: {detail.reason} · 마지막 정상 정보: {detail.lastNormal}
    </div>
  );
}

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
        {_metaDerivedFallbackAllowed(meta) ? (
          // v5.6.1 — 폴백: 메타 미발행 시 세대 데이터에서 누적 학습 요약을 파생(빈 화면 금지).
          (() => {
            const gens = (Array.isArray(state.generations) ? state.generations : []).filter(g => g.gen_no >= 0);
            if (!gens.length) {
              return (
                <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
                  {isDemo ? "데모 모드 — 메타분석은 라이브 실행에서 누적 발행됩니다." : "세대 데이터 대기 — run 진행 시 누적 학습 요약이 표시됩니다."}
                </div>
              );
            }
            const scores = gens.map(g => Number(g.graded_score)).filter(Number.isFinite);
            const passN = gens.filter(g => g.gate_passed).length;
            const first = scores.length ? scores[0] : null;
            const bestS = scores.length ? Math.max(...scores) : null;
            const rows = [
              ["누적 세대", String(gens.length)],
              ["게이트 통과율", `${passN}/${gens.length} (${gens.length ? Math.round(passN / gens.length * 100) : 0}%)`],
              ["평균 score", scores.length ? (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2) : "—"],
              ["score 개선(첫→최고)", first != null && bestS != null ? `${first.toFixed(2)} → ${bestS.toFixed(2)}` : "—"],
              ["최근 5세대 평균", scores.length ? (scores.slice(-5).reduce((a, b) => a + b, 0) / Math.min(5, scores.length)).toFixed(2) : "—"],
            ];
            return (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6 }}>메타 발행 전 — 세대 누적 요약(파생)</div>
                {rows.map(([k, v]) => (
                  <div key={k} className="mono" style={{ display: "flex", justifyContent: "space-between", fontSize: 11.5, padding: "4px 0", borderBottom: "1px solid var(--line-1)" }}>
                    <span style={{ color: "var(--ink-2)" }}>{k}</span><b style={{ color: "var(--ink-0)" }}>{v}</b>
                  </div>
                ))}
              </div>
            );
          })()
        ) : (
          <div>
            <_MetaAuthorityStatus meta={meta} />
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

Object.assign(window, { CurrentGenPanel, ActiveStrategyPanel, ActiveConfigPanel, PopulationPanel, MetaPanel, CONDITION_FETCH_TIMEOUT_MS });

// Track Z — dual-safe ESM export (stripped by build-app.mjs in the concat path; kept by the bundle for real module scope). KEEP on ONE physical line.
export { CurrentGenPanel, ActiveStrategyPanel, ActiveConfigPanel, PopulationPanel, MetaPanel };
