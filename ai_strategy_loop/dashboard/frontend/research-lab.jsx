/* research-lab.jsx — THIN BARREL (P5.6 분해).

   1,273줄 단일 파일을 동작 불변(pure code-move)으로 4개 sibling 모듈로 분해하고, 이 파일은
   배럴(re-export + window 재노출 표면 유지)로 남긴다. 소비처(app.jsx 의 ResearchLabPanel,
   dashboard-pages 의 VerdictPanel 이 쓰는 window.Vdt*, track-z-entry)는 변경 없음.

   분해 구조:
     - rl-vdt-shell.jsx  : P7 공유 표시 블록(VdtPromoteChecklist/VdtAlerts/VdtSummaryLines
                           + _VDT_STATUS_ICON). dashboard-pages 가 window.Vdt* 로 소비하는 정본.
     - rl-analysis.jsx   : correlation/combos 본문 보조 + 차트 프리미티브 + 포맷/빈상태 유틸.
     - rl-validation.jsx : 검증 탭(_ValidationPanel).
     - rl-panel.jsx      : ResearchLabPanel 오케스트레이터 + RESEARCH_TABS + 프로세스 오버레이.

   ORDER 보장: 이 배럴이 sibling 들을 import 하면 각 파일의 top-level Object.assign(window,…) 이
   실행돼 window 표면이 그대로 재구성된다(추가로 아래에서 명시 재노출).
*/
// Track Z — dual-safe ESM imports (the barrel pulls every sub-module so their window publishers run).
import { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines } from "./rl-vdt-shell.jsx";
import { ResearchLabPanel } from "./rl-panel.jsx";

// 원본과 동일한 window 재노출 표면(소비처 불변): Vdt* 공유 셸 + ResearchLabPanel.
Object.assign(window, { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines });
Object.assign(window, { ResearchLabPanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchLabPanel, VdtAlerts, VdtPromoteChecklist, VdtSummaryLines };
