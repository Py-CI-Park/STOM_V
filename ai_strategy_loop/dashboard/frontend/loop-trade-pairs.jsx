/* 페이지 34 — 거래 짝 뷰어.

   짝지은 검정은 "+0.1974%p [−0.084, +0.479]" 한 줄을 준다. 그 한 줄로는
   **왜** 그런지 알 수 없다. 여기서 그 거래를 직접 연다.

   같은 진입을 1:1 로 맞췄으므로 차이는 순수하게 매도 규칙의 결과다.

   관측 전용이다. 전역 충돌 방지로 LoopTp* 접두를 쓴다. */

const { useState: useState_tp, useEffect: useEffect_tp, useCallback: useCallback_tp } = React;

function loopTpGet(path) {
  return fetch(path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopTpNum(v, d) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toLocaleString(undefined, {
    minimumFractionDigits: d === undefined ? 0 : d,
    maximumFractionDigits: d === undefined ? 0 : d,
  });
}

function loopTpSign(v) {
  if (v === null || v === undefined) return "";
  return Number(v) >= 0 ? "pos" : "neg";
}

function LoopTpTradeTable({ rows, title, hint }) {
  if (!rows || !rows.length) return null;
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">{title}</div>
        <small className="v4s-en">{hint}</small></div>
      <div className="panel-bd"><div className="table-wrap">
        <table className="tbl">
          <thead><tr>
            <th>종목</th><th>매수시각</th>
            <th className="num">합격선</th><th className="num">후보</th><th className="num">차이</th>
            <th className="num">보유(초)</th><th>청산 사유</th>
          </tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="mono">{r["종목명"]}</td>
                <td className="mono" style={{ fontSize: 12 }}>{String(r["매수시간"]).slice(8, 14)}</td>
                <td className={"num mono " + loopTpSign(r["기준_수익률"])}>{loopTpNum(r["기준_수익률"], 2)}%</td>
                <td className={"num mono " + loopTpSign(r["후보_수익률"])}>{loopTpNum(r["후보_수익률"], 2)}%</td>
                <td className={"num mono " + loopTpSign(r["차이"])}><b>{loopTpNum(r["차이"], 2)}%p</b></td>
                <td className="num mono">{loopTpNum(r["기준_보유"], 0)} → {loopTpNum(r["후보_보유"], 0)}</td>
                <td style={{ fontSize: 12 }}>{r["후보_매도조건"] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div></div>
    </section>
  );
}

export function LoopTradePairsPanel() {
  const [payload, setPayload] = useState_tp(null);
  const [candidate, setCandidate] = useState_tp("");
  const [error, setError] = useState_tp("");

  const load = useCallback_tp((pick) => {
    loopTpGet("/loop/trade-pairs?candidate=" + encodeURIComponent(pick || ""))
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : (d && d.reason) || "");
        if (!pick && d && d.candidates && d.candidates.length) {
          setCandidate(d.candidates[0].candidate_id);
        }
      })
      .catch(() => setError("거래 짝 요청 실패"));
  }, []);

  useEffect_tp(() => { load(""); }, [load]);

  const picks = (payload && payload.candidates) || [];
  const reasons = (payload && payload.exit_reasons) || [];

  return (
    <div className="loop-trade-pairs" aria-label="거래 짝 뷰어 (페이지 34)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">거래 짝 뷰어 <small className="v4s-en">페이지 34 · 왜 그런지 직접 본다</small></div>
          <span className="badge" title="엔진 체결 기록만 읽습니다.">official</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">짝지은 검정은 숫자 한 줄을 줍니다. 그 한 줄로는
            <b> 왜</b> 그런지 알 수 없습니다 — 여기서 그 거래를 직접 엽니다.</p>
          <div className="v4s-log-controls" style={{ flexWrap: "wrap", gap: 8 }}>
            <select value={candidate} onChange={(e) => setCandidate(e.target.value)}
                    style={{ maxWidth: 340 }}>
              {picks.map((c) => (
                <option key={c.candidate_id} value={c.candidate_id}>
                  {c.sell_name} · {c.verdict} · 건당 {loopTpNum(c.avg_profit_pct, 2)}%
                </option>
              ))}
            </select>
            <button className="btn sm" type="button" onClick={() => load(candidate)}>열기</button>
          </div>
          {error && <p className="v4s-note">{error}</p>}
          {payload && payload.available && (
            <>
              <p className="v4s-note" style={{ marginTop: 8 }}>
                <b>{payload.baseline_label}</b> → <b>{payload.candidate_label}</b>
              </p>
              <div className="v4s-probe-grid">
                <div className="v4s-probe-card"><b>짝</b>
                  <span className="mono">{loopTpNum(payload.pairs)}건</span>
                  <small className="v4s-en">한쪽만 {loopTpNum(payload.baseline_only)}/{loopTpNum(payload.challenger_only)}</small></div>
                <div className="v4s-probe-card"><b>개선 / 악화</b>
                  <span className="mono"><span className="pos">{loopTpNum(payload.improved)}</span>
                    {" / "}<span className="neg">{loopTpNum(payload.worsened)}</span></span></div>
                <div className="v4s-probe-card"><b>평균 차이</b>
                  <span className={"mono " + loopTpSign(payload.mean_diff_pct)}>
                    {loopTpNum(payload.mean_diff_pct, 4)}%p</span>
                  <small className="v4s-en">중앙값 {loopTpNum(payload.median_diff_pct, 4)}%p</small></div>
                <div className="v4s-probe-card"><b>보유 변화</b>
                  <span className="mono">{loopTpNum(payload.hold_diff_mean, 0)}초</span></div>
                <div className="v4s-probe-card"><b>상위 10건 비중</b>
                  <span className={"mono " + ((payload.top10_share || 0) > 0.5 ? "neg" : "")}>
                    {payload.top10_share === null || payload.top10_share === undefined
                      ? "—" : loopTpNum(payload.top10_share * 100, 1) + "%"}</span>
                  <small className="v4s-en">1에 가까우면 꼬리가 지배</small></div>
              </div>
            </>
          )}
          {payload && (payload.reading_rules || []).map((r, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {r}</p>
          ))}
        </div>
      </div>

      {reasons.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">청산 사유별 — 어디서 이기고 어디서 지는가</div>
            <small className="v4s-en">합계 차이 오름차순 (가장 손해 보는 사유가 위)</small></div>
          <div className="panel-bd"><div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>후보 청산 사유</th><th className="num">건수</th>
                <th className="num">개선</th><th className="num">악화</th>
                <th className="num">평균 차이</th><th className="num">합계 차이</th></tr></thead>
              <tbody>
                {reasons.map((r, i) => (
                  <tr key={i}>
                    <td>{r["매도조건"] || "—"}</td>
                    <td className="num mono">{loopTpNum(r["건수"])}</td>
                    <td className="num mono pos">{loopTpNum(r["개선"])}</td>
                    <td className="num mono neg">{loopTpNum(r["악화"])}</td>
                    <td className={"num mono " + loopTpSign(r["평균차이"])}>{loopTpNum(r["평균차이"], 3)}%p</td>
                    <td className={"num mono " + loopTpSign(r["합계차이"])}><b>{loopTpNum(r["합계차이"], 2)}%p</b></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div></div>
        </section>
      )}

      <LoopTpTradeTable rows={payload && payload.worst} title="가장 나빠진 거래"
                        hint="이 규칙이 잘라 버린 것 — 되살아났을 거래가 여기 있다"/>
      <LoopTpTradeTable rows={payload && payload.best} title="가장 좋아진 거래"
                        hint="이 규칙이 구해 낸 것"/>
    </div>
  );
}
