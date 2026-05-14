"""V3U 데이터 레이어 통합 테스트 (잔고 dt-guard / 18거래소 / 빈 DB 자동생성).

Constraint: V3 official source 0줄 수정.
Constraint: 본 워크트리의 _database/ runtime DB는 절대 건드리지 않는다.
            모든 DB 작업은 tmp_path에서 수행한다.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


def test_b5_balance_dt_guard_simulation() -> None:
    """B5: trade/base_receiver.py의 'pre_dt is None or dt > pre_dt' 가드를 시뮬한다.

    동일한 dt가 반복되면 INSERT 1회만, 새 dt가 들어오면 추가 INSERT.
    실 큐 push 대신 카운터로 시뮬해 가드 로직 정확성만 검증한다.
    """
    pre_dt = None
    fired = 0
    test_inputs = [
        (100, "2026-05-12 09:00:01"),
        (100, "2026-05-12 09:00:01"),  # dup
        (100, "2026-05-12 09:00:02"),
        (100, "2026-05-12 09:00:02"),  # dup
        (100, "2026-05-12 09:00:03"),
    ]
    for _code, dt in test_inputs:
        if pre_dt is None or dt > pre_dt:
            fired += 1
            pre_dt = dt
    assert fired == 3, f"3개 unique dt 기대, {fired}회 fire"


def test_b5_balance_dt_guard_pattern_in_source() -> None:
    """B5 정적: trade/base_receiver.py에 dt-guard 패턴과 잔고갱신 큐 push가 존재한다.

    V3.18 baseline 실측:
    - dt-guard `pre_dt is None or dt > pre_dt` 2회 (line 237, 315)
    - `traderQ.put(('잔고갱신'` 3회 (line 238, 316, 504)
    line 504는 dt-guard 없이 unconditional push (is_tick + 주문/잔고 코드 분기 내부).
    drift 시 audit log 갱신 신호.
    """
    src = Path("trade/base_receiver.py").read_text(encoding="utf-8")
    guard_count = src.count("pre_dt is None or dt > pre_dt")
    jango_put = src.count("traderQ.put(('잔고갱신'")
    assert guard_count >= 2, f"dt-guard 패턴 2회 이상 기대, {guard_count}회"
    assert jango_put >= 3, f"잔고갱신 큐 push 3회 이상 기대, {jango_put}회"


def test_d2_18_exchanges_baseline() -> None:
    """D2: ACCOUNT/TELE/STG/BACT 데이터가 모두 18개 거래소 기반이다."""
    from utility.db_control import database_check as dbc

    counts = {
        "ACCOUNT_DATA": len(dbc.ACCOUNT_DATA),
        "TELE_DATA": len(dbc.TELE_DATA),
        "STG_DATA": len(dbc.STG_DATA),
        "BACT_DATA": len(dbc.BACT_DATA),
    }
    for name, cnt in counts.items():
        assert cnt == 18, f"{name} 행 수 mismatch: {cnt} (기대 18)"


def test_d2_bact_data_index_unique_1_to_18() -> None:
    """D2: BACT_DATA의 index 컬럼이 1~18 unique."""
    from utility.db_control import database_check as dbc

    indices = [row[0] for row in dbc.BACT_DATA]
    assert len(set(indices)) == 18, "BACT index 중복 발견"
    assert min(indices) == 1, f"BACT index 최솟값 1 기대, {min(indices)}"
    assert max(indices) == 18, f"BACT index 최댓값 18 기대, {max(indices)}"


def test_d3_database_check_callable() -> None:
    """D3: database_check 함수가 호출 가능 시그니처를 가진다.

    실제 DB 생성 호출은 사용자 환경(D1)에 영향을 주므로 callable 검증까지만.
    """
    from utility.db_control import database_check as dbc

    assert callable(dbc.database_check), "database_check는 callable이어야 함"
    # 모듈 상수 노출
    assert hasattr(dbc, "MAIN_CLOUMNS")
    assert hasattr(dbc, "MAIN_DATA")
    assert hasattr(dbc, "ACCOUNT_CLOUMNS")
    assert hasattr(dbc, "ACCOUNT_DATA")


def test_d3_temp_sqlite_supports_18_row_insert(tmp_path) -> None:
    """D3: 18거래소 row가 sqlite에 INSERT 가능한 구조다 (스키마 검증)."""
    from utility.db_control import database_check as dbc

    db = tmp_path / "test_18_exchanges.db"
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()

    # ACCOUNT 테이블 스키마 추론
    cols = ", ".join(f'"{c}"' for c in dbc.ACCOUNT_CLOUMNS)
    placeholders = ", ".join(["?"] * len(dbc.ACCOUNT_CLOUMNS))
    cur.execute(f"CREATE TABLE accounts ({cols})")
    cur.executemany(f"INSERT INTO accounts VALUES ({placeholders})", dbc.ACCOUNT_DATA)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM accounts")
    assert cur.fetchone()[0] == 18, "18행 INSERT 후 카운트 불일치"
    conn.close()
