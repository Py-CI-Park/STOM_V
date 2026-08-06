"""M-2 — 변수 정보력 랭킹·이익 포켓·얕은 트리 (전부 일 클러스터 추론).

겹침 표본 함정(명세 §3-4): 같은 날 인접 초의 라벨은 거의 같으므로 행 단위 검정은
표본수를 부풀린다. 여기의 모든 추론 단위는 **일(day) 클러스터 평균**이다.
산출은 관측(진단) 권위 — 조건식 채택은 M-5 게이트와 사람 승인 사항.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

FDR_ALPHA = 0.10
MIN_DAYS = 30          # 클러스터(일) 최소 수 — 이보다 적으면 통계 무효
_TOP, _BOTTOM = 9, 0   # 10분위 기준 상·하위


def day_clustered_spread(frame: pd.DataFrame, variable: str, *, label: str,
                         buckets: int = 10) -> dict:
    """상위-하위 분위 라벨 차이를 **일별 평균의 차이**로 검정한다."""
    rows = frame[[variable, label, "일자"]].dropna()
    deciles = pd.qcut(rows[variable], buckets, labels=False, duplicates="drop")
    top_bucket = int(deciles.max())
    per_day = rows.assign(_q=deciles).groupby(["일자", "_q"])[label].mean().unstack()
    paired = per_day[[0, top_bucket]].dropna()
    diffs = paired[top_bucket] - paired[0]
    t_stat, p_value = stats.ttest_1samp(diffs, 0.0) if len(diffs) >= MIN_DAYS else (np.nan, 1.0)
    return {
        "spread_pp": round(float(diffs.mean()), 4),
        "p_value": float(p_value),
        "n_days": int(len(diffs)),
        "n_rows": int(len(rows)),
    }


def rank_variables(frame: pd.DataFrame, variables: list[str], *, label: str,
                   buckets: int = 10) -> pd.DataFrame:
    """전 변수 스캔 + BH-FDR(q≤0.10). 표본수·일수 병기(표본 없는 밝은 칸 금지)."""
    records = []
    for variable in variables:
        result = day_clustered_spread(frame, variable, label=label, buckets=buckets)
        records.append({"변수": variable, "spread_pp": result["spread_pp"],
                        "p_value": result["p_value"], "표본수": result["n_rows"],
                        "일수": result["n_days"]})
    table = pd.DataFrame(records)
    ranked = table.sort_values("p_value").reset_index(drop=True)
    m = len(ranked)
    ranked["q_value"] = [min(p * m / (i + 1), 1.0) for i, p in enumerate(ranked["p_value"])]
    ranked["q_value"] = ranked["q_value"][::-1].cummin()[::-1]
    ranked["fdr_pass"] = ranked["q_value"] <= FDR_ALPHA
    return ranked.sort_values(["fdr_pass", "spread_pp"], ascending=[False, False],
                              key=lambda s: s.abs() if s.name == "spread_pp" else s
                              ).reset_index(drop=True)


def _cell_stats(rows: pd.DataFrame, label: str) -> tuple[float, float, int, int]:
    """칸 평균·일 클러스터 t·일수·행수."""
    per_day = rows.groupby("일자")[label].mean()
    if len(per_day) < MIN_DAYS:
        return float(rows[label].mean()), 1.0, int(len(per_day)), int(len(rows))
    t_stat, p_value = stats.ttest_1samp(per_day, 0.0)
    # 단측(양수) 검정 — 이익 포켓만 찾는다.
    one_sided = p_value / 2 if t_stat > 0 else 1.0
    return float(rows[label].mean()), float(one_sided), int(len(per_day)), int(len(rows))


def profit_pockets(frame: pd.DataFrame, var_x: str, var_y: str, *, label: str,
                   buckets: int = 10, alpha: float = FDR_ALPHA) -> list[dict]:
    """2D 이익 포켓 — FDR 통과 양수 칸 → 인접 병합(고립 1칸 금지)."""
    rows = frame[[var_x, var_y, label, "일자"]].dropna()
    qx = pd.qcut(rows[var_x], buckets, labels=False, duplicates="drop")
    qy = pd.qcut(rows[var_y], buckets, labels=False, duplicates="drop")
    cells = []
    for (x, y), sub in rows.groupby([qx, qy]):
        mean, p_one, n_days, n_rows = _cell_stats(sub, label)
        if mean > 0:
            cells.append({"x": int(x), "y": int(y), "mean_pp": round(mean, 4),
                          "p": p_one, "n_days": n_days, "n": n_rows})
    if not cells:
        return []
    # BH-FDR (칸 단위).
    cells.sort(key=lambda c: c["p"])
    m = len(cells)
    passing = set()
    q_prev = 1.0
    for i in range(m - 1, -1, -1):
        q_val = min(cells[i]["p"] * m / (i + 1), q_prev)
        q_prev = q_val
        cells[i]["q"] = round(q_val, 4)
    survivors = [c for c in cells if c["q"] <= alpha and c["n_days"] >= MIN_DAYS]
    # 인접(상하좌우) 연결 성분 — 2칸 이상만 포켓.
    remaining = {(c["x"], c["y"]): c for c in survivors}
    pockets: list[dict] = []
    while remaining:
        seed = next(iter(remaining))
        stack, component = [seed], []
        while stack:
            key = stack.pop()
            cell = remaining.pop(key, None)
            if cell is None:
                continue
            component.append(cell)
            x, y = key
            stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        if len(component) >= 2:
            pockets.append({
                "var_x": var_x, "var_y": var_y,
                "cells": sorted(component, key=lambda c: (c["x"], c["y"])),
                "mean_pp": round(float(np.average(
                    [c["mean_pp"] for c in component], weights=[c["n"] for c in component])), 4),
                "n": int(sum(c["n"] for c in component)),
            })
    return sorted(pockets, key=lambda p: p["mean_pp"] * p["n"], reverse=True)


def shallow_tree_paths(frame: pd.DataFrame, variables: list[str], *, label: str,
                       max_depth: int = 3, min_leaf_days: int = MIN_DAYS) -> list[dict]:
    """얕은 결정트리 — 각 흑자 리프 경로를 `{변수, 연산자, 임계}` 절 목록으로 반환.

    트리는 ND 구조 탐지기일 뿐이다. 임계는 이후 분위 격자에 스냅해야 하고(규율),
    블랙박스 예측기를 최종 산출물로 쓰지 않는다.
    """
    from sklearn.tree import DecisionTreeRegressor

    rows = frame[[*variables, label, "일자"]].dropna()
    tree = DecisionTreeRegressor(max_depth=max_depth, min_samples_leaf=max(len(rows) // 100, 50),
                                 random_state=0)
    tree.fit(rows[variables], rows[label])
    structure = tree.tree_

    paths: list[dict] = []

    def _walk(node: int, clauses: list[dict]) -> None:
        if structure.children_left[node] == -1:      # leaf
            mask = np.ones(len(rows), dtype=bool)
            for clause in clauses:
                col = rows[clause["변수"]].to_numpy()
                mask &= (col <= clause["임계"]) if clause["연산자"] == "<=" else (col > clause["임계"])
            leaf = rows[mask]
            mean, p_one, n_days, n_rows = _cell_stats(leaf, label)
            if mean > 0 and n_days >= min_leaf_days:
                paths.append({"절": clauses, "평균": round(mean, 4), "p": round(p_one, 5),
                              "표본수": n_rows, "일수": n_days})
            return
        variable = variables[structure.feature[node]]
        threshold = float(structure.threshold[node])
        _walk(structure.children_left[node],
              clauses + [{"변수": variable, "연산자": "<=", "임계": round(threshold, 6)}])
        _walk(structure.children_right[node],
              clauses + [{"변수": variable, "연산자": ">", "임계": round(threshold, 6)}])

    _walk(0, [])
    return sorted(paths, key=lambda p: p["평균"] * p["표본수"], reverse=True)
