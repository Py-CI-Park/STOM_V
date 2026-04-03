from __future__ import annotations

import argparse
import ntpath
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utility.upstream_sync_policy import (
    PROPAGATION_CHAIN,
    expected_branch_for_worktree,
    is_protected_non_git_path,
)

CANONICAL_RELEASE_ROOT = "C:/System_Trading/STOM/STOM_V"


@dataclass(frozen=True)
class ParsedStatus:
    branch: str
    tracked: list[str]
    untracked: list[str]


def parse_porcelain(lines: list[str]) -> ParsedStatus:
    branch_line = next(line for line in lines if line.startswith("## "))
    branch = branch_line[3:].split("...")[0].strip()
    tracked: list[str] = []
    untracked: list[str] = []

    for line in lines[1:]:
        if not line:
            continue
        path = line[3:]
        if line.startswith("?? "):
            untracked.append(path)
        else:
            tracked.append(path)

    return ParsedStatus(branch=branch, tracked=tracked, untracked=untracked)


def validate_status(worktree_path: str, parsed: ParsedStatus) -> list[str]:
    return validate_target(expected_branch_for_worktree(worktree_path), worktree_path, parsed)


def validate_target(
    expected_branch: str, worktree_path: str, parsed: ParsedStatus
) -> list[str]:
    failures: list[str] = []

    if parsed.branch != expected_branch:
        failures.append(
            f"{worktree_path}: expected branch {expected_branch}, got {parsed.branch}"
        )
    if parsed.tracked:
        failures.append(f"{worktree_path}: tracked edits present: {', '.join(parsed.tracked)}")

    unexpected_untracked = [
        path for path in parsed.untracked if not is_protected_non_git_path(path)
    ]
    if unexpected_untracked:
        failures.append(
            f"{worktree_path}: unexpected untracked paths: {', '.join(unexpected_untracked)}"
        )

    return failures


def git_status_lines(worktree_path: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", worktree_path, "status", "--porcelain=v1", "--branch"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def current_branch_for_worktree(worktree_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", worktree_path, "rev-parse", "--abbrev-ref", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def git_tracked_files(worktree_path: str, pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", worktree_path, "ls-files", "--", pathspec],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def normalize_root(path: str) -> str:
    normalized = ntpath.normpath(str(path)).replace("\\", "/").rstrip("/")
    return normalized.casefold()


def resolve_status_targets(root: str) -> list[tuple[str, str]]:
    normalized_root = normalize_root(root)
    if normalized_root == normalize_root(CANONICAL_RELEASE_ROOT):
        return list(PROPAGATION_CHAIN)
    return [(current_branch_for_worktree(root), root)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="C:/System_Trading/STOM/STOM_V")
    args = parser.parse_args(argv)

    failures: list[str] = []
    gitignore_text = (Path(args.root) / ".gitignore").read_text(encoding="utf-8")
    if "backtest/graph/" not in gitignore_text:
        failures.append(".gitignore must ignore backtest/graph/")

    for expected_branch, worktree_path in resolve_status_targets(args.root):
        parsed = parse_porcelain(git_status_lines(worktree_path))
        failures.extend(validate_target(expected_branch, worktree_path, parsed))
        tracked_graph_files = git_tracked_files(worktree_path, "backtest/graph")
        if tracked_graph_files:
            failures.append(
                f"{worktree_path}: tracked files present under backtest/graph: "
                f"{', '.join(tracked_graph_files)}"
            )

    if failures:
        print("\n".join(failures))
        return 1

    print("release sync preflight passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
