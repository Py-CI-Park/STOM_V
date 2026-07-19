from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from alpha_lab.reporting import registry
from alpha_lab.reporting.build_html import build_all, extract_report_links
from scripts import build_research_report as writer

_SAFE_REPORT_PREFIX = "/reports/view?path=research/condition_research/reports/"


def _assert_safe_links(html: str) -> None:
    lower = html.lower()
    assert "<script" not in lower
    assert "javascript:" not in lower
    assert not re.search(r"\shref=(['\"])https?://", html, re.IGNORECASE)
    assert not re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE)
    assert 'href="research/' not in html
    assert 'href="../' not in html
    links = extract_report_links(html)
    assert links
    for link in links:
        assert link.startswith("#tab-") or link.startswith(_SAFE_REPORT_PREFIX)


def test_generated_reports_are_scriptless_and_allowlisted() -> None:
    files = build_all(commit="abc123")

    assert "research_lab_report.html" in files
    assert f"research/{registry.STUDIES[0].id}.html" in files
    for html in files.values():
        _assert_safe_links(html)
        assert 'href="#tab-overview"' in html


def test_manifest_schema_hashes_and_stable_rows() -> None:
    files = build_all(commit="abc123")
    manifest = writer.build_manifest(files, commit="abc123", generated_at="2026-07-19T00:00:00Z")

    assert manifest["schema"] == "stom-research-report-manifest-v1"
    assert manifest["writer"] == "manual-offline"
    assert manifest["generated_at"] == "2026-07-19T00:00:00Z"
    assert manifest["commit"] == "abc123"

    rows = manifest["reports"]
    assert len(rows) == 1 + len(registry.STUDIES)
    assert rows[0]["path"] == "research_lab_report.html"
    assert rows[0]["kind"] == "hub"
    assert rows[0]["research_id"] == "alpha_restart_20260710"

    required = {
        "path", "title", "kind", "research_id", "html_sha256", "bytes", "source_paths",
        "source_sha256", "trust", "missing", "stale", "links",
    }
    for row in rows:
        assert required.issubset(row)
        html = files[row["path"]]
        assert row["html_sha256"] == hashlib.sha256(html.encode("utf-8")).hexdigest()
        assert row["bytes"] == len(html.encode("utf-8"))
        assert row["trust"] == "manual-offline"
        assert isinstance(row["source_paths"], list) and row["source_paths"]
        assert isinstance(row["source_sha256"], dict)
        assert isinstance(row["missing"], list)
        assert row["stale"] == bool(row["missing"])
        assert row["links"] == extract_report_links(html)
        for link in row["links"]:
            assert link.startswith("#tab-") or link.startswith(_SAFE_REPORT_PREFIX)

    detail_rows = rows[1:]
    assert {row["research_id"] for row in detail_rows} == {study.id for study in registry.STUDIES}
    assert all(row.get("step_id") for row in detail_rows)


def test_output_restriction_and_atomic_failure_leave_no_partial_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    allowed = tmp_path / "docs" / "research" / "condition_research" / "reports"
    monkeypatch.setattr(writer, "_DEFAULT_OUT", allowed)

    assert writer._resolve_out_dir(str(allowed)) == allowed
    with pytest.raises(ValueError, match="restricted"):
        writer._resolve_out_dir(str(tmp_path / "elsewhere"))

    out_dir = allowed

    def boom(_path: Path, _text: str) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(writer, "_write_text", boom)
    with pytest.raises(OSError, match="simulated"):
        writer.write_reports_atomic(
            out_dir,
            {"research_lab_report.html": "<html></html>"},
            {"schema": "stom-research-report-manifest-v1"},
        )

    assert not out_dir.exists()
    assert not any(allowed.parent.iterdir())
