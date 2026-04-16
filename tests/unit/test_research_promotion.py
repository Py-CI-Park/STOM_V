from cli.research_promotion import evaluate_research_candidate


def _comparison():
    return {
        'baseline_summary': {'trade_count': 100, 'avg_return': -0.2, 'win_rate': 0.40, 'avg_mae': -1.5, 'total_profit': -1000, 'date_concentration': 0.10, 'symbol_concentration': 0.10},
        'candidate_summary': {'trade_count': 85, 'avg_return': 0.1, 'win_rate': 0.48, 'avg_mae': -1.0, 'total_profit': 500, 'date_concentration': 0.12, 'symbol_concentration': 0.15},
        'excluded_summary': {'trade_count': 20, 'avg_return': -1.2, 'win_rate': 0.10, 'avg_mae': -2.2},
        'new_summary': {'trade_count': 5, 'avg_return': 0.2, 'win_rate': 0.60, 'avg_mae': -0.7},
        'trade_count_retention': 0.85,
        'trade_count_expansion': 0.05,
    }


def test_evaluate_research_candidate_passes_balanced_candidate():
    result = evaluate_research_candidate(_comparison())
    assert result['status'] == 'ok'
    assert result['passed'] is True
    assert result['reasons'] == []
    assert result['score'] > 0
    assert result['trade_count_retention_semantics'] == 'candidate_trade_count / baseline_trade_count'


def test_evaluate_research_candidate_rejects_low_trade_retention():
    comparison = _comparison()
    comparison['candidate_summary']['trade_count'] = 10
    comparison['trade_count_retention'] = 0.10
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'trade_count_retention<0.4' in result['reasons']


def test_evaluate_research_candidate_rejects_concentration():
    comparison = _comparison()
    comparison['candidate_summary']['date_concentration'] = 0.80
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'date_concentration>0.5' in result['reasons']


def test_evaluate_research_candidate_rejects_non_positive_score():
    comparison = _comparison()
    comparison['candidate_summary'].update({
        'avg_return': -0.3,
        'win_rate': 0.30,
        'avg_mae': -1.8,
        'total_profit': -2000,
    })
    comparison['excluded_summary']['avg_return'] = 0.0
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert result['reasons'] == ['score<=0']
    assert result['score'] <= 0


def test_evaluate_research_candidate_rejects_high_trade_retention():
    comparison = _comparison()
    comparison['trade_count_retention'] = 2.50
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'trade_count_retention>2.0' in result['reasons']


def test_evaluate_research_candidate_rejects_symbol_concentration():
    comparison = _comparison()
    comparison['candidate_summary']['symbol_concentration'] = 0.75
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'symbol_concentration>0.5' in result['reasons']


def test_evaluate_research_candidate_rejects_negative_date_concentration():
    comparison = _comparison()
    comparison['candidate_summary']['date_concentration'] = -0.01
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'invalid_date_concentration' in result['reasons']


def test_evaluate_research_candidate_rejects_negative_symbol_concentration():
    comparison = _comparison()
    comparison['candidate_summary']['symbol_concentration'] = -0.01
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'invalid_symbol_concentration' in result['reasons']


def test_evaluate_research_candidate_rejects_missing_baseline_summary():
    comparison = _comparison()
    del comparison['baseline_summary']
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'missing_baseline_summary' in result['reasons']


def test_evaluate_research_candidate_rejects_missing_candidate_summary():
    comparison = _comparison()
    del comparison['candidate_summary']
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'missing_candidate_summary' in result['reasons']


def test_evaluate_research_candidate_rejects_non_finite_retention_or_concentration():
    comparison = _comparison()
    comparison['trade_count_retention'] = float('nan')
    comparison['candidate_summary']['date_concentration'] = float('inf')
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'invalid_trade_count_retention' in result['reasons']
    assert 'invalid_date_concentration' in result['reasons']


def test_evaluate_research_candidate_rejects_non_numeric_score_contributor_without_exception():
    comparison = _comparison()
    comparison['candidate_summary']['avg_return'] = 'not-a-number'
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'invalid_avg_return_delta' in result['reasons']

    comparison = _comparison()
    comparison['candidate_summary']['total_profit'] = float('inf')
    result = evaluate_research_candidate(comparison)
    assert result['passed'] is False
    assert 'invalid_total_profit_delta' in result['reasons']


def test_evaluate_research_candidate_custom_gates_and_weights_still_work():
    comparison = _comparison()
    comparison['candidate_summary']['trade_count'] = 15
    comparison['trade_count_retention'] = 0.20
    result = evaluate_research_candidate(
        comparison,
        gates={'min_trade_count': 10, 'min_trade_count_retention': 0.10},
        weights={'avg_return_delta': 1.0, 'excluded_quality': 0.0},
    )
    assert result['passed'] is True
    assert result['reasons'] == []
    assert result['gates']['min_trade_count'] == 10
    assert result['weights']['avg_return_delta'] == 1.0
    assert result['score'] > 0


def test_evaluate_research_candidate_positive_score_with_mandatory_gate_reason_fails():
    comparison = _comparison()
    comparison['candidate_summary']['trade_count'] = 10
    result = evaluate_research_candidate(comparison)
    assert result['score'] > 0
    assert result['passed'] is False
    assert 'trade_count<20' in result['reasons']
