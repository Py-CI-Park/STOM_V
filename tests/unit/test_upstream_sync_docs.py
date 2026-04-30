from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CURRENT_PROMOTED_WORKTREE_LAYOUT_BLOCK = """```text
C:/System_Trading/STOM/
+-- STOM_V/            -> STOM_Version_2
+-- STOM_V.wt-2u/      -> STOM_Version_2U
+-- STOM_V.wt-2uc/     -> integration/adopt-cli-v267-into-2uc
+-- STOM_V.wt-dev/     -> STOM_Version_2U_C
```"""

CURRENT_PROMOTED_CHAIN_BLOCK = """```text
V2 -> 2U -> 2U_C
```"""

STALE_TRANSITION_CHAIN_BLOCK = """```text
V2 -> 2U -> integration/adopt-cli-v267-into-2uc -> STOM_Version_2U_C_CLI_v267 -> research/init
```"""

MIRROR_POLICY_LINE = (
    "The local mirror is reference-only. It is useful for inspection and fallback access, "
    "but it is not the sole freshness authority. When deciding whether the release lane is "
    "current, compare against the GitHub upstream first."
)

PREFLIGHT_COMMAND_BLOCK = """```bash
python scripts/verify_release_sync.py
```"""

PREFLIGHT_ROOT_COMMAND_BLOCK = """```bash
python scripts/verify_release_sync.py --root C:/System_Trading/STOM/STOM_V.wt-upsync
```"""

CLAUDE_FRESHNESS_BLOCK = """```bash
git fetch https://github.com/devstom/STOM.git refs/tags/V2.0:refs/remotes/devstom_tmp/tags/V2.0
git show refs/remotes/devstom_tmp/tags/V2.0:_update.txt | head -5
python scripts/verify_release_sync.py
```"""


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_worktree_strategy_locks_promoted_topology_and_archive_lane_contract():
    text = read_text("docs/WORKTREE_STRATEGY.md")

    assert CURRENT_PROMOTED_WORKTREE_LAYOUT_BLOCK in text
    assert CURRENT_PROMOTED_CHAIN_BLOCK in text
    assert "archive/history/transition checkout" in text
    assert "`research/init` is excluded from the current official propagation chain" in text
    assert STALE_TRANSITION_CHAIN_BLOCK not in text
    assert PREFLIGHT_COMMAND_BLOCK in text


def test_upstream_sync_strategy_locks_authority_promoted_state_and_preflight_blocks():
    text = read_text("docs/UPSTREAM_SYNC_STRATEGY.md")

    assert CURRENT_PROMOTED_WORKTREE_LAYOUT_BLOCK in text
    assert CURRENT_PROMOTED_CHAIN_BLOCK in text
    assert MIRROR_POLICY_LINE in text
    assert PREFLIGHT_COMMAND_BLOCK in text
    assert PREFLIGHT_ROOT_COMMAND_BLOCK in text
    assert "- Official freshness authority: `https://github.com/devstom/STOM.git`" in text
    assert "- Local reference mirror: `C:/System_Trading/STOM/STOM_devstom`" in text
    assert "- Current V2 wave source: `refs/tags/V2.0`" in text
    assert "archive/history/transition checkout" in text
    assert "Do not use `refs/heads/V3.00` or `refs/tags/V3.0` for the V2.79 wave." in text
    assert STALE_TRANSITION_CHAIN_BLOCK not in text


def test_claude_guide_locks_promoted_mapping_and_freshness_steps():
    text = read_text("CLAUDE.md")

    assert CURRENT_PROMOTED_WORKTREE_LAYOUT_BLOCK in text
    assert CURRENT_PROMOTED_CHAIN_BLOCK in text
    assert "Treat `C:/System_Trading/STOM/STOM_devstom` as a reference-only mirror, not the sole freshness authority." in text
    assert CLAUDE_FRESHNESS_BLOCK in text
    assert PREFLIGHT_ROOT_COMMAND_BLOCK in text
    assert "archive/transition checkout" in text
    assert "The current official propagation chain stops at `2U_C`; `research/init` is not part of the V2.79 wave." in text
    assert STALE_TRANSITION_CHAIN_BLOCK not in text


def test_carry_forward_registry_marks_research_entries_as_historical_for_v279():
    text = read_text("docs/CARRY_FORWARD_REGISTRY.md")

    assert "The active V2.79 official propagation chain is `V2 -> 2U -> 2U_C`." in text
    assert "They are not active V2.79 propagation targets" in text
