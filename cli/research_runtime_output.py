"""Runtime JSON output support for discovery research loops."""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any


class ResearchRuntimeWriteError(RuntimeError):
    """Raised when a research runtime payload cannot be written."""

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        super().__init__(f'runtime output write failed for {path}: {message}')


class ResearchRuntimeRecorder:
    """Record research checkpoints and optionally persist runtime JSON."""

    def __init__(self, output_path: str | None = None) -> None:
        self.output_path = output_path
        self.started_at = time.monotonic()
        self.events: list[dict[str, Any]] = []

    def mark(
        self,
        name: str,
        *,
        phase: str | None = None,
        message: str | None = None,
        candidate_index: int | None = None,
        strategy_name: str | None = None,
        consecutive_failure_count: int | None = None,
        detail: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        event = {
            'name': name,
            'elapsed_seconds': self._elapsed_seconds(),
        }
        if phase is not None:
            event['phase'] = phase
        if message is not None:
            event['message'] = message
        if candidate_index is not None:
            event['candidate_index'] = candidate_index
        if strategy_name is not None:
            event['strategy_name'] = strategy_name
        if consecutive_failure_count is not None:
            event['consecutive_failure_count'] = consecutive_failure_count
        if detail is not None:
            event['detail'] = _json_safe(detail)
        self.events.append(event)
        return event

    def summary(self) -> dict[str, Any]:
        return {
            'event_count': len(self.events),
            'last_checkpoint': self.events[-1]['name'] if self.events else None,
            'elapsed_seconds': self._elapsed_seconds(),
        }

    def decorate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            **payload,
            'checkpoints': list(self.events),
            'checkpoint_summary': self.summary(),
        }

    def write(self, payload: dict[str, Any]) -> str | None:
        if not self.output_path:
            return None
        path = Path(self.output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            text = json.dumps(self.decorate(payload), ensure_ascii=False, indent=2, default=str)
            temp_path = path.with_name(f'.{path.name}.tmp')
            temp_path.write_text(text, encoding='utf-8')
            os.replace(temp_path, path)
        except Exception as exc:
            raise ResearchRuntimeWriteError(str(path), str(exc)) from exc
        return str(path)

    def _elapsed_seconds(self) -> float:
        return round(time.monotonic() - self.started_at, 3)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return repr(value)
