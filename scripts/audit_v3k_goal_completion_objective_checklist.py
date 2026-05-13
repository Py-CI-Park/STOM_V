from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import (  # noqa: E402
    ACTUAL_APPROVAL_HEADINGS,
    FORBIDDEN_ARTIFACT_PATHS,
    FORBIDDEN_BEFORE_APPROVAL,
    GATES,
)
from scripts.audit_v3k_runtime_activation_gap import (  # noqa: E402
    APPROVAL_ORDER,
    RECOMMENDED_APPROVAL_ORDER_FIRST,
)
from scripts.summarize_v3k_gui_sidecar_first_gate_blockers import (  # noqa: E402
    build_blocker_snapshot,
)

OBJECTIVE_CHECKLIST_AUDIT_VERSION = "V3K_GOAL_COMPLETION_OBJECTIVE_CHECKLIST_AUDIT_V1"
OBJECTIVE_MARKER = "V3K_GOAL_COMPLETION_OBJECTIVE_CHECKLIST"
EXPECTED_PROGRESS = "0/6"
FIRST_GATE = "gui-sidecar-write-await-user-approval"
FIRST_GATE_PHRASE = "I approve gui-sidecar-write-await-user-approval only"

REQUIRED_DOCS = (
    "docs/plans/2026-05-14_v3k_page_073_goal_completion_audit_checklist_plan.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md",
    "docs/update_log/2026-05-08_v3k_full_feature_migration_goal_reset.md",
    "docs/update_log/2026-05-08_v3_2uc_unmet_features_audit_and_research.md",
    "docs/update_log/2026-05-14_v3k_goal_skill_and_remaining_gate_completion_audit.md",
    "docs/update_log/2026-05-14_v3k_goal_handoff_audit_suite_integration.md",
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_preflight.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_TOKENS = (
    OBJECTIVE_MARKER,
    "STOM_Version_2U_C",
    "V3 기능 + Kiwoom 유지",
    "LS증권 직접 의존",
    "Kiwoom API",
    "feature flag default-OFF",
    "Prompt-to-artifact checklist",
    "actual approval gate execution",
    EXPECTED_PROGRESS,
    "update_goal(status=\"complete\")",
    "python scripts/run_v3k_audit_suite.py",
    "python scripts/verify_nonrelease_sync.py",
    "git diff --check",
    FIRST_GATE,
    FIRST_GATE_PHRASE,
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


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


def _combined_docs() -> str:
    return "\n".join(_read(path) for path in REQUIRED_DOCS)


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing V3K objective checklist docs: {missing}")


def _assert_prompt_to_artifact_tokens() -> None:
    combined = _combined_docs()
    required = list(REQUIRED_TOKENS)
    for gate in GATES:
        required.extend((gate["gate"], gate["ack_env"], gate["phrase"]))
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"V3K objective checklist missing tokens: {missing}")


def _assert_gate_order_and_progress() -> None:
    expected_order = tuple(gate["gate"] for gate in GATES)
    if tuple(APPROVAL_ORDER) != expected_order:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != FIRST_GATE:
        raise AssertionError(f"unexpected first approval gate: {RECOMMENDED_APPROVAL_ORDER_FIRST}")

    snapshot = build_blocker_snapshot()
    if snapshot.gate != FIRST_GATE:
        raise AssertionError(f"unexpected blocker snapshot gate: {snapshot.gate}")
    if snapshot.accepted_phrase != FIRST_GATE_PHRASE:
        raise AssertionError("first gate phrase changed")
    if snapshot.ready_for_execution:
        raise AssertionError("first gate unexpectedly ready for execution before approval")
    if snapshot.actual_gate_execution_progress != EXPECTED_PROGRESS:
        raise AssertionError(
            f"unexpected actual gate execution progress: {snapshot.actual_gate_execution_progress}"
        )
    if snapshot.creates_user_ack or snapshot.creates_sidecar_artifact or snapshot.executes_runtime:
        raise AssertionError("blocker snapshot is no longer side-effect free")


def _assert_no_authority_or_execution_artifacts() -> None:
    enabled = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled:
        raise AssertionError(f"USER_ACK env vars enabled before approval: {enabled}")

    registry = _read("docs/CARRY_FORWARD_REGISTRY.md")
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before approval: {present}")

    present_files = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present_files:
        raise AssertionError(f"actual execution scripts exist before approval: {present_files}")

    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden V3K objective artifact status is not clean:\n{status}")


def _assert_runner_covers_objective_checklist() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "scripts/audit_v3k_goal_completion_objective_checklist.py",
        "goal_completion_objective_checklist",
        "gui_sidecar_first_gate_blocker_snapshot",
        "gate_approval_phrase_intake",
        "verify_1a",
        "verify_1b_closure",
        "nonrelease_sync",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing objective checklist coverage: {missing}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_prompt_to_artifact_tokens()
    _assert_gate_order_and_progress()
    _assert_no_authority_or_execution_artifacts()
    _assert_runner_covers_objective_checklist()

    print("V3K goal completion objective checklist audit passed")
    print(f"Checklist audit version: {OBJECTIVE_CHECKLIST_AUDIT_VERSION}")
    print("Objective: V3 features + Kiwoom retained, LS direct dependency excluded")
    print(f"Actual approval gate execution progress remains {EXPECTED_PROGRESS}")
    print("Goal completion remains blocked until every approval gate has concrete evidence")


if __name__ == "__main__":
    main()

