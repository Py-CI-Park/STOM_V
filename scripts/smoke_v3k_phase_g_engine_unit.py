from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import DEFAULT_FLAGS, FLAG_PHASE_G_MICROSTRUCTURE_ENGINE
from strategy.v3k_microstructure_engine import (
    ENGINE_OUTPUT_NAMES,
    KIWOOM_OPT_FIELD_MAPPING,
    V3KMicrostructureEngine,
)


def _row(price: float, bid_scale: float, ask_scale: float) -> dict[str, float]:
    row: dict[str, float] = {
        "현재가": price,
        "초당매수수량": 220.0 * bid_scale,
        "초당매도수량": 120.0 * ask_scale,
    }
    for level in range(1, 6):
        row[f"매도호가{level}"] = price + level * 5
        row[f"매수호가{level}"] = price - level * 5
        row[f"매도잔량{level}"] = (100.0 - level * 8) * ask_scale
        row[f"매수잔량{level}"] = (150.0 - level * 6) * bid_scale
    return row


def main() -> None:
    if DEFAULT_FLAGS[FLAG_PHASE_G_MICROSTRUCTURE_ENGINE] is not False:
        raise AssertionError("Phase G feature flag must remain default-OFF")

    disabled_engine = V3KMicrostructureEngine()
    disabled_result = disabled_engine.analyze_mapping(_row(1000.0, 1.0, 1.0), code="TEST")
    if disabled_result.enabled or disabled_result.signal != "disabled":
        raise AssertionError(f"default-OFF result mismatch: {disabled_result}")

    enabled_engine = V3KMicrostructureEngine(enabled=True)
    results = [
        enabled_engine.analyze_mapping(_row(1000.0, 1.00, 0.95), code="TEST"),
        enabled_engine.analyze_mapping(_row(1005.0, 1.10, 0.90), code="TEST"),
        enabled_engine.analyze_mapping(_row(1010.0, 1.20, 0.85), code="TEST"),
        enabled_engine.analyze_mapping(_row(1015.0, 1.25, 0.80), code="TEST"),
        enabled_engine.analyze_mapping(_row(1020.0, 1.30, 0.75), code="TEST"),
    ]
    final = results[-1]
    if not final.enabled:
        raise AssertionError("enabled test engine did not analyze caller-owned fixture")
    if final.signal not in {"buy", "sell", "hold"}:
        raise AssertionError(f"unexpected signal: {final.signal}")
    if not 0.0 <= final.confidence <= 1.0:
        raise AssertionError(f"confidence out of range: {final.confidence}")
    if not 0.0 <= final.total_risk <= 1.0:
        raise AssertionError(f"risk out of range: {final.total_risk}")
    values = final.as_formula_values()
    if tuple(values.keys()) != ENGINE_OUTPUT_NAMES:
        raise AssertionError(f"output contract mismatch: {values.keys()}")
    if KIWOOM_OPT_FIELD_MAPPING["current_price"] != "현재가":
        raise AssertionError("Kiwoom mapping contract changed unexpectedly")

    print("V3K Phase G engine default-OFF and unit smoke passed")
    print(f"final signal={final.signal}, confidence={final.confidence}, risk={final.total_risk}")


if __name__ == "__main__":
    main()
