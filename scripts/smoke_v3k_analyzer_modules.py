from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategy.v3k_analyzer_adapter import (
    ANALYZER_MODULE_CONTRACTS,
    missing_analyzer_fields,
    staged_analyzer_modules,
)
from utility.setting_base import (
    list_coin_min,
    list_coin_tick,
    list_stock_min,
    list_stock_tick,
)

FORBIDDEN_RUNTIME_PATHS = (
    ROOT / "_database",
    ROOT / "_database_v3k_shadow",
    ROOT / "_log",
    ROOT / "backup",
)


def _dict_findex(columns: list[str]) -> dict[str, int]:
    return {name: index for index, name in enumerate(columns)}


def _assert_no_runtime_artifacts() -> None:
    status = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "_database",
            "_database_v3k_shadow",
            "_log",
            "backup",
            "*.db",
            "backtest/graph",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if status:
        raise AssertionError("runtime artifact status changed during module staging smoke: " + status)


def _import_staged_modules() -> None:
    for contract in staged_analyzer_modules():
        module = importlib.import_module(contract.module_name)
        if not hasattr(module, contract.class_name):
            raise AssertionError(
                f"{contract.module_name} missing class {contract.class_name}"
            )
        print(f"import ok: {contract.module_name}.{contract.class_name}")


def _verify_field_contracts() -> None:
    cases = [
        ("stock-tick", True, _dict_findex(list_stock_tick)),
        ("stock-min", False, _dict_findex(list_stock_min)),
        ("coin-tick", True, _dict_findex(list_coin_tick)),
        ("coin-min", False, _dict_findex(list_coin_min)),
    ]

    for label, is_tick, dict_findex in cases:
        for kind, contract in ANALYZER_MODULE_CONTRACTS.items():
            missing = missing_analyzer_fields(kind, dict_findex, is_tick)
            if missing:
                if kind == "candle_pattern" and is_tick:
                    continue
                raise AssertionError(f"{label} {kind} missing fields: {missing}")
            mode = "tick" if is_tick else "min"
            print(f"field contract ok: {label} {contract.kind} ({mode})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Only import staged modules and class symbols.",
    )
    args = parser.parse_args()

    _assert_no_runtime_artifacts()
    _import_staged_modules()
    if not args.import_only:
        _verify_field_contracts()
    _assert_no_runtime_artifacts()
    print("v3k analyzer module staging smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
