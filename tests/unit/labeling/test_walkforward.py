"""QSP13 워크포워드 — 선택 편의를 탐색 루프 안에서 잡아내는 계약.

QSP12 실측: 사다리 3종(절별 고원·비용×1.5·국면 4분할)을 전부 통과한 후보가
홀드아웃에서 승률 45%→27.8% 로 무너졌다. 이 테스트의 핵심은
**엣지가 없는 시장에서 워크포워드가 '없다'고 말하는가**이다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.walkforward import make_folds, run

NO_HIT = 300
RULE = dict(tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
            horizon=NO_HIT, timeout_label="frA_300")
VARIABLES = ["signal", "noise1", "noise2", "noise3"]


def _market(*, persistent_edge: bool, n_days: int = 260, per_day: int = 40,
            seed: int = 61) -> pd.DataFrame:
    """`persistent_edge=True` 면 엣지가 전 기간 유지되고, False 면 **엣지가 아예 없다**.

    엣지가 없어도 변수 4종 × 분위 격자를 훑으면 학습 구간에서는 뭔가 '발견'된다 —
    그것이 선택 편의다. 워크포워드는 그 발견이 검증 구간으로 넘어가지 않음을 보여야 한다.
    """
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        columns = {name: rng.uniform(0, 1, per_day) for name in VARIABLES}
        probability = (np.where(columns["signal"] > 0.7, 0.62, 0.30) if persistent_edge
                       else np.full(per_day, 0.34))
        win = rng.random(per_day) < probability
        frames.append(pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": 90000 + rng.integers(0, 1800, per_day),
            "종목코드": rng.integers(1000, 1060, per_day).astype(str),
            "시가총액": rng.uniform(500, 6000, per_day),
            **columns,
            "hit_up_2": np.where(win, rng.integers(10, 200, per_day), NO_HIT),
            "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, per_day)),
            "frA_300": rng.normal(-0.2, 0.2, per_day),
        }))
    return pd.concat(frames, ignore_index=True)


def test_folds_never_validate_on_past() -> None:
    days = np.arange(20240301, 20240301 + 300)
    folds = make_folds(days, n_folds=5)

    assert folds, "폴드가 만들어지지 않았다"
    for train, valid in folds:
        assert train.max() < valid.min(), "검증 구간이 학습 구간보다 앞에 있다"
    # 학습 구간은 뒤로 갈수록 넓어진다(앞으로만 가는 분할).
    assert all(len(folds[i][0]) < len(folds[i + 1][0]) for i in range(len(folds) - 1))


def test_persistent_edge_survives_out_of_sample() -> None:
    result = run(_market(persistent_edge=True), variables=VARIABLES, n_folds=4, **RULE)

    assert result.folds, "폴드를 하나도 못 돌았다"
    assert result.summary["oos_day_mean_pct"] > 0
    assert result.summary["oos_positive_folds"] * 2 > result.summary["folds"]
    assert result.summary["passed"] is True


def test_selection_bias_is_caught_when_there_is_no_edge() -> None:
    """엣지가 없는 시장 — 학습에서는 '발견'되지만 검증으로 넘어가지 않아야 한다.

    QSP12 에서 사다리가 놓친 바로 그 상황이다.
    """
    result = run(_market(persistent_edge=False, seed=77), variables=VARIABLES,
                 n_folds=4, **RULE)

    if not result.folds:          # 아무것도 못 찾으면 그 자체로 통과(허위 발견 없음)
        return
    train_mean = result.summary["train_day_mean_pct"]
    oos_mean = result.summary["oos_day_mean_pct"]
    # 학습에서는 좋아 보여도(선택 편의) 표본 밖에서는 그만큼 나오지 않는다.
    assert oos_mean < train_mean
    assert result.summary["passed"] is False


def test_summary_exposes_every_fold_value() -> None:
    result = run(_market(persistent_edge=True), variables=VARIABLES, n_folds=4, **RULE)

    assert len(result.summary["oos_fold_values"]) == len(
        [f for f in result.folds if f.valid_stats["n"] > 0])
    for fold in result.folds:
        assert fold.train[1] < fold.valid[0], "학습 끝이 검증 시작보다 뒤다"
        assert fold.branches, "분기 없이 폴드가 기록됐다"
