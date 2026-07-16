"""Build the one sealed G005-X1 CSV-row input snapshot.

This script only materializes the preregistered external CSV rows into the
canonical JSON input. It performs no outcome aggregation, engine execution,
DB writes, registration, promotion, retry, or rescue action.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "g005-x1-input-v1"
HYPOTHESIS_ID = "G005-X1-EXIT-COMPETING-RISK"
PREREGISTRATION_PATH = "docs/research/condition_research/plans/2026-07-16_g005_x1_competing_risk_preregistration.md"
CANONICAL_OUTPUT_PATH = ROOT / "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json"
REQUIRED_FIELDS = ("매수시간", "매도시간", "매도조건", "수익률")
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
YEARS = (2022, 2023)
EXPECTED_FILTERED_COUNTS = MappingProxyType({2022: 510, 2023: 1148})
ZERO_SIDE_EFFECT_COUNTERS = MappingProxyType(
    {
        "engine_calls": 0,
        "db_writes": 0,
        "strategy_registrations": 0,
        "promotions": 0,
        "retries": 0,
        "rescue_runs": 0,
    }
)


@dataclass(frozen=True)
class SourceSpec:
    slot: str
    group: str
    path: str
    sha256: str
    size_bytes: int
    raw_rows: int
    encoding: str = "utf-8"

    def descriptor(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "group": self.group,
            "path": self.path,
            "encoding": self.encoding,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "raw_rows": self.raw_rows,
        }


SOURCE_FILES = (
    SourceSpec(
        slot="RR8_12",
        group="RR8",
        path="C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_12_20260707074238.csv",
        sha256="f5e3807f26c32d8e2409a56ed1cdc89c80c13b37bcf36f0dbed811595e2ee9ed",
        size_bytes=153817,
        raw_rows=454,
    ),
    SourceSpec(
        slot="RR8_0",
        group="RR8",
        path="C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_0_20260707074352.csv",
        sha256="ae90e89663dd1a704535893556a05954b016ec6b6ece766b9eeb236153fdd06c",
        size_bytes=115829,
        raw_rows=338,
    ),
    SourceSpec(
        slot="RR8_21",
        group="RR8",
        path="C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_RR8_21_20260707074459.csv",
        sha256="a22af054c264087d2b87f52ac178b7fe19d49a3c71e660965f6803b83083131f",
        size_bytes=128654,
        raw_rows=380,
    ),
    SourceSpec(
        slot="GPTAUTH_G8",
        group="GPTAUTH_G8",
        path="C:/System_Trading/STOM/STOM_V.wt-alpha/backtest/csv/stock_bt_ALP_V4_GPTAUTH_G8_20260707075127.csv",
        sha256="830a003a046e6e1f14372838c458badb198dedb069539d2b6e8ede7f807eb4cd",
        size_bytes=464671,
        raw_rows=1447,
    ),
)


class X1InputError(ValueError):
    """The sealed X1 input contract failed before canonical JSON output."""


def _fail(message: str) -> None:
    raise X1InputError(message)


def _coerce_source_spec(value: SourceSpec | Mapping[str, Any]) -> SourceSpec:
    if isinstance(value, SourceSpec):
        return value
    required = {"slot", "group", "path", "sha256", "size_bytes", "raw_rows"}
    if not isinstance(value, Mapping) and all(hasattr(value, name) for name in required):
        return SourceSpec(
            slot=str(getattr(value, "slot")),
            group=str(getattr(value, "group")),
            path=str(getattr(value, "path")),
            encoding=str(getattr(value, "encoding", "utf-8")),
            sha256=str(getattr(value, "sha256")),
            size_bytes=int(getattr(value, "size_bytes")),
            raw_rows=int(getattr(value, "raw_rows")),
        )
    if not isinstance(value, Mapping) or not required <= set(value):
        _fail(f"malformed source descriptor: {value!r}")
    return SourceSpec(
        slot=str(value["slot"]),
        group=str(value["group"]),
        path=str(value["path"]),
        encoding=str(value.get("encoding", "utf-8")),
        sha256=str(value["sha256"]),
        size_bytes=int(value["size_bytes"]),
        raw_rows=int(value["raw_rows"]),
    )


def _coerce_sources(source_files: Iterable[SourceSpec | Mapping[str, Any]]) -> tuple[SourceSpec, ...]:
    sources = tuple(_coerce_source_spec(item) for item in source_files)
    if not sources:
        _fail("at least one sealed source is required")
    slots = [source.slot for source in sources]
    if len(set(slots)) != len(slots):
        _fail("source slots must be unique")
    return sources


def _coerce_expected_counts(expected_counts: Mapping[int | str, int]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for key, value in expected_counts.items():
        year = int(key)
        if year not in YEARS:
            _fail(f"unexpected filtered year: {year}")
        count = int(value)
        if count < 0:
            _fail(f"negative filtered count for {year}: {count}")
        counts[year] = count
    if set(counts) != set(YEARS):
        _fail(f"expected counts must cover exactly {YEARS}")
    return counts


def _json_year_counts(counts: Mapping[int, int]) -> dict[str, int]:
    return {str(year): int(counts[year]) for year in YEARS}


def _expected_count_record(expected_counts: Mapping[int, int]) -> dict[str, int]:
    by_year = _json_year_counts(expected_counts)
    return {**by_year, "total": sum(int(expected_counts[year]) for year in YEARS)}


def contract_descriptor(
    source_files: Iterable[SourceSpec | Mapping[str, Any]] = SOURCE_FILES,
    expected_counts: Mapping[int | str, int] = EXPECTED_FILTERED_COUNTS,
) -> dict[str, Any]:
    sources = _coerce_sources(source_files)
    counts = _coerce_expected_counts(expected_counts)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "SEALED",
        "claim_type": "descriptive_not_causal",
        "source_preregistration": PREREGISTRATION_PATH,
        "discovery_window": {"start": "2022-01-01", "end": "2023-12-31"},
        "required_fields": list(REQUIRED_FIELDS),
        "timestamp_format": TIMESTAMP_FORMAT,
        "date_filter": "매수시간[0:4] in {'2022','2023'} before row output",
        "same_day_required": True,
        "condition_text": "raw Unicode 매도조건; no strip/normalization/casefold",
        "y_unit": "수익률 percentage point; finite numeric only",
        "expected_filtered_counts": _expected_count_record(counts),
        "comparison_groups": {
            "left": "RR8 family: RR8_12 + RR8_0 + RR8_21 strategy-slot ledgers, no deduplication",
            "right": "GPTAUTH_G8",
            "raw_contrast": "mean(RR8 수익률 pp) - mean(GPTAUTH_G8 수익률 pp)",
        },
        "source_files": [source.descriptor() for source in sources],
        "bans": [
            "2024_plus_rows",
            "outcome_aggregation_in_builder",
            "engine_execution",
            "db_write",
            "strategy_registration",
            "promotion",
            "retry",
            "rescue",
        ],
    }


def _source_identity_from_bytes(spec: SourceSpec, data: bytes, raw_rows: int) -> dict[str, Any]:
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "raw_rows": raw_rows,
    }


def _validate_header(fieldnames: list[str] | None, source_label: str) -> None:
    if fieldnames is None:
        _fail(f"{source_label}: missing CSV header")
    for field in REQUIRED_FIELDS:
        if fieldnames.count(field) != 1:
            _fail(f"{source_label}: required CSV field must appear exactly once: {field}")


def _count_raw_rows(text: str, source_label: str) -> int:
    reader = csv.DictReader(io.StringIO(text))
    _validate_header(reader.fieldnames, source_label)
    raw_rows = 0
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            _fail(f"{source_label}: row {row_number} has surplus ambiguous CSV fields")
        raw_rows += 1
    return raw_rows


def _capture_source(spec: SourceSpec) -> tuple[dict[str, Any], str]:
    path = Path(spec.path)
    if not path.is_file():
        _fail(f"missing sealed source: {spec.path}")
    data = path.read_bytes()
    try:
        text = data.decode(spec.encoding)
    except UnicodeDecodeError as exc:
        _fail(f"{spec.slot}: UTF-8 decode failed: {exc}")
    raw_rows = _count_raw_rows(text, spec.slot)
    identity = _source_identity_from_bytes(spec, data, raw_rows)
    expected = {"sha256": spec.sha256, "size_bytes": spec.size_bytes, "raw_rows": spec.raw_rows}
    if identity != expected:
        _fail(f"{spec.slot}: source drift/count mismatch: expected {expected!r}, observed {identity!r}")
    return identity, text


def _timestamp(value: Any, field: str, source_label: str, row_number: int) -> str:
    if not isinstance(value, str) or len(value) != 14 or not value.isdigit():
        _fail(f"{source_label}: row {row_number} invalid {field}: {value!r}")
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError as exc:
        _fail(f"{source_label}: row {row_number} invalid {field}: {value!r}: {exc}")
    return value


def _finite_y(value: Any, source_label: str, row_number: int) -> float:
    if not isinstance(value, str):
        _fail(f"{source_label}: row {row_number} invalid 수익률: {value!r}")
    try:
        parsed = float(value)
    except ValueError as exc:
        _fail(f"{source_label}: row {row_number} invalid 수익률: {value!r}: {exc}")
    if not math.isfinite(parsed):
        _fail(f"{source_label}: row {row_number} non-finite 수익률: {value!r}")
    return parsed


def parse_source_rows(spec: SourceSpec | Mapping[str, Any], text: str) -> list[dict[str, Any]]:
    source = _coerce_source_spec(spec)
    reader = csv.DictReader(io.StringIO(text))
    _validate_header(reader.fieldnames, source.slot)
    rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(reader, start=2):
        if None in row:
            _fail(f"{source.slot}: row {row_number} has surplus ambiguous CSV fields")
        buy_time = _timestamp(row.get("매수시간"), "매수시간", source.slot, row_number)
        year = int(buy_time[:4])
        if year not in YEARS:
            continue
        day = buy_time[:8]
        sell_time = _timestamp(row.get("매도시간"), "매도시간", source.slot, row_number)
        if sell_time[:8] != day:
            _fail(f"{source.slot}: row {row_number} buy/sell day mismatch: {buy_time!r} {sell_time!r}")
        condition = row.get("매도조건")
        if not isinstance(condition, str):
            _fail(f"{source.slot}: row {row_number} invalid 매도조건: {condition!r}")
        y = _finite_y(row.get("수익률"), source.slot, row_number)
        rows.append(
            {
                "group": source.group,
                "slot": source.slot,
                "day": day,
                "buy_time": buy_time,
                "sell_time": sell_time,
                "condition": condition,
                "y": y,
            }
        )
    return rows


def _count_record(
    rows: Iterable[Mapping[str, Any]],
    source_files: Iterable[SourceSpec | Mapping[str, Any]],
    expected_counts: Mapping[int, int],
) -> dict[str, Any]:
    sources = _coerce_sources(source_files)
    by_year = {str(year): 0 for year in YEARS}
    by_group: dict[str, int] = {}
    by_group_year: dict[str, dict[str, int]] = {}
    by_slot = {source.slot: 0 for source in sources}
    for row in rows:
        year = int(str(row["day"])[:4])
        group = str(row["group"])
        slot = str(row["slot"])
        by_year[str(year)] += 1
        by_group[group] = by_group.get(group, 0) + 1
        by_group_year.setdefault(group, {str(item): 0 for item in YEARS})[str(year)] += 1
        by_slot[slot] = by_slot.get(slot, 0) + 1
    return {
        "expected": _expected_count_record(expected_counts),
        "by_year": by_year,
        "total": sum(by_year.values()),
        "by_group": dict(sorted(by_group.items())),
        "by_group_year": {group: by_group_year[group] for group in sorted(by_group_year)},
        "by_slot": by_slot,
    }


def build_snapshot(
    source_files: Iterable[SourceSpec | Mapping[str, Any]] = SOURCE_FILES,
    expected_counts: Mapping[int | str, int] = EXPECTED_FILTERED_COUNTS,
) -> dict[str, Any]:
    sources = _coerce_sources(source_files)
    expected = _coerce_expected_counts(expected_counts)
    rows: list[dict[str, Any]] = []
    source_records: list[dict[str, Any]] = []
    for source in sources:
        pre, text = _capture_source(source)
        rows.extend(parse_source_rows(source, text))
        post, _ = _capture_source(source)
        if pre != post:
            _fail(f"{source.slot}: source changed during materialization")
        source_records.append({**source.descriptor(), "pre": pre, "post": post})
    counts = _count_record(rows, sources, expected)
    if counts["by_year"] != _json_year_counts(expected) or counts["total"] != sum(expected.values()):
        _fail(
            "filtered denominator mismatch: "
            f"expected {_expected_count_record(expected)!r}, observed "
            f"{{'2022': {counts['by_year'].get('2022', 0)}, '2023': {counts['by_year'].get('2023', 0)}, 'total': {counts['total']}}}"
        )
    return {
        "schema": SCHEMA,
        "contract": contract_descriptor(sources, expected),
        "sources": source_records,
        "counts": counts,
        "rows": rows,
        "side_effect_counters": dict(ZERO_SIDE_EFFECT_COUNTERS),
    }


def write_snapshot(path: Path, snapshot: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")


def main() -> None:
    snapshot = build_snapshot()
    write_snapshot(CANONICAL_OUTPUT_PATH, snapshot)
    print(json.dumps({"schema": SCHEMA, "path": CANONICAL_OUTPUT_PATH.as_posix(), "counts": snapshot["counts"]}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
