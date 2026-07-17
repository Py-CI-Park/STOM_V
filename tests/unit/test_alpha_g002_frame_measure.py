import ast
import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("g002_frame", ROOT / "scripts/u7_f0_frame_measure.py")
frame = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = frame
spec.loader.exec_module(frame)
HASH = "ab" * 32


def missing(reason):
    return {"status": "missing", "entry_price": None, "entry_time": None, "exit_price": None, "exit_time": None, "qty": None, "clause": None, "forced": False, "missing_reason": reason}


def cell(day, price, clause=1):
    return {"status": "matched", "entry_price": 100.0, "entry_time": day + "090000", "exit_price": price, "exit_time": day + "092800", "qty": 10, "clause": clause, "forced": False, "missing_reason": None}


def event(year, number, status="matched"):
    day = str(year) + "0103"
    identity = {"code": f"{number:06d}", "year": year, "day": day, "buy_time": day + "090000"}
    ledger = {"buy_price": 100.0, "buy_amount": 1000.0, "qty": 10, "sell_price": 107.0, "buy_timestamp": identity["buy_time"], "sell_timestamp": day + "092800"}
    if status == "engine_only":
        return {"identity": identity, "status": status, "reason": "no_l3", "ledger": ledger, "l3_net_ref": None, "branch": None, "cells": {key: missing("no_l3") for key in frame.CELL_KEYS}}
    if status == "excluded":
        return {"identity": identity, "status": status, "reason": "excluded", "ledger": ledger, "l3_net_ref": .01, "branch": 902, "cells": {key: missing("excluded") for key in frame.CELL_KEYS}}
    cells = {key: cell(day, 101.0) for key in frame.CELL_KEYS}
    cells["E1D1T1"] = cell(day, 105.0, 999999)
    return {"identity": identity, "status": "matched", "reason": None, "ledger": ledger, "l3_net_ref": .01, "branch": 905, "cells": cells}


def provenance(rows):
    def artifact(path):
        return {"path": path, "sha256": HASH, "size_bytes": 1}
    def physical(item):
        return {"pre": {"sha256": item["sha256"], "size_bytes": item["size_bytes"], "physical_id": f"{item['path']}:{item['size_bytes']}:{item['sha256']}"}, "post": {"sha256": item["sha256"], "size_bytes": item["size_bytes"], "physical_id": f"{item['path']}:{item['size_bytes']}:{item['sha256']}"}}
    matched = [row for row in rows if row["status"] == "matched"]
    reconciliation = [{"identity": row["identity"], "engine": {"ledger_sell_price": row["ledger"]["sell_price"], "ledger_sell_timestamp": row["ledger"]["sell_timestamp"], "cell_sell_price": row["cells"]["E1D1T1"]["exit_price"], "cell_sell_timestamp": row["cells"]["E1D1T1"]["exit_time"], "parity": False}, "l3": {"bank_exit_timestamp": row["cells"]["E0D0T0"]["exit_time"], "bank_clause": row["cells"]["E0D0T0"]["clause"], "cell_exit_timestamp": row["cells"]["E0D0T0"]["exit_time"], "cell_clause": row["cells"]["E0D0T0"]["clause"], "parity": True}} for row in matched]
    sources = {key: artifact(f"artifacts/{key}.json") for key in frame.SOURCES}
    authority = artifact("artifacts/source_authority.json")
    preregistration = artifact("docs/research/condition_research/plans/2026-07-16_g002_u7_f0_preregistration.md")
    launch = artifact("artifacts/launch.json")
    materializer = artifact("scripts/u7_f0_materialize.py")
    target = artifact("scripts/u7_f0_frame_measure.py")
    crosswalk = artifact(r"C:\sealed\identity_crosswalk.json")
    design_marker = artifact(r"C:\sealed\identity_design_marker.json")
    tick = {"path": r"C:\ticks.db", "sha256": HASH, "size_bytes": 1, "physical_id": f"C:\\ticks.db:1:{HASH}", "read_only": True, "query_only": True}
    tick_physical = {"sha256": tick["sha256"], "size_bytes": tick["size_bytes"], "physical_id": tick["physical_id"]}
    tick.update({"pre": dict(tick_physical), "post": dict(tick_physical)})
    descriptors = {**sources, "source_authority": authority, "preregistration": preregistration, "launch": launch, "materializer": materializer, "measurement_target": target, "identity_crosswalk": crosswalk, "design_marker": design_marker}
    physical_inputs = {key: physical(item) for key, item in descriptors.items()}
    physical_inputs["tick_db"] = {"pre": dict(tick_physical), "post": dict(tick_physical)}
    return {"schema": "u7-f0-provenance-v3", "source_authority": authority, "sources": sources, "preregistration": preregistration, "launch": launch, "cell_definition_binding": {"champion_sell_sha256": HASH, "equivalence_receipt_sha256": HASH, "champion_passport_sha256": HASH, "states": {"equivalence": "validated", "passport": "validated"}}, "physical_inputs": physical_inputs, "tick_db": tick, "materializer": materializer, "measurement_target": target, "identity_crosswalk": crosswalk, "design_marker": design_marker, "endpoint_reconciliation": reconciliation}


