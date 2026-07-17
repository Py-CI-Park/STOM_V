from __future__ import annotations

import copy
import json
import importlib.util
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script(filename: str) -> object:
    spec = importlib.util.spec_from_file_location(filename.replace(".py", "_test"), ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manual_sources(target, rows: int) -> dict[str, dict[str, object]]:
    return {
        target.L3_KEY: {"path": "tmp/l3.parquet", "sha256": "a" * 64, "size_bytes": 11, "rows": rows},
        target.D1_KEY: {"path": "tmp/d1.parquet", "sha256": "b" * 64, "size_bytes": 13, "rows": rows},
    }


def _config(target, rows: list[dict[str, object]], *, floor: int = 1, reps: int = 1, draws: int = 1,
            placebo_seed: int = 2026071601, bootstrap_seed: int = 2026071602):
    sources = _manual_sources(target, len(rows))
    return target.make_config(
        expected_sources=sources,
        joined_rows=len(rows),
        labeled_rows=len(rows),
        pooled_cell_floor=floor,
        annual_cell_floor=floor,
        placebo_replicates=reps,
        bootstrap_draws=draws,
        placebo_seed=placebo_seed,
        bootstrap_seed=bootstrap_seed,
    )


def _snapshot(target, rows: list[dict[str, object]], config: dict[str, object]) -> dict[str, object]:
    by_year = {str(year): sum(1 for row in rows if row["year"] == year) for year in target.YEARS}
    return {
        "schema": target.INPUT_SCHEMA,
        "contract": config["contract"],
        "sources": {key: {"pre": dict(value), "post": dict(value)} for key, value in config["expected_sources"].items()},
        "row_flow": {
            "joined_rows": len(rows),
            "labeled_rows": len(rows),
            "eligible_years": [2022, 2023],
            "eligible_by_year": by_year,
            "unlabeled_or_out_of_window_rows": 0,
        },
        "eligible_rows": rows,
    }


def _decision_rows(*, pass_case: bool = True) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cells = [(0, 0), (1, 0), (0, 1), (1, 1)]
    y_values = [10.0, 0.0, 0.0, 10.0] if pass_case else [0.0, 10.0, 10.0, 0.0]
    for year, day in ((2022, 20220323), (2023, 20230103)):
        for off, ((b16, bit), y) in enumerate(zip(cells, y_values)):
            rows.append({
                "code": "000001",
                "day": day,
                "off": off,
                "t0": f"{day}0900{off:02d}",
                "year": year,
                "y": y,
                "b16": b16,
                "b37": bit,
                "b38": bit,
            })
    return rows


def _undefined_placebo_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    specs = [
        ("A", 0, 0),
        ("A", 1, 1),
        ("B", 0, 1),
        ("C", 1, 0),
    ]
    for year, day in ((2022, 20220323), (2023, 20230103)):
        for off, (code, b16, bit) in enumerate(specs):
            rows.append({
                "code": code,
                "day": day,
                "off": off,
                "t0": f"{day}0900{off:02d}",
                "year": year,
                "y": 10.0 if b16 == bit else 0.0,
                "b16": b16,
                "b37": bit,
                "b38": bit,
            })
    return sorted(rows, key=lambda row: (row["code"], int(row["day"]), int(row["off"]), row["t0"]))


def _reference_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cells = [(0, 0, 1.0), (1, 0, 2.0), (0, 1, 4.0), (1, 1, 8.0)]
    for year, days in ((2022, (20220323, 20220324)), (2023, (20230103, 20230104))):
        year_delta = 0.0 if year == 2022 else 20.0
        for day_ordinal, day in enumerate(days):
            code = "A" if day_ordinal == 0 else "B"
            for off, (b16, bit, y) in enumerate(cells):
                rows.append({
                    "code": code,
                    "day": day,
                    "off": off,
                    "t0": f"{day}0900{off:02d}",
                    "year": year,
                    "y": y + year_delta + day_ordinal,
                    "b16": b16,
                    "b37": bit,
                    "b38": 1 - bit,
                })
        rows.append({
            "code": "Z",
            "day": days[0],
            "off": 99,
            "t0": f"{days[0]}099900",
            "year": year,
            "y": 3.0 + year_delta,
            "b16": 0,
            "b37": 0,
            "b38": 1,
        })
    return sorted(rows, key=lambda row: (row["code"], int(row["day"]), int(row["off"]), row["t0"]))


def _naive_placebo_thresholds(target, rows: list[dict[str, object]], config: dict[str, object]) -> dict[str, object]:
    groups = target._ordered_groups(rows)
    support = target._placebo_support(groups)
    rng = target._rng_state(config["placebo_seed"])
    y_values = [row["y"] for row in rows]
    b16_values = [row["b16"] for row in rows]
    values = {target._pair_key(bit): [] for _, bit in target.PAIRS}
    offset_calls = 0
    for replicate in range(config["placebo_replicates"]):
        rng, shifted37, shifted38, calls = target._shift_pressure_bits(rows, groups, rng)
        offset_calls += calls
        for bit, shifted in ((37, shifted37), (38, shifted38)):
            key = target._pair_key(bit)
            value = target._interaction_from_values(y_values, b16_values, shifted, support)
            if value is None:
                raise AssertionError(f"{key} placebo replicate {replicate} unexpectedly undefined")
            values[key].append(value)
    singleton_rows = sum(len(group) for group in groups if len(group) < 2)
    return {
        "q95_pp": {key: target._nearest_rank(series, 0.95) for key, series in values.items()},
        "replicates": int(config["placebo_replicates"]),
        "seed": int(config["placebo_seed"]),
        "support_rows": len(support),
        "singleton_rows_excluded": singleton_rows,
        "singleton_excluded_rate": singleton_rows / len(rows),
        "shiftable_groups": sum(1 for group in groups if len(group) >= 2),
        "singleton_groups": sum(1 for group in groups if len(group) < 2),
        "offset_calls": offset_calls,
    }


def _naive_bootstrap_cis(target, rows: list[dict[str, object]], config: dict[str, object]) -> dict[str, object]:
    rng = target._rng_state(config["bootstrap_seed"])
    values = {target._pair_key(bit): {str(year): [] for year in target.YEARS} for _, bit in target.PAIRS}
    for year in target.YEARS:
        blocks = target._day_blocks(rows, year)
        for draw in range(config["bootstrap_draws"]):
            rng, sampled_indices, _sampled_days = target._bootstrap_sample_indices(blocks, rng)
            for _, bit in target.PAIRS:
                key = target._pair_key(bit)
                value = target._interaction(rows, bit, sampled_indices)
                if value is None:
                    raise AssertionError(f"{key} {year} bootstrap draw {draw} unexpectedly undefined")
                values[key][str(year)].append(value)
    return {
        key: {
            year: [
                target._nearest_rank(series, 0.025),
                target._nearest_rank(series, 0.975),
            ]
            for year, series in annual.items()
        }
        for key, annual in values.items()
    }


def _naive_leave_one_code_out(target, rows: list[dict[str, object]]) -> dict[str, object]:
    codes = sorted({str(row["code"]) for row in rows})
    output: dict[str, object] = {}
    for _, bit in target.PAIRS:
        values: list[float] = []
        undefined: list[str] = []
        for code in codes:
            indices = [index for index, row in enumerate(rows) if str(row["code"]) != code]
            value = target._interaction(rows, bit, indices)
            if value is None:
                undefined.append(code)
            else:
                values.append(value)
        output[target._pair_key(bit)] = {
            "n_codes": len(codes),
            "finite_exclusions": len(values),
            "undefined_codes": undefined,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
        }
    return output


def _write_parquets(tmp_path: Path, builder, row_specs: list[dict[str, object]], *, omit_d1_bit38: bool = False) -> tuple[Path, Path]:
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    tmp_path.mkdir(parents=True, exist_ok=True)
    l3_rows = []
    d1_rows = []
    for row in row_specs:
        l3_rows.append({
            "code": row["code"],
            "day": row["day"],
            "off": row["off"],
            "t0": row["t0"],
            "year": row["year"],
            "updown_q": 0,
            "mktcap_b": 0,
            "time_b": 0,
            "l3_net": row["y"],
            "l3_labeled": 1,
            "l3_clause": "x",
            "l3_exit": "x",
        })
        d1 = {"code": row["code"], "day": row["day"], "off": row["off"], "t0": row["t0"]}
        for number in range(1, 40):
            if omit_d1_bit38 and number == 38:
                continue
            d1[f"bit_{number}"] = 0
        d1["bit_16"] = row["b16"]
        d1["bit_37"] = row["b37"]
        if not omit_d1_bit38:
            d1["bit_38"] = row["b38"]
        d1_rows.append(d1)
    l3_path, d1_path = tmp_path / "l3.parquet", tmp_path / "d1.parquet"
    pq.write_table(pa.Table.from_pylist(l3_rows), l3_path)
    pq.write_table(pa.Table.from_pylist(d1_rows), d1_path)
    return l3_path, d1_path


def _fixture_sources(builder, l3_path: Path, d1_path: Path) -> dict[str, dict[str, object]]:
    l3 = builder._source_descriptor(l3_path, "tmp/l3.parquet")
    d1 = builder._source_descriptor(d1_path, "tmp/d1.parquet")
    return {
        builder.L3_KEY: {field: l3[field] for field in ("path", "sha256", "size_bytes", "rows")},
        builder.D1_KEY: {field: d1[field] for field in ("path", "sha256", "size_bytes", "rows")},
    }


def test_builder_verifies_arrow_join_and_writes_deterministic_exclusive_plain_json(tmp_path: Path) -> None:
    builder = load_script("build_g005_c1_input.py")
    rows = _decision_rows(pass_case=True)
    l3_path, d1_path = _write_parquets(tmp_path, builder, rows)
    sources = _fixture_sources(builder, l3_path, d1_path)
    contract = builder.contract_constants(
        expected_sources=sources,
        joined_rows=len(rows),
        labeled_rows=len(rows),
        pooled_cell_floor=1,
        annual_cell_floor=1,
        placebo_replicates=1,
        bootstrap_draws=1,
    )
    snapshot = builder.build_snapshot(
        l3_path,
        d1_path,
        expected_sources=sources,
        expected_joined_rows=len(rows),
        expected_labeled_rows=len(rows),
        contract=contract,
    )
    assert snapshot["schema"] == builder.INPUT_SCHEMA
    assert snapshot["row_flow"]["joined_rows"] == len(rows)
    assert snapshot["row_flow"]["labeled_rows"] == len(rows)
    assert all(set(row) == set(builder.ROW_KEYS) for row in snapshot["eligible_rows"])
    assert snapshot["sources"][builder.L3_KEY]["pre"] == snapshot["sources"][builder.L3_KEY]["post"]
    assert snapshot["contract"]["discovery_window"] == {"start": "2022-03-23", "end": "2023-12-31"}

    out1, out2 = tmp_path / "c1_a.json", tmp_path / "c1_b.json"
    builder.write_snapshot(snapshot, out1)
    builder.write_snapshot(snapshot, out2)
    expected_json = builder.json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert out1.read_text(encoding="utf-8") == expected_json
    assert out2.read_text(encoding="utf-8") == expected_json
    assert builder.json.loads(out1.read_text(encoding="utf-8")) == snapshot
    with pytest.raises(FileExistsError):
        builder.write_snapshot(snapshot, out1)
    with pytest.raises(ValueError, match="already exists"):
        builder.materialize(
            l3_path,
            d1_path,
            out1,
            expected_sources=sources,
            expected_joined_rows=len(rows),
            expected_labeled_rows=len(rows),
            contract=contract,
        )


def test_builder_filters_exact_discovery_window_before_materialization(tmp_path: Path) -> None:
    builder = load_script("build_g005_c1_input.py")
    eligible_rows = _decision_rows(pass_case=True)
    pre_window = dict(eligible_rows[0])
    pre_window["code"] = "PRE"
    pre_window["day"] = 20220103
    pre_window["t0"] = "20220103090000"
    rows = [pre_window, *eligible_rows]
    l3_path, d1_path = _write_parquets(tmp_path, builder, rows)
    sources = _fixture_sources(builder, l3_path, d1_path)
    contract = builder.contract_constants(
        expected_sources=sources,
        joined_rows=len(rows),
        labeled_rows=len(eligible_rows),
        pooled_cell_floor=1,
        annual_cell_floor=1,
        placebo_replicates=1,
        bootstrap_draws=1,
    )

    snapshot = builder.build_snapshot(
        l3_path,
        d1_path,
        expected_sources=sources,
        expected_joined_rows=len(rows),
        expected_labeled_rows=len(eligible_rows),
        contract=contract,
    )

    assert snapshot["contract"]["discovery_window"] == {"start": "2022-03-23", "end": "2023-12-31"}
    assert snapshot["row_flow"]["labeled_rows"] == len(eligible_rows)
    assert snapshot["row_flow"]["unlabeled_or_out_of_window_rows"] == 1
    assert all(row["day"] >= builder.DISCOVERY_START_DAY for row in snapshot["eligible_rows"])


def test_builder_and_target_contract_constants_match() -> None:
    builder = load_script("build_g005_c1_input.py")
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    target_sources = _manual_sources(target, len(rows))
    builder_sources = {
        builder.L3_KEY: dict(target_sources[target.L3_KEY]),
        builder.D1_KEY: dict(target_sources[target.D1_KEY]),
    }

    assert builder.contract_constants(
        expected_sources=builder_sources,
        joined_rows=len(rows),
        labeled_rows=len(rows),
        pooled_cell_floor=1,
        annual_cell_floor=1,
        placebo_replicates=1,
        bootstrap_draws=1,
    ) == target.contract_constants(
        expected_sources=target_sources,
        joined_rows=len(rows),
        labeled_rows=len(rows),
        pooled_cell_floor=1,
        annual_cell_floor=1,
        placebo_replicates=1,
        bootstrap_draws=1,
    )


def test_builder_rejects_source_hash_and_arrow_schema_drift(tmp_path: Path) -> None:
    builder = load_script("build_g005_c1_input.py")
    rows = _decision_rows(pass_case=True)
    l3_path, d1_path = _write_parquets(tmp_path, builder, rows)
    sources = _fixture_sources(builder, l3_path, d1_path)
    bad_sources = copy.deepcopy(sources)
    bad_sources[builder.L3_KEY]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source drift"):
        builder.build_snapshot(
            l3_path,
            d1_path,
            expected_sources=bad_sources,
            expected_joined_rows=len(rows),
            expected_labeled_rows=len(rows),
        )

    bad_l3, bad_d1 = _write_parquets(tmp_path / "bad_schema", builder, rows, omit_d1_bit38=True)
    bad_schema_sources = _fixture_sources(builder, bad_l3, bad_d1)
    with pytest.raises(ValueError, match="Arrow schema"):
        builder.build_snapshot(
            bad_l3,
            bad_d1,
            expected_sources=bad_schema_sources,
            expected_joined_rows=len(rows),
            expected_labeled_rows=len(rows),
        )


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("code", None, "code must be a nonempty string"),
        ("code", 123, "code must be a nonempty string"),
        ("code", "", "code must be a nonempty string"),
        ("t0", None, "t0 must be a nonempty string"),
        ("t0", 123, "t0 must be a nonempty string"),
        ("t0", "", "t0 must be a nonempty string"),
    ],
)
def test_builder_rejects_missing_or_nonstring_identity_before_materialization(
    tmp_path: Path,
    field: str,
    bad_value: object,
    message: str,
) -> None:
    builder = load_script("build_g005_c1_input.py")
    rows = _decision_rows(pass_case=True)
    for row in rows:
        row[field] = bad_value
    l3_path, d1_path = _write_parquets(tmp_path, builder, rows)
    sources = _fixture_sources(builder, l3_path, d1_path)

    with pytest.raises(ValueError, match=message):
        builder.build_snapshot(
            l3_path,
            d1_path,
            expected_sources=sources,
            expected_joined_rows=len(rows),
            expected_labeled_rows=len(rows),
        )


