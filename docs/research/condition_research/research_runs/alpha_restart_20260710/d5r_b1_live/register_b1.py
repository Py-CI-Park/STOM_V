# -*- coding: utf-8 -*-
"""Historical B1 registration evidence notice; this module is non-executable."""

from __future__ import annotations


RECEIPT_NAME = "b1_registration_receipt.json"
NOTICE = (
    "HISTORICAL EVIDENCE: the 2026-07-12 B1 registration is retained only as "
    f"historical evidence. See {RECEIPT_NAME}.\n"
    "NON-EXECUTABLE ARCHIVE: this notice performs no mutation.\n"
    "Any future promotion requires a fresh v2 evidence chain and an authorized non-protected target."
)


def main() -> int:
    """Print the read-only archival notice."""
    print(NOTICE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
