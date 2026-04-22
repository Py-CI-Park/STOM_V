import importlib
from pathlib import Path

import pytest


CLI_DB_ENV_NAMES = (
    'STOM_CLI_DATABASE_DIR',
    'STOM_CLI_DB_SETTING',
    'STOM_CLI_DB_STRATEGY',
    'STOM_CLI_DB_BACKTEST',
    'STOM_CLI_DB_TRADELIST',
    'STOM_CLI_DB_OPTUNA',
    'STOM_CLI_DB_CODE_INFO',
    'STOM_CLI_DB_STOCK_TICK',
    'STOM_CLI_DB_STOCK_MIN',
    'STOM_CLI_DB_STOCK_BACK_TICK',
    'STOM_CLI_DB_STOCK_BACK_MIN',
    'STOM_CLI_DB_COIN_TICK',
    'STOM_CLI_DB_COIN_MIN',
    'STOM_CLI_DB_COIN_BACK_TICK',
    'STOM_CLI_DB_COIN_BACK_MIN',
    'STOM_CLI_DB_FUTURE_TICK',
    'STOM_CLI_DB_FUTURE_MIN',
    'STOM_CLI_DB_FUTURE_BACK_TICK',
    'STOM_CLI_DB_FUTURE_BACK_MIN',
    'STOM_CLI_DB_STOCK_USA_TICK',
    'STOM_CLI_DB_STOCK_USA_MIN',
    'STOM_CLI_DB_STOCK_USA_BACK_TICK',
    'STOM_CLI_DB_STOCK_USA_BACK_MIN',
)


def reload_setting_base(monkeypatch, env=None):
    for name in CLI_DB_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    for name, value in (env or {}).items():
        monkeypatch.setenv(name, value)

    import utility.setting_base as setting_base

    return importlib.reload(setting_base)


@pytest.fixture(autouse=True)
def restore_setting_base_defaults(monkeypatch):
    yield
    for name in CLI_DB_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    import utility.setting_base as setting_base
    importlib.reload(setting_base)


def test_setting_base_keeps_gui_database_defaults_without_cli_env(monkeypatch):
    setting_base = reload_setting_base(monkeypatch)

    assert setting_base.DB_PATH == './_database'
    assert setting_base.DB_SETTING == './_database/setting.db'
    assert setting_base.DB_BACKTEST == './_database/backtest.db'
    assert setting_base.DB_STRATEGY == './_database/strategy.db'
    assert setting_base.DB_STOCK_TICK_BACK == './_database/stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == setting_base.DB_STOCK_TICK_BACK


def test_setting_base_uses_cli_database_dir_for_db_paths(monkeypatch):
    root = r'C:\System_Trading\STOM\STOM_V.wt-dev\_database'
    setting_base = reload_setting_base(
        monkeypatch,
        {'STOM_CLI_DATABASE_DIR': root},
    )

    assert setting_base.DB_PATH == root
    assert setting_base.DB_SETTING == root + '/setting.db'
    assert setting_base.DB_BACKTEST == root + '/backtest.db'
    assert setting_base.DB_STRATEGY == root + '/strategy.db'
    assert setting_base.DB_STOCK_TICK_BACK == root + '/stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == setting_base.DB_STOCK_TICK_BACK


def test_setting_base_individual_cli_db_env_overrides_database_dir(monkeypatch):
    setting_base = reload_setting_base(
        monkeypatch,
        {
            'STOM_CLI_DATABASE_DIR': r'C:\runtime\_database',
            'STOM_CLI_DB_STOCK_BACK_TICK': r'D:\tick\stock_tick_back.db',
            'STOM_CLI_DB_BACKTEST': r'D:\result\backtest.db',
        },
    )

    assert setting_base.DB_PATH == r'C:\runtime\_database'
    assert setting_base.DB_BACKTEST == r'D:\result\backtest.db'
    assert setting_base.DB_SETTING == r'C:\runtime\_database/setting.db'
    assert setting_base.DB_STRATEGY == r'C:\runtime\_database/strategy.db'
    assert setting_base.DB_STOCK_TICK_BACK == r'D:\tick\stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == r'D:\tick\stock_tick_back.db'


def test_setting_base_empty_individual_cli_db_env_falls_back_to_database_dir(monkeypatch):
    setting_base = reload_setting_base(
        monkeypatch,
        {
            'STOM_CLI_DATABASE_DIR': r'C:\runtime\_database',
            'STOM_CLI_DB_BACKTEST': '',
            'STOM_CLI_DB_STOCK_BACK_TICK': '',
        },
    )

    assert setting_base.DB_BACKTEST == r'C:\runtime\_database/backtest.db'
    assert setting_base.DB_STOCK_TICK_BACK == r'C:\runtime\_database/stock_tick_back.db'
    assert setting_base.DB_STOCK_BACK_TICK == r'C:\runtime\_database/stock_tick_back.db'


def test_legacy_setting_uses_cli_database_override_resolver():
    content = Path('utility/setting.py').read_text(encoding='utf-8')

    assert "os.environ.get('STOM_CLI_DATABASE_DIR', './_database')" in content
    assert "def _resolve_db(filename, env_name):" in content
    assert "DB_SETTING          = _resolve_db('setting.db', 'STOM_CLI_DB_SETTING')" in content
    assert "DB_STRATEGY         = _resolve_db('strategy.db', 'STOM_CLI_DB_STRATEGY')" in content
    assert "DB_BACKTEST         = _resolve_db('backtest.db', 'STOM_CLI_DB_BACKTEST')" in content
    assert "DB_STOCK_BACK_TICK  = _resolve_db('stock_tick_back.db', 'STOM_CLI_DB_STOCK_BACK_TICK')" in content
