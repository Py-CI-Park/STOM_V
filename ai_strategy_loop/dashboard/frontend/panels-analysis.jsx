/* Reusable small panels — analysis panels (split from panels.jsx for the 800-line cap).
   세그먼트 부검 · 전략 계보(버전 경과) · holdout 졸업검사 · 비용/누적 · 피드백/부검 등
   세대 결과를 사후 분석해 LIVE로 렌더하는 패널 묶음. app.jsx 와 panels.jsx(배럴)이 소비한다.

   stom-ui 전역(fmtInt 등)은 절대 import-변환하지 않는다(window 전역으로 공유). DemoBadge·
   isDemoSource 도 window 전역으로 소비한다. React 훅은 파일 고유 별칭(useMemo_pan)으로
   destructure 한다(단일 번들 dup-globals 가드).
*/
const { useMemo: useMemo_pan, useState: useState_pan } = React;

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

// 쉬운 우리말을 앞에, 원어(로그·코드에서 보게 될 이름)를 작게 뒤에 붙인다.
//   사용자는 한국어만 읽어도 되고, 로그를 뒤질 때는 원어로 검색할 수 있다.
function _CdTerm({ ko, en }) {
  return (
    <span className="condition-discovery-term">
      {ko}{en ? <small>{en}</small> : null}
    </span>
  );
}

// 백엔드가 쓰는 상태 낱말을 그대로 노출하지 않는다 — 화면에서는 우리말이 정본이다.
const _CD_WORD = {
  present: "있음", missing: "없음", pending: "확인 중", ok: "정상",
  required: "필수", not_required: "불필요", optional: "선택",
  accepted: "맞았음", rejected: "빗나감", inconclusive: "판단 불가", untested: "확인 전",
  blocked: "막힘", allowed: "허용",
  advisory_process_only: "참고 절차 전용",
  requires_frozen_snapshot: "동결 스냅샷 필요",
  requires_hard_gates: "하드 게이트 통과 필요",
  requires_human_approval: "사람 승인 필요",
  human_approval_required: "사람 승인 필요",
  requires_complete_evidence_health: "증거 완비 필요",
  hard_gate_not_passed: "하드 게이트 미통과",
  research_prompt_maturity_only: "연구 성숙도 기록 전용",
};
function _cdWord(value) {
  if (value == null || value === "") return "미발행";
  const key = String(value).trim().toLowerCase();
  return _CD_WORD[key] || String(value);
}

// 한 줄 = 한 사실. label 은 쉬운 우리말, hint 는 왜/무엇을 뜻하는지.
function _CdFact({ ko, en, value, hint }) {
  return (
    <div className="condition-discovery-row">
      <_CdTerm ko={ko} en={en} />
      <b>{_cdWord(value)}</b>
      {hint ? <small>{hint}</small> : null}
    </div>
  );
}

