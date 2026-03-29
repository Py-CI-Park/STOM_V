import queue

from ui.ui_etc import update_dictset
from ui.ui_process_kill import telegram_process_kill
from ui.ui_process_alive import telegram_process_alive
from ui.ui_telegram_settings import apply_telegram_settings_save
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


class DummySettingsUI:
    def __init__(self):
        self.queryQ = queue.Queue()
        self.dict_set = {
            "키": "dummy",
            "텔레그램봇토큰1": None,
            "텔레그램사용자아이디1": None,
        }
        self._updated = False
        self.sj_tele_liEdit_01 = type("LineEdit", (), {"text": lambda self: "bot-token"})()
        self.sj_tele_liEdit_02 = type("LineEdit", (), {"text": lambda self: "12345"})()
        self.sj_main_comBox_01 = type("ComboBox", (), {"currentText": lambda self: "키움증권1"})()
        self.proc_chqs = DummyProcess(True)

    def UpdateDictSet(self):
        self._updated = True


class DummyKillUI:
    def __init__(self):
        self.proc_tele = DummyKilledProcess()

    def TelegramProcessAlive(self):
        return True


class DummyKilledProcess:
    def __init__(self):
        self.killed = False

    def kill(self):
        self.killed = True


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


def test_apply_telegram_settings_save_updates_runtime_without_restart():
    ui = DummySettingsUI()

    apply_telegram_settings_save(ui, "1", "bot-token", "12345", lambda key, value: f"enc:{value}")

    assert ui.queryQ.get_nowait() == ("설정디비", "UPDATE telegram SET str_bot = ?, int_id = ? WHERE `index` = ?", ("enc:bot-token", "enc:12345", "1"))
    assert ui.dict_set["텔레그램봇토큰1"] == "bot-token"
    assert ui.dict_set["텔레그램사용자아이디1"] == 12345
    assert ui._updated is True


def test_telegram_process_kill_terminates_running_process():
    ui = DummyKillUI()

    telegram_process_kill(ui)

    assert ui.proc_tele.killed is True