def snapshot(engine_only=0, excluded=0):
    rows = [event(2022, number) for number in range(101)] + [event(2023, number + 101) for number in range(197)]
    for number in range(engine_only): rows[-number - 1] = event(2023, 297 - number, "engine_only")
    for number in range(excluded): rows[-engine_only - number - 1] = event(2023, 297 - engine_only - number, "excluded")
    return {"contract": {"schema": frame.SCHEMA, "factor_coding": {"E0": "synthetic", "E1": "recorded", "D0": "l3_topbook", "D1": "engine_ladder3", "T0": "cap093000", "T1": "terminal092800"}, "years": [2022, 2023], "seed": frame.SEED, "replicates": frame.REPLICATES, "cell_net_support_pp": [-100, 100], "modeled_gap_support_pp": [-200, 200], "explanation_threshold": .5}, "provenance": provenance(rows), "flow": {"engine_rows": 298, "matched": 298 - engine_only - excluded, "engine_only": engine_only, "excluded": excluded, "offline_only": 0, "conservation_ok": True, "year_rows": {"2022": 101, "2023": 197}}, "events": rows, "offline_only": [], "side_effect_counters": {"engine_calls": 0, "db_writes": 0, "strategy_registrations": 0, "outcome_executions": 0}}


def test_retained_events_have_exact_status_specific_ranges():
    measured = frame.measure_events(snapshot(engine_only=1, excluded=1))
    assert len(measured) == 298
    assert measured[-1]["primary_range_pp"][0] < measured[-1]["primary_range_pp"][1]
    assert measured[-2]["primary_range_pp"][0] == measured[-2]["primary_range_pp"][1]
    assert measured[-1]["modeled_range_pp"] == (-200.0, 200.0)


def test_positive_nonforced_clauses_are_unbounded_but_zero_is_forced_only():
    value = snapshot()
    frame.validate_snapshot(value)
    arbitrary_clause = copy.deepcopy(value); arbitrary_clause["events"][0]["cells"]["E0D0T0"]["clause"] = 123456789
    arbitrary_l3 = arbitrary_clause["provenance"]["endpoint_reconciliation"][0]["l3"]; arbitrary_l3["cell_clause"] = 123456789; arbitrary_l3["parity"] = arbitrary_l3["bank_exit_timestamp"] == arbitrary_l3["cell_exit_timestamp"] and arbitrary_l3["bank_clause"] == arbitrary_l3["cell_clause"]
    frame.validate_snapshot(arbitrary_clause)
    zero_nonforced = copy.deepcopy(value); zero_nonforced["events"][0]["cells"]["E0D0T0"]["clause"] = 0
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(zero_nonforced)
    forced = copy.deepcopy(value); forced["events"][0]["cells"]["E0D0T0"].update({"forced": True, "clause": 0})
    forced_l3 = forced["provenance"]["endpoint_reconciliation"][0]["l3"]; forced_l3["cell_clause"] = 0; forced_l3["parity"] = forced_l3["bank_exit_timestamp"] == forced_l3["cell_exit_timestamp"] and forced_l3["bank_clause"] == forced_l3["cell_clause"]
    frame.validate_snapshot(forced)
    bad_clause = copy.deepcopy(value); bad_clause["events"][0]["cells"]["E0D0T0"]["clause"] = "cap"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(bad_clause)
    bad_parity = copy.deepcopy(value); bad_parity["provenance"]["endpoint_reconciliation"][0]["engine"]["parity"] = True
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(bad_parity)


def test_identified_counterexample_and_shared_sign_gate_are_conservative(monkeypatch):
    monkeypatch.setattr(frame, "REPLICATES", 2)
    result = frame.decide(snapshot(engine_only=10))
    assert result["decision"] == "UNDETERMINED"
    assert result["decision_diagnostics"]["identified_set_universally_passes"] is False
    ranges = {"2022": {"primary_gap_pp": (1, 1), "modeled_gap_pp": (1, 1)}, "2023": {"primary_gap_pp": (-1, -1), "modeled_gap_pp": (-1, -1)}, "pooled": {"primary_gap_pp": (1, 1), "modeled_gap_pp": (1, 1)}}
    assert frame._same_sign_gate(ranges, False) is False
