/* Backtest workbench tab — 탭 루트 컴포넌트 (split from backtest.jsx for the thin-barrel pattern).
   헬스 배지 + 상단 고정 실행 패널 + 하위 탭[조건식 편집|결과 분석] + 결과/분석 영역 + 접이식 섹션.
   상태(매수/매도·결과 잡·진화 세대·A/B 비교·하위 탭)를 탭 루트로 끌어올려 sub-panel 들에 공유한다.

   결과·분석 영역(BtResultArea + 메트릭 카드 + 차트 + 기여/인사이트)은 backtest-charts.jsx 에 있으며
   window 전역으로 공유된다(index.html 에서 이 파일보다 먼저 로드). 외부 차트 라이브러리 금지.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { BtResultArea } from "./backtest-charts.jsx";
import { useState_bt, useEffect_bt, useCallback_bt, useMemo_bt, _btFetchJson } from "./bt-tab-utils.jsx";
import { BtDualEditor, BtLibraryPanel } from "./bt-tab-library.jsx";
import { BtRunPanel, BtResultLibrary } from "./bt-tab-run.jsx";
import { BtModeResultPanel } from "./bt-tab-mode-results.jsx";
import { BtOverlayPanel, BtCollapsible, BtEvoSelector, BtPortfolioPanel, BtBackFinderPreflightPanel } from "./bt-tab-analysis.jsx";

// ===========================================================================
// 탭 루트 — 헬스 배지 + 좌(라이브러리·에디터·실행) / 우(결과) 레이아웃.
//   결과·분석 영역(BtResultArea + 메트릭 카드 + 차트 + 기여/인사이트)은
//   backtest-charts.jsx 에 있으며 window 전역으로 공유된다(이 파일보다 먼저 로드).
// ===========================================================================
function BacktestTab({ baseUrl, wsStatus }) {
  const isDemo = typeof window.isDemoSource === "function"
    ? window.isDemoSource(wsStatus) : (wsStatus === "demo");

  const [health, setHealth] = useState_bt(null);
  const [reloadKey, setReloadKey] = useState_bt(0);     // 라이브러리 재로드 트리거(저장/삭제 후).
  const [resultJobId, setResultJobId] = useState_bt("");
  const [libNames, setLibNames] = useState_bt({ buy: [], sell: [] });
  // 실행 셀렉터 = 듀얼 에디터 소스. 매수/매도 선택을 탭 루트로 끌어올려 공유한다.
  const [buyName, setBuyName] = useState_bt("");
  const [sellName, setSellName] = useState_bt("");
  // 진화 세대 분석 소스 — {run_id, gen_no} 또는 null. 잡 선택과 상호배타(둘 중 하나만).
  const [evoSource, setEvoSource] = useState_bt(null);
  // 포트폴리오·결과 라이브러리가 소비할 완료 잡 목록(BtRunPanel 이 끌어올려 공유).
  const [jobsList, setJobsList] = useState_bt([]);
  // 결과 라이브러리 강제 재로드 토큰(메타 갱신/잡 변경 후 잡 목록 새로고침).
  const [jobsReloadKey, setJobsReloadKey] = useState_bt(0);
  // A/B 비교 — compareA(기준 잡 id), compareView(/bt/compare 응답).
  const [compareA, setCompareA] = useState_bt("");
  const [compareView, setCompareView] = useState_bt(null);

  // B2 — 하위 탭 [조건식 편집 | 결과 분석]. STOM GUI 처럼 화면 전환(상단 실행바는 항상 노출).
  //   localStorage 로 마지막 선택을 유지(선택). 잘못된 값/접근 실패는 기본값으로 흡수.
  const [subTab, setSubTab] = useState_bt(() => {
    try {
      const v = window.localStorage && window.localStorage.getItem("bt_subtab");
      return v === "result" || v === "edit" ? v : "edit";
    } catch (e) { return "edit"; }
  });
  const selectSubTab = useCallback_bt((t) => {
    setSubTab(t);
    try { window.localStorage && window.localStorage.setItem("bt_subtab", t); } catch (e) {}
  }, []);

  // 잡 선택 → 잡 결과 모드(진화 세대 소스 해제) + 결과 분석 탭으로 자동 전환.
  const onPickJobResult = useCallback_bt((jobId) => {
    setResultJobId(jobId);
    if (jobId) { setEvoSource(null); selectSubTab("result"); }
  }, [selectSubTab]);
  // 진화 세대 선택 → 세대 결과 모드(잡 결과 해제) + 결과 분석 탭으로 자동 전환.
  const onPickGen = useCallback_bt((runId, genNo) => {
    setEvoSource({ run_id: runId, gen_no: genNo });
    setResultJobId("");
    selectSubTab("result");
  }, [selectSubTab]);

  // "바로 백테스트" 핸드오프 소비 — 진화 탭(evolution-analysis)·리서치 프로(pro.html)가
  //   localStorage(stom_bt_evo_pending)에 {run_id, gen_no}를 적재하고 탭/페이지를 전환한다.
  //   ① 마운트 시 pending 1회 소비(cross-page: pro.html → /ui/ 이동 케이스),
  //   ② 마운트 중에는 CustomEvent("stom:bt-evo-select")를 직접 수신(같은 페이지 케이스).
  //   소비 후 키를 지워 다음 진입 시 재적용을 막는다. 파싱 실패는 조용히 폐기.
  useEffect_bt(() => {
    const consume = (detail) => {
      if (detail && detail.run_id && detail.gen_no != null) {
        onPickGen(detail.run_id, detail.gen_no);
      }
    };
    try {
      const raw = window.localStorage && window.localStorage.getItem("stom_bt_evo_pending");
      if (raw) {
        window.localStorage.removeItem("stom_bt_evo_pending");
        consume(JSON.parse(raw));
      }
    } catch (e) {}
    const onSelect = (ev) => {
      try { window.localStorage && window.localStorage.removeItem("stom_bt_evo_pending"); } catch (e) {}
      consume(ev && ev.detail);
    };
    window.addEventListener("stom:bt-evo-select", onSelect);
    return () => window.removeEventListener("stom:bt-evo-select", onSelect);
  }, [onPickGen]);

  // 비교(B) 실행 — A 고정 후 다른 잡을 B 로 비교.
  const runCompare = useCallback_bt((jobB) => {
    if (isDemo || !baseUrl || !compareA || !jobB) return;
    const url = baseUrl + "/bt/compare?job_a=" + encodeURIComponent(compareA)
              + "&job_b=" + encodeURIComponent(jobB);
    _btFetchJson(url, 12000)
      .then(j => setCompareView(j || null))
      .catch(() => setCompareView(null));
  }, [baseUrl, isDemo, compareA]);

  const onSetCompareA = useCallback_bt((jobId) => {
    setCompareA(jobId);
    setCompareView(null);
  }, []);
  const onCloseCompare = useCallback_bt(() => { setCompareView(null); }, []);

  // 헬스 체크.
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setHealth(null); return; }
    _btFetchJson(baseUrl + "/bt/health", 3000).then(setHealth).catch(() => setHealth(null));
  }, [baseUrl, isDemo, reloadKey]);

  // 실행 셀렉터용 buy/sell 이름 목록(라이브러리와 독립적으로 양쪽 모두 필요).
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setLibNames({ buy: [], sell: [] }); return; }
    let cancelled = false;
    Promise.all([
      _btFetchJson(baseUrl + "/bt/strategies?kind=buy", 4000).catch(() => ({ items: [] })),
      _btFetchJson(baseUrl + "/bt/strategies?kind=sell", 4000).catch(() => ({ items: [] })),
    ]).then(([b, s]) => {
      if (cancelled) return;
      setLibNames({
        buy: (b.items || []).map(it => it.name),
        sell: (s.items || []).map(it => it.name),
      });
    });
    return () => { cancelled = true; };
  }, [baseUrl, isDemo, reloadKey]);

  const connected = !!(health && health.status === "ok");
  const badge = isDemo
    ? { label: "demo", color: "var(--ink-3)" }
    : connected
      ? { label: "connected · api v" + health.api_version, color: "var(--teal)" }
      : { label: "checking", color: "var(--amber)" };

  const onSaved = useCallback_bt(() => { setReloadKey(k => k + 1); }, []);
  const reloadJobs = useCallback_bt(() => { setJobsReloadKey(k => k + 1); }, []);


  // 선택 잡의 모드(wfo/sweep 이면 csv 단일 분석 대신 모드별 표를 띄운다).
  const selectedJobMode = useMemo_bt(() => {
    if (!resultJobId) return "backtest";
    const j = (jobsList || []).find(x => x.job_id === resultJobId);
    return (j && j.spec && j.spec.mode) || "backtest";
  }, [jobsList, resultJobId]);
  const isModeResult = resultJobId && (selectedJobMode === "wfo" || selectedJobMode === "sweep");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      {/* 탭 헤더 배지 행 */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 14px",
                    background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 8 }}>
        <span className="panel-hd-title" style={{ border: 0 }}>
          <span className="dot" style={{ background: "var(--teal)" }}></span>백테스트 워크벤치
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: badge.color, letterSpacing: ".06em", marginLeft: "auto" }}>
          ● {badge.label}
        </span>
      </div>

      {/* 데모 모드 안내 — 미연결 상태의 빈/예시 화면을 '버그'로 오인하지 않도록 명시 배너. */}
      {isDemo && (
        <div className="mono" style={{
          display: "flex", alignItems: "center", gap: 8, padding: "8px 14px",
          background: "rgba(240,179,90,0.08)", border: "1px solid rgba(240,179,90,0.35)",
          borderRadius: 8, fontSize: 11.5, color: "var(--amber)",
        }}>
          <span className="badge warn" style={{ flexShrink: 0 }}>데모 모드</span>
          백엔드 미연결 — 표시되는 결과는 예시이며 실제 데이터가 아닙니다. 서버에 연결하면 실거래 백테스트가 활성화됩니다.
        </div>
      )}

      {/* 상단 고정 전폭 실행 패널 — 항상 노출(매수/매도·기간·모드·대형 실행 버튼·활성 잡 카드) */}
      <BtRunPanel baseUrl={baseUrl} isDemo={isDemo} libNames={libNames} onResult={onPickJobResult}
                  compareA={compareA} onCompareB={runCompare} onJobs={setJobsList}
                  buy={buyName} sell={sellName} onBuy={setBuyName} onSell={setSellName}
                  reloadJobsKey={jobsReloadKey} />

      {/* B2 — 하위 탭 전환 바 [조건식 편집 | 결과 분석] (STOM GUI 화면 전환과 동일) */}
      <div className="bt-subtabs" style={{ display: "flex", gap: 4, padding: 4,
            background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 8 }}>
        {[
          { id: "edit", label: "조건식 편집" },
          { id: "result", label: "결과 분석" },
        ].map(t => {
          const active = subTab === t.id;
          return (
            <button key={t.id} onClick={() => selectSubTab(t.id)}
                    style={{
                      flex: 1, padding: "9px 14px", borderRadius: 6, cursor: "pointer",
                      fontFamily: "var(--mono)", fontSize: 13, fontWeight: active ? 700 : 400,
                      border: active ? "1px solid var(--teal-dim, var(--teal))" : "1px solid transparent",
                      background: active ? "var(--bg-0)" : "transparent",
                      color: active ? "var(--teal)" : "var(--ink-2)",
                    }}>
              {t.label}
            </button>
          );
        })}
      </div>

      {/* 조건식 편집 탭 — 듀얼 에디터(변수 칩 포함) + 조건식 라이브러리 */}
      {subTab === "edit" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <BtDualEditor baseUrl={baseUrl} isDemo={isDemo} buyName={buyName} sellName={sellName}
                        onSaved={onSaved}
                        onDeletedBuy={() => { setReloadKey(k => k + 1); setBuyName(""); }}
                        onDeletedSell={() => { setReloadKey(k => k + 1); setSellName(""); }} />
          <BtCollapsible title="조건식 라이브러리(빠른 선택)" accent="var(--teal)" defaultOpen>
            <div className="grid-main" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)" }}>
              <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="buy" onKind={() => {}} lockKind
                              onPick={setBuyName} selectedName={buyName} reloadKey={reloadKey} />
              <BtLibraryPanel baseUrl={baseUrl} isDemo={isDemo} kind="sell" onKind={() => {}} lockKind
                              onPick={setSellName} selectedName={sellName} reloadKey={reloadKey} />
            </div>
          </BtCollapsible>
          <BtCollapsible title="백파인더 사전 점검(실행 전용 준비)" accent="var(--amber)" defaultOpen={false}>
            <BtBackFinderPreflightPanel baseUrl={baseUrl} isDemo={isDemo} buyName={buyName} />
          </BtCollapsible>
        </div>
      )}

      {/* 결과 분석 탭 — 결과 라이브러리 + 전폭 결과/분석 영역 + 접이식 분석 섹션 */}
      {subTab === "result" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <BtResultLibrary baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} onResult={onPickJobResult}
                           selectedJobId={resultJobId} onReload={reloadJobs}
                           compareA={compareA} onSetCompareA={onSetCompareA} onCompareB={runCompare} />
          <div style={{ minWidth: 0, position: "relative" }}>
            {isModeResult ? (
              <BtModeResultPanel baseUrl={baseUrl} isDemo={isDemo} jobId={resultJobId} mode={selectedJobMode} />
            ) : (
              <BtResultArea baseUrl={baseUrl} isDemo={isDemo} jobId={resultJobId} evoSource={evoSource}
                            onSetCompareA={onSetCompareA} compareView={compareView} onCloseCompare={onCloseCompare} />
            )}
          </div>

          {/* 접이식 분석 섹션 — 진화 세대 분석 · 오버레이 · 포트폴리오 결합 */}
          <BtCollapsible title="진화 세대 분석" accent="var(--violet)" defaultOpen={false}>
            <BtEvoSelector baseUrl={baseUrl} isDemo={isDemo} onPickGen={onPickGen} activeEvo={evoSource} />
          </BtCollapsible>
          <BtCollapsible title="다중 잡 오버레이(수익곡선 겹쳐보기)" accent="var(--teal)" defaultOpen={false}>
            <BtOverlayPanel baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} />
          </BtCollapsible>
          <BtCollapsible title="포트폴리오 결합 분석" accent="var(--blue)" defaultOpen={false}>
            <BtPortfolioPanel baseUrl={baseUrl} isDemo={isDemo} jobs={jobsList} activeEvo={evoSource} />
          </BtCollapsible>
        </div>
      )}
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { BacktestTab };
