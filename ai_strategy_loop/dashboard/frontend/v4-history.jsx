/* v4-history.jsx — V4 "History" 탭: run/gen 아카이브 · Compare · governed 연구 기록.
 *   legacy evolution/records 의 정본(ResearchRecordsPanel + ResearchIndexPage)을 직접 마운트.
 *   규칙 유지: run/gen 재열람·Compare·ResultDetail 은 History 가 단독 소유한다.
 *   B트랙 승격(2026-07-17): v4.1 조건식 History 트리 + G002 시각화 3종(A/B 쌍대비교·
 *   셀 히트맵·홀드아웃 퍼널)을 legacy records 탭과 동일 순서로 마운트한다.
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { ResearchRecordsPanel } from "./research-records-panel.jsx";
import { ResearchIndexPage } from "./dashboard-pages.jsx";
import { HistoryConditionTreePanel } from "./history-condition-tree.jsx";
import { AbPairCompareView, CellHeatmap, HoldoutFunnel } from "./history-viz.jsx";
import { AuditDecisionTrace } from "./v4-audit.jsx";
import { VerdictPanel } from "./dashboard-pages.jsx";
import { RunComparePanel } from "./run-compare.jsx";
const { useState: useState_v4h, useEffect: useEffect_v4h } = React;

function V4History({ baseUrl, wsStatus, onNavigate }) {
  const historyLoading = wsStatus === "connecting" || wsStatus === "reconnecting";
  // V6.3(S4): 선택 연구 마스터-디테일 — records 패널이 lift 한 선택을 컨텍스트 바가 소유.
  const [selResearch, setSelResearch] = useState_v4h(null); // { name, meta|null }
  const onSelectCampaign = (name, meta) => setSelResearch(prev =>
    (prev && prev.name === name && !meta) ? prev : { name, meta: meta || (prev && prev.name === name ? prev.meta : null) });
  // L10: 재연결 문구 깜빡임 디바운스 — reconnecting 이 2초 지속될 때만 경고 문구 표시.
  // v5.4 H1 — 무거운 하위 섹션 lazy-mount: 접힘 상태에서는 fetch/렌더 자체를 하지 않는다.
  //   (색인 /research_index 는 대용량 — 탭 진입 즉시 로드가 히스토리 렌더 정지의 원인이었다)
  const [indexOpen, setIndexOpen] = useState_v4h(false);
  const [govOpen, setGovOpen] = useState_v4h(false);
  const [cmpOpen, setCmpOpen] = useState_v4h(false);
  const [vizOpen, setVizOpen] = useState_v4h(false);
  const [stableWs, setStableWs] = useState_v4h(wsStatus);
  useEffect_v4h(() => {
    if (wsStatus !== "reconnecting") { setStableWs(wsStatus); return undefined; }
    const t = setTimeout(() => setStableWs("reconnecting"), 2000);
    return () => clearTimeout(t);
  }, [wsStatus]);
  const freshnessLabel = stableWs === "open"
    ? "서버 연결됨 · 선택한 아카이브 응답을 표시합니다."
    : stableWs === "demo"
      ? "예시 아카이브 · 운영 기록과 분리된 데이터입니다."
      : stableWs === "reconnecting"
        ? "연결 끊김 · 표시된 기록은 마지막 응답일 수 있습니다. 새 응답 전에는 최신으로 간주하지 않습니다."
        : "아카이브 연결 중 · 로딩이 끝날 때까지 이전 응답을 최신으로 간주하지 않습니다.";

  return (
    <div className="v4-history">
      <section className="panel" aria-labelledby="v4-history-journey-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-history-journey-title">History 작업 흐름</div>
            <div className="mono">과거 run/gen을 선택하고 근거를 비교하는 읽기 전용 여정</div>
          </div>
        </header>
        <div className="panel-bd">
          <div className="v4-wf" aria-label="History 기본 작업 순서">
            <div className="v4-wf-step">
              <span className="v4-wf-num">1</span>
              <span className="v4-wf-txt"><b>아카이브 선택</b><span>run과 세대를 고정</span></span>
            </div>
            <div className="v4-wf-step">
              <span className="v4-wf-num">2</span>
              <span className="v4-wf-txt"><b>요약 확인</b><span>기간·성과·근거를 검토</span></span>
            </div>
            <div className="v4-wf-step">
              <span className="v4-wf-num">3</span>
              <span className="v4-wf-txt"><b>Compare</b><span>동일 기준으로 후보 비교</span></span>
            </div>
          </div>
          <p className="mono" aria-live="polite">{freshnessLabel}</p>
        </div>
      </section>

      {selResearch && (
        <div className="v6-selres" role="note" aria-label="선택 연구 컨텍스트">
          <span className="v6-selres-id mono" title="stable research ID">campaign:{selResearch.name}</span>
          {selResearch.meta && (
            <span className="v6-selres-meta mono">
              수정 {(() => { const u = selResearch.meta.updated_at; if (u == null) return "—"; const n = Number(u); return Number.isFinite(n) && n > 1e9 ? new Date(n * 1000).toISOString().slice(0, 10) : String(u).slice(0, 10); })()} · 후보 {selResearch.meta.candidate_count ?? "—"}
              {selResearch.meta.best && (selResearch.meta.best.label || selResearch.meta.best.name) ? " · best " + (selResearch.meta.best.label || selResearch.meta.best.name) : ""}
            </span>
          )}
          <button className="btn ghost sm" title="stable ID 복사"
                  onClick={() => { try { navigator.clipboard.writeText("campaign:" + selResearch.name); } catch (e) {} }}>ID 복사</button>
          <button className="btn ghost sm" title="연구 기록 색인으로 이동"
                  onClick={() => { const el = document.getElementById("v4-history-index-title"); el && el.scrollIntoView({ behavior: "smooth", block: "start" }); }}>색인에서 관련 기록</button>
          <span className="v6-selres-note">아래 모든 섹션은 이 선택 연구의 맥락에서 읽습니다.</span>
        </div>
      )}
      <section aria-labelledby="v4-history-archive-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-archive-title">아카이브 선택 · 요약</h2>
        <div className="v4-history-archive-scroll" data-region="scroll" tabIndex={0} aria-label="과거 run과 세대 비교 데이터 영역">
          <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} onSelectCampaign={onSelectCampaign} />
        </div>
      </section>

      {/* v5.6 U7 — 진입 비용 절감: Compare·계보 시각화는 lazy fold(열 때만 fetch/마운트). */}
      <details className="evo-group" onToggle={(e) => setCmpOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" style={{ margin: 0 }}>Run Compare · A/B 비교 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0}>
          {cmpOpen && <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />}
        </div>
      </details>
      <details className="evo-group" onToggle={(e) => setVizOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-lineage-title" style={{ margin: 0 }}>조건식 History 트리 · A/B · 셀 히트맵 · 홀드아웃 퍼널 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="조건식 계보 트리와 연구 시각화 영역">
          {vizOpen && (
            <React.Fragment>
              <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} />
              <AbPairCompareView baseUrl={baseUrl} wsStatus={wsStatus} />
              <CellHeatmap baseUrl={baseUrl} wsStatus={wsStatus} />
              <HoldoutFunnel baseUrl={baseUrl} wsStatus={wsStatus} />
            </React.Fragment>
          )}
        </div>
      </details>
      {/* v5.3.1: 엣지 섹션 제거 — 채점·부검 스테이지(Live)가 정위치. 중복 mount 해소. */}

      <details className="evo-group" aria-labelledby="v4-history-index-title"
               onToggle={(e) => setIndexOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-index-title" style={{ margin: 0 }}>연구 기록 색인 · 상세 근거 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="연구 기록 표와 상세 데이터 영역" aria-busy={historyLoading}>
          {indexOpen && <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} />}
        </div>
      </details>

      {/* v5.3.1(U3 추천 채택): 거버넌스 UI 는 기본닫힘 fold 로 격하 — export human 승인 계약은 백엔드 불변. */}
      <details className="evo-group" aria-labelledby="v4-history-gov-title"
               onToggle={(e) => setGovOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <div className="stom-section-label" id="v4-history-gov-title">거버넌스 · 결정 원장 (기본 접힘 · export 승인 경계는 불변)</div>
        </summary>
        <div className="evo-group-body">
          <p className="mono" style={{ color: "var(--ink-3)", fontSize: "10.5px", margin: "0 0 8px" }}>
            append-only 결정 감사 · freeze/verdict · human-approval/export 경계(이전 Audit 탭에서 이전).
          </p>
          <div data-region="scroll" tabIndex={0} aria-label="거버넌스 결정 원장과 검증 결산 영역">
            {govOpen && <AuditDecisionTrace baseUrl={baseUrl} />}
            {govOpen && <VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />}
          </div>
        </div>
      </details>
    </div>
  );
}

Object.assign(window, { V4History });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4History };
