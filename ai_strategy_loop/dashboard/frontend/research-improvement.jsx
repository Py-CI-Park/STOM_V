/* research-improvement.jsx — "연구가 실제로 좋아지고 있나"를 한 장으로 답하는 카드.
 *
 *   Live 탭은 지금까지 "현재 세대가 어떤 상태인가"만 보여줬다. 사용자가 알고 싶은 것은
 *   그게 아니라 "세대를 거듭하면서 수익금·수익률·연평균 수익률이 실제로 올라가고 있나"다.
 *   이 카드는 state.generations(이미 배포된 세대 행)만으로 그 질문에 답한다 — 새 백테스트를
 *   돌리지 않고, 발행되지 않은 값을 만들어내지도 않는다.
 *
 *   연평균 수익률은 loop_runs 가 직접 발행하지 않는다. 기간(연 수)이 확인될 때에만
 *   누적 수익률에서 기하평균으로 환산해 보여주고, 반드시 '파생값' 으로 표시한다.
 */
const { useMemo: useMemo_ri, useEffect: useEffect_ri, useState: useState_ri } = React;

function _riNum(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

// 누적 수익률(%) + 연 수 → 연평균(기하) 수익률(%). 원금 전손(-100% 이하)이면 계산 불가.
function riAnnualizedPct(totalPct, years) {
  const total = _riNum(totalPct);
  const y = _riNum(years);
  if (total == null || y == null || y <= 0) return null;
  const growth = 1 + total / 100;
  if (growth <= 0) return null;
  return (Math.pow(growth, 1 / y) - 1) * 100;
}

// 세대 행 → {gen, profit, pct, best*} 시계열. best* 는 지금까지의 최고치(러닝 맥스)다.
function riImprovementSeries(generations) {
  const rows = (Array.isArray(generations) ? generations : [])
    .filter(g => g && _riNum(g.gen_no) != null)
    .slice()
    .sort((a, b) => Number(a.gen_no) - Number(b.gen_no));
  let bestProfit = null;
  let bestPct = null;
  return rows.map(g => {
    const profit = _riNum(g.profit);
    const pct = _riNum(g.total_profit_pct);
    if (profit != null && (bestProfit == null || profit > bestProfit)) bestProfit = profit;
    if (pct != null && (bestPct == null || pct > bestPct)) bestPct = pct;
    return {
      gen: Number(g.gen_no),
      profit, pct,
      bestProfit, bestPct,
      isRecord: profit != null && profit === bestProfit,
      gatePassed: !!g.gate_passed,
    };
  });
}

function _RiChart({ series }) {
  // viewBox 비율을 실제 카드 폭(.ri-chart max-width)과 맞춘다. preserveAspectRatio="none"
  //   에서 비율이 어긋나면 축 글자가 가로로 늘어나 읽히지 않는다(2026-07-26 실측).
  const W = 1400, H = 320, padL = 58, padR = 16, padT = 14, padB = 30;
  const iw = W - padL - padR, ih = H - padT - padB;
  const pts = series.filter(p => p.pct != null);
  if (pts.length < 2) {
    return <div className="research-empty">세대가 2개 이상 완료되면 개선 추이를 그립니다.</div>;
  }
  const values = pts.flatMap(p => [p.pct, p.bestPct]).filter(v => v != null);
  const lo = Math.min(...values), hi = Math.max(...values);
  const span = (hi - lo) || 1;
  const x = i => padL + (pts.length === 1 ? iw / 2 : (i / (pts.length - 1)) * iw);
  const y = v => padT + ih - ((v - lo) / span) * ih;
  const path = key => pts.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join(" ");
  const zeroY = lo <= 0 && hi >= 0 ? y(0) : null;
  return (
    <div className="chart-wrap ri-chart">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="bt-plot-svg"
           role="img" aria-label="세대별 수익률과 지금까지 최고 수익률 추이">
        <line x1={padL} y1={padT + ih} x2={padL + iw} y2={padT + ih} stroke="var(--line)" />
        <line x1={padL} y1={padT} x2={padL} y2={padT + ih} stroke="var(--line)" />
        {zeroY != null && (
          <line x1={padL} y1={zeroY} x2={padL + iw} y2={zeroY} stroke="var(--chart-grid)" strokeDasharray="4 4" />
        )}
        {/* v5.13.0(D2) — y 중간 눈금 + 그리드(양끝만 있던 축 보강). */}
        {[0.25, 0.5, 0.75].map(t => {
          const v = lo + span * t;
          return (
            <g key={t}>
              <line x1={padL} x2={padL + iw} y1={y(v)} y2={y(v)} stroke="rgba(255,255,255,0.06)" />
              <text x={padL - 6} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--chart-axis)">{v.toFixed(1)}%</text>
            </g>
          );
        })}
        <path d={path("bestPct")} fill="none" stroke="var(--chart-profit)" strokeWidth="3" />
        <path d={path("pct")} fill="none" stroke="var(--chart-accent)" strokeWidth="1.6" strokeDasharray="5 3" />
        {pts.map((p, i) => (
          <circle key={p.gen} cx={x(i)} cy={y(p.pct)} r={p.isRecord ? 4.2 : 2.6}
                  fill={p.isRecord ? "var(--teal)" : "var(--ink-3)"}>
            <title>{`Gen ${p.gen} · ${p.pct.toFixed(2)}%${p.isRecord ? " · 신기록" : ""}${p.gatePassed ? " · 게이트 통과" : ""}`}</title>
          </circle>
        ))}
        <text x={padL - 6} y={y(hi) + 4} textAnchor="end" fontSize="11" fill="var(--chart-axis)">{hi.toFixed(1)}%</text>
        <text x={padL - 6} y={y(lo) + 4} textAnchor="end" fontSize="11" fill="var(--chart-axis)">{lo.toFixed(1)}%</text>
        {/* v5.13.0(D2) — x축 세대 라벨: g0 표기 대신 Gen N, 중간 라벨 포함(≤10개). */}
        {(() => {
          const step = Math.max(1, Math.ceil(pts.length / 10));
          const idx = [];
          for (let i = 0; i < pts.length; i += step) idx.push(i);
          if (idx[idx.length - 1] !== pts.length - 1) idx.push(pts.length - 1);
          return idx.map(i => (
            <text key={`gx${i}`} x={x(i)} y={H - 8} fontSize="11" fill="var(--chart-axis)"
                  textAnchor={i === 0 ? "start" : i === pts.length - 1 ? "end" : "middle"}>
              Gen {pts[i].gen}
            </text>
          ));
        })()}
      </svg>
    </div>
  );
}

