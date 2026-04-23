from cli.research_iteration_v2 import (
    build_v2_candidate_pool,
    candidate_from_expression,
    candidate_signature,
    filter_duplicate_v2_candidates,
)


BEST_CONTEXT = {
    'strategy_name': 'WideV1RetentionCand5_20260422__cand003',
    'expression': '66.999 <= 시가총액 < 2_580',
    'source_candidate': {
        'feature': 'B_시가총액',
        'operator': 'between',
        'lower_bound': 66.999,
        'upper_bound': 2580.0,
        'score': 0.2237,
        'source': 'quantile',
    },
    'rank_score': {
        'adjusted_score': 10943.034141541459,
        'trade_count_retention': 0.9018247551115128,
    },
}


def _candidate(feature, lower, upper, score=1.0, retention=0.9, source='quantile'):
    return {
        'feature': feature,
        'operator': 'between',
        'lower_bound': lower,
        'upper_bound': upper,
        'score': score,
        'combined_score': score,
        'source': source,
        'retention_estimate': {'estimated_retention': retention},
        'retention_filter_passed': True,
        'retention_fallback_used': False,
        'expression': f'{lower} <= {feature[2:]} < {upper}',
    }


def test_candidate_signature_uses_feature_operator_and_bounds():
    candidate = _candidate('B_시가총액', 66.999, 2580.0)

    assert candidate_signature(candidate) == ('B_시가총액', 'between', 66.999, 2580.0, None)


def test_candidate_signature_distinguishes_threshold_candidates():
    first = {
        'feature': 'B_threshold',
        'operator': '<=',
        'threshold': 1,
    }
    second = {
        'feature': 'B_threshold',
        'operator': '<=',
        'threshold': 2,
    }

    assert candidate_signature(first) == ('B_threshold', '<=', None, None, 1)
    assert candidate_signature(second) == ('B_threshold', '<=', None, None, 2)
    assert candidate_signature(first) != candidate_signature(second)


def test_filter_duplicate_v2_candidates_drops_near_duplicate_retention():
    candidates = [
        _candidate('B_시가총액', 66.999, 2580.0, score=1.0, retention=0.900),
        _candidate('B_시가총액', 66.999, 2580.0, score=2.0, retention=0.905),
        _candidate('B_체결강도', 0.009, 55.94, score=3.0, retention=0.900),
    ]

    result = filter_duplicate_v2_candidates(candidates, retention_tolerance=0.02)

    assert [item['feature'] for item in result] == ['B_시가총액', 'B_체결강도']
    assert result[0]['score'] == 1.0


def test_build_v2_candidate_pool_prefers_primary_variants_and_combinations():
    analysis_candidates = [
        _candidate('B_시가총액', 50.0, 2580.0, score=10.0, retention=0.88),
        _candidate('B_시가총액', 66.999, 3000.0, score=9.0, retention=0.87),
        _candidate('B_체결강도', 0.009, 55.94, score=8.0, retention=0.90),
        _candidate('B_등락율', 15.894, 25.0, score=7.0, retention=0.91),
        _candidate('B_당일거래대금', 1800.0, 3586.0, score=6.0, retention=0.92),
        _candidate('B_시분초', 90029.999, 90055.0, score=5.0, retention=0.98),
    ]

    result = build_v2_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금', 'B_시분초'],
        include_secondary_only=True,
        max_secondary_only=1,
        retention_tolerance=0.02,
    )

    expressions = [item['expression'] for item in result['candidates']]
    assert result['status'] == 'ok'
    assert result['primary_feature'] == 'B_시가총액'
    assert any('시가총액' in expression for expression in expressions)
    assert any(' and ' in expression for expression in expressions)
    assert result['mode'] == 'best_feature_mix'
    assert result['candidate_count'] == len(result['candidates'])
    assert result['type_counts']['primary_variant'] >= 1
    assert result['type_counts']['primary_secondary_combo'] >= 1
    assert result['type_counts']['secondary_only'] == 1


def test_candidate_from_expression_parses_best_between_expression():
    candidate = candidate_from_expression(
        '66.999 <= 시가총액 < 2_580',
        feature='B_시가총액',
    )

    assert candidate['feature'] == 'B_시가총액'
    assert candidate['operator'] == 'between'
    assert candidate['lower_bound'] == 66.999
    assert candidate['upper_bound'] == 2580.0
    assert candidate['source'] == 'best_context'


def test_build_v2_candidate_pool_uses_best_context_source_as_combo_seed():
    best_context = {
        **BEST_CONTEXT,
        'source_candidate': candidate_from_expression(
            '66.999 <= 시가총액 < 2_580',
            feature='B_시가총액',
        ),
    }
    analysis_candidates = [
        _candidate('B_시가총액', 50.0, 2580.0, score=10.0, retention=0.88),
        _candidate('B_체결강도', 0.009, 55.94, score=8.0, retention=0.90),
    ]

    result = build_v2_candidate_pool(
        analysis_candidates,
        best_context=best_context,
        primary_feature='B_시가총액',
        secondary_features=['B_체결강도'],
        include_secondary_only=False,
    )

    combo = [
        item for item in result['candidates']
        if item['v2_candidate_type'] == 'primary_secondary_combo'
    ][0]
    assert combo['primary_feature'] == 'B_시가총액'
    assert combo['expression'].startswith('66.999 <= 시가총액 < 2_580 and ')


def test_build_v2_candidate_pool_copies_secondary_features():
    secondary_features = ['B_secondary']

    result = build_v2_candidate_pool(
        [],
        best_context=BEST_CONTEXT,
        primary_feature='B_primary',
        secondary_features=secondary_features,
    )
    secondary_features.append('B_late_mutation')

    assert result['secondary_features'] == ['B_secondary']
    assert result['secondary_features'] is not secondary_features


def test_build_v2_candidate_pool_returns_disabled_when_no_context():
    result = build_v2_candidate_pool([], best_context=None)

    assert result['status'] == 'disabled'
    assert result['candidates'] == []
