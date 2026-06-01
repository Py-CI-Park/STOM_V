/* Main app composition */
const { useState: useState_a, useEffect: useEffect_a, useCallback: useCallback_a } = React;

function App() {
  const [baseUrl, setBaseUrl] = useState_a(() => {
    return localStorage.getItem("stom_base_url") || DEFAULT_BASE;
  });
  const [pendingBase, setPendingBase] = useState_a(baseUrl);
  const [theme, setTheme] = useState_a(() => localStorage.getItem("stom_theme") || "dark");

  const { state, health, wsStatus, configSpec, send, lastReply, reconnect } = useBackend(baseUrl);

  const [settingsOpen, setSettingsOpen] = useState_a(false);
  const [approvalOpen, setApprovalOpen] = useState_a(false);
  const [codeViewGen, setCodeViewGen] = useState_a(null); // gen object

  const running = state.status === "running" || state.status === "stopping";

  useEffect_a(() => {
    localStorage.setItem("stom_base_url", baseUrl);
  }, [baseUrl]);

  useEffect_a(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("stom_theme", theme);
  }, [theme]);

  const onStart = useCallback_a((config) => {
    send({ action: "start", config });
    setSettingsOpen(false);
  }, [send]);

  const onStop = useCallback_a(() => {
    send({ action: "stop" });
  }, [send]);

  const onApprove = useCallback_a(({ userBuy, userSell }) => {
    if (!state.winner) return;
    send({
      action: "final_approval",
      buy_name: state.winner.buy_name,
      sell_name: state.winner.sell_name,
      user_buy: userBuy,
      user_sell: userSell,
    });
    setApprovalOpen(false);
  }, [send, state.winner]);

  const onViewCodeByGen = useCallback_a((genNo) => {
    const g = (state.generations || []).find(x => x.gen_no === genNo);
    if (g) setCodeViewGen(g);
  }, [state.generations]);

  // Find mdd_cap from configSpec defaults to color MDDs in the table
  const mddCap = (configSpec.find(f => f.name === "mdd_cap")?.default) ?? 15;
  // 일평균거래횟수 하한(빈도 게이트 주 기준) — 테이블에서 미달 행을 경고색으로 표시.
  const minDailyTrades = (configSpec.find(f => f.name === "min_daily_trades")?.default) ?? 0.5;
  const targetScore = (configSpec.find(f => f.name === "target_score")?.default) ?? 1.0;

  const pct = state.max_generations > 0 ? Math.min(100, (state.current_gen / state.max_generations) * 100) : 0;
  const isIdle = state.status === "idle" && state.generations.length === 0 && !running;

  return (
    <div style={{ minHeight: "100vh", padding: "16px", maxWidth: 1600, margin: "0 auto" }}>

      {/* ============= TOP BAR ============= */}
      <header style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap", marginBottom: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Logo />
            <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
              <h1 style={{ fontSize: 15, letterSpacing: ".01em" }}>
                STOM AI · 조건식 자율 진화 대시보드
              </h1>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".08em" }}>
                autonomous_strategy_loop · contract_v{health.contract_version ?? state.contract_version ?? 1}
              </span>
            </div>
          </div>

          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <ThemeToggle theme={theme} onChange={setTheme} />
            <BaseUrlControl
              value={pendingBase}
              onChange={setPendingBase}
              onApply={() => setBaseUrl(pendingBase)}
              onReconnect={reconnect}
            />
            <ConnBadge health={health} wsStatus={wsStatus} />
            <StatusBadge status={state.status} />
          </div>
        </div>

        <div style={{
          display: "flex", alignItems: "center", gap: 14,
          padding: "12px 16px",
          background: "var(--bg-1)",
          border: "1px solid var(--line-1)",
          borderRadius: 8,
        }}>
          <div style={{ minWidth: 200 }}>
            <div className="stat-label" style={{ marginBottom: 4 }}>진행도</div>
            <div className="mono" style={{ fontSize: 15, color: "var(--ink-0)" }}>
              <span style={{ color: running ? "var(--amber)" : "var(--ink-0)" }}>{state.current_gen}</span>
              <span style={{ color: "var(--ink-3)" }}> / {state.max_generations}</span>
              <span style={{ marginLeft: 8, color: "var(--ink-2)", fontSize: 11 }}>세대</span>
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <div className="progress-track">
              <div className={`progress-fill ${running ? "running" : ""}`} style={{ width: `${pct}%` }}></div>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 10.5, color: "var(--ink-3)", fontFamily: "var(--mono)" }}>
              <span>provider={state.provider}</span>
              <span>tf={state.bt_timeframe}</span>
              <span>run_id={state.run_id || "—"}</span>
              <span>{pct.toFixed(1)}%</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn primary" onClick={() => setSettingsOpen(true)} disabled={running}>
              ▸ 시작
            </button>
            <button className="btn danger" onClick={onStop} disabled={!running}>
              ◼ 정지
            </button>
          </div>
        </div>
      </header>

      {/* ============= MAIN ============= */}
      {isIdle ? (
        <IdleState onStart={() => setSettingsOpen(true)} configSpec={configSpec} />
      ) : (
        <main style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {/* 승인 export 결과 배너(final_approval 게이트는 ApprovalDialog가 유지) */}
          <ExportStatusBanner reply={lastReply} />

          <CurrentGenPanel state={state} />
          <PhaseTimeline state={state} />
          <ProcessFlowPanel state={state} />
          <PhaseDetailPanel state={state} wsStatus={wsStatus} />
          <EnginePanel state={state} wsStatus={wsStatus} />

          <div className="grid-main">
            <div style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>
              <FitnessChart state={state} target={targetScore} />
              <ProfitChart state={state} targetPct={0} />
              <EquityOverlayChart baseUrl={baseUrl} wsStatus={wsStatus} runId={state.run_id} />
              {/* O1 — 백테 상세(일별손익 막대 + 누적수익곡선): 선택 세대의 per-trade CSV 시계열 재현 */}
              <BacktestDetailChart baseUrl={baseUrl} wsStatus={wsStatus} state={state} />
              <QualityTrendChart state={state} />
              {/* 🏆 명예의 전당 — 인간 벤치마크(19전략) + AI 생성 통합(목표선 가시화) */}
              <HallOfFamePanel baseUrl={baseUrl} wsStatus={wsStatus} />
              <GenerationsTable state={state} mddCap={mddCap} minDailyTrades={minDailyTrades}
                                onViewCode={(g) => setCodeViewGen(g)} />
              {/* 운영·관찰: run 비교 콘솔(REST /runs, loop_runs.db 직접) */}
              <RunComparePanel baseUrl={baseUrl} wsStatus={wsStatus} />
            </div>
            <aside style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <BestCard best={state.best} onViewCode={onViewCodeByGen} />
              <WinnerCard winner={state.winner}
                          onApprove={() => setApprovalOpen(true)}
                          onViewCode={onViewCodeByGen} />
              {/* R8 — 활성 설정/토글 스냅샷(LoopState.active_config) LIVE 노출 */}
              <ActiveConfigPanel state={state} />
              <CostPanel state={state} cap={50000} />
              <FeedbackPanel state={state} />

              {/* ── 분석 패널 묶음 (P1~P5 live page_data 소비, demo 배지 규약) ── */}
              <SectionLabel text="진화 분석 · P1~P5" />
              {/* P2b-2 — 가정 루프(세운 가정+채택/기각 판정) 가시화. 판정된 가정이
                  있는 세대가 없으면(토글 OFF/구 상태) 패널이 null 반환해 미표시. */}
              <HypothesisPanel state={state} />
              <AutopsyPanel state={state} wsStatus={wsStatus} />
              <PopulationPanel state={state} wsStatus={wsStatus} />
              <LineagePanel state={state} wsStatus={wsStatus} />
              <MetaPanel state={state} wsStatus={wsStatus} />
              <HoldoutPanel state={state} wsStatus={wsStatus} />
            </aside>
          </div>
        </main>
      )}

      {/* ============= MODALS ============= */}
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onStart={onStart}
        configSpec={configSpec}
        disabled={running}
      />
      <ApprovalDialog
        winner={approvalOpen ? state.winner : null}
        onClose={() => setApprovalOpen(false)}
        onConfirm={onApprove}
      />
      <CodeViewer
        generation={codeViewGen}
        onClose={() => setCodeViewGen(null)}
        runId={state.run_id}
        baseUrl={baseUrl}
      />

      {/* Footer */}
      <footer style={{ marginTop: 24, padding: "12px 0", textAlign: "center", color: "var(--ink-3)", fontSize: 10.5, fontFamily: "var(--mono)" }}>
        STOM AI · STATE_CONTRACT v{state.contract_version ?? 1} · last_update {fmtTime(state.updated_at)}
      </footer>
    </div>
  );
}

