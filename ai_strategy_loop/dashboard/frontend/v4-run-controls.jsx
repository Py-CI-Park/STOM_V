/* v4-run-controls.jsx — V4 상단 run 제어 스트립 (순수 표현)
 *
 *   설정·시작/정지 버튼 + 진행도 + RUN 셀렉터. 데이터/액션은 전부 props 로 받는다
 *   (fetch·send 는 셸 소유 — app.jsx:76-119/201-233 패턴을 셸이 재사용).
 *   V2 styles.css 의 .btn/.progress-track 을 재사용하고 신규 클래스만 .v4- 프리픽스.
 */

function V4RunControls({
  running, state, isDemo,
  runList, selectedRun, onSelectRun, onRefreshRun,
  onOpenSettings, onStop,
}) {
  // idle 백엔드는 current_gen=-1 을 줄 수 있다 — 음수는 "시작 전"이므로 — 로 표기.
  const curRaw = Number(state.current_gen);
  const cur = Number.isFinite(curRaw) && curRaw >= 0 ? curRaw : null;
  const max = Number(state.max_generations) || 0;
  const pct = max > 0 && cur != null ? Math.min(100, (cur / max) * 100) : 0;
  return (
    <div className="v4-runbar">
      <div className="v4-runbar-prog" title={`진행도 ${cur ?? "—"}/${max} 세대`}>
        <span className="mono v4-runbar-gen">
          <b style={{ color: running ? "var(--amber)" : "var(--ink-0)" }}>{cur ?? "—"}</b>
          <span style={{ color: "var(--ink-3)" }}> / {max || "—"}</span>
        </span>
        <span className="progress-track v4-runbar-track">
          <span className={"progress-fill" + (running ? " running" : "")} style={{ width: pct + "%" }}></span>
        </span>
      </div>
      <div className={"v4-runsel" + (selectedRun ? " is-archive" : "")}
           title="볼 연구 run 선택 — LIVE(현재 진행) 또는 과거 실 run 아카이브">
        <span className="mono v4-runsel-lbl">연구 RUN</span>
        <select className="mono v4-runsel-select" value={selectedRun} disabled={isDemo}
                onChange={e => onSelectRun(e.target.value)}>
          <option value="">● LIVE (현재 진행)</option>
          {(runList || []).map(r => (
            <option key={r.run_id} value={r.run_id}>
              {(r.gate_passed_count > 0 ? "✓ " : "")}{r.run_id}{r.label ? " · " + r.label : ""}
            </option>
          ))}
        </select>
        <span className={"v4-chip " + (selectedRun ? "warn" : "ok")}>
          {selectedRun ? "아카이브" : "LIVE"}
        </span>
        {selectedRun && (
          <button className="btn ghost sm" onClick={onRefreshRun} disabled={isDemo}
                  data-tip="선택 run 새로고침">↻</button>
        )}
      </div>
      <button className="btn danger" onClick={onStop} disabled={!running}>◼ 정지</button>
      <button className="btn primary" onClick={onOpenSettings} disabled={running}>▸ 설정·시작</button>
    </div>
  );
}

Object.assign(window, { V4RunControls });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4RunControls };
