from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from ai_strategy_loop.controller import state as state_module
from ai_strategy_loop.dashboard.app import create_app
from ai_strategy_loop.dashboard.security import DashboardSecurity, SESSION_COOKIE_NAME


ORIGIN = "http://127.0.0.1:8770"
ORIGIN_HEADER = {"Origin": ORIGIN}
WS_PATHS = ("/ws", "/bt/ws_job?job_id=missing", "/sim/ws")


def _client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    security: DashboardSecurity | None = None,
) -> TestClient:
    monkeypatch.setattr(state_module, "CURRENT_STATE_FILE", tmp_path / "current_state.json")
    monkeypatch.setattr(state_module, "STOP_FLAG_FILE", tmp_path / "STOP")
    for name in (
        "STOM_DASHBOARD_ALLOW_STRATEGY_WRITE",
        "STOM_DASHBOARD_ALLOW_DECISION_WRITE",
        "STOM_DASHBOARD_ALLOW_PROVIDER_TEST",
        "STOM_DASHBOARD_ALLOW_FINAL_APPROVAL",
    ):
        monkeypatch.delenv(name, raising=False)
    return TestClient(
        create_app(security_boundary=security),
        base_url=ORIGIN,
    )


def _bootstrap(client: TestClient) -> str:
    response = client.get("/ui/v4/", headers=ORIGIN_HEADER)
    assert response.status_code == 200
    token = client.cookies.get(SESSION_COOKIE_NAME)
    assert token
    return token


def _ws_url(path: str) -> str:
    return f"ws://127.0.0.1:8770{path}"


def test_public_reads_never_issue_session_cookie(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)

    health = client.get("/health", headers=ORIGIN_HEADER)
    status = client.get("/status")

    assert health.status_code == 200
    assert status.status_code == 200
    assert health.headers.get("set-cookie") is None
    assert status.headers.get("set-cookie") is None
    assert client.cookies.get(SESSION_COOKIE_NAME) is None
