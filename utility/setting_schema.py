CURRENT_BACKTEST_LOG_COLUMN = "백테스트로그기록안함"
LEGACY_BACKTEST_LOG_COLUMN = "최적화로그기록안함"


def read_backtest_log_skip(df_b):
    if CURRENT_BACKTEST_LOG_COLUMN in df_b.columns:
        return df_b[CURRENT_BACKTEST_LOG_COLUMN][0]
    if LEGACY_BACKTEST_LOG_COLUMN in df_b.columns:
        return df_b[LEGACY_BACKTEST_LOG_COLUMN][0]
    raise KeyError(CURRENT_BACKTEST_LOG_COLUMN)
