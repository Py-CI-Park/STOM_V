from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v3k_remaining_gate_approval_matrix import FORBIDDEN_ARTIFACT_PATHS  # noqa: E402

WORKTREE_ENTRYPOINT_ALIGNMENT_VERSION = "V3K_WORKTREE_ENTRYPOINT_ALIGNMENT_AUDIT_V1"
CONTRACT_MARKER = "V3K_WORKTREE_ENTRYPOINT_ALIGNMENT"

EXPECTED_WORKTREES = (
    ("STOM_V", "STOM_Version_2"),
    ("STOM_V.wt-2u", "STOM_Version_2U"),
    ("STOM_V.wt-3", "STOM_Version_3"),
    ("STOM_V.wt-3u", "STOM_Version_3U"),
    ("STOM_V.wt-dev", "STOM_Version_2U_C"),
)

REQUIRED_DOCS = (
    "AGENTS.md",
    "docs/plans/2026-05-14_v3k_page_075_worktree_entrypoint_alignment_plan.md",
    "docs/update_log/2026-05-14_v3k_worktree_entrypoint_alignment.md",
    "docs/update_log/2026-05-14_v3k_agent_entrypoint_contract.md",
    "docs/CARRY_FORWARD_REGISTRY.md",
)

REQUIRED_AGENT_TOKENS = (
    "STOM_V/          -> STOM_Version_2",
    "STOM_V.wt-2u/    -> STOM_Version_2U",
    "STOM_V.wt-3/     -> STOM_Version_3",
    "STOM_V.wt-3u/    -> STOM_Version_3U",
    "STOM_V.wt-dev/   -> STOM_Version_2U_C",
    "STOM_V.wt-2uc/` is no longer an active worktree",
    "formal V2.78/V2.79 wave",
    "separate active custom 2U_C V3-feature lane",
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
        raise AssertionError(f"missing V3K worktree entrypoint docs: {missing}")


def _assert_git_worktree_list_matches() -> None:
    output = _run_git("worktree", "list")
    for path_part, branch in EXPECTED_WORKTREES:
        if path_part not in output or f"[{branch}]" not in output:
            raise AssertionError(f"expected worktree missing from git worktree list: {path_part} [{branch}]")
    if "STOM_V.wt-2uc" in output:
        raise AssertionError("retired STOM_V.wt-2uc appears in git worktree list")


def _assert_agents_worktree_contract() -> None:
    agents = _read("AGENTS.md")
    missing = [token for token in REQUIRED_AGENT_TOKENS if token not in agents]
    if missing:
        raise AssertionError(f"AGENTS.md missing worktree alignment tokens: {missing}")
    if "integration/adopt-cli-v267-into-2uc" in agents:
        raise AssertionError("AGENTS.md still advertises retired integration/adopt-cli-v267-into-2uc as active")


def _assert_docs_and_registry_reference_alignment() -> None:
    combined = "\n".join(_read(path) for path in REQUIRED_DOCS)
    required = (
        CONTRACT_MARKER,
        "5-worktree layout",
        "STOM_Version_2U_C",
        "V3 features + Kiwoom retained",
        "0/6",
        "I approve gui-sidecar-write-await-user-approval only",
    )
    missing = [token for token in required if token not in combined]
    if missing:
        raise AssertionError(f"V3K worktree entrypoint docs missing tokens: {missing}")


def _assert_runner_covers_alignment() -> None:
    runner = _read("scripts/run_v3k_audit_suite.py")
    required = (
        "scripts/audit_v3k_worktree_entrypoint_alignment.py",
        "worktree_entrypoint_alignment",
        "agent_entrypoint_contract",
        "artifact_status",
    )
    missing = [token for token in required if token not in runner]
    if missing:
        raise AssertionError(f"V3K audit suite missing worktree alignment coverage: {missing}")


def _assert_no_forbidden_artifacts() -> None:
    status = _run_git("status", "--short", "--", *FORBIDDEN_ARTIFACT_PATHS)
    if status:
        raise AssertionError(f"forbidden V3K worktree alignment artifact status is not clean:\n{status}")


def main() -> None:
    _assert_required_docs_exist()
    _assert_git_worktree_list_matches()
    _assert_agents_worktree_contract()
    _assert_docs_and_registry_reference_alignment()
    _assert_runner_covers_alignment()
    _assert_no_forbidden_artifacts()

    print("V3K worktree entrypoint alignment audit passed")
    print(f"Alignment audit version: {WORKTREE_ENTRYPOINT_ALIGNMENT_VERSION}")
    print("AGENTS.md and git worktree list agree on the current five-worktree V3K layout")


if __name__ == "__main__":
    main()

