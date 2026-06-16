/* rl-panel.jsx — ResearchLabPanel 오케스트레이터 + 탭 정의 + 프로세스 흐름 오버레이
   (research-lab.jsx 에서 분리).

   compact 분석 워크스페이스(Edge·Feature·Correlation·Combos·Validation 탭).
   엣지/변수중요도 패널은 analysis.jsx, 상관/조합 본문 보조는 rl-analysis.jsx,
   검증 탭은 rl-validation.jsx 에서 import. (P5.6 분해: 본문 그대로, 정의 파일만 이동.)
   stom-ui 전역(window.STOM_PIPELINE / window.isDemoSource / window.ResearchProcessFlowOverlay)은
   런타임 window 조회 — import 금지. 외부 차트 라이브러리 금지.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { EdgeRatioPanel, FeatureImportancePanel } from "./analysis.jsx";
import { _ResearchEmptyState, _CorrelationControls, _CorrelationHeatmap, _CombinationList, _RangeSummaryList, _SegmentSummaryList, _RecencyResearchBadge } from "./rl-analysis.jsx";
import { _ValidationPanel } from "./rl-validation.jsx";
const {
  useState: useState_rl,
  useEffect: useEffect_rl,
  useCallback: useCallback_rl,
  useMemo: useMemo_rl,
} = React;

const RESEARCH_TABS = [
  { id: "edge", label: "엣지(승률·기대값)" },
  { id: "feature", label: "변수 중요도" },
  { id: "correlation", label: "상관관계" },
  { id: "combos", label: "변수 조합" },
  { id: "validation", label: "검증" },
];

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

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { ResearchLabPanel, RESEARCH_TABS, _RlProcessFlowOverlay };
