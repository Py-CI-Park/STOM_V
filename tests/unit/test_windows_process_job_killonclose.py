"""결함 E 회귀 테스트 — kill-on-close 잡: 부모가 죽으면 자식도 죽는다.

2026-07-28 실측: 배치 러너 강제 종료 2회가 warm 엔진 고아 105개(RAM 수십 GB)를 남겨
다음 prepare 가 무한 지연됐다. 수정 = 러너가 자신을 kill-on-close 잡에 부착.
이 테스트는 자식 파이썬(자기부착) → 손자 sleeper 를 띄운 뒤 자식을 강제 종료하고,
손자가 커널에 의해 정리되는지 실측한다(Windows 전용, 타 OS 는 skip).
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

import pytest

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows job object 전용")


def _pid_alive(pid: int) -> bool:
    import psutil  # noqa: PLC0415 - 대시보드 의존성에 이미 포함.

    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).is_running()
    except Exception:  # noqa: BLE001
        return False


def test_kill_on_close_reaps_grandchild(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    pid_file = tmp_path / "grandchild.pid"
    child_code = textwrap.dedent(f"""
        import os, subprocess, sys, time
        sys.path.insert(0, {repo!r})
        from ai_strategy_loop.dashboard._windows_process_job import attach_process_job
        job = attach_process_job(os.getpid(), kill_on_close=True)
        assert job is not None, "job attach failed"
        grand = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        open({str(pid_file)!r}, "w").write(str(grand.pid))
        time.sleep(120)
    """)
    child = subprocess.Popen([sys.executable, "-c", child_code])
    try:
        for _ in range(100):
            if pid_file.exists() and pid_file.read_text().strip():
                break
            time.sleep(0.2)
        assert pid_file.exists(), "자식이 손자를 띄우지 못함"
        grand_pid = int(pid_file.read_text().strip())
        assert _pid_alive(grand_pid), "손자가 살아있어야 사전조건 성립"

        child.kill()          # 부모(자기부착) 강제 종료 — 실측 사고와 동일 경로
        child.wait(timeout=10)

        deadline = time.time() + 10
        while time.time() < deadline and _pid_alive(grand_pid):
            time.sleep(0.3)
        assert not _pid_alive(grand_pid), "kill-on-close 잡이 손자를 정리해야 한다(고아 방지)"
    finally:
        if child.poll() is None:
            child.kill()
        try:
            gp = int(pid_file.read_text().strip()) if pid_file.exists() else None
            if gp and _pid_alive(gp):
                subprocess.run(["taskkill", "/PID", str(gp), "/F"], capture_output=True, check=False)
        except Exception:
            pass


def test_attach_without_flag_still_returns_job():
    # 하위호환: 기존 호출(kill_on_close 미지정)이 그대로 동작해야 한다.
    from ai_strategy_loop.dashboard._windows_process_job import attach_process_job
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        job = attach_process_job(proc.pid)
        assert job is not None
        assert job.terminate() is True
        job.close()
    finally:
        if proc.poll() is None:
            proc.kill()