// 분석 패널 묶음을 시각적으로 구분하는 작은 섹션 라벨(레이아웃 정리용).
function SectionLabel({ text }) {
  return (
    <div className="mono" style={{
      fontSize: 10.5, color: "var(--ink-3)", letterSpacing: ".12em",
      textTransform: "uppercase", padding: "2px 2px", marginTop: 4,
      borderTop: "1px solid var(--line-1)", paddingTop: 10,
    }}>
      {text}
    </div>
  );
}

function ThemeToggle({ theme, onChange }) {
  return (
    <div className="theme-toggle" role="group" aria-label="테마">
      <button className={theme === "dark" ? "active" : ""}
              onClick={() => onChange("dark")}
              data-tip="다크 모드">
        <SunMoonIcon dark /> Dark
      </button>
      <button className={theme === "light" ? "active" : ""}
              onClick={() => onChange("light")}
              data-tip="라이트 모드">
        <SunMoonIcon /> Light
      </button>
    </div>
  );
}

function SunMoonIcon({ dark }) {
  if (dark) return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <path d="M11.5 9.5A6 6 0 0 1 6 4c0-1.2.36-2.3.97-3.23A8 8 0 1 0 14.73 11a6 6 0 0 1-3.23.5z"
            fill="currentColor" />
    </svg>
  );
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
      <circle cx="8" cy="8" r="3" fill="currentColor" />
      <g stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
        <line x1="8" y1="1" x2="8" y2="2.5" />
        <line x1="8" y1="13.5" x2="8" y2="15" />
        <line x1="1" y1="8" x2="2.5" y2="8" />
        <line x1="13.5" y1="8" x2="15" y2="8" />
        <line x1="3" y1="3" x2="4" y2="4" />
        <line x1="12" y1="12" x2="13" y2="13" />
        <line x1="13" y1="3" x2="12" y2="4" />
        <line x1="4" y1="12" x2="3" y2="13" />
      </g>
    </svg>
  );
}

