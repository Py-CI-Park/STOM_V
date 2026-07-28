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
import ast
import datetime as _dt_module
import hashlib
import os
import re
import sqlite3
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Set, TypedDict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StringConstraints

from ai_strategy_loop.dashboard import backtest_analysis as analysis
from ai_strategy_loop.dashboard import backtest_report as report
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobSpec, get_job_manager
from ai_strategy_loop.dashboard.security import Capability, close_websocket_failure

# 라이브 잡 WS push 간격(초)·로그 테일 줄 수.
_WS_JOB_INTERVAL_SEC = 1.0
_WS_JOB_LOG_TAIL = 10
_JOB_TERMINAL = ("success", "no_trades", "error", "failed", "timeout", "cancelled", "stale")

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

# ---------------------------------------------------------------- result identity
_RESULT_OPEN_STATUSES = {"success", "no_trades"}
_RESULT_PROBLEM_STATUSES = {"error", "failed", "timeout", "cancelled", "stale"}

def _normalize_condition_code(code: Any) -> str:
    """조건식 identity용 코드 정규화: 개행/공백 차이로 해시가 흔들리지 않게 한다."""
    text = str(code or "").replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.strip().split("\n"))

def _condition_code_hash(code: Any) -> Optional[str]:
    normalized = _normalize_condition_code(code)
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def _lookup_strategy_code(kind: str, name: Any) -> Optional[str]:
    """strategy.db에서 현재 이름에 대응하는 코드를 읽는다. 실패/부재는 None(무예외)."""
    if not name:
        return None
    spec = _KIND_TABLES.get(kind)
    if spec is None:
        return None
    table, name_col, code_col = spec
    con = _connect_strategy(readonly=True)
    if con is None:
        return None
    try:
        row = con.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "{name_col}" = ? LIMIT 1',
            (str(name),),
        ).fetchone()
        return str(row[0]) if row and row[0] is not None else None
    except sqlite3.Error:
        return None
    finally:
        con.close()

def _condition_identity(
    buy_name: Any = "",
    sell_name: Any = "",
    *,
    buy_code: Any = None,
    sell_code: Any = None,
    artifact_note: str = "",
) -> Dict[str, Any]:
    """code-hash-first condition identity. 이름만 있는 legacy evidence는 낮은 신뢰도로 표시한다."""
    resolved_buy = buy_code
    resolved_sell = sell_code
    buy_hash = _condition_code_hash(resolved_buy)
    sell_hash = _condition_code_hash(resolved_sell)
    if buy_hash and sell_hash:
        kind = "code_hash"
        confidence = "high"
        note = artifact_note or "provided_code_snapshot"
    elif buy_hash or sell_hash:
        kind = "code_hash"
        confidence = "medium"
        note = artifact_note or "partial_provided_code_snapshot"
    else:
        kind = "name_only_legacy"
        confidence = "low"
        note = artifact_note or "code_snapshot_missing_name_only_legacy"
    return {
        "kind": kind,
        "buy_name": str(buy_name or ""),
        "sell_name": str(sell_name or ""),
        "buy_hash": buy_hash,
        "sell_hash": sell_hash,
        "display_name": " / ".join(x for x in (str(buy_name or ""), str(sell_name or "")) if x),
        "confidence": confidence,
        "artifact_note": note,
    }

def _resolve_artifact_path(raw: Any) -> Optional[str]:
    if not raw:
        return None
    path = Path(str(raw))
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        return str(path) if path.is_file() else None
    except OSError:
        return None

