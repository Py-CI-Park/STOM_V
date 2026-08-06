"""QSP10 날 차원 분석 — 누출 차단 계약과 심어둔 '좋은 날' 검출."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ai_strategy_loop.labeling.day_dimension import day_table, rank_day_features

NO_HIT = 300
RULE = dict(tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
            horizon=NO_HIT, timeout_label="frA_300")
FEATURE_END, ENTRY_START = 90500, 90500


def _market(n_days: int = 100, seed: int = 13) -> pd.DataFrame:
    """아침(09:00~09:05) 체결강도가 높은 날에만 이후 진입이 잘 되도록 심는다."""
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        hot = day % 3 == 0                      # 3일에 한 번은 '좋은 날'
        morning = pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": rng.integers(90000, 90500, 40),
            "종목코드": rng.integers(1000, 1010, 40).astype(str),
            "체결강도": rng.normal(200 if hot else 100, 10, 40),
            "등락율": rng.normal(3, 1, 40), "spread_pct": rng.uniform(0.1, 0.5, 40),
            "회전율": rng.uniform(1, 5, 40),
            "hit_up_2": NO_HIT, "hit_dn_1": NO_HIT, "frA_300": 0.0,
        })
        win = rng.random(60) < (0.55 if hot else 0.20)
        after = pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": rng.integers(90500, 92000, 60),
            "종목코드": rng.integers(1000, 1010, 60).astype(str),
            "체결강도": rng.normal(150, 20, 60), "등락율": rng.normal(3, 1, 60),
            "spread_pct": rng.uniform(0.1, 0.5, 60), "회전율": rng.uniform(1, 5, 60),
            "hit_up_2": np.where(win, rng.integers(10, 200, 60), NO_HIT),
            "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, 60)),
            "frA_300": rng.normal(-0.3, 0.3, 60),
        })
        frames += [morning, after]
    return pd.concat(frames, ignore_index=True)


def test_day_table_separates_feature_and_entry_windows() -> None:
    table = day_table(_market(), feature_end=FEATURE_END, entry_start=ENTRY_START, **RULE)

    assert len(table) == 100
    assert {"아침_체결강도", "거래수", "기대값"} <= set(table.columns)
    # 아침 창 행 수(40)와 진입 창 행 수(60)가 섞이지 않았다.
    assert (table["아침_신호수"] == 40).all()
    assert (table["거래수"] == 60).all()


def test_overlapping_windows_are_rejected_as_leakage() -> None:
    with pytest.raises(ValueError):
        day_table(_market(), feature_end=91000, entry_start=90500, **RULE)


def test_rank_day_features_finds_the_planted_day_signal() -> None:
    table = day_table(_market(), feature_end=FEATURE_END, entry_start=ENTRY_START, **RULE)
    ranked = rank_day_features(table, buckets=3)

    top = ranked.iloc[0]
    assert top["특징"] == "아침_체결강도"
    assert top["차이"] > 0                 # 아침이 뜨거운 날이 더 좋다
    assert top["p"] < 0.01
    assert top["n_days"] == 100
