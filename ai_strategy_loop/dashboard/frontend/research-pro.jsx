/* research-pro.jsx — 리서치 프로(풀스크린 분석 워크스페이스). Phase6 트랙 L. THIN BARREL (P5.7 분해 후).
   window.ResearchProPanel 노출. 백테스트 탭처럼 화면 전체를 써서 '유의미한 수치·
   인사이트 도출과 그 시각화'를 한 화면에 모은다(E2). 구성:
     · 상단 셀렉터 바: run 선택 + 세대 선택 + 새로고침 + 프로세스 버튼(E10)
     · 시간대×시가총액 대형 히트맵(E7) — /edge_ratio segments.cross 재사용, 반응형 대형 셀
     · 명예의 전당 프로(E5/E8) — 조건식 펼침 뷰(monospace 매수+매도) + 변수 칩 + '바로 백테스트'
     · Run Compare 프로(E6) — 선택 run/gen 비교 + 행별 '바로 백테스트'
     · 히스토리(E9) — 과거 run 브라우저 + 조건식 + Bt* 차트 상세 시각화(window.BtResultArea)

   제약(in-browser Babel): import/export 금지(Track Z dual-safe 단일라인 ESM 만 허용) ·
   window 전역 컴포넌트 · 파일별 훅 별칭 · 한국어 UI. 기존 파일(backtest.jsx/backtest-charts.jsx)은
   수정하지 않고 window 전역만 재사용한다.

   P5.7 — 본 파일은 1,045줄 단일 모듈에서 3개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - rp-utils    : 훅 별칭 · _rp* fetch/포매터/색상 · _rpOpenWorkbench · _RpVarChips · _RpStrategyCode
     - rp-heatmap  : _RpBigHeatmap/_RpHeatmapGrid · _RpHallOfFame · _RpRunCompare · _RpHistory
                     · _rpActiveStage/_RpProcessFlowOverlay(+ window.ResearchProcessFlowOverlay 게시)
     - rp-panel    : ResearchProPanel(오케스트레이터) · ResearchHeatmapPanel

   이 배럴은 (1) 두 진입 패널을 rp-panel 에서 import 해 (2) 기존과 동일한 window.X 표면을
   Object.assign 으로 재게시하고 (3) 2개 심볼을 기존과 동일하게 named export 한다. 소비처(app.jsx 의
   ProPage·ResearchHeatmapPanel, track-z-entry 의 side-effect import)는 무변경으로 동작한다.
   _RpProcessFlowOverlay → window.ResearchProcessFlowOverlay 게시는 rp-heatmap 에서 처리한다. */

// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definer. KEEP on ONE physical line.
import { ResearchProPanel, ResearchHeatmapPanel } from "./rp-panel.jsx";

Object.assign(window, { ResearchProPanel, ResearchHeatmapPanel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchHeatmapPanel, ResearchProPanel };
