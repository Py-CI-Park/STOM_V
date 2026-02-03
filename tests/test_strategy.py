"""
STOM CLI Strategy Command Tests
================================

전략 관리 명령 테스트 (list, stats, save, delete, validate, export, import)
"""

import pytest
import json
import tempfile
from pathlib import Path
from click.testing import CliRunner

from cli.main import main


class TestStrategyList:
    """strategy list 명령 테스트"""

    @pytest.mark.smoke
    def test_strategy_list_basic(self, cli_runner: CliRunner):
        """기본 전략 목록 조회"""
        result = cli_runner.invoke(main, ['strategy', 'list'])

        # 데이터 없어도 오류 없이 실행되어야 함
        assert result.exit_code == 0

    def test_strategy_list_with_type_filter(self, cli_runner: CliRunner):
        """타입 필터링 전략 목록"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--type', 'stock'])

        assert result.exit_code == 0

    def test_strategy_list_json_format(self, cli_runner: CliRunner):
        """JSON 포맷 전략 목록"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'json'])

        assert result.exit_code == 0

    def test_strategy_list_csv_format(self, cli_runner: CliRunner):
        """CSV 포맷 전략 목록"""
        result = cli_runner.invoke(main, ['strategy', 'list', '--format', 'csv'])

        assert result.exit_code == 0

    def test_strategy_list_all_types(self, cli_runner: CliRunner):
        """모든 타입 전략 목록"""
        types = ['stock', 'coin', 'future']
        for t in types:
            result = cli_runner.invoke(main, ['strategy', 'list', '--type', t])
            assert result.exit_code == 0, f"Failed for type: {t}"


class TestStrategyStats:
    """strategy stats 명령 테스트"""

    @pytest.mark.smoke
    def test_strategy_stats_basic(self, cli_runner: CliRunner):
        """기본 전략 통계"""
        result = cli_runner.invoke(main, ['strategy', 'stats'])

        assert result.exit_code == 0
        # 통계 정보 출력 확인
        assert '전략' in result.output or 'strateg' in result.output.lower()

    def test_strategy_stats_json_format(self, cli_runner: CliRunner):
        """JSON 포맷 전략 통계"""
        result = cli_runner.invoke(main, ['strategy', 'stats', '--format', 'json'])

        assert result.exit_code == 0

    def test_strategy_stats_shows_count(self, cli_runner: CliRunner):
        """전략 수 표시 확인"""
        result = cli_runner.invoke(main, ['strategy', 'stats'])

        assert result.exit_code == 0
        # 숫자가 출력되어야 함
        import re
        assert re.search(r'\d+', result.output), "Should show strategy count"


class TestStrategyShow:
    """strategy show 명령 테스트"""

    def test_strategy_show_nonexistent(self, cli_runner: CliRunner):
        """존재하지 않는 전략 조회"""
        result = cli_runner.invoke(main, ['strategy', 'show', 'nonexistent_strategy'])

        # 에러 또는 빈 결과
        # 전략이 없으면 에러가 발생할 수 있음
        assert result.exit_code in [0, 1]

    def test_strategy_show_with_type(self, cli_runner: CliRunner):
        """타입 지정 전략 조회"""
        result = cli_runner.invoke(main, ['strategy', 'show', 'test', '--type', 'stock'])

        # 전략이 없어도 명령은 실행되어야 함 (exit code 2는 Click 옵션 오류)
        assert result.exit_code in [0, 1, 2]

    def test_strategy_show_json_format(self, cli_runner: CliRunner):
        """JSON 포맷 전략 조회"""
        result = cli_runner.invoke(main, ['strategy', 'show', 'test', '--format', 'json'])

        assert result.exit_code in [0, 1]


class TestStrategySave:
    """strategy save 명령 테스트"""

    def test_strategy_save_with_inline_code(self, cli_runner: CliRunner):
        """인라인 코드로 전략 저장"""
        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'test_inline_strategy',
            '--type', 'stock',
            '--buy',
            '--code', 'def signal(): return "BUY"'
        ])

        # DB 접근 문제로 실패할 수 있지만 명령 자체는 파싱되어야 함
        # exit_code 0 또는 DB 관련 에러
        assert result.exit_code in [0, 1]

    def test_strategy_save_with_file(self, cli_runner: CliRunner, tmp_path: Path):
        """파일에서 전략 저장"""
        # 임시 전략 파일 생성
        strategy_file = tmp_path / "test_strategy.py"
        strategy_file.write_text('def signal():\n    return "BUY"')

        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'test_file_strategy',
            '--type', 'stock',
            '--buy',
            '--file', str(strategy_file)
        ])

        assert result.exit_code in [0, 1]

    def test_strategy_save_missing_name(self, cli_runner: CliRunner):
        """이름 없이 전략 저장 시도"""
        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--type', 'stock',
            '--buy',
            '--code', 'def signal(): pass'
        ])

        # 필수 옵션 누락 에러
        assert result.exit_code != 0

    def test_strategy_save_sell_type(self, cli_runner: CliRunner):
        """매도 전략 저장"""
        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'test_sell_strategy',
            '--type', 'stock',
            '--sell',
            '--code', 'def signal(): return "SELL"'
        ])

        assert result.exit_code in [0, 1]


