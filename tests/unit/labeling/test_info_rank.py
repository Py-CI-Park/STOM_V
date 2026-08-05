"""M-2 변수 정보력 랭킹 — 일 클러스터 추론·FDR·이익 포켓·게이트 계약.

핵심 함정 검증: 겹침 표본(같은 날 인접 초는 같은 정보)을 행 단위 t-검정으로 다루면
가짜 유의성이 나온다 — 반드시 **일 단위 클러스터** 평균으로 추론해야 한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.info_rank import (
    day_clustered_spread, profit_pockets, rank_variables, shallow_tree_paths,
)


def _synthetic(n_days: int = 60, rows_per_day: int = 400, seed: int = 11) -> pd.DataFrame:
    """신호 1개(signal: 상위 분위가 좋음)·잡음 1개(noise)를 심은 합성 라벨셋."""
    rng = np.random.default_rng(seed)
    frames = []
    for day in range(n_days):
        signal = rng.uniform(0, 1, rows_per_day)
        noise = rng.uniform(0, 1, rows_per_day)
        # 일 고정효과(공통 충격) + 신호 기여 — 겹침 표본의 상관을 흉내낸다.
        day_shock = rng.normal(0, 0.3)
        label = day_shock + 0.8 * (signal > 0.7) + rng.normal(0, 0.5, rows_per_day)
        frames.append(pd.DataFrame({
            "일자": 20240300 + day, "signal": signal, "noise": noise, "frA_300": label,
        }))
    return pd.concat(frames, ignore_index=True)


def test_day_clustered_spread_finds_signal_and_rejects_noise() -> None:
    df = _synthetic()
    sig = day_clustered_spread(df, "signal", label="frA_300")
    noi = day_clustered_spread(df, "noise", label="frA_300")
    assert sig["spread_pp"] > 0.3
    assert sig["p_value"] < 0.01
    assert noi["p_value"] > 0.05


def test_rank_variables_applies_fdr_and_orders_by_information() -> None:
    # 잡음 4개를 넣어 실사용(변수 ~20개)의 다중검정 구도를 흉내낸다 —
    # 변수 2개짜리 BH 는 p≈0.06 잡음도 통과시키는 게 수학적으로 맞아서 계약 검증이 안 된다.
    rng = np.random.default_rng(3)
    df = _synthetic()
    for i in range(4):
        df[f"noise{i}"] = rng.uniform(0, 1, len(df))
    table = rank_variables(df, ["signal", "noise", "noise0", "noise1", "noise2", "noise3"],
                           label="frA_300")
    assert list(table["변수"])[0] == "signal"
    row = table.set_index("변수")
    assert bool(row.loc["signal", "fdr_pass"]) is True
    # 잡음 5개 중 FDR 통과는 있어도 소수여야 한다 (q=0.10 오탐 허용 범위).
    noise_pass = int(row.loc[["noise", "noise0", "noise1", "noise2", "noise3"], "fdr_pass"].sum())
    assert noise_pass <= 1
    # 표본수·클러스터수(일수) 병기 계약.
    assert {"표본수", "일수", "spread_pp", "q_value"} <= set(table.columns)


def test_profit_pockets_requires_positive_clustered_ci_and_adjacency() -> None:
    df = _synthetic()
    pockets = profit_pockets(df, "signal", "noise", label="frA_300", buckets=5)
    # signal 상위 구간에서만 포켓이 나와야 한다 (x축 = signal 분위 3~4).
    assert pockets, "포켓 0개"
    assert all(cell["n_days"] >= 30 for p in pockets for cell in p["cells"])
    assert all(cell["x"] >= 3 for p in pockets for cell in p["cells"])
    # 고립 1칸 금지 — 모든 포켓은 인접 2칸 이상.
    assert all(len(p["cells"]) >= 2 for p in pockets)


def test_shallow_tree_paths_translate_to_clauses() -> None:
    df = _synthetic()
    paths = shallow_tree_paths(df, ["signal", "noise"], label="frA_300", max_depth=2)
    assert paths, "경로 0개"
    best = paths[0]
    # 경로 = 절 목록 {변수, 연산자, 임계} — DSL 번역 가능해야 한다.
    assert all({"변수", "연산자", "임계"} <= set(c) for c in best["절"])
    assert any(c["변수"] == "signal" for c in best["절"])
    assert best["표본수"] > 0 and best["평균"] > 0
