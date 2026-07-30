/* bt-leaf-explorer.jsx — QSP1 라벨셋 탐색기(P1): 리프(시간밴드×시총단계) 잔차 히트맵.
 *
 *   목적(사용자 방법론): 수익률이 라벨링된 백테 결과를 시간대·시총대 좌표로 펼쳐,
 *   "어느 리프가 손실을 만드는가"를 눈으로 짚고 → 그 리프의 대표 거래·변별 변수로
 *   조건식 수정(리프 경계 조임)의 근거를 얻는 화면이다.
 *
 *   데이터: GET /bt/analysis/leaf_matrix (job_id 또는 run_id+gen_no).
 *   포맷: 공통 카드 규약(제목 좌 · 메타 우 · 도움말 하) + 셀 클릭 → 상세(대표 거래).
 *   R0 반영: 평균과 중앙값·승률 병기(복권형 분포가 평균을 왜곡) — 셀은 중앙값 토글 지원.
 */
import { useState_btc, useEffect_btc } from "./bt-chart-utils.jsx";
import { _btFetchJson } from "./bt-tab-utils.jsx";
import { MetricHelpStrip } from "./chart-primitives.jsx";

const _LF_TIME_ORDER = [
  "B1_900_902", "B2_902_905", "B3_905_910", "B4_910_920", "B5_920_930",
  "B1_장초반", "B2_오전", "B3_한산", "B4_오후", "B5_마감",
  "out_of_window", "unknown",
];
const _LF_CAP_ORDER = ["S_3000미만", "M1_3000_5000", "M2_5000_10000", "L_10000이상", "unknown"];
const _LF_CAP_LABEL = {
  S_3000미만: "소형 <3천억", M1_3000_5000: "중소 3~5천억",
  M2_5000_10000: "중형 5천~1조", L_10000이상: "대형 ≥1조", unknown: "미상",
};

function _lfCellColor(v) {
  // 손실 red ↔ 이익 teal, 0 중심. |0.8%| 에서 포화(전형적 리프 평균 범위).
  if (v == null || !Number.isFinite(v)) return "var(--bg-2)";
  const t = Math.max(-1, Math.min(1, v / 0.8));
  return t >= 0 ? `rgba(76,214,179,${0.12 + 0.5 * t})` : `rgba(255,107,107,${0.12 + 0.5 * -t})`;
}

