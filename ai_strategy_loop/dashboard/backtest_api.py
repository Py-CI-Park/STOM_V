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
from fastapi.responses import HTMLResponse

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import backtest_report as report
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobSpec, get_job_manager

# 라이브 잡 WS push 간격(초)·로그 테일 줄 수.
_WS_JOB_INTERVAL_SEC = 1.0
_WS_JOB_LOG_TAIL = 10
_JOB_TERMINAL = ("success", "no_trades", "error", "timeout", "cancelled", "stale")

# 패키지 루트(.../ai_strategy_loop) 기준 경로.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_DATABASE_DIR = REPO_ROOT / "_database"

# back_db_override(#36) allowlist 루트 — 이 두 디렉토리 하위 경로만 시세 DB 교체에
#   허용한다(임의 절대경로로 하드링크 보호 시세 DB 영역 밖을 가리키는 것을 차단).
_BACK_DB_ALLOW_ROOTS = (
    _DATABASE_DIR.resolve(),
    (_PACKAGE_DIR / "state").resolve(),
)

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


def _validate_back_db_override(raw: str) -> Optional[str]:
    """back_db_override(#36) 경로를 allowlist 로 검증한다. 위반이면 None.

    _database/ 또는 ai_strategy_loop/state/ 하위 경로만 허용한다(임의 절대경로 차단).
    symlink/.. 우회를 막기 위해 resolve 후 root 의 하위인지 확인한다. 비ASCII/존재
    여부는 보지 않는다(경로 위치만 게이트 — 실제 존재 검사는 잡 매니저가 수행).
    """
    if not raw or not raw.strip():
        return None
    try:
        candidate = Path(raw.strip()).resolve()
    except (OSError, ValueError, RuntimeError):
        return None
    for root in _BACK_DB_ALLOW_ROOTS:
        try:
            candidate.relative_to(root)
            return str(candidate)
        except ValueError:
            continue
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
        back_db_override = None
        if payload.get("back_db_override"):
            raw_override = str(payload["back_db_override"]).strip()
            back_db_override = _validate_back_db_override(raw_override)
            # #36: allowlist(_database/ · ai_strategy_loop/state/) 밖이면 무예외 error.
            if back_db_override is None:
                return {
                    "status": "error",
                    "message": "back_db_override 는 _database/ 또는 ai_strategy_loop/state/ 하위 경로만 허용됩니다.",
                }
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


# 몬테카를로 시행수 상한(서버 보호 — 과도한 n 차단).
_MC_MAX_N = 20000


@backtest_router.get("/analysis/montecarlo")
def analysis_montecarlo(
    job_id: str = "",
    n: int = 2000,
    seed: Optional[int] = None,
    ruin_pct: float = 30.0,
    t_start: Optional[int] = None,
    t_end: Optional[int] = None,
) -> Dict[str, Any]:
    """몬테카를로 — 일별 손익 셔플 재배열로 MDD/최종손익 분포·파산확률·팬차트."""
    n = max(0, min(int(n), _MC_MAX_N))
    trades = _analysis_for_job(job_id, t_start, t_end)
    return {"job_id": job_id, "montecarlo": analysis.monte_carlo(trades, n=n, seed=seed, ruin_pct=ruin_pct)}


