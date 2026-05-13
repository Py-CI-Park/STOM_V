from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import (  # noqa: E402
    FORBIDDEN_ARTIFACT_PATHS,
    GATES,
)

AGENT_ENTRYPOINT_CONTRACT_VERSION = "V3K_2UC_AGENT_ENTRYPOINT_CONTRACT_AUDIT_V1"
CONTRACT_MARKER = "V3K_2UC_AGENT_ENTRYPOINT_CONTRACT"
FIRST_GATE_PHRASE = "I approve gui-sidecar-write-await-user-approval only"

REQUIRED_DOCS = (
    "AGENTS.md",
    "docs/plans/2026-05-14_v3k_page_074_agent_entrypoint_contract_plan.md",
    "docs/update_log/2026-05-14_v3k_agent_entrypoint_contract.md",
    "docs/update_log/2026-05-14_v3k_goal_completion_audit_checklist.md",
    "docs/update_log/2026-05-14_v3k_gui_sidecar_first_gate_blocker_snapshot.md",
    "docs/update_log/2026-05-14_v3k_gate_approval_phrase_intake_guard.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_AGENT_TOKENS = (
    CONTRACT_MARKER,
    "V3K = V3 features + Kiwoom retained",
    "LS Securities REST/TR/REAL direct",
    "Kiwoom API/order/exit/live runtime",
    "0/6",
    "update_goal(status=\"complete\")",
    "USER_ACK",
    "enable registry",
    "_v3k_sidecar",
    "_database/",
    "KHOPENAPI connect/login",
    "live order/exit rule",
    "feature flags must remain default-OFF",
    "python scripts/verify_nonrelease_sync.py",
    "python scripts/run_v3k_audit_suite.py",
    "git diff --check",
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


def _assert_required_docs_exist() -> None:
    missing = [path for path in REQUIRED_DOCS if not (ROOT / path).is_file()]
    if missing:
        raise AssertionError(f"missing V3K agent entrypoint docs: {missing}")


def _assert_agent_contract_tokens() -> None:
    agents = _read("AGENTS.md")
    missing = [token for token in REQUIRED_AGENT_TOKENS if token not in agents]
    for gate in GATES:
        if gate["gate"] not in agents:
            missing.append(gate["gate"])
    if missing:
        raise AssertionError(f"AGENTS.md missing V3K entrypoint tokens: {missing}")


def _assert_docs_and_registry_reference_contract() -> None:
    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        CONTRACT_MARKER,
        "V3 features + Kiwoom retained",
        "actual approval gate execution",
        "0/6",
        "verify_nonrelease_sync.py",
        FIRST_GATE_PHRASE,
    )
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"V3K agent entrypoint docs missing tokens: {missing}")


def _assert_runner_covers_contract() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "scripts/audit_v3k_agent_entrypoint_contract.py",
        "agent_entrypoint_contract",
        "goal_completion_objective_checklist",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing agent entrypoint coverage: {missing}")


def _assert_no_forbidden_artifacts() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden V3K agent entrypoint artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_agent_contract_tokens()
    _assert_docs_and_registry_reference_contract()
    _assert_runner_covers_contract()
    _assert_no_forbidden_artifacts()

    print("V3K agent entrypoint contract audit passed")
    print(f"Contract audit version: {AGENT_ENTRYPOINT_CONTRACT_VERSION}")
    print("AGENTS.md now points future agents to the V3K goal, gate order, and no-complete guard")


if __name__ == "__main__":
    main()

