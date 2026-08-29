"""Measured SYS-04 node selectors for the slow unit Gate."""

from __future__ import annotations

from typing import Final

SLOW_SUITE_NODE_PREFIXES: Final[tuple[str, ...]] = (
    "tests/unit/test_alpha_bridge.py::TestPromotionV2::",
    (
        "tests/unit/test_alpha_catalog.py::"
        "test_minimal_authority_catalog_builds_real_pre_and_post"
    ),
)


def is_slow_suite(nodeid: str) -> bool:
    """Return whether a collected node belongs to the measured slow Gate."""
    return nodeid.startswith(SLOW_SUITE_NODE_PREFIXES)
