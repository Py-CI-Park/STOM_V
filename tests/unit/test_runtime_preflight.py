import sqlite3
from pathlib import Path

from cli.config import BacktestConfig


def _make_strategy_db(path: Path, buy_code: object, sell_code: object) -> None:
    con = sqlite3.connect(path)
    try:
        con.execute('CREATE TABLE stockbuy (`index` TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('CREATE TABLE stocksell (`index` TEXT PRIMARY KEY, "전략코드" TEXT)')
        con.execute('INSERT INTO stockbuy VALUES (?, ?)', ('BuyWide', buy_code))
        con.execute('INSERT INTO stocksell VALUES (?, ?)', ('SellWide', sell_code))
        con.commit()
    finally:
        con.close()


def _make_runtime_files(tmp_path: Path, buy_code: object, sell_code: object) -> dict:
    strategy_db = tmp_path / 'strategy.db'
    setting_db = tmp_path / 'setting.db'
    backtest_db = tmp_path / 'backtest.db'
    tick_db = tmp_path / 'stock_tick_back.db'
    csv_dir = tmp_path / 'csv'
    _make_strategy_db(strategy_db, buy_code, sell_code)
    setting_db.write_bytes(b'setting')
    backtest_db.write_bytes(b'backtest')
    tick_db.write_bytes(b'tick')
    csv_dir.mkdir()
    return {
        'strategy_db': str(strategy_db),
        'setting_db': str(setting_db),
        'backtest_db': str(backtest_db),
        'stock_tick_back_db': str(tick_db),
        'stock_min_back_db': str(tmp_path / 'stock_min_back.db'),
        'csv_dir': str(csv_dir),
    }


def _wide_config() -> BacktestConfig:
    return BacktestConfig(
        buy_strategy='BuyWide',
        sell_strategy='SellWide',
        start_date=20250101,
        end_date=20251231,
        start_time=90000,
        end_time=92800,
        avg_time=30,
        engine_count=32,
        is_tick=True,
        timeout=900,
    )


def test_runtime_preflight_passes_with_valid_paths_and_strategies(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='매수 = True\nif 매수:\n    self.Buy()',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'ok'
    assert result['runtime_profile']['strategy_db_path'] == paths['strategy_db']
    assert result['runtime_profile']['stock_back_db_path'] == paths['stock_tick_back_db']
    assert result['runtime_profile']['csv_output_dir'] == paths['csv_dir']
    assert result['strategies']['buy']['status'] == 'ok'
    assert result['strategies']['sell']['status'] == 'ok'
    assert result['config']['start'] == 20250101
    assert result['config']['end_time'] == 92800
    assert result['config']['engines'] == 32


def test_runtime_preflight_does_not_create_missing_strategy_db(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='buy_flag = True\nif buy_flag:\n    self.Buy()',
        sell_code='sell_flag = True\nif sell_flag:\n    self.Sell()',
    )
    strategy_db = Path(paths['strategy_db'])
    strategy_db.unlink()

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert 'strategy_db' in result['failed_checks']
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'strategy_db_missing'
    assert result['strategies']['sell']['status'] == 'error'
    assert result['strategies']['sell']['reason'] == 'strategy_db_missing'
    assert strategy_db.exists() is False


def test_runtime_preflight_returns_error_when_strategy_code_is_null(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code=None,
        sell_code='sell_flag = True\nif sell_flag:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'evaluate_failed'
    assert 'buy_strategy' in result['failed_checks']


def test_runtime_preflight_fails_when_strategy_code_is_question_marks(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='????',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'suspicious_question_marks'
    assert 'buy_strategy' in result['failed_checks']


def test_runtime_preflight_fails_when_question_marks_include_whitespace(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='??\n??',
        sell_code='留ㅻ룄 = True\nif 留ㅻ룄:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'suspicious_question_marks'
    assert 'buy_strategy' in result['failed_checks']


def test_runtime_preflight_uses_raw_code_length_for_short_code_guard(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='12345678901   ',
        sell_code='留ㅻ룄 = True\nif 留ㅻ룄:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'ok'
    assert result['strategies']['buy']['status'] == 'ok'
    assert 'buy_strategy' not in result['failed_checks']


def test_runtime_preflight_fails_when_strategy_code_is_too_short(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='pass',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['strategies']['buy']['status'] == 'error'
    assert result['strategies']['buy']['reason'] == 'code_too_short'


def test_runtime_preflight_fails_when_tick_db_is_missing(tmp_path):
    from cli.runtime_preflight import run_runtime_preflight

    paths = _make_runtime_files(
        tmp_path,
        buy_code='매수 = True\nif 매수:\n    self.Buy()',
        sell_code='매도 = True\nif 매도:\n    self.Sell()',
    )
    Path(paths['stock_tick_back_db']).unlink()

    result = run_runtime_preflight(_wide_config(), paths=paths)

    assert result['status'] == 'error'
    assert result['runtime_profile']['stock_back_db_exists'] is False
    assert 'stock_back_db' in result['failed_checks']
