import os
import sys
import time
import shutil
import sqlite3
import pandas as pd
from utility.setting import ui_num, DB_TRADELIST, DB_SETTING, DB_STRATEGY, DB_COIN_TICK, DB_PATH, DB_STOCK_BACK_TICK, \
    DB_COIN_BACK_TICK, DB_STOCK_TICK, DB_BACKTEST, DICT_SET, DB_STOCK_BACK_MIN, DB_COIN_BACK_MIN, DB_STOCK_MIN, \
    DB_COIN_MIN


class Query:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ  = qlist[0]
        self.queryQ   = qlist[2]
        self.con1     = sqlite3.connect(DB_SETTING)
        self.cur1     = self.con1.cursor()
        self.con2     = sqlite3.connect(DB_TRADELIST)
        self.cur2     = self.con2.cursor()
        self.con3     = sqlite3.connect(DB_STRATEGY)
        self.cur3     = self.con3.cursor()
        self.dict_set = DICT_SET
        self.Start()

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()

    def Start(self):
        while True:
            query = self.queryQ.get()
            if query[0] == '설정변경':
                self.dict_set = query[1]
            elif query[0] == '설정파일변경':
                self.con1.close()
                os.remove(query[2])
                shutil.copy(query[1], query[2])
                self.con1 = sqlite3.connect(DB_SETTING)
                self.cur1 = self.con1.cursor()
            elif query[0] == '설정디비':
                try:
                    if len(query) == 2:
                        self.cur1.execute(query[1])
                        self.con1.commit()
                    elif len(query) == 4:
                        query[1].to_sql(query[2], self.con1, if_exists=query[3], chunksize=1000)
                        if query[2] == 'codename':
                            con2 = sqlite3.connect(DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN)
                            df = pd.read_sql('SELECT * FROM codename', self.con1)
                            df.to_sql('codename', con2, index=False, if_exists='replace', chunksize=1000)
                            con2.close()
                except Exception as e:
                    self.windowQ.put((ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - Query 설정디비 {e}'))
            elif query[0] == '거래디비':
                try:
                    if len(query) == 2:
                        self.cur2.execute(query[1])
                        self.con2.commit()
                    elif len(query) == 4:
                        query[1].to_sql(query[2], self.con2, if_exists=query[3], chunksize=1000)
                except Exception as e:
                    ui_text = 'S로그텍스트' if 's_' in query[2] else 'C로그텍스트'
                    self.windowQ.put((ui_num[ui_text], f'시스템 명령 오류 알림 - Query 거래디비 {e}'))
            elif query[0] == '전략디비':
                try:
                    if len(query) == 2:
                        self.cur3.execute(query[1])
                        self.con3.commit()
                    elif len(query) == 4:
                        query[1].to_sql(query[2], self.con3, if_exists=query[3], chunksize=1000)
                except Exception as e:
                    self.windowQ.put((ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - Query 전략디비 {e}'))
            elif query[0] == '백테디비':
                try:
                    con = sqlite3.connect(DB_BACKTEST)
                    cur = con.cursor()
                    cur.execute(query[1])
                    con.commit()
                    con.close()
                except Exception as e:
                    self.windowQ.put((ui_num['S로그텍스트'], f'시스템 명령 오류 알림 - Query 백테디비 {e}'))
            elif '백테DB지정일자삭제' in query[0]:
                if '주식' in query[0]:
                    BACK_FILE = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
                else:
                    BACK_FILE = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
                con = sqlite3.connect(BACK_FILE)
                cur = con.cursor()
                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                last = len(table_list)
                for i, code in enumerate(table_list):
                    query_del = f"DELETE FROM '{code}' WHERE `index` LIKE '{query[1]}%'"
                    cur.execute(query_del)
                    self.windowQ.put((ui_num['DB관리'], f'백테DB {code} 지정일자 데이터 삭제 완료 [{i + 1}/{last}]'))
                con.commit()
                con.close()
                self.windowQ.put((ui_num['DB관리'], '백테DB 지정일자 데이터 삭제 완료'))
            elif '일자DB지정일자삭제' in query[0]:
                if '주식' in query[0]:
                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                else:
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                file_name = f'{DB_PATH}/{firstname}' + query[1] + '.db'
                if os.path.isfile(file_name):
                    os.remove(file_name)
                    self.windowQ.put((ui_num['DB관리'], f'{file_name} 삭제 완료'))
                else:
                    self.windowQ.put((ui_num['DB관리'], '해당 날짜에 데이터가 존재하지 않습니다.'))
            elif '일자DB지정시간이후삭제' in query[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in query[0]:
                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                else:
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                last = len(file_list)
                if last == 0:
                    self.windowQ.put((ui_num['DB관리'], '날짜별 데이터가 존재하지 않습니다.'))
                else:
                    for i, db_name in enumerate(file_list):
                        con = sqlite3.connect(f'{DB_PATH}/{db_name}')
                        cur = con.cursor()
                        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                        table_list = df['name'].to_list()
                        df = pd.read_sql('SELECT * FROM moneytop', con)
                        df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                        df = df[df['시간'] <= int(query[1])]
                        df.drop(columns=['시간'], inplace=True)
                        df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
                        mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
                        for code in table_list:
                            if code in mtlist:
                                df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                                df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                                df = df[df['시간'] <= int(query[1])]
                                df.drop(columns=['시간'], inplace=True)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='replace', chunksize=1000)
                                else:
                                    cur.execute(f'DROP TABLE "{code}"')
                            elif code != 'moneytop':
                                cur.execute(f'DROP TABLE "{code}"')
                        cur.execute('VACUUM;')
                        con.close()
                        self.windowQ.put((ui_num['DB관리'], f'{db_name} 데이터 갱신 완료 [{i + 1}/{last}]'))
                    self.windowQ.put((ui_num['DB관리'], '지정시간 이후 데이터 삭제 완료'))
            elif '당일데이터지정시간이후삭제' in query[0]:
                try:
                    if '주식' in query[0]:
                        DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                    else:
                        DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN
                    con = sqlite3.connect(DB_FILE)
                    cur = con.cursor()
                except:
                    self.windowQ.put((ui_num['DB관리'], '데이터가 존재하지 않습니다.'))
                else:
                    df = pd.read_sql('SELECT * FROM moneytop', con)
                    df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                    df = df[df['시간'] <= int(query[1])]
                    df.drop(columns=['시간'], inplace=True)
                    df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
                    mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
                    df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                    table_list = df['name'].to_list()
                    if '코인' in query[0]:
                        if 'dist' in table_list:
                            table_list.remove('dist')
                        if 'dist_chk' in table_list:
                            table_list.remove('dist_chk')
                        if 'sqlite_sequence' in table_list:
                            table_list.remove('sqlite_sequence')
                        if 'temp' in table_list:
                            table_list.remove('temp')
                    last = len(table_list)
                    if last > 0:
                        for i, code in enumerate(table_list):
                            if code in mtlist:
                                df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                                df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                                df = df[df['시간'] <= int(query[1])]
                                df.drop(columns=['시간'], inplace=True)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='replace', chunksize=1000)
                                else:
                                    cur.execute(f'DROP TABLE "{code}"')
                            elif code != 'moneytop':
                                cur.execute(f'DROP TABLE "{code}"')
                            self.windowQ.put((ui_num['DB관리'], f'{code} 데이터 갱신 완료 [{i + 1}/{last}]'))
                        cur.execute('VACUUM;')
                    con.close()
                    self.windowQ.put((ui_num['DB관리'], '지정시간 이후 데이터 삭제 완료'))
            elif query[0] == '주식체결시간조정':
                try:
                    con = sqlite3.connect(DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN)
                    cur = con.cursor()
                except:
                    self.windowQ.put((ui_num['DB관리'], '데이터가 존재하지 않습니다.'))
                else:
                    df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                    table_list = df['name'].to_list()
                    last = len(table_list)
                    if last > 0:
                        for i, code in enumerate(table_list):
                            df = pd.read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{query[1]}%"', con)
                            cur.execute(f'DELETE FROM "{code}" WHERE "index" LIKE "{query[1]}%"')
                            con.commit()
                            if self.dict_set['주식타임프레임']:
                                df['index'] = df['index'] - 10000
                            else:
                                df['index'] = df['index'] - 100
                            df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                            self.windowQ.put((ui_num['DB관리'], f'{code} 데이터 갱신 완료 [{i + 1}/{last}]'))
                    con.close()
                    self.windowQ.put((ui_num['DB관리'], '체결시간 조정 완료'))
            elif '백테DB생성' in query[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in query[0]:
                    BACK_FILE = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                else:
                    BACK_FILE = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                if len(file_list) == 0:
                    self.windowQ.put((ui_num['DB관리'], '날짜별 데이터가 존재하지 않습니다.'))
                else:
                    if os.path.isfile(BACK_FILE):
                        os.remove(BACK_FILE)
                        self.windowQ.put((ui_num['DB관리'], f'{BACK_FILE} 삭제 완료'))
                    con = sqlite3.connect(BACK_FILE)
                    if 'stock' in firstname:
                        df = pd.read_sql('SELECT * FROM codename', self.con1)
                        df.to_sql('codename', con, index=False, if_exists='replace', chunksize=1000)
                    file_list = [x for x in file_list if int(query[1]) <= int(x.split(firstname)[1].replace('.db', '')) <= int(query[2])]
                    if file_list:
                        for db_name in file_list:
                            con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                            table_list = df['name'].to_list()
                            for code in table_list:
                                df = pd.read_sql(f'SELECT * FROM "{code}"', con2)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                            con2.close()
                            self.windowQ.put((ui_num['DB관리'], f'{db_name} 데이터 추가 완료'))
                        self.windowQ.put((ui_num['DB관리'], f'{BACK_FILE} 생성 완료'))
                    else:
                        self.windowQ.put((ui_num['DB관리'], '지정한 기간의 일자별 디비가 존재하지 않습니다.'))
                    con.close()
            elif '백테디비추가1' in query[0]:
                file_list = os.listdir(DB_PATH)
                if '주식' in query[0]:
                    BACK_FILE = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                else:
                    BACK_FILE = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                if len(file_list) == 0:
                    self.windowQ.put((ui_num['DB관리'], '날짜별 데이터가 존재하지 않습니다.'))
                else:
                    con = sqlite3.connect(BACK_FILE)
                    if firstname in ('stock_tick_', 'stock_min_'):
                        df = pd.read_sql('SELECT * FROM codename', self.con1)
                        df.to_sql('codename', con, index=False, if_exists='replace', chunksize=1000)
                    for db_name in file_list:
                        date = int(db_name.split(firstname)[1].replace('.db', ''))
                        if int(query[1]) <= date <= int(query[2]):
                            con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                            table_list = df['name'].to_list()
                            for code in table_list:
                                df = pd.read_sql(f'SELECT * FROM "{code}"', con2)
                                if len(df) > 0:
                                    df.to_sql(code, con, index=False, if_exists='append', chunksize=1000)
                            con2.close()
                            self.windowQ.put((ui_num['DB관리'], f'{db_name} 데이터 추가 완료'))
                    con.close()
                    self.windowQ.put((ui_num['DB관리'], f'{query[1]} ~ {query[2]} 추가 완료'))
            elif '백테디비추가2' in query[0]:
                if '주식' in query[0]:
                    DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                else:
                    DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN
                con = sqlite3.connect(DB_FILE)
                try:
                    df = pd.read_sql('SELECT * FROM moneytop', con)
                except:
                    self.windowQ.put((ui_num['DB관리'], '저장한 데이터가 존재하지 않습니다.'))
                else:
                    if '주식' in query[0]:
                        gubun     = '주식'
                        BACK_FILE = DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN
                        firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                    else:
                        gubun     = '코인'
                        BACK_FILE = DB_COIN_BACK_TICK if self.dict_set['코인타임프레임'] else DB_COIN_BACK_MIN
                        firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                    con2 = sqlite3.connect(BACK_FILE)
                    df['일자'] = df['index'].apply(lambda x: str(x)[:8])
                    day_list = list(set(df['일자'].to_list()))
                    file_list = os.listdir(DB_PATH)
                    file_day_list = [x.strip(firstname).strip('.db') for x in file_list if firstname in x and '.db' in x and 'back' not in x]
                    if len(list(set(day_list) - set(file_day_list))) > 0:
                        self.windowQ.put((ui_num['DB관리'], '경고! 추가 후 당일 DB가 삭제됩니다.'))
                        self.windowQ.put((ui_num['DB관리'], '날짜별 분리 후 재실행하십시오.'))
                        con2.close()
                        con.close()
                    else:
                        if firstname in ('stock_tick_', 'stock_min_'):
                            df = pd.read_sql('SELECT * FROM codename', self.con1)
                            df.to_sql('codename', con2, index=False, if_exists='replace', chunksize=1000)
                        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                        table_list = df['name'].to_list()
                        if '코인' in query[0]:
                            if 'dist' in table_list:
                                table_list.remove('dist')
                            if 'dist_chk' in table_list:
                                table_list.remove('dist_chk')
                            if 'sqlite_sequence' in table_list:
                                table_list.remove('sqlite_sequence')
                            if 'temp' in table_list:
                                table_list.remove('temp')
                        last = len(table_list)
                        for i, code in enumerate(table_list):
                            df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                            if len(df) > 0:
                                df.to_sql(code, con2, index=False, if_exists='append', chunksize=1000)
                            self.windowQ.put((ui_num['DB관리'], f'{code} 데이터 추가 완료 [{i + 1}/{last}]'))
                        self.windowQ.put((ui_num['DB관리'], f'{gubun} 당일 데이터 백테디비로 추가 완료'))
                        con2.close()
                        con.close()
                        if os.path.isfile(DB_FILE):
                            os.remove(DB_FILE)
                            self.windowQ.put((ui_num['DB관리'], f'{DB_FILE} 삭제 완료'))
            elif '일자DB분리' in query[0]:
                if '주식' in query[0]:
                    gubun   = '주식'
                    DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
                else:
                    gubun   = '코인'
                    DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN
                con = sqlite3.connect(DB_FILE)
                try:
                    df = pd.read_sql('SELECT * FROM moneytop', con)
                except:
                    self.windowQ.put((ui_num['DB관리'], '당일 데이터가 존재하지 않습니다.'))
                else:
                    df['일자'] = df['index'].apply(lambda x: int(str(x)[:8]))
                    day_list = list(set(df['일자'].to_list()))
                    df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                    table_list = df['name'].to_list()
                    if '코인' in query[0]:
                        if 'dist' in table_list:
                            table_list.remove('dist')
                        if 'dist_chk' in table_list:
                            table_list.remove('dist_chk')
                        if 'sqlite_sequence' in table_list:
                            table_list.remove('sqlite_sequence')
                        if 'temp' in table_list:
                            table_list.remove('temp')
                    last = len(table_list)
                    for i, code in enumerate(table_list):
                        for day in day_list:
                            df = pd.read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{day}%"', con)
                            if len(df) > 0:
                                if '주식' in query[0]:
                                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                                else:
                                    firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'
                                con2 = sqlite3.connect(f'{DB_PATH}/{firstname}{day}.db')
                                df.to_sql(code, con2, index=False, if_exists='replace', chunksize=1000)
                                con2.close()
                        self.windowQ.put((ui_num['DB관리'], f'{code} 데이터 분리 완료 [{i + 1}/{last}]'))
                    con.close()
                    self.windowQ.put((ui_num['DB관리'], f'{gubun} 날짜별 DB 생성 완료'))
            elif query == '프로세스종료':
                break
            self.windowQ.put((ui_num['DB관리'], 'DB업데이트완료'))

        time.sleep(1)
        sys.exit()
