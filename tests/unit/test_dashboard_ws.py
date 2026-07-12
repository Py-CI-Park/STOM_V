"""US-007 — 대시보드 WebSocket/REST 단위 테스트 (네트워크/실루프 없음).

검증:
  - GET /health → ok + contract_version.
  - GET /config/spec → 필드 명세.
  - WS /ws 연결 시 현재 LoopState 프레임 수신 (fake current_state.json).
  - stop 제어 메시지 → STOP 플래그 파일이 써진다(루프 관측 가능).
  - start 제어 → 서브프로세스 기동은 STUB (실제 gpt_auth 루프 미기동).
"""

import json
import os
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from .security_test_client import authorized_dashboard_client  # pyright: ignore[reportMissingImports]  # noqa: E402


@pytest.fixture
def isolated_state(monkeypatch, tmp_path):
    """current_state.json / STOP 플래그를 tmp로 격리한다 (운영 파일 미접촉)."""
    cur = tmp_path / "current_state.json"
    stop = tmp_path / "STOP"
    monkeypatch.setattr(S, "CURRENT_STATE_FILE", cur)
    monkeypatch.setattr(S, "STOP_FLAG_FILE", stop)
    return {"current": cur, "stop": stop}


@pytest.fixture
def client(isolated_state, monkeypatch):
    """대시보드 TestClient. create_app으로 새 앱을 만들어 매니저를 격리한다."""
    from fastapi.testclient import TestClient

    from ai_strategy_loop.dashboard.app import create_app

    monkeypatch.setenv("STOM_DASHBOARD_ALLOW_PROVIDER_TEST", "1")
    app = create_app()
    return authorized_dashboard_client(app)


class TestHealthAndSpec:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["contract_version"] == C.CONTRACT_VERSION

    def test_favicon_returns_svg(self, client):
        resp = client.get("/favicon.ico")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("image/svg+xml")
        assert "<svg" in resp.text

    def test_config_spec_returns_fields(self, client):
        resp = client.get("/config/spec")
        assert resp.status_code == 200
        body = resp.json()
        assert "fields" in body
        names = {f["name"] for f in body["fields"]}
        assert "provider" in names
        assert "max_generations" in names
    def test_gpt_auth_test_reports_safe_probe_without_start(self, client, monkeypatch):
        import requests

        class FakeResponse:
            status_code = 200

        called = {}

        def fake_post(url, **kwargs):
            called["url"] = url
            called["kwargs"] = kwargs
            return FakeResponse()

        monkeypatch.setattr(requests, "post", fake_post)
        resp = client.post("/gpt_auth/test")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["model"] == "gpt-5.5"
        assert body["reasoning_effort"] == "xhigh"
        assert body["safe"] is True
        assert body["starts_evolution"] is False
        assert "/chat/completions" in called["url"]
        assert called["kwargs"]["json"]["model"] == "gpt-5.5"

    def test_status_idle_when_no_state_file(self, client):
        resp = client.get("/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "idle"
        assert body["contract_version"] == C.CONTRACT_VERSION


class TestWebSocketState:
    def test_ws_sends_current_state_on_connect(self, client, isolated_state):
        # fake current_state.json 작성 (running LoopState).
        ls = C.LoopState(
            run_id="run_ws_test", status="running", current_gen=1,
            max_generations=5, provider="openrouter", bt_timeframe="min",
        )
        S.publish_loop_state(ls, path=str(isolated_state["current"]))
        assert isolated_state["current"].exists()

        with client.websocket_connect("/ws") as ws:
            frame = ws.receive_json()
            assert frame["contract_version"] == C.CONTRACT_VERSION
            assert frame["run_id"] == "run_ws_test"
            assert frame["status"] == "running"
            assert frame["current_gen"] == 1

    def test_ws_sends_idle_when_no_state(self, client):
        with client.websocket_connect("/ws") as ws:
            frame = ws.receive_json()
            assert frame["status"] == "idle"
            assert frame["contract_version"] == C.CONTRACT_VERSION


class TestStopControl:
    def test_stop_message_writes_stop_flag(self, client, isolated_state):
        assert not isolated_state["stop"].exists()
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 연결 프레임 소비.
            ws.send_text(json.dumps({"action": "stop"}))
            reply = ws.receive_json()
            assert reply["action"] == "stop"
            assert reply["status"] == "ok"
        # STOP 플래그가 루프가 관측 가능한 위치에 써졌다.
        assert isolated_state["stop"].exists()
        assert S.stop_requested(path=str(isolated_state["stop"])) is True


class TestStartControlStubbed:
    def test_start_message_launches_subprocess_stub(self, client, monkeypatch):
        """start 제어가 서브프로세스 기동을 호출하되, 실제 루프는 띄우지 않는다."""
        import ai_strategy_loop.dashboard.app as appmod

        launched = {}

        class FakePopen:
            def __init__(self, cmd, **kw):
                launched["cmd"] = cmd
                launched["kw"] = kw
                self.pid = 4242

            def poll(self):
                return None  # running

        monkeypatch.setattr(appmod.subprocess, "Popen", FakePopen)

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 연결 프레임.
            ws.send_text(json.dumps({
                "action": "start",
                "config": {"provider": "openrouter", "max_generations": 3},
            }))
            reply = ws.receive_json()
            assert reply["action"] == "start"
            assert reply["status"] == "ok"
            assert reply["pid"] == 4242

        # 실제 gpt_auth 루프가 아니라 stub Popen이 루프 모듈을 겨냥했는지 확인.
        assert launched["cmd"][1] == "-m"
        assert launched["cmd"][2] == "ai_strategy_loop.controller.loop"
        assert "--config-json" in launched["cmd"]

    def test_start_rejects_invalid_config(self, client, monkeypatch):
        import ai_strategy_loop.dashboard.app as appmod

        # Popen이 호출되면 안 됨 — 잘못된 config는 검증에서 막힌다.
        def _boom(*a, **k):
            raise AssertionError("Popen should not be called for invalid config")

        monkeypatch.setattr(appmod.subprocess, "Popen", _boom)

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({
                "action": "start",
                "config": {"provider": "bogus_provider"},
            }))
            reply = ws.receive_json()
            assert reply["status"] == "error"
            assert "invalid config" in reply["message"]


