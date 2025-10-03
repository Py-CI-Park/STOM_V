import os
import math
import talib
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from matplotlib import font_manager
from matplotlib import pyplot as plt
from utility.static import strp_time, timedelta_sec, strf_time, error_decorator
from utility.setting import ui_num, DICT_SET, DB_TRADELIST, DB_SETTING, DB_PATH, DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, \
    DB_BACKTEST, DB_COIN_BACK_MIN, DB_STOCK_BACK_MIN, DB_STRATEGY


class Chart:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ  = qlist[0]
        self.chartQ   = qlist[4]
        self.dict_set = DICT_SET

        con1 = sqlite3.connect(DB_SETTING)
        con2 = sqlite3.connect(DB_STOCK_BACK_TICK if self.dict_set['주식타임프레임'] else DB_STOCK_BACK_MIN)
        try:
            df = pd.read_sql('SELECT * FROM codename', con1).set_index('index')
        except:
            df = pd.read_sql('SELECT * FROM codename', con2).set_index('index')
        con1.close()
        con2.close()

        font_name = 'C:/Windows/Fonts/malgun.ttf'
        font_family = font_manager.FontProperties(fname=font_name).get_name()
        plt.rcParams['font.family'] = font_family
        plt.rcParams['axes.unicode_minus'] = False

        self.dict_name  = df['종목명'].to_dict()
        self.arry_kosp  = None
        self.arry_kosd  = None
        self.Start()

    def Start(self):
        while True:
            data = self.chartQ.get()
            if data[0] == '설정변경':
                self.dict_set = data[1]
            if data[0] == '그래프비교':
                self.GraphComparison(data[1])
            elif len(data) == 3:
                self.UpdateRealJisu(data)
            elif len(data) >= 7:
                self.UpdateChart(data)

    @staticmethod
    def GraphComparison(backdetail_list):
        plt.figure('그래프 비교', figsize=(12, 10))
        con = sqlite3.connect(DB_BACKTEST)
        for table in backdetail_list:
            df = pd.read_sql(f'SELECT `index`, `수익금` FROM {table}', con)
            df['index'] = df['index'].apply(lambda x: strp_time('%Y%m%d%H%M%S', x))
            df.set_index('index', inplace=True)
            df = df.resample('D').sum()
            df['수익금합계'] = df['수익금'].cumsum()
            plt.plot(df.index, df['수익금합계'], linewidth=1, label=table)
        con.close()
        plt.legend(loc='best')
        plt.tight_layout()
        plt.grid()
        plt.show()

    def UpdateRealJisu(self, data):
        gubun = data[0]
        jisu_data = data[1:]
        try:
            if gubun == '코스피':
                if self.arry_kosp is None:
                    self.arry_kosp = np.array([jisu_data])
                else:
                    self.arry_kosp = np.r_[self.arry_kosp, np.array([jisu_data])]
                xticks = [strp_time('%Y%m%d%H%M%S', str(int(x))).timestamp() for x in self.arry_kosp[:, 0]]
                self.windowQ.put((ui_num['코스피'], xticks, self.arry_kosp[:, 1]))
            elif gubun == '코스닥':
                if self.arry_kosd is None:
                    self.arry_kosd = np.array([jisu_data])
                else:
                    self.arry_kosd = np.r_[self.arry_kosd, np.array([jisu_data])]
                xticks = [strp_time('%Y%m%d%H%M%S', str(int(x))).timestamp() for x in self.arry_kosd[:, 0]]
                self.windowQ.put((ui_num['코스닥'], xticks, self.arry_kosd[:, 1]))
        except:
            pass

    @error_decorator
    def UpdateChart(self, data):
        if len(data) == 7:
            coin, code, tickcount, searchdate, starttime, endtime, k = data
            detail, buytimes = None, None
        else:
            coin, code, tickcount, searchdate, starttime, endtime, k, detail, buytimes = data

        con = sqlite3.connect(DB_STRATEGY)
        is_min = False
        if coin:
            if self.dict_set['코인타임프레임']:
                db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db'
                db_name2 = DB_COIN_BACK_TICK
                query1   = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%' and " \
                           f"`index` % 1000000 >= {starttime} and " \
                           f"`index` % 1000000 <= {endtime}"
            else:
                is_min   = True
                db_name1 = f'{DB_PATH}/coin_min_{searchdate}.db'
                db_name2 = DB_COIN_BACK_MIN
                query1   = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%' and " \
                           f"`index` % 10000 >= {starttime} and " \
                           f"`index` % 10000 <= {endtime}"
        else:
            if self.dict_set['주식타임프레임']:
                db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db'
                db_name2 = DB_STOCK_BACK_TICK
                query1   = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%' and " \
                           f"`index` % 1000000 >= {starttime} and " \
                           f"`index` % 1000000 <= {endtime}"
            else:
                is_min   = True
                db_name1 = f'{DB_PATH}/stock_min_{searchdate}.db'
                db_name2 = DB_STOCK_BACK_MIN
                query1   = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%' and " \
                           f"`index` % 10000 >= {starttime} and " \
                           f"`index` % 10000 <= {endtime}"
        con.close()

        df = None
        query2 = f"SELECT * FROM '{code}' WHERE `index` LIKE '{searchdate}%'"
        try:
            if os.path.isfile(db_name1):
                con = sqlite3.connect(db_name1)
                df = pd.read_sql(query1 if starttime != '' and endtime != '' else query2, con).set_index('index')
                con.close()
            elif os.path.isfile(db_name2):
                con = sqlite3.connect(db_name2)
                df = pd.read_sql(query1 if starttime != '' and endtime != '' else query2, con).set_index('index')
                con.close()
        except:
            pass

        if df is None or len(df) == 0:
            self.windowQ.put((ui_num['차트'], '차트오류', '', '', '', ''))
        else:
            if coin:
                round_unit = 8
                if tickcount == '': tickcount = self.dict_set['코인평균값계산틱수']
            else:
                round_unit = 3
                if tickcount == '': tickcount = self.dict_set['주식평균값계산틱수']

            df['체결시간'] = df.index
            if is_min:
                df['이동평균005'] = df['현재가'].rolling(window=5).mean().round(round_unit)
                df['이동평균010'] = df['현재가'].rolling(window=10).mean().round(round_unit)
                df['이동평균020'] = df['현재가'].rolling(window=20).mean().round(round_unit)
                df['이동평균060'] = df['현재가'].rolling(window=60).mean().round(round_unit)
                df['이동평균120'] = df['현재가'].rolling(window=120).mean().round(round_unit)
            else:
                df['이동평균0060'] = df['현재가'].rolling(window=60).mean().round(round_unit)
                df['이동평균0300'] = df['현재가'].rolling(window=300).mean().round(round_unit)
                df['이동평균0600'] = df['현재가'].rolling(window=600).mean().round(round_unit)
                df['이동평균1200'] = df['현재가'].rolling(window=1200).mean().round(round_unit)

            df[f'최고현재가'] = df['현재가'].rolling(window=tickcount).max()
            df[f'최저현재가'] = df['현재가'].rolling(window=tickcount).min()
            if is_min:
                df[f'최고분봉고가'] = df['분봉고가'].rolling(window=tickcount).max()
                df[f'최저분봉저가'] = df['분봉저가'].rolling(window=tickcount).min()
            df[f'체결강도평균'] = df['체결강도'].rolling(window=tickcount).mean().round(3)
            df[f'최고체결강도'] = df['체결강도'].rolling(window=tickcount).max()
            df[f'최저체결강도'] = df['체결강도'].rolling(window=tickcount).min()
            if is_min:
                df[f'최고분당매수수량'] = df['분당매수수량'].rolling(window=tickcount).max()
                df[f'최고분당매도수량'] = df['분당매도수량'].rolling(window=tickcount).max()
                df[f'누적분당매수수량'] = df['분당매수수량'].rolling(window=tickcount).sum()
                df[f'누적분당매도수량'] = df['분당매도수량'].rolling(window=tickcount).sum()
                df[f'분당거래대금평균'] = df['분당거래대금'].rolling(window=tickcount).mean().round(0)
            else:
                df[f'최고초당매수수량'] = df['초당매수수량'].rolling(window=tickcount).max()
                df[f'최고초당매도수량'] = df['초당매도수량'].rolling(window=tickcount).max()
                df[f'누적초당매수수량'] = df['초당매수수량'].rolling(window=tickcount).sum()
                df[f'누적초당매도수량'] = df['초당매도수량'].rolling(window=tickcount).sum()
                df[f'초당거래대금평균'] = df['초당거래대금'].rolling(window=tickcount).mean().round(0)

            df[f'등락율N{tickcount}'] = df['등락율'].shift(tickcount - 1)
            df['등락율차이'] = df['등락율'] - df[f'등락율N{tickcount}']
            df[f'당일거래대금N{tickcount}'] = df['당일거래대금'].shift(tickcount - 1)
            df['당일거래대금차이'] = df['당일거래대금'] - df[f'당일거래대금N{tickcount}']
            if not coin:
                df['등락율각도'] = df['등락율차이'].apply(lambda x: round(math.atan2(x * 5, tickcount) / (2 * math.pi) * 360, 2))
                df['당일거래대금각도'] = df['당일거래대금차이'].apply(lambda x: round(math.atan2(x / 100, tickcount) / (2 * math.pi) * 360, 2))
                df[f'전일비N{tickcount}'] = df['전일비'].shift(tickcount - 1)
                df['전일비차이'] = df['전일비'] - df[f'전일비N{tickcount}']
                df['전일비각도'] = df['전일비차이'].apply(lambda x: round(math.atan2(x, tickcount) / (2 * math.pi) * 360, 2))
            else:
                df['등락율각도'] = df['등락율차이'].apply(lambda x: round(math.atan2(x * 10, tickcount) / (2 * math.pi) * 360, 2))
                df['당일거래대금각도'] = df['당일거래대금차이'].apply(lambda x: round(math.atan2(x / 100_000_000, tickcount) / (2 * math.pi) * 360, 2))

            buy_index  = []
            sell_index = []
            df['매수가'] = 0
            df['매도가'] = 0
            if coin:
                df['매수가2'] = 0
                df['매도가2'] = 0

            if detail is None:
                con = sqlite3.connect(DB_TRADELIST)
                if coin:
                    df2 = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{code}'", con).set_index('index')
                else:
                    name = self.dict_name[code] if code in self.dict_name.keys() else code
                    df2 = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
                con.close()

                if len(df2) > 0:
                    for index in df2.index:
                        cgtime = int(float(str(df2['체결시간'][index])[:12] if is_min else df2['체결시간'][index]))
                        if 'USDT' not in code:
                            if df2['주문구분'][index] == '매수':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                buy_index.append(cgtime)
                                df.loc[cgtime, '매수가'] = df2['체결가'][index]
                            elif df2['주문구분'][index] == '매도':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                sell_index.append(cgtime)
                                df.loc[cgtime, '매도가'] = df2['체결가'][index]
                        else:
                            if df2['주문구분'][index] == 'BUY_LONG':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                buy_index.append(cgtime)
                                df.loc[cgtime, '매수가'] = df2['체결가'][index]
                            elif df2['주문구분'][index] == 'SELL_LONG':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                sell_index.append(cgtime)
                                df.loc[cgtime, '매도가'] = df2['체결가'][index]
                            elif df2['주문구분'][index] == 'SELL_SHORT':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                buy_index.append(cgtime)
                                df.loc[cgtime, '매수가2'] = df2['체결가'][index]
                            elif df2['주문구분'][index] == 'BUY_SHORT':
                                while cgtime not in df.index:
                                    onesecago = timedelta_sec(-1, strp_time('%Y%m%d%H%M%S', str(cgtime)))
                                    cgtime = int(strf_time('%Y%m%d%H%M%S', onesecago))
                                sell_index.append(cgtime)
                                df.loc[cgtime, '매도가2'] = df2['체결가'][index]
            else:
                매수시간, 매수가, 매도시간, 매도가 = detail
                buy_index.append(매수시간)
                sell_index.append(매도시간)
                df.loc[매수시간, '매수가'] = 매수가
                df.loc[매도시간, '매도가'] = 매도가
                if buytimes != '':
                    buytimes = buytimes.split('^')
                    buytimes = [x.split(';') for x in buytimes]
                    for x in buytimes:
                        추가매수시간, 추가매수가 = int(x[0]), int(x[1]) if not coin else float(x[1])
                        buy_index.append(추가매수시간)
                        df.loc[추가매수시간, '매수가'] = 추가매수가

            if not coin:
                if is_min:
                    columns = [
                        '체결시간', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '거래대금증감', '전일비', '회전율',
                        '전일동시간비', '시가총액', '라운드피겨위5호가이내', '분당매수수량', '분당매도수량', 'VI해제시간', 'VI가격', 'VI호가단위', '분봉시가',
                        '분봉고가', '분봉저가', '분당거래대금', '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5', '매도호가4', '매도호가3',
                        '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5', '매도잔량5', '매도잔량4', '매도잔량3',
                        '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5', '매도수5호가잔량합', '관심종목',
                        '이동평균005', '이동평균010', '이동평균020', '이동평균060', '이동평균120', '최고현재가', '최저현재가', '최고분봉고가',
                        '최저분봉저가', '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
                        '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도', '전일비각도'
                    ]
                else:
                    columns = [
                        '체결시간', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '거래대금증감', '전일비', '회전율',
                        '전일동시간비', '시가총액', '라운드피겨위5호가이내', '초당매수수량', '초당매도수량', 'VI해제시간', 'VI가격', 'VI호가단위',
                        '초당거래대금', '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1',
                        '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5', '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1',
                        '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5', '매도수5호가잔량합', '관심종목', '이동평균0060', '이동평균0300',
                        '이동평균0600', '이동평균1200', '최고현재가', '최저현재가', '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량',
                        '최고초당매도수량', '누적초당매수수량', '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도', '전일비각도'
                    ]
            else:
                if is_min:
                    columns = [
                        '체결시간', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '분당매수수량', '분당매도수량', '분봉시가',
                        '분봉고가', '분봉저가', '분당거래대금', '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5', '매도호가4', '매도호가3',
                        '매도호가2', '매도호가1', '매수호가1', '매수호가2', '매수호가3', '매수호가4', '매수호가5', '매도잔량5', '매도잔량4', '매도잔량3',
                        '매도잔량2', '매도잔량1', '매수잔량1', '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5', '매도수5호가잔량합', '관심종목',
                        '이동평균005', '이동평균010', '이동평균020', '이동평균060', '이동평균120', '최고현재가', '최저현재가', '최고분봉고가',
                        '최저분봉저가', '체결강도평균', '최고체결강도', '최저체결강도', '최고분당매수수량', '최고분당매도수량', '누적분당매수수량',
                        '누적분당매도수량', '분당거래대금평균', '등락율각도', '당일거래대금각도'
                    ]
                else:
                    columns = [
                        '체결시간', '현재가', '시가', '고가', '저가', '등락율', '당일거래대금', '체결강도', '초당매수수량', '초당매도수량', '초당거래대금',
                        '고저평균대비등락율', '매도총잔량', '매수총잔량', '매도호가5', '매도호가4', '매도호가3', '매도호가2', '매도호가1', '매수호가1',
                        '매수호가2', '매수호가3', '매수호가4', '매수호가5', '매도잔량5', '매도잔량4', '매도잔량3', '매도잔량2', '매도잔량1', '매수잔량1',
                        '매수잔량2', '매수잔량3', '매수잔량4', '매수잔량5', '매도수5호가잔량합', '관심종목', '이동평균0060', '이동평균0300', '이동평균0600',
                        '이동평균1200', '최고현재가', '최저현재가', '체결강도평균', '최고체결강도', '최저체결강도', '최고초당매수수량', '최고초당매도수량',
                        '누적초당매수수량', '누적초당매도수량', '초당거래대금평균', '등락율각도', '당일거래대금각도'
                    ]

            columns += ['매수가', '매도가']
            if coin:
                columns += ['매수가2', '매도가2']
            df = df[columns]
            df.fillna(0, inplace=True)

            arry_tick = np.array(df)
            if is_min:
                arry_tick = np.r_['1', arry_tick, np.zeros((len(arry_tick), 28))]
                try:
                    mc = arry_tick[:, 1]
                    if coin:
                        mh = arry_tick[:, 11]
                        ml = arry_tick[:, 12]
                        mv = arry_tick[:, 13]
                    else:
                        mh = arry_tick[:, 20]
                        ml = arry_tick[:, 21]
                        mv = arry_tick[:, 22]

                    AD = talib.AD(mh, ml, mc, mv)
                    arry_tick[:, -28] = AD
                    if k[0] != 0:
                        ADOSC = talib.ADOSC(mh, ml, mc, mv, fastperiod=k[0], slowperiod=k[1])
                        arry_tick[:, -27] = ADOSC
                    if k[2] != 0:
                        ADXR = talib.ADXR(mh, ml, mc, timeperiod=k[2])
                        arry_tick[:, -26] = ADXR
                    if k[3] != 0:
                        APO = talib.APO(mc, fastperiod=k[3], slowperiod=k[4], matype=k[5])
                        arry_tick[:, -25] = APO
                    if k[6] != 0:
                        AROOND, AROONU = talib.AROON(mh, ml, timeperiod=k[6])
                        arry_tick[:, -24] = AROOND
                        arry_tick[:, -23] = AROONU
                    if k[7] != 0:
                        ATR = talib.ATR(mh, ml, mc, timeperiod=k[7])
                        arry_tick[:, -22] = ATR
                    if k[8] != 0:
                        BBU, BBM, BBL = talib.BBANDS(mc, timeperiod=k[8], nbdevup=k[9], nbdevdn=k[10], matype=k[11])
                        arry_tick[:, -21] = BBU
                        arry_tick[:, -20] = BBM
                        arry_tick[:, -19] = BBL
                    if k[12] != 0:
                        CCI = talib.CCI(mh, ml, mc, timeperiod=k[12])
                        arry_tick[:, -18] = CCI
                    if k[13] != 0:
                        DIM = talib.MINUS_DI(mh, ml, mc, timeperiod=k[13])
                        DIP = talib.PLUS_DI(mh, ml, mc, timeperiod=k[13])
                        arry_tick[:, -17] = DIM
                        arry_tick[:, -16] = DIP
                    if k[14] != 0:
                        MACD, MACDS, MACDH = talib.MACD(mc, fastperiod=k[14], slowperiod=k[15], signalperiod=k[16])
                        arry_tick[:, -15] = MACD
                        arry_tick[:, -14] = MACDS
                        arry_tick[:, -13] = MACDH
                    if k[17] != 0:
                        MFI = talib.MFI(mh, ml, mc, mv, timeperiod=k[17])
                        arry_tick[:, -12] = MFI
                    if k[18] != 0:
                        MOM = talib.MOM(mc, timeperiod=k[18])
                        arry_tick[:, -11] = MOM
                    OBV = talib.OBV(mc, mv)
                    arry_tick[:, -10] = OBV
                    if k[19] != 0:
                        PPO = talib.PPO(mc, fastperiod=k[19], slowperiod=k[20], matype=k[21])
                        arry_tick[:,  -9] = PPO
                    if k[22] != 0:
                        ROC = talib.ROC(mc, timeperiod=k[22])
                        arry_tick[:,  -8] = ROC
                    if k[23] != 0:
                        RSI = talib.RSI(mc, timeperiod=k[23])
                        arry_tick[:,  -7] = RSI
                    if k[24] != 0:
                        SAR = talib.SAR(mh, ml, acceleration=k[24], maximum=k[25])
                        arry_tick[:,  -6] = SAR
                    if k[26] != 0:
                        STOCHSK, STOCHSD = talib.STOCH(mh, ml, mc, fastk_period=k[26], slowk_period=k[27], slowk_matype=k[28], slowd_period=k[29], slowd_matype=k[30])
                        arry_tick[:,  -5] = STOCHSK
                        arry_tick[:,  -4] = STOCHSD
                    if k[31] != 0:
                        STOCHFK, STOCHFD = talib.STOCHF(mh, ml, mc, fastk_period=k[31], fastd_period=k[32], fastd_matype=k[33])
                        arry_tick[:,  -3] = STOCHFK
                        arry_tick[:,  -2] = STOCHFD
                    if k[34] != 0:
                        WILLR = talib.WILLR(mh, ml, mc, timeperiod=k[34])
                        arry_tick[:,  -1] = WILLR
                    arry_tick = np.nan_to_num(arry_tick)
                except:
                    arry_tick = None
                    print(f'보조지표의 설정값이 잘못되었습니다.')
                    print_exc()

            if arry_tick is not None:
                xticks = [strp_time('%Y%m%d%H%M%S', f'{str(int(x))}00' if is_min else str(int(x))).timestamp() for x in df.index]
                self.windowQ.put((ui_num['차트'], coin, xticks, arry_tick, buy_index, sell_index))
