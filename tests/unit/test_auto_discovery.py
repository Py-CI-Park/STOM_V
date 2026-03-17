"""자동 조건식 탐색 엔진 (Auto-Discovery) 단위 테스트."""

import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.auto_discovery import (
    AutoDiscoveryConfig,
    AutoDiscoveryEngine,
    find_latest_csv,
    run_multi_round_analysis,
)


# ---------------------------------------------------------------------------
# find_latest_csv
# ---------------------------------------------------------------------------

class TestFindLatestCsv:
    """find_latest_csv() 함수 테스트."""

    def test_returns_none_for_missing_dir(self):
        result = find_latest_csv('MyStrat', csv_dir='/nonexistent/path', max_retries=1, retry_delay=0)
        assert result is None

    def test_returns_none_when_no_match(self, tmp_path):
        (tmp_path / 'other_file.csv').write_text('data', encoding='utf-8')
        result = find_latest_csv('NoMatch', csv_dir=str(tmp_path), max_retries=1, retry_delay=0)
        assert result is None

    def test_finds_matching_csv(self, tmp_path):
        before = time.time() - 1
        csv_file = tmp_path / 'stock_bt_MyStrat_20260317.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        result = find_latest_csv('MyStrat', csv_dir=str(tmp_path), after_timestamp=before, max_retries=1)
        assert result is not None
        assert 'MyStrat' in result
        assert result.endswith('.csv')

    def test_selects_newest_csv(self, tmp_path):
        before = time.time() - 2

        old_csv = tmp_path / 'stock_bt_Strat_old.csv'
        old_csv.write_text('old', encoding='utf-8')
        # Set old modification time
        os.utime(str(old_csv), (before - 10, before - 10))

        new_csv = tmp_path / 'stock_bt_Strat_new.csv'
        new_csv.write_text('new', encoding='utf-8')

        result = find_latest_csv('Strat', csv_dir=str(tmp_path), after_timestamp=before, max_retries=1)
        assert result is not None
        assert 'new' in os.path.basename(result)

    def test_filters_by_timestamp(self, tmp_path):
        old_csv = tmp_path / 'stock_bt_MyStrat_old.csv'
        old_csv.write_text('old', encoding='utf-8')
        old_time = time.time() - 100
        os.utime(str(old_csv), (old_time, old_time))

        future = time.time() + 100
        result = find_latest_csv('MyStrat', csv_dir=str(tmp_path), after_timestamp=future, max_retries=1, retry_delay=0)
        assert result is None

    def test_retry_finds_file(self, tmp_path):
        """재시도 중 파일이 나타나면 찾는지 검증."""
        before = time.time() - 1

        call_count = {'n': 0}
        original_glob = __import__('glob').glob

        def delayed_glob(pattern):
            call_count['n'] += 1
            if call_count['n'] <= 1:
                return []
            return original_glob(pattern)

        csv_file = tmp_path / 'stock_bt_RetryStrat_20260317.csv'
        csv_file.write_text('data', encoding='utf-8')

        with patch('glob.glob', side_effect=delayed_glob):
            result = find_latest_csv('RetryStrat', csv_dir=str(tmp_path),
                                     after_timestamp=before, max_retries=3, retry_delay=0.01)

        assert result is not None


# ---------------------------------------------------------------------------
# run_multi_round_analysis
# ---------------------------------------------------------------------------

