#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# How to run
# 1. Dry-run static/pair/mirror prep:
#      PYTHONUTF8=1 python artifacts/chart_sulsa_validation_20260702/mirror_insert_css_v7.py --write-pairs --static-report artifacts/chart_sulsa_validation_20260702/static_gate_report.json --report artifacts/chart_sulsa_validation_20260702/mirror_insert_dryrun.json
# 2. Apply INSERT-only mirror:
#      PYTHONUTF8=1 python artifacts/chart_sulsa_validation_20260702/mirror_insert_css_v7.py --apply --report artifacts/chart_sulsa_validation_20260702/mirror_insert_receipt.json

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ai_strategy_loop.brain.token_check import check_tokens  # noqa: E402
from ai_strategy_loop.brain.variable_scope import check_variable_scope  # noqa: E402

SOURCE_DB = REPO / "_database" / "strategy.db"
LOOP_DB = REPO / "ai_strategy_loop" / "state" / "loop_strategies.db"
ARTIFACT_DIR = REPO / "artifacts" / "chart_sulsa_validation_20260702"
PROVENANCE = REPO / "docs" / "research" / "condition_research" / "chart_sulsa" / "provenance_registry.jsonl"
PASSPORT_DIR = REPO / "docs" / "research" / "condition_research" / "condition_passports" / "chart_sulsa"
COMBOS = REPO / "ai_strategy_loop" / "brain" / "data" / "chart_sulsa_v7_combos.json"
ORDER_RUNTIME_NAMES = frozenset({"매수수량", "매도수량", "강제청산"})


class PlanCError(RuntimeError):
    """Expected Plan C preparation failure."""


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def code_column(cur: sqlite3.Cursor, table: str) -> str:
    columns = [str(row[1]) for row in cur.execute(f"pragma table_info({table})").fetchall()]
    for column in columns:
        if column != "index":
            return column
    raise PlanCError(f"{table}: code column not found")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def row_code(cur: sqlite3.Cursor, table: str, name: str) -> str | None:
    column = quote_ident(code_column(cur, table))
    row = cur.execute(f"select {column} from {table} where [index]=?", (name,)).fetchone()
    return None if row is None else str(row[0])


def validate_code(code: str, condition_id: str, table: str) -> list[str]:
    errors: list[str] = []
    try:
        compile(code, "<css_v7>", "exec")
    except SyntaxError as exc:
        errors.append(f"compile:{exc}")
    ok, token_msg = check_tokens(code)
    if not ok:
        errors.append(f"token:{token_msg}")
    timeframe = "tick" if "_TICK_" in condition_id else "min"
    kind = "buy" if table == "stockbuy" else "sell"
    ok, missing = check_variable_scope(code, timeframe, kind)
    scoped_missing = [name for name in missing if name not in ORDER_RUNTIME_NAMES]
    if not ok and scoped_missing:
        errors.append(f"scope:{','.join(scoped_missing)}")
    if timeframe == "tick":
        has_guard = "93000" in code and (kind == "sell" or "90000" in code)
        if not has_guard:
            errors.append("tick_window_guard_missing")
    return errors


def static_gate(source_db: Path) -> dict[str, Any]:
    rows = [r for r in load_jsonl(PROVENANCE) if r.get("entry_type") == "condition"]
    entries: list[dict[str, Any]] = []
    bad = 0
    with sqlite3.connect(source_db) as con:
        cur = con.cursor()
        for row in rows:
            table = str(row["db_table"])
            name = str(row["db_name"])
            code = row_code(cur, table, name)
            errors = ["missing_db_row"] if code is None else []
            actual_sha = None if code is None else sha_text(code)
            if code is not None:
                if actual_sha != row.get("code_sha256"):
                    errors.append("sha_mismatch")
                errors.extend(validate_code(code, str(row["id"]), table))
            if errors:
                bad += 1
            entries.append(
                {
                    "id": row["id"],
                    "table": table,
                    "db_name": name,
                    "expected_sha256": row.get("code_sha256"),
                    "actual_sha256": actual_sha,
                    "errors": errors,
                }
            )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_db": str(source_db),
        "checked": len(entries),
        "bad": bad,
        "scope_order_runtime_allowlist": sorted(ORDER_RUNTIME_NAMES),
        "entries": entries,
    }


def passport_field(text: str, field: str) -> str:
    match = re.search(rf"\|\s*{re.escape(field)}\s*\|\s*`([^`]+)`\s*\|", text)
    if match is None:
        raise PlanCError(f"passport field missing: {field}")
    return match.group(1)


