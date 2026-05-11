from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MISSING_SHADOW_DIR = ROOT / "_database_v3k_missing_smoke"

from strategy.v3k_analyzer_adapter import (
    ANALYZER_MODULE_CONTRACTS,
    FLAG_BACKTEST_LEARNING,
    LEARNING_DB_CONTRACTS,
    LearningLoadRequest,
    V3KLearningDataAdapter,
    learning_query_for_request,
    safe_identifier,
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


def _requests() -> list[LearningLoadRequest]:
    requests: list[LearningLoadRequest] = []
    for kind in LEARNING_DB_CONTRACTS:
        tick_modes = (False,) if kind == "candle_pattern" else (True, False)
        for is_tick in tick_modes:
            requests.append(
                LearningLoadRequest(
                    kind=kind,
                    code=f"SMOKE-{kind}-{'tick' if is_tick else 'min'}",
                    backtest_date=20260509,
                    strategy_gubun="stock",
                    is_tick=is_tick,
                    limit=5,
                )
            )
    return requests


def _assert_cutoff_query(request: LearningLoadRequest) -> None:
    query, params, table_name = learning_query_for_request(request)
    if "last_update < ?" not in query:
        raise AssertionError(f"{request.kind}: strict cutoff missing: {query}")
    if "last_update <= ?" in query:
        raise AssertionError(f"{request.kind}: leakage-prone cutoff found: {query}")
    if params[1] != 20260509:
        raise AssertionError(f"{request.kind}: unexpected cutoff params: {params}")
    if not table_name.startswith("stock_"):
        raise AssertionError(f"{request.kind}: unexpected table name: {table_name}")


def _assert_disabled_path(adapter: V3KLearningDataAdapter, request: LearningLoadRequest) -> None:
    result = adapter.load_before_backtest(request)
    if result.rows:
        raise AssertionError(f"{request.kind}: disabled path returned rows")
    if "disabled" not in " ".join(result.diagnostics):
        raise AssertionError(f"{request.kind}: disabled diagnostic missing: {result.diagnostics}")


def _assert_missing_db_path(request: LearningLoadRequest) -> None:
    contract = ANALYZER_MODULE_CONTRACTS[request.kind]
    enabled_request = LearningLoadRequest(
        kind=request.kind,
        code=request.code,
        backtest_date=request.backtest_date,
        strategy_gubun=request.strategy_gubun,
        is_tick=request.is_tick,
        feature_flags={
            FLAG_BACKTEST_LEARNING: True,
            contract.feature_flag: True,
        },
        limit=request.limit,
    )
    adapter = V3KLearningDataAdapter(base_dir=MISSING_SHADOW_DIR)
    result = adapter.load_before_backtest(enabled_request)
    if result.rows:
        raise AssertionError(f"{request.kind}: missing DB path returned rows")
    if "missing" not in " ".join(result.diagnostics):
        raise AssertionError(f"{request.kind}: missing DB diagnostic missing: {result.diagnostics}")
    if result.db_path.exists():
        raise AssertionError(f"{request.kind}: loader created DB path: {result.db_path}")


def main() -> int:
    before = _runtime_artifact_status()
    if before:
        raise AssertionError("runtime artifact status is dirty before smoke: " + before)

    disabled_adapter = V3KLearningDataAdapter()
    for request in _requests():
        _assert_cutoff_query(request)
        _assert_disabled_path(disabled_adapter, request)
        _assert_missing_db_path(request)
        print(
            "learning load contract ok: "
            f"{request.kind} {'tick' if request.is_tick else 'min'}"
        )

    try:
        safe_identifier("stock;DROP")
    except ValueError:
        print("unsafe identifier guard ok")
    else:
        raise AssertionError("unsafe identifier guard did not reject SQL-like value")

    after = _runtime_artifact_status()
    if after != before:
        raise AssertionError(
            f"runtime artifact status changed during smoke: before={before!r} after={after!r}"
        )

    print("v3k learning loader smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
