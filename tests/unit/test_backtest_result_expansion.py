import sqlite3

import numpy as np
import pandas as pd
import pytest

from backtest import backtest as backtest_module
from backtest.backengine_base import BackEngineBase
from backtest.back_subtotal import BackSubTotal
from backtest.back_static import (
    GetResultDataframe,
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_EXTRA_COLUMNS,
    get_trade_result_snapshot,
    get_trade_info,
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
    # v2 확장(QSP1 P1)으로 B 목록 끝이 분봉저가→RSI 로 바뀌었다. "마지막 B 컬럼의 값 =
    #   B 컬럼 수" 라는 원 의도를 이름 하드코딩 없이 검사한다(추후 확장에도 불변).
    assert df_tsg.iloc[0][TRADE_RESULT_B_COLUMNS[-1]] == len(TRADE_RESULT_B_COLUMNS)
    assert df_tsg.iloc[0]['B_분봉저가'] == TRADE_RESULT_B_COLUMNS.index('B_분봉저가') + 1
    assert df_tsg.iloc[0]['S_현재가'] == len(TRADE_RESULT_B_COLUMNS) + 1
    assert df_tsg.iloc[0]['S_매도총잔량'] == len(TRADE_RESULT_B_COLUMNS) + len(TRADE_RESULT_S_COLUMNS)
    assert df_tsg.iloc[0]['R_MAE'] == len(TRADE_RESULT_EXTRA_COLUMNS)
    assert df_tsg.iloc[0]['수익금합계'] == 1000
    assert list(df_bct.columns) == ['보유종목수', '보유금액']


def test_get_result_dataframe_pads_legacy_trade_rows_with_zero_extra_columns():
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
    ]]
    arry_bct = np.array([
        [20250101100000, 1, 100000],
    ], dtype='float64')

    df_tsg, _ = GetResultDataframe('S', list_tsg, arry_bct)

    assert list(df_tsg.columns[-len(TRADE_RESULT_EXTRA_COLUMNS):]) == TRADE_RESULT_EXTRA_COLUMNS
    assert df_tsg.iloc[0][TRADE_RESULT_EXTRA_COLUMNS].tolist() == [0] * len(TRADE_RESULT_EXTRA_COLUMNS)
    assert df_tsg.iloc[0]['수익금합계'] == 1000


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


def test_backengine_trade_result_extra_data_uses_buy_sell_and_result_snapshots():
    engine = BackEngineBase.__new__(BackEngineBase)
    source_names = []
    for column in TRADE_RESULT_B_COLUMNS + TRADE_RESULT_S_COLUMNS:
        source_name = column[2:]
        if source_name != '시분초' and source_name not in source_names:
            source_names.append(source_name)

    engine.dict_findex = {name: i + 1 for i, name in enumerate(source_names)}
    engine.arry_code = np.zeros((2, len(source_names) + 1), dtype='float64')
    engine.arry_code[0, 0] = 20250101100102
    engine.arry_code[1, 0] = 20250101100304
    for i, _ in enumerate(source_names, start=1):
        engine.arry_code[0, i] = 100 + i
        engine.arry_code[1, i] = 200 + i
    engine.is_tick = True
    engine.indexn = 0
    engine.trade_snapshots = {0: {0: get_trade_result_snapshot()}}

    engine._store_buy_snapshot(0, 0)
    engine.indexn = 1
    engine.curr_trade_info = {'최고수익률': 3.5, '최저수익률': -1.2}

    extra_data = dict(zip(TRADE_RESULT_EXTRA_COLUMNS, engine._get_trade_result_extra_data(0, 0)))

    assert extra_data['B_현재가'] == 101
    assert extra_data['B_시분초'] == 100102
    assert extra_data['S_현재가'] == 201
    assert extra_data['S_매도총잔량'] == 200 + engine.dict_findex['매도총잔량']
    assert extra_data['R_매수후최고수익률'] == 3.5
    assert extra_data['R_MAE'] == -1.2


