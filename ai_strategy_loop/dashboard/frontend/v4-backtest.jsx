/* v4-backtest.jsx — V4 "Backtest" 탭 (graph-first)
 *
 *   BacktestTab(self-contained orchestrator: run 패널 + edit/result 서브탭, /bt/* fetch)을
 *   통째 재사용한다. lifted state 때문에 sub-panel 을 쪼개지 않는다(계획 제약).
 *   graph-first 는 .v4-backtest CSS 로 결과 차트를 키운다(컴포넌트 수정 없음).
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { BacktestTab } from "./backtest.jsx";
import { BtTradePathTab } from "./bt-trade-path-tab.jsx";

function _confirmBacktestDanger(event) {
  const target = event.target;
  const button = target && typeof target.closest === "function" ? target.closest("button.btn.danger") : null;
  if (!button || !/중지|취소/.test(button.textContent || "")) return;
  if (window.confirm("실행 중인 백테스트를 취소하시겠습니까? 완료되지 않은 결과는 분석할 수 없습니다.")) return;
  event.preventDefault();
  event.stopPropagation();
}

function V4Backtest({ baseUrl, wsStatus, onNavigate }) {
  const connected = wsStatus === "open" || wsStatus === "connected";
  return (
    <section className="v4-backtest" aria-labelledby="v4-backtest-heading">
      <h2 id="v4-backtest-heading" className="panel-hd-title">Backtest · 전략 검증</h2>
      <ol className="v4-backtest-journey" aria-label="백테스트 실행 순서">
        <li>전략 선택</li><li>사전 점검</li><li>실행 또는 취소</li><li>결과 분석</li>
      </ol>
      <p className={"v4-backtest-status " + (connected ? "ready" : "blocked")} role="status" aria-live="polite">
        {connected ? "실행 준비 · 전략과 기간을 확인하세요" : "연결 확인 필요 · 실행 제어가 비활성화될 수 있습니다"}
      </p>
      <div className="v4-backtest-workspace" role="region" aria-label="백테스트 선택, 실행, 취소 및 결과"
           onClickCapture={_confirmBacktestDanger}>
        <BacktestTab baseUrl={baseUrl} wsStatus={wsStatus} />
      </div>
      <BtTradePathTab baseUrl={baseUrl} onNavigate={onNavigate} />
    </section>
  );
}

Object.assign(window, { V4Backtest });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Backtest };
