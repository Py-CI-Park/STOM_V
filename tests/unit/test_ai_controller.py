"""US-506: AI 백테스트 컨트롤러 테스트."""

import os
import sys
import json
import sqlite3
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from dataclasses import asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from cli.ai_controller import AIBacktestController
from cli.config import BacktestConfig


@pytest.fixture
def tmp_history_db(tmp_path):
    return str(tmp_path / 'test_history.db')


@pytest.fixture
def controller(tmp_history_db):
    return AIBacktestController(history_db_path=tmp_history_db)


def test_research_strategy_once_routes_iteration(monkeypatch):
    from cli.research_loop import ResearchLoopConfig

    calls = {}

    def fake_iteration(config, controller):
        calls['config'] = config
        calls['controller'] = controller
        return {'status': 'ok', 'phase': 'candidates_evaluated'}

    monkeypatch.setattr('cli.research_loop.run_research_iteration', fake_iteration)
    monkeypatch.setattr(
        'cli.research_loop.run_research_once',
        lambda config, controller: {'status': 'error', 'phase': 'wrong_route'},
    )

    controller = AIBacktestController()
    result = controller.research_strategy_once({
        'name': 'IterationRoute',
        'run_candidates': True,
        'candidate_count': 3,
    })

    assert result['phase'] == 'candidates_evaluated'
    assert isinstance(calls['config'], ResearchLoopConfig)
    assert calls['config'].run_candidates is True
    assert calls['config'].run_candidate is False
    assert calls['config'].candidate_count == 3
    assert calls['controller'] is controller


# === list_strategies ===

class TestListStrategies:
    def test_returns_ok(self, controller):
        with patch('cli.ai_controller.list_strategies') as mock:
            mock.return_value = {'stockbuy': ['A'], 'stocksell': ['B']}
            result = controller.list_strategies()
            assert result['status'] == 'ok'
            assert 'A' in result['strategies']['stockbuy']

    def test_handles_exception(self, controller):
        with patch('cli.ai_controller.list_strategies', side_effect=Exception('DB error')):
            result = controller.list_strategies()
            assert result['status'] == 'error'
            assert 'DB error' in result['message']


# === analyze_strategy ===

class TestAnalyzeStrategy:
    def test_analyze_ok(self, controller):
        mock_loader = {
            'status': 'ok',
            'code': 'if self.vars[0] > 0:\n    pass',
            'name': 'Min_B_Test',
            'type': 'buy',
            'var_refs': [0],
            'functions': [],
            'warnings': [],
        }
        with patch('cli.strategy_loader.load_strategy_from_db', return_value=mock_loader), \
             patch('cli.timeframe_detector.detect_timeframe', return_value='min'), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.analyze_strategy('Min_B_Test', 'buy')
            assert result['status'] == 'ok'
            assert result['timeframe'] == 'min'
            assert result['var_refs'] == [0]

    def test_analyze_not_found(self, controller):
        mock_loader = {'status': 'error', 'message': '전략 없음'}
        with patch('cli.strategy_loader.load_strategy_from_db', return_value=mock_loader), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.analyze_strategy('NonExistent', 'buy')
            assert result['status'] == 'error'


# === run ===

class TestRun:
    def test_run_success(self, controller):
        mock_result = {
            'status': 'success',
            'message': '완료',
            'metrics': {'tpi': 1.5, 'win_rate': 55.0},
        }
        with patch('cli.runner.run_backtest', return_value=mock_result), \
             patch('cli.timeframe_detector.validate_timeframe_match', return_value={'status': 'ok'}), \
             patch('cli.ai_controller.validate', return_value=[]):
            result = controller.run({
                'buy_strategy': 'Min_B_Test',
                'sell_strategy': 'Min_S_Test',
                'start_date': 20250407,
                'end_date': 20250409,
                'is_tick': False,
            })
            assert result['status'] == 'success'
            assert 'duration' in result

    def test_run_timeframe_mismatch(self, controller):
        tf_error = {'status': 'error', 'message': '분봉 전략을 틱 모드로 실행 불가'}
        with patch('cli.timeframe_detector.validate_timeframe_match', return_value=tf_error):
            result = controller.run({
                'buy_strategy': 'Min_B_Test',
                'sell_strategy': 'Min_S_Test',
                'start_date': 20250407,
                'end_date': 20250409,
                'is_tick': True,
            })
            assert result['status'] == 'error'
            assert '틱' in result['message']

    def test_run_validation_error(self, controller):
        with patch('cli.timeframe_detector.validate_timeframe_match', return_value={'status': 'ok'}), \
             patch('cli.ai_controller.validate', return_value=['매수 전략 없음']):
            result = controller.run({})
            assert result['status'] == 'error'


