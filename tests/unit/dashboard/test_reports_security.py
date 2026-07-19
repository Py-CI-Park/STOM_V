"""UXR-P7 — Reports 허브 보안 계약(§10-5).

검증:
  - /reports: docs/ 하위 *.html 목록(process_flow.html 포함).
  - /reports/view: 유효 리포트는 200 + 스크립트 차단 CSP(default-src 'none', script-src 없음)
    + nosniff.
  - traversal(../, 절대경로)·비-html·빈 경로·null byte 는 404(파일 유출 차단).
  - _safe_report_path 순수 함수: 루트 탈출/비-html/부재는 None.

실서버·운영 디스크 쓰기 없음: create_app + TestClient(loopback origin)와 tmp_path fixture만 쓴다.
"""

from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ai_strategy_loop" / "dashboard" / "frontend"

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard import app as app_module
from ai_strategy_loop.dashboard.app import create_app

ORIGIN = "http://127.0.0.1:8770"
ORIGIN_HEADER = {"Origin": ORIGIN}


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app(), base_url=ORIGIN)


def _manifest_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[TestClient, Path]:
    docs = tmp_path / "docs"
    docs.mkdir()
    monkeypatch.setattr(app_module, "_REPORTS_ROOT", str(docs))
    return _client(monkeypatch, tmp_path), docs


