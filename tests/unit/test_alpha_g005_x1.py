from __future__ import annotations

import ast
import copy
import csv
import hashlib
import inspect
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


builder = _load("g005_x1_builder_test", ROOT / "scripts/build_g005_x1_input.py")
measure = _load("g005_x1_measure_test", ROOT / "scripts/g005_x1_competing_risk.py")

def test_builder_contract_discovery_window_matches_sealed_target_without_materializing() -> None:
    loaded_builder = _load("g005_x1_builder_contract_window_test", ROOT / "scripts/build_g005_x1_input.py")
    prereg_window = {"start": "2022-03-23", "end": "2023-12-31"}
    assert measure.contract_descriptor()["discovery_window"] == prereg_window
    assert loaded_builder.contract_descriptor()["discovery_window"] == prereg_window


def _write_csv(tmp_path: Path, slot: str, group: str, rows: list[dict[str, str]], fieldnames=None):
    fieldnames = list(fieldnames or builder.REQUIRED_FIELDS)
    path = tmp_path / f"{slot}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    data = path.read_bytes()
    return builder.SourceSpec(
        slot=slot,
        group=group,
        path=path.as_posix(),
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        raw_rows=len(rows),
    )


def test_builder_filters_by_buy_date_before_row_output_and_requires_exact_field_names(tmp_path: Path) -> None:
    rows = [
        {"매수시간": "20220103090000", "매도시간": "20220103092900", "매도조건": "익절", "수익률": "1.25"},
        {"매수시간": "20240103090000", "매도시간": "not-a-time", "매도조건": "2024행", "수익률": "nan"},
    ]
    source = _write_csv(tmp_path, "RR8_12", "RR8", rows)
    snapshot = builder.build_snapshot((source,), {2022: 1, 2023: 0})
    assert snapshot["rows"] == [
        {
            "group": "RR8",
            "slot": "RR8_12",
            "day": "20220103",
            "buy_time": "20220103090000",
            "sell_time": "20220103092900",
            "condition": "익절",
            "y": 1.25,
        }
    ]
    bad = _write_csv(tmp_path, "BAD", "RR8", rows, fieldnames=("매수시간", "매도시간", "매도조건"))
    with pytest.raises(builder.X1InputError, match="required CSV field"):
        builder.build_snapshot((bad,), {2022: 1, 2023: 0})


def test_builder_preserves_rr8_slots_without_deduplication(tmp_path: Path) -> None:
    row = {"매수시간": "20220103090000", "매도시간": "20220103092900", "매도조건": "손절", "수익률": "-1"}
    left = _write_csv(tmp_path, "RR8_12", "RR8", [row])
    right = _write_csv(tmp_path, "RR8_0", "RR8", [row])
    snapshot = builder.build_snapshot((left, right), {2022: 2, 2023: 0})
    assert [item["slot"] for item in snapshot["rows"]] == ["RR8_12", "RR8_0"]
    assert len(snapshot["rows"]) == 2


def test_builder_source_drift_and_raw_count_mismatch_fail_closed(tmp_path: Path) -> None:
    source = _write_csv(
        tmp_path,
        "RR8_12",
        "RR8",
        [{"매수시간": "20220103090000", "매도시간": "20220103092900", "매도조건": "마감", "수익률": "1"}],
    )
    wrong_count = builder.SourceSpec(**{**source.descriptor(), "raw_rows": source.raw_rows + 1})
    with pytest.raises(builder.X1InputError, match="source drift/count mismatch"):
        builder.build_snapshot((wrong_count,), {2022: 1, 2023: 0})
    wrong_hash = builder.SourceSpec(**{**source.descriptor(), "sha256": "0" * 64})
    with pytest.raises(builder.X1InputError, match="source drift/count mismatch"):
        builder.build_snapshot((wrong_hash,), {2022: 1, 2023: 0})


