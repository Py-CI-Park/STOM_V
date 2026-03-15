from cli.promotion import PROMOTION_PRESETS, resolve_promotion_criteria


def test_resolve_promotion_criteria_balanced_defaults():
    result = resolve_promotion_criteria('balanced')
    assert result['preset'] == 'balanced'
    assert result['min_rounds'] == PROMOTION_PRESETS['balanced']['min_rounds']


def test_resolve_promotion_criteria_applies_overrides():
    result = resolve_promotion_criteria('conservative', {
        'min_success_rate': 0.9,
        'min_avg_trade_count': 120.0,
    })
    assert result['preset'] == 'conservative'
    assert result['min_success_rate'] == 0.9
    assert result['min_avg_trade_count'] == 120.0
