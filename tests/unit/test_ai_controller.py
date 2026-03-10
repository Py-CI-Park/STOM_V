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
             patch('utility.setting.DB_STRATEGY', 'fake.db'):
            result = controller.analyze_strategy('Min_B_Test', 'buy')
            assert result['status'] == 'ok'
            assert result['timeframe'] == 'min'
            assert result['var_refs'] == [0]

    def test_analyze_not_found(self, controller):
        mock_loader = {'status': 'error', 'message': '전략 없음'}
        with patch('cli.strategy_loader.load_strategy_from_db', return_value=mock_loader), \
             patch('utility.setting.DB_STRATEGY', 'fake.db'):
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

        result = controller.optimize(
            {'buy_strategy': 'T', 'sell_strategy': 'T',
             'start_date': 20250407, 'end_date': 20250409},
            {'avg_time': [60, 120]},
            objective='tpi',
            method='grid',
        )
        # optimizer uses run_fn parameter, so we test via the controller's optimize
        # which passes run_fn=None (uses real runner). With mock:
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
             patch('utility.setting.DB_STRATEGY', 'fake.db'):
            result = controller.create_strategy('Test', ['self.vars[0] > 0'], 'buy')
            assert result['status'] == 'ok'

    def test_delete_strategy(self, controller):
        mock_result = {'status': 'ok', 'name': 'Test', 'action': 'deleted'}
        with patch('cli.strategy_generator.delete_strategy_from_db', return_value=mock_result), \
             patch('utility.setting.DB_STRATEGY', 'fake.db'):
            result = controller.delete_strategy('Test', 'buy')
            assert result['status'] == 'ok'


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

    def test_generate_conditions_requires_source(self, controller):
        result = controller.generate_conditions()
        assert result['status'] == 'error'


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
