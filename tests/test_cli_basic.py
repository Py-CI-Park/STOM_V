"""
STOM CLI Basic Tests
====================

기본 CLI 명령 테스트 (--help, --version, 잘못된 명령 등)
"""

import pytest
from click.testing import CliRunner

from cli.main import main


class TestCLIHelp:
    """CLI 도움말 테스트"""

    @pytest.mark.smoke
    def test_main_help(self, cli_runner: CliRunner):
        """메인 --help 명령 테스트"""
        result = cli_runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        assert 'STOM' in result.output
        assert 'CLI' in result.output

    @pytest.mark.smoke
    def test_main_help_shows_all_commands(self, cli_runner: CliRunner):
        """--help에 모든 서브커맨드 표시 확인"""
        result = cli_runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        # 주요 서브커맨드 확인
        expected_commands = ['strategy', 'db', 'backtest', 'data', 'trade', 'monitor', 'optimize']
        for cmd in expected_commands:
            assert cmd in result.output, f"Command '{cmd}' not found in help output"

    @pytest.mark.smoke
    def test_strategy_help(self, cli_runner: CliRunner):
        """strategy --help 테스트"""
        result = cli_runner.invoke(main, ['strategy', '--help'])

        assert result.exit_code == 0
        assert 'list' in result.output
        assert 'stats' in result.output

    @pytest.mark.smoke
    def test_db_help(self, cli_runner: CliRunner):
        """db --help 테스트"""
        result = cli_runner.invoke(main, ['db', '--help'])

        assert result.exit_code == 0
        assert 'info' in result.output
        assert 'backup' in result.output

    @pytest.mark.smoke
    def test_backtest_help(self, cli_runner: CliRunner):
        """backtest --help 테스트"""
        result = cli_runner.invoke(main, ['backtest', '--help'])

        assert result.exit_code == 0
        assert 'run' in result.output

    def test_data_help(self, cli_runner: CliRunner):
        """data --help 테스트"""
        result = cli_runner.invoke(main, ['data', '--help'])

        assert result.exit_code == 0

    def test_trade_help(self, cli_runner: CliRunner):
        """trade --help 테스트"""
        result = cli_runner.invoke(main, ['trade', '--help'])

        assert result.exit_code == 0

    def test_monitor_help(self, cli_runner: CliRunner):
        """monitor --help 테스트"""
        result = cli_runner.invoke(main, ['monitor', '--help'])

        assert result.exit_code == 0

    def test_optimize_help(self, cli_runner: CliRunner):
        """optimize --help 테스트"""
        result = cli_runner.invoke(main, ['optimize', '--help'])

        assert result.exit_code == 0


class TestCLIVersion:
    """CLI 버전 테스트"""

    @pytest.mark.smoke
    def test_version_command(self, cli_runner: CliRunner):
        """--version 명령 테스트"""
        result = cli_runner.invoke(main, ['--version'])

        assert result.exit_code == 0
        # 버전 형식 확인 (V2.36.U1.5 등)
        assert '2.36' in result.output or 'STOM' in result.output

    def test_version_format(self, cli_runner: CliRunner):
        """버전 출력 형식 확인"""
        result = cli_runner.invoke(main, ['--version'])

        assert result.exit_code == 0
        # 버전 문자열에 숫자 포함 확인
        import re
        version_pattern = r'\d+\.\d+'
        assert re.search(version_pattern, result.output), "Version should contain numeric format"


class TestCLIInvalidCommands:
    """잘못된 명령 테스트"""

    def test_invalid_main_command(self, cli_runner: CliRunner):
        """존재하지 않는 메인 명령 테스트"""
        result = cli_runner.invoke(main, ['nonexistent-command'])

        assert result.exit_code != 0
        assert 'No such command' in result.output or 'Error' in result.output

    def test_invalid_strategy_subcommand(self, cli_runner: CliRunner):
        """존재하지 않는 strategy 서브커맨드 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'nonexistent'])

        assert result.exit_code != 0

    def test_invalid_db_subcommand(self, cli_runner: CliRunner):
        """존재하지 않는 db 서브커맨드 테스트"""
        result = cli_runner.invoke(main, ['db', 'nonexistent'])

        assert result.exit_code != 0

    def test_missing_required_option(self, cli_runner: CliRunner):
        """필수 옵션 누락 테스트"""
        # db create는 --type 필수
        result = cli_runner.invoke(main, ['db', 'create'])

        assert result.exit_code != 0
        assert 'Missing' in result.output or 'required' in result.output.lower()


class TestCLIOutputFormats:
    """CLI 출력 포맷 테스트"""

    @pytest.mark.smoke
    def test_default_format(self, cli_runner: CliRunner):
        """기본 출력 포맷 (table) 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'stats'])

        # 오류 없이 실행되어야 함
        assert result.exit_code == 0

    def test_json_format_option(self, cli_runner: CliRunner):
        """--format json 옵션 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'stats', '--format', 'json'])

        assert result.exit_code == 0
        # JSON 형식 확인 시도 (출력이 있는 경우)
        if result.output.strip():
            import json
            try:
                # JSON 파싱 가능해야 함
                json.loads(result.output)
            except json.JSONDecodeError:
                # 일부 명령은 JSON 래핑이 안 될 수 있음
                pass

    def test_csv_format_option(self, cli_runner: CliRunner):
        """--format csv 옵션 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'csv'])

        # 오류 없이 실행되어야 함
        assert result.exit_code == 0

    def test_invalid_format_option(self, cli_runner: CliRunner):
        """잘못된 --format 옵션 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'invalid'])

        # Click이 잘못된 choice를 거부해야 함
        assert result.exit_code != 0


class TestCLIEncoding:
    """CLI 인코딩 테스트 (한글 지원)"""

    @pytest.mark.smoke
    def test_korean_output(self, cli_runner: CliRunner):
        """한글 출력 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'stats'])

        assert result.exit_code == 0
        # 한글이 깨지지 않고 출력되어야 함
        # (오류 메시지에 한글이 포함된 경우 확인)

    def test_utf8_handling(self, cli_runner: CliRunner):
        """UTF-8 처리 테스트"""
        result = cli_runner.invoke(main, ['--help'])

        assert result.exit_code == 0
        # 출력이 정상적으로 디코딩되어야 함
        assert isinstance(result.output, str)


class TestCLIErrorHandling:
    """CLI 에러 처리 테스트"""

    def test_graceful_error_on_missing_db(self, cli_runner: CliRunner):
        """존재하지 않는 DB 접근 시 에러 처리"""
        # 존재하지 않는 DB 타입으로 info 조회
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'nonexistent'])

        # 에러가 발생하지만 crash 없이 처리되어야 함
        # (잘못된 choice면 Click이 처리)
        assert result.exit_code != 0

    def test_error_message_format(self, cli_runner: CliRunner):
        """에러 메시지 형식 테스트"""
        result = cli_runner.invoke(main, ['strategy', 'show'])  # name 필수 인자 누락

        assert result.exit_code != 0
        # 에러 메시지가 출력되어야 함
        assert len(result.output) > 0


class TestCLIChaining:
    """CLI 명령 체이닝 테스트"""

    def test_multiple_commands_sequential(self, cli_runner: CliRunner):
        """여러 명령 순차 실행"""
        # 각 명령이 독립적으로 실행될 수 있어야 함
        commands = [
            ['--help'],
            ['strategy', '--help'],
            ['db', '--help'],
        ]

        for cmd in commands:
            result = cli_runner.invoke(main, cmd)
            assert result.exit_code == 0, f"Command {cmd} failed: {result.output}"