def test_health_exposes_bounded_dashboard_process_identity_without_bootstrap(monkeypatch, tmp_path: Path) -> None:
    """Health is public and read-only while exposing enough identity to detect stale backends."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/health", headers=ORIGIN_HEADER)
    dashboard = response.json()["dashboard"]
    shell = dashboard["shell"]
    backend = dashboard["backend"]

    assert response.status_code == 200
    assert response.headers.get("set-cookie") is None
    assert shell["name"] == "v4-ops"
    assert shell["release"] == "v5.11.0"
    assert dashboard["release"] == shell["release"] == backend["release"]
    assert dashboard["build"] == shell["build"] == backend["build"]
    assert 1 <= len(shell["build"]) <= 64
    assert "/" not in shell["build"] and "\\" not in shell["build"]
    assert isinstance(backend["process"]["pid"], int) and backend["process"]["pid"] > 0
    assert isinstance(backend["process"]["started_at_unix"], int)
    assert client.cookies.get(SESSION_COOKIE_NAME) is None



def test_session_bound_debug_logs_are_not_cacheable(monkeypatch, tmp_path: Path) -> None:
    client = _client(monkeypatch, tmp_path)
    _bootstrap(client)

    response = client.get("/debug/logs", headers=ORIGIN_HEADER)

    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-store, private"



@pytest.mark.parametrize("path", ["/ui/v4", "/ui/v4/"])
def test_exact_v4_bootstrap_issues_bounded_strict_cookie(
    monkeypatch,
    tmp_path: Path,
    path: str,
) -> None:
    client = _client(monkeypatch, tmp_path)

    # v5.11.2: /ui/v4 는 정본 루트(/)로 통합돼 307 을 낸다. 세션은 그 첫 응답에서 발급되므로
    #   쿠키 속성은 리다이렉트를 따라가기 전 응답에서 확인한다(계약은 그대로).
    first = client.get(path, headers=ORIGIN_HEADER, follow_redirects=False)
    cookie = first.headers.get("set-cookie", "").lower()
    assert first.status_code in (200, 307)
    assert f"{SESSION_COOKIE_NAME}=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/" in cookie
    max_age = int(cookie.split("max-age=")[1].split(";")[0])
    assert 1 <= max_age <= 3600

    followed = client.get(path, headers=ORIGIN_HEADER)
    assert followed.status_code == 200
    assert client.cookies.get(SESSION_COOKIE_NAME)


@pytest.mark.parametrize("path", ["/ui/v4", "/ui/v4/"])
def test_top_level_v4_navigation_without_origin_issues_session_cookie(
    monkeypatch,
    tmp_path: Path,
    path: str,
) -> None:
    client = _client(monkeypatch, tmp_path)

    response = client.get(path)

    assert response.status_code == 200
    assert client.cookies.get(SESSION_COOKIE_NAME)


@pytest.mark.parametrize(
    "path",
    [
        "/ui/",
        "/ui/evolution",
        "/ui/evolution/records",
        "/ui/evolution/catalog",
        "/ui/evolution/workbench",
        "/ui/backtest",
        "/ui/chart-replay",
    ],
)
def test_canonical_v4_shell_paths_bootstrap_session_cookie(
    monkeypatch,
    tmp_path: Path,
    path: str,
) -> None:
    """V4 graph-first 승격 정본 경로도 세션을 발급해야 /ws 4401 무한 거부가 없다(UXR-P2)."""
    client = _client(monkeypatch, tmp_path)

    # 정본 루트로 통합된 경로(/ui/)는 307, 딥링크는 200 — 어느 쪽이든 첫 응답이 세션을 발급한다.
    first = client.get(path, headers=ORIGIN_HEADER, follow_redirects=False)
    assert first.status_code in (200, 307)
    cookie = first.headers.get("set-cookie", "").lower()
    assert f"{SESSION_COOKIE_NAME}=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie

    response = client.get(path, headers=ORIGIN_HEADER)
    assert response.status_code == 200
    assert client.cookies.get(SESSION_COOKIE_NAME)


def test_unknown_evolution_subtab_does_not_issue_cookie(monkeypatch, tmp_path: Path) -> None:
    """미지 하위탭은 404 — 부트스트랩 접두 매칭이어도 4xx 응답엔 세션을 발급하지 않는다."""
    client = _client(monkeypatch, tmp_path)

    response = client.get("/ui/evolution/garbage", headers=ORIGIN_HEADER, follow_redirects=False)

    assert response.status_code == 404
    assert response.headers.get("set-cookie") is None
    assert client.cookies.get(SESSION_COOKIE_NAME) is None


def test_v4_bootstrap_rejects_foreign_origin_and_non_loopback_host(
    monkeypatch,
    tmp_path: Path,
) -> None:
    loopback_client = _client(monkeypatch, tmp_path)
    foreign_origin = loopback_client.get(
        "/ui/v4/",
        headers={"Origin": "https://attacker.invalid"},
    )
    non_loopback_client = TestClient(
        create_app(),
        base_url="http://dashboard.invalid",
    )

    non_loopback = non_loopback_client.get("/ui/v4/")

    assert foreign_origin.headers.get("set-cookie") is None
    assert non_loopback.headers.get("set-cookie") is None


def test_mutation_failure_precedence_is_origin_session_capability(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)

    no_origin = client.post("/gpt_auth/test")
    no_session = client.post("/gpt_auth/test", headers=ORIGIN_HEADER)
    _bootstrap(client)
    disabled = client.post("/gpt_auth/test", headers=ORIGIN_HEADER)
    foreign = client.post(
        "/gpt_auth/test",
        headers={"Origin": "https://attacker.invalid"},
    )

    assert (no_origin.status_code, no_origin.json()["code"]) == (403, "origin_required")
    assert (no_session.status_code, no_session.json()["code"]) == (401, "session_required")
    assert (disabled.status_code, disabled.json()["code"]) == (403, "capability_disabled")
    assert (foreign.status_code, foreign.json()["code"]) == (403, "origin_mismatch")


def test_session_is_invalid_after_process_boundary(monkeypatch, tmp_path: Path) -> None:
    first = _client(monkeypatch, tmp_path)
    stale_token = _bootstrap(first)
    second = _client(monkeypatch, tmp_path)

    response = second.post(
        "/bt/job/cancel",
        headers={**ORIGIN_HEADER, "Cookie": f"{SESSION_COOKIE_NAME}={stale_token}"},
        json={"job_id": "missing"},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "session_required"


def test_expired_session_rotates_and_is_rejected(monkeypatch, tmp_path: Path) -> None:
    now = [1000.0]
    security = DashboardSecurity(now=lambda: now[0], session_ttl_seconds=60)
    client = _client(monkeypatch, tmp_path, security=security)
    expired_token = _bootstrap(client)
    now[0] += 61

    response = client.post(
        "/bt/job/cancel",
        headers=ORIGIN_HEADER,
        json={"job_id": "missing"},
    )
    fresh_token = _bootstrap(client)

    assert response.status_code == 401
    assert response.json()["code"] == "session_required"
    assert fresh_token != expired_token


@pytest.mark.parametrize("path", WS_PATHS)
def test_all_control_websockets_reject_missing_session(
    monkeypatch,
    tmp_path: Path,
    path: str,
) -> None:
    client = _client(monkeypatch, tmp_path)

    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect(_ws_url(path), headers=ORIGIN_HEADER) as websocket:
            websocket.receive_text()

    assert caught.value.code == 4401


@pytest.mark.parametrize("path", WS_PATHS)
def test_all_control_websockets_reject_foreign_origin(
    monkeypatch,
    tmp_path: Path,
    path: str,
) -> None:
    client = _client(monkeypatch, tmp_path)
    _bootstrap(client)

    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect(
            _ws_url(path),
            headers={"Origin": "https://attacker.invalid"},
        ) as websocket:
            websocket.receive_text()

    assert caught.value.code == 4403


def test_authenticated_dashboard_websocket_rejects_unknown_action(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)
    _bootstrap(client)

    with client.websocket_connect(_ws_url("/ws"), headers=ORIGIN_HEADER) as websocket:
        assert websocket.receive_json()["status"] == "idle"
        websocket.send_json({"action": "unknown"})
        frame = websocket.receive_json()

    assert frame["status"] == "error"
    assert frame["code"] == "invalid_message"


def test_authenticated_backtest_and_replay_websockets_remain_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    client = _client(monkeypatch, tmp_path)
    _bootstrap(client)

    with client.websocket_connect(
        _ws_url("/bt/ws_job?job_id=missing"),
        headers=ORIGIN_HEADER,
    ) as websocket:
        backtest_frame = websocket.receive_json()
    with client.websocket_connect(_ws_url("/sim/ws"), headers=ORIGIN_HEADER) as websocket:
        websocket.send_json({"action": "stop"})
        replay_frame = websocket.receive_json()

    assert backtest_frame["job_id"] == "missing"
    assert "error" in backtest_frame
    assert replay_frame == {"type": "done"}


@pytest.mark.parametrize(
    "config",
    [
        {"unknown_loop_setting": 1},
        {"tpi_gate_enabled": "true"},
    ],
)
def test_start_control_rejects_inner_config_extra_or_coercion(
    monkeypatch,
    tmp_path: Path,
    config: dict[str, object],
) -> None:
    client = _client(monkeypatch, tmp_path)
    _bootstrap(client)
    starts: list[dict[str, object]] = []
    manager = getattr(client.app, "state").loop_manager
    monkeypatch.setattr(
        manager,
        "start",
        lambda value: starts.append(value) or {"status": "ok"},
    )

    with client.websocket_connect(_ws_url("/ws"), headers=ORIGIN_HEADER) as websocket:
        websocket.receive_json()
        websocket.send_json({"action": "start", "config": config})
        frame = websocket.receive_json()

    assert frame["status"] == "error"
    assert frame["code"] == "invalid_message"
    assert starts == []
