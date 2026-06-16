/* Chart simulation candles — THIN BARREL (P5.3 분해 후).
   기본 엔진: TradingView lightweight-charts(standalone, vendor-lightweight-charts.js).
   window.LightweightCharts 전역이 있으면 그 엔진으로, 없으면(오프라인 등) 순수 SVG 폴백으로 그린다.

   P5.3 — 본 파일은 1,839줄 단일 모듈에서 5개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - sim-chart-utils    : React 별칭 · 상수(_SIM_*) · 클라이언트 지표(_simSma/_simEma/_simRsi/
                            _simMacd/_simVolMa/_simStrengthMa) · 색/세션/호가단위 헬퍼 · window 별칭(_simTimeLabel/_simPriceTick)
     - sim-chart-subpanes : SimHeatStrip · SimRestFlow · SimImbalancePane · SimNetDeltaStrip ·
                            SimRsiPane · SimMacdPane · SimOrderFlowTape · SimFootprint · SimOrderBook
     - sim-chart-shell    : SimChangeGauge · SimSessionRing · SimChartShell(헤더+본문+서브패인+히트 스트립)
     - sim-chart-engines  : SimCandleChartLWC · SimCandleChartSVG · SimCandleChart(엔진 자동선택)
     - sim-signal-log     : SimOverlayChart · SimSignalLog(+ CSV 내보내기 헬퍼)

   이 배럴은 (1) 모든 교차소비 컴포넌트/헬퍼를 sub-file 에서 import 해 (2) 기존과 동일한 window.X 표면을
   Object.assign 으로 재게시하고 (3) 5개 컴포넌트를 named export 한다. 소비처(simulation.jsx 의
   SimOverlayChart/SimSignalLog import, track-z-entry.pilot.js 의 SimCandleChart* import,
   sim-live-chart.jsx 의 window._simRsi/_simMacd/_simEma/_simStrengthMa/_strengthColor 사용)는 무변경으로 동작한다.

   window 전역으로 공유: index.html(번들 엔트리 그래프)에서 simulation.jsx 보다 먼저 로드된다.
   stom-ui(번들) 호스팅 심볼(_simTimeLabel/_simPriceTick)은 window 별칭으로 유지 — import 전환 금지. */
// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { _simTimeLabel, _simPriceTick, _strengthColor, _sessionProgress, _changeColor, _simSma, _simEma, _simRsi, _simMacd, _simVolMa, _simStrengthMa, _SIM_DEFAULT_INDICATORS } from "./sim-chart-utils.jsx";
import { SimHeatStrip, SimRestFlow, SimImbalancePane, SimNetDeltaStrip, SimRsiPane, SimMacdPane, SimOrderFlowTape, SimFootprint, SimOrderBook } from "./sim-chart-subpanes.jsx";
import { SimChangeGauge, SimSessionRing, SimChartShell } from "./sim-chart-shell.jsx";
import { SimCandleChartLWC, SimCandleChartSVG, SimCandleChart } from "./sim-chart-engines.jsx";
import { SimOverlayChart, SimSignalLog } from "./sim-signal-log.jsx";

Object.assign(window, {
  SimCandleChart, SimCandleChartLWC, SimCandleChartSVG,
  SimHeatStrip, SimRestFlow, SimSignalLog,
  SimChangeGauge, SimSessionRing,
  SimOrderFlowTape, SimFootprint, SimOrderBook, SimOverlayChart,
  SimImbalancePane, SimNetDeltaStrip, SimRsiPane, SimMacdPane,
  _simTimeLabel, _simPriceTick, _strengthColor, _sessionProgress, _changeColor,
  _simSma, _simEma, _simRsi, _simMacd, _simVolMa, _simStrengthMa,
  _SIM_DEFAULT_INDICATORS,
});

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { SimCandleChart, SimCandleChartLWC, SimCandleChartSVG, SimOverlayChart, SimSignalLog };
