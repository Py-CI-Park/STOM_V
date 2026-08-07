from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DB = ROOT / "ai_strategy_loop" / "state" / "loop_strategies.db"
TARGET_DB = ROOT / "artifacts" / "chart_sulsa_validation_20260702" / "css_v7_root_cause_strategy_copy.db"
CONFIG_OUT = ROOT / "artifacts" / "chart_sulsa_validation_20260702" / "css_v7_root_cause_micro_config.json"
PAIRS_OUT = ROOT / "artifacts" / "chart_sulsa_validation_20260702" / "css_v7_root_cause_pairs.json"
RECEIPT_OUT = (
    ROOT
    / ".omo"
    / "evidence"
    / "css-v7-root-cause-before-plan-b-20260703"
    / "r2-runtime-variant-setup.json"
)


SOURCE_NAMES = {
    "buy": "CSS_V7_TICK_B_MASTER_0900_0930",
    "sell": "CSS_V7_TICK_S_MASTER_0900_0930",
}
FIX_NAMES = {
    "buy": "CSS_V7_TICK_B_MASTER_0900_0930_FIXCALL",
    "sell": "CSS_V7_TICK_S_MASTER_0900_0930_FIXCALL",
}


def copy_db() -> None:
    if TARGET_DB.exists():
        TARGET_DB.unlink()
    source = sqlite3.connect(SOURCE_DB)
    target = sqlite3.connect(TARGET_DB)
    try:
        source.backup(target)
    finally:
        target.close()
        source.close()


def table_for(side: str) -> str:
    return "stockbuy" if side == "buy" else "stocksell"


def code_column(con: sqlite3.Connection, table: str) -> str:
    cols = [row[1] for row in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if len(cols) < 2:
        raise RuntimeError(f"missing code column: {table}")
    return cols[1]


def read_code(con: sqlite3.Connection, table: str, name: str) -> str:
    col = code_column(con, table)
    row = con.execute(f'SELECT "{col}" FROM {table} WHERE "index"=?', (name,)).fetchone()
    if row is None:
        raise RuntimeError(f"missing source condition: {name}")
    return row[0]


def fix_call_signature(code: str, side: str) -> str:
    method = "Buy" if side == "buy" else "Sell"
    return re.sub(rf"self\.{method}\([^\n]*\)", f"self.{method}()", code)


def insert_variant(con: sqlite3.Connection, side: str) -> dict[str, object]:
    table = table_for(side)
    col = code_column(con, table)
    source_name = SOURCE_NAMES[side]
    fix_name = FIX_NAMES[side]
    source_code = read_code(con, table, source_name)
    fixed_code = fix_call_signature(source_code, side)
    con.execute(f'INSERT INTO {table} ("index", "{col}") VALUES (?, ?)', (fix_name, fixed_code))
    return {
        "side": side,
        "table": table,
        "source_name": source_name,
        "fix_name": fix_name,
        "source_call_tail": source_code.splitlines()[-1].strip(),
        "fixed_call_tail": fixed_code.splitlines()[-1].strip(),
    }


def write_config_and_pairs() -> None:
    config = {
        "provider": "gpt_auth",
        "bt_engine_mode": "warm",
        "bt_warm_engine_count": 2,
        "bt_betting": "5",
        "bt_avg_time": 30,
        "min_daily_trades": 0.3,
        "mdd_cap": 35,
        "winner_objective": "uptrend",
        "autopsy_enabled": False,
        "bt_full_start": 20250102,
        "bt_full_end": 20250103,
        "max_generations": 1,
        "bt_timeout": 300,
        "bt_warm_run_timeout": 90,
        "equity_points_enabled": True,
        "bt_timeframe": "tick",
        "bt_universe_start_time": 90000,
        "bt_universe_end_time": 93000,
        "_comment": "CSS_V7 root-cause micro probe; strategy DB is isolated copy.",
    }
    pairs = [
        {
            "label": "root_cause_comparator_rr8_12",
            "buy": "GATE_rr8_12_turnover_min_902_1_5_B",
            "sell": "GATE_rr8_12_turnover_min_902_1_5_S",
        },
        {
            "label": "root_cause_css_v7_fixcall_pair",
            "buy": FIX_NAMES["buy"],
            "sell": FIX_NAMES["sell"],
        },
        {
            "label": "root_cause_css_v7_raw_pair",
            "buy": SOURCE_NAMES["buy"],
            "sell": SOURCE_NAMES["sell"],
        },
        {
            "label": "root_cause_css_v7_fix_buy_raw_sell",
            "buy": FIX_NAMES["buy"],
            "sell": SOURCE_NAMES["sell"],
        },
        {
            "label": "root_cause_css_v7_raw_buy_fix_sell",
            "buy": SOURCE_NAMES["buy"],
            "sell": FIX_NAMES["sell"],
        },
    ]
    CONFIG_OUT.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PAIRS_OUT.write_text(json.dumps(pairs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    TARGET_DB.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_OUT.parent.mkdir(parents=True, exist_ok=True)
    copy_db()
    con = sqlite3.connect(TARGET_DB)
    try:
        inserted = [insert_variant(con, "buy"), insert_variant(con, "sell")]
        con.commit()
    finally:
        con.close()
    write_config_and_pairs()
    receipt = {
        "source_db": str(SOURCE_DB.relative_to(ROOT)),
        "target_db": str(TARGET_DB.relative_to(ROOT)),
        "config": str(CONFIG_OUT.relative_to(ROOT)),
        "pairs": str(PAIRS_OUT.relative_to(ROOT)),
        "inserted_variants": inserted,
        "main_db_mutation": False,
    }
    RECEIPT_OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
