"""스모크 테스트 — pytest 수집 및 fixture 동작 확인."""


def test_conftest_fixtures_exist(sample_config, sample_result_success, sample_result_error):
    """conftest.py의 주요 fixtures가 정상 로드되는지 확인."""
    assert sample_config.buy_strategy == '테스트매수전략'
    assert sample_config.sell_strategy == '테스트매도전략'
    assert sample_config.start_date == 20250101
    assert sample_result_success['status'] == 'success'
    assert sample_result_error['status'] == 'error'


def test_tmp_strategy_db(tmp_strategy_db):
    """tmp_strategy_db fixture가 유효한 DB 파일을 생성하는지 확인."""
    import sqlite3
    con = sqlite3.connect(tmp_strategy_db)
    cur = con.cursor()
    cur.execute("SELECT `index` FROM stockbuy")
    rows = cur.fetchall()
    con.close()
    assert len(rows) == 1
    assert rows[0][0] == '테스트매수전략'


def test_tmp_backtest_db(tmp_backtest_db):
    """tmp_backtest_db fixture가 유효한 DB 파일을 생성하는지 확인."""
    import sqlite3
    con = sqlite3.connect(tmp_backtest_db)
    cur = con.cursor()
    cur.execute("SELECT * FROM stock_bt")
    rows = cur.fetchall()
    con.close()
    assert len(rows) == 1
    assert rows[0][0] == 150  # 거래횟수
