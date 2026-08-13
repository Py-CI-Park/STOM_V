/* 페이지 30 — 조건식 성과 원장.

   지금까지 만든 후보 전부를 한 표에 놓는다. 원장이 없으면 성과가 누적되지 않고,
   같은 실험을 두 번 하게 된다.

   판독 규율: 판정은 절대 기준이 아니라 **챔피언 대비**다. 그리고 총수익금만 보면
   자본을 더 쓴 후보가 항상 이기므로 총수익률을 나란히 놓는다.

   관측 전용이다. 전역 충돌 방지로 LoopSl* 접두를 쓴다. */

const { useState: useState_sl, useEffect: useEffect_sl, useCallback: useCallback_sl } = React;

function loopSlGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopSlNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

function loopSlSign(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
  return Number(value) >= 0 ? "pos" : "neg";
}

const LOOP_SL_TONE = { BASELINE: "", PASS: "", PROMISING: "warn", MIXED: "warn", REJECT: "warn" };

/* 델타 칸 — 챔피언 대비 얼마나 나은가. 방향이 반대인 지표(MDD·필요자금)는 부호를 뒤집어 읽는다. */
function LoopSlDelta({ value, digits, lowerBetter }) {
  if (value === null || value === undefined) return <span className="mono">—</span>;
  const good = lowerBetter ? Number(value) < 0 : Number(value) > 0;
  return <span className={"mono " + (good ? "pos" : "neg")}>
    {Number(value) >= 0 ? "+" : ""}{loopSlNum(value, digits)}</span>;
}

function LoopSlSummary({ payload }) {
  const v = (payload && payload.verdicts) || {};
  const labels = (payload && payload.verdict_labels) || {};
  return (
    <div className="v4s-probe-grid">
      <div className="v4s-probe-card"><b>후보</b>
        <span className="mono">{loopSlNum(payload && payload.candidates)}종</span>
        <small className="v4s-en">누적 기록 {loopSlNum(payload && payload.records)}행</small></div>
      <div className="v4s-probe-card"><b>승격(PASS)</b>
        <span className={"mono " + ((payload && payload.promoted) ? "pos" : "neg")}>
          {loopSlNum(payload && payload.promoted)}종</span>
        <small className="v4s-en">챔피언 이상 + 통계 확정</small></div>
      {["PROMISING", "MIXED", "REJECT"].map((key) => (
        <div className="v4s-probe-card" key={key}><b>{labels[key] || key}</b>
          <span className="mono">{loopSlNum(v[key])}종</span></div>
      ))}
    </div>
  );
}

