"""
Schema adapter contract tests.
"""

from __future__ import annotations

import sqlite3

from cli.adapters.schema_adapter import (
    detect_backtest_order_column,
    detect_strategy_name_column,
    get_tradelist_tables,
    list_columns,
    list_tables,
    table_exists,
)


def test_table_and_column_helpers():
    con = sqlite3.connect(":memory:")
    con.execute('CREATE TABLE "sample" ("id" INTEGER, "name" TEXT)')

    assert table_exists(con, "sample") is True
    assert "sample" in list_tables(con)
    assert list_columns(con, "sample") == ["id", "name"]
    con.close()


def test_detect_backtest_order_column_priority_created_at():
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY,
            created_at TEXT,
            datetime TEXT
        )
        """
    )
    assert detect_backtest_order_column(con, "backtest_results") == "created_at"
    con.close()


def test_detect_backtest_order_column_fallback_to_datetime():
    con = sqlite3.connect(":memory:")
    con.execute(
        """
        CREATE TABLE backtest_results (
            id INTEGER PRIMARY KEY,
            datetime TEXT
        )
        """
    )
    assert detect_backtest_order_column(con, "backtest_results") == "datetime"
    con.close()


def test_detect_strategy_name_column_variants():
    con = sqlite3.connect(":memory:")
    con.execute('CREATE TABLE stockbuy ("index" TEXT, "코드" TEXT)')
    con.execute('CREATE TABLE stocksell ("name" TEXT, "코드" TEXT)')
    con.execute('CREATE TABLE coinbuy ("전략명" TEXT, "코드" TEXT)')

    assert detect_strategy_name_column(con, "stockbuy") == "index"
    assert detect_strategy_name_column(con, "stocksell") == "name"
    assert detect_strategy_name_column(con, "coinbuy") == "전략명"
    con.close()


def test_get_tradelist_tables_resolution_by_kind_and_asset_type():
    con = sqlite3.connect(":memory:")
    con.execute('CREATE TABLE s_jangolist ("index" TEXT)')
    con.execute('CREATE TABLE c_jangolist ("index" TEXT)')
    con.execute('CREATE TABLE c_jangolist_future ("index" TEXT)')
    con.execute('CREATE TABLE f_chegeollist ("index" TEXT)')

    assert get_tradelist_tables(con, "positions", "stock") == ["s_jangolist"]
    assert get_tradelist_tables(con, "positions", "coin") == ["c_jangolist", "c_jangolist_future"]
    assert get_tradelist_tables(con, "orders", "future") == ["f_chegeollist"]

    merged = get_tradelist_tables(con, "positions")
    assert merged == ["s_jangolist", "c_jangolist", "c_jangolist_future"]
    con.close()
