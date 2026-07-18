/* history-condition-tree.jsx — G003 조건식 History(v4.1) 트리/테이블 패널.
 * condition_history_v1 read model(G002) 위에 얹는 탐색용 뷰. /history/index, /history/detail
 * 만 호출하고 클라이언트에서 조건식을 재구성하지 않는다(서버가 내려준 값만 표시).
 * 승급/검증(promotion/validation) 신호를 절대 발신하지 않는다 — 탐색용 표시만 한다. */
const {
  useState: useState_hct,
  useEffect: useEffect_hct,
  useCallback: useCallback_hct,
  useRef: useRef_hct,
} = React;

const HCT_SOURCE_KINDS = [
  { value: "", label: "전체" },
  { value: "campaign", label: "campaign" },
  { value: "loop_run", label: "loop_run" },
];

function _hctDate(ts) {
  if (!ts) return "-";
  try {
    return new Date(Number(ts) * 1000).toLocaleString();
  } catch {
    return "-";
  }
}

function _hctNum(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  return Number(value).toLocaleString();
}

function _hctMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return sign + Math.round(n).toLocaleString();
}

function _hctPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "\u2014";
  return Number(value).toFixed(2) + "%";
}

function _hctNegColor(value) {
  if (value == null || Number.isNaN(Number(value))) return "var(--ink-2)";
  return Number(value) < 0 ? "var(--red)" : "var(--ink-0)";
}

function _hctPresence(flag) {
  return flag ? "\u2713" : "\u2014";
}

// 서버 계약(history_adapters._generation_label)에 고정: ConditionNode.label은
// loop_run 어댑터에서 정렬 키 JSON 문자열(code_lookup_status, hypotheses_present,
// parent_condition_id, buy_name/sell_name, gen_no/parent_gen)이다. campaign
// 어댑터의 label은 일반 문자열이므로 파싱 실패 시 null(메타 없음)로 처리한다.
// 추측성 키 별칭 탐색은 금지 — 서버가 emit하지 않는 신호는 표시하지 않는다.
function _hctLabelMeta(row) {
  const label = row && row.label;
  if (typeof label !== "string" || label[0] !== "{") return null;
  try {
    const meta = JSON.parse(label);
    return (meta && typeof meta === "object") ? meta : null;
  } catch {
    return null;
  }
}

function _hctStatusCell(row) {
  const status = row.evaluation_status || "";
  if (status === "no_trades") {
    return <span className="mono" style={{ color: "var(--ink-2)" }}>0 trades</span>;
  }
  if (status === "failed" || status === "missing") {
    return (
      <span className="badge err" title={row.reason || ""}>
        {status}{row.reason ? `: ${row.reason}` : ""}
      </span>
    );
  }
  if (status === "timeout") {
    return (
      <span className="badge warn" title={row.reason || ""}>
        {status}{row.reason ? `: ${row.reason}` : ""}
      </span>
    );
  }
  return <span className="badge ok">{status || "\u2014"}</span>;
}

const HCT_EVAL_COLUMNS = [
  { key: "evaluation_status", label: "상태", numeric: false },
  { key: "trade_count", label: "거래수", numeric: true },
  { key: "traded_symbol_count", label: "거래종목수", numeric: true },
  { key: "net_profit", label: "순손익", numeric: true },
  { key: "gross_loss", label: "총손실", numeric: true },
  { key: "losing_trades", label: "손실거래수", numeric: true },
  { key: "win_rate", label: "승률", numeric: true },
  { key: "mdd", label: "MDD", numeric: true },
];

function _hctMetric(row, key) {
  const m = row.metrics || {};
  return m[key] != null ? m[key] : row[key];
}

function _hctSortedEvaluations(rows, sortKey, sortDir) {
  if (!sortKey) return rows;
  const dir = sortDir === "asc" ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const av = _hctMetric(a, sortKey);
    const bv = _hctMetric(b, sortKey);
    const an = av == null ? -Infinity : Number(av);
    const bn = bv == null ? -Infinity : Number(bv);
    if (an === bn) return 0;
    return an < bn ? -dir : dir;
  });
}

