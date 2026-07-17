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
@pytest.mark.skipif(os.name != "nt", reason="Windows authority is the supported platform")
def test_catalog_hash_query_validation_denies_same_inode_overwrite(tmp_path: Path):
    from alpha_lab.discipline.prereg import _WindowsAuthorityGuard

    catalog = tmp_path / "catalog.db"
    records = _write_catalog_db(catalog)
    original = catalog.read_bytes()
    guard = _WindowsAuthorityGuard(tmp_path, {}, ())
    try:
        guard.hold_write_denied_file(catalog)
        observed = evidence._hash_retained_file(guard, catalog, "catalog test")
        evidence._verify_catalog_authority_db(catalog, records)
        with pytest.raises(OSError) as exc:
            catalog.write_bytes(b"same-inode overwrite")
        assert (
            getattr(exc.value, "winerror", None) in {5, 32}
            or exc.value.errno == 13
        )
        assert catalog.read_bytes() == original
        assert evidence._hash_retained_file(guard, catalog, "catalog test") == observed
    finally:
        guard.close()


def test_catalog_authority_rejects_hash_a_then_query_b(tmp_path: Path, monkeypatch):
    catalog = tmp_path / "catalog.db"
    replacement = tmp_path / "replacement.db"
    records = _write_catalog_db(catalog)
    _write_catalog_db(replacement, user_version=1)

    class RetainedGuard:
        def hold_path(self, path: Path) -> None:
            pass

        def hold_write_denied_file(self, path: Path) -> None:
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
