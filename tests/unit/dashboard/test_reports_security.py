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

from pathlib import Path

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