def _rerun_spec_from_job(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    spec = record.get("spec") if isinstance(record, dict) else None
    if not isinstance(spec, dict):
        return None
    allowed = {
        "buy", "sell", "start", "end", "timeframe", "engines", "timeout", "divid_mode",
        "one_code", "back_db_override", "mode", "param_space", "opt_method", "opt_objective",
        "train_window_days", "test_window_days", "step_days", "sweep_action", "sweep_params",
        "window_days",
    }
    return {k: v for k, v in spec.items() if k in allowed and v not in (None, "")}

def _status_taxonomy(record: Dict[str, Any]) -> Dict[str, Any]:
    """UI가 상태별 open/recover/rerun affordance를 일관되게 그리도록 파생 taxonomy를 만든다."""
    status = str(record.get("status") or "pending")
    phase = str(record.get("phase") or "")
    mode = str((record.get("spec") or {}).get("mode", "backtest") or "backtest")
    csv_exists = _resolve_artifact_path(record.get("csv_path")) is not None
    mode_result = isinstance(record.get("mode_result"), dict) and bool(record.get("mode_result"))
    openable = status == "no_trades" or csv_exists or mode_result
    if phase == "stale" or status == "stale":
        status_kind = "stale"
        artifact_state = "lost_tracking"
    elif openable and status not in _RESULT_OPEN_STATUSES:
        status_kind = "recoverable"
        artifact_state = "artifact_present_status_not_success"
    elif status == "success" and not openable:
        status_kind = "artifact_missing"
        artifact_state = "success_without_openable_artifact"
    elif status in _RESULT_OPEN_STATUSES:
        status_kind = status
        artifact_state = "openable" if openable else "empty_result"
    elif status in _RESULT_PROBLEM_STATUSES:
        status_kind = status
        artifact_state = "terminal_without_openable_artifact"
    else:
        status_kind = status
        artifact_state = "in_progress" if status in ("pending", "running") else "unknown"
    actions: List[str] = []
    if openable:
        actions.append("open_result")
    if csv_exists and status != "no_trades":
        actions.append("open_report")
    if status_kind in {"artifact_missing", "error", "failed", "timeout", "cancelled", "stale", "recoverable"}:
        actions.append("rerun_same_condition")
    if status_kind in {"artifact_missing", "stale", "recoverable"}:
        actions.append("recover_result")
    return {
        "status_kind": status_kind,
        "artifact_state": artifact_state,
        "openable": openable,
        "recoverable": "recover_result" in actions,
        "open_actions": actions,
        "source_type": "job",
        "evidence_id": f"job:{record.get('job_id', '')}",
        "rerun_spec": _rerun_spec_from_job(record),
        "mode": mode,
    }

def _augment_job_payload(record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return record
    spec = record.get("spec") or {}
    out = dict(record)
    out.update(_status_taxonomy(record))
    out["condition_identity"] = _condition_identity(
        spec.get("buy", ""), spec.get("sell", ""),
        buy_code=spec.get("buy_code"),
        sell_code=spec.get("sell_code"),
        artifact_note="job_strategy_code_snapshot" if (spec.get("buy_code") or spec.get("sell_code")) else "job_record_name_only_legacy",
    )
    # 실행 중인 잡만 진행 신호를 본다. `--quiet` CLI 는 진행률을 올려주지 않으므로
    #   프로세스 트리의 디스크/CPU 활동이 유일한 "살아 있는가" 신호다.
    if record.get("status") == "running":
        from ai_strategy_loop.dashboard.backtest_jobs import probe_activity  # noqa: PLC0415

        out["idle_for_sec"] = probe_activity(str(record.get("job_id") or ""), record.get("pid"))
    return out

def _augment_job_listing(payload: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload or {})
    out["jobs"] = [_augment_job_payload(j) for j in out.get("jobs", []) if isinstance(j, dict)]
    out["count"] = len(out["jobs"])
    return out

def _augment_job_result(payload: Dict[str, Any], record: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(payload)
    enriched = _augment_job_payload(record)
    for key in (
        "evidence_id", "source_type", "condition_identity", "status_kind", "artifact_state",
        "openable", "recoverable", "open_actions", "rerun_spec",
    ):
        out[key] = enriched.get(key)
    return out

def _run_condition_identity(row: Dict[str, Any]) -> Dict[str, Any]:
    return _condition_identity(
        row.get("buy_name") or "", row.get("sell_name") or "",
        buy_code=row.get("buy_code"),
        sell_code=row.get("sell_code"),
        artifact_note="run_generation_code_snapshot" if (row.get("buy_code") or row.get("sell_code")) else "run_generation_name_only_legacy",
    )


class HealthResponse(TypedDict):
    status: str
    module: str
    api_version: int


backtest_router = APIRouter(prefix="/bt", tags=["backtest"])

StrategyKind = Literal["buy", "sell", "formula"]
StrategyName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
StrategyCode = Annotated[str, StringConstraints(min_length=1, max_length=100_000)]
ShortText = Annotated[str, StringConstraints(max_length=128)]
PathText = Annotated[str, StringConstraints(max_length=1024)]
MemoText = Annotated[str, StringConstraints(max_length=2_000)]
TagText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class _MutationPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class StrategyValidationPayload(_MutationPayload):
    code: StrategyCode


class StrategyWritePayload(_MutationPayload):
    kind: StrategyKind
    name: StrategyName
    code: StrategyCode
    overwrite: StrictBool = False


class StrategyDeletePayload(_MutationPayload):
    kind: StrategyKind
    name: StrategyName
    confirm: StrategyName


class SweepSpecPayload(_MutationPayload):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    min: int | float
    max: int | float
    step: int | float


class BacktestRunPayload(_MutationPayload):
    buy: StrategyName
    sell: StrategyName
    start: int = Field(ge=20_000_101, le=20_991_231)
    end: int = Field(ge=20_000_101, le=20_991_231)
    timeframe: Literal["tick", "min"] = "min"
    # v5.11.4 — 상한 16 은 코어가 적던 시절의 값이다. 64코어급 워크스테이션에서
    #   전 기간 전종목 백테스트를 돌릴 수 없어 상한만 올린다(기본값 규칙은 불변).
    engines: int = Field(default=4, ge=1, le=64)
    timeout: int = Field(default=600, ge=1, le=86_400)
    divid_mode: ShortText = ""
    one_code: ShortText | None = None
    back_db_override: PathText | None = None
    mode: Literal["backtest", "optimize", "wfo", "sweep"] = "backtest"
    param_space: PathText | None = None
    opt_method: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] = "grid"
    opt_objective: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] = "tpi"
    train_window_days: int = Field(default=0, ge=0, le=3_650)
    test_window_days: int = Field(default=0, ge=0, le=3_650)
    step_days: int = Field(default=0, ge=0, le=3_650)
    sweep_action: Literal["param", "rolling"] = "param"
    sweep_params: PathText | None = None
    sweep_spec: list[SweepSpecPayload] | None = Field(default=None, max_length=8)
    window_days: int = Field(default=0, ge=0, le=3_650)


class JobIdPayload(_MutationPayload):
    job_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class JobMetaPayload(JobIdPayload):
    tags: list[TagText] | None = Field(default=None, max_length=20)
    memo: MemoText | None = None
    favorite: StrictBool | None = None


class PortfolioItemPayload(_MutationPayload):
    job_id: ShortText | None = None
    run_id: ShortText | None = None
    gen_no: int | None = Field(default=None, ge=0, le=1_000_000)
    label: ShortText | None = None


class PortfolioPayload(_MutationPayload):
    items: list[PortfolioItemPayload] = Field(min_length=2, max_length=6)


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


def _gated_json_path(raw: Any) -> Optional[str]:
    """JSON 입력 경로(param_space·sweep_params)를 시세 DB 와 동일 allowlist 로 검증한다.

    빈 값/미지정은 None(미사용). allowlist(_database/·state/) 밖이면 None(호출측이 error
    페이로드로 변환). _validate_back_db_override 와 동일 게이트 — 임의 절대경로 차단.
    """
    if not raw or not str(raw).strip():
        return None
    return _validate_back_db_override(str(raw).strip())


# sweep param 인라인 스펙(빌더 UI) → CLI 가 기대하는 {변수명: [값,...]} dict.
#   cli/sweep.generate_combinations 가 product(*values) 로 데카르트 곱을 만들므로
#   각 변수의 값은 반드시 '명시적 값 리스트'여야 한다(min/max/step 이 아님 — 2026-06-13
#   cli/sweep.py·cli/subcommands._handle_sweep 계약 실측). 빌더의 [min][max][step] 행은
#   여기서 명시 값 리스트로 펼친다.
_SWEEP_MAX_VARS = 8            # 변수 개수 상한(조합 폭발·JSON 비대 방지).
_SWEEP_MAX_VALUES_PER_VAR = 64  # 변수 1개당 값 개수 상한.


def _expand_sweep_range(lo: float, hi: float, step: float) -> List[Any]:
    """[min, max, step] 을 명시적 값 리스트로 펼친다(포함 구간, 부동소수 오차 흡수).

    step<=0 이거나 lo>hi 면 [lo] 단일값(무예외). 정수만 들어오면 정수로, 하나라도 실수면
    실수로 보존한다(CLI 는 값 타입을 그대로 product 에 넣어 BacktestConfig 오버라이드).
    값 개수는 _SWEEP_MAX_VALUES_PER_VAR 로 절단한다(조합 폭발 방지).
    """
    is_int = all(float(v).is_integer() for v in (lo, hi, step))
    if step <= 0 or lo > hi:
        return [int(lo) if is_int else float(lo)]
    values: List[Any] = []
    cur = lo
    # 1e-9 여유로 hi 를 포함(0.1 누적 오차로 마지막 값이 빠지는 것 방지).
    while cur <= hi + 1e-9 and len(values) < _SWEEP_MAX_VALUES_PER_VAR:
        values.append(int(round(cur)) if is_int else round(cur, 10))
        cur += step
    return values


def _build_sweep_spec(rows: Any) -> Optional[Dict[str, List[Any]]]:
    """빌더 행 목록 → {변수명: [값,...]} sweep 스펙(CLI generate_combinations 입력).

    rows: [{"name": str, "min": num, "max": num, "step": num}] 또는 값 리스트를 직접
    담은 [{"name": str, "values": [..]}]. 빈/무효 행은 건너뛴다(무예외). 유효 변수가
    하나도 없으면 None(호출측이 error 페이로드). 변수명 중복은 마지막이 우선.
    """
    if not isinstance(rows, list) or not rows:
        return None
    spec: Dict[str, List[Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "") or "").strip()
        if not name:
            continue
        # 명시 값 리스트가 오면 그대로(숫자만 수용), 아니면 min/max/step 을 펼친다.
        if isinstance(row.get("values"), list):
            vals: List[Any] = []
            for v in row["values"][:_SWEEP_MAX_VALUES_PER_VAR]:
                if isinstance(v, bool):
                    continue  # bool 은 숫자 아님(파라미터 값으로 부적절).
                if isinstance(v, (int, float)):
                    vals.append(v)
                else:
                    try:
                        fv = float(str(v).strip())
                        vals.append(int(fv) if fv.is_integer() else fv)
                    except (TypeError, ValueError):
                        continue
            if vals:
                spec[name] = vals
            if len(spec) >= _SWEEP_MAX_VARS:
                break
            continue
        try:
            lo = float(row.get("min"))
            hi = float(row.get("max"))
            step = float(row.get("step"))
        except (TypeError, ValueError):
            continue
        spec[name] = _expand_sweep_range(lo, hi, step)
        if len(spec) >= _SWEEP_MAX_VARS:
            break
    return spec or None


def _write_sweep_spec_file(spec: Dict[str, List[Any]]) -> Optional[str]:
    """sweep 스펙 dict 를 게이트된 _database/ 하위 임시 JSON 으로 쓰고 경로를 반환한다.

    CLI 는 --params <파일경로> 만 받으므로 인라인 스펙을 파일로 직렬화해야 한다. 기존
    allowlist(_database/) 안에 쓰므로 sweep_params 게이트(_gated_json_path)를 그대로
    통과한다. IO 실패면 None(무예외 — 호출측이 error 페이로드). 파일명은 충돌 방지용
    타임스탬프+난수.
    """
    import json as _json
    import time as _time
    import uuid as _uuid

    if not isinstance(spec, dict) or not spec:
        return None
    sweep_dir = _DATABASE_DIR / "webbt_sweep"
    try:
        sweep_dir.mkdir(parents=True, exist_ok=True)
        fname = f"sweep_{_time.strftime('%Y%m%d_%H%M%S')}_{_uuid.uuid4().hex[:8]}.json"
        target = sweep_dir / fname
        with open(target, "w", encoding="utf-8") as fh:
            _json.dump(spec, fh, ensure_ascii=False)
        # 작성한 파일이 sweep_params 게이트(_database/ 하위)를 통과하는지 자기검증.
        return _gated_json_path(str(target))
    except OSError:
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
        return {
            "status": "error",
            "reason": "strategy_db_unavailable",
            "message": "전략 DB 조회 실패: strategy.db 연결 실패",
            "items": [],
            "count": 0,
            "kind": kind,
        }
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
    except sqlite3.Error as exc:
        return {
            "status": "error",
            "reason": f"strategy_list_failed: {exc}",
            "message": "전략 DB 조회 실패: 조건식 목록을 읽을 수 없습니다.",
            "items": [],
            "count": 0,
            "kind": kind,
        }
    finally:
        con.close()
    items.sort(key=lambda r: r["name"])
    return {"status": "ok", "items": items, "count": len(items), "kind": kind}


def _looks_ailoop(name: str) -> bool:
    """AI 루프 생성 전략 휴리스틱(이름 접두/패턴)."""
    markers = ("AUTO", "Auto_", "gen", "reframe", "_g", "TMP", "Study")
    return any(marker in name for marker in markers)


@backtest_router.get("/strategy")
def get_strategy(kind: str = "buy", name: str = "") -> Dict[str, Any]:
    """단일 조건식 코드 전문을 반환한다. 없으면 available=False."""
    spec = _KIND_TABLES.get(kind)
    if spec is None or not name:
        return {
            "available": False,
            "status": "error",
            "reason": "invalid_kind_or_name",
            "message": "조건식 종류와 이름이 필요합니다.",
            "name": name,
            "code": "",
        }
    table, name_col, code_col = spec
    con = _connect_strategy(readonly=True)
    if con is None:
        return {
            "available": False,
            "status": "error",
            "reason": "strategy_db_unavailable",
            "message": "전략 DB 조회 실패: strategy.db 연결 실패",
            "name": name,
            "code": "",
            "kind": kind,
        }
    try:
        row = con.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "{name_col}" = ?', (name,)
        ).fetchone()
    except sqlite3.Error as exc:
        return {
            "available": False,
            "status": "error",
            "reason": f"strategy_lookup_failed: {exc}",
            "message": "전략 DB 조회 실패: 조건식 코드를 읽을 수 없습니다.",
            "name": name,
            "code": "",
            "kind": kind,
        }
    finally:
        con.close()
    if row is None:
        return {
            "available": False,
            "status": "missing",
            "reason": "strategy_not_found",
            "message": "조건식을 찾을 수 없습니다.",
            "name": name,
            "code": "",
            "kind": kind,
        }
    return {"available": True, "status": "ok", "reason": "", "name": name, "code": str(row[0] or ""), "kind": kind}


@backtest_router.post("/strategy/validate")
def validate_strategy_code(payload: StrategyValidationPayload) -> Dict[str, Any]:
    """저장 없이 compile() 문법 검증. {ok, error?}."""
    return _compile_check(payload.code)


