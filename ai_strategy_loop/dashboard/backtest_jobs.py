"""Backtest workbench job manager — subprocess 백테 잡 큐/상태/취소 (PR2).

웹 워크벤치가 띄우는 백테스트 잡 1개(동시 실행 1개, 나머지는 큐잉)를 관리한다.
controller/loop.py 의 검증된 subprocess 계약(`stom_backtest.py --format json`)을 그대로
재사용하되, 실행 자식에는 submit 시점에 고정한 per-job strategy/backtest DB snapshot만
노출한다(운영 DB/루프 격리 DB를 직접 쓰지 않음).

설계 계약:
  - 동시 실행 1개. start 시 이미 running 이면 큐에 적재(FIFO), 워커 스레드가 순차 처리.
  - 잡 메타는 in-memory dict + ``state/webbt_jobs/<job_id>.json`` 영속(서버 재시작 후
    과거 잡 결과 조회 가능). stdout/stderr 는 ``<job_id>.log`` 로 기록(state 는 gitignored).
  - strategy/backtest DB snapshot은 ``state/webbt_jobs/snapshots/<job_id>/`` 아래 둔다.
  - cancel 은 LoopProcessManager 의 terminate→grace→kill→wait 패턴 재사용(좀비 reap).
  - command_builder 주입점: 테스트는 단명 가짜 커맨드를 주입해 라이프사이클을 검증한다.
  - 무예외에 가깝게: 잡 실패도 status='error'/'timeout' 레코드로 표준화(예외 누수 금지).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ai_strategy_loop.dashboard._windows_process_job import (
    WindowsProcessJob,
    attach_process_job,
)
from ai_strategy_loop.dashboard.backtest_job_spec import BacktestJobSpec
from ai_strategy_loop.controller.telemetry import dashboard_telemetry

# 패키지 루트(.../ai_strategy_loop) 기준 경로. CWD 무관.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_JOBS_DIR = _PACKAGE_DIR / "state" / "webbt_jobs"

# strategy/backtest DB 원본. 잡 실행은 운영 파일을 직접 쓰지 않고, submit 시점에
#   state/webbt_jobs 아래 per-job snapshot/copy(결과 DB는 원본 미지정 시 empty init)를
#   만든 뒤 자식 env 를 그쪽으로 묶는다.
_OPERATIONAL_STRATEGY_DB = REPO_ROOT / "_database" / "strategy.db"
_OPERATIONAL_BACKTEST_DB = REPO_ROOT / "_database" / "backtest.db"

_FORMULA_COLUMNS = (
    "수식명", "차트표시", "전략연산", "팩터명",
    "표시형태", "색상", "굵기", "종류", "수식코드",
)

# 진행 로그 테일 기본 줄 수.
_LOG_TAIL_LINES = 50
# stdout/stderr 폴링 간격.
_POLL_SEC = 0.4

CommandBuilder = Callable[["BacktestJobSpec"], List[str]]


# ---------------------------------------------------------------- 진행 신호 감시
# `--quiet` CLI 는 종료 시점까지 stdout 을 내지 않는다. 그래서 progress 는 0.05 에
#   고정되고, 화면에서는 "느린 실행"과 "멈춘 실행"을 구분할 수 없다. 실제로 조건식에
#   따라 엔진 트리가 데이터를 다 읽은 뒤 계산으로 넘어가지 못하고 교착하는 경우가
#   있는데(2026-07-26 실측: CPU 0% · 디스크 읽기 0B/s 로 28분), 이때도 상태는 계속
#   `running` 이었다. 프로세스 트리의 누적 디스크 읽기와 CPU 시간을 표본으로 삼아
#   "마지막으로 무언가 한 시점"을 추적한다.
_ACTIVITY_LOCK = threading.Lock()
_ACTIVITY: Dict[str, Dict[str, float]] = {}
# 표본 간격(초). /bt/job 폴링마다 트리를 훑으면 비싸므로 이 간격으로만 갱신한다.
_ACTIVITY_SAMPLE_SEC = 15.0


def _tree_work_units(pid: int) -> Optional[float]:
    """프로세스 트리의 누적 작업량(디스크 읽기 바이트 + CPU 초). 조회 불가면 None."""
    try:
        import psutil  # noqa: PLC0415
    except Exception:  # noqa: BLE001 - psutil 없으면 감시하지 않는다(기능 저하만).
        return None
    try:
        parent = psutil.Process(int(pid))
        procs = [parent] + parent.children(recursive=True)
    except Exception:  # noqa: BLE001 - 이미 종료됐거나 권한 없음.
        return None
    total = 0.0
    for proc in procs:
        try:
            total += float(proc.io_counters().read_bytes)
        except Exception:  # noqa: BLE001 - 일부 프로세스는 io_counters 를 못 준다.
            pass
        try:
            cpu = proc.cpu_times()
            total += (cpu.user + cpu.system) * 1_000_000.0
        except Exception:  # noqa: BLE001
            pass
    return total


def probe_activity(job_id: str, pid: Optional[int]) -> Optional[float]:
    """마지막 진행 신호 이후 경과 초. 판단할 수 없으면 None.

    None 은 "멈추지 않았다"가 아니라 "알 수 없다"는 뜻이다. 화면은 None 일 때
    아무 경고도 하지 않는다(근거 없는 경고 금지).
    """
    if not job_id or not pid:
        return None
    now = _now()
    with _ACTIVITY_LOCK:
        state = _ACTIVITY.get(job_id)
        if state is not None and now - state["sampled_at"] < _ACTIVITY_SAMPLE_SEC:
            return max(0.0, now - state["moved_at"])
    units = _tree_work_units(pid)
    if units is None:
        return None
    with _ACTIVITY_LOCK:
        state = _ACTIVITY.get(job_id)
        if state is None:
            _ACTIVITY[job_id] = {"units": units, "moved_at": now, "sampled_at": now}
            return 0.0
        # 표본 잡음을 피하려고 5MB 상당 이상 늘었을 때만 "움직였다"로 본다.
        if units > state["units"] + 5_000_000.0:
            state["moved_at"] = now
        state["units"] = units
        state["sampled_at"] = now
        return max(0.0, now - state["moved_at"])


def forget_activity(job_id: str) -> None:
    """잡이 끝나면 표본 상태를 버린다."""
    with _ACTIVITY_LOCK:
        _ACTIVITY.pop(job_id, None)


@dataclass
class BacktestJobRecord:
    """잡 1개의 상태/결과 레코드(JSON 영속 가능)."""

    job_id: str
    spec: Dict[str, Any]
    status: str = "pending"  # pending|running|success|no_trades|error|timeout|cancelled
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    returncode: Optional[int] = None
    csv_path: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    # CLI child protocol의 bounded checkpoint 요약. 원시 event payload나 거래 데이터는 보존하지 않는다.
    process_diagnostics: Optional[Dict[str, Any]] = None
    # wfo/sweep 등 csv_path 없는 모드의 구조화 결과(윈도우별/조합별 표). 단일 백테/최적화는 None.
    mode_result: Optional[Dict[str, Any]] = None
    message: str = ""
    progress: float = 0.0  # 0.0~1.0 추정.
    phase: str = "queued"
    pid: Optional[int] = None
    # 결과 체계 관리(트랙 B ③) — 사용자 분류 메타. 잡 실행과 무관하게 update_meta 로 갱신된다.
    tags: List[str] = field(default_factory=list)
    memo: str = ""
    favorite: bool = False
    # submit 시점에 고정한 per-job artifact 경로/검증 해시. 자식 프로세스는 이 snapshot만 본다.
    strategy_db_snapshot_path: Optional[str] = None
    strategy_db_snapshot_hashes: Optional[Dict[str, str]] = None
    backtest_db_snapshot_path: Optional[str] = None
    csv_dir_snapshot_path: Optional[str] = None

    def to_public(self) -> Dict[str, Any]:
        """API 응답용 dict(로그 테일은 매니저가 별도 부착)."""
        return asdict(self)


def _now() -> float:
    return time.time()

def _telemetry(
    event_type: str,
    record: Optional["BacktestJobRecord"] = None,
    *,
    spec: Optional[BacktestJobSpec] = None,
    stage: str = "",
    message: str = "",
    percent: Optional[float] = None,
    processed: Optional[int] = None,
    total: Optional[int] = None,
) -> None:
    """Emit bounded in-memory telemetry for the official backtest CLI wrapper only."""

    try:
        current_spec = spec or (BacktestJobSpec(**record.spec) if record is not None else None)
        job_id = record.job_id if record is not None else ""
        dashboard_telemetry().append(
            event_type,
            run_id=job_id,
            gen_no=-1,
            seed="",
            stage=stage,
            message=message,
            source="official_backtest_cli",
            trace_id=f"bt:{job_id}:{stage}:{event_type}",
            percent=percent,
            processed=processed,
            total=total,
            symbol=getattr(current_spec, "one_code", None),
            code=getattr(current_spec, "buy", None),
        )
    except Exception:
        pass


def _safe_name(value: str) -> bool:
    """전략 이름 안전성: 빈 값/제어문자/경로구분자 차단(서브프로세스 인자 위생)."""
    if not value or not value.strip():
        return False
    return not any(ch in value for ch in ("\x00", "\n", "\r"))


def _code_hash(code: str) -> str:
    """Per-job source snapshot integrity hash: exact UTF-8 source text."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _require_source_code(value: Optional[str], label: str) -> str:
    """잡 source snapshot 에 넣을 코드 전문은 submit 계약에서 반드시 넘어와야 한다."""
    if value is None:
        raise ValueError(f"{label} code snapshot missing")
    code = str(value)
    if not code.strip():
        raise ValueError(f"{label} code snapshot missing")
    return code


