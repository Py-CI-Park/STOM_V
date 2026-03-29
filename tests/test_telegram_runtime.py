import queue

from ui.ui_etc import update_dictset
from ui.ui_process_alive import telegram_process_alive
from utility.telegram_bot import get_telegram_runtime_queues


class DummyProcess:
    def __init__(self, alive):
        self._alive = alive

    def is_alive(self):
        return self._alive


class DummyUI:
    def __init__(self):
        self.dict_set = {"sample": "value"}
        self.wdzservQ = queue.Queue()
        self.creceivQ = queue.Queue()
        self.ctraderQ = queue.Queue()
        self.cstgQ = queue.Queue()
        self.chartQ = queue.Queue()
        self.teleQ = queue.Queue()
        self.proc_chqs = DummyProcess(False)
        self.backtest_engine = False

    def CoinReceiverProcessAlive(self):
        return False

    def CoinTraderProcessAlive(self):
        return False

    def CoinStrategyProcessAlive(self):
        return False

    def TelegramProcessAlive(self):
        return False


def test_get_telegram_runtime_queues_uses_current_mainwindow_layout():
    qlist = [object() for _ in range(15)]

    window_q, tele_q, ctrader_q, cstg_q, wdzserv_q = get_telegram_runtime_queues(qlist)

    assert window_q is qlist[0]
    assert tele_q is qlist[3]
    assert ctrader_q is qlist[9]
    assert cstg_q is qlist[10]
    assert wdzserv_q is qlist[13]


def test_telegram_process_alive_returns_false_when_proc_is_missing():
    class MissingProcUI:
        pass

    assert telegram_process_alive(MissingProcUI()) is False


def test_update_dictset_forwards_settings_change_to_telegram_queue_when_alive():
    ui = DummyUI()
    ui.TelegramProcessAlive = lambda: True

    update_dictset(ui)

    assert ui.wdzservQ.get_nowait() == ("manager", ("설정변경", ui.dict_set))
    assert ui.teleQ.get_nowait() == ("설정변경", ui.dict_set)
