/* ResearchLabPanel - compact analysis workspace for Edge, Feature, Correlation, and Variable Combinations. */

const {
  useState: useState_rl,
  useEffect: useEffect_rl,
  useCallback: useCallback_rl,
  useMemo: useMemo_rl,
} = React;

const RESEARCH_TABS = [
  { id: "edge", label: "Edge" },
  { id: "feature", label: "Feature Importance" },
  { id: "correlation", label: "Correlation" },
  { id: "combos", label: "Variable Combinations" },
  { id: "validation", label: "Validation" },
];

function _rlNum(value, digits) {
  if (typeof value !== "number" || !isFinite(value)) return "--";
  return value.toFixed(digits == null ? 3 : digits);
}

function _rlCorrColor(value) {
  if (typeof value !== "number" || !isFinite(value)) return "rgba(80,96,116,0.48)";
  const t = Math.min(1, Math.abs(value));
  if (value >= 0) return `rgba(${Math.round(35 + 30 * (1 - t))},${Math.round(130 + 70 * t)},${Math.round(126 + 40 * t)},0.86)`;
  return `rgba(${Math.round(178 + 48 * t)},${Math.round(108 - 32 * t)},${Math.round(62 - 24 * t)},0.86)`;
}

function _ResearchEmptyState({ message }) {
  return (
    <div className="research-empty">
      {message || "insufficient data for the selected research view."}
    </div>
  );
}

function _CorrelationControls({ method, setMethod, axis, setAxis, loading, pooledTrades, featureCount }) {
  return (
    <div className="research-controls">
      <label>
        <span>method</span>
        <select value={method} onChange={(e) => setMethod(e.target.value)} disabled={loading}>
          <option value="pearson">pearson</option>
          <option value="spearman">spearman</option>
        </select>
      </label>
      <label>
        <span>segment axis</span>
        <select value={axis} onChange={(e) => setAxis(e.target.value)}>
          <option value="time">time</option>
          <option value="market_cap">market_cap</option>
          <option value="change">change</option>
        </select>
      </label>
      <div className="research-kpis">
        <span>sample count {_rlNum(pooledTrades, 0)}</span>
        <span>features {_rlNum(featureCount, 0)}</span>
      </div>
    </div>
  );
}

