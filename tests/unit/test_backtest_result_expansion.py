import sqlite3

import numpy as np
import pandas as pd
import pytest

from backtest import backtest as backtest_module
from backtest.back_subtotal import BackSubTotal
from backtest.back_static import (
    GetResultDataframe,
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_EXTRA_COLUMNS,
    get_trade_result_snapshot,
)


def test_get_trade_result_snapshot_defaults():
    snapshot = get_trade_result_snapshot()

    assert list(snapshot.keys()) == TRADE_RESULT_B_COLUMNS
    assert all(value == 0 for value in snapshot.values())


def test_get_result_dataframe_preserves_trade_result_extra_columns():
    extra_values = list(range(1, len(TRADE_RESULT_EXTRA_COLUMNS) + 1))
    list_tsg = [[
        '20250101100000',
        '테스트종목',
        123456789,
        20250101100000,
        20250101100500,
        5,
        1000,
        1010,
        100000,
        101000,
        1.0,
        1000,
        '기본매도',
        '',
        *extra_values,
    ]]
    arry_bct = np.array([
        [20250101100000, 1, 100000],
        [20250101100500, 0, 0],
    ], dtype='float64')

    df_tsg, df_bct = GetResultDataframe('S', list_tsg, arry_bct)

    assert list(df_tsg.columns[-len(TRADE_RESULT_EXTRA_COLUMNS):]) == TRADE_RESULT_EXTRA_COLUMNS
    assert df_tsg.iloc[0]['B_현재가'] == 1
    assert df_tsg.iloc[0]['B_분봉저가'] == len(TRADE_RESULT_B_COLUMNS)
    assert df_tsg.iloc[0]['S_현재가'] == len(TRADE_RESULT_B_COLUMNS) + 1
    assert df_tsg.iloc[0]['S_매도총잔량'] == len(TRADE_RESULT_B_COLUMNS) + len(TRADE_RESULT_S_COLUMNS)
    assert df_tsg.iloc[0]['R_MAE'] == len(TRADE_RESULT_EXTRA_COLUMNS)
    assert df_tsg.iloc[0]['수익금합계'] == 1000
    assert list(df_bct.columns) == ['보유종목수', '보유금액']


def test_backsubtotal_collect_data_preserves_extra_columns():
    subtotal = BackSubTotal.__new__(BackSubTotal)
    subtotal.dummy_tsg = {}
    subtotal.ddict_tsg = {}
    subtotal.ddict_bct = {}
    subtotal.arry_bct_ = np.array([
        [20250101100000, 0, 0],
        [20250101100500, 0, 0],
    ], dtype='float64')
    subtotal.buystd = True
    subtotal.opti_turn = 2

    extra_values = list(range(1, len(TRADE_RESULT_EXTRA_COLUMNS) + 1))
    data = (
        '백테결과',
        '테스트종목',
        123456789,
        20250101100000,
        20250101100500,
        5,
        1000,
        1010,
        100000,
        101000,
        1.0,
        1000,
        '기본매도',
        '',
        True,
        *extra_values,
        0,
        0,
    )

    subtotal.CollectData(data)

    detail_row = subtotal.ddict_tsg[0][0][0]
    assert len(detail_row) == 14 + len(TRADE_RESULT_EXTRA_COLUMNS)
    assert detail_row[-len(TRADE_RESULT_EXTRA_COLUMNS):] == extra_values
    assert subtotal.ddict_bct[0][0][:, 1].tolist() == [1.0, 1.0]
    assert subtotal.ddict_bct[0][0][:, 2].tolist() == [100000.0, 100000.0]


class _DummyQueue(list):
    def put(self, item):
        self.append(item)


def test_total_report_writes_extended_detail_csv_and_db(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(backtest_module, 'DB_BACKTEST', str(tmp_path / 'backtest.db'))
    monkeypatch.setattr(backtest_module, 'str_ymdhms', lambda: '20260310120000')
    monkeypatch.setattr(
        backtest_module,
        'GetResult',
        lambda *args, **kwargs: (1, 1.0, 1, 0, 100.0, 60.0, 1.0, 1.0, 10, 1, 100000, 10.0, 1.0)
    )
    monkeypatch.setattr(backtest_module, 'AddMdd', lambda _arry, result: result + (0.0, 0))
    monkeypatch.setattr(backtest_module, 'bootstrap_test', lambda *_args, **_kwargs: np.array([0.01, 0.02]))
    monkeypatch.setattr(backtest_module, 'PlotShow', lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.time, 'sleep', lambda *_args, **_kwargs: None)

    total = backtest_module.Total.__new__(backtest_module.Total)
    total.wq = _DummyQueue()
    total.sq = _DummyQueue()
    total.tq = _DummyQueue()
    total.mq = _DummyQueue()
    total.lq = _DummyQueue()
    total.teleQ = _DummyQueue()
    total.bstq_list = []
    total.backname = '테스트백테스트'
    total.ui_gubun = 'S'
    total.gubun = 'stock'
    total.market_text = '주식'
    total.dict_set = {
        '스톰라이브': False,
        '주식타임프레임': True,
        '그래프저장하지않기': True,
        '그래프띄우지않기': True,
    }
    total.savename = 'stock_bt'
    total.betting = 100000
    total.avgtime = 60
    total.startday = 20260310
    total.endday = 20260310
    total.starttime = 90000
    total.endtime = 90100
    total.buystg_name = '테스트전략'
    total.buystg = 'if 매수:\n    pass'
    total.sellstg = 'if 매도:\n    pass'
    total.dict_cn = {}
    total.blacklist = False
    total.day_count = 1
    total.schedul = False
    total.back_club = False
    total.insertlist = []

    extra_values = list(range(1, len(TRADE_RESULT_EXTRA_COLUMNS) + 1))
    list_tsg = [[
        20260310090000,
        '테스트종목',
        123456789,
        20260310090000,
        20260310090100,
        60,
        1000,
        1010,
        1000,
        1010,
        1.0,
        10,
        '전략매도',
        '20260310090000;1000',
        *extra_values,
    ]]
    arry_bct = np.array([[20260310090100, 1, 1000]], dtype='float64')

    with pytest.raises(SystemExit):
        total.Report(list_tsg, arry_bct)

    csv_path = tmp_path / 'backtest' / 'csv' / 'stock_bt_테스트전략_20260310120000.csv'
    assert csv_path.exists()

    df_csv = pd.read_csv(csv_path, encoding='utf-8-sig')
    assert TRADE_RESULT_EXTRA_COLUMNS == df_csv.columns[-len(TRADE_RESULT_EXTRA_COLUMNS):].tolist()

    table_name = 'stock_bt_테스트전략_20260310120000'
    con = sqlite3.connect(tmp_path / 'backtest.db')
    try:
        tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert table_name in tables
