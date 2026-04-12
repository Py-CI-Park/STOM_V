import numpy as np

from backtest.backengine_base import BackEngineBase


def test_tick_day_values_use_yyyymmdd_from_tick_index():
    indexes = np.array([20250408090000, 20250408151800, 20250409090000], dtype=np.int64)

    assert BackEngineBase.GetDayValues(indexes, is_tick=True).tolist() == [
        20250408,
        20250408,
        20250409,
    ]


def test_minute_day_values_use_yyyymmdd_from_minute_index():
    indexes = np.array([202504080900, 202504081518, 202504090900], dtype=np.int64)

    assert BackEngineBase.GetDayValues(indexes, is_tick=False).tolist() == [
        20250408,
        20250408,
        20250409,
    ]
