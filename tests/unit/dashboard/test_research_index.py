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
    }

    monkeypatch.setattr(research_api.research_index, "list_research_index", lambda: raw_response)
    route_response = research_api.research_index_route()
    serialized = json.dumps(route_response, ensure_ascii=False)
    assert "C:/private" not in serialized
    assert r"\\server\share" not in serialized
    assert route_response["records"][0]["summary"] == "source:summary.json."
    assert route_response["records"][0]["network"] == {
        "source:network.json": "network-value.json",
        "shared.json": "first",
        "shared.json#2": "second",
    }
    assert research_index._redact_embedded_absolute_paths("/") == "[absolute-path]"
    assert research_index._redact_embedded_absolute_paths("C:/") == "[absolute-path]"
