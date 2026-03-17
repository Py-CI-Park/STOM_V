"""Phase 4: 리포트 강화 + 히스토리 DB 단위 테스트."""

import os
import sys
import json
import sqlite3

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ---------------------------------------------------------------------------
# pipeline_timing in AutoDiscoveryEngine.run()
# ---------------------------------------------------------------------------

class TestPipelineTiming:
    """파이프라인 타이밍 필드 검증."""

    def test_run_returns_pipeline_timing(self, tmp_path):
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        csv_file = tmp_path / 'stock_bt_Buy_20260317.csv'
        csv_file.write_text('col1,col2\n1,2', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 2,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': True,
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Buy', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert 'pipeline_timing' in result
        timing = result['pipeline_timing']
        assert 'phase_a' in timing
        assert 'phase_b' in timing
        assert 'phase_c' in timing
        assert 'total' in timing
        assert isinstance(timing['total'], float)
        assert timing['total'] >= 0

    def test_phase_a_has_duration(self, tmp_path):
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        csv_file = tmp_path / 'stock_bt_Buy_20260317.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.run.return_value = {
            'status': 'success', 'csv_path': str(csv_file), 'metrics': {},
        }

        config = AutoDiscoveryConfig(
            buy_strategy='Buy', sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        engine = AutoDiscoveryEngine(config, controller)
        result = engine._phase_a_backtest()
        assert 'phase_duration' in result
        assert isinstance(result['phase_duration'], float)

    def test_input_csv_skipped_no_duration(self, tmp_path):
        """input_csv로 스킵된 Phase A에는 phase_duration이 없다 (skipped=True)."""
        from cli.auto_discovery import AutoDiscoveryConfig, AutoDiscoveryEngine

        csv_file = tmp_path / 'existing.csv'
        csv_file.write_text('data', encoding='utf-8')

        controller = MagicMock()
        controller.analyze_results.return_value = {'status': 'ok'}
        controller.generate_conditions.return_value = {
            'status': 'ok', 'candidate_count': 1,
            'code': 'pass', 'analysis_result': {'status': 'ok'},
        }
        controller.discover_and_promote_strategy.return_value = {
            'status': 'ok', 'promoted': False,
        }

        config = AutoDiscoveryConfig(
            input_csv=str(csv_file), sell_strategy='Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = AutoDiscoveryEngine.run(config, controller)

        assert result['pipeline_timing']['phase_a'] == 0.0  # skipped → 0


# ---------------------------------------------------------------------------
# discovery_report에 pipeline_timing, rounds_log 섹션
# ---------------------------------------------------------------------------

class TestDiscoveryReportEnhancements:
    """리포트 강화 필드 검증."""

    def _sample_result_with_timing(self):
        return {
            'status': 'ok',
            'promoted': True,
            'pipeline_timing': {
                'phase_a': 45.2, 'phase_b': 3.1, 'phase_c': 180.5, 'total': 228.8,
            },
            'phase_b': {
                'rounds_log': [
                    {'round': 1, 'alpha': 0.05, 'min_samples': 30, 'quantiles': 10,
                     'top_n': 5, 'candidate_count': 0, 'status': 'ok'},
                    {'round': 2, 'alpha': 0.07, 'min_samples': 25, 'quantiles': 8,
                     'top_n': 4, 'candidate_count': 3, 'status': 'ok'},
                ],
            },
            'expression_result': {'candidate_count': 3, 'expressions': ['등락율 <= 2']},
            'walk_forward': {'summary': {'round_count': 3, 'success_rate': 1.0}},
            'promotion_evaluation': {'passed': True, 'preset': 'balanced', 'reasons': []},
            'strategy_result': {'name': 'Auto_Test', 'action': 'created'},
        }

    def test_build_report_includes_timing(self):
        from cli.discovery_report import build_discovery_report

        report = build_discovery_report(self._sample_result_with_timing())
        assert report['pipeline_timing'] is not None
        assert report['pipeline_timing']['phase_a'] == 45.2
        assert report['pipeline_timing']['total'] == 228.8

    def test_build_report_includes_rounds_log(self):
        from cli.discovery_report import build_discovery_report

        report = build_discovery_report(self._sample_result_with_timing())
        assert len(report['analysis_rounds_log']) == 2
        assert report['analysis_rounds_log'][0]['round'] == 1
        assert report['analysis_rounds_log'][1]['candidate_count'] == 3

    def test_markdown_contains_timing_section(self):
        from cli.discovery_report import build_discovery_report, render_discovery_report_markdown

        report = build_discovery_report(self._sample_result_with_timing())
        md = render_discovery_report_markdown(report)
        assert '## Pipeline Timing' in md
        assert '45.2' in md
        assert '228.8' in md

    def test_markdown_contains_rounds_log_section(self):
        from cli.discovery_report import build_discovery_report, render_discovery_report_markdown

        report = build_discovery_report(self._sample_result_with_timing())
        md = render_discovery_report_markdown(report)
        assert '## Analysis Rounds Log' in md
        assert '0.05' in md  # alpha from round 1
        assert '0.07' in md  # alpha from round 2

    def test_empty_timing_renders_none(self):
        from cli.discovery_report import build_discovery_report, render_discovery_report_markdown

        result = {
            'status': 'ok', 'promoted': False,
            'expression_result': {'candidate_count': 0, 'expressions': []},
            'promotion_evaluation': {'passed': False, 'preset': 'balanced', 'reasons': ['no_trades']},
            'strategy_result': {'name': 'Test'},
        }
        report = build_discovery_report(result)
        md = render_discovery_report_markdown(report)
        assert '## Pipeline Timing' in md
        assert '## Analysis Rounds Log' in md


# ---------------------------------------------------------------------------
# history.save_discovery_run / get_discovery_runs
# ---------------------------------------------------------------------------

class TestDiscoveryHistory:
    """히스토리 DB 저장/조회 테스트."""

    def test_save_and_retrieve(self, tmp_path):
        from cli.history import save_discovery_run, get_discovery_runs, init_history_db

        db_path = str(tmp_path / 'test_history.db')
        init_history_db(db_path)

        config = {
            'buy_strategy': 'TestBuy',
            'sell_strategy': 'TestSell',
            'start_date': 20250401,
            'end_date': 20250430,
        }
        result = {
            'status': 'ok',
            'promoted': True,
            'strategy_name': 'Auto_TestBuy_123',
            'csv_path': '/tmp/test.csv',
            'pipeline_duration': 120.5,
            'pipeline_timing': {
                'phase_a': 50.0, 'phase_b': 2.5, 'phase_c': 68.0, 'total': 120.5,
            },
            'phase_b': {'final_round': 2},
        }

        discovery_id = save_discovery_run(config, result, db_path)
        assert discovery_id > 0

        runs = get_discovery_runs(limit=10, db_path=db_path)
        assert len(runs) == 1
        assert runs[0]['buy_strategy'] == 'TestBuy'
        assert runs[0]['promoted'] == 1
        assert runs[0]['strategy_name'] == 'Auto_TestBuy_123'
        assert runs[0]['pipeline_duration'] == 120.5
        assert runs[0]['phase_a_duration'] == 50.0
        assert runs[0]['phase_b_rounds'] == 2

    def test_promoted_only_filter(self, tmp_path):
        from cli.history import save_discovery_run, get_discovery_runs, init_history_db

        db_path = str(tmp_path / 'test_history.db')
        init_history_db(db_path)

        for promoted in [True, False, True]:
            save_discovery_run(
                {'buy_strategy': 'B', 'sell_strategy': 'S'},
                {'status': 'ok', 'promoted': promoted, 'pipeline_timing': {}},
                db_path,
            )

        all_runs = get_discovery_runs(db_path=db_path)
        assert len(all_runs) == 3

        promoted_runs = get_discovery_runs(promoted_only=True, db_path=db_path)
        assert len(promoted_runs) == 2
        assert all(r['promoted'] == 1 for r in promoted_runs)

    def test_save_with_dataclass_config(self, tmp_path):
        from cli.auto_discovery import AutoDiscoveryConfig
        from cli.history import save_discovery_run, get_discovery_runs, init_history_db

        db_path = str(tmp_path / 'test_history.db')
        init_history_db(db_path)

        config = AutoDiscoveryConfig(
            buy_strategy='DC_Buy', sell_strategy='DC_Sell',
            start_date=20250401, end_date=20250430,
            train_window_days=30, test_window_days=10,
        )
        result = {'status': 'ok', 'promoted': False, 'pipeline_timing': {}}

        discovery_id = save_discovery_run(config, result, db_path)
        assert discovery_id > 0

        runs = get_discovery_runs(db_path=db_path)
        assert runs[0]['buy_strategy'] == 'DC_Buy'


# ---------------------------------------------------------------------------
# AIBacktestController.get_discovery_history
# ---------------------------------------------------------------------------

class TestControllerDiscoveryHistory:
    """ai_controller.get_discovery_history() 메서드 테스트."""

    def test_get_discovery_history(self, tmp_path):
        from cli.history import save_discovery_run, init_history_db

        db_path = str(tmp_path / 'test_history.db')
        init_history_db(db_path)
        save_discovery_run(
            {'buy_strategy': 'B'},
            {'status': 'ok', 'promoted': True, 'pipeline_timing': {}},
            db_path,
        )

        from cli.ai_controller import AIBacktestController
        controller = AIBacktestController(history_db_path=db_path)
        result = controller.get_discovery_history(limit=5)

        assert result['status'] == 'ok'
        assert result['total'] == 1
        assert result['runs'][0]['promoted'] == 1

    def test_auto_discover_saves_history(self, tmp_path):
        """auto_discover()가 히스토리를 자동 저장하는지 검증."""
        db_path = str(tmp_path / 'test_history.db')

        with patch('cli.auto_discovery.AutoDiscoveryEngine.run') as mock_run:
            mock_run.return_value = {
                'status': 'ok', 'promoted': True,
                'pipeline_timing': {'phase_a': 1.0, 'phase_b': 2.0, 'phase_c': 3.0, 'total': 6.0},
            }

            from cli.ai_controller import AIBacktestController
            controller = AIBacktestController(history_db_path=db_path)
            result = controller.auto_discover(
                buy_strategy='HistBuy', sell_strategy='HistSell',
                start_date=20250401, end_date=20250430,
                train_window_days=30, test_window_days=10,
            )

            assert 'discovery_id' in result
            assert result['discovery_id'] > 0

            history = controller.get_discovery_history()
            assert history['total'] == 1
