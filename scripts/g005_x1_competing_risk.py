"""Measure the sealed G005-X1 exit competing-risk descriptive contract."""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "g005-x1-input-v1"
RESULT_SCHEMA = "g005-x1-competing-risk-result-v1"
HYPOTHESIS_ID = "G005-X1-EXIT-COMPETING-RISK"
PREREGISTRATION_PATH = "docs/research/condition_research/plans/2026-07-16_g005_x1_competing_risk_preregistration.md"
INPUT_PATH = "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
YEARS = (2022, 2023)
GROUPS = ("RR8", "GPTAUTH_G8")
CAUSES = ("forced_cap", "stop_loss", "trailing", "time_exit", "profit_take", "other")
REQUIRED_ROW_KEYS = frozenset(("group", "slot", "day", "buy_time", "sell_time", "condition", "y"))
EXPECTED_FILTERED_COUNTS = MappingProxyType({2022: 510, 2023: 1148})
BOOTSTRAP_SEED = 2026071603
BOOTSTRAP_DRAWS = 20000
RATIO_KILL_THRESHOLD = 0.8
CAVEAT = (
    "Descriptive not causal: exit-cause labels are observed text/time classifications only; "
    "no counterfactual exit adoption, strategy registration, promotion, engine execution, or DB write is authorized."
)
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

    def identity(self) -> dict[str, Any]:
        return {"sha256": self.sha256, "size_bytes": self.size_bytes, "raw_rows": self.raw_rows}


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


class X1MeasureError(ValueError):
    """The sealed X1 measurement input failed integrity validation."""


def _fail(message: str) -> None:
    raise X1MeasureError(message)


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
        _fail("at least one source descriptor is required")
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
        "required_fields": ["매수시간", "매도시간", "매도조건", "수익률"],
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


def _timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or len(value) != 14 or not value.isdigit():
        _fail(f"invalid {field}: {value!r}")
    try:
        datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError as exc:
        _fail(f"invalid {field}: {value!r}: {exc}")
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"invalid finite numeric {field}: {value!r}")
    parsed = float(value)
    if not math.isfinite(parsed):
        _fail(f"non-finite {field}: {value!r}")
    return parsed


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


def validate_snapshot(
    snapshot: Mapping[str, Any],
    *,
    source_files: Iterable[SourceSpec | Mapping[str, Any]] = SOURCE_FILES,
    expected_counts: Mapping[int | str, int] = EXPECTED_FILTERED_COUNTS,
) -> list[dict[str, Any]]:
    sources = _coerce_sources(source_files)
    expected = _coerce_expected_counts(expected_counts)
    if not isinstance(snapshot, Mapping):
        _fail("snapshot must be a JSON object")
    if snapshot.get("schema") != SCHEMA:
        _fail(f"snapshot schema mismatch: {snapshot.get('schema')!r}")
    if snapshot.get("contract") != contract_descriptor(sources, expected):
        _fail("contract descriptor mismatch")
    source_records = snapshot.get("sources")
    if not isinstance(source_records, list) or len(source_records) != len(sources):
        _fail("source descriptor count mismatch")
    for record, source in zip(source_records, sources):
        if not isinstance(record, Mapping):
            _fail("source record must be an object")
        descriptor = source.descriptor()
        if set(record) != set(descriptor) | {"pre", "post"}:
            _fail(f"source record has unexpected keys for {source.slot}")
        for key, value in descriptor.items():
            if record.get(key) != value:
                _fail(f"source descriptor mismatch for {source.slot}.{key}")
        if record.get("pre") != source.identity() or record.get("post") != source.identity():
            _fail(f"source pre/post identity mismatch for {source.slot}")
    slot_group = {source.slot: source.group for source in sources}
    raw_rows = snapshot.get("rows")
    if not isinstance(raw_rows, list):
        _fail("rows must be a list")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw_rows):
        if not isinstance(row, Mapping) or set(row) != REQUIRED_ROW_KEYS:
            _fail(f"row {index} must contain exactly {sorted(REQUIRED_ROW_KEYS)}")
        slot = row["slot"]
        group = row["group"]
        if slot not in slot_group or group != slot_group[slot]:
            _fail(f"row {index} slot/group mismatch: {slot!r} {group!r}")
        if group not in GROUPS:
            _fail(f"row {index} invalid group: {group!r}")
        day = row["day"]
        if not isinstance(day, str) or len(day) != 8 or not day.isdigit():
            _fail(f"row {index} invalid day: {day!r}")
        year = int(day[:4])
        if year not in YEARS:
            _fail(f"row {index} forbidden year: {year}")
        buy_time = _timestamp(row["buy_time"], "buy_time")
        sell_time = _timestamp(row["sell_time"], "sell_time")
        if buy_time[:8] != day or sell_time[:8] != day:
            _fail(f"row {index} buy/sell/day mismatch")
        condition = row["condition"]
        if not isinstance(condition, str):
            _fail(f"row {index} condition must be a raw string")
        rows.append(
            {
                "group": str(group),
                "slot": str(slot),
                "day": day,
                "buy_time": buy_time,
                "sell_time": sell_time,
                "condition": condition,
                "y": _finite_number(row["y"], "y"),
            }
        )
    counts = _count_record(rows, sources, expected)
    if counts != snapshot.get("counts"):
        _fail("count descriptor mismatch")
    if counts["by_year"] != _json_year_counts(expected) or counts["total"] != sum(expected.values()):
        _fail("filtered count mismatch")
    side_effect_counters = snapshot.get("side_effect_counters")
    if side_effect_counters is not None and side_effect_counters != dict(ZERO_SIDE_EFFECT_COUNTERS):
        _fail("prohibited side-effect counter is non-zero or malformed")
    return rows


