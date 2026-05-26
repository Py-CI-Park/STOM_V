"""CONVERGENCE — 등급화 적합도(선택 그래디언트) 단위 테스트.

검증:
  (a) 게이트 통과 전략은 모든 실패 전략보다 graded 점수가 높다.
  (b) 실패 전략들 사이: 통과에 가까울수록 높다
      (MDD 30 vs cap25 > MDD 60; 거래 25 > 5; 작은 이익 > 큰 손실).
  (c) 각 항(trades/mdd/profit/uptrend)에 대해 단조 증가.
  (d) MDD≈0 / 0거래에서 크래시하지 않는다.
  (e) 하드 게이트 compute_fitness는 그대로 유지된다(졸업 기준).
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.score import (
    compute_fitness,
    compute_graded_fitness,
)


def _config():
    """min_trades=30, mdd_cap=25 — 태스크의 기준 게이트."""
    return LoopConfig(min_trades=30, mdd_cap=25.0)


_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _metrics(cagr, mdd, trades, profit):
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }


# ============================================================
# (a) 게이트 통과 > 모든 실패
# ============================================================

def test_passing_strategy_outranks_all_failing():
    """게이트 통과 전략(graded>=1.0)이 어떤 실패 전략보다도 높다."""
    cfg = _config()
    passing = compute_graded_fitness(
        _metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg
    )
    assert passing.gate_passed is True
    assert passing.graded >= 1.0

    # 다양한 실패 케이스 — 전부 passing보다 낮아야 한다.
    failing_metrics = [
        _metrics(30.0, 10.0, 5, 1_000_000),     # 거래 부족
        _metrics(30.0, 60.0, 50, 1_000_000),    # MDD 초과
        _metrics(5.0, 10.0, 50, -500_000),      # 손실
        _metrics(30.0, 24.0, 29, 500_000),      # 거래 거의 통과지만 미달
    ]
    for m in failing_metrics:
        f = compute_graded_fitness(m, _STEADY, cfg)
        assert f.gate_passed is False
        assert f.graded < 1.0
        assert passing.graded > f.graded


# ============================================================
# (b) 실패끼리: 통과에 가까울수록 높다
# ============================================================

def test_closer_mdd_ranks_higher_among_failing():
    """MDD 30(cap25에 근접)이 MDD 60보다 graded가 높다 (둘 다 게이트 실패)."""
    cfg = _config()
    near = compute_graded_fitness(_metrics(30.0, 30.0, 50, 1_000_000), _STEADY, cfg)
    far = compute_graded_fitness(_metrics(30.0, 60.0, 50, 1_000_000), _STEADY, cfg)
    assert near.gate_passed is False and far.gate_passed is False
    assert near.graded > far.graded
    assert near.mdd_term > far.mdd_term


def test_more_trades_ranks_higher_among_failing():
    """거래 25건이 5건보다 graded가 높다 (둘 다 min_trades=30 미달)."""
    cfg = _config()
    more = compute_graded_fitness(_metrics(30.0, 10.0, 25, 1_000_000), _STEADY, cfg)
    few = compute_graded_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert more.gate_passed is False and few.gate_passed is False
    assert more.graded > few.graded
    assert more.trades_term > few.trades_term


def test_small_profit_ranks_higher_than_big_loss_among_failing():
    """작은 양(+)의 이익이 큰 손실보다 graded가 높다 (거래 부족으로 둘 다 실패)."""
    cfg = _config()
    small_pos = compute_graded_fitness(_metrics(5.0, 10.0, 5, 50_000), _STEADY, cfg)
    big_loss = compute_graded_fitness(_metrics(5.0, 10.0, 5, -5_000_000), _STEADY, cfg)
    assert small_pos.gate_passed is False and big_loss.gate_passed is False
    assert small_pos.graded > big_loss.graded
    assert small_pos.profit_term > big_loss.profit_term


def test_profit_term_breakeven_is_about_half():
    """손익분기(0) profit_term은 ~0.5 (로지스틱 중앙)."""
    cfg = _config()
    breakeven = compute_graded_fitness(_metrics(5.0, 10.0, 5, 0), _STEADY, cfg)
    assert abs(breakeven.profit_term - 0.5) < 1e-6


# ============================================================
# (c) 각 항에 대해 단조 증가
# ============================================================

def test_monotonic_in_trades_term():
    """거래수가 늘수록(min 미만 구간) graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(30.0, 10.0, t, 1_000_000), _STEADY, cfg).graded
        for t in (3, 10, 20, 29)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_mdd_term():
    """MDD가 줄수록(cap 초과 구간) graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(30.0, mdd, 50, 1_000_000), _STEADY, cfg).graded
        for mdd in (100.0, 60.0, 40.0, 26.0)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_profit_term():
    """손익이 커질수록 graded 단조 증가."""
    cfg = _config()
    scores = [
        compute_graded_fitness(_metrics(5.0, 10.0, 5, p), _STEADY, cfg).graded
        for p in (-5_000_000, -500_000, 0, 500_000, 5_000_000)
    ]
    assert scores == sorted(scores)
    assert scores[0] < scores[-1]


def test_monotonic_in_uptrend_term():
    """우상향도(R²)가 높을수록 graded 단조 증가 (실패 구간, 동일 metrics)."""
    cfg = _config()
    # 거래 부족으로 게이트 실패 — uptrend_term만 다르게.
    m = _metrics(30.0, 10.0, 5, 1_000_000)
    steady = compute_graded_fitness(m, _STEADY, cfg)        # R²≈1
    spiky = compute_graded_fitness(m, [0, 0, 0, 0, 900], cfg)  # 낮은 R²
    assert steady.uptrend_term > spiky.uptrend_term
    assert steady.graded > spiky.graded


# ============================================================
# (d) 안전성: MDD≈0 / 0거래
# ============================================================

def test_mdd_zero_does_not_crash():
    """MDD≈0에서 예외 없이 결과를 낸다 (cap 이하로 본다)."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(20.0, 0.0, 50, 1_000_000), _STEADY, cfg)
    assert res.mdd_term == 1.0
    assert res.graded >= 0.0


