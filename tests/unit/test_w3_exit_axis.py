# -*- coding: utf-8 -*-
"""W3 매도 축 평가기 계약 테스트.

계약:
  1. 정확/하한/상한을 반드시 구분해 고지한다(상한을 판정에 쓰면 곧 미래 참조).
  2. time_stop 은 라벨의 지평 수익률 그 자체다(exact).
  3. barrier 는 기존 지도 경로(frontier.row_values)와 **수치가 일치**한다 —
     축이 다르면 배리어 계열과 신규 계열을 나란히 읽을 수 없다.
  4. trailing 하한은 무장 사실(최초 도달)만 쓰고 구간 최고점을 쓰지 않는다.
  5. mfe_capture 는 천장이다 — 어떤 규칙도 이보다 클 수 없다.
  6. 격자는 사전 고정이며 전셀 보고한다(고른 셀만 보고하지 않는다).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling import exit_axis
from ai_strategy_loop.labeling.exit_axis import ExitRule, evaluate, evaluate_grid, gross_to_net
from ai_strategy_loop.labeling.frontier import row_values


def _frame(n=6):
    """합성 라벨 프레임 — 봉투·배리어 도달 시각·지평 수익률."""
    return pd.DataFrame({
        "일자": [20250403] * (n // 2) + [20250404] * (n - n // 2),
        "종목코드": [f"00000{i}" for i in range(n)],
        "시분초": [90100 + i for i in range(n)],
        # 배리어 최초 도달(초). 600 = 미도달(지평).
        "hit_up_1": [60, 500, 150, 600, 20, 600],
        "hit_up_2": [100, 600, 300, 600, 50, 600],
        "hit_up_3": [600, 600, 600, 600, 120, 600],
        "hit_up_5": [600, 600, 600, 600, 280, 600],
        "hit_dn_1": [600, 200, 600, 600, 600, 600],
        "hit_dn_2": [600, 600, 600, 400, 600, 600],
        "hit_dn_3": [600, 600, 600, 600, 600, 600],
        # 봉투(총값 %)
        "mfe_300": [2.5, 0.4, 3.1, 0.2, 5.0, 0.1],
        "mae_300": [-0.3, -1.2, -0.5, -2.1, -0.2, -0.4],
        "mfe_600": [2.8, 0.5, 3.4, 0.3, 5.4, 0.2],
        "mae_600": [-0.4, -1.4, -0.6, -2.3, -0.3, -0.5],
        # 지평 수익률(순값 %)
        "frA_300": [1.4, -0.9, 2.0, -1.8, 3.2, -0.2],
        "frB_300": [1.4, -0.9, 2.0, -1.8, 3.2, -0.2],
        "frA_600": [1.1, -1.1, 2.4, -2.0, 3.9, -0.3],
        "frB_600": [1.1, -1.1, 2.4, -2.0, 3.9, -0.3],
    })


# ---------------------------------------------------------------------------
# 정확/근사 고지
# ---------------------------------------------------------------------------

def test_exactness_is_declared_per_family():
    assert ExitRule("time_stop", horizon=300).exactness == "exact"
    assert ExitRule("barrier", horizon=300, tp_pct=2.0, sl_pct=1.0).exactness == "exact"
    # 하한/상한을 반드시 갈라야 한다 — 상한을 후보 판정에 쓰면 곧 미래 참조다.
    assert ExitRule("trailing", horizon=300, arm_pct=2.0, give_pct=1.0).exactness == "lower_bound"
    assert ExitRule("trailing_ceiling", horizon=300, arm_pct=2.0,
                    give_pct=1.0).exactness == "upper_bound"
    assert ExitRule("mfe_capture", horizon=600).exactness == "upper_bound"


def test_grid_rows_carry_exactness():
    rows = evaluate_grid(_frame())
    assert rows, "격자가 비었다"
    assert all("exactness" in row for row in rows)
    upper = {row["rule"] for row in rows if row["exactness"] == "upper_bound"}
    lower = {row["rule"] for row in rows if row["exactness"] == "lower_bound"}
    assert any(r.startswith("mfe_capture") for r in upper)
    assert any(r.startswith("trailing_max") for r in upper)
    assert any(r.startswith("trailing_min") for r in lower)


# ---------------------------------------------------------------------------
# 정확 계열
# ---------------------------------------------------------------------------

def test_time_stop_is_label_value_itself():
    frame = _frame()
    got = evaluate(frame, ExitRule("time_stop", horizon=300))
    assert np.allclose(got, frame["frA_300"].to_numpy())


def test_barrier_matches_existing_map_path():
    """★ 기존 지도 경로와 수치가 일치해야 나란히 읽을 수 있다."""
    frame = _frame()
    mine = evaluate(frame, ExitRule("barrier", horizon=300, tp_pct=2.0, sl_pct=1.0))
    theirs = row_values(frame, tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
                        horizon=300, timeout_label="frA_300")
    assert np.allclose(mine, theirs)


def test_barrier_outside_sealed_grid_is_rejected():
    with pytest.raises(ValueError):
        evaluate(_frame(), ExitRule("barrier", horizon=300, tp_pct=4.0, sl_pct=1.0))


def test_barrier_requires_both_thresholds():
    with pytest.raises(ValueError):
        evaluate(_frame(), ExitRule("barrier", horizon=300, tp_pct=2.0))


# ---------------------------------------------------------------------------
# 근사 계열
# ---------------------------------------------------------------------------

def test_trailing_lower_bound_has_no_lookahead():
    """★ 하한은 무장 사실(최초 도달)만 쓰고 구간 최고점을 쓰지 않는다."""
    frame = _frame()
    got = evaluate(frame, ExitRule("trailing", horizon=300, arm_pct=2.0, give_pct=1.0))
    armed = frame["hit_up_2"].to_numpy() < 300          # 최초 도달 = 정확
    timeout = frame["frA_300"].to_numpy()

    assert np.allclose(got[armed], gross_to_net(np.array([2.0 - 1.0]))[0])
    assert np.allclose(got[~armed], timeout[~armed])
    # MFE 를 바꿔도 하한은 변하지 않는다 — 미래를 보지 않는다는 증거.
    louder = frame.copy()
    louder["mfe_300"] = louder["mfe_300"] * 3
    assert np.allclose(
        got, evaluate(louder, ExitRule("trailing", horizon=300, arm_pct=2.0, give_pct=1.0)),
    )


def test_trailing_ceiling_uses_peak_and_dominates_lower_bound():
    frame = _frame()
    lower = evaluate(frame, ExitRule("trailing", horizon=300, arm_pct=2.0, give_pct=1.0))
    upper = evaluate(frame, ExitRule("trailing_ceiling", horizon=300, arm_pct=2.0, give_pct=1.0))
    assert np.all(upper >= lower - 1e-9)
    armed = frame["hit_up_2"].to_numpy() < 300
    assert np.allclose(upper[armed], gross_to_net(frame["mfe_300"].to_numpy()[armed] - 1.0))


def test_trailing_requires_arm_and_give():
    with pytest.raises(ValueError):
        evaluate(_frame(), ExitRule("trailing", horizon=300, arm_pct=2.0))
    with pytest.raises(ValueError):        # 봉인 격자 밖 무장 임계
        evaluate(_frame(), ExitRule("trailing", horizon=300, arm_pct=4.0, give_pct=1.0))


def test_mfe_capture_is_a_ceiling():
    """어떤 규칙도 고점 전량 포착을 넘을 수 없다."""
    frame = _frame()
    ceiling = evaluate(frame, ExitRule("mfe_capture", horizon=300))
    for rule in (
        ExitRule("time_stop", horizon=300),
        ExitRule("trailing", horizon=300, arm_pct=1.0, give_pct=0.5),
        ExitRule("trailing_ceiling", horizon=300, arm_pct=1.0, give_pct=0.5),
        ExitRule("barrier", horizon=300, tp_pct=2.0, sl_pct=1.0),
    ):
        got = evaluate(frame, rule)
        assert np.all(got <= ceiling + 1e-9), rule.label


def test_gross_to_net_subtracts_round_trip_cost():
    """총값 0% 진입은 비용만큼 손실이다 — 축 변환이 맞는지 확인."""
    assert gross_to_net(np.array([0.0]))[0] < 0
    assert gross_to_net(np.array([0.0]))[0] == pytest.approx(-0.2097, abs=1e-3)


# ---------------------------------------------------------------------------
# 격자 계약
# ---------------------------------------------------------------------------

def test_default_grid_is_prefixed_and_reports_all_cells():
    grid = exit_axis.default_grid()
    labels = [r.label for r in grid]
    assert len(labels) == len(set(labels)), "격자에 중복 셀이 있다"
    # 사전 고정 지평만 쓴다(사후에 고르면 그 자체가 편의).
    assert set(r.horizon for r in grid) <= set(exit_axis.ENVELOPE_HORIZONS)
    # **만기값(frA_*)이 필요한** 규칙군만 RETURN_HORIZONS 제약을 받는다.
    #   mfe_capture 는 봉투만, trailing_exact 는 라벨 v4 실현값 열만 쓴다.
    needs_timeout = {"time_stop", "barrier", "trailing", "trailing_ceiling"}
    for rule in grid:
        if rule.family in needs_timeout:
            assert rule.horizon in exit_axis.RETURN_HORIZONS, rule.label

    rows = evaluate_grid(_frame(), grid)
    assert len(rows) == len(grid), "전셀 보고가 아니다 — 일부 셀이 누락됐다"


def test_missing_column_reports_unavailable_not_crash():
    frame = _frame().drop(columns=["mfe_600"])
    rows = evaluate_grid(frame, [ExitRule("mfe_capture", horizon=600)])
    assert rows[0]["available"] is False
    assert "mfe_600" in rows[0]["reason"]


def test_grid_rows_include_day_statistics():
    rows = evaluate_grid(_frame(), [ExitRule("time_stop", horizon=300)])
    row = rows[0]
    assert row["days"] == 2
    assert "day_mean_pct" in row and "day_positive_ratio" in row


# ---------------------------------------------------------------------------
# 라벨 v4 — 트레일링 실현값(정확 계열)
# ---------------------------------------------------------------------------

def test_trailing_exact_reads_label_column():
    """라벨 v4 열이 있으면 정확 계열로 그대로 읽는다(재계산·근사 없음)."""
    frame = _frame()
    frame["trail_2_1"] = [1.2, -0.4, 2.2, -1.5, 3.0, -0.1]
    rule = ExitRule("trailing_exact", arm_pct=2.0, give_pct=1.0)
    assert rule.exactness == "exact"
    assert np.allclose(evaluate(frame, rule), frame["trail_2_1"].to_numpy())


def test_trailing_exact_without_label_reports_rebuild_needed():
    """열이 없으면 조용히 근사로 대체하지 않는다 — 재빌드가 필요하다고 말한다."""
    rows = evaluate_grid(_frame(), [ExitRule("trailing_exact", arm_pct=2.0, give_pct=1.0)])
    assert rows[0]["available"] is False
    assert "재빌드" in rows[0]["reason"]


def test_trailing_exact_requires_arm_and_give():
    with pytest.raises(ValueError):
        evaluate(_frame(), ExitRule("trailing_exact", arm_pct=2.0))