class TestStaticFrontendServing:
    """US-007 — 프론트엔드를 같은 origin(/ui/)에서 서빙하고, /는 거기로 리다이렉트."""

    def test_root_redirects_to_ui(self, client):
        # 리다이렉트를 따라가지 않고 3xx + Location 헤더를 직접 검증한다.
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code in (302, 307)
        assert resp.headers["location"] == "/ui/"

    def test_ui_serves_dashboard_html(self, client):
        resp = client.get("/ui/")
        assert resp.status_code == 200
        body = resp.text
        # index.html(= 대시보드 HTML)이 서빙되는지 핵심 마커로 확인.
        #   Phase14.4: 운영 컴포넌트는 단일 컴파일 번들 bundle/app.js(+stom-ui.js)로 로드(런타임 babel 제거).
        assert '<div id="root">' in body
        assert "bundle/app.js" in body
        assert "bundle/stom-ui.js" in body

    def test_ui_serves_static_assets(self, client):
        # 상대 경로로 로드되는 정적 자산이 /ui 하위에서 해석되는지 확인.
        css = client.get("/ui/styles.css")
        assert css.status_code == 200
        jsx = client.get("/ui/connection.jsx")
        assert jsx.status_code == 200
        assert "DEFAULT_BASE" in jsx.text

    def test_frontend_dir_and_index_exist(self):
        # StaticFiles(html=True)가 /ui/ 에서 서빙하려면 디렉토리 + index.html 필요.
        import ai_strategy_loop.dashboard.app as appmod

        assert os.path.isdir(appmod._FRONTEND_DIR)
        assert os.path.isfile(os.path.join(appmod._FRONTEND_DIR, "index.html"))


class TestUnknownControl:
    def test_unknown_action_returns_error(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_text(json.dumps({"action": "frobnicate"}))
            reply = ws.receive_json()
            assert reply["status"] == "error"
            assert reply["code"] == "invalid_message"


class TestHardStopReapsChild:
    """HIGH-2: 매니저 hard_stop이 살아있는 자식을 terminate+reap 한다(오펀 방지)."""

    def test_hard_stop_terminates_and_reaps_long_lived_child(self):
        import subprocess as _sp
        import sys as _sys

        from ai_strategy_loop.dashboard.app import LoopProcessManager

        mgr = LoopProcessManager()
        # 실제 루프가 아닌 더미 장수 프로세스(60초 sleep)를 직접 주입한다.
        proc = _sp.Popen([_sys.executable, "-c", "import time; time.sleep(60)"])
        mgr._proc = proc
        assert mgr.is_running() is True

        reaped = mgr.hard_stop(grace=10.0)
        assert reaped is True
        # grace 윈도우 안에 회수되어 poll()이 non-None을 돌려준다.
        assert proc.poll() is not None
        assert mgr.is_running() is False

    def test_hard_stop_noop_when_no_child(self):
        from ai_strategy_loop.dashboard.app import LoopProcessManager

        mgr = LoopProcessManager()
        assert mgr.hard_stop() is False


class TestFinalApprovalDestIsServerControlled:
    """HIGH-3: final_approval은 클라이언트 dest_strategy_db를 무시하고 운영 경로로만 export."""

    def test_legacy_client_winner_and_dest_fields_are_rejected(self, client, monkeypatch):
        captured = {}

        def _fake_export(winner_buy, winner_sell, dest, user_buy, user_sell, **kw):
            captured["dest"] = dest
            return {"status": "ok", "dest_db": dest}

        # export 모듈의 export_winner를 가로채 호출 인자를 캡처한다.
        import ai_strategy_loop.controller.export as exportmod
        monkeypatch.setattr(exportmod, "export_winner", _fake_export)

        with client.websocket_connect("/ws") as ws:
            ws.receive_json()  # 연결 프레임.
            ws.send_text(json.dumps({
                "action": "final_approval",
                "buy_name": "AILOOP_run_x_g2_buy",
                "sell_name": "AILOOP_run_x_g2_sell",
                "user_buy": "내전략_buy",
                "user_sell": "내전략_sell",
                "dest_strategy_db": "C:/evil/attacker.db",  # 악의적 목적지.
            }))
            reply = ws.receive_json()
            assert reply["status"] == "error"
            assert reply["code"] == "invalid_message"

        # 클라이언트가 준 악성 경로가 아니라 운영 상수 경로로 export 되어야 한다.
        assert captured == {}