class TestRunMultiRoundAnalysis:
    """run_multi_round_analysis() 함수 테스트."""

    def _make_config(self, **overrides):
        defaults = dict(
            top_n=5, min_samples=30, quantiles=10, alpha=0.05,
            buy_var='매수', max_rounds=3,
            relax_alpha_step=0.02, relax_min_samples_step=5,
            relax_quantiles_step=2, relax_top_n_step=1,
            ml_feature_limit=0, ml_model_type='random_forest',
            ml_top_n=10, ml_n_splits=5, ml_weight=0.0,
        )
        defaults.update(overrides)
        return AutoDiscoveryConfig(**defaults)

    def test_success_on_first_round(self):
        controller = MagicMock()
        controller.analyze_results.return_value = {'status': 'ok', 'candidates': []}
        controller.generate_conditions.return_value = {
            'status': 'ok',
            'candidate_count': 3,
            'code': 'if 매수:\n    pass',
            'analysis_result': {'status': 'ok'},
        }

        config = self._make_config()
        result = run_multi_round_analysis('/fake/path.csv', config, controller)

        assert result['status'] == 'ok'
        assert result['final_round'] == 1
        assert len(result['rounds_log']) == 1
        assert result['rounds_log'][0]['candidate_count'] == 3

    def test_retries_with_relaxed_params(self):
        controller = MagicMock()
        controller.analyze_results.return_value = {'status': 'ok'}

        # First two rounds: 0 candidates. Third round: success
        controller.generate_conditions.side_effect = [
            {'status': 'ok', 'candidate_count': 0, 'code': '', 'analysis_result': {'status': 'ok'}},
            {'status': 'ok', 'candidate_count': 0, 'code': '', 'analysis_result': {'status': 'ok'}},
            {'status': 'ok', 'candidate_count': 2, 'code': 'if 매수:\n    pass', 'analysis_result': {'status': 'ok'}},
        ]

        config = self._make_config(max_rounds=3)
        result = run_multi_round_analysis('/fake/path.csv', config, controller)

        assert result['status'] == 'ok'
        assert result['final_round'] == 3
        assert len(result['rounds_log']) == 3
        # 파라미터 완화 확인
        assert result['rounds_log'][1]['alpha'] > result['rounds_log'][0]['alpha']
        assert result['rounds_log'][1]['min_samples'] < result['rounds_log'][0]['min_samples']

    def test_all_rounds_fail(self):
        controller = MagicMock()
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 0, 'code': '',
        }

        config = self._make_config(max_rounds=2)
        result = run_multi_round_analysis('/fake/path.csv', config, controller)

        assert result['status'] == 'error'
        assert len(result['rounds_log']) == 2


# ---------------------------------------------------------------------------
# AutoDiscoveryEngine._phase_a_backtest
# ---------------------------------------------------------------------------

