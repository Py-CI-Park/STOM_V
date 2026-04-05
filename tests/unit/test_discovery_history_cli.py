"""Auto-Discovery 히스토리 CLI 대시보드 단위 테스트."""

import os
import sys
import json

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.table_formatter import format_table, _truncate
from cli.history import compare_discovery_runs, save_discovery_run, init_history_db


# ---------------------------------------------------------------------------
# TestFormatTable
# ---------------------------------------------------------------------------

class TestFormatTable:
    """터미널 테이블 포맷터 테스트."""

    def test_basic_rendering(self):
        rows = [
            {'id': 1, 'name': 'Alice', 'score': 95},
            {'id': 2, 'name': 'Bob', 'score': 87},
        ]
        columns = [('id', 'ID', 3), ('name', 'Name', 5), ('score', 'Score', 5)]
        result = format_table(rows, columns)
        assert 'ID' in result
        assert 'Alice' in result
        assert 'Bob' in result
        assert result.count('|') > 0

    def test_truncation(self):
        rows = [{'val': 'a' * 100}]
        columns = [('val', 'Value', 10)]
        result = format_table(rows, columns, max_width=20)
        assert '...' in result

    def test_empty_rows(self):
        result = format_table([], [('a', 'A', 3)])
        assert result == '(no data)'

    def test_empty_columns(self):
        result = format_table([{'a': 1}], [])
        assert result == '(no data)'

    def test_missing_key_shows_empty(self):
        rows = [{'a': 1}]
        columns = [('a', 'A', 3), ('b', 'B', 3)]
        result = format_table(rows, columns)
        assert 'A' in result
        assert 'B' in result


# ---------------------------------------------------------------------------
# TestTruncate
# ---------------------------------------------------------------------------

