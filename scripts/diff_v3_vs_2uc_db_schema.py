from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / ".omx" / "reports"
DEFAULT_V3_ROOT = ROOT.parent / "STOM_V.wt-3"
DEFAULT_2UC_ROOT = ROOT.parent / "STOM_V.wt-dev"
CORE_DBS = ["setting.db", "strategy.db", "tradelist.db", "code_info.db", "backtest.db"]

LEARNING_DB_MANIFEST: dict[str, dict[str, Any]] = {
    "pattern_analysis.db": {
        "source": "strategy/analyzer_candle_pattern.py",
        "setting_table": "pattern_setting",
        "score_table_pattern": "{strategy_gubun}_pattern_score",
        "primary_key": ["code", "pattern_name", "setting_hash", "last_update"],
        "date_rule": "last_update < backtest_date",
    },
    "volume_spike.db": {
        "source": "strategy/analyzer_volume_spike.py",
        "setting_table": "spike_setting",
        "score_table_pattern": "{strategy_gubun}_volume_spike_{tick|min}",
        "primary_key": ["code", "spike_level", "setting_hash", "last_update"],
        "date_rule": "last_update < backtest_date",
    },
    "volume_profile.db": {
        "source": "strategy/analyzer_volume_profile.py",
        "setting_table": "volume_setting",
        "score_table_pattern": "{strategy_gubun}_volume_score_{tick|min}",
        "primary_key": ["code", "price_level", "setting_hash", "last_update"],
        "date_rule": "last_update < backtest_date",
    },
    "volatility_pattern.db": {
        "source": "strategy/analyzer_volatility_pattern.py",
        "setting_table": "volatility_setting",
        "score_table_pattern": "{strategy_gubun}_volatility_pattern_{tick|min}",
        "primary_key": ["code", "volatility_level", "setting_hash", "last_update"],
        "date_rule": "normalize to last_update < backtest_date before V3K runtime use",
    },
    "volatility_stop_take.db": {
        "source": "strategy/analyzer_volatility_stop_take.py",
        "setting_table": "volatility_stop_take_setting",
        "score_table_pattern": "{strategy_gubun}_volatility_{tick|min}",
        "primary_key": ["code", "volatility_level", "setting_hash", "last_update"],
        "date_rule": "normalize to last_update < backtest_date before V3K runtime use",
    },
}


@dataclass(frozen=True)
class ColumnInfo:
    cid: int
    name: str
    type: str
    notnull: int
    default: Any
    pk: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_report_path(path: Path) -> Path:
    resolved = path if path.is_absolute() else ROOT / path
    resolved = resolved.resolve()
    reports = REPORTS_DIR.resolve()
    try:
        resolved.relative_to(reports)
    except ValueError as exc:
        raise SystemExit(f"output must be under {reports}: {resolved}") from exc
    return resolved


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table_schema(con: sqlite3.Connection, table_name: str) -> dict[str, Any]:
    cols = [ColumnInfo(*row).__dict__ for row in con.execute(f"PRAGMA table_info('{table_name}')")]
    indexes = []
    for row in con.execute(f"PRAGMA index_list('{table_name}')"):
        index_name = row[1]
        index_cols = [x[2] for x in con.execute(f"PRAGMA index_info('{index_name}')")]
        indexes.append({"name": index_name, "unique": bool(row[2]), "columns": index_cols})
    return {"columns": cols, "indexes": indexes}


def inspect_db(db_path: Path) -> dict[str, Any]:
    if not db_path.exists():
        return {"exists": False, "path": str(db_path)}
    with connect_readonly(db_path) as con:
        tables = [
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ]
        views = [
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
        ]
        return {
            "exists": True,
            "path": str(db_path),
            "size": db_path.stat().st_size,
            "sha256": file_sha256(db_path),
            "tables": {name: table_schema(con, name) for name in tables},
            "views": views,
        }


def summarize_diff(v3_schema: dict[str, Any], twouc_schema: dict[str, Any]) -> dict[str, Any]:
    v3_tables = set(v3_schema.get("tables", {})) if v3_schema.get("exists") else set()
    twouc_tables = set(twouc_schema.get("tables", {})) if twouc_schema.get("exists") else set()
    common = sorted(v3_tables & twouc_tables)
    table_diffs = {}
    for table in common:
        v3_cols = [c["name"] for c in v3_schema["tables"][table]["columns"]]
        twouc_cols = [c["name"] for c in twouc_schema["tables"][table]["columns"]]
        if v3_cols != twouc_cols:
            table_diffs[table] = {
                "v3_only_columns": [c for c in v3_cols if c not in twouc_cols],
                "twouc_only_columns": [c for c in twouc_cols if c not in v3_cols],
                "same_order": False,
            }
    return {
        "v3_only_tables": sorted(v3_tables - twouc_tables),
        "twouc_only_tables": sorted(twouc_tables - v3_tables),
        "common_tables": common,
        "column_diffs": table_diffs,
    }


def build_report(v3_root: Path, twouc_root: Path) -> dict[str, Any]:
    v3_db_dir = v3_root / "_database"
    twouc_db_dir = twouc_root / "_database"
    dbs = sorted(set(CORE_DBS) | set(LEARNING_DB_MANIFEST))
    schemas = {}
    diffs = {}
    for db_name in dbs:
        v3_schema = inspect_db(v3_db_dir / db_name)
        twouc_schema = inspect_db(twouc_db_dir / db_name)
        schemas[db_name] = {"v3": v3_schema, "twouc": twouc_schema}
        diffs[db_name] = summarize_diff(v3_schema, twouc_schema)
    return {
        "generated_at": utc_now(),
        "mode": "read-only",
        "v3_root": str(v3_root),
        "twouc_root": str(twouc_root),
        "core_dbs": CORE_DBS,
        "learning_db_manifest": LEARNING_DB_MANIFEST,
        "schemas": schemas,
        "diffs": diffs,
        "policy": {
            "kiwoom_core_db_preserved": True,
            "forbidden_writes": ["_database", "_database_v3k_shadow", "backup", "*.db"],
            "allowed_write_root": str(REPORTS_DIR),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only V3 vs 2U_C DB schema diff for V3K-DESIGN-1B.")
    parser.add_argument("--v3-root", type=Path, default=DEFAULT_V3_ROOT)
    parser.add_argument("--twouc-root", type=Path, default=DEFAULT_2UC_ROOT)
    parser.add_argument("--output", type=Path, default=Path(".omx/reports/v3k-db-schema-diff.json"))
    parser.add_argument("--stdout", action="store_true", help="also print report JSON to stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = ensure_report_path(args.output)
    report = build_report(args.v3_root.resolve(), args.twouc_root.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"wrote read-only schema diff report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())