// 세 영역(규칙·과정·증거)은 탭으로 감추지 않는다 — 한 화면에서 같이 읽어야 판단이 된다.
const _CD_SECTIONS = [
  { key: "policy", label: "① 규칙 — 어디까지 만들 수 있나", hint: "생성이 허용된 범위와, 넘으면 무조건 탈락하는 한도입니다." },
  { key: "observability", label: "② 과정 — 이 후보가 어떻게 나왔나", hint: "어떤 자료를 읽고, 어떤 경로로 갈라져, 몇 개의 후보가 만들어졌는지입니다." },
  { key: "evidence", label: "③ 증거 — 무엇이 승격을 막고 있나", hint: "저장된 근거가 충분한지, 지금 막혀 있는 이유가 무엇인지입니다." },
];

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
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>규칙 · 과정 · 증거</span>
        </div>
        <div className="panel-bd">
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {isDemo
              ? "데모 모드 — 조건식 발굴 규칙과 점수는 실제 연구가 돌 때 표시됩니다."
              : "실시간 데이터 대기 — 한 세대가 끝나면 규칙·과정·증거가 여기에 채워집니다."}
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
          {discovery.preset || "fast"} · 점수는 참고용(승격 권한 없음)
        </span>
      </div>
      <div className="panel-bd condition-discovery-body">
        <p className="condition-discovery-lede">
          이 패널은 <b>AI가 조건식을 만들 때 지켜야 하는 규칙</b>과 <b>지금 실전 승격이 막혀 있는 이유</b>를 한 화면에서 보여줍니다.
          점수는 연구 참고용이며, 점수만으로는 어떤 전략도 승격되지 않습니다.
        </p>
        <div className="condition-discovery-hero">
          <div>
            <span className="stat-label"><_CdTerm ko="탐색 정책" en="preset" /></span>
            <b>{policy.label || discovery.preset}</b>
            <small>{policy.purpose || "조건식 발굴 기본 정책"}</small>
          </div>
          <div>
            <span className="stat-label"><_CdTerm ko="연구 시간대" en="time window" /></span>
            <b>{timeWindow.timeframe || "—"} · {_cdTime(timeWindow.start_time)}~{_cdTime(timeWindow.end_time)}</b>
            <small>이 시간대 밖의 거래는 연구 대상이 아닙니다.</small>
          </div>
          <div>
            <span className="stat-label"><_CdTerm ko="최대 낙폭 한도" en="MDD gate" /></span>
            <b>{mddGate.cap ?? "—"}%</b>
            <small>이보다 더 깊게 물리면 무조건 탈락 · 기본 {mddGate.preset_cap ?? "—"} / 설정 {mddGate.configured_cap ?? "—"}</small>
          </div>
          <div>
            <span className="stat-label"><_CdTerm ko="하루 최소 거래" en="trade gate" /></span>
            <b>{tradeGate.value ?? "—"}건 / 일</b>
            <small>거래가 이보다 드물면 표본이 모자라 탈락합니다.</small>
          </div>
        </div>

        <div className="condition-discovery-score-row" aria-label="참고용 100점 점수 카드">
          <div className="condition-score-card">
            <span>성과 점수 <small>performance</small></span>
            <b>{_cdScore(perf.score)}</b>
            <small>{perf.scale || "0-100"}점 · 참고용(승격 권한 없음)</small>
          </div>
          <div className="condition-score-card">
            <span>생성 품질 점수 <small>condition quality</small></span>
            <b>{_cdScore(quality.score)}</b>
            <small>문법 · 다양성 · 비용 · 매도 구조</small>
          </div>
          <div className={"condition-score-card authority" + (authority.promotion_review_ready ? "" : " blocked")}>
            <span>실전 승격 <small>promotion / export</small></span>
            <b>{authority.promotion_review_ready ? "사람 검토 가능" : "막힘"}</b>
            <small>{authority.score_can_promote === true ? "점수로 승격 가능" : "점수만으로는 승격 불가"}</small>
          </div>
        </div>

        <div className="condition-discovery-board">
          <section className="condition-discovery-block" aria-label={_CD_SECTIONS[0].label}>
            <h4>{_CD_SECTIONS[0].label}</h4>
            <p className="condition-discovery-tab-intro">{_CD_SECTIONS[0].hint}</p>
            <_CdFact ko="생성 권한" en="generation authority"
                     value={modeAuthority.generation_allowed === true
                       ? "연구용 생성 허용"
                       : (modeAuthority.generation_allowed === false ? "생성 금지 · 검토 전용" : "권한 확인 중")}
                     hint={`${modeAuthority.process || discovery.current_process?.code || "process"} · ${modeAuthority.preset || discovery.preset}`} />
            {/* v5.13.0 — 낙폭 한도·최소 거래는 상단 카드와 중복이라 문장 하나로 줄였다(B1). */}
            <div className="condition-discovery-note">
              낙폭 한도 <b>{mddGate.cap ?? "—"}%</b> · 하루 최소 거래 <b>{tradeGate.value ?? "—"}건</b> —
              위 카드의 값이 정본이며, 이 두 한도는 점수로 상쇄되지 않습니다.
            </div>
          </section>

          <section className="condition-discovery-block" aria-label={_CD_SECTIONS[1].label}>
            <h4>{_CD_SECTIONS[1].label}</h4>
            <p className="condition-discovery-tab-intro">{_CD_SECTIONS[1].hint}</p>
            <_CdFact ko="연구 자료 묶음 상태" en="context pack"
                     value={contextPackHealth.status || "확인 중"}
                     hint={`읽는 자료 토큰 상한 ${(contextPackHealth.fail_closed_budget_tokens || 250000).toLocaleString()} — 넘으면 생성을 멈춥니다.`} />
            {/* v5.13.0 — 원어 필드명 나열은 접어 둔다(B1: 글자 과다). 필요할 때만 펼쳐 본다. */}
            {contextFields.length > 0 && (
              <details className="condition-discovery-fields">
                <summary>생성 전 필수 자료 {contextFields.length}개 펼쳐 보기</summary>
                <div className="condition-discovery-pillrow">
                  {contextFields.map(field => <_CdPill key={field} label={field} tone="info" title="생성 전에 반드시 채워져야 하는 자료 항목" />)}
                </div>
              </details>
            )}
            {branchTree.length > 0 && (
              <ol className="condition-discovery-note condition-discovery-branch-tree">
                {branchTree.map(step => <li key={step.step}><b>{step.step}</b> → {step.output}</li>)}
              </ol>
            )}
            <_CdFact ko="후보 묶음" en="candidate pack" value={`${candidatePack.recommended_candidates || "2-3+"}개 권장`}
                     hint={`최소 ${candidatePack.min_candidates || 2}개 · 부족하면 ${candidatePack.fallback_source || "진단용 대체 후보"}`} />
            {candidateFields.length > 0 && (
              <details className="condition-discovery-fields">
                <summary>후보별 필수 항목 {candidateFields.length}개 펼쳐 보기</summary>
                <div className="condition-discovery-pillrow">
                  {candidateFields.map(field => <_CdPill key={field} label={field} tone="success" title="후보마다 채워져야 하는 항목" />)}
                </div>
              </details>
            )}
            <_CdFact ko="분석 카드 형식" en="analysis cards" value={analysisCards.schema || "analysis_card_v2"}
                     hint={analysisFields.join(" · ") || "원인 · 구간 기여 · 인사이트 점수"} />
            <_CdFact ko="프롬프트 기록" en="prompt receipts"
                     value={promptReceipts.prompt_maturity_authority || "연구 성숙도 기록 전용"}
                     hint={promptFields.join(" · ") || "실제 승격은 공식 백테스트 결과가 있어야 합니다."} />
            <div className="condition-discovery-note">
              규칙만으로 걸러낸 후보는 <b>진단용 대체 후보</b>로만 표시되고 성숙도 점수를 받지 못합니다.
            </div>
          </section>

          <section className="condition-discovery-block" aria-label={_CD_SECTIONS[2].label}>
            <h4>{_CD_SECTIONS[2].label}</h4>
            <p className="condition-discovery-tab-intro">{_CD_SECTIONS[2].hint}</p>
            <_CdFact ko="승격 단계" en="promotion review"
                     value={promotionBlockers.generation_allowed === false ? "생성 금지 상태" : "연구 단계"}
                     hint="실전 승격에는 신규·동결 홀드아웃, OOS/전진분석, 슬리피지 참고치, 사람 승인이 모두 필요합니다." />
            <div className="condition-discovery-pillrow">
              {blockerItems.length === 0
                ? <_CdPill label="막는 항목 집계 중" tone="info" />
                : blockerItems.map(blocker => <_CdPill key={blocker} label={_cdWord(blocker)} tone="danger" title={blocker + " — 이 항목이 채워질 때까지 승격이 막힙니다."} />)}
            </div>
            <div className="condition-discovery-subhead">증거 상태 <small>evidence health</small></div>
            <div className="condition-discovery-pillrow">
              {evidenceRows.length === 0
                ? <_CdPill label="증거 집계 대기" tone="info" />
                : evidenceRows.map(row => (
                  <_CdPill key={row.name} label={`${row.name} · ${_cdWord(row.status)}`}
                           tone={row.blocker_reason ? "danger" : (row.status === "present" ? "success" : "info")}
                           title={row.blocker_reason || (row.required ? "필수 증거" : "선택 증거")} />
                ))}
            </div>
            {blockedBy.length > 0 && (
              <div className="condition-discovery-note danger" title={blockedBy.join(" · ")}>
                지금 막고 있는 것: {blockedBy.map(_cdWord).join(" · ")}
              </div>
            )}
            <div className="condition-discovery-subhead">저장 기록 <small>persistence</small></div>
            {persistenceRows.length === 0
              ? <div className="condition-discovery-note">저장 기록 집계 대기</div>
              : persistenceRows.map(row => (
                <_CdFact key={row.kind} ko={row.kind} value={row.status}
                         hint={row.count == null ? "건수 미발행" : `${row.count}건 저장됨`} />
              ))}
            <div className="condition-discovery-subhead">부검이 세운 가정 <small>hypothesis</small></div>
            {hypotheses.length === 0
              ? <div className="condition-discovery-note">아직 환류된 가정이 없습니다.</div>
              : hypotheses.slice(0, 3).map(row => (
                <_CdFact key={row.id} ko={row.id} value={row.status} hint={row.hypothesis} />
              ))}
            <_CdFact ko="사람 매매 패턴 카드" en="human pattern cards" value={`${patternCards.length}장`}
                     hint="아이디어 참고용입니다. 임계값·전체식·성과 복사는 차단됩니다." />
          </section>
        </div>
      </div>
    </div>
  );
}

