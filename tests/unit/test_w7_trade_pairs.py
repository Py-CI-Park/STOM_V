# -*- coding: utf-8 -*-
"""W7-5 계약 테스트 — 거래 짝 뷰어(페이지 34).

계약:
  1. **같은 진입만 짝짓는다.** 한쪽에만 있는 거래는 짝이 아니므로 따로 센다.
  2. 짝지은 평균이 `engine_ladder.paired_test` 와 **같은 수**를 낸다.
     두 곳이 어긋나면 화면이 판정과 다른 말을 한다.
  3. 청산 사유별로 개선/악화를 가른다 — "어디서 이기고 어디서 지는가".
  4. 꼬리 지배 여부(top10_share)를 낸다. 평균 하나로는 안 보인다.
  5. 짝이 없으면 없다고 답한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.controller import trade_pairs as tp
from ai_strategy_loop.labeling import engine_ladder as el


def _frame(profits, holds=None, reasons=None, names=None, offset=0):
    n = len(profits)
    names = names or [f"S{i:03d}" for i in range(offset, offset + n)]
    return pd.DataFrame({
        "매수시간": [f"2024030{1 + i % 9}09{(i % 5) + 1:02d}00" for i in range(n)],
        "종목명": names,
        "수익률": profits,
        "수익금": [p * 1000 for p in profits],
        "보유시간": holds or [300.0] * n,
        "매도조건": reasons or ["트레일링"] * n,
    })


def _arm(frame, name):
    f = frame.copy()
    f["일자"] = f["매수시간"].str[:8].astype(int)
    f["entry_key"] = f["매수시간"] + "|" + f["종목명"]
    return el.Arm(name=name, trades=f)


# ---------------------------------------------------------------------------
# 짝짓기
# ---------------------------------------------------------------------------

def test_only_shared_entries_are_paired():
    """★ 한쪽에만 있는 거래를 섞으면 짝지은 비교가 아니다."""
    base = _frame([1.0, 2.0, 3.0])
    chal = _frame([1.5, 2.5], names=list(base["종목명"][:2]))
    chal["매수시간"] = list(base["매수시간"][:2])
    view = tp.analyze(base, chal)
    assert view["pairs"] == 2
    assert view["baseline_only"] == 1 and view["challenger_only"] == 0


def test_no_overlap_says_so():
    base = _frame([1.0, 2.0])
    chal = _frame([1.0, 2.0], names=["X", "Y"], offset=99)
    chal["매수시간"] = ["20240401090100", "20240401090200"]
    view = tp.analyze(base, chal)
    assert view["available"] is False
    assert view["baseline_only"] == 2 and view["challenger_only"] == 2


def test_paired_mean_matches_engine_ladder():
    """★ 화면과 심판이 다른 수를 내면 안 된다."""
    rng = np.random.default_rng(3)
    base_p = rng.normal(0.5, 2.0, 120).round(4)
    chal_p = (base_p + rng.normal(0.2, 1.0, 120)).round(4)
    base, chal = _frame(list(base_p)), _frame(list(chal_p))
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]

    ours = tp.analyze(base, chal)
    theirs = el.paired_test(_arm(base, "b"), _arm(chal, "c"))
    assert ours["pairs"] == theirs["pairs"]
    assert ours["mean_diff_pct"] == pytest.approx(theirs["mean_diff_pct"], rel=1e-9)
    assert ours["improved"] == theirs["improved_trades"]
    assert ours["worsened"] == theirs["worsened_trades"]


# ---------------------------------------------------------------------------
# 읽는 값
# ---------------------------------------------------------------------------

def test_worst_and_best_are_sorted_and_capped():
    base = _frame([0.0] * 40)
    chal = _frame([float(i) - 20 for i in range(40)])
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]
    view = tp.analyze(base, chal, limit=5)
    assert len(view["worst"]) == 5 and len(view["best"]) == 5
    assert view["worst"][0]["차이"] < view["worst"][-1]["차이"]      # 나쁜 순
    assert view["best"][0]["차이"] > view["best"][-1]["차이"]        # 좋은 순
    assert view["worst"][0]["차이"] < view["best"][0]["차이"]


def test_exit_reason_breakdown_splits_win_and_loss():
    """★ '어디서 이기고 어디서 지는가' 에 직접 답한다."""
    base = _frame([1.0, 1.0, 1.0, 1.0])
    chal = _frame([2.0, 2.0, 0.0, 0.0],
                  reasons=["트레일링", "트레일링", "시간손절", "시간손절"])
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]
    rows = {r["매도조건"]: r for r in tp.analyze(base, chal)["exit_reasons"]}
    assert rows["트레일링"]["개선"] == 2 and rows["트레일링"]["악화"] == 0
    assert rows["시간손절"]["악화"] == 2 and rows["시간손절"]["합계차이"] == pytest.approx(-2.0)


def test_top10_share_flags_tail_domination():
    """소수 거래가 결과를 지배하면 평균만 보고 판단하면 안 된다."""
    base = _frame([0.0] * 60)
    chal = _frame([0.0] * 50 + [10.0] * 10)
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]
    assert tp.analyze(base, chal)["top10_share"] == pytest.approx(1.0)


def test_hold_difference_is_reported():
    base = _frame([1.0, 1.0], holds=[500.0, 500.0])
    chal = _frame([1.0, 1.0], holds=[300.0, 300.0])
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]
    view = tp.analyze(base, chal)
    assert view["hold_diff_mean"] == pytest.approx(-200.0)
    assert view["worst"][0]["보유차"] == pytest.approx(-200.0)


def test_rows_carry_both_sides_for_inspection():
    base = _frame([1.0], reasons=["챔피언5"])
    chal = _frame([2.5], reasons=["트레일링"])
    chal["종목명"], chal["매수시간"] = base["종목명"], base["매수시간"]
    row = tp.analyze(base, chal)["best"][0]
    assert row["기준_수익률"] == 1.0 and row["후보_수익률"] == 2.5
    assert row["기준_매도조건"] == "챔피언5" and row["후보_매도조건"] == "트레일링"
    assert row["종목명"] and row["매수시간"]
