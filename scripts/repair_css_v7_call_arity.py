#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

# How to run
#   PYTHONUTF8=1 python scripts/repair_css_v7_call_arity.py \
#     --pairs-in artifacts/chart_sulsa_validation_20260702/pairs_unique.json \
#     --out-dir artifacts/chart_sulsa_validation_20260702 \
#     --report artifacts/chart_sulsa_validation_20260702/css_v7_fixcall_insert_receipt.json \
#     --apply

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


REPO = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO / "ai_strategy_loop" / "state" / "loop_strategies.db"
DEFAULT_PAIRS = REPO / "artifacts" / "chart_sulsa_validation_20260702" / "pairs_unique.json"
DEFAULT_OUT_DIR = REPO / "artifacts" / "chart_sulsa_validation_20260702"
DEFAULT_REPORT = DEFAULT_OUT_DIR / "css_v7_fixcall_insert_receipt.json"
BUY_TABLE = "stockbuy"
SELL_TABLE = "stocksell"
INDEX_COLUMN = "index"
FIX_SUFFIX = "_FIXCALL"


@dataclass(frozen=True, slots=True)
class OrderCallViolation:
    method: str
    line: int
    arg_count: int


@dataclass(frozen=True, slots=True)
class VariantPlan:
    table: str
    source_name: str
    target_name: str
    source_sha256: str
    target_sha256: str
    fixed_code: str
    invalid_call_count: int


class RepairError(RuntimeError):
    """Expected repair preparation failure."""


class _OrderCallVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.violations: list[OrderCallViolation] = []

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in {"Buy", "Sell"}
            and isinstance(func.value, ast.Name)
            and func.value.id == "self"
            and len(node.args) > 0
        ):
            self.violations.append(OrderCallViolation(func.attr, node.lineno, len(node.args)))
        self.generic_visit(node)


def find_order_call_arity_violations(code: str) -> list[OrderCallViolation]:
    tree = ast.parse(code)
    visitor = _OrderCallVisitor()
    visitor.visit(tree)
    return visitor.violations


