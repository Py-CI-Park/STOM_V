from __future__ import annotations

import pytest

from ai_strategy_loop.revision.bayesian_sequential import (
    NO_ADOPTION_AUTHORITY,
    Decision,
    SequentialConfig,
    calibrate_fixed_seed,
    evaluate,
    initial_state,
    update,
)


def test_prior_evaluation_has_receipts_and_no_authority():
    config = SequentialConfig(max_sample=20)

    result = evaluate(config)

    assert result.decision is Decision.CONTINUE
    assert result.posterior_mean == pytest.approx(0.5)
    assert result.credible_interval[0] == pytest.approx(0.025, abs=1e-5)
    assert result.credible_interval[1] == pytest.approx(0.975, abs=1e-5)
    assert result.probability_above_rope == pytest.approx(0.5)
    assert result.probability_below_rope == pytest.approx(0.5)
    assert result.config_receipt.digest == config.receipt().digest
    assert result.seed_receipt.purpose == "external_observations_no_rng"
    assert result.seed_receipt.digest
    assert result.look_receipt == ()
    assert result.adoption_authority == NO_ADOPTION_AUTHORITY
    assert result.can_adopt is False


def test_update_accumulates_counts_without_mutating_prior_state():
    config = SequentialConfig(max_sample=10)
    state = initial_state(config)

    first = update(state, successes=1, failures=0)
    second = update(first.state, successes=0, failures=1)

    assert state.successes == 0
    assert state.failures == 0
    assert state.looks == ()
    assert first.successes == 1
    assert first.failures == 0
    assert second.successes == 1
    assert second.failures == 1
    assert second.posterior_alpha == pytest.approx(2.0)
    assert second.posterior_beta == pytest.approx(2.0)
    assert second.posterior_mean == pytest.approx(0.5)


def test_all_decisions_are_reachable():
    config = SequentialConfig(max_sample=10)

    assert evaluate(config, successes=9, failures=0).decision is Decision.APPROVE
    assert evaluate(config, successes=0, failures=9).decision is Decision.REJECT
    assert evaluate(config, successes=1, failures=1).decision is Decision.CONTINUE
    assert evaluate(config, successes=5, failures=5).decision is Decision.MAX_SAMPLE


def test_invalid_config_is_rejected():
    cases = [
        {"prior_alpha": 0.0},
        {"prior_beta": -1.0},
        {"rope_lower": 0.0},
        {"rope_lower": 1.0},
        {"approve_prob_threshold": 1.0},
        {"reject_prob_threshold": 0.0},
        {"approve_prob_threshold": 0.4, "reject_prob_threshold": 0.4},
        {"max_sample": 0},
        {"credible_mass": 1.0},
    ]

    for kwargs in cases:
        with pytest.raises((TypeError, ValueError)):
            SequentialConfig(**kwargs)


def test_invalid_observation_inputs_are_rejected():
    config = SequentialConfig(max_sample=3)
    state = initial_state(config)

    with pytest.raises(ValueError):
        update(state, successes=0, failures=0)
    with pytest.raises(TypeError):
        update(state, successes=True, failures=0)
    with pytest.raises(ValueError):
        evaluate(config, successes=4, failures=0)


def test_receipt_preserves_every_look_append_only():
    config = SequentialConfig(max_sample=10)
    state = initial_state(config)

    first = update(state, successes=1, failures=1)
    second = update(first.state, successes=2, failures=0)
    third = update(second.state, successes=0, failures=2)

    assert len(first.look_receipt) == 1
    assert len(second.look_receipt) == 2
    assert len(third.look_receipt) == 3
    assert third.look_receipt[:2] == second.look_receipt
    assert third.look_receipt[0] == first.look_receipt[0]
    assert [look.look_index for look in third.look_receipt] == [1, 2, 3]
    assert [(look.look_successes, look.look_failures) for look in third.look_receipt] == [
        (1, 1),
        (2, 0),
        (0, 2),
    ]
    assert [(look.cumulative_successes, look.cumulative_failures) for look in third.look_receipt] == [
        (1, 1),
        (3, 1),
        (3, 3),
    ]
    assert third.look_receipt[1].previous_receipt_digest == third.look_receipt[0].receipt_digest
    assert third.look_receipt[2].previous_receipt_digest == third.look_receipt[1].receipt_digest
    assert all(look.adoption_authority == NO_ADOPTION_AUTHORITY for look in third.look_receipt)
    assert all(not look.can_adopt for look in third.look_receipt)


def test_fixed_seed_calibration_is_deterministic_and_advisory_only():
    config = SequentialConfig(max_sample=12)

    first = calibrate_fixed_seed(
        config,
        seed=1234,
        true_success_rates=(0.25, 0.75),
        simulations_per_rate=20,
        look_size=2,
    )
    second = calibrate_fixed_seed(
        config,
        seed=1234,
        true_success_rates=(0.25, 0.75),
        simulations_per_rate=20,
        look_size=2,
    )

    assert first == second
    assert first.config_receipt.digest == config.receipt().digest
    assert first.seed_receipt.seed == 1234
    assert first.seed_receipt.purpose == "fixed_seed_calibration"
    assert first.adoption_authority == NO_ADOPTION_AUTHORITY
    assert first.can_adopt is False
    assert first.total_false_approvals == sum(
        summary.false_approval_count for summary in first.summaries
    )
    assert len(first.summaries) == 2
    for summary in first.summaries:
        assert sum(count for _, count in summary.decision_counts) == 20
        assert 0 <= summary.false_approval_rate <= 1
        assert 0 < summary.min_sample_size <= summary.mean_sample_size <= summary.max_sample_size
        assert summary.max_sample_size <= config.max_sample


def test_calibration_counts_rope_boundary_approval_as_false_approval():
    config = SequentialConfig(
        prior_alpha=12.0,
        prior_beta=1.0,
        rope_lower=0.5,
        approve_prob_threshold=0.99,
        reject_prob_threshold=0.02,
        max_sample=1,
    )

    report = calibrate_fixed_seed(
        config,
        seed=7,
        true_success_rates=(config.rope_lower, config.rope_lower + 0.01),
        simulations_per_rate=3,
        look_size=1,
    )

    boundary, above_boundary = report.summaries
    assert boundary.true_success_rate == config.rope_lower
    assert dict(boundary.decision_counts)[Decision.APPROVE.value] == 3
    assert boundary.false_approval_count == 3
    assert boundary.false_approval_rate == 1.0
    assert above_boundary.false_approval_count == 0
    assert report.total_false_approvals == 3
