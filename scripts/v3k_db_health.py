from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / ".omx" / "reports"
EXPECTED_DBS = [
    "v3k_meta.db",
    "v3k_code_meta.db",
    "pattern_analysis.db",
    "volume_spike.db",
    "volume_profile.db",
    "volatility_pattern.db",
    "volatility_stop_take.db",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def ensure_report_path(path: Path) -> Path:
    resolved = path if path.is_absolute() else ROOT / path
    resolved = resolved.resolve()
    reports = REPORTS_DIR.resolve()
    try:
        resolved.relative_to(reports)
    except ValueError as exc:
        raise SystemExit(f"health output must be under {reports}: {resolved}") from exc
    return resolved


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def inspect_existing_db(path: Path) -> dict[str, Any]:
    with connect_readonly(path) as con:
        tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        details = {}
        for table in tables:
            cols = [row[1] for row in con.execute(f"PRAGMA table_info('{table}')")]
            count = None
            try:
                count = con.execute(f"SELECT COUNT(*) FROM '{table}'").fetchone()[0]
            except sqlite3.DatabaseError as exc:
                count = f"error: {exc}"
            details[table] = {"columns": cols, "row_count": count}
        return {"exists": True, "path": str(path), "size": path.stat().st_size, "tables": details}


def build_report(shadow_dir: Path) -> dict[str, Any]:
    dbs: dict[str, Any] = {}
    missing = []
    for db_name in EXPECTED_DBS:
        path = shadow_dir / db_name
        if path.exists():
            dbs[db_name] = inspect_existing_db(path)
        else:
            dbs[db_name] = {"exists": False, "path": str(path)}
            missing.append(db_name)
    return {
        "generated_at": utc_now(),
        "mode": "read-only",
        "shadow_dir": str(shadow_dir),
        "shadow_dir_exists": shadow_dir.exists(),
        "ok": shadow_dir.exists() and not missing,
        "missing_dbs": missing,
        "dbs": dbs,
        "policy": {
            "no_create": True,
            "no_modify": True,
            "allowed_write_root": str(REPORTS_DIR),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only V3K DB health report. Does not create DB files.")
    parser.add_argument("--read-only", action="store_true", required=True, help="required safety flag")
    parser.add_argument("--shadow-dir", type=Path, default=Path("_database_v3k_shadow"))
    parser.add_argument("--output", type=Path, default=Path(".omx/reports/v3k-db-health.json"))
    parser.add_argument("--strict", action="store_true", help="return non-zero if shadow dir or expected DBs are missing")
    parser.add_argument("--stdout", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.read_only:
        raise SystemExit("--read-only is required")
    output = ensure_report_path(args.output)
    shadow_dir = args.shadow_dir if args.shadow_dir.is_absolute() else ROOT / args.shadow_dir
    report = build_report(shadow_dir.resolve())
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.stdout:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"wrote read-only V3K DB health report: {output}")
        if not report["ok"]:
            print("health status: missing shadow dir or expected DBs (expected during DESIGN-1B before DB creation)")
    return 1 if args.strict and not report["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())