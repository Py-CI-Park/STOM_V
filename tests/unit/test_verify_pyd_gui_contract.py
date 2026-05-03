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
    write(tmp_path / "ui" / "ui_mainwindow.py", "class MainWindow: pass\n")
    write(
        tmp_path / "ui" / "ui_button_clicked_editer_unified.py",
        "def backtest_start(ui, ui_type):\n"
        "    if ui_type == 'stock':\n"
        "        from ui.ui_button_clicked_editer_stock import stock_backtest_start\n"
        "        stock_backtest_start(ui)\n"
        "    elif ui_type == 'coin':\n"
        "        from ui.ui_button_clicked_editer_coin import coin_backtest_start\n"
        "        coin_backtest_start(ui)\n",
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


def test_unified_backtest_legacy_parity_failures_are_reported(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_button_clicked_editer_unified.py",
        "def backtest_start(ui, ui_type):\n"
        "    pass\n",
    )

    monkeypatch.setattr(contract, "ROOT", tmp_path)

    failures = contract.unified_backtest_legacy_parity_failures()

    assert "unified backtest_start lacks stock legacy call" in failures
    assert "unified backtest_start lacks coin legacy call" in failures


def test_unified_backtest_legacy_parity_passes_with_stock_coin_dispatch(monkeypatch, tmp_path):
    write(
        tmp_path / "ui" / "ui_button_clicked_editer_unified.py",
        "def backtest_start(ui, ui_type):\n"
        "    if ui_type == 'stock':\n"
        "        from ui.ui_button_clicked_editer_stock import stock_backtest_start\n"
        "        stock_backtest_start(ui)\n"
        "    elif ui_type == 'coin':\n"
        "        from ui.ui_button_clicked_editer_coin import coin_backtest_start\n"
        "        coin_backtest_start(ui)\n",
    )

    monkeypatch.setattr(contract, "ROOT", tmp_path)

    assert contract.unified_backtest_legacy_parity_failures() == []
