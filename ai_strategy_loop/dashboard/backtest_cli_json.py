"""Recover the final structured CLI payload from noisy subprocess output."""

from __future__ import annotations

from typing import Final

from pydantic import ConfigDict, TypeAdapter, ValidationError

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue

type JsonDocument = dict[str, JsonValue]

_DOCUMENT_ADAPTER: Final[TypeAdapter[JsonDocument]] = TypeAdapter(
    JsonDocument,
    config=ConfigDict(strict=True),
)


def parse_cli_json(stdout: str) -> JsonDocument:
    """Return the last status-bearing JSON document embedded in CLI output."""
    text = stdout.strip()
    if not text:
        return {}

    latest: JsonDocument = {}
    depth = 0
    object_start = -1
    in_string = False
    escaped = False
    for index, character in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            if depth == 0:
                object_start = index
            depth += 1
        elif character == "}" and depth > 0:
            depth -= 1
        if depth != 0 or object_start < 0:
            continue
        try:
            document = _DOCUMENT_ADAPTER.validate_json(
                text[object_start : index + 1]
            )
        except ValidationError:
            object_start = -1
            continue
        if isinstance(document.get("status"), str):
            latest = document
        object_start = -1
    return latest
