"""S0: _build_warm_btconfig의 timeframe+full_session 인지 end_time 선택 검증(백테 실행 0).

OFF(기본)=byte-identical(end_time=92800), min+full_session_enabled=풀세션 151900,
tick은 토글과 무관(항상 bt_universe_end_time). start_time은 항상 90000.
"""
from types import SimpleNamespace

import cli.warm_session as warm
from ai_strategy_loop.config import LoopConfig
from ai_strategy_loop.controller import loop as L


def _bt(**kw):
    return L._build_warm_btconfig(LoopConfig(**kw))


class TestWarmSessionWindow:
    def test_default_off_byte_identical_min(self):
        bt = _bt(bt_timeframe="min")
        assert bt.end_time == 92800
        assert bt.start_time == 90000

    def test_default_off_byte_identical_tick(self):
        bt = _bt(bt_timeframe="tick")
        assert bt.end_time == 92800
        assert bt.start_time == 90000

    def test_min_full_session_opens_end_time(self):
        bt = _bt(bt_timeframe="min", full_session_enabled=True)
        assert bt.end_time == 151900
        assert bt.start_time == 90000

    def test_tick_ignores_full_session_toggle(self):
        bt = _bt(bt_timeframe="tick", full_session_enabled=True)
        assert bt.end_time == 92800

    def test_custom_min_end_time_respected(self):
        bt = _bt(bt_timeframe="min", full_session_enabled=True,
                 bt_min_universe_end_time=150000)
        assert bt.end_time == 150000


def _warm_config(engine_count=3):
    return SimpleNamespace(
        engine_count=engine_count,
        verbose=False,
        betting=1000000,
        timeout=10,
    )


class _DummyDrainer:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


class _DummyProc:
    exitcode = 0

    def __init__(self, alive=False):
        self._alive = alive

    def join(self, timeout=None):
        pass

    def is_alive(self):
        return self._alive


def _assert_non_negative_timing(timing, keys):
    for key in keys:
        assert key in timing
        assert timing[key] >= 0.0


def test_warm_prepare_timing_metadata_is_additive(monkeypatch):
    session = warm.WarmBacktestSession(_warm_config(engine_count=4))
    monkeypatch.setattr(warm, "_register_signals", lambda: None)
    monkeypatch.setattr(warm, "_ensure_cli_db_env", lambda: None)
    monkeypatch.setattr(
        warm, "_sync_dict_set", lambda config: {"백테매수시간기준": "체결시간"}
    )
    monkeypatch.setattr(warm, "QueueDrainer", _DummyDrainer)
    monkeypatch.setattr(session, "_create_queues", lambda: None)
    monkeypatch.setattr(session, "_spawn_subtotals", lambda: None)
    monkeypatch.setattr(session, "_spawn_engines", lambda: None)
    monkeypatch.setattr(
        session, "_load_market_data", lambda: {"status": "ok", "dict_info": {}}
    )
    monkeypatch.setattr(
        session,
        "_send_engine_data",
        lambda data: setattr(session, "back_count", 2) or {"status": "ok"},
    )

    result = session.prepare()

    assert result["status"] == "ok"
    assert result["back_count"] == 2
    timing = result["timing"]
    assert timing["status"] == "ok"
    assert timing["engine_count"] == 4
    assert timing["back_count"] == 2
    _assert_non_negative_timing(
        timing,
        [
            "prepare_elapsed",
            "spawn_subtotals_elapsed",
            "spawn_engines_elapsed",
            "market_data_load_elapsed",
            "engine_data_send_elapsed",
        ],
    )


def test_warm_run_timing_metadata_is_additive(monkeypatch):
    session = warm.WarmBacktestSession(_warm_config(engine_count=5))
    session._prepared = True
    session.back_count = 3
    session.back_eques = []
    monkeypatch.setattr(warm, "_get_backtest_last_rowid", lambda: 10)
    monkeypatch.setattr(session, "_clear_run_queues", lambda: None)
    monkeypatch.setattr(session, "_spawn_backtest", lambda *args, **kwargs: _DummyProc())
    monkeypatch.setattr(
        session,
        "_collect_run_result",
        lambda *args, **kwargs: {
            "status": "success",
            "message": "백테스트 완료",
            "metrics": {"total_profit": 1.0},
            "csv_path": "out.csv",
        },
    )

    result = session.run("BUY", "SELL", timeout=1)

    assert result["status"] == "success"
    assert result["metrics"] == {"total_profit": 1.0}
    timing = result["timing"]
    assert timing["status"] == "success"
    assert timing["engine_count"] == 5
    assert timing["back_count"] == 3
    assert timing["timeout"] is False
    _assert_non_negative_timing(
        timing,
        [
            "run_elapsed",
            "timeout_count",
            "recovery_attempts",
            "recovery_success_count",
            "recovery_failure_count",
            "nuclear_fallback_count",
        ],
    )


def test_warm_run_timeout_timing_tracks_recovery_counters(monkeypatch):
    session = warm.WarmBacktestSession(_warm_config(engine_count=2))
    session._prepared = True
    session.back_count = 2
    session.back_eques = []
    monkeypatch.setattr(warm, "_get_backtest_last_rowid", lambda: 10)
    monkeypatch.setattr(session, "_clear_run_queues", lambda: None)
    monkeypatch.setattr(session, "_spawn_backtest", lambda *args, **kwargs: _DummyProc(alive=True))
    monkeypatch.setattr(
        session,
        "_recover_after_failure",
        lambda proc, timeout_hit, error_message: {
            "status": "error",
            "message": error_message,
            "metrics": None,
        },
    )

    result = session.run("BUY", "SELL", timeout=1)

    assert result["status"] == "error"
    timing = result["timing"]
    assert timing["status"] == "error"
    assert timing["timeout"] is True
    assert timing["timeout_count"] == 1
    assert timing["engine_count"] == 2
    assert timing["back_count"] == 2
    assert timing["run_elapsed"] >= 0.0


def test_warm_session_page_data_projects_prepare_and_last_run_timing():
    prepare = {"timing": {"prepare_elapsed": 0.1, "status": "ok"}}
    last_run = {"timing": {"run_elapsed": 0.2, "status": "success"}}

    page_data = L._warm_session_page_data(prepare=prepare, last_run=last_run)

    assert page_data == {
        "warm_session": {
            "prepare": {"prepare_elapsed": 0.1, "status": "ok"},
            "prepare_elapsed_sec": 0.1,
            "last_run": {"run_elapsed": 0.2, "status": "success"},
            "last_run_elapsed_sec": 0.2,
            "run_elapsed_sec": 0.2,
            "status": "success",
        }
    }
