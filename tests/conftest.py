"""
STOM CLI Test Configuration
============================

pytest 공용 픽스처 및 설정 파일.
모든 CLI 테스트에서 공통으로 사용하는 픽스처 정의.
"""

import pytest
import os
import sys
import tempfile
import shutil
import sqlite3
from pathlib import Path
from typing import Generator, Dict, Any

from click.testing import CliRunner

# 프로젝트 루트를 Python 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.main import main


# ============================================================
# CLI Runner 픽스처
# ============================================================

@pytest.fixture
def cli_runner() -> CliRunner:
    """Click CLI 테스트 러너 생성"""
    return CliRunner()


@pytest.fixture
def cli_runner_isolated(cli_runner: CliRunner) -> Generator[CliRunner, None, None]:
    """격리된 파일시스템 환경에서 CLI 러너 제공"""
    with cli_runner.isolated_filesystem():
        yield cli_runner


# ============================================================
# 데이터베이스 픽스처
# ============================================================

@pytest.fixture(scope="session")
def test_db_dir() -> Generator[str, None, None]:
    """테스트용 임시 DB 디렉토리 생성 (세션 단위)"""
    tmp_dir = tempfile.mkdtemp(prefix="stom_test_db_")
    yield tmp_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def temp_db_dir() -> Generator[Path, None, None]:
    """테스트용 임시 DB 디렉토리 생성 (함수 단위)"""
    tmp_dir = Path(tempfile.mkdtemp(prefix="stom_test_"))
    db_dir = tmp_dir / "_database"
    db_dir.mkdir(parents=True)
    yield db_dir
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture
def mock_strategy_db(temp_db_dir: Path) -> Path:
    """테스트용 전략 데이터베이스 생성"""
    db_path = temp_db_dir / "strategy.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # 기본 테이블 생성
    tables = [
        'stockbuy', 'stocksell', 'coinbuy', 'coinsell',
        'futurebuy', 'futuresell', 'stockoptibuy', 'stockoptisell',
        'coinoptibuy', 'coinoptisell', 'futureoptibuy', 'futureoptisell',
        'stockvars', 'coinvars', 'futurevars',
        'stockoptivars', 'coinoptivars', 'futureoptivars',
        'stockbuyconds', 'stocksellconds', 'coinbuyconds', 'coinsellconds',
        'futurebuyconds', 'futuresellconds', 'schedule'
    ]

    for table in tables:
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                name TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_strategy_db_with_data(mock_strategy_db: Path) -> Path:
    """테스트 데이터가 포함된 전략 데이터베이스"""
    conn = sqlite3.connect(str(mock_strategy_db))
    cursor = conn.cursor()

    # 샘플 전략 데이터 삽입
    sample_strategies = [
        ('stockbuy', 'test_ma_cross', 'def signal(price, ma20, ma50):\n    return "BUY" if ma20 > ma50 else "HOLD"'),
        ('stockbuy', 'test_rsi_oversold', 'def signal(rsi):\n    return "BUY" if rsi < 30 else "HOLD"'),
        ('stocksell', 'test_profit_taking', 'def signal(profit):\n    return "SELL" if profit > 0.1 else "HOLD"'),
        ('coinbuy', 'test_breakout', 'def signal(price, resistance):\n    return "BUY" if price > resistance else "HOLD"'),
    ]

    for table, name, code in sample_strategies:
        cursor.execute(f"INSERT OR REPLACE INTO {table} (name, code) VALUES (?, ?)", (name, code))

    conn.commit()
    conn.close()
    return mock_strategy_db


