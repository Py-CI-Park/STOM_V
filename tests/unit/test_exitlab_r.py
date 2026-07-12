"""alpha_lab.exitlab_r.patch_exit 단위 테스트 — D5-R 패치 청산 리플레이.

실DB 불필요(전부 합성 DayContext). 실행:
    python -m pytest tests/unit/test_exitlab_r.py -q

검증 축:
- identity 패치(patch=None) == replay_champion_exit_vector (합성 퍼즈).
- 순수 == 벡터 (Family A·B, 무작위 퍼즈).
- Family A: 절5 배수 하향 → 발동 더 늦음(승자 연장), 배수 범위 검증.
- Family B: 신규 저활력 절 발동 조건(hold≥T ∧ best<x ∧ sp<y)·절 순서 보존
  (현직 절이 먼저 발동하면 신규 절 미도달)·승자 보호(best≥x → 미발동).
- analyze_path: t=T 상태(누적최고·수익률) 재구성·held 판정.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pytest

from alpha_lab.dataset.labels_v2 import (
    build_day_context,
    replay_champion_exit_vector,
)
from alpha_lab.distill.replay import precompute_windows
from alpha_lab.exitlab_r.patch_exit import (
    B_CLAUSE_TAG,
    Patch,
    analyze_path,
    eval_row_clause_patched,
    replay_patched_pure,
    replay_patched_vector,
    time_stop_cut,
)


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
            "매수호가2": price, "매수호가3": price,
            "매수잔량1": 100000.0, "매수잔량2": 100000.0, "매수잔량3": 100000.0,
        }
        for key, fn in overrides.items():
            row[key] = float(fn(s))
        rows[_ts(day, s)] = row
    return rows


# 사다리 체결까지 포함한 전 컬럼(replay.load_day_rows 출력 미러 — day_context_from_rows
# 는 L3 라벨용 9컬럼만 적재해 사다리 잔량이 0이 되므로 여기선 쓰지 않는다).
_FULL_COLS = (
    "현재가", "시가", "등락율", "초당매수수량", "초당매도수량", "시가총액",
    "매수총잔량", "매수호가1", "매도호가1", "매수호가2", "매수호가3",
    "매수잔량1", "매수잔량2", "매수잔량3",
)


def _ctx(rows, day="20220401"):
    keys = sorted(rows)
    idxs = np.array(keys, dtype=np.int64)
    arr = np.array(
        [[float(rows[k].get(c, 0.0)) for c in _FULL_COLS] for k in keys],
        dtype=np.float64,
    )
    ci = {c: i for i, c in enumerate(_FULL_COLS)}
    pre = precompute_windows(arr, ci)
    return build_day_context(idxs, arr, ci, pre)


# ---------------------------------------------------------------------------
# Patch 명세 검증
# ---------------------------------------------------------------------------

class TestPatchSpec:
    def test_identity(self):
        p = Patch()
        assert p.family is None and p.trailing_keep == 0.6

    def test_family_a_range(self):
        assert Patch(family="A", mult=0.55).trailing_keep == 0.55
        assert Patch(family="A", mult=0.50).trailing_keep == 0.50
        with pytest.raises(ValueError):
            Patch(family="A", mult=0.6)   # 하향이 아님.
        with pytest.raises(ValueError):
            Patch(family="A")             # mult 누락.

    def test_family_b_requires_txy(self):
        Patch(family="B", T=120, x=1.0, y=0.0)
        with pytest.raises(ValueError):
            Patch(family="B", T=120, x=1.0)  # y 누락.

    def test_unknown_family(self):
        with pytest.raises(ValueError):
            Patch(family="Z", mult=0.5)


# ---------------------------------------------------------------------------
# identity == replay_champion_exit_vector
# ---------------------------------------------------------------------------

class TestIdentityMatchesIncumbent:
    def test_hard_stop_scenario(self):
        # 급락 → 절4(수익률<=-5) 발동.
        rows = _mk_rows("20220401", range(0, 200),
                        lambda s: 10000.0 if s == 0 else 9300.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        ref = replay_champion_exit_vector(ctx, buy_time=buy, buy_price=10000.0, qty=100)
        idp = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100, patch=Patch())
        idv = replay_patched_vector(ctx, buy_time=buy, buy_price=10000.0, qty=100, patch=Patch())
        assert ref["status"] == "ok" == idp.status
        assert (idp.sell_time, idp.sell_price, idp.cond) == (ref["sell_time"], ref["sell_price"], ref["cond"])
        assert (idp.sell_time, idp.sell_price, idp.cond) == (idv.sell_time, idv.sell_price, idv.cond)

    def test_last_sell_scenario(self):
        # 잔잔한 상승 — 어떤 절도 발동 안 함 → LastSell(절0).
        rows = _mk_rows("20220401", range(0, 150), lambda s: 10000.0 + s)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        ref = replay_champion_exit_vector(ctx, buy_time=buy, buy_price=10000.0, qty=50)
        idp = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=50, patch=Patch())
        assert idp.cond == 0 == ref["cond"]
        assert idp.sell_time == ref["sell_time"]


# ---------------------------------------------------------------------------
# Family B — 신규 저활력 절
# ---------------------------------------------------------------------------

class TestFamilyB:
    def _low_vitality_ctx(self):
        # 매수 10000 → 이후 9990 유지(손실·저피크·신저가 미형성). 시총<1만(cap 블록).
        rows = _mk_rows("20220401", range(0, 300),
                        lambda s: 10000.0 if s == 0 else 9990.0,
                        시가총액=lambda s: 5000.0)
        return _ctx(rows), _ts("20220401", 0)

    def test_fires_after_T_when_low(self):
        ctx, buy = self._low_vitality_ctx()
        inc = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100, patch=Patch())
        patched = replay_patched_pure(
            ctx, buy_time=buy, buy_price=10000.0, qty=100,
            patch=Patch(family="B", T=120, x=1.0, y=0.0),
        )
        assert patched.cond == B_CLAUSE_TAG
        assert patched.hold_exit >= 120
        # 신규 절이 현직보다 먼저 절단(저활력 → 현직은 LastSell 까지 감).
        assert patched.sell_time < inc.sell_time

    def test_winner_protected(self):
        # best 가 x 이상까지 오른 뒤 하락 — best<x 위배 → 신규 절 미발동.
        def price(s):
            if s == 0:
                return 10000.0
            if s < 30:
                return 10250.0     # best ≈ +2%
            return 9990.0
        rows = _mk_rows("20220401", range(0, 300), price, 시가총액=lambda s: 5000.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        patched = replay_patched_pure(
            ctx, buy_time=buy, buy_price=10000.0, qty=100,
            patch=Patch(family="B", T=120, x=1.0, y=0.0),
        )
        assert patched.cond != B_CLAUSE_TAG   # best≥1.0 이라 보호됨.

    def test_x_threshold_separates(self):
        # best ≈ +1.2%: x=1.0 이면 보호, x=1.5 이면 절단.
        def price(s):
            if s == 0:
                return 10000.0
            if s < 30:
                return 10150.0
            return 9990.0
        rows = _mk_rows("20220401", range(0, 300), price, 시가총액=lambda s: 5000.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        p10 = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100,
                                  patch=Patch(family="B", T=120, x=1.0, y=0.0))
        p15 = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100,
                                  patch=Patch(family="B", T=120, x=1.5, y=0.0))
        assert p10.cond != B_CLAUSE_TAG
        assert p15.cond == B_CLAUSE_TAG

    def test_precedence_incumbent_wins(self):
        # 현직 절4(하드손절) 발동 행에서는 신규 절이 도달하지 못한다.
        rows = _mk_rows("20220401", range(0, 300),
                        lambda s: 10000.0 if s == 0 else 9300.0,
                        시가총액=lambda s: 5000.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        patched = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100,
                                      patch=Patch(family="B", T=120, x=1.0, y=0.0))
        assert patched.cond == 4   # 하드손절이 우선.


# ---------------------------------------------------------------------------
# Family A — 트레일링 완화
# ---------------------------------------------------------------------------

class TestFamilyA:
    def _trailing_ctx(self):
        # best ≈ +5% 까지 상승 후 계단식 하락 — 절5(트레일)가 어딘가에서 발동.
        def price(s):
            if s == 0:
                return 10000.0
            if s < 40:
                return 10500.0            # best≈+4.8
            return 10500.0 - (s - 40) * 5.0
        rows = _mk_rows("20220401", range(0, 400), price)
        return _ctx(rows), _ts("20220401", 0)

    def test_relaxed_holds_longer(self):
        ctx, buy = self._trailing_ctx()
        base = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100, patch=Patch())
        a2 = replay_patched_pure(ctx, buy_time=buy, buy_price=10000.0, qty=100,
                                 patch=Patch(family="A", mult=0.50))
        # 완화 배수는 절5 발동을 늦춘다 → 더 오래 보유(청산 시각 ≥ 현직).
        assert a2.sell_time >= base.sell_time
        if base.cond == 5:
            assert a2.hold_exit >= base.hold_exit


# ---------------------------------------------------------------------------
# 순수 == 벡터 퍼즈
# ---------------------------------------------------------------------------

class TestPureVectorParity:
    @pytest.mark.parametrize("seed", range(6))
    def test_fuzz(self, seed):
        rng = np.random.default_rng(seed)
        base = 10000.0
        prices = [base]
        for _ in range(299):
            prices.append(max(9000.0, prices[-1] * (1.0 + rng.normal(0, 0.004))))
        rows = _mk_rows("20220401", range(0, 300),
                        lambda s: round(prices[s] / 10.0) * 10.0,
                        시가총액=lambda s: 5000.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        for patch in (Patch(), Patch(family="A", mult=0.55), Patch(family="A", mult=0.50),
                      Patch(family="B", T=120, x=1.0, y=0.0),
                      Patch(family="B", T=240, x=1.5, y=0.0)):
            p = replay_patched_pure(ctx, buy_time=buy, buy_price=base, qty=100, patch=patch)
            v = replay_patched_vector(ctx, buy_time=buy, buy_price=base, qty=100, patch=patch)
            assert (p.sell_time, p.sell_price, p.cond) == (v.sell_time, v.sell_price, v.cond), \
                f"patch={patch.family} seed={seed}"


# ---------------------------------------------------------------------------
# analyze_path — R1 t=T 상태
# ---------------------------------------------------------------------------

class TestAnalyzePath:
    def test_state_reconstruction(self):
        # 완만한 상승 — held at all T, best_T 단조 증가.
        rows = _mk_rows("20220401", range(0, 300), lambda s: 10000.0 + s * 2.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        pa = analyze_path(ctx, buy_time=buy, buy_price=10000.0, qty=100)
        assert pa.status == "ok"
        assert pa.per_T[120]["held"] == 1
        assert pa.per_T[240]["best_T"] >= pa.per_T[120]["best_T"]  # 누적최고 단조.

    def test_not_held_when_early_exit(self):
        # 즉시 급락 → 현직 조기 청산 → 긴 T 에서 held=0.
        rows = _mk_rows("20220401", range(0, 300),
                        lambda s: 10000.0 if s == 0 else 9300.0)
        ctx = _ctx(rows)
        buy = _ts("20220401", 0)
        pa = analyze_path(ctx, buy_time=buy, buy_price=10000.0, qty=100)
        assert pa.inc_hold < 120
        assert pa.per_T[120]["held"] == 0


# ---------------------------------------------------------------------------
# time_stop_cut — 순수 전역 절단(R1 대조군)
# ---------------------------------------------------------------------------

def test_time_stop_cut_fires_at_T():
    rows = _mk_rows("20220401", range(0, 300), lambda s: 10000.0 + s)
    ctx = _ctx(rows)
    buy = _ts("20220401", 0)
    cut = time_stop_cut(ctx, buy_time=buy, buy_price=10000.0, qty=100, T=120)
    assert cut.status == "ok"
    assert cut.hold_exit >= 120
