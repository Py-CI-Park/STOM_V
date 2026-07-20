from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"
BUNDLE = FRONTEND / "bundle"

LOOP_NODE_LABELS = ["시드", "프롬프트 조립", "AI 생성", "게이트", "공식 백테", "채점", "부검", "환류"]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_v4_loop_cycle_source_declares_all_eight_nodes_and_ai_badges() -> None:
    # Given: the new circular loop-cycle component source.
    source = _read(FRONTEND / "v4-loop-cycle.jsx")

    # When/Then: component name, all 8 Korean node labels, active-state class, and
    # AI-badge markers on exactly the AI intervention nodes (AI 생성 / 환류) are present.
    assert "function V4LoopCycle(" in source
    for label in LOOP_NODE_LABELS:
        assert f'"{label}"' in source, f"missing loop node label: {label}"
    assert "v4-loop-node--active" in source
    assert "v4-loop-badge--ai" in source
    assert "v4-loop-badge--code" in source
    assert '{ key: "generate", label: "AI 생성"' in source and "ai: true" in source
    assert '{ key: "feedback", label: "환류"' in source
    # AI badge appears on exactly 2 of the 8 node definitions (AI 생성, 환류).
    assert source.count("ai: true") == 2
    assert source.count("ai: false") == 6
    # Cyclic connection: node i -> node (i+1) % total, closing the loop back to node 0.
    assert "(i + 1) % total" in source
    # Completion state dims the whole diagram + shows a completion badge.
    assert "v4-loop-cycle--complete" in source
    assert "완료 · run 종료" in source
    # dual-safe ESM export, matching sibling v4-*.jsx components.
    assert "export { V4LoopCycle };" in source


def test_v4_loop_cycle_reuses_five_step_phase_mapping_convention() -> None:
    # Given: the loop-cycle component.
    source = _read(FRONTEND / "v4-loop-cycle.jsx")

    # When/Then: it prefers the existing phase-detail.jsx 5-step normalizer (no duplicate
    # mapping implementation authority) and only falls back locally when absent.
    assert 'typeof window.normalizeFlowStepIndex === "function"' in source
    assert "window.normalizeFlowStepIndex(rawStep, phase)" in source
    assert "_loopCycleFallbackStep" in source


def test_v4_research_places_pipeline_belt_in_status_board() -> None:
    # v5.3.2: 원형 사이클(V4LoopCycle)+PhaseTimeline 은 수평 파이프라인 벨트로 흡수(N3).
    # 불변: Live 상황판이 루프 파이프라인을 렌더하고, 현재세대(CurrentGenPanel)는 상황판 통합(N4).
    source = _read(FRONTEND / "v4-research.jsx")
    assert "function _V6PipelineBelt(" in source
    board_start = source.index("function _V6StatusBoard(")
    board_end = source.index("function V4ResearchLive(")
    board_body = source[board_start:board_end]
    assert "<_V6PipelineBelt" in board_body
    assert "<CurrentGenPanel state={s} />" in board_body
    # 벨트 8노드가 4스테이지 매핑을 가진다(클릭 pin).
    assert '{ key: "loop", label: "환류 ↩", ai: false, stage: 3 }' in source
    assert "STAGE_FROM_PHASE = [0, 1, 2, 2]" in source
def test_v4_research_status_helper_makes_complete_the_terminal_stage() -> None:
    source = _read(FRONTEND / "v4-research.jsx")

    assert "function _v4RunStatus(status, phase)" in source
    for status in ["idle", "running", "stopping", "complete", "error", "blocked"]:
        assert f"{status}: {{ stage:" in source
    assert 'complete: { stage: 3, engineLabel: "완료"' in source
    assert "const liveStage = runStatus.stage;" in source
    assert 'status === "done"' not in source
    assert "runStatus.engineLabel" in source


def test_analysis_fallback_only_derives_missing_or_pending_authority() -> None:
    analysis = _read(FRONTEND / "panels-analysis.jsx")
    config = _read(FRONTEND / "panels-config.jsx")

    assert 'return !data || data.status === "missing" || data.status === "pending";' in analysis
    assert "_derivedFallbackAllowed(autopsy)" in analysis
    assert "_derivedFallbackAllowed(lineage)" in analysis
    assert 'autopsy.status !== "ok"' not in analysis
    assert 'lineage.status !== "ok"' not in analysis
    assert "정본 상태:" in analysis
    assert "마지막 정상 정보:" in analysis

    assert 'return !meta || meta.status === "missing" || meta.status === "pending";' in config
    assert "_metaDerivedFallbackAllowed(meta)" in config
    assert 'meta.status !== "ok"' not in config
    assert "정본 상태:" in config
    assert "마지막 정상 정보:" in config



def test_v4_css_declares_loop_cycle_pulse_animation_with_reduced_motion_guard() -> None:
    # Given: the shared V4 stylesheet.
    css = _read(FRONTEND / "v4.css")

    # When/Then: pulse keyframes exist for the active node and respect reduced motion.
    assert "@keyframes v4-loop-pulse" in css
    assert ".v4-loop-node--active" in css
    assert "animation: v4-loop-pulse" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".v4-loop-node--active { animation: none; }" in css
    assert ".v4-loop-cycle--complete" in css


def test_v4_loop_cycle_bundle_is_rebuilt_and_carries_markers() -> None:
    # Given: the committed served bundle artifact.
    app_js = _read(BUNDLE / "app.js")
    manifest = json.loads(_read(BUNDLE / "manifest.json"))

    # When/Then(v5.3.2): 원형 사이클은 수평 파이프라인 벨트로 대체 — 번들은 벨트 마커를 담고,
    # V4LoopCycle 은 미사용으로 tree-shake 되는 것이 올바른 상태다.
    assert "_V6PipelineBelt" in app_js or "v6-belt-node" in app_js
    assert "v6-belt-badge" in app_js
    # ascii-safe 벨트 노드 키(한글 라벨은 \uXXXX escape 되므로 키로 단언).
    for key in ["seed", "prompt", "gen", "gate", "bt", "score", "autopsy", "loop"]:
        assert f'"{key}"' in app_js, f"missing belt node key in bundle: {key}"

    app_v = manifest["bundles"]["app.js"]["v"]
    assert isinstance(app_v, str) and app_v
    # 아키텍트 리뷰 HIGH 반영: HEAD-diff 단언은 재빌드 manifest가 같은 커밋에 포함되는
    #   순간 자기모순(클린 체크아웃 영구 실패)이라 제거. 내구 가드는
    #   test_p14_build_harness의 content-hash 재해시가 담당하고, 여기서는
    #   서빙 HTML의 app.js ?v= pin이 manifest와 정합함(스테일 pin 회귀)을 가드한다.
    v4_html = (FRONTEND / "v4.html").read_text(encoding="utf-8")
    assert f"/ui/bundle/app.js?v={app_v}" in v4_html, "v4.html app.js pin이 manifest v와 불일치"