def test_deterministic_one_shot_writer(tmp_path: Path) -> None:
    source = _write_csv(tmp_path, "EMPTY", "RR8", [])
    snapshot = builder.build_snapshot((source,), {2022: 0, 2023: 0})
    out = tmp_path / "g005" / "x1_input.json"
    builder.write_snapshot(out, snapshot)
    first = out.read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        builder.write_snapshot(out, snapshot)
    assert out.read_text(encoding="utf-8") == first


def _fixture_sources():
    return (
        measure.SourceSpec("RR8_12", "RR8", "C:/fixture/rr8.csv", "a" * 64, 10, 10),
        measure.SourceSpec("GPTAUTH_G8", "GPTAUTH_G8", "C:/fixture/gpt.csv", "b" * 64, 10, 10),
    )


def _row(group: str, slot: str, day: str, y: float, condition: str, sell_hms: str = "092900") -> dict[str, object]:
    return {
        "group": group,
        "slot": slot,
        "day": day,
        "buy_time": day + "090000",
        "sell_time": day + sell_hms,
        "condition": condition,
        "y": y,
    }


def _snapshot(rows: list[dict[str, object]], *, sources=None, expected=None) -> dict[str, object]:
    sources = tuple(sources or _fixture_sources())
    if expected is None:
        expected = {2022: sum(1 for row in rows if str(row["day"]).startswith("2022")), 2023: sum(1 for row in rows if str(row["day"]).startswith("2023"))}
    return {
        "schema": measure.SCHEMA,
        "contract": measure.contract_descriptor(sources, expected),
        "sources": [{**measure._source_descriptor(source), "pre": measure._source_identity(source), "post": measure._source_identity(source)} for source in sources],
        "counts": measure._count_record(rows, sources, expected),
        "rows": rows,
        "side_effect_counters": dict(measure.ZERO_SIDE_EFFECT_COUNTERS),
    }

def _measure_snapshot(snapshot: dict[str, object], **kwargs):
    counts = snapshot["counts"]
    expected = {2022: counts["expected"]["2022"], 2023: counts["expected"]["2023"]}
    return measure._measure_non_authoritative_for_tests(snapshot, source_files=_fixture_sources(), expected_counts=expected, **kwargs)


def _measure_rows(rows: list[dict[str, object]], **kwargs):
    return _measure_snapshot(_snapshot(rows), **kwargs)

def _composition_rows(rr8_forced: float, gpt_forced: float) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for day in ("20220103", "20230103"):
        rows.extend(
            [
                _row("RR8", "RR8_12", day, rr8_forced, "마감"),
                _row("RR8", "RR8_12", day, rr8_forced, "마감"),
                _row("RR8", "RR8_12", day, 0.0, "손절"),
                _row("GPTAUTH_G8", "GPTAUTH_G8", day, gpt_forced, "마감"),
                _row("GPTAUTH_G8", "GPTAUTH_G8", day, 0.0, "손절"),
                _row("GPTAUTH_G8", "GPTAUTH_G8", day, 0.0, "손절"),
            ]
        )
    return rows


def test_unicode_substring_precedence_and_forced_cap_time_are_exact() -> None:
    assert measure.classify_cause("20220103092900", "손절 강제") == "forced_cap"
    assert measure.classify_cause("20220103092900", "마감 손절") == "forced_cap"
    assert measure.classify_cause("20220103093000", "손절") == "forced_cap"
    assert measure.classify_cause("20220103092900", "최저가이탈 트레일링") == "stop_loss"
    assert measure.classify_cause("20220103092900", "트레일링 익절") == "trailing"
    assert measure.classify_cause("20220103092900", "보유시간 익절") == "time_exit"
    assert measure.classify_cause("20220103092900", "익절") == "profit_take"
    assert measure.classify_cause("20220103092900", " 손절 ") == "stop_loss"