# ---------------------------------------------------------------- variables SSOT
# 전략 변수 SSOT(단일 진실 공급원) — 한글 식별자 추출 + 화이트리스트 대조에 쓴다.
#   변수 키워드 칩(트랙 B ①)이 이 어휘로 코드의 한글 변수를 식별/배지 표시한다.
_VARIABLES_REF = (
    REPO_ROOT / "utility" / "ai_agent" / "system_prompt" / "v1" / "variables_reference.md"
)
# 백틱 인라인 코드 토큰(함수형 이름) — test_ai_dictionary 와 동일 정규식.
_INLINE_CODE_TOKEN = re.compile(r"`([0-9A-Za-z_가-힣]+)`")
# 한글이 1자 이상 포함된 식별자(코드에서 한글 변수만 추출 — ASCII-only 토큰 제외).
_HANGUL_IDENT = re.compile(r"[0-9A-Za-z_가-힣]*[가-힣][0-9A-Za-z_가-힣]*")
# variables_reference.md 의 "- 변수명 — 설명" / "- 변수명, 변수명 ..." 줄에서 스칼라 변수명 추출.
_SCALAR_BULLET = re.compile(r"^\s*-\s+(.+)$")

_SSOT_CACHE: Optional[Set[str]] = None


def _load_ssot_vocabulary() -> Set[str]:
    """variables_reference.md 에서 전략 변수 어휘 집합을 만든다(백틱 함수형 + 스칼라 불릿).

    프로세스 생애 1회 캐시(SSOT 파일은 런타임 불변). 파일 부재/IO 실패면 빈 집합(무예외).
    백틱 토큰은 함수형 화이트리스트(181개), 불릿의 콤마/공백 분리 한글 토큰은 스칼라 변수다.
    """
    global _SSOT_CACHE
    if _SSOT_CACHE is not None:
        return _SSOT_CACHE
    vocab: Set[str] = set()
    try:
        text = _VARIABLES_REF.read_text(encoding="utf-8")
    except OSError:
        _SSOT_CACHE = vocab
        return vocab
    # 함수형 이름(백틱).
    vocab.update(_INLINE_CODE_TOKEN.findall(text))
    # 스칼라/잔고 변수 — 불릿 줄의 한글 식별자 토큰(설명 텍스트의 한글은 어휘 오염이 되지만,
    #   추출은 '코드 안의 한글 식별자가 어휘에 있는지' 멤버십 판정에만 쓰므로 false-negative
    #   를 줄이는 방향이 안전하다 — 미지 변수만 'SSOT 외'로 표시되면 충분).
    for line in text.splitlines():
        m = _SCALAR_BULLET.match(line)
        if not m:
            continue
        # 불릿 본문에서 한글 식별자만 뽑는다(예: "현재가 — 현재 틱의 현재가" → 현재가, 현재, 틱…).
        for tok in _HANGUL_IDENT.findall(m.group(1)):
            if len(tok) >= 2:
                vocab.add(tok)
    _SSOT_CACHE = vocab
    return vocab


@backtest_router.get("/variables")
def list_variables() -> Dict[str, Any]:
    """전략 변수 SSOT 어휘 목록(정렬) + 개수. 변수 키워드 칩 패널이 소비한다."""
    vocab = _load_ssot_vocabulary()
    return {"variables": sorted(vocab), "count": len(vocab)}


@backtest_router.post("/extract_vars")
def extract_variables(payload: StrategyValidationPayload) -> Dict[str, Any]:
    """전략 코드에서 한글 식별자를 추출하고 SSOT 화이트리스트 멤버십을 판정한다.

    {code} → {known:[{name,count}], unknown:[{name,count}]}. known 은 SSOT 어휘에 있는
    한글 변수(칩 청록), unknown 은 어휘 밖(칩 경고). Python 키워드/주석은 식별자 추출
    특성상 제외된다(한글 키워드 없음). 무예외(빈 코드→빈 목록).
    """
    code = payload.code
    vocab = _load_ssot_vocabulary()
    counts: Dict[str, int] = {}
    for tok in _HANGUL_IDENT.findall(code):
        if len(tok) >= 2:
            counts[tok] = counts.get(tok, 0) + 1
    known: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
    for name in sorted(counts):
        entry = {"name": name, "count": counts[name]}
        (known if name in vocab else unknown).append(entry)
    return {"known": known, "unknown": unknown, "total": len(counts)}


