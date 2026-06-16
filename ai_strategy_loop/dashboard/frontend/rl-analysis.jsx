/* rl-analysis.jsx — ResearchLab 상관/조합/차트 보조 컴포넌트 (research-lab.jsx 에서 분리).

   correlation/combos 탭 본문(컨트롤·히트맵·조합 행렬·드릴다운 팝오버·구간/세그먼트 요약)과
   _ValidationPanel 이 쓰는 차트 프리미티브(_GridHeatmap/_EquityChart/_CurveSpark/_McFanChart)
   + 파이프라인 체크포인트 패널, 공통 빈 상태/포맷 유틸을 한곳에 모은다.
   (P5.6 분해: 함수들의 상대 순서는 원본 그대로 — 정적 테스트가 함수 경계로 본문을 추출하므로
    _rlCorrColor→_ResearchEmptyState, _rlPairInterpret→_ComboPairPopover→_CombinationList→
    _RangeSummaryList 인접을 유지한다.)
   stom-ui 전역은 import 하지 않는다(런타임 window 조회). 외부 차트 라이브러리 금지.
*/
const {
  useState: useState_rla,
  useEffect: useEffect_rla,
} = React;

function _rlNum(value, digits) {
  if (typeof value !== "number" || !isFinite(value)) return "--";
  return value.toFixed(digits == null ? 3 : digits);
}