// ---- Segment autopsy panel (P1) ----
// page_data.autopsy(세그먼트 강화 부검 요약)를 LIVE로 렌더한다. backend가 발행하면
//   세그먼트/임계값 테이블을 보이고, 없으면(데모 또는 미발행) 출처를 명시한다.
//   M1 LIVE↔DEMO 규약 준수: 데모면 DEMO 배지, 라이브인데 미발행이면 "실시간 데이터 대기".
function _pct(x) { return typeof x === "number" && Number.isFinite(x) ? (x * 100).toFixed(0) + "%" : "미발행"; }
function _num(x) { return typeof x === "number" && Number.isFinite(x) ? x.toFixed(2) : "미발행"; }

function _ThresholdCond(t) {
  if (!t || typeof t !== "object" || Array.isArray(t)) return "임계값 형식 불완전";
  const variable = typeof t.stom_var === "string" && t.stom_var ? t.stom_var : "변수 미발행";
  if (t.operator === "between") {
    const lo = t.lower_bound == null ? "-∞" : _num(t.lower_bound);
    const hi = t.upper_bound == null ? "∞" : _num(t.upper_bound);
    return `${variable} ∈ [${lo}, ${hi}]`;
  }
  if (typeof t.operator === "string" && t.threshold != null) return `${variable} ${t.operator} ${_num(t.threshold)}`;
  return variable;
}

