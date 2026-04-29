"""Tests for discovery research command wiring helpers."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch

from cli.commands.research import (
    build_research_strategy_payload,
    build_wide_v2_optimizer_config,
    handle_optimize_wide_v2,
    handle_research,
)


def _research_args(**overrides):
    values = {
        'name': 'ResearchRun',
        'input_file': 'baseline.csv',
        'score_reference_csv': 'root.csv',
        'base_buy_strategy': 'BaseBuy',
        'sell': 'BaseSell',
        'start': 20250101,
        'end': 20250131,
        'timeframe': 'min',
        'betting': '2',
        'avg_time': 30,
        'start_time': 90100,
        'end_time': 145500,
        'engines': 2,
        'top_n': 3,
        'min_samples': 20,
        'quantiles': 8,
        'alpha': 0.1,
        'run_candidate': False,
        'run_candidates': True,
        'candidate_count': 7,
        'candidate_name_prefix': 'Batch',
        'cleanup_best_candidate': True,
        'keep_loser_candidates': True,
        'min_estimated_retention': 0.55,
        'allow_retention_fallback': False,
        'use_retention_penalty': False,
        'candidate_pool_multiplier': 4,
        'candidate_start': 20250102,
        'candidate_end': 20250130,
        'candidate_timeout': 300,
        'candidate_plan_only': True,
        'keep_failed_candidate': True,
        'runtime_output_path': 'backtest/temp/research.json',
        'max_consecutive_candidate_failures': 5,
        'iteration_v2_mode': 'best_feature_mix_v5',
        'iteration_v2_best_candidate': 'SeedCandidate',
        'iteration_v2_best_expression': 'B_등락율 > 1',
        'iteration_v2_primary_feature': 'B_시가총액',
        'iteration_v2_trade_amount_feature': 'B_등락율',
        'iteration_v2_secondary_features': 'B_거래대금',
        'iteration_v2_include_secondary_only': False,
        'iteration_v2_max_secondary_only': 0,
        'iteration_v2_duplicate_retention_tolerance': 0.03,
    }
    values.update(overrides)
    return Namespace(**values)


def _optimizer_args(**overrides):
    values = {
        'name': 'WideV2AutoLoop',
        'input_file': 'baseline.csv',
        'score_reference_csv': 'root.csv',
        'base_buy_strategy': 'WideV1Final',
        'sell': 'BaseSell',
        'seed_candidate': 'SeedCandidate',
        'seed_expression': 'B_등락율 > 1',
        'start': 20250101,
        'end': 20251231,
        'timeframe': 'tick',
        'betting': '1',
        'avg_time': 60,
        'start_time': 90000,
        'end_time': 152800,
        'engines': 4,
        'top_n': 1,
        'min_samples': 30,
        'quantiles': 10,
        'alpha': 0.05,
        'candidate_count': 10,
        'candidate_timeout': 1200,
        'cleanup_best_candidate': False,
        'keep_loser_candidates': False,
        'keep_failed_candidate': True,
        'min_estimated_retention': 0.4,
        'allow_retention_fallback': True,
        'use_retention_penalty': True,
        'candidate_pool_multiplier': 3,
        'iteration_v2_mode': 'best_feature_mix_v5',
        'iteration_v2_primary_feature': 'B_시가총액',
        'iteration_v2_trade_amount_feature': 'B_당일거래대금',
        'iteration_v2_secondary_features': '',
        'iteration_v2_include_secondary_only': True,
        'iteration_v2_max_secondary_only': 1,
        'iteration_v2_duplicate_retention_tolerance': 0.02,
        'max_rounds': 3,
        'min_improvement': 0.01,
        'stop_after_no_improvement': 2,
        'max_consecutive_candidate_failures': 3,
        'runtime_output_path': 'backtest/temp/runtime.json',
        'leaderboard_output_path': 'backtest/temp/leaderboard.json',
        'summary_output_path': 'backtest/temp/summary.json',
        'report_path': 'docs/research/condition_research/pilot_logs/report.md',
    }
    values.update(overrides)
    return Namespace(**values)


class _FakeController:
    def __init__(self, result):
        self.result = result
        self.payloads = []

    def research_strategy_once(self, payload):
        self.payloads.append(payload)
        return self.result


def test_build_research_strategy_payload_preserves_cli_contract():
    payload = build_research_strategy_payload(_research_args())

    assert payload == {
        'name': 'ResearchRun',
        'baseline_csv': 'baseline.csv',
        'score_reference_csv': 'root.csv',
        'base_buy_strategy': 'BaseBuy',
        'sell_strategy': 'BaseSell',
        'start_date': 20250101,
        'end_date': 20250131,
        'is_tick': False,
        'betting': '2',
        'avg_time': 30,
        'start_time': 90100,
        'end_time': 145500,
        'engine_count': 2,
        'top_n': 3,
        'min_samples': 20,
        'quantiles': 8,
        'alpha': 0.1,
        'run_candidate': False,
        'run_candidates': True,
        'candidate_count': 7,
        'candidate_name_prefix': 'Batch',
        'cleanup_best_candidate': True,
        'keep_loser_candidates': True,
        'min_estimated_retention': 0.55,
        'allow_retention_fallback': False,
        'use_retention_penalty': False,
        'candidate_pool_multiplier': 4,
        'candidate_start_date': 20250102,
        'candidate_end_date': 20250130,
        'candidate_timeout': 300,
        'candidate_plan_only': True,
        'keep_failed_candidate': True,
        'runtime_output_path': 'backtest/temp/research.json',
        'max_consecutive_candidate_failures': 5,
        'iteration_v2_mode': 'best_feature_mix_v5',
        'iteration_v2_best_candidate': 'SeedCandidate',
        'iteration_v2_best_expression': 'B_등락율 > 1',
        'iteration_v2_primary_feature': 'B_시가총액',
        'iteration_v2_trade_amount_feature': 'B_등락율',
        'iteration_v2_secondary_features': 'B_거래대금',
        'iteration_v2_include_secondary_only': False,
        'iteration_v2_max_secondary_only': 0,
        'iteration_v2_duplicate_retention_tolerance': 0.03,
    }


def test_build_research_strategy_payload_handles_missing_input():
    payload = build_research_strategy_payload(_research_args(input_file=None, timeframe='tick'))

    assert payload['baseline_csv'] is None
    assert payload['is_tick'] is True


def test_build_wide_v2_optimizer_config_preserves_cli_contract():
    config = build_wide_v2_optimizer_config(_optimizer_args())

    assert config.name == 'WideV2AutoLoop'
    assert config.baseline_csv == 'baseline.csv'
    assert config.score_reference_csv == 'root.csv'
    assert config.base_buy_strategy == 'WideV1Final'
    assert config.sell_strategy == 'BaseSell'
    assert config.seed_candidate == 'SeedCandidate'
    assert config.seed_expression == 'B_등락율 > 1'
    assert config.start_date == 20250101
    assert config.end_date == 20251231
    assert config.is_tick is True
    assert config.candidate_count == 10
    assert config.candidate_timeout == 1200
    assert config.keep_failed_candidate is True
    assert config.iteration_v2_mode == 'best_feature_mix_v5'
    assert config.max_rounds == 3
    assert config.runtime_output_path == 'backtest/temp/runtime.json'
    assert config.leaderboard_output_path == 'backtest/temp/leaderboard.json'
    assert config.summary_output_path == 'backtest/temp/summary.json'
    assert config.report_path == 'docs/research/condition_research/pilot_logs/report.md'


def test_handle_research_prints_json_and_returns_exit_code(capsys):
    controller = _FakeController({'status': 'ok', 'run_id': 'ResearchRun'})

    exit_code = handle_research(_research_args(), controller)

    assert exit_code == 0
    assert controller.payloads[0]['name'] == 'ResearchRun'
    assert 'ResearchRun' in capsys.readouterr().out


def test_handle_research_returns_nonzero_for_error(capsys):
    controller = _FakeController({'status': 'error', 'phase': 'failed'})

    exit_code = handle_research(_research_args(), controller)

    assert exit_code == 1
    assert 'failed' in capsys.readouterr().out


def test_handle_optimize_wide_v2_prints_json_and_returns_exit_code(capsys):
    with patch('cli.research_optimizer.run_wide_v2_optimizer') as mock:
        mock.return_value = {'status': 'ok', 'run_id': 'WideV2AutoLoop'}

        exit_code = handle_optimize_wide_v2(_optimizer_args(), _FakeController({'status': 'unused'}))

    assert exit_code == 0
    config = mock.call_args.args[0]
    assert config.name == 'WideV2AutoLoop'
    assert 'WideV2AutoLoop' in capsys.readouterr().out
