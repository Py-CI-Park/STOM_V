"""Schema helpers for mapping CLI queries to live STOM SQLite schemas."""

from __future__ import annotations

import sqlite3
from typing import Dict, Iterable, List, Optional

# Candidate columns for ordering backtest results.
BACKTEST_ORDER_COLUMNS = ["created_at", "datetime", "id"]

# Candidate columns used to locate strategy names.
STRATEGY_NAME_COLUMNS = ["index", "name", "전략명"]

# Tradelist table candidates mapped by asset type.
TRADELIST_TABLES: Dict[str, Dict[str, List[str]]] = {
    "positions": {
        "stock": ["s_jangolist"],
        "coin": ["c_jangolist", "c_jangolist_future"],
        "future": ["f_jangolist"],
    },
    "orders": {
        "stock": ["s_chegeollist"],
        "coin": ["c_chegeollist"],
        "future": ["f_chegeollist"],
    },
    "trades": {
        "stock": ["s_tradelist"],
        "coin": ["c_tradelist", "c_tradelist_future"],
        "future": ["f_tradelist"],
    },
    "totals": {
        "stock": ["s_totaltradelist"],
        "coin": ["c_totaltradelist", "f_totaltradelist"],
        "future": ["f_totaltradelist"],
    },
}


def list_tables(connection: sqlite3.Connection) -> List[str]:
    """Return all SQLite table names sorted alphabetically."""
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    """Return True when a table exists."""
    cursor = connection.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    )
    return cursor.fetchone() is not None


def list_columns(connection: sqlite3.Connection, table_name: str) -> List[str]:
    """Return column names for the given table."""
    cursor = connection.cursor()
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    return [row[1] for row in cursor.fetchall()]


def find_first_column(
    connection: sqlite3.Connection,
    table_name: str,
    candidates: Iterable[str],
) -> Optional[str]:
    """Return the first matching candidate column in the table, or None."""
    columns = set(list_columns(connection, table_name))
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def resolve_existing_tables(
    connection: sqlite3.Connection,
    candidates: Iterable[str],
) -> List[str]:
    """Return candidate tables that exist, preserving candidate order."""
    existing = set(list_tables(connection))
    return [table for table in candidates if table in existing]


def get_tradelist_tables(
    connection: sqlite3.Connection,
    kind: str,
    asset_type: Optional[str] = None,
) -> List[str]:
    """Return resolved tradelist tables for a table kind and optional asset type."""
    table_map = TRADELIST_TABLES.get(kind, {})
    if asset_type:
        return resolve_existing_tables(connection, table_map.get(asset_type, []))

    merged: List[str] = []
    for key in ("stock", "coin", "future"):
        merged.extend(table_map.get(key, []))
    return resolve_existing_tables(connection, merged)


def detect_backtest_order_column(
    connection: sqlite3.Connection,
    table_name: str = "backtest_results",
) -> str:
    """Resolve the safest order column for backtest history queries."""
    resolved = find_first_column(connection, table_name, BACKTEST_ORDER_COLUMNS)
    return resolved or "id"


def detect_strategy_name_column(
    connection: sqlite3.Connection,
    table_name: str,
) -> Optional[str]:
    """Resolve the strategy name key column from known variants."""
    return find_first_column(connection, table_name, STRATEGY_NAME_COLUMNS)
