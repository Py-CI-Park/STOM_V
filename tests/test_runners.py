"""
Runner contract tests for headless CLI execution paths.
"""

from __future__ import annotations

import queue
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from cli.runners.backtest_runner import HeadlessBacktestRunner
from cli.runners.optimize_runner import HeadlessOptimizeRunner
from cli.runners.trade_runner import HeadlessTradeRunner


def _prepare_tradelist_db(db_path: Path):
    con = sqlite3.connect(db_path)
    cursor = con.cursor()

    cursor.execute(
        """
        CREATE TABLE s_jangolist (
            "index" TEXT,
            "종목코드" TEXT,
            "보유수량" INTEGER,
            "평가손익" REAL
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO s_jangolist ("index", "종목코드", "보유수량", "평가손익")
        VALUES ('005930', '005930', 10, 12000.0)
        """
    )

    cursor.execute(
        """
        CREATE TABLE s_chegeollist (
            "주문번호" TEXT,
            "미체결수량" INTEGER,
            "주문구분" TEXT
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO s_chegeollist ("주문번호", "미체결수량", "주문구분")
        VALUES ('o-1', 3, '매수')
        """
    )
    cursor.execute(
        """
        INSERT INTO s_chegeollist ("주문번호", "미체결수량", "주문구분")
        VALUES ('o-2', 0, '매도')
        """
    )

    cursor.execute(
        """
        CREATE TABLE s_tradelist (
            "index" TEXT,
            "체결시간" TEXT,
            "수익금" REAL
        )
        """
    )
    cursor.execute(
        """
        INSERT INTO s_tradelist ("index", "체결시간", "수익금")
        VALUES ('005930', '20240102100000', 2500.0)
        """
    )

    con.commit()
    con.close()


class TestTradeRunner:
    def test_start_stop_status_state(self, monkeypatch):
        runner = HeadlessTradeRunner()
        monkeypatch.setattr(
            "cli.runners.trade_runner.load_settings_without_qt",
            lambda: {"mode": "test"},
        )

        assert runner.start_trading("stock") is True
        status = runner.get_status()
        assert status["stock"]["active"] is True
        assert runner.stop_trading("stock") is True
        assert runner.get_status()["stock"]["active"] is False
        assert runner.start_trading("unknown") is False

    def test_positions_orders_history_and_placeholder_boundaries(self, tmp_path: Path, monkeypatch):
        db_path = tmp_path / "tradelist.db"
        _prepare_tradelist_db(db_path)
        monkeypatch.setattr("cli.runners.trade_runner.DB_TRADELIST", str(db_path))

        runner = HeadlessTradeRunner()

        positions = runner.get_positions("stock")
        assert len(positions) == 1
        assert "table_name" in positions.columns

        pending_orders = runner.get_orders("stock")
        assert len(pending_orders) == 1
        assert pending_orders.iloc[0]["주문번호"] == "o-1"

        history = runner.get_trade_history("stock", "20240101", "20240131")
        assert len(history) == 1

        # 브로커 연동 미구현 경로는 성공을 반환하지 않아야 한다.
        assert runner.close_position("stock", code="005930") is False
        assert runner.cancel_order("stock", order_id="o-1") is False

    def test_close_position_close_all_returns_false_until_broker_integration(self, monkeypatch):
        runner = HeadlessTradeRunner()
        monkeypatch.setattr(
            runner,
            "get_positions",
            lambda _trade_type: pd.DataFrame([{"index": "005930", "보유수량": 3}]),
        )

        assert runner.close_position("stock", close_all=True) is False

    def test_cancel_order_cancel_all_returns_false_until_broker_integration(self, monkeypatch):
        runner = HeadlessTradeRunner()
        monkeypatch.setattr(
            runner,
            "get_orders",
            lambda _trade_type: pd.DataFrame([{"order_id": "o-100", "미체결수량": 1}]),
        )

        assert runner.cancel_order("stock", cancel_all=True) is False

    def test_close_position_with_missing_position_key_column_returns_false(self, monkeypatch):
        runner = HeadlessTradeRunner()
        monkeypatch.setattr(
            runner,
            "get_positions",
            lambda _trade_type: pd.DataFrame([{"ticker": "005930", "qty": 3}]),
        )

        assert runner.close_position("stock", code="005930") is False

    def test_cancel_order_with_missing_order_id_column_returns_false(self, monkeypatch):
        runner = HeadlessTradeRunner()
        monkeypatch.setattr(
            runner,
            "get_orders",
            lambda _trade_type: pd.DataFrame([{"code": "005930", "qty": 1}]),
        )

        assert runner.cancel_order("stock", order_id="o-100") is False