function BtLeafExplorer({ baseUrl, jobId, evoSource, isDemo }) {
  const [data, setData] = useState_btc(null);
  const [metric, setMetric] = useState_btc("mean_pct");   // mean_pct | median_pct
  const [picked, setPicked] = useState_btc(null);          // "time×cap" | null
  const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);

  useEffect_btc(() => {
    setData(null); setPicked(null);
    if (isDemo || !baseUrl || (!jobId && !isEvo)) return undefined;
    const q = jobId
      ? "job_id=" + encodeURIComponent(jobId)
      : "run_id=" + encodeURIComponent(evoSource.run_id) + "&gen_no=" + encodeURIComponent(evoSource.gen_no);
    let cancelled = false;
    _btFetchJson(baseUrl + "/bt/analysis/leaf_matrix?" + q, 15000)
      .then(j => { if (!cancelled) setData(j && j.available ? j : { available: false }); })
      .catch(() => { if (!cancelled) setData({ available: false }); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, jobId, isEvo, isEvo ? evoSource.run_id : "", isEvo ? evoSource.gen_no : -1]);

  if (isDemo || (!jobId && !isEvo)) return null;
  const rows = (data && data.leaf_matrix) || [];
  const times = _LF_TIME_ORDER.filter(t => rows.some(r => r.leaf_time === t));
  const caps = _LF_CAP_ORDER.filter(c => rows.some(r => r.leaf_cap === c));
  const byKey = {};
  rows.forEach(r => { byKey[r.leaf_time + "×" + r.leaf_cap] = r; });
  const pickedRow = picked ? byKey[picked] : null;
  const samples = (picked && data && data.leaf_samples && data.leaf_samples[picked]) || [];
  const feats = (data && data.features) || [];

  return (
    <section className="panel bt-equal-card" aria-label="리프 잔차 히트맵 — 시간밴드×시총단계">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          리프 잔차 히트맵 · 시간 × 시총
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="bt-quant-meta mono">
            {data && data.available ? `${data.n.toLocaleString("ko-KR")}거래 · ${data.timeframe} · 파생 ${(data.derived || []).length}종` : "—"}
          </span>
          <span className="bt-mc-method" role="group" aria-label="셀 값 기준">
            <button type="button" className={"btn ghost sm" + (metric === "mean_pct" ? " active" : "")}
                    onClick={() => setMetric("mean_pct")} title="셀 값 = 리프 평균 수익률">평균</button>
            <button type="button" className={"btn ghost sm" + (metric === "median_pct" ? " active" : "")}
                    onClick={() => setMetric("median_pct")}
                    title="셀 값 = 리프 중앙값 수익률 — 복권형(가끔 큰 승) 분포에서 평균 왜곡을 걷어냅니다">중앙값</button>
          </span>
        </div>
      </div>
      <div className="panel-bd">
        <MetricHelpStrip items={[
          "행 = 시총단계 · 열 = 시간밴드 · 셀 = 수익률(색) + 표본·승률",
          "빨강이 짙을수록 손실 집중 — 조건식 조임(경계 수정)의 1순위 후보",
          "셀 클릭 = 그 리프의 대표 거래(최악 4·최고 4)와 좌표 확인",
        ]} />
        {!data && <p className="v54-quant-note">리프 매트릭스 로딩…</p>}
        {data && !data.available && <p className="v54-quant-note">이 결과에는 리프 분석용 CSV 가 없습니다.</p>}
        {data && data.available && (
          <>
            <div className="bt-leaf-grid" style={{ gridTemplateColumns: `120px repeat(${times.length}, minmax(84px, 1fr))` }}>
              <div className="bt-leaf-corner mono">시총 \ 시간</div>
              {times.map(t => <div key={t} className="bt-leaf-colhead mono">{t.replace(/^B\d_/, "")}</div>)}
              {caps.map(c => (
                <React.Fragment key={c}>
                  <div className="bt-leaf-rowhead mono">{_LF_CAP_LABEL[c] || c}</div>
                  {times.map(t => {
                    const r = byKey[t + "×" + c];
                    const v = r ? r[metric] : null;
                    const key = t + "×" + c;
                    return (
                      <button key={key} type="button"
                              className={"bt-leaf-cell mono" + (picked === key ? " picked" : "") + (r && !r.reliable ? " thin" : "")}
                              style={{ background: _lfCellColor(v) }}
                              title={r ? `${key}\n평균 ${r.mean_pct.toFixed(3)}% · 중앙값 ${r.median_pct.toFixed(2)}% · 승률 ${r.win_rate.toFixed(1)}%\nn=${r.n}${r.reliable ? "" : " (표본 부족)"}` : "거래 없음"}
                              onClick={() => setPicked(picked === key ? null : key)}>
                        {r ? <>
                          <b>{v.toFixed(2)}%</b>
                          <small>n={r.n} · 승 {Math.round(r.win_rate)}%</small>
                        </> : <small>—</small>}
                      </button>
                    );
                  })}
                </React.Fragment>
              ))}
            </div>
            {pickedRow && (
              <div className="bt-leaf-detail" role="region" aria-label={"리프 상세 " + picked}>
                <div className="bt-leaf-detail-hd mono">
                  <b>{picked}</b>
                  <span>n={pickedRow.n} · 평균 {pickedRow.mean_pct.toFixed(3)}% · 중앙값 {pickedRow.median_pct.toFixed(2)}% ·
                    승률 {pickedRow.win_rate.toFixed(1)}% · 합계 {Math.round(pickedRow.total_krw).toLocaleString("ko-KR")}원
                    {pickedRow.reliable ? "" : " · ⚠ 표본 부족(수정 근거로 쓰지 말 것)"}</span>
                </div>
                {samples.length > 0 && (
                  <table className="mono bt-leaf-sample"><thead>
                    <tr><th>종목</th><th>매수시간</th><th>수익률</th><th>수익금</th></tr></thead>
                    <tbody>
                      {samples.map((s, i) => (
                        <tr key={i} className={s.pct >= 0 ? "pos" : "neg"}>
                          <td>{s.name}</td><td>{s.buy_time}</td>
                          <td>{s.pct.toFixed(2)}%</td><td>{Math.round(s.krw).toLocaleString("ko-KR")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
            {feats.length > 0 && (
              <div className="bt-leaf-feats">
                <b className="mono">변별 상위 변수 (승·패 Cohen&apos;s d)</b>
                <div className="bt-leaf-feat-bars">
                  {feats.slice(0, 8).map(f => (
                    <div key={f.feature} className="bt-leaf-feat mono" title={`승 평균 ${f.win_mean.toFixed(4)} / 패 평균 ${f.loss_mean.toFixed(4)} · n=${f.n}`}>
                      <span className="k">{f.feature}</span>
                      <span className="bar"><i className={f.d >= 0 ? "pos" : "neg"}
                        style={{ width: Math.min(100, Math.abs(f.d) * 220) + "%" }}></i></span>
                      <span className="v">{f.d >= 0 ? "+" : ""}{f.d.toFixed(3)}</span>
                    </div>
                  ))}
                </div>
                <p className="v54-quant-note">|d| 가 큰 변수가 승·패를 가른다 — 리프 경계 수정(P2 제안 생성)의 재료.</p>
              </div>
            )}
          </>
        )}
      </div>
    </section>
  );
}

Object.assign(window, { BtLeafExplorer });
// dual-safe ESM export. KEEP on ONE physical line.
export { BtLeafExplorer };
