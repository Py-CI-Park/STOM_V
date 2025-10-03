import os
import psutil
import sqlite3
import pandas as pd
from multiprocessing import Process

DB_PATH = '../_database'


def Updater(gubun, file_list_):
    def convert(index):
        if index in df_mt.index and code in df_mt['거래대금순위'][index]:
            return 1
        return 0

    print(f'[{gubun}] 데이터베이스 관심종목 칼럼 업데이트 시작')

    last = len(file_list_)
    for k, db_name in enumerate(file_list_):
        con   = sqlite3.connect(f'{DB_PATH}/{db_name}')
        df_mt = pd.read_sql("SELECT * FROM moneytop", con).set_index('index')
        df_tb = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df_tb['name'].to_list()
        table_list.remove('moneytop')
        for code in table_list:
            df = pd.read_sql(f"SELECT * FROM '{code}'", con)
            df['관심종목'] = df['index'].apply(lambda x: convert(x))
            df.to_sql(code, con, index=False, if_exists='replace', chunksize=1000)
        print(f'[{gubun}] 데이터베이스 관심종목 칼럼 업데이트 중 ... [{k + 1}/{last}]')
        con.close()

    print(f'[{gubun}] 데이터베이스 관심종목 칼럼 업데이트 완료')


if __name__ == '__main__':
    file_list = os.listdir(DB_PATH)
    file_list = [x for x in file_list if '_tick_' in x and '.db' in x and 'back' not in x]

    file_lists = []
    multi = psutil.cpu_count()
    for i in range(multi):
        file_lists.append([file for j, file in enumerate(file_list) if j % multi == i])

    proc_list = []
    for i, file_list in enumerate(file_lists):
        p = Process(target=Updater, args=(i + 1, file_list), daemon=True)
        p.start()
        proc_list.append(p)

    for p in proc_list:
        p.join()
