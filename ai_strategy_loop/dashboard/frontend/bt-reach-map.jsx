/* QSP10 페이지 22~24 — 도달 지도 패널 · 슬라이더 작업대 · 검증 현황판.
   원칙: 모든 수치에 표본수 병기 · 권위 배지(탐색용) 상시 · 외부 차트 라이브러리 금지(순수 SVG).
   전역 이름 충돌 방지를 위해 BtReachMap* 접두를 쓴다. */

const { useState: useState_rm, useEffect: useEffect_rm, useCallback: useCallback_rm } = React;

const BT_MAP_BARRIERS = [
  { tp: 1, sl: 1 }, { tp: 2, sl: 1 }, { tp: 3, sl: 1 },
  { tp: 2, sl: 2 }, { tp: 3, sl: 2 }, { tp: 5, sl: 3 },
];

function btMapPost(path, body) {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then((r) => r.json());
}

function BtReachMapBadge({ text }) {
  return <span className="badge warn" title="라벨 지도 위의 추정입니다. 공식 판정은 엔진 실측과 검증 사다리에서만 합니다.">{text || "탐색용 · 공식 아님"}</span>;
}

/* 표본수를 항상 함께 보여주는 수치 셀 — 표본 없는 밝은 칸은 함정이다. */
function BtReachMapStat({ label, value, sample, good, hint }) {
  const tone = good === undefined ? "" : (good ? "pos" : "neg");
  return (
    <div className="stat-card" title={hint || ""}>
      <div className="stat-label">{label}</div>
      <div className={"stat-value mono " + tone}>{value}</div>
      {sample !== undefined && <div className="stat-sub mono">표본 {Number(sample).toLocaleString()}건</div>}
    </div>
  );
}

