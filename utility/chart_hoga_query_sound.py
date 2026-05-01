
import os
import time
import talib
import shutil
import sqlite3
import pyttsx3
import numpy as np
import pandas as pd
from copy import deepcopy
from threading import Lock
from traceback import format_exc
from trade.formula_manager import FormulaManager, get_formula_data
from utility.static import timedelta_sec, str_ymdhms, dt_ymdhms, add_rolling_data, dt_ymdhm, str_ymdhm, thread_decorator
from utility.setting_base import ui_num, DB_TRADELIST, DB_PATH, DB_STOCK_TICK_BACK, DB_COIN_TICK_BACK, \
    DB_BACKTEST, DB_COIN_MIN_BACK, DB_STOCK_MIN_BACK, DB_CODE_INFO, DB_FUTURE_OS_MIN_BACK, DB_FUTURE_OS_TICK_BACK, \
    list_stock_min, list_coin_min, DB_SETTING, DB_STRATEGY, DB_STOCK_TICK, DB_STOCK_MIN, DB_FUTURE_OS_TICK, DB_FUTURE_OS_MIN, \
    DB_COIN_TICK, DB_COIN_MIN, list_stock_tick, list_coin_tick, columns_hj


class ChartHogaQuerySound:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, wdzservQ
           0        1       2      3       4      5      6      7       8         9         10     11      12
        """
        self.windowQ   = qlist[0]
        self.soundQ    = qlist[1]
        self.queryQ    = qlist[2]
        self.chartQ    = qlist[4]
        self.hogaQ     = qlist[5]
        self.dict_set  = dict_set
        self.dict_name = {}

        self.arry_kosp = None
        self.arry_kosd = None

        con = sqlite3.connect(DB_CODE_INFO)
        df = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
        self.dict_name.update(df['종목명'].to_dict())
        df = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
        self.dict_name.update(df['종목명'].to_dict())
        con.close()

        self.factor_index = {
            '주식분봉종가': list_stock_min.index('현재가'),
            '주식분봉시가': list_stock_min.index('분봉시가'),
            '주식분봉고가': list_stock_min.index('분봉고가'),
            '주식분봉저가': list_stock_min.index('분봉저가'),
            '주식거래대금': list_stock_min.index('분당거래대금'),
            '그외분봉종가': list_coin_min.index('현재가'),
            '그외분봉시가': list_coin_min.index('분봉시가'),
            '그외분봉고가': list_coin_min.index('분봉고가'),
            '그외분봉저가': list_coin_min.index('분봉저가'),
            '그외거래대금': list_coin_min.index('분당거래대금')
        }

        self.text2speak = pyttsx3.init()
        self.text2speak.setProperty('rate', 170)
        self.text2speak.setProperty('volume', 1.0)
        self.tts_lock = Lock()

        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()
        self.con2 = sqlite3.connect(DB_TRADELIST)
        self.cur2 = self.con2.cursor()
        self.con3 = sqlite3.connect(DB_STRATEGY)
        self.cur3 = self.con3.cursor()
        self.con4 = sqlite3.connect(DB_CODE_INFO)

        self.gubun     = None
        self.hoga_name = None
        self.dict_hj   = None
        self.dict_hc   = None
        self.dict_hg   = None
        self.InitHoga('S')
        self.fi = {
            '현재가': list_stock_tick.index('현재가'),
            '시가': list_stock_tick.index('시가'),
            '고가': list_stock_tick.index('고가'),
            '저가': list_stock_tick.index('저가'),
            '등락율': list_stock_tick.index('등락율'),
            '시가총액': list_stock_tick.index('시가총액'),
            'VI가격': list_stock_tick.index('VI가격'),

            '주식틱봉호가시작': list_stock_tick.index('매도호가5'),
            '주식틱봉호가종료': list_stock_tick.index('매수호가5') + 1,
            '주식틱봉잔량시작': list_stock_tick.index('매도잔량5'),
            '주식틱봉잔량종료': list_stock_tick.index('매수잔량5') + 1,
            '주식틱봉매도총잔': list_stock_tick.index('매도총잔량'),
            '주식틱봉매수총잔': list_stock_tick.index('매수총잔량'),

            '주식분봉호가시작': list_stock_min.index('매도호가5'),
            '주식분봉호가종료': list_stock_min.index('매수호가5') + 1,
            '주식분봉잔량시작': list_stock_min.index('매도잔량5'),
            '주식분봉잔량종료': list_stock_min.index('매수잔량5') + 1,
            '주식분봉매도총잔': list_stock_min.index('매도총잔량'),
            '주식분봉매수총잔': list_stock_min.index('매수총잔량'),

            '그외틱봉호가시작': list_coin_tick.index('매도호가5'),
            '그외틱봉호가종료': list_coin_tick.index('매수호가5') + 1,
            '그외틱봉잔량시작': list_coin_tick.index('매도잔량5'),
            '그외틱봉잔량종료': list_coin_tick.index('매수잔량5') + 1,
            '그외틱봉매도총잔': list_coin_tick.index('매도총잔량'),
            '그외틱봉매수총잔': list_coin_tick.index('매수총잔량'),

            '그외분봉호가시작': list_coin_min.index('매도호가5'),
            '그외분봉호가종료': list_coin_min.index('매수호가5') + 1,
            '그외분봉잔량시작': list_coin_min.index('매도잔량5'),
            '그외분봉잔량종료': list_coin_min.index('매수잔량5') + 1,
            '그외분봉매도총잔': list_coin_min.index('매도총잔량'),
            '그외분봉매수총잔': list_coin_min.index('매수총잔량')
        }

        self.MainLoop()

    def __del__(self):
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    def MainLoop(self):
        while True:
            try:
                if not self.hogaQ.empty():
                    data = self.hogaQ.get()
                    if data[0] == '설정변경':
                        self.dict_set = data[1]
                    elif len(data) == 8:
                        self.UpdateHogaJongmok(data)
                    elif len(data) == 2:
                        self.UpdateChegeolcount(data)
                    elif len(data) == 4:
                        self.UpdateHogaForChart(data)
                    else:
                        if self.hoga_name == data[0]:
                            self.UpdateHogajalryang(data)
                            if self.gubun is not None:
                                if self.dict_hj is not None:
                                    self.windowQ.put((ui_num[f'{self.gubun}호가종목'], pd.DataFrame([self.dict_hj])))
                                if self.dict_hc is not None:
                                    self.windowQ.put((ui_num[f'{self.gubun}호가체결'], pd.DataFrame(self.dict_hc)))
                                if self.dict_hg is not None:
                                    self.windowQ.put((ui_num[f'{self.gubun}호가잔량'], pd.DataFrame(self.dict_hg)))

                if not self.queryQ.empty():
                    data = self.queryQ.get()
                    if data[0] == '설정파일변경':
                        self.SettingsChange(data)
                    elif data[0] == '설정디비':
                        self.ExecuteQuery(data, self.con1, self.cur1)
                    elif data[0] == '거래디비':
                        self.ExecuteQuery(data, self.con2, self.cur2)
                    elif data[0] == '전략디비':
                        self.ExecuteQuery(data, self.con3, self.cur3)
                    elif data[0] == '종목디비':
                        self.DataFrameToSql(data, self.con4)
                    elif data[0] == '백테디비':
                        self.BacktestQuery(data)
                    elif '백테DB지정일자삭제' in data[0]:
                        self.DBBackDayDelete(data)
                    elif '일자DB지정일자삭제' in data[0]:
                        self.DBDayDayDelete(data)
                    elif '일자DB지정시간이후삭제' in data[0]:
                        self.DBDayTimeDelete(data)
                    elif '당일데이터지정시간이후삭제' in data[0]:
                        self.DBNowTimeDelete(data)
                    elif data[0] == '주식체결시간조정':
                        self.DBNowTimeChange(data)
                    elif '백테DB생성' in data[0]:
                        self.DBBackCreate(data)
                    elif '백테디비추가1' in data[0]:
                        self.DBBackAreaAdd(data)
                    elif '백테디비추가2' in data[0]:
                        self.DBBackAdd(data)
                    elif '일자DB분리' in data[0]:
                        self.DBNowDayDivide(data)
                    elif data == '프로세스종료':
                        break
                    self.windowQ.put((ui_num['DB관리'], 'DB업데이트완료'))

                if not self.chartQ.empty():
                    data = self.chartQ.get()
                    if data[0] == '설정변경':
                        self.dict_set = data[1]
                    elif data[0] == '그래프비교':
                        self.GraphComparison(data[1])
                    elif len(data) >= 7:
                        self.UpdateChart(data)

                if not self.soundQ.empty():
                    data = self.soundQ.get()
                    self.TextToSpeak(data)

                time.sleep(0.01)
            except:
                self.windowQ.put((ui_num['시스템로그'], format_exc()))

    def InitHoga(self, gubun):
        self.dict_hj = {
            '종목명': '', '현재가': 0., '등락율': 0., '시가총액': 0, 'UVI': 0., '시가': 0., '고가': 0., '저가': 0.
        }
        self.dict_hc = {
            '체결수량': [0.] * 12, '체결강도': [0.] * 12
        }
        self.dict_hg = {
            '잔량': [0.] * 12, '호가': [0.] * 12
        }
        self.windowQ.put((ui_num[f'{gubun}호가종목'], pd.DataFrame([self.dict_hj])))
        self.windowQ.put((ui_num[f'{gubun}호가체결'], pd.DataFrame(self.dict_hc)))
        self.windowQ.put((ui_num[f'{gubun}호가잔량'], pd.DataFrame(self.dict_hg)))
        self.hoga_name = ''

    def UpdateHogaJongmok(self, data):
        종목명, 현재가, 등락율, 시가총액, UVI, 시가, 고가, 저가 = data
        self.gubun = 'C' if 'KRW' in 종목명 or 'USDT' in 종목명 else 'S'
        if self.hoga_name != 종목명:
            self.InitHoga(self.gubun)
            self.hoga_name = 종목명

        self.dict_hj = {
            '종목명': 종목명, '현재가': 현재가, '등락율': 등락율, '시가총액': 시가총액,
            'UVI': UVI, '시가': 시가, '고가': 고가, '저가': 저가
        }

    def UpdateChegeolcount(self, data):
        v, ch = data
        if 'KRW' in self.hoga_name or 'USDT' in self.hoga_name:
            if v > 0:
                tbc = round(self.dict_hc['체결수량'][0] + v, 8)
                tsc = round(self.dict_hc['체결수량'][11], 8)
            else:
                tbc = round(self.dict_hc['체결수량'][0], 8)
                tsc = round(self.dict_hc['체결수량'][11] + abs(v), 8)
        else:
            if v > 0:
                tbc = self.dict_hc['체결수량'][0] + v
                tsc = self.dict_hc['체결수량'][11]
            else:
                tbc = self.dict_hc['체결수량'][0]
                tsc = self.dict_hc['체결수량'][11] + abs(v)

        hch = self.dict_hc['체결강도'][0]
        lch = self.dict_hc['체결강도'][11]

        if hch < ch:
            hch = ch
        if lch == 0 or lch > ch:
            lch = ch

        self.dict_hc['체결수량'] = [tbc, v] + self.dict_hc['체결수량'][1:10] + [tsc]
        self.dict_hc['체결강도'] = [hch, ch] + self.dict_hc['체결강도'][1:10] + [lch]

    def UpdateHogajalryang(self, data):
        jr = [data[1]] + list(data[13:23]) + [data[2]]
        if 'KRW' in self.hoga_name or 'USDT' in self.hoga_name or '해외선물' in self.dict_set['증권사']:
            hg = [self.dict_hj['고가']] + list(data[3:13]) + [self.dict_hj['저가']]
        else:
            hg = [data[23]] + [round(x) for x in data[3:13]] + [data[24]]

        self.dict_hg['잔량'] = jr
        self.dict_hg['호가'] = hg

    def UpdateHogaForChart(self, data):
        cmd, code, name, index = data
        searchdate = index[:8]
        gubun = 'C' if 'KRW' in code or 'USDT' in code else 'S'
        index = int(index)
        self.InitHoga(gubun)

        if gubun == 'C':
            db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db' if self.dict_set['코인타임프레임'] else f'{DB_PATH}/coin_min_{searchdate}.db'
            db_name2 = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
        else:
            if '키움증권' in self.dict_set['증권사']:
                db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db' if self.dict_set['주식타임프레임'] else f'{DB_PATH}/stock_min_{searchdate}.db'
                db_name2 = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
            else:
                db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db' if self.dict_set['주식타임프레임'] else f'{DB_PATH}/future_min_{searchdate}.db'
                db_name2 = DB_FUTURE_OS_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN_BACK

        if cmd == '이전호가정보요청':
            query = f"SELECT * FROM '{code}' WHERE `index` < {index} ORDER BY `index` DESC LIMIT 1"
        elif cmd == '다음호가정보요청':
            query = f"SELECT * FROM '{code}' WHERE `index` > {index} ORDER BY `index` LIMIT 1"
        else:
            query = f"SELECT * FROM '{code}' WHERE `index` = {index}"

        df = None
        try:
            if os.path.isfile(db_name1):
                con = sqlite3.connect(db_name1)
                df = pd.read_sql(query, con)
                con.close()
            elif os.path.isfile(db_name2):
                con = sqlite3.connect(db_name2)
                df = pd.read_sql(query, con)
                con.close()
        except:
            pass

        if df is not None and len(df) > 0:
            data = list(df.iloc[0])
            if gubun == 'C' or '해외선물' in self.dict_set['증권사']:
                hj = [
                    name, data[self.fi['현재가']], data[self.fi['등락율']], 0, 0,
                    data[self.fi['시가']], data[self.fi['고가']], data[self.fi['저가']]
                ]

                if (gubun == 'C' and self.dict_set['코인타임프레임']) or \
                        ('해외선물' in self.dict_set['증권사'] and self.dict_set['주식타임프레임']):
                    jr = [data[self.fi['그외틱봉매도총잔']]] + data[self.fi['그외틱봉잔량시작']:self.fi['그외틱봉잔량종료']] + [data[self.fi['그외틱봉매수총잔']]]
                    hg = [data[self.fi['고가']]]  + data[self.fi['그외틱봉호가시작']:self.fi['그외틱봉호가종료']] + [data[self.fi['저가']]]
                else:
                    jr = [data[self.fi['그외분봉매도총잔']]] + data[self.fi['그외분봉잔량시작']:self.fi['그외분봉잔량종료']] + [data[self.fi['그외분봉매수총잔']]]
                    hg = [data[self.fi['고가']]]  + data[self.fi['그외분봉호가시작']:self.fi['그외분봉호가종료']] + [data[self.fi['저가']]]
            else:
                hj = [
                    name, data[self.fi['현재가']], data[self.fi['등락율']], data[self.fi['시가총액']], data[self.fi['VI가격']],
                    data[self.fi['시가']], data[self.fi['고가']], data[self.fi['저가']]
                ]

                if self.dict_set['주식타임프레임']:
                    jr = [data[self.fi['주식틱봉매도총잔']]] + data[self.fi['주식틱봉잔량시작']:self.fi['주식틱봉잔량종료']] + [data[self.fi['주식틱봉매수총잔']]]
                    hg = [data[self.fi['고가']]] + data[self.fi['주식틱봉호가시작']:self.fi['주식틱봉호가종료']] + [data[self.fi['저가']]]
                else:
                    jr = [data[self.fi['주식분봉매도총잔']]] + data[self.fi['주식분봉잔량시작']:self.fi['주식분봉잔량종료']] + [data[self.fi['주식분봉매수총잔']]]
                    hg = [data[self.fi['고가']]] + data[self.fi['주식분봉호가시작']:self.fi['주식분봉호가종료']] + [data[self.fi['저가']]]

            df_hj = pd.DataFrame([hj], columns=columns_hj)
            df_hg = pd.DataFrame({'잔량': jr, '호가': hg})
            self.windowQ.put((ui_num[f'{gubun}호가종목'], df_hj, str(int(data[0]))))
            self.windowQ.put((ui_num[f'{gubun}호가잔량'], df_hg))

    def SettingsChange(self, data):
        self.con1.close()
        os.remove(data[2])
        shutil.copy(data[1], data[2])
        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()

    def ExecuteQuery(self, data, con, cur):
        if len(data) == 2:
            cur.execute(data[1])
            con.commit()
        elif len(data) == 3:
            cur.execute(data[1], data[2])
            con.commit()
        elif len(data) == 4:
            data[1].to_sql(data[2], con, if_exists=data[3], chunksize=1000)

    def DataFrameToSql(self, data, con):
        if len(data) == 4:
            data[1].to_sql(data[2], con, if_exists=data[3], chunksize=1000)

    def BacktestQuery(self, data):
        con = sqlite3.connect(DB_BACKTEST)
        cur = con.cursor()
        cur.execute(data[1])
        con.commit()
        con.close()

    def DBBackDayDelete(self, data):
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
            else:
                BACK_FILE = DB_FUTURE_OS_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN_BACK
        else:
            BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK

        con = sqlite3.connect(BACK_FILE)
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
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

    def DBDayDayDelete(self, data):
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

    def DBDayTimeDelete(self, data):
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
                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                df = pd.read_sql('SELECT * FROM moneytop', con)
                df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                df = df[df['시간'] <= int(data[1])]
                df.drop(columns=['시간'], inplace=True)
                df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
                mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
                for code in table_list:
                    if code in mtlist:
                        df = pd.read_sql(f'SELECT * FROM "{code}"', con)
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

    def DBNowTimeDelete(self, data):
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
            else:
                DB_FILE = DB_FUTURE_OS_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN
        else:
            DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except:
            self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        else:
            cur = con.cursor()
            df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
            df = df[df['시간'] <= int(data[1])]
            df.drop(columns=['시간'], inplace=True)
            df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=1000)
            mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))

            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
            table_list = df['name'].to_list()
            if table_list:
                last = len(table_list)
                for i, code in enumerate(table_list):
                    if code in mtlist:
                        df = pd.read_sql(f'SELECT * FROM "{code}"', con)
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

    def DBNowTimeChange(self, data):
        if '키움증권' in self.dict_set['증권사']:
            DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
        else:
            DB_FILE = DB_FUTURE_OS_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN

        con = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()
        if table_list:
            cur = con.cursor()
            last = len(table_list)
            for i, code in enumerate(table_list):
                df = pd.read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{data[1]}%"', con)
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

    def DBBackCreate(self, data):
        file_list = os.listdir(DB_PATH)
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
            else:
                BACK_FILE = DB_FUTURE_OS_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN_BACK
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
                df = pd.read_sql('SELECT * FROM stockinfo', self.con4)
                df.to_sql('stockinfo', con, index=False, if_exists='replace', chunksize=1000)
            elif 'future' in firstname:
                df = pd.read_sql('SELECT * FROM futureinfo', self.con4)
                df.to_sql('futureinfo', con, index=False, if_exists='replace', chunksize=1000)

            file_list = [x for x in file_list if
                         int(data[1]) <= int(x.split(firstname)[1].replace('.db', '')) <= int(data[2])]
            if file_list:
                last = len(file_list)
                for i, db_name in enumerate(file_list):
                    con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                    df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                    table_list = df['name'].to_list()
                    for code in table_list:
                        df = pd.read_sql(f'SELECT * FROM "{code}"', con2)
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

    def DBBackAreaAdd(self, data):
        file_list = os.listdir(DB_PATH)
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
            else:
                BACK_FILE = DB_FUTURE_OS_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN_BACK
                firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
        else:
            BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
            firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

        file_list = [x for x in file_list if firstname in x and '.db' in x and 'back' not in x]
        if file_list:
            con = sqlite3.connect(BACK_FILE)
            if 'stock' in firstname:
                df = pd.read_sql('SELECT * FROM stockinfo', self.con4)
                df.to_sql('stockinfo', con, index=False, if_exists='replace', chunksize=1000)
            elif 'future' in firstname:
                df = pd.read_sql('SELECT * FROM futureinfo', self.con4)
                df.to_sql('futureinfo', con, index=False, if_exists='replace', chunksize=1000)

            file_list = [x for x in file_list if
                         int(data[1]) <= int(x.split(firstname)[1].replace('.db', '')) <= int(data[2])]
            if file_list:
                last = len(file_list)
                for i, db_name in enumerate(file_list):
                    con2 = sqlite3.connect(f'{DB_PATH}/{db_name}')
                    df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con2)
                    table_list = df['name'].to_list()
                    for code in table_list:
                        df = pd.read_sql(f'SELECT * FROM "{code}"', con2)
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

    def DBBackAdd(self, data):
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
            else:
                DB_FILE = DB_FUTURE_OS_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN
        else:
            DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except:
            self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
            con.close()
        else:
            if '주식' in data[0]:
                if '키움증권' in self.dict_set['증권사']:
                    gubun = '주식'
                    BACK_FILE = DB_STOCK_TICK_BACK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN_BACK
                    firstname = 'stock_tick_' if self.dict_set['주식타임프레임'] else 'stock_min_'
                else:
                    gubun = '해선'
                    BACK_FILE = DB_FUTURE_OS_TICK_BACK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN_BACK
                    firstname = 'future_tick_' if self.dict_set['주식타임프레임'] else 'future_min_'
            else:
                gubun = '코인'
                BACK_FILE = DB_COIN_TICK_BACK if self.dict_set['코인타임프레임'] else DB_COIN_MIN_BACK
                firstname = 'coin_tick_' if self.dict_set['코인타임프레임'] else 'coin_min_'

            con2 = sqlite3.connect(BACK_FILE)
            df['일자'] = df['index'].apply(lambda x: str(x)[:8])
            day_list = df['일자'].unique()
            file_list = os.listdir(DB_PATH)
            file_day_list = [x.strip(firstname).strip('.db') for x in file_list if
                             firstname in x and '.db' in x and 'back' not in x]
            if len(set(day_list) - set(file_day_list)) > 0:
                self.windowQ.put((ui_num['DB관리'], '경고! 추가 후 당일 DB가 삭제됩니다.'))
                self.windowQ.put((ui_num['DB관리'], '일자별 분리 후 재실행하십시오.'))
                con2.close()
                con.close()
            else:
                if 'stock' in firstname:
                    df = pd.read_sql('SELECT * FROM stockinfo', self.con4)
                    df.to_sql('stockinfo', con2, index=False, if_exists='replace', chunksize=1000)
                elif 'future' in firstname:
                    df = pd.read_sql('SELECT * FROM futureinfo', self.con4)
                    df.to_sql('futureinfo', con2, index=False, if_exists='replace', chunksize=1000)

                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                last = len(table_list)
                for i, code in enumerate(table_list):
                    df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                    if len(df) > 0:
                        df.to_sql(code, con2, index=False, if_exists='append', chunksize=1000)
                    self.windowQ.put((ui_num['DB관리'], f'백테DB [{code}] 데이터 추가 중 ... [{i + 1}/{last}]'))
                self.windowQ.put((ui_num['DB관리'], f'{gubun} 당일DB 데이터, 백테DB로 추가 완료'))
                con2.close()
                con.close()

                if os.path.isfile(DB_FILE):
                    os.remove(DB_FILE)
                    self.windowQ.put((ui_num['DB관리'], f'당일DB {DB_FILE} 삭제 완료'))

    def DBNowDayDivide(self, data):
        if '주식' in data[0]:
            if '키움증권' in self.dict_set['증권사']:
                gubun = '주식'
                DB_FILE = DB_STOCK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_MIN
            else:
                gubun = '해선'
                DB_FILE = DB_FUTURE_OS_TICK if self.dict_set['주식타임프레임'] else DB_FUTURE_OS_MIN
        else:
            gubun = '코인'
            DB_FILE = DB_COIN_TICK if self.dict_set['코인타임프레임'] else DB_COIN_MIN

        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except:
            self.windowQ.put((ui_num['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        else:
            df['일자'] = df['index'].apply(lambda x: int(str(x)[:8]))
            day_list = df['일자'].unique()
            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
            table_list = df['name'].to_list()
            if table_list:
                last = len(table_list)
                for i, code in enumerate(table_list):
                    for day in day_list:
                        df = pd.read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{day}%"', con)
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

    @staticmethod
    def GraphComparison(backdetail_list):
        from matplotlib import pyplot as plt, font_manager
        plt.rcParams['figure.max_open_warning'] = 0
        plt.rcParams['font.family'] = font_manager.FontProperties(fname='C:/Windows/Fonts/malgun.ttf').get_name()
        plt.rcParams['axes.unicode_minus'] = False
        plt.rcParams['path.simplify'] = True
        plt.rcParams['path.snap'] = True
        plt.rcParams['figure.autolayout'] = True
        plt.rcParams['figure.constrained_layout.use'] = True

        plt.figure('그래프 비교', figsize=(12, 10))
        con = sqlite3.connect(DB_BACKTEST)
        for table in backdetail_list:
            df = pd.read_sql(f'SELECT `index`, `수익금` FROM {table}', con)
            df['index'] = df['index'].apply(lambda x: dt_ymdhms(x))
            df.set_index('index', inplace=True)
            df = df.resample('D').sum()
            df['수익금합계'] = df['수익금'].cumsum()
            plt.plot(df.index, df['수익금합계'], linewidth=1, label=table)
        con.close()
        plt.legend(loc='best')
        plt.tight_layout()
        plt.grid()
        plt.show()

    def UpdateChart(self, data):
        if len(data) == 7:
            coin, code, w_unit, searchdate, starttime, endtime, k = data
            detail, buytimes, cf1, cf2 = None, None, None, None
        elif len(data) == 9:
            coin, code, w_unit, searchdate, starttime, endtime, k = data[:7]
            if data[7].__class__ == list:
                detail, buytimes = data[7:]
                cf1, cf2 = None, None
            else:
                detail, buytimes = None, None
                cf1, cf2 = data[7:]
        else:
            coin, code, w_unit, searchdate, starttime, endtime, k, detail, buytimes, cf1, cf2 = data

        is_tick = False
        if coin:
            if 'KRW' in code: market = 3
            else:             market = 4
            if w_unit == '': w_unit = self.dict_set['코인평균값계산틱수']
            if starttime == '': starttime, endtime = '000000', '235000'
            if self.dict_set['코인타임프레임']:
                is_tick  = True
                db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db'
                db_name2 = DB_COIN_TICK_BACK
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                           f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
            else:
                db_name1 = f'{DB_PATH}/coin_min_{searchdate}.db'
                db_name2 = DB_COIN_MIN_BACK
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                           f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"
        else:
            if w_unit == '': w_unit = self.dict_set['주식평균값계산틱수']
            if '키움증권' in self.dict_set['증권사']:
                market = 1
                if self.dict_set['주식타임프레임']:
                    is_tick  = True
                    if starttime == '': starttime, endtime = '090000', '093000'
                    db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db'
                    db_name2 = DB_STOCK_TICK_BACK
                else:
                    if starttime == '': starttime, endtime = '090000', '152000'
                    db_name1 = f'{DB_PATH}/stock_min_{searchdate}.db'
                    db_name2 = DB_STOCK_MIN_BACK
            else:
                market = 2
                if self.dict_set['주식타임프레임']:
                    is_tick  = True
                    if starttime == '': starttime, endtime = '093000', '103000'
                    db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db'
                    db_name2 = DB_FUTURE_OS_TICK_BACK
                else:
                    if starttime == '': starttime, endtime = '090000', '160000'
                    db_name1 = f'{DB_PATH}/future_min_{searchdate}.db'
                    db_name2 = DB_FUTURE_OS_MIN_BACK

            if is_tick:
                query1 = f"SELECT * FROM '{code}' WHERE " \
                         f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                         f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
            else:
                query1 = f"SELECT * FROM '{code}' WHERE " \
                         f"`index` >= {int(searchdate) * 10000 + int(int(starttime) / 100)} and " \
                         f"`index` <= {int(searchdate) * 10000 + int(int(endtime) / 100)}"

        df = None
        query2 = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%'"
        try:
            if os.path.isfile(db_name1):
                con = sqlite3.connect(db_name1)
                df = pd.read_sql(query1 if starttime and endtime else query2, con)
                con.close()
            elif os.path.isfile(db_name2):
                con = sqlite3.connect(db_name2)
                df = pd.read_sql(query1 if starttime and endtime else query2, con)
                con.close()
        except:
            pass

        if df is None or df.empty:
            self.windowQ.put((ui_num['차트'], '차트오류', '', '', '', ''))
            return

        if cf1 is None:
            arry = add_rolling_data(df, market, is_tick, [w_unit])
        else:
            arry = add_rolling_data(df, market, is_tick, [w_unit], cf1=cf1, cf2=cf2)

        buy_index  = []
        sell_index = []

        arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))
        if market in (2, 4):
            arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))

        indices = arry[:, 0]

        def get_cgidx_and_cgtime(cgtime_):
            while cgtime_ not in indices:
                if is_tick:
                    dt_cgtime = dt_ymdhms(str(cgtime_))
                    onesecago = timedelta_sec(-1, dt_cgtime)
                    cgtime_   = int(str_ymdhms(onesecago))
                else:
                    dt_cgtime = dt_ymdhm(str(cgtime_))
                    onesecago = timedelta_sec(-1, dt_cgtime)
                    cgtime_   = int(str_ymdhm(onesecago))
            cgidx_ = np.where(indices == cgtime_)[0][0]
            return cgidx_, cgtime_

        if detail is None:
            con = sqlite3.connect(DB_TRADELIST)
            if market in (3, 4):
                df = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{code}'", con).set_index('index')
            else:
                name = self.dict_name[code] if code in self.dict_name else code
                if market == 1:
                    df = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
                else:
                    df = pd.read_sql(f"SELECT * FROM f_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
            con.close()

            if len(df) > 0:
                for index in df.index:
                    cgtime = int(df['체결시간'][index] if is_tick else str(df['체결시간'][index])[:12])
                    if cgtime < indices[0] or indices[-1] < cgtime:
                        continue

                    cgidx, cgtime = get_cgidx_and_cgtime(cgtime)
                    if market in (1, 3):
                        if df['주문구분'][index] == '매수':
                            buy_index.append(cgtime)
                            arry[cgidx, -2] = df['체결가'][index]
                        elif df['주문구분'][index] == '매도':
                            sell_index.append(cgtime)
                            arry[cgidx, -1] = df['체결가'][index]
                    else:
                        if df['주문구분'][index] == 'BUY_LONG':
                            buy_index.append(cgtime)
                            arry[cgidx, -4] = df['체결가'][index]
                        elif df['주문구분'][index] == 'SELL_LONG':
                            sell_index.append(cgtime)
                            arry[cgidx, -3] = df['체결가'][index]
                        elif df['주문구분'][index] == 'SELL_SHORT':
                            buy_index.append(cgtime)
                            arry[cgidx, -2] = df['체결가'][index]
                        elif df['주문구분'][index] == 'BUY_SHORT':
                            sell_index.append(cgtime)
                            arry[cgidx, -1] =  df['체결가'][index]
        else:
            매수시간, 매수가, 매도시간, 매도가 = detail
            buy_cgidx, _  = get_cgidx_and_cgtime(매수시간)
            sell_cgidx, _ = get_cgidx_and_cgtime(매도시간)
            buy_index.append(매수시간)
            sell_index.append(매도시간)
            arry[buy_cgidx, -2] = 매수가
            arry[sell_cgidx, -1] = 매도가

            if buytimes:
                # noinspection PyUnresolvedReferences
                buytimes = buytimes.split('^')
                buytimes = [x.split(';') for x in buytimes]
                for x in buytimes:
                    추가매수시간, 추가매수가 = int(x[0]), int(x[1]) if market in (1, 2) else float(x[1])
                    buy_cgidx, _  = get_cgidx_and_cgtime(추가매수시간)
                    buy_index.append(추가매수시간)
                    arry[buy_cgidx, -2] = 추가매수가

        if not is_tick:
            arry = np.column_stack((arry, np.zeros((arry.shape[0], 28))))
            try:
                mc = arry[:, 1]
                mh = arry[:, self.factor_index['주식분봉고가' if market == 1 else '그외분봉고가']]
                ml = arry[:, self.factor_index['주식분봉저가' if market == 1 else '그외분봉저가']]
                mv = arry[:, self.factor_index['주식거래대금' if market == 1 else '그외거래대금']]

                AD = talib.AD(mh, ml, mc, mv)
                arry[:, -28] = AD
                if k[0] != 0:
                    ADOSC = talib.ADOSC(mh, ml, mc, mv, fastperiod=k[0], slowperiod=k[1])
                    arry[:, -27] = ADOSC
                if k[2] != 0:
                    ADXR = talib.ADXR(mh, ml, mc, timeperiod=k[2])
                    arry[:, -26] = ADXR
                if k[3] != 0:
                    APO = talib.APO(mc, fastperiod=k[3], slowperiod=k[4], matype=k[5])
                    arry[:, -25] = APO
                if k[6] != 0:
                    AROOND, AROONU = talib.AROON(mh, ml, timeperiod=k[6])
                    arry[:, -24] = AROOND
                    arry[:, -23] = AROONU
                if k[7] != 0:
                    ATR = talib.ATR(mh, ml, mc, timeperiod=k[7])
                    arry[:, -22] = ATR
                if k[8] != 0:
                    BBU, BBM, BBL = talib.BBANDS(mc, timeperiod=k[8], nbdevup=k[9], nbdevdn=k[10], matype=k[11])
                    arry[:, -21] = BBU
                    arry[:, -20] = BBM
                    arry[:, -19] = BBL
                if k[12] != 0:
                    CCI = talib.CCI(mh, ml, mc, timeperiod=k[12])
                    arry[:, -18] = CCI
                if k[13] != 0:
                    DIM = talib.MINUS_DI(mh, ml, mc, timeperiod=k[13])
                    DIP = talib.PLUS_DI(mh, ml, mc, timeperiod=k[13])
                    arry[:, -17] = DIM
                    arry[:, -16] = DIP
                if k[14] != 0:
                    MACD, MACDS, MACDH = talib.MACD(mc, fastperiod=k[14], slowperiod=k[15], signalperiod=k[16])
                    arry[:, -15] = MACD
                    arry[:, -14] = MACDS
                    arry[:, -13] = MACDH
                if k[17] != 0:
                    MFI = talib.MFI(mh, ml, mc, mv, timeperiod=k[17])
                    arry[:, -12] = MFI
                if k[18] != 0:
                    MOM = talib.MOM(mc, timeperiod=k[18])
                    arry[:, -11] = MOM
                OBV = talib.OBV(mc, mv)
                arry[:, -10] = OBV
                if k[19] != 0:
                    PPO = talib.PPO(mc, fastperiod=k[19], slowperiod=k[20], matype=k[21])
                    arry[:,  -9] = PPO
                if k[22] != 0:
                    ROC = talib.ROC(mc, timeperiod=k[22])
                    arry[:,  -8] = ROC
                if k[23] != 0:
                    RSI = talib.RSI(mc, timeperiod=k[23])
                    arry[:,  -7] = RSI
                if k[24] != 0:
                    SAR = talib.SAR(mh, ml, acceleration=k[24], maximum=k[25])
                    arry[:,  -6] = SAR
                if k[26] != 0:
                    STOCHSK, STOCHSD = talib.STOCH(mh, ml, mc, fastk_period=k[26], slowk_period=k[27], slowk_matype=k[28], slowd_period=k[29], slowd_matype=k[30])
                    arry[:,  -5] = STOCHSK
                    arry[:,  -4] = STOCHSD
                if k[31] != 0:
                    STOCHFK, STOCHFD = talib.STOCHF(mh, ml, mc, fastk_period=k[31], fastd_period=k[32], fastd_matype=k[33])
                    arry[:,  -3] = STOCHFK
                    arry[:,  -2] = STOCHFD
                if k[34] != 0:
                    WILLR = talib.WILLR(mh, ml, mc, timeperiod=k[34])
                    arry[:,  -1] = WILLR
                arry = np.nan_to_num(arry)
            except:
                arry = None
                self.windowQ.put((ui_num['시스템로그'], f'{format_exc()}오류 알림 - 보조지표의 설정값이 잘못되었습니다.'))

        if arry is not None:
            fm_list, dict_fm, fm_tcnt = get_formula_data(True, arry.shape[1])
            if fm_tcnt > 0:
                arry = np.column_stack((arry, np.zeros((arry.shape[0], fm_tcnt))))
                fm = FormulaManager(deepcopy(fm_list))
                fm.update_all_data(code, arry, market, is_tick, w_unit)

            if is_tick: xticks = [dt_ymdhms(str(int(x))).timestamp() for x in arry[:, 0]]
            else:       xticks = [dt_ymdhms(f'{int(x)}00').timestamp() for x in arry[:, 0]]
            gubun = 'C' if coin else 'S' if '키움증권' in self.dict_set['증권사'] else 'F'
            self.windowQ.put((ui_num['차트'], gubun, xticks, arry, buy_index, sell_index, fm_list, dict_fm, fm_tcnt))

    @thread_decorator
    def TextToSpeak(self, data):
        with self.tts_lock:
            self.text2speak.say(data)
            self.text2speak.runAndWait()
