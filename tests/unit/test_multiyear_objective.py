"""② 다년 학습 — 다년 전구간 우상향 winner 점수(winner_objective='multiyear') 단위 테스트.

목표: 게이트통과 세대의 graded를 composite(Calmar×R²)에 **전구간 단일 누적곡선의
우상향 R²**(stability_term)를 곱한 composite×stability로 매겨, 단일년 과적합이 아니라
여러 해에 걸쳐 누적곡선이 장기 우상향하는 전략을 winner/best로 우대한다(§3.20·§3.21).

평가기준 정정(사용자): 합격선은 "매 연도 흑자/일정 기울기/연도 균등성"이 **아니라**
"등락·기울기 변동이 있어도 다년 전구간 누적이 장기 우상향"이다. 따라서 stability_term은
연도별 균등성(positive_frac/consistency/profit_even)을 **제거**하고 전구간 R² 하나만 쓴다.
다년 참여 게이트(유효연도>=min_years)만 균등성 요구 없이 유지한다.

검증:
  (a) compute_multiyear_stability:
      - 매끄러운 다년 우상향 → stability_term ≈ 전구간 R²(높음).
      - 단일년(유효연도<min_years) → None(중립).
      - **down-year 허용(핵심)**: 전구간이 강하게 우상향하면 중간 하락/평평 연도가
        있어도 stability_term은 높다(균등성으로 깎이지 않음). 구 동작과 대비.
      - min_trades_per_year 미만 연도는 참여 게이트에서 드롭.
      - stability_term ∈ [0,1].
  (b) 불변식: multiyear gate-passed graded ≥ 1.0; multiyear_stability=None이면
      gate-passed graded == risk_adjusted graded(composite) byte-동일.
  (c) _gate_passed_term('multiyear',...) == composite×s, s=None이면 == composite.
  (d) **winner-strength(gen4 버그 회귀가드)**: '강하지만 덜 균등'(seed-like, graded↑)이
      '약하지만 균등'(gen4-like, graded↓)을 winner로 이긴다 — _winner_compare_key/
      _winner_score_value('multiyear')가 graded 기준 정렬.

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

def _full_curve_r2(trades):
    """trades 리스트(거래순서)의 전구간 누적손익 곡선 우상향 R²(기대값 계산용)."""
    from ai_strategy_loop.fitness.score import compute_uptrend_r2  # noqa: PLC0415

    equity = []
    running = 0.0
    for _day, profit in trades:
        running += float(profit)
        equity.append(running)
    return compute_uptrend_r2(equity)


def test_smooth_multiyear_uptrend_high_stability(tmp_path):
    """매끄러운 다년 우상향 → stability_term ≈ 전구간 R²(높음)."""
    trades = []
    for yr in (2023, 2024, 2025):
        # 각 연도 25거래 모두 +1000(꾸준한 우상향).
        trades += _year_trades(yr, 25, 1000.0)
    csv_path = _write_csv(tmp_path, trades)

    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    assert res.total_year_count == 3
    assert len(res.years) == 3
    # stability_term은 전구간 단일 누적곡선의 우상향 R²와 동일하다(연도별 분할 아님).
    expected = _full_curve_r2(trades)
    assert abs(res.stability_term - res.full_period_uptrend_r2) < 1e-12
    assert abs(res.stability_term - expected) < 1e-9
    # 일정 기울기 직선이라 R²≈1.
    assert res.stability_term > 0.99
    assert 0.0 <= res.stability_term <= 1.0


def test_down_year_tolerated_when_full_period_trends_up(tmp_path):
    """down-year 허용(사용자 핵심 요구): 전구간이 강하게 우상향하면 중간 하락 연도가
    있어도 stability_term은 높다 — 균등성/매년흑자로 깎이지 않는다.

    구 동작(positive_frac·profit_even)이라면 1년 적자가 stability를 강하게 끌어내렸겠지만,
    새 정의는 전구간 누적곡선 R²만 보므로 전체 추세가 우상향이면 페널티가 없다.
    """
    trades = []
    # 2023: 강한 상승(+2000 ×25).
    trades += _year_trades(2023, 25, 2000.0)
    # 2024: 완만한 하락 연도(-300 ×25) — 누적곡선이 잠시 꺾이지만 전체 우상향 유지.
    trades += _year_trades(2024, 25, -300.0)
    # 2025: 다시 강한 상승(+2000 ×25) → 전구간 누적은 우상향.
    trades += _year_trades(2025, 25, 2000.0)
    csv_path = _write_csv(tmp_path, trades)

    res = compute_multiyear_stability(csv_path, _cfg("multiyear"))
    assert res is not None
    assert res.total_year_count == 3
    # 2024는 적자라 진단상 positive_year_count는 2지만 — term에는 영향이 없어야 한다.
    assert res.positive_year_count == 2
    # 전구간 누적이 우상향이므로 stability_term은 여전히 높다(균등성 페널티 없음).
    #   stability_term == 전구간 R². 중간 하락 연도로 R²가 1에서 약간만 내려갈 뿐,
    #   균등성 항으로 *추가* 페널티를 받지 않는다(이게 핵심).
    expected = _full_curve_r2(trades)
    assert abs(res.stability_term - expected) < 1e-9
    assert res.stability_term > 0.80, (
        "전구간 우상향인데 down-year로 stability가 과하게 깎였다 — 균등성 페널티가 남아있다"
    )

    # 핵심 대비(구 동작 vs 새 동작): 구 평균식
    #   mean(positive_frac=2/3, mean_r2≈1, consistency, profit_even)은 적자/변동성으로
    #   stability를 크게 끌어내렸다. 새 정의(전구간 R²)는 그보다 명확히 높아야 한다.
    old_style_positive_frac = res.positive_year_count / res.total_year_count  # 2/3≈0.667
    assert res.stability_term > old_style_positive_frac, (
        "새 전구간-R² 항이 구 positive_frac(균등성) 항보다 낮다 — 정정 실패"
    )

    # 대비: 매년 균등 흑자 케이스도 전구간 우상향이라 둘 다 높은 stability.
    #   균등성으로 가르지 않는다(둘 다 0.80 이상).
    good = []
    for yr in (2023, 2024, 2025):
        good += _year_trades(yr, 25, 1000.0)
    good_path = _write_csv(tmp_path, good)
    good_res = compute_multiyear_stability(good_path, _cfg("multiyear"))
    assert good_res.stability_term > 0.99
    assert res.stability_term > 0.80


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
    """_winner_*용 최소 graded 더블. 'multiyear'는 이제 graded(전체 점수)로 정렬한다."""

    def __init__(self, graded=0.0, multiyear_stability_term=0.0, total_profit=0.0,
                 mdd=0.0, profit_term=0.0):
        self.graded = float(graded)
        self.multiyear_stability_term = float(multiyear_stability_term)
        self.total_profit = float(total_profit)
        self.mdd = float(mdd)
        self.profit_term = float(profit_term)


def test_loop_winner_strength_beats_evenness_multiyear():
    """winner-strength 회귀가드(gen4 버그): '강하지만 덜 균등'(seed-like, graded↑)이
    '약하지만 균등'(gen4-like, graded↓)을 이긴다 — 'multiyear'는 graded 기준 정렬.

    실 데이터(myr4): seed graded ≈ 1 + 2.87×0.90 = 3.58 vs gen4 ≈ 1 + 1.32×0.725 = 1.96.
    구 동작(stability_term 정렬)은 stability만 보고 더 약한 gen4의 stability가 높으면
    그쪽을 winner로 골랐다. 새 동작은 graded(=composite×R²+1)를 봐서 강한 seed를 고른다.
    """
    from ai_strategy_loop.controller.loop import (
        _winner_compare_key,
        _winner_score_value,
    )

    cfg = _cfg("multiyear")
    # seed-like: 강하지만(=graded 높음) stability_term 자체는 더 낮을 수도 있다.
    seed_fit = _FakeFit(score=2.87)
    seed_g = _FakeGraded(graded=3.58, multiyear_stability_term=0.90)
    # gen4-like: 약하지만(=graded 낮음) — 구 동작이라면 stability로 이겼을 수 있다.
    gen4_fit = _FakeFit(score=1.32)
    gen4_g = _FakeGraded(graded=1.96, multiyear_stability_term=0.725)

    # 점수 스칼라 = graded(전체 점수). seed가 더 강하다.
    assert _winner_score_value(seed_fit, seed_g, cfg) == 3.58
    assert _winner_score_value(gen4_fit, gen4_g, cfg) == 1.96
    # 비교 키 = (graded,). seed(강함) > gen4(약함) → seed가 winner.
    assert _winner_compare_key(seed_fit, seed_g, cfg) > _winner_compare_key(gen4_fit, gen4_g, cfg)

    # 회귀가드의 핵심: gen4의 stability_term이 seed보다 (가정상) 높아도 graded로 골라야 한다.
    even_but_weak = _FakeGraded(graded=1.96, multiyear_stability_term=0.99)
    assert _winner_compare_key(seed_fit, seed_g, cfg) > _winner_compare_key(gen4_fit, even_but_weak, cfg)


def test_loop_winner_key_default_unchanged_with_multiyear():
    """risk_adjusted(기본)에서는 비교 키가 (score,) 그대로 — multiyear 추가가 무영향."""
    from ai_strategy_loop.controller.loop import _winner_compare_key

    cfg = _cfg("risk_adjusted")
    fit = _FakeFit(score=7.0)
    g = _FakeGraded(graded=8.0, multiyear_stability_term=0.95)
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
