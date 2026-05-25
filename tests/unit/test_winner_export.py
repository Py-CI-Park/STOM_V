"""US-005 Phase 2b — 우승 전략 export 단위 테스트 (human-approved gate).

검증:
  (a) export 후 TEMP 운영 DB에 사용자 이름으로 전략 행이 존재한다.
  (b) 루프 DB는 export로 변경되지 않는다 (read-only 소스).
  (c) export 경로는 주문/계좌/라이브 모듈을 import/접촉하지 않는다.
  (d) dest가 루프 DB와 동일하면 거부한다 (안전 단언).
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.controller.export import export_winner  # noqa: E402


def _make_loop_db(path, buy_name, sell_name, buy_code, sell_code):
    """루프 DB를 만들고 namespaced buy/sell 전략을 심는다."""
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute('CREATE TABLE stockbuy ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        cur.execute('CREATE TABLE stocksell ("index" TEXT PRIMARY KEY, "전략코드" TEXT)')
        cur.execute('INSERT INTO stockbuy VALUES (?, ?)', (buy_name, buy_code))
        cur.execute('INSERT INTO stocksell VALUES (?, ?)', (sell_name, sell_code))
        con.commit()
    finally:
        con.close()


def _read_strategy(path, table, name):
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        cur.execute('PRAGMA table_info(%s)' % table)
        cols = [r[1] for r in cur.fetchall()]
        code_col = cols[1]
        row = cur.execute(
            f'SELECT "{code_col}" FROM {table} WHERE "index" = ?', (name,)
        ).fetchone()
    finally:
        con.close()
    return row[0] if row else None


def test_export_writes_user_named_rows_to_production_db(tmp_path):
    """(a) export 후 운영 DB에 사용자 이름으로 buy/sell이 존재한다."""
    loop_db = str(tmp_path / "loop_strategies.db")
    dest_db = str(tmp_path / "production_strategy.db")

    buy_ns = "AILOOP_run1_g3_buy"
    sell_ns = "AILOOP_run1_g3_sell"
    buy_code = "buy_var = 등락율\nmae = 1"
    sell_code = "sell_var = 수익률\nmae = 2"
    _make_loop_db(loop_db, buy_ns, sell_ns, buy_code, sell_code)

    res = export_winner(
        buy_ns, sell_ns, dest_db,
        user_buy_name="MyWinningBuy", user_sell_name="MyWinningSell",
        loop_db=loop_db,
    )
    assert res["status"] == "ok", res
    assert res["dest_db"] == dest_db

    # 운영 DB에 사용자 이름으로 코드가 그대로 들어갔는지.
    assert _read_strategy(dest_db, "stockbuy", "MyWinningBuy") == buy_code
    assert _read_strategy(dest_db, "stocksell", "MyWinningSell") == sell_code


def test_export_leaves_loop_db_untouched(tmp_path):
    """(b) export는 루프 DB(소스)를 변경하지 않는다."""
    loop_db = str(tmp_path / "loop_strategies.db")
    dest_db = str(tmp_path / "production_strategy.db")
    buy_ns, sell_ns = "AILOOP_r_g0_buy", "AILOOP_r_g0_sell"
    _make_loop_db(loop_db, buy_ns, sell_ns, "b=1", "s=1")

    before = os.path.getmtime(loop_db)
    before_size = os.path.getsize(loop_db)
    before_buy = _read_strategy(loop_db, "stockbuy", buy_ns)

    export_winner(buy_ns, sell_ns, dest_db, "UB", "US", loop_db=loop_db)

    # 내용/크기 불변 (export는 읽기만 한다).
    assert _read_strategy(loop_db, "stockbuy", buy_ns) == before_buy
    assert os.path.getsize(loop_db) == before_size
    # 루프 DB에 사용자 이름이 새로 생기지 않았는지.
    assert _read_strategy(loop_db, "stockbuy", "UB") is None
    _ = before  # mtime은 OS 캐시로 신뢰도 낮아 size/content로 판정.


def test_export_does_not_import_order_account_live_modules(tmp_path, monkeypatch):
    """(c) export가 주문/계좌/라이브 모듈을 import하지 않는다.

    export 호출 동안 새로 import된 모듈명을 스냅샷으로 비교해, 위험 키워드를
    포함한 모듈이 새로 import되지 않았음을 단언한다.
    """
    loop_db = str(tmp_path / "loop_strategies.db")
    dest_db = str(tmp_path / "production_strategy.db")
    buy_ns, sell_ns = "AILOOP_r_g1_buy", "AILOOP_r_g1_sell"
    _make_loop_db(loop_db, buy_ns, sell_ns, "b=1", "s=1")

    before = set(sys.modules.keys())
    export_winner(buy_ns, sell_ns, dest_db, "UB", "US", loop_db=loop_db)
    after = set(sys.modules.keys())
    newly = after - before

    # 라이브 매매/주문/계좌 경로를 시사하는 모듈이 새로 로드되면 실패.
    forbidden = ("order", "account", "trader", "live", "kiwoom", "trade.")
    offending = [
        m for m in newly
        if any(tok in m.lower() for tok in forbidden)
    ]
    assert not offending, f"export가 위험 모듈을 import함: {offending}"


def test_export_refuses_when_dest_equals_loop_db(tmp_path):
    """(d) dest가 루프 DB와 동일하면 거부 (실수로 루프 DB로 export 방지)."""
    loop_db = str(tmp_path / "loop_strategies.db")
    buy_ns, sell_ns = "AILOOP_r_g0_buy", "AILOOP_r_g0_sell"
    _make_loop_db(loop_db, buy_ns, sell_ns, "b=1", "s=1")

    res = export_winner(buy_ns, sell_ns, loop_db, "UB", "US", loop_db=loop_db)
    assert res["status"] == "error"
    assert "동일" in res["message"]


def test_export_errors_on_missing_strategy(tmp_path):
    """루프 DB에 없는 전략을 export하면 에러를 반환한다 (크래시 아님)."""
    loop_db = str(tmp_path / "loop_strategies.db")
    dest_db = str(tmp_path / "production_strategy.db")
    _make_loop_db(loop_db, "AILOOP_r_g0_buy", "AILOOP_r_g0_sell", "b=1", "s=1")

    res = export_winner("NOPE_buy", "NOPE_sell", dest_db, "UB", "US", loop_db=loop_db)
    assert res["status"] == "error"
