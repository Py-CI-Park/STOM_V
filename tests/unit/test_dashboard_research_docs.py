"""Read-only research document dashboard API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    """Create an isolated dashboard client without touching live loop state."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


def test_research_docs_lists_only_whitelisted_markdown(monkeypatch, tmp_path: Path) -> None:
    """Given repository docs, When listing research docs, Then only relative markdown ids appear."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/research_docs")

    assert response.status_code == 200
    body = response.json()
    ids = {doc["id"] for doc in body["docs"]}
    assert "docs/reference/STOM_Good_Results/backtest_analysis_report.md" in ids
    assert "docs/update_log/2026-06-03_tick_program_complete_handoff.md" in ids
    assert any(doc_id.startswith("docs/research/condition_research/") for doc_id in ids)
    assert all(doc_id.endswith(".md") for doc_id in ids)
    assert all(not Path(doc_id).is_absolute() for doc_id in ids)
    assert "AGENTS.md" not in ids
    assert body["count"] == len(ids)


def test_research_doc_reads_whitelisted_markdown(monkeypatch, tmp_path: Path) -> None:
    """Given a listed doc id, When reading it, Then markdown text and metadata are returned."""
    client = _client(monkeypatch, tmp_path)
    doc_id = "docs/reference/STOM_Good_Results/backtest_analysis_report.md"

    response = client.get("/research_doc", params={"id": doc_id})

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == doc_id
    assert body["available"] is True
    assert body["category"] == "good_results"
    assert body["markdown"].lstrip().startswith("#")
    assert body["size"] == len(body["markdown"])


def test_research_doc_rejects_traversal(monkeypatch, tmp_path: Path) -> None:
    """Given traversal input, When reading a doc, Then no markdown content is served."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/research_doc", params={"id": "../AGENTS.md"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["error"] == "doc_not_allowed"
    assert "markdown" not in body
