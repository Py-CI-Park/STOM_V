/* v4-replay.jsx — V4 "Replay" 탭 (graph-first)
 *
 *   SimulationTab(WS /sim/ws 재생 상태머신 + playback 컨트롤 + 캔들차트 + signal log)을
 *   통째 재사용한다. keep-alive(탭 전환에도 언마운트 금지 → WS·재생 위치·종목 선택 유지)는
 *   셸(DashboardV4Shell)이 담당하고, 여기선 wrapping 만 한다. graph-first 는 .v4-replay CSS.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { SimulationTab } from "./simulation.jsx";
import { BtReplayTradeContext } from "./bt-replay-trade-context.jsx";

function V4Replay({ baseUrl, wsStatus, active }) {
  const replayReady = wsStatus === "open" || wsStatus === "demo";
  const replayConnecting = wsStatus === "connecting" || wsStatus === "reconnecting";
  const availability = replayReady ? "available" : replayConnecting ? "checking" : "unavailable";
  const connectionLabel = wsStatus === "open"
    ? "사용 가능 · 연결된 Replay 표면"
    : wsStatus === "demo"
      ? "예시 데이터 표면 · 운영 재생과 분리됨"
      : replayConnecting ? "준비 상태 확인 중 · 제어 가능 여부는 아래 표면에서 결정됩니다"
        : "현재 사용 불가 · 연결 상태가 준비되지 않았습니다";

  return (
    <div className="v4-replay">
      <BtReplayTradeContext />
      <section className="panel" aria-labelledby="v4-replay-journey-title">
        <header className="panel-hd">
          <div>
            <div className="stom-section-label" id="v4-replay-journey-title">Replay 작업 흐름</div>
            <div className="mono">실제 시장 시각과 프레임 타임스탬프를 보존하는 프레임 단위 재생</div>
          </div>
        </header>
        <div className="panel-bd">
          <div className="v4-wf" aria-label="Replay 기본 작업 순서">
            <div className={`v4-wf-step ${replayReady ? "done" : "active"}`}>
              <span className="v4-wf-num">1</span>
              <span className="v4-wf-txt"><b>연결 · 데이터 선택</b><span>날짜와 종목을 확인</span></span>
            </div>
            <div className="v4-wf-step">
              <span className="v4-wf-num">2</span>
              <span className="v4-wf-txt"><b>재생 · 일시정지</b><span>시장 흐름을 단계별 관찰</span></span>
            </div>
            <div className="v4-wf-step">
              <span className="v4-wf-num">3</span>
              <span className="v4-wf-txt"><b>정확 탐색 · 배속</b><span>프레임 경계와 신호를 재검토</span></span>
            </div>
          </div>
          <p className="mono" aria-live="polite">{connectionLabel}</p>
          <p className="mono" id="v4-replay-time-contract">
            목적: 기록된 시장 시계열과 신호를 검토하는 읽기 중심 Replay 진입점입니다. 이 래퍼는 데이터 가용성, 재생 제어 또는 결과를 보장하지 않으며 아래 기존 표면의 실제 상태만 표시합니다.
          </p>
          <p className="mono" role="status">가용성 계약: {availability} · websocket={wsStatus || "unknown"}</p>
        </div>
      </section>
      <section
        aria-label="Replay 재생 제어와 시장 시계열"
        aria-describedby="v4-replay-time-contract"
        aria-busy={replayConnecting}
      >
        <SimulationTab baseUrl={baseUrl} wsStatus={wsStatus} active={active} />
      </section>
    </div>
  );
}

Object.assign(window, { V4Replay });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Replay };
