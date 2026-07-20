/* Generations table - newest at top, current highlighted, expandable gist */
const { useState: useState_t, useMemo: useMemo_t } = React;

// fmtDaily: 일평균거래횟수를 소수 2자리로 표시(없으면 0.00). fmt 헬퍼가 없을 때 폴백.
function fmtDaily(v) {
  const n = typeof v === "number" ? v : 0;
  return n.toFixed(2);
}

function GenerationsTable({ state, mddCap = 15, minDailyTrades = 0.5, onViewCode, onSelectDetail }) {
  const [expanded, setExpanded] = useState_t(new Set());
  const [sortKey, setSortKey] = useState_t("gen_desc");

  const rows = useMemo_t(() => {
    const base = [...(state.generations || [])];
    if (sortKey === "profit_desc") {
      return base.sort((a, b) => (b.profit || 0) - (a.profit || 0));
    }
    // gen_desc default: newest first
    return base.reverse();
  }, [state.generations, sortKey]);

  const running = state.status === "running" || state.status === "stopping";
  const currentDisplayGen = running ? state.current_gen + 1 : state.current_gen;

  const toggleExpand = (g) => {
    setExpanded(prev => {
      const n = new Set(prev);
      if (n.has(g)) n.delete(g); else n.add(g);
      return n;
    });
  };

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot"></span>세대 이력 — Generations
          {/* v5.6.1 — 연구 타이틀(어느 run 의 이력인지) 명시 */}
          {state.run_id && (
            <span className="mono tag-slim" style={{ marginLeft: 8, fontSize: 10.5, color: "var(--violet)" }}
                  title="이 세대 이력이 속한 연구 run">{state.run_id}</span>
          )}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
            {rows.length}개 세대 누적
          </span>
          <button className="btn ghost sm" onClick={() => setSortKey("profit_desc")} data-tip="total_profit sort">
            Sort: Total Profit
          </button>
          <button className="btn ghost sm" onClick={() => setSortKey("gen_desc")}>
            Sort: Gen
          </button>
        </div>
      </div>
      <div style={{ maxHeight: 520, overflowY: "auto" }}>
        <table className="gens">
          <thead>
            <tr>
              <th style={{ width: 68 }}>세대</th>
              <th style={{ width: 70 }}>상태</th>
              <th style={{ width: 82 }}>등급점수</th>
              <th style={{ width: 64 }}>Calmar</th>
              <th style={{ width: 56 }}>R²</th>
              <th style={{ width: 64 }}>게이트</th>
              <th style={{ width: 70 }}>거래수</th>
              <th style={{ width: 84 }}>일평균거래</th>
              <th style={{ width: 72 }}>동시보유</th>
              <th style={{ width: 72 }}>Payoff</th>
              <th style={{ width: 80 }}>Give-back%</th>
              <th style={{ width: 76 }}>MDD</th>
              <th style={{ width: 80 }}>수익률</th>
              <th style={{ width: 120 }}>수익금</th>
              <th>사유 / 전략 요지</th>
              <th style={{ width: 60, textAlign: "center" }}>코드</th>
              <th style={{ width: 76, textAlign: "center" }}>백테상세</th>
            </tr>
          </thead>
          <tbody>
            {running && (
              <tr className="current">
                <td className="mono">gen_{String(currentDisplayGen).padStart(2, "0")}</td>
                <td><span className="pill" style={{ color: "var(--amber)", borderColor: "rgba(240,179,90,0.32)", background: "rgba(240,179,90,0.06)" }}>
                  <span className="dot pulse-dot" style={{ background: "var(--amber)", width: 5, height: 5, borderRadius: "50%" }}></span>
                  진행중
                </span></td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="num-muted">—</td>
                <td className="gist-cell" style={{ color: "var(--amber)" }}>
                  {state.latest?.phase || "—"} · {state.latest?.last_checkpoint || ""}
                </td>
                <td></td>
                <td></td>
              </tr>
            )}
            {rows.length === 0 && !running && (
              <tr>
                <td colSpan="17" style={{ textAlign: "center", padding: 32, color: "var(--ink-3)" }}>
                  아직 실행된 세대가 없습니다
                </td>
              </tr>
            )}
            {rows.map(g => {
              const mddBad = typeof g.mdd === "number" && g.mdd > mddCap;
              // 일평균거래횟수가 빈도 하한 미달이면 경고색(빈도 게이트 탈락 신호).
              const dailyBad = typeof g.daily_avg_trades === "number"
                && g.daily_avg_trades < minDailyTrades;
              const sparseHoldSuspicious = typeof g.max_hold_count === "number"
                && g.max_hold_count <= 1
                && (g.trade_count || 0) >= 50;
              const isExp = expanded.has(g.gen_no);
              return (
                <tr key={g.gen_no}>
                  <td className="mono">gen_{String(g.gen_no).padStart(2, "0")}</td>
                  <td>
                    {g.status === "error" ? (
                      <span className="pill error">오류</span>
                    ) : (
                      <span className="pill success">success</span>
                    )}
                  </td>
                  <td className={`mono ${g.graded_score >= 1 ? "num-pos" : ""}`}>
                    {fmtScore(g.graded_score)}
                  </td>
                  <td className={`mono ${typeof g.calmar === "number" && g.calmar > 0 ? "num-pos" : "num-muted"}`}
                      title="Calmar 비율 (CAGR/MDD) — 위험조정 수익. 높을수록 우수">
                    {typeof g.calmar === "number" ? g.calmar.toFixed(2) : "—"}
                  </td>
                  <td className={`mono ${typeof g.uptrend_r2 === "number" && g.uptrend_r2 > 0 ? "" : "num-muted"}`}
                      title="우상향 R² (누적수익 곡선의 직선 적합도, 0~1) — 1에 가까울수록 꾸준한 우상향">
                    {typeof g.uptrend_r2 === "number" ? g.uptrend_r2.toFixed(2) : "—"}
                  </td>
                  <td>
                    {g.gate_passed
                      ? <span className="pill gate-pass">✓ 통과</span>
                      : <span className="pill gate-fail">✗</span>}
                  </td>
                  <td className="mono">{g.trade_count ?? 0}</td>
                  <td className={`mono ${dailyBad ? "num-neg" : g.daily_avg_trades >= minDailyTrades ? "num-pos" : ""}`}
                      title="일평균거래횟수 (거래수/거래일수) — 빈도 게이트 주 기준">
                    {fmtDaily(g.daily_avg_trades)}
                  </td>
                  <td className={`mono ${sparseHoldSuspicious ? "num-neg" : typeof g.max_hold_count === "number" && g.max_hold_count > 0 ? "" : "num-muted"}`}
                      title={sparseHoldSuspicious
                        ? "Sparse hold warning: max_hold_count <= 1 with enough trades; compare Backtest Detail CSV peak_holdings. human corridor 6-12"
                        : "최대 동시보유 종목 수 — 다종목 분산 진입의 1차 근사(클수록 분산)"}>
                    {typeof g.max_hold_count === "number"
                      ? `${g.max_hold_count.toFixed(0)}${sparseHoldSuspicious ? " !" : ""}`
                      : "—"}
                  </td>
                  <td className={`mono ${typeof g.payoff_ratio === "number" && g.payoff_ratio > 0 ? "num-pos" : "num-muted"}`}
                      title="손익비 (평균이익/abs(평균손실)) — 1 초과일수록 우수">
                    {typeof g.payoff_ratio === "number" ? g.payoff_ratio.toFixed(2) : "—"}
                  </td>
                  <td className={`mono ${typeof g.give_back_rate === "number" && g.give_back_rate > 0 ? "num-neg" : "num-muted"}`}
                      title="기회 반납률 — MFE 도달 후 손실 전환 비율. 낮을수록 우수">
                    {typeof g.give_back_rate === "number" ? (g.give_back_rate * 100).toFixed(1) + "%" : "—"}
                  </td>
                  <td className={`mono ${typeof g.mdd !== "number" ? "num-muted" : "num-neg"}`}
                      style={mddBad ? { fontWeight: 700 } : undefined}
                      title={mddBad ? `MDD 상한(${mddCap}%) 초과` : "최대 낙폭"}>{fmtPct(g.mdd)}</td>
                  <td className={`mono ${typeof g.total_profit_pct !== "number" ? "num-muted" : g.total_profit_pct > 0 ? "num-pos" : g.total_profit_pct < 0 ? "num-neg" : "num-muted"}`}>
                    {typeof g.total_profit_pct === "number" ? fmtPct(g.total_profit_pct) : "—"}
                  </td>
                  <td className={`mono ${g.profit > 0 ? "num-pos" : g.profit < 0 ? "num-neg" : "num-muted"}`}>
                    {fmtMoney(g.profit)}
                  </td>
                  <td>
                    <div
                      className={`gist-cell ${isExp ? "expanded" : "truncated"}`}
                      onClick={() => toggleExpand(g.gen_no)}
                      style={{ cursor: "pointer" }}
                      title={isExp ? "축소" : "확장"}
                    >
                      {g.gate_reason && g.gate_reason !== "조건 충족" && (
                        <span style={{ color: "var(--ink-2)" }}>[{g.gate_reason}] </span>
                      )}
                      <span style={{ color: "var(--ink-0)" }}>{g.strategy_gist || "—"}</span>
                    </div>
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button className="btn ghost sm"
                            onClick={() => onViewCode && onViewCode(g)}
                            data-tip="매수/매도 조건식 코드 보기"
                            style={{ padding: "3px 8px", fontSize: 11 }}>
                      &lt;/&gt;
                    </button>
                  </td>
                  {/* #65 P1 — 행의 백테상세 액션: BacktestDetailChart의 선택 세대를 이 gen으로
                      동기화(드롭다운 재선택 제거). App의 selectedDetailGen을 올린다. */}
                  <td style={{ textAlign: "center" }}>
                    <button className="btn ghost sm"
                            onClick={() => onSelectDetail && onSelectDetail(g.gen_no)}
                            data-tip="이 세대를 백테 상세 차트에 표시"
                            style={{ padding: "3px 8px", fontSize: 11 }}>
                      📊
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

Object.assign(window, { GenerationsTable });

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { GenerationsTable };
