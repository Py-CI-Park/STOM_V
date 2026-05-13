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

GOAL_SKILL_HANDOFF_AUDIT_VERSION = "V3K_GOAL_SKILL_HANDOFF_AUDIT_V1"
HANDOFF_STATUS = "not-complete-awaiting-one-gate-approval"
FIRST_GATE = "gui-sidecar-write-await-user-approval"
FIRST_GATE_PHRASE = "I approve gui-sidecar-write-await-user-approval only"

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_goal_skill_and_remaining_gate_completion_audit.md",
    "docs/plans/2026-05-14_v3k_page_068_goal_skill_and_remaining_gate_execution_plan.md",
    "docs/update_log/2026-05-14_v3k_one_gate_sequence_guard.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_authority_audit.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_TOKENS = (
    "V3K_GOAL_SKILL_AND_REMAINING_GATE_AUDIT",
    HANDOFF_STATUS,
    "STOM_Version_2U_C",
    "Kiwoom API",
    "live runtime",
    "feature flag default-OFF",
    "Prompt-to-artifact checklist",
    "not executable",
    "omx ralph",
    "verify_nonrelease_sync.py",
    FIRST_GATE,
    FIRST_GATE_PHRASE,
    "Actual approval gate execution",
    "0/6 = 0%",
    "Do not call `update_goal(status=\"complete\")`",
)

FORBIDDEN_TOKENS = (
    "all gates approved | accepted",
    "goal status: complete",
    "update_goal(status=\"complete\") ?? ??",
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


def _assert_docs_exist_and_are_not_mojibake() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing Page068 handoff docs: {missing}")
    page = _read(REQUIRED_DOCS[0]) + "\n" + _read(REQUIRED_DOCS[1])
    if "??" in page or "?" in page:
        raise AssertionError("Page068 handoff docs contain mojibake placeholder characters")


def _assert_required_tokens() -> None:
    docs = _combined_docs()
    missing = [token for token in REQUIRED_TOKENS if token not in docs]
    if missing:
        raise AssertionError(f"Page068 handoff docs missing required tokens: {missing}")
    forbidden = [token for token in FORBIDDEN_TOKENS if token in docs]
    if forbidden:
        raise AssertionError(f"Page068 handoff docs contain forbidden completion tokens: {forbidden}")


def _assert_gate_order_and_authority_absent() -> None:
    expected_order = tuple(gate["gate"] for gate in GATES)
    if tuple(APPROVAL_ORDER) != expected_order:
        raise AssertionError(f"approval order mismatch: {APPROVAL_ORDER}")
    if RECOMMENDED_APPROVAL_ORDER_FIRST != FIRST_GATE:
        raise AssertionError(f"unexpected first gate: {RECOMMENDED_APPROVAL_ORDER_FIRST}")
    if expected_order[0] != FIRST_GATE:
        raise AssertionError(f"first gate tuple changed: {expected_order}")

    enabled = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled:
        raise AssertionError(f"USER_ACK env vars enabled before approval: {enabled}")

    registry = _read("docs/CARRY_FORWARD_REGISTRY.md")
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before approval: {present}")


def _assert_no_execution_artifacts() -> None:
    present = [path for path in FORBIDDEN_BEFORE_APPROVAL if (ROOT / path).exists()]
    if present:
        raise AssertionError(f"actual execution scripts exist before approval: {present}")
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden Page068 handoff artifact status is not clean:\n{status}")


def _assert_runner_covers_handoff() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "audit_v3k_goal_skill_remaining_gate_handoff.py",
        "goal_skill_remaining_gate_handoff",
        "goal_completion_authority",
        "one_gate_sequence_guard",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing Page068 handoff tokens: {missing}")


def main() -> None:
    _assert_docs_exist_and_are_not_mojibake()
    _assert_required_tokens()
    _assert_gate_order_and_authority_absent()
    _assert_no_execution_artifacts()
    _assert_runner_covers_handoff()

    print("V3K goal skill remaining gate handoff audit passed")
    print(f"Handoff audit version: {GOAL_SKILL_HANDOFF_AUDIT_VERSION}")
    print(f"Handoff status: {HANDOFF_STATUS}")
    print(f"First gate phrase: {FIRST_GATE_PHRASE}")
    print("Active goal remains intentionally incomplete before one-gate approval evidence")


if __name__ == "__main__":
    main()
