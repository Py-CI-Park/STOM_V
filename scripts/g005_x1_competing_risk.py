"""Measure the sealed G005-X1 exit competing-risk descriptive contract."""
import json


SCHEMA = "g005-x1-input-v1"
RESULT_SCHEMA = "g005-x1-competing-risk-result-v1"
HYPOTHESIS_ID = "G005-X1-EXIT-COMPETING-RISK"
PREREGISTRATION_PATH = "docs/research/condition_research/plans/2026-07-16_g005_x1_competing_risk_preregistration.md"
INPUT_PATH = "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json"
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"
YEARS = (2022, 2023)
GROUPS = ("RR8", "GPTAUTH_G8")
CAUSES = ("forced_cap", "stop_loss", "trailing", "time_exit", "profit_take", "other")
REQUIRED_ROW_KEYS = ("group", "slot", "day", "buy_time", "sell_time", "condition", "y")
EXPECTED_FILTERED_COUNTS = ((2022, 510), (2023, 1148))
BOOTSTRAP_SEED = 2026071603
BOOTSTRAP_DRAWS = 20000
RATIO_KILL_THRESHOLD = 0.8
CAVEAT = (
    "Descriptive not causal: exit-cause labels are observed text/time classifications only; "
    "no counterfactual exit adoption, strategy registration, promotion, engine execution, or DB write is authorized."
)
ZERO_SIDE_EFFECT_COUNTERS = (
    ("engine_calls", 0),
    ("db_writes", 0),
    ("strategy_registrations", 0),
    ("promotions", 0),
    ("retries", 0),
    ("rescue_runs", 0),
)


def SourceSpec(slot, group, path, sha256, size_bytes, raw_rows, encoding="utf-8"):
    return (
        ("slot", str(slot)),
        ("group", str(group)),
        ("path", str(path)),
        ("encoding", str(encoding)),
        ("sha256", str(sha256)),
        ("size_bytes", int(size_bytes)),
        ("raw_rows", int(raw_rows)),
    )


def _source_values(source):
    return source if isinstance(source, dict) else dict(source)


def _source_value(source, key):
    values = _source_values(source)
    return values[key]


def _source_descriptor(source):
    return {
        "slot": _source_value(source, "slot"),
        "group": _source_value(source, "group"),
        "path": _source_value(source, "path"),
        "encoding": _source_value(source, "encoding"),
        "sha256": _source_value(source, "sha256"),
        "size_bytes": _source_value(source, "size_bytes"),
        "raw_rows": _source_value(source, "raw_rows"),
    }


