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

UI_DEEP_LINKS = {
    "/ui/evolution": 200,
    "/ui/evolution/process": 200,
    "/ui/evolution/records": 200,
    "/ui/evolution/lab": 200,
    "/ui/evolution/workbench": 200,
    "/ui/evolution/verdict": 200,
    "/ui/backtest": 200,
    "/ui/chart-replay": 200,
}

UI_LEGACY_ALIASES = {
    "/ui/process": "/ui/evolution/process",
    "/ui/records": "/ui/evolution/records",
    "/ui/history": "/ui/evolution/records",
    "/ui/evolution/history": "/ui/evolution/records",
    "/ui/lab": "/ui/evolution/lab",
    "/ui/pro": "/ui/evolution/workbench",
    "/ui/verdict": "/ui/evolution/verdict",
    "/ui/simulation": "/ui/chart-replay",
}

FRONTEND_ROUTE_OWNERS = {
    "/strategy_diff": "strategy-inspector.jsx",
    "/prompts": "strategy-inspector.jsx",
    "/ai_context_pack": "ai-context.jsx",
    "/research_criteria": "panels-status.jsx",
    "/research_docs": "research-wiki.jsx",
    "/research_doc": "research-wiki.jsx",
    "/variable_correlation": "rl-panel.jsx",
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

def test_dashboard_ui_deep_links_serve_spa_without_broad_catchall(monkeypatch, tmp_path: Path) -> None:
    """Given explicit dashboard UI deep links, Then only named routes serve the SPA shell."""
    client = _client(monkeypatch, tmp_path)

    for route, status_code in UI_DEEP_LINKS.items():
        response = client.get(route)
        assert response.status_code == status_code
        assert "STOM AI" in response.text
        assert 'href="/ui/styles.css' in response.text
        assert 'src="/ui/vendor-react.js' in response.text
        assert 'src="/ui/bundle/app.js' in response.text
        assert 'src="bundle/app.js' not in response.text

    missing = client.get("/ui/not-a-real-dashboard-route.js")
    assert missing.status_code == 404


def test_dashboard_legacy_ui_aliases_redirect_to_evolution_subtabs(monkeypatch, tmp_path: Path) -> None:
    """Given old route keys, Then they canonicalize to Evolution nested subtab URLs."""
    client = _client(monkeypatch, tmp_path)

    for route, target in UI_LEGACY_ALIASES.items():
        response = client.get(route, follow_redirects=False)
        assert response.status_code in {307, 308}
        assert response.headers["location"] == target
