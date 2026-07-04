# -*- coding: utf-8 -*-
"""register_chart_sulsa_conditions.py 자기 테스트 (tmp sqlite 전용).

검증 항목: 백업 생성, INSERT-only(기존 행 보존), 멱등 skip, sha 불일치 conflict,
dry-run 무변경, receipt 스키마, 원장 결정론 생성, 파괴적 SQL 문자열 부재.
"""
import hashlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "register_chart_sulsa_conditions.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "register_chart_sulsa_conditions", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MOD = _load_module()


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _make_condition(cid, side, code, section="4.1"):
    return {
        "id": cid,
        "name_ko": "테스트 " + cid,
        "lane": "tick",
        "side": side,
        "principle_ids": ["P1"],
        "code": code,
        "code_sha256": _sha(code),
        "vars_ranges": None,
        "time_window": "09:00:00-09:30:00",
        "status": "hypothesis_seed",
        "source": "chart_sulsa_v7_0",
        "source_section": section,
    }


def _sample_docs():
    conditions = [
        _make_condition("CSS_V7_TEST_B_ALPHA", "buy", "매수 = False\nif True:\n    매수 = True\n"),
        _make_condition("CSS_V7_TEST_B_BETA", "buy", "매수 = False\n", section="4.2"),
        _make_condition("CSS_V7_TEST_S_ALPHA", "sell", "매도 = False\n", section="4.5"),
    ]
    conditions_doc = {
        "schema_version": 1,
        "source": "chart_sulsa_v7_0",
        "source_file": "chart_sulsa_stom_quant_insight_report_v7_0.html",
        "conditions": conditions,
    }
    combos_doc = {
        "schema_version": 1,
        "source_path": "C:/System_Trading/chart_sulsa_stom_quant_insight_report_v7_0.html",
        "source_sha256": "ab" * 32,
        "generated_date": "2026-07-02",
        "combos": [
            {
                "combo_id": "CSS_V7_TEST_COMBO_01",
                "name_ko": "테스트 조합",
                "lane": "tick",
                "buy_condition_id": "CSS_V7_TEST_B_ALPHA",
                "sell_condition_id": "CSS_V7_TEST_S_ALPHA",
                "source_sections": ["12.1"],
                "status": "hypothesis_seed",
                "priority": 1,
            }
        ],
    }
    return conditions_doc, combos_doc


def _write_docs(tmp_path, conditions_doc, combos_doc):
    cpath = tmp_path / "conditions.json"
    kpath = tmp_path / "combos.json"
    cpath.write_text(json.dumps(conditions_doc, ensure_ascii=False), encoding="utf-8")
    kpath.write_text(json.dumps(combos_doc, ensure_ascii=False), encoding="utf-8")
    return cpath, kpath


PRE_ROWS = {
    "stockbuy": ("기존매수전략", "매수 = True\n"),
    "stocksell": ("기존매도전략", "매도 = True\n"),
}


def _make_db(tmp_path):
    db_path = tmp_path / "strategy.db"
    con = sqlite3.connect(str(db_path))
    for table, row in PRE_ROWS.items():
        con.execute('CREATE TABLE "%s" ( "index" TEXT, "전략코드" TEXT )' % table)
        con.execute('INSERT INTO "%s" VALUES (?, ?)' % table, row)
    con.commit()
    con.close()
    return db_path


def _rows(db_path, table):
    con = sqlite3.connect(str(db_path))
    try:
        return con.execute('SELECT "index", "전략코드" FROM "%s"' % table).fetchall()
    finally:
        con.close()


def _run(tmp_path, extra_args, docs=None):
    conditions_doc, combos_doc = docs or _sample_docs()
    cpath, kpath = _write_docs(tmp_path, conditions_doc, combos_doc)
    db_path = tmp_path / "strategy.db"
    if not db_path.exists():
        _make_db(tmp_path)
    report = tmp_path / "receipt.json"
    argv = ["--db", str(db_path), "--conditions", str(cpath),
            "--combos", str(kpath), "--report", str(report)] + extra_args
    code = MOD.run(argv)
    receipt = None
    if report.exists():
        receipt = json.loads(report.read_text(encoding="utf-8"))
    return code, receipt, db_path


