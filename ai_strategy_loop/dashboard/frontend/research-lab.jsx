/* ResearchLabPanel - compact analysis workspace for Edge, Feature, Correlation, and Variable Combinations. */

const {
  useState: useState_rl,
  useEffect: useEffect_rl,
  useCallback: useCallback_rl,
  useMemo: useMemo_rl,
} = React;

/* ─────────────────────────────────────────────────────────────────────────────
 * P7(2026-06-15) — freeze_verdict 공유 표시 블록.
 *   research-lab(_ValidationPanel)·dashboard-pages(VerdictPanel) 두 패널이 동일한
 *   PROMOTE 체크리스트·경보·요약줄을 각자 인라인 렌더링하던 것을 단일 정본 컴포넌트로
 *   통합한다(필드 무손실). research-lab 이 ORDER 상 dashboard-pages 보다 앞서므로 여기서
 *   정의하고 window-export → dashboard-pages 는 window.* 로 소비한다.
 *   정본 스타일: fontSize 12, width:100%, alert 색 var(--amber)(토큰), 빈 상태 메시지,
 *   상태→아이콘은 전역 ICON 비의존(컴포넌트-로컬 맵).
 *   데이터 계약: v.promote_checklist[].{item,status,detail}, v.alerts[], v.lines[].
 * ──────────────────────────────────────────────────────────────────────────── */
const _VDT_STATUS_ICON = { pass: "✅", warn: "⚠️", fail: "❌", pending: "⏳" };

