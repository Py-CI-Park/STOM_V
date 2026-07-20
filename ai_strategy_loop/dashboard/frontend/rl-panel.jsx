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
  { id: "edge", label: "탐색 히트맵 · Edge Ratio" },
  { id: "feature", label: "변수 중요도" },
  { id: "correlation", label: "상관관계" },
  { id: "combos", label: "변수 조합" },
  { id: "validation", label: "검증" },
];
function _rlPipelineState() {
  const raw = Array.isArray(window.STOM_PIPELINE) && window.STOM_PIPELINE.length ? window.STOM_PIPELINE : null;
  if (!raw) {
    return {
      pipeline: [],
      error: "window.STOM_PIPELINE 정본을 불러오지 못했습니다. 오래된 로컬 fallback 프로세스는 표시하지 않습니다.",
    };
  }
  return {
    pipeline: raw.map((s, i) => ({
      key: s && s.key ? String(s.key) : `stage-${i}`,
      icon: s && s.icon ? String(s.icon) : "•",
      title: s && s.title ? String(s.title) : `단계 ${i + 1}`,
      desc: s && s.desc ? String(s.desc) : "단계 설명 없음",
      terms: Array.isArray(s && s.terms)
        ? s.terms
            .filter((pair) => Array.isArray(pair) && pair.length >= 2)
            .map(([t, d]) => [String(t || ""), String(d || "")])
            .filter(([t, d]) => t && d)
        : [],
    })),
    error: null,
  };
}

/* E10(2026-06-13) — 진화 프로세스 플로우 오버레이(자족형).
   research-pro.jsx가 로드되면 더 풍부한 window.ResearchProcessFlowOverlay를 쓰지만,
   메인 앱(index.html)에는 research-pro.jsx가 없으므로 리서치랩이 자체 오버레이를
   포함해 어느 페이지에서도 '프로세스' 버튼이 동작하게 한다. 단계별 한국어 설명 +
   용어 사전(세대/격자/니치/OOS/동결)을 카드+화살표로 보여준다. */
