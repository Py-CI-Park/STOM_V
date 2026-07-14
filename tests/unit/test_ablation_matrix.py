"""Contract tests for CL-R06 2x2 buy/sell attribution (todo 12)."""

from __future__ import annotations
from dataclasses import replace

import pytest

from ai_strategy_loop.controller.ablation_matrix import (
    ARM_STATUS_INDETERMINATE_EXTERNAL_EFFECT,
    ArmBudgetV1,
    ArmBudgetAuthority,
    BudgetReservationV1,
    build_arm_cache_key,
    build_arm_id,
    build_arm_receipt_v1,
    cache_disposition,
    complete_arm_receipt,
    compute_attribution,
    compute_receipt_attribution,
    crash_arm_receipt,
    evaluator_admitted,
    reserve_arm_budget,
)


def _arm(profit: float, mdd: float, trade_count: int, daily_freq: float) -> dict:
    return {'profit': profit, 'mdd': mdd, 'trade_count': trade_count, 'daily_freq': daily_freq}


def _receipt(arm: str, **overrides):
    values = {
        'arm': arm,
        'candidate_id': 'candidate-1',
        'parent_id': 'parent-1',
        'manifest_id': 'manifest-1',
        'role': 'TRAIN',
        'capability': 'READY',
        'engine_id': 'engine-1',
        'data_id': 'data-1',
        'universe_id': 'universe-1',
        'cost_model_id': 'cost-1',
        'fill_model_id': 'fill-1',
        'capital_profile_id': 'capital-1',
        'session_id': 'session-1',
        'buy_hash': 'buy-parent' if arm in ('A', 'C') else 'buy-candidate',
        'sell_hash': 'sell-parent' if arm in ('A', 'B') else 'sell-candidate',
    }
    values.update(overrides)
    return build_arm_receipt_v1(**values)


def _admission(receipt, limit=1):
    authority = ArmBudgetAuthority()
    budget, reservation = reserve_arm_budget(
        ArmBudgetV1(limit=limit), receipt, authority
    )
    return budget, reservation, authority


def test_complete_2x2_known_numbers_exact_effects_and_mdd_sign_normalization():
    arms = {
        'A': _arm(profit=100.0, mdd=20.0, trade_count=50, daily_freq=2.0),
        'B': _arm(profit=130.0, mdd=15.0, trade_count=55, daily_freq=2.2),
        'C': _arm(profit=110.0, mdd=25.0, trade_count=52, daily_freq=2.1),
        'D': _arm(profit=150.0, mdd=18.0, trade_count=60, daily_freq=2.5),
    }
    result = compute_attribution(arms)

    assert result['valid'] is True
    assert 'reason' not in result

    # profit / trade_count / daily_freq: higher is better -> plain deltas.
    assert result['buy_effect']['profit'] == 30.0        # B - A
    assert result['sell_effect']['profit'] == 10.0        # C - A
    assert result['interaction']['profit'] == 10.0        # D - B - C + A

    assert result['buy_effect']['trade_count'] == 5
    assert result['sell_effect']['trade_count'] == 2
    assert result['interaction']['trade_count'] == 3      # 60 - 55 - 52 + 50

    assert abs(result['buy_effect']['daily_freq'] - 0.2) < 1e-9
    assert abs(result['sell_effect']['daily_freq'] - 0.1) < 1e-9
    assert abs(result['interaction']['daily_freq'] - 0.2) < 1e-9  # 2.5-2.2-2.1+2.0

    # mdd: lower is better -> sign-normalized so positive == improvement.
    # buy_effect.mdd = A - B = 20 - 15 = 5 (buy change reduced drawdown: good)
    assert result['buy_effect']['mdd'] == 5.0
    # sell_effect.mdd = A - C = 20 - 25 = -5 (sell change increased drawdown: bad)
    assert result['sell_effect']['mdd'] == -5.0
    # interaction.mdd = B + C - A - D = 15 + 25 - 20 - 18 = 2
    assert result['interaction']['mdd'] == 2.0


def test_missing_arm_returns_attribution_invalid_with_no_effect_numbers():
    arms = {
        'A': _arm(100.0, 20.0, 50, 2.0),
        'B': _arm(130.0, 15.0, 55, 2.2),
        'C': _arm(110.0, 25.0, 52, 2.1),
        # 'D' omitted entirely.
    }
    result = compute_attribution(arms)

    assert result == {
        'valid': False,
        'reason': 'attribution_invalid',
        'missing_arms': ['D'],
    }
    assert 'buy_effect' not in result
    assert 'sell_effect' not in result
    assert 'interaction' not in result


