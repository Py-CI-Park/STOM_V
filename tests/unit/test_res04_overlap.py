"""Family co-firing is descriptive, not proof of thesis conflict or routing edge."""

from __future__ import annotations

from datetime import date

import pytest

from ai_strategy_loop.revision import res04_overlap as overlap
from ai_strategy_loop.revision.res04_control_models import ControlInput, ControlScope
from ai_strategy_loop.revision.res04_event_stream import build_event_stream
from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation
from tests.unit.test_res04_event_stream import candidate, day
from tests.unit.test_res04_preparation_contract import payload


def examples() -> tuple[Res04Preparation, tuple[ControlInput, ...]]:
    """Seven synthetic candidates over one identical observed tick projection."""
    plan = Res04Preparation.model_validate_json(payload())
    ticks = day()
    ticks.interest[65] = ticks.interest[75] = 0
    values: list[ControlInput] = []
    for index, candidate_id in enumerate(plan.candidate_ids):
        item = candidate().model_copy(update={"candidate_id": candidate_id})
        if index >= 4:
            item = item.model_copy(
                update={
                    "family_id": "COMPRESSION_CONFIRMED_BREAKOUT",
                    "parameters": {
                        "vol_window": 10,
                        "price_window": 5,
                        "flow_window": 10,
                        "compression": 100.0,
                        "expansion": 0.0,
                        "strength_ratio": 0.0,
                    },
                }
            )
        scope = ControlScope(
            candidate=candidate_id,
            family=item.family_id,
            fold="F2",
            day=date(2022, 4, 1),
            symbol="005930",
        )
        values.append(
            ControlInput(
                scope=scope,
                stream=build_event_stream(ticks, item, plan, symbol="005930"),
            )
        )
    return plan, tuple(values)


def test_family_overlap_counts_common_observation_grid() -> None:
    # Given: two synthetic families with identical known-true intervals.
    plan, inputs = examples()
    # When.
    result = overlap.describe_family_overlap(inputs, plan)
    # Then: count simultaneous signals, without assigning router superiority.
    assert result.status == "OBSERVED"
    assert result.common_observations == 30
    assert result.pairs[0].co_firing == 28
    assert result.pairs[0].neither == 2
    assert result.interpretation == "CO_FIRING_NOT_PROVEN_CONFLICT"


def test_missing_candidate_is_incomplete() -> None:
    # Given / When.
    plan, inputs = examples()
    result = overlap.describe_family_overlap(inputs[:-1], plan)
    # Then: not an observed zero-overlap matrix.
    assert result.status == "INCOMPLETE"
    assert result.common_observations is None
    assert result.pairs == ()


def test_different_source_cannot_be_aligned() -> None:
    # Given: a different tick projection under one candidate.
    plan, inputs = examples()
    changed = inputs[-1].model_copy(
        update={
            "stream": inputs[-1].stream.model_copy(
                update={"observed_input_sha256": "0" * 64}
            )
        }
    )
    # When / Then.
    with pytest.raises(ValueError, match="OVERLAP_SOURCE_IDENTITY"):
        overlap.describe_family_overlap((*inputs[:-1], changed), plan)