@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("day", None, "day must be an integer"),
        ("day", "20220323", "day must be an integer"),
        ("day", 20220230, "day must be a valid YYYYMMDD integer"),
        ("off", None, "off must be an integer"),
        ("off", "0", "off must be an integer"),
    ],
)
def test_builder_rejects_null_or_invalid_day_off_before_join(
    tmp_path: Path,
    field: str,
    bad_value: object,
    message: str,
) -> None:
    builder = load_script("build_g005_c1_input.py")
    rows = _decision_rows(pass_case=True)
    for row in rows:
        row[field] = bad_value
    l3_path, d1_path = _write_parquets(tmp_path, builder, rows)
    sources = _fixture_sources(builder, l3_path, d1_path)

    with pytest.raises(ValueError, match=message):
        builder.build_snapshot(
            l3_path,
            d1_path,
            expected_sources=sources,
            expected_joined_rows=len(rows),
            expected_labeled_rows=len(rows),
        )


def test_target_schema_hash_and_floor_failures_are_undetermined() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, rows, config)

    bad_schema = copy.deepcopy(snapshot)
    bad_schema["schema"] = "wrong"
    assert target.measure(bad_schema, config=config)["decision"] == "UNDETERMINED"

    bad_hash = copy.deepcopy(snapshot)
    bad_hash["sources"][target.L3_KEY]["pre"]["sha256"] = "0" * 64
    bad_hash["sources"][target.L3_KEY]["post"]["sha256"] = "0" * 64
    result = target.measure(bad_hash, config=config)
    assert result["decision"] == "UNDETERMINED"
    assert "source sha256" in result["integrity_reasons"][0]

    high_floor_config = _config(target, rows, floor=2)
    high_floor_snapshot = _snapshot(target, rows, high_floor_config)
    result = target.measure(high_floor_snapshot, config=high_floor_config)
    assert result["decision"] == "UNDETERMINED"
    assert "floor" in result["integrity_reasons"][0]

    pre_window = copy.deepcopy(snapshot)
    pre_window["eligible_rows"][0]["day"] = 20220103
    pre_window["eligible_rows"][0]["t0"] = "20220103090000"
    result = target.measure(pre_window, config=config)
    assert result["decision"] == "UNDETERMINED"
    assert "discovery window" in result["integrity_reasons"][0]

    shuffled = copy.deepcopy(snapshot)
    shuffled["eligible_rows"] = [shuffled["eligible_rows"][1], shuffled["eligible_rows"][0], *shuffled["eligible_rows"][2:]]
    result = target.measure(shuffled, config=config)
    assert result["decision"] == "UNDETERMINED"
    assert "sorted by (code,day,off,t0)" in result["integrity_reasons"][0]

