from scripts import verify_release_sync
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


def test_main_uses_root_for_gitignore_and_worktree_resolution(tmp_path, monkeypatch, capsys):
    root = tmp_path / "isolated-root"
    root.mkdir()
    (root / ".gitignore").write_text("backtest/graph/\n", encoding="utf-8")

    seen: dict[str, object] = {}

    def fake_resolve_status_targets(worktree_root: str):
        seen["resolved_root"] = worktree_root
        return [("feature/upstream-worktree-propagation", worktree_root)]

    def fake_git_status_lines(worktree_path: str):
        seen["status_path"] = worktree_path
        return ["## feature/upstream-worktree-propagation"]

    def fake_parse_porcelain(lines: list[str]):
        seen["parsed_lines"] = lines
        return ParsedStatus(
            branch="feature/upstream-worktree-propagation",
            tracked=[],
            untracked=[],
        )

    def fake_validate_target(expected_branch: str, worktree_path: str, parsed: ParsedStatus):
        seen["validated"] = (expected_branch, worktree_path, parsed.branch)
        return []

    monkeypatch.setattr(
        verify_release_sync, "resolve_status_targets", fake_resolve_status_targets
    )
    monkeypatch.setattr(verify_release_sync, "git_status_lines", fake_git_status_lines)
    monkeypatch.setattr(verify_release_sync, "parse_porcelain", fake_parse_porcelain)
    monkeypatch.setattr(verify_release_sync, "validate_target", fake_validate_target)

    assert verify_release_sync.main(["--root", str(root)]) == 0
    assert seen["resolved_root"] == str(root)
    assert seen["status_path"] == str(root)
    assert seen["validated"] == (
        "feature/upstream-worktree-propagation",
        str(root),
        "feature/upstream-worktree-propagation",
    )
    assert capsys.readouterr().out.strip() == "release sync preflight passed"
