"""Read-only P1-P7 condition-process platform contract audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _has(relative: str, *needles: str) -> bool:
    text = _text(relative)
    return all(needle in text for needle in needles)


def _not_has(relative: str, *needles: str) -> bool:
    text = _text(relative)
    return all(needle not in text for needle in needles)


def _runtime_contract() -> bool:
    from ai_strategy_loop.revision.probabilistic_discovery_d2 import propose_d2_batch

    batch = propose_d2_batch(seed=20260815, per_family_budget=4)
    return len(batch.candidates) == 16 and all(item.execution_ok for item in batch.candidates)


def _tick_catalog_contract() -> bool:
    from ai_strategy_loop.revision.variable_catalog import catalog_payload

    catalog = catalog_payload("tick")
    source = json.dumps(catalog, ensure_ascii=False, default=str)
    return all(symbol not in source for symbol in ("분봉시가", "분봉고가", "분봉저가"))


def run_audit() -> dict[str, object]:
    checks: list[tuple[str, str, Callable[[], bool]]] = [
        ("P1", "d2_runtime_contract_16_of_16", _runtime_contract),
        ("P1", "tick_catalog_excludes_minute_symbols", _tick_catalog_contract),
        ("P1", "job_strategy_result_csv_snapshots", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_jobs.py",
            "STOM_CLI_DB_STRATEGY", "STOM_CLI_DB_BACKTEST", "STOM_CLI_BACKTEST_CSV_DIR",
        )),
        ("P1", "cli_metrics_match_exact_sources", lambda: _has(
            "cli/runner.py", '"매수전략" = ?', '"매도전략" = ?', "_current_strategy_source_filter",
        )),
        ("P1", "backtest_csv_directory_is_overridable", lambda: _has(
            "backtest/backtest.py", "STOM_CLI_BACKTEST_CSV_DIR",
        )),
        ("P2", "tick_min_date_range_width_safe", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_api.py", "_back_index_date",
        )),
        ("P2", "artifact_reads_use_safe_resolver", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_api.py", "_resolve_artifact_path", "failed_reasons",
        )),
        ("P3", "source_hash_verified_before_spawn", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_jobs.py", "source snapshot hash verification failed",
        )),
        ("P4", "telemetry_and_selection_pareto_split", lambda: _has(
            "ai_strategy_loop/labeling/run_d1_engine_screen.py", "selection_pareto", "underpowered_evidence",
        )),
        ("P4", "family_top_k_supported", lambda: _has(
            "ai_strategy_loop/labeling/run_d2_engine_screen.py", "family_top_k",
        )),
        ("P5", "bucket_tests_use_bh_fdr", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_analysis.py", "q_value", "fdr_pass",
        )),
        ("P5", "bayesian_combined_limit_enforced", lambda: _has(
            "ai_strategy_loop/dashboard/research_tools_api.py", "max_bayesian_sample", "MAX_OBSERVATION_COUNT",
        )),
        ("P6", "analysis_snapshot_get_does_not_persist", lambda: _not_has(
            "ai_strategy_loop/dashboard/analysis_snapshot.py", "persist_analysis_bundle(payload",
        )),
        ("P6", "ledger_reads_are_sqlite_readonly", lambda: _has(
            "ai_strategy_loop/dashboard/strategy_ledger_api.py", "mode=ro",
        )),
        ("P6", "trade_path_reads_are_sqlite_readonly", lambda: (
            _has("ai_strategy_loop/dashboard/trade_path_api.py", "mode=ro")
            and _has("ai_strategy_loop/dashboard/trade_path_report.py", "mode=ro")
            and _has("ai_strategy_loop/dashboard/sell_dsl_api.py", "_readonly_trade_path_job")
        )),
        ("P6", "portfolio_missing_artifact_fails", lambda: _has(
            "ai_strategy_loop/dashboard/backtest_api.py", "failed_reasons", "job_csv_missing",
        )),
        ("P7", "candidate_identity_is_mandatory", lambda: (
            _has("ai_strategy_loop/dashboard/frontend/v4-research.jsx", "candidate_identity")
            and _not_has("ai_strategy_loop/dashboard/app.py", "P5_BALANCED_CANDIDATE")
        )),
        ("P7", "legacy_final_approval_removed", lambda: _not_has(
            "ai_strategy_loop/dashboard/frontend/app.jsx", "final_approval", "ApprovalDialog",
        )),
        ("P7", "promotion_gate_is_post_and_pure_by_default", lambda: _has(
            "ai_strategy_loop/dashboard/trade_path_official_api.py",
            '@official_trade_path_router.post("/promotion-gate")', "persist: bool = False",
        )),
        ("P7", "product_release_is_v5_15", lambda: _has(
            "ai_strategy_loop/dashboard/app.py", '_DASHBOARD_RELEASE = "v5.15.0"',
        )),
    ]
    rows = []
    for track, check_id, check in checks:
        try:
            passed = bool(check())
            error = None
        except Exception as exc:  # audit must report every lane, not stop at first error
            passed = False
            error = f"{type(exc).__name__}: {exc}"
        rows.append({"track": track, "check_id": check_id, "passed": passed, "error": error})
    failed = [row["check_id"] for row in rows if not row["passed"]]
    return {
        "schema": "stom.condition_process_platform_audit.v1",
        "authority": "read_only_diagnostic",
        "checks": rows,
        "passed": len(rows) - len(failed),
        "total": len(rows),
        "failed": failed,
        "verdict": "PASS" if not failed else "FAIL",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_audit()
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    raise SystemExit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