def test_errored_arm_returns_attribution_invalid_with_no_effect_numbers():
    arms = {
        'A': _arm(100.0, 20.0, 50, 2.0),
        'B': {'status': 'error'},
        'C': _arm(110.0, 25.0, 52, 2.1),
        'D': None,
    }
    result = compute_attribution(arms)

    assert result['valid'] is False
    assert result['reason'] == 'attribution_invalid'
    assert sorted(result['missing_arms']) == ['B', 'D']
    assert 'buy_effect' not in result
    assert 'sell_effect' not in result
    assert 'interaction' not in result


def test_arm_missing_a_required_metric_key_is_also_treated_as_missing():
    arms = {
        'A': _arm(100.0, 20.0, 50, 2.0),
        'B': {'profit': 130.0, 'mdd': 15.0, 'trade_count': 55},  # no daily_freq
        'C': _arm(110.0, 25.0, 52, 2.1),
        'D': _arm(150.0, 18.0, 60, 2.5),
    }
    result = compute_attribution(arms)

    assert result['valid'] is False
    assert result['reason'] == 'attribution_invalid'
    assert result['missing_arms'] == ['B']


def test_identical_inputs_yield_identical_attribution_regardless_of_dict_key_order():
    arms_a = {
        'A': _arm(100.0, 20.0, 50, 2.0),
        'B': _arm(130.0, 15.0, 55, 2.2),
        'C': _arm(110.0, 25.0, 52, 2.1),
        'D': _arm(150.0, 18.0, 60, 2.5),
    }
    arms_b = {
        'D': _arm(150.0, 18.0, 60, 2.5),
        'C': _arm(110.0, 25.0, 52, 2.1),
        'B': _arm(130.0, 15.0, 55, 2.2),
        'A': _arm(100.0, 20.0, 50, 2.0),
    }
    assert compute_attribution(arms_a) == compute_attribution(arms_b)
def test_arm_receipt_ids_are_deterministic_and_bind_every_evaluation_input():
    first = _receipt('A')
    second = _receipt('A')
    changed_role = _receipt('A', role='HOLDOUT')

    assert first == second
    assert first.arm_id == second.arm_id
    assert first.cache_key == second.cache_key
    assert first.arm_id != changed_role.arm_id
    assert first.cache_key != changed_role.cache_key
    assert first.arm_id.startswith('arm_')
    assert len(first.arm_id) == 68
    assert build_arm_id(
        arm='A', candidate_id='candidate-1', parent_id='parent-1',
        manifest_id='manifest-1', role='TRAIN', capability='READY',
        engine_id='engine-1', data_id='data-1', universe_id='universe-1',
        cost_model_id='cost-1', fill_model_id='fill-1',
        capital_profile_id='capital-1', session_id='session-1',
        buy_hash='buy-parent', sell_hash='sell-parent',
    ).startswith('arm_')
    assert build_arm_cache_key(
        arm='A', candidate_id='candidate-1', parent_id='parent-1',
        manifest_id='manifest-1', role='TRAIN', capability='READY',
        engine_id='engine-1', data_id='data-1', universe_id='universe-1',
        cost_model_id='cost-1', fill_model_id='fill-1',
        capital_profile_id='capital-1', session_id='session-1',
        buy_hash='buy-parent', sell_hash='sell-parent',
    ) == first.cache_key


def test_cache_accepts_only_exact_completed_same_role_receipt():
    pending = _receipt('A')
    _, reservation, authority = _admission(pending)
    completed = complete_arm_receipt(
        pending, reservation, authority, attempt_id='attempt-1', result_hash='result-1',
        metric_verdict='PASS', metrics=_arm(1, 2, 3, 4),
    )

    assert cache_disposition(pending, completed) == 'HIT_VALID'
    assert cache_disposition(pending, pending) == 'REJECT_NOT_COMPLETED'
    assert cache_disposition(pending, _receipt('A', role='HOLDOUT')) == 'REJECT_ROLE_MISMATCH'
    assert cache_disposition(pending, _receipt('B')) == 'REJECT_CACHE_KEY_MISMATCH'


def test_receipt_construction_and_cache_fail_closed_without_completion_provenance():
    with pytest.raises(ValueError, match="unbound pending"):
        _receipt("A", status="COMPLETED", result_hash="forged")

    pending = _receipt("A")
    _, reservation, authority = _admission(pending)
    with pytest.raises(ValueError, match="finite metrics"):
        complete_arm_receipt(
            pending,
            reservation,
            authority,
            attempt_id="attempt-1",
            result_hash="result-1",
            metric_verdict="PASS",
            metrics={"profit": 1.0},
        )

    completed = complete_arm_receipt(
        pending,
        reservation,
        authority,
        attempt_id="attempt-1",
        result_hash="result-1",
        metric_verdict="PASS",
        metrics=_arm(1, 2, 3, 4),
    )
    assert cache_disposition(pending, replace(completed, attempt_id="")) == "REJECT_NOT_COMPLETED"


