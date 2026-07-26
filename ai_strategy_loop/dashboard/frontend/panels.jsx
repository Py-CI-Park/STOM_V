/* Reusable small panels — THIN BARREL (P5.9 decomposition of the former 910-line panels.jsx).
   15개 패널을 관심사별 3개 sibling 으로 분해하고, 이 파일은 배럴로 남아 동일한 window 전역
   재노출 + 동일한 15-심볼 ESM export 표면을 유지한다(소비처 app.jsx · 엔트리 무수정).

     · panels-status.jsx   = ConnBadge · StatusBadge · ResearchCriteriaBanner · ExportStatusBanner
     · panels-config.jsx   = CurrentGenPanel · ActiveStrategyPanel · ActiveConfigPanel · PopulationPanel · MetaPanel
     · panels-analysis.jsx = AutopsyPanel · LineagePanel · HoldoutPanel · CostPanel · FeedbackPanel · ConditionDiscoveryPanel

   동작 불변(순수 코드 이동). stom-ui 전역(fmt* 등)은 sibling 안에서 window 전역으로 소비(절대
   import-변환 금지). 각 sibling 은 자기 Object.assign(window,…) 으로 자기 심볼을 재노출하므로,
   이 배럴의 Object.assign 은 import 한 동일 참조를 한 번 더 보장한다(번들/standalone 양립).
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { ConnBadge, StatusBadge, ResearchCriteriaBanner, ExportStatusBanner } from "./panels-status.jsx";
import { CurrentGenPanel, ActiveStrategyPanel, ActiveConfigPanel, PopulationPanel, MetaPanel } from "./panels-config.jsx";
import { AutopsyPanel, AutopsyFocusCard, LineagePanel, HoldoutPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel } from "./panels-analysis.jsx";

Object.assign(window, { ConnBadge, StatusBadge, CurrentGenPanel, ActiveStrategyPanel, ResearchCriteriaBanner, ActiveConfigPanel, CostPanel, FeedbackPanel, ConditionDiscoveryPanel, AutopsyPanel, AutopsyFocusCard, PopulationPanel, LineagePanel, MetaPanel, HoldoutPanel, ExportStatusBanner });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ActiveConfigPanel, ActiveStrategyPanel, AutopsyFocusCard, AutopsyPanel, ConditionDiscoveryPanel, ConnBadge, CostPanel, CurrentGenPanel, ExportStatusBanner, FeedbackPanel, HoldoutPanel, LineagePanel, MetaPanel, PopulationPanel, ResearchCriteriaBanner, StatusBadge };
