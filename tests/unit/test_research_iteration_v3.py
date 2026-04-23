from cli.research_iteration_v3 import (
    build_v3_candidate_pool,
    parse_best_expression_conditions,
)


BEST_EXPRESSION = '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4'
BEST_CONTEXT = {
    'strategy_name': 'WideV1IterationV2_20260423__cand005',
    'expression': BEST_EXPRESSION,
    'reference_adjusted_score': 13497.662902097409,
}


def _candidate(feature, lower, upper, score=1.0, retention=0.9):
    return {
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


def test_parse_best_expression_conditions_parses_primary_and_trade_amount():
    conditions = parse_best_expression_conditions(
        BEST_EXPRESSION,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
    )

    assert [item['feature'] for item in conditions] == ['B_시가총액', 'B_당일거래대금']
    assert conditions[0]['lower_bound'] == 66.999
    assert conditions[0]['upper_bound'] == 2580.0
    assert conditions[1]['lower_bound'] == 1805.7
    assert conditions[1]['upper_bound'] == 3654.4


def test_parse_best_expression_conditions_tolerates_newline_around_and():
    conditions = parse_best_expression_conditions(
        '66.999 <= 시가총액 < 2_580\nand 1805.7 <= 당일거래대금 < 3654.4',
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
    )

    assert [item['feature'] for item in conditions] == ['B_시가총액', 'B_당일거래대금']
    assert conditions[0]['upper_bound'] == 2580.0
    assert conditions[1]['lower_bound'] == 1805.7


def test_build_v3_candidate_pool_returns_control_metadata_without_running_control():
    result = build_v3_candidate_pool(
        [],
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도'],
    )

    assert result['status'] == 'ok'
    assert result['mode'] == 'best_feature_mix_v3'
    assert result['control_candidate']['v3_candidate_type'] == 'v3_control_keep_best'
    assert result['control_candidate']['strategy_name'] == 'WideV1IterationV2_20260423__cand005'
    assert result['control_candidate']['expression'] == BEST_EXPRESSION
    assert result['control_candidate']['skip_backtest'] is True
    assert result['type_counts']['v3_control_keep_best'] == 1
    assert result['candidates'] == []


def test_build_v3_candidate_pool_generates_tighten_repair_and_replace_families():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, score=8.0),
        _candidate('B_등락율', 15.894, 25.0, score=7.0),
        _candidate('B_당일거래대금', 1500.0, 3654.4, score=6.0),
        _candidate('B_당일거래대금', 178.999, 1805.7, score=5.0),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율', 'B_당일거래대금'],
    )

    expressions_by_type = {
        item['v3_candidate_type']: item['expression']
        for item in result['candidates']
    }
    assert 'v3_tighten_secondary' in result['type_counts']
    assert 'v3_repair_trade_amount' in result['type_counts']
    assert 'v3_replace_secondary' in result['type_counts']
    assert (
        '66.999 <= 시가총액 < 2_580 and 1805.7 <= 당일거래대금 < 3654.4 and '
        in expressions_by_type['v3_tighten_secondary']
    )
    assert (
        '66.999 <= 시가총액 < 2_580 and 1500.0 <= 당일거래대금 < 3654.4'
        == expressions_by_type['v3_repair_trade_amount']
    )
    assert (
        '66.999 <= 시가총액 < 2_580 and 0.039 <= 체결강도 < 54.89'
        == expressions_by_type['v3_replace_secondary']
    )


def test_build_v3_candidate_pool_filters_low_retention_when_retention_is_known():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, retention=0.2),
        _candidate('B_등락율', 15.894, 25.0, retention=0.8),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율'],
        min_estimated_retention=0.4,
    )

    expressions = [item['expression'] for item in result['candidates']]
    assert all('체결강도' not in expression for expression in expressions)
    assert any('등락율' in expression for expression in expressions)


def test_build_v3_candidate_pool_filters_low_retention_by_default():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, retention=0.2),
        _candidate('B_등락율', 15.894, 25.0, retention=0.8),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도', 'B_등락율'],
    )

    expressions = [item['expression'] for item in result['candidates']]
    assert all('체결강도' not in expression for expression in expressions)
    assert any('등락율' in expression for expression in expressions)


def test_build_v3_candidate_pool_skips_identical_trade_amount_repair():
    analysis_candidates = [
        _candidate('B_당일거래대금', 1805.7, 3654.4, score=6.0),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_당일거래대금'],
    )

    repair_candidates = [
        item for item in result['candidates']
        if item['v3_candidate_type'] == 'v3_repair_trade_amount'
    ]
    assert repair_candidates == []


def test_build_v3_candidate_pool_removes_duplicate_expressions():
    analysis_candidates = [
        _candidate('B_체결강도', 0.039, 54.89, score=8.0, retention=0.90),
        _candidate('B_체결강도', 0.039, 54.89, score=9.0, retention=0.91),
    ]

    result = build_v3_candidate_pool(
        analysis_candidates,
        best_context=BEST_CONTEXT,
        primary_feature='B_시가총액',
        trade_amount_feature='B_당일거래대금',
        secondary_features=['B_체결강도'],
        retention_tolerance=0.02,
    )

    tighten = [
        item for item in result['candidates']
        if item['v3_candidate_type'] == 'v3_tighten_secondary'
    ]
    replace = [
        item for item in result['candidates']
        if item['v3_candidate_type'] == 'v3_replace_secondary'
    ]
    assert len(tighten) == 1
    assert len(replace) == 1
