"""UXR-P7 — Reports 허브 보안 계약(§10-5).

검증:
  - /reports: docs/ 하위 *.html 목록(process_flow.html 포함).
  - /reports/view: 유효 리포트는 200 + 스크립트 차단 CSP(default-src 'none', script-src 없음)
    + nosniff.
  - traversal(../, 절대경로)·비-html·빈 경로·null byte 는 404(파일 유출 차단).
  - _safe_report_path 순수 함수: 루트 탈출/비-html/부재는 None.

실서버·디스크 쓰기 없음: create_app + TestClient(loopback origin)만 쓴다.
"""

from __future__ import annotations
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard import app as app_module
from ai_strategy_loop.dashboard.app import create_app

ORIGIN = "http://127.0.0.1:8770"
ORIGIN_HEADER = {"Origin": ORIGIN}
FRONTEND = Path(__file__).resolve().parents[3] / "ai_strategy_loop" / "dashboard" / "frontend"


def _frontend_source(name: str) -> str:
    return (FRONTEND / name).read_text(encoding="utf-8")


def _client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app(), base_url=ORIGIN)


def test_reports_lists_docs_html_including_process_flow(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    r = client.get("/reports", headers=ORIGIN_HEADER)
    assert r.status_code == 200
    body = r.json()
    assert body["root"] == "docs"
    paths = {item["path"] for item in body["reports"]}
    assert "process_flow.html" in paths
    # 모든 항목은 .html 이고 상대 경로(탈출 없음).
    for item in body["reports"]:
        assert item["path"].lower().endswith(".html")
        assert ".." not in item["path"]



def test_reports_catalog_exposes_verified_manifest_metadata(
    monkeypatch, tmp_path: Path,
) -> None:
    reports_root = tmp_path / "docs"
    generated = reports_root / "generated_reports"
    generated.mkdir(parents=True)
    html = '<!doctype html><h2 id="sec-flow">Flow</h2>'
    report_path = generated / "run_report_demo.html"
    report_path.write_text(html, encoding="utf-8")
    digest = hashlib.sha256(html.encode("utf-8")).hexdigest()
    (generated / "manifest.json").write_text(json.dumps({
        "schema_version": "stom-research-report-v1",
        "count": 1,
        "reports": [{
            "schema_version": "stom-research-report-v1",
            "path": report_path.name,
            "registered": True,
            "report_id": "run:demo",
            "report_type": "run",
            "research_id": "demo",
            "run_id": "demo",
            "status": "complete",
            "trust": "derived",
            "content_sha256": digest,
            "bytes": len(html.encode("utf-8")),
            "source_sha256": "1" * 64,
            "toc": [{"id": "sec-flow", "label": "Flow"}],
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(app_module, "_REPORTS_ROOT", str(reports_root))
    app_module._REPORT_CATALOG_CACHE.clear()

    response = _client(monkeypatch, tmp_path).get("/reports", headers=ORIGIN_HEADER)

    assert response.status_code == 200
    body = response.json()
    assert body["registered_count"] == 1
    item = body["reports"][0]
    assert item["registered"] is True
    assert item["report_type"] == "run"
    assert item["run_id"] == "demo"
    assert item["content_sha256"] == digest
    assert item["toc"] == [{"id": "sec-flow", "label": "Flow"}]
    assert item["integrity_status"] == "verified"


def test_reports_catalog_rejects_tampered_manifest_registered_file(
    monkeypatch, tmp_path: Path,
) -> None:
    reports_root = tmp_path / "docs"
    generated = reports_root / "generated_reports"
    generated.mkdir(parents=True)
    report_path = generated / "run_report_demo.html"
    report_path.write_text("original", encoding="utf-8")
    digest = hashlib.sha256(report_path.read_bytes()).hexdigest()
    (generated / "manifest.json").write_text(json.dumps({
        "schema_version": "stom-research-report-v1",
        "count": 1,
        "reports": [{
            "schema_version": "stom-research-report-v1",
            "path": report_path.name,
            "content_sha256": digest,
            "bytes": len("original".encode("utf-8")),
            "status": "complete",
            "trust": "derived",
        }],
    }), encoding="utf-8")
    report_path.write_text("tampered", encoding="utf-8")
    monkeypatch.setattr(app_module, "_REPORTS_ROOT", str(reports_root))
    app_module._REPORT_CATALOG_CACHE.clear()

    body = _client(monkeypatch, tmp_path).get("/reports", headers=ORIGIN_HEADER).json()
    item = body["reports"][0]

    assert body["registered_count"] == 0
    assert item["registered"] is False
    assert item["integrity_status"] == "failed"
    assert item["integrity_error"] == "content_sha256_mismatch"
    assert "status" not in item and "trust" not in item and "content_sha256" not in item


def test_reports_catalog_cold_rebuild_is_single_flight(monkeypatch, tmp_path: Path) -> None:
    reports_root = tmp_path / "docs"
    reports_root.mkdir()
    (reports_root / "report.html").write_text("report", encoding="utf-8")
    monkeypatch.setattr(app_module, "_REPORTS_ROOT", str(reports_root))
    app_module._REPORT_CATALOG_CACHE.clear()
    original = app_module._report_manifest_rows
    calls = 0

    def delayed_rows(root: str):
        nonlocal calls
        calls += 1
        time.sleep(0.02)
        return original(root)

    monkeypatch.setattr(app_module, "_report_manifest_rows", delayed_rows)
    with ThreadPoolExecutor(max_workers=6) as pool:
        catalogs = list(pool.map(lambda _: app_module._report_catalog(), range(6)))

    assert calls == 1
    assert all(catalog == catalogs[0] for catalog in catalogs)


def test_debug_logs_require_session_and_redact_sensitive_values(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    denied = client.get("/debug/logs", headers=ORIGIN_HEADER)
    assert denied.status_code == 401

    bootstrap = client.get("/ui/", headers=ORIGIN_HEADER)
    assert bootstrap.status_code == 200
    logging.getLogger("dashboard-test").warning(
        "token=secret-value Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.sig "
        "windows=C:/Users/parkc/private posix=/home/parkc/private"
    )
    allowed = client.get("/debug/logs", headers=ORIGIN_HEADER)
    assert allowed.status_code == 200
    messages = [row["msg"] for row in allowed.json()["logs"]]
    assert any("token=<redacted>" in message for message in messages)
    assert allowed.headers.get("cache-control") == "no-store, private"
    assert all(
        secret not in message
        for secret in (
            "secret-value", "eyJhbGciOiJIUzI1NiJ9.payload.sig", "C:/Users/parkc",
            "/home/parkc",
        )
        for message in messages
    )

def test_report_view_serves_with_script_blocking_csp(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    r = client.get("/reports/view", params={"path": "process_flow.html"}, headers=ORIGIN_HEADER)
    assert r.status_code == 200
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp          # 스크립트 포함 모든 기본 소스 차단
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
def test_reports_frontend_uses_metadata_toc_without_duplicate_html_fetch() -> None:
    source = _frontend_source("v4-reports.jsx")

    assert "function _reportToc(report)" in source
    assert "Array.isArray(report && report.toc)" in source
    assert 'fetch(baseUrl + "/reports/view?path="' not in source
    assert 'iframe key={sel}' in source
    assert "목차 없음 · 레거시 리포트 메타데이터 미제공" in source


def test_reports_mode_tabs_link_panels_and_roving_keys() -> None:
    source = _frontend_source("v4-reports.jsx")

    assert 'id="v4-reports-mode-tab-reports"' in source
    assert 'aria-controls="v4-reports-panel-reports"' in source
    assert 'id="v4-reports-mode-tab-wiki"' in source
    assert 'aria-controls="v4-reports-panel-wiki"' in source
    assert 'tabIndex={mode === "reports" ? 0 : -1}' in source
    assert 'tabIndex={mode === "wiki" ? 0 : -1}' in source
    assert 'event.key === "Home"' in source
    assert 'event.key === "End"' in source
def test_reports_frontend_catalog_uses_manifest_metadata_and_preserves_unregistered_boundary() -> None:
    source = _frontend_source("v4-reports.jsx")
    css = _frontend_source("v4.css")

    assert 'report.registered !== true' in source
    assert '["run", "step", "legacy"].includes(report.report_type)' in source
    assert "미등록·검증 불가" in source
    assert "rp.research_id" in source or "selectedReport.research_id" in source
    assert "rp.run_id" in source or "selectedReport.run_id" in source
    assert "rp.status" in source and "selectedReport.status" in source
    assert "rp.trust" in source and "selectedReport.trust" in source
    assert "content_sha256" in source and "source_sha256" in source
    assert "v4-reports-toc-toggle" in source
    assert "v4-reports-toc-slot.open" in css
    assert "@media (max-width: 1200px)" in css
    assert "run_report_" not in source
def test_reports_frontend_keeps_the_report_iframe_as_the_single_view_request() -> None:
    source = _frontend_source("v4-reports.jsx")

    assert 'fetch(baseUrl + "/reports/view?path="' not in source
    assert 'iframe key={sel}' in source
    assert 'src={frameSrc}' in source
