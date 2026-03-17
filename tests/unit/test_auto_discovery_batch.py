"""Auto-Discovery 배치 실행 단위 테스트."""

import os
import sys
import json

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.auto_discovery import (
    AutoDiscoveryConfig,
    load_batch_config,
    run_batch,
    _merge_batch_run,
)


# ---------------------------------------------------------------------------
# load_batch_config
# ---------------------------------------------------------------------------

class TestLoadBatchConfig:
    """배치 설정 JSON 로딩 테스트."""

    def test_load_valid_config(self, tmp_path):
        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430},
            'runs': [
                {'buy_strategy': 'A'},
                {'buy_strategy': 'B', 'alpha': 0.03},
            ],
        }), encoding='utf-8')

        result = load_batch_config(str(config_file))
        assert result['common']['sell_strategy'] == 'S'
        assert len(result['runs']) == 2
        assert result['runs'][1]['alpha'] == 0.03

    def test_load_missing_runs_raises(self, tmp_path):
        config_file = tmp_path / 'bad.json'
        config_file.write_text(json.dumps({'common': {}}), encoding='utf-8')

        with pytest.raises(ValueError, match='runs'):
            load_batch_config(str(config_file))

    def test_load_empty_common(self, tmp_path):
        config_file = tmp_path / 'minimal.json'
        config_file.write_text(json.dumps({
            'runs': [{'buy_strategy': 'X', 'sell_strategy': 'Y',
                       'train_window_days': 30, 'test_window_days': 10}],
        }), encoding='utf-8')

        result = load_batch_config(str(config_file))
        assert result['common'] == {}
        assert len(result['runs']) == 1

    def test_load_nonexistent_file_raises(self):
        with pytest.raises(FileNotFoundError):
            load_batch_config('/nonexistent/batch.json')


# ---------------------------------------------------------------------------
# _merge_batch_run
# ---------------------------------------------------------------------------

