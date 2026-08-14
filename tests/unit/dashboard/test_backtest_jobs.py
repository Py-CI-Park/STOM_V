"""Backtest job manager 라이프사이클 테스트 (PR2).

실제 백테 대신 단명 가짜 커맨드(sys.executable -c "...")를 command_builder 로 주입해
잡 라이프사이클(시작→완료/취소)을 검증한다. 동시 1개 큐잉도 확인한다.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.dashboard import backtest_jobs as backtest_jobs_module  # noqa: E402
from ai_strategy_loop.dashboard.backtest_jobs import (  # noqa: E402
    BacktestJobManager,
    BacktestJobSpec,
)


def _spec(
    buy: str = "테스트매수",
    *,
    start: int = 20250407,
    end: int = 20250409,
    timeframe: str = "min",
    timeout: int = 600,
) -> BacktestJobSpec:
    return BacktestJobSpec(
        buy=buy,
        sell="테스트매도",
        start=start,
        end=end,
        buy_code=f"if {buy!r}:\n    매수 = True\n",
        sell_code="if '테스트매도':\n    매도 = True\n",
        timeframe=timeframe,
        timeout=timeout,
    )


def _success_command(csv_path: str):
    """status=success JSON 을 stdout 으로 즉시 뱉는 가짜 백테 커맨드.

    Windows 콘솔 인코딩 이슈를 피하려 ASCII 키만 쓰고 json.dumps 로 직렬화한다.
    """
    code = (
        "import json;"
        f"print(json.dumps({{'status':'success','csv_path':{csv_path!r},"
        "'metrics':{'total_profit_pct':12.5},"
        "'backtest_process_diagnostics':{'event_count':2,"
        "'last_checkpoint':'backtest_child_mq_first_received',"
        "'last_by_source':{'BackTest':'backtest_child_mq_first_received'}}}))"
    )

    def builder(spec):
        return [sys.executable, "-c", code]
    return builder


def _slow_command():
    """일정 시간 sleep 하는 가짜 백테(취소 테스트용). ASCII stdout 으로 인코딩 안전."""
    def builder(spec):
        return [sys.executable, "-c", "import time,sys; print('engine started'); sys.stdout.flush(); time.sleep(30)"]
    return builder


def _error_command():
    """status=error JSON 을 뱉는 가짜 백테."""
    def builder(spec):
        return [sys.executable, "-c", 'print(\'{"status": "error", "message": "no trades"}\')']
    return builder


def _wait_status(manager, job_id, targets, timeout=15.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rec = manager.get(job_id)
        if rec.get("status") in targets:
            return rec
        time.sleep(0.1)
    return manager.get(job_id)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _write_strategy_db(path: Path, *, buy: str, sell: str, buy_code: str, sell_code: str) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('INSERT INTO stockbuy VALUES (?, ?)', (buy, buy_code))
        con.execute('INSERT INTO stocksell VALUES (?, ?)', (sell, sell_code))
        con.commit()
    finally:
        con.close()


def _read_strategy_code(path: Path, table: str, name: str) -> str:
    con = sqlite3.connect(path)
    try:
        row = con.execute(
            f'SELECT "전략코드" FROM {table} WHERE "index" = ?',
            (name,),
        ).fetchone()
        return row[0]
    finally:
        con.close()


# ------------------------------------------------------------------ lifecycle
def test_submit_and_success(tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/fake.csv"),
    )
    res = manager.submit(_spec())
    assert res["status"] == "ok"
    job_id = res["job_id"]

    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "success"
    assert rec["csv_path"] == "backtest/csv/fake.csv"
    assert rec["metrics"]["total_profit_pct"] == 12.5
    assert rec["process_diagnostics"]["event_count"] == 2
    assert rec["process_diagnostics"]["last_checkpoint"] == "backtest_child_mq_first_received"
    assert rec["progress"] == 1.0
    assert manager.result_csv_path(job_id) == "backtest/csv/fake.csv"


def test_protocol_jsonl_preserves_checkpoint_and_final_json():
    output = "\n".join([
        '[CLI_DIAG] {"source":"BackTest","checkpoint":"waiting_first"}',
        '[CLI_DIAG] {"source":"BackTest","checkpoint":"waiting_heartbeat"}',
        '{"status":"success","csv_path":"x.csv","metrics":{}}',
    ])
    assert backtest_jobs_module._parse_cli_json(output)["status"] == "success"
    assert backtest_jobs_module._protocol_summary(output) == {
        "event_count": 2,
        "last_checkpoint": "waiting_heartbeat",
        "last_by_source": {"BackTest": "waiting_heartbeat"},
        "last_detail_by_source": {},
    }


def test_protocol_jsonl_allows_pretty_printed_final_json():
    output = "\n".join([
        '[CLI_DIAG] {"source":"BackTest","checkpoint":"completed"}',
        "{",
        '  "status": "success",',
        '  "csv_path": "x.csv",',
        '  "metrics": {}',
        "}",
    ])
    assert backtest_jobs_module._parse_cli_json(output)["status"] == "success"


def test_job_strategy_db_override_is_explicit_and_default_preserving(monkeypatch, tmp_path):
    monkeypatch.delenv("STOM_WEBBT_JOB_STRATEGY_DB", raising=False)
    monkeypatch.delenv("STOM_WEBBT_JOB_BACKTEST_DB", raising=False)
    assert backtest_jobs_module._default_job_strategy_db() == (
        backtest_jobs_module._OPERATIONAL_STRATEGY_DB
    )
    assert backtest_jobs_module._default_job_backtest_db() is None
    sidecar = tmp_path / "strategy.db"
    backtest_sidecar = tmp_path / "backtest.db"
    monkeypatch.setenv("STOM_WEBBT_JOB_STRATEGY_DB", str(sidecar))
    monkeypatch.setenv("STOM_WEBBT_JOB_BACKTEST_DB", str(backtest_sidecar))
    assert backtest_jobs_module._default_job_strategy_db() == sidecar
    assert backtest_jobs_module._default_job_backtest_db() == backtest_sidecar


def test_submit_creates_immutable_strategy_snapshot_and_child_env(tmp_path: Path):
    buy_code = "if original_buy:\n    매수 = True\n"
    sell_code = "if original_sell:\n    매도 = True\n"
    source_db = tmp_path / "source_strategy.db"
    _write_strategy_db(
        source_db,
        buy="스냅매수",
        sell="스냅매도",
        buy_code="source buy should be overwritten",
        sell_code="source sell should be overwritten",
    )
    builder_entered = threading.Event()
    release_builder = threading.Event()

    def snapshot_reader(spec):
        builder_entered.set()
        assert release_builder.wait(timeout=5.0)
        code = (
            "import hashlib,json,os,sqlite3;"
            "strategy=os.environ['STOM_CLI_DB_STRATEGY'];"
            "backtest=os.environ['STOM_CLI_DB_BACKTEST'];"
            "csvdir=os.environ['STOM_CLI_BACKTEST_CSV_DIR'];"
            f"buy_name={spec.buy!r};sell_name={spec.sell!r};"
            "con=sqlite3.connect(strategy);"
            "buy=con.execute('SELECT \"전략코드\" FROM stockbuy WHERE \"index\"=?',(buy_name,)).fetchone()[0];"
            "sell=con.execute('SELECT \"전략코드\" FROM stocksell WHERE \"index\"=?',(sell_name,)).fetchone()[0];"
            "con.close();"
            "print(json.dumps({'status':'success','csv_path':'snapshot.csv','metrics':{"
            "'strategy_path':strategy,'backtest_path':backtest,'csv_dir':csvdir,"
            "'buy_code':buy,'sell_code':sell,"
            "'buy_hash':hashlib.sha256(buy.encode('utf-8')).hexdigest(),"
            "'sell_hash':hashlib.sha256(sell.encode('utf-8')).hexdigest()"
            "}}, ensure_ascii=False))"
        )
        return [sys.executable, "-c", code]

    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=snapshot_reader,
        strategy_db=source_db,
    )
    submitted = manager.submit(BacktestJobSpec(
        buy="스냅매수",
        sell="스냅매도",
        start=20250407,
        end=20250409,
        buy_code=buy_code,
        sell_code=sell_code,
    ))
    assert submitted["status"] == "ok"
    job_id = submitted["job_id"]
    assert builder_entered.wait(timeout=5.0)

    con = sqlite3.connect(source_db)
    try:
        con.execute('UPDATE stockbuy SET "전략코드"=? WHERE "index"=?', ("mutated buy", "스냅매수"))
        con.execute('UPDATE stocksell SET "전략코드"=? WHERE "index"=?', ("mutated sell", "스냅매도"))
        con.commit()
    finally:
        con.close()

    release_builder.set()
    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "success"

    jobs_root = (tmp_path / "jobs").resolve()
    strategy_snapshot = Path(rec["strategy_db_snapshot_path"]).resolve()
    backtest_snapshot = Path(rec["backtest_db_snapshot_path"]).resolve()
    csv_snapshot = Path(rec["csv_dir_snapshot_path"]).resolve()
    assert jobs_root in strategy_snapshot.parents
    assert jobs_root in backtest_snapshot.parents
    assert jobs_root in csv_snapshot.parents
    assert strategy_snapshot.name == "strategy.db"
    assert backtest_snapshot.name == "backtest.db"
    assert csv_snapshot.name == "csv"
    assert strategy_snapshot.parent == backtest_snapshot.parent == csv_snapshot.parent
    assert strategy_snapshot.is_file()
    assert backtest_snapshot.is_file()
    assert csv_snapshot.is_dir()

    expected_hashes = {"buy": _hash_code(buy_code), "sell": _hash_code(sell_code)}
    assert rec["strategy_db_snapshot_hashes"] == expected_hashes
    assert _read_strategy_code(strategy_snapshot, "stockbuy", "스냅매수") == buy_code
    assert _read_strategy_code(strategy_snapshot, "stocksell", "스냅매도") == sell_code
    assert _read_strategy_code(source_db, "stockbuy", "스냅매수") == "mutated buy"

    metrics = rec["metrics"]
    assert Path(metrics["strategy_path"]).resolve() == strategy_snapshot
    assert Path(metrics["backtest_path"]).resolve() == backtest_snapshot
    assert Path(metrics["csv_dir"]).resolve() == csv_snapshot
    assert metrics["buy_code"] == buy_code
    assert metrics["sell_code"] == sell_code
    assert metrics["buy_hash"] == expected_hashes["buy"]
    assert metrics["sell_hash"] == expected_hashes["sell"]


def test_web_job_child_env_uses_unique_strategy_backtest_and_csv_artifacts(tmp_path: Path):
    def env_echo(spec):
        code = (
            "import json,os;"
            "csvdir=os.environ['STOM_CLI_BACKTEST_CSV_DIR'];"
            "print(json.dumps({'status':'success','csv_path':os.path.join(csvdir,'result.csv'),"
            "'metrics':{'strategy':os.environ['STOM_CLI_DB_STRATEGY'],"
            "'backtest':os.environ['STOM_CLI_DB_BACKTEST'],"
            "'csv_dir':csvdir}}))"
        )
        return [sys.executable, "-c", code]

    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=env_echo,
        strategy_db=tmp_path / "source_strategy.db",
    )
    first_id = manager.submit(_spec("first"))["job_id"]
    second_id = manager.submit(_spec("second"))["job_id"]

    first = _wait_status(manager, first_id, {"success", "error", "timeout"})
    second = _wait_status(manager, second_id, {"success", "error", "timeout"})

    assert first["status"] == "success"
    assert second["status"] == "success"
    first_paths = {
        "strategy": Path(first["metrics"]["strategy"]).resolve(),
        "backtest": Path(first["metrics"]["backtest"]).resolve(),
        "csv_dir": Path(first["metrics"]["csv_dir"]).resolve(),
    }
    second_paths = {
        "strategy": Path(second["metrics"]["strategy"]).resolve(),
        "backtest": Path(second["metrics"]["backtest"]).resolve(),
        "csv_dir": Path(second["metrics"]["csv_dir"]).resolve(),
    }

    assert first_paths["strategy"] == Path(first["strategy_db_snapshot_path"]).resolve()
    assert first_paths["backtest"] == Path(first["backtest_db_snapshot_path"]).resolve()
    assert first_paths["csv_dir"] == Path(first["csv_dir_snapshot_path"]).resolve()
    assert second_paths["strategy"] == Path(second["strategy_db_snapshot_path"]).resolve()
    assert second_paths["backtest"] == Path(second["backtest_db_snapshot_path"]).resolve()
    assert second_paths["csv_dir"] == Path(second["csv_dir_snapshot_path"]).resolve()
    assert first_paths["strategy"] != second_paths["strategy"]
    assert first_paths["backtest"] != second_paths["backtest"]
    assert first_paths["csv_dir"] != second_paths["csv_dir"]
    assert first_paths["csv_dir"].is_dir()
    assert second_paths["csv_dir"].is_dir()


def test_submit_rejects_missing_code_snapshot(tmp_path: Path):
    def never_spawn(spec):
        raise AssertionError("missing code must fail before command construction")

    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=never_spawn)
    result = manager.submit(BacktestJobSpec(
        buy="매수A",
        sell="매도A",
        start=20250407,
        end=20250409,
        buy_code="if A:\n    매수 = True\n",
    ))

    assert result["status"] == "error"
    assert "sell code snapshot missing" in result["message"]
    assert manager.list_jobs()["count"] == 0


def test_normal_queued_jobs_complete_and_release_slot(tmp_path: Path):
    first_builder_entered = threading.Event()
    release_first_builder = threading.Event()

    def queued_success(spec):
        if spec.buy == "first":
            first_builder_entered.set()
            assert release_first_builder.wait(timeout=5.0)
        return _success_command(f"backtest/csv/{spec.buy}.csv")(spec)

    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=queued_success,
    )
    first_id = manager.submit(_spec("first"))["job_id"]
    assert first_builder_entered.wait(timeout=5.0)
    second_id = manager.submit(_spec("second"))["job_id"]
    worker = manager._worker
    assert worker is not None

    release_first_builder.set()
    worker.join(timeout=10.0)

    assert not worker.is_alive()
    assert manager.get(first_id)["status"] == "success"
    assert manager.get(second_id)["status"] == "success"
    assert manager._current_job is None
    assert manager._proc is None
    assert manager._queue == []


def test_error_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_error_command())
    job_id = manager.submit(_spec())["job_id"]
    rec = _wait_status(manager, job_id, {"success", "error", "timeout"})
    assert rec["status"] == "error"
    assert "no trades" in rec["message"]


def test_cancel_running_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_slow_command())
    job_id = manager.submit(_spec())["job_id"]
    # running 상태가 될 때까지 대기.
    rec = _wait_status(manager, job_id, {"running"}, timeout=10.0)
    assert rec["status"] == "running"
    cancel = manager.cancel(job_id)
    assert cancel["status"] == "ok"
    rec = _wait_status(manager, job_id, {"cancelled", "error", "timeout"}, timeout=15.0)
    assert rec["status"] == "cancelled"


def test_cancel_queued_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_slow_command())
    first = manager.submit(_spec("first"))["job_id"]
    second = manager.submit(_spec("second"))["job_id"]
    # second 는 큐에서 대기 → 큐 취소 가능.
    _wait_status(manager, first, {"running"}, timeout=10.0)
    cancel = manager.cancel(second)
    assert cancel["status"] == "ok"
    assert cancel["cancelled"] == "queued"
    assert manager.get(second)["status"] == "cancelled"
    # 정리: 실행 중인 first 도 취소.
    manager.cancel(first)


def test_cancel_before_spawn_prevents_child_and_releases_slot(monkeypatch, tmp_path: Path):
    builder_entered = threading.Event()
    release_builder = threading.Event()
    spawned_commands = []
    real_popen = backtest_jobs_module.subprocess.Popen

    def gated_builder(spec):
        if spec.buy == "first":
            builder_entered.set()
            assert release_builder.wait(timeout=5.0)
        return _success_command(f"backtest/csv/{spec.buy}.csv")(spec)

    def tracking_popen(*args, **kwargs):
        spawned_commands.append(args[0])
        return real_popen(*args, **kwargs)

    monkeypatch.setattr(backtest_jobs_module.subprocess, "Popen", tracking_popen)
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=gated_builder,
    )
    first_id = manager.submit(_spec("first"))["job_id"]
    assert builder_entered.wait(timeout=5.0)
    cancel = manager.cancel(first_id)
    second_id = manager.submit(_spec("second"))["job_id"]
    worker = manager._worker
    assert worker is not None

    release_builder.set()
    worker.join(timeout=10.0)

    assert cancel["cancelled"] == "requested"
    assert not worker.is_alive()
    assert manager.get(first_id)["status"] == "cancelled"
    assert manager.get(second_id)["status"] == "success"
    assert len(spawned_commands) == 1
    assert manager._current_job is None
    assert manager._proc is None


def test_cancel_between_running_and_process_registration_stops_child(monkeypatch, tmp_path: Path):
    spawn_entered = threading.Event()
    release_spawn = threading.Event()
    spawned = []
    real_popen = backtest_jobs_module.subprocess.Popen

    def gated_popen(*args, **kwargs):
        spawn_entered.set()
        assert release_spawn.wait(timeout=5.0)
        proc = real_popen(*args, **kwargs)
        spawned.append(proc)
        return proc

    monkeypatch.setattr(backtest_jobs_module.subprocess, "Popen", gated_popen)
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_slow_command(),
    )
    job_id = manager.submit(_spec())["job_id"]
    worker = manager._worker
    assert worker is not None
    assert spawn_entered.wait(timeout=5.0)
    assert manager.get(job_id)["status"] == "running"
    assert manager._proc is None

    cancel = manager.cancel(job_id)
    release_spawn.set()
    worker.join(timeout=10.0)
    needed_manual_cleanup = worker.is_alive()
    if needed_manual_cleanup and spawned:
        manager._hard_stop(spawned[0], grace=1.0)
        worker.join(timeout=5.0)

    assert cancel["cancelled"] == "requested"
    assert not needed_manual_cleanup
    assert not worker.is_alive()
    assert manager.get(job_id)["status"] == "cancelled"
    assert spawned and spawned[0].poll() is not None
    assert manager._current_job is None
    assert manager._proc is None


def test_repeated_cancel_during_spawn_stops_process_once(monkeypatch, tmp_path: Path):
    spawn_entered = threading.Event()
    release_spawn = threading.Event()
    spawned = []
    hard_stop_calls = []
    real_popen = backtest_jobs_module.subprocess.Popen
    real_hard_stop = BacktestJobManager._hard_stop

    def gated_popen(*args, **kwargs):
        spawn_entered.set()
        assert release_spawn.wait(timeout=5.0)
        proc = real_popen(*args, **kwargs)
        spawned.append(proc)
        return proc

    def counting_hard_stop(self, proc, *, grace=10.0):
        hard_stop_calls.append(proc.pid)
        return real_hard_stop(self, proc, grace=grace)

    monkeypatch.setattr(backtest_jobs_module.subprocess, "Popen", gated_popen)
    monkeypatch.setattr(BacktestJobManager, "_hard_stop", counting_hard_stop)
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/misleading-success.csv"),
    )
    job_id = manager.submit(_spec())["job_id"]
    worker = manager._worker
    assert worker is not None
    assert spawn_entered.wait(timeout=5.0)

    first_cancel = manager.cancel(job_id)
    second_cancel = manager.cancel(job_id)
    release_spawn.set()
    worker.join(timeout=10.0)
    needed_manual_cleanup = worker.is_alive()
    if needed_manual_cleanup and spawned:
        real_hard_stop(manager, spawned[0], grace=1.0)
        worker.join(timeout=5.0)

    assert first_cancel["cancelled"] == "requested"
    assert second_cancel["cancelled"] == "requested"
    assert not needed_manual_cleanup
    assert not worker.is_alive()
    assert manager.get(job_id)["status"] == "cancelled"
    assert len(hard_stop_calls) == 1
    assert spawned and spawned[0].poll() is not None


def test_cancelled_job_stays_cancelled_when_builder_is_interrupted(tmp_path: Path):
    builder_entered = threading.Event()
    release_builder = threading.Event()

    class BuilderInterrupted(RuntimeError):
        pass

    def interrupted_builder(spec):
        builder_entered.set()
        assert release_builder.wait(timeout=5.0)
        raise BuilderInterrupted

    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=interrupted_builder,
    )
    job_id = manager.submit(_spec())["job_id"]
    worker = manager._worker
    assert worker is not None
    assert builder_entered.wait(timeout=5.0)

    cancel = manager.cancel(job_id)
    release_builder.set()
    worker.join(timeout=10.0)

    assert cancel["cancelled"] == "requested"
    assert not worker.is_alive()
    assert manager.get(job_id)["status"] == "cancelled"
    assert manager._current_job is None
    assert manager._proc is None


# --------------------------------------------------------------- validation
def test_submit_rejects_bad_name(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(buy=""))["status"] == "error"
    assert manager.submit(_spec(buy="bad\nname"))["status"] == "error"


def test_submit_rejects_bad_dates(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(start=20250410, end=20250407))["status"] == "error"
    assert manager.submit(_spec(start=123))["status"] == "error"


def test_submit_rejects_bad_timeframe(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.submit(_spec(timeframe="hour"))["status"] == "error"


# -------------------------------------------------------------- list/persist
def test_list_jobs_and_persistence(tmp_path: Path):
    jobs_dir = tmp_path / "jobs"
    manager = BacktestJobManager(jobs_dir=jobs_dir, command_builder=_success_command("x.csv"))
    job_id = manager.submit(_spec())["job_id"]
    _wait_status(manager, job_id, {"success", "error", "timeout"})
    listing = manager.list_jobs()
    assert listing["count"] >= 1
    assert any(j["job_id"] == job_id for j in listing["jobs"])

    # 재시작 시뮬레이션: 새 매니저가 JSON 영속에서 과거 잡 복원.
    manager2 = BacktestJobManager(jobs_dir=jobs_dir, command_builder=_success_command("x.csv"))
    restored = manager2.get(job_id)
    assert restored["available"] is True
    assert restored["status"] == "success"


def test_get_missing_job(tmp_path: Path):
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=_success_command("x.csv"))
    assert manager.get("nope")["available"] is False


# ------------------------------------------------- watchdog / tree-kill (회귀)
def test_quiet_job_times_out_without_output(tmp_path: Path):
    """--quiet CLI 처럼 stdout 무출력 + 장기 실행이면 워치독이 데드라인에 회수해야 한다.

    회귀 근거(2026-06-12): 데드라인 검사가 stdout 읽기 루프 안에만 있어 무출력
    프로세스에서 타임아웃이 영원히 발동하지 않았다.
    """
    def quiet_slow(spec):
        return [sys.executable, "-c", "import time; time.sleep(60)"]

    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs", command_builder=quiet_slow, deadline_grace=1.0,
    )
    job_id = manager.submit(_spec(timeout=1))["job_id"]
    rec = _wait_status(manager, job_id, {"timeout", "error", "success"}, timeout=20.0)
    assert rec["status"] == "timeout"


def test_cancel_kills_child_tree_and_releases_queue(tmp_path: Path):
    """취소가 자식 트리까지 회수하고 동시 1실행 슬롯을 해제해야 한다.

    회귀 근거(2026-06-12): 부모만 죽이면 spawn 자식이 stdout 파이프를 쥐고 있어
    워커가 EOF 를 못 받고 영구 블록 → 후속 잡이 pending 에 갇혔다.
    """
    spawner = (
        "import subprocess, sys;"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)']);"
        "p.wait()"
    )

    def tree_command(spec):
        return [sys.executable, "-c", spawner]

    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs", command_builder=tree_command)
    job_id = manager.submit(_spec(timeout=300))["job_id"]
    rec = _wait_status(manager, job_id, {"running"}, timeout=10.0)
    assert rec["status"] == "running"

    assert manager.cancel(job_id)["status"] == "ok"
    rec = _wait_status(manager, job_id, {"cancelled", "error", "timeout"}, timeout=20.0)
    assert rec["status"] == "cancelled"

    # 슬롯 해제 검증: 후속 잡이 pending 에 갇히지 않고 완주해야 한다.
    manager._command_builder = _success_command("backtest/csv/after_cancel.csv")
    follow_id = manager.submit(_spec("follow"))["job_id"]
    rec2 = _wait_status(manager, follow_id, {"success", "error", "timeout"}, timeout=20.0)
    assert rec2["status"] == "success"


def test_log_tail_captured(tmp_path: Path):
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=_success_command("backtest/csv/fake.csv"),
    )
    job_id = manager.submit(_spec())["job_id"]
    _wait_status(manager, job_id, {"success", "error", "timeout"})
    rec = manager.get(job_id, log_tail=50)
    assert isinstance(rec["log_tail"], list)
    assert any("success" in line for line in rec["log_tail"])
