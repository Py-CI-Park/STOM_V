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


def _generation_durations_payload(run_id: Optional[str] = None) -> Dict[str, Any]:
    """세대별 소요초를 인접 created_at 차분으로 산출한다(#64, 읽기 전용·무예외).

    generations.created_at은 각 세대 *종료* 시각(record_generation 시 _now())이 영속된다.
    따라서 gen[i] 소요 = created_at[i] - created_at[i-1]. 첫 세대(i=0)는 이전 세대가 없으니
    runs.started_at(run 시작 시각)으로 보정해 created_at[0] - started_at를 쓴다. 이 방식은
    추가 백테 0회이고, LIVE 발행이 없던 과거 run(예: reframe1)에도 retroactive하게 작동한다
    (DB에 이미 created_at/started_at가 있으므로).

    run_id가 주어지면 그 run만, 없으면 모든 run을 산출한다. DB 부재/조회 실패/이상치는
    빈 목록·None으로 표준화한다(무예외 — 대시보드가 깨지지 않게). 음수 차(시계 역행/UPSERT
    재기록)는 None으로 둔다(잘못된 소요 표시 방지).

    반환: {"durations": [{"run_id","gen_no","duration_sec","created_at","status"}], "count": N}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
        runs = {r.get("run_id"): r for r in st.list_runs()}
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답.
        return {"durations": [], "count": 0}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # run별로 gen_no 순 그룹핑(인접 차분을 같은 run 안에서만 계산).
    by_run: Dict[str, list] = {}
    for g in all_gens:
        rid = g.get("run_id")
        if run_id and rid != run_id:
            continue
        by_run.setdefault(rid, []).append(g)

    durations: list = []
    for rid, gens in by_run.items():
        gens_sorted = sorted(gens, key=lambda g: int(g.get("gen_no", 0) or 0))
        started_at = (runs.get(rid) or {}).get("started_at")
        prev_created = float(started_at) if started_at is not None else None
        for g in gens_sorted:
            created = g.get("created_at")
            duration_sec: Optional[float] = None
            if created is not None and prev_created is not None:
                delta = float(created) - float(prev_created)
                # 음수(시계 역행/재기록)는 None으로 — 잘못된 소요 표시 방지.
                duration_sec = delta if delta >= 0.0 else None
            # gen_no는 0이 유효값이므로 `or -1`(0을 falsy로 떨구는 버그) 금지 — None만 -1.
            _gen_no = g.get("gen_no")
            durations.append({
                "run_id": rid,
                "gen_no": (-1 if _gen_no is None else int(_gen_no)),
                "duration_sec": duration_sec,
                "created_at": (None if created is None else float(created)),
                "status": str(g.get("status", "") or ""),
            })
            if created is not None:
                prev_created = float(created)

    return {"durations": durations, "count": len(durations)}


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


_REFERENCE_STRATEGIES_JSON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "reference_strategies.json"
)

# 인간 reference 결과 스크린샷 디렉토리(REPO_ROOT 기준). 읽기 전용으로 /reference_img에
#   StaticFiles 마운트하고, /reference_screenshots가 이 디렉토리의 이미지 파일명을 나열한다.
#   이 디렉토리만 노출하며(다른 디렉토리 노출 금지) 디렉토리가 없으면 마운트를 스킵한다.
_REFERENCE_SCREENSHOTS_DIR = os.path.join(REPO_ROOT, "docs", "reference", "STOM_Good_Results")

# 갤러리에 표시할 이미지 확장자. 결과 스크린샷은 .png 17장이 정본이다. 같은 #1의
#   .jpg/.jpeg 중복 포맷 변환본은 동일 화면이라 갤러리 노이즈가 되므로 .png만 노출한다
#   (StaticFiles 마운트 자체는 디렉토리 전체를 읽기 전용 서빙하므로 직접 URL 접근엔 영향 없음).
_SCREENSHOT_EXTS = (".png",)


def _reference_screenshots() -> list:
    """인간 reference 결과 스크린샷 파일명 목록을 반환한다(읽기 전용, 무예외).

    _REFERENCE_SCREENSHOTS_DIR의 최상위(서브디렉토리 미탐색) .png 결과 스크린샷만 나열한다.
    분석용 파생 크롭/줌(언더스코어 `_`로 시작하는 보조 파일: `_zoom_*`, `_crops` 등)은
    실제 결과 스크린샷이 아니므로 제외한다. #1의 .jpg/.jpeg 중복 포맷본도 .png 정본과
    같은 화면이라 제외해(확장자 화이트리스트=.png) 갤러리가 결과 화면 17장만 브라우징하게 한다.
    파일명만(경로 제외) 정렬해 돌려준다 — 프론트가 baseUrl+'/reference_img/'+filename으로
    StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록으로 표준화한다(무예외).
    """
    try:
        entries = os.listdir(_REFERENCE_SCREENSHOTS_DIR)
    except OSError:
        return []
    out = []
    for name in entries:
        if name.startswith("_"):
            continue  # 분석용 파생 크롭/줌(보조 파일) 제외 — 결과 스크린샷만.
        if not name.lower().endswith(_SCREENSHOT_EXTS):
            continue
        try:
            full = os.path.join(_REFERENCE_SCREENSHOTS_DIR, name)
            if not os.path.isfile(full):
                continue  # 서브디렉토리(_crops 등)는 제외.
        except OSError:
            continue
        out.append(name)
    return sorted(out)


def _load_reference_strategies() -> list:
    """reference_strategies.json을 읽어 인간 벤치마크 목록을 반환한다(읽기 전용, 무예외).

    파일은 이 모듈 기준 dashboard/reference_strategies.json. 파일 부재/JSON 파싱
    실패는 빈 목록으로 표준화한다(대시보드가 빈 상태를 표시). 각 항목을 명예의
    전당 공통 스키마(label·total_return_krw·total_return_pct·annual_return_pct·
    mdd_pct·payoff·trades·daily_avg_trades·max_holdings·operating_capital_krw·
    kind='human')로 매핑한다.
    """
    try:
        with open(_REFERENCE_STRATEGIES_JSON, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError, TypeError):
        return []

    strategies = (raw or {}).get("strategies") or []
    out: list = []
    for s in strategies:
        if not isinstance(s, dict):
            continue
        out.append({
            "kind": "human",
            "label": str(s.get("id") or ""),
            "period": s.get("period"),
            "days": s.get("days"),
            "operating_capital_krw": s.get("operating_capital_krw"),
            "total_return_krw": s.get("profit_krw"),
            "total_return_pct": s.get("total_return_pct"),
            "annual_return_pct": s.get("annual_return_pct"),
            "annual_unreliable": False,
            "mdd_pct": s.get("mdd_pct"),
            "payoff": s.get("payoff"),
            "trades": s.get("trades"),
            "daily_avg_trades": s.get("daily_avg_trades"),
            "max_holdings": s.get("max_holdings"),
            "win_rate_pct": s.get("win_rate_pct"),
        })
    return out


def _window_years_from_config(config_json: Optional[str]) -> Optional[float]:
    """runs.config_json의 bt_full_start/bt_full_end(YYYYMMDD 정수)에서 창 길이(년)를 구한다.

    (date(end) − date(start)).days / 365.25. 파싱 실패/필드 부재/비정상 값은 None
    으로 표준화한다(연평균을 산출하지 못함 → 호출부가 None 처리). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    days = (end - start).days
    if days <= 0:
        return None
    return days / 365.25


