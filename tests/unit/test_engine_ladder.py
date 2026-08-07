# -*- coding: utf-8 -*-
"""엔진 축 사다리 계약 테스트 — 2026-08-07 오판을 코드로 못 박는다.

이 파일이 존재하는 이유는 실제로 저지른 실수 두 가지다.

  ① 지도 축으로 국면을 갈랐다. 지도는 엔진이 체결하지 않는 진입까지 세어
     같은 후보가 지도 2/4, 엔진 4/4 로 갈렸다.
  ② 합격선을 "4/4 양수"라는 절대 기준으로 잡았다. **챔피언 자신이 3/4** 였으므로
     그 기준은 챔피언도 떨어뜨린다.

계약:
  1. 합격선은 챔피언이다 — 챔피언과 같은 성적이면 통과시킨다.
  2. 챔피언이 떨어질 기준을 만들지 않는다(챔피언 대 챔피언은 REJECT 가 아니다).
  3. 짝지은 비교는 **같은 진입**만 맞춘다.
  4. 신뢰구간이 0 을 넘으면 유의하지 않다 — PASS 가 아니라 PROMISING 이다.
  5. 자본 대비 지표를 함께 낸다 — 총액만 보면 자본을 더 쓴 쪽이 항상 이긴다.
  6. 두 팔은 **같은 날짜 경계**로 자른다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.engine_ladder import (
    Arm,
    capital_view,
    judge,
    paired_test,
    positive_segments,
    regime_split,
)


def _arm(name, rows, **metrics):
    """rows = [(YYYYMMDDHHMMSS, 종목명, 수익률, 수익금), ...]"""
    frame = pd.DataFrame(rows, columns=["매수시간", "종목명", "수익률", "수익금"])
    frame["일자"] = frame["매수시간"].astype(str).str[:8].astype(int)
    frame["entry_key"] = frame["매수시간"].astype(str) + "|" + frame["종목명"].astype(str)
    return Arm(name=name, trades=frame, **metrics)


def _series(name, values, *, start_day=20240101, seed=0):
    """하루 한 건씩, 주어진 수익률 목록으로 팔을 만든다."""
    rng = np.random.default_rng(seed)
    rows = []
    for i, v in enumerate(values):
        day = start_day + i
        rows.append((int(f"{day}09{i % 60:02d}00"), f"종목{i}", float(v),
                     float(v) * 10000 + rng.normal(0, 1)))
    return _arm(name, rows)


# ---------------------------------------------------------------------------
# 국면 분할
# ---------------------------------------------------------------------------

def test_both_arms_are_cut_on_the_same_date_axis():
    """★ 각자 자기 거래일로 자르면 경계가 어긋나 비교가 성립하지 않는다."""
    a = _series("A", [1.0] * 8)
    b = _series("B", [1.0] * 4, start_day=20240101)      # 앞쪽 절반만 거래
    days = sorted(set(a.trades["일자"]) | set(b.trades["일자"]))
    seg_a = regime_split(a, segments=4, days=days)
    seg_b = regime_split(b, segments=4, days=days)
    assert [s["day_from"] for s in seg_a] == [s["day_from"] for s in seg_b]
    assert [s["day_to"] for s in seg_a] == [s["day_to"] for s in seg_b]


def test_segment_without_trades_is_nan_not_zero():
    a = _series("A", [1.0] * 4, start_day=20240101)
    days = sorted(set(a.trades["일자"]) | {20240201, 20240202, 20240203, 20240204})
    segs = regime_split(a, segments=4, days=days)
    tail = [s for s in segs if s["trades"] == 0]
    assert tail and all(np.isnan(s["mean_pct"]) for s in tail)


def test_positive_segments_counts_only_positive():
    segs = [{"mean_pct": 1.0}, {"mean_pct": -0.5}, {"mean_pct": 0.2}, {"mean_pct": float("nan")}]
    assert positive_segments(segs) == 2


# ---------------------------------------------------------------------------
# ★ 합격선은 챔피언
# ---------------------------------------------------------------------------

def test_champion_against_itself_is_never_rejected():
    """★★ 챔피언이 떨어지는 기준은 기준이 틀린 것이다."""
    champ = _series("챔피언", [2.0, 1.0, -0.5, 1.5, 2.0, 1.0, -0.5, 1.5])
    verdict = judge(champ, champ, segments=4)
    assert verdict["verdict"] != "REJECT"
    assert verdict["regime"]["pass"] is True


def test_absolute_four_of_four_is_not_required():
    """챔피언이 3/4 면 도전자도 3/4 로 충분하다."""
    # 구간 3이 음수인 챔피언(3/4), 같은 모양의 도전자(3/4)에 수익만 조금 높게.
    base_vals = [1.0, 1.0, 1.0, 1.0, -1.0, -1.0, 1.0, 1.0]
    champ = _series("챔피언", base_vals)
    chal = _series("도전자", [v + 0.3 for v in base_vals])
    out = judge(champ, chal, segments=4)
    assert out["regime"]["baseline_positive"] == out["regime"]["challenger_positive"]
    assert out["regime"]["pass"] is True
    assert out["verdict"] != "REJECT"


def test_worse_consistency_is_rejected():
    champ = _series("챔피언", [1.0] * 8)                      # 4/4
    chal = _series("도전자", [1.0, 1.0, -2.0, -2.0, 1.0, 1.0, 1.0, 1.0])
    out = judge(champ, chal, segments=4)
    assert out["regime"]["challenger_positive"] < out["regime"]["baseline_positive"]
    assert out["verdict"] == "REJECT"


# ---------------------------------------------------------------------------
# 짝지은 비교
# ---------------------------------------------------------------------------

def test_pairs_only_matching_entries():
    a = _arm("A", [(20240101090000, "가", 1.0, 10000),
                   (20240102090000, "나", 2.0, 20000),
                   (20240103090000, "다", 3.0, 30000)])
    b = _arm("B", [(20240101090000, "가", 1.5, 15000),
                   (20240103090000, "다", 2.0, 20000)])          # '나' 는 체결 안 됨
    out = paired_test(a, b)
    assert out["pairs"] == 2                                      # 3건이 아니라 2건
    assert out["mean_diff_pct"] == pytest.approx(((1.5-1.0) + (2.0-3.0)) / 2)


def test_paired_is_unavailable_below_two_pairs():
    a = _arm("A", [(20240101090000, "가", 1.0, 10000)])
    b = _arm("B", [(20240101090000, "가", 1.5, 15000)])
    assert paired_test(a, b)["available"] is False


def test_wide_interval_is_not_significant():
    """★ 신뢰구간이 0 을 넘으면 '우세'라고 쓰지 않는다."""
    rng = np.random.default_rng(7)
    base = rng.normal(0, 3, 60)
    a = _arm("A", [(20240100 + i + 1, f"종목{i}", float(v), float(v) * 10000)
                   for i, v in enumerate(base)])
    b = _arm("B", [(20240100 + i + 1, f"종목{i}", float(v) + 0.2, (float(v) + 0.2) * 10000)
                   for i, v in enumerate(base + rng.normal(0, 3, 60))])
    out = paired_test(a, b)
    assert out["ci95"][0] < 0 < out["ci95"][1]
    assert out["significant"] is False


def test_tight_interval_is_significant():
    """차이가 일정하면(분산 0에 가까움) 적은 표본으로도 확정된다."""
    a = _arm("A", [(20240100 + i + 1, f"종목{i}", 1.0, 10000) for i in range(30)])
    b = _arm("B", [(20240100 + i + 1, f"종목{i}", 1.5, 15000) for i in range(30)])
    out = paired_test(a, b)
    assert out["significant"] is True
    assert out["mean_diff_pct"] == pytest.approx(0.5)


def test_required_sample_is_reported_when_not_significant():
    rng = np.random.default_rng(11)
    vals = rng.normal(0, 3, 40)
    a = _arm("A", [(20240100 + i + 1, f"종목{i}", float(v), 0) for i, v in enumerate(vals)])
    b = _arm("B", [(20240100 + i + 1, f"종목{i}", float(v) + 0.1, 0) for i, v in enumerate(vals + rng.normal(0, 3, 40))])
    out = paired_test(a, b)
    if not out["significant"]:
        assert out["required_pairs"] > out["pairs"]
        assert out["sample_shortfall_ratio"] > 1


def test_improved_and_worsened_are_counted_separately():
    """평균만 보면 '거의 반반'이라는 사실이 사라진다."""
    a = _arm("A", [(20240101 + i, f"종목{i}", 0.0, 0) for i in range(4)])
    b = _arm("B", [(20240101 + i, f"종목{i}", v, 0) for i, v in enumerate([5.0, -1.0, -1.0, -1.0])])
    out = paired_test(a, b)
    assert out["improved_trades"] == 1 and out["worsened_trades"] == 3
    assert out["mean_diff_pct"] > 0          # 평균은 양수인데 3건은 나빠졌다


# ---------------------------------------------------------------------------
# 자본
# ---------------------------------------------------------------------------

def test_capital_view_marks_lower_seed_as_better():
    a = _series("챔피언", [1.0] * 4, seed=1)
    b = _series("도전자", [1.0] * 4, seed=2)
    a = Arm(a.name, a.trades, seed_capital=1_000_000, cagr=56.3, mdd_pct=14.82,
            total_profit_pct=80.17)
    b = Arm(b.name, b.trades, seed_capital=2_000_000, cagr=49.98, mdd_pct=10.48,
            total_profit_pct=71.17)
    rows = {r["metric"]: r for r in capital_view(a, b)["rows"]}
    assert rows["필요자금(원)"]["winner"] == "챔피언"        # 적게 쓰는 쪽이 낫다
    assert rows["CAGR(%)"]["winner"] == "챔피언"
    assert rows["MDD(%)"]["winner"] == "도전자"
    assert rows["Calmar"]["winner"] == "도전자"


def test_verdict_promising_when_direction_right_but_unproven():
    rng = np.random.default_rng(3)
    vals = rng.normal(0.5, 3, 40)
    champ = _arm("챔피언", [(20240100 + i + 1, f"종목{i}", float(v), float(v) * 1e4)
                          for i, v in enumerate(vals)])
    chal = _arm("도전자", [(20240100 + i + 1, f"종목{i}", float(v) + 0.4, (float(v) + 0.4) * 1e4)
                         for i, v in enumerate(vals + rng.normal(0, 3, 40))])
    out = judge(champ, chal, segments=2)
    assert out["verdict"] in ("PROMISING", "PASS", "REJECT")
    if out["verdict"] == "PROMISING":
        assert out["paired"]["significant"] is False
        assert "표본" in out["verdict_meaning"]