def _source_identity(source):
    return {
        "sha256": _source_value(source, "sha256"),
        "size_bytes": _source_value(source, "size_bytes"),
        "raw_rows": _source_value(source, "raw_rows"),
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


class X1MeasureError(Exception):
    """Intentional sealed X1 input/integrity failure."""


def _x1_error_text(self):
    return type(self).__name__


def _fail(message):
    raise type(str(message), (X1MeasureError,), {"__str__": _x1_error_text})


def _coerce_source_spec(value):
    required = {"slot", "group", "path", "sha256", "size_bytes", "raw_rows"}
    values = _source_values(value)
    if not required <= set(values):
        _fail(f"malformed source descriptor: {value!r}")
    return SourceSpec(
        slot=values["slot"],
        group=values["group"],
        path=values["path"],
        encoding=values["encoding"] if "encoding" in values else "utf-8",
        sha256=values["sha256"],
        size_bytes=values["size_bytes"],
        raw_rows=values["raw_rows"],
    )


def _coerce_sources(source_files):
    sources = tuple(_coerce_source_spec(item) for item in source_files)
    if not sources:
        _fail("at least one source descriptor is required")
    slots = [_source_value(source, "slot") for source in sources]
    if len(set(slots)) != len(slots):
        _fail("source slots must be unique")
    return sources


def _coerce_expected_count_item(key, value):
    year = int(key)
    if year not in YEARS:
        _fail(f"unexpected filtered year: {year}")
    count = int(value)
    if count < 0:
        _fail(f"negative filtered count for {year}: {count}")
    return year, count


def _coerce_expected_counts(expected_counts):
    raw_items = (
        tuple((key, expected_counts[key]) for key in expected_counts)
        if isinstance(expected_counts, dict)
        else tuple(expected_counts)
    )
    items = tuple(_coerce_expected_count_item(item[0], item[1]) for item in raw_items)
    counts = {year: count for year, count in items}
    if set(counts) != set(YEARS):
        _fail(f"expected counts must cover exactly {YEARS}")
    return counts


def _json_year_counts(counts):
    return {str(year): int(counts[year]) for year in YEARS}


def _expected_count_record(expected_counts):
    by_year = _json_year_counts(expected_counts)
    return {**by_year, "total": sum(int(expected_counts[year]) for year in YEARS)}


def contract_descriptor(
    source_files=SOURCE_FILES,
    expected_counts=EXPECTED_FILTERED_COUNTS,
):
    sources = _coerce_sources(source_files)
    counts = _coerce_expected_counts(expected_counts)
    return {
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "SEALED",
        "claim_type": "descriptive_not_causal",
        "source_preregistration": PREREGISTRATION_PATH,
        "discovery_window": {"start": "2022-03-23", "end": "2023-12-31"},
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
        "source_files": [_source_descriptor(source) for source in sources],
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


def _is_leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_month(year, month):
    if month == 2:
        return 29 if _is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def _valid_timestamp(value):
    if not isinstance(value, str) or len(value) != 14 or not all(char in "0123456789" for char in value):
        return False
    year = int(value[:4])
    month = int(value[4:6])
    day = int(value[6:8])
    hour = int(value[8:10])
    minute = int(value[10:12])
    second = int(value[12:14])
    return (
        1 <= month <= 12
        and 1 <= day <= _days_in_month(year, month)
        and 0 <= hour <= 23
        and 0 <= minute <= 59
        and 0 <= second <= 59
    )


def _timestamp(value, field):
    if not _valid_timestamp(value):
        _fail(f"invalid {field}: {value!r}")
    return value


def _finite_number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"invalid finite numeric {field}: {value!r}")
    parsed = float(value)
    if parsed != parsed or parsed == float("inf") or parsed == float("-inf"):
        _fail(f"non-finite {field}: {value!r}")
    return parsed


def _count_record(
    rows,
    source_files,
    expected_counts,
):
    sources = _coerce_sources(source_files)
    row_records = tuple(
        (str(row["day"])[:4], str(row["group"]), str(row["slot"]))
        for row in rows
    )
    by_year = {
        str(year): sum(1 for row_year, _, _ in row_records if row_year == str(year))
        for year in YEARS
    }
    groups = sorted({group for _, group, _ in row_records})
    by_group = {
        group: sum(1 for _, row_group, _ in row_records if row_group == group)
        for group in groups
    }
    by_group_year = {
        group: {
            str(year): sum(
                1
                for row_year, row_group, _ in row_records
                if row_year == str(year) and row_group == group
            )
            for year in YEARS
        }
        for group in groups
    }
    by_slot = {
        _source_value(source, "slot"): sum(
            1 for _, _, slot in row_records if slot == _source_value(source, "slot")
        )
        for source in sources
    }
    return {
        "expected": _expected_count_record(expected_counts),
        "by_year": by_year,
        "total": sum(by_year[str(year)] for year in YEARS),
        "by_group": by_group,
        "by_group_year": by_group_year,
        "by_slot": by_slot,
    }


def _validated_snapshot_row(index, row, slot_group):
    if not isinstance(row, dict) or set(row) != set(REQUIRED_ROW_KEYS):
        _fail(f"row {index} must contain exactly {sorted(REQUIRED_ROW_KEYS)}")
    slot = row["slot"]
    group = row["group"]
    if slot not in slot_group or group != slot_group[slot]:
        _fail(f"row {index} slot/group mismatch: {slot!r} {group!r}")
    if group not in GROUPS:
        _fail(f"row {index} invalid group: {group!r}")
    day = row["day"]
    if not isinstance(day, str) or len(day) != 8 or not all(char in "0123456789" for char in day):
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
    return {
        "group": str(group),
        "slot": str(slot),
        "day": day,
        "buy_time": buy_time,
        "sell_time": sell_time,
        "condition": condition,
        "y": _finite_number(row["y"], "y"),
    }


def validate_snapshot(
    snapshot,
    *,
    source_files=SOURCE_FILES,
    expected_counts=EXPECTED_FILTERED_COUNTS,
):
    sources = _coerce_sources(source_files)
    expected = _coerce_expected_counts(expected_counts)
    if not isinstance(snapshot, dict):
        _fail("snapshot must be a JSON object")
    schema = snapshot["schema"] if "schema" in snapshot else None
    if schema != SCHEMA:
        _fail(f"snapshot schema mismatch: {schema!r}")
    contract = snapshot["contract"] if "contract" in snapshot else None
    if contract != contract_descriptor(sources, expected):
        _fail("contract descriptor mismatch")
    source_records = snapshot["sources"] if "sources" in snapshot else None
    if not isinstance(source_records, list) or len(source_records) != len(sources):
        _fail("source descriptor count mismatch")
    for record, source in zip(source_records, sources):
        if not isinstance(record, dict):
            _fail("source record must be an object")
        descriptor = _source_descriptor(source)
        if set(record) != set(descriptor) | {"pre", "post"}:
            _fail(f"source record has unexpected keys for {_source_value(source, 'slot')}")
        for key in descriptor:
            if (record[key] if key in record else None) != descriptor[key]:
                _fail(f"source descriptor mismatch for {_source_value(source, 'slot')}.{key}")
        pre_identity = record["pre"] if "pre" in record else None
        post_identity = record["post"] if "post" in record else None
        if pre_identity != _source_identity(source) or post_identity != _source_identity(source):
            _fail(f"source pre/post identity mismatch for {_source_value(source, 'slot')}")
    slot_group = {_source_value(source, "slot"): _source_value(source, "group") for source in sources}
    raw_rows = snapshot["rows"] if "rows" in snapshot else None
    if not isinstance(raw_rows, list):
        _fail("rows must be a list")
    rows = [
        _validated_snapshot_row(index, row, slot_group)
        for index, row in enumerate(raw_rows)
    ]
    counts = _count_record(rows, sources, expected)
    if counts != (snapshot["counts"] if "counts" in snapshot else None):
        _fail("count descriptor mismatch")
    if counts["by_year"] != _json_year_counts(expected) or counts["total"] != sum(expected[year] for year in YEARS):
        _fail("filtered count mismatch")
    side_effect_counters = snapshot["side_effect_counters"] if "side_effect_counters" in snapshot else None
    if side_effect_counters != dict(ZERO_SIDE_EFFECT_COUNTERS):
        _fail("missing or nonzero side-effect counters")
    return rows


def classify_cause(sell_time, condition):
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


def _mean(values):
    if not values:
        return None
    return float(sum(values) / len(values))


def _sign(value):
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _join_text(separator, values):
    text = ""
    for index, value in enumerate(values):
        text = text + (separator if index else "") + str(value)
    return text


def _rows_by_group(rows):
    enriched_rows = tuple(
        {
            **row,
            "cause": classify_cause(str(row["sell_time"]), str(row["condition"])),
        }
        for row in rows
    )
    return {
        group: [row for row in enriched_rows if str(row["group"]) == group]
        for group in GROUPS
    }


def _cause_record(grouped, cause_counts, group, cause):
    values = [float(row["y"]) for row in grouped[group] if row["cause"] == cause]
    n = cause_counts[group][cause]
    denominator = len(grouped[group])
    conditional = _mean(values)
    incidence = (n / denominator) if denominator else None
    contribution = (incidence * conditional) if incidence is not None and conditional is not None else None
    return {
        "n": n,
        "incidence": incidence,
        "conditional_mean": conditional,
        "raw_contribution": contribution,
    }


def _annual_raw_contrast(grouped, year):
    year_values = {
        group: [
            float(row["y"])
            for row in grouped[group]
            if str(row["day"])[:4] == str(year)
        ]
        for group in GROUPS
    }
    left = _mean(year_values["RR8"])
    right = _mean(year_values["GPTAUTH_G8"])
    return None if left is None or right is None else float(left - right)


def compute_statistics(rows):
    grouped = _rows_by_group(rows)
    group_means = {
        group: _mean([float(row["y"]) for row in grouped[group]])
        for group in GROUPS
    }
    missing_group_reasons = [
        f"missing_group_{group}"
        for group in GROUPS
        if group_means[group] is None
    ]
    raw_contrast = None
    if group_means["RR8"] is not None and group_means["GPTAUTH_G8"] is not None:
        raw_contrast = float(group_means["RR8"] - group_means["GPTAUTH_G8"])
    cause_counts = {
        group: {
            cause: sum(1 for row in grouped[group] if row["cause"] == cause)
            for cause in CAUSES
        }
        for group in GROUPS
    }
    cause_table_without_standardized = {
        group: {
            cause: _cause_record(grouped, cause_counts, group, cause)
            for cause in CAUSES
        }
        for group in GROUPS
    }
    total_rows = sum(len(grouped[group]) for group in GROUPS)
    pooled_weights = {
        cause: (
            sum(cause_counts[group][cause] for group in GROUPS) / total_rows
            if total_rows
            else 0.0
        )
        for cause in CAUSES
    }
    missing_support = [
        cause
        for cause in CAUSES
        if pooled_weights[cause] > 0 and any(cause_counts[group][cause] == 0 for group in GROUPS)
    ]
    support_reasons = (
        ["missing_positive_weight_cause_support:" + _join_text(",", missing_support)]
        if missing_support
        else []
    )
    cause_table = {
        group: {
            cause: {
                **cause_table_without_standardized[group][cause],
                "pooled_standardized_contribution": (
                    pooled_weights[cause] * cause_table_without_standardized[group][cause]["conditional_mean"]
                    if cause_table_without_standardized[group][cause]["conditional_mean"] is not None
                    else None
                ),
            }
            for cause in CAUSES
        }
        for group in GROUPS
    }
    standardized_group_means = (
        {
            group: float(
                sum(
                    pooled_weights[cause] * cause_table_without_standardized[group][cause]["conditional_mean"]
                    for cause in CAUSES
                    if pooled_weights[cause] > 0
                )
            )
            for group in GROUPS
        }
        if not missing_support and total_rows
        else {group: None for group in GROUPS}
    )
    standardized_contrast = (
        float(standardized_group_means["RR8"] - standardized_group_means["GPTAUTH_G8"])
        if not missing_support and total_rows
        else None
    )
    raw_contrast_reasons = ["raw_contrast_zero"] if raw_contrast == 0 else []
    residual_ratio = (
        abs(float(standardized_contrast / raw_contrast))
        if raw_contrast not in (None, 0) and standardized_contrast is not None
        else None
    )
    annual_raw_contrasts = {
        str(year): _annual_raw_contrast(grouped, year)
        for year in YEARS
    }
    annual_signs = {
        str(year): (
            None
            if annual_raw_contrasts[str(year)] is None
            else _sign(annual_raw_contrasts[str(year)])
        )
        for year in YEARS
    }
    annual_reasons = [
        reason
        for year in YEARS
        for reason in (
            [f"annual_raw_contrast_missing:{year}"]
            if annual_raw_contrasts[str(year)] is None
            else (
                [f"annual_raw_contrast_zero:{year}"]
                if annual_raw_contrasts[str(year)] == 0
                else []
            )
        )
    ]
    sign_values = [annual_signs[str(year)] for year in YEARS]
    annual_sign_conflict = None not in sign_values and 0 not in sign_values and len(set(sign_values)) > 1
    return {
        "undefined_reasons": (
            missing_group_reasons + support_reasons + raw_contrast_reasons + annual_reasons
        ),
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


def _day_blocks(rows):
    days_by_year = {
        year: sorted({
            str(row["day"])
            for row in rows
            if int(str(row["day"])[:4]) == year
        })
        for year in YEARS
    }
    return {
        year: [
            [
                row
                for row in rows
                if int(str(row["day"])[:4]) == year and str(row["day"]) == day
            ]
            for day in days_by_year[year]
        ]
        for year in YEARS
    }


def _splitmix64(counter):
    value = (counter + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return (value ^ (value >> 31)) & 0xFFFFFFFFFFFFFFFF


def _draw_index(seed, replicate, year, offset, limit):
    counter = (
        int(seed)
        ^ (int(replicate) * 0xD1B54A32D192ED03)
        ^ (int(year) * 0xABC98388FB8FAC03)
        ^ (int(offset) * 0x8CB92BA72F3D8DD7)
    ) & 0xFFFFFFFFFFFFFFFF
    threshold = ((1 << 64) - limit) % limit
    candidate = _splitmix64(counter)
    while candidate < threshold:
        counter = (counter + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
        candidate = _splitmix64(counter)
    return candidate % limit


def _draw_year_blocks(year, year_blocks, seed, replicate, plan):
    if not year_blocks:
        _fail(f"bootstrap has no blocks for {year}")
    if plan is None:
        indices = [
            _draw_index(seed, replicate, year, offset, len(year_blocks))
            for offset in range(len(year_blocks))
        ]
    else:
        raw_indices = (
            plan[year]
            if year in plan
            else (plan[str(year)] if str(year) in plan else ())
        )
        indices = [int(index) for index in raw_indices]
        if len(indices) != len(year_blocks):
            _fail(f"bootstrap plan for {year} must draw {len(year_blocks)} day blocks")
        if any(index < 0 or index >= len(year_blocks) for index in indices):
            _fail(f"bootstrap plan index out of range for {year}: {indices!r}")
    return [year_blocks[index] for index in indices]


def _draw_replicate(
    blocks,
    seed,
    replicate,
    plan=None,
):
    selected_blocks = [
        block
        for year in YEARS
        for block in _draw_year_blocks(year, list(blocks[year] if year in blocks else ()), seed, replicate, plan)
    ]
    return [row for block in selected_blocks for row in block]


def _nearest_rank_ci(values):
    ordered = sorted(values)
    if not ordered:
        _fail("bootstrap CI requires at least one value")
    n = len(ordered)
    return [ordered[max(0, ((25 * n + 999) // 1000) - 1)], ordered[max(0, ((975 * n + 999) // 1000) - 1)]]


def bootstrap_intervals(
    rows,
    *,
    draws=BOOTSTRAP_DRAWS,
    seed=BOOTSTRAP_SEED,
    plan=None,
):
    if plan is not None:
        draws = len(plan)
    if draws <= 0:
        _fail("bootstrap draws must be positive")
    blocks = _day_blocks(rows)
    replicate_stats = [
        (
            replicate,
            compute_statistics(
                _draw_replicate(blocks, seed, replicate, None if plan is None else plan[replicate])
            ),
        )
        for replicate in range(draws)
    ]
    first_undefined = next(
        (
            (replicate, stats)
            for replicate, stats in replicate_stats
            if stats["undefined_reasons"]
        ),
        None,
    )
    if first_undefined is not None:
        replicate, stats = first_undefined
        return None, [f"bootstrap_undefined_replicate:{replicate}:" + _join_text(";", stats["undefined_reasons"])]
    raw_values = [float(stats["raw_contrast"]) for _, stats in replicate_stats]
    standardized_values = [float(stats["standardized_contrast"]) for _, stats in replicate_stats]
    ratio_values = [float(stats["residual_ratio"]) for _, stats in replicate_stats]
    return {
        "raw_contrast": _nearest_rank_ci(raw_values),
        "standardized_contrast": _nearest_rank_ci(standardized_values),
        "residual_ratio": _nearest_rank_ci(ratio_values),
    }, []


def _result(decision, *, stats, bootstrap_ci, undetermined, kill):
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


NON_AUTHORITATIVE_TEST_MARKER = "NON_AUTHORITATIVE_TEST_ONLY_NOT_VALID_FOR_EVIDENCE"


def _measure_impl(
    snapshot,
    source_files,
    expected_counts,
    bootstrap_draws,
    bootstrap_seed,
    bootstrap_plan,
):
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
    kill = (
        (["residual_ratio_ge_0.8"] if float(stats["residual_ratio"]) >= RATIO_KILL_THRESHOLD else [])
        + (["annual_sign_conflict"] if stats["annual_sign_conflict"] else [])
    )
    if kill:
        return _result("KILL", stats=stats, bootstrap_ci=bootstrap_ci, undetermined=[], kill=kill)
    return _result("PASS", stats=stats, bootstrap_ci=bootstrap_ci, undetermined=[], kill=[])


def _mark_non_authoritative(result):
    return {
        **result,
        "non_authoritative_test_marker": NON_AUTHORITATIVE_TEST_MARKER,
    }


def _measure_non_authoritative_for_tests(
    snapshot,
    *,
    source_files=SOURCE_FILES,
    expected_counts=EXPECTED_FILTERED_COUNTS,
    bootstrap_draws=BOOTSTRAP_DRAWS,
    bootstrap_seed=BOOTSTRAP_SEED,
    bootstrap_plan=None,
):
    result = _measure_impl(
        snapshot,
        source_files,
        expected_counts,
        bootstrap_draws,
        bootstrap_seed,
        bootstrap_plan,
    )
    return _mark_non_authoritative(result)


def measure(snapshot):
    result = _measure_impl(
        snapshot,
        SOURCE_FILES,
        EXPECTED_FILTERED_COUNTS,
        BOOTSTRAP_DRAWS,
        BOOTSTRAP_SEED,
        None,
    )
    return result


if __name__ == "__main__":
    with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json", mode="r", encoding="utf-8") as handle:
        payload = json.load(handle)
    result = measure(payload)
    output = json.dumps(result)
    print(output)
