from __future__ import annotations

import sys
import subprocess
import threading
import time
from pathlib import Path

import psutil
import pytest

from ai_strategy_loop.dashboard import backtest_jobs as backtest_jobs_module
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobManager, BacktestJobSpec


def test_cancel_after_process_exit_precedes_success_finalization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given a successful child whose result parsing is paused after cancellation was snapshotted.
    finalize_entered = threading.Event()
    release_finalize = threading.Event()
    real_parse = backtest_jobs_module._parse_cli_json

    def gated_parse(stdout: str):
        finalize_entered.set()
        assert release_finalize.wait(timeout=5.0)
        return real_parse(stdout)

    monkeypatch.setattr(backtest_jobs_module, "_parse_cli_json", gated_parse)
    command = [
        sys.executable,
        "-u",
        "-c",
        (
            "import json; "
            "print(json.dumps({'status': 'success', "
            "'csv_path': 'backtest/csv/misleading.csv'}), flush=True)"
        ),
    ]
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=lambda _spec: command,
    )
    submitted = manager.submit(
        BacktestJobSpec(
            buy="finalize-race",
            sell="sell",
            buy_code="매수 = True",
            sell_code="매도 = False",
            start=20250407,
            end=20250409,
        )
    )
    job_id = str(submitted["job_id"])
    worker = manager._worker
    assert worker is not None
    assert finalize_entered.wait(timeout=5.0)
    proc = manager._proc
    assert proc is not None
    assert proc.poll() == 0

    # When cancellation is accepted before the terminal record is persisted.
    cancel = manager.cancel(job_id)
    release_finalize.set()
    worker.join(timeout=5.0)

    # Then cancellation wins over the already-buffered success payload.
    assert cancel["cancelled"] == "running"
    assert not worker.is_alive()
    assert manager.get(job_id)["status"] == "cancelled"
    assert manager._current_job is None
    assert manager._proc is None


def test_cancel_reaps_hung_descendant_after_parent_exits(tmp_path: Path) -> None:
    # Given a parent that exits after spawning a hung child which retains the manager stdout pipe.
    pid_file = tmp_path / "tree-pids.txt"
    parent_code = """
import json
import os
import subprocess
import sys

child = subprocess.Popen([sys.executable, "-u", "-c", "import time; time.sleep(60)"])
with open(sys.argv[1], "w", encoding="utf-8") as stream:
    stream.write(f"{os.getpid()},{child.pid}")
print(json.dumps({"status": "success", "csv_path": "backtest/csv/misleading.csv"}), flush=True)
"""
    command = [sys.executable, "-u", "-c", parent_code, str(pid_file)]
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=lambda _spec: command,
    )
    submitted = manager.submit(
        BacktestJobSpec(
            buy="orphan-tree",
            sell="sell",
            buy_code="매수 = True",
            sell_code="매도 = False",
            start=20250407,
            end=20250409,
        )
    )
    job_id = str(submitted["job_id"])
    worker = manager._worker
    child: psutil.Process | None = None
    child_alive_after_cancel = True
    worker_alive_after_cancel = True
    cancel_kind = ""
    try:
        assert worker is not None
        file_deadline = time.monotonic() + 5.0
        while not pid_file.is_file() and time.monotonic() < file_deadline:
            time.sleep(0.01)
        assert pid_file.is_file()
        _parent_text, child_text = pid_file.read_text(encoding="utf-8").split(",")
        child = psutil.Process(int(child_text))
        exit_deadline = time.monotonic() + 5.0
        while (
            manager._proc is not None
            and manager._proc.poll() is None
            and time.monotonic() < exit_deadline
        ):
            time.sleep(0.01)
        proc = manager._proc
        assert proc is not None
        assert proc.poll() == 0
        assert manager.get(job_id)["status"] == "running"

        # When cancellation is accepted after the parent has exited.
        cancel = manager.cancel(job_id)
        cancel_kind = str(cancel["cancelled"])
        worker.join(timeout=1.0)
        child_alive_after_cancel = child.is_running()
        worker_alive_after_cancel = worker.is_alive()
    finally:
        if child is not None:
            try:
                if child.is_running():
                    child.kill()
                child.wait(timeout=5.0)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
        if worker is not None:
            worker.join(timeout=5.0)

    # Then the descendant and worker are both reclaimed instead of stranding the queue slot.
    assert cancel_kind == "running"
    assert not child_alive_after_cancel
    assert not worker_alive_after_cancel
    assert manager.get(job_id)["status"] == "cancelled"
    assert manager._current_job is None
    assert manager._proc is None


def test_hard_stop_scans_ppid_when_dead_parent_reports_no_children(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    # Given a terminated parent whose direct child is visible only in the ppid snapshot.
    proc = subprocess.Popen(
        [sys.executable, "-u", "-c", "pass"],
        cwd=tmp_path,
        text=True,
    )
    proc.wait(timeout=5.0)

    class ParentWithoutChildren:
        def __init__(self, _pid: int) -> None:
            pass

        def children(self, *, recursive: bool = False) -> list[psutil.Process]:
            return []

    class SnapshotChild:
        def __init__(self) -> None:
            self.pid = proc.pid + 1
            self.info = {"ppid": proc.pid}
            self.killed = False

        def kill(self) -> None:
            self.killed = True

    child = SnapshotChild()
    monkeypatch.setattr(psutil, "Process", ParentWithoutChildren)
    monkeypatch.setattr(psutil, "process_iter", lambda _attrs: iter([child]))
    monkeypatch.setattr(psutil, "wait_procs", lambda _children, timeout: ([], []))
    manager = BacktestJobManager(jobs_dir=tmp_path / "jobs")

    # When hard-stop runs after the parent has already exited.
    stopped = manager._hard_stop(proc, grace=0.0)

    # Then the ppid snapshot child is still killed and reported as reclaimed.
    assert stopped is True
    assert child.killed is True

