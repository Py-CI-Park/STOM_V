"""V3U_C strategy.db V2 → V3 조건식 마이그레이션 (E7).

V2 (Kiwoom)와 V3 (LS API)는 strategy.db 테이블 이름이 다르다.
- V2: `stockbuy`, `stocksell`, `stockoptibuy`, `stockoptisell`, `stockoptivars`, ...
- V3: `stock_buy`, `stock_sell`, `stock_optibuy`, ... (밑줄 추가 + 거래소별 분리)

V3는 setting_market.py의 '전략구분' 값(`stock`, `stock_etf`, `stock_etn`, `stock_usa`, `coin`, `future`, ...)을
prefix로 사용해 거래소별 분리한다. 본 도구는 V2의 단일 테이블 데이터를 V3의 가장 일반적인 전략구분
(`stock` = 국내주식01·02)에 자동 복사하여 사용자가 백테를 즉시 시도할 수 있게 한다.

## 매핑 규칙 (기본 stock 거래소)

| V2 테이블 | V3 테이블 | 비고 |
|---|---|---|
| stockbuy | stock_buy | 매수 조건식 (핵심) |
| stocksell | stock_sell | 매도 조건식 (핵심) |
| stockbuyconds | stock_buyconds | 매수 보조 |
| stocksellconds | stock_sellconds | 매도 보조 |
| stockoptibuy | stock_optibuy | 최적화 매수 변수값 |
| stockoptisell | stock_optisell | 최적화 매도 |
| stockoptivars | stock_optivars | 최적화 변수 |
| stockoptigavars | stock_optigavars | GA 최적화 변수 |
| stockpassticks | stock_passticks | 패스틱 설정 |
| stockvars | stock_vars | 일반 변수 |

## 동작 모드

| 모드 | 액션 |
|---|---|
| `scan` (기본) | read-only. V2/V3 테이블 매핑 + rows 매트릭스 |
| `migrate` | V2 데이터를 V3 빈 테이블에 복사 (V3 테이블이 비어있을 때만 안전 진행) |
| `--target <prefix>` | 대상 prefix 변경 (기본 `stock`, `stock_etf`/`stock_usa`/`coin` 등 가능) |
| `--dry-run` | migrate 모드에서 실 변경 없이 시뮬 |
| `--force` | V3 테이블에 데이터 있어도 덮어쓰기 (위험, 백업 보유 검증) |

## 사용 예

```powershell
cd C:/System_Trading/STOM/STOM_V.wt-3u
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_strategy_migration.py scan
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_strategy_migration.py migrate --dry-run
python C:/System_Trading/STOM/STOM_V.wt-3uc/scripts/v3uc_strategy_migration.py migrate
```
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_DB = Path("./_database/strategy.db")
DEFAULT_BACKUP_GLOB = "_database_backup_*"

# V2 → V3 테이블 명 매핑 (밑줄 추가 + 거래소 prefix)
V2_TO_V3_SUFFIX_MAP = {
    "buy": "buy",
    "buyconds": "buyconds",
    "sell": "sell",
    "sellconds": "sellconds",
    "optibuy": "optibuy",
    "optisell": "optisell",
    "optivars": "optivars",
    "optigavars": "optigavars",
    "passticks": "passticks",
    "vars": "vars",
}


def v2_table_name(suffix: str) -> str:
    """V2 컨벤션: stockbuy, stockoptivars 등."""
    return f"stock{suffix}"


def v3_table_name(target_prefix: str, suffix: str) -> str:
    """V3 컨벤션: stock_buy, stock_etf_optivars 등."""
    return f"{target_prefix}_{V2_TO_V3_SUFFIX_MAP[suffix]}"


def count_rows(con: sqlite3.Connection, table: str) -> int:
    try:
        cur = con.cursor()
        cur.execute(f'SELECT COUNT(*) FROM "{table}"')
        return cur.fetchone()[0]
    except sqlite3.Error:
        return -1


def get_columns(con: sqlite3.Connection, table: str) -> list[str]:
    try:
        cur = con.cursor()
        cur.execute(f'PRAGMA table_info("{table}")')
        return [r[1] for r in cur.fetchall()]
    except sqlite3.Error:
        return []


def find_backup_dirs(root: Path) -> list[Path]:
    return sorted(p for p in root.glob(DEFAULT_BACKUP_GLOB) if p.is_dir())


def cmd_scan(args) -> int:
    db_path = Path(args.db).resolve()
    if not db_path.is_file():
        print(f"[FAIL] strategy.db 없음: {db_path}")
        return 1
    target = args.target
    con = sqlite3.connect(str(db_path))
    print(f"[SCAN] strategy.db: {db_path}")
    print(f"[SCAN] V2 → V3 매핑 (target prefix='{target}')")
    print(f"\n{'V2 테이블':25s} {'V2 rows':>8s}  →  {'V3 테이블':25s} {'V3 rows':>8s}  비고")
    print("-" * 100)
    payload = {"db": str(db_path), "target_prefix": target, "mappings": []}
    total_v2 = total_v3 = 0
    for suffix in V2_TO_V3_SUFFIX_MAP:
        v2 = v2_table_name(suffix)
        v3 = v3_table_name(target, suffix)
        v2_rows = count_rows(con, v2)
        v3_rows = count_rows(con, v3)
        v2_cols = get_columns(con, v2)
        v3_cols = get_columns(con, v3)
        note = ""
        if v2_rows < 0:
            note = "V2 테이블 없음"
        elif v3_rows < 0:
            note = "V3 테이블 없음"
        elif v2_rows == 0:
            note = "V2 비어있음 (마이그레이션 불필요)"
        elif v3_rows > 0:
            note = "V3 이미 있음 (--force 필요)"
        else:
            note = "마이그레이션 후보"
        print(f"{v2:25s} {v2_rows:>8d}  →  {v3:25s} {v3_rows:>8d}  {note}")
        if v2_rows > 0:
            total_v2 += v2_rows
        if v3_rows > 0:
            total_v3 += v3_rows
        payload["mappings"].append({
            "v2_table": v2,
            "v2_rows": v2_rows,
            "v2_cols": v2_cols,
            "v3_table": v3,
            "v3_rows": v3_rows,
            "v3_cols": v3_cols,
            "note": note,
            "schemas_match": v2_cols == v3_cols and v2_cols != [],
        })
    print(f"\n총 V2 rows: {total_v2} / V3 rows: {total_v3}")
    payload["summary"] = {
        "v2_total_rows": total_v2,
        "v3_total_rows": total_v3,
        "migration_candidates": sum(1 for m in payload["mappings"] if m["note"] == "마이그레이션 후보"),
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n[INFO] JSON 매니페스트: {out}")
    con.close()
    if total_v2 == 0:
        print("\n[INFO] V2 데이터 없음 — 마이그레이션 불필요")
        return 0
    if payload["summary"]["migration_candidates"] == 0 and total_v2 > 0:
        print("\n[INFO] 모든 V2 데이터가 이미 V3에 존재. --force로 덮어쓰기 가능")
        return 0
    print(f"\n[OK] 마이그레이션 후보 {payload['summary']['migration_candidates']}건. `migrate` 명령으로 진행 가능")
    return 0


def cmd_migrate(args) -> int:
    db_path = Path(args.db).resolve()
    if not db_path.is_file():
        print(f"[FAIL] strategy.db 없음: {db_path}")
        return 1
    target = args.target
    backups = find_backup_dirs(db_path.parent.parent)
    if not backups and not args.force:
        print(f"[FAIL] 백업 없음. xcopy _database _database_backup_<date> 후 재시도. (--force 우회 가능, 위험)")
        return 1
    if backups:
        print(f"[INFO] 백업 발견: {backups[-1]}")

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    processed = errors = skipped = 0
    print(f"\n[MIGRATE] strategy.db V2 → V3 (target='{target}', dry_run={args.dry_run})")
    for suffix in V2_TO_V3_SUFFIX_MAP:
        v2 = v2_table_name(suffix)
        v3 = v3_table_name(target, suffix)
        v2_rows = count_rows(con, v2)
        v3_rows = count_rows(con, v3)
        v2_cols = get_columns(con, v2)
        v3_cols = get_columns(con, v3)
        if v2_rows <= 0:
            skipped += 1
            continue
        if v3_rows < 0:
            print(f"  [SKIP] {v2} → {v3}: V3 테이블 없음")
            skipped += 1
            continue
        if v3_rows > 0 and not args.force:
            print(f"  [SKIP] {v2}({v2_rows}) → {v3}({v3_rows} 이미 있음): --force 필요")
            skipped += 1
            continue
        if v2_cols != v3_cols:
            print(f"  [WARN] {v2}↔{v3} 컬럼 차이: V2={v2_cols} V3={v3_cols}")
        try:
            if args.dry_run:
                print(f"  [DRY] {v2}({v2_rows}) → {v3}({v3_rows}): {v2_rows} 행 복사 예정")
                processed += 1
                continue
            if v3_rows > 0 and args.force:
                cur.execute(f'DELETE FROM "{v3}"')
            cols_quoted = ", ".join(f'"{c}"' for c in v2_cols)
            cur.execute(f'INSERT INTO "{v3}" ({cols_quoted}) SELECT {cols_quoted} FROM "{v2}"')
            print(f"  [OK]  {v2}({v2_rows}) → {v3}: {cur.rowcount} 행 복사")
            processed += 1
        except sqlite3.Error as exc:
            print(f"  [FAIL] {v2} → {v3}: {exc}")
            errors += 1
            con.rollback()
            continue
    if not args.dry_run:
        con.commit()
    con.close()
    print(f"\n[OK] 처리 {processed} | skip {skipped} | 에러 {errors}")
    return 0 if errors == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="V3U_C strategy.db V2→V3 조건식 마이그레이션 (E7)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="strategy.db 경로 (기본 ./_database/strategy.db)")
    parser.add_argument("--target", default="stock",
                        help="V3 target prefix (stock|stock_etf|stock_etn|stock_usa|coin|future|future_nt|future_os|coin_future)")
    sub = parser.add_subparsers(dest="cmd")

    p_scan = sub.add_parser("scan", help="V2/V3 매핑 + rows 매트릭스 (read-only)")
    p_scan.add_argument("--output", help="JSON 매니페스트 출력 (선택)")

    p_mig = sub.add_parser("migrate", help="V2 데이터 → V3 테이블 복사 (백업 보유 필수)")
    p_mig.add_argument("--dry-run", action="store_true", help="시뮬 (실 변경 없음)")
    p_mig.add_argument("--force", action="store_true", help="V3에 데이터 있어도 덮어쓰기 / 백업 없이 강제")

    # legacy alias
    parser.add_argument("--scan", action="store_const", const="scan", dest="cmd_legacy")
    parser.add_argument("--migrate", action="store_const", const="migrate", dest="cmd_legacy")
    parser.add_argument("--output", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args(argv)
    cmd = args.cmd or args.cmd_legacy or "scan"
    if cmd == "scan":
        return cmd_scan(args)
    if cmd == "migrate":
        return cmd_migrate(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
