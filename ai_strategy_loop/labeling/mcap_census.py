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


def _bucket_expression(lane: str) -> str:
    value = _time_expression(lane)
    return (
        f"(CAST(substr({value}, 1, 2) AS INTEGER) * 60 + "
        f"CAST(substr({value}, 3, 2) AS INTEGER)) / 5 * 5"
    )


def _minute_to_hhmmss(minute: int) -> str:
    hour, minute_of_hour = divmod(minute, 60)
    return f"{hour:02d}{minute_of_hour:02d}00"


def _longest_contiguous_buckets(values: set[int]) -> list[int]:
    runs: list[list[int]] = []
    for value in sorted(values):
        if not runs or value != runs[-1][-1] + 5:
            runs.append([value])
        else:
            runs[-1].append(value)
    return max(runs, key=lambda run: (len(run), -run[0]), default=[])


def scan_table_mcap(connection: sqlite3.Connection, table: str, lane: str) -> list[dict[str, Any]]:
    columns = table_columns(connection, table)
    if "index" not in columns or "시가총액" not in columns:
        return []
    quoted = _quoted_table(table)
    band_sql = mcap_band_case_sql()
    time_sql = _time_expression(lane)
    bucket_sql = _bucket_expression(lane)
    optional = []
    for column, alias in (("당일거래대금", "avg_turnover"), ("초당거래대금", "avg_second_turnover"), ("체결강도", "avg_strength")):
        optional.append(f'AVG("{column}") AS {alias}' if column in columns else f"NULL AS {alias}")
    query = f"""
        SELECT {band_sql} AS band_id, {bucket_sql} AS bucket_minute,
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
        GROUP BY {band_sql}, {bucket_sql}
    """
    keys = ("band_id", "bucket_minute", "rows", "days", "day_values", "first_index", "last_index",
            "min_time", "max_time", "min_mcap", "max_mcap", "avg_mcap", "avg_turnover",
            "avg_second_turnover", "avg_strength")
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


def moneytop_membership_masks(connection: sqlite3.Connection, lane: str, tables: list[str]) -> tuple[dict[tuple[str, int], int], dict[str, Any]]:
    columns = [str(row[1]) for row in connection.execute("PRAGMA table_info(moneytop)")]
    value_columns = [column for column in columns if column != "index"]
    if not value_columns:
        return {}, {"available": False, "reason": "membership_column_missing"}
    membership_column = "거래대금순위" if "거래대금순위" in value_columns else value_columns[0]
    code_bits = {code: 1 << index for index, code in enumerate(tables)}
    masks: dict[tuple[str, int], int] = {}
    unknown_codes: set[str] = set()
    quoted_column = '"' + membership_column.replace('"', '""') + '"'
    query = (
        f'SELECT substr(CAST("index" AS TEXT), 1, 8), {_bucket_expression(lane)}, {quoted_column} '
        "FROM moneytop"
    )
    for day, bucket, raw_codes in connection.execute(query):
        key = (str(day), int(bucket))
        mask = masks.get(key, 0)
        for code in re.split(r"[;,|\s]+", str(raw_codes or "")):
            if not code:
                continue
            bit = code_bits.get(code)
            if bit is None:
                unknown_codes.add(code)
            else:
                mask |= bit
        masks[key] = mask
    return masks, {
        "available": True, "membership_column": membership_column,
        "day_buckets": len(masks), "unknown_codes": len(unknown_codes),
        "unknown_code_sample": sorted(unknown_codes)[:20],
    }


def _source_unavailable(path: Path, config: CensusConfig, fingerprint: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema": "stom.mcap_census.v2", "authority": AUTHORITY,
        "status": "SOURCE_UNAVAILABLE", "reason": reason,
        "source": {"path": str(path), "lane": config.lane, "source_mode": config.source_mode,
                   "fingerprint": fingerprint},
        "bands": [], "can_adopt": False,
    }