@backtest_router.get("/analysis/orderflow")
def analysis_orderflow(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    """오더플로우 — 승/패 그룹별 진입 체결강도/호가불균형/전일동시간비/등락율 분포 비교."""
    return {"job_id": job_id, "orderflow": analysis.entry_orderflow(_analysis_for_job(job_id, t_start, t_end))}


# --------------------------------------------------------------------- compare
def _compare_side(job_id: str) -> Optional[Dict[str, Any]]:
    """단일 잡의 비교 페이로드 {job_id, status, metrics, equity}. 없으면 None(무예외).

    metrics 는 CLI 저장 메트릭이 있으면 그것을, 없으면 analysis.summary 를 쓴다.
    equity 는 결과 CSV 로부터 누적수익곡선을 재계산한다(없으면 빈 구조).
    """
    if not job_id:
        return None
    manager = get_job_manager()
    record = manager.get(job_id, log_tail=0)
    if not record.get("available"):
        return None
    csv_path = manager.result_csv_path(job_id)
    trades = analysis.load_trades_csv(csv_path)
    summary = analysis.summary_metrics(trades)
    cli_metrics = record.get("metrics")
    return {
        "job_id": job_id,
        "status": record.get("status"),
        "metrics": cli_metrics if cli_metrics else summary,
        "summary": summary,
        "equity": analysis.equity_series(trades),
        "trade_count": summary["trade_count"],
    }


# 비교 delta 산출 대상 메트릭(둘 다 숫자일 때만 차이 계산).
_COMPARE_KEYS = (
    "trade_count", "win_rate", "total_profit_pct", "total_profit_krw",
    "max_drawdown_pct", "profit_factor", "payoff_ratio", "sharpe", "calmar",
)


def _compare_delta(a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """두 잡 summary 의 주요 메트릭 차이(b - a). 한쪽이라도 없으면 빈 dict."""
    if not a or not b:
        return {}
    sa = a.get("summary") or {}
    sb = b.get("summary") or {}
    delta: Dict[str, Any] = {}
    for key in _COMPARE_KEYS:
        va, vb = sa.get(key), sb.get(key)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            delta[key] = float(vb) - float(va)
    return delta


@backtest_router.get("/compare")
def compare_jobs(job_a: str = "", job_b: str = "") -> Dict[str, Any]:
    """두 잡 A/B 비교 — 각 메트릭·수익곡선 + delta(b-a). 한쪽 없으면 해당 키 null(무예외)."""
    a = _compare_side(job_a)
    b = _compare_side(job_b)
    return {
        "a": a,
        "b": b,
        "delta": _compare_delta(a, b),
    }


# --------------------------------------------------------------------- report
def _period_label(start: Any, end: Any) -> str:
    """잡 spec/세대의 시작·종료를 'YYYYMMDD~YYYYMMDD' 라벨로(없으면 '—')."""
    s = str(start or "").strip()
    e = str(end or "").strip()
    if s and e:
        return f"{s}~{e}"
    return s or e or "—"


def _report_payload_for_job(
    job_id: str, t_start: Optional[int], t_end: Optional[int]
) -> Optional[Dict[str, Any]]:
    """완료 잡 → render_report payload. 잡 없음이면 None(404 대신 에러 HTML 은 호출측)."""
    manager = get_job_manager()
    record = manager.get(job_id, log_tail=0)
    if not record.get("available"):
        return None
    status = record.get("status")
    spec = record.get("spec") or {}
    csv_path = record.get("csv_path")
    bundle = analysis.full_analysis(csv_path, t_start, t_end)
    trades = analysis.filter_trades(analysis.load_trades_csv(csv_path), t_start, t_end)
    mc = analysis.monte_carlo(trades, n=2000)
    ranged = t_start is not None or t_end is not None
    note = ""
    if status == "no_trades":
        note = "거래 0건 — 전략이 해당 기간에 매수 신호를 내지 않았습니다(메트릭 없음)."
    elif not csv_path:
        note = "결과 CSV 가 없어 메트릭 요약만 표시합니다."
    return {
        "meta": {
            "title": f"백테스트 리포트 · {spec.get('buy', '')}",
            "buy": spec.get("buy"),
            "sell": spec.get("sell"),
            "period": _period_label(spec.get("start"), spec.get("end")),
            "source": f"job:{job_id}" + (" (구간)" if ranged else ""),
            "trade_count": bundle["summary"]["trade_count"],
            "status": status,
            "note": note,
        },
        "metrics": bundle["summary"] if ranged else (record.get("metrics") or bundle["summary"]),
        "analysis": bundle,
        "montecarlo": mc,
    }


def _report_payload_for_run(run_id: str, gen_no: int) -> Optional[Dict[str, Any]]:
    """loop_runs.db(읽기전용) 세대 → render_report payload. 세대 없음이면 None.

    csv_path 존재 시 같은 풀 분석 리포트. CSV 부재 시 generations 행의
    trade_count/profit/mdd 등으로 축약 리포트(무예외).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    row: Optional[Dict[str, Any]] = None
    st: Optional[LoopState] = None
    try:
        st = LoopState()
        for r in st.get_generations(run_id):
            if int(r.get("gen_no", -1)) == int(gen_no):
                row = r
                break
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 None(무예외).
        return None
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass
    if row is None:
        return None

    raw_csv = row.get("csv_path")
    csv_path = None
    if raw_csv:
        csv_path = raw_csv if os.path.isabs(raw_csv) else os.path.join(str(REPO_ROOT), raw_csv)
        if not os.path.isfile(csv_path):
            csv_path = None

    base_meta = {
        "title": f"세대 리포트 · {run_id} / g{gen_no}",
        "buy": row.get("buy_name"),
        "sell": row.get("sell_name"),
        "period": "—",
        "source": f"run:{run_id} gen:{gen_no}",
    }
    if csv_path:
        bundle = analysis.full_analysis(csv_path)
        trades = analysis.load_trades_csv(csv_path)
        mc = analysis.monte_carlo(trades, n=2000)
        return {
            "meta": {**base_meta, "trade_count": bundle["summary"]["trade_count"], "note": ""},
            "metrics": bundle["summary"],
            "analysis": bundle,
            "montecarlo": mc,
        }
    # CSV 부재 — generations 행 메트릭으로 축약 리포트(메트릭 카드만).
    fallback_metrics = {
        "trade_count": row.get("trade_count"),
        "total_profit_krw": row.get("profit"),
        "total_profit_pct": row.get("total_profit_pct"),
        "max_drawdown_pct": row.get("mdd"),
        "payoff_ratio": row.get("payoff_ratio"),
    }
    return {
        "meta": {
            **base_meta,
            "trade_count": row.get("trade_count"),
            "note": "결과 CSV 가 없어 세대 메트릭 요약만 표시합니다(차트/분석 생략).",
        },
        "metrics": fallback_metrics,
        "analysis": {},
        "montecarlo": None,
    }


@backtest_router.get("/report")
def backtest_report_html(
    job_id: str = "",
    t_start: Optional[int] = None,
    t_end: Optional[int] = None,
    run_id: str = "",
    gen_no: Optional[int] = None,
) -> HTMLResponse:
    """자급자족 HTML 리포트(외부 리소스 0). job_id 또는 run_id+gen_no 로 호출.

    - job_id: 완료 잡의 전체 분석+몬테카를로 리포트(t_start/t_end 로 구간 한정 가능).
    - run_id+gen_no: loop_runs.db 세대의 csv_path 로 같은 리포트, CSV 부재 시 축약.
    잡/세대를 못 찾으면 안내 HTML(200)을 반환한다(무예외 — 대시보드 새 탭이 소비).
    """
    payload: Optional[Dict[str, Any]] = None
    if job_id:
        payload = _report_payload_for_job(job_id, t_start, t_end)
    elif run_id and gen_no is not None:
        payload = _report_payload_for_run(run_id, int(gen_no))
    if payload is None:
        notice = {
            "meta": {
                "title": "리포트를 생성할 수 없습니다",
                "note": "해당 job_id 또는 run_id/gen_no 의 결과를 찾을 수 없습니다.",
            }
        }
        return HTMLResponse(content=report.render_report(notice), status_code=200)
    return HTMLResponse(content=report.render_report(payload), status_code=200)


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
