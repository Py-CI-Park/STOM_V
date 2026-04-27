import json

from cli.research_optimizer import run_wide_v2_optimizer
from cli.research_optimizer_state import WideV2OptimizerConfig


class DummyController:
    pass


def _round_result(name, expression, score):
    return {
        'status': 'ok',
        'phase': 'candidates_evaluated',
        'best_candidate': {
            'index': 1,
            'strategy_name': name,
            'expression': expression,
            'status': 'ok',
            'selected_as_best': True,
            'actual_rowset_selected': True,
            'rank_score': {
                'promotion_passed': True,
                'promotion_score': score,
                'adjusted_score': score,
                'score_basis': 'reference',
                'trade_count': 100,
                'trade_count_retention': 0.5,
                'date_concentration': 0.2,
                'symbol_concentration': 0.1,
            },
        },
        'candidates': [
            {
                'index': 1,
                'strategy_name': name,
                'expression': expression,
                'status': 'ok',
                'selected_as_best': True,
                'actual_rowset_selected': True,
                'rank_score': {
                    'promotion_passed': True,
                    'promotion_score': score,
                    'adjusted_score': score,
                    'score_basis': 'reference',
                    'trade_count': 100,
                    'trade_count_retention': 0.5,
                    'date_concentration': 0.2,
                    'symbol_concentration': 0.1,
                },
            }
        ],
    }


def test_optimizer_runs_two_rounds_and_promotes_round_best_seed():
    calls = []
    results = [
        _round_result('WideV2__round001__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        _round_result('WideV2__round002__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2',
            base_buy_strategy='WideV1Final_B_20260425',
            sell_strategy='ResearchTest_Tick_S_090000_092800_Wide_20260419',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
            min_improvement=0.01,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'max_rounds_reached'
    assert len(calls) == 2
    assert calls[0].candidate_name_prefix == 'WideV2__round001'
    assert calls[0].iteration_v2_best_candidate == 'WideV1Final_B_20260425'
    assert calls[0].iteration_v2_best_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.83'
    assert calls[0].iteration_v2_trade_amount_feature == 'B_등락율'
    assert calls[1].candidate_name_prefix == 'WideV2__round002'
    assert calls[1].iteration_v2_best_candidate == 'WideV2__round001__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90'
    assert calls[1].iteration_v2_trade_amount_feature == 'B_등락율'
    assert result['final_best_candidate']['strategy_name'] == 'WideV2__round002__cand001'
    assert result['wfo_candidate']['strategy_name'] == 'WideV2__round002__cand001'


def test_optimizer_allows_legacy_best_feature_mix_seed_shape():
    calls = []

    def fake_runner(config, controller):
        calls.append(config)
        return _round_result('R1__cand001', 'legacy-single-condition-round-best', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2LegacyMix',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-single-condition-seed',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert calls[0].iteration_v2_mode == 'best_feature_mix'
    assert calls[0].iteration_v2_best_expression == 'legacy-single-condition-seed'
    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'max_rounds_reached'


def test_optimizer_stops_after_no_improvement_streak():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        _round_result('R2__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.70', 1.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2NoImprove',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=3,
            stop_after_no_improvement=1,
            min_improvement=0.01,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'no_improvement_streak_reached'
    assert result['final_best_candidate']['strategy_name'] == 'R1__cand001'


def test_optimizer_prefers_no_improvement_stop_before_invalid_next_seed():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        _round_result('R2__cand001', 'not parseable', 1.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2StopPrecedence',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=3,
            stop_after_no_improvement=1,
            min_improvement=0.01,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert result['status'] == 'ok'
    assert result['stop_reason'] == 'no_improvement_streak_reached'
    assert result['completed_round_count'] == 2


def test_optimizer_stops_before_next_round_when_seed_expression_is_invalid():
    calls = []

    def fake_runner(config, controller):
        calls.append(config)
        return _round_result('R1__cand001', 'not parseable', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2InvalidSeed',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'invalid_seed_expression'
    assert result['completed_round_count'] == 1


def test_optimizer_maps_research_runtime_error_and_preserves_completed_rounds():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0),
        {'status': 'error', 'phase': 'candidate_iteration_runtime_failure', 'message': 'maximum consecutive candidate failures reached'},
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RuntimeFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['completed_round_count'] == 1
    assert result['rounds'][1]['failure_message'] == 'maximum consecutive candidate failures reached'


def test_optimizer_maps_candidate_iteration_failure_to_runtime_failure():
    calls = []
    results = [
        {
            'status': 'error',
            'phase': 'candidate_iteration',
            'message': 'no candidate evaluated successfully',
        }
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2CandidateIterationFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['completed_round_count'] == 0
    assert result['rounds'][0]['failure_message'] == 'no candidate evaluated successfully'


def test_optimizer_maps_insufficient_retention_candidates_to_insufficient_candidates():
    calls = []
    results = [
        {
            'status': 'error',
            'phase': 'insufficient_retention_candidates',
            'message': 'retention filter removed too many candidates',
        }
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2InsufficientCandidates',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'insufficient_candidates'


def test_optimizer_exposes_explicit_final_and_wfo_contract():
    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2Contract',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90',
            1.0,
        ),
    )

    leaderboard_entry = result['final_best_candidate']
    raw_candidate = result['final_best_round_candidate']
    wfo_candidate = result['wfo_candidate']

    assert leaderboard_entry == result['final_best_leaderboard_entry']
    assert leaderboard_entry['strategy_name'] == 'R1__cand001'
    assert 'round_index' in leaderboard_entry
    assert 'source_candidate' in leaderboard_entry
    assert raw_candidate['strategy_name'] == 'R1__cand001'
    assert raw_candidate['selected_as_best'] is True
    assert 'round_index' not in raw_candidate
    assert set(wfo_candidate) >= {
        'strategy_name',
        'expression',
        'source_round',
        'source_candidate',
        'reason_selected',
        'next_command',
    }
    assert wfo_candidate['strategy_name'] == 'R1__cand001'
    assert wfo_candidate['source_round'] == 1
    assert wfo_candidate['source_candidate'] == 'Base'


def test_optimizer_writes_summary_and_leaderboard_json(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'

    def fake_runner(config, controller):
        return _round_result('R1__cand001', '66.999 <= 시가총액 < 2_580 and 등락율 > 4.90', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RuntimeOutput',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= 시가총액 < 2_580 and 등락율 > 4.83',
            iteration_v2_trade_amount_feature='B_등락율',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            runtime_output_path=str(runtime_output),
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    summary_path = tmp_path / 'wide_v2_summary.json'
    leaderboard_path = tmp_path / 'wide_v2_leaderboard.json'
    assert result['summary_output_path'] == str(summary_path)
    assert result['leaderboard_output_path'] == str(leaderboard_path)
    assert json.loads(summary_path.read_text(encoding='utf-8'))['stop_reason'] == 'max_rounds_reached'
    assert json.loads(leaderboard_path.read_text(encoding='utf-8'))[0]['strategy_name'] == 'R1__cand001'
