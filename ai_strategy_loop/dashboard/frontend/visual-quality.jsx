/* Visual regression and performance profiling surface for dashboard remodel work. */
const VISUAL_BASELINE_TARGETS = [
  { route: "evolution", label: "조건식 AI", widths: [1440, 1180, 980], evidence: "run monitor + process + HoF + verdict cards" },
  { route: "records", label: "히스토리", widths: [1440, 1180, 980], evidence: "search/filter/detail split" },
  { route: "lab", label: "리서치 Wiki", widths: [1440, 1180, 980], evidence: "wiki/context/evidence workspace" },
  { route: "pro", label: "분석 워크벤치", widths: [1440, 1180, 980], evidence: "workbench and HoF responsibility" },
  { route: "verdict", label: "결정 감사", widths: [1440, 1180, 980], evidence: "append-only decision form/history" },
  { route: "process", label: "프로세스", widths: [1440, 1180, 980], evidence: "native live strip/timing/grid/log/default gates" },
  { route: "hof", label: "명예의 전당", widths: [1440, 1180, 980], evidence: "inventory fields and screenshots" },
];

const PERF_PROFILE_BUDGETS = [
  { surface: "records", metric: "largest list render", threshold: "500 rows before windowing review", action: "row cap/metadata filter first" },
  { surface: "generations", metric: "table rows", threshold: "300 rows before windowing review", action: "preserve onViewCode/onSelectDetail" },
  { surface: "hof", metric: "combined rows", threshold: "150 rows before windowing review", action: "preserve field inventory" },
  { surface: "verdict", metric: "history rows", threshold: "300 decisions before windowing review", action: "append-only order preserved" },
  { surface: "process", metric: "log entries", threshold: "50 visible lines", action: "summarize, do not mutate state contract" },
];

function VisualQualityPanel({ compact = false }) {
  return (
    <div className="panel visual-quality-panel">
      <div className="panel-hd">
        <div className="panel-hd-title"><span className="dot" style={{ background: "var(--blue)" }}></span>UI 품질 게이트</div>
        <span className="mono" style={{ color: "var(--ink-2)", fontSize: 11 }}>visual · perf · no-dependency</span>
      </div>
      <div className="panel-bd">
        <div className="visual-quality-note">
          대공사 UI 변경은 스크린샷 기준과 성능 임계값을 먼저 고정한 뒤 진행합니다. 새 의존성 없이
          현재 bundle/Track Z/pytest 계약 안에서 측정하고, 임계값을 넘을 때만 no-dependency windowing을 설계합니다.
        </div>
        <div className="visual-quality-grid">
          <div>
            <h4>Visual baseline</h4>
            {VISUAL_BASELINE_TARGETS.map(target => (
              <div key={target.route} className="visual-quality-row">
                <b>{target.label}</b>
                <span className="mono">{target.widths.join("/")} px</span>
                {!compact && <small>{target.evidence}</small>}
              </div>
            ))}
          </div>
          <div>
            <h4>Performance profile</h4>
            {PERF_PROFILE_BUDGETS.map(item => (
              <div key={item.surface + item.metric} className="visual-quality-row">
                <b>{item.surface}</b>
                <span className="mono">{item.threshold}</span>
                {!compact && <small>{item.action}</small>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { PERF_PROFILE_BUDGETS, VISUAL_BASELINE_TARGETS, VisualQualityPanel });

// Track Z — dual-safe ESM export. KEEP on ONE physical line.
export { PERF_PROFILE_BUDGETS, VISUAL_BASELINE_TARGETS, VisualQualityPanel };
