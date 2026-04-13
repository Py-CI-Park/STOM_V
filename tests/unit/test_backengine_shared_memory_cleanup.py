import inspect

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
