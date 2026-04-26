from __future__ import annotations

# pyright: reportAny=none, reportExplicitAny=none, reportMissingTypeStubs=none

from typing import Any, TypeAlias

import pandas as pd

from cli.research_iteration_v4 import (
    annotate_candidate_rowset_proxy,
    build_v4_candidate_pool,
    estimate_candidate_rowset_proxy,
    select_rowset_diverse_candidates,
)

JsonDict: TypeAlias = dict[str, Any]

BEST_EXPRESSION = '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4'
BEST_CONTEXT = {
    'strategy_name': 'WideV1IterationV2_20260423__cand005',
    'expression': BEST_EXPRESSION,
    'reference_adjusted_score': 13497.662902097409,
}


def _candidate(
    feature: str,
    lower: float,
    upper: float,
    *,
    score: float = 1.0,
    retention: float = 0.9,
    original_index: int | None = None,
) -> JsonDict:
    candidate: JsonDict = {
        'feature': feature,
        'operator': 'between',
        'lower_bound': lower,
        'upper_bound': upper,
        'score': score,
        'combined_score': score,
        'source': 'quantile',
        'retention_estimate': {'estimated_retention': retention},
        'retention_filter_passed': True,
        'retention_fallback_used': False,
        'expression': f'{lower} <= {feature[2:]} < {upper}',
    }
    if original_index is not None:
        candidate['original_index'] = original_index
    return candidate


def _threshold_candidate(
    feature: str,
    operator: str,
    threshold: float,
    *,
    score: float = 1.0,
    retention: float = 0.9,
) -> JsonDict:
    return {
        'feature': feature,
        'operator': operator,
        'lower_bound': None,
        'upper_bound': None,
        'threshold': threshold,
        'score': score,
        'combined_score': score,
        'source': 'ttest',
        'retention_estimate': {'estimated_retention': retention},
        'retention_filter_passed': True,
        'retention_fallback_used': False,
        'expression': f'{feature[2:]} {operator} {threshold}',
    }


def _baseline_frame() -> pd.DataFrame:
    return pd.DataFrame({
        '시가총액': [100.0, 200.0, 300.0, 400.0],
        '당일거래대금': [1900.0, 2500.0, 4000.0, 1000.0],
        '체결강도': [10.0, 20.0, 30.0, 40.0],
        '등락율': [1.0, 2.0, 3.0, 4.0],
    })


def test_build_v4_candidate_pool_generates_v4_families():
    result = build_v4_candidate_pool(
        [
            _candidate('B_체결강도', 0.0, 25.0, score=8.0),
            _candidate('B_등락율', 0.0, 3.0, score=7.0),
            _candidate('B_당일거래대금', 1000.0, 5000.0, score=6.0),
            _candidate('B_당일거래대금', 1500.0, 3000.0, score=5.0),
        ],
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금'],
    )

    assert result['status'] == 'ok'
    assert result['mode'] == 'best_feature_mix_v4'
    assert result['control_candidate']['v4_candidate_type'] == 'v4_control_keep_best'
    assert result['type_counts']['v4_tighten_secondary'] >= 1
    assert result['type_counts']['v4_replace_secondary'] >= 1
    assert result['type_counts']['v4_repair_trade_amount'] >= 1
    assert result['type_counts']['v4_relax_trade_amount'] >= 1


def test_build_v4_candidate_pool_classifies_threshold_trade_amount_relax():
    result = build_v4_candidate_pool(
        [
            _threshold_candidate('B_당일거래대금', '>=', 500.0, score=6.0),
            _threshold_candidate('B_당일거래대금', '>=', 1500.0, score=5.0),
        ],
        best_context={
            **BEST_CONTEXT,
            'expression': '시가총액 >= 100 and 당일거래대금 >= 1000',
        },
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_당일거래대금'],
    )

    trade_candidates = {
        item['conditions'][1]['threshold']: item['v4_candidate_type']
        for item in result['candidates']
    }

    assert trade_candidates[500.0] == 'v4_relax_trade_amount'
    assert trade_candidates[1500.0] == 'v4_repair_trade_amount'


def test_build_v4_candidate_pool_preserves_original_index_for_selection_tie_breaks():
    result = build_v4_candidate_pool(
        [
            _candidate('B_aaa', 0.0, 10.0, score=5.0, original_index=2),
            _candidate('B_zzz', 0.0, 10.0, score=5.0, original_index=1),
        ],
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_aaa', 'B_zzz'],
    )
    replace_candidates = [
        dict(item)
        for item in result['candidates']
        if item['v4_candidate_type'] == 'v4_replace_secondary'
    ]
    for item in replace_candidates:
        if item['secondary_feature'] == 'B_aaa':
            item['rowset_proxy'] = {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'aaa',
                'proxy_retention': 0.95,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            }
        else:
            item['rowset_proxy'] = {
                'proxy_signature': frozenset({1, 2, 3}),
                'proxy_signature_hash': 'zzz',
                'proxy_retention': 0.95,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            }

    selected, _summary = select_rowset_diverse_candidates(
        replace_candidates,
        candidate_count=1,
        min_retention=0.4,
        family_targets={'v4_replace_secondary': 1},
    )

    assert [item['secondary_feature'] for item in selected] == ['B_zzz']


