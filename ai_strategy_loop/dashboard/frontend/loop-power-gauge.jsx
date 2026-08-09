/* 페이지 31 — 표본·검정력 계기판.

   페이지 30(원장)이 "이 후보가 나은가"를 답한다면 여기는 **"그 판정을 믿을 만한가,
   못 믿겠으면 얼마나 더 재야 하나"**를 답한다.

   판독 규율: MDE(최소 검출 가능 효과)는 지금 표본의 **눈금 폭**이다. 관측 차이가
   눈금보다 작으면 결과가 0이 아니어도 아직 잰 것이 아니다.

   관측 전용이다. 전역 충돌 방지로 LoopPg* 접두를 쓴다. */

const { useState: useState_pg, useEffect: useEffect_pg, useCallback: useCallback_pg } = React;

function loopPgGet(path) {
  return fetch(path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopPgNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

/* 확정만 중립(배지 없음), 나머지는 전부 경고색 — "아직 아니다"가 눈에 띄어야 한다. */
const LOOP_PG_TONE = { "확정": "", "표본 부족": "warn", "표본 절망": "warn", "역방향": "warn", "판정 불가": "warn" };

/* 검정력 막대 — 숫자만 있으면 80%가 멀었는지 가까운지 한눈에 안 들어온다. */
function LoopPgPowerBar({ value, target }) {
  if (value === null || value === undefined) return <span className="mono">—</span>;
  const pct = Math.max(0, Math.min(1, Number(value)));
  const reached = pct >= (target || 0.8);
  return (
    <div title={`검정력 ${(pct * 100).toFixed(1)}% / 목표 ${((target || 0.8) * 100).toFixed(0)}%`}>
      <span className={"mono " + (reached ? "pos" : "neg")}>{(pct * 100).toFixed(1)}%</span>
      <div style={{ height: 4, background: "rgba(127,127,127,.25)", borderRadius: 2, marginTop: 2 }}>
        <div style={{
          width: (pct * 100).toFixed(1) + "%", height: "100%", borderRadius: 2,
          background: reached ? "var(--pos, #2e9e5b)" : "var(--warn, #c98a1b)",
        }}/>
      </div>
    </div>
  );
}

function LoopPgSummary({ payload }) {
  const rate = (payload && payload.trade_rate) || {};
  return (
    <div className="v4s-probe-grid">
      <div className="v4s-probe-card"><b>확정</b>
        <span className={"mono " + ((payload && payload.confirmed) ? "pos" : "neg")}>
          {loopPgNum(payload && payload.confirmed)}종</span>
        <small className="v4s-en">신뢰구간 하한 &gt; 0</small></div>
      <div className="v4s-probe-card"><b>표본 부족</b>
        <span className="mono">{loopPgNum(payload && payload.reachable)}종</span>
        <small className="v4s-en">더 모으면 확정 가능</small></div>
      <div className="v4s-probe-card"><b>표본 절망</b>
        <span className="mono">{loopPgNum(payload && payload.hopeless)}종</span>
        <small className="v4s-en">필요 표본 10배 초과</small></div>
      <div className="v4s-probe-card"><b>역방향</b>
        <span className="mono">{loopPgNum(payload && payload.wrong_way)}종</span>
        <small className="v4s-en">차이 ≤ 0</small></div>
      <div className="v4s-probe-card"><b>라운드 완주까지</b>
        <span className="mono">{payload && payload.days_to_finish_round
          ? loopPgNum(payload.days_to_finish_round, 0) + "거래일" : "—"}</span>
        <small className="v4s-en">가장 오래 걸리는 후보 기준</small></div>
      <div className="v4s-probe-card"><b>실측 거래 빈도</b>
        <span className="mono">{rate.available ? loopPgNum(rate.trades_per_day, 2) + "건/일" : "—"}</span>
        <small className="v4s-en">{rate.available
          ? `${loopPgNum(rate.trades)}건 / DB ${loopPgNum(rate.db_trading_days)}거래일` : (rate.reason || "")}</small></div>
    </div>
  );
}

export function LoopPowerGaugePanel() {
  const [payload, setPayload] = useState_pg(null);
  const [error, setError] = useState_pg("");

  const load = useCallback_pg(() => {
    loopPgGet("/loop/power-gauge")
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : "잴 수 있는 후보가 없습니다 — 짝지은 비교가 있는 기록이 필요합니다.");
      })
      .catch(() => setError("계기판 요청 실패"));
  }, []);

  useEffect_pg(() => { load(); }, [load]);

  const gauges = (payload && payload.gauges) || [];
  return (
    <div className="loop-power-gauge" aria-label="표본·검정력 계기판 (페이지 31)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">표본·검정력 계기판 <small className="v4s-en">페이지 31 · 지금 표본으로 무엇을 확정할 수 있나</small></div>
          <span className="badge" title="원장의 짝지은 신뢰구간에서 역산합니다. 값을 지어내지 않습니다.">official</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">체중계 눈금이 1kg 단위면 500g 감량은 <b>잰 게 아니라 안 보이는 것</b>입니다.
            <b> MDE</b> 가 그 눈금 폭입니다.</p>
          <LoopPgSummary payload={payload}/>
          <div className="v4s-log-controls">
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
          </div>
          {error && <p className="v4s-note">{error}</p>}
          {payload && (payload.reading_rules || []).map((rule, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {rule}</p>
          ))}
        </div>
      </div>

      {gauges.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">후보별 계기</div>
            <small className="v4s-en">확정 → 표본 부족 → 표본 절망 → 역방향 순</small></div>
          <div className="panel-bd">
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr>
                  <th>후보</th><th>상태</th>
                  <th className="num">짝</th><th className="num">관측 차이</th>
                  <th className="num">MDE(눈금)</th><th className="num">차이/눈금</th>
                  <th className="num">검정력</th><th className="num">필요 짝</th>
                  <th className="num">부족분</th><th className="num">추가 거래일</th>
                </tr></thead>
                <tbody>
                  {gauges.map((g, index) => (
                    <tr key={g.candidate_id || index}>
                      <td className="mono">{g.sell_name || g.candidate_id}
                        <br/><small className="v4s-en">{g.verdict}</small></td>
                      <td><span className={"badge " + (LOOP_PG_TONE[g.capability] || "")}
                                title={g.capability_note || ""}>{g.capability}</span></td>
                      <td className="num mono">{loopPgNum(g.pairs)}</td>
                      <td className={"num mono " + ((g.mean_diff_pct || 0) >= 0 ? "pos" : "neg")}>
                        {loopPgNum(g.mean_diff_pct, 4)}%p</td>
                      <td className="num mono">{loopPgNum(g.mde_pct, 4)}%p</td>
                      <td className="num mono">{g.effect_vs_mde === null || g.effect_vs_mde === undefined
                        ? "—"
                        : <span className={Number(g.effect_vs_mde) >= 1 ? "pos" : "neg"}>
                            {loopPgNum(g.effect_vs_mde, 2)}배</span>}</td>
                      <td className="num"><LoopPgPowerBar value={g.achieved_power} target={g.target_power}/></td>
                      <td className="num mono">{loopPgNum(g.required_pairs, 0)}</td>
                      <td className="num mono">{g.extra_pairs_needed === null || g.extra_pairs_needed === undefined
                        ? "—" : "+" + loopPgNum(g.extra_pairs_needed, 0)}</td>
                      <td className="num mono">{g.extra_days_needed === null || g.extra_days_needed === undefined
                        ? "—" : "+" + loopPgNum(g.extra_days_needed, 0) + "일"}</td>
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
