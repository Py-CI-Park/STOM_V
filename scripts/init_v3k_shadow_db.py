from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / ".omx" / "reports"

LEARNING_DBS: dict[str, dict[str, Any]] = {
    "pattern_analysis.db": {
        "source_file": "strategy/analyzer_candle_pattern.py",
        "tables": {
            "pattern_setting": {
                "columns": ["market INTEGER NOT NULL", "analysis_period INTEGER NOT NULL", "rate_threshold INTEGER NOT NULL"],
                "primary_key": ["market"],
            },
            "{strategy_gubun}_pattern_score": {
                "columns": [
                    "code TEXT NOT NULL",
                    "pattern_name TEXT NOT NULL",
                    "avg_score REAL NOT NULL",
                    "max_score REAL NOT NULL",
                    "min_score REAL NOT NULL",
                    "std_score REAL NOT NULL",
                    "sample_count INTEGER NOT NULL",
                    "confidence_score REAL NOT NULL",
                    "setting_hash TEXT NOT NULL",
                    "last_update INTEGER NOT NULL",
                ],
                "primary_key": ["code", "pattern_name", "setting_hash", "last_update"],
            },
        },
    },
    "volume_spike.db": {
        "source_file": "strategy/analyzer_volume_spike.py",
        "tables": {
            "spike_setting": {
                "columns": ["market INTEGER NOT NULL", "is_tick INTEGER NOT NULL", "analysis_period INTEGER NOT NULL", "rate_threshold INTEGER NOT NULL"],
                "primary_key": ["market", "is_tick"],
            },
            "{strategy_gubun}_volume_spike_{tick|min}": {
                "columns": [
                    "code TEXT NOT NULL",
                    "spike_level REAL NOT NULL",
                    "avg_score REAL NOT NULL",
                    "max_score REAL NOT NULL",
                    "min_score REAL NOT NULL",
                    "std_score REAL NOT NULL",
                    "sample_count INTEGER NOT NULL",
                    "confidence_score REAL NOT NULL",
                    "setting_hash TEXT NOT NULL",
                    "last_update INTEGER NOT NULL",
                ],
                "primary_key": ["code", "spike_level", "setting_hash", "last_update"],
            },
        },
    },
    "volume_profile.db": {
        "source_file": "strategy/analyzer_volume_profile.py",
        "tables": {
            "volume_setting": {
                "columns": [
                    "market INTEGER NOT NULL",
                    "is_tick INTEGER NOT NULL",
                    "analysis_period INTEGER NOT NULL",
                    "rate_threshold REAL NOT NULL",
                    "price_range_pct REAL NOT NULL",
                ],
                "primary_key": ["market", "is_tick"],
            },
            "{strategy_gubun}_volume_score_{tick|min}": {
                "columns": [
                    "code TEXT NOT NULL",
                    "price_level REAL NOT NULL",
                    "avg_score REAL NOT NULL",
                    "upward_strength REAL NOT NULL",
                    "downward_strength REAL NOT NULL",
                    "sample_count INTEGER NOT NULL",
                    "confidence_score REAL NOT NULL",
                    "setting_hash TEXT NOT NULL",
                    "last_update INTEGER NOT NULL",
                ],
                "primary_key": ["code", "price_level", "setting_hash", "last_update"],
            },
        },
    },
    "volatility_pattern.db": {
        "source_file": "strategy/analyzer_volatility_pattern.py",
        "tables": {
            "volatility_setting": {
                "columns": ["market INTEGER NOT NULL", "is_tick INTEGER NOT NULL", "analysis_period INTEGER NOT NULL", "rate_threshold INTEGER NOT NULL"],
                "primary_key": ["market", "is_tick"],
            },
            "{strategy_gubun}_volatility_pattern_{tick|min}": {
                "columns": [
                    "code TEXT NOT NULL",
                    "volatility_level REAL NOT NULL",
                    "avg_score REAL NOT NULL",
                    "max_score REAL NOT NULL",
                    "min_score REAL NOT NULL",
                    "std_score REAL NOT NULL",
                    "sample_count INTEGER NOT NULL",
                    "confidence_score REAL NOT NULL",
                    "setting_hash TEXT NOT NULL",
                    "last_update INTEGER NOT NULL",
                ],
                "primary_key": ["code", "volatility_level", "setting_hash", "last_update"],
            },
        },
    },
    "volatility_stop_take.db": {
        "source_file": "strategy/analyzer_volatility_stop_take.py",
        "tables": {
            "volatility_stop_take_setting": {
                "columns": ["market INTEGER NOT NULL", "is_tick INTEGER NOT NULL", "analysis_period INTEGER NOT NULL"],
                "primary_key": ["market", "is_tick"],
            },
            "{strategy_gubun}_volatility_{tick|min}": {
                "columns": [
                    "code TEXT NOT NULL",
                    "volatility_level REAL NOT NULL",
                    "level_stop REAL NOT NULL",
                    "level_take REAL NOT NULL",
                    "avg_return REAL NOT NULL",
                    "max_return REAL NOT NULL",
                    "min_return REAL NOT NULL",
                    "std_return REAL NOT NULL",
                    "win_rate REAL NOT NULL",
                    "sample_count INTEGER NOT NULL",
                    "confidence_score REAL NOT NULL",
                    "setting_hash TEXT NOT NULL",
                    "last_update INTEGER NOT NULL",
                ],
                "primary_key": ["code", "volatility_level", "setting_hash", "last_update"],
            },
        },
    },
}

