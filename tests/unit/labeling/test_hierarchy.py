"""QSP12 계층 구조 탐색 — 분기 분할·분기별 임계·결합 판정 계약.

핵심 가설: 902/905 처럼 **시간창마다 임계가 다른** 구조는 전 구간 공통 임계 탐색으로는
찾을 수 없다. 이 테스트는 그런 구조를 심어두고 계층 탐색이 찾아내는지 확인한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.converge import converge
from ai_strategy_loop.labeling.hierarchy import partitions, search

NO_HIT = 300
RULE = dict(tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
            horizon=NO_HIT, timeout_label="frA_300")


def _split_threshold_market(n_days: int = 140, seed: int = 31) -> pd.DataFrame:
    """시간창마다 **유리한 임계가 반대**인 시장.

    09:00~09:02 → signal 이 **높을 때** 승률 높음
    09:02~09:05 → signal 이 **낮을 때** 승률 높음
    전 구간 공통 임계로는 두 효과가 상쇄돼 아무것도 안 보인다.
    """
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        for start, high_is_good in ((90000, True), (90200, False)):
            count = 60
            signal = rng.uniform(0, 1, count)
            favourable = signal > 0.7 if high_is_good else signal < 0.3
            win = rng.random(count) < np.where(favourable, 0.75, 0.20)
            clock = start + rng.integers(0, 150, count)
            frames.append(pd.DataFrame({
                "일자": 20240300 + day,
                "시분초": clock,
                "종목코드": rng.integers(1000, 1010, count).astype(str),
                "시가총액": rng.uniform(500, 2000, count),
                "signal": signal,
                "hit_up_2": np.where(win, rng.integers(10, 200, count), NO_HIT),
                "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, count)),
                "frA_300": rng.normal(-0.2, 0.3, count),
            }))
    return pd.concat(frames, ignore_index=True)


def test_partitions_are_disjoint_and_carry_render_spec() -> None:
    frame = _split_threshold_market(n_days=5)
    parts = partitions(frame)

    assert parts, "분기가 만들어지지 않았다"
    stacked = np.vstack([mask for _, _, mask in parts])
    assert stacked.sum(axis=0).max() <= 1, "분기가 겹친다"
    # 조건식 렌더에 쓸 사양이 함께 나온다.
    for _, spec, _ in parts:
        assert "time" in spec and len(spec["time"]) == 2


def test_hierarchy_finds_branch_specific_thresholds() -> None:
    frame = _split_threshold_market()
    result = search(frame, variables=["signal"], min_rows=300, max_depth=2, **RULE)

    assert len(result.branches) >= 2, "분기별 절을 못 찾았다"
    by_name = {branch.name.split("/")[0]: branch for branch in result.branches}
    early = next(b for k, b in by_name.items() if k.startswith("90000"))
    later = next(b for k, b in by_name.items() if k.startswith("90200"))
    # 이른 창은 '크다', 늦은 창은 '작다' — 반대 방향 임계를 각각 찾아야 한다.
    assert early.clauses[0]["연산자"] == ">"
    assert later.clauses[0]["연산자"] == "<="


def test_hierarchy_beats_flat_search_on_split_threshold_market() -> None:
    """이 시장에서는 전 구간 공통 임계가 상쇄돼 실패하고, 계층 탐색만 성공한다."""
    frame = _split_threshold_market()
    flat = converge(frame, variables=["signal"], min_rows=300, max_depth=2,
                    objective="day_mean", **RULE)
    hierarchical = search(frame, variables=["signal"], min_rows=300, max_depth=2, **RULE)

    flat_value = (flat.steps[-1].stats["expectancy_pct"] if flat.steps
                  else flat.rule["base"]["expectancy_pct"])
    assert hierarchical.combined["expectancy_pct"] > flat_value
    assert hierarchical.combined["day_mean_pct"] > 0
    assert hierarchical.combined["p_value"] < 0.05


def test_combined_stats_report_days_and_positive_ratio() -> None:
    result = search(_split_threshold_market(), variables=["signal"],
                    min_rows=300, max_depth=2, **RULE)
    combined = result.combined

    assert combined["rows"] > 0 and combined["days"] >= 60
    assert 0.0 <= combined["day_positive_ratio"] <= 1.0
    assert combined["branches"] == len(result.branches)


def test_small_branches_are_skipped_not_crashed() -> None:
    frame = _split_threshold_market(n_days=3)      # 일수 부족
    result = search(frame, variables=["signal"], min_rows=300, max_depth=2, **RULE)

    assert result.branches == []
    assert result.combined["rows"] == 0
    assert result.combined["p_value"] == pytest.approx(1.0)