def _safe_literal_eval_node(node: ast.AST) -> Any:
    """Return ast.literal_eval(node) or None without executing strategy code."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return None


def _self_vars_row(index: Any, entry: Any) -> Optional[Dict[str, Any]]:
    """Convert one legacy self.vars entry into a semantic sweep-builder row.

    Legacy GUI optimization stores values like ``self.vars[0] = [[10, 30, 5], 20]``
    or ``self.vars = {0: [[10, 30, 5], 20]}``. The web dashboard previews that
    structure only; it never exec()'s arbitrary strategy code.
    """
    if isinstance(index, bool):
        return None
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return None
    if not isinstance(entry, (list, tuple)) or len(entry) != 2:
        return None
    rng, default = entry
    if not isinstance(rng, (list, tuple)) or len(rng) != 3:
        return None
    try:
        lo, hi, step = (float(rng[0]), float(rng[1]), float(rng[2]))
    except (TypeError, ValueError):
        return None
    if step == 0:
        return None

    def norm(v: float) -> Any:
        return int(v) if float(v).is_integer() else v

    return {
        "index": idx,
        "name": f"self.vars[{idx}]",
        "min": norm(lo),
        "max": norm(hi),
        "step": norm(step),
        "default": default,
    }


def _self_vars_roundtrip_code(rows: List[Dict[str, Any]]) -> str:
    payload = {
        int(r["index"]): [[r["min"], r["max"], r["step"]], r.get("default")]
        for r in rows
        if isinstance(r, dict) and r.get("index") is not None
    }
    return "self.vars = " + repr(payload) if payload else ""


def _extract_self_vars_rows(code: str) -> Dict[str, Any]:
    """Safely parse legacy self.vars range declarations for sweep preview."""
    rows: Dict[int, Dict[str, Any]] = {}
    refs: List[str] = []
    try:
        tree = ast.parse(str(code or ""))
    except SyntaxError as exc:
        return {
            "available": False,
            "adapter": "self.vars-range-preview",
            "rows": [],
            "refs": [],
            "message": f"전략 코드 구문 오류로 self.vars를 해석할 수 없습니다: {exc}",
            "reversible": False,
            "roundtrip_available": False,
            "roundtrip_code": "",
            "exec_used": False,
        }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
                and target.attr == "vars"
            ):
                literal = _safe_literal_eval_node(node.value)
                if isinstance(literal, dict):
                    for k, v in literal.items():
                        row = _self_vars_row(k, v)
                        if row:
                            rows[int(row["index"])] = row
                            refs.append(f"self.vars[{row['index']}]")
            elif (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "self"
                and target.value.attr == "vars"
            ):
                idx_node = target.slice
                if isinstance(idx_node, ast.Index):  # pragma: no cover - py<3.9 compatibility.
                    idx_node = idx_node.value
                idx = _safe_literal_eval_node(idx_node)
                entry = _safe_literal_eval_node(node.value)
                row = _self_vars_row(idx, entry)
                if row:
                    rows[int(row["index"])] = row
                    refs.append(f"self.vars[{row['index']}]")

    ordered = [rows[k] for k in sorted(rows)]
    roundtrip_code = _self_vars_roundtrip_code(ordered)
    return {
        "available": bool(ordered),
        "adapter": "self.vars-range-preview",
        "rows": ordered,
        "refs": sorted(set(refs)),
        "message": (
            f"self.vars {len(ordered)}개를 스윕 빌더 행으로 변환할 수 있습니다."
            if ordered else "실행 없이 해석 가능한 self.vars 범위 선언이 없습니다."
        ),
        "reversible": bool(roundtrip_code),
        "roundtrip_available": bool(roundtrip_code),
        "roundtrip_code": roundtrip_code,
        "exec_used": False,
    }


def _strategy_lookup_for_name(kind: str, name: str) -> Dict[str, Any]:
    """Read one strategy code with explicit lookup status for legacy preview tools."""
    spec = _KIND_TABLES.get(kind)
    if spec is None or not name:
        return {"available": False, "status": "error", "reason": "invalid_kind_or_name", "code": ""}
    table, name_col, code_col = spec
    con = _connect_strategy(readonly=True)
    if con is None:
        return {"available": False, "status": "error", "reason": "strategy_db_unavailable", "code": ""}
    try:
        row = con.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "{name_col}" = ? LIMIT 1',
            (str(name),),
        ).fetchone()
    except sqlite3.Error as exc:
        return {"available": False, "status": "error", "reason": f"strategy_lookup_failed: {exc}", "code": ""}
    finally:
        con.close()
    if not row:
        return {"available": False, "status": "missing", "reason": "strategy_not_found", "code": ""}
    code = str(row[0] or "")
    if not code.strip():
        return {"available": False, "status": "empty_code", "reason": "strategy_code_empty", "code": ""}
    return {"available": True, "status": "ok", "reason": "", "code": code}


def _strategy_code_for_name(kind: str, name: str) -> str:
    got = _strategy_lookup_for_name(kind, name)
    return str(got.get("code", "") or "") if got.get("available") else ""


@backtest_router.get("/legacy/self_vars")
def legacy_self_vars(kind: str = "buy", name: str = "") -> Dict[str, Any]:
    """Preview legacy self.vars ranges with semantic round-trip metadata."""
    if kind not in ("buy", "sell") or not name:
        return {
            "available": False,
            "adapter": "self.vars-range-preview",
            "rows": [],
            "refs": [],
            "message": "매수/매도 조건식 이름이 필요합니다.",
            "reversible": False,
            "exec_used": False,
            "roundtrip_available": False,
            "roundtrip_code": "",
        }
    lookup = _strategy_lookup_for_name(kind, name)
    if lookup.get("status") != "ok":
        return {
            "available": False,
            "status": lookup.get("status"),
            "reason": lookup.get("reason"),
            "adapter": "self.vars-range-preview",
            "rows": [],
            "refs": [],
            "message": (
                "전략 DB 조회 실패로 self.vars를 해석할 수 없습니다."
                if lookup.get("status") == "error" else "조건식을 찾을 수 없거나 코드가 비어 있습니다."
            ),
            "reversible": False,
            "exec_used": False,
            "roundtrip_available": False,
            "roundtrip_code": "",
            "kind": kind,
            "name": name,
        }
    out = _extract_self_vars_rows(str(lookup.get("code", "")))
    out.update({"kind": kind, "name": name, "status": "ok"})
    return out


def _literal_list_count(node: ast.AST) -> Optional[int]:
    if isinstance(node, (ast.List, ast.Tuple)):
        return len(node.elts)
    value = _safe_literal_eval_node(node)
    if isinstance(value, (list, tuple)):
        return len(value)
    return None


def _extract_backfinder_preconditions(code: str) -> Dict[str, Any]:
    """Check BackFinder-only self.tickcols/self.tickdata declarations without running code."""
    has_cols = False
    has_data = False
    cols_count: Optional[int] = None
    data_count: Optional[int] = None
    try:
        tree = ast.parse(str(code or ""))
    except SyntaxError as exc:
        return {
            "precondition_ok": False,
            "has_tickcols": False,
            "has_tickdata": False,
            "cols_count": None,
            "data_count": None,
            "run_enabled": False,
            "message": f"전략 코드 구문 오류로 백파인더 사전 점검을 할 수 없습니다: {exc}",
        }

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                if target.attr == "tickcols":
                    has_cols = True
                    cols_count = _literal_list_count(node.value)
                elif target.attr == "tickdata":
                    has_data = True
                    data_count = _literal_list_count(node.value)

    if not has_cols or not has_data:
        return {
            "precondition_ok": False,
            "has_tickcols": has_cols,
            "has_tickdata": has_data,
            "cols_count": cols_count,
            "data_count": data_count,
            "run_enabled": False,
            "message": "self.tickcols와 self.tickdata가 모두 있어야 백파인더용 전략입니다.",
        }
    if cols_count is None or data_count is None:
        return {
            "precondition_ok": False,
            "has_tickcols": has_cols,
            "has_tickdata": has_data,
            "cols_count": cols_count,
            "data_count": data_count,
            "run_enabled": False,
            "message": "self.tickcols/self.tickdata는 실행 없이 해석 가능한 리스트 리터럴이어야 합니다.",
        }
    ok = cols_count == data_count
    return {
        "precondition_ok": ok,
        "has_tickcols": has_cols,
        "has_tickdata": has_data,
        "cols_count": cols_count,
        "data_count": data_count,
        "run_enabled": False,
        "message": (
            "백파인더 사전 조건 통과 — 현재 웹 UI는 안전 점검만 제공하고 원본 GUI 실행은 연결하지 않습니다."
            if ok else "self.tickcols의 개수와 self.tickdata의 개수가 일치하지 않습니다."
        ),
    }


@backtest_router.get("/backfinder/preflight")
def backfinder_preflight(kind: str = "buy", name: str = "") -> Dict[str, Any]:
    """BackFinder staged UI preflight; validates self.tickcols/tickdata before any run wiring."""
    if kind not in ("buy", "sell") or not name:
        return {
            "available": False,
            "kind": kind,
            "name": name,
            "precondition_ok": False,
            "has_tickcols": False,
            "has_tickdata": False,
            "cols_count": None,
            "data_count": None,
            "run_enabled": False,
            "message": "매수/매도 조건식 이름이 필요합니다.",
        }
    lookup = _strategy_lookup_for_name(kind, name)
    if lookup.get("status") != "ok":
        return {
            "available": False,
            "status": lookup.get("status"),
            "reason": lookup.get("reason"),
            "kind": kind,
            "name": name,
            "precondition_ok": False,
            "has_tickcols": False,
            "has_tickdata": False,
            "cols_count": None,
            "data_count": None,
            "run_enabled": False,
            "message": (
                "전략 DB 조회 실패로 백파인더 사전 점검을 할 수 없습니다."
                if lookup.get("status") == "error" else "조건식을 찾을 수 없거나 코드가 비어 있습니다."
            ),
        }
    out = _extract_backfinder_preconditions(str(lookup.get("code", "")))
    out.update({"available": True, "status": "ok", "kind": kind, "name": name})
    return out


def _compile_check(code: str) -> Dict[str, Any]:
    if not code.strip():
        return {"ok": False, "error": "전략 코드가 비어있습니다."}
    try:
        compile(code, "<strategy>", "exec")
    except SyntaxError as exc:
        return {"ok": False, "error": f"구문 오류: {exc}"}
    return {"ok": True, "error": None}


@backtest_router.post("/strategy")
def save_strategy(payload: StrategyWritePayload) -> Dict[str, Any]:
    """조건식 생성/수정 — compile() 검증 후 INSERT OR REPLACE.

    overwrite=false 인데 동일 이름이 이미 있으면 status='error'/code='exists' (HTTP 200,
    무예외 컨벤션). buy/sell 은 PK 충돌을 REPLACE 로 처리. formula 는 PK 가 없어
    수식명 기준으로 DELETE+INSERT(중복 방지).
    """
    kind = payload.kind
    name = payload.name
    code = payload.code
    overwrite = payload.overwrite

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
def delete_strategy(payload: StrategyDeletePayload) -> Dict[str, Any]:
    """조건식 삭제(실수 방지: confirm 에 이름 재입력 필수)."""
    kind = payload.kind
    name = payload.name
    confirm = payload.confirm

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
def run_backtest(payload: BacktestRunPayload) -> Dict[str, Any]:
    """백테스트 잡 시작 → {job_id}. 이름/날짜 검증은 잡 매니저가 수행."""
    one_code = payload.one_code
    divid_mode = payload.divid_mode.strip() or (
        "한종목 로딩" if one_code else "종목코드별 분류"
    )
    back_db_override = _gated_json_path(payload.back_db_override)
    if payload.back_db_override and back_db_override is None:
        return {
            "status": "error",
            "message": "back_db_override 는 _database/ 또는 ai_strategy_loop/state/ 하위 경로만 허용됩니다.",
        }
    param_space = _gated_json_path(payload.param_space)
    if payload.param_space and param_space is None:
        return {
            "status": "error",
            "message": "param_space 는 _database/ 또는 ai_strategy_loop/state/ 하위 경로만 허용됩니다.",
        }
    sweep_params = _gated_json_path(payload.sweep_params)
    if payload.sweep_params and sweep_params is None:
        return {
            "status": "error",
            "message": "sweep_params 는 _database/ 또는 ai_strategy_loop/state/ 하위 경로만 허용됩니다.",
        }
    if not sweep_params and payload.sweep_spec is not None:
        rows = [row.model_dump() for row in payload.sweep_spec]
        spec_dict = _build_sweep_spec(rows)
        if spec_dict is None:
            return {
                "status": "error",
                "message": "sweep 스펙이 비었습니다 — 변수명·범위(min/max/step)가 있는 행이 1개 이상 필요합니다.",
            }
        sweep_params = _write_sweep_spec_file(spec_dict)
        if sweep_params is None:
            return {
                "status": "error",
                "message": "sweep 스펙 임시 파일 생성에 실패했습니다.",
            }
    # 없는 조건식으로는 잡을 만들지 않는다. 이전에는 그대로 실행돼 CLI 가 0.05초 만에
    #   exit=1 로 죽었고, 화면에는 종료 기록만 쌓여 "결과가 왜 없냐"로 읽혔다.
    #   (2026-07-26 전수 조사: 잡 333건 전부 이미 삭제된 `기존매수`/`기존매도` 참조)
    buy_code = _lookup_strategy_code("buy", payload.buy)
    sell_code = _lookup_strategy_code("sell", payload.sell)
    missing = [
        label for label, name, code in (
            ("매수", payload.buy, buy_code),
            ("매도", payload.sell, sell_code),
        )
        if not code
    ]
    if missing:
        names = " · ".join(
            f"{label} '{payload.buy if label == '매수' else payload.sell}'" for label in missing
        )
        return {
            "status": "error",
            "code": "strategy_not_found",
            "message": (
                f"{names} 조건식을 라이브러리에서 찾을 수 없습니다. "
                "조건식 편집 탭에서 현재 저장된 이름을 다시 선택하세요."
            ),
        }

    # 백테스트 엔진은 거래일 수보다 많은 엔진을 쓸 수 없다(엔진이 "일자 수가 엔진 수보다
    #   적습니다"로 즉시 실패한다). 사용자의 의도는 "이 백테스트를 돌린다"이지 엔진 수가
    #   아니므로 막지 않고 조용히 낮춘 뒤, 무엇을 왜 바꿨는지 응답으로 알린다.
    engines = payload.engines
    engine_note = ""
    day_count = _trading_days_in_range(payload.timeframe, payload.start, payload.end)
    if day_count is not None and 0 < day_count < engines:
        engine_note = (
            f"엔진 수를 {engines} → {day_count}로 낮췄습니다. "
            f"이 기간의 거래일이 {day_count}일이라 엔진을 그보다 많이 쓸 수 없습니다."
        )
        engines = day_count

    spec = BacktestJobSpec(
        buy=payload.buy,
        sell=payload.sell,
        start=payload.start,
        end=payload.end,
        buy_code=buy_code,
        sell_code=sell_code,
        timeframe=payload.timeframe,
        engines=engines,
        timeout=payload.timeout,
        divid_mode=divid_mode,
        one_code=one_code,
        back_db_override=back_db_override,
        mode=payload.mode,
        param_space=param_space,
        opt_method=payload.opt_method,
        opt_objective=payload.opt_objective,
        train_window_days=payload.train_window_days,
        test_window_days=payload.test_window_days,
        step_days=payload.step_days,
        sweep_action=payload.sweep_action,
        sweep_params=sweep_params,
        window_days=payload.window_days,
    )
    result = get_job_manager().submit(spec)
    if engine_note and isinstance(result, dict) and result.get("status") == "ok":
        result["engine_note"] = engine_note
    return result



def _trading_days_in_range(timeframe: str, start: int, end: int) -> Optional[int]:
    """기간 내 보유 일일 DB 거래일 수. 인벤토리 자체가 비면 None(판단 불가 — 건드리지 않음).

    일일 DB 가 하나도 없는 환경(테스트·신규 설치)에서 잘못 막지 않도록, 인벤토리가
    비었을 때는 아무 판단도 하지 않는다.
    """
    try:
        from ai_strategy_loop.dashboard.simulation_api import _daily_db_dates  # noqa: PLC0415

        prefix = "stock_tick" if str(timeframe) == "tick" else "stock_min"
        days = _daily_db_dates(prefix)
    except Exception:  # noqa: BLE001 - 인벤토리 조회 실패는 판단 불가로 흡수.
        return None
    if not days:
        return None
    return sum(1 for d in days if int(start) <= int(d) <= int(end))


@backtest_router.get("/trading_days")
def trading_days(timeframe: str = "min", start: int = 0, end: int = 0) -> Dict[str, Any]:
    """기간 내 보유 거래일 수 — 실행 전에 엔진 수 상한을 화면이 알 수 있게 한다."""
    count = _trading_days_in_range(timeframe, start, end)
    return {
        "timeframe": "tick" if str(timeframe) == "tick" else "min",
        "start": start,
        "end": end,
        # None 이면 인벤토리를 알 수 없다는 뜻 — 화면은 상한을 강제하지 않는다.
        "days": count,
        "max_engines": None if count is None else max(1, count),
    }

@backtest_router.get("/jobs")
def list_jobs() -> Dict[str, Any]:
    """모든 잡(최신순)."""
    return _augment_job_listing(get_job_manager().list_jobs())


@backtest_router.get("/job")
def get_job(job_id: str = "") -> Dict[str, Any]:
    """잡 상태 + 진행률 + 로그 테일(마지막 50줄)."""
    if not job_id:
        return {"available": False, "job_id": job_id}
    return _augment_job_payload(get_job_manager().get(job_id))


@backtest_router.post("/job/cancel")
def cancel_job(payload: JobIdPayload) -> Dict[str, Any]:
    """잡 취소(대기 중이면 큐 제거, 실행 중이면 프로세스 회수)."""
    return get_job_manager().cancel(payload.job_id)


@backtest_router.post("/job/meta")
def update_job_meta(payload: JobMetaPayload) -> Dict[str, Any]:
    """잡 결과 메타(태그·메모·즐겨찾기) 부분 갱신 — 결과 체계 관리(트랙 B ③).

    {job_id, tags?(list[str]), memo?(str), favorite?(bool)}. 미포함 키는 미변경.
    잡 없음/잘못된 타입은 무예외 error 페이로드(HTTP 200, 대시보드 컨벤션).
    """
    result = get_job_manager().update_meta(
        payload.job_id,
        tags=payload.tags,
        memo=payload.memo,
        favorite=payload.favorite,
    )
    if not result.get("available"):
        return {"status": "error", "message": "job_id 없음", "job_id": payload.job_id}
    return {"status": "ok", **result}


# --------------------------------------------------------------------- result
@backtest_router.get("/result")
def get_result(
    job_id: str = "",
    t_start: Optional[int] = None,
    t_end: Optional[int] = None,
    run_id: str = "",
    gen_no: Optional[int] = None,
    demo: int = 0,
) -> Dict[str, Any]:
    """완료 잡 또는 진화 세대의 metrics + 분석 전체 묶음. 없음이면 available=False.

    호출 경로(셋 중 하나):
      - demo=1: 합성 예시 결과(잡 미선택 기본 화면 — 빈 화면 금지, 트랙 B ④). is_demo:true.
      - job_id: 완료 잡 결과(t_start/t_end 로 구간 한정 가능 — 브러시).
      - run_id+gen_no: loop_runs.db 세대 결과(잡과 동일 스키마, CSV 부재 시 축약).
    no_trades 잡은 metrics=None, analysis=빈 구조로 정상 반환(에러 아님).
    """
    # 데모 경로 — 잡/세대 없이 합성 거래로 풀 분석을 만든다(분석 전 키 포함).
    #   sentinel job_id("__demo__") 도 데모로 라우팅한다(프론트 BtResultArea 가 job_id 만
    #   URL 에 싣고 호출하므로, 별도 charts 수정 없이 기본 화면 예시 렌더를 가능케 한다).
    if demo or job_id == _DEMO_JOB_ID:
        return _demo_result()
    # 진화 세대 경로 — 잡 매니저를 거치지 않고 loop_runs.db(읽기 전용)에서 직접.
    if not job_id and run_id and gen_no is not None:
        return _result_for_run(run_id, int(gen_no), t_start, t_end)
    manager = get_job_manager()
    record = manager.get(job_id, log_tail=0)
    if not record.get("available"):
        return {"available": False, "job_id": job_id}
    status = record.get("status")
    csv_path = record.get("csv_path")
    spec = record.get("spec") or {}
    mode = str(spec.get("mode", "backtest") or "backtest")
    # wfo/sweep 모드 — csv 단일 분석 대신 구조화 결과(윈도우별/조합별 표)를 반환한다.
    if mode in ("wfo", "sweep"):
        return _augment_job_result({
            "available": True,
            "job_id": job_id,
            "status": status,
            "mode": mode,
            "mode_result": record.get("mode_result"),
            "message": record.get("message", ""),
        }, record)
    # no_trades 는 csv_path 없이 정상 종결 — 빈 분석 구조를 반환한다.
    if status == "no_trades":
        return _augment_job_result({
            "available": True,
            "job_id": job_id,
            "status": status,
            "metrics": None,
            "analysis": analysis.full_analysis(None),
            "message": record.get("message", ""),
        }, record)
    bundle = analysis.full_analysis(csv_path, t_start, t_end)
    ranged = t_start is not None or t_end is not None
    return _augment_job_result({
        "available": True,
        "job_id": job_id,
        "status": status,
        # 구간 분석 시 metrics 는 CLI 전체 메트릭 대신 구간 summary 로 대체(카드 동기).
        "metrics": bundle["summary"] if ranged else record.get("metrics"),
        "analysis": bundle,
        "ranged": ranged,
    }, record)


def _analysis_for_job(
    job_id: str, t_start: Optional[int] = None, t_end: Optional[int] = None
) -> List[Dict[str, Any]]:
    """잡 결과 CSV → trades 리스트(분석 개별 엔드포인트 공용, 옵션 매수시간 범위 필터)."""
    csv_path = get_job_manager().result_csv_path(job_id)
    trades = analysis.load_trades_csv(csv_path)
    return analysis.filter_trades(trades, t_start, t_end)


def _analysis_for_run(
    run_id: str, gen_no: int, t_start: Optional[int] = None, t_end: Optional[int] = None
) -> List[Dict[str, Any]]:
    """진화 세대 CSV → trades 리스트(잡과 동일 계약). 세대/CSV 없음이면 빈 목록(무예외).

    세대 결과도 잡과 같은 거래 CSV 를 남기므로 몬테카를로·구간 분석 입력 표본이 실제로
    존재한다. 이 헬퍼가 없던 동안 세대 결과는 '표본 없음'으로 잘못 안내됐다.
    """
    row = _gen_row_readonly(run_id, int(gen_no))
    if row is None:
        return []
    csv_path = _resolve_gen_csv(row)
    if not csv_path:
        return []
    trades = analysis.load_trades_csv(csv_path)
    return analysis.filter_trades(trades, t_start, t_end)


# --------------------------------------------------------------- evo (run/gen)
def _gen_row_readonly(run_id: str, gen_no: int) -> Optional[Dict[str, Any]]:
    """loop_runs.db(읽기 전용) 에서 (run_id, gen_no) 세대 한 행을 dict로 읽는다.

    LoopState(readonly=True) 는 mode=ro URI 로만 열어 보호된 loop_runs.db 에 어떤
    쓰기(WAL 생성·스키마 마이그레이션·디렉토리 생성)도 하지 않는다. DB 부재/조회
    실패/세대 없음은 None(무예외 — 호출측이 available=False 로 표준화).
    """
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    try:
        st = LoopState(readonly=True)
        for r in st.get_generations(run_id):
            if int(r.get("gen_no", -1)) == int(gen_no):
                return r
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 None(무예외).
        return None
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass
    return None


def _opt_metric(value: Any) -> Optional[float]:
    """세대 행 메트릭을 Optional[float]로 정규화한다(None/비숫자→None, 숫자→float).

    None(미측정)은 그대로 None으로 전파해 '미측정'과 '실제 0%'를 구분한다(대시보드가
    손실 세대를 0%로 오표시하지 않도록). 비숫자(손상 행)도 None으로 흡수(무예외).
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _annualize_pct(return_pct: Optional[float], calendar_days: Optional[int]) -> Optional[float]:
    """기간 수익률(%) → 연환산 수익률(%). 기간/입력이 부실하면 None(추정 금지).

    복리 환산: (1+r)^(365/days) - 1. days<20 이면 표본이 짧아 연환산이 과장되므로
    계산하지 않는다(대시보드가 '기간 짧음'으로 표시).
    """
    if return_pct is None or not calendar_days or int(calendar_days) < 20:
        return None
    try:
        growth = 1.0 + float(return_pct) / 100.0
        if growth <= 0.0:  # 원금 전손 이상 — 연환산 정의 불가.
            return None
        return (growth ** (365.0 / float(calendar_days)) - 1.0) * 100.0
    except (ValueError, TypeError, OverflowError, ZeroDivisionError):
        return None


