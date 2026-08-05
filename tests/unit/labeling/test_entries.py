"""진입 단위 정합 — 지도의 '초'를 엔진의 '거래'로 환산하는 계약.

실측 배경(2026-08-06): 지도가 조건 통과 15,032초를 전부 세는 동안 엔진은 698개
기회에서 833거래만 냈다. 이 차이가 지도 추정을 4.7배 부풀려 부호를 뒤집었다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ai_strategy_loop.labeling.entries import entry_mask, entry_positions


def _frame(rows: list[tuple[int, str, int]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["일자", "종목코드", "시분초"])


def test_one_entry_per_continuous_run() -> None:
    # 같은 종목이 09:00:00~09:00:09 동안 연속으로 조건 통과 → 진입은 1회뿐.
    frame = _frame([(20240304, "A", 90000 + i) for i in range(10)])
    positions = entry_positions(frame, np.ones(len(frame), bool), horizon=300)

    assert positions.tolist() == [0]


def test_reentry_allowed_after_holding_period() -> None:
    # 09:00:00 진입 → 300초 보유 → 09:05:00 이후에야 재진입 가능.
    frame = _frame([(20240304, "A", 90000), (20240304, "A", 90200),
                    (20240304, "A", 90500), (20240304, "A", 90501)])
    positions = entry_positions(frame, np.ones(len(frame), bool), horizon=300)

    clock = frame["시분초"].to_numpy()[positions]
    assert clock.tolist() == [90000, 90500]      # 09:02 는 보유 중이라 제외


def test_different_stocks_and_days_are_independent() -> None:
    frame = _frame([(20240304, "A", 90000), (20240304, "B", 90001),
                    (20240305, "A", 90002)])
    positions = entry_positions(frame, np.ones(len(frame), bool), horizon=300)

    assert len(positions) == 3      # 종목·날이 다르면 서로 막지 않는다


def test_mask_input_is_respected() -> None:
    frame = _frame([(20240304, "A", 90000 + i) for i in range(5)])
    mask = np.array([False, True, True, False, True])
    positions = entry_positions(frame, mask, horizon=300)

    assert positions.tolist() == [1]     # 마스크 통과 중 첫 초만


def test_entry_mask_matches_positions() -> None:
    frame = _frame([(20240304, "A", 90000), (20240304, "A", 90500),
                    (20240304, "B", 90000)])
    mask = np.ones(len(frame), bool)
    positions = entry_positions(frame, mask, horizon=300)

    assert entry_mask(frame, mask, horizon=300).sum() == len(positions)
    assert np.flatnonzero(entry_mask(frame, mask, horizon=300)).tolist() == positions.tolist()


def test_empty_mask_is_safe() -> None:
    frame = _frame([(20240304, "A", 90000)])
    assert entry_positions(frame, np.zeros(1, bool), horizon=300).size == 0


def test_minute_lane_uses_minute_arithmetic() -> None:
    # min 레인은 HHMM — 09:59 다음이 10:00 이고 간격은 1분이다.
    frame = _frame([(20250407, "A", 959), (20250407, "A", 1000), (20250407, "A", 1030)])
    positions = entry_positions(frame, np.ones(3, bool), horizon=30, time_digits=12)

    clock = frame["시분초"].to_numpy()[positions]
    assert clock.tolist() == [959, 1030]      # 10:00 은 보유 중(959+30분=10:29)


def test_deduper_matches_exact_on_simple_runs() -> None:
    """단순한 연속 구간에서는 벡터화 근사가 정확판과 같아야 한다."""
    from ai_strategy_loop.labeling.entries import EntryDeduper

    frame = _frame([(20240304, "A", 90000 + i) for i in range(10)]
                   + [(20240304, "B", 90000 + i) for i in range(5)]
                   + [(20240305, "A", 90000)])
    mask = np.ones(len(frame), bool)
    exact = entry_mask(frame, mask, horizon=300)
    fast = EntryDeduper(frame, horizon=300).apply(mask)

    assert fast.sum() == exact.sum() == 3        # (A,3/4일) + (B,3/4일)
    assert np.array_equal(fast, exact)


def test_deduper_respects_mask_and_is_idempotent() -> None:
    from ai_strategy_loop.labeling.entries import EntryDeduper

    frame = _frame([(20240304, "A", 90000 + i) for i in range(20)])
    deduper = EntryDeduper(frame, horizon=300)
    mask = np.zeros(len(frame), bool)
    mask[5:15] = True

    first = deduper.apply(mask)
    assert first.sum() == 1
    assert np.flatnonzero(first).tolist() == [5]        # 마스크 통과 중 첫 행
    assert np.array_equal(deduper.apply(first), first)  # 이미 걸러진 것은 그대로


def test_deduper_never_selects_more_than_mask() -> None:
    from ai_strategy_loop.labeling.entries import EntryDeduper

    rng = np.random.default_rng(5)
    rows = [(20240300 + d, chr(65 + s), 90000 + t)
            for d in range(3) for s in range(2) for t in range(0, 60, 3)]
    frame = _frame(rows)
    mask = rng.random(len(frame)) < 0.5
    fast = EntryDeduper(frame, horizon=300).apply(mask)

    assert fast.sum() <= mask.sum()
    assert (fast & ~mask).sum() == 0        # 마스크 밖을 고르지 않는다
