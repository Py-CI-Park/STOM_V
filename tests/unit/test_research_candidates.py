from cli.research_candidates import candidate_to_expression, generate_segment_filter_candidates, reject_leaky_expression


def test_candidate_to_expression_for_single_axis_segment():
    candidate = {
        'level': 2,
        'conditions': [
            {'feature': 'B_시분초', 'operator': '<', 'threshold': 93000},
            {'feature': 'B_시가총액', 'operator': '<', 'threshold': 3000},
        ],
    }
    assert candidate_to_expression(candidate) == '시분초 < 93000 and 시가총액 < 3000'


def test_candidate_to_expression_for_between_range():
    candidate = {'level': 1, 'conditions': [{'feature': 'B_체결강도', 'operator': 'between', 'lower_bound': 80, 'upper_bound': 100}]}
    assert candidate_to_expression(candidate) == '80 <= 체결강도 < 100'


def test_reject_leaky_expression_blocks_sell_and_result_features():
    assert reject_leaky_expression('S_체결강도 < 90') is True
    assert reject_leaky_expression('R_MAE < -2') is True
    assert reject_leaky_expression('체결강도 < 90') is False


def test_generate_segment_filter_candidates_scores_weak_segments():
    segment_rows = [
        {'segment': '장초반', 'count': 100, 'avg_return': -1.2, 'win_rate': 0.2, 'avg_mae': -2.5, 'return_diff': -0.8, 'win_rate_diff': -0.2},
        {'segment': '오전', 'count': 100, 'avg_return': 0.4, 'win_rate': 0.6, 'avg_mae': -0.5, 'return_diff': 0.8, 'win_rate_diff': 0.2},
    ]
    candidates = generate_segment_filter_candidates(
        segment_rows,
        axis='B_시분초',
        segment_to_condition={'장초반': {'feature': 'B_시분초', 'operator': '<', 'threshold': 93000}},
        min_samples=30,
    )
    assert len(candidates) == 1
    assert candidates[0]['reason'] == 'weak_segment'
    assert candidates[0]['expression'] == '시분초 < 93000'