function VdtPromoteChecklist({ v }) {
  const checks = (v && v.promote_checklist) || [];
  if (checks.length === 0) {
    return (
      <div className="mono" style={{ fontSize: 11, opacity: 0.6 }}>
        PROMOTE 체크리스트: 데이터 없음
      </div>
    );
  }
  return (
    <table className="mono" style={{ fontSize: 12, width: "100%", marginBottom: 8 }}>
      <thead><tr><th>PROMOTE 조건</th><th>상태</th><th>근거</th></tr></thead>
      <tbody>
        {checks.map((c, i) => (
          <tr key={"vdtc" + i}>
            <td>{c.item}</td>
            <td>{_VDT_STATUS_ICON[c.status] || "?"}</td>
            <td>{c.detail || "—"}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function VdtAlerts({ v }) {
  const alerts = (v && v.alerts) || [];
  return alerts.map((a, i) => (
    <div key={"vdta" + i} className="mono" style={{ fontSize: 12, color: "var(--amber)" }}>⚠️ {a}</div>
  ));
}

function VdtSummaryLines({ v }) {
  const lines = (v && v.lines) || [];
  return lines.map((l, i) => (
    <div key={"vdtl" + i} className="mono" style={{ fontSize: 12 }}>{l}</div>
  ));
}

Object.assign(window, { VdtPromoteChecklist, VdtAlerts, VdtSummaryLines });

const RESEARCH_TABS = [
  { id: "edge", label: "엣지(승률·기대값)" },
  { id: "feature", label: "변수 중요도" },
  { id: "correlation", label: "상관관계" },
  { id: "combos", label: "변수 조합" },
  { id: "validation", label: "검증" },
];

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
  useEffect_rl(() => {
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
  const [selected, setSelected] = useState_rl(null);  /* P13 — 드릴다운 선택 변수쌍. */
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
  const [items, setItems] = useState_rl(null);
  useEffect_rl(() => {
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

/* D1/D2/D4(2026-06-10) — 검증 패널: 연도 분해 · 선택기 미리보기 · 부검 요약.
   읽기 전용 GET 3종(/run_yearly /selector_preview /autopsy)만 소비한다.
   근거: 원인5(연도별 쇠퇴는 합계로 안 보임)·원인1(기준-목표 비정합을 눈으로 확인). */
function _ValidationPanel({ baseUrl, runId, isDemo }) {
  const [selector, setSelector] = useState_rl("seed_relative_v1");
  const [yearly, setYearly] = useState_rl(null);
  const [preview, setPreview] = useState_rl(null);
  const [autopsyGen, setAutopsyGen] = useState_rl(0);
  const [autopsy, setAutopsy] = useState_rl(null);
  const [cf, setCf] = useState_rl(null);
  const [mc, setMc] = useState_rl(null);
  const [tmap, setTmap] = useState_rl(null);
  const [compareRun, setCompareRun] = useState_rl("");  /* M12 — 지도 비교 run. */
  const [ops, setOps] = useState_rl(null);  /* 운영 현황 — 10초 자동 갱신. */
  const [grid, setGrid] = useState_rl(null);     /* C6 — 2-D 격자 히트맵. */
  const [gridRun, setGridRun] = useState_rl("");
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const fetchGrid = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    const rid = gridRun.trim() || runId;
    if (!rid) return;
    fetch(baseUrl + "/tmap_grid?run_id=" + encodeURIComponent(rid),
          { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setGrid(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, gridRun, isDemo, runId]);

  const [gridMetric, setGridMetric] = useState_rl("profit");  /* E5 — 히트맵 색 기준. */
  const [runOptions, setRunOptions] = useState_rl([]);  /* F2 — run 자동완성. */
  useEffect_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/runs", { signal: AbortSignal.timeout(10000) })
      .then(r => (r.ok ? r.json() : null))
      .then(d => setRunOptions(((d && d.runs) || []).slice(0, 40).map(r => r.run_id)))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  const [niche, setNiche] = useState_rl(null);  /* D3 — 니치 지도 비교. */
  const fetchNiche = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    fetch(baseUrl + "/niche_compare", { signal: AbortSignal.timeout(15000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setNiche(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, isDemo]);

  /* 과업2(2026-06-12) — 포트폴리오 결합 시뮬 v0 균등가중. */
  const [psimRun1, setPsimRun1] = useState_rl("");
  const [psimRun2, setPsimRun2] = useState_rl("");
  const [psim, setPsim] = useState_rl(null);
  const fetchPsim = useCallback_rl(() => {
    if (isDemo || !baseUrl) return;
    const r1 = psimRun1.trim(), r2 = psimRun2.trim();
    if (!r1 || !r2) return;
    fetch(baseUrl + "/portfolio_sim?runs=" + encodeURIComponent(r1 + "," + r2),
          { signal: AbortSignal.timeout(15000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setPsim(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, isDemo, psimRun1, psimRun2]);

  const [verdict, setVerdict] = useState_rl(null);  /* 검증 결산 — V1~V5 종합. */

  useEffect_rl(() => {
    if (isDemo || !baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setOps(j))
      .catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    fetch(baseUrl + "/freeze_verdict", { signal: AbortSignal.timeout(12000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => setVerdict(j))
      .catch(() => {});
    return () => clearInterval(timer);
  }, [baseUrl, isDemo]);

  const fetchTmap = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const cmp = compareRun.trim()
      ? "&compare_run_id=" + encodeURIComponent(compareRun.trim()) : "";
    fetch(baseUrl + "/tmap_map?run_id=" + encodeURIComponent(runId) + cmp,
          { signal: AbortSignal.timeout(10000) })
      .then(r => r.ok ? r.json() : null)
      .then(j => setTmap(j))
      .catch(e => setErr(String(e)));
  }, [baseUrl, compareRun, isDemo, runId]);

  const refresh = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const yUrl = baseUrl + "/run_yearly?run_id=" + encodeURIComponent(runId);
    const pUrl = baseUrl + "/selector_preview?run_id=" + encodeURIComponent(runId)
      + "&selector=" + encodeURIComponent(selector);
    Promise.all([
      fetch(yUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
      fetch(pUrl, { signal: AbortSignal.timeout(8000) }).then(r => r.ok ? r.json() : null),
    ])
      .then(([y, p]) => { setYearly(y); setPreview(p); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, selector]);

  useEffect_rl(() => { refresh(); }, [refresh]);

  const [equity, setEquity] = useState_rl(null);  /* E2/D4 — 누적 수익곡선. */
  const fetchAutopsy = useCallback_rl(() => {
    if (isDemo || !baseUrl || !runId) return;
    const q = "?run_id=" + encodeURIComponent(runId) + "&gen_no=" + encodeURIComponent(autopsyGen);
    Promise.all([
      fetch(baseUrl + "/autopsy" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/counterfactual" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/freeze_mc" + q, { signal: AbortSignal.timeout(15000) })
        .then(r => r.ok ? r.json() : null),
      fetch(baseUrl + "/equity_curve" + q, { signal: AbortSignal.timeout(10000) })
        .then(r => r.ok ? r.json() : null),
    ])
      .then(([a, c, m, eq]) => { setAutopsy(a); setCf(c); setMc(m); setEquity(eq); })
      .catch(e => setErr(String(e)));
  }, [autopsyGen, baseUrl, isDemo, runId]);

  if (isDemo || !runId) {
    return <div className="research-lab-panel"><_ResearchEmptyState message="검증 화면을 표시할 run 컨텍스트가 부족합니다." /></div>;
  }

  const gens = (yearly && Array.isArray(yearly.generations)) ? yearly.generations : [];
  return (
    <div className="research-lab-panel">
      <div className="research-controls">
        <label>
          <span>selector</span>
          <select value={selector} onChange={(e) => setSelector(e.target.value)} disabled={loading}>
            <option value="seed_relative_v1">seed_relative_v1</option>
            <option value="sparse_positive_v1">sparse_positive_v1</option>
          </select>
        </label>
        <span className="research-empty">diagnostic_only · 동결 아티팩트 아님</span>
        {/* E4 — 품질/적합도 용어 hover 설명(이 파이프라인 기준). */}
        <span className="research-help"
              title="적합도(Fitness): 손익·MDD·거래수·일관성을 가중합한 한 개의 점수. 세대(전략)가 목표 기준에 얼마나 부합하는지를 나타냅니다 — 높을수록 좋고, 게이트의 1차 통과 기준입니다. 차트는 세대 진행(x)에 따라 적합도가 우상향하는지를 봅니다.">
          적합도 ?
        </span>
        <span className="research-help"
              title="품질(Quality): 결과의 견고함 지표 모음(흑자율·고원/mesa 안정성·OOS 유지 등). 단발 고점이 아니라 이웃 파라미터·다른 기간에서도 성과가 유지되는지를 봅니다 — 과최적화를 거르는 척도입니다.">
          품질 ?
        </span>
      </div>
      {err && <_ResearchEmptyState message={"응답을 받지 못했습니다: " + err} />}

      {ops && (
        <div style={{ marginTop: 6 }}>
          <div className="research-empty">
            {"운영 현황 (10초 자동 갱신)"
              + (ops.walkforward
                ? ` · WF ${ops.walkforward.path}: 정책 ${Math.round(ops.walkforward.policy_total || 0).toLocaleString()} vs 시드 ${Math.round(ops.walkforward.baseline_total || 0).toLocaleString()} (${ops.walkforward.windows_done}창 완료)`
                : "")}
          </div>
          {(ops.active || []).length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>실행 중 run 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>실행 중 run</th><th>세대</th><th>마지막 포인트</th><th>무진행(초)</th><th>상태</th></tr></thead>
                <tbody>
                  {ops.active.map(a => (
                    <tr key={a.run_id}>
                      <td>{a.run_id}</td>
                      <td>{a.gens}</td>
                      <td>{a.last_label || "—"}</td>
                      <td>{a.seconds_since_last_gen}</td>
                      <td>{a.health === "active" ? "✅ 진행 중" : "⚠️ 정체 의심"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          {(ops.recent || []).length > 0 && (
            <div className="mono" style={{ fontSize: 11 }}>
              {"최근 완료: " + ops.recent.slice(0, 5).map(r =>
                `${r.run_id}(${r.gens}세대${r.best_profit != null ? "·최고 " + Math.round(r.best_profit).toLocaleString() : ""})`
              ).join("  ·  ")}
            </div>
          )}
          {(ops.evidence || []).length > 0 && (
            <div className="research-empty">
              {"최신 증거: " + ops.evidence.map(e => `${e.name}(${e.age_min}분 전)`).join(" · ")}
            </div>
          )}
        </div>
      )}

      {verdict && (verdict.lines || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">검증 결산 (V1~V5 + 리스크 — 결정 카드 라이브)</div>
          {/* P7 — 공유 PROMOTE 체크리스트(정본: research-lab 정의). 빈 상태 메시지 포함. */}
          {(verdict.promote_checklist || []).length > 0 && (
            <VdtPromoteChecklist v={verdict} />
          )}
          {verdict.walkforward && Array.isArray(verdict.walkforward.windows)
            && verdict.walkforward.windows.length > 0 && (
            <table className="mono" style={{ fontSize: 11, marginBottom: 4 }}>
              <thead><tr><th>WF 창(fit)</th><th>eval</th><th>θ 선택</th><th>정책</th><th>시드</th></tr></thead>
              <tbody>
                {verdict.walkforward.windows.map((w, i) => (
                  <tr key={"w" + i}>
                    <td>{w.fit_start}~{w.fit_end}</td>
                    <td>{w.eval_start}~{w.eval_end}</td>
                    <td>{w.theta
                      ? Object.entries(w.theta).map(([k, v]) => `${k}=${v}`).join(",")
                      : "기권(시드 유지)"}</td>
                    <td>{w.policy ? Math.round(w.policy.profit).toLocaleString() : "—"}</td>
                    <td>{w.baseline ? Math.round(w.baseline.profit).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {/* P7 — 공유 경보·요약줄(정본: research-lab 정의). */}
          <VdtAlerts v={verdict} />
          <VdtSummaryLines v={verdict} />
        </div>
      )}

      {niche && (niche.runs || []).length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">니치 지도 비교 (최근 tmap run 자동 — 신규 니치 4종 아침 분석용)</div>
          <table className="mono" style={{ fontSize: 11, width: "100%" }}>
            <thead><tr><th>run</th><th>상태</th><th>ok세대</th><th>베이스라인</th><th>최강 슬롯 고원 / 격자</th><th>최고 단일점</th><th>시간대</th><th>R²·정체</th><th>동결상관</th></tr></thead>
            <tbody>
              {niche.runs.map(r => (
                <tr key={r.run_id}>
                  <td>{r.run_id}</td>
                  <td>{r.status === "running" ? "🔄" : "✅"}</td>
                  <td>{r.gens_ok}</td>
                  <td>{r.baseline ? `${Math.round(r.baseline.profit).toLocaleString()} (MDD ${_rlNum(r.baseline.mdd, 1)})` : "—"}</td>
                  <td>
                    {r.top_slot
                      ? `${r.top_slot.param}: 중심 ${r.top_slot.center} · 평균 ${Math.round(r.top_slot.mean_profit || 0).toLocaleString()} (score ${_rlNum(r.top_slot.plateau_score, 2)})`
                      : r.grid
                        ? `격자 ${r.grid.cells}셀 · 흑자 ${Math.round((r.grid.positive_ratio || 0) * 100)}% · mesa ${r.grid.mesa}`
                        : "—"}
                  </td>
                  <td>{r.best_profit != null ? Math.round(r.best_profit).toLocaleString() : "—"}</td>
                  <td>{(r.time_buckets || []).join(",") || "—"}</td>
                  <td>{r.shape_r2 != null ? `${_rlNum(r.shape_r2, 2)}·${r.stagnation_days}일` : "—"}</td>
                  <td>{r.corr_vs_frozen != null ? _rlNum(r.corr_vs_frozen, 2) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="research-empty" style={{ marginTop: 6 }}>연도 분해 (per-trade CSV 집계)</div>
      <table className="mono" style={{ fontSize: 11, width: "100%" }}>
        <thead><tr><th>gen</th><th>label</th><th>연도별 손익(거래수·승률)</th></tr></thead>
        <tbody>
          {gens.map(g => (
            <tr key={g.gen_no}>
              <td>{g.gen_no}</td>
              <td>{g.label || g.buy_name || "—"}</td>
              <td>
                {(g.years || []).length
                  ? g.years.map(y => `${y.year}: ${Math.round(y.profit).toLocaleString()} (${y.trades}건·${Math.round((y.win_rate || 0) * 100)}%)`).join("  ·  ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="research-empty" style={{ marginTop: 8 }}>
        선택기 미리보기 — selected: {preview && preview.selected ? "TRUE" : "false"}
        {preview && preview.mdd_limit != null ? ` · mdd_limit ${_rlNum(preview.mdd_limit, 2)}` : ""}
        {preview && preview.selected_candidate
          ? ` · gen${preview.selected_candidate.gen_no} ${preview.selected_candidate.label || preview.selected_candidate.buy_name}`
          : ""}
      </div>
      {preview && Array.isArray(preview.rejected) && preview.rejected.length > 0 && (
        <ul className="mono" style={{ fontSize: 11 }}>
          {preview.rejected.map(rj => (
            <li key={rj.gen_no}>gen{rj.gen_no} {rj.label || ""}: {(rj.reasons || []).join("; ")}</li>
          ))}
        </ul>
      )}

      <div className="research-controls" style={{ marginTop: 8 }}>
        <label>
          <span>gen</span>
          <input type="number" value={autopsyGen} min={0}
                 onChange={(e) => setAutopsyGen(Number(e.target.value) || 0)}
                 style={{ width: 64 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchAutopsy}>부검·반사실·MC 보기</button>
        <datalist id="rl-run-options">
          {runOptions.map(id => <option key={id} value={id} />)}
        </datalist>
        <label>
          <span>비교 run</span>
          <input type="text" value={compareRun} placeholder="다른 스윕 run_id (선택)"
                 list="rl-run-options"
                 onChange={(e) => setCompareRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchTmap}>TMAP 지도</button>
        <label>
          <span>격자 run</span>
          <input type="text" value={gridRun} placeholder="--grid 스윕 run_id"
                 list="rl-run-options"
                 onChange={(e) => setGridRun(e.target.value)} style={{ width: 180 }} />
        </label>
        <button type="button" className="research-tab" onClick={fetchGrid}>2-D 히트맵</button>
        <button type="button" className="research-tab" onClick={fetchNiche}>니치 비교</button>
      </div>
      {autopsy && (
        <div className="mono" style={{ fontSize: 11, whiteSpace: "pre-wrap" }}>
          {autopsy.status !== "ok"
            ? `autopsy: ${autopsy.status}`
            : `${autopsy.entry_summary || "(진입 부검 없음)"}\n\n${autopsy.exit_summary || "(청산 부검 없음)"}`}
        </div>
      )}

      {cf && cf.status === "ok" && Array.isArray(cf.suggestions) && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">반사실 필터 제안 (백테 0회·인샘플 advisory — 채택 시 정식 파이프라인 검증 필수)</div>
          {cf.suggestions.length === 0
            ? <div className="mono" style={{ fontSize: 11 }}>총손익이 깎이지 않는 강화 필터 없음</div>
            : (
              <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                <thead><tr><th>필터</th><th>거래</th><th>총손익</th><th>승률</th><th>잘린 거래 순손익</th><th>최근연도</th></tr></thead>
                <tbody>
                  {cf.suggestions.map((s, i) => (
                    <tr key={i}>
                      <td>{s.filter}</td>
                      <td>{s.base_trades}→{s.kept_trades}</td>
                      <td>{Math.round((s.profit_ratio || 0) * 100)}%</td>
                      <td>{Math.round((s.base_win_rate || 0) * 100)}%→{Math.round((s.kept_win_rate || 0) * 100)}%</td>
                      <td>{Math.round(s.cut_net_profit || 0).toLocaleString()}</td>
                      <td>{s.recent_year
                        ? `${s.recent_year.year}: ${Math.round(s.recent_year.base_profit).toLocaleString()}→${Math.round(s.recent_year.kept_profit).toLocaleString()}`
                        : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {mc && mc.status === "ok" && mc.mc && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            블록 부트스트랩 MC (일별 손익·레짐 군집 보존 — iid 거래 추출 MC의 OOS 전이 실패 교훈 반영)
          </div>
          <div className="mono" style={{ fontSize: 11 }}>
            {`P(총손익>0)=${Math.round((mc.mc.p_positive || 0) * 100)}% · 총손익 p05/p50/p95 = `
              + `${Math.round(mc.mc.profit_p05).toLocaleString()} / ${Math.round(mc.mc.profit_p50).toLocaleString()} / ${Math.round(mc.mc.profit_p95).toLocaleString()}`
              + ` · MDD(낙폭금액) p50/p95 = ${Math.round(mc.mc.mdd_p50).toLocaleString()} / ${Math.round(mc.mc.mdd_p95).toLocaleString()}`
              + ` (${mc.mc.n_days}일·${mc.mc.n_boot}회·블록 ${mc.mc.block_len}일)`}
          </div>
          <_McFanChart fan={mc.mc.fan} />
        </div>
      )}

      {equity && equity.status === "ok" && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty"
               title="x축은 거래일 진행(왼→오른쪽=과거→현재), y축은 누적 손익(원). 0선 점선 위는 흑자 구간입니다.">
            {`누적 수익곡선 — gen ${equity.gen_no}${equity.label ? " · " + equity.label : ""}`
              + ` · 총 ${Math.round(equity.total).toLocaleString()}`}
          </div>
          {/* E3 — 축 의미(거래일 진행)·기간(연도 포함) 명시. */}
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-2)", marginBottom: 2 }}>
            {`x축: 거래일 진행(${equity.n_days}거래일) · 기간 ${_rlPeriodFromDays(equity.days)} · y축: 누적 손익(원)`}
          </div>
          <_EquityChart cum={equity.cum} />
        </div>
      )}

      {tmap && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty">
            TMAP 경향성 지도 (고원 &gt; 피크 — 이웃 θ도 흑자인 영역이 진짜)
          </div>
          {(!tmap.count || !Object.keys(tmap.params || {}).length)
            ? <div className="mono" style={{ fontSize: 11 }}>이 run은 TMAP 스윕이 아닙니다 (tmap_sweep run_id를 선택하세요)</div>
            : (
              <div>
                <div className="mono" style={{ fontSize: 11 }}>
                  {tmap.baseline
                    ? `베이스라인(θ=기본값): 손익 ${Math.round(tmap.baseline.profit).toLocaleString()} · MDD ${_rlNum(tmap.baseline.mdd, 2)} · ${tmap.baseline.trades}건`
                    : "베이스라인 없음"}
                </div>
                <table className="mono" style={{ fontSize: 11, width: "100%" }}>
                  <thead><tr><th>슬롯(θ)</th><th>응답 곡선</th><th>plateau score</th><th>고원 중심</th><th>폭</th><th>고원 평균손익</th><th>흑자율</th><th>절벽(최대 점프)</th><th>중심 형태(R²·정체일)</th>{tmap.compare && <th>비교 run(중심·score)</th>}</tr></thead>
                  <tbody>
                    {Object.entries(tmap.params)
                      .sort((a, b) => (b[1].plateau_score || 0) - (a[1].plateau_score || 0))
                      .map(([name, m]) => {
                        const cm = (tmap.compare && tmap.compare.params) ? tmap.compare.params[name] : null;
                        return (
                          <tr key={name}>
                            <td>{name}</td>
                            <td><_CurveSpark curve={m.curve} /></td>
                            <td>{_rlNum(m.plateau_score, 3)}</td>
                            <td>{m.plateau ? m.plateau.center_value : "—"}</td>
                            <td>{m.plateau ? m.plateau.width : "—"}</td>
                            <td>{m.plateau ? Math.round(m.plateau.mean_profit).toLocaleString() : "—"}</td>
                            <td>{Math.round((m.positive_ratio || 0) * 100)}%</td>
                            <td>{m.cliff ? `${Math.round(m.cliff.jump).toLocaleString()} @${m.cliff.between.join("→")}` : "—"}</td>
                            <td>{m.center_shape ? `${_rlNum(m.center_shape.uptrend_r2, 2)}·${m.center_shape.max_stagnation_days}일` : "—"}</td>
                            {tmap.compare && <td>{cm && cm.plateau ? `${cm.plateau.center_value} · ${_rlNum(cm.plateau_score, 2)}` : "—"}</td>}
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
                {tmap.compare && (
                  <div className="research-empty">
                    비교 run: {tmap.compare.run_id || "—"} — 구간별 경향 발산 확인용(M12). 다년 지도의 고원만 동결 자격.
                  </div>
                )}
              </div>
            )}
        </div>
      )}

      {grid && grid.count > 0 && (
        <div style={{ marginTop: 8 }}>
          <div className="research-empty" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span>
              {`2-D 격자 히트맵 (${grid.param_a} × ${grid.param_b}) — ★=mesa(4-이웃 전부 흑자) · 흑자율 ${Math.round((grid.positive_ratio || 0) * 100)}%`
                + (grid.baseline ? ` · 베이스라인 ${Math.round(grid.baseline.profit).toLocaleString()}` : "")}
            </span>
            <button type="button" className="research-tab"
                    onClick={() => setGridMetric(gridMetric === "profit" ? "mdd" : "profit")}>
              색: {gridMetric === "profit" ? "수익" : "MDD"}
            </button>
          </div>
          <_GridHeatmap grid={grid} metric={gridMetric} />
        </div>
      )}
      {grid && grid.count === 0 && (
        <div className="mono" style={{ fontSize: 11 }}>격자 run 아님(--grid 스윕 run_id를 입력하세요)</div>
      )}

      {/* 과업3(2026-06-12) — 파이프라인 체크포인트 패널 */}
      <_PipelineCheckpointPanel baseUrl={baseUrl} isDemo={isDemo} />

      {/* 과업2(2026-06-12) — 결합 시뮬(v0 균등가중) advisory 패널 */}
      <div style={{ marginTop: 10 }}>
        <div className="research-empty">결합 시뮬 (v0 균등가중) — advisory. 판정 미사용.</div>
        <div className="research-controls" style={{ marginTop: 4 }}>
          <label>
            <span>run 1</span>
            <input type="text" value={psimRun1} placeholder="run_id"
                   list="rl-run-options"
                   onChange={e => setPsimRun1(e.target.value)} style={{ width: 180 }} />
          </label>
          <label>
            <span>run 2</span>
            <input type="text" value={psimRun2} placeholder="run_id"
                   list="rl-run-options"
                   onChange={e => setPsimRun2(e.target.value)} style={{ width: 180 }} />
          </label>
          <button type="button" className="research-tab" onClick={fetchPsim}>결합 시뮬 실행</button>
        </div>
        {psim && !psim.error && (
          <div style={{ marginTop: 6 }}>
            <div className="mono" style={{ fontSize: 11 }}>
              결합 총손익: <b>{Math.round(psim.combined_total || 0).toLocaleString()}</b>
              {" · "}결합 MDD: <b>{Math.round(psim.combined_mdd || 0).toLocaleString()}</b>
              {psim.diversification_gain != null
                ? ` · 분산이득: ${(psim.diversification_gain * 100).toFixed(1)}%`
                : ""}
            </div>
            {psim.correlation && Array.isArray(psim.correlation.labels) && (
              <table className="mono" style={{ fontSize: 11, marginTop: 4 }}>
                <thead>
                  <tr>
                    <th>상관</th>
                    {psim.correlation.labels.map(l => <th key={l}>{l.split(":")[0]}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {psim.correlation.labels.map((row, i) => (
                    <tr key={row}>
                      <th>{row.split(":")[0]}</th>
                      {(psim.correlation.matrix[i] || []).map((v, j) => (
                        <td key={j}>{v.toFixed(2)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
        {psim && psim.error && (
          <div className="mono" style={{ fontSize: 11, color: "var(--amber)" }}>{psim.error}</div>
        )}
      </div>
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

/* E10(2026-06-13) — 진화 프로세스 플로우 오버레이(자족형).
   research-pro.jsx가 로드되면 더 풍부한 window.ResearchProcessFlowOverlay를 쓰지만,
   메인 앱(index.html)에는 research-pro.jsx가 없으므로 리서치랩이 자체 오버레이를
   포함해 어느 페이지에서도 '프로세스' 버튼이 동작하게 한다. 단계별 한국어 설명 +
   용어 사전(세대/격자/니치/OOS/동결)을 카드+화살표로 보여준다. */
// P4(2026-06-14): 진화 프로세스 7단계는 format.ts 의 정본 window.STOM_PIPELINE 로 통합(중복 제거).
//   research-pro 와 동일 정본 공유 — 과거 로컬 사본(터서 문구)은 삭제, 더 풍부한 정본 채택.
function _RlProcessFlowOverlay({ onClose, activeStage }) {
  const PIPELINE = window.STOM_PIPELINE || [];
  useEffect_rl(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const ai = typeof activeStage === "number" ? activeStage : -1;
  return (
    <div className="rp-overlay" onClick={onClose}>
      <div className="rp-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="rp-overlay-hd">
          <span className="rp-card-title">진화 프로세스 — 전체 흐름</span>
          {ai >= 0 && <span className="rp-card-sub">현재 단계: {PIPELINE[ai].title}</span>}
          <button type="button" className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕ 닫기 (Esc)
          </button>
        </div>
        <div className="rp-flow">
          {PIPELINE.map((s, i) => (
            <React.Fragment key={s.title}>
              <div className={"rp-flow-node" + (i === ai ? " rp-flow-active" : "")}>
                <div className="rp-flow-ico">{s.icon}</div>
                <div className="rp-flow-name">
                  {i + 1}. {s.title}
                  {i === ai && <span className="rp-flow-pulse"> ● 진행</span>}
                </div>
                <div className="rp-flow-desc">{s.desc}</div>
                <div className="rp-flow-terms">
                  {s.terms.map(([t, d]) => (
                    <div key={t} className="rp-flow-term"><b>{t}</b> {d}</div>
                  ))}
                </div>
              </div>
              {i < PIPELINE.length - 1 && <div className="rp-flow-arrow">→</div>}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
}

function ResearchLabPanel({ baseUrl, wsStatus, runId }) {
  const [tab, setTab] = useState_rl("edge");
  const [fullscreen, setFullscreen] = useState_rl(false);  /* 전체 화면 토글. */
  const [opsStrip, setOpsStrip] = useState_rl(null);       /* 탭 공통 운영 띠. */
  const [showFlow, setShowFlow] = useState_rl(false);      /* E10 — 프로세스 흐름 오버레이. */

  useEffect_rl(() => {
    if (!baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : null))
      .then(j => {
        setOpsStrip(j);
        try {  /* F7 — 정체 의심 시 브라우저 탭 제목 경고(자리 비움 감지용). */
          const stalled = ((j && j.active) || []).some(a => a.health !== "active");
          const base = document.title.replace(/^⚠️ /, "");
          document.title = (stalled ? "⚠️ " : "") + base;
        } catch (e) { /* 제목 갱신 실패는 무시. */ }
      })
      .catch(() => {});
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [baseUrl]);
  const [method, setMethod] = useState_rl("spearman");
  const [axis, setAxis] = useState_rl("time");
  const [data, setData] = useState_rl(null);
  const [loading, setLoading] = useState_rl(false);
  const [err, setErr] = useState_rl(null);

  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");
  const needsCorrelation = tab === "correlation" || tab === "combos";

  const refreshCorrelation = useCallback_rl(() => {
    if (!needsCorrelation || isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const url = baseUrl + "/variable_correlation?run_id=" + encodeURIComponent(runId)
      + "&method=" + encodeURIComponent(method);
    fetch(url, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, method, needsCorrelation, runId]);

  useEffect_rl(() => {
    refreshCorrelation();
  }, [refreshCorrelation]);

  const matrixRows = (data && Array.isArray(data.feature_matrix)) ? data.feature_matrix : [];
  const outcomeRows = (data && Array.isArray(data.outcome_correlations)) ? data.outcome_correlations : [];
  const rangeRows = (data && Array.isArray(data.range_summaries)) ? data.range_summaries : [];
  const segmentSummary = (data && data.segment_summaries) || {};
  const recencyResearch = (data && data.recency_research) || null;
  const pairRows = useMemo_rl(() => {
    const raw = (data && Array.isArray(data.interaction_candidates) && data.interaction_candidates.length)
      ? data.interaction_candidates
      : ((data && Array.isArray(data.top_pairs) && data.top_pairs.length) ? data.top_pairs : matrixRows);
    return [...raw].sort((a, b) => (
      (b.research_score || b.abs_correlation || Math.abs(b.correlation || 0))
      - (a.research_score || a.abs_correlation || Math.abs(a.correlation || 0))
    ));
  }, [data, matrixRows]);

  let body = null;
  if (tab === "edge") {
    body = <EdgeRatioPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />;
  } else if (tab === "validation") {
    body = <_ValidationPanel baseUrl={baseUrl} runId={runId} isDemo={isDemo} />;
  } else if (tab === "feature") {
    body = (
      <div>
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <FeatureImportancePanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
      </div>
    );
  } else if (isDemo || !runId) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="상관 분석을 표시할 run 컨텍스트가 부족합니다." /></div>;
  } else if (err) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message={"응답을 받지 못했습니다: " + err} /></div>;
  } else if (loading && !data) {
    body = <div className="research-lab-panel"><_ResearchEmptyState message="상관 분석을 불러오는 중…" /></div>;
  } else if (tab === "correlation") {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CorrelationHeatmap rows={matrixRows.length ? matrixRows : outcomeRows} />
        <_RangeSummaryList rows={rangeRows} />
        <_SegmentSummaryList summary={segmentSummary} axis={axis} />
        <_RecencyResearchBadge recency={recencyResearch} />
      </div>
    );
  } else {
    body = (
      <div className="research-lab-panel">
        <_CorrelationControls method={method} setMethod={setMethod} axis={axis} setAxis={setAxis}
                              loading={loading} pooledTrades={data && data.pooled_trades}
                              featureCount={data && data.feature_count} />
        <_CombinationList rows={pairRows} />
      </div>
    );
  }

  const shellStyle = fullscreen
    ? { position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 9999,
        background: "#0d1117", overflow: "auto", padding: "12px 18px" }
    : undefined;
  const activeOps = (opsStrip && opsStrip.active) || [];
  const recentOps = (opsStrip && opsStrip.recent) || [];
  /* E1 — '모드/대상' 라벨을 명시(이전엔 "운영 연구 결과"류 평문이라 의미 불명). */
  const labMode = activeOps.length ? "운영(실행 중)" : "연구(분석)";
  /* E10 — 활성 단계 추정: 실행 중 작업이 있으면 백테 평가(3) 단계로 강조, 없으면 정적(-1). */
  const flowActiveStage = activeOps.length ? 3 : -1;
  return (
    <div className="research-lab-shell" style={shellStyle}>
      <div className="research-tabs" role="tablist" aria-label="Research Lab"
           style={{ display: "flex", alignItems: "center" }}>
        {RESEARCH_TABS.map(item => (
          <button key={item.id}
                  type="button"
                  className={"research-tab" + (tab === item.id ? " active" : "")}
                  onClick={() => setTab(item.id)}>
            {item.label}
          </button>
        ))}
        {/* E10 — 진화 전체 프로세스를 흐름으로 보는 오버레이(자족형, 어느 페이지에서도 동작). */}
        <button type="button" className="research-tab" style={{ marginLeft: "auto" }}
                title="시드→생성→격자→백테→게이트→OOS→동결 전체 흐름과 용어 보기"
                onClick={() => setShowFlow(true)}>
          🧭 프로세스
        </button>
        {/* E2 — 리서치 프로(전체화면 분석)를 새 탭으로. */}
        <a className="research-tab" href="/ui/pro.html" target="_blank" rel="noopener"
           style={{ textDecoration: "none" }}
           title="화면 전체를 쓰는 상세 분석 워크스페이스(히트맵·명예의전당·비교·히스토리)">
          🔬 리서치 프로
        </a>
        <button type="button" className="research-tab"
                onClick={() => setFullscreen(!fullscreen)}>
          {fullscreen ? "✕ 전체 화면 닫기" : "⛶ 전체 화면"}
        </button>
      </div>
      {/* E1 — 평문 대신 라벨+값+툴팁 상태 배지 바. */}
      <div className="research-statusbar mono">
        <span className="research-badge" title="현재 리서치랩 모드 — 실행 중 run이 있으면 '운영', 없으면 '연구(분석)'.">
          <b>모드</b> {labMode}
        </span>
        <span className="research-badge" title="이 패널이 보여주는 대상 — 분석 중인 run/세대 결과의 건수.">
          <b>대상</b> 실행 {activeOps.length}건 · 최근완료 {recentOps.length}건
        </span>
        {activeOps.length
          ? activeOps.map(a => (
              <span key={a.run_id} className="research-badge"
                    title={`run ${a.run_id} · ${a.gens}세대 · 마지막 ${a.last_label || "—"} · ${a.health === "active" ? "정상 진행" : "10분+ 무진행(정체 의심)"}`}>
                <b>{a.health === "active" ? "🔄 진행" : "⚠️ 정체"}</b> {a.run_id} · {a.gens}세대
              </span>
            ))
          : (
            <span className="research-badge" title="현재 실행 중인 진화 작업이 없습니다(분석 전용).">
              <b>상태</b> 실행 중 작업 없음
            </span>
          )}
      </div>
      {body}
      {/* E10 — research-pro.jsx가 로드된 페이지면 더 풍부한 전역 오버레이를, 아니면 자족형. */}
      {showFlow && (typeof window.ResearchProcessFlowOverlay === "function"
        ? React.createElement(window.ResearchProcessFlowOverlay, {
            onClose: () => setShowFlow(false),
            liveState: activeOps.length ? { status: "running" } : null,
            ops: opsStrip,
          })
        : <_RlProcessFlowOverlay onClose={() => setShowFlow(false)} activeStage={flowActiveStage} />)}
    </div>
  );
}

Object.assign(window, { ResearchLabPanel });
