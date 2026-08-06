"""M-1 지형도 집계 — 분 프로파일·분위 격자·파셋 히트맵의 표본수 병기 계약."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.terrain import facet_heatmap, minute_profile, quantile_grid


def _frame(n: int = 1000, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    minutes = rng.integers(0, 21, n)
    return pd.DataFrame({
        "분": minutes,
        # 5분(=분 버킷 5)에만 뚜렷한 양수 엣지를 심는다.
        "frA_300": np.where(minutes == 5, 1.0, 0.0) + rng.normal(0, 0.01, n),
        "mfe_300": rng.uniform(0, 3, n),
        "mae_300": -rng.uniform(0, 2, n),
        "체결강도": rng.uniform(0, 300, n),
        "등락율": rng.uniform(0, 20, n),
        "시가총액": rng.uniform(100, 5000, n),
    })


def test_minute_profile_reports_sample_counts_and_finds_planted_edge() -> None:
    profile = minute_profile(_frame())
    assert set(profile.columns) >= {"분", "표본수", "평균", "양수비율"}
    by_minute = profile.set_index("분")
    # 심어둔 5분 엣지가 가장 밝아야 한다.
    assert by_minute["평균"].idxmax() == 5
    assert (by_minute["표본수"] > 0).all()


def test_quantile_grid_exposes_edges_for_threshold_snapping() -> None:
    grid = quantile_grid(_frame(), "체결강도", buckets=10)
    # Then: 임계 스냅용 하한/상한 경계와 표본수가 함께 나온다.
    assert {"분위", "표본수", "평균", "하한", "상한"} <= set(grid.columns)
    assert len(grid) == 10
    assert (grid["하한"] < grid["상한"]).all()


def test_facet_heatmap_every_cell_carries_n() -> None:
    payload = facet_heatmap(_frame(), "체결강도", "등락율", facet="시가총액",
                            buckets=5, facet_bins=3)
    assert payload["facet"] == "시가총액"
    assert payload["cells"], "빈 히트맵"
    assert all("n" in cell and cell["n"] > 0 for cell in payload["cells"])
    assert {cell["facet"] for cell in payload["cells"]} <= {0, 1, 2}
