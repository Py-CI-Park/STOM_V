import pytest
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


def test_unknown_preset_raises_value_error():
    """존재하지 않는 프리셋명은 ValueError를 발생시켜야 한다."""
    with pytest.raises(ValueError, match="unknown promotion preset"):
        resolve_promotion_criteria('nonexistent')


def test_none_override_values_are_skipped():
    """overrides에 None 값이 있으면 기존 프리셋 값을 유지해야 한다."""
    result = resolve_promotion_criteria('balanced', {
        'min_rounds': None,
        'min_success_rate': 0.99,
    })
    assert result['min_rounds'] == PROMOTION_PRESETS['balanced']['min_rounds']
    assert result['min_success_rate'] == 0.99


def test_all_presets_have_required_keys():
    """모든 프리셋(conservative/balanced/aggressive)에 필수 키 4개가 존재해야 한다."""
    required_keys = {'min_rounds', 'min_success_rate', 'min_mean_oos_metric', 'min_avg_trade_count'}
    for preset_name in ('conservative', 'balanced', 'aggressive'):
        result = resolve_promotion_criteria(preset_name)
        assert required_keys.issubset(result.keys()), f"{preset_name} 프리셋에 필수 키 누락"
        assert result['preset'] == preset_name


def test_conservative_stricter_than_aggressive():
    """conservative 프리셋은 aggressive보다 엄격한 기준이어야 한다."""
    con = resolve_promotion_criteria('conservative')
    agg = resolve_promotion_criteria('aggressive')
    assert con['min_rounds'] >= agg['min_rounds']
    assert con['min_success_rate'] >= agg['min_success_rate']
    assert con['min_avg_trade_count'] >= agg['min_avg_trade_count']


def test_empty_overrides_dict():
    """빈 overrides dict는 프리셋 기본값과 동일해야 한다."""
    result = resolve_promotion_criteria('balanced', {})
    default = resolve_promotion_criteria('balanced')
    assert result == default
