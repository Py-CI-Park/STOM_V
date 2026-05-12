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

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    V3KAnalyzerAdapter,
    learning_db_manifest,
)


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


def _assert_temp_positive_path() -> None:
    with tempfile.TemporaryDirectory(prefix="v3k-prod-read-") as tmp:
        tmpdir = Path(tmp)
        contract = next(iter(learning_db_manifest()))
        table_name = contract.table_name("stock", False)
        db_path = tmpdir / contract.db_name
        with closing(sqlite3.connect(db_path)) as conn:
            conn.execute(
                f"CREATE TABLE {table_name} (code TEXT, last_update INTEGER, confidence_score REAL)",
            )
            conn.execute(
                f"INSERT INTO {table_name} VALUES (?, ?, ?)",
                ("005930", 20260101, 0.75),
            )
            conn.commit()

        adapter = V3KAnalyzerAdapter(production_db_dir=tmpdir)
        result = adapter.read_production_learning_db(contract.db_name, table_name)
        if not result.exists or not result.table_exists or not result.has_rows:
            raise AssertionError(f"temp production read positive path failed: {result}")
        if result.uri is None or not result.uri.endswith("?mode=ro"):
            raise AssertionError(f"production read must use mode=ro URI: {result.uri}")
        if result.rows[0]["code"] != "005930":
            raise AssertionError(f"sample row mismatch: {result.rows}")


def _assert_real_production_paths_read_or_noop() -> None:
    adapter = V3KAnalyzerAdapter()
    rows = []
    for contract in learning_db_manifest():
        table_name = contract.table_name("stock", False)
        result = adapter.read_production_learning_db(contract.db_name, table_name)
        if result.uri is not None and not result.uri.endswith("?mode=ro"):
            raise AssertionError(f"production read must use mode=ro URI: {result.uri}")
        status = "read" if result.table_exists else ("missing-db" if not result.exists else "missing-table")
        rows.append((contract.db_name, table_name, status, len(result.rows), result.diagnostics))
    if len(rows) != len(learning_db_manifest()):
        raise AssertionError("production read smoke did not cover every learning DB contract")
    for db_name, table_name, status, sample_count, diagnostics in rows:
        print(
            f"production read {db_name}:{table_name} -> {status}, "
            f"samples={sample_count}, diagnostics={diagnostics}",
        )


def main() -> None:
    before = _artifact_status()
    _assert_temp_positive_path()
    _assert_real_production_paths_read_or_noop()
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "production read smoke changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k production learning DB read smoke passed")
    print("mode=ro positive path and real production read/no-op paths verified")


if __name__ == "__main__":
    main()
