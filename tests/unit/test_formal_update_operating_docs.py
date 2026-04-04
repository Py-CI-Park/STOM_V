from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


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


def test_agents_points_to_the_operating_system_and_registry():
    text = read_text("AGENTS.md")

    assert "FORMAL_UPDATE_OPERATING_SYSTEM.md" in text
    assert "CARRY_FORWARD_REGISTRY.md" in text
    assert "docs/update_log/2026-04-05_v274_v277_cycle_status.md" in text
    assert "V2 -> 2U -> 2U_C -> CLI_v267 -> research/init" in text


def test_central_claude_mentions_preflight_and_entrypoint_docs():
    text = read_text("CLAUDE.md")

    assert "python scripts/verify_release_sync.py" in text
    assert "docs/FORMAL_UPDATE_OPERATING_SYSTEM.md" in text
    assert "docs/CARRY_FORWARD_REGISTRY.md" in text
    assert "docs/update_log/2026-04-05_v274_v277_cycle_status.md" in text


def test_cycle_status_contains_current_release_and_downstream_heads():
    relative_path = "docs/update_log/2026-04-05_v274_v277_cycle_status.md"

    assert (ROOT / relative_path).exists()

    text = read_text(relative_path)

    assert "## Release commits" in text
    assert "## Downstream heads" in text
    assert "## Protected result data" in text
    assert "## Next recommended start" in text


def test_registry_tracks_current_carry_forward_items():
    text = read_text("docs/CARRY_FORWARD_REGISTRY.md")

    assert "# Carry Forward Registry" in text
    assert "## Release-side upstream risks" in text
    assert "## Downstream carry-forward tests" in text
    assert "## Rule" in text
