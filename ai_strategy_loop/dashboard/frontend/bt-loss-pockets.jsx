/* QSP7 페이지 18 — 2D 손실 포켓 지도(G-0c).
 * 한 변수로는 안 보이고 조합에서만 드러나는 손실 영역을 찾는다.
 * FDR(q≤0.10) 통과 칸으로만 포켓을 만들고, 직사각형 근사 낭비 30% 이하만 남긴다. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_pk, useEffect: useEffect_pk } = React;

const _pkDEFAULT = "B_등락율,B_체결강도,B_회전율,B_시분초,B_시가총액,B_전일비";

function _pkNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function _pkPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? (number * 100).toFixed(2) + "%" : "—";
}
function _pkBound(low, high, name) {
  if (low === null || low === undefined) return `${name} ≤ ${_pkNum(high, 2)}`;
  if (high === null || high === undefined) return `${name} > ${_pkNum(low, 2)}`;
  return `${_pkNum(low, 2)} < ${name} ≤ ${_pkNum(high, 2)}`;
}

/* 10×10 격자 위에 포켓 칸만 칠한다. 전체 칸 통계는 API 가 주지 않으므로
 * '어디에 있는지'를 보여주는 위치 지도이며, 수치는 포켓 단위로 읽는다. */
function _pkGrid({ pocket }) {
  const cells = new Set((pocket.cell_list || []).map(cell => `${cell[0]}:${cell[1]}`));
  const rows = [];
  for (let y = 10; y >= 1; y -= 1) {
    const columns = [];
    for (let x = 1; x <= 10; x += 1) {
      const hit = cells.has(`${x}:${y}`);
      columns.push(<i key={x} className={hit ? "hit" : ""} title={`${pocket.pair[0]} D${x} × ${pocket.pair[1]} D${y}`}/>);
    }
    rows.push(<div key={y} className="row">{columns}</div>);
  }
  return <div className="tp-pk-grid" aria-label="포켓 위치 격자">{rows}</div>;
}

function BtLossPockets({ baseUrl, jobId, lane }) {
  const [variables, setVariables] = useState_pk(_pkDEFAULT);
  const [applied, setApplied] = useState_pk(_pkDEFAULT);
  const [payload, setPayload] = useState_pk(null);
  const [error, setError] = useState_pk("");

  useEffect_pk(() => {
    if (!baseUrl || !jobId) return undefined;
    let alive = true;
    setPayload(null); setError("");
    const query = `job_id=${encodeURIComponent(jobId)}&lane=${encodeURIComponent(lane)}&variables=${encodeURIComponent(applied)}`;
    _btFetchJson(`${baseUrl}/bt/trade-path/loss-pockets?${query}`, 300000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, jobId, lane, applied]);

  if (!jobId) return <div className="tp-empty">완료된 백테스트 결과를 먼저 선택하세요.</div>;

  const pockets = (payload && payload.pockets) || [];
  return <section className="tp-subpanel tp-loss-pockets" aria-labelledby="tp-pk-title">
    <header>
      <div><b id="tp-pk-title">2D 손실 포켓 지도</b>
        <small>상관 |r|&lt;0.6 인 쌍만 · 설계·홀드아웃 동시 손실 · Welch t + BH-FDR(q≤0.10) · 인접 2칸 이상</small></div>
      <span className="tp-authority diagnostic">진단</span>
    </header>

    <div className="tp-pk-controls">
      <label>변수(쉼표 구분)
        <input value={variables} onChange={event => setVariables(event.target.value)} spellCheck="false"/>
      </label>
      <button className="btn ghost sm" onClick={() => setApplied(variables)}>다시 탐색</button>
      <button className="btn ghost sm" onClick={() => { setVariables(_pkDEFAULT); setApplied(_pkDEFAULT); }}>기본값</button>
    </div>

    {error && <p className="tp-error" role="alert">포켓 탐색 실패: {error}</p>}
    {!payload && !error && <div className="tp-empty">변수쌍 격자를 훑는 중입니다… (변수가 많으면 시간이 걸립니다)</div>}

    {payload && <>
      <div className="tp-pk-kpis mono">
        분할 {payload.split} · 변수 {(payload.variables || []).length}개 · FDR α={payload.fdr_alpha} · 포켓 {pockets.length}건
      </div>
      {pockets.length === 0 && <div className="tp-empty">
        {payload.reason === "no_eligible_pair"
          ? "2D 포켓은 변수 2개 이상이 필요합니다."
          : "유의한 손실 포켓이 없습니다 — 이것도 결과입니다."}
      </div>}
      <div className="tp-pk-list">
        {pockets.map((pocket, index) => <article key={`${pocket.pair[0]}-${pocket.pair[1]}-${index}`} className="tp-pk-card">
          <header>
            <b><code>{pocket.pair[0]}</code> × <code>{pocket.pair[1]}</code></b>
            <span className="mono">칸 {pocket.cells} · q≤{Number(pocket.max_q).toFixed(3)} · 낭비 {_pkPct(pocket.rect_waste)}</span>
          </header>
          {_pkGrid({ pocket })}
          <div className="tp-pk-expr">
            <code>{_pkBound(pocket.x_low, pocket.x_high, pocket.pair[0].replace(/^B_/, ""))} and {_pkBound(pocket.y_low, pocket.y_high, pocket.pair[1].replace(/^B_/, ""))}</code>
          </div>
          <div className="tp-pk-metrics mono">
            <span>제거 {_pkPct(pocket.design_share)}</span>
            <span className="neg">설계 건당 {_pkNum(pocket.design_per_trade)}</span>
            <span className="neg">홀드 건당 {_pkNum(pocket.holdout_per_trade)}</span>
            <span>거래 {_pkNum(pocket.design_n)}/{_pkNum(pocket.holdout_n)}</span>
          </div>
        </article>)}
      </div>
      {payload.note && <div className="tp-entry-guard">{payload.note}</div>}
    </>}
  </section>;
}

Object.assign(window, { BtLossPockets });
export { BtLossPockets };
