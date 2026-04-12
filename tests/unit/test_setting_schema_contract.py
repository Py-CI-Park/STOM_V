from pathlib import Path

import pandas as pd
import pytest

from utility.setting_schema import (
    CURRENT_BACKTEST_LOG_COLUMN,
    LEGACY_BACKTEST_LOG_COLUMN,
    read_backtest_log_skip,
)


def test_database_check_creates_current_backtest_log_column():
    text = Path('utility/database_check.py').read_text(encoding='utf-8')

    assert '"백테스트로그기록안함"' in text


def test_database_check_renames_legacy_backtest_log_column():
    text = Path('utility/database_check.py').read_text(encoding='utf-8')

    assert "'최적화로그기록안함': '백테스트로그기록안함'" in text


def test_read_backtest_log_skip_reads_current_column():
    df_b = pd.DataFrame({CURRENT_BACKTEST_LOG_COLUMN: [1]})

    assert read_backtest_log_skip(df_b) == 1


def test_read_backtest_log_skip_reads_legacy_column():
    df_b = pd.DataFrame({LEGACY_BACKTEST_LOG_COLUMN: [0]})

    assert read_backtest_log_skip(df_b) == 0


def test_read_backtest_log_skip_raises_current_column_key_error():
    df_b = pd.DataFrame({'다른컬럼': [1]})

    with pytest.raises(KeyError) as exc_info:
        read_backtest_log_skip(df_b)

    assert CURRENT_BACKTEST_LOG_COLUMN in str(exc_info.value)
