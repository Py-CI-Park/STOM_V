from __future__ import annotations

import pytest

from ai_strategy_loop.revision.execution_contract import evaluate_execution_contract
from ai_strategy_loop.revision.mcap_controls import (
    control_receipt,
    direction_inversion_control,
    event_offset_random_control,
    parameter_random_baseline,
    symbol_shuffle_control,
    timestamp_shuffle_control,
)
from ai_strategy_loop.revision.mcap_event_estimator import (
    block_sparse_candidates,
    estimate_candidate_events,
)
from ai_strategy_loop.revision.mcap_state_machine import (
    D3_ALLOWED_FUNCTIONS,
    FAMILIES,
    build_candidate,
)
from ai_strategy_loop.revision.window_contract import ResearchWindowContract


def _window() -> ResearchWindowContract:
    return ResearchWindowContract(
        lane="stock_tick", start=90000, end_exclusive=93000,
        bucket_minutes=tuple(range(540, 570, 5)), source_fingerprint="a" * 64,
    )


def _defaults(family):
    return {spec.name: spec.default for spec in family.parameters}


def test_five_families_have_sequential_steps_and_six_entry_variables():
    assert [family.family_id for family in FAMILIES] == [
        "ABSORPTION_REVERSAL", "FAILED_BREAKOUT_RETURN",
        "COMPRESSION_CONFIRMED_BREAKOUT", "FLOW_PRICE_DIVERGENCE",
        "OPENING_OVERREACTION_MEAN_REVERT",
    ]
    assert all(family.steps == ("STATE_ENTER", "STATE_PERSIST", "EVENT", "CONFIRM", "ENTER") for family in FAMILIES)
    assert all(len(family.parameters) == 6 for family in FAMILIES)


@pytest.mark.parametrize("band_id", [
    "MCAP_A_LT3000", "MCAP_B_3000_5000", "MCAP_C_5000_10000", "MCAP_D_GE10000",
])
def test_candidate_renders_exactly_one_band_and_window(band_id):
    family = FAMILIES[0]
    candidate = build_candidate(
        family_id=family.family_id, band_id=band_id,
        parameters=_defaults(family), window=_window(),
    )
    assert candidate.band_id == band_id
    assert candidate.source.count("시가총액") == 1
    assert "90000 <= 시분초 < 93000" in candidate.source
    assert "self.Buy()" in candidate.source
    assert "OOS/자동채택/실전 권한 없음" in candidate.source
    assert len(candidate.source_sha256) == 64
    assert candidate.authority == "existing_db_development_no_oos_no_adoption"


def test_candidate_identity_is_deterministic_and_parameter_drift_changes_hash():
    family = FAMILIES[2]
    defaults = _defaults(family)
    first = build_candidate(family_id=family.family_id, band_id="MCAP_C_5000_10000", parameters=defaults, window=_window())
    second = build_candidate(family_id=family.family_id, band_id="MCAP_C_5000_10000", parameters=defaults, window=_window())
    changed = dict(defaults)
    changed[family.parameters[0].name] += 1
    third = build_candidate(family_id=family.family_id, band_id="MCAP_C_5000_10000", parameters=changed, window=_window())
    assert first == second
    assert first.canonical_sha256 != third.canonical_sha256


def test_every_family_default_source_passes_static_runtime_contract():
    for family in FAMILIES:
        for band_id in (
            "MCAP_A_LT3000", "MCAP_B_3000_5000",
            "MCAP_C_5000_10000", "MCAP_D_GE10000",
        ):
            candidate = build_candidate(
                family_id=family.family_id, band_id=band_id,
                parameters=_defaults(family), window=_window(),
            )
            result = evaluate_execution_contract(
                candidate.source, allowed_functions=D3_ALLOWED_FUNCTIONS,
                max_clauses=32, max_lookback=240, max_estimated_work=256,
            )
            assert result.ok, (family.family_id, band_id, result.reasons)


def test_direct_source_contract_allows_preregistered_g1_confirmation_functions():
    assert {"연속상승", "호가상승압력"}.issubset(D3_ALLOWED_FUNCTIONS)


def test_event_estimator_blocks_sparse_candidate_without_reading_pnl():
    rows = [
        {"candidate_id": "C1", "triggered": True, "fold_id": f"F{i % 2}", "day": i // 2, "symbol": f"S{i % 30}"}
        for i in range(240)
    ]
    passed = estimate_candidate_events("C1", rows, expected_folds=("F0", "F1"), min_total=200, min_per_fold=20)
    sparse = estimate_candidate_events("C2", rows, expected_folds=("F0", "F1"), min_total=200, min_per_fold=20)
    assert passed.verdict == "EVENT_COUNT_PASS"
    assert sparse.verdict == "INSUFFICIENT_SAMPLE"
    assert block_sparse_candidates([passed, sparse]) == (["C1"], ["C2"])
    assert "profit" not in passed.to_dict()


def test_event_estimator_zero_fills_missing_expected_fold():
    rows = [{"candidate_id": "C1", "triggered": True, "fold_id": "F0", "day": 1, "symbol": "S"}] * 240
    estimate = estimate_candidate_events(
        "C1", rows, expected_folds=("F0", "F1"), min_total=200, min_per_fold=20,
    )
    assert estimate.fold_counts == {"F0": 240, "F1": 0}
    assert estimate.verdict == "INSUFFICIENT_SAMPLE"


def test_negative_controls_preserve_row_count_and_are_deterministic():
    rows = [
        {"timestamp": index, "symbol": f"S{index}", "direction": "long"}
        for index in range(10)
    ]
    assert timestamp_shuffle_control(rows, seed=7) == timestamp_shuffle_control(rows, seed=7)
    assert symbol_shuffle_control(rows, seed=7) == symbol_shuffle_control(rows, seed=7)
    assert all(row["direction"] == "short" for row in direction_inversion_control(rows))
    offset = event_offset_random_control(rows, seed=7)
    assert len(offset) == len(rows)
    assert all(row["timestamp"] == row["original_timestamp"] + row["offset_seconds"] for row in offset)
    params = parameter_random_baseline({"a": (0, 1), "b": (2, 3)}, seed=7)
    assert 0 <= params["a"] <= 1 and 2 <= params["b"] <= 3
    receipt = control_receipt("timestamp_shuffle", timestamp_shuffle_control(rows, seed=7), seed=7)
    assert receipt["row_count"] == 10
    assert len(receipt["sha256"]) == 64
