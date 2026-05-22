"""V3U_C DB 호환성 진단·자동 PK 추가 도구 (E5).

V2 → V3 마이그레이션 잔여 결함(PRIMARY KEY 누락) 자동 해소.

## 동작 모드

| 모드 | 액션 |
|---|---|
| `--scan` (기본) | read-only. _database 모든 .db의 PK 매트릭스 + V3.08 호환성 매트릭스 보고 |
| `--add-pk` | PK 누락 테이블에 자동 추가 (백업 보유 검증 후). stock_min/tick만 대상 |
| `--analyze-extra` | backtest.db/code_info.db/setting.db 등 stock 외 DB schema 추가 분석 |

## 사용 예

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_db_compatibility_check.py --scan
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_db_compatibility_check.py --add-pk
```

## Constraint

- V3 official source 0줄 수정
- 사용자 데이터 무수정 (--scan 모드) 또는 백업 보유 검증 후 변경 (--add-pk)
- sqlite ALTER TABLE 미사용 (호환성 위해 CREATE + INSERT + DROP + RENAME 패턴)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB_DIR = Path("./_database")
DEFAULT_BACKUP_GLOB = "_database_backup_*"


def find_db_files(db_dir: Path) -> list[Path]:
    if not db_dir.is_dir():
        return []
    return sorted(p for p in db_dir.glob("*.db") if p.stat().st_size > 0)


def find_backup_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.glob(DEFAULT_BACKUP_GLOB) if p.is_dir())


def table_has_pk(con: sqlite3.Connection, table: str) -> bool:
    """sqlite_master에서 CREATE TABLE 본문에 PRIMARY KEY 포함 여부 검증."""
    cur = con.cursor()
    cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,))
    row = cur.fetchone()
    if not row or not row[0]:
        return False
    sql = row[0]
    return "PRIMARY KEY" in sql.upper()


def scan_db(db_path: Path) -> dict:
    """단일 DB의 테이블별 PK 매트릭스."""
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        result = {
            "path": str(db_path),
            "name": db_path.name,
            "table_count": len(tables),
            "tables_with_pk": 0,
            "tables_without_pk": 0,
            "missing_pk_examples": [],
        }
        for t in tables:
            if table_has_pk(con, t):
                result["tables_with_pk"] += 1
            else:
                result["tables_without_pk"] += 1
                if len(result["missing_pk_examples"]) < 3:
                    result["missing_pk_examples"].append(t)
        return result
    finally:
        con.close()


def is_stock_data_db(db_path: Path) -> bool:
    """stock_min_*.db / stock_tick_*.db / coin_tick_*.db 만 PK 추가 대상."""
    name = db_path.name.lower()
    return bool(re.search(r"(stock|coin)_(min|tick)_\d{8}\.db$", name))


def add_pk_to_db(db_path: Path, *, dry_run: bool = False) -> dict:
    """PK 누락 테이블에 'index' 컬럼 PK 자동 추가.

    sqlite ALTER TABLE이 ADD CONSTRAINT를 지원하지 않으므로:
    1. 신규 테이블을 CREATE (PK 포함)
    2. 기존 데이터 INSERT INTO new SELECT * FROM old
    3. DROP TABLE old
    4. ALTER TABLE new RENAME TO old
    """
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    result = {
        "path": str(db_path),
        "processed": 0,
        "skipped_already_pk": 0,
        "errors": [],
        "dry_run": dry_run,
    }
    try:
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for t in tables:
            if t == "moneytop":
                continue  # update_db_20260418.py도 제외
            if table_has_pk(con, t):
                result["skipped_already_pk"] += 1
                continue
            cur.execute(f'PRAGMA table_info("{t}")')
            cols = cur.fetchall()
            if not cols:
                continue
            col_defs = []
            col_names = []
            for c in cols:
                cname = c[1]
                ctype = c[2] or "REAL"
                col_names.append(f'"{cname}"')
                if cname == "index":
                    col_defs.append(f'"{cname}" {ctype} PRIMARY KEY')
                else:
                    col_defs.append(f'"{cname}" {ctype}')
            new_table = f"__pk_migration_{t}"
            try:
                if dry_run:
                    result["processed"] += 1
                    continue
                cur.execute(f'CREATE TABLE "{new_table}" ({", ".join(col_defs)})')
                cur.execute(f'INSERT INTO "{new_table}" SELECT * FROM "{t}"')
                cur.execute(f'DROP TABLE "{t}"')
                cur.execute(f'ALTER TABLE "{new_table}" RENAME TO "{t}"')
                result["processed"] += 1
            except sqlite3.Error as exc:
                result["errors"].append({"table": t, "error": str(exc)})
                con.rollback()
                continue
        if not dry_run:
            con.commit()
        return result
    finally:
        con.close()


def analyze_extra_db(db_path: Path) -> dict:
    """stock 외 DB(backtest/code_info/setting 등)의 schema 요약."""
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        summary = {"path": str(db_path), "name": db_path.name, "tables": {}}
        for t in tables:
            cur.execute(f'PRAGMA table_info("{t}")')
            cols = [r[1] for r in cur.fetchall()]
            summary["tables"][t] = {
                "column_count": len(cols),
                "columns_preview": cols[:8],
                "has_pk": table_has_pk(con, t),
            }
        return summary
    finally:
        con.close()


def cmd_scan(args) -> int:
    db_dir = Path(args.db_dir).resolve()
    print(f"[SCAN] DB 디렉토리: {db_dir}")
    db_files = find_db_files(db_dir)
    print(f"[SCAN] 발견된 .db 파일: {len(db_files)}")

    stock_dbs: list[dict] = []
    extra_dbs: list[dict] = []
    for db_path in db_files:
        result = scan_db(db_path)
        if is_stock_data_db(db_path):
            stock_dbs.append(result)
        else:
            extra_dbs.append(result)

    print(f"\n=== Stock data DB (PK 추가 대상) ===")
    total_with = total_without = 0
    for d in stock_dbs:
        print(
            f"  {d['name']:40s} 테이블 {d['table_count']:3d} | "
            f"PK 있음 {d['tables_with_pk']:3d} | 없음 {d['tables_without_pk']:3d}"
        )
        total_with += d["tables_with_pk"]
        total_without += d["tables_without_pk"]
    print(f"  합계: PK 있음 {total_with} / 없음 {total_without}")

    print(f"\n=== 기타 DB (별도 분석 후보) ===")
    for d in extra_dbs:
        print(
            f"  {d['name']:40s} 테이블 {d['table_count']:3d} | "
            f"PK 있음 {d['tables_with_pk']:3d} | 없음 {d['tables_without_pk']:3d}"
        )

    payload = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "db_dir": str(db_dir),
        "stock_dbs": stock_dbs,
        "extra_dbs": extra_dbs,
        "summary": {
            "stock_db_count": len(stock_dbs),
            "extra_db_count": len(extra_dbs),
            "total_tables_with_pk": total_with,
            "total_tables_without_pk": total_without,
            "v3_08_compatible": total_without == 0,
        },
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n[INFO] JSON 매니페스트: {out}")

    if total_without > 0:
        print(f"\n[WARN] V3.08 PRIMARY KEY 호환 안 됨. --add-pk로 자동 추가 가능 (백업 보유 필수)")
        return 1
    print(f"\n[OK] V3.08 PRIMARY KEY 호환 OK")
    return 0


def cmd_add_pk(args) -> int:
    db_dir = Path(args.db_dir).resolve()
    # 백업 보유 검증
    backups = find_backup_dirs(db_dir.parent)
    if not backups and not args.force:
        print(f"[FAIL] 백업 디렉토리 없음 ({db_dir.parent}/_database_backup_*).")
        print(f"       xcopy {db_dir.name} _database_backup_<date> /E /I 로 사전 백업 필수.")
        print(f"       또는 --force로 강제 진행 (위험)")
        return 1
    if backups:
        print(f"[INFO] 백업 발견: {backups[-1]}")

    db_files = find_db_files(db_dir)
    stock_dbs = [p for p in db_files if is_stock_data_db(p)]
    print(f"[ADD-PK] 대상 stock DB: {len(stock_dbs)}")
    total_processed = total_errors = 0
    for db_path in stock_dbs:
        result = add_pk_to_db(db_path, dry_run=args.dry_run)
        if result["processed"] > 0 or result["errors"]:
            tag = "DRY" if args.dry_run else "ADD"
            print(
                f"  [{tag}] {db_path.name:40s} "
                f"처리 {result['processed']:3d} | "
                f"기존 PK {result['skipped_already_pk']:3d} | "
                f"에러 {len(result['errors']):2d}"
            )
        total_processed += result["processed"]
        total_errors += len(result["errors"])
        if result["errors"]:
            for e in result["errors"][:3]:
                print(f"    error: {e['table']}: {e['error']}")
    print(f"\n[OK] 처리 완료. 총 {total_processed} 테이블에 PK 추가 (에러 {total_errors})")
    return 0 if total_errors == 0 else 1


def cmd_analyze_extra(args) -> int:
    db_dir = Path(args.db_dir).resolve()
    db_files = find_db_files(db_dir)
    extra_dbs = [p for p in db_files if not is_stock_data_db(p)]
    print(f"[ANALYZE-EXTRA] 대상 기타 DB: {len(extra_dbs)}")
    for db_path in extra_dbs:
        summary = analyze_extra_db(db_path)
        print(f"\n--- {summary['name']} ({len(summary['tables'])} tables) ---")
        for tname, tinfo in list(summary["tables"].items())[:10]:
            pk_tag = " [PK]" if tinfo["has_pk"] else ""
            print(
                f"  {tname:30s} cols={tinfo['column_count']:3d}{pk_tag} "
                f"preview={tinfo['columns_preview']}"
            )
        if len(summary["tables"]) > 10:
            print(f"  ... ({len(summary['tables']) - 10} more)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3U_C DB 호환성 진단·자동 PK 추가 (E5)")
    parser.add_argument("--db-dir", default=str(DEFAULT_DB_DIR), help="DB 디렉토리 (기본 ./_database)")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="read-only PK 매트릭스 진단")
    p_scan.add_argument("--output", help="JSON 매니페스트 출력 경로 (선택)")

    p_addpk = sub.add_parser("add-pk", help="PK 누락 테이블에 자동 추가 (백업 필수)")
    p_addpk.add_argument("--dry-run", action="store_true", help="실 변경 없이 시뮬")
    p_addpk.add_argument("--force", action="store_true", help="백업 없어도 강제 진행 (위험)")

    p_extra = sub.add_parser("analyze-extra", help="stock 외 DB schema 분석")

    # legacy alias: --scan / --add-pk
    parser.add_argument("--scan", action="store_const", const="scan", dest="cmd_legacy")
    parser.add_argument("--add-pk", action="store_const", const="add-pk", dest="cmd_legacy")
    parser.add_argument("--analyze-extra", action="store_const", const="analyze-extra", dest="cmd_legacy")
    parser.add_argument("--output", help="JSON 매니페스트 (--scan용)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="시뮬 모드 (--add-pk용)")
    parser.add_argument("--force", action="store_true", help="--add-pk 백업 없이 강제")

    args = parser.parse_args(argv)
    cmd = args.cmd or args.cmd_legacy or "scan"

    if cmd == "scan":
        return cmd_scan(args)
    if cmd == "add-pk":
        return cmd_add_pk(args)
    if cmd == "analyze-extra":
        return cmd_analyze_extra(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