def test_estimate_candidate_rowset_proxy_groups_identical_masks():
    frame = _baseline_frame()

    first = estimate_candidate_rowset_proxy(frame, '체결강도 < 25')
    second = estimate_candidate_rowset_proxy(frame, '체결강도 <= 20')
    distinct = estimate_candidate_rowset_proxy(frame, '등락율 <= 3')

    assert first['evaluation_error'] is None
    assert first['proxy_removed_count'] == 2
    assert first['proxy_kept_count'] == 2
    assert first['proxy_retention'] == 0.5
    assert first['proxy_signature'] == second['proxy_signature']
    assert first['proxy_signature'] != distinct['proxy_signature']


def test_annotate_candidate_rowset_proxy_records_hash_and_counts():
    annotated = annotate_candidate_rowset_proxy(
        [
            {'expression': '체결강도 < 25', 'v4_candidate_type': 'v4_tighten_secondary'},
            {'expression': '등락율 < 3', 'v4_candidate_type': 'v4_replace_secondary'},
        ],
        _baseline_frame(),
        min_retention=0.4,
    )

    assert annotated[0]['rowset_proxy']['proxy_retention'] == 0.5
    assert annotated[0]['rowset_proxy']['proxy_filter_passed'] is True
    assert isinstance(annotated[0]['rowset_proxy']['proxy_signature_hash'], str)
    assert 'proxy_signature' in annotated[0]['rowset_proxy']


def test_select_rowset_diverse_candidates_skips_duplicate_proxy_groups_and_honors_family_targets():
    candidates = [
        {
            'expression': 'tighten-a',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 100.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'a',
                'proxy_retention': 0.90,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'tighten-duplicate',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 99.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'a',
                'proxy_retention': 0.90,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'repair-a',
            'v4_candidate_type': 'v4_repair_trade_amount',
            'combined_score': 80.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({2, 3}),
                'proxy_signature_hash': 'b',
                'proxy_retention': 0.85,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'replace-a',
            'v4_candidate_type': 'v4_replace_secondary',
            'combined_score': 70.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({3, 4}),
                'proxy_signature_hash': 'c',
                'proxy_retention': 0.80,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
    ]

    selected, summary = select_rowset_diverse_candidates(
        candidates,
        candidate_count=3,
        min_retention=0.4,
        family_targets={
            'v4_repair_trade_amount': 1,
            'v4_replace_secondary': 1,
            'v4_tighten_secondary': 1,
            'v4_relax_trade_amount': 1,
        },
    )

    assert [item['expression'] for item in selected] == ['repair-a', 'replace-a', 'tighten-a']
    assert 'tighten-duplicate' not in [item['expression'] for item in selected]
    assert summary['status'] == 'ok'
    assert summary['phase'] == 'rowset_diverse_candidates_selected'
    assert summary['proxy_group_count'] == 3
    assert summary['skipped_duplicate_proxy_count'] == 1
    assert summary['selected_proxy_groups'] == ['b', 'c', 'a']
    assert summary['passed_count'] == 4
    assert summary['fallback_count'] == 0
    assert summary['allow_retention_fallback'] is False
    assert summary['quota_summary']['v4_relax_trade_amount']['shortfall'] == 1


def test_select_rowset_diverse_candidates_prefers_proxy_target_distance_before_score():
    candidates = [
        {
            'expression': 'high-score-far-retention',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 100.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2}),
                'proxy_signature_hash': 'far',
                'proxy_retention': 0.87,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'lower-score-target-retention',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 10.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2, 3}),
                'proxy_signature_hash': 'target',
                'proxy_retention': 0.95,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
    ]

    selected, _summary = select_rowset_diverse_candidates(
        candidates,
        candidate_count=1,
        min_retention=0.4,
        family_targets={'v4_tighten_secondary': 1},
    )

    assert [item['expression'] for item in selected] == ['lower-score-target-retention']


def test_select_rowset_diverse_candidates_rechecks_min_retention_argument():
    candidates = [
        {
            'expression': 'low-retention',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 100.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1}),
                'proxy_signature_hash': 'a',
                'proxy_retention': 0.10,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
        {
            'expression': 'high-retention',
            'v4_candidate_type': 'v4_tighten_secondary',
            'combined_score': 10.0,
            'rowset_proxy': {
                'proxy_signature': frozenset({1, 2, 3}),
                'proxy_signature_hash': 'b',
                'proxy_retention': 0.95,
                'proxy_filter_passed': True,
                'evaluation_error': None,
            },
        },
    ]

    selected, summary = select_rowset_diverse_candidates(
        candidates,
        candidate_count=1,
        min_retention=0.9,
        family_targets={'v4_tighten_secondary': 1},
    )

    assert [item['expression'] for item in selected] == ['high-retention']
    assert summary['eligible_count'] == 1
