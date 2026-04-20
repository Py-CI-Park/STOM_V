"""Small checkpoint recorder for CLI backtest result payloads."""

from __future__ import annotations

import time
from typing import Any


class BacktestCheckpointRecorder:
    """Record named backtest checkpoints as JSON-friendly dictionaries."""

    def __init__(self) -> None:
        self.started_at = time.monotonic()
        self.events: list[dict[str, Any]] = []

    def mark(self, name: str, detail: dict[str, Any] | None = None) -> None:
        self.events.append(
            {
                'name': name,
                'elapsed_seconds': self._elapsed_seconds(),
                'detail': detail or {},
            }
        )

    @property
    def last_checkpoint(self) -> str | None:
        if not self.events:
            return None
        return self.events[-1]['name']

    def to_result_fields(
        self,
        status: str,
        cleanup_status: str | None = None,
    ) -> dict[str, Any]:
        fields = {
            'checkpoint_status': status,
            'last_checkpoint': self.last_checkpoint,
            'elapsed_seconds': self._elapsed_seconds(),
            'checkpoints': self.events,
        }
        if cleanup_status is not None:
            fields['cleanup_status'] = cleanup_status
        return fields

    def _elapsed_seconds(self) -> float:
        return round(time.monotonic() - self.started_at, 3)
