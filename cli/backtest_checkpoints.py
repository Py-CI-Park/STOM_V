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
                'detail': _detail_to_json_friendly(detail),
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


def _detail_to_json_friendly(detail: dict[str, Any] | None) -> dict[str, Any]:
    if detail is None:
        return {}
    return _to_json_friendly(detail)


def _to_json_friendly(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_to_json_friendly(item) for item in value]
    if isinstance(value, dict):
        return {
            _to_json_friendly_key(key): _to_json_friendly(item)
            for key, item in value.items()
        }
    return repr(value)


def _to_json_friendly_key(key: Any) -> str | int | float | bool | None:
    if key is None or isinstance(key, (str, int, float, bool)):
        return key
    return repr(key)
