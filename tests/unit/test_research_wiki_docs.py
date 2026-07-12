"""Condition research wiki documentation contract tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402

WIKI_DIR = Path(PROJECT_ROOT) / "docs" / "research" / "condition_research" / "wiki"
REQUIRED_DOCS = (
    "research_method_registry.md",
    "metrics_glossary.md",
    "tick_oos_failure_lesson.md",
)
REQUIRED_TERMS = (
    "hillclimb/refine",
    "GA",
    "band compiler",
    "seed_902",
    "Optuna",
    "edge ratio",
    "feature_importance",
    "adaptive timing",
    "segment feedback",
    "prompt logging",
    "PBO",
    "DSR",
    "payoff_ratio",
    "OOS",
    "overfit",
    "MDD",
    "MFE/MAE",
    "slippage",
    "win-day ratio",
    "recent-weighted score",
    "hard gate",
    "graded",
    "PBO/DSR advisory blocker",
    "REJECT_CANDIDATE",
    "screenshots are reference, not live proof",
)


def _wiki_text() -> str:
    return "\n\n".join((WIKI_DIR / name).read_text(encoding="utf-8") for name in REQUIRED_DOCS)


def test_research_wiki_required_docs_exist() -> None:
    """Given the research wiki, When checking docs, Then the required starter docs exist."""
    missing = [name for name in REQUIRED_DOCS if not (WIKI_DIR / name).is_file()]
    assert missing == []


def test_research_wiki_covers_methods_metrics_and_rejected_candidate() -> None:
    """Given wiki text, When scanning terms, Then methods, metrics, and current caution are explicit."""
    text = _wiki_text()

    missing = [term for term in REQUIRED_TERMS if term not in text]

    assert missing == []
    assert "PROMOTE_CANDIDATE" not in text


def test_research_wiki_is_discoverable_from_docs_api(monkeypatch, tmp_path: Path) -> None:
    """Given Task 5 docs API, When listing docs, Then wiki files are listed with safe ids."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    client = authorized_dashboard_client(create_app())

    response = client.get("/research_docs")

    assert response.status_code == 200
    docs = response.json()["docs"]
    ids = {doc["id"] for doc in docs}
    assert "docs/research/condition_research/wiki/research_method_registry.md" in ids
    assert {
        doc["category"]
        for doc in docs
        if doc["id"].startswith("docs/research/condition_research/wiki/")
    } == {"wiki"}
