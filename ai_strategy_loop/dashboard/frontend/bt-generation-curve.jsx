/* QSP7 페이지 20 — 세대 진행 곡선(G-0c/G-0e).
 * 언제 멈출지 판단한다. 판정 입력은 홀드아웃 '건당' 손익이다 —
 * 총손익은 거래를 줄이기만 해도 좋아지므로 수렴 판정에 쓰지 않는다. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_gc, useEffect: useEffect_gc } = React;

const _gcVERDICT = {
  not_started: ["시작 전", "neutral"],
  running: ["진행 가능", "ok"],
  converged: ["수렴", "done"],
  budget_exhausted: ["예산 소진", "warn"],
  diverged: ["발산 — 롤백 필요", "danger"],
};

function _gcNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function _gcPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "—";
}

/* 세대별 건당 손익 2선. 값이 음수 영역이라 0선이 아니라 최솟값 기준으로 그린다. */
function _gcLines({ rows }) {
  const all = rows.flatMap(row => [Number(row.design_per_trade) || 0, Number(row.holdout_per_trade) || 0]);
  const low = Math.min(...all), high = Math.max(...all);
  const span = high - low || 1;
  const place = value => 100 - Math.round(((Number(value) - low) / span) * 100);
  return <div className="tp-gc-lines" role="img" aria-label="세대별 건당 손익 추이">
    {rows.map((row, index) => <div key={row.generation} className="col" style={{ left: `${(index / Math.max(1, rows.length - 1)) * 100}%` }}>
      <span className="dot design" style={{ top: `${place(row.design_per_trade)}%` }}
        title={`${row.generation}세대 설계 ${_gcNum(row.design_per_trade)}원`}/>
      <span className="dot holdout" style={{ top: `${place(row.holdout_per_trade)}%` }}
        title={`${row.generation}세대 홀드아웃 ${_gcNum(row.holdout_per_trade)}원`}/>
      <small>{row.generation}</small>
    </div>)}
  </div>;
}

function BtGenerationCurve({ baseUrl, lane }) {
  const [payload, setPayload] = useState_gc(null);
  const [error, setError] = useState_gc("");

  useEffect_gc(() => {
    if (!baseUrl) return undefined;
    let alive = true;
    setPayload(null); setError("");
    _btFetchJson(`${baseUrl}/bt/trade-path/generations?lane=${encodeURIComponent(lane)}`, 30000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, lane]);

  if (error) return <p className="tp-error" role="alert">세대 이력 조회 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">세대 이력을 불러오는 중입니다…</div>;

  const rows = payload.generations || [];
  const [label, tone] = _gcVERDICT[payload.verdict] || [payload.verdict, "neutral"];
  const deltas = rows.map(row => Number(row.holdout_delta) || 0);
  const peak = Math.max(1, ...deltas.map(Math.abs));

  return <section className="tp-subpanel tp-generation-curve" aria-labelledby="tp-gc-title">
    <header>
      <div><b id="tp-gc-title">세대 진행 곡선</b>
        <small>{payload.rule}</small></div>
      <span className="tp-authority official">정본</span>
    </header>

    <div className={`tp-gc-verdict ${tone}`}>
      <b>{label}</b><span>{payload.reason}</span>
      {payload.rollback_to && <em>→ {payload.rollback_to}세대로 롤백하세요</em>}
    </div>

    {rows.length === 0
      ? <div className="tp-empty">아직 기록된 세대가 없습니다. G-1 에서 기준선과 1세대 후보를 공식 실행하면 여기에 쌓입니다.</div>
      : <>
        {_gcLines({ rows })}
        <div className="tp-gc-legend mono"><span className="design">● 설계</span><span className="holdout">● 홀드아웃</span></div>

        <div className="tp-gc-deltas" aria-label="세대별 추가 개선폭">
          {rows.map(row => {
            const value = Number(row.holdout_delta) || 0;
            return <div key={row.generation} className="bar">
              <i className={value >= 0 ? "pos" : "neg"} style={{ height: `${Math.round((Math.abs(value) / peak) * 100)}%` }}/>
              <small className="mono">{value >= 0 ? "+" : ""}{_gcNum(value)}</small>
              <small>{row.generation}세대</small>
            </div>;
          })}
        </div>

        <div className="tp-gc-table" role="table" aria-label="세대 이력">
          <div role="row" className="head">
            <span>세대</span><span>후보</span><span>설계 건당</span><span>홀드 건당</span>
            <span>홀드 개선</span><span>누적 유지율</span><span>게이트</span>
          </div>
          {rows.map(row => <div role="row" key={`${row.generation}-${row.candidate_id}`}>
            <b>{row.generation}</b>
            <code title={(row.clauses || []).join(" · ")}>{row.candidate_id}</code>
            <span className="mono">{_gcNum(row.design_per_trade)}</span>
            <span className="mono">{_gcNum(row.holdout_per_trade)}</span>
            <span className={`mono ${Number(row.holdout_delta) >= 0 ? "pos" : "neg"}`}>
              {Number(row.holdout_delta) >= 0 ? "+" : ""}{_gcNum(row.holdout_delta)}</span>
            <span className={`mono ${Number(row.cumulative_retention) < Number(payload.cumulative_floor) ? "neg" : ""}`}>
              {_gcPct(row.cumulative_retention)}</span>
            <span>{row.gate_verdict || "—"}</span>
          </div>)}
        </div>

        <div className="tp-entry-guard">
          누적 유지율 하한 {_gcPct(payload.cumulative_floor)} · 수렴 임계 {_gcNum(payload.epsilon)}원/건 ·
          채택은 사람 승인 사항입니다.
        </div>
      </>}
  </section>;
}

Object.assign(window, { BtGenerationCurve });
export { BtGenerationCurve };
