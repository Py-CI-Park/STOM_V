"""전략 채택 기준 프리셋 (library-only)."""

from __future__ import annotations


PROMOTION_PRESETS = {
    'conservative': {
        'min_rounds': 3,
        'min_success_rate': 0.80,
        'min_mean_oos_metric': 0.10,
        'min_avg_trade_count': 100.0,
    },
    'balanced': {
        'min_rounds': 2,
        'min_success_rate': 0.60,
        'min_mean_oos_metric': 0.00,
        'min_avg_trade_count': 50.0,
    },
    'aggressive': {
        'min_rounds': 1,
        'min_success_rate': 0.50,
        'min_mean_oos_metric': -0.10,
        'min_avg_trade_count': 20.0,
    },
}


def resolve_promotion_criteria(preset: str = 'balanced', overrides: dict | None = None) -> dict:
    if preset not in PROMOTION_PRESETS:
        raise ValueError(f"unknown promotion preset: {preset}")

    result = dict(PROMOTION_PRESETS[preset])
    if overrides:
        for key, value in overrides.items():
            if value is not None:
                result[key] = value
    result['preset'] = preset
    return result
