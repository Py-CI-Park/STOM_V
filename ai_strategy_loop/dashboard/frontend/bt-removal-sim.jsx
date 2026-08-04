/* QSP7 페이지 19 — 제거 시뮬레이터(G-0c).
 * 공식 백테스트 전에 제거 조합을 즉시 실험한다. 백테스트가 아니라 CSV 재계산이다.
 * ⚠ 체계적 편향: 제거로 풀린 자금의 재유입을 반영하지 못한다 — 순위용이다. */
import { _btPostJson } from "./bt-tab-utils.jsx";
const { useState: useState_rs } = React;

function _rsNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function _rsPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "—";
}
function _rsParse(text) {
  /* "B_등락율 > 15.68" / "B_등락율 6.3~15.7" / "B_등락율 <= 3" 를 구간으로 읽는다. */
  const cleaned = String(text || "").trim();
  if (!cleaned) return null;
  let match = cleaned.match(/^(\S+)\s*(>=|>)\s*(-?[\d.]+)$/);
  if (match) return { column: match[1], low: Number(match[3]), high: null };
  match = cleaned.match(/^(\S+)\s*(<=|<)\s*(-?[\d.]+)$/);
  if (match) return { column: match[1], low: null, high: Number(match[3]) };
  match = cleaned.match(/^(\S+)\s+(-?[\d.]+)\s*~\s*(-?[\d.]+)$/);
  if (match) return { column: match[1], low: Number(match[2]), high: Number(match[3]) };
  return null;
}
function _rsLabel(interval) {
  if (interval.low === null) return `${interval.column} ≤ ${interval.high}`;
  if (interval.high === null) return `${interval.column} > ${interval.low}`;
  return `${interval.low} < ${interval.column} ≤ ${interval.high}`;
}