# === dry_run ===

class TestDryRun:
    def test_dry_run_ok(self, controller):
        with patch('cli.timeframe_detector.validate_timeframe_match', return_value={'status': 'ok'}), \
             patch('cli.ai_controller.validate', return_value=[]):
            result = controller.dry_run({
                'buy_strategy': 'Min_B_Test',
                'sell_strategy': 'Min_S_Test',
                'start_date': 20250407,
                'end_date': 20250409,
                'is_tick': False,
            })
            assert result['status'] == 'ok'
            assert 'config' in result


# === optimize ===

class TestOptimize:
    def test_optimize_grid(self, controller):
        def mock_run(config):
            avg = config.avg_time if isinstance(config.avg_time, int) else 60
            return {'status': 'success', 'metrics': {'tpi': avg * 0.01}}

        # optimizer uses run_fn parameter to avoid real runner import
        from cli.optimizer import optimize as run_optimize
        opt_result = run_optimize(
            BacktestConfig(buy_strategy='T', sell_strategy='T',
                           start_date=20250407, end_date=20250409),
            {'avg_time': [60, 120]},
            objective='tpi', method='grid',
            run_fn=mock_run,
        )
        assert opt_result['status'] == 'ok'
        assert opt_result['total'] == 2


class TestWalkForward:
    def test_walk_forward_ok(self, controller, tmp_path):
        mock_result = {
            'status': 'ok',
            'summary': {'round_count': 2, 'success_count': 2},
            'rounds': [],
        }
        with patch('cli.wfo.run_walk_forward', return_value=mock_result):
            output_path = tmp_path / 'wfo_report.json'
            result = controller.walk_forward(
                {
                    'buy_strategy': 'Min_B_Test',
                    'sell_strategy': 'Min_S_Test',
                    'start_date': 20240101,
                    'end_date': 20240630,
                },
                {'avg_time': [60, 120]},
                train_window_days=60,
                test_window_days=20,
                output_path=str(output_path),
            )
            assert result['status'] == 'ok'
            assert result['summary']['round_count'] == 2
            assert result['saved']['status'] == 'ok'

    def test_evaluate_walk_forward_result_pass(self, controller):
        result = controller.evaluate_walk_forward_result({
            'status': 'ok',
            'summary': {'round_count': 3, 'success_rate': 1.0, 'mean_oos_metric': 0.5},
            'rounds': [
                {'test_result': {'metrics': {'trade_count': 120}}},
                {'test_result': {'metrics': {'trade_count': 150}}},
                {'test_result': {'metrics': {'trade_count': 100}}},
            ],
        }, min_rounds=2, min_success_rate=0.7, min_mean_oos_metric=0.1, min_avg_trade_count=50)
        assert result['status'] == 'ok'
        assert result['passed'] is True

    def test_evaluate_walk_forward_result_rejects_thresholds(self, controller):
        result = controller.evaluate_walk_forward_result({
            'status': 'ok',
            'summary': {'round_count': 1, 'success_rate': 0.5, 'mean_oos_metric': -0.1},
            'rounds': [{'test_result': {'metrics': {'trade_count': 10}}}],
        }, min_rounds=2, min_success_rate=0.7, min_mean_oos_metric=0.0, min_avg_trade_count=30)
        assert result['status'] == 'ok'
        assert result['passed'] is False
        assert len(result['reasons']) >= 3

    def test_evaluate_walk_forward_result_marks_all_zero_trade_rounds(self, controller):
        result = controller.evaluate_walk_forward_result({
            'status': 'ok',
            'summary': {
                'round_count': 2,
                'success_rate': 1.0,
                'mean_oos_metric': 0.2,
                'zero_trade_rounds': 2,
            },
            'rounds': [
                {'test_result': {'metrics': {'trade_count': 0}}},
                {'test_result': {'metrics': {'trade_count': 0}}},
            ],
        }, min_rounds=1, min_success_rate=0.5, min_mean_oos_metric=0.0, min_avg_trade_count=0)
        assert result['status'] == 'ok'
        assert result['passed'] is False
        assert 'all_rounds_no_trades' in result['reasons']
        assert result['summary']['zero_trade_rounds'] == 2

    def test_evaluate_walk_forward_result_marks_missing_metrics_as_no_trade(self, controller):
        result = controller.evaluate_walk_forward_result({
            'status': 'ok',
            'summary': {
                'round_count': 1,
                'success_rate': 1.0,
                'mean_oos_metric': None,
                'trade_count_rounds': 0,
                'zero_trade_rounds': 0,
            },
            'rounds': [
                {'test_result': {'status': 'success', 'message': '백테스트 완료 (결과 테이블이 비어있습니다)'}},
            ],
        }, min_rounds=1, min_success_rate=0.5, min_mean_oos_metric=-0.1, min_avg_trade_count=0)
        assert result['status'] == 'ok'
        assert result['passed'] is False
        assert 'all_rounds_no_trades' in result['reasons']
        assert result['summary']['zero_trade_rounds'] == 1