def _write_report(docs: Path, rel: str, html: str = "<h1>report</h1>") -> Path:
    target = docs / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(docs: Path, payload: dict) -> Path:
    target = docs / app_module._REPORTS_MANIFEST_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def test_reports_lists_docs_html_including_process_flow(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    r = client.get("/reports", headers=ORIGIN_HEADER)
    assert r.status_code == 200
    body = r.json()
    assert body["root"] == "docs"
    assert body["manifest"]["schema"] == app_module._REPORTS_MANIFEST_SCHEMA
    assert body["manifest"]["source"] == app_module._REPORTS_MANIFEST_REL
    paths = {item["path"] for item in body["reports"]}
    assert "process_flow.html" in paths
    # 모든 항목은 .html 이고 상대 경로(탈출 없음).
    for item in body["reports"]:
        assert item["path"].lower().endswith(".html")
        assert ".." not in item["path"]


def test_report_view_serves_with_script_blocking_csp(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    r = client.get("/reports/view", params={"path": "process_flow.html"}, headers=ORIGIN_HEADER)
    assert r.status_code == 200
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp          # 스크립트 포함 모든 기본 소스 차단
    assert csp == app_module._REPORTS_CSP
    assert "script-src" not in csp               # script-src 명시 없음 → default-src 'none' 적용
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert "no-store" in r.headers.get("cache-control", "")


@pytest.mark.parametrize(
    "bad",
    [
        "../README.md",
        "../../etc/passwd",
        "..\\..\\Windows\\win.ini",
        "/etc/passwd",
        "AGENTS.md",           # 루트 하위지만 비-html
        "process_flow.html/../../secret",
        "",
    ],
)
def test_report_view_rejects_traversal_and_non_html(monkeypatch, tmp_path: Path, bad: str) -> None:
    client = _client(monkeypatch, tmp_path)
    r = client.get("/reports/view", params={"path": bad}, headers=ORIGIN_HEADER)
    assert r.status_code == 404, f"경로 유출 가능: {bad!r}"


def test_report_routes_reject_symlink_escape(monkeypatch, tmp_path: Path) -> None:
    reports_root = tmp_path / "docs"
    reports_root.mkdir()
    outside = tmp_path / "outside.html"
    outside.write_text("<h1>outside secret</h1>", encoding="utf-8")
    escape = reports_root / "escape.html"
    try:
        os.symlink(outside, escape)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")

    monkeypatch.setattr(app_module, "_REPORTS_ROOT", str(reports_root))
    client = _client(monkeypatch, tmp_path)

    assert app_module._safe_report_path("escape.html") is None
    view = client.get("/reports/view", params={"path": "escape.html"}, headers=ORIGIN_HEADER)
    assert view.status_code == 404
    listed = client.get("/reports", headers=ORIGIN_HEADER)
    assert listed.status_code == 200
    assert "escape.html" not in {item["path"] for item in listed.json()["reports"]}


def test_safe_report_path_unit_boundary() -> None:
    root = app_module._reports_root_abs()
    # 유효.
    ok = app_module._safe_report_path("process_flow.html")
    assert ok is not None and ok.startswith(root)
    # 탈출/비-html/빈/부재.
    assert app_module._safe_report_path("../README.md") is None
    assert app_module._safe_report_path("AGENTS.md") is None
    assert app_module._safe_report_path("") is None
    assert app_module._safe_report_path("nope.html") is None
    assert app_module._safe_report_path("a\x00b.html") is None


def test_reports_marks_flat_fallback_as_legacy_when_manifest_missing(monkeypatch, tmp_path: Path) -> None:
    client, docs = _manifest_client(monkeypatch, tmp_path)
    _write_report(docs, "flat/only.html")

    r = client.get("/reports", headers=ORIGIN_HEADER)

    assert r.status_code == 200
    body = r.json()
    assert body["reports"] == [
        {"path": "flat/only.html", "name": "only.html", "bytes": len("<h1>report</h1>"), "mtime": body["reports"][0]["mtime"]}
    ]
    assert body["manifest"]["available"] is False
    assert body["manifest"]["reports"] == []
    assert body["manifest"]["errors"][0]["type"] == "manifest_missing"


def test_reports_accepts_writer_generated_manifest_contract(monkeypatch, tmp_path: Path) -> None:
    from alpha_lab.reporting.build_html import build_all
    from scripts import build_research_report as report_writer

    client, docs = _manifest_client(monkeypatch, tmp_path)
    out_dir = docs / "research" / "condition_research" / "reports"
    _write_report(
        docs,
        "research/condition_research/reports/2026-07-16_b1_program_report.html",
        "<h1>preserved legacy report</h1>",
    )
    files = build_all(commit="writer-contract")
    manifest = report_writer.build_manifest(
        files,
        commit="writer-contract",
        generated_at="2026-07-19T00:00:00Z",
    )
    report_writer.write_reports_atomic(out_dir, files, manifest)

    response = client.get("/reports", headers=ORIGIN_HEADER)

    assert response.status_code == 200
    envelope = response.json()["manifest"]
    assert envelope["available"] is True
    assert envelope["errors"] == []
    assert envelope["count"] == len(files)
    assert all(isinstance(row["missing"], list) for row in envelope["reports"])
    assert all(row["trust"] == "manual-offline" for row in envelope["reports"])


def test_reports_manifest_validates_paths_and_exposes_only_safe_metadata(monkeypatch, tmp_path: Path) -> None:
    client, docs = _manifest_client(monkeypatch, tmp_path)
    good_rel = "research/condition_research/reports/good.html"
    stale_rel = "research/condition_research/reports/stale.html"
    bad_hash_rel = "research/condition_research/reports/bad_hash.html"
    good = _write_report(docs, good_rel, "<h1>good</h1>")
    stale = _write_report(docs, stale_rel, "<h1>stale</h1>")
    bad_hash = _write_report(docs, bad_hash_rel, "<h1>bad hash</h1>")
    _write_report(docs, "secret.html", "<h1>secret</h1>")
    _write_manifest(docs, {
        "schema": app_module._REPORTS_MANIFEST_SCHEMA,
        "writer": "manual-offline",
        "generated_at": "2026-07-19T00:00:00Z",
        "commit": "abc123",
        "reports": [
            {
                "path": good_rel,
                "title": "Good Report",
                "kind": "program",
                "research_id": "rid-good",
                "step_id": "step-1",
                "html_sha256": _sha256(good),
                "bytes": good.stat().st_size,
                "source_paths": ["research/source/good.md", "../escape.md"],
                "source_sha256": {"research/source/good.md": "1" * 64, str(tmp_path / "secret.md"): "2" * 64},
                "trust": "manual-offline",
                "missing": ["research/source/good.md", "../escape.md"],
                "stale": False,
                "links": ["#summary", f"/reports/view?path={good_rel}#summary", "https://example.invalid/report"],
            },
            {
                "path": stale_rel,
                "title": "Stale Report",
                "kind": "step",
                "research_id": "rid-good",
                "step_id": "step-2",
                "html_sha256": "0" * 64,
                "bytes": stale.stat().st_size + 9,
                "source_paths": [],
                "source_sha256": {},
                "trust": "manual-offline",
                "missing": [],
                "stale": False,
                "links": [],
            },
            {
                "path": bad_hash_rel,
                "title": "Bad Hash",
                "kind": "step",
                "research_id": "rid-bad",
                "step_id": "bad-hash",
                "html_sha256": "not-a-sha",
                "bytes": bad_hash.stat().st_size,
                "source_paths": [],
                "source_sha256": {},
                "trust": "manual-offline",
                "missing": [],
                "stale": False,
                "links": [],
            },
            {
                "path": "../secret.html",
                "title": "Traversal",
                "kind": "step",
                "research_id": "rid-bad",
                "step_id": "step-x",
                "html_sha256": "3" * 64,
                "bytes": 1,
                "source_paths": [],
                "source_sha256": {},
                "trust": "manual-offline",
                "missing": [],
                "stale": False,
                "links": [],
            },
        ],
    })

    r = client.get("/reports", headers=ORIGIN_HEADER)

    assert r.status_code == 200
    body = r.json()
    manifest = body["manifest"]
    assert manifest["available"] is True
    assert manifest["writer"] == "manual-offline"
    assert manifest["source"] == app_module._REPORTS_MANIFEST_REL
    rows = {row["path"]: row for row in manifest["reports"]}
    assert set(rows) == {good_rel, stale_rel}
    assert rows[good_rel]["research_id"] == "rid-good"
    assert rows[good_rel]["step_id"] == "step-1"
    assert rows[good_rel]["hash_status"] == "match"
    assert rows[good_rel]["missing"] == ["research/source/good.md"]
    assert rows[good_rel]["stale"] is False
    assert rows[good_rel]["source_paths"] == ["research/source/good.md"]
    assert rows[good_rel]["source_sha256"] == {"research/source/good.md": "1" * 64}
    assert rows[good_rel]["links"] == ["#summary", f"/reports/view?path={good_rel}#summary"]
    assert rows[stale_rel]["hash_status"] == "mismatch"
    assert rows[stale_rel]["stale"] is True
    error_types = {error["type"] for error in manifest["errors"]}
    assert {
        "report_path_invalid",
        "report_source_path_invalid",
        "report_missing_path_invalid",
        "report_link_invalid",
        "report_hash_invalid",
        "report_hash_mismatch",
        "report_bytes_mismatch",
    } <= error_types
    serialized = json.dumps(body)
    assert str(tmp_path) not in serialized
    assert "../secret.html" not in serialized


def test_reports_manifest_requires_manual_writer(monkeypatch, tmp_path: Path) -> None:
    client, docs = _manifest_client(monkeypatch, tmp_path)
    rel = "research/condition_research/reports/report.html"
    report = _write_report(docs, rel)
    _write_manifest(docs, {
        "schema": app_module._REPORTS_MANIFEST_SCHEMA,
        "writer": "frontend-build",
        "reports": [{
            "path": rel,
            "title": "Report",
            "kind": "step",
            "research_id": "rid",
            "step_id": "step",
            "html_sha256": _sha256(report),
            "bytes": report.stat().st_size,
            "source_paths": [],
            "source_sha256": {},
            "trust": "manual-offline",
            "missing": [],
            "stale": False,
            "links": [],
        }],
    })

    r = client.get("/reports", headers=ORIGIN_HEADER)

    assert r.status_code == 200
    manifest = r.json()["manifest"]
    assert manifest["available"] is False
    assert manifest["reports"] == []
    assert manifest["errors"][0]["type"] == "manifest_writer_invalid"


def test_reports_manifest_code_does_not_add_get_or_ws_writes() -> None:
    source = (ROOT / "ai_strategy_loop" / "dashboard" / "app.py").read_text(encoding="utf-8")
    helper_region = source[source.index("_REPORTS_MANIFEST_REL"):source.index("_DASHBOARD_FAVICON_SVG")]
    route_region = source[source.index('@app.get("/reports")'):source.index('@app.get("/status")')]
    guarded = helper_region + route_region

    assert ".write(" not in guarded
    assert "os.makedirs" not in guarded
    assert "@app.websocket" not in route_region


def test_report_and_wiki_sources_cancel_stale_base_requests() -> None:
    reports = (FRONTEND / "v4-reports.jsx").read_text(encoding="utf-8")
    wiki = (FRONTEND / "research-wiki.jsx").read_text(encoding="utf-8")

    assert "new AbortController()" in reports
    assert "generation !== generationRef.current" in reports
    assert "baseUrl !== baseRef.current" in reports
    assert 'setList(baseUrl ? null : []);' in reports
    assert 'setSel("");' in reports
    assert "j.reports.filter(isReport)" in reports
    assert "const ownsSelection = Boolean(baseUrl && listedBase === baseUrl" in reports
    assert 'sandbox=""' in reports
    assert 'referrerPolicy="no-referrer"' in reports
    assert "manifestReports.length ? manifestReports : reports" in reports
    assert "setManifest(null)" in reports
    assert "_manifestGroups(manifestRows)" in reports
    assert "manifest errors:" in reports
    assert "provenance" in reports
    assert "allowlisted links" in reports
    assert "!usingManifest && list.map" in reports
    assert "dangerouslySetInnerHTML" not in reports
    assert "const [listLoading, setListLoading]" in wiki
    assert "const [detailLoading, setDetailLoading]" in wiki
    assert "const [listErr, setListErr]" in wiki
    assert "const [detailErr, setDetailErr]" in wiki
    assert "new AbortController()" in wiki
    assert "generation !== listGenerationRef.current" in wiki
    assert "generation !== detailGenerationRef.current" in wiki
    assert "baseUrl !== baseRef.current" in wiki
    assert "selectedId !== selectedIdRef.current" in wiki
    assert "baseUrl === baseRef.current" in wiki
    assert "const owned = listedBase === baseUrl" in wiki
    assert "}, [baseUrl, isDemo]);" in wiki
    assert "isSelectedWikiDoc(j, selectedId) ? j : null" in wiki
    assert "j.docs.filter(isWikiRow)" in wiki
    assert '<pre className="research-wiki-markdown">' in wiki
    assert "innerHTML" not in wiki