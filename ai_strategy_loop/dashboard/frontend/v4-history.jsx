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
import { ResearchLabPanel } from "./rl-panel.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { ResearchWikiPanel } from "./research-wiki.jsx";

const { useState: useState_v4history, useCallback: useCallback_v4history } = React;
function V4History({ baseUrl, wsStatus, runId, onNavigate }) {
  const [selectedResearchId, setSelectedResearchId] = useState_v4history("");
  const selectResearch = useCallback_v4history((researchId) => {
    setSelectedResearchId(typeof researchId === "string" ? researchId : "");
  }, []);
  const historyLoading = wsStatus === "connecting" || wsStatus === "reconnecting";
  const freshnessLabel = wsStatus === "open"
    ? "서버 연결됨 · 선택한 아카이브 응답을 표시합니다."
    : wsStatus === "demo"
      ? "예시 아카이브 · 운영 기록과 분리된 데이터입니다."
      : wsStatus === "reconnecting"
        ? "연결 끊김 · 표시된 기록은 마지막 응답일 수 있습니다. 새 응답 전에는 최신으로 간주하지 않습니다."
        : "아카이브 연결 중 · 로딩이 끝날 때까지 이전 응답을 최신으로 간주하지 않습니다.";

  return (
    <div className="v4-history">
      <section className="panel" aria-labelledby="v4-history-journey-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-history-journey-title">History 작업 흐름</div>
            <div className="mono">아카이브/Compare 탐색만 읽기 전용이며, 아래 append-only 결정 기록은 예외입니다.</div>
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

      <section aria-labelledby="v4-history-archive-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-archive-title">아카이브 선택 · 요약 · Compare <span className="mono" style={{ fontSize: "10.5px", color: "var(--ink-3)" }}>— legacy run/gen archive selection (governed research selection과 별도)</span></h2>
        <div className="v4-history-archive-scroll" data-region="scroll" tabIndex={0} aria-label="과거 run과 세대 비교 데이터 영역">
          <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} />
        </div>
      </section>

      <section aria-labelledby="v4-history-lineage-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-lineage-title">조건식 History 트리 · A/B · 셀 히트맵 · 홀드아웃 퍼널</h2>
        <p className="mono" aria-live="polite" style={{ color: "var(--ink-3)", fontSize: "10.5px", margin: "0 0 8px" }}>
          Governed research selection: {selectedResearchId || "선택 없음 · 근거는 unavailable/missing으로 표시됩니다."}
        </p>
        <div data-region="scroll" tabIndex={0} aria-label="조건식 계보 트리와 연구 시각화 영역">
          <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} onSelectedResearchIdChange={selectResearch} />
          <AbPairCompareView baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} />
          <CellHeatmap baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} />
          <HoldoutFunnel baseUrl={baseUrl} wsStatus={wsStatus} selectedResearchId={selectedResearchId} />
        </div>
      </section>
      <section aria-labelledby="v4-history-analysis-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-analysis-title">엣지 · 변수 분석</h2>
        <p className="mono" style={{ color: "var(--ink-3)", fontSize: "10.5px", margin: "0 0 8px" }}>
          Archive run context: {runId || "선택 없음"} · governed research selection과 별도이며 campaign ID에서 run ID를 추정하지 않습니다.
        </p>
        <div data-region="scroll" tabIndex={0} aria-label="아카이브 run 기반 엣지와 변수 분석 영역">
          <ResearchLabPanel
            baseUrl={baseUrl}
            wsStatus={wsStatus}
            runId={runId}
            enabledTabIds={["edge", "feature", "correlation", "combos"]}
            showOpsStatus={false}
            showWorkbenchLink={false}
          />
        </div>
      </section>

      <section aria-labelledby="v4-history-candidate-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-candidate-title">후보 Compare</h2>
        <div data-region="scroll" tabIndex={0} aria-label="아카이브 run 기반 후보 분석과 비교 영역">
          <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
        </div>
      </section>

      <section aria-labelledby="v4-history-wiki-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-wiki-title">연구 Wiki</h2>
        <div data-region="scroll" tabIndex={0} aria-label="연구 위키 기록 영역">
          <ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        </div>
      </section>

      <section aria-labelledby="v4-history-index-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-index-title">연구 기록 색인 · 상세 근거</h2>
        <div data-region="scroll" tabIndex={0} aria-label="연구 기록 표와 상세 데이터 영역">
          <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} />
        </div>
      </section>

      <section aria-labelledby="v4-history-gov-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-gov-title">거버넌스 · 결정 원장 · 승급/Export 경계</h2>
        <p className="mono" style={{ color: "var(--ink-3)", fontSize: "10.5px", margin: "0 0 8px" }}>
          읽기 전용 범위는 아카이브/Compare 탐색뿐입니다. <b>Append-only 결정 기록은 쓰기 예외</b>이며, 아래 승급/Export 거버넌스 제어 전에 명시합니다.
        </p>
        <div data-region="scroll" tabIndex={0} aria-label="거버넌스 결정 원장과 검증 결산 영역">
          <AuditDecisionTrace baseUrl={baseUrl} selectedResearchId={selectedResearchId} onSelectResearch={selectResearch} showDecisionLedger={false} />
          <VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />
        </div>
      </section>
    </div>
  );
}

Object.assign(window, { V4History });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4History };
