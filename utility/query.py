
import os
import shutil
import sqlite3
from utility.lazy_imports import get_pd
from utility.static import error_decorator, set_builtin_print
from utility.setting_base import ui_num, DB_TRADELIST, DB_SETTING, DB_STRATEGY, DB_COIN_TICK, DB_PATH, DB_STOCK_TICK_BACK, \
    DB_COIN_TICK_BACK, DB_STOCK_TICK, DB_BACKTEST, DB_STOCK_MIN_BACK, DB_COIN_MIN_BACK, DB_STOCK_MIN, \
    DB_COIN_MIN, DB_FUTURE_MIN_BACK, DB_FUTURE_MIN, DB_CODE_INFO, DB_FUTURE_TICK_BACK, DB_FUTURE_TICK


class Query:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ  = qlist[0]
        self.queryQ   = qlist[2]
        self.dict_set = dict_set
        self.con1     = sqlite3.connect(DB_SETTING)
        self.cur1     = self.con1.cursor()
        self.con2     = sqlite3.connect(DB_TRADELIST)
        self.cur2     = self.con2.cursor()
        self.con3     = sqlite3.connect(DB_STRATEGY)
        self.cur3     = self.con3.cursor()
        self.con4     = sqlite3.connect(DB_CODE_INFO)

        set_builtin_print(True, self.windowQ)
        self.MainLoop()

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    @error_decorator
    def MainLoop(self):
        while True:
            data = self.queryQ.get()
            if data[0] == '설정변경':
                self.dict_set = data[1]

            elif data[0] == '설정파일변경':
                self.con1.close()
                os.remove(data[2])
                shutil.copy(data[1], data[2])
                self.con1 = sqlite3.connect(DB_SETTING)
                self.cur1 = self.con1.cursor()

            elif data[0] == '설정디비':
                if len(data) == 2:
                    self.cur1.execute(data[1])
                    self.con1.commit()
                elif len(data) == 3:
                    self.cur1.execute(data[1], data[2])
                    self.con1.commit()
                elif len(data) == 4:
                    data[1].to_sql(data[2], self.con1, if_exists=data[3], chunksize=1000)

            elif data[0] == '거래디비':
                if len(data) == 2:
                    self.cur2.execute(data[1])
                    self.con2.commit()
                elif len(data) == 3:
                    self.cur2.execute(data[1], data[2])
                    self.con2.commit()
                elif len(data) == 4:
                    data[1].to_sql(data[2], self.con2, if_exists=data[3], chunksize=1000)

            elif data[0] == '전략디비':
                if len(data) == 2:
                    self.cur3.execute(data[1])
                    self.con3.commit()
                elif len(data) == 3:
                    self.cur3.execute(data[1], data[2])
                    self.con3.commit()
                elif len(data) == 4:
                    data[1].to_sql(data[2], self.con3, if_exists=data[3], chunksize=1000)

            elif data[0] == '종목디비':
                if len(data) == 4:
                    data[1].to_sql(data[2], self.con4, if_exists=data[3], chunksize=1000)

            elif data[0] == '백테디비':
                con = sqlite3.connect(DB_BACKTEST)
                cur = con.cursor()
                cur.execute(data[1])
                con.commit()
                con.close()

            elif '백테DB지정일자삭제' in data[0]:
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                    else:
                        BACK_FILE = DB_FUTURE_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK
                else:
                    BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK

                con = sqlite3.connect(BACK_FILE)
                df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                if table_list:
                    cur = con.cursor()
                    last = len(table_list)
                    for i, code in enumerate(table_list):
                        query_del = f"DELETE FROM '{code}' WHERE `index` LIKE '{data[1]}%'"
                        cur.execute(query_del)
                        self.windowQ.put((ui_num['DB관리'], f'백테DB [{code}] 지정일자 데이터 삭제 중 ... [{i + 1}/{last}]'))
                    con.commit()
                    self.windowQ.put((ui_num['DB관리'], '백테DB 지정일자 데이터 삭제 완료'))
                else:
                    self.windowQ.put((ui_num['DB관리'], '백테DB에 데이터가 존재하지 않습니다.'))
                con.close()

            elif '일자DB지정일자삭제' in data[0]:
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                    else:
                        firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                else:
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

                file_name = f'{DB_PATH}/{firstname}' + data[1] + '.db'
                if os.path.isfile(file_name):
                    os.remove(file_name)
                    self.windowQ.put((ui_num['DB관리'], f'일자DB [{file_name}] 삭제 완료'))
                else:
                    self.windowQ.put((ui_num['DB관리'], '지정한 일자의 일자DB가 존재하지 않습니다.'))

            elif '일자DB지정시간이후삭제' in data[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                    else:
                        firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                else:
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                if file_list:
                    last = len(file_list)
                    for i, db_name in enumerate(file_list):
                        con = sqlite3.connect(f'{DB_PATH}/{db_name}')
                        cur = con.cursor()
                        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                        table_list = df['name'].to_list()
                        df = get_pd().read_sql('SELECT * FROM moneytop', con)
                        df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                        df = df[df['시간'] <= int(data[1])]
                        df.drop(columns=['시간'], inplace=True)
                        df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
                        mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
                        for code in table_list:
                            if code in mtlist:
                                df = get_pd().read_sql(f'SELECT * FROM "{code}"', con)
                                df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                                df = df[df['시간'] <= int(data[1])]
                                df.drop(columns=['시간'], inplace=True)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='replace', chunksize=1000)
                                else:
                                    cur.execute(f'DROP TABLE "{code}"')
                            elif code != 'moneytop':
                                cur.execute(f'DROP TABLE "{code}"')
                        cur.execute('VACUUM;')
                        con.close()
                        self.windowQ.put((ui_num['DB관리'], f'일자DB [{db_name}] 지정시간 이후 데이터 삭제 중 ... [{i + 1}/{last}]'))
                    self.windowQ.put((ui_num['DB관리'], '일자DB 지정시간 이후 데이터 삭제 완료'))
                else:
                    self.windowQ.put((ui_num['DB관리'], '일자DB가 존재하지 않습니다.'))

            elif '당일데이터지정시간이후삭제' in data[0]:
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                    else:
                        DB_FILE = DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN
                else:
                    DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

                con = sqlite3.connect(DB_FILE)
                try:
                    df = get_pd().read_sql('SELECT * FROM moneytop', con)
                except:
                    self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
                else:
                    cur = con.cursor()
                    df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                    df = df[df['시간'] <= int(data[1])]
                    df.drop(columns=['시간'], inplace=True)
                    df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
                    mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))

                    df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                    table_list = df['name'].to_list()
                    if table_list:
                        last = len(table_list)
                        for i, code in enumerate(table_list):
                            if code in mtlist:
                                df = get_pd().read_sql(f'SELECT * FROM "{code}"', con)
                                df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                                df = df[df['시간'] <= int(data[1])]
                                df.drop(columns=['시간'], inplace=True)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='replace', chunksize=1000)
                                else:
                                    cur.execute(f'DROP TABLE "{code}"')
                            elif code != 'moneytop':
                                cur.execute(f'DROP TABLE "{code}"')
                            self.windowQ.put((ui_num['DB관리'], f'당일DB [{code}] 지정시간 이후 데이터 삭제 중 ... [{i + 1}/{last}]'))
                        cur.execute('VACUUM;')
                        self.windowQ.put((ui_num['DB관리'], '당일DB 지정시간 이후 데이터 삭제 완료'))
                    else:
                        self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
                con.close()

            elif data[0] == '주식체결시간조정':
                if '키움증권' in self.dict_set['증권사']:
                    DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                else:
                    DB_FILE = DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN

                con = sqlite3.connect(DB_FILE)
                df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                if table_list:
                    cur = con.cursor()
                    last = len(table_list)
                    for i, code in enumerate(table_list):
                        df = get_pd().read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{data[1]}%"', con)
                        cur.execute(f'DELETE FROM "{code}" WHERE "index" LIKE "{data[1]}%"')
                        con.commit()
                        if self.dict_set['주식타임프레임']:
                            df['index'] = df['index'] - 10000
                        else:
                            df['index'] = df['index'] - 100
                        df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                        self.windowQ.put((ui_num['DB관리'], f'당일DB [{code}] 체결시간 조정 중 ... [{i + 1}/{last}]'))
                    self.windowQ.put((ui_num['DB관리'], '당일DB 체결시간 조정 완료'))
                else:
                    self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
                con.close()

            elif '백테DB생성' in data[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                        firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                    else:
                        BACK_FILE = DB_FUTURE_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK
                        firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                else:
                    BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                if file_list:
                    if os.path.isfile(BACK_FILE):
                        os.remove(BACK_FILE)
                        self.windowQ.put((ui_num['DB관리'], f'{BACK_FILE} 삭제 완료'))

                    con = sqlite3.connect(BACK_FILE)
                    if 'stock' in firstname:
                        df = get_pd().read_sql('SELECT * FROM stockinfo', self.con4)
                        df.to_sql('stockinfo', con, index=False, if_exists='replace', chunksize=1000)
                    elif 'future' in firstname:
                        df = get_pd().read_sql('SELECT * FROM futureinfo', self.con4)
                        df.to_sql('futureinfo', con, index=False, if_exists='replace', chunksize=1000)

                    file_list = [x for x in file_list if int(data[1]) <= int(x.split(firstname)[1].replace('.db', '')) <= int(data[2])]
                    if file_list:
                        last = len(file_list)
                        for i, db_name in enumerate(file_list):
                            con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                            df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                            table_list = df['name'].to_list()
                            for code in table_list:
                                df = get_pd().read_sql(f'SELECT * FROM "{code}"', con2)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='append', chunksize=2000)
                            con2.close()
                            self.windowQ.put((ui_num['DB관리'], f'백테DB [{db_name}] 데이터 추가 중 ... [{i + 1}/{last}]'))
                        self.windowQ.put((ui_num['DB관리'], f'백테DB {BACK_FILE} 생성 완료'))
                    else:
                        self.windowQ.put((ui_num['DB관리'], '지정한 기간의 일자DB가 존재하지 않습니다.'))
                    con.close()
                else:
                    self.windowQ.put((ui_num['DB관리'], '일자DB가 존재하지 않습니다.'))

            elif '백테디비추가1' in data[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                        firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                    else:
                        BACK_FILE = DB_FUTURE_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK
                        firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                else:
                    BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                if file_list:
                    con = sqlite3.connect(BACK_FILE)
                    if 'stock' in firstname:
                        df = get_pd().read_sql('SELECT * FROM stockinfo', self.con4)
                        df.to_sql('stockinfo', con, index=False, if_exists='replace', chunksize=1000)
                    elif 'future' in firstname:
                        df = get_pd().read_sql('SELECT * FROM futureinfo', self.con4)
                        df.to_sql('futureinfo', con, index=False, if_exists='replace', chunksize=1000)

                    file_list = [x for x in file_list if int(data[1]) <= int(x.split(firstname)[1].replace('.db', '')) <= int(data[2])]
                    if file_list:
                        last = len(file_list)
                        for i, db_name in enumerate(file_list):
                            con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                            df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                            table_list = df['name'].to_list()
                            for code in table_list:
                                df = get_pd().read_sql(f'SELECT * FROM "{code}"', con2)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                            con2.close()
                            self.windowQ.put((ui_num['DB관리'], f'백테DB [{db_name}] 데이터 추가 중 ... [{i + 1}/{last}]'))
                        self.windowQ.put((ui_num['DB관리'], f'백테DB [{data[1]} ~ {data[2]}] 데이터 추가 완료'))
                    else:
                        self.windowQ.put((ui_num['DB관리'], '지정한 기간의 일자DB가 존재하지 않습니다.'))
                    con.close()
                else:
                    self.windowQ.put((ui_num['DB관리'], '일자DB가 존재하지 않습니다.'))

            elif '백테디비추가2' in data[0]:
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                    else:
                        DB_FILE = DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN
                else:
                    DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

                con = sqlite3.connect(DB_FILE)
                try:
                    df = get_pd().read_sql('SELECT * FROM moneytop', con)
                except:
                    self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
                    con.close()
                else:
                    if '주식' in data[0]:
                        if '키움증권' in self.dict_set['증권사']:
                            gubun     = '주식'
                            BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                            firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                        else:
                            gubun     = '해선'
                            BACK_FILE = DB_FUTURE_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN_BACK
                            firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                    else:
                        gubun     = '코인'
                        BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
                        firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

                    con2 = sqlite3.connect(BACK_FILE)
                    df['일자'] = df['index'].apply(lambda x: str(x)[:8])
                    day_list = df['일자'].unique()
                    file_list = os.listdir(DB_PATH)
                    file_day_list = [x.strip(firstname).strip('.db') for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                    if len(set(day_list) - set(file_day_list)) > 0:
                        self.windowQ.put((ui_num['DB관리'], '경고! 추가 후 당일 DB가 삭제됩니다.'))
                        self.windowQ.put((ui_num['DB관리'], '일자별 분리 후 재실행하십시오.'))
                        con2.close()
                        con.close()
                    else:
                        if 'stock' in firstname:
                            df = get_pd().read_sql('SELECT * FROM stockinfo', self.con4)
                            df.to_sql('stockinfo', con2, index=False, if_exists='replace', chunksize=1000)
                        elif 'future' in firstname:
                            df = get_pd().read_sql('SELECT * FROM futureinfo', self.con4)
                            df.to_sql('futureinfo', con2, index=False, if_exists='replace', chunksize=1000)

                        df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                        table_list = df['name'].to_list()
                        last = len(table_list)
                        for i, code in enumerate(table_list):
                            df = get_pd().read_sql(f'SELECT * FROM "{code}"', con)
                            if len(df) > 0:
                                df.to_sql(code, con2, index=False, if_exists='append', chunksize=1000)
                            self.windowQ.put((ui_num['DB관리'], f'백테DB [{code}] 데이터 추가 중 ... [{i + 1}/{last}]'))
                        self.windowQ.put((ui_num['DB관리'], f'{gubun} 당일DB 데이터, 백테DB로 추가 완료'))
                        con2.close()
                        con.close()

                        if os.path.isfile(DB_FILE):
                            os.remove(DB_FILE)
                            self.windowQ.put((ui_num['DB관리'], f'당일DB {DB_FILE} 삭제 완료'))

            elif '일자DB분리' in data[0]:
                if '주식' in data[0]:
                    if '키움증권' in self.dict_set['증권사']:
                        gubun   = '주식'
                        DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                    else:
                        gubun   = '해선'
                        DB_FILE = DB_FUTURE_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_MIN
                else:
                    gubun   = '코인'
                    DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

                con = sqlite3.connect(DB_FILE)
                try:
                    df = get_pd().read_sql('SELECT * FROM moneytop', con)
                except:
                    self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
                else:
                    df['일자'] = df['index'].apply(lambda x: int(str(x)[:8]))
                    day_list = df['일자'].unique()
                    df = get_pd().read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                    table_list = df['name'].to_list()
                    if table_list:
                        last = len(table_list)
                        for i, code in enumerate(table_list):
                            for day in day_list:
                                df = get_pd().read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{day}%"', con)
                                if len(df) > 0:
                                    if '주식' in data[0]:
                                        if '키움증권' in self.dict_set['증권사']:
                                            firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                                        else:
                                            firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
                                    else:
                                        firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                                    con2 = sqlite3.connect(f'{DB_PATH}/{firstname}{day}.db')
                                    df.to_sql(code, con2, index=False, if_exists='replace', chunksize=1000)
                                    con2.close()
                            self.windowQ.put((ui_num['DB관리'], f'당일DB [{code}] 데이터 분리 중 ... [{i + 1}/{last}]'))
                        self.windowQ.put((ui_num['DB관리'], f'{gubun} 당일DB 데이터, 일자DB로 분리 완료'))
                    else:
                        self.windowQ.put((ui_num['DB관리'], '일자DB에 데이터가 존재하지 않습니다.'))
                con.close()

            elif data == '프로세스종료':
                break

            self.windowQ.put((ui_num['DB관리'], 'DB업데이트완료'))
