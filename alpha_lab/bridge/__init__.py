"""Append-only v2 promotion bridge.

Use ``register_conditions_v2`` only with verified PRE provenance. The legacy
``register_conditions`` fence remains exported so callers fail closed rather
than bypassing the authenticated journal.
"""

from alpha_lab.bridge.receipts import (
    ALLOWED_SOURCE_KINDS,
    append_receipt,
    read_receipts,
)
from alpha_lab.discipline.evidence import verify_promotion_result_v2
from alpha_lab.bridge.registrar import (
    LegacyPromotionBlockedError,
    NAME_PREFIX,
    inspect_promotion_journal_v2,
    register_conditions,
    register_conditions_v2,
    verify_promotion_manifest,
)

__all__ = [
    "ALLOWED_SOURCE_KINDS",
    "LegacyPromotionBlockedError",
    "NAME_PREFIX",
    "append_receipt",
    "inspect_promotion_journal_v2",
    "read_receipts",
    "register_conditions",
    "register_conditions_v2",
    "verify_promotion_manifest",
    "verify_promotion_result_v2",
]
