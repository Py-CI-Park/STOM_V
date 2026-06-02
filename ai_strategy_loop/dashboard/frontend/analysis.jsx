/* EdgeRatioPanel + FeatureImportancePanel — AI Strategy Loop 분석 패널.
   백엔드 /edge_ratio·/feature_importance REST 엔드포인트를 fetch해 시각화한다.
   - 백엔드 파일 무수정(프론트 전용).
   - ErrorBoundary 호환: 패널 단독 크래시가 전체 화면 검게 되지 않도록 window.ErrorBoundary에
     감싸 등록하지 않고 패널 내부에서 자체 에러 상태를 관리한다.
   - 데이터 없음/로딩/에러 각각 친절한 빈 상태를 표시한다. */

const {
  useState: useState_an,
  useEffect: useEffect_an,
  useCallback: useCallback_an,
  useMemo: useMemo_an,
} = React;

/* ── 내부 유틸 ─────────────────────────────────────────────────────────── */

function _anNum(x, digits) {
  if (typeof x !== "number" || !isFinite(x)) return "—";
  return x.toFixed(digits != null ? digits : 3);
}

/* edge_ratio 값을 0~2 사이 발산색으로 변환.
   1.0 기준: 1.0 = 중립(흰색에 가까움), >1 = teal(양), <1 = amber/red(음). */
function _edgeColor(v, alpha) {
  if (typeof v !== "number" || !isFinite(v)) return `rgba(80,100,120,${alpha || 0.5})`;
  const delta = v - 1.0;
  if (delta >= 0) {
    // 양: teal 계열. 강도 0~1 (최대 delta=1.0 기준).
    const t = Math.min(1, delta);
    const r = Math.round(20 + (1 - t) * 80);
    const g = Math.round(100 + t * 114);
    const b = Math.round(100 + t * 79);
    return `rgba(${r},${g},${b},${alpha || 0.85})`;
  } else {
    // 음: amber → red 계열.
    const t = Math.min(1, -delta);
    const r = Math.round(200 + t * 55);
    const g = Math.round(Math.round(179 * (1 - t)));
    return `rgba(${r},${g},40,${alpha || 0.85})`;
  }
}

/* Cohen's d 부호에 따른 색: 양=teal, 음=amber */
function _cohensColor(d) {
  if (typeof d !== "number" || !isFinite(d)) return "var(--ink-3)";
  return d >= 0 ? "var(--teal)" : "var(--amber)";
}

/* ── 빈 상태 공통 컴포넌트 ──────────────────────────────────────────────── */
function _EmptyState({ msg }) {
  return (
    <div style={{
      padding: "28px 18px",
      color: "var(--ink-3)",
      fontSize: 12,
      fontFamily: "var(--mono)",
      lineHeight: 1.7,
      textAlign: "center",
    }}>
      {msg}
    </div>
  );
}

