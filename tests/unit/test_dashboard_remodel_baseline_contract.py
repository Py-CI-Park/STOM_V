from __future__ import annotations

from pathlib import Path

from tests.unit.security_test_client import authorized_dashboard_client


REPO = Path(__file__).resolve().parents[2]
FRONTEND = REPO / "ai_strategy_loop" / "dashboard" / "frontend"
REMODEL = FRONTEND / "remodel"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_canonical_dashboard_routes_keep_v2_default_and_explicit_v3_selector() -> None:
    from ai_strategy_loop.dashboard.app import create_app

    client = authorized_dashboard_client(create_app())
    for path in ["/ui/", "/ui/evolution", "/ui/evolution/process", "/ui/backtest", "/ui/chart-replay"]:
        response = client.get(path, follow_redirects=False)
        assert response.status_code == 200, path
        assert "STOM AI · 조건식 자율 진화 대시보드" in response.text
        assert "/ui/bundle/app.js" in response.text
        assert "/ui/remodel/src/app.js" not in response.text
        assert response.headers["x-stom-dashboard-version"] == "v2"

        v3 = client.get(path, params={"dashboard_version": "v3"}, follow_redirects=False)
        assert v3.status_code == 200, path
        assert "STOM AI · 조건식 AI 연구 대시보드" in v3.text
        assert "/ui/remodel/src/app.js?v=20260628canonical" in v3.text
        assert "/ui/bundle/app.js" not in v3.text
        assert v3.headers["x-stom-dashboard-version"] == "v3-remodel"



def test_v2_default_bundle_exposes_nonpersistent_v3_preview_link() -> None:
    source = _text(FRONTEND / "app.jsx")
    bundle = _text(FRONTEND / "bundle" / "app.js")

    for blob in [source, bundle]:
        assert 'data-dashboard-preview="v3"' in blob or '"data-dashboard-preview": "v3"' in blob
        assert "dashboard_version=v3" in blob
        assert "V3 Preview" in blob

    assert "stom_dashboard_version" not in source
    assert "stom_dashboard_version" not in bundle
    assert "localStorage.setItem(\"dashboard_version" not in bundle
    assert "sessionStorage.setItem(\"dashboard_version" not in bundle


def test_remodel_zip_prototype_root_and_deeplinks_are_scoped() -> None:
    from ai_strategy_loop.dashboard.app import create_app

    client = authorized_dashboard_client(create_app())
    response = client.get("/ui/remodel/")
    assert response.status_code == 200
    assert "STOM AI · 조건식 AI 연구 대시보드" in response.text
    assert response.headers["x-stom-dashboard-version"] == "v3-remodel"
    assert "/ui/remodel/styles/theme.css?v=20260628canonical" in response.text
    assert "/ui/remodel/src/data.js?v=20260628canonical" in response.text
    assert "/ui/remodel/src/app.js?v=20260628canonical" in response.text
    assert "/ui/bundle/app.js" not in response.text
    assert 'rel="icon"' in response.text

    for path in [
        "/ui/remodel/condition",
        "/ui/remodel/process",
        "/ui/remodel/history",
        "/ui/remodel/lab",
        "/ui/remodel/workbench",
        "/ui/remodel/audit",
        "/ui/remodel/backtest",
        "/ui/remodel/chart-replay",
        "/ui/remodel/settings",
    ]:
        deep = client.get(path, follow_redirects=False)
        assert deep.status_code == 200, path
        assert "/ui/remodel/src/app.js?v=20260628canonical" in deep.text

    missing = client.get("/ui/remodel/not-a-real-dashboard-route", follow_redirects=False)
    assert missing.status_code == 404

    app_js = client.get("/ui/remodel/src/app.js")
    assert app_js.status_code == 200
    assert "routeToState" in app_js.text
    assert "connectStateSocket" in app_js.text

def test_production_backtest_and_replay_contract_sources_exist_for_parity_work() -> None:
    required = [
        FRONTEND / "bt-tab-root.jsx",
        FRONTEND / "bt-tab-run.jsx",
        FRONTEND / "bt-tab-library.jsx",
        FRONTEND / "bt-tab-analysis.jsx",
        FRONTEND / "sim-tab-root.jsx",
        FRONTEND / "sim-tab-controls.jsx",
        FRONTEND / "sim-chart-engines.jsx",
        FRONTEND / "sim-live-chart.jsx",
        REPO / "ai_strategy_loop" / "dashboard" / "backtest_api.py",
        REPO / "ai_strategy_loop" / "dashboard" / "simulation_api.py",
    ]
    for path in required:
        assert path.is_file(), str(path.relative_to(REPO))

    backtest_api = _text(REPO / "ai_strategy_loop" / "dashboard" / "backtest_api.py")
    for marker in [
        '@backtest_router.get("/health")',
        '@backtest_router.post("/run")',
        '@backtest_router.get("/result")',
        '@backtest_router.websocket("/ws_job")',
    ]:
        assert marker in backtest_api

    simulation_api = _text(REPO / "ai_strategy_loop" / "dashboard" / "simulation_api.py")
    for marker in [
        '@simulation_router.get("/health")',
        '@simulation_router.get("/days")',
        '@simulation_router.get("/signals")',
        '@simulation_router.websocket("/ws")',
    ]:
        assert marker in simulation_api


def test_remodel_forbidden_action_guards_cover_source_and_dom_terms() -> None:
    source_blobs = [
        _text(REMODEL / "index.html"),
        _text(REMODEL / "remodel-bootstrap.js"),
        _text(REMODEL / "src" / "app.js"),
        _text(REMODEL / "src" / "data.js"),
    ]
    combined = "\n".join(source_blobs)

    forbidden_action_markers = [
        'data-action="live-order"',
        'data-action="broker-login"',
        'data-action="account-trade"',
        'data-action="account-balance"',
        "automatic production export",
        "자동 프로덕션 Export",
        "final_approval",
    ]
    for marker in forbidden_action_markers:
        assert marker not in combined

    required_safety_cues = [
        "실거래/주문 기능 없음",
        "브로커 로그인 없음",
        "계좌/자산 연동 없음",
        "Human Approval Gate",
        "Append-Only Audit",
    ]
    for cue in required_safety_cues:
        assert cue in combined


def test_remodel_uses_reviewed_zip_renderer_not_production_bundle() -> None:
    index = _text(REMODEL / "index.html")
    app = _text(REMODEL / "src" / "app.js")

    assert "/ui/remodel/src/data.js?v=20260628canonical" in index
    assert "/ui/remodel/src/app.js?v=20260628canonical" in index
    assert "/ui/bundle/app.js" not in index
    assert "/ui/bundle/stom-ui.js" not in index
    assert "STOM_REMODEL_MODE" not in index
    assert "routeToState" in app
    assert "mapLoopState" in app