def test_target_failures_remain_fail_closed_under_python_optimized_mode() -> None:
    code = (
        "import importlib.util,json;"
        "spec=importlib.util.spec_from_file_location('target','scripts/g005_c1_time_shift.py');"
        "module=importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(module);"
        "print(json.dumps(module.measure({})))"
    )

    completed = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["decision"] == "UNDETERMINED"
    assert result["integrity_reasons"] == ["snapshot shape is not the sealed G005-C1 input shape"]


def test_target_normalizes_scale_shaped_rows_linearly_and_rejects_duplicate_keys() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = [
        {
            "code": f"{index:06d}",
            "day": 20220323 if index % 2 == 0 else 20230103,
            "off": index,
            "t0": f"{index:06d}",
            "year": 2022 if index % 2 == 0 else 2023,
            "y": float(index % 4),
            "b16": index % 2,
            "b37": (index // 2) % 2,
            "b38": (index // 3) % 2,
        }
        for index in range(20_000)
    ]
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, rows, config)

    normalized = target._normalize_rows(snapshot["eligible_rows"], config, snapshot["row_flow"])

    assert len(normalized) == len(rows)
    source = (ROOT / "scripts" / "g005_c1_time_shift.py").read_text(encoding="utf-8")
    assert "rows = rows +" not in source
    assert "seen_keys" not in source

    duplicate_rows = [*rows[:-1], dict(rows[0])]
    duplicate_config = _config(target, duplicate_rows, floor=1)
    duplicate_snapshot = _snapshot(target, duplicate_rows, duplicate_config)
    duplicate_snapshot["row_flow"]["eligible_by_year"] = {
        str(year): sum(1 for row in duplicate_rows if row["year"] == year)
        for year in target.YEARS
    }
    with pytest.raises(KeyError) as excinfo:
        target._normalize_rows(
            duplicate_snapshot["eligible_rows"],
            duplicate_config,
            duplicate_snapshot["row_flow"],
        )
    assert excinfo.value.args[0] == (target.FAIL_SENTINEL, "eligible rows contain duplicate (code,day,off,t0) keys")


def test_target_reraises_accidental_key_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, rows, config)

    def accidental_key_error(_rows: object) -> object:
        raise KeyError("accidental")

    monkeypatch.setattr(target, "_row_arrays", accidental_key_error)

    with pytest.raises(KeyError) as excinfo:
        target.measure(snapshot, config=config)

    assert excinfo.value.args[0] == "accidental"


