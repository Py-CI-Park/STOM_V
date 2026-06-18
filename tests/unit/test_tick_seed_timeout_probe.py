from __future__ import annotations

import json
from pathlib import Path

import pytest


def _write_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "provider": "gpt_auth",
                "bt_engine_mode": "warm",
                "bt_timeframe": "tick",
                "bt_full_start": 20250102,
                "bt_full_end": 20250102,
                "bt_universe_start_time": 90000,
                "bt_universe_end_time": 90100,
                "bt_avg_time": 30,
                "bt_betting": "5",
                "bt_warm_engine_count": 1,
                "bt_warm_run_timeout": 60,
                "bt_timeout": 600,
                "max_generations": 1,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_inspect_writes_seed_and_warm_config_without_process(tmp_path, monkeypatch):
    # Given: a tiny warm config and monkeypatched seed text.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    config_path = tmp_path / "config.json"
    out_path = tmp_path / "inspect.json"
    _write_config(config_path)

    def fake_read_strategy_code(name: str, kind: str) -> str:
        if kind == "buy":
            return f"# {name}\nself.Buy('A000001')\n"
        return f"# {name}\nself.Sell('A000001')\n"

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("inspect must not start a process")

    monkeypatch.setattr(probe, "_read_strategy_code", fake_read_strategy_code)
    monkeypatch.setattr(probe.subprocess, "Popen", fail_popen)

    # When: the inspect probe runs.
    payload = probe.inspect_probe(
        config_json=config_path,
        buy_name="C_T_900_920_U2_B",
        sell_name="C_T_900_920_U2_S",
        out_path=out_path,
    )

    # Then: it writes deterministic seed/config facts and no runtime process.
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload == written
    assert written["status"] == "ok"
    assert written["seed_buy"]["contains_self_buy"] is True
    assert written["seed_sell"]["contains_self_sell"] is True
    assert written["effective_warm_backtest_config"]["start_date"] == 20250102
    assert written["effective_warm_backtest_config"]["engine_count"] == 1


def test_run_loop_uses_safe_env_and_owned_process(tmp_path, monkeypatch):
    # Given: a loop command and a fake owned subprocess.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    config_path = tmp_path / "config.json"
    out_path = tmp_path / "run.json"
    _write_config(config_path)
    captured: dict[str, str | list[str]] = {}

    class FakeProcess:
        pid = 12345
        returncode = 0

        def wait(self, timeout: int) -> int:
            captured["timeout"] = str(timeout)
            return self.returncode

    def fake_popen(command, **kwargs):
        captured["command"] = list(command)
        captured["env_pythonutf8"] = kwargs["env"]["PYTHONUTF8"]
        captured["env_unbuffered"] = kwargs["env"]["PYTHONUNBUFFERED"]
        return FakeProcess()

    monkeypatch.setattr(probe.subprocess, "Popen", fake_popen)

    # When: the helper executes the bounded loop wrapper.
    result = probe.run_loop_probe(
        config_json=config_path,
        run_id="tick_seed_timeout_warm_1d_1m_e1_20260605",
        wall_cap=7,
        out_path=out_path,
    )

    # Then: the command is an owned Python child with UTF-8/unbuffered env.
    command = captured["command"]
    assert isinstance(command, list)
    joined = " ".join(command)
    assert result["status"] == "ok"
    assert result["pid"] == 12345
    assert captured["timeout"] == "7"
    assert captured["env_pythonutf8"] == "1"
    assert captured["env_unbuffered"] == "1"
    assert "-m ai_strategy_loop.controller.loop" in joined
    assert "final_approval" not in joined
    assert "export_winner" not in joined
    assert "taskkill" not in joined.lower()


def test_run_cold_command_uses_warm_window_and_forbidden_tokens_are_absent(tmp_path):
    # Given: a warm-loop config for direct same-window cold comparison.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    config_path = tmp_path / "config.json"
    _write_config(config_path)

    # When: the cold command is built.
    spec = probe.build_cold_command(
        config_json=config_path,
        buy_name="C_T_900_920_U2_B",
        sell_name="C_T_900_920_U2_S",
    )

    # Then: it carries the exact warm window into stom_backtest.py safely.
    joined = " ".join(spec.command)
    assert "stom_backtest.py" in joined
    assert "--start 20250102" in joined
    assert "--end 20250102" in joined
    assert "--start-time 90000" in joined
    assert "--end-time 90100" in joined
    assert "--avg-time 30" in joined
    assert "--engines 1" in joined
    assert "--timeout 60" in joined
    assert spec.env["PYTHONUTF8"] == "1"
    assert spec.env["PYTHONUNBUFFERED"] == "1"
    assert "final_approval" not in joined
    assert "export_winner" not in joined
    assert "taskkill" not in joined.lower()


