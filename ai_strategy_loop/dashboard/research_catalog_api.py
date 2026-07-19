"""Read-only rdc-1 research catalog routes."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path, PureWindowsPath
import sqlite3
import time
from typing import Any, Final, Sequence
from urllib.parse import quote

from fastapi import APIRouter


router = APIRouter()

_CATALOG_ENV: Final[str] = "STOM_RESEARCH_ASSETS_DB"
_CONTRACT_VERSION: Final[str] = "rdc-1"
_BUSY_ATTEMPTS: Final[int] = 2
_BUSY_DELAY_SECONDS: Final[float] = 0.05
_CONNECT_TIMEOUT_SECONDS: Final[float] = 0.1
_ASSETS_DEFAULT_LIMIT: Final[int] = 500
_ASSETS_MAX_LIMIT: Final[int] = 5000
_JUDGMENTS_DEFAULT_LIMIT: Final[int] = 200
_JUDGMENTS_MAX_LIMIT: Final[int] = 5000
_CELLS_DEFAULT_LIMIT: Final[int] = 2000
_CELLS_MAX_LIMIT: Final[int] = 10000
_TEXT_FILTER_MAX: Final[int] = 240

_REQUIRED_COLUMNS: Final[dict[str, tuple[str, ...]]] = {
    "assets": (
        "asset_id",
        "kind",
        "path",
        "produced_commit",
        "seal_doc",
        "window",
        "status_tag",
        "regen_cmd",
        "summary",
        "exists_on_disk",
        "sha256",
        "size_bytes",
        "mtime_utc",
    ),
    "judgments": (
        "series",
        "verdict",
        "key_metrics_json",
        "ledger_rows",
        "n_ledger_rows",
        "report_path",
        "source_path",
        "produced_commit",
        "ga_path_flag",
        "note",
    ),
    "clauses": (
        "clause_num",
        "text",
        "family",
        "w5_category",
        "tier",
        "n_sat",
        "n_unsat",
        "delta_pp",
        "ci_low_pp",
        "ci_high_pp",
        "mde_pp",
        "p_one_sided",
        "p_two_sided",
        "both_year_positive",
        "both_year_negative",
        "floor_pass",
        "fdr_survive",
        "classification",
        "year_delta_json",
        "extra_json",
    ),
    "strategies": (
        "name",
        "source_section",
        "family",
        "rank_by_total",
        "total_return_pct",
        "annual_return_pct",
        "monthly_return_pct",
        "mdd_pct",
        "win_rate",
        "payoff",
        "trades",
        "api_compat",
        "source_sha256",
        "lineage",
        "rank_metrics_json",
        "status_tag",
    ),
    "cells": (
        "cell_id",
        "source",
        "source_path",
        "label_kind",
        "label_tag",
        "axis_set",
        "map_type",
        "time_label",
        "time_b",
        "updown_q",
        "mktcap_b",
        "gap_b",
        "gap_label",
        "win",
        "win_label",
        "exit_kind",
        "h",
        "n",
        "n_candidates",
        "censor_rate",
        "exclusion_rate",
        "insufficient",
        "mean_net",
        "median_net",
        "q25_net",
        "q75_net",
        "p_net_ge0",
        "p_net_ge1",
        "ci_low",
        "ci_high",
        "winrate",
        "payoff",
        "mfe_mean",
        "mae_mean",
        "year2022_mean",
        "year2022_sign",
        "year2023_mean",
        "year2023_sign",
        "extra_json",
    ),
    "ledger_mirror": (
        "row_num",
        "ts",
        "series",
        "window",
        "trial_type",
        "target",
        "result",
        "session",
        "raw_json",
    ),
}
_ASSET_COLUMNS: Final[tuple[str, ...]] = _REQUIRED_COLUMNS["assets"]
_JUDGMENT_COLUMNS: Final[tuple[str, ...]] = _REQUIRED_COLUMNS["judgments"]
_CELL_COLUMNS: Final[tuple[str, ...]] = _REQUIRED_COLUMNS["cells"]
_CLAUSE_COLUMNS: Final[tuple[str, ...]] = _REQUIRED_COLUMNS["clauses"]
_LEDGER_COLUMNS: Final[tuple[str, ...]] = _REQUIRED_COLUMNS["ledger_mirror"]

_CELL_INT_FILTERS: Final[dict[str, str]] = {
    "time_b": "time_b",
    "updown_q": "updown_q",
    "mktcap_b": "mktcap_b",
    "gap_b": "gap_b",
    "win": "win",
}


def _unavailable(reason: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"available": False, "reason": reason, "contract_version": _CONTRACT_VERSION}
    for key, value in extra.items():
        if value is not None:
            payload[key] = value
    return payload


def _invalid_param(param: str, allowed: Sequence[str] | None = None) -> dict[str, Any]:
    extra: dict[str, Any] = {"param": param}
    if allowed is not None:
        extra["allowed"] = list(allowed)
    return _unavailable("invalid_param", **extra)


def _catalog_payload(mtime_utc: str, structure_ok: bool = True) -> dict[str, Any]:
    return {"db_mtime_utc": mtime_utc, "structure_ok": structure_ok}


def _success(catalog: dict[str, Any], items: list[dict[str, Any]], **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "available": True,
        "contract_version": _CONTRACT_VERSION,
        "catalog": catalog,
        "items": items,
        "count": len(items),
    }
    payload.update(extra)
    return payload


def _single_success(catalog: dict[str, Any], item: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "available": True,
        "contract_version": _CONTRACT_VERSION,
        "catalog": catalog,
        "item": item,
        "count": 1 if item is not None else 0,
    }


def _configured_path() -> Path | None:
    raw = os.environ.get(_CATALOG_ENV, "").strip()
    if not raw:
        return None
    if not (Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute()):
        return None
    return Path(raw)


def _path_hint(path: Path) -> str:
    name = path.name
    parent = path.parent.name
    return f"{parent}/{name}" if parent else name


def _db_uri(path: Path) -> str:
    encoded = quote(path.resolve(strict=False).as_posix(), safe="/:")
    return f"file:{encoded}?mode=ro"


def _is_busy(exc: sqlite3.Error) -> bool:
    text = str(exc).casefold()
    return "busy" in text or "locked" in text


def _connect_read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(_db_uri(path), uri=True, timeout=_CONNECT_TIMEOUT_SECONDS)


def _columns_sql(columns: Sequence[str]) -> str:
    return ", ".join(columns)


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def _missing_schema(conn: sqlite3.Connection) -> list[str]:
    missing: list[str] = []
    for table, required in _REQUIRED_COLUMNS.items():
        cursor = conn.execute(f"PRAGMA table_info({table})")
        present = {str(row[1]) for row in cursor.fetchall()}
        if not present:
            missing.append(table)
            continue
        for column in required:
            if column not in present:
                missing.append(f"{table}.{column}")
    return missing


def _catalog_connection() -> tuple[sqlite3.Connection | None, dict[str, Any] | None, dict[str, Any] | None]:
    path = _configured_path()
    if path is None:
        return None, None, _unavailable("catalog_not_configured")
    if not path.is_file():
        return None, None, _unavailable("catalog_not_found", path_hint=_path_hint(path))
    try:
        stat = path.stat()
    except FileNotFoundError:
        return None, None, _unavailable("catalog_not_found", path_hint=_path_hint(path))
    except OSError:
        return None, None, _unavailable("catalog_open_error")

    mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    catalog = _catalog_payload(mtime_utc)
    for attempt in range(_BUSY_ATTEMPTS):
        try:
            conn = _connect_read_only(path)
            conn.row_factory = sqlite3.Row
            missing = _missing_schema(conn)
            if missing:
                conn.close()
                catalog = _catalog_payload(mtime_utc, structure_ok=False)
                return None, catalog, _unavailable("schema_mismatch", catalog=catalog, missing=missing)
            return conn, catalog, None
        except sqlite3.OperationalError as exc:
            if _is_busy(exc):
                if attempt + 1 < _BUSY_ATTEMPTS:
                    time.sleep(_BUSY_DELAY_SECONDS)
                    continue
                return None, catalog, _unavailable("catalog_busy", catalog=catalog)
            return None, catalog, _unavailable("catalog_open_error", catalog=catalog)
        except sqlite3.Error:
            return None, catalog, _unavailable("catalog_open_error", catalog=catalog)
    return None, catalog, _unavailable("catalog_busy", catalog=catalog)


def _parse_limit(value: str | None, default: int, max_limit: int) -> tuple[int | None, dict[str, Any] | None]:
    if value in (None, ""):
        return default, None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None, _invalid_param("limit")
    if parsed < 1:
        return None, _invalid_param("limit")
    return min(parsed, max_limit), None


def _parse_offset(value: str | None) -> tuple[int | None, dict[str, Any] | None]:
    if value in (None, ""):
        return 0, None
    try:
        parsed = int(str(value).strip())
    except ValueError:
        return None, _invalid_param("offset")
    if parsed < 0:
        return None, _invalid_param("offset")
    return parsed, None


def _parse_flag(value: str | None, param: str) -> tuple[int | None, dict[str, Any] | None]:
    if value in (None, ""):
        return None, None
    stripped = str(value).strip()
    if stripped not in {"0", "1"}:
        return None, _invalid_param(param, allowed=("0", "1"))
    return int(stripped), None


def _parse_optional_int(value: str | None, param: str) -> tuple[int | None, dict[str, Any] | None]:
    if value in (None, ""):
        return None, None
    try:
        return int(str(value).strip()), None
    except ValueError:
        return None, _invalid_param(param)


def _clean_text_filter(value: str | None, param: str) -> tuple[str | None, dict[str, Any] | None]:
    if value in (None, ""):
        return None, None
    text = str(value).strip()
    if not text:
        return None, None
    if len(text) > _TEXT_FILTER_MAX:
        return None, _invalid_param(param)
    return text, None


def _like_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _decode_object(raw: Any, empty: Any) -> tuple[Any, bool]:
    if raw in (None, ""):
        return empty, False
    try:
        decoded = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return empty, True
    if not isinstance(decoded, dict):
        return empty, True
    return decoded, False


def _decode_int_csv(raw: Any) -> tuple[list[int], bool]:
    if raw in (None, ""):
        return [], False
    values: list[int] = []
    bad = False
    for piece in str(raw).split(","):
        text = piece.strip()
        if not text:
            continue
        try:
            values.append(int(text))
        except ValueError:
            bad = True
    return values, bad


def _query_error(exc: sqlite3.Error, catalog: dict[str, Any]) -> dict[str, Any]:
    reason = "catalog_busy" if _is_busy(exc) else "catalog_open_error"
    return _unavailable(reason, catalog=catalog)


def _select_rows(
    conn: sqlite3.Connection,
    columns: Sequence[str],
    table: str,
    where: Sequence[str],
    params: Sequence[Any],
    order_by: str,
    limit: int | None = None,
    offset: int | None = None,
) -> list[dict[str, Any]]:
    sql = f"SELECT {_columns_sql(columns)} FROM {table}"
    sql_params: list[Any] = list(params)
    if where:
        sql = f"{sql} WHERE {' AND '.join(where)}"
    sql = f"{sql} ORDER BY {order_by}"
    if limit is not None:
        sql = f"{sql} LIMIT ?"
        sql_params.append(limit)
    if offset is not None:
        sql = f"{sql} OFFSET ?"
        sql_params.append(offset)
    return _rows(conn.execute(sql, tuple(sql_params)))


def _decode_judgment(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    metrics, metrics_error = _decode_object(item.pop("key_metrics_json", None), {})
    ledger_rows, ledger_error = _decode_int_csv(item.get("ledger_rows"))
    item["key_metrics"] = metrics
    item["ledger_rows"] = ledger_rows
    if metrics_error:
        item["key_metrics_error"] = True
    if ledger_error:
        item["ledger_rows_error"] = True
    return item


def _add_ledger_rows(conn: sqlite3.Connection, item: dict[str, Any]) -> None:
    row_nums = item.get("ledger_rows")
    if not isinstance(row_nums, list) or not row_nums:
        item["ledger"] = []
        return
    placeholders = ", ".join("?" for _ in row_nums)
    sql = (
        f"SELECT {_columns_sql(_LEDGER_COLUMNS)} FROM ledger_mirror "
        f"WHERE row_num IN ({placeholders}) ORDER BY row_num"
    )
    item["ledger"] = _rows(conn.execute(sql, tuple(row_nums)))


def _decode_cell(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    extra, extra_error = _decode_object(item.pop("extra_json", None), None)
    item["extra"] = extra
    if extra_error:
        item["extra_error"] = True
    return item


def _decode_clause(row: dict[str, Any]) -> dict[str, Any]:
    item = dict(row)
    year_delta, year_error = _decode_object(item.pop("year_delta_json", None), {})
    extra, extra_error = _decode_object(item.pop("extra_json", None), {})
    item["year_delta"] = year_delta
    item["extra"] = extra
    if year_error:
        item["year_delta_error"] = True
    if extra_error:
        item["extra_error"] = True
    return item


def _allowed_cell_sources(conn: sqlite3.Connection) -> list[str]:
    seen: set[str] = set()
    allowed: list[str] = []
    for row in conn.execute("SELECT source FROM cells ORDER BY source"):
        value = row[0]
        if isinstance(value, str) and value not in seen:
            seen.add(value)
            allowed.append(value)
    return allowed


@router.get("/research/assets")
def research_catalog_assets(
    kind: str | None = None,
    q: str | None = None,
    exists: str | None = None,
    limit: str | None = None,
    offset: str | None = None,
) -> dict[str, Any]:
    conn, catalog, error = _catalog_connection()
    if error is not None:
        return error
    assert conn is not None and catalog is not None
    try:
        parsed_limit, limit_error = _parse_limit(limit, _ASSETS_DEFAULT_LIMIT, _ASSETS_MAX_LIMIT)
        if limit_error is not None:
            return limit_error
        parsed_offset, offset_error = _parse_offset(offset)
        if offset_error is not None:
            return offset_error
        exists_flag, exists_error = _parse_flag(exists, "exists")
        if exists_error is not None:
            return exists_error
        q_text, q_error = _clean_text_filter(q, "q")
        if q_error is not None:
            return q_error
        kind_text, kind_error = _clean_text_filter(kind, "kind")
        if kind_error is not None:
            return kind_error

        where: list[str] = []
        params: list[Any] = []
        if kind_text is not None:
            where.append("kind = ?")
            params.append(kind_text)
        if exists_flag is not None:
            where.append("exists_on_disk = ?")
            params.append(exists_flag)
        if q_text is not None:
            pattern = _like_pattern(q_text)
            where.append("(asset_id LIKE ? ESCAPE '\\' OR path LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\')")
            params.extend([pattern, pattern, pattern])

        items = _select_rows(
            conn,
            _ASSET_COLUMNS,
            "assets",
            where,
            params,
            "asset_id",
            parsed_limit,
            parsed_offset,
        )
        return _success(catalog, items)
    except sqlite3.Error as exc:
        return _query_error(exc, catalog)
    finally:
        conn.close()


@router.get("/research/judgments")
def research_catalog_judgments(
    series: str | None = None,
    q: str | None = None,
    include_ledger: str | None = None,
    limit: str | None = None,
    offset: str | None = None,
) -> dict[str, Any]:
    conn, catalog, error = _catalog_connection()
    if error is not None:
        return error
    assert conn is not None and catalog is not None
    try:
        parsed_limit, limit_error = _parse_limit(limit, _JUDGMENTS_DEFAULT_LIMIT, _JUDGMENTS_MAX_LIMIT)
        if limit_error is not None:
            return limit_error
        parsed_offset, offset_error = _parse_offset(offset)
        if offset_error is not None:
            return offset_error
        ledger_flag, ledger_error = _parse_flag(include_ledger, "include_ledger")
        if ledger_error is not None:
            return ledger_error
        q_text, q_error = _clean_text_filter(q, "q")
        if q_error is not None:
            return q_error
        series_text, series_error = _clean_text_filter(series, "series")
        if series_error is not None:
            return series_error

        where: list[str] = []
        params: list[Any] = []
        if series_text is not None:
            where.append("series = ?")
            params.append(series_text)
        if q_text is not None:
            pattern = _like_pattern(q_text)
            where.append("(series LIKE ? ESCAPE '\\' OR verdict LIKE ? ESCAPE '\\')")
            params.extend([pattern, pattern])

        rows = _select_rows(
            conn,
            _JUDGMENT_COLUMNS,
            "judgments",
            where,
            params,
            "rowid",
            parsed_limit,
            parsed_offset,
        )
        items = [_decode_judgment(row) for row in rows]
        if ledger_flag == 1:
            for item in items:
                _add_ledger_rows(conn, item)
        return _success(catalog, items)
    except sqlite3.Error as exc:
        return _query_error(exc, catalog)
    finally:
        conn.close()


@router.get("/research/cells")
def research_catalog_cells(
    source: str | None = None,
    label_kind: str | None = None,
    axis_set: str | None = None,
    time_b: str | None = None,
    updown_q: str | None = None,
    mktcap_b: str | None = None,
    gap_b: str | None = None,
    win: str | None = None,
    limit: str | None = None,
    offset: str | None = None,
) -> dict[str, Any]:
    conn, catalog, error = _catalog_connection()
    if error is not None:
        return error
    assert conn is not None and catalog is not None
    try:
        allowed = _allowed_cell_sources(conn)
        source_text, source_error = _clean_text_filter(source, "source")
        if source_error is not None:
            return source_error
        if source_text is None or source_text not in allowed:
            return _invalid_param("source", allowed=allowed)
        parsed_limit, limit_error = _parse_limit(limit, _CELLS_DEFAULT_LIMIT, _CELLS_MAX_LIMIT)
        if limit_error is not None:
            return limit_error
        parsed_offset, offset_error = _parse_offset(offset)
        if offset_error is not None:
            return offset_error
        label_kind_text, label_kind_error = _clean_text_filter(label_kind, "label_kind")
        if label_kind_error is not None:
            return label_kind_error
        axis_set_text, axis_set_error = _clean_text_filter(axis_set, "axis_set")
        if axis_set_error is not None:
            return axis_set_error

        where: list[str] = ["source = ?"]
        params: list[Any] = [source_text]
        if label_kind_text is not None:
            where.append("label_kind = ?")
            params.append(label_kind_text)
        if axis_set_text is not None:
            where.append("axis_set = ?")
            params.append(axis_set_text)
        for param, column in _CELL_INT_FILTERS.items():
            parsed, param_error = _parse_optional_int(locals()[param], param)
            if param_error is not None:
                return param_error
            if parsed is not None:
                where.append(f"{column} = ?")
                params.append(parsed)

        rows = _select_rows(
            conn,
            _CELL_COLUMNS,
            "cells",
            where,
            params,
            "cell_id",
            parsed_limit,
            parsed_offset,
        )
        return _success(catalog, [_decode_cell(row) for row in rows], allowed=allowed)
    except sqlite3.Error as exc:
        return _query_error(exc, catalog)
    finally:
        conn.close()


@router.get("/research/clauses")
def research_catalog_clauses(
    classification: str | None = None,
    family: str | None = None,
    w5_category: str | None = None,
    clause_num: str | None = None,
) -> dict[str, Any]:
    conn, catalog, error = _catalog_connection()
    if error is not None:
        return error
    assert conn is not None and catalog is not None
    try:
        clause_id, clause_error = _parse_optional_int(clause_num, "clause_num")
        if clause_error is not None:
            return clause_error
        classification_text, classification_error = _clean_text_filter(classification, "classification")
        if classification_error is not None:
            return classification_error
        family_text, family_error = _clean_text_filter(family, "family")
        if family_error is not None:
            return family_error
        w5_text, w5_error = _clean_text_filter(w5_category, "w5_category")
        if w5_error is not None:
            return w5_error

        where: list[str] = []
        params: list[Any] = []
        if clause_id is not None:
            where.append("clause_num = ?")
            params.append(clause_id)
        if classification_text is not None:
            where.append("classification = ?")
            params.append(classification_text)
        if family_text is not None:
            where.append("family = ?")
            params.append(family_text)
        if w5_text is not None:
            where.append("w5_category = ?")
            params.append(w5_text)

        rows = _select_rows(conn, _CLAUSE_COLUMNS, "clauses", where, params, "clause_num")
        items = [_decode_clause(row) for row in rows]
        if clause_id is not None:
            return _single_success(catalog, items[0] if items else None)
        return _success(catalog, items)
    except sqlite3.Error as exc:
        return _query_error(exc, catalog)
    finally:
        conn.close()