def test_randomized_hot_paths_use_linear_cons_accumulation_on_production_shape() -> None:
    target = load_script("g005_c1_time_shift.py")
    source = (ROOT / "scripts" / "g005_c1_time_shift.py").read_text(encoding="utf-8")
    forbidden = (
        "results = results +",
        "source_results = source_results +",
        "replicate_results = replicate_results +",
        "sampled_days = sampled_days +",
        "sampled_indices = sampled_indices +",
        "positions = positions +",
        "draw_values = draw_values +",
        "annual_results = annual_results +",
        "groups = groups +",
        "twisted = twisted +",
        "current_group = current_group +",
    )
    assert all(pattern not in source for pattern in forbidden)
    assert "tuple(index for index, row_code in enumerate(arrays[\"code\"]) if row_code != code)" not in source
    ordered_body = source.split("def _ordered_groups", 1)[1].split("def _placebo_support", 1)[0]
    twist_body = source.split("def _mt_twist", 1)[1].split("def _mt_uint32", 1)[0]
    assert "sorted(" not in ordered_body
    assert "twisted = twisted +" not in twist_body

    group_count = 5_000
    rows = [
        {
            "code": f"{index:06d}",
            "day": 20220323,
            "off": leg,
            "t0": f"{index:06d}{leg}",
            "year": 2022,
            "y": float((index + leg) % 4),
            "b16": leg,
            "b37": (index + leg) % 2,
            "b38": (index // 2 + leg) % 2,
        }
        for index in range(group_count)
        for leg in (0, 1)
    ]
    groups = target._ordered_groups(rows)
    state, shifted37, shifted38, calls = target._shift_pressure_bits(rows, groups, target._rng_state(target.PLACEBO_SEED))
    assert len(shifted37) == len(rows)
    assert len(shifted38) == len(rows)
    assert calls == group_count

    day_blocks = {20220323 + index: (index,) for index in range(20_000)}
    state, indices, days = target._bootstrap_sample_indices(day_blocks, target._rng_state(target.BOOTSTRAP_SEED))
    assert len(indices) == len(day_blocks)
    assert len(days) == len(day_blocks)





@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("code", None, "code must be a nonempty string"),
        ("code", 123, "code must be a nonempty string"),
        ("code", "", "code must be a nonempty string"),
        ("t0", None, "t0 must be a nonempty string"),
        ("t0", 123, "t0 must be a nonempty string"),
        ("t0", "", "t0 must be a nonempty string"),
    ],
)
def test_target_rejects_null_numeric_or_empty_identity_rows(
    field: str,
    bad_value: object,
    message: str,
) -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, copy.deepcopy(rows), config)
    snapshot["eligible_rows"][0][field] = bad_value

    result = target.measure(snapshot, config=config)

    assert result["decision"] == "UNDETERMINED"
    assert message in result["integrity_reasons"][0]

