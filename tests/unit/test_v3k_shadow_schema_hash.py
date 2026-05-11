from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "init_v3k_shadow_db",
    ROOT / "scripts" / "init_v3k_shadow_db.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
compute_schema_hash = MODULE.compute_schema_hash


def _sample_table() -> dict[str, object]:
    return {
        "columns": [
            "code TEXT NOT NULL",
            "last_update INTEGER NOT NULL DEFAULT 0",
            "confidence_score REAL NOT NULL",
        ],
        "primary_key": ["code", "last_update"],
    }


def test_schema_hash_is_idempotent() -> None:
    table = _sample_table()

    assert compute_schema_hash("stock_sample", table) == compute_schema_hash("stock_sample", table)


def test_schema_hash_is_independent_from_dict_key_order() -> None:
    table_a = _sample_table()
    table_b = {
        "primary_key": ["code", "last_update"],
        "columns": list(table_a["columns"]),
    }

    assert compute_schema_hash("stock_sample", table_a) == compute_schema_hash("stock_sample", table_b)


def test_schema_hash_normalizes_default_sql_whitespace() -> None:
    table_a = {
        "columns": [
            "name TEXT NOT NULL",
            "enabled INTEGER NOT NULL DEFAULT 0",
        ],
        "primary_key": ["name"],
    }
    table_b = {
        "columns": [
            "name TEXT NOT NULL",
            "enabled INTEGER NOT NULL DEFAULT    0",
        ],
        "primary_key": ["name"],
    }

    hash_a = compute_schema_hash("v3k_feature_flags", table_a)
    hash_b = compute_schema_hash("v3k_feature_flags", table_b)

    assert len(hash_a) == 64
    assert hash_a == hash_b