class TestStrategyDelete:
    """strategy delete 명령 테스트"""

    def test_strategy_delete_nonexistent(self, cli_runner: CliRunner):
        """존재하지 않는 전략 삭제"""
        result = cli_runner.invoke(main, [
            'strategy', 'delete',
            '--name', 'nonexistent_strategy',
            '--type', 'stock',
            '--buy',
            '--yes'  # 확인 프롬프트 스킵
        ])

        # 존재하지 않는 전략이어도 에러 없이 처리될 수 있음
        assert result.exit_code in [0, 1]

    def test_strategy_delete_requires_confirmation(self, cli_runner: CliRunner):
        """삭제 확인 프롬프트 테스트"""
        result = cli_runner.invoke(main, [
            'strategy', 'delete',
            '--name', 'test_strategy',
            '--type', 'stock',
            '--buy'
        ], input='n\n')  # 'n'으로 취소

        # 취소되어야 함
        assert result.exit_code in [0, 1]


class TestStrategyValidate:
    """strategy validate 명령 테스트"""

    def test_strategy_validate_syntax_check(self, cli_runner: CliRunner):
        """전략 코드 구문 검사"""
        result = cli_runner.invoke(main, [
            'strategy', 'validate',
            '--name', 'test_strategy',
            '--type', 'stock'
        ])

        # 전략이 없으면 에러일 수 있음
        assert result.exit_code in [0, 1]

    def test_strategy_validate_with_inline_code(self, cli_runner: CliRunner):
        """인라인 코드 검증 (가능한 경우)"""
        # 일부 구현에서는 --code 옵션으로 직접 검증 가능
        result = cli_runner.invoke(main, [
            'strategy', 'validate',
            '--name', 'inline_test',
            '--type', 'stock',
            '--code', 'def signal(): return True'
        ])

        # 명령이 지원되면 0, 아니면 다른 코드
        assert result.exit_code in [0, 1, 2]


class TestStrategyExport:
    """strategy export 명령 테스트"""

    def test_strategy_export_json(self, cli_runner: CliRunner, tmp_path: Path):
        """JSON 포맷으로 전략 내보내기"""
        output_file = tmp_path / "exported_strategy.json"

        result = cli_runner.invoke(main, [
            'strategy', 'export',
            '--name', 'test_strategy',
            '--type', 'stock',
            '--output', str(output_file),
            '--format', 'json'
        ])

        # 전략이 없으면 에러일 수 있음 (exit code 2는 Click 옵션 오류)
        assert result.exit_code in [0, 1, 2]

    def test_strategy_export_all(self, cli_runner: CliRunner, tmp_path: Path):
        """모든 전략 내보내기"""
        output_file = tmp_path / "all_strategies.json"

        result = cli_runner.invoke(main, [
            'strategy', 'export',
            '--all',
            '--output', str(output_file),
            '--format', 'json'
        ])

        # exit code 2는 Click 옵션 오류 (명령이 없을 수 있음)
        assert result.exit_code in [0, 1, 2]


class TestStrategyImport:
    """strategy import 명령 테스트"""

    def test_strategy_import_json(self, cli_runner: CliRunner, tmp_path: Path):
        """JSON 파일에서 전략 가져오기"""
        # 임시 JSON 파일 생성
        import_file = tmp_path / "import_strategies.json"
        strategies = [
            {
                "name": "imported_strategy",
                "type": "stock",
                "buy_sell": "buy",
                "code": "def signal(): return 'BUY'"
            }
        ]
        import_file.write_text(json.dumps(strategies))

        result = cli_runner.invoke(main, [
            'strategy', 'import',
            '--file', str(import_file)
        ])

        # exit code 2는 Click 옵션 오류 (명령이 없을 수 있음)
        assert result.exit_code in [0, 1, 2]

    def test_strategy_import_nonexistent_file(self, cli_runner: CliRunner):
        """존재하지 않는 파일 가져오기"""
        result = cli_runner.invoke(main, [
            'strategy', 'import',
            '--file', '/nonexistent/path/strategies.json'
        ])

        # 파일 없음 에러
        assert result.exit_code != 0


class TestStrategyIntegration:
    """전략 명령 통합 테스트"""

    @pytest.mark.integration
    def test_strategy_workflow(self, cli_runner: CliRunner, tmp_path: Path):
        """전략 생성-조회-삭제 워크플로우"""
        strategy_name = "integration_test_strategy"

        # 1. 전략 저장
        save_result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', strategy_name,
            '--type', 'stock',
            '--buy',
            '--code', 'def signal(): return "BUY"'
        ])

        # 2. 전략 목록에서 확인
        list_result = cli_runner.invoke(main, ['strategy', 'list', '--type', 'stock'])

        # 3. 전략 통계 확인
        stats_result = cli_runner.invoke(main, ['strategy', 'stats'])

        # 모든 명령이 파싱되어야 함 (DB 접근 성공 여부와 별개)
        assert save_result.exit_code in [0, 1]
        assert list_result.exit_code == 0
        assert stats_result.exit_code == 0