@pytest.mark.parametrize(
    ("field", "bad_value", "message"),
    [
        ("day", "20220323", "day must be an integer"),
        ("year", "2022", "year must be an integer"),
        ("off", "0", "off must be an integer"),
    ],
)
def test_target_rejects_numeric_string_day_year_and_off(
    field: str,
    bad_value: object,
    message: str,
) -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, copy.deepcopy(rows), config)
    snapshot["eligible_rows"][0][field] = bad_value

    result = target.measure(snapshot, config=config)

    assert result["decision"] == "UNDETERMINED"
    assert result["integrity_reasons"] == [message]




def test_target_rejects_row_flow_remainder_tamper() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _decision_rows(pass_case=True)
    config = _config(target, rows, floor=1)
    snapshot = _snapshot(target, copy.deepcopy(rows), config)
    snapshot["row_flow"]["unlabeled_or_out_of_window_rows"] = 1

    result = target.measure(snapshot, config=config)

    assert result["decision"] == "UNDETERMINED"
    assert "unlabeled_or_out_of_window_rows" in result["integrity_reasons"][0]


def test_nearest_rank_boundaries_and_interaction_formula() -> None:
    target = load_script("g005_c1_time_shift.py")
    assert target._nearest_rank([10, 20, 30, 40], 0.0) == 10
    assert target._nearest_rank([10, 20, 30, 40], 0.25) == 10
    assert target._nearest_rank([10, 20, 30, 40], 0.26) == 20
    assert target._nearest_rank([10, 20, 30, 40], 0.95) == 40
    assert target._nearest_rank([10, 20, 30, 40], 1.0) == 40
    assert target._interaction_from_values(
        [1.0, 2.0, 3.0, 10.0],
        [0, 0, 1, 1],
        [0, 1, 0, 1],
    ) == pytest.approx(10.0 - 3.0 - 2.0 + 1.0)


