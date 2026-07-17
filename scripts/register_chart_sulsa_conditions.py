"""Read-only historical preview for chart_sulsa v7 condition records.

This retired utility is not a v2 authority path.  It never writes a database,
ledger, receipt, backup, or other file.  Its only purpose is to inspect a
historical condition document against an existing strategy database.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "_database" / "strategy.db"
DEFAULT_CONDITIONS_PATH = (
    PROJECT_ROOT / "ai_strategy_loop" / "brain" / "data" / "chart_sulsa_v7_conditions.json"
)
DEFAULT_COMBOS_PATH = (
    PROJECT_ROOT / "ai_strategy_loop" / "brain" / "data" / "chart_sulsa_v7_combos.json"
)

TABLE_BY_SIDE = {"buy": "stockbuy", "sell": "stocksell"}
NAME_COLUMN = "index"
CODE_COLUMN = "전략코드"
REQUIRED_STATUS = "hypothesis_seed"
MAX_DB_NAME_LEN = 128


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def db_name_for(condition_id: str) -> str:
    return condition_id if len(condition_id) <= MAX_DB_NAME_LEN else condition_id[:MAX_DB_NAME_LEN]


def validate_documents(conditions_doc: dict, combos_doc: dict) -> list[str]:
    """Return validation problems for the historical input documents."""
    problems: list[str] = []
    conditions = conditions_doc.get("conditions")
    if not isinstance(conditions, list):
        return ["conditions must be a list"]

    ids: set[str] = set()
    for condition in conditions:
        condition_id = condition.get("id")
        code = condition.get("code")
        side = condition.get("side")
        if not isinstance(condition_id, str) or not condition_id:
            problems.append("condition has invalid id")
            continue
        if condition_id in ids:
            problems.append("duplicate condition id: %s" % condition_id)
        ids.add(condition_id)
        if side not in TABLE_BY_SIDE:
            problems.append("condition %s has invalid side: %r" % (condition_id, side))
        if not isinstance(code, str):
            problems.append("condition %s has invalid code" % condition_id)
        elif condition.get("code_sha256") != _sha256_text(code):
            problems.append("condition %s has invalid code_sha256" % condition_id)
        if condition.get("status") != REQUIRED_STATUS:
            problems.append("condition %s must have status %s" % (condition_id, REQUIRED_STATUS))

    combos = combos_doc.get("combos", [])
    if not isinstance(combos, list):
        return problems + ["combos must be a list"]
    for combo in combos:
        combo_id = combo.get("combo_id", "<unknown>")
        for ref in (combo.get("buy_condition_id"), combo.get("sell_condition_id")):
            if ref not in ids:
                problems.append("combo %s references unknown condition: %r" % (combo_id, ref))
    return problems


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open the database exclusively in SQLite read-only mode."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_existing_shas(con: sqlite3.Connection, table: str) -> dict:
    """Map stored names to all code hashes without modifying the database."""
    if table not in TABLE_BY_SIDE.values():
        raise ValueError("unexpected table: %s" % table)
    sql = 'SELECT "%s", "%s" FROM "%s"' % (NAME_COLUMN, CODE_COLUMN, table)
    result: dict = {}
    for name, code in con.execute(sql).fetchall():
        sha = _sha256_text(code) if isinstance(code, str) else ""
        result = {**result, name: result.get(name, ()) + (sha,)}
    return result


def build_plan(conditions: list, existing_by_table: dict) -> tuple:
    """Build a read-only comparison of historical records and database rows."""
    inserts: list = []
    skips: list = []
    conflicts: list = []
    for condition in conditions:
        table = TABLE_BY_SIDE[condition["side"]]
        name = db_name_for(condition["id"])
        entry = {
            "id": condition["id"],
            "db_name": name,
            "table": table,
            "code_sha256": condition["code_sha256"],
        }
        existing_shas = existing_by_table.get(table, {}).get(name)
        if existing_shas is None:
            inserts.append(entry)
        elif all(sha == condition["code_sha256"] for sha in existing_shas):
            skips.append({**entry, "reason": "identical_code_sha256"})
        else:
            conflicts.append({**entry, "existing_code_sha256": list(existing_shas)})
    return inserts, skips, conflicts


def _emit(message: str) -> None:
    sys.stdout.write(message + "\n")


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="register_chart_sulsa_conditions",
        description="NON-AUTHORITATIVE historical chart_sulsa inspection (read-only)",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--conditions", default=str(DEFAULT_CONDITIONS_PATH))
    parser.add_argument("--combos", default=str(DEFAULT_COMBOS_PATH))
    args = parser.parse_args(argv)

    conditions_doc = _load_json(Path(args.conditions))
    combos_doc = _load_json(Path(args.combos))
    problems = validate_documents(conditions_doc, combos_doc)
    if problems:
        for problem in problems:
            _emit("VALIDATION: " + problem)
        return 2

    db_path = Path(args.db)
    read_con = open_db(db_path)
    try:
        existing_by_table = {
            table: fetch_existing_shas(read_con, table)
            for table in TABLE_BY_SIDE.values()
        }
    finally:
        read_con.close()

    planned_inserts, skips, conflicts = build_plan(
        conditions_doc["conditions"], existing_by_table
    )
    _emit("mode=HISTORICAL-PREVIEW-NON-AUTHORITATIVE db=%s" % db_path)
    _emit("No database, ledger, receipt, backup, or file writes are supported.")
    for item in planned_inserts:
        _emit("historical-missing: %s -> %s" % (item["id"], item["table"]))
    for item in skips:
        _emit("historical-match: %s" % item["id"])
    for item in conflicts:
        _emit("HISTORICAL-CONFLICT(sha mismatch): %s" % item["id"])
    _emit("totals missing=%d matching=%d conflicts=%d" % (
        len(planned_inserts), len(skips), len(conflicts)
    ))
    return 3 if conflicts else 0


if __name__ == "__main__":
    sys.exit(run())
