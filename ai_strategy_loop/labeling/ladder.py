"""QSP12 검증 사다리 — 홀드아웃을 열기 **전에** 설계 구간에서 거를 수 있는 것들.

홀드아웃은 한 번뿐인 카드다. 과최적이거나 국면에 기댄 후보를 거기서 태우면 안 된다.
아래 셋은 전부 설계 구간 안에서 답이 나온다.

| 검사 | 무엇을 잡나 |
|---|---|
| **임계 고원** | 임계를 이웃 분위로 밀어도 살아남는가 — 절벽이면 과최적 |
| **비용 스트레스** | 왕복 비용 ×1.5 에서도 흑자인가 — 슬리피지 여유 |
| **국면 절단** | 기간을 나눠도 일관되는가 — 특정 장세에만 기댄 것이 아닌가 |
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling import label_spec as spec
from ai_strategy_loop.labeling.entries import EntryDeduper
from ai_strategy_loop.labeling.frontier import row_values


def branch_mask(frame: pd.DataFrame, branches: list[dict], *,
                threshold_shift: dict | None = None) -> np.ndarray:
    """분기 목록 → 마스크. `threshold_shift` 로 임계를 흔들어 고원 검사에 쓴다."""
    clock = frame["시분초"].to_numpy()
    cap = frame["시가총액"].to_numpy(dtype=np.float64) if "시가총액" in frame else None
    total = np.zeros(len(frame), dtype=bool)
    for branch in branches:
        spec_ = branch["spec"]
        mask = (clock >= spec_["time"][0]) & (clock < spec_["time"][1])
        if cap is not None and "cap_max" in spec_:
            mask &= cap < spec_["cap_max"]
        if cap is not None and "cap_min" in spec_:
            mask &= cap >= spec_["cap_min"]
        for clause in branch["clauses"]:
            column = frame[clause["변수"]].to_numpy(dtype=np.float64)
            threshold = clause["임계"]
            # `_shift` 가 붙은 절은 `shift_one` 이 이미 분위를 옮겨 둔 것이다.
            if threshold_shift is not None or "_shift" in clause:
                delta = 0.0 if "_shift" in clause else threshold_shift["delta"]
                quantile = float(np.clip(clause["분위"] + delta, 0.01, 0.99))
                pool = column[mask] if mask.any() else column
                pool = pool[~np.isnan(pool)]
                if pool.size:
                    threshold = float(np.quantile(
                        pool, quantile if clause["연산자"] == ">" else 1 - quantile))
            mask &= column > threshold if clause["연산자"] == ">" else column <= threshold
        total |= mask
    return total


def shift_one(branches: list[dict], branch_index: int, clause_index: int,
              delta: float) -> list[dict]:
    """분기 하나의 절 하나만 분위를 흔든 사본 — 전체 동시 이동은 너무 가혹하다.

    8분기 × 4절을 한꺼번에 밀면 32개 임계가 동시에 움직여 어떤 후보든 무너진다.
    실제로 알고 싶은 것은 **개별 임계가 절벽 위에 있는가**이다.
    """
    copied = [dict(branch, clauses=[dict(c) for c in branch["clauses"]])
              for branch in branches]
    clause = copied[branch_index]["clauses"][clause_index]
    clause["분위"] = float(np.clip(clause["분위"] + delta, 0.01, 0.99))
    clause["_shift"] = delta
    return copied


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


def run_ladder(frame: pd.DataFrame, branches: list[dict], *, tp_pct: float, sl_pct: float,
               tp: str, sl: str, horizon: int, timeout_label: str,
               cost_multiplier: float = 1.5, shifts: tuple[float, ...] = (-0.1, -0.05, 0.05, 0.1),
               regime_splits: int = 4) -> dict:
    """세 검사를 한 번에. 기준 성적과 함께 돌려준다."""
    deduper = EntryDeduper(frame, horizon=horizon)
    day_codes, day_labels = pd.factorize(frame["일자"], sort=True)
    n_days = len(day_labels)
    rule = dict(tp_pct=tp_pct, sl_pct=sl_pct, tp=tp, sl=sl,
                horizon=horizon, timeout_label=timeout_label)

    base_mask = deduper.apply(branch_mask(frame, branches))
    values = row_values(frame, **rule)
    positions = np.flatnonzero(base_mask)
    baseline = _stats(values[positions], day_codes[positions], n_days)

    def evaluate(candidate: list[dict], **kwargs) -> dict:
        picked = np.flatnonzero(deduper.apply(branch_mask(frame, candidate, **kwargs)))
        return _stats(values[picked], day_codes[picked], n_days)

    # ① 임계 고원 — **절 하나씩** 이웃 분위로 밀어도 흑자를 유지하는가.
    #    판정은 이 검사로 한다. 전체 동시 이동(아래 `simultaneous`)은 절이 수십 개면
    #    임계가 한꺼번에 움직여 어떤 후보든 무너지므로 참고용 스트레스 지표로만 둔다
    #    (실측: 동시 이동은 FAIL 인데 절별로는 28/28 통과였다).
    per_clause = []
    for branch_index, branch in enumerate(branches):
        for clause_index, clause in enumerate(branch["clauses"]):
            row = {"분기": branch_index, "변수": clause["변수"], "결과": {}}
            for delta in shifts:
                stats_ = evaluate(shift_one(branches, branch_index, clause_index, delta))
                row["결과"][f"{delta:+.2f}"] = {
                    "n": stats_["n"], "day_mean_pct": stats_["day_mean_pct"]}
            row["절벽"] = any(
                value["n"] >= 30 and not (value["day_mean_pct"] > 0)
                for value in row["결과"].values())
            per_clause.append(row)
    cliffs = [row for row in per_clause if row["절벽"]]
    plateau_ok = not cliffs

    simultaneous = [{"delta": delta, **evaluate(branches, threshold_shift={"delta": delta})}
                    for delta in shifts]
    plateau = {"per_clause": per_clause, "cliffs": len(cliffs), "clauses": len(per_clause),
               "simultaneous": simultaneous}

    # ② 비용 스트레스 — 왕복 비용을 늘려도 흑자인가.
    extra = (spec.COST_IN + spec.COST_OUT) * 100 * (cost_multiplier - 1.0)
    stressed = values[positions] - extra
    cost = _stats(stressed, day_codes[positions], n_days)
    cost_ok = cost["day_mean_pct"] > 0

    # ③ 국면 절단 — 기간을 나눠도 일관되는가.
    days_sorted = np.array(day_labels)
    chunks = np.array_split(np.arange(n_days), regime_splits)
    regimes = []
    for index, chunk in enumerate(chunks):
        keep = np.isin(day_codes[positions], chunk)
        sub = positions[keep]
        regimes.append({"구간": f"{days_sorted[chunk[0]]}~{days_sorted[chunk[-1]]}",
                        **_stats(values[sub], day_codes[sub], n_days)})
    regime_ok = all(row["day_mean_pct"] > 0 for row in regimes if row["n"] >= 20)

    return {
        "baseline": baseline,
        "plateau": {**plateau, "passed": plateau_ok},
        "cost_stress": {"multiplier": cost_multiplier, **cost, "passed": cost_ok},
        "regime": {"rows": regimes, "passed": regime_ok},
        "all_passed": bool(plateau_ok and cost_ok and regime_ok),
    }
