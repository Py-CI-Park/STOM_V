from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from init_v3k_shadow_db import (
    LEARNING_DBS,
    META_DBS,
    ROOT,
    compute_schema_hash,
    create_table_sql,
)

REPORTS_DIR = ROOT / ".omx" / "reports"
EXPECTED_BRANCH = "STOM_Version_2U_C"
BRANCH_BYPASS_ENV = "V3K_PHASE_A_BRANCH_BYPASS"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+", value):
        raise ValueError(f"unsafe SQL identifier: {value!r}")
    return value


def ensure_shadow_dir(path: Path) -> Path:
    resolved = (path if path.is_absolute() else ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise SystemExit(f"shadow dir must stay under {ROOT}: {resolved}") from exc
    if resolved.name != "_database_v3k_shadow":
        raise SystemExit(f"shadow dir must be named _database_v3k_shadow: {resolved}")
    if resolved == (ROOT / "_database").resolve():
        raise SystemExit("refusing to apply V3K shadow schema to operational _database")
    return resolved


def current_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def current_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def enforce_branch_guard() -> None:
    if os.environ.get(BRANCH_BYPASS_ENV) == "1":
        return
    branch = current_branch()
    if branch != EXPECTED_BRANCH:
        raise SystemExit(
            f"V3K Phase A apply is allowed only on {EXPECTED_BRANCH}; "
            f"current branch={branch!r}. Set {BRANCH_BYPASS_ENV}=1 only for CI/read-only rehearsal."
        )


def ensure_report_path(path: Path) -> Path:
    resolved = path if path.is_absolute() else ROOT / path
    resolved = resolved.resolve()
    reports = REPORTS_DIR.resolve()
    try:
        resolved.relative_to(reports)
    except ValueError as exc:
        raise SystemExit(f"apply report output must be under {reports}: {resolved}") from exc
    return resolved


def expanded_table_names(template: str, strategy_gubun: str) -> tuple[str, ...]:
    safe_strategy = safe_identifier(strategy_gubun)
    name = template.replace("{strategy_gubun}", safe_strategy)
    if "{tick|min}" in name:
        return (name.replace("{tick|min}", "tick"), name.replace("{tick|min}", "min"))
    if "{timeframe}" in name:
        return (name.replace("{timeframe}", "tick"), name.replace("{timeframe}", "min"))
    if "{" in name or "}" in name:
        raise ValueError(f"unexpanded table placeholder: {template!r}")
    return (name,)


def iter_db_specs() -> Iterable[tuple[str, dict[str, Any]]]:
    yield from {**LEARNING_DBS, **META_DBS}.items()


def expected_db_names() -> tuple[str, ...]:
    return tuple(db_name for db_name, _ in iter_db_specs())


def create_schema_manifest_table(con: sqlite3.Connection) -> None:
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS v3k_schema_manifest (
            db_name TEXT NOT NULL,
            table_name TEXT NOT NULL,
            schema_hash TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_commit TEXT,
            last_verified_at TEXT,
            PRIMARY KEY (db_name, table_name)
        )
        """,
    )


def apply_shadow_schema(
    shadow_dir: Path,
    *,
    strategy_gubun: str,
    allow_existing: bool,
) -> dict[str, Any]:
    existing = [db_name for db_name in expected_db_names() if (shadow_dir / db_name).exists()]
    if existing and not allow_existing:
        raise SystemExit(
            "shadow DB already exists; rerun with --allow-existing after confirming idempotency: "
            + ", ".join(existing)
        )

    shadow_dir.mkdir(parents=True, exist_ok=True)
    source_commit = current_commit()
    stamped_at = utc_now()
    manifest_rows: list[dict[str, Any]] = []
    db_reports: dict[str, Any] = {}

    for db_name, db_spec in iter_db_specs():
        db_path = shadow_dir / db_name
        table_reports = {}
        with sqlite3.connect(db_path) as con:
            for table_template, table in db_spec["tables"].items():
                for table_name in expanded_table_names(table_template, strategy_gubun):
                    con.executescript(create_table_sql(table_name, table))
                    schema_hash = compute_schema_hash(table_name, table)
                    table_reports[table_name] = {
                        "schema_hash": schema_hash,
                        "source_file": db_spec.get("source_file"),
                    }
                    manifest_rows.append(
                        {
                            "db_name": db_name,
                            "table_name": table_name,
                            "schema_hash": schema_hash,
                            "source_file": db_spec.get("source_file") or "scripts/init_v3k_shadow_db.py",
                            "source_commit": source_commit,
                            "last_verified_at": stamped_at,
                        }
                    )

            con.commit()
        db_reports[db_name] = {
            "path": str(db_path),
            "tables": table_reports,
        }

    with sqlite3.connect(shadow_dir / "v3k_meta.db") as con:
        create_schema_manifest_table(con)
        con.executemany(
            """
            INSERT OR REPLACE INTO v3k_schema_manifest
            (db_name, table_name, schema_hash, source_file, source_commit, last_verified_at)
            VALUES (:db_name, :table_name, :schema_hash, :source_file, :source_commit, :last_verified_at)
            """,
            manifest_rows,
        )
        con.commit()

    return {
        "generated_at": stamped_at,
        "mode": "apply",
        "shadow_dir": str(shadow_dir),
        "strategy_gubun": strategy_gubun,
        "expected_dbs": list(expected_db_names()),
        "created_or_verified_dbs": db_reports,
        "schema_manifest_rows": len(manifest_rows),
        "policy": {
            "operational_database_untouched": True,
            "feature_flag_rows_inserted": False,
            "listed_share_rows_inserted": False,
            "ls_direct_dependency": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Apply V3K Phase A shadow DB DDL only. "
            "Phase A creates _database_v3k_shadow and never writes operational _database."
        ),
    )
    parser.add_argument("--apply", action="store_true", required=True, help="required safety flag")
    parser.add_argument("--shadow-dir", type=Path, default=Path("_database_v3k_shadow"))
    parser.add_argument(
        "--strategy-gubun",
        default="stock",
        help="Phase A limited table expansion token. Phase B may redesign this signature.",
    )
    parser.add_argument("--allow-existing", action="store_true", help="allow idempotent re-application")
    parser.add_argument("--report", type=Path, default=Path(".omx/reports/v3k-shadow-apply-report.json"))
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.apply:
        raise SystemExit("--apply is required")
    enforce_branch_guard()
    shadow_dir = ensure_shadow_dir(args.shadow_dir)
    report_path = ensure_report_path(args.report)
    report = apply_shadow_schema(
        shadow_dir,
        strategy_gubun=args.strategy_gubun,
        allow_existing=args.allow_existing,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"applied V3K shadow DB rehearsal schema: {shadow_dir}")
        print(f"wrote apply report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
