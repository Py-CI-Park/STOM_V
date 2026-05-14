"""합성 OHLCV/틱 데이터 생성기.

Constraint: V3 분석기가 가정하는 dict_findex 키 순서와 numpy dtype을 정확히 따른다.
Constraint: 외부 데이터·실 시장 데이터 의존 0. 결정적 합성 데이터만 생성한다.
"""
from __future__ import annotations

from typing import Mapping

import numpy as np


def build_min_array(
    dict_findex: Mapping[str, int],
    *,
    n: int = 200,
    seed: int = 42,
    base_price: float = 50000.0,
) -> np.ndarray:
    """분봉 합성 데이터 생성.

    V3 분봉 분석기가 호출하는 핵심 컬럼만 채우고 나머지는 0으로 둔다.
    drift 발생 시 fail이 분명하도록 결정적 시드를 강제한다.
    """
    rng = np.random.default_rng(seed)
    width = max(dict_findex.values()) + 1
    arr = np.zeros((n, width), dtype=np.float64)

    walk = np.cumsum(rng.normal(0.0, base_price * 0.001, n))
    close = base_price + walk
    high = close + np.abs(rng.normal(0.0, base_price * 0.0008, n))
    low = close - np.abs(rng.normal(0.0, base_price * 0.0008, n))
    op = (high + low) / 2.0
    volume = rng.integers(100_000, 1_000_000, n).astype(np.float64)

    arr[:, dict_findex["index"]] = np.arange(n)
    arr[:, dict_findex["현재가"]] = close
    arr[:, dict_findex["시가"]] = op
    arr[:, dict_findex["고가"]] = high
    arr[:, dict_findex["저가"]] = low
    arr[:, dict_findex["등락율"]] = (close - close[0]) / close[0] * 100.0
    arr[:, dict_findex["당일거래대금"]] = volume * close
    arr[:, dict_findex["체결강도"]] = 100.0 + rng.normal(0.0, 5.0, n)
    arr[:, dict_findex["분당매수수량"]] = volume / 2
    arr[:, dict_findex["분당매도수량"]] = volume / 2
    arr[:, dict_findex["분봉시가"]] = op
    arr[:, dict_findex["분봉고가"]] = high
    arr[:, dict_findex["분봉저가"]] = low
    arr[:, dict_findex["분당거래대금"]] = volume * close
    arr[:, dict_findex["고저평균대비등락율"]] = (close - (high + low) / 2.0) / close * 100.0
    arr[:, dict_findex["최고현재가"]] = np.maximum.accumulate(close)
    arr[:, dict_findex["최저현재가"]] = np.minimum.accumulate(close)
    arr[:, dict_findex["체결강도평균"]] = arr[:, dict_findex["체결강도"]].cumsum() / np.arange(1, n + 1)
    arr[:, dict_findex["등락율각도"]] = rng.normal(0.0, 1.0, n)
    return arr


def build_tick_array(
    dict_findex: Mapping[str, int],
    *,
    n: int = 1800,
    seed: int = 42,
    base_price: float = 50000.0,
) -> np.ndarray:
    """틱(초봉) 합성 데이터 생성. 1800 = 30분 분량 1초 스냅샷."""
    rng = np.random.default_rng(seed)
    width = max(dict_findex.values()) + 1
    arr = np.zeros((n, width), dtype=np.float64)

    walk = np.cumsum(rng.normal(0.0, base_price * 0.0002, n))
    close = base_price + walk
    op = close - rng.normal(0.0, base_price * 0.00005, n)
    high = close + np.abs(rng.normal(0.0, base_price * 0.0001, n))
    low = close - np.abs(rng.normal(0.0, base_price * 0.0001, n))
    volume = rng.integers(100, 5_000, n).astype(np.float64)

    arr[:, dict_findex["index"]] = np.arange(n)
    arr[:, dict_findex["현재가"]] = close
    arr[:, dict_findex["시가"]] = op
    arr[:, dict_findex["고가"]] = high
    arr[:, dict_findex["저가"]] = low
    arr[:, dict_findex["등락율"]] = (close - close[0]) / close[0] * 100.0
    arr[:, dict_findex["당일거래대금"]] = volume * close
    arr[:, dict_findex["체결강도"]] = 100.0 + rng.normal(0.0, 5.0, n)
    arr[:, dict_findex["초당매수수량"]] = volume / 2
    arr[:, dict_findex["초당매도수량"]] = volume / 2
    arr[:, dict_findex["초당거래대금"]] = volume * close
    arr[:, dict_findex["고저평균대비등락율"]] = (close - (high + low) / 2.0) / close * 100.0
    arr[:, dict_findex["최고현재가"]] = np.maximum.accumulate(close)
    arr[:, dict_findex["최저현재가"]] = np.minimum.accumulate(close)
    arr[:, dict_findex["체결강도평균"]] = arr[:, dict_findex["체결강도"]].cumsum() / np.arange(1, n + 1)
    arr[:, dict_findex["등락율각도"]] = rng.normal(0.0, 1.0, n)
    return arr
