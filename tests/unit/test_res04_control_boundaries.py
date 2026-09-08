"""Control boundaries, evidence identity and review-only feasibility states."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_strategy_loop.revision import res04_controls as controls
from ai_strategy_loop.revision.res04_event_stream import build_event_stream
from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation
from tests.unit.test_res04_controls import example
from tests.unit.test_res04_event_stream import candidate, day
from tests.unit.test_res04_preparation_contract import payload


def test_sufficient_sample_only_allows_review() -> None:
    # Given: synthetic thresholds solely to exercise the positive branch.
    raw = (
        payload()
        .replace('"min_total_episodes": 200', '"min_total_episodes": 8')
        .replace('"min_episodes_per_fold": 20', '"min_episodes_per_fold": 2')
        .replace('"min_distinct_days": 20', '"min_distinct_days": 4')
        .replace('"min_distinct_symbols": 10', '"min_distinct_symbols": 1')
    )
    plan = Res04Preparation.model_validate_json(raw)
    inputs = tuple(example(y, plan=plan)[1] for y in range(2022, 2026))
    # When.
    result = controls.assess_candidate(
        plan, "candidate_0", tuple(d.scope for d in inputs), iter(inputs)
    )
    # Then: not an economic pass or an execution grant.
    assert result.status == "REVIEW_ONLY"
    assert result.execution_policy == "SEPARATE_APPROVAL_REQUIRED"


def test_duplicate_inventory_and_duplicate_input_rejected() -> None:
    # Given: duplicate evidence must not inflate counts.
    plan, data = example()
    # When / Then.
    with pytest.raises(ValueError, match="CONTROL_INVENTORY_INVALID"):
        controls.assess_candidate(
            plan, "candidate_0", (data.scope, data.scope), (data,)
        )
    with pytest.raises(ValueError, match="CONTROL_UNEXPECTED_OR_DUPLICATE_SLICE"):
        controls.assess_candidate(plan, "candidate_0", (data.scope,), (data, data))


def test_gap_first_true_not_used_as_onset_or_control() -> None:
    # Given: a two-second gap inside a known-true run.
    plan, data = example()
    ticks = day()
    ticks.interest[65] = ticks.interest[75] = 0
    ticks.timestamp[70:] += 1  # fixture seconds10..29, no calendar rollover
    stream = build_event_stream(ticks, candidate(), plan, symbol="005930")
    # When.
    result = controls.select_controls(
        controls.ControlInput(scope=data.scope, stream=stream), plan
    )
    # Then.
    assert 70 not in result.onset_positions
    assert 70 not in result.control_positions
    assert result.censored_true_count == 2


def test_same_counts_different_input_has_different_receipt() -> None:
    # Given: same signal counts, different actual price inputs.
    plan, data = example()
    ticks = day()
    ticks.interest[65] = ticks.interest[75] = 0
    ticks.price[:] += 1
    altered = controls.ControlInput(
        scope=data.scope,
        stream=build_event_stream(ticks, candidate(), plan, symbol="005930"),
    )
    # When.
    first = controls.assess_candidate(plan, "candidate_0", (data.scope,), (data,))
    second = controls.assess_candidate(plan, "candidate_0", (data.scope,), (altered,))
    # Then: evidence changes even if aggregate counts/status do not.
    assert first.input_receipt_sha256 != second.input_receipt_sha256


def test_scope_identifiers_are_bounded() -> None:
    # Given / When / Then: prevent huge identity strings in per-row hash ranking.
    _, data = example()
    raw = data.scope.model_dump_json().replace("ABSORPTION_REVERSAL", "x" * 129)
    with pytest.raises(ValidationError):
        controls.ControlScope.model_validate_json(raw)


def test_different_candidate_definitions_cannot_be_pooled() -> None:
    # Given: one ID but a different declared definition in the second fold.
    pairs = [example(year) for year in range(2022, 2026)]
    plan = pairs[0][0]
    inputs = [data for _, data in pairs]
    inputs[1] = inputs[1].model_copy(
        update={
            "stream": inputs[1].stream.model_copy(
                update={"candidate_definition_sha256": "0" * 64}
            )
        }
    )
    # When / Then: cannot turn mixed variants into one sample screen.
    with pytest.raises(ValueError, match="CONTROL_CANDIDATE_DEFINITION"):
        controls.assess_candidate(
            plan, "candidate_0", tuple(data.scope for data in inputs), inputs
        )
