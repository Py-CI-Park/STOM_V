"""Authenticated v2 promotion bridge."""

from alpha_lab.discipline.evidence import verify_promotion_result_v2
from alpha_lab.bridge.registrar import (
    LegacyPromotionBlockedError,
    inspect_promotion_journal_v2,
    register_conditions_v2,
    verify_promotion_manifest,
)

__all__ = [
    "LegacyPromotionBlockedError",
    "inspect_promotion_journal_v2",
    "register_conditions_v2",
    "verify_promotion_manifest",
    "verify_promotion_result_v2",
]