def test_placebo_rng_is_deterministic_joint_and_skips_singletons() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = [
        {"code": "A", "day": 20220323, "off": 0, "t0": "0", "year": 2022, "y": 0.0, "b16": 0, "b37": 0, "b38": 1},
        {"code": "A", "day": 20220323, "off": 1, "t0": "1", "year": 2022, "y": 0.0, "b16": 0, "b37": 1, "b38": 0},
        {"code": "A", "day": 20220323, "off": 2, "t0": "2", "year": 2022, "y": 0.0, "b16": 1, "b37": 1, "b38": 1},
        {"code": "B", "day": 20220323, "off": 0, "t0": "0", "year": 2022, "y": 0.0, "b16": 1, "b37": 0, "b38": 0},
    ]
    groups = target._ordered_groups(rows)

    python_rng = random.Random(7)
    expected_offset = python_rng.randrange(1, 3)
    rng = target._rng_state(7)
    rng, shifted37, shifted38, calls = target._shift_pressure_bits(rows, groups, rng)
    assert calls == 1
    assert target._placebo_support(groups) == (0, 1, 2)
    assert [shifted37[index] for index in (0, 1, 2)] == [
        rows[(position - expected_offset) % 3]["b37"] for position in range(3)
    ]
    assert [shifted38[index] for index in (0, 1, 2)] == [
        rows[(position - expected_offset) % 3]["b38"] for position in range(3)
    ]
    rng, optimized_next = target._rng_randrange(rng, 10_000)
    assert optimized_next == python_rng.randrange(10_000)

    first = target._shift_pressure_bits(rows, groups, target._rng_state(7))[1:3]
    second = target._shift_pressure_bits(rows, groups, target._rng_state(7))[1:3]
    assert first == second


def test_placebo_vectorized_source_indices_match_naive_and_rng_stream() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _reference_rows()
    groups = target._ordered_groups(rows)
    base_indices = tuple(range(len(rows)))
    shiftable_groups = target._shiftable_group_arrays(groups)

    optimized_rng = target._rng_state(17)
    optimized_rng, source_indices, calls = target._placebo_source_indices(base_indices, shiftable_groups, optimized_rng)

    naive_rng = target._rng_state(17)
    naive_rng, shifted37, shifted38, naive_calls = target._shift_pressure_bits(rows, groups, naive_rng)
    arrays = target._row_arrays(rows)

    assert calls == naive_calls
    assert [arrays["b37"][index] for index in source_indices] == shifted37
    assert [arrays["b38"][index] for index in source_indices] == shifted38
    python_rng = random.Random(17)
    for group in shiftable_groups:
        python_rng.randrange(1, len(group))
    optimized_rng, optimized_next = target._rng_randrange(optimized_rng, 10_000)
    assert optimized_next == python_rng.randrange(10_000)


