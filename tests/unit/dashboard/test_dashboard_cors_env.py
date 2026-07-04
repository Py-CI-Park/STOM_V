"""CORS env 옵트인(STOM_DASHBOARD_ALLOWED_ORIGINS) 게이트.

기본 allowlist(8770 localhost 전용)는 불변이어야 하고, env 로만 명시 확장된다.
V4 프리뷰(다른 포트 서빙)가 백엔드 데이터를 읽는 cross-origin 시나리오의 정식 경로.
"""
from __future__ import annotations

import os
import sys

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from starlette.testclient import TestClient  # noqa: E402


def _client(monkeypatch, extra=None) -> TestClient:
    if extra is None:
        monkeypatch.delenv("STOM_DASHBOARD_ALLOWED_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("STOM_DASHBOARD_ALLOWED_ORIGINS", extra)
    from ai_strategy_loop.dashboard import app as app_mod

    return TestClient(app_mod.create_app())


def test_default_denies_unlisted_origin(monkeypatch) -> None:
    """env 미설정 시 8790 등 미등록 origin 은 CORS 헤더를 받지 못한다(기본 정책 불변)."""
    c = _client(monkeypatch)
    r = c.get("/health", headers={"Origin": "http://127.0.0.1:8790"})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers.keys()}


def test_default_allows_dashboard_port(monkeypatch) -> None:
    """기본 allowlist(8770)는 그대로 허용된다."""
    c = _client(monkeypatch)
    r = c.get("/health", headers={"Origin": "http://127.0.0.1:8770"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:8770"


def test_env_extends_allowlist(monkeypatch) -> None:
    """env 에 명시한 origin 은 허용 목록에 가산된다(콤마 구분·후행 슬래시 무시)."""
    c = _client(monkeypatch, "http://127.0.0.1:8790/, http://localhost:8790")
    r = c.get("/health", headers={"Origin": "http://127.0.0.1:8790"})
    assert r.headers.get("access-control-allow-origin") == "http://127.0.0.1:8790"


def test_env_rejects_non_http_entries(monkeypatch) -> None:
    """http(s) 형식이 아닌 항목은 무시된다(오설정 안전)."""
    c = _client(monkeypatch, "ftp://evil, not-a-url")
    r = c.get("/health", headers={"Origin": "ftp://evil"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers.keys()}
