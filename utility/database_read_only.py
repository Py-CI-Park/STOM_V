
import sqlite3
import pandas as pd
from utility.setting_base import DB_SETTING, DB_STRATEGY, DB_BACKTEST, DB_TRADELIST


class DatabaseReadOnly:
    def read_sql(self, gubun, query):
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
