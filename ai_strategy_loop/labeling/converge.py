"""QSP10 P3 — 수렴 루프: 넓은 시드에서 필터를 쌓아 손익분기를 넘기는 조합을 찾는다.

902/905 등 사람 조건식에 의존하지 않는다. 출발은 **무조건 진입**(전 집행 우주)이고,
매 단계에서 기대값을 가장 크게 올리는 (변수, 방향, 분위 임계) 하나를 채택한다.

규율: 임계는 분위 격자에서만 · 표본 하한 · 일 클러스터 유의 · 설계 구간만.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.frontier import row_values
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
    day_clusters: int = 0


@dataclass
class ConvergeResult:
    rule: dict
    steps: list[Step] = field(default_factory=list)

    def clauses(self) -> list[dict]:
        return [step.clause for step in self.steps]


def _day_significance(frame: pd.DataFrame, *, tp: str, sl: str, horizon: int,
                      tp_pct: float, sl_pct: float, timeout_label: str) -> tuple[float, int]:
    """일별 기대값의 부호 검정 — 겹침 표본을 일 클러스터로 흡수(단측).

    **거래가 1건이라도 있는 날은 전부 클러스터로 쓴다.** 하루 최소 건수를 두면
    표본이 작은 후보에서 클러스터 수가 급감해 p 가 계산되지 않고 1.0 으로 기본
    반환된다 — 실측 결함(2026-08-05): n≈3,000 후보의 p 가 전부 1.0 으로 찍혀
    '증거 없음'처럼 보였으나 사실은 '계산 불가'였다. 사용한 일수를 함께 돌려준다.
    """
    daily = [
        expectancy(group, tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                   horizon=horizon, timeout_label=timeout_label)["expectancy_pct"]
        for _, group in frame.groupby("일자")
    ]
    if len(daily) < MIN_DAYS:
        return 1.0, len(daily)
    t_stat, p_two = stats.ttest_1samp(daily, 0.0)
    return float(p_two / 2 if t_stat > 0 else 1.0), len(daily)


def _day_mean_fast(values: np.ndarray, day_index: np.ndarray, n_days: int) -> float:
    """일평균 기대값 — bincount 로 벡터화.

    후보마다 `groupby` 를 돌면 30변수×5분위×2방향×깊이 만큼 반복돼 실행이 불가능하다
    (프런티어에서 이미 겪은 문제). 행별 실현 수익률을 한 번만 만들고 부분 집계한다.
    """
    if values.size == 0:
        return float("-inf")
    counts = np.bincount(day_index, minlength=n_days)
    sums = np.bincount(day_index, weights=values, minlength=n_days)
    active = counts > 0
    return float((sums[active] / counts[active]).mean())


def converge(frame: pd.DataFrame, *, variables: list[str], tp_pct: float, sl_pct: float,
             tp: str, sl: str, horizon: int, timeout_label: str,
             max_depth: int = MAX_DEPTH, min_rows: int = MIN_ROWS,
             objective: str = "pooled") -> ConvergeResult:
    """탐욕 필터 스태킹 — 매 단계 목표값을 가장 크게 올리는 절 1개를 채택.

    `objective`:
      - `pooled`(기존): 전체 합계 기대값. **거래가 몰린 날에 가중**되므로 탐욕이
        소수 날에 집중된 해를 고르는 편향이 있다(QSP10·11 실측: 거래일 64~77일).
      - `day_mean`: **일평균 기대값** — 게이트가 검정하는 바로 그 값. 최적화 대상과
        판정 대상을 일치시켜 날 편중 해를 구조적으로 피한다.
    """
    if objective not in ("pooled", "day_mean"):
        raise ValueError(f"objective 는 pooled|day_mean: {objective!r}")
    current = frame
    base_kwargs = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                       horizon=horizon, timeout_label=timeout_label)
    base = expectancy(current, **base_kwargs)
    result = ConvergeResult(rule={"tp_pct": tp_pct, "sl_pct": sl_pct, "horizon": horizon,
                                  "objective": objective, "base": base})
    used: set[str] = set()
    # 사전 계산 — 규칙이 고정이므로 **행별 실현 수익률을 한 번만** 만든다.
    #   이후 후보 평가는 위치 색인의 부분 집계라 DataFrame 을 만들지 않는다
    #   (후보마다 subset/groupby 를 만들면 30변수×5분위×2방향×깊이만큼 반복돼 실행 불가).
    day_codes, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    row_value = row_values(frame, **base_kwargs)
    columns = {name: frame[name].to_numpy(dtype=np.float64)
               for name in variables if name in frame.columns}
    current_pos = np.arange(len(frame))

    def objective_value(positions: np.ndarray) -> float:
        picked = row_value[positions]
        return (float(picked.mean()) if objective == "pooled"
                else _day_mean_fast(picked, day_codes[positions], n_days))

    incumbent = objective_value(current_pos)

    for depth in range(1, max_depth + 1):
        best = None
        for variable, values in columns.items():
            if variable in used:
                continue
            column = values[current_pos]
            finite = column[~np.isnan(column)]
            if finite.size == 0:
                continue
            for quantile in QUANTILE_GRID:
                for operator in (">", "<="):
                    threshold = float(np.quantile(
                        finite, quantile if operator == ">" else 1 - quantile))
                    keep = column > threshold if operator == ">" else column <= threshold
                    positions = current_pos[keep]
                    if positions.size < min_rows:
                        continue
                    if np.unique(day_codes[positions]).size < MIN_DAYS:
                        continue
                    value = objective_value(positions)
                    if best is None or value > best[0]:
                        best = (value, Clause(variable, operator, threshold, quantile), positions)
        if best is None:
            break
        value, clause, positions = best
        if value <= incumbent:     # 더 못 올리면 수렴
            break
        incumbent = value
        used.add(clause.variable)
        current_pos = positions
        current = frame.iloc[current_pos]      # 채택된 절에서만 실체화한다
        score = expectancy(current, **base_kwargs)
        p_value, clusters = _day_significance(current, tp=tp, sl=sl, horizon=horizon,
                                              tp_pct=tp_pct, sl_pct=sl_pct,
                                              timeout_label=timeout_label)
        result.steps.append(Step(
            depth=depth, clause=clause.as_dict(), stats=score,
            cluster=cluster_load(current), day_p_value=p_value, day_clusters=clusters,
        ))
    return result
