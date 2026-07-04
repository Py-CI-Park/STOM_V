/* v4-audit.jsx — V4 "Audit" 탭: append-only 결정 감사(VerdictPanel) + compact 안전 strip.
 *   안전/감사 정보는 quiet-by-default(작은 strip). VerdictPanel 은 /decisions·/freeze_verdict
 *   등을 자체 fetch 하는 self-contained 원장이다. app.jsx:529-551 인라인 안전 타일을 복제.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { VerdictPanel } from "./dashboard-pages.jsx";

// 연구 전용 경계 — 실거래/주문/브로커 없음(app.jsx 안전 타일과 동일 문구).
const V4_SAFETY_TILES = [
  ["실거래/주문 기능 없음", "No Live Order"],
  ["브로커 로그인 없음", "No Broker Login"],
  ["계좌/자산 연동 없음", "No Account Trading"],
  ["연구 전용", "Research Only"],
  ["Human Approval Gate", "승인 후 Export"],
  ["Append-Only Audit", "불변 감사 로그"],
];

function V4Audit({ baseUrl, onNavigate }) {
  return (
    <div className="v4-audit">
      <section className="v4-safety-strip" data-safety-boundary="v4-research-only">
        {V4_SAFETY_TILES.map(([title, detail]) => (
          <div key={title} className="v4-safety-tile">
            <b>{title}</b>
            <span className="mono">{detail}</span>
          </div>
        ))}
      </section>
      <VerdictPanel baseUrl={baseUrl} onNavigate={onNavigate} />
    </div>
  );
}

Object.assign(window, { V4Audit });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Audit };
