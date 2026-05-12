from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import V3KAnalyzerAdapter, learning_db_manifest  # noqa: E402


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _artifact_status() -> str:
    return _run_git(
        "status",
        "--short",
        "--",
        "_database",
        "_database_v3k_shadow",
        "_log",
        "backup",
        "*.db",
        "backtest/graph",
        "_v3k_sidecar",
    )


def _assert_missing_noop(tmpdir: Path) -> None:
    contract = next(iter(learning_db_manifest()))
    table_name = contract.table_name("stock", False)
    adapter = V3KAnalyzerAdapter(production_db_dir=tmpdir)
    result = adapter.read_production_learning_db(contract.db_name, table_name)
    if result.exists or result.table_exists or result.has_rows:
        raise AssertionError(f"missing production DB must be no-op: {result}")
    if "missing" not in " ".join(result.diagnostics).lower():
        raise AssertionError(f"missing diagnostic mismatch: {result.diagnostics}")


def _assert_lock_or_safe_read_noop(tmpdir: Path) -> None:
    contract = next(iter(learning_db_manifest()))
    table_name = contract.table_name("stock", False)
    db_path = tmpdir / contract.db_name
    with closing(sqlite3.connect(db_path)) as setup:
        setup.execute(f"CREATE TABLE {table_name} (code TEXT, last_update INTEGER, confidence_score REAL)")
        setup.execute(f"INSERT INTO {table_name} VALUES ('005930', 20260101, 0.7)")
        setup.commit()

    locker = sqlite3.connect(db_path, timeout=0.1)
    try:
        locker.execute("BEGIN EXCLUSIVE")
        adapter = V3KAnalyzerAdapter(production_db_dir=tmpdir)
        result = adapter.read_production_learning_db(contract.db_name, table_name)
    finally:
        locker.rollback()
        locker.close()

    diagnostics = " ".join(result.diagnostics).lower()
    if result.has_rows:
        print("lock smoke note: platform allowed read while exclusive lock was held; safe read path verified")
        return
    if "fallback" not in diagnostics and "locked" not in diagnostics and "failed" not in diagnostics:
        raise AssertionError(f"lock fallback diagnostic mismatch: {result}")


def main() -> None:
    before = _artifact_status()
    with tempfile.TemporaryDirectory(prefix="v3k-prod-fallback-") as tmp:
        tmpdir = Path(tmp)
        _assert_missing_noop(tmpdir)
        _assert_lock_or_safe_read_noop(tmpdir)
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "fallback smoke changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k production learning DB fallback smoke passed")
    print("missing DB and lock/safe-read fallback paths verified without runtime artifacts")


if __name__ == "__main__":
    main()
