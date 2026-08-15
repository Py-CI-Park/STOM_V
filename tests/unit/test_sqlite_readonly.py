from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    connect_existing_db_readonly,
    sqlite_fingerprint,
    sqlite_sidefile_snapshot,
)


def _db(path: Path) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO sample(value) VALUES ('ok')")
    connection.commit()
    connection.close()


def test_connector_reads_existing_database_without_sidefiles(tmp_path):
    path = tmp_path / "source.db"
    _db(path)
    before = sqlite_sidefile_snapshot(path)
    connection = connect_existing_db_readonly(path)
    assert connection.execute("SELECT value FROM sample").fetchone() == ("ok",)
    assert connection.execute("PRAGMA query_only").fetchone() == (1,)
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("INSERT INTO sample(value) VALUES ('blocked')")
    connection.close()
    assert_sqlite_sidefiles_unchanged(path, before)


def test_connector_fails_closed_for_missing_database(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        connect_existing_db_readonly(path)
    assert not path.exists()


def test_fingerprint_detects_source_change(tmp_path):
    path = tmp_path / "source.db"
    _db(path)
    before = sqlite_fingerprint(path)
    connection = sqlite3.connect(path)
    connection.execute("INSERT INTO sample(value) VALUES ('changed')")
    connection.commit()
    connection.close()
    after = sqlite_fingerprint(path)
    assert before["sha256"] != after["sha256"]
    assert before["hash_mode"] == "full"


def test_large_fingerprint_uses_deterministic_sample_mode(tmp_path):
    path = tmp_path / "large.db"
    path.write_bytes(b"0123456789" * 100)
    first = sqlite_fingerprint(path, full_hash_limit=10)
    second = sqlite_fingerprint(path, full_hash_limit=10)
    assert first["hash_mode"] == "sampled_v1"
    assert first["sha256"] == second["sha256"]
