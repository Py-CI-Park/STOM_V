/* QSP7 original STOM sell-expression trace for one fixed-entry trade. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_sdt, useEffect: useEffect_sdt } = React;

function _sdtMoney(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toLocaleString()}원` : "—";
}

function BtSellDslTrace({ baseUrl, analysisId, episode }) {
  const [payload, setPayload] = useState_sdt(null);
  const [error, setError] = useState_sdt("");
  const tradeKey = episode?.key && `${episode.key.run_id}:${episode.key.result_row_id}:${episode.key.stock_code}:${episode.key.buy_time}:${episode.key.entry_sequence || 0}`;
  useEffect_sdt(() => {
    if (!baseUrl || !analysisId || !tradeKey) return undefined;
    let alive = true;
    setPayload(null); setError("");
    _btFetchJson(`${baseUrl}/bt/trade-path/sell-dsl-trace?analysis_id=${encodeURIComponent(analysisId)}&trade_key=${encodeURIComponent(tradeKey)}`, 30000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, analysisId, tradeKey]);
  if (!episode) return <div className="tp-empty">거래 경로에서 분석할 거래를 먼저 선택하세요.</div>;
  if (error) return <p className="tp-error">매도식 추적 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">원본 매도식을 tick/min DB 위에서 순서대로 재생 중입니다.</div>;
  if (!payload.available) return <div className="tp-empty">재생 불가 · {payload.reason || "원본 매도식 없음"}</div>;
  const replay = payload.replay || {}, actual = payload.actual_exit || {}, quality = payload.data_quality || {};
  const supported = replay.status === "supported";
  return <section className="tp-sell-trace" aria-labelledby="tp-sell-trace-title">
    <header><div><b id="tp-sell-trace-title">원본 매도식 · 첫 발동 추적</b><small>동일 진입 고정 · {payload.timeframe} 전용 · 전체청산 이전까지만</small></div><span className="tp-authority advisory">자문</span></header>
    <div className={`tp-trace-status ${supported ? "ready" : "blocked"}`}>
      <b>{supported ? "재현 지원" : "정확 재현 중단"}</b>
      <span>{supported ? `DB ${quality.source_db} · 매수 전 ${quality.pre_entry_rows || 0}행 포함` : `미지원: ${(replay.unsupported || []).join(", ") || replay.status}`}</span>
      <small>{supported ? "가상 결과는 후보 선별용이며 공식 백테스트가 정본입니다." : "지원하지 않는 변수·함수는 임의 값으로 추측하지 않습니다."}</small>
    </div>
    <div className="tp-trace-compare">
      <article><small>공식 실제 매도</small><b>{String(actual.timestamp || "—")}</b><span>{actual.reason || "미분류"} · {_sdtMoney(actual.profit_krw)}</span></article>
      <i>→</i>
      <article><small>원본식 DB 재생</small><b>{replay.exit_timestamp || "발동 없음"}</b><span>{replay.condition || "전체청산"} · {_sdtMoney(replay.profit_krw)}</span></article>
      <article className={Number(replay.delta_profit_krw) >= 0 ? "pos" : "neg"}><small>차이 · 자문</small><b>{_sdtMoney(replay.delta_profit_krw)}</b><span>{replay.triggered ? `조건 #${replay.rule_order} 첫 발동` : "전체청산까지 미발동"}</span></article>
    </div>
    <div className="tp-trace-grid">
      <section><h4>조건 경로 · 코드 순서</h4><div className="tp-trace-clauses">{(payload.clauses || []).map((clause, index) => <article key={`${clause.index}-${index}`} className={replay.rule_order === index + 1 ? "hit" : ""}><strong>#{index + 1}</strong><code>{clause.text}</code><small>{(clause.variables || []).join(" · ") || "상수"}</small></article>)}</div></section>
      <section><h4>원본 STOM 매도식</h4><pre>{payload.strategy_sell}</pre><div className="tp-trace-limits">{(payload.limitations || []).map(line => <small key={line}>• {line}</small>)}</div></section>
    </div>
  </section>;
}

Object.assign(window, { BtSellDslTrace });
export { BtSellDslTrace };
