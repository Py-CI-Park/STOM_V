from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSING_SHADOW_DIR = ROOT / "_database_v3k_missing_smoke"

from strategy.v3k_analyzer_adapter import (  # noqa: E402
    FLAG_CANDLE_ANALYSIS,
    FLAG_REALTIME_LEARNING,
    FLAG_VOLATILITY_PATTERN_ANALYSIS,
    FLAG_VOLATILITY_STOP_TAKE_ANALYSIS,
    FLAG_VOLUME_PROFILE_ANALYSIS,
    FLAG_VOLUME_SPIKE_ANALYSIS,
    RealtimeLearningPreloadRequest,
    V3KRealtimeLearningAdapter,
)


def _artifact_status() -> str:
    result = subprocess.run(
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
    )
    return result.stdout.strip()


def _all_feature_flags() -> dict[str, bool]:
    return {
        FLAG_REALTIME_LEARNING: True,
        FLAG_CANDLE_ANALYSIS: True,
        FLAG_VOLUME_SPIKE_ANALYSIS: True,
        FLAG_VOLUME_PROFILE_ANALYSIS: True,
        FLAG_VOLATILITY_PATTERN_ANALYSIS: True,
        FLAG_VOLATILITY_STOP_TAKE_ANALYSIS: True,
    }


def _request(*, is_tick: bool, feature_flags: dict[str, bool] | None = None):
    return RealtimeLearningPreloadRequest(
        codes=("005930", "000660"),
        as_of_date=20260509,
        strategy_gubun="stock",
        is_tick=is_tick,
        feature_flags=feature_flags or {},
        limit=3,
    )


def _assert_off_noop() -> None:
    before = _artifact_status()
    result = V3KRealtimeLearningAdapter(base_dir=MISSING_SHADOW_DIR).preload(_request(is_tick=True))
    after = _artifact_status()

    assert before == after, "OFF path must not create or modify runtime artifacts"
    assert not result.load_results
    assert not result.has_rows
    assert result.diagnostics == (
        "realtime learning preload disabled by V3K feature flags",
    )
    print("realtime learning OFF no-op ok")


def _assert_no_codes_noop() -> None:
    result = V3KRealtimeLearningAdapter(
        base_dir=MISSING_SHADOW_DIR,
        feature_flags={FLAG_REALTIME_LEARNING: True},
    ).preload(
        RealtimeLearningPreloadRequest(
            codes=(),
            as_of_date=20260509,
            strategy_gubun="stock",
            is_tick=True,
        ),
    )

    assert not result.load_results
    assert not result.has_rows
    assert result.diagnostics == ("realtime learning preload skipped: no codes",)
    print("realtime learning no-code no-op ok")


def _assert_enabled_missing_db(is_tick: bool, expected_kinds_per_code: int) -> None:
    before = _artifact_status()
    result = V3KRealtimeLearningAdapter(
        base_dir=MISSING_SHADOW_DIR,
        feature_flags=_all_feature_flags(),
    ).preload(_request(is_tick=is_tick))
    after = _artifact_status()

    expected_total = 2 * expected_kinds_per_code
    assert before == after, "ON missing-DB path must remain read-only/no-create"
    assert result.diagnostics == ("realtime learning preload dry-run executed",)
    assert len(result.load_results) == expected_total
    assert not result.has_rows

    kinds = {load_result.request.kind for load_result in result.load_results}
    if is_tick:
        assert "candle_pattern" not in kinds
    else:
        assert "candle_pattern" in kinds

    for load_result in result.load_results:
        assert load_result.request.feature_flags[FLAG_REALTIME_LEARNING] is True
        assert load_result.params[1] == 20260509
        assert "last_update < ?" in (load_result.query or "")
        assert load_result.diagnostics == (
            "learning DB missing; read-only load skipped",
        )

    label = "tick" if is_tick else "min"
    print(f"realtime learning ON missing-DB no-op ok: {label}")


def main() -> None:
    _assert_off_noop()
    _assert_no_codes_noop()
    _assert_enabled_missing_db(is_tick=True, expected_kinds_per_code=4)
    _assert_enabled_missing_db(is_tick=False, expected_kinds_per_code=5)
    print("v3k realtime learning boundary smoke passed")


if __name__ == "__main__":
    main()
