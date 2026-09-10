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
import { useFeatureEvidence, FeatureQualityNotice } from "./bt-feature-evidence.jsx";
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

const _lfNumber=(value,digits=2)=>Number.isFinite(value)?value.toFixed(digits):"—";
const _lfWhole=value=>Number.isFinite(value)?Math.round(value).toLocaleString("ko-KR"):"—";

function BtLeafExplorer({ baseUrl, jobId, evoSource, isDemo, sourceHash }) {
  const [metric, setMetric] = useState_btc("mean_pct");   // mean_pct | median_pct
  const [picked, setPicked] = useState_btc(null);          // "time×cap" | null
  // v5.13.4(P2) — 수정 제안(읽기 전용 미리보기): 버튼 클릭 시에만 계산(지연 로드).
  const isEvo = !jobId && !!(evoSource && evoSource.run_id && evoSource.gen_no != null);
  const q = jobId
      ? "job_id=" + encodeURIComponent(jobId)
      : (isEvo ? "run_id=" + encodeURIComponent(evoSource.run_id) + "&gen_no=" + encodeURIComponent(evoSource.gen_no) : "");
  const query=useFeatureEvidence({baseUrl,paths:["/bt/analysis/leaf_matrix?"+q],enabled:!isDemo&&!!q,expectedHash:sourceHash});
  const data=query.payloads?.[0] || null;
  const proposals=useFeatureEvidence({baseUrl,paths:["/bt/analysis/revision_proposals?"+q],
    enabled:!isDemo&&isEvo&&!query.mismatch&&data?.analysis_ready!==false,automatic:false,timeoutMs:20000,
    expectedHash:data?.data_quality?.source_sha256||sourceHash});
  const props_=proposals.payloads?.[0] || null;
  const propsBusy=proposals.loading;
  const loadProposals=()=>{if(!propsBusy && data?.analysis_ready!==false) proposals.load();};
  useEffect_btc(()=>{setPicked(null);},[query.key]);

  if (isDemo || (!jobId && !isEvo)) return null;
  if(query.error || query.mismatch || data?.analysis_ready===false) return <FeatureQualityNotice payload={data} title="리프 분석 보류" reason={query.error||(query.mismatch?"선택한 결과와 분석 원본의 일치를 확인할 수 없습니다. 결과를 다시 조회하세요.":"")}/>;
  const proposalMismatch=proposals.mismatch;
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
          "전체 결과 CSV 기준 · 선택 구간 필터 미적용",
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
                              title={r ? `${key}\n평균 ${_lfNumber(r.mean_pct,3)}% · 중앙값 ${_lfNumber(r.median_pct)}% · 승률 ${_lfNumber(r.win_rate,1)}%\nn=${r.n}${r.reliable ? "" : " (표본 부족)"}` : "거래 없음"}
                              onClick={() => setPicked(picked === key ? null : key)}>
                        {r ? <>
                          <b>{_lfNumber(v)}%</b>
                          <small>n={r.n} · 승 {_lfWhole(r.win_rate)}%</small>
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
                  <span>n={pickedRow.n} · 평균 {_lfNumber(pickedRow.mean_pct,3)}% · 중앙값 {_lfNumber(pickedRow.median_pct)}% ·
                    승률 {_lfNumber(pickedRow.win_rate,1)}% · 합계 {_lfWhole(pickedRow.total_krw)}원
                    {pickedRow.reliable ? "" : " · ⚠ 표본 부족(수정 근거로 쓰지 말 것)"}</span>
                </div>
                {samples.length > 0 && (
                  <table className="mono bt-leaf-sample"><thead>
                    <tr><th>종목</th><th>매수시간</th><th>수익률</th><th>수익금</th></tr></thead>
                    <tbody>
                      {samples.map((s, i) => (
                        <tr key={i} className={s.pct >= 0 ? "pos" : "neg"}>
                          <td>{s.name}</td><td>{s.buy_time}</td>
                          <td>{_lfNumber(s.pct)}%</td><td>{_lfWhole(s.krw)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
            {isEvo && (
              <div className="bt-leaf-proposals">
                <div className="bt-leaf-prop-hd">
                  <b className="mono">수정 제안 (분석→조건식 번역 · 읽기 전용 미리보기)</b>
                  <button className="btn ghost sm" onClick={loadProposals} disabled={propsBusy}
                          title="손실 리프의 변별 변수와 승자 분위수 경계로 리프 단위 수정안을 만듭니다. 등록·적용은 하지 않습니다.">
                    {propsBusy ? "생성 중…" : (props_ ? "↻ 다시 생성" : "제안 생성")}
                  </button>
                </div>
                {(proposals.error || props_?.analysis_ready===false || proposalMismatch) && <FeatureQualityNotice payload={props_} title="수정 제안 보류" reason={proposals.error || (proposalMismatch?"리프 표와 제안의 원본 일치를 확인할 수 없습니다. 결과를 다시 조회하세요.":"")}/>}
                {props_ && props_.analysis_ready!==false && !props_.available && <p className="v54-quant-note">{props_.reason}</p>}
                {props_ && props_.available && (props_.proposals || []).length === 0 && (
                  <p className="v54-quant-note">{props_.reason}</p>
                )}
                {props_ && props_.analysis_ready!==false && !proposalMismatch && (props_.proposals || []).map((p, i) => (
                  <div key={i} className="bt-leaf-prop mono">
                    <div className="bt-leaf-prop-title">
                      <span className={"badge " + ((p.gate && p.gate.ok) ? "done" : "warn")}
                            title="의도-일치 게이트: 골격 불변 · 명세 외 변경 0 · preflight">
                        {(p.gate && p.gate.ok) ? "의도 일치 PASS" : "의도 일치 FAIL"}
                      </span>
                      <b>{p.spec.change}</b>
                    </div>
                    <div className="bt-leaf-prop-ev">
                      근거: n={p.spec.evidence.n} · 중앙값 {_lfNumber(p.spec.evidence.median_pct)}%
                      (전체 대비 {_lfNumber(p.spec.evidence.vs_overall_median)}%p) ·
                      d={_lfNumber(p.spec.evidence.cohen_d)} · 승자분위 경계 {Number.isFinite(p.spec.evidence.win_quantile_bound)?p.spec.evidence.win_quantile_bound.toPrecision(3):"—"}
                    </div>
                    {(p.diff_preview || []).map((d, k) => (
                      <div key={k} className="bt-leaf-prop-diff">
                        <span className="del">− {d.old.trim()}</span>
                        <span className="add">＋ {d.new.trim()}</span>
                      </div>
                    ))}
                  </div>
                ))}
                <p className="v54-quant-note">이 화면은 메모리 미리보기만 제공합니다. 의도 일치 검사는 경제적 검증·채택 승인이 아닙니다.</p>
              </div>
            )}
            {feats.length > 0 && (
              <div className="bt-leaf-feats">
                <b className="mono">변별 상위 변수 (승·패 Cohen&apos;s d)</b>
                <div className="bt-leaf-feat-bars">
                  {feats.slice(0, 8).map(f => (
                    <div key={f.feature} className="bt-leaf-feat mono" title={`승 평균 ${_lfNumber(f.win_mean,4)} / 패 평균 ${_lfNumber(f.loss_mean,4)} · n=${f.n}`}>
                      <span className="k">{f.feature}</span>
                      <span className="bar"><i className={f.d >= 0 ? "pos" : "neg"}
                        style={{ width: Math.min(100, Math.abs(f.d) * 220) + "%" }}></i></span>
                      <span className="v">{Number.isFinite(f.d)&&f.d >= 0 ? "+" : ""}{_lfNumber(f.d,3)}</span>
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
