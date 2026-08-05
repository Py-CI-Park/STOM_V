"""QSP10 프런티어 스캔 — 심어둔 흑자 구역을 규모대별로 찾고, 없으면 없다고 말한다."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.frontier import scan

NO_HIT = 300
RULE = dict(tp_pct=2.0, sl_pct=1.0, tp="hit_up_2", sl="hit_dn_1",
            horizon=NO_HIT, timeout_label="frA_300")


def _make(win_prob_good: float, seed: int = 4, n_days: int = 120,
          per_day: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        signal = rng.uniform(0, 1, per_day)
        noise = rng.uniform(0, 1, per_day)
        good = signal > 0.8                     # 상위 20% 구간에만 심는다
        win = rng.random(per_day) < np.where(good, win_prob_good, 0.20)
        frames.append(pd.DataFrame({
            "일자": 20240300 + day,
            "시분초": rng.integers(90000, 92000, per_day),
            "종목코드": rng.integers(1000, 1020, per_day).astype(str),
            "signal": signal, "noise": noise,
            "hit_up_2": np.where(win, rng.integers(10, 200, per_day), NO_HIT),
            "hit_dn_1": np.where(win, NO_HIT, rng.integers(10, 200, per_day)),
            "frA_300": rng.normal(-0.3, 0.4, per_day),
        }))
    return pd.concat(frames, ignore_index=True)


def test_scan_finds_planted_region_with_band_and_evidence() -> None:
    result = scan(_make(win_prob_good=0.75), variables=["signal", "noise"], buckets=10, **RULE)

    assert result["survivors"] > 0
    assert result["frontier"], "프런티어가 비었다"
    best = max(result["frontier"], key=lambda row: row["expectancy_pct"])
    assert "signal" in best["description"]
    assert best["expectancy_pct"] > 0
    assert best["win_rate"] > best["breakeven"]      # 손익분기 돌파
    assert best["q_value"] <= 0.10                   # FDR 통과
    assert best["cluster"]["days"] > 0               # 자본 경로 경고 동반


def test_scan_reports_nothing_when_there_is_no_edge() -> None:
    # 어디에도 엣지가 없으면(전 구간 동일 승률) 프런티어는 비어야 한다.
    result = scan(_make(win_prob_good=0.20, seed=9), variables=["signal", "noise"],
                  buckets=10, **RULE)
    assert result["frontier"] == []


def test_frontier_bands_are_disjoint_and_sample_backed() -> None:
    result = scan(_make(win_prob_good=0.75), variables=["signal", "noise"], buckets=10, **RULE)
    bands = [row["band"] for row in result["frontier"]]
    assert len(bands) == len(set(bands)), "같은 규모대가 중복 보고됐다"
    assert all(row["n"] > 0 and row["per_day"] > 0 for row in result["frontier"])
