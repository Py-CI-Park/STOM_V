/* rp-panel.jsx — 리서치 프로 오케스트레이터 (P5.7 분해 후).
   research-pro.jsx 의 두 진입 패널을 모은다(동작 불변, 코드 이동만):
     · ResearchProPanel — 풀스크린 워크스페이스(상단 셀렉터 바 + 4개 분석 카드 그리드 + 프로세스 오버레이)
     · ResearchHeatmapPanel — 메인 진화 탭용 독립 히트맵 패널(_RpBigHeatmap 재사용)

   제약: window 전역 컴포넌트 · 파일별 훅 별칭(rp-utils.jsx 공유) · 한국어 UI.
   window.isDemoSource 는 typeof 방어 소비로 그대로 둔다(load-order — connection.jsx 미로드 흡수). */

// Track Z (PR-3) — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_rp, useEffect_rp, useCallback_rp, useMemo_rp, _rpFetchJson } from "./rp-utils.jsx";
import { _RpBigHeatmap, _RpHallOfFame, _RpRunCompare, _RpHistory, _RpProcessFlowOverlay } from "./rp-heatmap.jsx";

/* ── 메인: ResearchProPanel — 풀스크린 워크스페이스. ── */
function ResearchProPanel({ baseUrl, wsStatus, runId }) {
  const isDemo =
    typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";

  const [runList, setRunList] = useState_rp([]);
  const [selRun, setSelRun] = useState_rp(runId || "");
  const [selGen, setSelGen] = useState_rp(0);
  const [ops, setOps] = useState_rp(null);
  const [liveState, setLiveState] = useState_rp(null);
  const [showFlow, setShowFlow] = useState_rp(false);
  const [refreshKey, setRefreshKey] = useState_rp(0);

  /* 부모 runId가 처음 들어오면 기본 선택으로 따라간다(명시 선택 전까지). */
  useEffect_rp(() => {
    if (runId && !selRun) setSelRun(runId);
  }, [runId]);

  /* run 목록(/runs). */
  useEffect_rp(() => {
    if (isDemo || !baseUrl) {
      setRunList([]);
      return undefined;
    }
    let cancelled = false;
    _rpFetchJson(baseUrl + "/runs", 6000)
      .then((j) => {
        if (cancelled) return;
        const runs = Array.isArray(j && j.runs) ? j.runs : [];
        runs.sort((a, b) => (Number(b.started_at) || 0) - (Number(a.started_at) || 0));
        setRunList(runs);
        if (!selRun && runs.length) setSelRun(runs[0].run_id);
      })
      .catch(() => {
        if (!cancelled) setRunList([]);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, isDemo, refreshKey]);

  /* ops_status(10초) + live state(현재 단계 추정용). */
  useEffect_rp(() => {
    if (isDemo || !baseUrl) return undefined;
    const pull = () => {
      _rpFetchJson(baseUrl + "/ops_status", 8000)
        .then((j) => setOps(j))
        .catch(() => {});
      _rpFetchJson(baseUrl + "/status", 8000)
        .then((j) => setLiveState(j))
        .catch(() => {});
    };
    pull();
    const timer = setInterval(pull, 10000);
    return () => clearInterval(timer);
  }, [baseUrl, isDemo, refreshKey]);

  const onRefresh = useCallback_rp(() => setRefreshKey((k) => k + 1), []);
  const onOpenWorkbench = useCallback_rp(() => {
    /* 풀스크린(별도 페이지)에서는 부모 앱 탭을 직접 못 바꾸므로, 운영 앱이 새로고침 시
       마지막 탭으로 쓰는 localStorage(stom_active_tab)를 'backtest'로 설정한 뒤 운영
       페이지로 이동한다. 선택 세대는 _rpOpenWorkbench가 stom_bt_evo_pending에 적재해 둔다
       (백테 탭의 진화 셀렉터가 그 run을 펼쳐 둔 상태로 보여줌). 같은 페이지(운영 내부)
       에서 열린 경우엔 이 콜백이 주입되지 않으므로 이 경로는 풀스크린 전용이다. */
    try {
      localStorage.setItem("stom_active_tab", "backtest");
      window.location.href = "/ui/";
    } catch (e) {
      /* 무시 — 이동 실패해도 CustomEvent/localStorage 적재는 이미 끝났다. */
    }
  }, []);

  const activeRunLabel = useMemo_rp(() => {
    const r = (runList || []).find((x) => x.run_id === selRun);
    return r && r.label ? r.label : "";
  }, [runList, selRun]);

  return (
    <div className="research-pro">
      {/* 상단 셀렉터 바 */}
      <div className="rp-topbar">
        <div className="rp-topbar-title">
          <span className="rp-topbar-mark">🔬</span>
          <div>
            <div className="rp-topbar-h">리서치 프로 — 전체화면 분석 워크스페이스</div>
            <div className="rp-topbar-sub mono">
              {selRun ? selRun : "run 미선택"}
              {activeRunLabel ? " · " + activeRunLabel : ""}
            </div>
          </div>
        </div>
        <div className="rp-topbar-controls">
          <label className="rp-ctl mono">
            <span>run</span>
            <select
              className="mono rp-select"
              value={selRun}
              onChange={(e) => setSelRun(e.target.value)}
              disabled={isDemo}
            >
              <option value="">선택…</option>
              {(runList || []).map((r) => (
                <option key={r.run_id} value={r.run_id}>
                  {r.run_id}
                  {r.label ? " · " + r.label : ""}
                  {r.gate_passed_count > 0 ? " ✓" : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="rp-ctl mono">
            <span>gen</span>
            <input
              type="number"
              min={0}
              value={selGen}
              onChange={(e) => setSelGen(Number(e.target.value) || 0)}
              className="rp-num-input mono"
            />
          </label>
          <button className="btn ghost sm" onClick={onRefresh} disabled={isDemo}>
            ↻ 새로고침
          </button>
          <button className="btn ghost sm" onClick={() => setShowFlow(true)} data-tip="진화 전체 프로세스 보기">
            🧭 프로세스
          </button>
        </div>
      </div>

      {isDemo ? (
        <div className="rp-empty" style={{ margin: 24 }}>
          데모(미연결) 모드 — 실 run에 연결하면 리서치 프로 분석이 표시됩니다.
        </div>
      ) : (
        <div className="rp-grid">
          <_RpBigHeatmap baseUrl={baseUrl} isDemo={isDemo} runId={selRun} key={"hm" + refreshKey} />
          <_RpHallOfFame baseUrl={baseUrl} isDemo={isDemo} onOpenWorkbench={onOpenWorkbench} key={"hof" + refreshKey} />
          <_RpRunCompare
            baseUrl={baseUrl}
            isDemo={isDemo}
            runList={runList}
            currentRunId={selRun}
            currentGenNo={selGen}
            onOpenWorkbench={onOpenWorkbench}
          />
          <_RpHistory baseUrl={baseUrl} isDemo={isDemo} runList={runList} onOpenWorkbench={onOpenWorkbench} />
        </div>
      )}

      {showFlow && (
        <_RpProcessFlowOverlay onClose={() => setShowFlow(false)} liveState={liveState} ops={ops} />
      )}
    </div>
  );
}

/* Phase6.1(E7) — 메인 진화 탭용 독립 히트맵 패널: 적합도 추이와 같은 급(패널 카드)으로
   시간대×시가총액 탐색 히트맵을 노출한다. _RpBigHeatmap 재사용(자체 /edge_ratio 조회). */
function ResearchHeatmapPanel({ baseUrl, wsStatus, runId }) {
  const isDemo =
    typeof window.isDemoSource === "function" ? window.isDemoSource(wsStatus) : wsStatus === "demo";
  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--violet)" }}></span>
          탐색 히트맵 — 시간대 × 시가총액
          <span data-tip="진화 루프가 어느 시간대·어느 시가총액 구간에서 엣지(edge_ratio)를 찾고 있는지 보여줍니다. 1.0 초과(녹색) = 해당 구간에서 시드 대비 우위, 1.0 미만(적색) = 열위. 셀에 마우스를 올리면 상세 수치가 나옵니다."
                style={{ marginLeft: 6, fontSize: 10, color: "var(--ink-3)", border: "1px solid var(--line-2)",
                         borderRadius: "50%", width: 15, height: 15, display: "inline-flex",
                         alignItems: "center", justifyContent: "center", cursor: "help" }}>?</span>
        </div>
      </div>
      <div className="panel-bd">
        {isDemo || !runId ? (
          <div className="mono" style={{ fontSize: 12, color: "var(--ink-3)", padding: "18px 0", textAlign: "center" }}>
            {isDemo ? "데모 모드 — 백엔드 연결 시 히트맵이 표시됩니다." : "run 데이터가 누적되면 히트맵이 표시됩니다."}
          </div>
        ) : (
          <_RpBigHeatmap baseUrl={baseUrl} isDemo={isDemo} runId={runId} />
        )}
      </div>
    </div>
  );
}

// Track Z (PR-3) — dual-safe ESM export (stripped by build-app.mjs `_stripTopLevelEsm` in the concat path; kept by the flagged bundle for real module scope). KEEP on ONE physical line.
export { ResearchProPanel, ResearchHeatmapPanel };
