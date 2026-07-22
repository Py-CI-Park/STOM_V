/* v4-history.jsx — V4 "History" 탭: run/gen 아카이브 · Compare · governed 연구 기록.
 *   legacy evolution/records 의 정본(ResearchRecordsPanel + ResearchIndexPage)을 직접 마운트.
 *   규칙 유지: run/gen 재열람·Compare·ResultDetail 은 History 가 단독 소유한다.
 *   B트랙 승격(2026-07-17): v4.1 조건식 History 트리 + G002 시각화 3종(A/B 쌍대비교·
 *   셀 히트맵·홀드아웃 퍼널)을 legacy records 탭과 동일 순서로 마운트한다.
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { ResearchRecordsPanel } from "./research-records-panel.jsx";
import { HistoryConditionTreePanel } from "./history-condition-tree.jsx";
import { AbPairCompareView, CellHeatmap, HoldoutFunnel } from "./history-viz.jsx";
import { AuditDecisionTrace } from "./v4-audit.jsx";
import { ResearchIndexPage, VerdictPanel } from "./dashboard-pages.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { BtResultArea } from "./backtest-charts.jsx";
const { useState: useState_v4h, useEffect: useEffect_v4h } = React;

function V4History({ baseUrl, wsStatus, onNavigate }) {
  const historyLoading = wsStatus === "connecting" || wsStatus === "reconnecting";
  // V6.3(S4): 선택 연구 마스터-디테일 — records 패널이 lift 한 선택을 컨텍스트 바가 소유.
  const [selResearch, setSelResearch] = useState_v4h(null); // { name, researchId, meta|null }
  const onSelectCampaign = (name, meta) => {
    const researchId = "campaign:" + name;
    setSelResearch(prev => (prev && prev.researchId === researchId && !meta)
      ? prev
      : { name, researchId, meta: meta || (prev && prev.researchId === researchId ? prev.meta : null) });
  };
  const [selectedAnalysis, setSelectedAnalysis] = useState_v4h(null);
  const onSelectAnalysis = (selection) => {
    if (selection && selection.run_id && selection.gen_no != null) setSelectedAnalysis(selection);
  };
  // L10: 재연결 문구 깜빡임 디바운스 — reconnecting 이 2초 지속될 때만 경고 문구 표시.
  // 대용량 색인·거버넌스·시각화 근거는 접힌 동안 마운트하지 않는다.
  const [indexOpen, setIndexOpen] = useState_v4h(false);
  const [govOpen, setGovOpen] = useState_v4h(false);
  const [cmpOpen, setCmpOpen] = useState_v4h(true);
  const [treeOpen, setTreeOpen] = useState_v4h(true);
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
          <span className="v6-selres-id mono" title="stable research ID">{selResearch.researchId}</span>
          {selResearch.meta && (
            <span className="v6-selres-meta mono">
              수정 {(() => { const u = selResearch.meta.updated_at; if (u == null) return "—"; const n = Number(u); return Number.isFinite(n) && n > 1e9 ? new Date(n * 1000).toISOString().slice(0, 10) : String(u).slice(0, 10); })()} · 후보 {selResearch.meta.candidate_count ?? "—"}
              {selResearch.meta.best && (selResearch.meta.best.label || selResearch.meta.best.name) ? " · best " + (selResearch.meta.best.label || selResearch.meta.best.name) : ""}
            </span>
          )}
          <button className="btn ghost sm" title="stable ID 복사"
                  onClick={() => { try { navigator.clipboard.writeText(selResearch.researchId); } catch (e) {} }}>ID 복사</button>
          <button className="btn ghost sm" title="연구 기록 색인으로 이동"
                  onClick={() => { const el = document.getElementById("v4-history-index-title"); el && el.scrollIntoView({ behavior: "smooth", block: "start" }); }}>색인에서 관련 기록</button>
          <span className="v6-selres-note">호환 섹션만 이 연구 ID를 사용합니다. 다른 유형의 분석은 독립 선택 상태로 유지됩니다.</span>
        </div>
      )}
      <section aria-labelledby="v4-history-archive-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-archive-title">아카이브 선택 · 요약</h2>
        <p className="v4-history-feature-copy">목적: 기록의 출처와 후보를 고정합니다. 방법: 캠페인을 선택해 상세를 확인하세요. 필요성: 이후 비교는 선택된 읽기 전용 근거를 기준으로 합니다.</p>
        <div className="v4-history-archive-scroll" data-region="scroll" tabIndex={0} aria-label="과거 run과 세대 비교 데이터 영역">
          <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} onSelectCampaign={onSelectCampaign} />
        </div>
      </section>

      {/* Compare와 조건식 트리는 즉시 열고, 대용량 시각화 근거는 필요할 때만 마운트한다. */}
      <details className="evo-group" open onToggle={(e) => setCmpOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label">Run Compare · A/B 비교</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0}>
          <p className="v4-history-feature-copy">목적: run의 성과와 winner 세대를 같은 기준으로 비교합니다. 방법: 최대 6개 run을 선택하고 ‘분석 보기’를 누르세요. 필요성: <b>campaign 연구 ID는 호환되지 않으며</b> Run Compare는 loop_run만 사용합니다.</p>
          {cmpOpen && <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} onSelectAnalysis={onSelectAnalysis} />}
          {selectedAnalysis && (
            <section className="v4-history-analysis" aria-label="선택한 run winner 분석">
              <div className="v4-history-analysis-head">
                <span className="mono">{selectedAnalysis.run_id} / gen {selectedAnalysis.gen_no}</span>
                <button className="btn ghost sm" onClick={() => setSelectedAnalysis(null)}>분석 닫기</button>
              </div>
              <BtResultArea baseUrl={baseUrl} isDemo={wsStatus === "demo"} jobId={null} evoSource={selectedAnalysis} />
            </section>
          )}
        </div>
      </details>
      <details className="evo-group" open onToggle={(e) => setTreeOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-lineage-title">조건식 History 트리</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="조건식 계보 트리 영역">
          <p className="v4-history-feature-copy">목적: 조건식 계보와 평가 흔적을 탐색합니다. 방법: research ID를 선택해 단계와 조건을 펼치세요. 필요성: <b>loop_run과 campaign ID는 서로 호환되지 않는 경우가 있어</b> 서버가 허용한 기록만 표시합니다.</p>
          {treeOpen && <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} />}
        </div>
      </details>
      <details className="evo-group" onToggle={(e) => setVizOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label">A/B · 셀 히트맵 · 홀드아웃 퍼널 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="조건식 대용량 시각화 근거 영역">
          <p className="v4-history-feature-copy">목적: A/B와 홀드아웃 근거를 교차 확인합니다. 방법: 트리 검토 뒤 필요할 때만 펼치세요. 필요성: 대용량 증거는 lazy 로드하며 호환되지 않는 research ID를 추정 결합하지 않습니다.</p>
          {vizOpen && (
            <React.Fragment>
              <AbPairCompareView baseUrl={baseUrl} wsStatus={wsStatus} />
              <CellHeatmap baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} />
              <HoldoutFunnel baseUrl={baseUrl} wsStatus={wsStatus} preferredResearchId={selResearch && selResearch.researchId} />
            </React.Fragment>
          )}
        </div>
      </details>
      {/* v5.3.1: 엣지 섹션 제거 — 채점·부검 스테이지(Live)가 정위치. 중복 mount 해소. */}

      <details className="evo-group" aria-labelledby="v4-history-index-title"
               onToggle={(e) => setIndexOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <h2 className="stom-section-label" id="v4-history-index-title">연구 기록 색인 · 상세 근거 (클릭 시 로드)</h2>
        </summary>
        <div className="evo-group-body" data-region="scroll" tabIndex={0} aria-label="연구 기록 표와 상세 데이터 영역" aria-busy={historyLoading}>
          <p className="v4-history-feature-copy">목적: 대량 연구 기록의 상세 근거를 찾습니다. 방법: 필요할 때만 펼쳐 검색하세요. 필요성: 색인은 무겁고, 호환되지 않는 research ID는 독립 조회로 남습니다.</p>
          {indexOpen && <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} initialQuery={selResearch ? selResearch.researchId : ""} preferredResearchId={selResearch && selResearch.researchId} />}
        </div>
      </details>

      {/* v5.3.1(U3 추천 채택): 거버넌스 UI 는 기본닫힘 fold 로 격하 — export human 승인 계약은 백엔드 불변. */}
      <details className="evo-group" aria-labelledby="v4-history-gov-title"
               onToggle={(e) => setGovOpen(e.currentTarget.open)}>
        <summary className="evo-group-summary">
          <div className="stom-section-label" id="v4-history-gov-title">거버넌스 · 결정 원장 (기본 접힘 · export 승인 경계는 불변)</div>
        </summary>
        <div className="evo-group-body">
          <p className="v4-history-feature-copy">목적: 결정 감사와 승인 경계를 확인합니다. 방법: 필요할 때만 펼쳐 원장을 읽으세요. 필요성: 거버넌스는 증거 조회 전용이며 호환되지 않는 연구 ID를 결합하지 않습니다.</p>
          <p className="mono v4-history-governance-note">
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
