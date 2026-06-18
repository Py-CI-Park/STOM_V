"""tests/unit/test_regime_advisory.py — regime_advisory 순수 함수 단위 테스트."""
import sqlite3

import pytest

from ai_strategy_loop.fitness.regime_advisory import (
    label_regimes,
    load_daily_turnover_from_moneytop,
    monthly_aggregate,
    regime_breakdown,
)


# ---------------------------------------------------------------------------
# 1. monthly_aggregate
# ---------------------------------------------------------------------------

def test_monthly_aggregate_averages_within_month():
    daily = {
        "20220101": {"turnover": 100.0},
        "20220115": {"turnover": 200.0},
        "20220201": {"turnover": 50.0},
    }
    result = monthly_aggregate(daily)
    assert result["202201"]["turnover"] == pytest.approx(150.0)
    assert result["202202"]["turnover"] == pytest.approx(50.0)


def test_monthly_aggregate_single_day_per_month():
    daily = {"20260101": {"vol": 300.0, "turnover": 500.0}}
    result = monthly_aggregate(daily)
    assert result == {"202601": {"vol": 300.0, "turnover": 500.0}}


def test_monthly_aggregate_empty_returns_empty():
    assert monthly_aggregate({}) == {}


def test_monthly_aggregate_multiple_metrics():
    daily = {
        "20220101": {"a": 10.0, "b": 20.0},
        "20220102": {"a": 30.0, "b": 40.0},
    }
    result = monthly_aggregate(daily)
    assert result["202201"]["a"] == pytest.approx(20.0)
    assert result["202201"]["b"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# 2. label_regimes
# ---------------------------------------------------------------------------

def test_label_regimes_median_threshold():
    # 값: 100, 200, 300 → 중앙값 200 → 200 이상=active, 미만=contracted
    monthly = {
        "202201": {"turnover": 100.0},
        "202202": {"turnover": 200.0},
        "202203": {"turnover": 300.0},
    }
    result = label_regimes(monthly)
    assert result["202201"] == "contracted"
    assert result["202202"] == "active"   # >= 중앙값
    assert result["202203"] == "active"


def test_label_regimes_explicit_threshold():
    monthly = {
        "202201": {"turnover": 50.0},
        "202202": {"turnover": 150.0},
    }
    result = label_regimes(monthly, threshold=100.0)
    assert result["202201"] == "contracted"
    assert result["202202"] == "active"


def test_label_regimes_missing_metric_excluded():
    monthly = {
        "202201": {"turnover": 100.0},
        "202202": {"vol": 999.0},  # turnover 없음
    }
    result = label_regimes(monthly, metric="turnover")
    assert "202201" in result
    assert "202202" not in result   # metric 없는 월은 결과에서 제외


def test_label_regimes_empty_monthly_returns_empty():
    assert label_regimes({}) == {}


def test_label_regimes_all_same_value_all_active():
    # 중앙값과 동일하면 active (>=)
    monthly = {"202201": {"turnover": 100.0}, "202202": {"turnover": 100.0}}
    result = label_regimes(monthly)
    assert all(v == "active" for v in result.values())


# ---------------------------------------------------------------------------
# 3. regime_breakdown
# ---------------------------------------------------------------------------

def _make_pnl():
    """2022-01(active) 2개 날짜, 2022-02(contracted) 1개, 2022-03(unlabeled) 1개."""
    return {
        "20220101": 1000.0,
        "20220115": 500.0,
        "20220201": -200.0,
        "20220301": 300.0,   # 레짐 라벨 없는 월
    }


def _make_regimes():
    return {"202201": "active", "202202": "contracted"}


def test_regime_breakdown_basic_structure():
    result = regime_breakdown(_make_pnl(), _make_regimes())
    assert "active" in result
    assert "contracted" in result
    assert "unlabeled" in result
    assert "concentration" in result
    assert "warning" in result


def test_regime_breakdown_profit_sums():
    result = regime_breakdown(_make_pnl(), _make_regimes())
    assert result["active"]["profit"] == pytest.approx(1500.0)
    assert result["contracted"]["profit"] == pytest.approx(-200.0)
    assert result["unlabeled"]["profit"] == pytest.approx(300.0)


def test_regime_breakdown_days_count():
    result = regime_breakdown(_make_pnl(), _make_regimes())
    assert result["active"]["days"] == 2
    assert result["contracted"]["days"] == 1
    assert result["unlabeled"]["days"] == 1


def test_regime_breakdown_months_set():
    result = regime_breakdown(_make_pnl(), _make_regimes())
    assert result["active"]["months"] == {"202201"}
    assert result["unlabeled"]["months"] == {"202203"}


def test_regime_breakdown_unlabeled_separated():
    """레짐 라벨 없는 월의 손익이 unlabeled에 집계되고 은폐되지 않는다."""
    result = regime_breakdown(_make_pnl(), _make_regimes())
    assert result["unlabeled"]["profit"] != 0.0
    assert result["unlabeled"]["days"] > 0


def test_regime_breakdown_warning_triggered():
    """한 레짐에 이익 90% 이상 → warning 발동."""
    pnl = {"20220101": 900.0, "20220201": 100.0}
    regimes = {"202201": "active", "202202": "contracted"}
    result = regime_breakdown(pnl, regimes)
    assert result["concentration"] > 0.8
    assert result["warning"] == "레짐 편중 — 한 레짐 의존 후보"


def test_regime_breakdown_warning_not_triggered():
    """이익이 고르게 분포 → warning None."""
    pnl = {"20220101": 500.0, "20220201": 500.0}
    regimes = {"202201": "active", "202202": "contracted"}
    result = regime_breakdown(pnl, regimes)
    assert result["concentration"] == pytest.approx(0.5)
    assert result["warning"] is None


def test_regime_breakdown_no_positive_profit_concentration_zero():
    """이익이 전혀 없으면 concentration=0.0."""
    pnl = {"20220101": -100.0, "20220201": -200.0}
    regimes = {"202201": "active", "202202": "contracted"}
    result = regime_breakdown(pnl, regimes)
    assert result["concentration"] == pytest.approx(0.0)
    assert result["warning"] is None


def test_regime_breakdown_empty_pnl():
    result = regime_breakdown({}, {"202201": "active"})
    assert result["active"]["profit"] == pytest.approx(0.0)
    assert result["active"]["days"] == 0


# ---------------------------------------------------------------------------
# 4. load_daily_turnover_from_moneytop (인메모리 sqlite)
# ---------------------------------------------------------------------------

def _make_moneytop_db():
    """인메모리 moneytop 모사 테이블 생성."""
    con = sqlite3.connect(":memory:")
    con.execute(
        "CREATE TABLE moneytop ("
        '"[index]" TEXT, '
        "vol1 REAL, "
        "vol2 REAL"
        ")"
    )
    con.executemany(
        'INSERT INTO moneytop VALUES (?, ?, ?)',
        [
            ("20220101090000", 100.0, 50.0),
            ("20220101100000", 200.0, 80.0),
            ("20220102090000", 300.0, 120.0),
            ("20220201090000", 400.0, 160.0),
        ],
    )
    con.commit()
    return con


def test_load_daily_turnover_sums_columns():
    con = _make_moneytop_db()
    result = load_daily_turnover_from_moneytop(con, turnover_columns=["vol1", "vol2"])
    # 20220101: (100+50) + (200+80) = 430
    assert result["20220101"] == pytest.approx(430.0)
    # 20220102: 300+120 = 420
    assert result["20220102"] == pytest.approx(420.0)
    # 20220201: 400+160 = 560
    assert result["20220201"] == pytest.approx(560.0)


def test_load_daily_turnover_single_column():
    con = _make_moneytop_db()
    result = load_daily_turnover_from_moneytop(con, turnover_columns=["vol1"])
    assert result["20220101"] == pytest.approx(300.0)  # 100+200


def test_load_daily_turnover_unknown_column_ignored():
    con = _make_moneytop_db()
    result = load_daily_turnover_from_moneytop(
        con, turnover_columns=["vol1", "nonexistent"]
    )
    # nonexistent 무시 → vol1만 합산
    assert result["20220101"] == pytest.approx(300.0)


def test_load_daily_turnover_all_unknown_returns_empty():
    con = _make_moneytop_db()
    result = load_daily_turnover_from_moneytop(con, turnover_columns=["ghost"])
    assert result == {}


def test_load_daily_turnover_keys_are_yyyymmdd():
    con = _make_moneytop_db()
    result = load_daily_turnover_from_moneytop(con, turnover_columns=["vol1"])
    for key in result:
        assert len(key) == 8
        assert key.isdigit()
