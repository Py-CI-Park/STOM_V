"""sell_clause_lab 단위 테스트 — 미러 등가·드롭 이동·full-mask·판정 경계.

핵심: 합성 DayContext(duck-typing)에서 drop=∅ 결과가 labels_v2 원본 함수와
완전 동일해야 한다(미러 드리프트 즉시 검출 — §14-F9 전수 게이트의 축소판).
"""
import os
import sys
from types import SimpleNamespace

import numpy as np
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from alpha_lab.dataset import labels_v2 as lv2  # noqa: E402
from alpha_lab.sell_clause_lab import harness  # noqa: E402
from alpha_lab.sell_clause_lab.judge_s import (  # noqa: E402
    _classify, _grade, EFFECT_FLOOR_PP)


def _synth_ctx(n=240, seed=7):
    """합성 컨텍스트 — labels_v2/하니스가 쓰는 필드만 duck-typing 으로 구성."""
    rng = np.random.default_rng(seed)
    price = rng.uniform(5000, 20000, n)
    day = 20220517
    hms = 90100 + np.arange(n)  # 09:01:00~ (초 단위 증가, 93000 미만 유지)
    ctx = SimpleNamespace(
        n=n,
        idxs=(day * 1_000_000 + hms).astype(np.int64),
        sec=np.arange(n, dtype=np.int64),
        price=price,
        open_=np.full(n, 9000.0),
        pct=rng.uniform(-3, 12, n),
        prev=price * rng.uniform(0.99, 1.01, n),
        sellv=rng.uniform(0, 500, n),
        buyv=rng.uniform(0, 500, n),
        bidtot=rng.uniform(100, 5000, n),
        cap=rng.choice([500.0, 3000.0, 20000.0], n),
        ma60=rng.uniform(5000, 20000, n),
        ang30=rng.uniform(-5, 20, n),
        rmin60=rng.uniform(4000, 19000, n),
        open_neg=rng.random(n) < 0.3,
        capgate=rng.random(n) < 0.6,
        tgate=np.ones(n, dtype=bool),
        c1_row=rng.random(n) < 0.02,
        c6_row=rng.random(n) < 0.05,
        c7_row=rng.random(n) < 0.05,
        c8_row=rng.random(n) < 0.05,
        c9_row=rng.random(n) < 0.05,
        ask1=price + 10,
        bid1=price - 10,
    )
    return ctx


# ── 미러 등가(드리프트 검출) ─────────────────────────────────────────────
def test_scalar_mirror_equals_original_when_no_drop():
    ctx = _synth_ctx()
    rng = np.random.default_rng(11)
    empty = frozenset()
    for _ in range(300):
        i = int(rng.integers(0, ctx.n))
        sp = float(rng.uniform(-8, 12))
        best = float(rng.uniform(0, 8))
        hold = int(rng.integers(0, 120))
        assert harness.eval_row_clause_drop(
            ctx, i, sp=sp, best=best, hold=hold, drop=empty
        ) == lv2._eval_row_clause(ctx, i, sp=sp, best=best, hold=hold)


def test_vector_mirror_equals_original_when_no_drop():
    ctx = _synth_ctx(seed=13)
    fire_h, sp_h, best_h, hold_h = harness.fire_arrays_drop(
        ctx, lo=1, hi=ctx.n, entry_pos=0, bg=5_000_000.0, qty=300,
        drop=frozenset())
    fire_o, sp_o, best_o, hold_o = lv2._fire_arrays(
        ctx, lo=1, hi=ctx.n, entry_pos=0, bg=5_000_000.0, qty=300)
    assert np.array_equal(fire_h, fire_o)
    assert np.array_equal(sp_h, sp_o) and np.array_equal(best_h, best_o)
    assert np.array_equal(hold_h, hold_o)


