"""Audit the V3K preparation-first sequence without actual gate execution.

This script is the executable companion to
``docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md``.

It validates the P1~P5 preparation lane only:

- P1 F1 cutover prep: dry-run report + guarded apply/rollback policy.
- P2 Phase F prep: default-OFF smoke + parity baseline.
- P3 Phase G prep: parity + benchmark proof.
- P4 F7 prep: closure remains blocked before actual Step 2~5 evidence.
- P5 checkpoint: aggregate readiness summary.

It intentionally does not:

- issue USER_ACK environment variables,
- call Kiwoom live connect/login,
- write operating ``_database/``,
- flip feature flags default-ON,
- declare V3K mission completion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EVIDENCE_DIR = ROOT / "docs" / "evidence"
SCHEMA_VERSION = 1
PREPARATION_PLAN = "docs/plans/2026-05-15_v3k_preparation_first_execution_sequence_plan.md"
STATUS_PLAN = "docs/plans/2026-05-15_v3k_step2_to_step6_progress_status_plan.md"

GUARDED_STATUS_PATHS = (
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    "v3k_settings*.json",
    "_v3k_sidecar",
)

ACTUAL_EVIDENCE_PATTERNS = (
    "v3k-phase-h-h2-execution-*.json",
    "v3k-f1-cutover-result-*.json",
    "v3k-phase-f-f4-on-*.json",
    "v3k-phase-g-g3-on-*.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _host_identifier() -> str:
    return hashlib.sha256(platform.node().encode()).hexdigest()[:8]


def _run_python(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != expect:
        raise AssertionError(
            "unexpected command result\n"
            f"args={[sys.executable, *args]}\n"
            f"expected={expect} actual={result.returncode}\n"
            f"stdout={result.stdout}\n"
            f"stderr={result.stderr}",
        )
    return result


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def _guarded_status() -> str:
    return _run_git("status", "--short", "--", *GUARDED_STATUS_PATHS)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _json_from_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"stdout was not JSON: {result.stdout}") from exc


def _json_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_no_guarded_status_change(before: str, after: str, label: str) -> None:
    if before != after:
        raise AssertionError(
            f"{label} changed guarded runtime artifacts:\n"
            f"before={before!r}\n"
            f"after={after!r}",
        )


def _static_guard_tokens(path: str, tokens: tuple[str, ...]) -> list[str]:
    text = _read(path)
    return [token for token in tokens if token not in text]


def _p1_f1_cutover_prep() -> dict[str, Any]:
    before = _guarded_status()
    cutover = _json_from_stdout(_run_python("scripts/cutover_v3k_shadow_to_database.py", "--stdout"))
    after = _guarded_status()
    _assert_no_guarded_status_change(before, after, "P1 cutover dry-run")

    cutover_missing = _static_guard_tokens(
        "scripts/cutover_v3k_shadow_to_database.py",
        (
            'ACK_ENV = "V3K_CUTOVER_USER_ACK"',
            "--backup-first is required for cutover --apply",
            "--allow-operating-target is required to write the real _database directory",
        ),
    )
    rollback_missing = _static_guard_tokens(
        "scripts/rollback_v3k_cutover.py",
        (
            'ACK_ENV = "V3K_CUTOVER_USER_ACK"',
            "--allow-operating-target is required to write the real _database directory",
        ),
    )
    if cutover_missing or rollback_missing:
        raise AssertionError(
            f"P1 guard token missing: cutover={cutover_missing}, rollback={rollback_missing}",
        )

    return {
        "step": "P1",
        "name": "F1 cutover prep package",
        "ready": cutover.get("mode") == "dry-run",
        "cutover_mode": cutover.get("mode"),
        "shadow_dir_exists": bool(cutover.get("shadow", {}).get("exists")),
        "target_dir_exists": bool(cutover.get("target", {}).get("exists")),
        "shadow_file_count": int(cutover.get("shadow", {}).get("file_count", 0)),
        "target_file_count": int(cutover.get("target", {}).get("file_count", 0)),
        "rollback_guard_present": True,
        "actual_cutover_attempted": False,
        "operating_database_write_attempted": False,
        "user_ack_env_issued": False,
    }


def _p2_phase_f_prep() -> dict[str, Any]:
    before = _guarded_status()
    default_off = _run_python("scripts/smoke_v3k_phase_f_default_off.py")
    report_path = ROOT / ".omx" / "reports" / "v3k-prep-phase-f-parity.json"
    parity = _run_python(
        "scripts/backtest_v3k_phase_f_parity.py",
        "--report",
        str(report_path.relative_to(ROOT)),
    )
    after = _guarded_status()
    _assert_no_guarded_status_change(before, after, "P2 Phase F prep")
    report = _json_file(report_path)
    return {
        "step": "P2",
        "name": "Phase F F-4 prep package",
        "ready": bool(report.get("passed")),
        "default_off_smoke_passed": "v3k phase f default-OFF smoke passed" in default_off.stdout,
        "parity_passed": bool(report.get("passed")),
        "limits": report.get("limits"),
        "deltas": report.get("deltas"),
        "runtime_hook_connected": bool(report.get("runtime_hook_connected")),
        "live_order_exit_consumption": bool(report.get("live_order_exit_consumption")),
        "operating_database_written": bool(report.get("operating_database_written")),
        "actual_flip_attempted": False,
        "user_ack_env_issued": False,
        "report_path": str(report_path.relative_to(ROOT)).replace("\\", "/"),
        "stdout_tail": parity.stdout.strip().splitlines()[-2:],
    }


def _p3_phase_g_prep() -> dict[str, Any]:
    before = _guarded_status()
    parity_path = ROOT / ".omx" / "reports" / "v3k-prep-phase-g-parity.json"
    benchmark_path = ROOT / ".omx" / "reports" / "v3k-prep-phase-g-benchmark.json"
    _run_python(
        "scripts/backtest_v3k_phase_g_parity.py",
        "--report",
        str(parity_path.relative_to(ROOT)),
    )
    _run_python(
        "scripts/benchmark_v3k_phase_g_engine.py",
        "--report",
        str(benchmark_path.relative_to(ROOT)),
    )
    after = _guarded_status()
    _assert_no_guarded_status_change(before, after, "P3 Phase G prep")
    parity = _json_file(parity_path)
    benchmark = _json_file(benchmark_path)
    return {
        "step": "P3",
        "name": "Phase G G-3 prep package",
        "ready": bool(parity.get("passed")) and bool(benchmark.get("passed")),
        "parity_passed": bool(parity.get("passed")),
        "benchmark_passed": bool(benchmark.get("passed")),
        "parity_limit": parity.get("parity_limit"),
        "performance_limit": benchmark.get("performance_limit"),
        "elapsed_seconds": benchmark.get("elapsed_seconds"),
        "max_seconds": benchmark.get("max_seconds"),
        "peak_bytes": benchmark.get("peak_bytes"),
        "max_peak_bytes": benchmark.get("max_peak_bytes"),
        "runtime_hook_connected": bool(parity.get("runtime_hook_connected")),
        "live_decision_consumption": bool(parity.get("live_decision_consumption")),
        "broker_runtime_called": bool(parity.get("broker_runtime_called")),
        "operating_store_written": bool(parity.get("operating_store_written")),
        "actual_flip_attempted": False,
        "user_ack_env_issued": False,
        "parity_report_path": str(parity_path.relative_to(ROOT)).replace("\\", "/"),
        "benchmark_report_path": str(benchmark_path.relative_to(ROOT)).replace("\\", "/"),
    }


def _p4_f7_closure_prep() -> dict[str, Any]:
    before = _guarded_status()
    gate_audit = _run_python("scripts/audit_v3k_gate5_gate6_review_only_blocked.py")
    after = _guarded_status()
    _assert_no_guarded_status_change(before, after, "P4 F7 closure prep")
    actual_evidence = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for pattern in ACTUAL_EVIDENCE_PATTERNS
        for path in EVIDENCE_DIR.glob(pattern)
    )
    actual_evidence_complete = len(actual_evidence) >= 4
    return {
        "step": "P4",
        "name": "F7 closure prep package",
        "ready": True,
        "actual_evidence_files": actual_evidence,
        "actual_evidence_complete": actual_evidence_complete,
        "mission_complete_commit_allowed": False,
        "closure_ready": False,
        "blocked_as_expected": "Blocked review-only targets" in gate_audit.stdout,
        "gate_audit_stdout_tail": gate_audit.stdout.strip().splitlines()[-4:],
    }


def _p5_checkpoint(prep_results: list[dict[str, Any]]) -> dict[str, Any]:
    all_ready = all(bool(result.get("ready")) for result in prep_results)
    actual_side_effects = {
        "live_connect_attempted": False,
        "operating_database_write_attempted": False,
        "feature_flag_default_on_changed": False,
        "user_ack_env_issued": False,
        "mission_complete_commit_emitted": False,
    }
    return {
        "step": "P5",
        "name": "Preparation-first checkpoint",
        "ready": all_ready and not any(actual_side_effects.values()),
        "prep_steps_ready": [result["step"] for result in prep_results if result.get("ready")],
        "actual_side_effects": actual_side_effects,
        "next_actual_gate": "phase-h-h2-h3-live-dryrun-await-user-approval",
        "actual_execution_blocked_until_user_trigger": True,
    }


def build_report() -> dict[str, Any]:
    missing_docs = [path for path in (PREPARATION_PLAN, STATUS_PLAN) if not (ROOT / path).is_file()]
    if missing_docs:
        raise AssertionError(f"required V3K preparation docs missing: {missing_docs}")

    before = _guarded_status()
    p1 = _p1_f1_cutover_prep()
    p2 = _p2_phase_f_prep()
    p3 = _p3_phase_g_prep()
    p4 = _p4_f7_closure_prep()
    p5 = _p5_checkpoint([p1, p2, p3, p4])
    after = _guarded_status()
    _assert_no_guarded_status_change(before, after, "V3K preparation-first sequence")

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_kind": "v3k_preparation_first_sequence",
        "timestamp_utc": _utc_now(),
        "host_identifier": _host_identifier(),
        "basis_plan": PREPARATION_PLAN,
        "status_plan": STATUS_PLAN,
        "prep_results": [p1, p2, p3, p4, p5],
        "preparation_lane_complete": bool(p5["ready"]),
        "actual_lane_complete": False,
        "actual_execution_order_unchanged": True,
        "scope_guard": {
            "kiwoom_runtime_mutated": False,
            "operating_database_write_attempted": False,
            "live_connect_attempted": False,
            "user_ack_env_issued": False,
            "feature_flag_default_on_changed": False,
            "mission_complete_commit_emitted": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit V3K preparation-first P1~P5 readiness.")
    parser.add_argument("--stdout", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument(
        "--evidence",
        type=Path,
        help="Optional committed evidence path. Omit to avoid writing docs/evidence.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    if args.evidence:
        evidence_path = args.evidence if args.evidence.is_absolute() else ROOT / args.evidence
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"V3K preparation-first evidence written: {evidence_path.relative_to(ROOT)}")
    if args.stdout or not args.evidence:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"preparation_lane_complete={report['preparation_lane_complete']}")
        print("actual_lane_complete=False")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
