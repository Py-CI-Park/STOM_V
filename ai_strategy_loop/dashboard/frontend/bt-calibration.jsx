/* QSP7 virtual↔official calibration ledger (P3-3): trust of advisory deltas, accumulated. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_cal, useEffect: useEffect_cal } = React;

function BtCalibration({ baseUrl, lane }) {
  const [payload, setPayload] = useState_cal(null);
  const [error, setError] = useState_cal("");
  useEffect_cal(() => {
    if (!baseUrl) return undefined;
    let alive = true;
    _btFetchJson(`${baseUrl}/bt/trade-path/calibration?lane=${encodeURIComponent(lane || "")}`, 20000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, lane]);

  if (error) return <p className="tp-error">캘리브레이션 조회 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">가상↔공식 오차 기록을 불러오는 중…</div>;
  const records = payload.records || [];
  return <section className="tp-subpanel tp-calibration" aria-labelledby="tp-cal-title">
    <header><div><b id="tp-cal-title">가상 ↔ 공식 캘리브레이션</b><small>advisory delta 를 얼마나 믿을 수 있는지의 실측 — 후보 {payload.minimum_for_calibration}개 이상 축적 시 판정</small></div><span className="tp-authority diagnostic">진단</span></header>
    {records.length === 0
      ? <div className="tp-empty">축적된 기록이 없습니다. 후보 실행 콘솔에서 귀속 실행한 공식 pair 가 자동으로 쌓입니다.</div>
      : <div className="tp-cal-table" role="table">
        <div role="row" className="head"><span>후보</span><span>레인</span><span>구간</span><span>공식 delta</span><span>가상 delta</span></div>
        {records.map((row, index) => <div role="row" key={`${row.candidate_id}-${index}`}>
          <code>{row.candidate_id}</code><span>{row.lane}</span><span>{row.role}</span>
          <b>{Number(row.official_delta_profit_krw || 0).toLocaleString()}원</b>
          <span>{row.virtual_delta_profit_krw == null ? "미기록" : `${Number(row.virtual_delta_profit_krw).toLocaleString()}원`}</span>
        </div>)}
      </div>}
    <small className="tp-cal-note">상태: {payload.status === "ready" ? "판정 가능" : "축적 중"} · 오차 분포는 공식 pair 실행이 쌓일수록 정확해집니다.</small>
  </section>;
}

Object.assign(window, { BtCalibration });
export { BtCalibration };
