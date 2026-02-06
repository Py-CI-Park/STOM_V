"""
Runner contract tests for headless CLI execution paths.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

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
