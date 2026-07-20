/* v4-run-controls.jsx — V4 상단 run 제어 스트립 (순수 표현)
 *
 *   RUN 셀렉터(데이터 스코프) + 진행도 + 설정·시작/정지. 데이터/액션은 전부 props.
 *   컨텍스트 정합: 진행도·설정·시작은 **Live 탭에서만** 노출/강조한다(다른 탭에선
 *   run 제어가 화면 내용과 무관해 혼선). RUN 셀렉터는 모든 탭 공통(어떤 run 데이터를
 *   볼지 고르는 스코프). 연구가 도는 중 비-Live 탭에서는 "진행중 → Live" 링크와
 *   안전 정지 버튼만 남겨 사용자가 어디서든 상태를 인지·중단할 수 있게 한다.
 *   V2 styles.css 의 .btn/.progress-track 을 재사용하고 신규 클래스만 .v4- 프리픽스.
 */

function V4RunControls({
  running, state, isDemo, isLive,
  runList, selectedRun, onSelectRun, onRefreshRun,
  onOpenSettings, onStop, onGoLive,
}) {
  // idle 백엔드는 current_gen=-1 을 줄 수 있다 — 음수는 "시작 전"이므로 — 로 표기.
  const curRaw = Number(state.current_gen);
  const cur = Number.isFinite(curRaw) && curRaw >= 0 ? curRaw : null;
  const max = Number(state.max_generations) || 0;
  const pct = max > 0 && cur != null ? Math.min(100, (cur / max) * 100) : 0;
  return (
    <div className="v4-runbar">
      {/* 진행도 — Live 탭 전용(다른 탭에선 무맥락) */}
      {isLive && (
        <div className="v4-runbar-prog" title={`진행도 ${cur ?? "—"}/${max} 세대`}>
          <span className="mono v4-runbar-gen">
            <b style={{ color: running ? "var(--amber)" : "var(--ink-0)" }}>{cur ?? "—"}</b>
            <span style={{ color: "var(--ink-3)" }}> / {max || "—"}</span>
          </span>
          <span className="progress-track v4-runbar-track">
            <span className={"progress-fill" + (running ? " running" : "")} style={{ width: pct + "%" }}></span>
          </span>
        </div>
      )}
      {/* 비-Live 탭: 연구가 도는 중이면 진행 상태를 알리는 Live 바로가기(맥락 이탈 방지) */}
      {!isLive && running && (
        <button className="v4-runbar-livelink" onClick={onGoLive}
                title="연구 진행 중 — Live 탭에서 상세 보기">
          <span className="v4-runbar-livedot"></span>
          <span className="mono">연구 진행 {cur ?? "—"}/{max || "—"} · Live ↗</span>
        </button>
      )}
      {/* v5.5 F6 — RUN 셀렉터는 Live 탭 전용(다른 탭에선 화면 내용과 무관해 혼선). */}
      {isLive && (
      <div className={"v4-runsel" + (selectedRun ? " is-archive" : "")}
           title="볼 연구 run 선택 — LIVE(현재 진행) 또는 과거 실 run 아카이브">
        <span className="mono v4-runsel-lbl">연구 RUN</span>
        <select className="mono v4-runsel-select" value={selectedRun} disabled={isDemo}
                onChange={e => onSelectRun(e.target.value)}>
          <option value="">● LIVE (현재 진행)</option>
          {(runList || []).map(r => {
            // v5.5 F6 — 가독 라벨: 날짜 · run_id · 세대수 · 게이트(제목 잘림은 폭 확장 CSS 로 해소).
            const d = typeof r.started_at === "number" && r.started_at > 1e9
              ? new Date(r.started_at * 1000).toISOString().slice(0, 10) : "";
            const gens = r.gen_count != null ? ` · ${r.gen_count}세대` : "";
            const gate = r.gate_passed_count > 0 ? ` · ✓${r.gate_passed_count}` : "";
            return (
              <option key={r.run_id} value={r.run_id}>
                {(d ? d + " · " : "")}{r.run_id}{gens}{gate}{r.label ? " · " + r.label : ""}
              </option>
            );
          })}
        </select>
        <span className={"v4-chip " + (selectedRun ? "warn" : "ok")}>
          {selectedRun ? "아카이브" : "LIVE"}
        </span>
        {selectedRun && (
          <button className="btn ghost sm" onClick={onRefreshRun} disabled={isDemo}
                  data-tip="선택 run 새로고침">↻</button>
        )}
      </div>
      )}
      {/* 정지 — Live 에선 상시(비활성 시 disabled), 다른 탭에선 도는 중일 때만(안전 중단) */}
      {(isLive || running) && (
        <button className="btn danger" onClick={onStop} disabled={!running}>◼ 정지</button>
      )}
      {/* 설정·시작 — Live 탭 전용(연구 시작은 Live 의 행위) */}
      {isLive && (
        <button className="btn primary" onClick={onOpenSettings} disabled={running}>▸ 설정·시작</button>
      )}
    </div>
  );
}

Object.assign(window, { V4RunControls });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4RunControls };
