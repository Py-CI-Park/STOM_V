/* 페이지 26 — 자율 루프 관제 (마스터 웨이브 W2).
   사람 승인 없이 도는 루프의 관측면: 세대별 가설 → 판정 → 실측 델타 → 예산 잔량.

   왜 필요한가: 자율 루프가 무한히 수정하면 그 자체가 선택 편의를 키운다(QSP13
   실측 0.6225%p). 예산(아이디어당 15회)과 가정 적중률을 화면에 상시 노출해
   "학습하고 있는가 / 그냥 헤매는가"를 구분한다.

   권한 계약: 관측 전용 — 제어 버튼 없음. 전역 충돌 방지로 Loop* 접두를 쓴다. */

const { useState: useState_la, useEffect: useEffect_la, useCallback: useCallback_la } = React;

function loopGet(baseUrl, path) {
  return fetch((baseUrl || "") + path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopNum(value, digits) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits === undefined ? 0 : digits,
    maximumFractionDigits: digits === undefined ? 0 : digits,
  });
}

const LOOP_VERDICT_LABEL = {
  accepted: ["가정 적중", "pos"],
  rejected: ["가정 빗나감", "neg"],
  inconclusive: ["판정 불가", ""],
  untested: ["미검증", ""],
};

/* 예산 막대 — 초과하면 붉게. 무한 수정이 편의를 키우는 것을 눈으로 막는다. */
function LoopBudgetBar({ used, budget, over }) {
  const ratio = Math.min(1, budget ? used / budget : 0);
  return (
    <div className="loop-budget" title={`수정 ${used}/${budget}회`}>
      <div className="loop-budget-track">
        <i className={"loop-budget-fill" + (over ? " over" : "")} style={{ width: `${Math.round(ratio * 100)}%` }}/>
      </div>
      <span className={"mono" + (over ? " neg" : "")}>{used} / {budget}{over ? " · 예산 초과" : ""}</span>
    </div>
  );
}

/* 결론 칸 — 편의 차감 후 성적을 원값과 나란히 보여준다. */
function LoopBudgetSummary({ budget }) {
  if (!budget || !budget.available) {
    return <p className="v4s-note">아직 자율 루프 기록이 없습니다. 루프를 한 번 돌리면 여기에 채워집니다.</p>;
  }
  const raw = budget.design_per_trade_pct;
  const adjusted = budget.bias_adjusted_pct;
  return (
    <>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>수정 예산</b>
          <LoopBudgetBar used={budget.revisions_used} budget={budget.revision_budget} over={budget.over_budget}/></div>
        <div className="v4s-probe-card"><b>설계 구간 건당</b>
          <span className="mono">{raw === null || raw === undefined ? "—" : `${loopNum(raw, 4)}%`}</span></div>
        <div className="v4s-probe-card"><b>편의 차감 후</b>
          <span className={"mono " + (adjusted > 0 ? "pos" : "neg")}>
            {adjusted === null || adjusted === undefined ? "—" : `${loopNum(adjusted, 4)}%`}</span></div>
        <div className="v4s-probe-card"><b>선택 편의</b>
          <span className="mono">−{loopNum(budget.selection_bias_pct, 4)}%p</span></div>
      </div>
      <p className="v4s-note">{budget.note}</p>
    </>
  );
}

/* 가정 판정 분포 — 적중률이 0에 가까우면 부검→가정 연결이 헛돌고 있다는 뜻. */
function LoopVerdictSummary({ verdicts, hitRate }) {
  const entries = Object.entries(verdicts || {});
  if (entries.length === 0) return null;
  return (
    <div className="v4s-probe-grid">
      {entries.map(([key, count]) => {
        const [label, tone] = LOOP_VERDICT_LABEL[key] || [key, ""];
        return <div className="v4s-probe-card" key={key}><b>{label}</b>
          <span className={"mono " + tone}>{loopNum(count)}건</span></div>;
      })}
      <div className="v4s-probe-card"><b>가정 적중률</b>
        <span className="mono">{hitRate === null || hitRate === undefined ? "—" : `${loopNum(hitRate * 100, 1)}%`}</span></div>
    </div>
  );
}

