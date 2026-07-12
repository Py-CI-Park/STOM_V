"""A-6 — seed_db few-shot 골드 우선순위/임시전략 배제 계약 테스트."""
import sqlite3

from ai_strategy_loop.brain.exemplar_pool import _seed_db_rank, select_exemplars


def _make_seed_db(path, rows):
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE stockbuy ("index" TEXT, 전략코드 TEXT)')
    con.executemany('INSERT INTO stockbuy VALUES (?, ?)', rows)
    con.commit()
    con.close()


def test_rank_orders_gold_then_family_then_misc():
    ordered = sorted(
        ["20250715_Study", "Min_B_Study_250824", "Tick_B_905",
         "Tick_B_902_905_Update_2", "C_T_900_920_U2_B", "CSS_V7_MIN_B_MASTER_0900_1518"],
        key=_seed_db_rank,
    )
    assert ordered[0] == "Tick_B_902_905_Update_2"   # 골드 exact 최우선
    assert ordered[1] == "C_T_900_920_U2_B"          # 골드 exact 2순위
    assert ordered[-1] == "20250715_Study"           # 기타 최후순위


def test_select_exemplars_prefers_gold_and_excludes_auto_tmp(tmp_path):
    db = str(tmp_path / "strategy.db")
    _make_seed_db(db, [
        # 테이블 순서상 앞에 있어도 임시 전략은 배제, study는 후순위여야 한다.
        ("__AUTO_TMP__Auto_B_Pilot01_1", "if 현재가 > 100:\n    매수 = True\nif 매수:\n    self.Buy()"),
        ("20250715_Study", "if 체결강도 > 90:\n    매수 = True\nif 매수:\n    self.Buy()"),
        ("Tick_B_902_905_Update_2", "if 현재가 > 시가:\n    매수 = True\nif 매수:\n    self.Buy()"),
        ("Min_B_Study_250824", "if 등락율 > 3:\n    매수 = True\nif 매수:\n    self.Buy()"),
    ])
    picked = select_exemplars(kind="buy", timeframe="min", k=2, source="seed_db", db_path=db)
    assert len(picked) == 2
    assert "현재가 > 시가" in picked[0]          # 골드 시드가 1순위
    assert all("__AUTO_TMP__" not in c for c in picked)
    # k=4로 넓혀도 임시 전략은 절대 포함되지 않는다.
    picked_all = select_exemplars(kind="buy", timeframe="min", k=4, source="seed_db", db_path=db)
    assert len(picked_all) == 3