def _backups(tmp_path):
    return sorted(tmp_path.glob("strategy.db.bak.chart_sulsa_*"))


def test_dry_run_makes_no_changes(tmp_path):
    code, receipt, db_path = _run(tmp_path, [])
    assert code == 0
    assert receipt["dry_run"] is True
    assert receipt["inserted"] == []
    assert len(receipt["planned_inserts"]) == 3
    assert receipt["backup_path"] is None
    assert _backups(tmp_path) == []
    assert _rows(db_path, "stockbuy") == [PRE_ROWS["stockbuy"]]
    assert _rows(db_path, "stocksell") == [PRE_ROWS["stocksell"]]


def test_apply_creates_backup_and_only_appends(tmp_path):
    code, receipt, db_path = _run(tmp_path, ["--apply"])
    assert code == 0
    backups = _backups(tmp_path)
    assert len(backups) == 1
    assert receipt["backup_path"] == str(backups[0])
    buy_rows = _rows(db_path, "stockbuy")
    sell_rows = _rows(db_path, "stocksell")
    # 기존 행 원형 보존 (INSERT-only)
    assert buy_rows[0] == PRE_ROWS["stockbuy"]
    assert sell_rows[0] == PRE_ROWS["stocksell"]
    assert len(buy_rows) == 1 + 2
    assert len(sell_rows) == 1 + 1
    names = {r[0] for r in buy_rows}
    assert {"CSS_V7_TEST_B_ALPHA", "CSS_V7_TEST_B_BETA"} <= names
    assert len(receipt["inserted"]) == 3
    assert receipt["conflicts"] == []
    # 백업본에는 신규 행이 없어야 한다(저장 직전 스냅샷)
    assert len(_rows(backups[0], "stockbuy")) == 1


def test_apply_twice_is_idempotent_skip(tmp_path):
    _run(tmp_path, ["--apply"])
    code, receipt, db_path = _run(tmp_path, ["--apply"])
    assert code == 0
    assert receipt["inserted"] == []
    assert len(receipt["skipped"]) == 3
    assert all(s["reason"] == "identical_code_sha256" for s in receipt["skipped"])
    assert len(_rows(db_path, "stockbuy")) == 3
    assert len(_rows(db_path, "stocksell")) == 2


def test_sha_mismatch_reports_conflict_and_preserves_row(tmp_path):
    db_path = _make_db(tmp_path)
    other_code = "매수 = False\n# 다른 코드\n"
    con = sqlite3.connect(str(db_path))
    con.execute('INSERT INTO "stockbuy" VALUES (?, ?)',
                ("CSS_V7_TEST_B_ALPHA", other_code))
    con.commit()
    con.close()
    code, receipt, db_path = _run(tmp_path, ["--apply"])
    assert code == 3
    conflict_ids = [c["id"] for c in receipt["conflicts"]]
    assert conflict_ids == ["CSS_V7_TEST_B_ALPHA"]
    assert receipt["conflicts"][0]["existing_code_sha256"] == [_sha(other_code)]
    # 충돌 조건식은 저장되지 않고, 기존 행은 그대로다
    buy_rows = _rows(db_path, "stockbuy")
    alpha_rows = [r for r in buy_rows if r[0] == "CSS_V7_TEST_B_ALPHA"]
    assert alpha_rows == [("CSS_V7_TEST_B_ALPHA", other_code)]
    # 충돌 없는 나머지는 저장된다
    inserted_ids = {i["id"] for i in receipt["inserted"]}
    assert inserted_ids == {"CSS_V7_TEST_B_BETA", "CSS_V7_TEST_S_ALPHA"}


