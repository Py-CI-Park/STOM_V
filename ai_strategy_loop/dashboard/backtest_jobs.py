"""Backtest workbench job manager — subprocess 백테 잡 큐/상태/취소 (PR2).

웹 워크벤치가 띄우는 백테스트 잡 1개(동시 실행 1개, 나머지는 큐잉)를 관리한다.
controller/loop.py 의 검증된 subprocess 계약(`stom_backtest.py --format json`)을 그대로
재사용하되, 운영 ``_database/strategy.db`` 를 대상으로 한다(루프 격리 DB가 아님).

설계 계약:
  - 동시 실행 1개. start 시 이미 running 이면 큐에 적재(FIFO), 워커 스레드가 순차 처리.
  - 잡 메타는 in-memory dict + ``state/webbt_jobs/<job_id>.json`` 영속(서버 재시작 후
    과거 잡 결과 조회 가능). stdout/stderr 는 ``<job_id>.log`` 로 기록(state 는 gitignored).
  - cancel 은 LoopProcessManager 의 terminate→grace→kill→wait 패턴 재사용(좀비 reap).
  - command_builder 주입점: 테스트는 단명 가짜 커맨드를 주입해 라이프사이클을 검증한다.
  - 무예외에 가깝게: 잡 실패도 status='error'/'timeout' 레코드로 표준화(예외 누수 금지).
"""

from __future__ import annotations

import json
import os
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
from ai_strategy_loop.controller.telemetry import dashboard_telemetry

# 패키지 루트(.../ai_strategy_loop) 기준 경로. CWD 무관.
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = _PACKAGE_DIR.parent
_JOBS_DIR = _PACKAGE_DIR / "state" / "webbt_jobs"

# 운영 strategy.db (bootstrap 이 STOM_CLI_DB_STRATEGY 를 루프 격리 DB로 바꿔두므로,
#   워크벤치는 env 오버라이드를 무시하고 운영 _database/strategy.db 를 명시 대상으로 한다).
_OPERATIONAL_STRATEGY_DB = REPO_ROOT / "_database" / "strategy.db"

# 진행 로그 테일 기본 줄 수.
_LOG_TAIL_LINES = 50
# stdout/stderr 폴링 간격.
_POLL_SEC = 0.4

CommandBuilder = Callable[["BacktestJobSpec"], List[str]]


@dataclass
class BacktestJobSpec:
    """잡 실행 파라미터. /bt/run 페이로드에서 검증 후 생성된다."""

    buy: str
    sell: str
    start: int
    end: int
    buy_code: Optional[str] = None
    sell_code: Optional[str] = None
    timeframe: str = "min"
    engines: int = 4
    timeout: int = 600
    divid_mode: str = "종목코드별 분류"
    one_code: Optional[str] = None
    # 스모크/서브셋 백테용: 절대 경로를 주면 STOM_CLI_DB_STOCK_BACK_TICK/MIN 으로 주입된다.
    back_db_override: Optional[str] = None
    # 실행 모드(GUI 패리티 진입점):
    #   "backtest"(기본, --buy/--sell 단일 실행)
    #   "optimize"(stom_backtest optimize 래핑 — param_space JSON 파일 필수)
    #   "wfo"(stom_backtest wfo 래핑 — 전진분석, train/test 윈도우 필수)
    #   "sweep"(stom_backtest sweep param|rolling 래핑 — sweep_action 으로 분기)
    mode: str = "backtest"
    # optimize/wfo 모드 파라미터 탐색공간 JSON 파일 절대경로(--param-space 로 전달).
    param_space: Optional[str] = None
    # optimize/wfo 방법(grid|random)·목표지표.
    opt_method: str = "grid"
    opt_objective: str = "tpi"
    # wfo(전진분석) train/test 윈도우 크기(일). mode=="wfo" 필수(>=1).
    train_window_days: int = 0
    test_window_days: int = 0
    # wfo/sweep rolling 윈도우 이동 간격(일). wfo 미지정(0)이면 test_window_days 사용.
    step_days: int = 0
    # sweep 하위 동작: "param"(조합 스윕, sweep_params JSON 필수) | "rolling"(날짜 롤링).
    sweep_action: str = "param"
    # sweep param 모드 파라미터 조합 JSON 파일 절대경로(--params 로 전달).
    sweep_params: Optional[str] = None
    # sweep rolling 모드 윈도우 크기(일). mode=="sweep" + sweep_action=="rolling" 필수(>=1).
    window_days: int = 0


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
        deadline_grace: float = 60.0,
    ) -> None:
        self._jobs_dir = Path(jobs_dir) if jobs_dir else _JOBS_DIR
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._command_builder = command_builder or default_command_builder
        self._strategy_db = Path(strategy_db) if strategy_db else _OPERATIONAL_STRATEGY_DB
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
        with self._lock:
            record = BacktestJobRecord(job_id=job_id, spec=asdict(spec))
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
        # 워크벤치는 운영 strategy.db 를 대상으로 한다(bootstrap 의 루프 격리 오버라이드를 되돌림).
        env["STOM_CLI_DB_STRATEGY"] = str(self._strategy_db)
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
        mode = str((record.spec or {}).get("mode", "backtest") or "backtest")

        with self._lock:
            record.returncode = returncode
            record.finished_at = finished
            record.csv_path = csv_path
            record.metrics = metrics
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
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


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


def get_job_manager() -> BacktestJobManager:
    """프로세스 전역 잡 매니저 싱글톤을 반환한다(지연 초기화)."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = BacktestJobManager()
    return _manager
