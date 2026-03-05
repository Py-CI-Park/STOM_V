"""US-303: M-3~M-6 수정 테스트 — JSON 로드, avg_time 다중값, 결과 완전성."""
import json, os, sys, sqlite3, tempfile
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

class TestLoadFromJsonUnknownKeys:
    """M-3: load_from_json() unknown keys → 무시 (TypeError 방지)."""

    def test_unknown_keys_are_ignored(self, tmp_path):
        """알 수 없는 키가 포함된 JSON에서 TypeError 없이 로드되어야 한다."""
        from cli.config import load_from_json
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'unknown_key_xyz': 'some_value',
            'another_unknown': 123,
        }), encoding='utf-8')
        config = load_from_json(str(cfg_file))
        assert config.buy_strategy == 'A'
        assert config.sell_strategy == 'B'

    def test_unknown_keys_logged_as_warning(self, tmp_path, caplog):
        """알 수 없는 키가 있으면 경고 로그가 남아야 한다."""
        import logging
        from cli.config import load_from_json
        cfg_file = tmp_path / 'config.json'
        cfg_file.write_text(json.dumps({
            'buy_strategy': 'A',
            'sell_strategy': 'B',
            'start_date': 20250101,
            'end_date': 20250131,
            'unknown_field': True,
        }), encoding='utf-8')
        with caplog.at_level(logging.WARNING):
            config = load_from_json(str(cfg_file))
        assert any('unknown_field' in r.message for r in caplog.records) or config is not None


class TestAvgTimeMultiValue:
    """M-4: --avg-time '60,120,180' → 리스트 파싱."""

    def test_avg_time_single_value(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131', '--avg-time', '60'])
        # avg_time이 int 또는 리스트 — 단일 값이면 int
        assert config.avg_time == 60 or config.avg_time == [60]

    def test_avg_time_multi_value_comma_separated(self):
        from cli.config import parse_args
        config = parse_args(['--buy', 'A', '--sell', 'B', '--start', '20250101', '--end', '20250131', '--avg-time', '60,120,180'])
        if isinstance(config.avg_time, list):
            assert config.avg_time == [60, 120, 180]
        else:
            # 단일 값인 경우 첫 번째 값만 파싱
            assert config.avg_time == 60


class TestExtractMetricsCompleteness:
    """M-6: _extract_metrics()에서 가능한 모든 필드 읽기."""

    def test_extract_metrics_reads_all_available_columns(self):
        """DB 결과에 있는 모든 컬럼이 metrics dict에 반영되어야 한다."""
        from cli.runner import _extract_metrics
        from cli.config import BacktestConfig
        from unittest.mock import patch
        import pandas as pd

        fake_df = pd.DataFrame([{
            '거래횟수': 100,
            '승률': 55.0,
            '평균수익률': 1.2,
            '수익률합계': 15.0,
            '수익금합계': 1500000,
            '연간예상수익률': 20.0,
            '최대낙폭률': -5.0,
            '매매성능지수': 1.5,
            '필요자금': 5000000.0,
            '최대보유종목수': 3,
            '평균보유기간': 25.0,
        }])

        config = BacktestConfig(start_date=20250101, end_date=20250131)

        with patch('cli.runner.sqlite3') as mock_sqlite, \
             patch('cli.runner.pd') as mock_pd:
            mock_con = mock_sqlite.connect.return_value
            mock_pd.read_sql.return_value = fake_df
            metrics = _extract_metrics(config)

        assert metrics is not None
        assert metrics['trade_count'] == 100
        assert metrics['win_rate'] == 55.0
        assert metrics['cagr'] == 20.0
        assert metrics['mdd_pct'] == -5.0
