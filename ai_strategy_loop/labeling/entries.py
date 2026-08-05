"""진입 단위 정합 — 지도의 '초'와 엔진의 '거래'를 같은 단위로 맞춘다.

**이 세션 최대의 구조적 결함(2026-08-06 실측)**:
지도는 조건이 참인 **모든 초**를 세지만, 엔진은 한 기회에서 **첫 초에만 진입**하고
청산까지 보유한다. 실측 대조:

| | 값 |
|---|---|
| 지도 마스크 행 | 15,032초 |
| 실제 기회 (일자·종목) | **698개** (엔진 실측 833거래와 정합) |
| 기회당 지속 | 21.5초 |
| 전 초 평균(지도가 쓰던 값) | **+0.0849%** |
| **첫 초만**(엔진 진입 시점) | **+0.0180%** |
| 일평균 | +0.2254% → **+0.0117%** |

나중 초들이 더 좋아 보여(+0.088%) 지도 추정이 **4.7배 부풀려졌다.** 지도가 양수라고
한 후보가 엔진에서 음수(−0.1%)로 뒤집힌 직접 원인이다.

교정: 조건 통과 초 중 **엔진이 실제로 진입할 수 있는 초만** 남긴다 —
(일자, 종목) 안에서 첫 초를 잡고, 그 뒤 `horizon` 초(보유 기간) 동안은 건너뛴다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec


def entry_positions(frame: pd.DataFrame, mask: np.ndarray, *, horizon: int,
                    time_digits: int = 14) -> np.ndarray:
    """조건 통과 초 → **엔진이 실제로 진입하는 초**의 위치 색인.

    같은 (일자, 종목) 안에서 진입 후 `horizon` 동안은 보유 중이라 재진입하지 않는다.
    """
    picked = np.flatnonzero(mask)
    if picked.size == 0:
        return picked
    clock = frame["시분초"].to_numpy()[picked]
    unit = (np.array([spec.hhmmss_to_sod(int(c)) for c in clock], dtype=np.int64)
            if time_digits == 14
            else (clock // 100) * 60 + (clock % 100))
    day = frame["일자"].to_numpy()[picked]
    code = pd.factorize(frame["종목코드"].to_numpy()[picked])[0]

    order = np.lexsort((unit, code, day))
    picked, unit, day, code = picked[order], unit[order], day[order], code[order]

    keep = np.zeros(len(picked), dtype=bool)
    last_day, last_code, busy_until = -1, -1, -(10 ** 9)
    for index in range(len(picked)):
        if day[index] != last_day or code[index] != last_code:
            last_day, last_code, busy_until = day[index], code[index], -(10 ** 9)
        if unit[index] >= busy_until:
            keep[index] = True
            busy_until = unit[index] + horizon
    return np.sort(picked[keep])


def entry_mask(frame: pd.DataFrame, mask: np.ndarray, *, horizon: int,
               time_digits: int = 14) -> np.ndarray:
    """`entry_positions` 를 불리언 마스크로."""
    out = np.zeros(len(frame), dtype=bool)
    out[entry_positions(frame, mask, horizon=horizon, time_digits=time_digits)] = True
    return out
