"""Static frontend contract for the Research Lab panel."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _read_front(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def test_research_lab_component_contract() -> None:
    """Given research-lab modules, When scanning source, Then tabs and endpoint contracts exist.

    P5.6 분해: research-lab.jsx 는 배럴이 되고 본문은 rl-panel.jsx(오케스트레이터+탭)와
    rl-analysis.jsx(상관/조합 보조)로 이동했다. 계약 검증은 두 모듈을 이어 수행한다.
    """
    src = _read_front("rl-panel.jsx") + "\n" + _read_front("rl-analysis.jsx")

    assert "function ResearchLabPanel(" in src
    assert "/variable_correlation" in src
    assert "pearson" in src
    assert "spearman" in src
    assert "Edge" in src
    # Phase7 §7.7 — 탭 라벨은 한글화됨(영문 라벨 누수 제거). 분석 섹션 존재는 한글 라벨로 검증.
    assert "변수 중요도" in src
    assert "Correlation" in src
    # 분해 후 combos 탭 라벨은 한글 "변수 조합"(영문 "Variable Combinations" 누수 제거).
    assert "변수 조합" in src
    assert "데이터가 부족합니다" in src
    assert "feature_matrix" in src
    assert "sample count" in src
    assert "range_summaries" in src
    assert "segment_summaries" in src
    assert "interaction_candidates" in src
    assert "histogram" in src
    assert "win/loss" in src
    assert "recency_research" in src
    assert "research_score_not_promotion" in src
    assert "fullscreen" not in src
    assert "전체 화면" not in src


def test_research_lab_exposes_window_symbol() -> None:
    """Given browser-loaded modules, When app runs, Then ResearchLabPanel is globally exposed."""
    src = _read_front("research-lab.jsx")
    tail = src[src.rfind("Object.assign(window"):]

    assert "ResearchLabPanel" in tail


def test_research_lab_is_loaded_before_app() -> None:
    """Given app.js 번들, Then research-lab 이 산출 번들에 포함된다(Phase14.4 단일 번들).

    모델-무관: concat 텍스트 순서(research-lab < app) DROP — 모듈 스코프에선 무의미.
    research-lab 이 정의하는 심볼 존재로 검증한다(concat·bundle 양쪽 통과).
    """
    app = _read_front("bundle/app.js")

    assert "ResearchLabPanel" in app, "app.js 에 research-lab(ResearchLabPanel) 누락"


def test_lab_page_wires_research_lab_with_selected_run() -> None:
    """Given LabPage, When dashboard renders Lab, Then ResearchLabPanel receives selected run context."""
    src = _read_front("dashboard-pages.jsx")
    idx = src.find("<LabPanel")
    snippet = src[idx: idx + 220]

    assert idx >= 0
    assert "baseUrl={base}" in snippet
    assert 'wsStatus="na"' in snippet
    assert "runId={runId}" in snippet


def test_research_lab_shows_status_before_active_analysis() -> None:
    """The active analysis follows its status bar; glossary/examples live in the glossary tab."""
    src = _read_front("rl-panel.jsx")

    assert src.index('className="research-statusbar mono"') < src.index("{body}")
    assert 'className="lab-glossary"' not in src
    assert 'className="lab-example"' not in src


def test_edge_heatmap_uses_intrinsic_bounded_scroll_size() -> None:
    """Given the edge heatmap, Then small grids do not stretch to the full panel width."""
    src = _read_front("analysis.jsx")
    css = _read_front("styles.css")

    assert 'style={{ width: W, height: H, display: "block" }}' in src
    assert 'width: "100%", minWidth: W' not in src
    heatmap_scroll = css.split(".edge-heatmap-scroll {", 1)[1].split("}", 1)[0]
    assert "max-height: 360px" in heatmap_scroll
    assert "overflow: auto" in heatmap_scroll


def test_existing_edge_and_feature_panels_still_exported() -> None:
    """Given analysis.jsx, When Research Lab wraps existing panels, Then old exports stay available."""
    src = _read_front("analysis.jsx")
    tail = src[src.rfind("Object.assign(window"):]

    assert "EdgeRatioPanel" in tail
    assert "FeatureImportancePanel" in tail
