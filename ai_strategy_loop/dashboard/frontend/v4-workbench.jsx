/* v4-workbench.jsx — V4 Workbench: candidate analysis, comparison, and evidence. */
// dual-safe ESM import (esbuild bundle path). KEEP each on ONE physical line.
import { ResearchProPanel } from "./research-pro.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { HallOfFamePanel } from "./chart.jsx";
import { HofInventoryGate } from "./hof-inventory.jsx";

function V4Workbench({ baseUrl, wsStatus, runId }) {
  const surfaceState = wsStatus === "connecting"
    ? "loading"
    : (wsStatus === "error" || wsStatus === "closed" || (!baseUrl && runId))
      ? "error"
      : runId
        ? "ready"
        : "empty";
  const statusText = surfaceState === "loading"
    ? "후보 비교 데이터를 연결하고 있습니다."
    : surfaceState === "error"
      ? "후보 비교 데이터를 확인할 수 없습니다. 승격 판단을 중지하세요."
      : surfaceState === "ready"
        ? `Run ${runId} 후보를 비교합니다. 후보 선택 상태는 아래 비교표의 선택 개수로 표시됩니다.`
        : "선택된 Run이 없습니다. 후보 선택 상태는 Run을 고른 뒤 비교표에 표시됩니다.";

  return (
    <section
      className="v4-workbench v4-cjk-safe"
      aria-labelledby="v4-workbench-title"
      aria-busy={surfaceState === "loading"}
      data-state={surfaceState}
    >
      <header className="panel v4-tab-intro">
        <div className="panel-hd">
          <h2 id="v4-workbench-title" className="panel-hd-title">Workbench · 후보 비교와 의사결정 근거</h2>
        </div>
        <div className="panel-bd">
          <p className="v4-surface-status" role="status" aria-live="polite">{statusText}</p>
          {surfaceState === "error" && (
            <p className="research-empty danger" role="alert">
              연결 오류 때문에 비교 근거가 불완전합니다. 어떤 후보도 승격하지 마세요.
            </p>
          )}
          <p id="v4-workbench-caveat" className="v4-data-caveat">
            수익률·점수는 비교 근거일 뿐 미래 성과를 보장하지 않습니다. 기간, 표본 수, MDD,
            체결 비용과 표본 외 검증을 함께 확인하세요.
          </p>
          <aside className="v4-decision-blocker" aria-label="승격 결정 차단 조건">
            승격·최종 승인·운영 반영은 이 탭에서 실행되지 않습니다. 서버 검증, hard gate,
            코드·근거 해시와 사람의 최종 승인이 없으면 결정은 차단됩니다.
          </aside>
        </div>
      </header>

      <section className="v4-workbench-region v4-cjk-safe" aria-labelledby="v4-workbench-analysis-title">
        <h3 id="v4-workbench-analysis-title" className="stom-section-label">후보 정밀 분석</h3>
        <ResearchProPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </section>

      <section
        className="v4-workbench-region v4-data-region v4-local-scroll v4-cjk-safe"
        aria-labelledby="v4-workbench-compare-title"
        aria-describedby="v4-workbench-caveat"
        data-v4-scroll-owner="workbench-candidate-compare"
        tabIndex={0}
      >
        <h3 id="v4-workbench-compare-title" className="stom-section-label">후보 선택과 비교</h3>
        <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
      </section>

      <section className="v4-workbench-region v4-cjk-safe" aria-labelledby="v4-workbench-hof-title">
        <h3 id="v4-workbench-hof-title" className="stom-section-label">장기 비교 기준과 명예의 전당</h3>
        <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
        <HofInventoryGate compact />
      </section>
    </section>
  );
}

Object.assign(window, { V4Workbench });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Workbench };
