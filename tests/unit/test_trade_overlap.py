"""M1(2026-06-11) — 거래 중복도(Jaccard) 테스트.

계약: 키=(종목명, 매수시간 분 절사) / 사전선언 해석 구간(0.8/0.4) /
어떤 실패도 None(advisory — V6 결정 참고용, 판정 미사용).
"""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.trade_overlap import trade_overlap  # noqa: E402


def _csv(path: Path, rows) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "수익금"])
        w.writeheader()
        for name, buy_time, profit in rows:
            w.writerow({"종목명": name, "매수시간": buy_time, "수익금": profit})
    return str(path)


def test_identical_trades_jaccard_one(tmp_path) -> None:
    rows = [("A", "20230102090101", 100), ("B", "20230102090201", -50)]
    a = _csv(tmp_path / "a.csv", rows)
    b = _csv(tmp_path / "b.csv", rows)
    out = trade_overlap(a, b)
    assert out["jaccard"] == 1.0
    assert "대체" in out["interpretation"]


def test_partial_overlap_counts(tmp_path) -> None:
    a = _csv(tmp_path / "a.csv", [
        ("A", "20230102090101", 1), ("B", "20230102090201", 1),
        ("C", "20230102090301", 1), ("D", "20230102090401", 1),
    ])
    b = _csv(tmp_path / "b.csv", [
        ("A", "20230102090101", 1), ("B", "20230102090201", 1),
        ("E", "20230102090501", 1),
    ])
    out = trade_overlap(a, b)
    assert out["n_common"] == 2
    assert out["jaccard"] == 0.4  # 2 / (4+3-2).
    assert "부분 중복" in out["interpretation"]


def test_same_minute_different_seconds_is_same_trade(tmp_path) -> None:
    a = _csv(tmp_path / "a.csv", [("A", "20230102090101", 1)])
    b = _csv(tmp_path / "b.csv", [("A", "20230102090159", 1)])  # 같은 분, 58초 차.
    out = trade_overlap(a, b)
    assert out["jaccard"] == 1.0


def test_low_overlap_label_and_graceful(tmp_path) -> None:
    a = _csv(tmp_path / "a.csv", [("A", "20230102090101", 1)])
    b = _csv(tmp_path / "b.csv", [("Z", "20230103100101", 1)])
    out = trade_overlap(a, b)
    assert out["jaccard"] == 0.0
    assert "포트폴리오" in out["interpretation"]
    assert trade_overlap(a, str(tmp_path / "nope.csv")) is None
