/* 페이지 29 — 상설화 현황 (마스터 웨이브 W5).

   연구가 캠페인 한 번으로 끝나면, 그 결과는 캠페인이 끝난 날부터 썩는다.
   상설화는 두 가지를 상시로 돌린다 — 새 거래일 백필, 보유 후보 재판정.

   이 화면은 **계획만** 보여준다. 실행 버튼이 없다. 특히 홀드아웃 결손은
   목록에 뜨더라도 잠긴 채다 — 자동으로 채우면 그날부터 홀드아웃이 아니다.

   전역 충돌 방지로 LoopSt* 접두를 쓴다. */

const { useState: useState_st, useEffect: useEffect_st, useCallback: useCallback_st } = React;

function loopStGet(path) {
  return fetch(path, { credentials: "same-origin", cache: "no-store" }).then((r) => r.json());
}

function loopStNum(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  return Number(value).toLocaleString();
}

function loopStToday() {
  const now = new Date();
  return now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
}

/* 날짜 목록 요약 — 200일을 다 뿌리면 화면이 아니라 로그가 된다. */
function LoopStDays({ days, limit }) {
  const list = days || [];
  if (!list.length) return <span className="mono">없음</span>;
  const cap = limit || 8;
  const head = list.slice(0, cap).join(", ");
  return <span className="mono">{head}{list.length > cap ? ` … 외 ${list.length - cap}일` : ""}</span>;
}

function LoopStBackfill({ backfill }) {
  if (!backfill) return <p className="v4s-note">백필 계획을 읽지 못했습니다.</p>;
  const locked = (backfill.holdout_missing || []).length;
  return (
    <>
      <div className="v4s-probe-grid">
        <div className="v4s-probe-card"><b>보유 라벨</b>
          <span className="mono">{loopStNum(backfill.label_day_count)}일</span>
          <small className="v4s-en">{backfill.out_name} · {backfill.lane} 레인</small></div>
        <div className="v4s-probe-card"><b>결손</b>
          <span className={"mono " + (backfill.missing_total ? "neg" : "pos")}>
            {loopStNum(backfill.missing_total)}일</span>
          <small className="v4s-en">DB 에는 있는데 라벨이 없는 날</small></div>
        <div className="v4s-probe-card"><b>이번 배치</b>
          <span className="mono">{loopStNum((backfill.next_batch || []).length)}일</span>
          <small className="v4s-en">{backfill.next_batch_range
            ? `${backfill.next_batch_range[0]} ~ ${backfill.next_batch_range[1]}`
            : "만들 날 없음"}</small></div>
        <div className="v4s-probe-card"><b>다음 회차로</b>
          <span className="mono">{loopStNum(backfill.deferred_count)}일</span>
          <small className="v4s-en">배치 상한을 넘어 미뤘습니다 — 잘라 버린 것이 아닙니다</small></div>
      </div>

      <div className="table-wrap" style={{ marginTop: 10 }}>
        <table className="tbl">
          <tbody>
            <tr><th style={{ width: 160 }}>설계 구간 결손</th>
              <td><LoopStDays days={backfill.design_missing}/></td></tr>
            <tr className={locked ? "row-warn" : ""}>
              <th>홀드아웃 결손 🔒</th>
              <td><LoopStDays days={backfill.holdout_missing}/>
                {locked > 0 && <div className="v4s-note" style={{ marginTop: 4 }}>
                  {backfill.holdout_start} 이후는 <b>자동으로 만들지 않습니다</b>. {backfill.note}</div>}</td></tr>
          </tbody>
        </table>
      </div>
    </>
  );
}

