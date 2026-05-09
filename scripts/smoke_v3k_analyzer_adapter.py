from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (
    FIELD_CHANGE_RATE_ANGLE,
    FIELD_CHEGYEOL_STRENGTH,
    FIELD_CHEGYEOL_STRENGTH_AVG,
    FIELD_CURRENT_PRICE,
    FIELD_DAY_TRADE_VALUE,
    FIELD_HIGH_LOW_RATIO,
    FIELD_MAX_CURRENT_PRICE,
    FIELD_MIN_BUY_VOLUME,
    FIELD_MIN_CURRENT_PRICE,
    FIELD_MIN_SELL_VOLUME,
    FIELD_TICK_BUY_VOLUME,
    FIELD_TICK_SELL_VOLUME,
    FLAG_BACKTEST_LEARNING,
    FLAG_RISK_ANALYSIS,
    FLAG_RISK_ANALYZER_V3,
    V3KAnalyzerAdapter,
    V3KAnalyzerContext,
    market_type_from_gubun,
)
from utility.setting_base import (
    list_coin_min,
    list_coin_tick,
    list_stock_min,
    list_stock_tick,
)


def _dict_findex(columns: list[str]) -> dict[str, int]:
    return {name: index for index, name in enumerate(columns)}


def _set_if_present(
    data: np.ndarray,
    dict_findex: dict[str, int],
    row: int,
    name: str,
    value: float,
) -> None:
    index = dict_findex.get(name)
    if index is not None:
        data[row, index] = value


def build_fixture(columns: list[str], rows: int = 64) -> tuple[np.ndarray, dict[str, int]]:
    dict_findex = _dict_findex(columns)
    data = np.zeros((rows, len(columns)), dtype=np.float64)

    for row in range(rows):
        price = 100.0 + row * 0.25
        _set_if_present(data, dict_findex, row, FIELD_CURRENT_PRICE, price)
        _set_if_present(data, dict_findex, row, FIELD_DAY_TRADE_VALUE, 100_000.0 + row * 500.0)
        _set_if_present(data, dict_findex, row, FIELD_CHEGYEOL_STRENGTH, 95.0 + row % 7)
        _set_if_present(data, dict_findex, row, FIELD_TICK_BUY_VOLUME, 30.0 + row)
        _set_if_present(data, dict_findex, row, FIELD_TICK_SELL_VOLUME, 20.0 + row)
        _set_if_present(data, dict_findex, row, FIELD_MIN_BUY_VOLUME, 30.0 + row)
        _set_if_present(data, dict_findex, row, FIELD_MIN_SELL_VOLUME, 20.0 + row)
        _set_if_present(data, dict_findex, row, FIELD_HIGH_LOW_RATIO, 0.5)
        _set_if_present(data, dict_findex, row, FIELD_MAX_CURRENT_PRICE, 130.0)
        _set_if_present(data, dict_findex, row, FIELD_MIN_CURRENT_PRICE, 90.0)
        _set_if_present(data, dict_findex, row, FIELD_CHEGYEOL_STRENGTH_AVG, 100.0)
        _set_if_present(data, dict_findex, row, FIELD_CHANGE_RATE_ANGLE, 3.0)

    return data, dict_findex


def run_smoke(enable_v3_risk: bool) -> None:
    cases = [
        ("stock-tick", 1, True, list_stock_tick),
        ("stock-min", 1, False, list_stock_min),
        ("coin-tick", 3, True, list_coin_tick),
        ("coin-min", 3, False, list_coin_min),
    ]

    off_adapter = V3KAnalyzerAdapter()
    on_adapter = V3KAnalyzerAdapter(
        {
            FLAG_BACKTEST_LEARNING: enable_v3_risk,
            FLAG_RISK_ANALYZER_V3: enable_v3_risk,
            FLAG_RISK_ANALYSIS: enable_v3_risk,
        }
    )

    for label, market_gubun, is_tick, columns in cases:
        code_data, dict_findex = build_fixture(columns)
        context = V3KAnalyzerContext(
            market_gubun=market_gubun,
            market_type=market_type_from_gubun(market_gubun),
            is_tick=is_tick,
            dict_findex=dict_findex,
            code_data=code_data,
            code=f"SMOKE-{label}",
            backtest_date=20260509,
        )

        off_result = off_adapter.analyze_risk(context)
        if off_result.risk_score is not None:
            raise AssertionError(f"{label}: OFF risk score must stay None")

        on_result = on_adapter.analyze_risk(context)
        if enable_v3_risk:
            if on_result.risk_score is None:
                raise AssertionError(f"{label}: ON risk score missing: {on_result.diagnostics}")
            if not 0.0 <= on_result.risk_score <= 100.0:
                raise AssertionError(f"{label}: risk score out of range: {on_result.risk_score}")
            print(f"{label}: OFF no-signal, ON risk_score={on_result.risk_score}")
        else:
            if on_result.risk_score is not None:
                raise AssertionError(f"{label}: disabled ON adapter must stay no-signal")
            print(f"{label}: OFF no-signal, ON path intentionally disabled")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--enable-v3-risk",
        action="store_true",
        help="Execute dormant AnalyzerRisk through the adapter smoke path.",
    )
    args = parser.parse_args()
    run_smoke(enable_v3_risk=args.enable_v3_risk)
    print("v3k analyzer adapter smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
