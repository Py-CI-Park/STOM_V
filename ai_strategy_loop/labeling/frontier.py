"""QSP10 P3 보강 — 프런티어 스캔: 표본 규모대별 '유의한 흑자 구역'이 있는가.

탐욕 수렴(converge.py)은 기대값만 최대화하므로 **표본 하한까지 밀고 내려가는 편향**이
있다(첫 실행에서 n=2,267 이 하한 2,000 에 근접). 이 모듈은 반대로 묻는다 —
"하루 N건 규모를 유지하면서 통계적으로 유의한 흑자 구역이 존재하는가?"

1D 분위 구간과 2D 분위 셀을 전수 스캔하고, 일 클러스터 검정 + BH-FDR 로 걸러
**표본 규모대별 최고 기대값**을 프런티어로 보고한다. 없으면 "없다"가 결론이다.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.universe import ROUND_TRIP_COST_PCT

FDR_ALPHA = 0.10
MIN_DAYS = 60
MIN_ROWS = 1_000
#: 표본 규모대(하루 평균 건수) — 각 밴드의 최고 구역을 따로 보고한다.
BANDS = ((1, 5), (5, 20), (20, 100), (100, 1_000), (1_000, 10_000_000))


@dataclass
class Region:
    kind: str                 # "1d" | "2d"
    description: str
    mask_spec: list[dict]     # 재현용 절 목록
    stats: dict
    day_p_value: float
    per_day: float
    cluster: dict


def row_values(frame: pd.DataFrame, *, tp_pct: float, sl_pct: float, tp: str, sl: str,
               horizon: int, timeout_label: str) -> np.ndarray:
    """행별 실현 수익률(%) — 배리어 규칙을 한 번만 벡터로 푼다.

    이후 모든 구역 평가는 이 배열의 **부분 평균**이라 O(구역 크기) 로 끝난다.
    (파이썬 루프로 구역마다 groupby 하면 수만 배 느려 스캔이 불가능하다.)
    """
    tp_time = frame[tp].to_numpy()
    sl_time = frame[sl].to_numpy()
    win_ret = tp_pct - ROUND_TRIP_COST_PCT
    loss_ret = -(sl_pct + ROUND_TRIP_COST_PCT)
    timeout = np.nan_to_num(frame[timeout_label].to_numpy(dtype=np.float64))
    # 동시 도달은 보수적으로 손절 — universe.barrier_outcome 과 같은 규약.
    values = np.where(tp_time < sl_time, win_ret,
                      np.where(sl_time < tp_time, loss_ret,
                               np.where(tp_time < horizon, loss_ret, timeout)))
    return values.astype(np.float64)


def _day_stats(values: np.ndarray, day_index: np.ndarray, n_days: int) -> np.ndarray:
    """일별 평균 — bincount 로 벡터화. 거래가 있는 날만 남긴다."""
    counts = np.bincount(day_index, minlength=n_days)
    sums = np.bincount(day_index, weights=values, minlength=n_days)
    active = counts > 0
    return sums[active] / counts[active]


def _p_value(daily: np.ndarray) -> float:
    if len(daily) < MIN_DAYS:
        return 1.0
    t_stat, p_two = stats.ttest_1samp(daily, 0.0)
    return float(p_two / 2 if t_stat > 0 else 1.0)


def _evaluate(mask: np.ndarray, values: np.ndarray, day_index: np.ndarray, n_days: int,
              spec: list[dict], kind: str, description: str) -> Region | None:
    """마스크 하나를 평가 — 전부 벡터 연산."""
    count = int(mask.sum())
    if count < MIN_ROWS:
        return None
    picked = values[mask]
    mean = float(picked.mean())
    if mean <= 0:
        return None
    daily = _day_stats(picked, day_index[mask], n_days)
    if len(daily) < MIN_DAYS:
        return None
    return Region(
        kind=kind, description=description, mask_spec=spec,
        stats={"n": count, "expectancy_pct": mean, "day_positive_ratio": float((daily > 0).mean()),
               "day_mean_pct": float(daily.mean()), "days": int(len(daily))},
        day_p_value=_p_value(daily),
        per_day=count / max(n_days, 1), cluster={"days": int(len(daily))},
    )


def scan(frame: pd.DataFrame, *, variables: list[str], buckets: int = 20,
         pair_limit: int = 10, corr_cap: float = 0.6, **rule) -> dict:
    """1D 구간 + 2D 셀 전수 스캔 → FDR 통과 흑자 구역의 규모대별 프런티어."""
    day_index, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    values = row_values(frame, **rule)

    usable = [v for v in variables if v in frame.columns and frame[v].notna().any()]
    codes: dict[str, np.ndarray] = {}
    edges: dict[str, np.ndarray] = {}
    for variable in usable:
        code, edge = pd.qcut(frame[variable], buckets, labels=False,
                             duplicates="drop", retbins=True)
        codes[variable], edges[variable] = code.to_numpy(), edge

    regions: list[Region] = []
    # 1D — 인접 분위 묶음(2~6칸 연속). 고립 1칸 금지 규율.
    for variable in usable:
        code = codes[variable]
        top = int(np.nanmax(code))
        for start in range(top + 1):
            for width in (2, 3, 4, 6):
                stop = start + width - 1
                if stop > top:
                    continue
                mask = (code >= start) & (code <= stop)
                low, high = float(edges[variable][start]), float(edges[variable][stop + 1])
                spec = [{"변수": variable, "연산자": ">", "임계": low},
                        {"변수": variable, "연산자": "<=", "임계": high}]
                region = _evaluate(mask, values, day_index, n_days, spec, "1d",
                                   f"{variable} ∈ ({low:.4g}, {high:.4g}]")
                if region:
                    regions.append(region)

    # 2D — 상관 낮은 쌍의 분위 셀(2×2 블록).
    if len(usable) >= 2:
        correlation = frame[usable].corr().abs()
        pairs = [(a, b) for a, b in itertools.combinations(usable, 2)
                 if correlation.loc[a, b] < corr_cap][:pair_limit]
        for var_x, var_y in pairs:
            cx, cy = codes[var_x], codes[var_y]
            top_x, top_y = int(np.nanmax(cx)), int(np.nanmax(cy))
            for x in range(0, top_x, 2):
                for y in range(0, top_y, 2):
                    mask = (cx >= x) & (cx <= x + 1) & (cy >= y) & (cy <= y + 1)
                    spec = [
                        {"변수": var_x, "연산자": ">", "임계": float(edges[var_x][x])},
                        {"변수": var_x, "연산자": "<=", "임계": float(edges[var_x][min(x + 2, top_x + 1)])},
                        {"변수": var_y, "연산자": ">", "임계": float(edges[var_y][y])},
                        {"변수": var_y, "연산자": "<=", "임계": float(edges[var_y][min(y + 2, top_y + 1)])},
                    ]
                    region = _evaluate(mask, values, day_index, n_days, spec, "2d",
                                       f"{var_x}[{x},{x+1}] × {var_y}[{y},{y+1}]")
                    if region:
                        regions.append(region)
    days = n_days

    if not regions:
        return {"regions": 0, "survivors": 0, "frontier": [], "days": days}

    # BH-FDR (구역 전체 단측 p).
    regions.sort(key=lambda r: r.day_p_value)
    total = len(regions)
    q_prev = 1.0
    survivors: list[Region] = []
    for index in range(total - 1, -1, -1):
        q_value = min(regions[index].day_p_value * total / (index + 1), q_prev)
        q_prev = q_value
        regions[index].stats["q_value"] = q_value
        if q_value <= FDR_ALPHA:
            survivors.append(regions[index])

    frontier = []
    for low, high in BANDS:
        band = [r for r in survivors if low <= r.per_day < high]
        if not band:
            continue
        best = max(band, key=lambda r: r.stats["expectancy_pct"])
        frontier.append({
            "band": f"하루 {low}~{high}건", "kind": best.kind,
            "description": best.description, "clauses": best.mask_spec,
            "n": best.stats["n"], "per_day": round(best.per_day, 2),
            "expectancy_pct": best.stats["expectancy_pct"],
            "day_mean_pct": best.stats["day_mean_pct"],
            "day_positive_ratio": best.stats["day_positive_ratio"],
            "days": best.stats["days"],
            "q_value": best.stats.get("q_value"),
        })
    return {"regions": total, "survivors": len(survivors), "frontier": frontier, "days": days}
