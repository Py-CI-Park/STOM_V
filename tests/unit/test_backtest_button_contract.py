import inspect

from backtest.back_subtotal import BackSubTotal
from backtest.backtest import BackTest


def test_backtest_constructor_contract_is_small_and_queue_driven():
    params = list(inspect.signature(BackTest.__init__).parameters)
    assert params == [
        "self",
        "sc",
        "wq",
        "bq",
        "sq",
        "tq",
        "lq",
        "teleQ",
        "beq_list",
        "bstq_list",
        "backname",
        "ui_gubun",
        "dict_set",
    ]


def test_backsubtotal_constructor_contract_includes_window_queue():
    params = list(inspect.signature(BackSubTotal.__init__).parameters)
    assert params == [
        "self",
        "vkey",
        "wq",
        "tq",
        "bstqs",
        "buystd",
    ]
