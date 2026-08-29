"""SYS-04 slow unit Gate 분류 계약."""

from __future__ import annotations

from tests.unit.slow_suite_manifest import is_slow_suite


def test_promotion_v2_contracts_are_slow_suite() -> None:
    """Given a PromotionV2 node, When classified, Then it belongs to slow Gate."""
    nodeid = (
        "tests/unit/test_alpha_bridge.py::TestPromotionV2::"
        "test_canonical_post_is_catalog_direct_input"
    )

    assert is_slow_suite(nodeid)


def test_real_authority_catalog_contract_is_slow_suite() -> None:
    """Given the measured catalog node, When classified, Then it belongs to slow Gate."""
    nodeid = (
        "tests/unit/test_alpha_catalog.py::"
        "test_minimal_authority_catalog_builds_real_pre_and_post"
    )

    assert is_slow_suite(nodeid)


def test_nearby_fast_contract_stays_in_commit_gate() -> None:
    """Given a nearby fast node, When classified, Then it remains in fast Gate."""
    nodeid = "tests/unit/test_alpha_catalog.py::test_rebuild_is_idempotent"

    assert not is_slow_suite(nodeid)