/* 페이지 22 — 도달 지도 패널: 변수 분위별 배리어 성적(막대 + 표). */
function BtReachMapTerrain({ lane, rule }) {
  const [variable, setVariable] = useState_rm("체결강도");
  const [cells, setCells] = useState_rm([]);
  const [vars, setVars] = useState_rm([]);
  const [error, setError] = useState_rm("");

  useEffect_rm(() => {
    fetch(`/bt/map/universe?lane=${lane}`).then((r) => r.json()).then((d) => {
      if (d && d.available) setVars(d.variables || []);
      else setError((d && d.message) || "지도를 불러올 수 없습니다.");
    }).catch(() => setError("지도 요청에 실패했습니다."));
  }, [lane]);

  const load = useCallback_rm(() => {
    const q = `/bt/map/cube?lane=${lane}&variable=${encodeURIComponent(variable)}&tp_pct=${rule.tp}&sl_pct=${rule.sl}&buckets=20`;
    fetch(q).then((r) => r.json()).then((d) => {
      if (d && d.available) { setCells(d.cells || []); setError(""); }
      else setError((d && d.message) || "큐브 없음");
    }).catch(() => setError("큐브 요청 실패"));
  }, [lane, variable, rule.tp, rule.sl]);

  useEffect_rm(() => { if (variable) load(); }, [load, variable]);

  const maxAbs = cells.reduce((m, c) => Math.max(m, Math.abs(c.expectancy_pct || 0)), 0.01);
  return (
    <section className="panel">
      <header className="panel-head">
        <h3>페이지 22 · 도달 지도 <BtReachMapBadge /></h3>
        <select value={variable} onChange={(e) => setVariable(e.target.value)}
                title="분위별 배리어 성적을 볼 변수">
          {vars.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </header>
      {error && <p className="hint warn">{error}</p>}
      <div className="reach-bars">
        {cells.map((c) => {
          const w = Math.abs(c.expectancy_pct || 0) / maxAbs * 100;
          const pos = (c.expectancy_pct || 0) > 0;
          return (
            <div className="reach-bar-row" key={c.분위}
                 title={`분위 ${c.분위} · 구간 ${Number(c.하한).toFixed(3)}~${Number(c.상한).toFixed(3)} · 표본 ${Number(c.n).toLocaleString()}건 · 승률 ${(c.win_rate * 100).toFixed(1)}%`}>
              <span className="mono reach-bar-idx">{c.분위}</span>
              <span className="reach-bar-track">
                <span className={"reach-bar-fill " + (pos ? "pos" : "neg")} style={{ width: w + "%" }} />
              </span>
              <span className="mono reach-bar-val">{(c.expectancy_pct || 0).toFixed(3)}%</span>
              <span className="mono reach-bar-n">n={Number(c.n).toLocaleString()}</span>
            </div>
          );
        })}
      </div>
      {!cells.length && !error && <p className="hint">데이터를 불러오는 중입니다.</p>}
    </section>
  );
}

/* 페이지 23 — 슬라이더 작업대: 조건을 움직이면 즉시 기대값이 갱신된다(엔진 없음). */
function BtReachMapWorkbench({ lane, rule, onRule }) {
  const [status, setStatus] = useState_rm(null);
  const [clauses, setClauses] = useState_rm([]);
  const [result, setResult] = useState_rm(null);
  const [busy, setBusy] = useState_rm(false);
  const [name, setName] = useState_rm("QSP10_후보_1");
  const [saved, setSaved] = useState_rm("");

  useEffect_rm(() => {
    fetch(`/bt/map/universe?lane=${lane}`).then((r) => r.json()).then(setStatus)
      .catch(() => setStatus({ available: false, message: "상태 조회 실패" }));
  }, [lane]);

  const run = useCallback_rm(() => {
    setBusy(true);
    btMapPost("/bt/map/slider", {
      lane, tp_pct: rule.tp, sl_pct: rule.sl,
      clauses: clauses.filter((c) => c.variable && Number.isFinite(Number(c.value)))
        .map((c) => ({ variable: c.variable, operator: c.operator, value: Number(c.value) })),
    }).then(setResult).catch(() => setResult({ available: false, message: "질의 실패" }))
      .finally(() => setBusy(false));
  }, [lane, rule.tp, rule.sl, clauses]);

  useEffect_rm(() => { run(); }, [run]);

  const m = (result && result.metrics) || null;
  const over = m && m.win_rate > m.breakeven_win_rate;
  return (
    <section className="panel">
      <header className="panel-head">
        <h3>페이지 23 · 슬라이더 작업대 <BtReachMapBadge /></h3>
        <span className="mono hint">
          {status && status.available
            ? `집행 우주 ${Number(status.rows).toLocaleString()}행 · ${status.days}일 · ${status.universe_version}`
            : (status && status.message) || ""}
        </span>
      </header>

      <div className="row gap">
        <label>익절/손절
          <select value={`${rule.tp}/${rule.sl}`} title="배리어 규칙(사전 고정 그리드)"
                  onChange={(e) => { const [tp, sl] = e.target.value.split("/").map(Number); onRule({ tp, sl }); }}>
            {BT_MAP_BARRIERS.map((b) => <option key={`${b.tp}/${b.sl}`} value={`${b.tp}/${b.sl}`}>+{b.tp}% / -{b.sl}%</option>)}
          </select>
        </label>
        <button className="btn sm" onClick={() => setClauses(clauses.concat([{ variable: (status && status.variables && status.variables[0]) || "", operator: ">", value: 0 }]))}>
          조건 추가
        </button>
        <button className="btn sm ghost" onClick={() => setClauses([])}>초기화</button>
      </div>

      {clauses.map((c, i) => (
        <div className="row gap clause-row" key={i}>
          <select value={c.variable} onChange={(e) => { const n = clauses.slice(); n[i] = { ...c, variable: e.target.value }; setClauses(n); }}>
            {(status && status.variables || []).map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select value={c.operator} onChange={(e) => { const n = clauses.slice(); n[i] = { ...c, operator: e.target.value }; setClauses(n); }}>
            {[">", ">=", "<", "<="].map((o) => <option key={o} value={o}>{o}</option>)}
          </select>
          <input type="number" step="any" value={c.value} className="mono"
                 onChange={(e) => { const n = clauses.slice(); n[i] = { ...c, value: e.target.value }; setClauses(n); }} />
          <button className="btn sm ghost" onClick={() => setClauses(clauses.filter((_, j) => j !== i))}>삭제</button>
        </div>
      ))}

      {result && !result.available && <p className="hint warn">{result.message}</p>}
      {m && (
        <div className="stat-grid">
          <BtReachMapStat label="기대값(건당)" value={`${m.expectancy_pct.toFixed(4)}%`} sample={result.rows}
                          good={m.expectancy_pct > 0} hint="비용 차감 후 1건당 평균 수익률" />
          <BtReachMapStat label="승률(결정 건)" value={`${(m.win_rate * 100).toFixed(1)}%`} sample={m.win_n + m.loss_n}
                          good={over} hint="익절이 손절보다 먼저 닿은 비율" />
          <BtReachMapStat label="손익분기 승률" value={`${(m.breakeven_win_rate * 100).toFixed(1)}%`}
                          hint="이 익절/손절 조합에서 본전이 되는 승률" />
          <BtReachMapStat label="손익비" value={m.payoff.toFixed(3)} hint="이길 때 벌어들이는 크기 ÷ 질 때 잃는 크기" />
          <BtReachMapStat label="하루 기회" value={result.per_day.toFixed(1)} sample={result.rows} />
          <BtReachMapStat label="동시신호(평균/최대)"
                          value={`${result.cluster.mean_simultaneous.toFixed(2)} / ${result.cluster.max_simultaneous}`}
                          hint="같은 순간에 겹치는 신호 수 — 클수록 자본 한도 때문에 엔진 실측이 지도보다 나빠집니다" />
          <BtReachMapStat label="응답" value={`${result.elapsed_ms}ms`} hint="엔진 실행 없이 지도에서 계산했습니다" />
        </div>
      )}

      <div className="row gap">
        <input value={name} onChange={(e) => setName(e.target.value)} className="mono" />
        <button className="btn sm" disabled={busy || !m}
                onClick={() => btMapPost("/bt/map/candidate", { name, query: { lane, tp_pct: rule.tp, sl_pct: rule.sl, clauses: clauses.map((c) => ({ variable: c.variable, operator: c.operator, value: Number(c.value) })) }, metrics: m })
                  .then((d) => setSaved(d.status === "ok" ? `저장됨: ${d.saved}` : "저장 실패"))}>
          후보 저장(근거 포함)
        </button>
        {saved && <span className="hint">{saved}</span>}
      </div>
      <p className="hint">저장은 채택이 아닙니다. 엔진 실측과 검증 사다리를 통과해야 승인 요청이 됩니다.</p>
    </section>
  );
}

/* 페이지 24 — 검증 현황판: 저장된 후보의 계보와 다음 단계. */
function BtReachMapVerify() {
  const [rows, setRows] = useState_rm([]);
  useEffect_rm(() => {
    fetch("/bt/map/candidates").then((r) => r.json()).then((d) => setRows(d.candidates || [])).catch(() => setRows([]));
  }, []);
  return (
    <section className="panel">
      <header className="panel-head"><h3>페이지 24 · 검증 현황판</h3></header>
      {!rows.length && <p className="hint">저장된 후보가 없습니다. 페이지 23에서 조건을 만들고 저장하세요.</p>}
      {rows.length > 0 && (
        <table className="tbl">
          <thead><tr><th>후보</th><th>규칙</th><th>조건</th><th>기대값</th><th>다음 단계</th></tr></thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="mono">{r.name}</td>
                <td className="mono">+{r.query.tp_pct}% / -{r.query.sl_pct}%</td>
                <td className="mono">{(r.query.clauses || []).map((c) => `${c.variable}${c.operator}${c.value}`).join(" & ") || "(무조건)"}</td>
                <td className="mono">{r.metrics && r.metrics.expectancy_pct !== undefined ? Number(r.metrics.expectancy_pct).toFixed(4) + "%" : "-"}</td>
                <td>엔진 실측 → 전이율 기록 → 홀드아웃 → 사다리 6종 → 사람 승인</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/* 루트 — 세 페이지를 한 화면에 쌓는다(지도 → 조립 → 판정 동선). */
export function BtReachMapTab() {
  const [lane, setLane] = useState_rm("tick");
  const [rule, setRule] = useState_rm({ tp: 2, sl: 1 });
  return (
    <div className="reach-map-tab">
      <div className="row gap">
        <label>레인
          <select value={lane} onChange={(e) => setLane(e.target.value)}>
            <option value="tick">tick (시초 30분)</option>
            <option value="min">min (전일장)</option>
          </select>
        </label>
        <BtReachMapBadge text="지도=탐색 · 엔진=심판 · 소액 실전=최종 확인" />
      </div>
      <BtReachMapWorkbench lane={lane} rule={rule} onRule={setRule} />
      <BtReachMapTerrain lane={lane} rule={rule} />
      <BtReachMapVerify />
    </div>
  );
}