@pytest.mark.parametrize(("ratio", "expected"), ((.49, False), (.5, True), (1.5, True), (1.51, False)))
def test_annual_ratio_boundaries_are_closed_and_not_pooled(ratio, expected):
    ranges = {"2022": {"primary_gap_pp": (10, 10), "modeled_gap_pp": (10 * ratio, 10 * ratio)}, "2023": {"primary_gap_pp": (20, 20), "modeled_gap_pp": (20 * ratio, 20 * ratio)}, "pooled": {"primary_gap_pp": (1, 1), "modeled_gap_pp": (1, 1)}}
    assert frame._same_sign_gate(ranges, True) is expected
    assert frame._same_sign_gate(ranges, False) is expected


def test_aggregate_explanation_uses_closeness_and_zero_primary_fails_safe():
    base = {"shapley_pp": {"E": 0, "D": 0, "T": 0}}
    assert frame._aggregate([{**base, "primary_gap_pp": 10, "modeled_gap_pp": 5}])["explanation"] == pytest.approx(.5)
    assert frame._aggregate([{**base, "primary_gap_pp": 10, "modeled_gap_pp": 15}])["explanation"] == pytest.approx(.5)
    assert frame._aggregate([{**base, "primary_gap_pp": 0, "modeled_gap_pp": 0}])["explanation"] == 0.0


def test_opposite_sign_annual_completion_cannot_pass():
    ranges = {"2022": {"primary_gap_pp": (10, 10), "modeled_gap_pp": (10, 10)}, "2023": {"primary_gap_pp": (-10, -10), "modeled_gap_pp": (-10, -10)}, "pooled": {"primary_gap_pp": (1, 1), "modeled_gap_pp": (1, 1)}}
    assert frame._same_sign_gate(ranges, False) is False
def test_crossing_zero_ranges_use_attainable_same_sign_ratio_bounds():
    ranges = {"2022": {"primary_gap_pp": (-10, 10), "modeled_gap_pp": (20, 20)}, "2023": {"primary_gap_pp": (-10, 10), "modeled_gap_pp": (20, 20)}, "pooled": {"primary_gap_pp": (0, 0), "modeled_gap_pp": (0, 0)}}
    assert frame._same_sign_gate(ranges, False) is False
    ranges["2022"]["modeled_gap_pp"] = (5, 5)
    ranges["2023"]["modeled_gap_pp"] = (5, 5)
    assert frame._same_sign_gate(ranges, False) is True
    assert frame._same_sign_gate(ranges, True) is False


def test_whole_day_resampling_preserves_within_day_multiplicity_and_fixed_weights():
    rows = ({"day": "20220103", "identity": "a"}, {"day": "20220103", "identity": "b"}, {"day": "20220104", "identity": "c"})
    sampled = frame._year_sample(rows, iter((0, 0)))
    assert [row["identity"] for row in sampled] == ["a", "b", "a", "b"]
    left = {"primary_gap_pp": 10, "modeled_gap_pp": 5, "shapley_E_pp": 1, "shapley_D_pp": 2, "shapley_T_pp": 3}
    right = {"primary_gap_pp": 20, "modeled_gap_pp": 10, "shapley_E_pp": 4, "shapley_D_pp": 5, "shapley_T_pp": 6}
    pooled = frame._weighted_aggregate(left, right)
    assert pooled["primary_gap_pp"] == pytest.approx((10 * 101 + 20 * 197) / 298)
    assert pooled["modeled_gap_pp"] == pytest.approx((5 * 101 + 10 * 197) / 298)


@pytest.mark.parametrize("key", frame.SOURCES + ("tick_db", "source_authority", "preregistration", "launch", "materializer", "measurement_target", "identity_crosswalk", "design_marker"))
def test_every_custody_class_requires_descriptor_derived_pre_and_post_triples(key):
    value = snapshot()
    physical = value["provenance"]["physical_inputs"]
    alternate = next(name for name in physical if name != key)
    for field, replacement in (("sha256", "cd" * 32), ("size_bytes", 2), ("physical_id", "forged")):
        tampered = copy.deepcopy(value)
        tampered["provenance"]["physical_inputs"][key]["pre"][field] = replacement
        with pytest.raises(frame.FrameSchemaError):
            frame.validate_snapshot(tampered)
    swapped = copy.deepcopy(value)
    swapped["provenance"]["physical_inputs"][key] = copy.deepcopy(swapped["provenance"]["physical_inputs"][alternate])
    with pytest.raises(frame.FrameSchemaError):
        frame.validate_snapshot(swapped)
    descriptor_swapped = copy.deepcopy(value)
    if key in frame.SOURCES:
        alternate_source = next(name for name in frame.SOURCES if name != key)
        descriptor_swapped["provenance"]["sources"][key] = copy.deepcopy(descriptor_swapped["provenance"]["sources"][alternate_source])
    elif key == "tick_db":
        descriptor_swapped["provenance"]["tick_db"]["sha256"] = "de" * 32
    else:
        alternate_descriptor = "design_marker" if key != "design_marker" else "identity_crosswalk"
        descriptor_swapped["provenance"][key] = copy.deepcopy(descriptor_swapped["provenance"][alternate_descriptor])
    with pytest.raises(frame.FrameSchemaError):
        frame.validate_snapshot(descriptor_swapped)