# === get_history / get_best ===

class TestHistory:
    def test_get_history_empty(self, controller):
        from cli.history import init_history_db
        init_history_db(controller._history_db)
        result = controller.get_history()
        assert result['status'] == 'ok'
        assert result['total'] == 0

    def test_get_history_with_data(self, controller):
        from cli.history import init_history_db, save_run
        init_history_db(controller._history_db)
        config = BacktestConfig(buy_strategy='A', sell_strategy='B',
                                start_date=20250407, end_date=20250409)
        mock_result = {'status': 'success', 'metrics': {'tpi': 1.0, 'win_rate': 50.0,
                       'total_profit_pct': 10.0, 'cagr': 20.0, 'mdd_pct': -5.0,
                       'trade_count': 100}}
        save_run(config, mock_result, 10.0, controller._history_db)

        result = controller.get_history(limit=5)
        assert result['status'] == 'ok'
        assert result['total'] == 1

    def test_get_best(self, controller):
        from cli.history import init_history_db, save_run
        init_history_db(controller._history_db)
        config1 = BacktestConfig(buy_strategy='A', sell_strategy='B',
                                 start_date=20250407, end_date=20250409)
        config2 = BacktestConfig(buy_strategy='C', sell_strategy='D',
                                 start_date=20250407, end_date=20250409)
        save_run(config1, {'status': 'success', 'metrics': {'tpi': 1.0, 'win_rate': 50.0,
                 'total_profit_pct': 10.0, 'cagr': 20.0, 'mdd_pct': -5.0,
                 'trade_count': 50}}, 10.0, controller._history_db)
        save_run(config2, {'status': 'success', 'metrics': {'tpi': 2.0, 'win_rate': 60.0,
                 'total_profit_pct': 20.0, 'cagr': 30.0, 'mdd_pct': -3.0,
                 'trade_count': 80}}, 15.0, controller._history_db)

        result = controller.get_best('tpi')
        assert result['status'] == 'ok'
        assert result['total'] >= 1


# === system_info ===

class TestSystemInfo:
    def test_system_info(self, controller):
        result = controller.system_info()
        assert result['status'] == 'ok'
        assert 'system' in result
        assert 'recommended_engines' in result


# === compare ===

