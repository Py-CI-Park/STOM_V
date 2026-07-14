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


def _ranked_candidate(name, expression, score, *, rank, selected=False):
    return {
        'index': rank,
        'strategy_name': name,
        'expression': expression,
        'status': 'ok',
        'selected_as_best': selected,
        'actual_rowset_selected': True,
        'rank': rank,
        'rank_score': {
            'promotion_passed': True,
            'promotion_score': score,
            'adjusted_score': score,
            'score_basis': 'reference',
            'trade_count': 100,
            'trade_count_retention': 0.8,
            'date_concentration': 0.1,
            'symbol_concentration': 0.1,
        },
    }


def test_optimizer_records_round_best_next_seed_when_seed_compatible():
    calls = []
    results = [
        _round_result('R1__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 4.90', 1.0),
        _round_result('R2__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedRoundBest',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert calls[1].iteration_v2_best_candidate == 'R1__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= PRIMARY < 2_580 and TRADE > 4.90'
    assert result['rounds'][0]['next_seed_selection_status'] == 'round_best'
    assert result['rounds'][0]['next_seed_strategy_name'] == 'R1__cand001'
    assert result['next_seed_selection_status'] == 'round_best'
    assert result['next_seed_strategy_name'] == 'R1__cand001'


def test_optimizer_falls_back_to_seed_compatible_candidate_without_changing_global_best():
    calls = []
    incompatible_best = _ranked_candidate(
        'R1__cand003',
        '66.999 <= PRIMARY < 2_580 and OTHER > 1.50',
        10.0,
        rank=1,
        selected=True,
    )
    compatible_seed = _ranked_candidate(
        'R1__cand001',
        '66.999 <= PRIMARY < 2_580 and TRADE > 4.90',
        8.0,
        rank=2,
    )
    results = [
        {
            'status': 'ok',
            'phase': 'candidates_evaluated',
            'best_candidate': incompatible_best,
            'candidates': [incompatible_best, compatible_seed],
        },
        _round_result('R2__cand001', '66.999 <= PRIMARY < 2_580 and TRADE > 5.10', 2.0),
    ]

    def fake_runner(config, controller):
        calls.append(config)
        return results[len(calls) - 1]

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedFallback',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 2
    assert calls[1].iteration_v2_best_candidate == 'R1__cand001'
    assert calls[1].iteration_v2_best_expression == '66.999 <= PRIMARY < 2_580 and TRADE > 4.90'
    assert result['rounds'][0]['next_seed_selection_status'] == 'compatible_fallback'
    assert result['rounds'][0]['next_seed_strategy_name'] == 'R1__cand001'
    assert result['rounds'][0]['rejected_round_best_seed_strategy_name'] == 'R1__cand003'
    assert result['rounds'][0]['rejected_round_best_seed_reason'] == 'invalid_seed_expression'
    assert result['final_best_candidate']['strategy_name'] == 'R1__cand003'
    assert result['wfo_candidate']['strategy_name'] == 'R1__cand003'
    assert result['next_seed_selection_status'] == 'compatible_fallback'
    assert result['next_seed_strategy_name'] == 'R1__cand001'


def test_optimizer_reports_not_found_when_no_seed_compatible_candidate_exists():
    calls = []
    incompatible_best = _ranked_candidate(
        'R1__cand003',
        '66.999 <= PRIMARY < 2_580 and OTHER > 1.50',
        10.0,
        rank=1,
        selected=True,
    )
    incompatible_second = _ranked_candidate(
        'R1__cand004',
        '66.999 <= PRIMARY < 2_580 and STRENGTH > 20',
        8.0,
        rank=2,
    )

    def fake_runner(config, controller):
        calls.append(config)
        return {
            'status': 'ok',
            'phase': 'candidates_evaluated',
            'best_candidate': incompatible_best,
            'candidates': [incompatible_best, incompatible_second],
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SeedNotFound',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'invalid_seed_expression'
    assert result['completed_round_count'] == 1
    assert result['failed_round'] == 2
    assert result['failure_phase'] == 'invalid_seed_expression'
    assert result['failure_message'] == 'next seed expression is invalid'
    assert result['next_seed_selection_status'] == 'not_found'
    assert result['rejected_round_best_seed_strategy_name'] == 'R1__cand003'
    assert result['rejected_round_best_seed_expression'] == '66.999 <= PRIMARY < 2_580 and OTHER > 1.50'
    assert result['rounds'][0]['next_seed_selection_status'] == 'not_found'


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
    assert result['failed_round'] == 2
    assert result['failure_phase'] == 'candidate_iteration_runtime_failure'
    assert result['failure_message'] == 'maximum consecutive candidate failures reached'
    assert result['rounds'][1]['failure_message'] == 'maximum consecutive candidate failures reached'


def test_optimizer_maps_candidate_iteration_failure_to_runtime_failure():
    calls = []
    results = [
        {
            'status': 'error',
            'phase': 'candidate_iteration',
            'message': 'no candidate evaluated successfully',
            'candidates': [{
                'strategy_name': 'failed-fallback',
                'status': 'error',
                'fallback_used': True,
                'fallback_reason': 'provider_failed',
                'source_candidate': {'hypothesis_id': 'h-failed'},
                'candidate_result': {'status': 'error'},
                'promotion': {'passed': False},
            }],
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
    assert result['failed_round'] == 1
    assert result['failure_phase'] == 'candidate_iteration'
    assert result['failure_message'] == 'no candidate evaluated successfully'
    assert result['rounds'][0]['failure_message'] == 'no candidate evaluated successfully'
    lineage = result['rounds'][0]['failed_candidate_lineage']
    assert lineage[0]['strategy_name'] == 'failed-fallback'
    assert lineage[0]['fallback_used'] is True
    assert result['failed_candidate_lineage'] == lineage


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
    assert result['failed_round'] == 1
    assert result['failure_phase'] == 'insufficient_retention_candidates'
    assert result['failure_message'] == 'retention filter removed too many candidates'


def test_optimizer_preserves_v5_recovery_metadata_on_insufficient_candidates():
    def fake_runner(config, controller):
        return {
            'status': 'error',
            'phase': 'insufficient_retention_candidates',
            'message': 'candidate_count=2 requested but only 0 candidates selected after retention filtering',
            'requested_candidate_count': 2,
            'selected_candidate_count': 0,
            'initial_v4_candidate_count': 0,
            'recovery_attempted': True,
            'recovery_reason': 'v4_candidate_pool_empty',
            'recovery_family_counts': {'recovered_trade_feature': 1},
            'final_candidate_pool_count': 1,
            'eligible_count': 0,
            'execution_count': 0,
            'planned_execution_count': 0,
            'iteration_v5': {
                'recovery': {
                    'recovery_attempted': True,
                    'recovery_reason': 'v4_candidate_pool_empty',
                    'recovery_family_counts': {'recovered_trade_feature': 1},
                    'final_candidate_pool_count': 1,
                },
            },
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2RecoveryMetadata',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='66.999 <= PRIMARY < 2_580 and TRADE > 4.83',
            iteration_v2_primary_feature='B_PRIMARY',
            iteration_v2_trade_amount_feature='B_TRADE',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=3,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'insufficient_candidates'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 0
    assert result['initial_v4_candidate_count'] == 0
    assert result['recovery_attempted'] is True
    assert result['recovery_reason'] == 'v4_candidate_pool_empty'
    assert result['recovery_family_counts'] == {'recovered_trade_feature': 1}
    assert result['final_candidate_pool_count'] == 1
    assert result['eligible_count'] == 0


def test_optimizer_stops_when_actual_rowset_selection_is_duplicate_only():
    calls = []

    def fake_runner(config, controller):
        calls.append(config)
        return {
            **_round_result('R1__cand001', 'legacy-round-best-expression', 1.0),
            'actual_rowset_selection': {
                'status': 'shortfall',
                'row_set_identity_status': 'duplicate_only',
                'requested_count': 2,
                'selected_count': 1,
                'duplicate_actual_rowset_count': 1,
            },
        }

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2DuplicateOnly',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            candidate_count=2,
            max_rounds=2,
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    assert len(calls) == 1
    assert result['status'] == 'error'
    assert result['stop_reason'] == 'duplicate_rowset_only'
    assert result['completed_round_count'] == 0
    assert result['failed_round'] == 1
    assert result['failure_phase'] == 'actual_rowset_selection'
    assert result['requested_candidate_count'] == 2
    assert result['selected_candidate_count'] == 1
    assert result['final_best_candidate'] is None


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


def test_optimizer_returns_error_when_leaderboard_output_write_fails(tmp_path):
    blocked_leaderboard_path = tmp_path / 'blocked_leaderboard.json'
    blocked_leaderboard_path.mkdir()
    summary_path = tmp_path / 'summary.json'

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2LeaderboardWriteFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            leaderboard_output_path=str(blocked_leaderboard_path),
            summary_output_path=str(summary_path),
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            'legacy-round-best-expression',
            1.0,
        ),
    )

    summary_payload = json.loads(summary_path.read_text(encoding='utf-8'))

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['failure_phase'] == 'optimizer_leaderboard_output_write_failure'
    assert result['failure_message']
    assert result['output_write_failures'][0]['output_path'] == str(blocked_leaderboard_path)
    assert summary_payload['failure_phase'] == 'optimizer_leaderboard_output_write_failure'


def test_optimizer_returns_error_when_report_output_write_fails(tmp_path):
    blocked_report_path = tmp_path / 'blocked_report.md'
    blocked_report_path.mkdir()
    summary_path = tmp_path / 'summary.json'

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2ReportWriteFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            summary_output_path=str(summary_path),
            report_path=str(blocked_report_path),
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            'legacy-round-best-expression',
            1.0,
        ),
    )

    summary_payload = json.loads(summary_path.read_text(encoding='utf-8'))

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['failure_phase'] == 'optimizer_report_output_write_failure'
    assert result['report_path'] is None
    assert result['output_write_failures'][0]['output_path'] == str(blocked_report_path)
    assert summary_payload['failure_phase'] == 'optimizer_report_output_write_failure'


def test_optimizer_returns_error_when_summary_output_write_fails(tmp_path):
    blocked_summary_path = tmp_path / 'blocked_summary.json'
    blocked_summary_path.mkdir()

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2SummaryWriteFailure',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            summary_output_path=str(blocked_summary_path),
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            'legacy-round-best-expression',
            1.0,
        ),
    )

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'runtime_failure'
    assert result['failure_phase'] == 'optimizer_summary_output_write_failure'
    assert result['output_write_failures'][0]['output_path'] == str(blocked_summary_path)