class TestTruncate:
    """_truncate 헬퍼 테스트."""

    def test_short_value_unchanged(self):
        assert _truncate('abc', 10) == 'abc'

    def test_exact_length(self):
        assert _truncate('abcde', 5) == 'abcde'

    def test_long_value_truncated(self):
        result = _truncate('abcdefghij', 7)
        assert result == 'abcd...'
        assert len(result) == 7

    def test_very_short_max_len(self):
        result = _truncate('abcdef', 3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# TestCompareDiscoveryRuns
# ---------------------------------------------------------------------------

class TestCompareDiscoveryRuns:
    """compare_discovery_runs() 비교 로직 테스트."""

    def _seed_db(self, db_path):
        """테스트용 discovery_runs 3개를 DB에 삽입한다."""
        from dataclasses import dataclass

        @dataclass
        class FakeConfig:
            buy_strategy: str = 'A'
            sell_strategy: str = 'S'
            start_date: int = 20250401
            end_date: int = 20250430

        configs = [
            (FakeConfig(buy_strategy='A'), {
                'status': 'ok', 'promoted': True, 'strategy_name': 'Auto_A',
                'csv_path': '/tmp/a.csv', 'pipeline_duration': 10.5,
                'pipeline_timing': {'phase_a': 3.0, 'phase_b': 4.0, 'phase_c': 3.5},
                'phase_b': {'final_round': 1},
            }),
            (FakeConfig(buy_strategy='B'), {
                'status': 'ok', 'promoted': False, 'strategy_name': 'Auto_B',
                'csv_path': '/tmp/b.csv', 'pipeline_duration': 20.0,
                'pipeline_timing': {'phase_a': 8.0, 'phase_b': 7.0, 'phase_c': 5.0},
                'phase_b': {'final_round': 3},
            }),
            (FakeConfig(buy_strategy='C'), {
                'status': 'ok', 'promoted': True, 'strategy_name': 'Auto_C',
                'csv_path': '/tmp/c.csv', 'pipeline_duration': 15.0,
                'pipeline_timing': {'phase_a': 5.0, 'phase_b': 5.0, 'phase_c': 5.0},
                'phase_b': {'final_round': 2},
            }),
        ]
        ids = []
        for cfg, result in configs:
            did = save_discovery_run(cfg, result, db_path)
            ids.append(did)
        return ids

    def test_compare_basic(self, tmp_path):
        db = str(tmp_path / 'test.db')
        init_history_db(db)
        ids = self._seed_db(db)

        result = compare_discovery_runs(ids, db)
        assert len(result['runs']) == 3
        # pipeline_duration: lowest is best (10.5 for id=1)
        assert result['best']['pipeline_duration'] == ids[0]

    def test_compare_empty_ids(self, tmp_path):
        db = str(tmp_path / 'test.db')
        init_history_db(db)
        result = compare_discovery_runs([], db)
        assert result['runs'] == []
        assert result['best'] == {}

    def test_compare_best_detection(self, tmp_path):
        db = str(tmp_path / 'test.db')
        init_history_db(db)
        ids = self._seed_db(db)

        result = compare_discovery_runs([ids[0], ids[1]], db)
        assert len(result['runs']) == 2
        # phase_b_rounds: 1 < 3, so id[0] is best
        assert result['best']['phase_b_rounds'] == ids[0]


# ---------------------------------------------------------------------------
# TestHistoryCliParsing
# ---------------------------------------------------------------------------

class TestHistoryCliParsing:
    """discovery history CLI 파싱 테스트."""

    def test_history_help(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'history', '--help'])
        assert exc_info.value.code == 0

    def test_history_default_args(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args(['discovery', 'history'])
        assert args.discovery_action == 'history'
        assert args.promoted_only is False
        assert args.limit == 20
        assert args.json_output is False

    def test_history_promoted_only(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args(['discovery', 'history', '--promoted-only'])
        assert args.promoted_only is True

    def test_history_limit(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args(['discovery', 'history', '--limit', '5'])
        assert args.limit == 5

    def test_history_json_flag(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args(['discovery', 'history', '--json'])
        assert args.json_output is True


# ---------------------------------------------------------------------------
# TestCompareCliParsing
# ---------------------------------------------------------------------------

class TestCompareCliParsing:
    """discovery compare CLI 파싱 테스트."""

    def test_compare_help(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'compare', '--help'])
        assert exc_info.value.code == 0

    def test_compare_ids_parsing(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        args = parser.parse_args(['discovery', 'compare', '--ids', '1,2,3'])
        assert args.ids == '1,2,3'
        assert args.json_output is False

    def test_compare_missing_ids(self):
        from cli.subcommands import create_subcommand_parser
        parser = create_subcommand_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['discovery', 'compare'])
        assert exc_info.value.code != 0


# ---------------------------------------------------------------------------
# TestHistoryCliExecution
# ---------------------------------------------------------------------------

class TestHistoryCliExecution:
    """discovery history/compare 핸들러 실행 테스트."""

    def test_history_handler_json(self):
        with patch('cli.ai_controller.AIBacktestController') as MockCtrl:
            mock = MockCtrl.return_value
            mock.get_discovery_history.return_value = {
                'status': 'ok', 'total': 1,
                'runs': [{'discovery_id': 1, 'buy_strategy': 'A', 'promoted': 1}],
            }

            from cli.subcommands import handle_subcommand
            code = handle_subcommand(['discovery', 'history', '--json'])
            assert code == 0
            mock.get_discovery_history.assert_called_once_with(
                limit=20, promoted_only=False)

    def test_history_handler_table(self, capsys):
        with patch('cli.ai_controller.AIBacktestController') as MockCtrl:
            mock = MockCtrl.return_value
            mock.get_discovery_history.return_value = {
                'status': 'ok', 'total': 1,
                'runs': [{'discovery_id': 1, 'timestamp': '2025-01-01',
                          'buy_strategy': 'A', 'status': 'ok',
                          'promoted': 1, 'strategy_name': 'Auto_A',
                          'pipeline_duration': 10.5}],
            }

            from cli.subcommands import handle_subcommand
            code = handle_subcommand(['discovery', 'history'])
            assert code == 0
            output = capsys.readouterr().out
            assert 'Auto_A' in output

    def test_compare_handler_json(self):
        with patch('cli.ai_controller.AIBacktestController') as MockCtrl:
            mock = MockCtrl.return_value
            mock.compare_discovery_history.return_value = {
                'status': 'ok',
                'runs': [{'discovery_id': 1}, {'discovery_id': 2}],
                'best': {'pipeline_duration': 1},
            }

            from cli.subcommands import handle_subcommand
            code = handle_subcommand(['discovery', 'compare', '--ids', '1,2', '--json'])
            assert code == 0
            mock.compare_discovery_history.assert_called_once_with([1, 2])
