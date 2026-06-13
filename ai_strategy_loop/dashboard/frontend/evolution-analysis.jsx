/* 진화 대시보드 — 결과 분석 시각화 패널 (트랙 L).
   선택 run 의 세대 데이터를 백테스트 탭 수준의 시각화로 보여준다:
     1) 세대 진화 다중지표 차트(score·profit·mdd·trade_count 멀티라인, 정규화 토글, 게이트 마커)
     2) 세대 산점도(x=mdd, y=profit, 색=gate, 호버 상세) — '니치 지도' 스타일
     3) 세대 비교 미니 테이블(상위 N + [워크벤치 분석] 버튼 → 백테탭 evoSource 연동)

   데이터: GET /bt/evo_gens?run_id= 재사용(읽기 전용, LoopState readonly). 기본 run = 현재 runId.
   디자인 언어: chart.jsx 의 순수 SVG(외부 차트 라이브러리 금지) · panel/panel-hd/panel-bd 클래스 ·
     CSS 변수 색(var(--teal)/var(--violet)/var(--blue)/var(--red)) · mono 라벨. 전역 헬퍼
     (fmtScore/fmtPct/fmtMoney/fmtInt/Mini/LegendDot)는 connection.jsx·chart.jsx 가 먼저 로드해
     window 에 올린 것을 그대로 쓴다.

   워크벤치 연동(느슨 결합): [워크벤치 분석]은 backtest.jsx 를 직접 import 하지 않고
     CustomEvent("stom:bt-evo-select", {detail:{run_id, gen_no}})를 window 에 발행 + 선택을
     localStorage(stom_bt_evo_pending)에 적재한 뒤, app.jsx 가 내려준 onOpenWorkbench 로 탭만
     전환한다(직접 상태 결합 없음). */
const {
  useState: useState_ea, useEffect: useEffect_ea,
  useMemo: useMemo_ea, useRef: useRef_ea, useCallback: useCallback_ea,
} = React;

// 무예외 fetch — 실패 시 거부를 호출측 catch 로 흘린다(빈 상태 + 무크래시).
function _eaFetchJson(url, timeoutMs) {
  return fetch(url, { signal: AbortSignal.timeout(timeoutMs || 5000) })
    .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))));
}

// 안전 포매터 — 전역(window) 헬퍼가 아직 없을 극단 케이스 대비 로컬 폴백.
const _fScore = (v) => (typeof window.fmtScore === "function" ? window.fmtScore(v)
  : (typeof v === "number" ? v.toFixed(3) : "—"));
const _fPct = (v) => (typeof window.fmtPct === "function" ? window.fmtPct(v)
  : (typeof v === "number" ? v.toFixed(2) + "%" : "—"));
const _fMoney = (v) => (typeof window.fmtMoney === "function" ? window.fmtMoney(v)
  : (typeof v === "number" ? v.toLocaleString("ko-KR") + "원" : "—"));
const _fInt = (v) => (typeof window.fmtInt === "function" ? window.fmtInt(v)
  : (typeof v === "number" ? v.toLocaleString("ko-KR") : "—"));

// 지표 메타 — 멀티라인 차트의 계열 정의(키·라벨·색·포맷·정규화 시 방향).
//   mdd 는 작을수록 좋으므로 정규화 라벨에 (역) 표기만 한다(값 반전은 하지 않음 — 원형 유지).
const EA_SERIES = [
  { key: "score", label: "score", color: "var(--teal)", fmt: _fScore },
  { key: "profit", label: "profit", color: "var(--violet)", fmt: _fMoney },
  { key: "mdd", label: "mdd(%)", color: "var(--red)", fmt: _fPct },
  { key: "trade_count", label: "trades", color: "var(--blue)", fmt: _fInt },
];

