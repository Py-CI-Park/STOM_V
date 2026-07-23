/* Shared evidence-chart contract: metadata and bounded source rows remain available
 * without relying on canvas, SVG hover, or colour alone. */
const { useState: useState_cf } = React;

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

function _chartColumns(columns, rows) {
  if (Array.isArray(columns) && columns.length) {
    return columns.map(column => typeof column === "string"
      ? { key: column, label: column }
      : { key: column.key, label: column.label || column.key }).filter(column => column.key);
  }
  return Array.from(new Set(rows.flatMap(row => Object.keys(row)))).map(key => ({ key, label: key }));
}

function _chartRowsWindow(rows, maxRows) {
  const limit = Math.max(1, Number.isFinite(maxRows) ? Math.floor(maxRows) : 40);
  if (rows.length <= limit) return rows;
  const firstCount = Math.ceil(limit / 2);
  return rows.slice(0, firstCount).concat(rows.slice(-(limit - firstCount)));
}

function ChartFrame({
  title, unit, period, sampleCount, freshness, threshold, source, rows,
  status, columns, rowKey, validator, maxRows = 40, children,
}) {
  const [tableOpen, setTableOpen] = useState_cf(false);
  const rowInput = Array.isArray(rows) ? rows : [];
  const isObjectRow = row => row != null && typeof row === "object" && !Array.isArray(row);
  const isValidRow = row => isObjectRow(row) && (!validator || validator(row) === true);
  const validRows = rowInput.filter(isValidRow);
  const invalidCount = Array.isArray(rows) ? rows.length - validRows.length : 0;
  const derivedState = rows == null ? "loading"
    : !Array.isArray(rows) || invalidCount ? "malformed"
      : validRows.length ? "ready" : "empty";
  const requestedState = ["loading", "ready", "empty", "stale", "malformed", "error"].includes(status) ? status : null;
  const state = derivedState === "malformed" ? "malformed" : (requestedState || derivedState);
  const displayRows = _chartRowsWindow(validRows, maxRows);
  const tableColumns = _chartColumns(columns, validRows);
  const message = {
    loading: "차트 원본 데이터를 불러오는 중입니다.",
    empty: "표시할 원본 데이터가 없습니다.",
    stale: "차트 데이터의 최신 상태를 확인할 수 없습니다. 표시된 값은 마지막 수신값입니다.",
    malformed: invalidCount
      ? `차트 원본 데이터 ${invalidCount}건의 형식 또는 필수 값이 올바르지 않습니다.`
      : "차트 원본 데이터 형식이 올바르지 않아 값을 표시하지 않습니다.",
    error: "차트 원본 데이터를 불러오지 못했습니다.",
  }[state];
  const rowId = (row, index) => typeof rowKey === "function" ? rowKey(row, index)
    : typeof rowKey === "string" && row[rowKey] != null ? row[rowKey]
      : row.id ?? row.gen_no ?? row.evaluation_id ?? index;

  return (
    <div className={`chart-frame chart-frame-${state}`} aria-busy={state === "loading"}>
      <ChartMeta title={title} unit={unit} period={period} sampleCount={sampleCount}
        freshness={freshness} threshold={threshold} source={source} />
      {state !== "ready" && <p className="chart-frame-state" role="status">{message}</p>}
      {!["loading", "malformed", "error"].includes(state) && children}
      <details className="chart-frame-fallback" onToggle={event => setTableOpen(event.currentTarget.open)}>
        <summary>{title} 원본값 표 · {validRows.length}건{displayRows.length < validRows.length ? ` 중 처음/마지막 ${displayRows.length}건 표시` : ""}</summary>
        {tableOpen && (validRows.length && tableColumns.length ? (
          <div className="chart-frame-table-wrap">
            <table>
              <thead><tr>{tableColumns.map(column => <th key={column.key} scope="col">{column.label}</th>)}</tr></thead>
              <tbody>{displayRows.map((row, index) => (
                <tr key={rowId(row, index)}>
                  {tableColumns.map(column => <td key={column.key}>{_chartText(row[column.key], "—")}</td>)}
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <p>{message}</p>)}
      </details>
    </div>
  );
}

export { ChartFrame, ChartMeta };
