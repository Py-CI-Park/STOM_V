"""alpha_lab.dataset.labels_v2 단위 테스트 — L3_replay 라벨러·등가성 게이트·CLI.

실DB 불필요(전부 합성). 실행:
    python -m pytest tests/unit/test_alpha_labels_v2.py -q

검증 축:
- 매도식 sha 게이트(blocked), strategy.db 적재.
- 수기 수치: entry +2틱 / exit -2틱 / L3_net 비용식, 하드스톱(절4)·트레일(절5)·
  최저현재가(절3)·상한가(절1)·09:30 강제캡·결측 skip.
- 벡터 경로 == 순수 경로(무작위 퍼즈), 벡터 미러 == replay_champion_exit.
- 등가성 게이트 영수증 로직(pass/fail/부재/파손) + 미니 e2e.
- to_arrays label_dtypes(additive), 사전등록 v2 로더(additive), CLI build/gate.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from alpha_lab import registry
from alpha_lab.dataset.cache import to_arrays
from alpha_lab.dataset.labels import adverse_fill, net_rate
from alpha_lab.dataset.labels_v2 import (
    CHAMPION_SELL_SHA256,
    L3_NOMINAL_BETTING,
    SellExprMismatch,
    _vector_sp,
    build_day_context,
    build_l3_labels,
    day_context_from_rows,
    equivalence_gate_pass,
    load_champion_sell_expr,
    replay_champion_exit_vector,
    run_equivalence_gate,
    verify_sell_expr,
)
from alpha_lab.distill.replay import (
    kiwoom_pgsgsp,
    precompute_windows,
    replay_champion_exit,
)

SYNTH_SELL_TEXT = "매도 = False\nif 수익률 <= -5.0:\n    매도 = True\n"
SYNTH_SELL_SHA = hashlib.sha256(SYNTH_SELL_TEXT.encode("utf-8")).hexdigest()

_REPO = Path(__file__).resolve().parents[2]
_REAL_STRATEGY_DB = _REPO / "_database" / "strategy.db"


def _ts(day: str, second: int) -> int:
    base = datetime.strptime(day + "090000", "%Y%m%d%H%M%S")
    return int((base + timedelta(seconds=second)).strftime("%Y%m%d%H%M%S"))


def _mk_rows(day: str, seconds, price_fn, **overrides):
    """합성 rows_by_t0 — 기본: 절 1·6~9 차단(등락율 5, 시가총액 2조)."""
    rows = {}
    for s in seconds:
        price = float(price_fn(s))
        row = {
            "현재가": price, "시가": 10000.0, "등락율": 5.0,
            "초당매수수량": 10.0, "초당매도수량": 10.0,
            "시가총액": 20000.0, "매수총잔량": 1000.0,
            "매수호가1": price, "매도호가1": price,
        }
        for key, fn in overrides.items():
            row[key] = float(fn(s))
        rows[_ts(day, s)] = row
    return rows


# ---------------------------------------------------------------------------
# 매도식 sha 게이트
# ---------------------------------------------------------------------------

class TestSellExprGate:
    def test_verify_ok_and_mismatch(self):
        assert verify_sell_expr(SYNTH_SELL_TEXT, SYNTH_SELL_SHA) == SYNTH_SELL_SHA
        with pytest.raises(SellExprMismatch):
            verify_sell_expr(SYNTH_SELL_TEXT + " ", SYNTH_SELL_SHA)
        with pytest.raises(SellExprMismatch):
            verify_sell_expr(SYNTH_SELL_TEXT)  # 봉인 챔피언 sha 와 불일치.

    def test_load_from_strategy_db(self, tmp_path):
        db = tmp_path / "strategy.db"
        conn = sqlite3.connect(db)
        conn.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
        conn.execute(
            "INSERT INTO stocksell VALUES (?, ?)",
            ("ALP_EXITCHK_A_INCUMBENT", SYNTH_SELL_TEXT),
        )
        conn.commit()
        conn.close()
        assert load_champion_sell_expr(db) == SYNTH_SELL_TEXT
        with pytest.raises(ValueError):
            load_champion_sell_expr(db, name="NO_SUCH_STRATEGY")

    def test_build_l3_labels_blocked_on_sha_mismatch(self):
        with pytest.raises(SellExprMismatch):
            build_l3_labels({}, [], SYNTH_SELL_TEXT)  # 기대 sha=봉인 챔피언.

    @pytest.mark.skipif(
        not _REAL_STRATEGY_DB.exists(), reason="local strategy.db not present"
    )
    def test_real_incumbent_matches_sealed_sha(self):
        text = load_champion_sell_expr(_REAL_STRATEGY_DB)
        assert verify_sell_expr(text) == CHAMPION_SELL_SHA256


# ---------------------------------------------------------------------------
# 수익률 벡터화 — kiwoom_pgsgsp 스칼라와 비트 동일
# ---------------------------------------------------------------------------

class TestVectorSp:
    def test_parity_random_integer_prices(self):
        rng = np.random.default_rng(20260706)
        for _ in range(20):
            buy = float(rng.integers(500, 200_000))
            qty = max(1, int(5_000_000 / buy))
            bg = qty * buy
            prices = rng.integers(
                max(1, int(buy * 0.7)), int(buy * 1.35), size=400
            ).astype(np.float64)
            vec = _vector_sp(bg, qty * prices)
            ref = np.array(
                [kiwoom_pgsgsp(bg, qty * float(p))[2] for p in prices]
            )
            assert np.array_equal(vec, ref)

    def test_parity_near_threshold_values(self):
        # 절 임계(-5.0/-2.0/9.0) 부근 촘촘한 가격 — 반올림 경계 포함.
        buy = 10020.0
        qty = 499
        bg = qty * buy
        prices = np.arange(9400, 9600, 1, dtype=np.float64)
        vec = _vector_sp(bg, qty * prices)
        ref = np.array([kiwoom_pgsgsp(bg, qty * float(p))[2] for p in prices])
        assert np.array_equal(vec, ref)

    def test_zero_price_row_matches_scalar(self):
        # 가격 0(NULL→0 엔진 미러) 행도 스칼라 kiwoom_pgsgsp 와 동일해야 한다.
        vec = _vector_sp(1_000_000.0, np.array([0.0]))[0]
        assert vec == kiwoom_pgsgsp(1_000_000.0, 0.0)[2]


# ---------------------------------------------------------------------------
# L3 라벨 — 수기 시나리오 (봉인 label_spec_v2)
# ---------------------------------------------------------------------------

DAY = "20240103"


def _labels(rows, t0_seconds, engine="pure", **kw):
    t0s = [_ts(DAY, s) for s in t0_seconds]
    return build_l3_labels(
        rows, t0s, SYNTH_SELL_TEXT, engine=engine,
        expected_sha=SYNTH_SELL_SHA, **kw
    )


class TestL3Scenarios:
    def test_hard_stop_clause4_manual_numbers(self):
        # t0=초5, entry=초6 ask 10000 → buy_fill 10020(+2틱: 10→10010→10020).
        # 초8부터 9400(-6%대, 절4) → exit=초8 bid 9400 → sell_fill 9380(-2틱).
        rows = _mk_rows(
            DAY, range(0, 20), lambda s: 10000.0 if s <= 7 else 9400.0,
            매수호가1=lambda s: 10000.0 if s <= 7 else 9400.0,
            매도호가1=lambda s: 10000.0,
        )
        labels, stats = _labels(rows, [5])
        lab = labels[_ts(DAY, 5)]
        assert lab is not None
        assert lab["clause"] == 4
        assert lab["exit_time"] == _ts(DAY, 8)
        buy_fill, sell_fill = adverse_fill(10000.0, 9400.0)
        assert (buy_fill, sell_fill) == (10020.0, 9380.0)
        expected = (9380.0 * (1 - 0.0018 - 0.00015) - 10020.0 * 1.00015) / (
            10020.0 * 1.00015
        )
        assert lab["L3_net"] == pytest.approx(expected, abs=1e-12)
        assert lab["L3_net"] == pytest.approx(net_rate(buy_fill, sell_fill))
        assert lab["L3_pos"] == 0
        assert stats["fired"] == 1 and stats["forced_cap"] == 0

    def test_trailing_clause5_fires_after_best_retrace(self):
        # +4.6%대 최고(암 3 초과) 후 +1.6%대로 리테이스 → 절5.
        def price(s):
            if s <= 6:
                return 10000.0
            if s <= 9:
                return 10500.0
            return 10200.0
        rows = _mk_rows(DAY, range(0, 20), price)
        labels, _ = _labels(rows, [5])
        lab = labels[_ts(DAY, 5)]
        assert lab is not None
        assert lab["clause"] == 5
        assert lab["exit_time"] == _ts(DAY, 10)
        # 검증: 발화 초 bid(10200) -2틱 = 10180 기준 net_rate.
        _, sell_fill = adverse_fill(10000.0, 10200.0)
        assert lab["L3_net"] == pytest.approx(net_rate(10020.0, sell_fill))
        assert lab["L3_pos"] == 1

    def test_low_price_clause3_needs_history_gate(self):
        # 이른 진입(t0=초3)은 tick_count 게이트로 절3 영구 불발(신저가에도),
        # 늦은 진입(t0=초70)은 hold>60 후 신저가에서 절3 발동.
        def price(s):
            if s == 40:
                return 9950.0  # 진입 전 60행 최저.
            if s >= 135:
                return 9940.0  # 최저(9950) 하회 — 절3 후보.
            return 10000.0
        rows = _mk_rows(DAY, range(0, 160), price)
        early, _ = _labels(rows, [3])
        lab_early = early[_ts(DAY, 3)]
        assert lab_early is not None
        assert lab_early["clause"] == 0  # 절3 불발 → 강제캡.
        late, _ = _labels(rows, [70])
        lab_late = late[_ts(DAY, 70)]
        assert lab_late is not None
        assert lab_late["clause"] == 3
        # hold>60 최초 충족 + 신저가 최초 관측 초 = 진입(71)+64 = 135 이후.
        assert lab_late["exit_time"] == _ts(DAY, 135)

    def test_limit_up_clause1_not_time_gated(self):
        rows = _mk_rows(
            DAY, range(0, 10), lambda s: 10000.0,
            등락율=lambda s: 29.9 if s >= 4 else 5.0,
        )
        labels, _ = _labels(rows, [1])
        lab = labels[_ts(DAY, 1)]
        assert lab is not None
        assert lab["clause"] == 1
        assert lab["exit_time"] == _ts(DAY, 4)

    def test_0930_forced_cap_at_last_observed_row(self):
        # 발동 절 없음 → 09:30:00 상한 — 마지막 관측 초(09:29:57) 강제 청산.
        seconds = list(range(0, 1798))  # 마지막 = 초1797 = 09:29:57.
        rows = _mk_rows(DAY, seconds, lambda s: 10000.0)
        labels, stats = _labels(rows, [5])
        lab = labels[_ts(DAY, 5)]
        assert lab is not None
        assert lab["clause"] == 0
        assert lab["exit_time"] == _ts(DAY, 1797)
        assert stats["forced_cap"] == 1
        # 09:30:00 행이 있으면 그 행에서 캡.
        rows2 = _mk_rows(DAY, list(range(0, 1801)), lambda s: 10000.0)
        labels2, _ = _labels(rows2, [5])
        assert labels2[_ts(DAY, 5)]["exit_time"] == _ts(DAY, 1800)
        # 09:30:00 이후 행은 컨텍스트에서 제외된다(캡 불변).
        rows3 = _mk_rows(DAY, list(range(0, 1900)), lambda s: 10000.0)
        labels3, _ = _labels(rows3, [5])
        assert labels3[_ts(DAY, 5)]["exit_time"] == _ts(DAY, 1800)

    def test_entry_missing_and_bad_quote_excluded(self):
        rows = _mk_rows(DAY, [0, 1, 2, 4, 5, 6], lambda s: 10000.0)
        # t0=2 → entry 초3 결측 → 제외. t0=4 → entry 초5 존재 → 라벨.
        labels, stats = _labels(rows, [2, 4])
        assert labels[_ts(DAY, 2)] is None
        assert labels[_ts(DAY, 4)] is not None
        assert stats["entry_missing"] == 1
        rows_bad = _mk_rows(
            DAY, range(0, 6), lambda s: 10000.0,
            매도호가1=lambda s: 0.0 if s == 3 else 10000.0,
        )
        labels_bad, stats_bad = _labels(rows_bad, [2])
        assert labels_bad[_ts(DAY, 2)] is None
        assert stats_bad["entry_quote_bad"] == 1

    def test_missing_path_seconds_skipped(self):
        # 결측 초 구간에서 하락 — 발화는 최초 '관측' 초에서만.
        seconds = [0, 1, 2, 3, 10, 11]
        rows = _mk_rows(
            DAY, seconds, lambda s: 10000.0 if s <= 3 else 9300.0,
        )
        labels, _ = _labels(rows, [1])
        lab = labels[_ts(DAY, 1)]
        assert lab is not None
        assert lab["clause"] == 4
        assert lab["exit_time"] == _ts(DAY, 10)

    def test_bad_bid_at_fired_row_continues_holding(self):
        rows = _mk_rows(
            DAY, range(0, 12), lambda s: 10000.0 if s <= 4 else 9300.0,
            매수호가1=lambda s: 0.0 if s == 5 else (
                10000.0 if s <= 4 else 9300.0
            ),
        )
        labels, stats = _labels(rows, [1])
        lab = labels[_ts(DAY, 1)]
        assert lab is not None
        assert lab["exit_time"] == _ts(DAY, 6)  # 초5 호가 0 → 보유 지속.
        assert stats["bad_fire_quote_rows"] == 1

    def test_nominal_qty_floor_is_one(self):
        # 초고가 종목(> 배팅금액)도 qty=1 로 라벨된다.
        rows = _mk_rows(DAY, range(0, 8), lambda s: 6_000_000.0)
        labels, _ = _labels(rows, [1])
        assert labels[_ts(DAY, 1)] is not None
        assert L3_NOMINAL_BETTING < 6_000_000.0

    def test_multi_day_grid_rejected(self):
        rows = _mk_rows(DAY, range(0, 8), lambda s: 10000.0)
        with pytest.raises(ValueError):
            build_l3_labels(
                rows, [_ts(DAY, 1), _ts("20240104", 1)], SYNTH_SELL_TEXT,
                expected_sha=SYNTH_SELL_SHA,
            )


# ---------------------------------------------------------------------------
# 벡터 == 순수 (퍼즈) / 벡터 미러 == replay_champion_exit
# ---------------------------------------------------------------------------

def _fuzz_rows(seed: int, n: int = 240):
    rng = np.random.default_rng(seed)
    price = 10000.0 + np.cumsum(rng.integers(-40, 41, size=n)).astype(float)
    price = np.maximum(price, 500.0)
    pct = np.round(np.cumsum(rng.normal(0, 0.4, size=n)) + 5.0, 2)
    rows = {}
    missing = set(rng.choice(np.arange(30, n), size=n // 10, replace=False))
    for s in range(n):
        if s in missing:
            continue
        rows[_ts(DAY, s)] = {
            "현재가": float(price[s]),
            "시가": 10100.0,
            "등락율": float(min(pct[s], 29.4)),
            "초당매수수량": float(rng.integers(0, 300)),
            "초당매도수량": float(rng.integers(0, 300)),
            "시가총액": float(rng.choice([5000.0, 20000.0])),
            "매수총잔량": float(rng.integers(1, 400)),
            "매수호가1": float(price[s] - 10.0),
            "매도호가1": float(price[s] + 10.0),
        }
    return rows


class TestVectorPureEquivalence:
    def test_fuzz_labels_identical(self):
        for seed in range(6):
            rows = _fuzz_rows(20260706 + seed)
            t0_seconds = list(range(1, 150, 7))
            pure, _ = _labels(rows, t0_seconds, engine="pure")
            vector, _ = _labels(rows, t0_seconds, engine="vector")
            assert pure == vector

    def test_unknown_engine_rejected(self):
        rows = _mk_rows(DAY, range(0, 5), lambda s: 10000.0)
        with pytest.raises(ValueError):
            _labels(rows, [1], engine="gpu")


_COLS = ("현재가", "시가", "등락율", "초당매수수량", "초당매도수량", "시가총액",
         "매수총잔량", "매수호가1", "매수호가2", "매수호가3",
         "매수잔량1", "매수잔량2", "매수잔량3")


def _mk_day_arrays(n, price_fn, ladder_fn, *, cap=20000.0, pct_fn=None):
    idxs, rows = [], []
    for i in range(n):
        hh, rem = divmod(i, 3600)
        mm, ss = divmod(rem, 60)
        idxs.append(20250103090000 + hh * 10000 + mm * 100 + ss)
        bid1, bid2, bid3, r1, r2, r3 = ladder_fn(i)
        pct = pct_fn(i) if pct_fn else 5.0
        rows.append([price_fn(i), 9000.0, pct, 10.0, 10.0, cap, 1000.0,
                     bid1, bid2, bid3, r1, r2, r3])
    arr = np.array(rows, dtype=np.float64)
    ci = {c: k for k, c in enumerate(_COLS)}
    return np.array(idxs, dtype=np.int64), arr, ci


def _both_replays(idxs, arr, ci, *, buy_pos, buy_price, qty):
    pre = precompute_windows(arr, ci)
    ref = replay_champion_exit(
        idxs, arr, ci, pre, buy_time=int(idxs[buy_pos]),
        buy_price=buy_price, qty=qty,
    )
    ctx = build_day_context(idxs, arr, ci, pre)
    vec = replay_champion_exit_vector(
        ctx, buy_time=int(idxs[buy_pos]), buy_price=buy_price, qty=qty,
    )
    return ref, vec


class TestReplayMirror:
    def test_ladder_retry_scenario_identical(self):
        buy_pos = 60

        def price_fn(i):
            return 10000.0 if i <= buy_pos + 1 else 9400.0

        def ladder_fn(i):
            if i == buy_pos + 2:
                return (9390.0, 9380.0, 9370.0, 30.0, 30.0, 30.0)
            return (9390.0, 9380.0, 9370.0, 100.0, 0.0, 0.0)
        idxs, arr, ci = _mk_day_arrays(buy_pos + 6, price_fn, ladder_fn)
        ref, vec = _both_replays(
            idxs, arr, ci, buy_pos=buy_pos, buy_price=10000.0, qty=100,
        )
        assert ref == vec
        assert vec["cond"] == 4
        assert vec["sell_time"] == int(idxs[buy_pos + 3])

    def test_lastsell_scenario_identical(self):
        idxs, arr, ci = _mk_day_arrays(
            66, lambda i: 10000.0,
            lambda i: (9990.0, 9980.0, 9970.0, 0.0, 0.0, 0.0),
        )
        ref, vec = _both_replays(
            idxs, arr, ci, buy_pos=60, buy_price=10000.0, qty=100,
        )
        assert ref == vec
        assert vec["cond"] == 0 and vec["sell_price"] == 9990.0

    def test_entry_row_missing_identical(self):
        idxs, arr, ci = _mk_day_arrays(
            70, lambda i: 10000.0,
            lambda i: (9990.0, 9980.0, 9970.0, 1.0, 1.0, 1.0),
        )
        pre = precompute_windows(arr, ci)
        ctx = build_day_context(idxs, arr, ci, pre)
        vec = replay_champion_exit_vector(
            ctx, buy_time=20250103095959, buy_price=10000.0, qty=10,
        )
        assert vec == {"status": "entry_row_missing"}

    def test_fuzz_identical_to_scalar_replay(self):
        rng = np.random.default_rng(7)
        for trial in range(30):
            n = int(rng.integers(70, 260))
            walk = 10000.0 + np.cumsum(rng.integers(-60, 61, size=n))
            walk = np.maximum(walk.astype(float), 500.0)
            pcts = np.round(
                np.minimum(np.cumsum(rng.normal(0, 0.6, size=n)) + 3.0, 29.4), 2
            )
            rem_pool = rng.integers(0, 200, size=(n, 3)).astype(float)
            cap = float(rng.choice([4000.0, 20000.0]))

            def ladder_fn(i):
                b1 = walk[i] - 10.0
                return (b1, b1 - 10.0, b1 - 20.0, *rem_pool[i])

            idxs, arr, ci = _mk_day_arrays(
                n, lambda i: float(walk[i]), ladder_fn,
                cap=cap, pct_fn=lambda i: float(pcts[i]),
            )
            # 무작위 행 결측(관측 초만 평가 — 재현게이트 컨벤션).
            keep = np.sort(rng.choice(
                np.arange(n), size=max(65, n - n // 8), replace=False,
            ))
            idxs, arr = idxs[keep], arr[keep]
            buy_pos = int(rng.integers(1, len(idxs) - 2))
            qty = int(rng.integers(1, 600))
            ref, vec = _both_replays(
                idxs, arr, ci, buy_pos=buy_pos,
                buy_price=float(walk[keep[buy_pos]]), qty=qty,
            )
            assert ref == vec, f"trial={trial} buy_pos={buy_pos}"


# ---------------------------------------------------------------------------
# 등가성 게이트 — 영수증 로직 + 미니 e2e
# ---------------------------------------------------------------------------

class TestEquivalenceGate:
    def test_receipt_pass_fail_absent_corrupt(self, tmp_path):
        path = tmp_path / "v2_labeler_equivalence.json"
        assert equivalence_gate_pass(path) is False
        path.write_text("{broken", encoding="utf-8")
        assert equivalence_gate_pass(path) is False
        path.write_text(json.dumps(
            {"kind": "v2_labeler_equivalence", "gate_pass": False}
        ), encoding="utf-8")
        assert equivalence_gate_pass(path) is False
        path.write_text(json.dumps(
            {"kind": "other", "gate_pass": True}
        ), encoding="utf-8")
        assert equivalence_gate_pass(path) is False
        path.write_text(json.dumps(
            {"kind": "v2_labeler_equivalence", "gate_pass": True}
        ), encoding="utf-8")
        assert equivalence_gate_pass(path) is True

    def test_mini_end_to_end_gate(self, tmp_path):
        # 합성 back DB: stockinfo + 종목 테이블(급락 → 절4 발동 거래 1건).
        back = tmp_path / "stock_tick_back.db"
        conn = sqlite3.connect(back)
        conn.execute('CREATE TABLE stockinfo ("index" TEXT, "종목명" TEXT)')
        conn.execute("INSERT INTO stockinfo VALUES ('123456', '합성종목')")
        col_defs = ", ".join(f'"{c}" REAL' for c in _COLS)
        conn.execute(f'CREATE TABLE "123456" ("index" INTEGER, {col_defs})')
        buy_pos = 61
        for i in range(120):
            hh, rem = divmod(i, 3600)
            mm, ss = divmod(rem, 60)
            ts = 20250103090000 + hh * 10000 + mm * 100 + ss
            price = 10000.0 if i <= buy_pos + 1 else 9400.0
            bid1 = price - 10.0
            conn.execute(
                f'INSERT INTO "123456" VALUES ({", ".join(["?"] * 14)})',
                (ts, price, 9000.0, 5.0, 10.0, 10.0, 20000.0, 1000.0,
                 bid1, bid1 - 10.0, bid1 - 20.0, 500.0, 0.0, 0.0),
            )
        conn.commit()
        conn.close()
        ledger = tmp_path / "ledger.jsonl"
        rec = {
            "전략명": "GATE_TEST", "종목코드": "합성종목",
            "진입일자": "20250103", "진입시각": "090101",
            "매수시간": 20250103090101, "매도시간": 20250103090104,
            "매수가": 10000.0, "매도가": 9390.0, "매수금액": 1000000.0,
            "수익률": -6.3, "매도조건": "    if 수익률 >= 9 or 수익률 <= -5.0:",
            "R_매수후최고수익률": 0.0, "R_매수후최저수익률": -6.3,
        }
        ledger.write_text(
            json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        out = tmp_path / "v2_labeler_equivalence.json"
        report = run_equivalence_gate(
            ledger, back, back, out, generated="2026-07-06T00:00:00",
        )
        assert report["n_trades"] == 1
        assert report["n_both_match"] == 1
        assert report["equivalence_pct"] == 100.0
        assert report["gate_pass"] is True
        assert report["mismatches"] == []
        assert equivalence_gate_pass(out) is True

    def test_threshold_boundary_semantics(self):
        # 667거래 기준 0.999 임계는 사실상 전수 일치(666/667=0.99850 < 0.999).
        assert 666 / 667 < 0.999 <= 667 / 667


# ---------------------------------------------------------------------------
# to_arrays additive dtype + 사전등록 v2 로더
# ---------------------------------------------------------------------------

class TestAdditiveInfra:
    def test_to_arrays_label_dtypes_override(self):
        from alpha_lab.dataset.schema import ALL_FEATURES

        sample = {"date": 20240103, "code": "123456", "t0": 20240103090001}
        for name in ALL_FEATURES:
            sample[name] = 0.5
        sample["L3_net"] = 0.0123
        sample["L3_pos"] = 1
        arrays = to_arrays(
            [sample], label_dtypes={"L3_net": np.float32, "L3_pos": np.int8}
        )
        assert arrays["L3_net"].dtype == np.float32
        assert arrays["L3_pos"].dtype == np.int8
        assert arrays["L3_net"][0] == pytest.approx(0.0123, abs=1e-7)
        # 기본 경로(int8) 불변.
        legacy = dict(sample)
        del legacy["L3_net"], legacy["L3_pos"]
        legacy["L1_60"] = 1
        assert to_arrays([legacy])["L1_60"].dtype == np.int8

    def test_load_verified_prereg_v2_name(self, tmp_path):
        from cli.alpha_common import PREREG_V2_NAME, load_verified_prereg

        payload = {"program": "alpha_lab_v2", "sample_grid": {"stride_sec": 5}}
        sha = registry.seal(payload, tmp_path / PREREG_V2_NAME)
        (tmp_path / "preregistration_v2.sha256").write_text(
            sha + "\n", encoding="utf-8"
        )
        prereg, got_sha = load_verified_prereg(tmp_path, PREREG_V2_NAME)
        assert prereg["program"] == "alpha_lab_v2"
        assert got_sha == sha
        with pytest.raises(FileNotFoundError):
            load_verified_prereg(tmp_path)  # v1 이름은 이 디렉토리에 없다.


# ---------------------------------------------------------------------------
# CLI — build/gate 스모크 (합성 일 DB + 미니 봉인)
# ---------------------------------------------------------------------------

COLUMNS_54 = (
    "index", "현재가", "시가", "고가", "저가", "등락율", "당일거래대금", "체결강도",
    "초당매수수량", "초당매도수량", "거래대금증감", "전일비", "회전율", "전일동시간비",
    "시가총액", "라운드피겨위5호가이내", "VI해제시간", "VI가격", "VI호가단위",
    "초당거래대금", "고저평균대비등락율", "저가대비고가등락율", "초당매수금액",
    "초당매도금액", "당일매수금액", "최고매수금액", "최고매수가격", "당일매도금액",
    "최고매도금액", "최고매도가격", "매도호가5", "매도호가4", "매도호가3", "매도호가2",
    "매도호가1", "매수호가1", "매수호가2", "매수호가3", "매수호가4", "매수호가5",
    "매도잔량5", "매도잔량4", "매도잔량3", "매도잔량2", "매도잔량1", "매수잔량1",
    "매수잔량2", "매수잔량3", "매수잔량4", "매수잔량5", "매도총잔량", "매수총잔량",
    "매도수5호가잔량합", "관심종목",
)
CLI_DATE = "20240103"
POS_CODE, NEG_CODE = "111111", "222222"
LAST_SECOND = 390


def _cli_row(second: int, *, pos: bool) -> dict:
    row = {c: 0.0 for c in COLUMNS_54}
    row.update({
        "index": _ts(CLI_DATE, second),
        "현재가": 10000.0, "시가": 10000.0, "고가": 10000.0, "저가": 10000.0,
        "등락율": 2.5, "시가총액": 20000.0,
        "매도호가1": 10000.0,
        "매수호가1": 10600.0 if pos else 10000.0,
        "매도총잔량": 100.0, "매수총잔량": 100.0,
    })
    return row


@pytest.fixture(scope="module")
def cli_v2_env(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("alpha_cli_v2")
    db_dir, run_dir = root / "db", root / "run"
    db_dir.mkdir()
    run_dir.mkdir()
    conn = sqlite3.connect(db_dir / f"stock_tick_{CLI_DATE}.db")
    col_defs = ", ".join(
        f'"{c}" INTEGER PRIMARY KEY' if c == "index" else f'"{c}" REAL'
        for c in COLUMNS_54
    )
    holders = ", ".join("?" for _ in COLUMNS_54)
    for code, pos in ((POS_CODE, True), (NEG_CODE, False)):
        conn.execute(f'CREATE TABLE "{code}" ({col_defs})')
        conn.executemany(
            f'INSERT INTO "{code}" VALUES ({holders})',
            [tuple(_cli_row(s, pos=pos)[c] for c in COLUMNS_54)
             for s in range(0, LAST_SECOND + 1)],
        )
    conn.execute(
        'CREATE TABLE moneytop ("index" INTEGER PRIMARY KEY, "거래대금순위" TEXT)'
    )
    conn.executemany(
        "INSERT INTO moneytop VALUES (?, ?)",
        [(_ts(CLI_DATE, s), f"{POS_CODE};{NEG_CODE}")
         for s in range(0, LAST_SECOND + 1)],
    )
    conn.commit()
    conn.close()
    prereg = {
        "program": "alpha_lab_v2_smoke",
        "sealed_date": "2026-07-06",
        "sample_grid": {"stride_sec": 5, "days": {"y2024": [CLI_DATE]}},
        "label_spec_v2": {"champion_sell_sha256": SYNTH_SELL_SHA},
        "ledger": {"path": "n_trials_ledger.jsonl"},
    }
    sha = registry.seal(prereg, run_dir / "preregistration_v2.json")
    (run_dir / "preregistration_v2.sha256").write_text(sha + "\n", encoding="utf-8")
    strategy_db = root / "strategy.db"
    conn = sqlite3.connect(strategy_db)
    conn.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
    conn.execute(
        "INSERT INTO stocksell VALUES (?, ?)",
        ("ALP_EXITCHK_A_INCUMBENT", SYNTH_SELL_TEXT),
    )
    conn.commit()
    conn.close()
    return {"db_dir": db_dir, "run_dir": run_dir, "strategy_db": strategy_db}


class TestCliV2:
    def test_build_writes_v2_shard_and_receipt(self, cli_v2_env):
        from cli import alpha_dataset_v2

        code = alpha_dataset_v2.main([
            "build", "--mvp",
            "--run-dir", str(cli_v2_env["run_dir"]),
            "--db-dir", str(cli_v2_env["db_dir"]),
            "--strategy-db", str(cli_v2_env["strategy_db"]),
            "--log-level", "WARNING",
        ])
        assert code == 0
        shard = cli_v2_env["run_dir"] / "cache" / f"{CLI_DATE}.npz"
        with np.load(shard) as npz:
            keys = set(npz.files)
            assert keys == {"L3_net", "L3_pos", "code", "date", "features", "t0"}
            assert npz["L3_net"].dtype == np.float32
            assert npz["L3_pos"].dtype == np.int8
            assert npz["features"].shape[1] == 25
            n = npz["t0"].shape[0]
            assert n > 0
            # 플랜트: pos 코드(매수호가 10600)는 L3_pos=1, neg 코드는 0.
            pos_mask = npz["code"] == POS_CODE
            assert pos_mask.any() and (~pos_mask).any()
            assert np.all(npz["L3_pos"][pos_mask] == 1)
            assert np.all(npz["L3_pos"][~pos_mask] == 0)
        receipt = json.loads(
            (cli_v2_env["run_dir"] / "v2_dataset_build_receipt.json")
            .read_text(encoding="utf-8")
        )
        assert receipt["label_mode"] == "v2"
        assert receipt["l3_engine"] == "pure"  # 게이트 영수증 부재 → auto=pure.
        assert receipt["sell_sha_ok"] is True
        assert receipt["sell_sha256"] == SYNTH_SELL_SHA
        assert receipt["n_samples"] > 0
        assert receipt["labels"]["L3_pos"]["n"] == receipt["n_samples"]
        assert receipt["admission"] == "same_as_v1"

    def test_build_blocked_on_sell_sha_mismatch(self, cli_v2_env, tmp_path):
        from cli import alpha_dataset_v2

        bad_db = tmp_path / "strategy_bad.db"
        conn = sqlite3.connect(bad_db)
        conn.execute('CREATE TABLE stocksell ("index" TEXT, "전략코드" TEXT)')
        conn.execute(
            "INSERT INTO stocksell VALUES (?, ?)",
            ("ALP_EXITCHK_A_INCUMBENT", SYNTH_SELL_TEXT + "# drifted\n"),
        )
        conn.commit()
        conn.close()
        code = alpha_dataset_v2.main([
            "build", "--mvp",
            "--run-dir", str(cli_v2_env["run_dir"]),
            "--db-dir", str(cli_v2_env["db_dir"]),
            "--strategy-db", str(bad_db),
            "--log-level", "ERROR",
        ])
        assert code == 3

    def test_build_vector_requires_gate_receipt(self, cli_v2_env):
        from cli import alpha_dataset_v2

        gate_receipt = cli_v2_env["run_dir"] / "v2_labeler_equivalence.json"
        assert not gate_receipt.exists()
        code = alpha_dataset_v2.main([
            "build", "--mvp",
            "--run-dir", str(cli_v2_env["run_dir"]),
            "--db-dir", str(cli_v2_env["db_dir"]),
            "--strategy-db", str(cli_v2_env["strategy_db"]),
            "--l3-engine", "vector",
            "--log-level", "ERROR",
        ])
        assert code == 3
        # gate_pass 영수증이 생기면 vector 허용 + auto 도 vector 선택.
        gate_receipt.write_text(json.dumps(
            {"kind": "v2_labeler_equivalence", "gate_pass": True}
        ), encoding="utf-8")
        try:
            code2 = alpha_dataset_v2.main([
                "build", "--mvp",
                "--run-dir", str(cli_v2_env["run_dir"]),
                "--db-dir", str(cli_v2_env["db_dir"]),
                "--strategy-db", str(cli_v2_env["strategy_db"]),
                "--l3-engine", "vector",
                "--receipt-name", "v2_dataset_build_receipt_vec.json",
                "--log-level", "WARNING",
            ])
            assert code2 == 0
            vec_receipt = json.loads(
                (cli_v2_env["run_dir"] / "v2_dataset_build_receipt_vec.json")
                .read_text(encoding="utf-8")
            )
            assert vec_receipt["l3_engine"] == "vector"
            # 순수 경로 영수증과 표본 수·양성 수 동일(엔진 등가 재확인).
            pure_receipt = json.loads(
                (cli_v2_env["run_dir"] / "v2_dataset_build_receipt.json")
                .read_text(encoding="utf-8")
            )
            assert (
                vec_receipt["labels"]["L3_pos"]
                == pure_receipt["labels"]["L3_pos"]
            )
        finally:
            gate_receipt.unlink()

    def test_build_seal_violation_exits_3(self, cli_v2_env, tmp_path):
        from cli import alpha_dataset_v2

        bad_run = tmp_path / "bad_run"
        bad_run.mkdir()
        (bad_run / "preregistration_v2.json").write_text("{}", encoding="utf-8")
        (bad_run / "preregistration_v2.sha256").write_text(
            "0" * 64 + "\n", encoding="utf-8"
        )
        code = alpha_dataset_v2.main([
            "build", "--dates", CLI_DATE,
            "--run-dir", str(bad_run),
            "--db-dir", str(cli_v2_env["db_dir"]),
            "--strategy-db", str(cli_v2_env["strategy_db"]),
            "--log-level", "ERROR",
        ])
        assert code == 3
