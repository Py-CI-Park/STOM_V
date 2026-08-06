"""QSP13 — 워크포워드: 표본 밖 검증을 **탐색 루프 안**으로 넣는다.

QSP12 결론: 사다리 3종(절별 고원·비용 스트레스·국면 4분할)을 전부 통과한 후보가
홀드아웃에서 승률 45%→27.8% 로 무너졌다. 원인은 **선택 편의** — 수백만 조합을 훑고
최고를 고른 뒤에 검사하면, 그 검사는 이미 선택된 것에 대한 검사라 선택 과정을
반영하지 못한다. 설계 구간을 4분할해 전부 양수여도 5번째 구간에서 무너졌다.

교정의 핵심: **한 번도 보지 않은 구간에서 평가하는 일을 여러 번 반복**한다.

    학습[1..k] → 검증[k+1] → 학습[1..k+1] → 검증[k+2] → ...

각 폴드에서 탐색은 **학습 구간만** 보고, 성적은 **검증 구간에서만** 잰다. 이렇게 모은
검증 성적의 평균이 표본 밖 기대 성능의 정직한 추정치다. 폴드 대부분이 음수면
"이 탐색 방식으로는 안 된다"가 **설계 구간 안에서** 확정된다 — 홀드아웃을 태우지 않고.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

from ai_strategy_loop.labeling.entries import EntryDeduper
from ai_strategy_loop.labeling.frontier import row_values
from ai_strategy_loop.labeling.hierarchy import search
from ai_strategy_loop.labeling.ladder import branch_mask

MIN_TRAIN_DAYS = 120
MIN_VALID_DAYS = 20


@dataclass
class Fold:
    index: int
    train: tuple[int, int]
    valid: tuple[int, int]
    branches: list[dict]
    train_stats: dict
    valid_stats: dict


@dataclass
class WalkForwardResult:
    rule: dict
    folds: list[Fold] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def make_folds(days: np.ndarray, *, n_folds: int = 5,
               min_train_days: int = MIN_TRAIN_DAYS) -> list[tuple[np.ndarray, np.ndarray]]:
    """앞으로만 가는 분할 — 검증 구간은 학습 구간보다 **항상 뒤**다."""
    total = len(days)
    if total < min_train_days + MIN_VALID_DAYS:
        return []
    remaining = total - min_train_days
    step = max(remaining // n_folds, MIN_VALID_DAYS)
    folds = []
    start = min_train_days
    while start + MIN_VALID_DAYS <= total and len(folds) < n_folds:
        stop = min(start + step, total)
        folds.append((np.arange(0, start), np.arange(start, stop)))
        start = stop
    return folds


def _stats(values: np.ndarray, day_codes: np.ndarray, n_days: int) -> dict:
    if values.size == 0:
        return {"n": 0, "expectancy_pct": float("nan"), "day_mean_pct": float("nan"),
                "day_positive_ratio": float("nan"), "days": 0}
    counts = np.bincount(day_codes, minlength=n_days)
    sums = np.bincount(day_codes, weights=values, minlength=n_days)
    active = counts > 0
    daily = sums[active] / counts[active]
    return {"n": int(values.size), "expectancy_pct": float(values.mean()),
            "day_mean_pct": float(daily.mean()),
            "day_positive_ratio": float((daily > 0).mean()), "days": int(len(daily))}


def run(frame: pd.DataFrame, *, variables: list[str], tp_pct: float, sl_pct: float,
        tp: str, sl: str, horizon: int, timeout_label: str, n_folds: int = 5,
        min_rows: int = 400, max_depth: int = 4) -> WalkForwardResult:
    """폴드마다 학습 구간에서만 탐색하고 검증 구간에서만 평가한다."""
    rule_kwargs = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                       horizon=horizon, timeout_label=timeout_label)
    day_codes, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    values = row_values(frame, **rule_kwargs)
    deduper = EntryDeduper(frame, horizon=horizon)

    result = WalkForwardResult(rule={"tp_pct": tp_pct, "sl_pct": sl_pct, "horizon": horizon})
    for index, (train_days, valid_days) in enumerate(make_folds(day_labels, n_folds=n_folds)):
        train_rows = np.isin(day_codes, train_days)
        valid_rows = np.isin(day_codes, valid_days)
        if train_rows.sum() < min_rows or valid_rows.sum() < min_rows // 4:
            continue
        found = search(frame.loc[train_rows].reset_index(drop=True), variables=variables,
                       min_rows=min_rows, max_depth=max_depth, objective="day_mean",
                       **rule_kwargs)
        if not found.branches:
            continue
        branches = [{"name": b.name, "spec": b.mask_spec, "clauses": b.clauses}
                    for b in found.branches]
        # **검증 구간에는 학습에서 정한 임계를 그대로 적용**한다(재적합 금지).
        applied = deduper.apply(branch_mask(frame, branches))
        train_pos = np.flatnonzero(applied & train_rows)
        valid_pos = np.flatnonzero(applied & valid_rows)
        result.folds.append(Fold(
            index=index,
            train=(int(day_labels[train_days[0]]), int(day_labels[train_days[-1]])),
            valid=(int(day_labels[valid_days[0]]), int(day_labels[valid_days[-1]])),
            branches=branches,
            train_stats=_stats(values[train_pos], day_codes[train_pos], n_days),
            valid_stats=_stats(values[valid_pos], day_codes[valid_pos], n_days),
        ))

    valid_means = [fold.valid_stats["day_mean_pct"] for fold in result.folds
                   if fold.valid_stats["n"] > 0 and not np.isnan(fold.valid_stats["day_mean_pct"])]
    if valid_means:
        t_stat, p_two = (stats.ttest_1samp(valid_means, 0.0) if len(valid_means) >= 3
                         else (0.0, 1.0))
        result.summary = {
            "folds": len(result.folds),
            "oos_day_mean_pct": float(np.mean(valid_means)),
            "oos_positive_folds": int(sum(1 for v in valid_means if v > 0)),
            "oos_fold_values": [round(v, 4) for v in valid_means],
            "p_value": float(p_two / 2 if t_stat > 0 else 1.0),
            "train_day_mean_pct": float(np.mean(
                [f.train_stats["day_mean_pct"] for f in result.folds])),
        }
        # 표본 밖 평균이 양수이고 과반 폴드가 양수여야 통과.
        result.summary["passed"] = bool(
            result.summary["oos_day_mean_pct"] > 0
            and result.summary["oos_positive_folds"] * 2 > len(valid_means))
    else:
        result.summary = {"folds": len(result.folds), "passed": False,
                          "oos_day_mean_pct": float("nan"), "oos_positive_folds": 0}
    return result
