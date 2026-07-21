/* rp-heatmap.jsx — 리서치 프로 분석 컴포넌트 묶음 (P5.7 분해 후).
   research-pro.jsx 의 핵심 분석 카드들을 모은다(동작 불변, 코드 이동만):
     · E7 _RpBigHeatmap / _RpHeatmapGrid — 시간대×시가총액 대형 히트맵(/edge_ratio cross 재사용)
     · E5 _RpHallOfFame — 명예의 전당 프로(행 펼침 조건식 + 변수칩 + 바로 백테스트)
     · E6 _RpRunCompare — run/gen 후보 나란히 비교 + 행별 바로 백테스트
     · E9 _RpHistory — 과거 run 브라우저 + 조건식 + Bt* 차트 상세(window.BtResultArea 소비)
     · E10 _rpActiveStage / _RpProcessFlowOverlay — 진화 파이프라인 시각 흐름(window.STOM_PIPELINE)

   제약: window 전역 컴포넌트 · 파일별 훅 별칭(rp-utils.jsx 공유) · 한국어 UI.
   window.BtResultArea 는 import 가 아닌 <window.BtResultArea/>·typeof 방어 소비로 그대로 둔다
   (load-order/cross-tab — backtest 패밀리가 먼저 로드되지 않아도 빈 상태로 흡수). */

// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definer. KEEP on ONE physical line.
import { useState_rp, useEffect_rp, useCallback_rp, useMemo_rp, _rpFetchJson, _rpMoney, _rpInt, _rpNum, _rpPct, _rpOpenWorkbench, _rpEdgeColor, _RpStrategyCode } from "./rp-utils.jsx";

function _rpSplitCrossLabel(c) {
  const directTime = c && (c.time || c.time_label || c.time_segment || c._time_segment);
  const directCap = c && (c.market_cap || c.market_cap_label || c.market_cap_segment || c._market_cap_segment || c.cap || c.cap_label);
  if (directTime && directCap) return [String(directTime).trim(), String(directCap).trim()];
  const label = String((c && c.label) || "");
  for (const sep of ["×", " x ", " X ", "|", "/", "·", " - "]) {
    if (label.includes(sep)) {
      const parts = label.split(sep);
      return [parts[0] ? parts[0].trim() : "", parts.slice(1).join(sep).trim()];
    }
  }
  return ["", ""];
}

/* ── E7: 시간대×시가총액 대형 히트맵 — /edge_ratio segments.cross 재사용, 반응형 큰 셀. ── */
function _RpBigHeatmap({ baseUrl, isDemo, runId }) {
  const [data, setData] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);
  const [err, setErr] = useState_rp(null);

  const refresh = useCallback_rp(() => {
    if (isDemo || !baseUrl || !runId) {
      setData(null);
      return;
    }
    setLoading(true);
    _rpFetchJson(
      baseUrl + "/edge_ratio?run_ids=" + encodeURIComponent(runId) + "&fine_time=true",
      8000
    )
      .then((j) => {
        setData(j);
        setErr(null);
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId]);

  useEffect_rp(() => {
    refresh();
  }, [refresh]);

  const grid = useMemo_rp(() => {
    const cross = (data && data.segments && data.segments.cross) || [];
    if (!cross.length) return null;
    const timeLabels = [];
    const capLabels = [];
    const cellMap = {};
    for (const c of cross) {
      const [tl, cl] = _rpSplitCrossLabel(c);
      if (!tl || !cl) continue;
      if (!timeLabels.includes(tl)) timeLabels.push(tl);
      if (cl && !capLabels.includes(cl)) capLabels.push(cl);
      cellMap[tl + "×" + cl] = c;
    }
    if (capLabels.length === 0) return null;
    return { timeLabels, capLabels, cellMap };
  }, [data]);

  const globalEr = data && data.global && typeof data.global.edge_ratio === "number"
    ? data.global.edge_ratio : null;

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">시간대 × 시가총액 탐색 히트맵</span>
        <span
          className="rp-help"
          title="Edge Ratio = 유리한 가격 진행 / 불리한 가격 진행. 1.0 초과면 평균적으로 유리한 구간입니다. 시간대(행) × 시가총액(열) 교차에서 어느 환경이 우위인지 한눈에 봅니다."
        >
          ?
        </span>
        {globalEr != null && (
          <span className="rp-card-sub">전체 edge {_rpNum(globalEr, 3)}</span>
        )}
        <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={refresh} disabled={isDemo || loading}>
          {loading ? "조회중…" : "↻ 새로고침"}
        </button>
      </div>
      <div className="rp-card-bd">
        {isDemo ? (
          <div className="rp-empty">데모 모드 — 라이브 run 연결 시 히트맵이 표시됩니다.</div>
        ) : !runId ? (
          <div className="rp-empty">run을 선택하면 시간대×시총 히트맵이 표시됩니다.</div>
        ) : err ? (
          <div className="rp-empty">조회 실패 — {err}</div>
        ) : !grid ? (
          <div className="rp-empty">
            교차 세그먼트(시간대×시총)가 누적되면 히트맵이 표시됩니다.{loading ? " (로딩중…)" : ""}
          </div>
        ) : (
          <_RpHeatmapGrid grid={grid} />
        )}
      </div>
    </div>
  );
}

