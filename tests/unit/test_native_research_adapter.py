from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import sys

import pytest

from ai_strategy_loop.native_research.adapter import NativeResearchAdapter
from ai_strategy_loop.native_research.contracts import NativeRunSpec, NativeTool
from ai_strategy_loop.native_research.sidecar import NativeSidecar


def _db(path: Path, table: str = "sample") -> None:
    connection = sqlite3.connect(path)
    connection.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute(f"INSERT INTO {table}(value) VALUES ('ok')")
    connection.commit()
    connection.close()


def _spec(tmp_path: Path) -> NativeRunSpec:
    for name in ("strategy", "backtest", "setting", "optuna", "market"):
        _db(tmp_path / f"{name}.db")
    return NativeRunSpec(
        run_id="run-001",
        tool=NativeTool.BACKFINDER,
        strategy_db=str(tmp_path / "strategy.db"),
        backtest_db=str(tmp_path / "backtest.db"),
        setting_db=str(tmp_path / "setting.db"),
        optuna_db=str(tmp_path / "optuna.db"),
        market_db_paths=(str(tmp_path / "market.db"),),
        output_root=str(tmp_path / "native_runs"),
    )


def test_adapter_prepares_only_run_local_writable_databases(tmp_path):
    spec = _spec(tmp_path)
    adapter = NativeResearchAdapter(spec)
    receipt = adapter.prepare_run()
    assert receipt["status"] == "prepared"
    assert receipt["authority"] == "existing_db_development_no_oos_no_adoption"
    for name in ("strategy.db", "backtest.db", "setting.db", "optuna.db", "native_ledger.db", "receipt.json"):
        assert (adapter.run_dir / name).is_file()
    assert (adapter.run_dir / "csv").is_dir()
    environment = adapter.environment()
    assert environment["STOM_CLI_DB_STRATEGY"] == str(adapter.run_dir / "strategy.db")
    assert environment["STOM_CLI_DB_BACKTEST"] == str(adapter.run_dir / "backtest.db")
    assert environment["STOM_CLI_DB_OPTUNA"] == str(adapter.run_dir / "optuna.db")
    verified = adapter.verify_operational_unchanged()
    assert verified["operational_fingerprints_after"] == verified["operational_fingerprints_before"]


def test_adapter_fails_closed_on_bad_identity_or_reuse(tmp_path):
    spec = _spec(tmp_path)
    with pytest.raises(ValueError):
        NativeResearchAdapter(replace(spec, run_id="../escape"))
    adapter = NativeResearchAdapter(spec)
    adapter.prepare_run()
    with pytest.raises(FileExistsError):
        NativeResearchAdapter(spec).prepare_run()


def test_adapter_detects_operational_source_change(tmp_path):
    spec = _spec(tmp_path)
    adapter = NativeResearchAdapter(spec)
    adapter.prepare_run()
    connection = sqlite3.connect(spec.market_db_paths[0])
    connection.execute("INSERT INTO sample(value) VALUES ('changed')")
    connection.commit()
    connection.close()
    with pytest.raises(RuntimeError, match="operational source changed"):
        adapter.verify_operational_unchanged()


def test_adapter_launches_fresh_process_with_sidecar_environment(tmp_path):
    spec = _spec(tmp_path)
    adapter = NativeResearchAdapter(spec)
    adapter.prepare_run()
    completed = adapter.run_subprocess(
        [sys.executable, "-c", "import os; print(os.environ['STOM_CLI_DB_STRATEGY'])"],
        timeout_seconds=30,
    )
    assert completed.returncode == 0
    assert str(adapter.run_dir / "strategy.db") in completed.stdout
    receipt = json.loads(adapter.receipt_path.read_text(encoding="utf-8"))
    assert receipt["status"] == "engine_success"


def test_sidecar_resume_skips_only_successful_terminal_trials(tmp_path):
    ledger = NativeSidecar(tmp_path / "ledger.db")
    ledger.init_schema()
    successful = ledger.record_trial(
        run_id="run", phase="entry", family_id="F", band_id="B", candidate_id="C1",
        source_sha256="a" * 64, parameters={"x": 1}, resume_key="entry:B:F:C1:1",
        status="engine_success",
    )
    failed = ledger.record_trial(
        run_id="run", phase="entry", family_id="F", band_id="B", candidate_id="C2",
        source_sha256="b" * 64, parameters={"x": 2}, resume_key="entry:B:F:C2:2",
        status="execution_failure",
    )
    assert ledger.completed_trial_hashes() == {successful}
    assert failed not in ledger.completed_trial_hashes()
    assert ledger.is_resume_complete("entry:B:F:C1:1") is True
    assert ledger.is_resume_complete("entry:B:F:C2:2") is False
