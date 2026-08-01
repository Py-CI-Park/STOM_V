"""Research index detail serialization contracts."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import research_index  # noqa: E402
from ai_strategy_loop.dashboard import research_api  # noqa: E402
from ai_strategy_loop.dashboard import research_records  # noqa: E402
from ai_strategy_loop.dashboard import history_api  # noqa: E402


_PATHS = {
    "/private/evidence/posix-key.json": "/private/evidence/posix-value.json",
    "D:/private/evidence/drive-key.json": "D:/private/evidence/drive-value.json",
    r"\\server\share\unc-key.json": r"\\server\share\unc-value.json",
    r"\\?\C:\private\evidence\extended-drive-key.json": r"\\?\C:\private\evidence\extended-drive-value.json",
    r"\\?\UNC\server\share\extended-unc-key.json": r"\\?\UNC\server\share\extended-unc-value.json",
}


def _row(record_id: str, source_path: str = "docs/research/detail.md") -> dict[str, object]:
    return {
        "id": record_id,
        "kind": record_id.split(":", 1)[0],
        "title": "Public detail",
        "source_path": source_path,
        "updated_at": "2026-07-19T00:00:00+00:00",
        "canonicality": "canonical",
        "source_authority": "curated_doc",
        "trace_status": "unknown",
        "related_ids": [],
        "exact_link": f"research-index://{record_id}",
        "detail_available": True,
        "summary": "Keep this summary.",
    }


def _nested_paths() -> dict[str, object]:
    return {
        "label": "keep-me",
        "score": 7,
        "nested": {
            "paths": dict(_PATHS),
            "embedded": {
                "source:C:/private/evidence/key.json": "source:C:/private/evidence/value.json.",
                "link": "[report](C:/private/evidence/link.json)",
                "autolink": "<C:/private/evidence/autolink.json>",
                "inline": "`C:/private/evidence/inline.json`",
                "uri": "https://example.test/C:/private/evidence/keep.json",
                "index_uri": "research-index://doc:docs/research/detail.md",
                "relative": "docs/research/detail.md",
                "route": "/reports/view",
            },
        },
    }


def test_research_index_detail_recursively_redacts_public_absolute_paths(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    document = repo / "docs" / "research" / "detail.md"
    document.parent.mkdir(parents=True)
    document.write_text(
        "\n".join(
            [
                "# Keep this heading",
                "Metadata remains visible.",
                *[f"Path: {path}" for path in _PATHS.values()],
                "Source: source:C:/private/evidence/source.json.",
                "Markdown [link](C:/private/evidence/link.json) <C:/private/evidence/autolink.json> `C:/private/evidence/inline.json`",
                "Preserve https://example.test/C:/private/evidence/keep.json research-index://doc:docs/research/detail.md docs/research/detail.md",
            ]
        ),
        encoding="utf-8",
    )
    rows = [
        _row("doc:docs/research/detail.md"),
        _row("registry:public-entry"),
        _row("loop_run:public-run"),
        _row("decision:1"),
    ]
    monkeypatch.setattr(
        research_index,
        "list_research_index",
        lambda *_args: {"count": len(rows), "records": rows, "errors": [], "cache": {"hit": False, "sources": 0}},
    )
    monkeypatch.setattr(research_index, "_registry_entry", lambda *_args: _nested_paths())
    monkeypatch.setattr(research_index, "_loop_run_entry", lambda *_args: _nested_paths())
    monkeypatch.setattr(research_index, "_decision_entry", lambda *_args: _nested_paths())

    expected_paths = {
        "posix-key.json": "posix-value.json",
        "drive-key.json": "drive-value.json",
        "unc-key.json": "unc-value.json",
        "extended-drive-key.json": "extended-drive-value.json",
        "extended-unc-key.json": "extended-unc-value.json",
    }
    for record_id, detail_field in (
        ("doc:docs/research/detail.md", "markdown"),
        ("registry:public-entry", "registry_entry"),
        ("loop_run:public-run", "registry_entry"),
        ("decision:1", "registry_entry"),
    ):
        detail = research_index.research_index_detail(record_id, repo)

        assert detail["available"] is True
        assert detail["row"]["id"] == record_id
        assert detail["row"]["summary"] == "Keep this summary."
        serialized = json.dumps(detail, ensure_ascii=False)
        assert all(path not in serialized for path in (*_PATHS, *_PATHS.values()))

        if detail_field == "markdown":
            embedded = detail["markdown"]
            assert embedded.startswith("# Keep this heading\nMetadata remains visible.")
            assert all(path in embedded for path in expected_paths.values())
        else:
            entry = detail["registry_entry"]
            assert entry["label"] == "keep-me"
            assert entry["score"] == 7
            assert entry["nested"]["paths"] == expected_paths
            embedded = entry["nested"]["embedded"]
        redacted_text = json.dumps(embedded, ensure_ascii=False).replace(
            "https://example.test/C:/private/evidence/keep.json",
            "",
        )
        assert "C:/private" not in redacted_text
        if isinstance(embedded, str):
            assert "source:source.json." in embedded
            assert "[link](link.json)" in embedded
            assert "<autolink.json>" in embedded
            assert "`inline.json`" in embedded
            assert "https://example.test/C:/private/evidence/keep.json" in embedded
            assert "research-index://doc:docs/research/detail.md" in embedded
            assert "docs/research/detail.md" in embedded
        else:
            assert embedded["source:key.json"] == "source:value.json."
            assert embedded["link"] == "[report](link.json)"
            assert embedded["autolink"] == "<autolink.json>"
            assert embedded["inline"] == "`inline.json`"
            assert embedded["uri"] == "https://example.test/C:/private/evidence/keep.json"
            assert embedded["index_uri"] == "research-index://doc:docs/research/detail.md"
            assert embedded["relative"] == "docs/research/detail.md"
            assert embedded["route"] == "/reports/view"


def test_research_index_list_and_route_use_the_public_serializer(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    evidence = repo / ".omo" / "evidence" / "tmap-walkforward"
    raw_response = {
        "count": 1,
        "records": [
            {
                **_row("doc:docs/research/detail.md"),
                "summary": "source:C:/private/evidence/summary.json.",
                "network": {
                    "source:/private/evidence/network.json": r"\\server\share\network-value.json",
                    "/private/a/shared.json": "first",
                    "C:/private/b/shared.json": "second",
                    "route": "/research_docs",
                },
            },
        ],
        "errors": [{"source_path": "D:/private/evidence/error.json", "reason": "source:C:/private/evidence/error-detail.json"}],
        "cache": {"hit": False, "sources": 0},
    }
    cache_key = f"{repo.resolve()}|{evidence.resolve()}"
    monkeypatch.setattr(research_index, "_collect_sources", lambda *_args: [])
    monkeypatch.setitem(research_index._CACHE, cache_key, ((), raw_response))

    internal_response = research_index.list_research_index(repo, evidence)
    assert internal_response["records"][0]["summary"] == "source:C:/private/evidence/summary.json."
    assert internal_response["records"][0]["network"] == {
        "source:/private/evidence/network.json": r"\\server\share\network-value.json",
        "/private/a/shared.json": "first",
        "C:/private/b/shared.json": "second",
        "route": "/research_docs",
    }

    monkeypatch.setattr(research_api.research_index, "list_research_index", lambda *a, **k: raw_response)
    research_index._PUBLIC_CACHE.clear()
    route_response = research_api.research_index_route()
    serialized = json.dumps(route_response, ensure_ascii=False)
    assert "C:/private" not in serialized
    assert r"\\server\share" not in serialized
    assert route_response["records"][0]["summary"] == "source:summary.json."
    assert route_response["records"][0]["network"] == {
        "source:network.json": "network-value.json",
        "shared.json": "first",
        "shared.json#2": "second",
        "route": "/research_docs",
    }
    assert research_index._redact_embedded_absolute_paths("/") == "[absolute-path]"
    assert research_index._redact_embedded_absolute_paths("C:/") == "[absolute-path]"
    assert research_index._redact_embedded_absolute_paths("/reports/view") == "/reports/view"
    assert research_index._redact_embedded_absolute_paths("/ui/") == "/ui/"
    research_index._PUBLIC_CACHE.clear()


def test_research_doc_route_sanitizes_markdown_without_changing_source(monkeypatch, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    document = repo / "docs" / "research" / "condition_research" / "report.md"
    document.parent.mkdir(parents=True)
    raw_markdown = (
        "# Report\n"
        "source:C:/private/evidence/report.json\n"
        "unix:/private/evidence/report.json\n"
        "route:/research_docs\n"
        "public:https://example.test/C:/private/evidence/keep.json\n"
    )
    document.write_text(raw_markdown, encoding="utf-8")
    summary = {
        "id": "docs/research/condition_research/report.md",
        "title": "Report",
        "category": "condition_research",
        "updated_at": "2026-07-19T00:00:00Z",
    }
    monkeypatch.setattr(research_api, "REPO_ROOT", repo)
    monkeypatch.setattr(research_api, "_doc_index", lambda: {summary["id"]: (document, summary)})
    response = research_api.research_doc(summary["id"])

    assert response["available"] is True
    assert response["markdown"] == (
        "# Report\n"
        "source:report.json\n"
        "unix:report.json\n"
        "route:/research_docs\n"
        "public:https://example.test/C:/private/evidence/keep.json\n"
    )
    assert response["size"] == len(raw_markdown)
    assert document.read_text(encoding="utf-8") == raw_markdown
def test_research_doc_metadata_index_invalidates_on_path_mtime_or_size_change(
    monkeypatch, tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    document = repo / "docs" / "research" / "condition_research" / "cached.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Initial\n", encoding="utf-8")
    monkeypatch.setattr(research_api, "REPO_ROOT", repo)
    monkeypatch.setattr(research_api, "_iter_allowed_docs", lambda: [(document, "condition_research")])
    monkeypatch.setattr(research_api, "_relative_id", lambda path: f"docs/research/condition_research/{path.name}")
    research_api._DOC_INDEX_CACHE = None
    monkeypatch.setattr(research_api, "_DOC_INDEX_SIDECAR", tmp_path / "missing-sidecar.json")
    research_api._DOC_INDEX_CHECKED_AT = 0.0

    calls = 0
    original_summary_for = research_api._summary_for

    def counted_summary(path: Path, category: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        return original_summary_for(path, category)

    monkeypatch.setattr(research_api, "_summary_for", counted_summary)
    assert research_api.research_docs()["docs"][0]["title"] == "Initial"
    assert research_api.research_doc("docs/research/condition_research/cached.md")["available"] is True
    assert calls == 1

    document.write_text("# Changed title\n", encoding="utf-8")
    research_api._DOC_INDEX_CHECKED_AT = 0.0
    assert research_api.research_docs()["docs"][0]["title"] == "Changed title"
    assert calls == 2


def test_research_docs_loads_tracked_sidecar_without_markdown_scan(monkeypatch, tmp_path: Path) -> None:
    document = tmp_path / "docs" / "research" / "condition_research" / "sidecar.md"
    document.parent.mkdir(parents=True)
    document.write_text("# Sidecar source\n", encoding="utf-8")
    sidecar = tmp_path / "docs" / "generated_reports" / "research_docs_index.json"
    sidecar.parent.mkdir(parents=True)
    sidecar.write_text(json.dumps({
        "schema_version": research_api._DOC_INDEX_SIDECAR_SCHEMA,
        "docs": [{
            "id": "docs/research/condition_research/sidecar.md",
            "title": "Sidecar title",
            "category": "condition_research",
            "updated_at": "2026-07-20T00:00:00Z",
            "size": 17,
        }, {
            "id": "docs/research/condition_research/../../secret.md",
            "title": "Traversal must be rejected",
            "category": "condition_research",
            "updated_at": "2026-07-20T00:00:00Z",
            "size": 1,
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(research_api, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(research_api, "_DOC_INDEX_SIDECAR", sidecar)
    monkeypatch.setattr(
        research_api,
        "_iter_allowed_docs",
        lambda: (_ for _ in ()).throw(AssertionError("sidecar must avoid markdown scan")),
    )
    research_api._DOC_INDEX_CACHE = None
    research_api._DOC_INDEX_CHECKED_AT = 0.0

    payload = research_api.research_docs()

    assert payload["total"] == 1
    assert payload["docs"][0]["title"] == "Sidecar title"
    assert research_api.research_doc("docs/research/condition_research/sidecar.md")["available"] is True


def test_research_docs_cache_rebuilds_when_sidecar_identity_changes(monkeypatch, tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    for sidecar, doc_id in (
        (first, "docs/research/condition_research/first.md"),
        (second, "docs/research/condition_research/second.md"),
    ):
        sidecar.write_text(json.dumps({
            "schema_version": research_api._DOC_INDEX_SIDECAR_SCHEMA,
            "docs": [{
                "id": doc_id,
                "title": Path(doc_id).stem,
                "category": "condition_research",
                "updated_at": "2026-08-02T00:00:00Z",
                "size": 1,
            }],
        }), encoding="utf-8")

    monkeypatch.setattr(research_api, "_DOC_INDEX_SIDECAR", first)
    research_api._DOC_INDEX_CACHE = None
    research_api._DOC_INDEX_CACHE_SOURCE = None
    research_api._DOC_INDEX_CHECKED_AT = 0.0
    assert {row["id"] for row in research_api.research_docs()["docs"]} == {
        "docs/research/condition_research/first.md",
    }

    monkeypatch.setattr(research_api, "_DOC_INDEX_SIDECAR", second)
    assert {row["id"] for row in research_api.research_docs()["docs"]} == {
        "docs/research/condition_research/second.md",
    }


def test_research_records_cache_reuses_jsonl_and_invalidates_on_source_change(
    monkeypatch, tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    jsonl = evidence / "campaign.jsonl"
    jsonl.write_text('{"event":"cand","label":"first","profit":1}\n', encoding="utf-8")
    research_records._RECORD_CACHE.clear()

    calls = 0
    original_load_candidates = research_records._load_candidates

    def counted_load(path: Path, errors: list[dict[str, str]]) -> list[dict[str, object]]:
        nonlocal calls
        calls += 1
        return original_load_candidates(path, errors)

    monkeypatch.setattr(research_records, "_load_candidates", counted_load)
    assert research_records.list_research_records(evidence)["count"] == 1
    assert research_records.research_record_detail("campaign", evidence)["available"] is True
    assert calls == 1

    jsonl.write_text('{"event":"cand","label":"second","profit":22}\n', encoding="utf-8")
    detail = research_records.research_record_detail("campaign", evidence)
    assert detail["campaign"]["candidates"][0]["label"] == "second"
    assert calls == 2
def test_history_index_cache_invalidates_from_evidence_signature(monkeypatch, tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    source = evidence / "campaign.jsonl"
    source.write_text('{"event":"cand"}\n', encoding="utf-8")
    history_api._INDEX_CACHE.clear()
    history_api._INDEX_CACHE_CHECKED_AT.clear()
    monkeypatch.setattr(history_api, "EVIDENCE_ROOT", evidence)

    calls = 0

    def build_campaign_index() -> tuple[list[dict[str, object]], bool]:
        nonlocal calls
        calls += 1
        return ([{"research_id": f"campaign:{calls}"}], True)

    monkeypatch.setattr(history_api, "_campaign_index_items", build_campaign_index)
    assert history_api._cached_index_items("campaign")[0][0]["research_id"] == "campaign:1"
    assert history_api._cached_index_items("campaign")[0][0]["research_id"] == "campaign:1"
    assert calls == 1

    source.write_text('{"event":"cand","label":"changed"}\n', encoding="utf-8")
    history_api._INDEX_CACHE_CHECKED_AT["campaign"] = 0.0
    assert history_api._cached_index_items("campaign")[0][0]["research_id"] == "campaign:2"
    assert calls == 2