/* 반응형 대형 히트맵 그리드 — CSS grid로 컨테이너 폭을 채우는 큰 셀(트렌드 차트 급 크기). */
function _RpHeatmapGrid({ grid }) {
  const { timeLabels, capLabels, cellMap } = grid;
  const cols = `112px repeat(${capLabels.length}, minmax(58px, 96px))`;
  return (
    <div className="rp-heatmap-scroll">
      <div className="rp-heatmap" style={{ gridTemplateColumns: cols }}>
      {/* 헤더 행 */}
      <div className="rp-heatmap-corner mono">시간대 \ 시총</div>
      {capLabels.map((cl) => (
        <div key={"h" + cl} className="rp-heatmap-colhd mono" title={cl}>
          {cl}
        </div>
      ))}
      {/* 본문 */}
      {timeLabels.map((tl) => (
        <React.Fragment key={"r" + tl}>
          <div className="rp-heatmap-rowhd mono" title={tl}>
            {tl}
          </div>
          {capLabels.map((cl) => {
            const cell = cellMap[tl + "×" + cl];
            const er = cell ? cell.edge_ratio : null;
            const bg = _rpEdgeColor(er, 0.85);
            const strong = er != null && Math.abs(er - 1) > 0.15;
            return (
              <div
                key={"c" + tl + cl}
                className="rp-heatmap-cell mono"
                style={{ background: bg, color: strong ? "#fff" : "var(--ink-1)" }}
                title={
                  cell
                    ? `${tl} × ${cl} · edge ${_rpNum(er, 3)} · ${cell.count || 0}건` +
                      (typeof cell.win_rate === "number" ? ` · 승률 ${_rpPct(cell.win_rate * 100)}` : "")
                    : `${tl} × ${cl} · 데이터 없음`
                }
              >
                <strong>{er != null ? _rpNum(er, 2) : "—"}</strong>
                {cell && typeof cell.count === "number" && (
                  <small>{cell.count}건</small>
                )}
              </div>
            );
          })}
        </React.Fragment>
      ))}
      </div>
    </div>
  );
}

