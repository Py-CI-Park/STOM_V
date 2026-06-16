/* Chart simulation tab — THIN BARREL (P5.5 분해 후).
   일일 tick/min DB 리플레이 + 조건식 매매 오버레이. /sim/* REST + WS /sim/ws 를 소비한다
   (simulation_api.py·replay_engine.py). 디자인 언어: 다크 테마(var(--bg-1)/var(--line-1)) ·
   mono 라벨 · panel/btn 클래스 재사용.

   P5.5 — 본 파일은 1,495줄 단일 모듈에서 4개 sibling 모듈 + 이 배럴로 분해되었다(동작 불변, 코드 이동만).
     - sim-tab-utils    : 공용 헬퍼/상수(무예외 fetch·WS URL·배속/엔진/분할 상수·localStorage 토글·
                          _simWsBar·_responsiveCols·_simFmtDate/_simFmtNum·_flattenSignals·
                          _SIM_VIEWBAR_LABEL·_SIM_ENGINE_ROWS·_SIM_WATCH_VARS·임계 평가·React 훅)
     - sim-tab-controls : SimControlBar · SimPresetBar · SimMarketMinimap · SimPlaybackBar ·
                          SimEnginePopover · SimViewBar (+ _simTileColor 는 utils)
     - sim-tab-panels   : SimIndicatorCell · SimIndicatorTable · SimLearningPanel ·
                          SimVariableWatch · SimChartByEngine(엔진 디스패처)
     - sim-tab-root     : SimulationTab(탭 루트 오케스트레이터)

   이 배럴은 (1) SimulationTab(루트)을 sub-file 에서 import 해 (2) 기존과 동일한 window.X 표면
   (Object.assign)을 유지하고 (3) SimulationTab 을 named export 한다. 소비처(app.jsx 의
   SimulationTab import)는 무변경으로 동작한다.

   캔들 차트·체결 로그는 simulation-charts.jsx 의 순수 컴포넌트(window 전역)를 쓴다. 외부 차트 라이브러리 금지.
*/
// Track Z (PR-3) — dual-safe ESM import from the in-bundle definer (stripped by `_stripTopLevelEsm` in the concat path). KEEP on ONE physical line.
import { SimulationTab } from "./sim-tab-root.jsx";

Object.assign(window, { SimulationTab });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { SimulationTab };