/* ── EdgeRatioPanel ─────────────────────────────────────────────────────── */
/*
   /edge_ratio?run_ids=<>&fine_time=true 응답:
   {
     global: { edge_ratio, mae_efficiency, win_rate, trade_count, ... },
     segments: {
       market_cap: [{label, count, win_rate, edge_ratio, ...}],
       time:       [{label, count, win_rate, edge_ratio, ...}],
       cross:      [{label, edge_ratio, count, win_rate, ...}],
       change:     [{label, edge_ratio, count, ...}],
     }
   }
*/
function EdgeRatioPanel({ baseUrl, wsStatus, runId }) {
  const [data, setData] = useState_an(null);
  const [loading, setLoading] = useState_an(false);
  const [err, setErr] = useState_an(null);

  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_an(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const url = baseUrl + "/edge_ratio?run_ids=" + encodeURIComponent(runId) + "&fine_time=true";
    fetch(url, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId]);

  useEffect_an(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const global_ = (data && data.global) || {};
  const segs = (data && data.segments) || {};
  const crossSegs = (segs.cross) || [];
  const changeSegs = (segs.change) || [];
  const timeSegs = (segs.time) || [];
  const capSegs = (segs.market_cap) || [];

  /* 히트맵: time 행 × market_cap 열 교차 grid.
     cross 세그먼트 label 은 "<time>×<cap>" 형식으로 온다(백엔드 관행).
     파싱 실패 시 cross를 단순 목록으로 fallback. */
  const heatmap = useMemo_an(() => {
    if (!crossSegs.length) return null;
    const timeLabels = [];
    const capLabels = [];
    const cellMap = {};
    for (const c of crossSegs) {
      const parts = (c.label || "").split("×");
      const tl = parts[0] ? parts[0].trim() : c.label;
      const cl = parts[1] ? parts[1].trim() : "";
      if (!timeLabels.includes(tl)) timeLabels.push(tl);
      if (cl && !capLabels.includes(cl)) capLabels.push(cl);
      cellMap[tl + "×" + cl] = c;
    }
    // fallback: cross label에 "×" 없으면 단순 목록으로
    if (capLabels.length === 0) return null;
    return { timeLabels, capLabels, cellMap };
  }, [crossSegs]);

  const hasData = data && (
    typeof global_.edge_ratio === "number" || crossSegs.length > 0 || changeSegs.length > 0
  );

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--teal)" }}></span>
          Edge Ratio 분석
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
            시간대×시총 히트맵 · 등락률 축
          </span>
          <button className="btn ghost sm" onClick={refresh}
                  disabled={isDemo || loading || !runId}
                  data-tip="edge_ratio 새로고침">
            {loading ? "조회중…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <_EmptyState msg="데모 모드 — Edge Ratio 분석은 라이브 실행에서 발행됩니다." />
        ) : !runId ? (
          <_EmptyState msg="run을 선택하거나 루프를 시작하면 Edge Ratio 분석이 표시됩니다." />
        ) : err ? (
          <_EmptyState msg={"조회 실패 — " + err} />
        ) : !hasData ? (
          <_EmptyState msg={"세대 데이터가 누적되면 Edge Ratio 분석이 표시됩니다." + (loading ? " (로딩중…)" : "")} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {/* ① 글로벌 지표 */}
            {(typeof global_.edge_ratio === "number" || typeof global_.mae_efficiency === "number") && (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 8, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  글로벌 지표
                </div>
                <div style={{ display: "flex", gap: 20, flexWrap: "wrap" }}>
                  {typeof global_.edge_ratio === "number" && (
                    <_EdgeStat label="Edge Ratio" value={_anNum(global_.edge_ratio, 3)}
                               color={_edgeColor(global_.edge_ratio, 1)} hint="1.0 기준: 높을수록 유리" />
                  )}
                  {typeof global_.mae_efficiency === "number" && (
                    <_EdgeStat label="MAE Efficiency" value={_anNum(global_.mae_efficiency, 3)}
                               color={global_.mae_efficiency >= 0 ? "var(--teal)" : "var(--amber)"}
                               hint="평균 불리 노출 효율(높을수록 적은 역방향 노출)" />
                  )}
                  {typeof global_.win_rate === "number" && (
                    <_EdgeStat label="승률" value={_anNum(global_.win_rate * 100, 1) + "%"}
                               color="var(--ink-0)" />
                  )}
                  {typeof global_.trade_count === "number" && (
                    <_EdgeStat label="거래수" value={String(global_.trade_count)} color="var(--ink-2)" />
                  )}
                </div>
              </div>
            )}

            {/* ② 시간대×시총 크로스 히트맵 */}
            {heatmap ? (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 8, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  시간대 × 시총 교차 히트맵 (edge_ratio · 1.0 기준 발산색)
                </div>
                <_Heatmap heatmap={heatmap} />
              </div>
            ) : crossSegs.length > 0 ? (
              /* fallback: cross 목록 */
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  교차 세그먼트
                </div>
                <_SegBarList segs={crossSegs} />
              </div>
            ) : null}

            {/* ③ 등락률 축 막대 */}
            {changeSegs.length > 0 && (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  등락률 구간별 edge_ratio
                </div>
                <_SegBarList segs={changeSegs} />
              </div>
            )}

            {/* ④ 시간대 단독(크로스 없을 때) */}
            {!crossSegs.length && timeSegs.length > 0 && (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  시간대별 edge_ratio
                </div>
                <_SegBarList segs={timeSegs} />
              </div>
            )}

            {/* ⑤ 시총 단독(크로스 없을 때) */}
            {!crossSegs.length && capSegs.length > 0 && (
              <div>
                <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginBottom: 6, letterSpacing: ".1em", textTransform: "uppercase" }}>
                  시총 밴드별 edge_ratio
                </div>
                <_SegBarList segs={capSegs} />
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}

/* 글로벌 지표 카드 */
function _EdgeStat({ label, value, color, hint }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}
         title={hint || ""}>
      <span style={{ fontSize: 10, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", fontFamily: "var(--mono)" }}>
        {label}
      </span>
      <span className="mono" style={{ fontSize: 18, color: color || "var(--ink-0)" }}>
        {value}
      </span>
    </div>
  );
}

/* 히트맵 SVG(시간대행 × 시총열) */
function _Heatmap({ heatmap }) {
  const { timeLabels, capLabels, cellMap } = heatmap;
  const cellW = 72, cellH = 30;
  const labelColW = 80, labelRowH = 26;
  const W = labelColW + capLabels.length * cellW;
  const H = labelRowH + timeLabels.length * cellH;

  return (
    <div style={{ overflowX: "auto" }}>
      <svg viewBox={`0 0 ${W} ${H}`}
           style={{ width: "100%", maxWidth: W, display: "block" }}
           preserveAspectRatio="xMinYMin meet">
        {/* 열 라벨 (시총) */}
        {capLabels.map((cl, ci) => (
          <text key={"ch" + ci}
                x={labelColW + ci * cellW + cellW / 2}
                y={labelRowH - 6}
                textAnchor="middle"
                style={{ fontSize: 9, fill: "var(--ink-3)", fontFamily: "var(--mono)" }}>
            {cl.length > 8 ? cl.slice(0, 8) + "…" : cl}
          </text>
        ))}
        {/* 행 라벨 + 셀 */}
        {timeLabels.map((tl, ti) => (
          <g key={"tr" + ti}>
            {/* 행 라벨 (시간대) */}
            <text x={labelColW - 4}
                  y={labelRowH + ti * cellH + cellH / 2 + 4}
                  textAnchor="end"
                  style={{ fontSize: 9.5, fill: "var(--ink-2)", fontFamily: "var(--mono)" }}>
              {tl.length > 9 ? tl.slice(0, 9) + "…" : tl}
            </text>
            {capLabels.map((cl, ci) => {
              const cell = cellMap[tl + "×" + cl];
              const er = cell ? cell.edge_ratio : null;
              const bg = er != null ? _edgeColor(er, 0.82) : "rgba(40,50,60,0.4)";
              const textColor = er != null ? (Math.abs(er - 1) > 0.15 ? "#fff" : "var(--ink-1)") : "var(--ink-3)";
              const cx = labelColW + ci * cellW;
              const cy = labelRowH + ti * cellH;
              return (
                <g key={"c" + ci}>
                  <rect x={cx + 1} y={cy + 1} width={cellW - 2} height={cellH - 2}
                        rx="3" fill={bg} />
                  <text x={cx + cellW / 2} y={cy + cellH / 2 + 4}
                        textAnchor="middle"
                        style={{ fontSize: 9.5, fill: textColor, fontFamily: "var(--mono)", fontWeight: 600 }}>
                    {er != null ? _anNum(er, 2) : "—"}
                  </text>
                  {cell && typeof cell.count === "number" && (
                    <text x={cx + cellW / 2} y={cy + cellH - 4}
                          textAnchor="middle"
                          style={{ fontSize: 7.5, fill: "rgba(255,255,255,0.45)", fontFamily: "var(--mono)" }}>
                      {cell.count}건
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        ))}
      </svg>
    </div>
  );
}

/* 세그먼트 목록 수평 막대 */
function _SegBarList({ segs }) {
  if (!segs || !segs.length) return null;
  const maxAbsDelta = segs.reduce((m, s) => {
    const d = typeof s.edge_ratio === "number" ? Math.abs(s.edge_ratio - 1) : 0;
    return Math.max(m, d);
  }, 0.01);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
      {segs.map((s, i) => {
        const er = typeof s.edge_ratio === "number" ? s.edge_ratio : null;
        const delta = er != null ? er - 1 : 0;
        const barFrac = er != null ? Math.abs(delta) / (maxAbsDelta || 1) : 0;
        const barW = Math.max(2, Math.round(barFrac * 120));
        const barColor = _edgeColor(er != null ? er : 1, 0.85);
        return (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)", minWidth: 90, flexShrink: 0 }}>
              {s.label || "—"}
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <div style={{
                width: barW, height: 12, borderRadius: 3,
                background: barColor, flexShrink: 0,
              }} />
              <span className="mono" style={{ fontSize: 11, color: barColor, minWidth: 42 }}>
                {er != null ? _anNum(er, 3) : "—"}
              </span>
            </div>
            {typeof s.win_rate === "number" && (
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
                승률 {_anNum(s.win_rate * 100, 1)}%
              </span>
            )}
            {typeof s.count === "number" && (
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>
                {s.count}건
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ── FeatureImportancePanel ──────────────────────────────────────────────── */
/*
   /feature_importance?run_ids=<>&axis=<axis>&fine_time=true 응답:
   {
     global: [{feature, cohens_d, mean_pass, mean_fail, ...}],
     by_segment: { "<segLabel>": [{feature, cohens_d, ...}] }
   }
*/
function FeatureImportancePanel({ baseUrl, wsStatus, runId }) {
  const [data, setData] = useState_an(null);
  const [loading, setLoading] = useState_an(false);
  const [err, setErr] = useState_an(null);
  const [axis, setAxis] = useState_an("time");       // time | market_cap | change
  const [selSeg, setSelSeg] = useState_an(null);      // 선택된 세그먼트 라벨(null=global)

  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const refresh = useCallback_an(() => {
    if (isDemo || !baseUrl || !runId) return;
    setLoading(true);
    const url = baseUrl + "/feature_importance?run_ids=" + encodeURIComponent(runId)
      + "&axis=" + encodeURIComponent(axis) + "&fine_time=true";
    fetch(url, { signal: AbortSignal.timeout(5000) })
      .then(r => r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status)))
      .then(j => { setData(j); setErr(null); setSelSeg(null); })
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [baseUrl, isDemo, runId, axis]);

  useEffect_an(() => {
    refresh();
    const id = setInterval(refresh, 30000);
    return () => clearInterval(id);
  }, [refresh]);

  const globalFeats = (data && Array.isArray(data.global)) ? data.global : [];
  const bySeg = (data && data.by_segment) ? data.by_segment : {};
  const segKeys = Object.keys(bySeg);

  /* 표시할 피처 목록: 선택 세그먼트 우선, 없으면 global. |d| 내림차순. */
  const activeFeats = useMemo_an(() => {
    const raw = (selSeg && bySeg[selSeg]) ? bySeg[selSeg] : globalFeats;
    return [...raw].sort((a, b) => Math.abs(b.cohens_d || 0) - Math.abs(a.cohens_d || 0));
  }, [selSeg, bySeg, globalFeats]);

  const maxAbsD = activeFeats.reduce((m, f) => Math.max(m, Math.abs(f.cohens_d || 0)), 0.01);

  const hasData = data && (globalFeats.length > 0 || segKeys.length > 0);

  /* 축 토글 버튼 */
  const _AxisBtn = ({ val, label }) => (
    <button
      onClick={() => { setAxis(val); setSelSeg(null); }}
      className="btn ghost sm"
      style={{
        fontFamily: "var(--mono)",
        fontSize: 10.5,
        padding: "3px 9px",
        background: axis === val ? "rgba(76,214,179,0.12)" : "transparent",
        border: axis === val ? "1px solid var(--teal)" : "1px solid var(--line-2)",
        color: axis === val ? "var(--teal)" : "var(--ink-3)",
      }}>
      {label}
    </button>
  );

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          Feature Importance 분석
          {isDemo && typeof window.DemoBadge === "function" && <window.DemoBadge />}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          <_AxisBtn val="time" label="시간대" />
          <_AxisBtn val="market_cap" label="시총" />
          <_AxisBtn val="change" label="등락률" />
          <button className="btn ghost sm" onClick={refresh}
                  disabled={isDemo || loading || !runId}
                  data-tip="feature importance 새로고침">
            {loading ? "조회중…" : "↻ 새로고침"}
          </button>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <_EmptyState msg="데모 모드 — Feature Importance 분석은 라이브 실행에서 발행됩니다." />
        ) : !runId ? (
          <_EmptyState msg="run을 선택하거나 루프를 시작하면 Feature Importance 분석이 표시됩니다." />
        ) : err ? (
          <_EmptyState msg={"조회 실패 — " + err} />
        ) : !hasData ? (
          <_EmptyState msg={"세대 데이터가 누적되면 Feature Importance 분석이 표시됩니다." + (loading ? " (로딩중…)" : "")} />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>

            {/* 세그먼트 탭 */}
            {segKeys.length > 0 && (
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                <button
                  onClick={() => setSelSeg(null)}
                  className="btn ghost sm"
                  style={{
                    fontFamily: "var(--mono)", fontSize: 10.5, padding: "2px 8px",
                    background: selSeg === null ? "rgba(165,148,255,0.12)" : "transparent",
                    border: selSeg === null ? "1px solid var(--violet)" : "1px solid var(--line-2)",
                    color: selSeg === null ? "var(--violet)" : "var(--ink-3)",
                  }}>
                  전체
                </button>
                {segKeys.map(k => (
                  <button key={k}
                    onClick={() => setSelSeg(k)}
                    className="btn ghost sm"
                    style={{
                      fontFamily: "var(--mono)", fontSize: 10.5, padding: "2px 8px",
                      background: selSeg === k ? "rgba(165,148,255,0.12)" : "transparent",
                      border: selSeg === k ? "1px solid var(--violet)" : "1px solid var(--line-2)",
                      color: selSeg === k ? "var(--violet)" : "var(--ink-3)",
                    }}>
                    {k.length > 14 ? k.slice(0, 14) + "…" : k}
                  </button>
                ))}
              </div>
            )}

            {/* 안내 문구 */}
            <div style={{ fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
              Cohen's d: 통과/탈락 세대 간 피처 분포 차이. 양(teal)=통과세대 더 높음, 음(amber)=낮을수록 통과. |d|↓ 정렬.
            </div>

            {/* 수평 막대 차트 */}
            {activeFeats.length === 0 ? (
              <_EmptyState msg="이 세그먼트에 피처 데이터가 없습니다." />
            ) : (
              <_FeatureBarChart feats={activeFeats} maxAbsD={maxAbsD} />
            )}

          </div>
        )}
      </div>
    </div>
  );
}

/* 피처별 수평막대(Cohen's d · 부호 색) */
function _FeatureBarChart({ feats, maxAbsD }) {
  const BAR_MAX_W = 180; // px 기준 최대 막대 폭

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {feats.map((f, i) => {
        const d = typeof f.cohens_d === "number" ? f.cohens_d : 0;
        const absD = Math.abs(d);
        const frac = absD / (maxAbsD || 1);
        const barW = Math.max(2, Math.round(frac * BAR_MAX_W));
        const barColor = _cohensColor(d);
        const featureLabel = f.feature || f.name || ("feature_" + i);

        return (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "3px 0",
            borderBottom: i < feats.length - 1 ? "1px solid var(--bg-2)" : "none",
          }}>
            {/* 피처 이름 */}
            <span className="mono" style={{
              fontSize: 11, color: "var(--ink-1)",
              minWidth: 140, maxWidth: 180, overflow: "hidden",
              textOverflow: "ellipsis", whiteSpace: "nowrap", flexShrink: 0,
            }}
              title={featureLabel}>
              {featureLabel}
            </span>

            {/* 막대: 0 중심, 부호 방향 */}
            <div style={{ display: "flex", alignItems: "center", gap: 2, minWidth: BAR_MAX_W * 2 + 10 }}>
              {/* 음수 영역(왼쪽) */}
              <div style={{ width: BAR_MAX_W, display: "flex", justifyContent: "flex-end" }}>
                {d < 0 && (
                  <div style={{
                    width: barW, height: 12, borderRadius: "3px 0 0 3px",
                    background: barColor, opacity: 0.85,
                  }} />
                )}
              </div>
              {/* 0 기준선 */}
              <div style={{ width: 1, height: 14, background: "var(--line-2)", flexShrink: 0 }} />
              {/* 양수 영역(오른쪽) */}
              <div style={{ width: BAR_MAX_W }}>
                {d >= 0 && (
                  <div style={{
                    width: barW, height: 12, borderRadius: "0 3px 3px 0",
                    background: barColor, opacity: 0.85,
                  }} />
                )}
              </div>
            </div>

            {/* d 값 */}
            <span className="mono" style={{
              fontSize: 11, color: barColor, minWidth: 52, textAlign: "right",
            }}>
              {d >= 0 ? "+" : ""}{_anNum(d, 3)}
            </span>

            {/* 보조 지표(mean_pass/mean_fail) */}
            {typeof f.mean_pass === "number" && typeof f.mean_fail === "number" && (
              <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
                통과 {_anNum(f.mean_pass, 2)} / 탈락 {_anNum(f.mean_fail, 2)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { EdgeRatioPanel, FeatureImportancePanel });
