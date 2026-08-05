"""QSP10 P3 — 수렴 루프 계약: 심어둔 신호를 찾고, 표본·수렴 규율을 지킨다."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.converge import converge

NO_HIT = 300


def _planted(n_days: int = 120, per_day: int = 400, seed: int = 5) -> pd.DataFrame:
    """`signal` 상위 30% 에서만 익절이 잘 나오도록 심는다. `noise` 는 무관."""
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        signal = rng.uniform(0, 1, per_day)
        noise = rng.uniform(0, 1, per_day)
        good = signal > 0.7
        win = rng.random(per_day) < np.where(good, 0.55, 0.22)
        hit_up = np.where(win, rng.integers(10, 200, per_day), NO_HIT)
        hit_dn = np.where(win, NO_HIT, rng.integers(10, 200, per_day))
        frames.append(pd.DataFrame({
            "일자": 20240300 + day, "시분초": rng.integers(90000, 92000, per_day),
            "종목코드": rng.integers(1000, 1010, per_day).astype(str),
            "signal": signal, "noise": noise,
            "hit_up_2": hit_up, "hit_dn_1": hit_dn,
            "frA_300": rng.normal(-0.3, 0.5, per_day),
        }))
    return pd.concat(frames, ignore_index=True)


def _run(frame: pd.DataFrame, **kwargs):
    options = {"min_rows": 1_000, **kwargs}
    return converge(frame, variables=["signal", "noise"], tp_pct=2.0, sl_pct=1.0,
                    tp="hit_up_2", sl="hit_dn_1", horizon=NO_HIT,
                    timeout_label="frA_300", **options)


def test_converge_finds_planted_signal_and_improves_expectancy() -> None:
    result = _run(_planted())

    assert result.steps, "절을 하나도 못 찾았다"
    first = result.steps[0]
    assert first.clause["변수"] == "signal"
    assert first.clause["연산자"] == ">"
    # 기대값이 기준선보다 개선됐고, 일 클러스터 검정도 통과한다.
    assert first.stats["expectancy_pct"] > result.rule["base"]["expectancy_pct"]
    assert first.day_p_value < 0.05


def test_thresholds_come_from_quantile_grid_only() -> None:
    frame = _planted()
    result = _run(frame)
    clause = result.steps[0].clause
    column = frame[clause["변수"]]
    expected = float(column.quantile(clause["분위"]))
    assert abs(clause["임계"] - expected) < 1e-9


def test_convergence_stops_and_reports_cluster_load() -> None:
    result = _run(_planted(), max_depth=5)

    # 개선이 멈추면 더 쌓지 않는다.
    values = [step.stats["expectancy_pct"] for step in result.steps]
    assert values == sorted(values), "기대값이 단조 증가가 아니다"
    assert len(result.steps) <= 5
    # 자본 경로 경고 지표가 매 단계 실린다.
    for step in result.steps:
        assert step.cluster["mean_simultaneous"] >= 1.0
        assert step.cluster["days"] > 0


def test_sample_floor_blocks_overfit_slices() -> None:
    # 표본 하한을 아주 크게 두면 어떤 절도 통과하지 못한다.
    result = _run(_planted(), min_rows=10_000_000)
    assert result.steps == []