// 빈 차트/패널 공통 플레이스홀더.
function EaEmpty({ text }) {
  return (
    <div style={{
      position: "absolute", inset: 0,
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "var(--ink-3)", fontSize: 12, fontFamily: "var(--mono)",
    }}>
      {text}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 1) 세대 진화 다중지표 차트 — gen 별 score·profit·mdd·trade_count 멀티라인.
//    정규화 토글: ON 이면 각 계열을 자기 min/max 로 [0,1] 스케일해 같은 축에 겹쳐 그린다.
//    OFF 면 첫 계열(score)만 원축으로(스케일 상이 → 동시 비교 무의미하므로) 그린다.
//    게이트 통과 세대는 하단 X 축에 마커(▲)로 표시.
// ---------------------------------------------------------------------------
function EaMultiMetricChart({ gens, normalize }) {
  const W = 880, H = 320;
  const padL = 46, padR = 24, padT = 18, padB = 34;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const nums = gens.filter(g => g.gen_no >= 0);
  const xMax = Math.max(8, ...nums.map(g => g.gen_no + 1));
  const x = (g) => padL + (g + 0.5) / xMax * innerW;

  // 계열별 [min,max] — 정규화 스케일 기준.
  const ranges = useMemo_ea(() => {
    const r = {};
    for (const s of EA_SERIES) {
      const vals = nums.map(g => (typeof g[s.key] === "number" ? g[s.key] : 0));
      const mn = Math.min(0, ...vals), mx = Math.max(1, ...vals);
      r[s.key] = { mn, mx, span: (mx - mn) || 1 };
    }
    return r;
  }, [nums]);

  // 정규화 모드: 값 → [0,1]. 비정규화: score 만 자기 범위로.
  const yNorm = (v, key) => {
    const rg = ranges[key];
    const t = (v - rg.mn) / rg.span;
    return padT + innerH - t * innerH;
  };
  const activeSeries = normalize ? EA_SERIES : [EA_SERIES[0]];

  const paths = useMemo_ea(() => {
    return activeSeries.map(s => {
      if (nums.length === 0) return { key: s.key, d: "" };
      const d = nums.map((g, i) =>
        `${i === 0 ? "M" : "L"} ${x(g.gen_no).toFixed(2)} ${yNorm(typeof g[s.key] === "number" ? g[s.key] : 0, s.key).toFixed(2)}`
      ).join(" ");
      return { key: s.key, d, color: s.color };
    });
  }, [nums, xMax, normalize, ranges]);

  // X 눈금(chart.jsx 규칙).
  const xStep = xMax <= 15 ? 1 : xMax <= 30 ? 2 : 5;
  const xTicks = [];
  for (let g = 0; g < xMax; g++) {
    if (g === 0 || g === xMax - 1 || g % xStep === 0) xTicks.push(g);
  }

  const [hover, setHover] = useState_ea(null);
  const svgRef = useRef_ea(null);
  const onMove = (e) => {
    if (!nums.length || !svgRef.current) return;
    const rect = svgRef.current.getBoundingClientRect();
    const px = (e.clientX - rect.left) * (W / rect.width);
    let best = null, bestDist = Infinity;
    for (const g of nums) {
      const d = Math.abs(x(g.gen_no) - px);
      if (d < bestDist) { bestDist = d; best = g; }
    }
    setHover(best && bestDist < 40 ? best : null);
  };

  return (
    <div className="chart-wrap" style={{ position: "relative" }}>
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
           onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        {/* Y 그리드(정규화 0/0.5/1, 비정규화 score 눈금) */}
        {(normalize ? [0, 0.25, 0.5, 0.75, 1] : [0, 0.5, 1]).map((t, i) => {
          const yy = normalize ? padT + innerH - t * innerH : yNorm(t, "score");
          return (
            <g key={`g${i}`}>
              <line className="chart-grid-line" x1={padL} x2={W - padR} y1={yy} y2={yy} />
              <text className="chart-axis-text" x={padL - 8} y={yy + 3} textAnchor="end">
                {normalize ? t.toFixed(2) : t.toFixed(1)}
              </text>
            </g>
          );
        })}
        {/* X 눈금 */}
        {xTicks.map((g, i) => (
          <text key={`x${i}`} className="chart-axis-text" x={x(g)} y={H - 14} textAnchor="middle">
            g{g}
          </text>
        ))}
        {/* 프레임 */}
        <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
        <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
        {/* 계열 라인 */}
        {nums.length > 1 && paths.map(p => (
          <path key={p.key} d={p.d} fill="none" stroke={p.color} strokeWidth="1.6"
                strokeLinejoin="round" strokeLinecap="round" opacity="0.92" />
        ))}
        {/* 게이트 통과 마커(하단 ▲) */}
        {nums.map((g, i) => g.gate_passed ? (
          <path key={`m${i}`}
                d={`M ${x(g.gen_no)} ${padT + innerH + 2} l 4 7 l -8 0 Z`}
                fill="var(--teal)" opacity="0.9" />
        ) : null)}
        {/* 호버 가이드 */}
        {hover && (
          <line x1={x(hover.gen_no)} x2={x(hover.gen_no)} y1={padT} y2={padT + innerH}
                stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
        )}
      </svg>

      {hover && (
        <div style={{
          position: "absolute", top: 14, right: 14,
          background: "var(--bg-0)", border: "1px solid var(--line-2)", borderRadius: 6,
          padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 190,
          boxShadow: "0 6px 16px rgba(0,0,0,0.4)",
        }}>
          <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 }}>
            gen_{String(hover.gen_no).padStart(2, "0")}
            {hover.gate_passed && <span style={{ color: "var(--teal)", marginLeft: 6 }}>✓</span>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
            {EA_SERIES.map(s => (
              <React.Fragment key={s.key}>
                <span style={{ color: s.color }}>{s.label}</span>
                <span>{s.fmt(hover[s.key])}</span>
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {nums.length === 0 && <EaEmpty text="세대 데이터가 없습니다" />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 2) 세대 산점도 — x=mdd, y=profit, 색=gate(통과 teal / 탈락 ink). '니치 지도' 스타일.
//    호버 시 gen·score·mdd·profit·trades 상세. 0 손익선(y=0)을 강조.
// ---------------------------------------------------------------------------
function EaScatterChart({ gens }) {
  const W = 880, H = 360;
  const padL = 64, padR = 24, padT = 18, padB = 40;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;

  const pts = gens.filter(g => g.gen_no >= 0 && g.status !== "error");

  const mddVals = pts.map(p => (typeof p.mdd === "number" ? p.mdd : 0));
  const profVals = pts.map(p => (typeof p.profit === "number" ? p.profit : 0));
  const mddMax = Math.max(1, ...mddVals);
  const profMax = Math.max(0, ...profVals);
  const profMin = Math.min(0, ...profVals);
  const profSpan = (profMax - profMin) || 1;

  const x = (mdd) => padL + (mdd / mddMax) * innerW;
  const y = (p) => padT + innerH - ((p - profMin) / profSpan) * innerH;

  // 눈금.
  const xTicks = useMemo_ea(() => {
    const out = []; const step = mddMax <= 10 ? 2 : mddMax <= 30 ? 5 : 10;
    for (let v = 0; v <= mddMax + 1e-9; v += step) out.push(+v.toFixed(1));
    return out;
  }, [mddMax]);
  const yTicks = useMemo_ea(() => {
    const out = []; const step = profSpan / 4;
    for (let i = 0; i <= 4; i++) out.push(profMin + step * i);
    return out;
  }, [profMin, profSpan]);

  const [hover, setHover] = useState_ea(null);

  return (
    <div className="chart-wrap" style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
           onMouseLeave={() => setHover(null)}>
        {/* Y 그리드 + 라벨(손익, 원) */}
        {yTicks.map((t, i) => (
          <g key={`y${i}`}>
            <line className="chart-grid-line" x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} />
            <text className="chart-axis-text" x={padL - 8} y={y(t) + 3} textAnchor="end">
              {Math.abs(t) >= 1e6 ? (t / 1e6).toFixed(1) + "M" : Math.round(t / 1e3) + "k"}
            </text>
          </g>
        ))}
        {/* 0 손익선 강조 */}
        {profMin < 0 && (
          <line x1={padL} x2={W - padR} y1={y(0)} y2={y(0)}
                stroke="rgba(106,166,255,0.5)" strokeWidth="1" strokeDasharray="5 4" />
        )}
        {/* X 그리드 + 라벨(MDD %) */}
        {xTicks.map((t, i) => (
          <g key={`x${i}`}>
            <line x1={x(t)} x2={x(t)} y1={padT} y2={padT + innerH} stroke="var(--line-1)" strokeWidth="1" opacity="0.5" />
            <text className="chart-axis-text" x={x(t)} y={H - 18} textAnchor="middle">{t}%</text>
          </g>
        ))}
        <text className="chart-axis-text" x={padL + innerW / 2} y={H - 4} textAnchor="middle" fill="var(--ink-2)">
          MDD (낙폭 %) →  ·  ↑ 손익(원)
        </text>
        {/* 프레임 */}
        <line x1={padL} x2={W - padR} y1={padT + innerH} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
        <line x1={padL} x2={padL} y1={padT} y2={padT + innerH} stroke="var(--line-2)" strokeWidth="1" />
        {/* 점 */}
        {pts.map((p, i) => {
          const cx = x(typeof p.mdd === "number" ? p.mdd : 0);
          const cy = y(typeof p.profit === "number" ? p.profit : 0);
          const col = p.gate_passed ? "var(--teal)" : "var(--ink-3)";
          const isH = hover && hover.gen_no === p.gen_no;
          return (
            <g key={i} onMouseEnter={() => setHover(p)} style={{ cursor: "pointer" }}>
              {p.gate_passed && <circle cx={cx} cy={cy} r="8" fill="rgba(76,214,179,0.14)" />}
              <circle cx={cx} cy={cy} r={isH ? 6 : 4} fill={col}
                      stroke={isH ? "var(--ink-0)" : "none"} strokeWidth="1.2" />
            </g>
          );
        })}
      </svg>

      {hover && (
        <div style={{
          position: "absolute", top: 14, left: 80,
          background: "var(--bg-0)", border: "1px solid var(--line-2)", borderRadius: 6,
          padding: "8px 10px", fontFamily: "var(--mono)", fontSize: 11, minWidth: 190,
          boxShadow: "0 6px 16px rgba(0,0,0,0.4)", pointerEvents: "none",
        }}>
          <div style={{ fontSize: 10.5, color: "var(--ink-2)", letterSpacing: ".12em", textTransform: "uppercase", marginBottom: 4 }}>
            gen_{String(hover.gen_no).padStart(2, "0")}
            {hover.gate_passed && <span style={{ color: "var(--teal)", marginLeft: 6 }}>✓ 통과</span>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "auto 1fr", gap: "2px 10px" }}>
            <span style={{ color: "var(--ink-2)" }}>score</span><span>{_fScore(hover.score)}</span>
            <span style={{ color: "var(--ink-2)" }}>MDD</span><span style={{ color: "var(--red)" }}>{_fPct(hover.mdd)}</span>
            <span style={{ color: "var(--ink-2)" }}>손익</span>
            <span className={hover.profit > 0 ? "num-pos" : hover.profit < 0 ? "num-neg" : ""}>{_fMoney(hover.profit)}</span>
            <span style={{ color: "var(--ink-2)" }}>거래</span><span>{_fInt(hover.trade_count)}</span>
          </div>
        </div>
      )}

      {pts.length === 0 && <EaEmpty text="산점 데이터가 없습니다" />}
    </div>
  );
}

// ---------------------------------------------------------------------------
// 3) 세대 비교 미니 테이블 — 상위 N(score 내림차순) + [워크벤치 분석] 버튼.
//    버튼: backtest.jsx 직접 import 없이 window 이벤트 발행 + 탭 전환(onOpenWorkbench).
// ---------------------------------------------------------------------------
function EaTopTable({ runId, gens, topN, onOpenWorkbench }) {
  // 워크벤치 연동 가능 여부 — 콜백이 없으면 탭 전환이 일어나지 않으므로(조용한 무동작 방지)
  //   버튼을 비활성화하고 그 이유를 툴팁으로 알린다.
  const canOpenWorkbench = typeof onOpenWorkbench === "function";
  const top = useMemo_ea(() => {
    return gens.filter(g => g.gen_no >= 0)
      .slice()
      .sort((a, b) => (b.score || 0) - (a.score || 0))
      .slice(0, topN);
  }, [gens, topN]);

  const openInWorkbench = useCallback_ea((genNo) => {
    const detail = { run_id: runId, gen_no: genNo };
    // 느슨 결합: 선택을 window 이벤트 + localStorage 로 전달(backtest.jsx 가 소비).
    try {
      window.dispatchEvent(new CustomEvent("stom:bt-evo-select", { detail }));
      localStorage.setItem("stom_bt_evo_pending", JSON.stringify(detail));
    } catch (e) { /* 무시 — 전달 실패해도 탭 전환은 진행 */ }
    if (typeof onOpenWorkbench === "function") onOpenWorkbench(detail);
  }, [runId, onOpenWorkbench]);

  if (top.length === 0) {
    return <div className="mono" style={{ padding: "16px 4px", color: "var(--ink-3)", fontSize: 12 }}>
      상위 세대가 없습니다
    </div>;
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <table className="mono" style={{ width: "100%", borderCollapse: "collapse", fontSize: 11.5 }}>
        <thead>
          <tr style={{ color: "var(--ink-2)", textAlign: "right" }}>
            <th style={{ textAlign: "left", padding: "6px 8px" }}>gen</th>
            <th style={{ padding: "6px 8px" }}>score</th>
            <th style={{ padding: "6px 8px" }}>손익</th>
            <th style={{ padding: "6px 8px" }}>MDD</th>
            <th style={{ padding: "6px 8px" }}>거래</th>
            <th style={{ textAlign: "center", padding: "6px 8px" }}>게이트</th>
            <th style={{ padding: "6px 8px" }}></th>
          </tr>
        </thead>
        <tbody>
          {top.map(g => (
            <tr key={g.gen_no} style={{ borderTop: "1px solid var(--line-1)", textAlign: "right" }}>
              <td style={{ textAlign: "left", padding: "6px 8px", color: "var(--ink-0)" }}>
                gen_{String(g.gen_no).padStart(2, "0")}
              </td>
              <td style={{ padding: "6px 8px", color: "var(--teal)" }}>{_fScore(g.score)}</td>
              <td style={{ padding: "6px 8px" }}
                  className={g.profit > 0 ? "num-pos" : g.profit < 0 ? "num-neg" : ""}>{_fMoney(g.profit)}</td>
              <td style={{ padding: "6px 8px", color: "var(--red)" }}>{_fPct(g.mdd)}</td>
              <td style={{ padding: "6px 8px" }}>{_fInt(g.trade_count)}</td>
              <td style={{ textAlign: "center", padding: "6px 8px",
                           color: g.gate_passed ? "var(--teal)" : "var(--ink-3)" }}>
                {g.gate_passed ? "✓" : "—"}
              </td>
              <td style={{ padding: "6px 8px", textAlign: "center" }}>
                <button className="btn ghost sm" disabled={!g.has_csv || !canOpenWorkbench}
                        data-tip={!canOpenWorkbench ? "워크벤치 연동이 비활성화됨(탭 전환 콜백 없음)"
                                  : g.has_csv ? "백테스트 탭에서 이 세대 결과를 상세 분석"
                                              : "결과 CSV 가 없어 상세 분석 불가"}
                        onClick={() => openInWorkbench(g.gen_no)}>
                  워크벤치 분석
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// 메인 패널 — run 셀렉터 + 요약 + 3종 시각화.
// ---------------------------------------------------------------------------
function EvolutionAnalysisPanel({ baseUrl, wsStatus, runId, onOpenWorkbench }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [runList, setRunList] = useState_ea([]);
  const [selRun, setSelRun] = useState_ea(runId || "");
  const [gens, setGens] = useState_ea([]);
  const [loading, setLoading] = useState_ea(false);
  const [normalize, setNormalize] = useState_ea(true);

  // 부모 runId 가 바뀌면(라이브 run 갱신) 사용자가 명시 선택 전까지 따라간다.
  useEffect_ea(() => {
    if (runId && !selRun) setSelRun(runId);
  }, [runId]);

  // run 목록(GET /runs) — 데모/미연결이면 빈 목록.
  useEffect_ea(() => {
    if (isDemo || !baseUrl) { setRunList([]); return; }
    let cancelled = false;
    _eaFetchJson(baseUrl + "/runs", 3000)
      .then(j => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
      })
      .catch(() => { if (!cancelled) setRunList([]); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo]);

  // 선택 run 의 세대(GET /bt/evo_gens) — 읽기 전용.
  useEffect_ea(() => {
    const rid = selRun || runId || "";
    if (isDemo || !baseUrl || !rid) { setGens([]); return; }
    let cancelled = false;
    setLoading(true);
    _eaFetchJson(baseUrl + "/bt/evo_gens?run_id=" + encodeURIComponent(rid), 8000)
      .then(j => {
        if (cancelled) return;
        setGens(Array.isArray(j && j.items) ? j.items : []);
      })
      .catch(() => { if (!cancelled) setGens([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, selRun, runId]);

  // 요약 통계.
  const summary = useMemo_ea(() => {
    const nums = gens.filter(g => g.gen_no >= 0);
    if (!nums.length) return null;
    const gate = nums.filter(g => g.gate_passed).length;
    const best = nums.reduce((a, b) => ((b.score || 0) > (a.score || 0) ? b : a), nums[0]);
    const bestProfit = nums.reduce((a, b) => ((b.profit || 0) > (a.profit || 0) ? b : a), nums[0]);
    return { count: nums.length, gate, best, bestProfit };
  }, [gens]);

  const effRun = selRun || runId || "";

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          진화 결과 분석 — Generation Analytics
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {/* run 셀렉터 — 기본 현재 run, 과거 run 선택 가능 */}
          <select
            value={effRun}
            onChange={e => setSelRun(e.target.value)}
            disabled={isDemo}
            className="mono"
            data-tip="분석할 run 선택(기본 현재 run)"
            style={{
              fontSize: 11, background: "var(--bg-1)", color: "var(--ink-0)",
              border: "1px solid var(--line-2)", borderRadius: 5, padding: "3px 6px", maxWidth: 240,
            }}>
            {effRun && !runList.some(r => r.run_id === effRun) && (
              <option value={effRun}>{effRun} (현재)</option>
            )}
            {(runList || []).map(r => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id}{r.label ? " · " + r.label : ""}{r.gate_passed_count > 0 ? " ✓" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo ? (
          <div className="mono" style={{ padding: "20px 4px", color: "var(--ink-3)", fontSize: 12 }}>
            데모(미연결) 모드 — 실 run 에 연결하면 세대 분석이 표시됩니다.
          </div>
        ) : !effRun ? (
          <div className="mono" style={{ padding: "20px 4px", color: "var(--ink-3)", fontSize: 12 }}>
            run 을 선택하면 세대 분석이 표시됩니다.
          </div>
        ) : (
          <>
            {/* 요약 미니 */}
            <div style={{ display: "flex", gap: 22, marginBottom: 12, flexWrap: "wrap" }}>
              <Mini label="세대 수" value={summary ? _fInt(summary.count) : "—"} />
              <Mini label="게이트 통과" value={summary ? `${summary.gate} / ${summary.count}` : "—"}
                    color={summary && summary.gate > 0 ? "var(--teal)" : undefined} />
              <Mini label="최고 점수" value={summary ? _fScore(summary.best.score) : "—"}
                    sub={summary ? `gen_${summary.best.gen_no}` : ""} />
              <Mini label="최대 손익" value={summary ? _fMoney(summary.bestProfit.profit) : "—"}
                    sub={summary ? `gen_${summary.bestProfit.gen_no}` : ""} />
            </div>

            {/* 다중지표 차트 + 정규화 토글 */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "6px 0 8px" }}>
              <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
                {EA_SERIES.map(s => <LegendDot key={s.key} color={s.color} label={s.label} />)}
              </div>
              <label className="mono" style={{ fontSize: 11, color: "var(--ink-2)", display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
                <input type="checkbox" checked={normalize} onChange={e => setNormalize(e.target.checked)} />
                정규화(0~1)
              </label>
            </div>
            <EaMultiMetricChart gens={gens} normalize={normalize} />
            {!normalize && (
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginTop: 4 }}>
                정규화 OFF — 스케일이 다른 계열은 겹쳐 비교가 어려워 score 만 원축으로 표시합니다.
              </div>
            )}

            {/* 산점도 */}
            <div style={{ display: "flex", gap: 14, alignItems: "center", margin: "16px 0 8px" }}>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)", letterSpacing: ".08em" }}>
                세대 산점도 — MDD × 손익(니치 지도)
              </span>
              <LegendDot color="var(--teal)" label="게이트 통과" filled="ring" />
              <LegendDot color="var(--ink-3)" label="게이트 탈락(흐린 점)" />
            </div>
            <EaScatterChart gens={gens} />

            {/* 상위 세대 테이블 */}
            <div style={{ margin: "16px 0 8px" }}>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-2)", letterSpacing: ".08em" }}>
                상위 세대 — score 내림차순(워크벤치 분석으로 백테 탭 연동)
              </span>
            </div>
            <EaTopTable runId={effRun} gens={gens} topN={8} onOpenWorkbench={onOpenWorkbench} />

            {loading && (
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", marginTop: 8 }}>
                불러오는 중…
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// 빌드 없는 text/babel 전역 등록(app.jsx 가 window 에서 참조).
Object.assign(window, { EvolutionAnalysisPanel });
