
import os
import sqlite3
from multiprocessing import Process
from static import get_logger


_pd = None


def get_pd():
    global _pd
    if _pd is None:
        import pandas as pd
        _pd = pd
    return _pd


DB_PATH = '../_database'


def Updater(gubun, file_list_):
    logger = get_logger('DBDistinct')
    logger.info(f'[{gubun}] 데이터베이스 중복 확인 시작')
    last = len(file_list_)
    count = 0
    for k, db_name in enumerate(file_list_):
        con = sqlite3.connect(f'{DB_PATH}/{db_name}')
        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()
        for code in table_list:
            if code != 'moneytop':
                df1 = get_pd().read_sql(f"SELECT DISTINCT * FROM '{code}'", con)
                df2 = get_pd().read_sql(f"SELECT * FROM '{code}'", con)
                if len(df1) != len(df2):
                    df1.to_sql(code, con, if_exists='replace', chunksize=1000)
                    count += 1
                    logger.info(f'[{gubun}] 데이터베이스 중복 제거 [{db_name}]')
        logger.info(f'[{gubun}] 데이터베이스 중복 확인 중 ... [{k + 1}/{last}]')
        con.close()
    logger.info(f'[{gubun}] 데이터베이스 중복 제거 건수 [{count}]')
    logger.info(f'[{gubun}] 데이터베이스 중복 확인 완료')


if __name__ == '__main__':
    file_list = os.listdir(DB_PATH)
    file_list = [x for x in file_list if ('_tick_' in x or '_min_' in x) and '.db' in x and 'back' not in x]

    file_lists = []
    for i in range(8):
        file_lists.append([file for j, file in enumerate(file_list) if j % 8 == i])

    proc_list = []
    for i, file_list in enumerate(file_lists):
        p = Process(target=Updater, args=(i + 1, file_list), daemon=True)
        p.start()
        proc_list.append(p)

    for p in proc_list:
        p.join()
