/* v4-backtest.jsx — V4 "Backtest" 탭 (graph-first)
 *
 *   BacktestTab(self-contained orchestrator: run 패널 + edit/result 서브탭, /bt/* fetch)을
 *   통째 재사용한다. lifted state 때문에 sub-panel 을 쪼개지 않는다(계획 제약).
 *   graph-first 는 .v4-backtest CSS 로 결과 차트를 키운다(컴포넌트 수정 없음).
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { BacktestTab } from "./backtest.jsx";

function V4Backtest({ baseUrl, wsStatus }) {
  return (
    <div className="v4-backtest">
      <BacktestTab baseUrl={baseUrl} wsStatus={wsStatus} />
    </div>
  );
}

Object.assign(window, { V4Backtest });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Backtest };
