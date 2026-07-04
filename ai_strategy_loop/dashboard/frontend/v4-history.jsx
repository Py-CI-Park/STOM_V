/* v4-history.jsx — V4 "History" 탭: run/gen 아카이브 · Compare · governed 연구 기록.
 *   V2 evolution/records 의 정본(ResearchRecordsPanel + ResearchIndexPage)을 직접 마운트.
 *   V2 규칙 유지: run/gen 재열람·Compare·ResultDetail 은 History 가 단독 소유한다.
 */
// dual-safe ESM import. KEEP each on ONE physical line.
import { ResearchRecordsPanel } from "./research-records-panel.jsx";
import { ResearchIndexPage } from "./dashboard-pages.jsx";

function V4History({ baseUrl, wsStatus, onNavigate }) {
  return (
    <div className="v4-history">
      <ResearchRecordsPanel baseUrl={baseUrl} wsStatus={wsStatus} />
      <ResearchIndexPage baseUrl={baseUrl} onNavigate={onNavigate} />
    </div>
  );
}

Object.assign(window, { V4History });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4History };
