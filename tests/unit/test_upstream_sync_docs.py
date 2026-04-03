from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_worktree_strategy_mentions_the_actual_worktree_layout():
    text = read_text("docs/WORKTREE_STRATEGY.md")

    assert "STOM_V.wt-2uc/" in text
    assert "STOM_V.wt-dev/" in text
    assert "research/init" in text
    assert "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init" in text


def test_upstream_sync_strategy_uses_v2_only_ingress_and_release_preflight():
    text = read_text("docs/UPSTREAM_SYNC_STRATEGY.md")

    assert "python scripts/verify_release_sync.py" in text
    assert "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init" in text
    assert "https://github.com/devstom/STOM.git" in text
    assert "STOM_devstom" in text


def test_claude_guide_uses_the_current_worktree_mapping():
    text = read_text("CLAUDE.md")

    assert "STOM_V.wt-2uc/" in text
    assert "STOM_V.wt-dev/" in text
    assert "STOM_Version_2U_C_CLI_v267" in text
    assert "python scripts/verify_release_sync.py" in text
