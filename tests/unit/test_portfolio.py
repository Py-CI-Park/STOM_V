"""포트폴리오 결합 시뮬 v0 — 단위 테스트.

검증 항목:
  1. 완전 역상관 2종: combined_mdd < sum(per_mdd) 이고 diversification_gain > 0
  2. 동일 시리즈 2종: 분산 이득 ≈ 0 (상관 1, 결합 MDD = 개별 MDD)
  3. 날짜 불일치(부분 겹침): 합집합 처리 확인
  4. 시리즈 1개: error dict 반환
"""

import math

from ai_strategy_loop.fitness.portfolio import (
    combined_curve,
    mdd_money,
    portfolio_report,
)


# ---------------------------------------------------------------------------
# mdd_money 단위 테스트
# ---------------------------------------------------------------------------

def test_mdd_money_empty_returns_zero():
    assert mdd_money([]) == 0.0


def test_mdd_money_single_returns_zero():
    assert mdd_money([100.0]) == 0.0


def test_mdd_money_monotone_up_returns_zero():
    assert mdd_money([10.0, 20.0, 30.0]) == 0.0


def test_mdd_money_simple_drawdown():
    # 100 → 150 → 80 → 120: peak=150, trough=80 → mdd=70
    curve = [100.0, 150.0, 80.0, 120.0]
    assert mdd_money(curve) == 70.0


def test_mdd_money_all_negative():
    curve = [-10.0, -20.0, -30.0]
    # peak는 첫 원소(-10), -10 → -30 → dd=20
    assert mdd_money(curve) == 20.0


# ---------------------------------------------------------------------------
# combined_curve 단위 테스트
# ---------------------------------------------------------------------------

def test_combined_curve_equal_weight_two_series():
    s = {
        "A": {"20240101": 100.0, "20240102": 200.0},
        "B": {"20240101": 100.0, "20240102": 200.0},
    }
    result = combined_curve(s)
    # 균등 가중 1/2씩 → 각 날 100, 200 → 누적 100, 300
    assert result["days"] == ["20240101", "20240102"]
    assert result["curve"] == [100.0, 300.0]
    assert result["total"] == 300.0


def test_combined_curve_union_of_dates():
    """날짜 합집합: 한쪽에 없는 날은 0으로 채워야 한다."""
    s = {
        "A": {"20240101": 200.0},
        "B": {"20240102": 100.0},
    }
    result = combined_curve(s)
    assert result["days"] == ["20240101", "20240102"]
    # 균등 1/2 가중, 날짜1: A=200*0.5=100, B=0 → 100; 날짜2: A=0, B=100*0.5=50
    assert result["curve"][0] == pytest.approx(100.0)
    assert result["curve"][1] == pytest.approx(150.0)


def test_combined_curve_empty_series():
    result = combined_curve({})
    assert result["days"] == []
    assert result["curve"] == []
    assert result["total"] == 0.0


# ---------------------------------------------------------------------------
# 테스트 1: 완전 역상관 2종
# ---------------------------------------------------------------------------

def _anticorrelated_series():
    """A: +1000, -1000 교대 / B: -1000, +1000 교대 (완전 역상관)."""
    n = 20
    series_a = {}
    series_b = {}
    for i in range(n):
        day = f"2024{(i // 28 + 1):02d}{(i % 28 + 1):02d}"
        # A는 홀수 인덱스 양수, 짝수 인덱스 음수
        series_a[day] = 1000.0 if i % 2 == 0 else -1000.0
        series_b[day] = -1000.0 if i % 2 == 0 else 1000.0
    return {"A": series_a, "B": series_b}


def test_anticorrelated_combined_mdd_smaller_than_mean_individual():
    """역상관 결합 시 combined_mdd < 개별 MDD 가중평균."""
    report = portfolio_report(_anticorrelated_series())
    assert "error" not in report
    assert report["combined_mdd"] < report["mean_individual_mdd"]


def test_anticorrelated_diversification_gain_positive():
    """역상관 분산 이득 > 0."""
    report = portfolio_report(_anticorrelated_series())
    assert report["diversification_gain"] is not None
    assert report["diversification_gain"] > 0.0


# ---------------------------------------------------------------------------
# 테스트 2: 동일 시리즈 2종 — 분산 이득 ≈ 0
# ---------------------------------------------------------------------------

def _identical_series():
    """두 전략이 완전히 동일한 일별 손익."""
    days = {f"202401{i:02d}": float(100 * (i - 10)) for i in range(1, 29)}
    return {"X": dict(days), "Y": dict(days)}


