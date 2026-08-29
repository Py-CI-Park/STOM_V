from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from tests.seed_db_guard import open_seed_database

ROOT = Path(__file__).resolve().parents[2]


def test_missing_seed_database_skips_without_creating_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.db"

    with (
        pytest.raises(pytest.skip.Exception, match="seed DB unavailable"),
        open_seed_database(missing, required_tables=("stockbuy",)),
    ):
        pass

    assert missing.exists() is False


def test_seed_database_without_required_table_skips_read_only(tmp_path: Path) -> None:
    empty = tmp_path / "empty.db"
    with sqlite3.connect(empty):
        pass
    size_before = empty.stat().st_size

    with (
        pytest.raises(
            pytest.skip.Exception, match="required seed tables unavailable"
        ),
        open_seed_database(empty, required_tables=("stockbuy",)),
    ):
        pass

    assert empty.stat().st_size == size_before


def test_valid_seed_fixture_is_readable_but_not_writable(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture.db"
    with sqlite3.connect(fixture) as connection:
        _ = connection.execute(
            'CREATE TABLE stockbuy ("index" TEXT, "전략코드" TEXT)'
        )
        _ = connection.execute(
            'INSERT INTO stockbuy ("index", "전략코드") VALUES (?, ?)',
            ("seed", "매수 = True"),
        )

    with open_seed_database(fixture, required_tables=("stockbuy",)) as connection:
        dump = "\n".join(connection.iterdump())
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            _ = connection.execute("CREATE TABLE forbidden (value TEXT)")

    assert "매수 = True" in dump


def test_real_seed_tests_use_shared_read_only_guard() -> None:
    sources = {
        path.name: path.read_text(encoding="utf-8")
        for path in (
            ROOT / "tests" / "unit" / "test_filter_gate.py",
            ROOT / "tests" / "unit" / "test_time_window.py",
            ROOT / "tests" / "unit" / "test_w7_champion_clauses.py",
            ROOT / "tests" / "unit" / "test_w7_condition_diff.py",
        )
    }

    assert all("open_seed_database" in source for source in sources.values())
    assert 'sqlite3.connect("_database/strategy.db")' not in sources[
        "test_w7_champion_clauses.py"
    ]
    assert 'sqlite3.connect("_database/strategy.db")' not in sources[
        "test_w7_condition_diff.py"
    ]
    assert "sqlite3.connect(_SEED_DB)" not in sources["test_filter_gate.py"]
    assert "sqlite3.connect(_SEED_DB)" not in sources["test_time_window.py"]
