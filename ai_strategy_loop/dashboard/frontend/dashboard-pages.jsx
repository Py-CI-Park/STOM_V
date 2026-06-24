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

// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { ResearchWikiPanel } from "./research-wiki.jsx";
import { ResearchIndexPanel } from "./research-index.jsx";
import { AIContextPanel } from "./ai-context.jsx";
import { dashboardPathFor, normalizeEvolutionSubtabKey } from "./ui-contract.jsx";
import { UiStateBlock } from "./ui-state.jsx";
import { VisualQualityPanel } from "./visual-quality.jsx";
import { HofInventoryGate } from "./hof-inventory.jsx";
import { Phase2InventoryPanel, pageOwnerContract } from "./dashboard-inventory.jsx";
const { useState: useState_dp, useEffect: useEffect_dp } = React;

// 필수 전역이 누락되면 무한 로딩처럼 숨기지 않고 진단 가능한 오류로 표시한다.
function _DpLoading({ name }) {
  return (
    <UiStateBlock kind="error" compact title={`${name} 로드 실패`} detail="required dashboard component global missing">
      번들 로드 순서 또는 빌드 산출물에 문제가 있습니다. 이 표면은 대체 데이터 없이 중단됩니다.
    </UiStateBlock>
  );
}

// baseUrl prop 이 없으면 현재 페이지 origin 을 쓴다(standalone HTML 직접 진입 대비).
function _dpBase(baseUrl) {
  if (baseUrl) return baseUrl;
  return (typeof window !== "undefined" && window.location && window.location.origin) || "";
}
function _dpNavigateToTab(key) {
  const subtab = normalizeEvolutionSubtabKey(key === "pro" ? "workbench" : key);
  try {
    window.localStorage.setItem("stom_active_tab", "evolution");
    window.localStorage.setItem("stom_active_evolution_tab", subtab);
  } catch (e) {}
  if (window.location) window.location.href = dashboardPathFor("evolution", subtab);
}
const VERDICT_SECTION_KEYS = ["summary", "regime", "portfolio", "decide"];
const VERDICT_SECTION_META = {
  summary: { label: "검증 결산", ico: "📋", anchor: "verdict-summary", hint: "승격 체크리스트와 OOS 신뢰구간" },
  regime: { label: "레짐·부활", ico: "🌐", anchor: "verdict-regime", hint: "상황별 성과와 재검증 후보" },
  portfolio: { label: "V6 포트폴리오", ico: "★", anchor: "verdict-portfolio", hint: "채택 추천 조합과 기준선 비교" },
  decide: { label: "운용 결정", ico: "⚖️", anchor: "verdict-decide", hint: "append-only 결정 기록" },
};


