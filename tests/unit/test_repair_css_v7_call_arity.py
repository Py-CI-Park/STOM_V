# -*- coding: utf-8 -*-
"""Tests for CSS_V7 Buy/Sell call-arity repair."""

import importlib.util
import json
import sqlite3
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "repair_css_v7_call_arity.py"
BAD_BUY_CODE = "buy = True\nif buy:\n    self.Buy(code, name, qty, price, ask1, bid1, n)"
BAD_SELL_CODE = "sell = True\nif sell:\n    self.Sell(code, name, qty, price, ask1, bid1, force)"
FIXED_BUY_CODE = "buy = True\nif buy:\n    self.Buy()"
FIXED_SELL_CODE = "sell = True\nif sell:\n    self.Sell()"


def _load_module():
    spec = importlib.util.spec_from_file_location("repair_css_v7_call_arity", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_db(tmp_path):
    db_path = tmp_path / "loop_strategies.db"
    con = sqlite3.connect(str(db_path))
    con.execute('CREATE TABLE "stockbuy" ("index" TEXT PRIMARY KEY, "code" TEXT)')
    con.execute('CREATE TABLE "stocksell" ("index" TEXT PRIMARY KEY, "code" TEXT)')
    con.execute('INSERT INTO "stockbuy" VALUES (?, ?)', ("CSS_V7_TEST_B", BAD_BUY_CODE))
    con.execute('INSERT INTO "stocksell" VALUES (?, ?)', ("CSS_V7_TEST_S", BAD_SELL_CODE))
    con.commit()
    con.close()
    return db_path


def _rows(db_path, table):
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute(f'SELECT "index", "code" FROM "{table}" ORDER BY "index"').fetchall()
    finally:
        con.close()


def _write_pairs(tmp_path):
    pairs = [
        {
            "label": "CSS_V7_TEST_PAIR",
            "buy": "CSS_V7_TEST_B",
            "sell": "CSS_V7_TEST_S",
            "lane": "tick",
        }
    ]
    path = tmp_path / "pairs.json"
    path.write_text(json.dumps(pairs, ensure_ascii=False), encoding="utf-8")
    return path


def test_detects_invalid_and_normalizes_order_calls():
    mod = _load_module()

    violations = mod.find_order_call_arity_violations(BAD_BUY_CODE)
    fixed = mod.normalize_order_calls(BAD_BUY_CODE)

    assert len(violations) == 1
    assert violations[0].method == "Buy"
    assert violations[0].arg_count == 7
    assert fixed.endswith("self.Buy()")
    assert mod.find_order_call_arity_violations(fixed) == []


def test_dry_run_writes_repaired_pairs_without_db_changes(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    pairs_path = _write_pairs(tmp_path)
    out_dir = tmp_path / "out"
    report = tmp_path / "receipt.json"

    code = mod.run([
        "--db", str(db_path),
        "--pairs-in", str(pairs_path),
        "--out-dir", str(out_dir),
        "--report", str(report),
    ])

    assert code == 0
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["dry_run"] is True
    assert receipt["planned_insert_count"] == 2
    assert receipt["inserted_count"] == 0
    assert not list(tmp_path.glob("loop_strategies.db.bak.css_v7_fixcall_*"))
    assert _rows(db_path, "stockbuy") == [("CSS_V7_TEST_B", BAD_BUY_CODE)]
    repaired_pairs = json.loads((out_dir / "pairs_unique_fixcall.json").read_text(encoding="utf-8"))
    assert repaired_pairs[0]["buy"] == "CSS_V7_TEST_B_FIXCALL"
    assert repaired_pairs[0]["sell"] == "CSS_V7_TEST_S_FIXCALL"


def test_apply_inserts_fixcall_rows_append_only(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    pairs_path = _write_pairs(tmp_path)
    out_dir = tmp_path / "out"
    report = tmp_path / "receipt.json"

    code = mod.run([
        "--db", str(db_path),
        "--pairs-in", str(pairs_path),
        "--out-dir", str(out_dir),
        "--report", str(report),
        "--apply",
    ])

    assert code == 0
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["dry_run"] is False
    assert receipt["inserted_count"] == 2
    assert Path(receipt["backup_path"]).exists()
    buy_rows = _rows(db_path, "stockbuy")
    sell_rows = _rows(db_path, "stocksell")
    assert buy_rows[0] == ("CSS_V7_TEST_B", BAD_BUY_CODE)
    assert buy_rows[1] == ("CSS_V7_TEST_B_FIXCALL", FIXED_BUY_CODE)
    assert sell_rows[1] == ("CSS_V7_TEST_S_FIXCALL", FIXED_SELL_CODE)
    assert receipt["invalid_runtime_call_count_after_repair"] == 0


def test_apply_aborts_on_conflicting_fixcall_name(tmp_path):
    mod = _load_module()
    db_path = _make_db(tmp_path)
    pairs_path = _write_pairs(tmp_path)
    con = sqlite3.connect(str(db_path))
    con.execute('INSERT INTO "stockbuy" VALUES (?, ?)', ("CSS_V7_TEST_B_FIXCALL", "other code"))
    con.commit()
    con.close()
    out_dir = tmp_path / "out"
    report = tmp_path / "receipt.json"

    code = mod.run([
        "--db", str(db_path),
        "--pairs-in", str(pairs_path),
        "--out-dir", str(out_dir),
        "--report", str(report),
        "--apply",
    ])

    assert code == 3
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert receipt["status"] == "collision_abort"
    assert receipt["conflicts"][0]["name"] == "CSS_V7_TEST_B_FIXCALL"
    assert receipt["inserted_count"] == 0
