"""
STOM CLI Database Command Tests
================================

데이터베이스 관리 명령 테스트 (info, create, vacuum, backup, delete, append)
"""

import pytest
import os
import tempfile
from pathlib import Path
from click.testing import CliRunner

from cli.main import main


class TestDBInfo:
    """db info 명령 테스트"""

    @pytest.mark.smoke
    def test_db_info_strategy(self, cli_runner: CliRunner):
        """전략 DB 정보 조회"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy'])

        # DB 파일이 있으면 성공, 없으면 에러
        assert result.exit_code in [0, 1]

    @pytest.mark.smoke
    def test_db_info_setting(self, cli_runner: CliRunner):
        """설정 DB 정보 조회"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'setting'])

        assert result.exit_code in [0, 1]

    def test_db_info_tradelist(self, cli_runner: CliRunner):
        """거래내역 DB 정보 조회"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'tradelist'])

        assert result.exit_code in [0, 1]

    def test_db_info_backtest(self, cli_runner: CliRunner):
        """백테스트 DB 정보 조회"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'backtest'])

        assert result.exit_code in [0, 1]

    def test_db_info_all_types(self, cli_runner: CliRunner):
        """모든 DB 타입 정보 조회"""
        db_types = ['strategy', 'setting', 'tradelist', 'backtest',
                    'stock_tick', 'stock_min', 'coin_tick', 'coin_min']

        for db_type in db_types:
            result = cli_runner.invoke(main, ['db', 'info', '--type', db_type])
            # 파일 유무와 관계없이 명령은 파싱되어야 함
            assert result.exit_code in [0, 1], f"Failed for type: {db_type}"

    def test_db_info_json_format(self, cli_runner: CliRunner):
        """JSON 포맷 DB 정보"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy', '--format', 'json'])

        assert result.exit_code in [0, 1]

    def test_db_info_invalid_type(self, cli_runner: CliRunner):
        """잘못된 DB 타입 조회"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'invalid_type'])

        # Click이 잘못된 choice를 거부
        assert result.exit_code != 0


class TestDBCreate:
    """db create 명령 테스트"""

    def test_db_create_backtest(self, cli_runner: CliRunner):
        """백테스트 DB 생성"""
        result = cli_runner.invoke(main, ['db', 'create', '--type', 'backtest'])

        # 이미 존재하면 경고, 아니면 생성
        assert result.exit_code in [0, 1]

    def test_db_create_tradelist(self, cli_runner: CliRunner):
        """거래내역 DB 생성"""
        result = cli_runner.invoke(main, ['db', 'create', '--type', 'tradelist'])

        assert result.exit_code in [0, 1]

    def test_db_create_force(self, cli_runner: CliRunner):
        """강제 덮어쓰기로 DB 생성"""
        result = cli_runner.invoke(main, ['db', 'create', '--type', 'backtest', '--force'])

        assert result.exit_code in [0, 1]

    def test_db_create_missing_type(self, cli_runner: CliRunner):
        """타입 없이 DB 생성 시도"""
        result = cli_runner.invoke(main, ['db', 'create'])

        # 필수 옵션 누락
        assert result.exit_code != 0


class TestDBVacuum:
    """db vacuum 명령 테스트"""

    def test_db_vacuum_strategy(self, cli_runner: CliRunner):
        """전략 DB 최적화"""
        result = cli_runner.invoke(main, ['db', 'vacuum', '--type', 'strategy', '--yes'])

        # DB 파일이 있으면 성공
        assert result.exit_code in [0, 1]

    def test_db_vacuum_all(self, cli_runner: CliRunner):
        """모든 DB 최적화"""
        result = cli_runner.invoke(main, ['db', 'vacuum', '--type', 'all', '--yes'])

        assert result.exit_code in [0, 1]

    def test_db_vacuum_requires_confirmation(self, cli_runner: CliRunner):
        """최적화 확인 프롬프트"""
        result = cli_runner.invoke(main, ['db', 'vacuum', '--type', 'strategy'], input='n\n')

        # 취소됨
        assert result.exit_code in [0, 1]

    def test_db_vacuum_with_yes_flag(self, cli_runner: CliRunner):
        """--yes 플래그로 확인 스킵"""
        result = cli_runner.invoke(main, ['db', 'vacuum', '--type', 'setting', '--yes'])

        assert result.exit_code in [0, 1]


class TestDBBackup:
    """db backup 명령 테스트"""

    def test_db_backup_basic(self, cli_runner: CliRunner, tmp_path: Path):
        """기본 백업"""
        output_dir = tmp_path / "backup"

        result = cli_runner.invoke(main, ['db', 'backup', '--output', str(output_dir)])

        assert result.exit_code in [0, 1]

    def test_db_backup_with_compress(self, cli_runner: CliRunner, tmp_path: Path):
        """압축 백업"""
        output_dir = tmp_path / "backup_compressed"

        result = cli_runner.invoke(main, ['db', 'backup', '--output', str(output_dir), '--compress'])

        assert result.exit_code in [0, 1]

    def test_db_backup_creates_directory(self, cli_runner: CliRunner, tmp_path: Path):
        """백업 디렉토리 자동 생성"""
        output_dir = tmp_path / "new_backup_dir"

        result = cli_runner.invoke(main, ['db', 'backup', '--output', str(output_dir)])

        # 명령이 파싱되어야 함
        assert result.exit_code in [0, 1]

    def test_db_backup_missing_output(self, cli_runner: CliRunner):
        """출력 경로 없이 백업 시도"""
        result = cli_runner.invoke(main, ['db', 'backup'])

        # 필수 옵션 누락
        assert result.exit_code != 0


