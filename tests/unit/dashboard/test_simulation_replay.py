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


class TestDemoRecommend:
    """/sim/demo — 즉시 체험 추천(자동 데모·원클릭 프리셋이 소비). 무예외·인벤토리만 읽음."""

    def test_latest_picks_most_recent_day_and_top_mover(self, synthetic_min_db):
        out = SA.sim_demo(src="min", mode="latest")
        assert out["available"] is True
        assert out["date"] == 20250102            # 인벤토리 유일 날짜.
        # 마지막 행 등락 1위: 000660=4.0 > 005930=2.0.
        assert out["code"] == "000660"
        assert out["name"] == "SK하이닉스"
        assert out["change_pct"] == 4.0
        assert out["src"] == "min"
        assert out["mode"] == "latest"

    def test_top_gainer_scans_for_largest_change(self, synthetic_min_db):
        out = SA.sim_demo(src="min", mode="top_gainer")
        assert out["available"] is True
        # 단일 날짜뿐 — 그날 등락 1위(000660)가 곧 최대 상승.
        assert out["date"] == 20250102
        assert out["code"] == "000660"
        assert out["change_pct"] == 4.0
        assert out["mode"] == "top_gainer"

    def test_empty_when_no_inventory(self, synthetic_min_db):
        # tick DB 는 없다 → 추천 불가(available=False), 무예외 빈 페이로드.
        out = SA.sim_demo(src="tick", mode="latest")
        assert out["available"] is False
        assert out["date"] == 0
        assert out["code"] == ""

    def test_mode_normalized_to_latest_on_garbage(self, synthetic_min_db):
        out = SA.sim_demo(src="min", mode="bogus")
        assert out["mode"] == "latest"
        assert out["available"] is True

    def test_top_gainer_picks_day_with_highest_top_mover(self, monkeypatch, tmp_path):
        """여러 날 중 등락 1위가 가장 큰 날을 고른다('최대 상승일' 근사)."""
        db_dir = tmp_path / "_database"
        db_dir.mkdir()
        # 0102: 종목 등락 1위 +4.0 / 0103: 등락 1위 +9.0 (더 큼) → top_gainer 는 0103 선택.
        _make_daily_db(db_dir / "stock_min_20250102.db", "min", {
            "005930": [(202501020900, 100.0, 99.0, 101.0, 98.0, 4.0, 5000.0, 110.0, 30.0, 20.0)],
        })
        _make_daily_db(db_dir / "stock_min_20250103.db", "min", {
            "000660": [(202501030900, 50.0, 49.0, 51.0, 49.0, 9.0, 3000.0, 90.0, 15.0, 18.0)],
        })
        monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
        monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
        out = SA.sim_demo(src="min", mode="top_gainer")
        assert out["date"] == 20250103
        assert out["code"] == "000660"
        assert out["change_pct"] == 9.0
        # latest 모드는 최신 날짜(0103)를 고른다(동일 결과지만 경로 다름).
        latest = SA.sim_demo(src="min", mode="latest")
        assert latest["date"] == 20250103


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


# --------------------------------------------------------------- live indicators
# 호가불균형 컬럼(매수총잔량/매도총잔량)을 포함한 확장 min 컬럼 레이아웃.
_MIN_COLS_IMB = _MIN_COLS + ["매도총잔량", "매수총잔량"]


def _make_min_db_imbalance(path: Path, tables: dict) -> None:
    """매도총잔량/매수총잔량 컬럼을 가진 합성 min DB. tables=={code:[(idx, +base9, sell_tot, buy_tot)...]}."""
    con = sqlite3.connect(str(path))
    con.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    for code, rows in tables.items():
        coldef = ", ".join(f'"{c}" REAL' for c in _MIN_COLS_IMB)
        con.execute(f'CREATE TABLE "{code}" ("index" INTEGER, {coldef})')
        ph = ", ".join("?" for _ in range(len(_MIN_COLS_IMB) + 1))
        con.executemany(f'INSERT INTO "{code}" VALUES ({ph})', rows)
    con.commit()
    con.close()


