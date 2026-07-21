"""Read-only research document dashboard API tests."""

from __future__ import annotations

import os
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402
import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    """Create an isolated dashboard client without touching live loop state."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


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
def test_research_docs_without_limit_returns_full_set(monkeypatch, tmp_path: Path) -> None:
    from ai_strategy_loop.dashboard import research_api

    rows = {
        f"docs/research/condition_research/doc_{index}.md": (
            tmp_path / f"doc_{index}.md",
            {
                "id": f"docs/research/condition_research/doc_{index}.md",
                "title": f"Doc {index}",
                "category": "condition_research",
                "updated_at": "",
                "size": index,
            },
        )
        for index in range(3)
    }
    monkeypatch.setattr(research_api, "_doc_index", lambda: rows)

    full = research_api.research_docs()
    paged = research_api.research_docs(limit=2)

    assert full["count"] == full["total"] == 3
    assert full["next_offset"] is None
    assert paged["count"] == 2
    assert paged["total"] == 3
    assert paged["next_offset"] == 2


def test_research_doc_rejects_symlink_outside_allowlisted_root(monkeypatch, tmp_path: Path) -> None:
    from ai_strategy_loop.dashboard import research_api

    repo = tmp_path / "repo"
    document = repo / "docs" / "research" / "condition_research" / "linked.md"
    document.parent.mkdir(parents=True)
    secret = tmp_path / "secret.md"
    secret.write_text("# Secret\n", encoding="utf-8")
    try:
        document.symlink_to(secret)
    except OSError as exc:
        pytest.skip(f"symlinks unavailable: {exc}")

    doc_id = "docs/research/condition_research/linked.md"
    summary = {"id": doc_id, "title": "Linked", "category": "condition_research", "updated_at": "", "size": 0}
    monkeypatch.setattr(research_api, "REPO_ROOT", repo)
    monkeypatch.setattr(research_api, "_doc_index", lambda: {doc_id: (document, summary)})

    response = research_api.research_doc(doc_id)

    assert response == {"available": False, "error": "doc_not_allowed", "id": doc_id}


def test_tracked_research_docs_sidecar_matches_allowlisted_sources() -> None:
    from ai_strategy_loop.dashboard import research_api
    from scripts import build_research_docs_index

    sidecar = research_api._DOC_INDEX_SIDECAR
    payload = build_research_docs_index.build_index(sidecar)

    assert build_research_docs_index.index_matches(sidecar, payload)


def test_research_docs_sidecar_parity_ignores_checkout_mtime(tmp_path: Path) -> None:
    from scripts import build_research_docs_index

    payload = {
        "schema_version": "stom-research-doc-index-v1",
        "source_fingerprint": "content-hash",
        "count": 1,
        "docs": [{"id": "docs/a.md", "title": "A", "size": 1, "updated_at": "new"}],
    }
    tracked = {
        **payload,
        "docs": [{**payload["docs"][0], "updated_at": "old"}],
    }
    sidecar = tmp_path / "research_docs_index.json"
    sidecar.write_text(json.dumps(tracked), encoding="utf-8")

    assert build_research_docs_index.index_matches(sidecar, payload)
