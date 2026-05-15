"""V3K Phase H Gate4 environment status audit (Option B parallel, plan §C T01).

This audit is the **active polling** companion to the historical frozen audit
``scripts/audit_v3k_phase_h_gate4_blocked_environment.py`` (commit ``b6327b30``).

Branching policy (LH4 ↔ V07 invariant, plan v2 §D.1):

- ``khopenapi_compatible == True``  → ``_assert_environment_unblocked()``
- ``khopenapi_compatible == False`` → ``_assert_environment_blocked_or_pending()``

Historical script identity is preserved (rename rejected, Option B accepted in
``docs/plans/2026-05-15_v3k_phase_h_lh4_clarification_plan.md`` §I.3). This
script never imports, mutates, or replaces the historical one — it is a
parallel emitter.

LH5 forward-only invariant: this script emits with ``schema_version == 2``
audit JSON (inherited from ``audit_v3k_phase_h_env_check.py``). Historical
``b6327b30`` ``schema_version == 1`` artifacts are out of scope (no retroactive
re-evaluation).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_phase_h_env_check import (  # noqa: E402
    AUDIT_SCHEMA_VERSION,
    _assert_default_off_and_sentinel_contract,
    _assert_hook_source_guard,
    _assert_runtime_paths_clean,
    build_report,
)
from scripts.check_v3k_gate_approval_phrase import evaluate_approval_phrase  # noqa: E402
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE  # noqa: E402

AUDIT_VERSION = "V3K_PHASE_H_GATE4_ENV_STATUS_AUDIT_V1"
PHASE_H_GATE = "phase-h-h2-h3-live-dryrun-await-user-approval"
PHASE_H_PHRASE = "I approve phase-h-h2-h3-live-dryrun-await-user-approval only"
BLOCKED_HEADING = "## V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED"
COMPLETION_HEADING = "## V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL"
REGISTRY = "docs/CARRY_FORWARD_REGISTRY.md"
FORBIDDEN_STATUS_PATHS = (
    "_database",
    "_database_v3k_shadow",
    "_log",
    "backup",
    "*.db",
    "backtest/graph",
    ".omx/reports",
    "v3k_settings*.json",
)


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


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def _registry_headings() -> set[str]:
    return {
        line.strip()
        for line in _read(REGISTRY).splitlines()
        if line.startswith("## ")
    }


def _assert_lh5_forward_only(report: dict) -> None:
    # LH5: schema_version >= 2 only; schema_version == 1 historical artifacts excluded.
    schema_version = int(report.get("schema_version", 0))
    if schema_version < 2:
        raise AssertionError(
            f"LH5 forward-only violation: this audit requires schema_version >= 2; got {schema_version}",
        )


def _assert_environment_unblocked() -> dict:
    # Primary signal exists branch (V05 SKIP equivalent for the historical blocked-env audit).
    _assert_hook_source_guard()
    _assert_default_off_and_sentinel_contract()
    _assert_runtime_paths_clean()
    report = build_report()
    _assert_lh5_forward_only(report)
    if not report["khopenapi_compatible"]:
        raise AssertionError(
            "environment_status audit unblocked path called but khopenapi_compatible=False; "
            "use the blocked_or_pending branch instead",
        )
    primary = report.get("khopenapi_primary_signal", {})
    if not primary.get("exists"):
        raise AssertionError(
            "V07 invariant violation: khopenapi_compatible=True but primary_signal.exists=False",
        )
    if report.get("live_connect_attempted") or report.get("order_or_exit_path_changed"):
        raise AssertionError(
            f"Phase H Gate4 environment_status audit must not attempt live/connect or mutate order paths: {report}",
        )
    return report


def _assert_environment_blocked_or_pending() -> dict:
    # Primary signal absent branch (parity with historical _assert_environment_blocked).
    _assert_hook_source_guard()
    _assert_default_off_and_sentinel_contract()
    _assert_runtime_paths_clean()
    report = build_report()
    _assert_lh5_forward_only(report)
    if report["khopenapi_compatible"]:
        raise AssertionError(
            "environment_status audit blocked_or_pending path called but khopenapi_compatible=True; "
            "use the unblocked branch instead",
        )
    if report.get("live_connect_attempted") or report.get("order_or_exit_path_changed"):
        raise AssertionError(
            f"Phase H Gate4 environment_status audit must not attempt live/connect or mutate order paths: {report}",
        )
    return report


def _assert_registry_headings() -> None:
    headings = _registry_headings()
    if BLOCKED_HEADING not in headings:
        raise AssertionError(f"historical blocked approval heading missing: {BLOCKED_HEADING}")
    # COMPLETION_HEADING may or may not exist depending on later approval state;
    # this audit does not enforce its absence (left to the historical blocked-env audit
    # and to actual H-2 completion gates that own that invariant).


def _assert_runtime_boundaries() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_STATUS_PATHS)
    if status:
        raise AssertionError(f"forbidden runtime/DB artifact status is not clean:\n{status}")
    tracked = _run_git("ls-files", V3K_GUI_SIDECAR_FILE)
    if tracked:
        raise AssertionError(f"runtime sidecar artifact must remain untracked: {tracked}")
    for rel_path in ("trade/base_strategy.py", "trade/formula_manager.py"):
        text = (ROOT / rel_path).read_text(encoding="utf-8", errors="replace")
        if "V3K" in text or "v3k_" in text.lower():
            raise AssertionError(
                f"Phase H Gate4 environment_status audit must not wire live runtime file: {rel_path}",
            )


def _assert_phrase_state(report: dict) -> None:
    # LH4 branching: primary True → phrase pending H-2 execution; primary False → phrase still current pre-execution.
    # Both branches leave the phrase as "current" until H-2 actually runs (which is out of scope here).
    verdict = evaluate_approval_phrase(PHASE_H_PHRASE)
    if not verdict.accepted or verdict.gate != PHASE_H_GATE:
        raise AssertionError(f"Phase H phrase must remain current until live-dryrun evidence exists: {verdict}")
    next_verdict = evaluate_approval_phrase("I approve f1-actual-db-cutover-await-user-approval only")
    if next_verdict.accepted:
        raise AssertionError(f"F1 cutover phrase must remain blocked while Phase H is incomplete: {next_verdict}")


def main() -> None:
    # Branching entrypoint (plan v2 §D.1).
    report = build_report()
    _assert_lh5_forward_only(report)
    if report["khopenapi_compatible"]:
        _assert_environment_unblocked()
        _assert_registry_headings()
        _assert_runtime_boundaries()
        _assert_phrase_state(report)
        print("V3K Phase H gate4 environment_status audit passed (branch: unblocked)")
        print(f"Gate4 environment_status audit version: {AUDIT_VERSION}")
        print(f"schema_version: {report['schema_version']} (LH5 forward-only compliant)")
        print("primary_signal.exists=True; H-2 dry-run execution requires explicit user approval + V3K_PHASE_H_USER_ACK=1")
        print(f"Current approval gate remains: {PHASE_H_GATE}")
    else:
        _assert_environment_blocked_or_pending()
        _assert_registry_headings()
        _assert_runtime_boundaries()
        _assert_phrase_state(report)
        print("V3K Phase H gate4 environment_status audit passed (branch: blocked_or_pending)")
        print(f"Gate4 environment_status audit version: {AUDIT_VERSION}")
        print(f"schema_version: {report['schema_version']} (LH5 forward-only compliant)")
        print("primary_signal.exists=False; KHOPENAPI environment unavailable, H-2 dry-run cannot proceed")
        print(f"Current approval gate remains: {PHASE_H_GATE}")


if __name__ == "__main__":
    main()
