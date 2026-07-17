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

function V4History({ baseUrl, wsStatus, onNavigate }) {
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

      <section aria-labelledby="v4-history-archive-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-archive-title">아카이브 선택 · 요약 · Compare</h2>
        <div className="v4-history-archive-scroll" data-region="scroll" tabIndex={0} aria-label="과거 run과 세대 비교 데이터 영역">
          <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} />
        </div>
      </section>

      <section aria-labelledby="v4-history-lineage-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-lineage-title">조건식 History 트리 · A/B · 셀 히트맵 · 홀드아웃 퍼널</h2>
        <div data-region="scroll" tabIndex={0} aria-label="조건식 계보 트리와 연구 시각화 영역">
          <HistoryConditionTreePanel baseUrl={baseUrl} wsStatus={wsStatus} />
          <AbPairCompareView baseUrl={baseUrl} wsStatus={wsStatus} />
          <CellHeatmap baseUrl={baseUrl} wsStatus={wsStatus} />
          <HoldoutFunnel baseUrl={baseUrl} wsStatus={wsStatus} />
        </div>
      </section>

      <section aria-labelledby="v4-history-index-title" aria-busy={historyLoading}>
        <h2 className="stom-section-label" id="v4-history-index-title">연구 기록 색인 · 상세 근거</h2>
        <div data-region="scroll" tabIndex={0} aria-label="연구 기록 표와 상세 데이터 영역">
          <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} />
        </div>
      </section>
    </div>
  );
}

Object.assign(window, { V4History });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4History };
