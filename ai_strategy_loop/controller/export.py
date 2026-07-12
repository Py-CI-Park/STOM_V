"""US-005 Phase 2b — 우승 전략 export (human-approved live-deploy gate).

루프 격리 DB에서 검증된 우승 buy/sell 전략을 PRODUCTION strategy.db로
복사한다. 이름은 namespaced(`AILOOP_<run>_g<gen>_buy`)에서 사람이 지정한
이름으로 de-namespace 된다.

설계 원칙(단순 + 안전):
  - dest_strategy_db는 **명시적 파라미터**다. 루프 env 오버라이드
    (STOM_CLI_DB_STRATEGY=loop DB)를 절대 따르지 않는다. 호출자가 운영 경로를
    명시적으로 넘겨야 한다(실수로 루프 DB에 쓰는 것 방지).
  - 운영 경로 기본값은 repo 루트의 `_database/strategy.db`이며, env가 아니라
    파일 위치에서 결정론적으로 해석한다.
  - export는 stockbuy/stocksell 테이블만 건드린다. 주문/계좌/라이브 경로
    모듈은 import하지도 호출하지도 않는다(이 모듈은 그런 import가 없다).
    이것이 사람 승인 후의 유일한 live-deploy 통로다.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

# repo 루트 = .../STOM_V.wt-dev (이 파일: .../ai_strategy_loop/controller/export.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
# 운영 strategy.db의 결정론적 기본 경로 (env 오버라이드와 무관).
PRODUCTION_STRATEGY_DB = _REPO_ROOT / "_database" / "strategy.db"


def _strip_namespace_marker(code: str) -> str:
    """namespaced 전략 코드를 그대로 반환한다.

    전략 코드 자체에는 이름이 박혀 있지 않다(이름은 DB index 컬럼에만 있다).
    따라서 코드는 변형 없이 그대로 옮긴다. 이 함수는 향후 코드 내 마커
    제거가 필요해질 경우의 단일 후크로 둔다(현재는 no-op).
    """
    return code


def _read_strategy_code(loop_db: str, name: str, kind: str) -> str:
    """루프 DB에서 (kind, name) 전략 코드를 읽어온다.

    Raises:
        KeyError: 전략이 없을 때.
    """
    table = "stockbuy" if kind == "buy" else "stocksell"
    loop_path = Path(loop_db).resolve()
    con = sqlite3.connect(f"file:{loop_path.as_posix()}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(f'PRAGMA table_info({table})')
        cols = [r[1] for r in cur.fetchall()]
        # 코드 컬럼은 named 컬럼 "전략코드"를 명시 선택한다. 없을 때만 위치 접근
        #   cols[1]로 폴백한다(엉뚱한 컬럼을 운영 DB에 쓰는 사고 방지).
        code_col = "전략코드" if "전략코드" in cols else (cols[1] if len(cols) >= 2 else "전략코드")
        row = cur.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "index" = ?', (name,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise KeyError(f"루프 DB에 전략이 없습니다: {kind}/{name} ({loop_db})")
    return row[0]


def _strategy_code_column(connection: sqlite3.Connection, table: str) -> str:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    if not rows:
        connection.execute(
            f'CREATE TABLE {table} ("index" TEXT PRIMARY KEY, "전략코드" TEXT)'
        )
        return "전략코드"
    columns = [str(row[1]) for row in rows]
    if "전략코드" in columns:
        return "전략코드"
    if len(columns) >= 2:
        return columns[1]
    raise sqlite3.OperationalError(f"missing strategy code column: {table}")


def _upsert_strategy(
    connection: sqlite3.Connection,
    table: str,
    name: str,
    code: str,
) -> str:
    code_column = _strategy_code_column(connection, table)
    exists = connection.execute(
        f'SELECT 1 FROM {table} WHERE "index" = ?',
        (name,),
    ).fetchone()
    if exists is None:
        connection.execute(
            f'INSERT INTO {table} ("index", "{code_column}") VALUES (?, ?)',
            (name, code),
        )
        return "created"
    connection.execute(
        f'UPDATE {table} SET "{code_column}" = ? WHERE "index" = ?',
        (code, name),
    )
    return "updated"


def export_winner(
    winner_buy: str,
    winner_sell: str,
    dest_strategy_db: Optional[str],
    user_buy_name: str,
    user_sell_name: str,
    *,
    loop_db: Optional[str] = None,
    expected_buy_code_hash: Optional[str] = None,
    expected_sell_code_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """우승 buy/sell 전략을 운영 strategy.db로 export 한다.

    Args:
        winner_buy/winner_sell: 루프 DB 내 namespaced 전략 이름.
        dest_strategy_db: 운영 strategy.db 경로(명시적). None이면 결정론적
            기본값 PRODUCTION_STRATEGY_DB를 쓴다 (env 오버라이드 무시).
        user_buy_name/user_sell_name: 운영 DB에 저장할 사람이 정한 이름.
        loop_db: 우승 전략을 읽어올 루프 DB 경로. None이면 bootstrap의
            루프 DB(STOM_CLI_DB_STRATEGY가 가리키는 격리 DB)를 쓴다.

    Returns:
        {"status": "ok", "dest_db", "buy", "sell"} 또는
        {"status": "error", "message"}.
    """
    # 운영 경로는 명시 파라미터 우선, 없으면 결정론적 기본값 (env 무시).
    dest = str(dest_strategy_db or PRODUCTION_STRATEGY_DB)

    # 루프 DB는 명시 파라미터 우선, 없으면 bootstrap 격리 DB.
    if loop_db is None:
        import ai_strategy_loop.bootstrap as bootstrap  # noqa: PLC0415
        loop_db = str(bootstrap.LOOP_DB_STRATEGY)
    loop_db = str(loop_db)

    # 안전 단언: 운영 경로와 루프 경로가 동일하면 export 의미가 없고 위험하다.
    if Path(dest).resolve() == Path(loop_db).resolve():
        return {
            "status": "error",
            "message": (
                "dest_strategy_db가 루프 DB와 동일합니다. 운영 strategy.db를 "
                "명시적으로 지정하세요(루프 DB로 export 금지)."
            ),
        }

    try:
        buy_code = _strip_namespace_marker(_read_strategy_code(loop_db, winner_buy, "buy"))
        sell_code = _strip_namespace_marker(_read_strategy_code(loop_db, winner_sell, "sell"))
    except (KeyError, sqlite3.Error) as exc:
        return {"status": "error", "message": str(exc)}
    actual_buy_hash = hashlib.sha256(buy_code.encode("utf-8")).hexdigest()
    actual_sell_hash = hashlib.sha256(sell_code.encode("utf-8")).hexdigest()
    if (
        expected_buy_code_hash is not None
        and actual_buy_hash != expected_buy_code_hash
    ) or (
        expected_sell_code_hash is not None
        and actual_sell_hash != expected_sell_code_hash
    ):
        return {
            "status": "error",
            "code": "source_code_hash_mismatch",
            "message": "winner source code changed after approval review",
        }

    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(dest)
        connection.execute("BEGIN IMMEDIATE")
        buy_action = _upsert_strategy(
            connection,
            "stockbuy",
            user_buy_name,
            buy_code,
        )
        sell_action = _upsert_strategy(
            connection,
            "stocksell",
            user_sell_name,
            sell_code,
        )
        connection.commit()
    except sqlite3.Error as exc:
        if connection is not None:
            connection.rollback()
        return {"status": "error", "message": f"strategy export failed: {exc}"}
    finally:
        if connection is not None:
            connection.close()

    return {
        "status": "ok",
        "dest_db": dest,
        "buy": {"name": user_buy_name, "action": buy_action},
        "sell": {"name": user_sell_name, "action": sell_action},
    }
