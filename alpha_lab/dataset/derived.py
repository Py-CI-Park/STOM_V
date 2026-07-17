"""alpha_lab.dataset.derived — 엔진 파생 18항 미러 재계산기 (stock tick 전용).

원천 코드 실측 정독 결과의 미러다(추정 금지 규율):
- 컬럼 정의: utility/setting_base.py:155-166 ``list_stock_tick[54:72]``.
  일 DB 저장은 54컬럼(index~관심종목)이고, 엔진이 로딩 시
  add_rolling_data로 뒤에 18컬럼을 재계산해 붙여 총 72열 배열을 만든다
  (backtest/backengine_base.py:351-366 DataLoad → np.array 72열 실측).
- 재계산 로직: utility/static.py:78-132 ``add_rolling_data(df, market,
  is_tick, avg_list)`` — 본 모듈은 market=1(주식)·is_tick=True 프로파일만
  미러한다.
- 이동평균 윈도우: utility/static.py:74-75 ``get_ema_list(True)`` ==
  (60, 150, 300, 600, 1200).
- 각도 계수: utility/static.py:571-590 ``get_angle_cf`` —
  get_angle_cf(1, True, 0) == 5(등락율각도), get_angle_cf(1, True, 1) ==
  0.01(당일거래대금각도). 전일비각도는 계수 없음(static.py:125-129).
- avg 동결값: 공식 프로파일 bt_avg_time=30
  (.omo/evidence/claude-condition-research-20260610/train-config.json) →
  cli/runner.py:33-39 ``_normalize_avg_list`` → avg_list=[30].

사전등록 표기와의 정합 주의: preregistration_v3.json feature_space_v3는
'derived_19'로 표기하나 엔진이 stock tick에서 추가하는 컬럼은 실측 18개다
(np.array 72열 - 저장 54열 = 18). 본 모듈은 실측 18항 전부를 미러하며,
불일치는 v3_feature_annex.json method에 기록한다.

엔진과 의도적으로 다른 점(값은 동일):
- 엔진은 전달받은 df를 제자리 변형하지만, 본 모듈은 입력을 변형하지 않고
  파생 18열만 담은 새 DataFrame을 반환한다(불변성 규율).
- 엔진 컬럼명은 avg 접미사형(예: '최고현재가30')이나 본 모듈은
  list_stock_tick 정식명('최고현재가')을 쓴다 — 위치·값 1:1
  (ENGINE_COLUMN_MAP 참조).
- 엔진은 마지막에 np.nan_to_num(utility/static.py:131-132)로 워밍업 NaN을
  0.0으로 만든다 — ``nan_to_num=True``(기본)가 같은 값을 재현한다.

멀티데이 주의: 공식 CLI 기본 divid_mode='종목코드별 분류'
(cli/config.py:34)에서는 여러 날이 한 query로 붙어 rolling이 일 경계를
넘는다(backtest/backengine_base.py:352-359). 본 모듈은 받은 df 그대로
계산하므로, 일 경계 처리(단일일/멀티데이)는 호출측이 엔진과 같은 방식으로
df를 구성해 결정한다.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

__all__ = [
    "ANGLE_CF_AMOUNT",
    "ANGLE_CF_RATE",
    "AVG_WINDOW_FROZEN",
    "DERIVED_TICK_FEATURES",
    "ENGINE_COLUMN_MAP",
    "FORMULA_REFS",
    "SOURCE_COLUMNS",
    "TICK_MA_WINDOWS",
    "angle",
    "compute_derived_tick",
    "engine_column_name",
    "moving_average",
    "rolling_max",
    "rolling_mean_round",
    "rolling_min",
    "rolling_sum",
]

logger = logging.getLogger(__name__)

# utility/static.py:74-75 get_ema_list(is_tick=True) 동결값.
TICK_MA_WINDOWS: Tuple[int, ...] = (60, 150, 300, 600, 1200)

# 공식 프로파일 bt_avg_time=30 → cli/runner.py:33-39 → avg_list=[30] 동결.
AVG_WINDOW_FROZEN: int = 30

# utility/static.py:571-590 get_angle_cf(1, True, 0)/(1, True, 1) 동결값.
ANGLE_CF_RATE: float = 5.0
ANGLE_CF_AMOUNT: float = 0.01

# utility/setting_base.py:163-165 list_stock_tick[54:72] — 순서 봉인(18항).
DERIVED_TICK_FEATURES: Tuple[str, ...] = (
    "이동평균60",
    "이동평균150",
    "이동평균300",
    "이동평균600",
    "이동평균1200",
    "최고현재가",
    "최저현재가",
    "체결강도평균",
    "최고체결강도",
    "최저체결강도",
    "최고초당매수수량",
    "최고초당매도수량",
    "누적초당매수수량",
    "누적초당매도수량",
    "초당거래대금평균",
    "등락율각도",
    "당일거래대금각도",
    "전일비각도",
)

# 파생 18항 계산에 필요한 저장 컬럼(utility/static.py:78-129에서 참조하는 원천).
SOURCE_COLUMNS: Tuple[str, ...] = (
    "현재가",
    "체결강도",
    "초당매수수량",
    "초당매도수량",
    "초당거래대금",
    "등락율",
    "당일거래대금",
    "전일비",
)

# 피처별 엔진 원천 코드 참조(annex formula_ref로 재사용).
FORMULA_REFS: Dict[str, str] = {
    "이동평균60": "utility/static.py:79-80 현재가.rolling(60).mean().round(3)",
    "이동평균150": "utility/static.py:79-80 현재가.rolling(150).mean().round(3)",
    "이동평균300": "utility/static.py:79-80 현재가.rolling(300).mean().round(3)",
    "이동평균600": "utility/static.py:79-80 현재가.rolling(600).mean().round(3)",
    "이동평균1200": "utility/static.py:79-80 현재가.rolling(1200).mean().round(3)",
    "최고현재가": "utility/static.py:83-84 현재가.rolling(30).max() [엔진명 최고현재가30]",
    "최저현재가": "utility/static.py:83-85 현재가.rolling(30).min() [엔진명 최저현재가30]",
    "체결강도평균": "utility/static.py:91-92 체결강도.rolling(30).mean().round(3) [엔진명 체결강도평균30]",
    "최고체결강도": "utility/static.py:91-93 체결강도.rolling(30).max() [엔진명 최고체결강도30]",
    "최저체결강도": "utility/static.py:91-94 체결강도.rolling(30).min() [엔진명 최저체결강도30]",
    "최고초당매수수량": "utility/static.py:96-99 초당매수수량.rolling(30).max() [엔진명 최고초당매수수량30]",
    "최고초당매도수량": "utility/static.py:96-100 초당매도수량.rolling(30).max() [엔진명 최고초당매도수량30]",
    "누적초당매수수량": "utility/static.py:97-101 초당매수수량.rolling(30).sum() [엔진명 누적초당매수수량30]",
    "누적초당매도수량": "utility/static.py:98-102 초당매도수량.rolling(30).sum() [엔진명 누적초당매도수량30]",
    "초당거래대금평균": "utility/static.py:103 초당거래대금.rolling(30).mean().round(0) [엔진명 초당거래대금평균30]",
    "등락율각도": (
        "utility/static.py:117-122 round(arctan2((등락율-등락율.shift(29))*5, 30)"
        "/(2*pi)*360, 2) — cf1=get_angle_cf(1,True,0)=5"
    ),
    "당일거래대금각도": (
        "utility/static.py:117-123 round(arctan2((당일거래대금-당일거래대금.shift(29))*0.01, 30)"
        "/(2*pi)*360, 2) — cf2=get_angle_cf(1,True,1)=0.01"
    ),
    "전일비각도": (
        "utility/static.py:125-129 round(arctan2(전일비-전일비.shift(29), 30)"
        "/(2*pi)*360, 2) — 계수 미적용"
    ),
}

# 이동평균·각도 3종은 엔진도 접미사 없는 정식명을 그대로 쓴다
# (utility/static.py:80,122,123,129). 나머지 13종은 f'{정식명}{avg}'.
_UNSUFFIXED = frozenset(
    ("이동평균60", "이동평균150", "이동평균300", "이동평균600", "이동평균1200",
     "등락율각도", "당일거래대금각도", "전일비각도")
)


def engine_column_name(name: str, avg: int = AVG_WINDOW_FROZEN) -> str:
    """정식명(list_stock_tick) → add_rolling_data가 df에 붙이는 실제 컬럼명."""
    if name not in DERIVED_TICK_FEATURES:
        raise ValueError(f"파생 18항이 아님: {name!r}")
    return name if name in _UNSUFFIXED else f"{name}{int(avg)}"


# avg=30 기준 정식명 → 엔진명 전체 맵(참조·패리티용).
ENGINE_COLUMN_MAP: Dict[str, str] = {
    name: engine_column_name(name) for name in DERIVED_TICK_FEATURES
}


def moving_average(price: pd.Series, window: int, market: int = 1) -> pd.Series:
    """utility/static.py:79-80 — 현재가.rolling(window).mean().round(3 if market==1 else 8).

    min_periods 미지정(=window)이므로 앞 window-1행은 NaN — 엔진과 동일.
    """
    return price.rolling(window=int(window)).mean().round(3 if market == 1 else 8)


def rolling_max(series: pd.Series, window: int) -> pd.Series:
    """utility/static.py:83-84,93,99-100 — series.rolling(window).max()."""
    return series.rolling(window=int(window)).max()


def rolling_min(series: pd.Series, window: int) -> pd.Series:
    """utility/static.py:85,94 — series.rolling(window).min()."""
    return series.rolling(window=int(window)).min()


def rolling_sum(series: pd.Series, window: int) -> pd.Series:
    """utility/static.py:101-102 — series.rolling(window).sum() (누적초당매수/매도수량)."""
    return series.rolling(window=int(window)).sum()


def rolling_mean_round(series: pd.Series, window: int, digits: int) -> pd.Series:
    """utility/static.py:92(체결강도평균 round 3)·103(초당거래대금평균 round 0) 미러."""
    return series.rolling(window=int(window)).mean().round(int(digits))


def angle(series: pd.Series, avg: int, cf: Optional[float]) -> pd.Series:
    """utility/static.py:117-129 각도 공식 미러.

    엔진 식(원문 순서 그대로 — 부동소수 연산 순서 보존):
        차이 = series - series.shift(avg - 1)
        round(np.arctan2(차이 * cf, avg) / (2 * np.pi) * 360, 2)
    전일비각도(static.py:129)는 cf 곱이 없으므로 cf=None으로 호출한다.
    앞 avg-1행은 shift NaN → arctan2 NaN → 엔진 nan_to_num 단계에서 0.0.
    """
    window = int(avg)
    diff = series - series.shift(window - 1)
    if cf is not None:
        diff = diff * cf
    radians = np.arctan2(diff, window)
    return round(radians / (2 * np.pi) * 360, 2)


def _require_columns(df: pd.DataFrame, names: Tuple[str, ...]) -> None:
    missing = [name for name in names if name not in df.columns]
    if missing:
        raise ValueError(f"파생 재계산에 필요한 저장 컬럼 누락: {missing}")


def compute_derived_tick(
    df: pd.DataFrame,
    avg: int = AVG_WINDOW_FROZEN,
    *,
    nan_to_num: bool = True,
) -> pd.DataFrame:
    """저장 54컬럼(부분집합 가능) df에서 파생 18항을 엔진 순서로 재계산한다.

    utility/static.py:78-132 add_rolling_data(df, market=1, is_tick=True,
    avg_list=[avg])가 뒤에 붙이는 18컬럼과 위치·값이 1:1인 새 DataFrame을
    반환한다(입력 df는 변형하지 않는다). nan_to_num=True(기본)이면 엔진의
    최종 np.nan_to_num(utility/static.py:132)을 미러해 워밍업 NaN을 0.0으로
    바꾼다. False이면 NaN을 보존한다(진단용).

    Args:
        df: SOURCE_COLUMNS를 포함한 종목-일(또는 엔진과 동일 구성) tick 행렬.
        avg: 엔진 avg_list의 단일 원소 — 공식 동결값 30.
        nan_to_num: 엔진 배열 의미론(NaN→0.0) 재현 여부.
    """
    if int(avg) < 1:
        raise ValueError(f"avg는 1 이상이어야 합니다: {avg!r}")
    _require_columns(df, SOURCE_COLUMNS)
    window = int(avg)

    out: Dict[str, pd.Series] = {}
    # utility/static.py:79-80 — 이동평균 5종(윈도우는 get_ema_list 동결값).
    for ma_window in TICK_MA_WINDOWS:
        out[f"이동평균{ma_window}"] = moving_average(df["현재가"], ma_window)
    # utility/static.py:83-85 — 현재가 rolling max/min.
    out["최고현재가"] = rolling_max(df["현재가"], window)
    out["최저현재가"] = rolling_min(df["현재가"], window)
    # utility/static.py:91-94 — 체결강도 mean(round 3)/max/min.
    out["체결강도평균"] = rolling_mean_round(df["체결강도"], window, 3)
    out["최고체결강도"] = rolling_max(df["체결강도"], window)
    out["최저체결강도"] = rolling_min(df["체결강도"], window)
    # utility/static.py:96-102 — 초당매수/매도수량 max·sum.
    out["최고초당매수수량"] = rolling_max(df["초당매수수량"], window)
    out["최고초당매도수량"] = rolling_max(df["초당매도수량"], window)
    out["누적초당매수수량"] = rolling_sum(df["초당매수수량"], window)
    out["누적초당매도수량"] = rolling_sum(df["초당매도수량"], window)
    # utility/static.py:103 — 초당거래대금 mean(round 0).
    out["초당거래대금평균"] = rolling_mean_round(df["초당거래대금"], window, 0)
    # utility/static.py:117-129 — 각도 3종(cf는 get_angle_cf 동결값).
    out["등락율각도"] = angle(df["등락율"], window, ANGLE_CF_RATE)
    out["당일거래대금각도"] = angle(df["당일거래대금"], window, ANGLE_CF_AMOUNT)
    out["전일비각도"] = angle(df["전일비"], window, None)

    frame = pd.DataFrame(out, index=df.index)
    # 삽입 순서 == add_rolling_data 추가 순서 == list_stock_tick[54:72] 검증.
    expected = [f"이동평균{w}" for w in TICK_MA_WINDOWS] + [
        name for name in DERIVED_TICK_FEATURES if not name.startswith("이동평균")
    ]
    if list(frame.columns) != expected or tuple(expected) != DERIVED_TICK_FEATURES:
        raise RuntimeError("파생 18항 컬럼 순서 불변식 위반 — 소스 확인 필요")
    if nan_to_num:
        # utility/static.py:131-132 — np.nan_to_num(np.array(df)) 미러
        # (파생 18열에 대한 원소별 동일 변환).
        values = np.nan_to_num(frame.to_numpy(dtype="float64"))
        frame = pd.DataFrame(
            values, columns=list(DERIVED_TICK_FEATURES), index=df.index
        )
    logger.debug(
        "compute_derived_tick: rows=%d avg=%d nan_to_num=%s",
        len(frame), window, nan_to_num,
    )
    return frame