export function LoopStrategyLedgerPanel({ baseUrl, onSelectContext, reviewContext }) {
  const [payload, setPayload] = useState_sl(null);
  const [error, setError] = useState_sl("");
  const [history, setHistory] = useState_sl(false);

  const load = useCallback_sl(() => {
    loopSlGet(baseUrl, "/loop/strategy-ledger?history=" + (history ? "true" : "false"))
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : "원장이 비어 있습니다 — 엔진 실측 후 run_ledger_sync 를 돌리면 채워집니다.");
      })
      .catch(() => setError("원장 요청 실패"));
  }, [baseUrl, history]);

  useEffect_sl(() => { load(); }, [load]);

  const rows = (payload && payload.rows) || [];
  return (
    <div className="loop-strategy-ledger" aria-label="조건식 성과 원장 (페이지 30)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">조건식 성과 원장 <small className="v4s-en">페이지 30 · 엔진 실측 누적</small></div>
          <span className="badge" title="엔진 체결 기록만 들어옵니다. 지도 추정치는 참고 열입니다.">official</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">지금까지 만든 후보를 <b>한 표</b>에 놓습니다. 원장이 없으면 성과가 누적되지 않고
            같은 실험을 두 번 하게 됩니다.</p>
          <LoopSlSummary payload={payload}/>
          <div className="v4s-log-controls">
            <label style={{ fontSize: 12 }}>
              <input type="checkbox" checked={history} onChange={(e) => setHistory(e.target.checked)}/>
              &nbsp;전체 이력 보기 (재측정 기록 포함)
            </label>
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
          </div>
          {error && <p className="v4s-note">{error}</p>}
          {payload && (payload.reading_rules || []).map((rule, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {rule}</p>
          ))}
        </div>
      </div>

      {rows.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">후보별 성과</div>
            <small className="v4s-en">합격선(챔피언)이 맨 위 · 그 아래는 건당 내림차순</small></div>
          <div className="panel-bd">
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr>
                  <th>후보</th><th>판정</th>
                  <th className="num">거래</th><th className="num">건당</th>
                  <th className="num">총수익금</th><th className="num">필요자금</th>
                  <th className="num">총수익률</th><th className="num">CAGR</th>
                  <th className="num">MDD</th><th className="num">Calmar</th>
                  <th className="num">국면</th><th className="num">짝지은 차이</th>
                </tr></thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.row_id || index}
                        className={row.is_baseline ? "row-accent" : ""}
                        aria-selected={reviewContext && reviewContext.candidate_id === row.candidate_id}
                        onClick={() => onSelectContext && onSelectContext({
                          candidate_id: row.candidate_id || row.sell_name || null,
                          baseline_id: row.baseline_id || null,
                          artifact_id: row.artifact_id || row.source || null,
                          study_id: row.study_id || null,
                          lane: row.lane || null,
                          split: row.split || null,
                          source_hash: row.source_hash || null,
                        })}
                        style={{ cursor: onSelectContext ? "pointer" : undefined }}>
                      <td className="mono">{row.sell_name || row.candidate_id}
                        {row.is_baseline && <span className="badge" style={{ marginLeft: 4 }}>합격선</span>}
                        <br/><small className="v4s-en">{row.source} · {row.period_start}~{row.period_end}</small></td>
                      <td><span className={"badge " + (LOOP_SL_TONE[row.verdict] || "")}
                                title={row.verdict_reason || ""}>{row.verdict_label}</span></td>
                      <td className="num mono">{loopSlNum(row.trades)}</td>
                      <td className={"num mono " + loopSlSign(row.avg_profit_pct)}>
                        {loopSlNum(row.avg_profit_pct, 2)}%
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_avg_profit_pct} digits={2}/></>}</td>
                      <td className="num mono">{loopSlNum(row.total_profit_krw)}원</td>
                      <td className="num mono">{loopSlNum(row.seed_capital)}원
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_seed_capital} lowerBetter/></>}</td>
                      <td className={"num mono " + loopSlSign(row.total_profit_pct)}>
                        {loopSlNum(row.total_profit_pct, 2)}%
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_total_profit_pct} digits={2}/></>}</td>
                      <td className="num mono">{loopSlNum(row.cagr, 2)}
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_cagr} digits={2}/></>}</td>
                      <td className="num mono">{loopSlNum(row.mdd_pct, 2)}
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_mdd_pct} digits={2} lowerBetter/></>}</td>
                      <td className="num mono">{loopSlNum(row.calmar, 2)}
                        {!row.is_baseline && <><br/><LoopSlDelta value={row.delta_calmar} digits={2}/></>}</td>
                      <td className="num mono">{row.regime_positive === null || row.regime_positive === undefined
                        ? "—" : `${row.regime_positive}/4`}
                        {!row.is_baseline && row.regime_baseline != null &&
                          <><br/><small className="v4s-en">기준 {row.regime_baseline}/4</small></>}</td>
                      <td className="num mono">
                        {row.paired_mean_diff_pct === null || row.paired_mean_diff_pct === undefined ? "—" : <>
                          <span className={loopSlSign(row.paired_mean_diff_pct)}>
                            {loopSlNum(row.paired_mean_diff_pct, 4)}%p</span>
                          {!row.paired_significant && <><br/><span className="badge warn">미확정</span></>}
                        </>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
