"""연도 키 세율 비용식 — V2-A §1 교정 세율을 v1 비용 모형에 주입.

v1 비용식(labels.net_rate / costs.net_from_quotes)은 매도세 0.18% 고정이다.
V2-A는 세금만 연도 키로 교정하고(수수료·불리체결·호가단위 밴드는 봉인 유지)
나머지 식·연산 순서를 v1과 동일하게 둔다. 세율의 유일 출처는 config_v2.
YEAR_TAX_RATE 뿐이며, h300 라벨 경로와 L3 라벨 경로가 모두 여기를 거친다
(지점 간 세율 패리티의 구현 보증).

정합 증거: tax=0.0018 을 넘기면 v1 net_rate 와 원소별 완전 일치(reduce-to-v1),
세율만 바뀌면 균일 %p 이동(parity_max_err_year 0.0). 호가단위 밴드 단계 통과
(adverse_fill)는 v1 벡터판(costs.adverse_fill_vec)을 그대로 재사용한다.
"""
from __future__ import annotations

import numpy as np

from alpha_lab.dataset import labels as _labels
from alpha_lab.stats_map import config_v2, costs as _costs_v1

# 수수료는 키움 실측 봉인 유지(세금만 연도 교정 대상).
FEE_RATE = _labels.FEE_RATE
ADVERSE_TICKS = _labels.ADVERSE_TICKS

__all__ = [
    "adverse_fill_year",
    "net_from_quotes_year",
    "net_rate_year",
    "net_rate_year_vec",
    "parity_max_err_year",
]


def net_rate_year(buy_fill: float, sell_fill: float, tax: float) -> float:
    """연도 세율 tax 를 적용한 순수익률(스칼라) — v1 net_rate 의 세율 일반화.

    net = (sell×(1-tax-fee) - buy×(1+fee)) / (buy×(1+fee)).
    tax=0.0018 이면 labels.net_rate 와 완전 일치(reduce-to-v1).
    """
    buy_cost = float(buy_fill) * (1.0 + FEE_RATE)
    sell_net = float(sell_fill) * (1.0 - float(tax) - FEE_RATE)
    return (sell_net - buy_cost) / buy_cost


def net_rate_year_vec(buy_fill: np.ndarray, sell_fill: np.ndarray,
                      tax: float) -> np.ndarray:
    """net_rate_year 의 벡터판 — 연산 순서를 스칼라와 동일하게 둔다."""
    buy_cost = np.asarray(buy_fill, dtype=np.float64) * (1.0 + FEE_RATE)
    sell_net = np.asarray(sell_fill, dtype=np.float64) * (1.0 - float(tax) - FEE_RATE)
    return (sell_net - buy_cost) / buy_cost


def adverse_fill_year(entry_ask: np.ndarray, exit_bid: np.ndarray):
    """진입 +2틱·청산 -2틱 불리 체결가(벡터) — v1 밴드 로직 재사용."""
    return _costs_v1.adverse_fill_vec(entry_ask, exit_bid)


def net_from_quotes_year(entry_ask: np.ndarray, exit_bid: np.ndarray,
                         year: int) -> np.ndarray:
    """진입 매도호가1·청산 매수호가1 → 연도 세율 tick2 불리 net_rate(벡터).

    세율은 config_v2.year_tax_rate(year) 단일 출처에서만 온다.
    """
    tax = config_v2.year_tax_rate(year)
    buy_fill, sell_fill = adverse_fill_year(entry_ask, exit_bid)
    return net_rate_year_vec(buy_fill, sell_fill, tax)


def parity_max_err_year(entry_ask: np.ndarray, exit_bid: np.ndarray,
                        year: int) -> float:
    """표본 (entry_ask, exit_bid, year)에서 스칼라 vs 벡터 net 최대 절대오차.

    0.0 이면 벡터판이 스칼라식과 원소별 완전 정합(세율 패리티 게이트 근거).
    """
    entry = np.asarray(entry_ask, dtype=np.float64)
    exit_ = np.asarray(exit_bid, dtype=np.float64)
    tax = config_v2.year_tax_rate(year)
    vec = net_from_quotes_year(entry, exit_, year)
    scalar = np.array([
        net_rate_year(*_labels.adverse_fill(float(a), float(b)), tax)
        for a, b in zip(entry, exit_)
    ])
    return float(np.max(np.abs(vec - scalar))) if vec.size else 0.0