def build_pairs() -> list[dict[str, Any]]:
    pairs: dict[tuple[str, str, str], dict[str, Any]] = {}
    for passport in sorted(PASSPORT_DIR.glob("css_v7_*.md")):
        text = passport.read_text(encoding="utf-8")
        condition_id = passport_field(text, "condition_id")
        lane = passport_field(text, "lane")
        buy = passport_field(text, "buy_strategy_id")
        sell = passport_field(text, "sell_strategy_id")
        key = (lane, buy, sell)
        if key not in pairs:
            pairs[key] = {
                "label": condition_id,
                "buy": buy,
                "sell": sell,
                "combo_priority": None,
                "combo_id": None,
                "lane": lane,
                "passport": str(passport.relative_to(REPO)),
                "source_condition_ids": [],
            }
        pairs[key]["source_condition_ids"].append(condition_id)
    combos = json.loads(COMBOS.read_text(encoding="utf-8"))["combos"]
    for combo in combos:
        key = (combo["lane"], combo["buy_condition_id"], combo["sell_condition_id"])
        if key not in pairs:
            raise PlanCError(f"combo pair missing from passports: {combo['combo_id']}")
        pairs[key]["combo_priority"] = combo["priority"]
        pairs[key]["combo_id"] = combo["combo_id"]
        pairs[key]["label"] = combo["combo_id"]
    def sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
        priority = row["combo_priority"]
        first = 0 if priority is not None else 1
        master = 0 if "_MASTER_" in row["buy"] or "_MASTER_" in row["sell"] else 1
        opt = 0 if "_OPT_" in row["buy"] or "_OPT_" in row["sell"] else 1
        return (first, master * 10 + opt, str(row["label"]))
    return sorted(pairs.values(), key=sort_key)


def write_pairs(pairs: list[dict[str, Any]], artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    all_path = artifact_dir / "pairs_unique.json"
    all_path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lane in ("tick", "min"):
        lane_rows = [{"label": p["label"], "buy": p["buy"], "sell": p["sell"]} for p in pairs if p["lane"] == lane]
        (artifact_dir / f"pairs_{lane}.json").write_text(
            json.dumps(lane_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def source_rows(source_db: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    with sqlite3.connect(source_db) as con:
        cur = con.cursor()
        for table in ("stockbuy", "stocksell"):
            column = quote_ident(code_column(cur, table))
            for name, code in cur.execute(f"select [index], {column} from {table} where [index] like ? order by [index]", ("CSS_V7_%",)):
                items.append({"table": table, "name": str(name), "code": str(code), "sha256": sha_text(str(code))})
    return items


def mirror(source_db: Path, loop_db: Path, apply: bool, report: Path) -> dict[str, Any]:
    rows = source_rows(source_db)
    backup_path: Path | None = None
    collisions: list[dict[str, str]] = []
    before_counts: dict[str, int] = {}
    with sqlite3.connect(loop_db) as con:
        cur = con.cursor()
        for table in ("stockbuy", "stocksell"):
            before_counts[table] = int(cur.execute(f"select count(*) from {table}").fetchone()[0])
        for row in rows:
            hit = cur.execute(f"select 1 from {row['table']} where [index]=?", (row["name"],)).fetchone()
            if hit is not None:
                collisions.append({"table": row["table"], "name": row["name"]})
        if collisions:
            return {"schema_version": 1, "dry_run": not apply, "status": "collision_abort", "source_rows": len(rows), "collisions": collisions, "before_counts": before_counts}
        if apply:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_path = loop_db.with_name(loop_db.name + f".bak.css_v7_{stamp}")
            shutil.copy2(loop_db, backup_path)
            for row in rows:
                column = quote_ident(code_column(cur, row["table"]))
                cur.execute(f"insert into {row['table']} ([index], {column}) values (?, ?)", (row["name"], row["code"]))
            con.commit()
    after_bad = 0
    after_counts: dict[str, int] = {}
    with sqlite3.connect(loop_db) as con:
        cur = con.cursor()
        for table in ("stockbuy", "stocksell"):
            after_counts[table] = int(cur.execute(f"select count(*) from {table}").fetchone()[0])
        if apply:
            for row in rows:
                code = row_code(cur, row["table"], row["name"])
                if code is None or sha_text(code) != row["sha256"]:
                    after_bad += 1
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": not apply,
        "status": "inserted" if apply else "dry_run_ok",
        "source_db": str(source_db),
        "loop_db": str(loop_db),
        "source_rows": len(rows),
        "inserted_rows": len(rows) if apply else 0,
        "collisions": [],
        "before_counts": before_counts,
        "after_counts": after_counts,
        "post_insert_sha_bad": after_bad,
        "backup_path": None if backup_path is None else str(backup_path),
        "restore_command": None if backup_path is None else f"Copy-Item -LiteralPath {backup_path} -Destination {loop_db} -Force",
        "sql_policy": "INSERT-only; no UPDATE/DELETE used",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-db", type=Path, default=SOURCE_DB)
    parser.add_argument("--loop-db", type=Path, default=LOOP_DB)
    parser.add_argument("--artifact-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--report", type=Path, default=ARTIFACT_DIR / "mirror_insert_dryrun.json")
    parser.add_argument("--static-report", type=Path, default=None)
    parser.add_argument("--write-pairs", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    if args.static_report is not None:
        args.static_report.write_text(json.dumps(static_gate(args.source_db), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_pairs:
        write_pairs(build_pairs(), args.artifact_dir)
    receipt = mirror(args.source_db, args.loop_db, args.apply, args.report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return 0 if receipt["status"] in {"dry_run_ok", "inserted"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