/* E3(2026-06-13) — YYYYMMDD 정수를 'YYYY-MM-DD'로 포맷(연도 표기 포함). 비정상 값은 null. */
function _rlYmd(v) {
  const n = typeof v === "number" ? v : parseInt(v, 10);
  if (!isFinite(n) || n < 19000101 || n > 21001231) return null;
  const y = Math.floor(n / 10000);
  const m = Math.floor((n % 10000) / 100);
  const d = n % 100;
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

/* E3 — equity_curve.days(정렬된 YYYYMMDD 배열)에서 '시작 ~ 끝(연도 포함)' 기간 문자열. */
function _rlPeriodFromDays(days) {
  if (!Array.isArray(days) || days.length === 0) return "기간 정보 없음";
  const s = _rlYmd(days[0]);
  const e = _rlYmd(days[days.length - 1]);
  if (!s || !e) return "기간 정보 없음";
  return s === e ? s : `${s} ~ ${e}`;
}

/* 상관계수 → 발산형(0 중심) 색. 라이트/다크 정합을 위해 하드코딩 rgba 대신
   디자인 토큰(var(--teal)/var(--red)/var(--ink-2))을 color-mix 로 농도 스케일한다.
   양(+)=teal, 음(-)=red, |값|이 클수록 진해진다. 결측/비정상은 faint ink. */
function _rlCorrColor(value) {
  if (typeof value !== "number" || !isFinite(value)) {
    return "color-mix(in srgb, var(--ink-2) 42%, transparent)";
  }
  const t = Math.min(1, Math.abs(value));
  const pct = Math.round(22 + 64 * t);  /* 22%~86% — 0 근처는 옅게, ±1 근처는 진하게. */
  const token = value >= 0 ? "var(--teal)" : "var(--red)";
  return `color-mix(in srgb, ${token} ${pct}%, transparent)`;
}

function _ResearchEmptyState({ message }) {
  return (
    <div className="research-empty">
      {message || "선택한 리서치 화면에 표시할 데이터가 부족합니다."}
    </div>
  );
}

function _CorrelationControls({ method, setMethod, axis, setAxis, loading, pooledTrades, featureCount }) {
  return (
    <div className="research-controls">
      <label>
        <span>method</span>
        <select value={method} onChange={(e) => setMethod(e.target.value)} disabled={loading}>
          <option value="pearson">pearson</option>
          <option value="spearman">spearman</option>
        </select>
      </label>
      <label>
        <span>segment axis</span>
        <select value={axis} onChange={(e) => setAxis(e.target.value)}>
          <option value="time">time</option>
          <option value="market_cap">market_cap</option>
          <option value="change">change</option>
        </select>
      </label>
      <div className="research-kpis">
        <span>sample count {_rlNum(pooledTrades, 0)}</span>
        <span>features {_rlNum(featureCount, 0)}</span>
      </div>
    </div>
  );
}

function _CorrelationHeatmap({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="상관 히트맵을 그릴 feature_matrix 행이 부족합니다." />;
  }
  return (
    <div className="research-heatmap">
      {rows.slice(0, 36).map((row, i) => {
        const label = [row.feature_a, row.feature_b].filter(Boolean).join(" / ") || row.feature || ("feature_" + i);
        const corr = typeof row.correlation === "number" ? row.correlation : null;
        return (
          <div key={i}
               className="research-cell"
               style={{ background: _rlCorrColor(corr) }}
               title={`${label} | correlation ${_rlNum(corr, 4)} | sample count ${row.n || 0}`}>
            <strong>{label}</strong>
            <span>{_rlNum(corr, 3)}</span>
            <small>n={row.n || 0}</small>
          </div>
        );
      })}
    </div>
  );
}

/* P11(2026-06-13) — 변수 조합 탭: 평면 행 목록 → 2-D 상호작용 히트맵.
   pair 배열({feature_a, feature_b, research_score|correlation, sample_count})을
   대칭 행렬로 피벗한다. feature 는 |research_score|(없으면 |corr|) 합으로 점수화해
   상위 N(가독성 위해 cap=10)만 축으로 잡고, 셀 배경은 _rlCorrColor 발산색으로 칠한다.
   대각=자기자신(blank), 누락 pair=빈 셀. hover title 로 "A × B · score · n=…" 노출. */
const _COMBO_MAX_FEATURES = 10;

function _combinationMatrix(rows) {
  const score = {};   /* feature → Σ|score| (축 선정용). */
  const cellMap = {};  /* "a|b" → {score, n} (양방향 저장으로 대칭화). */
  rows.forEach(row => {
    const a = row.feature_a || row.feature;
    const b = row.feature_b;
    if (!a || !b || a === b) return;
    const corr = typeof row.correlation === "number" ? row.correlation : null;
    const val = typeof row.research_score === "number" ? row.research_score : corr;
    if (val == null) return;
    const n = row.sample_count || row.n || 0;
    const w = Math.abs(val);
    score[a] = (score[a] || 0) + w;
    score[b] = (score[b] || 0) + w;
    cellMap[a + "|" + b] = { score: val, n };
    cellMap[b + "|" + a] = { score: val, n };
  });
  const features = Object.keys(score)
    .sort((x, y) => score[y] - score[x])
    .slice(0, _COMBO_MAX_FEATURES);
  return { features, cellMap };
}

/* P13(2026-06-13) — 셀 드릴다운 해석: cellMap 에 이미 있는 score·n 만으로
   부호(양/음 상호작용)·|값| 강도 라벨·표본 충분성(n<임계 경고)을 1줄 한국어로 해석한다.
   백테/거래분포 등 데이터에 없는 통계는 절대 지어내지 않는다(정직성). */
const _COMBO_MIN_SAMPLE = 30;  /* 표본 부족 경고 임계(n<이 값이면 해석 신뢰도 낮음). */

function _rlPairInterpret(score, n) {
  const v = typeof score === "number" && isFinite(score) ? score : null;
  if (v == null) {
    return { sign: "—", strength: "해석 불가", line: "값이 없어 상호작용을 해석할 수 없습니다." };
  }
  const a = Math.abs(v);
  const sign = v >= 0 ? "양(+)" : "음(-)";
  /* |값| 강도 라벨(상관계수 관례: 0.1/0.3/0.5 경계). */
  const strength = a >= 0.5 ? "강함" : a >= 0.3 ? "중간" : a >= 0.1 ? "약함" : "미미";
  const lowSample = (n || 0) < _COMBO_MIN_SAMPLE;
  let line;
  if (a >= 0.5) {
    line = v >= 0
      ? "강한 양의 상호작용 — 두 변수가 함께 높을 때 우수한 경향."
      : "강한 음의 상호작용 — 한쪽이 높고 다른 쪽이 낮을 때 우수한 경향.";
  } else if (a >= 0.3) {
    line = v >= 0
      ? "중간 양의 상호작용 — 함께 움직이는 경향이 관찰됩니다."
      : "중간 음의 상호작용 — 반대로 움직이는 경향이 관찰됩니다.";
  } else if (a >= 0.1) {
    line = "약한 상관 — 방향성은 있으나 신호가 약합니다.";
  } else {
    line = "미미한 상관 — 두 변수의 상호작용이 거의 없습니다.";
  }
  if (lowSample) {
    line += ` 표본 부족 주의(n=${n || 0} < ${_COMBO_MIN_SAMPLE}) — 해석 신뢰도 낮음.`;
  }
  return { sign, strength, line, lowSample };
}

/* P13 — 선택 변수쌍 상세 팝오버(.rp-overlay 재사용, click-outside + Esc 닫기).
   cellMap 에 이미 있는 score·n 만 노출하고, 더 깊은 per-pair 거래 분포는
   향후 백엔드 엔드포인트가 필요함을 정직하게 안내한다(통계 날조 금지). */
function _ComboPairPopover({ pair, onClose }) {
  useEffect_rla(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  if (!pair) return null;
  const info = _rlPairInterpret(pair.score, pair.n);
  return (
    <div className="rp-overlay" onClick={onClose}>
      <div className="rp-overlay-card" style={{ maxWidth: 460 }} onClick={(e) => e.stopPropagation()}>
        <div className="rp-overlay-hd">
          <span className="rp-card-title">변수쌍 상세 — {pair.a} × {pair.b}</span>
          <button type="button" className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕ 닫기 (Esc)
          </button>
        </div>
        <div style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: 8 }}>
          <div className="mono" style={{ fontSize: 12 }}>
            변수쌍: <b>{pair.a}</b> × <b>{pair.b}</b>
          </div>
          <div className="mono" style={{ fontSize: 12 }}>
            research_score/correlation: <b style={{ color: pair.score >= 0 ? "var(--teal)" : "var(--red)" }}>
              {_rlNum(pair.score, 4)}
            </b>
            {" · "}부호 {info.sign} · 강도 {info.strength}
          </div>
          <div className="mono" style={{ fontSize: 12 }}>
            sample_count: <b>{pair.n || 0}</b>
            {info.lowSample ? <span style={{ color: "var(--amber)" }}> · 표본 부족</span> : null}
          </div>
          <div className="research-empty" style={{ marginTop: 2 }}>
            {info.line}
          </div>
          <div className="research-empty" style={{ color: "var(--ink-3)", fontSize: 11 }}>
            ※ 더 깊은 변수쌍별 거래 분포(승률·구간별 손익 등)는 향후 백엔드 엔드포인트가 필요합니다 —
            현재는 이 화면 데이터(score·n)에 없는 통계를 만들어 표시하지 않습니다.
          </div>
        </div>
      </div>
    </div>
  );
}

