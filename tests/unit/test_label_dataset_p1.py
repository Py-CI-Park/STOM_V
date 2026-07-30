"""QSP1 P1 — 라벨 데이터셋 빌더 + 엔진 결과부 v2 확장 회귀 테스트.

고정하는 계약:
  ① TRADE_RESULT_B_COLUMNS v2 확장(17컬럼)이 스냅샷·데이터프레임 양쪽에 일관 반영.
  ② 구버전 14+α 행은 normalize 가 0-패딩(하위호환).
  ③ label_dataset: 파생 수식 정확성 · 리프 좌표 · 컬럼 자동 편입/제외(zero-variance).
  ④ 리프 잔차표가 평균과 중앙값·승률을 병기(R0 발견 — 복권형 분포 왜곡 대응).
"""

from __future__ import annotations

import pandas as pd
import pytest

from backtest.back_static import (
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_BASE_COLUMN_COUNT,
    TRADE_RESULT_EXTRA_COLUMNS,
    normalize_trade_result_rows,
)
from ai_strategy_loop.autopsy import label_dataset as L


# ---------------------------------------------------------------- ① v2 확장
def test_v2_extension_columns_present_and_ordered():
    # 기존 14 + 확장 17 = 31. 확장은 기존 뒤에 append(구 코드가 앞 14를 위치로 읽어도 안전).
    assert len(TRADE_RESULT_B_COLUMNS) == 31
    assert TRADE_RESULT_B_COLUMNS[:14][-1] == "B_분봉저가"
    for col in ("B_시가", "B_고가", "B_저가", "B_체결강도평균",
                "B_초당거래대금", "B_분당거래대금", "B_RSI"):
        assert col in TRADE_RESULT_B_COLUMNS, col
    # EXTRA = B + S + R 순서 계약 유지.
    assert TRADE_RESULT_EXTRA_COLUMNS[: len(TRADE_RESULT_B_COLUMNS)] == TRADE_RESULT_B_COLUMNS


def test_autopsy_b_columns_follow_single_source():
    from ai_strategy_loop.autopsy.analyze import B_COLUMNS, B_TO_STOM_VAR

    assert list(B_COLUMNS) == list(TRADE_RESULT_B_COLUMNS)
    # 모든 B_ 컬럼은 동명 STOM 변수로 매핑돼 있어야 요약 가이드가 끊기지 않는다.
    for col in B_COLUMNS:
        assert col in B_TO_STOM_VAR, col


def test_normalize_pads_legacy_rows_to_new_width():
    base = list(range(TRADE_RESULT_BASE_COLUMN_COUNT))          # 구형 14열 행
    legacy_v1 = base + [0] * 23                                  # 구 확장(14+5+4=23)
    want = TRADE_RESULT_BASE_COLUMN_COUNT + len(TRADE_RESULT_EXTRA_COLUMNS)
    rows = normalize_trade_result_rows([base, legacy_v1], want)
    assert all(len(r) == want for r in rows)
    assert rows[0][:14] == base                                  # 원 데이터 보존


# ------------------------------------------------------------- ③ 파생·리프
def _tick_frame():
    # 2거래: 승 1(+2%)·패 1(-1%). v2 확장 컬럼 포함(신선 CSV 시뮬레이션).
    return pd.DataFrame([
        {"종목명": "A", "시가총액": 2500, "매수시간": "20250407090130",
         "수익률": 2.0, "수익금": 20000,
         "B_현재가": 10100, "B_등락율": 1.0, "B_당일거래대금": 500, "B_거래대금증감": 0,
         "B_체결강도": 120, "B_시가총액": 2500, "B_회전율": 3, "B_전일동시간비": 1.2,
         "B_매수총잔량": 3000, "B_매도총잔량": 1000, "B_시분초": 90130,
         "B_분봉시가": 0, "B_분봉고가": 0, "B_분봉저가": 0,
         "B_시가": 10000, "B_고가": 10200, "B_저가": 9900, "B_체결강도평균": 100,
         "B_초당거래대금": 30, "B_초당거래대금평균": 10,
         "B_누적초당매수수량": 900, "B_누적초당매도수량": 300,
         "B_분당거래대금": 0, "B_분당거래대금평균": 0, "B_분당매수수량": 0,
         "B_분당매도수량": 0, "B_RSI": 0},
        {"종목명": "B", "시가총액": 12000, "매수시간": "20250407091530",
         "수익률": -1.0, "수익금": -10000,
         "B_현재가": 50500, "B_등락율": 1.0, "B_당일거래대금": 900, "B_거래대금증감": 0,
         "B_체결강도": 90, "B_시가총액": 12000, "B_회전율": 1, "B_전일동시간비": 0.8,
         "B_매수총잔량": 1000, "B_매도총잔량": 4000, "B_시분초": 91530,
         "B_분봉시가": 0, "B_분봉고가": 0, "B_분봉저가": 0,
         "B_시가": 50000, "B_고가": 50600, "B_저가": 49800, "B_체결강도평균": 100,
         "B_초당거래대금": 5, "B_초당거래대금평균": 10,
         "B_누적초당매수수량": 200, "B_누적초당매도수량": 600,
         "B_분당거래대금": 0, "B_분당거래대금평균": 0, "B_분당매수수량": 0,
         "B_분당매도수량": 0, "B_RSI": 0},
    ])


