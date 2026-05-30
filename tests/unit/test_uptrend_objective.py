"""레버 — 우상향 winner 점수(winner_objective='uptrend') 단위 테스트.

목표: 게이트통과 세대의 graded를 composite(Calmar×R²)에 R²를 한 번 더 곱한
composite×R²로 매겨, 누적수익 곡선이 장기 우상향(uptrend_r2 높음)에 가까운 전략을
winner/best로 우대한다(보고서 우수전략의 정의적 특성).

검증:
  (a) winner_objective 미설정/risk_adjusted/profit/balanced/multi면 'uptrend' 추가
      전과 graded byte-동일(회귀 — 동일 입력에서 기존 공식 그대로).
  (b) 'uptrend': graded≥1.0(통과>실패 불변)이고, 같은 calmar에서 R² 높은 곡선이
      낮은 곡선보다 graded↑ (composite×R²의 단조성 — R²가 두 번 곱해진다).
  (c) loop._winner_compare_key / _winner_score_value가 'uptrend'에서 R² 기준으로
      정렬되고(동률 시 composite), GA 미러(_ga_winner_*)도 동일하게 동작한다.
  (d) 하드게이트(compute_fitness)·게이트실패 분기는 objective='uptrend'와 무관하게 불변.

OFF=기존동작 보존이 핵심 — 'uptrend'는 명시 설정 시에만 동작한다.
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
    compute_uptrend_r2,
    _gate_passed_term,
    _clamp01,
)

# 우상향 직선(R²≈1) — 거의 완벽한 우상향 equity.
_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
# 같은 시작/끝(총수익 동일)이지만 들쭉날쭉(spiky)해 R²가 낮은 곡선.
#   끝점은 _STEADY와 같은 900이라 total_profit 게이트는 동일하게 통과한다.
_SPIKY = [0, 800, 100, 850, 150, 880, 200, 890, 300, 900]


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
    """min_trades=30, mdd_cap=25, min_daily_trades=0.0(빈도 게이트 무력화) 기본 게이트."""
    return LoopConfig(
        min_trades=30, mdd_cap=25.0, min_daily_trades=0.0,
        winner_objective=objective, **kw
    )


# ============================================================
# (a) 회귀 — 미설정/기존 objective는 byte-동일
# ============================================================

def test_default_risk_adjusted_unchanged_by_uptrend_addition():
    """미설정(기본 risk_adjusted)이면 graded == 1.0 + 하드 composite (기존 동작 byte-동일)."""
    cfg = LoopConfig(min_trades=30, mdd_cap=25.0)  # winner_objective 미설정.
    assert cfg.winner_objective == "risk_adjusted"
    m = _metrics(30.0, 10.0, 1_000_000)
    hard = compute_fitness(m, _STEADY, cfg)
    graded = compute_graded_fitness(m, _STEADY, cfg)
    assert hard.gate_passed
    assert abs(graded.graded - (1.0 + hard.score)) < 1e-12


def test_existing_objectives_unchanged_with_uptrend_present():
    """profit/balanced/multi graded는 'uptrend' 추가 후에도 기존 공식과 byte-동일(회귀)."""
    m = _metrics(300.0, 10.0, 500_000, daily=5.0, payoff=1.25)

    # profit: graded-1.0 == profit_term.
    cfg_pr = _cfg("profit")
    g_pr = compute_graded_fitness(m, _STEADY, cfg_pr)
    assert g_pr.gate_passed
    assert abs((g_pr.graded - 1.0) - g_pr.profit_term) < 1e-12

    # balanced: graded-1.0 == composite·(1-w)+profit_term·w.
    cfg_ba = _cfg("balanced", profit_weight=0.5)
    hard = compute_fitness(m, _STEADY, cfg_ba)
    g_ba = compute_graded_fitness(m, _STEADY, cfg_ba)
    expected = hard.score * 0.5 + g_ba.profit_term * 0.5
    assert abs((g_ba.graded - 1.0) - expected) < 1e-12

    # multi: 통과항은 4항 평균(uptrend 추가가 multi 분기를 바꾸지 않음).
    cfg_mu = _cfg("multi")
    g_mu = compute_graded_fitness(m, _STEADY, cfg_mu)
    calmar = 300.0 / 10.0  # 30
    expected_mu = (
        _clamp01(calmar / 30.0)
        + _clamp01(g_mu.uptrend_r2)
        + _clamp01(5.0 / 10.0)
        + _clamp01((1.25 - 1.0) / (1.3 - 1.0))
    ) / 4.0
    assert abs((g_mu.graded - 1.0) - expected_mu) < 1e-9


def test_gate_passed_term_uptrend_only_uses_r2():
    """_gate_passed_term('uptrend',...)는 composite×R²만 쓴다(calmar/daily/payoff 무시)."""
    cfg = _cfg("uptrend")
    # composite=5.0, r²=0.81 → 5.0*0.81 = 4.05. 나머지 키워드는 무시돼야 한다.
    term = _gate_passed_term(
        "uptrend", 5.0, 0.7, cfg,
        calmar=100.0, uptrend_r2=0.81, daily_avg_trades=20.0, payoff_ratio=2.0,
    )
    assert abs(term - (5.0 * 0.81)) < 1e-12
    # uptrend_r2=None이면 0.0으로 폴백 → composite×0 = 0.
    term_none = _gate_passed_term("uptrend", 5.0, 0.7, cfg, uptrend_r2=None)
    assert term_none == 0.0
    # r²>1(부동소수 오차 가정)은 clamp01로 1.0 → composite 그대로.
    term_clamp = _gate_passed_term("uptrend", 5.0, 0.7, cfg, uptrend_r2=1.5)
    assert abs(term_clamp - 5.0) < 1e-12


# ============================================================
# (b) uptrend — 높은 R²가 graded를 끌어올린다 + graded≥1.0
# ============================================================

def test_uptrend_passing_still_ge_one():
    """uptrend 모드에서도 통과 전략은 graded≥1.0 (통과>실패 불변)."""
    cfg = _cfg("uptrend")
    res = compute_graded_fitness(_metrics(300.0, 10.0, 1_000_000), _STEADY, cfg)
    assert res.gate_passed
    assert res.objective == "uptrend"
    assert res.graded >= 1.0


def test_uptrend_high_r2_outranks_low_r2_same_calmar():
    """'uptrend': 같은 calmar에서 우상향 R²가 높은 곡선이 낮은 곡선보다 graded↑.

    cagr/mdd/profit 동일(=calmar·composite 분모 동일)이고 equity 모양만 다르다.
    _STEADY(R²≈1)가 _SPIKY(R² 낮음)보다 graded가 높아야 한다(composite×R²의 단조성).
    """
    cfg = _cfg("uptrend")
    m = _metrics(300.0, 10.0, 1_000_000)  # calmar=30, total_profit 동일.
    g_steady = compute_graded_fitness(m, _STEADY, cfg)
    g_spiky = compute_graded_fitness(m, _SPIKY, cfg)
    assert g_steady.gate_passed and g_spiky.gate_passed
    # R² 자체가 _STEADY가 더 높음을 확인(전제).
    assert g_steady.uptrend_r2 > g_spiky.uptrend_r2
    # composite×R² → R²가 두 번 곱해져 우상향이 더 강하게 보상된다.
    assert g_steady.graded > g_spiky.graded
    # 정확값: graded-1.0 == composite × r².  composite = calmar × r².
    for g in (g_steady, g_spiky):
        composite = g.composite  # = calmar × r² (게이트 통과 시 hard.score)
        assert abs((g.graded - 1.0) - composite * g.uptrend_r2) < 1e-9


# ============================================================
# (c) winner 비교/점수 — loop + GA 미러
# ============================================================

class _FakeFit:
    """_winner_*용 최소 fit 더블(uptrend_r2/score만 본다)."""

    def __init__(self, uptrend_r2, score):
        self.uptrend_r2 = float(uptrend_r2)
        self.score = float(score)


class _FakeGraded:
    """_winner_*용 최소 graded 더블."""

    def __init__(self, total_profit=0.0, mdd=0.0, profit_term=0.0):
        self.total_profit = float(total_profit)
        self.mdd = float(mdd)
        self.profit_term = float(profit_term)


def test_loop_winner_score_and_key_uptrend():
    """loop._winner_score_value/_winner_compare_key가 'uptrend'에서 R² 기준 정렬."""
    from ai_strategy_loop.controller.loop import (
        _winner_score_value,
        _winner_compare_key,
    )

    cfg = _cfg("uptrend")
    hi = _FakeFit(uptrend_r2=0.95, score=10.0)
    lo = _FakeFit(uptrend_r2=0.40, score=99.0)  # score 더 높지만 R²는 낮다.
    g = _FakeGraded()

    # 점수 스칼라 = uptrend_r2.
    assert _winner_score_value(hi, g, cfg) == 0.95
    assert _winner_score_value(lo, g, cfg) == 0.40
    # 비교 키 = (uptrend_r2, score). R² 1차 → hi > lo (score가 거꾸로여도).
    assert _winner_compare_key(hi, g, cfg) > _winner_compare_key(lo, g, cfg)
    # 동률 R²면 composite(score)로 가른다.
    a = _FakeFit(uptrend_r2=0.80, score=5.0)
    b = _FakeFit(uptrend_r2=0.80, score=3.0)
    assert _winner_compare_key(a, g, cfg) > _winner_compare_key(b, g, cfg)


def test_loop_winner_key_default_unchanged():
    """risk_adjusted(기본)에서는 비교 키가 (score,) 그대로 — uptrend 추가가 무영향."""
    from ai_strategy_loop.controller.loop import _winner_compare_key

    cfg = _cfg("risk_adjusted")
    fit = _FakeFit(uptrend_r2=0.95, score=7.0)
    g = _FakeGraded()
    assert _winner_compare_key(fit, g, cfg) == (7.0,)


class _FakeInd:
    """_ga_winner_*용 최소 Individual 더블."""

    def __init__(self, uptrend_r2=0.0, hard_score=0.0, profit=0.0, mdd=0.0,
                 profit_term=0.0):
        self.uptrend_r2 = float(uptrend_r2)
        self.hard_score = float(hard_score)
        self.profit = float(profit)
        self.mdd = float(mdd)
        self.profit_term = float(profit_term)


def test_ga_winner_score_and_key_uptrend():
    """ga._ga_winner_score/_ga_winner_key가 'uptrend'에서 R² 기준 정렬(loop 미러)."""
    from ai_strategy_loop.controller.ga import _ga_winner_score, _ga_winner_key

    cfg = _cfg("uptrend")
    hi = _FakeInd(uptrend_r2=0.95, hard_score=10.0)
    lo = _FakeInd(uptrend_r2=0.40, hard_score=99.0)
    assert _ga_winner_score(hi, cfg) == 0.95
    assert _ga_winner_score(lo, cfg) == 0.40
    assert _ga_winner_key(hi, cfg) > _ga_winner_key(lo, cfg)
    # 동률 R² → hard_score(composite)로 가른다.
    a = _FakeInd(uptrend_r2=0.80, hard_score=5.0)
    b = _FakeInd(uptrend_r2=0.80, hard_score=3.0)
    assert _ga_winner_key(a, cfg) > _ga_winner_key(b, cfg)


def test_ga_winner_uptrend_getattr_fallback():
    """Individual에 uptrend_r2가 없어도 getattr 폴백으로 0.0 — 크래시 없이 동작."""
    from ai_strategy_loop.controller.ga import _ga_winner_score, _ga_winner_key

    cfg = _cfg("uptrend")

    class _NoR2:
        hard_score = 4.0
        profit = 0.0
        mdd = 0.0
        profit_term = 0.0
        # uptrend_r2 속성 없음.

    ind = _NoR2()
    assert _ga_winner_score(ind, cfg) == 0.0
    assert _ga_winner_key(ind, cfg) == (0.0, 4.0)


# ============================================================
# (d) 하드게이트·게이트실패 분기 불변
# ============================================================

def test_hard_gate_unchanged_by_uptrend():
    """compute_fitness(하드게이트)는 winner_objective='uptrend'와 전혀 무관하다."""
    cfg = _cfg("uptrend")
    m = _metrics(300.0, 10.0, 1_000_000)
    fit_up = compute_fitness(m, _STEADY, cfg)
    fit_ra = compute_fitness(m, _STEADY, _cfg("risk_adjusted"))
    assert fit_up.gate_passed is True
    assert fit_up.score == fit_ra.score  # 하드게이트는 objective를 보지 않는다.


def test_gate_failed_branch_invariant_including_uptrend():
    """게이트 실패 graded는 objective와 무관하게 동일(uptrend 포함, profit_term×mean 그대로)."""
    # 수익+거래충분이지만 MDD 60 > cap 25 → 게이트 실패.
    m = _metrics(30.0, 60.0, 1_000_000)
    ra = compute_graded_fitness(m, _STEADY, _cfg("risk_adjusted"))
    up = compute_graded_fitness(m, _STEADY, _cfg("uptrend"))
    assert not (ra.gate_passed or up.gate_passed)
    assert abs(ra.graded - up.graded) < 1e-12  # uptrend도 실패 분기는 불변.
    assert up.graded < 1.0
