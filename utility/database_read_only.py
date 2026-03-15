
import sqlite3
from utility.setting_base import DB_SETTING, DB_STRATEGY, DB_BACKTEST, DB_TRADELIST


_pd = None


def get_pd():
    global _pd
    if _pd is None:
        import pandas as pd
        _pd = pd
    return _pd


class DatabaseReadOnly:
    def __init__(self):
        self.con1 = sqlite3.connect(DB_SETTING)
        self.con2 = sqlite3.connect(DB_STRATEGY)
        self.con3 = sqlite3.connect(DB_BACKTEST)
        self.con4 = sqlite3.connect(DB_TRADELIST)

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    def read_sql(self, gubun, query):
        df = None
        if gubun == '설정디비':
            df = get_pd().read_sql(query, self.con1)
        elif gubun == '전략디비':
            df = get_pd().read_sql(query, self.con2)
        elif gubun == '백테디비':
            df = get_pd().read_sql(query, self.con3)
        elif gubun == '거래디비':
            df = get_pd().read_sql(query, self.con4)
        return df
