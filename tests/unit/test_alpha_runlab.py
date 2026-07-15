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
import sysconfig
import pytest
import hashlib
import stat
from contextlib import nullcontext

from alpha_lab.discipline import measure_gate, prereg
from alpha_lab.runlab.sealed_execution import (
    load_execution_evidence,
    stage_execution,
    validate_staged_execution,
)

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
    """격리 bootstrap 검증용 환경 — caller PYTHONPATH를 전달하지 않는다."""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _bootstrap_cmd(mode: str, *args: str) -> list[str]:
    bootstrap = _ROOT / "alpha_lab" / "runlab" / "bootstrap.py"
    return [sys.executable, "-I", "-S", str(bootstrap), mode, *args]


def _isolated_startup_paths() -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-I", "-S", "-c", "import json, sys; print(json.dumps(sys.path))"],
        capture_output=True, check=True, text=True, timeout=30)
    return [str(Path(path).resolve()) for path in json.loads(proc.stdout) if path]


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
def test_detached_launch_requires_receipt_and_claim(tmp_path):
    child = _write_child(tmp_path, "late.py", "raise AssertionError('must not run')\n")
    with pytest.raises(TypeError):
        launch_detached(tmp_path / "run", child, heartbeat_interval=0.1)


# ── child_wrap: 무수정 래핑 — 인자 전달 + 실패 exit_code 보존 ───────────────
def test_child_wrap_requires_receipt_and_claim(tmp_path):
    child = _write_child(tmp_path, "late.py", "raise AssertionError('must not run')\n")
    run_dir = tmp_path / "run_fail"
    proc = subprocess.run(
        _bootstrap_cmd("child-wrap", "--interval", "0.1", str(run_dir), str(child)),
        cwd=str(tmp_path), env=_child_env(), capture_output=True, timeout=60)
    assert proc.returncode != 0
    assert b"--repo-root" in proc.stderr
# ── bootstrap: caller path/site hook 차단 + 신뢰 루트 우선순위 ───────────────


def test_bootstrap_target_requires_sealed_evidence(tmp_path):
    target = _write_child(tmp_path, "late.py", "raise AssertionError('must not run')\n")
    proc = subprocess.run(
        _bootstrap_cmd("target", str(target)), cwd=str(tmp_path),
        env=_child_env(), capture_output=True, timeout=60)
    assert proc.returncode != 0
    assert b"--repo-root" in proc.stderr


def test_wrapper_command_uses_isolated_bootstrap_and_removes_pythonpath(monkeypatch,
                                                                         tmp_path):
    from alpha_lab.runlab import detached_runner

    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "shadow"))
    event = type("Event", (), {"handle": 1})()
    cmd = detached_runner._wrapper_cmd(
        tmp_path / "run", tmp_path / "target.py", (), 5.0,
        repo_root=_ROOT, receipt=_ROOT / "receipts" / "r.json",
        claim=_ROOT / "claims" / "r.json", stage_root=tmp_path / "stage",
        wrapper_ready=event, parent_release=event)
    assert cmd[1:5] == ("-I", "-S",
                        str(_ROOT / "alpha_lab" / "runlab" / "bootstrap.py"),
                        "child-wrap")
    assert "PYTHONPATH" not in detached_runner._prepare_env(None)
    assert cmd[0] == sys.executable
    assert "python_exe" not in detached_runner.launch_detached.__annotations__


