/* Backtest workbench tab — 모드별 결과 표(WFO·스윕) 묶음 (split from backtest.jsx).
   /bt/result 의 mode_result 를 정렬 가능 표로. wfo: 윈도우(라운드)별 train/test 기간·메트릭.
   sweep: 조합/윈도우별 결과. csv 단일 분석(BtResultArea)과 별개 — wfo/sweep 잡 선택 시 이 표가 뜬다.

   숫자포맷(_btNum)·드릴다운 행(_BtRowDetail)·잡 배지(_BT_JOB_BADGE)는 bt-tab-utils 에서 공유.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_bt, useEffect_bt, useMemo_bt, _btFetchJson, _BT_JOB_BADGE, _btNum, _BtRowDetail } from "./bt-tab-utils.jsx";

function _btModeMetric(row) {
  const n = Number(row && row.total_profit_pct);
  return isFinite(n) ? n : null;
}

function _btSweepCombo(item) {
  const params = item && item.params;
  if (params && typeof params === "object" && !Array.isArray(params)) {
    const combo = {};
    Object.keys(params).forEach(name => { combo[name] = params[name]; });
    return combo;
  }
  const combo = {};
  Object.keys(item || {}).forEach(name => {
    if (name === "result" || name === "metrics" || name === "window" || name === "status" || name === "params") return;
    combo[name] = item[name];
  });
  return combo;
}


function _btVariableInfluenceRows(result, mode) {
  const groups = {};
  const push = (name, value, metric) => {
    if (!name || metric == null) return;
    const key = String(name);
    const val = String(value == null ? "—" : value);
    if (!groups[key]) groups[key] = {};
    if (!groups[key][val]) groups[key][val] = [];
    groups[key][val].push(metric);
  };

  if (mode === "wfo") {
    ((result && result.rounds) || []).forEach((round) => {
      const params = round && round.best_params;
      const metric = _btModeMetric((round && round.test_result && round.test_result.metrics) || {});
      if (!params || typeof params !== "object") return;
      Object.keys(params).forEach(name => push(name, params[name], metric));
    });
  } else {
    ((result && result.results) || []).forEach((item) => {
      const metric = _btModeMetric((item && item.result && item.result.metrics) || item.metrics || {});
      const combo = _btSweepCombo(item);
      Object.keys(combo).forEach(name => push(name, combo[name], metric));
    });
  }

  return Object.keys(groups).map(name => {
    const values = Object.keys(groups[name]).map(value => {
      const vals = groups[name][value];
      const avg = vals.reduce((a, b) => a + b, 0) / Math.max(1, vals.length);
      return { value, avg, samples: vals.length };
    }).sort((a, b) => b.avg - a.avg);
    const best = values[0] || null;
    const worst = values[values.length - 1] || null;
    const impact = best && worst ? best.avg - worst.avg : 0;
    return { name, impact, best, worst, values, samples: values.reduce((a, v) => a + v.samples, 0) };
  }).filter(row => row.values.length >= 2)
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact));
}

function BtVariableInfluencePanel({ result, mode }) {
  const rows = useMemo_bt(() => _btVariableInfluenceRows(result, mode), [result, mode]);
  return (
    <div style={{ border: "1px solid var(--line-1)", borderRadius: 8, padding: 10, background: "var(--bg-0)", display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="dot" style={{ background: "var(--violet)" }}></span>
        <span className="panel-hd-title" style={{ border: 0, padding: 0 }}>변수 영향도 자동 분석</span>
        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
          {mode === "wfo" ? "WFO 선택 파라미터별 OOS 수익률 영향" : "스윕 조합별 수익률 분산 영향"}
        </span>
      </div>
      {rows.length === 0 ? (
        <div className="research-empty" style={{ padding: 10 }}>
          비교 가능한 변수 값이 2개 이상 있어야 영향도를 계산할 수 있습니다.
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8 }}>
          {rows.slice(0, 8).map(row => (
            <div key={row.name} style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 8, display: "flex", flexDirection: "column", gap: 5 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <b className="mono" style={{ fontSize: 12, color: "var(--ink-0)", flex: 1, overflow: "hidden", textOverflow: "ellipsis" }}>{row.name}</b>
                <span className="mono" style={{ fontSize: 11, color: Math.abs(row.impact) > 0 ? "var(--amber)" : "var(--ink-3)" }}>
                  Δ {_btNum(row.impact)}%p
                </span>
              </div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--teal)" }}>
                best {row.best.value} · avg {_btNum(row.best.avg)}%
              </div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--red)" }}>
                worst {row.worst.value} · avg {_btNum(row.worst.avg)}%
              </div>
              <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
                samples {row.samples} · values {row.values.length}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


// wfo rounds → 정렬 가능 행. 각 round: {window:{round,train_*,test_*}, best_params, test_result:{metrics}}.
function BtWfoTable({ result }) {
  const [sortKey, setSortKey] = useState_bt("round");
  const [sortAsc, setSortAsc] = useState_bt(true);
  const [expanded, setExpanded] = useState_bt(null);   // 펼친 라운드 번호(드릴다운) 또는 null.
  const rounds = (result && result.rounds) || [];
  const summary = (result && result.summary) || {};
  const rows = useMemo_bt(() => rounds.map((r, i) => {
    const w = r.window || {};
    const tr = (r.test_result && r.test_result.metrics) || {};
    return {
      round: w.round != null ? w.round : (i + 1),
      train: (w.train_start != null ? w.train_start : "—") + "~" + (w.train_end != null ? w.train_end : "—"),
      test: (w.test_start != null ? w.test_start : "—") + "~" + (w.test_end != null ? w.test_end : "—"),
      status: (r.test_result && r.test_result.status) || "—",
      trade_count: tr.trade_count,
      total_profit_pct: tr.total_profit_pct,
      max_drawdown_pct: tr.max_drawdown_pct,
      best_params: r.best_params || {},   // 드릴다운: 이 라운드가 훈련에서 고른 파라미터.
      _metrics: tr,                       // 드릴다운: 표에 없는 전체 테스트 메트릭.
    };
  }), [rounds]);
  const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
    const va = a[sortKey], vb = b[sortKey];
    const na = Number(va), nb = Number(vb);
    const cmp = (!isNaN(na) && !isNaN(nb)) ? (na - nb) : String(va).localeCompare(String(vb));
    return sortAsc ? cmp : -cmp;
  }), [rows, sortKey, sortAsc]);
  const setSort = (k) => { if (k === sortKey) setSortAsc(a => !a); else { setSortKey(k); setSortAsc(true); } };
  const cols = [
    ["round", "라운드"], ["train", "훈련기간"], ["test", "테스트기간"], ["status", "상태"],
    ["trade_count", "거래수"], ["total_profit_pct", "수익%"], ["max_drawdown_pct", "MDD%"],
  ];
  if (rounds.length === 0) return <div className="research-empty">WFO 라운드 결과가 없습니다.</div>;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", display: "flex", gap: 14, flexWrap: "wrap" }}>
        <span>라운드 {summary.round_count != null ? summary.round_count : rounds.length}</span>
        <span>성공률 {summary.success_rate != null ? (summary.success_rate * 100).toFixed(0) + "%" : "—"}</span>
        <span>평균 OOS {summary.metric || "tpi"} {_btNum(summary.mean_oos_metric)}</span>
        <span>무거래 라운드 {summary.zero_trade_rounds != null ? summary.zero_trade_rounds : "—"}</span>
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
          <thead>
            <tr>
              {cols.map(([k, lbl]) => (
                <th key={k} onClick={() => setSort(k)} title="정렬"
                  style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)",
                           borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {lbl}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => {
              const isOpen = expanded === r.round;
              return (
              <React.Fragment key={i}>
              <tr onClick={() => setExpanded(isOpen ? null : r.round)}
                  style={{ cursor: "pointer", background: isOpen ? "var(--bg-2)" : undefined }}
                  title="클릭 — 이 라운드의 선택 파라미터·전체 메트릭 펼치기/접기">
                <td style={{ padding: "4px 8px", color: "var(--ink-0)" }}>{isOpen ? "▾ " : "▸ "}{r.round}</td>
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.train}</td>
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.test}</td>
                <td style={{ padding: "4px 8px" }}>
                  <span className={(_BT_JOB_BADGE[r.status] || _BT_JOB_BADGE.pending).cls}>{r.status}</span>
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right" }}>{r.trade_count == null ? "—" : r.trade_count}</td>
                <td style={{ padding: "4px 8px", textAlign: "right",
                             color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {_btNum(r.total_profit_pct)}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "var(--red)" }}>{_btNum(r.max_drawdown_pct)}</td>
              </tr>
              {isOpen && (
                <tr>
                  <td colSpan={cols.length} style={{ padding: "6px 12px 10px", background: "var(--bg-2)" }}>
                    <_BtRowDetail label="선택 파라미터" data={r.best_params} />
                    <_BtRowDetail label="전체 메트릭" data={r._metrics} numeric />
                  </td>
                </tr>
              )}
              </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// sweep results → 정렬 가능 표. 각 항목: {...combo, result:{metrics}} 또는 {window, ...metrics}.
function BtSweepTable({ result }) {
  const [sortKey, setSortKey] = useState_bt("__idx");
  const [sortAsc, setSortAsc] = useState_bt(true);
  const [expanded, setExpanded] = useState_bt(null);   // 펼친 조합 #(드릴다운) 또는 null.
  const raw = (result && result.results) || [];
  // 조합 키(combo)는 result/window 외 임의 키. 동적 컬럼을 수집한다.
  const rows = useMemo_bt(() => raw.map((item, i) => {
    const m = (item && item.result && item.result.metrics) || item.metrics || {};
    const combo = _btSweepCombo(item);
    return {
      __idx: i + 1,
      __combo: combo,
      window: item.window ? (Array.isArray(item.window) ? item.window.join("~") : String(item.window)) : null,
      trade_count: m.trade_count,
      total_profit_pct: m.total_profit_pct,
      max_drawdown_pct: m.max_drawdown_pct,
      _metrics: m,   // 드릴다운: 표 3컬럼 밖의 전체 메트릭(win_rate·sharpe·cagr…).
    };
  }), [raw]);
  const comboKeys = useMemo_bt(() => {
    const s = new Set();
    rows.forEach(r => Object.keys(r.__combo).forEach(k => s.add(k)));
    return Array.from(s);
  }, [rows]);
  const hasWindow = useMemo_bt(() => rows.some(r => r.window != null), [rows]);
  const sorted = useMemo_bt(() => rows.slice().sort((a, b) => {
    const get = (r) => (r.__combo[sortKey] != null ? r.__combo[sortKey] : r[sortKey]);
    const va = get(a), vb = get(b);
    const na = Number(va), nb = Number(vb);
    const cmp = (!isNaN(na) && !isNaN(nb)) ? (na - nb) : String(va).localeCompare(String(vb));
    return sortAsc ? cmp : -cmp;
  }), [rows, sortKey, sortAsc]);
  const setSort = (k) => { if (k === sortKey) setSortAsc(a => !a); else { setSortKey(k); setSortAsc(true); } };
  if (raw.length === 0) return <div className="research-empty">스윕 결과가 없습니다.</div>;
  const metricCols = [["trade_count", "거래수"], ["total_profit_pct", "수익%"], ["max_drawdown_pct", "MDD%"]];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
        총 {result.total_combinations != null ? result.total_combinations : raw.length}개 조합
      </div>
      <div style={{ overflowX: "auto" }}>
        <table className="mono" style={{ borderCollapse: "collapse", fontSize: 11, width: "100%" }}>
          <thead>
            <tr>
              <th onClick={() => setSort("__idx")} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" }}>
                #{sortKey === "__idx" ? (sortAsc ? " ▲" : " ▼") : ""}
              </th>
              {hasWindow && (
                <th onClick={() => setSort("window")} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)" }}>
                  윈도우{sortKey === "window" ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              )}
              {comboKeys.map(k => (
                <th key={k} onClick={() => setSort(k)} style={{ padding: "5px 8px", textAlign: "left", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {k}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
              {metricCols.map(([k, lbl]) => (
                <th key={k} onClick={() => setSort(k)} style={{ padding: "5px 8px", textAlign: "right", cursor: "pointer", color: "var(--ink-3)", borderBottom: "1px solid var(--line-1)", whiteSpace: "nowrap" }}>
                  {lbl}{sortKey === k ? (sortAsc ? " ▲" : " ▼") : ""}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((r, i) => {
              const isOpen = expanded === r.__idx;
              const span = 1 + (hasWindow ? 1 : 0) + comboKeys.length + 3;
              return (
              <React.Fragment key={i}>
              <tr onClick={() => setExpanded(isOpen ? null : r.__idx)}
                  style={{ cursor: "pointer", background: isOpen ? "var(--bg-2)" : undefined }}
                  title="클릭 — 이 조합의 전체 메트릭 펼치기/접기">
                <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{isOpen ? "▾ " : "▸ "}{r.__idx}</td>
                {hasWindow && <td style={{ padding: "4px 8px", color: "var(--ink-3)" }}>{r.window || "—"}</td>}
                {comboKeys.map(k => (
                  <td key={k} style={{ padding: "4px 8px", color: "var(--ink-0)" }}>
                    {r.__combo[k] != null ? String(r.__combo[k]) : "—"}
                  </td>
                ))}
                <td style={{ padding: "4px 8px", textAlign: "right" }}>{r.trade_count == null ? "—" : r.trade_count}</td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: Number(r.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)" }}>
                  {_btNum(r.total_profit_pct)}
                </td>
                <td style={{ padding: "4px 8px", textAlign: "right", color: "var(--red)" }}>{_btNum(r.max_drawdown_pct)}</td>
              </tr>
              {isOpen && (
                <tr>
                  <td colSpan={span} style={{ padding: "6px 12px 10px", background: "var(--bg-2)" }}>
                    <_BtRowDetail label="조합" data={r.__combo} />
                    <_BtRowDetail label="전체 메트릭" data={r._metrics} numeric />
                  </td>
                </tr>
              )}
              </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BtModeResultPanel({ baseUrl, isDemo, jobId, mode }) {
  const [data, setData] = useState_bt(null);
  const [err, setErr] = useState_bt("");
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !jobId) { setData(null); return; }
    let cancelled = false;
    _btFetchJson(baseUrl + "/bt/result?job_id=" + encodeURIComponent(jobId), 12000)
      .then(j => { if (!cancelled) { setData(j); setErr(""); } })
      .catch(e => { if (!cancelled) { setData(null); setErr(String(e)); } });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, jobId]);
  const mr = data && data.mode_result;
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          {mode === "wfo" ? "전진분석(WFO) 결과" : "스윕 결과"}
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {err ? (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>
        ) : !mr ? (
          <div className="research-empty">결과를 불러오는 중이거나 구조화 결과가 없습니다.</div>
        ) : (
          <>
            <BtVariableInfluencePanel result={mr} mode={mode} />
            {mode === "wfo" ? (
              <BtWfoTable result={mr} />
            ) : (
              <BtSweepTable result={mr} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { _btVariableInfluenceRows, _btSweepCombo, BtVariableInfluencePanel, BtWfoTable, BtSweepTable, BtModeResultPanel };
