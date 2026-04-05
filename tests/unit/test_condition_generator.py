from cli.condition_generator import (
    candidate_to_expression,
    generate_condition_code,
    generate_condition_expressions_from_analysis,
    generate_conditions_from_analysis,
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
