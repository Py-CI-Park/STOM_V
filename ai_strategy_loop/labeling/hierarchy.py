"""QSP12 — 계층 구조 탐색: 먼저 나누고, 분기마다 다른 절 집합을 찾는다.

QSP11 결론: 네 갈래 독립 탐색이 모두 실패했고, 한계는 탐색 방식이 아니라
**"전 구간 공통 임계 ≤6절"이라는 가설 공간의 모양**이었다.

흑자가 증명된 902/905 는 그런 모양이 아니다:

    if 시분초 < 90200:            # 시간창 분기
        if 시가총액 < 3000:        # 국면 분기
            ...절 다발 A (서지 3.0배, 등락율 2~4%, ...)
    elif 90200 <= 시분초 < 90500:  # 다른 시간창
        if 시가총액 < 3000:
            ...절 다발 B (서지 2.0배, 등락율 3~8%, ...)   ← 임계가 다르다

이 모듈은 그 구조를 탐색한다 — **분기별로 독립 수렴**한 뒤 합집합을 평가한다.
분기 수만큼 다중검정이 늘어나므로 **결합 성적으로만 판정**한다(분기별 성적은 진단용).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.converge import MIN_DAYS, converge
from ai_strategy_loop.labeling.frontier import row_values

#: 분기 축 정의 — 902/905 의 실제 구조(시간창 → 시총)를 따른다.
TIME_BANDS: tuple[tuple[int, int], ...] = ((90000, 90200), (90200, 90500),
                                           (90500, 91000), (91000, 92000))
CAP_TIERS: tuple[float, ...] = (3000.0,)      # 시가총액(억) 경계 — 소형/그 외


@dataclass
class Branch:
    name: str
    mask_spec: dict
    clauses: list[dict]
    stats: dict
    rows: int


@dataclass
class HierarchyResult:
    rule: dict
    branches: list[Branch] = field(default_factory=list)
    combined: dict = field(default_factory=dict)


def partitions(frame: pd.DataFrame, *, time_bands=TIME_BANDS,
               cap_tiers=CAP_TIERS) -> list[tuple[str, dict, np.ndarray]]:
    """분기 목록 — (이름, 사양, 불리언 마스크). 사양은 조건식 렌더에 그대로 쓴다."""
    clock = frame["시분초"].to_numpy()
    cap = frame["시가총액"].to_numpy(dtype=np.float64) if "시가총액" in frame else None
    result: list[tuple[str, dict, np.ndarray]] = []
    for start, end in time_bands:
        time_mask = (clock >= start) & (clock < end)
        if cap is None:
            result.append((f"{start}~{end}", {"time": [start, end]}, time_mask))
            continue
        for tier in cap_tiers:
            result.append((f"{start}~{end}/시총<{tier:.0f}",
                           {"time": [start, end], "cap_max": tier},
                           time_mask & (cap < tier)))
            result.append((f"{start}~{end}/시총>={tier:.0f}",
                           {"time": [start, end], "cap_min": tier},
                           time_mask & (cap >= tier)))
    return result


def _day_stats(values: np.ndarray, day_index: np.ndarray, n_days: int) -> np.ndarray:
    counts = np.bincount(day_index, minlength=n_days)
    sums = np.bincount(day_index, weights=values, minlength=n_days)
    active = counts > 0
    return sums[active] / counts[active]


def search(frame: pd.DataFrame, *, variables: list[str], tp_pct: float, sl_pct: float,
           tp: str, sl: str, horizon: int, timeout_label: str,
           min_rows: int = 800, max_depth: int = 4,
           objective: str = "day_mean") -> HierarchyResult:
    """분기별 독립 수렴 → 합집합 결합 평가.

    분기 표본이 작으므로 `min_rows` 를 전역 탐색보다 낮춘다. 대신 분기별 성적은
    **진단용**이고, 게이트에 쓰는 값은 **결합 성적**이다(분기 수만큼 다중검정이 늘기 때문).
    """
    rule_kwargs = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                       horizon=horizon, timeout_label=timeout_label)
    day_codes, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    values = row_values(frame, **rule_kwargs)

    result = HierarchyResult(rule={"tp_pct": tp_pct, "sl_pct": sl_pct,
                                   "horizon": horizon, "objective": objective})
    selected = np.zeros(len(frame), dtype=bool)

    for name, spec, mask in partitions(frame):
        if mask.sum() < min_rows:
            continue
        branch_frame = frame.loc[mask]
        if branch_frame["일자"].nunique() < MIN_DAYS:
            continue
        outcome = converge(branch_frame, variables=variables, min_rows=min_rows,
                           max_depth=max_depth, objective=objective, **rule_kwargs)
        if not outcome.steps:
            continue
        final = outcome.steps[-1]
        # 분기 안에서 채택된 절을 원본 위치로 되돌린다.
        branch_mask = np.zeros(len(frame), dtype=bool)
        keep = pd.Series(True, index=branch_frame.index)
        for clause in outcome.clauses():
            column = branch_frame[clause["변수"]]
            keep &= (column > clause["임계"] if clause["연산자"] == ">"
                     else column <= clause["임계"])
        branch_mask[frame.index.get_indexer(branch_frame.index[keep.to_numpy()])] = True
        selected |= branch_mask
        result.branches.append(Branch(
            name=name, mask_spec=spec, clauses=outcome.clauses(),
            stats=final.stats, rows=int(branch_mask.sum()),
        ))

    if selected.any():
        picked = values[selected]
        daily = _day_stats(picked, day_codes[selected], n_days)
        t_stat, p_two = stats.ttest_1samp(daily, 0.0) if len(daily) >= MIN_DAYS else (0.0, 1.0)
        result.combined = {
            "rows": int(selected.sum()), "days": int(len(daily)),
            "expectancy_pct": float(picked.mean()),
            "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean()),
            "p_value": float(p_two / 2 if t_stat > 0 else 1.0),
            "branches": len(result.branches),
        }
    else:
        result.combined = {"rows": 0, "days": 0, "branches": 0, "p_value": 1.0,
                           "expectancy_pct": float("nan"), "day_mean_pct": float("nan"),
                           "day_positive_ratio": float("nan")}
    return result