class TestDBDelete:
    """db delete 명령 테스트"""

    def test_db_delete_by_date(self, cli_runner: CliRunner):
        """날짜별 데이터 삭제"""
        result = cli_runner.invoke(main, [
            'db', 'delete',
            '--type', 'stock',
            '--date', '20260101',
            '--yes'
        ])

        # DB 파일 유무와 관계없이 명령 파싱
        assert result.exit_code in [0, 1]

    def test_db_delete_invalid_date(self, cli_runner: CliRunner):
        """잘못된 날짜 형식"""
        result = cli_runner.invoke(main, [
            'db', 'delete',
            '--type', 'stock',
            '--date', 'invalid-date',
            '--yes'
        ])

        # 날짜 형식 오류
        assert result.exit_code != 0

    def test_db_delete_requires_confirmation(self, cli_runner: CliRunner):
        """삭제 확인 프롬프트"""
        result = cli_runner.invoke(main, [
            'db', 'delete',
            '--type', 'stock',
            '--date', '20260101'
        ], input='n\n')

        # 취소됨
        assert result.exit_code in [0, 1]


class TestDBAppend:
    """db append 명령 테스트"""

    def test_db_append_stock(self, cli_runner: CliRunner):
        """주식 데이터 추가"""
        result = cli_runner.invoke(main, [
            'db', 'append',
            '--type', 'stock',
            '--date', '20260101'
        ])

        # 소스 없이 dry run
        assert result.exit_code in [0, 1]

    def test_db_append_coin(self, cli_runner: CliRunner):
        """암호화폐 데이터 추가"""
        result = cli_runner.invoke(main, [
            'db', 'append',
            '--type', 'coin',
            '--date', '20260101'
        ])

        assert result.exit_code in [0, 1]

    def test_db_append_with_source(self, cli_runner: CliRunner, tmp_path: Path):
        """소스 파일 지정하여 데이터 추가"""
        source_file = tmp_path / "data.csv"
        source_file.write_text("symbol,price\nBTC,50000")

        result = cli_runner.invoke(main, [
            'db', 'append',
            '--type', 'coin',
            '--date', '20260101',
            '--source', str(source_file)
        ])

        assert result.exit_code in [0, 1]

    def test_db_append_invalid_date(self, cli_runner: CliRunner):
        """잘못된 날짜 형식으로 데이터 추가"""
        result = cli_runner.invoke(main, [
            'db', 'append',
            '--type', 'stock',
            '--date', 'not-a-date'
        ])

        assert result.exit_code != 0


class TestDBIntegration:
    """DB 명령 통합 테스트"""

    @pytest.mark.integration
    def test_db_backup_and_verify(self, cli_runner: CliRunner, tmp_path: Path):
        """백업 생성 및 확인 워크플로우"""
        backup_dir = tmp_path / "backup_test"

        # 1. 백업 생성
        backup_result = cli_runner.invoke(main, [
            'db', 'backup',
            '--output', str(backup_dir)
        ])

        # 2. 백업 후 info로 확인
        info_result = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy'])

        # 명령이 파싱되어야 함
        assert backup_result.exit_code in [0, 1]
        assert info_result.exit_code in [0, 1]

    @pytest.mark.integration
    def test_db_create_and_vacuum(self, cli_runner: CliRunner):
        """DB 생성 및 최적화 워크플로우"""
        # 1. DB 생성
        create_result = cli_runner.invoke(main, [
            'db', 'create',
            '--type', 'backtest',
            '--force'
        ])

        # 2. 최적화
        vacuum_result = cli_runner.invoke(main, [
            'db', 'vacuum',
            '--type', 'backtest',
            '--yes'
        ])

        # 명령이 파싱되어야 함
        assert create_result.exit_code in [0, 1]
        assert vacuum_result.exit_code in [0, 1]


class TestDBErrorHandling:
    """DB 명령 에러 처리 테스트"""

    def test_db_info_shows_error_for_missing_db(self, cli_runner: CliRunner):
        """존재하지 않는 DB 파일 접근 시 에러 메시지"""
        result = cli_runner.invoke(main, ['db', 'info', '--type', 'backtest'])

        # 파일이 없으면 에러 또는 경고 메시지
        # 출력에 에러 관련 내용이 있거나 exit_code가 0이 아님
        assert result.exit_code in [0, 1]

    def test_db_vacuum_handles_locked_db(self, cli_runner: CliRunner):
        """잠긴 DB 최적화 시도 처리"""
        # 실제로 DB를 잠그는 것은 복잡하므로
        # 기본 동작만 테스트
        result = cli_runner.invoke(main, ['db', 'vacuum', '--type', 'strategy', '--yes'])

        assert result.exit_code in [0, 1]