def test_optimizer_writes_report_and_rewrites_summary_json_with_report_path(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'
    report_path = tmp_path / 'reports' / 'wide_v2_summary.md'

    def fake_runner(config, controller):
        return _round_result('R1__cand001', 'legacy-round-best-expression', 1.0)

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2ReportOutput',
            base_buy_strategy='Base',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            runtime_output_path=str(runtime_output),
            report_path=str(report_path),
        ),
        DummyController(),
        research_runner=fake_runner,
    )

    summary_path = tmp_path / 'wide_v2_summary.json'
    summary_payload = json.loads(summary_path.read_text(encoding='utf-8'))

    assert result['report_path'] == str(report_path)
    assert report_path.read_text(encoding='utf-8').startswith('# Wide v2 optimizer summary')
    assert summary_payload['report_path'] == str(report_path)


def test_optimizer_persists_initial_seed_metadata_in_summary_json(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'
    report_path = tmp_path / 'reports' / 'wide_v2_summary.md'

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2InitialSeed',
            base_buy_strategy='BaseStrategy',
            seed_candidate='SeedCandidate',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            iteration_v2_primary_feature='PrimaryFeature',
            iteration_v2_trade_amount_feature='TradeFeature',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            runtime_output_path=str(runtime_output),
            report_path=str(report_path),
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            'legacy-round-best-expression',
            1.0,
        ),
    )

    summary_payload = json.loads((tmp_path / 'wide_v2_summary.json').read_text(encoding='utf-8'))

    assert result['initial_seed'] == {
        'base_buy_strategy': 'BaseStrategy',
        'source_baseline': 'BaseStrategy',
        'seed_candidate': 'SeedCandidate',
        'seed_expression': 'legacy-seed-expression',
        'iteration_v2_mode': 'best_feature_mix',
        'iteration_v2_primary_feature': 'PrimaryFeature',
        'iteration_v2_trade_amount_feature': 'TradeFeature',
    }
    assert summary_payload['report_path'] == str(report_path)
    assert summary_payload['initial_seed'] == result['initial_seed']


