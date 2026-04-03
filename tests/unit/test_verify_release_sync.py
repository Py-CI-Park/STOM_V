from scripts.verify_release_sync import ParsedStatus, parse_porcelain, validate_status


def test_parse_porcelain_splits_branch_tracked_and_untracked_entries():
    parsed = parse_porcelain(
        [
            "## STOM_Version_2U_C_CLI_v267...origin/STOM_Version_2U_C_CLI_v267 [ahead 18]",
            " M docs/WORKTREE_STRATEGY.md",
            "?? backtest/graph",
            "?? scratch.txt",
        ]
    )

    assert parsed.branch == "STOM_Version_2U_C_CLI_v267"
    assert parsed.tracked == ["docs/WORKTREE_STRATEGY.md"]
    assert parsed.untracked == ["backtest/graph", "scratch.txt"]


def test_validate_status_allows_only_protected_untracked_paths():
    parsed = ParsedStatus(
        branch="STOM_Version_2U_C_CLI_v267",
        tracked=[],
        untracked=["backtest/graph"],
    )

    assert validate_status("C:/System_Trading/STOM/STOM_V.wt-dev", parsed) == []


def test_validate_status_rejects_branch_mismatch_tracked_edits_and_unknown_untracked_paths():
    parsed = ParsedStatus(
        branch="wrong-branch",
        tracked=["ui/set_widget.py"],
        untracked=["scratch.txt"],
    )

    failures = validate_status("C:/System_Trading/STOM/STOM_V.wt-dev", parsed)

    assert any("expected branch" in failure for failure in failures)
    assert any("tracked edits" in failure for failure in failures)
    assert any("scratch.txt" in failure for failure in failures)