function Logo() {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
      <rect x="0.5" y="0.5" width="35" height="35" rx="6" fill="#0c1014" stroke="#2a3441"/>
      {/* Stylized rising-and-evolving curve */}
      <path d="M5 26 L11 22 L16 24 L21 16 L26 18 L31 9"
            stroke="#4cd6b3" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="11" cy="22" r="1.6" fill="#4cd6b3" />
      <circle cx="16" cy="24" r="1.6" fill="#4cd6b3" />
      <circle cx="21" cy="16" r="1.6" fill="#4cd6b3" />
      <circle cx="26" cy="18" r="1.6" fill="#4cd6b3" />
      <circle cx="31" cy="9" r="2.2" fill="#a594ff" stroke="#fff" strokeWidth="0.6" />
      {/* corner ticks */}
      <path d="M3 3 L7 3 M3 3 L3 7" stroke="#2a3441" strokeWidth="1" />
      <path d="M33 33 L29 33 M33 33 L33 29" stroke="#2a3441" strokeWidth="1" />
    </svg>
  );
}

function BaseUrlControl({ value, onChange, onApply, onReconnect }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6,
                  background: "var(--bg-1)", border: "1px solid var(--line-1)", borderRadius: 5, padding: "3px 6px" }}>
      <span className="mono" style={{ fontSize: 10, color: "var(--ink-3)", letterSpacing: ".08em" }}>BASE</span>
      <input className="toolbar-input"
             value={value} onChange={e => onChange(e.target.value)}
             onKeyDown={e => { if (e.key === "Enter") onApply(); }}
             spellCheck={false} />
      <button className="btn ghost sm" onClick={onApply} data-tip="Base URL 적용 후 재연결">적용</button>
      <button className="btn ghost sm" onClick={onReconnect} data-tip="현재 URL로 재연결">↻</button>
    </div>
  );
}

