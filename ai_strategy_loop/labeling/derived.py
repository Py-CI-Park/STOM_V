"""QSP11 — 파생 특징(변화율·비율·누적·직전 대비).

QSP10 근본 원인: 지도의 68열이 전부 **현재 값(level)** 이었고, 흑자가 증명된 902/905 가
쓰는 **변화율 계열**이 하나도 없었다. 이 모듈이 그 재료를 채운다.

정의는 추측이 아니라 **엔진 정답지에서 역산**했다(2026-08-06, 와이드 기준선 CSV 의
`B_*` 기록값 대조 — 3일 표본):

| 특징 | 확정 정의 | 일치율 |
|---|---|---|
| `체결강도평균(n)` | 최근 n틱 평균 | **100%** |
| `누적초당매수/매도수량(n)` | 최근 n틱 합 | **100%** |
| `초당거래대금평균(n)` | **round**(최근 n틱 평균) — 엔진이 반올림한다 | **100%** |
| `등락율각도(n)` | `deg(atan((r[t] − r[t−n]) / n × 5))` | **100%** |
| `당일거래대금각도(n)` | 미확정 — 제외(후보 생성에 쓰지 않는다) | — |

엔진 기본 창(`평균값계산틱수`)은 **60**으로 실측됐다.
"""

from __future__ import annotations

from typing import Final

import numpy as np
import pandas as pd

#: 엔진 기본 평균값계산틱수(실측). 902/905 는 30 도 함께 쓰므로 둘 다 만든다.
WINDOWS: Final = (30, 60)
ANGLE_SCALE: Final = 5.0     # 역산으로 확정된 각도 스케일


def _rolling(series: pd.Series, window: int, how: str) -> np.ndarray:
    rolled = series.rolling(window, min_periods=window)
    result = rolled.mean() if how == "mean" else rolled.sum()
    return result.to_numpy()


def angle(series: pd.Series, window: int) -> np.ndarray:
    """엔진 `등락율각도(n)` 재현 — 창 양 끝 차이의 기울기를 각도로."""
    diff = series.to_numpy() - series.shift(window).to_numpy()
    with np.errstate(invalid="ignore"):
        return np.degrees(np.arctan(diff / window * ANGLE_SCALE))


def build(frame: pd.DataFrame, *, flow_prefix: str = "초당") -> dict[str, np.ndarray]:
    """종목 하나의 시계열(시간순 정렬) → 파생 특징 사전.

    frame 은 **한 종목의 관측 행**이어야 한다(종목이 섞이면 창이 오염된다).
    """
    features: dict[str, np.ndarray] = {}
    flow_value = f"{flow_prefix}거래대금"
    buy_qty, sell_qty = f"{flow_prefix}매수수량", f"{flow_prefix}매도수량"

    for window in WINDOWS:
        # 급증 비율 — 902/905 의 핵심 신호(`초당거래대금 / 초당거래대금평균(30) > 3.0`).
        mean_value = np.round(_rolling(frame[flow_value], window, "mean"))
        with np.errstate(divide="ignore", invalid="ignore"):
            features[f"{flow_value}배율_{window}"] = np.where(
                mean_value > 0, frame[flow_value].to_numpy() / mean_value, np.nan)
        features[f"체결강도평균_{window}"] = _rolling(frame["체결강도"], window, "mean")
        features[f"등락율각도_{window}"] = angle(frame["등락율"], window)

        # 누적 흐름 비교 — `누적초당매수수량(30) vs 누적초당매도수량(30)`.
        cum_buy = _rolling(frame[buy_qty], window, "sum")
        cum_sell = _rolling(frame[sell_qty], window, "sum")
        with np.errstate(divide="ignore", invalid="ignore"):
            features[f"누적매수매도비_{window}"] = np.where(cum_sell > 0, cum_buy / cum_sell, np.nan)

    # 직전 대비 변화 — `초당거래대금 > 초당거래대금N(1)`.
    previous = frame[flow_value].shift(1).to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        features[f"{flow_value}직전비"] = np.where(
            previous > 0, frame[flow_value].to_numpy() / previous, np.nan)

    # 흐름/호가 비율 — `초당매수수량 > 매도총잔량 × 0.20`.
    ask_book = frame["매도총잔량"].to_numpy(dtype=np.float64)
    bid_book = frame["매수총잔량"].to_numpy(dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        features["매수흐름_매도잔량비"] = np.where(
            ask_book > 0, frame[buy_qty].to_numpy() / ask_book, np.nan)
        features["잔량비"] = np.where(bid_book > 0, ask_book / bid_book, np.nan)
    return features


#: 파생 특징 이름(수렴·프런티어 탐색 변수 목록에 그대로 넣는다).
def feature_names(flow_prefix: str = "초당") -> list[str]:
    flow_value = f"{flow_prefix}거래대금"
    names = [f"{flow_value}직전비", "매수흐름_매도잔량비", "잔량비"]
    for window in WINDOWS:
        names += [f"{flow_value}배율_{window}", f"체결강도평균_{window}",
                  f"등락율각도_{window}", f"누적매수매도비_{window}"]
    return names
