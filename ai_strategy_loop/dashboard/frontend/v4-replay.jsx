/* v4-replay.jsx — V4 "Replay" 탭 (graph-first)
 *
 *   SimulationTab(WS /sim/ws 재생 상태머신 + playback 컨트롤 + 캔들차트 + signal log)을
 *   통째 재사용한다. keep-alive(탭 전환에도 언마운트 금지 → WS·재생 위치·종목 선택 유지)는
 *   셸(DashboardV4Shell)이 담당하고, 여기선 wrapping 만 한다. graph-first 는 .v4-replay CSS.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP on ONE physical line.
import { SimulationTab } from "./simulation.jsx";

function V4Replay({ baseUrl, wsStatus }) {
  return (
    <div className="v4-replay">
      <SimulationTab baseUrl={baseUrl} wsStatus={wsStatus} />
    </div>
  );
}

Object.assign(window, { V4Replay });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4Replay };
