# -*- coding: utf-8 -*-
"""Historical B1 finalization evidence notice; this module is non-executable."""

from __future__ import annotations


VERDICT_NAME = "_ab_verdict.json"
RECEIPT_NAME = "b1_registration_receipt.json"
NOTICE = (
    "HISTORICAL EVIDENCE: the 2026-07-12 B1 finalization is retained only as "
    f"historical evidence. See committed {VERDICT_NAME} and {RECEIPT_NAME}.\n"
    "NON-EXECUTABLE ARCHIVE: this notice performs no mutation.\n"
    "Any future promotion requires a fresh v2 evidence chain and an authorized non-protected target."
)


def main() -> int:
    """Print the read-only archival notice."""
    print(NOTICE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
