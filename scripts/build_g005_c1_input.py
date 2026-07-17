#!/usr/bin/env python3
"""Build the sealed, outcome-preserving G005-C1 time-shift input snapshot."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
from pathlib import Path
from numbers import Integral
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
RUN_ROOT = ROOT / "docs/research/condition_research/research_runs/alpha_restart_20260710"
OUTPUT_PATH = RUN_ROOT / "g005/c1_input.json"
L3_SOURCE_PATH = Path(
    "C:/System_Trading/STOM/STOM_V.wt-alpha/docs/research/condition_research/"
    "research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet"
)
D1_SOURCE_PATH = RUN_ROOT / "stats_map/d1_onset_clause_bits.parquet"

INPUT_SCHEMA = "g005-c1-input-v1"
HYPOTHESIS_ID = "G005-C1-TIME-SHIFT"
YEARS = (2022, 2023)
DISCOVERY_START_DAY = 20220323
DISCOVERY_END_DAY = 20231231
DISCOVERY_WINDOW = {"start": "2022-03-23", "end": "2023-12-31"}
PAIRS = ((16, 37), (16, 38))
JOINED_ROWS = 863446
LABELED_ROWS = 862932
POOLED_CELL_FLOOR = 2000
ANNUAL_CELL_FLOOR = 400
PLACEBO_SEED = 2026071601
PLACEBO_REPLICATES = 400
BOOTSTRAP_SEED = 2026071602
BOOTSTRAP_DRAWS = 20000

L3_KEY = "l3_onset_bank"
D1_KEY = "local_d1_bits"
SOURCE_KEYS = (L3_KEY, D1_KEY)
EXPECTED_SOURCES: dict[str, dict[str, Any]] = {
    L3_KEY: {
        "path": "C:/System_Trading/STOM/STOM_V.wt-alpha/docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/onset_l3_bank.parquet",
        "sha256": "0b6268e0eff8e73831539aba8ff83b8a02608405269732a33c78565c3bfa22fd",
        "size_bytes": 11741034,
        "rows": JOINED_ROWS,
    },
    D1_KEY: {
        "path": "docs/research/condition_research/research_runs/alpha_restart_20260710/stats_map/d1_onset_clause_bits.parquet",
        "sha256": "4df57b776bc1cb1ca7afc42e9eecd1b80c6fecbedd13e8379e017530a6600e56",
        "size_bytes": 6783855,
        "rows": JOINED_ROWS,
    },
}

L3_SCHEMA = (
    "code",
    "day",
    "off",
    "t0",
    "year",
    "updown_q",
    "mktcap_b",
    "time_b",
    "l3_net",
    "l3_labeled",
    "l3_clause",
    "l3_exit",
)
D1_SCHEMA = ("code", "day", "off", "t0") + tuple(f"bit_{number}" for number in range(1, 40))
D1_READ_COLUMNS = ("code", "day", "off", "t0", "bit_16", "bit_37", "bit_38")
ROW_KEYS = ("code", "day", "off", "t0", "year", "y", "b16", "b37", "b38")


def contract_constants(
    *,
    expected_sources: Mapping[str, Mapping[str, Any]] = EXPECTED_SOURCES,
    joined_rows: int = JOINED_ROWS,
    labeled_rows: int = LABELED_ROWS,
    pooled_cell_floor: int = POOLED_CELL_FLOOR,
    annual_cell_floor: int = ANNUAL_CELL_FLOOR,
    placebo_replicates: int = PLACEBO_REPLICATES,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    placebo_seed: int = PLACEBO_SEED,
    bootstrap_seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    """Return the sealed constants embedded in every G005-C1 input snapshot."""
    return {
        "input_schema": INPUT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "SEALED",
        "discovery_window": dict(DISCOVERY_WINDOW),
        "source_files": {
            key: {
                "path": str(expected_sources[key]["path"]),
                "sha256": str(expected_sources[key]["sha256"]),
                "size_bytes": int(expected_sources[key]["size_bytes"]),
                "rows": int(expected_sources[key]["rows"]),
            }
            for key in SOURCE_KEYS
        },
        "fixed_pairs": [[16, 37], [16, 38]],
        "outcome": {"column": "l3_net", "unit": "percentage_points"},
        "years": [2022, 2023],
        "sample_floors": {"joined_rows": int(joined_rows), "labeled_rows": int(labeled_rows)},
        "cell_floors": {
            "pooled_each_cell": int(pooled_cell_floor),
            "annual_each_cell": int(annual_cell_floor),
        },
        "placebo_rng": {
            "engine": "Python random.Random",
            "seed": int(placebo_seed),
            "replicates": int(placebo_replicates),
            "replicate_order": f"0..{int(placebo_replicates) - 1}",
            "group_order": "lexicographic by (str(code), int(day)) within each replicate",
            "row_order": "(off,t0)",
            "offset_call": "For each group n>=2 call rng.randrange(1,n) exactly once; groups n<2 make no RNG call; use the offset jointly for bits37 and bit38; no other RNG calls in the placebo offset path.",
        },
        "bootstrap_ci": {
            "engine": "Python random.Random",
            "seed": int(bootstrap_seed),
            "draws": int(bootstrap_draws),
            "strata": "annual whole-day clusters",
            "ci": "[Q(.025), Q(.975)] using nearest-rank quantiles",
        },
        "quantile_rule": "Nearest-rank quantiles: for sorted n values x, Q(p)=x[ceil(p*n)-1].",
        "multiplicity_family": "single G005-C1-TIME-SHIFT family; fixed pairs (16,37) and (16,38), conjunctive PASS with no pair rescue",
        "decision_precedence": "integrity/provenance/schema/join/floors/nonfinite/undefined-replicate => UNDETERMINED first; otherwise evaluate PASS then KILL",
        "undefined_replicate_rule": "If any placebo replicate or bootstrap draw lacks any required 4-cell finite mean, terminal UNDETERMINED before PASS/KILL; no replicate or draw may be dropped.",
        "one_shot": {"materializations": 1, "target_runs": 1, "retry": False},
        "forbidden_operations": [
            "engine_run",
            "database_write",
            "strategy_registration",
            "catalog_promotion",
            "post_2023_rows",
            "retry",
            "rescue",
        ],
    }


CONTRACT = contract_constants()


def _fail(message: str) -> None:
    raise ValueError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parquet_module() -> Any:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:  # pragma: no cover - environment contract
        raise ValueError("pyarrow is required for sealed parquet inputs") from exc
    return pq


def _arrow_schema_sha256(schema: Any) -> str:
    return hashlib.sha256(schema.serialize().to_pybytes()).hexdigest()


def _source_descriptor(path: Path, canonical_path: str, parquet_file: Any | None = None) -> dict[str, Any]:
    if not path.is_file():
        _fail(f"missing sealed source: {path}")
    sha256 = _sha256(path)
    size_bytes = path.stat().st_size
    pq = _parquet_module()
    parquet = parquet_file if parquet_file is not None else pq.ParquetFile(path)
    return {
        "path": canonical_path,
        "sha256": sha256,
        "size_bytes": size_bytes,
        "rows": parquet.metadata.num_rows,
        "row_groups": parquet.metadata.num_row_groups,
        "arrow_schema_sha256": _arrow_schema_sha256(parquet.schema_arrow),
        "arrow_schema": list(parquet.schema_arrow.names),
    }


def _expected_path(expected_sources: Mapping[str, Mapping[str, Any]], key: str) -> str:
    try:
        return str(expected_sources[key]["path"])
    except KeyError as exc:
        raise ValueError(f"missing expected source descriptor for {key}") from exc


def _validate_source_descriptor(actual: Mapping[str, Any], expected: Mapping[str, Any], key: str) -> None:
    for field in ("path", "sha256", "size_bytes", "rows"):
        if actual.get(field) != expected.get(field):
            _fail(f"{key} source drift: {field}={actual.get(field)!r}")
    for optional in ("row_groups", "arrow_schema_sha256", "arrow_schema"):
        if optional in expected and actual.get(optional) != expected.get(optional):
            _fail(f"{key} Arrow provenance drift: {optional}")


def _open_sources(
    l3_path: Path,
    d1_path: Path,
    expected_sources: Mapping[str, Mapping[str, Any]],
) -> tuple[Any, Any, dict[str, dict[str, Any]]]:
    before = {
        L3_KEY: _source_descriptor(l3_path, _expected_path(expected_sources, L3_KEY)),
        D1_KEY: _source_descriptor(d1_path, _expected_path(expected_sources, D1_KEY)),
    }
    pq = _parquet_module()
    l3_file = pq.ParquetFile(l3_path)
    d1_file = pq.ParquetFile(d1_path)
    for key in SOURCE_KEYS:
        _validate_source_descriptor(before[key], expected_sources[key], key)
    return l3_file, d1_file, before


def _validate_arrow_schema(parquet_file: Any, expected_names: tuple[str, ...], key: str) -> None:
    names = tuple(parquet_file.schema_arrow.names)
    if names != expected_names:
        _fail(f"{key} Arrow schema is not sealed")
    if parquet_file.metadata.num_row_groups < 1:
        _fail(f"{key} Arrow row groups are empty")


def _bit(value: Any, name: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return int(value)
    _fail(f"{name} must be a boolean/integer bit")


def _label(value: Any) -> bool:
    return bool(_bit(value, "l3_labeled"))


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        _fail(f"{name} must be finite")
    return float(value)


def _int_value(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        _fail(f"{name} must be an integer")
    return int(value)


def _day_value(value: Any) -> int:
    day = _int_value(value, "day")
    text = str(day)
    if len(text) != 8 or not text.isdigit():
        _fail("day must be a valid YYYYMMDD integer")
    try:
        dt.datetime.strptime(text, "%Y%m%d")
    except ValueError as exc:
        raise ValueError("day must be a valid YYYYMMDD integer") from exc
    return day


def _in_discovery_window(day: int) -> bool:
    return DISCOVERY_START_DAY <= day <= DISCOVERY_END_DAY


def _identity_string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"{name} must be a nonempty string")
    return value


def _key_columns(table: Any) -> list[tuple[str, int, int, str]]:
    values = {name: table.column(name).to_pylist() for name in ("code", "day", "off", "t0")}
    keys: list[tuple[str, int, int, str]] = []
    for code, day, off, t0 in zip(values["code"], values["day"], values["off"], values["t0"]):
        keys.append((
            _identity_string(code, "code"),
            _day_value(day),
            _int_value(off, "off"),
            _identity_string(t0, "t0"),
        ))
    return keys


def _unique_keys(keys: list[tuple[str, int, int, str]], label: str) -> None:
    if len(set(keys)) != len(keys):
        _fail(f"{label} contains duplicate (code,day,off,t0) keys")


def _joined_rows(l3_file: Any, d1_file: Any, expected_joined_rows: int) -> list[dict[str, Any]]:
    if l3_file.metadata.num_rows != expected_joined_rows or d1_file.metadata.num_rows != expected_joined_rows:
        _fail("source row metadata does not match the sealed joined row count")
    _validate_arrow_schema(l3_file, L3_SCHEMA, L3_KEY)
    _validate_arrow_schema(d1_file, D1_SCHEMA, D1_KEY)
    l3 = l3_file.read(columns=list(L3_SCHEMA))
    d1 = d1_file.read(columns=list(D1_READ_COLUMNS))
    l3_keys = _key_columns(l3)
    d1_keys = _key_columns(d1)
    _unique_keys(l3_keys, L3_KEY)
    _unique_keys(d1_keys, D1_KEY)
    if set(l3_keys) != set(d1_keys):
        _fail("L3/D1 exact 1:1 identity join failed")

    d1_columns = {name: d1.column(name).to_pylist() for name in D1_READ_COLUMNS}
    d1_by_key: dict[tuple[str, int, int, str], tuple[int, int, int]] = {}
    for index, key in enumerate(d1_keys):
        d1_by_key[key] = (
            _bit(d1_columns["bit_16"][index], "bit_16"),
            _bit(d1_columns["bit_37"][index], "bit_37"),
            _bit(d1_columns["bit_38"][index], "bit_38"),
        )

    l3_columns = {name: l3.column(name).to_pylist() for name in L3_SCHEMA}
    rows: list[dict[str, Any]] = []
    for index, key in enumerate(l3_keys):
        code, day, off, t0 = key
        year = _int_value(l3_columns["year"][index], "year")
        if year != int(str(day)[:4]):
            _fail("year and day disagree")
        labeled = _label(l3_columns["l3_labeled"][index])
        if year not in YEARS or not _in_discovery_window(day) or not labeled:
            continue
        b16, b37, b38 = d1_by_key[key]
        rows.append(
            {
                "code": code,
                "day": day,
                "off": off,
                "t0": t0,
                "year": year,
                "y": _finite(l3_columns["l3_net"][index], "l3_net"),
                "b16": b16,
                "b37": b37,
                "b38": b38,
            }
        )
    rows.sort(key=lambda row: (row["code"], int(row["day"]), int(row["off"]), row["t0"]))
    return rows


def _row_flow(rows: list[Mapping[str, Any]], expected_joined_rows: int, expected_labeled_rows: int) -> dict[str, Any]:
    if len(rows) != expected_labeled_rows:
        _fail("eligible labeled row count is not sealed")
    by_year = {str(year): sum(1 for row in rows if row["year"] == year) for year in YEARS}
    if any(count <= 0 for count in by_year.values()):
        _fail("eligible rows must contain both sealed years 2022 and 2023")
    return {
        "joined_rows": int(expected_joined_rows),
        "labeled_rows": len(rows),
        "eligible_years": [2022, 2023],
        "eligible_by_year": by_year,
        "unlabeled_or_out_of_window_rows": int(expected_joined_rows) - len(rows),
    }


def _post_sources(
    l3_path: Path,
    d1_path: Path,
    l3_file: Any,
    d1_file: Any,
    expected_sources: Mapping[str, Mapping[str, Any]],
    before: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    after = {
        L3_KEY: _source_descriptor(l3_path, _expected_path(expected_sources, L3_KEY), l3_file),
        D1_KEY: _source_descriptor(d1_path, _expected_path(expected_sources, D1_KEY), d1_file),
    }
    for key in SOURCE_KEYS:
        _validate_source_descriptor(after[key], expected_sources[key], key)
        if after[key] != before[key]:
            _fail(f"{key} source drifted during sealed read")
    return {key: {"pre": dict(before[key]), "post": dict(after[key])} for key in SOURCE_KEYS}


def build_snapshot(
    l3_path: Path,
    d1_path: Path,
    *,
    expected_sources: Mapping[str, Mapping[str, Any]] = EXPECTED_SOURCES,
    expected_joined_rows: int = JOINED_ROWS,
    expected_labeled_rows: int = LABELED_ROWS,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a G005-C1 input snapshot from explicit paths without writing it."""
    l3_file, d1_file, before = _open_sources(l3_path, d1_path, expected_sources)
    rows = _joined_rows(l3_file, d1_file, expected_joined_rows)
    sources = _post_sources(l3_path, d1_path, l3_file, d1_file, expected_sources, before)
    flow = _row_flow(rows, expected_joined_rows, expected_labeled_rows)
    return {
        "schema": INPUT_SCHEMA,
        "contract": dict(contract if contract is not None else CONTRACT),
        "sources": sources,
        "row_flow": flow,
        "eligible_rows": rows,
    }


