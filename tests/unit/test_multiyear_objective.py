"""② 다년 학습 — 다년 안정성 winner 점수(winner_objective='multiyear') 단위 테스트.

목표: 게이트통과 세대의 graded를 composite(Calmar×R²)에 결과 CSV를 연도별로 쪼개
산출한 cross-year stability_term을 곱한 composite×stability로 매겨, 단일년 과적합이
아니라 여러 해에 걸쳐 안정적으로 우상향하는(레짐-강건) 전략을 winner/best로 우대한다
(§3.20 시드의 다년 우상향 형태).

검증:
  (a) compute_multiyear_stability:
      - 3년 모두 흑자 + 매끄러운 우상향 → 높은 stability_term.
      - 단일년 과적합(1년만 흑자/우상향, 나머지 평평/적자) → 낮은 stability_term.
      - 유효연도 < min_years → None.
      - min_trades_per_year 미만 연도는 드롭.
      - stability_term ∈ [0,1].
  (b) 불변식: multiyear gate-passed graded ≥ 1.0; multiyear_stability=None이면
      gate-passed graded == risk_adjusted graded(composite) byte-동일.
  (c) _gate_passed_term('multiyear',...) == composite×s, s=None이면 == composite.
  (d) loop._winner_compare_key/_winner_score_value가 'multiyear'에서 stability 기준 정렬.

OFF=기존동작 보존이 핵심 — 'multiyear'는 명시 설정 시에만 동작한다.
"""

import csv
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness import (
    MultiYearStability,
    compute_multiyear_stability,
)
from ai_strategy_loop.fitness.holdout import _PROFIT_COLUMN, _SELL_TIME_COLUMN
from ai_strategy_loop.fitness.score import (
    _clamp01,
    _gate_passed_term,
    compute_fitness,
    compute_graded_fitness,
)

# 우상향 직선(R²≈1) — 거의 완벽한 우상향 equity.
_STEADY = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]


def _write_csv(tmp_path, trades):
    """(day:int(YYYYMMDD), profit:float) 리스트를 결과 CSV로 쓴다(매도시간/수익금 컬럼).

    매도시간은 'YYYYMMDDHHMM' 형식이어야 하므로 day(8자리)에 '0930'(시각)을 붙인다.
    """
    path = os.path.join(str(tmp_path), "trades.csv")
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([_SELL_TIME_COLUMN, _PROFIT_COLUMN])
        for day, profit in trades:
            writer.writerow([f"{int(day):08d}0930", profit])
    return path


def _year_trades(year, n, per):
    """year의 n거래를 만든다. per는 거래당 손익(고정 또는 리스트)."""
    base = year * 10000 + 615  # YYYY0615 (6월 15일) — 연중 임의 거래일.
    if isinstance(per, (int, float)):
        return [(base, float(per)) for _ in range(n)]
    return [(base, float(p)) for p in per]


def _cfg(objective="risk_adjusted", **kw):
    """min_trades=30, mdd_cap=25, min_daily_trades=0.0(빈도 게이트 무력화) 기본 게이트."""
    return LoopConfig(
        min_trades=30, mdd_cap=25.0, min_daily_trades=0.0,
        winner_objective=objective, **kw
    )


def _metrics(cagr, mdd, profit, *, trades=50):
    return {
        "cagr": cagr,
        "mdd_pct": mdd,
        "trade_count": trades,
        "total_profit_krw": profit,
    }


# ============================================================
# (a) compute_multiyear_stability
# ============================================================

