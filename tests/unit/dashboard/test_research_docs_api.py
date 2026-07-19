"""Structured read-only research Wiki docs API contracts."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import research_api  # noqa: E402


def _install_tmp_docs(monkeypatch, tmp_path: Path) -> tuple[Path, str, str, str]:
    repo = tmp_path / "repo"
    wiki_dir = repo / "docs" / "research" / "condition_research" / "wiki"
    wiki_dir.mkdir(parents=True)
    a = wiki_dir / "alpha.md"
    b = wiki_dir / "beta.md"
    c = wiki_dir / "gamma.md"
    raw_a = (
        "---\n"
        "title: Raw frontmatter stays raw\n"
        "---\n"
        "# Alpha\n"
        "source:C:/private/evidence/alpha.json\n"
        "public:https://example.test/C:/private/evidence/keep.json\n"
    )
    a.write_text(raw_a, encoding="utf-8")
    b.write_text("# Beta\n", encoding="utf-8")
    c.write_text("# Gamma\n", encoding="utf-8")
    a_id = "docs/research/condition_research/wiki/alpha.md"
    b_id = "docs/research/condition_research/wiki/beta.md"
    c_id = "docs/research/condition_research/wiki/gamma.md"
    (wiki_dir / "_wiki_index.json").write_text(
        json.dumps(
            {
                "docs": {
                    a_id: {
                        "tags": ["Audit", "G006"],
                        "related_ids": [b_id, "../AGENTS.md", c_id],
                        "chronology": [
                            {"date": "2026-07-19", "label": "sealed", "id": b_id},
                            {"date": "2026-07-20", "label": "bad id", "id": "../AGENTS.md"},
                        ],
                        "trust": {"level": "reviewed"},
                        "standard_template": {"status": "standard"},
                        "source_sha256": hashlib.sha256(a.read_bytes()).hexdigest(),
                    },
                    b_id: {"tags": ["Audit"], "trust": "candidate", "standard_template_status": "partial"},
                    c_id: {"tags": ["Audit"], "trust": "low"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (wiki_dir / "beta.wiki.json").write_text(
        json.dumps({"id": "../AGENTS.md", "tags": ["must-not-publish"], "trust": "forged"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(research_api, "REPO_ROOT", repo)
    monkeypatch.setattr(
        research_api,
        "_DOC_ROOTS",
        (research_api.DocRoot(category="condition_research", rel_path="docs/research/condition_research"),),
    )
    monkeypatch.setattr(research_api, "_SELECTED_UPDATE_LOGS", ())
    return repo, a_id, b_id, c_id


def test_research_doc_metadata_uses_sidecar_without_mutating_markdown(monkeypatch, tmp_path: Path) -> None:
    repo, a_id, b_id, c_id = _install_tmp_docs(monkeypatch, tmp_path)
    source_path = repo / a_id
    raw_bytes = source_path.read_bytes()

    response = research_api.research_doc(a_id)

    assert response["available"] is True
    assert response["source_sha256"] == hashlib.sha256(raw_bytes).hexdigest()
    assert response["source_bytes"] == len(raw_bytes)
    normalized_markdown = raw_bytes.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    assert response["size"] == len(normalized_markdown)
    assert response["markdown"] == normalized_markdown.replace(
        "source:C:/private/evidence/alpha.json",
        "source:alpha.json",
    )
    assert source_path.read_bytes() == raw_bytes
    assert response["tags"] == ["audit", "g006"]
    assert response["related_ids"] == [b_id, c_id]
    assert "../AGENTS.md" not in response["related_ids"]
    assert response["chronology"][0] == {"date": "2026-07-19", "label": "sealed", "id": b_id}
    assert response["chronology"][1] == {"date": "2026-07-20", "label": "bad id"}
    assert response["trust"] == "reviewed"
    assert response["standard_template_status"] == "standard"
    assert response["metadata_status"] == "ok"
    assert response["stale"] is False


def test_invalid_sidecar_id_fails_closed(monkeypatch, tmp_path: Path) -> None:
    _repo, _a_id, b_id, _c_id = _install_tmp_docs(monkeypatch, tmp_path)

    response = research_api.research_doc(b_id)

    assert response["available"] is True
    assert response["metadata_status"] == "invalid_sidecar"
    assert response["tags"] == []
    assert response["related_ids"] == []
    assert response["trust"] == "unknown"
    assert response["standard_template_status"] == "unknown"


def test_research_docs_filters_and_paginates_deterministically(monkeypatch, tmp_path: Path) -> None:
    _repo, a_id, b_id, c_id = _install_tmp_docs(monkeypatch, tmp_path)

    first = research_api.research_docs(tag="audit", category="wiki", limit="1", cursor="0")
    second = research_api.research_docs(
        tag="audit",
        category="wiki",
        limit="1",
        cursor=first["next_cursor"] or "",
    )
    q_match = research_api.research_docs(q="g006", limit="10", cursor="0")

    assert first["available"] is True
    assert first["status"] == "ok"
    assert first["count"] == 1
    assert first["total_count"] == 2
    assert first["next_cursor"] == "1"
    assert first["docs"][0]["id"] == a_id
    assert second["docs"][0]["id"] == c_id
    assert second["next_cursor"] is None
    assert [doc["id"] for doc in q_match["docs"]] == [a_id]
    assert b_id not in {doc["id"] for doc in first["docs"] + second["docs"]}


def test_research_docs_typed_failures_are_bounded(monkeypatch, tmp_path: Path) -> None:
    _install_tmp_docs(monkeypatch, tmp_path)

    for kwargs, status in (
        ({"limit": "0"}, "invalid_limit"),
        ({"limit": "1001"}, "invalid_limit"),
        ({"cursor": "-1"}, "invalid_cursor"),
        ({"q": "bad\x00query"}, "invalid_q"),
        ({"tag": "x" * 49}, "invalid_tag"),
        ({"category": "x" * 49}, "invalid_category"),
    ):
        response = research_api.research_docs(**kwargs)
        assert response == {
            "available": False,
            "status": status,
            "error": status,
            "docs": [],
            "count": 0,
            "total_count": 0,
            "limit": 0,
            "cursor": "0",
            "next_cursor": None,
        }


def test_research_wiki_frontend_source_contracts() -> None:
    frontend = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"
    wiki = (frontend / "research-wiki.jsx").read_text(encoding="utf-8")
    css = (frontend / "styles.css").read_text(encoding="utf-8")

    assert "new URLSearchParams()" in wiki
    assert 'params.set("limit", String(WIKI_PAGE_LIMIT))' in wiki
    assert 'params.set("cursor", filters.cursor || "0")' in wiki
    assert 'params.set("q", filters.q.trim())' in wiki
    assert 'params.set("tag", filters.tag.trim())' in wiki
    assert 'params.set("category", filters.category.trim())' in wiki
    assert "j.docs.filter(isWikiRow)" in wiki
    assert "isWikiChronology" in wiki
    assert "source_sha256" in wiki
    assert "source_bytes" in wiki
    assert "allowedDocById" in wiki
    assert "relatedDocs" in wiki
    assert "listedBase === baseUrl" in wiki
    assert '<pre className="research-wiki-markdown">' in wiki
    assert "innerHTML" not in wiki
    assert ".research-wiki-filters" in css
    assert ".research-wiki-chips" in css
    assert ".research-wiki-metadata" in css
    assert ".research-wiki-related" in css
