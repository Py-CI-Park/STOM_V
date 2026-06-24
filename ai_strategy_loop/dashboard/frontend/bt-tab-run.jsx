/* Backtest workbench tab — 실행 컨트롤·스윕 빌더·결과 라이브러리 묶음 (split from backtest.jsx).
   buy/sell 선택 + 기간/tf/engines + 모드(백테스트·최적화·WFO·스윕) + 잡 카드/이력/폴링 + WS 라이브,
   스윕 파라미터 빌더([변수명][min][max][step]), 결과 라이브러리(태그·메모·즐겨찾기·A/B 비교).

   모든 fetch 는 무예외(실패→빈 상태+재시도), AbortSignal.timeout, 폴링은 running 중에만.
*/
// Track Z — dual-safe ESM imports from the in-bundle definers. KEEP each on ONE physical line.
import { useState_bt, useEffect_bt, useCallback_bt, useRef_bt, useMemo_bt, _btFetchJson, _btPostJson, _btWsUrl, _BT_JOB_BADGE, _BT_MODE_RUN_LABEL, _BT_MODE_TIP, _BT_START_EG, _BT_END_EG, _btElapsed, _btSweepRowCount, _btSweepValueCount } from "./bt-tab-utils.jsx";

// ===========================================================================
// 2b. 스윕 파라미터 빌더 — [변수명][min][max][step] 행 추가/삭제 → sweep 스펙으로 직렬화.
//   백엔드 /bt/run 이 sweep_spec(행 배열)을 받아 게이트된 _database/ 임시 JSON 으로 쓰고
//   CLI --params 경로로 잇는다. CLI 계약은 {변수명:[값,...]} 명시 값 리스트이므로(2026-06-13
//   cli/sweep.generate_combinations 실측), 각 행의 min/max/step 은 백엔드가 값 리스트로 펼친다.
//   유효 행 수/값 개수 추정 헬퍼(_btSweepRowCount·_btSweepValueCount)는 bt-tab-utils 에서 공유.
// ===========================================================================
function _SweepParamBuilder({ rows, onChange, disabled }) {
  const safeRows = Array.isArray(rows) ? rows : [];
  const setRow = (i, patch) => {
    const next = safeRows.map((r, idx) => (idx === i ? Object.assign({}, r, patch) : r));
    onChange(next);
  };
  const addRow = () => onChange(safeRows.concat([{ name: "", min: "", max: "", step: "" }]));
  const removeRow = (i) => onChange(safeRows.filter((_, idx) => idx !== i));

  // 유효 행들의 데카르트 곱 추정(빈 변수명 제외, 값 0개 행은 곱에서 제외).
  let comboEst = 1;
  let validCount = 0;
  safeRows.forEach(r => {
    if (!r || !String(r.name || "").trim()) return;
    const vc = _btSweepValueCount(r);
    if (vc > 0) { comboEst *= vc; validCount += 1; }
  });
  if (validCount === 0) comboEst = 0;

  return (
    <div className="field" style={{ flex: 1, minWidth: 320 }}>
      <label>스윕 변수 빌더 (변수명 · 최소 · 최대 · 간격)</label>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {safeRows.length === 0 && (
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
            변수 행을 추가하세요(예: avg_time 60~180 간격 60 → 60·120·180).
          </div>
        )}
        {safeRows.map((r, i) => (
          <div key={i} style={{ display: "flex", gap: 4, alignItems: "center" }}>
            <input className="input mono" value={r.name || ""} disabled={disabled}
                   onChange={e => setRow(i, { name: e.target.value })}
                   placeholder="변수명 (예: avg_time)" spellCheck={false}
                   style={{ flex: 1, minWidth: 110, fontSize: 11 }} />
            <input className="input" type="number" value={r.min == null ? "" : r.min} disabled={disabled}
                   onChange={e => setRow(i, { min: e.target.value })}
                   placeholder="min" style={{ width: 64, fontSize: 11 }} />
            <input className="input" type="number" value={r.max == null ? "" : r.max} disabled={disabled}
                   onChange={e => setRow(i, { max: e.target.value })}
                   placeholder="max" style={{ width: 64, fontSize: 11 }} />
            <input className="input" type="number" value={r.step == null ? "" : r.step} disabled={disabled}
                   onChange={e => setRow(i, { step: e.target.value })}
                   placeholder="step" style={{ width: 64, fontSize: 11 }} />
            {(r.index != null || r.default != null) && (
              <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)", minWidth: 92 }}>
                {r.index != null ? `#${r.index}` : ""}{r.default != null ? ` 기본 ${r.default}` : ""}
              </span>
            )}
            <button className="btn ghost sm" onClick={() => removeRow(i)} disabled={disabled}
                    title="이 변수 행 삭제" style={{ padding: "2px 8px" }}>✕</button>
          </div>
        ))}
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn ghost sm" onClick={addRow} disabled={disabled}>+ 변수 추가</button>
          {validCount > 0 && (
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
              예상 조합 {comboEst}개 ({validCount}개 변수)
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ===========================================================================
// 3. 백테스트 실행 패널 — buy/sell 선택, 기간/tf/engines, 잡 카드 + 이력 + 폴링.
// ===========================================================================
function BtRunPanel({ baseUrl, isDemo, libNames, onResult, compareA, onCompareB, onJobs,
                      buy, sell, onBuy, onSell, reloadJobsKey }) {
  const [start, setStart] = useState_bt("");
  const [end, setEnd] = useState_bt("");
  const [timeframe, setTimeframe] = useState_bt("min");
  const [engines, setEngines] = useState_bt(4);
  const [mode, setMode] = useState_bt("backtest");      // backtest | optimize | wfo | sweep.
  const [paramSpace, setParamSpace] = useState_bt("");  // optimize/wfo 탐색공간 JSON 경로.
  // wfo(전진분석) 입력.
  const [trainWindow, setTrainWindow] = useState_bt("");
  const [testWindow, setTestWindow] = useState_bt("");
  const [stepDays, setStepDays] = useState_bt("");       // wfo/sweep rolling 공용.
  // sweep 입력.
  const [sweepAction, setSweepAction] = useState_bt("param");  // param | rolling.
  const [sweepParams, setSweepParams] = useState_bt("");       // sweep param 조합 JSON 경로(파일 폴백).
  const [sweepRows, setSweepRows] = useState_bt([{ name: "", min: "", max: "", step: "" }]);  // 빌더 행.
  const [sweepInputMode, setSweepInputMode] = useState_bt("builder");  // builder | file.
  const [windowDays, setWindowDays] = useState_bt("");         // sweep rolling 윈도우 크기.
  const [range, setRange] = useState_bt(null);          // /bt/data_range
  const [jobs, setJobs] = useState_bt([]);              // 이력
  const [activeJob, setActiveJob] = useState_bt(null);  // 현재 추적 job record
  const [runErr, setRunErr] = useState_bt("");
  const [showLog, setShowLog] = useState_bt(false);
  const [selectedJobId, setSelectedJobId] = useState_bt("");
  const [legacyVars, setLegacyVars] = useState_bt(null);
  const [legacyVarsBusy, setLegacyVarsBusy] = useState_bt(false);

  // 데이터 가용 범위 로드.
  useEffect_bt(() => {
    if (isDemo || !baseUrl) { setRange(null); return; }
    _btFetchJson(baseUrl + "/bt/data_range", 5000).then(setRange).catch(() => setRange(null));
  }, [baseUrl, isDemo]);

  // 잡 이력 로드(결과 라이브러리가 검색/필터하므로 전체를 끌어온다).
  const loadJobs = useCallback_bt(() => {
    if (isDemo || !baseUrl) { setJobs([]); return; }
    _btFetchJson(baseUrl + "/bt/jobs", 4000)
      .then(j => setJobs(Array.isArray(j && j.jobs) ? j.jobs : []))
      .catch(() => {});
  }, [baseUrl, isDemo]);

  useEffect_bt(() => { loadJobs(); }, [loadJobs, reloadJobsKey]);

  // 잡 목록이 바뀌면 부모로 끌어올린다(포트폴리오 패널이 완료 잡을 소비).
  useEffect_bt(() => { onJobs && onJobs(jobs); }, [jobs, onJobs]);

  // 추적 대상 job_id(WS/폴링 공용). 활성 잡이 running/pending 이면 그 id.
  const trackId = activeJob && (activeJob.status === "running" || activeJob.status === "pending")
    ? activeJob.job_id : null;
  // WS 연결 성공 여부 ref — 성공 시 폴링을 끈다(폴백 전용).
  const wsOkRef = useRef_bt(false);

  // 라이브 잡 WebSocket — running/pending 일 때 구독. 실패 시 폴링 폴백(무예외).
  useEffect_bt(() => {
    wsOkRef.current = false;
    if (isDemo || !baseUrl || !trackId) return;
    let ws = null;
    let closedByUs = false;
    try {
      const wsUrl = _btWsUrl(baseUrl, "/bt/ws_job?job_id=" + encodeURIComponent(trackId));
      ws = new WebSocket(wsUrl);
    } catch (e) { return; }
    ws.onopen = () => { wsOkRef.current = true; };
    ws.onmessage = (ev) => {
      let m = null;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (!m || m.error) { return; }
      wsOkRef.current = true;
      // WS 페이로드를 activeJob 형태로 머지(job 카드가 기대하는 필드 유지).
      setActiveJob(prev => Object.assign({}, prev, {
        job_id: m.job_id, status: m.status, progress: m.progress,
        phase: m.phase, message: m.message, log_tail: m.log_tail || (prev && prev.log_tail) || [],
      }));
      if (m.terminal) {
        loadJobs();
        _btFetchJson(baseUrl + "/bt/job?job_id=" + encodeURIComponent(m.job_id), 4000)
          .then(j => { if (j && j.available) setActiveJob(j); })
          .catch(() => {});
      }
    };
    ws.onerror = () => { wsOkRef.current = false; };
    ws.onclose = () => { if (!closedByUs) { /* 폴링 폴백이 이어받음 */ } };
    return () => { closedByUs = true; try { ws && ws.close(); } catch (e) {} };
  }, [baseUrl, isDemo, trackId, loadJobs]);

  // 폴링 폴백 — WS 미연결일 때만 2초 간격(WS 성공 시 즉시 중단).
  useEffect_bt(() => {
    if (isDemo || !baseUrl || !trackId) return;
    const id = setInterval(() => {
      if (wsOkRef.current) return;   // WS 가 살아있으면 폴링은 쉰다(폴백 전용).
      _btFetchJson(baseUrl + "/bt/job?job_id=" + encodeURIComponent(trackId), 4000)
        .then(j => {
          if (j && j.available) {
            setActiveJob(j);
            if (j.status !== "running" && j.status !== "pending") { loadJobs(); }
          }
        })
        .catch(() => {});
    }, 2000);
    return () => clearInterval(id);
  }, [baseUrl, isDemo, trackId, loadJobs]);

  // B2 — 잡이 성공/거래0건으로 종결되면 결과를 자동 선택(부모가 결과 분석 탭으로 전환).
  //   같은 잡을 두 번 자동선택하지 않도록 마지막 자동선택 id 를 기억한다.
  const autoPickedRef = useRef_bt("");
  useEffect_bt(() => {
    if (!activeJob || isDemo) return;
    const actions = Array.isArray(activeJob.open_actions) ? activeJob.open_actions : [];
    const hasActionTaxonomy = actions.length > 0 || activeJob.openable != null
      || activeJob.status_kind || activeJob.artifact_state;
    const statusKind = activeJob.status_kind || activeJob.status;
    const successAutoOpen = statusKind === "success" || statusKind === "no_trades";
    const legacySuccessAutoOpen = !hasActionTaxonomy
      && (activeJob.status === "success" || activeJob.status === "no_trades");
    const canOpenByTaxonomy = actions.includes("open_result") || activeJob.openable === true;
    const autoOpen = activeJob.job_id
      && ((hasActionTaxonomy && successAutoOpen && canOpenByTaxonomy) || legacySuccessAutoOpen)
      && autoPickedRef.current !== activeJob.job_id;
    if (autoOpen) {
      autoPickedRef.current = activeJob.job_id;
      onResult && onResult(activeJob.job_id);
    }
  }, [activeJob, isDemo, onResult]);

  const tfRange = range ? range[timeframe] : null;

  const submit = () => {
    if (isDemo) return;
    setRunErr("");
    const payload = {
      buy: (buy || "").trim(), sell: (sell || "").trim(),
      start: parseInt(start, 10) || 0, end: parseInt(end, 10) || 0,
      timeframe, engines: parseInt(engines, 10) || 4,
      mode,
    };
    if (!payload.buy || !payload.sell) { setRunErr("매수/매도 조건식을 선택하세요."); return; }
    if (!/^\d{8}$/.test(String(start)) || !/^\d{8}$/.test(String(end))) {
      setRunErr("기간은 YYYYMMDD 8자리로 입력하세요."); return;
    }
    if (mode === "optimize") {
      const ps = (paramSpace || "").trim();
      if (!ps) { setRunErr("최적화 모드는 파라미터 탐색공간 JSON 경로가 필요합니다."); return; }
      payload.param_space = ps;
    } else if (mode === "wfo") {
      const tr = parseInt(trainWindow, 10) || 0;
      const te = parseInt(testWindow, 10) || 0;
      if (tr < 1 || te < 1) { setRunErr("전진분석은 훈련·테스트 윈도우(일, 1 이상)가 필요합니다."); return; }
      payload.train_window_days = tr;
      payload.test_window_days = te;
      if (stepDays) payload.step_days = parseInt(stepDays, 10) || 0;
      if ((paramSpace || "").trim()) payload.param_space = (paramSpace || "").trim();
      payload.opt_objective = "tpi";
      payload.opt_method = "grid";
    } else if (mode === "sweep") {
      payload.sweep_action = sweepAction;
      if (sweepAction === "rolling") {
        const wd = parseInt(windowDays, 10) || 0;
        const sd = parseInt(stepDays, 10) || 0;
        if (wd < 1 || sd < 1) { setRunErr("롤링 스윕은 윈도우·이동(일, 1 이상)이 필요합니다."); return; }
        payload.window_days = wd;
        payload.step_days = sd;
      } else if (sweepInputMode === "file") {
        const sp = (sweepParams || "").trim();
        if (!sp) { setRunErr("파라미터 스윕은 조합 JSON 경로가 필요합니다."); return; }
        payload.sweep_params = sp;
      } else {
        // 빌더 모드 — 유효 행을 sweep_spec 으로 보낸다(백엔드가 게이트 임시 JSON 으로 직렬화).
        const validRows = (sweepRows || [])
          .filter(r => r && String(r.name || "").trim())
          .map(r => ({
            name: String(r.name).trim(),
            min: Number(r.min), max: Number(r.max), step: Number(r.step),
          }));
        if (_btSweepRowCount(sweepRows) < 1) {
          setRunErr("파라미터 스윕은 변수 행이 1개 이상 필요합니다(변수명 입력)."); return;
        }
        const bad = validRows.find(r => !isFinite(r.min) || !isFinite(r.max) || !isFinite(r.step));
        if (bad) { setRunErr(`변수 '${bad.name}' 의 min/max/step 을 숫자로 입력하세요.`); return; }
        payload.sweep_spec = validRows;
      }
    }
    _btPostJson(baseUrl + "/bt/run", payload, 8000)
      .then(j => {
        if (j && j.status === "ok" && j.job_id) {
          setActiveJob({ job_id: j.job_id, status: "pending", progress: 0, spec: payload, log_tail: [] });
          setSelectedJobId(j.job_id);
          loadJobs();
        } else {
          setRunErr((j && j.message) || "실행 실패");
        }
      })
      .catch(e => setRunErr("실행 실패: " + e));
  };

  const cancelJob = (jobId) => {
    if (isDemo || !jobId) return;
    _btPostJson(baseUrl + "/bt/job/cancel", { job_id: jobId }, 5000)
      .then(() => {
        _btFetchJson(baseUrl + "/bt/job?job_id=" + encodeURIComponent(jobId), 4000)
          .then(j => { if (j && j.available) setActiveJob(j); loadJobs(); })
          .catch(() => {});
      })
      .catch(() => {});
  };

  // 잡 이력 클릭 → 결과 로드(부모로 위임).
  const pickJob = (jobId) => {
    setSelectedJobId(jobId);
    onResult && onResult(jobId);
  };

  // 자급자족 HTML 리포트를 새 탭으로 연다(외부 리소스 0 — /bt/report 가 완성 HTML 반환).
  const openReport = (jobId) => {
    if (isDemo || !baseUrl || !jobId) return;
    const url = baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId);
    try { window.open(url, "_blank", "noopener"); } catch (e) {}
  };

  const importSelfVars = () => {
    if (isDemo || !baseUrl || !buy) {
      setRunErr("self.vars를 가져올 매수 조건식을 선택하세요.");
      return;
    }
    setLegacyVarsBusy(true);
    setRunErr("");
    _btFetchJson(baseUrl + "/bt/legacy/self_vars?kind=buy&name=" + encodeURIComponent(buy), 6000)
      .then(j => {
        setLegacyVars(j || null);
        if (j && Array.isArray(j.rows) && j.rows.length > 0) {
          setMode("sweep");
          setSweepAction("param");
          setSweepInputMode("builder");
          setSweepRows(j.rows.map(r => ({ name: r.name, min: r.min, max: r.max, step: r.step, index: r.index, default: r.default })));
        } else {
          setRunErr((j && j.message) || "self.vars 범위를 찾지 못했습니다.");
        }
      })
      .catch(e => setRunErr("self.vars 해석 실패: " + e))
      .finally(() => setLegacyVarsBusy(false));
  };

  const pct = activeJob ? Math.round((activeJob.progress || 0) * 100) : 0;
  const tracking = activeJob && (activeJob.status === "running" || activeJob.status === "pending");
  const activeActions = Array.isArray(activeJob && activeJob.open_actions) ? activeJob.open_actions : [];
  const activeHasActionTaxonomy = activeJob && (activeActions.length > 0 || activeJob.openable != null
    || activeJob.status_kind || activeJob.artifact_state);
  const activeStatusKind = activeJob ? (activeJob.status_kind || activeJob.status) : "pending";
  const activeBadge = activeJob
    ? (_BT_JOB_BADGE[activeStatusKind] || _BT_JOB_BADGE[activeJob.status] || _BT_JOB_BADGE.pending)
    : _BT_JOB_BADGE.pending;
  const activeCanOpen = activeJob && (activeActions.includes("open_result") || activeJob.openable === true
    || (!activeHasActionTaxonomy && (activeJob.status === "success" || activeJob.status === "no_trades")));
  const activeCanReport = activeJob && (activeActions.includes("open_report")
    || (!activeHasActionTaxonomy && activeJob.status === "success"));

  return (
    <div className="panel" style={{ background: "var(--bg-1)" }}>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {/* 전폭 실행 컨트롤 바 — 모드 토글 · 매수/매도 · 기간 · tf/engines · 대형 실행 버튼 */}
        <div style={{ display: "flex", flexWrap: "wrap", alignItems: "flex-end", gap: 10 }}>
          {/* 모드 토글 [백테스트|최적화|WFO|스윕] */}
          <div className="field" style={{ minWidth: 240 }}>
            <label>모드</label>
            <div style={{ display: "flex", gap: 4 }}>
              {[["backtest", "백테스트"], ["optimize", "최적화"], ["wfo", "WFO"], ["sweep", "스윕"]].map(([m, lbl]) => (
                <button key={m} onClick={() => setMode(m)} className="mono" disabled={isDemo}
                  title={_BT_MODE_TIP[m]} data-tip={_BT_MODE_TIP[m]}
                  style={{
                    flex: 1, padding: "6px 8px", fontSize: 11, borderRadius: 5,
                    border: "1px solid " + (mode === m ? "var(--amber)" : "var(--line-1)"),
                    background: mode === m ? "rgba(240,179,90,0.1)" : "transparent",
                    color: mode === m ? "var(--amber)" : "var(--ink-2)", cursor: "pointer",
                  }}>
                  {lbl}
                </button>
              ))}
            </div>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>매수 조건식</label>
            <select className="select" value={buy} onChange={e => onBuy(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {libNames.buy.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 160 }}>
            <label>매도 조건식</label>
            <select className="select" value={sell} onChange={e => onSell(e.target.value)} disabled={isDemo}>
              <option value="">— 선택 —</option>
              {libNames.sell.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
          <div className="field" style={{ minWidth: 110 }}>
            <label>시작 (YYYYMMDD)</label>
            <input className="input" value={start} onChange={e => setStart(e.target.value)}
                   placeholder={_BT_START_EG} spellCheck={false} disabled={isDemo} />
          </div>
          <div className="field" style={{ minWidth: 110 }}>
            <label>종료 (YYYYMMDD)</label>
            <input className="input" value={end} onChange={e => setEnd(e.target.value)}
                   placeholder={_BT_END_EG} spellCheck={false} disabled={isDemo} />
          </div>
          <div className="field" style={{ minWidth: 100 }}>
            <label>시간단위</label>
            <select className="select" value={timeframe} onChange={e => setTimeframe(e.target.value)} disabled={isDemo}>
              <option value="min">분봉 (min)</option>
              <option value="tick">틱 (tick)</option>
            </select>
          </div>
          <div className="field" style={{ minWidth: 76 }}>
            <label>엔진 수</label>
            <input className="input" type="number" min="1" max="16" value={engines}
                   onChange={e => setEngines(e.target.value)} disabled={isDemo} />
          </div>
          {/* 대형 실행 버튼 — 폴드 위 가시성 핵심 */}
          <button className="btn primary" onClick={submit}
                  disabled={isDemo || tracking}
                  style={{ fontSize: 14, padding: "10px 22px", minWidth: 120 }}>
            ▸ {_BT_MODE_RUN_LABEL[mode] || "백테스트 실행"}
          </button>
          <button className="btn ghost sm" onClick={loadJobs} disabled={isDemo}>↻ 이력</button>
          <button className="btn ghost sm" onClick={importSelfVars}
                  disabled={isDemo || legacyVarsBusy || !buy}
                  title="선택된 매수 조건식의 legacy self.vars 범위를 실행 없이 스윕 빌더 행으로 변환">
            {legacyVarsBusy ? "self.vars 해석…" : "self.vars → 스윕 빌더"}
          </button>
        </div>

        {/* optimize 전용 — 파라미터 탐색공간 JSON 경로 */}
        {mode === "optimize" && (
          <div className="field">
            <label>파라미터 탐색공간 JSON 경로 (_database/ 또는 ai_strategy_loop/state/ 하위)</label>
            <input className="input mono" value={paramSpace} onChange={e => setParamSpace(e.target.value)}
                   placeholder="_database/param_space.json" spellCheck={false} disabled={isDemo}
                   style={{ fontSize: 11 }} />
          </div>
        )}

        {/* wfo 전용 — 전진분석 윈도우 입력(훈련/테스트/이동일, 선택 탐색공간 JSON) */}
        {mode === "wfo" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
            <div className="field" style={{ minWidth: 120 }}>
              <label>훈련 윈도우 (일)</label>
              <input className="input" type="number" min="1" value={trainWindow}
                     onChange={e => setTrainWindow(e.target.value)} placeholder="60" disabled={isDemo} />
            </div>
            <div className="field" style={{ minWidth: 120 }}>
              <label>테스트 윈도우 (일)</label>
              <input className="input" type="number" min="1" value={testWindow}
                     onChange={e => setTestWindow(e.target.value)} placeholder="20" disabled={isDemo} />
            </div>
            <div className="field" style={{ minWidth: 120 }}>
              <label>이동 간격 (일, 선택)</label>
              <input className="input" type="number" min="1" value={stepDays}
                     onChange={e => setStepDays(e.target.value)} placeholder="테스트 윈도우" disabled={isDemo} />
            </div>
            <div className="field" style={{ flex: 1, minWidth: 200 }}>
              <label>탐색공간 JSON 경로 (선택 — 미지정 시 고정 파라미터)</label>
              <input className="input mono" value={paramSpace} onChange={e => setParamSpace(e.target.value)}
                     placeholder="_database/param_space.json" spellCheck={false} disabled={isDemo}
                     style={{ fontSize: 11 }} />
            </div>
          </div>
        )}

        {/* sweep 전용 — 하위 동작 토글(param|rolling) + 동작별 입력 */}
        {mode === "sweep" && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
            <div className="field" style={{ minWidth: 160 }}>
              <label>스윕 종류</label>
              <div style={{ display: "flex", gap: 4 }}>
                {[["param", "파라미터"], ["rolling", "날짜 롤링"]].map(([a, lbl]) => (
                  <button key={a} onClick={() => setSweepAction(a)} className="mono" disabled={isDemo}
                    style={{
                      flex: 1, padding: "6px 8px", fontSize: 11, borderRadius: 5,
                      border: "1px solid " + (sweepAction === a ? "var(--amber)" : "var(--line-1)"),
                      background: sweepAction === a ? "rgba(240,179,90,0.1)" : "transparent",
                      color: sweepAction === a ? "var(--amber)" : "var(--ink-2)", cursor: "pointer",
                    }}>
                    {lbl}
                  </button>
                ))}
              </div>
            </div>
            {sweepAction === "param" ? (
              <>
                {/* 입력 방식 토글 [빌더|파일] — 빌더는 행을 sweep_spec 으로, 파일은 경로를 보낸다. */}
                <div className="field" style={{ minWidth: 150 }}>
                  <label>입력 방식</label>
                  <div style={{ display: "flex", gap: 4 }}>
                    {[["builder", "빌더"], ["file", "파일 경로"]].map(([m, lbl]) => (
                      <button key={m} onClick={() => setSweepInputMode(m)} className="mono" disabled={isDemo}
                        style={{
                          flex: 1, padding: "6px 8px", fontSize: 11, borderRadius: 5,
                          border: "1px solid " + (sweepInputMode === m ? "var(--amber)" : "var(--line-1)"),
                          background: sweepInputMode === m ? "rgba(240,179,90,0.1)" : "transparent",
                          color: sweepInputMode === m ? "var(--amber)" : "var(--ink-2)", cursor: "pointer",
                        }}>
                        {lbl}
                      </button>
                    ))}
                  </div>
                </div>
                {sweepInputMode === "builder" ? (
                  <_SweepParamBuilder rows={sweepRows} onChange={setSweepRows} disabled={isDemo} />
                ) : (
                  <div className="field" style={{ flex: 1, minWidth: 220 }}>
                    <label>스윕 조합 JSON 경로 (_database/ 또는 ai_strategy_loop/state/ 하위)</label>
                    <input className="input mono" value={sweepParams} onChange={e => setSweepParams(e.target.value)}
                           placeholder="_database/sweep_params.json" spellCheck={false} disabled={isDemo}
                           style={{ fontSize: 11 }} />
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="field" style={{ minWidth: 120 }}>
                  <label>윈도우 (일)</label>
                  <input className="input" type="number" min="1" value={windowDays}
                         onChange={e => setWindowDays(e.target.value)} placeholder="20" disabled={isDemo} />
                </div>
                <div className="field" style={{ minWidth: 120 }}>
                  <label>이동 간격 (일)</label>
                  <input className="input" type="number" min="1" value={stepDays}
                         onChange={e => setStepDays(e.target.value)} placeholder="5" disabled={isDemo} />
                </div>
              </>
            )}
          </div>
        )}

        {/* 가용 범위 안내 + 실행 오류 */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
          {tfRange && (
            <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)" }}>
              가용 {timeframe}: 일일DB {tfRange.count}일
              {tfRange.back_range ? ` · back ${tfRange.back_range.start}~${tfRange.back_range.end}` : ""}
            </span>
          )}
          {runErr && <span className="mono" style={{ fontSize: 11, color: "var(--red)" }}>{runErr}</span>}
          {legacyVars && (
            <span className="mono" style={{ fontSize: 10.5, color: legacyVars.available ? "var(--teal)" : "var(--ink-3)" }}>
              {legacyVars.adapter || "self.vars"} · {(legacyVars.rows || []).length}개 행 · 실행 없이 미리보기
            </span>
          )}
          {compareA && (
            <span className="mono tag-slim" style={{ fontSize: 9.5, color: "var(--amber)", marginLeft: "auto" }}
                  title="비교 기준(A) 고정됨 — 결과 라이브러리에서 다른 잡의 '비교(B)' 를 누르세요">
              비교 A={compareA}
            </span>
          )}
        </div>

        {/* 활성 잡 카드 */}
        {activeJob && (
          <div style={{ border: "1px solid var(--line-1)", borderRadius: 6, padding: 10, background: "var(--bg-0)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <span className={activeBadge.cls}>
                <span className={"dot " + (activeJob.status === "running" ? "pulse-dot" : "")}></span>
                {activeBadge.txt}
              </span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{activeJob.job_id}</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", marginLeft: "auto" }}>
                {_btElapsed(activeJob)}
              </span>
            </div>
            <div className="progress-track">
              <div className={"progress-fill " + (activeJob.status === "running" ? "running" : "")} style={{ width: pct + "%" }}></div>
            </div>
            {activeJob.message && (
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{activeJob.message}</div>
            )}
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {tracking && (
                <button className="btn danger sm" onClick={() => cancelJob(activeJob.job_id)}>◼ 중지</button>
              )}
              {activeCanOpen && (
                <button className="btn ghost sm" onClick={() => pickJob(activeJob.job_id)}>결과 보기</button>
              )}
              {activeCanReport && (
                <button className="btn ghost sm" onClick={() => openReport(activeJob.job_id)}
                        title="자급자족 HTML 리포트를 새 탭으로 열기">📄 리포트</button>
              )}
              {(activeJob.log_tail && activeJob.log_tail.length > 0) && (
                <button className="btn ghost sm" onClick={() => setShowLog(s => !s)}>
                  {showLog ? "로그 접기" : "로그 보기"}
                </button>
              )}
            </div>
            {showLog && activeJob.log_tail && activeJob.log_tail.length > 0 && (
              <pre className="process-log-pane" style={{ margin: 0 }}>
                {activeJob.log_tail.join("\n")}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ===========================================================================
// 3b. 결과 라이브러리 — 잡 이력 + 태그·메모·즐겨찾기·검색·필터(결과 체계 관리).
//   완료 잡을 클릭하면 결과를 로드(onResult). 메타는 POST /bt/job/meta 로 영속.
// ===========================================================================
function BtResultLibrary({ baseUrl, isDemo, jobs, onResult, selectedJobId, onReload,
                           compareA, onSetCompareA, onCompareB }) {
  const [query, setQuery] = useState_bt("");
  const [favOnly, setFavOnly] = useState_bt(false);
  const [tagFilter, setTagFilter] = useState_bt("");
  const [editing, setEditing] = useState_bt("");      // 메타 편집 중인 job_id.
  const [tagDraft, setTagDraft] = useState_bt("");
  const [memoDraft, setMemoDraft] = useState_bt("");

  const openReport = (jobId) => {
    if (isDemo || !baseUrl || !jobId) return;
    try { window.open(baseUrl + "/bt/report?job_id=" + encodeURIComponent(jobId), "_blank", "noopener"); } catch (e) {}
  };

  const rerunJob = (j) => {
    if (isDemo || !baseUrl || !j) return;
    const spec = j.rerun_spec || j.spec || {};
    if (!spec.buy || !spec.sell || !spec.start || !spec.end) return;
    _btPostJson(baseUrl + "/bt/run", spec, 8000)
      .then(() => { onReload && onReload(); })
      .catch(() => {});
  };
  const recoverJob = (j) => {
    if (isDemo || !j || !j.job_id) return;
    const actions = Array.isArray(j.open_actions) ? j.open_actions : [];
    const hasOpenableArtifact = actions.includes("open_result") || j.openable === true;
    if (hasOpenableArtifact && onResult) {
      onResult(j.job_id);
      return;
    }
    rerunJob(j);
  };


  const saveMeta = (jobId, patch) => {
    if (isDemo || !baseUrl || !jobId) return;
    _btPostJson(baseUrl + "/bt/job/meta", Object.assign({ job_id: jobId }, patch), 6000)
      .then(() => { onReload && onReload(); })
      .catch(() => {});
  };

  const toggleFav = (j) => saveMeta(j.job_id, { favorite: !j.favorite });

  const beginEdit = (j) => {
    setEditing(j.job_id);
    setTagDraft((j.tags || []).join(", "));
    setMemoDraft(j.memo || "");
  };
  const commitEdit = (jobId) => {
    const tags = tagDraft.split(",").map(s => s.trim()).filter(Boolean);
    saveMeta(jobId, { tags, memo: memoDraft });
    setEditing("");
  };

  // 전체 태그 어휘(필터 셀렉터용).
  const allTags = useMemo_bt(() => {
    const s = new Set();
    (jobs || []).forEach(j => (j.tags || []).forEach(t => s.add(t)));
    return Array.from(s).sort();
  }, [jobs]);

  const filtered = useMemo_bt(() => {
    const q = query.trim().toLowerCase();
    let out = (jobs || []);
    if (favOnly) out = out.filter(j => j.favorite);
    if (tagFilter) out = out.filter(j => (j.tags || []).includes(tagFilter));
    if (q) out = out.filter(j => {
      const hay = (j.job_id + " " + (j.memo || "") + " " + (j.tags || []).join(" ")
        + " " + ((j.spec && (j.spec.buy + " " + j.spec.sell)) || "")).toLowerCase();
      return hay.includes(q);
    });
    // 즐겨찾기 우선 정렬(이후 원래 최신순 유지).
    return out.slice().sort((a, b) => (b.favorite ? 1 : 0) - (a.favorite ? 1 : 0));
  }, [jobs, query, favOnly, tagFilter]);

  return (
    <div className="panel">
      <div className="panel-hd">
        <div className="panel-hd-title">
          <span className="dot" style={{ background: "var(--amber)" }}></span>
          결과 라이브러리
          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", marginLeft: 6 }}>
            {filtered.length}/{(jobs || []).length}
          </span>
        </div>
        <button className="btn ghost sm" onClick={onReload} disabled={isDemo}>↻</button>
      </div>
      <div className="panel-bd" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {isDemo ? (
          <div className="research-empty">데모 모드 — 백엔드 연결 시 결과 이력이 표시됩니다.</div>
        ) : (
          <>
            {/* 검색·필터 */}
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <input className="input" placeholder="잡/메모/태그/전략 검색…" value={query}
                     onChange={e => setQuery(e.target.value)} spellCheck={false}
                     style={{ flex: 1, minWidth: 140 }} />
              <button className="mono" onClick={() => setFavOnly(f => !f)}
                style={{
                  padding: "5px 9px", fontSize: 11, borderRadius: 5, cursor: "pointer",
                  border: "1px solid " + (favOnly ? "var(--amber)" : "var(--line-1)"),
                  background: favOnly ? "rgba(240,179,90,0.1)" : "transparent",
                  color: favOnly ? "var(--amber)" : "var(--ink-2)",
                }}>
                ★ 즐겨찾기
              </button>
              {allTags.length > 0 && (
                <select className="select" value={tagFilter} onChange={e => setTagFilter(e.target.value)}
                        style={{ maxWidth: 140 }}>
                  <option value="">전체 태그</option>
                  {allTags.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              )}
            </div>
            {/* 목록 */}
            {filtered.length === 0 ? (
              <div className="research-empty">{(jobs || []).length === 0 ? "실행 이력이 없습니다" : "조건에 맞는 결과 없음"}</div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 360, overflowY: "auto" }}>
                {filtered.map(j => {
                  const statusKind = j.status_kind || j.status;
                  const b = _BT_JOB_BADGE[statusKind] || _BT_JOB_BADGE[j.status] || _BT_JOB_BADGE.pending;
                  const actions = Array.isArray(j.open_actions) ? j.open_actions : [];
                  const hasActionTaxonomy = actions.length > 0 || j.openable != null || j.status_kind || j.artifact_state;
                  const clickable = actions.includes("open_result") || j.openable === true
                    || (!hasActionTaxonomy && (j.status === "success" || j.status === "no_trades"));
                  const active = j.job_id === selectedJobId;
                  const canCompare = clickable && compareA && onCompareB && j.job_id !== compareA;
                  const isEditing = editing === j.job_id;
                  return (
                    <div key={j.job_id}
                      style={{
                        display: "flex", flexDirection: "column", gap: 5, padding: "7px 9px", borderRadius: 5,
                        border: "1px solid " + (active ? "var(--teal-dim)" : "var(--line-1)"),
                        background: active ? "rgba(76,214,179,0.06)" : "var(--bg-0)",
                        opacity: clickable ? 1 : 0.7,
                      }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <button onClick={() => toggleFav(j)} title="즐겨찾기 토글"
                          style={{ background: "transparent", border: 0, cursor: "pointer", fontSize: 13, padding: 0,
                                   color: j.favorite ? "var(--amber)" : "var(--ink-3)" }}>
                          {j.favorite ? "★" : "☆"}
                        </button>
                        <button onClick={() => clickable && onResult(j.job_id)} disabled={!clickable}
                          title={clickable ? "결과 상세 열기" : (j.artifact_state || j.message || "열 수 있는 결과 아티팩트가 없습니다")}
                          style={{
                            display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 0,
                            background: "transparent", border: 0, padding: 0, textAlign: "left",
                            cursor: clickable ? "pointer" : "default",
                          }}>
                          <span className={b.cls} style={{ flexShrink: 0 }}>{b.txt}</span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--ink-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", flex: 1 }}>
                            {j.job_id}
                          </span>
                          <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", flexShrink: 0 }}>{_btElapsed(j)}</span>
                        </button>
                        {actions.includes("open_report") && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => openReport(j.job_id)} title="HTML 리포트 새 탭">📄</button>
                        )}
                        {actions.includes("recover_result") && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => recoverJob(j)} title="아티팩트가 남아 있으면 열고, 없으면 같은 조건으로 재실행">복구</button>
                        )}
                        {actions.includes("rerun_same_condition") && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => rerunJob(j)} title="같은 조건으로 새 백테스트 실행">재실행</button>
                        )}
                        {clickable && onSetCompareA && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => onSetCompareA(j.job_id)} title="비교 기준(A) 으로 고정">A</button>
                        )}
                        {canCompare && (
                          <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                  onClick={() => onCompareB(j.job_id)} title={"A(" + compareA + ") 와 비교"}>B</button>
                        )}
                        <button className="btn ghost sm" style={{ flexShrink: 0, fontSize: 10, padding: "2px 6px" }}
                                onClick={() => (isEditing ? setEditing("") : beginEdit(j))} title="태그·메모 편집">🏷</button>
                      </div>
                      {j.artifact_state && !isEditing && (
                        <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-3)" }}>
                          evidence {j.evidence_id || "—"} · {j.artifact_state}
                          {j.condition_identity && j.condition_identity.confidence
                            ? " · condition " + j.condition_identity.confidence : ""}
                        </div>
                      )}
                      {/* 태그·메모 표시 */}
                      {!isEditing && ((j.tags && j.tags.length > 0) || j.memo) && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, alignItems: "center" }}>
                          {(j.tags || []).map(t => (
                            <span key={t} className="tag-slim" style={{ fontSize: 9.5, color: "var(--teal)" }}>{t}</span>
                          ))}
                          {j.memo && <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>· {j.memo}</span>}
                        </div>
                      )}
                      {/* 태그·메모 편집 */}
                      {isEditing && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
                          <input className="input" value={tagDraft} onChange={e => setTagDraft(e.target.value)}
                                 placeholder="태그(쉼표 구분)" spellCheck={false} style={{ fontSize: 11 }} />
                          <input className="input" value={memoDraft} onChange={e => setMemoDraft(e.target.value)}
                                 placeholder="메모" spellCheck={false} style={{ fontSize: 11 }} />
                          <div style={{ display: "flex", gap: 6 }}>
                            <button className="btn primary sm" onClick={() => commitEdit(j.job_id)}>저장</button>
                            <button className="btn ghost sm" onClick={() => setEditing("")}>취소</button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { _SweepParamBuilder, BtRunPanel, BtResultLibrary };
