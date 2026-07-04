"""Filename-safe naming helpers for lattice strategy registration."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
UNSAFE_COMPONENT_CHARS = re.compile(r"[^A-Za-z0-9_.-]+")


def sanitize_strategy_component(raw: str) -> str:
    safe = UNSAFE_FILENAME_CHARS.sub("_", raw)
    safe = UNSAFE_COMPONENT_CHARS.sub("_", safe)
    safe = re.sub(r"_+", "_", safe).strip("._ ")
    if not safe:
        raise ValueError(f"strategy component became empty after sanitize: {raw!r}")
    if len(safe) > 160:
        digest = hashlib.sha256(safe.encode("utf-8")).hexdigest()[:12]
        safe = f"{safe[:147].rstrip('._ ')}_{digest}"
    return safe


def is_filename_safe(name: str) -> bool:
    return name == sanitize_strategy_component(name)


def legacy_names(condition_id: str) -> tuple[str, str]:
    return f"LAT_{condition_id}_B", f"LAT_{condition_id}_S"


def mapping_entry(seed: Mapping[str, Any], pair: Mapping[str, str]) -> dict[str, Any]:
    legacy_buy_name, legacy_sell_name = legacy_names(str(seed["condition_id"]))
    return {
        "condition_id": seed["condition_id"],
        "cell_id": seed["cell_id"],
        "family": seed["family"],
        "legacy_buy_name": legacy_buy_name,
        "legacy_sell_name": legacy_sell_name,
        "safe_buy_name": pair["buy"],
        "safe_sell_name": pair["sell"],
        "legacy_buy_filename_safe": is_filename_safe(legacy_buy_name),
        "legacy_sell_filename_safe": is_filename_safe(legacy_sell_name),
        "safe_buy_filename_safe": is_filename_safe(pair["buy"]),
        "safe_sell_filename_safe": is_filename_safe(pair["sell"]),
        "name_style": "filename_safe_v2",
    }


def unsafe_legacy_name_count(seeds: list[dict[str, Any]]) -> int:
    total = 0
    for seed in seeds:
        legacy_buy_name, legacy_sell_name = legacy_names(str(seed["condition_id"]))
        total += 0 if is_filename_safe(legacy_buy_name) else 1
        total += 0 if is_filename_safe(legacy_sell_name) else 1
    return total


def unsafe_target_name_count(pairs: list[dict[str, str]]) -> int:
    return sum(
        0 if is_filename_safe(pair[key]) else 1
        for pair in pairs
        for key in ("buy", "sell")
    )
