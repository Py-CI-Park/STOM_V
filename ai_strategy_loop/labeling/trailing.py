"""트레일링 실현값 계산 (라벨 v4) — 청산 축을 근사에서 정확으로 올린다.

배경(W3 재현 게이트 FAIL): 라벨 v3 는 경로를 **요약**만 담아서(구간 최고/최저·
최초 도달·지평 수익률) 트레일링을 하한/상한으로만 잴 수 있었다. 그 격차가 커서
챔피언 재현 게이트가 판정 불가로 멈췄다 — 여지(천장 +2.6%)는 보이는데 실현
가능한 값이 0 이었다.

이 모듈은 라벨 공장이 이미 들고 있는 **가격 경로**로 트레일링 청산을 그대로
시뮬레이션해 실현 수익률을 기록한다. 근사가 아니라 계산이다.

## 규칙 정의 (엔진과 같은 체결 모델)
  진입: 매도호가1 매수 (ask[p])
  청산: 매수호가1 매도 (bid[t])
  수익률(%) = (bid[t]*(1-COST_OUT)) / (ask[p]*(1+COST_IN)) - 1, ×100

  무장: 진입 후 실현 가능 수익률의 **러닝 최고**가 arm 이상이 된 순간
  청산: 무장 후 러닝 최고 대비 give(%p) 이상 되돌린 **첫** 순간의 수익률
  미청산: 지평 h 까지 조건이 안 오면 그 시점 수익률(만기)

러닝 최고는 **그 시점까지의 최고**다 — 구간 최종 최고점이 아니다. 이 구분이
v3 근사가 미래를 참조하던 지점이었다.
"""

from __future__ import annotations

import numpy as np
from numba import njit

from ai_strategy_loop.labeling import label_spec as spec

#: 사전 고정 트레일링 격자 (arm%, give%p). 사후에 고르면 그 자체가 편의다.
TRAILING_GRID: tuple[tuple[float, float], ...] = (
    (1.0, 0.5), (1.5, 0.5), (2.0, 1.0), (3.0, 1.0), (3.0, 1.5), (5.0, 2.0),
)


@njit(cache=True)
def _trailing_kernel(bid, ask, entry_pos, horizon, arm, give, stale_ok):
    """진입별 트레일링 실현 수익률(%). 미체결 구간은 NaN.

    O(진입 × 지평). numba 로 컴파일돼 355일 × 21k 진입도 초 단위로 끝난다.
    """
    n = entry_pos.shape[0]
    out = np.empty(n, dtype=np.float64)
    exit_at = np.empty(n, dtype=np.int64)
    end = bid.shape[0] - 1

    for i in range(n):
        p = entry_pos[i]
        buy = ask[p]
        if buy <= 0.0 or not np.isfinite(buy):
            out[i] = np.nan
            exit_at[i] = -1
            continue
        denom = buy * (1.0 + spec.COST_IN)
        scale = (1.0 - spec.COST_OUT) / denom
        peak = -1.0e18
        last = np.nan
        chosen = np.nan
        chosen_at = -1
        armed = False
        for step in range(1, horizon + 1):
            t = p + step
            if t > end:
                break
            if stale_ok[t] == 0:
                continue
            b = bid[t]
            if b <= 0.0 or not np.isfinite(b):
                continue
            ret = (b * scale - 1.0) * 100.0
            last = ret
            if ret > peak:
                peak = ret
            if not armed and peak >= arm:
                armed = True
            if armed and (peak - ret) >= give:
                chosen = ret
                chosen_at = step
                break
        if chosen_at >= 0:
            out[i] = chosen
            exit_at[i] = chosen_at
        else:
            # 되돌림이 오지 않았다 → 만기 청산(마지막 유효 호가).
            out[i] = last
            exit_at[i] = horizon
    return out, exit_at


def trailing_columns(
    *,
    bid: np.ndarray,
    ask: np.ndarray,
    entry_pos: np.ndarray,
    horizon: int,
    stale_ok: np.ndarray,
    grid: tuple[tuple[float, float], ...] = TRAILING_GRID,
) -> dict[str, np.ndarray]:
    """사전 고정 격자 전셀의 실현 수익률·청산 시각 열을 만든다.

    Returns:
        {"trail_1.0_0.5": 수익률(%), "trailt_1.0_0.5": 청산 경과(단위), ...}
    """
    bid = np.ascontiguousarray(bid, dtype=np.float64)
    ask = np.ascontiguousarray(ask, dtype=np.float64)
    entry_pos = np.ascontiguousarray(entry_pos, dtype=np.int64)
    stale_ok = np.ascontiguousarray(stale_ok, dtype=np.int8)

    out: dict[str, np.ndarray] = {}
    for arm, give in grid:
        values, exits = _trailing_kernel(
            bid, ask, entry_pos, int(horizon), float(arm), float(give), stale_ok,
        )
        out[f"trail_{arm:g}_{give:g}"] = values
        out[f"trailt_{arm:g}_{give:g}"] = exits.astype(np.int32)
    return out
