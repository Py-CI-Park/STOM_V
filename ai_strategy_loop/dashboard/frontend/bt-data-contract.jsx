/* QSP7 immutable CSV/DB readiness and provenance surface. */
const _DC_STATUS = {
  available: { label: "사용", tone: "ready" },
  zero_only: { label: "0-only", tone: "zero" },
  missing: { label: "누락", tone: "missing" },
};

function _dcTime(value) {
  const text = String(value == null ? "" : value).padStart(6, "0");
  return text ? `${text.slice(0, 2)}:${text.slice(2, 4)}:${text.slice(4, 6)}` : "—";
}

function BtDataContract({ contract }) {
  if (!contract) return <div className="tp-empty">사전 점검을 실행하면 공식 CSV와 변수 가용성을 확인합니다.</div>;
  const artifact = contract.artifact || {};
  const boundary = contract.boundary || {};
  const cost = contract.cost_policy || {};
  const strategy = contract.strategy || {};
  const groups = contract.groups || [];
  const columns = contract.columns || [];
  return <section className="tp-contract" aria-labelledby="tp-contract-title">
    <header>
      <div><b id="tp-contract-title">데이터 계약</b><small>공식 CSV 원본은 보존하고 연구용 가용성만 계산합니다</small></div>
      <span className="tp-authority diagnostic">진단</span>
    </header>
    <div className="tp-contract-lineage">
      <article><small>CSV schema</small><b>{artifact.schema_variant || "미확인"}</b><span>{artifact.row_count || 0}행 · {artifact.column_count || 0}열</span></article>
      <article><small>전체청산 경계</small><b>{_dcTime(boundary.forced_liquidation_time)}</b><span>{boundary.source || "missing"} · {boundary.confidence || "unknown"}</span></article>
      <article><small>비용 정책</small><b>{Number(cost.round_trip_rate_pct || 0).toFixed(3)}%</b><span>{cost.result_profit_state === "already_net" ? "수익금에 이미 반영" : "상태 미확인"}</span></article>
      <article><small>timeframe</small><b>{contract.timeframe || "—"}</b><span>tick/min 독립 계약</span></article>
    </div>
    <div className="tp-hash-grid">
      <span><small>CSV SHA256</small><code title={artifact.sha256}>{artifact.sha256 || "—"}</code></span>
      <span><small>매수식 hash</small><code title={strategy.buy_sha256}>{strategy.buy_sha256 || "—"}</code></span>
      <span><small>매도식 hash</small><code title={strategy.sell_sha256}>{strategy.sell_sha256 || "—"}</code></span>
    </div>
    <div className="tp-contract-groups">{groups.map(group => <article key={group.group}>
      <b>{group.group}_ 변수</b><strong>{group.available_count}/{group.expected_count}</strong>
      <span>0-only {group.zero_only_count} · missing {group.missing_count}</span>
    </article>)}</div>
    <div className="tp-contract-table" role="table" aria-label="CSV 변수 가용성">
      {columns.map(column => {
        const status = _DC_STATUS[column.status] || _DC_STATUS.missing;
        return <div key={column.name} role="row"><code>{column.name}</code><span className={`tp-col-status ${status.tone}`}>{status.label}</span><small>값 {column.populated_count} · 비0 {column.non_zero_count}</small></div>;
      })}
    </div>
  </section>;
}

Object.assign(window, { BtDataContract });
export { BtDataContract };