class TestMergeBatchRun:
    """common + run 오버라이드 병합 테스트."""

    def test_common_only(self):
        common = {'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                  'train_window_days': 30, 'test_window_days': 10}
        config = _merge_batch_run(common, {})
        assert config.sell_strategy == 'S'
        assert config.train_window_days == 30

    def test_override_takes_precedence(self):
        common = {'alpha': 0.05, 'top_n': 5}
        override = {'alpha': 0.03, 'buy_strategy': 'MyBuy'}
        config = _merge_batch_run(common, override)
        assert config.alpha == 0.03
        assert config.top_n == 5
        assert config.buy_strategy == 'MyBuy'

    def test_unknown_fields_ignored(self):
        common = {'sell_strategy': 'S'}
        override = {'unknown_field': 'value', 'buy_strategy': 'B'}
        config = _merge_batch_run(common, override)
        assert config.buy_strategy == 'B'
        assert not hasattr(config, 'unknown_field')


# ---------------------------------------------------------------------------
# run_batch
# ---------------------------------------------------------------------------

class TestRunBatch:
    """run_batch() 순차 실행 테스트."""

    def test_batch_all_promoted(self, tmp_path):
        csv_file = tmp_path / 'result.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 3,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': True,
        }

        result = run_batch(
            common={'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                    'train_window_days': 30, 'test_window_days': 10},
            runs=[
                {'buy_strategy': 'A'},
                {'buy_strategy': 'B'},
            ],
            controller=controller,
        )

        assert result['status'] == 'ok'
        assert result['total'] == 2
        assert result['promoted'] == 2
        assert result['rejected'] == 0
        assert len(result['results']) == 2
        assert all(r['promoted'] for r in result['results'])

    def test_batch_mixed_results(self, tmp_path):
        csv_file = tmp_path / 'result.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 2,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        # 첫번째 promoted, 두번째 rejected
        controller.discover_and_promote_strategy.side_effect = [
            {'status': 'ok', 'promoted': True},
            {'status': 'ok', 'promoted': False,
             'promotion_evaluation': {'reasons': ['success_rate<0.6']}},
        ]

        result = run_batch(
            common={'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                    'train_window_days': 30, 'test_window_days': 10},
            runs=[
                {'buy_strategy': 'A'},
                {'buy_strategy': 'B'},
            ],
            controller=controller,
        )

        assert result['total'] == 2
        assert result['promoted'] == 1
        assert result['rejected'] == 1
        assert result['results'][0]['promoted'] is True
        assert result['results'][1]['promoted'] is False

    def test_batch_empty_runs(self):
        result = run_batch(common={}, runs=[], controller=MagicMock())
        assert result['status'] == 'error'
        assert 'runs' in result['message']

    def test_batch_from_file(self, tmp_path):
        csv_file = tmp_path / 'result.csv'
        csv_file.write_text('data', encoding='utf-8')

        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                       'train_window_days': 30, 'test_window_days': 10},
            'runs': [{'buy_strategy': 'X'}],
        }), encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 1,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': True,
        }

        result = run_batch(batch_path=str(config_file), controller=controller)

        assert result['status'] == 'ok'
        assert result['total'] == 1
        assert result['promoted'] == 1

    def test_batch_has_duration(self, tmp_path):
        csv_file = tmp_path / 'r.csv'
        csv_file.write_text('d', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 1,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': False,
        }

        result = run_batch(
            common={'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                    'train_window_days': 30, 'test_window_days': 10},
            runs=[{'buy_strategy': 'Z'}],
            controller=controller,
        )
        assert 'batch_duration' in result
        assert isinstance(result['batch_duration'], float)

    def test_batch_preserves_run_index(self, tmp_path):
        csv_file = tmp_path / 'r.csv'
        csv_file.write_text('d', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 1,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': True,
        }

        result = run_batch(
            common={'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                    'train_window_days': 30, 'test_window_days': 10},
            runs=[{'buy_strategy': 'A'}, {'buy_strategy': 'B'}, {'buy_strategy': 'C'}],
            controller=controller,
        )
        assert [r['index'] for r in result['results']] == [0, 1, 2]
        assert [r['buy_strategy'] for r in result['results']] == ['A', 'B', 'C']


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------

class TestBatchCliParsing:
    """discovery batch CLI 파싱 테스트."""

    def test_batch_help(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'batch', '--help'])
        assert exc_info.value.code == 0

    def test_batch_parse_config(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args(['discovery', 'batch', '--config', '/tmp/batch.json'])
        assert args.command == 'discovery'
        assert args.discovery_action == 'batch'
        assert args.batch_config == '/tmp/batch.json'

    def test_batch_short_option(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        args = parser.parse_args(['discovery', 'batch', '-c', 'my_batch.json'])
        assert args.batch_config == 'my_batch.json'

    def test_batch_missing_config(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()

        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'batch'])
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# AIBacktestController.auto_discover_batch
# ---------------------------------------------------------------------------

class TestAIControllerBatch:
    """ai_controller.auto_discover_batch() 편의 메서드 테스트."""

    def test_batch_delegates(self, tmp_path):
        with patch('cli.auto_discovery.run_batch') as mock_batch:
            mock_batch.return_value = {'status': 'ok', 'total': 2, 'promoted': 1}

            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController()
            result = controller.auto_discover_batch(
                common={'sell_strategy': 'S'},
                runs=[{'buy_strategy': 'A'}, {'buy_strategy': 'B'}],
            )

            assert result['status'] == 'ok'
            mock_batch.assert_called_once()

    def test_batch_from_file_delegates(self, tmp_path):
        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {}, 'runs': [{'buy_strategy': 'X'}],
        }), encoding='utf-8')

        with patch('cli.auto_discovery.run_batch') as mock_batch:
            mock_batch.return_value = {'status': 'ok', 'total': 1, 'promoted': 0}

            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController()
            result = controller.auto_discover_batch(batch_path=str(config_file))

            assert result['status'] == 'ok'
            mock_batch.assert_called_once()