function _hctFetchSection(baseUrl, researchId, section, cursor, selectionGeneration, signal) {
  let url = baseUrl + "/history/detail?research_id=" + encodeURIComponent(researchId) + "&section=" + section
    + "&selection_generation=" + encodeURIComponent(String(selectionGeneration));
  if (cursor) url += "&cursor=" + encodeURIComponent(cursor);
  return fetch(url, { signal })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

function _hctDestinationState(value) {
  return ["complete", "partial", "missing", "conflict"].includes(value) ? value : "missing";
}

function _hctCompactValue(value) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.length + " entries";
  if (value && typeof value === "object") return Object.keys(value).join(", ") || "present";
  return "missing";
}

function _hctResearchWorkspace(node, selectedId) {
  const research = node && typeof node === "object" ? node : {};
  const identity = research.identity && typeof research.identity === "object" ? research.identity : {};
  const destinations = identity.destinations && typeof identity.destinations === "object" ? identity.destinations : {};
  const names = ["conditions", "evaluations", "autopsy", "holdout", "ab", "docs", "commits", "governance"];
  return (
    <section aria-label="선택 연구 상세 근거" style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 8 }}>
      <div className="stat-label">Governed research detail · {_hctCompactValue(research.research_id || selectedId)}</div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", margin: "5px 0" }}>
        source owner: {_hctCompactValue(identity.provenance_owner)} · redaction: {_hctCompactValue(identity.redaction)} · byte-identical: {_hctCompactValue(identity.byte_identical)}
      </div>
      <div role="list" aria-label="연구 근거 목적지 상태" style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
        {names.map(name => {
          const value = destinations[name];
          const state = _hctDestinationState(value && value.state);
          return <span key={name} role="listitem" className={"badge " + (state === "complete" ? "ok" : state === "conflict" ? "err" : "warn")}>{name}: {state}</span>;
        })}
      </div>
    </section>
  );
}

