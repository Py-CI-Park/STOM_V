/* dashboard-pages.jsx — Phase9(2026-06-13) SPA 6탭 통합.
 *
 * 기존 별도 HTML(lab.html / pro.html / verdict.html)의 루트 컴포넌트(LabRoot /
 * ProRoot / VerdictRoot)를 window 전역으로 추출해 단일 SPA(app.jsx)의 인페이지
 * 탭으로 마운트한다(풀 리로드 제거·WS 유지·중복 진입 제거). 동시에 각 standalone
 * HTML 도 이 파일의 전역(LabPage / ProPage / VerdictPanel)을 마운트하므로 직접
 * URL(/ui/lab.html 등)도 로직 중복 없이 그대로 동작한다.
 *
 * in-browser Babel JSX — import/export·TS 금지. 컴포넌트는 Object.assign(window, …)
 * 로 전역 노출. 파일별 훅 별칭(다른 파일과 충돌 방지)을 상단에 둔다.
 *
 * ResearchLabPanel / ResearchProPanel 는 research-lab.jsx / research-pro.jsx 의
 * 전역이다 — 본 파일이 그보다 늦게 로드되더라도 마운트 시점엔 존재한다. 방어적으로
 * (부재 시 "로딩 중" 자리표시자) 참조해 절대 크래시하지 않는다. */

const { useState: useState_dp, useEffect: useEffect_dp } = React;

// 의존 전역이 아직 로드되지 않았을 때(이론상) 크래시 대신 보이는 작은 자리표시자.
function _DpLoading({ name }) {
  return (
    <div className="research-empty" style={{ padding: "12px 16px" }}>
      {name} 로딩 중…
    </div>
  );
}

// baseUrl prop 이 없으면 현재 페이지 origin 을 쓴다(standalone HTML 직접 진입 대비).
function _dpBase(baseUrl) {
  if (baseUrl) return baseUrl;
  return (typeof window !== "undefined" && window.location && window.location.origin) || "";
}

/* G-3 — run 종류 뱃지(접두 휴리스틱). lab.html 에서 추출(동일 의미 유지). */
const RUN_KIND = id =>
  id.startsWith("tmap2") ? "격자" :
  id.startsWith("tmap") ? "지도" :
  id.startsWith("wf_") ? "전진" :
  id.includes("placebo") ? "대조" :
  id.includes("oos") ? "OOS" :
  (id.includes("reeval") || id.includes("combo")) ? "재평가" :
  id.includes("multiseed") ? "발굴" : "루프";

// ============================================================ LabPage (연구실)
// lab.html 의 Sidebar + LabRoot 를 그대로 추출. props: {baseUrl}.
function _DpSidebar({ runs, runId, setRunId, ops, verdict }) {
  const active = (ops && ops.active) || [];
  return (
    <div style={{ width: 280, flexShrink: 0, paddingRight: 12, overflowY: "auto",
                  maxHeight: "calc(100vh - 24px)",
                  borderRight: "1px solid rgba(255,255,255,0.08)" }}>
      <div className="research-empty">실행 중</div>
      {active.length === 0
        ? <div className="mono" style={{ fontSize: 11 }}>없음</div>
        : active.map(a => (
          <div key={a.run_id} className="mono" style={{ fontSize: 11, marginBottom: 4 }}>
            🔄 {a.run_id}
            <div style={{ opacity: 0.65 }}>
              {a.gens}세대 · {a.health === "active" ? "진행 중" : "⚠️ 정체 의심"}
            </div>
          </div>
        ))}
      {ops && ops.batch_queue && (
        <div className="mono" style={{ fontSize: 10.5, opacity: 0.7, marginTop: 2 }}>
          큐: {ops.batch_queue.stages_done}단계 완료 · {ops.batch_queue.current_template || "—"}
        </div>
      )}

      {verdict && (verdict.lines || []).length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="research-empty">
            검증 결산 요약{(verdict.alerts || []).length ? ` · ⚠️${verdict.alerts.length}` : ""}
          </div>
          {verdict.lines.slice(0, 2).map((l, i) => (
            <div key={i} className="mono" style={{ fontSize: 10.5, opacity: 0.85 }}>{l}</div>
          ))}
        </div>
      )}

      <div className="research-empty" style={{ marginTop: 10 }}>run 목록 (최신순)</div>
      {runs.map(r => (
        <div key={r.run_id} onClick={() => setRunId(r.run_id)} className="mono"
             style={{ fontSize: 11, padding: "3px 5px", cursor: "pointer", borderRadius: 4,
                      background: r.run_id === runId ? "rgba(90,140,200,0.25)" : "transparent" }}>
          <span style={{ opacity: 0.55 }}>[{RUN_KIND(r.run_id)}]</span>
          {r.status === "running" ? " 🔄 " : " "}{r.run_id}
          {r.label ? <div style={{ opacity: 0.5, fontSize: 10 }}>{r.label}</div> : null}
        </div>
      ))}
    </div>
  );
}

