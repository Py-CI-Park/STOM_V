"""CLI 경량 경로 상수.

`utility.setting` 을 import 하지 않고도 CLI가 사용할 DB 경로를 제공한다.
가벼운 help/list/subcommand 경로에서 heavy runtime import를 피하기 위한 모듈이다.
"""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_DIR = Path(
    os.environ.get("STOM_CLI_DATABASE_DIR", str(PROJECT_ROOT / "_database"))
)


def _resolve_db(filename: str, env_name: str) -> str:
    override = os.environ.get(env_name)
    if override:
        return override
    return str(DATABASE_DIR / filename)


DB_SETTING = _resolve_db("setting.db", "STOM_CLI_DB_SETTING")
DB_STRATEGY = _resolve_db("strategy.db", "STOM_CLI_DB_STRATEGY")
DB_BACKTEST = _resolve_db("backtest.db", "STOM_CLI_DB_BACKTEST")
DB_STOCK_BACK_TICK = _resolve_db("stock_tick_back.db", "STOM_CLI_DB_STOCK_BACK_TICK")
DB_STOCK_BACK_MIN = _resolve_db("stock_min_back.db", "STOM_CLI_DB_STOCK_BACK_MIN")

