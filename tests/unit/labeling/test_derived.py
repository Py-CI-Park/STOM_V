"""QSP11 파생 특징 — 엔진 정의 재현 계약.

역산으로 확정된 정의(2026-08-06, 와이드 기준선 CSV `B_*` 대조 3일 표본):
체결강도평균=최근 n틱 평균 / 누적수량=최근 n틱 합 / 초당거래대금평균=**round**(평균) /
등락율각도=deg(atan(diff_n / n × 5)).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.derived import ANGLE_SCALE, WINDOWS, angle, build, feature_names


def _series(n: int = 200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame({
        "초당거래대금": rng.uniform(1, 100, n),
        "초당매수수량": rng.uniform(0, 500, n),
        "초당매도수량": rng.uniform(0, 500, n),
        "체결강도": rng.uniform(50, 300, n),
        "등락율": np.cumsum(rng.normal(0, 0.1, n)) + 5,
        "매도총잔량": rng.uniform(1000, 5000, n),
        "매수총잔량": rng.uniform(1000, 5000, n),
    })


def test_angle_matches_engine_formula() -> None:
    frame = _series()
    result = angle(frame["등락율"], 60)
    values = frame["등락율"].to_numpy()

    assert np.isnan(result[:60]).all(), "창이 안 찬 구간은 NaN 이어야 한다"
    expected = math.degrees(math.atan((values[100] - values[40]) / 60 * ANGLE_SCALE))
    assert result[100] == pytest.approx(expected, abs=1e-9)


def test_surge_ratio_uses_rounded_mean_like_the_engine() -> None:
    frame = _series()
    features = build(frame)
    window = 60
    mean_60 = round(frame["초당거래대금"].iloc[41:101].mean())
    expected = frame["초당거래대금"].iloc[100] / mean_60

    assert features[f"초당거래대금배율_{window}"][100] == pytest.approx(expected, abs=1e-9)


def test_cumulative_and_book_ratios() -> None:
    frame = _series()
    features = build(frame)
    window = 30
    cum_buy = frame["초당매수수량"].iloc[71:101].sum()
    cum_sell = frame["초당매도수량"].iloc[71:101].sum()

    assert features[f"누적매수매도비_{window}"][100] == pytest.approx(cum_buy / cum_sell, abs=1e-9)
    assert features["매수흐름_매도잔량비"][100] == pytest.approx(
        frame["초당매수수량"].iloc[100] / frame["매도총잔량"].iloc[100], abs=1e-9)
    assert features["초당거래대금직전비"][100] == pytest.approx(
        frame["초당거래대금"].iloc[100] / frame["초당거래대금"].iloc[99], abs=1e-9)


def test_min_lane_uses_minute_columns() -> None:
    frame = _series().rename(columns={
        "초당거래대금": "분당거래대금", "초당매수수량": "분당매수수량",
        "초당매도수량": "분당매도수량"})
    features = build(frame, flow_prefix="분당")

    assert "분당거래대금배율_60" in features
    assert "분당거래대금" not in features          # 원값은 파생이 아니다
    assert set(feature_names("분당")) <= set(features)


def test_feature_names_cover_every_built_feature() -> None:
    assert set(feature_names()) == set(build(_series()))
    assert len(WINDOWS) == 2


def test_no_lookahead_every_feature_uses_only_past() -> None:
    """미래 누출 검사 — 뒷부분을 바꿔도 앞부분 값은 변하지 않아야 한다."""
    frame = _series()
    baseline = build(frame)
    tampered = frame.copy()
    tampered.loc[150:, :] = tampered.loc[150:, :] * 10      # 미래만 오염

    after = build(tampered)
    for name, values in baseline.items():
        head, later = values[:150], after[name][:150]
        assert np.allclose(head, later, equal_nan=True), f"{name} 가 미래를 보고 있다"
