
import os
import talib
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from matplotlib import font_manager
from matplotlib import pyplot as plt
from utility.static import timedelta_sec, error_decorator, str_ymdhms, dt_ymdhms, get_logger, add_rolling_data, dt_ymdhm
from utility.setting import ui_num, DICT_SET, DB_TRADELIST, DB_PATH, DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, \
    DB_BACKTEST, DB_COIN_BACK_MIN, DB_STOCK_BACK_MIN, DB_CODE_INFO, DB_FUTURE_BACK_MIN, DB_FUTURE_BACK_TICK


class Chart:
    def __init__(self, qlist):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ   = qlist[0]
        self.chartQ    = qlist[4]
        self.dict_set  = DICT_SET
        self.logger    = get_logger(self.__class__.__name__)
        self.dict_name = {}

        con = sqlite3.connect(DB_CODE_INFO)
        df = pd.read_sql('SELECT * FROM stockinfo', con).set_index('index')
        self.dict_name.update(df['종목명'].to_dict())
        df = pd.read_sql('SELECT * FROM futureinfo', con).set_index('index')
        self.dict_name.update(df['종목명'].to_dict())
        con.close()

        font_name = 'C:/Windows/Fonts/malgun.ttf'
        font_family = font_manager.FontProperties(fname=font_name).get_name()
        plt.rcParams['font.family'] = font_family
        plt.rcParams['axes.unicode_minus'] = False

        self.arry_kosp  = None
        self.arry_kosd  = None
        self.MainLoop()

    def MainLoop(self):
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

    def UpdateRealJisu(self, data):
        gubun = data[0]
        jisu_data = data[1:]
        try:
            if gubun == '코스피':
                if self.arry_kosp is None:
                    self.arry_kosp = np.array([jisu_data])
                else:
                    self.arry_kosp = np.r_[self.arry_kosp, np.array([jisu_data])]
                xticks = [dt_ymdhms(str(int(x))).timestamp() for x in self.arry_kosp[:, 0]]
                self.windowQ.put((ui_num['코스피'], xticks, self.arry_kosp[:, 1]))
            elif gubun == '코스닥':
                if self.arry_kosd is None:
                    self.arry_kosd = np.array([jisu_data])
                else:
                    self.arry_kosd = np.r_[self.arry_kosd, np.array([jisu_data])]
                xticks = [dt_ymdhms(str(int(x))).timestamp() for x in self.arry_kosd[:, 0]]
                self.windowQ.put((ui_num['코스닥'], xticks, self.arry_kosd[:, 1]))
        except:
            pass

    @error_decorator
    def UpdateChart(self, data):
        def get_cgtime(cgtime_):
            while cgtime_ not in df.index:
                onesecago = timedelta_sec(-1, dt_ymdhms(str(cgtime_)) if is_tick else dt_ymdhm(str(cgtime_)))
                cgtime_ = int(str_ymdhms(onesecago))
            return cgtime_

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
        if starttime == '': return

        is_tick = False
        if coin:
            if 'KRW' in code: market = 3
            else:             market = 4
            if w_unit == '': w_unit = self.dict_set['코인평균값계산틱수']
            if self.dict_set['코인타임프레임']:
                is_tick  = True
                db_name1 = f'{DB_PATH}/coin_tick_{searchdate}.db'
                db_name2 = DB_COIN_BACK_TICK
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                           f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
            else:
                db_name1 = f'{DB_PATH}/coin_min_{searchdate}.db'
                db_name2 = DB_COIN_BACK_MIN
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 10000 + int(starttime)} and " \
                           f"`index` <= {int(searchdate) * 10000 + int(endtime)}"
        else:
            if w_unit == '': w_unit = self.dict_set['주식평균값계산틱수']
            if '키움증권' in self.dict_set['증권사']:
                market = 1
                if self.dict_set['주식타임프레임']:
                    is_tick  = True
                    db_name1 = f'{DB_PATH}/stock_tick_{searchdate}.db'
                    db_name2 = DB_STOCK_BACK_TICK
                else:
                    db_name1 = f'{DB_PATH}/stock_min_{searchdate}.db'
                    db_name2 = DB_STOCK_BACK_MIN
            else:
                market = 2
                if self.dict_set['주식타임프레임']:
                    is_tick  = True
                    db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db'
                    db_name2 = DB_FUTURE_BACK_TICK
                else:
                    db_name1 = f'{DB_PATH}/future_min_{searchdate}.db'
                    db_name2 = DB_FUTURE_BACK_MIN

            if self.dict_set['주식타임프레임']:
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 1000000 + int(starttime)} and " \
                           f"`index` <= {int(searchdate) * 1000000 + int(endtime)}"
            else:
                query1   = f"SELECT * FROM '{code}' WHERE " \
                           f"`index` >= {int(searchdate) * 10000 + int(starttime)} and " \
                           f"`index` <= {int(searchdate) * 10000 + int(endtime)}"

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

        if df is None or len(df) == 0:
            self.windowQ.put((ui_num['차트'], '차트오류', '', '', '', ''))
        else:
            if cf1 is None:
                arry = add_rolling_data(df, market, is_tick, [w_unit])
            else:
                arry = add_rolling_data(df, market, is_tick, [w_unit], cf1=cf1, cf2=cf2)

            buy_index  = []
            sell_index = []

            arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))
            if coin or '해외선물' in self.dict_set['증권사']:
                arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))

            if detail is None:
                con = sqlite3.connect(DB_TRADELIST)
                if coin:
                    df2 = pd.read_sql(f"SELECT * FROM c_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{code}'", con).set_index('index')
                else:
                    name = self.dict_name[code] if code in self.dict_name else code
                    if '키움증권' in self.dict_set['증권사']:
                        df2 = pd.read_sql(f"SELECT * FROM s_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
                    else:
                        df2 = pd.read_sql(f"SELECT * FROM f_chegeollist WHERE 체결시간 LIKE '{searchdate}%' and 종목명 = '{name}'", con).set_index('index')
                con.close()

                if len(df2) > 0:
                    for index in df2.index:
                        cgtime = int(df2['체결시간'][index] if is_tick else str(df2['체결시간'][index])[:12])
                        if market in (1, 3):
                            if df2['주문구분'][index] == '매수':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -2] = df2['체결가'][index]

                            elif df2['주문구분'][index] == '매도':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -1] = df2['체결가'][index]
                        else:
                            if df2['주문구분'][index] == 'BUY_LONG':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -4] = df2['체결가'][index]

                            elif df2['주문구분'][index] == 'SELL_LONG':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -3] = df2['체결가'][index]

                            elif df2['주문구분'][index] == 'SELL_SHORT':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -2] = df2['체결가'][index]

                            elif df2['주문구분'][index] == 'BUY_SHORT':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -1] =  df2['체결가'][index]
            else:
                매수시간, 매수가, 매도시간, 매도가 = detail
                buy_index.append(매수시간)
                sell_index.append(매도시간)

                arry[arry[:, 0] == 매수시간, -2] = 매수가
                arry[arry[:, 0] == 매도시간, -1] = 매도가

                if buytimes:
                    buytimes = buytimes.split('^')
                    buytimes = [x.split(';') for x in buytimes]
                    for x in buytimes:
                        추가매수시간, 추가매수가 = int(x[0]), int(x[1]) if not coin else float(x[1])
                        buy_index.append(추가매수시간)
                        arry[arry[:, 0] == 추가매수시간, -2] = 추가매수가

            if not is_tick:
                arry = np.r_['1', arry, np.zeros((len(arry), 28))]
                try:
                    mc = arry[:, 1]
                    if coin or '해외선물' in self.dict_set['증권사']:
                        mh = arry[:, 11]
                        ml = arry[:, 12]
                        mv = arry[:, 13]
                    else:
                        mh = arry[:, 20]
                        ml = arry[:, 21]
                        mv = arry[:, 22]

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
                    self.logger.error(f'보조지표의 설정값이 잘못되었습니다.')
                    print_exc()

            if arry is not None:
                if is_tick: xticks = [dt_ymdhms(str(int(x))).timestamp() for x in arry[:, 0]]
                else:       xticks = [dt_ymdhms(f'{int(x)}00').timestamp() for x in arry[:, 0]]
                gubun = 'C' if coin else 'S' if '키움증권' in self.dict_set['증권사'] else 'F'
                self.windowQ.put((ui_num['차트'], gubun, xticks, arry, buy_index, sell_index))