class TestPhaseABacktest:
    """Phase A (백테스트 실행) 테스트."""

    def test_phase_a_success(self, tmp_path):
        csv_file = tmp_path / 'stock_bt_TestBuy_20260317.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success',
            'message': '백테스트 완료',
            'csv_path': str(csv_file),
            'metrics': {'trade_count': 100},
        }

        config = AutoDiscoveryConfig(
            buy_strategy='TestBuy', sell_strategy='TestSell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        engine = AutoDiscoveryEngine(config, controller)
        result = engine._phase_a_backtest()

        assert result['status'] == 'ok'
        assert result['phase'] == 'A'
        assert result['csv_path'] == str(csv_file)

    def test_phase_a_backtest_failure(self):
        controller = MagicMock()
        controller.run.return_value = {
            'status': 'error',
            'message': '전략이 없습니다.',
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Missing', sell_strategy='TestSell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        engine = AutoDiscoveryEngine(config, controller)
        result = engine._phase_a_backtest()

        assert result['status'] == 'error'
        assert result['phase'] == 'A'

    def test_phase_a_csv_not_found(self):
        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success',
            'message': '백테스트 완료',
            'csv_path': None,
            'metrics': {},
        }

        config = AutoDiscoveryConfig(
            buy_strategy='TestBuy', sell_strategy='TestSell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
            csv_dir='/nonexistent/dir',
        )
        engine = AutoDiscoveryEngine(config, controller)
        result = engine._phase_a_backtest()

        assert result['status'] == 'error'
        assert 'CSV' in result['message']


# ---------------------------------------------------------------------------
# AutoDiscoveryEngine.run (full pipeline mock)
# ---------------------------------------------------------------------------

class TestAutoDiscoveryEngineRun:
    """전체 파이프라인 mock 테스트."""

    def test_full_pipeline_promoted(self, tmp_path):
        csv_file = tmp_path / 'stock_bt_Buy_20260317.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        controller = MagicMock()

        # Phase A: 백테스트 성공
        controller.run.return_value = {
            'status': 'success',
            'csv_path': str(csv_file),
            'metrics': {'trade_count': 50},
        }

        # Phase B: 분석 성공
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok',
            'candidate_count': 3,
            'code': 'if 매수:\n    pass',
            'analysis_result': {'status': 'ok'},
        }

        # Phase C: discover_and_promote_strategy 성공
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok',
            'promoted': True,
            'strategy_result': {'name': 'Auto_Buy_123', 'action': 'created'},
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Buy', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['status'] == 'ok'
        assert result['promoted'] is True
        assert result['csv_path'] == str(csv_file)
        assert result['phase_a']['status'] == 'ok'
        assert result['phase_b']['status'] == 'ok'
        assert result['phase_c']['status'] == 'ok'
        assert 'pipeline_duration' in result

    def test_pipeline_stops_on_phase_a_failure(self):
        controller = MagicMock()
        controller.run.return_value = {
            'status': 'error',
            'message': '데이터 없음',
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Bad', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
            csv_dir='/nonexistent',
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['status'] == 'error'
        assert result['phase'] == 'A'
        controller.analyze_results.assert_not_called()

    def test_pipeline_stops_on_phase_b_failure(self, tmp_path):
        csv_file = tmp_path / 'stock_bt_Buy_20260317.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success',
            'csv_path': str(csv_file),
            'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok',
            'candidate_count': 0,
            'code': '',
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Buy', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
            max_rounds=1,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['status'] == 'error'
        assert result['phase'] == 'B'
        controller.discover_and_promote_strategy.assert_not_called()


# ---------------------------------------------------------------------------
# AIBacktestController.auto_discover
# ---------------------------------------------------------------------------

class TestAIControllerAutoDiscover:
    """ai_controller.auto_discover() 편의 메서드 테스트."""

    def test_auto_discover_delegates(self, tmp_path):
        csv_file = tmp_path / 'stock_bt_TestBuy_20260317.csv'
        csv_file.write_text('data', encoding='utf-8')

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run') as mock_run:
            mock_run.return_value = {'status': 'ok', 'promoted': True}

            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController()
            result = controller.auto_discover(
                buy_strategy='TestBuy', sell_strategy='TestSell',
                start_date=20250401, end_date=20250430,
                train_window_days=30, test_window_days=10,
            )

            assert result['status'] == 'ok'
            mock_run.assert_called_once()

    def test_auto_discover_with_config_object(self):
        with patch('cli.auto_discovery.AutoDiscoveryEngine.run') as mock_run:
            mock_run.return_value = {'status': 'ok', 'promoted': False}

            from cli.ai_controller import AIBacktestController
            config = AutoDiscoveryConfig(
                buy_strategy='A', sell_strategy='B',
                start_date=20250401, end_date=20250430,
                train_window_days=30, test_window_days=10,
            )
            controller = AIBacktestController()
            result = controller.auto_discover(config=config)

            assert result['status'] == 'ok'
            mock_run.assert_called_once()


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCliParsing:
    """discovery auto CLI 인자 파싱 테스트."""

    def test_discovery_auto_help(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'auto', '--help'])
        assert exc_info.value.code == 0

    def test_discovery_auto_parse_required(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args([
            'discovery', 'auto',
            '--buy', 'MyBuy',
            '--sell', 'MySell',
            '--start', '20250401',
            '--end', '20250430',
            '--train-window-days', '30',
            '--test-window-days', '10',
        ])
        assert args.command == 'discovery'
        assert args.discovery_action == 'auto'
        assert args.buy == 'MyBuy'
        assert args.sell == 'MySell'
        assert args.start == 20250401
        assert args.end == 20250430
        assert args.train_window_days == 30
        assert args.test_window_days == 10

    def test_discovery_auto_parse_defaults(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args([
            'discovery', 'auto',
            '--buy', 'B', '--sell', 'S',
            '--start', '20250401', '--end', '20250430',
            '--train-window-days', '30', '--test-window-days', '10',
        ])
        assert args.timeframe == 'tick'
        assert args.engines == 4
        assert args.top_n == 5
        assert args.alpha == 0.05
        assert args.promotion_preset == 'balanced'
        assert args.auto_relax is False
        assert args.max_rounds == 3

    def test_discovery_auto_missing_required(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'auto', '--buy', 'B'])
        assert exc_info.value.code != 0

    def test_discovery_auto_input_option_parsed(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args([
            'discovery', 'auto',
            '--input', '/tmp/my_result.csv',
            '--sell', 'MySell',
            '--start', '20250401',
            '--end', '20250430',
            '--train-window-days', '30',
            '--test-window-days', '10',
        ])
        assert args.input_file == '/tmp/my_result.csv'
        assert args.buy is None  # --buy는 --input 사용 시 선택

    def test_discovery_auto_input_short_option(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args([
            'discovery', 'auto',
            '-i', '/tmp/short.csv',
            '--sell', 'S',
            '--start', '20250401',
            '--end', '20250430',
            '--train-window-days', '30',
            '--test-window-days', '10',
        ])
        assert args.input_file == '/tmp/short.csv'


# ---------------------------------------------------------------------------
# Phase 2: input_csv 직접 지정 테스트
# ---------------------------------------------------------------------------

class TestInputCsvSkipPhaseA:
    """input_csv 지정 시 Phase A 스킵 검증."""

    def test_input_csv_skips_phase_a(self, tmp_path):
        """input_csv가 유효한 파일이면 Phase A를 스킵하고 Phase B/C로 직행한다."""
        csv_file = tmp_path / 'existing_result.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        controller = MagicMock()
        # Phase B: 분석 성공
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok',
            'candidate_count': 3,
            'code': 'if 매수:\n    pass',
            'analysis_result': {'status': 'ok'},
        }
        # Phase C: 승격 성공
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok',
            'promoted': True,
        }

        config = AutoDiscoveryConfig(
            input_csv=str(csv_file),
            sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['status'] == 'ok'
        assert result['promoted'] is True
        assert result['csv_path'] == str(csv_file)
        assert result['phase_a']['skipped'] is True
        # Phase A 백테스트가 호출되지 않았는지 확인
        controller.run.assert_not_called()

    def test_input_csv_nonexistent_returns_error(self):
        """존재하지 않는 CSV 경로 → 에러 반환."""
        controller = MagicMock()

        config = AutoDiscoveryConfig(
            input_csv='/nonexistent/path/fake.csv',
            sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['status'] == 'error'
        assert result['phase'] == 'A'
        assert 'CSV' in result['message']
        controller.run.assert_not_called()

    def test_input_csv_none_runs_phase_a(self, tmp_path):
        """input_csv=None일 때 기존대로 Phase A가 실행된다."""
        csv_file = tmp_path / 'stock_bt_TestBuy_20260317.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success',
            'csv_path': str(csv_file),
            'metrics': {'trade_count': 10},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 2,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': False,
        }

        config = AutoDiscoveryConfig(
            buy_strategy='TestBuy', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        # Phase A가 실행되었는지 확인
        controller.run.assert_called_once()
        assert result['phase_a'].get('skipped') is not True

    def test_input_csv_field_exists_on_config(self):
        """AutoDiscoveryConfig에 input_csv 필드가 존재하고 기본값은 None."""
        config = AutoDiscoveryConfig()
        assert config.input_csv is None

        config2 = AutoDiscoveryConfig(input_csv='/tmp/test.csv')
        assert config2.input_csv == '/tmp/test.csv'
