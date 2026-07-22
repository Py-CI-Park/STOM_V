export function btRequestIsCurrent(requestState, seq, currentKey, expectedKey, signal) {
  return !signal?.aborted && requestState?.seq === seq && currentKey === expectedKey;
}

export function btMetricValue(metrics, summary, key) {
  const source = metrics && typeof metrics === "object" ? metrics : {};
  const fallback = summary && typeof summary === "object" ? summary : {};
  if (Object.prototype.hasOwnProperty.call(source, key)) return source[key];
  if (key === "mdd_pct" && Object.prototype.hasOwnProperty.call(source, "max_drawdown_pct")) return source.max_drawdown_pct;
  if (key === "mdd_pct" && Object.prototype.hasOwnProperty.call(source, "mdd")) return source.mdd;
  const aliases = {
    trade_count: fallback.trade_count,
    win_rate: fallback.win_rate,
    total_profit_pct: fallback.total_profit_pct,
    total_profit_krw: fallback.total_profit_krw,
    mdd_pct: fallback.max_drawdown_pct,
    cagr: undefined,
  };
  return aliases[key];
}