def test_backengine_calculation_eyun_emits_extended_trade_result_row():
    engine = BackEngineBase.__new__(BackEngineBase)
    engine.info_for_order = (None, None, 0, 0)
    engine.curr_trade_info = get_trade_info(1)
    engine.curr_trade_info.update({
        '보유중': 1,
        '매수가': 1000,
        '매도가': 1010,
        '주문수량': 10,
        '보유수량': 10,
        '최고수익률': 2.5,
        '최저수익률': -0.5,
        '매수틱번호': 0,
        '매수시간': pd.Timestamp('2025-01-01 09:00:00'),
    })
    engine.is_tick = True
    engine.index = 20250101090500
    engine.indexn = 1
    engine.arry_code = np.array([
        [20250101090000, 1000, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
        [20250101090500, 1010, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
    ], dtype='float64')
    engine.dict_findex = {
        '현재가': 1,
        '등락율': 2,
        '당일거래대금': 3,
        '거래대금증감': 4,
        '체결강도': 5,
        '시가총액': 6,
        '회전율': 7,
        '전일동시간비': 8,
        '매수총잔량': 9,
        '매도총잔량': 10,
        '분봉시가': 11,
        '분봉고가': 12,
        '분봉저가': 13,
    }
    engine.trade_snapshots = {0: {0: get_trade_result_snapshot()}}
    engine.indexn = 0
    engine._store_buy_snapshot(0, 0)
    engine.indexn = 1
    engine.name = '테스트종목'
    engine.dict_sconds = {0: '기본매도'}
    engine.sell_cond = 0
    engine.back_type = '백테스트'
    engine.opti_kind = 0
    engine.sell_count = 0
    engine.bstq_list = [_DummyQueue() for _ in range(5)]
    engine.trade_info = {0: {0: engine.curr_trade_info}}
    engine.GetProfitInfo = lambda _sell, _buy, _count: (123456789, 10100, 100, 1.0)

    engine.CalculationEyun()

    data = engine.bstq_list[0][0]
    extra_values = data[15:-2]
    assert len(extra_values) == len(TRADE_RESULT_EXTRA_COLUMNS)
    assert data[-2:] == (0, 0)
    assert extra_values[TRADE_RESULT_EXTRA_COLUMNS.index('B_현재가')] == 1000
    assert extra_values[TRADE_RESULT_EXTRA_COLUMNS.index('S_현재가')] == 1010
    assert extra_values[TRADE_RESULT_EXTRA_COLUMNS.index('R_MFE')] == 2.5
    assert engine.trade_snapshots[0][0] == get_trade_result_snapshot()


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

    backtest = backtest_module.BackTest.__new__(backtest_module.BackTest)
    backtest.wq = _DummyQueue()
    backtest.sq = _DummyQueue()
    backtest.tq = _DummyQueue()
    backtest.lq = _DummyQueue()
    backtest.teleQ = _DummyQueue()
    backtest.bstq_list = []
    backtest.backname = '테스트백테스트'
    backtest.ui_gubun = 'S'
    backtest.gubun = 'stock'
    backtest.market_text = '주식'
    backtest.dict_set = {
        '스톰라이브': False,
        '주식타임프레임': True,
        '그래프저장하지않기': True,
        '그래프띄우지않기': True,
    }
    backtest.savename = 'stock_bt'
    backtest.betting = 100000
    backtest.avgtime = 60
    backtest.startday = 20260310
    backtest.endday = 20260310
    backtest.starttime = 90000
    backtest.endtime = 90100
    backtest.buystg_name = '테스트전략'
    backtest.buystg = 'if 매수:\n    pass'
    backtest.sellstg = 'if 매도:\n    pass'
    backtest.dict_cn = {}
    backtest.blacklist = False
    backtest.day_count = 1
    backtest.schedul = False
    backtest.back_club = False
    backtest.insertblacklist = []
    backtest.start_time = backtest_module.now()
    backtest.is_tick = True

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

    backtest.Report(list_tsg, arry_bct)

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
