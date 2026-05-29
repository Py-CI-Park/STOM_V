"""4레버 ① — 다목적 winner 점수(winner_objective='multi') 단위 테스트.

목표: 게이트통과 세대의 graded를 calmar·R²·일평균빈도·payoff를 [0,1]로 정규화해
동일가중 결합한 다목적 점수로 매겨, '고빈도이면서 위험조정 좋은' 세대를 우대한다.
현 profit obj는 시드만 뽑아 다양성이 죽으므로, multi가 freq 항으로 고빈도를 끌어올린다.

검증:
  (a) winner_objective 미설정/risk_adjusted/profit/balanced면 기존 graded와 byte-동일(회귀).
  (b) 'multi': 고빈도+고calmar 세대(daily10)가 저빈도 세대(daily0.4)보다 graded↑
      (freq 항이 차이를 만든다 — 다른 항은 동일).
  (c) payoff/calmar None 항 제외 평균 동작.
  (d) 하드게이트(compute_fitness)·게이트실패 분기는 objective와 무관하게 불변.

OFF=기존동작 보존이 핵심 — 'multi'는 명시 설정 시에만 동작한다.
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
    _gate_passed_term,
    _multi_objective_term,
    _clamp01,
)

# 우상향 직선(R²≈1) — 게이트 통과 전략의 equity로 쓴다.
_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _metrics(cagr, mdd, profit, *, daily=None, trades=50, payoff=None):
    """게이트 통과를 위한 metrics. daily가 주어지면 daily_avg_trades 게이트 경로를 탄다."""
    m = {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }
    if daily is not None:
        m["daily_avg_trades"] = daily
    if payoff is not None:
        m["payoff_ratio"] = payoff
    return m


def _cfg(objective="risk_adjusted", **kw):
    """min_trades=30, mdd_cap=25, min_daily_trades=0.0(빈도 게이트 무력화) 기본 게이트.

    min_daily_trades=0.0이면 daily_avg_trades가 metrics에 있어도 빈도 하드게이트는
    항상 통과한다 — 저빈도(daily0.4) 세대도 게이트통과 분기를 타게 해 graded를 비교한다.
    """
    return LoopConfig(
        min_trades=30, mdd_cap=25.0, min_daily_trades=0.0,
        winner_objective=objective, **kw
    )


# ============================================================
# (a) 회귀 — 미설정/기존 objective는 byte-동일
# ============================================================

def test_default_risk_adjusted_unchanged_by_multi_addition():
    """미설정(기본 risk_adjusted)이면 graded == 1.0 + 하드 composite (기존 동작 byte-동일)."""
    cfg = LoopConfig(min_trades=30, mdd_cap=25.0)  # winner_objective 미설정.
    assert cfg.winner_objective == "risk_adjusted"
    m = _metrics(30.0, 10.0, 1_000_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert hard.gate_passed
    assert abs(graded.graded - (1.0 + hard.score)) < 1e-12


def test_profit_balanced_unchanged_when_multi_constants_present():
    """profit/balanced graded는 multi 상수가 있어도 기존 공식과 byte-동일하다(회귀)."""
    m = _metrics(30.0, 10.0, 500_000, daily=5.0, payoff=1.25)

    # profit: graded-1.0 == profit_term (multi 항 미개입).
    cfg_pr = _cfg("profit")
    g_pr = compute_graded_fitness(m, _STEADY, cfg_pr)
    assert g_pr.gate_passed
    assert abs((g_pr.graded - 1.0) - g_pr.profit_term) < 1e-12

    # balanced: graded-1.0 == composite·(1-w)+profit_term·w (multi 항 미개입).
    cfg_ba = _cfg("balanced", profit_weight=0.5)
    hard = compute_fitness(m, _STEADY, cfg_ba)
    g_ba = compute_graded_fitness(m, _STEADY, cfg_ba)
    expected = hard.score * 0.5 + g_ba.profit_term * 0.5
    assert abs((g_ba.graded - 1.0) - expected) < 1e-12


def test_gate_passed_term_extra_kwargs_ignored_for_non_multi():
    """비-multi objective는 calmar/r²/daily/payoff 키워드를 무시한다(하위호환·byte-동일)."""
    cfg = _cfg("risk_adjusted")
    base = _gate_passed_term("risk_adjusted", 5.0, 0.7, cfg)
    with_kw = _gate_passed_term(
        "risk_adjusted", 5.0, 0.7, cfg,
        calmar=100.0, uptrend_r2=0.9, daily_avg_trades=20.0, payoff_ratio=2.0,
    )
    assert base == with_kw == 5.0  # composite 그대로.


# ============================================================
# (b) multi — 고빈도가 graded를 끌어올린다
# ============================================================

def test_multi_high_freq_outranks_low_freq():
    """'multi': 고빈도(daily10) 세대가 저빈도(daily0.4) 세대보다 graded↑.

    calmar30·r²≈1·payoff1.3 동일, daily만 10 vs 0.4 → freq 항이 차이를 만든다.
    """
    cfg = _cfg("multi")  # multi_calmar_norm=30, multi_daily_target=10, multi_payoff_norm=1.3.
    # calmar = cagr/mdd. cagr=300, mdd=10 → calmar=30(= norm, 항=1.0).
    hi = compute_graded_fitness(
        _metrics(300.0, 10.0, 1_000_000, daily=10.0, payoff=1.3), _STEADY, cfg
    )
    lo = compute_graded_fitness(
        _metrics(300.0, 10.0, 1_000_000, daily=0.4, payoff=1.3), _STEADY, cfg
    )
    assert hi.gate_passed and lo.gate_passed
    assert hi.objective == "multi" and lo.objective == "multi"
    # freq 항: hi=clamp01(10/10)=1.0, lo=clamp01(0.4/10)=0.04 → hi graded가 더 높다.
    assert hi.graded > lo.graded


def test_multi_passing_still_ge_one():
    """multi 모드에서도 통과 전략은 graded≥1.0 (통과>실패 불변)."""
    cfg = _cfg("multi")
    res = compute_graded_fitness(
        _metrics(300.0, 10.0, 1_000_000, daily=10.0, payoff=1.3), _STEADY, cfg
    )
    assert res.gate_passed
    assert res.graded >= 1.0


def test_multi_term_equal_weight_average_exact():
    """multi 통과항 == calmar·R²·빈도·payoff 4항 동일가중 평균(정확 값 검증)."""
    cfg = _cfg("multi")  # norm: calmar30, payoff1.3, daily10.
    # calmar=30 → 30/30=1.0; r²≈1.0; daily=5 → 5/10=0.5; payoff=1.15 → (1.15-1)/(1.3-1)=0.5.
    m = _metrics(300.0, 10.0, 1_000_000, daily=5.0, payoff=1.15)
    g = compute_graded_fitness(m, _STEADY, cfg)
    assert g.gate_passed
    calmar_comp = _clamp01(30.0 / 30.0)        # 1.0
    r2_comp = _clamp01(g.uptrend_r2)           # ≈1.0
    freq_comp = _clamp01(5.0 / 10.0)           # 0.5
    payoff_comp = _clamp01((1.15 - 1.0) / (1.3 - 1.0))  # 0.5
    expected = (calmar_comp + r2_comp + freq_comp + payoff_comp) / 4.0
    assert abs((g.graded - 1.0) - expected) < 1e-9


def test_multi_passing_outranks_failing():
    """multi 모드에서 통과(graded≥1.0)가 모든 실패(graded<1.0)보다 위."""
    cfg = _cfg("multi")
    passing = compute_graded_fitness(
        _metrics(300.0, 10.0, 100_000, daily=10.0, payoff=1.3), _STEADY, cfg
    )
    failing = compute_graded_fitness(
        _metrics(300.0, 60.0, 9_000_000, daily=10.0, payoff=1.3), _STEADY, cfg  # MDD 초과
    )
    assert passing.gate_passed and not failing.gate_passed
    assert passing.graded >= 1.0 > failing.graded


# ============================================================
# (c) None 항 제외 평균
# ============================================================

def test_multi_term_excludes_none_components():
    """payoff/calmar None 항은 평균에서 제외된다(_multi_objective_term 직접 검증)."""
    cfg = _cfg("multi")  # calmar30, payoff1.3, daily10.
    # 4항 모두: calmar30→1.0, r²1.0, daily5→0.5, payoff1.15→0.5 → 평균 0.75.
    full = _multi_objective_term(30.0, 1.0, 5.0, 1.15, cfg)
    assert abs(full - 0.75) < 1e-9
    # payoff None → 3항 평균(1.0,1.0,0.5)=0.8333.
    no_payoff = _multi_objective_term(30.0, 1.0, 5.0, None, cfg)
    assert abs(no_payoff - (1.0 + 1.0 + 0.5) / 3.0) < 1e-9
    # calmar None + payoff None → 2항 평균(1.0,0.5)=0.75.
    no_calmar_payoff = _multi_objective_term(None, 1.0, 5.0, None, cfg)
    assert abs(no_calmar_payoff - (1.0 + 0.5) / 2.0) < 1e-9
    # 전부 None → 0.0(graded=1.0, 통과>실패 불변 유지).
    assert _multi_objective_term(None, None, None, None, cfg) == 0.0


def test_multi_payoff_missing_in_metrics_excluded():
    """metrics에 payoff_ratio가 없으면 payoff 항이 제외되어도 multi graded는 정상 산출된다."""
    cfg = _cfg("multi")
    # payoff 키 없음 → calmar·r²·freq 3항 평균.
    m = _metrics(300.0, 10.0, 1_000_000, daily=5.0)  # payoff None
    g = compute_graded_fitness(m, _STEADY, cfg)
    assert g.gate_passed
    calmar_comp = _clamp01(30.0 / 30.0)
    r2_comp = _clamp01(g.uptrend_r2)
    freq_comp = _clamp01(5.0 / 10.0)
    expected = (calmar_comp + r2_comp + freq_comp) / 3.0
    assert abs((g.graded - 1.0) - expected) < 1e-9


# ============================================================
# (d) 하드게이트·게이트실패 분기 불변
# ============================================================

def test_hard_gate_unchanged_by_multi():
    """compute_fitness(하드게이트)는 winner_objective='multi'와 전혀 무관하다."""
    cfg = _cfg("multi")
    m = _metrics(300.0, 10.0, 1_000_000, daily=10.0, payoff=1.3)
    fit_multi = compute_fitness(m, _STEADY, cfg)
    fit_ra = compute_fitness(m, _STEADY, _cfg("risk_adjusted"))
    assert fit_multi.gate_passed is True
    assert fit_multi.score == fit_ra.score  # 하드게이트는 objective를 보지 않는다.


def test_gate_failed_branch_invariant_including_multi():
    """게이트 실패 graded는 objective와 무관하게 동일(multi 포함, profit_term×mean 그대로)."""
    # 수익+거래충분이지만 MDD 60 > cap 25 → 게이트 실패.
    m = _metrics(30.0, 60.0, 1_000_000, daily=10.0, payoff=1.3)
    ra = compute_graded_fitness(m, _STEADY, _cfg("risk_adjusted"))
    pr = compute_graded_fitness(m, _STEADY, _cfg("profit"))
    ba = compute_graded_fitness(m, _STEADY, _cfg("balanced"))
    mu = compute_graded_fitness(m, _STEADY, _cfg("multi"))
    assert not (ra.gate_passed or pr.gate_passed or ba.gate_passed or mu.gate_passed)
    assert abs(ra.graded - pr.graded) < 1e-12
    assert abs(ra.graded - ba.graded) < 1e-12
    assert abs(ra.graded - mu.graded) < 1e-12  # multi도 실패 분기는 불변.
    assert mu.graded < 1.0
