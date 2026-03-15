
import os
import talib
import sqlite3
import numpy as np
import pandas as pd
from traceback import print_exc
from matplotlib import font_manager
from matplotlib import pyplot as plt
from trade.strategy_base import Strategy
from utility.static import timedelta_sec, error_decorator, str_ymdhms, dt_ymdhms, get_logger, add_rolling_data, dt_ymdhm
from utility.setting_base import ui_num, DB_TRADELIST, DB_PATH, DB_STOCK_BACK_TICK, DB_COIN_BACK_TICK, \
    DB_BACKTEST, DB_COIN_BACK_MIN, DB_STOCK_BACK_MIN, DB_CODE_INFO, DB_FUTURE_BACK_MIN, DB_FUTURE_BACK_TICK, \
    list_stock_min, list_coin_min, list_stock_tick2, list_stock_min2, list_coin_tick2, list_coin_min2, \
    list_future_tick2, list_future_min2, DB_STRATEGY


class Chart:
    def __init__(self, qlist, dict_set):
        """
        windowQ, soundQ, queryQ, teleQ, chartQ, hogaQ, webcQ, backQ, creceivQ, ctraderQ,  cstgQ, liveQ, kimpQ, wdzservQ, totalQ
           0        1       2      3       4      5      6      7       8         9         10     11    12      13       14
        """
        self.windowQ   = qlist[0]
        self.chartQ    = qlist[4]
        self.dict_set  = dict_set
        self.logger    = get_logger(self.__class__.__name__)
        self.dict_name = {}

        self.arry_kosp   = None
        self.arry_kosd   = None

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

        is_tick = False
        if coin:
            if 'KRW' in code: market = 3
            else:             market = 4
            if w_unit == '': w_unit = self.dict_set['코인평균값계산틱수']
            if starttime == '': starttime, endtime = '000000', '235000'
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
                    db_name2 = DB_STOCK_BACK_TICK
                else:
                    if starttime == '': starttime, endtime = '090000', '152000'
                    db_name1 = f'{DB_PATH}/stock_min_{searchdate}.db'
                    db_name2 = DB_STOCK_BACK_MIN
            else:
                market = 2
                if self.dict_set['주식타임프레임']:
                    is_tick  = True
                    if starttime == '': starttime, endtime = '093000', '103000'
                    db_name1 = f'{DB_PATH}/future_tick_{searchdate}.db'
                    db_name2 = DB_FUTURE_BACK_TICK
                else:
                    if starttime == '': starttime, endtime = '090000', '160000'
                    db_name1 = f'{DB_PATH}/future_min_{searchdate}.db'
                    db_name2 = DB_FUTURE_BACK_MIN

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
        else:
            if cf1 is None:
                arry = add_rolling_data(df, market, is_tick, [w_unit])
            else:
                arry = add_rolling_data(df, market, is_tick, [w_unit], cf1=cf1, cf2=cf2)

            buy_index  = []
            sell_index = []

            arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))
            if market in (2, 4):
                arry = np.column_stack((arry, np.zeros((arry.shape[0], 2))))

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
                        if market in (1, 3):
                            if df['주문구분'][index] == '매수':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -2] = df['체결가'][index]

                            elif df['주문구분'][index] == '매도':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -1] = df['체결가'][index]
                        else:
                            if df['주문구분'][index] == 'BUY_LONG':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -4] = df['체결가'][index]

                            elif df['주문구분'][index] == 'SELL_LONG':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -3] = df['체결가'][index]

                            elif df['주문구분'][index] == 'SELL_SHORT':
                                buy_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -2] = df['체결가'][index]

                            elif df['주문구분'][index] == 'BUY_SHORT':
                                sell_index.append(get_cgtime(cgtime))
                                arry[arry[:, 0] == cgtime, -1] =  df['체결가'][index]
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
                        추가매수시간, 추가매수가 = int(x[0]), int(x[1]) if market in (1, 2) else float(x[1])
                        buy_index.append(추가매수시간)
                        arry[arry[:, 0] == 추가매수시간, -2] = 추가매수가

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
                    print_exc()
                    self.logger.error(f'보조지표의 설정값이 잘못되었습니다.')

            con = sqlite3.connect(DB_STRATEGY)
            fm_df = pd.read_sql("SELECT * FROM formula", con)
            con.close()

            dict_fm  = fm_df.to_dict('index')
            dict_fm  = {k: v for k, v in dict_fm.items() if v['체크유무'] == 1}
            dict_fn  = {}
            fm_index = {}

            dict_count = {
                '선:일반': 1,
                '선:조건': 1,
                '화살표:일반': 1,
                '화살표:매매': 2,
                '범위': 3
            }

            fm_cnt = sum(dict_count[v['표시형태']] for v in dict_fm.values())
            if fm_cnt > 0:
                col_cnt = arry.shape[1]
                fm_index = {}
                for v in dict_fm.values():
                    fm_index[v['수식명']] = col_cnt
                    col_cnt += dict_count[v['표시형태']]

                dict_fn = set([v['팩터명'] for v in dict_fm.values()])
                dict_fn = {fn: {v['수식명']: [fm_index[v['수식명']], v['표시형태']] for v in dict_fm.values() if v['팩터명'] == fn} for fn in dict_fn}

                arry = np.column_stack((arry, np.zeros((arry.shape[0], fm_cnt))))
                fm = FormulaManager()
                fm.update_user_data(code, arry, market, is_tick, w_unit, dict_fm, fm_index)

            if arry is not None:
                if is_tick: xticks = [dt_ymdhms(str(int(x))).timestamp() for x in arry[:, 0]]
                else:       xticks = [dt_ymdhms(f'{int(x)}00').timestamp() for x in arry[:, 0]]
                gubun = 'C' if coin else 'S' if '키움증권' in self.dict_set['증권사'] else 'F'
                self.windowQ.put((ui_num['차트'], gubun, xticks, arry, buy_index, sell_index, dict_fm, fm_index, dict_fn, fm_cnt))


