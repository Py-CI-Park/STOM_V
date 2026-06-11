"""Tab-shell contract tests (PR1) — backtest/simulation health routes + frontend wiring.

검증 대상:
- 신규 라우터 ``/bt/health`` / ``/sim/health`` 가 200 + 약속된 페이로드를 반환한다.
- 기존 ``/health`` 가 여전히 200 (라우터 추가가 기존 계약을 깨지 않음).
- ``/ui/`` 정적 서빙이 여전히 200 (마운트 무영향).
- index.html 이 backtest.jsx / simulation.jsx 를 app.jsx 보다 먼저 로드한다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402

FRONTEND = Path(PROJECT_ROOT) / "ai_strategy_loop" / "dashboard" / "frontend"


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    """Create an isolated dashboard client without touching live loop state."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


def test_backtest_health_returns_contract_payload(monkeypatch, tmp_path: Path) -> None:
    """Given the tab shell, When GET /bt/health, Then the backtest module reports ok."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/bt/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "backtest_api", "api_version": 1}


def test_simulation_health_returns_contract_payload(monkeypatch, tmp_path: Path) -> None:
    """Given the tab shell, When GET /sim/health, Then the simulation module reports ok."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/sim/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "module": "simulation_api", "api_version": 1}


def test_existing_health_route_unaffected(monkeypatch, tmp_path: Path) -> None:
    """Given new routers added, When GET /health, Then the legacy route still returns 200."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_static_ui_mount_unaffected(monkeypatch, tmp_path: Path) -> None:
    """Given new routers added, When GET /ui/, Then static serving still returns 200 html."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/ui/")

    assert response.status_code == 200
    assert "text/html" in (response.headers.get("content-type") or "")


def test_index_html_loads_tab_scripts_before_app() -> None:
    """Given index.html, Then backtest.jsx and simulation.jsx load before app.jsx."""
    index = (FRONTEND / "index.html").read_text(encoding="utf-8")

    assert "backtest.jsx" in index
    assert "simulation.jsx" in index
    assert index.index("backtest.jsx") < index.index("app.jsx")
    assert index.index("simulation.jsx") < index.index("app.jsx")
