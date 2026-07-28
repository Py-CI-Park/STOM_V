export function btRequestIsCurrent(requestState, seq, currentKey, expectedKey, signal) {
  return !signal?.aborted && requestState?.seq === seq && currentKey === expectedKey;
}

export function btMetricValue(metrics, summary, key) {
  const source = metrics && typeof metrics === "object" ? metrics : {};
  const fallback = summary && typeof summary === "object" ? summary : {};
  if (Object.prototype.hasOwnProperty.call(source, key)) return source[key];
  if (key === "mdd_pct" && Object.prototype.hasOwnProperty.call(source, "max_drawdown_pct")) return source.max_drawdown_pct;
  if (key === "mdd_pct" && Object.prototype.hasOwnProperty.call(source, "mdd")) return source.mdd;
  // v5.13.2 — 이름이 다른 것만 별칭으로 잇고, 나머지는 fallback 을 그대로 읽는다.
  //   기존에는 별칭 표에 적힌 6개 키만 통과해서, 새로 추가한 지표(자본대비 수익률·
  //   보유시간)는 값이 있어도 카드가 "—" 로 비었고 cagr 은 아예 undefined 로 못 박혀
  //   있었다(CAGR 카드가 한 번도 채워지지 않던 원인).
  const renamed = { mdd_pct: "max_drawdown_pct" };
  if (Object.prototype.hasOwnProperty.call(fallback, key)) return fallback[key];
  const alt = renamed[key];
  if (alt && Object.prototype.hasOwnProperty.call(fallback, alt)) return fallback[alt];
  return undefined;
}
