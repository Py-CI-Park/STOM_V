import json
from queue import Queue

from backtest.backengine_base import _emit_engine_protocol_checkpoint


def test_engine_protocol_checkpoint_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("STOM_CLI_BACKTEST_PROTOCOL_DIAG", raising=False)
    queue = Queue()
    _emit_engine_protocol_checkpoint(queue, 3, "engine_started", {"code": "A"})
    assert queue.empty()


def test_engine_protocol_checkpoint_is_bounded_and_identifies_worker(monkeypatch):
    monkeypatch.setenv("STOM_CLI_BACKTEST_PROTOCOL_DIAG", "1")
    queue = Queue()
    _emit_engine_protocol_checkpoint(
        queue,
        3,
        "engine_strategy_progress",
        {"code": "A" * 200, "tick_count": 12000, "unsafe": object()},
    )
    _, message = queue.get_nowait()
    assert message.startswith("[CLI_DIAG] ")
    payload = json.loads(message[len("[CLI_DIAG] "):])
    assert payload["source"] == "BackEngine:3"
    assert payload["checkpoint"] == "engine_strategy_progress"
    assert payload["detail"]["tick_count"] == 12000
    assert len(payload["detail"]["code"]) == 128
    assert len(payload["detail"]["unsafe"]) <= 128


def test_engine_protocol_checkpoint_bounds_exception_text(monkeypatch):
    monkeypatch.setenv("STOM_CLI_BACKTEST_PROTOCOL_DIAG", "1")
    queue = Queue()
    _emit_engine_protocol_checkpoint(
        queue, 0, "engine_strategy_exception", {"error": "E" * 500}
    )
    _, message = queue.get_nowait()
    payload = json.loads(message[len("[CLI_DIAG] "):])
    assert payload["detail"]["error"] == "E" * 128