// P4(2026-06-14): 진화 프로세스 7단계는 format.ts 의 정본 window.STOM_PIPELINE 로 통합(중복 제거).
//   research-pro 와 동일 정본 공유 — 과거 로컬 사본(터서 문구)은 삭제, 더 풍부한 정본 채택.
function _RlProcessFlowOverlay({ onClose, activeStage }) {
  const { pipeline: PIPELINE, error: pipelineError } = _rlPipelineState();
  useEffect_rl(() => {
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  const ai = typeof activeStage === "number" && activeStage >= 0 && activeStage < PIPELINE.length ? activeStage : -1;
  return (
    <div className="rp-overlay" onClick={onClose}>
      <div className="rp-overlay-card" onClick={(e) => e.stopPropagation()}>
        <div className="rp-overlay-hd">
          <span className="rp-card-title">진화 프로세스 — 전체 흐름</span>
          {pipelineError ? <span className="rp-card-sub">프로세스 정본 로드 실패</span> : ai >= 0 && <span className="rp-card-sub">현재 단계: {PIPELINE[ai].title}</span>}
          <button type="button" className="btn ghost sm" style={{ marginLeft: "auto" }} onClick={onClose}>
            ✕ 닫기 (Esc)
          </button>
        </div>
        {pipelineError && (
          <div className="rp-flow-error" role="alert">
            <_ResearchEmptyState message={pipelineError} />
          </div>
        )}
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

function ResearchLabPanel({ baseUrl, wsStatus, runId, onOpenWorkbench }) {
  const [tab, setTab] = useState_rl("edge");
  // v5.5.1 F4 — 매트릭스가 기본. 구 키(stom_v54_lab_all)는 검수 중 저장된 "0"이 기본을 덮어
  //   사장님 화면에 탭 모드가 고정되던 원인이라 **무시**하고 새 키로 마이그레이션한다.
  const [viewAll, setViewAll] = useState_rl(() => {
    try { return window.localStorage.getItem("stom_v55_lab_view") !== "single"; } catch (e) { return true; }
  });
  const setViewAllPersist = (v) => {
    setViewAll(v);
    try { window.localStorage.setItem("stom_v55_lab_view", v ? "matrix" : "single"); } catch (e) {}
  };
  const [opsStrip, setOpsStrip] = useState_rl(null);       /* 탭 공통 운영 띠. */
  const [opsError, setOpsError] = useState_rl(null);

  useEffect_rl(() => {
    if (!baseUrl) return undefined;
    const pull = () => fetch(baseUrl + "/ops_status", { signal: AbortSignal.timeout(8000) })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then(j => {
        setOpsStrip(j);
        setOpsError(null);
        try {  /* F7 — 정체 의심 시 브라우저 탭 제목 경고(자리 비움 감지용). */
          const stalled = ((j && j.active) || []).some(a => a.health !== "active");
          const base = document.title.replace(/^⚠️ /, "");
          document.title = (stalled ? "⚠️ " : "") + base;
        } catch (e) { /* 제목 갱신 실패는 무시. */ }
      })
      .catch((e) => { setOpsStrip(null); setOpsError(String(e)); });
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
  const needsCorrelation = viewAll || tab === "correlation" || tab === "combos";

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
      : ((data && Array.isArray(data.top_pairs) && data.top_pairs.length) ? data.top_pairs : []);
    return [...raw].sort((a, b) => (
      (b.research_score || b.abs_correlation || Math.abs(b.correlation || 0))
      - (a.research_score || a.abs_correlation || Math.abs(a.correlation || 0))
    ));
  }, [data]);

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
                              featureCount={data && data.feature_count} runId={runId} />
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
                              featureCount={data && data.feature_count} runId={runId} />
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
                              featureCount={data && data.feature_count} runId={runId} />
        {pairRows.length
          ? <_CombinationList rows={pairRows} />
          : <_ResearchEmptyState message="명시적 변수 조합 후보가 없습니다. interaction_candidates 또는 top_pairs 응답이 필요합니다." />}
      </div>
    );
  }
  // v5.4 L5 — 한눈에(전체) 그리드: 각 분석을 개별 블록으로 병렬 표시(탭 선택보다 우선).
  if (viewAll) {
    const corrReady = !isDemo && runId && !err && data;
    body = (
      <div className="v54-lab-all">
        <section className="v54-lab-cell wide">
          <h4 className="stom-section-label">탐색 히트맵 · Edge Ratio</h4>
          <EdgeRatioPanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        </section>
        <section className="v54-lab-cell">
          <h4 className="stom-section-label">변수 중요도</h4>
          <FeatureImportancePanel baseUrl={baseUrl} wsStatus={wsStatus} runId={runId} />
        </section>
        <section className="v54-lab-cell">
          <h4 className="stom-section-label">상관관계</h4>
          {corrReady
            ? (<div><_CorrelationHeatmap rows={matrixRows.length ? matrixRows : outcomeRows} />
                 <_RecencyResearchBadge recency={recencyResearch} /></div>)
            : <_ResearchEmptyState message={err ? ("응답을 받지 못했습니다: " + err) : "상관 분석 데이터 대기(run 컨텍스트 필요)"} />}
        </section>
        <section className="v54-lab-cell">
          <h4 className="stom-section-label">변수 조합 후보</h4>
          {corrReady && pairRows.length
            ? <_CombinationList rows={pairRows} />
            : <_ResearchEmptyState message="변수 조합 후보 대기" />}
        </section>
        <section className="v54-lab-cell">
          <h4 className="stom-section-label">구간 요약</h4>
          {corrReady
            ? (<div><_RangeSummaryList rows={rangeRows} /><_SegmentSummaryList summary={segmentSummary} axis={axis} /></div>)
            : <_ResearchEmptyState message="구간 요약 데이터 대기" />}
        </section>
        <section className="v54-lab-cell">
          <h4 className="stom-section-label">검증 · 안정성</h4>
          <_ValidationPanel baseUrl={baseUrl} runId={runId} isDemo={isDemo} />
        </section>
      </div>
    );
  }

  const activeOps = !opsError && opsStrip ? (opsStrip.active || []) : [];
  const recentOps = !opsError && opsStrip ? (opsStrip.recent || []) : [];
  /* E1 — '모드/대상' 라벨을 명시(이전엔 "운영 연구 결과"류 평문이라 의미 불명). */
  const labMode = opsError ? "상태 오류" : (activeOps.length ? "운영(실행 중)" : "연구(분석)");
  const openWorkbench = useCallback_rl(() => {
    if (typeof onOpenWorkbench === "function") {
      onOpenWorkbench();
      return;
    }
    try {
      window.localStorage.setItem("stom_active_tab", "evolution");
      window.localStorage.setItem("stom_active_evolution_tab", "workbench");
      window.location.href = "/ui/evolution/workbench";
    } catch (e) {
      if (window.location) window.location.href = "/ui/evolution/workbench";
    }
  }, [onOpenWorkbench]);
  return (
    <div className="research-lab-shell">
      <div className="research-section-filter" aria-label="연구실 보기 선택">
        {/* v5.5 F4 — 매트릭스(전체 동시)가 기본. 칩 탭은 '개별 보기'에서만 노출. */}
        {!viewAll && RESEARCH_TABS.map(item => (
          <button key={item.id}
                  type="button"
                  className={"research-filter-chip" + (tab === item.id ? " active" : "")}
                  aria-pressed={tab === item.id}
                  onClick={() => { setViewAllPersist(false); setTab(item.id); }}>
            {item.label}
          </button>
        ))}
        <button type="button"
                className={"research-filter-chip" + (viewAll ? " active" : "")}
                aria-pressed={viewAll}
                title={viewAll ? "개별 분석을 하나씩 크게 보는 모드로 전환" : "5개 분석을 매트릭스로 동시에 보는 기본 모드로 복귀"}
                onClick={() => setViewAllPersist(!viewAll)}>
          {viewAll ? "개별 보기 전환" : "▦ 매트릭스 보기(기본)"}
        </button>
        {/* E2 — 분석 워크벤치로 SPA 전환(standalone pro.html 풀리로드 하드링크 금지). */}
        <button type="button" className="research-filter-action"
                title="진화 홈 하위 분석 워크벤치로 전환해 히트맵·명예의전당·비교·히스토리를 봅니다."
                onClick={openWorkbench}>
          🔬 상세 워크벤치
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
          : opsError ? (
            <span className="research-badge research-badge-error" title="운영 상태 endpoint 로드 실패 — 실행 없음으로 표시하지 않습니다.">
              <b>상태</b> 로드 실패
            </span>
          ) : (
            <span className="research-badge" title="현재 실행 중인 진화 작업이 없습니다(분석 전용).">
              <b>상태</b> 실행 중 작업 없음
            </span>
          )}
      </div>
      {opsError && (
        <div className="research-lab-panel research-lab-error">
          <_ResearchEmptyState message={"운영 상태를 불러오지 못했습니다: " + opsError} />
        </div>
      )}
      {body}
      <div className="lab-glossary" aria-label="연구실 용어 설명">
        <span><b>엣지</b> 조건이 실제로 유리한 구간</span>
        <span><b>변수 중요도</b> 성과 차이를 크게 만든 입력 변수</span>
        <span><b>상관관계</b> 변수와 결과가 같이 움직인 정도</span>
        <span><b>검증</b> 후보를 다른 기간·조건으로 다시 확인하는 단계</span>
      </div>
      <details className="lab-example">
        <summary>예시 보기: 연구실에서 결과를 해석하는 순서</summary>
        <ol>
          <li>엣지에서 시간·시총·회전율별 승률/기대값을 봅니다.</li>
          <li>변수 중요도와 상관관계로 왜 좋아졌는지 확인합니다.</li>
          <li>검증 섹션에서 다른 기간에서도 유지되는지 확인합니다.</li>
        </ol>
      </details>
    </div>
  );
}

Object.assign(window, { ResearchLabPanel });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { ResearchLabPanel, RESEARCH_TABS, _RlProcessFlowOverlay };