function LoopStRevalidation({ revalidation }) {
  if (!revalidation) {
    return <p className="v4s-note">오늘 날짜를 기준으로 재검증 계획을 만듭니다 — 새로고침하면 채워집니다.</p>;
  }
  const due = revalidation.due || [];
  return (
    <>
      <p className="v4s-note">재판정은 <b>표본을 늘리는 일</b>이지 성적을 고치는 일이 아닙니다.
        결과가 나빠지면 그것이 새 사실입니다.</p>
      <div className="v4s-log-controls">
        <span className="mono" style={{ fontSize: 11.5 }}>
          재판정 대상 {loopStNum(revalidation.due_count)} ·
          아직 유효 {loopStNum(revalidation.fresh_count)} ·
          기준 {loopStNum(revalidation.max_age_days)}일 ·
          오늘 {revalidation.today}</span>
      </div>
      {due.length === 0
        ? <p className="v4s-note">지금 다시 판정할 후보가 없습니다.</p>
        : <div className="table-wrap">
            <table className="tbl">
              <thead><tr><th>후보</th><th>마지막 판정</th><th className="num">경과일</th><th>사유</th></tr></thead>
              <tbody>
                {due.map((row, index) => (
                  <tr key={row.name || index} className={row.reason === "never_validated" ? "row-warn" : ""}>
                    <td className="mono">{row.name || "—"}</td>
                    <td className="mono">{row.last_verdict_day || "—"}</td>
                    <td className="num mono">{loopStNum(row.age_days)}</td>
                    <td>{row.reason === "never_validated"
                      ? <span className="badge warn" title="한 번도 표본 밖에서 판정한 적이 없습니다">판정 이력 없음</span>
                      : <span className="badge">기한 경과</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>}
    </>
  );
}

export function LoopStandingPanel({ outName, lane }) {
  const [payload, setPayload] = useState_st(null);
  const [error, setError] = useState_st("");
  const [maxAge, setMaxAge] = useState_st(30);
  const name = outName || "design_v4";
  const laneName = lane || "tick";

  const load = useCallback_st(() => {
    const query = `?out_name=${encodeURIComponent(name)}&lane=${encodeURIComponent(laneName)}`
      + `&today=${loopStToday()}&max_age_days=${maxAge}`;
    loopStGet("/loop/standing" + query)
      .then((d) => { setPayload(d); setError(d && d.available ? "" : "상설화 현황을 읽지 못했습니다."); })
      .catch(() => setError("상설화 요청 실패"));
  }, [name, laneName, maxAge]);

  useEffect_st(() => { load(); }, [load]);

  return (
    <div className="loop-standing" aria-label="상설화 현황 (페이지 29)">
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title">상설화 현황 <small className="v4s-en">페이지 29 · 백필 · 재검증</small></div>
          <span className="badge warn" title="계획만 보여줍니다. 실행은 러너가, 채택은 사람이 합니다.">계획 전용</span>
        </div>
        <div className="panel-bd">
          <p className="v4s-note">연구는 한 번의 캠페인으로 끝나지 않습니다. 새 거래일이 들어오면 라벨도
            따라와야 하고, 보유 후보는 <b>시간이 준 새 표본</b>으로 다시 판정해야 합니다.</p>
          <div className="v4s-log-controls">
            <label>재판정 기준(일)
              <input className="mono" value={maxAge} inputMode="numeric" style={{ width: 70 }}
                     onChange={(e) => setMaxAge(Number(e.target.value.replace(/\D/g, "")) || 0)}
                     aria-label="재판정 기준 일수"/></label>
            <button className="btn ghost sm" type="button" onClick={load}>새로고침</button>
            <span className="mono" style={{ fontSize: 11.5 }}>
              후보 {loopStNum(payload && payload.candidate_count)}건</span>
          </div>
          {error && <p className="tp-error" role="alert">{error}</p>}
        </div>
      </div>

      <section className="panel" style={{ marginTop: 12 }}>
        <div className="panel-hd"><div className="panel-hd-title">① 백필 — 새 거래일을 라벨로</div>
          <small className="v4s-en">멱등 · 홀드아웃 경계에서 멈춤</small></div>
        <div className="panel-bd"><LoopStBackfill backfill={payload && payload.backfill}/></div>
      </section>

      <section className="panel" style={{ marginTop: 12 }}>
        <div className="panel-hd"><div className="panel-hd-title">② 상설 재검증 — 시간을 표본으로</div>
          <small className="v4s-en">오래된 판정 · 판정 이력 없는 후보</small></div>
        <div className="panel-bd"><LoopStRevalidation revalidation={payload && payload.revalidation}/></div>
      </section>
    </div>
  );
}