/* ── E5: 명예의 전당 프로 — 행 펼침 시 조건식 + 변수칩 + '바로 백테스트'. ── */
function _RpHallOfFame({ baseUrl, isDemo, onOpenWorkbench }) {
  const [hof, setHof] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);
  const [expanded, setExpanded] = useState_rp(null); // "run/gen" 또는 null

  const refresh = useCallback_rp(() => {
    if (isDemo || !baseUrl) {
      setHof(null);
      return;
    }
    setLoading(true);
    _rpFetchJson(baseUrl + "/hall_of_fame", 8000)
      .then((j) => setHof(j))
      .catch(() => setHof(null))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo]);

  useEffect_rp(() => {
    refresh();
  }, [refresh]);

  const ai = (hof && Array.isArray(hof.ai) ? hof.ai : []).filter((r) => r.run_id && r.gen_no != null);

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">🏆 명예의 전당 프로 — 조건식 · 바로 사용</span>
        <span
          className="rp-help"
          title="게이트를 통과한 흑자 전략을 점수 내림차순으로 보여줍니다. 행을 펼치면 매수·매도 조건식과 변수 칩을 확인하고, '바로 백테스트'로 백테스트 탭에 그대로 적재합니다."
        >
          ?
        </span>
        <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={refresh} disabled={isDemo || loading}>
          {loading ? "조회중…" : "↻ 새로고침"}
        </button>
      </div>
      <div className="research-index-note">
        목적: Research Pro 워크벤치용 HoF입니다. 행을 펼쳐 조건식·변수칩을 검토하고 바로 백테스트로
        넘기는 화면이며, 벤치마크 전체 비교는 진화 대시보드의 성과 명예의 전당이 담당합니다.
      </div>
      <div className="rp-card-bd">
        {isDemo ? (
          <div className="rp-empty">데모 모드 — 백엔드 연결 시 명예의 전당이 표시됩니다.</div>
        ) : ai.length === 0 ? (
          <div className="rp-empty">게이트 통과 전략이 누적되면 표시됩니다.{loading ? " (로딩중…)" : ""}</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="rp-table mono">
              <thead>
                <tr>
                  <th>종류</th>
                  <th>전략(run/gen)</th>
                  <th>백테 기간</th>
                  <th>점수</th>
                  <th>총수익</th>
                  <th>수익률</th>
                  <th>연환산</th>
                  <th>MDD</th>
                  <th>거래</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {ai.map((r) => {
                  const key = r.run_id + "/" + r.gen_no;
                  const isOpen = expanded === key;
                  return (
                    <React.Fragment key={key}>
                      <tr className={isOpen ? "rp-row-open" : ""}>
                        <td>
                          <span className={"rp-kind rp-kind-" + (r.kind || "ai")}>
                            {r.kind === "seed" ? "시드" : "AI"}
                          </span>
                        </td>
                        <td title={r.buy_name || ""}>{r.label || key}</td>
                        <td>{r.period || "기간 정보 없음"}</td>
                        <td style={{ color: "var(--teal)" }}>{_rpNum(r.score, 3)}</td>
                        <td className={r.total_return_krw > 0 ? "rp-pos" : "rp-neg"}>
                          {_rpMoney(r.total_return_krw)}
                        </td>
                        <td>{_rpPct(r.total_return_pct)}</td>
                        <td title={r.annual_unreliable ? "창 길이 0.25년 미만 — 연환산 과대 주의" : ""}>
                          {_rpPct(r.annual_return_pct)}
                          {r.annual_unreliable ? " ⚠" : ""}
                        </td>
                        <td style={{ color: "var(--red)" }}>{_rpPct(r.mdd_pct)}</td>
                        <td>{_rpInt(r.trades)}</td>
                        <td style={{ whiteSpace: "nowrap" }}>
                          <button
                            className="btn ghost sm"
                            onClick={() => setExpanded(isOpen ? null : key)}
                            data-tip="조건식·변수 칩 펼치기"
                          >
                            {isOpen ? "▲ 닫기" : "▼ 조건식"}
                          </button>
                          <button
                            className="btn ghost sm"
                            style={{ marginLeft: 4 }}
                            onClick={() => _rpOpenWorkbench(r.run_id, r.gen_no, onOpenWorkbench)}
                            data-tip="백테스트 탭에 이 전략을 적재하고 전환"
                          >
                            바로 백테스트
                          </button>
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="rp-row-detail">
                          <td colSpan={10}>
                            <_RpStrategyCode baseUrl={baseUrl} isDemo={isDemo} runId={r.run_id} genNo={r.gen_no} />
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E6: Run Compare 프로 — run/gen 후보를 담아 나란히 비교 + 행별 바로 백테스트. ── */
function _RpRunCompare({ baseUrl, isDemo, runList, currentRunId, currentGenNo, onOpenWorkbench }) {
  const [items, setItems] = useState_rp([]); // [{run_id,gen_no,result}]
  const [addRun, setAddRun] = useState_rp("");
  const [addGen, setAddGen] = useState_rp(0);

  /* 현재 선택을 비교 후보로 추가 + 결과(/bt/result run+gen) 적재. */
  const add = useCallback_rp(
    (runId, genNo) => {
      if (isDemo || !baseUrl || !runId || genNo == null) return;
      const key = runId + "/" + genNo;
      setItems((prev) => {
        if (prev.some((p) => p.key === key)) return prev;
        return [...prev, { key, run_id: runId, gen_no: genNo, result: null, loading: true }];
      });
      _rpFetchJson(
        baseUrl + "/bt/result?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(genNo),
        9000
      )
        .then((j) => {
          setItems((prev) =>
            prev.map((p) => (p.key === key ? { ...p, result: j, loading: false } : p))
          );
        })
        .catch(() => {
          setItems((prev) => prev.map((p) => (p.key === key ? { ...p, loading: false } : p)));
        });
    },
    [baseUrl, isDemo]
  );

  const remove = useCallback_rp((key) => {
    setItems((prev) => prev.filter((p) => p.key !== key));
  }, []);

  const metricOf = (it) => {
    const m = (it.result && (it.result.metrics || (it.result.analysis && it.result.analysis.summary))) || {};
    return m || {};
  };

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">Run Compare 프로 — 좋은 결과를 바로 사용</span>
        <span
          className="rp-help"
          title="여러 run/세대 결과를 나란히 비교합니다. 각 행에서 '바로 백테스트'로 백테스트 탭에 적재해 정밀 분석합니다."
        >
          ?
        </span>
      </div>
      <div className="rp-card-bd">
        <div className="rp-compare-add">
          <button
            className="btn ghost sm"
            onClick={() => add(currentRunId, currentGenNo)}
            disabled={isDemo || !currentRunId}
            data-tip="상단에서 선택한 run·세대를 비교에 추가"
          >
            + 현재 선택 추가 ({currentRunId || "—"}/g{currentGenNo})
          </button>
          <span className="rp-compare-sep">또는</span>
          <select
            className="mono rp-select"
            aria-label="비교에 추가할 run 선택"
            value={addRun}
            onChange={(e) => setAddRun(e.target.value)}
            disabled={isDemo}
          >
            <option value="">run 선택</option>
            {(runList || []).map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}
                {r.label ? " · " + r.label : ""}
              </option>
            ))}
          </select>
          <label className="rp-compare-genlbl mono">
            gen
            <input
              type="number"
              min={0}
              value={addGen}
              onChange={(e) => setAddGen(Number(e.target.value) || 0)}
              className="rp-num-input mono"
            />
          </label>
          <button
            className="btn ghost sm"
            onClick={() => add(addRun, addGen)}
            disabled={isDemo || !addRun}
          >
            + 추가
          </button>
        </div>

        {items.length === 0 ? (
          <div className="rp-empty">비교할 run/세대를 추가하세요.</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="rp-table mono">
              <thead>
                <tr>
                  <th>run / gen</th>
                  <th>총손익</th>
                  <th>MDD</th>
                  <th>승률</th>
                  <th>거래</th>
                  <th>Payoff</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => {
                  const m = metricOf(it);
                  return (
                    <tr key={it.key}>
                      <td>{it.key}</td>
                      {it.loading ? (
                        <td colSpan={5} className="rp-muted">불러오는 중…</td>
                      ) : (
                        <>
                          <td className={m.total_profit > 0 ? "rp-pos" : "rp-neg"}>
                            {_rpMoney(m.total_profit != null ? m.total_profit : m.profit)}
                          </td>
                          <td style={{ color: "var(--red)" }}>{_rpPct(m.mdd)}</td>
                          <td>{_rpPct(m.win_rate != null ? m.win_rate * 100 : m.win_rate_pct)}</td>
                          <td>{_rpInt(m.trade_count != null ? m.trade_count : m.trades)}</td>
                          <td>{_rpNum(m.payoff_ratio != null ? m.payoff_ratio : m.payoff, 2)}</td>
                        </>
                      )}
                      <td style={{ whiteSpace: "nowrap" }}>
                        <button
                          className="btn ghost sm"
                          onClick={() => _rpOpenWorkbench(it.run_id, it.gen_no, onOpenWorkbench)}
                          data-tip="백테스트 탭에 적재"
                        >
                          바로 백테스트
                        </button>
                        <button className="btn ghost sm" style={{ marginLeft: 4 }} onClick={() => remove(it.key)}>
                          ✕
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E9: 히스토리 — 과거 run 브라우저. 선택 시 세대·조건식 + Bt* 차트 상세 시각화. ── */
function _RpHistory({ baseUrl, isDemo, runList, onOpenWorkbench }) {
  const [selRun, setSelRun] = useState_rp("");
  const [gens, setGens] = useState_rp([]);
  const [selGen, setSelGen] = useState_rp(null);
  const [loading, setLoading] = useState_rp(false);

  /* 선택 run의 세대 목록(/bt/evo_gens, 읽기 전용) — evolution-analysis.jsx와 동일 소스. */
  useEffect_rp(() => {
    if (isDemo || !baseUrl || !selRun) {
      setGens([]);
      setSelGen(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    _rpFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(selRun), 9000)
      .then((j) => {
        if (cancelled) return;
        const items = Array.isArray(j && j.items) ? j.items : [];
        setGens(items);
        /* 기본 선택: gate 통과 세대 우선, 없으면 score 최고. */
        const ranked = items
          .filter((g) => g.gen_no >= 0)
          .slice()
          .sort((a, b) => (b.score || 0) - (a.score || 0));
        const best = ranked.find((g) => g.gate_passed) || ranked[0];
        setSelGen(best ? best.gen_no : null);
      })
      .catch(() => {
        if (!cancelled) {
          setGens([]);
          setSelGen(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, selRun]);

  const topGens = useMemo_rp(
    () =>
      gens
        .filter((g) => g.gen_no >= 0)
        .slice()
        .sort((a, b) => (b.score || 0) - (a.score || 0))
        .slice(0, 12),
    [gens]
  );

  const hasBt = typeof window.BtResultArea === "function";

  return (
    <div className="rp-card">
      <div className="rp-card-hd">
        <span className="rp-card-title">히스토리 — 과거 연구 재열람</span>
        <span
          className="rp-help"
          title="과거 run을 골라 세대별 조건식과 백테스트 탭과 동일한 상세 결과 시각화(자본곡선·분포·히트맵·언더워터 등)를 다시 봅니다."
        >
          ?
        </span>
      </div>
      <div className="rp-card-bd">
        <div className="rp-history-bar">
          <select
            className="mono rp-select"
            aria-label="과거 run 선택"
            value={selRun}
            onChange={(e) => setSelRun(e.target.value)}
            disabled={isDemo}
          >
            <option value="">과거 run 선택…</option>
            {(runList || []).map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}
                {r.label ? " · " + r.label : ""}
                {r.gate_passed_count > 0 ? " ✓" : ""}
              </option>
            ))}
          </select>
          {loading && <span className="rp-muted mono">세대 불러오는 중…</span>}
        </div>

        {!selRun ? (
          <div className="rp-empty">과거 run을 선택하면 세대·조건식·상세 결과가 표시됩니다.</div>
        ) : (
          <div className="rp-history-grid">
            <div className="rp-history-genlist">
              <div className="rp-mini-label">세대 (score 내림차순)</div>
              {topGens.length === 0 ? (
                <div className="rp-empty">세대 없음</div>
              ) : (
                topGens.map((g) => (
                  <button
                    key={g.gen_no}
                    className={"rp-gen-btn mono" + (selGen === g.gen_no ? " active" : "")}
                    onClick={() => setSelGen(g.gen_no)}
                    title={`score ${_rpNum(g.score, 3)} · 손익 ${_rpMoney(g.profit)} · MDD ${_rpPct(g.mdd)}`}
                  >
                    <span>gen_{String(g.gen_no).padStart(2, "0")}</span>
                    <span className={g.profit > 0 ? "rp-pos" : "rp-neg"}>{_rpMoney(g.profit)}</span>
                    {g.gate_passed && <span style={{ color: "var(--teal)" }}>✓</span>}
                  </button>
                ))
              )}
            </div>
            <div className="rp-history-detail">
              {selGen == null ? (
                <div className="rp-empty">세대를 선택하세요.</div>
              ) : (
                <>
                  <div className="rp-history-actions">
                    <span className="rp-mini-label">
                      {selRun} / gen_{String(selGen).padStart(2, "0")} — 조건식 & 상세 결과
                    </span>
                    <button
                      className="btn ghost sm"
                      style={{ marginLeft: "auto" }}
                      onClick={() => _rpOpenWorkbench(selRun, selGen, onOpenWorkbench)}
                      data-tip="백테스트 탭에 적재"
                    >
                      바로 백테스트
                    </button>
                  </div>
                  <_RpStrategyCode baseUrl={baseUrl} isDemo={isDemo} runId={selRun} genNo={selGen} />
                  <div className="rp-history-charts">
                    {hasBt ? (
                      <window.BtResultArea
                        baseUrl={baseUrl}
                        isDemo={isDemo}
                        jobId={null}
                        evoSource={{ run_id: selRun, gen_no: selGen }}
                      />
                    ) : (
                      <div className="rp-empty">상세 차트 컴포넌트(BtResultArea)를 불러올 수 없습니다.</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── E10: 프로세스 플로우 오버레이 — 전체 진화 파이프라인을 시각적 흐름으로. ── */
// P4(2026-06-14): 진화 7단계 정본은 format.ts 의 window.STOM_PIPELINE 로 통합(로컬 사본 삭제).

/* live 상태/ops에서 현재 활성 단계를 휴리스틱으로 추정(불가하면 -1=정적 흐름). */
function _rpActiveStage(liveState, ops) {
  const phase = (liveState && (liveState.phase || (liveState.latest && liveState.latest.phase))) || "";
  const status = (liveState && liveState.status) || "";
  const p = String(phase).toLowerCase();
  if (status === "running") {
    if (p.indexOf("generate") >= 0 || p.indexOf("loop_start") >= 0 || p.indexOf("warm") >= 0 || p.indexOf("ga_init") >= 0)
      return 1; // 후보 생성
    if (p.indexOf("backtest") >= 0 || p.indexOf("evaluate") >= 0) return 3; // 백테 평가
    if (p.indexOf("score") >= 0) return 4; // 게이트
    if (p.indexOf("autopsy") >= 0 || p.indexOf("generation_done") >= 0) return 1; // 다음 후보 생성
  }
  const active = (ops && Array.isArray(ops.active) ? ops.active : []).length;
  if (active > 0 && status !== "complete") return 3; // 돌고 있으면 평가 중으로 가정
  return -1;
}

function _RpProcessFlowOverlay({ onClose, liveState, ops }) {
  const activeStage = _rpActiveStage(liveState, ops);
  const PIPELINE = window.STOM_PIPELINE || [];

  useEffect_rp(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="rp-overlay" onClick={onClose}>
      <div className="rp-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="rp-overlay-hd">
          <span className="rp-card-title">진화 프로세스 — 전체 흐름</span>
          {activeStage >= 0 && (
            <span className="rp-card-sub">현재 단계: {PIPELINE[activeStage].title}</span>
          )}
          <button className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕ 닫기 (Esc)
          </button>
        </div>
        <div className="rp-flow">
          {PIPELINE.map((s, i) => {
            const isActive = i === activeStage;
            return (
              <React.Fragment key={s.key}>
                <div className={"rp-flow-node" + (isActive ? " rp-flow-active" : "")}>
                  <div className="rp-flow-ico">{s.icon}</div>
                  <div className="rp-flow-name">
                    {i + 1}. {s.title}
                    {isActive && <span className="rp-flow-pulse"> ● 진행</span>}
                  </div>
                  <div className="rp-flow-desc">{s.desc}</div>
                  <div className="rp-flow-terms">
                    {s.terms.map(([t, d]) => (
                      <div key={t} className="rp-flow-term">
                        <b>{t}</b> {d}
                      </div>
                    ))}
                  </div>
                </div>
                {i < PIPELINE.length - 1 && <div className="rp-flow-arrow">→</div>}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}
/* 외부(research-lab.jsx 헤더 버튼 등)에서도 오버레이를 쓸 수 있게 전역 노출. */
Object.assign(window, { ResearchProcessFlowOverlay: _RpProcessFlowOverlay });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { _RpBigHeatmap, _RpHeatmapGrid, _RpHallOfFame, _RpRunCompare, _RpHistory, _rpActiveStage, _RpProcessFlowOverlay };
