from cli.research_iteration_v5_recovery import build_v5_recovery_candidate_pool


BEST_CONTEXT = {
    'strategy_name': 'WideV1Final_B_20260425',
    'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
}


def _candidate(
    feature,
    operator='between',
    lower=1.0,
    upper=2.0,
    threshold=None,
    score=1.0,
    original_index=1,
):
    return {
        'feature': feature,
        'operator': operator,
        'lower_bound': lower,
        'upper_bound': upper,
        'threshold': threshold,
        'score': score,
        'combined_score': score,
        'source': 'quantile',
        'count': 100,
        'original_index': original_index,
    }


def test_v5_recovery_keeps_existing_v4_candidates_without_recovery():
    existing = [{
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
    }]

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[],
        existing_v4_result={'candidates': existing, 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=1,
    )

    assert result['recovery_attempted'] is False
    assert result['recovery_reason'] == 'direct_v4_available'
    assert result['initial_v4_candidate_count'] == 1
    assert result['requested_candidate_count'] == 1
    assert result['recovery_needed_count'] == 0
    assert result['candidates'] == existing
    assert result['recovery_family_counts'] == {'direct_v4': 1}


def test_v5_recovery_supplements_direct_v4_shortfall():
    existing = [{
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
        'score': 20.0,
        'combined_score': 20.0,
        'conditions': [
            {
                'feature': 'B_PRIMARY',
                'operator': 'between',
                'lower_bound': 66.999,
                'upper_bound': 2580.0,
                'threshold': None,
            },
            {
                'feature': 'B_TRADE',
                'operator': '>',
                'lower_bound': None,
                'upper_bound': None,
                'threshold': 5.0,
            },
        ],
    }]

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate(
                'B_TRADE',
                operator='>',
                lower=None,
                upper=None,
                threshold=5.2,
                score=4.0,
                original_index=1,
            ),
            _candidate('B_STRENGTH', lower=70.0, upper=90.0, score=3.0, original_index=2),
            _candidate('B_PRICE', lower=8000.0, upper=12000.0, score=2.0, original_index=3),
        ],
        existing_v4_result={'candidates': existing, 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=3,
    )

    sources = [candidate['v5_candidate_source'] for candidate in result['candidates']]

    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'direct_v4_shortfall'
    assert result['initial_v4_candidate_count'] == 1
    assert result['requested_candidate_count'] == 3
    assert result['recovery_needed_count'] == 2
    assert result['recovery_family_counts']['direct_v4'] == 1
    assert result['final_candidate_pool_count'] >= 3
    assert result['candidate_count'] == len(result['candidates'])
    assert sources[0] == 'direct_v4'
    assert 'recovered_trade_feature' in sources
    assert 'auto_secondary_feature' in sources


def test_v5_recovery_dedupe_prefers_direct_v4_when_recovery_duplicates_it():
    direct = {
        'expression': '66.999 <= PRIMARY < 2_580 and TRADE > 5.2',
        'v4_candidate_type': 'v4_repair_trade_amount',
        'v5_candidate_source': 'direct_v4',
        'score': 1.0,
        'combined_score': 1.0,
        'conditions': [
            {
                'feature': 'B_PRIMARY',
                'operator': 'between',
                'lower_bound': 66.999,
                'upper_bound': 2580.0,
                'threshold': None,
            },
            {
                'feature': 'B_TRADE',
                'operator': '>',
                'lower_bound': None,
                'upper_bound': None,
                'threshold': 5.2,
            },
        ],
    }

    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate(
                'B_TRADE',
                operator='>',
                lower=None,
                upper=None,
                threshold=5.2,
                score=10.0,
                original_index=1,
            ),
        ],
        existing_v4_result={'candidates': [direct], 'candidate_count': 1},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=2,
    )

    matching = [
        candidate for candidate in result['candidates']
        if candidate['expression'] == '66.999 <= PRIMARY < 2_580 and TRADE > 5.2'
    ]

    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'direct_v4_shortfall'
    assert len(matching) == 1
    assert matching[0]['v5_candidate_source'] == 'direct_v4'
    assert result['recovery_family_counts']['direct_v4'] == 1


def test_v5_recovery_builds_trade_feature_candidates_from_full_recommended_candidates():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_STRENGTH', score=5.0, original_index=1),
            _candidate(
                'B_TRADE',
                operator='>',
                lower=None,
                upper=None,
                threshold=5.2,
                score=4.0,
                original_index=2,
            ),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=2,
    )

    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_family_counts']['recovered_trade_feature'] == 1
    assert any(candidate['v5_candidate_source'] == 'recovered_trade_feature' for candidate in result['candidates'])
    assert any('66.999 <= PRIMARY < 2_580' in candidate['expression'] for candidate in result['candidates'])
    assert any('TRADE > 5.2' in candidate['expression'] for candidate in result['candidates'])


def test_v5_recovery_builds_auto_secondary_candidates_when_secondary_features_are_empty():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_STRENGTH', lower=70.0, upper=90.0, score=5.0, original_index=1),
            _candidate('B_PRICE', lower=8000.0, upper=12000.0, score=3.0, original_index=2),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=2,
    )

    auto_candidates = [
        candidate for candidate in result['candidates']
        if candidate['v5_candidate_source'] == 'auto_secondary_feature'
    ]
    assert result['recovery_family_counts']['auto_secondary_feature'] == 4
    assert len(auto_candidates) == 4
    assert any(candidate['secondary_feature'] == 'B_STRENGTH' for candidate in auto_candidates)
    assert any('STRENGTH' in candidate['expression'] for candidate in auto_candidates)


def test_v5_recovery_uses_safe_recommended_fallback_when_trade_and_secondary_are_missing():
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[
            _candidate('B_PRIMARY', lower=3000.0, upper=5000.0, score=9.0, original_index=1),
            _candidate(
                'B_TURNOVER',
                operator='>',
                lower=None,
                upper=None,
                threshold=1.5,
                score=2.0,
                original_index=2,
            ),
        ],
        existing_v4_result={'candidates': [], 'candidate_count': 2},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=['B_MISSING'],
        candidate_count=2,
    )

    fallback_candidates = [
        candidate for candidate in result['candidates']
        if candidate['v5_candidate_source'] == 'safe_recommended_fallback'
    ]
    assert result['recovery_family_counts']['safe_recommended_fallback'] == 1
    assert len(fallback_candidates) == 1
    assert 'TURNOVER > 1.5' in fallback_candidates[0]['expression']
    assert 'PRIMARY' in fallback_candidates[0]['expression']


def test_v5_recovery_dedupes_candidates_and_records_final_pool_count():
    duplicate_trade = _candidate(
        'B_TRADE',
        operator='>',
        lower=None,
        upper=None,
        threshold=5.2,
        score=4.0,
        original_index=2,
    )
    result = build_v5_recovery_candidate_pool(
        full_recommended_candidates=[duplicate_trade, dict(duplicate_trade)],
        existing_v4_result={'candidates': [], 'candidate_count': 0},
        best_context=BEST_CONTEXT,
        primary_feature='B_PRIMARY',
        trade_amount_feature='B_TRADE',
        secondary_features=[],
        candidate_count=2,
    )

    expressions = [candidate['expression'] for candidate in result['candidates']]
    assert len(expressions) == len(set(expressions))
    assert result['final_candidate_pool_count'] == len(result['candidates'])
    assert result['candidate_count'] == len(result['candidates'])