def test_three_good_years_high_stability(tmp_path):
    """3년 모두 흑자 + 매끄러운 우상향 → 높은 stability_term."""
    trades = []
    for yr in (2023, 2024, 2025):
        # 각 연도 25거래 모두 +1000(꾸준한 우상향, 흑자, 변동 없음).
        trades += _year_trades(yr, 25, 1000.0)
    csv_path = _write_csv(tmp_path, trades)

    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    assert res.total_year_count == 3
    assert res.positive_year_count == 3
    assert len(res.years) == 3
    # 각 연도 흑자 + r²≈1 (직선 우상향).
    for ym in res.years:
        assert ym.profit > 0.0
        assert ym.uptrend_r2 > 0.99
        assert ym.win_rate == 1.0
    # positive_frac=1, mean_r2≈1, consistency≈1, profit_even≈1 → stability_term 높음.
    assert res.stability_term > 0.95
    assert 0.0 <= res.stability_term <= 1.0


def test_single_year_overfit_low_stability(tmp_path):
    """단일년 과적합(1년만 강한 우상향 흑자, 나머지 적자) → 낮은 stability_term.

    positive_frac(1/3)과 수익 변동성(profit_even)이 끌어내린다.
    """
    trades = []
    # 2023: 강한 흑자 + 우상향.
    trades += _year_trades(2023, 25, 5000.0)
    # 2024: 적자(꾸준한 하락 — r² 높지만 profit<0).
    trades += _year_trades(2024, 25, -2000.0)
    # 2025: 적자.
    trades += _year_trades(2025, 25, -2000.0)
    csv_path = _write_csv(tmp_path, trades)

    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    assert res.total_year_count == 3
    assert res.positive_year_count == 1  # 2023만 흑자.
    # positive_frac=1/3가 stability를 강하게 끌어내린다.
    assert res.stability_term < 0.7
    assert 0.0 <= res.stability_term <= 1.0

    # 3년 모두 흑자인 케이스보다 확실히 낮아야 한다.
    good = []
    for yr in (2023, 2024, 2025):
        good += _year_trades(yr, 25, 1000.0)
    good_path = _write_csv(tmp_path, good)
    good_res = compute_multiyear_stability(good_path, _cfg("multiyear"))
    assert res.stability_term < good_res.stability_term


def test_fewer_than_min_years_returns_none(tmp_path):
    """유효연도 < min_years(기본 2) → None(중립)."""
    # 단일 연도만(2023) → 유효연도 1 < 2.
    trades = _year_trades(2023, 25, 1000.0)
    csv_path = _write_csv(tmp_path, trades)
    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is None


def test_sparse_year_dropped_by_min_trades_per_year(tmp_path):
    """min_trades_per_year(기본 20) 미만 거래 연도는 드롭된다."""
    trades = []
    trades += _year_trades(2023, 25, 1000.0)  # 충분.
    trades += _year_trades(2024, 25, 1000.0)  # 충분.
    trades += _year_trades(2025, 5, 1000.0)   # 5 < 20 → 드롭.
    csv_path = _write_csv(tmp_path, trades)

    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    # 2025는 드롭 → 유효연도 2개.
    assert res.total_year_count == 2
    assert {ym.year for ym in res.years} == {2023, 2024}


def test_all_sparse_years_returns_none(tmp_path):
    """모든 연도가 min_trades_per_year 미만이면 유효연도 0 < min_years → None."""
    trades = []
    trades += _year_trades(2023, 5, 1000.0)
    trades += _year_trades(2024, 5, 1000.0)
    csv_path = _write_csv(tmp_path, trades)
    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is None


def test_missing_csv_returns_none(tmp_path):
    """존재하지 않는 CSV → None(중립, 예외 흡수)."""
    res = compute_multiyear_stability(
        os.path.join(str(tmp_path), "nope.csv"), _cfg("multiyear")
    )
    assert res is None


def test_stability_term_in_unit_range(tmp_path):
    """stability_term은 항상 [0,1]."""
    trades = []
    # 변동 큰 손익(우상향 깨짐) 섞어도 clamp.
    for yr in (2023, 2024, 2025):
        per = [3000.0, -2500.0, 4000.0, -3500.0, 2000.0] * 5  # 25거래, 들쭉날쭉.
        trades += _year_trades(yr, 25, per)
    csv_path = _write_csv(tmp_path, trades)
    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    assert 0.0 <= res.stability_term <= 1.0


