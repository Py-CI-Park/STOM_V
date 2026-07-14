/* v4-loop-cycle.jsx — V4 "반복 세대 사이클" 순환 다이어그램 (G004)
 *
 *   조건식 AI 루프의 8단계를 원형으로 배치하고, 현재 phase에 해당하는 노드를
 *   하이라이트한다: 시드 → 프롬프트 조립 → AI 생성 → 게이트 → 공식 백테 →
 *   채점 → 부검 → 환류 → (다시 시드로 순환, 마지막 화살표가 원을 닫는다).
 *
 *   단계 인덱스는 backend controller/loop.py `_PHASE_STEP` 주석과 동일한 5단계
 *   공간(0=생성 1=백테 2=채점 3=부검 4=반복)을 쓴다. 프론트에는 이미 같은 5단계를
 *   정규화하는 phase-detail.jsx `normalizeFlowStepIndex(rawStep, phase)`가 있으므로
 *   전역에 있으면 그대로 재사용하고(중복 구현 금지), 없을 때만(로드 순서 등) 아래
 *   로컬 폴백을 쓴다 — 다른 컴포넌트들이 window.X를 쓰는 방어적 패턴과 동일
 *   (`typeof window.X === "function"` 가드, 예: engine.jsx/evolution-analysis.jsx).
 */
const LOOP_NODES = [
  { key: "seed", label: "시드", tip: "탐색 시작점 — 시드 격자에서 다음 세대 조건식 후보의 출발 파라미터를 고른다.", step: 0, ai: false },
  { key: "prompt", label: "프롬프트 조립", tip: "시드와 이전 세대 부검 피드백을 조합해 LLM 프롬프트를 구성한다.", step: 0, ai: false },
  { key: "generate", label: "AI 생성", tip: "LLM이 매수/매도 조건식 코드를 생성한다.", step: 0, ai: true },
  { key: "gate", label: "게이트", tip: "생성된 코드가 구문·금지 변수 등 필터 게이트를 통과하는지 검사한다.", step: 0, ai: false },
  { key: "backtest", label: "공식 백테", tip: "게이트를 통과한 코드를 공식 백테스트 엔진으로 과거 데이터에 실행한다.", step: 1, ai: false },
  { key: "score", label: "채점", tip: "백테스트 결과에서 MDD·수익·빈도 등으로 graded fitness 점수를 산출한다.", step: 2, ai: false },
  { key: "autopsy", label: "부검", tip: "손실 집중 세그먼트 등 실패 원인을 부검 리포트로 정리한다.", step: 3, ai: false },
  { key: "feedback", label: "환류", tip: "부검 인사이트를 다음 세대 프롬프트에 되먹임해 루프를 반복한다.", step: 4, ai: true },
];

const LOOP_STEP_NAMES = ["생성", "백테", "채점", "부검", "반복"];

// 로컬 폴백 전용 — controller/loop.py `_PHASE_STEP` 주석과 동일한 phase→5단계 맵.
//   window.normalizeFlowStepIndex(phase-detail.jsx)가 있으면 그쪽이 우선이라 이 맵은
//   그 전역이 아직 없을 때만(로드 순서 안전망) 쓰인다.
const _LOOP_CYCLE_PHASE_STEP = {
  generate_start: 0, generate_done: 0, warm_prepare_start: 0, warm_prepare_done: 0, loop_start: 0,
  ga_init: 0,
  backtest_start: 1, backtest_end: 1, ga_evaluate_start: 1,
  score_start: 2, score_done: 2,
  autopsy_start: 3, autopsy_done: 3,
  generation_done: 4, ga_generation_done: 4,
  complete: -1, stopping: -1,
};

function _loopCycleFallbackStep(rawStep, phase) {
  let value = Number(rawStep);
  if (!Number.isInteger(value)) {
    value = Object.prototype.hasOwnProperty.call(_LOOP_CYCLE_PHASE_STEP, phase)
      ? _LOOP_CYCLE_PHASE_STEP[phase] : -1;
  }
  if (!Number.isInteger(value) || value < 0) return -1;
  return Math.min(LOOP_STEP_NAMES.length - 1, value);
}

function _loopCycleCurrentStep(state) {
  const s = state || {};
  const latest = s.latest || {};
  const rawStep = latest.current_step != null ? latest.current_step : s.live_phase_step;
  const phase = latest.phase || s.phase || "";
  if (typeof window.normalizeFlowStepIndex === "function") {
    return window.normalizeFlowStepIndex(rawStep, phase);
  }
  return _loopCycleFallbackStep(rawStep, phase);
}

