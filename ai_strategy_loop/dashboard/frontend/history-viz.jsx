/* history-viz.jsx — G002 정본 대시보드 고도화: A/B 쌍대비교 · 셀 히트맵 · 홀드아웃 퍼널.
 * condition_history_v1 read model 위에 얹는 탐색용 뷰. /history/ab-pairs, /history/index,
 * /history/detail 만 호출하고 클라이언트에서 조건식을 재구성하지 않는다(서버가 내려준 값만 표시).
 * 서버 슬라이스(ab-pairs, index의 series/ab_role/gate_passed_count)가 병렬 진행 중이므로
 * 모든 optional 필드는 방어적으로 소비한다 — 필드 부재 시 빈 상태로 흡수하고 절대 추측하지 않는다.
 * 승급/검증(promotion/validation) 신호를 절대 발신하지 않는다 — 탐색용 표시만 한다. */
const {
  useState: useState_hv,
  useEffect: useEffect_hv,
  useCallback: useCallback_hv,
} = React;

function _hvNum(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  return Number(value).toLocaleString();
}

function _hvMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return sign + Math.round(n).toLocaleString();
}

function _hvPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  return Number(value).toFixed(2) + "%";
}

function _hvNegColor(value) {
  if (value == null || Number.isNaN(Number(value))) return "var(--ink-2)";
  return Number(value) < 0 ? "var(--red)" : "var(--ink-0)";
}

function _hvMetric(row, key) {
  const m = (row && row.metrics) || {};
  return m[key] != null ? m[key] : null;
}

// metrics 키 이름이 발행기 세대(campaign은 trades, loop_run은 trade_count)에 따라 달라지므로
// 후보 키를 순서대로 시도한다 — 존재하는 키만 읽고 없는 키는 절대 만들어내지 않는다.
function _hvMetricAny(row, keys) {
  const m = (row && row.metrics) || {};
  for (const k of keys) {
    if (m[k] != null) return m[k];
  }
  return null;
}