class TestCompare:
    def test_compare_runs(self, controller):
        from cli.history import init_history_db, save_run
        init_history_db(controller._history_db)
        config = BacktestConfig(buy_strategy='A', sell_strategy='B',
                                start_date=20250407, end_date=20250409)
        metrics = {'tpi': 1.0, 'win_rate': 50.0, 'total_profit_pct': 10.0,
                   'cagr': 20.0, 'mdd_pct': -5.0, 'trade_count': 50}
        id1 = save_run(config, {'status': 'success', 'metrics': metrics}, 10.0,
                       controller._history_db)
        id2 = save_run(config, {'status': 'success', 'metrics': {**metrics, 'tpi': 2.0}},
                       12.0, controller._history_db)

        result = controller.compare([id1, id2])
        assert 'runs' in result or result.get('status') == 'ok'


# === create_strategy / delete_strategy ===

class TestStrategyManagement:
    def test_create_strategy(self, controller):
        mock_result = {'status': 'ok', 'name': 'Test', 'action': 'created'}
        with patch('cli.strategy_generator.create_and_save', return_value=mock_result), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.create_strategy('Test', ['self.vars[0] > 0'], 'buy')
            assert result['status'] == 'ok'

    def test_delete_strategy(self, controller):
        mock_result = {'status': 'ok', 'name': 'Test', 'action': 'deleted'}
        with patch('cli.strategy_generator.delete_strategy_from_db', return_value=mock_result), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.delete_strategy('Test', 'buy')
            assert result['status'] == 'ok'

    def test_create_strategy_from_analysis_ok(self, controller, tmp_path):
        csv_path = tmp_path / 'result.csv'
        pd.DataFrame([
            {'수익률': -1.0, 'B_등락율': 0.5, 'B_시가총액': 100_000_000_000, 'B_시분초': 91000, 'B_체결강도': 90},
            {'수익률': -0.8, 'B_등락율': 0.8, 'B_시가총액': 100_000_000_000, 'B_시분초': 91500, 'B_체결강도': 91},
            {'수익률': 0.5, 'B_등락율': 2.5, 'B_시가총액': 800_000_000_000, 'B_시분초': 100000, 'B_체결강도': 110},
            {'수익률': 1.1, 'B_등락율': 3.5, 'B_시가총액': 2_000_000_000_000, 'B_시분초': 140000, 'B_체결강도': 130},
        ] * 10).to_csv(csv_path, index=False, encoding='utf-8-sig')

        with patch('cli.strategy_generator.create_and_save', return_value={'status': 'ok', 'name': 'Auto_B_Test', 'action': 'created'}), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.create_strategy_from_analysis(
                'Auto_B_Test',
                input_path=str(csv_path),
                top_n=2,
                min_samples=5,
                quantiles=4,
                output_code_path=str(tmp_path / 'generated.py'),
            )
            assert result['status'] == 'ok'
            assert result['strategy_result']['action'] == 'created'
            assert len(result['expression_result']['expressions']) == 2
            assert '매수 = False' in result['generated_code']
            assert result['saved_code']['status'] == 'ok'
            assert 'feature_whitelist' in result

    def test_create_strategy_from_analysis_rejects_non_buy(self, controller):
        result = controller.create_strategy_from_analysis('BadSell', analysis_result={'status': 'ok'}, strategy_type='sell')
        assert result['status'] == 'error'

    def test_create_strategy_from_analysis_with_ml_feature_filter(self, controller, tmp_path):
        csv_path = tmp_path / 'result.csv'
        pd.DataFrame([
            {'수익률': -1.0, 'B_등락율': 0.5, 'B_시가총액': 100_000_000_000, 'B_시분초': 91000, 'B_체결강도': 90},
            {'수익률': -0.8, 'B_등락율': 0.8, 'B_시가총액': 100_000_000_000, 'B_시분초': 91500, 'B_체결강도': 91},
            {'수익률': 0.5, 'B_등락율': 2.5, 'B_시가총액': 800_000_000_000, 'B_시분초': 100000, 'B_체결강도': 110},
            {'수익률': 1.1, 'B_등락율': 3.5, 'B_시가총액': 2_000_000_000_000, 'B_시분초': 140000, 'B_체결강도': 130},
        ] * 10).to_csv(csv_path, index=False, encoding='utf-8-sig')

        with patch('cli.strategy_generator.create_and_save', return_value={'status': 'ok', 'name': 'Auto_B_Test', 'action': 'created'}), \
             patch('cli.paths.DB_STRATEGY', 'fake.db'):
            result = controller.create_strategy_from_analysis(
                'Auto_B_Test',
                input_path=str(csv_path),
                top_n=5,
                min_samples=5,
                quantiles=4,
                ml_feature_limit=1,
                ml_top_n=3,
                ml_n_splits=2,
            )
            assert result['status'] == 'ok'
            assert result['feature_whitelist'] is not None
            assert len(result['feature_whitelist']) == 1

    def test_discover_strategy_runs_strategy_flow_and_optional_wfo(self, controller):
        strategy_flow = {
            'status': 'ok',
            'strategy_result': {'status': 'ok', 'action': 'created'},
            'expression_result': {'candidate_count': 2},
        }
        walk_forward_result = {
            'status': 'ok',
            'summary': {'round_count': 3},
        }

        with patch.object(controller, 'create_strategy_from_analysis', return_value=strategy_flow) as mock_create, \
             patch.object(controller, 'walk_forward', return_value=walk_forward_result) as mock_wfo:
            result = controller.discover_strategy(
                'Auto_B_Discover',
                config_dict={
                    'buy_strategy': 'BaseBuy',
                    'sell_strategy': 'BaseSell',
                    'start_date': 20240101,
                    'end_date': 20240630,
                },
                input_path='dummy.csv',
                param_space={'avg_time': [60, 120]},
                walk_forward_settings={
                    'train_window_days': 60,
                    'test_window_days': 20,
                },
            )

            assert result['status'] == 'ok'
            assert result['strategy_flow']['strategy_result']['action'] == 'created'
            assert result['walk_forward']['summary']['round_count'] == 3
            mock_create.assert_called_once()
            mock_wfo.assert_called_once()

    def test_discover_and_promote_strategy_promotes_on_pass(self, controller):
        prepared = {
            'status': 'ok',
            'analysis_result': {'status': 'ok'},
            'expression_result': {'expressions': ['B_등락율 <= 2'], 'candidate_count': 1},
            'code_result': {'status': 'ok', 'code': 'if B_등락율 <= 2: 매수 = False'},
        }
        with patch.object(controller, '_prepare_strategy_candidate', return_value=prepared), \
             patch.object(controller, 'create_strategy', side_effect=[
                 {'status': 'ok', 'name': '__tmp__', 'action': 'created'},
                 {'status': 'ok', 'name': 'Auto_B_Final', 'action': 'created'},
             ]) as mock_create, \
             patch.object(controller, 'walk_forward', return_value={
                 'status': 'ok',
                 'summary': {'round_count': 3, 'success_rate': 1.0, 'mean_oos_metric': 0.5},
                 'rounds': [
                     {'test_result': {'metrics': {'trade_count': 120}}},
                     {'test_result': {'metrics': {'trade_count': 140}}},
                     {'test_result': {'metrics': {'trade_count': 110}}},
                 ],
             }) as mock_wfo, \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}) as mock_delete:
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
                promotion_preset='balanced',
            )
            assert result['status'] == 'ok'
            assert result['promoted'] is True
            assert result['criteria_mode'] == 'strict'
            assert result['strategy_result']['action'] == 'created'
            assert result['promotion_evaluation']['preset'] == 'balanced'
            assert result['promotion_evaluation']['criteria_mode'] == 'strict'
            assert result['report']['promotion_preset'] == 'balanced'
            assert result['report']['criteria_mode'] == 'strict'
            assert mock_create.call_count == 2
            mock_wfo.assert_called_once()
            mock_delete.assert_called_once()

    def test_discover_and_promote_strategy_rejects_on_failed_wfo(self, controller):
        prepared = {
            'status': 'ok',
            'analysis_result': {'status': 'ok'},
            'expression_result': {'expressions': ['B_등락율 <= 2'], 'candidate_count': 1},
            'code_result': {'status': 'ok', 'code': 'if B_등락율 <= 2: 매수 = False'},
        }
        with patch.object(controller, '_prepare_strategy_candidate', return_value=prepared), \
             patch.object(controller, 'create_strategy', return_value={'status': 'ok', 'name': '__tmp__', 'action': 'created'}) as mock_create, \
             patch.object(controller, 'walk_forward', return_value={'status': 'ok', 'summary': {'round_count': 1, 'success_rate': 0.0, 'mean_oos_metric': -1.0}, 'rounds': []}), \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}) as mock_delete:
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
            )
            assert result['status'] == 'ok'
            assert result['promoted'] is False
            assert result['strategy_result']['action'] == 'rejected'
            assert mock_create.call_count == 1
            mock_delete.assert_called_once()

    def test_discover_and_promote_strategy_saves_reports(self, controller, tmp_path):
        prepared = {
            'status': 'ok',
            'analysis_result': {'status': 'ok'},
            'expression_result': {'expressions': ['B_등락율 <= 2'], 'candidate_count': 1},
            'code_result': {'status': 'ok', 'code': 'if B_등락율 <= 2: 매수 = False'},
        }
        with patch.object(controller, '_prepare_strategy_candidate', return_value=prepared), \
             patch.object(controller, 'create_strategy', side_effect=[
                 {'status': 'ok', 'name': '__tmp__', 'action': 'created'},
                 {'status': 'ok', 'name': 'Auto_B_Final', 'action': 'created'},
             ]), \
             patch.object(controller, 'walk_forward', return_value={'status': 'ok', 'summary': {'round_count': 3, 'success_rate': 1.0, 'mean_oos_metric': 0.5}, 'rounds': []}), \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}):
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
                report_json_path=str(tmp_path / 'report.json'),
                report_md_path=str(tmp_path / 'report.md'),
            )
            assert result['saved_report_json']['status'] == 'ok'
            assert result['saved_report_md']['status'] == 'ok'

    def test_discover_and_promote_strategy_auto_relax_retries_until_trades_exist(self, controller):
        prepared_history = []

        def prepared_factory(*args, **kwargs):
            top_n = kwargs.get('top_n')
            prepared_history.append(top_n)
            return {
                'status': 'ok',
                'analysis_result': {'status': 'ok'},
                'expression_result': {
                    'expressions': [f'등락율 <= {top_n}'],
                    'candidate_count': top_n,
                },
                'code_result': {'status': 'ok', 'code': f'if 등락율 <= {top_n}: 매수 = False'},
            }

        walk_forward_results = [
            {
                'status': 'ok',
                'summary': {'round_count': 2, 'success_rate': 0.0, 'mean_oos_metric': None, 'zero_trade_rounds': 2},
                'rounds': [
                    {'test_result': {'metrics': {'trade_count': 0}}},
                    {'test_result': {'metrics': {'trade_count': 0}}},
                ],
            },
            {
                'status': 'ok',
                'summary': {'round_count': 2, 'success_rate': 1.0, 'mean_oos_metric': 0.3, 'zero_trade_rounds': 0},
                'rounds': [
                    {'test_result': {'metrics': {'trade_count': 12}}},
                    {'test_result': {'metrics': {'trade_count': 18}}},
                ],
            },
        ]

        with patch.object(controller, '_prepare_strategy_candidate', side_effect=prepared_factory), \
             patch.object(controller, 'create_strategy', side_effect=[
                 {'status': 'ok', 'name': '__tmp1__', 'action': 'created'},
                 {'status': 'ok', 'name': '__tmp2__', 'action': 'created'},
                 {'status': 'ok', 'name': 'Auto_B_Final', 'action': 'created'},
             ]), \
             patch.object(controller, 'walk_forward', side_effect=walk_forward_results) as mock_wfo, \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}):
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
                top_n=5,
                auto_relax=True,
                max_relax_steps=2,
            )

            assert result['status'] == 'ok'
            assert result['promoted'] is True
            assert result['criteria_mode'] == 'relaxed'
            assert prepared_history == [5, 4]
            assert mock_wfo.call_count == 2
            assert result['auto_relax_history'] == [
                {'step': 0, 'top_n': 5, 'zero_trade_rounds': 2, 'total_rounds': 2},
                {'step': 1, 'top_n': 4, 'zero_trade_rounds': 0, 'total_rounds': 2},
            ]

    def test_discover_and_promote_strategy_auto_relax_fails_gracefully_at_top_n_one(self, controller):
        def prepared_factory(*args, **kwargs):
            top_n = kwargs.get('top_n')
            return {
                'status': 'ok',
                'analysis_result': {'status': 'ok'},
                'expression_result': {
                    'expressions': [f'등락율 <= {top_n}'],
                    'candidate_count': top_n,
                },
                'code_result': {'status': 'ok', 'code': f'if 등락율 <= {top_n}: 매수 = False'},
            }

        no_trade_wfo = {
            'status': 'ok',
            'summary': {'round_count': 2, 'success_rate': 0.0, 'mean_oos_metric': None, 'zero_trade_rounds': 2},
            'rounds': [
                {'test_result': {'metrics': {'trade_count': 0}}},
                {'test_result': {'metrics': {'trade_count': 0}}},
            ],
        }

        with patch.object(controller, '_prepare_strategy_candidate', side_effect=prepared_factory), \
             patch.object(controller, 'create_strategy', side_effect=[
                 {'status': 'ok', 'name': '__tmp3__', 'action': 'created'},
                 {'status': 'ok', 'name': '__tmp4__', 'action': 'created'},
             ]), \
             patch.object(controller, 'walk_forward', side_effect=[no_trade_wfo, no_trade_wfo]), \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}):
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
                top_n=2,
                auto_relax=True,
                max_relax_steps=3,
            )

            assert result['status'] == 'ok'
            assert result['promoted'] is False
            assert result['auto_relax_failed'] is True
            assert result['auto_relax_history'][-1]['top_n'] == 1
            assert result['promotion_evaluation']['reasons'][-1] == 'all_rounds_no_trades'

    def test_discover_and_promote_strategy_auto_relax_can_be_disabled(self, controller):
        prepared = {
            'status': 'ok',
            'analysis_result': {'status': 'ok'},
            'expression_result': {'expressions': ['등락율 <= 5'], 'candidate_count': 5},
            'code_result': {'status': 'ok', 'code': 'if 등락율 <= 5: 매수 = False'},
        }

        with patch.object(controller, '_prepare_strategy_candidate', return_value=prepared), \
             patch.object(controller, 'create_strategy', return_value={'status': 'ok', 'name': '__tmp__', 'action': 'created'}), \
             patch.object(controller, 'walk_forward', return_value={
                 'status': 'ok',
                 'summary': {'round_count': 2, 'success_rate': 0.0, 'mean_oos_metric': None, 'zero_trade_rounds': 2},
                 'rounds': [
                     {'test_result': {'metrics': {'trade_count': 0}}},
                     {'test_result': {'metrics': {'trade_count': 0}}},
                 ],
             }) as mock_wfo, \
             patch.object(controller, 'delete_strategy', return_value={'status': 'ok', 'action': 'deleted'}):
            result = controller.discover_and_promote_strategy(
                'Auto_B_Final',
                config_dict={'buy_strategy': 'BaseBuy', 'sell_strategy': 'BaseSell', 'start_date': 20240101, 'end_date': 20240630},
                walk_forward_settings={'train_window_days': 60, 'test_window_days': 20},
                top_n=5,
                auto_relax=False,
            )

            assert result['status'] == 'ok'
            assert result['promoted'] is False
            assert result.get('auto_relax_history') in (None, [])
            assert mock_wfo.call_count == 1