// 원형 좌표 — viewBox 0 0 100 100 기준 퍼센트 좌표. i=0이 12시 방향에서 시작해
// 시계방향으로 8등분한다(시드가 맨 위).
function _loopCycleNodePos(i, total) {
  const angle = (-90 + (i * 360) / total) * (Math.PI / 180);
  const radius = 38;
  return { x: 50 + radius * Math.cos(angle), y: 50 + radius * Math.sin(angle) };
}

function _loopCycleEdge(i, total, nodeRadius) {
  const a = _loopCycleNodePos(i, total);
  const b = _loopCycleNodePos((i + 1) % total, total);
  const dx = b.x - a.x, dy = b.y - a.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const ux = dx / dist, uy = dy / dist;
  return {
    x1: a.x + ux * nodeRadius, y1: a.y + uy * nodeRadius,
    x2: b.x - ux * nodeRadius, y2: b.y - uy * nodeRadius,
  };
}

function V4LoopCycle({ state }) {
  const s = state || {};
  const running = s.status === "running" || s.status === "stopping";
  const isComplete = s.status === "complete";
  const currentStep = running ? _loopCycleCurrentStep(s) : -1;
  const currentStepName = currentStep >= 0 ? LOOP_STEP_NAMES[currentStep] : null;
  const total = LOOP_NODES.length;

  return (
    <section className="v4-loop-cycle-panel panel" aria-labelledby="v4-loop-cycle-heading">
      <div className="panel-hd">
        <div className="panel-hd-title" id="v4-loop-cycle-heading">
          <span className="dot"></span>반복 세대 사이클
        </div>
        {isComplete && (
          <span className="v4-chip ok" data-tip="이번 run의 세대 루프가 완료되었습니다">완료 · run 종료</span>
        )}
        {!isComplete && currentStepName && (
          <span className="v4-chip win" data-tip="현재 활성 단계">진행 중 · {currentStepName}</span>
        )}
      </div>
      <div
        className={"v4-loop-cycle" + (isComplete ? " v4-loop-cycle--complete" : "")}
        role="img"
        aria-label={
          "조건식 AI 루프 반복 세대 사이클 다이어그램 · 시드 → 프롬프트 조립 → AI 생성 → 게이트 → 공식 백테 → 채점 → 부검 → 환류 순환. 현재 단계 "
          + (currentStepName || "대기")
        }
      >
        <svg className="v4-loop-cycle-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
          <defs>
            <marker id="v4-loop-arrowhead" viewBox="0 0 10 10" refX="8" refY="5"
                    markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0,0 L10,5 L0,10 Z" className="v4-loop-arrowhead-fill" />
            </marker>
          </defs>
          {LOOP_NODES.map((_, i) => {
            const isWrap = i === total - 1;
            const lit = currentStep >= 0 && (isWrap
              ? currentStep === LOOP_STEP_NAMES.length - 1
              : LOOP_NODES[(i + 1) % total].step <= currentStep);
            const { x1, y1, x2, y2 } = _loopCycleEdge(i, total, 9);
            return (
              <line key={"edge-" + LOOP_NODES[i].key}
                    x1={x1} y1={y1} x2={x2} y2={y2}
                    className={"v4-loop-edge" + (lit ? " v4-loop-edge--lit" : "") + (isWrap ? " v4-loop-edge--wrap" : "")}
                    markerEnd="url(#v4-loop-arrowhead)" />
            );
          })}
        </svg>
        {LOOP_NODES.map((node, i) => {
          const pos = _loopCycleNodePos(i, total);
          const active = running && !isComplete && node.step === currentStep;
          return (
            <div key={node.key}
                 className={"v4-loop-node" + (active ? " v4-loop-node--active" : "") + (isComplete ? " v4-loop-node--dim" : "")}
                 style={{ left: pos.x + "%", top: pos.y + "%" }}
                 data-tip={node.tip}
                 aria-label={node.label + " — " + node.tip + (active ? " (현재 단계)" : "")}
                 tabIndex={0}>
              <span className={"v4-loop-badge " + (node.ai ? "v4-loop-badge--ai" : "v4-loop-badge--code")}
                    title={node.ai ? "AI 개입 지점" : "결정론적 코드"}>
                {node.ai ? "AI" : "\u2699"}
              </span>
              <span className="v4-loop-node-label">{node.label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

Object.assign(window, { V4LoopCycle });
// dual-safe ESM export. KEEP on ONE physical line.
export { V4LoopCycle };
