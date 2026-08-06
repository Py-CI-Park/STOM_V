# -*- coding: utf-8 -*-
"""봉인(seal) 테스트의 환경 전제 검사기.

배경: 챔피언 봉인 테스트들은 `strategy.db` 의 특정 전략 행을 읽어 SHA 를 대조한다.
그런데 skip 조건이 **DB 파일 존재**만 확인해서, 파일은 있고 **행이 없는** 워크트리
(전략이 다른 레인에서만 등록된 경우)에서 ValueError/KeyError 로 실패했다 —
"검증 실패"가 아니라 "검증 불가"인데 실패로 보고되던 것이다.

계약:
  - 행이 **없으면** skip (환경 전제 미충족 — 이 워크트리에서는 검증할 대상이 없다).
  - 행이 **있으면** 반드시 실행 (있는데 다르면 실패해야 한다 — 봉인의 존재 이유).

읽기 전용 접근만 하며 DB 를 만들거나 수정하지 않는다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


def strategy_row_exists(db_path: str | Path, table: str, index_name: str) -> bool:
    """`table` 에 `index_name` 행이 존재하고 전략코드가 비어 있지 않은가."""
    path = Path(db_path)
    if not path.exists():
        return False
    try:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error:
        return False
    try:
        row = conn.execute(
            f'SELECT "전략코드" FROM {table} WHERE "index" = ?', (index_name,)
        ).fetchone()
    except sqlite3.Error:
        return False
    finally:
        conn.close()
    return bool(row and row[0])


def requires_strategy_row(db_path: str | Path, table: str, index_name: str):
    """행이 없을 때만 skip 하는 마커 (있으면 반드시 실행)."""
    return pytest.mark.skipif(
        not strategy_row_exists(db_path, table, index_name),
        reason=f"{table}.{index_name} 행이 이 워크트리 strategy.db 에 없음 — 검증 대상 부재",
    )
