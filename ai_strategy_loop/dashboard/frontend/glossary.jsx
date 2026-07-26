/* ResearchGlossaryPanel - user-visible glossary for research metrics and proof status. */
const { useState: useState_g } = React;

const RESEARCH_GLOSSARY_ITEMS = [
  {
    label: "OOS",
    text: "Out-of-sample. 후보 선택과 튜닝에 쓰지 않은 기간 검증이다. OOS disabled는 탐색은 허용하지만 human-level claim blocked 상태다.",
  },
  {
    label: "overfit",
    text: "특정 구간에만 맞춘 과적합이다. 전체 기간 우상향이면 연구 신호로 볼 수 있지만 research signal, not production proof 이다.",
  },
  {
    label: "MDD",
    text: "Maximum Drawdown. 누적 수익곡선의 고점 대비 최대 하락폭이며, 손실 구간의 깊이를 본다.",
  },
  {
    label: "payoff",
    text: "payoff_ratio. 평균 이익을 평균 손실 절댓값으로 나눈 값이다. 승률이 낮아도 큰 이익 거래가 있으면 보완될 수 있다.",
  },
  {
    label: "edge ratio",
    text: "MFE를 MAE 절댓값으로 나눈 진입 품질 지표다. 1보다 높으면 유리한 움직임이 불리한 움직임보다 컸다는 뜻이다.",
  },
  {
    label: "MFE/MAE",
    text: "MFE는 보유 중 최대 유리 움직임, MAE는 최대 불리 움직임이다. 매수 타점과 매도 타이밍을 분리해 본다.",
  },
  {
    label: "slippage",
    text: "백테스트 가정가와 실제 체결가의 차이다. 거래량·호가·시장충격 때문에 실전에서는 반드시 비용으로 반영해야 한다.",
  },
  {
    label: "PBO",
    text: "Probability of Backtest Overfitting. 많은 후보를 시도한 뒤 우연히 좋은 후보를 고른 위험을 추정한다.",
  },
  {
    label: "DSR",
    text: "Deflated Sharpe Ratio. 여러 번의 탐색과 비정규 수익분포를 감안해 Sharpe 계열 성과를 보수적으로 본다.",
  },
  {
    label: "win-day ratio",
    text: "수익이 플러스인 거래일 비율이다. 일별 손익이 복합되는 전략에서 하루 단위 안정성을 확인한다.",
  },
  {
    label: "recent-weighted score",
    text: "2024~2026 같은 최근 데이터에 더 큰 가중을 주는 연구 점수다. 시장 변화 대응용이며 단독 승격 증거는 아니다.",
  },
];

function ResearchGlossaryPanel() {
  const [expanded, setExpanded] = useState_g(false);
  const visibleItems = expanded ? RESEARCH_GLOSSARY_ITEMS : RESEARCH_GLOSSARY_ITEMS.slice(0, 6);

  return (
    <div className="panel research-glossary-panel" data-testid="research-glossary-panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot"></span>지표 사전 <small className="v4s-en">Metric Glossary</small></div>
        <button className="btn tiny" onClick={() => setExpanded(!expanded)}>
          {expanded ? "less" : "all"}
        </button>
      </div>
      <div className="panel-bd">
        <div className="glossary-proof-note">
          research signal, not production proof · human-level claim blocked until multiyear holdout/OOS evidence exists.
        </div>
        <div className="glossary-grid">
          {visibleItems.map((item) => (
            <div className="glossary-card" key={item.label}>
              <div className="glossary-term">{item.label}</div>
              <div className="glossary-text">{item.text}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ResearchGlossaryPanel, RESEARCH_GLOSSARY_ITEMS });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchGlossaryPanel };
