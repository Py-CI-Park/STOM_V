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
    """Given research-lab.jsx, When scanning source, Then tabs and endpoint contracts exist."""
    src = _read_front("research-lab.jsx")

    assert "function ResearchLabPanel(" in src
    assert "/variable_correlation" in src
    assert "pearson" in src
    assert "spearman" in src
    assert "Edge" in src
    assert "Feature Importance" in src
    assert "Correlation" in src
    assert "Variable Combinations" in src
    assert "insufficient" in src
    assert "feature_matrix" in src
    assert "sample count" in src
    assert "range_summaries" in src
    assert "segment_summaries" in src
    assert "interaction_candidates" in src
    assert "histogram" in src
    assert "win/loss" in src
    assert "recency_research" in src
    assert "research_score_not_promotion" in src


def test_research_lab_exposes_window_symbol() -> None:
    """Given browser-loaded modules, When app runs, Then ResearchLabPanel is globally exposed."""
    src = _read_front("research-lab.jsx")
    tail = src[src.rfind("Object.assign(window"):]

    assert "ResearchLabPanel" in tail


def test_research_lab_is_loaded_before_app() -> None:
    """Given index.html, When scripts load, Then research-lab is available before app.jsx."""
    html = _read_front("index.html")

    assert "research-lab.jsx" in html
    assert html.find("research-lab.jsx") < html.find("app.jsx")


def test_app_jsx_wires_research_lab() -> None:
    """Given app.jsx, When dashboard renders analysis, Then ResearchLabPanel receives run context."""
    src = _read_front("app.jsx")
    idx = src.find("<ResearchLabPanel")
    snippet = src[idx: idx + 220]

    assert idx >= 0
    assert "baseUrl={baseUrl}" in snippet
    assert "wsStatus={wsStatus}" in snippet
    assert "runId={state.run_id || \"\"}" in snippet


def test_existing_edge_and_feature_panels_still_exported() -> None:
    """Given analysis.jsx, When Research Lab wraps existing panels, Then old exports stay available."""
    src = _read_front("analysis.jsx")
    tail = src[src.rfind("Object.assign(window"):]

    assert "EdgeRatioPanel" in tail
    assert "FeatureImportancePanel" in tail
