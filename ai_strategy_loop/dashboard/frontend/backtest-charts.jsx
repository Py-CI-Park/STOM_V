/* Backtest workbench analysis charts — THIN BARREL (P5.1 분해 후).
   순수 SVG 차트(외부 라이브러리 금지)로 /bt/result 의 analysis 묶음을 시각화한다.
   chart.jsx 의 디자인 언어(chart-wrap·chart-grid-line·chart-axis-text·Mini·LegendDot)를 그대로 따른다.

   P5.1 — 본 파일은 2,873줄 단일 모듈에서 5개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - bt-chart-utils      : 공용 헬퍼(포맷·축약·모션·카운트업·게이지·스파크·빈상태·_gpMoney·_btAxisTicks)
     - bt-equity-charts    : BtEquityChart · BtMaeMfeScatter · BtUnderwaterChart · BtRollingChart · BtCumulativeTradesChart
     - bt-distribution-charts: BtDistributionChart · BtHeatmap · BtMonteCarloChart · BtMonthlyCalendar
     - bt-stat-panels      : BtExitReasonPanel · BtContribTable · BtInsightsPanel · BtOrderflowPanel · BtStatTestPanel · BtCompareView
     - bt-gui-parity       : BtMddRandomChart · BtDailyPnlChart · BtHourlyPnlChart · BtWeekdayPnlChart · BtHoldingCurveChart · BtTradeRollingChart · BtGuiParitySection
     - bt-result-area      : BtResultArea(오케스트레이터) + 풀스크린 분석 + 메트릭 카드

   이 배럴은 (1) 모든 교차소비 컴포넌트를 sub-file 에서 import 해 (2) 기존과 동일한 window.X 표면을
   Object.assign 으로 재게시하고 (3) BtResultArea 를 named export 한다. 소비처(backtest.jsx 의
   BtResultArea import, track-z-entry.pilot.js, evolution-analysis 의 window.Bt* 사용)는 무변경으로 동작한다.

   window 전역으로 공유: index.html 에서 backtest.jsx 보다 먼저 로드된다.
*/
// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { BtEquityChart, BtMaeMfeScatter, BtUnderwaterChart, BtRollingChart, BtCumulativeTradesChart } from "./bt-equity-charts.jsx";
import { BtDistributionChart, BtHeatmap, BtMonteCarloChart, BtMonthlyCalendar } from "./bt-distribution-charts.jsx";
import { BtExitReasonPanel, BtContribTable, BtInsightsPanel, BtOrderflowPanel, BtStatTestPanel, BtCompareView } from "./bt-stat-panels.jsx";
import { BtMddRandomChart, BtDailyPnlChart, BtHourlyPnlChart, BtWeekdayPnlChart, BtHoldingCurveChart, BtTradeRollingChart, BtGuiParitySection } from "./bt-gui-parity.jsx";
import { BtResultArea, ResultDetailBody } from "./bt-result-area.jsx";

Object.assign(window, {
  BtEquityChart, BtDistributionChart, BtHeatmap, BtUnderwaterChart, BtResultArea, ResultDetailBody,
  BtMaeMfeScatter, BtExitReasonPanel,
  BtMonteCarloChart, BtOrderflowPanel, BtStatTestPanel, BtCompareView,
  BtRollingChart, BtMonthlyCalendar, BtCumulativeTradesChart,
  BtMddRandomChart, BtDailyPnlChart, BtHourlyPnlChart, BtWeekdayPnlChart,
  BtHoldingCurveChart, BtTradeRollingChart, BtGuiParitySection,
});

// Track Z (PR-3) — dual-safe ESM export (kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { BtResultArea, ResultDetailBody };
