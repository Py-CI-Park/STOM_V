/* Backtest workbench tab — 다중 잡 오버레이·진화 세대 셀렉터·포트폴리오 결합 분석 묶음
   (split from backtest.jsx). 접이식 분석 섹션이 소비. 순수 SVG(외부 차트 라이브러리 금지).
     - 다중 잡 오버레이: 2~4개 수익곡선 겹침/분할(GET /bt/overlay).
     - 접이식 섹션 래퍼(BtCollapsible) — 수직 과적 해소.
     - 진화 세대 셀렉터: run 선택(GET /runs) → 세대 선택(GET /bt/evo_gens).
     - 포트폴리오 결합 분석: 잡/세대 다중 선택(2~6) → POST /bt/portfolio.

   팔레트(_BT_OVERLAY_COLORS)·숫자포맷(_btNum)·금액포맷(_pfFmtMoney)은 bt-tab-utils 에서 공유.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_bt, useEffect_bt, useCallback_bt, useRef_bt, _btFetchJson, _btPostJson, _BT_OVERLAY_COLORS, _btNum, _pfFmtMoney } from "./bt-tab-utils.jsx";
import { fetchRunsShared } from "./runs-shared.jsx";
// v5.13.0(H3) — 진화 세대 행에서 조건식 즉시 열람. KEEP on ONE physical line.
import { CodeViewer } from "./code-viewer.jsx";

// ===========================================================================
// 3b-3. 다중 잡 오버레이 — 결과 라이브러리에서 2~4개 선택 → 수익곡선 겹쳐 보기.
//   GET /bt/overlay?job_ids=a,b,c. 정규화 토글(첫 포인트 0 기준)·범례.
// ===========================================================================
function BtOverlayCurves({ series, normalize }) {
  if (!series || series.length === 0) return <div className="research-empty">오버레이할 곡선이 없습니다.</div>;
  const W = 680, H = 220, padL = 8, padR = 8, padT = 12, padB = 12;
  // 각 시리즈의 cum_profit 배열(정규화 시 첫 포인트를 0으로 평행이동).
  const lines = series.map(s => {
    const cums = (s.cumulative || []).map(p => p.cum_profit || 0);
    const base = (normalize && cums.length > 0) ? cums[0] : 0;
    return cums.map(v => v - base);
  });
  const allVals = lines.reduce((acc, ln) => acc.concat(ln), [0]);
  const lo = Math.min(...allVals), hi = Math.max(...allVals);
  const span = (hi - lo) || 1;
  const maxN = Math.max(1, ...lines.map(l => l.length));
  const x = (i, n) => padL + (n <= 1 ? 0 : (i * (W - padL - padR) / (Math.max(1, maxN - 1))));
  const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
  const zeroY = y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 220 }} preserveAspectRatio="none">
      <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} stroke="var(--line-1)" strokeDasharray="3 3" />
      {lines.map((ln, si) => {
        if (ln.length === 0) return null;
        const path = ln.map((v, i) => (i === 0 ? "M" : "L") + x(i, ln.length).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
        return <path key={si} d={path} fill="none" stroke={_BT_OVERLAY_COLORS[si % _BT_OVERLAY_COLORS.length]} strokeWidth="1.6" />;
      })}
    </svg>
  );
}

// 분할(small-multiple) 그리드 — 각 잡을 자기 셀의 작은 SVG 수익곡선으로 그린다.
//   BtOverlayCurves 의 단일 시리즈 경로(누적·정규화)를 셀마다 재사용한다. normalize 토글은
//   겹침/분할 양쪽에서 동일하게 동작한다(정규화 시 첫 포인트 0 기준 평행이동).
//   열 수: 2~3개 → 2열, 4개 → 2열(2×2). 가독성 위해 최대 2열 고정(작은 화면 대비).
function _btSplitCellPath(cumulative, normalize, W, H, padL, padR, padT, padB) {
  const cums = (cumulative || []).map(p => p.cum_profit || 0);
  const base = (normalize && cums.length > 0) ? cums[0] : 0;
  const vals = cums.map(v => v - base);
  if (vals.length === 0) return { path: "", zeroY: padT + (H - padT - padB) / 2 };
  const withZero = vals.concat([0]);
  const lo = Math.min(...withZero), hi = Math.max(...withZero);
  const span = (hi - lo) || 1;
  const n = vals.length;
  const x = (i) => padL + (n <= 1 ? 0 : (i * (W - padL - padR) / (n - 1)));
  const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
  const path = vals.map((v, i) => (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
  return { path, zeroY: y(0) };
}

function BtSplitGrid({ series, normalize }) {
  if (!series || series.length === 0) return <div className="research-empty">분할할 곡선이 없습니다.</div>;
  const W = 320, H = 140, padL = 6, padR = 6, padT = 10, padB = 10;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
      {series.map((s, si) => {
        const { path, zeroY } = _btSplitCellPath(s.cumulative, normalize, W, H, padL, padR, padT, padB);
        const color = _BT_OVERLAY_COLORS[si % _BT_OVERLAY_COLORS.length];
        const pos = Number(s.summary && s.summary.total_profit_pct) >= 0;
        return (
          <div key={s.job_id} style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 8, background: "var(--bg-0)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <span style={{ width: 10, height: 3, background: color, display: "inline-block", flexShrink: 0 }}></span>
              <span className="mono" style={{ fontSize: 10, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
              <span className="mono" style={{ fontSize: 10, color: (pos ? "var(--teal)" : "var(--red)") }}>
                {_btNum(s.summary && s.summary.total_profit_pct)}%
              </span>
            </div>
            <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 120 }} preserveAspectRatio="none">
              <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} stroke="var(--line-1)" strokeDasharray="3 3" />
              {path && <path d={path} fill="none" stroke={color} strokeWidth="1.6" />}
            </svg>
          </div>
        );
      })}
    </div>
  );
}

function BtOverlayPanel({ baseUrl, isDemo, jobs }) {
  const [picked, setPicked] = useState_bt([]);   // job_id 목록(2~4).
  const [normalize, setNormalize] = useState_bt(false);
  const [viewMode, setViewMode] = useState_bt("overlay");  // overlay(겹침) | split(분할).
  const [result, setResult] = useState_bt(null);
  const [busy, setBusy] = useState_bt(false);
  const [err, setErr] = useState_bt("");

  const doneJobs = (jobs || []).filter(j => j.status === "success" || j.status === "no_trades");
  const toggle = (jobId) => {
    setPicked(prev => prev.includes(jobId)
      ? prev.filter(p => p !== jobId)
      : (prev.length >= 4 ? prev : prev.concat([jobId])));
  };
  const run = () => {
    if (isDemo || !baseUrl || picked.length < 2) return;
    setBusy(true); setErr(""); setResult(null);
    _btFetchJson(baseUrl + "/bt/overlay?job_ids=" + encodeURIComponent(picked.join(",")), 15000)
      .then(j => {
        if (j && j.status === "ok") setResult(j);
        else { setErr((j && j.message) || "오버레이 실패"); }
      })
      .catch(e => setErr("실패: " + e))
      .finally(() => setBusy(false));
  };
  const clearAll = () => { setPicked([]); setResult(null); setErr(""); };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          다중 잡 오버레이
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>{picked.length}/4</span>
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {/* 보기 방식 토글 [겹침|분할] — 겹침은 한 차트에, 분할은 잡별 small-multiple. */}
          <div style={{ display: "flex", gap: 4 }}>
            {[["overlay", "겹침"], ["split", "분할"]].map(([m, lbl]) => (
              <button key={m} onClick={() => setViewMode(m)} className="mono"
                title={m === "overlay" ? "겹침 — 모든 잡 곡선을 한 차트에 겹쳐 그립니다." : "분할 — 잡마다 작은 차트로 나눠 그립니다."}
                style={{
                  padding: "4px 9px", fontSize: 10.5, borderRadius: 5, cursor: "pointer",
                  border: "1px solid " + (viewMode === m ? "var(--teal)" : "var(--line-1)"),
                  background: viewMode === m ? "rgba(76,214,179,0.1)" : "transparent",
                  color: viewMode === m ? "var(--teal)" : "var(--ink-2)",
                }}>
                {lbl}
              </button>
            ))}
          </div>
          <button className="btn primary sm" onClick={run} disabled={isDemo || busy || picked.length < 2}>
            {busy ? "로딩…" : "▸ 겹쳐보기"}
          </button>
          <button className="btn ghost sm" onClick={clearAll} disabled={picked.length === 0}>비우기</button>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 완료 잡을 겹쳐볼 수 있습니다.</div>
        ) : (
          <>
            {doneJobs.length === 0 ? (
              <div className="research-empty">완료된 잡이 없습니다.</div>
            ) : (
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {doneJobs.slice(0, 16).map(j => {
                  const on = picked.includes(j.job_id);
                  return (
                    <button key={j.job_id} className="mono" onClick={() => toggle(j.job_id)}
                      disabled={!on && picked.length >= 4}
                      style={{
                        fontSize: 10, padding: "3px 7px", borderRadius: 4, cursor: "pointer",
                        border: "1px solid " + (on ? "var(--teal)" : "var(--line-1)"),
                        background: on ? "rgba(76,214,179,0.1)" : "transparent",
                        color: on ? "var(--teal)" : "var(--ink-2)",
                      }}
                      title={j.job_id}>
                      {on ? "✓ " : ""}{j.job_id.slice(0, 14)}
                    </button>
                  );
                })}
              </div>
            )}
            {picked.length < 2 && (
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>오버레이에는 2~4개 잡이 필요합니다.</div>
            )}
            {err && <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>}
            {result && result.series && result.series.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--line-1)", paddingTop: 10 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <button className="mono" onClick={() => setNormalize(n => !n)}
                    style={{
                      padding: "4px 9px", fontSize: 10.5, borderRadius: 5, cursor: "pointer",
                      border: "1px solid " + (normalize ? "var(--amber)" : "var(--line-1)"),
                      background: normalize ? "rgba(240,179,90,0.1)" : "transparent",
                      color: normalize ? "var(--amber)" : "var(--ink-2)",
                    }}>
                    {normalize ? "✓ " : ""}정규화(첫 포인트 0)
                  </button>
                  {/* 범례 */}
                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    {result.series.map((s, i) => (
                      <span key={s.job_id} className="mono" style={{ fontSize: 10, display: "inline-flex", alignItems: "center", gap: 5 }}>
                        <span style={{ width: 12, height: 3, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], display: "inline-block" }}></span>
                        {s.label}
                      </span>
                    ))}
                  </div>
                </div>
                {viewMode === "split"
                  ? <BtSplitGrid series={result.series} normalize={normalize} />
                  : <BtOverlayCurves series={result.series} normalize={normalize} />}
                {/* 시리즈별 요약 */}
                <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  {result.series.map((s, i) => (
                    <div key={s.job_id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 6px", borderBottom: "1px solid var(--line-1)" }}>
                      <span style={{ width: 10, height: 10, borderRadius: 2, background: _BT_OVERLAY_COLORS[i % _BT_OVERLAY_COLORS.length], flexShrink: 0 }}></span>
                      <span className="mono" style={{ fontSize: 10.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
                      <span className="mono" style={{ fontSize: 10.5, color: (Number(s.summary.total_profit_pct) >= 0 ? "var(--teal)" : "var(--red)") }}>
                        {_btNum(s.summary.total_profit_pct)}%
                      </span>
                      <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", width: 70, textAlign: "right" }}>
                        {s.summary.trade_count}거래
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3c. 접이식 섹션 래퍼 — 수직 과적 해소(evo/포트폴리오를 접을 수 있게).
// ===========================================================================
function BtCollapsible({ title, accent, defaultOpen, children }) {
  const [open, setOpen] = useState_bt(!!defaultOpen);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: open ? 10 : 0 }}>
      <button onClick={() => setOpen(o => !o)} className="mono"
        style={{
          display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 6,
          border: "1px solid var(--line-1)", background: "var(--bg-1)", cursor: "pointer",
          color: "var(--ink-1)", fontSize: 12, textAlign: "left",
        }}>
        <span className="dot" style={{ background: accent || "var(--ink-3)" }}></span>
        <span style={{ flex: 1 }}>{title}</span>
        <span style={{ color: "var(--ink-3)" }}>{open ? "▾ 접기" : "▸ 펼치기"}</span>
      </button>
      {open && children}
    </div>
  );
}

// ===========================================================================
// 4. 진화 세대 분석 셀렉터 — run 선택(GET /runs) → 세대 선택(GET /bt/evo_gens).
//   선택 시 부모로 {run_id, gen_no} 를 올려 BtResultArea 가 run/gen 모드로 로드한다.
//   진화 탭 파일은 건드리지 않는다 — /runs·/bt/evo_gens 읽기 전용 계약만 소비.
// ===========================================================================
function BtEvoSelector({ baseUrl, isDemo, onPickGen, activeEvo, compareA, onSetCompareA, onCompareB }) {
  const [runs, setRuns] = useState_bt([]);
  const [runId, setRunId] = useState_bt("");
  const [gens, setGens] = useState_bt([]);
  const [loadingRuns, setLoadingRuns] = useState_bt(false);
  const [loadingGens, setLoadingGens] = useState_bt(false);
  // v5.13.0(H3) — 조건식 즉시 열람 모달 상태({gen_no, buy_name, sell_name} | null).
  const [codeGen, setCodeGen] = useState_bt(null);
  const autoPickedRunRef = useRef_bt("");

  // run 목록 로드(최신 우선 — 서버 정렬 그대로).
  const loadRuns = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setRuns([]); return; }
    setLoadingRuns(true);
    fetchRunsShared(baseUrl, { timeoutMs: 6000 })
      .then(j => {
        const items = Array.isArray(j && j.runs) ? j.runs : [];
        setRuns(items);
        setRunId(current => current || (activeEvo && activeEvo.run_id) || (items[0] && items[0].run_id) || "");
      })
      .catch(() => setRuns([]))
      .finally(() => setLoadingRuns(false));
  }, [baseUrl, isDemo, activeEvo]);
  useEffect_bt(() => { loadRuns(); }, [loadRuns]);

  // run 선택 시 세대 목록 로드.
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !runId) { setGens([]); return; }
    setLoadingGens(true);
    _btFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(runId), 6000)
      .then(j => {
        const items = Array.isArray(j && j.items) ? j.items : [];
        setGens(items);
        if (!activeEvo && autoPickedRunRef.current !== runId) {
          const candidate = items.findLast(g => g && g.status === "ok" && g.has_csv)
            || items.findLast(g => g && g.status === "ok");
          if (candidate) {
            autoPickedRunRef.current = runId;
            onPickGen(runId, candidate.gen_no); // 최신 유효 세대 자동 선택.
          }
        }
      })
      .catch(() => setGens([]))
      .finally(() => setLoadingGens(false));
  }, [baseUrl, isDemo, runId, activeEvo, onPickGen]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          진화 세대 결과 라이브러리
        </div>
        <button className="btn ghost sm" onClick={loadRuns} disabled={isDemo || loadingRuns}>
          {loadingRuns ? "로딩…" : "↻ run"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 진화 run 목록이 표시됩니다.</div>
        ) : (
          <>
            <div className="field">
              <label>진화 run</label>
              <select className="select" value={runId} onChange={e => setRunId(e.target.value)}>
                <option value="">— run 선택 —</option>
                {runs.map(r => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}{r.label ? " · " + r.label : ""}{r.status ? " [" + r.status + "]" : ""}
                  </option>
                ))}
              </select>
            </div>
            {runId && (
              <div style={{ display: "flex", flexDirection: "column", gap: 3, maxHeight: 280, overflowY: "auto" }}>
                {loadingGens ? (
                  <div className="research-empty">세대 로딩 중…</div>
                ) : gens.length === 0 ? (
                  <div className="research-empty">세대가 없습니다</div>
                ) : gens.map(g => {
                  const active = activeEvo && activeEvo.run_id === runId && activeEvo.gen_no === g.gen_no;
                  // v5.11.3 — 세대끼리도 A/B 비교가 된다. 기준(A)이 잡혀 있고 다른 세대이며
                  //   양쪽 다 결과 CSV 가 있어야 비교 표본이 성립한다.
                  const evoKey = runId + "/" + g.gen_no;
                  const isCompareA = compareA === evoKey;
                  const canCompareB = !!compareA && !isCompareA && g.has_csv;
                  return (
                    <div key={g.gen_no}
                      style={{
                        padding: "6px 9px", borderRadius: 5,
                        border: "1px solid " + (active ? "var(--violet)" : (isCompareA ? "var(--teal-dim)" : "var(--line-1)")),
                        background: active ? "rgba(168,130,255,0.08)" : "var(--bg-0)",
                        display: "flex", alignItems: "center", gap: 8,
                      }}>
                      <button onClick={() => onPickGen(runId, g.gen_no)}
                        title="이 세대의 결과 분석을 연다"
                        style={{
                          textAlign: "left", background: "transparent", border: 0, padding: 0,
                          cursor: "pointer", display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0,
                        }}>
                        <span className="mono" style={{ fontSize: 11, color: active ? "var(--violet)" : "var(--ink-0)", flexShrink: 0 }}>
                          Gen {g.gen_no}
                        </span>
                        <span className={"badge " + (g.gate_passed ? "done" : "idle")} style={{ flexShrink: 0 }}>
                          {g.gate_passed ? "gate" : "—"}
                        </span>
                        {/* v5.13.0(H3) — 조건식 이름을 우선 표시(어느 조건식인지 즉시 식별). */}
                        <span className="mono" title={(g.buy_name || "") + (g.sell_name ? " / " + g.sell_name : "")}
                              style={{ fontSize: 10, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
                          {g.buy_name || g.strategy_gist || ""}
                        </span>
                        <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>
                          {g.trade_count}거래{g.has_csv ? "" : " ·축약"}
                        </span>
                      </button>
                      {/* v5.13.0(H3) — 조건식 즉시 열람. */}
                      <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                              title="이 세대의 매수·매도 조건식 코드를 봅니다"
                              onClick={() => setCodeGen({ gen_no: g.gen_no, buy_name: g.buy_name, sell_name: g.sell_name })}>
                        &lt;/&gt;
                      </button>
                      {typeof onSetCompareA === "function" && g.has_csv && (
                        <button className={"btn ghost sm" + (isCompareA ? " active" : "")}
                                style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                title={isCompareA ? "비교 기준(A) 해제" : "이 세대를 비교 기준(A)으로 고정"}
                                onClick={() => onSetCompareA(isCompareA ? "" : evoKey)}>A</button>
                      )}
                      {canCompareB && typeof onCompareB === "function" && (
                        <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                title={"기준(" + compareA + ") 과 이 세대를 비교"}
                                onClick={() => onCompareB(evoKey)}>B</button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
            <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
              run {runs.length}개 · 세대 {gens.length}개 (읽기 전용)
            </div>
          </>
        )}
      </div>
      {/* v5.13.0(H3) — 조건식 즉시 열람 모달. */}
      {codeGen && (
        <CodeViewer generation={codeGen} runId={runId} baseUrl={baseUrl} onClose={() => setCodeGen(null)} />
      )}
    </div>
  );
}

// ===========================================================================
// 5. 포트폴리오 결합 분석 패널 — 잡/세대 다중 선택(2~6) → POST /bt/portfolio.
//   결합 수익곡선 SVG · 상관 히트맵 · 개별 기여 표를 그린다. 워크벤치 UI 레이어
//   (부모 P-A 의 포트폴리오 상관 스캔과 역할 구분 — backtest_api docstring 참조).
//   금액포맷(_pfFmtMoney)은 bt-tab-utils 에서 공유.
// ===========================================================================
// 결합 누적수익곡선 SVG(외부 라이브러리 금지 — 순수 path).
function BtPortfolioCurve({ equity }) {
  if (!equity || equity.length === 0) return <div className="research-empty">결합 곡선 없음</div>;
  const W = 640, H = 180, padL = 8, padR = 8, padT = 12, padB = 12;
  const cums = equity.map(p => p.cum_profit || 0);
  const lo = Math.min(0, ...cums), hi = Math.max(0, ...cums);
  const span = (hi - lo) || 1;
  const n = equity.length;
  const x = (i) => padL + (n <= 1 ? 0 : (i * (W - padL - padR) / (n - 1)));
  const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
  const path = cums.map((v, i) => (i === 0 ? "M" : "L") + x(i).toFixed(1) + " " + y(v).toFixed(1)).join(" ");
  const zeroY = y(0);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: 180 }} preserveAspectRatio="none">
      <line x1={padL} y1={zeroY} x2={W - padR} y2={zeroY} stroke="var(--line-1)" strokeDasharray="3 3" />
      <path d={path} fill="none" stroke="var(--teal)" strokeWidth="1.6" />
    </svg>
  );
}

// 상관 히트맵(피어슨, -1~+1; None 은 회색).
function BtPortfolioHeatmap({ correlation }) {
  const labels = (correlation && correlation.labels) || [];
  const matrix = (correlation && correlation.matrix) || [];
  if (labels.length === 0) return null;
  const cell = (r) => {
    if (r == null) return { bg: "var(--bg-1)", txt: "—" };
    // -1(빨강) ~ 0(중립) ~ +1(청록). 절대값으로 알파.
    const a = Math.min(1, Math.abs(r));
    const color = r >= 0 ? `rgba(76,214,179,${0.12 + a * 0.5})` : `rgba(255,107,107,${0.12 + a * 0.5})`;
    return { bg: color, txt: r.toFixed(2) };
  };
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="mono" style={{ borderCollapse: "collapse", fontSize: 10 }}>
        <thead>
          <tr>
            <th style={{ padding: 4 }}></th>
            {labels.map((l, j) => (
              <th key={j} style={{ padding: 4, color: "var(--ink-3)", maxWidth: 80, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={l}>{l}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td style={{ padding: 4, color: "var(--ink-3)", maxWidth: 90, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={labels[i]}>{labels[i]}</td>
              {row.map((v, j) => {
                const c = cell(v);
                return <td key={j} style={{ padding: "6px 8px", textAlign: "center", background: c.bg, color: "var(--ink-1)", border: "1px solid var(--bg-0)" }}>{c.txt}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BtPortfolioPanel({ baseUrl, isDemo, jobs, activeEvo }) {
  // 선택 항목: [{kind:"job"|"gen", id, label}]. 최대 6개.
  const [picked, setPicked] = useState_bt([]);
  const [result, setResult] = useState_bt(null);
  const [busy, setBusy] = useState_bt(false);
  const [err, setErr] = useState_bt("");

  const addJob = (j) => {
    if (picked.length >= 6) return;
    const key = "job:" + j.job_id;
    if (picked.some(p => p.key === key)) return;
    setPicked(prev => prev.concat([{ key, kind: "job", job_id: j.job_id, label: j.job_id.slice(0, 14) }]));
  };
  const addEvo = () => {
    if (!activeEvo || picked.length >= 6) return;
    const key = "gen:" + activeEvo.run_id + "/" + activeEvo.gen_no;
    if (picked.some(p => p.key === key)) return;
    setPicked(prev => prev.concat([{
      key, kind: "gen", run_id: activeEvo.run_id, gen_no: activeEvo.gen_no,
      label: activeEvo.run_id.slice(0, 8) + "/g" + activeEvo.gen_no,
    }]));
  };
  const removeAt = (key) => setPicked(prev => prev.filter(p => p.key !== key));
  const clearAll = () => { setPicked([]); setResult(null); setErr(""); };

  const run = () => {
    if (isDemo || !baseUrl) return;
    setBusy(true); setErr(""); setResult(null);
    const items = picked.map(p => p.kind === "job"
      ? { job_id: p.job_id, label: p.label }
      : { run_id: p.run_id, gen_no: p.gen_no, label: p.label });
    _btPostJson(baseUrl + "/bt/portfolio", { items }, 20000)
      .then(j => {
        if (j && j.status === "ok") { setResult(j.portfolio); }
        else { setErr((j && j.message) || "포트폴리오 분석 실패"); }
      })
      .catch(e => setErr("실패: " + e))
      .finally(() => setBusy(false));
  };

  const doneJobs = (jobs || []).filter(j => j.status === "success" || j.status === "no_trades");

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--blue)" }}></span>
          포트폴리오 결합 분석
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
            {picked.length}/6
          </span>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button className="btn primary sm" onClick={run}
                  disabled={isDemo || busy || picked.length < 2}>
            {busy ? "분석중…" : "▸ 결합 분석"}
          </button>
          <button className="btn ghost sm" onClick={clearAll} disabled={picked.length === 0}>비우기</button>
        </div>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 잡/세대를 결합할 수 있습니다.</div>
        ) : (
          <>
            {/* 추가 소스 */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>추가:</span>
              {activeEvo && (
                <button className="btn ghost sm" onClick={addEvo} disabled={picked.length >= 6}
                        title="현재 선택된 진화 세대를 포트폴리오에 추가">
                  ＋세대 {activeEvo.run_id.slice(0, 6)}/g{activeEvo.gen_no}
                </button>
              )}
            </div>
            {/* 완료 잡 칩 */}
            {doneJobs.length > 0 && (
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {doneJobs.slice(0, 10).map(j => (
                  <button key={j.job_id} className="btn ghost sm" onClick={() => addJob(j)}
                          disabled={picked.length >= 6}
                          style={{ fontSize: 10, padding: "3px 7px" }}
                          title={"잡 " + j.job_id + " 추가"}>
                    ＋{j.job_id.slice(0, 12)}
                  </button>
                ))}
              </div>
            )}
            {/* 선택 항목 */}
            {picked.length > 0 && (
              <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                {picked.map(p => (
                  <span key={p.key} className="mono" style={{
                    fontSize: 10, padding: "3px 6px", borderRadius: 4,
                    border: "1px solid " + (p.kind === "gen" ? "var(--violet)" : "var(--teal-dim)"),
                    color: p.kind === "gen" ? "var(--violet)" : "var(--teal)",
                    display: "inline-flex", alignItems: "center", gap: 5,
                  }}>
                    {p.label}
                    <button onClick={() => removeAt(p.key)} style={{ background: "transparent", border: 0, color: "var(--ink-3)", cursor: "pointer", padding: 0 }}>✕</button>
                  </span>
                ))}
              </div>
            )}
            {picked.length < 2 && (
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                결합 분석에는 2~6개 전략(잡/세대)이 필요합니다.
              </div>
            )}
            {err && <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{err}</div>}

            {/* 결과 */}
            {result && (
              <div style={{ display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--line-1)", paddingTop: 10 }}>
                <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                  <span className="mono" style={{ fontSize: 11 }}>
                    결합 총손익 <b style={{ color: (result.combined.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)") }}>
                      {_pfFmtMoney(result.combined.total_profit_krw)}</b>
                  </span>
                  <span className="mono" style={{ fontSize: 11 }}>
                    결합 MDD <b style={{ color: "var(--red)" }}>{Math.round(result.combined.max_drawdown_krw).toLocaleString()}원</b>
                  </span>
                  <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>
                    {result.combined.trading_days}거래일 · {result.count}전략
                  </span>
                </div>
                {/* 결합 곡선 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>결합 누적수익곡선</div>
                  <BtPortfolioCurve equity={result.combined.equity} />
                </div>
                {/* 상관 히트맵 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>전략 간 일별손익 상관</div>
                  <BtPortfolioHeatmap correlation={result.correlation} />
                </div>
                {/* 개별 기여 표 */}
                <div>
                  <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginBottom: 4 }}>개별 기여</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    {result.strategies.map((s, i) => (
                      <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 6px", borderBottom: "1px solid var(--line-1)" }}>
                        <span className="mono" style={{ fontSize: 11, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.label}</span>
                        <span className="mono" style={{ fontSize: 10.5, color: (s.total_profit_krw >= 0 ? "var(--teal)" : "var(--red)") }}>
                          {_pfFmtMoney(s.total_profit_krw)}
                        </span>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", width: 64, textAlign: "right" }}>
                          기여 {s.contribution_pct.toFixed(0)}%
                        </span>
                        <span className="mono" style={{ fontSize: 10.5, color: "var(--red)", width: 90, textAlign: "right" }}>
                          MDD {Math.round(s.max_drawdown_krw).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function BtBackFinderPreflightPanel({ baseUrl, isDemo, buyName }) {
  const [data, setData] = useState_bt(null);
  const [busy, setBusy] = useState_bt(false);
  const [err, setErr] = useState_bt("");

  const load = useCallback_bt(() => {
    if (isDemo || !baseUrl || !buyName) {
      setData(null);
      setErr("");
      return;
    }
    setBusy(true);
    setErr("");
    _btFetchJson(baseUrl + "/bt/backfinder/preflight?kind=buy&name=" + encodeURIComponent(buyName), 6000)
      .then(j => setData(j || null))
      .catch(e => { setData(null); setErr(String(e)); })
      .finally(() => setBusy(false));
  }, [baseUrl, isDemo, buyName]);

  useEffect_bt(() => { load(); }, [load]);

  const ok = data && data.precondition_ok;
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: ok ? "var(--teal)" : "var(--amber)" }}></span>
          백파인더 사전 점검
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
            self.tickcols · self.tickdata
          </span>
        </div>
        <button className="btn ghost sm" onClick={load} disabled={isDemo || busy || !buyName}>
          {busy ? "점검…" : "↻ 점검"}
        </button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {!buyName ? (
          <div className="research-empty">매수 조건식을 선택하면 백파인더 사전 조건을 점검합니다.</div>
        ) : err ? (
          <div className="mono" style={{ fontSize: 11, color: "var(--red)" }}>점검 실패: {err}</div>
        ) : !data ? (
          <div className="research-empty">백파인더 사전 점검 대기 중…</div>
        ) : (
          <>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              <span className={ok ? "badge done" : "badge warn"}>{ok ? "조건 통과" : "조건 미충족"}</span>
              <span className="mono" style={{ fontSize: 10.5, color: data.has_tickcols ? "var(--teal)" : "var(--red)" }}>
                self.tickcols {data.has_tickcols ? "있음" : "없음"} · {data.cols_count == null ? "?" : data.cols_count}
              </span>
              <span className="mono" style={{ fontSize: 10.5, color: data.has_tickdata ? "var(--teal)" : "var(--red)" }}>
                self.tickdata {data.has_tickdata ? "있음" : "없음"} · {data.data_count == null ? "?" : data.data_count}
              </span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
                run_enabled={String(!!data.run_enabled)}
              </span>
            </div>
            <div className="mono" style={{ fontSize: 11, color: ok ? "var(--teal)" : "var(--ink-2)", lineHeight: 1.5 }}>
              {data.message}
            </div>
            <div className="readability-note">
              현재 웹 대시보드는 원본 GUI BackFinder 실행을 연결하지 않고, 안전한 preflight/staging만 제공합니다.
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { BtOverlayCurves, _btSplitCellPath, BtSplitGrid, BtOverlayPanel, BtCollapsible, BtEvoSelector, BtPortfolioCurve, BtPortfolioHeatmap, BtPortfolioPanel, BtBackFinderPreflightPanel };