def test_receipt_schema_keys(tmp_path):
    _, receipt, _ = _run(tmp_path, [])
    required = {"backup_path", "inserted", "skipped", "conflicts",
                "db_path", "table", "schema_version"}
    assert required <= set(receipt)
    assert receipt["table"] == {"buy": "stockbuy", "sell": "stocksell"}
    assert receipt["schema_version"] == 1
    assert receipt["status_label"] == "hypothesis_seed"


def test_ledger_generation_is_deterministic(tmp_path):
    conditions_doc, combos_doc = _sample_docs()
    entries_a = MOD.build_ledger_entries(conditions_doc, combos_doc)
    entries_b = MOD.build_ledger_entries(conditions_doc, combos_doc)
    text_a = MOD.render_ledger_jsonl(entries_a)
    text_b = MOD.render_ledger_jsonl(entries_b)
    assert text_a == text_b
    assert len(entries_a) == 3 + 1
    lines = text_a.strip().split("\n")
    assert len(lines) == 4
    parsed = [json.loads(line) for line in lines]
    cond_entries = [e for e in parsed if e["entry_type"] == "condition"]
    combo_entries = [e for e in parsed if e["entry_type"] == "combo"]
    assert len(cond_entries) == 3 and len(combo_entries) == 1
    for entry in cond_entries:
        assert entry["db_name"] == entry["id"]
        assert entry["db_table"] in ("stockbuy", "stocksell")
        assert entry["passport"].endswith(entry["id"].lower() + ".md")
        assert entry["source_document_sha256"] == "ab" * 32
        assert entry["extracted_at"] == "2026-07-02"
        assert entry["extraction_method"] == "phase4_workflow + this_script"
        assert entry["status"] == "hypothesis_seed"
    combo = combo_entries[0]
    assert combo["db_name"] is None and combo["db_table"] is None
    assert combo["code_sha256"]["buy"] == _sha("매수 = False\nif True:\n    매수 = True\n")
    assert combo["code_sha256"]["sell"] == _sha("매도 = False\n")
    assert combo["source_sections"] == ["12.1"]


def test_write_ledger_flag_writes_jsonl(tmp_path):
    ledger_path = tmp_path / "ledger" / "provenance_registry.jsonl"
    code, _, _ = _run(tmp_path, ["--write-ledger", str(ledger_path)])
    assert code == 0
    content = ledger_path.read_text(encoding="utf-8")
    assert content.endswith("\n") and "\r" not in content
    assert len(content.strip().split("\n")) == 4


def test_integrity_guard_blocks_on_bad_sha(tmp_path):
    conditions_doc, combos_doc = _sample_docs()
    broken = {**conditions_doc["conditions"][0], "code_sha256": "0" * 64}
    docs = ({**conditions_doc, "conditions": [broken] + conditions_doc["conditions"][1:]},
            combos_doc)
    code, receipt, db_path = _run(tmp_path, ["--apply"], docs=docs)
    assert code == 2
    assert receipt is None
    assert _backups(tmp_path) == []
    assert _rows(db_path, "stockbuy") == [PRE_ROWS["stockbuy"]]


def test_status_guard_requires_hypothesis_seed(tmp_path):
    conditions_doc, combos_doc = _sample_docs()
    promoted = {**conditions_doc["conditions"][0], "status": "promoted"}
    docs = ({**conditions_doc, "conditions": [promoted] + conditions_doc["conditions"][1:]},
            combos_doc)
    code, _, db_path = _run(tmp_path, ["--apply"], docs=docs)
    assert code == 2
    assert _rows(db_path, "stockbuy") == [PRE_ROWS["stockbuy"]]


def test_source_contains_no_destructive_sql():
    source = SCRIPT_PATH.read_text(encoding="utf-8").upper()
    for token in ("UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "REPLACE"):
        assert token not in source, "forbidden token in script source: " + token
    assert "PRINT(" not in source
