"""US-007 — AI strategy loop 대시보드 FastAPI 백엔드.

엔드포인트:
  - GET  /health       → {status, contract_version}
  - GET  /status       → 현재 LoopState (current_state.json 또는 idle 기본값)
  - GET  /config/spec  → config_field_specs (GUI 폼 렌더용)
  - WS   /ws           → 연결 시 현재 LoopState 송신 후 current_state.json
                         변경을 폴링(~1s)해 push. 인바운드 제어 메시지 수신:
                           {"action":"start","config":{...}}
                           {"action":"stop"}
                           {"action":"final_approval", ...}

제어 구현:
  - start          : 루프를 서브프로세스로 기동 (STOP 플래그 선제거).
  - stop           : STOP 플래그 파일을 쓴다 (루프가 세대 시작 전 관측).
  - final_approval : export_winner(...) 호출 (사람 승인 live-deploy 게이트).

CORS는 모두 허용 — Claude Design 프론트엔드가 별도 origin에서 서빙된다.

라이브 상태 seam은 controller/contract.py(LoopState) + controller/state.py
(publish/read/stop helpers)에 정의되어 있다.
"""

from __future__ import annotations

# bootstrap을 가장 먼저 — cli.*/utility.* import 전 env 격리 (export 경로용).
import ai_strategy_loop.bootstrap  # noqa: E402,F401

import asyncio  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from typing import Any, Dict, Optional  # noqa: E402

from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 폴링 주기(초) — current_state.json 변경 감지 → WS push.
_POLL_INTERVAL = 1.0

# 대시보드는 로컬 전용(서버는 127.0.0.1 바인드)이다. CORS를 와일드카드로 열면
#   임의 origin 페이지가 사용자의 로컬 대시보드 API를 호출할 수 있으므로
#   명시적 localhost allowlist로 제한한다(allow_credentials=False 유지).
_DASHBOARD_PORT = 8770
_ALLOWED_ORIGINS = [
    f"http://localhost:{_DASHBOARD_PORT}",
    f"http://127.0.0.1:{_DASHBOARD_PORT}",
    "http://localhost",
    "http://127.0.0.1",
]


class LoopProcessManager:
    """루프 서브프로세스 핸들을 in-process로 관리하는 단순 매니저.

    한 번에 하나의 루프만 추적한다(MVP). start는 STOP 플래그를 먼저 지우고
    `python -m ai_strategy_loop.controller.loop --config-json <...>` 를 띄운다.
    """

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """루프를 서브프로세스로 기동한다. 이미 running이면 거부."""
        if self.is_running():
            return {"status": "error", "message": "loop already running"}

        # 설정 검증 (CLI=GUI 동일 경로). 잘못된 값이면 여기서 막는다.
        try:
            cfg = config_from_dict(config_dict)
        except ValueError as exc:
            return {"status": "error", "message": f"invalid config: {exc}"}

        # 기동 전 잔여 STOP 플래그 제거 (즉시 정지 방지).
        S.clear_stop_flag()

        env = dict(os.environ)
        env.setdefault("STOM_ALLOW_MINIMAL_SETTING", "1")
        env["PYTHONUNBUFFERED"] = "1"

        cmd = [
            sys.executable, "-m", "ai_strategy_loop.controller.loop",
            "--config-json", json.dumps(cfg.to_dict(), ensure_ascii=False),
        ]
        self._proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env)
        return {"status": "ok", "pid": self._proc.pid}

    def stop(self, *, grace: float = 10.0) -> Dict[str, Any]:
        """STOP 플래그를 써서 깔끔한 종료를 요청하고, 안 멈추면 강제 종료한다.

        1) STOP 플래그를 쓴다(루프가 세대 시작 전 관측 → 깔끔히 종료).
        2) grace 동안 자식이 스스로 끝나길 기다린다.
        3) 여전히 살아 있으면 hard_stop()으로 terminate→kill→reap 해서
           오펀 백테스트를 남기지 않는다.
        """
        path = S.set_stop_flag()
        reaped = self.hard_stop(grace=grace)
        return {"status": "ok", "stop_flag": path, "reaped": reaped}

    def hard_stop(self, *, grace: float = 10.0) -> bool:
        """실행 중인 자식을 terminate→(grace 대기)→kill→wait 로 강제 회수한다.

        오펀 방지: 서버 종료/강제 정지 시 자식 백테스트가 남지 않도록 반드시
        wait()으로 좀비를 reap 한다. 추적 중인 자식이 없거나 이미 종료됐으면
        조용히 False를 반환한다(회수할 것 없음). 회수했으면 True.
        """
        proc = self._proc
        if proc is None:
            return False
        if proc.poll() is not None:
            self._proc = None
            return False
        try:
            proc.terminate()
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except OSError:
            # 이미 죽었거나 회수 불가 — 그래도 핸들은 비워 다음 start를 허용한다.
            pass
        self._proc = None
        return True


