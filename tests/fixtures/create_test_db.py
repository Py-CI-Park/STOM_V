"""테스트용 DB 생성 스크립트.

사용법:
    python tests/fixtures/create_test_db.py [output_dir]

strategy.db와 backtest.db를 지정 디렉토리에 생성한다.
"""
import os
import sys
import sqlite3


def create_strategy_db(path):
    """테스트용 strategy.db 생성."""
    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS stockbuy (
            "index" TEXT PRIMARY KEY,
            "전략코드" TEXT
        )
    ''')
    cur.execute("INSERT OR REPLACE INTO stockbuy VALUES ('테스트매수전략', '매수 = True')")
    cur.execute("INSERT OR REPLACE INTO stockbuy VALUES ('이평돌파매수', 'if 이동평균(5) > 이동평균(20): 매수 = True')")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS stocksell (
            "index" TEXT PRIMARY KEY,
            "전략코드" TEXT
        )
    ''')
    cur.execute("INSERT OR REPLACE INTO stocksell VALUES ('테스트매도전략', 'self.sell_cond = 1')")
    cur.execute("INSERT OR REPLACE INTO stocksell VALUES ('손절매도', 'if 수익률 < -2: self.sell_cond = 1')")

    cur.execute('''
        CREATE TABLE IF NOT EXISTS formula (
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
    cur.execute("INSERT OR REPLACE INTO formula VALUES ('테스트수식', '1', '팩터1', '선:일반', '#FF0000', '1', '실선', 'x=현재가')")

    con.commit()
    con.close()
    print(f'Created: {path}')


def create_backtest_db(path):
    """테스트용 backtest.db 생성."""
    con = sqlite3.connect(path)
    cur = con.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS stock_bt (
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

    con.commit()
    con.close()
    print(f'Created: {path}')


if __name__ == '__main__':
    output_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)

    create_strategy_db(os.path.join(output_dir, 'strategy_test.db'))
    create_backtest_db(os.path.join(output_dir, 'backtest_test.db'))
    print('Done.')
