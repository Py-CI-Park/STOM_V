/* 페이지 33 — 조건식 비교 뷰어.

   원장(30)이 "어느 후보가 나은가", 계기판(31)이 "믿을 만한가",
   응답면(32)이 "표본 밖에서 살아남는가"를 답한다. 여기는 그 앞의 질문이다:
   **두 조건식이 정확히 무엇이 다른가.**

   두 층으로 본다. 절 층만 보면 임계 변경을 놓치고, 줄 층만 보면 잡음에 묻힌다.

   관측 전용이다. 전역 충돌 방지로 LoopCd* 접두를 쓴다. */

const { useState: useState_cd, useEffect: useEffect_cd, useCallback: useCallback_cd } = React;

function loopCdGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

const LOOP_CD_STATE = {
  active: { label: "살아 있음", tone: "" },
  commented: { label: "주석 처리", tone: "warn" },
  absent: { label: "없음", tone: "" },
};

/* diff 한 줄. 색만으로 읽히면 안 되므로 왼쪽에 기호를 둔다(접근성). */
function LoopCdRow({ row }) {
  const style = {
    del: { mark: "−", bg: "rgba(200,60,60,.13)" },
    add: { mark: "+", bg: "rgba(46,158,91,.13)" },
    same: { mark: " ", bg: "transparent" },
    gap: { mark: "⋯", bg: "transparent" },
    identical: { mark: " ", bg: "transparent" },
  }[row.op] || { mark: " ", bg: "transparent" };
  const muted = row.op === "gap" || row.op === "identical";
  return (
    <tr style={{ background: style.bg }}>
      <td className="num mono" style={{ opacity: .55, width: 44 }}>{row.left_no || ""}</td>
      <td className="num mono" style={{ opacity: .55, width: 44 }}>{row.right_no || ""}</td>
      <td className="mono" style={{ whiteSpace: "pre", fontSize: 12.5, opacity: muted ? .6 : 1 }}>
        <span aria-hidden="true" style={{ opacity: .7 }}>{style.mark} </span>{row.text}
      </td>
    </tr>
  );
}

export function LoopConditionDiffPanel({ baseUrl, reviewContext }) {
  const [kind, setKind] = useState_cd("buy");
  const [names, setNames] = useState_cd([]);
  const [left, setLeft] = useState_cd("");
  const [right, setRight] = useState_cd("");
  const [payload, setPayload] = useState_cd(null);
  const [error, setError] = useState_cd("");

  useEffect_cd(() => {
    loopCdGet(baseUrl, "/loop/condition-names?kind=" + kind)
      .then((d) => {
        const list = (d && d.names) || [];
        setNames(list);
        const baseline = reviewContext && reviewContext.baseline_id;
        const candidate = reviewContext && reviewContext.candidate_id;
        setLeft(baseline && list.includes(baseline) ? baseline : (list[0] || ""));
        setRight(candidate && list.includes(candidate) ? candidate : (list[1] || list[0] || ""));
        setPayload(null);
      })
      .catch(() => setError("조건식 목록 요청 실패"));
  }, [baseUrl, kind, reviewContext]);

  const run = useCallback_cd(() => {
    if (!left || !right) return;
    loopCdGet(baseUrl, `/loop/condition-diff?kind=${kind}&left=${encodeURIComponent(left)}`
              + `&right=${encodeURIComponent(right)}`)
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : (d && d.reason) || "비교할 수 없습니다.");
      })
      .catch(() => setError("비교 요청 실패"));
  }, [baseUrl, kind, left, right]);

  const delta = (payload && payload.clause_delta) || [];
  const diff = (payload && payload.diff) || [];

  return (
    <div className="loop-condition-diff" aria-label="조건식 비교 뷰어 (페이지 33)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">조건식 비교 <small className="v4s-en">페이지 33 · 절 단위 diff</small></div>
          <span className="badge" title="조건식을 실행하지 않습니다. 텍스트만 읽습니다.">read-only</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">“조기 청산 <b>한 줄만</b> 얹었다”가 정말 한 줄인지,
            눈이 아니라 <b>코드</b>로 확인합니다.</p>
          <div className="v4s-log-controls" style={{ flexWrap: "wrap", gap: 8 }}>
            <select value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="buy">매수식</option>
              <option value="sell">매도식</option>
            </select>
            <select value={left} onChange={(e) => setLeft(e.target.value)} style={{ maxWidth: 260 }}>
              {names.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
            <span aria-hidden="true">→</span>
            <select value={right} onChange={(e) => setRight(e.target.value)} style={{ maxWidth: 260 }}>
              {names.map((n) => <option key={n} value={n}>{n}</option>)}
            </select>
            <button className="btn sm" type="button" onClick={run}>비교</button>
          </div>
          {error && <p className="v4s-note">{error}</p>}
          {payload && payload.available && (
            <div className="v4s-probe-grid" style={{ marginTop: 10 }}>
              <div className="v4s-probe-card"><b>바뀐 줄</b>
                <span className="mono">{payload.changed_lines}줄</span>
                <small className="v4s-en">{payload.left.code_lines} → {payload.right.code_lines} 코드줄</small></div>
              <div className="v4s-probe-card"><b>절 변화</b>
                <span className="mono">{delta.length}개</span></div>
              <div className="v4s-probe-card"><b>한 변수 실험</b>
                <span className={"mono " + (payload.comment_only ? "pos" : "")}>
                  {payload.identical ? "동일" : (payload.comment_only ? "주석 처리뿐" : "코드 변경 포함")}</span>
                <small className="v4s-en">실행 코드가 줄기만 했나</small></div>
            </div>
          )}
          {payload && (payload.reading_rules || []).map((rule, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {rule}</p>
          ))}
        </div>
      </div>

      {delta.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">절 층 — 달라진 절만</div></div>
          <div className="panel-bd"><div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>절</th><th>설명</th><th>왼쪽</th><th>오른쪽</th></tr></thead>
              <tbody>
                {delta.map((d) => (
                  <tr key={d.clause}>
                    <td className="mono">{d.clause}</td>
                    <td>{d.label}</td>
                    <td><span className={"badge " + (LOOP_CD_STATE[d.left] || {}).tone}>
                      {(LOOP_CD_STATE[d.left] || {}).label || d.left}</span></td>
                    <td><span className={"badge " + (LOOP_CD_STATE[d.right] || {}).tone}>
                      {(LOOP_CD_STATE[d.right] || {}).label || d.right}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div></div>
        </section>
      )}

      {diff.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">줄 층</div>
            <small className="v4s-en">− 왼쪽에만 · + 오른쪽에만 · ⋯ 생략</small></div>
          <div className="panel-bd"><div className="table-wrap">
            <table className="tbl">
              <thead><tr>
                <th className="num" style={{ width: 44 }}>L</th>
                <th className="num" style={{ width: 44 }}>R</th>
                <th>{payload.left.name} → {payload.right.name}</th>
              </tr></thead>
              <tbody>{diff.map((row, i) => <LoopCdRow key={i} row={row}/>)}</tbody>
            </table>
          </div></div>
        </section>
      )}
    </div>
  );
}
