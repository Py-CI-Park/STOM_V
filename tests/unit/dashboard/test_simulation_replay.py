"""Chart simulation replay engine + inventory routes — PR3.

합성 일일 DB(tmp_path, 2종목×수백 행)로 검증:
- replay_engine.load_replay: 시간순 병합·tick agg 집계·seek 인덱스.
- /sim/days·/sim/stocks: 인벤토리·등락순·이름 결합(code_info).

실DB/백테 미사용: tmp SQLite 만 쓴다(기존 dashboard 테스트 패턴).
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.dashboard import replay_engine as RE  # noqa: E402
from ai_strategy_loop.dashboard import simulation_api as SA  # noqa: E402

# 일일 DB candle 컬럼(선두 10열 — load_code_rows 가 읽는 것).
_MIN_COLS = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "분당매수수량", "분당매도수량",
]
_TICK_COLS = [
    "현재가", "시가", "고가", "저가", "등락율", "당일거래대금",
    "체결강도", "초당매수수량", "초당매도수량",
]


def _make_daily_db(path: Path, src: str, tables: dict) -> None:
    """합성 일일 DB 를 만든다. tables = {code: [(index, current, open, high, low, change, value, strength, buyq, sellq)...]}."""
    cols = _TICK_COLS if src == "tick" else _MIN_COLS
    con = sqlite3.connect(str(path))
    # moneytop(요약 테이블) — 종목 테이블 목록에서 제외돼야 한다.
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    for code, rows in tables.items():
        coldef = ", ".join(f'"{c}" REAL' for c in cols)
        con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
        placeholders = ", ".join("?" for _ in range(len(cols) + 1))
        con.executemany(f'INSERT INTO "{code}" VALUES ({placeholders})', rows)
    con.commit()
    con.close()


@pytest.fixture
def synthetic_min_db(monkeypatch, tmp_path):
    """min 일일 DB(20250102) 2종목 — A005930 3행, A000660 2행(시간 일부 겹침)."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    # index = YYYYMMDDHHMM (12자리). 09:00, 09:01, 09:02.
    tables = {
        "005930": [
            (202501020900, 100.0, 99.0, 101.0, 98.0, 1.0, 5000.0, 110.0, 30.0, 20.0),
            (202501020901, 102.0, 100.0, 103.0, 100.0, 3.0, 6000.0, 120.0, 40.0, 25.0),
            (202501020902, 101.0, 102.0, 102.0, 100.0, 2.0, 5500.0, 105.0, 35.0, 30.0),
        ],
        "000660": [
            (202501020900, 50.0, 49.0, 51.0, 49.0, -1.0, 3000.0, 90.0, 15.0, 18.0),
            (202501020902, 52.0, 50.0, 53.0, 50.0, 4.0, 3500.0, 130.0, 22.0, 12.0),
        ],
    }
    _make_daily_db(db_dir / "stock_min_20250102.db", "min", tables)
    # code_info.db
    ci = db_dir / "code_info.db"
    con = sqlite3.connect(str(ci))
    con.execute('CREATE TABLE stockinfo ("index" TEXT, "종목명" TEXT, "코스닥" INTEGER)')
    con.executemany(
        'INSERT INTO stockinfo VALUES (?, ?, ?)',
        [("005930", "삼성전자", 0), ("000660", "SK하이닉스", 0)],
    )
    con.commit()
    con.close()
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_CODE_INFO_DB", ci)
    return db_dir


