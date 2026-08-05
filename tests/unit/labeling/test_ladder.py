"""검증 사다리 — 홀드아웃을 열기 전에 과최적·비용 취약·국면 의존을 거르는 계약."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.ladder import branch_mask, run_ladder

NO_HIT = 300
RULE = dict(tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
            horizon=NO_HIT, timeout_label="frA_300")
BRANCH = [{"name": "a", "spec": {"time": [90000, 92000]},
           "clauses": [{"변수": "signal", "연산자": ">", "임계": 0.7, "분위": 0.7}]}]


def _market(*, edge_width: float = 0.3, regime_break: bool = False,
            n_days: int = 160, seed: int = 41) -> pd.DataFrame:
    """`signal` 상위 `edge_width` 구간에 엣지를 심는다. 좁게 심으면 고원 검사에서 걸린다."""
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        count = 40
        signal = rng.uniform(0, 1, count)
        good = signal > (1.0 - edge_width)
        if regime_break and day >= n_days // 2:      # 후반부에는 엣지가 사라진다
            good = np.zeros(count, dtype=bool)
        win = rng.random(count) < np.where(good, 0.80, 0.20)
        frames.append(pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": 90000 + rng.integers(0, 1800, count),
            "종목코드": rng.integers(1000, 1040, count).astype(str),
            "signal": signal,
            "hit_up_2": np.where(win, rng.integers(10, 200, count), NO_HIT),
            "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, count)),
            "frA_300": rng.normal(-0.2, 0.2, count),
        }))
    return pd.concat(frames, ignore_index=True)


def test_branch_mask_shift_moves_threshold_on_quantile_grid() -> None:
    frame = _market()
    base = branch_mask(frame, BRANCH)
    tighter = branch_mask(frame, BRANCH, threshold_shift={"delta": 0.1})

    assert tighter.sum() < base.sum()      # 분위를 올리면 더 좁아진다


def test_robust_edge_passes_all_three_checks() -> None:
    result = run_ladder(_market(edge_width=0.3), BRANCH, **RULE)

    assert result["baseline"]["day_mean_pct"] > 0
    assert result["plateau"]["passed"], "넓은 엣지인데 고원 검사에서 떨어졌다"
    assert result["cost_stress"]["passed"]
    assert result["regime"]["passed"]
    assert result["all_passed"]


def test_regime_dependent_edge_is_caught() -> None:
    """후반부에 엣지가 사라지는 시장은 국면 절단에서 걸려야 한다."""
    result = run_ladder(_market(regime_break=True), BRANCH, **RULE)

    assert result["regime"]["passed"] is False
    assert result["all_passed"] is False


def test_cost_stress_uses_higher_cost_and_reports_multiplier() -> None:
    result = run_ladder(_market(), BRANCH, cost_multiplier=3.0, **RULE)

    assert result["cost_stress"]["multiplier"] == 3.0
    # 비용을 올리면 기대값은 반드시 내려간다.
    assert result["cost_stress"]["expectancy_pct"] < result["baseline"]["expectancy_pct"]


def test_ladder_reports_every_shift_and_regime_slice() -> None:
    result = run_ladder(_market(), BRANCH, shifts=(-0.05, 0.05), regime_splits=3, **RULE)

    plateau = result["plateau"]
    assert plateau["clauses"] == 1                       # 분기 1 x 절 1
    assert len(plateau["per_clause"][0]["결과"]) == 2      # 흔든 방향 2
    assert len(plateau["simultaneous"]) == 2             # 참고용 동시 이동
    assert len(result["regime"]["rows"]) == 3
    assert all("구간" in row for row in result["regime"]["rows"])


def test_plateau_verdict_uses_per_clause_not_simultaneous() -> None:
    """판정은 절별 이동으로 한다 — 동시 이동은 절이 많으면 무조건 무너진다.

    실측(2026-08-06): 8분기 28절 후보가 동시 이동에서는 FAIL 인데 절별로는 28/28 통과였다.
    """
    result = run_ladder(_market(edge_width=0.3), BRANCH, **RULE)

    assert result["plateau"]["cliffs"] == 0
    assert result["plateau"]["passed"] is True
    assert "simultaneous" in result["plateau"]           # 참고 지표는 남긴다
