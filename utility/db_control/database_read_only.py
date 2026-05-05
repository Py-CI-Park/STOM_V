
import sqlite3
import pandas as pd
from utility.settings.setting_base import DB_SETTING, DB_STRATEGY, DB_BACKTEST, DB_TRADELIST


class DatabaseReadOnly:
    """데이터베이스 읽기 전용 클래스입니다.
    다양한 데이터베이스에서 SQL 쿼리를 실행하여 데이터를 읽습니다.
    """
    def read_sql(self, gubun, query):
        """SQL 쿼리를 실행하여 데이터를 읽습니다.
        Args:
            gubun: 데이터베이스 구분 ('설정디비', '전략디비', '백테디비', '거래디비')
            query: SQL 쿼리
        Returns:
            쿼리 실행 결과 데이터프레임
        """
        df = None
        if gubun == '설정디비':
            con = sqlite3.connect(DB_SETTING)
            df = pd.read_sql(query, con)
            con.close()
        elif gubun == '전략디비':
            con = sqlite3.connect(DB_STRATEGY)
            df = pd.read_sql(query, con)
            con.close()
        elif gubun == '백테디비':
            con = sqlite3.connect(DB_BACKTEST)
            df = pd.read_sql(query, con)
            con.close()
        elif gubun == '거래디비':
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(query, con)
            con.close()
        return df