def normalize_order_calls(code: str) -> str:
    fixed = re.sub(r"self\.Buy\([^\n)]*\)", "self.Buy()", code)
    return re.sub(r"self\.Sell\([^\n)]*\)", "self.Sell()", fixed)


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def code_column(con: sqlite3.Connection, table: str) -> str:
    columns = [str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    for column in columns:
        if column != INDEX_COLUMN:
            return column
    raise RepairError(f"{table}: code column not found")


def read_code(con: sqlite3.Connection, table: str, name: str) -> str | None:
    column = quote_ident(code_column(con, table))
    row = con.execute(f"SELECT {column} FROM {table} WHERE [index]=?", (name,)).fetchone()
    return None if row is None else str(row[0])


def load_pairs(path: Path) -> list[dict[str, str]]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        raise RepairError("pairs JSON must be a list")
    return [dict(row) for row in loaded]


def build_variant(con: sqlite3.Connection, table: str, source_name: str) -> VariantPlan | None:
    source_code = read_code(con, table, source_name)
    if source_code is None:
        raise RepairError(f"missing strategy row: {table}/{source_name}")
    violations = find_order_call_arity_violations(source_code)
    if not violations:
        return None
    target_name = source_name + FIX_SUFFIX
    fixed_code = normalize_order_calls(source_code)
    return VariantPlan(
        table=table,
        source_name=source_name,
        target_name=target_name,
        source_sha256=sha_text(source_code),
        target_sha256=sha_text(fixed_code),
        fixed_code=fixed_code,
        invalid_call_count=len(violations),
    )


def unique_variant_plans(con: sqlite3.Connection, pairs: list[dict[str, str]]) -> list[VariantPlan]:
    plans: dict[tuple[str, str], VariantPlan] = {}
    for pair in pairs:
        for table, key in ((BUY_TABLE, "buy"), (SELL_TABLE, "sell")):
            plan = build_variant(con, table, pair[key])
            if plan is not None:
                plans[(table, pair[key])] = plan
    return sorted(plans.values(), key=lambda item: (item.table, item.source_name))


def collision_report(con: sqlite3.Connection, plans: list[VariantPlan]) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for plan in plans:
        existing = read_code(con, plan.table, plan.target_name)
        if existing is not None and sha_text(existing) != plan.target_sha256:
            conflicts.append({"table": plan.table, "name": plan.target_name})
    return conflicts


def insertable_plans(con: sqlite3.Connection, plans: list[VariantPlan]) -> list[VariantPlan]:
    result: list[VariantPlan] = []
    for plan in plans:
        existing = read_code(con, plan.table, plan.target_name)
        if existing is None:
            result.append(plan)
    return result


def repaired_pairs(pairs: list[dict[str, str]], plans: list[VariantPlan]) -> list[dict[str, str]]:
    mapping = {plan.source_name: plan.target_name for plan in plans}
    fixed: list[dict[str, str]] = []
    for pair in pairs:
        row = dict(pair)
        row["source_buy"] = pair["buy"]
        row["source_sell"] = pair["sell"]
        row["buy"] = mapping.get(pair["buy"], pair["buy"])
        row["sell"] = mapping.get(pair["sell"], pair["sell"])
        row["repair_version"] = "fixcall_v1"
        fixed.append(row)
    return fixed


def write_pair_files(out_dir: Path, pairs: list[dict[str, str]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pairs_unique_fixcall.json").write_text(
        json.dumps(pairs, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for lane in ("tick", "min"):
        lane_rows = [
            {"label": row["label"], "buy": row["buy"], "sell": row["sell"]}
            for row in pairs
            if row.get("lane") == lane
        ]
        (out_dir / f"pairs_{lane}_fixcall.json").write_text(
            json.dumps(lane_rows, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def make_backup(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = db_path.with_name(db_path.name + f".bak.css_v7_fixcall_{stamp}")
    shutil.copy2(db_path, backup)
    return backup


def apply_inserts(con: sqlite3.Connection, plans: list[VariantPlan]) -> None:
    for plan in plans:
        column = quote_ident(code_column(con, plan.table))
        con.execute(
            f"INSERT INTO {plan.table} ([index], {column}) VALUES (?, ?)",
            (plan.target_name, plan.fixed_code),
        )
    con.commit()


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pairs-in", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    pairs = load_pairs(args.pairs_in)
    backup_path: Path | None = None
    with closing(sqlite3.connect(args.db)) as con:
        plans = unique_variant_plans(con, pairs)
        conflicts = collision_report(con, plans)
        write_pair_files(args.out_dir, repaired_pairs(pairs, plans))
        if conflicts:
            receipt = build_receipt(args, plans, [], conflicts, None, pairs)
            write_receipt(args.report, receipt, "collision_abort")
            return 3
        to_insert = insertable_plans(con, plans)
        if args.apply and to_insert:
            backup_path = make_backup(args.db)
            apply_inserts(con, to_insert)
        inserted = to_insert if args.apply else []
        receipt = build_receipt(args, plans, inserted, [], backup_path, pairs)
        write_receipt(args.report, receipt, "inserted" if args.apply else "dry_run_ok")
    sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return 0


def build_receipt(
    args: argparse.Namespace,
    plans: list[VariantPlan],
    inserted: list[VariantPlan],
    conflicts: list[dict[str, str]],
    backup_path: Path | None,
    pairs: list[dict[str, str]],
) -> dict[str, str | int | bool | list[dict[str, str]] | None]:
    invalid_after = 0
    for plan in plans:
        invalid_after += len(find_order_call_arity_violations(plan.fixed_code))
    return {
        "schema_version": 1,
        "dry_run": not args.apply,
        "db_path": str(args.db),
        "pairs_in": str(args.pairs_in),
        "pairs_unique_fixcall": str(args.out_dir / "pairs_unique_fixcall.json"),
        "backup_path": None if backup_path is None else str(backup_path),
        "planned_insert_count": len(plans),
        "inserted_count": len(inserted),
        "pair_count": len(pairs),
        "conflicts": conflicts,
        "invalid_runtime_call_count_before_repair": sum(plan.invalid_call_count for plan in plans),
        "invalid_runtime_call_count_after_repair": invalid_after,
    }


def write_receipt(path: Path, receipt: dict[str, str | int | bool | list[dict[str, str]] | None], status: str) -> None:
    enriched = {"status": status, **receipt}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(run())
