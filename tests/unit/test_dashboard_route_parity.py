"""Dashboard route parity tests for frontend-called read-only APIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import state as S  # noqa: E402

FRONTEND = PROJECT_ROOT / "ai_strategy_loop" / "dashboard" / "frontend"

READ_ONLY_ROUTE_PROBES = {
    "/strategy_diff": {"gen_no": "0"},
    "/prompts": {},
    "/ai_context_pack": {},
    "/research_criteria": {},
    "/research_docs": {},
    "/research_doc": {},
    "/index_compare": {},
    "/variable_correlation": {},
}

FRONTEND_ROUTE_OWNERS = {
    "/strategy_diff": "strategy-inspector.jsx",
    "/prompts": "strategy-inspector.jsx",
    "/ai_context_pack": "ai-context.jsx",
    "/research_criteria": "panels.jsx",
    "/research_docs": "research-wiki.jsx",
    "/research_doc": "research-wiki.jsx",
    "/variable_correlation": "research-lab.jsx",
}


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    """Create an isolated dashboard client without touching live loop state."""
    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setattr(S, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(S, "STOP_FLAG_FILE", tmp_path / "STOP")
    return TestClient(create_app())


def test_dashboard_fresh_app_exposes_frontend_called_routes(monkeypatch, tmp_path: Path) -> None:
    """Given a fresh app, When read-only dashboard routes are inspected, Then none are missing."""
    client = _client(monkeypatch, tmp_path)

    route_paths = {getattr(route, "path", "") for route in client.app.routes}
    openapi_paths = set(client.get("/openapi.json").json()["paths"])

    for route in READ_ONLY_ROUTE_PROBES:
        assert route in route_paths
        assert route in openapi_paths


def test_dashboard_frontend_route_strings_match_backend_contract() -> None:
    """Given frontend callers, When route strings are scanned, Then they match backend routes."""
    for route, owner in FRONTEND_ROUTE_OWNERS.items():
        source = (FRONTEND / owner).read_text(encoding="utf-8")
        assert route in source


def test_dashboard_frontend_called_read_only_routes_do_not_404(monkeypatch, tmp_path: Path) -> None:
    """Given a fresh app, When frontend-called routes are probed, Then they do not return 404."""
    client = _client(monkeypatch, tmp_path)

    for route, params in READ_ONLY_ROUTE_PROBES.items():
        response = client.get(route, params=params)
        assert response.status_code != 404
