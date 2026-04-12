from pathlib import Path
import re


def _extract_backtest_spawn_block(text: str) -> str:
    pattern = re.compile(
        r"ui\.proc_backtester_bs\s*=\s*Process\(\s*target=BackTest,\s*args=\((.*?)\)\s*\)",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, "BackTest spawn block not found"
    return match.group(1)


def _extract_backsubtotal_spawn_block(text: str) -> str:
    pattern = re.compile(
        r"target=BackSubTotal,\s*args=\((.*?)\),\s*daemon=True",
        re.DOTALL,
    )
    match = pattern.search(text)
    assert match is not None, "BackSubTotal spawn block not found"
    return match.group(1)


def test_stock_backtest_spawn_does_not_pass_legacy_long_signature():
    text = Path("ui/ui_button_clicked_editer_stock.py").read_text(encoding="utf-8")
    block = _extract_backtest_spawn_block(text)

    assert "target=BackTest" in text
    assert "ui.back_sques" in block
    assert "ui.dict_set" in block
    assert "betting" not in block
    assert "avgtime" not in block
    assert "startday" not in block
    assert "endtime" not in block
    assert "ui.back_count" not in block


def test_coin_backtest_spawn_does_not_pass_legacy_long_signature():
    text = Path("ui/ui_button_clicked_editer_coin.py").read_text(encoding="utf-8")
    block = _extract_backtest_spawn_block(text)

    assert "target=BackTest" in text
    assert "ui.back_sques" in block
    assert "ui.dict_set" in block
    assert "betting" not in block
    assert "avgtime" not in block
    assert "startday" not in block
    assert "endtime" not in block
    assert "ui.back_count" not in block


def test_cli_backsubtotal_spawn_passes_window_queue():
    text = Path("cli/runner.py").read_text(encoding="utf-8")
    block = _extract_backsubtotal_spawn_block(text)

    assert "windowQ" in block
    assert "totalQ" in block
    assert "back_sques" in block
