"""크로스 타임프레임 탐색 단위 테스트."""

import os
import sys
import json

import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cli.auto_discovery import (
    AutoDiscoveryConfig,
    _expand_timeframes,
    _validate_timeframe_compat,
    load_batch_config,
    run_batch,
)
from cli.discovery_report import (
    build_cross_timeframe_report,
    render_cross_timeframe_markdown,
)


# ---------------------------------------------------------------------------
# TestExpandTimeframes
# ---------------------------------------------------------------------------

class TestExpandTimeframes:
    """_expand_timeframes() 확장 로직 테스트."""

    def test_expand_tick_min(self):
        """tick/min 양쪽으로 확장."""
        runs = [{'buy_strategy': 'A'}, {'buy_strategy': 'B'}]
        result = _expand_timeframes({}, runs, ['tick', 'min'])
        assert len(result) == 4
        assert result[0]['is_tick'] is True
        assert result[0]['_timeframe'] == 'tick'
        assert result[1]['is_tick'] is False
        assert result[1]['_timeframe'] == 'min'
        assert result[2]['buy_strategy'] == 'B'
        assert result[2]['is_tick'] is True
        assert result[3]['is_tick'] is False

    def test_expand_empty_timeframes(self):
        """빈 timeframes면 원본 그대로."""
        runs = [{'buy_strategy': 'A'}]
        result = _expand_timeframes({}, runs, [])
        assert result is runs
        assert len(result) == 1

    def test_expand_single_timeframe(self):
        """단일 timeframe만 지정."""
        runs = [{'buy_strategy': 'X'}]
        result = _expand_timeframes({}, runs, ['min'])
        assert len(result) == 1
        assert result[0]['is_tick'] is False
        assert result[0]['_timeframe'] == 'min'

    def test_expand_preserves_original_fields(self):
        """원본 run 필드가 보존됨."""
        runs = [{'buy_strategy': 'A', 'alpha': 0.03}]
        result = _expand_timeframes({}, runs, ['tick', 'min'])
        assert result[0]['alpha'] == 0.03
        assert result[1]['alpha'] == 0.03


# ---------------------------------------------------------------------------
# TestCrossTimeframeBatchConfig
# ---------------------------------------------------------------------------

class TestCrossTimeframeBatchConfig:
    """배치 JSON에서 timeframes 로딩 테스트."""

    def test_load_with_timeframes(self, tmp_path):
        config_file = tmp_path / 'cross.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S'},
            'timeframes': ['tick', 'min'],
            'runs': [{'buy_strategy': 'A'}],
        }), encoding='utf-8')

        result = load_batch_config(str(config_file))
        assert result['timeframes'] == ['tick', 'min']
        assert len(result['runs']) == 1

    def test_load_without_timeframes(self, tmp_path):
        config_file = tmp_path / 'no_tf.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S'},
            'runs': [{'buy_strategy': 'A'}],
        }), encoding='utf-8')

        result = load_batch_config(str(config_file))
        assert result['timeframes'] == []


# ---------------------------------------------------------------------------
# TestCrossTimeframeReport
# ---------------------------------------------------------------------------

class TestCrossTimeframeReport:
    """build_cross_timeframe_report() 테스트."""

    def test_pair_matching(self):
        """tick/min 짝 매칭."""
        batch_result = {
            'results': [
                {'buy_strategy': 'A', '_timeframe': 'tick', 'promoted': True,
                 'status': 'ok', 'pipeline_duration': 10.0},
                {'buy_strategy': 'A', '_timeframe': 'min', 'promoted': False,
                 'status': 'ok', 'pipeline_duration': 15.0},
            ],
        }
        report = build_cross_timeframe_report(batch_result)
        assert len(report['pairs']) == 1
        assert report['pairs'][0]['winner'] == 'tick'
        assert report['tick_promoted'] == 1
        assert report['min_promoted'] == 0

    def test_both_promoted(self):
        """양쪽 승격 시 duration 비교."""
        batch_result = {
            'results': [
                {'buy_strategy': 'B', '_timeframe': 'tick', 'promoted': True,
                 'status': 'ok', 'pipeline_duration': 20.0},
                {'buy_strategy': 'B', '_timeframe': 'min', 'promoted': True,
                 'status': 'ok', 'pipeline_duration': 12.0},
            ],
        }
        report = build_cross_timeframe_report(batch_result)
        assert report['pairs'][0]['winner'] == 'min'
        assert report['tick_promoted'] == 1
        assert report['min_promoted'] == 1

    def test_markdown_rendering(self):
        """Markdown 렌더링 기본 확인."""
        report = {
            'tick_promoted': 1,
            'min_promoted': 0,
            'pairs': [
                {'buy_strategy': 'A', 'tick': {'promoted': True, 'status': 'ok'},
                 'min': {'promoted': False, 'status': 'ok'}, 'winner': 'tick'},
            ],
        }
        md = render_cross_timeframe_markdown(report)
        assert '# Cross-Timeframe Comparison' in md
        assert 'promoted' in md
        assert 'tick' in md

    def test_empty_results(self):
        """빈 결과."""
        report = build_cross_timeframe_report({'results': []})
        assert report['pairs'] == []
        assert report['tick_promoted'] == 0
        assert report['min_promoted'] == 0


# ---------------------------------------------------------------------------
# TestCrossTimeframeBatch
# ---------------------------------------------------------------------------

class TestCrossTimeframeBatch:
    """크로스 타임프레임 배치 실행 통합 테스트 (mock)."""

    def test_batch_with_timeframes_expands(self, tmp_path):
        """timeframes 지정 시 runs가 확장됨."""
        csv_file = tmp_path / 'r.csv'
        csv_file.write_text('data', encoding='utf-8')

        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                       'train_window_days': 30, 'test_window_days': 10},
            'timeframes': ['tick', 'min'],
            'runs': [{'buy_strategy': 'A'}],
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
        # 1 run × 2 timeframes = 2 results
        assert result['total'] == 2
        assert result['status'] == 'ok'

    def test_batch_without_timeframes_unchanged(self, tmp_path):
        """timeframes 미지정 시 기존 동작."""
        csv_file = tmp_path / 'r.csv'
        csv_file.write_text('data', encoding='utf-8')

        config_file = tmp_path / 'batch.json'
        config_file.write_text(json.dumps({
            'common': {'sell_strategy': 'S', 'start_date': 20250401, 'end_date': 20250430,
                       'train_window_days': 30, 'test_window_days': 10},
            'runs': [{'buy_strategy': 'A'}],
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
        assert result['total'] == 1
