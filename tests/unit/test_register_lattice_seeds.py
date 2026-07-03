# -*- coding: utf-8 -*-
"""Tests for INSERT-only lattice seed registration."""

import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "ai_strategy_loop" / "scripts" / "register_lattice_seeds.py"
BUY_CODE = "buy = True\nif buy:\n    self.Buy()"
SELL_CODE = "sell = True\nif sell:\n    self.Sell()"


def _load_module():
    spec = importlib.util.spec_from_file_location("register_lattice_seeds", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_db(tmp_path):
    db_path = tmp_path / "loop_strategies.db"
    con = sqlite3.connect(str(db_path))
    con.execute('CREATE TABLE "stockbuy" ("index" TEXT PRIMARY KEY, "code" TEXT)')
    con.execute('CREATE TABLE "stocksell" ("index" TEXT PRIMARY KEY, "code" TEXT)')
    con.commit()
    con.close()
    return db_path


def _write_seeds(
    tmp_path,
    *,
    condition_id="tick_0900_small_low_momentum_breakout",
    cell_id="tick_0900_small_low",
    family="momentum_breakout",
):
    seeds = {
        "schema": "seed_lattice_seeds_v1",
        "seed_count": 1,
        "seeds": [
            {
                "condition_id": condition_id,
                "cell_id": cell_id,
                "family": family,
                "buy_code": BUY_CODE,
                "sell_code": SELL_CODE,
                "buy_sha256": _sha(BUY_CODE),
                "sell_sha256": _sha(SELL_CODE),
                "params": {"lane": "tick"},
                "created_reason": "unit test",
                "passport_md": f"passports/{cell_id}__{family}.md",
            }
        ],
    }
    path = tmp_path / "lattice_seeds.json"
    path.write_text(json.dumps(seeds, ensure_ascii=False), encoding="utf-8")
    return path


def _rows(db_path, table):
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute(f'SELECT "index", "code" FROM "{table}" ORDER BY "index"').fetchall()
    finally:
        con.close()


def test_dry_run_reports_pairs_without_db_or_ledger_changes(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    seeds = _write_seeds(tmp_path)
    pairs = tmp_path / "pairs.json"
    ledger = tmp_path / "ledger.jsonl"
    report = tmp_path / "report.json"

    code = mod.run([
        "--seeds", str(seeds),
        "--db", str(db_path),
        "--pairs-out", str(pairs),
        "--ledger-out", str(ledger),
        "--report", str(report),
    ])

    assert code == 0
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["dry_run"] is True
    assert receipt["planned_seed_count"] == 1
    assert receipt["planned_insert_count"] == 2
    assert receipt["inserted_seed_count"] == 0
    assert _rows(db_path, "stockbuy") == []
    assert not ledger.exists()
    assert json.loads(pairs.read_text(encoding="utf-8"))[0]["buy"].endswith("_B")


def test_apply_inserts_buy_sell_pairs_and_ledger(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    seeds = _write_seeds(tmp_path)
    pairs = tmp_path / "pairs.json"
    ledger = tmp_path / "ledger.jsonl"
    report = tmp_path / "report.json"

    code = mod.run([
        "--seeds", str(seeds),
        "--db", str(db_path),
        "--pairs-out", str(pairs),
        "--ledger-out", str(ledger),
        "--report", str(report),
        "--apply",
    ])

    assert code == 0
    receipt = json.loads(report.read_text(encoding="utf-8"))
    buy_name = "LAT_tick_0900_small_low_momentum_breakout_B"
    sell_name = "LAT_tick_0900_small_low_momentum_breakout_S"
    assert receipt["dry_run"] is False
    assert receipt["inserted_seed_count"] == 1
    assert Path(receipt["backup_path"]).exists()
    assert _rows(db_path, "stockbuy") == [(buy_name, BUY_CODE)]
    assert _rows(db_path, "stocksell") == [(sell_name, SELL_CODE)]
    assert json.loads(pairs.read_text(encoding="utf-8")) == [
        {"label": "tick_0900_small_low_momentum_breakout", "buy": buy_name, "sell": sell_name, "lane": "tick"}
    ]
    entry = json.loads(ledger.read_text(encoding="utf-8").strip())
    assert entry["label"] == "hypothesis_seed"
    assert entry["db_buy_name"] == buy_name
    assert entry["db_sell_name"] == sell_name


def test_apply_sanitizes_lattice_condition_id_for_db_and_filename_safety(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    seeds = _write_seeds(
        tmp_path,
        condition_id="lattice_v1:tick_0900_small_low:momentum_breakout",
    )
    pairs = tmp_path / "pairs.json"
    mapping = tmp_path / "mapping.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    report = tmp_path / "report.json"

    code = mod.run([
        "--seeds", str(seeds),
        "--db", str(db_path),
        "--pairs-out", str(pairs),
        "--mapping-out", str(mapping),
        "--ledger-out", str(ledger),
        "--report", str(report),
        "--apply",
    ])

    buy_name = "LAT_lattice_v1_tick_0900_small_low_momentum_breakout_B"
    sell_name = "LAT_lattice_v1_tick_0900_small_low_momentum_breakout_S"
    forbidden = set('<>:"/\\|?*')
    assert code == 0
    assert not any(ch in buy_name for ch in forbidden)
    assert _rows(db_path, "stockbuy") == [(buy_name, BUY_CODE)]
    assert _rows(db_path, "stocksell") == [(sell_name, SELL_CODE)]
    assert json.loads(pairs.read_text(encoding="utf-8")) == [
        {
            "label": "lattice_v1:tick_0900_small_low:momentum_breakout",
            "buy": buy_name,
            "sell": sell_name,
            "lane": "tick",
        }
    ]
    mapping_entry = json.loads(mapping.read_text(encoding="utf-8").strip())
    assert mapping_entry["legacy_buy_name"] == "LAT_lattice_v1:tick_0900_small_low:momentum_breakout_B"
    assert mapping_entry["safe_buy_name"] == buy_name
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["unsafe_legacy_name_count"] == 2
    assert receipt["mapping_out"] == str(mapping)


def test_apply_aborts_on_existing_target_name(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    seeds = _write_seeds(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute('INSERT INTO "stockbuy" VALUES (?, ?)', ("LAT_tick_0900_small_low_momentum_breakout_B", "old"))
    con.commit()
    con.close()
    report = tmp_path / "report.json"

    code = mod.run([
        "--seeds", str(seeds),
        "--db", str(db_path),
        "--pairs-out", str(tmp_path / "pairs.json"),
        "--ledger-out", str(tmp_path / "ledger.jsonl"),
        "--report", str(report),
        "--apply",
    ])

    assert code == 3
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["status"] == "collision_abort"
    assert receipt["conflicts"][0]["name"] == "LAT_tick_0900_small_low_momentum_breakout_B"
    assert _rows(db_path, "stocksell") == []
