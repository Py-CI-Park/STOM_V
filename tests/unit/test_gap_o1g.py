"""gap_o1g 단위 테스트 — 갭 공식·구간·제외 규약·진입창·비용 패리티(§2/§3)."""
from __future__ import annotations

import sqlite3

import numpy as np
import pytest

from alpha_lab.dataset.labels import adverse_fill
from alpha_lab.stats_map import config, costs_v2, gap_o1g


# ---------------------------------------------------------------------------
# 갭 공식(§2) — 전일종가 = 현재가/(1+등락율/100), 갭 = (시가/전일종가-1)*100.
# ---------------------------------------------------------------------------

class TestGapPercent:
    def test_formula_basic(self):
        # 현재가 110, 등락율 +10% → 전일종가 100. 시가 105 → 갭 +5%.
        gap, valid = gap_o1g.gap_percent(
            np.array([110.0]), np.array([10.0]), np.array([105.0]))
        assert valid[0]
        assert gap[0] == pytest.approx(5.0)

    def test_negative_gap(self):
        # 전일종가 200(현재가 190, -5%), 시가 194 → 갭 -3%.
        gap, valid = gap_o1g.gap_percent(
            np.array([190.0]), np.array([-5.0]), np.array([194.0]))
        assert valid[0]
        assert gap[0] == pytest.approx(-3.0)

    def test_exclusions(self):
        # 시가<=0 / 등락율=-100 / 전일종가<=0(현재가 0) → 전부 무효.
        cur = np.array([110.0, 110.0, 0.0])
        ud = np.array([10.0, -100.0, 10.0])
        op = np.array([0.0, 105.0, 105.0])
        gap, valid = gap_o1g.gap_percent(cur, ud, op)
        assert not valid.any()
        assert np.isnan(gap).all()


