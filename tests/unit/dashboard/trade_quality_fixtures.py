"""Official named CSV fixtures derived from production owner constants."""

from backtest.back_static import (
    TRADE_RESULT_B_COLUMNS,
    TRADE_RESULT_R_COLUMNS,
    TRADE_RESULT_S_COLUMNS,
)
from utility.setting_base import columns_bt


def official_pair(*, legacy: bool = False) -> tuple[str, str]:
    """Reorder named columns to keep frequently mutated core cells at the end."""
    core = ["종목명", "매수시간", "매도시간", "보유시간", "수익률", "수익금"]
    b_columns = TRADE_RESULT_B_COLUMNS[:14] if legacy else TRADE_RESULT_B_COLUMNS
    extras = [c for c in columns_bt if c not in core]
    extras.extend([*b_columns, *TRADE_RESULT_S_COLUMNS, *TRADE_RESULT_R_COLUMNS])
    return (
        ",".join([*extras, *core]) + "\n",
        "0," * len(extras) + "삼성전자,20250102090000,20250102090100,60,0,0\n",
    )