function IdleState({ onStart, configSpec }) {
  return (
    <>
      <div style={{
        padding: "10px 14px",
        background: "linear-gradient(90deg, rgba(240,179,90,0.10), rgba(240,179,90,0.02))",
        border: "1px solid rgba(240,179,90,0.32)",
        borderRadius: 6,
        marginBottom: 14,
        display: "flex",
        alignItems: "center",
        gap: 12,
        fontSize: 12,
        color: "var(--ink-1)",
      }}>
        <span style={{ fontSize: 16 }}>💡</span>
        <span>
          <strong style={{ color: "var(--amber)" }}>대시보드는 진화 시작 후 활성화됩니다.</strong>
          {" "}아래 <span className="mono" style={{ color: "var(--ink-0)" }}>▸ 진화 시작 설정 열기</span>를 누르면
          페이즈 타임라인(생성→백테→채점→부검), 엔진 메트릭, 자본곡선, 점수 분해, 부검 스트리밍이 실시간으로 보입니다.
        </span>
        <button className="btn primary" style={{ marginLeft: "auto" }} onClick={onStart}>
          ▸ 시작
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 }}>
      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot" style={{ background: "var(--teal)" }}></span>Welcome</div>
        </div>
        <div className="panel-bd" style={{ padding: "28px 24px" }}>
          <h2 style={{ fontSize: 22, marginBottom: 10, letterSpacing: "-0.01em" }}>
            루프를 시작할 준비가 되었습니다.
          </h2>
          <p style={{ color: "var(--ink-1)", lineHeight: 1.6, marginBottom: 22, fontSize: 13 }}>
            AI가 한국 주식 매수/매도 전략 코드를 자동 생성·백테스트·채점·반복합니다.
            각 세대의 부검(autopsy)이 다음 세대 생성기에 피드백되어 조건식이 점진적으로 진화합니다.
            <br /><br />
            <span style={{ color: "var(--ink-2)" }}>
              목표 점수와 MDD 상한을 동시에 만족하면 하드 게이트를 통과한 우승 전략으로 등록되고,
              <br />
              사용자의 명시적 승인 후에만 운영 strategy.db로 export 됩니다.
            </span>
          </p>
          <button className="btn primary lg" onClick={onStart}>
            ▸ 진화 시작 설정 열기
          </button>
        </div>
      </div>

      <div className="panel">
        <div className="panel-hd">
          <div className="panel-hd-title"><span className="dot"></span>루프 개요</div>
        </div>
        <div className="panel-bd" style={{ padding: 0 }}>
          <ol style={{ margin: 0, padding: 0, listStyle: "none" }}>
            {[
              { n: 1, k: "생성", d: "LLM이 직전 부검을 컨텍스트로 매수/매도 전략 코드를 생성 (실시간 스트리밍 표시)" },
              { n: 2, k: "백테스트", d: "지정된 시간단위·스코프·윈도우로 자본곡선·낙폭·매매를 시뮬레이션" },
              { n: 3, k: "채점", d: "graded_score = 손익·MDD·거래수·일관성의 가중합 (메트릭별 분해 표시)" },
              { n: 4, k: "게이트", d: "score ≥ target & MDD ≤ cap & trades ≥ min → 통과" },
              { n: 5, k: "부검", d: "탈락 원인을 자연어로 요약 → 다음 세대 컨텍스트에 주입" },
              { n: 6, k: "승인", d: "통과 전략을 운영 DB로 export (사용자 명시적 확인 필요)" },
            ].map((s, i, arr) => (
              <li key={s.n} style={{
                padding: "12px 16px",
                borderBottom: i < arr.length - 1 ? "1px solid var(--line-1)" : "none",
                display: "flex", gap: 12, alignItems: "flex-start",
              }}>
                <span className="mono" style={{
                  width: 22, height: 22, borderRadius: "50%",
                  background: "var(--bg-0)", border: "1px solid var(--line-2)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: 11, color: "var(--ink-1)", flexShrink: 0,
                }}>{s.n}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, color: "var(--ink-0)", marginBottom: 2 }}>{s.k}</div>
                  <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>{s.d}</div>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
      </div>
    </>
  );
}

Object.assign(window, { App });

// Mount
const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
