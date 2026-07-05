/* v4-lab.jsx — V4 "Lab" 탭: 대형 탐색 히트맵 + 연구실 종합(자체 fetch).
 *   LabPage 레이아웃 래퍼(사이드바 등)를 스킵하고 내부 패널을 직접 마운트한다.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP each on ONE physical line.
import { ResearchLabPanel } from "./research-lab.jsx";
import { ResearchHeatmapPanel } from "./research-pro.jsx";
import { ResearchWikiPanel } from "./research-wiki.jsx";

function V4Lab({ baseUrl, wsStatus, runId, onNavigate }) {
  return (
    <div className="v4-lab">
      <ResearchHeatmapPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      <ResearchLabPanel
        baseUrl={baseUrl} wsStatus={wsStatus} runId={runId}
        onOpenWorkbench={() => { if (typeof onNavigate === "function") onNavigate("workbench"); }} />
      {/* 연구 위키는 보조 참고(느린 fetch·타임아웃 가능) — V2 처럼 접이식으로 기본 접어
          상시 에러 노출을 막는다. */}
      <details className="evo-group v4-lab-wiki">
        <summary className="evo-group-summary">
          <div className="stom-section-label">연구 위키 · AI 컨텍스트 (선택)</div>
        </summary>
        <div className="evo-group-body">
          <ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        </div>
      </details>
    </div>
  );
}

Object.assign(window, { V4Lab });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Lab };
