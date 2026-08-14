/* 페이지 12 강화 — 전이율 누적 원장 (QSP10 계획서 §3 미구현분 회수).

   지도는 탐색용 추정, 엔진이 심판이다. 그 비율(전이율)을 누적해야 "지도가
   +0.35%라 할 때 실제로는 얼마인가"를 사후가 아니라 사전에 읽을 수 있다.

   판독 규율: 전이율은 **부호가 같을 때만** 감쇠 계수다. 부호가 뒤집힌 건은
   계수가 아니라 구조 불일치 경고다(QSP12 진입 단위 결함이 −1.18 이었다).
   전역 충돌 방지로 BtTl* 접두를 쓴다. */

const { useState: useState_tl, useEffect: useEffect_tl, useCallback: useCallback_tl } = React;

function btTlGet(path) {
  return fetch(path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function btTlNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

const BT_TL_AXIS_LABEL = {
  exit_only: "진입 고정 · 청산만 변경",
  entry_and_exit: "진입까지 함께 변경",
};

/* 계수 환산기 — 지도 수치를 넣으면 엔진 예상치를 돌려준다.

   축을 고르게 하는 이유(2026-08-06 실측): 진입까지 바꾼 후보는 전이율 0.1~0.34
   (지도가 과대평가), 진입 고정·청산만 바꾼 후보는 2.2~4.2(지도가 과소평가).
   방향이 반대인 두 무리를 하나의 계수로 뭉개면 어느 쪽에도 맞지 않는다. */
function BtTlEstimator({ coefficient, status, byAxis, mixed }) {
  const [input, setInput] = useState_tl("0.35");
  const [axis, setAxis] = useState_tl("");
  const bucket = axis && byAxis ? byAxis[axis] : null;
  const active = bucket ? bucket.coefficient : coefficient;
  const activeStatus = bucket ? bucket.status : status;
  const value = Number(input);
  const estimate = active !== null && active !== undefined && !Number.isNaN(value)
    ? value * active : null;
  return (
    <>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>지도 추정 건당(%)</b>
          <input className="mono" value={input} inputMode="decimal"
                 onChange={(e) => setInput(e.target.value.replace(/[^0-9.\-]/g, ""))}
                 style={{ width: 90 }} aria-label="지도 추정 건당 수익률"/></div>
        <div className="v4s-probe-card"><b>비교 축</b>
          <select value={axis} onChange={(e) => setAxis(e.target.value)}
                  aria-label="전이율 비교 축">
            <option value="">전체(섞임)</option>
            {Object.keys(byAxis || {}).map((key) => (
              <option key={key} value={key}>{BT_TL_AXIS_LABEL[key] || key}</option>
            ))}
          </select></div>
        <div className="v4s-probe-card"><b>보수 계수</b>
          <span className="mono">{active === null || active === undefined ? "—" : btTlNum(active, 3)}</span>
          {bucket && <small className="v4s-en">표본 {btTlNum(bucket.aligned_count)}건</small>}</div>
        <div className="v4s-probe-card"><b>엔진 예상 건당(%)</b>
          <span className={"mono " + (estimate > 0 ? "pos" : "neg")}>
            {estimate === null ? "—" : btTlNum(estimate, 4)}</span></div>
        <div className="v4s-probe-card"><b>계수 상태</b>
          <span className="mono">{activeStatus === "ready" ? "사용 가능" : "축적 중"}</span></div>
      </div>
      {mixed && !axis && <p className="tp-error" role="alert">
        ⚠ 지금 계수는 <b>방향이 반대인 두 무리를 섞은</b> 중앙값입니다 —
        진입까지 바꾼 후보는 지도를 <b>깎아야</b> 하고, 진입 고정·청산만 바꾼 후보는
        지도가 오히려 <b>과소평가</b>합니다. 위에서 축을 골라 읽으세요.</p>}
    </>
  );
}

export function BtTransferLedgerPanel() {
  const [payload, setPayload] = useState_tl(null);
  const [error, setError] = useState_tl("");

  const load = useCallback_tl(() => {
    btTlGet("/bt/transfer-ledger")
      .then((d) => { setPayload(d); setError(d && d.available ? "" : "전이율 기록이 아직 없습니다 — P5 엔진 검증을 한 번 돌리면 채워집니다."); })
      .catch(() => setError("원장 요청 실패"));
  }, []);

  useEffect_tl(() => { load(); }, [load]);

  const records = (payload && payload.records) || [];
  const flips = (payload && payload.sign_flip_count) || 0;
  return (
    <div className="bt-transfer-ledger" aria-label="전이율 누적 원장 (페이지 12 강화)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">전이율 누적 원장 <small className="v4s-en">페이지 12 강화 · 지도 → 엔진</small></div>
          <span className="badge warn" title="진단용입니다. 공식 판정은 엔진 실측에서만 합니다.">diagnostic</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">지도는 <b>탐색용 추정</b>, 엔진이 <b>심판</b>입니다.
            둘의 비율을 쌓아 두면 지도 수치를 그대로 믿는 대신 <b>깎아서</b> 읽을 수 있습니다.</p>
          <BtTlEstimator coefficient={payload && payload.conservative_coefficient}
                         status={payload && payload.status}
                         byAxis={payload && payload.by_axis}
                         mixed={payload && payload.axis_mixed}/>
          {payload && <p className="v4s-note">{payload.note}</p>}
          {payload && payload.axis_note && <p className="v4s-note">{payload.axis_note}</p>}
          <div className="v4s-log-controls">
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
            <span className="mono" style={{ fontSize: 11.5 }}>
              기록 {btTlNum(payload && payload.record_count)}건 ·
              부호 일치 {btTlNum(payload && payload.aligned_count)}건 ·
              최소 {btTlNum(payload && payload.minimum_for_coefficient)}건 필요</span>
          </div>
          {flips > 0 && <p className="tp-error" role="alert">
            ⚠ 부호 반전 {flips}건 — 감쇠가 아니라 <b>구조 불일치</b> 신호입니다(지도와 엔진이 서로 다른 것을 세고 있을 수 있습니다).</p>}
          {error && <p className="v4s-note">{error}</p>}
        </div>
      </div>

      {records.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">후보별 기록</div>
            <small className="v4s-en">지도 추정 ↔ 엔진 실측</small></div>
          <div className="panel-bd">
            <div className="table-wrap">
              <table className="tbl">
                <thead>
                  <tr>
                    <th>후보</th><th>규칙</th><th>비교 축</th>
                    <th className="num">지도 건당</th><th className="num">엔진 건당</th>
                    <th className="num">전이율</th>
                    <th className="num">거래수 지도/엔진</th>
                    <th className="num">CAGR</th><th className="num">MDD</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((row, index) => (
                    <tr key={`${row.job_id || index}`} className={row.sign_flip ? "row-warn" : ""}>
                      <td><b>{row.name || "—"}</b><br/><small className="mono">{row.lane}</small></td>
                      <td className="mono">{row.rule || "—"}</td>
                      <td><span className="badge" title="무엇을 바꿔 가며 잰 전이율인가">
                        {BT_TL_AXIS_LABEL[row.axis] || row.axis || "—"}</span></td>
                      <td className={"num mono " + (row.map_expectancy_pct >= 0 ? "pos" : "neg")}>{btTlNum(row.map_expectancy_pct, 4)}%</td>
                      <td className={"num mono " + (row.engine_avg_profit_pct >= 0 ? "pos" : "neg")}>{btTlNum(row.engine_avg_profit_pct, 4)}%</td>
                      <td className="num mono">
                        {btTlNum(row.transfer_ratio, 3)}
                        {row.sign_flip && <span className="badge warn" title="부호 반전 — 계수로 쓰지 않는다">반전</span>}</td>
                      <td className="num mono">{btTlNum(row.map_trades)} / {btTlNum(row.engine_trades)}</td>
                      <td className="num mono">{btTlNum(row.engine_cagr, 2)}%</td>
                      <td className="num mono">{btTlNum(row.engine_mdd_pct, 2)}%</td>
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