// 부검은 "어디서 얼마나 잃었는가"를 한눈에 보여줘야 다음 조건식 수정으로 이어진다.
//   숫자만 늘어놓으면 어떤 구간이 더 나쁜지 비교가 안 되므로 막대 길이로 대비를 보인다.
function _segDiff(row) {
  return row && typeof row.return_diff === "number" && Number.isFinite(row.return_diff) ? row.return_diff : null;
}

function _SegRows({ title, rows, limit = 6 }) {
  if (!Array.isArray(rows) || rows.length === 0) return null;
  const valid = rows.filter(r => r && typeof r === "object" && !Array.isArray(r));
  const broken = rows.length - valid.length;
  // 최악(대비가 가장 낮은) 구간부터 — 고쳐야 할 순서와 화면 순서를 일치시킨다.
  const ordered = valid.slice().sort((a, b) => (_segDiff(a) ?? 0) - (_segDiff(b) ?? 0)).slice(0, limit);
  const scale = Math.max(1e-9, ...ordered.map(r => Math.abs(_segDiff(r) ?? 0)));
  return (
    <div className="autopsy-seg-group">
      <div className="autopsy-seg-title">{title}</div>
      <ul className="autopsy-seg-list">
        {ordered.map((s, i) => {
          const diff = _segDiff(s);
          const negative = diff != null && diff < 0;
          const width = diff == null ? 0 : Math.min(100, (Math.abs(diff) / scale) * 100);
          return (
            <li key={i} className={"autopsy-seg-row" + (negative ? " negative" : "")}>
              <span className="autopsy-seg-label">{typeof s.label === "string" ? s.label : "라벨 미발행"}</span>
              <i className="autopsy-seg-bar" aria-hidden="true"><b style={{ width: width + "%" }}></b></i>
              <b className="autopsy-seg-diff">{diff == null ? "미발행" : `${diff >= 0 ? "+" : ""}${_num(diff)}%p`}</b>
              <small className="autopsy-seg-meta">
                {typeof s.count === "number" ? `${s.count}건` : "건수 미발행"} · 승률 {_pct(s.win_rate)} ·
                평균 {typeof s.avg_return === "number" && Number.isFinite(s.avg_return) ? `${_num(s.avg_return)}%` : "미발행"}
              </small>
            </li>
          );
        })}
      </ul>
      {broken > 0 && <div className="autopsy-seg-note">형식이 불완전한 구간 {broken}건은 표시하지 않았습니다.</div>}
    </div>
  );
}