class TestGapBucket:
    def test_sealed_edges(self):
        # (-inf,0)/[0,2)/[2,5)/[5,10)/[10,20)/[20,inf) — 경계값은 상단 구간.
        gaps = np.array([-0.5, 0.0, 1.99, 2.0, 4.99, 5.0, 9.99, 10.0, 19.99,
                         20.0, 35.0])
        expect = np.array([0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
        assert (gap_o1g.gap_bucket(gaps) == expect).all()


class TestEntryWindow:
    def test_split_offsets(self):
        # 09:00:01~09:04:59 → win 0, 09:05:00~09:09:59 → win 1.
        offs = np.array([1, 299, 300, 599])
        win = (offs >= gap_o1g.WIN_SPLIT_OFF).astype(int)
        assert win.tolist() == [0, 0, 1, 1]
        assert gap_o1g.ENTRY_MAX_OFF == 599


# ---------------------------------------------------------------------------
# 비용 패리티 — 고정지평 net 이 스칼라 수기 계산(연도 세율·2틱 불리)과 일치.
# ---------------------------------------------------------------------------

class TestCostParity:
    @pytest.mark.parametrize("year,tax", [(2022, 0.0023), (2023, 0.0020)])
    def test_net_matches_manual(self, year, tax):
        entry_ask, exit_bid = 10000.0, 10100.0
        buy_fill, sell_fill = adverse_fill(entry_ask, exit_bid)
        fee = 0.00015
        buy_cost = buy_fill * (1.0 + fee)
        sell_net = sell_fill * (1.0 - tax - fee)
        expect = (sell_net - buy_cost) / buy_cost
        got = costs_v2.net_from_quotes_year(
            np.array([entry_ask]), np.array([exit_bid]), year)
        assert got[0] == pytest.approx(expect, abs=1e-12)


# ---------------------------------------------------------------------------
# 합성 일 DB 추출 — 후보 규약·갭 제외·지평 라벨(L3 제외 경로).
# ---------------------------------------------------------------------------

def _make_synth_db(path):
    """관심종목 1종목·연속 초 관측의 합성 tick 일 DB(20220401)."""
    conn = sqlite3.connect(str(path))
    cols = ", ".join(f'"{c}" REAL' for c in (
        "현재가", "시가", "매도호가1", "매수호가1", "등락율", "시가총액",
        "초당거래대금", "체결강도"))
    conn.execute(f'CREATE TABLE "123456" ("index" INTEGER, {cols})')
    rows = []
    # 09:00:00 ~ 09:07:00(오프셋 0..420): 현재가 110 고정, 등락율 +10%,
    # 시가 105 → 갭 +5%(버킷 3). 시총 1500억(버킷 1).
    for off in range(0, 421):
        hh, rem = divmod(9 * 3600 + off, 3600)
        mm, ss = divmod(rem, 60)
        idx = 20220401 * 1_000_000 + hh * 10000 + mm * 100 + ss
        rows.append((idx, 110.0, 105.0, 111.0, 109.0, 10.0, 1500.0, 500.0, 120.0))
    conn.executemany('INSERT INTO "123456" VALUES (?,?,?,?,?,?,?,?,?)', rows)
    conn.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
    mt = []
    for off in range(0, 421):
        hh, rem = divmod(9 * 3600 + off, 3600)
        mm, ss = divmod(rem, 60)
        idx = 20220401 * 1_000_000 + hh * 10000 + mm * 100 + ss
        mt.append((idx, "123456"))
    conn.executemany("INSERT INTO moneytop VALUES (?,?)", mt)
    conn.commit()
    conn.close()


class TestExtractDaySynthetic:
    def test_candidates_and_horizon_net(self, tmp_path):
        db = tmp_path / "stock_tick_20220401.db"
        _make_synth_db(db)
        sample, meta = gap_o1g.extract_day_o1g(
            db, "20220401", sell_text="", include_l3=False)
        # 후보 = t0 1..419(관측 0..420, entry=t0+1 필요) 중 진입창 상한 599 내.
        assert int(sample["off"].size) == 419
        assert meta["n_gap_excluded"] == 0
        assert (sample["gap_b"] == 3).all()        # 갭 +5% → [5,10).
        assert (sample["mktcap_b"] == 1).all()     # 1500억 → 1000-3000.
        assert set(sample["win"].tolist()) == {0, 1}
        # h60: t0<=359 만 exit 관측(오프셋<=419+... 관측 상한 420) → valid.
        valid60 = sample["valid_60"]
        assert valid60.sum() == (sample["off"] + 60 <= 420).sum()
        # net 은 상수 호가(ask 111→bid 109)의 스칼라 수기값과 일치(2022 세율).
        buy_fill, sell_fill = adverse_fill(111.0, 109.0)
        fee, tax = 0.00015, 0.0023
        buy_cost = buy_fill * (1.0 + fee)
        expect = (sell_fill * (1.0 - tax - fee) - buy_cost) / buy_cost
        got = sample["net_60"][valid60]
        assert np.allclose(got, expect, atol=1e-6)
        # 절단 없음(진입창 + h<=300 → off+h <= 899 < 1800).
        assert not sample["censored_300"].any()

    def test_gap_exclusion_counted(self, tmp_path):
        db = tmp_path / "stock_tick_20220402.db"
        conn = sqlite3.connect(str(db))
        cols = ", ".join(f'"{c}" REAL' for c in (
            "현재가", "시가", "매도호가1", "매수호가1", "등락율", "시가총액",
            "초당거래대금", "체결강도"))
        conn.execute(f'CREATE TABLE "222222" ("index" INTEGER, {cols})')
        rows = []
        for off in range(0, 10):
            idx = 20220402 * 1_000_000 + 90000 + off
            # 시가 0 → 갭 무효(§2 제외).
            rows.append((idx, 110.0, 0.0, 111.0, 109.0, 10.0, 500.0, 1.0, 1.0))
        conn.executemany('INSERT INTO "222222" VALUES (?,?,?,?,?,?,?,?,?)', rows)
        conn.execute('CREATE TABLE moneytop ("index" INTEGER, "거래대금순위" TEXT)')
        conn.executemany("INSERT INTO moneytop VALUES (?,?)", [
            (20220402 * 1_000_000 + 90000 + off, "222222") for off in range(10)])
        conn.commit()
        conn.close()
        sample, meta = gap_o1g.extract_day_o1g(
            db, "20220402", sell_text="", include_l3=False)
        assert int(sample["off"].size) == 0
        assert meta["n_gap_excluded"] == meta["n_candidates"] > 0


# ---------------------------------------------------------------------------
# 셀 집계 — 144셀 전수·좌표 결정론·insufficient 규약.
# ---------------------------------------------------------------------------

class TestAggregateCells:
    def test_full_grid_144(self, tmp_path):
        db = tmp_path / "stock_tick_20220401.db"
        _make_synth_db(db)
        sample, _ = gap_o1g.extract_day_o1g(
            db, "20220401", sell_text="", include_l3=False)
        cells = gap_o1g.aggregate_cells(sample)
        assert len(cells) == 144
        keys = {(c["gap_b"], c["mktcap_b"], c["win"], c["exit"]) for c in cells}
        assert len(keys) == 144
        nonzero = [c for c in cells if c["n"] > 0]
        # 합성 표본은 (gap_b=3, mktcap_b=1) 두 진입창 × h60/h120/h300 에만 존재.
        assert all(c["gap_b"] == 3 and c["mktcap_b"] == 1 for c in nonzero)
        assert all(c["exit"] != "l3" for c in nonzero)
        for c in nonzero:
            assert c["insufficient"] == int(c["n"] < config.MIN_CELL_N)
            assert c["mean_net"] is not None
            assert c["ci_low"] is not None and c["ci_high"] is not None

    def test_empty_cells_reported_not_dropped(self, tmp_path):
        db = tmp_path / "stock_tick_20220401.db"
        _make_synth_db(db)
        sample, _ = gap_o1g.extract_day_o1g(
            db, "20220401", sell_text="", include_l3=False)
        cells = gap_o1g.aggregate_cells(sample)
        empty = [c for c in cells if c["n"] == 0]
        assert empty and all(c["mean_net"] is None for c in empty)
        assert all(c["insufficient"] == 1 for c in empty)


class TestDeterminism:
    def test_param_sha_stable(self):
        sha1 = gap_o1g.param_sha_o1g()
        sha2 = gap_o1g.param_sha_o1g()
        assert sha1 == sha2 and len(sha1) == 16

    def test_cell_seed_deterministic(self):
        s1 = gap_o1g._cell_seed("o1g", "h60", 1, 2, 0)
        s2 = gap_o1g._cell_seed("o1g", "h60", 1, 2, 0)
        s3 = gap_o1g._cell_seed("o1g", "h60", 1, 2, 1)
        assert s1 == s2 != s3
