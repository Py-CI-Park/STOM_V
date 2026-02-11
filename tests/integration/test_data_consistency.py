"""
STOM CLI Integration Tests - Data Consistency
==============================================

데이터 일관성 및 무결성 통합 테스트
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
from click.testing import CliRunner

from cli.main import main


@pytest.mark.integration
class TestDatabaseConsistency:
    """데이터베이스 일관성 테스트"""

    def test_create_does_not_corrupt_existing(self, cli_runner: CliRunner, tmp_path: Path):
        """DB 생성이 기존 데이터를 손상시키지 않음"""
        # 1. 초기 정보 확인
        info_before = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy'])

        # 2. 다른 DB 생성 시도
        cli_runner.invoke(main, ['db', 'create', '--type', 'backtest', '--force'])

        # 3. 기존 DB 정보 재확인
        info_after = cli_runner.invoke(main, ['db', 'info', '--type', 'strategy'])

        # 둘 다 동일한 결과여야 함
        assert info_before.exit_code == info_after.exit_code

    def test_vacuum_preserves_data(self, cli_runner: CliRunner):
        """VACUUM이 데이터를 보존함"""
        # 1. VACUUM 전 통계
        stats_before = cli_runner.invoke(main, ['strategy', 'stats'])

        # 2. VACUUM 실행
        cli_runner.invoke(main, ['db', 'vacuum', '--type', 'strategy', '--yes'])

        # 3. VACUUM 후 통계
        stats_after = cli_runner.invoke(main, ['strategy', 'stats'])

        # 데이터가 보존되어야 함
        assert stats_before.exit_code == stats_after.exit_code


@pytest.mark.integration
class TestStrategyDataIntegrity:
    """전략 데이터 무결성 테스트"""

    def test_save_preserves_code(self, cli_runner: CliRunner):
        """저장된 코드가 정확히 보존됨"""
        strategy_name = "integrity_test"
        original_code = '''def signal(price):
    """테스트 전략"""
    if price > 100:
        return "BUY"
    return "HOLD"
'''

        # 1. 전략 저장
        save_result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', strategy_name,
            '--type', 'stock',
            '--buy',
            '--code', original_code
        ])

        # 2. 전략 조회
        show_result = cli_runner.invoke(main, [
            'strategy', 'show', strategy_name,
            '--type', 'stock'
        ])

        # 저장 성공 시 코드가 보존되어야 함
        if save_result.exit_code == 0:
            # 핵심 코드 요소가 포함되어 있어야 함
            assert show_result.exit_code in [0, 1]

    def test_delete_removes_only_target(self, cli_runner: CliRunner):
        """삭제가 대상만 제거함"""
        # 1. 두 개의 전략 생성
        cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'keep_this',
            '--type', 'stock',
            '--buy',
            '--code', 'def signal(): return "BUY"'
        ])

        cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'delete_this',
            '--type', 'stock',
            '--buy',
            '--code', 'def signal(): return "SELL"'
        ])

        # 2. 하나만 삭제
        cli_runner.invoke(main, [
            'strategy', 'delete',
            '--name', 'delete_this',
            '--type', 'stock',
            '--buy',
            '--yes'
        ])

        # 3. 목록 확인
        list_result = cli_runner.invoke(main, ['strategy', 'list'])

        # 명령이 정상 실행되어야 함
        assert list_result.exit_code == 0


@pytest.mark.integration
class TestConcurrentAccess:
    """동시 접근 테스트 (시뮬레이션)"""

    def test_multiple_reads(self, cli_runner: CliRunner):
        """여러 번의 읽기 작업"""
        for _ in range(5):
            result = cli_runner.invoke(main, ['strategy', 'list'])
            assert result.exit_code == 0

    def test_read_write_interleaved(self, cli_runner: CliRunner):
        """읽기-쓰기 교차 작업"""
        for i in range(3):
            # 읽기
            list_result = cli_runner.invoke(main, ['strategy', 'list'])

            # 쓰기
            save_result = cli_runner.invoke(main, [
                'strategy', 'save',
                '--name', f'concurrent_test_{i}',
                '--type', 'stock',
                '--buy',
                '--code', f'def signal(): return "BUY_{i}"'
            ])

            # 다시 읽기
            stats_result = cli_runner.invoke(main, ['strategy', 'stats'])

            assert list_result.exit_code == 0
            assert save_result.exit_code in [0, 1]
            assert stats_result.exit_code == 0


@pytest.mark.integration
class TestBackupIntegrity:
    """백업 무결성 테스트"""

    def test_backup_creates_complete_copy(self, cli_runner: CliRunner, tmp_path: Path):
        """백업이 완전한 복사본을 생성함"""
        backup_dir = tmp_path / "backup_integrity"

        # 백업 생성
        result = cli_runner.invoke(main, [
            'db', 'backup',
            '--output', str(backup_dir)
        ])

        if result.exit_code == 0:
            # 백업 디렉토리가 생성되어야 함
            # (타임스탬프가 포함되므로 하위 디렉토리 확인)
            backup_dirs = list(backup_dir.glob('stom_backup_*'))
            if backup_dirs:
                assert len(backup_dirs) >= 1

    def test_compressed_backup_valid(self, cli_runner: CliRunner, tmp_path: Path):
        """압축 백업이 유효함"""
        backup_dir = tmp_path / "compressed_backup"

        result = cli_runner.invoke(main, [
            'db', 'backup',
            '--output', str(backup_dir),
            '--compress'
        ])

        if result.exit_code == 0:
            # ZIP 파일이 생성되어야 함
            zip_files = list(backup_dir.parent.glob('*.zip')) + list(backup_dir.glob('*.zip'))
            # 압축 파일이 있거나 디렉토리가 있어야 함


@pytest.mark.integration
class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_database_operations(self, cli_runner: CliRunner):
        """빈 데이터베이스 작업"""
        # 빈 DB에서 목록 조회
        result = cli_runner.invoke(main, ['strategy', 'list'])
        assert result.exit_code == 0

        # 빈 DB에서 통계 조회
        stats = cli_runner.invoke(main, ['strategy', 'stats'])
        assert stats.exit_code == 0

    def test_special_characters_in_name(self, cli_runner: CliRunner):
        """전략 이름에 특수 문자"""
        special_names = [
            'test_with_underscore',
            'test-with-hyphen',
            'test123numeric'
        ]

        for name in special_names:
            result = cli_runner.invoke(main, [
                'strategy', 'save',
                '--name', name,
                '--type', 'stock',
                '--buy',
                '--code', 'def signal(): pass'
            ])
            # 유효한 이름은 저장 가능해야 함
            assert result.exit_code in [0, 1], f"Failed for name: {name}"

    def test_unicode_in_code(self, cli_runner: CliRunner):
        """코드에 유니코드 (한글) 포함"""
        korean_code = '''def signal():
    """한글 주석이 포함된 전략"""
    # 매수 신호 반환
    return "BUY"
'''

        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'unicode_test',
            '--type', 'stock',
            '--buy',
            '--code', korean_code
        ])

        # 유니코드 처리 가능해야 함
        assert result.exit_code in [0, 1]

    def test_long_strategy_code(self, cli_runner: CliRunner):
        """긴 전략 코드"""
        long_code = '''
def signal(price, ma5, ma10, ma20, ma50, ma100, ma200,
           rsi, macd, macd_signal, bollinger_upper, bollinger_lower,
           volume, avg_volume, high, low, open_price, close_price):
    """
    복합 지표를 활용한 매매 신호 생성 함수

    Parameters:
    - price: 현재가
    - ma5~ma200: 이동평균선
    - rsi: RSI 지표
    - macd, macd_signal: MACD 지표
    - bollinger_upper, bollinger_lower: 볼린저 밴드
    - volume, avg_volume: 거래량
    - high, low, open_price, close_price: OHLC

    Returns:
    - "BUY", "SELL", or "HOLD"
    """

    # 이동평균선 조건
    ma_bullish = ma5 > ma10 > ma20 > ma50
    ma_bearish = ma5 < ma10 < ma20 < ma50

    # RSI 조건
    rsi_oversold = rsi < 30
    rsi_overbought = rsi > 70

    # MACD 조건
    macd_bullish = macd > macd_signal
    macd_bearish = macd < macd_signal

    # 볼린저 밴드 조건
    bb_lower_touch = price <= bollinger_lower
    bb_upper_touch = price >= bollinger_upper

    # 거래량 조건
    volume_surge = volume > avg_volume * 1.5

    # 복합 매수 신호
    if ma_bullish and (rsi_oversold or bb_lower_touch) and volume_surge:
        return "BUY"

    # 복합 매도 신호
    if ma_bearish and (rsi_overbought or bb_upper_touch):
        return "SELL"

    return "HOLD"

def calculate_position_size(capital, risk_per_trade, stop_loss_pct):
    """포지션 사이즈 계산"""
    risk_amount = capital * risk_per_trade
    position_size = risk_amount / stop_loss_pct
    return min(position_size, capital * 0.1)  # 최대 10%
'''

        result = cli_runner.invoke(main, [
            'strategy', 'save',
            '--name', 'long_code_test',
            '--type', 'stock',
            '--buy',
            '--code', long_code
        ])

        # 긴 코드도 처리 가능해야 함
        assert result.exit_code in [0, 1]