def test_budget_admission_and_crash_contracts_are_fail_closed():
    pending = _receipt('A')
    exhausted_budget, exhausted, authority = _admission(pending, limit=0)
    assert exhausted_budget == ArmBudgetV1(limit=0)
    assert exhausted.status == 'BUDGET_EXHAUSTED'
    assert evaluator_admitted(pending, exhausted, authority) is False
    with pytest.raises(ValueError, match="mismatched budget"):
        reserve_arm_budget(ArmBudgetV1(limit=1), pending, authority)

    budget, reservation, authority = _admission(pending)
    assert budget == ArmBudgetV1(limit=1, reserved=1)
    assert evaluator_admitted(pending, reservation, authority) is True
    forged = BudgetReservationV1(
        reservation_id="0" * 64,
        arm_id=pending.arm_id,
        status="RESERVED",
        budget_limit=1,
        reserved_before=0,
    )
    assert evaluator_admitted(pending, forged, authority) is False

    before = crash_arm_receipt(pending, authority=ArmBudgetAuthority())
    after = crash_arm_receipt(pending, reservation, authority=authority)
    assert before.retryable is True
    assert before.status == 'PENDING'
    assert after.status == ARM_STATUS_INDETERMINATE_EXTERNAL_EFFECT
    assert after.retryable is False
    assert 'crash_after_reservation' in after.reason_codes
    assert evaluator_admitted(pending, reservation, authority) is False
    with pytest.raises(ValueError, match="stale budget"):
        reserve_arm_budget(ArmBudgetV1(limit=1), pending, authority)
    with pytest.raises(ValueError, match="stale budget"):
        reserve_arm_budget(ArmBudgetV1(limit=1), _receipt("B"), authority)


def test_receipt_attribution_requires_four_completed_same_manifest_and_role():
    metrics = {
        'A': _arm(100, 20, 50, 2),
        'B': _arm(130, 15, 55, 2.2),
        'C': _arm(110, 25, 52, 2.1),
        'D': _arm(150, 18, 60, 2.5),
    }
    receipts = {}
    for arm in ('A', 'B', 'C', 'D'):
        pending = _receipt(arm)
        _, reservation, authority = _admission(pending)
        receipts[arm] = complete_arm_receipt(
            pending, reservation, authority, attempt_id=f'attempt-{arm}', result_hash=f'result-{arm}',
            metric_verdict='PASS', metrics=metrics[arm],
        )

    assert compute_receipt_attribution(receipts)['valid'] is True
    incomplete = dict(receipts)
    incomplete['D'] = _receipt('D')
    assert compute_receipt_attribution(incomplete) == {
        'valid': False, 'reason': 'attribution_invalid', 'missing_arms': ['D'],
    }
    mixed_role = dict(receipts)
    mixed_role['C'] = _receipt('C', role='HOLDOUT')
    _, reservation, authority = _admission(mixed_role['C'])
    mixed_role['C'] = complete_arm_receipt(
        mixed_role['C'], reservation, authority, attempt_id='attempt-C', result_hash='result-C',
        metric_verdict='PASS', metrics=metrics['C'],
    )
    rejected = compute_receipt_attribution(mixed_role)
    assert rejected['valid'] is False
    assert 'buy_effect' not in rejected
    mixed_manifest = dict(receipts)
    mixed_manifest['D'] = _receipt('D', manifest_id='manifest-2')
    _, reservation, authority = _admission(mixed_manifest['D'])
    mixed_manifest['D'] = complete_arm_receipt(
        mixed_manifest['D'], reservation, authority, attempt_id='attempt-D', result_hash='result-D',
        metric_verdict='PASS', metrics=metrics['D'],
    )
    rejected = compute_receipt_attribution(mixed_manifest)
    assert rejected['valid'] is False
    assert 'sell_effect' not in rejected
    mixed_engine = dict(receipts)
    engine_receipt = _receipt("D", engine_id="engine-2")
    _, engine_reservation, engine_authority = _admission(engine_receipt)
    mixed_engine["D"] = complete_arm_receipt(
        engine_receipt,
        engine_reservation,
        engine_authority,
        attempt_id="attempt-D2",
        result_hash="result-D2",
        metric_verdict="PASS",
        metrics=metrics["D"],
    )
    assert compute_receipt_attribution(mixed_engine)["reason"] == "attribution_identity_mismatch"

    wrong_pair = dict(receipts)
    wrong_receipt = _receipt("D", buy_hash="wrong-buy")
    _, wrong_reservation, wrong_authority = _admission(wrong_receipt)
    wrong_pair["D"] = complete_arm_receipt(
        wrong_receipt,
        wrong_reservation,
        wrong_authority,
        attempt_id="attempt-D3",
        result_hash="result-D3",
        metric_verdict="PASS",
        metrics=metrics["D"],
    )
    assert compute_receipt_attribution(wrong_pair)["reason"] == "attribution_pairing_mismatch"
