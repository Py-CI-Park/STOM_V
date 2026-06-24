"""P5 포렌식 — in-sample per-strategy Lift·EV(기대값) 산출 순수 모듈 테스트.

`ai_strategy_loop/fitness/lift.py`의 compute_lift_ev / lift_ev_by_segment를 검증한다.
순수·무예외 계약(빈/단일클래스/컬럼부재→graceful, status 키로 표현)과
정확값(win>loss 픽스처에서 win_rate·ev·lift·payoff)을 함께 본다.

PROJECT_ROOT sys.path 삽입은 test_quantile_feedback.py 패턴을 따른다.
"""

from __future__ import annotations

import csv
import math
import os
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import ai_strategy_loop.bootstrap  # noqa: E402,F401
from ai_strategy_loop.fitness.lift import (  # noqa: E402
    compute_lift_ev,
    lift_ev_by_segment,
)


def _df(returns) -> pd.DataFrame:
    """수익률 리스트로 per-trade DataFrame을 만든다(수익률 컬럼명='수익률')."""
    return pd.DataFrame({"수익률": list(returns)})


# ---------------------------------------------------------------------------
# compute_lift_ev — 정확값 (win > loss 픽스처)
# ---------------------------------------------------------------------------

def test_compute_lift_ev_exact_values() -> None:
    # 승자 6건(+2.0%), 패자 4건(-1.0%). win_rate=0.6.
    returns = [2.0] * 6 + [-1.0] * 4
    out = compute_lift_ev(_df(returns), baseline_win_rate=0.5)

    assert out["status"] == "ok"
    assert out["n"] == 10
    assert math.isclose(out["win_rate"], 0.6, rel_tol=1e-9)
    assert math.isclose(out["avg_win"], 2.0, rel_tol=1e-9)
    assert math.isclose(out["avg_loss"], -1.0, rel_tol=1e-9)
    # payoff = avg_win / |avg_loss| = 2.0 / 1.0 = 2.0.
    assert math.isclose(out["payoff"], 2.0, rel_tol=1e-9)
    # ev = 0.6*2.0 + 0.4*(-1.0) = 1.2 - 0.4 = 0.8.
    assert math.isclose(out["ev"], 0.8, rel_tol=1e-9)
    # lift = win_rate / baseline = 0.6 / 0.5 = 1.2.
    assert math.isclose(out["lift"], 1.2, rel_tol=1e-9)