def test_enrich_derivations_are_condition_reproducible():
    ds = L.enrich(_tick_frame())
    assert ds.timeframe == "tick"
    row = ds.df.iloc[0]
    # D_전일종가 = 현재가/(1+등락율/100) = 10100/1.01 = 10000
    assert row["D_전일종가"] == pytest.approx(10000.0)
    # D_시가등락율 = (시가-전일종가)/전일종가*100 = 0
    assert row["D_시가등락율"] == pytest.approx(0.0)
    # D_시가대비등락율 = (10100-10000)/10000*100 = 1.0
    assert row["D_시가대비등락율"] == pytest.approx(1.0)
    # D_총호가매수비율 = 3000/(3000+1000) = 0.75
    assert row["D_총호가매수비율"] == pytest.approx(0.75)
    # D_현재가위치 = (10100-9900)/(10200-9900)*100 = 66.67
    assert row["D_현재가위치"] == pytest.approx(66.666, rel=1e-3)
    # D_체결강도비율 = 120/100 · D_거래대금폭발배수 = 30/10 · D_누적수급비 = 3
    assert row["D_체결강도비율"] == pytest.approx(1.2)
    assert row["D_거래대금폭발배수"] == pytest.approx(3.0)
    assert row["D_누적수급비"] == pytest.approx(3.0)


def test_enrich_leaf_coordinates_match_seed_skeleton():
    ds = L.enrich(_tick_frame())
    assert list(ds.df["leaf_time"]) == ["B1_900_902", "B4_910_920"]
    assert list(ds.df["leaf_cap"]) == ["S_3000미만", "L_10000이상"]


def test_zero_variance_and_min_only_columns_are_auto_excluded():
    ds = L.enrich(_tick_frame())
    # tick 프레임에서 분당*/RSI/분봉* 은 전부 0 → zero_variance 제외.
    for col in ("B_분당거래대금", "B_RSI", "B_분봉시가"):
        assert ds.excluded.get(col) == "zero_variance", col
        assert col not in ds.features
    # 실제 변별 후보는 편입.
    assert "D_총호가매수비율" in ds.features
    assert "B_체결강도" in ds.features


def test_enrich_does_not_mutate_input():
    df = _tick_frame()
    before = df.copy(deep=True)
    L.enrich(df)
    pd.testing.assert_frame_equal(df, before)


def test_unknown_future_b_column_is_auto_included():
    df = _tick_frame()
    df["B_미래에추가된변수"] = [1.0, 2.0]
    ds = L.enrich(df)
    assert "B_미래에추가된변수" in ds.features  # 하드코딩 없음 — 헤더 주도 편입.


# ------------------------------------------------------------- ④ 리프 잔차표
def test_leaf_matrix_reports_median_and_winrate_alongside_mean():
    df = pd.concat([_tick_frame()] * 20, ignore_index=True)  # 리프당 n=20
    ds = L.enrich(df)
    rows = L.leaf_matrix(ds, min_n=30)
    assert rows, "리프 행이 나와야 한다"
    for r in rows:
        for key in ("mean_pct", "median_pct", "win_rate", "n", "reliable"):
            assert key in r, key
    # n=20 < min_n=30 → 신뢰 아님으로 정직 표기.
    assert all(r["reliable"] is False for r in rows)


def test_min_timeframe_bands_and_supply_ratio():
    df = pd.DataFrame([{
        "종목명": "C", "시가총액": 8000, "매수시간": "202504071405",
        "수익률": 0.5, "수익금": 5000,
        "B_현재가": 20200, "B_등락율": 1.0, "B_매수총잔량": 100, "B_매도총잔량": 100,
        "B_당일거래대금": 100, "B_시가총액": 8000,
        "B_분당거래대금": 40, "B_분당거래대금평균": 20,
        "B_분당매수수량": 300, "B_분당매도수량": 150,
        "B_분봉고가": 20300, "B_분봉저가": 20000,
    }, {
        "종목명": "C", "시가총액": 8000, "매수시간": "202504070915",
        "수익률": -0.5, "수익금": -5000,
        "B_현재가": 20000, "B_등락율": 1.0, "B_매수총잔량": 100, "B_매도총잔량": 300,
        "B_당일거래대금": 100, "B_시가총액": 8000,
        "B_분당거래대금": 10, "B_분당거래대금평균": 20,
        "B_분당매수수량": 100, "B_분당매도수량": 400,
        "B_분봉고가": 20300, "B_분봉저가": 20000,
    }])
    ds = L.enrich(df)
    assert ds.timeframe == "min"
    assert list(ds.df["leaf_time"]) == ["B4_오후", "B1_장초반"]
    assert ds.df.iloc[0]["D_거래대금폭발배수"] == pytest.approx(2.0)
    assert ds.df.iloc[0]["D_수급비"] == pytest.approx(2.0)