def test_bootstrap_sample_uses_whole_day_multiplicity() -> None:
    target = load_script("g005_c1_time_shift.py")

    blocks = {20220323: (0, 1), 20220324: (2, 3)}
    python_rng = random.Random(1)
    expected_days = [sorted(blocks)[python_rng.randrange(2)] for _ in range(2)]
    rng, indices, days = target._bootstrap_sample_indices(blocks, target._rng_state(1))
    assert days == expected_days
    assert indices == [index for day in expected_days for index in blocks[day]]


def test_bootstrap_day_positions_match_python_randrange_stream() -> None:
    target = load_script("g005_c1_time_shift.py")
    optimized_rng = target._rng_state(23)
    optimized_rng, positions = target._bootstrap_sample_day_positions(3, optimized_rng)

    naive_rng = random.Random(23)
    assert list(positions) == [naive_rng.randrange(3) for _ in range(3)]
    optimized_rng, optimized_next = target._rng_randrange(optimized_rng, 10_000)
    assert optimized_next == naive_rng.randrange(10_000)


def test_custom_mt_randrange_matches_python_random_for_production_seeds_and_cardinalities() -> None:
    target = load_script("g005_c1_time_shift.py")
    seeds = (
        target.PLACEBO_SEED,
        target.BOOTSTRAP_SEED,
        1,
        7,
        17,
        23,
        101,
        202,
    )
    cardinalities = (1, 2, 3, 4, 5, 8, 16, 37, 400, 20_000, 862_932)

    for seed in seeds:
        state = target._rng_state(seed)
        python_rng = random.Random(seed)
        for _ in range(3):
            for limit in cardinalities:
                state, value = target._rng_randrange(state, limit)
                assert value == python_rng.randrange(limit)
            for stop in (2, 3, 8, 37):
                state, value = target._rng_randrange(state, 1, stop)
                assert value == python_rng.randrange(1, stop)


def test_optimized_randomized_helpers_and_measure_fields_match_naive_reference() -> None:
    target = load_script("g005_c1_time_shift.py")
    rows = _reference_rows()
    config = _config(target, rows, floor=1, reps=7, draws=5, placebo_seed=101, bootstrap_seed=202)
    arrays = target._row_arrays(rows)

    placebo = target._placebo_thresholds(rows, config, arrays)
    naive_placebo = _naive_placebo_thresholds(target, rows, config)
    assert {key: value for key, value in placebo.items() if key != "q95_pp"} == {
        key: value for key, value in naive_placebo.items() if key != "q95_pp"
    }
    assert placebo["q95_pp"] == pytest.approx(naive_placebo["q95_pp"])

    bootstrap = target._bootstrap_cis(rows, config, arrays)
    naive_bootstrap = _naive_bootstrap_cis(target, rows, config)
    for _, bit in target.PAIRS:
        pair_key = target._pair_key(bit)
        for year in target.YEARS:
            assert bootstrap[pair_key][str(year)] == pytest.approx(naive_bootstrap[pair_key][str(year)])

    leave_one = target._leave_one_code_out(rows, arrays)
    naive_leave_one = _naive_leave_one_code_out(target, rows)
    for _, bit in target.PAIRS:
        pair_key = target._pair_key(bit)
        assert leave_one[pair_key]["n_codes"] == naive_leave_one[pair_key]["n_codes"]
        assert leave_one[pair_key]["finite_exclusions"] == naive_leave_one[pair_key]["finite_exclusions"]
        assert leave_one[pair_key]["undefined_codes"] == naive_leave_one[pair_key]["undefined_codes"]
        assert leave_one[pair_key]["min"] == pytest.approx(naive_leave_one[pair_key]["min"])
        assert leave_one[pair_key]["max"] == pytest.approx(naive_leave_one[pair_key]["max"])

    result = target.measure(_snapshot(target, rows, config), config=config)
    assert result["decision"] in {"PASS", "KILL"}
    assert result["placebo"]["q95_pp"] == pytest.approx(naive_placebo["q95_pp"])
    for _, bit in target.PAIRS:
        pair_key = target._pair_key(bit)
        for year in target.YEARS:
            assert result["bootstrap_ci_pp"][pair_key][str(year)] == pytest.approx(
                naive_bootstrap[pair_key][str(year)]
            )
    assert result["leave_one_code_out_range_pp"]["16x37"]["min"] == pytest.approx(naive_leave_one["16x37"]["min"])