@pytest.fixture
def synthetic_ma_db(monkeypatch, tmp_path):
    """min DB(20250103) 1종목 6행 — 종가 10,12,14,16,18,20 으로 MA5 점등을 검증한다."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    closes = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    rows = [
        (202501030900 + i, c, c, c, c, 0.0, 1000.0, 100.0, 5.0, 5.0)
        for i, c in enumerate(closes)
    ]
    _make_daily_db(db_dir / "stock_min_20250103.db", "min", {"005930": rows})
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    return db_dir


@pytest.fixture
def synthetic_imbalance_db(monkeypatch, tmp_path):
    """매수/매도총잔량 컬럼을 가진 min DB(20250104) 1종목 — imbalance 가용 분기."""
    db_dir = tmp_path / "_database"
    db_dir.mkdir()
    # (index, 현재가..분당매도수량(9), 매도총잔량, 매수총잔량)
    rows = [
        (202501040900, 100.0, 99.0, 101.0, 98.0, 1.0, 5000.0, 110.0, 30.0, 20.0, 200.0, 300.0),
        (202501040901, 102.0, 100.0, 103.0, 100.0, 3.0, 6000.0, 120.0, 40.0, 25.0, 100.0, 250.0),
        (202501040902, 101.0, 102.0, 102.0, 100.0, 2.0, 5500.0, 105.0, 35.0, 30.0, 0.0, 250.0),
    ]
    _make_min_db_imbalance(db_dir / "stock_min_20250104.db", {"005930": rows})
    monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
    monkeypatch.setattr(SA, "_DATABASE_DIR", db_dir)
    return db_dir


class TestMovingAverages:
    def test_ma5_none_until_window_filled(self, synthetic_ma_db):
        rd = RE.load_replay(20250103, "min", ["005930"], agg_sec=10)
        items = [f["items"][0] for f in rd.frames]
        assert len(items) == 6
        # MA5 는 5번째 bar(인덱스 4)부터 점등. 그 전엔 None.
        for i in range(4):
            assert items[i]["ma5"] is None
        # 인덱스 4: (10+12+14+16+18)/5 = 14.0.
        assert items[4]["ma5"] == 14.0
        # 인덱스 5: (12+14+16+18+20)/5 = 16.0 — 증분 윈도우 슬라이드 검증.
        assert items[5]["ma5"] == 16.0

    def test_ma20_ma60_none_when_series_short(self, synthetic_ma_db):
        rd = RE.load_replay(20250103, "min", ["005930"], agg_sec=10)
        # 6행뿐이라 MA20/MA60 은 끝까지 None.
        for f in rd.frames:
            assert f["items"][0]["ma20"] is None
            assert f["items"][0]["ma60"] is None

    def test_ma_present_in_frame_schema(self, synthetic_ma_db):
        rd = RE.load_replay(20250103, "min", ["005930"], agg_sec=10)
        item = rd.frames[0]["items"][0]
        for key in ("ma5", "ma20", "ma60", "imbalance", "buy_rest", "sell_rest"):
            assert key in item


class TestImbalance:
    def test_imbalance_computed_when_columns_present(self, synthetic_imbalance_db):
        rd = RE.load_replay(20250104, "min", ["005930"], agg_sec=10)
        items = [f["items"][0] for f in rd.frames]
        # 첫 행: 매수총잔량/매도총잔량 = 300/200 = 1.5.
        assert items[0]["imbalance"] == 1.5
        # 둘째: 250/100 = 2.5.
        assert items[1]["imbalance"] == 2.5
        # 셋째: 매도총잔량=0 → 분모 보호로 None.
        assert items[2]["imbalance"] is None

    def test_imbalance_none_when_columns_absent(self, synthetic_min_db):
        # synthetic_min_db 는 총잔량 컬럼이 없다 → imbalance 전부 None.
        rd = RE.load_replay(20250102, "min", ["005930"], agg_sec=10)
        for f in rd.frames:
            assert f["items"][0]["imbalance"] is None


class TestRawRestQuantities:
    """raw 호가총잔량(buy_rest/sell_rest) — imbalance 와 같은 컬럼 공유, 가용/부재 분기."""

    def test_rest_raw_values_when_columns_present(self, synthetic_imbalance_db):
        rd = RE.load_replay(20250104, "min", ["005930"], agg_sec=10)
        items = [f["items"][0] for f in rd.frames]
        # 매수총잔량 raw: 300, 250, 250 / 매도총잔량 raw: 200, 100, 0.
        assert [it["buy_rest"] for it in items] == [300.0, 250.0, 250.0]
        assert [it["sell_rest"] for it in items] == [200.0, 100.0, 0.0]

    def test_rest_present_even_when_imbalance_none(self, synthetic_imbalance_db):
        # 셋째 행: 매도총잔량=0 → imbalance 는 None 이지만 raw 잔량은 그대로 보존.
        rd = RE.load_replay(20250104, "min", ["005930"], agg_sec=10)
        third = rd.frames[2]["items"][0]
        assert third["imbalance"] is None
        assert third["buy_rest"] == 250.0
        assert third["sell_rest"] == 0.0

    def test_rest_none_when_columns_absent(self, synthetic_min_db):
        # 총잔량 컬럼 부재 → buy_rest/sell_rest 전부 None(하위호환).
        rd = RE.load_replay(20250102, "min", ["005930"], agg_sec=10)
        for f in rd.frames:
            assert f["items"][0]["buy_rest"] is None
            assert f["items"][0]["sell_rest"] is None

    def test_tick_rest_carries_last_value_in_bucket(self, monkeypatch, tmp_path):
        # tick agg 버킷은 잔량 스냅샷의 마지막 값을 대표로 싣는다.
        db_dir = tmp_path / "_database"
        db_dir.mkdir()
        tick_cols = _TICK_COLS + ["매도총잔량", "매수총잔량"]
        con = sqlite3.connect(str(db_dir / "stock_tick_20250105.db"))
        con.execute('CREATE TABLE moneytop ("index" INTEGER, "x" TEXT)')
        coldef = ", ".join(f'"{c}" REAL' for c in tick_cols)
        con.execute(f'CREATE TABLE "005930" ("index" INTEGER, {coldef})')
        ph = ", ".join("?" for _ in range(len(tick_cols) + 1))
        # 09:00:00, :03, :07 → 한 버킷(agg 10s). 마지막(=:07) 매수총잔량=330, 매도총잔량=110.
        rows = [
            (20250105090000, 100.0, 99.0, 102.0, 98.0, 0.0, 1000.0, 100.0, 10.0, 5.0, 200.0, 300.0),
            (20250105090003, 101.0, 100.0, 103.0, 99.0, 1.0, 1100.0, 101.0, 10.0, 5.0, 150.0, 320.0),
            (20250105090007, 102.0, 101.0, 104.0, 100.0, 2.0, 1200.0, 102.0, 10.0, 5.0, 110.0, 330.0),
        ]
        con.executemany(f'INSERT INTO "005930" VALUES ({ph})', rows)
        con.commit()
        con.close()
        monkeypatch.setattr(RE, "_DATABASE_DIR", db_dir)
        rd = RE.load_replay(20250105, "tick", ["005930"], agg_sec=10)
        bar0 = rd.frames[0]["items"][0]
        assert bar0["buy_rest"] == 330.0
        assert bar0["sell_rest"] == 110.0
