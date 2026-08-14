import inspect
from queue import Queue

from backtest.backengine_base import BackEngineBase


def test_backstop_cleans_up_shared_memory():
    source = inspect.getsource(BackEngineBase.BackStop)

    assert "self.CleanupSharedMemory()" in source


def test_backtest_normal_completion_does_not_cleanup_shared_memory():
    source = inspect.getsource(BackEngineBase.BackTest)

    assert "self.CleanupSharedMemory()" not in source


def test_cleanup_shared_memory_unlinks_segments():
    source = inspect.getsource(BackEngineBase.CleanupSharedMemory)

    assert "unlink()" in source
    assert "FileNotFoundError" in source


def test_strategy_error_notifies_parent_instead_of_waiting_for_timeout():
    engine = BackEngineBase.__new__(BackEngineBase)
    engine.CleanupSharedMemory = lambda: None
    engine.back_type = "백테스트"
    engine.gubun = 1
    engine.tq = Queue()
    engine.bq = Queue()
    engine.BackStop(3)
    assert engine.tq.get_nowait() == "백테중지"