def test_child_target_command_uses_isolated_bootstrap(monkeypatch, tmp_path):
    from alpha_lab.runlab import child_wrap

    seen = {}

    class DummyProcess:
        pid = 1

        def poll(self):
            return 0

        def terminate(self):
            pass

    class FakeEvent:
        handle = 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def wait(self, timeout):
            return True

    def fake_popen(cmd, **kwargs):
        seen["cmd"] = cmd
        seen["kwargs"] = kwargs
        return DummyProcess()

    monkeypatch.setattr(child_wrap.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        child_wrap, "WindowsEvent",
        type("Events", (), {"inherited": staticmethod(lambda _: None),
                            "create": staticmethod(lambda: FakeEvent())}))
    monkeypatch.setattr(child_wrap, "inherited_handle_startupinfo",
                        lambda handles: {"handles": handles})
    evidence = type("Evidence", (), {
        "repo_root": _ROOT, "receipt_path": _ROOT / "receipts" / "r.json",
        "claim_path": _ROOT / "claims" / "r.json",
        "receipt": {"code_manifest": [{"path": "target.py"}]}})()
    monkeypatch.setattr(child_wrap, "locked_execution",
                        lambda *args: nullcontext(evidence))
    stage = tmp_path / "stage"
    stage.mkdir()
    target = stage / "target.py"
    target.write_text("", encoding="utf-8")
    assert child_wrap._run(
        tmp_path, str(target), [], 0.1, repo_root=_ROOT,
        receipt=_ROOT / "receipts" / "r.json", claim=_ROOT / "claims" / "r.json",
        stage_root=stage) == 0
    assert seen["cmd"][1:5] == ["-I", "-S",
                                 str(_ROOT / "alpha_lab" / "runlab" / "bootstrap.py"),
                                 "target"]



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
    evidence = type("Evidence", (), {
        "repo_root": _ROOT, "receipt_path": _ROOT / "receipts" / "r.json",
        "claim_path": _ROOT / "claims" / "r.json",
        "receipt": {"code_manifest": [{"path": "slow_child.py"}]}})()
    monkeypatch.setattr(child_wrap, "locked_execution",
                        lambda *args: nullcontext(evidence))
    class FakeEvent:
        handle = 1

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def wait(self, timeout):
            return True

    monkeypatch.setattr(
        child_wrap, "WindowsEvent",
        type("Events", (), {"inherited": staticmethod(lambda _: None),
                            "create": staticmethod(lambda: FakeEvent())}))
    monkeypatch.setattr(child_wrap, "inherited_handle_startupinfo",
                        lambda handles: {"handles": handles})
    real_child = subprocess.Popen([sys.executable, str(child)])

    class LiveProcess:
        pid = real_child.pid

        def poll(self):
            return real_child.poll()

        def terminate(self):
            real_child.terminate()

    monkeypatch.setattr(child_wrap.subprocess, "Popen",
                        lambda *args, **kwargs: LiveProcess())
    stage = tmp_path / "stage"
    stage.mkdir()
    staged_child = stage / "slow_child.py"
    staged_child.write_text(child.read_text(encoding="utf-8"), encoding="utf-8")
    child_pid = None
    try:
        rc = child_wrap._run(
            run_dir, str(staged_child), [], interval=0.1, repo_root=_ROOT,
            receipt=_ROOT / "receipts" / "r.json", claim=_ROOT / "claims" / "r.json",
            stage_root=stage)
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
def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ("git", "-C", str(repo), *args), capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def _sealed_runlab_repo(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    repo = tmp_path / "sealed-repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "code").mkdir()
    (repo / "package").mkdir()
    (repo / "package" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "package" / "helper.py").write_text("VALUE = 'sealed-run'\n", encoding="utf-8")
    sealed = repo / "docs" / "prereg.md"
    sealed.write_text(
        """# sealed

> 지위: **SEALED**

```json prereg-contract-v2
{"authority_paths":{"backup_dir":"backups","catalog_dir":"catalog","journal_dir":"journal","promotions_dir":"promotions","seal_dir":"seals","target_db":"code/entry.py"},"dependency_roots":["code/entry.py"],"discovery_window":{"end":"2023-12-31","start":"2022-03-23"},"dynamic_python_dependencies":[],"hypothesis_id":"H-runlab","kill_rule":"none","ledger_path":"ledger.jsonl","multiplicity_family":"runlab","non_python_dependencies":[],"primary_estimand":"run","sample_floors":{"qualified":1},"schema_version":2}
```
""", encoding="utf-8")
    target = repo / "code" / "entry.py"
    target.write_text(
        "from package import helper\nRESULT = helper.VALUE\n",
        encoding="utf-8")
    _git(repo.parent, "init", "-q", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=test", "-c", "user.email=test@example.com",
         "commit", "-qm", "initial")
    seal = repo / "seals" / f"{hashlib.sha256(sealed.read_bytes()).hexdigest()}.seal.json"
    prereg.finalize_prereg(
        sealed, repo_root=repo,
        code_files=(target, repo / "package" / "__init__.py", repo / "package" / "helper.py"),
        manifest_path=seal, sealed_at="2026-07-14T00:00:00+00:00")
    _git(repo, "add", "seals")
    _git(repo, "-c", "user.name=test", "-c", "user.email=test@example.com",
         "commit", "-qm", "seal")
    receipt = measure_gate.issue_gate_receipt_v2(
        repo, seal, issued_at="2026-07-14T00:01:00+00:00", nonce="runlab")
    receipt_path = repo / "receipts" / f"{receipt['receipt_id']}.json"
    measure_gate.claim_gate_receipt_v2(
        receipt_path, repo_root=repo, consumer="runlab-test",
        consumed_at="2026-07-14T00:02:00+00:00")
    return repo, target, receipt_path, repo / "claims" / f"{receipt['receipt_id']}.json"


def test_sealed_execution_stages_and_runs_dependency_root(tmp_path):
    repo, target, receipt, claim = _sealed_runlab_repo(tmp_path)
    evidence = load_execution_evidence(repo, receipt, claim)
    stage, staged_target = stage_execution(tmp_path / "run", evidence, target)
    proc = subprocess.run(
        _bootstrap_cmd("target", "--repo-root", str(repo), "--receipt", str(receipt),
                       "--claim", str(claim), "--stage-root", str(stage),
                       str(staged_target)),
        env=_child_env(), capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")


def test_sealed_execution_rejects_late_target_claim_tamper_and_stage_extra(tmp_path):
    repo, target, receipt, claim = _sealed_runlab_repo(tmp_path)
    evidence = load_execution_evidence(repo, receipt, claim)
    late = repo / "code" / "late.py"
    late.write_text("raise AssertionError('late')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="dependency_roots"):
        stage_execution(tmp_path / "run-late", evidence, late)
    with pytest.raises(RuntimeError, match="dependency_roots"):
        stage_execution(tmp_path / "run-member", evidence, repo / "package" / "helper.py")
    stage, staged_target = stage_execution(tmp_path / "run", evidence, target)
    stage.chmod(stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    extra = stage / "late.py"
    extra.write_text("raise AssertionError('extra')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="exactly the manifest"):
        validate_staged_execution(repo, receipt, claim, stage, staged_target)
    claim.write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="invalid gate claim"):
        load_execution_evidence(repo, receipt, claim)