@pytest.fixture
def mock_backtest_db(temp_db_dir: Path) -> Path:
    """테스트용 백테스트 데이터베이스 생성"""
    db_path = temp_db_dir / "backtest.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_return REAL,
            sharpe_ratio REAL,
            max_drawdown REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 샘플 백테스트 결과
    results = [
        ('test_ma_cross', '20260101', '20260131', 0.15, 1.5, -0.08),
        ('test_rsi_oversold', '20260101', '20260131', 0.08, 0.9, -0.12),
        ('test_breakout', '20260115', '20260131', 0.22, 2.1, -0.05),
    ]

    for strategy, start, end, ret, sharpe, dd in results:
        cursor.execute("""
            INSERT INTO backtest_results
            (strategy_name, start_date, end_date, total_return, sharpe_ratio, max_drawdown)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (strategy, start, end, ret, sharpe, dd))

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def mock_tradelist_db(temp_db_dir: Path) -> Path:
    """테스트용 거래내역 데이터베이스 생성"""
    db_path = temp_db_dir / "tradelist.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            trade_date TEXT NOT NULL,
            trade_time TEXT NOT NULL,
            side TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 샘플 거래 데이터
    trades = [
        ('005930', '20260101', '093000', 'BUY', 10, 70000),
        ('005930', '20260101', '143000', 'SELL', 10, 71500),
        ('000660', '20260102', '100000', 'BUY', 5, 120000),
    ]

    for symbol, date, time, side, qty, price in trades:
        cursor.execute("""
            INSERT INTO trades
            (symbol, trade_date, trade_time, side, quantity, price)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (symbol, date, time, side, qty, price))

    conn.commit()
    conn.close()
    return db_path


# ============================================================
# 샘플 데이터 픽스처
# ============================================================

@pytest.fixture
def sample_strategy_code() -> str:
    """샘플 전략 코드"""
    return """
def signal(price, moving_avg):
    '''이동평균선 교차 전략'''
    if price > moving_avg:
        return 'BUY'
    elif price < moving_avg:
        return 'SELL'
    return 'HOLD'

def risk_management(position_size, stop_loss):
    '''리스크 관리'''
    return position_size * (1 - stop_loss)
"""


@pytest.fixture
def sample_invalid_strategy_code() -> str:
    """문법 오류가 있는 전략 코드"""
    return """
def signal(price moving_avg):  # 쉼표 누락
    if price > moving_avg
        return 'BUY'  # 콜론 누락
"""


@pytest.fixture
def sample_strategies_json() -> list:
    """JSON 형식의 샘플 전략 목록"""
    return [
        {
            "name": "ma_crossover",
            "type": "stock",
            "buy_sell": "buy",
            "code": "def signal(): return 'BUY' if ma20 > ma50 else 'HOLD'"
        },
        {
            "name": "rsi_strategy",
            "type": "coin",
            "buy_sell": "buy",
            "code": "def signal(rsi): return 'BUY' if rsi < 30 else 'HOLD'"
        }
    ]


# ============================================================
# 환경 설정 픽스처
# ============================================================

@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    """백업 테스트용 디렉토리"""
    backup_path = tmp_path / "backups"
    backup_path.mkdir()
    return backup_path


@pytest.fixture(autouse=True)
def reset_environment():
    """각 테스트 전후 환경 초기화"""
    # 테스트 전 설정
    original_cwd = os.getcwd()

    yield

    # 테스트 후 복원
    os.chdir(original_cwd)


# ============================================================
# 마커 정의
# ============================================================

def pytest_configure(config):
    """pytest 마커 설정"""
    config.addinivalue_line("markers", "slow: 느린 테스트 (대용량 데이터 등)")
    config.addinivalue_line("markers", "integration: 통합 테스트")
    config.addinivalue_line("markers", "unit: 단위 테스트")
    config.addinivalue_line("markers", "smoke: 스모크 테스트")
    config.addinivalue_line("markers", "requires_db: 데이터베이스 필요 테스트")


# ============================================================
# 헬퍼 함수
# ============================================================

def invoke_cli(runner: CliRunner, args: list, catch_exceptions: bool = True) -> Any:
    """CLI 명령 실행 헬퍼"""
    return runner.invoke(main, args, catch_exceptions=catch_exceptions)


def assert_success(result) -> None:
    """CLI 결과 성공 확인"""
    assert result.exit_code == 0, f"Expected success but got exit code {result.exit_code}: {result.output}"


def assert_failure(result) -> None:
    """CLI 결과 실패 확인"""
    assert result.exit_code != 0, f"Expected failure but got exit code {result.exit_code}: {result.output}"


def assert_output_contains(result, text: str) -> None:
    """출력에 특정 텍스트 포함 확인"""
    assert text in result.output, f"Expected '{text}' in output: {result.output}"


def assert_json_output(result) -> dict:
    """JSON 출력 검증 및 파싱"""
    import json
    try:
        return json.loads(result.output)
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON output: {e}\nOutput: {result.output}")
