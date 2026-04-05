import inspect

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
