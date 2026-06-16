/* rl-vdt-shell.jsx — P7 freeze_verdict 공유 표시 블록(research-lab.jsx 에서 분리, byte-identical 이전).

   research-lab(_ValidationPanel)·dashboard-pages(VerdictPanel) 두 패널이 동일한 PROMOTE
   체크리스트·경보·요약줄을 단일 정본 컴포넌트로 소비한다. research-lab 이 ORDER 상 dashboard-pages
   보다 앞서므로 여기서 정의하고 window-export → dashboard-pages 는 window.* 로 소비한다.
   (P5.6 분해: 정의 파일만 research-lab.jsx → rl-vdt-shell.jsx 로 옮겼고, 내용은 그대로다.)
   세 컴포넌트는 stateless(JSX 만) 이므로 React 훅 별칭은 필요 없다 — JSX 트랜스폼만 의존.
*/
/* ─────────────────────────────────────────────────────────────────────────────
 * P7(2026-06-15) — freeze_verdict 공유 표시 블록.
 *   research-lab(_ValidationPanel)·dashboard-pages(VerdictPanel) 두 패널이 동일한
 *   PROMOTE 체크리스트·경보·요약줄을 각자 인라인 렌더링하던 것을 단일 정본 컴포넌트로
 *   통합한다(필드 무손실). research-lab 이 ORDER 상 dashboard-pages 보다 앞서므로 여기서
 *   정의하고 window-export → dashboard-pages 는 window.* 로 소비한다.
 *   정본 스타일: fontSize 12, width:100%, alert 색 var(--amber)(토큰), 빈 상태 메시지,
 *   상태→아이콘은 전역 ICON 비의존(컴포넌트-로컬 맵).
 *   데이터 계약: v.promote_checklist[].{item,status,detail}, v.alerts[], v.lines[].
 * ──────────────────────────────────────────────────────────────────────────── */
const _VDT_STATUS_ICON = { pass: "✅", warn: "⚠️", fail: "❌", pending: "⏳" };

function VdtPromoteChecklist({ v }) {
  const checks = (v && v.promote_checklist) || [];
  if (checks.length === 0) {
    return (
      <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>
        PROMOTE 체크리스트: 데이터 없음
      </div>
    );
  }
  return (
    <table className="mono" style={{ fontSize: 12, width: "100%", marginBottom: 8 }}>
      <thead><tr><th>PROMOTE 조건</th><th>상태</th><th>근거</th></tr></thead>
      <tbody>
        {checks.map((c, i) => (
          <tr key={"vdtc" + i}>
            <td>{c.item}</td>
            <td>{_VDT_STATUS_ICON[c.status] || "?"}</td>
            <td>{c.detail || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function VdtAlerts({ v }) {
  const alerts = (v && v.alerts) || [];
  return alerts.map((a, i) => (
    <div key={"vdta" + i} className="mono" style={{ fontSize: 12, color: "var(--amber)" }}>⚠️ {a}</div>
  ));
}

function VdtSummaryLines({ v }) {
  const lines = (v && v.lines) || [];
  return lines.map((l, i) => (
    <div key={"vdtl" + i} className="mono" style={{ fontSize: 12 }}>{l}</div>
  ));
}

Object.assign(window, { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines, _VDT_STATUS_ICON };
