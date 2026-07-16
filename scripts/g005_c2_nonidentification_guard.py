#!/usr/bin/env python3
"""Import-safe schema sentinel for terminal nonidentified G005-C2."""
from __future__ import annotations

MESSAGE = (
    "G005-C2-ACTIVATION-ORDER is terminal nonidentified: no exact "
    "pre-existing activation trace authority exists; this guard is a "
    "schema sentinel only, not an authorized target invocation."
)


def main() -> None:
    """Abort every attempted execution without filesystem or outcome access."""
    raise SystemExit(MESSAGE)


if __name__ == "__main__":
    main()