def test_swapped_year_and_invalid_calendar_identities_and_timestamps_fail_closed():
    swapped_year = snapshot(); swapped_year["events"][0]["identity"]["year"] = 2023
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(swapped_year)
    invalid_event_date = snapshot(); invalid_event_date["events"][0]["identity"]["day"] = "20220230"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(invalid_event_date)
    invalid_ledger_time = snapshot(); invalid_ledger_time["events"][0]["ledger"]["sell_timestamp"] = "20220103246000"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(invalid_ledger_time)
    invalid_cell_time = snapshot(); invalid_cell_time["events"][0]["cells"]["E0D0T0"]["entry_time"] = "20220103246000"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(invalid_cell_time)
    invalid_reconciliation_time = snapshot(); invalid_reconciliation_time["provenance"]["endpoint_reconciliation"][0]["l3"]["bank_exit_timestamp"] = "20220103246000"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(invalid_reconciliation_time)
    invalid_offline = snapshot(); invalid_offline["flow"]["offline_only"] = 1; invalid_offline["offline_only"] = [{"identity": {"code": "999999", "year": 2022, "day": "20220230", "buy_time": "20220230090000"}, "status": "offline_only", "reason": "invalid"}]
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(invalid_offline)



def test_scanner_shape_is_json_only_with_literal_input_open():
    source = (ROOT / "scripts/u7_f0_frame_measure.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = [node for node in tree.body if isinstance(node, ast.Import)]
    assert len(imports) == 1 and [(alias.name, alias.asname) for alias in imports[0].names] == [("json", None)]
    assert not any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree))
    guards = [node for node in tree.body if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)]
    opens = [node for node in ast.walk(guards[-1]) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open"]
    assert len(opens) == 1 and isinstance(opens[0].args[0], ast.Constant) and opens[0].args[0].value == frame.INPUT_PATH
    assert json.loads(json.dumps({"scanner": "json-only"}))["scanner"] == "json-only"
def test_cells_require_event_buy_time_reason_forced_false_and_exact_horizons():
    value = snapshot(engine_only=1, excluded=1)
    frame.validate_snapshot(value)
    mismatched_reason = copy.deepcopy(value)
    mismatched_reason["events"][-1]["cells"]["E0D0T0"]["missing_reason"] = "other"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(mismatched_reason)
    forced_missing = copy.deepcopy(value)
    forced_missing["events"][-1]["cells"]["E0D0T0"]["forced"] = True
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(forced_missing)
    wrong_entry = copy.deepcopy(value)
    wrong_entry["events"][0]["cells"]["E0D0T0"]["entry_time"] = "20220103090001"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(wrong_entry)
    t1_late = copy.deepcopy(value)
    t1_late["events"][0]["cells"]["E0D0T1"]["exit_time"] = "20220103092801"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(t1_late)
def test_absolute_path_predicate_rejects_relative_and_malformed_windows_paths():
    assert frame._absolute_path("/sealed/ticks.db")
    assert frame._absolute_path(r"C:\sealed\ticks.db")
    assert not frame._absolute_path("C:ticks.db")
    assert not frame._absolute_path("artifacts/ticks.db")
    value = snapshot()
    value["provenance"]["tick_db"]["path"] = "ticks.db"
    with pytest.raises(frame.FrameSchemaError): frame.validate_snapshot(value)
@pytest.mark.parametrize("path", ("docs/research/source.json", "alpha_lab/catalog/input.parquet"))
def test_consumer_accepts_each_canonical_producer_source_path(path):
    assert frame._project_path(path) is True

@pytest.mark.parametrize("path", ("/sealed/input.json", "C:/sealed/input.json", r"C:\sealed\input.json", r"docs\source.json", "docs/../source.json", "./source.json", "docs//source.json", "docs/source.json/"))
def test_consumer_rejects_each_noncanonical_producer_source_path(path):
    assert frame._project_path(path) is False
def test_consumer_accepts_stripped_producer_source_descriptor_and_rejects_read_path() -> None:
    descriptor = {"path": "alpha_lab/catalog/onset_l3_bank.parquet", "sha256": HASH, "size_bytes": 1}
    assert frame._artifact(descriptor, "provenance.sources.onset_l3_bank") == descriptor
    with pytest.raises(frame.FrameSchemaError):
        frame._artifact({**descriptor, "read_path": "C:/sealed/onset_l3_bank.parquet"}, "provenance.sources.onset_l3_bank")
