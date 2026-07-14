import json
import math
from pathlib import Path

from cli.research_optimizer_state import (
    WideV2OptimizerConfig,
    build_leaderboard_entries,
    compute_improvement,
    json_safe_value,
    mark_global_best,
    round_runtime_output_path,
    select_global_best_candidate,
)
from cli.research_ranking import select_strict_official_candidates


def _candidate(name, expression, score, *, selected=False, status='ok', index=1):
    return {
        'index': index,
        'strategy_name': name,
        'expression': expression,
        'status': status,
        'selected_as_best': selected,
        'actual_rowset_selected': selected,
        'candidate_csv': f'backtest/csv/{name}.csv',
        'rank_score': {
            'promotion_passed': score > 0,
            'promotion_score': score,
            'adjusted_score': score,
            'score_basis': 'reference',
            'trade_count': 100 + index,
            'trade_count_retention': 0.5,
            'date_concentration': 0.2,
            'symbol_concentration': 0.1,
        },
        'comparison': {
            'candidate_summary': {
                'trade_count': 100 + index,
                'date_concentration': 0.2,
                'symbol_concentration': 0.1,
            },
            'trade_count_retention': 0.5,
        },
    }


def test_optimizer_config_defaults_are_mvp_safe():
    config = WideV2OptimizerConfig(
        name='WideV2Run',
        base_buy_strategy='WideV1Final_B_20260425',
        sell_strategy='ResearchTest_Tick_S_090000_092800_Wide_20260419',
        start_date=20250101,
        end_date=20251231,
    )

    assert config.candidate_count == 10
    assert config.max_rounds == 3
    assert config.min_improvement == 0.01
    assert config.stop_after_no_improvement == 2
    assert config.iteration_v2_mode == 'best_feature_mix_v5'
    assert config.iteration_v2_trade_amount_feature == 'B_당일거래대금'
    assert config.run_id == 'WideV2Run'
    assert config.strict_research_profile is False
    assert config.research_schema_version == 11


def test_round_runtime_output_path_derives_round_specific_json():
    config = WideV2OptimizerConfig(
        name='WideV2Run',
        runtime_output_path='backtest/temp/wide_v2_run.json',
    )

    assert round_runtime_output_path(config, 2) == str(Path('backtest/temp/wide_v2_run_round002.json'))


def test_json_safe_value_normalizes_non_finite_numbers():
    payload = {
        'good': 1.5,
        'nan': math.nan,
        'inf': math.inf,
        'items': [1, math.nan],
    }

    safe = json_safe_value(payload)

    assert safe == {'good': 1.5, 'nan': None, 'inf': None, 'items': [1, None]}
    json.dumps(safe)


def test_build_leaderboard_entries_uses_candidate_rank_score():
    round_result = {
        'status': 'ok',
        'best_candidate': _candidate('Round1__cand002', '등락율 > 4.8', 2.0, selected=True, index=2),
        'candidates': [
            _candidate('Round1__cand001', '등락율 > 4.0', 1.0, index=1),
            _candidate('Round1__cand002', '등락율 > 4.8', 2.0, selected=True, index=2),
        ],
    }

    entries = build_leaderboard_entries(
        run_id='WideV2Run',
        round_index=1,
        round_result=round_result,
        source_baseline='WideV1Final_B_20260425',
        source_candidate='WideV1Final_B_20260425',
    )

    assert len(entries) == 2
    assert entries[1]['run_id'] == 'WideV2Run'
    assert entries[1]['round_index'] == 1
    assert entries[1]['candidate_index'] == 2
    assert entries[1]['strategy_name'] == 'Round1__cand002'
    assert entries[1]['expression'] == '등락율 > 4.8'
    assert entries[1]['promotion_passed'] is True
    assert entries[1]['adjusted_score'] == 2.0
    assert entries[1]['selected_as_round_best'] is True
    assert entries[1]['selected_as_global_best'] is False
    assert entries[1]['runtime_json_path'] is None
    assert entries[1]['candidate_csv_path'] == 'backtest/csv/Round1__cand002.csv'


