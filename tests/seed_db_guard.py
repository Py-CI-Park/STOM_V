"""Read-only access guard for optional human seed databases used by tests."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest


@contextmanager
def open_seed_database(
    path: str | Path, *, required_tables: tuple[str, ...]
) -> Iterator[sqlite3.Connection]:
    database = Path(path).resolve()
    if not database.is_file():
        pytest.skip(f"seed DB unavailable: {database}")
    try:
        connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        pytest.skip(f"seed DB unavailable: {database}: {exc}")
    try:
        missing = sorted(
            table
            for table in required_tables
            if connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table,),
            ).fetchone()
            is None
        )
        if missing:
            pytest.skip(
                "required seed tables unavailable: " + ", ".join(missing)
            )
        yield connection
    finally:
        connection.close()