class TestResultAnalysis:
    def _write_csv(self, tmp_path):
        df = pd.DataFrame([
            {'수익률': -1.0, 'B_등락율': 0.5, 'B_시가총액': 100_000_000_000, 'B_시분초': 91000, 'B_체결강도': 90},
            {'수익률': -0.8, 'B_등락율': 0.8, 'B_시가총액': 100_000_000_000, 'B_시분초': 91500, 'B_체결강도': 91},
            {'수익률': 0.5, 'B_등락율': 2.5, 'B_시가총액': 800_000_000_000, 'B_시분초': 100000, 'B_체결강도': 110},
            {'수익률': 1.1, 'B_등락율': 3.5, 'B_시가총액': 2_000_000_000_000, 'B_시분초': 140000, 'B_체결강도': 130},
        ] * 10)
        path = tmp_path / 'result.csv'
        df.to_csv(path, index=False, encoding='utf-8-sig')
        return path

    def test_analyze_results_ok(self, controller, tmp_path):
        input_path = self._write_csv(tmp_path)
        output_path = tmp_path / 'analysis.json'

        result = controller.analyze_results(
            str(input_path),
            min_samples=5,
            quantiles=4,
            output_path=str(output_path),
        )

        assert result['status'] == 'ok'
        assert result['saved']['status'] == 'ok'
        assert output_path.exists()
        assert len(result['recommended_candidates']) > 0

    def test_generate_conditions_ok(self, controller, tmp_path):
        input_path = self._write_csv(tmp_path)
        output_path = tmp_path / 'generated_conditions.py'

        result = controller.generate_conditions(
            input_path=str(input_path),
            top_n=2,
            output_path=str(output_path),
            min_samples=5,
            quantiles=4,
        )

        assert result['status'] == 'ok'
        assert result['candidate_count'] == 2
        assert result['saved']['status'] == 'ok'
        assert '매수 = False' in result['code']
        assert output_path.exists()

    def test_generate_conditions_with_ml_feature_filter(self, controller, tmp_path):
        input_path = self._write_csv(tmp_path)
        result = controller.generate_conditions(
            input_path=str(input_path),
            top_n=5,
            min_samples=5,
            quantiles=4,
            ml_feature_limit=1,
            ml_top_n=3,
            ml_n_splits=2,
            ml_weight=0.5,
        )
        assert result['status'] == 'ok'
        assert result['feature_whitelist'] is not None
        assert len(result['feature_whitelist']) == 1
        assert result['candidate_count'] <= 5
        assert 'feature_importance_map' in result

    def test_generate_conditions_requires_source(self, controller):
        result = controller.generate_conditions()
        assert result['status'] == 'error'

    def test_analyze_results_ml_ok(self, controller, tmp_path):
        input_path = self._write_csv(tmp_path)
        output_path = tmp_path / 'ml_analysis.json'

        result = controller.analyze_results_ml(
            str(input_path),
            top_n=3,
            n_splits=2,
            output_path=str(output_path),
        )

        assert result['status'] == 'ok'
        assert len(result['top_features']) == 3
        assert result['saved']['status'] == 'ok'
        assert output_path.exists()
        assert 'shap_status' in result


# === error handling ===

class TestErrorHandling:
    def test_all_methods_return_dict(self, controller):
        """모든 public 메서드가 dict를 반환하는지 검증."""
        methods_to_test = [
            ('list_strategies', []),
            ('system_info', []),
            ('get_history', []),
        ]
        for method_name, args in methods_to_test:
            method = getattr(controller, method_name)
            result = method(*args)
            assert isinstance(result, dict), f'{method_name} did not return dict'

    def test_run_with_bad_config(self, controller):
        """잘못된 config가 에러 dict를 반환하는지 검증."""
        result = controller.run({'nonexistent_field': 'value'})
        assert isinstance(result, dict)