def classify_cause(sell_time: str, condition: str) -> str:
    if sell_time[-6:] >= "093000" or "강제" in condition or "마감" in condition:
        return "forced_cap"
    if "손절" in condition or "최저가이탈" in condition:
        return "stop_loss"
    if "트레일링" in condition or "최고수익률" in condition:
        return "trailing"
    if "보유시간" in condition:
        return "time_exit"
    if "익절" in condition:
        return "profit_take"
    return "other"


def _mean(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return float(sum(values) / len(values))


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _rows_by_group(rows: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped = {group: [] for group in GROUPS}
    for row in rows:
        enriched = dict(row)
        enriched["cause"] = classify_cause(str(row["sell_time"]), str(row["condition"]))
        grouped[str(row["group"])].append(enriched)
    return grouped


def compute_statistics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped = _rows_by_group(rows)
    undefined: list[str] = []
    group_means: dict[str, float | None] = {}
    for group in GROUPS:
        mean = _mean([float(row["y"]) for row in grouped[group]])
        group_means[group] = mean
        if mean is None:
            undefined.append(f"missing_group_{group}")
    raw_contrast = None
    if group_means["RR8"] is not None and group_means["GPTAUTH_G8"] is not None:
        raw_contrast = float(group_means["RR8"] - group_means["GPTAUTH_G8"])
    cause_table: dict[str, dict[str, dict[str, Any]]] = {group: {} for group in GROUPS}
    cause_counts = {group: {cause: 0 for cause in CAUSES} for group in GROUPS}
    cause_values = {group: {cause: [] for cause in CAUSES} for group in GROUPS}
    for group in GROUPS:
        for row in grouped[group]:
            cause = row["cause"]
            cause_counts[group][cause] += 1
            cause_values[group][cause].append(float(row["y"]))
    for group in GROUPS:
        denominator = len(grouped[group])
        for cause in CAUSES:
            n = cause_counts[group][cause]
            conditional = _mean(cause_values[group][cause])
            incidence = (n / denominator) if denominator else None
            contribution = (incidence * conditional) if incidence is not None and conditional is not None else None
            cause_table[group][cause] = {
                "n": n,
                "incidence": incidence,
                "conditional_mean": conditional,
                "raw_contribution": contribution,
            }
    total_rows = sum(len(grouped[group]) for group in GROUPS)
    pooled_weights: dict[str, float] = {}
    missing_support: list[str] = []
    for cause in CAUSES:
        pooled_n = sum(cause_counts[group][cause] for group in GROUPS)
        weight = pooled_n / total_rows if total_rows else 0.0
        pooled_weights[cause] = weight
        if weight > 0 and any(cause_counts[group][cause] == 0 for group in GROUPS):
            missing_support.append(cause)
    if missing_support:
        undefined.append("missing_positive_weight_cause_support:" + ",".join(missing_support))
    for group in GROUPS:
        for cause in CAUSES:
            conditional = cause_table[group][cause]["conditional_mean"]
            cause_table[group][cause]["pooled_standardized_contribution"] = (
                pooled_weights[cause] * conditional if conditional is not None else None
            )
    standardized_group_means: dict[str, float | None] = {group: None for group in GROUPS}
    standardized_contrast = None
    residual_ratio = None
    if not missing_support and total_rows:
        for group in GROUPS:
            standardized_group_means[group] = float(
                sum(pooled_weights[cause] * cause_table[group][cause]["conditional_mean"] for cause in CAUSES if pooled_weights[cause] > 0)
            )
        standardized_contrast = float(standardized_group_means["RR8"] - standardized_group_means["GPTAUTH_G8"])
    if raw_contrast == 0:
        undefined.append("raw_contrast_zero")
    if raw_contrast not in (None, 0) and standardized_contrast is not None:
        residual_ratio = abs(float(standardized_contrast / raw_contrast))
    annual_raw_contrasts: dict[str, float | None] = {}
    annual_signs: dict[str, int | None] = {}
    for year in YEARS:
        year_values = {
            group: [float(row["y"]) for row in grouped[group] if str(row["day"]).startswith(str(year))]
            for group in GROUPS
        }
        left = _mean(year_values["RR8"])
        right = _mean(year_values["GPTAUTH_G8"])
        contrast = None if left is None or right is None else float(left - right)
        annual_raw_contrasts[str(year)] = contrast
        annual_signs[str(year)] = None if contrast is None else _sign(contrast)
        if contrast is None:
            undefined.append(f"annual_raw_contrast_missing:{year}")
        elif contrast == 0:
            undefined.append(f"annual_raw_contrast_zero:{year}")
    sign_values = [annual_signs[str(year)] for year in YEARS]
    annual_sign_conflict = None not in sign_values and 0 not in sign_values and len(set(sign_values)) > 1
    return {
        "undefined_reasons": undefined,
        "raw_group_means": group_means,
        "raw_contrast": raw_contrast,
        "cause_table": cause_table,
        "pooled_weights": pooled_weights,
        "standardized_group_means": standardized_group_means,
        "standardized_contrast": standardized_contrast,
        "residual_ratio": residual_ratio,
        "annual_raw_contrasts": annual_raw_contrasts,
        "annual_signs": annual_signs,
        "annual_sign_conflict": annual_sign_conflict,
    }


def _day_blocks(rows: Sequence[Mapping[str, Any]]) -> dict[int, list[list[Mapping[str, Any]]]]:
    by_year_day: dict[int, dict[str, list[Mapping[str, Any]]]] = {year: {} for year in YEARS}
    for row in rows:
        year = int(str(row["day"])[:4])
        by_year_day[year].setdefault(str(row["day"]), []).append(row)
    return {year: [by_year_day[year][day] for day in sorted(by_year_day[year])] for year in YEARS}


def _draw_replicate(
    blocks: Mapping[int, Sequence[Sequence[Mapping[str, Any]]]],
    rng: random.Random,
    plan: Mapping[int | str, Sequence[int]] | None = None,
) -> list[Mapping[str, Any]]:
    sampled: list[Mapping[str, Any]] = []
    for year in YEARS:
        year_blocks = list(blocks.get(year, ()))
        if not year_blocks:
            _fail(f"bootstrap has no blocks for {year}")
        if plan is None:
            indices = [rng.randrange(len(year_blocks)) for _ in range(len(year_blocks))]
        else:
            raw_indices = plan.get(year, plan.get(str(year), ()))
            indices = [int(index) for index in raw_indices]
            if len(indices) != len(year_blocks):
                _fail(f"bootstrap plan for {year} must draw {len(year_blocks)} day blocks")
            if any(index < 0 or index >= len(year_blocks) for index in indices):
                _fail(f"bootstrap plan index out of range for {year}: {indices!r}")
        for index in indices:
            sampled.extend(year_blocks[index])
    return sampled


def _nearest_rank_ci(values: Sequence[float]) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        _fail("bootstrap CI requires at least one value")
    n = len(ordered)
    return [ordered[max(0, math.ceil(0.025 * n) - 1)], ordered[max(0, math.ceil(0.975 * n) - 1)]]


def bootstrap_intervals(
    rows: Sequence[Mapping[str, Any]],
    *,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
    plan: Sequence[Mapping[int | str, Sequence[int]]] | None = None,
) -> tuple[dict[str, list[float]] | None, list[str]]:
    if plan is not None:
        draws = len(plan)
    if draws <= 0:
        _fail("bootstrap draws must be positive")
    blocks = _day_blocks(rows)
    rng = random.Random(seed)
    raw_values: list[float] = []
    standardized_values: list[float] = []
    ratio_values: list[float] = []
    for replicate in range(draws):
        sample = _draw_replicate(blocks, rng, None if plan is None else plan[replicate])
        stats = compute_statistics(sample)
        if stats["undefined_reasons"]:
            return None, [f"bootstrap_undefined_replicate:{replicate}:" + ";".join(stats["undefined_reasons"])]
        raw_values.append(float(stats["raw_contrast"]))
        standardized_values.append(float(stats["standardized_contrast"]))
        ratio_values.append(float(stats["residual_ratio"]))
    return {
        "raw_contrast": _nearest_rank_ci(raw_values),
        "standardized_contrast": _nearest_rank_ci(standardized_values),
        "residual_ratio": _nearest_rank_ci(ratio_values),
    }, []


def _result(decision: str, *, stats: Mapping[str, Any] | None, bootstrap_ci: Mapping[str, Any] | None, undetermined: list[str], kill: list[str]) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "decision": decision,
        "caveat": CAVEAT,
        "statistics": stats,
        "bootstrap_ci": bootstrap_ci,
        "decision_diagnostics": {
            "undetermined_reasons": undetermined,
            "kill_reasons": kill,
            "pass_rule": "pooled residual_ratio < 0.8 and 2022/2023 annual raw signs agree nonzero",
            "decision_precedence": ["UNDETERMINED", "KILL", "PASS"],
        },
        "side_effect_counters": dict(ZERO_SIDE_EFFECT_COUNTERS),
    }


def measure(
    snapshot: Mapping[str, Any],
    *,
    source_files: Iterable[SourceSpec | Mapping[str, Any]] = SOURCE_FILES,
    expected_counts: Mapping[int | str, int] = EXPECTED_FILTERED_COUNTS,
    bootstrap_draws: int = BOOTSTRAP_DRAWS,
    bootstrap_seed: int = BOOTSTRAP_SEED,
    bootstrap_plan: Sequence[Mapping[int | str, Sequence[int]]] | None = None,
) -> dict[str, Any]:
    try:
        rows = validate_snapshot(snapshot, source_files=source_files, expected_counts=expected_counts)
    except X1MeasureError as exc:
        return _result("UNDETERMINED", stats=None, bootstrap_ci=None, undetermined=["integrity_issue:" + str(exc)], kill=[])
    stats = compute_statistics(rows)
    if stats["undefined_reasons"]:
        return _result("UNDETERMINED", stats=stats, bootstrap_ci=None, undetermined=list(stats["undefined_reasons"]), kill=[])
    try:
        bootstrap_ci, bootstrap_errors = bootstrap_intervals(rows, draws=bootstrap_draws, seed=bootstrap_seed, plan=bootstrap_plan)
    except X1MeasureError as exc:
        return _result("UNDETERMINED", stats=stats, bootstrap_ci=None, undetermined=["bootstrap_integrity_issue:" + str(exc)], kill=[])
    if bootstrap_errors:
        return _result("UNDETERMINED", stats=stats, bootstrap_ci=None, undetermined=bootstrap_errors, kill=[])
    kill: list[str] = []
    if float(stats["residual_ratio"]) >= RATIO_KILL_THRESHOLD:
        kill.append("residual_ratio_ge_0.8")
    if stats["annual_sign_conflict"]:
        kill.append("annual_sign_conflict")
    if kill:
        return _result("KILL", stats=stats, bootstrap_ci=bootstrap_ci, undetermined=[], kill=kill)
    return _result("PASS", stats=stats, bootstrap_ci=bootstrap_ci, undetermined=[], kill=[])


if __name__ == "__main__":
    with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json", encoding="utf-8") as handle:
        print(json.dumps(measure(json.load(handle)), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
