"""STOM CLI 테스트 공통 fixtures."""
import os
import sys
import sqlite3
import tempfile
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def tmp_strategy_db(tmp_path):
    """테스트용 strategy.db를 생성하여 경로를 반환한다.

    stockbuy, stocksell 테이블에 각각 1개 전략을 삽입한다.
    """
    db_path = str(tmp_path / 'strategy.db')
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE stockbuy (
            "index" TEXT PRIMARY KEY,
            "전략코드" TEXT
        )
    ''')
    cur.execute('''
        INSERT INTO stockbuy ("index", "전략코드")
        VALUES ('테스트매수전략', '매수 = True')
    ''')

    cur.execute('''
        CREATE TABLE stocksell (
            "index" TEXT PRIMARY KEY,
            "전략코드" TEXT
        )
    ''')
    cur.execute('''
        INSERT INTO stocksell ("index", "전략코드")
        VALUES ('테스트매도전략', 'self.sell_cond = 1')
    ''')

    # formula 테이블 (Phase 4용)
    cur.execute('''
        CREATE TABLE formula (
            "수식명" TEXT,
            "체크유무" TEXT,
            "팩터명" TEXT,
            "표시형태" TEXT,
            "색상" TEXT,
            "크기" TEXT,
            "라인타입" TEXT,
            "수식코드" TEXT
        )
    ''')
    cur.execute('''
        INSERT INTO formula VALUES
        ('테스트수식', '1', '팩터1', '선:일반', '#FF0000', '1', '실선', 'x=현재가')
    ''')

    con.commit()
    con.close()
    return db_path


@pytest.fixture
def sample_config():
    """기본 BacktestConfig 인스턴스를 반환한다."""
    from cli.config import BacktestConfig
    return BacktestConfig(
        buy_strategy='테스트매수전략',
        sell_strategy='테스트매도전략',
        start_date=20250101,
        end_date=20250131,
        start_time=90000,
        end_time=152800,
        betting='1',
        avg_time=60,
        engine_count=2,
        is_tick=True,
    )


@pytest.fixture
def sample_result_success():
    """성공 백테스트 결과 dict."""
    return {
        'status': 'success',
        'message': '백테스트 완료',
        'metrics': {
            'trade_count': 150,
            'win_rate': 55.3,
            'avg_profit_pct': 0.82,
            'total_profit_pct': 12.5,
            'total_profit_krw': 1250000,
            'cagr': 15.2,
            'mdd_pct': -8.3,
            'mdd_amount': -830000,
            'tpi': 1.45,
            'seed_capital': 10000000,
            'max_hold_count': 5,
            'avg_hold_time': 35.2,
            'day_count': 22,
            'bootstrap_avg': 12.1,
            'bootstrap_min': 5.3,
            'bootstrap_max': 19.8,
        },
        'config': {
            'buy_strategy': '테스트매수전략',
            'sell_strategy': '테스트매도전략',
            'start_date': '20250101',
            'end_date': '20250131',
        },
    }


@pytest.fixture
def sample_result_error():
    """에러 백테스트 결과 dict."""
    return {
        'status': 'error',
        'message': '매수 전략이 DB에 없습니다.',
        'metrics': None,
    }


@pytest.fixture
def tmp_backtest_db(tmp_path):
    """테스트용 backtest.db를 생성하여 경로를 반환한다."""
    db_path = str(tmp_path / 'backtest.db')
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE stock_bt (
            "거래횟수" INTEGER,
            "승률" REAL,
            "평균수익률" REAL,
            "수익률합계" REAL,
            "수익금합계" INTEGER,
            "연간예상수익률" REAL,
            "최대낙폭률" REAL,
            "매매성능지수" REAL,
            "필요자금" REAL,
            "최대보유종목수" INTEGER,
            "평균보유기간" REAL,
            "매수전략" TEXT,
            "매도전략" TEXT
        )
    ''')
    cur.execute('''
        INSERT INTO stock_bt VALUES
        (150, 55.3, 0.82, 12.5, 1250000, 15.2, -8.3, 1.45, 10000000.0, 5, 35.2,
         '테스트매수전략', '테스트매도전략')
    ''')

    con.commit()
    con.close()
    return db_path
