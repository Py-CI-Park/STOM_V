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
from fastapi.responses import RedirectResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from ai_strategy_loop.controller import contract as C  # noqa: E402
from ai_strategy_loop.controller import state as S  # noqa: E402
from ai_strategy_loop.launch_config import config_field_specs, config_from_dict  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 프론트엔드(Claude Design 산출물) 정적 자산 디렉토리. 모듈 위치 기준 절대 경로로
#   해석해 CWD와 무관하게 동작한다. 이 디렉토리를 /ui 하위에 마운트해 같은 origin에서
#   서빙한다(REST/WS API와 동일 출처 → CORS 우회 + 단일 진입점).
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

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
        """루프를 서브프로세스로 기동한다. 이미 running이면 거부.

        P6 — 대시보드가 추적하는 자식(is_running)뿐 아니라, **cross-process 락**도
        확인한다. LoopProcessManager는 이 대시보드 인스턴스 한정 보호라, 다른
        진입점(CLI 또는 다른 대시보드 프로세스)이 이미 루프를 돌리는 경우를 못 본다.
        runlock.is_locked()로 그 경우까지 막아 같은 state/DB 동시 쓰기를 차단한다.
        실제 락 획득/해제는 자식 run_loop가 소유한다(여기선 사전 거부만).
        """
        if self.is_running():
            return {"status": "error", "message": "loop already running"}

        # cross-process 락: 살아있는 다른 루프(CLI/타 GUI)가 보유 중이면 거부.
        from ai_strategy_loop.controller.runlock import is_locked  # noqa: PLC0415

        if is_locked():
            return {
                "status": "error",
                "message": "다른 루프가 실행 중입니다(cross-process 락 보유). 동시 실행 차단.",
            }

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