def test_compute_lift_ev_lift_uses_baseline() -> None:
    returns = [1.0] * 4 + [-1.0] * 4  # win_rate=0.5.
    out = compute_lift_ev(_df(returns), baseline_win_rate=0.25)
    # lift = 0.5 / 0.25 = 2.0.
    assert math.isclose(out["lift"], 2.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# compute_lift_ev — baseline graceful (0 / 음수 → lift None)
# ---------------------------------------------------------------------------

def test_compute_lift_ev_baseline_zero_lift_none() -> None:
    out = compute_lift_ev(_df([1.0, -1.0, 1.0, -1.0]), baseline_win_rate=0.0)
    assert out["status"] == "ok"
    assert out["lift"] is None


def test_compute_lift_ev_baseline_negative_lift_none() -> None:
    out = compute_lift_ev(_df([1.0, -1.0]), baseline_win_rate=-0.3)
    assert out["lift"] is None


# ---------------------------------------------------------------------------
# compute_lift_ev — graceful (빈 입력 / 컬럼 부재 / 단일 클래스)
# ---------------------------------------------------------------------------

def test_compute_lift_ev_empty_insufficient() -> None:
    out = compute_lift_ev(_df([]))
    assert out["status"] == "insufficient"
    assert out["n"] == 0
    assert out["win_rate"] is None or out["win_rate"] == 0
    assert out["ev"] is None
    assert out["lift"] is None


def test_compute_lift_ev_missing_return_column_insufficient() -> None:
    df = pd.DataFrame({"수익금": [100, -50]})  # '수익률' 컬럼 없음.
    out = compute_lift_ev(df)
    assert out["status"] == "insufficient"
    assert out["ev"] is None


def test_compute_lift_ev_all_winners_single_class() -> None:
    # 전부 승자(손실 없음) → avg_loss 산출 불가.
    out = compute_lift_ev(_df([1.0, 2.0, 3.0]), baseline_win_rate=0.5)
    assert out["status"] == "ok"
    assert math.isclose(out["win_rate"], 1.0, rel_tol=1e-9)
    assert out["avg_loss"] is None
    assert out["payoff"] is None
    # ev = 1.0*avg_win + 0.0*(missing) = avg_win = 2.0.
    assert math.isclose(out["ev"], 2.0, rel_tol=1e-9)


def test_compute_lift_ev_all_losers_single_class() -> None:
    out = compute_lift_ev(_df([-1.0, -2.0, -3.0]), baseline_win_rate=0.5)
    assert out["status"] == "ok"
    assert math.isclose(out["win_rate"], 0.0, rel_tol=1e-9)
    assert out["avg_win"] is None
    assert out["payoff"] is None
    # ev = 0.0*(missing) + 1.0*avg_loss = avg_loss = -2.0.
    assert math.isclose(out["ev"], -2.0, rel_tol=1e-9)


def test_compute_lift_ev_non_numeric_coerced() -> None:
    df = pd.DataFrame({"수익률": ["2.0", "abc", "-1.0"]})  # 'abc' → 드롭.
    out = compute_lift_ev(df, baseline_win_rate=0.5)
    assert out["status"] == "ok"
    assert out["n"] == 2  # 'abc' 제외.
    assert math.isclose(out["win_rate"], 0.5, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# compute_lift_ev — CSV 경로 입력 (BOM 자동 제거)
# ---------------------------------------------------------------------------

def _make_csv(path: Path, returns) -> str:
    """utf-8-sig(BOM) 결과 CSV를 만든다(수익률 컬럼)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "수익률"])
        w.writeheader()
        for r in returns:
            w.writerow({"종목명": "T", "수익률": r})
    return str(path)


def test_compute_lift_ev_csv_path_input(tmp_path) -> None:
    returns = [2.0] * 6 + [-1.0] * 4
    csv_path = _make_csv(tmp_path / "bt.csv", returns)
    out = compute_lift_ev(csv_path, baseline_win_rate=0.5)
    assert out["status"] == "ok"
    assert out["n"] == 10
    assert math.isclose(out["win_rate"], 0.6, rel_tol=1e-9)
    assert math.isclose(out["ev"], 0.8, rel_tol=1e-9)


def test_compute_lift_ev_bad_path_insufficient() -> None:
    out = compute_lift_ev("C:/__no_such_file__/nope.csv")
    assert out["status"] == "insufficient"
    assert out["ev"] is None


# ---------------------------------------------------------------------------
# lift_ev_by_segment (선택) — 세그먼트별 EV/lift
# ---------------------------------------------------------------------------

def _make_segment_csv(path: Path, rows) -> str:
    """rows: [(수익률, 시가총액)] — 시총 세그먼트 라벨링용 CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["종목명", "매수시간", "수익률", "B_시가총액"])
        w.writeheader()
        for i, (pct, cap) in enumerate(rows):
            w.writerow({
                "종목명": "T",
                "매수시간": f"202301{(i % 28) + 1:02d}090100",
                "수익률": pct,
                "B_시가총액": cap,
            })
    return str(path)


def test_lift_ev_by_segment_market_cap(tmp_path) -> None:
    # 소형주(시총 1000대) 승자 집중, 대형주(시총 9000대) 패자 집중.
    rows = []
    for _ in range(10):
        rows.append((2.0, 1000))
        rows.append((-1.0, 9000))
    csv_path = _make_segment_csv(tmp_path / "seg.csv", rows)
    out = lift_ev_by_segment(csv_path, axis="market_cap", baseline_win_rate=0.5, min_samples=5)
    assert out["status"] == "ok"
    assert isinstance(out["segments"], list)
    assert len(out["segments"]) >= 1
    for cell in out["segments"]:
        assert "label" in cell
        assert "n" in cell
        assert "ev" in cell
        assert "win_rate" in cell
        assert "lift" in cell


def test_lift_ev_by_segment_empty_graceful() -> None:
    out = lift_ev_by_segment(_df([]), axis="market_cap")
    assert out["status"] == "insufficient"
    assert out["segments"] == []


def test_lift_ev_by_segment_missing_return_column_graceful() -> None:
    df = pd.DataFrame({"B_시가총액": [1000, 2000]})
    out = lift_ev_by_segment(df, axis="market_cap")
    assert out["status"] == "insufficient"
    assert out["segments"] == []