function BtRemovalSim({ baseUrl, jobId, lane }) {
  const [draft, setDraft] = useState_rs("");
  const [cart, setCart] = useState_rs([]);      // [{ terms: [[interval, ...]] }]
  const [pending, setPending] = useState_rs([]); // 지금 조립 중인 AND 묶음
  const [payload, setPayload] = useState_rs(null);
  const [error, setError] = useState_rs("");
  const [busy, setBusy] = useState_rs(false);
  const [autos, setAutos] = useState_rs(null);

  const addInterval = () => {
    const parsed = _rsParse(draft);
    if (!parsed) { setError("형식을 읽지 못했습니다. 예: B_등락율 > 15.68 · B_체결강도 62~111 · B_시분초 <= 90122"); return; }
    setError(""); setPending(pending.concat([parsed])); setDraft("");
  };
  const commitClause = () => {
    if (!pending.length) return;
    setCart(cart.concat([{ terms: [pending] }])); setPending([]);
  };
  const run = () => {
    const clauses = cart.concat(pending.length ? [{ terms: [pending] }] : []);
    if (!clauses.length || !jobId) return;
    setBusy(true); setError(""); setPayload(null);
    _btPostJson(`${baseUrl}/bt/trade-path/removal-simulate`,
      { job_id: jobId, lane, clauses }, 180000
    ).then(result => { setPayload(result); if (!result.available) setError(result.reason || "실패"); })
      .catch(reason => setError(String(reason.message || reason)))
      .finally(() => setBusy(false));
  };

  const suggest = () => {
    setBusy(true); setError(""); setAutos(null);
    _btPostJson(`${baseUrl}/bt/trade-path/region-candidates`,
      { job_id: jobId, lane, generation: 1 }, 600000
    ).then(result => { setAutos(result); if (!result.available) setError(result.reason || "실패"); })
      .catch(reason => setError(String(reason.message || reason)))
      .finally(() => setBusy(false));
  };
  const adopt = candidate => {
    setCart((candidate.clauses || []).map(clause => ({
      terms: (clause.terms || []).map(group => group.map(interval => ({
        column: interval.column, low: interval.low, high: interval.high,
      }))),
    })));
    setPending([]); setPayload(null);
  };

  if (!jobId) return <div className="tp-empty">완료된 백테스트 결과를 먼저 선택하세요.</div>;

  const clauses = cart.concat(pending.length ? [{ terms: [pending] }] : []);
  const retention = payload && payload.available ? Number(payload.design_retention) : null;
  const floor = payload ? Number(payload.cumulative_floor) : 0.4;
  const gauge = retention === null ? 0 : Math.max(0, Math.min(100, Math.round(retention * 100)));

  return <section className="tp-subpanel tp-removal-sim" aria-labelledby="tp-rs-title">
    <header>
      <div><b id="tp-rs-title">제거 시뮬레이터</b>
        <small>CSV 재계산 · 공식 백테스트가 아닙니다</small></div>
      <span className="tp-authority advisory">자문</span>
    </header>

    <div className="tp-rs-warn" role="note">
      ⚠ <b>재유입 미반영 · 순위용</b> — 제거로 풀린 자금이 다른 종목으로 재유입되는 효과를 계산하지 않습니다.
      R2 실측에서는 필터 적용 후 거래가 오히려 늘었습니다(유지율 100.7%). 판정은 공식 pair/gate 가 합니다.
    </div>

    <div className="tp-rs-controls">
      <label>제거 구간
        <input value={draft} placeholder="예: B_등락율 > 15.68" spellCheck="false"
          onChange={event => setDraft(event.target.value)}
          onKeyDown={event => { if (event.key === "Enter") addInterval(); }}/>
      </label>
      <button className="btn ghost sm" onClick={addInterval}>AND 로 추가</button>
      <button className="btn ghost sm" onClick={commitClause} disabled={!pending.length}>절로 확정</button>
      <button className="btn primary sm" onClick={run} disabled={!clauses.length || busy}>{busy ? "계산 중…" : "즉시 계산"}</button>
      <button className="btn ghost sm" onClick={() => { setCart([]); setPending([]); setPayload(null); setError(""); }}>비우기</button>
      <button className="btn ghost sm" onClick={suggest} disabled={busy}>후보 자동 생성</button>
    </div>

    <div className="tp-rs-cart">
      {cart.map((clause, index) => <span key={index} className="tp-rs-chip">
        <code>{clause.terms[0].map(_rsLabel).join(" and ")}</code>
        <button aria-label="이 절 제거" onClick={() => setCart(cart.filter((_, at) => at !== index))}>×</button>
      </span>)}
      {pending.length > 0 && <span className="tp-rs-chip pending">
        <code>{pending.map(_rsLabel).join(" and ")}</code>
        <button aria-label="조립 취소" onClick={() => setPending([])}>×</button>
      </span>}
      {clauses.length === 0 && <small>담긴 제거 구간이 없습니다. 프로파일러·포켓 지도에서 본 구간을 입력하세요.</small>}
    </div>

    {error && <p className="tp-error" role="alert">{error}</p>}

    {autos && autos.available && <div className="tp-rs-autos">
      <b>자동 생성 후보 — 손실 구간 {autos.profiles_tested}변수 · 2D 포켓 {autos.pockets_found}건에서</b>
      {(autos.candidates || []).map(candidate => <article key={candidate.candidate_id} className={`tp-rs-auto ${candidate.budget}`}>
        <header>
          <b>{candidate.candidate_id}</b>
          <span className="mono">유지 {_rsPct(candidate.design_retention)}/{_rsPct(candidate.holdout_retention)} ·
            설계 {_rsNum(candidate.design_per_trade_after - candidate.design_per_trade_before, 0)} ·
            홀드 {_rsNum(candidate.holdout_per_trade_after - candidate.holdout_per_trade_before, 0)}원/건</span>
          <button className="btn ghost sm" onClick={() => adopt(candidate)}>장바구니에 담기</button>
        </header>
        {(candidate.clauses || []).map((clause, index) => <div key={index} className="tp-rs-auto-clause">
          <code>{clause.expression}</code><small>{clause.source}</small>
        </div>)}
      </article>)}
      {(autos.candidates || []).length === 0 && <div className="tp-empty">예산 안에서 만들 수 있는 후보가 없습니다 — 이것도 결과입니다.</div>}
      {(autos.skipped || []).length > 0 && <details className="tp-bf-skipped">
        <summary>제외 {autos.skipped.length}건</summary>
        {autos.skipped.slice(0, 20).map((item, index) => <small key={index}>{item.item} — {item.reason}</small>)}
      </details>}
    </div>}

    {payload && payload.available && <>
      <div className="tp-rs-gauge" role="img" aria-label={`설계 유지율 ${gauge}%`}>
        <i style={{ width: `${gauge}%` }} className={retention < floor ? "danger" : ""}/>
        <b className="mono">설계 유지율 {_rsPct(payload.design_retention)} · 홀드 {_rsPct(payload.holdout_retention)}</b>
        <span className="floor" style={{ left: `${Math.round(floor * 100)}%` }} title={`누적 하한 ${Math.round(floor * 100)}%`}/>
      </div>
      <div className={`tp-rs-budget ${payload.budget}`}>
        예산 {payload.budget === "ok" ? "여유 있음" : "초과 — 이 조합은 후보로 쓰지 마세요"}
      </div>
      <div className="tp-rs-kpis">
        <article><small>설계 건당</small>
          <b>{_rsNum(payload.design_per_trade_before)} → {_rsNum(payload.design_per_trade_after)}</b>
          <span className={payload.design_per_trade_after >= payload.design_per_trade_before ? "pos" : "neg"}>
            {payload.design_per_trade_after >= payload.design_per_trade_before ? "+" : ""}
            {_rsNum(payload.design_per_trade_after - payload.design_per_trade_before)}원
          </span></article>
        <article><small>홀드아웃 건당</small>
          <b>{_rsNum(payload.holdout_per_trade_before)} → {_rsNum(payload.holdout_per_trade_after)}</b>
          <span className={payload.holdout_per_trade_after >= payload.holdout_per_trade_before ? "pos" : "neg"}>
            {payload.holdout_per_trade_after >= payload.holdout_per_trade_before ? "+" : ""}
            {_rsNum(payload.holdout_per_trade_after - payload.holdout_per_trade_before)}원
          </span></article>
        <article><small>제거된 손익</small>
          <b>{_rsNum(payload.design_removed_pnl)}원</b>
          <span>홀드 {_rsNum(payload.holdout_removed_pnl)}원</span></article>
      </div>
      <details className="tp-rs-code" open>
        <summary>생성될 STOM 매수식 (intent gate 통과분)</summary>
        <pre className="mono">{payload.stom_code}</pre>
      </details>
      <div className="tp-entry-guard">{payload.caveat}</div>
    </>}
  </section>;
}

Object.assign(window, { BtRemovalSim });
export { BtRemovalSim };