function EvidenceWorkspaceHeader({ activeKey }) {
  const owner = pageOwnerContract(activeKey === "workbench" ? "pro" : activeKey);
  return (
    <div className="evidence-workspace-head evidence-workspace-head-static">
      <div>
        <div className="workspace-kicker mono">EVIDENCE WORKSPACE · OWNER MATRIX</div>
        <h2>기록 · 연구 · 분석 · 결정 역할 맵</h2>
        <p>
          현재 표면: <b>{owner.owner}</b>
        </p>
        <div className="workspace-owner-boundary mono">
          <span>owns: {owner.owns}</span>
          <span>not-owner: {owner.notOwner}</span>
        </div>
      </div>
      <Phase2InventoryPanel compact />
    </div>
  );
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

function LabPage({ baseUrl, onNavigate }) {
  const base = _dpBase(baseUrl);
  const [runs, setRuns] = useState_dp([]);
  const [runId, setRunId] = useState_dp("");
  const [ops, setOps] = useState_dp(null);
  const [verdict, setVerdict] = useState_dp(null);
  const [labErrors, setLabErrors] = useState_dp([]);
  useEffect_dp(() => {
    const markLabError = (label) => setLabErrors(prev => prev.includes(label) ? prev : [...prev, label]);
    fetch(base + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(d => {
        const list = ((d && d.runs) || []).slice(0, 40);
        setRuns(list);
        if (list.length) setRunId(prev => prev || list[0].run_id);
      }).catch(() => markLabError("runs"));
    fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setVerdict(j)).catch(() => markLabError("freeze_verdict"));
    const pull = () => fetch(base + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setOps(j)).catch(() => markLabError("ops_status"));
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [base]);

  const WikiPanel = window.ResearchWikiPanel || ResearchWikiPanel;
  const ContextPanel = window.AIContextPanel || AIContextPanel;
  const LabPanel = window.ResearchLabPanel;

  return (
    <div className="dashboard-page dashboard-page-lab" data-legacy-lab-panel={LabPanel ? "mounted" : "missing"}>
      <EvidenceWorkspaceHeader activeKey="lab" />
      <div style={{ display: "flex", gap: 14, padding: "12px 0", minHeight: "60vh" }}>
        <_DpSidebar runs={runs} runId={runId} setRunId={setRunId} ops={ops} verdict={verdict} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="dashboard-page-title">
            <b>STOM 연구실</b>
            <span className="mono">exploration · edge · variables · validation</span>
          </div>
          {labErrors.length > 0 && (
            <UiStateBlock kind="error" compact title="연구실 데이터 일부 로드 실패" detail={labErrors.join(" · ")}>
              실패한 endpoint를 빈 데이터로 숨기지 않습니다. 연결 또는 백엔드 상태를 확인하세요.
            </UiStateBlock>
          )}
          {LabPanel
            ? <LabPanel baseUrl={base} wsStatus="na" runId={runId} onOpenWorkbench={() => _dpNavigateToTab("workbench")} />
            : <_DpLoading name="연구실 분석 패널" />}
          <details className="lab-example" style={{ marginTop: 14 }}>
            <summary>연구 위키 · AI 컨텍스트 보기</summary>
            {WikiPanel ? (
              <div style={{ marginTop: 14 }}>
                {WikiPanel === ResearchWikiPanel
                  ? <ResearchWikiPanel baseUrl={base} wsStatus="na" runId={runId} />
                  : <WikiPanel baseUrl={base} wsStatus="na" runId={runId} />}
              </div>
            ) : <_DpLoading name="리서치 위키 패널" />}
            {ContextPanel ? (
              <div style={{ marginTop: 14 }}>
                {ContextPanel === AIContextPanel
                  ? <AIContextPanel baseUrl={base} wsStatus="na" runId={runId} genNo={null} />
                  : <ContextPanel baseUrl={base} wsStatus="na" runId={runId} genNo={null} />}
              </div>
            ) : <_DpLoading name="AI 컨텍스트 패널" />}
          </details>
          <div style={{ marginTop: 14 }}>
            <VisualQualityPanel compact />
          </div>
        </div>
      </div>
    </div>
  );
}

function ResearchIndexPage({ baseUrl, onNavigate }) {
  const base = _dpBase(baseUrl);
  const Panel = window.ResearchIndexPanel || ResearchIndexPanel;
  return (
    <div className="dashboard-page dashboard-page-records" style={{ padding: "12px 0", minHeight: "60vh" }}>
      <EvidenceWorkspaceHeader activeKey="records" onSelect={onNavigate} />
      <div className="research-index-page-head">
        <b>STOM 히스토리</b>
        <span className="mono">run/gen result archive · Compare · campaign/docs/update_log/registry lineage</span>
      </div>
      <Panel baseUrl={base} wsStatus="na" />
    </div>
  );
}

// ============================================================= ProPage (분석 프로)
// pro.html 의 ProRoot 를 추출. props: {baseUrl}.
function ProPage({ baseUrl, onNavigate }) {
  const base = _dpBase(baseUrl);
  const [runId, setRunId] = useState_dp("");
  const [proErrors, setProErrors] = useState_dp([]);
  useEffect_dp(() => {
    fetch(base + "/runs", { signal: AbortSignal.timeout(10000) })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((d) => {
        const list = ((d && d.runs) || []).slice(0, 40);
        if (list.length) setRunId((prev) => prev || list[0].run_id);
      })
      .catch(() => setProErrors(prev => prev.includes("runs") ? prev : [...prev, "runs"]));
  }, [base]);

  const Panel = window.ResearchProPanel;
  return (
    <div className="dashboard-page dashboard-page-pro" style={{ minHeight: "60vh" }}>
      <EvidenceWorkspaceHeader activeKey="workbench" onSelect={onNavigate} />
      <div className="dashboard-page-title">
        <b>STOM 분석 워크벤치</b>
        <span className="mono">candidate analysis · HoF field contract · workbench actions</span>
      </div>
      <HofInventoryGate />
      {proErrors.length > 0 && (
        <UiStateBlock kind="error" compact title="분석 워크벤치 데이터 일부 로드 실패" detail={proErrors.join(" · ")}>
          실패한 endpoint를 빈 워크벤치처럼 숨기지 않습니다. 연결 또는 백엔드 상태를 확인하세요.
        </UiStateBlock>
      )}
      {Panel
        ? <Panel baseUrl={base} wsStatus="na" runId={runId} />
        : <_DpLoading name="리서치 프로 패널" />}
    </div>
  );
}

// =========================================================== VerdictPanel (결정 이력)
// verdict.html 의 VerdictRoot 를 통째로 추출. props: {baseUrl}.
//   append-only 의미(번복도 새 레코드)를 정확히 보존한다.
//   (P7: 상태 아이콘 맵은 공유 VdtPromoteChecklist(_VDT_STATUS_ICON)로 이전 — 여기 ICON 은 제거.)

// P7(2026-06-15) — freeze_verdict 공유 표시 블록(정본: research-lab.jsx 정의, ORDER 선행).
//   주의: 여기서 `const VdtPromoteChecklist = window.VdtPromoteChecklist` 처럼 최상위 const 로
//   별칭하면 단일 번들 스코프에서 research-lab 의 `function VdtPromoteChecklist` 와 이름 충돌
//   ("already been declared" SyntaxError → 전 앱 크래시). 따라서 별칭 없이 JSX 에서 멤버표현식
//   `<window.VdtPromoteChecklist .../>` 로 직접 참조한다(window.LabPage 패턴과 동일).

function VerdictPanel({ baseUrl, onNavigate }) {
  const base = _dpBase(baseUrl);
  const [v, setV] = useState_dp(null);
  const [history, setHistory] = useState_dp([]);
  const [historyFailed, setHistoryFailed] = useState_dp(false);
  const [choice, setChoice] = useState_dp("hold");
  const [note, setNote] = useState_dp("");
  const [saved, setSaved] = useState_dp(null);
  const [regime, setRegime] = useState_dp(null);
  const [revival, setRevival] = useState_dp(null);
  const [portfolio, setPortfolio] = useState_dp(null);  // 부모 Phase3 — V6 채택 추천 포트폴리오.
  const [verdictErrors, setVerdictErrors] = useState_dp([]);
  const markVerdictError = (label) => setVerdictErrors(prev => prev.includes(label) ? prev : [...prev, label]);
  // G006 — 결정 감사는 하위 탭이 아니라 한 페이지에서 읽는 섹션 묶음이다.
  //   검증 결산·레짐·포트폴리오·운용 결정은 같은 감사 문맥의 일부이므로
  //   숨겨진 tab state/localStorage 없이 앵커 섹션과 요약 필터만 제공한다.

  const loadHistory = () =>
    fetch(base + "/decisions", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(d => { setHistory((d && d.decisions) || []); setHistoryFailed(false); })
      .catch(() => { markVerdictError("decisions"); setHistoryFailed(true); });
  useEffect_dp(() => {
    fetch(base + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setV(j)).catch(() => markVerdictError("freeze_verdict"));
    fetch(base + "/regime_report", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setRegime(j)).catch(() => markVerdictError("regime_report"));
    fetch(base + "/revival_registry", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setRevival(j)).catch(() => markVerdictError("revival_registry"));
    fetch(base + "/portfolio_verdict", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))).then(j => setPortfolio(j)).catch(() => markVerdictError("portfolio_verdict"));
    loadHistory();
  }, [base]);

  const submit = () => {
    fetch(base + "/record_decision", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ verdict: choice, note }),
    })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(d => { setSaved(d); setNote(""); loadHistory(); })
      .catch(e => setSaved({ status: "error", error: String(e) }));
  };
  const missingVerdictGlobals = ["VdtPromoteChecklist", "VdtAlerts", "VdtSummaryLines"]
    .filter(name => typeof window[name] !== "function");

  // 섹션 인덱스 배지 — 라벨 옆에 현황(개수/상태)을 보여 한눈에 분류한다.
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
  const VSECTIONS = VERDICT_SECTION_KEYS.map(key => ({ key, ...VERDICT_SECTION_META[key] }));

  return (
    <div className="dashboard-page dashboard-page-verdict" style={{ padding: "14px 0", maxWidth: 980, margin: "0 auto", minHeight: "60vh" }}>
      <EvidenceWorkspaceHeader activeKey="verdict" onSelect={onNavigate} />
      <div className="dashboard-page-title">
        <b>검증 결산과 결정 감사</b>
        <span className="mono">증거 → 결정 기록 append-only · final approval 분리</span>
      </div>

      {/* G006 — 하위 탭 제거: 같은 페이지 안에서 모두 보이는 감사 섹션 인덱스. */}
      <div className="verdict-section-index" aria-label="결정 감사 섹션 바로가기">
        {VSECTIONS.map(t => (
          <a key={t.key} href={`#${t.anchor}`} className="verdict-section-link">
            <span aria-hidden="true">{t.ico}</span>
            <b>{t.label}</b>
            {_vBadge[t.key] ? <span className="verdict-section-badge">{_vBadge[t.key]}</span> : null}
            <small>{t.hint}</small>
          </a>
        ))}
      </div>
      <div className="readability-note verdict-readability-note">
        결정 감사는 탭을 다시 숨기지 않고 한 화면에서 검증 → 상황 해석 → 포트폴리오 → 운용 기록 순서로 읽습니다.
        final approval은 전략 내보내기 승인이고, 이 페이지는 근거와 운용 판단을 append-only로 남기는 감사 장부입니다.
      </div>
      <div className="verdict-glossary" aria-label="결정 감사 용어 설명">
        <span><b>PROMOTE</b> 실매매 후보로 승격 가능한지 보는 체크리스트</span>
        <span><b>OOS</b> 학습에 쓰지 않은 기간의 검증 결과</span>
        <span><b>레짐</b> 시장 상황별 성과 차이</span>
        <span><b>append-only</b> 수정·삭제 대신 새 기록을 추가해 이력을 보존</span>
      </div>
      <details className="verdict-example">
        <summary>예시 보기: 결정을 남기는 흐름</summary>
        <ol>
          <li>검증 결산에서 경보와 OOS 신뢰구간을 확인합니다.</li>
          <li>레짐·부활에서 특정 상황에만 좋은 후보인지 확인합니다.</li>
          <li>포트폴리오 기준선 비교 후 운용 결정에 근거 메모를 남깁니다.</li>
        </ol>
      </details>
      {verdictErrors.length > 0 && (
        <UiStateBlock kind="error" compact title="결정 감사 데이터 일부 로드 실패" detail={verdictErrors.join(" · ")}>
          실패한 endpoint를 빈 기록처럼 숨기지 않습니다. 연결 또는 백엔드 상태를 확인하세요.
        </UiStateBlock>
      )}

      <section id="verdict-summary" className="verdict-section">
        <div className="verdict-section-head">
          <h3>📋 검증 결산</h3>
          <p>PROMOTE 체크리스트, OOS 차이 신뢰구간, 경보와 요약을 한 번에 확인합니다.</p>
        </div>
        <div>
          {missingVerdictGlobals.length > 0 ? (
            <UiStateBlock kind="error" compact title="결정 감사 공용 컴포넌트 로드 실패" detail={missingVerdictGlobals.join(" · ")}>
              PROMOTE 체크리스트와 요약 컴포넌트가 번들에 없습니다. 대체 판정 없이 오류로 표시합니다.
            </UiStateBlock>
          ) : (
            <>
              <window.VdtPromoteChecklist v={v} />
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
              <window.VdtAlerts v={v} />
              <window.VdtSummaryLines v={v} />
            </>
          )}
        </div>
      </section>

      <section id="verdict-regime" className="verdict-section">
        <div className="verdict-section-head">
          <h3>🌐 레짐·부활</h3>
          <p>시장 상황별 성과 차이와 재검증 대기 후보를 advisory 정보로 분리해 봅니다.</p>
        </div>
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
      </section>

      <section id="verdict-portfolio" className="verdict-section">
        <div className="verdict-section-head">
          <h3>★ V6 포트폴리오</h3>
          <p>채택 추천 포트폴리오와 M4 기준선 비교를 운용 결정 전에 확인합니다.</p>
        </div>
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
          {!portfolio && !verdictErrors.includes("portfolio_verdict") && (
            <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>V6 포트폴리오: 로딩 중…</div>
          )}
          {!portfolio && verdictErrors.includes("portfolio_verdict") && (
            <div className="mono" style={{ fontSize: 11, color: "var(--amber)" }}>V6 포트폴리오: 로드 실패</div>
          )}
        </div>
      </section>

      <section id="verdict-decide" className="verdict-section">
        <div className="verdict-section-head">
          <h3>⚖️ 운용 결정</h3>
          <p>결정과 근거 메모를 append-only 이력으로 남깁니다. 번복도 삭제가 아니라 새 기록입니다.</p>
        </div>
        <div>
          {/* P2 결정 동선 크로스링크: 이 폼(REST /record_decision)은 운용 결정을 append-only로
              남기는 기록부. 실제 전략 내보내기 승인은 진화 탭 승인·내보내기 다이얼로그(WS
              final_approval)에서 처리 — 두 단계는 별개 계약. */}
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
              <button type="button" className="btn primary sm" onClick={submit}>기록</button>
            </div>
            {saved && (
              <div className="mono" style={{ fontSize: 11, color: saved.status === "ok" ? "#5b9" : "#c95" }}>
                {saved.status === "ok" ? "기록됨" : `실패: ${saved.error || saved.status}`}
              </div>
            )}
          </div>

          <div style={{ marginTop: 12 }}>
            <div className="research-empty">결정 이력</div>
            {historyFailed
              ? <div className="mono" style={{ fontSize: 11, color: "var(--warn)" }}>결정 이력 로드 실패 — endpoint 오류를 빈 기록으로 숨기지 않습니다.</div>
              : history.length === 0
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
      </section>
    </div>
  );
}

Object.assign(window, { LabPage, ProPage, VerdictPanel, ResearchIndexPage });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { LabPage, ProPage, VerdictPanel, ResearchIndexPage };
