
import os
import sys
import psutil
import sqlite3
import pandas as pd
from loguru import logger
from multiprocessing import Process

DB_PATH = './_database'

list_stock_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량', '시가총액',
    'VI해제시간', 'VI가격', 'VI호가단위',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]

list_stock_min = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량', '시가총액',
    'VI해제시간', 'VI가격', 'VI호가단위',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]

list_basic_tick = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량',
    '초당거래대금', '고저평균대비등락율', '저가대비고가등락율', '초당매수금액', '초당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]

list_basic_min = [
    'index', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량',
    '분봉시가', '분봉고가', '분봉저가',
    '분당거래대금', '고저평균대비등락율', '저가대비고가등락율', '분당매수금액', '분당매도금액',
    '당일매수금액', '최고매수금액', '최고매수가격', '당일매도금액', '최고매도금액', '최고매도가격',
    '매도호가1', '매도호가2', '매도호가3', '매도호가4', '매도호가5', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5',
    '매도잔량1', '매도잔량2', '매도잔량3', '매도잔량4', '매도잔량5', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5',
    '매도총잔량', '매수총잔량', '매도수5호가잔량합', '관심종목'
]


def get_logger(name):
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <5}</level> | "
               f"<cyan>{name}</cyan> : "
               "<level>{message}</level>",
        level="DEBUG",
        colorize=True
    )
    return logger


def Updater(gubun, file_list):
    def convert_dataframe(df):
        if '당일매수금액' not in df.columns:
            if '초당매수수량' in df.columns:
                df['일자'] = (df['index'].values // 1000000).astype(int)
            else:
                df['일자'] = (df['index'].values // 10000).astype(int)
            day_list = df['일자'].unique()

            df_result = []
            for day in day_list:
                df2 = df[df['일자'] == day].copy()
                df2['저가대비고가등락율'] = (df2['고가'] / df2['저가'] - 1) * 100
                df2['저가대비고가등락율'] = df2['저가대비고가등락율'].round(2)

                if '초당매수수량' in df2.columns:
                    df2['초당매수금액'] = df2['현재가'] * df2['초당매수수량']
                    df2['초당매도금액'] = df2['현재가'] * df2['초당매도수량']
                    df2['당일매수금액'] = df2['초당매수금액'].cumsum()
                    df2['당일매도금액'] = df2['초당매도금액'].cumsum()

                    df2['가격별누적매수금액'] = df2.groupby('현재가')['초당매수금액'].cumsum()
                    df2['가격별누적매도금액'] = df2.groupby('현재가')['초당매도금액'].cumsum()

                    df2['최고매수금액'] = df2['가격별누적매수금액'].cummax()
                    df2['최고매도금액'] = df2['가격별누적매도금액'].cummax()

                    df2['최고매수가격'] = df2['현재가'].where(
                        df2['가격별누적매수금액'] == df2['최고매수금액']
                    ).ffill().fillna(df2['현재가'].iloc[0])

                    df2['최고매도가격'] = df2['현재가'].where(
                        df2['가격별누적매도금액'] == df2['최고매도금액']
                    ).ffill().fillna(df2['현재가'].iloc[0])
                else:
                    df2['분당매수금액'] = df2['현재가'] * df2['분당매수수량']
                    df2['분당매도금액'] = df2['현재가'] * df2['분당매도수량']
                    df2['당일매수금액'] = df2['분당매수금액'].cumsum()
                    df2['당일매도금액'] = df2['분당매도금액'].cumsum()

                    df2['가격별누적매수금액'] = df2.groupby('현재가')['분당매수금액'].cumsum()
                    df2['가격별누적매도금액'] = df2.groupby('현재가')['분당매도금액'].cumsum()

                    df2['최고매수금액'] = df2['가격별누적매수금액'].cummax()
                    df2['최고매도금액'] = df2['가격별누적매도금액'].cummax()

                    df2['최고매수가격'] = df2['현재가'].where(
                        df2['가격별누적매수금액'] == df2['최고매수금액']
                    ).ffill().fillna(df2['현재가'].iloc[0])

                    df2['최고매도가격'] = df2['현재가'].where(
                        df2['가격별누적매도금액'] == df2['최고매도금액']
                    ).ffill().fillna(df2['현재가'].iloc[0])

                df_result.append(df2)

            df3 = pd.concat(df_result)
        else:
            df3 = df

        if 'VI해제시간' in df3.columns:
            if '초당매수수량' in df3.columns:
                df3 = df3[list_stock_tick]
            else:
                df3 = df3[list_stock_min]
        else:
            if '초당매수수량' in df3.columns:
                df3 = df3[list_basic_tick]
            else:
                df3 = df3[list_basic_min]

        return df3

    llogger = get_logger('UpdateDatabse')
    llogger.info(f'[{gubun}] 데이터베이스 칼럼 업데이트 시작')

    last = len(file_list)
    for k, db_name in enumerate(file_list):
        con   = sqlite3.connect(f'{DB_PATH}/{db_name}')
        df_tb = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df_tb['name'].to_list()
        table_list.remove('moneytop')
        for code in table_list:
            df_origin = pd.read_sql(f"SELECT * FROM '{code}'", con)
            df_converted = convert_dataframe(df_origin)
            df_converted.to_sql(code, con, index=False, if_exists='replace', chunksize=2000)
        llogger.info(f'[{gubun}] 데이터베이스 칼럼 업데이트 중 ... [{k+1:02d}/{last:02d}]')
        con.close()

    llogger.info(f'[{gubun}] 데이터베이스 칼럼 업데이트 완료')


if __name__ == '__main__':
    file_list_ = os.listdir(DB_PATH)
    file_list_ = [x for x in file_list_ if ('_tick_' in x or '_min_' in x) and '.db' in x and 'back' not in x]

    if file_list_:
        file_lists = []
        multi = psutil.cpu_count()
        for h in range(multi):
            file_lists.append([file for j, file in enumerate(file_list_) if j % multi == h])

        proc_list = []
        for h, file_list_ in enumerate(file_lists):
            p = Process(target=Updater, args=(h + 1, file_list_), daemon=True)
            p.start()
            proc_list.append(p)

        for p in proc_list:
            p.join()