function _CorrelationHeatmap({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient feature_matrix rows for a correlation heatmap." />;
  }
  return (
    <div className="research-heatmap">
      {rows.slice(0, 36).map((row, i) => {
        const label = [row.feature_a, row.feature_b].filter(Boolean).join(" / ") || row.feature || ("feature_" + i);
        const corr = typeof row.correlation === "number" ? row.correlation : null;
        return (
          <div key={i}
               className="research-cell"
               style={{ background: _rlCorrColor(corr) }}
               title={`${label} | correlation ${_rlNum(corr, 4)} | sample count ${row.n || 0}`}>
            <strong>{label}</strong>
            <span>{_rlNum(corr, 3)}</span>
            <small>n={row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

function _CombinationList({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient variable combinations for the selected run." />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 14).map((row, i) => {
        const a = row.feature_a || row.feature || "feature_a";
        const b = row.feature_b || "feature_b";
        const corr = typeof row.correlation === "number" ? row.correlation : null;
        const score = typeof row.research_score === "number" ? row.research_score : null;
        return (
          <div key={i} className="research-combo-row">
            <span className="mono">{a}</span>
            <span className="research-muted">x</span>
            <span className="mono">{b}</span>
            <strong style={{ color: _rlCorrColor(score == null ? corr : score) }}>
              {score == null ? _rlNum(corr, 3) : _rlNum(score, 3)}
            </strong>
            <small>sample count {row.sample_count || row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

function _RangeSummaryList({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="insufficient range_summaries for histogram research." />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row" title="histogram and win/loss range contrast">
          <span className="mono">{row.feature}</span>
          <span>median {_rlNum(row.median, 2)}</span>
          <span>q25-q75 {_rlNum(row.q25, 2)}~{_rlNum(row.q75, 2)}</span>
          <span>win/loss Δ {_rlNum(row.win_loss && row.win_loss.mean_delta, 3)}</span>
          <small>histogram {(row.histogram || []).map(b => b.count).join("/")}</small>
        </div>
      ))}
    </div>
  );
}

function _SegmentSummaryList({ summary, axis }) {
  const rows = summary && Array.isArray(summary[axis]) ? summary[axis] : [];
  if (rows.length === 0) {
    return <_ResearchEmptyState message={"insufficient segment_summaries for " + axis + "."} />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row">
          <span className="mono">{axis}:{row.label}</span>
          <span>avg {_rlNum(row.avg_return, 3)}</span>
          <span>win {_rlNum(row.win_rate, 3)}</span>
          <small>sample count {row.sample_count || 0}</small>
        </div>
      ))}
    </div>
  );
}

function _RecencyResearchBadge({ recency }) {
  if (!recency) return null;
  return (
    <div className="research-empty" title="research_score_not_promotion">
      recency_research · {recency.score_label || "research_score_not_promotion"} ·
      score {_rlNum(recency.research_score, 4)}
    </div>
  );
}

/* D1/D2/D4(2026-06-10) — 검증 패널: 연도 분해 · 선택기 미리보기 · 부검 요약.
   읽기 전용 GET 3종(/run_yearly /selector_preview /autopsy)만 소비한다.
   근거: 원인5(연도별 쇠퇴는 합계로 안 보임)·원인1(기준-목표 비정합을 눈으로 확인). */
function _ValidationPanel({ baseUrl, runId, isDemo }) {
  const [selector, setSelector] = useState_rl("seed_relative_v1");
  const [yearly, setYearly] = useState_rl(null);
  const [preview, setPreview] = useState_rl(null);
  const [autopsyGen, setAutopsyGen] = useState_rl(0);
  const [autopsy, setAutopsy] = useState_rl(null);
  const [cf, setCf] = useState_rl(null);
  const [mc, setMc] = useState_rl(null);
  const [tmap, setTmap] = useState_rl(null);
  const [compareRun, setCompareRun] = useState_rl("");  /* M12 — 지도 비교 run. */
  const [ops, setOps] = useState_rl(null);  /* 운영 현황 — 10초 자동 갱신. */
  const [grid, setGrid] = useState_rl(null);     /* C6 — 2-D 격자 히트맵. */
  const [gridRun, setGridRun] = useState_rl("");
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const fetchGrid = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    const rid = gridRun.trim() || runId;
    if (!rid) return;
    fetch(baseUrl + "/tmap_grid?run_id=" + encodeURIComponent(rid),
          { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setGrid(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, gridRun, isDemo, runId]);

  const [gridMetric, setGridMetric] = useState_rl("profit");  /* E5 — 히트맵 색 기준. */
  const [runOptions, setRunOptions] = useState_rl([]);  /* F2 — run 자동완성. */
  useEffect_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(d => setRunOptions(((d && d.runs) || []).slice(0, 40).map(r => r.run_id)))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  const [niche, setNiche] = useState_rl(null);  /* D3 — 니치 지도 비교. */
  const fetchNiche = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/niche_compare", { signal: AbortSignal.timeout(15000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setNiche(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, isDemo]);

  const [verdict, setVerdict] = useState_rl(null);  /* 검증 결산 — V1~V5 종합. */

  useEffect_rl(() => {
    if (isDemo || !baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setOps(j))
      .catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    fetch(baseUrl + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setVerdict(j))
      .catch(() => {});
    return () => clearInterval(timer);
  }, [baseUrl, isDemo]);

  const fetchTmap = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const cmp = compareRun.trim()
      ? "&compare_run_id=" + encodeURIComponent(compareRun.trim()) : "";
    fetch(baseUrl + "/tmap_map?run_id=" + encodeURIComponent(runId) + cmp,
          { signal: AbortSignal.timeout(10000) })
      .then(r => r.ok ? r.json() : null)
      .then(j => setTmap(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, compareRun, isDemo, runId]);

  const refresh = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const yUrl = baseUrl + "/run_yearly?run_id=" + encodeURIComponent(runId);
    const pUrl = baseUrl + "/selector_preview?run_id=" + encodeURIComponent(runId)
      + "&selector=" + encodeURIComponent(selector);
    Promise.all([
      fetch(yUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
      fetch(pUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
    ])
      .then(([y, p]) => { setYearly(y); setPreview(p); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, selector]);

  useEffect_rl(() => { refresh(); }, [refresh]);

  const [equity, setEquity] = useState_rl(null);  /* E2/D4 — 누적 수익곡선. */
  const fetchAutopsy = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const q = "?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(autopsyGen);
    Promise.all([
      fetch(baseUrl + "/autopsy" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/counterfactual" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/freeze_mc" + q, { signal: AbortSignal.timeout(15000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/equity_curve" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
    ])
      .then(([a, c, m, eq]) => { setAutopsy(a); setCf(c); setMc(m); setEquity(eq); })
      .catch(e => setErr(String(e)));
  }, [autopsyGen, baseUrl, isDemo, runId]);

  if (isDemo || !runId) {
    return <div className="research-lab-panel"><_ResearchEmptyState message="insufficient run context for validation views." /></div>;
  }

  const gens = (yearly && Array.isArray(yearly.generations)) ? yearly.generations : [];
  return (
    <div className="research-lab-panel">
      <div className="research-controls">
        <label>
          <span>selector</span>
          <select value={selector} onChange={(e) => setSelector(e.target.value)} disabled={loading}>
            <option value="seed_relative_v1">seed_relative_v1</option>
            <option value="sparse_positive_v1">sparse_positive_v1</option>
          </select>
        </label>
        <span className="research-empty">diagnostic_only · 동결 아티팩트 아님</span>
      </div>
      {err && <_ResearchEmptyState message={"insufficient response: " + err} />}

      {ops && (
        <div style={{ marginTop: 6 }}>
          <div className="research-empty">
            {"운영 현황 (10초 자동 갱신)"
              + (ops.walkforward
                ? ` · WF ${ops.walkforward.path}: 정책 ${Math.round(ops.walkforward.policy_total || 0).toLocaleString()} vs 시드 ${Math.round(ops.walkforward.baseline_total || 0).toLocaleString()} (${ops.walkforward.windows_done}창 완료)`
                : "")}
          </div>
          {(ops.active || []).length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>실행 중 run 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>실행 중 run</th><th>세대</th><th>마지막 포인트</th><th>무진행(초)</th><th>상태</th></tr></thead>
                <tbody>
                  {ops.active.map(a => (
                    <tr key={a.run_id}>
                      <td>{a.run_id}</td>
                      <td>{a.gens}</td>
                      <td>{a.last_label || "—"}</td>
                      <td>{a.seconds_since_last_gen}</td>
                      <td>{a.health === "active" ? "✅ 진행 중" : "⚠️ 정체 의심"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          {(ops.recent || []).length > 0 && (
            <div className="mono" style={{ fontSize: 11 }}>
              {"최근 완료: " + ops.recent.slice(0, 5).map(r =>
                `${r.run_id}(${r.gens}세대${r.best_profit != null ? "·최고 " + Math.round(r.best_profit).toLocaleString() : ""})`
              ).join("  ·  ")}
            </div>
          )}
          {(ops.evidence || []).length > 0 && (
            <div className="research-empty">
              {"최신 증거: " + ops.evidence.map(e => `${e.name}(${e.age_min}분 전)`).join(" · ")}
            </div>
          )}
        </div>
      )}

      {verdict && (verdict.lines || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">검증 결산 (V1~V5 + 리스크 — 결정 카드 라이브)</div>
          {(verdict.promote_checklist || []).length > 0 && (
            <table className="mono" style={{ fontSize: 11, marginBottom: 4 }}>
              <thead><tr><th>PROMOTE 조건</th><th>상태</th><th>근거</th></tr></thead>
              <tbody>
                {verdict.promote_checklist.map((c, i) => (
                  <tr key={"c" + i}>
                    <td>{c.item}</td>
                    <td>{c.status === "pass" ? "✅" : c.status === "warn" ? "⚠️" : c.status === "fail" ? "❌" : "⏳"}</td>
                    <td>{c.detail || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {verdict.walkforward && Array.isArray(verdict.walkforward.windows)
            && verdict.walkforward.windows.length > 0 && (
            <table className="mono" style={{ fontSize: 11, marginBottom: 4 }}>
              <thead><tr><th>WF 창(fit)</th><th>eval</th><th>θ 선택</th><th>정책</th><th>시드</th></tr></thead>
              <tbody>
                {verdict.walkforward.windows.map((w, i) => (
                  <tr key={"w" + i}>
                    <td>{w.fit_start}~{w.fit_end}</td>
                    <td>{w.eval_start}~{w.eval_end}</td>
                    <td>{w.theta
                      ? Object.entries(w.theta).map(([k, v]) => `${k}=${v}`).join(",")
                      : "기권(시드 유지)"}</td>
                    <td>{w.policy ? Math.round(w.policy.profit).toLocaleString() : "—"}</td>
                    <td>{w.baseline ? Math.round(w.baseline.profit).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {(verdict.alerts || []).map((a, i) => (
            <div key={"a" + i} className="mono" style={{ fontSize: 11, color: "#c95" }}>⚠️ {a}</div>
          ))}
          {verdict.lines.map((l, i) => (
            <div key={"l" + i} className="mono" style={{ fontSize: 11 }}>{l}</div>
          ))}
        </div>
      )}

      {niche && (niche.runs || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">니치 지도 비교 (최근 tmap run 자동 — 신규 니치 4종 아침 분석용)</div>
          <table className="mono" style={{ fontSize: 11, width: "100%" }}>
            <thead><tr><th>run</th><th>상태</th><th>ok세대</th><th>베이스라인</th><th>최강 슬롯 고원 / 격자</th><th>최고 단일점</th><th>시간대</th><th>R²·정체</th><th>동결상관</th></tr></thead>
            <tbody>
              {niche.runs.map(r => (
                <tr key={r.run_id}>
                  <td>{r.run_id}</td>
                  <td>{r.status === "running" ? "🔄" : "✅"}</td>
                  <td>{r.gens_ok}</td>
                  <td>{r.baseline ? `${Math.round(r.baseline.profit).toLocaleString()} (MDD ${_rlNum(r.baseline.mdd, 1)})` : "—"}</td>
                  <td>
                    {r.top_slot
                      ? `${r.top_slot.param}: 중심 ${r.top_slot.center} · 평균 ${Math.round(r.top_slot.mean_profit || 0).toLocaleString()} (score ${_rlNum(r.top_slot.plateau_score, 2)})`
                      : r.grid
                        ? `격자 ${r.grid.cells}셀 · 흑자 ${Math.round((r.grid.positive_ratio || 0) * 100)}% · mesa ${r.grid.mesa}`
                        : "—"}
                  </td>
                  <td>{r.best_profit != null ? Math.round(r.best_profit).toLocaleString() : "—"}</td>
                  <td>{(r.time_buckets || []).join(",") || "—"}</td>
                  <td>{r.shape_r2 != null ? `${_rlNum(r.shape_r2, 2)}·${r.stagnation_days}일` : "—"}</td>
                  <td>{r.corr_vs_frozen != null ? _rlNum(r.corr_vs_frozen, 2) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="research-empty" style={{ marginTop: 6 }}>연도 분해 (per-trade CSV 집계)</div>
      <table className="mono" style={{ fontSize: 11, width: "100%" }}>
        <thead><tr><th>gen</th><th>label</th><th>연도별 손익(거래수·승률)</th></tr></thead>
        <tbody>
          {gens.map(g => (
            <tr key={g.gen_no}>
              <td>{g.gen_no}</td>
              <td>{g.label || g.buy_name || "—"}</td>
              <td>
                {(g.years || []).length
                  ? g.years.map(y => `${y.year}: ${Math.round(y.profit).toLocaleString()} (${y.trades}건·${Math.round((y.win_rate || 0) * 100)}%)`).join("  ·  ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="research-empty" style={{ marginTop: 8 }}>
        선택기 미리보기 — selected: {preview && preview.selected ? "TRUE" : "false"}
        {preview && preview.mdd_limit != null ? ` · mdd_limit ${_rlNum(preview.mdd_limit, 2)}` : ""}
        {preview && preview.selected_candidate
          ? ` · gen${preview.selected_candidate.gen_no} ${preview.selected_candidate.label || preview.selected_candidate.buy_name}`
          : ""}
      </div>
      {preview && Array.isArray(preview.rejected) && preview.rejected.length > 0 && (
        <ul className="mono" style={{ fontSize: 11 }}>
          {preview.rejected.map(rj => (
            <li key={rj.gen_no}>gen{rj.gen_no} {rj.label || ""}: {(rj.reasons || []).join("; ")}</li>
          ))}
        </ul>
      )}

      <div className="research-controls" style={{ marginTop: 8 }}>
        <label>
          <span>gen</span>
          <input type="number" value={autopsyGen} min={0}
                 onChange={(e) => setAutopsyGen(Number(e.target.value) || 0)}
                 style={{ width: 64 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchAutopsy}>부검·반사실·MC 보기</button>
        <datalist id="rl-run-options">
          {runOptions.map(id => <option key={id} value={id} />)}
        </datalist>
        <label>
          <span>비교 run</span>
          <input type="text" value={compareRun} placeholder="다른 스윕 run_id (선택)"
                 list="rl-run-options"
                 onChange={(e) => setCompareRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchTmap}>TMAP 지도</button>
        <label>
          <span>격자 run</span>
          <input type="text" value={gridRun} placeholder="--grid 스윕 run_id"
                 list="rl-run-options"
                 onChange={(e) => setGridRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchGrid}>2-D 히트맵</button>
        <button type="button" className="research-tab" onClick={fetchNiche}>니치 비교</button>
      </div>
      {autopsy && (
        <div className="mono" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
          {autopsy.status !== "ok"
            ? `autopsy: ${autopsy.status}`
            : `${autopsy.entry_summary || "(진입 부검 없음)"}\n\n${autopsy.exit_summary || "(청산 부검 없음)"}`}
        </div>
      )}

      {cf && cf.status === "ok" && Array.isArray(cf.suggestions) && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">반사실 필터 제안 (백테 0회·인샘플 advisory — 채택 시 정식 파이프라인 검증 필수)</div>
          {cf.suggestions.length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>총손익이 깎이지 않는 강화 필터 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>필터</th><th>거래</th><th>총손익</th><th>승률</th><th>잘린 거래 순손익</th><th>최근연도</th></tr></thead>
                <tbody>
                  {cf.suggestions.map((s, i) => (
                    <tr key={i}>
                      <td>{s.filter}</td>
                      <td>{s.base_trades}→{s.kept_trades}</td>
                      <td>{Math.round((s.profit_ratio || 0) * 100)}%</td>
                      <td>{Math.round((s.base_win_rate || 0) * 100)}%→{Math.round((s.kept_win_rate || 0) * 100)}%</td>
                      <td>{Math.round(s.cut_net_profit || 0).toLocaleString()}</td>
                      <td>{s.recent_year
                        ? `${s.recent_year.year}: ${Math.round(s.recent_year.base_profit).toLocaleString()}→${Math.round(s.recent_year.kept_profit).toLocaleString()}`
                        : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {mc && mc.status === "ok" && mc.mc && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            블록 부트스트랩 MC (일별 손익·레짐 군집 보존 — iid 거래 추출 MC의 OOS 전이 실패 교훈 반영)
          </div>
          <div className="mono" style={{ fontSize: 11 }}>
            {`P(총손익>0)=${Math.round((mc.mc.p_positive || 0) * 100)}% · 총손익 p05/p50/p95 = `
              + `${Math.round(mc.mc.profit_p05).toLocaleString()} / ${Math.round(mc.mc.profit_p50).toLocaleString()} / ${Math.round(mc.mc.profit_p95).toLocaleString()}`
              + ` · MDD(낙폭금액) p50/p95 = ${Math.round(mc.mc.mdd_p50).toLocaleString()} / ${Math.round(mc.mc.mdd_p95).toLocaleString()}`
              + ` (${mc.mc.n_days}일·${mc.mc.n_boot}회·블록 ${mc.mc.block_len}일)`}
          </div>
          <_McFanChart fan={mc.mc.fan} />
        </div>
      )}

      {equity && equity.status === "ok" && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            {`누적 수익곡선 — gen ${equity.gen_no}${equity.label ? " · " + equity.label : ""}`
              + ` · ${equity.n_days}거래일 · 총 ${Math.round(equity.total).toLocaleString()}`}
          </div>
          <_EquityChart cum={equity.cum} />
        </div>
      )}

      {tmap && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            TMAP 경향성 지도 (고원 &gt; 피크 — 이웃 θ도 흑자인 영역이 진짜)
          </div>
          {(!tmap.count || !Object.keys(tmap.params || {}).length)
            ? <div className="mono" style={{ fontSize: 11 }}>이 run은 TMAP 스윕이 아닙니다 (tmap_sweep run_id를 선택하세요)</div>
            : (
              <div>
                <div className="mono" style={{ fontSize: 11 }}>
                  {tmap.baseline
                    ? `베이스라인(θ=기본값): 손익 ${Math.round(tmap.baseline.profit).toLocaleString()} · MDD ${_rlNum(tmap.baseline.mdd, 2)} · ${tmap.baseline.trades}건`
                    : "베이스라인 없음"}
                </div>
                <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                  <thead><tr><th>슬롯(θ)</th><th>응답 곡선</th><th>plateau score</th><th>고원 중심</th><th>폭</th><th>고원 평균손익</th><th>흑자율</th><th>절벽(최대 점프)</th><th>중심 형태(R²·정체일)</th>{tmap.compare && <th>비교 run(중심·score)</th>}</tr></thead>
                  <tbody>
                    {Object.entries(tmap.params)
                      .sort((a, b) => (b[1].plateau_score || 0) - (a[1].plateau_score || 0))
                      .map(([name, m]) => {
                        const cm = (tmap.compare && tmap.compare.params) ? tmap.compare.params[name] : null;
                        return (
                          <tr key={name}>
                            <td>{name}</td>
                            <td><_CurveSpark curve={m.curve} /></td>
                            <td>{_rlNum(m.plateau_score, 3)}</td>
                            <td>{m.plateau ? m.plateau.center_value : "—"}</td>
                            <td>{m.plateau ? m.plateau.width : "—"}</td>
                            <td>{m.plateau ? Math.round(m.plateau.mean_profit).toLocaleString() : "—"}</td>
                            <td>{Math.round((m.positive_ratio || 0) * 100)}%</td>
                            <td>{m.cliff ? `${Math.round(m.cliff.jump).toLocaleString()} @${m.cliff.between.join("→")}` : "—"}</td>
                            <td>{m.center_shape ? `${_rlNum(m.center_shape.uptrend_r2, 2)}·${m.center_shape.max_stagnation_days}일` : "—"}</td>
                            {tmap.compare && <td>{cm && cm.plateau ? `${cm.plateau.center_value} · ${_rlNum(cm.plateau_score, 2)}` : "—"}</td>}
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
                {tmap.compare && (
                  <div className="research-empty">
                    비교 run: {tmap.compare.run_id || "—"} — 구간별 경향 발산 확인용(M12). 다년 지도의 고원만 동결 자격.
                  </div>
                )}
              </div>
            )}
        </div>
      )}

      {grid && grid.count > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>
              {`2-D 격자 히트맵 (${grid.param_a} × ${grid.param_b}) — ★=mesa(4-이웃 전부 흑자) · 흑자율 ${Math.round((grid.positive_ratio || 0) * 100)}%`
                + (grid.baseline ? ` · 베이스라인 ${Math.round(grid.baseline.profit).toLocaleString()}` : "")}
            </span>
            <button type="button" className="research-tab"
                    onClick={() => setGridMetric(gridMetric === "profit" ? "mdd" : "profit")}>
              색: {gridMetric === "profit" ? "수익" : "MDD"}
            </button>
          </div>
          <_GridHeatmap grid={grid} metric={gridMetric} />
        </div>
      )}
      {grid && grid.count === 0 && (
        <div className="mono" style={{ fontSize: 11 }}>격자 run 아님(--grid 스윕 run_id를 입력하세요)</div>
      )}
    </div>
  );
}

/* C6(2026-06-11) — 2-D 격자 히트맵: 수익(부호·크기) 또는 MDD(E5 토글)를 색으로, mesa를 ★로. */
function _GridHeatmap({ grid, metric }) {
  const useMdd = metric === "mdd";
  const cells = {};
  (grid.cells || []).forEach(c => { cells[c.a + "|" + c.b] = c; });
  const maxAbs = Math.max(1, ...((grid.cells || []).map(c => Math.abs(useMdd ? c.mdd : c.profit))));
  const mesaSet = new Set((grid.mesa_cells || []).map(m => m.a + "|" + m.b));
  return (
    <table className="mono" style={{ fontSize: 10, marginTop: 4 }}>
      <thead>
        <tr>
          <th>{grid.param_a + " \\ " + grid.param_b}</th>
          {(grid.b_values || []).map(b => <th key={b} style={{ padding: "2px 6px" }}>{b}</th>)}
        </tr>
      </thead>
      <tbody>
        {(grid.a_values || []).map(a => (
          <tr key={a}>
            <th style={{ padding: "2px 6px" }}>{a}</th>
            {(grid.b_values || []).map(b => {
              const c = cells[a + "|" + b];
              if (!c) return <td key={b}>—</td>;
              const value = useMdd ? c.mdd : c.profit;
              const alpha = (0.15 + 0.7 * Math.abs(value) / maxAbs).toFixed(2);
              const bg = useMdd
                ? `rgba(200,80,80,${alpha})`  /* MDD — 클수록 진한 적색(위험 지형). */
                : (c.profit > 0 ? `rgba(60,160,90,${alpha})` : `rgba(200,80,80,${alpha})`);
              const isMesa = mesaSet.has(a + "|" + b);
              return (
                <td key={b}
                    title={`${grid.param_a}=${a}, ${grid.param_b}=${b} · 손익 ${Math.round(c.profit).toLocaleString()} · MDD ${_rlNum(c.mdd, 2)} · ${c.trades}건`}
                    style={{ background: bg, textAlign: "right", padding: "2px 6px",
                             outline: isMesa ? "2px solid #d4af37" : "none" }}>
                  {useMdd ? _rlNum(c.mdd, 1) : Math.round(c.profit / 10000).toLocaleString() + "만"}{isMesa ? "★" : ""}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* E2/D4(2026-06-11) — 누적 수익곡선: '우상향 그림'을 직접 렌더(0선 점선). */
function _EquityChart({ cum }) {
  const pts = (cum || []).map(Number).filter(v => isFinite(v));
  if (pts.length < 2) return null;
  const W = 620, H = 150, PAD = 6;
  const min = Math.min(0, ...pts), max = Math.max(0, ...pts);
  const span = Math.max(max - min, 1);
  const x = i => PAD + (i / (pts.length - 1)) * (W - PAD * 2);
  const y = v => H - PAD - ((v - min) / span) * (H - PAD * 2);
  const path = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg width={W} height={H} style={{ background: "rgba(255,255,255,0.03)", borderRadius: 4 }}>
      <line x1={PAD} y1={y(0)} x2={W - PAD} y2={y(0)} stroke="#777" strokeDasharray="3,3" strokeWidth="0.8" />
      <path d={path} fill="none" stroke={last >= 0 ? "#4c9" : "#c66"} strokeWidth="1.8" />
      <text x={W - PAD - 4} y={y(last) - 6} fill="#9ab" fontSize="10" textAnchor="end">
        {Math.round(last).toLocaleString()}
      </text>
    </svg>
  );
}

/* C6 보조 — 1-D 응답 곡선 스파크라인(0선 점선 기준, 흑자 구간이 한눈에). */
function _CurveSpark({ curve }) {
  const pts = (curve || []).filter(p => p && p.ok);
  if (pts.length < 2) return null;
  const W = 90, H = 22;
  const profits = pts.map(p => p.profit || 0);
  const min = Math.min(0, ...profits), max = Math.max(0, ...profits);
  const span = Math.max(max - min, 1);
  const x = i => 2 + (i / (pts.length - 1)) * (W - 4);
  const y = v => H - 2 - ((v - min) / span) * (H - 4);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.profit || 0).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} style={{ verticalAlign: "middle" }}>
      <line x1="2" y1={y(0)} x2={W - 2} y2={y(0)} stroke="#777" strokeDasharray="2,2" strokeWidth="0.8" />
      <path d={path} fill="none" stroke="#5b9" strokeWidth="1.5" />
    </svg>
  );
}

function _McFanChart({ fan }) {
  if (!fan || !Array.isArray(fan.x) || !fan.x.length) return null;
  const W = 320, H = 90, PAD = 4;
  const all = [].concat(fan.p05 || [], fan.p95 || [], fan.p50 || []);
  const lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
  const span = (hi - lo) || 1;
  const px = (i) => PAD + (W - 2 * PAD) * (fan.x[i] || 0);
  const py = (v) => H - PAD - (H - 2 * PAD) * ((v - lo) / span);
  const pts = (arr) => arr.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(" ");
  const band = (upper, lower) =>
    pts(upper) + " " + lower.map((v, i) => `${px(lower.length - 1 - i).toFixed(1)},${py(lower[lower.length - 1 - i]).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} style={{ display: "block", marginTop: 4 }}
         role="img" aria-label="MC fan chart">
      <polygon points={band(fan.p95, fan.p05)} fill="rgba(80,140,200,0.18)" stroke="none" />
      <polygon points={band(fan.p75, fan.p25)} fill="rgba(80,140,200,0.28)" stroke="none" />
      <polyline points={pts(fan.p50)} fill="none" stroke="rgba(120,190,255,0.95)" strokeWidth="1.5" />
      <line x1={PAD} y1={py(0)} x2={W - PAD} y2={py(0)}
            stroke="rgba(200,200,200,0.4)" strokeDasharray="3,3" strokeWidth="1" />
    </svg>
  );
}

function ResearchLabPanel({ baseUrl, wsStatus, runId }) {
  const [tab, setTab] = useState_rl("edge");
  const [fullscreen, setFullscreen] = useState_rl(false);  /* 전체 화면 토글. */
  const [opsStrip, setOpsStrip] = useState_rl(null);       /* 탭 공통 운영 띠. */

  useEffect_rl(() => {
    if (!baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        setOpsStrip(j);
        try {  /* F7 — 정체 의심 시 브라우저 탭 제목 경고(자리 비움 감지용). */
          const stalled = ((j && j.active) || []).some(a => a.health !== "active");
          const base = document.title.replace(/^⚠️ /, "");
          document.title = (stalled ? "⚠️ " : "") + base;
        } catch (e) { /* 제목 갱신 실패는 무시. */ }
      })
      .catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [baseUrl]);
  const [method, setMethod] = useState_rl("spearman");
  const [axis, setAxis] = useState_rl("time");
  const [data, setData] = useState_rl(null);
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const needsCorrelation = tab === "correlation" || tab === "combos";

  const refreshCorrelation = useCallback_rl(() => {
    if (!needsCorrelation || isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const url = baseUrl + "/variable_correlation?run_id=" + encodeURIComponent(runId)
      + "&method=" + encodeURIComponent(method);
    fetch(url, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, method, needsCorrelation, runId]);

  useEffect_rl(() => {
    refreshCorrelation();
  }, [refreshCorrelation]);

  const matrixRows = (data && Array.isArray(data.feature_matrix)) ? data.feature_matrix : [];
  const outcomeRows = (data && Array.isArray(data.outcome_correlations)) ? data.outcome_correlations : [];
  const rangeRows = (data && Array.isArray(data.range_summaries)) ? data.range_summaries : [];
  const segmentSummary = (data && data.segment_summaries) || {};
  const recencyResearch = (data && data.recency_research) || null;
  const pairRows = useMemo_rl(() => {
    const raw = (data && Array.isArray(data.interaction_candidates) && data.interaction_candidates.length)
      ? data.interaction_candidates
      : ((data && Array.isArray(data.top_pairs) && data.top_pairs.length) ? data.top_pairs : matrixRows);
    return [...raw].sort((a, b) => (
      (b.research_score || b.abs_correlation || Math.abs(b.correlation || 0))
      - (a.research_score || a.abs_correlation || Math.abs(a.correlation || 0))
    ));
  }, [data, matrixRows]);

  let body = null;
  if (tab === "edge") {
    body = <EdgeRatioPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />;
  } else if (tab === "validation") {
    body = <_ValidationPanel baseUrl={baseUrl} runId={runId} isDemo={isDemo} />;
  } else if (tab === "feature") {
    body = (
      <div>
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <FeatureImportancePanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </div>
    );
  } else if (isDemo || !runId) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="insufficient run context for correlation research." /></div>;
  } else if (err) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message={"insufficient response: " + err} /></div>;
  } else if (loading && !data) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="loading correlation research..." /></div>;
  } else if (tab === "correlation") {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CorrelationHeatmap rows={matrixRows.length ? matrixRows : outcomeRows} />
        <_RangeSummaryList rows={rangeRows} />
        <_SegmentSummaryList summary={segmentSummary} axis={axis} />
        <_RecencyResearchBadge recency={recencyResearch} />
      </div>
    );
  } else {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CombinationList rows={pairRows} />
      </div>
    );
  }

  const shellStyle = fullscreen
    ? { position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 9999,
        background: "#0d1117", overflow: "auto", padding: "12px 18px" }
    : undefined;
  const activeOps = (opsStrip && opsStrip.active) || [];
  return (
    <div className="research-lab-shell" style={shellStyle}>
      <div className="research-tabs" role="tablist" aria-label="Research Lab"
           style={{ display: "flex", alignItems: "center" }}>
        {RESEARCH_TABS.map(item => (
          <button key={item.id}
                  type="button"
                  className={"research-tab" + (tab === item.id ? " active" : "")}
                  onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
        <button type="button" className="research-tab" style={{ marginLeft: "auto" }}
                onClick={() => setFullscreen(!fullscreen)}>
          {fullscreen ? "✕ 전체 화면 닫기" : "⛶ 전체 화면"}
        </button>
      </div>
      <div className="mono" style={{ fontSize: 11, margin: "2px 0 6px", opacity: 0.9 }}>
        {activeOps.length
          ? activeOps.map(a =>
              `🔄 ${a.run_id} · ${a.gens}세대 · ${a.last_label || ""} · ${a.health === "active" ? "진행 중" : "⚠️ 정체 의심"}`
            ).join("  |  ")
          : "실행 중 작업 없음"}
      </div>
      {body}
    </div>
  );
}

Object.assign(window, { ResearchLabPanel });
