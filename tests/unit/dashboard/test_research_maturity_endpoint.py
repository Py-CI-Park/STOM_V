"""G005 — GET /research_maturity 대시보드 엔드포인트 계약 테스트.

- 정상 경로: build_scorecard가 반환하는 스코어카드 payload를 그대로 전달한다.
- 모듈 실패 경로: scripts.research_maturity_scorecard가 없거나 예외를 던져도
  엔드포인트는 500이 아니라 status="error" payload를 무예외로 반환한다.
"""

from __future__ import annotations

import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402

_MODULE_NAME = "scripts.research_maturity_scorecard"


@pytest.fixture
def client(monkeypatch, tmp_path):
    from ai_strategy_loop.dashboard.app import create_app

    db = tmp_path / "loop_runs.db"
    monkeypatch.setattr(S, "LOOP_RUNS_DB", db)
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return authorized_dashboard_client(create_app())


def test_research_maturity_ok(client):
    r = client.get("/research_maturity")
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == "research_maturity_v1"
    assert len(body["stages"]) == 9
    assert 0 <= body["overall_score"] <= 100
    assert "markdown" in body


def test_research_maturity_no_cache_reflects_live_state(client):
    # 캐시 없이 매 호출 재계산 -> 연속 호출도 항상 200과 동일 스키마를 낸다.
    first = client.get("/research_maturity").json()
    second = client.get("/research_maturity").json()
    assert first["schema"] == second["schema"] == "research_maturity_v1"
    assert first["overall_score"] == second["overall_score"]


def test_research_maturity_import_failure_is_graceful(client, monkeypatch):
    monkeypatch.setitem(sys.modules, _MODULE_NAME, None)
    r = client.get("/research_maturity")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "error"
    assert "error" in body


def test_research_maturity_build_scorecard_raises_is_graceful(client, monkeypatch):
    import types

    fake = types.ModuleType(_MODULE_NAME)

    def _boom(repo_root=None):
        raise RuntimeError("synthetic failure")

    fake.build_scorecard = _boom
    monkeypatch.setitem(sys.modules, _MODULE_NAME, fake)
    r = client.get("/research_maturity")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "error"
    assert "synthetic failure" in body.get("error", "")