def test_optimizer_uses_effective_seed_candidate_in_initial_metadata_when_omitted(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'
    report_path = tmp_path / 'reports' / 'wide_v2_summary.md'

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2EffectiveSeedCandidate',
            base_buy_strategy='BaseStrategy',
            sell_strategy='Sell',
            seed_expression='legacy-seed-expression',
            iteration_v2_mode='best_feature_mix',
            start_date=20250101,
            end_date=20251231,
            max_rounds=1,
            runtime_output_path=str(runtime_output),
            report_path=str(report_path),
        ),
        DummyController(),
        research_runner=lambda config, controller: _round_result(
            'R1__cand001',
            'legacy-round-best-expression',
            1.0,
        ),
    )

    summary_payload = json.loads((tmp_path / 'wide_v2_summary.json').read_text(encoding='utf-8'))
    markdown = report_path.read_text(encoding='utf-8')

    assert result['initial_seed']['seed_candidate'] == 'BaseStrategy'
    assert summary_payload['initial_seed'] == result['initial_seed']
    assert '- seed_candidate=BaseStrategy' in markdown


def test_optimizer_writes_report_for_invalid_seed_with_initial_metadata(tmp_path):
    runtime_output = tmp_path / 'wide_v2.json'
    report_path = tmp_path / 'reports' / 'wide_v2_invalid_summary.md'

    result = run_wide_v2_optimizer(
        WideV2OptimizerConfig(
            name='WideV2InvalidSeedReport',
            base_buy_strategy='Base|Strategy',
            seed_candidate='Seed|Candidate',
            sell_strategy='Sell',
            seed_expression='not parseable',
            iteration_v2_mode='best_feature_mix_v5',
            iteration_v2_primary_feature='Primary|Feature',
            iteration_v2_trade_amount_feature='Trade|Feature',
            start_date=20250101,
            end_date=20251231,
            max_rounds=2,
            runtime_output_path=str(runtime_output),
            report_path=str(report_path),
        ),
        DummyController(),
    )

    summary_payload = json.loads((tmp_path / 'wide_v2_summary.json').read_text(encoding='utf-8'))
    markdown = report_path.read_text(encoding='utf-8')

    assert result['status'] == 'error'
    assert result['stop_reason'] == 'invalid_seed_expression'
    assert result['failed_round'] == 1
    assert result['failure_phase'] == 'invalid_seed_expression'
    assert result['failure_message']
    assert result['completed_round_count'] == 0
    assert result['rounds'] == []
    assert result['initial_seed']['base_buy_strategy'] == 'Base|Strategy'
    assert summary_payload['initial_seed'] == result['initial_seed']
    assert 'Base\\|Strategy' in markdown
    assert 'Seed\\|Candidate' in markdown
    assert '- stop_reason=invalid_seed_expression' in markdown
    assert '- failed_round=1' in markdown
    assert '- failure_phase=invalid_seed_expression' in markdown