def test_standardization_removes_composition_and_passes_with_same_annual_signs() -> None:
    result = _measure_rows(_composition_rows(10.0, 8.0), bootstrap_draws=3)
    stats = result["statistics"]
    assert result["decision"] == "PASS"
    assert stats["raw_contrast"] == pytest.approx(4.0)
    assert stats["standardized_contrast"] == pytest.approx(1.0)
    assert stats["residual_ratio"] == pytest.approx(0.25)
    assert stats["pooled_weights"]["forced_cap"] == pytest.approx(0.5)
    assert stats["pooled_weights"]["stop_loss"] == pytest.approx(0.5)


def test_missing_positive_weight_support_is_undetermined_before_kill() -> None:
    rows = []
    for day in ("20220103", "20230103"):
        rows.append(_row("RR8", "RR8_12", day, 10.0, "마감"))
        rows.append(_row("GPTAUTH_G8", "GPTAUTH_G8", day, 0.0, "손절"))
    result = _measure_rows(rows, bootstrap_draws=1)
    assert result["decision"] == "UNDETERMINED"
    assert any(reason.startswith("missing_positive_weight_cause_support") for reason in result["decision_diagnostics"]["undetermined_reasons"])


def test_raw_zero_and_annual_zero_are_undetermined() -> None:
    raw_zero_rows = []
    for day in ("20220103", "20230103"):
        raw_zero_rows.append(_row("RR8", "RR8_12", day, 1.0, "마감"))
        raw_zero_rows.append(_row("GPTAUTH_G8", "GPTAUTH_G8", day, 1.0, "마감"))
    raw_zero = _measure_rows(raw_zero_rows, bootstrap_draws=1)
    assert raw_zero["decision"] == "UNDETERMINED"
    assert "raw_contrast_zero" in raw_zero["decision_diagnostics"]["undetermined_reasons"]

    annual_zero_rows = [
        _row("RR8", "RR8_12", "20220103", 1.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20220103", 1.0, "마감"),
        _row("RR8", "RR8_12", "20230103", 3.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20230103", 1.0, "마감"),
    ]
    annual_zero = _measure_rows(annual_zero_rows, bootstrap_draws=1)
    assert annual_zero["decision"] == "UNDETERMINED"
    assert "annual_raw_contrast_zero:2022" in annual_zero["decision_diagnostics"]["undetermined_reasons"]


def test_any_undefined_bootstrap_replicate_is_undetermined() -> None:
    rows = [
        _row("RR8", "RR8_12", "20220103", 10.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20220103", 8.0, "마감"),
        _row("RR8", "RR8_12", "20220103", 0.0, "트레일링"),
        _row("RR8", "RR8_12", "20220104", 10.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20220104", 8.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20220104", 0.0, "트레일링"),
    ] + _composition_rows(10.0, 8.0)[6:]
    result = _measure_rows(rows, bootstrap_plan=[{2022: [0, 0], 2023: [0]}])
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["undetermined_reasons"][0].startswith("bootstrap_undefined_replicate:0")



def test_bootstrap_splitmix_stream_draws_with_replacement_for_two_block_years() -> None:
    blocks = {
        2022: [[{"day": "20220103"}], [{"day": "20220104"}]],
        2023: [[{"day": "20230103"}]],
    }
    draws = [
        [row["day"] for row in measure._draw_replicate(blocks, measure.BOOTSTRAP_SEED, replicate)[:2]]
        for replicate in range(64)
    ]
    assert any(draw[0] == draw[1] for draw in draws)
    assert any(draw[0] != draw[1] for draw in draws)
    assert measure._draw_replicate(blocks, measure.BOOTSTRAP_SEED, 7) == measure._draw_replicate(blocks, measure.BOOTSTRAP_SEED, 7)


def test_bootstrap_splitmix_stream_has_stable_balanced_black_box_distribution() -> None:
    blocks = {
        2022: [[{"bucket": "left"}], [{"bucket": "right"}]],
        2023: [[{"bucket": "fixed"}]],
    }
    first_draws = [
        measure._draw_replicate(blocks, 777, replicate)[0]["bucket"]
        for replicate in range(512)
    ]
    left = first_draws.count("left")
    right = first_draws.count("right")
    assert left + right == 512
    assert 200 <= left <= 312
    assert 200 <= right <= 312

def test_ratio_boundary_point_eight_is_kill() -> None:
    result = _measure_rows(_composition_rows(7.0, -1.0), bootstrap_draws=2)
    assert result["statistics"]["raw_contrast"] == pytest.approx(5.0)
    assert result["statistics"]["standardized_contrast"] == pytest.approx(4.0)
    assert result["statistics"]["residual_ratio"] == pytest.approx(0.8)
    assert result["decision"] == "KILL"
    assert "residual_ratio_ge_0.8" in result["decision_diagnostics"]["kill_reasons"]


def test_annual_sign_conflict_is_kill_after_undetermined_checks_pass() -> None:
    rows = [
        _row("RR8", "RR8_12", "20220103", 5.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20220103", 1.0, "마감"),
        _row("RR8", "RR8_12", "20230103", 1.0, "마감"),
        _row("GPTAUTH_G8", "GPTAUTH_G8", "20230103", 2.0, "마감"),
    ]
    result = _measure_rows(rows, bootstrap_draws=1)
    assert result["decision"] == "KILL"
    assert result["decision_diagnostics"]["undetermined_reasons"] == []
    assert "annual_sign_conflict" in result["decision_diagnostics"]["kill_reasons"]


def test_source_drift_and_count_mismatch_return_undetermined_not_pass_or_kill() -> None:
    snapshot = _snapshot(_composition_rows(10.0, 8.0))
    drifted = copy.deepcopy(snapshot)
    drifted["sources"][0]["post"]["sha256"] = "0" * 64
    assert measure._measure_non_authoritative_for_tests(drifted, source_files=_fixture_sources(), expected_counts={2022: 6, 2023: 6}, bootstrap_draws=1)["decision"] == "UNDETERMINED"
    mismatched = copy.deepcopy(snapshot)
    mismatched["counts"]["total"] += 1
    result = measure._measure_non_authoritative_for_tests(mismatched, source_files=_fixture_sources(), expected_counts={2022: 6, 2023: 6}, bootstrap_draws=1)
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["undetermined_reasons"][0].startswith("integrity_issue")
    assert result["decision_diagnostics"]["undetermined_reasons"][0] == "integrity_issue:count descriptor mismatch"


def test_public_measure_has_no_overrides_and_private_helper_marks_results() -> None:
    assert list(inspect.signature(measure.measure).parameters) == ["snapshot"]
    with pytest.raises(TypeError):
        measure.measure({}, bootstrap_draws=1)
    public_result = measure.measure({})
    assert "non_authoritative_test_marker" not in public_result
    assert public_result["decision"] == "UNDETERMINED"

    private_result = _measure_rows(_composition_rows(10.0, 8.0), bootstrap_draws=1)
    assert private_result["non_authoritative_test_marker"] == measure.NON_AUTHORITATIVE_TEST_MARKER


def test_unrelated_runtime_error_is_not_converted_to_undetermined(monkeypatch) -> None:
    sealed_input = json.loads((ROOT / measure.INPUT_PATH).read_text(encoding="utf-8"))

    def raise_runtime_error(rows):
        raise RuntimeError("injected unrelated failure")

    monkeypatch.setattr(measure, "compute_statistics", raise_runtime_error)
    with pytest.raises(RuntimeError, match="injected unrelated failure"):
        measure.measure(sealed_input)


def test_side_effect_counters_are_required_exact_zero_field() -> None:
    snapshot = _snapshot(_composition_rows(10.0, 8.0))
    missing = copy.deepcopy(snapshot)
    del missing["side_effect_counters"]
    result = measure._measure_non_authoritative_for_tests(
        missing,
        source_files=_fixture_sources(),
        expected_counts={2022: 6, 2023: 6},
        bootstrap_draws=1,
    )
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["undetermined_reasons"][0] == "integrity_issue:missing or nonzero side-effect counters"

    nonzero = copy.deepcopy(snapshot)
    nonzero["side_effect_counters"]["db_writes"] = 1
    result = measure._measure_non_authoritative_for_tests(
        nonzero,
        source_files=_fixture_sources(),
        expected_counts={2022: 6, 2023: 6},
        bootstrap_draws=1,
    )
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["undetermined_reasons"][0] == "integrity_issue:missing or nonzero side-effect counters"

    extra_key = copy.deepcopy(snapshot)
    extra_key["side_effect_counters"]["unexpected"] = 0
    result = measure._measure_non_authoritative_for_tests(
        extra_key,
        source_files=_fixture_sources(),
        expected_counts={2022: 6, 2023: 6},
        bootstrap_draws=1,
    )
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["undetermined_reasons"][0] == "integrity_issue:missing or nonzero side-effect counters"


def test_optimized_python_cannot_bypass_fail_closed_malformed_input() -> None:
    code = (
        "import importlib.util, json, pathlib;"
        "path = pathlib.Path('scripts/g005_x1_competing_risk.py');"
        "spec = importlib.util.spec_from_file_location('g005_x1_measure_o', path);"
        "module = importlib.util.module_from_spec(spec);"
        "spec.loader.exec_module(module);"
        "print(json.dumps(module.measure({}), sort_keys=True))"
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
    assert result["decision_diagnostics"]["undetermined_reasons"][0] == "integrity_issue:snapshot schema mismatch: None"


def test_main_uses_scanner_valid_literal_json_input_and_production_constants_are_immutable() -> None:
    source = (ROOT / "scripts/g005_x1_competing_risk.py").read_text(encoding="utf-8")
    expected_open = (
        'with open("docs/research/condition_research/research_runs/alpha_restart_20260710/g005/x1_input.json", mode="r", encoding="utf-8") as handle:'
    )
    assert expected_open in source
    tree = ast.parse(source)
    opens = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"]
    assert len(opens) == 1
    call = opens[0]
    assert len(call.args) == 1 and isinstance(call.args[0], ast.Constant) and call.args[0].value == measure.INPUT_PATH
    assert [keyword.arg for keyword in call.keywords] == ["mode", "encoding"]
    assert [keyword.value.value for keyword in call.keywords if isinstance(keyword.value, ast.Constant)] == ["r", "utf-8"]
    executable_annotations = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign)
        or isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and (
            node.returns is not None
            or any(
                argument.annotation is not None
                for argument in (
                    *node.args.posonlyargs,
                    *node.args.args,
                    *node.args.kwonlyargs,
                    *((node.args.vararg,) if node.args.vararg else ()),
                    *((node.args.kwarg,) if node.args.kwarg else ()),
                )
            )
        )
    ]
    assert executable_annotations == []
    assert measure.contract_descriptor()["discovery_window"]["start"] == "2022-03-23"
    sealed_input = json.loads((ROOT / measure.INPUT_PATH).read_text(encoding="utf-8"))
    assert sealed_input["contract"]["discovery_window"]["start"] == "2022-03-23"
    assert sealed_input["counts"]["expected"] == {"2022": 510, "2023": 1148, "total": 1658}
    assert len(sealed_input["rows"]) == 1658
    assert dict(measure.EXPECTED_FILTERED_COUNTS)[2022] == 510
    with pytest.raises(TypeError):
        measure.EXPECTED_FILTERED_COUNTS[0] = (2022, 1)
    with pytest.raises(TypeError):
        measure.SOURCE_FILES[0][0] = ("slot", "mutated")
    with pytest.raises(measure.X1MeasureError, match="diagnostic-message"):
        measure._fail("diagnostic-message")
