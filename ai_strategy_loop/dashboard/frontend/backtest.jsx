/* Backtest workbench tab — THIN BARREL (P5.2 분해 후).
   GUI 백테스트의 웹 이관. /bt/* REST 계약을 소비한다(backtest_api.py·backtest_analysis.py).
   디자인 언어: 다크 테마(var(--bg-1)/var(--line-1)) · mono 라벨 · panel/btn 클래스 재사용.

   P5.2 — 본 파일은 2,209줄 단일 모듈에서 6개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - bt-tab-utils        : 공용 헬퍼/상수(무예외 fetch·WS URL·잡 배지·모드 라벨/팁·기간 예시·
                             _btElapsed·_btNum·_BtRowDetail·_BT_OVERLAY_COLORS·스윕 카운트·_pfFmtMoney·React 훅)
     - bt-tab-library      : BtLibraryPanel · BtVarChips · BtCodeEditor · BtDualEditor
     - bt-tab-run          : _SweepParamBuilder · BtRunPanel · BtResultLibrary
     - bt-tab-mode-results : BtWfoTable · BtSweepTable · BtModeResultPanel
     - bt-tab-analysis     : BtOverlayCurves · BtSplitGrid · BtOverlayPanel · BtCollapsible ·
                             BtEvoSelector · BtPortfolioCurve · BtPortfolioHeatmap · BtPortfolioPanel
     - bt-tab-root         : BacktestTab(탭 루트 오케스트레이터)

   이 배럴은 (1) BacktestTab(루트)·BtVarChips 를 sub-file 에서 import 해 (2) 기존과 동일한 window.X
   표면(Object.assign)을 유지하고 (3) BacktestTab·BtVarChips 를 named export 한다. 소비처(app.jsx 의
   BacktestTab import, track-z-entry.pilot 의 BtVarChips import, research-pro 의 window.BtVarChips 사용)는
   무변경으로 동작한다.

   결과·분석 영역(BtResultArea + 메트릭 카드 + 차트)은 backtest-charts.jsx 에 있으며 window 전역으로
   공유된다(index.html 에서 이 파일보다 먼저 로드). 외부 차트 라이브러리 금지.
*/
// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definers (stripped by `_stripTopLevelEsm` in the concat path). KEEP each on ONE physical line.
import { BacktestTab } from "./bt-tab-root.jsx";
import { BtVarChips } from "./bt-tab-library.jsx";

Object.assign(window, { BacktestTab });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { BacktestTab, BtVarChips };