/* 세대 타임라인 — 무엇을 바꿨고(diff) 무엇이 움직였나(델타). */
function LoopGenerationTable({ generations }) {
  if (!generations || generations.length === 0) {
    return <p className="v4s-note">세대 기록이 없습니다.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="tbl">
        <thead>
          <tr>
            <th className="num">세대</th><th>변경 내용</th><th className="num">거래</th>
            <th className="num">수익</th><th className="num">MDD</th>
            <th className="num">Δ수익</th><th className="num">Δ점수</th>
            <th>게이트</th><th>가정</th>
          </tr>
        </thead>
        <tbody>
          {generations.map((row) => (
            <tr key={`${row.run_id}-${row.gen_no}`}>
              <td className="num mono">{row.gen_no}</td>
              <td className="mono" title={row.diff_from_parent || ""}>
                {(row.diff_from_parent || "—").slice(0, 60)}</td>
              <td className="num mono">{loopNum(row.trade_count)}</td>
              <td className={"num mono " + (Number(row.profit) >= 0 ? "pos" : "neg")}>{loopNum(row.profit)}</td>
              <td className="num mono">{loopNum(row.mdd, 2)}</td>
              <td className={"num mono " + (Number(row.d_profit) >= 0 ? "pos" : "neg")}>{loopNum(row.d_profit)}</td>
              <td className={"num mono " + (Number(row.d_graded) >= 0 ? "pos" : "neg")}>{loopNum(row.d_graded, 4)}</td>
              <td>{row.gate_passed
                ? <span className="badge ok">통과</span>
                : <span className="badge warn" title={row.reason || ""}>미통과</span>}</td>
              <td>
                {(row.hypotheses || []).length === 0 ? <span className="mono">—</span> : (row.hypotheses || []).map((h, i) => {
                  const [label, tone] = LOOP_VERDICT_LABEL[h.verdict] || [h.verdict, ""];
                  return <div key={i} className={"mono " + tone} title={`${h.text || ""} · 근거 ${h.basis || "—"}`}>
                    {label} · {h.target_metric}{h.expected_direction > 0 ? "↑" : "↓"}</div>;
                })}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function LoopAutonomyPanel({ baseUrl }) {
  const [runs, setRuns] = useState_la([]);
  const [runId, setRunId] = useState_la("");
  const [generations, setGenerations] = useState_la([]);
  const [verdicts, setVerdicts] = useState_la(null);
  const [hitRate, setHitRate] = useState_la(null);
  const [budget, setBudget] = useState_la(null);
  const [error, setError] = useState_la("");

  useEffect_la(() => {
    loopGet(baseUrl, "/loop/autonomy/runs?limit=20")
      .then((d) => {
        if (d && d.available) { setRuns(d.runs || []); if (!runId && d.runs.length) setRunId(d.runs[0].run_id); }
        else setError("자율 루프 기록이 아직 없습니다.");
      })
      .catch(() => setError("run 목록 요청 실패"));
  }, [baseUrl]);

  const load = useCallback_la(() => {
    if (!runId) return;
    loopGet(baseUrl, `/loop/autonomy/generations?run_id=${encodeURIComponent(runId)}&limit=60`)
      .then((d) => { setGenerations(d.generations || []); setVerdicts(d.hypothesis_verdicts || null); setHitRate(d.hypothesis_hit_rate); })
      .catch(() => setError("세대 조회 실패"));
    loopGet(baseUrl, `/loop/autonomy/budget?run_id=${encodeURIComponent(runId)}`)
      .then(setBudget)
      .catch(() => setError("예산 조회 실패"));
  }, [baseUrl, runId]);

  useEffect_la(() => { load(); }, [runId, load]);

  return (
    <div className="loop-autonomy" aria-label="자율 루프 관제 (페이지 26)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">자율 루프 관제 <small className="v4s-en">페이지 26 · 관측 전용</small></div>
          <span className="badge warn" title="이 화면에는 제어 기능이 없습니다. 루프는 사람 승인 없이 돌고, 사람 게이트는 실전 투입 1곳입니다.">observation_only</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">자율 루프가 <b>무엇을 가정했고</b>, <b>그 가정이 맞았는지</b>, <b>수정 예산을 얼마나 썼는지</b>를 봅니다.
            무한 수정은 그 자체로 선택 편의를 키우므로 아이디어당 예산을 둡니다.</p>
          <div className="v4s-log-controls">
            <label>연구 run
              <select value={runId} onChange={(e) => setRunId(e.target.value)}>
                {runs.map((r) => <option key={r.run_id} value={r.run_id}>
                  {r.run_id} · {r.generations}세대{r.over_budget ? " · 예산 초과" : ""}</option>)}
              </select>
            </label>
            <button className="btn ghost sm" type="button" onClick={load} disabled={!runId}>새로고침</button>
          </div>
          {error && <p className="tp-error" role="alert">{error}</p>}
          <LoopBudgetSummary budget={budget}/>
        </div>
      </div>

      <section className="panel" style={{ marginTop: 12 }}>
        <div className="panel-hd"><div className="panel-hd-title">가정 판정 분포</div>
          <small className="v4s-en">부검 → 가정 → 개선이 학습하고 있는가</small></div>
        <div className="panel-bd"><LoopVerdictSummary verdicts={verdicts} hitRate={hitRate}/></div>
      </section>

      <section className="panel" style={{ marginTop: 12 }}>
        <div className="panel-hd"><div className="panel-hd-title">세대 타임라인</div>
          <small className="v4s-en">변경 1건 = 가정 1건</small></div>
        <div className="panel-bd"><LoopGenerationTable generations={generations}/></div>
      </section>
    </div>
  );
}
