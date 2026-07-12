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
from tests.unit.security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402

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
    return authorized_dashboard_client(create_app())


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

def test_dashboard_ui_deep_links_preserve_v2_default_and_explicit_v3_selector(monkeypatch, tmp_path: Path) -> None:
    """Given canonical dashboard routes, Then V2 remains default and V3 is explicit."""
    client = _client(monkeypatch, tmp_path)

    for route, status_code in UI_DEEP_LINKS.items():
        response = client.get(route)
        assert response.status_code == status_code
        assert "STOM AI · 조건식 자율 진화 대시보드" in response.text
        assert 'src="/ui/bundle/app.js' in response.text
        assert 'src="/ui/remodel/src/app.js' not in response.text
        assert response.headers["x-stom-dashboard-version"] == "v2"

        v3 = client.get(route, params={"dashboard_version": "v3"})
        assert v3.status_code == status_code
        assert "STOM AI · 조건식 AI 연구 대시보드" in v3.text
        assert 'href="/ui/remodel/styles/theme.css' in v3.text
        assert 'src="/ui/remodel/src/data.js' in v3.text
        assert 'src="/ui/remodel/src/app.js' in v3.text
        assert 'src="/ui/bundle/app.js' not in v3.text
        assert v3.headers["x-stom-dashboard-version"] == "v3-remodel"

    missing = client.get("/ui/not-a-real-dashboard-route.js")
    assert missing.status_code == 404

    missing_remodel = client.get("/ui/remodel/not-a-real-dashboard-route")
    assert missing_remodel.status_code == 404

    for remodel_route in [
        "/ui/remodel/condition",
        "/ui/remodel/process",
        "/ui/remodel/history",
        "/ui/remodel/lab",
        "/ui/remodel/workbench",
        "/ui/remodel/audit",
        "/ui/remodel/backtest",
        "/ui/remodel/chart-replay",
    ]:
        remodel = client.get(f"{remodel_route}?demo=reference")
        assert remodel.status_code == 200
        assert remodel.headers["x-stom-dashboard-version"] == "v3-remodel"
        assert 'src="/ui/remodel/src/app.js' in remodel.text

    for asset_route in [
        "/ui/remodel/src/app.js",
        "/ui/remodel/src/data.js",
        "/ui/remodel/styles/theme.css",
    ]:
        asset = client.get(asset_route)
        assert asset.status_code == 200


def test_dashboard_legacy_ui_aliases_redirect_to_evolution_subtabs(monkeypatch, tmp_path: Path) -> None:
    """Given old route keys, Then they canonicalize to Evolution nested subtab URLs."""
    client = _client(monkeypatch, tmp_path)

    for route, target in UI_LEGACY_ALIASES.items():
        response = client.get(route, follow_redirects=False)
        assert response.status_code in {307, 308}
        assert response.headers["location"] == target

        selected = client.get(f"{route}?dashboard_version=v3", follow_redirects=False)
        assert selected.status_code in {307, 308}
        assert selected.headers["location"] == f"{target}?dashboard_version=v3"


def test_dashboard_ui_v4_no_slash_redirect_preserves_query(monkeypatch, tmp_path: Path) -> None:
    """Given /ui/v4?base=... (no trailing slash), Then the redirect to /ui/v4/ keeps the query.

    Regression: the no-slash V4 route once hardcoded '/ui/v4/' and dropped the query, so a
    cross-origin data link (?base=http://127.0.0.1:8791) silently reverted to the local backend
    and the RUN archive selector rendered empty (사용자 신고 2026-07-05)."""
    client = _client(monkeypatch, tmp_path)
    r = client.get("/ui/v4?base=http://127.0.0.1:8791&tab=research", follow_redirects=False)
    assert r.status_code in {307, 308}
    assert r.headers["location"] == "/ui/v4/?base=http://127.0.0.1:8791&tab=research"
    bare = client.get("/ui/v4", follow_redirects=False)
    assert bare.status_code in {307, 308}
    assert bare.headers["location"] == "/ui/v4/"
