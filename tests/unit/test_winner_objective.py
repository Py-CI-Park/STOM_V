"""P7 — 절대수익 최적화(winner_objective) 단위 테스트.

검증:
  (a) objective='profit': 고수익 통과전략이 저수익 통과전략보다 graded↑.
  (b) objective='risk_adjusted'(기본): 현행 1.0+composite 동작 보존(하위호환).
  (c) objective='balanced': composite·(1-w)+profit_term·w 블렌드.
  (d) gate-failed 분기는 objective와 무관하게 불변(profit_term×mean).
  (e) 통과(graded≥1.0)>실패(<1.0) 불변식이 모든 objective에서 유지.
  (f) winner 선택 헬퍼: 'profit'은 total_profit 최대(동률 시 MDD 낮은 것),
      'risk_adjusted'는 fit.score, 'balanced'는 블렌드.
  (g) gen8(+537K) vs gen13(+230K) 재현: profit 모드에서 gen8이 winner.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller.loop import _winner_compare_key, _winner_score_value
from ai_strategy_loop.fitness.score import compute_fitness, compute_graded_fitness

# 우상향 직선(R²≈1) — 게이트 통과 전략의 equity로 쓴다.
_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _metrics(cagr, mdd, trades, profit):
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }


def _cfg(objective="risk_adjusted", **kw):
    """min_trades=30, mdd_cap=25 기본 게이트 + objective."""
    return LoopConfig(min_trades=30, mdd_cap=25.0, winner_objective=objective, **kw)


# ============================================================
# (a) profit 모드: 고수익 통과전략 > 저수익 통과전략
# ============================================================

def test_profit_mode_high_profit_outranks_low_profit_among_passing():
    """objective='profit': 둘 다 게이트 통과면 수익 큰 쪽이 graded 높다."""
    cfg = _cfg("profit")
    # 동일 Calmar/R²/거래/MDD, 수익만 다르게 (둘 다 게이트 통과).
    #   기본 profit_scale(1M)로도 537만 > 230만이면 profit_term 단조 증가로 graded↑.
    high = compute_graded_fitness(_metrics(30.0, 10.0, 50, 5_370_000), _STEADY, cfg)
    low = compute_graded_fitness(_metrics(30.0, 10.0, 50, 2_300_000), _STEADY, cfg)
    assert high.gate_passed and low.gate_passed
    assert high.graded > low.graded
    assert high.objective == "profit"


def test_profit_mode_passing_still_ge_one():
    """profit 모드에서도 통과 전략은 graded≥1.0 (통과>실패 불변)."""
    cfg = _cfg("profit")
    res = compute_graded_fitness(_metrics(30.0, 10.0, 50, 1_000_000), _STEADY, cfg)
    assert res.gate_passed
    assert res.graded >= 1.0


def test_profit_mode_passing_outranks_failing():
    """profit 모드에서 통과(graded≥1.0)가 모든 실패(graded<1.0)보다 위."""
    cfg = _cfg("profit")
    passing = compute_graded_fitness(_metrics(30.0, 10.0, 50, 100_000), _STEADY, cfg)
    failing = compute_graded_fitness(_metrics(30.0, 60.0, 50, 9_000_000), _STEADY, cfg)
    assert passing.gate_passed and not failing.gate_passed
    assert passing.graded >= 1.0 > failing.graded


# ============================================================
# (b) risk_adjusted(기본): 현행 동작 보존 (하위호환)
# ============================================================

def test_risk_adjusted_default_unchanged():
    """미설정(기본 risk_adjusted)이면 graded == 1.0 + 하드 composite (기존 동작)."""
    cfg = LoopConfig(min_trades=30, mdd_cap=25.0)  # winner_objective 미설정.
    assert cfg.winner_objective == "risk_adjusted"
    m = _metrics(30.0, 10.0, 50, 1_000_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert hard.gate_passed
    assert abs(graded.graded - (1.0 + hard.score)) < 1e-9


def test_risk_adjusted_ignores_profit_among_passing():
    """risk_adjusted에서는 수익이 달라도 composite 같으면 graded가 같다."""
    cfg = _cfg("risk_adjusted")
    a = compute_graded_fitness(_metrics(30.0, 10.0, 50, 537_000), _STEADY, cfg)
    b = compute_graded_fitness(_metrics(30.0, 10.0, 50, 230_000), _STEADY, cfg)
    assert abs(a.graded - b.graded) < 1e-9  # composite 동일 → graded 동일.


# ============================================================
# (c) balanced: 블렌드
# ============================================================

def test_balanced_blends_composite_and_profit():
    """balanced: graded-1.0 == composite·(1-w) + profit_term·w."""
    cfg = _cfg("balanced", profit_weight=0.5)
    m = _metrics(30.0, 10.0, 50, 500_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    expected_term = hard.score * 0.5 + graded.profit_term * 0.5
    assert abs((graded.graded - 1.0) - expected_term) < 1e-9


def test_balanced_weight_one_matches_profit_term():
    """profit_weight=1.0이면 balanced 통과항이 profit_term과 같다."""
    cfg = _cfg("balanced", profit_weight=1.0)
    m = _metrics(30.0, 10.0, 50, 500_000)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert abs((graded.graded - 1.0) - graded.profit_term) < 1e-9


def test_balanced_weight_zero_matches_risk_adjusted():
    """profit_weight=0.0이면 balanced 통과항이 composite(risk_adjusted)와 같다."""
    cfg = _cfg("balanced", profit_weight=0.0)
    m = _metrics(30.0, 10.0, 50, 500_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert abs((graded.graded - 1.0) - hard.score) < 1e-9


# ============================================================
# (d) gate-failed 분기는 objective와 무관하게 불변
# ============================================================

def test_gate_failed_branch_invariant_across_objectives():
    """게이트 실패 graded는 objective와 무관하게 동일(profit_term×mean 그대로)."""
    m = _metrics(30.0, 60.0, 50, 1_000_000)  # MDD 초과 → 실패.
    ra = compute_graded_fitness(m, _STEADY, _cfg("risk_adjusted"))
    pr = compute_graded_fitness(m, _STEADY, _cfg("profit"))
    ba = compute_graded_fitness(m, _STEADY, _cfg("balanced"))
    assert not (ra.gate_passed or pr.gate_passed or ba.gate_passed)
    assert abs(ra.graded - pr.graded) < 1e-12
    assert abs(ra.graded - ba.graded) < 1e-12
    assert ra.graded < 1.0


# ============================================================
# (f) winner 선택 헬퍼 (loop)
# ============================================================

def test_winner_score_profit_is_total_profit():
    """profit 모드 winner 점수 = total_profit."""
    cfg = _cfg("profit")
    m = _metrics(30.0, 10.0, 50, 537_000)
    fit = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert _winner_score_value(fit, graded, cfg) == 537_000.0


def test_winner_score_risk_adjusted_is_fit_score():
    """risk_adjusted 모드 winner 점수 = fit.score(하드 composite)."""
    cfg = _cfg("risk_adjusted")
    m = _metrics(30.0, 10.0, 50, 537_000)
    fit = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert _winner_score_value(fit, graded, cfg) == fit.score


def test_winner_key_profit_breaks_tie_by_lower_mdd():
    """profit 동률이면 MDD 낮은 쪽 키가 더 크다(우선)."""
    cfg = _cfg("profit")
    m_lowmdd = _metrics(30.0, 8.0, 50, 500_000)
    m_himdd = _metrics(30.0, 20.0, 50, 500_000)
    f1 = compute_fitness(m_lowmdd, _STEADY, cfg)
    g1 = compute_graded_fitness(m_lowmdd, _STEADY, cfg)
    f2 = compute_fitness(m_himdd, _STEADY, cfg)
    g2 = compute_graded_fitness(m_himdd, _STEADY, cfg)
    assert _winner_compare_key(f1, g1, cfg) > _winner_compare_key(f2, g2, cfg)


# ============================================================
# (g) gen8(+537K) vs gen13(+230K) 재현
# ============================================================

def test_gen8_beats_gen13_in_profit_mode():
    """profit 모드: gen8(고수익 +537K, MDD 큼)이 gen13(저수익 +230K, 위험조정 우수)을
    winner 비교에서 이긴다. risk_adjusted였다면 gen13이 이겼을 시나리오."""
    # gen13: 낮은 MDD(위험조정 우수) → composite 큼, 수익은 적음.
    gen13 = _metrics(cagr=40.0, mdd=10.0, trades=50, profit=230_000)
    # gen8: 높은 수익이지만 MDD 큼 → composite 작음.
    gen8 = _metrics(cagr=30.0, mdd=22.0, trades=50, profit=537_000)

    # --- risk_adjusted: gen13이 winner(현행 문제 재현) ---
    cfg_ra = _cfg("risk_adjusted")
    f13 = compute_fitness(gen13, _STEADY, cfg_ra)
    g13 = compute_graded_fitness(gen13, _STEADY, cfg_ra)
    f8 = compute_fitness(gen8, _STEADY, cfg_ra)
    g8 = compute_graded_fitness(gen8, _STEADY, cfg_ra)
    assert f13.gate_passed and f8.gate_passed
    # gen13 composite가 더 큼(낮은 MDD → 높은 Calmar).
    assert _winner_compare_key(f13, g13, cfg_ra) > _winner_compare_key(f8, g8, cfg_ra)

    # --- profit: gen8이 winner(사용자 의도) ---
    cfg_pr = _cfg("profit")
    f8p = compute_fitness(gen8, _STEADY, cfg_pr)
    g8p = compute_graded_fitness(gen8, _STEADY, cfg_pr)
    f13p = compute_fitness(gen13, _STEADY, cfg_pr)
    g13p = compute_graded_fitness(gen13, _STEADY, cfg_pr)
    assert _winner_compare_key(f8p, g8p, cfg_pr) > _winner_compare_key(f13p, g13p, cfg_pr)
    # graded도 gen8이 더 높다(profit 모드 통과 분기 = 1+profit_term).
    assert g8p.graded > g13p.graded
