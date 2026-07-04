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
      <ResearchWikiPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
    </div>
  );
}

Object.assign(window, { V4Lab });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Lab };
