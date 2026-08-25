"""Canonical JSON and read-only artifact identity helpers for analysis bundles."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import override

from ai_strategy_loop.dashboard.backtest_terminal_classification import JsonValue


@dataclass(frozen=True, slots=True)
class AnalysisBundleBuildError(ValueError):
    code: str

    @override
    def __str__(self) -> str:
        return self.code


def canonical_json(value: JsonValue) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: JsonValue) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_identity(path: Path | None) -> tuple[str | None, int | None]:
    if path is None:
        return None, None
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise AnalysisBundleBuildError("analysis_bundle_csv_unreadable") from exc
    return digest.hexdigest(), size