class TestOptimizeRunner:
    def test_save_and_query_optimization_job(self, tmp_path: Path):
        runner = HeadlessOptimizeRunner()
        backtest_db = tmp_path / "backtest.db"
        runner.con_bt = sqlite3.connect(backtest_db)

        job_id = runner._save_optimization_job(
            opt_type="grid",
            backtest_type="stock",
            buy_strategy="buy_a",
            sell_strategy="sell_a",
            start_date="20240101",
            end_date="20240131",
            betting=100000,
            params={"x": [1, 2, 3]},
        )

        status = runner.get_job_status(job_id)
        assert status["job_id"] == job_id
        assert status["status"] == "queued"

        jobs = runner.list_jobs()
        assert any(job["job_id"] == job_id for job in jobs)

        runner._cleanup()

    def test_status_and_list_without_db_connection(self):
        runner = HeadlessOptimizeRunner()
        assert runner.get_job_status("missing") == {"error": "Database not connected"}
        assert runner.list_jobs() == []

    def test_save_job_error_returns_error_prefix(self):
        class BrokenConnection:
            def cursor(self):
                raise sqlite3.OperationalError("cursor failure")

        runner = HeadlessOptimizeRunner()
        runner.con_bt = BrokenConnection()
        job_id = runner._save_optimization_job(
            opt_type="grid",
            backtest_type="stock",
            buy_strategy="buy_a",
            sell_strategy="sell_a",
            start_date="20240101",
            end_date="20240131",
            betting=100000,
            params={"x": [1, 2]},
        )
        assert job_id.startswith("error_")

    def test_run_grid_handles_module_load_failure(self, monkeypatch):
        runner = HeadlessOptimizeRunner()
        cleanup_called = {"value": False}

        def _raise_modules():
            raise RuntimeError("module load failure")

        def _mark_cleanup():
            cleanup_called["value"] = True

        monkeypatch.setattr("cli.runners.optimize_runner._load_optimize_modules", _raise_modules)
        monkeypatch.setattr(runner, "_cleanup", _mark_cleanup)

        result = runner.run_grid_optimization(
            backtest_type="stock",
            buy_strategy="buy_a",
            sell_strategy="sell_a",
            start_date="20240101",
            end_date="20240131",
            betting=100000,
        )
        assert result["success"] is False
        assert "module load failure" in result["error_message"]
        assert cleanup_called["value"] is True


class TestBacktestRunner:
    def test_invalid_backtest_type_fails_before_module_load(self, monkeypatch):
        runner = HeadlessBacktestRunner()
        runner.dict_set = {
            "주식타임프레임": True,
            "코인타임프레임": True,
            "백테주문관리적용": False,
            "거래소": "업비트",
        }

        def _must_not_be_called():
            raise AssertionError("backtest modules should not be loaded for invalid type")

        monkeypatch.setattr("cli.runners.backtest_runner._load_backtest_modules", _must_not_be_called)

        assert (
            runner.start_backtest(
                backtest_type="invalid",
                buy_strategy="buy_a",
                sell_strategy="sell_a",
                start_date="20240101",
                end_date="20240131",
            )
            is False
        )

    def test_create_queues_initializes_core_queues(self):
        runner = HeadlessBacktestRunner()
        runner._create_queues()

        assert runner.windowQ is not None
        assert runner.soundQ is not None
        assert runner.totalQ is not None
        assert runner.backQ is not None
        assert runner.liveQ is not None
        assert runner.teleQ is not None

    def test_start_backtest_returns_false_when_settings_load_fails(self, monkeypatch):
        runner = HeadlessBacktestRunner()
        runner.dict_set = None
        monkeypatch.setattr(runner, "load_settings", lambda: False)

        assert (
            runner.start_backtest(
                backtest_type="stock",
                buy_strategy="buy_a",
                sell_strategy="sell_a",
                start_date="20240101",
                end_date="20240131",
            )
            is False
        )

    def test_monitor_results_stops_when_process_terminates(self):
        class DeadProcess:
            def is_alive(self):
                return False

        runner = HeadlessBacktestRunner()
        runner.windowQ = queue.Queue()
        runner.soundQ = queue.Queue()
        runner.backtest_process = DeadProcess()

        # Covers tuple-handling branch before loop exits by dead process.
        runner.windowQ.put(("progress", 1, 2, 3))
        runner._monitor_results()

    def test_monitor_results_handles_queue_timeout_gracefully(self):
        class TimeoutQueue:
            def __init__(self):
                self.calls = 0

            def empty(self):
                return False

            def get(self, timeout=0.1):
                self.calls += 1
                raise queue.Empty()

        runner = HeadlessBacktestRunner()
        timeout_queue = TimeoutQueue()
        runner.windowQ = timeout_queue
        runner.soundQ = queue.Queue()

        # Queue timeout(Empty) 예외가 발생해도 모니터 루프가 중단되어야 한다.
        runner._monitor_results()
        assert timeout_queue.calls == 1

    def test_kill_processes_terminates_alive_processes(self):
        class DummyProcess:
            def __init__(self):
                self._alive = True
                self.terminated = False
                self.killed = False

            def is_alive(self):
                return self._alive

            def terminate(self):
                self.terminated = True
                self._alive = False

            def join(self, timeout=None):
                return None

            def kill(self):
                self.killed = True
                self._alive = False

        runner = HeadlessBacktestRunner()
        engine_proc = DummyProcess()
        subtotal_proc = DummyProcess()
        main_proc = DummyProcess()

        runner.back_eprocs = [engine_proc]
        runner.back_sprocs = [subtotal_proc]
        runner.backtest_process = main_proc

        runner.kill_processes()

        assert engine_proc.terminated is True
        assert subtotal_proc.terminated is True
        assert main_proc.terminated is True

    def test_kill_processes_calls_kill_when_join_timeout(self):
        class StubbornProcess:
            def __init__(self):
                self.terminate_calls = 0
                self.kill_calls = 0
                self.join_calls = []

            def is_alive(self):
                return True

            def terminate(self):
                self.terminate_calls += 1

            def join(self, timeout=None):
                self.join_calls.append(timeout)

            def kill(self):
                self.kill_calls += 1

        runner = HeadlessBacktestRunner()
        engine_proc = StubbornProcess()
        subtotal_proc = StubbornProcess()
        main_proc = StubbornProcess()

        runner.back_eprocs = [engine_proc]
        runner.back_sprocs = [subtotal_proc]
        runner.backtest_process = main_proc

        runner.kill_processes()

        assert engine_proc.terminate_calls == 1
        assert subtotal_proc.terminate_calls == 1
        assert main_proc.terminate_calls == 1
        assert engine_proc.kill_calls == 1
        assert subtotal_proc.kill_calls == 1
        assert main_proc.kill_calls == 1
