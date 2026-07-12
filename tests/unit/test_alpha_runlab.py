"""alpha_lab.runlab 단위 테스트 — 분리 기동→심박→종료 계약 + 워치독 판정.

검증 대상(WBS v3 P1-4, 백로그 A18·A19):
- detached_runner: 세션 독립 기동 후 run_dir 계약 파일 4종
  (pid/heartbeat/status/log)이 채워지고 정상 종료가 exited(0)으로 기록되는가.
- child_wrap: 대상 스크립트 무수정 래핑 — 인자 전달·실패 exit_code 보존.
- watchdog: RUNNING/STALLED/DEAD/EXITED/MISSING 판정 + ctypes pid 생존 확인.
- scripts/batch_watch.py: 보고 전용 CLI 출력·종료코드.

실프로세스는 수백 ms짜리 초소형 자식 스크립트만 사용하고, 테스트 종료 시
잔존 프로세스를 정리한다(taskkill 트리 강제 종료 — 잔존 금지 규율).
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from alpha_lab.runlab import contract, watchdog
from alpha_lab.runlab.detached_runner import launch_detached

_ROOT = Path(__file__).resolve().parents[2]
_WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt",
                                   reason="분리 기동 계약은 Windows 전용")

# 초소형 자식 스크립트 — 마커 출력 후 잠깐 대기, 정상 종료.
_OK_CHILD = (
    "import time\n"
    "print('CHILD_START', flush=True)\n"
    "time.sleep(0.7)\n"
    "print('CHILD_DONE', flush=True)\n"
)
# 인자를 파일로 남기고 exit 3 — 인자 전달과 실패 코드 보존을 함께 검증.
_FAIL_CHILD = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "Path(sys.argv[1]).write_text('|'.join(sys.argv[2:]), encoding='utf-8')\n"
    "time.sleep(0.2)\n"
    "sys.exit(3)\n"
)


def _write_child(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _child_env() -> dict:
    """자식 파이썬이 ROOT의 alpha_lab을 임포트할 수 있게 PYTHONPATH 주입."""
    env = dict(os.environ)
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(_ROOT) + (os.pathsep + prev if prev else "")
    return env


def _force_kill_tree(pid) -> None:
    """잔존 프로세스 정리 — 테스트 실패 시에도 자식을 남기지 않는다."""
    if pid and watchdog.check_pid_alive(pid):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                       capture_output=True, timeout=15)


def _wait_until(cond, timeout_sec: float, poll_sec: float = 0.05) -> bool:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        if cond():
            return True
        time.sleep(poll_sec)
    return cond()


# ── detached_runner: 기동→심박→정상 종료 계약 ──────────────────────────────
@_WINDOWS_ONLY
def test_detached_launch_full_contract(tmp_path):
    child = _write_child(tmp_path, "ok_child.py", _OK_CHILD)
    run_dir = tmp_path / "run_ok"
    res = launch_detached(run_dir, child, heartbeat_interval=0.1)
    try:
        hb = run_dir / contract.HEARTBEAT_FILE
        assert _wait_until(hb.exists, timeout_sec=20.0), "심박 미생성"
        first_mtime = hb.stat().st_mtime
        status = watchdog.wait_for_exited(run_dir, timeout_sec=25.0)
        assert status is not None and status["state"] == "exited"
        assert status["exit_code"] == 0
        assert status["child_pid"] > 0 and status["started_utc"]
        # pid.txt는 래퍼 PID와 일치, 심박은 구동 중 주기 갱신됐어야 한다.
        assert contract.read_pid(run_dir) == res.pid
        assert hb.stat().st_mtime > first_mtime, "심박이 주기 갱신되지 않음"
        log_text = res.log_path.read_text(encoding="utf-8", errors="replace")
        assert "CHILD_START" in log_text and "CHILD_DONE" in log_text
        # 종료 후 래퍼 프로세스는 곧 사라져야 한다(잔존 금지).
        assert _wait_until(lambda: not watchdog.check_pid_alive(res.pid),
                           timeout_sec=10.0), "래퍼 프로세스 잔존"
        report = watchdog.inspect_run(run_dir)
        assert report.verdict == watchdog.VERDICT_EXITED
        assert report.exit_code == 0
    finally:
        _force_kill_tree(res.pid)


# ── child_wrap: 무수정 래핑 — 인자 전달 + 실패 exit_code 보존 ───────────────
def test_child_wrap_preserves_args_and_exit_code(tmp_path):
    child = _write_child(tmp_path, "fail_child.py", _FAIL_CHILD)
    argv_dump = tmp_path / "argv.txt"
    run_dir = tmp_path / "run_fail"
    cmd = [sys.executable, "-m", "alpha_lab.runlab.child_wrap",
           "--interval", "0.1", str(run_dir), str(child),
           str(argv_dump), "alpha", "--beta=1"]
    proc = subprocess.run(cmd, cwd=str(tmp_path), env=_child_env(),
                          capture_output=True, timeout=60)
    assert proc.returncode == 3, proc.stderr.decode(errors="replace")
    status = contract.read_status(run_dir)
    assert status["state"] == "exited" and status["exit_code"] == 3
    assert argv_dump.read_text(encoding="utf-8") == "alpha|--beta=1"
    assert (run_dir / contract.HEARTBEAT_FILE).exists()
    assert contract.read_pid(run_dir) > 0


# ── watchdog: pid 생존 확인(ctypes) ─────────────────────────────────────────
def test_check_pid_alive_true_and_false():
    assert watchdog.check_pid_alive(os.getpid()) is True
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait(timeout=30)
    assert _wait_until(lambda: not watchdog.check_pid_alive(dead.pid),
                       timeout_sec=5.0)
    assert watchdog.check_pid_alive(None) is False
    assert watchdog.check_pid_alive(0) is False


# ── watchdog: 판정 분기(실프로세스 없이 파일만 조작) ────────────────────────
def test_watchdog_running_then_stalled(tmp_path):
    run_dir = tmp_path / "run_live"
    run_dir.mkdir()
    contract.write_pid(run_dir, os.getpid())  # 살아 있는 pid = 이 테스트 프로세스.
    contract.write_status(run_dir, contract.STATE_RUNNING, pid=os.getpid())
    contract.touch_heartbeat(run_dir)
    assert watchdog.inspect_run(run_dir, stall_sec=60.0).verdict == \
        watchdog.VERDICT_RUNNING
    # 심박 mtime을 과거로 밀면 STALLED — 임계 초과 판정.
    old = time.time() - 1000.0
    os.utime(run_dir / contract.HEARTBEAT_FILE, (old, old))
    report = watchdog.inspect_run(run_dir, stall_sec=60.0)
    assert report.verdict == watchdog.VERDICT_STALLED
    assert report.pid_alive is True
    assert report.heartbeat_age_sec > 60.0


def test_watchdog_dead_missing_exited(tmp_path):
    # DEAD: exited 기록 없이 pid 사망(세션 동반사 서명).
    dead_proc = subprocess.Popen([sys.executable, "-c", "pass"])
    dead_proc.wait(timeout=30)
    run_dead = tmp_path / "run_dead"
    run_dead.mkdir()
    contract.write_pid(run_dead, dead_proc.pid)
    contract.write_status(run_dead, contract.STATE_RUNNING, pid=dead_proc.pid)
    contract.touch_heartbeat(run_dead)
    assert watchdog.inspect_run(run_dead).verdict == watchdog.VERDICT_DEAD
    # MISSING: status.json 없음.
    run_none = tmp_path / "run_none"
    run_none.mkdir()
    assert watchdog.inspect_run(run_none).verdict == watchdog.VERDICT_MISSING
    # EXITED: exit_code 그대로 보고.
    run_done = tmp_path / "run_done"
    run_done.mkdir()
    contract.write_status(run_done, contract.STATE_EXITED, exit_code=0)
    report = watchdog.inspect_run(run_done)
    assert report.verdict == watchdog.VERDICT_EXITED and report.exit_code == 0


# ── scripts/batch_watch.py: 보고 전용 CLI ───────────────────────────────────
def _load_batch_watch():
    spec = importlib.util.spec_from_file_location(
        "batch_watch_under_test", _ROOT / "scripts" / "batch_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_watch_cli_exit_codes_and_output(tmp_path, capsys):
    bw = _load_batch_watch()
    ok_dir = tmp_path / "ok"
    ok_dir.mkdir()
    contract.write_status(ok_dir, contract.STATE_EXITED, exit_code=0)
    stalled_dir = tmp_path / "stalled"
    stalled_dir.mkdir()
    contract.write_pid(stalled_dir, os.getpid())
    contract.write_status(stalled_dir, contract.STATE_RUNNING, pid=os.getpid())
    contract.touch_heartbeat(stalled_dir)
    old = time.time() - 1000.0
    os.utime(stalled_dir / contract.HEARTBEAT_FILE, (old, old))
    # 정상만 → 0.
    assert bw.main([str(ok_dir)]) == 0
    # 정체 포함 → 2, 출력에 STALLED 판정 포함.
    assert bw.main([str(ok_dir), str(stalled_dir), "--stall-sec", "60"]) == 2
    out = capsys.readouterr().out
    assert "STALLED" in out and "EXITED" in out
    # --scan: 부모 폴더에서 두 run_dir 전개, --json 파싱 가능.
    assert bw.main([str(tmp_path), "--scan", "--stall-sec", "60",
                    "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    verdicts = {row["verdict"] for row in payload}
    assert verdicts == {watchdog.VERDICT_EXITED, watchdog.VERDICT_STALLED}


# ── wrapper_error: 거짓 EXITED 방지 경로(검증 지적 반영) ─────────────────────
@_WINDOWS_ONLY
def test_watchdog_wrapper_error_child_alive_and_dead(tmp_path):
    """wrapper_error 상태 판정 — 자식 생존/사망을 구분 보고한다."""
    run_alive = tmp_path / "alive"
    run_alive.mkdir()
    contract.write_status(run_alive, contract.STATE_WRAPPER_ERROR,
                          child_pid=os.getpid(), error="테스트: 심박 IO 장애")
    report = watchdog.inspect_run(run_alive)
    assert report.verdict == watchdog.VERDICT_WRAPPER_ERROR
    assert report.pid_alive is True  # child_pid(현 프로세스) 생존 감지.
    assert "생존" in report.detail

    run_dead = tmp_path / "dead"
    run_dead.mkdir()
    dead_proc = subprocess.Popen([sys.executable, "-c", "pass"])
    dead_proc.wait(timeout=10)
    contract.write_status(run_dead, contract.STATE_WRAPPER_ERROR,
                          child_pid=dead_proc.pid, error="테스트")
    report = watchdog.inspect_run(run_dead)
    assert report.verdict == watchdog.VERDICT_WRAPPER_ERROR
    assert report.pid_alive is False


@_WINDOWS_ONLY
def test_child_wrap_heartbeat_failure_preserves_alive_child(tmp_path,
                                                            monkeypatch):
    """심박 IO 장애 시 자식이 살아 있으면 exited(거짓 종료) 대신
    wrapper_error + child_pid 보존으로 기록된다."""
    from alpha_lab.runlab import child_wrap

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    child = _write_child(tmp_path, "slow_child.py",
                         "import time\ntime.sleep(2.5)\n")

    calls = {"n": 0}
    real_touch = contract.touch_heartbeat

    def flaky_touch(rd):
        calls["n"] += 1
        if calls["n"] >= 3:  # 기동 직후 2회는 정상, 감시 루프에서 장애 발생.
            raise OSError("테스트: 심박 쓰기 장애")
        real_touch(rd)

    monkeypatch.setattr(child_wrap.contract, "touch_heartbeat", flaky_touch)
    child_pid = None
    try:
        rc = child_wrap._run(run_dir, str(child), [], interval=0.1)
        status = contract.read_status(run_dir)
        assert rc == 1
        assert status is not None
        assert status["state"] == contract.STATE_WRAPPER_ERROR
        child_pid = status.get("child_pid")
        assert child_pid  # 보존 확인 — 고아 추적 수단 유지.
        assert watchdog.check_pid_alive(child_pid) is True  # 거짓 종료 아님.
        report = watchdog.inspect_run(run_dir)
        assert report.verdict == watchdog.VERDICT_WRAPPER_ERROR
        # 자식은 스스로 종료한다 — 잔존 금지 규율 확인.
        assert _wait_until(lambda: not watchdog.check_pid_alive(child_pid), 10)
    finally:
        _force_kill_tree(child_pid)
