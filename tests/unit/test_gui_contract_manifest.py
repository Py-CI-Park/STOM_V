from pathlib import Path

import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from gui_contract_manifest import build_contract, contract_summary


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_contract_includes_static_and_parsed_gui_items(tmp_path):
    write(
        tmp_path / "ui" / "set_dialog_etc.py",
        """
self.ui.dialog_db = self.wc.setDialog('STOM DATABASE')
self.ui.set_tapWidgett_01.addTab(self.ui.ssd_tab, '일반설정')
""",
    )
    write(
        tmp_path / "ui" / "set_stg_stock_tap.py",
        """
self.ui.ss_pushButtonn_01 = self.wc.setPushbutton('백테스트', parent=self.ui.ss_tab, click=lambda: run())
""",
    )
    write(
        tmp_path / "ui" / "set_dialog_back.py",
        """
self.ui.be_pushButtonnn_01 = self.wc.setPushbutton('백테스트 엔진 시작', parent=self.ui.be_groupBoxxxxx_01, click=lambda: run())
""",
    )

    contract = build_contract(tmp_path)
    labels = {item.label for item in contract}
    attrs = {item.attr for item in contract}
    summary = contract_summary(contract)

    assert "Home(Ctrl+1)" in labels
    assert "STOM DATABASE" in labels
    assert "일반설정" in labels
    assert "백테스트" in labels
    assert "백테스트 엔진 시작" in labels
    assert "pushButton_00" in attrs
    assert "trading" in attrs
    assert "ctpg_code" in attrs
    assert "canvas" in attrs
    assert "saqsize" in attrs
    assert summary["main_menu"] == 8
    assert summary["runtime_state"] == 6
    assert summary["strategy_button"] == 1
    assert summary["backtest_button"] == 1

