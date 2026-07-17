# -*- coding: utf-8 -*-
"""Read-only retirement contract for register_chart_sulsa_conditions.py."""
import hashlib
import importlib.util
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "register_chart_sulsa_conditions.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "register_chart_sulsa_conditions", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _condition(condition_id, side, code):
    return {
        "id": condition_id,
        "side": side,
        "code": code,
        "code_sha256": _sha(code),
        "status": "hypothesis_seed",
    }


def _write_docs(tmp_path):
    conditions = [
        _condition("CSS_V7_TEST_B", "buy", "매수 = False\n"),
        _condition("CSS_V7_TEST_S", "sell", "매도 = False\n"),
    ]
    conditions_path = tmp_path / "conditions.json"
    combos_path = tmp_path / "combos.json"
    conditions_path.write_text(json.dumps({"conditions": conditions}), encoding="utf-8")
    combos_path.write_text(json.dumps({"combos": []}), encoding="utf-8")
    return conditions_path, combos_path


def _make_db(tmp_path):
    db_path = tmp_path / "strategy.db"
    con = sqlite3.connect(str(db_path))
    try:
        for table in ("stockbuy", "stocksell"):
            con.execute('CREATE TABLE "%s" ("index" TEXT, "전략코드" TEXT)' % table)
        con.commit()
    finally:
        con.close()
    return db_path


def _argv(db_path, conditions_path, combos_path, *extra):
    return [
        "--db", str(db_path),
        "--conditions", str(conditions_path),
        "--combos", str(combos_path),
        *extra,
    ]


def _file_snapshot(root):
    return {
        path.relative_to(root): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_historical_preview_is_non_authoritative_and_read_only(tmp_path, capsys):
    conditions_path, combos_path = _write_docs(tmp_path)
    db_path = _make_db(tmp_path)
    before = _file_snapshot(tmp_path)

    assert MOD.run(_argv(db_path, conditions_path, combos_path)) == 0

    output = capsys.readouterr().out
    assert "HISTORICAL-PREVIEW-NON-AUTHORITATIVE" in output
    assert "No database, ledger, receipt, backup, or file writes" in output
    assert _file_snapshot(tmp_path) == before


def test_apply_and_all_file_write_flags_are_refused_before_sqlite_open(tmp_path, monkeypatch):
    conditions_path, combos_path = _write_docs(tmp_path)
    db_path = _make_db(tmp_path)
    before = _file_snapshot(tmp_path)

    def sqlite_must_not_open(_):
        raise AssertionError("rejected write flag opened SQLite")

    monkeypatch.setattr(MOD, "open_db", sqlite_must_not_open)
    rejected_flags = (
        ("--apply",),
        ("--write-ledger", str(tmp_path / "ledger.jsonl")),
        ("--report", str(tmp_path / "receipt.json")),
    )
    for extra in rejected_flags:
        try:
            MOD.run(_argv(db_path, conditions_path, combos_path, *extra))
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError("retired write flag was accepted: %s" % (extra,))

    assert _file_snapshot(tmp_path) == before


def test_open_db_uses_sqlite_read_only_uri(tmp_path):
    db_path = _make_db(tmp_path)
    con = MOD.open_db(db_path)
    try:
        assert con.execute("PRAGMA query_only").fetchone() == (0,)
        try:
            con.execute('INSERT INTO "stockbuy" VALUES (?, ?)', ("x", "y"))
        except sqlite3.OperationalError:
            pass
        else:
            raise AssertionError("read-only connection accepted an INSERT")
    finally:
        con.close()


def test_source_has_no_legacy_write_modes():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert 'parser.add_argument("--apply"' not in source
    assert 'parser.add_argument("--write-ledger"' not in source
    assert 'parser.add_argument("--report"' not in source
    assert "mode=ro" in source