def _result_context(row: Dict[str, Any], run_id: str, gen_no: int,
                    summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """결과 요약 상단에 붙는 '이 결과가 무엇인지' 블록(v5.13.2).

    "언제 실행했고 어떤 연구의 몇 세대이며 어느 기간을 어떤 타임프레임으로 돌렸는지"를
    한 곳에 모은다. 수익률은 의미가 다른 두 값을 분리해 싣는다:
      - return_on_capital_pct : 운용자본 대비 수익률(loop 채점기 기준, 진짜 수익률)
      - sum_trade_return_pct  : 거래별 수익률 단순 합(참고치 — 자본 대비가 아님)
    이 둘이 같은 이름(total_profit_pct)으로 섞여 65.36% vs 32.71% 처럼 보이던 혼선을 끝낸다.
    """
    summary = summary or {}
    created = row.get("created_at")
    executed_at_iso: Optional[str] = None
    try:
        if created:
            executed_at_iso = _dt_module.datetime.fromtimestamp(float(created)).isoformat(timespec="seconds")
    except (ValueError, TypeError, OSError):
        executed_at_iso = None

    return_krw = _opt_metric(row.get("profit"))
    return_on_capital = _opt_metric(row.get("total_profit_pct"))
    capital_krw: Optional[float] = None
    if return_krw is not None and return_on_capital not in (None, 0):
        capital_krw = return_krw / return_on_capital * 100.0
    calendar_days = summary.get("calendar_days") or 0
    return {
        "run_id": run_id,
        "gen_no": int(gen_no),
        "research_label": row.get("strategy_gist") or "",
        "buy_name": row.get("buy_name") or "",
        "sell_name": row.get("sell_name") or "",
        "executed_at": executed_at_iso,
        "executed_at_unix": float(created) if created else None,
        "timeframe": summary.get("timeframe") or "unknown",
        "period_start": summary.get("period_start"),
        "period_end": summary.get("period_end"),
        "calendar_days": calendar_days,
        "trading_days": summary.get("trading_days") or 0,
        "capital_krw": capital_krw,
        "return_krw": return_krw,
        "return_on_capital_pct": return_on_capital,
        # v5.13.2 — MDD 도 두 정의가 같은 이름으로 섞여 있었다(같은 세대에서 2.16% vs 47.53%).
        #   generations.mdd  : 자본 대비 낙폭(엔진/채점기 정의) ← 명예의 전당이 쓰는 값
        #   summary.max_drawdown_pct : 누적 실현손익 '고점 대비 반납률'(CSV 파생)
        #   둘 다 유효하지만 묻는 질문이 다르므로 이름을 갈라 함께 싣는다.
        "mdd_on_capital_pct": _opt_metric(row.get("mdd")),
        "sum_trade_return_pct": summary.get("sum_trade_return_pct"),
        "annual_return_pct": _annualize_pct(return_on_capital, calendar_days),
        "gate_passed": bool(row.get("gate_passed")),
        "score": _opt_metric(row.get("score")),
        "status": row.get("status"),
    }


def _resolve_gen_csv(row: Dict[str, Any]) -> Optional[str]:
    """세대 행의 csv_path 를 절대경로로 정규화한다(상대경로는 REPO_ROOT 기준). 없으면 None."""
    raw_csv = row.get("csv_path")
    if not raw_csv:
        return None
    csv_path = raw_csv if os.path.isabs(raw_csv) else os.path.join(str(REPO_ROOT), raw_csv)
    return csv_path if os.path.isfile(csv_path) else None


@backtest_router.get("/evo_gens")
def evo_generations(run_id: str = "") -> Dict[str, Any]:
    """진화 run 의 세대 목록(loop_runs.db 읽기 전용). 백테스트 탭 '진화 세대 분석' 셀렉터용.

    각 항목: {gen_no, buy_name, sell_name, status, trade_count, gate_passed, score,
              profit, mdd, has_csv, strategy_gist}. run_id 없음/DB 부재/조회 실패면
    빈 목록(무예외). has_csv 는 결과 CSV 가 실제로 존재하는지(없으면 축약 분석만 가능).
    """
    if not run_id:
        return {"items": [], "count": 0, "run_id": run_id}
    from ai_strategy_loop.controller.state import LoopState  # noqa: PLC0415

    st: Optional[LoopState] = None
    rows: List[Dict[str, Any]] = []
    try:
        st = LoopState(readonly=True)
        rows = st.get_generations(run_id)
    except Exception:  # noqa: BLE001 - DB 없거나 조회 실패면 빈 목록(무예외).
        return {"items": [], "count": 0, "run_id": run_id}
    finally:
        if st is not None:
            try:
                st.close()
            except Exception:  # noqa: BLE001
                pass
    items: List[Dict[str, Any]] = []
    for r in rows:
        raw_gen = r.get("gen_no")
        gen_csv = _resolve_gen_csv(r)
        items.append({
            # gen 0 은 falsy 라 `or -1` 로 합치면 -1 로 뭉개진다 — is None 가드로 보존.
            "gen_no": -1 if raw_gen is None else int(raw_gen),
            "buy_name": r.get("buy_name"),
            "sell_name": r.get("sell_name"),
            "status": r.get("status"),
            "trade_count": int(r.get("trade_count", 0) or 0),
            "gate_passed": bool(r.get("gate_passed")),
            "score": float(r.get("score", 0.0) or 0.0),
            "profit": float(r.get("profit", 0.0) or 0.0),
            "mdd": float(r.get("mdd", 0.0) or 0.0),
            "has_csv": gen_csv is not None,
            "strategy_gist": r.get("strategy_gist") or "",
            # v5.13.2 — tick/min 배지용. 첫 행만 읽어 판별한다(전체 파싱 없음).
            "timeframe": analysis.peek_timeframe_csv(gen_csv),
            "created_at": float(r.get("created_at") or 0.0) or None,
        })
    return {"items": items, "count": len(items), "run_id": run_id}


def _result_for_run(
    run_id: str, gen_no: int, t_start: Optional[int] = None, t_end: Optional[int] = None
) -> Dict[str, Any]:
    """run/gen 세대 → 잡 결과(/bt/result)와 동일 스키마 응답(무예외).

    csv_path 존재 시 풀 분석(잡과 동일 묶음, t_start/t_end 구간 한정 지원). CSV 부재 시
    generations 행 메트릭 요약 + 빈 분석 구조(차트/분석 생략, 카드만). 세대 없음이면
    available=False.
    """
    row = _gen_row_readonly(run_id, gen_no)
    if row is None:
        return {"available": False, "run_id": run_id, "gen_no": gen_no}
    csv_path = _resolve_gen_csv(row)
    if csv_path:
        ranged = t_start is not None or t_end is not None
        bundle = analysis.full_analysis(csv_path, t_start, t_end)
        return {
            "ranged": ranged,
            "available": True,
            "run_id": run_id,
            "gen_no": gen_no,
            "evidence_id": f"gen:{run_id}:{int(gen_no)}",
            "source_type": "generation",
            "condition_identity": _run_condition_identity(row),
            "status": row.get("status"),
            "status_kind": row.get("status") or "generation",
            "artifact_state": "openable",
            "openable": True,
            "recoverable": False,
            "open_actions": ["open_result"],
            "rerun_spec": None,
            "metrics": bundle["summary"],
            "analysis": bundle,
            "has_csv": True,
            # v5.13.2 — "언제·어떤 연구·몇 세대·어느 기간·tick/min" 실행 맥락(결과 요약 상단).
            "context": _result_context(row, run_id, gen_no, bundle.get("summary")),
        }
    # CSV 부재 — generations 행 메트릭 요약 + 빈 분석 구조(무예외).
    #   None(미측정)은 모든 저장 메트릭에서 그대로 전파해 실제 0과 구분한다.
    fallback_metrics = {
        "trade_count": _opt_metric(row.get("trade_count")),
        "total_profit_krw": _opt_metric(row.get("profit")),
        "total_profit_pct": _opt_metric(row.get("total_profit_pct")),
        "max_drawdown_pct": _opt_metric(row.get("mdd")),
        "payoff_ratio": _opt_metric(row.get("payoff_ratio")),
    }
    return {
        "available": True,
        "run_id": run_id,
        "gen_no": gen_no,
        "evidence_id": f"gen:{run_id}:{int(gen_no)}",
        "source_type": "generation",
        "condition_identity": _run_condition_identity(row),
        "status": row.get("status"),
        "status_kind": row.get("status") or "generation",
        "artifact_state": "metrics_only_csv_missing",
        "openable": True,
        "recoverable": False,
        "open_actions": ["open_result"],
        "rerun_spec": None,
        "metrics": fallback_metrics,
        "analysis": analysis.full_analysis(None),
        "has_csv": False,
        "context": _result_context(row, run_id, gen_no, None),
        "message": "결과 CSV 가 없어 세대 메트릭 요약만 표시합니다(차트/분석 생략).",
    }


# ----------------------------------------------------------------------- demo
# 데모 합성 결과 캐시(state/ 하위, gitignored). 같은 시드로 재생성하므로 결정적.
# seed 를 파일명에 반영한다 — 스키마/시드 변경 시 새 파일로 분기해 구 캐시(구 컬럼)를
#   자연 무효화한다(_ensure_demo_csv 는 파일 부재 시에만 재생성하므로 파일명 분기가 필요).
_DEMO_SEED = 20260613
_DEMO_CSV = _PACKAGE_DIR / "state" / "webbt_demo" / f"demo_trades_{_DEMO_SEED}.csv"
_DEMO_TRADE_COUNT = 180
# 프론트가 BtResultArea 에 실어 보내는 데모 sentinel job_id(charts 무수정 렌더 경로).
_DEMO_JOB_ID = "__demo__"


def _demo_trades_rows() -> List[Dict[str, Any]]:
    """결정적(시드 고정) 합성 거래 행 목록 — 분석 전 키를 모두 채운다(빈 화면 금지).

    완만한 우상향 수익곡선·현실적 승률(약 55%)·요일/시간대 분산·MAE/MFE·청산사유·
    오더플로우 스냅샷을 포함해 모든 차트가 의미 있게 그려지도록 한다(예시 데이터 배지).
    """
    import datetime as _dt
    import random as _random

    rng = _random.Random(_DEMO_SEED)
    base = _dt.date(2025, 4, 7)
    names = ["삼성전자", "에코프로", "포스코퓨처엠", "에코프로비엠", "한미반도체", "두산에너빌리티"]
    reasons = ["목표가도달", "손절", "시간청산", "추세이탈", "변동성청산"]
    rows: List[Dict[str, Any]] = []
    day_cursor = base
    per_day = 0
    for i in range(_DEMO_TRADE_COUNT):
        if per_day >= 4 or rng.random() < 0.3:
            day_cursor += _dt.timedelta(days=1)
            while day_cursor.weekday() >= 5:  # 주말 건너뜀.
                day_cursor += _dt.timedelta(days=1)
            per_day = 0
        per_day += 1
        ymd = day_cursor.strftime("%Y%m%d")
        hh = rng.randint(9, 14)
        mm = rng.randint(0, 59)
        buy_t = f"{ymd}{hh:02d}{mm:02d}00"
        hold_min = round(rng.uniform(3.0, 90.0), 1)
        sell_dt = _dt.datetime(day_cursor.year, day_cursor.month, day_cursor.day, hh, mm) + _dt.timedelta(minutes=hold_min)
        sell_t = sell_dt.strftime("%Y%m%d%H%M%S")
        # 55% 승률·약한 양의 기대값(현실적 소폭 손익 — 합산 우상향).
        win = rng.random() < 0.55
        pct = round(rng.uniform(0.2, 2.2) if win else -rng.uniform(0.2, 1.6), 2)
        # 진입 체결금액(원) — 보유금액 곡선용. 청산금액 = 매수금액*(1+수익률/100) 근사.
        buy_amount = round(rng.uniform(2_000_000, 8_000_000))
        krw = round(buy_amount * pct / 100.0)
        sell_amount = round(buy_amount + krw)
        mfe = round(abs(pct) + rng.uniform(0.1, 1.5), 2)
        mae = round(-(abs(pct) * 0.5 + rng.uniform(0.1, 1.2)), 2)
        reason = "목표가도달" if win and rng.random() < 0.6 else rng.choice(reasons)
        rows.append({
            analysis.COL_NAME: rng.choice(names),
            analysis.COL_BUY_TIME: buy_t,
            analysis.COL_SELL_TIME: sell_t,
            # 데모 시각은 14자리(YYYYMMDDHHMMSS) = tick 규약이므로 보유시간도 **초**로
            #   적는다(엔진 규약과 동일 — backengine_base.py:909). 분으로 적으면 데모만
            #   60배 부풀어 보인다.
            analysis.COL_HOLD_MIN: round(hold_min * 60.0),
            analysis.COL_PROFIT_PCT: pct,
            analysis.COL_PROFIT_KRW: krw,
            analysis.COL_BUY_AMOUNT: buy_amount,
            analysis.COL_SELL_AMOUNT: sell_amount,
            analysis.COL_MFE: mfe,
            analysis.COL_MAE: mae,
            analysis.COL_EXIT_REASON: reason,
            analysis.COL_OF_STRENGTH: round(rng.uniform(80, 220), 1),
            analysis.COL_OF_BUY_REST: rng.randint(20000, 200000),
            analysis.COL_OF_SELL_REST: rng.randint(20000, 200000),
            analysis.COL_OF_PREVDAY: round(rng.uniform(0.5, 3.0), 2),
            analysis.COL_OF_UPDOWN: round(rng.uniform(-2.0, 8.0), 2),
        })
    return rows


def _ensure_demo_csv() -> Optional[str]:
    """데모 합성 거래 CSV 를 (없으면) 생성하고 경로를 반환한다. IO 실패면 None(무예외)."""
    import csv as _csv

    try:
        _DEMO_CSV.parent.mkdir(parents=True, exist_ok=True)
        if not _DEMO_CSV.is_file():
            rows = _demo_trades_rows()
            cols = [
                analysis.COL_NAME, analysis.COL_BUY_TIME, analysis.COL_SELL_TIME,
                analysis.COL_HOLD_MIN, analysis.COL_PROFIT_PCT, analysis.COL_PROFIT_KRW,
                analysis.COL_BUY_AMOUNT, analysis.COL_SELL_AMOUNT,
                analysis.COL_MFE, analysis.COL_MAE, analysis.COL_EXIT_REASON,
                analysis.COL_OF_STRENGTH, analysis.COL_OF_BUY_REST, analysis.COL_OF_SELL_REST,
                analysis.COL_OF_PREVDAY, analysis.COL_OF_UPDOWN,
            ]
            with open(_DEMO_CSV, "w", encoding="utf-8-sig", newline="") as fh:
                writer = _csv.DictWriter(fh, fieldnames=cols)
                writer.writeheader()
                writer.writerows(rows)
        return str(_DEMO_CSV)
    except OSError:
        return None


def _demo_result() -> Dict[str, Any]:
    """합성 예시 결과(/bt/result?demo=1) — 잡과 동일 스키마 + is_demo:true(빈 화면 금지).

    실제 잡 CSV 와 동일한 full_analysis 묶음을 쓰므로 모든 차트/카드가 정상 렌더된다.
    CSV 생성 실패 시 빈 분석 구조로 폴백(무예외).
    """
    csv_path = _ensure_demo_csv()
    bundle = analysis.full_analysis(csv_path)
    return {
        "available": True,
        "is_demo": True,
        "job_id": "",
        "status": "success",
        "evidence_id": f"demo:{_DEMO_JOB_ID}",
        "source_type": "demo",
        "condition_identity": _condition_identity(
            "demo_buy", "demo_sell", artifact_note="synthetic_demo_name_only"
        ),
        "status_kind": "success",
        "artifact_state": "openable" if csv_path else "synthetic_metrics_only",
        "openable": True,
        "recoverable": False,
        "open_actions": ["open_result"],
        "rerun_spec": None,
        "metrics": bundle["summary"],
        "analysis": bundle,
        "message": "예시 데이터 — 실제 백테스트를 실행하면 이 자리에 결과가 표시됩니다.",
    }


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
    run_id: str = "",
    gen_no: Optional[int] = None,
    method: str = "shuffle",
) -> Dict[str, Any]:
    """몬테카를로 — 일별 손익 재구성으로 MDD/최종손익 분포·파산확률·팬차트.

    입력 경로는 /bt/result 와 같다: job_id(완료 잡) 또는 run_id+gen_no(진화 세대).
    세대도 같은 거래 CSV 를 남기므로 동일한 표본으로 계산한다.
    method="shuffle"(순서 위험) | "bootstrap"(표본 위험) — 의미는 analysis.monte_carlo 참조.
    """
    n = max(0, min(int(n), _MC_MAX_N))
    if not job_id and run_id and gen_no is not None:
        trades = _analysis_for_run(run_id, int(gen_no), t_start, t_end)
    else:
        trades = _analysis_for_job(job_id, t_start, t_end)
    return {
        "job_id": job_id,
        "run_id": run_id,
        "gen_no": gen_no,
        "montecarlo": analysis.monte_carlo(trades, n=n, seed=seed, ruin_pct=ruin_pct,
                                           method=method),
    }


