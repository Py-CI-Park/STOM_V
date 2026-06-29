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
def _run_database_check_in_tmp(tmp_path, monkeypatch):
    """runtime DB를 건드리지 않도록 database_check 경로를 tmp_path로 격리 실행한다."""
    from utility.db_control import database_check as dbc

    db_dir = tmp_path / "database"
    log_dir = tmp_path / "log"
    graph_dir = tmp_path / "graph"
    back_temp_dir = tmp_path / "back_temp"

    monkeypatch.setattr(dbc, "DB_PATH", str(db_dir))
    monkeypatch.setattr(dbc, "LOG_PATH", str(log_dir))
    monkeypatch.setattr(dbc, "GRAPH_PATH", str(graph_dir))
    monkeypatch.setattr(dbc, "BACK_TEMP", str(back_temp_dir))
    monkeypatch.setattr(dbc, "DB_SETTING", str(db_dir / "setting.db"))
    monkeypatch.setattr(dbc, "DB_CODE_INFO", str(db_dir / "code_info.db"))
    monkeypatch.setattr(dbc, "DB_STRATEGY", str(db_dir / "strategy.db"))
    monkeypatch.setattr(dbc, "DB_TRADELIST", str(db_dir / "tradelist.db"))
    monkeypatch.setattr(dbc, "read_key", lambda: "test-key")
    monkeypatch.setattr(dbc, "write_key", lambda: None)

    ok, message = dbc.database_check()
    assert ok, message
    return dbc



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


def test_d2_18_exchanges_baseline(tmp_path, monkeypatch) -> None:
    """D2: ACCOUNT/TELE/STG/BACT 데이터가 모두 18개 거래소 기반이다."""
    _run_database_check_in_tmp(tmp_path, monkeypatch)

    db = tmp_path / "database" / "setting.db"
    conn = sqlite3.connect(str(db))
    counts = {}
    for table in ("account", "telegram", "strategy", "back"):
        cur = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
        counts[table] = cur.fetchone()[0]
    conn.close()

    for name, cnt in counts.items():
        assert cnt == 18, f"{name} 행 수 mismatch: {cnt} (기대 18)"


def test_d2_bact_data_index_unique_1_to_18(tmp_path, monkeypatch) -> None:
    """D2: back 테이블의 index 컬럼이 1~18 unique."""
    _run_database_check_in_tmp(tmp_path, monkeypatch)

    db = tmp_path / "database" / "setting.db"
    conn = sqlite3.connect(str(db))
    cur = conn.execute('SELECT "index" FROM back ORDER BY "index"')
    indices = [row[0] for row in cur.fetchall()]
    conn.close()

    assert len(set(indices)) == 18, "back index 중복 발견"
    assert min(indices) == 1, f"back index 최솟값 1 기대, {min(indices)}"
    assert max(indices) == 18, f"back index 최댓값 18 기대, {max(indices)}"


def test_d3_database_check_callable(tmp_path, monkeypatch) -> None:
    """D3: database_check 함수가 tmp_path 격리 상태에서 호출 가능하다."""
    from utility.db_control import database_check as dbc

    assert callable(dbc.database_check), "database_check는 callable이어야 함"
    _run_database_check_in_tmp(tmp_path, monkeypatch)


def test_d3_temp_sqlite_supports_18_row_insert(tmp_path, monkeypatch) -> None:
    """D3: database_check가 생성한 18거래소 account row 구조를 재삽입할 수 있다."""
    _run_database_check_in_tmp(tmp_path, monkeypatch)

    setting_db = tmp_path / "database" / "setting.db"
    conn = sqlite3.connect(str(setting_db))
    rows = conn.execute('SELECT * FROM account ORDER BY "index"').fetchall()
    columns = [row[1] for row in conn.execute('PRAGMA table_info(account)').fetchall()]
    conn.close()

    db = tmp_path / "test_18_exchanges.db"
    conn = sqlite3.connect(str(db))
    cols = ", ".join(f'"{c}"' for c in columns)
    placeholders = ", ".join(["?"] * len(columns))
    conn.execute(f"CREATE TABLE accounts ({cols})")
    conn.executemany(f"INSERT INTO accounts VALUES ({placeholders})", rows)
    conn.commit()

    cur = conn.execute("SELECT COUNT(*) FROM accounts")
    assert cur.fetchone()[0] == 18, "18행 INSERT 후 카운트 불일치"
    conn.close()
