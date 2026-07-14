"""Retired D5/D9 measurement entry point.

Historical records may still reference this filename, but the legacy workflow
cannot emit the required v2 receipt, claim, artifact, and candidate evidence.
It is deliberately non-executable and has no authority to measure or write.
"""
from __future__ import annotations

import sys

NOTICE = (
    "D5/D9 measurement is retired and non-authoritative; "
    "it cannot produce required v2 receipt/claim/artifact/candidate evidence."
)


def main(argv=None) -> int:
    del argv
    sys.stderr.write(NOTICE + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
