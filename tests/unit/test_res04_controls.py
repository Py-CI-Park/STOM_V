"""E1 controls consume actual synthetic production-adapter observations."""

from __future__ import annotations

from datetime import date

import pytest

from ai_strategy_loop.revision import res04_controls as controls
from ai_strategy_loop.revision.res04_event_stream import build_event_stream
from ai_strategy_loop.revision.res04_preparation_contract import Res04Preparation
from tests.unit.test_res04_event_stream import candidate, day
from tests.unit.test_res04_preparation_contract import payload


def example(
    year: int = 2022,
    *,
    all_false: bool = False,
    size: int = 90,
    plan: Res04Preparation | None = None,
) -> tuple[Res04Preparation, controls.ControlInput]:
    """Synthetic declared scope, never market or Holdout data."""
    plan = plan if plan is not None else Res04Preparation.model_validate_json(payload())
    ticks = day(size)
    ticks.timestamp[:] += (year - 2022) * 10_000_000_000
    if size > 75:
        ticks.interest[65] = 0
        ticks.interest[75] = 0
    if all_false:
        ticks.interest[:] = 0
    stream = build_event_stream(ticks, candidate(), plan, symbol="005930")
    scope = controls.ControlScope(
        candidate="candidate_0",
        family="ABSORPTION_REVERSAL",
        fold=f"F{year - 2020}",
        day=date(year, 4, 1),
        symbol="005930",
    )
    return plan, controls.ControlInput(scope=scope, stream=stream)


def test_onsets_and_control_counts_match_without_censored_start() -> None:
    # Given: first observed true is censored; two later false->true transitions.
    plan, data = example()
    # When.
    result = controls.select_controls(data, plan)
    # Then: same count, selected only from observed true with known predecessor.
    assert result.onset_positions == (66, 76)
    assert len(result.control_positions) == 2
    assert 59 not in result.control_positions
    pool = {
        r.source_position
        for r in data.stream.observations
        if r.triggered and r.previous_triggered is not None
    }
    assert set(result.control_positions) <= pool
    assert result.censored_true_count == 1
    assert result.use == "RETROSPECTIVE_DIAGNOSTIC_NOT_EXECUTABLE_ENTRY_POLICY"


def test_reproducible_and_no_trades_is_not_assumed() -> None:
    # Given / When.
    plan, data = example(all_false=True)
    result = controls.select_controls(data, plan)
    # Then: observed zero onsets is not an economic no-trades result.
    assert result == controls.select_controls(data, plan)
    assert result.status == "OBSERVED"
    assert result.onset_positions == ()
    assert result.control_positions == ()


@pytest.mark.parametrize("size", [20, 61])
def test_no_known_transitions_is_not_evaluable(size: int) -> None:
    # Given: only warmup/terminal, or a single censored observation.
    plan, data = example(size=size)
    # When / Then.
    assert controls.select_controls(data, plan).status == "NOT_EVALUABLE"


def test_wrong_identity_rejected() -> None:
    # Given: a forged scope label over another candidate's observations.
    plan, data = example()
    altered = data.model_copy(
        update={"scope": data.scope.model_copy(update={"candidate": "candidate_1"})}
    )
    # When / Then.
    with pytest.raises(ValueError, match="CONTROL_SCOPE"):
        controls.select_controls(altered, plan)


def test_forged_predecessor_rejected() -> None:
    # Given: a true->true continuation mislabeled as a fresh onset.
    plan, data = example()
    rows = list(data.stream.observations)
    rows[1] = rows[1].model_copy(update={"previous_triggered": False})
    altered = data.model_copy(
        update={"stream": data.stream.model_copy(update={"observations": tuple(rows)})}
    )
    # When / Then.
    with pytest.raises(ValueError, match="CONTROL_PREDECESSOR"):
        controls.select_controls(altered, plan)


def test_missing_fold_incomplete_not_normal_stop() -> None:
    # Given: four expected scopes but only three inputs supplied.
    pairs = [example(y) for y in range(2022, 2026)]
    expected = tuple(item.scope for _, item in pairs)
    # When.
    result = controls.assess_candidate(
        pairs[0][0], "candidate_0", expected, tuple(item for _, item in pairs[:3])
    )
    # Then: missing data is not synthesized as zero or failure evidence.
    assert result.status == "INCOMPLETE"


def test_complete_low_sample_normal_stop() -> None:
    # Given: complete declared inventory, but only eight observed onsets.
    pairs = [example(y) for y in range(2022, 2026)]
    expected = tuple(item.scope for _, item in pairs)
    # When.
    result = controls.assess_candidate(
        pairs[0][0], "candidate_0", expected, tuple(item for _, item in pairs)
    )
    # Then: normal sample STOP, without economic/adoption authority.
    assert result.status == "NORMAL_STOP"
    assert result.total_onsets == 8
    assert result.execution_policy == "SEPARATE_APPROVAL_REQUIRED"
