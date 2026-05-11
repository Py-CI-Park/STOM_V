from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSING_SHADOW_DIR = ROOT / "_database_v3k_missing_smoke"

if "talib" not in sys.modules:
    talib_stub = types.ModuleType("talib")
    talib_stub.stream = types.SimpleNamespace()
    sys.modules["talib"] = talib_stub

from backtest.backengine_base import BackEngineBase
from strategy.v3k_analyzer_adapter import (
    FLAG_BACKTEST_LEARNING,
    FLAG_CANDLE_ANALYSIS,
    FLAG_VOLATILITY_PATTERN_ANALYSIS,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
    FLAG_VOLUME_PROFILE_ANALYSIS,
    FLAG_VOLUME_SPIKE_ANALYSIS,
    V3KLearningDataAdapter,
)

RUNTIME_ARTIFACT_PATHS = (
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
)


def _runtime_artifact_status() -> str:
    return subprocess.run(
        ["git", "status", "--short", "--", *RUNTIME_ARTIFACT_PATHS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _dummy_engine(*, enabled: bool, is_tick: bool) -> BackEngineBase:
    engine = object.__new__(BackEngineBase)
    engine.market_gubun = 1
    engine.is_tick = is_tick
    engine.v3k_learning_loader = V3KLearningDataAdapter(base_dir=MISSING_SHADOW_DIR)
    engine.v3k_learning_load_plan = {}
    engine.dict_set = {
        FLAG_BACKTEST_LEARNING: enabled,
        FLAG_CANDLE_ANALYSIS: enabled,
        FLAG_VOLUME_SPIKE_ANALYSIS: enabled,
        FLAG_VOLUME_PROFILE_ANALYSIS: enabled,
        FLAG_VOLATILITY_PATTERN_ANALYSIS: enabled,
        FLAG_VOLATILITY_STOP_TAKE_ANALYSIS: enabled,
    }
    return engine


def _assert_off_noop() -> None:
    engine = _dummy_engine(enabled=False, is_tick=False)
    result = engine.PrepareV3KLearningLoadPlan("SMOKE", 20260509)
    if result:
        raise AssertionError(f"OFF hook returned load results: {result}")
    if engine.v3k_learning_load_plan:
        raise AssertionError("OFF hook mutated v3k_learning_load_plan")
    print("backtest hook OFF no-op ok")


def _assert_enabled_missing_db_noop(*, is_tick: bool, expected_count: int) -> None:
    engine = _dummy_engine(enabled=True, is_tick=is_tick)
    result = engine.PrepareV3KLearningLoadPlan("SMOKE", 20260509)
    if len(result) != expected_count:
        raise AssertionError(f"unexpected load result count: {len(result)} != {expected_count}")
    if ("SMOKE", 20260509) not in engine.v3k_learning_load_plan:
        raise AssertionError("enabled hook did not record load plan")
    for item in result:
        diagnostics = " ".join(item.diagnostics)
        if "missing" not in diagnostics:
            raise AssertionError(f"missing DB diagnostic not found: {item}")
        if item.rows:
            raise AssertionError(f"missing DB hook returned rows: {item.rows}")
    mode = "tick" if is_tick else "min"
    print(f"backtest hook ON missing-DB no-op ok: {mode}")


def main() -> int:
    before = _runtime_artifact_status()
    if before:
        raise AssertionError("runtime artifact status is dirty before smoke: " + before)

    _assert_off_noop()
    _assert_enabled_missing_db_noop(is_tick=True, expected_count=4)
    _assert_enabled_missing_db_noop(is_tick=False, expected_count=5)

    after = _runtime_artifact_status()
    if after != before:
        raise AssertionError(
            f"runtime artifact status changed during smoke: before={before!r} after={after!r}"
        )
    print("v3k backtest learning hook smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
