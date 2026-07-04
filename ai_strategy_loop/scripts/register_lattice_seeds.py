#!/usr/bin/env python
"""Register lattice seeds into loop_strategies.db with INSERT-only semantics."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ai_strategy_loop.scripts.lattice_strategy_names import (
    legacy_names,
    mapping_entry,
    sanitize_strategy_component,
    unsafe_legacy_name_count,
    unsafe_target_name_count,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SEEDS = ROOT / "docs" / "research" / "condition_research" / "generated_conditions" / "lattice" / "lattice_seeds.json"
DEFAULT_DB = ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db"
DEFAULT_RUN_DIR = ROOT / "docs" / "research" / "condition_research" / "research_runs" / "seed_lattice_20260702"
DEFAULT_PAIRS = DEFAULT_RUN_DIR / "pairs_all.json"
DEFAULT_LEDGER = DEFAULT_RUN_DIR / "provenance_lattice_register.jsonl"
DEFAULT_MAPPING = DEFAULT_RUN_DIR / "lattice_strategy_name_mapping.jsonl"
DEFAULT_REPORT = DEFAULT_RUN_DIR / "register_lattice_seeds_receipt.json"
SEEDS_SCHEMA = "seed_lattice_seeds_v1"
BUY_TABLE = "stockbuy"
SELL_TABLE = "stocksell"
INDEX_COLUMN = "index"


class RegisterError(RuntimeError):
    """Expected registration failure."""


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def code_column(con: sqlite3.Connection, table: str) -> str:
    columns = [str(row[1]) for row in con.execute(f"PRAGMA table_info({quote_ident(table)})")]
    for column in columns:
        if column != INDEX_COLUMN:
            return column
    raise RegisterError(f"{table}: code column not found")


def row_exists(con: sqlite3.Connection, table: str, name: str) -> bool:
    row = con.execute(f"SELECT 1 FROM {quote_ident(table)} WHERE [index]=?", (name,)).fetchone()
    return row is not None


def load_seeds(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SEEDS_SCHEMA:
        raise RegisterError(f"seeds schema mismatch: {path}")
    seeds = data.get("seeds")
    if not isinstance(seeds, list):
        raise RegisterError(f"seeds list missing: {path}")
    checked: list[dict[str, Any]] = []
    for raw in seeds:
        seed = dict(raw)
        for key in ("condition_id", "cell_id", "family", "buy_code", "sell_code", "buy_sha256", "sell_sha256"):
            if seed.get(key) is None:
                raise RegisterError(f"seed missing {key}: {seed.get('condition_id')}")
        if sha_text(str(seed["buy_code"])) != seed["buy_sha256"]:
            raise RegisterError(f"buy sha mismatch: {seed['condition_id']}")
        if sha_text(str(seed["sell_code"])) != seed["sell_sha256"]:
            raise RegisterError(f"sell sha mismatch: {seed['condition_id']}")
        checked.append(seed)
    return checked


def pair_for_seed(seed: Mapping[str, Any]) -> dict[str, str]:
    condition_id = str(seed["condition_id"])
    safe_condition_id = sanitize_strategy_component(condition_id)
    cell_id = str(seed["cell_id"])
    lane = cell_id.split("_", 1)[0] if "_" in cell_id else cell_id
    return {
        "label": condition_id,
        "buy": f"LAT_{safe_condition_id}_B",
        "sell": f"LAT_{safe_condition_id}_S",
        "lane": lane,
    }


def find_conflicts(con: sqlite3.Connection, pairs: list[dict[str, str]]) -> list[dict[str, str]]:
    conflicts: list[dict[str, str]] = []
    for pair in pairs:
        for table, key in ((BUY_TABLE, "buy"), (SELL_TABLE, "sell")):
            if row_exists(con, table, pair[key]):
                conflicts.append({"table": table, "name": pair[key]})
    return conflicts


def write_pairs(path: Path, pairs: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    by_lane: dict[str, list[dict[str, str]]] = {"tick": [], "min": []}
    for pair in pairs:
        lane = pair.get("lane")
        if lane in by_lane:
            by_lane[lane].append({"label": pair["label"], "buy": pair["buy"], "sell": pair["sell"]})
    for lane, lane_pairs in by_lane.items():
        lane_path = path.with_name(f"pairs_{lane}.json")
        lane_path.write_text(json.dumps(lane_pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_backup(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = db_path.with_name(db_path.name + f".bak.lattice_{stamp}")
    shutil.copy2(db_path, backup)
    return backup


def insert_seed_rows(con: sqlite3.Connection, seeds: list[dict[str, Any]], pairs: list[dict[str, str]]) -> None:
    buy_column = quote_ident(code_column(con, BUY_TABLE))
    sell_column = quote_ident(code_column(con, SELL_TABLE))
    for seed, pair in zip(seeds, pairs):
        con.execute(
            f"INSERT INTO {quote_ident(BUY_TABLE)} ([index], {buy_column}) VALUES (?, ?)",
            (pair["buy"], str(seed["buy_code"])),
        )
        con.execute(
            f"INSERT INTO {quote_ident(SELL_TABLE)} ([index], {sell_column}) VALUES (?, ?)",
            (pair["sell"], str(seed["sell_code"])),
        )
    con.commit()


def ledger_entry(seed: Mapping[str, Any], pair: Mapping[str, str], source_doc: Path) -> dict[str, Any]:
    legacy_buy_name, legacy_sell_name = legacy_names(str(seed["condition_id"]))
    return {
        "condition_id": seed["condition_id"],
        "cell_id": seed["cell_id"],
        "family": seed["family"],
        "buy_sha256": seed["buy_sha256"],
        "sell_sha256": seed["sell_sha256"],
        "legacy_buy_name": legacy_buy_name,
        "legacy_sell_name": legacy_sell_name,
        "db_buy_name": pair["buy"],
        "db_sell_name": pair["sell"],
        "name_style": "filename_safe_v2",
        "source_doc": str(source_doc),
        "source_schema": SEEDS_SCHEMA,
        "passport_md": seed.get("passport_md"),
        "params": seed.get("params", {}),
        "created_reason": seed.get("created_reason"),
        "label": "hypothesis_seed",
    }


def write_ledger(path: Path, seeds: list[dict[str, Any]], pairs: list[dict[str, str]], source_doc: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for seed, pair in zip(seeds, pairs):
            fh.write(json.dumps(ledger_entry(seed, pair, source_doc), ensure_ascii=False) + "\n")


def write_mapping_ledger(path: Path, seeds: list[dict[str, Any]], pairs: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(mapping_entry(seed, pair), ensure_ascii=False) for seed, pair in zip(seeds, pairs)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def write_report(path: Path, receipt: Mapping[str, Any], status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": status, **dict(receipt)}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_receipt(
    args: argparse.Namespace,
    seeds: list[dict[str, Any]],
    pairs: list[dict[str, str]],
    conflicts: list[dict[str, str]],
    backup: Path | None,
    inserted: bool,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "dry_run": not args.apply,
        "seeds": str(args.seeds),
        "db": str(args.db),
        "pairs_out": str(args.pairs_out),
        "ledger_out": str(args.ledger_out),
        "mapping_out": str(args.mapping_out),
        "backup_path": None if backup is None else str(backup),
        "planned_seed_count": len(seeds),
        "planned_insert_count": len(pairs) * 2,
        "inserted_seed_count": len(seeds) if inserted else 0,
        "inserted_row_count": len(pairs) * 2 if inserted else 0,
        "unsafe_legacy_name_count": unsafe_legacy_name_count(seeds),
        "unsafe_target_name_count": unsafe_target_name_count(pairs),
        "name_style": "filename_safe_v2",
        "conflicts": conflicts,
    }


def run(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=Path, default=DEFAULT_SEEDS)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--pairs-out", type=Path, default=DEFAULT_PAIRS)
    parser.add_argument("--ledger-out", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--mapping-out", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        seeds = load_seeds(args.seeds)
        pairs = [pair_for_seed(seed) for seed in seeds]
        backup: Path | None = None
        with closing(sqlite3.connect(args.db)) as con:
            conflicts = find_conflicts(con, pairs)
            if conflicts:
                receipt = build_receipt(args, seeds, pairs, conflicts, None, False)
                write_report(args.report, receipt, "collision_abort")
                sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
                return 3
            write_pairs(args.pairs_out, pairs)
            write_mapping_ledger(args.mapping_out, seeds, pairs)
            if args.apply:
                backup = make_backup(args.db)
                insert_seed_rows(con, seeds, pairs)
                write_ledger(args.ledger_out, seeds, pairs, args.seeds)
            receipt = build_receipt(args, seeds, pairs, [], backup, args.apply)
            write_report(args.report, receipt, "inserted" if args.apply else "dry_run_ok")
            sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
            return 0
    except (RegisterError, ValueError) as exc:
        receipt = {"schema_version": 1, "dry_run": not args.apply, "error": str(exc)}
        write_report(args.report, receipt, "error")
        sys.stdout.write(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(run())