function ResearchImprovementCard({ state, baseUrl, runId }) {
  const series = useMemo_ri(() => riImprovementSeries(state && state.generations), [state && state.generations]);
  // 연 수는 run 메타에만 있다. 없으면 연평균은 계산하지 않고 '미발행'으로 둔다.
  const [years, setYears] = useState_ri(null);
  useEffect_ri(() => {
    setYears(null);
    if (!baseUrl || !runId) return undefined;
    const controller = new AbortController();
    fetch(baseUrl + "/runs", { signal: controller.signal })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        const hit = ((j && j.runs) || []).find(r => r && r.run_id === runId);
        const list = hit && Array.isArray(hit.years) ? hit.years : null;
        if (list && list.length > 0) setYears(list.length);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [baseUrl, runId]);

  const last = series.length ? series[series.length - 1] : null;
  const bestPct = last ? last.bestPct : null;
  const bestProfit = last ? last.bestProfit : null;
  const annual = riAnnualizedPct(bestPct, years);
  // 마지막으로 최고 기록을 갱신한 이후 몇 세대가 지났는가 — 정체 판단의 핵심 신호.
  let sinceRecord = null;
  for (let i = series.length - 1; i >= 0; i -= 1) {
    if (series[i].isRecord) { sinceRecord = series.length - 1 - i; break; }
  }
  const gateCount = series.filter(p => p.gatePassed).length;

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          연구가 실제로 좋아지고 있나 · 세대별 개선 추이
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
          {series.length}세대 · 게이트 통과 {gateCount}건
        </span>
      </div>
      <div className="panel-bd">
        {series.length === 0 ? (
          <div className="research-empty">완료된 세대가 없습니다. 연구가 한 세대라도 끝나면 개선 추이가 그려집니다.</div>
        ) : (
          <>
            <div className="ri-kpis">
              <div>
                <span>지금까지 최고 수익금</span>
                <b className={bestProfit != null && bestProfit < 0 ? "neg" : "pos"}>
                  {bestProfit == null ? "미발행" : fmtMoney(bestProfit)}
                </b>
                <small>모든 세대 중 가장 좋았던 값</small>
              </div>
              <div>
                <span>지금까지 최고 수익률</span>
                <b className={bestPct != null && bestPct < 0 ? "neg" : "pos"}>
                  {bestPct == null ? "미발행" : `${bestPct.toFixed(2)}%`}
                </b>
                <small>전체 기간 누적 기준</small>
              </div>
              <div>
                <span>연평균 수익률 <i>파생값</i></span>
                <b className={annual != null && annual < 0 ? "neg" : "pos"}>
                  {annual == null ? "미발행" : `${annual.toFixed(2)}%`}
                </b>
                <small>
                  {annual == null
                    ? "연구 기간(연 수)이 확인되지 않아 계산하지 않았습니다."
                    : `누적 수익률을 ${years}년 기하평균으로 환산 — 백엔드가 발행한 값이 아닙니다.`}
                </small>
              </div>
              <div>
                <span>최고 기록 갱신</span>
                <b className={sinceRecord != null && sinceRecord >= 5 ? "neg" : "pos"}>
                  {sinceRecord == null ? "미발행" : (sinceRecord === 0 ? "직전 세대" : `${sinceRecord}세대 전`)}
                </b>
                <small>
                  {sinceRecord != null && sinceRecord >= 5
                    ? "여러 세대째 최고치가 갱신되지 않았습니다 — 탐색 방향을 바꿀 시점입니다."
                    : "최근에 개선이 있었습니다."}
                </small>
              </div>
            </div>
            <p className="v59-section-intro">
              <b>굵은 선</b>은 지금까지의 최고 수익률(계단처럼 올라가야 정상), <b>점선</b>은 각 세대의 성적입니다.
              점선이 오르내려도 굵은 선이 계단식으로 올라가면 연구가 전진하고 있는 것입니다.
            </p>
            <_RiChart series={series} />
          </>
        )}
      </div>
    </div>
  );
}

Object.assign(window, { ResearchImprovementCard, riImprovementSeries, riAnnualizedPct });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { ResearchImprovementCard, riImprovementSeries, riAnnualizedPct };
