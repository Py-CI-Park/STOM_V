from cli.condition_generator import (
    candidate_to_expression,
    generate_condition_code,
    generate_condition_expressions_from_analysis,
    expression_result_from_candidate_pack,
    generate_conditions_from_analysis,
    mark_diagnostic_fallback,
    validate_multi_hypothesis_candidate_pack,
    save_condition_code,
)


def test_candidate_to_expression_between():
    candidate = {
        'feature': 'B_시분초',
        'operator': 'between',
        'lower_bound': 90000,
        'upper_bound': 93000,
    }
    assert candidate_to_expression(candidate) == '90_000 <= B_시분초 < 93_000'


def test_generate_condition_code_contains_metadata_and_rules():
    candidates = [
        {
            'feature': 'B_등락율',
            'source': 'quantile',
            'operator': '<=',
            'threshold': 2.0,
            'count': 20,
            'mean_return': -1.0,
            'win_rate': 0.1,
        },
        {
            'feature': 'B_시분초',
            'source': 'time_of_day',
            'operator': 'between',
            'lower_bound': 90000,
            'upper_bound': 93000,
            'count': 20,
            'mean_return': -1.0,
            'win_rate': 0.1,
            'label': '장초반',
        },
    ]

    code = generate_condition_code(candidates)

    assert '# 자동 생성 필터' in code
    assert 'if 등락율 <=' in code
    assert 'if 90_000 <= 시분초 < 93_000: 매수 = False' in code
    assert 'source=time_of_day' in code


def test_generate_conditions_from_analysis_selects_top_n(tmp_path):
    analysis_result = {
        'recommended_candidates': [
            {'feature': 'B_등락율', 'source': 'quantile', 'operator': '<=', 'threshold': 2.0, 'score': 3.0},
            {'feature': 'B_시가총액', 'source': 'market_cap', 'operator': 'between', 'lower_bound': 0, 'upper_bound': 300_000_000_000, 'score': 2.0},
        ]
    }

    result = generate_conditions_from_analysis(analysis_result, top_n=1)
    assert result['status'] == 'ok'
    assert result['candidate_count'] == 1
    assert result['selected_candidates'][0]['feature'] == 'B_등락율'

    out_path = tmp_path / 'generated_conditions.py'
    save_result = save_condition_code(result['code'], str(out_path))
    assert save_result['status'] == 'ok'
    assert out_path.exists()

    expression_result = generate_condition_expressions_from_analysis(analysis_result, top_n=2)
    assert expression_result['candidate_count'] == 2
    assert expression_result['expressions'][0] == '등락율 <= 2'

    filtered = generate_condition_expressions_from_analysis(
        analysis_result,
        top_n=2,
        feature_whitelist=['B_시가총액'],
    )
    assert filtered['candidate_count'] == 1
    assert filtered['expressions'] == ['0 <= 시가총액 < 300_000_000_000']

    ranked = generate_condition_expressions_from_analysis(
        {
            'recommended_candidates': [
                {'feature': 'B_등락율', 'source': 'quantile', 'operator': '<=', 'threshold': 2.0, 'score': 1.0},
                {'feature': 'B_시가총액', 'source': 'market_cap', 'operator': 'between', 'lower_bound': 0, 'upper_bound': 300_000_000_000, 'score': 1.0},
            ]
        },
        top_n=1,
        feature_importance_map={'B_시가총액': 0.9, 'B_등락율': 0.1},
        ml_weight=1.0,
    )
    assert ranked['candidate_count'] == 1
    assert ranked['selected_candidates'][0]['feature'] == 'B_시가총액'


