"""Read-only market-cap census for aggregate STOM stock databases."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Any, Callable

from ai_strategy_loop.revision.mcap_bands import MCAP_BANDS, mcap_band_case_sql
from utility.sqlite_readonly import (
    assert_sqlite_sidefiles_unchanged,
    connect_existing_db_readonly,
    sqlite_fingerprint,
    sqlite_sidefile_snapshot,
)

AUTHORITY = "existing_db_development_no_oos_no_adoption"
_STOCK_TABLE = re.compile(r"^[0-9A-Za-z_]{1,24}$")


@dataclass(frozen=True, slots=True)
class CensusConfig:
    db_path: str
    lane: str
    source_mode: str = "aggregate_engine_parity"
    min_days: int = 120
    min_symbols: int = 30
    progress_every: int = 25


def _quoted_table(name: str) -> str:
    if not _STOCK_TABLE.fullmatch(name) or name.lower() == "moneytop":
        raise ValueError(f"invalid stock table: {name!r}")
    return '"' + name.replace('"', '""') + '"'


def iter_stock_tables(connection: sqlite3.Connection) -> list[str]:
    names = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )]
    return [name for name in names if _STOCK_TABLE.fullmatch(name) and name.lower() != "moneytop"]


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    quoted = _quoted_table(table)
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({quoted})")}


def _time_expression(lane: str) -> str:
    width = 6 if lane == "stock_tick" else 4
    return f"substr(CAST(\"index\" AS TEXT), 9, {width})"


def scan_table_mcap(connection: sqlite3.Connection, table: str, lane: str) -> list[dict[str, Any]]:
    columns = table_columns(connection, table)
    if "index" not in columns or "시가총액" not in columns:
        return []
    quoted = _quoted_table(table)
    band_sql = mcap_band_case_sql()
    time_sql = _time_expression(lane)
    optional = []
    for column, alias in (("당일거래대금", "avg_turnover"), ("초당거래대금", "avg_second_turnover"), ("체결강도", "avg_strength")):
        optional.append(f'AVG("{column}") AS {alias}' if column in columns else f"NULL AS {alias}")
    query = f"""
        SELECT {band_sql} AS band_id,
               COUNT(*) AS rows,
               COUNT(DISTINCT substr(CAST("index" AS TEXT), 1, 8)) AS days,
               GROUP_CONCAT(DISTINCT substr(CAST("index" AS TEXT), 1, 8)) AS day_values,
               MIN(CAST("index" AS INTEGER)) AS first_index,
               MAX(CAST("index" AS INTEGER)) AS last_index,
               MIN({time_sql}) AS min_time,
               MAX({time_sql}) AS max_time,
               MIN("시가총액") AS min_mcap,
               MAX("시가총액") AS max_mcap,
               AVG("시가총액") AS avg_mcap,
               {', '.join(optional)}
        FROM {quoted}
        GROUP BY {band_sql}
    """
    keys = ("band_id", "rows", "days", "day_values", "first_index", "last_index", "min_time", "max_time",
            "min_mcap", "max_mcap", "avg_mcap", "avg_turnover", "avg_second_turnover", "avg_strength")
    return [dict(zip(keys, row, strict=True)) for row in connection.execute(query)]


def moneytop_scope(connection: sqlite3.Connection, lane: str) -> dict[str, Any]:
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND lower(name)='moneytop'"
    ).fetchone()
    if not exists:
        return {"available": False, "reason": "source_missing"}
    time_sql = _time_expression(lane)
    row = connection.execute(f"""
        SELECT COUNT(*), COUNT(DISTINCT substr(CAST("index" AS TEXT), 1, 8)),
               MIN(CAST("index" AS INTEGER)), MAX(CAST("index" AS INTEGER)),
               MIN({time_sql}), MAX({time_sql}) FROM moneytop
    """).fetchone()
    return {
        "available": True, "rows": row[0], "days": row[1], "first_index": row[2],
        "last_index": row[3], "min_time": row[4], "max_time": row[5],
    }


def scan_mcap_census(config: CensusConfig, *, progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    path = Path(config.db_path).expanduser().resolve(strict=True)
    before_sidefiles = sqlite_sidefile_snapshot(path)
    before_fingerprint = sqlite_fingerprint(path)
    connection = connect_existing_db_readonly(path)
    try:
        tables = iter_stock_tables(connection)
        accumulators = {
            band.band_id: {"band_id": band.band_id, "rows": 0, "symbols": set(), "days_max": 0,
                           "dates": set(),
                           "first_index": None, "last_index": None, "min_time": None, "max_time": None,
                           "min_mcap": None, "max_mcap": None, "weighted_mcap": 0.0}
            for band in MCAP_BANDS
        }
        invalid = {"band_id": "INVALID", "rows": 0, "symbols": set(), "days_max": 0, "dates": set()}
        skipped: list[dict[str, str]] = []
        for index, table in enumerate(tables, start=1):
            try:
                rows = scan_table_mcap(connection, table, config.lane)
            except sqlite3.DatabaseError as exc:
                skipped.append({"table": table, "reason": type(exc).__name__})
                continue
            if not rows:
                skipped.append({"table": table, "reason": "required_columns_missing"})
                continue
            for row in rows:
                target = accumulators.get(row["band_id"], invalid)
                count = int(row["rows"] or 0)
                target["rows"] += count
                target["symbols"].add(table)
                target["days_max"] = max(target.get("days_max", 0), int(row["days"] or 0))
                target["dates"].update((row.get("day_values") or "").split(","))
                if target is invalid:
                    continue
                for key, chooser in (("first_index", min), ("min_time", min), ("min_mcap", min),
                                     ("last_index", max), ("max_time", max), ("max_mcap", max)):
                    value = row.get(key)
                    if value is not None:
                        target[key] = value if target[key] is None else chooser(target[key], value)
                target["weighted_mcap"] += float(row["avg_mcap"] or 0.0) * count
            if progress and (index % config.progress_every == 0 or index == len(tables)):
                progress({"scanned_tables": index, "total_tables": len(tables), "skipped_tables": len(skipped)})
        band_rows = []
        for band in MCAP_BANDS:
            item = accumulators[band.band_id]
            symbol_count = len(item.pop("symbols"))
            weighted = item.pop("weighted_mcap")
            item["symbols"] = symbol_count
            item.pop("days_max")
            item["days"] = len(item.pop("dates") - {""})
            item["avg_mcap"] = weighted / item["rows"] if item["rows"] else None
            item["verdict"] = (
                "CENSUS_PASS" if item["days"] >= config.min_days and symbol_count >= config.min_symbols
                else "INSUFFICIENT_SAMPLE"
            )
            band_rows.append(item)
        stock_times = [value for row in band_rows for value in (row["min_time"], row["max_time"]) if value]
        return {
            "schema": "stom.mcap_census.v1",
            "authority": AUTHORITY,
            "source": {"path": str(path), "lane": config.lane, "source_mode": config.source_mode,
                       "fingerprint": before_fingerprint},
            "moneytop_scope": moneytop_scope(connection, config.lane),
            "stock_table_scope": {
                "table_count": len(tables), "scanned_tables": len(tables) - len(skipped),
                "skipped_tables": len(skipped), "min_time": min(stock_times) if stock_times else None,
                "max_time": max(stock_times) if stock_times else None,
            },
            "bands": band_rows,
            "invalid": {"rows": invalid["rows"], "symbols": len(invalid["symbols"])},
            "skipped": skipped[:200],
            "window_contract": "pending_census_verdict",
            "can_adopt": False,
        }
    finally:
        connection.close()
        assert_sqlite_sidefiles_unchanged(path, before_sidefiles)
        if sqlite_fingerprint(path) != before_fingerprint:
            raise RuntimeError("market database changed during census")
