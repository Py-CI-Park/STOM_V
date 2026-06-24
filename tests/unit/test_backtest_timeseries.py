"""백테 시계열 차트 helper — 동시보유 종목수·시간대별 수익 (순수·무예외)."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.backtest_timeseries import (  # noqa: E402
    concurrent_holdings,
    time_of_day_profit,
)


def _csv(path: Path, rows: list) -> str:
    """rows: [(매수시간, 매도시간, 수익률, 수익금)]"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "매도시간", "수익률", "수익금"])
        w.writeheader()
        for buy, sell, ret, prof in rows:
            w.writerow({"종목명": "T", "매수시간": buy, "매도시간": sell, "수익률": ret, "수익금": prof})
    return str(path)


def _fixture(tmp_path: Path) -> str:
    # T1 09:00:00~09:03:00, T2 09:01:00~09:02:00(T1과 겹침), T3 09:30:00~09:31:00(단독).
    return _csv(tmp_path / "ts.csv", [
        ("20230101090000", "20230101090300", 1.0, 1000),
        ("20230101090100", "20230101090200", -0.5, -500),
        ("20230101093000", "20230101093100", 2.0, 2000),
    ])


class TestConcurrentHoldings:
    def test_overlap_counts_max_two(self, tmp_path) -> None:
        r = concurrent_holdings(_fixture(tmp_path))
        assert r["n_trades"] == 3
        assert r["max_concurrent"] == 2  # 09:01~09:02 T1+T2 동시.
        # 진입 시점 동시보유: T1→1, T2→2, T3→1.
        hist = {h["n"]: h["events"] for h in r["histogram"]}
        assert hist == {1: 2, 2: 1}
        assert r["series"][0]["n"] == 1 and max(p["n"] for p in r["series"]) == 2

    def test_missing_columns_graceful(self, tmp_path) -> None:
        p = tmp_path / "no.csv"
        p.write_text("수익률\n1.0\n", encoding="utf-8-sig")
        r = concurrent_holdings(str(p))
        assert r["max_concurrent"] == 0 and r["series"] == []

    def test_bad_input_no_raise(self) -> None:
        assert concurrent_holdings("")["max_concurrent"] == 0
        assert concurrent_holdings(None)["n_trades"] == 0


class TestTimeOfDayProfit:
    def test_buckets_by_time(self, tmp_path) -> None:
        r = time_of_day_profit(_fixture(tmp_path), bucket_sec=300)
        by = {b["time"]: b for b in r["buckets"]}
        assert "09:00" in by and "09:30" in by
        assert by["09:00"]["n"] == 2  # T1·T2 둘 다 09:00 버킷.
        assert by["09:30"]["n"] == 1
        assert abs(by["09:00"]["avg_return"] - 0.25) < 1e-9  # (1.0 + -0.5)/2
        assert by["09:00"]["win_rate"] == 0.5
        assert by["09:30"]["sum_profit"] == 2000

    def test_graceful(self, tmp_path) -> None:
        assert time_of_day_profit("")["buckets"] == []