def _valid_candidate_pack():
    return {
        'schema_version': 1,
        'candidate_pack_id': 'pack-1',
        'context_pack_id': 'rcp-pack-1',
        'context_pack_sha256': 'sha-pack-1',
        'full_stom_sources_included': True,
        'prompt_budget_estimated_tokens': 125000,
        'mode_authority': 'repair_discovery_research_only',
        'generation_allowed': True,
        'parents': {
            'buy': {'id': 'buy-parent', 'code': 'if 체결강도 > 90:\n    매수 = True'},
            'sell': {'id': 'sell-parent', 'code': 'if 수익률 < -1:\n    매도 = True'},
        },
        'candidates': [
            {
                'hypothesis_id': 'A',
                'lane': 'repair',
                'expression': '체결강도 > 100',
                'intended_hypothesis': 'conservative repair',
                'mutation_axis': 'entry_strength',
                'expected_effect': 'reduce weak entries',
                'risk_note': 'may reduce trades',
                'parent_buy_id': 'buy-parent',
                'parent_sell_id': 'sell-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'B',
                'lane': 'repair',
                'expression': '등락율 < 5',
                'intended_hypothesis': 'alternate repair',
                'mutation_axis': 'overheat_cap',
                'expected_effect': 'reduce chase losses',
                'risk_note': 'may miss breakouts',
                'parent_buy_id': 'buy-parent',
                'analysis_card_id': 'analysis-1',
                'preserves_parent_structure': True,
            },
            {
                'hypothesis_id': 'C',
                'lane': 'discovery',
                'expression': '거래대금 > 1000',
                'intended_hypothesis': 'discover liquidity regime',
                'mutation_axis': 'liquidity_regime',
                'expected_effect': 'find new coverage',
                'risk_note': 'may overtrade liquid names',
                'coverage_bucket_keys': ['liquidity-midday'],
                'novelty': {'coverage_regime': 'midday-liquidity'},
                'novelty_rationale': 'new market segment and feature family',
            },
            {
                'hypothesis_id': 'bad',
                'lane': 'discovery',
                'expression': '체결강도 > 100',
                'intended_hypothesis': 'duplicate invalid sibling',
                'mutation_axis': 'dup',
                'expected_effect': 'none',
                'risk_note': 'dup',
                'coverage_bucket_keys': ['dup'],
                'novelty': {'feature_family': 'dup'},
                'novelty_rationale': 'dup',
            },
        ],
    }


def test_multi_hypothesis_candidate_pack_isolates_invalid_siblings():
    validation = validate_multi_hypothesis_candidate_pack(_valid_candidate_pack())
    assert validation['valid'] is True
    assert validation['valid_candidate_count'] == 3
    assert validation['invalid_candidate_count'] == 1
    assert validation['lane_counts'] == {'repair': 2, 'discovery': 1}
    assert validation['invalid_candidates'][0]['failure_reasons'] == ['duplicate_expression']

    expression_result = expression_result_from_candidate_pack(_valid_candidate_pack(), planned_count=3)
    assert expression_result['status'] == 'ok'
    assert expression_result['source'] == 'llm_multi_hypothesis_candidate_pack'
    assert expression_result['fallback_used'] is False
    assert expression_result['candidate_count'] == 3
    assert [item['hypothesis_id'] for item in expression_result['selected_candidates']] == ['A', 'B', 'C']
    first = expression_result['selected_candidates'][0]
    assert first['context_pack_id'] == 'rcp-pack-1'
    assert first['context_pack_sha256'] == 'sha-pack-1'
    assert first['candidate_contract_id'] == 'pack-1::A'
    assert first['full_stom_sources_included'] is True
    assert first['prompt_budget_estimated_tokens'] == 125000
    assert first['parent_buy_code'] == 'if 체결강도 > 90:\n    매수 = True'
    assert first['parent_sell_code'] == 'if 수익률 < -1:\n    매도 = True'
    assert first['parent_buy_sha256']
    assert first['parent_sell_sha256']


