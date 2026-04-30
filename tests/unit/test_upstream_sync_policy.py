from utility.upstream_sync_policy import (
    LOCAL_UPSTREAM_MIRROR,
    PROPAGATION_CHAIN,
    PROTECTED_NON_GIT_PATHS,
    RELEASE_OVERLAY_EXCLUDES,
    UPSTREAM_REMOTE_URL,
    expected_branch_for_worktree,
    is_protected_non_git_path,
)


def test_propagation_chain_matches_the_real_worktree_layout():
    assert PROPAGATION_CHAIN == (
        ("STOM_Version_2", "C:/System_Trading/STOM/STOM_V"),
        ("STOM_Version_2U", "C:/System_Trading/STOM/STOM_V.wt-2u"),
        ("STOM_Version_2U_C", "C:/System_Trading/STOM/STOM_V.wt-dev"),
    )


def test_release_policy_prefers_real_upstream_before_local_mirror():
    assert UPSTREAM_REMOTE_URL == "https://github.com/devstom/STOM.git"
    assert LOCAL_UPSTREAM_MIRROR == "C:/System_Trading/STOM/STOM_devstom"


def test_backtest_graph_is_a_protected_non_git_asset():
    assert PROTECTED_NON_GIT_PATHS == ("backtest/graph/",)
    assert is_protected_non_git_path("backtest/graph")
    assert is_protected_non_git_path("backtest/graph/run-2026-04-03")
    assert is_protected_non_git_path("./backtest/graph/output.png")
    assert not is_protected_non_git_path("../../backtest/graph/output.png")
    assert not is_protected_non_git_path("backtester/graph/output.png")


def test_expected_branch_lookup_uses_exact_worktree_roots():
    assert expected_branch_for_worktree("C:/System_Trading/STOM/STOM_V") == "STOM_Version_2"
    assert expected_branch_for_worktree("C:/System_Trading/STOM/STOM_V.wt-dev") == "STOM_Version_2U_C"


def test_release_overlay_excludes_cover_docs_scripts_and_branch_only_surfaces():
    assert RELEASE_OVERLAY_EXCLUDES == (
        ".git/",
        ".gitignore",
        "CLAUDE.md",
        "AGENTS.md",
        "docs/",
        "scripts/",
        "tests/",
        "cli/",
        "research/",
    )