def _period_string_from_config(config_json: Optional[str]) -> Optional[str]:
    """runs.config_json의 bt_full_start/end(YYYYMMDD 정수)를 'YYYY-MM-DD ~ YYYY-MM-DD'로 포맷한다.

    명예의 전당 '백테 기간' 컬럼용. 인간 전략은 reference_strategies.json의 period 문자열을
    그대로 쓰고, AI 전략은 이 헬퍼로 run 창에서 동일 포맷의 기간 문자열을 만든다.
    파싱 실패/필드 부재/비정상 값(end<=start)은 None으로 표준화한다(컬럼이 '—' 표시). 무예외.
    """
    from datetime import date  # noqa: PLC0415

    if not config_json:
        return None
    try:
        cfg = json.loads(config_json)
    except (ValueError, TypeError):
        return None
    if not isinstance(cfg, dict):  # 비-dict JSON(리스트/스칼라) → None(무예외 보장).
        return None
    start_i = cfg.get("bt_full_start")
    end_i = cfg.get("bt_full_end")
    if start_i is None or end_i is None:
        return None
    try:
        si, ei = int(start_i), int(end_i)
        start = date(si // 10000, (si // 100) % 100, si % 100)
        end = date(ei // 10000, (ei // 100) % 100, ei % 100)
    except (ValueError, TypeError):
        return None
    if (end - start).days <= 0:
        return None
    return f"{start.isoformat()} ~ {end.isoformat()}"


def _hall_of_fame_payload(ai_limit: int = 30) -> Dict[str, Any]:
    """명예의 전당 payload: 인간 벤치마크 + AI 생성 통합(읽기 전용, 무예외).

    인간: reference_strategies.json을 로드한다(파일 없으면 빈 목록).
    AI: loop_runs.db에서 gate_passed=1 AND profit>0 세대를 조회해 워크플로 확정
        산식으로 매핑한다(추가 백테 0회).
          - operating_capital_krw = profit / total_profit_pct × 100
            (total_profit_pct는 '운영금 대비 수익률합계'. ≤0이면 그 행 제외).
          - total_return_krw = profit (수익금합계, 원).
          - total_return_pct = total_profit_pct (이미 DB; profit/운영금×100).
          - annual_return_pct = total_return_pct / window_years (단리).
            window_years는 runs.config_json의 bt_full_start/end에서 산출. <0.25면
            annual_unreliable=true(짧은 창 연환산 과대) + 연평균은 그대로 계산.
            window를 못 구하면 annual_return_pct=None.
        graded(score) 내림차순 상위 ai_limit.

    LoopState 무예외·close() 패턴은 _equity_curves_payload/_runs_payload와 동일.
    DB/JSON 부재는 빈 목록(무예외).

    반환: {"human": [...], "ai": [...]}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    human = _load_reference_strategies()

    st: Optional[LoopState] = None
    all_gens: list = []
    run_window_cache: Dict[str, Optional[float]] = {}
    run_period_cache: Dict[str, Optional[str]] = {}
    try:
        st = LoopState()
        all_gens = st.get_all_generations()
        # 각 run의 창 길이(년)·기간 문자열을 한 번씩 조회해 캐시한다(연평균·백테기간 산출용).
        run_ids = {str(g.get("run_id") or "") for g in all_gens if g.get("run_id")}
        for rid in run_ids:
            run_row = st.get_run(rid)
            cfg_json = run_row.get("config_json") if run_row else None
            run_window_cache[rid] = _window_years_from_config(cfg_json)
            run_period_cache[rid] = _period_string_from_config(cfg_json)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 AI 빈 목록(무예외).
        return {"human": human, "ai": []}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    ai: list = []
    for g in all_gens:
        if not bool(g.get("gate_passed")):
            continue
        profit = g.get("profit")
        total_pct = g.get("total_profit_pct")
        if profit is None or total_pct is None:
            continue
        try:
            profit_f = float(profit)
            total_pct_f = float(total_pct)
        except (ValueError, TypeError):
            continue
        # 흑자(profit>0) + 수익률합계>0(운영금 역산 가능)인 세대만.
        if profit_f <= 0 or total_pct_f <= 0:
            continue

        # 운영금 역산: profit / total_profit_pct × 100 (total_profit_pct=운영금대비%).
        operating_capital = profit_f / total_pct_f * 100.0

        run_id = str(g.get("run_id") or "")
        gen_no = int(g.get("gen_no", -1))
        window_years = run_window_cache.get(run_id)
        period_str = run_period_cache.get(run_id)
        if window_years and window_years > 0:
            annual_pct = total_pct_f / window_years
            annual_unreliable = window_years < 0.25
        else:
            annual_pct = None
            annual_unreliable = False

        # 시드(Tick_902 등 비-AILOOP, 주로 gen0)는 인간이 튜닝한 출발점이고, AILOOP_*만
        #   AI가 직접 생성한 전략이다. 사용자가 "AI가 직접 한것"과 인간 시드를 구분해 보도록
        #   kind를 나눈다('ai' vs 'seed'). 둘 다 loop_runs.db 출처라 ai 목록에 함께 담는다.
        buy_name_str = str(g.get("buy_name") or "")
        # 시드 = 명명된 비-AILOOP 전략(보통 Tick_902 등 인간 튜닝 gen0). AILOOP_* = AI 생성.
        #   빈 이름은 시드로 확정할 수 없으므로 'ai'로 둔다(시드/AI 구분 정직성).
        kind = "seed" if (buy_name_str and not buy_name_str.startswith("AILOOP")) else "ai"
        ai.append({
            "kind": kind,
            "run_id": run_id,
            "gen_no": gen_no,
            "label": f"{run_id}/g{gen_no}",
            "period": period_str,
            "buy_name": g.get("buy_name"),
            "score": (float(g.get("score")) if g.get("score") is not None else None),
            "operating_capital_krw": operating_capital,
            "total_return_krw": profit_f,
            "total_return_pct": total_pct_f,
            "annual_return_pct": annual_pct,
            "annual_unreliable": annual_unreliable,
            "mdd_pct": (float(g.get("mdd")) if g.get("mdd") is not None else None),
            "calmar": (float(g.get("calmar")) if g.get("calmar") is not None else None),
            "payoff": (float(g.get("payoff_ratio")) if g.get("payoff_ratio") is not None else None),
            "trades": (int(g.get("trade_count")) if g.get("trade_count") is not None else None),
            "daily_avg_trades": (
                float(g.get("daily_avg_trades")) if g.get("daily_avg_trades") is not None else None
            ),
            "max_hold_count": (
                float(g.get("max_hold_count")) if g.get("max_hold_count") is not None else None
            ),
        })

    # graded(score) 내림차순 상위 ai_limit.
    ai.sort(key=lambda r: (
        (r.get("score") if r.get("score") is not None else -1e18),
        r.get("run_id") or "", r.get("gen_no") or 0,
    ), reverse=True)  # score 동률 시 (run_id, gen_no)로 결정론적 순서(cap 경계 안정).
    ai = ai[: max(0, int(ai_limit))]

    return {"human": human, "ai": ai}


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


def _run_state_payload(run_id: str) -> Dict[str, Any]:
    """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성한다(읽기 전용·무예외).

    #65 P0 — run 셀렉터용. 대시보드 라이브 상태(current_state.json)는 한 번에 하나의
    run만 보여주고, 에이전트 테스트가 합성 run('segrun')을 그 파일에 쓰면 화면이 오염된다.
    이 엔드포인트는 loop_runs.db의 runs+generations에서 임의 run을 통째로 재구성하므로,
    사용자가 라이브 오염과 무관하게 실제 run(reframe1 등)을 골라 브라우징할 수 있다.

    재구성:
      - generations 행을 읽어 summary(best/winner)를 만든다.
          best   = graded(score) 최고 세대.
          winner = 하드게이트 통과 세대 중 score 최고(없으면 None).
        이는 lineage._summarize_run의 우승 선택 규칙과 동일하나, to_loop_state가
        소비하는 평탄 키(best_gen/best_score/best_buy/best_sell, winner_*)로 만든다.
      - runs.config_json에서 LoopConfig를 복원해 provider/bt_timeframe/active_config를 채운다.
      - to_loop_state(summary, gens, config=cfg, status='complete', current_gen=len-1)로 빌드.
    status='complete'는 과거 run의 정적 스냅샷이라는 의미다(라이브 진행이 아님).

    DB 부재/없는 run/조회 실패는 idle_state로 표준화한다(무예외 — 대시보드가 빈 상태 표시).
    엔진/하드게이트/CSV 무수정. 추가 백테 0회(DB 조회만).
    """
    from ai_strategy_loop.config import LoopConfig  # noqa: PLC0415
    from ai_strategy_loop.controller.state import LoopState, to_loop_state  # noqa: PLC0415

    if not run_id:
        return C.idle_state().model_dump()

    st: Optional[LoopState] = None
    run_row: Optional[Dict[str, Any]] = None
    gens: list = []
    try:
        st = LoopState()
        run_row = st.get_run(run_id)
        gens = st.get_generations(run_id)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 idle(무예외).
        return C.idle_state().model_dump()
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    # 없는 run(행도 세대도 없음) → idle(무예외 계약).
    if run_row is None and not gens:
        return C.idle_state().model_dump()

    # config_json에서 LoopConfig 복원(provider/bt_timeframe/active_config 채움). 실패는 None.
    cfg: Any = None
    cfg_json = (run_row or {}).get("config_json")
    if cfg_json:
        try:
            cfg = LoopConfig.from_dict(json.loads(cfg_json))
        except (ValueError, TypeError):
            cfg = None

    # best = graded(score) 최고 세대(점수 None은 제외). 동률은 gen_no 큰 쪽(최신).
    best_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if g.get("score") is None:
            continue
        if best_row is None or float(g.get("score") or 0.0) >= float(best_row.get("score") or 0.0):
            best_row = g
    # winner = 하드게이트 통과 세대 중 score 최고(없으면 None). 동률은 gen_no 큰 쪽.
    winner_row: Optional[Dict[str, Any]] = None
    for g in gens:
        if not bool(g.get("gate_passed")):
            continue
        if winner_row is None or float(g.get("score") or 0.0) >= float(winner_row.get("score") or 0.0):
            winner_row = g

    summary: Dict[str, Any] = {
        "run_id": run_id,
        "best_gen": (int(best_row.get("gen_no", -1)) if best_row is not None else -1),
        "best_score": (float(best_row.get("score")) if best_row and best_row.get("score") is not None else None),
        "best_buy": (best_row.get("buy_name") if best_row is not None else None),
        "best_sell": (best_row.get("sell_name") if best_row is not None else None),
        "winner_gen": (int(winner_row.get("gen_no", -1)) if winner_row is not None else -1),
        "winner_score": (
            float(winner_row.get("score")) if winner_row and winner_row.get("score") is not None else None
        ),
        "winner_buy": (winner_row.get("buy_name") if winner_row is not None else None),
        "winner_sell": (winner_row.get("sell_name") if winner_row is not None else None),
    }

    try:
        snapshot = to_loop_state(
            summary, gens, config=cfg, status="complete",
            current_gen=(len(gens) - 1 if gens else -1),
        )
        return snapshot.model_dump()
    except Exception:  # noqa: BLE001 - 빌드 실패도 idle로 표준화(무예외 계약).
        return C.idle_state().model_dump()


def _backtest_detail_payload(run_id: str, gen_no: int) -> Dict[str, Any]:
    """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(읽기 전용, 무예외).

    O1 — 대시보드 BacktestDetailChart가 fetch 한다. 일반 STOM 백테가 만드는 2-그래프
    (일별손익 막대 + 누적수익곡선)를 헤드리스 루프 결과로 재현한다. 엔진 PNG 생성은
    꺼져 있으나(cli/runner.py) per-trade 거래 CSV는 항상 생성되므로, 이미 있는 그 CSV
    하나를 O2의 parse_backtest_series로 시계열 변환한다(추가 백테 0회).

    세대 행(generations)에서 (run_id, gen_no)의 csv_path·gate_passed·daily_avg_trades를
    조회하고, 그 run의 config_json에서 bt_betting을 뽑아 누적%(cum_pct) 산출에 쓴다.
    csv_path가 상대경로면 REPO_ROOT 기준으로 해석해 서버 CWD와 무관하게 동작한다.

    csv 없음/파싱 실패/없는 세대는 빈 시계열(daily=[]·summary 0)로 표준화한다(무예외).

    반환:
      {"run_id","gen_no","gate_passed",
       "daily":[{date,daily_pnl,profit,loss,net}...],
       "cumulative":[{date,cum_profit,cum_pct}...],
       "drawdown":[{date,drawdown}...],
       "holdings":[{t_index,count}...],   # 동시보유 종목수(이벤트/시각축, STOM fig2 상단 대응)
       "summary":{trade_count,final_profit,max_drawdown,n_days,peak_holdings}}
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.equity_series import parse_backtest_series  # noqa: PLC0415

    empty_series: Dict[str, Any] = {
        "daily": [],
        "cumulative": [],
        "drawdown": [],
        "holdings": [],
        "summary": {
            "trade_count": 0,
            "final_profit": 0.0,
            "max_drawdown": 0.0,
            "n_days": 0,
            "peak_holdings": 0,
        },
    }

    # 세대 행에서 csv_path·gate_passed 조회 + run config_json에서 bt_betting 추출.
    csv_path: Optional[str] = None
    gate_passed = False
    betting = None
    found = False
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for row in st.get_generations(run_id):
            if int(row.get("gen_no", -1)) == int(gen_no):
                csv_path = row.get("csv_path")
                gate_passed = bool(row.get("gate_passed"))
                found = True
                break
        # bt_betting은 runs.config_json(JSON 문자열)에서 뽑는다(cum_pct 산출용).
        if found:
            run_row = st.get_run(run_id)
            if run_row is not None:
                try:
                    cfg = json.loads(run_row.get("config_json") or "{}")
                    betting = cfg.get("bt_betting")
                except (ValueError, TypeError):
                    betting = None
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 응답(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": False, **empty_series}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not found or not csv_path:
        # 없는 (run,gen) 또는 csv_path 없는 세대 → 빈 시계열(무예외).
        return {"run_id": run_id, "gen_no": int(gen_no), "gate_passed": gate_passed, **empty_series}

    # 상대경로면 REPO_ROOT 기준으로 해석(서버 CWD 무관 동작). 파서는 실패 시 빈 구조.
    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    series = parse_backtest_series(resolved, betting=betting)
    return {
        "run_id": run_id,
        "gen_no": int(gen_no),
        "gate_passed": gate_passed,
        "daily": series.get("daily", []),
        "cumulative": series.get("cumulative", []),
        "drawdown": series.get("drawdown", []),
        "holdings": series.get("holdings", []),
        "summary": series.get("summary", empty_series["summary"]),
    }


def _adaptive_timing_payload(run_id: Optional[str], lookback: int) -> Dict[str, Any]:
    """run의 gen0(또는 첫 gate_passed) 전략 CSV에 적응형 타이밍 리포트를 적용한다(읽기 전용, 무예외).

    분석 전용(엔진/하드게이트/스코어/생성 무영향) 오버레이다. loop_runs.db의 generations에서
    그 run의 gen0(가장 낮은 gen_no) 행 csv_path를 찾아 adaptive_timing_report를 돌려준다.
    gen0에 csv_path가 없으면 첫 gate_passed=1 세대의 csv_path로 폴백한다(_backtest_detail
    payload와 동일한 LoopState DB 경로/무예외 패턴).

    run_id 미지정/없는 run/csv_path 없음/파싱 실패는 {"error": ...}로 표준화한다(무예외).
    상대경로 csv_path는 REPO_ROOT 기준으로 해석한다(서버 CWD 무관).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415
    from ai_strategy_loop.fitness.adaptive_timing import adaptive_timing_report  # noqa: PLC0415

    if not run_id:
        return {"error": "run_id required"}

    csv_path: Optional[str] = None
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        rows = st.get_generations(run_id)  # gen_no 오름차순.
        if not rows:
            return {"error": f"no generations for run_id={run_id!r}"}
        # gen0(가장 낮은 gen_no)의 csv_path 우선. 없으면 첫 gate_passed 세대로 폴백.
        first = rows[0]
        csv_path = first.get("csv_path")
        if not csv_path:
            for row in rows:
                if bool(row.get("gate_passed")) and row.get("csv_path"):
                    csv_path = row.get("csv_path")
                    break
    except Exception as exc:  # noqa: BLE001 - DB 없거나 조회 실패면 error(무예외).
        return {"error": str(exc)}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass

    if not csv_path:
        return {"error": f"no csv_path for run_id={run_id!r}"}

    resolved = csv_path if os.path.isabs(csv_path) else os.path.join(REPO_ROOT, csv_path)
    try:
        report = adaptive_timing_report(resolved, lookback)
    except Exception as exc:  # noqa: BLE001 - 리포트 산출 실패도 error로 흡수(무예외).
        return {"error": str(exc)}

    return {"run_id": run_id, "lookback": lookback, **report}


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

    @app.get("/hall_of_fame")
    def hall_of_fame() -> Dict[str, Any]:
        """명예의 전당: 인간 벤치마크 + AI 생성 통합 목록을 반환한다(읽기 전용, 무예외).

        인간은 reference_strategies.json(19전략), AI는 loop_runs.db의 gate_passed=1·
        흑자 세대를 운영금 역산·연평균 산식으로 매핑해 graded 상위 30개를 돌려준다.
        JSON/DB가 없으면 빈 목록(무예외 계약 — 대시보드가 빈 상태를 표시).
        """
        return _hall_of_fame_payload()

    @app.get("/reference_screenshots")
    def reference_screenshots() -> Dict[str, Any]:
        """인간 reference 결과 스크린샷 파일명 목록을 반환한다(갤러리 fetch용, 읽기 전용, 무예외).

        docs/reference/STOM_Good_Results의 최상위 이미지 파일명만 나열한다(분석용 파생
        크롭/줌은 제외). 프론트가 각 파일명을 baseUrl+'/reference_img/'+filename으로
        StaticFiles에서 직접 가져온다. 디렉토리 부재/조회 실패는 빈 목록(무예외 계약).
        """
        files = _reference_screenshots()
        return {"screenshots": files, "count": len(files)}

    @app.get("/runs")
    def runs() -> Dict[str, Any]:
        """loop_runs.db의 모든 run 요약을 반환한다(run 비교 콘솔 목록).

        lineage.compare_runs(run_ids=None)로 전 run을 요약한다. DB가 없거나
        조회 실패면 빈 목록을 돌려 대시보드가 깨지지 않게 한다(무예외 계약).
        """
        return _runs_payload(None)

    @app.get("/run_state")
    def run_state(run_id: str = "") -> Dict[str, Any]:
        """과거(또는 현재) run의 전체 LoopState payload를 DB에서 재구성해 반환한다(#65 run 셀렉터).

        쿼리: ?run_id=<run_id>. loop_runs.db의 runs+generations에서 그 run을 통째로
        재구성한다(세대표·best/winner·코드뷰어가 그 run을 소비). 라이브 상태가 합성 run으로
        오염돼도 사용자가 실제 run을 골라 본다. run_id 미지정/없는 run/조회 실패는 idle
        상태로 표준화한다(무예외 — 대시보드가 빈 상태 표시). 읽기 전용·추가 백테 0회.
        """
        return _run_state_payload(run_id)

    @app.get("/generation_durations")
    def generation_durations(run_id: Optional[str] = None) -> Dict[str, Any]:
        """세대별 소요초(인접 created_at 차분)를 반환한다(#64 과거 run retroactive).

        쿼리: ?run_id=<run_id>(선택). 없으면 전체 run. LIVE 발행이 없던 과거 run에도
        DB의 created_at/started_at로 산출되므로 사용자가 지금 바로 세대 소요를 본다.
        DB 없거나 조회 실패면 빈 목록(무예외).
        """
        return _generation_durations_payload(run_id)

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

    @app.get("/backtest_detail")
    def backtest_detail(run_id: str = "", gen_no: int = -1) -> Dict[str, Any]:
        """한 세대의 백테 상세 시계열(일별손익·누적수익·낙폭)을 반환한다(차트 fetch용).

        쿼리: ?run_id=<run_id>&gen_no=<n>. 그 세대의 per-trade 결과 CSV를
        parse_backtest_series로 일별손익+누적곡선+낙폭으로 변환해 돌려준다(추가 백테 0회).
        run_id 미지정/없는 gen/CSV 없음/파싱 실패는 빈 시계열로 표준화한다(무예외 —
        대시보드가 빈 상태 패널을 표시).
        """
        if not run_id or gen_no < 0:
            return {
                "run_id": run_id, "gen_no": gen_no, "gate_passed": False,
                "daily": [], "cumulative": [], "drawdown": [],
                "summary": {
                    "trade_count": 0, "final_profit": 0.0,
                    "max_drawdown": 0.0, "n_days": 0,
                },
            }
        return _backtest_detail_payload(run_id, gen_no)

    @app.get("/adaptive_timing")
    def adaptive_timing(run_id: Optional[str] = None, lookback: int = 2) -> Dict[str, Any]:
        """run의 gen0(또는 첫 gate_passed) 전략 결과 CSV에 적응형 레짐-타이밍 리포트를 돌린다.

        쿼리: ?run_id=<run_id>&lookback=<n>. 분석 전용(엔진/하드게이트/스코어 무영향)
        오버레이로, always-on 대비 위험조정(수익/MDD)을 비교한다(추가 백테 0회). run_id
        미지정/없는 run/CSV 없음/파싱 실패는 {"error": ...}로 표준화한다(읽기 전용·무예외).
        """
        return _adaptive_timing_payload(run_id, lookback)

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

    # 인간 reference 결과 스크린샷을 /reference_img 하위에 읽기 전용으로 마운트한다.
    #   StaticFiles는 GET/HEAD만 처리(쓰기 불가)하고, 노출 대상은 STOM_Good_Results
    #   디렉토리 단 하나뿐이다(다른 디렉토리 노출 금지). 디렉토리가 없으면 마운트를
    #   스킵해 API만으로도 기동되게 한다(무예외). 갤러리는 /reference_screenshots로 받은
    #   파일명을 baseUrl+'/reference_img/'+filename 으로 직접 가져온다.
    if os.path.isdir(_REFERENCE_SCREENSHOTS_DIR):
        app.mount(
            "/reference_img",
            StaticFiles(directory=_REFERENCE_SCREENSHOTS_DIR),
            name="reference_img",
        )

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