function _hvFetchJson(url, timeoutMs) {
  // 전체 인덱스는 서버 측 트리 빌드로 수 초가 걸릴 수 있어 기본 30초로 잡는다.
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 30000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

// cursor 기반 전체 수집: /history/detail을 limit=100으로 요청하고 next_cursor를 따라가며
// 안전 상한(50페이지)까지 모든 행을 모은다. 서버가 next_cursor를 더는 주지 않으면 중단한다.
function _hvFetchAllPages(url, timeoutMs) {
  const MAX_PAGES = 50;
  const sep = url.includes("?") ? "&" : "?";
  const base = url + sep + "limit=100";
  const step = (cursor, acc, page) => {
    const pageUrl = base + (cursor ? "&cursor=" + encodeURIComponent(cursor) : "");
    return _hvFetchJson(pageUrl, timeoutMs).then(j => {
      const rows = Array.isArray(j && j.rows) ? j.rows : [];
      const merged = acc.concat(rows);
      const next = j && j.next_cursor ? j.next_cursor : null;
      if (next && page < MAX_PAGES) return step(next, merged, page + 1);
      return merged;
    });
  };
  return step(null, [], 1);
}

// 서버가 loop_run 평가 행에는 gate_passed(bool)를 additive로 내려준다(campaign 행은 원천 데이터가
// 없어 필드 자체가 없다). boolean으로 존재할 때만 판정하고, 부재 시 정직하게 null(→"—")을
// 반환한다 — 휴리스틱 추론 금지.
function _hvGatePassed(row) {
  return row && typeof row.gate_passed === "boolean" ? row.gate_passed : null;
}

function _hvGateBadge(row) {
  const passed = _hvGatePassed(row);
  if (passed == null) return <span className="badge">{"\u2014"}</span>;
  return <span className={"badge " + (passed ? "ok" : "err")}>{passed ? "pass" : "reject"}</span>;
}

// label의 "시간창 × 시총" 문자열을 두 축으로 분리한다(rp-heatmap.jsx의 분리 규칙과 동일 구분자
// 집합). 분리 불가한 label은 히트맵 축으로 쓰지 않는다(추측 금지 — 서버가 내려준 문자열만 사용).
function _hvSplitAxisLabel(label) {
  const text = String(label || "").trim();
  if (!text) return null;
  for (const sep of ["\u00d7", " x ", " X ", "|", "/", "\u00b7", " - "]) {
    if (text.includes(sep)) {
      const parts = text.split(sep);
      const a = parts[0] ? parts[0].trim() : "";
      const b = parts.slice(1).join(sep).trim();
      if (a && b) return [a, b];
    }
  }
  return null;
}

function _HvEmpty({ children }) {
  return <div className="research-empty">{children}</div>;
}

function _HvError({ err, onRetry }) {
  if (!err) return null;
  return (
    <div className="research-empty danger">
      {err}
      {onRetry && <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={onRetry}>재시도</button></div>}
    </div>
  );
}

/* ── B-3: AbPairCompareView — series의 legacy/typed 발행기 쌍을 세대별로 나란히 비교. ── */
function AbPairCompareView({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [series, setSeries] = useState_hv(""); // 기본값 없음 — placeholder(예: abmain0716f)로만 안내
  const [pairsAvailable, setPairsAvailable] = useState_hv(null); // null=미조회
  const [pairs, setPairs] = useState_hv([]);
  const [pairsLoading, setPairsLoading] = useState_hv(false);
  const [pairsErr, setPairsErr] = useState_hv("");
  const [selectedPair, setSelectedPair] = useState_hv("");

  const [legacyRows, setLegacyRows] = useState_hv({ loading: false, err: "", rows: [] });
  const [typedRows, setTypedRows] = useState_hv({ loading: false, err: "", rows: [] });

  const loadPairs = useCallback_hv(() => {
    if (isDemo || !baseUrl || !series.trim()) return;
    setPairsLoading(true);
    setPairsErr("");
    _hvFetchJson(baseUrl + "/history/ab-pairs?series=" + encodeURIComponent(series.trim()), 8000)
      .then(j => {
        const items = Array.isArray(j && j.items) ? j.items : [];
        setPairsAvailable(!!(j && j.available));
        setPairs(items);
        setSelectedPair(items.length ? items[0].pair : "");
      })
      .catch(e => {
        setPairsErr(String(e));
        setPairsAvailable(false);
        setPairs([]);
        setSelectedPair("");
      })
      .finally(() => setPairsLoading(false));
  }, [baseUrl, isDemo, series]);

  useEffect_hv(() => {
    loadPairs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const current = pairs.find(p => p.pair === selectedPair) || null;

  const loadSide = useCallback_hv((researchId, setter) => {
    if (isDemo || !baseUrl || !researchId) {
      setter({ loading: false, err: "", rows: [] });
      return;
    }
    setter(prev => ({ ...prev, loading: true, err: "" }));
    _hvFetchAllPages(
      baseUrl + "/history/detail?research_id=" + encodeURIComponent(researchId) + "&section=evaluations"
    )
      .then(rows => setter({ loading: false, err: "", rows }))
      .catch(e => setter({ loading: false, err: String(e), rows: [] }));
  }, [baseUrl, isDemo]);

  useEffect_hv(() => {
    if (!current) {
      setLegacyRows({ loading: false, err: "", rows: [] });
      setTypedRows({ loading: false, err: "", rows: [] });
      return;
    }
    loadSide(current.legacy_research_id, setLegacyRows);
    loadSide(current.typed_research_id, setTypedRows);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current && current.pair]);

  const renderSide = (title, gatePassedFlag, side) => (
    <div style={{ flex: "1 1 260px", minWidth: 260 }}>
      <div className="stat-label" style={{ marginBottom: 6 }}>
        {title}{typeof gatePassedFlag === "boolean" && (
          <span className={"badge " + (gatePassedFlag ? "ok" : "err")} style={{ marginLeft: 6 }}>
            gate {gatePassedFlag ? "pass" : "reject"}
          </span>
        )}
      </div>
      {side.err && <_HvError err={side.err} />}
      {!side.err && side.rows.length === 0 && !side.loading && (
        <_HvEmpty>evaluation 데이터 없음</_HvEmpty>
      )}
      {side.loading && <_HvEmpty>조회중…</_HvEmpty>}
      {side.rows.length > 0 && (
        <div style={{ overflowX: "auto" }}>
          <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
            <thead>
              <tr style={{ color: "var(--ink-3)" }}>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>#</th>
                <th style={{ textAlign: "left", padding: "6px 8px" }}>gate</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>거래수</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>MDD</th>
                <th style={{ textAlign: "right", padding: "6px 8px" }}>손익</th>
              </tr>
            </thead>
            <tbody>
              {side.rows.map((row, idx) => (
                <tr key={row.evaluation_id || idx} style={{ borderTop: "1px solid var(--line-1)" }}>
                  <td style={{ padding: "6px 8px" }}>{idx + 1}</td>
                  <td style={{ padding: "6px 8px" }}>{_hvGateBadge(row)}</td>
                  <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hvNum(_hvMetricAny(row, ["trade_count", "trades"]))}</td>
                  <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hvPct(_hvMetric(row, "mdd"))}</td>
                  <td style={{ padding: "6px 8px", textAlign: "right", color: _hvNegColor(_hvMetric(row, "profit")) }}>
                    {_hvMoney(_hvMetric(row, "profit"))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          A/B 쌍대비교 (legacy · typed)
        </div>
        <button className="btn ghost sm" onClick={loadPairs} disabled={isDemo || pairsLoading}>
          {pairsLoading ? "조회중…" : "\u21bb 새로고침"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {isDemo && <_HvEmpty>Demo mode — 백엔드 연결 시 A/B 쌍대비교가 표시됩니다.</_HvEmpty>}
        {!isDemo && (
          <React.Fragment>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                className="mono"
                style={{ flex: "1 1 200px", padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)" }}
                placeholder="series (예: abmain0716f)"
                value={series}
                onChange={e => setSeries(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") loadPairs(); }}
              />
              {pairs.length > 0 && (
                <select
                  className="mono"
                  style={{ padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)" }}
                  value={selectedPair}
                  onChange={e => setSelectedPair(e.target.value)}
                >
                  {pairs.map(p => <option key={p.pair} value={p.pair}>{p.pair}</option>)}
                </select>
              )}
              <button className="btn ghost sm" onClick={loadPairs} disabled={pairsLoading}>
                {pairsLoading ? "조회중…" : "조회"}
              </button>
            </div>
            <_HvError err={pairsErr} onRetry={loadPairs} />
            {!pairsErr && pairsAvailable === false && (
              <_HvEmpty>이 series의 A/B 쌍 데이터가 없습니다(발행기 병렬 슬라이스 대기 중일 수 있음)</_HvEmpty>
            )}
            {!pairsErr && pairsAvailable && pairs.length === 0 && (
              <_HvEmpty>이 series에 발행된 A/B 쌍이 없습니다</_HvEmpty>
            )}
            {current && (
              <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                {current.legacy_research_id
                  ? renderSide("legacy · " + current.legacy_research_id, current.legacy_gate_passed, legacyRows)
                  : <_HvEmpty>이 쌍은 legacy 판이 없습니다(typed만 발행됨)</_HvEmpty>}
                {current.typed_research_id
                  ? renderSide("typed · " + current.typed_research_id, current.typed_gate_passed, typedRows)
                  : <_HvEmpty>이 쌍은 typed 판이 없습니다(legacy만 발행됨)</_HvEmpty>}
              </div>
            )}
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

/* ── B-3: CellHeatmap — campaign evaluations의 시간창×시총 셀 히트맵. ── */
function CellHeatmap({ baseUrl, wsStatus, preferredResearchId }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [campaigns, setCampaigns] = useState_hv([]);
  const [campaignsLoading, setCampaignsLoading] = useState_hv(false);
  const [campaignsErr, setCampaignsErr] = useState_hv("");
  const [selected, setSelected] = useState_hv("");

  const [rows, setRows] = useState_hv([]);
  const [rowsLoading, setRowsLoading] = useState_hv(false);
  const [rowsErr, setRowsErr] = useState_hv("");
  const [metricMode, setMetricMode] = useState_hv("profit");

  const loadCampaigns = useCallback_hv(() => {
    if (isDemo || !baseUrl) return;
    setCampaignsLoading(true);
    setCampaignsErr("");
    _hvFetchJson(baseUrl + "/history/index?limit=50&source_kind=campaign", 30000)
      .then(j => {
        const items = Array.isArray(j && j.items) ? j.items : [];
        setCampaigns(items);
        setSelected(prev => (
          preferredResearchId && preferredResearchId.startsWith("campaign:") && items.some(item => item.research_id === preferredResearchId)
            ? preferredResearchId
            : (prev || (items.length ? items[0].research_id : ""))
        ));
      })
      .catch(e => { setCampaignsErr(String(e)); setCampaigns([]); })
      .finally(() => setCampaignsLoading(false));
  }, [baseUrl, isDemo, preferredResearchId]);

  useEffect_hv(() => {
    loadCampaigns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect_hv(() => {
    if (preferredResearchId && preferredResearchId.startsWith("campaign:") && campaigns.some(c => c.research_id === preferredResearchId)) {
      setSelected(preferredResearchId);
    }
  }, [preferredResearchId, campaigns]);

  const loadRows = useCallback_hv(() => {
    if (isDemo || !baseUrl || !selected) {
      setRows([]);
      return;
    }
    setRowsLoading(true);
    setRowsErr("");
    _hvFetchAllPages(
      baseUrl + "/history/detail?research_id=" + encodeURIComponent(selected) + "&section=evaluations"
    )
      .then(rows => setRows(rows))
      .catch(e => { setRowsErr(String(e)); setRows([]); })
      .finally(() => setRowsLoading(false));
  }, [baseUrl, isDemo, selected]);

  useEffect_hv(() => {
    loadRows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  // 캠페인 companion 셀 메트릭 키는 net_profit/win_rate(stage1 분해 계약),
  // loop_run 행은 profit/total_profit_pct — 후보 키로 둘 다 지원한다.
  const hasProfit = rows.some(r => _hvMetricAny(r, ["net_profit", "profit"]) != null);
  const hasPct = rows.some(r => _hvMetricAny(r, ["win_rate", "total_profit_pct"]) != null);
  const effectiveMode = metricMode === "profit" && !hasProfit && hasPct ? "total_profit_pct" : metricMode;
  // 캠페인 win_rate는 0~1 비율, loop_run total_profit_pct는 % 값 — 표시 배율 분기.
  const pctIsWinRate = rows.some(r => ((r && r.metrics) || {}).win_rate != null);

  const grid = (() => {
    const timeLabels = [];
    const capLabels = [];
    const cellMap = {};
    for (const row of rows) {
      const axis = _hvSplitAxisLabel(row.label);
      if (!axis) continue;
      const [t, c] = axis;
      if (!timeLabels.includes(t)) timeLabels.push(t);
      if (!capLabels.includes(c)) capLabels.push(c);
      const key = t + "\u00d7" + c;
      if (!cellMap[key]) cellMap[key] = { count: 0, profitSum: 0, pctSum: 0, pctN: 0 };
      const cell = cellMap[key];
      cell.count += 1;
      const profit = _hvMetricAny(row, ["net_profit", "profit"]);
      if (profit != null && !Number.isNaN(Number(profit))) cell.profitSum += Number(profit);
      const pct = _hvMetricAny(row, ["win_rate", "total_profit_pct"]);
      if (pct != null && !Number.isNaN(Number(pct))) { cell.pctSum += Number(pct); cell.pctN += 1; }
    }
    if (!capLabels.length || !timeLabels.length) return null;
    return { timeLabels, capLabels, cellMap };
  })();

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          12셀 히트맵 (시간창 × 시총)
        </div>
        <button className="btn ghost sm" onClick={loadRows} disabled={isDemo || rowsLoading || !selected}>
          {rowsLoading ? "조회중…" : "\u21bb 새로고침"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {isDemo && <_HvEmpty>Demo mode — 백엔드 연결 시 히트맵이 표시됩니다.</_HvEmpty>}
        {!isDemo && (
          <React.Fragment>
            {preferredResearchId && !preferredResearchId.startsWith("campaign:") && (
              <_HvEmpty>선택 연구 {preferredResearchId}는 campaign 히트맵과 호환되지 않습니다. 이 패널은 독립 campaign 분석입니다.</_HvEmpty>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <select
                className="mono"
                style={{ padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)", minWidth: 220 }}
                value={selected}
                onChange={e => setSelected(e.target.value)}
                disabled={campaignsLoading || campaigns.length === 0}
              >
                {campaigns.length === 0 && <option value="">캠페인 없음</option>}
                {campaigns.map(c => (
                  <option key={c.research_id} value={c.research_id}>{c.label || c.research_id}</option>
                ))}
              </select>
              {hasProfit && hasPct && (
                <button className="btn ghost sm" onClick={() => setMetricMode(m => (m === "profit" ? "total_profit_pct" : "profit"))}>
                  값: {effectiveMode === "profit" ? "손익" : (pctIsWinRate ? "승률" : "수익률%")}
                </button>
              )}
            </div>
            <_HvError err={campaignsErr} onRetry={loadCampaigns} />
            <_HvError err={rowsErr} onRetry={loadRows} />
            {!campaignsErr && campaigns.length === 0 && !campaignsLoading && (
              <_HvEmpty>캠페인 companion 발행 시 표시됩니다</_HvEmpty>
            )}
            {!rowsErr && campaigns.length > 0 && !grid && !rowsLoading && (
              <_HvEmpty>캠페인 companion 발행 시 표시됩니다</_HvEmpty>
            )}
            {grid && (
              <div style={{ overflowX: "auto" }}>
                <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr>
                      <th style={{ padding: "6px 8px", textAlign: "left", color: "var(--ink-3)" }}>시간창 \ 시총</th>
                      {grid.capLabels.map(c => (
                        <th key={c} style={{ padding: "6px 8px", textAlign: "center", color: "var(--ink-3)" }} title={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {grid.timeLabels.map(t => (
                      <tr key={t} style={{ borderTop: "1px solid var(--line-1)" }}>
                        <td style={{ padding: "6px 8px", color: "var(--ink-2)" }} title={t}>{t}</td>
                        {grid.capLabels.map(c => {
                          const cell = grid.cellMap[t + "\u00d7" + c];
                          const value = !cell ? null
                            : effectiveMode === "total_profit_pct"
                              ? (cell.pctN ? cell.pctSum / cell.pctN : null)
                              : cell.profitSum;
                          return (
                            <td
                              key={c}
                              style={{ padding: "6px 10px", textAlign: "center", color: _hvNegColor(value) }}
                              title={cell ? `${t} × ${c} · ${cell.count}건` : `${t} × ${c} · 데이터 없음`}
                            >
                              {value == null ? "\u2014" : (effectiveMode === "total_profit_pct" ? _hvPct(pctIsWinRate ? value * 100 : value) : _hvMoney(value))}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

/* ── B-3: HoldoutFunnel — run 선택 후 평가수 → gate 통과수 → 홀드아웃 3단 퍼널. ── */
function HoldoutFunnel({ baseUrl, wsStatus, preferredResearchId }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [runs, setRuns] = useState_hv([]);
  const [runsLoading, setRunsLoading] = useState_hv(false);
  const [runsErr, setRunsErr] = useState_hv("");
  const [selected, setSelected] = useState_hv("");

  const [rows, setRows] = useState_hv([]);
  const [rowsLoading, setRowsLoading] = useState_hv(false);
  const [rowsErr, setRowsErr] = useState_hv("");

  const loadRuns = useCallback_hv(() => {
    if (isDemo || !baseUrl) return;
    setRunsLoading(true);
    setRunsErr("");
    _hvFetchJson(baseUrl + "/history/index?limit=50&source_kind=loop_run", 30000)
      .then(j => {
        const items = Array.isArray(j && j.items) ? j.items : [];
        setRuns(items);
        setSelected(prev => (
          preferredResearchId && preferredResearchId.startsWith("loop_run:") && items.some(item => item.research_id === preferredResearchId)
            ? preferredResearchId
            : (prev || (items.length ? items[0].research_id : ""))
        ));
      })
      .catch(e => { setRunsErr(String(e)); setRuns([]); })
      .finally(() => setRunsLoading(false));
  }, [baseUrl, isDemo, preferredResearchId]);

  useEffect_hv(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect_hv(() => {
    if (preferredResearchId && preferredResearchId.startsWith("loop_run:") && runs.some(r => r.research_id === preferredResearchId)) {
      setSelected(preferredResearchId);
    }
  }, [preferredResearchId, runs]);

  const loadRows = useCallback_hv(() => {
    if (isDemo || !baseUrl || !selected) {
      setRows([]);
      return;
    }
    setRowsLoading(true);
    setRowsErr("");
    _hvFetchAllPages(
      baseUrl + "/history/detail?research_id=" + encodeURIComponent(selected) + "&section=evaluations"
    )
      .then(rows => setRows(rows))
      .catch(e => { setRowsErr(String(e)); setRows([]); })
      .finally(() => setRowsLoading(false));
  }, [baseUrl, isDemo, selected]);

  useEffect_hv(() => {
    loadRows();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  const evaluatedCount = rows.length;
  // gate_passed는 loop_run 평가 행에만 additive로 존재한다(campaign 행은 필드 자체가 없음).
  // boolean 신호가 하나라도 있을 때만 통과수를 집계하고, 전혀 없으면 "—"로 정직하게 표시한다.
  const gateSignalSeen = rows.some(r => r && typeof r.gate_passed === "boolean");
  const gatePassedCount = rows.filter(r => r && r.gate_passed === true).length;
  // 홀드아웃 신호는 metrics 키에 "holdout"이 실제로 존재할 때만 집계한다
  // (추측 금지 — 서버가 명시적으로 내려준 신호만 사용, reason 같은 존재하지 않는 필드는 참조하지 않는다).
  let holdoutTotal = 0;
  let holdoutPassed = 0;
  let holdoutSignalSeen = false;
  for (const row of rows) {
    const metrics = (row && row.metrics) || {};
    const metricKeys = Object.keys(metrics).filter(k => k.toLowerCase().includes("holdout"));
    if (metricKeys.length === 0) continue;
    holdoutSignalSeen = true;
    holdoutTotal += 1;
    const truthy = metricKeys.some(k => !!metrics[k]);
    if (truthy) holdoutPassed += 1;
  }

  const maxCount = Math.max(evaluatedCount, 1);
  const barStyle = (count) => ({
    height: 22,
    borderRadius: 4,
    background: "var(--teal)",
    width: Math.max(4, Math.round((count / maxCount) * 100)) + "%",
    display: "flex",
    alignItems: "center",
    paddingLeft: 8,
    color: "#04241d",
    fontWeight: 600,
    fontSize: 11,
  });

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          홀드아웃 퍼널
        </div>
        <button className="btn ghost sm" onClick={loadRows} disabled={isDemo || rowsLoading || !selected}>
          {rowsLoading ? "조회중…" : "\u21bb 새로고침"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {isDemo && <_HvEmpty>Demo mode — 백엔드 연결 시 홀드아웃 퍼널이 표시됩니다.</_HvEmpty>}
        {!isDemo && (
          <React.Fragment>
            {preferredResearchId && !preferredResearchId.startsWith("loop_run:") && (
              <_HvEmpty>선택 연구 {preferredResearchId}는 loop_run 퍼널과 호환되지 않습니다. 이 패널은 독립 run 분석입니다.</_HvEmpty>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <select
                className="mono"
                style={{ padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)", minWidth: 220 }}
                value={selected}
                onChange={e => setSelected(e.target.value)}
                disabled={runsLoading || runs.length === 0}
              >
                {runs.length === 0 && <option value="">run 없음</option>}
                {runs.map(r => (
                  <option key={r.research_id} value={r.research_id}>{r.label || r.research_id}</option>
                ))}
              </select>
            </div>
            <_HvError err={runsErr} onRetry={loadRuns} />
            <_HvError err={rowsErr} onRetry={loadRows} />
            {!runsErr && runs.length === 0 && !runsLoading && (
              <_HvEmpty>run이 누적되면 표시됩니다</_HvEmpty>
            )}
            {!rowsErr && runs.length > 0 && evaluatedCount === 0 && !rowsLoading && (
              <_HvEmpty>evaluation 데이터 없음</_HvEmpty>
            )}
            {evaluatedCount > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>평가수</div>
                  <div style={barStyle(evaluatedCount)}>{_hvNum(evaluatedCount)}</div>
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>gate 통과수</div>
                  {gateSignalSeen ? (
                    <div style={barStyle(gatePassedCount)}>{_hvNum(gatePassedCount)}</div>
                  ) : (
                    <_HvEmpty>{"\u2014"}</_HvEmpty>
                  )}
                </div>
                <div>
                  <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 4 }}>홀드아웃</div>
                  {holdoutSignalSeen ? (
                    <div style={barStyle(holdoutPassed)}>{_hvNum(holdoutPassed)} / {_hvNum(holdoutTotal)}</div>
                  ) : (
                    <_HvEmpty>홀드아웃 신호 미발행(향후 제공)</_HvEmpty>
                  )}
                </div>
              </div>
            )}
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { AbPairCompareView, CellHeatmap, HoldoutFunnel });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { AbPairCompareView, CellHeatmap, HoldoutFunnel };