def test_timeout_is_reported_and_owned_tree_cleanup_runs(tmp_path, monkeypatch):
    # Given: a fake child that times out, then exits after owned tree cleanup.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    out_path = tmp_path / "timeout.json"
    spec = probe.CommandSpec(
        command=["python", "-m", "ai_strategy_loop.controller.loop"],
        env={"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
    )
    calls: list[str] = []

    class FakeProcess:
        pid = 67890
        returncode = 1

        def wait(self, timeout: int) -> int:
            calls.append(f"wait:{timeout}")
            if len(calls) == 1:
                raise probe.subprocess.TimeoutExpired("python", timeout)
            return self.returncode

    def fake_cleanup(pid: int, *, grace_seconds: int):
        calls.append(f"tree:{pid}:{grace_seconds}")
        return {
            "parent_pid": pid,
            "descendant_pids": [24680],
            "terminated_pids": [24680, pid],
            "killed_pids": [],
            "errors": [],
        }

    monkeypatch.setattr(probe.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    monkeypatch.setattr(probe, "terminate_process_tree", fake_cleanup)

    # When: the command exceeds its outer wall cap.
    result = probe.run_owned_command(spec=spec, wall_cap=3, out_path=out_path)

    # Then: status is explicit timeout and cleanup targets only the owned tree.
    written = json.loads(out_path.read_text(encoding="utf-8"))
    assert result == written
    assert result["status"] == "timeout"
    assert result["pid"] == 67890
    assert result["cleanup"]["descendant_pids"] == [24680]
    assert calls == ["wait:3", "tree:67890:10", "wait:1"]
    assert "taskkill" not in " ".join(result["command"]).lower()


def test_executor_rejects_forbidden_command_before_process_start(tmp_path, monkeypatch):
    # Given: a direct CommandSpec that bypasses builders.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    def fail_popen(*_args, **_kwargs):
        raise AssertionError("forbidden command must not start")

    monkeypatch.setattr(probe.subprocess, "Popen", fail_popen)
    spec = probe.CommandSpec(
        command=["python", "-m", "ai_strategy_loop.dashboard.app", "final_approval"],
        env={"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
    )

    # When / Then: executor boundary rejects the command.
    with pytest.raises(RuntimeError, match="forbidden token"):
        probe.run_owned_command(spec=spec, wall_cap=1, out_path=tmp_path / "blocked.json")


def test_output_paths_under_protected_runtime_dirs_are_rejected(tmp_path):
    # Given: an output path under a protected runtime directory.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    spec = probe.CommandSpec(
        command=["python", "-m", "ai_strategy_loop.controller.loop"],
        env={"PYTHONUTF8": "1", "PYTHONUNBUFFERED": "1"},
    )

    # When / Then: no JSON/stdout/stderr files may be written there.
    with pytest.raises(RuntimeError, match="protected runtime"):
        probe.run_owned_command(spec=spec, wall_cap=1, out_path=Path("_database") / "probe.json")


def test_db_suffix_output_path_is_rejected():
    # Given / When / Then: DB-looking output files are never diagnostic destinations.
    from ai_strategy_loop.scripts import tick_seed_timeout_probe as probe

    with pytest.raises(RuntimeError, match="protected runtime"):
        probe._write_json(probe.REPO_ROOT_PATH / ".omo" / "evidence" / "probe.db", {"status": "blocked"})


def test_process_tree_cleanup_terminates_descendants(monkeypatch):
    # Given: a fake process tree where one descendant survives terminate.
    from ai_strategy_loop.scripts import _tick_seed_probe_safety as safety

    class FakeProcess:
        def __init__(self, pid: int, children: list["FakeProcess"] | None = None) -> None:
            self.pid = pid
            self._children = children or []
            self.terminated = False
            self.killed = False

        def children(self, *, recursive: bool) -> list["FakeProcess"]:
            assert recursive is True
            return self._children

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

    child = FakeProcess(222)
    parent = FakeProcess(111, [child])
    wait_calls: list[list[int]] = []

    def fake_process(pid: int) -> FakeProcess:
        assert pid == 111
        return parent

    def fake_wait_procs(processes, *, timeout: int):
        wait_calls.append([int(proc.pid) for proc in processes])
        if len(wait_calls) == 1:
            return [parent], [child]
        return list(processes), []

    monkeypatch.setattr(safety.psutil, "Process", fake_process)
    monkeypatch.setattr(safety.psutil, "wait_procs", fake_wait_procs)

    # When: cleanup runs against the owned parent PID.
    result = safety.terminate_process_tree(111, grace_seconds=2)

    # Then: parent and descendants are targeted, with surviving descendants killed.
    assert result["descendant_pids"] == [222]
    assert result["terminated_pids"] == [222, 111]
    assert result["killed_pids"] == [222]
    assert child.terminated is True
    assert child.killed is True
    assert parent.terminated is True
    assert wait_calls == [[222, 111], [222]]