META_DBS: dict[str, dict[str, Any]] = {
    "v3k_meta.db": {
        "tables": {
            "v3k_feature_flags": {
                "columns": [
                    "name TEXT PRIMARY KEY",
                    "enabled INTEGER NOT NULL DEFAULT 0",
                    "updated_at TEXT",
                    "note TEXT",
                ],
                "primary_key": ["name"],
            },
            "v3k_schema_manifest": {
                "columns": [
                    "db_name TEXT NOT NULL",
                    "table_name TEXT NOT NULL",
                    "schema_hash TEXT NOT NULL",
                    "source_file TEXT NOT NULL",
                    "source_commit TEXT",
                    "last_verified_at TEXT",
                ],
                "primary_key": ["db_name", "table_name"],
            },
        },
    },
    "v3k_code_meta.db": {
        "tables": {
            "v3k_listed_shares": {
                "columns": [
                    "code TEXT NOT NULL",
                    "market TEXT NOT NULL",
                    "listed_shares INTEGER",
                    "source TEXT NOT NULL",
                    "as_of_date INTEGER NOT NULL",
                ],
                "primary_key": ["code", "market", "as_of_date"],
            },
        },
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_report_path(path: Path) -> Path:
    resolved = path if path.is_absolute() else ROOT / path
    resolved = resolved.resolve()
    reports = REPORTS_DIR.resolve()
    try:
        resolved.relative_to(reports)
    except ValueError as exc:
        raise SystemExit(f"manifest output must be under {reports}: {resolved}") from exc
    return resolved


def create_table_sql(table_name: str, table: dict[str, Any]) -> str:
    parts = list(table["columns"])
    pk = table.get("primary_key") or []
    if pk and not any("PRIMARY KEY" in col.upper() for col in parts):
        parts.append("PRIMARY KEY (" + ", ".join(pk) + ")")
    inner = ",\n    ".join(parts)
    return f"CREATE TABLE IF NOT EXISTS {table_name} (\n    {inner}\n);"


def build_manifest(shadow_dir: Path) -> dict[str, Any]:
    all_dbs = {**LEARNING_DBS, **META_DBS}
    dbs: dict[str, Any] = {}
    for db_name, db_spec in all_dbs.items():
        tables = {}
        for table_name, table in db_spec["tables"].items():
            tables[table_name] = {**table, "create_sql": create_table_sql(table_name, table)}
        dbs[db_name] = {
            "target_path": str(shadow_dir / db_name),
            "source_file": db_spec.get("source_file"),
            "tables": tables,
        }
    return {
        "generated_at": utc_now(),
        "mode": "dry-run",
        "creates_databases": False,
        "creates_directories": False,
        "shadow_dir": str(shadow_dir),
        "dbs": dbs,
        "policy": {
            "feature_flags_default_off": True,
            "backtest_date_rule": "last_update < backtest_date unless leakage safety is proven",
            "forbidden_writes": ["_database", "_database_v3k_shadow", "backup", "*.db"],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V3K shadow DB manifest generator. DESIGN-1B allows --dry-run only.")
    parser.add_argument("--dry-run", action="store_true", required=True, help="required; no DB files or directories are created")
    parser.add_argument("--shadow-dir", type=Path, default=Path("_database_v3k_shadow"))
    parser.add_argument("--manifest", type=Path, default=Path(".omx/reports/v3k-shadow-manifest.json"))
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dry_run:
        raise SystemExit("DESIGN-1B only supports --dry-run")
    output = ensure_report_path(args.manifest)
    shadow_dir = args.shadow_dir if args.shadow_dir.is_absolute() else ROOT / args.shadow_dir
    manifest = build_manifest(shadow_dir.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stdout:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"wrote dry-run shadow DB manifest: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())