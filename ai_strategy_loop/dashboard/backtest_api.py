"""Backtest workbench API — 조건식 CRUD · 잡 실행 · 분석 라우트 (PR2).

PR1 의 헬스 골격 위에 GUI 백테스트의 웹 이관(조건식 CRUD, 잡 실행, 결과/분석)을
확장한다. 모든 엔드포인트는 무예외 계약을 따른다(데이터 없으면 빈 구조, 충돌/검증
실패도 HTTP 200 + {"status":"error", ...} 페이로드 — 기존 대시보드 컨벤션과 동일).

데이터 경계:
  - 쓰기는 운영 ``_database/strategy.db`` 의 stockbuy/stocksell/formula 에 한정.
    (bootstrap 이 STOM_CLI_DB_STRATEGY 를 루프 격리 DB로 바꿔두므로, 워크벤치는
     env 오버라이드를 무시하고 운영 DB 경로를 명시 사용한다.)
  - 시세 DB(일일 + *_back.db)는 반드시 ``file:...?mode=ro`` 로만 연다(하드링크 보호).
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from fastapi import APIRouter, Body, WebSocket, WebSocketDisconnect

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobSpec, get_job_manager

# 라이브 잡 WS push 간격(초)·로그 테일 줄 수.
_WS_JOB_INTERVAL_SEC = 1.0
_WS_JOB_LOG_TAIL = 10
_JOB_TERMINAL = ("success", "no_trades", "error", "timeout", "cancelled", "stale")

# 패키지 루트(.../ai_strategy_loop) 기준 경로.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_DATABASE_DIR = REPO_ROOT / "_database"

# 운영 strategy.db / 시세 통합 back-DB(읽기전용).
_STRATEGY_DB = _DATABASE_DIR / "strategy.db"
_STOCK_MIN_BACK = _DATABASE_DIR / "stock_min_back.db"
_STOCK_TICK_BACK = _DATABASE_DIR / "stock_tick_back.db"

# kind → (table, name_col, code_col).
_KIND_TABLES: Dict[str, tuple[str, str, str]] = {
    "buy": ("stockbuy", "index", "전략코드"),
    "sell": ("stocksell", "index", "전략코드"),
    "formula": ("formula", "수식명", "수식코드"),
}


class HealthResponse(TypedDict):
    status: str
    module: str
    api_version: int


backtest_router = APIRouter(prefix="/bt", tags=["backtest"])


@backtest_router.get("/health")
def backtest_health() -> HealthResponse:
    """백테스트 API 헬스 체크. 탭 셸 연결 상태 배지가 소비한다."""
    return {"status": "ok", "module": "backtest_api", "api_version": 1}


# --------------------------------------------------------------------------- db
def _strategy_db_path() -> str:
    """운영 strategy.db 경로(테스트는 STOM_WEBBT_STRATEGY_DB env 로 오버라이드)."""
    return os.environ.get("STOM_WEBBT_STRATEGY_DB") or str(_STRATEGY_DB)


def _connect_strategy(*, readonly: bool = False) -> Optional[sqlite3.Connection]:
    """운영 strategy.db 연결을 연다. 실패하면 None(무예외)."""
    path = _strategy_db_path()
    try:
        if readonly:
            return sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        return sqlite3.connect(path)
    except sqlite3.Error:
        return None


def _connect_ro(db_path: Path) -> Optional[sqlite3.Connection]:
    """시세 DB를 읽기전용(mode=ro)으로만 연다. 없거나 실패하면 None."""
    if not db_path.is_file():
        return None
    try:
        return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return None


# --------------------------------------------------------------- strategy CRUD
@backtest_router.get("/strategies")
def list_strategies(kind: str = "buy") -> Dict[str, Any]:
    """strategy.db 조건식 목록(이름/코드 미리보기/길이/ailoop 여부)."""
    spec = _KIND_TABLES.get(kind)
    if spec is None:
        return {"status": "error", "message": f"kind 는 buy|sell|formula: {kind!r}", "items": []}
    table, name_col, code_col = spec
    con = _connect_strategy(readonly=True)
    if con is None:
        return {"items": [], "count": 0, "kind": kind}
    items: List[Dict[str, Any]] = []
    try:
        rows = con.execute(f'SELECT "{name_col}", "{code_col}" FROM {table}').fetchall()
        for name, code in rows:
            code = code or ""
            first_line = next((ln for ln in str(code).splitlines() if ln.strip()), "")
            items.append({
                "name": str(name),
                "preview": first_line[:120],
                "length": len(str(code)),
                "is_ailoop": _looks_ailoop(str(name)),
            })
    except sqlite3.Error:
        return {"items": [], "count": 0, "kind": kind}
    finally:
        con.close()
    items.sort(key=lambda r: r["name"])
    return {"items": items, "count": len(items), "kind": kind}


def _looks_ailoop(name: str) -> bool:
    """AI 루프 생성 전략 휴리스틱(이름 접두/패턴)."""
    markers = ("AUTO", "Auto_", "gen", "reframe", "_g", "TMP", "Study")
    return any(marker in name for marker in markers)


@backtest_router.get("/strategy")
def get_strategy(kind: str = "buy", name: str = "") -> Dict[str, Any]:
    """단일 조건식 코드 전문을 반환한다. 없으면 available=False."""
    spec = _KIND_TABLES.get(kind)
    if spec is None or not name:
        return {"available": False, "name": name, "code": ""}
    table, name_col, code_col = spec
    con = _connect_strategy(readonly=True)
    if con is None:
        return {"available": False, "name": name, "code": ""}
    try:
        row = con.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "{name_col}" = ?', (name,)
        ).fetchone()
    except sqlite3.Error:
        return {"available": False, "name": name, "code": ""}
    finally:
        con.close()
    if row is None:
        return {"available": False, "name": name, "code": ""}
    return {"available": True, "name": name, "code": str(row[0] or ""), "kind": kind}


@backtest_router.post("/strategy/validate")
def validate_strategy_code(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """저장 없이 compile() 문법 검증. {ok, error?}."""
    code = str(payload.get("code", "") or "")
    return _compile_check(code)


def _compile_check(code: str) -> Dict[str, Any]:
    if not code.strip():
        return {"ok": False, "error": "전략 코드가 비어있습니다."}
    try:
        compile(code, "<strategy>", "exec")
    except SyntaxError as exc:
        return {"ok": False, "error": f"구문 오류: {exc}"}
    return {"ok": True, "error": None}


@backtest_router.post("/strategy")
def save_strategy(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """조건식 생성/수정 — compile() 검증 후 INSERT OR REPLACE.

    overwrite=false 인데 동일 이름이 이미 있으면 status='error'/code='exists' (HTTP 200,
    무예외 컨벤션). buy/sell 은 PK 충돌을 REPLACE 로 처리. formula 는 PK 가 없어
    수식명 기준으로 DELETE+INSERT(중복 방지).
    """
    kind = str(payload.get("kind", "") or "")
    name = str(payload.get("name", "") or "").strip()
    code = str(payload.get("code", "") or "")
    overwrite = bool(payload.get("overwrite", False))

    spec = _KIND_TABLES.get(kind)
    if spec is None:
        return {"status": "error", "message": f"kind 는 buy|sell|formula: {kind!r}"}
    if not name:
        return {"status": "error", "message": "이름이 비었습니다."}
    if any(ch in name for ch in ("\x00", "\n", "\r")):
        return {"status": "error", "message": "이름에 허용되지 않는 문자가 있습니다."}

    check = _compile_check(code)
    if not check["ok"]:
        return {"status": "error", "message": check["error"]}

    table, name_col, code_col = spec
    con = _connect_strategy()
    if con is None:
        return {"status": "error", "message": "strategy.db 연결 실패"}
    try:
        existing = con.execute(
            f'SELECT 1 FROM {table} WHERE "{name_col}" = ?', (name,)
        ).fetchone()
        if existing is not None and not overwrite:
            return {"status": "error", "code": "exists", "message": f"'{name}' 이(가) 이미 존재합니다(overwrite=true 필요)."}
        # 멱등 저장: 기존 행 삭제 후 삽입(formula 는 PK 가 없어 REPLACE 불가하므로
        #   DELETE+INSERT 로 단일 행을 보장한다. buy/sell 도 동일 경로로 통일).
        con.execute(f'DELETE FROM {table} WHERE "{name_col}" = ?', (name,))
        con.execute(
            f'INSERT INTO {table} ("{name_col}", "{code_col}") VALUES (?, ?)', (name, code)
        )
        con.commit()
    except sqlite3.Error as exc:
        return {"status": "error", "message": f"저장 실패: {exc}"}
    finally:
        con.close()
    return {"status": "ok", "name": name, "kind": kind, "created": existing is None}


@backtest_router.post("/strategy/delete")
def delete_strategy(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """조건식 삭제(실수 방지: confirm 에 이름 재입력 필수)."""
    kind = str(payload.get("kind", "") or "")
    name = str(payload.get("name", "") or "").strip()
    confirm = str(payload.get("confirm", "") or "").strip()

    spec = _KIND_TABLES.get(kind)
    if spec is None:
        return {"status": "error", "message": f"kind 는 buy|sell|formula: {kind!r}"}
    if not name:
        return {"status": "error", "message": "이름이 비었습니다."}
    if confirm != name:
        return {"status": "error", "message": "confirm 이 이름과 일치하지 않습니다."}

    table, name_col, _ = spec
    con = _connect_strategy()
    if con is None:
        return {"status": "error", "message": "strategy.db 연결 실패"}
    try:
        cur = con.execute(f'DELETE FROM {table} WHERE "{name_col}" = ?', (name,))
        con.commit()
        deleted = cur.rowcount
    except sqlite3.Error as exc:
        return {"status": "error", "message": f"삭제 실패: {exc}"}
    finally:
        con.close()
    if deleted <= 0:
        return {"status": "error", "message": f"'{name}' 을(를) 찾을 수 없습니다."}
    return {"status": "ok", "name": name, "kind": kind, "deleted": int(deleted)}


# ---------------------------------------------------------------- data_range
@backtest_router.get("/data_range")
def data_range() -> Dict[str, Any]:
    """tick/min 일일 DB 인벤토리 + *_back.db 보유 기간(moneytop min/max)."""
    tick_days = _daily_db_dates("stock_tick")
    min_days = _daily_db_dates("stock_min")
    return {
        "tick": {
            "dates": tick_days,
            "count": len(tick_days),
            "back_range": _back_range(_STOCK_TICK_BACK),
        },
        "min": {
            "dates": min_days,
            "count": len(min_days),
            "back_range": _back_range(_STOCK_MIN_BACK),
        },
    }


def _daily_db_dates(prefix: str) -> List[int]:
    """``_database/<prefix>_YYYYMMDD.db`` 파일에서 날짜 목록(정렬)을 추출한다."""
    dates: List[int] = []
    try:
        for entry in _DATABASE_DIR.glob(f"{prefix}_*.db"):
            stem = entry.stem  # stock_tick_20250407
            tail = stem.rsplit("_", 1)[-1]
            if len(tail) == 8 and tail.isdigit():
                dates.append(int(tail))
    except OSError:
        return []
    return sorted(set(dates))


def _back_range(db_path: Path) -> Optional[Dict[str, int]]:
    """*_back.db 의 moneytop index(YYYYMMDDHHMM) min/max → 보유 날짜 범위(YYYYMMDD)."""
    con = _connect_ro(db_path)
    if con is None:
        return None
    try:
        row = con.execute('SELECT MIN("index"), MAX("index") FROM moneytop').fetchone()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not row or row[0] is None or row[1] is None:
        return None
    return {"start": int(row[0]) // 10000, "end": int(row[1]) // 10000}


# ------------------------------------------------------------------- jobs/run
@backtest_router.post("/run")
def run_backtest(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """백테스트 잡 시작 → {job_id}. 이름/날짜 검증은 잡 매니저가 수행."""
    try:
        one_code = str(payload["one_code"]).strip() if payload.get("one_code") else None
        divid_mode = str(payload.get("divid_mode", "") or "").strip() or (
            "한종목 로딩" if one_code else "종목코드별 분류"
        )
        back_db_override = (
            str(payload["back_db_override"]).strip() if payload.get("back_db_override") else None
        )
        spec = BacktestJobSpec(
            buy=str(payload.get("buy", "") or "").strip(),
            sell=str(payload.get("sell", "") or "").strip(),
            start=int(payload.get("start", 0) or 0),
            end=int(payload.get("end", 0) or 0),
            timeframe=str(payload.get("timeframe", "min") or "min"),
            engines=int(payload.get("engines", 4) or 4),
            timeout=int(payload.get("timeout", 600) or 600),
            divid_mode=divid_mode,
            one_code=one_code,
            back_db_override=back_db_override,
        )
    except (TypeError, ValueError) as exc:
        return {"status": "error", "message": f"잘못된 파라미터: {exc}"}
    return get_job_manager().submit(spec)


@backtest_router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """모든 잡(최신순)."""
    return get_job_manager().list_jobs()


@backtest_router.get("/job")
def get_job(job_id: str = "") -> Dict[str, Any]:
    """잡 상태 + 진행률 + 로그 테일(마지막 50줄)."""
    if not job_id:
        return {"available": False, "job_id": job_id}
    return get_job_manager().get(job_id)


@backtest_router.post("/job/cancel")
def cancel_job(payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """잡 취소(대기 중이면 큐 제거, 실행 중이면 프로세스 회수)."""
    job_id = str(payload.get("job_id", "") or "")
    if not job_id:
        return {"status": "error", "message": "job_id 가 비었습니다."}
    return get_job_manager().cancel(job_id)


# --------------------------------------------------------------------- result
@backtest_router.get("/result")
def get_result(
    job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None
) -> Dict[str, Any]:
    """완료 잡의 metrics + 분석 전체 묶음. 미완료/없음이면 available=False.

    no_trades 잡은 metrics=None, analysis=빈 구조로 정상 반환(에러 아님).
    t_start/t_end(매수시간 YYYYMMDDHHMMSS) 가 있으면 그 구간만 재분석한다(브러시).
    """
    manager = get_job_manager()
    record = manager.get(job_id, log_tail=0)
    if not record.get("available"):
        return {"available": False, "job_id": job_id}
    status = record.get("status")
    csv_path = record.get("csv_path")
    # no_trades 는 csv_path 없이 정상 종결 — 빈 분석 구조를 반환한다.
    if status == "no_trades":
        return {
            "available": True,
            "job_id": job_id,
            "status": status,
            "metrics": None,
            "analysis": analysis.full_analysis(None),
            "message": record.get("message", ""),
        }
    bundle = analysis.full_analysis(csv_path, t_start, t_end)
    ranged = t_start is not None or t_end is not None
    return {
        "available": True,
        "job_id": job_id,
        "status": status,
        # 구간 분석 시 metrics 는 CLI 전체 메트릭 대신 구간 summary 로 대체(카드 동기).
        "metrics": bundle["summary"] if ranged else record.get("metrics"),
        "analysis": bundle,
        "ranged": ranged,
    }


def _analysis_for_job(
    job_id: str, t_start: Optional[int] = None, t_end: Optional[int] = None
) -> List[Dict[str, Any]]:
    """잡 결과 CSV → trades 리스트(분석 개별 엔드포인트 공용, 옵션 매수시간 범위 필터)."""
    csv_path = get_job_manager().result_csv_path(job_id)
    trades = analysis.load_trades_csv(csv_path)
    return analysis.filter_trades(trades, t_start, t_end)


@backtest_router.get("/analysis/summary")
def analysis_summary(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    return {"job_id": job_id, "summary": analysis.summary_metrics(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/equity")
def analysis_equity(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    return {"job_id": job_id, "equity": analysis.equity_series(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/distribution")
def analysis_distribution(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    return {"job_id": job_id, "distribution": analysis.pnl_distribution(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/heatmap")
def analysis_heatmap(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    return {"job_id": job_id, "heatmap": analysis.time_heatmap(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/underwater")
def analysis_underwater(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    return {"job_id": job_id, "underwater": analysis.underwater(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/insights")
def analysis_insights(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    trades = _analysis_for_job(job_id, t_start, t_end)
    return {"job_id": job_id, "insights": analysis.generate_insights(trades)}


@backtest_router.get("/analysis/mae_mfe")
def analysis_mae_mfe(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    """MAE/MFE 산점도 포인트(R_MAE/R_MFE, 결측 제외, 최대 1000pt)."""
    return {"job_id": job_id, "mae_mfe": analysis.mae_mfe(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/exit_reasons")
def analysis_exit_reasons(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    """매도조건(청산사유)별 거래수/총손익/승률 분해."""
    return {"job_id": job_id, "exit_reasons": analysis.exit_reason_breakdown(_analysis_for_job(job_id, t_start, t_end))}


# --------------------------------------------------------------------- live WS
@backtest_router.websocket("/ws_job")
async def ws_job(websocket: WebSocket, job_id: str = "") -> None:
    """라이브 잡 상태 WS — 1초 간격으로 진행 상태를 push, 종결 시 close.

    페이로드: {job_id, status, progress, phase, elapsed, log_tail(최근 10줄)}.
    잡이 없으면 {error} 후 close. 터미널 상태 도달 시 마지막 페이로드에 terminal:true.
    잡 매니저는 기존 모듈 레벨 싱글톤을 재사용한다(수정 없음).
    """
    await websocket.accept()
    if not job_id:
        await websocket.send_json({"error": "job_id 가 필요합니다."})
        await websocket.close()
        return
    manager = get_job_manager()
    try:
        while True:
            record = manager.get(job_id, log_tail=_WS_JOB_LOG_TAIL)
            if not record.get("available"):
                await websocket.send_json({"error": "job_id 없음", "job_id": job_id})
                await websocket.close()
                return
            status = record.get("status")
            terminal = status in _JOB_TERMINAL
            await websocket.send_json({
                "job_id": job_id,
                "status": status,
                "progress": record.get("progress", 0.0),
                "phase": record.get("phase", ""),
                "elapsed": _job_elapsed(record),
                "log_tail": record.get("log_tail", []),
                "message": record.get("message", ""),
                "terminal": terminal,
            })
            if terminal:
                await websocket.close()
                return
            await asyncio.sleep(_WS_JOB_INTERVAL_SEC)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - 어떤 예외도 흡수(대시보드 보호), 연결만 닫는다.
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass


def _job_elapsed(record: Dict[str, Any]) -> float:
    """잡 경과초(시작~종료 또는 현재). 미시작이면 0."""
    import time

    started = record.get("started_at")
    if not started:
        return 0.0
    end = record.get("finished_at") or time.time()
    return max(0.0, float(end) - float(started))
