from __future__ import annotations

import sys
import time
from pathlib import Path

import psutil
import pytest

from ai_strategy_loop.dashboard import _windows_process_job as process_job_module
from ai_strategy_loop.dashboard import backtest_jobs as backtest_jobs_module
from ai_strategy_loop.dashboard._windows_process_job import WindowsProcessJob
from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobManager, BacktestJobSpec


class FakeKernel32:
    def __init__(self, *, assignment_succeeds: bool = True) -> None:
        self.assignment_succeeds = assignment_succeeds
        self.closed_handles: list[int] = []
        self.terminated_handles: list[int] = []

    def CreateJobObjectW(self, _attributes, _name) -> int:
        return 41

    def OpenProcess(self, _access, _inherit, _pid) -> int:
        return 42

    def AssignProcessToJobObject(self, _job, _process) -> bool:
        return self.assignment_succeeds

    def TerminateJobObject(self, handle, _exit_code) -> bool:
        self.terminated_handles.append(int(handle.value))
        return True

    def CloseHandle(self, handle) -> bool:
        value = handle if isinstance(handle, int) else handle.value
        self.closed_handles.append(int(value))
        return True


class RecordingProcessJob:
    def __init__(self) -> None:
        self.terminate_calls = 0
        self.close_calls = 0
        self.closed = False

    def terminate(self) -> bool:
        self.terminate_calls += 1
        return not self.closed

    def close(self) -> None:
        if not self.closed:
            self.close_calls += 1
            self.closed = True


def test_assignment_failure_closes_both_native_handles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a Windows kernel adapter that rejects process assignment.
    kernel32 = FakeKernel32(assignment_succeeds=False)
    monkeypatch.setattr(process_job_module, "_kernel32", lambda: kernel32)

    # When the process is attached to a new Job Object.
    process_job = process_job_module.attach_process_job(1234)

    # Then it falls back without leaking either native handle.
    assert process_job is None
    assert kernel32.closed_handles == [41, 42]


def test_process_job_close_is_idempotent_and_blocks_late_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given a live native Job Object handle.
    kernel32 = FakeKernel32()
    monkeypatch.setattr(process_job_module, "_kernel32", lambda: kernel32)
    process_job = WindowsProcessJob(41)

    # When it is terminated, closed twice, and terminated again.
    assert process_job.terminate() is True
    process_job.close()
    process_job.close()

    # Then the handle is closed once and never reused after close.
    assert process_job.terminate() is False
    assert kernel32.terminated_handles == [41]
    assert kernel32.closed_handles == [41]


@pytest.mark.parametrize(
    ("payload", "expected_status"),
    [
        ('{"status":"success","csv_path":"backtest/csv/result.csv"}', "success"),
        ("not-json", "error"),
    ],
)
def test_manager_closes_process_job_on_normal_and_error_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: str,
    expected_status: str,
) -> None:
    # Given a manager with an observable assigned process resource.
    process_job = RecordingProcessJob()
    monkeypatch.setattr(
        backtest_jobs_module,
        "attach_process_job",
        lambda _pid: process_job,
    )
    command = [sys.executable, "-u", "-c", f"print({payload!r}, flush=True)"]
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=lambda _spec: command,
    )

    # When the worker reaches either terminal result.
    submitted = manager.submit(
        BacktestJobSpec(
            buy="resource-close",
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
    worker.join(timeout=5.0)

    # Then the Job Object is terminated and closed exactly once.
    assert not worker.is_alive()
    assert manager.get(job_id)["status"] == expected_status
    assert process_job.terminate_calls == 1
    assert process_job.close_calls == 1
    assert manager._process_job is None


@pytest.mark.skipif(sys.platform != "win32", reason="Windows Job Object contract")
def test_cancel_reaps_grandchild_after_parent_and_intermediate_exit(
    tmp_path: Path,
) -> None:
    # Given a registered parent that starts only after the manager owns its process tree.
    release_file = tmp_path / "release.txt"
    pid_file = tmp_path / "grandchild-pids.txt"
    middle_code = """
import os
import subprocess
import sys

grandchild = subprocess.Popen(
    [sys.executable, "-u", "-c", "import time; time.sleep(120)"]
)
with open(sys.argv[1], "w", encoding="utf-8") as stream:
    stream.write(f"{os.getpid()},{grandchild.pid}")
"""
    parent_code = """
import json
import pathlib
import subprocess
import sys
import time

release_file = pathlib.Path(sys.argv[1])
while not release_file.is_file():
    time.sleep(0.01)
middle = subprocess.Popen([sys.executable, "-u", "-c", sys.argv[3], sys.argv[2]])
middle.wait()
print(json.dumps({"status": "success", "csv_path": "backtest/csv/misleading.csv"}), flush=True)
"""
    command = [
        sys.executable,
        "-u",
        "-c",
        parent_code,
        str(release_file),
        str(pid_file),
        middle_code,
    ]
    manager = BacktestJobManager(
        jobs_dir=tmp_path / "jobs",
        command_builder=lambda _spec: command,
    )
    submitted = manager.submit(
        BacktestJobSpec(
            buy="orphan-grandchild",
            sell="sell",
            buy_code="매수 = True",
            sell_code="매도 = False",
            start=20250407,
            end=20250409,
        )
    )
    job_id = str(submitted["job_id"])
    worker = manager._worker
    grandchild: psutil.Process | None = None
    grandchild_create_time: float | None = None
    try:
        assert worker is not None
        register_deadline = time.monotonic() + 5.0
        while manager._proc is None and time.monotonic() < register_deadline:
            time.sleep(0.01)
        assert manager._proc is not None
        release_file.touch()
        pid_deadline = time.monotonic() + 5.0
        while not pid_file.is_file() and time.monotonic() < pid_deadline:
            time.sleep(0.01)
        assert pid_file.is_file()
        _middle_text, grandchild_text = pid_file.read_text(encoding="utf-8").split(",")
        grandchild = psutil.Process(int(grandchild_text))
        grandchild_create_time = grandchild.create_time()
        exit_deadline = time.monotonic() + 5.0
        while manager._proc.poll() is None and time.monotonic() < exit_deadline:
            time.sleep(0.01)
        assert manager._proc.poll() == 0
        assert manager.get(job_id)["status"] == "running"

        # When cancellation is accepted after both ancestor processes exited.
        cancel = manager.cancel(job_id)
        worker.join(timeout=5.0)

        # Then kernel-owned membership reaps the otherwise untraceable grandchild.
        assert cancel["cancelled"] == "running"
        assert not worker.is_alive()
        with pytest.raises((psutil.NoSuchProcess, psutil.ZombieProcess)):
            psutil.Process(grandchild.pid).status()
        assert manager.get(job_id)["status"] == "cancelled"
        assert manager._current_job is None
        assert manager._proc is None
        assert manager._process_job is None
    finally:
        if grandchild is not None and grandchild_create_time is not None:
            try:
                current = psutil.Process(grandchild.pid)
                if abs(current.create_time() - grandchild_create_time) < 0.001:
                    current.kill()
                    current.wait(timeout=5.0)
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                pass
        if worker is not None:
            worker.join(timeout=5.0)