def _runs_payload(run_ids: Optional[list]) -> Dict[str, Any]:
    """loop_runs.db를 열어 run 비교 요약을 만든다(읽기 전용, 무예외).

    lineage.compare_runs를 호출하고 LoopState 연결을 반드시 닫는다. DB 부재/조회
    실패는 빈 목록으로 표준화한다(대시보드 콘솔이 깨지지 않게).
    """
    from ai_strategy_loop.controller.lineage import compare_runs  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        result = compare_runs(st, run_ids)
        return result
    except Exception as exc:  # noqa: BLE001 - run 비교 조회 실패는 빈 목록으로.
        return {"runs": [], "count": 0, "error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass


def _equity_curves_payload(
    cap: int = 200, downsample: int = 200, run_id: Optional[str] = None
) -> Dict[str, Any]:
    """loop_runs.db의 세대 equity curve를 읽어 반환한다(읽기 전용, 무예외).

    run_id가 주어지면 그 run의 세대만 반환한다 — 전체 이력에는 과발화 폭망 곡선
    (±수십억)이 섞여 있어, 그것까지 한 차트에 그리면 정상 곡선이 y스케일에 압착돼
    0선에 한 줄처럼 뭉개진다. 현재 보고 있는 run만 보내면 스케일이 정상화된다.
    run_id 미지정이면 전체(하위호환).

    각 세대의 csv_path로 load_equity_series_from_csv를 호출해 수익금합계 시계열을
    얻는다. 곡선이 많으면 최근 cap 개로 제한하고, 곡선당 포인트는 downsample 개로
    줄인다. CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 응답(무예외).

    반환: {"curves": [{"run_id","gen_no","gate_passed","final_pct","equity":[...]}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.score import load_equity_series_from_csv  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"curves": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # created_at 내림차순(최신 우선).
    sorted_gens = sorted(all_gens, key=lambda g: g.get("created_at") or 0, reverse=True)
    # run_id가 주어지면 해당 run만(현재 보고 있는 run의 곡선만 정상 스케일로 표시).
    if run_id:
        sorted_gens = [g for g in sorted_gens if g.get("run_id") == run_id]
    candidates = sorted_gens[:cap]

    curves = []
    for g in candidates:
        csv_path = g.get("csv_path")
        if not csv_path:
            continue
        try:
            equity_raw = load_equity_series_from_csv(str(csv_path))
        except Exception:  # noqa: BLE001 - CSV 없거나 파싱 실패는 skip.
            continue
        if not equity_raw:
            continue
        # 다운샘플: 포인트 수가 downsample 초과면 균등 간격으로 추려 payload 축소.
        if len(equity_raw) > downsample:
            step = len(equity_raw) / downsample
            equity_ds = [equity_raw[int(i * step)] for i in range(downsample)]
            equity_ds.append(equity_raw[-1])  # 마지막 값 보존.
        else:
            equity_ds = equity_raw
        curves.append({
            "run_id": g.get("run_id", ""),
            "gen_no": int(g.get("gen_no", -1)),
            "gate_passed": bool(g.get("gate_passed")),
            "final_pct": float(g.get("total_profit_pct") or 0.0),
            "equity": [float(v) for v in equity_ds],
        })

    return {"curves": curves, "count": len(curves)}


def _strategy_code_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """루프 DB에서 한 세대의 매수/매도 전략 코드를 조회한다(읽기 전용, 무예외).

    P10 — 대시보드 코드 뷰어가 fetch 한다. 세대 행(generations)의 실제 buy_name/
    sell_name을 먼저 읽어(시드 세대는 seed 이름, 일반 세대는 AILOOP_<run>_g<gen>_*),
    그 이름으로 loop.py의 _read_strategy_code(stockbuy/stocksell의 "전략코드")를
    재사용해 코드를 가져온다. 행이 없으면 namespaced 기본 이름으로 폴백한다.

    조회 실패/미존재는 빈 문자열로 표준화한다(대시보드가 "코드가 없습니다"를 표시).
    """
    from ai_strategy_loop.controller.loop import _read_strategy_code  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    buy_name = f"AILOOP_{run_id}_g{gen_no}_buy"
    sell_name = f"AILOOP_{run_id}_g{gen_no}_sell"
    # 세대 행에서 실제 전략 이름을 읽는다(시드 세대는 seed 이름일 수 있음).
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                buy_name = row.get("buy_name") or buy_name
                sell_name = row.get("sell_name") or sell_name
                break
    except Exception:  # noqa: BLE001 - 행 조회 실패는 namespaced 기본 이름으로 폴백.
        pass
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    buy_code = _read_strategy_code(buy_name, "buy") or ""
    sell_code = _read_strategy_code(sell_name, "sell") or ""
    return {
        "run_id": run_id,
        "gen": int(gen_no),
        "buy_name": buy_name,
        "sell_name": sell_name,
        "buy_code": buy_code,
        "sell_code": sell_code,
    }


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

    @app.get("/")
    def root() -> RedirectResponse:
        # 단일 진입점: 루트로 들어오면 정적 대시보드(/ui/)로 보낸다.
        return RedirectResponse(url="/ui/")

    @app.get("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok", "contract_version": C.CONTRACT_VERSION}

    @app.get("/status")
    def status() -> Dict[str, Any]:
        return _current_state_payload()

    @app.get("/config/spec")
    def config_spec() -> Dict[str, Any]:
        return {"contract_version": C.CONTRACT_VERSION, "fields": config_field_specs()}

    @app.get("/equity_curves")
    def equity_curves(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 누적수익 시계열(equity curve)을 반환한다(읽기 전용, 무예외).

        run_id 주면 그 run의 세대만(현재 run 정상 스케일), 없으면 전체(하위호환).
        최근 200 세대까지 조회하며, 세대당 포인트는 최대 200개로 다운샘플한다.
        CSV 없거나 파싱 실패한 세대는 건너뛴다. DB 없으면 빈 배열(무예외).
        """
        return _equity_curves_payload(run_id=run_id)

    @app.get("/runs")
    def runs() -> Dict[str, Any]:
        """loop_runs.db의 모든 run 요약을 반환한다(run 비교 콘솔 목록).

        lineage.compare_runs(run_ids=None)로 전 run을 요약한다. DB가 없거나
        조회 실패면 빈 목록을 돌려 대시보드가 깨지지 않게 한다(무예외 계약).
        """
        return _runs_payload(None)

    @app.get("/runs/compare")
    def runs_compare(ids: str = "") -> Dict[str, Any]:
        """지정한 run id들을 지표/우승전략으로 비교한다(loop_runs.db 직접).

        ids는 쉼표로 구분한 run_id 목록(예: `?ids=run_a,run_b`). 비면 전체 run.
        """
        id_list = [s.strip() for s in ids.split(",") if s.strip()] or None
        return _runs_payload(id_list)

    @app.get("/strategy_code")
    def strategy_code(run: str = "", gen: int = -1) -> Dict[str, Any]:
        """한 세대의 매수/매도 전략 코드를 반환한다(코드 뷰어 fetch용).

        쿼리: ?run=<run_id>&gen=<n>. 루프 DB(STOM_CLI_DB_STRATEGY)의
        stockbuy/stocksell에서 그 세대의 코드를 조회해 {buy_code, sell_code}를
        돌려준다. run 미지정/조회 실패/없는 gen은 빈 코드 문자열로 표준화한다
        (무예외 — 대시보드가 "코드가 없습니다"를 표시).
        """
        if not run or gen < 0:
            return {
                "run_id": run, "gen": gen,
                "buy_name": "", "sell_name": "", "buy_code": "", "sell_code": "",
            }
        return _strategy_code_payload(run, gen)

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

    # 정적 프론트엔드 마운트는 모든 API 라우트(/health, /status, /config/spec, /ws, /)
    #   등록 이후에 한다. /ui 하위 경로에 마운트하므로 위 API 라우트와 WS를 가리지
    #   않는다(StaticFiles는 /ui/* 만 처리). html=True 로 /ui/ 가 index.html을 서빙.
    #   .jsx 는 StaticFiles 기본 content-type으로 서빙되며 브라우저 fetch+Babel 변환에
    #   문제 없다. 프론트엔드 디렉토리가 없으면 API만으로도 기동되도록 가드한다.
    if os.path.isdir(_FRONTEND_DIR):
        app.mount("/ui", StaticFiles(directory=_FRONTEND_DIR, html=True), name="ui")

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
