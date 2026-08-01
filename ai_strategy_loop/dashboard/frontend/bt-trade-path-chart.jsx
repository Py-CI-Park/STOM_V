/* QSP7 selected-trade path chart: entry → actual exit → forced liquidation. */
function _tpTime(value) {
  const text = String(value || "").padStart(14, "0");
  return text.length >= 14 ? `${text.slice(8, 10)}:${text.slice(10, 12)}:${text.slice(12, 14)}` : "—";
}

function BtTradePathChart({ episode }) {
  const points = (episode && episode.market_path) || [];
  if (!points.length) return <div className="tp-empty">시장 경로가 없습니다. DB 범위·종목코드 결합 상태를 확인하세요.</div>;
  const prices = points.map(point => Number(point.price)).filter(Number.isFinite);
  const low = Math.min(...prices), high = Math.max(...prices);
  const span = Math.max(1, high - low);
  const width = 900, height = 260, pad = 28;
  const x = index => pad + index * (width - pad * 2) / Math.max(1, points.length - 1);
  const y = price => height - pad - (Number(price) - low) * (height - pad * 2) / span;
  const path = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(point.price).toFixed(1)}`).join(" ");
  const actual = episode.actual_exit || {};
  const actualIndex = Math.max(0, points.findIndex(point => Number(point.timestamp) >= Number(actual.timestamp)));
  const boundaryIndex = points.length - 1;
  return (
    <figure className="tp-chart" aria-label="매수부터 전체청산까지 가격 경로">
      <svg viewBox={`0 0 ${width} ${height}`} role="img">
        <defs><linearGradient id="tpPathFade" x1="0" x2="1"><stop stopColor="#42d6b8"/><stop offset="1" stopColor="#e7b65b"/></linearGradient></defs>
        <line className="tp-zero-line" x1={pad} x2={width - pad} y1={y(episode.buy_price)} y2={y(episode.buy_price)} />
        <path className="tp-price-path" d={path} />
        <line className="tp-marker actual" x1={x(actualIndex)} x2={x(actualIndex)} y1={pad} y2={height - pad} />
        <line className="tp-marker boundary" x1={x(boundaryIndex)} x2={x(boundaryIndex)} y1={pad} y2={height - pad} />
        {points.filter((_, index) => index % Math.max(1, Math.ceil(points.length / 80)) === 0).map((point, sampled) => {
          const index = points.indexOf(point);
          return <circle key={`${point.timestamp}-${sampled}`} cx={x(index)} cy={y(point.price)} r="2"><title>{_tpTime(point.timestamp)} · {Number(point.price).toLocaleString()}원</title></circle>;
        })}
      </svg>
      <figcaption>
        <span><i className="tp-dot entry"/>매수 {Number(episode.buy_price).toLocaleString()}원</span>
        <span><i className="tp-dot actual"/>실제 매도 {_tpTime(actual.timestamp)} · {actual.reason || "미분류"}</span>
        <span><i className="tp-dot boundary"/>전체청산 {_tpTime(episode.forced_liquidation_timestamp)}</span>
      </figcaption>
    </figure>
  );
}

Object.assign(window, { BtTradePathChart });
export { BtTradePathChart, _tpTime };
