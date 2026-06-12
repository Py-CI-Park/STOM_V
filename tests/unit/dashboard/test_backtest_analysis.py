"""Backtest analysis pure-function tests (PR2).

합성 트레이드 데이터로 summary/equity/distribution/heatmap/underwater/insights 를
검증한다. 빈 입력 무예외 계약도 함께 확인한다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.dashboard import backtest_analysis as A  # noqa: E402


def _trade(
    name, buy, sell, hold, pct, krw, *, mae=None, mfe=None, exit_reason="",
    of_strength=None, of_buy_rest=None, of_sell_rest=None, of_prevday=None, of_updown=None,
):
    return {
        "name": name,
        "buy_time": buy,
        "sell_time": sell,
        "day": int(sell[:8]),
        "hold_min": float(hold),
        "profit_pct": float(pct),
        "profit_krw": float(krw),
        "mae": mae,
        "mfe": mfe,
        "exit_reason": exit_reason,
        "of_strength": of_strength,
        "of_buy_rest": of_buy_rest,
        "of_sell_rest": of_sell_rest,
        "of_prevday": of_prevday,
        "of_updown": of_updown,
    }


def _sample_trades():
    """3 거래일에 걸친 6 거래(이익 3, 손실 3)."""
    return [
        _trade("알파", "202504070930", "202504071000", 30, 2.0, 20000),
        _trade("베타", "202504071030", "202504071100", 30, -1.0, -10000),
        _trade("알파", "202504080935", "202504081005", 30, 3.0, 30000),
        _trade("감마", "202504081330", "202504081400", 30, -2.0, -25000),
        _trade("알파", "202504090940", "202504091200", 140, 5.0, 50000),
        _trade("베타", "202504091030", "202504091100", 30, -0.5, -5000),
    ]


# ---------------------------------------------------------------- empty inputs
def test_empty_inputs_never_raise():
    assert A.summary_metrics([]) == A._empty_summary()
    assert A.equity_series([]) == {"daily": [], "cumulative": [], "drawdown": []}
    dist = A.pnl_distribution([])
    assert dist["pnl_histogram"] == [] and dist["top_contributors"] == []
    assert A.time_heatmap([]) == {"cells": []}
    uw = A.underwater([])
    assert uw["series"] == [] and uw["max_drawdown"] is None
    assert A.generate_insights([]) == []
    assert A.full_analysis(None)["trade_count"] == 0


def test_load_trades_csv_missing_file_returns_empty():
    assert A.load_trades_csv("/nonexistent/path/file.csv") == []
    assert A.load_trades_csv("") == []
    assert A.load_trades_csv(None) == []


# ------------------------------------------------------------------- summary
def test_summary_metrics_basic():
    s = A.summary_metrics(_sample_trades())
    assert s["trade_count"] == 6
    assert s["win_count"] == 3
    assert s["loss_count"] == 3
    assert s["win_rate"] == 50.0
    assert s["total_profit_krw"] == 60000.0  # 20+30+50 -10-25-5 (천원)
    assert abs(s["total_profit_pct"] - 6.5) < 1e-9  # 2+3+5 -1-2-0.5
    assert s["trading_days"] == 3
    # payoff = avg_win(33333.3) / |avg_loss(13333.3)| = 2.5
    assert abs(s["payoff_ratio"] - 2.5) < 1e-6
    # profit factor = 100000 / 40000 = 2.5
    assert abs(s["profit_factor"] - 2.5) < 1e-9
    assert s["max_consecutive_wins"] >= 1
    assert s["median_hold_min"] == 30.0


def test_summary_drawdown_and_streaks():
    # 손실만 연속 3회 → 누적곡선 하강.
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 10000),
        _trade("a", "202504070935", "202504071005", 10, -1.0, -5000),
        _trade("a", "202504070940", "202504071010", 10, -1.0, -5000),
        _trade("a", "202504070945", "202504071015", 10, -1.0, -5000),
    ]
    s = A.summary_metrics(trades)
    assert s["max_consecutive_losses"] == 3
    assert s["max_consecutive_wins"] == 1
    # peak=10000 (1거래 후), 이후 -15000 → trough=-5000, dd=15000.
    assert s["max_drawdown_krw"] == 15000.0


def test_sharpe_zero_when_no_variance():
    # 모든 거래가 같은 날, 단일 거래일 → daily 표본 1개 → sharpe 0.
    trades = [_trade("a", "202504070930", "202504071000", 10, 1.0, 10000)]
    s = A.summary_metrics(trades)
    assert s["sharpe"] == 0.0
    assert s["calmar"] == 0.0  # MDD 0.


# -------------------------------------------------------------------- equity
def test_equity_series_cumulative_and_downsample():
    eq = A.equity_series(_sample_trades())
    assert len(eq["cumulative"]) == 3  # 거래일 3개.
    # 누적: day1=+10000, day2=+15000(누적), day3=+60000(누적).
    cum = [c["cum_profit"] for c in eq["cumulative"]]
    assert cum[0] == 10000.0
    assert cum[1] == 15000.0
    assert cum[2] == 60000.0
    # drawdown: day2 누적 15000 > peak? day1 peak=10000, day2=15000 새 peak → dd=0.
    assert eq["drawdown"][-1]["drawdown"] == 0.0


# ---------------------------------------------------------------- distribution
def test_distribution_histograms_and_contributors():
    dist = A.pnl_distribution(_sample_trades())
    assert len(dist["pnl_histogram"]) >= 1
    assert sum(b["count"] for b in dist["pnl_histogram"]) == 6
    assert len(dist["hold_histogram"]) >= 1
    # 알파가 최대 기여(20+30+50=100000), 감마가 최저(-25000).
    top_names = [c["name"] for c in dist["top_contributors"]]
    assert top_names[0] == "알파"
    assert dist["top_contributors"][0]["profit_krw"] == 100000.0
    bottom_names = [c["name"] for c in dist["bottom_contributors"]]
    assert "감마" in bottom_names


def test_histogram_single_value():
    trades = [_trade("a", "202504070930", "202504071000", 10, 1.0, 1000)] * 3
    dist = A.pnl_distribution(trades)
    # 모든 pct 동일 → 단일 bin.
    assert len(dist["pnl_histogram"]) == 1
    assert dist["pnl_histogram"][0]["count"] == 3


# ------------------------------------------------------------------- heatmap
def test_time_heatmap_weekday_slots():
    hm = A.time_heatmap(_sample_trades())
    cells = hm["cells"]
    assert len(cells) >= 1
    # 2025-04-07 = 월요일(weekday 0). 09:30 → slot=(9*60+30)//30=19.
    monday = [c for c in cells if c["weekday"] == 0]
    assert monday
    slot19 = [c for c in monday if c["slot"] == 19]
    assert slot19 and slot19[0]["slot_label"] == "09:30"


# ----------------------------------------------------------------- underwater
def test_underwater_max_drawdown_window():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 30000),   # day1 peak +30000
        _trade("a", "202504080930", "202504081000", 10, -1.0, -40000), # day2 trough -10000
        _trade("a", "202504090930", "202504091000", 10, 1.0, 50000),   # day3 recover +40000
    ]
    uw = A.underwater(trades)
    md = uw["max_drawdown"]
    assert md is not None
    assert md["drawdown"] == 40000.0  # 30000 - (-10000)
    assert md["start_date"] == 20250407
    assert md["trough_date"] == 20250408
    assert md["recovery_date"] == 20250409


def test_underwater_no_recovery():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 30000),
        _trade("a", "202504080930", "202504081000", 10, -1.0, -40000),
    ]
    uw = A.underwater(trades)
    assert uw["max_drawdown"]["recovery_date"] is None


# ------------------------------------------------------------------- insights
def test_generate_insights_returns_rules():
    insights = A.generate_insights(_sample_trades())
    assert isinstance(insights, list)
    assert len(insights) >= 1
    for ins in insights:
        assert set(ins.keys()) == {"severity", "title", "detail"}
        assert ins["severity"] in ("info", "warning", "critical")


def test_insights_consecutive_losses_rule():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, -1.0, -5000) for _ in range(6)
    ]
    insights = A.generate_insights(trades)
    titles = [i["title"] for i in insights]
    assert "연속 패배 구간" in titles
    assert "순손실 결과" in titles


def test_insights_profit_factor_loss_rule():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 5000),
        _trade("a", "202504070935", "202504071005", 10, -3.0, -20000),
    ]
    insights = A.generate_insights(trades)
    titles = [i["title"] for i in insights]
    assert "손실 우위 전략" in titles


# ------------------------------------------------------- csv roundtrip parsing
def test_load_trades_csv_roundtrip(tmp_path: Path):
    csv_path = tmp_path / "trades.csv"
    csv_path.write_text(
        "﻿종목명,매수시간,매도시간,보유시간,수익률,수익금\n"
        "알파,202504070930,202504071000,30,2.0,20000\n"
        "베타,202504071030,202504071100,30,-1.0,-10000\n"
        ",,bad,,,\n",  # 불량 행 — 건너뜀.
        encoding="utf-8",
    )
    trades = A.load_trades_csv(str(csv_path))
    assert len(trades) == 2
    assert trades[0]["name"] == "알파"
    assert trades[0]["profit_krw"] == 20000.0
    assert trades[0]["day"] == 20250407


def test_full_analysis_from_csv(tmp_path: Path):
    csv_path = tmp_path / "trades.csv"
    lines = ["﻿종목명,매수시간,매도시간,보유시간,수익률,수익금"]
    for t in _sample_trades():
        lines.append(f"{t['name']},{t['buy_time']},{t['sell_time']},{int(t['hold_min'])},{t['profit_pct']},{int(t['profit_krw'])}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bundle = A.full_analysis(str(csv_path))
    assert bundle["trade_count"] == 6
    assert bundle["summary"]["total_profit_krw"] == 60000.0
    assert "equity" in bundle and "insights" in bundle
    # 1단계 — mae_mfe/exit_reasons 가 묶음에 포함된다(합성 CSV 엔 결측 → 빈 구조 허용).
    assert "mae_mfe" in bundle and "exit_reasons" in bundle


# ----------------------------------------------------------- filter_trades (B)
def test_filter_trades_by_buy_time_range():
    trades = _sample_trades()
    # 매수시간(YYYYMMDDHHMMSS 가 아니라 YYYYMMDDHHMM=12자리) — int 비교는 동일하게 동작.
    buys = sorted(int(t["buy_time"]) for t in trades)
    mid = buys[len(buys) // 2]
    sub = A.filter_trades(trades, t_start=mid)
    assert all(int(t["buy_time"]) >= mid for t in sub)
    assert 0 < len(sub) < len(trades)
    # 상한만.
    upper = A.filter_trades(trades, t_end=buys[0])
    assert all(int(t["buy_time"]) <= buys[0] for t in upper)


def test_filter_trades_empty_range_no_raise():
    trades = _sample_trades()
    buys = sorted(int(t["buy_time"]) for t in trades)
    # 첫 거래보다 이른 상한 → 빈 결과(무예외).
    assert A.filter_trades(trades, t_end=buys[0] - 1) == []
    # 경계 둘 다 None → 원본 그대로.
    assert len(A.filter_trades(trades)) == len(trades)


def test_filter_trades_skips_nonnumeric_buy_time():
    trades = [_trade("a", "bad", "202504071000", 10, 1.0, 1000)]
    assert A.filter_trades(trades, t_start=0) == []


def test_full_analysis_with_range(tmp_path: Path):
    csv_path = tmp_path / "trades.csv"
    lines = ["﻿종목명,매수시간,매도시간,보유시간,수익률,수익금"]
    for t in _sample_trades():
        lines.append(f"{t['name']},{t['buy_time']},{t['sell_time']},{int(t['hold_min'])},{t['profit_pct']},{int(t['profit_krw'])}")
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    buys = sorted(int(t["buy_time"]) for t in _sample_trades())
    mid = buys[len(buys) // 2]
    bundle = A.full_analysis(str(csv_path), t_start=mid)
    assert bundle["trade_count"] < 6
    assert bundle["trade_count"] > 0


# ----------------------------------------------------------------- mae_mfe (D)
def test_mae_mfe_points_exclude_missing():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 1000, mae=-0.5, mfe=2.0, exit_reason="익절"),
        _trade("b", "202504070935", "202504071005", 20, -1.0, -2000, mae=-1.5, mfe=0.3, exit_reason="손절"),
        _trade("c", "202504070940", "202504071010", 10, 0.5, 500),  # mae/mfe 결측 → 제외.
    ]
    pts = A.mae_mfe(trades)
    assert len(pts) == 2
    p0 = pts[0]
    assert set(p0.keys()) == {"mae", "mfe", "pnl_pct", "hold_sec", "code"}
    assert p0["mae"] == -0.5 and p0["mfe"] == 2.0
    assert p0["pnl_pct"] == 1.0
    assert p0["hold_sec"] == 600.0  # 10분 → 600초.


def test_mae_mfe_empty_no_raise():
    assert A.mae_mfe([]) == []
    assert A.mae_mfe(_sample_trades()) == []  # 합성 trade 엔 mae/mfe 결측.


def test_mae_mfe_downsamples_over_cap():
    big = [
        _trade("x", "202504070930", "202504071000", 1, 0.1, 100, mae=-0.1, mfe=0.1)
        for _ in range(1500)
    ]
    pts = A.mae_mfe(big)
    assert len(pts) <= A._SCATTER_MAX


# ------------------------------------------------------- exit_reason_breakdown
def test_exit_reason_breakdown_groups_and_sorts():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 10000, exit_reason="익절"),
        _trade("b", "202504070935", "202504071005", 10, 2.0, 20000, exit_reason="익절"),
        _trade("c", "202504070940", "202504071010", 10, -1.0, -5000, exit_reason="손절"),
    ]
    rows = A.exit_reason_breakdown(trades)
    assert len(rows) == 2
    # total_pnl 내림차순 → 익절(30000) 먼저.
    assert rows[0]["reason"] == "익절"
    assert rows[0]["count"] == 2
    assert rows[0]["total_pnl"] == 30000.0
    assert rows[0]["win_rate"] == 100.0
    assert rows[1]["reason"] == "손절"
    assert rows[1]["win_rate"] == 0.0


def test_exit_reason_breakdown_blank_reason():
    trades = [_trade("a", "202504070930", "202504071000", 10, 1.0, 1000)]
    rows = A.exit_reason_breakdown(trades)
    assert rows[0]["reason"] == "(미상)"


def test_exit_reason_breakdown_empty():
    assert A.exit_reason_breakdown([]) == []


# ============================================================================
# 2단계 B — monte_carlo
# ============================================================================
def _multiday_trades():
    """5 거래일 · 일별 손익이 서로 다른 데이터(셔플 효과 검증용)."""
    return [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 30000),    # day1
        _trade("a", "202504080930", "202504081000", 10, -1.0, -50000),  # day2
        _trade("a", "202504090930", "202504091000", 10, 2.0, 40000),    # day3
        _trade("a", "202504100930", "202504101000", 10, -1.0, -20000),  # day4
        _trade("a", "202504110930", "202504111000", 10, 1.0, 25000),    # day5
    ]


def test_monte_carlo_reproducible_with_seed():
    trades = _multiday_trades()
    mc1 = A.monte_carlo(trades, n=300, seed=7)
    mc2 = A.monte_carlo(trades, n=300, seed=7)
    assert mc1["mdd_krw"] == mc2["mdd_krw"]
    assert mc1["final"] == mc2["final"]
    assert mc1["ruin_prob"] == mc2["ruin_prob"]
    assert mc1["fan"] == mc2["fan"]


def test_monte_carlo_empty_and_zero_n_no_raise():
    empty = A.monte_carlo([], n=100)
    assert empty["n"] == 0 and empty["days"] == 0 and empty["fan"] == []
    assert empty["mdd_pct"] == {"p5": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p95": 0.0}
    # n=0 → 빈 분포(무예외).
    z = A.monte_carlo(_multiday_trades(), n=0)
    assert z["n"] == 0


def test_monte_carlo_final_invariant_under_shuffle():
    # 최종 누적손익은 셔플 순서와 무관(합은 동일) → final 백분위가 모두 동일해야 한다.
    trades = _multiday_trades()
    mc = A.monte_carlo(trades, n=500, seed=1)
    total = sum(t["profit_krw"] for t in trades)  # 25000
    for key in ("p5", "p25", "p50", "p75", "p95"):
        assert abs(mc["final"][key] - total) < 1e-6
    # observed 최종손익도 총합과 일치.
    assert abs(mc["observed"]["final_krw"] - total) < 1e-6


def test_monte_carlo_quantile_monotonic():
    mc = A.monte_carlo(_multiday_trades(), n=800, seed=3)
    q = mc["mdd_krw"]
    assert q["p5"] <= q["p25"] <= q["p50"] <= q["p75"] <= q["p95"]
    # MDD 는 항상 >=0.
    assert q["p5"] >= 0.0


def test_monte_carlo_fan_downsampled():
    # 250 거래일 → fan 은 200pt 이하로 다운샘플.
    trades = [
        _trade("a", f"202504{(i % 28) + 1:02d}0930", f"202504{(i % 28) + 1:02d}1000", 10, 0.1, (i % 5 - 2) * 1000)
        for i in range(250)
    ]
    # 서로 다른 일자가 되도록 day 를 강제로 분산(같은 월일 중복 방지 위해 day 직접 세팅).
    for i, t in enumerate(trades):
        t["day"] = 20250101 + i
    mc = A.monte_carlo(trades, n=50, seed=9)
    assert mc["days"] == 250
    assert len(mc["fan"]) <= A._MC_FAN_MAX


# ============================================================================
# 2단계 C — entry_orderflow
# ============================================================================
def _orderflow_trades():
    """승(높은 체결강도) vs 패(낮은 체결강도) 분리가 명확한 합성 데이터."""
    wins = [
        _trade("w", "202504070930", "202504071000", 10, 1.0, 1000,
               of_strength=120.0, of_buy_rest=8000.0, of_sell_rest=2000.0, of_prevday=300.0, of_updown=5.0)
        for _ in range(10)
    ]
    losses = [
        _trade("l", "202504070935", "202504071005", 10, -1.0, -1000,
               of_strength=60.0, of_buy_rest=2000.0, of_sell_rest=8000.0, of_prevday=150.0, of_updown=1.0)
        for _ in range(10)
    ]
    return wins + losses


def test_entry_orderflow_separates_win_loss():
    of = A.entry_orderflow(_orderflow_trades())
    assert "wins" in of and "losses" in of and "separation" in of
    # 체결강도: 승 120 > 패 60 → diff = +60.
    sep_by_var = {s["var"]: s for s in of["separation"]}
    assert "strength" in sep_by_var
    assert abs(sep_by_var["strength"]["diff"] - 60.0) < 1e-6
    assert sep_by_var["strength"]["win_p50"] == 120.0
    assert sep_by_var["strength"]["loss_p50"] == 60.0
    # 호가불균형: 승 8000/2000=4.0 vs 패 2000/8000=0.25 → diff +3.75.
    assert abs(sep_by_var["imbalance"]["diff"] - 3.75) < 1e-6


def test_entry_orderflow_separation_sorted_by_abs_diff():
    of = A.entry_orderflow(_orderflow_trades())
    diffs = [abs(s["diff"]) for s in of["separation"]]
    assert diffs == sorted(diffs, reverse=True)


def test_entry_orderflow_missing_columns_no_raise():
    # of_* 전부 결측 → separation 빈, wins/losses 분포는 n=0.
    of = A.entry_orderflow(_sample_trades())
    assert of["separation"] == []
    assert of["wins"]["strength"]["n"] == 0


def test_entry_orderflow_imbalance_zero_sell_excluded():
    trades = [
        _trade("a", "202504070930", "202504071000", 10, 1.0, 1000,
               of_buy_rest=5000.0, of_sell_rest=0.0),  # 분모 0 → 호가불균형 제외.
    ]
    of = A.entry_orderflow(trades)
    assert of["wins"]["imbalance"]["n"] == 0


# ============================================================================
# 2단계 D — statistical_tests (scipy 유/무 분기)
# ============================================================================
def _two_weekday_trades():
    """월요일(이익 큼) vs 화요일(손실) — 평균차가 크고 그룹 내 분산이 있는 두 요일 버킷.

    Welch t-test 가 정의되려면 그룹 내 분산>0 이어야 하므로 값에 작은 변동을 준다.
    """
    out = []
    for i in range(40):
        pct = 3.0 + (0.2 if i % 2 == 0 else -0.2)  # 월: 평균 3.0, 분산 있음.
        out.append(_trade("a", "202504070930", "202504071000", 10, pct, pct * 1000))
    for i in range(40):
        pct = -2.0 + (0.2 if i % 2 == 0 else -0.2)  # 화: 평균 -2.0, 분산 있음.
        out.append(_trade("a", "202504080930", "202504081000", 10, pct, pct * 1000))
    return out


def test_statistical_tests_detects_significant_weekday():
    st = A.statistical_tests(_two_weekday_trades())
    wd = [s for s in st if s["kind"] == "weekday"]
    assert len(wd) == 2
    # 평균차가 크고 표본 40 → 유의.
    assert any(s["significant"] for s in wd)
    for s in wd:
        assert s["n"] == 40
        assert not s["underpowered"]  # 40 >= 30.
        assert s["p_value"] is not None


def test_statistical_tests_underpowered_small_sample():
    # 표본 < 30 → underpowered=True, significant 는 표본 부족으로 False 강제.
    trades = (
        [_trade("a", "202504070930", "202504071000", 10, 5.0, 5000) for _ in range(5)]
        + [_trade("a", "202504080930", "202504081000", 10, -5.0, -5000) for _ in range(5)]
    )
    st = A.statistical_tests(trades)
    wd = [s for s in st if s["kind"] == "weekday"]
    assert all(s["underpowered"] for s in wd)
    assert all(not s["significant"] for s in wd)


def test_statistical_tests_scipy_and_fallback_branches(monkeypatch):
    trades = _two_weekday_trades()
    # scipy 가용(기본).
    with_scipy = A.statistical_tests(trades)
    # scipy import 실패를 강제 → 정규근사 폴백.
    import builtins
    real_import = builtins.__import__

    def _no_scipy(name, *args, **kwargs):
        if name == "scipy" or name.startswith("scipy."):
            raise ImportError("forced")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_scipy)
    without_scipy = A.statistical_tests(trades)
    # 두 분기 모두 동일 버킷 수 + p값 산출(값은 근사라 다를 수 있으나 유의성 결론은 동일).
    assert len(with_scipy) == len(without_scipy)
    sig_with = {(s["kind"], s["bucket"]) for s in with_scipy if s["significant"]}
    sig_without = {(s["kind"], s["bucket"]) for s in without_scipy if s["significant"]}
    assert sig_with == sig_without


def test_statistical_tests_single_bucket_empty():
    # 모든 거래가 같은 요일+같은 슬롯 → 버킷 1개 → 검정 없음.
    trades = [_trade("a", "202504070930", "202504071000", 10, 1.0, 1000) for _ in range(10)]
    assert A.statistical_tests(trades) == []


# ============================================================================
# 인사이트 연결 — mc/orderflow/stats 가 인사이트에 반영
# ============================================================================
def test_insights_orderflow_rule():
    of = A.entry_orderflow(_orderflow_trades())
    insights = A.generate_insights(_orderflow_trades(), orderflow=of)
    titles = [i["title"] for i in insights]
    assert "승리 진입 오더플로우 프로파일" in titles


def test_insights_statistical_rule():
    trades = _two_weekday_trades()
    st = A.statistical_tests(trades)
    insights = A.generate_insights(trades, stats=st)
    titles = [i["title"] for i in insights]
    # 유의한 양수/음수 시점 중 적어도 하나는 등장.
    assert ("통계적으로 유의한 시점 효과" in titles) or ("유의한 손실 시점" in titles)


def test_full_analysis_includes_stats_and_orderflow(tmp_path: Path):
    csv_path = tmp_path / "trades.csv"
    header = "﻿종목명,매수시간,매도시간,보유시간,수익률,수익금,B_체결강도,B_매수총잔량,B_매도총잔량,B_전일동시간비,B_등락율"
    lines = [header]
    for t in _orderflow_trades():
        lines.append(
            f"{t['name']},{t['buy_time']},{t['sell_time']},{int(t['hold_min'])},{t['profit_pct']},{int(t['profit_krw'])},"
            f"{t['of_strength']},{t['of_buy_rest']},{t['of_sell_rest']},{t['of_prevday']},{t['of_updown']}"
        )
    csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    bundle = A.full_analysis(str(csv_path))
    assert "stats" in bundle and "orderflow" in bundle
    assert bundle["orderflow"]["separation"]  # 분리 가능한 합성 데이터.


# ============================================================================
# portfolio_analysis — 복수 전략 일별손익 합성(결합 곡선·MDD·상관·기여)
# ============================================================================
def _pf_trade(day: str, krw: float):
    """포트폴리오용 최소 trade(매도시간 day + 손익만; 분석은 day/profit_krw 만 쓴다)."""
    return _trade("x", day + "0930", day + "094500", 10, krw / 1000.0, krw)


def test_portfolio_empty_and_single_no_raise():
    empty = A.portfolio_analysis([])
    assert empty["count"] == 0
    assert empty["combined"]["equity"] == []
    assert empty["correlation"]["matrix"] == []
    # 단일 전략도 무예외(상관 1x1, 대각 1.0).
    one = A.portfolio_analysis([{"label": "솔로", "trades": [_pf_trade("20230102", 1000)]}])
    assert one["count"] == 1
    assert one["correlation"]["matrix"] == [[1.0]]


def test_portfolio_combined_total_and_mdd():
    # A: +100, -300, +50 (일별)  → 누적 100, -200, -150 → MDD = 100-(-200)=300.
    # B: +50, +50, +50          → 누적 50, 100, 150     → MDD = 0.
    # 결합(합산): 150, -250, 100 → 누적 150, -100, 0     → MDD = 150-(-100)=250.
    a = [_pf_trade("20230101", 100), _pf_trade("20230102", -300), _pf_trade("20230103", 50)]
    b = [_pf_trade("20230101", 50), _pf_trade("20230102", 50), _pf_trade("20230103", 50)]
    pf = A.portfolio_analysis([{"label": "A", "trades": a}, {"label": "B", "trades": b}])

    strat = {s["label"]: s for s in pf["strategies"]}
    assert strat["A"]["total_profit_krw"] == -150.0
    assert strat["A"]["max_drawdown_krw"] == 300.0
    assert strat["B"]["total_profit_krw"] == 150.0
    assert strat["B"]["max_drawdown_krw"] == 0.0
    # 결합: 총손익 0, 결합 MDD 250(합성 정합).
    assert pf["combined"]["total_profit_krw"] == 0.0
    assert pf["combined"]["max_drawdown_krw"] == 250.0
    assert pf["combined"]["trading_days"] == 3


def test_portfolio_correlation_perfect_positive_and_negative():
    # 완전 양의 상관: B = 2*A (일별).  → corr = +1.
    a = [_pf_trade("20230101", 100), _pf_trade("20230102", -50), _pf_trade("20230103", 30)]
    b = [_pf_trade("20230101", 200), _pf_trade("20230102", -100), _pf_trade("20230103", 60)]
    pf = A.portfolio_analysis([{"label": "A", "trades": a}, {"label": "B", "trades": b}])
    mat = pf["correlation"]["matrix"]
    assert mat[0][0] == 1.0 and mat[1][1] == 1.0
    assert abs(mat[0][1] - 1.0) < 1e-9
    assert abs(mat[1][0] - 1.0) < 1e-9

    # 완전 음의 상관: C = -A.  → corr = -1.
    c = [_pf_trade("20230101", -100), _pf_trade("20230102", 50), _pf_trade("20230103", -30)]
    pf2 = A.portfolio_analysis([{"label": "A", "trades": a}, {"label": "C", "trades": c}])
    assert abs(pf2["correlation"]["matrix"][0][1] - (-1.0)) < 1e-9


def test_portfolio_correlation_aligns_on_day_union_with_zero_fill():
    # A 는 day1·day2, B 는 day2·day3 → 합집합 3일, 결측일 0 채움.
    #   A aligned: [100, -50, 0],  B aligned: [0, 80, 40] → 상관 산출 가능(분산>0).
    a = [_pf_trade("20230101", 100), _pf_trade("20230102", -50)]
    b = [_pf_trade("20230102", 80), _pf_trade("20230103", 40)]
    pf = A.portfolio_analysis([{"label": "A", "trades": a}, {"label": "B", "trades": b}])
    assert pf["combined"]["trading_days"] == 3
    r = pf["correlation"]["matrix"][0][1]
    assert r is not None and -1.0 <= r <= 1.0


def test_portfolio_correlation_none_when_zero_variance():
    # 한 전략이 매일 동일 손익(분산 0) → 상관 정의 불가 → None(무예외).
    a = [_pf_trade("20230101", 100), _pf_trade("20230102", 100)]   # 분산 0.
    b = [_pf_trade("20230101", 50), _pf_trade("20230102", -50)]
    pf = A.portfolio_analysis([{"label": "A", "trades": a}, {"label": "B", "trades": b}])
    assert pf["correlation"]["matrix"][0][1] is None


def test_portfolio_contribution_pct_sums_meaningfully():
    # A 총 +200, B 총 +100, C 총 -100 → 결합 +200. 기여: A=100%, B=50%, C=-50%.
    a = [_pf_trade("20230101", 200)]
    b = [_pf_trade("20230101", 100)]
    c = [_pf_trade("20230101", -100)]
    pf = A.portfolio_analysis([
        {"label": "A", "trades": a}, {"label": "B", "trades": b}, {"label": "C", "trades": c},
    ])
    contrib = {s["label"]: s["contribution_pct"] for s in pf["strategies"]}
    assert abs(contrib["A"] - 100.0) < 1e-6
    assert abs(contrib["B"] - 50.0) < 1e-6
    assert abs(contrib["C"] - (-50.0)) < 1e-6


def test_portfolio_csv_path_input(tmp_path: Path):
    # trades 대신 csv_path 입력도 동작(load_trades_csv 경유).
    def _write(path, krws):
        with open(path, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write("종목명,매수시간,매도시간,보유시간,수익률,수익금\n")
            for i, krw in enumerate(krws):
                day = f"202301{i + 1:02d}"
                fh.write(f"x,{day}0930,{day}094500,10,{krw / 1000.0},{krw}\n")
        return str(path)

    p1 = _write(tmp_path / "s1.csv", [100, -50, 30])
    p2 = _write(tmp_path / "s2.csv", [50, 50, 50])
    pf = A.portfolio_analysis([{"label": "S1", "csv_path": p1}, {"label": "S2", "csv_path": p2}])
    assert pf["count"] == 2
    assert len(pf["strategies"]) == 2
    assert pf["combined"]["trading_days"] == 3


def test_portfolio_duplicate_labels_uniquified():
    a = [_pf_trade("20230101", 100)]
    b = [_pf_trade("20230101", -100)]
    pf = A.portfolio_analysis([{"label": "동일", "trades": a}, {"label": "동일", "trades": b}])
    labels = pf["correlation"]["labels"]
    assert len(set(labels)) == 2  # 라벨 충돌은 접미 인덱스로 유일화.
