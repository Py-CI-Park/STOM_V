"""
Adapter unit tests for settings/queue helper modules.
"""

from __future__ import annotations

import io
import logging
from queue import Empty

import pandas as pd

from cli.adapters import queue_adapter, settings_adapter


def test_get_database_paths_contains_core_keys():
    paths = settings_adapter.get_database_paths()
    assert "setting" in paths
    assert "backtest" in paths
    assert "tradelist" in paths
    assert "strategy" in paths
    assert len(paths) >= 10


def test_get_blacklists_uses_loader(monkeypatch):
    monkeypatch.setattr(
        settings_adapter,
        "_load_blacklists",
        lambda: (["005930"], ["ES"], ["BTC"]),
    )
    blacklists = settings_adapter.get_blacklists()
    assert blacklists == {"stock": ["005930"], "future": ["ES"], "coin": ["BTC"]}


def test_safe_get_handles_missing_column_or_index():
    df = pd.DataFrame({"a": [10]}, index=["row0"])
    en_key = b"key"

    assert settings_adapter._safe_get(df, "missing", "row0", en_key) is None
    assert settings_adapter._safe_get(df, "a", "rowX", en_key) is None
    assert settings_adapter._safe_get(df, "a", "row0", en_key) == 10


def test_safe_get_decrypt_path(monkeypatch):
    df = pd.DataFrame({"enc": ["cipher"]}, index=[1])
    monkeypatch.setattr(settings_adapter, "de_text", lambda key, val: f"dec:{val}")
    value = settings_adapter._safe_get(df, "enc", 1, b"k", decrypt=True)
    assert value == "dec:cipher"


def test_parse_ratios_success_and_failure():
    df_ok = pd.DataFrame({"ratio": ["0.1;0.2;0.7"]}, index=[0])
    assert settings_adapter._parse_ratios(df_ok, "ratio", 0) == [0.1, 0.2, 0.7]

    df_bad = pd.DataFrame({"ratio": ["bad;value"]}, index=[0])
    assert settings_adapter._parse_ratios(df_bad, "ratio", 0) == []


def test_load_settings_without_qt_minimal(monkeypatch):
    df_m = pd.DataFrame(
        {
            "증권사": ["키움"],
            "바이낸스선물변동레버리지값": ["1;2^3;4"],
        },
        index=[0],
    )
    df_s = pd.DataFrame({"주식모의투자": [True]}, index=[0])
    df_c = pd.DataFrame({"코인모의투자": [False]}, index=[0])
    df_sa = pd.DataFrame()
    df_ca = pd.DataFrame()
    df_t = pd.DataFrame()
    df_sb = pd.DataFrame()
    df_ss = pd.DataFrame()
    df_cb = pd.DataFrame()
    df_cs = pd.DataFrame()
    df_e = pd.DataFrame({"창위치": ["10;20;30;40"]}, index=[0])
    df_b = pd.DataFrame({"보조지표설정": ["1;2.5;3"]}, index=[0])

    monkeypatch.setattr(settings_adapter, "read_key", lambda: b"dummy-key")
    monkeypatch.setattr(
        settings_adapter,
        "_load_database_records",
        lambda: (
            df_m,
            df_s,
            df_c,
            df_sa,
            df_ca,
            df_t,
            df_sb,
            df_ss,
            df_cb,
            df_cs,
            df_e,
            df_b,
        ),
    )
    monkeypatch.setattr(settings_adapter, "_load_blacklists", lambda: (["A"], ["B"], ["C"]))

    loaded = settings_adapter.load_settings_without_qt()
    assert loaded["키"] == b"dummy-key"
    assert loaded["증권사"] == "키움"
    assert loaded["바이낸스선물변동레버리지값"] == [[1.0, 2.0], [3.0, 4.0]]
    assert loaded["보조지표설정"] == [1, 2.5, 3]
    assert loaded["창위치"] == [10, 20, 30, 40]
    assert loaded["주식블랙리스트"] == ["A"]
    assert loaded["해선블랙리스트"] == ["B"]
    assert loaded["코인블랙리스트"] == ["C"]


def test_logging_queue_put_logs_and_stores(caplog):
    logger = logging.getLogger("test-logging-queue")
    caplog.set_level(logging.INFO, logger=logger.name)
    q = queue_adapter.LoggingQueue(logger, "window")

    payload = (3, "hello-log")
    q.put(payload)

    assert q.get(timeout=0.1) == payload
    assert "hello-log" in caplog.text


def test_null_queue_get_raises_empty():
    q = queue_adapter.NullQueue()
    q.put("ignored")
    try:
        q.get(timeout=0.1)
        assert False, "NullQueue.get() must raise Empty"
    except Empty:
        assert True


def test_progress_queue_updates_progress(monkeypatch):
    fake_stdout = io.StringIO()
    monkeypatch.setattr(queue_adapter.sys, "stdout", fake_stdout)

    q = queue_adapter.ProgressQueue(show_progress=True)
    q.put((8, 5, 10))

    assert q.last_progress == 50
    assert q.get(timeout=0.1) == (8, 5, 10)


def test_progress_queue_no_output_when_disabled(monkeypatch):
    fake_stdout = io.StringIO()
    monkeypatch.setattr(queue_adapter.sys, "stdout", fake_stdout)

    q = queue_adapter.ProgressQueue(show_progress=False)
    q.put((8, 5, 10))

    assert q.last_progress == -1
    assert q.get(timeout=0.1) == (8, 5, 10)


def test_cli_queue_adapter_factory_methods():
    adapter = queue_adapter.CLIQueueAdapter(verbose=False, show_progress=False)

    assert isinstance(adapter.create_window_queue(), queue_adapter.LoggingQueue)
    assert isinstance(adapter.create_sound_queue(), queue_adapter.NullQueue)
    assert isinstance(adapter.create_progress_queue(), queue_adapter.ProgressQueue)
    assert isinstance(adapter.create_tele_queue(), queue_adapter.NullQueue)
    assert isinstance(adapter.create_live_queue(), queue_adapter.NullQueue)


def test_cli_queue_adapter_process_queue_message_and_completion(monkeypatch):
    adapter = queue_adapter.CLIQueueAdapter(verbose=False, show_progress=True)

    called = {"value": False}

    def _capture_progress(current, total):
        called["value"] = (current, total)

    monkeypatch.setattr(adapter, "_show_progress", _capture_progress)

    assert adapter.process_queue_message((8, 2, 10, 0)) is False
    assert called["value"] == (2, 10)

    assert adapter.process_queue_message((46, {"row": 1})) is False
    assert adapter.results[-1] == {"row": 1}

    assert adapter.process_queue_message((6, "COMPLETE")) is True
    assert adapter.completion_detected is True


def test_cli_queue_adapter_completion_helpers():
    adapter = queue_adapter.CLIQueueAdapter(verbose=False, show_progress=False)

    assert adapter.process_queue_message("작업 완료") is True
    assert adapter.is_completion_message("STOP") is True
    assert adapter.is_completion_message((6, "COMPLETE")) is True
    assert adapter.is_completion_message((46, {"detail": "x"})) is False