def test_large_scale_leave_one_code_out_matches_naive_without_rescans() -> None:
    target = load_script("g005_c1_time_shift.py")
    cells = [(0, 0, 1.0), (0, 1, 2.0), (1, 0, 4.0), (1, 1, 8.0)]
    rows = [
        {
            "code": f"{code_index:05d}",
            "day": day,
            "off": cell_index + year_offset * 10,
            "t0": f"{day}{code_index:05d}{cell_index}",
            "year": year,
            "y": y + code_index * 0.01 + year_offset,
            "b16": b16,
            "b37": bit,
            "b38": 1 - bit,
        }
        for code_index in range(500)
        for year_offset, (year, day) in enumerate(((2022, 20220323), (2023, 20230103)))
        for cell_index, (b16, bit, y) in enumerate(cells)
    ]
    arrays = target._row_arrays(rows)

    optimized = target._leave_one_code_out(rows, arrays)
    naive = _naive_leave_one_code_out(target, rows)

    assert optimized["16x37"]["n_codes"] == naive["16x37"]["n_codes"] == 500
    assert optimized["16x37"]["finite_exclusions"] == naive["16x37"]["finite_exclusions"]
    assert optimized["16x37"]["undefined_codes"] == naive["16x37"]["undefined_codes"]
    assert optimized["16x37"]["min"] == pytest.approx(naive["16x37"]["min"])
    assert optimized["16x37"]["max"] == pytest.approx(naive["16x37"]["max"])
    assert optimized["16x38"]["n_codes"] == naive["16x38"]["n_codes"] == 500
    assert optimized["16x38"]["finite_exclusions"] == naive["16x38"]["finite_exclusions"]
    assert optimized["16x38"]["undefined_codes"] == naive["16x38"]["undefined_codes"]
    assert optimized["16x38"]["min"] == pytest.approx(naive["16x38"]["min"])
    assert optimized["16x38"]["max"] == pytest.approx(naive["16x38"]["max"])



def test_measure_decisions_pass_kill_and_undefined_precedence() -> None:
    target = load_script("g005_c1_time_shift.py")

    pass_rows = _decision_rows(pass_case=True)
    pass_config = _config(target, pass_rows, floor=1, reps=1, draws=1)
    pass_result = target.measure(_snapshot(target, pass_rows, pass_config), config=pass_config)
    assert pass_result["decision"] == "PASS"
    assert pass_result["observed_interactions_pp"]["16x37"]["pooled"] == pytest.approx(20.0)
    assert pass_result["decision_diagnostics"]["pair_pass"] == {"16x37": True, "16x38": True}

    kill_rows = _decision_rows(pass_case=False)
    kill_config = _config(target, kill_rows, floor=1, reps=1, draws=1)
    kill_result = target.measure(_snapshot(target, kill_rows, kill_config), config=kill_config)
    assert kill_result["decision"] == "KILL"

    undefined_rows = _undefined_placebo_rows()
    undefined_config = _config(target, undefined_rows, floor=1, reps=1, draws=1)
    undefined_result = target.measure(_snapshot(target, undefined_rows, undefined_config), config=undefined_config)
    assert undefined_result["decision"] == "UNDETERMINED"
    assert "placebo replicate" in undefined_result["integrity_reasons"][0]


def test_target_declares_literal_plain_json_main_input() -> None:
    source = (ROOT / "scripts" / "g005_c1_time_shift.py").read_text(encoding="utf-8")
    expected = (
        'with open("docs/research/condition_research/research_runs/'
        'alpha_restart_20260710/g005/c1_input.json", mode="r", encoding="utf-8") as handle:'
    )
    assert expected in source
    assert "gzip" not in source
    assert "_production_input_path" not in source


def test_target_main_emits_mocked_measure_json(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = load_script("g005_c1_time_shift.py")
    payload = {"schema": target.INPUT_SCHEMA, "eligible_rows": []}
    captured: dict[str, object] = {}

    def fake_measure(
        snapshot: object,
        *,
        config: object = target.PRODUCTION_CONFIG,
    ) -> dict[str, object]:
        captured["snapshot"] = snapshot
        captured["config"] = config
        return {"schema": target.RESULT_SCHEMA, "decision": "UNDETERMINED", "integrity_reasons": []}

    monkeypatch.setattr(target, "measure", fake_measure)

    target.main(payload)

    assert captured == {"snapshot": payload, "config": target.PRODUCTION_CONFIG}
    result = target.json.loads(capsys.readouterr().out)
    assert result == {
        "schema": target.RESULT_SCHEMA,
        "decision": "UNDETERMINED",
        "integrity_reasons": [],
    }
