"""Read-only index comparison dashboard API tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


def test_index_compare_reports_missing_local_source(monkeypatch, tmp_path: Path) -> None:
    """Given no supported local index source, When comparing, Then the API is honest and offline."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    client = authorized_dashboard_client(create_app())

    response = client.get("/index_compare", params={"run_id": "missing_run"})

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "available": False,
        "reason": "local_index_source_not_found",
        "run_id": "missing_run",
        "network_used": False,
        "source": "local",
    }
