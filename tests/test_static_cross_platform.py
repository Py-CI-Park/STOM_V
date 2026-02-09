"""
Cross-platform regression tests for utility.static fallbacks.
"""

from __future__ import annotations

import logging

import utility.static as static


def test_get_logger_falls_back_without_loguru(monkeypatch):
    monkeypatch.setattr(static, "_loguru_logger", None)
    logger = static.get_logger("fallback-logger")
    assert isinstance(logger, logging.Logger)


def test_win_proc_alive_returns_false_without_psutil(monkeypatch):
    monkeypatch.setattr(static, "psutil", None)
    assert static.win_proc_alive("dummy-process") is False


def test_qtest_qwait_uses_sleep_without_pyqt(monkeypatch):
    recorded = {}

    monkeypatch.setattr(static, "QTest", None)
    monkeypatch.setattr(static.time, "sleep", lambda sec: recorded.setdefault("sec", sec))

    static.qtest_qwait(0.25)
    assert recorded["sec"] == 0.25


def test_read_key_uses_env_without_windows_registry(monkeypatch):
    monkeypatch.setattr(static, "reg", None)
    monkeypatch.setenv("STOM_EN_KEY", "test-fallback-key")
    assert static.read_key() == "test-fallback-key"


def test_cme_normal_open_returns_false_without_exchange_calendars(monkeypatch):
    monkeypatch.setattr(static, "ec", None)
    assert static.cme_normal_open() is False