def scan_mcap_census(config: CensusConfig, *, progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    path = Path(config.db_path).expanduser().resolve(strict=True)
    before_sidefiles = sqlite_sidefile_snapshot(path)
    before_fingerprint = sqlite_fingerprint(path)
    connection = connect_existing_db_readonly(path)
    try:
        tables = iter_stock_tables(connection)
        if not tables:
            return _source_unavailable(path, config, before_fingerprint, "stock_tables_missing")
        moneytop = moneytop_scope(connection, config.lane)
        if not moneytop.get("available"):
            return _source_unavailable(path, config, before_fingerprint, "moneytop_missing")
        membership_masks, membership_meta = moneytop_membership_masks(connection, config.lane, tables)
        if not membership_meta.get("available"):
            return _source_unavailable(path, config, before_fingerprint, str(membership_meta.get("reason")))
        accumulators = {
            band.band_id: {
                "band_id": band.band_id, "rows": 0, "symbols_set": set(), "dates": set(),
                "first_index": None, "last_index": None, "min_time": None, "max_time": None,
                "min_mcap": None, "max_mcap": None, "weighted_mcap": 0.0,
                "intersection_code_days": 0, "bucket_rows": {}, "bucket_code_days": {},
                "bucket_dates": {}, "bucket_symbols": {},
            }
            for band in MCAP_BANDS
        }
        invalid = {"rows": 0, "symbols": set()}
        skipped: list[dict[str, str]] = []
        code_bits = {code: 1 << index for index, code in enumerate(tables)}
        for index, table in enumerate(tables, start=1):
            try:
                rows = scan_table_mcap(connection, table, config.lane)
            except sqlite3.DatabaseError as exc:
                skipped.append({"table": table, "reason": type(exc).__name__})
                continue
            if not rows:
                skipped.append({"table": table, "reason": "required_columns_missing"})
                continue
            local_intersection_dates = {band.band_id: set() for band in MCAP_BANDS}
            table_bit = code_bits[table]
            for row in rows:
                count = int(row["rows"] or 0)
                target = accumulators.get(row["band_id"])
                if target is None:
                    invalid["rows"] += count
                    invalid["symbols"].add(table)
                    continue
                target["rows"] += count
                target["symbols_set"].add(table)
                row_days = {day for day in (row.get("day_values") or "").split(",") if day}
                target["dates"].update(row_days)
                bucket = int(row["bucket_minute"])
                target["bucket_rows"][bucket] = target["bucket_rows"].get(bucket, 0) + count
                matching_dates = {
                    day for day in row_days if membership_masks.get((day, bucket), 0) & table_bit
                }
                if matching_dates:
                    target["bucket_dates"].setdefault(bucket, set()).update(matching_dates)
                    target["bucket_symbols"].setdefault(bucket, set()).add(table)
                    target["bucket_code_days"][bucket] = target["bucket_code_days"].get(bucket, 0) + len(matching_dates)
                    local_intersection_dates[target["band_id"]].update(matching_dates)
                for key, chooser in (("first_index", min), ("min_time", min), ("min_mcap", min),
                                     ("last_index", max), ("max_time", max), ("max_mcap", max)):
                    value = row.get(key)
                    if value is not None:
                        target[key] = value if target[key] is None else chooser(target[key], value)
                target["weighted_mcap"] += float(row["avg_mcap"] or 0.0) * count
            for band_id, dates in local_intersection_dates.items():
                accumulators[band_id]["intersection_code_days"] += len(dates)
            if progress and (index % config.progress_every == 0 or index == len(tables)):
                progress({"scanned_tables": index, "total_tables": len(tables), "skipped_tables": len(skipped)})
        band_rows = []
        valid_bucket_sets = []
        for band in MCAP_BANDS:
            item = accumulators[band.band_id]
            symbol_count = len(item.pop("symbols_set"))
            weighted = item.pop("weighted_mcap")
            item["symbols"] = symbol_count
            item["days"] = len(item.pop("dates"))
            item["avg_mcap"] = weighted / item["rows"] if item["rows"] else None
            bucket_dates = item.pop("bucket_dates")
            bucket_symbols = item.pop("bucket_symbols")
            item["buckets"] = [
                {"minute": bucket, "time": _minute_to_hhmmss(bucket),
                 "rows": item["bucket_rows"].get(bucket, 0),
                 "moneytop_code_days": item["bucket_code_days"].get(bucket, 0),
                 "days": len(bucket_dates.get(bucket, set())),
                 "symbols": len(bucket_symbols.get(bucket, set()))}
                for bucket in sorted(item["bucket_rows"])
            ]
            item.pop("bucket_rows")
            item.pop("bucket_code_days")
            item["verdict"] = (
                "CENSUS_PASS" if item["days"] >= config.min_days and symbol_count >= config.min_symbols
                and item["intersection_code_days"] > 0 else "INSUFFICIENT_SAMPLE"
            )
            valid_bucket_sets.append({
                bucket["minute"] for bucket in item["buckets"]
                if bucket["days"] >= config.min_days and bucket["symbols"] >= config.min_symbols
            })
            band_rows.append(item)
        common_buckets = _longest_contiguous_buckets(
            set.intersection(*valid_bucket_sets) if valid_bucket_sets else set()
        )
        window_contract = (
            {"status": "AVAILABLE", "start": _minute_to_hhmmss(min(common_buckets)),
             "end_exclusive": _minute_to_hhmmss(max(common_buckets) + 5),
             "bucket_minutes": sorted(common_buckets),
             "basis": "moneytop_stock_intersection_all_four_bands"}
            if common_buckets else
            {"status": "SOURCE_COVERAGE_UNAVAILABLE", "start": None, "end_exclusive": None,
             "bucket_minutes": [], "basis": "moneytop_stock_intersection_all_four_bands"}
        )
        stock_times = [value for row in band_rows for value in (row["min_time"], row["max_time"]) if value]
        skipped_counts: dict[str, int] = {}
        for item in skipped:
            skipped_counts[item["reason"]] = skipped_counts.get(item["reason"], 0) + 1
        return {
            "schema": "stom.mcap_census.v2", "authority": AUTHORITY, "status": "CENSUS_COMPLETED",
            "source": {"path": str(path), "lane": config.lane, "source_mode": config.source_mode,
                       "fingerprint": before_fingerprint, "fingerprint_semantics": before_fingerprint["hash_mode"]},
            "moneytop_scope": {**moneytop, **membership_meta},
            "stock_table_scope": {"table_count": len(tables), "scanned_tables": len(tables) - len(skipped),
                                  "skipped_tables": len(skipped), "min_time": min(stock_times) if stock_times else None,
                                  "max_time": max(stock_times) if stock_times else None},
            "bands": band_rows,
            "invalid": {"rows": invalid["rows"], "symbols": len(invalid["symbols"])},
            "skipped": {"counts_by_reason": skipped_counts, "sample": skipped[:200]},
            "distribution_scope": {
                "available": True,
                "metrics": ["rows", "mcap_min_max_weighted_mean", "five_minute_moneytop_intersection"],
                "quantiles": "deferred_to_backfinder_event_stage",
                "microstructure": "deferred_to_backfinder_event_stage",
            },
            "window_contract": window_contract,
            "can_adopt": False,
        }
    finally:
        connection.close()
        assert_sqlite_sidefiles_unchanged(path, before_sidefiles)
        if sqlite_fingerprint(path) != before_fingerprint:
            raise RuntimeError("market database changed during census")
