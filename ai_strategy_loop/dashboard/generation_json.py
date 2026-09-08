"""Finite JSON projection of legacy generation metadata; originals stay intact."""

from __future__ import annotations

import math
from datetime import datetime
from typing import assert_never

from pydantic import JsonValue, RootModel


class GenerationJson(RootModel[dict[str, JsonValue]]):
    """Named projection boundary; not an AnalysisBundle or execution receipt."""


def finite_timestamp(value: JsonValue) -> float | None:
    """Legacy context needs a platform-representable timestamp, not just a finite one."""
    number = finite_metric(value)
    if number is None:
        return None
    try:
        _ = datetime.fromtimestamp(number)  # noqa: DTZ006 -- Match the legacy context's local timestamp conversion.
    except (ValueError, OverflowError, OSError):
        return None
    return number


def finite_json(value: JsonValue) -> JsonValue:
    match value:
        case None | str() | bool() | int():
            return value
        case float():
            return value if math.isfinite(value) else None
        case list():
            return [finite_json(item) for item in value]
        case dict():
            return {key: finite_json(item) for key, item in value.items()}
        case unreachable:
            assert_never(unreachable)


def finite_metric(value: JsonValue) -> float | None:
    match value:
        case None | bool() | list() | dict():
            return None
        case str() | int() | float():
            try:
                number = float(value)
            except (ValueError, OverflowError):
                return None
            return number if math.isfinite(number) else None
        case unreachable:
            assert_never(unreachable)
