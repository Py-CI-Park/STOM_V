/* Generations table - newest at top, current highlighted, expandable gist */
const { useState: useState_t, useMemo: useMemo_t } = React;

// fmtDaily: 일평균거래횟수를 소수 2자리로 표시(없으면 0.00). fmt 헬퍼가 없을 때 폴백.
function fmtDaily(v) {
  const n = typeof v === "number" ? v : 0;
  return n.toFixed(2);
}

function GenerationsTable({ state, mddCap = 15, minDailyTrades = 0.5, onViewCode }) {
  const [expanded, setExpanded] = useState_t(new Set());

  const rows = useMemo_t(() => {
    // newest first
    return [...(state.generations || [])].reverse();
  }, [state.generations]);

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
        </div>
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)" }}>
          {rows.length}개 세대 누적
        </span>
      </div>
      <div style={{ maxHeight: 520, overflowY: "auto" }}>
        <table className="gens">
          <thead>
            <tr>
              <th style={{ width: 68 }}>세대</th>
              <th style={{ width: 70 }}>상태</th>
              <th style={{ width: 82 }}>등급점수</th>
              <th style={{ width: 64 }}>게이트</th>
              <th style={{ width: 70 }}>거래수</th>
              <th style={{ width: 84 }}>일평균거래</th>
              <th style={{ width: 76 }}>MDD</th>
              <th style={{ width: 80 }}>수익률</th>
              <th style={{ width: 120 }}>수익금</th>
              <th>사유 / 전략 요지</th>
              <th style={{ width: 60, textAlign: "center" }}>코드</th>
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
                <td className="gist-cell" style={{ color: "var(--amber)" }}>
                  {state.latest?.phase || "—"} · {state.latest?.last_checkpoint || ""}
                </td>
                <td></td>
              </tr>
            )}
            {rows.length === 0 && !running && (
              <tr>
                <td colSpan="11" style={{ textAlign: "center", padding: 32, color: "var(--ink-3)" }}>
                  아직 실행된 세대가 없습니다
                </td>
              </tr>
            )}
            {rows.map(g => {
              const mddBad = typeof g.mdd === "number" && g.mdd > mddCap;
              // 일평균거래횟수가 빈도 하한 미달이면 경고색(빈도 게이트 탈락 신호).
              const dailyBad = typeof g.daily_avg_trades === "number"
                && g.daily_avg_trades < minDailyTrades;
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
                  <td className={`mono ${mddBad ? "num-neg" : ""}`}>{fmtPct(g.mdd)}</td>
                  <td className={`mono ${g.total_profit_pct > 0 ? "num-pos" : g.total_profit_pct < 0 ? "num-neg" : "num-muted"}`}>
                    {fmtPct(g.total_profit_pct)}
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