def _copy_sqlite_readonly(source: Path, destination: Path) -> bool:
    """Copy source SQLite DB into destination using a read-only source connection.

    Returns False when the source file does not exist. Existing-but-unreadable sources
    raise so callers fail closed instead of silently launching from a partial DB.
    """
    source_path = Path(source)
    if not source_path.is_file():
        return False
    src = sqlite3.connect(f"file:{source_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(str(destination))
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()
    return True


def _ensure_strategy_snapshot_schema(con: sqlite3.Connection) -> None:
    con.execute('CREATE TABLE IF NOT EXISTS stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    con.execute('CREATE TABLE IF NOT EXISTS stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
    cols_sql = ", ".join(f'"{col}" TEXT' for col in _FORMULA_COLUMNS)
    con.execute(f"CREATE TABLE IF NOT EXISTS formula ({cols_sql})")


def _bind_strategy_code(
    con: sqlite3.Connection,
    *,
    table: str,
    name: str,
    code: str,
) -> str:
    con.execute(f'DELETE FROM {table} WHERE "index" = ?', (name,))
    con.execute(f'INSERT INTO {table} ("index", "전략코드") VALUES (?, ?)', (name, code))
    row = con.execute(
        f'SELECT "전략코드" FROM {table} WHERE "index" = ? LIMIT 1',
        (name,),
    ).fetchone()
    actual = "" if row is None or row[0] is None else str(row[0])
    expected_hash = _code_hash(code)
    if actual != code or _code_hash(actual) != expected_hash:
        raise RuntimeError(f"{table} source snapshot hash verification failed")
    return expected_hash


def _read_snapshot_code(snapshot_path: Path, *, table: str, name: str) -> str:
    con = sqlite3.connect(f"file:{Path(snapshot_path).resolve().as_posix()}?mode=ro", uri=True)
    try:
        row = con.execute(
            f'SELECT "전략코드" FROM {table} WHERE "index" = ? LIMIT 1',
            (name,),
        ).fetchone()
        return "" if row is None or row[0] is None else str(row[0])
    finally:
        con.close()


def default_command_builder(spec: BacktestJobSpec) -> List[str]:
    """stom_backtest.py 서브프로세스 커맨드를 만든다(mode 에 따라 분기).

    backtest(기본): controller/loop.py 와 동일한 --buy/--sell 단일 실행.
    optimize: stom_backtest optimize 래핑(--param-space JSON 필수, --method, --objective).
    wfo: stom_backtest wfo 래핑(전진분석 — --train-window-days/--test-window-days 필수,
      선택 --param-space, --step-days). cli/subcommands.py 계약은 --divid-mode 를 받지 않는다.
    sweep: stom_backtest sweep param|rolling 래핑(sweep_action 으로 분기 — param 은 --params
      JSON, rolling 은 --window-days/--step-days). 마찬가지로 --divid-mode 없음.
    """
    _STOM = str(REPO_ROOT / "stom_backtest.py")
    if spec.mode == "optimize":
        cmd = [
            sys.executable,
            _STOM,
            "optimize",
            "--buy", spec.buy,
            "--sell", spec.sell,
            "--start", str(spec.start),
            "--end", str(spec.end),
            "--start-time", str(spec.start_time),
            "--end-time", str(spec.end_time),
            "--param-space", str(spec.param_space or ""),
            "--method", spec.opt_method,
            "--objective", spec.opt_objective,
            "--timeframe", spec.timeframe,
            "--engines", str(spec.engines),
            "--timeout", str(spec.timeout),
            "--format", "json",
        ]
        return cmd
    if spec.mode == "wfo":
        cmd = [
            sys.executable,
            _STOM,
            "wfo",
            "--buy", spec.buy,
            "--sell", spec.sell,
            "--start", str(spec.start),
            "--end", str(spec.end),
            "--start-time", str(spec.start_time),
            "--end-time", str(spec.end_time),
            "--train-window-days", str(spec.train_window_days),
            "--test-window-days", str(spec.test_window_days),
            "--objective", spec.opt_objective,
            "--method", spec.opt_method,
            "--timeframe", spec.timeframe,
            "--engines", str(spec.engines),
            "--timeout", str(spec.timeout),
            "--format", "json",
        ]
        if spec.step_days:
            cmd.extend(["--step-days", str(spec.step_days)])
        if spec.param_space:
            cmd.extend(["--param-space", str(spec.param_space)])
        return cmd
    if spec.mode == "sweep":
        cmd = [sys.executable, _STOM, "sweep"]
        if spec.sweep_action == "rolling":
            cmd.extend([
                "rolling",
                "--buy", spec.buy,
                "--sell", spec.sell,
                "--start", str(spec.start),
                "--end", str(spec.end),
                "--start-time", str(spec.start_time),
                "--end-time", str(spec.end_time),
                "--window-days", str(spec.window_days),
                "--step-days", str(spec.step_days),
            ])
        else:
            cmd.extend([
                "param",
                "--buy", spec.buy,
                "--sell", spec.sell,
                "--start", str(spec.start),
                "--end", str(spec.end),
                "--start-time", str(spec.start_time),
                "--end-time", str(spec.end_time),
                "--params", str(spec.sweep_params or ""),
            ])
        cmd.extend([
            "--timeframe", spec.timeframe,
            "--engines", str(spec.engines),
            "--timeout", str(spec.timeout),
            "--format", "json",
        ])
        return cmd
    cmd = [
        sys.executable,
        str(REPO_ROOT / "stom_backtest.py"),
        "--buy", spec.buy,
        "--sell", spec.sell,
        "--start", str(spec.start),
        "--end", str(spec.end),
        "--start-time", str(spec.start_time),
        "--end-time", str(spec.end_time),
        "--timeframe", spec.timeframe,
        "--divid-mode", spec.divid_mode,
        "--engines", str(spec.engines),
        "--timeout", str(spec.timeout),
        "--format", "json",
        "--quiet",
    ]
    if spec.one_code:
        cmd.extend(["--one-code", str(spec.one_code)])
    return cmd


class BacktestJobManager:
    """동시 1개 실행 + FIFO 큐 백테 잡 매니저.

    command_builder 주입으로 테스트가 단명 가짜 커맨드를 쓸 수 있다(실제 백테 미실행).
    """

    def __init__(
        self,
        *,
        jobs_dir: Optional[Path] = None,
        command_builder: Optional[CommandBuilder] = None,
        strategy_db: Optional[Path] = None,
        backtest_db: Optional[Path] = None,
        deadline_grace: float = 60.0,
    ) -> None:
        self._jobs_dir = Path(jobs_dir) if jobs_dir else _JOBS_DIR
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._command_builder = command_builder or default_command_builder
        self._strategy_db = Path(strategy_db) if strategy_db else _OPERATIONAL_STRATEGY_DB
        self._backtest_db = Path(backtest_db) if backtest_db else None
        # spec.timeout 에 더해지는 하드 데드라인 유예(초). 테스트가 짧게 줄일 수 있다.
        self._deadline_grace = float(deadline_grace)
        self._lock = threading.RLock()
        self._records: Dict[str, BacktestJobRecord] = {}
        self._queue: List[str] = []
        self._proc: Optional[subprocess.Popen[str]] = None
        self._process_job: WindowsProcessJob | None = None
        self._current_job: Optional[str] = None
        self._worker: Optional[threading.Thread] = None
        self._cancel_requested: set[str] = set()
        self._load_persisted()

    # ------------------------------------------------------------ DB snapshots
    def _snapshot_dir(self, job_id: str) -> Path:
        return self._jobs_dir / "snapshots" / job_id

    def _create_strategy_snapshot(
        self,
        job_id: str,
        spec: BacktestJobSpec,
    ) -> tuple[Path, Dict[str, str]]:
        """Create immutable per-job strategy DB and bind exact submitted source code."""
        buy_code = _require_source_code(spec.buy_code, "buy")
        sell_code = _require_source_code(spec.sell_code, "sell")
        snapshot_dir = self._snapshot_dir(job_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / "strategy.db"
        tmp_path = snapshot_dir / "strategy.db.tmp"
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass

        try:
            if not _copy_sqlite_readonly(self._strategy_db, tmp_path):
                sqlite3.connect(str(tmp_path)).close()
            con = sqlite3.connect(str(tmp_path))
            try:
                _ensure_strategy_snapshot_schema(con)
                hashes = {
                    "buy": _bind_strategy_code(
                        con,
                        table="stockbuy",
                        name=spec.buy,
                        code=buy_code,
                    ),
                    "sell": _bind_strategy_code(
                        con,
                        table="stocksell",
                        name=spec.sell,
                        code=sell_code,
                    ),
                }
                con.commit()
            finally:
                con.close()
            os.replace(tmp_path, snapshot_path)
            return snapshot_path.resolve(), hashes
        except Exception:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            raise

    def _create_backtest_db_snapshot(self, job_id: str) -> Path:
        """Create an isolated per-job result DB so child writes never hit operating DB."""
        snapshot_dir = self._snapshot_dir(job_id)
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = snapshot_dir / "backtest.db"
        tmp_path = snapshot_dir / "backtest.db.tmp"
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        try:
            if not self._backtest_db or not _copy_sqlite_readonly(self._backtest_db, tmp_path):
                sqlite3.connect(str(tmp_path)).close()
            os.replace(tmp_path, snapshot_path)
            return snapshot_path.resolve()
        except Exception:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            raise

    def _create_csv_dir_snapshot(self, job_id: str) -> Path:
        """Create an isolated per-job CSV output directory under the job snapshot."""
        csv_dir = self._snapshot_dir(job_id) / "csv"
        csv_dir.mkdir(parents=True, exist_ok=True)
        return csv_dir.resolve()

    def _verify_strategy_snapshot(self, record: BacktestJobRecord, spec: BacktestJobSpec) -> Path:
        """Fail closed if the per-job source snapshot is missing or no longer matches spec."""
        if not record.strategy_db_snapshot_path:
            raise RuntimeError("strategy DB snapshot missing")
        snapshot_path = Path(record.strategy_db_snapshot_path)
        if not snapshot_path.is_file():
            raise RuntimeError("strategy DB snapshot file missing")
        hashes = record.strategy_db_snapshot_hashes or {}
        expected = {
            "buy": _code_hash(_require_source_code(spec.buy_code, "buy")),
            "sell": _code_hash(_require_source_code(spec.sell_code, "sell")),
        }
        if hashes != expected:
            raise RuntimeError("strategy DB snapshot metadata hash mismatch")
        actual_buy = _read_snapshot_code(snapshot_path, table="stockbuy", name=spec.buy)
        actual_sell = _read_snapshot_code(snapshot_path, table="stocksell", name=spec.sell)
        if _code_hash(actual_buy) != expected["buy"] or actual_buy != str(spec.buy_code):
            raise RuntimeError("buy strategy DB snapshot hash mismatch")
        if _code_hash(actual_sell) != expected["sell"] or actual_sell != str(spec.sell_code):
            raise RuntimeError("sell strategy DB snapshot hash mismatch")
        return snapshot_path

    def _require_backtest_snapshot(self, record: BacktestJobRecord) -> Path:
        if not record.backtest_db_snapshot_path:
            raise RuntimeError("backtest DB snapshot missing")
        snapshot_path = Path(record.backtest_db_snapshot_path)
        if not snapshot_path.is_file():
            raise RuntimeError("backtest DB snapshot file missing")
        return snapshot_path

    def _require_csv_dir_snapshot(self, record: BacktestJobRecord) -> Path:
        if not record.csv_dir_snapshot_path:
            raise RuntimeError("CSV directory snapshot missing")
        csv_dir = Path(record.csv_dir_snapshot_path)
        csv_dir.mkdir(parents=True, exist_ok=True)
        if not csv_dir.is_dir():
            raise RuntimeError("CSV directory snapshot file missing")
        return csv_dir.resolve()

    # ------------------------------------------------------------------ public
    def submit(self, spec: BacktestJobSpec) -> Dict[str, Any]:
        """잡을 큐에 넣고 job_id 를 돌려준다. 이름 검증 실패는 error 페이로드."""
        if not _safe_name(spec.buy) or not _safe_name(spec.sell):
            return {"status": "error", "message": "전략 이름이 비었거나 허용되지 않는 문자를 포함합니다."}
        if spec.timeframe not in ("tick", "min"):
            return {"status": "error", "message": f"timeframe 은 tick|min 만 허용: {spec.timeframe!r}"}
        if not (10000000 <= spec.start <= 99999999 and 10000000 <= spec.end <= 99999999):
            return {"status": "error", "message": "start/end 는 YYYYMMDD 8자리여야 합니다."}
        if spec.start > spec.end:
            return {"status": "error", "message": "start 가 end 보다 늦습니다."}
        if spec.mode not in ("backtest", "optimize", "wfo", "sweep"):
            return {"status": "error", "message": f"mode 는 backtest|optimize|wfo|sweep 만 허용: {spec.mode!r}"}
        if spec.mode == "optimize" and not (spec.param_space and str(spec.param_space).strip()):
            return {"status": "error", "message": "optimize 모드는 param_space(탐색공간 JSON 경로)가 필요합니다."}
        if spec.mode == "wfo":
            if spec.train_window_days < 1 or spec.test_window_days < 1:
                return {"status": "error", "message": "wfo 모드는 train_window_days·test_window_days(>=1)가 필요합니다."}
        if spec.mode == "sweep":
            if spec.sweep_action not in ("param", "rolling"):
                return {"status": "error", "message": f"sweep_action 은 param|rolling 만 허용: {spec.sweep_action!r}"}
            if spec.sweep_action == "param" and not (spec.sweep_params and str(spec.sweep_params).strip()):
                return {"status": "error", "message": "sweep param 모드는 sweep_params(조합 JSON 경로)가 필요합니다."}
            if spec.sweep_action == "rolling" and (spec.window_days < 1 or spec.step_days < 1):
                return {"status": "error", "message": "sweep rolling 모드는 window_days·step_days(>=1)가 필요합니다."}

        job_id = self._new_job_id(spec.buy)
        try:
            strategy_snapshot_path, strategy_hashes = self._create_strategy_snapshot(job_id, spec)
            backtest_snapshot_path = self._create_backtest_db_snapshot(job_id)
            csv_dir_snapshot_path = self._create_csv_dir_snapshot(job_id)
        except Exception as exc:  # noqa: BLE001 - submit 계약은 HTTP 200 error payload로 표준화된다.
            return {"status": "error", "message": f"잡 artifact snapshot 생성 실패: {exc}"}
        with self._lock:
            record = BacktestJobRecord(
                job_id=job_id,
                spec=asdict(spec),
                strategy_db_snapshot_path=str(strategy_snapshot_path),
                strategy_db_snapshot_hashes=strategy_hashes,
                backtest_db_snapshot_path=str(backtest_snapshot_path),
                csv_dir_snapshot_path=str(csv_dir_snapshot_path),
            )
            self._records[job_id] = record
            self._queue.append(job_id)
            self._persist(record)
            _telemetry(
                "backtest_queued",
                record,
                stage="queued",
                message=f"{spec.mode} queued",
                percent=0.0,
            )
            self._ensure_worker()
        return {"status": "ok", "job_id": job_id}

    def get(self, job_id: str, *, log_tail: int = _LOG_TAIL_LINES) -> Dict[str, Any]:
        """잡 상태 + 로그 테일을 반환한다. 없으면 available=False(무예외)."""
        with self._lock:
            record = self._records.get(job_id)
            payload = record.to_public() if record else None
        if payload is None:
            return {"available": False, "job_id": job_id}
        payload["available"] = True
        payload["log_tail"] = self._read_log_tail(job_id, log_tail)
        return payload

    def list_jobs(self) -> Dict[str, Any]:
        """모든 잡을 최신순(created_at desc)으로 반환한다(로그 테일 제외)."""
        with self._lock:
            records = sorted(self._records.values(), key=lambda r: r.created_at, reverse=True)
            jobs = [r.to_public() for r in records]
        return {"jobs": jobs, "count": len(jobs)}

    def cancel(self, job_id: str) -> Dict[str, Any]:
        """대기 중이면 큐에서 제거, 실행 중이면 프로세스 트리 회수(무예외)."""
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return {"status": "error", "message": "job_id 없음", "job_id": job_id}
            if record.status in ("success", "no_trades", "error", "timeout", "cancelled"):
                return {"status": "error", "message": f"이미 종료된 잡({record.status})", "job_id": job_id}
            already_requested = job_id in self._cancel_requested
            self._cancel_requested.add(job_id)
            if job_id in self._queue:
                self._queue.remove(job_id)
                self._finalize_cancel_without_process(record, "큐에서 취소됨")
                return {"status": "ok", "job_id": job_id, "cancelled": "queued"}
            running_proc = self._proc if self._current_job == job_id else None
            if already_requested:
                return {"status": "ok", "job_id": job_id, "cancelled": "requested"}
        # 실행 중인 프로세스 회수는 락 밖에서(긴 wait 회피).
        if running_proc is not None:
            self._hard_stop(running_proc)
            return {"status": "ok", "job_id": job_id, "cancelled": "running"}
        return {"status": "ok", "job_id": job_id, "cancelled": "requested"}

    def result_csv_path(self, job_id: str) -> Optional[str]:
        """완료된 잡의 결과 CSV 경로(분석 재계산용). 미완료/없음이면 None."""
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return None
            return record.csv_path

    def update_meta(
        self,
        job_id: str,
        *,
        tags: Optional[List[str]] = None,
        memo: Optional[str] = None,
        favorite: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """잡 결과 메타(태그/메모/즐겨찾기)를 갱신·영속한다(결과 체계 관리, 트랙 B ③).

        None 인자는 미변경(부분 업데이트). 잡 없음이면 available=False(무예외). 태그는
        공백 제거·중복 제거 후 정렬해 저장한다(빈 토큰 무시).
        """
        with self._lock:
            record = self._records.get(job_id)
            if record is None:
                return {"available": False, "job_id": job_id}
            if tags is not None:
                # 시스템 경계 위생: 태그 64자·50개, 메모 2000자 상한(리뷰 권고 — JSON 비대 방지).
                cleaned = {t.strip()[:64] for t in tags if isinstance(t, str) and t.strip()}
                record.tags = sorted(cleaned)[:50]
            if memo is not None:
                record.memo = str(memo)[:2000]
            if favorite is not None:
                record.favorite = bool(favorite)
            self._persist(record)
            return {
                "available": True,
                "job_id": job_id,
                "tags": list(record.tags),
                "memo": record.memo,
                "favorite": record.favorite,
            }

    # ----------------------------------------------------------------- worker
    def _finalize_cancel_without_process(self, record: BacktestJobRecord, message: str) -> None:
        with self._lock:
            record.status = "cancelled"
            record.phase = "cancelled"
            record.finished_at = _now()
            record.message = message
            self._cancel_requested.discard(record.job_id)
            self._persist(record)
            _telemetry(
                "error",
                record,
                stage="cancelled",
                message=message,
                percent=0.0,
            )

    def _ensure_worker(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._drain_queue, name="webbt-jobs", daemon=True)
        self._worker.start()

    def _drain_queue(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    self._worker = None
                    return
                job_id = self._queue.pop(0)
                record = self._records.get(job_id)
                if record is None or job_id in self._cancel_requested:
                    continue
                self._current_job = job_id
            try:
                self._run_one(record)
            except Exception as exc:  # noqa: BLE001 - 잡 단위 실패는 레코드로 표준화.
                with self._lock:
                    if job_id in self._cancel_requested:
                        self._finalize_cancel_without_process(record, "잡 실행 준비 중 취소됨")
                    else:
                        record.status = "error"
                        record.phase = "error"
                        record.message = f"job runner failed: {exc}"
                        record.finished_at = _now()
                        self._persist(record)
                        _telemetry(
                            "error",
                            record,
                            stage="error",
                            message=record.message,
                            percent=0.0,
                        )
            finally:
                with self._lock:
                    process_job = self._process_job
                    self._current_job = None
                    self._proc = None
                    self._process_job = None
                if process_job is not None:
                    process_job.terminate()
                    process_job.close()

    def _run_one(self, record: BacktestJobRecord) -> None:
        spec = BacktestJobSpec(**record.spec)
        strategy_snapshot_path = self._verify_strategy_snapshot(record, spec)
        backtest_snapshot_path = self._require_backtest_snapshot(record)
        csv_dir_snapshot_path = self._require_csv_dir_snapshot(record)
        cmd = self._command_builder(spec)
        log_path = self._jobs_dir / f"{record.job_id}.log"

        env = dict(os.environ)
        env["STOM_ALLOW_MINIMAL_SETTING"] = "1"
        env["PYTHONUNBUFFERED"] = "1"
        # 자식 stdout 을 UTF-8 로 고정한다. 부모는 아래 Popen 에서 utf-8/errors="replace" 로
        #   읽는데, Windows 기본 콘솔 인코딩(cp949)으로 나온 한글은 전부 U+FFFD 로 치환돼
        #   복구가 불가능하다. 실제로 잡 기록의 실패 사유가 "������ ���� ..." 로 남아
        #   사용자가 원인을 읽을 수 없었다(2026-07-26 실측).
        env["PYTHONIOENCODING"] = "utf-8"
        # quiet CLI도 protocol checkpoint만 bounded JSONL로 내보내 워치독 종료 전에
        # 마지막 엔진 단계를 job record에 보존한다.
        env["STOM_CLI_BACKTEST_PROTOCOL_STREAM"] = "1"
        # 잡별 immutable snapshot만 자식에게 보인다. 운영 DB/매니저 원본은 실행 경로에 없다.
        env["STOM_CLI_DB_STRATEGY"] = str(strategy_snapshot_path)
        env["STOM_CLI_DB_BACKTEST"] = str(backtest_snapshot_path)
        env["STOM_CLI_BACKTEST_CSV_DIR"] = str(csv_dir_snapshot_path)
        # 스모크/서브셋 백테: back_db_override 가 있으면 시세 DB를 교체한다.
        if spec.back_db_override:
            key = "STOM_CLI_DB_STOCK_BACK_MIN" if spec.timeframe == "min" else "STOM_CLI_DB_STOCK_BACK_TICK"
            env[key] = spec.back_db_override

        run_start = _now()
        with self._lock:
            if record.job_id in self._cancel_requested:
                self._finalize_cancel_without_process(record, "프로세스 시작 전 취소됨")
                return
            record.status = "running"
            record.phase = "running"
            record.started_at = run_start
            record.progress = 0.05
            self._persist(record)
            _telemetry(
                "backtest_started",
                record,
                stage="running",
                message=f"{spec.mode} started",
                percent=5.0,
            )

        try:
            log_fh = open(log_path, "w", encoding="utf-8")
        except OSError as exc:
            with self._lock:
                record.status = "error"
                record.message = f"로그 파일 생성 실패: {exc}"
                record.finished_at = _now()
                self._persist(record)
                _telemetry(
                    "error",
                    record,
                    stage="error",
                    message=record.message,
                    percent=0.0,
                )
            return

        stdout_buf: List[str] = []
        with self._lock:
            if record.job_id in self._cancel_requested:
                log_fh.close()
                self._finalize_cancel_without_process(record, "프로세스 시작 전 취소됨")
                return
        try:
            proc = subprocess.Popen(
                cmd, cwd=str(REPO_ROOT), env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except Exception as exc:  # noqa: BLE001 - spawn 실패도 레코드로 표준화.
            log_fh.close()
            with self._lock:
                if record.job_id in self._cancel_requested:
                    self._finalize_cancel_without_process(record, "프로세스 시작 중 취소됨")
                else:
                    record.status = "error"
                    record.message = f"서브프로세스 기동 실패: {exc}"
                    record.finished_at = _now()
                    self._persist(record)
                    _telemetry(
                        "error",
                        record,
                        stage="error",
                        message=record.message,
                        percent=0.0,
                    )
            return

        process_job = attach_process_job(proc.pid)
        with self._lock:
            self._proc = proc
            self._process_job = process_job
            record.pid = proc.pid
            cancel_after_spawn = record.job_id in self._cancel_requested
        if cancel_after_spawn:
            self._hard_stop(proc)

        deadline = run_start + spec.timeout + self._deadline_grace
        # 워치독: --quiet CLI 는 종료 시점까지 stdout 을 전혀 내지 않으므로
        #   읽기 루프 안의 데드라인 검사만으로는 타임아웃이 영원히 발동하지
        #   않는다(첫 read 에서 블록 — 2026-06-12 실측). 출력과 무관하게
        #   데드라인에 트리 전체를 회수하는 독립 타이머가 필요하다.
        watchdog = threading.Timer(
            max(1.0, deadline - _now()),
            self._hard_stop,
            args=(proc,),
        )
        watchdog.daemon = True
        watchdog.start()
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                stdout_buf.append(line)
                log_fh.write(line)
                log_fh.flush()
                self._update_progress(record, line, run_start, spec.timeout)
                if _now() > deadline:
                    self._hard_stop(proc)
                    break
        except Exception:  # noqa: BLE001 - 스트림 읽기 실패는 종료 처리로 흡수.
            pass
        finally:
            log_fh.close()

        returncode = proc.wait()
        watchdog.cancel()
        finished = _now()
        full_stdout = "".join(stdout_buf)
        cancelled = record.job_id in self._cancel_requested
        self._finalize(record, returncode, full_stdout, finished, cancelled, deadline)

    def _finalize(
        self,
        record: BacktestJobRecord,
        returncode: int,
        stdout: str,
        finished: float,
        cancelled: bool,
        deadline: float,
    ) -> None:
        payload = _parse_cli_json(stdout)
        status = payload.get("status")
        csv_path = payload.get("csv_path")
        metrics = payload.get("metrics")
        diagnostics = payload.get("backtest_process_diagnostics") or _protocol_summary(stdout)
        mode = str((record.spec or {}).get("mode", "backtest") or "backtest")

        with self._lock:
            record.returncode = returncode
            record.finished_at = finished
            record.csv_path = csv_path
            record.metrics = metrics
            record.process_diagnostics = diagnostics if isinstance(diagnostics, dict) else None
            record.progress = 1.0
            if cancelled or record.job_id in self._cancel_requested:
                record.status = "cancelled"
                record.phase = "cancelled"
                record.message = "실행 중 취소됨"
            elif finished > deadline:
                record.status = "timeout"
                record.phase = "timeout"
                record.message = f"timeout (>{int(deadline - (record.started_at or finished))}s)"
            elif mode in ("wfo", "sweep") and returncode == 0 and status == "ok":
                # wfo/sweep 은 csv_path 없이 구조화 결과(windows/rounds/results)를 낸다.
                #   전체 payload 를 mode_result 로 보존해 API 가 모드별 표로 반환한다.
                record.status = "success"
                record.phase = "done"
                record.message = "ok"
                record.mode_result = payload
            elif returncode == 0 and status == "success" and csv_path:
                record.status = "success"
                record.phase = "done"
                record.message = "ok"
            elif _is_no_trades(returncode, payload):
                record.status = "no_trades"
                record.phase = "done"
                record.message = "거래 0건 — 전략이 해당 기간에 매수 신호를 내지 않음"
            else:
                record.status = "error"
                record.phase = "error"
                msg = payload.get("message") or ""
                checkpoint = payload.get("last_checkpoint") or ""
                record.message = f"non-success: exit={returncode} status={status} {msg} {checkpoint}".strip()
            self._cancel_requested.discard(record.job_id)
            forget_activity(record.job_id)
            self._persist(record)
            final_event = "backtest_done" if record.status in ("success", "no_trades") else "error"
            _telemetry(
                final_event,
                record,
                stage=record.phase,
                message=record.message or record.status,
                percent=100.0,
            )

    def _update_progress(
        self, record: BacktestJobRecord, line: str, run_start: float, timeout: int
    ) -> None:
        """stdout 라인/경과시간으로 진행률을 비차단 추정한다(정밀할 필요 없음)."""
        elapsed = _now() - run_start
        est = min(0.95, 0.05 + elapsed / max(1.0, float(timeout)))
        lowered = line.lower()
        if "csv" in lowered or "csv_detected" in line:
            est = max(est, 0.9)
        elif "engine" in lowered or "백테" in line:
            est = max(est, 0.3)
        with self._lock:
            if est > record.progress:
                record.progress = est
                self._persist(record)
                _telemetry(
                    "backtest_progress",
                    record,
                    stage=record.phase,
                    message=line.strip() or "backtest progress",
                    percent=round(record.progress * 100.0, 4),
                )

    # ----------------------------------------------------------- process kill
    def _hard_stop(
        self,
        proc: subprocess.Popen[str],
        *,
        grace: float = 10.0,
    ) -> bool:
        """프로세스 **트리 전체**를 강제 회수한다(자식 우선, 그 다음 부모).

        부모만 죽이면 CLI 가 spawn 한 엔진/BackTest 자식들이 상속받은 stdout
        파이프를 계속 쥐고 있어 `for line in proc.stdout` 가 EOF 를 영원히 받지
        못한다 → 워커 스레드가 영구 블록되고 동시 1실행 슬롯이 해제되지 않아
        후속 잡이 pending 에 갇힌다(2026-06-12 실측). 트리 킬로 파이프의 모든
        보유자를 정리해야 읽기 루프가 풀린다.
        """
        with self._lock:
            process_job = self._process_job if self._proc is proc else None
        if process_job is not None and process_job.terminate():
            if proc.poll() is None:
                try:
                    proc.wait(timeout=grace)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            return True

        had_children = False
        try:
            import psutil  # noqa: PLC0415 - 킬 경로에서만 필요(콜드 임포트 회피).

            descendants: List[psutil.Process] = []
            descendant_pids: set[int] = set()
            parent_pids = {proc.pid}
            candidates = list(psutil.process_iter(["pid", "ppid"]))
            while parent_pids:
                next_parent_pids: set[int] = set()
                for candidate in candidates:
                    if candidate.pid not in descendant_pids and candidate.info["ppid"] in parent_pids:
                        descendants.append(candidate)
                        descendant_pids.add(candidate.pid)
                        next_parent_pids.add(candidate.pid)
                parent_pids = next_parent_pids
            children = list(reversed(descendants))
            had_children = bool(children)
            for child in children:
                try:
                    child.kill()
                except psutil.Error:
                    pass
            if children:
                try:
                    psutil.wait_procs(children, timeout=grace)
                except psutil.Error:
                    pass
        except ImportError:
            pass  # psutil 부재 시 부모 단독 킬로 폴백(파이프 잔류 위험은 워치독이 보완).
        if proc.poll() is not None:
            return had_children
        try:
            proc.terminate()
            try:
                proc.wait(timeout=grace)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        except OSError:
            pass
        return True

    # -------------------------------------------------------------- persistence
    def _new_job_id(self, buy: str) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        safe = "".join(ch for ch in buy if ch.isalnum())[:24] or "job"
        return f"{ts}_{safe}_{int(time.time() * 1000) % 100000}"

    def _persist(self, record: BacktestJobRecord) -> None:
        try:
            path = self._jobs_dir / f"{record.job_id}.json"
            tmp = path.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(record.to_public(), fh, ensure_ascii=False)
            os.replace(tmp, path)
        except OSError:
            pass  # 영속 실패는 in-memory 진행을 막지 않는다.

    def _load_persisted(self) -> None:
        """서버 재시작 후 과거 잡 결과를 in-memory 로 복원한다(running 은 stale 처리)."""
        try:
            files = sorted(self._jobs_dir.glob("*.json"))
        except OSError:
            return
        for path in files:
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                continue
            if not isinstance(data, dict) or "job_id" not in data:
                continue
            # 재시작으로 잃은 running/pending 은 더 추적 불가 → stale error 표시.
            if data.get("status") in ("running", "pending"):
                data["status"] = "error"
                data["phase"] = "stale"
                data["message"] = "서버 재시작으로 추적 불가(과거 잡)"
            record = self._record_from_dict(data)
            if record is not None:
                self._records[record.job_id] = record

    @staticmethod
    def _record_from_dict(data: Dict[str, Any]) -> Optional[BacktestJobRecord]:
        try:
            allowed = {f for f in BacktestJobRecord.__dataclass_fields__}
            filtered = {k: v for k, v in data.items() if k in allowed}
            return BacktestJobRecord(**filtered)
        except (TypeError, ValueError):
            return None

    def _read_log_tail(self, job_id: str, lines: int) -> List[str]:
        path = self._jobs_dir / f"{job_id}.log"
        if not path.is_file() or lines <= 0:
            return []
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.readlines()
        except OSError:
            return []
        return [ln.rstrip("\n") for ln in content[-lines:]]


def _parse_cli_json(stdout: str) -> Dict[str, Any]:
    """CLI --format json stdout 에서 결과 JSON 을 파싱한다(loop._parse_cli_json 동형)."""
    text = stdout.strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    without_protocol = "\n".join(
        line for line in text.splitlines()
        if not line.strip().startswith("[CLI_DIAG] ")
    ).strip()
    if without_protocol:
        try:
            parsed = json.loads(without_protocol)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            return parsed
    # protocol JSONL이 결과 앞에 스트리밍될 수 있으므로 마지막 완전한 JSON 행을 우선한다.
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if not candidate or candidate.startswith("[CLI_DIAG] "):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _protocol_summary(stdout: str) -> Optional[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    prefix = "[CLI_DIAG] "
    for line in stdout.splitlines():
        text = line.strip()
        if not text.startswith(prefix):
            continue
        try:
            event = json.loads(text[len(prefix):])
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    if not events:
        return None
    last_by_source: Dict[str, str] = {}
    last_detail_by_source: Dict[str, Dict[str, Any]] = {}
    for event in events:
        source = str(event.get("source") or "")
        checkpoint = str(event.get("checkpoint") or "")
        if source and checkpoint:
            last_by_source[source] = checkpoint
            detail = event.get("detail")
            if isinstance(detail, dict):
                last_detail_by_source[source] = {
                    str(key)[:64]: value
                    for key, value in detail.items()
                    if value is None or isinstance(value, (bool, int, float, str))
                }
    return {
        "event_count": len(events),
        "last_checkpoint": events[-1].get("checkpoint"),
        "last_by_source": last_by_source,
        "last_detail_by_source": last_detail_by_source,
    }


def _is_no_trades(returncode: int, payload: Dict[str, Any]) -> bool:
    """CLI 가 '거래 없음 정상 종결'을 보고했는지 판별한다.

    backtest.py Report() 는 list_tsg 가 비면 SysExit(True) → exit=2 로 끝나며,
    CLI 는 message 에 'backtest completed without metrics' 를 포함해 종료한다.
    두 패턴을 함께 확인해야 오탐을 막는다(exit=2 단독은 다른 오류일 수 있음).
    """
    msg = (payload.get("message") or "").lower()
    # CLI 명시 메시지: "backtest completed without metrics"
    if "without metrics" in msg:
        return True
    # exit=2 + CLI 가 status="error" + message 에 metrics/trade 관련 키워드
    if returncode == 2 and "metric" in msg:
        return True
    return False


# 모듈 레벨 싱글톤 — API 라우트가 공유한다(app.py 추가 수정 없이 import 만으로 연결).
_manager: Optional[BacktestJobManager] = None
_manager_lock = threading.Lock()


def _default_job_strategy_db() -> Path:
    override = os.environ.get("STOM_WEBBT_JOB_STRATEGY_DB")
    return Path(override) if override else _OPERATIONAL_STRATEGY_DB


def _default_job_backtest_db() -> Optional[Path]:
    override = os.environ.get("STOM_WEBBT_JOB_BACKTEST_DB")
    return Path(override) if override else None


def get_job_manager() -> BacktestJobManager:
    """프로세스 전역 잡 매니저 싱글톤을 반환한다(지연 초기화)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = BacktestJobManager(
                    strategy_db=_default_job_strategy_db(),
                    backtest_db=_default_job_backtest_db(),
                )
    return _manager