def test_build_leaderboard_entries_keeps_missing_metrics_as_none_for_failed_candidate():
    round_result = {
        'candidates': [
            {
                'index': 7,
                'strategy_name': 'Round1__cand007',
                'expression': 'A',
                'status': 'comparison',
                'phase': 'comparison',
                'message': 'missing candidate csv',
                'selected_as_best': False,
                'actual_rowset_selected': False,
            }
        ],
    }

    entries = build_leaderboard_entries(
        run_id='WideV2Run',
        round_index=1,
        round_result=round_result,
        source_baseline='Base',
        source_candidate='Seed',
    )

    assert len(entries) == 1
    assert entries[0]['promotion_score'] is None
    assert entries[0]['adjusted_score'] is None
    assert entries[0]['trade_count'] is None
    assert entries[0]['trade_count_retention'] is None
    assert entries[0]['date_concentration'] is None
    assert entries[0]['symbol_concentration'] is None
    assert entries[0]['rank_score'] is None
    assert entries[0]['failure_phase'] == 'comparison'
    assert entries[0]['failure_message'] == 'missing candidate csv'


def test_build_leaderboard_entries_preserves_explicit_zero_metrics():
    round_result = {
        'candidates': [
            {
                'index': 3,
                'strategy_name': 'Round1__cand003',
                'expression': 'B',
                'status': 'ok',
                'selected_as_best': False,
                'actual_rowset_selected': False,
                'rank_score': {
                    'promotion_passed': False,
                    'promotion_score': 0,
                    'adjusted_score': 0,
                    'trade_count': 0,
                    'trade_count_retention': 0,
                    'date_concentration': 0,
                    'symbol_concentration': 0,
                },
            }
        ],
    }

    entries = build_leaderboard_entries(
        run_id='WideV2Run',
        round_index=1,
        round_result=round_result,
        source_baseline='Base',
        source_candidate='Seed',
    )

    assert len(entries) == 1
    assert entries[0]['promotion_passed'] is False
    assert entries[0]['promotion_score'] == 0
    assert entries[0]['adjusted_score'] == 0
    assert entries[0]['trade_count'] == 0
    assert entries[0]['trade_count_retention'] == 0
    assert entries[0]['date_concentration'] == 0
    assert entries[0]['symbol_concentration'] == 0
    assert isinstance(entries[0]['rank_score'], dict)


def test_select_and_mark_global_best_candidate():
    entries = [
        build_leaderboard_entries(
            run_id='WideV2Run',
            round_index=1,
            round_result={'candidates': [_candidate('R1__cand001', 'A', 1.0, selected=True)]},
            source_baseline='Base',
            source_candidate='Seed',
        )[0],
        build_leaderboard_entries(
            run_id='WideV2Run',
            round_index=2,
            round_result={'candidates': [_candidate('R2__cand001', 'B', 3.0, selected=True)]},
            source_baseline='Base',
            source_candidate='R1__cand001',
        )[0],
    ]

    best = select_global_best_candidate(entries)
    marked = mark_global_best(entries, best)

    assert best['strategy_name'] == 'R2__cand001'
    assert marked[0]['selected_as_global_best'] is False
    assert marked[1]['selected_as_global_best'] is True


def test_compute_improvement_uses_adjusted_score_delta():
    previous = {'adjusted_score': 1.25}
    current = {'adjusted_score': 1.50}

    assert compute_improvement(current, previous) == 0.25
    assert compute_improvement(current, None) is None


def test_compute_improvement_returns_none_for_missing_or_non_finite_scores():
    assert compute_improvement({'adjusted_score': math.inf}, {'adjusted_score': 1.0}) is None
    assert compute_improvement({'adjusted_score': 2.0}, {'adjusted_score': math.nan}) is None
    assert compute_improvement({'promotion_score': None}, {'adjusted_score': 1.0}) is None