def test_zero_trades_does_not_crash():
    """거래 0건에서 크래시 없이 trades_term=0, graded in [0,1)."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(0.0, 0.0, 0, 0), [], cfg)
    assert res.gate_passed is False
    assert res.trades_term == 0.0
    assert 0.0 <= res.graded < 1.0


def test_gate_distance_text_is_human_readable():
    """게이트 실패 시 gate_distance에 원인 단서가 담긴다."""
    cfg = _config()
    res = compute_graded_fitness(_metrics(30.0, 48.0, 50, -100_000), _STEADY, cfg)
    assert res.gate_passed is False
    # MDD 초과 + 손실 음수가 문자열에 드러나야 한다.
    assert "MDD" in res.gate_distance
    assert "cap" in res.gate_distance
    assert "negative" in res.gate_distance


# ============================================================
# (e) 하드 게이트는 그대로 유지된다 (졸업 기준)
# ============================================================

def test_hard_gate_compute_fitness_intact():
    """compute_fitness(하드 게이트)는 실패 전략을 여전히 score=0으로 거절한다."""
    cfg = _config()
    # 거래 부족 → 하드 게이트 실패 → score 0.
    hard = compute_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert hard.gate_passed is False
    assert hard.score == 0.0

    # 같은 입력에 대해 graded는 0보다 큰 그래디언트를 준다(선택 가능).
    graded = compute_graded_fitness(_metrics(30.0, 10.0, 5, 1_000_000), _STEADY, cfg)
    assert graded.graded > 0.0
    assert graded.graded < 1.0


def test_passing_graded_equals_one_plus_composite():
    """게이트 통과 시 graded == 1.0 + 하드 composite."""
    cfg = _config()
    m = _metrics(30.0, 10.0, 50, 1_000_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert hard.gate_passed is True
    assert abs(graded.graded - (1.0 + hard.score)) < 1e-9


# ============================================================
# (f) 적자 영역 그래디언트 결함 회귀 (P8)
#     큰 적자 범위(−수억~−수십억)에서도 profit_term/graded가 단조 변별돼야 한다.
#     기존 선형 로지스틱(scale≈1백만)은 이 범위 전체가 0으로 포화됐다.
# ============================================================

# wide baseline 영역의 실측 게이트 설정(min_trades=30, mdd_cap=35).
def _wide_config():
    return LoopConfig(min_trades=30, mdd_cap=35.0)


def test_deficit_gen0_below_gen1_core_acceptance():
    """핵심 수용: gen0(−12.4억/42691거래/MDD603)보다
    gen1(−0.997억/3967거래/MDD285)의 graded가 높아야 한다.

    둘 다 게이트 실패지만 gen1이 손실↓·거래↓·MDD↓로 '명백히 개선'됐으므로
    선택 그래디언트가 이를 반영해야 한다(이전엔 둘 다 ≈0이라 climb 실패)."""
    cfg = _wide_config()
    gen0 = compute_graded_fitness(
        _metrics(0.0, 603.0, 42691, -1_236_067_340), _STEADY, cfg
    )
    gen1 = compute_graded_fitness(
        _metrics(0.0, 285.0, 3967, -99_663_323), _STEADY, cfg
    )
    assert gen0.gate_passed is False and gen1.gate_passed is False
    assert gen1.graded > gen0.graded
    # 둘 다 [0,1) 범위(게이트 실패) 유지.
    assert 0.0 <= gen0.graded < 1.0
    assert 0.0 <= gen1.graded < 1.0


def test_profit_term_monotonic_across_large_deficits():
    """큰 적자 3종(−12억 < −1억 < −1천만)에서 profit_term이 단조 증가해야 한다.

    이전 선형 로지스틱은 이 범위 전체가 0으로 포화돼 변별 불가였다."""
    cfg = _wide_config()
    big = compute_graded_fitness(_metrics(0.0, 50.0, 50, -1_200_000_000), _STEADY, cfg)
    mid = compute_graded_fitness(_metrics(0.0, 50.0, 50, -100_000_000), _STEADY, cfg)
    small = compute_graded_fitness(_metrics(0.0, 50.0, 50, -10_000_000), _STEADY, cfg)
    # 손실이 작을수록 profit_term↑ (포화 없이 변별).
    assert big.profit_term < mid.profit_term < small.profit_term
    # 모두 손실이므로 0.5 미만(흑자 영역과 분리).
    assert small.profit_term < 0.5
    # graded(동일 구조항)도 같은 순서.
    assert big.graded < mid.graded < small.graded


def test_profit_positive_outranks_negative_among_failing():
    """흑자 게이트실패 > 적자 게이트실패: 수익이 양수면 더 높게.

    동일 구조(거래/MDD/우상향)에서 +1억(흑자)이 −1억(적자)보다 graded 높다."""
    cfg = _wide_config()  # mdd 50 > cap 35 → 둘 다 게이트 실패.
    profit = compute_graded_fitness(_metrics(0.0, 50.0, 50, 100_000_000), _STEADY, cfg)
    loss = compute_graded_fitness(_metrics(0.0, 50.0, 50, -100_000_000), _STEADY, cfg)
    assert profit.gate_passed is False and loss.gate_passed is False
    assert profit.profit_term > 0.5 > loss.profit_term
    assert profit.graded > loss.graded


def test_gate_passed_outranks_gate_failed_even_with_huge_loss_diff():
    """gate 통과(≥1.0) > gate 실패(<1.0) 불변 — 적자 변별을 살려도 유지."""
    cfg = _wide_config()
    passing = compute_graded_fitness(_metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg)
    # 가장 작은 적자(통과에 가장 가까운 실패)라도 통과 전략을 넘지 못한다.
    near_fail = compute_graded_fitness(_metrics(30.0, 36.0, 50, 5_000_000), _STEADY, cfg)
    assert passing.gate_passed is True and near_fail.gate_passed is False
    assert passing.graded >= 1.0 > near_fail.graded


def test_deficit_improves_with_lower_trades_and_mdd():
    """거래/MDD 개선 시 graded↑ (적자 유지, 동일 손실)."""
    cfg = _wide_config()
    worse = compute_graded_fitness(_metrics(0.0, 600.0, 42000, -100_000_000), _STEADY, cfg)
    better = compute_graded_fitness(_metrics(0.0, 285.0, 3900, -100_000_000), _STEADY, cfg)
    assert worse.gate_passed is False and better.gate_passed is False
    # 거래 적고 MDD 낮은 better가 더 높다.
    assert better.graded > worse.graded


# ============================================================
# (g) plateau 붕괴 방지 — sub-min-trades 페널티 (P8)
#     루프가 MDD를 낮추려 거래를 2~26건(min_trades 미달)으로 붕괴시키는 정체를
#     막는다. undertrade_factor=(trade/min)**2 를 gate-failed graded에 곱한다.
# ============================================================

def test_undertrade_penalty_two_trades_far_below_full_trades():
    """거래 2건(<<min) graded가 거래 35건(>=min, 타 지표 동일)보다 대폭 낮다.

    P8 핵심: 손익분기 근처·저MDD라도 거래 2건은 강하게 눌려야 루프가
    '거래 붕괴'를 더 이상 선택하지 않는다."""
    cfg = _config()  # min_trades=30, mdd_cap=25. MDD 60 → 둘 다 게이트 실패.
    two = compute_graded_fitness(_metrics(0.0, 60.0, 2, 0), _STEADY, cfg)
    full = compute_graded_fitness(_metrics(0.0, 60.0, 35, 0), _STEADY, cfg)
    assert two.gate_passed is False and full.gate_passed is False
    # 거래 2건 graded는 35건보다 훨씬 낮다(제곱 페널티).
    assert two.graded < full.graded
    # 제곱 페널티의 강도 확인: factor(2/30)**2≈0.0044 → graded가 1/100 미만 수준.
    assert two.graded < full.graded * 0.1


def test_undertrade_factor_inactive_at_min_trades():
    """거래수=min_trades면 페널티 없음(factor=1.0): 거래 30 vs 100 graded 동일 구조.

    [min_trades, softcap] 밴드 안에서는 거래수가 graded를 더 깎지 않는다."""
    cfg = _config()  # min_trades=30, mdd_cap=25, overtrade_softcap=150(LoopConfig 기본).
    at_min = compute_graded_fitness(_metrics(0.0, 60.0, 30, 0), _STEADY, cfg)
    in_band = compute_graded_fitness(_metrics(0.0, 60.0, 100, 0), _STEADY, cfg)
    assert at_min.gate_passed is False and in_band.gate_passed is False
    # 거래 30(=min)과 100(밴드 내, <softcap 150)은 undertrade/overtrade 모두 무벌점 →
    #   다른 항이 동일하므로 graded가 같아야 한다.
    assert abs(at_min.graded - in_band.graded) < 1e-12


def test_undertrade_penalty_disabled_when_min_trades_zero():
    """min_trades<=0이면 undertrade 페널티 비활성 — 거래 2건도 감점 없음."""
    cfg = LoopConfig(min_trades=0, mdd_cap=25.0)
    two = compute_graded_fitness(_metrics(0.0, 60.0, 2, 0), _STEADY, cfg)
    full = compute_graded_fitness(_metrics(0.0, 60.0, 35, 0), _STEADY, cfg)
    assert two.gate_passed is False and full.gate_passed is False
    # min_trades=0이면 trades_term=1.0(비활성) + undertrade_factor=1.0(비활성) →
    #   거래수에 무관하게 graded 동일.
    assert abs(two.graded - full.graded) < 1e-12


def test_undertrade_preserves_profit_over_loss_invariant():
    """페널티 적용 후에도 흑자>적자 불변(같은 거래수에서 곱셈 상수라 순서 보존)."""
    cfg = _config()
    profit = compute_graded_fitness(_metrics(0.0, 60.0, 5, 1_000_000), _STEADY, cfg)
    loss = compute_graded_fitness(_metrics(0.0, 60.0, 5, -1_000_000), _STEADY, cfg)
    assert profit.gate_passed is False and loss.gate_passed is False
    assert profit.graded > loss.graded


def test_undertrade_preserves_gate_passed_over_failed_invariant():
    """페널티가 곱셈([0,1])이라 gate-failed는 여전히 <1.0 < gate-passed."""
    cfg = _config()
    passing = compute_graded_fitness(_metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg)
    # 거래 2건 붕괴 전략(저MDD·손익분기)이라도 통과 전략을 넘지 못한다.
    collapsed = compute_graded_fitness(_metrics(0.0, 5.0, 2, 0), _STEADY, cfg)
    assert passing.gate_passed is True and collapsed.gate_passed is False
    assert passing.graded >= 1.0 > collapsed.graded