def test_multi_hypothesis_candidate_pack_rejects_weak_or_unsafe_packs():
    weak = _valid_candidate_pack()
    weak['candidates'] = weak['candidates'][:1]
    weak_result = expression_result_from_candidate_pack(weak, planned_count=3)
    assert weak_result['status'] == 'error'
    assert 'insufficient_valid_candidates' in weak_result['fallback_reason']
    assert 'missing_discovery_candidate' in weak_result['fallback_reason']

    not_object_result = expression_result_from_candidate_pack(['not-a-pack'], planned_count=3)
    assert not_object_result['status'] == 'error'
    assert 'candidate_pack_not_object' in not_object_result['fallback_reason']

    unsafe = _valid_candidate_pack()
    unsafe['candidates'][0]['can_live'] = True
    unsafe_result = validate_multi_hypothesis_candidate_pack(unsafe)
    assert unsafe_result['valid'] is True
    assert unsafe_result['invalid_candidate_count'] == 1
    unsafe_failures = [
        reason
        for item in unsafe_result['invalid_candidates']
        for reason in item['failure_reasons']
    ]
    assert 'authority_smuggling' in unsafe_failures

    pack_unsafe = _valid_candidate_pack()
    pack_unsafe['authority'] = {'can_live': True}
    pack_unsafe_result = expression_result_from_candidate_pack(pack_unsafe, planned_count=3)

    assert pack_unsafe_result['status'] == 'error'
    assert 'pack_authority_smuggling' in pack_unsafe_result['fallback_reason']
    assert pack_unsafe_result['candidate_count'] == 0

    top_level_unsafe = _valid_candidate_pack()
    top_level_unsafe['can_live'] = True
    top_level_unsafe_result = expression_result_from_candidate_pack(top_level_unsafe, planned_count=3)

    assert top_level_unsafe_result['status'] == 'error'
    assert 'pack_authority_smuggling' in top_level_unsafe_result['fallback_reason']

    nested_pack_unsafe = _valid_candidate_pack()
    nested_pack_unsafe['metadata'] = {'can_export': True}
    nested_pack_unsafe_result = expression_result_from_candidate_pack(nested_pack_unsafe, planned_count=3)

    assert nested_pack_unsafe_result['status'] == 'error'
    assert 'pack_authority_smuggling' in nested_pack_unsafe_result['fallback_reason']


def test_multi_hypothesis_candidate_pack_rejects_result_leakage_candidate():
    leaky = _valid_candidate_pack()
    leaky['candidates'][0]['expression'] = 'R_MFE < 0'

    validation = validate_multi_hypothesis_candidate_pack(leaky)

    assert validation['valid'] is True
    leak_failures = [
        reason
        for item in validation['invalid_candidates']
        for reason in item['failure_reasons']
    ]
    assert 'expression_uses_R_diagnostic' in leak_failures
    assert 'A' not in [item['hypothesis_id'] for item in validation['valid_candidates']]

    leaky_sell = _valid_candidate_pack()
    leaky_sell['candidates'][2]['expression'] = 'S_보유시간 > 10'

    validation_sell = validate_multi_hypothesis_candidate_pack(leaky_sell)
    sell_failures = [
        reason
        for item in validation_sell['invalid_candidates']
        for reason in item['failure_reasons']
    ]
    assert 'expression_uses_S_diagnostic' in sell_failures


def test_deterministic_generation_rejects_non_b_features_and_leaky_fallback():
    analysis_result = {
        'recommended_candidates': [
            {'feature': 'R_MFE', 'source': 'quantile', 'operator': '<=', 'threshold': 0, 'score': 9.0},
            {'feature': 'S_보유시간', 'source': 'ttest', 'operator': '>', 'threshold': 10, 'score': 8.0},
            {'feature': 'B_체결강도', 'source': 'quantile', 'operator': '>', 'threshold': 100, 'score': 7.0},
        ]
    }

    expression_result = generate_condition_expressions_from_analysis(analysis_result, top_n=3)

    assert expression_result['candidate_count'] == 1
    assert expression_result['expressions'] == ['체결강도 > 100']

    unsafe_fallback = mark_diagnostic_fallback(
        {
            'status': 'ok',
            'expressions': ['R_MFE < 0'],
            'selected_candidates': [{'source': 'quantile', 'feature': 'R_MFE'}],
            'candidate_count': 1,
        },
        reason='llm_candidate_pack_missing',
    )

    assert unsafe_fallback['status'] == 'error'
    assert unsafe_fallback['expressions'] == []
    assert 'diagnostic_fallback_expression_leakage' in unsafe_fallback['fallback_reason']


def test_deterministic_candidates_are_marked_diagnostic_fallback():
    fallback = mark_diagnostic_fallback(
        {
            'status': 'ok',
            'expressions': ['등락율 <= 2'],
            'selected_candidates': [{'source': 'quantile', 'feature': 'B_등락율'}],
            'candidate_count': 1,
        },
        reason='llm_candidate_pack_missing',
    )
    assert fallback['source'] == 'diagnostic_deterministic_candidate_fallback'
    assert fallback['fallback_used'] is True
    assert fallback['prompt_maturity_credit_allowed'] is False
    assert fallback['selected_candidates'][0]['fallback_reason'] == 'llm_candidate_pack_missing'
    assert fallback['selected_candidates'][0]['prompt_maturity_score'] == 0