# ============================================================
# (b) 불변식 — graded≥1.0 + None→risk_adjusted byte-동일
# ============================================================

def test_multiyear_passing_ge_one():
    """multiyear 모드에서도 통과 전략은 graded≥1.0 (통과>실패 불변)."""
    cfg = _cfg("multiyear")
    res = compute_graded_fitness(
        _metrics(300.0, 10.0, 1_000_000), _STEADY, cfg,
        multiyear_stability=0.8,
    )
    assert res.gate_passed
    assert res.objective == "multiyear"
    assert res.graded >= 1.0
    # graded-1.0 == composite × stability.
    assert abs((res.graded - 1.0) - res.composite * 0.8) < 1e-9
    assert res.multiyear_stability_term == 0.8


def test_multiyear_none_equals_risk_adjusted_byte_identical():
    """multiyear_stability=None이면 gate-passed graded == risk_adjusted graded(composite) byte-동일."""
    m = _metrics(300.0, 10.0, 1_000_000)
    g_ra = compute_graded_fitness(m, _STEADY, _cfg("risk_adjusted"))
    g_my = compute_graded_fitness(m, _STEADY, _cfg("multiyear"), multiyear_stability=None)
    assert g_ra.gate_passed and g_my.gate_passed
    # None → 1.0 중립 → composite 그대로 == risk_adjusted.
    assert g_my.graded == g_ra.graded
    assert g_my.multiyear_stability_term == 1.0


def test_multiyear_default_field_backward_compatible():
    """다른 objective에서는 multiyear_stability_term 기본 1.0(맨 끝 필드, 하위호환)."""
    g = compute_graded_fitness(_metrics(300.0, 10.0, 1_000_000), _STEADY, _cfg("risk_adjusted"))
    assert g.multiyear_stability_term == 1.0


# ============================================================
# (c) _gate_passed_term('multiyear', ...)
# ============================================================

def test_gate_passed_term_multiyear():
    """_gate_passed_term('multiyear',...) == composite × s; s=None이면 == composite."""
    cfg = _cfg("multiyear")
    # composite=5.0, stability=0.6 → 3.0. calmar/r²/daily/payoff는 무시돼야 한다.
    term = _gate_passed_term(
        "multiyear", 5.0, 0.7, cfg,
        calmar=100.0, uptrend_r2=0.81, daily_avg_trades=20.0, payoff_ratio=2.0,
        multiyear_stability=0.6,
    )
    assert abs(term - (5.0 * 0.6)) < 1e-12
    # None → 1.0 중립 → composite 그대로.
    term_none = _gate_passed_term("multiyear", 5.0, 0.7, cfg, multiyear_stability=None)
    assert abs(term_none - 5.0) < 1e-12
    # s>1(부동소수 오차 가정)은 clamp01로 1.0 → composite 그대로.
    term_clamp = _gate_passed_term("multiyear", 5.0, 0.7, cfg, multiyear_stability=1.5)
    assert abs(term_clamp - 5.0) < 1e-12


def test_existing_objectives_unchanged_with_multiyear_present():
    """risk_adjusted/profit/balanced graded는 'multiyear' 추가 후에도 byte-동일(회귀)."""
    m = _metrics(300.0, 10.0, 500_000)
    # risk_adjusted: graded-1.0 == composite.
    cfg_ra = _cfg("risk_adjusted")
    hard = compute_fitness(m, _STEADY, cfg_ra)
    g_ra = compute_graded_fitness(m, _STEADY, cfg_ra)
    assert abs((g_ra.graded - 1.0) - hard.score) < 1e-12
    # profit: graded-1.0 == profit_term.
    cfg_pr = _cfg("profit")
    g_pr = compute_graded_fitness(m, _STEADY, cfg_pr)
    assert abs((g_pr.graded - 1.0) - g_pr.profit_term) < 1e-12


