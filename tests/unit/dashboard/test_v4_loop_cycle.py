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


def test_v4_research_places_loop_cycle_in_observability_rail() -> None:
    # Given: the V4 Research Live tab source.
    source = _read(FRONTEND / "v4-research.jsx")

    # When/Then: it imports the loop-cycle component and renders it inside the
    # observability rail (aside), alongside CurrentGenPanel.
    assert 'import { V4LoopCycle } from "./v4-loop-cycle.jsx";' in source
    aside_start = source.index('<aside className="v4-side-col">')
    aside_end = source.index("</aside>", aside_start)
    aside_body = source[aside_start:aside_end]
    assert "<CurrentGenPanel state={s} />" in aside_body
    assert "<V4LoopCycle state={s} />" in aside_body


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

    # When/Then: the bundle graph resolved the new module (source markers reachable) and
    # the manifest's content-hash version reflects the change (differs from HEAD's).
    assert "function V4LoopCycle(" in app_js
    assert "v4-loop-node--active" in app_js
    assert "v4-loop-badge--ai" in app_js
    # Korean labels are \uXXXX-escaped by the esbuild minifier, so assert on the
    # ascii-safe node keys instead (unique per node, stable across minification).
    for key in ["seed", "prompt", "generate", "gate", "backtest", "score", "autopsy", "feedback"]:
        assert f'"{key}"' in app_js, f"missing loop node key in bundle: {key}"

    app_v = manifest["bundles"]["app.js"]["v"]
    assert isinstance(app_v, str) and app_v
    # 아키텍트 리뷰 HIGH 반영: HEAD-diff 단언은 재빌드 manifest가 같은 커밋에 포함되는
    #   순간 자기모순(클린 체크아웃 영구 실패)이라 제거. 내구 가드는
    #   test_p14_build_harness의 content-hash 재해시가 담당하고, 여기서는
    #   서빙 HTML의 app.js ?v= pin이 manifest와 정합함(스테일 pin 회귀)을 가드한다.
    v4_html = (FRONTEND / "v4.html").read_text(encoding="utf-8")
    assert f"/ui/bundle/app.js?v={app_v}" in v4_html, "v4.html app.js pin이 manifest v와 불일치"