def test_strict_official_selector_keeps_failed_and_fallback_candidates_advisory():
    failed = _candidate('Failed', '현재가 > 1', 100, index=1)
    failed['promotion'] = {'passed': False, 'score': 100}
    fallback = _candidate('Fallback', '현재가 > 2', 99, index=2)
    fallback['promotion'] = {'passed': True, 'score': 99}
    fallback['fallback_used'] = True

    result = select_strict_official_candidates([failed, fallback])

    assert result['official_best_candidate'] is None
    assert result['official_parent_candidate'] is None
    assert result['best_advisory_candidate']['strategy_name'] == 'Failed'
    assert result['official_authority'] == 0
    assert result['stop_reason'] == 'NO_ELIGIBLE_PARENT'
    assert {item['strategy_name'] for item in result['diagnostic_candidates']} == {'Failed', 'Fallback'}
    assert {item['official_authority'] for item in result['diagnostic_candidates']} == {0}


def test_strict_official_selector_returns_only_promotion_passed_candidate():
    failed = _candidate('Failed', '현재가 > 1', 100, index=1)
    failed['promotion'] = {'passed': False, 'score': 100}
    eligible = _candidate('Eligible', '현재가 > 2', 1, index=2)
    eligible['promotion'] = {'passed': True, 'score': 1}

    result = select_strict_official_candidates([failed, eligible])

    assert [item['strategy_name'] for item in result['official_eligible_candidates']] == ['Eligible']
    assert result['official_best_candidate']['strategy_name'] == 'Eligible'
    assert result['official_parent_candidate']['strategy_name'] == 'Eligible'
    assert result['stop_reason'] is None


def test_strict_official_selector_cannot_replace_canonical_final_owner():
    canonical = _candidate('Canonical', '현재가 > 1', 1, index=1)
    canonical.update({'promotion': {'passed': True, 'score': 1}, 'hypothesis_id': 'hyp-canonical'})
    higher_scored_peer = _candidate('Peer', '현재가 > 2', 100, index=2)
    higher_scored_peer.update({'promotion': {'passed': True, 'score': 100}, 'hypothesis_id': 'hyp-peer'})

    result = select_strict_official_candidates(
        [canonical, higher_scored_peer],
        authoritative_candidate_id='hyp-canonical',
    )

    assert result['official_best_candidate']['strategy_name'] == 'Canonical'
    assert result['authoritative_candidate_id'] == 'hyp-canonical'
    peer_diagnostic = next(
        item for item in result['diagnostic_candidates'] if item['strategy_name'] == 'Peer'
    )
    assert peer_diagnostic['reason'] == 'canonical_final_owner_mismatch'


def test_strict_official_selector_rejects_nested_fallback_and_failed_result():
    nested_fallback = _candidate('NestedFallback', '현재가 > 1', 10, index=1)
    nested_fallback.update({
        'promotion': {'passed': True, 'score': 10},
        'candidate_result': {'status': 'ok', 'fallback_used': True},
    })
    nested_failure = _candidate('NestedFailure', '현재가 > 2', 9, index=2)
    nested_failure.update({
        'promotion': {'passed': True, 'score': 9},
        'source_candidate': {'candidate_result': {'status': 'error'}},
    })

    result = select_strict_official_candidates([nested_fallback, nested_failure])

    assert result['official_best_candidate'] is None
    reasons = {
        item['strategy_name']: item['reason']
        for item in result['diagnostic_candidates']
    }
    assert reasons == {
        'NestedFallback': 'diagnostic_fallback',
        'NestedFailure': 'candidate_result_status_not_ok',
    }


def test_strict_official_selector_rejects_malformed_provenance_types():
    malformed = _candidate('Malformed', '현재가 > 1', 10, index=1)
    malformed.update({
        'promotion': {'passed': True, 'score': 10},
        'candidate_result': 'not-a-mapping',
        'fallback_used': 'false',
        'strict_response_validation': 'valid',
    })

    result = select_strict_official_candidates([malformed])

    assert result['official_best_candidate'] is None
    assert result['diagnostic_candidates'][0]['reason'] == 'candidate_result_invalid'
