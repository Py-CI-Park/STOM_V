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


def _trade(name, buy, sell, hold, pct, krw, *, mae=None, mfe=None, exit_reason=""):
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