def _canonical_json_text(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_snapshot(snapshot: Mapping[str, Any], output_path: Path) -> None:
    """Write deterministic plain UTF-8 JSON exclusively; existing outputs are sealed failures."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json_text(snapshot)
    with output_path.open("x", encoding="utf-8") as handle:
        handle.write(payload)


def materialize(
    l3_path: Path = L3_SOURCE_PATH,
    d1_path: Path = D1_SOURCE_PATH,
    output_path: Path = OUTPUT_PATH,
    *,
    expected_sources: Mapping[str, Mapping[str, Any]] = EXPECTED_SOURCES,
    expected_joined_rows: int = JOINED_ROWS,
    expected_labeled_rows: int = LABELED_ROWS,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build and exclusively write the one sealed production input snapshot."""
    if output_path.exists():
        _fail(f"sealed output already exists: {output_path}")
    snapshot = build_snapshot(
        l3_path,
        d1_path,
        expected_sources=expected_sources,
        expected_joined_rows=expected_joined_rows,
        expected_labeled_rows=expected_labeled_rows,
        contract=contract,
    )
    write_snapshot(snapshot, output_path)
    return snapshot


def main() -> None:
    snapshot = materialize()
    receipt = {"schema": INPUT_SCHEMA, "output": OUTPUT_PATH.as_posix(), "row_flow": snapshot["row_flow"]}
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
