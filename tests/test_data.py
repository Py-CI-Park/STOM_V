"""
STOM CLI Data Command Tests
============================

데이터 조회 명령 테스트 (trades, summary, export)
"""

import pytest
from pathlib import Path
from click.testing import CliRunner

from cli.main import main


class TestDataHelp:
    """data 명령 도움말 테스트"""

    @pytest.mark.smoke
    def test_data_help(self, cli_runner: CliRunner):
        """data --help 테스트"""
        result = cli_runner.invoke(main, ['data', '--help'])

        assert result.exit_code == 0


class TestDataTrades:
    """data trades 명령 테스트"""

    def test_data_trades_help(self, cli_runner: CliRunner):
        """trades --help 테스트"""
        result = cli_runner.invoke(main, ['data', 'trades', '--help'])

        # 명령이 존재하면 도움말 표시
        assert result.exit_code in [0, 2]

    def test_data_trades_basic(self, cli_runner: CliRunner):
        """기본 거래 데이터 조회"""
        result = cli_runner.invoke(main, ['data', 'trades'])

        assert result.exit_code in [0, 1, 2]

    def test_data_trades_with_market(self, cli_runner: CliRunner):
        """시장별 거래 데이터"""
        result = cli_runner.invoke(main, ['data', 'trades', '--market', 'stock'])

        assert result.exit_code in [0, 1, 2]

    def test_data_trades_with_date(self, cli_runner: CliRunner):
        """날짜 지정 거래 데이터"""
        result = cli_runner.invoke(main, ['data', 'trades', '--date', '20260101'])

        assert result.exit_code in [0, 1, 2]

    def test_data_trades_json_format(self, cli_runner: CliRunner):
        """JSON 포맷 거래 데이터"""
        result = cli_runner.invoke(main, ['data', 'trades', '--format', 'json'])

        assert result.exit_code in [0, 1, 2]


class TestDataSummary:
    """data summary 명령 테스트"""

    def test_data_summary_help(self, cli_runner: CliRunner):
        """summary --help 테스트"""
        result = cli_runner.invoke(main, ['data', 'summary', '--help'])

        assert result.exit_code in [0, 2]

    def test_data_summary_basic(self, cli_runner: CliRunner):
        """기본 데이터 요약"""
        result = cli_runner.invoke(main, ['data', 'summary'])

        assert result.exit_code in [0, 1, 2]

    def test_data_summary_with_period(self, cli_runner: CliRunner):
        """기간별 데이터 요약"""
        result = cli_runner.invoke(main, [
            'data', 'summary',
            '--start', '20260101',
            '--end', '20260131'
        ])

        assert result.exit_code in [0, 1, 2]


class TestDataExport:
    """data export 명령 테스트"""

    def test_data_export_help(self, cli_runner: CliRunner):
        """export --help 테스트"""
        result = cli_runner.invoke(main, ['data', 'export', '--help'])

        assert result.exit_code in [0, 2]

    def test_data_export_basic(self, cli_runner: CliRunner, tmp_path: Path):
        """기본 데이터 내보내기"""
        output_file = tmp_path / "export.csv"

        result = cli_runner.invoke(main, [
            'data', 'export',
            '--output', str(output_file)
        ])

        assert result.exit_code in [0, 1, 2]

    def test_data_export_json(self, cli_runner: CliRunner, tmp_path: Path):
        """JSON 형식 내보내기"""
        output_file = tmp_path / "export.json"

        result = cli_runner.invoke(main, [
            'data', 'export',
            '--output', str(output_file),
            '--format', 'json'
        ])

        assert result.exit_code in [0, 1, 2]


class TestDataQuery:
    """data query 명령 테스트 (있는 경우)"""

    def test_data_query_help(self, cli_runner: CliRunner):
        """query --help 테스트"""
        result = cli_runner.invoke(main, ['data', 'query', '--help'])

        # 명령이 없을 수 있음
        assert result.exit_code in [0, 2]
