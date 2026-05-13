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
    GATES,
)
from scripts.check_v3k_gate_approval_phrase import (  # noqa: E402
    FIRST_GATE,
    FIRST_GATE_PHRASE,
    evaluate_approval_phrase,
)

PHRASE_INTAKE_AUDIT_VERSION = "V3K_GATE_APPROVAL_PHRASE_INTAKE_AUDIT_V1"

BROAD_OR_INVALID_PHRASES = (
    "approve all gates",
    "I approve all gates",
    "turn everything on",
    "approve everything",
    "모두 승인",
    "전체 승인",
    "전부 승인",
    "I approve gui-sidecar-write-await-user-approval",
    "I approve gui-sidecar-write-await-user-approval now",
)

REQUIRED_DOCS = (
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
    "docs/plans/2026-05-14_v3k_page_070_gate_approval_phrase_intake_guard_plan.md",
    "docs/update_log/2026-05-14_v3k_goal_handoff_audit_suite_integration.md",
    "docs/update_log/2026-05-14_v3k_remaining_gate_approval_matrix.md",
    "docs/update_log/2026-05-14_v3k_one_gate_sequence_guard.md",
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


def _assert_docs() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing V3K phrase intake docs: {missing}")
    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        "V3K_GATE_APPROVAL_PHRASE_INTAKE_GUARD",
        PHRASE_INTAKE_AUDIT_VERSION,
        FIRST_GATE,
        FIRST_GATE_PHRASE,
        "review-only",
        "No USER_ACK creation",
        "No enable registry creation",
        "No ON/DB/live execution",
        "broad approval",
        "out-of-order",
    )
    missing_tokens = [token for token in required if token not in combined]
    if missing_tokens:
        raise AssertionError(f"phrase intake docs missing tokens: {missing_tokens}")


def _assert_phrase_verdicts() -> None:
    accepted = evaluate_approval_phrase(FIRST_GATE_PHRASE)
    if not accepted.accepted:
        raise AssertionError(f"first gate phrase was not accepted: {accepted}")
    if accepted.gate != FIRST_GATE:
        raise AssertionError(f"accepted gate mismatch: {accepted.gate}")
    if accepted.creates_user_ack or accepted.creates_enable_registry or accepted.executes_runtime:
        raise AssertionError("approval phrase checker must be side-effect free")

    for gate in GATES:
        phrase = str(gate["phrase"])
        verdict = evaluate_approval_phrase(phrase)
        if gate["gate"] == FIRST_GATE:
            if not verdict.accepted:
                raise AssertionError(f"first gate phrase unexpectedly rejected: {verdict}")
        elif verdict.accepted or verdict.status != "rejected-out-of-order-gate":
            raise AssertionError(f"out-of-order gate phrase was not rejected: {gate['gate']} -> {verdict}")

    for phrase in BROAD_OR_INVALID_PHRASES:
        verdict = evaluate_approval_phrase(phrase)
        if verdict.accepted:
            raise AssertionError(f"broad/invalid phrase was accepted: {phrase} -> {verdict}")


def _assert_no_authority_or_artifacts() -> None:
    enabled_env = [gate["ack_env"] for gate in GATES if os.environ.get(gate["ack_env"]) == "1"]
    if enabled_env:
        raise AssertionError(f"USER_ACK env vars enabled before approval: {enabled_env}")

    registry = _read("docs/CARRY_FORWARD_REGISTRY.md")
    registry_headings = {line.strip() for line in registry.splitlines() if line.startswith("## ")}
    present = [heading for heading in ACTUAL_APPROVAL_HEADINGS if heading in registry_headings]
    if present:
        raise AssertionError(f"actual approval or enable registry exists before approval: {present}")

    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden phrase intake artifact status is not clean:\n{status}")


def _assert_runner_covers_phrase_intake() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "check_v3k_gate_approval_phrase.py",
        "audit_v3k_gate_approval_phrase_intake.py",
        "gate_approval_phrase_intake",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing phrase intake tokens: {missing}")


def main() -> None:
    _assert_docs()
    _assert_phrase_verdicts()
    _assert_no_authority_or_artifacts()
    _assert_runner_covers_phrase_intake()

    print("V3K gate approval phrase intake audit passed")
    print(f"Phrase intake audit version: {PHRASE_INTAKE_AUDIT_VERSION}")
    print(f"First accepted review-only phrase: {FIRST_GATE_PHRASE}")
    print("Broad, invalid, and out-of-order approval phrases remain rejected")


if __name__ == "__main__":
    main()
