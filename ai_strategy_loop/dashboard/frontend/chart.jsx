/* SVG charts for the AI evolution dashboard — THIN BARREL (P5.4 분해 후).
   순수 SVG 차트(외부 라이브러리 금지)로 세대 진화·수익·품질·백테상세·명예의 전당을 시각화한다.
   세대별 graded_score 추이를 비롯한 진화/백테 추이 차트 묶음.

   P5.4 — 본 파일은 1,742줄 단일 모듈에서 4개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - chart-primitives      : LegendDot · Mini · MetricHelpStrip (광범위 소비되는 표현 컴포넌트)
     - chart-equity          : FitnessChart · ProfitChart · QualityTrendChart (세대 진화 추이)
     - chart-backtest-detail : EquityOverlayChart · BacktestDetailChart (fetch 기반 백테 상세/오버랩)
     - chart-hall-of-fame    : HallOfFamePanel · ReferenceGallery

   이 배럴은 (1) 모든 교차소비 컴포넌트를 sub-file 에서 import 해 (2) 기존과 동일한 window.X 표면을
   Object.assign 으로 재게시하고 (3) 9개 심볼을 기존과 동일하게 named export 한다. 소비처(bt-* 모듈의
   LegendDot/Mini/MetricHelpStrip import, evolution-analysis 의 LegendDot/Mini import, app.jsx 의
   FitnessChart 등 import, track-z-entry)는 무변경으로 동작한다.

   stom-ui 전역(window._axisTicks · fmt*)은 sub-file 에서 window. 로 그대로 쓴다(import-convert 금지).
*/
// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { LegendDot, MetricHelpStrip, Mini } from "./chart-primitives.jsx";
import { FitnessChart, ProfitChart, QualityTrendChart } from "./chart-equity.jsx";
import { BacktestDetailChart, EquityOverlayChart } from "./chart-backtest-detail.jsx";
import { HallOfFamePanel, ReferenceGallery } from "./chart-hall-of-fame.jsx";

Object.assign(window, { FitnessChart, ProfitChart, EquityOverlayChart, QualityTrendChart, BacktestDetailChart, HallOfFamePanel, ReferenceGallery });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { BacktestDetailChart, EquityOverlayChart, FitnessChart, HallOfFamePanel, LegendDot, MetricHelpStrip, Mini, ProfitChart, QualityTrendChart };