# ============================================================
# (d) winner 비교/점수 — loop 미러
# ============================================================

class _FakeFit:
    """_winner_*용 최소 fit 더블(uptrend_r2/score만 본다)."""

    def __init__(self, score):
        self.score = float(score)
        self.uptrend_r2 = 0.0


class _FakeGraded:
    """_winner_*용 최소 graded 더블(multiyear_stability_term 보유)."""

    def __init__(self, multiyear_stability_term=0.0, total_profit=0.0, mdd=0.0,
                 profit_term=0.0):
        self.multiyear_stability_term = float(multiyear_stability_term)
        self.total_profit = float(total_profit)
        self.mdd = float(mdd)
        self.profit_term = float(profit_term)


def test_loop_winner_score_and_key_multiyear():
    """loop._winner_score_value/_winner_compare_key가 'multiyear'에서 stability 기준 정렬."""
    from ai_strategy_loop.controller.loop import (
        _winner_compare_key,
        _winner_score_value,
    )

    cfg = _cfg("multiyear")
    hi = _FakeFit(score=10.0)
    g_hi = _FakeGraded(multiyear_stability_term=0.9)
    lo = _FakeFit(score=99.0)  # score 더 높지만 stability는 낮다.
    g_lo = _FakeGraded(multiyear_stability_term=0.4)

    # 점수 스칼라 = multiyear_stability_term.
    assert _winner_score_value(hi, g_hi, cfg) == 0.9
    assert _winner_score_value(lo, g_lo, cfg) == 0.4
    # 비교 키 = (stability, score). stability 1차 → hi > lo (score가 거꾸로여도).
    assert _winner_compare_key(hi, g_hi, cfg) > _winner_compare_key(lo, g_lo, cfg)
    # 동률 stability면 composite(score)로 가른다.
    a_g = _FakeGraded(multiyear_stability_term=0.8)
    a = _FakeFit(score=5.0)
    b = _FakeFit(score=3.0)
    assert _winner_compare_key(a, a_g, cfg) > _winner_compare_key(b, a_g, cfg)


def test_loop_winner_key_default_unchanged_with_multiyear():
    """risk_adjusted(기본)에서는 비교 키가 (score,) 그대로 — multiyear 추가가 무영향."""
    from ai_strategy_loop.controller.loop import _winner_compare_key

    cfg = _cfg("risk_adjusted")
    fit = _FakeFit(score=7.0)
    g = _FakeGraded(multiyear_stability_term=0.95)
    assert _winner_compare_key(fit, g, cfg) == (7.0,)


# ============================================================
# (e) 하드게이트 불변
# ============================================================

def test_hard_gate_unchanged_by_multiyear():
    """compute_fitness(하드게이트)는 winner_objective='multiyear'와 전혀 무관하다."""
    m = _metrics(300.0, 10.0, 1_000_000)
    fit_my = compute_fitness(m, _STEADY, _cfg("multiyear"))
    fit_ra = compute_fitness(m, _STEADY, _cfg("risk_adjusted"))
    assert fit_my.gate_passed is True
    assert fit_my.score == fit_ra.score  # 하드게이트는 objective를 보지 않는다.


def test_gate_failed_branch_invariant_including_multiyear():
    """게이트 실패 graded는 objective와 무관하게 동일(multiyear 포함)."""
    # 수익+거래충분이지만 MDD 60 > cap 25 → 게이트 실패.
    m = _metrics(30.0, 60.0, 1_000_000)
    ra = compute_graded_fitness(m, _STEADY, _cfg("risk_adjusted"))
    my = compute_graded_fitness(m, _STEADY, _cfg("multiyear"), multiyear_stability=0.9)
    assert not (ra.gate_passed or my.gate_passed)
    assert abs(ra.graded - my.graded) < 1e-12  # multiyear도 실패 분기는 불변.
    assert my.graded < 1.0
