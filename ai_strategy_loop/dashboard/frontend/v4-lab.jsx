/* v4-lab.jsx — V4 Lab: factor/edge evidence with the existing research panels. */
// dual-safe ESM import (esbuild bundle path). KEEP each on ONE physical line.
import { ResearchLabPanel } from "./research-lab.jsx";
import { ResearchHeatmapPanel } from "./research-pro.jsx";
import { ResearchWikiPanel } from "./research-wiki.jsx";

function V4Lab({ baseUrl, wsStatus, runId, onNavigate }) {
  const surfaceState = wsStatus === "connecting"
    ? "loading"
    : (wsStatus === "error" || wsStatus === "closed" || (!baseUrl && runId))
      ? "error"
      : runId
        ? "ready"
        : "empty";
  const statusText = surfaceState === "loading"
    ? "연구 데이터를 연결하고 있습니다."
    : surfaceState === "error"
      ? "연구 데이터 연결을 확인할 수 없습니다. 현재 결과를 근거로 사용하지 마세요."
      : surfaceState === "ready"
        ? `Run ${runId}의 팩터·엣지 근거를 분석합니다.`
        : "선택된 Run이 없습니다. Run을 선택하면 팩터·엣지 근거가 표시됩니다.";

  return (
    <section
      className="v4-lab v4-cjk-safe"
      aria-labelledby="v4-lab-title"
      aria-busy={surfaceState === "loading"}
      data-state={surfaceState}
    >
      <header className="panel v4-tab-intro">
        <div className="panel-hd">
          <h2 id="v4-lab-title" className="panel-hd-title">Lab · 팩터와 엣지 근거 검사</h2>
        </div>
        <div className="panel-bd">
          <p className="v4-surface-status" role="status" aria-live="polite">{statusText}</p>
          {surfaceState === "error" && (
            <p className="research-empty danger" role="alert">
              연결 오류가 해소되기 전에는 빈 결과를 정상 결과로 간주하지 않습니다.
            </p>
          )}
        </div>
      </header>

      <section
        className="v4-lab-region v4-data-region v4-local-scroll v4-cjk-safe"
        aria-labelledby="v4-lab-factor-title"
        aria-describedby="v4-lab-provenance"
        data-v4-scroll-owner="lab-factor-evidence"
        tabIndex={0}
      >
        <h3 id="v4-lab-factor-title" className="stom-section-label">팩터 분포와 탐색 엣지</h3>
        <p id="v4-lab-provenance" className="v4-data-caveat">
          출처: 선택한 Run의 저장된 연구·백테스트 결과. 표본 구간과 표본 외 구간(OOS)을 함께 확인하고,
          상관관계를 인과관계로 해석하지 마세요.
        </p>
        <ResearchHeatmapPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </section>

      <section className="v4-lab-region v4-cjk-safe" aria-labelledby="v4-lab-edge-title">
        <h3 id="v4-lab-edge-title" className="stom-section-label">엣지·상관·안정성 검증</h3>
        <ResearchLabPanel
          baseUrl={baseUrl}
          wsStatus={wsStatus}
          runId={runId}
          onOpenWorkbench={() => { if (typeof onNavigate === "function") onNavigate("workbench"); }}
        />
      </section>

      <details className="evo-group v4-lab-wiki v4-cjk-safe">
        <summary className="evo-group-summary">
          <div className="stom-section-label">연구 위키 · AI 컨텍스트 (선택)</div>
        </summary>
        <div className="evo-group-body">
          <ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        </div>
      </details>
    </section>
  );
}

Object.assign(window, { V4Lab });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Lab };
