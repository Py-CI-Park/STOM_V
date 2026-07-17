"""LEGACY_NON_AUTHORITATIVE historical provenance receipt reader.

Legacy receipt JSONL files remain readable only for historical review. New
promotion authority is the authenticated v2 evidence chain; this module must
not create or append receipt files.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from alpha_lab.bridge.registrar import NAME_PREFIX

LEGACY_NON_AUTHORITATIVE = "LEGACY_NON_AUTHORITATIVE"
ALLOWED_SOURCE_KINDS: frozenset = frozenset({"leaf", "event_cell"})
_REQUIRED_KEYS: tuple = ("name", "source", "prereg_sha", "n_trials_context")
__all__ = [
    "ALLOWED_SOURCE_KINDS",
    "LEGACY_NON_AUTHORITATIVE",
    "LegacyReceiptWriteBlockedError",
    "append_receipt",
    "read_receipts",
    "validate_historical_receipt",
]


class LegacyReceiptWriteBlockedError(RuntimeError):
    """Raised when code attempts to write a LEGACY_NON_AUTHORITATIVE receipt."""


def _validate_receipt_fields(record: dict) -> None:
    if not isinstance(record, dict):
        raise ValueError("record는 dict여야 합니다: %r" % (record,))
    for key in _REQUIRED_KEYS:
        if key not in record:
            raise ValueError("영수증 필수 키 누락: %r" % key)
    name = record["name"]
    if not isinstance(name, str) or not name.startswith(NAME_PREFIX):
        raise ValueError("영수증 name은 %r 접두가 강제됩니다: %r" % (NAME_PREFIX, name))
    source = record["source"]
    if not isinstance(source, dict) or "payload" not in source:
        raise ValueError("source는 {kind, payload} dict여야 합니다: %r" % (source,))
    if source.get("kind") not in ALLOWED_SOURCE_KINDS:
        raise ValueError(
            "source.kind는 %s만 허용: %r"
            % (sorted(ALLOWED_SOURCE_KINDS), source.get("kind"))
        )
    if not isinstance(record["prereg_sha"], str) or not record["prereg_sha"]:
        raise ValueError("prereg_sha는 비어있지 않은 str: %r" % (record["prereg_sha"],))
    n_ctx = record["n_trials_context"]
    if isinstance(n_ctx, bool) or not isinstance(n_ctx, int) or n_ctx < 0:
        raise ValueError("n_trials_context는 0 이상의 int: %r" % (n_ctx,))


def validate_historical_receipt(record: dict) -> None:
    """Validate one historical LEGACY_NON_AUTHORITATIVE receipt record."""
    _validate_receipt_fields(record)
    created_at = record.get("created_at")
    if not isinstance(created_at, str) or not created_at:
        raise ValueError("historical created_at은 비어있지 않은 str이어야 합니다")
    try:
        dt.datetime.fromisoformat(created_at)
    except ValueError as exc:
        raise ValueError("historical created_at은 ISO-8601이어야 합니다") from exc


def append_receipt(path, record: dict, *, now) -> dict:
    """Always block legacy receipt writes before inspecting or mutating ``path``."""
    raise LegacyReceiptWriteBlockedError(
        "legacy-receipt-write-blocked: receipts are LEGACY_NON_AUTHORITATIVE; "
        "use the authenticated v2 evidence chain"
    )


def read_receipts(path) -> list:
    """Read and strictly validate historical receipt records, or return [] if absent."""
    target = Path(path)
    if not target.exists():
        return []
    records: list = []
    with open(target, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if line:
                record = json.loads(line)
                validate_historical_receipt(record)
                records.append(record)
    return records
