/* QSP7 페이지 17 — 손실 프로파일러(G-0c).
 * 어느 변수의 어느 구간이 설계·홀드아웃 양쪽에서 지속 손실인지 눈으로 확인한다.
 * 관찰(진단) 권위 — 제거 효과가 아니라 '지금 그 구간이 얼마나 나쁜가'를 보여준다. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_lp, useEffect: useEffect_lp } = React;

const _lpSHAPE = {
  monotone_up: ["단조 상승", "값이 클수록 좋아짐 → 낮은 쪽을 자름"],
  monotone_down: ["단조 하락", "값이 클수록 나빠짐 → 높은 쪽을 자름"],
  tail_high: ["상단 꼬리", "위쪽 2분위만 급락"],
  tail_low: ["하단 꼬리", "아래쪽 2분위만 급락"],
  valley: ["골짜기", "가운데 구간만 나쁨 → 양측 범위로 자름"],
  multi_band: ["다중 밴드", "나쁜 구간이 둘로 갈라짐 → or 로 묶어 자름"],
  flat: ["평탄", "판별력 없음 — 자를 곳이 없습니다"],
};

function _lpNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function _lpPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "—";
}
function _lpEdge(value) {
  return value === null || value === undefined ? "∞" : _lpNum(value, 2);
}

function _lpBars({ rows, overall, span }) {
  const values = rows.map(row => Number(row.per_trade) || 0);
  const limit = Math.max(1, ...values.map(Math.abs));
  return <div className="tp-lp-bars">
    {rows.map(row => {
      const value = Number(row.per_trade) || 0;
      const inSpan = span && row.bucket >= span.from_bucket && row.bucket <= span.to_bucket;
      const width = Math.round((Math.abs(value) / limit) * 100);
      const tone = value < overall ? "bad" : "good";
      return <div key={row.bucket} className={`tp-lp-bar ${tone}${row.insufficient ? " thin" : ""}${inSpan ? " span" : ""}`}
        title={`D${row.bucket} · ${row.n.toLocaleString()}건 · 건당 ${_lpNum(value)}원${row.insufficient ? " · 표본 부족" : ""}`}>
        <span className="lbl">D{row.bucket}</span>
        <i style={{ width: `${width}%` }}/>
        <span className="val mono">{_lpNum(value)}</span>
      </div>;
    })}
  </div>;
}

function BtLossProfile({ baseUrl, jobId, lane }) {
  const [payload, setPayload] = useState_lp(null);
  const [error, setError] = useState_lp("");
  const [picked, setPicked] = useState_lp("");

  useEffect_lp(() => {
    if (!baseUrl || !jobId) return undefined;
    let alive = true;
    setPayload(null); setError(""); setPicked("");
    _btFetchJson(`${baseUrl}/bt/trade-path/loss-profile?job_id=${encodeURIComponent(jobId)}&lane=${encodeURIComponent(lane)}`, 180000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, jobId, lane]);

  if (!jobId) return <div className="tp-empty">완료된 백테스트 결과를 먼저 선택하세요.</div>;
  if (error) return <p className="tp-error" role="alert">손실 프로파일 조회 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">변수별 10분위 손실 곡선을 계산 중입니다…</div>;
  if (!payload.available) {
    return <div className="tp-empty">표본이 부족합니다 — 설계 {payload.design_rows}건 / 홀드아웃 {payload.holdout_rows}건
      (최소 {payload.minimum_total}건 필요). 이것도 결과입니다.</div>;
  }

  const profiles = payload.profiles || [];
  const current = profiles.find(row => row.variable === picked) || profiles[0] || null;

  return <section className="tp-subpanel tp-loss-profile" aria-labelledby="tp-lp-title">
    <header>
      <div><b id="tp-lp-title">손실 프로파일러</b>
        <small>10분위 경계는 설계 구간에서만 산출 · 홀드아웃에 같은 경계 적용(누출 금지)</small></div>
      <span className="tp-authority diagnostic">진단</span>
    </header>
    <div className="tp-lp-kpis mono">
      분할 {payload.split} · 설계 {_lpNum(payload.design_rows)}건 / 홀드아웃 {_lpNum(payload.holdout_rows)}건 ·
      검정 {payload.tested}변수 · 홀드아웃 확인 {payload.confirmed_count} · 조건식 가능 {payload.proposable_count}
    </div>
    <div className="tp-entry-guard">{payload.guard}</div>

    {(payload.pareto || []).length > 0 && <div className="tp-lp-pareto">
      <b>파레토 전선 — 적게 자르고 많이 얻는 축</b>
      {(payload.pareto || []).map(row => <span key={row.variable} className="mono">
        {row.variable} · 제거 {_lpPct(row.removal)} · 건당 +{_lpNum(row.gain)}원
      </span>)}
    </div>}

    <div className="tp-lp-body">
      <div className="tp-lp-list" role="listbox" aria-label="변수 목록">
        {profiles.map(row => {
          const shape = _lpSHAPE[row.shape] || [row.shape, ""];
          const active = current && row.variable === current.variable;
          return <button key={row.variable} role="option" aria-selected={!!active}
            className={active ? "active" : ""} onClick={() => setPicked(row.variable)}>
            <code>{row.variable}</code>
            <span className={`tp-lp-shape ${row.shape}`}>{shape[0]}</span>
            {row.confirmed ? <span className="tp-lp-ok">확인</span>
              : <span className="tp-lp-weak">{row.reason === "flat" ? "평탄" : "미확인"}</span>}
            {!row.proposable && <span className="tp-lp-diag">진단 전용</span>}
          </button>;
        })}
        {profiles.length === 0 && <div className="tp-empty">판별력 있는 변수가 없습니다 — 이것도 결과입니다.</div>}
      </div>

      {current && <div className="tp-lp-detail">
        <div className="tp-lp-head">
          <b><code>{current.variable}</code></b>
          <span className={`tp-lp-shape ${current.shape}`}>{(_lpSHAPE[current.shape] || [current.shape])[0]}</span>
          <small>{(_lpSHAPE[current.shape] || ["", ""])[1]}</small>
          {!current.proposable && <span className="tp-lp-diag">이 변수는 진단 전용입니다 — 조건식 후보 축으로 쓰지 않습니다.</span>}
        </div>
        <div className="tp-lp-two">
          <div><small>설계 (전체 건당 {_lpNum(current.design_overall)}원)</small>
            {_lpBars({ rows: current.design || [], overall: current.design_overall, span: current.worst_span })}</div>
          <div><small>홀드아웃 (전체 건당 {_lpNum(current.holdout_overall)}원)</small>
            {_lpBars({ rows: current.holdout || [], overall: current.holdout_overall, span: current.worst_span })}</div>
        </div>
        {current.worst_span
          ? <div className={`tp-lp-span ${current.confirmed ? "confirmed" : "unstable"}`}>
            <b>{current.confirmed ? "홀드아웃 확인됨" : "홀드아웃 미확인 — 후보 제외"}</b>
            <code>{_lpEdge(current.worst_span.low)} &lt; {current.variable} ≤ {_lpEdge(current.worst_span.high)}</code>
            <span className="mono">D{current.worst_span.from_bucket}~D{current.worst_span.to_bucket} ·
              제거 {_lpPct(current.worst_span.design_share)} ·
              설계 건당 {_lpNum(current.worst_span.design_per_trade)} ·
              홀드 건당 {_lpNum(current.worst_span.holdout_per_trade)}</span>
            {!current.confirmed && <small>사유: {current.reason}</small>}
          </div>
          : <div className="tp-empty">인접 2칸 이상 연속인 손실 구간이 없습니다 — 고립 1칸은 노이즈로 보고 제외합니다.</div>}
      </div>}
    </div>
  </section>;
}

Object.assign(window, { BtLossProfile });
export { BtLossProfile };
