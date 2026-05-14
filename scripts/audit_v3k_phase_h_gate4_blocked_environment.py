from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_phase_h_env_check import (  # noqa: E402
    _assert_default_off_and_sentinel_contract,
    _assert_hook_source_guard,
    _assert_runtime_paths_clean,
    build_report,
)
from scripts.check_v3k_gate_approval_phrase import evaluate_approval_phrase  # noqa: E402
from strategy.v3k_gui_sidecar import V3K_GUI_SIDECAR_FILE  # noqa: E402

AUDIT_VERSION = "V3K_PHASE_H_GATE4_BLOCKED_ENV_AUDIT_V1"
PHASE_H_GATE = "phase-h-h2-h3-live-dryrun-await-user-approval"
PHASE_H_PHRASE = "I approve phase-h-h2-h3-live-dryrun-await-user-approval only"
BLOCKED_HEADING = "## V3K-PHASE-H-LIVE-DRYRUN-APPROVAL-BLOCKED"
COMPLETION_HEADING = "## V3K-PHASE-H-LIVE-DRYRUN-ACTUAL-APPROVAL"
UPDATE_LOG = "docs/update_log/2026-05-14_v3k_phase_h_gate4_blocked_environment.md"
PLAN_DOC = "docs/plans/2026-05-14_v3k_page_082_phase_h_gate4_blocked_environment_plan.md"
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


def _assert_docs_and_registry() -> None:
    missing = [path for path in (UPDATE_LOG, PLAN_DOC) if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing Phase H gate4 blocked docs: {missing}")

    headings = _registry_headings()
    if BLOCKED_HEADING not in headings:
        raise AssertionError(f"blocked approval heading missing: {BLOCKED_HEADING}")
    if COMPLETION_HEADING in headings:
        raise AssertionError(f"completion heading must not exist while KHOPENAPI env is absent: {COMPLETION_HEADING}")

    combined = "\n".join(_read(path) for path in (UPDATE_LOG, PLAN_DOC, REGISTRY))
    required = (
        "V3K_PHASE_H_GATE4_BLOCKED_ENVIRONMENT",
        AUDIT_VERSION,
        PHASE_H_GATE,
        PHASE_H_PHRASE,
        "khopenapi_compatible=false",
        "live_connect_attempted=false",
        "order_api_calls=0",
        "3/6",
        "V3K_PHASE_H_USER_ACK=1 not used",
        "No DB cutover",
        "No KHOPENAPI connect/login",
        "No live order/exit wiring",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"Phase H blocked docs/registry missing tokens: {missing_tokens}")


def _assert_environment_blocked() -> None:
    _assert_hook_source_guard()
    _assert_default_off_and_sentinel_contract()
    _assert_runtime_paths_clean()
    report = build_report()
    if report["khopenapi_compatible"]:
        raise AssertionError(
            "KHOPENAPI sentinel is available; do not use the blocked-env audit path. "
            "Run an actual live-dryrun execution gate instead."
        )
    if report["live_connect_attempted"] or report["order_or_exit_path_changed"]:
        raise AssertionError(f"Phase H blocked audit must not attempt live/connect or mutate order paths: {report}")


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
            raise AssertionError(f"Phase H gate4 blocked audit must not wire live runtime file: {rel_path}")


def _assert_phrase_still_current() -> None:
    verdict = evaluate_approval_phrase(PHASE_H_PHRASE)
    if not verdict.accepted or verdict.gate != PHASE_H_GATE:
        raise AssertionError(f"Phase H phrase must remain current until live-dryrun evidence exists: {verdict}")
    next_verdict = evaluate_approval_phrase("I approve f1-actual-db-cutover-await-user-approval only")
    if next_verdict.accepted:
        raise AssertionError(f"F1 cutover phrase must remain blocked while Phase H is incomplete: {next_verdict}")


def main() -> None:
    _assert_docs_and_registry()
    _assert_environment_blocked()
    _assert_runtime_boundaries()
    _assert_phrase_still_current()
    print("V3K Phase H gate4 blocked-environment audit passed")
    print(f"Gate4 blocked audit version: {AUDIT_VERSION}")
    print("Actual gate execution progress remains: 3/6")
    print(f"Current approval gate remains: {PHASE_H_GATE}")


if __name__ == "__main__":
    main()
