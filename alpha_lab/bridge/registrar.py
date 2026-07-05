"""alpha_lab 조건식 → 전략 DB 등록기 (INSERT-only, 연구 레인 전용).

scripts/register_chart_sulsa_conditions.py 의 실측 계약을 미러한다:
- 테이블: stockbuy(매수) / stocksell(매도), 컬럼 "index"(이름 TEXT), "전략코드"(TEXT).
  (utility/database_check.py 실측 DDL: CREATE TABLE "stockbuy" ( "index" TEXT, "전략코드" TEXT ))
- INSERT-only: 기존 행은 어떤 방식으로도 변형하지 않는다(UPDATE/DELETE 금지).
- 실쓰기 전 DB 파일 백업 복사를 강제한다(쓸 것이 없으면 백업도 만들지 않는다).
- 동명이 어느 한 테이블에라도 존재하면 그 항목 쌍 전체를 스킵하고 conflicts에
  기록한다(부분 삽입 금지). 따라서 재실행은 멱등(inserted 0)이다.

규율: 이름은 'ALP_' 접두 강제(연구 산출물 네임스페이스 격리). 현재시각은
호출자가 now 인자로 주입한다(내부 datetime.now() 금지). print 금지(logging).
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import sqlite3
from pathlib import Path

logger = logging.getLogger(__name__)

NAME_PREFIX = "ALP_"
TABLE_BY_SIDE: dict[str, str] = {"buy": "stockbuy", "sell": "stocksell"}
NAME_COLUMN = "index"
CODE_COLUMN = "전략코드"
_EXPR_KEY_BY_TABLE: dict[str, str] = {"stockbuy": "buy_expr", "stocksell": "sell_expr"}


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_items(items: list) -> None:
    """배치 전체를 사전 검증한다 — 위반 1건이라도 있으면 DB 접근 전에 ValueError.

    검사: dict 여부, 'ALP_' 접두, buy_expr/sell_expr 비어있지 않은 str,
    배치 내 이름 중복.
    """
    if not isinstance(items, list) or not items:
        raise ValueError("items는 비어있지 않은 list여야 합니다: %r" % (items,))
    seen: set[str] = set()
    for pos, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("items[%d]가 dict가 아닙니다: %r" % (pos, item))
        name = item.get("name")
        if not isinstance(name, str) or not name.startswith(NAME_PREFIX):
            raise ValueError(
                "items[%d] 이름은 %r 접두가 강제됩니다: %r" % (pos, NAME_PREFIX, name)
            )
        for key in ("buy_expr", "sell_expr"):
            expr = item.get(key)
            if not isinstance(expr, str) or not expr.strip():
                raise ValueError(
                    "items[%d](%s) %s가 비어있지 않은 str이 아닙니다: %r"
                    % (pos, name, key, expr)
                )
        if name in seen:
            raise ValueError("배치 내 이름 중복: %r" % name)
        seen.add(name)


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    """존재 확인용 연결은 read-only URI로 열어 변형 가능성 자체를 차단한다."""
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _existing_names(con: sqlite3.Connection, table: str) -> set:
    if table not in TABLE_BY_SIDE.values():
        raise ValueError("unexpected table: %s" % table)
    sql = 'SELECT "%s" FROM "%s"' % (NAME_COLUMN, table)
    return {row[0] for row in con.execute(sql).fetchall()}


def _split_plan(items: list, names_by_table: dict) -> tuple:
    """(to_insert, conflicts)로 나눈다. 동명이 한 테이블에라도 있으면 conflict."""
    to_insert: list = []
    conflicts: list = []
    for item in items:
        name = item["name"]
        hit_tables = sorted(
            table for table, names in names_by_table.items() if name in names
        )
        if hit_tables:
            conflicts.append(
                {"name": name, "reason": "name_exists", "tables": hit_tables}
            )
        else:
            to_insert.append(item)
    return to_insert, conflicts


def _backup_db(db_path: Path, backup_dir: Path, now) -> Path:
    """실쓰기 직전 DB 파일 사본을 backup_dir에 만든다(동명 충돌 시 suffix)."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%S")
    base = "%s.bak.alpha_lab_%s" % (db_path.name, stamp)
    candidate = backup_dir / base
    counter = 2
    while candidate.exists():
        candidate = backup_dir / ("%s-%d" % (base, counter))
        counter += 1
    shutil.copy2(db_path, candidate)
    return candidate


def _apply_inserts(con: sqlite3.Connection, to_insert: list) -> list:
    """계획된 항목만 INSERT한다(테이블별 1행씩, 쌍 단위). inserted 기록 반환."""
    inserted: list = []
    for item in to_insert:
        for table in ("stockbuy", "stocksell"):
            sql = 'INSERT INTO "%s" ("%s", "%s") VALUES (?, ?)' % (
                table, NAME_COLUMN, CODE_COLUMN,
            )
            con.execute(sql, (item["name"], item[_EXPR_KEY_BY_TABLE[table]]))
        inserted.append(
            {
                "name": item["name"],
                "tables": ["stockbuy", "stocksell"],
                "buy_sha256": _sha256_text(item["buy_expr"]),
                "sell_sha256": _sha256_text(item["sell_expr"]),
                "meta": item.get("meta"),
            }
        )
    con.commit()
    return inserted


def register_conditions(db_path, items: list, *, backup_dir, now) -> dict:
    """조건식 배치를 전략 DB에 INSERT-only로 등록한다.

    items: [{name, buy_expr, sell_expr, meta}] — name은 'ALP_' 접두 강제.
    buy_expr→stockbuy, sell_expr→stocksell에 같은 이름으로 쌍 저장한다.
    동명이 어느 테이블에든 이미 있으면 쌍 전체 스킵 + conflicts 기록(멱등).
    실쓰기 전 backup_dir에 DB 파일 백업을 강제한다(삽입 0건이면 백업 생략).
    now: 호출자 주입 datetime(백업 파일명 스탬프에만 사용).

    반환: {"inserted": [...], "conflicts": [...], "backup_path": str | None}
    """
    _validate_items(items)
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError("전략 DB 파일이 없습니다: %s" % db_file)

    read_con = _open_readonly(db_file)
    try:
        names_by_table = {
            table: _existing_names(read_con, table)
            for table in TABLE_BY_SIDE.values()
        }
    finally:
        read_con.close()

    to_insert, conflicts = _split_plan(items, names_by_table)
    backup_path = None
    inserted: list = []
    if to_insert:
        backup_path = _backup_db(db_file, Path(backup_dir), now)
        write_con = sqlite3.connect(str(db_file))
        try:
            inserted = _apply_inserts(write_con, to_insert)
        finally:
            write_con.close()
    logger.info(
        "register_conditions db=%s inserted=%d conflicts=%d backup=%s",
        db_file, len(inserted), len(conflicts), backup_path,
    )
    return {
        "inserted": inserted,
        "conflicts": conflicts,
        "backup_path": str(backup_path) if backup_path else None,
    }