@pytest.fixture
def synthetic_tick_db(monkeypatch, tmp_path):
    """tick 일일 DB(20250102) 1종목 — 09:00:00~09:00:25 사이 여러 행(agg 검증용)."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    rows = []
    base = 20250102090000
    for i, sec in enumerate([0, 3, 7, 11, 14, 22, 25]):
        idx = base + sec  # ...090000 + sec.
        price = 100.0 + i
        rows.append((idx, price, price - 1, price + 2, price - 2, float(i), 1000.0 + i, 100.0 + i, 10.0, 5.0))
    _make_daily_db(db_dir / "stock_tick_20250102.db", "tick", {"005930": rows})
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    return db_dir


class TestInventoryRoutes:
    def test_days_lists_synthetic_date(self, synthetic_min_db):
        out = SA.sim_days("min")
        assert out["days"] == [20250102]
        assert out["count"] == 1
        assert out["src"] == "min"

    def test_days_empty_for_missing_src(self, synthetic_min_db):
        out = SA.sim_days("tick")  # tick DB 없음 → 빈.
        assert out["days"] == []
        assert out["count"] == 0

    def test_stocks_sorted_by_change_with_names(self, synthetic_min_db):
        out = SA.sim_stocks(20250102, "min")
        assert out["count"] == 2
        # 마지막 행 등락율: 005930=2.0, 000660=4.0 → 000660 먼저(내림차순).
        codes = [s["code"] for s in out["stocks"]]
        assert codes == ["000660", "005930"]
        first = out["stocks"][0]
        assert first["name"] == "SK하이닉스"
        assert first["last_change_pct"] == 4.0

    def test_stocks_excludes_moneytop(self, synthetic_min_db):
        out = SA.sim_stocks(20250102, "min")
        assert "moneytop" not in [s["code"] for s in out["stocks"]]

    def test_stocks_graceful_on_bad_date(self, synthetic_min_db):
        out = SA.sim_stocks(0, "min")
        assert out["stocks"] == []
        assert out["count"] == 0


class TestReplayMerge:
    def test_min_merges_codes_in_time_order(self, synthetic_min_db):
        rd = RE.load_replay(20250102, "min", ["005930", "000660"], agg_sec=10)
        assert rd.codes == ["005930", "000660"]
        # 3 distinct slots: 0900, 0901, 0902.
        times = [f["t"] for f in rd.frames]
        assert times == sorted(times)
        assert times == [90000, 90100, 90200]
        # 0900 슬롯엔 두 종목 모두, 0901 엔 005930 만.
        f0 = rd.frames[0]
        assert {it["code"] for it in f0["items"]} == {"005930", "000660"}
        f1 = rd.frames[1]
        assert {it["code"] for it in f1["items"]} == {"005930"}

    def test_min_bar_ohlc_mapping(self, synthetic_min_db):
        rd = RE.load_replay(20250102, "min", ["005930"], agg_sec=10)
        bar = rd.frames[0]["items"][0]
        # 첫 행: current=100, open=99, high=101, low=98 → o=open, c=current.
        assert bar["o"] == 99.0
        assert bar["c"] == 100.0
        assert bar["h"] == 101.0
        assert bar["l"] == 98.0
        # vol = buyq + sellq = 30 + 20.
        assert bar["vol"] == 50.0

    def test_seek_index_jumps_to_time(self, synthetic_min_db):
        rd = RE.load_replay(20250102, "min", ["005930"], agg_sec=10)
        assert rd.seek_index(90000) == 0
        assert rd.seek_index(90100) == 1
        assert rd.seek_index(90200) == 2
        assert rd.seek_index(90150) == 2  # 사이값 → 다음 슬롯.
        assert rd.seek_index(160000) == rd.bars_total  # 범위 밖 → 끝.

    def test_empty_for_missing_code(self, synthetic_min_db):
        rd = RE.load_replay(20250102, "min", ["999999"], agg_sec=10)
        assert rd.bars_total == 0
        assert rd.codes == []

    def test_caps_at_four_codes(self, synthetic_min_db):
        rd = RE.load_replay(20250102, "min", ["005930", "000660", "x", "y", "z"], agg_sec=10)
        # 입력은 4개로 잘리고, 존재하는 2개만 valid.
        assert set(rd.codes) <= {"005930", "000660"}


class TestTickAggregation:
    def test_tick_aggregates_into_buckets(self, synthetic_tick_db):
        rd = RE.load_replay(20250102, "tick", ["005930"], agg_sec=10)
        # 초: 0,3,7 (버킷 09:00:00), 11,14 (09:00:10), 22,25 (09:00:20) → 3 버킷.
        times = [f["t"] for f in rd.frames]
        assert times == [90000, 90010, 90020]

    def test_tick_bucket_ohlc(self, synthetic_tick_db):
        rd = RE.load_replay(20250102, "tick", ["005930"], agg_sec=10)
        # 첫 버킷(초 0,3,7 → price 100,101,102): o=100(첫), c=102(마지막), h>=102, l<=100.
        bar0 = rd.frames[0]["items"][0]
        assert bar0["o"] == 100.0
        assert bar0["c"] == 102.0
        assert bar0["h"] >= 102.0
        assert bar0["l"] <= 100.0
        # vol 합산: 3 행 × (10+5) = 45.
        assert bar0["vol"] == 45.0

    def test_tick_agg_sec_one_no_aggregation(self, synthetic_tick_db):
        rd = RE.load_replay(20250102, "tick", ["005930"], agg_sec=1)
        # 집계 없음 → 7 행 그대로.
        assert rd.bars_total == 7
