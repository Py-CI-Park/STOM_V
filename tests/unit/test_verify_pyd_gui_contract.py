from pathlib import Path

import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import verify_pyd_gui_contract as contract


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_read_smoke_requires_matching_log_file(tmp_path):
    smoke, error = contract.read_smoke(tmp_path, "STOM_Version_2U", "V2.78")

    assert smoke is None
    assert "missing smoke log" in error


def test_evaluate_fails_closed_on_missing_smoke_and_missing_import(monkeypatch, tmp_path):
    write(tmp_path / "ui" / "ui_mainwindow.py", "from ui.missing_module import *\nclass MainWindow: pass\n")
    write(tmp_path / "ui" / "set_dialog_etc.py", "self.ui.dialog_db = self.wc.setDialog('STOM DATABASE')\n")

    monkeypatch.setattr(contract, "ROOT", tmp_path)
    monkeypatch.setattr(contract, "upstream_pyd_evidence", lambda ref: ({"byte_size": 1, "sha256": "x"}, None))
    monkeypatch.setattr(contract, "tracked_pyd_files", lambda: [])

    payload, failures = contract.evaluate("STOM_Version_2U", "V2.78", "refs/tags/V2.0", tmp_path / ".omx/logs")

    assert payload["result"] == "failed"
    assert any("missing modules" in failure for failure in failures)
    assert any("missing smoke log" in failure for failure in failures)


def test_evaluate_passes_with_smoke_log_and_upstream_evidence(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_mainwindow.py",
        "class MainWindow:\n"
        "    self.ctpg_code             = None\n"
        "    self.trading          = False\n"
        "    self.canvas  = None\n"
        "    self.saqsize = 0\n"
        "    self.back_start_time  = None\n"
        "    def UpdateProgressBar(self):\n"
        "        update_back_progressbar(self)\n"
        "    def BindPydDialogPositionPersistence(self):\n"
        "        self.BindPydDialogPosition(self.dialog_backengine, 16, 17)\n"
        "    def BindPydBacktestEngineButton(self): pass\n"
        "    def PydBacktestEngineStart(self):\n"
        "        self.back_engining = True\n"
        "        backengine_start(self, gubun)\n"
        "    def CleanupPydStaleBacktestSharedMemory(self): pass\n"
        "    def RestorePydDialogPosition(self, dialog, x_index, y_index): pass\n"
        "    def SavePydDialogPosition(self, dialog, x_index, y_index):\n"
        "        QEvent.Move\n"
        "        dialog.installEventFilter(self)\n"
        "    def eventFilter(self, widget, event):\n"
        "        self.HandlePydDialogPositionEvent(widget, event)\n"
        "    def BindLegacyStrategyBacktestButtons(self):\n"
        "        self.svj_pushButton_01, self.StockBacktestStart\n"
        "        self.cvj_pushButton_01, self.CoinBacktestStart\n"
        "    def LegacyBacktestShortcut(self, event):\n"
        "        self.StockBacktestStart()\n"
        "        self.CoinBacktestStart()\n",
    )
    write(tmp_path / "ui" / "set_dialog_etc.py", "self.ui.dialog_db = self.wc.setDialog('STOM DATABASE')\n")
    log_dir = tmp_path / ".omx" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "smoke_STOM_Version_2U_V2_78.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")

    monkeypatch.setattr(contract, "ROOT", tmp_path)
    monkeypatch.setattr(contract, "upstream_pyd_evidence", lambda ref: ({"byte_size": 1, "sha256": "x"}, None))
    monkeypatch.setattr(contract, "tracked_pyd_files", lambda: [])

    payload, failures = contract.evaluate("STOM_Version_2U", "V2.78", "refs/tags/V2.0", log_dir)

    assert failures == []
    assert payload["result"] == "passed"



def test_unresolved_activated_alias_calls_are_reported(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_mainwindow.py",
        "class MainWindow:\n"
        "    def sActivated_09(self): sactivated_09(self)\n"
        "    def cActivated_09(self): cactivated_09(self)\n",
    )

    monkeypatch.setattr(contract, "ROOT", tmp_path)

    assert contract.unresolved_activated_alias_calls() == [
        "cActivated_09->cactivated_09",
        "sActivated_09->sactivated_09",
    ]


def test_pyd_mainwindow_backtest_parity_failures_are_reported(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_mainwindow.py",
        "class MainWindow:\n"
        "    pass\n",
    )

    monkeypatch.setattr(contract, "ROOT", tmp_path)

    failures = contract.pyd_mainwindow_backtest_parity_failures()

    assert "pyd mainwindow backtest parity lacks stock button connect" in failures
    assert "pyd mainwindow backtest parity lacks chart current code state" in failures
    assert "pyd mainwindow backtest parity lacks chart trading state" in failures
    assert "pyd mainwindow backtest parity lacks treemap canvas state" in failures
    assert "pyd mainwindow backtest parity lacks queue sagent qsize state" in failures
    assert "pyd mainwindow backtest parity lacks back progress updater" in failures
    assert "pyd mainwindow backtest parity lacks dialog position binder" in failures
    assert "pyd mainwindow backtest parity lacks backengine start latch" in failures
    assert "pyd mainwindow backtest parity lacks stale shared memory cleanup" in failures
    assert "pyd mainwindow backtest parity lacks shortcut handler" in failures


def test_pyd_mainwindow_backtest_parity_passes_with_legacy_bindings(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_mainwindow.py",
        "class MainWindow:\n"
        "    self.ctpg_code             = None\n"
        "    self.trading          = False\n"
        "    self.canvas  = None\n"
        "    self.saqsize = 0\n"
        "    self.back_start_time  = None\n"
        "    def UpdateProgressBar(self):\n"
        "        update_back_progressbar(self)\n"
        "    def BindPydDialogPositionPersistence(self):\n"
        "        self.BindPydDialogPosition(self.dialog_backengine, 16, 17)\n"
        "    def BindPydBacktestEngineButton(self): pass\n"
        "    def PydBacktestEngineStart(self):\n"
        "        self.back_engining = True\n"
        "        backengine_start(self, gubun)\n"
        "    def CleanupPydStaleBacktestSharedMemory(self): pass\n"
        "    def RestorePydDialogPosition(self, dialog, x_index, y_index): pass\n"
        "    def SavePydDialogPosition(self, dialog, x_index, y_index):\n"
        "        QEvent.Move\n"
        "        dialog.installEventFilter(self)\n"
        "    def eventFilter(self, widget, event):\n"
        "        self.HandlePydDialogPositionEvent(widget, event)\n"
        "    def BindLegacyStrategyBacktestButtons(self):\n"
        "        self.svj_pushButton_01, self.StockBacktestStart\n"
        "        self.cvj_pushButton_01, self.CoinBacktestStart\n"
        "    def LegacyBacktestShortcut(self, event):\n"
        "        self.StockBacktestStart()\n"
        "        self.CoinBacktestStart()\n",
    )

    monkeypatch.setattr(contract, "ROOT", tmp_path)

    assert contract.pyd_mainwindow_backtest_parity_failures() == []
