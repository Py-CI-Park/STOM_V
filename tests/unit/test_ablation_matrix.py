"""Contract tests for CL-R06 2x2 buy/sell attribution (todo 12)."""

from __future__ import annotations

import pytest

from ai_strategy_loop.controller.ablation_matrix import compute_attribution


def _arm(profit: float, mdd: float, trade_count: int, daily_freq: float) -> dict:
    return {'profit': profit, 'mdd': mdd, 'trade_count': trade_count, 'daily_freq': daily_freq}




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

@pytest.mark.parametrize(
    ('arm_key', 'metric', 'non_finite'),
    [
        (arm_key, metric, non_finite)
        for non_finite in (float('nan'), float('inf'), float('-inf'))
        for arm_key, metric in zip(
            ('A', 'B', 'C', 'D'),
            ('profit', 'mdd', 'trade_count', 'daily_freq'),
        )
    ],
    ids=[
        f'{arm_key}-{metric}-{non_finite_name}'
        for non_finite_name in ('nan', 'positive-infinity', 'negative-infinity')
        for arm_key, metric in zip(
            ('A', 'B', 'C', 'D'),
            ('profit', 'mdd', 'trade_count', 'daily_freq'),
        )
    ],
)
def test_non_finite_required_metric_refuses_attribution(
    arm_key: str,
    metric: str,
    non_finite: float,
):
    arms = {
        'A': _arm(100.0, 20.0, 50, 2.0),
        'B': _arm(130.0, 15.0, 55, 2.2),
        'C': _arm(110.0, 25.0, 52, 2.1),
        'D': _arm(150.0, 18.0, 60, 2.5),
    }
    arms[arm_key][metric] = non_finite

    assert compute_attribution(arms) == {
        'valid': False,
        'reason': 'attribution_invalid',
        'missing_arms': [arm_key],
    }


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
