
import os
import time
import talib
import shutil
import sqlite3
import numpy as np
import pandas as pd
from copy import deepcopy
from traceback import format_exc
from strategy.manager_formula import ManagerFormula, get_formula_data
from utility.static_method.static import timedelta_sec, str_ymdhms, dt_ymdhms, add_rolling_data, dt_ymdhm, str_ymdhm
from utility.settings.setting_base import UI_NUM, DB_TRADELIST, DB_PATH, DB_BACKTEST, DB_CODE_INFO, DB_SETTING, \
    DB_STRATEGY, COLUMNS_HJ, CODE_INFO_TABLES


class ChartHogaQuery:
    """차트 호가 쿼리 및 사운드 클래스입니다.
    호가 데이터를 처리하고 알림 소리를 재생합니다."""
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, receivQ, traderQ, stgQs, liveQ, testQ
           0        1       2      3       4      5      6      7       8        9       10     11    12
        """
        self.windowQ      = qlist[0]
        self.queryQ       = qlist[2]
        self.chartQ       = qlist[4]
        self.hogaQ        = qlist[5]
        self.testQ        = qlist[12]
        self.dict_set     = dict_set
        self.dict_name    = {}
        self.dict_findex  = {}
        self.index_arry   = None
        self.market_gubun = None
        self.market_info  = None
        self.arry_kosp    = None
        self.arry_kosd    = None
        self.hoga_name    = None
        self.dict_hj      = None
        self.dict_hc      = None
        self.dict_hg      = None

        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()
        self.con2 = sqlite3.connect(DB_TRADELIST)
        self.cur2 = self.con2.cursor()
        self.con3 = sqlite3.connect(DB_STRATEGY)
        self.cur3 = self.con3.cursor()
        self.con4 = sqlite3.connect(DB_CODE_INFO)

        self._init_hoga()
        self._update_dict_name()
        self._set_dict_findex()
        self._main_loop()

    def _update_dict_name(self):
        """종목명 딕셔너리를 업데이트합니다."""
        con = sqlite3.connect(DB_CODE_INFO)
        for table in CODE_INFO_TABLES:
            df = pd.read_sql(f'SELECT * FROM {table}', con).set_index('index')
            self.dict_name.update(df['종목명'].to_dict())
        con.close()

    def _set_dict_findex(self):
        """팩터 인덱스 딕셔너리를 설정합니다."""
        from utility.settings.setting_market import DICT_MARKET_GUBUN, DICT_MARKET_INFO
        self.market_gubun = DICT_MARKET_GUBUN[self.dict_set['거래소']]
        self.market_info  = DICT_MARKET_INFO[self.market_gubun]
        self.is_tick      = self.dict_set['타임프레임']
        factor_list       = self.market_info['팩터목록'][self.is_tick]
        self.dict_findex  = {factor: i for i, factor in enumerate(factor_list)}
        if self.is_tick:
            self.index_arry = np.array([
                self.dict_findex['현재가'], self.dict_findex['체결강도'], self.dict_findex['등락율'],
                self.dict_findex['당일거래대금'], self.dict_findex['초당매수수량'], self.dict_findex['초당매도수량'],
                self.dict_findex['초당거래대금']
            ])
        else:
            self.index_arry = np.array([
                self.dict_findex['현재가'], self.dict_findex['체결강도'], self.dict_findex['등락율'],
                self.dict_findex['당일거래대금'], self.dict_findex['분당매수수량'], self.dict_findex['분당매도수량'],
                self.dict_findex['분당거래대금'], self.dict_findex['분봉고가'], self.dict_findex['분봉저가']
            ])

    def __del__(self):
        """소멸자입니다. 데이터베이스 연결을 닫습니다."""
        self.con1.close()
        self.con2.close()
        self.con3.close()
        self.con4.close()

    def _main_loop(self):
        """메인 루프를 실행합니다."""
        while True:
            try:
                if not self.hogaQ.empty():
                    data = self.hogaQ.get()
                    if len(data) == 8:
                        self._update_hoga_jongmok(data)
                    elif len(data) == 2:
                        self._update_chegeol_count(data)
                    elif len(data) == 4:
                        self._update_hoga_for_chart(data)
                    else:
                        if self.hoga_name == data[0]:
                            self._update_hoga_jalryang(data)
                            if self.dict_hj is not None:
                                self.windowQ.put((UI_NUM['호가종목'], pd.DataFrame([self.dict_hj])))
                            if self.dict_hc is not None:
                                self.windowQ.put((UI_NUM['호가체결'], pd.DataFrame(self.dict_hc)))
                            if self.dict_hg is not None:
                                self.windowQ.put((UI_NUM['호가잔량'], pd.DataFrame(self.dict_hg)))

                if not self.queryQ.empty():
                    data = self.queryQ.get()
                    if data[0] == '설정파일변경':
                        self._settings_change(data)
                    elif data[0] == '설정디비':
                        self._execute_query(data, self.con1, self.cur1)
                        if len(data) == 3:
                            self.testQ.put('설정저장완료')
                    elif data[0] == '거래디비':
                        self._execute_query(data, self.con2, self.cur2)
                    elif data[0] == '전략디비':
                        self._execute_query(data, self.con3, self.cur3)
                    elif data[0] == '종목디비':
                        self._dataframe_to_sql(data, self.con4)
                    elif data[0] == '백테디비':
                        self._backtest_query(data)
                    elif '백테DB지정일자삭제' in data[0]:
                        self._db_back_day_delete(data)
                    elif '일자DB지정일자삭제' in data[0]:
                        self._db_day_day_delete(data)
                    elif '일자DB지정시간이후삭제' in data[0]:
                        self._db_day_time_delete(data)
                    elif '당일데이터지정시간이후삭제' in data[0]:
                        self._db_now_time_delete(data)
                    elif data[0] == '체결시간조정':
                        self._db_now_time_change(data)
                    elif '백테DB생성' in data[0]:
                        self._db_back_create(data)
                    elif '백테디비추가1' in data[0]:
                        self._db_back_area_add(data)
                    elif '백테디비추가2' in data[0]:
                        self._db_back_add()
                    elif '일자DB분리' in data[0]:
                        self._db_now_day_divide()
                    elif data == '프로세스종료':
                        break
                    self.windowQ.put((UI_NUM['DB관리'], 'DB업데이트완료'))

                if not self.chartQ.empty():
                    data = self.chartQ.get()
                    if data[0] == '설정변경':
                        self.dict_set = data[1]
                        self._set_dict_findex()
                    elif data[0] == '그래프비교':
                        self._graph_comparison(data[1])
                    elif len(data) >= 6:
                        self._update_chart(data)

                time.sleep(0.01)
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], format_exc()))

    def _init_hoga(self):
        """호가 딕셔너리를 초기화합니다."""
        self.dict_hj = {
            '종목명': '', '현재가': 0., '등락율': 0., '시가총액': 0, 'UVI': 0., '시가': 0., '고가': 0., '저가': 0.
        }
        self.dict_hc = {
            '체결수량': [0.] * 12, '체결강도': [0.] * 12
        }
        self.dict_hg = {
            '잔량': [0.] * 12, '호가': [0.] * 12
        }
        self.windowQ.put((UI_NUM['호가종목'], pd.DataFrame([self.dict_hj])))
        self.windowQ.put((UI_NUM['호가체결'], pd.DataFrame(self.dict_hc)))
        self.windowQ.put((UI_NUM['호가잔량'], pd.DataFrame(self.dict_hg)))
        self.hoga_name = ''

    def _update_hoga_jongmok(self, data):
        """호가 종목 정보를 업데이트합니다.
        Args:
            data: 호가 데이터
        """
        종목명, 현재가, 등락율, 시가총액, UVI, 시가, 고가, 저가 = data
        if self.hoga_name != 종목명:
            self._init_hoga()
            self.hoga_name = 종목명

        self.dict_hj = {
            '종목명': 종목명, '현재가': 현재가, '등락율': 등락율, '시가총액': 시가총액,
            'UVI': UVI, '시가': 시가, '고가': 고가, '저가': 저가
        }

    def _update_chegeol_count(self, data):
        """체결 수를 업데이트합니다.
        Args:
            data: 체결 데이터
        """
        v, ch = data
        if self.market_gubun < 4 or self.market_gubun in (6, 7, 8):
            if v > 0:
                tbc = self.dict_hc['체결수량'][0] + v
                tsc = self.dict_hc['체결수량'][11]
            else:
                tbc = self.dict_hc['체결수량'][0]
                tsc = self.dict_hc['체결수량'][11] + abs(v)
        elif self.market_gubun == 4:
            if v > 0:
                tbc = round(self.dict_hc['체결수량'][0] + v, 2)
                tsc = round(self.dict_hc['체결수량'][11], 2)
            else:
                tbc = round(self.dict_hc['체결수량'][0], 2)
                tsc = round(self.dict_hc['체결수량'][11] + abs(v), 2)
        else:
            if v > 0:
                tbc = round(self.dict_hc['체결수량'][0] + v, 8)
                tsc = round(self.dict_hc['체결수량'][11], 8)
            else:
                tbc = round(self.dict_hc['체결수량'][0], 8)
                tsc = round(self.dict_hc['체결수량'][11] + abs(v), 8)

        hch = self.dict_hc['체결강도'][0]
        lch = self.dict_hc['체결강도'][11]

        if hch < ch:
            hch = ch
        if lch == 0 or lch > ch:
            lch = ch

        self.dict_hc['체결수량'] = [tbc, v] + self.dict_hc['체결수량'][1:10] + [tsc]
        self.dict_hc['체결강도'] = [hch, ch] + self.dict_hc['체결강도'][1:10] + [lch]

    def _update_hoga_jalryang(self, data):
        """호가 잔량을 업데이트합니다.
        Args:
            data: 호가 데이터
        """
        jr = [data[1]] + list(data[13:23]) + [data[2]]
        hg = [self.dict_hj['고가']] + list(data[3:13]) + [self.dict_hj['저가']]
        self.dict_hg['잔량'] = jr
        self.dict_hg['호가'] = hg

    def _update_hoga_for_chart(self, data):
        """차트용 호가 정보를 업데이트합니다.
        Args:
            data: 호가 데이터
        """
        cmd, code, name, index = data
        searchdate = index[:8]
        index = int(index)
        self._init_hoga()

        db_name1 = f"{self.market_info['일자디비경로'][self.is_tick]}_{searchdate}.db"
        db_name2 = self.market_info['백테디비'][self.is_tick]

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
        except Exception:
            pass

        if df is not None and len(df) > 0:
            data = list(df.iloc[0])
            현재가 = data[self.dict_findex['현재가']]
            등락율 = data[self.dict_findex['등락율']]
            시가 = data[self.dict_findex['시가']]
            고가 = data[self.dict_findex['고가']]
            저가 = data[self.dict_findex['저가']]

            매도총잔량 = data[self.dict_findex['매도총잔량']]
            매도잔량5 = data[self.dict_findex['매도잔량5']]
            매도잔량4 = data[self.dict_findex['매도잔량4']]
            매도잔량3 = data[self.dict_findex['매도잔량3']]
            매도잔량2 = data[self.dict_findex['매도잔량2']]
            매도잔량1 = data[self.dict_findex['매도잔량1']]
            매수잔량1 = data[self.dict_findex['매수잔량1']]
            매수잔량2 = data[self.dict_findex['매수잔량2']]
            매수잔량3 = data[self.dict_findex['매수잔량3']]
            매수잔량4 = data[self.dict_findex['매수잔량4']]
            매수잔량5 = data[self.dict_findex['매수잔량5']]
            매수총잔량 = data[self.dict_findex['매수총잔량']]

            매도호가5 = data[self.dict_findex['매도호가5']]
            매도호가4 = data[self.dict_findex['매도호가4']]
            매도호가3 = data[self.dict_findex['매도호가3']]
            매도호가2 = data[self.dict_findex['매도호가2']]
            매도호가1 = data[self.dict_findex['매도호가1']]
            매수호가1 = data[self.dict_findex['매수호가1']]
            매수호가2 = data[self.dict_findex['매수호가2']]
            매수호가3 = data[self.dict_findex['매수호가3']]
            매수호가4 = data[self.dict_findex['매수호가4']]
            매수호가5 = data[self.dict_findex['매수호가5']]

            if self.market_gubun < 4:
                시가총액 = data[self.dict_findex['시가총액']]
                VI가격 = data[self.dict_findex['VI가격']]
                hj = [name, 현재가, 등락율, 시가총액, VI가격, 시가, 고가, 저가]
            elif self.market_gubun == 4:
                시가총액 = data[self.dict_findex['시가총액']]
                hj = [name, 현재가, 등락율, 시가총액, 0, 시가, 고가, 저가]
            else:
                hj = [name, 현재가, 등락율, 0, 0, 시가, 고가, 저가]

            jr = [
                매도총잔량,
                매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5,
                매수총잔량
            ]
            hg = [
                고가,
                매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5,
                저가
            ]

            df_hj = pd.DataFrame([hj], columns=COLUMNS_HJ)
            df_hg = pd.DataFrame({'잔량': jr, '호가': hg})
            self.windowQ.put((UI_NUM['호가종목'], df_hj, str(int(data[0]))))
            self.windowQ.put((UI_NUM['호가잔량'], df_hg))

    def _settings_change(self, data):
        """설정을 변경합니다.
        Args:
            data: 설정 데이터
        """
        self.con1.close()
        os.remove(data[2])
        shutil.copy(data[1], data[2])
        self.con1 = sqlite3.connect(DB_SETTING)
        self.cur1 = self.con1.cursor()

    def _execute_query(self, data, con, cur):
        """SQL 쿼리를 실행합니다.
        Args:
            data: 쿼리 데이터
            con: 데이터베이스 연결
            cur: 커서
        """
        if len(data) == 2:
            cur.execute(data[1])
            con.commit()
        elif len(data) == 3:
            cur.execute(data[1], data[2])
            con.commit()
        elif len(data) == 4:
            data[1].to_sql(data[2], con, if_exists=data[3], chunksize=2000)

    def _dataframe_to_sql(self, data, con):
        """데이터프레임을 SQL로 저장합니다.
        Args:
            data: 데이터
            con: 데이터베이스 연결
        """
        if len(data) == 4:
            data[1].to_sql(data[2], con, if_exists=data[3], chunksize=2000)

    def _backtest_query(self, data):
        """백테스트 쿼리를 실행합니다.
        Args:
            data: 쿼리 데이터
        """
        con = sqlite3.connect(DB_BACKTEST)
        cur = con.cursor()
        cur.execute(data[1])
        con.commit()
        con.close()

    def _db_back_day_delete(self, data):
        """백테스트 DB의 지정일자 데이터를 삭제합니다.
        Args:
            data: 데이터
        """
        BACK_FILE = self.market_info['백테디비'][self.is_tick]
        con = sqlite3.connect(BACK_FILE)
        df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
        table_list = df['name'].to_list()
        if table_list:
            cur = con.cursor()
            last = len(table_list)
            for i, code in enumerate(table_list):
                query_del = f"DELETE FROM '{code}' WHERE `index` LIKE '{data[1]}%'"
                cur.execute(query_del)
                self.windowQ.put((UI_NUM['DB관리'], f'백테DB [{code}] 지정일자 데이터 삭제 중 ... [{i+1}/{last}]'))
            con.commit()
            self.windowQ.put((UI_NUM['DB관리'], '백테DB 지정일자 데이터 삭제 완료'))
        else:
            self.windowQ.put((UI_NUM['DB관리'], '백테DB에 데이터가 존재하지 않습니다.'))
        con.close()

    def _db_day_day_delete(self, data):
        """일자DB의 지정일자 데이터를 삭제합니다.
        Args:
            data: 데이터
        """
        file_name = f"{self.market_info['일자디비경로'][self.is_tick]}_{data[1]}.db"
        if os.path.isfile(file_name):
            os.remove(file_name)
            self.windowQ.put((UI_NUM['DB관리'], f'일자DB [{file_name}] 삭제 완료'))
        else:
            self.windowQ.put((UI_NUM['DB관리'], '지정한 일자의 일자DB가 존재하지 않습니다.'))

    def _db_day_time_delete(self, data):
        """일자DB의 지정시간 이후 데이터를 삭제합니다.
        Args:
            data: 데이터
        """
        first_name = f"{self.market_info['일자디비경로'][self.is_tick].split('/')[2]}_"
        file_list = os.listdir(DB_PATH)
        file_list = [x for x in file_list if first_name in x and '.db' in x and 'back' not in x]
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
                df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=2000)
                mtlist = list(set(';'.join(df['거래대금순위'].to_list()[29:]).split(';')))
                for code in table_list:
                    if code in mtlist:
                        df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                        df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
                        df = df[df['시간'] <= int(data[1])]
                        df.drop(columns=['시간'], inplace=True)
                        if len(df) > 0:
                            df.to_sql(code, con, index=False, if_exists='replace', chunksize=2000)
                        else:
                            cur.execute(f'DROP TABLE "{code}"')
                    elif code != 'moneytop':
                        cur.execute(f'DROP TABLE "{code}"')
                cur.execute('VACUUM;')
                con.close()
                self.windowQ.put((UI_NUM['DB관리'], f'일자DB [{db_name}] 지정시간 이후 데이터 삭제 중 ... [{i+1}/{last}]'))
            self.windowQ.put((UI_NUM['DB관리'], '일자DB 지정시간 이후 데이터 삭제 완료'))
        else:
            self.windowQ.put((UI_NUM['DB관리'], '일자DB가 존재하지 않습니다.'))

    def _db_now_time_delete(self, data):
        """당일DB의 지정시간 이후 데이터를 삭제합니다.
        Args:
            data: 데이터
        """
        DB_FILE = self.market_info['당일디비'][self.is_tick]
        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except Exception:
            self.windowQ.put((UI_NUM['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        else:
            cur = con.cursor()
            df['시간'] = df['index'].apply(lambda x: int(str(x)[8:]))
            df = df[df['시간'] <= int(data[1])]
            df.drop(columns=['시간'], inplace=True)
            df.to_sql('moneytop', con, index=False, if_exists='replace', chunksize=2000)
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
                            df.to_sql(code, con, index=False, if_exists='replace', chunksize=2000)
                        else:
                            cur.execute(f'DROP TABLE "{code}"')
                    elif code != 'moneytop':
                        cur.execute(f'DROP TABLE "{code}"')
                    self.windowQ.put((UI_NUM['DB관리'], f'당일DB [{code}] 지정시간 이후 데이터 삭제 중 ... [{i+1}/{last}]'))
                cur.execute('VACUUM;')
                self.windowQ.put((UI_NUM['DB관리'], '당일DB 지정시간 이후 데이터 삭제 완료'))
            else:
                self.windowQ.put((UI_NUM['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        con.close()

    def _db_now_time_change(self, data):
        """당일DB의 체결시간을 조정합니다.
        Args:
            data: 데이터
        """
        DB_FILE = self.market_info['당일디비'][self.is_tick]
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
                if self.dict_set['타임프레임']:
                    df['index'] = df['index'] - 10000
                else:
                    df['index'] = df['index'] - 100
                df.to_sql(code, con, index=False, if_exists='append', chunksize=2000)
                self.windowQ.put((UI_NUM['DB관리'], f'당일DB [{code}] 체결시간 조정 중 ... [{i+1}/{last}]'))
            self.windowQ.put((UI_NUM['DB관리'], '당일DB 체결시간 조정 완료'))
        else:
            self.windowQ.put((UI_NUM['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        con.close()

    def _db_back_create(self, data):
        """백테스트 DB를 생성합니다.
        Args:
            data: 데이터
        """
        BACK_FILE = self.market_info['백테디비'][self.is_tick]
        first_name = f"{self.market_info['일자디비경로'][self.is_tick].split('/')[2]}_"
        file_list = os.listdir(DB_PATH)
        file_list = [x for x in file_list if first_name in x and '.db' in x and 'back' not in x]
        if file_list:
            if os.path.isfile(BACK_FILE):
                os.remove(BACK_FILE)
                self.windowQ.put((UI_NUM['DB관리'], f'{BACK_FILE} 삭제 완료'))

            con = sqlite3.connect(BACK_FILE)
            code_info_table_name = self.market_info['종목디비']
            df = pd.read_sql(f'SELECT * FROM {code_info_table_name}', self.con4)
            df.to_sql(code_info_table_name, con, index=False, if_exists='replace', chunksize=2000)

            file_list = [x for x in file_list if int(data[1]) <= int(x.split(first_name)[1].replace('.db', '')) <= int(data[2])]
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
                    self.windowQ.put((UI_NUM['DB관리'], f'백테DB [{db_name}] 데이터 추가 중 ... [{i+1}/{last}]'))
                self.windowQ.put((UI_NUM['DB관리'], f'백테DB {BACK_FILE} 생성 완료'))
            else:
                self.windowQ.put((UI_NUM['DB관리'], '지정한 기간의 일자DB가 존재하지 않습니다.'))
            con.close()
        else:
            self.windowQ.put((UI_NUM['DB관리'], '일자DB가 존재하지 않습니다.'))

    def _db_back_area_add(self, data):
        """백테스트 DB에 일자 데이터를 추가합니다.
        Args:
            data: 데이터
        """
        BACK_FILE = self.market_info['백테디비'][self.is_tick]
        first_name = f"{self.market_info['일자디비경로'][self.is_tick].split('/')[2]}_"
        file_list = os.listdir(DB_PATH)
        file_list = [x for x in file_list if first_name in x and '.db' in x and 'back' not in x]
        if file_list:
            con = sqlite3.connect(BACK_FILE)
            code_info_table_name = self.market_info['종목디비']
            df = pd.read_sql(f'SELECT * FROM {code_info_table_name}', self.con4)
            df.to_sql(code_info_table_name, con, index=False, if_exists='replace', chunksize=2000)

            file_list = [x for x in file_list if int(data[1]) <= int(x.split(first_name)[1].replace('.db', '')) <= int(data[2])]
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
                    self.windowQ.put((UI_NUM['DB관리'], f'백테DB [{db_name}] 데이터 추가 중 ... [{i+1}/{last}]'))
                self.windowQ.put((UI_NUM['DB관리'], f'백테DB [{data[1]} ~ {data[2]}] 데이터 추가 완료'))
            else:
                self.windowQ.put((UI_NUM['DB관리'], '지정한 기간의 일자DB가 존재하지 않습니다.'))
            con.close()
        else:
            self.windowQ.put((UI_NUM['DB관리'], '일자DB가 존재하지 않습니다.'))

    def _db_back_add(self):
        """백테스트 DB에 당일DB 데이터를 추가합니다.
        """
        DB_FILE = self.market_info['당일디비'][self.is_tick]
        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except Exception:
            self.windowQ.put((UI_NUM['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
            con.close()
        else:
            BACK_FILE = self.market_info['백테디비'][self.is_tick]
            first_name = f"{self.market_info['일자디비경로'][self.is_tick].split('/')[2]}_"
            con2 = sqlite3.connect(BACK_FILE)
            df['일자'] = df['index'].apply(lambda x: str(x)[:8])
            day_list = df['일자'].unique()
            file_list = os.listdir(DB_PATH)
            file_day_list = [x.strip(first_name).strip('.db') for x in file_list if
                             first_name in x and '.db' in x and 'back' not in x]
            if len(set(day_list) - set(file_day_list)) > 0:
                self.windowQ.put((UI_NUM['DB관리'], '경고! 추가 후 당일 DB가 삭제됩니다.'))
                self.windowQ.put((UI_NUM['DB관리'], '일자별 분리 후 재실행하십시오.'))
                con2.close()
                con.close()
            else:
                code_info_table_name = self.market_info['종목디비']
                df = pd.read_sql(f'SELECT * FROM {code_info_table_name}', self.con4)
                df.to_sql(code_info_table_name, con2, index=False, if_exists='replace', chunksize=2000)

                df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
                table_list = df['name'].to_list()
                last = len(table_list)
                for i, code in enumerate(table_list):
                    df = pd.read_sql(f'SELECT * FROM "{code}"', con)
                    if len(df) > 0:
                        df.to_sql(code, con2, index=False, if_exists='append', chunksize=2000)
                    self.windowQ.put((UI_NUM['DB관리'], f'백테DB [{code}] 데이터 추가 중 ... [{i+1}/{last}]'))
                self.windowQ.put((UI_NUM['DB관리'], '당일DB 데이터, 백테DB로 추가 완료'))
                con2.close()
                con.close()

                if os.path.isfile(DB_FILE):
                    os.remove(DB_FILE)
                    self.windowQ.put((UI_NUM['DB관리'], f'당일DB {DB_FILE} 삭제 완료'))

    def _db_now_day_divide(self):
        """당일DB 데이터를 일자별로 분리합니다.
        """
        DB_FILE = self.market_info['당일디비'][self.is_tick]
        con = sqlite3.connect(DB_FILE)
        try:
            df = pd.read_sql('SELECT * FROM moneytop', con)
        except Exception:
            self.windowQ.put((UI_NUM['DB관리'], '당일DB에 데이터가 존재하지 않습니다.'))
        else:
            df['일자'] = df['index'].apply(lambda x: int(str(x)[:8]))
            day_list = df['일자'].unique()
            df = pd.read_sql("SELECT name FROM sqlite_master WHERE TYPE = 'table'", con)
            table_list = df['name'].to_list()
            if table_list:
                last = len(table_list)
                first_name = f"{self.market_info['일자디비경로'][self.is_tick].split('/')[2]}_"
                for i, code in enumerate(table_list):
                    for day in day_list:
                        df = pd.read_sql(f'SELECT * FROM "{code}" WHERE "index" LIKE "{day}%"', con)
                        if len(df) > 0:
                            con2 = sqlite3.connect(f'{DB_PATH}/{first_name}{day}.db')
                            df.to_sql(code, con2, index=False, if_exists='replace', chunksize=2000)
                            con2.close()
                    self.windowQ.put((UI_NUM['DB관리'], f'당일DB [{code}] 데이터 분리 중 ... [{i+1}/{last}]'))
                self.windowQ.put((UI_NUM['DB관리'], '당일DB 데이터, 일자DB로 분리 완료'))
            else:
                self.windowQ.put((UI_NUM['DB관리'], '일자DB에 데이터가 존재하지 않습니다.'))
        con.close()

    @staticmethod
    def _graph_comparison(backdetail_list):
        """그래프 비교를 수행합니다.
        Args:
            backdetail_list: 백테스트 상세 리스트
        """
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

    def _update_chart(self, data):
        """차트를 업데이트합니다.
        Args:
            data: 차트 데이터
        """
        if len(data) == 6:
            code, w_unit, searchdate, starttime, endtime, k = data
            detail, buytimes, cf1, cf2 = None, None, None, None
        elif len(data) == 8:
            code, w_unit, searchdate, starttime, endtime, k = data[:6]
            if data[6].__class__ == list:
                detail, buytimes = data[6:]
                cf1, cf2 = None, None
            else:
                detail, buytimes = None, None
                cf1, cf2 = data[6:]
        else:
            code, w_unit, searchdate, starttime, endtime, k, detail, buytimes, cf1, cf2 = data

        db_name  = None
        db_name1 = f"{self.market_info['일자디비경로'][self.is_tick]}_{searchdate}.db"
        db_name2 = self.market_info['백테디비'][self.is_tick]

        if os.path.isfile(db_name1):
            db_name = db_name1
        elif os.path.isfile(db_name2):
            db_name = db_name2

        if db_name is None:
            self.windowQ.put((UI_NUM['차트'], '차트오류'))
            return

        if starttime == '':
            starttime = str(self.market_info['시작시간']).zfill(6)
            endtime = str(self.market_info['종료시간'][self.is_tick]).zfill(6)

        starttime = int(starttime)
        endtime = int(endtime)

        if self.is_tick:
            query = f"SELECT * FROM '{code}' WHERE " \
                    f"`index` >= {int(searchdate) * 1000000 + starttime} and " \
                    f"`index` <= {int(searchdate) * 1000000 + endtime}"
        else:
            query = f"SELECT * FROM '{code}' WHERE " \
                    f"`index` >= {int(searchdate) * 10000 + int(starttime / 100)} and " \
                    f"`index` <= {int(searchdate) * 10000 + int(endtime / 100)}"

        try:
            con = sqlite3.connect(db_name)
            df = pd.read_sql(query, con)
            con.close()
        except Exception:
            self.windowQ.put((UI_NUM['차트'], '차트오류'))
            return

        round_unit = self.market_info['반올림단위']
        angle_cf_list = self.market_info['각도계수'][self.is_tick]
        if w_unit == '':
            w_unit = self.dict_set['평균값계산틱수']

        if cf1 is None:
            arry = add_rolling_data(df, round_unit, angle_cf_list, [w_unit], self.is_tick, self.index_arry)
        else:
            arry = add_rolling_data(df, round_unit, angle_cf_list, [w_unit], self.is_tick, self.index_arry, cf1=cf1, cf2=cf2)

        if not self.is_tick:
            arry = np.column_stack((arry, np.zeros((arry.shape[0], 28))))
            try:
                mc = arry[:, 1]
                mh = arry[:, self.dict_findex['분봉고가']]
                ml = arry[:, self.dict_findex['분봉저가']]
                mv = arry[:, self.dict_findex['분당거래대금']]

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
            except Exception:
                self.windowQ.put((UI_NUM['시스템로그'], f'{format_exc()}오류 알림 - 보조지표의 설정값이 잘못되었습니다.'))
                return

        fm_list, dict_fm, fm_tcnt = get_formula_data(True, arry.shape[1])
        if fm_tcnt > 0:
            arry = np.column_stack((arry, np.zeros((arry.shape[0], fm_tcnt))))
            fm = ManagerFormula(deepcopy(fm_list), self.dict_set, self.is_tick, self.dict_findex)
            fm.update_all_data(code, arry, self.market_gubun, w_unit)

        buy_index  = []
        sell_index = []
        # noinspection PyUnresolvedReferences
        arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))
        if self.market_gubun > 5:
            arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))

        indices = arry[:, 0]

        def get_cgidx_and_cgtime(cgtime_):
            while cgtime_ not in indices:
                if self.is_tick:
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
            name = self.dict_name.get(code, code)
            chegeol_table = self.market_info['체결디비']
            con = sqlite3.connect(DB_TRADELIST)
            df = pd.read_sql(f"SELECT * FROM {chegeol_table} WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
            con.close()

            if len(df) > 0:
                for index in df.index:
                    cgtime = int(df['체결시간'][index] if self.is_tick else str(df['체결시간'][index])[:12])
                    if cgtime < indices[0] or indices[-1] < cgtime:
                        continue

                    cgidx, cgtime = get_cgidx_and_cgtime(cgtime)
                    if self.market_gubun < 6:
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
                    추가매수시간, 추가매수가 = int(x[0]), float(x[1])
                    buy_cgidx, _  = get_cgidx_and_cgtime(추가매수시간)
                    buy_index.append(추가매수시간)
                    arry[buy_cgidx, -2] = 추가매수가

        if self.is_tick: xticks = [dt_ymdhms(str(int(x))).timestamp() for x in arry[:, 0]]
        else:            xticks = [dt_ymdhms(f'{int(x)}00').timestamp() for x in arry[:, 0]]
        self.windowQ.put((UI_NUM['차트'], xticks, arry, buy_index, sell_index, fm_list, dict_fm, fm_tcnt))
