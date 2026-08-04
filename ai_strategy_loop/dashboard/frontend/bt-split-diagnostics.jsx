/* QSP7 페이지 21 — 구간 분할 진단(G-0c, 평가 프로토콜 v2 전용).
 * 연속 1회 런의 자본 곡선 위에서 설계/홀드아웃 경계를 보고 구간별 성적을 비교한다.
 * ⚠ 연속 런은 자본이 이어진다 — 홀드아웃은 독립 OOS 가 아니다. */
import { _btFetchJson } from "./bt-tab-utils.jsx";
const { useState: useState_sd, useEffect: useEffect_sd } = React;

function _sdNum(value, digits = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString(undefined, { maximumFractionDigits: digits }) : "—";
}
function _sdPct(value) {
  const number = Number(value);
  return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "—";
}
function _sdDate(value) {
  const text = String(value || "");
  return text.length === 8 ? `${text.slice(0, 4)}-${text.slice(4, 6)}-${text.slice(6)}` : text || "—";
}

function _sdCard({ title, tone, row }) {
  return <article className={`tp-sd-card ${tone}`}>
    <header><b>{title}</b><small>{_sdDate(row.first_date)} ~ {_sdDate(row.last_date)}</small></header>
    <div className="tp-sd-kpis">
      <span><small>거래</small><b>{_sdNum(row.trades)}</b></span>
      <span><small>건당 손익</small><b className={Number(row.per_trade_krw) >= 0 ? "pos" : "neg"}>{_sdNum(row.per_trade_krw)}원</b></span>
      <span><small>총손익</small><b className={Number(row.profit_krw) >= 0 ? "pos" : "neg"}>{_sdNum(row.profit_krw)}원</b></span>
      <span><small>승률</small><b>{_sdPct(row.win_rate)}</b></span>
    </div>
  </article>;
}

function BtSplitDiagnostics({ baseUrl, jobId, lane }) {
  const [payload, setPayload] = useState_sd(null);
  const [error, setError] = useState_sd("");

  useEffect_sd(() => {
    if (!baseUrl || !jobId) return undefined;
    let alive = true;
    setPayload(null); setError("");
    _btFetchJson(`${baseUrl}/bt/trade-path/split-diagnostics?job_id=${encodeURIComponent(jobId)}&lane=${encodeURIComponent(lane)}`, 120000)
      .then(result => { if (alive) setPayload(result); })
      .catch(reason => { if (alive) setError(String(reason.message || reason)); });
    return () => { alive = false; };
  }, [baseUrl, jobId, lane]);

  if (!jobId) return <div className="tp-empty">완료된 백테스트 결과를 먼저 선택하세요.</div>;
  if (error) return <p className="tp-error" role="alert">구간 분할 진단 실패: {error}</p>;
  if (!payload) return <div className="tp-empty">구간별 성적을 계산 중입니다…</div>;
  if (!payload.available) return <div className="tp-empty">분할 진단 불가: {payload.reason}</div>;

  const design = payload.design || {}, holdout = payload.holdout || {}, whole = payload.whole || {};
  const total = Number(whole.trades) || 1;
  const designShare = Math.round(((Number(design.trades) || 0) / total) * 100);

  return <section className="tp-subpanel tp-split-diagnostics" aria-labelledby="tp-sd-title">
    <header>
      <div><b id="tp-sd-title">구간 분할 진단</b>
        <small>연속 1회 런을 {_sdDate(payload.split)} 경계로 나눠 비교합니다 (후보당 백테스트 1회)</small></div>
      <span className="tp-authority official">정본</span>
    </header>

    <div className="tp-sd-warn" role="note">
      ⚠ <b>자본 연속 · 독립 OOS 아님</b> — {payload.caveat}
    </div>

    <div className="tp-sd-timeline" role="img" aria-label={`설계 구간 ${designShare}% · 홀드아웃 구간 ${100 - designShare}%`}>
      <i className="design" style={{ width: `${designShare}%` }}/>
      <i className="holdout" style={{ width: `${100 - designShare}%` }}/>
      <span className="boundary" style={{ left: `${designShare}%` }} title={`분할 경계 ${_sdDate(payload.split)}`}/>
    </div>

    <div className="tp-sd-cards">
      {_sdCard({ title: "설계 구간", tone: "design", row: design })}
      {_sdCard({ title: "홀드아웃 구간", tone: "holdout", row: holdout })}
      {_sdCard({ title: "전체 런", tone: "whole", row: whole })}
    </div>

    <div className={`tp-sd-recon ${payload.reconciled ? "ok" : "bad"}`}>
      {payload.reconciled
        ? <>검산 통과 — 설계 {_sdNum(design.trades)} + 홀드아웃 {_sdNum(holdout.trades)} = 전체 {_sdNum(whole.trades)}건</>
        : <>⚠ 검산 실패 — 설계 {_sdNum(design.trades)} + 홀드아웃 {_sdNum(holdout.trades)} ≠ 전체 {_sdNum(whole.trades)}건.
          분할이 거래를 빠뜨렸습니다. 이 판정은 신뢰할 수 없습니다.</>}
    </div>

    <div className="tp-sd-links">
      <b>구간별 자본곡선·언더워터·히트맵</b>
      <small>기존 분석 화면에 기간을 넘겨 그대로 봅니다(신규 차트 없음).</small>
      {Object.entries(payload.analysis_endpoints || {}).map(([name, url]) =>
        <button key={name} className="btn ghost sm"
          onClick={() => window.open(`${baseUrl}${url}&t_start=${design.first_date}&t_end=${design.last_date}`, "_blank", "noopener")}>
          설계 {name}
        </button>)}
      {Object.entries(payload.analysis_endpoints || {}).map(([name, url]) =>
        <button key={`h-${name}`} className="btn ghost sm"
          onClick={() => window.open(`${baseUrl}${url}&t_start=${holdout.first_date}&t_end=${holdout.last_date}`, "_blank", "noopener")}>
          홀드 {name}
        </button>)}
    </div>
  </section>;
}

Object.assign(window, { BtSplitDiagnostics });
export { BtSplitDiagnostics };
