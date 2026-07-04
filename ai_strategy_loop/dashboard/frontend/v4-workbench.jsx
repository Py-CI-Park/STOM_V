/* v4-workbench.jsx — V4 "Workbench" 탭: 후보 정밀 분석 + 후보 비교 + 명예의 전당(자체 fetch).
 *   ProPage 레이아웃 래퍼를 스킵하고 내부 패널을 직접 마운트한다.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP each on ONE physical line.
import { ResearchProPanel } from "./research-pro.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { HallOfFamePanel } from "./chart.jsx";

function V4Workbench({ baseUrl, wsStatus, runId }) {
  return (
    <div className="v4-workbench">
      <ResearchProPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
      <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
    </div>
  );
}

Object.assign(window, { V4Workbench });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Workbench };
