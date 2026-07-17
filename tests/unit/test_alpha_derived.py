"""alpha_lab.dataset.derived / parity 단위 테스트 — v3 P1 파생 재계산기.

검증(계약):
- 합성 시퀀스 수기 검증: 이동평균(윈도우 평균+round 3)·rolling max/min/sum·
  mean round·각도(shift(avg-1), arctan2, cf, round 2) — 기대값은 테스트 안에서
  손계산 리터럴/독립 math 식으로 고정(모듈 자기참조 금지).
- compute_derived_tick: 컬럼명·순서 == list_stock_tick[54:72] 18항,
  워밍업 NaN→0.0(nan_to_num) 미러, 입력 df 불변, 누락 컬럼/잘못된 avg 거부.
- 패리티 하네스: 합성 df에서 엔진 add_rolling_data(read-only import) 대비
  전 18항 일치율 100%, 주입 불일치 검출, 비교 전제(컬럼/행수) 위반 거부.
- 실DB 스팟(있을 때만): 20240103 상위 1종목 전 18항 일치율 >= 99.9.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_lab.dataset.derived import (
    AVG_WINDOW_FROZEN,
    DERIVED_TICK_FEATURES,
    ENGINE_COLUMN_MAP,
    FORMULA_REFS,
    TICK_MA_WINDOWS,
    angle,
    compute_derived_tick,
    engine_column_name,
    moving_average,
    rolling_max,
    rolling_mean_round,
    rolling_min,
    rolling_sum,
)
from alpha_lab.dataset.parity import (
    PASS_THRESHOLD_PCT,
    build_annex_payload,
    compare_columns,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_DB = REPO_ROOT / "_database" / "stock_tick_20240103.db"

EXPECTED_18 = (
    "이동평균60", "이동평균150", "이동평균300", "이동평균600", "이동평균1200",
    "최고현재가", "최저현재가",
    "체결강도평균", "최고체결강도", "최저체결강도",
    "최고초당매수수량", "최고초당매도수량", "누적초당매수수량", "누적초당매도수량",
    "초당거래대금평균", "등락율각도", "당일거래대금각도", "전일비각도",
)


def _synthetic_df(n: int = 80, seed: int = 20260706) -> pd.DataFrame:
    """SOURCE_COLUMNS 8종을 가진 합성 종목-일 tick 행렬(결정적 시드)."""
    rng = np.random.default_rng(seed)
    price = 10_000.0 + np.cumsum(rng.integers(-50, 51, size=n)).astype(float)
    per_sec_amount = rng.integers(0, 5_000_000, size=n).astype(float)
    return pd.DataFrame(
        {
            "현재가": price,
            "체결강도": rng.uniform(10.0, 250.0, size=n).round(2),
            "초당매수수량": rng.integers(0, 900, size=n).astype(float),
            "초당매도수량": rng.integers(0, 900, size=n).astype(float),
            "초당거래대금": per_sec_amount,
            "등락율": rng.uniform(-3.0, 8.0, size=n).round(2),
            "당일거래대금": np.cumsum(per_sec_amount),
            "전일비": rng.uniform(-100.0, 500.0, size=n).round(2),
        }
    )


# ------------------------------------------------- 수기 검증: 이동평균/rolling


def test_moving_average_hand_values():
    price = pd.Series(np.arange(1.0, 71.0))  # 1..70
    ma = moving_average(price, 60)
    assert ma.iloc[:59].isna().all()  # min_periods=window 워밍업
    assert ma.iloc[59] == 30.5  # mean(1..60)
    assert ma.iloc[69] == 40.5  # mean(11..70)


def test_moving_average_round3():
    price = pd.Series([1.0 / 3.0] * 5)
    assert moving_average(price, 3).iloc[-1] == 0.333


def test_rolling_max_min_sum_hand_values():
    s = pd.Series([1.0, 5.0, 2.0, 4.0])
    assert rolling_max(s, 3).iloc[2] == 5.0 and rolling_max(s, 3).iloc[3] == 5.0
    assert rolling_min(s, 3).iloc[2] == 1.0 and rolling_min(s, 3).iloc[3] == 2.0
    assert rolling_sum(s, 3).iloc[2] == 8.0 and rolling_sum(s, 3).iloc[3] == 11.0
    assert rolling_sum(s, 3).iloc[:2].isna().all()


def test_rolling_mean_round_digits():
    strength = pd.Series([1.0, 2.0, 2.0])
    assert rolling_mean_round(strength, 3, 3).iloc[-1] == 1.667  # 5/3
    amount = pd.Series([1000.0, 2000.0, 2500.0])
    assert rolling_mean_round(amount, 3, 0).iloc[-1] == 1833.0  # 5500/3


# --------------------------------------------------------- 수기 검증: 각도


def test_angle_rate_hand_value():
    # 등락율 0.1*i → 29스텝 차이 2.9, cf=5, avg=30 → atan2(14.5, 30) 기반.
    s = pd.Series(0.1 * np.arange(40.0))
    out = angle(s, 30, 5.0)
    expected = round(math.atan2(2.9 * 5.0, 30) / (2 * math.pi) * 360, 2)
    assert expected == 25.8  # 손계산 고정 리터럴
    assert out.iloc[:29].isna().all()
    assert (out.iloc[29:] == expected).all()


def test_angle_no_cf_hand_value():
    # 전일비 = i → 차이 29, 계수 미적용(utility/static.py:129 미러).
    s = pd.Series(np.arange(40.0))
    out = angle(s, 30, None)
    expected = round(math.atan2(29.0, 30) / (2 * math.pi) * 360, 2)
    assert expected == 44.03
    assert (out.iloc[29:] == expected).all()


def test_angle_amount_hand_value():
    # 당일거래대금 = 1000*i → 차이 29000, cf=0.01 → atan2(290, 30) 기반.
    s = pd.Series(1000.0 * np.arange(40.0))
    out = angle(s, 30, 0.01)
    expected = round(math.atan2(290.0, 30) / (2 * math.pi) * 360, 2)
    assert expected == 84.09
    assert (out.iloc[29:] == expected).all()


# ------------------------------------------------------ compute_derived_tick


def test_compute_columns_order_is_sealed_18():
    frame = compute_derived_tick(_synthetic_df())
    assert tuple(frame.columns) == EXPECTED_18
    assert DERIVED_TICK_FEATURES == EXPECTED_18
    assert len(frame) == 80


def test_compute_warmup_nan_to_num_mirror():
    df = _synthetic_df()
    df["초당매수수량"] = 1.0  # 상수 1 → 누적 30 (윈도우 30 합)
    engine_like = compute_derived_tick(df)  # nan_to_num=True 기본
    assert (engine_like["누적초당매수수량"].iloc[:29] == 0.0).all()
    assert engine_like["누적초당매수수량"].iloc[29] == 30.0
    # 행수 80 < 이동평균1200 윈도우 → 전 구간 0.0 (엔진 nan_to_num 실측 동일)
    assert (engine_like["이동평균1200"] == 0.0).all()
    raw = compute_derived_tick(df, nan_to_num=False)
    assert raw["누적초당매수수량"].iloc[:29].isna().all()
    assert raw["이동평균1200"].isna().all()


def test_compute_does_not_mutate_input():
    df = _synthetic_df()
    before = df.copy(deep=True)
    compute_derived_tick(df)
    pd.testing.assert_frame_equal(df, before)


def test_compute_missing_column_raises():
    df = _synthetic_df().drop(columns=["전일비"])
    with pytest.raises(ValueError, match="누락"):
        compute_derived_tick(df)


def test_compute_invalid_avg_raises():
    with pytest.raises(ValueError):
        compute_derived_tick(_synthetic_df(), avg=0)


def test_engine_column_name_map():
    assert engine_column_name("최고현재가") == "최고현재가30"
    assert engine_column_name("체결강도평균", 30) == "체결강도평균30"
    assert engine_column_name("이동평균60") == "이동평균60"
    assert engine_column_name("등락율각도") == "등락율각도"
    assert set(ENGINE_COLUMN_MAP) == set(DERIVED_TICK_FEATURES)
    with pytest.raises(ValueError):
        engine_column_name("현재가")
    assert AVG_WINDOW_FROZEN == 30
    assert TICK_MA_WINDOWS == (60, 150, 300, 600, 1200)
    assert set(FORMULA_REFS) == set(DERIVED_TICK_FEATURES)


# --------------------------------------------------------- 패리티 하네스


def test_parity_synthetic_full_agreement():
    """합성 1300행 — 엔진 add_rolling_data 재적용 대비 전 18항 100% 일치."""
    pytest.importorskip("utility.static")
    from alpha_lab.dataset.parity import engine_reference

    df = _synthetic_df(n=1300, seed=7)
    mine = compute_derived_tick(df)
    ref = engine_reference(df)
    stats = compare_columns(mine, ref)
    assert set(stats) == set(DERIVED_TICK_FEATURES)
    for name, stat in stats.items():
        assert stat["agreement_pct"] == 100.0, (name, stat)
        assert stat["n"] == 1300


def test_compare_columns_detects_mismatch():
    df = _synthetic_df(n=100)
    mine = compute_derived_tick(df)
    ref = mine.copy(deep=True)
    ref.loc[50, "체결강도평균"] = ref.loc[50, "체결강도평균"] + 1.0
    stats = compare_columns(mine, ref)
    bad = stats["체결강도평균"]
    assert bad["n_agree"] == 99 and bad["agreement_pct"] < 100.0
    assert bad["max_rel_err"] > 0.0
    assert stats["최고현재가"]["agreement_pct"] == 100.0


def test_compare_columns_rejects_shape_mismatch():
    df = _synthetic_df(n=60)
    mine = compute_derived_tick(df)
    with pytest.raises(ValueError, match="컬럼"):
        compare_columns(mine, mine[list(reversed(mine.columns))])
    with pytest.raises(ValueError, match="행수"):
        compare_columns(mine, mine.iloc[:30])


def test_build_annex_payload_pass_fail_split():
    per_feature = {
        name: {"n": 1000, "n_agree": 1000, "agreement_pct": 100.0, "max_rel_err": 0.0}
        for name in DERIVED_TICK_FEATURES
    }
    per_feature["전일비각도"] = {
        "n": 1000, "n_agree": 990, "agreement_pct": 99.0, "max_rel_err": 0.5,
    }
    result = {
        "per_feature": per_feature,
        "samples": [{"day": 20240103, "code": "000100", "rows": 1000}],
        "rows_total": 1000,
        "codes": {"20240103": ["000100"]},
    }
    payload = build_annex_payload(result)
    assert {f["name"] for f in payload["passed_features"]} == (
        set(DERIVED_TICK_FEATURES) - {"전일비각도"}
    )
    assert len(payload["failed_features"]) == 1
    fail = payload["failed_features"][0]
    assert fail["name"] == "전일비각도" and "사유" in fail
    assert all("formula_ref" in f for f in payload["passed_features"])
    assert payload["method"]["avg_frozen"] == 30
    assert PASS_THRESHOLD_PCT == 99.9


# ------------------------------------------------------------- 실DB 스팟


@pytest.mark.skipif(not REAL_DB.exists(), reason="_database/stock_tick_20240103.db 없음")
def test_parity_real_db_spot_top_code():
    pytest.importorskip("utility.static")
    from alpha_lab.dataset.parity import (
        engine_reference, load_engine_input, pick_codes,
    )

    codes = pick_codes(REAL_DB, 20240103, 1)
    assert len(codes) == 1
    df = load_engine_input(REAL_DB, codes[0], 20240103)
    assert list(df.columns[:2]) == ["index", "현재가"] and df.shape[1] == 54
    mine = compute_derived_tick(df)
    ref = engine_reference(df)
    stats = compare_columns(mine, ref)
    for name, stat in stats.items():
        assert stat["agreement_pct"] >= PASS_THRESHOLD_PCT, (name, stat)