function _CombinationList({ rows }) {
  const { features, cellMap } = _combinationMatrix(rows || []);
  const [selected, setSelected] = useState_rla(null);  /* P13 — 드릴다운 선택 변수쌍. */
  if (features.length === 0) {
    return <_ResearchEmptyState message="선택한 run 에 분석할 변수 조합이 부족합니다." />;
  }
  const N = features.length;
  const selKey = selected ? selected.a + "|" + selected.b : null;
  return (
    <div>
      <div className="stom-combo-grid"
           style={{ gridTemplateColumns: `auto repeat(${N}, minmax(0,1fr))` }}>
        {/* 헤더 행: 좌상단 빈 칸 + 열 라벨(세로). */}
        <div className="stom-combo-axis" />
        {features.map(f => (
          <div key={"col-" + f} className="stom-combo-axis col" title={f}>{f}</div>
        ))}
        {/* 본문: 행 라벨 + 셀(대각=blank, 누락=빈 셀). */}
        {features.map(rowF => (
          <React.Fragment key={"row-" + rowF}>
            <div className="stom-combo-axis" title={rowF}>{rowF}</div>
            {features.map(colF => {
              if (rowF === colF) {
                return <div key={rowF + "|" + colF} className="stom-combo-cell" />;
              }
              const cell = cellMap[rowF + "|" + colF];
              if (!cell) {
                return <div key={rowF + "|" + colF} className="stom-combo-cell" />;
              }
              const key = rowF + "|" + colF;
              const isSel = selKey === key;
              /* P13 — 채워진 셀 클릭 시 드릴다운 팝오버. hover title 은 유지. */
              return (
                <div key={key}
                     className="stom-combo-cell"
                     role="button"
                     tabIndex={0}
                     style={{ background: _rlCorrColor(cell.score), cursor: "pointer",
                              outline: isSel ? "2px solid var(--blue)" : "none" }}
                     title={`${rowF} × ${colF} · ${_rlNum(cell.score, 3)} · n=${cell.n} · 클릭=상세`}
                     onClick={() => setSelected({ a: rowF, b: colF, score: cell.score, n: cell.n })}>
                  {_rlNum(cell.score, 2)}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <div className="research-empty" style={{ marginTop: 6 }}>
        범례: <span style={{ color: "var(--teal)" }}>teal=양(+)</span>
        {" · "}<span style={{ color: "var(--red)" }}>red=음(-)</span>
        {" · |값|이 클수록 진함 · 대각/누락 조합은 빈 셀 · 셀 클릭=변수쌍 상세"}
      </div>
      {/* P13 — 변수쌍 드릴다운 팝오버(click-outside + Esc 닫기). */}
      {selected && <_ComboPairPopover pair={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function _RangeSummaryList({ rows }) {
  if (!rows || rows.length === 0) {
    return <_ResearchEmptyState message="히스토그램 분석에 필요한 range_summaries 가 부족합니다." />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row" title="histogram and win/loss range contrast">
          <span className="mono">{row.feature}</span>
          <span>median {_rlNum(row.median, 2)}</span>
          <span>q25-q75 {_rlNum(row.q25, 2)}~{_rlNum(row.q75, 2)}</span>
          <span>win/loss Δ {_rlNum(row.win_loss && row.win_loss.mean_delta, 3)}</span>
          <small>histogram {(row.histogram || []).map(b => b.count).join("/")}</small>
        </div>
      ))}
    </div>
  );
}

function _SegmentSummaryList({ summary, axis }) {
  const rows = summary && Array.isArray(summary[axis]) ? summary[axis] : [];
  if (rows.length === 0) {
    return <_ResearchEmptyState message={axis + " 축의 segment_summaries 가 부족합니다."} />;
  }
  return (
    <div className="research-combo-list">
      {rows.slice(0, 8).map((row, i) => (
        <div key={i} className="research-combo-row">
          <span className="mono">{axis}:{row.label}</span>
          <span>avg {_rlNum(row.avg_return, 3)}</span>
          <span>win {_rlNum(row.win_rate, 3)}</span>
          <small>sample count {row.sample_count || 0}</small>
        </div>
      ))}
    </div>
  );
}

function _RecencyResearchBadge({ recency }) {
  if (!recency) return null;
  return (
    <div className="research-empty" title="research_score_not_promotion">
      recency_research · {recency.score_label || "research_score_not_promotion"} ·
      score {_rlNum(recency.research_score, 4)}
    </div>
  );
}

/* 과업3(2026-06-12) — 파이프라인 체크포인트 소형 패널.
   /pipeline_status → {items:[{prefix, stages:{stage:bool,...}, mtime},...]}
   prefix별로 단계 체크리스트(done=✅/미완=·) 1줄씩, 최대 5개. */
function _PipelineCheckpointPanel({ baseUrl, isDemo }) {
  const [items, setItems] = useState_rla(null);
  useEffect_rla(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/pipeline_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setItems(j && Array.isArray(j.items) ? j.items : []))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginTop: 10 }}>
      <div className="research-empty">파이프라인 체크포인트</div>
      {items.slice(0, 5).map((item, i) => {
        const stages = item.stages || {};
        const stageList = Object.entries(stages);
        return (
          <div key={i} className="mono" style={{ fontSize: 11, marginTop: 2 }}>
            <b>{item.prefix}</b>
            {" · "}
            {stageList.length === 0
              ? "단계 없음"
              : stageList.map(([k, v]) => (v ? "✅" : "·") + k).join("  ")}
          </div>
        );
      })}
    </div>
  );
}

/* C6(2026-06-11) — 2-D 격자 히트맵: 수익(부호·크기) 또는 MDD(E5 토글)를 색으로, mesa를 ★로. */
function _GridHeatmap({ grid, metric }) {
  const useMdd = metric === "mdd";
  const cells = {};
  (grid.cells || []).forEach(c => { cells[c.a + "|" + c.b] = c; });
  const maxAbs = Math.max(1, ...((grid.cells || []).map(c => Math.abs(useMdd ? c.mdd : c.profit))));
  const mesaSet = new Set((grid.mesa_cells || []).map(m => m.a + "|" + m.b));
  return (
    <table className="mono" style={{ fontSize: 10, marginTop: 4 }}>
      <thead>
        <tr>
          <th>{grid.param_a + " \\ " + grid.param_b}</th>
          {(grid.b_values || []).map(b => <th key={b} style={{ padding: "2px 6px" }}>{b}</th>)}
        </tr>
      </thead>
      <tbody>
        {(grid.a_values || []).map(a => (
          <tr key={a}>
            <th style={{ padding: "2px 6px" }}>{a}</th>
            {(grid.b_values || []).map(b => {
              const c = cells[a + "|" + b];
              if (!c) return <td key={b}>—</td>;
              const value = useMdd ? c.mdd : c.profit;
              const pct = Math.round(15 + 70 * Math.abs(value) / maxAbs);  /* 15%~85% 농도. */
              /* MDD=위험 적색, 수익은 부호별 발산(흑자 teal · 적자 red) — 라이트/다크 토큰. */
              const token = useMdd ? "var(--red)" : (c.profit > 0 ? "var(--teal)" : "var(--red)");
              const bg = `color-mix(in srgb, ${token} ${pct}%, transparent)`;
              const isMesa = mesaSet.has(a + "|" + b);
              return (
                <td key={b}
                    title={`${grid.param_a}=${a}, ${grid.param_b}=${b} · 손익 ${Math.round(c.profit).toLocaleString()} · MDD ${_rlNum(c.mdd, 2)} · ${c.trades}건`}
                    style={{ background: bg, textAlign: "right", padding: "2px 6px",
                             outline: isMesa ? "2px solid var(--mesa-gold)" : "none" }}>
                  {useMdd ? _rlNum(c.mdd, 1) : Math.round(c.profit / 10000).toLocaleString() + "만"}{isMesa ? "★" : ""}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/* E2/D4(2026-06-11) — 누적 수익곡선: '우상향 그림'을 직접 렌더(0선 점선). */
function _EquityChart({ cum }) {
  const pts = (cum || []).map(Number).filter(v => isFinite(v));
  if (pts.length < 2) return null;
  const W = 620, H = 150, PAD = 6;
  const min = Math.min(0, ...pts), max = Math.max(0, ...pts);
  const span = Math.max(max - min, 1);
  const x = i => PAD + (i / (pts.length - 1)) * (W - PAD * 2);
  const y = v => H - PAD - ((v - min) / span) * (H - PAD * 2);
  const path = pts.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg width={W} height={H} style={{ background: "rgba(255,255,255,0.03)", borderRadius: 4 }}>
      <line x1={PAD} y1={y(0)} x2={W - PAD} y2={y(0)} stroke="#777" strokeDasharray="3,3" strokeWidth="0.8" />
      <path d={path} fill="none" stroke={last >= 0 ? "#4c9" : "#c66"} strokeWidth="1.8" />
      <text x={W - PAD - 4} y={y(last) - 6} fill="var(--ink-2)" fontSize="10" textAnchor="end">
        {Math.round(last).toLocaleString()}
      </text>
    </svg>
  );
}

/* C6 보조 — 1-D 응답 곡선 스파크라인(0선 점선 기준, 흑자 구간이 한눈에). */
function _CurveSpark({ curve }) {
  const pts = (curve || []).filter(p => p && p.ok);
  if (pts.length < 2) return null;
  const W = 90, H = 22;
  const profits = pts.map(p => p.profit || 0);
  const min = Math.min(0, ...profits), max = Math.max(0, ...profits);
  const span = Math.max(max - min, 1);
  const x = i => 2 + (i / (pts.length - 1)) * (W - 4);
  const y = v => H - 2 - ((v - min) / span) * (H - 4);
  const path = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.profit || 0).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} style={{ verticalAlign: "middle" }}>
      <line x1="2" y1={y(0)} x2={W - 2} y2={y(0)} stroke="#777" strokeDasharray="2,2" strokeWidth="0.8" />
      <path d={path} fill="none" stroke="#5b9" strokeWidth="1.5" />
    </svg>
  );
}

function _McFanChart({ fan }) {
  if (!fan || !Array.isArray(fan.x) || !fan.x.length) return null;
  const W = 320, H = 90, PAD = 4;
  const all = [].concat(fan.p05 || [], fan.p95 || [], fan.p50 || []);
  const lo = Math.min.apply(null, all), hi = Math.max.apply(null, all);
  const span = (hi - lo) || 1;
  const px = (i) => PAD + (W - 2 * PAD) * (fan.x[i] || 0);
  const py = (v) => H - PAD - (H - 2 * PAD) * ((v - lo) / span);
  const pts = (arr) => arr.map((v, i) => `${px(i).toFixed(1)},${py(v).toFixed(1)}`).join(" ");
  const band = (upper, lower) =>
    pts(upper) + " " + lower.map((v, i) => `${px(lower.length - 1 - i).toFixed(1)},${py(lower[lower.length - 1 - i]).toFixed(1)}`).join(" ");
  return (
    <svg width={W} height={H} style={{ display: "block", marginTop: 4 }}
         role="img" aria-label="MC fan chart">
      <polygon points={band(fan.p95, fan.p05)} fill="rgba(80,140,200,0.18)" stroke="none" />
      <polygon points={band(fan.p75, fan.p25)} fill="rgba(80,140,200,0.28)" stroke="none" />
      <polyline points={pts(fan.p50)} fill="none" stroke="rgba(120,190,255,0.95)" strokeWidth="1.5" />
      <line x1={PAD} y1={py(0)} x2={W - PAD} y2={py(0)}
            stroke="rgba(200,200,200,0.4)" strokeDasharray="3,3" strokeWidth="1" />
    </svg>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { _rlNum, _rlYmd, _rlPeriodFromDays, _rlCorrColor, _ResearchEmptyState, _CorrelationControls, _CorrelationHeatmap, _COMBO_MAX_FEATURES, _combinationMatrix, _COMBO_MIN_SAMPLE, _rlPairInterpret, _ComboPairPopover, _CombinationList, _RangeSummaryList, _SegmentSummaryList, _RecencyResearchBadge, _PipelineCheckpointPanel, _GridHeatmap, _EquityChart, _CurveSpark, _McFanChart };
