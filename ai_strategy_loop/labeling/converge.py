"""QSP10 P3 — 수렴 루프: 넓은 시드에서 필터를 쌓아 손익분기를 넘기는 조합을 찾는다.

902/905 등 사람 조건식에 의존하지 않는다. 출발은 **무조건 진입**(전 집행 우주)이고,
매 단계에서 기대값을 가장 크게 올리는 (변수, 방향, 분위 임계) 하나를 채택한다.

규율: 임계는 분위 격자에서만 · 표본 하한 · 일 클러스터 유의 · 설계 구간만.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.universe import cluster_load, expectancy

MIN_ROWS = 2_000          # 후보 조건의 최소 표본
MIN_DAYS = 60             # 최소 지지 일수
QUANTILE_GRID = (0.5, 0.6, 0.7, 0.8, 0.9)   # 분위 임계 후보
MAX_DEPTH = 6


@dataclass
class Clause:
    variable: str
    operator: str        # ">" | "<="
    threshold: float
    quantile: float

    def mask(self, frame: pd.DataFrame) -> pd.Series:
        column = frame[self.variable]
        return column > self.threshold if self.operator == ">" else column <= self.threshold

    def as_dict(self) -> dict:
        return {"변수": self.variable, "연산자": self.operator,
                "임계": float(self.threshold), "분위": float(self.quantile)}


@dataclass
class Step:
    depth: int
    clause: dict
    stats: dict
    cluster: dict
    day_p_value: float


@dataclass
class ConvergeResult:
    rule: dict
    steps: list[Step] = field(default_factory=list)

    def clauses(self) -> list[dict]:
        return [step.clause for step in self.steps]


def _day_significance(frame: pd.DataFrame, *, tp: str, sl: str, horizon: int,
                      tp_pct: float, sl_pct: float, timeout_label: str) -> float:
    """일별 기대값의 부호 검정 — 겹침 표본을 일 클러스터로 흡수(단측)."""
    daily = []
    for _, group in frame.groupby("일자"):
        if len(group) < 5:
            continue
        daily.append(expectancy(group, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                                horizon=horizon, timeout_label=timeout_label)["expectancy_pct"])
    if len(daily) < MIN_DAYS:
        return 1.0
    t_stat, p_two = stats.ttest_1samp(daily, 0.0)
    return float(p_two / 2 if t_stat > 0 else 1.0)


def converge(frame: pd.DataFrame, *, variables: list[str], tp_pct: float, sl_pct: float,
             tp: str, sl: str, horizon: int, timeout_label: str,
             max_depth: int = MAX_DEPTH, min_rows: int = MIN_ROWS) -> ConvergeResult:
    """탐욕 필터 스태킹 — 매 단계 기대값을 가장 크게 올리는 절 1개를 채택."""
    current = frame
    base = expectancy(current, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                      horizon=horizon, timeout_label=timeout_label)
    result = ConvergeResult(rule={"tp_pct": tp_pct, "sl_pct": sl_pct, "horizon": horizon,
                                  "base": base})
    used: set[str] = set()

    for depth in range(1, max_depth + 1):
        best = None
        for variable in variables:
            if variable in used or variable not in current:
                continue
            column = current[variable].dropna()
            if column.empty:
                continue
            for quantile in QUANTILE_GRID:
                for operator in (">", "<="):
                    threshold = float(column.quantile(quantile if operator == ">" else 1 - quantile))
                    clause = Clause(variable, operator, threshold, quantile)
                    subset = current[clause.mask(current)]
                    if len(subset) < min_rows or subset["일자"].nunique() < MIN_DAYS:
                        continue
                    score = expectancy(subset, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                                       horizon=horizon, timeout_label=timeout_label)
                    value = score["expectancy_pct"]
                    if best is None or value > best[0]:
                        best = (value, clause, score, subset)
        if best is None:
            break
        value, clause, score, subset = best
        previous = result.steps[-1].stats["expectancy_pct"] if result.steps else base["expectancy_pct"]
        if value <= previous:      # 더 못 올리면 수렴
            break
        used.add(clause.variable)
        current = subset
        result.steps.append(Step(
            depth=depth, clause=clause.as_dict(), stats=score,
            cluster=cluster_load(current),
            day_p_value=_day_significance(current, tp=tp, sl=sl, horizon=horizon,
                                          tp_pct=tp_pct, sl_pct=sl_pct,
                                          timeout_label=timeout_label),
        ))
    return result
