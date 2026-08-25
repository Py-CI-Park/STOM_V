"""Fail-closed terminal classification for legacy backtest payloads."""

from __future__ import annotations

import json
from collections.abc import Mapping

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]

_NO_TRADES_RECEIPT = "total_report_no_trades"
_FAILURE_RECEIPTS = (
    "engine_strategy_exception",
    "engine_data_response_timeout",
)


def _diagnostics(payload: Mapping[str, JsonValue]) -> Mapping[str, JsonValue] | None:
    value = payload.get("backtest_process_diagnostics")
    return value if isinstance(value, dict) else None


def _positive_event_count(diagnostics: Mapping[str, JsonValue]) -> bool:
    value = diagnostics.get("event_count")
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _checkpoint_receipts(diagnostics: Mapping[str, JsonValue]) -> frozenset[str]:
    receipts: set[str] = set()
    checkpoint = diagnostics.get("last_checkpoint")
    if isinstance(checkpoint, str):
        receipts.add(checkpoint.strip().lower())
    by_source = diagnostics.get("last_by_source")
    if isinstance(by_source, dict):
        receipts.update(
            value.strip().lower()
            for value in by_source.values()
            if isinstance(value, str)
        )
    return frozenset(receipts)


def _contains_failure_receipt(
    payload: Mapping[str, JsonValue],
    diagnostics: Mapping[str, JsonValue],
) -> bool:
    searchable = json.dumps(
        {"payload": dict(payload), "diagnostics": dict(diagnostics)},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    return any(receipt in searchable for receipt in _FAILURE_RECEIPTS)


def is_verified_no_trades_payload(
    returncode: int,
    payload: Mapping[str, JsonValue],
) -> bool:
    """Accept no-trades only with the exact engine receipt and no failure receipt."""
    diagnostics = _diagnostics(payload)
    if diagnostics is None:
        return False
    return (
        returncode == 2
        and payload.get("status") == "error"
        and payload.get("metrics") is None
        and _positive_event_count(diagnostics)
        and _NO_TRADES_RECEIPT in _checkpoint_receipts(diagnostics)
        and not _contains_failure_receipt(payload, diagnostics)
    )
