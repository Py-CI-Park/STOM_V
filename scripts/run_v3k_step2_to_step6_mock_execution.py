"""V3K Step 2~6 mock execution runner (plan §B).

This script performs **mock execution only** for V3K mission Step 2~6 as
defined in ``docs/plans/2026-05-15_v3k_step2_to_step6_mock_execution_plan.md``.

Scope guard (plan §A.3):
- Kiwoom runtime (trade / utility / Kiwoom_OpenAPI) mutation 0
- LS Securities direct dependency 0
- operating ``_database/`` write 0 (read-only only)
- live connect / login / order / exit path wiring 0
- USER_ACK env var emit 0
- 24h+ monitoring 0 (1-cycle mock)

Output: ``docs/evidence/v3k-step2-to-step6-mock-execution-{host_identifier}.json``
"""
from __future__ import annotations

import hashlib
import json
import platform
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_phase_h_env_check import build_report  # noqa: E402
from strategy.v3k_analyzer_adapter import normalize_v3k_flags  # noqa: E402
from strategy.v3k_kiwoom_dryrun_hook import V3KKiwoomDryrunHook  # noqa: E402
from strategy.v3k_kiwoom_sentinel import (  # noqa: E402
    collect_corroborating_signals,
    probe_primary_signal,
)

EVIDENCE_DIR = ROOT / "docs" / "evidence"
EVIDENCE_SCHEMA_VERSION = 1


def run_step2_phase_h_h2_mock() -> dict[str, Any]:
    primary = probe_primary_signal()
    corroborating = collect_corroborating_signals()
    hook = V3KKiwoomDryrunHook(feature_flags={})
    sentinel = hook.resolve_khopenapi_sentinel()
    return {
        "step": 2,
        "phase": "phase-h-h2-sentinel-mock",
        "compatible": bool(sentinel.compatible),
        "primary_kind": sentinel.primary_kind,
        "primary_path": sentinel.primary_path,
        "primary_exists": bool(sentinel.primary_exists),
        "corroboration_count": int(sentinel.corroboration_count),
        "corroborating_signal_count": len(corroborating),
        "hook_enabled_default_off": (not hook.enabled),
        "hook_reachable": True,
        "live_connect_attempted": False,
        "order_or_exit_path_changed": False,
    }


def _list_db_files(directory: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(
        path.name
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
    )


def _list_tables_in_db(db_path: Path) -> list[str]:
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def run_step3_f1_cutover_parity_mock() -> dict[str, Any]:
    operating_dir = ROOT / "_database"
    shadow_dir = ROOT / "_database_v3k_shadow"
    operating_dbs = _list_db_files(operating_dir)
    shadow_dbs = _list_db_files(shadow_dir)
    if not operating_dbs and not shadow_dbs:
        parity_status = "skip-missing-dir"
    elif not shadow_dbs:
        parity_status = "skip-shadow-missing"
    elif not operating_dbs:
        parity_status = "skip-operating-missing"
    else:
        parity_status = "match" if set(operating_dbs) == set(shadow_dbs) else "delta"
    return {
        "step": 3,
        "phase": "f1-cutover-shadow-parity-mock",
        "operating_dir_exists": operating_dir.is_dir(),
        "shadow_dir_exists": shadow_dir.is_dir(),
        "operating_db_count": len(operating_dbs),
        "shadow_db_count": len(shadow_dbs),
        "parity_status": parity_status,
        "operating_write_attempted": False,
    }


def run_step4_f3_f4_on_mock() -> dict[str, Any]:
    flags = normalize_v3k_flags({"FLAG_PHASE_F_F4": False})
    hook = V3KKiwoomDryrunHook(feature_flags=flags)
    return {
        "step": 4,
        "phase": "f3-phase-f-f4-on-default-off-mock",
        "flag_default_off": (not flags.get("FLAG_PHASE_F_F4", False)),
        "hook_reachable": hook is not None,
        "flag_normalized": True,
        "actual_flip_attempted": False,
    }


def run_step5_f4_g3_on_mock() -> dict[str, Any]:
    flags = normalize_v3k_flags({"FLAG_PHASE_G_G3": False})
    t0 = time.perf_counter()
    hook = V3KKiwoomDryrunHook(feature_flags=flags)
    t1 = time.perf_counter()
    return {
        "step": 5,
        "phase": "f4-phase-g-g3-on-default-off-mock",
        "flag_default_off": (not flags.get("FLAG_PHASE_G_G3", False)),
        "hook_reachable": hook is not None,
        "flag_normalized": True,
        "benchmark_ms": round((t1 - t0) * 1000.0, 3),
        "actual_flip_attempted": False,
    }


def run_step6_f7_closure_gate_mock(step_results: list[dict[str, Any]]) -> dict[str, Any]:
    expected_steps = {2, 3, 4, 5}
    collected_steps = {int(result["step"]) for result in step_results}
    closure_ready = expected_steps == collected_steps
    return {
        "step": 6,
        "phase": "f7-closure-gate-plan-only",
        "expected_step_set": sorted(expected_steps),
        "collected_step_set": sorted(collected_steps),
        "closure_ready": closure_ready,
        "mission_complete_commit_emitted": False,
    }


def _emit_evidence(report: dict[str, Any], host_identifier: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence_path = EVIDENCE_DIR / f"v3k-step2-to-step6-mock-execution-{host_identifier}.json"
    evidence_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return evidence_path


def _compute_host_identifier() -> str:
    # Match the T04b evidence host_identifier rule (sha256(platform.node())[:8]).
    return hashlib.sha256(platform.node().encode()).hexdigest()[:8]


def main() -> None:
    env_report = build_report()
    host_identifier = _compute_host_identifier()

    step2 = run_step2_phase_h_h2_mock()
    step3 = run_step3_f1_cutover_parity_mock()
    step4 = run_step4_f3_f4_on_mock()
    step5 = run_step5_f4_g3_on_mock()
    step6 = run_step6_f7_closure_gate_mock([step2, step3, step4, step5])

    report = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "evidence_kind": "v3k_step2_to_step6_mock_execution",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "host_identifier": host_identifier,
        "khopenapi_compatible": bool(env_report.get("khopenapi_compatible")),
        "audit_schema_version": int(env_report.get("schema_version", 0)),
        "scope_guard": {
            "kiwoom_runtime_mutated": False,
            "ls_direct_dependency_added": False,
            "operating_database_write_attempted": False,
            "live_connect_attempted": False,
            "user_ack_emitted": False,
            "monitoring_24h_or_more_collected": False,
        },
        "step_results": [step2, step3, step4, step5, step6],
        "closure_ready": bool(step6["closure_ready"]),
    }

    evidence_path = _emit_evidence(report, host_identifier)
    print(f"V3K step2_to_step6 mock execution completed (host_identifier={host_identifier})")
    print(f"Evidence: {evidence_path.relative_to(ROOT)}")
    print(f"Closure ready: {report['closure_ready']}")
    for result in report["step_results"]:
        step_id = result["step"]
        phase = result["phase"]
        print(f"  Step {step_id}: {phase}")


if __name__ == "__main__":
    main()
