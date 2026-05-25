"""MEDIUM-2 — export _read_strategy_code 컬럼 선택 단위 테스트 (네트워크 없음).

검증:
  - "전략코드" named 컬럼이 있으면 위치(cols[1])가 아니라 named 컬럼을 읽는다
    (엉뚱한 컬럼을 운영 DB에 쓰는 사고 방지).
  - named 컬럼이 없을 때만 위치 cols[1] 폴백을 쓴다.

테이블 레이아웃을 일부러 [index, 다른컬럼, 전략코드]로 만들어, 위치 접근이면
'다른컬럼' 값을, named 접근이면 '전략코드' 값을 읽게 해 둘을 구분한다.
"""

import os
import sqlite3
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.controller.export import _read_strategy_code  # noqa: E402


def _make_db(path, *, with_named_column: bool):
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        if with_named_column:
            # [index, 다른컬럼(decoy at cols[1]), 전략코드]
            cur.execute(
                'CREATE TABLE stockbuy ("index" TEXT, "다른컬럼" TEXT, "전략코드" TEXT)'
            )
            cur.execute(
                'INSERT INTO stockbuy ("index", "다른컬럼", "전략코드") VALUES (?, ?, ?)',
                ("AILOOP_x_g0_buy", "WRONG_DECOY", "REAL_STRATEGY_CODE"),
            )
        else:
            # named 컬럼 없음 → 위치 cols[1] 폴백. [index, 코드]
            cur.execute('CREATE TABLE stockbuy ("index" TEXT, "코드본문" TEXT)')
            cur.execute(
                'INSERT INTO stockbuy ("index", "코드본문") VALUES (?, ?)',
                ("AILOOP_x_g0_buy", "FALLBACK_CODE"),
            )
        con.commit()
    finally:
        con.close()


def test_reads_named_column_not_positional(tmp_path):
    db = str(tmp_path / "loop.db")
    _make_db(db, with_named_column=True)
    code = _read_strategy_code(db, "AILOOP_x_g0_buy", "buy")
    # named "전략코드"를 읽어야 한다 — 위치 cols[1]('다른컬럼')의 decoy가 아님.
    assert code == "REAL_STRATEGY_CODE"
    assert code != "WRONG_DECOY"


def test_positional_fallback_when_no_named_column(tmp_path):
    db = str(tmp_path / "loop.db")
    _make_db(db, with_named_column=False)
    code = _read_strategy_code(db, "AILOOP_x_g0_buy", "buy")
    # named 컬럼이 없으니 위치 cols[1] 폴백.
    assert code == "FALLBACK_CODE"


def test_missing_strategy_raises_keyerror(tmp_path):
    import pytest

    db = str(tmp_path / "loop.db")
    _make_db(db, with_named_column=True)
    with pytest.raises(KeyError):
        _read_strategy_code(db, "does_not_exist", "buy")
