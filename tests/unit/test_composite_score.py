"""US-004 Phase 2a — 복합 적합도(composite fitness) 단위 테스트.

검증:
  (a) 동일 CAGR/MDD인데 꾸준히 우상향(높은 R²)인 곡선이 spiky(낮은 R²)보다 점수가 높다.
  (b) gate: trade_count < min_trades / mdd > mdd_cap / total_profit <= 0 -> composite 0.
  (c) 깨끗한 통과 케이스 -> composite > 0 이고 calmar x r2 x 1 수식과 일치.
  (d) MDD≈0이 크래시하지 않는다.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.score import (
    compute_calmar,
    compute_fitness,
    compute_uptrend_r2,
)


def _passing_config():
    """gate를 통과하기 쉬운 느슨한 config (min_trades 작게, mdd_cap 넉넉히)."""
    return LoopConfig(min_trades=3, mdd_cap=50.0)


# ============================================================
# (a) 우상향도(R²): 꾸준한 상승이 spiky보다 높은 점수
# ============================================================

def test_steady_uptrend_scores_higher_than_spiky_at_equal_cagr_mdd():
    """동일 metrics(같은 CAGR/MDD/거래수/총수익)에서 꾸준한 우상향 곡선이
    한 번에 튀는 곡선보다 복합 점수가 높아야 한다 (R² 차이가 점수를 가른다)."""
    config = _passing_config()
    metrics = {
        "cagr": 30.0,
        "mdd_pct": 10.0,
        "trade_count": 10,
        "total_profit_krw": 1000,
    }

    # 꾸준히 우상향: 거의 직선 -> R²≈1
    steady = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    # spiky: 대부분 평평하다가 마지막에 한 번에 점프 -> 직선 적합 나쁨 -> 낮은 R²
    spiky = [0, 0, 0, 0, 0, 0, 0, 0, 0, 900]

    res_steady = compute_fitness(metrics, steady, config)
    res_spiky = compute_fitness(metrics, spiky, config)

    assert res_steady.gate_passed is True
    assert res_spiky.gate_passed is True
    assert res_steady.uptrend_r2 > res_spiky.uptrend_r2
    assert res_steady.score > res_spiky.score


def test_uptrend_r2_perfect_line_is_one():
    """완벽한 직선 누적수익은 R²=1.0 (부동소수 허용오차 내)."""
    r2 = compute_uptrend_r2([0, 10, 20, 30, 40, 50])
    assert abs(r2 - 1.0) < 1e-9


def test_uptrend_r2_is_clamped_to_unit_interval():
    """임의 곡선의 R²는 항상 [0,1] 안에 있다."""
    r2 = compute_uptrend_r2([0, 5, 1, 9, 3, 8, 2, 10])
    assert 0.0 <= r2 <= 1.0


def test_uptrend_r2_too_few_points_is_zero():
    """점이 2개 미만이면 R²=0."""
    assert compute_uptrend_r2([]) == 0.0
    assert compute_uptrend_r2([42]) == 0.0


def test_uptrend_r2_flat_curve_is_zero():
    """평평한(분산 0) 곡선은 R²=0."""
    assert compute_uptrend_r2([5, 5, 5, 5, 5]) == 0.0

def test_uptrend_r2_downward_line_is_zero():
    """DR-01: 완벽한 하락 직선은 corr²=1.0 이지만 우상향 의도가 아니므로 0.0이어야 한다."""
    assert compute_uptrend_r2([50, 40, 30, 20, 10]) == 0.0


def test_uptrend_r2_positive_line_is_near_one():
    """DR-01: 양(+)기울기 완벽한 직선은 여전히 R²≈1.0(하락 게이트가 상승 케이스를 죽이면 안 됨)."""
    r2 = compute_uptrend_r2([10, 20, 30, 40, 50])
    assert abs(r2 - 1.0) < 1e-9


# ============================================================
# (b) gate: 위반 시 composite 0
# ============================================================

def test_gate_fails_when_trade_count_below_min():
    """trade_count < min_trades -> composite 0, 사유에 trade_count 명시."""
    config = LoopConfig(min_trades=30, mdd_cap=50.0)
    metrics = {"cagr": 30.0, "mdd_pct": 10.0, "trade_count": 5, "total_profit_krw": 1000}
    res = compute_fitness(metrics, [0, 100, 200, 300, 400], config)
    assert res.gate_passed is False
    assert res.score == 0.0
    assert "trade_count" in res.reason


def test_gate_fails_when_mdd_exceeds_cap():
    """mdd > mdd_cap -> composite 0, 사유에 mdd 명시."""
    config = LoopConfig(min_trades=3, mdd_cap=25.0)
    metrics = {"cagr": 30.0, "mdd_pct": 76.0, "trade_count": 10, "total_profit_krw": 1000}
    res = compute_fitness(metrics, [0, 100, 200, 300, 400], config)
    assert res.gate_passed is False
    assert res.score == 0.0
    assert "mdd" in res.reason


def test_gate_fails_when_total_profit_not_positive():
    """total_profit <= 0 -> composite 0, 사유에 total_profit 명시."""
    config = _passing_config()
    metrics = {"cagr": 5.0, "mdd_pct": 10.0, "trade_count": 10, "total_profit_krw": -500}
    res = compute_fitness(metrics, [0, -100, -200, -300, -400], config)
    assert res.gate_passed is False
    assert res.score == 0.0
    assert "total_profit" in res.reason


def test_gate_fails_when_total_profit_exactly_zero():
    """total_profit == 0 (> 0 아님) -> composite 0."""
    config = _passing_config()
    metrics = {"cagr": 5.0, "mdd_pct": 10.0, "trade_count": 10, "total_profit_krw": 0}
    res = compute_fitness(metrics, [0, 100, 200, 300, 400], config)
    assert res.gate_passed is False
    assert res.score == 0.0


# ============================================================
# (c) 깨끗한 통과 케이스 -> composite > 0 이고 수식 일치
# ============================================================

def test_clean_pass_score_matches_component_math():
    """gate 통과 시 score == calmar x uptrend_r2 (gate=1)."""
    config = _passing_config()
    metrics = {"cagr": 30.0, "mdd_pct": 10.0, "trade_count": 10, "total_profit_krw": 1000}
    equity = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]

    res = compute_fitness(metrics, equity, config)

    assert res.gate_passed is True
    assert res.reason == "ok"
    assert res.score > 0.0

    expected_calmar = 30.0 / 10.0  # = 3.0
    assert abs(res.calmar - expected_calmar) < 1e-9
    # 완벽한 직선이므로 R²=1 -> score == calmar.
    assert abs(res.uptrend_r2 - 1.0) < 1e-9
    assert abs(res.score - (res.calmar * res.uptrend_r2)) < 1e-9
    assert abs(res.score - expected_calmar) < 1e-6


# ============================================================
# (d) MDD≈0 안전성
# ============================================================

def test_calmar_mdd_zero_positive_cagr_is_capped_not_crash():
    """MDD≈0 이고 CAGR>0 -> 큰 상한값(크래시/∞ 아님)."""
    val = compute_calmar(cagr=20.0, mdd=0.0)
    assert val > 0.0
    assert val == 1e6  # _CALMAR_CAP


def test_calmar_mdd_zero_nonpositive_cagr_is_zero():
    """MDD≈0 이고 CAGR<=0 -> 0.0."""
    assert compute_calmar(cagr=0.0, mdd=0.0) == 0.0
    assert compute_calmar(cagr=-5.0, mdd=0.0) == 0.0


def test_compute_fitness_with_mdd_zero_does_not_crash():
    """compute_fitness가 mdd_pct=0에서 예외 없이 결과를 낸다."""
    config = _passing_config()
    metrics = {"cagr": 20.0, "mdd_pct": 0.0, "trade_count": 10, "total_profit_krw": 1000}
    equity = [0, 100, 200, 300, 400, 500, 600, 700, 800, 900]
    res = compute_fitness(metrics, equity, config)
    # mdd=0 <= mdd_cap 이므로 gate 통과, calmar는 capped 값.
    assert res.gate_passed is True
    assert res.calmar == 1e6
    assert res.score > 0.0


def test_load_exit_quality_from_csv_neutral_trades_do_not_change_payoff_ratio(tmp_path):
    """DR-01: 무손익(0%) 거래 98건을 1승/1패 세트에 더해도 payoff_ratio 는 변하지 않는다."""
    import csv

    from ai_strategy_loop.fitness.score import load_exit_quality_from_csv

    base_rows = [{"수익률": "10.0"}, {"수익률": "-5.0"}]
    neutral_rows = [{"수익률": "0.0"} for _ in range(98)]

    def _write(path, rows):
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=["수익률"])
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    base_csv = _write(tmp_path / "base.csv", base_rows)
    padded_csv = _write(tmp_path / "padded.csv", base_rows + neutral_rows)

    base_result = load_exit_quality_from_csv(base_csv)
    padded_result = load_exit_quality_from_csv(padded_csv)

    assert abs(base_result["payoff_ratio"] - 2.0) < 1e-9  # mean_win=10 / |mean_loss|=5.
    assert abs(padded_result["payoff_ratio"] - base_result["payoff_ratio"]) < 1e-9
