from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    V3KAnalyzerAdapter,
    learning_db_manifest,
    safe_identifier,
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


def _max_last_update(adapter: V3KAnalyzerAdapter, db_name: str, table_name: str) -> int | None:
    db_path = adapter.production_learning_db_path(db_name)
    if not db_path.exists():
        return None
    uri = db_path.resolve().as_uri() + "?mode=ro"
    safe_table = safe_identifier(table_name)
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=0.1)) as conn:
            exists = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
            if exists is None:
                return None
            columns = {row[1] for row in conn.execute(f"PRAGMA table_info({safe_table})")}
            if "last_update" not in columns:
                return None
            row = conn.execute(f"SELECT MAX(last_update) FROM {safe_table}").fetchone()
            return None if row is None or row[0] is None else int(row[0])
    except sqlite3.Error as exc:
        print(f"leakage guard no-op for {db_name}:{table_name}: {type(exc).__name__}: {exc}")
        return None


def _assert_no_leakage(adapter: V3KAnalyzerAdapter, backtest_date: int) -> None:
    leaks: list[str] = []
    checked = 0
    for contract in learning_db_manifest():
        table_name = contract.table_name("stock", False)
        max_update = _max_last_update(adapter, contract.db_name, table_name)
        if max_update is None:
            print(f"leakage guard {contract.db_name}:{table_name} -> no-op")
            continue
        checked += 1
        print(f"leakage guard {contract.db_name}:{table_name} -> max_last_update={max_update}")
        if max_update >= backtest_date:
            leaks.append(f"{contract.db_name}:{table_name}:{max_update} >= {backtest_date}")
    if leaks:
        raise AssertionError(f"V3K learning DB leakage guard failed: {leaks}")
    print(f"leakage guard PASS: checked={checked}, backtest_date={backtest_date}")


def _write_temp_learning_db(tmpdir: Path, db_name: str, table_name: str, last_update: int) -> None:
    db_path = tmpdir / db_name
    safe_table = safe_identifier(table_name)
    with closing(sqlite3.connect(db_path)) as conn:
        conn.execute(f"CREATE TABLE {safe_table} (code TEXT, last_update INTEGER, confidence_score REAL)")
        conn.execute(
            f"INSERT INTO {safe_table} VALUES (?, ?, ?)",
            ("005930", last_update, 0.5),
        )
        conn.commit()


def _assert_temp_leakage_detector() -> None:
    contract = next(iter(learning_db_manifest()))
    table_name = contract.table_name("stock", False)
    with tempfile.TemporaryDirectory(prefix="v3k-leakage-pass-") as tmp:
        tmpdir = Path(tmp)
        _write_temp_learning_db(tmpdir, contract.db_name, table_name, 20260101)
        _assert_no_leakage(V3KAnalyzerAdapter(production_db_dir=tmpdir), 20260512)
    with tempfile.TemporaryDirectory(prefix="v3k-leakage-fail-") as tmp:
        tmpdir = Path(tmp)
        _write_temp_learning_db(tmpdir, contract.db_name, table_name, 20260512)
        try:
            _assert_no_leakage(V3KAnalyzerAdapter(production_db_dir=tmpdir), 20260512)
        except AssertionError:
            return
        raise AssertionError("temp leakage violation was not detected")


def main() -> None:
    before = _artifact_status()
    _assert_temp_leakage_detector()
    backtest_date = int(datetime.now().strftime("%Y%m%d"))
    _assert_no_leakage(V3KAnalyzerAdapter(), backtest_date)
    after = _artifact_status()
    if before != after:
        raise AssertionError(
            "leakage guard changed runtime artifacts:\n"
            f"before={before!r}\nafter={after!r}",
        )
    print("v3k production learning DB leakage guard smoke passed")


if __name__ == "__main__":
    main()