def _current_state_payload() -> Dict[str, Any]:
    """current_state.json을 읽어 dict로 반환 (없으면 idle 기본값)."""
    raw = S.read_current_state()
    if raw is not None:
        return raw
    return C.idle_state().model_dump()


def create_app() -> FastAPI:
    """대시보드 FastAPI 앱을 생성한다 (테스트가 TestClient로 감싼다)."""
    manager = LoopProcessManager()

    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        # 서버 수명 동안 매니저를 보유하고, 종료 시 추적 중인 루프 자식을
        #   강제 회수한다(오펀 백테스트 방지).
        yield
        manager.hard_stop()

    app = FastAPI(
        title="STOM AI Strategy Loop Dashboard", version="1.0", lifespan=_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.loop_manager = manager

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "contract_version": C.CONTRACT_VERSION}

    @app.get("/status")
    def status() -> Dict[str, Any]:
        return _current_state_payload()

    @app.get("/config/spec")
    def config_spec() -> Dict[str, Any]:
        return {"contract_version": C.CONTRACT_VERSION, "fields": config_field_specs()}

    @app.websocket("/ws")
    async def ws(websocket: WebSocket) -> None:
        await websocket.accept()
        # 연결 즉시 현재 상태 송신.
        last_sent = _current_state_payload()
        await websocket.send_json(last_sent)

        async def _pusher() -> None:
            """current_state.json 변경을 폴링해 변경 시에만 push."""
            nonlocal last_sent
            while True:
                await asyncio.sleep(_POLL_INTERVAL)
                payload = _current_state_payload()
                if payload != last_sent:
                    last_sent = payload
                    await websocket.send_json(payload)

        push_task = asyncio.create_task(_pusher())
        try:
            while True:
                # 인바운드 제어 메시지 수신.
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except (ValueError, TypeError):
                    await websocket.send_json({"status": "error", "message": "invalid JSON"})
                    continue
                result = _handle_control(msg, manager)
                await websocket.send_json(result)
        except WebSocketDisconnect:
            pass
        finally:
            push_task.cancel()

    return app


def _handle_control(msg: Dict[str, Any], manager: LoopProcessManager) -> Dict[str, Any]:
    """인바운드 제어 메시지를 처리한다 (start | stop | final_approval).

    제어 결과 dict를 반환한다(클라이언트로 에코). 어떤 예외도 흡수해 WS를
    끊지 않는다.
    """
    action = (msg or {}).get("action")
    try:
        if action == "start":
            return {"action": "start", **manager.start(msg.get("config") or {})}
        if action == "stop":
            return {"action": "stop", **manager.stop()}
        if action == "final_approval":
            return {"action": "final_approval", **_do_final_approval(msg)}
        return {"status": "error", "message": f"unknown action: {action!r}"}
    except Exception as exc:  # noqa: BLE001 - 제어 실패는 WS를 끊지 않는다.
        return {"status": "error", "action": action, "message": str(exc)}


def _do_final_approval(msg: Dict[str, Any]) -> Dict[str, Any]:
    """final_approval — 우승 전략을 운영 strategy.db로 export (사람 승인 게이트).

    필요 키: buy_name, sell_name (루프 DB 내 namespaced 우승 이름),
             user_buy, user_sell (운영 DB에 저장할 사람이 정한 이름).

    보안: export 목적지는 클라이언트가 고를 수 없다. 메시지에 dest_strategy_db가
    들어와도 무시하고 항상 export.PRODUCTION_STRATEGY_DB(결정론적 운영 경로)로만
    내보낸다(임의 경로 쓰기 방지).
    """
    from ai_strategy_loop.controller.export import (  # noqa: PLC0415
        PRODUCTION_STRATEGY_DB,
        export_winner,
    )

    buy_name = msg.get("buy_name")
    sell_name = msg.get("sell_name")
    user_buy = msg.get("user_buy")
    user_sell = msg.get("user_sell")
    if not (buy_name and sell_name and user_buy and user_sell):
        return {
            "status": "error",
            "message": "final_approval requires buy_name, sell_name, user_buy, user_sell",
        }
    # 클라이언트 제공 dest_strategy_db는 의도적으로 무시한다 — 항상 운영 경로.
    return export_winner(
        buy_name, sell_name, str(PRODUCTION_STRATEGY_DB), user_buy, user_sell,
    )


# 모듈 레벨 app — uvicorn `ai_strategy_loop.dashboard.app:app` 로도 띄울 수 있다.
app = create_app()
