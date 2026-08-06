/* 페이지 28 — 매도 축 종합. 지도 · 워크포워드 · 엔진을 한 줄에 놓는다.

   왜 필요한가: 같은 규칙이 세 곳에서 다른 숫자로 나온다. 자가 달라서 그런 것인데,
   화면이 없으면 세 숫자를 머릿속에서 섞어 읽게 된다 — "지도에서 좋았는데 엔진에서
   뒤집혔다"가 정확히 그 혼동에서 나왔다.

   관측 전용이다. 승인·실행 버튼이 없다.
   전역 충돌 방지로 BtEa* 접두를 쓴다. */

const { useState: useState_ea, useEffect: useEffect_ea, useCallback: useCallback_ea } = React;

function btEaGet(path) {
  return fetch(path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function btEaNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

function btEaSign(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "";
  return Number(value) >= 0 ? "pos" : "neg";
}

/* 정확도 배지 — 무엇을 판정 근거로 써도 되는지가 여기서 갈린다. */
function BtEaExactness({ value }) {
  const label = { exact: "정확", lower_bound: "하한", upper_bound: "상한(천장)" }[value] || value || "—";
  const tone = value === "upper_bound" ? "warn" : "";
  const hint = value === "upper_bound"
    ? "미래를 참조합니다 — 판정 근거가 아니라 천장으로만 읽습니다."
    : value === "lower_bound"
      ? "실현 가능한 최소값입니다 — 실제는 이보다 좋을 수 있습니다."
      : "경로를 그대로 시뮬레이션한 값입니다.";
  return <span className={"badge " + tone} title={hint}>{label}</span>;
}

/* 게이트 · 워크포워드 요약 — 표를 읽기 전에 '어떤 자로 쟀는지'부터 본다. */
function BtEaHeadline({ gate, walkforward, baseline }) {
  return (
    <div className="v4s-probe-grid">
      <div className="v4s-probe-card"><b>재현 게이트</b>
        <span className={"mono " + (gate && gate.verdict === "PASS" ? "pos" : "neg")}>
          {(gate && gate.verdict) || "미실행"}</span>
        <small className="v4s-en">챔피언 진입 {btEaNum(gate && gate.entry_positions)}건 위에서 평가</small></div>
      <div className="v4s-probe-card"><b>워크포워드</b>
        <span className={"mono " + (walkforward && walkforward.verdict === "PASS" ? "pos" : "neg")}>
          {(walkforward && walkforward.verdict) || "미실행"}</span>
        <small className="v4s-en">표본 밖 일평균 {btEaNum(walkforward && walkforward.mean_valid_day_mean_pct, 4)}%
          · 양수 {btEaNum(walkforward && walkforward.positive_folds)}폴드</small></div>
      <div className="v4s-probe-card"><b>탐색 편의</b>
        <span className="mono">{btEaNum(walkforward && walkforward.mean_train_valid_gap_pct, 4)}%p</span>
        <small className="v4s-en">후보 {btEaNum(walkforward && walkforward.candidates)}셀
          · 대규모 탐색은 {btEaNum(walkforward && walkforward.selection_bias_pct_large_scale, 4)}%p</small></div>
      <div className="v4s-probe-card"><b>엔진 기준선</b>
        <span className={"mono " + btEaSign(baseline && baseline.avg_profit_pct)}>
          {baseline ? btEaNum(baseline.avg_profit_pct, 4) + "%" : "미실측"}</span>
        <small className="v4s-en">{baseline
          ? `${baseline.rule} · 거래 ${btEaNum(baseline.trade_count)}`
          : "챔피언 원본 매도를 같은 런에서 재면 채워집니다"}</small></div>
    </div>
  );
}

/* 폴드 표 — 평균 하나로 뭉개면 편차가 사라진다. 폴드별로 보여준다. */
function BtEaFolds({ folds }) {
  if (!folds || !folds.length) return null;
  return (
    <section className="panel" style={{ marginTop: 12 }}>
      <div className="panel-hd"><div className="panel-hd-title">워크포워드 폴드</div>
        <small className="v4s-en">앞으로만 가는 분할 · 검증은 항상 학습 뒤</small></div>
      <div className="panel-bd">
        <p className="v4s-note">평균만 보면 편차가 사라집니다. <b>어느 폴드가 음수였는지</b>가
          그 규칙을 믿어도 되는지를 말해 줍니다.</p>
        <div className="table-wrap">
          <table className="tbl">
            <thead><tr>
              <th className="num">폴드</th><th>선택된 청산</th>
              <th className="num">학습일</th><th className="num">검증일</th>
              <th className="num">학습 일평균</th><th className="num">표본 밖 일평균</th>
              <th className="num">간극</th>
            </tr></thead>
            <tbody>
              {folds.map((fold) => (
                <tr key={fold.fold} className={Number(fold.valid_day_mean_pct) < 0 ? "row-warn" : ""}>
                  <td className="num mono">{fold.fold}</td>
                  <td className="mono">{fold.chosen}</td>
                  <td className="num mono">{btEaNum(fold.train_days)}</td>
                  <td className="num mono">{btEaNum(fold.valid_days)}</td>
                  <td className={"num mono " + btEaSign(fold.train_day_mean_pct)}>{btEaNum(fold.train_day_mean_pct, 4)}%</td>
                  <td className={"num mono " + btEaSign(fold.valid_day_mean_pct)}>{btEaNum(fold.valid_day_mean_pct, 4)}%</td>
                  <td className="num mono">{btEaNum(fold.gap_pct, 4)}%p</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export function BtExitAxisPanel({ outName }) {
  const [payload, setPayload] = useState_ea(null);
  const [error, setError] = useState_ea("");
  const [judgeableOnly, setJudgeableOnly] = useState_ea(true);
  const name = outName || "design_v4";

  const load = useCallback_ea(() => {
    btEaGet("/bt/exit-axis?out_name=" + encodeURIComponent(name))
      .then((d) => {
        setPayload(d);
        setError(d && d.available ? "" : "매도 축 기록이 아직 없습니다 — 재현 게이트를 한 번 돌리면 채워집니다.");
      })
      .catch(() => setError("매도 축 요청 실패"));
  }, [name]);

  useEffect_ea(() => { load(); }, [load]);

  const rows = ((payload && payload.rows) || []).filter((r) => !judgeableOnly || r.judgeable);
  const sources = (payload && payload.sources) || {};
  const engineMissing = payload && payload.available && !sources.engine;

  return (
    <div className="bt-exit-axis" aria-label="매도 축 종합 (페이지 28)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">매도 축 종합 <small className="v4s-en">페이지 28 · 지도 → 워크포워드 → 엔진</small></div>
          <span className="badge warn" title="진단용입니다. 공식 판정은 엔진 실측에서만 합니다.">diagnostic</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">같은 청산 규칙이 세 곳에서 다른 숫자로 나옵니다. <b>자가 다르기 때문</b>입니다 —
            지도는 건당 %, 워크포워드는 일평균 %, 엔진은 자본 경로까지 반영한 심판값입니다.
            여기서는 세 값을 <b>한 줄에</b> 놓고 나눗셈은 하지 않습니다.</p>

          <BtEaHeadline gate={payload && payload.gate}
                        walkforward={payload && payload.walkforward}
                        baseline={payload && payload.engine_baseline}/>

          <div className="v4s-log-controls">
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
            <label style={{ fontSize: 12 }}>
              <input type="checkbox" checked={judgeableOnly}
                     onChange={(e) => setJudgeableOnly(e.target.checked)}/>
              &nbsp;판정 가능한 셀만 (상한 숨김)
            </label>
            <span className="mono" style={{ fontSize: 11.5 }}>
              출처 — 게이트 {sources.reproduction_gate ? "✓" : "—"} ·
              워크포워드 {sources.walkforward ? "✓" : "—"} ·
              엔진 {sources.engine ? "✓" : "—"}
            </span>
          </div>

          {engineMissing && <p className="tp-error" role="alert">
            ⚠ 엔진 실측이 아직 없습니다 — 지도 수치만으로는 판정하지 않습니다.
            같은 규칙을 엔진에 올려야 전이율이 생깁니다.</p>}
          {error && <p className="v4s-note">{error}</p>}
          {payload && (payload.reading_rules || []).map((rule, i) => (
            <p key={i} className="v4s-note" style={{ fontSize: 11.5 }}>· {rule}</p>
          ))}
        </div>
      </div>

      {rows.length > 0 && (
        <section className="panel" style={{ marginTop: 12 }}>
          <div className="panel-hd"><div className="panel-hd-title">청산 규칙 전셀</div>
            <small className="v4s-en">좋은 셀만 고르지 않고 전부 싣습니다 — 고르면 그게 편의입니다</small></div>
          <div className="panel-bd">
            <div className="table-wrap">
              <table className="tbl">
                <thead><tr>
                  <th>청산 규칙</th><th>정확도</th>
                  <th className="num">지도 건당</th><th className="num">지도 일평균</th>
                  <th className="num">폴드 선택</th>
                  <th className="num">엔진 건당</th><th className="num">기준선 Δ</th>
                  <th className="num">전이율</th>
                  <th className="num">엔진 CAGR</th><th className="num">엔진 MDD</th>
                </tr></thead>
                <tbody>
                  {rows.map((row, index) => (
                    <tr key={row.rule || index}
                        className={row.exactness === "upper_bound" ? "row-warn" : ""}>
                      <td className="mono">{row.rule}
                        {row.reproduces_champion && <span className="badge" title="챔피언 성적을 부호·크기로 재현한 셀">재현</span>}</td>
                      <td><BtEaExactness value={row.exactness}/></td>
                      <td className={"num mono " + btEaSign(row.map_expectancy_pct)}>{btEaNum(row.map_expectancy_pct, 4)}%</td>
                      <td className={"num mono " + btEaSign(row.map_day_mean_pct)}>{btEaNum(row.map_day_mean_pct, 4)}%</td>
                      <td className="num mono">{row.walkforward_chosen_count || "—"}</td>
                      <td className={"num mono " + btEaSign(row.engine_avg_profit_pct)}>
                        {row.engine_avg_profit_pct === null || row.engine_avg_profit_pct === undefined
                          ? "미실측" : btEaNum(row.engine_avg_profit_pct, 4) + "%"}</td>
                      <td className={"num mono " + btEaSign(row.engine_delta_vs_baseline_pct)}>
                        {row.engine_delta_vs_baseline_pct === null || row.engine_delta_vs_baseline_pct === undefined
                          ? "—" : btEaNum(row.engine_delta_vs_baseline_pct, 4) + "%p"}</td>
                      <td className="num mono">{btEaNum(row.transfer_ratio, 3)}</td>
                      <td className="num mono">{btEaNum(row.engine_cagr, 2)}</td>
                      <td className="num mono">{btEaNum(row.engine_mdd_pct, 2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      <BtEaFolds folds={payload && payload.walkforward && payload.walkforward.folds}/>
    </div>
  );
}