function _autopsyAvailability(data) {
  if (!data) return "부검 데이터 미발행";
  if (typeof data !== "object" || Array.isArray(data)) return "부검 데이터 형식 불완전";
  if (data.status === "missing") return "부검 데이터 미발행";
  if (data.status === "pending") return "부검 데이터 대기";
  return null;
}

function _authorityDetail(data) {
  const reason = data.reason || data.error || data.message || "사유 미발행";
  const lastNormal = data.last_normal || data.last_known_good || data.last_success_at || data.last_ok_at || "마지막 정상 정보 미발행";
  return { reason: String(reason), lastNormal: String(lastNormal) };
}

function _AuthorityStatus({ data }) {
  if (!data || data.status === "ok") return null;
  const detail = _authorityDetail(data);
  return (
    <div className="mono" role="status" style={{ fontSize: 10.5, color: "var(--amber)", marginBottom: 8, lineHeight: 1.55 }}>
      정본 상태: {String(data.status)} · 사유: {detail.reason} · 마지막 정상 정보: {detail.lastNormal}
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
          어디서 잃었는가 · 다음 조건식이 고칠 지점
        </span>
      </div>
      <div className="panel-bd">
        {_autopsyAvailability(autopsy) ? (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }}>
            {_autopsyAvailability(autopsy)}
          </div>
        ) : (
          <div>
            <_AuthorityStatus data={autopsy} />
            <p className="v59-section-intro" style={{ marginTop: 0 }}>
              막대는 <b>전체 평균 대비 얼마나 더 나빴는지</b>(%p)입니다. 길수록 손실이 그 구간에 몰려 있다는 뜻이고,
              다음 세대 조건식은 보통 여기부터 손봅니다.
            </p>
            <div className="autopsy-kpis">
              <div><span>거래</span><b>{typeof autopsy.trade_count === "number" ? `${autopsy.trade_count}건` : "미발행"}</b></div>
              <div><span>전체 승률</span><b>{_pct(autopsy.overall_win_rate)}</b></div>
              <div><span>평균 수익률</span><b>{_num(autopsy.overall_avg_return)}%</b></div>
            </div>
            <_SegRows title="시간대별 — 언제 잃었나" rows={autopsy.time_segments} />
            <_SegRows title="시가총액 밴드별 — 어떤 종목에서 잃었나" rows={autopsy.market_cap_segments} />
            <_SegRows title="시간대 × 시총 교차 — 가장 좁힌 구간" rows={autopsy.cross_segments} />
            {Array.isArray(autopsy.thresholds) && autopsy.thresholds.length > 0 ? (
              <div className="autopsy-seg-group">
                <div className="autopsy-seg-title">바로 쓸 수 있는 임계값 — 이 조건이면 손실 구간</div>
                <ul className="autopsy-threshold-list">
                  {autopsy.thresholds.map((t, i) => (
                    <li key={i}>
                      <b className="mono">{_ThresholdCond(t)}</b>
                      <small>
                        {typeof t?.count === "number" ? `${t.count}건` : "건수 미발행"} · 승률 {_pct(t?.win_rate)} ·
                        평균 {typeof t?.mean_return === "number" && Number.isFinite(t.mean_return) ? `${_num(t.mean_return)}%` : "미발행"}
                      </small>
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="autopsy-seg-note">아직 임계값이 발행되지 않았습니다.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// 1단계(생성)에서도 "무엇을 고치려는가"의 근거를 볼 수 있어야 한다.
//   전체 부검은 3단계에 그대로 남고, 여기서는 최악 구간 3개만 요약한다.
function AutopsyFocusCard({ state, onOpenAutopsy }) {
  const autopsy = state.page_data?.autopsy;
  const unavailable = _autopsyAvailability(autopsy);
  const pool = unavailable
    ? []
    : []
      .concat(Array.isArray(autopsy.cross_segments) ? autopsy.cross_segments : [])
      .concat(Array.isArray(autopsy.time_segments) ? autopsy.time_segments : [])
      .concat(Array.isArray(autopsy.market_cap_segments) ? autopsy.market_cap_segments : [])
      .filter(r => r && typeof r === "object" && _segDiff(r) != null && _segDiff(r) < 0);
  const worst = pool.sort((a, b) => _segDiff(a) - _segDiff(b)).slice(0, 3);
  const scale = Math.max(1e-9, ...worst.map(r => Math.abs(_segDiff(r))));

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--red)" }}></span>직전 세대가 잃은 곳 · 요약</div>
        {typeof onOpenAutopsy === "function" && (
          <button className="btn ghost sm" onClick={onOpenAutopsy} title="채점·부검 단계에서 전체 부검을 봅니다">전체 부검 보기</button>
        )}
      </div>
      <div className="panel-bd">
        {unavailable || worst.length === 0 ? (
          <div className="research-empty">
            {unavailable || "직전 세대에서 평균보다 뚜렷하게 나빴던 구간이 없습니다."}
          </div>
        ) : (
          <>
            <p className="v59-section-intro" style={{ marginTop: 0 }}>
              이번 세대 조건식은 아래 구간을 피하거나 조건을 좁히는 방향으로 만들어집니다.
            </p>
            <ul className="autopsy-seg-list">
              {worst.map((s, i) => {
                const diff = _segDiff(s);
                return (
                  <li key={i} className="autopsy-seg-row negative">
                    <span className="autopsy-seg-label">{typeof s.label === "string" ? s.label : "라벨 미발행"}</span>
                    <i className="autopsy-seg-bar" aria-hidden="true"><b style={{ width: Math.min(100, (Math.abs(diff) / scale) * 100) + "%" }}></b></i>
                    <b className="autopsy-seg-diff">{_num(diff)}%p</b>
                    <small className="autopsy-seg-meta">
                      {typeof s.count === "number" ? `${s.count}건` : "건수 미발행"} · 승률 {_pct(s.win_rate)}
                    </small>
                  </li>
                );
              })}
            </ul>
          </>
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
        {lineage && lineage.status === "ok" ? (
          <div>
            <_AuthorityStatus data={lineage} />
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
        ) : (
          <div style={{ padding: 14, color: "var(--ink-3)", fontSize: 12, lineHeight: 1.6 }} role="status">
            {isDemo
              ? "데모 모드 — 전략 계보는 라이브 실행에서 발행됩니다."
              : `전략 계보 미발행 — ${lineage && lineage.status ? lineage.status : "authoritative lineage 없음"}`}
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

Object.assign(window, { AutopsyPanel, AutopsyFocusCard, LineagePanel, HoldoutPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel });

// Track Z — dual-safe ESM export (stripped by build-app.mjs in the concat path; kept by the bundle for real module scope). KEEP on ONE physical line.
export { AutopsyPanel, AutopsyFocusCard, LineagePanel, HoldoutPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel };
