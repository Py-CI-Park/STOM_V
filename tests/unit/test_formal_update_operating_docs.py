from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CURRENT_PROMOTED_FLOW = "V2 -> 2U -> 2U_C -> research/init"
ARCHIVE_REFERENCE_FLOW = "integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C"
RETIRED_TRANSITION_FLOW = (
    "V2 -> 2U -> integration/adopt-cli-v267-into-2uc -> "
    "STOM_Version_2U_C_CLI_v267 -> research/init"
)
RETIRED_CLI_CHILD_LANE_FLOW = "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init"

LOCAL_GUIDE_EXPECTATIONS = {
    "2U": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-2u/CLAUDE.md",
        "relative_path": "../STOM_V.wt-2u/CLAUDE.md",
        "title": "# STOM Project Guidelines (STOM_Version_2U)",
        "worktree_path": "`STOM_V.wt-2u/`",
        "identity_marker": "`2U`",
        "marker": (
            "C:/System_Trading/STOM/STOM_V.wt-2u/docs/update_log/"
            "2026-04-04_v274_v277_2u_baseline_note.md"
        ),
        "required_strings": (),
        "forbidden_strings": (),
    },
    "2U_C_archive": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-2uc/CLAUDE.md",
        "relative_path": "../STOM_V.wt-2uc/CLAUDE.md",
        "title": "# STOM Project Guidelines (STOM_Version_2U_C archive transition lane)",
        "worktree_path": "`STOM_V.wt-2uc/`",
        "identity_marker": "`integration/adopt-cli-v267-into-2uc`",
        "marker": (
            "C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/"
            "2026-04-05_2uc_single_baseline_consolidation_execution_log.md"
        ),
        "required_strings": (
            "archive/transition checkout",
            CURRENT_PROMOTED_FLOW,
        ),
        "forbidden_strings": (
            RETIRED_TRANSITION_FLOW,
            RETIRED_CLI_CHILD_LANE_FLOW,
        ),
    },
    "2U_C_active": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-dev/CLAUDE.md",
        "relative_path": "../STOM_V.wt-dev/CLAUDE.md",
        "title": "# STOM Project Guidelines (STOM_Version_2U_C)",
        "worktree_path": "`STOM_V.wt-dev/`",
        "identity_marker": "`STOM_Version_2U_C`",
        "marker": (
            "C:/System_Trading/STOM/STOM_V.wt-2uc/docs/update_log/"
            "2026-04-05_2uc_single_baseline_consolidation_execution_log.md"
        ),
        "required_strings": (
            CURRENT_PROMOTED_FLOW,
            "`integration/adopt-cli-v267-into-2uc`",
        ),
        "forbidden_strings": (
            RETIRED_TRANSITION_FLOW,
            RETIRED_CLI_CHILD_LANE_FLOW,
            "`STOM_Version_2U_C_CLI_v267`",
        ),
    },
    "research/init": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-lab/CLAUDE.md",
        "relative_path": "../STOM_V.wt-lab/CLAUDE.md",
        "title": "# STOM Project Guidelines (research/init)",
        "worktree_path": "`STOM_V.wt-lab/`",
        "identity_marker": "`research/init`",
        "marker": (
            "C:/System_Trading/STOM/STOM_V.wt-lab/docs/update_log/"
            "2026-04-04_v274_v277_research_init_baseline_note.md"
        ),
        "required_strings": (),
        "forbidden_strings": (),
    },
}

SIBLING_AGENT_GUIDE_EXPECTATIONS = {
    "2U_C_archive": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-2uc/AGENTS.md",
        "relative_path": "../STOM_V.wt-2uc/AGENTS.md",
        "required_strings": (
            "# STOM_Version_2U_C - AI Agent Instructions",
            "This checkout is the post-promotion archive/transition lane.",
            "`STOM_V.wt-2uc/` -> `integration/adopt-cli-v267-into-2uc`",
            "`STOM_V.wt-dev/` -> `STOM_Version_2U_C`",
            "Active propagation chain:",
            CURRENT_PROMOTED_FLOW,
            "Archive reference flow:",
            ARCHIVE_REFERENCE_FLOW,
        ),
        "forbidden_strings": (
            RETIRED_TRANSITION_FLOW,
            "`STOM_V.wt-dev/` -> `STOM_Version_2U_C_CLI_v267`",
        ),
    },
    "2U_C_active": {
        "display_path": "C:/System_Trading/STOM/STOM_V.wt-dev/AGENTS.md",
        "relative_path": "../STOM_V.wt-dev/AGENTS.md",
        "required_strings": (
            "# STOM_Version_2U_C - AI Agent Instructions",
            "This checkout is the active single-baseline lane after the CLI_v267 promotion.",
            "`STOM_V.wt-dev/` -> `STOM_Version_2U_C`",
            "`STOM_V.wt-2uc/` -> `integration/adopt-cli-v267-into-2uc`",
            "Active propagation chain:",
            CURRENT_PROMOTED_FLOW,
        ),
        "forbidden_strings": (
            "CLI_v258",
            RETIRED_TRANSITION_FLOW,
            RETIRED_CLI_CHILD_LANE_FLOW,
            "`STOM_Version_2U_C_CLI_v267`",
        ),
    },
}

LIVE_DOWNSTREAM_HEADS = {
    "2U": "8c70573",
    "2U_C": "b0c3a6d",
    "CLI_v267": "d80fe62",
    "research/init": "2544521",
}


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_formal_update_operating_system_doc_exists_and_names_the_lifecycle():
    text = read_text("docs/FORMAL_UPDATE_OPERATING_SYSTEM.md")

    assert "release intake" in text
    assert "downstream baseline check" in text
    assert "version-wave propagation" in text
    assert "blocker audit" in text
    assert "branch-local corrective fix" in text
    assert "carry-forward recording" in text
    assert "cycle closeout" in text
    assert "## Current promoted state" in text
    assert CURRENT_PROMOTED_FLOW in text
    assert "archive/history/transition checkout" in text
    assert RETIRED_TRANSITION_FLOW not in text


def test_agents_points_to_the_operating_system_and_registry():
    text = read_text("AGENTS.md")

    assert "FORMAL_UPDATE_OPERATING_SYSTEM.md" in text
    assert "CARRY_FORWARD_REGISTRY.md" in text
    assert "docs/update_log/2026-04-05_v274_v277_cycle_status.md" in text
    assert "Current promoted state:" in text
    assert CURRENT_PROMOTED_FLOW in text
    assert "archive/transition lane" in text
    assert RETIRED_TRANSITION_FLOW not in text
    assert "STOM V2.49" not in text


def test_central_claude_mentions_preflight_entrypoint_docs_and_promoted_topology():
    text = read_text("CLAUDE.md")

    assert "python scripts/verify_release_sync.py" in text
    assert "docs/FORMAL_UPDATE_OPERATING_SYSTEM.md" in text
    assert "docs/CARRY_FORWARD_REGISTRY.md" in text
    assert "docs/update_log/2026-04-05_v274_v277_cycle_status.md" in text
    assert "## Current Promoted State" in text
    assert CURRENT_PROMOTED_FLOW in text
    assert "archive/transition checkout" in text
    assert ARCHIVE_REFERENCE_FLOW in text
    assert RETIRED_TRANSITION_FLOW not in text


def test_strategy_docs_declare_the_formal_update_operating_system_as_parent():
    upstream_text = read_text("docs/UPSTREAM_SYNC_STRATEGY.md")
    worktree_text = read_text("docs/WORKTREE_STRATEGY.md")
    subordinate_note = (
        "> This document is subordinate to "
        "`docs/FORMAL_UPDATE_OPERATING_SYSTEM.md`."
    )

    assert subordinate_note in upstream_text
    assert subordinate_note in worktree_text


def test_cycle_status_contains_current_release_and_downstream_heads():
    relative_path = "docs/update_log/2026-04-05_v274_v277_cycle_status.md"

    assert (ROOT / relative_path).exists()

    text = read_text(relative_path)

    assert "## Release commits" in text
    assert "## Downstream heads" in text
    assert "## Protected result data" in text
    assert "## Next recommended start" in text
    for lane, live_sha in LIVE_DOWNSTREAM_HEADS.items():
        assert f"- `{lane}`: `{live_sha}`" in text


@pytest.mark.parametrize(
    ("lane", "expectation"),
    LOCAL_GUIDE_EXPECTATIONS.items(),
    ids=LOCAL_GUIDE_EXPECTATIONS.keys(),
)
def test_worktree_local_claude_guides_keep_read_first_and_branch_gate_contract(
    lane: str, expectation: dict[str, object]
):
    guide_path = (ROOT / expectation["relative_path"]).resolve()
    if not guide_path.exists():
        pytest.skip(f"missing sibling worktree guide: {expectation['display_path']}")

    text = guide_path.read_text(encoding="utf-8")

    assert expectation["title"] in text, lane
    assert expectation["worktree_path"] in text, lane
    assert expectation["identity_marker"] in text, lane
    assert "## Read First" in text, lane
    assert "## Branch Gate" in text, lane
    assert expectation["marker"] in text, lane

    for required in expectation["required_strings"]:
        assert required in text, lane
    for forbidden in expectation["forbidden_strings"]:
        assert forbidden not in text, lane


@pytest.mark.parametrize(
    ("lane", "expectation"),
    SIBLING_AGENT_GUIDE_EXPECTATIONS.items(),
    ids=SIBLING_AGENT_GUIDE_EXPECTATIONS.keys(),
)
def test_worktree_sibling_agents_guides_keep_promoted_and_archive_contracts(
    lane: str, expectation: dict[str, tuple[str, ...]]
):
    guide_path = (ROOT / expectation["relative_path"]).resolve()

    assert guide_path.exists(), expectation["display_path"]

    text = guide_path.read_text(encoding="utf-8")

    for required in expectation["required_strings"]:
        assert required in text, f"{lane}: missing {required!r}"

    for forbidden in expectation["forbidden_strings"]:
        assert forbidden not in text, f"{lane}: unexpected {forbidden!r}"


def test_registry_tracks_current_carry_forward_items():
    text = read_text("docs/CARRY_FORWARD_REGISTRY.md")

    assert "# Carry Forward Registry" in text
    assert "## Release-side upstream risks" in text
    assert "## Downstream carry-forward tests" in text
    assert "## Rule" in text