def test_identical_series_diversification_gain_zero():
    """동일 시리즈 2종 결합의 분산 이득은 정확히 0이어야 한다 (의미 교정 검증).

    수식 (2026-06-12 교정 — 분모를 합이 아닌 가중평균으로):
      결합 일손익        = 0.5x + 0.5x = x → combined_mdd = individual_mdd
      mean_individual_mdd = individual_mdd
      gain               = 1 - mdd/mdd = 0

    같은 전략을 두 번 든다고 분산 이득이 생기면 안 된다 — 합으로 나누던
    종전 정의는 동일 전략 N개 결합에 1-1/N의 가짜 이득을 부여했다.
    """
    report = portfolio_report(_identical_series())
    assert "error" not in report
    gain = report["diversification_gain"]
    assert gain is not None
    assert gain == pytest.approx(0.0, abs=1e-9)


def test_identical_series_correlation_near_one():
    """동일 시리즈 상관은 1에 가까워야 한다."""
    report = portfolio_report(_identical_series())
    corr = report["correlation"]
    assert corr is not None
    # corr["matrix"][0][1] 이 피어슨 상관 (≈1.0)
    assert corr["matrix"][0][1] == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 테스트 3: 날짜 불일치(부분 겹침) — 합집합 처리
# ---------------------------------------------------------------------------

def test_partial_overlap_union_date_count():
    """부분 겹침: 결합 곡선의 날짜 수 = 전략별 날짜 합집합."""
    s = {
        "A": {"20240101": 100.0, "20240102": 200.0, "20240103": 150.0},
        "B": {"20240102": 50.0, "20240103": 75.0, "20240104": 100.0},
    }
    report = portfolio_report(s)
    assert "error" not in report
    combined = combined_curve(s)
    # 합집합: 20240101, 20240102, 20240103, 20240104 → 4일
    assert len(combined["days"]) == 4
    assert combined["days"] == ["20240101", "20240102", "20240103", "20240104"]


def test_partial_overlap_missing_days_filled_zero():
    """겹치지 않는 날의 손익은 0으로 채워 결합한다."""
    s = {
        "A": {"20240101": 400.0},
        "B": {"20240102": 200.0},
    }
    result = combined_curve(s)
    # 날짜1: A=400*0.5=200, B=0 → cum=200
    # 날짜2: A=0, B=200*0.5=100 → cum=300
    assert result["curve"][0] == pytest.approx(200.0)
    assert result["curve"][1] == pytest.approx(300.0)
    assert result["total"] == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# 테스트 4: 시리즈 1개 → error dict
# ---------------------------------------------------------------------------

def test_single_series_returns_error_dict():
    """시리즈 1개면 예외 없이 error 키를 가진 dict를 반환한다."""
    result = portfolio_report({"A": {"20240101": 100.0}})
    assert isinstance(result, dict)
    assert "error" in result
    assert "error" not in ["names", "combined_mdd", "diversification_gain"]


def test_empty_series_returns_error_dict():
    """시리즈 0개도 error dict를 반환한다."""
    result = portfolio_report({})
    assert isinstance(result, dict)
    assert "error" in result


# ---------------------------------------------------------------------------
# 추가: portfolio_report 반환 키 완전성
# ---------------------------------------------------------------------------

def test_portfolio_report_keys_complete():
    """정상 입력 시 필수 키가 모두 있어야 한다."""
    s = {
        "A": {"20240101": 100.0, "20240102": -50.0},
        "B": {"20240101": -80.0, "20240102": 120.0},
    }
    report = portfolio_report(s)
    required_keys = {
        "names", "per_total", "per_mdd",
        "combined_total", "combined_mdd",
        "mean_individual_mdd", "diversification_gain",
        "correlation", "marginal_mdd",
    }
    assert required_keys.issubset(report.keys())


def test_marginal_mdd_excludes_each_strategy():
    """marginal_mdd 항목은 해당 전략 제외 후 나머지 결합 MDD여야 한다."""
    s = {
        "A": {"20240101": 500.0, "20240102": -300.0, "20240103": 200.0},
        "B": {"20240101": -100.0, "20240102": 400.0, "20240103": -50.0},
    }
    report = portfolio_report(s)
    # marginal_mdd["A"] = B만 있을 때 MDD
    b_only = combined_curve({"B": s["B"]})
    expected_a = mdd_money(b_only["curve"])
    assert report["marginal_mdd"]["A"] == pytest.approx(expected_a)


import pytest  # noqa: E402 — pytest는 파일 하단에서도 동작
