"""QSP10 P2 — 통계 큐브: (변수 분위 × 배리어 규칙) 사전 집계.

모든 칸에 표본수를 병기한다(UI 원칙 1). 임계 후보는 이 큐브의 분위 경계에서만 고른다.
"""

from __future__ import annotations

import pandas as pd

from ai_strategy_loop.labeling.universe import expectancy

DEFAULT_BUCKETS = 100


def build_cube(frame: pd.DataFrame, *, variables: list[str], tp_pct: float, sl_pct: float,
               tp: str, sl: str, horizon: int, timeout_label: str,
               buckets: int = DEFAULT_BUCKETS) -> pd.DataFrame:
    """변수 × 분위별 배리어 성적표. 분위 경계(하한/상한)를 함께 실어 임계 스냅에 쓴다."""
    records = []
    for variable in variables:
        rows = frame[frame[variable].notna()]
        if rows.empty:
            continue
        codes, edges = pd.qcut(rows[variable], buckets, labels=False,
                               duplicates="drop", retbins=True)
        for bucket, group in rows.groupby(codes):
            stats = expectancy(group, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                               horizon=horizon, timeout_label=timeout_label)
            records.append({
                "변수": variable, "분위": int(bucket),
                "하한": float(edges[int(bucket)]), "상한": float(edges[int(bucket) + 1]),
                **stats,
            })
    cube = pd.DataFrame(records)
    if not cube.empty:
        cube = cube.rename(columns={"n": "n"})
        cube.attrs["universe_version"] = frame.attrs.get("universe_version", "?")
        cube.attrs["rule"] = f"TP{tp_pct}/SL{sl_pct}/T{horizon}"
    return cube
