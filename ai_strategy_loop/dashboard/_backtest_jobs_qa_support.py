from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import psutil

from ai_strategy_loop.dashboard.backtest_jobs import BacktestJobSpec


WAIT_TREE_CODE = """
import json
import os
import subprocess
import sys

child = subprocess.Popen([sys.executable, "-u", "-c", "import time; time.sleep(120)"])
with open(sys.argv[1], "w", encoding="utf-8") as stream:
    stream.write(f"{os.getpid()},{child.pid}")
print(json.dumps({"status": "success", "csv_path": "backtest/csv/misleading-wait.csv"}), flush=True)
child.wait()
"""

ORPHAN_TREE_CODE = """
import json
import os
import subprocess
import sys

child = subprocess.Popen([sys.executable, "-u", "-c", "import time; time.sleep(120)"])
with open(sys.argv[1], "w", encoding="utf-8") as stream:
    stream.write(f"{os.getpid()},{child.pid}")
print(json.dumps({"status": "success", "csv_path": "backtest/csv/misleading-orphan.csv"}), flush=True)
"""

FOLLOW_CODE = """
import json
import sys

with open(sys.argv[1], "a", encoding="utf-8") as stream:
    stream.write(sys.argv[2] + "\\n")
print(json.dumps({"status": "success", "csv_path": "backtest/csv/follow.csv"}), flush=True)
"""


class QaFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ProcessIdentity:
    pid: int
    create_time: float


@dataclass(frozen=True, slots=True)
class JobScenarioReport:
    strategy: str
    job_id: str
    parent_pid: int
    child_pid: int
    parent_exited_before_cancel: bool
    cancel_kind: str
    terminal_status: str
    misleading_success_logged: bool
    parent_absent: bool
    child_absent: bool
    successor_id: str
    successor_initial_status: str
    successor_terminal_status: str
    successor_builder_calls: int
    successor_marker_lines: int


@dataclass(frozen=True, slots=True)
class ManagerReport:
    public_singleton_used: bool
    current_job_clear: bool
    process_slot_clear: bool
    queue_empty: bool
    worker_stopped: bool
    restored_statuses: tuple[str, ...]
    stale_status: str
    stale_phase: str
    repeated_terminal_cancel_status: str


@dataclass(frozen=True, slots=True)
class CleanupReceipt:
    qa_root: str
    qa_root_absent: bool
    residual_processes: int


@dataclass(frozen=True, slots=True)
class FinalReport:
    scenarios: tuple[JobScenarioReport, ...]
    manager: ManagerReport
    cleanup: CleanupReceipt


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise QaFailure(detail)


def wait_for(predicate: Callable[[], bool], *, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def process_identity(pid: int) -> ProcessIdentity | None:
    try:
        process = psutil.Process(pid)
        return ProcessIdentity(pid=pid, create_time=process.create_time())
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return None


def same_process_alive(identity: ProcessIdentity | None) -> bool:
    if identity is None:
        return False
    try:
        process = psutil.Process(identity.pid)
        return (
            abs(process.create_time() - identity.create_time) < 0.001
            and process.is_running()
        )
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return False


def cleanup_process(identity: ProcessIdentity) -> None:
    if not same_process_alive(identity):
        return
    try:
        process = psutil.Process(identity.pid)
        for child in process.children(recursive=True):
            child.kill()
        process.kill()
        process.wait(timeout=5.0)
    except (psutil.NoSuchProcess, psutil.ZombieProcess):
        return


def spec(strategy: str) -> BacktestJobSpec:
    return BacktestJobSpec(
        buy=strategy,
        sell="sell",
        start=20250407,
        end=20250409,
        timeout=300,
    )
