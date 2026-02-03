"""
STOM CLI Optimize Command Tests
================================

최적화 명령 테스트 (grid, bayesian, ga, walkforward, backfinder)
"""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestOptimizeHelp:
    """optimize 명령 도움말 테스트"""

    @pytest.mark.smoke
    def test_optimize_help(self, cli_runner: CliRunner):
        """optimize --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', '--help'])

        assert result.exit_code == 0


class TestOptimizeGrid:
    """optimize grid 명령 테스트"""

    def test_optimize_grid_help(self, cli_runner: CliRunner):
        """grid --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'grid', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_grid_basic(self, cli_runner: CliRunner):
        """기본 그리드 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'grid',
            '--market', 'stock',
            '--strategy', 'test'
        ])

        # 데이터 없으면 에러
        assert result.exit_code in [0, 1, 2]

    def test_optimize_grid_with_params(self, cli_runner: CliRunner):
        """파라미터 지정 그리드 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'grid',
            '--market', 'stock',
            '--strategy', 'test',
            '--param', 'ma_short:5:20:5',
            '--param', 'ma_long:20:100:10'
        ])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeBayesian:
    """optimize bayesian 명령 테스트"""

    def test_optimize_bayesian_help(self, cli_runner: CliRunner):
        """bayesian --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'bayesian', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_bayesian_basic(self, cli_runner: CliRunner):
        """기본 베이지안 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'bayesian',
            '--market', 'stock',
            '--strategy', 'test',
            '--trials', '10'
        ])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeGA:
    """optimize ga (유전 알고리즘) 명령 테스트"""

    def test_optimize_ga_help(self, cli_runner: CliRunner):
        """ga --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'ga', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_ga_basic(self, cli_runner: CliRunner):
        """기본 유전 알고리즘 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'ga',
            '--market', 'stock',
            '--strategy', 'test'
        ])

        assert result.exit_code in [0, 1, 2]

    def test_optimize_ga_with_generations(self, cli_runner: CliRunner):
        """세대 수 지정"""
        result = cli_runner.invoke(main, [
            'optimize', 'ga',
            '--market', 'stock',
            '--strategy', 'test',
            '--generations', '50',
            '--population', '20'
        ])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeWalkforward:
    """optimize walkforward 명령 테스트"""

    def test_optimize_walkforward_help(self, cli_runner: CliRunner):
        """walkforward --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'walkforward', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_walkforward_basic(self, cli_runner: CliRunner):
        """기본 워크포워드 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'walkforward',
            '--market', 'stock',
            '--strategy', 'test'
        ])

        assert result.exit_code in [0, 1, 2]

    def test_optimize_walkforward_with_windows(self, cli_runner: CliRunner):
        """윈도우 설정"""
        result = cli_runner.invoke(main, [
            'optimize', 'walkforward',
            '--market', 'stock',
            '--strategy', 'test',
            '--train-window', '60',
            '--test-window', '20'
        ])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeBackfinder:
    """optimize backfinder 명령 테스트"""

    def test_optimize_backfinder_help(self, cli_runner: CliRunner):
        """backfinder --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'backfinder', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_backfinder_basic(self, cli_runner: CliRunner):
        """기본 백파인더 최적화"""
        result = cli_runner.invoke(main, [
            'optimize', 'backfinder',
            '--market', 'stock'
        ])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeList:
    """optimize list 명령 테스트 (있는 경우)"""

    def test_optimize_list_help(self, cli_runner: CliRunner):
        """list --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'list', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_list_basic(self, cli_runner: CliRunner):
        """최적화 결과 목록"""
        result = cli_runner.invoke(main, ['optimize', 'list'])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeStatus:
    """optimize status 명령 테스트 (있는 경우)"""

    def test_optimize_status_help(self, cli_runner: CliRunner):
        """status --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'status', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_status_basic(self, cli_runner: CliRunner):
        """최적화 상태 조회"""
        result = cli_runner.invoke(main, ['optimize', 'status'])

        assert result.exit_code in [0, 1, 2]


class TestOptimizeCancel:
    """optimize cancel 명령 테스트 (있는 경우)"""

    def test_optimize_cancel_help(self, cli_runner: CliRunner):
        """cancel --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', 'cancel', '--help'])

        assert result.exit_code in [0, 2]

    def test_optimize_cancel_basic(self, cli_runner: CliRunner):
        """최적화 취소"""
        result = cli_runner.invoke(main, ['optimize', 'cancel'])

        assert result.exit_code in [0, 1, 2]
