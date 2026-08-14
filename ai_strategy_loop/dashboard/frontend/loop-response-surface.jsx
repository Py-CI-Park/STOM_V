/* 페이지 32 — 국소 파라미터 민감도.

   같은 연구 표본에서 이웃 격자점의 성적이 얼마나 변하는지 읽는다.
   이 표면만으로 표본 밖 성과나 채택 여부를 말하지 않는다.

   관측 전용이다. 전역 충돌 방지로 LoopRs* 접두를 쓴다. */

const { useState: useState_rs, useEffect: useEffect_rs, useCallback: useCallback_rs } = React;

function loopRsGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopRsNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

/* 판정별 배경 — 색만으로 읽히면 안 되므로 칸 안에 기호도 함께 둔다(접근성). */
const LOOP_RS_STYLE = {
  "고원": { bg: "rgba(46,158,91,.20)", mark: "O" },
  "경사": { bg: "rgba(201,138,27,.20)", mark: "/" },
  "절벽": { bg: "rgba(200,60,60,.24)", mark: "!" },
  "음수": { bg: "rgba(127,127,127,.16)", mark: "−" },
  "가장자리": { bg: "transparent", mark: "·" },
  "빈칸": { bg: "transparent", mark: "" },
};

function LoopRsSummary({ payload }) {
  const counts = (payload && payload.verdict_counts) || {};
  const best = payload && payload.best;
  const flat = payload && payload.best_plateau;
  return (
    <div className="v4s-probe-grid">
      {["고원", "경사", "절벽", "음수", "가장자리"].map((key) => (
        <div className="v4s-probe-card" key={key}><b>{key}</b>
          <span className={"mono " + (key === "절벽" && counts[key] ? "neg" : "")}>
            {loopRsNum(counts[key] || 0)}셀</span></div>
      ))}
      <div className="v4s-probe-card"><b>최고 셀</b>
        <span className="mono">{best ? best.rule : "—"}</span>
        <small className="v4s-en">{best ? `${loopRsNum(best[payload.metric], 4)}% · ${best.verdict}` : ""}</small></div>
      <div className="v4s-probe-card"><b>고원 최고</b>
        <span className={"mono " + (flat ? "pos" : "neg")}>{flat ? flat.rule : "없음"}</span>
        <small className="v4s-en">{flat
          ? `이웃최소 ${loopRsNum(flat.neighbour_min, 4)}% (유지 ${loopRsNum(flat.retention * 100, 0)}%)`
          : "국소 비교값이 없다"}</small></div>
      <div className="v4s-probe-card"><b>국소 격차</b>
        <span className={"mono " + ((payload && payload.overfit_gap) ? "neg" : "pos")}>
          {payload && payload.overfit_gap ? loopRsNum(payload.overfit_gap, 4) + "%p" : "없음"}</span>
        <small className="v4s-en">최고 셀과 고원 셀의 차이</small></div>
    </div>
  );
}

function LoopRsProvenance({ payload }) {
  if (!payload) return null;
  if (!payload.provenance_available) {
    return <p className="v4s-note">출처 정보: {payload.provenance_error || "없음"}</p>;
  }
  const provenance = payload.provenance || {};
  const fields = ["study", "study_id", "artifact", "artifact_id", "source", "source_id",
    "split", "window", "hash", "created_at"].filter((key) => provenance[key] !== undefined && provenance[key] !== null);
  if (!fields.length) return null;
  return <p className="v4s-note">출처 정보: {fields.map((key) => (
    <span key={key} className="mono" style={{ marginRight: 8 }}>{key} {
      typeof provenance[key] === "object" ? JSON.stringify(provenance[key]) : String(provenance[key])
    }</span>
  ))}</p>;
}

export function LoopResponseSurfacePanel({ baseUrl, reviewContext }) {
  const [payload, setPayload] = useState_rs(null);
  const [error, setError] = useState_rs("");

  const load = useCallback_rs(() => {
    loopRsGet(baseUrl, "/loop/response-surface")
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : (d && d.reason) || "응답면이 없습니다.");
      })
      .catch(() => setError("응답면 요청 실패"));
  }, [baseUrl]);

  useEffect_rs(() => { load(); }, [load]);

  const arms = (payload && payload.arms) || [];
  const gives = (payload && payload.gives) || [];
  const metric = (payload && payload.metric) || "expectancy_pct";
  const byAxis = {};
  ((payload && payload.cells) || []).forEach((c) => { byAxis[`${c.arm}|${c.give}`] = c; });

  return (
    <div className="loop-response-surface" aria-label="국소 파라미터 민감도 (페이지 32)">
      {reviewContext && reviewContext.candidate_id && <p className="v4s-note">
        검토 후보: <span className="mono">{reviewContext.candidate_id}</span>
      </p>}
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">파라미터 응답면 <small className="v4s-en">페이지 32 · 국소 민감도</small></div>
          <span className="badge" title="같은 연구 표본에서 계산한 국소 격자 지도입니다.">map</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">이웃한 파라미터를 조금 바꿨을 때 성적이 얼마나 변하는지 봅니다.
            <b> 칼날 능선</b>은 국소 변화에 민감하고, <b>평평한 곳</b>은 같은 표본에서 변화가 작습니다.</p>
          <LoopRsSummary payload={payload}/>
          <div className="v4s-log-controls">
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
            {payload && payload.source && <small className="v4s-en">{payload.out_name} · {payload.source}</small>}
          </div>
          <LoopRsProvenance payload={payload}/>
          {error && <p className="v4s-note">{error}</p>}
          {payload && payload.oos_verdict && payload.recommendation &&
            <p className="v4s-note"><b>OOS 판정</b> — {payload.oos_verdict} · {payload.recommendation}</p>}
          {payload && (payload.reading_rules || []).map((rule, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {rule}</p>
          ))}
        </div>
      </div>

      {arms.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">무장 × 되돌림 격자</div>
            <small className="v4s-en">진입 {loopRsNum(payload.entry_positions)}건 · 이웃 유지 기준 {loopRsNum(payload.retain * 100, 0)}%</small></div>
          <div className="panel-bd">
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr>
                  <th>무장 \ 되돌림</th>
                  {gives.map((g) => <th className="num" key={g}>{g}%p</th>)}
                </tr></thead>
                <tbody>
                  {arms.map((arm) => (
                    <tr key={arm}>
                      <th scope="row" className="mono">+{arm}%</th>
                      {gives.map((give) => {
                        const cell = byAxis[`${arm}|${give}`];
                        if (!cell) return <td className="num mono" key={give}>—</td>;
                        const style = LOOP_RS_STYLE[cell.verdict] || LOOP_RS_STYLE["빈칸"];
                        return (
                          <td className="num mono" key={give}
                              style={{ background: style.bg }}
                              title={`${cell.verdict_label} · 이웃 ${cell.neighbours}칸 · 최소 ${loopRsNum(cell.neighbour_min, 4)}%`}>
                            {loopRsNum(cell[metric], 3)}<span aria-hidden="true"> {style.mark}</span>
                            <span className="sr-only">{cell.verdict}</span>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="v4s-note" style={{ fontSize: 11.5 }}>
              O 고원 · / 경사 · ! 절벽 · − 음수 · · 가장자리 &nbsp;|&nbsp;
              값은 {metric === "expectancy_pct" ? "건당 기대값" : "일평균"}(%)입니다.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
