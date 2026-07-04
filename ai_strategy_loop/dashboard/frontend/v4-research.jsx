/* v4-research.jsx — V4 "Research Live" 탭 (graph-first)
 *
 *   기존 V2 컴포넌트를 재배치한다(신규 컴포넌트 없음): 좌측 대형 fitness/equity hero +
 *   우측 slim 관찰성 rail. graph-first 는 .v4-research CSS(대형 chart-wrap)로 달성한다.
 *   모든 하위 컴포넌트는 app.jsx 가 쓰는 것과 동일하며 idle/empty state 를 견딘다.
 */
// dual-safe ESM import (esbuild bundle 경로). KEEP each on ONE physical line.
import { CurrentGenPanel, PopulationPanel } from "./panels.jsx";
import { FitnessChart, ProfitChart, QualityTrendChart, EquityOverlayChart } from "./chart.jsx";
import { EnginePanel } from "./engine.jsx";
import { BestCard, WinnerCard, MergedBestWinnerCard, ApprovalDialog } from "./cards.jsx";
import { PhaseTimeline } from "./phase-detail.jsx";
import { ResearchProPanel } from "./research-pro.jsx";
const { useState: useState_v4r } = React;

function V4ResearchLive({ baseUrl, state, wsStatus, send }) {
  const [approvalOpen, setApprovalOpen] = useState_v4r(false);
  const s = state || {};
  const runId = s.run_id || "";
  const hasData = Array.isArray(s.generations) && s.generations.length > 0;
  // best.gen === winner.gen 이면 병합 카드(app.jsx 규약), 아니면 2카드.
  const merged = s.best && s.winner && s.best.gen === s.winner.gen;

  const onApprove = ({ userBuy, userSell }) => {
    if (!s.winner || typeof send !== "function") { setApprovalOpen(false); return; }
    // final_approval 은 연구 확인과 분리된 human gate(운영 export). WS send.
    send({
      action: "final_approval",
      buy_name: s.winner.buy_name, sell_name: s.winner.sell_name,
      user_buy: userBuy, user_sell: userSell,
    });
    setApprovalOpen(false);
  };

  return (
    <div className="v4-research">
      <div className="v4-research-hero">
        {!hasData && (
          <div className="v4-idle-strip mono">
            연구 대기 · 라이브 데이터 없음 — 세대가 진행되면 아래 차트가 실시간으로 채워집니다.
          </div>
        )}
        {/* 주인공: 대형 적합도 곡선 */}
        <div className="v4-hero-primary">
          <FitnessChart state={s} target={1.0} />
        </div>
        <div className="v4-research-row2">
          <ProfitChart state={s} targetPct={0} />
          <QualityTrendChart state={s} />
        </div>
        {/* 라이브 자본곡선(자체 fetch) + 엔진 메트릭·per-gen 백테 차트 */}
        <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        <EnginePanel state={s} wsStatus={wsStatus} />
        <PhaseTimeline state={s} />
        {/* 실시간 연구 관찰성(자체 fetch): 선택 바 + HoF + 프로세스 오버레이 */}
        <ResearchProPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </div>

      <aside className="v4-research-rail">
        <CurrentGenPanel state={s} />
        {merged ? (
          <MergedBestWinnerCard
            best={s.best} winner={s.winner}
            onApprove={() => setApprovalOpen(true)} onViewCode={() => {}} />
        ) : (
          <>
            <BestCard best={s.best} onViewCode={() => {}} />
            <WinnerCard winner={s.winner}
              onApprove={() => setApprovalOpen(true)} onViewCode={() => {}} />
          </>
        )}
        <PopulationPanel state={s} wsStatus={wsStatus} />
      </aside>

      {/* Human approval gate — 연구 확인과 분리된 명시적 승인(운영 export) */}
      <ApprovalDialog
        winner={approvalOpen ? s.winner : null}
        onClose={() => setApprovalOpen(false)}
        onConfirm={onApprove} />
    </div>
  );
}

Object.assign(window, { V4ResearchLive });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4ResearchLive };
