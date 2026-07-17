"""라벨 함수 + 비용 모형 — ai_strategy_loop/fitness/slippage_profiles.py 정합.

정합 방식:
- ``krx_tick_size`` 는 원본의 공개 심볼(__all__ 등재)을 그대로 재사용한다
  (2023년 개편 KRX 코스피/코스닥 공통 호가단위 — 정의는 fitness/slippage_stress.py).
- ``_tick_size_below``/``_adverse_fill_prices`` 는 원본의 사설 심볼이라 동일
  로직을 재구현했다(밴드 한 틱씩 단계 통과 — 예: 매수 1999 +2틱 = 2005,
  선형 1999+2×1=2001 아님. 매도는 0 바닥 클램프).
  tests/unit/test_alpha_dataset.py 에서 원본 함수와의 대조 테스트로 봉인.
- 수수료/세금 상수는 원본 실측 상수(_KIWOOM_FEE_RATE/_KIWOOM_TAX_RATE)와 동일.

라벨 규약(봉인):
- L1: entry(t0+1초 매도호가1) 매수 / exit(t0+h초 매수호가1) 매도, 양측 tick2
  불리 체결 + 수수료·세금 차감 net_rate ≥ +1% → 1.
- L2 트리플배리어: TP +3% / SL -2% / 300초 timeout, t0+1 이후 관측 초들의
  매수호가1 경로 net_rate로 first-touch. 동시 터치 → SL 우선(보수). timeout → 0.
"""
from __future__ import annotations

from typing import Sequence, Tuple

# 공개 심볼 재사용 — 호가단위 로직 원본 단일 출처 유지(중복 정의 금지).
from ai_strategy_loop.fitness.slippage_profiles import krx_tick_size

__all__ = [
    "ADVERSE_TICKS",
    "FEE_RATE",
    "L1_NET_THRESHOLD",
    "SL_RATE",
    "TAX_RATE",
    "TIMEOUT_SEC",
    "TP_RATE",
    "adverse_fill",
    "krx_tick_size",
    "l1_label",
    "l2_triple_barrier",
    "net_rate",
    "tick_size_below",
]

# 비용 상수 — slippage_profiles.py의 _KIWOOM_FEE_RATE/_KIWOOM_TAX_RATE 실측치.
FEE_RATE = 0.00015   # 매수/매도 각각의 수수료율.
TAX_RATE = 0.0018    # 매도금액 기준 거래세.
ADVERSE_TICKS = 2    # tick2 불리 체결(진입 +2틱, 매도 -2틱).

L1_NET_THRESHOLD = 0.01  # L1 양성 판정: net_rate >= +1%.
TP_RATE = 0.03           # L2 take-profit 배리어(net_rate 기준).
SL_RATE = -0.02          # L2 stop-loss 배리어(net_rate 기준).
TIMEOUT_SEC = 300        # L2 타임아웃(초).


def tick_size_below(price: float) -> float:
    """가격 바로 아래 호가의 단위(원). 밴드 경계에서는 하단 밴드 단위를 쓴다.

    slippage_profiles._tick_size_below 미러(사설 심볼 재구현 — 대조 테스트 봉인).
    """
    return krx_tick_size(price - 1.0) if price > 1.0 else 1.0


def adverse_fill(
    buy_ref: float, sell_ref: float, ticks: int = ADVERSE_TICKS
) -> Tuple[float, float]:
    """진입 +N틱·매도 -N틱 불리 체결가 (buy_fill, sell_fill).

    slippage_profiles._adverse_fill_prices 미러: 호가단위 밴드를 한 틱씩
    단계 통과(step)하며 계산하고, 매도 체결가는 0 밑으로 내려가지 않는다.
    """
    buy = float(buy_ref)
    sell = float(sell_ref)
    for _ in range(max(int(ticks), 0)):
        buy += krx_tick_size(buy)
        sell = max(sell - tick_size_below(sell), 0.0)
    return buy, sell


def net_rate(buy_fill: float, sell_fill: float) -> float:
    """수수료·세금 차감 순수익률 = 순스프레드 / 매수원가.

    net_rate = (sell×(1-세금-수수료) - buy×(1+수수료)) / (buy×(1+수수료)).
    분자는 slippage_profiles._net_spread와 동일식(키움 순손익 모델).
    """
    buy_cost = float(buy_fill) * (1.0 + FEE_RATE)
    sell_net = float(sell_fill) * (1.0 - TAX_RATE - FEE_RATE)
    return (sell_net - buy_cost) / buy_cost


def l1_label(entry_ask: float, exit_bid: float) -> int:
    """고정 지평 라벨: tick2 불리 체결 net_rate ≥ +1% 이면 1, 아니면 0."""
    buy_fill, sell_fill = adverse_fill(entry_ask, exit_bid)
    return int(net_rate(buy_fill, sell_fill) >= L1_NET_THRESHOLD)


def l2_triple_barrier(
    entry_ask: float,
    path: Sequence[Tuple[int, float]],
    tp: float = TP_RATE,
    sl: float = SL_RATE,
    timeout_sec: int = TIMEOUT_SEC,
) -> int:
    """트리플배리어 라벨 {1, -1, 0} — first-touch, 동시 터치는 SL 우선(보수).

    Args:
        entry_ask: t0+1초 매도호가1(진입 기준가 — +2틱 불리 매수 체결).
        path: (sec_offset, 매수호가1) 오름차순 목록. sec_offset은 t0 기준 초
            오프셋이며 관측된 초만 담는다(결측 초는 항목 없음).
        tp/sl: net_rate 기준 배리어. timeout_sec: 이 오프셋 초과 항목은 무시.

    Returns:
        SL 먼저 터치 -1, TP 먼저 터치 +1, timeout(미터치) 0.
    """
    for sec_offset, bid in path:
        if sec_offset > timeout_sec:
            break
        buy_fill, sell_fill = adverse_fill(entry_ask, bid)
        rate = net_rate(buy_fill, sell_fill)
        if rate <= sl:
            return -1
        if rate >= tp:
            return 1
    return 0