@backtest_router.get("/analysis/orderflow")
def analysis_orderflow(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    """오더플로우 — 승/패 그룹별 진입 체결강도/호가불균형/전일동시간비/등락율 분포 비교."""
    return {"job_id": job_id, "orderflow": analysis.entry_orderflow(_analysis_for_job(job_id, t_start, t_end))}


@backtest_router.get("/analysis/gui_parity")
def analysis_gui_parity(job_id: str = "", t_start: Optional[int] = None, t_end: Optional[int] = None) -> Dict[str, Any]:
    """STOM GUI PlotShow 2장 이미지 패리티 — MDD 랜덤곡선·일별·시간대·요일·보유금액·거래롤링.

    full_analysis 묶음의 gui_parity 와 동일 데이터를 개별 라우트로도 제공한다(구간 필터 지원).
    """
    return {"job_id": job_id, "gui_parity": analysis.gui_parity(_analysis_for_job(job_id, t_start, t_end))}


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


def _compare_side_for_run(run_id: str, gen_no: Optional[int]) -> Optional[Dict[str, Any]]:
    """진화 세대의 비교 페이로드 — 잡과 동일 스키마. 세대/CSV 없음이면 None(무예외).

    세대 결과도 잡과 같은 거래 CSV 를 남기므로 같은 방식으로 요약·수익곡선을 만든다.
    이것이 없어 A/B 비교가 '완료 잡 전용'으로 묶여 있었고, 정작 완주한 잡이 없어
    비교 기능 자체를 쓸 수 없었다(2026-07-26).
    """
    if not run_id or gen_no is None:
        return None
    row = _gen_row_readonly(run_id, int(gen_no))
    if row is None:
        return None
    csv_path = _resolve_gen_csv(row)
    if not csv_path:
        return None
    trades = analysis.load_trades_csv(csv_path)
    summary = analysis.summary_metrics(trades)
    return {
        "job_id": f"gen:{run_id}:{int(gen_no)}",
        "run_id": run_id,
        "gen_no": int(gen_no),
        "source_type": "generation",
        "label": f"{run_id} / g{int(gen_no)}",
        "status": row.get("status"),
        "metrics": summary,
        "summary": summary,
        "equity": analysis.equity_series(trades),
        "trade_count": summary["trade_count"],
    }


@backtest_router.get("/compare")
def compare_jobs(
    job_a: str = "",
    job_b: str = "",
    run_a: str = "",
    gen_a: Optional[int] = None,
    run_b: str = "",
    gen_b: Optional[int] = None,
) -> Dict[str, Any]:
    """A/B 비교 — 각 메트릭·수익곡선 + delta(b-a). 한쪽 없으면 해당 키 null(무예외).

    양쪽 모두 완료 잡(job_a/job_b) 또는 진화 세대(run_a+gen_a / run_b+gen_b)를 받는다.
    한쪽은 잡, 다른 쪽은 세대인 교차 비교도 같은 스키마로 처리된다.
    """
    a = _compare_side(job_a) if job_a else _compare_side_for_run(run_a, gen_a)
    b = _compare_side(job_b) if job_b else _compare_side_for_run(run_b, gen_b)
    return {
        "a": a,
        "b": b,
        "delta": _compare_delta(a, b),
    }


# --------------------------------------------------------------------- overlay
# 다중 잡 오버레이 입력 개수 경계(2~4). 1개는 오버레이 의미 없음, 과다는 곡선 가독성 저하.
_OVERLAY_MIN = 2
_OVERLAY_MAX = 4


def _overlay_series(job_id: str) -> Optional[Dict[str, Any]]:
    """단일 잡 → 오버레이 시계열 {job_id, label, summary, cumulative}. 없으면 None(무예외).

    cumulative 는 결과 CSV 의 거래일축 누적수익곡선(equity_series.cumulative). 프론트가
    정규화 토글로 첫 포인트 기준 상대화하거나 원시 누적손익으로 그린다.
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
    spec = record.get("spec") or {}
    label = f"{spec.get('buy', '')}·{job_id[:8]}" if spec.get("buy") else job_id[:12]
    return {
        "job_id": job_id,
        "label": label,
        "status": record.get("status"),
        "summary": summary,
        "cumulative": analysis.equity_series(trades).get("cumulative", []),
    }


@backtest_router.get("/overlay")
def overlay_jobs(job_ids: str = "") -> Dict[str, Any]:
    """다중 잡(2~4) 수익곡선 오버레이 — 각 잡 누적수익곡선 + summary(범례/정규화는 프론트).

    job_ids: 쉼표구분 job_id 목록(2~4). 각 잡을 거래일축 누적수익곡선으로 해석해 한 화면에
    겹쳐 그릴 시리즈를 반환한다. 개수 경계 위반/해석 실패는 무예외 error 페이로드(HTTP 200,
    대시보드 컨벤션). 정규화(첫 포인트 0 기준)는 프론트 토글이 처리한다(원시 곡선 그대로 전달).
    """
    ids = [s.strip() for s in str(job_ids or "").split(",") if s.strip()]
    # 중복 제거(입력 순서 유지).
    seen: Set[str] = set()
    unique_ids = [i for i in ids if not (i in seen or seen.add(i))]
    if not (_OVERLAY_MIN <= len(unique_ids) <= _OVERLAY_MAX):
        return {
            "status": "error",
            "message": f"오버레이는 {_OVERLAY_MIN}~{_OVERLAY_MAX}개 잡이 필요합니다(받음: {len(unique_ids)}).",
            "series": [],
        }
    series: List[Dict[str, Any]] = []
    failed: List[str] = []
    for jid in unique_ids:
        got = _overlay_series(jid)
        if got is None:
            failed.append(jid)
        else:
            series.append(got)
    if len(series) < _OVERLAY_MIN:
        return {
            "status": "error",
            "message": f"유효한 잡이 {_OVERLAY_MIN}개 미만입니다(해석 실패: {failed}).",
            "series": series,
            "failed": failed,
        }
    return {"status": "ok", "series": series, "count": len(series), "failed": failed}


# ------------------------------------------------------------------- portfolio
# 포트폴리오 결합 분석 입력 개수 경계(2~6). 1개는 결합 의미 없음, 과다는 히트맵 가독성 저하.
_PORTFOLIO_MIN = 2
_PORTFOLIO_MAX = 6


def _portfolio_item_trades(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """포트폴리오 입력 1개({job_id} | {run_id,gen_no}) → {label, trades}. 못 찾으면 None.

    잡은 result_csv_path 로, 세대는 loop_runs.db(읽기 전용)의 csv_path 로 trades 를
    읽는다. CSV 부재(세대 축약)면 trades=[] 로 포함한다(빈 전략 — 합성에 0 기여).
    """
    if not isinstance(item, dict):
        return None
    job_id = str(item.get("job_id", "") or "").strip()
    if job_id:
        manager = get_job_manager()
        record = manager.get(job_id, log_tail=0)
        if not record.get("available"):
            return None
        csv_path = manager.result_csv_path(job_id)
        spec = record.get("spec") or {}
        label = str(item.get("label", "") or "").strip() or (
            f"{spec.get('buy', '')}·{job_id[:8]}" if spec.get("buy") else job_id[:12]
        )
        return {"label": label, "trades": analysis.load_trades_csv(csv_path)}
    run_id = str(item.get("run_id", "") or "").strip()
    gen_no = item.get("gen_no")
    if run_id and gen_no is not None:
        try:
            gen_int = int(gen_no)
        except (TypeError, ValueError):
            return None
        row = _gen_row_readonly(run_id, gen_int)
        if row is None:
            return None
        csv_path = _resolve_gen_csv(row)
        label = str(item.get("label", "") or "").strip() or f"{run_id}/g{gen_int}"
        return {"label": label, "trades": analysis.load_trades_csv(csv_path)}
    return None


@backtest_router.post("/portfolio")
def portfolio_combine(payload: PortfolioPayload) -> Dict[str, Any]:
    """포트폴리오 결합 분석 — 2~6 전략(잡/세대)의 일별손익 합성(워크벤치 UI 레이어).

    요청: {"items": [{"job_id"} | {"run_id","gen_no"} (옵션 "label") ...]} (2~6개).
    각 item 을 trades 로 해석해 analysis.portfolio_analysis 로 결합 곡선·결합 MDD·
    전략 간 일별손익 상관행렬·기여도를 만든다. 개수 경계 위반/해석 실패는 무예외
    error 페이로드(HTTP 200, 대시보드 컨벤션).

    부모 P-A 의 포트폴리오 상관 스캔(.omo/evidence — 선택기 레이어)과 역할이 다르다:
    본 엔드포인트는 워크벤치가 한 화면에서 바로 시각화할 결합 결과만 만든다(advisory
    판정 지표 미생산). 레이어 구분은 backtest_analysis.portfolio_analysis docstring 참조.
    """
    raw_items = [item.model_dump(exclude_none=True) for item in payload.items]
    resolved: List[Dict[str, Any]] = []
    failed: List[int] = []
    for idx, item in enumerate(raw_items):
        got = _portfolio_item_trades(item)
        if got is None:
            failed.append(idx)
        else:
            resolved.append(got)
    if len(resolved) < _PORTFOLIO_MIN:
        return {
            "status": "error",
            "message": f"유효한 전략이 {_PORTFOLIO_MIN}개 미만입니다(해석 실패 인덱스: {failed}).",
            "failed": failed,
        }
    result = analysis.portfolio_analysis(resolved)
    return {"status": "ok", "portfolio": result, "failed": failed}


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
    trade_count/profit/mdd 등으로 축약 리포트(무예외). 세대 조회는 LoopState(readonly=True)
    로 mode=ro URI 만 열어 보호된 loop_runs.db 에 어떤 쓰기도 하지 않는다.
    """
    row = _gen_row_readonly(run_id, gen_no)
    if row is None:
        return None

    csv_path = _resolve_gen_csv(row)

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
            # v5.13.2 — 리포트도 대시보드와 같은 실행 맥락을 싣는다(사람용 표 + AI용 JSON).
            "context": _result_context(row, run_id, gen_no, bundle.get("summary")),
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
        "context": _result_context(row, run_id, gen_no, None),
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
    security = websocket.app.state.dashboard_security
    failure = security.authorize_websocket(websocket, Capability.SAFE_BACKTEST)
    if failure is not None:
        await close_websocket_failure(websocket, failure)
        return
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
