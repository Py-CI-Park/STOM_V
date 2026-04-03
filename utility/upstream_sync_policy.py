UPSTREAM_REMOTE_URL = "https://github.com/devstom/STOM.git"
LOCAL_UPSTREAM_MIRROR = "C:/System_Trading/STOM/STOM_devstom"

PROPAGATION_CHAIN = (
    ("STOM_Version_2", "C:/System_Trading/STOM/STOM_V"),
    ("STOM_Version_2U", "C:/System_Trading/STOM/STOM_V.wt-2u"),
    ("STOM_Version_2U_C", "C:/System_Trading/STOM/STOM_V.wt-2uc"),
    ("STOM_Version_2U_C_CLI_v267", "C:/System_Trading/STOM/STOM_V.wt-dev"),
    ("research/init", "C:/System_Trading/STOM/STOM_V.wt-lab"),
)

RELEASE_OVERLAY_EXCLUDES = (
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

PROTECTED_NON_GIT_PATHS = ("backtest/graph/",)


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/").strip()


def expected_branch_for_worktree(worktree_path: str) -> str:
    normalized = _normalize_path(worktree_path).rstrip("/")
    for branch, root in PROPAGATION_CHAIN:
        if normalized == root.rstrip("/"):
            return branch
    raise KeyError(f"unknown worktree path: {worktree_path}")


def is_protected_non_git_path(path: str) -> bool:
    normalized = _normalize_path(path)
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if ".." in normalized.split("/"):
        return False
    for protected in PROTECTED_NON_GIT_PATHS:
        prefix = protected.rstrip("/")
        if normalized == prefix or normalized.startswith(f"{prefix}/"):
            return True
    return False
