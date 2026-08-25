from __future__ import annotations

import inspect

from backtest.backengine_base import BackEngineBase
from utility.backtest_shared_memory import create_backtest_shared_memory_name


def test_shared_memory_names_are_unique_for_parallel_backtests() -> None:
    names = {
        create_backtest_shared_memory_name(engine_index)
        for _ in range(2)
        for engine_index in range(4)
    }

    assert len(names) == 8
    assert all(name.startswith("stom_backdata_") for name in names)


def test_backengine_uses_isolated_shared_memory_name() -> None:
    source = inspect.getsource(BackEngineBase.DataLoad)

    assert "create_backtest_shared_memory_name(self.gubun)" in source
    assert "name = f'backdata_{self.gubun}'" not in source
