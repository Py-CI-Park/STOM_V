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
