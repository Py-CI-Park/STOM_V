"""Deterministic D3 event controls; these functions never inspect PnL or labels."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta
from typing import Any, Iterable, Mapping


def _copy_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def timestamp_shuffle_control(rows: Iterable[Mapping[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    result = _copy_rows(rows)
    values = [row.get("timestamp") for row in result]
    random.Random(seed).shuffle(values)
    for row, value in zip(result, values, strict=True):
        row["timestamp"] = value
        row["control"] = "timestamp_shuffle"
    return result


def symbol_shuffle_control(rows: Iterable[Mapping[str, Any]], *, seed: int) -> list[dict[str, Any]]:
    result = _copy_rows(rows)
    values = [row.get("symbol") for row in result]
    random.Random(seed).shuffle(values)
    for row, value in zip(result, values, strict=True):
        row["symbol"] = value
        row["control"] = "symbol_shuffle"
    return result


def direction_inversion_control(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result = _copy_rows(rows)
    for row in result:
        direction = str(row.get("direction") or "long")
        row["direction"] = "short" if direction == "long" else "long"
        row["control"] = "direction_inversion"
    return result


def event_offset_random_control(rows: Iterable[Mapping[str, Any]], *, seed: int,
                                max_offset_seconds: int = 120) -> list[dict[str, Any]]:
    result = _copy_rows(rows)
    rng = random.Random(seed)
    for row in result:
        offset = rng.randint(-max_offset_seconds, max_offset_seconds)
        original = row.get("timestamp")
        row["original_timestamp"] = original
        text = str(original)
        if text.isdigit() and len(text) == 14:
            shifted = datetime.strptime(text, "%Y%m%d%H%M%S") + timedelta(seconds=offset)
            row["timestamp"] = int(shifted.strftime("%Y%m%d%H%M%S"))
        elif isinstance(original, (int, float)):
            row["timestamp"] = original + offset
        else:
            raise ValueError("event_offset_random requires numeric or YYYYMMDDHHMMSS timestamp")
        row["offset_seconds"] = offset
        row["control"] = "event_offset_random"
    return result


def parameter_random_baseline(parameters: Mapping[str, tuple[float, float]], *, seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    return {name: rng.uniform(float(bounds[0]), float(bounds[1])) for name, bounds in sorted(parameters.items())}


def control_receipt(name: str, rows: Iterable[Mapping[str, Any]], *, seed: int | None) -> dict[str, Any]:
    payload = [dict(row) for row in rows]
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "control": name, "seed": seed, "row_count": len(payload),
        "sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "authority": "negative_control_only_no_adoption",
    }
