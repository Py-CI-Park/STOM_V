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
    # PR2: 차트 분리 모듈은 backtest.jsx 보다 먼저 로드돼야 한다(window 전역 공유 의존).
    assert index.index("backtest-charts.jsx") < index.index("backtest.jsx?")


# --------------------------------------------------- Track C (즉시 체험) frontend
def test_simulation_jsx_has_instant_experience_surface() -> None:
    """simulation.jsx 가 자동 데모·원클릭 프리셋 표면을 갖는다(Track C)."""
    src = (FRONTEND / "simulation.jsx").read_text(encoding="utf-8")
    # 원클릭 프리셋 바 + 두 모드.
    assert "SimPresetBar" in src
    assert "최근 거래일" in src
    assert "최대 상승일" in src
    # 자동 데모: /sim/demo 소비 + 예시 배지 + 해제 버튼 + localStorage 1회 기억.
    assert "/sim/demo" in src
    assert "예시 자동 재생" in src
    assert "내가 선택하기" in src
    assert "stom.sim.demoSeen" in src


def test_simulation_charts_jsx_has_visual_components() -> None:
    """simulation-charts.jsx 가 등락 게이지·세션 링·신호 플래시 비주얼을 갖는다(Track C)."""
    src = (FRONTEND / "simulation-charts.jsx").read_text(encoding="utf-8")
    assert "SimChangeGauge" in src        # 등락율 반원 게이지.
    assert "SimSessionRing" in src        # 세션 진행 링.
    assert "_sessionProgress" in src      # 09:00~15:30 진행률.
    # 신호 도달 플래시 — 인라인 boxShadow(styles.css 불가)로 1회 점멸.
    assert "boxShadow" in src
    assert "window._simTimeLabel" not in src or "_simTimeLabel" in src
    # 두 컴포넌트가 window 전역으로 노출돼 simulation.jsx 가 쓸 수 있어야 한다.
    assert "SimChangeGauge, SimSessionRing" in src


def test_simulation_demo_route_returns_contract(monkeypatch, tmp_path: Path) -> None:
    """GET /sim/demo 가 추천 계약(date/code/available 키)을 반환한다(데이터 없어도 무예외)."""
    client = _client(monkeypatch, tmp_path)
    # 격리 클라이언트엔 _database 가 없으므로 available=False 빈 추천(무예외 200).
    from ai_strategy_loop.dashboard import simulation_api as SA

    monkeypatch.setattr(SA, "_DATABASE_DIR", tmp_path / "no_such_db_dir")
    response = client.get("/sim/demo?src=min&mode=latest")
    assert response.status_code == 200
    body = response.json()
    for key in ("date", "code", "name", "change_pct", "src", "mode", "available"):
        assert key in body
    assert body["available"] is False
    assert body["mode"] == "latest"
