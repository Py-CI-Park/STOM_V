from __future__ import annotations

import math

import pytest

from ai_strategy_loop.revision import qmc_pareto as qp


def _space():
    return (
        qp.DimensionSpec.continuous("threshold", 10.0, 20.0),
        qp.DimensionSpec.integer("bucket", 1, 3),
        qp.DimensionSpec.categorical("lane", ("early", "mid", "late")),
    )


def test_halton_proposals_are_deterministic_and_receipted_without_authority():
    first = qp.propose_initial_candidates(_space(), budget=6, seed=1234, scramble=True)
    second = qp.propose_initial_candidates(_space(), budget=6, seed=1234, scramble=True)
    different_seed = qp.propose_initial_candidates(_space(), budget=6, seed=1235, scramble=True)

    assert [candidate.unit_sample for candidate in first.candidates] == [
        candidate.unit_sample for candidate in second.candidates
    ]
    assert [dict(candidate.parameters) for candidate in first.candidates] == [
        dict(candidate.parameters) for candidate in second.candidates
    ]
    assert [candidate.unit_sample for candidate in first.candidates] != [
        candidate.unit_sample for candidate in different_seed.candidates
    ]
    assert first.receipt.seed == 1234
    assert first.receipt.scramble is True
    assert first.receipt.bases == (2, 3, 5)
    assert first.adoption_authority == qp.NO_ADOPTION_AUTHORITY
    assert first.oos_claim == qp.NO_OOS_CLAIM
    assert all(candidate.adoption_authority == qp.NO_ADOPTION_AUTHORITY for candidate in first.candidates)
    assert all(candidate.oos_claim == qp.NO_OOS_CLAIM for candidate in first.candidates)


def test_unscrambled_halton_maps_continuous_integer_and_categorical_bounds():
    batch = qp.propose_initial_candidates(_space(), budget=4, seed=0, scramble=False)
    rows = [dict(candidate.parameters) for candidate in batch.candidates]

    assert rows[0] == {"threshold": 15.0, "bucket": 2, "lane": "early"}
    assert rows[1] == {"threshold": 12.5, "bucket": 3, "lane": "mid"}
    assert rows[2]["threshold"] == 17.5
    assert rows[2]["bucket"] == 1
    assert rows[2]["lane"] == "mid"
    for row in rows:
        assert 10.0 <= row["threshold"] <= 20.0
        assert isinstance(row["bucket"], int)
        assert 1 <= row["bucket"] <= 3
        assert row["lane"] in {"early", "mid", "late"}

    upper = qp.map_unit_sample(_space(), (1.0, 1.0, 1.0))
    assert dict(upper) == {"threshold": 20.0, "bucket": 3, "lane": "late"}


def test_halton_bases_are_validated_primes():
    with pytest.raises(qp.QmcParetoError, match="prime"):
        qp.halton_unit_samples(2, 1, bases=(2, 4))


def test_candidate_budget_limits_number_of_proposals():
    batch = qp.propose_initial_candidates(_space(), budget=3, seed=0, scramble=False)

    assert len(batch.candidates) == 3
    assert [candidate.trial_index for candidate in batch.candidates] == [1, 2, 3]
    assert batch.receipt.budget == 3


def test_pareto_archive_enforces_trial_budget():
    archive = qp.ParetoArchive({"score": qp.DIRECTION_MAXIMIZE}, budget=2)

    archive.add("a", {"score": 1.0})
    archive.add("b", {"score": 2.0})

    assert archive.remaining_budget == 0
    with pytest.raises(qp.TrialBudgetExceeded):
        archive.add("c", {"score": 3.0})


def test_dominance_supports_mixed_maximize_minimize_directions():
    objectives = {
        "profit": qp.DIRECTION_MAXIMIZE,
        "drawdown": qp.DIRECTION_MINIMIZE,
    }

    assert qp.dominates({"profit": 10.0, "drawdown": 2.0}, {"profit": 9.0, "drawdown": 3.0}, objectives)
    assert not qp.dominates({"profit": 10.0, "drawdown": 4.0}, {"profit": 9.0, "drawdown": 3.0}, objectives)

    archive = qp.ParetoArchive(objectives, budget=4)
    archive.add("low_risk", {"profit": 9.0, "drawdown": 1.0})
    archive.add("high_profit", {"profit": 12.0, "drawdown": 5.0})
    archive.add("dominated", {"profit": 8.0, "drawdown": 2.0})

    assert [entry.key for entry in archive.entries] == ["low_risk", "high_profit"]


def test_duplicate_key_replaces_previous_record_preserving_first_order():
    archive = qp.ParetoArchive({"score": qp.DIRECTION_MAXIMIZE}, budget=4)

    archive.add("dup", {"score": 1.0}, payload={"version": 1})
    archive.add("other", {"score": 1.5}, payload={"version": 1})
    result = archive.add("dup", {"score": 2.0}, payload={"version": 2})

    assert result.trial.first_trial_index == 1
    assert result.trial.last_trial_index == 3
    assert [entry.key for entry in archive.entries] == ["dup"]
    assert dict(archive.entries[0].payload) == {"version": 2}


def test_nan_objective_scores_are_rejected_without_spending_budget():
    archive = qp.ParetoArchive({"score": qp.DIRECTION_MAXIMIZE}, budget=1)

    with pytest.raises(qp.QmcParetoError, match="finite number"):
        archive.add("bad", {"score": math.nan})

    assert archive.remaining_budget == 1
    archive.add("good", {"score": 1.0})
    assert archive.remaining_budget == 0


def test_unit_mapping_rejects_nan():
    with pytest.raises(qp.QmcParetoError, match="finite number"):
        qp.map_unit_sample((qp.DimensionSpec.continuous("x", 0.0, 1.0),), (math.nan,))


def test_continuous_dimension_rejects_ranges_that_overflow_mapping_arithmetic():
    with pytest.raises(qp.QmcParetoError, match="continuous range"):
        qp.DimensionSpec.continuous("wide", -1.0e308, 1.0e308)

    spec = qp.DimensionSpec.continuous("safe", -1.0e154, 1.0e154)
    mapped = qp.map_unit_sample((spec,), (1.0,))

    assert math.isfinite(mapped["safe"])
    assert mapped["safe"] == 1.0e154


def test_integer_dimension_rejects_ranges_unsafe_for_float_unit_mapping():
    with pytest.raises(qp.QmcParetoError, match="integer range"):
        qp.DimensionSpec.integer("wide", 0, 1 << 53)
    with pytest.raises(qp.QmcParetoError, match="finite unit mapping"):
        qp.DimensionSpec.integer("huge", 10**400, 10**400)

    spec = qp.DimensionSpec.integer("safe", -3, 3)
    mapped = qp.map_unit_sample((spec,), (1.0,))

    assert mapped["safe"] == 3


def test_stable_order_keeps_equal_non_duplicate_ties_in_first_trial_order():
    archive = qp.ParetoArchive(
        {
            "profit": qp.DIRECTION_MAXIMIZE,
            "drawdown": qp.DIRECTION_MINIMIZE,
        },
        budget=3,
    )

    archive.add("first", {"profit": 10.0, "drawdown": 2.0})
    archive.add("second", {"profit": 10.0, "drawdown": 2.0})
    archive.add("tradeoff", {"profit": 12.0, "drawdown": 4.0})

    assert [entry.key for entry in archive.entries] == ["first", "second", "tradeoff"]
    assert archive.snapshot().receipt.tie_rule == qp._TIE_RULE
    assert archive.snapshot().adoption_authority == qp.NO_ADOPTION_AUTHORITY