# ── 드롭 의미론 — 제거 시 같은 행의 후속 절로 이동 ───────────────────────
def _crafted_ctx():
    """행 140 에서 절 3(최저이탈)과 절 5(트레일링)가 동시에 참이 되는 구성."""
    ctx = _synth_ctx(seed=17)
    i = 140
    ctx.pct[i] = 5.0                       # c1 아님.
    ctx.open_neg = np.zeros(ctx.n, dtype=bool)   # c2 차단.
    ctx.price[11:71] = 15000.0             # low_price(60, hold=70) = 15000.
    ctx.price[i] = 10000.0                 # cur < low → c3 성립(hold>60 필요).
    ctx.cap[i] = 20000.0                   # c6~c9 게이트 차단.
    return ctx, i


def test_drop_moves_fire_to_next_clause_scalar():
    ctx, i = _crafted_ctx()
    kw = dict(sp=1.0, best=5.0, hold=70)   # c5: best>3 ∧ best*0.6=3.0 ≥ sp.
    assert harness.eval_row_clause_drop(ctx, i, drop=frozenset(), **kw) == 3
    assert harness.eval_row_clause_drop(ctx, i, drop=frozenset({3}), **kw) == 5
    assert harness.eval_row_clause_drop(
        ctx, i, drop=frozenset({3, 5}), **kw) is None


def test_fullmask_never_fires():
    ctx = _synth_ctx(seed=23)
    allset = harness.normalize_drop(harness.DROP_ALL)
    rng = np.random.default_rng(5)
    for _ in range(200):
        i = int(rng.integers(0, ctx.n))
        assert harness.eval_row_clause_drop(
            ctx, i, sp=float(rng.uniform(-8, 12)),
            best=float(rng.uniform(0, 8)), hold=int(rng.integers(0, 120)),
            drop=allset) is None
    fire, *_ = harness.fire_arrays_drop(
        ctx, lo=1, hi=ctx.n, entry_pos=0, bg=5e6, qty=300, drop=allset)
    assert not fire.any()


def test_vector_drop_matches_scalar_attribution():
    ctx, i = _crafted_ctx()
    got = list(harness._fire_vector_drop(
        ctx, lo=i, hi=i + 1, entry_pos=0, bg=5e6, qty=300,
        drop=frozenset({3})))
    # 벡터가 그 행을 발화로 보면 스칼라 어트리뷰션이 3이 아닌 절을 줘야 한다.
    for _, clause in got:
        assert clause != 3


# ── drop 정규화 ──────────────────────────────────────────────────────────
def test_normalize_drop():
    assert harness.normalize_drop(None) == frozenset()
    assert harness.normalize_drop(3) == frozenset({3})
    assert harness.normalize_drop("all") == frozenset(range(1, 10))
    with pytest.raises(ValueError):
        harness.normalize_drop(0)
    with pytest.raises(ValueError):
        harness.normalize_drop(10)


# ── 판정 경계(§14-F3·F4) ─────────────────────────────────────────────────
def test_grade_boundaries():
    assert _grade(2000, {2022: 400, 2023: 400}) == "formal"
    assert _grade(2000, {2022: 399, 2023: 900}) == "observational"
    assert _grade(150, {2022: 80, 2023: 70}) == "observational"
    assert _grade(99, {2022: 50, 2023: 49}) == "insufficient"


def test_classify_boundaries():
    c = _classify
    assert c(+0.15, +0.05, +0.30, True, False, 0.05, True) == "removal_candidate"
    assert c(-0.15, -0.30, -0.05, False, True, 0.05, True) == "load_bearing"
    assert c(+0.15, +0.05, +0.30, True, False, 0.05, False) != "removal_candidate"
    assert c(+0.07, +0.02, +0.12, True, False, 0.05, True) == "weak_signal"
    assert c(+0.02, -0.10, +0.15, False, False, 0.50, True) == "no_detect_power"
    assert c(+0.02, -0.03, +0.06, False, False, 0.04, True) == "no_detect_local_opt"
    assert EFFECT_FLOOR_PP == 0.10
