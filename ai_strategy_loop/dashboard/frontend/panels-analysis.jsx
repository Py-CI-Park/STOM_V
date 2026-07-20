/* Reusable small panels — analysis panels (split from panels.jsx for the 800-line cap).
   세그먼트 부검 · 전략 계보(버전 경과) · holdout 졸업검사 · 비용/누적 · 피드백/부검 등
   세대 결과를 사후 분석해 LIVE로 렌더하는 패널 묶음. app.jsx 와 panels.jsx(배럴)이 소비한다.

   stom-ui 전역(fmtInt 등)은 절대 import-변환하지 않는다(window 전역으로 공유). DemoBadge·
   isDemoSource 도 window 전역으로 소비한다. React 훅은 파일 고유 별칭(useMemo_pan)으로
   destructure 한다(단일 번들 dup-globals 가드).
*/
const { useMemo: useMemo_pan } = React;

// ---- Cost / cumulative panel ----
function CostPanel({ state, cap = 50000 }) {
  const tokens = state.cumulative?.tokens ?? 0;
  const cost = state.cumulative?.cost_or_count ?? 0;
  const pct = Math.min(100, (tokens / cap) * 100);
  // v5.6.1 — 상세화: 세대당 평균·예상 완주 비용(풍부한 누적 정보).
  const gens = Array.isArray(state.generations) ? state.generations : [];
  const nGen = gens.length;
  const maxGen = Number(state.max_generations) || 0;
  const avgTok = nGen ? tokens / nGen : 0;
  const avgCost = nGen && typeof cost === "number" ? cost / nGen : 0;
  const projCost = maxGen && nGen && typeof cost === "number" ? (cost / nGen) * maxGen : null;
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>비용 · 누적</div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{nGen}세대 누적</span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div className="row-2" style={{ gap: 10 }}>
          <div className="stat">
            <span className="stat-label">누적 토큰</span>
            <span className="stat-value mono">{fmtInt(tokens)}</span>
          </div>
          <div className="stat">
            <span className="stat-label">비용 / Count</span>
            <span className="stat-value mono">${(typeof cost === "number" ? cost : 0).toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}</span>
          </div>
        </div>
        <div className="row-2" style={{ gap: 10 }}>
          <div className="stat">
            <span className="stat-label">세대당 평균 토큰</span>
            <span className="stat-value mono">{nGen ? fmtInt(Math.round(avgTok)) : "—"}</span>
          </div>
          <div className="stat">
            <span className="stat-label">세대당 평균 비용</span>
            <span className="stat-value mono">{nGen ? "$" + avgCost.toFixed(4) : "—"}</span>
          </div>
        </div>
        <div className="row-2" style={{ gap: 10 }}>
          <div className="stat">
            <span className="stat-label">예상 완주 비용({maxGen || "—"}세대)</span>
            <span className="stat-value mono">{projCost != null ? "$" + projCost.toFixed(4) : "—"}</span>
          </div>
          <div className="stat">
            <span className="stat-label">토큰 추세</span>
            <span className="stat-value mono">{nGen >= 2 ? (avgTok >= 1000 ? (avgTok / 1000).toFixed(1) + "k" : Math.round(avgTok)) + "/gen" : "—"}</span>
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
  // v5.6.1 — 상세화: 최근 10세대 부검/게이트 사유 전체 + LIVE 메시지.
  const history = useMemo_pan(() => {
    const items = [];
    if (state.latest?.message) {
      items.push({ kind: "latest", text: state.latest.message, gen: state.current_gen });
    }
    const lastGens = [...state.generations].slice(-10).reverse();
    for (const g of lastGens) {
      const reason = g.gate_reason && g.gate_reason !== "조건 충족" ? g.gate_reason : (g.reason || "");
      if (reason) items.push({ kind: "gen", text: `gen_${g.gen_no}: ${reason}`, gen: g.gen_no });
    }
    return items.slice(0, 12);
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

function _cdTime(value) {
  const raw = String(value == null ? "" : value).padStart(6, "0");
  if (raw.length < 6) return "—";
  return `${raw.slice(0, 2)}:${raw.slice(2, 4)}:${raw.slice(4, 6)}`;
}

function _cdScore(score) {
  const n = Number(score);
  return Number.isFinite(n) ? n.toFixed(1) : "—";
}

function _CdPill({ label, tone = "info", title }) {
  return <span className={`condition-discovery-pill ${tone}`} title={title}>{label}</span>;
}

function ConditionDiscoveryPanel({ state, wsStatus }) {
  const discovery = state.page_data?.condition_discovery;
  const scores = state.page_data?.advisory_scores;
  const feedback = state.page_data?.condition_feedback;
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  if (!discovery) {
    return (
      <div className="panel condition-discovery-panel">
        <div className="panel-hd">
          <div className="panel-hd-title">
            <span className="dot" style={{ background: "var(--teal)" }}></span>조건식 발굴 거버넌스
            {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
          </div>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>preset · hard gates · evidence</span>
        </div>
        <div className="panel-bd">
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — 조건식 발굴 정책/점수는 라이브 상태에서 발행됩니다."
              : "실시간 데이터 대기 — 세대 완료 시 condition_discovery page_data가 발행됩니다."}
          </div>
        </div>
      </div>
    );
  }

  const policy = discovery.policy || {};
  const gate = discovery.hard_gates || {};
  const mddGate = gate.mdd || {};
  const tradeGate = gate.minimum_daily_trades || {};
  const timeWindow = discovery.time_window || {};
  const evidenceRows = (discovery.evidence_health && discovery.evidence_health.components) || [];
  const perf = scores?.performance_score_100 || {};
  const quality = scores?.condition_quality_score_100 || {};
  const authority = scores?.authority_guard || {};
  const blockedBy = authority.blocked_by || [];
  const persistenceRows = (feedback?.persistence?.items) || [];
  const hypotheses = (feedback?.hypotheses?.items) || [];
  const patternCards = (feedback?.pattern_cards?.items) || [];
  const observability = discovery.research_observability || {};
  const modeAuthority = observability.mode_authority || {};
  const contextPackHealth = observability.context_pack_health || {};
  const branchTree = Array.isArray(observability.branch_tree) ? observability.branch_tree : [];
  const candidatePack = observability.candidate_pack || {};
  const analysisCards = observability.analysis_cards || {};
  const promptReceipts = observability.prompt_receipts || {};
  const promotionBlockers = observability.promotion_blockers || {};
  const contextFields = contextPackHealth.required_fields || [];
  const candidateFields = candidatePack.required_fields || [];
  const analysisFields = analysisCards.required_fields || [];
  const promptFields = promptReceipts.required_fields || [];
  const blockerItems = promotionBlockers.blockers || [];

  return (
    <div className="panel condition-discovery-panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>조건식 발굴 거버넌스
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {discovery.preset || "fast"} · 점수는 advisory-only
        </span>
      </div>
      <div className="panel-bd condition-discovery-body">
        <div className="condition-discovery-hero">
          <div>
            <span className="stat-label">preset</span>
            <b>{policy.label || discovery.preset}</b>
            <small>{policy.purpose || "조건식 발굴 기본 정책"}</small>
          </div>
          <div>
            <span className="stat-label">time window</span>
            <b>{timeWindow.timeframe || "—"} · {_cdTime(timeWindow.start_time)}~{_cdTime(timeWindow.end_time)}</b>
            <small>{timeWindow.notes || timeWindow.source || "window policy"}</small>
          </div>
          <div>
            <span className="stat-label">MDD gate</span>
            <b>{mddGate.cap ?? "—"}%</b>
            <small>preset cap {mddGate.preset_cap ?? "—"} · configured {mddGate.configured_cap ?? "—"}</small>
          </div>
          <div>
            <span className="stat-label">trade gate</span>
            <b>{tradeGate.value ?? "—"} / day</b>
            <small>{tradeGate.authority || "hard gate"}</small>
          </div>
        </div>

        <div className="condition-discovery-score-row" aria-label="100점 advisory score cards">
          <div className="condition-score-card">
            <span>성과 점수</span>
            <b>{_cdScore(perf.score)}</b>
            <small>{perf.scale || "0-100"} · promotion authority 없음</small>
          </div>
          <div className="condition-score-card">
            <span>생성품질 점수</span>
            <b>{_cdScore(quality.score)}</b>
            <small>{quality.scale || "0-100"} · 문법/다양성/비용/매도구조</small>
          </div>
          <div className="condition-score-card authority">
            <span>승격/Export</span>
            <b>{authority.promotion_review_ready ? "review-ready" : "blocked"}</b>
            <small>score_can_promote={String(authority.score_can_promote === true)}</small>
          </div>
        </div>

        {/* v5.4 L3 — 거버넌스 분리: 기술 상세는 접이식, 핵심(정책·게이트·점수)만 상시 노출 */}
        <details className="evo-group v54-gov-fold">
        <summary className="evo-group-summary"><div className="stom-section-label">연구 관찰성 · Research Pack 상세</div></summary>
        <div className="condition-discovery-grid research-observability-grid" aria-label="Research Pack Branch Tree">
          <section>
            <h4>Research Pack / Branch Tree</h4>
            <div className="condition-discovery-row">
              <span>mode authority</span>
              <b>{modeAuthority.generation_allowed === true ? "research generation allowed" : (modeAuthority.generation_allowed === false ? "zero-generation review" : "authority pending/blocked")}</b>
              <small>{modeAuthority.process || discovery.current_process?.code || "process"} · {modeAuthority.preset || discovery.preset}</small>
            </div>
            <div className="condition-discovery-note">
              context pack health: {contextPackHealth.status || "pending"} · budget≤{contextPackHealth.fail_closed_budget_tokens || 250000}
            </div>
            <div className="condition-discovery-pillrow">
              {contextFields.map(field => <_CdPill key={field} label={field} tone="info" />)}
            </div>
            {branchTree.length > 0 && (
              <ol className="condition-discovery-note" style={{ margin: "8px 0 0", paddingLeft: 18 }}>
                {branchTree.map(step => (
                  <li key={step.step}><b>{step.step}</b> → {step.output}</li>
                ))}
              </ol>
            )}
          </section>

          <section>
            <h4>Candidate pack · Analysis cards</h4>
            <div className="condition-discovery-row">
              <span>candidate pack</span>
              <b>{candidatePack.recommended_candidates || "2-3+"}</b>
              <small>min {candidatePack.min_candidates || 2} · fallback {candidatePack.fallback_source || "diagnostic fallback"}</small>
            </div>
            <div className="condition-discovery-pillrow">
              {candidateFields.map(field => <_CdPill key={field} label={field} tone="success" />)}
            </div>
            <div className="condition-discovery-row">
              <span>analysis cards</span>
              <b>{analysisCards.schema || "analysis_card_v2"}</b>
              <small>{analysisFields.join(" · ") || "root cause / segment contribution / insight score"}</small>
            </div>
          </section>

          <section>
            <h4>Prompt receipts · Fallback</h4>
            <div className="condition-discovery-row">
              <span>prompt receipts</span>
              <b>{promptReceipts.prompt_maturity_authority || "research_prompt_maturity_only"}</b>
              <small>{promptFields.join(" · ") || "downstream official backtest result required"}</small>
            </div>
            <div className="condition-discovery-note">
              fallback status: deterministic filter-only 후보는 diagnostic fallback으로만 표시되고 prompt maturity credit은 0입니다.
            </div>
          </section>

          <section>
            <h4>Promotion blockers</h4>
            <div className="condition-discovery-row">
              <span>promotion-review</span>
              <b>{promotionBlockers.generation_allowed === false ? "zero generation" : "research only"}</b>
              <small>{promotionBlockers.authority || "fresh/frozen holdout · OOS/WF · slippage advisory required"}</small>
            </div>
            <div className="condition-discovery-pillrow">
              {blockerItems.length === 0 ? (
                <_CdPill label="blockers pending" tone="info" />
              ) : blockerItems.map(blocker => <_CdPill key={blocker} label={blocker} tone="danger" />)}
            </div>
          </section>
        </div>
        </details>
        <details className="evo-group v54-gov-fold">
        <summary className="evo-group-summary"><div className="stom-section-label">증거 건전성 · 저장 · 부검 가설 상세</div></summary>

        <div className="condition-discovery-grid">
          <section>
            <h4>Evidence health</h4>
            <div className="condition-discovery-pillrow">
              {evidenceRows.map(row => (
                <_CdPill key={row.name}
                         label={`${row.name}:${row.status}`}
                         tone={row.blocker_reason ? "danger" : (row.status === "present" ? "success" : "info")}
                         title={row.blocker_reason || (row.required ? "required" : "optional")} />
              ))}
            </div>
            {blockedBy.length > 0 && (
              <div className="condition-discovery-note danger">
                authority blocked: {blockedBy.join(" · ")}
              </div>
            )}
          </section>

          <section>
            <h4>Prompt / Equity 저장</h4>
            {persistenceRows.length === 0 ? (
              <div className="condition-discovery-note">persistence rows pending</div>
            ) : persistenceRows.map(row => (
              <div className="condition-discovery-row" key={row.kind}>
                <span>{row.kind}</span>
                <b>{row.status}</b>
                <small>{row.count == null ? "count unavailable" : `${row.count} records`}</small>
              </div>
            ))}
          </section>

          <section>
            <h4>부검 hypothesis</h4>
            {hypotheses.length === 0 ? (
              <div className="condition-discovery-note">가정 환류 대기</div>
            ) : hypotheses.slice(0, 3).map(row => (
              <div className="condition-discovery-row" key={row.id}>
                <span>{row.status}</span>
                <b>{row.id}</b>
                <small>{row.hypothesis}</small>
              </div>
            ))}
          </section>

          <section>
            <h4>Human DB pattern cards</h4>
            <div className="condition-discovery-row">
              <span>cards</span>
              <b>{patternCards.length}</b>
              <small>{feedback?.pattern_cards?.authority || "creativity only"}</small>
            </div>
            <div className="condition-discovery-note">
              임계값·전체식·성과 복사는 anti-copy guard가 차단합니다.
            </div>
          </section>
        </div>
        </details>
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
          // v5.6.1 — 폴백: 발행 전에도 세대별 부검/게이트 사유를 파생 표시(빈 화면 금지).
          (() => {
            const gens = Array.isArray(state.generations) ? state.generations : [];
            const rows = gens.filter(g => (g.gate_reason && g.gate_reason !== "조건 충족") || g.reason).slice(-8).reverse();
            if (!rows.length) {
              return (
                <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
                  {isDemo ? "데모 모드 — 세그먼트 부검은 라이브 실행에서 발행됩니다."
                          : "부검 데이터 대기 — 운영 run 진행 시 세그먼트(시간대·시총) 부검이 발행됩니다."}
                </div>
              );
            }
            return (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6 }}>
                  세그먼트 부검 발행 전 — 세대별 부검 사유(파생)
                </div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {rows.map((g, i) => (
                    <li key={i} className="mono" style={{ fontSize: 11.5, color: "var(--ink-1)", padding: "4px 0", borderBottom: "1px solid var(--line-1)", lineHeight: 1.55 }}>
                      <b style={{ color: g.gate_passed ? "var(--teal)" : "var(--ink-2)" }}>gen_{String(g.gen_no).padStart(2, "0")}</b>
                      {" "}{String(g.gate_reason && g.gate_reason !== "조건 충족" ? g.gate_reason : g.reason)}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })()
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
          // v5.6.1 — 폴백: lineage 미발행 시 세대 흐름(파생 계보)을 표시(빈 화면 금지).
          (() => {
            const gens = (Array.isArray(state.generations) ? state.generations : []).filter(g => g.gen_no >= 0);
            if (!gens.length) {
              return (
                <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
                  {isDemo ? "데모 모드 — 전략 계보는 라이브 실행에서 발행됩니다." : "세대 데이터 대기 — run 시작 시 계보가 표시됩니다."}
                </div>
              );
            }
            const bestGen = state.best && state.best.gen;
            return (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6 }}>
                  계보 발행 전 — 세대 흐름(파생) · best gen_{bestGen != null ? bestGen : "—"}
                </div>
                <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
                  {gens.slice(-10).map((g, i) => (
                    <li key={i} className="mono" style={{ padding: "4px 0", borderBottom: "1px solid var(--line-1)", fontSize: 11.5, display: "flex", gap: 10 }}>
                      <b style={{ color: g.gen_no === bestGen ? "var(--violet)" : (g.gate_passed ? "var(--teal)" : "var(--ink-2)"), flex: "0 0 58px" }}>
                        gen_{String(g.gen_no).padStart(2, "0")}{g.gen_no === bestGen ? " ★" : g.gate_passed ? " ✓" : ""}
                      </b>
                      <span style={{ color: "var(--ink-1)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", minWidth: 0 }}>{g.buy_name || "—"}</span>
                      <span style={{ marginLeft: "auto", color: (g.graded_score ?? 0) > 0 ? "var(--teal)" : "var(--ink-3)" }}>
                        {typeof g.graded_score === "number" ? g.graded_score.toFixed(2) : "—"}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })()
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

Object.assign(window, { AutopsyPanel, LineagePanel, HoldoutPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel });

// Track Z — dual-safe ESM export (stripped by build-app.mjs in the concat path; kept by the bundle for real module scope). KEEP on ONE physical line.
export { AutopsyPanel, LineagePanel, HoldoutPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel };
