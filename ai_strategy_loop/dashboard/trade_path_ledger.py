"""Append-only, compact provenance ledger for QSP7 research events."""

from __future__ import annotations

import json
import threading
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Final


LEDGER_SCHEMA: Final[str] = "stom-trade-path-ledger-v1"


class TradePathLedger:
    """Persist summaries only; tick paths and mutable strategy state stay outside."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def append(
        self, *, event: str, authority: str, payload: dict[str, object],
    ) -> dict[str, object]:
        record: dict[str, object] = {
            "schema_version": LEDGER_SCHEMA,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "authority": authority,
            "payload": payload,
        }
        encoded = json.dumps(record, ensure_ascii=False, default=str, separators=(",", ":"))
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(encoded + "\n")
        return record

    def tail(self, limit: int = 200) -> tuple[dict[str, object], ...]:
        bounded = max(1, min(limit, 1_000))
        with self._lock:
            try:
                with self.path.open("r", encoding="utf-8") as handle:
                    lines = deque(handle, maxlen=bounded)
            except OSError:
                return ()
        records: list[dict[str, object]] = []
        for line in lines:
            try:
                value = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(value, dict) and value.get("schema_version") == LEDGER_SCHEMA:
                records.append(value)
        return tuple(reversed(records))
