"""alpha_lab.stats_map v2 확장 단위 테스트 — 기반 교정(V2-A) config/costs/pilot.

실DB 불필요(전부 합성). 실행:
    python -m pytest tests/unit/test_stats_map_v2.py -q

검증 축:
- config_v2: 연도 세율 단일 조회, 새 경계, param_sha 결정성.
- costs_v2: tax=0.0018 → v1 net_rate 환원, 스칼라==벡터 패리티(0), 연도 세율
  더 음(-).
- pilot_v2: v2 등락율 버킷, 오프셋→인덱스, v1 온셋 재사용, h300 교정·절단,
  L3 발화+연도 세율 재계상, 재현 게이트(순수==벡터 통과·불일치 분류), 셀 집계,
  합성 일 DB 미니 e2e, v2 파티션 DB 라운드트립.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.stats_map import config_v2, costs_v2, pilot_v2

SYNTH_SELL_TEXT = "매도 = False\nif 수익률 <= -5.0:\n    매도 = True\n"
SYNTH_SELL_SHA = hashlib.sha256(SYNTH_SELL_TEXT.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# config_v2 — 연도 세율 단일 출처 + 새 경계 + 지문
# ---------------------------------------------------------------------------

class TestConfigV2:
    def test_year_tax_lookup(self):
        assert config_v2.year_tax_rate(2022) == 0.0023
        assert config_v2.year_tax_rate(2023) == 0.0020
        assert config_v2.year_tax_rate(2026) == 0.0020
        with pytest.raises(KeyError):
            config_v2.year_tax_rate(2021)

    def test_new_edges(self):
        assert config_v2.UPDOWN_EDGES_V2 == (1.59, 3.56, 6.88)

    def test_param_sha_deterministic(self):
        assert config_v2.param_sha_v2() == config_v2.param_sha_v2()
        assert len(config_v2.param_sha_v2()) == 16


# ---------------------------------------------------------------------------
# costs_v2 — 연도 세율 비용식(환원·패리티·방향)
# ---------------------------------------------------------------------------

class TestCostsV2:
    def test_reduce_to_v1_at_018(self):
        rng = np.random.default_rng(1)
        for _ in range(50):
            bf = float(rng.integers(1000, 200000))
            sf = float(rng.integers(1000, 200000))
            assert costs_v2.net_rate_year(bf, sf, 0.0018) == pytest.approx(
                net_rate(bf, sf), abs=1e-15)

    def test_scalar_vector_parity_zero(self):
        rng = np.random.default_rng(2)
        entry = rng.integers(1000, 200000, size=500).astype(np.float64)
        exit_ = rng.integers(1000, 200000, size=500).astype(np.float64)
        for year in (2022, 2023, 2024):
            assert costs_v2.parity_max_err_year(entry, exit_, year) == 0.0

    def test_year_tax_more_negative_than_v1(self):
        # 2022 세율(0.23%)은 v1(0.18%)보다 net 을 더 음(-)으로 만든다.
        bf, sf = adverse_fill(10000.0, 10000.0)
        assert costs_v2.net_rate_year(bf, sf, 0.0023) < net_rate(bf, sf)

    def test_net_from_quotes_uses_single_source(self):
        entry = np.array([10000.0])
        exit_ = np.array([10000.0])
        got = costs_v2.net_from_quotes_year(entry, exit_, 2022)[0]
        bf, sf = costs_v2.adverse_fill_year(entry, exit_)
        expect = costs_v2.net_rate_year_vec(bf, sf, config_v2.year_tax_rate(2022))[0]
        assert got == expect


# ---------------------------------------------------------------------------
# pilot_v2 — 축·오프셋·온셋·h300·L3
# ---------------------------------------------------------------------------

class TestAxesV2:
    def test_updown_quartile_v2_boundaries(self):
        vals = np.array([1.0, 1.59, 3.56, 6.88, 10.0])
        q = pilot_v2.updown_quartile_v2(vals)
        # 경계값은 상단 구간 포함(searchsorted right) — 1.59→1, 3.56→2, 6.88→3.
        assert q.tolist() == [0, 1, 2, 3, 3]

    def test_offset_to_index(self):
        assert pilot_v2._offset_to_index(20220323, 0) == 20220323090000
        assert pilot_v2._offset_to_index(20220323, 65) == 20220323090105
        assert pilot_v2._offset_to_index(20220323, 1800) == 20220323093000


def _dense(n=1801, *, amount, present=None, ask=1000.0, bid=1000.0,
           updown=5.0, cap=20000.0):
    present = np.ones(n, dtype=bool) if present is None else present
    return {
        "present": present,
        "매도호가1": np.full(n, ask), "매수호가1": np.full(n, bid),
        "초당거래대금": np.asarray(amount, dtype=np.float64),
        "등락율": np.full(n, updown), "시가총액": np.full(n, cap),
        "체결강도": np.full(n, 100.0),
        "매수총잔량": np.full(n, 1000.0), "매도총잔량": np.full(n, 1000.0),
    }


class TestOnsetDetection:
    def test_surge_onset_offset_and_universe_gate(self):
        n = 1801  # dense 는 항상 창 전체(09:00:00~09:30:00) 크기.
        amount = np.full(n, 100.0)
        amount[120] = 500.0  # 직전 30초 평균 100 → ratio 5, 교차 온셋.
        dense = _dense(n, amount=amount)
        uni_all = np.arange(n, dtype=np.int64)
        offs = pilot_v2._onset_offsets(dense, uni_all)
        assert 120 in offs.tolist()
        # 유니버스에서 120 제외 → 온셋 후보 아님.
        uni_no120 = np.array([o for o in range(n) if o != 120], dtype=np.int64)
        assert 120 not in pilot_v2._onset_offsets(dense, uni_no120).tolist()


class TestH300Labels:
    def test_h300_net_and_censor(self):
        n = 1801
        dense = _dense(n, amount=np.full(n, 100.0), ask=1000.0, bid=1000.0)
        onset = np.array([60, 1600])  # 1600+300=1900>1800 → 절단.
        net, valid, censored = pilot_v2._h300_labels(dense, onset, 2022)
        assert valid[0] and not censored[0]
        assert not valid[1] and censored[1]
        expect = costs_v2.net_from_quotes_year(
            np.array([1000.0]), np.array([1000.0]), 2022)[0]
        assert net[0] == pytest.approx(expect)
        assert np.isnan(net[1])


def _ts(day, second):
    base = datetime.strptime(f"{day}090000", "%Y%m%d%H%M%S")
    return int((base + timedelta(seconds=second)).strftime("%Y%m%d%H%M%S"))


def _rows(day, seconds, price_fn, **overrides):
    rows = {}
    for s in seconds:
        price = float(price_fn(s))
        row = {
            "현재가": price, "시가": 10000.0, "등락율": 5.0,
            "초당매수수량": 10.0, "초당매도수량": 10.0, "시가총액": 20000.0,
            "매수총잔량": 1000.0, "매수호가1": price, "매도호가1": price,
        }
        for k, fn in overrides.items():
            row[k] = float(fn(s))
        rows[_ts(day, s)] = row
    return rows


class TestL3Labels:
    def test_clause4_exit_and_year_tax(self):
        day = "20220323"
        rows = _rows(day, range(0, 20),
                     lambda s: 10000.0 if s <= 7 else 9400.0,
                     매수호가1=lambda s: 10000.0 if s <= 7 else 9400.0,
                     매도호가1=lambda s: 10000.0)
        t0 = _ts(day, 5)
        entry_ask = np.array([10000.0])
        net, exit_t, price, clause, labeled = pilot_v2._l3_labels(
            rows, [t0], entry_ask, SYNTH_SELL_TEXT, "pure", 2022, SYNTH_SELL_SHA)
        assert labeled[0] and clause[0] == 4
        assert exit_t[0] == _ts(day, 8)
        buy_fill, sell_fill = adverse_fill(10000.0, 9400.0)
        assert price[0] == pytest.approx(sell_fill)
        assert net[0] == pytest.approx(
            costs_v2.net_rate_year(buy_fill, sell_fill, 0.0023))
        # 연도 세율판이 v1 라벨보다 더 음(-).
        assert net[0] < net_rate(buy_fill, sell_fill)


# ---------------------------------------------------------------------------
# 재현 게이트 + 셀 집계
# ---------------------------------------------------------------------------

def _paired_sample(n=200, mismatch_at=None):
    rng = np.random.default_rng(3)
    exit_t = rng.integers(20220323090100, 20220323092000, size=n).astype(np.int64)
    price = rng.integers(9000, 11000, size=n).astype(np.float64)
    net = rng.normal(-0.01, 0.005, size=n)
    sample = {
        "day": np.full(n, 20220323, dtype=np.int32),
        "off": np.arange(n, dtype=np.int16),
        "l3_labeled_pure": np.ones(n, bool),
        "l3_labeled_vector": np.ones(n, bool),
        "l3_exit_pure": exit_t.copy(), "l3_exit_vector": exit_t.copy(),
        "l3_price_pure": price.copy(), "l3_price_vector": price.copy(),
        "l3_net_pure": net.copy(), "l3_net_vector": net.copy(),
        "l3_clause_pure": np.full(n, 4, np.int8),
    }
    if mismatch_at is not None:
        sample["l3_exit_vector"][mismatch_at] += 5  # 벡터 늦은 청산.
        sample["l3_net_vector"][mismatch_at] -= 0.02
        sample["l3_price_vector"][mismatch_at] -= 100.0
    return sample


class TestReproductionGate:
    def test_pure_equals_vector_passes(self):
        report = pilot_v2.reproduction_gate(_paired_sample())
        assert report["gate_pass"] is True
        assert report["time_and_price_match_rate"] == 1.0
        assert report["err_median_pp"] == 0.0
        assert report["err_max_pp"] == 0.0
        assert report["n_mismatch"] == 0

    def test_mismatch_fails_and_classified(self):
        report = pilot_v2.reproduction_gate(_paired_sample(mismatch_at=[10, 20]))
        assert report["gate_pass"] is False
        assert report["n_mismatch"] == 2
        assert report["mismatch_causes"]["vector_later_exit"] == 2
        assert report["err_max_pp"] > 0.0
        assert len(report["mismatch_causes"]["examples"]) == 2

    def test_label_presence_mismatch_fails(self):
        sample = _paired_sample(n=50)
        sample["l3_labeled_vector"][0] = False
        report = pilot_v2.reproduction_gate(sample)
        assert report["only_pure_labeled"] == 1
        assert report["gate_pass"] is False


class TestAggregateCells:
    def test_cells_membership_and_labels(self):
        n = 40
        sample = {
            "day": np.full(n, 20220323, dtype=np.int32),
            "off": np.arange(n, dtype=np.int16),
            "time_b": np.zeros(n, np.int8),
            "updown_q": np.zeros(n, np.int8),
            "mktcap_b": np.zeros(n, np.int8),
            "h300_net": np.full(n, -0.01),
            "h300_valid": np.ones(n, bool),
            "h300_censored": np.zeros(n, bool),
            "l3_net_pure": np.full(n, -0.005),
            "l3_labeled_pure": np.ones(n, bool),
        }
        rows = pilot_v2.aggregate_cells(sample)
        cell = [r for r in rows if r["axis_set"] == "time_ud"
                and r["time_b"] == 0 and r["updown_q"] == 0]
        by_label = {r["label_kind"]: r for r in cell}
        assert by_label["h300"]["n"] == n
        assert by_label["l3"]["n"] == n
        assert by_label["h300"]["mean_net"] == pytest.approx(-0.01)
        assert by_label["l3"]["mean_net"] == pytest.approx(-0.005)


# ---------------------------------------------------------------------------
# 미니 e2e — 합성 일 DB(온셋 + 급락 절4) + v2 파티션 DB 라운드트립
# ---------------------------------------------------------------------------

_E2E_COLS = ("현재가", "시가", "등락율", "초당매수수량", "초당매도수량",
             "초당거래대금", "시가총액", "체결강도", "매수총잔량", "매도총잔량",
             "매수호가1", "매도호가1")


def _make_day_db(path, day="20220323", code="123456"):
    conn = sqlite3.connect(path)
    col_defs = ", ".join(f'"{c}" REAL' for c in _E2E_COLS)
    conn.execute(f'CREATE TABLE "{code}" ("index" INTEGER PRIMARY KEY, {col_defs})')
    n = 500
    for s in range(n):
        price = 10000.0 if s <= 130 else 9300.0  # 온셋(120) 뒤 급락 → 절4.
        amount = 500.0 if s == 120 else 100.0
        row = {
            "현재가": price, "시가": 10000.0, "등락율": 5.0,
            "초당매수수량": 10.0, "초당매도수량": 10.0, "초당거래대금": amount,
            "시가총액": 20000.0, "체결강도": 100.0,
            "매수총잔량": 1000.0, "매도총잔량": 1000.0,
            "매수호가1": price, "매도호가1": 10000.0 if s <= 130 else 9300.0,
        }
        conn.execute(
            f'INSERT INTO "{code}" VALUES ({", ".join(["?"] * (len(_E2E_COLS) + 1))})',
            (pilot_v2._offset_to_index(int(day), s),
             *[row[c] for c in _E2E_COLS]))
    conn.execute(
        'CREATE TABLE moneytop ("index" INTEGER PRIMARY KEY, "거래대금순위" TEXT)')
    conn.executemany(
        "INSERT INTO moneytop VALUES (?, ?)",
        [(pilot_v2._offset_to_index(int(day), s), code) for s in range(n)])
    conn.commit()
    conn.close()


class TestPilotE2E:
    def test_extract_day_and_gate_and_db(self, tmp_path):
        db = tmp_path / "stock_tick_20220323.db"
        _make_day_db(db)
        sample = pilot_v2.extract_day(db, "20220323", SYNTH_SELL_TEXT, SYNTH_SELL_SHA)
        assert sample["off"].size >= 1
        # 온셋(120) 존재, L3 순수/벡터 동일, 절4 발화.
        assert np.all(sample["l3_labeled_pure"] == sample["l3_labeled_vector"])
        report = pilot_v2.reproduction_gate(sample)
        assert report["gate_pass"] is True
        cells = pilot_v2.aggregate_cells(sample)
        assert any(r["label_kind"] == "l3" and r["n"] > 0 for r in cells)
        out = tmp_path / "stats_map_v2a_pilot.db"
        pilot_v2.write_pilot_db(out, cells, {
            "build_id": "v2a_pilot_test", "date_start": "20220323",
            "date_end": "20220323", "input_files": 1,
            "n_onsets": int(sample["off"].size),
            "param_sha": config_v2.param_sha_v2(),
            "updown_edges": str(config_v2.UPDOWN_EDGES_V2),
            "year_tax": "2022=0.0023", "sell_sha256": SYNTH_SELL_SHA,
            "gate_pass": "True",
            "created_at": "2026-07-11T00:00:00+00:00",
        })
        conn = sqlite3.connect(out)
        n_cells = conn.execute("SELECT COUNT(*) FROM cells_pilot_v2").fetchone()[0]
        rc = conn.execute(
            "SELECT build_id, n_onsets FROM build_receipts_v2").fetchone()
        conn.close()
        assert n_cells > 0
        assert rc[0] == "v2a_pilot_test"
