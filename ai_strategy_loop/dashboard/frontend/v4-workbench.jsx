/* v4-workbench.jsx — V4 "Workbench" 탭: 후보 정밀 분석 + 후보 비교 + 명예의 전당(자체 fetch).
 *   ProPage 레이아웃 래퍼를 스킵하고 내부 패널을 직접 마운트한다.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP each on ONE physical line.
import { ResearchProPanel } from "./research-pro.jsx";
import { RunComparePanel } from "./run-compare.jsx";
import { HallOfFamePanel } from "./chart.jsx";
import { HofInventoryGate } from "./hof-inventory.jsx";

function V4Workbench({ baseUrl, wsStatus, runId }) {
  return (
    <div className="v4-workbench">
      <ResearchProPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
      <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
      {/* HoF 필드/머지 계약 체크리스트(정적 계약 게이트) — compact.
          긴 HoF/RunCompare 테이블은 v4.css 가 워크벤치 스코프에서 경계 스크롤 처리해
          페이지를 통째로 밀지 않게 한다(공유 컴포넌트 JS 는 무수정). */}
      <HofInventoryGate compact />
    </div>
  );
}

Object.assign(window, { V4Workbench });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Workbench };
