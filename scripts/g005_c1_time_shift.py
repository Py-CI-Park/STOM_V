#!/usr/bin/env python3
"""SEALED G005-C1 time-shift finalizer; prints exactly one JSON result."""

import json

INPUT_PATH = "docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_input.json"
INPUT_SCHEMA = "g005-c1-input-v1"
RESULT_SCHEMA = "g005-c1-result-v1"
HYPOTHESIS_ID = "G005-C1-TIME-SHIFT"
YEARS = (2022, 2023)
DISCOVERY_START_DAY = 20220323
DISCOVERY_END_DAY = 20231231
MONTH_DAYS = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
PAIRS = ((16, 37), (16, 38))
PAIR_KEYS = {37: "16x37", 38: "16x38"}
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
ROW_KEYS = ("code", "day", "off", "t0", "year", "y", "b16", "b37", "b38")
CELL_LABELS = ("00", "01", "10", "11")
CELL_COORDS = ((0, 0), (0, 1), (1, 0), (1, 1))
MT_N = 624
MT_M = 397
MT_MATRIX_A = 0x9908B0DF
MT_UPPER_MASK = 0x80000000
MT_LOWER_MASK = 0x7FFFFFFF
MT_WORD_MASK = 0xFFFFFFFF
FAIL_SENTINEL = "G005_C1_UNDETERMINED"
EMPTY_NODE = None
EXPECTED_SOURCES = {
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


def contract_constants(
    *,
    expected_sources = EXPECTED_SOURCES,
    joined_rows = JOINED_ROWS,
    labeled_rows = LABELED_ROWS,
    pooled_cell_floor = POOLED_CELL_FLOOR,
    annual_cell_floor = ANNUAL_CELL_FLOOR,
    placebo_replicates = PLACEBO_REPLICATES,
    bootstrap_draws = BOOTSTRAP_DRAWS,
    placebo_seed = PLACEBO_SEED,
    bootstrap_seed = BOOTSTRAP_SEED,
):
    return {
        "input_schema": INPUT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "status": "SEALED",
        "discovery_window": {"start": "2022-03-23", "end": "2023-12-31"},
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


def make_config(
    *,
    expected_sources = EXPECTED_SOURCES,
    joined_rows = JOINED_ROWS,
    labeled_rows = LABELED_ROWS,
    pooled_cell_floor = POOLED_CELL_FLOOR,
    annual_cell_floor = ANNUAL_CELL_FLOOR,
    placebo_replicates = PLACEBO_REPLICATES,
    bootstrap_draws = BOOTSTRAP_DRAWS,
    placebo_seed = PLACEBO_SEED,
    bootstrap_seed = BOOTSTRAP_SEED,
):
    if placebo_replicates < 1 or bootstrap_draws < 1:
        return {}["replicate and bootstrap counts must be positive"]
    return {
        "expected_sources": {
            key: {
                "path": str(expected_sources[key]["path"]),
                "sha256": str(expected_sources[key]["sha256"]),
                "size_bytes": int(expected_sources[key]["size_bytes"]),
                "rows": int(expected_sources[key]["rows"]),
            }
            for key in SOURCE_KEYS
        },
        "joined_rows": int(joined_rows),
        "labeled_rows": int(labeled_rows),
        "pooled_cell_floor": int(pooled_cell_floor),
        "annual_cell_floor": int(annual_cell_floor),
        "placebo_replicates": int(placebo_replicates),
        "bootstrap_draws": int(bootstrap_draws),
        "placebo_seed": int(placebo_seed),
        "bootstrap_seed": int(bootstrap_seed),
        "contract": contract_constants(
            expected_sources=expected_sources,
            joined_rows=joined_rows,
            labeled_rows=labeled_rows,
            pooled_cell_floor=pooled_cell_floor,
            annual_cell_floor=annual_cell_floor,
            placebo_replicates=placebo_replicates,
            bootstrap_draws=bootstrap_draws,
            placebo_seed=placebo_seed,
            bootstrap_seed=bootstrap_seed,
        ),
    }


PRODUCTION_CONFIG = make_config()
CONTRACT = PRODUCTION_CONFIG["contract"]


def _fail(reason):
    return {}[(FAIL_SENTINEL, reason)]


def _pair_key(bit):
    return PAIR_KEYS[bit]


def _undetermined(reason):
    return {
        "schema": RESULT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "decision": "UNDETERMINED",
        "integrity_reasons": [reason],
    }


def _mapping_get(mapping, key, default = None):
    return mapping[key] if key in mapping else default


def _tuple_replace(values, index, value):
    return values[:index] + (value,) + values[index + 1:]


def _cons(value, tail):
    return (value, tail)


def _iter_cons(node):
    while node is not EMPTY_NODE:
        value, node = node
        yield value


def _freeze_cons(node):
    values = tuple(_iter_cons(node))
    return values[::-1]


def _ascii_digits(text):
    return bool(text) and all(char in "0123456789" for char in text)


def _leap_year(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _valid_day_number(day):
    text = str(day)
    if len(text) != 8 or not _ascii_digits(text):
        return False
    year = int(text[:4])
    month = int(text[4:6])
    month_day = int(text[6:8])
    if month < 1 or month > 12:
        return False
    limit = 29 if month == 2 and _leap_year(year) else MONTH_DAYS[month]
    return 1 <= month_day <= limit


def _float_isfinite(value):
    parsed = float(value)
    return parsed == parsed and parsed != float("inf") and parsed != float("-inf")


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not _float_isfinite(value):
        _fail(f"{name} must be finite")
    return float(value)


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        _fail(f"{name} must be an integer")
    return int(value)


def _bit(value, name):
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int) and value in (0, 1):
        return int(value)
    _fail(f"{name} must be a boolean/integer bit")


def _identity_string(value, name):
    if not isinstance(value, str) or not value:
        _fail(f"{name} must be a nonempty string")
    return value


def _day(value):
    day = _integer(value, "day")
    if not _valid_day_number(day):
        _fail("day must be a valid YYYYMMDD")
    if day < DISCOVERY_START_DAY or day > DISCOVERY_END_DAY:
        _fail("day falls outside the sealed 2022-2023 discovery window")
    return day


def _validate_source(actual, expected, key):
    for field in ("path", "sha256", "size_bytes", "rows"):
        if _mapping_get(actual, field) != _mapping_get(expected, field):
            _fail(f"{key} source {field} does not match the sealed descriptor")


def _validate_sources(snapshot_sources, config):
    if not isinstance(snapshot_sources, dict) or tuple(snapshot_sources) != SOURCE_KEYS:
        _fail("sources must contain exactly the sealed source keys")
    expected = config["expected_sources"]
    for key in SOURCE_KEYS:
        source = snapshot_sources[key]
        if not isinstance(source, dict) or set(source) != {"pre", "post"}:
            _fail(f"{key} source must contain pre and post descriptors only")
        pre, post = source["pre"], source["post"]
        if pre != post:
            _fail(f"{key} source drifted between pre and post descriptors")
        if not isinstance(pre, dict):
            _fail(f"{key} source descriptor is malformed")
        _validate_source(pre, expected[key], key)


def _normalize_row(row, ordinal):
    if not isinstance(row, dict) or set(row) != set(ROW_KEYS):
        _fail(f"eligible row {ordinal} does not contain exactly the sealed fields")
    code = _identity_string(row["code"], "code")
    day = _day(row["day"])
    year = _integer(row["year"], "year")
    if year not in YEARS or year != int(str(day)[:4]):
        _fail("row year is not one of the sealed years or conflicts with day")
    off = _integer(row["off"], "off")
    t0 = _identity_string(row["t0"], "t0")
    return {
        "code": code,
        "day": day,
        "off": off,
        "t0": t0,
        "year": year,
        "y": _finite(row["y"], "l3_net"),
        "b16": _bit(row["b16"], "b16"),
        "b37": _bit(row["b37"], "b37"),
        "b38": _bit(row["b38"], "b38"),
    }


def _normalize_rows(raw_rows, config, row_flow):
    if not isinstance(raw_rows, list):
        _fail("eligible_rows must be a list")
    expected_labeled = config["labeled_rows"]
    if len(raw_rows) != expected_labeled:
        _fail("eligible row count does not match the sealed labeled floor")
    rows = tuple(_normalize_row(row, ordinal) for ordinal, row in enumerate(raw_rows))
    row_keys = tuple((row["code"], row["day"], row["off"], row["t0"]) for row in rows)
    if len(set(row_keys)) != len(row_keys):
        _fail("eligible rows contain duplicate (code,day,off,t0) keys")
    by_year = {
        str(year): sum(1 for row in rows if row["year"] == year)
        for year in YEARS
    }
    if _mapping_get(row_flow, "eligible_by_year") != by_year:
        _fail("row_flow eligible_by_year does not match eligible rows")
    if _mapping_get(row_flow, "eligible_years") != [2022, 2023] or any(by_year[str(year)] <= 0 for year in YEARS):
        _fail("eligible rows must contain exactly the sealed years")
    return rows


def _validate_snapshot(snapshot, config):
    if not isinstance(snapshot, dict) or set(snapshot) != {"schema", "contract", "sources", "row_flow", "eligible_rows"}:
        _fail("snapshot shape is not the sealed G005-C1 input shape")
    if snapshot["schema"] != INPUT_SCHEMA:
        _fail("input schema mismatch")
    if snapshot["contract"] != config["contract"]:
        _fail("contract constants mismatch")
    _validate_sources(snapshot["sources"], config)
    row_flow = snapshot["row_flow"]
    if not isinstance(row_flow, dict):
        _fail("row_flow is malformed")
    if set(row_flow) != {"joined_rows", "labeled_rows", "eligible_years", "eligible_by_year", "unlabeled_or_out_of_window_rows"}:
        _fail("row_flow does not contain exactly the sealed fields")
    joined_rows = _mapping_get(row_flow, "joined_rows")
    labeled_rows = _mapping_get(row_flow, "labeled_rows")
    if joined_rows != config["joined_rows"]:
        _fail("joined row floor mismatch")
    if labeled_rows != config["labeled_rows"]:
        _fail("labeled row floor mismatch")
    if _mapping_get(row_flow, "unlabeled_or_out_of_window_rows") != joined_rows - labeled_rows:
        _fail("row_flow unlabeled_or_out_of_window_rows does not match joined_rows-labeled_rows")
    return _normalize_rows(snapshot["eligible_rows"], config, row_flow), row_flow


def _ceil_positive(value):
    integer = int(value)
    return integer + 1 if value > integer else integer


def _nearest_rank(values, p):
    if not values:
        _fail("nearest-rank quantile has no values")
    if p < 0 or p > 1:
        _fail("p must be in [0,1]")
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, max(0, _ceil_positive(p * len(ordered)) - 1))
    return ordered[index]


def _cell_id(b16_value, bit_value):
    return int(b16_value) * 2 + int(bit_value)


def _row_arrays(rows):
    return {
        "y": tuple(float(row["y"]) for row in rows),
        "b16": tuple(int(row["b16"]) for row in rows),
        "b37": tuple(int(row["b37"]) for row in rows),
        "b38": tuple(int(row["b38"]) for row in rows),
        "day": tuple(int(row["day"]) for row in rows),
        "year": tuple(int(row["year"]) for row in rows),
        "code": tuple(str(row["code"]) for row in rows),
    }


def _selected_indices(length, indices):
    return tuple(range(length)) if indices is None else tuple(indices)


def _cell_counts_from_arrays(b16_values, bit_values, indices = None):
    selected = _selected_indices(len(b16_values), indices)
    return {
        label: sum(1 for index in selected if _cell_id(b16_values[index], bit_values[index]) == position)
        for position, label in enumerate(CELL_LABELS)
    }


def _cell_counts(rows, bit, indices = None):
    bit_name = f"b{bit}"
    selected = _selected_indices(len(rows), indices)
    return {
        label: sum(1 for index in selected if f"{rows[index]['b16']}{rows[index][bit_name]}" == label)
        for label in CELL_LABELS
    }


def _cell_sums_counts_from_arrays(y_values, b16_values, bit_values, indices = None):
    selected = _selected_indices(len(y_values), indices)
    sums = (0.0, 0.0, 0.0, 0.0)
    counts = (0, 0, 0, 0)
    for index in selected:
        cell = _cell_id(b16_values[index], bit_values[index])
        if cell < 0 or cell > 3:
            return sums, (0, 0, 0, 0)
        y = float(y_values[index])
        if not _float_isfinite(y):
            return sums, (0, 0, 0, 0)
        sums = _tuple_replace(sums, cell, sums[cell] + y)
        counts = _tuple_replace(counts, cell, counts[cell] + 1)
    return sums, counts


def _interaction_from_cell_sums_counts(sums, counts):
    if len(sums) < 4 or len(counts) < 4 or any(counts[index] <= 0 for index in range(4)):
        return None
    means = tuple(sums[index] / counts[index] for index in range(4))
    if any(not _float_isfinite(value) for value in means):
        return None
    return float(means[3] - means[2] - means[1] + means[0])


def _interaction_from_arrays(y_values, b16_values, bit_values, indices = None):
    sums, counts = _cell_sums_counts_from_arrays(y_values, b16_values, bit_values, indices)
    return _interaction_from_cell_sums_counts(sums, counts)


def _interaction_from_values(y_values, b16_values, bit_values, indices = None):
    result = _interaction_from_arrays(tuple(y_values), tuple(b16_values), tuple(bit_values), indices)
    return result


def _interaction(rows, bit, indices = None):
    result = _interaction_from_values(
        [row["y"] for row in rows],
        [row["b16"] for row in rows],
        [row[f"b{bit}"] for row in rows],
        indices,
    )
    return result


def _year_indices(year_values, year):
    indices = tuple(index for index, value in enumerate(year_values) if value == year)
    return indices


def _enforce_cell_floors(rows, config, arrays = None):
    arrays = _row_arrays(rows) if arrays is None else arrays
    entries = ()
    for _, bit in PAIRS:
        key = _pair_key(bit)
        bit_values = arrays[f"b{bit}"]
        pooled = _cell_counts_from_arrays(arrays["b16"], bit_values)
        if any(pooled[label] < config["pooled_cell_floor"] for label in CELL_LABELS):
            _fail(f"{key} pooled cell floor failed")
        annual_entries = ()
        for year in YEARS:
            counts = _cell_counts_from_arrays(arrays["b16"], bit_values, _year_indices(arrays["year"], year))
            if any(counts[label] < config["annual_cell_floor"] for label in CELL_LABELS):
                _fail(f"{key} {year} annual cell floor failed")
            annual_entries = annual_entries + ((str(year), counts),)
        entries = entries + ((key, {"pooled": pooled, "annual": dict(annual_entries)}),)
    return dict(entries)


def _observed(rows, arrays = None):
    arrays = _row_arrays(rows) if arrays is None else arrays
    entries = ()
    for _, bit in PAIRS:
        key = _pair_key(bit)
        bit_values = arrays[f"b{bit}"]
        pooled = _interaction_from_arrays(arrays["y"], arrays["b16"], bit_values)
        if pooled is None:
            _fail(f"{key} observed pooled interaction is undefined")
        annual_entries = ()
        for year in YEARS:
            value = _interaction_from_arrays(arrays["y"], arrays["b16"], bit_values, _year_indices(arrays["year"], year))
            if value is None:
                _fail(f"{key} {year} observed annual interaction is undefined")
            annual_entries = annual_entries + ((str(year), value),)
        entries = entries + ((key, {"pooled": pooled, "annual": dict(annual_entries)}),)
    return dict(entries)


def _ordered_groups(rows):
    groups = EMPTY_NODE
    group_keys = EMPTY_NODE
    current_key = None
    current_group = EMPTY_NODE
    previous_sort_key = None
    for index, row in enumerate(rows):
        sort_key = (str(row["code"]), int(row["day"]), int(row["off"]), str(row["t0"]))
        key = (sort_key[0], sort_key[1])
        if previous_sort_key is not None and sort_key < previous_sort_key:
            _fail("eligible rows must be sorted by (code,day,off,t0)")
        if current_key is None or key == current_key:
            current_group = _cons(index, current_group)
        else:
            groups = _cons(_freeze_cons(current_group), groups)
            group_keys = _cons(current_key, group_keys)
            current_group = _cons(index, EMPTY_NODE)
        current_key = key
        previous_sort_key = sort_key
    if current_key is not None:
        groups = _cons(_freeze_cons(current_group), groups)
        group_keys = _cons(current_key, group_keys)
    frozen_keys = _freeze_cons(group_keys)
    if len(set(frozen_keys)) != len(frozen_keys):
        _fail("eligible rows contain noncontiguous (code,day) groups")
    return _freeze_cons(groups)


def _placebo_support(groups):
    support = tuple(index for group in groups if len(group) >= 2 for index in group)
    return support


def _shiftable_group_arrays(groups):
    group_arrays = tuple(tuple(group) for group in groups if len(group) >= 2)
    return group_arrays


def _bit_length(value):
    number = int(value)
    bits = 0
    while number:
        bits = bits + 1
        number = number >> 1
    return bits


def _seed_key(seed):
    value = abs(int(seed))
    if value == 0:
        return (0,)
    chunks = ()
    while value:
        chunks = chunks + (value & MT_WORD_MASK,)
        value = value >> 32
    return chunks


def _mt_init_genrand(seed):
    value = int(seed) & MT_WORD_MASK
    mt = (value,)
    for index in range(1, MT_N):
        value = (1812433253 * (value ^ (value >> 30)) + index) & MT_WORD_MASK
        mt = mt + (value,)
    return mt


def _mt_seed(seed):
    key = _seed_key(seed)
    mt = _mt_init_genrand(19650218)
    i = 1
    j = 0
    limit = max(MT_N, len(key))
    for _ in range(limit):
        previous = mt[i - 1]
        value = (mt[i] ^ ((previous ^ (previous >> 30)) * 1664525)) + key[j] + j
        mt = _tuple_replace(mt, i, value & MT_WORD_MASK)
        i = i + 1
        j = j + 1
        if i >= MT_N:
            mt = _tuple_replace(mt, 0, mt[MT_N - 1])
            i = 1
        if j >= len(key):
            j = 0
    for _ in range(MT_N - 1):
        previous = mt[i - 1]
        value = (mt[i] ^ ((previous ^ (previous >> 30)) * 1566083941)) - i
        mt = _tuple_replace(mt, i, value & MT_WORD_MASK)
        i = i + 1
        if i >= MT_N:
            mt = _tuple_replace(mt, 0, mt[MT_N - 1])
            i = 1
    mt = _tuple_replace(mt, 0, MT_UPPER_MASK)
    return mt, MT_N


def _rng_state(seed):
    state = _mt_seed(seed)
    return state


def _mt_twist(mt):
    twisted = EMPTY_NODE
    for index in range(MT_N):
        y = (mt[index] & MT_UPPER_MASK) | (mt[(index + 1) % MT_N] & MT_LOWER_MASK)
        value = mt[(index + MT_M) % MT_N] ^ (y >> 1)
        if y & 1:
            value = value ^ MT_MATRIX_A
        twisted = _cons(value & MT_WORD_MASK, twisted)
    return _freeze_cons(twisted)


def _mt_uint32(state):
    mt, index = state
    if index >= MT_N:
        mt = _mt_twist(mt)
        index = 0
    y = mt[index]
    index = index + 1
    y = y ^ (y >> 11)
    y = y ^ ((y << 7) & 0x9D2C5680)
    y = y ^ ((y << 15) & 0xEFC60000)
    y = y ^ (y >> 18)
    return (mt, index), y & MT_WORD_MASK


def _mt_getrandbits(state, bits):
    if bits <= 0:
        return state, 0
    if bits <= 32:
        next_state, word = _mt_uint32(state)
        return next_state, word >> (32 - bits)
    value = 0
    shift = 0
    next_state = state
    remaining = bits
    while remaining > 0:
        take = min(remaining, 32)
        next_state, word = _mt_getrandbits(next_state, take)
        value = value | (word << shift)
        shift = shift + take
        remaining = remaining - take
    return next_state, value


def _mt_randbelow(state, limit):
    if limit <= 0:
        _fail("empty randrange")
    bits = _bit_length(limit)
    next_state, value = _mt_getrandbits(state, bits)
    while value >= limit:
        next_state, value = _mt_getrandbits(next_state, bits)
    return next_state, value


def _rng_randrange(state, *args):
    if len(args) == 1:
        start = 0
        stop = int(args[0])
    elif len(args) == 2:
        start = int(args[0])
        stop = int(args[1])
    else:
        _fail("randrange supports one or two arguments")
    width = stop - start
    next_state, offset = _mt_randbelow(state, width)
    return next_state, start + offset


def _rolled_group_with_call(group, rng_state):
    n = len(group)
    if n < 2:
        return rng_state, group, 0
    next_state, offset = _rng_randrange(rng_state, 1, n)
    rolled = tuple(group[(position - offset) % n] for position in range(n))
    return next_state, rolled, 1


def _placebo_shifted_group_results(shiftable_groups, rng_state):
    results = EMPTY_NODE
    state = rng_state
    for group in shiftable_groups:
        state, rolled, calls = _rolled_group_with_call(group, state)
        results = _cons((rolled, calls), results)
    return state, _freeze_cons(results)


def _placebo_shifted_sources(shiftable_groups, rng_state):
    state, shifted_results = _placebo_shifted_group_results(shiftable_groups, rng_state)
    shifted_sources = tuple(source for group, _ in shifted_results for source in group)
    return state, shifted_sources, sum(call_count for _, call_count in shifted_results)


def _placebo_source_indices(base_indices, shiftable_groups, rng_state):
    state, shifted_results = _placebo_shifted_group_results(shiftable_groups, rng_state)
    source_pairs = tuple(
        (int(target), int(source))
        for group, (rolled_group, _) in zip(shiftable_groups, shifted_results)
        for target, source in zip(group, rolled_group)
    )
    source_lookup = dict(source_pairs)
    source_array = tuple(_mapping_get(source_lookup, int(index), int(index)) for index in base_indices)
    return state, source_array, sum(call_count for _, call_count in shifted_results)


def _shift_group_source_pairs(group, rng_state):
    n = len(group)
    if n < 2:
        return rng_state, (), 0
    next_state, offset = _rng_randrange(rng_state, 1, n)
    return next_state, tuple((row_index, group[(position - offset) % n]) for position, row_index in enumerate(group)), 1


def _shift_pressure_bits(rows, groups, rng_state):
    source_results = EMPTY_NODE
    state = rng_state
    for group in groups:
        state, pairs, calls = _shift_group_source_pairs(group, state)
        source_results = _cons((pairs, calls), source_results)
    frozen_results = _freeze_cons(source_results)
    source_lookup = dict(pair for pairs, _ in frozen_results for pair in pairs)
    shifted37 = [int(rows[_mapping_get(source_lookup, index, index)]["b37"]) for index in range(len(rows))]
    shifted38 = [int(rows[_mapping_get(source_lookup, index, index)]["b38"]) for index in range(len(rows))]
    return state, shifted37, shifted38, sum(call_count for _, call_count in frozen_results)


def _placebo_replicate_values(replicate, arrays, y_support, b16_support, shiftable_groups, rng_state):
    state, shifted_sources, calls = _placebo_shifted_sources(shiftable_groups, rng_state)
    pair_values = tuple(
        (
            _pair_key(bit),
            _interaction_from_arrays(
                y_support,
                b16_support,
                tuple(arrays[f"b{bit}"][index] for index in shifted_sources),
            ),
        )
        for _, bit in PAIRS
    )
    undefined = tuple(key for key, value in pair_values if value is None)
    if undefined:
        _fail(f"{undefined[0]} placebo replicate {replicate} is undefined")
    return state, dict(pair_values), calls


def _placebo_thresholds(rows, config, arrays = None):
    arrays = _row_arrays(rows) if arrays is None else arrays
    groups = _ordered_groups(rows)
    support = _placebo_support(groups)
    if not support:
        _fail("placebo support contains no shiftable rows")
    state = _rng_state(config["placebo_seed"])
    shiftable_groups = _shiftable_group_arrays(groups)
    y_support = tuple(arrays["y"][index] for index in support)
    b16_support = tuple(arrays["b16"][index] for index in support)
    replicate_results = EMPTY_NODE
    for replicate in range(config["placebo_replicates"]):
        state, values_by_pair, calls = _placebo_replicate_values(
            replicate,
            arrays,
            y_support,
            b16_support,
            shiftable_groups,
            state,
        )
        replicate_results = _cons((values_by_pair, calls), replicate_results)
    frozen_results = _freeze_cons(replicate_results)
    pair_series = {
        _pair_key(bit): [values_by_pair[_pair_key(bit)] for values_by_pair, _ in frozen_results]
        for _, bit in PAIRS
    }
    singleton_rows = sum(len(group) for group in groups if len(group) < 2)
    return {
        "q95_pp": {key: _nearest_rank(pair_series[key], 0.95) for key in pair_series},
        "replicates": int(config["placebo_replicates"]),
        "seed": int(config["placebo_seed"]),
        "support_rows": len(support),
        "singleton_rows_excluded": singleton_rows,
        "singleton_excluded_rate": singleton_rows / len(rows) if rows else 0.0,
        "shiftable_groups": len(shiftable_groups),
        "singleton_groups": sum(1 for group in groups if len(group) < 2),
        "offset_calls": sum(call_count for _, call_count in frozen_results),
    }


def _day_blocks(rows, year):
    days = sorted(set(int(row["day"]) for row in rows if row["year"] == year))
    return {
        day: tuple(index for index, row in enumerate(rows) if row["year"] == year and int(row["day"]) == day)
        for day in days
    }


def _bootstrap_sample_indices(day_blocks, rng_state):
    days = sorted(day_blocks)
    if not days:
        _fail("bootstrap day support is empty")
    sampled_days = EMPTY_NODE
    sampled_indices = EMPTY_NODE
    state = rng_state
    for _ in days:
        state, position = _rng_randrange(state, len(days))
        day = days[position]
        sampled_days = _cons(day, sampled_days)
        for index in day_blocks[day]:
            sampled_indices = _cons(index, sampled_indices)
    return state, list(_freeze_cons(sampled_indices)), list(_freeze_cons(sampled_days))


def _bootstrap_sample_day_positions(day_count, rng_state):
    if day_count <= 0:
        _fail("bootstrap day support is empty")
    positions = EMPTY_NODE
    state = rng_state
    for _ in range(day_count):
        state, position = _rng_randrange(state, day_count)
        positions = _cons(position, positions)
    return state, _freeze_cons(positions)


def _day_pair_cell_aggregate(day_indices, y_values, b16_values, bit_values):
    aggregates = tuple(
        _cell_sums_counts_from_arrays(y_values, b16_values, bit_values, indices)
        for indices in day_indices
    )
    return aggregates


def _bootstrap_day_cell_aggregates(arrays, year):
    days = sorted(set(arrays["day"][index] for index, value in enumerate(arrays["year"]) if value == year))
    if not days:
        return [], (), ()
    day_indices = tuple(
        tuple(index for index, value in enumerate(arrays["day"]) if value == day and arrays["year"][index] == year)
        for day in days
    )
    pair_aggregates = tuple(
        _day_pair_cell_aggregate(day_indices, arrays["y"], arrays["b16"], arrays[f"b{bit}"])
        for _, bit in PAIRS
    )
    pair_sums = tuple(tuple(sums for sums, _ in aggregate) for aggregate in pair_aggregates)
    pair_counts = tuple(tuple(counts for _, counts in aggregate) for aggregate in pair_aggregates)
    return days, pair_sums, pair_counts


def _aggregate_sampled_cells(day_values, sampled_positions):
    aggregates = tuple(sum(day_values[position][cell] for position in sampled_positions) for cell in range(4))
    return aggregates


def _bootstrap_draw_pair_values(year, draw, day_count, pair_sums, pair_counts, rng_state):
    state, sampled_positions = _bootstrap_sample_day_positions(day_count, rng_state)
    pair_values = tuple(
        (
            _pair_key(bit),
            _interaction_from_cell_sums_counts(
                _aggregate_sampled_cells(pair_sums[pair_index], sampled_positions),
                _aggregate_sampled_cells(pair_counts[pair_index], sampled_positions),
            ),
        )
        for pair_index, (_, bit) in enumerate(PAIRS)
    )
    undefined = tuple(key for key, value in pair_values if value is None)
    if undefined:
        _fail(f"{undefined[0]} {year} bootstrap draw {draw} is undefined")
    return state, dict(pair_values)


def _bootstrap_year_values(year, config, arrays, rng_state):
    days, pair_sums, pair_counts = _bootstrap_day_cell_aggregates(arrays, year)
    day_count = len(days)
    if day_count == 0:
        _fail(f"{year} bootstrap day support is empty")
    draw_values = EMPTY_NODE
    state = rng_state
    for draw in range(config["bootstrap_draws"]):
        state, values_by_pair = _bootstrap_draw_pair_values(year, draw, day_count, pair_sums, pair_counts, state)
        draw_values = _cons(values_by_pair, draw_values)
    frozen_values = _freeze_cons(draw_values)
    return state, str(year), {
        _pair_key(bit): [values_by_pair[_pair_key(bit)] for values_by_pair in frozen_values]
        for _, bit in PAIRS
    }


def _bootstrap_cis(rows, config, arrays = None):
    arrays = _row_arrays(rows) if arrays is None else arrays
    state = _rng_state(config["bootstrap_seed"])
    annual_results = EMPTY_NODE
    for year in YEARS:
        state, year_key, series_by_pair = _bootstrap_year_values(year, config, arrays, state)
        annual_results = _cons((year_key, series_by_pair), annual_results)
    frozen_results = _freeze_cons(annual_results)
    return {
        _pair_key(bit): {
            year: [
                _nearest_rank(series_by_pair[_pair_key(bit)], 0.025),
                _nearest_rank(series_by_pair[_pair_key(bit)], 0.975),
            ]
            for year, series_by_pair in frozen_results
        }
        for _, bit in PAIRS
    }


def _code_ranges(code_values):
    ranges = EMPTY_NODE
    current_code = None
    start = 0
    for index, code in enumerate(code_values):
        if current_code is None:
            current_code = code
            start = index
        elif code != current_code:
            ranges = _cons((current_code, start, index), ranges)
            current_code = code
            start = index
    if current_code is not None:
        ranges = _cons((current_code, start, len(code_values)), ranges)
    frozen = _freeze_cons(ranges)
    if len(set(code for code, _, _ in frozen)) != len(frozen):
        _fail("eligible rows must be sorted by code for leave-one-code-out")
    return frozen


def _code_cell_sums_counts(arrays, bit_values, start, stop):
    result = _cell_sums_counts_from_arrays(
        arrays["y"],
        arrays["b16"],
        bit_values,
        range(start, stop),
    )
    return result


def _subtract_cells(total_values, removed_values):
    values = tuple(total_values[cell] - removed_values[cell] for cell in range(4))
    return values


def _leave_one_pair(arrays, bit, code_ranges):
    bit_values = arrays[f"b{bit}"]
    total_sums, total_counts = _cell_sums_counts_from_arrays(arrays["y"], arrays["b16"], bit_values)
    per_code = tuple(
        (
            code,
            *_code_cell_sums_counts(arrays, bit_values, start, stop),
        )
        for code, start, stop in code_ranges
    )
    exclusion_values = tuple(
        (
            code,
            _interaction_from_cell_sums_counts(
                _subtract_cells(total_sums, code_sums),
                _subtract_cells(total_counts, code_counts),
            ),
        )
        for code, code_sums, code_counts in per_code
    )
    values = [value for _, value in exclusion_values if value is not None]
    undefined = [code for code, value in exclusion_values if value is None]
    return {
        "n_codes": len(code_ranges),
        "finite_exclusions": len(values),
        "undefined_codes": undefined,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _leave_one_code_out(rows, arrays = None):
    arrays = _row_arrays(rows) if arrays is None else arrays
    code_ranges = _code_ranges(arrays["code"])
    return {
        _pair_key(bit): _leave_one_pair(arrays, bit, code_ranges)
        for _, bit in PAIRS
    }


def measure(snapshot, *, config = PRODUCTION_CONFIG):
    """Pure G005-C1 measurement over a sealed input snapshot; performs no filesystem access."""
    try:
        rows, row_flow = _validate_snapshot(snapshot, config)
        arrays = _row_arrays(rows)
        cell_counts = _enforce_cell_floors(rows, config, arrays)
        observed = _observed(rows, arrays)
        placebo = _placebo_thresholds(rows, config, arrays)
        bootstrap_ci = _bootstrap_cis(rows, config, arrays)
        leave_one_code_out = _leave_one_code_out(rows, arrays)
    except KeyError as exc:
        marker = exc.args[0] if exc.args else None
        if isinstance(marker, tuple) and len(marker) == 2 and marker[0] == FAIL_SENTINEL:
            return _undetermined(marker[1])
        raise

    pair_pass = {
        _pair_key(bit): bool(
            observed[_pair_key(bit)]["pooled"] > placebo["q95_pp"][_pair_key(bit)]
            and all(bootstrap_ci[_pair_key(bit)][str(year)][0] > 0 for year in YEARS)
        )
        for _, bit in PAIRS
    }
    decision = "PASS" if all(pair_pass[key] for key in pair_pass) else "KILL"
    return {
        "schema": RESULT_SCHEMA,
        "hypothesis_id": HYPOTHESIS_ID,
        "decision": decision,
        "integrity_reasons": [],
        "row_flow": dict(row_flow),
        "cell_counts": cell_counts,
        "observed_interactions_pp": observed,
        "placebo": placebo,
        "bootstrap_ci_pp": bootstrap_ci,
        "leave_one_code_out_range_pp": leave_one_code_out,
        "decision_diagnostics": {
            "pair_pass": pair_pass,
            "rule": "PASS requires both fixed pairs to have pooled observed I strictly greater than their placebo Q(.95) and both 2022 and 2023 annual day-block bootstrap lower CI bounds strictly greater than zero; otherwise identified measurements KILL.",
        },
    }


def main(snapshot):
    result = measure(snapshot)
    print(json.dumps(result))


if __name__ == "__main__":
    with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g005/c1_input.json", mode="r", encoding="utf-8") as handle:
        snapshot = json.load(handle)
    main(snapshot)