function HistoryConditionTreePanel({ baseUrl, wsStatus, selectedResearchId, onSelectedResearchIdChange }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const selectedId = selectedResearchId || "";
  const requestsRef = useRef_hct({ index: null, detail: null });
  const generationRef = useRef_hct({ index: 0, detail: 0 });

  const [q, setQ] = useState_hct("");
  const [sourceKind, setSourceKind] = useState_hct("");
  const [items, setItems] = useState_hct([]);
  const [nextCursor, setNextCursor] = useState_hct(null);
  const [total, setTotal] = useState_hct(0);
  const [indexLoading, setIndexLoading] = useState_hct(false);
  const [indexErr, setIndexErr] = useState_hct("");
  const [sections, setSections] = useState_hct({});
  const [expandedStages, setExpandedStages] = useState_hct({});
  const [expandedConditions, setExpandedConditions] = useState_hct({});
  const [sortKey, setSortKey] = useState_hct("");
  const [sortDir, setSortDir] = useState_hct("desc");

  const loadIndex = useCallback_hct((cursor) => {
    if (isDemo || !baseUrl) return;
    if (requestsRef.current.index) requestsRef.current.index.abort();
    const controller = new AbortController();
    const generation = ++generationRef.current.index;
    requestsRef.current.index = controller;
    setIndexLoading(true);
    setIndexErr("");
    let url = baseUrl + "/history/index?limit=50&selection_generation=" + encodeURIComponent(String(generation));
    if (q.trim()) url += "&q=" + encodeURIComponent(q.trim());
    if (sourceKind) url += "&source_kind=" + encodeURIComponent(sourceKind);
    if (cursor) url += "&cursor=" + encodeURIComponent(cursor);
    fetch(url, { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        if (generation !== generationRef.current.index || controller.signal.aborted
          || !j || String(j.selection_generation) !== String(generation)) return;
        const rows = Array.isArray(j.items) ? j.items : [];
        setItems(prev => (cursor ? prev.concat(rows) : rows));
        setNextCursor(j.next_cursor ? j.next_cursor : null);
        setTotal(j.total != null ? j.total : rows.length);
      })
      .catch(e => {
        if (generation !== generationRef.current.index || controller.signal.aborted) return;
        setIndexErr(String(e));
        if (!cursor) setItems([]);
      })
      .finally(() => {
        if (generation === generationRef.current.index && !controller.signal.aborted) setIndexLoading(false);
      });
  }, [baseUrl, isDemo, q, sourceKind]);

  useEffect_hct(() => {
    loadIndex(null);
  }, [loadIndex]);

  useEffect_hct(() => {
    if (requestsRef.current.detail) requestsRef.current.detail.abort();
    const generation = ++generationRef.current.detail;
    setExpandedStages({});
    setExpandedConditions({});
    if (isDemo || !baseUrl || !selectedId) {
      setSections({});
      return undefined;
    }
    const controller = new AbortController();
    requestsRef.current.detail = controller;
    setSections({ research: { loading: true, err: "", node: null } });
    _hctFetchSection(baseUrl, selectedId, "research", null, generation, controller.signal)
      .then(payload => {
        if (generation !== generationRef.current.detail || controller.signal.aborted
          || !payload || payload.research_id !== selectedId || payload.section !== "research"
          || String(payload.selection_generation) !== String(generation)) return;
        setSections({ research: { loading: false, err: "", node: payload.node || null } });
      })
      .catch(e => {
        if (generation !== generationRef.current.detail || controller.signal.aborted) return;
        setSections({ research: { loading: false, err: String(e), node: null } });
      });
    return () => controller.abort();
  }, [baseUrl, isDemo, selectedId]);

  useEffect_hct(() => () => {
    if (requestsRef.current.index) requestsRef.current.index.abort();
    if (requestsRef.current.detail) requestsRef.current.detail.abort();
  }, []);

  const selectResearch = useCallback_hct((researchId) => {
    if (researchId && researchId !== selectedId && onSelectedResearchIdChange) onSelectedResearchIdChange(researchId);
  }, [onSelectedResearchIdChange, selectedId]);

  const loadSection = useCallback_hct((section, cursor) => {
    if (isDemo || !baseUrl || !selectedId) return;
    if (requestsRef.current.detail) requestsRef.current.detail.abort();
    const controller = new AbortController();
    const generation = ++generationRef.current.detail;
    requestsRef.current.detail = controller;
    setSections(prev => ({
      ...prev,
      [section]: { ...(prev[section] || {}), loading: true, err: prev[section] ? prev[section].err : "" },
    }));
    _hctFetchSection(baseUrl, selectedId, section, cursor, generation, controller.signal)
      .then(payload => {
        if (generation !== generationRef.current.detail || controller.signal.aborted
          || !payload || payload.research_id !== selectedId || payload.section !== section
          || String(payload.selection_generation) !== String(generation)) return;
        const rows = Array.isArray(payload.rows) ? payload.rows : [];
        setSections(prev => ({
          ...prev,
          [section]: {
            loading: false, err: "", rows: cursor ? (prev[section] && prev[section].rows || []).concat(rows) : rows,
            next_cursor: payload.next_cursor ? payload.next_cursor : null,
          },
        }));
      })
      .catch(e => {
        if (generation !== generationRef.current.detail || controller.signal.aborted) return;
        setSections(prev => ({ ...prev, [section]: { loading: false, err: String(e), rows: (prev[section] && prev[section].rows) || [], next_cursor: null } }));
      });
  }, [baseUrl, isDemo, selectedId]);

  const toggleStage = useCallback_hct((stageId) => {
    setExpandedStages(prev => ({ ...prev, [stageId]: !prev[stageId] }));
    if (!sections.conditions) loadSection("conditions", null);
  }, [sections.conditions, loadSection]);

  const toggleCondition = useCallback_hct((conditionId) => {
    setExpandedConditions(prev => ({ ...prev, [conditionId]: !prev[conditionId] }));
    if (!sections.evaluations) loadSection("evaluations", null);
  }, [sections.evaluations, loadSection]);

  const toggleSort = useCallback_hct((key) => {
    setSortKey(prevKey => {
      if (prevKey === key) {
        setSortDir(d => (d === "asc" ? "desc" : "asc"));
        return key;
      }
      setSortDir("desc");
      return key;
    });
  }, []);

  const stageRows = (sections.stages && sections.stages.rows) || [];
  const conditionRows = (sections.conditions && sections.conditions.rows) || [];
  const evaluationRows = (sections.evaluations && sections.evaluations.rows) || [];
  const sortedEvaluations = _hctSortedEvaluations(evaluationRows, sortKey, sortDir);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          조건식 History (v4.1)
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {total} records
        </span>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {isDemo && <div className="research-empty">Demo mode — 백엔드 연결 시 History가 표시됩니다.</div>}
        {!isDemo && (
          <React.Fragment>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <input
                className="mono"
                style={{ flex: "1 1 200px", padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)" }}
                placeholder="검색어 (label / research_id)"
                value={q}
                onChange={e => setQ(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") loadIndex(null); }}
              />
              <select
                className="mono"
                style={{ padding: "6px 8px", background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, color: "var(--ink-0)" }}
                value={sourceKind}
                onChange={e => setSourceKind(e.target.value)}
              >
                {HCT_SOURCE_KINDS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
              <button className="btn ghost sm" onClick={() => loadIndex(null)} disabled={indexLoading}>
                {indexLoading ? "조회중…" : "검색"}
              </button>
            </div>
            {indexErr && (
              <div className="research-empty danger">
                {indexErr}
                <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={() => loadIndex(null)}>재시도</button></div>
              </div>
            )}
            {!indexErr && items.length === 0 && !indexLoading && <div className="research-empty">기록 없음</div>}
            {items.length > 0 && (
              <div style={{ overflowX: "auto" }}>
                <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                  <thead>
                    <tr style={{ color: "var(--ink-3)" }}>
                      <th style={{ textAlign: "left", padding: "6px 8px" }}>Label</th>
                      <th style={{ textAlign: "left", padding: "6px 8px" }}>Source</th>
                      <th style={{ textAlign: "right", padding: "6px 8px" }}>Stages</th>
                      <th style={{ textAlign: "right", padding: "6px 8px" }}>Conditions</th>
                      <th style={{ textAlign: "right", padding: "6px 8px" }}>Evaluations</th>
                      <th style={{ textAlign: "left", padding: "6px 8px" }}>Tree</th>
                      <th style={{ textAlign: "right", padding: "6px 8px" }}>Updated</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(row => {
                      const active = row.research_id === selectedId;
                      const counts = row.counts || {};
                      return (
                        <tr
                          key={row.research_id}
                          style={{
                            borderTop: "1px solid var(--line-1)",
                            background: active ? "rgba(159,180,255,0.08)" : "transparent",
                            cursor: "pointer",
                          }}
                          tabIndex={0}
                          role="button"
                          aria-pressed={active}
                          onClick={() => selectResearch(row.research_id)}
                          onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectResearch(row.research_id); } }}
                        >
                          <td style={{ padding: "7px 8px", maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis" }}>
                            <div style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{row.label || row.research_id}</div>
                            {(row.series || row.ab_role || (row.gate_passed_count > 0)) && (
                              <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 3 }}>
                                {row.series && (
                                  <span className="badge" title="series">{row.series}</span>
                                )}
                                {row.ab_role && row.ab_role.pair && (
                                  <span className="badge" title="A/B 역할(pair·arm)">
                                    {row.ab_role.pair}{row.ab_role.arm ? "\u00b7" + row.ab_role.arm : ""}
                                  </span>
                                )}
                                {row.gate_passed_count > 0 && (
                                  <span className="badge ok" title="gate 통과 세대수">gate {row.gate_passed_count}</span>
                                )}
                              </div>
                            )}
                          </td>
                          <td style={{ padding: "7px 8px", color: "var(--ink-2)" }}>{row.source_kind || "-"}</td>
                          <td style={{ padding: "7px 8px", textAlign: "right" }}>{_hctNum(counts.stages)}</td>
                          <td style={{ padding: "7px 8px", textAlign: "right" }}>{_hctNum(counts.conditions)}</td>
                          <td style={{ padding: "7px 8px", textAlign: "right" }}>{_hctNum(counts.evaluations)}</td>
                          <td style={{ padding: "7px 8px" }}><span className="badge">{row.condition_tree_status || "-"}</span></td>
                          <td style={{ padding: "7px 8px", textAlign: "right", color: "var(--ink-3)" }}>{_hctDate(row.updated_at)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {nextCursor && (
                  <div style={{ marginTop: 8 }}>
                    <button className="btn ghost sm" onClick={() => loadIndex(nextCursor)} disabled={indexLoading}>
                      {indexLoading ? "로딩…" : "더보기"}
                    </button>
                  </div>
                )}
              </div>
            )}

            {selectedId && (
              <div className="panel" style={{ borderColor: "var(--line-1)", background: "var(--bg-0)" }}>
                <div className="panel-hd">
                  <div className="panel-hd-title">
                    <span className="dot" style={{ background: "var(--teal)" }}></span>
                    {selectedId}
                  </div>
                  <button className="btn ghost sm" onClick={() => loadSection("stages", null)} disabled={sections.stages && sections.stages.loading}>
                    {sections.stages && sections.stages.loading ? "로딩…" : "Stages 로드"}
                  </button>
                </div>
                <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {sections.research && !sections.research.loading && _hctResearchWorkspace(sections.research.node, selectedId)}
                  {sections.research && sections.research.err && (
                    <div className="research-empty danger">
                      {sections.research.err}
                      <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={() => selectResearch(selectedId)}>재시도</button></div>
                    </div>
                  )}
                  {sections.stages && sections.stages.err && (
                    <div className="research-empty danger">
                      {sections.stages.err}
                      <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={() => loadSection("stages", null)}>재시도</button></div>
                    </div>
                  )}
                  {stageRows.length === 0 && !(sections.stages && sections.stages.loading) && (
                    <div className="research-empty">{sections.stages ? "stage 없음" : "Stages 로드 버튼으로 트리를 펼치세요"}</div>
                  )}
                  {stageRows.map(stage => {
                    const stageOpen = !!expandedStages[stage.stage_id];
                    const stageConditions = conditionRows.filter(c => c.stage_id === stage.stage_id);
                    return (
                      <div key={stage.stage_id} style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 8 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }} onClick={() => toggleStage(stage.stage_id)}>
                          <span className="mono">{stageOpen ? "▼" : "▶"}</span>
                          <span className="mono" style={{ color: "var(--ink-0)" }}>{stage.label || stage.stage_id}</span>
                          <span className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5 }}>{stage.stage_id}</span>
                        </div>
                        {stageOpen && (
                          <div style={{ marginTop: 8, marginLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
                            {sections.conditions && sections.conditions.err && (
                              <div className="research-empty danger">
                                {sections.conditions.err}
                                <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={() => loadSection("conditions", null)}>재시도</button></div>
                              </div>
                            )}
                            {stageConditions.length === 0 && !(sections.conditions && sections.conditions.loading) && (
                              <div className="research-empty" style={{ padding: "4px 0" }}>condition 없음</div>
                            )}
                            {stageConditions.map(cond => {
                              const condOpen = !!expandedConditions[cond.condition_id];
                              const condEvaluations = evaluationRows.filter(e => e.condition_id === cond.condition_id);
                              const meta = _hctLabelMeta(cond);
                              const parentId = (meta && meta.parent_condition_id) || cond.parent_condition_id;
                              return (
                                <div key={cond.condition_id} style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 6 }}>
                                  <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", cursor: "pointer" }} onClick={() => toggleCondition(cond.condition_id)}>
                                    <span className="mono">{condOpen ? "▼" : "▶"}</span>
                                    <span className="badge" style={{ color: cond.side === "sell" ? "var(--red)" : "var(--teal)" }}>{cond.side || "-"}</span>
                                    <span className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5 }}>{cond.condition_id}</span>
                                    {parentId && (
                                      <span className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5 }}>
                                        parent={parentId}
                                      </span>
                                    )}
                                    {meta && meta.code_lookup_status && (
                                      <span className="badge" title="buy/sell 이름 참조의 코드 조회 상태 (서버 code_lookup_status)">code {meta.code_lookup_status}</span>
                                    )}
                                    {meta && ("hypotheses_present" in meta) && (
                                      <span className="badge" title="가설(hypotheses_json) 존재 여부">가설 {_hctPresence(!!meta.hypotheses_present)}</span>
                                    )}
                                  </div>
                                  {condOpen && (
                                    <div style={{ marginTop: 6, marginLeft: 18 }}>
                                      {sections.evaluations && sections.evaluations.err && (
                                        <div className="research-empty danger">
                                          {sections.evaluations.err}
                                          <div style={{ marginTop: 8 }}><button className="btn ghost sm" onClick={() => loadSection("evaluations", null)}>재시도</button></div>
                                        </div>
                                      )}
                                      {condEvaluations.length === 0 && !(sections.evaluations && sections.evaluations.loading) && (
                                        <div className="research-empty" style={{ padding: "4px 0" }}>evaluation 없음</div>
                                      )}
                                      {condEvaluations.map(ev => (
                                        <div key={ev.evaluation_id} className="mono" style={{ display: "flex", gap: 8, padding: "3px 0", fontSize: 10.5, color: "var(--ink-2)" }}>
                                          <span>{ev.evaluation_id}</span>
                                          {_hctStatusCell(ev)}
                                        </div>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}

                  <div>
                    <div className="stat-label" style={{ marginBottom: 6 }}>Evaluation Rows</div>
                    {sortedEvaluations.length === 0 ? (
                      <div className="research-empty">evaluation 로드 후 표시됩니다 (조건 노드를 펼치세요)</div>
                    ) : (
                      <div style={{ overflowX: "auto" }}>
                        <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
                          <thead>
                            <tr style={{ color: "var(--ink-3)" }}>
                              {HCT_EVAL_COLUMNS.map(col => (
                                <th
                                  key={col.key}
                                  style={{ textAlign: col.numeric ? "right" : "left", padding: "6px 8px", cursor: col.numeric ? "pointer" : "default" }}
                                  onClick={() => col.numeric && toggleSort(col.key)}
                                >
                                  {col.label}{sortKey === col.key ? (sortDir === "asc" ? " ▲" : " ▼") : ""}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {sortedEvaluations.map(row => (
                              <tr key={row.evaluation_id} style={{ borderTop: "1px solid var(--line-1)" }}>
                                <td style={{ padding: "6px 8px" }}>{_hctStatusCell(row)}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hctNum(_hctMetric(row, "trade_count"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hctNum(_hctMetric(row, "traded_symbol_count"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right", color: _hctNegColor(_hctMetric(row, "net_profit")) }}>{_hctMoney(_hctMetric(row, "net_profit"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right", color: _hctNegColor(_hctMetric(row, "gross_loss")) }}>{_hctMoney(_hctMetric(row, "gross_loss"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hctNum(_hctMetric(row, "losing_trades"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hctPct(_hctMetric(row, "win_rate"))}</td>
                                <td style={{ padding: "6px 8px", textAlign: "right" }}>{_hctPct(_hctMetric(row, "mdd"))}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {sections.evaluations && sections.evaluations.next_cursor && (
                          <div style={{ marginTop: 8 }}>
                            <button className="btn ghost sm" onClick={() => loadSection("evaluations", sections.evaluations.next_cursor)} disabled={sections.evaluations.loading}>
                              {sections.evaluations.loading ? "로딩…" : "더보기"}
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                    <div className="mono" style={{ marginTop: 8, fontSize: 10.5, color: "var(--amber)" }}>
                      탐색용 결과 — OOS/승격 근거 아님
                    </div>
                  </div>
                </div>
              </div>
            )}
          </React.Fragment>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { HistoryConditionTreePanel });

export { HistoryConditionTreePanel };
