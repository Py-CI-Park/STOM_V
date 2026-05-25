"""US-004 Phase 2a — holdout 분할 토글 단위 테스트 (RV2-4).

검증:
  OFF -> holdout_* None, train = 전체 입력 윈도우.
  ON  -> 끝에서 최근 N일을 holdout으로 떼고, train은 그 앞부분. 경계값 확인.
"""

import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.fitness.holdout import HoldoutSplit, split_window


# ============================================================
# OFF: 분할하지 않음
# ============================================================

def test_disabled_returns_full_range_train_and_none_holdout():
    """enabled=False -> train=전체, holdout_*=None."""
    split = split_window(20260101, 20260131, enabled=False, holdout_recent_days=30)
    assert isinstance(split, HoldoutSplit)
    assert split.train_start == 20260101
    assert split.train_end == 20260131
    assert split.holdout_start is None
    assert split.holdout_end is None


def test_disabled_ignores_holdout_days_value():
    """OFF면 holdout_recent_days 값과 무관하게 전체 train."""
    split = split_window(20260101, 20260630, enabled=False, holdout_recent_days=90)
    assert split.train_start == 20260101
    assert split.train_end == 20260630
    assert split.holdout_start is None
    assert split.holdout_end is None


# ============================================================
# ON: 끝에서 최근 N일을 holdout으로 예약
# ============================================================

def test_enabled_reserves_last_n_days_as_holdout():
    """enabled=True -> holdout=마지막 N일, train=나머지 앞부분.

    윈도우 2026-01-01 .. 2026-03-31, N=30:
      holdout = 2026-03-02 .. 2026-03-31 (30일, end 포함)
      train   = 2026-01-01 .. 2026-03-01
    """
    split = split_window(20260101, 20260331, enabled=True, holdout_recent_days=30)
    assert split.train_start == 20260101
    assert split.train_end == 20260301
    assert split.holdout_start == 20260302
    assert split.holdout_end == 20260331


def test_enabled_holdout_length_is_exactly_n_days():
    """holdout 구간 길이(end 포함)가 정확히 N일이다."""
    from datetime import date

    split = split_window(20260101, 20260331, enabled=True, holdout_recent_days=30)
    hs = split.holdout_start
    he = split.holdout_end
    d_start = date(hs // 10000, (hs // 100) % 100, hs % 100)
    d_end = date(he // 10000, (he // 100) % 100, he % 100)
    assert (d_end - d_start).days + 1 == 30


def test_enabled_train_and_holdout_are_contiguous_and_non_overlapping():
    """train_end 다음 날이 holdout_start (겹치지 않고 연속)."""
    from datetime import date, timedelta

    split = split_window(20260101, 20260331, enabled=True, holdout_recent_days=30)
    te = split.train_end
    hs = split.holdout_start
    d_train_end = date(te // 10000, (te // 100) % 100, te % 100)
    d_holdout_start = date(hs // 10000, (hs // 100) % 100, hs % 100)
    assert d_train_end + timedelta(days=1) == d_holdout_start


def test_enabled_but_holdout_swallows_whole_window_falls_back_to_full_train():
    """N이 윈도우보다 크면 분할 불가 -> OFF처럼 전체 train, holdout None."""
    # 윈도우 10일인데 holdout 30일 요청 -> 분할 무의미.
    split = split_window(20260101, 20260110, enabled=True, holdout_recent_days=30)
    assert split.train_start == 20260101
    assert split.train_end == 20260110
    assert split.holdout_start is None
    assert split.holdout_end is None


def test_enabled_with_nonpositive_days_falls_back_to_full_train():
    """holdout_recent_days <= 0 -> 전체 train (방어)."""
    split = split_window(20260101, 20260331, enabled=True, holdout_recent_days=0)
    assert split.train_start == 20260101
    assert split.train_end == 20260331
    assert split.holdout_start is None
    assert split.holdout_end is None


def test_config_default_holdout_recent_days_is_30():
    """LoopConfig.holdout_recent_days 기본값은 30."""
    assert LoopConfig().holdout_recent_days == 30


def test_config_default_graduation_holdout_is_off():
    """graduation_holdout 기본값은 OFF(False)."""
    assert LoopConfig().graduation_holdout is False