function LabPage({ baseUrl }) {
  const base = _dpBase(baseUrl);
  const [runs, setRuns] = useState_dp([]);
  const [runId, setRunId] = useState_dp("");
  const [ops, setOps] = useState_dp(null);
  const [verdict, setVerdict] = useState_dp(null);
  useEffect_dp(() => {
    fetch(base + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        const list = ((d && d.runs) || []).slice(0, 40);
        setRuns(list);
        if (list.length) setRunId(prev => prev || list[0].run_id);
      }).catch(() => {});
    fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setVerdict(j)).catch(() => {});
    const pull = () => fetch(base + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setOps(j)).catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [base]);

  const Panel = window.ResearchLabPanel;
  return (
    <div style={{ display: "flex", gap: 14, padding: "12px 0", minHeight: "60vh" }}>
      <_DpSidebar runs={runs} runId={runId} setRunId={setRunId} ops={ops} verdict={verdict} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
          <b style={{ fontSize: 15 }}>STOM Research Lab</b>
          <span className="mono" style={{ marginLeft: 10, fontSize: 11, opacity: 0.7 }}>{runId}</span>
        </div>
        {Panel
          ? <Panel baseUrl={base} wsStatus="na" runId={runId} />
          : <_DpLoading name="연구실 패널" />}
        {/* P1(2026-06-14): ResearchWiki + AIContext 의 전용 홈 — 진화 사이드바 중복 제거(P2)의
            선행 작업. 진화 사이드바와 동일 백엔드 컨텍스트 props(baseUrl/wsStatus/runId[+genNo])로
            연구실 탭 본문에 가산 렌더. (가산 단계 — 사이드바는 P2 에서 제거.) */}
        {window.ResearchWikiPanel && (
          <div style={{ marginTop: 14 }}>
            <ResearchWikiPanel baseUrl={base} wsStatus="na" runId={runId} />
          </div>
        )}
        {window.AIContextPanel && (
          <div style={{ marginTop: 14 }}>
            <AIContextPanel baseUrl={base} wsStatus="na" runId={runId} genNo={null} />{/* null=gen 필터 없이 최신 컨텍스트(lab 탭엔 활성 세대 없음) */}
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================= ProPage (분석 프로)
// pro.html 의 ProRoot 를 추출. props: {baseUrl}.
function ProPage({ baseUrl }) {
  const base = _dpBase(baseUrl);
  const [runId, setRunId] = useState_dp("");
  useEffect_dp(() => {
    fetch(base + "/runs", { signal: AbortSignal.timeout(10000) })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        const list = ((d && d.runs) || []).slice(0, 40);
        if (list.length) setRunId((prev) => prev || list[0].run_id);
      })
      .catch(() => {});
  }, [base]);

  const Panel = window.ResearchProPanel;
  return (
    <div style={{ minHeight: "60vh" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0",
                    borderBottom: "1px solid rgba(255,255,255,0.08)", marginBottom: 8 }}>
        <b style={{ fontSize: 15 }}>STOM 리서치 프로</b>
      </div>
      {Panel
        ? <Panel baseUrl={base} wsStatus="na" runId={runId} />
        : <_DpLoading name="리서치 프로 패널" />}
    </div>
  );
}

// =========================================================== VerdictPanel (결정 이력)
// verdict.html 의 VerdictRoot 를 통째로 추출. props: {baseUrl}.
//   ICON 맵과 append-only 의미(번복도 새 레코드)를 정확히 보존한다.
const ICON = { pass: "✅", warn: "⚠️", fail: "❌", pending: "⏳" };

function VerdictPanel({ baseUrl }) {
  const base = _dpBase(baseUrl);
  const [v, setV] = useState_dp(null);
  const [history, setHistory] = useState_dp([]);
  const [choice, setChoice] = useState_dp("hold");
  const [note, setNote] = useState_dp("");
  const [saved, setSaved] = useState_dp(null);
  const [regime, setRegime] = useState_dp(null);
  const [revival, setRevival] = useState_dp(null);
  const [portfolio, setPortfolio] = useState_dp(null);  // 부모 Phase3 — V6 채택 추천 포트폴리오.
  // 하위 탭 — 다른 탭(연구실)과 동일한 .research-tabs 패턴으로 밀집된 결정 화면을 분류.
  //   summary(검증 결산)·regime(레짐·부활)·portfolio(V6 포트폴리오)·decide(운용 결정).
  const [vsub, setVsub] = useState_dp(() => {
    try { return window.localStorage.getItem("stom_verdict_subtab") || "summary"; }
    catch (e) { return "summary"; }
  });
  const selectVsub = (k) => {
    setVsub(k);
    try { window.localStorage.setItem("stom_verdict_subtab", k); } catch (e) {}
  };

  const loadHistory = () =>
    fetch(base + "/decisions", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(d => setHistory((d && d.decisions) || []))
      .catch(() => {});
  useEffect_dp(() => {
    fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setV(j)).catch(() => {});
    fetch(base + "/regime_report", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setRegime(j)).catch(() => {});
    fetch(base + "/revival_registry", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setRevival(j)).catch(() => {});
    fetch(base + "/portfolio_verdict", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null)).then(j => setPortfolio(j)).catch(() => {});
    loadHistory();
  }, [base]);

  const submit = () => {
    fetch(base + "/record_decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verdict: choice, note }),
    })
      .then(r => r.json())
      .then(d => { setSaved(d); setNote(""); loadHistory(); })
      .catch(e => setSaved({ status: "error", error: String(e) }));
  };

  // 하위 탭 정의 — 라벨 옆에 현황 배지(개수/상태)를 달아 한눈에 분류되게 한다.
  const _vBadge = (() => {
    const checks = (v && v.promote_checklist) || [];
    const alerts = ((v && v.alerts) || []).length;
    return {
      summary: checks.length ? (alerts ? "⚠️" + alerts : "✓") : "",
      regime: (regime && regime.status !== "unavailable" ? "" : "—"),
      portfolio: (portfolio && portfolio.adopted ? "★" : (portfolio && portfolio.status === "unavailable" ? "—" : "")),
      decide: history.length ? String(history.length) : "",
    };
  })();
  const VSUBS = [
    { key: "summary", label: "검증 결산", ico: "📋" },
    { key: "regime", label: "레짐·부활", ico: "🌐" },
    { key: "portfolio", label: "V6 포트폴리오", ico: "★" },
    { key: "decide", label: "운용 결정", ico: "⚖️" },
  ];

  return (
    <div style={{ padding: "14px 0", maxWidth: 980, margin: "0 auto", minHeight: "60vh" }}>
      <div style={{ display: "flex", alignItems: "center", marginBottom: 10 }}>
        <b style={{ fontSize: 16 }}>검증 결산과 운용 결정 (V6)</b>
        <span className="mono" style={{ marginLeft: 10, fontSize: 11, color: "var(--ink-3)" }}>
          증거 → 결정(append-only) 워크플로우
        </span>
      </div>

      {/* 하위 탭바 — 다른 탭(연구실)과 동일한 .research-tabs 패턴으로 체계화. */}
      <div className="research-tabs" role="tablist" aria-label="결정 이력 하위 탭" style={{ marginBottom: 12 }}>
        {VSUBS.map(t => (
          <button key={t.key} type="button" role="tab" aria-selected={vsub === t.key}
                  className={"research-tab" + (vsub === t.key ? " active" : "")}
                  onClick={() => selectVsub(t.key)}>
            <span aria-hidden="true" style={{ marginRight: 4 }}>{t.ico}</span>
            {t.label}
            {_vBadge[t.key] ? <span style={{ marginLeft: 5, opacity: 0.7 }}>{_vBadge[t.key]}</span> : null}
          </button>
        ))}
      </div>

      {/* ── 검증 결산: PROMOTE 체크리스트 · OOS CI · 경보/요약 ── */}
      {vsub === "summary" && (
        <div>
          {v && (v.promote_checklist || []).length > 0 ? (
            <table className="mono" style={{ fontSize: 12, width: "100%", marginBottom: 8 }}>
              <thead><tr><th>PROMOTE 조건</th><th>상태</th><th>근거</th></tr></thead>
              <tbody>
                {v.promote_checklist.map((c, i) => (
                  <tr key={i}><td>{c.item}</td><td>{ICON[c.status] || "?"}</td><td>{c.detail || "—"}</td></tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>PROMOTE 체크리스트: 데이터 없음</div>
          )}
          {v && v.oos_diff_ci && Object.keys(v.oos_diff_ci).length > 0 && (
            <div style={{ marginTop: 8, marginBottom: 4 }}>
              <div className="mono" style={{ fontSize: 11, color: "#9fb0c0", marginBottom: 2 }}>
                OOS 차이 신뢰구간 (advisory) — CI가 0을 걸치면 표본 부족 신호 — 판정 미사용
              </div>
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>OOS 연도</th><th>total_diff</th><th>CI 95%</th><th>P(diff≤0)</th></tr></thead>
                <tbody>
                  {Object.entries(v.oos_diff_ci).map(([year, ci]) => (
                    <tr key={year}>
                      <td>{year}</td>
                      <td>{ci ? Math.round(ci.total_diff).toLocaleString() : "—"}</td>
                      <td>{ci ? `[${Math.round(ci.ci_low).toLocaleString()}, ${Math.round(ci.ci_high).toLocaleString()}]` : "—"}</td>
                      <td>{ci ? ci.p_diff_le_0 : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {v && (v.alerts || []).map((a, i) => (
            <div key={"a" + i} className="mono" style={{ fontSize: 12, color: "#c95" }}>⚠️ {a}</div>
          ))}
          {v && (v.lines || []).map((l, i) => (
            <div key={"l" + i} className="mono" style={{ fontSize: 12 }}>{l}</div>
          ))}
        </div>
      )}

      {/* ── 레짐·부활: 레짐 분해 · 패자부활 레지스트리 (둘 다 advisory) ── */}
      {vsub === "regime" && (
        <div>
          {regime && regime.status !== "unavailable" && (
            <div>
              <div className="research-empty">레짐 분해 (advisory) — 판정 미사용</div>
              {["THETA", "SEED"].map(grp => {
                const d = (regime.breakdowns || {})[grp];
                if (!d) return null;
                const act = d.active || {}, con = d.contracted || {};
                return (
                  <div key={grp} className="mono" style={{ fontSize: 11, marginTop: 4 }}>
                    <b>{grp}</b>
                    {" · 활성장 "}
                    {act.profit != null ? "+" + Math.round(act.profit).toLocaleString() : "—"}
                    {act.days != null ? ` (${act.days}일)` : ""}
                    {" · 위축장 "}
                    {con.profit != null ? "+" + Math.round(con.profit).toLocaleString() : "—"}
                    {con.days != null ? ` (${con.days}일)` : ""}
                    {d.concentration != null ? ` · 집중도 ${(d.concentration * 100).toFixed(1)}%` : ""}
                    {d.warning ? <span style={{ color: "#c95" }}> ⚠️ {d.warning}</span> : <span style={{ color: "#7c4" }}> ✓ 레짐 균형</span>}
                  </div>
                );
              })}
            </div>
          )}
          {regime && regime.status === "unavailable" && (
            <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>레짐 분해: 데이터 없음</div>
          )}

          {revival && revival.status !== "unavailable" && (
            <div style={{ marginTop: 14 }}>
              <div className="research-empty">
                패자부활 레지스트리
                {Array.isArray(revival.rejected) ? ` — 등재 ${revival.rejected.length}건` : ""}
              </div>
              {Array.isArray(revival.rejected) && revival.rejected.slice(0, 10).map((item, i) => (
                <div key={i} className="mono" style={{ fontSize: 11, marginTop: 2 }}>
                  <b>{item.label || "—"}</b>
                  {item.rejected_at ? ` · 기각 ${item.rejected_at}` : ""}
                  {item.reject_basis ? ` · ${item.reject_basis}` : ""}
                </div>
              ))}
              <div className="mono" style={{ fontSize: 10, opacity: 0.65, marginTop: 2 }}>
                신규 데이터 도착 시 전수 자동 재검증
              </div>
            </div>
          )}
          {revival && revival.status === "unavailable" && (
            <div className="mono" style={{ fontSize: 11, marginTop: 14, opacity: 0.6 }}>패자부활 레지스트리: 데이터 없음</div>
          )}
        </div>
      )}

      {/* ── V6 포트폴리오: 채택 추천 포트폴리오 (부모 Phase3 — /portfolio_verdict) ── */}
      {vsub === "portfolio" && (
        <div>
          {portfolio && portfolio.adopted && (
            <div style={{ padding: 12, border: "1px solid rgba(90,180,100,0.35)", borderRadius: 6, background: "rgba(50,120,60,0.08)" }}>
              <div className="research-empty" style={{ color: "#7c4" }}>★ V6 채택 추천 포트폴리오</div>
              <div className="mono" style={{ fontSize: 12, marginTop: 6 }}>
                {(portfolio.members || []).map(m => (
                  <span key={m.name} style={{ marginRight: 16 }}>
                    <b>{m.name}</b> {Math.round(m.weight * 100)}%
                  </span>
                ))}
              </div>
              {portfolio.m4 && (
                <div style={{ marginTop: 8 }}>
                  <div className="mono" style={{ fontSize: 11, opacity: 0.75, marginBottom: 2 }}>M4 baseline (포트폴리오 vs 시드 — {portfolio.m4.n_months}개월)</div>
                  <div className="mono" style={{ fontSize: 12 }}>
                    포트폴리오 합계: <b>{portfolio.m4.champion_total != null ? Math.round(portfolio.m4.champion_total).toLocaleString() : "—"}</b>
                    {" · "}
                    시드 합계: <b>{portfolio.m4.challenger_total != null ? Math.round(portfolio.m4.challenger_total).toLocaleString() : "—"}</b>
                    {portfolio.m4.champion_total != null && portfolio.m4.challenger_total != null && portfolio.m4.challenger_total !== 0 && (
                      <span style={{ marginLeft: 8, color: portfolio.m4.champion_total >= portfolio.m4.challenger_total ? "#7c4" : "#c95" }}>
                        ({portfolio.m4.champion_total >= portfolio.m4.challenger_total ? "+" : ""}
                        {(((portfolio.m4.champion_total - portfolio.m4.challenger_total) / Math.abs(portfolio.m4.challenger_total)) * 100).toFixed(1)}% 우위)
                      </span>
                    )}
                  </div>
                  {(portfolio.m4.alerts || []).length > 0 && portfolio.m4.alerts.map((a, i) => (
                    <div key={i} className="mono" style={{ fontSize: 11, color: "#c95" }}>⚠️ {a}</div>
                  ))}
                  {(portfolio.m4.alerts || []).length === 0 && (
                    <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>경보 없음</div>
                  )}
                </div>
              )}
              {portfolio.decision_note && (
                <div className="mono" style={{ fontSize: 11, marginTop: 8, opacity: 0.85, borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: 6 }}>
                  결정 노트: {portfolio.decision_note}
                </div>
              )}
              {portfolio.findings_doc && (
                <div className="mono" style={{ fontSize: 10, marginTop: 4, opacity: 0.55 }}>
                  검증 문서: {portfolio.findings_doc}
                </div>
              )}
            </div>
          )}
          {portfolio && !portfolio.adopted && portfolio.status !== "unavailable" && (
            <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6 }}>
              <div className="research-empty">V6 포트폴리오 채택 미결정</div>
              <div className="mono" style={{ fontSize: 11, opacity: 0.6, marginTop: 4 }}>complement 결정 기록 없음</div>
            </div>
          )}
          {portfolio && portfolio.status === "unavailable" && (
            <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>V6 포트폴리오: 데이터 없음</div>
          )}
          {!portfolio && (
            <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>V6 포트폴리오: 로딩 중…</div>
          )}
        </div>
      )}

      {/* ── 운용 결정: 결정 기록 폼(append-only) + 결정 이력 ── */}
      {vsub === "decide" && (
        <div>
          {/* P2 결정 동선 크로스링크: 이 폼(REST /record_decision)은 운용 결정을 append-only로
              남기는 기록부. 실제 전략 내보내기 승인은 진화 탭 승인·내보내기 다이얼로그(WS
              final_approval)에서 처리 — 두 단계는 별개 계약. (decide 하위탭 — 기본 스냅샷 밖) */}
          <div className="mono" style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5, marginBottom: 8, padding: "6px 8px", border: "1px dashed var(--line-1)", borderRadius: 6 }}>
            ℹ️ 운영 채택 동선: 우승 전략 <b>내보내기 승인</b>은 진화 탭의 <b>승인·내보내기 다이얼로그</b>에서
            WS(<span className="mono">final_approval</span>)로 처리됩니다. 이 폼은 그 운용 <b>결정을 append-only</b>로
            남기는 기록부입니다(REST <span className="mono">/record_decision</span>).
          </div>
          <div style={{ padding: 12, border: "1px solid rgba(255,255,255,0.12)", borderRadius: 6 }}>
            <div className="research-empty">운용 결정 기록 (append-only — 번복도 새 레코드로 이력 보존)</div>
            <div style={{ display: "flex", gap: 12, alignItems: "center", margin: "8px 0", flexWrap: "wrap" }}>
              {["promote", "complement", "hold", "reject"].map(k => (
                <label key={k} className="mono" style={{ fontSize: 12, cursor: "pointer" }}>
                  <input type="radio" name="verdict" checked={choice === k}
                         onChange={() => setChoice(k)} /> {k}
                </label>
              ))}
              <input type="text" value={note} placeholder="결정 근거 메모"
                     onChange={e => setNote(e.target.value)}
                     className="mono" style={{ flex: 1, minWidth: 220, fontSize: 12 }} />
              <button type="button" className="research-tab" onClick={submit}>기록</button>
            </div>
            {saved && (
              <div className="mono" style={{ fontSize: 11, color: saved.status === "ok" ? "#5b9" : "#c95" }}>
                {saved.status === "ok" ? "기록됨" : `실패: ${saved.error || saved.status}`}
              </div>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <div className="research-empty">결정 이력</div>
            {history.length === 0
              ? <div className="mono" style={{ fontSize: 11 }}>기록 없음</div>
              : (
                <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                  <thead><tr><th>시각</th><th>결정</th><th>대상 후보</th><th>메모</th></tr></thead>
                  <tbody>
                    {history.slice().reverse().map((d, i) => (
                      <tr key={i}>
                        <td>{new Date((d.ts || 0) * 1000).toLocaleString("ko-KR")}</td>
                        <td>{d.verdict}</td>
                        <td>{d.candidate ? `${d.candidate.buy_name} (${Math.round(d.candidate.profit || 0).toLocaleString()})` : "—"}</td>
                        <td>{d.note || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
          </div>
        </div>
      )}
    </div>
  );
}

Object.assign(window, { LabPage, ProPage, VerdictPanel });