class FormulaManager(Strategy):
    def __init__(self):
        super().__init__()
        self.base_cnt = None
        self.check    = None
        self.buy      = None
        self.sell     = None
        self.line     = None
        self.up       = None
        self.down     = None
        self.hold     = False

        self.SetGlobalsFunc()

    def UpdateGlobalsFunc(self, dict_add_func):
        globals().update(dict_add_func)

    # noinspection PyUnusedLocal
    def update_user_data(self, code, arry, market, is_tick, w_unit, dict_fm, fm_index):
        self.code        = code
        self.arry_code   = arry
        self.is_tick     = is_tick
        self.avg_list    = [w_unit]
        self.high_low    = {}
        self.tick_count  = 0

        if market == 1:
            factor_list = list_stock_tick2 if self.is_tick else list_stock_min2
        elif market == 3:
            factor_list = list_coin_tick2 if self.is_tick else list_coin_min2
        else:
            factor_list = list_future_tick2 if self.is_tick else list_future_min2

        self.dict_findex = {name: i for i, name in enumerate(factor_list)}
        if self.is_tick:
            self.dict_findex['초당매도수금액'] = self.dict_findex['초당매수금액']
            self.dict_findex['누적초당매도수수량'] = self.dict_findex['누적초당매수수량']
        else:
            self.dict_findex['분당매도수금액'] = self.dict_findex['분당매수금액']
            self.dict_findex['누적분당매도수수량'] = self.dict_findex['누적분당매수수량']

        self.dict_findex['당일매도수금액'] = self.dict_findex['당일매수금액']
        self.dict_findex['최고매도수금액'] = self.dict_findex['최고매수금액']
        self.dict_findex['최고매도수가격'] = self.dict_findex['최고매수가격']
        self.dict_findex['호가총잔량'] = self.dict_findex['매수총잔량']
        self.dict_findex['매도수호가잔량1'] = self.dict_findex['매수잔량1']

        self.base_cnt = self.dict_findex['관심종목'] + 1

        fm_list = []
        for v in dict_fm.values():
            fm = list(v.values())
            fm[-1] = compile(fm[-1], '<string>', 'exec')
            fm_list.append(fm)

        for i, index in enumerate(self.arry_code[:, 0]):
            self.index  = int(index)
            self.indexn = i
            self.tick_count += 1

            if market == 1:
                if self.is_tick:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                        거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위, \
                        초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, \
                        매수호가5, 매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
                    VI해제시간 = dt_ymdhms(str(int(VI해제시간)))
                else:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                        거래대금증감, 전일비, 회전율, 전일동시간비, 시가총액, 라운드피겨위5호가이내, VI해제시간, VI가격, VI호가단위, \
                        분봉시가, 분봉고가, 분봉저가, \
                        분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
                    VI해제시간 = dt_ymdhms(str(int(VI해제시간)))
            else:
                if self.is_tick:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 초당매수수량, 초당매도수량, \
                        초당거래대금, 고저평균대비등락율, 저가대비고가등락율, 초당매수금액, 초당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]
                else:
                    현재가, 시가, 고가, 저가, 등락율, 당일거래대금, 체결강도, 분당매수수량, 분당매도수량, \
                        분봉시가, 분봉고가, 분봉저가, \
                        분당거래대금, 고저평균대비등락율, 저가대비고가등락율, 분당매수금액, 분당매도금액, 당일매수금액, 최고매수금액, 최고매수가격, 당일매도금액, 최고매도금액, 최고매도가격, \
                        매도호가5, 매도호가4, 매도호가3, 매도호가2, 매도호가1, 매수호가1, 매수호가2, 매수호가3, 매수호가4, 매수호가5, \
                        매도잔량5, 매도잔량4, 매도잔량3, 매도잔량2, 매도잔량1, 매수잔량1, 매수잔량2, 매수잔량3, 매수잔량4, 매수잔량5, \
                        매도총잔량, 매수총잔량, 매도수5호가잔량합, 관심종목 = self.arry_code[self.indexn, 1:self.base_cnt]

            시분초 = int(str(self.index)[8:]) if self.is_tick else int(str(self.index)[8:] + '00')
            # noinspection PyUnboundLocalVariable
            순매수금액 = 초당매수금액 - 초당매도금액 if self.is_tick else 분당매수금액 - 분당매도금액
            종목명, 종목코드, 데이터길이, 체결시간 = self.name, self.code, self.tick_count, self.index

            high_low = self.high_low.get(self.code)
            if self.is_tick:
                if high_low:
                    if 현재가 >= high_low[0]:
                        high_low[0] = 현재가
                        high_low[1] = self.indexn
                    if 현재가 <= high_low[2]:
                        high_low[2] = 현재가
                        high_low[3] = self.indexn
                else:
                    self.high_low[self.code] = [현재가, self.indexn, 현재가, self.indexn]
            else:
                if high_low:
                    # noinspection PyUnboundLocalVariable
                    if 분봉고가 >= high_low[0]:
                        high_low[0] = 분봉고가
                        high_low[1] = self.indexn
                    # noinspection PyUnboundLocalVariable
                    if 분봉저가 <= high_low[2]:
                        high_low[2] = 분봉저가
                        high_low[3] = self.indexn
                else:
                    self.high_low[self.code] = [분봉고가, self.indexn, 분봉저가, self.indexn]

            for name, _, fname, data_type, _, _, style, stg in fm_list:
                col_idx = fm_index[name]
                self.check, self.line, self.buy, self.sell, self.up, self.down = None, None, None, None, None, None
                try:
                    exec(stg)
                except:
                    pass

                if data_type == '선:일반':
                    if self.line is not None:
                        arry[i, col_idx] = self.line

                elif data_type == '선:조건':
                    if self.check is not None and self.line is not None:
                        if self.check:
                            arry[i, col_idx] = self.line
                        else:
                            pre_line = arry[i-1, col_idx]
                            if pre_line > 0:
                                arry[i, col_idx] = pre_line

                elif data_type == '화살표:일반':
                    if self.check is not None and self.check:
                        if self.is_tick or fname != '현재가':
                            price = arry[i, self.dict_findex[fname]]
                        else:
                            if style == 6:
                                price = 분봉저가
                            else:
                                price = 분봉고가
                        arry[i, col_idx] = price

                elif data_type == '화살표:매매':
                    if self.buy is not None and self.sell is not None:
                        if not self.hold and self.buy:
                            arry[i, col_idx] = 현재가
                            self.hold = True
                        elif self.hold and self.sell:
                            arry[i, col_idx + 1] = 현재가
                            self.hold = False

                elif data_type == '범위':
                    if self.check is not None and self.up is not None and self.down is not None:
                        arry[i, col_idx] = 1.0 if self.check else 0.0
                        arry[i, col_idx + 1] = self.up
                        arry[i, col_idx + 2] = self.down
