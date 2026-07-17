"""비용식 벡터화판 — alpha_lab/dataset/labels.py 봉인식과 원소별 완전 정합.

labels.py는 스칼라 루프(krx_tick_size 밴드 한 틱씩 통과)로 net_rate를 준다.
셀 지도는 수백만 표본을 처리하므로 같은 식을 numpy로 벡터화한다. 부동소수
연산 순서를 labels.py와 동일하게 유지해 max_err=0 패리티를 보장하며,
parity_max_err()가 표본 대조로 이를 증명한다(W4-2a 비용식 게이트).
"""
from __future__ import annotations

import numpy as np

from alpha_lab.dataset import labels as _labels

# 봉인 상수는 labels.py에서 그대로 가져온다(중복 정의 금지 — 단일 출처).
FEE_RATE = _labels.FEE_RATE
TAX_RATE = _labels.TAX_RATE
ADVERSE_TICKS = _labels.ADVERSE_TICKS

# KRX 2023 개편 호가단위 밴드(slippage_stress.krx_tick_size 경계와 동일).
_BAND_EDGES = np.array([2000.0, 5000.0, 20000.0, 50000.0, 200000.0, 500000.0])
_BAND_TICKS = np.array([1.0, 5.0, 10.0, 50.0, 100.0, 500.0, 1000.0])

__all__ = [
    "adverse_fill_vec",
    "krx_tick_size_vec",
    "net_rate_vec",
    "parity_max_err",
    "tick_size_below_vec",
]


def krx_tick_size_vec(price: np.ndarray) -> np.ndarray:
    """krx_tick_size(price)의 벡터화판 — price별 호가단위(원)."""
    idx = np.searchsorted(_BAND_EDGES, np.asarray(price, dtype=np.float64),
                          side="right")
    return _BAND_TICKS[idx]


def tick_size_below_vec(price: np.ndarray) -> np.ndarray:
    """labels.tick_size_below 벡터화판 — price>1이면 krx_tick_size(price-1), 아니면 1."""
    p = np.asarray(price, dtype=np.float64)
    below = krx_tick_size_vec(p - 1.0)
    return np.where(p > 1.0, below, 1.0)


def adverse_fill_vec(buy_ref: np.ndarray, sell_ref: np.ndarray,
                     ticks: int = ADVERSE_TICKS):
    """labels.adverse_fill 벡터화 — 밴드를 한 틱씩 단계 통과(매도 0 클램프)."""
    buy = np.asarray(buy_ref, dtype=np.float64).copy()
    sell = np.asarray(sell_ref, dtype=np.float64).copy()
    for _ in range(max(int(ticks), 0)):
        buy = buy + krx_tick_size_vec(buy)
        sell = np.maximum(sell - tick_size_below_vec(sell), 0.0)
    return buy, sell


def net_rate_vec(buy_fill: np.ndarray, sell_fill: np.ndarray) -> np.ndarray:
    """labels.net_rate 벡터화 — (sell순액 - buy원가)/buy원가."""
    buy_cost = np.asarray(buy_fill, dtype=np.float64) * (1.0 + FEE_RATE)
    sell_net = np.asarray(sell_fill, dtype=np.float64) * (1.0 - TAX_RATE - FEE_RATE)
    return (sell_net - buy_cost) / buy_cost


def net_from_quotes(entry_ask: np.ndarray, exit_bid: np.ndarray) -> np.ndarray:
    """진입 매도호가1·청산 매수호가1 → tick2 불리 체결 net_rate(벡터)."""
    buy_fill, sell_fill = adverse_fill_vec(entry_ask, exit_bid)
    return net_rate_vec(buy_fill, sell_fill)


def parity_max_err(entry_ask: np.ndarray, exit_bid: np.ndarray) -> float:
    """표본 (entry_ask, exit_bid)에서 labels.py 스칼라식과의 최대 절대오차.

    W4-2a 비용식 패리티 게이트 근거 — 0.0이면 벡터화판이 봉인식과 완전 정합.
    """
    entry = np.asarray(entry_ask, dtype=np.float64)
    exit_ = np.asarray(exit_bid, dtype=np.float64)
    vec = net_from_quotes(entry, exit_)
    scalar = np.array([
        _labels.net_rate(*_labels.adverse_fill(float(a), float(b)))
        for a, b in zip(entry, exit_)
    ])
    return float(np.max(np.abs(vec - scalar))) if vec.size else 0.0
