/* Shared chart contract: metadata stays visible and the underlying values remain available
 * without relying on canvas, SVG hover, or colour alone. */
function _chartText(value, missing = "미발행") {
  return value == null || value === "" ? missing : String(value);
}

function ChartMeta({ title, unit, period, sampleCount, freshness, threshold, source }) {
  const fields = [
    ["단위", unit],
    ["기간", period],
    ["표본", typeof sampleCount === "number" ? `${sampleCount}건` : sampleCount],
    ["신선도", freshness],
    ["기준", threshold],
    ["출처", source],
  ];
  return (
    <dl className="chart-meta" aria-label={`${title} 차트 메타데이터`}>
      {fields.map(([label, value]) => (
        <div className="chart-meta-item" key={label}>
          <dt>{label}</dt><dd>{_chartText(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function ChartFrame({ title, unit, period, sampleCount, freshness, threshold, source, rows = [], status, maxRows = 200, children }) {
  const validRows = Array.isArray(rows) ? rows.filter(row => row && typeof row === "object") : [];
  const displayRows = validRows.slice(0, Math.max(1, maxRows));
  const state = status || (validRows.length ? "ready" : "empty");
  const message = state === "malformed"
    ? "차트 원본 데이터 형식이 올바르지 않아 값을 표시하지 않습니다."
    : state === "stale"
      ? "차트 데이터가 최신 상태인지 확인할 수 없습니다. 표시된 값은 마지막 수신값입니다."
      : "표시할 원본 데이터가 없습니다.";
  const columns = Array.from(new Set(validRows.flatMap(row => Object.keys(row))));

  return (
    <div className={`chart-frame chart-frame-${state}`}>
      <ChartMeta title={title} unit={unit} period={period} sampleCount={sampleCount}
        freshness={freshness} threshold={threshold} source={source} />
      {state !== "ready" && <p className="chart-frame-state" role="status">{message}</p>}
      {state !== "malformed" && children}
      <details className="chart-frame-fallback">
        <summary>{title} 원본값 표 · {validRows.length}건{displayRows.length < validRows.length ? ` 중 ${displayRows.length}건 표시` : ""}</summary>
        {validRows.length && columns.length ? (
          <div className="chart-frame-table-wrap">
            <table>
              <thead><tr>{columns.map(key => <th key={key} scope="col">{key}</th>)}</tr></thead>
              <tbody>{displayRows.map((row, index) => (
                <tr key={row.id || row.gen_no || row.evaluation_id || index}>
                  {columns.map(key => <td key={key}>{_chartText(row[key], "—")}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p>{message}</p>}
      </details>
    </div>
  );
}

export { ChartFrame, ChartMeta };
