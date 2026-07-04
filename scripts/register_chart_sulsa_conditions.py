"""chart_sulsa v7 조건식 전략 DB 등록 도구 (연구 레인 전용, INSERT-only).

동작 원칙 (위반 금지):
- 모든 조건식은 무근거 가설 시드(hypothesis_seed) 라벨이 있어야만 처리한다.
- 전략 DB에는 신규 행 INSERT만 수행한다. 기존 행은 어떤 방식으로도 변형하지 않는다.
- 기본은 dry-run이며 --apply 명시 시에만 실저장한다.
- 실저장 전 DB 파일 백업(.bak.chart_sulsa_<UTC>)을 강제한다.
- 이름이 이미 존재하면: 코드 sha256 동일 -> skip(멱등), 상이 -> 저장하지 않고 conflict 보고.
- 출처 원장(provenance JSONL)은 조건식/조합 JSON에서 결정론적으로 생성한다.

종료 코드: 0=정상(스킵 포함), 2=입력 검증 실패, 3=이름 충돌 존재.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
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
EXTRACTION_METHOD = "phase4_workflow + this_script"
CATALOG_DOC_RELPATH = "2026-07-02_chart_sulsa_v7_condition_catalog.md"
PASSPORT_DIR_RELPATH = "../condition_passports/chart_sulsa"
FALLBACK_SOURCE_DOCUMENT = "C:/System_Trading/chart_sulsa_stom_quant_insight_report_v7_0.html"
FALLBACK_EXTRACTED_AT = "2026-07-02"

# 저장명 절단 규칙: 스키마는 TEXT 무제한이지만 방어적으로 상한을 두고,
# 초과 시 앞에서부터 MAX_DB_NAME_LEN 문자만 유지한다(양쪽 이름은 원장에 기록됨).
MAX_DB_NAME_LEN = 128


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def db_name_for(condition_id: str) -> str:
    if len(condition_id) <= MAX_DB_NAME_LEN:
        return condition_id
    return condition_id[:MAX_DB_NAME_LEN]


def validate_documents(conditions_doc: dict, combos_doc: dict) -> list[str]:
    """입력 JSON 정합성 검사. 문제 목록(빈 리스트면 통과)을 반환한다."""
    problems: list[str] = []
    conditions = conditions_doc.get("conditions", [])
    if not conditions:
        problems.append("no conditions found in conditions JSON")
    ids = set()
    for cond in conditions:
        cid = cond.get("id", "<missing-id>")
        if cid in ids:
            problems.append("duplicated condition id: %s" % cid)
        ids.add(cid)
        if cond.get("status") != REQUIRED_STATUS:
            problems.append("condition %s status is not %s" % (cid, REQUIRED_STATUS))
        if cond.get("side") not in TABLE_BY_SIDE:
            problems.append("condition %s has unknown side: %r" % (cid, cond.get("side")))
        code = cond.get("code")
        if not isinstance(code, str) or not code:
            problems.append("condition %s has empty code" % cid)
        elif _sha256_text(code) != cond.get("code_sha256"):
            problems.append("condition %s code_sha256 mismatch (integrity)" % cid)
    for combo in combos_doc.get("combos", []):
        combo_id = combo.get("combo_id", "<missing-combo-id>")
        for key in ("buy_condition_id", "sell_condition_id"):
            ref = combo.get(key)
            if ref not in ids:
                problems.append("combo %s references unknown condition: %r" % (combo_id, ref))
    return problems


def open_db(db_path: Path, writable: bool) -> sqlite3.Connection:
    """dry-run은 read-only URI로 열어 DB 변형 가능성 자체를 차단한다."""
    if writable:
        return sqlite3.connect(str(db_path))
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def fetch_existing_shas(con: sqlite3.Connection, table: str) -> dict:
    """테이블의 저장명 -> (코드 sha256 튜플) 매핑. 중복 이름도 전부 수집."""
    if table not in TABLE_BY_SIDE.values():
        raise ValueError("unexpected table: %s" % table)
    sql = 'SELECT "%s", "%s" FROM "%s"' % (NAME_COLUMN, CODE_COLUMN, table)
    result: dict = {}
    for name, code in con.execute(sql).fetchall():
        sha = _sha256_text(code) if isinstance(code, str) else ""
        result = {**result, name: result.get(name, ()) + (sha,)}
    return result


def build_plan(conditions: list, existing_by_table: dict) -> tuple:
    """(inserts, skips, conflicts) 계획을 만든다. 계획 단계는 DB를 읽기만 한다."""
    inserts: list = []
    skips: list = []
    conflicts: list = []
    for cond in conditions:
        table = TABLE_BY_SIDE[cond["side"]]
        name = db_name_for(cond["id"])
        entry = {
            "id": cond["id"],
            "db_name": name,
            "table": table,
            "code_sha256": cond["code_sha256"],
        }
        existing_shas = existing_by_table.get(table, {}).get(name)
        if existing_shas is None:
            inserts.append(entry)
        elif all(sha == cond["code_sha256"] for sha in existing_shas):
            skips.append({**entry, "reason": "identical_code_sha256"})
        else:
            conflicts.append({**entry, "existing_code_sha256": list(existing_shas)})
    return inserts, skips, conflicts


def make_backup(db_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = Path(str(db_path) + ".bak.chart_sulsa_" + stamp)
    shutil.copy2(db_path, backup_path)
    return backup_path


def apply_inserts(con: sqlite3.Connection, conditions_by_id: dict, inserts: list) -> None:
    for item in inserts:
        table = item["table"]
        if table not in TABLE_BY_SIDE.values():
            raise ValueError("unexpected table: %s" % table)
        sql = 'INSERT INTO "%s" ("%s", "%s") VALUES (?, ?)' % (table, NAME_COLUMN, CODE_COLUMN)
        con.execute(sql, (item["db_name"], conditions_by_id[item["id"]]["code"]))
    con.commit()


def build_ledger_entries(conditions_doc: dict, combos_doc: dict) -> list:
    """조건식+조합 전건의 출처 원장 엔트리(결정론)를 생성한다."""
    source_document = combos_doc.get("source_path", FALLBACK_SOURCE_DOCUMENT)
    source_sha = combos_doc.get("source_sha256")
    extracted_at = combos_doc.get("generated_date", FALLBACK_EXTRACTED_AT)
    sha_by_id = {c["id"]: c["code_sha256"] for c in conditions_doc["conditions"]}
    entries: list = []
    for cond in conditions_doc["conditions"]:
        entries.append({
            "entry_type": "condition",
            "id": cond["id"],
            "name_ko": cond["name_ko"],
            "db_table": TABLE_BY_SIDE[cond["side"]],
            "db_name": db_name_for(cond["id"]),
            "source_document": source_document,
            "source_document_sha256": source_sha,
            "source_sections": [cond["source_section"]],
            "code_sha256": cond["code_sha256"],
            "extracted_at": extracted_at,
            "extraction_method": EXTRACTION_METHOD,
            "catalog_doc": CATALOG_DOC_RELPATH,
            "passport": "%s/%s.md" % (PASSPORT_DIR_RELPATH, cond["id"].lower()),
            "status": cond.get("status"),
        })
    for combo in combos_doc.get("combos", []):
        entries.append({
            "entry_type": "combo",
            "id": combo["combo_id"],
            "name_ko": combo["name_ko"],
            "db_table": None,
            "db_name": None,
            "source_document": source_document,
            "source_document_sha256": source_sha,
            "source_sections": list(combo.get("source_sections", [])),
            "code_sha256": {
                "buy": sha_by_id.get(combo.get("buy_condition_id")),
                "sell": sha_by_id.get(combo.get("sell_condition_id")),
            },
            "buy_condition_id": combo.get("buy_condition_id"),
            "sell_condition_id": combo.get("sell_condition_id"),
            "extracted_at": extracted_at,
            "extraction_method": EXTRACTION_METHOD,
            "catalog_doc": CATALOG_DOC_RELPATH,
            "passport": None,
            "status": combo.get("status"),
        })
    return entries


def render_ledger_jsonl(entries: list) -> str:
    lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
    return "\n".join(lines) + "\n"


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def build_receipt(db_path: Path, conditions_doc: dict, backup_path, inserted: list,
                  planned_inserts: list, skips: list, conflicts: list, dry_run: bool) -> dict:
    return {
        "backup_path": str(backup_path) if backup_path else None,
        "inserted": inserted,
        "skipped": skips,
        "conflicts": conflicts,
        "db_path": str(db_path),
        "table": dict(TABLE_BY_SIDE),
        "schema_version": conditions_doc.get("schema_version"),
        "dry_run": dry_run,
        "planned_inserts": planned_inserts,
        "status_label": REQUIRED_STATUS,
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {
            "inserted": len(inserted),
            "planned": len(planned_inserts),
            "skipped": len(skips),
            "conflicts": len(conflicts),
        },
    }


def _emit(message: str) -> None:
    sys.stdout.write(message + "\n")


def run(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="register_chart_sulsa_conditions",
        description="chart_sulsa v7 conditions -> strategy DB (research lane, INSERT-only)",
    )
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--conditions", default=str(DEFAULT_CONDITIONS_PATH))
    parser.add_argument("--combos", default=str(DEFAULT_COMBOS_PATH))
    parser.add_argument("--apply", action="store_true", help="perform real INSERTs")
    parser.add_argument("--report", default=None, help="receipt JSON output path")
    parser.add_argument("--write-ledger", default=None, dest="write_ledger",
                        help="provenance JSONL output path")
    args = parser.parse_args(argv)

    conditions_doc = _load_json(Path(args.conditions))
    combos_doc = _load_json(Path(args.combos))
    problems = validate_documents(conditions_doc, combos_doc)
    if problems:
        for problem in problems:
            _emit("VALIDATION: " + problem)
        return 2

    if args.write_ledger:
        entries = build_ledger_entries(conditions_doc, combos_doc)
        write_text_file(Path(args.write_ledger), render_ledger_jsonl(entries))
        _emit("ledger written: %s (%d entries)" % (args.write_ledger, len(entries)))

    conditions = conditions_doc["conditions"]
    conditions_by_id = {c["id"]: c for c in conditions}
    db_path = Path(args.db)

    read_con = open_db(db_path, writable=False)
    try:
        existing_by_table = {
            table: fetch_existing_shas(read_con, table)
            for table in TABLE_BY_SIDE.values()
        }
    finally:
        read_con.close()
    planned_inserts, skips, conflicts = build_plan(conditions, existing_by_table)

    backup_path = None
    inserted: list = []
    if args.apply:
        backup_path = make_backup(db_path)
        write_con = open_db(db_path, writable=True)
        try:
            apply_inserts(write_con, conditions_by_id, planned_inserts)
        finally:
            write_con.close()
        inserted = planned_inserts

    receipt = build_receipt(
        db_path, conditions_doc, backup_path, inserted,
        planned_inserts, skips, conflicts, dry_run=not args.apply,
    )
    if args.report:
        write_text_file(
            Path(args.report),
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        )

    mode = "APPLY" if args.apply else "DRY-RUN"
    _emit("mode=%s db=%s" % (mode, db_path))
    if backup_path:
        _emit("backup=%s" % backup_path)
    for item in planned_inserts:
        _emit("%s: %s -> %s" % ("insert" if args.apply else "plan-insert",
                                item["id"], item["table"]))
    for item in skips:
        _emit("skip(identical sha): %s" % item["id"])
    for item in conflicts:
        _emit("CONFLICT(sha mismatch, not saved): %s" % item["id"])
    _emit("totals inserted=%d planned=%d skipped=%d conflicts=%d" % (
        len(inserted), len(planned_inserts), len(skips), len(conflicts)))
    return 3 if conflicts else 0


if __name__ == "__main__":
    sys.exit(run())
