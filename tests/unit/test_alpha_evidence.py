"""Authority identity regressions for discipline evidence validation."""
from __future__ import annotations

import contextlib
import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from alpha_lab.discipline import evidence


def _write_catalog_db(path: Path, *, user_version: int = 0) -> list[dict[str, str]]:
    records = [{
        "name": "candidate-a",
        "buy_sha256": "a" * 64,
        "sell_sha256": "b" * 64,
        "phase": "PRE",
        "outcome": "authorized",
        "disposition": "pending_post",
    }]
    con = sqlite3.connect(path)
    try:
        con.execute(
            "CREATE TABLE catalog_authority (name TEXT PRIMARY KEY, "
            "buy_sha256 TEXT NOT NULL, sell_sha256 TEXT NOT NULL, phase TEXT NOT NULL, "
            "outcome TEXT NOT NULL, disposition TEXT NOT NULL)"
        )
        con.execute(
            "INSERT INTO catalog_authority VALUES (?, ?, ?, ?, ?, ?)",
            tuple(records[0].values()),
        )
        con.execute(f"PRAGMA user_version = {user_version}")
        con.commit()
    finally:
        con.close()
    return records


def test_catalog_authority_rejects_hash_a_then_query_b(tmp_path: Path, monkeypatch):
    catalog = tmp_path / "catalog.db"
    replacement = tmp_path / "replacement.db"
    records = _write_catalog_db(catalog)
    _write_catalog_db(replacement, user_version=1)

    class RetainedGuard:
        def hold_path(self, path: Path) -> None:
            pass

        def open_path(self, path: Path, flags: int) -> int:
            return os.open(path, flags)

        def validate_file(self, path: Path) -> None:
            pass

    @contextlib.contextmanager
    def retained_guard(*args, **kwargs):
        yield RetainedGuard()

    from alpha_lab.discipline import prereg

    monkeypatch.setattr(prereg, "authority_mutation_guard", retained_guard)
    original_verify = evidence._verify_catalog_authority_db

    def swap_then_query(path: Path, expected_records: list[dict[str, str]]) -> None:
        os.replace(replacement, path)
        original_verify(path, expected_records)

    monkeypatch.setattr(evidence, "_verify_catalog_authority_db", swap_then_query)

    with pytest.raises(evidence.EvidenceSchemaError, match="pathname identity changed"):
        evidence._verify_catalog_authority_db_from_retained_identity(
            tmp_path,
            {"catalog_dir": "catalog"},
            catalog,
            hashlib.sha256(catalog.read_bytes()).hexdigest(),
            records,
        )
